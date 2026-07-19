"""Episode-stratified residual statistics, generic over LTST DB / EDB.

For a given pair of strata (e.g. ischemic vs rate_related, or ischemic vs
matched_baseline) computes:
  1. Uncertainty-weighted contrast: WLS on |residual| ~ C(stratum), weights =
     1/qt_sigma_ms^2, cluster-robust SEs by record ("record-lead" unit) --
     the practical implementation of concept.md's "uncertainty-weighted
     mixed-effects contrast" (statsmodels MixedLM has no supported per-
     observation weight argument, so inverse-variance WLS + cluster-robust
     SE is used instead; documented explicitly here and in the manuscript).
  2. Unweighted MixedLM with record-lead random intercept, as a cross-check.
  3. Record-level paired Wilcoxon signed-rank test on per-record median
     |residual| (stratum A vs B), Hodges-Lehmann shift estimate, bootstrap
     percentile CI.
"""
import argparse
import sys
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))

RNG = np.random.default_rng(12345)


def hodges_lehmann(x, y, n_boot=2000):
    diffs = np.array([xi - yi for xi in x for yi in y]) if len(x) * len(y) < 2_000_000 else None
    if diffs is None:
        # subsample for large n to keep this tractable
        xs = RNG.choice(x, size=min(len(x), 2000), replace=False)
        ys = RNG.choice(y, size=min(len(y), 2000), replace=False)
        diffs = np.array([xi - yi for xi in xs for yi in ys])
    hl = np.median(diffs)
    return hl


def bootstrap_ci_paired_diff(paired_diff, n_boot=5000, alpha=0.05):
    n = len(paired_diff)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = RNG.integers(0, n, n)
        boots[i] = np.median(paired_diff[idx])
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi


def wls_cluster_contrast(df, stratum_col, group_a, group_b, value_col="abs_resid_ms",
                          weight_col="qt_sigma_ms", cluster_col="record_lead"):
    sub = df[df[stratum_col].isin([group_a, group_b])].copy()
    sub["group"] = (sub[stratum_col] == group_a).astype(int)  # 1=A, 0=B
    sub["w"] = 1.0 / (sub[weight_col].clip(lower=1e-3) ** 2)
    model = smf.wls(f"{value_col} ~ group", data=sub, weights=sub["w"])
    res = model.fit(cov_type="cluster", cov_kwds={"groups": sub[cluster_col]})
    return res, sub


def mixedlm_crosscheck(df, stratum_col, group_a, group_b, value_col="abs_resid_ms",
                        cluster_col="record_lead"):
    sub = df[df[stratum_col].isin([group_a, group_b])].copy()
    sub["group"] = (sub[stratum_col] == group_a).astype(int)
    try:
        model = smf.mixedlm(f"{value_col} ~ group", data=sub, groups=sub[cluster_col])
        res = model.fit(reml=True)
        return res
    except Exception as e:
        return None


def record_level_paired_test(df, stratum_col, group_a, group_b, value_col="abs_resid_ms",
                              unit_col="record_lead"):
    med_a = df[df[stratum_col] == group_a].groupby(unit_col)[value_col].median()
    med_b = df[df[stratum_col] == group_b].groupby(unit_col)[value_col].median()
    common = med_a.index.intersection(med_b.index)
    a = med_a.loc[common].values
    b = med_b.loc[common].values
    if len(a) < 5:
        return None
    diff = a - b
    try:
        wstat, pval = stats.wilcoxon(a, b)
    except Exception:
        wstat, pval = np.nan, np.nan
    hl = hodges_lehmann(a, b)
    ci_lo, ci_hi = bootstrap_ci_paired_diff(diff)
    return dict(n_units=len(common), wilcoxon_stat=wstat, wilcoxon_p=pval,
                hodges_lehmann_ms=hl, boot_ci_lo=ci_lo, boot_ci_hi=ci_hi,
                mean_diff_ms=diff.mean(), median_diff_ms=np.median(diff))


