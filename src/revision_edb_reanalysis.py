"""Corrected generic ST-episode-versus-baseline EDB reanalysis."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from baseline_fit import rr_smoothed
from episodes import parse_edb_episodes
from revision_residual_reanalysis import PRIMARY_GRID, select_tau_continuous
from run_residual_pipeline import assign_matched_baseline, label_episodes


SAME_SUBJECT_GROUPS=[{"e0118","e0119","e0120","e0121","e0122"},
                     {"e0123","e0124","e0125","e0126"},{"e0129","e0133"},
                     {"e0136","e0139"},{"e0147","e0148"},{"e0154","e0155"},
                     {"e0162","e0163"}]


def subject_id(record):
    for group in SAME_SUBJECT_GROUPS:
        if record in group:return sorted(group)[0]+"_subject"
    return record+"_subject"


def process(df,record,lead,data_dir):
    df=df.sort_values('sample').reset_index(drop=True)
    episodes,_=parse_edb_episodes(str(data_dir/record)); episodes=[x for x in episodes if x['lead']==lead]
    raw,_,_=label_episodes(len(df),df['sample'].to_numpy(),episodes,0,250.)
    plausible=(df.qt_ms.between(200,700)&df.rr_ms.gt(0)&df.rr_ms.notna()).to_numpy()
    fit=select_tau_continuous(df,(raw==None)&plausible,PRIMARY_GRID)  # noqa:E711
    if fit is None:return None
    samples=df['sample'].to_numpy(); label,eid,spans=label_episodes(len(df),samples,episodes,1.5*fit['tau'],250.)
    ml,mid=assign_matched_baseline(len(df),samples,label,spans,250.)
    sm=rr_smoothed(df.rr_ms.to_numpy(),fit['tau']); pred=np.exp(fit['intercept']+fit['slope']*np.log(np.clip(sm,1,None)))
    resid=df.qt_ms.to_numpy()-pred; time=samples/250.; hr=60000/np.clip(sm,1,None)
    out=df.copy(); out['subject_id']=subject_id(record)
    out['episode_type']=pd.array(np.where(label!=None,label,ml),dtype='string')  # noqa:E711
    out['episode_id']=np.where(label!=None,eid,mid)  # noqa:E711
    out['rr_smoothed_ms']=sm; out['drr_dt_ms_per_s']=np.gradient(sm,time)
    out['dhr_dt_bpm_per_s']=np.gradient(hr,time); out['pred_qt_ms']=pred
    out['resid_ms']=resid; out['abs_resid_ms']=np.abs(resid); out['tau_s']=fit['tau']
    out['baseline_cv_r2']=fit['cv_r2']; out['baseline_full_r2']=fit['full_r2'];out['baseline_n_beats']=fit['n_beats']
    out['measured_plausible']=plausible;out['predicted_plausible']=pred>=200
    out['predicted_plausible']&=pred<=700;out['analysis_eligible']=out.measured_plausible&out.predicted_plausible
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--measurements',type=Path,default=Path('revision_work/cache/edb_measurements_57.parquet'))
    ap.add_argument('--data-dir',type=Path,default=Path('edb/edb/1.0.0'));ap.add_argument('--out',type=Path,default=Path('revision_work/analysis/edb_residuals_revised.parquet'))
    args=ap.parse_args();con=duckdb.connect();pairs=con.execute(f"select distinct record,lead from read_parquet('{args.measurements}') order by 1,2").fetchall()
    if args.out.exists():args.out.unlink()
    writer=None
    try:
        for record,lead in pairs:
            df=con.execute(f"select * from read_parquet('{args.measurements}') where record=? and lead=? order by sample",[record,lead]).fetchdf()
            out=process(df,record,int(lead),args.data_dir)
            if out is None:continue
            table=pa.Table.from_pandas(out,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(args.out,table.schema,compression='zstd')
            writer.write_table(table)
    finally:
        if writer:writer.close()
        con.close()
    print('saved',args.out)


if __name__=='__main__':main()
