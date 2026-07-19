"""Individualized, hysteresis-corrected QT-RR baseline per record.

Fits log(QT) ~ log(RR_smoothed) on non-episode, quality-clean beats, where
RR_smoothed is a variable-time-step exponentially-weighted moving average of
preceding RR intervals with per-record time constant selected by block
cross-validation (maximizing held-out R^2), rather than a fixed literature
constant -- per concept.md's "individualized" framing.
"""
import numpy as np
import pandas as pd

TAU_GRID_S = [10, 15, 20, 30, 45, 60, 90, 120, 150, 180, 240, 300]
N_CV_BLOCKS = 5


def rr_smoothed(rr_ms, tau_s):
    """Variable-time-step EWMA of RR history. rr_ms: array (beat's own RR to
    the previous beat, ms; NaN for the first beat). Uses each beat's own RR
    as its local time step."""
    tau_ms = tau_s * 1000.0
    out = np.full(len(rr_ms), np.nan)
    valid = ~np.isnan(rr_ms)
    if valid.sum() == 0:
        return out
    first = np.argmax(valid)
    cur = rr_ms[first]
    out[first] = cur
    for i in range(first + 1, len(rr_ms)):
        if np.isnan(rr_ms[i]):
            out[i] = cur
            continue
        dt = rr_ms[i]
        alpha = 1 - np.exp(-dt / tau_ms)
        cur = cur + alpha * (rr_ms[i] - cur)
        out[i] = cur
    return out


def _fit_ols(x, y):
    # Closed-form simple OLS is exactly the two-parameter model required here
    # and avoids repeatedly invoking a general SVD solver on ~100k beats in
    # every cross-validation fold.
    x_mean = np.mean(x); y_mean = np.mean(y)
    x_centered = x - x_mean; y_centered = y - y_mean
    sxx = np.dot(x_centered, x_centered)
    slope = np.dot(x_centered, y_centered) / sxx if sxx > 0 else 0.0
    intercept = y_mean - slope * x_mean
    coef = np.array([intercept, slope])
    pred = intercept + slope * x
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return coef, r2


def select_tau_and_fit(df_clean, taus=TAU_GRID_S, n_blocks=N_CV_BLOCKS, min_beats=200):
    """df_clean: DataFrame sorted by sample, restricted to non-episode,
    quality-clean, presence-valid beats for ONE record (one lead's worth).
    Returns dict(tau, coef=(intercept,slope), cv_r2, n_beats) or None if too
    few beats.
    """
    n = len(df_clean)
    if n < min_beats:
        return None

    rr_full = df_clean["rr_ms"].values
    qt_full = df_clean["qt_ms"].values

    block_ids = (np.arange(n) * n_blocks // n)

    best_tau, best_cv_r2 = None, -np.inf
    for tau in taus:
        rrs = rr_smoothed(rr_full, tau)
        valid = ~np.isnan(rrs) & ~np.isnan(qt_full) & (rrs > 0) & (qt_full > 0)
        if valid.sum() < min_beats:
            continue
        x_all = np.log(rrs[valid]); y_all = np.log(qt_full[valid])
        blocks_v = block_ids[valid]
        fold_r2 = []
        for b in range(n_blocks):
            test_mask = blocks_v == b
            train_mask = ~test_mask
            if test_mask.sum() < 10 or train_mask.sum() < 20:
                continue
            coef, _ = _fit_ols(x_all[train_mask], y_all[train_mask])
            pred_test = coef[0] + coef[1] * x_all[test_mask]
            ss_res = np.sum((y_all[test_mask] - pred_test) ** 2)
            ss_tot = np.sum((y_all[test_mask] - y_all[test_mask].mean()) ** 2)
            if ss_tot > 0:
                fold_r2.append(1 - ss_res / ss_tot)
        if not fold_r2:
            continue
        mean_r2 = np.mean(fold_r2)
        if mean_r2 > best_cv_r2:
            best_cv_r2 = mean_r2
            best_tau = tau

    if best_tau is None:
        return None

    rrs = rr_smoothed(rr_full, best_tau)
    valid = ~np.isnan(rrs) & ~np.isnan(qt_full) & (rrs > 0) & (qt_full > 0)
    coef, r2_full = _fit_ols(np.log(rrs[valid]), np.log(qt_full[valid]))
    return dict(tau=best_tau, intercept=coef[0], slope=coef[1],
                cv_r2=best_cv_r2, full_r2=r2_full, n_beats=int(valid.sum()))