def run_comparison(df, stratum_col, group_a, group_b, label):
    print(f"\n=== {label}: {group_a} vs {group_b} ===")
    n_a = (df[stratum_col] == group_a).sum()
    n_b = (df[stratum_col] == group_b).sum()
    print(f"n beats: {group_a}={n_a} {group_b}={n_b}")
    if n_a < 20 or n_b < 20:
        print("insufficient data, skipping")
        return None

    wls_res, sub = wls_cluster_contrast(df, stratum_col, group_a, group_b)
    print(wls_res.summary().tables[1])

    mixed_res = mixedlm_crosscheck(df, stratum_col, group_a, group_b)
    if mixed_res is not None:
        print("\nMixedLM cross-check (unweighted):")
        print(mixed_res.summary().tables[1])

    rec_test = record_level_paired_test(df, stratum_col, group_a, group_b)
    if rec_test:
        print(f"\nRecord-level paired Wilcoxon: n_units={rec_test['n_units']} "
              f"p={rec_test['wilcoxon_p']:.4g} HL={rec_test['hodges_lehmann_ms']:.2f}ms "
              f"boot95CI=[{rec_test['boot_ci_lo']:.2f},{rec_test['boot_ci_hi']:.2f}]")

    return dict(
        label=label, group_a=group_a, group_b=group_b, n_a=int(n_a), n_b=int(n_b),
        wls_coef_ms=wls_res.params.get("group", np.nan),
        wls_se=wls_res.bse.get("group", np.nan),
        wls_p=wls_res.pvalues.get("group", np.nan),
        wls_ci_lo=wls_res.conf_int().loc["group", 0] if "group" in wls_res.params.index else np.nan,
        wls_ci_hi=wls_res.conf_int().loc["group", 1] if "group" in wls_res.params.index else np.nan,
        mixedlm_coef_ms=(mixed_res.params.get("group", np.nan) if mixed_res is not None else np.nan),
        mixedlm_p=(mixed_res.pvalues.get("group", np.nan) if mixed_res is not None else np.nan),
        **({f"rectest_{k}": v for k, v in rec_test.items()} if rec_test else {}),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--residuals", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    dfs = [pd.read_csv(p, low_memory=False) for p in args.residuals]
    df = pd.concat(dfs, ignore_index=True)
    df["record_lead"] = df["dataset"].astype(str) + ":" + df["record"].astype(str) + ":L" + df["lead"].astype(str)
    df = df[df.episode_type.notna()].copy()

    # Physiological plausibility filter: a transiently exploding RR_smoothed
    # (e.g. one missed/doubled beat under a short tau) can send the log-log
    # extrapolation to nonsensical predicted-QT values with huge leverage on
    # mean-based statistics. Drop the (tiny, <0.02%) fraction of beats where
    # measured or predicted QT falls outside the physiologically possible
    # human QT range before any statistical test.
    n_before = len(df)
    plausible = df.qt_ms.between(200, 700) & df.pred_qt_ms.between(200, 700)
    df = df[plausible].copy()
    print(f"physiological-plausibility filter: dropped {n_before - len(df)} / {n_before} beats "
          f"({(n_before - len(df)) / n_before:.4%})")

    print(f"total analyzable beats: {len(df)} across {df.record_lead.nunique()} record-leads")
    print(df.groupby(["dataset", "episode_type"]).size())

    results = []

    has_ltst = "rate_related" in df.episode_type.unique()
    if has_ltst:
        r = run_comparison(df[df.dataset == "ltstdb"], "episode_type", "ischemic", "rate_related",
                            "PRIMARY: ischemic vs rate-related (LTST DB)")
        if r: results.append(r)

    if "matched_baseline" in df.episode_type.unique():
        r = run_comparison(df, "episode_type", "ischemic", "matched_baseline",
                            "SECONDARY 1: ischemic vs matched baseline (pooled)")
        if r: results.append(r)
        if has_ltst:
            r = run_comparison(df[df.dataset == "ltstdb"], "episode_type", "ischemic", "matched_baseline",
                                "SECONDARY 1a: ischemic vs matched baseline (LTST DB only)")
            if r: results.append(r)
        if "edb" in df.dataset.unique():
            r = run_comparison(df[df.dataset == "edb"], "episode_type", "ischemic", "matched_baseline",
                                "SECONDARY 5: EDB replication (ischemic vs matched baseline)")
            if r: results.append(r)

    if has_ltst and "matched_baseline" in df.episode_type.unique():
        r = run_comparison(df[df.dataset == "ltstdb"], "episode_type", "rate_related", "matched_baseline",
                            "EXTRA: rate-related vs matched baseline (LTST DB, should show ~no excess)")
        if r: results.append(r)

    # secondary endpoint 3: uncertainty magnitude vs episode type
    print("\n=== SECONDARY 3: model uncertainty (qt_sigma_ms) by episode type ===")
    unc_summary = df.groupby(["dataset", "episode_type"])["qt_sigma_ms"].agg(["mean", "median", "std", "count"])
    print(unc_summary)
    if has_ltst:
        r = run_comparison(df[df.dataset == "ltstdb"].assign(abs_resid_ms=lambda d: d.qt_sigma_ms),
                            "episode_type", "ischemic", "rate_related",
                            "SECONDARY 3: uncertainty ischemic vs rate-related (LTST DB)")
        if r: results.append(r)

    # exploratory endpoint 2: signed residual direction
    print("\n=== EXPLORATORY 2: signed residual direction by episode type ===")
    signed_summary = df.groupby(["dataset", "episode_type"])["resid_ms"].agg(["mean", "median", "std", "count"])
    print(signed_summary)

    res_df = pd.DataFrame(results)
    if len(res_df):
        from statsmodels.stats.multitest import multipletests
        pvals = res_df["wls_p"].fillna(1.0).values
        rej, p_adj, _, _ = multipletests(pvals, method="fdr_bh")
        res_df["wls_p_fdr"] = p_adj
        res_df["significant_fdr_05"] = rej

    res_df.to_csv(args.out, index=False)
    unc_summary.to_csv(args.out.replace(".csv", "_uncertainty_by_episode.csv"))
    signed_summary.to_csv(args.out.replace(".csv", "_signed_residual_by_episode.csv"))
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
