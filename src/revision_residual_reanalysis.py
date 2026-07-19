"""Rebuild LTST DB residuals and matched baselines from frozen beat measures.

The expensive neural-network measurements are reused, while every downstream
quantity affected by the revision (subject mapping, episode filtering,
hysteresis, baseline matching, IDs, rate dynamics, and residuals) is rebuilt.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from baseline_fit import _fit_ols, rr_smoothed
from episodes import parse_ltstdb_episodes
from run_residual_pipeline import assign_matched_baseline, label_episodes


PRIMARY_GRID = [10, 15, 20, 30, 45, 60, 90, 120, 150, 180, 240, 300]
EXPANDED_GRID = [5, 10, 15, 20, 30, 45, 60, 90, 120, 150, 180, 240, 300, 420, 600]


def fixed_tau_fit(measures: pd.DataFrame, baseline_mask: np.ndarray,
                  tau: float) -> dict | None:
    smoothed = rr_smoothed(measures.rr_ms.to_numpy(), tau)
    qt = measures.qt_ms.to_numpy()
    valid = baseline_mask & np.isfinite(smoothed) & np.isfinite(qt) & (smoothed > 0) & (qt > 0)
    if valid.sum() < 200:
        return None
    coef, r2 = _fit_ols(np.log(smoothed[valid]), np.log(qt[valid]))
    return {"tau": tau, "intercept": coef[0], "slope": coef[1],
            "cv_r2": np.nan, "full_r2": r2, "n_beats": int(valid.sum())}


def select_tau_continuous(measures: pd.DataFrame, baseline_mask: np.ndarray,
                          grid: list[float], n_blocks: int = 5) -> dict | None:
    """Select tau while preserving RR adaptation through excluded episodes."""
    qt = measures.qt_ms.to_numpy()
    rr = measures.rr_ms.to_numpy()
    valid_base = baseline_mask & np.isfinite(qt) & (qt > 0)
    if valid_base.sum() < 200:
        return None
    valid_order = np.cumsum(valid_base) - 1
    block = np.floor(valid_order * n_blocks / valid_base.sum()).astype(int)
    block = np.clip(block, 0, n_blocks - 1)
    best_tau, best_score = None, -np.inf
    for tau in grid:
        smoothed = rr_smoothed(rr, tau)
        valid = valid_base & np.isfinite(smoothed) & (smoothed > 0)
        x = np.log(smoothed[valid]); y = np.log(qt[valid]); b = block[valid]
        scores = []
        for fold in range(n_blocks):
            test = b == fold; train = ~test
            if test.sum() < 10 or train.sum() < 20:
                continue
            coef, _ = _fit_ols(x[train], y[train])
            pred = coef[0] + coef[1] * x[test]
            ss_res = np.sum((y[test] - pred) ** 2)
            ss_tot = np.sum((y[test] - y[test].mean()) ** 2)
            if ss_tot > 0:
                scores.append(1 - ss_res / ss_tot)
        if scores and np.mean(scores) > best_score:
            best_tau, best_score = tau, float(np.mean(scores))
    if best_tau is None:
        return None
    smoothed = rr_smoothed(rr, best_tau)
    valid = valid_base & np.isfinite(smoothed) & (smoothed > 0)
    coef, r2 = _fit_ols(np.log(smoothed[valid]), np.log(qt[valid]))
    return {"tau": best_tau, "intercept": coef[0], "slope": coef[1],
            "cv_r2": best_score, "full_r2": r2, "n_beats": int(valid.sum())}


def process(measures: pd.DataFrame, record: str, lead: int, data_dir: Path,
            protocol: str, tau_mode: str, fixed_tau: float | None = None,
            write_all: bool = False) -> pd.DataFrame | None:
    measures = measures.sort_values("sample").reset_index(drop=True)
    episodes, _ = parse_ltstdb_episodes(str(data_dir / record), protocol=protocol)
    episodes = [x for x in episodes if x["lead"] == lead]
    raw_label, _, _ = label_episodes(len(measures), measures["sample"].to_numpy(),
                                     episodes, 0, 250.0)
    measured_plausible = (measures.qt_ms.between(200, 700) &
                          measures.rr_ms.gt(0) & measures.rr_ms.notna()).to_numpy()
    baseline_mask = (raw_label == None) & measured_plausible  # noqa: E711
    if tau_mode == "fixed":
        fit = fixed_tau_fit(measures, baseline_mask, float(fixed_tau))
    else:
        grid = PRIMARY_GRID if tau_mode == "individualized" else EXPANDED_GRID
        fit = select_tau_continuous(measures, baseline_mask, grid)
    if fit is None:
        return None
    samples = measures["sample"].to_numpy()
    label, episode_id, spans = label_episodes(
        len(measures), samples, episodes, 1.5 * fit["tau"], 250.0)
    matched_label, matched_id = assign_matched_baseline(
        len(measures), samples, label, spans, 250.0)
    final_label = np.where(label != None, label, matched_label)  # noqa: E711
    final_id = np.where(label != None, episode_id, matched_id)  # noqa: E711
    smoothed = rr_smoothed(measures.rr_ms.to_numpy(), fit["tau"])
    pred = np.exp(fit["intercept"] + fit["slope"] * np.log(np.clip(smoothed, 1, None)))
    resid = measures.qt_ms.to_numpy() - pred
    time_s = samples / 250.0
    drr_dt = np.gradient(smoothed, time_s, edge_order=1)
    hr = 60000.0 / np.clip(smoothed, 1, None)
    dhr_dt = np.gradient(hr, time_s, edge_order=1)
    out = measures.copy()
    out["subject_id"] = record[:-1]
    out["episode_type"] = pd.array(final_label, dtype="string")
    out["episode_id"] = final_id
    out["rr_smoothed_ms"] = smoothed
    out["drr_dt_ms_per_s"] = drr_dt
    out["dhr_dt_bpm_per_s"] = dhr_dt
    out["pred_qt_ms"] = pred
    out["resid_ms"] = resid
    out["abs_resid_ms"] = np.abs(resid)
    out["measured_plausible"] = measured_plausible
    out["predicted_plausible"] = (pred >= 200) & (pred <= 700)
    out["analysis_eligible"] = out.measured_plausible & out.predicted_plausible
    out["tau_s"] = fit["tau"]
    out["baseline_cv_r2"] = fit["cv_r2"]
    out["baseline_full_r2"] = fit["full_r2"]
    out["baseline_n_beats"] = fit["n_beats"]
    out["protocol"] = protocol
    out["tau_mode"] = tau_mode
    if not write_all:
        out = out[out.episode_type.notna() & out.analysis_eligible].copy()
    return out


def summarize_spec(df: pd.DataFrame, spec: str) -> pd.DataFrame:
    kept = df[df.episode_type.notna() & (df.episode_id >= 0) & df.analysis_eligible]
    if kept.empty:
        return pd.DataFrame()
    summary = kept.groupby(
        ["record", "subject_id", "lead", "episode_type", "episode_id"],
        as_index=False).agg(
        retained_beats=("sample", "size"), first_sample=("sample", "min"),
        last_sample=("sample", "max"), mean_abs_resid_ms=("abs_resid_ms", "mean"),
        median_abs_resid_ms=("abs_resid_ms", "median"),
        mean_signed_resid_ms=("resid_ms", "mean"),
        median_signed_resid_ms=("resid_ms", "median"),
        median_rr_smoothed_ms=("rr_smoothed_ms", "median"),
        median_drr_dt_ms_per_s=("drr_dt_ms_per_s", "median"),
        median_dhr_dt_bpm_per_s=("dhr_dt_bpm_per_s", "median"),
        median_qt_sigma_ms=("qt_sigma_ms", "median"), tau_s=("tau_s", "first"),
        baseline_cv_r2=("baseline_cv_r2", "first"))
    summary.insert(0, "specification", spec)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measurements", type=Path,
                    default=Path("revision_work/cache/ltstdb_measurements_86.parquet"))
    ap.add_argument("--data-dir", type=Path,
                    default=Path("revision_work/data/ltstdb_verified"))
    ap.add_argument("--out-dir", type=Path, default=Path("revision_work/analysis"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    pairs = con.execute(f"""SELECT DISTINCT record,lead
      FROM read_parquet('{str(args.measurements)}') ORDER BY record,lead""").fetchall()
    specifications = [("stb_individualized", "stb", "individualized", None)]
    specifications += [(f"stb_fixed_{tau}s", "stb", "fixed", tau)
                       for tau in (30, 60, 120, 180)]
    specifications += [("stb_expanded_grid", "stb", "expanded", None),
                       ("sta_individualized", "sta", "individualized", None),
                       ("stc_individualized", "stc", "individualized", None)]
    all_summaries = []
    writer = None
    primary_path = args.out_dir / "ltstdb_residuals_revised.parquet"
    if primary_path.exists():
        primary_path.unlink()
    try:
        for spec, protocol, mode, tau in specifications:
            print(f"SPEC {spec}", flush=True)
            for record, lead in pairs:
                measures = con.execute(f"""SELECT * FROM read_parquet('{str(args.measurements)}')
                  WHERE record=? AND lead=? ORDER BY sample""", [record, lead]).fetchdf()
                result = process(measures, record, int(lead), args.data_dir,
                                 protocol, mode, tau, write_all=(spec == "stb_individualized"))
                if result is None:
                    continue
                if spec == "stb_individualized":
                    table = pa.Table.from_pandas(result, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(primary_path, table.schema,
                                                  compression="zstd")
                    writer.write_table(table)
                summary = summarize_spec(result, spec)
                if not summary.empty:
                    all_summaries.append(summary)
    finally:
        if writer is not None:
            writer.close()
        con.close()
    pd.concat(all_summaries, ignore_index=True).to_csv(
        args.out_dir / "hysteresis_protocol_episode_summaries.csv", index=False)
    print(f"Saved {primary_path}")


if __name__ == "__main__":
    main()
