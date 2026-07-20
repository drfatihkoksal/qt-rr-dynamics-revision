"""Reproducibly select non-extreme ECG examples for Reviewer 1."""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import wfdb


DATA = Path('revision_work/data/ltstdb_verified')
RESIDUALS = 'revision_work/analysis/ltstdb_residuals_revised.parquet'
WIN_BEFORE, WIN_AFTER = 200, 300


def representative_episode_rows(candidate, key):
    chosen = candidate[(candidate.subject_id == key[0]) &
                       (candidate.record == key[1]) &
                       (candidate.lead == key[2])]
    rows = []
    for kind in ('ischemic', 'rate_related'):
        sub = chosen[chosen.episode_type == kind].copy()
        target = sub.effect.median()
        rows.append(sub.iloc[(sub.effect - target).abs().argmin()].copy())
    return rows


def strip_roughness(con, record, lead, episode_type, episode_id):
    beats = con.execute(f"""select sample,abs_resid_ms from read_parquet('{RESIDUALS}')
        where record=? and lead=? and episode_type=? and episode_id=? and analysis_eligible
        order by sample""", [record, int(lead), episode_type, int(episode_id)]).fetchdf()
    target = beats.abs_resid_ms.median()
    peak = int(beats.iloc[(beats.abs_resid_ms - target).abs().argmin()]['sample'])
    signal = wfdb.rdrecord(str(DATA / record), sampfrom=peak-WIN_BEFORE,
                           sampto=peak+WIN_AFTER, channels=[int(lead)]).p_signal[:, 0]
    amplitude = np.percentile(signal, 95) - np.percentile(signal, 5)
    return float(np.median(np.abs(np.diff(signal))) / max(amplitude, 1e-6))


def main():
    effects=pd.read_csv('revision_work/analysis/episode_matched_effects.csv')
    raw=pd.read_csv('revision_work/audit/ltstdb_raw_episodes_stb.csv')
    raw_ischemic=set(raw.loc[raw.episode_type=='ischemic','subject_id'])
    event=effects.copy();event['effect']=event.mean_abs_resid_ms_episode-event.mean_abs_resid_ms_baseline
    # Case A requires both labels in the same subject and lead.
    counts=event.groupby(['subject_id','record','lead']).episode_type.nunique()
    eligible=set(counts[counts==2].index)
    candidate=event[event.apply(lambda r:(r.subject_id,r.record,r.lead) in eligible,axis=1)].copy()
    # Choose the subject-record-lead medoid by distance of its two label means
    # to their respective eligible-group medians.
    med=candidate.groupby('episode_type').effect.median()
    score=(candidate.assign(distance=lambda d:(d.effect-d.episode_type.map(med)).abs())
           .groupby(['subject_id','record','lead']).distance.mean().sort_values())
    # Preserve a non-extreme example while preferring clean morphology strips:
    # among candidates within 2.5 ms of the best medoid score, retain only
    # morphology strips that pass the documented visual QC, then minimize the worst
    # normalized point-to-point roughness across baseline and both label strips.
    near=score[score <= score.iloc[0] + 2.5]
    qc=pd.read_csv('revision_work/audit/figure1_candidate_visual_qc.csv')
    passed={(r.subject_id,r.record,int(r.lead)) for _,r in qc[qc.visual_qc_pass==1].iterrows()}
    near=near[[key in passed for key in near.index]]
    if near.empty:
        raise RuntimeError('No visually clean candidate remained within the non-extreme medoid range')
    con=duckdb.connect();quality=[]
    for key,medoid_distance in near.items():
        ischemic,rate_related=representative_episode_rows(candidate,key)
        display_span_h=(max(ischemic.last_sample_episode,rate_related.last_sample_episode)-
                        min(ischemic.first_sample_episode,rate_related.first_sample_episode))/250/3600
        roughness=[
            strip_roughness(con,key[1],key[2],'matched_baseline',ischemic.episode_id),
            strip_roughness(con,key[1],key[2],'ischemic',ischemic.episode_id),
            strip_roughness(con,key[1],key[2],'rate_related',rate_related.episode_id),
        ]
        quality.append((key,float(medoid_distance),max(roughness),float(display_span_h)))
    con.close()
    chosen_key,medoid_distance,max_roughness,display_span_h=min(
        quality,key=lambda x:(x[2],x[1]))
    rows=representative_episode_rows(candidate,chosen_key)
    for row in rows:
        row['case']='A';row['selection_medoid_distance_ms']=medoid_distance
        row['selection_max_normalized_roughness']=max_roughness
        row['selection_display_span_h']=display_span_h
        row['visual_qc_pass']=1
    # Case B: HR episode from a subject with no raw ischemic annotation,
    # closest to that subgroup's median effect.
    b=event[(event.episode_type=='rate_related')&~event.subject_id.isin(raw_ischemic)].copy()
    target=b.effect.median();row=b.iloc[(b.effect-target).abs().argmin()].copy();row['case']='B'
    row['selection_medoid_distance_ms']=np.nan;row['selection_max_normalized_roughness']=np.nan;rows.append(row)
    row['selection_display_span_h']=np.nan
    row['visual_qc_pass']=np.nan
    out=pd.DataFrame(rows)
    keep=['case','subject_id','record','lead','episode_type','episode_id','first_sample_episode',
          'last_sample_episode','first_sample_baseline','last_sample_baseline',
          'mean_abs_resid_ms_episode','mean_abs_resid_ms_baseline','effect',
          'selection_medoid_distance_ms','selection_max_normalized_roughness']
    keep.append('selection_display_span_h')
    keep.append('visual_qc_pass')
    out[keep].to_csv('revision_work/analysis/selected_ecg_examples.csv',index=False)
    print(out[keep].to_string(index=False))


if __name__=='__main__':main()
