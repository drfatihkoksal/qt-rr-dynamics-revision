"""Subject-equal specification curve across protocol and hysteresis choices."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from revision_statistics import partially_paired_subject_bootstrap


def one_sample(subject_values):
    x=np.asarray(subject_values,float);est=x.mean();se=stats.sem(x);c=stats.t.ppf(.975,len(x)-1)
    return est,est-c*se,est+c*se,2*stats.t.sf(abs(est/se),len(x)-1)


def main():
    path=Path('revision_work/analysis/hysteresis_protocol_episode_summaries.csv')
    e=pd.read_csv(path);rows=[]
    for spec,d in e.groupby('specification'):
        keys=['record','subject_id','lead','episode_id']
        events=d[d.episode_type.isin(['ischemic','rate_related'])]
        base=d[d.episode_type=='matched_baseline']
        paired=events.merge(base[keys+['mean_abs_resid_ms','mean_signed_resid_ms']],on=keys,
                            suffixes=('_episode','_baseline'))
        for outcome in ('mean_abs_resid_ms','mean_signed_resid_ms'):
            for kind,name in (('ischemic','ischemic_vs_baseline'),('rate_related','hr_vs_baseline')):
                sub=paired[paired.episode_type==kind].copy()
                sub['delta']=sub[f'{outcome}_episode']-sub[f'{outcome}_baseline']
                sv=sub.groupby('subject_id').delta.mean();est,lo,hi,p=one_sample(sv)
                rows.append({'specification':spec,'contrast':name,'outcome':outcome,'effect_ms':est,
                             'ci_low_ms':lo,'ci_high_ms':hi,'p_value':p,'subjects':len(sv),'episodes':len(sub)})
            sm=events.groupby(['subject_id','episode_type'])[outcome].mean().unstack()
            est,lo,hi,p,n_unique,n_isc,n_hr,n_both=partially_paired_subject_bootstrap(
                sm,outcome,seed=20260721)
            rows.append({'specification':spec,'contrast':'ischemic_vs_hr','outcome':outcome,
                         'effect_ms':est,'ci_low_ms':lo,'ci_high_ms':hi,'p_value':p,
                         'subjects':n_unique,'episodes':len(events),
                         'ischemic_subjects':n_isc,'hr_subjects':n_hr,
                         'overlapping_subjects':n_both,
                         'model':'partially_paired_unique_subject_bootstrap'})
    out=pd.DataFrame(rows);out.to_csv('revision_work/analysis/sensitivity_effects.csv',index=False)
    tau=(e[['specification','record','subject_id','lead','tau_s','baseline_cv_r2']]
         .drop_duplicates().sort_values(['specification','record','lead']))
    tau.to_csv('revision_work/analysis/tau_selection_by_specification.csv',index=False)
    print(out[out.outcome=='mean_abs_resid_ms'].to_string(index=False))


if __name__=='__main__':main()
