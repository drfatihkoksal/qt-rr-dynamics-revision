"""Prediction-interval coverage (PICP) of the delineator's uncertainty against
GROUND TRUTH (expert annotation), the calibration quantity the manuscript
should actually lead with. For each landmark on each beat we have the model's
predicted mean (mu, ms) and SD (sigma, ms) and the expert-marked truth; the
z-score = (mu - truth)/sigma. A well-calibrated Gaussian predictor yields, at
nominal central level p (z-threshold from the normal quantile), an empirical
fraction of |z| <= z_p equal to p (PICP ~ nominal).

Evaluated on two ground-truth sources:
  (a) the fine-tuning VALIDATION records (held-out during fine-tuning), truth =
      the single expert annotation;
  (b) the 11 dually-annotated CALIBRATION records, truth = annotator 1 (q1c),
      with annotator 2 (q2c) as a robustness check.
"""
import glob
import os
import sys
import numpy as np
import pandas as pd
import torch
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from model import ECGDelineator, LANDMARKS
from dataset import WIN_BEFORE, WIN_AFTER, WIN_LEN

FS = 250.0
LM_COL = {"p_onset": 3, "qrs_onset": 0, "qrs_offset": 1, "t_offset": 6}
NOMINAL_LEVELS = [0.50, 0.68, 0.80, 0.90, 0.95]


def load_model(ckpt="results/ckpt_qtdb.pt", device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    sd = torch.load(ckpt, map_location=device)
    m = ECGDelineator(win_len=WIN_LEN).to(device)
    m.load_state_dict(sd["model"])
    m.eval()
    return m, device, sd.get("val_records", [])


@torch.no_grad()
def infer_record(model, device, npz_path):
    """Returns per-beat (mu_ms, sigma_ms, truth_ms, present) arrays, shape (N,4)
    for the 4 landmarks, in absolute sample -> ms terms relative to record."""
    d = np.load(npz_path)
    sig = d["signal"].astype(np.float32)
    beats = d["beats"]
    N = len(beats)
    mu_ms = np.full((N, 4), np.nan)
    sigma_ms = np.full((N, 4), np.nan)
    truth_ms = np.full((N, 4), np.nan)

    windows, starts, idxs = [], [], []
    for i, b in enumerate(beats):
        peak = b[2]
        s = peak - WIN_BEFORE; e = peak + WIN_AFTER
        if s < 0 or e > len(sig):
            continue
        w = sig[s:e].astype(np.float32)
        if w.std() < 1e-8:
            continue
        windows.append((w - w.mean()) / (w.std() + 1e-6))
        starts.append(s); idxs.append(i)

    for b0 in range(0, len(windows), 512):
        chunk = np.stack(windows[b0:b0+512])
        x = torch.from_numpy(chunk).unsqueeze(1).to(device)
        _, mu, log_var, pres_logit = model(x)
        mu = mu.cpu().numpy()
        sig_ = np.exp(0.5 * np.clip(log_var.cpu().numpy(), -14, 6))
        pres = torch.sigmoid(pres_logit).cpu().numpy()
        for k, gi in enumerate(idxs[b0:b0+512]):
            st = starts[b0 + k]
            for li in range(4):
                if pres[k, li] > 0.5:
                    mu_ms[gi, li] = (st + mu[k, li] * WIN_LEN) / FS * 1000
                    sigma_ms[gi, li] = sig_[k, li] * WIN_LEN / FS * 1000
            for li, lm in enumerate(LANDMARKS):
                col = LM_COL[lm]
                v = beats[gi, col]
                if v >= 0:
                    truth_ms[gi, li] = v / FS * 1000
    return mu_ms, sigma_ms, truth_ms


def collect(npz_paths):
    model, device, _ = load_model()
    rows = []
    for p in npz_paths:
        mu, sg, tr = infer_record(model, device, p)
        for li, lm in enumerate(LANDMARKS):
            m = ~np.isnan(mu[:, li]) & ~np.isnan(tr[:, li]) & ~np.isnan(sg[:, li])
            for e, s in zip((mu[m, li] - tr[m, li]), sg[m, li]):
                rows.append(dict(landmark=lm, err_ms=e, sigma_ms=s, z=e / s))
    return pd.DataFrame(rows)


def picp_table(df, label):
    out = []
    for lm in LANDMARKS:
        sub = df[df.landmark == lm]
        if len(sub) < 20:
            continue
        row = dict(source=label, landmark=lm, n=len(sub),
                   mae_ms=np.abs(sub.err_ms).mean(),
                   mean_sigma_ms=sub.sigma_ms.mean(),
                   rmse_ms=np.sqrt((sub.err_ms**2).mean()))
        for p in NOMINAL_LEVELS:
            zt = stats.norm.ppf(0.5 + p / 2)
            cov = (np.abs(sub.z) <= zt).mean()
            row[f"PICP_{int(p*100)}"] = cov
        out.append(row)
    return pd.DataFrame(out)


def main():
    model, device, val_records = load_model()

    val_paths = [os.path.join("data_processed/qtdb", f) for f in val_records]
    val_paths = [p for p in val_paths if os.path.exists(p)]
    calib_q1 = sorted(glob.glob("data_processed/qtdb_calib/*.q1c.npz"))
    calib_q2 = sorted(glob.glob("data_processed/qtdb_calib/*.q2c.npz"))

    tables = []
    if val_paths:
        df_val = collect(val_paths)
        tables.append(picp_table(df_val, "finetune_val (single expert)"))
    df_c1 = collect(calib_q1)
    tables.append(picp_table(df_c1, "calibration (annotator 1)"))
    df_c2 = collect(calib_q2)
    tables.append(picp_table(df_c2, "calibration (annotator 2)"))

    full = pd.concat(tables, ignore_index=True)
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    print(full.to_string(index=False))
    full.to_csv("results/coverage_picp.csv", index=False)
    print("\nsaved results/coverage_picp.csv")


if __name__ == "__main__":
    main()
