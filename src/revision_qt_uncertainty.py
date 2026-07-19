"""Direct QT accuracy and covariance-aware predictive-interval validation."""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from coverage import infer_record, load_model


LEVELS = (0.50, 0.68, 0.80, 0.90, 0.95)
QRS_ONSET = 1
T_OFFSET = 3


def collect(paths: list[str], model, device) -> pd.DataFrame:
    rows = []
    for path in paths:
        mu, sigma, truth = infer_record(model, device, path)
        keep = np.isfinite(mu[:, QRS_ONSET]) & np.isfinite(mu[:, T_OFFSET])
        keep &= np.isfinite(sigma[:, QRS_ONSET]) & np.isfinite(sigma[:, T_OFFSET])
        keep &= np.isfinite(truth[:, QRS_ONSET]) & np.isfinite(truth[:, T_OFFSET])
        for beat_idx in np.where(keep)[0]:
            q_err = mu[beat_idx, QRS_ONSET] - truth[beat_idx, QRS_ONSET]
            t_err = mu[beat_idx, T_OFFSET] - truth[beat_idx, T_OFFSET]
            rows.append({
                "record": Path(path).name.split(".")[0], "beat_index": beat_idx,
                "qrs_onset_error_ms": q_err, "t_offset_error_ms": t_err,
                "qrs_onset_sigma_ms": sigma[beat_idx, QRS_ONSET],
                "t_offset_sigma_ms": sigma[beat_idx, T_OFFSET],
                "qt_error_ms": t_err - q_err,
            })
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, source: str,
              calibration_zcorr: float) -> tuple[dict, pd.DataFrame]:
    q = df.qrs_onset_error_ms.to_numpy()
    t = df.t_offset_error_ms.to_numpy()
    qt = df.qt_error_ms.to_numpy()
    sq = df.qrs_onset_sigma_ms.to_numpy()
    st = df.t_offset_sigma_ms.to_numpy()
    cov = float(np.cov(q, t, ddof=1)[0, 1])
    corr = float(np.corrcoef(q, t)[0, 1])
    zcorr = float(np.corrcoef(q / sq, t / st)[0, 1])
    sigma_ind = np.sqrt(sq**2 + st**2)
    # The covariance-aware predictor is fixed using the same-protocol
    # validation estimate. Held-out errors are never used to tune their own
    # interval width.
    variance_cov = sq**2 + st**2 - 2 * calibration_zcorr * sq * st
    sigma_cov = np.sqrt(np.clip(variance_cov, 1e-12, None))
    row = {
        "source": source, "n": len(df), "qt_mae_ms": np.abs(qt).mean(),
        "qt_median_ae_ms": np.median(np.abs(qt)), "qt_bias_ms": qt.mean(),
        "qt_rmse_ms": np.sqrt(np.mean(qt**2)),
        "qrs_t_error_covariance_ms2": cov, "qrs_t_error_correlation": corr,
        "standardized_error_correlation": zcorr,
        "calibration_standardized_correlation_used": calibration_zcorr,
        "mean_qt_sigma_independence_ms": sigma_ind.mean(),
        "mean_qt_sigma_covariance_aware_ms": sigma_cov.mean(),
    }
    coverage_rows = []
    for method, sig in (("independence", sigma_ind),
                        ("covariance_aware", sigma_cov)):
        item = {"source": source, "method": method, "n": len(df)}
        for level in LEVELS:
            zcrit = stats.norm.ppf(0.5 + level / 2)
            item[f"picp_{int(level*100)}"] = np.mean(np.abs(qt) <= zcrit * sig)
        coverage_rows.append(item)
    return row, pd.DataFrame(coverage_rows)


def main() -> None:
    model, device, val_records = load_model()
    sources = {
        "same_protocol_validation": [f"data_processed/qtdb/{x}" for x in val_records
                                      if os.path.exists(f"data_processed/qtdb/{x}")],
        "fully_held_out_annotator_1": sorted(glob.glob("data_processed/qtdb_calib/*.q1c.npz")),
        "fully_held_out_annotator_2": sorted(glob.glob("data_processed/qtdb_calib/*.q2c.npz")),
    }
    out_dir = Path("revision_work/analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, coverage, beats = [], [], []
    collected = {source: collect(paths, model, device)
                 for source, paths in sources.items()}
    val = collected["same_protocol_validation"]
    calibration_zcorr = float(np.corrcoef(
        val.qrs_onset_error_ms / val.qrs_onset_sigma_ms,
        val.t_offset_error_ms / val.t_offset_sigma_ms)[0, 1])
    for source, df in collected.items():
        df.insert(0, "source", source)
        row, cov = summarize(df, source, calibration_zcorr)
        summaries.append(row); coverage.append(cov); beats.append(df)
    pd.DataFrame(summaries).to_csv(out_dir / "direct_qt_accuracy_covariance.csv", index=False)
    pd.concat(coverage, ignore_index=True).to_csv(out_dir / "direct_qt_picp.csv", index=False)
    pd.concat(beats, ignore_index=True).to_csv(out_dir / "direct_qt_beat_errors.csv", index=False)
    print(pd.DataFrame(summaries).to_string(index=False))
    print("\n", pd.concat(coverage, ignore_index=True).to_string(index=False))


if __name__ == "__main__":
    main()
