"""Beat/lead exclusion audit with mutually interpretable reason counts."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import wfdb

from episodes import parse_ltstdb_episodes


NORMAL={"N",".","•"}


def inside_intervals(samples, intervals):
    out=np.zeros(len(samples),dtype=bool)
    for start,stop in intervals:
        out |= (samples>=start)&(samples<stop)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",type=Path,default=Path("revision_work/data/ltstdb_verified"))
    ap.add_argument("--measurements",type=Path,default=Path("revision_work/cache/ltstdb_measurements_86.parquet"))
    ap.add_argument("--revised",type=Path,default=Path("revision_work/analysis/ltstdb_residuals_revised.parquet"))
    ap.add_argument("--out",type=Path,default=Path("revision_work/audit/exclusion_audit.csv"))
    args=ap.parse_args(); con=duckdb.connect()
    records=[x.strip() for x in (args.data_dir/'RECORDS').read_text().splitlines() if x.strip()]
    rows=[]
    for record in records:
        header=wfdb.rdheader(str(args.data_dir/record)); sig_len=header.sig_len
        ann=wfdb.rdann(str(args.data_dir/record),'atr')
        all_samples=np.asarray(ann.sample); symbols=np.asarray(ann.symbol)
        normal=all_samples[np.array([x in NORMAL for x in symbols])]
        _,qbad=parse_ltstdb_episodes(str(args.data_dir/record),'stb')
        for lead in range(header.n_sig):
            measured=con.execute(f"SELECT sample,qt_ms FROM read_parquet('{args.measurements}') WHERE record=? AND lead=? ORDER BY sample",[record,lead]).fetchdf()
            edge=(normal<200)|(normal+300>sig_len)
            bad=inside_intervals(normal,qbad.get(lead,[]))
            eligible=normal[~edge&~bad]
            measured_set=set(measured['sample'].astype(int))
            no_delineation=sum(int(x) not in measured_set for x in eligible)
            revised=con.execute(f"""SELECT count(*) n,
              sum(NOT measured_plausible) measured_implausible,
              sum(measured_plausible AND NOT predicted_plausible) predicted_implausible,
              sum(analysis_eligible) analysis_eligible
              FROM read_parquet('{args.revised}') WHERE record=? AND lead=?""",[record,lead]).fetchone()
            rows.append({"record":record,"subject_id":record[:-1],"lead":lead,
                         "all_annotated_beats":len(all_samples),"normal_annotated_beats":len(normal),
                         "edge_window_exclusions":int(edge.sum()),
                         "signal_quality_exclusions":int((bad&~edge).sum()),
                         "eligible_normal_clean_window_beats":len(eligible),
                         "no_valid_delineation_exclusions":int(no_delineation),
                         "retained_measurements":len(measured),
                         "measured_qt_plausibility_exclusions":int(revised[1] or 0),
                         "predicted_qt_plausibility_exclusions":int(revised[2] or 0),
                         "analysis_eligible_beats":int(revised[3] or 0)})
    con.close(); out=pd.DataFrame(rows); out.to_csv(args.out,index=False)
    print(out.drop(columns=['record','subject_id','lead']).sum().to_string())


if __name__=='__main__':main()
