"""Generate revised statistical, calibration, and sensitivity figures."""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT=Path('paper/figures_revision');OUT.mkdir(parents=True,exist_ok=True)


def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=300,bbox_inches='tight')
    fig.savefig(OUT/f'{name}.tiff',dpi=300,bbox_inches='tight',pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)


def figure2():
    ep=pd.read_csv('revision_work/analysis/episode_level_results.csv')
    ef=pd.read_csv('revision_work/analysis/episode_matched_effects.csv')
    hier=pd.read_csv('revision_work/analysis/hierarchical_effects.csv')
    sub=pd.read_csv('revision_work/analysis/subgroup_effects.csv')
    fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    rng=np.random.default_rng(42)
    for i,(kind,color) in enumerate((('ischemic','#d95f5f'),('rate_related','#4c78a8'))):
        d=ef[ef.episode_type==kind];y=d.delta_mean_abs_resid_ms
        axs[0,0].scatter(rng.normal(i,.06,len(y)),y,s=8,alpha=.25,color=color)
        sv=d.groupby('subject_id').delta_mean_abs_resid_ms.mean()
        axs[0,0].errorbar(i,sv.mean(),yerr=1.96*sv.sem(),fmt='o',color='black',capsize=4,zorder=5)
    axs[0,0].axhline(0,color='grey',lw=.8);axs[0,0].set_xticks([0,1],['Ischemic','HR-related'])
    axs[0,0].set_yscale('symlog',linthresh=20)
    axs[0,0].set_ylabel('Episode − matched baseline\nmean absolute residual (ms)');axs[0,0].set_title('A  Episode heterogeneity')
    event=ep[ep.episode_type.isin(['ischemic','rate_related'])]
    sm=event.groupby(['subject_id','episode_type']).mean_abs_resid_ms.mean().unstack()
    for i,(kind,color,label) in enumerate((('ischemic','#d95f5f','Ischemic'),('rate_related','#4c78a8','HR-related'))):
        vals=sm[kind].dropna();axs[0,1].scatter(rng.normal(i,.05,len(vals)),vals,s=24,alpha=.65,color=color)
        axs[0,1].errorbar(i,vals.mean(),yerr=1.96*vals.sem(),fmt='D',color='black',capsize=4)
    for _,r in sm.dropna().iterrows():axs[0,1].plot([0,1],[r.ischemic,r.rate_related],color='grey',alpha=.35,lw=.7)
    axs[0,1].set_xticks([0,1],['Ischemic','HR-related']);axs[0,1].set_ylabel('Subject-mean absolute residual (ms)')
    axs[0,1].set_title('B  Subject-level values; paired lines for both-label subjects')
    q=sub[(sub.analysis=='hr_episode_vs_baseline')&(sub.subgroup_variable=='raw_ischemic_overlap')&
          (sub.outcome=='mean_abs_resid_ms')]
    for i,(_,r) in enumerate(q.iterrows()):
        axs[1,0].errorbar(r.effect_ms,i,xerr=[[r.effect_ms-r.ci_low_ms],[r.ci_high_ms-r.effect_ms]],fmt='o',capsize=4,
                          color=('#d95f5f' if 'any_raw' in r.subgroup else '#4c78a8'))
    axs[1,0].axvline(0,color='grey',lw=.8);axs[1,0].set_yticks(range(len(q)),['Any annotated ischemic episode','No annotated ischemic episode'])
    axs[1,0].set_xlabel('HR-related episode − baseline (ms)');axs[1,0].set_title('C  Reviewer-requested overlap subgroups')
    ids=['LTST_002','LTST_010','LTST_018','LTST_019'];labels=['Ischemic − baseline','HR-related − baseline','Ischemic − HR-related','Within-subject ischemic − HR-related']
    q=hier.set_index('analysis_id').loc[ids]
    for i,(_,r) in enumerate(q.iterrows()):axs[1,1].errorbar(r.effect_ms,i,xerr=[[r.effect_ms-r.ci_low_ms],[r.ci_high_ms-r.effect_ms]],fmt='o',color='black',capsize=4)
    axs[1,1].axvline(0,color='grey',lw=.8);axs[1,1].set_yticks(range(4),labels);axs[1,1].invert_yaxis();axs[1,1].set_xlabel('Difference in mean absolute residual (ms)')
    axs[1,1].set_title('D  Subject-equal primary estimands')
    for ax in axs.flat:ax.grid(alpha=.15)
    save(fig,'figure2_subject_episode_effects')


