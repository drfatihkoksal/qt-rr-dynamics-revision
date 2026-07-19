"""Reviewer-required cohort, identifier, and episode-overlap audit.

All outputs are derived from immutable database annotations and the frozen
beat-level pipeline output.  LTST DB subject identifiers follow the official
naming rule: records from one subject differ only in the final digit.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import wfdb

from episodes import parse_ltstdb_episodes


def read_records(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text().splitlines() if x.strip()]


def subject_id(record: str) -> str:
    if not record or not record[-1].isdigit():
        raise ValueError(f"Unexpected LTST DB record identifier: {record!r}")
    return record[:-1]


def header_n_leads(header: Path) -> int | None:
    if not header.exists():
        return None
    fields = header.read_text(errors="replace").splitlines()[0].split()
    return int(fields[1])


def raw_episode_table(data_dir: Path, records: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for record in records:
        base = data_dir / record
        if not (base.with_suffix(".stb")).exists():
            continue
        try:
            # LTST DB is uniformly sampled at 250 Hz. Annotation parsing does
            # not require the large signal file or header, allowing the raw
            # pre-exclusion audit to cover all catalogued records.
            fs = 250.0
            episodes, _ = parse_ltstdb_episodes(str(base), protocol="stb")
            beats = wfdb.rdann(str(base), "atr")
            beat_samples = beats.sample
            normal_samples = beats.sample[np.array([s in {"N", ".", "•"}
                                                     for s in beats.symbol])]
        except Exception as exc:  # retained explicitly in audit output
            rows.append({"record": record, "subject_id": subject_id(record),
                         "lead": pd.NA, "episode_type": "parse_failure",
                         "episode_id_raw": pd.NA, "onset_sample": pd.NA,
                         "offset_sample": pd.NA, "duration_s": pd.NA,
                         "parse_error": repr(exc)})
            continue
        for eid, ep in enumerate(episodes):
            rows.append({"record": record, "subject_id": subject_id(record),
                         "lead": ep["lead"], "episode_type": ep["kind"],
                         "episode_id_raw": eid, "onset_sample": ep["onset"],
                         "offset_sample": ep["offset"],
                         "duration_s": (ep["offset"] - ep["onset"]) / fs,
                         "annotated_beats_raw": int(np.sum(
                             (beat_samples >= ep["onset"]) & (beat_samples <= ep["offset"]))),
                         "normal_annotated_beats_raw": int(np.sum(
                             (normal_samples >= ep["onset"]) & (normal_samples <= ep["offset"]))),
                         "parse_error": ""})
    return pd.DataFrame(rows)


def retained_tables(residual_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect()
    source = str(residual_csv).replace("'", "''")
    scan = (f"read_parquet('{source}')" if residual_csv.suffix == ".parquet"
            else f"read_csv_auto('{source}', header=true)")
    episodes = con.execute(f"""
        SELECT record, left(record, length(record)-1) AS subject_id, lead,
               episode_type, episode_id,
               min(sample) AS first_retained_sample,
               max(sample) AS last_retained_sample,
               count(*) AS retained_beats,
               (max(sample)-min(sample))/250.0 AS retained_span_s,
               median(abs_resid_ms) AS median_abs_resid_ms,
               avg(abs_resid_ms) AS mean_abs_resid_ms,
               median(resid_ms) AS median_signed_resid_ms,
               avg(resid_ms) AS mean_signed_resid_ms,
               median(rr_ms) AS median_rr_ms,
               median(rr_smoothed_ms) AS median_rr_smoothed_ms,
               median(qt_sigma_ms) AS median_qt_sigma_ms,
               any_value(tau_s) AS tau_s
        FROM {scan}
        WHERE episode_type IN ('ischemic','rate_related') AND episode_id >= 0
          AND analysis_eligible
        GROUP BY ALL
        ORDER BY record, lead, episode_type, episode_id
    """).fetchdf()
    record_leads = con.execute(f"""
        SELECT record, left(record, length(record)-1) AS subject_id, lead,
               count(*) AS retained_clean_normal_beats,
               sum(episode_type='ischemic') AS retained_ischemic_beats,
               sum(episode_type='rate_related') AS retained_hr_beats,
               sum(episode_type='matched_baseline') AS retained_baseline_beats,
               any_value(tau_s) AS tau_s
        FROM {scan}
        WHERE analysis_eligible
        GROUP BY ALL ORDER BY record, lead
    """).fetchdf()
    con.close()
    return episodes, record_leads


def overlap_table(raw: pd.DataFrame, retained_ep: pd.DataFrame,
                  retained_rl: pd.DataFrame, subjects: list[str]) -> pd.DataFrame:
    rows = []
    for sid in subjects:
        rr = raw[raw.subject_id == sid]
        ee = retained_ep[retained_ep.subject_id == sid]
        rl = retained_rl[retained_rl.subject_id == sid]
        raw_i = rr[rr.episode_type == "ischemic"]
        raw_h = rr[rr.episode_type == "rate_related"]
        ret_i = ee[ee.episode_type == "ischemic"]
        ret_h = ee[ee.episode_type == "rate_related"]
        has_i, has_h = len(ret_i) > 0, len(ret_h) > 0
        group = ("both" if has_i and has_h else "ischemic_only" if has_i else
                 "heart_rate_related_only" if has_h else "neither_retained")
        rows.append({
            "subject_id": sid, "subject_group": group,
            "records_available": rr.record.nunique(),
            "records_processed": rl.record.nunique(),
            "record_leads_processed": len(rl),
            "raw_ischemic_episodes": len(raw_i),
            "raw_hr_episodes": len(raw_h),
            "raw_ischemic_duration_s": raw_i.duration_s.sum(),
            "raw_hr_duration_s": raw_h.duration_s.sum(),
            "raw_ischemic_normal_beats": raw_i.normal_annotated_beats_raw.sum(),
            "raw_hr_normal_beats": raw_h.normal_annotated_beats_raw.sum(),
            "retained_ischemic_episodes": len(ret_i),
            "retained_hr_episodes": len(ret_h),
            "retained_ischemic_span_s": ret_i.retained_span_s.sum(),
            "retained_hr_span_s": ret_h.retained_span_s.sum(),
            "retained_ischemic_beats": int(ret_i.retained_beats.sum()),
            "retained_hr_beats": int(ret_h.retained_beats.sum()),
            "has_any_raw_ischemic_episode": len(raw_i) > 0,
            "has_any_retained_ischemic_episode": has_i,
        })
    return pd.DataFrame(rows)


def cohort_flow(records: list[str], data_dir: Path, retained_rl: pd.DataFrame,
                retained_ep: pd.DataFrame) -> pd.DataFrame:
    available_signal = [r for r in records if (data_dir / f"{r}.dat").exists()]
    available_headers = [r for r in records if (data_dir / f"{r}.hea").exists()]
    processed = set(retained_rl.record)
    with_episode = set(retained_ep.record)
    rows = [
        ("ltstdb", "database_catalog", "all_catalogued", "records", len(records)),
        ("ltstdb", "local_source", "signal_and_header_available", "records",
         len(set(available_signal) & set(available_headers))),
        ("ltstdb", "pipeline", "successfully_processed", "records", len(processed)),
        ("ltstdb", "primary_analysis", "eligible_retained_episode", "records",
         len(with_episode)),
        ("ltstdb", "pipeline", "successfully_processed", "unique_subjects",
         len({subject_id(r) for r in processed})),
        ("ltstdb", "primary_analysis", "eligible_retained_episode", "unique_subjects",
         len({subject_id(r) for r in with_episode})),
        ("ltstdb", "pipeline", "successfully_processed", "record_leads",
         len(retained_rl)),
        ("ltstdb", "primary_analysis", "eligible_retained_episode", "episodes",
         len(retained_ep)),
    ]
    return pd.DataFrame(rows, columns=["dataset", "stage", "reason_code", "unit", "n"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ltstdb-dir", type=Path, default=Path("ltstdb/ltstdb/1.0.0"))
    ap.add_argument("--residuals", type=Path, default=Path("results/ltstdb_residuals.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("revision_work/audit"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records = read_records(args.ltstdb_dir / "RECORDS")
    map_rows = [{"record": r, "subject_id": subject_id(r),
                 "header_available": (args.ltstdb_dir / f"{r}.hea").exists(),
                 "signal_available": (args.ltstdb_dir / f"{r}.dat").exists(),
                 "n_leads": header_n_leads(args.ltstdb_dir / f"{r}.hea")}
                for r in records]
    subject_map = pd.DataFrame(map_rows)
    raw = raw_episode_table(args.ltstdb_dir, records)
    retained_ep, retained_rl = retained_tables(args.residuals)
    overlap = overlap_table(raw, retained_ep, retained_rl,
                            sorted(subject_map.subject_id.unique()))
    flow = cohort_flow(records, args.ltstdb_dir, retained_rl, retained_ep)

    subject_map.to_csv(args.out_dir / "ltstdb_subject_map.csv", index=False,
                       quoting=csv.QUOTE_MINIMAL)
    raw.to_csv(args.out_dir / "ltstdb_raw_episodes_stb.csv", index=False)
    retained_ep.to_csv(args.out_dir / "episode_level_results.csv", index=False)
    retained_rl.to_csv(args.out_dir / "record_lead_audit.csv", index=False)
    overlap.to_csv(args.out_dir / "subject_episode_overlap.csv", index=False)
    summary_cols = ["records_processed", "record_leads_processed",
                    "raw_ischemic_episodes", "raw_hr_episodes",
                    "raw_ischemic_duration_s", "raw_hr_duration_s",
                    "retained_ischemic_episodes", "retained_hr_episodes",
                    "retained_ischemic_span_s", "retained_hr_span_s",
                    "retained_ischemic_beats", "retained_hr_beats"]
    group_summary = overlap.groupby("subject_group", as_index=False).agg(
        unique_subjects=("subject_id", "size"),
        **{col: (col, "sum") for col in summary_cols})
    group_summary.to_csv(args.out_dir / "subject_overlap_summary.csv", index=False)
    hr = overlap[overlap.retained_hr_episodes > 0]
    hr_overlap = hr[hr.has_any_raw_ischemic_episode]
    fractions = []
    for unit, col in (("subjects", None), ("episodes", "retained_hr_episodes"),
                      ("episode_span_s", "retained_hr_span_s"),
                      ("retained_beats", "retained_hr_beats")):
        numerator = len(hr_overlap) if col is None else hr_overlap[col].sum()
        denominator = len(hr) if col is None else hr[col].sum()
        fractions.append({"definition": "retained_hr_contributors_with_any_raw_ischemic_episode",
                          "unit": unit, "numerator": numerator,
                          "denominator": denominator,
                          "proportion": numerator / denominator})
    pd.DataFrame(fractions).to_csv(args.out_dir / "hr_overlap_fractions.csv", index=False)
    flow.to_csv(args.out_dir / "cohort_flow.csv", index=False)
    print(flow.to_string(index=False))
    print("\nSubject groups after primary exclusions:")
    print(overlap.groupby("subject_group").size().to_string())


if __name__ == "__main__":
    main()
