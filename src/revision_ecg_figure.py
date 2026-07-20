"""Generate reproducible Reviewer-1 ECG strips and aligned trend figure."""
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import wfdb

from beat_extraction import load_model, run_delineation
from dataset import WIN_BEFORE, WIN_AFTER
from episodes import parse_ltstdb_episodes


FS=250.0
DATA=Path('revision_work/data/ltstdb_verified')
SOURCE=Path('revision_work/figure_source');SOURCE.mkdir(parents=True,exist_ok=True)
FIG=Path('paper/figures_revision');FIG.mkdir(parents=True,exist_ok=True)


def st_trend(record,lead,start,stop):
    candidates=[Path('ltstdb/ltstdb/1.0.0')/f'{record}.stf',Path('LTSTDB_ISCHEMIC')/f'{record}.stf']
    path=next(p for p in candidates if p.exists())
    raw=np.loadtxt(path,usecols=(0,3+3*lead))
    raw=raw[(raw[:,0]>=start)&(raw[:,0]<=stop)]
    return pd.DataFrame({'sample':raw[:,0].astype(int),'st_deviation_uv':raw[:,1]*5.0})


def selected_beat(con,record,lead,kind,eid):
    rows=con.execute("""select * from read_parquet('revision_work/analysis/ltstdb_residuals_revised.parquet')
      where record=? and lead=? and episode_type=? and episode_id=? and analysis_eligible
      order by sample""",[record,int(lead),kind,int(eid)]).fetchdf()
    target=rows.abs_resid_ms.median();return rows.iloc[(rows.abs_resid_ms-target).abs().argmin()]


def strip_data(model,device,row,panel):
    peak=int(row['sample']);start=peak-WIN_BEFORE;stop=peak+WIN_AFTER
    sig=wfdb.rdrecord(str(DATA/row['record']),sampfrom=start,sampto=stop,
                      channels=[int(row['lead'])]).p_signal[:,0].astype(np.float32)
    pred=run_delineation(model,device,sig,np.array([WIN_BEFORE]))
    q=float(pred['qrs_onset'][0]);t=float(pred['t_offset'][0])
    qs=float(pred['qrs_onset_sigma'][0]/FS*1000);ts=float(pred['t_offset_sigma'][0]/FS*1000)
    out=pd.DataFrame({'panel':panel,'time_s':(np.arange(len(sig))-WIN_BEFORE)/FS,
                      'amplitude_mv':sig})
    meta={'panel':panel,'record':row['record'],'subject_id':row['subject_id'],'lead':int(row['lead']),
          'episode_type':row['episode_type'],'episode_id':int(row['episode_id']),'beat_sample':peak,
          'qrs_onset_time_s':(q-WIN_BEFORE)/FS,'t_offset_time_s':(t-WIN_BEFORE)/FS,
          'qrs_onset_sigma_ms':qs,'t_offset_sigma_ms':ts,'qt_ms':row['qt_ms'],
          'pred_qt_ms':row['pred_qt_ms'],'signed_resid_ms':row['resid_ms'],
          'abs_resid_ms':row['abs_resid_ms'],'rr_ms':row['rr_ms'],
          'heart_rate_bpm':60000/row['rr_ms'],'qt_sigma_ms':row['qt_sigma_ms']}
    return out,meta


