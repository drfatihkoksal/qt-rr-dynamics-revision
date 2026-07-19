import argparse
import os
import sys
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(__file__))
from model import ECGDelineator, LANDMARKS
from dataset import BeatWindowDataset, WIN_LEN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--fs", type=float, default=250.0)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sd = torch.load(args.ckpt, map_location=device)
    val_records = set(sd.get("val_records", []))
    paths = [os.path.join(args.data_dir, f) for f in val_records]
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        print("no val records found on disk, aborting")
        return

    model = ECGDelineator(win_len=WIN_LEN).to(device)
    model.load_state_dict(sd["model"])
    model.eval()

    ds = BeatWindowDataset(paths)
    loader = DataLoader(ds, batch_size=256, shuffle=False)

    correct = total = 0
    abs_err = {lm: [] for lm in LANDMARKS}
    with torch.no_grad():
        for sig_w, seg_w, targets, presence in loader:
            sig_w = sig_w.to(device); seg_w = seg_w.to(device)
            seg_logits, mu, log_var, presence_logit = model(sig_w)
            pred = seg_logits.argmax(1)
            correct += (pred == seg_w).sum().item()
            total += seg_w.numel()
            mu = mu.cpu().numpy(); targets = targets.numpy(); presence = presence.numpy()
            for i, lm in enumerate(LANDMARKS):
                mask = presence[:, i] > 0.5
                if mask.sum() > 0:
                    err_samples = (mu[mask, i] - targets[mask, i]) * WIN_LEN
                    abs_err[lm].extend(np.abs(err_samples).tolist())

    print(f"per-sample seg accuracy: {correct/total:.4f}")
    for lm in LANDMARKS:
        e = np.array(abs_err[lm])
        if len(e):
            ms = e / args.fs * 1000
            print(f"{lm}: n={len(e)} MAE={ms.mean():.1f}ms median={np.median(ms):.1f}ms p90={np.percentile(ms,90):.1f}ms")


if __name__ == "__main__":
    main()
