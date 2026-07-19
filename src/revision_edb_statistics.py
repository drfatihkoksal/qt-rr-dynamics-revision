"""Subject-aware generic ST-episode-versus-baseline EDB statistics."""
from pathlib import Path
import pandas as pd
from revision_statistics import (beat_cluster_wls, episode_summaries,
                                 paired_episode_effects, subject_bootstrap)


def main():
    path=Path('revision_work/analysis/edb_residuals_revised.parquet')
    outdir=Path('revision_work/analysis');ep=episode_summaries(path);effects=paired_episode_effects(ep)
    ep.to_csv(outdir/'edb_episode_level_results.csv',index=False)
    effects.to_csv(outdir/'edb_episode_matched_effects.csv',index=False)
    rows=[]
    for outcome in ('mean_abs_resid_ms','median_abs_resid_ms','mean_signed_resid_ms','median_signed_resid_ms'):
        value=f'delta_{outcome}';est,lo,hi,p=subject_bootstrap(effects,value)
        rows.append({'contrast':'generic_st_episode_vs_baseline','analysis_level':'subject_equal_weight',
                     'model':'subject_mean_with_subject_bootstrap','weighting':'equal_subject','outcome':outcome,
                     'effect_ms':est,'ci_low_ms':lo,'ci_high_ms':hi,'p_value':p,
                     'independent_subjects':effects.subject_id.nunique(),'episodes':len(effects)})
    for outcome in ('abs_resid_ms','resid_ms'):
        for weighted in (False,True):
            row=beat_cluster_wls(path,outcome,'ischemic','matched_baseline',weighted)
            row['contrast']='generic_st_episode_vs_baseline';rows.append(row)
    result=pd.DataFrame(rows);result.insert(0,'analysis_id',[f'EDB_{i+1:03d}' for i in range(len(result))])
    result.to_csv(outdir/'edb_hierarchical_effects.csv',index=False);print(result.to_string(index=False))


if __name__=='__main__':main()