def trend_data(con,record,lead,start,stop,case):
    d=con.execute("""select sample,rr_smoothed_ms,resid_ms,abs_resid_ms,qt_sigma_ms,episode_type
      from read_parquet('revision_work/analysis/ltstdb_residuals_revised.parquet')
      where record=? and lead=? and sample between ? and ? and analysis_eligible order by sample""",
      [record,int(lead),int(start),int(stop)]).fetchdf()
    d['bin']=(d['sample']//2500).astype(int)
    agg=d.groupby('bin',as_index=False).agg(sample=('sample','median'),rr_smoothed_ms=('rr_smoothed_ms','median'),
        signed_resid_ms=('resid_ms','median'),abs_resid_ms=('abs_resid_ms','median'),
        qt_sigma_ms=('qt_sigma_ms','median'))
    agg['heart_rate_bpm']=60000/agg.rr_smoothed_ms;agg['case']=case
    st=st_trend(record,int(lead),start,stop);st['bin']=(st['sample']//2500).astype(int)
    st=st.groupby('bin',as_index=False).agg(sample=('sample','median'),st_deviation_uv=('st_deviation_uv','median'))
    agg=agg.merge(st[['bin','st_deviation_uv']],on='bin',how='left')
    agg['time_h']=(agg['sample']-start)/FS/3600
    episodes,_=parse_ltstdb_episodes(str(DATA/record),'stb')
    spans=pd.DataFrame([{'case':case,'record':record,'lead':lead,'episode_type':x['kind'],
                         'start_h':(max(x['onset'],start)-start)/FS/3600,
                         'stop_h':(min(x['offset'],stop)-start)/FS/3600}
                        for x in episodes if x['lead']==lead and x['offset']>=start and x['onset']<=stop])
    return agg,spans


def shade(ax,spans):
    colors={'ischemic':'#d95f5f','rate_related':'#4c78a8'}
    for _,s in spans.iterrows():ax.axvspan(s.start_h,s.stop_h,color=colors[s.episode_type],alpha=.16,lw=0)


def main():
    sel=pd.read_csv('revision_work/analysis/selected_ecg_examples.csv');con=duckdb.connect();model,device=load_model()
    a=sel[sel.case=='A'];ai=a[a.episode_type=='ischemic'].iloc[0];ah=a[a.episode_type=='rate_related'].iloc[0];b=sel[sel.case=='B'].iloc[0]
    specs=[('A baseline',ai,'matched_baseline'),('A ischemic',ai,'ischemic'),
           ('A HR-related',ah,'rate_related'),('B baseline',b,'matched_baseline'),('B HR-related',b,'rate_related')]
    strips=[];metas=[]
    for panel,r,kind in specs:
        row=selected_beat(con,r.record,r.lead,kind,r.episode_id);d,m=strip_data(model,device,row,panel);strips.append(d);metas.append(m)
    strips=pd.concat(strips);meta=pd.DataFrame(metas);strips.to_csv(SOURCE/'figure1_ecg_strips.csv',index=False);meta.to_csv(SOURCE/'figure1_ecg_metadata.csv',index=False)
    astart=min(ai.first_sample_episode,ah.first_sample_episode)-5*60*FS;astop=max(ai.last_sample_episode,ah.last_sample_episode)+5*60*FS
    bstart=min(b.first_sample_episode,b.first_sample_baseline)-5*60*FS;bstop=max(b.last_sample_episode,b.last_sample_baseline)+5*60*FS
    ta,sa=trend_data(con,ai.record,ai.lead,astart,astop,'A');tb,sb=trend_data(con,b.record,b.lead,bstart,bstop,'B')
    pd.concat([ta,tb]).to_csv(SOURCE/'figure1_trends.csv',index=False);pd.concat([sa,sb]).to_csv(SOURCE/'figure1_episode_spans.csv',index=False)
    fig=plt.figure(figsize=(13,13.5),layout='constrained');gs=fig.add_gridspec(8,2)
    # Five morphology strips.
    positions=[(0,0),(1,0),(2,0),(0,1),(1,1)]
    for (panel,_),pos in zip([(x[0],x[1]) for x in specs],positions):
        ax=fig.add_subplot(gs[pos]);d=strips[strips.panel==panel];m=meta[meta.panel==panel].iloc[0]
        ax.plot(d.time_s,d.amplitude_mv,color='black',lw=.7)
        ax.axvline(m.qrs_onset_time_s,color='#f58518',lw=1,label='QRS onset');ax.axvline(m.t_offset_time_s,color='#54a24b',lw=1,label='T offset')
        ax.axvspan(m.qrs_onset_time_s-m.qrs_onset_sigma_ms/1000,m.qrs_onset_time_s+m.qrs_onset_sigma_ms/1000,color='#f58518',alpha=.12)
        ax.axvspan(m.t_offset_time_s-m.t_offset_sigma_ms/1000,m.t_offset_time_s+m.t_offset_sigma_ms/1000,color='#54a24b',alpha=.12)
        ax.set_title(f"{panel}: QT {m.qt_ms:.1f} ms; expected {m.pred_qt_ms:.1f}; residual {m.signed_resid_ms:+.1f} ms")
        ax.set(xlabel='Time from R peak (s)',ylabel='ECG (mV)',xlim=(-.5,.8));ax.grid(alpha=.15)
    # Four aligned trends per case.
    for col,(tr,sp,title) in enumerate(((ta,sa,'Case A: same subject/lead'),(tb,sb,'Case B: no annotated ischemic episode'))):
        variables=[('heart_rate_bpm','Heart rate (bpm)'),('st_deviation_uv','ST deviation (µV)'),
                   ('signed_resid_ms','Signed residual (ms)'),('abs_resid_ms','Absolute residual (ms)'),
                   ('qt_sigma_ms','QT uncertainty (ms)')]
        for j,(var,label) in enumerate(variables,start=3):
            ax=fig.add_subplot(gs[j,col]);ax.plot(tr.time_h,tr[var],color='black',lw=.65);shade(ax,sp)
            ax.set_ylabel(label);ax.grid(alpha=.15)
            if j==3:ax.set_title(title)
            if j==7:ax.set_xlabel('Hours from displayed-window start')
    handles=[plt.Line2D([0],[0],color='#d95f5f',lw=8,alpha=.25,label='Database-labeled ischemic'),
             plt.Line2D([0],[0],color='#4c78a8',lw=8,alpha=.25,label='Database-labeled HR-related')]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,-.025),ncol=2)
    fig.savefig(FIG/'figure1_ecg_examples.png',dpi=300,bbox_inches='tight',pad_inches=.18)
    fig.savefig(FIG/'figure1_ecg_examples.tiff',dpi=300,bbox_inches='tight',pad_inches=.18,
                pil_kwargs={'compression':'tiff_lzw'})
    con.close();print(meta.to_string(index=False))


if __name__=='__main__':main()
