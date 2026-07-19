import glob
import os
import numpy as np
import torch
from torch.utils.data import Dataset

WIN_BEFORE = 200  # samples before R-peak (0.8s @ 250Hz)
WIN_AFTER = 300  # samples after R-peak (1.2s @ 250Hz)
WIN_LEN = WIN_BEFORE + WIN_AFTER  # 500


class BeatWindowDataset(Dataset):
    """Loads preprocessed per-record npz files and exposes one beat-centered
    window per item: (signal_window, seg_label_window, landmark_targets[4],
    presence_mask[4]).
    """

    def __init__(self, npz_paths, win_before=WIN_BEFORE, win_after=WIN_AFTER, augment=False):
        self.win_before = win_before
        self.win_after = win_after
        self.win_len = win_before + win_after
        self.augment = augment
        self.records = []  # list of (signal, dense, beats)
        self.index = []  # (record_idx, beat_idx)
        for p in npz_paths:
            d = np.load(p)
            sig = d["signal"].astype(np.float32)
            dense = d["dense"].astype(np.int64)
            beats = d["beats"]
            ridx = len(self.records)
            self.records.append((sig, dense))
            for bi in range(len(beats)):
                peak = beats[bi, 2]
                if peak - win_before < 0 or peak + win_after > len(sig):
                    continue
                self.index.append((ridx, beats[bi]))

    def __len__(self):
        return len(self.index)

    def _normalize(self, sig):
        mu = sig.mean()
        sd = sig.std() + 1e-6
        return (sig - mu) / sd

    def __getitem__(self, idx):
        ridx, beat = self.index[idx]
        sig, dense = self.records[ridx]
        qrs_on, qrs_off, qrs_peak, p_on, p_off, t_on, t_off = beat
        start = qrs_peak - self.win_before
        end = qrs_peak + self.win_after

        sig_w = self._normalize(sig[start:end].copy())
        seg_w = dense[start:end].copy()

        targets = np.zeros(4, dtype=np.float32)
        presence = np.zeros(4, dtype=np.float32)
        # landmark order: p_onset, qrs_onset, qrs_offset, t_offset
        raw_vals = [p_on, qrs_on, qrs_off, t_off]
        for i, v in enumerate(raw_vals):
            if v is not None and v >= 0:
                rel = v - start
                if 0 <= rel < self.win_len:
                    targets[i] = rel / self.win_len  # normalize to [0,1]
                    presence[i] = 1.0

        return (torch.from_numpy(sig_w).unsqueeze(0),
                torch.from_numpy(seg_w),
                torch.from_numpy(targets),
                torch.from_numpy(presence))


def list_npz(pattern):
    return sorted(glob.glob(pattern))
