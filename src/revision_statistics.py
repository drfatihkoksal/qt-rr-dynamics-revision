"""Hierarchical reviewer-required inference for revised LTST DB analysis.

Produces distinct beat-, episode-, and subject-level estimands. Beat-level
cluster-robust WLS is computed from subject-level sufficient statistics so the
multi-gigabyte CSV never needs to be loaded into memory.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf


CONTRASTS = {
    "ischemic_vs_hr": ("ischemic", "rate_related"),
    "ischemic_vs_baseline": ("ischemic", "matched_baseline"),
    "hr_vs_baseline": ("rate_related", "matched_baseline"),
}


def _source(path: Path) -> str:
    return str(path).replace("'", "''")


def _scan(path: Path) -> str:
    src = _source(path)
    return (f"read_parquet('{src}')" if path.suffix == ".parquet"
            else f"read_csv_auto('{src}', header=true)")


def beat_cluster_wls(path: Path, outcome: str, exposed: str, reference: str,
                     weighted: bool) -> dict:
    """Binary WLS with CR1 sandwich clustered by unique LTST subject."""
    con = duckdb.connect()
    scan = _scan(path)
    weight = "1.0/(qt_sigma_ms*qt_sigma_ms)" if weighted else "1.0"
    # Matched baseline is episode-specific. Restrict it to the episode kind in
    # the requested contrast by joining on record/lead/episode_id.
    if reference == "matched_baseline":
        eligible = f"""WITH episode_keys AS (
          SELECT DISTINCT record, lead, episode_id FROM {scan}
          WHERE episode_type='{exposed}' AND episode_id>=0 AND analysis_eligible
        ), d AS (
          SELECT r.*
          FROM {scan} r
          JOIN episode_keys k USING(record,lead,episode_id)
          WHERE r.episode_type IN ('{exposed}','matched_baseline') AND r.analysis_eligible
        )"""
    else:
        eligible = f"""WITH d AS (
          SELECT *
          FROM {scan}
          WHERE episode_type IN ('{exposed}','{reference}') AND analysis_eligible
        )"""
    grouped = con.execute(eligible + f"""
        SELECT subject_id,
          sum({weight}) sw,
          sum(({weight})*({outcome})) swy,
          sum(({weight})*(episode_type='{exposed}')::INT) swx,
          sum(({weight})*(episode_type='{exposed}')::INT*({outcome})) swxy,
          count(*) n
        FROM d GROUP BY subject_id ORDER BY subject_id
    """).fetchdf()
    con.close()
    sw, swx = grouped.sw.sum(), grouped.swx.sum()
    xtwx = np.array([[sw, swx], [swx, swx]], dtype=float)
    xtwy = np.array([grouped.swy.sum(), grouped.swxy.sum()], dtype=float)
    beta = np.linalg.solve(xtwx, xtwy)
    # Cluster score X'W(y-Xb) from sufficient statistics.
    s0 = grouped.swy - beta[0] * grouped.sw - beta[1] * grouped.swx
    s1 = grouped.swxy - beta[0] * grouped.swx - beta[1] * grouped.swx
    scores = np.column_stack([s0, s1])
    bread = np.linalg.inv(xtwx)
    meat = scores.T @ scores
    g, n, k = len(grouped), int(grouped.n.sum()), 2
    cr1 = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 else np.nan
    vcov = cr1 * bread @ meat @ bread
    se = float(np.sqrt(vcov[1, 1]))
    tval = float(beta[1] / se)
    p = float(2 * stats.t.sf(abs(tval), df=g - 1))
    crit = stats.t.ppf(0.975, g - 1)
    return {"analysis_level": "beat", "model": "cluster_robust_wls",
            "weighting": "inverse_qt_variance" if weighted else "unweighted",
            "outcome": outcome, "exposed": exposed, "reference": reference,
            "effect_ms": beta[1], "ci_low_ms": beta[1] - crit * se,
            "ci_high_ms": beta[1] + crit * se, "p_value": p,
            "independent_subjects": g, "observations": n,
            "cluster_correction": "CR1; t reference with G-1 df"}


def episode_summaries(path: Path) -> pd.DataFrame:
    con = duckdb.connect()
    scan = _scan(path)
    df = con.execute(f"""
      SELECT record, subject_id, lead,
        episode_type, episode_id, count(*) retained_beats,
        min(sample) first_sample, max(sample) last_sample,
        (max(sample)-min(sample))/250.0 retained_span_s,
        avg(abs_resid_ms) mean_abs_resid_ms,
        median(abs_resid_ms) median_abs_resid_ms,
        avg(resid_ms) mean_signed_resid_ms,
        median(resid_ms) median_signed_resid_ms,
        avg(rr_ms) mean_rr_ms, median(rr_ms) median_rr_ms,
        avg(rr_smoothed_ms) mean_rr_smoothed_ms,
        median(rr_smoothed_ms) median_rr_smoothed_ms,
        avg(drr_dt_ms_per_s) mean_drr_dt_ms_per_s,
        median(drr_dt_ms_per_s) median_drr_dt_ms_per_s,
        avg(dhr_dt_bpm_per_s) mean_dhr_dt_bpm_per_s,
        median(dhr_dt_bpm_per_s) median_dhr_dt_bpm_per_s,
        avg(qt_sigma_ms) mean_qt_sigma_ms,
        median(qt_sigma_ms) median_qt_sigma_ms,
        any_value(tau_s) tau_s
      FROM {scan}
      WHERE episode_type IS NOT NULL AND episode_id>=0 AND analysis_eligible
      GROUP BY ALL ORDER BY record,lead,episode_id,episode_type
    """).fetchdf()
    con.close()
    return df


def paired_episode_effects(ep: pd.DataFrame) -> pd.DataFrame:
    event = ep[ep.episode_type.isin(["ischemic", "rate_related"])].copy()
    base = ep[ep.episode_type == "matched_baseline"].copy()
    keys = ["record", "subject_id", "lead", "episode_id"]
    cols = ["first_sample", "last_sample",
            "mean_abs_resid_ms", "median_abs_resid_ms",
            "mean_signed_resid_ms", "median_signed_resid_ms",
            "mean_rr_ms", "median_rr_ms", "mean_rr_smoothed_ms",
            "median_rr_smoothed_ms", "mean_qt_sigma_ms", "median_qt_sigma_ms"]
    # Optional dynamic-rate columns are present in the revised output.
    for col in ("mean_dhr_dt_bpm_per_s", "median_dhr_dt_bpm_per_s",
                "mean_drr_dt_ms_per_s", "median_drr_dt_ms_per_s"):
        if col in ep.columns:
            cols.append(col)
    merged = event.merge(base[keys + cols], on=keys, suffixes=("_episode", "_baseline"),
                         validate="one_to_one")
    for col in [x for x in cols if "resid" in x]:
        merged[f"delta_{col}"] = merged[f"{col}_episode"] - merged[f"{col}_baseline"]
    return merged


def subject_bootstrap(values: pd.DataFrame, value: str, seed: int = 20260719,
                      n_boot: int = 10000) -> tuple[float, float, float, float]:
    by_subject = values.groupby("subject_id", as_index=False)[value].mean()
    arr = by_subject[value].to_numpy(float)
    rng = np.random.default_rng(seed)
    boot = np.mean(rng.choice(arr, size=(n_boot, len(arr)), replace=True), axis=1)
    estimate = float(arr.mean())
    lo, hi = np.quantile(boot, [0.025, 0.975])
    # Sign-flip randomization at the independent-subject level.
    signs = rng.choice((-1, 1), size=(n_boot, len(arr)))
    null = np.mean(signs * arr, axis=1)
    p = float((np.sum(np.abs(null) >= abs(estimate)) + 1) / (n_boot + 1))
    return estimate, float(lo), float(hi), p


def partially_paired_subject_bootstrap(
        subject_label: pd.DataFrame, value: str,
        ischemic_col: str = "ischemic", hr_col: str = "rate_related",
        seed: int = 20260721, n_boot: int = 20000
) -> tuple[float, float, float, float, int, int, int, int]:
    """Equal-label-mean contrast with unique-subject cluster bootstrap.

    Rows are indexed by unique subject and columns contain label-specific
    summaries. Resampling a subject retains both values when both are present,
    thereby respecting the partially paired design while preserving the
    estimand (mean ischemic-subject summary minus mean HR-subject summary).
    The two-sided p value is the bootstrap tail probability around zero.
    """
    wide = subject_label[[ischemic_col, hr_col]].copy()
    wide = wide.loc[wide.notna().any(axis=1)]
    a = wide[ischemic_col].to_numpy(float)
    b = wide[hr_col].to_numpy(float)
    estimate = float(np.nanmean(a) - np.nanmean(b))
    rng = np.random.default_rng(seed)
    n = len(wide)
    draws = []
    while sum(len(x) for x in draws) < n_boot:
        batch = min(2000, n_boot - sum(len(x) for x in draws) + 200)
        idx = rng.integers(0, n, size=(batch, n))
        aa, bb = a[idx], b[idx]
        na, nb = np.isfinite(aa).sum(axis=1), np.isfinite(bb).sum(axis=1)
        vals = np.full(batch, np.nan)
        valid = (na > 0) & (nb > 0)
        vals[valid] = (np.nansum(aa[valid], axis=1) / na[valid] -
                       np.nansum(bb[valid], axis=1) / nb[valid])
        draws.append(vals[np.isfinite(vals)])
    boot = np.concatenate(draws)[:n_boot]
    lo, hi = np.quantile(boot, [0.025, 0.975])
    p = float(min(1.0, 2 * min(
        (np.count_nonzero(boot <= 0) + 1) / (n_boot + 1),
        (np.count_nonzero(boot >= 0) + 1) / (n_boot + 1))))
    return (estimate, float(lo), float(hi), p, n,
            int(np.isfinite(a).sum()), int(np.isfinite(b).sum()),
            int((np.isfinite(a) & np.isfinite(b)).sum()))


def hierarchical_results(ep: pd.DataFrame, effects: pd.DataFrame) -> list[dict]:
    rows = []
    for kind, name in (("ischemic", "ischemic_vs_baseline"),
                       ("rate_related", "hr_vs_baseline")):
        sub = effects[effects.episode_type == kind]
        for base_col in ("mean_abs_resid_ms", "median_abs_resid_ms",
                         "mean_signed_resid_ms", "median_signed_resid_ms"):
            val = f"delta_{base_col}"
            fit = smf.ols(f"{val} ~ 1", data=sub).fit(use_t=True,
                cov_type="cluster", cov_kwds={"groups": sub.subject_id,
                                               "use_correction": True})
            ci = fit.conf_int().loc["Intercept"]
            rows.append({"contrast": name, "analysis_level": "episode",
                         "model": "episode_delta_clustered_by_subject",
                         "weighting": "equal_episode", "outcome": base_col,
                         "effect_ms": fit.params["Intercept"],
                         "ci_low_ms": ci.iloc[0], "ci_high_ms": ci.iloc[1],
                         "p_value": fit.pvalues["Intercept"],
                         "independent_subjects": sub.subject_id.nunique(),
                         "episodes": len(sub)})
            est, lo, hi, p = subject_bootstrap(sub, val)
            rows.append({"contrast": name, "analysis_level": "subject_equal_weight",
                         "model": "subject_mean_with_subject_bootstrap",
                         "weighting": "equal_subject", "outcome": base_col,
                         "effect_ms": est, "ci_low_ms": lo, "ci_high_ms": hi,
                         "p_value": p, "independent_subjects": sub.subject_id.nunique(),
                         "episodes": len(sub)})
    # Direct label contrast: each subject's episode mean; between-subject by
    # default, plus a limited within-subject paired estimand among both-label subjects.
    event = ep[ep.episode_type.isin(["ischemic", "rate_related"])]
    for col in ("mean_abs_resid_ms", "median_abs_resid_ms",
                "mean_signed_resid_ms", "median_signed_resid_ms"):
        direct = event.copy()
        direct["ischemic_indicator"] = (direct.episode_type == "ischemic").astype(int)
        fit = smf.ols(f"{col} ~ ischemic_indicator", direct).fit(use_t=True,
            cov_type="cluster", cov_kwds={"groups": direct.subject_id,
                                           "use_correction": True})
        ci = fit.conf_int().loc["ischemic_indicator"]
        rows.append({"contrast": "ischemic_vs_hr", "analysis_level": "episode",
                     "model": "episode_ols_clustered_by_subject", "weighting": "equal_episode",
                     "outcome": col, "effect_ms": fit.params["ischemic_indicator"],
                     "ci_low_ms": ci.iloc[0], "ci_high_ms": ci.iloc[1],
                     "p_value": fit.pvalues["ischemic_indicator"],
                     "independent_subjects": direct.subject_id.nunique(),
                     "episodes": len(direct)})
        sm = event.groupby(["subject_id", "episode_type"])[col].mean().unstack()
        est, lo, hi, p, n_unique, n_isc, n_hr, n_both = (
            partially_paired_subject_bootstrap(sm, col))
        rows.append({"contrast": "ischemic_vs_hr", "analysis_level": "subject_equal_weight",
                     "model": "partially_paired_unique_subject_bootstrap",
                     "weighting": "equal_subject_within_label",
                     "outcome": col, "effect_ms": est, "ci_low_ms": lo,
                     "ci_high_ms": hi, "p_value": p,
                     "independent_subjects": n_unique,
                     "ischemic_subjects": n_isc, "hr_subjects": n_hr,
                     "overlapping_subjects": n_both,
                     "cluster_correction": "20,000 unique-subject bootstrap draws; both labels retained"})
        both = sm.dropna()
        diff = (both.ischemic - both.rate_related).rename("difference").reset_index()
        est, lo, hi, p = subject_bootstrap(diff, "difference", seed=20260720)
        rows.append({"contrast": "ischemic_vs_hr", "analysis_level": "within_subject",
                     "model": "paired_subject_mean_with_bootstrap", "weighting": "equal_subject",
                     "outcome": col, "effect_ms": est, "ci_low_ms": lo,
                     "ci_high_ms": hi, "p_value": p,
                     "independent_subjects": len(both)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--residuals", type=Path,
                    default=Path("revision_work/analysis/ltstdb_residuals_revised.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("revision_work/analysis"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ep = episode_summaries(args.residuals)
    if not (ep.episode_type == "matched_baseline").any():
        raise RuntimeError("No episode-specific matched baselines; revised pipeline must be rerun")
    effects = paired_episode_effects(ep)
    ep.to_csv(args.out_dir / "episode_level_results.csv", index=False)
    effects.to_csv(args.out_dir / "episode_matched_effects.csv", index=False)
    direction = (ep[ep.episode_type.isin(["ischemic", "rate_related"])]
                 .assign(direction=lambda d: np.select(
                     [d.median_signed_resid_ms > 0, d.median_signed_resid_ms < 0],
                     ["positive", "negative"], default="zero"))
                 .groupby(["episode_type", "direction"], as_index=False)
                 .agg(episodes=("record", "size"), subjects=("subject_id", "nunique")))
    totals = direction.groupby("episode_type").episodes.transform("sum")
    direction["proportion"] = direction.episodes / totals
    direction.to_csv(args.out_dir / "signed_residual_direction.csv", index=False)
    rows = hierarchical_results(ep, effects)
    for name, (exposed, reference) in CONTRASTS.items():
        for outcome in ("abs_resid_ms", "resid_ms"):
            for weighted in (False, True):
                row = beat_cluster_wls(args.residuals, outcome, exposed, reference, weighted)
                row["contrast"] = name
                rows.append(row)
    out = pd.DataFrame(rows)
    out.insert(0, "analysis_id", [f"LTST_{i+1:03d}" for i in range(len(out))])
    out["multiplicity_family"] = "exploratory_or_sensitivity"
    confirm = ((out.analysis_level == "subject_equal_weight") &
               (out.outcome == "mean_abs_resid_ms") &
               out.contrast.isin(CONTRASTS))
    out.loc[confirm, "multiplicity_family"] = "three_primary_absolute_contrasts"
    out["p_adjusted"] = np.nan
    if confirm.sum():
        from statsmodels.stats.multitest import multipletests
        out.loc[confirm, "p_adjusted"] = multipletests(
            out.loc[confirm, "p_value"].astype(float), method="fdr_bh")[1]
    out.to_csv(args.out_dir / "hierarchical_effects.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
