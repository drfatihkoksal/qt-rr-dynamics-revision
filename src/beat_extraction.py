"""Beat-by-beat QT + uncertainty extraction for a single record/lead, using
known R-peak locations (WFDB beat annotations, .atr) as the window anchors
and the fine-tuned delineator to predict QRS-onset and T-offset (+ sigma).
"""
import os
import sys
import numpy as np
import pandas as pd
import torch
import wfdb

sys.path.insert(0, os.path.dirname(__file__))
from model import ECGDelineator
from dataset import WIN_BEFORE, WIN_AFTER, WIN_LEN

NORMAL_BEAT_SYMBOLS = {"N", "•", "."}  # normal-beat annotation symbols (varies by db)


def load_model(ckpt_path="results/ckpt_qtdb.pt", device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    sd = torch.load(ckpt_path, map_location=device)
    model = ECGDelineator(win_len=WIN_LEN).to(device)
    model.load_state_dict(sd["model"])
    model.eval()
    return model, device


def get_beat_annotations(record_path, ann_ext="atr"):
    ann = wfdb.rdann(record_path, ann_ext)
    return ann.sample, ann.symbol


@torch.no_grad()
def run_delineation(model, device, sig, peak_samples, batch_size=1024):
    """sig: 1D float array (already the desired lead). peak_samples: int array
    of R-peak sample indices. Returns dict of arrays aligned to peak_samples:
    qrs_onset, t_offset (sample idx, float), qrs_onset_sigma_ms, t_offset_sigma_ms
    (nan where window falls outside the signal or presence prob < 0.5)."""
    n = len(peak_samples)
    qrs_onset = np.full(n, np.nan); t_offset = np.full(n, np.nan)
    qrs_sigma = np.full(n, np.nan); t_sigma = np.full(n, np.nan)

    valid_idx = []
    windows = []
    starts = []
    for i, p in enumerate(peak_samples):
        s = p - WIN_BEFORE
        e = p + WIN_AFTER
        if s < 0 or e > len(sig):
            continue
        w = sig[s:e].astype(np.float32)
        sd_ = w.std()
        if sd_ < 1e-8:
            continue
        w = (w - w.mean()) / (sd_ + 1e-6)
        windows.append(w)
        starts.append(s)
        valid_idx.append(i)

    for b0 in range(0, len(windows), batch_size):
        chunk = windows[b0:b0 + batch_size]
        chunk_idx = valid_idx[b0:b0 + batch_size]
        chunk_starts = starts[b0:b0 + batch_size]
        x = torch.from_numpy(np.stack(chunk)).unsqueeze(1).to(device)
        _, mu, log_var, presence_logit = model(x)
        mu = mu.cpu().numpy()
        sigma = np.exp(0.5 * np.clip(log_var.cpu().numpy(), -14, 6))
        pres = torch.sigmoid(presence_logit).cpu().numpy()
        for k, gi in enumerate(chunk_idx):
            st = chunk_starts[k]
            if pres[k, 1] > 0.5:  # qrs_onset landmark index 1
                qrs_onset[gi] = st + mu[k, 1] * WIN_LEN
                qrs_sigma[gi] = sigma[k, 1] * WIN_LEN
            if pres[k, 3] > 0.5:  # t_offset landmark index 3
                t_offset[gi] = st + mu[k, 3] * WIN_LEN
                t_sigma[gi] = sigma[k, 3] * WIN_LEN

    return dict(qrs_onset=qrs_onset, t_offset=t_offset,
                qrs_onset_sigma=qrs_sigma, t_offset_sigma=t_sigma)


def extract_beats(record_path, lead_idx, model, device, ann_ext="atr", fs=250.0):
    """Returns a DataFrame with one row per beat (excluding the first, which
    has no preceding RR): sample, rr_ms, qt_ms, qt_sigma_ms, beat_symbol."""
    rec = wfdb.rdrecord(record_path, channels=[lead_idx])
    sig = rec.p_signal[:, 0].astype(np.float32)
    samples, symbols = get_beat_annotations(record_path, ann_ext)

    keep = [i for i, s in enumerate(symbols) if s in NORMAL_BEAT_SYMBOLS]
    peak_samples = samples[keep]
    beat_symbols = [symbols[i] for i in keep]

    res = run_delineation(model, device, sig, peak_samples)

    qt_samples = res["t_offset"] - res["qrs_onset"]
    qt_sigma = np.sqrt(res["qrs_onset_sigma"] ** 2 + res["t_offset_sigma"] ** 2)

    rr_ms = np.full(len(peak_samples), np.nan)
    rr_ms[1:] = np.diff(peak_samples) / fs * 1000

    df = pd.DataFrame(dict(
        sample=peak_samples,
        beat_symbol=beat_symbols,
        rr_ms=rr_ms,
        qt_ms=qt_samples / fs * 1000,
        qt_sigma_ms=qt_sigma / fs * 1000,
        qrs_onset_sample=res["qrs_onset"],
        t_offset_sample=res["t_offset"],
    ))
    return df