def figure3():
    landmark=pd.read_csv('results/coverage_picp.csv');qt=pd.read_csv('revision_work/analysis/direct_qt_picp.csv')
    source_map={'finetune_val (single expert)':'Same-protocol validation','calibration (annotator 1)':'Fully held-out, annotator 1',
                'calibration (annotator 2)':'Fully held-out, annotator 2','same_protocol_validation':'Same-protocol validation',
                'fully_held_out_annotator_1':'Fully held-out, annotator 1','fully_held_out_annotator_2':'Fully held-out, annotator 2'}
    levels=np.array([50,68,80,90,95]);fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    colors=['#4c78a8','#f58518','#54a24b']
    for color,(source,d) in zip(colors,landmark[landmark.landmark=='t_offset'].groupby('source',sort=False)):
        axs[0].plot(levels,[d.iloc[0][f'PICP_{x}']*100 for x in levels],marker='o',label=source_map[source],color=color)
    for color,(source,d) in zip(colors,qt[qt.method=='independence'].groupby('source',sort=False)):
        axs[1].plot(levels,[d.iloc[0][f'picp_{x}']*100 for x in levels],marker='o',label=source_map[source],color=color)
    for ax,title in zip(axs,['A  T-offset prediction intervals','B  Direct QT intervals (independence approximation)']):
        ax.plot(levels,levels,'--',color='black',lw=1,label='Nominal');ax.set(xlabel='Nominal coverage (%)',ylabel='Empirical coverage (%)',title=title,xlim=(48,97),ylim=(45,100));ax.grid(alpha=.2)
    axs[1].legend(fontsize=8,loc='lower right');save(fig,'figure3_calibration')


def supplementary():
    sens=pd.read_csv('revision_work/analysis/sensitivity_effects.csv')
    q=sens[(sens.contrast=='ischemic_vs_hr')&(sens.outcome=='mean_abs_resid_ms')].copy().sort_values('effect_ms')
    fig,ax=plt.subplots(figsize=(7,4.5),layout='constrained')
    y=np.arange(len(q));ax.errorbar(q.effect_ms,y,xerr=[q.effect_ms-q.ci_low_ms,q.ci_high_ms-q.effect_ms],fmt='o',color='black',capsize=3)
    ax.axvline(0,color='grey',lw=.8);ax.set_yticks(y,q.specification);ax.set_xlabel('Subject-equal ischemic − HR-related difference (ms)');ax.grid(alpha=.2)
    save(fig,'figureS1_specification_curve')
    tau=pd.read_csv('revision_work/analysis/tau_selection_primary_all_record_leads.csv')
    fig,ax=plt.subplots(figsize=(6,4),layout='constrained');bins=np.array([5,12.5,17.5,25,37.5,52.5,75,105,135,165,210,270,330])
    ax.hist(tau.tau_s,bins=bins,color='#4c78a8',edgecolor='white');ax.set(xlabel='Selected tau (s)',ylabel='Record-leads',title='Primary individualized hysteresis constants');ax.grid(axis='y',alpha=.2)
    save(fig,'figureS2_tau_distribution')
    ep=pd.read_csv('revision_work/analysis/episode_level_results.csv');ep=ep[ep.episode_type.isin(['ischemic','rate_related'])]
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
    for kind,color in [('ischemic','#d95f5f'),('rate_related','#4c78a8')]:
        x=ep.loc[ep.episode_type==kind,'median_signed_resid_ms'];ax.hist(x,bins=50,density=True,histtype='step',lw=1.5,color=color,label=kind.replace('_',' '))
    ax.axvline(0,color='grey',lw=.8);ax.set(xlabel='Episode median signed residual (ms)',ylabel='Density');ax.legend();ax.grid(alpha=.15)
    save(fig,'figureS3_signed_residuals')
    conc=pd.read_csv('revision_work/audit/cross_lead_concordance_stb.csv')
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained');labels=(conc.concordance_status+' / '+conc.consolidated_label).str.replace('_',' ')
    ax.barh(labels,conc.duration_s/3600,color='#72b7b2');ax.set_xlabel('Annotated duration (hours)');ax.grid(axis='x',alpha=.2)
    save(fig,'figureS4_cross_lead_concordance')


if __name__=='__main__':figure2();figure3();supplementary()
