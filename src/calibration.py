"""Calibration benchmark: compare the fine-tuned model's predicted landmark
uncertainty against genuine inter-observer disagreement in the 11 dually-
annotated QTDB records (sel100, sel102, ..., sel230), held out of fine-tuning.

For each matched beat (nearest QRS peak between annotators 1 and 2, tolerance
50 ms), we have:
  - the model's predicted SD (sigma) for a landmark, evaluated on the q1c-
    anchored window
  - the actual |q1c - q2c| absolute disagreement for that landmark

A Gaussian with SD sigma has E|X1 - X2| = sigma * 2/sqrt(pi) for two iid
draws; we convert the model's sigma to this "expected inter-observer-like
absolute difference" and TOST-test it for equivalence against the observed
|q1c - q2c| values, with a pre-specified small-effect equivalence margin
(0.2 * SD of the observed differences, per landmark).
"""
import glob
import os
import sys
import numpy as np
import pandas as pd
import torch
from statsmodels.stats.weightstats import ttost_paired

sys.path.insert(0, os.path.dirname(__file__))
from model import ECGDelineator, LANDMARKS
from dataset import WIN_BEFORE, WIN_AFTER, WIN_LEN

DUAL_RECORDS = ["sel100", "sel102", "sel103", "sel114", "sel116", "sel117",
                "sel123", "sel213", "sel221", "sel223", "sel230"]
FS = 250.0
MATCH_TOL_SAMPLES = int(0.05 * FS)  # 50 ms
GAUSS_E_ABS_DIFF = 2.0 / np.sqrt(np.pi)  # E|X1-X2| / sigma for iid Gaussians


def load_model(ckpt_path, device):
    sd = torch.load(ckpt_path, map_location=device)
    model = ECGDelineator(win_len=WIN_LEN).to(device)
    model.load_state_dict(sd["model"])
    model.eval()
    return model


def match_beats(beats1, beats2, tol=MATCH_TOL_SAMPLES):
    """Match beats between two annotators by nearest QRS peak."""
    peaks2 = beats2[:, 2]
    pairs = []
    for i, b1 in enumerate(beats1):
        p1 = b1[2]
        j = np.argmin(np.abs(peaks2 - p1))
        if abs(peaks2[j] - p1) <= tol:
            pairs.append((i, j))
    return pairs


def run_inference(model, sig, beats, device):
    """Returns mu (samples, N x 4), sigma (samples, N x 4), presence_prob (N x 4)."""
    model.eval()
    N = len(beats)
    mus = np.zeros((N, 4)); sigmas = np.zeros((N, 4)); pres = np.zeros((N, 4))
    batch = []
    idxs = []
    def flush(batch, idxs):
        if not batch:
            return
        x = torch.from_numpy(np.stack(batch)).unsqueeze(1).to(device)
        with torch.no_grad():
            _, mu, log_var, pres_logit = model(x)
        mu = mu.cpu().numpy(); sig_ = np.exp(0.5 * np.clip(log_var.cpu().numpy(), -14, 6))
        p = torch.sigmoid(pres_logit).cpu().numpy()
        for k, ii in enumerate(idxs):
            mus[ii] = mu[k]; sigmas[ii] = sig_[k]; pres[ii] = p[k]

    for i, b in enumerate(beats):
        peak = b[2]
        start = peak - WIN_BEFORE
        end = peak + WIN_AFTER
        if start < 0 or end > len(sig):
            continue
        w = sig[start:end].astype(np.float32)
        w = (w - w.mean()) / (w.std() + 1e-6)
        batch.append(w); idxs.append(i)
        if len(batch) >= 256:
            flush(batch, idxs); batch = []; idxs = []
    flush(batch, idxs)
    return mus, sigmas, pres


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_model("results/ckpt_qtdb.pt", device)

    rows = []
    for rid in DUAL_RECORDS:
        d1 = np.load(f"data_processed/qtdb_calib/{rid}.q1c.npz")
        d2 = np.load(f"data_processed/qtdb_calib/{rid}.q2c.npz")
        sig = d1["signal"]
        beats1 = d1["beats"]; beats2 = d2["beats"]
        pairs = match_beats(beats1, beats2)
        if not pairs:
            continue
        idx1 = np.array([p[0] for p in pairs])
        matched_beats1 = beats1[idx1]
        mus, sigmas, pres = run_inference(model, sig, matched_beats1, device)

        for k, (i1, i2) in enumerate(pairs):
            start = beats1[i1, 2] - WIN_BEFORE
            for li, lm in enumerate(LANDMARKS):
                col = {"p_onset": 3, "qrs_onset": 0, "qrs_offset": 1, "t_offset": 6}[lm]
                v1 = beats1[i1, col]
                v2 = beats2[i2, col]
                if v1 < 0 or v2 < 0:
                    continue
                obs_diff_ms = abs(int(v1) - int(v2)) / FS * 1000
                sigma_ms = sigmas[k, li] * WIN_LEN / FS * 1000
                if pres[k, li] < 0.5:
                    continue
                rows.append(dict(record=rid, landmark=lm, obs_diff_ms=obs_diff_ms,
                                  model_sigma_ms=sigma_ms,
                                  model_equiv_diff_ms=GAUSS_E_ABS_DIFF * sigma_ms))

    df = pd.DataFrame(rows)
    df.to_csv("results/calibration_beats.csv", index=False)
    print(f"matched beat-landmark observations: {len(df)}")

    summary_rows = []
    for lm in LANDMARKS:
        sub = df[df.landmark == lm]
        if len(sub) < 10:
            print(f"{lm}: insufficient matched beats (n={len(sub)}), skipping TOST")
            continue
        obs = sub.obs_diff_ms.values
        pred = sub.model_equiv_diff_ms.values
        margin = 0.2 * obs.std(ddof=1)
        try:
            pval, (t1, p1, df1), (t2, p2, df2) = ttost_paired(pred, obs, -margin, margin)
        except Exception as e:
            print(f"{lm}: TOST failed: {e}")
            continue
        summary_rows.append(dict(
            landmark=lm, n=len(sub),
            mean_obs_interobs_diff_ms=obs.mean(), sd_obs_ms=obs.std(ddof=1),
            mean_model_equiv_diff_ms=pred.mean(), sd_model_ms=pred.std(ddof=1),
            mean_diff_ms=pred.mean() - obs.mean(), equivalence_margin_ms=margin,
            tost_pvalue=pval, equivalent_at_0_05=pval < 0.05,
        ))
        print(f"{lm}: n={len(sub)} obs={obs.mean():.1f}ms model_equiv={pred.mean():.1f}ms "
              f"margin=+-{margin:.1f}ms TOST p={pval:.4f} equivalent={pval<0.05}")

    summary = pd.DataFrame(summary_rows)
    summary.to_csv("results/calibration_summary.csv", index=False)
    print("\nSaved results/calibration_beats.csv and results/calibration_summary.csv")


if __name__ == "__main__":
    main()
