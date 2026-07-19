"""Reproducibly select non-extreme ECG examples for Reviewer 1."""
from pathlib import Path
import pandas as pd


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
    chosen_key=score.index[0]
    chosen=candidate[(candidate.subject_id==chosen_key[0])&(candidate.record==chosen_key[1])&
                     (candidate.lead==chosen_key[2])]
    rows=[]
    for kind in ('ischemic','rate_related'):
        sub=chosen[chosen.episode_type==kind].copy();target=sub.effect.median()
        row=sub.iloc[(sub.effect-target).abs().argmin()].copy();row['case']='A';rows.append(row)
    # Case B: HR episode from a subject with no raw ischemic annotation,
    # closest to that subgroup's median effect.
    b=event[(event.episode_type=='rate_related')&~event.subject_id.isin(raw_ischemic)].copy()
    target=b.effect.median();row=b.iloc[(b.effect-target).abs().argmin()].copy();row['case']='B';rows.append(row)
    out=pd.DataFrame(rows)
    keep=['case','subject_id','record','lead','episode_type','episode_id','first_sample_episode',
          'last_sample_episode','first_sample_baseline','last_sample_baseline',
          'mean_abs_resid_ms_episode','mean_abs_resid_ms_baseline','effect']
    out[keep].to_csv('revision_work/analysis/selected_ecg_examples.csv',index=False)
    print(out[keep].to_string(index=False))


if __name__=='__main__':main()
