import argparse
import os
import sys
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(__file__))
from model import ECGDelineator, LANDMARKS
from dataset import BeatWindowDataset, list_npz, WIN_BEFORE, WIN_AFTER, WIN_LEN

def set_seed(seed=0):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def landmark_loss(mu, log_var, presence_logit, targets, presence):
    log_var = torch.clamp(log_var, min=-14, max=6)
    nll = 0.5 * log_var + (targets - mu) ** 2 / (2 * torch.exp(log_var))
    nll = (nll * presence).sum() / presence.sum().clamp(min=1)
    pres_loss = nn.functional.binary_cross_entropy_with_logits(presence_logit, presence)
    return nll, pres_loss


def run_epoch(model, loader, device, optimizer=None, seg_weight=1.0, lm_weight=5.0, pres_weight=1.0):
    train = optimizer is not None
    model.train(train)
    tot_loss = tot_seg = tot_nll = tot_pres = 0.0
    n_batches = 0
    ce = nn.CrossEntropyLoss()
    with torch.set_grad_enabled(train):
        for sig_w, seg_w, targets, presence in loader:
            sig_w = sig_w.to(device)
            seg_w = seg_w.to(device)
            targets = targets.to(device)
            presence = presence.to(device)

            seg_logits, mu, log_var, presence_logit = model(sig_w)
            seg_loss = ce(seg_logits, seg_w)
            nll, pres_loss = landmark_loss(mu, log_var, presence_logit, targets, presence)
            loss = seg_weight * seg_loss + lm_weight * nll + pres_weight * pres_loss

            if train:
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()

            tot_loss += loss.item(); tot_seg += seg_loss.item()
            tot_nll += nll.item(); tot_pres += pres_loss.item()
            n_batches += 1
    return tot_loss / n_batches, tot_seg / n_batches, tot_nll / n_batches, tot_pres / n_batches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-glob", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--init-ckpt", default=None)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--patience", type=int, default=10)
    args = ap.parse_args()

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    paths = list_npz(args.data_glob)
    rng = random.Random(args.seed)
    rng.shuffle(paths)
    n_val = max(1, int(len(paths) * args.val_frac))
    val_paths = paths[:n_val]
    train_paths = paths[n_val:]
    print(f"records: train={len(train_paths)} val={len(val_paths)}")

    train_ds = BeatWindowDataset(train_paths)
    val_ds = BeatWindowDataset(val_paths)
    print(f"beats: train={len(train_ds)} val={len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = ECGDelineator(win_len=WIN_LEN).to(device)
    if args.init_ckpt:
        sd = torch.load(args.init_ckpt, map_location=device)
        model.load_state_dict(sd["model"])
        print(f"initialized from {args.init_ckpt}")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=4)

    best_val = float("inf")
    best_state = None
    bad_epochs = 0
    for epoch in range(args.epochs):
        tr = run_epoch(model, train_loader, device, optimizer)
        va = run_epoch(model, val_loader, device, None)
        scheduler.step(va[0])
        print(f"epoch {epoch:03d} train loss={tr[0]:.4f} (seg={tr[1]:.4f} nll={tr[2]:.4f} pres={tr[3]:.4f}) "
              f"val loss={va[0]:.4f} (seg={va[1]:.4f} nll={va[2]:.4f} pres={va[3]:.4f}) lr={optimizer.param_groups[0]['lr']:.2e}")
        if va[0] < best_val - 1e-4:
            best_val = va[0]
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= args.patience:
                print("early stopping")
                break

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save({"model": best_state, "win_before": WIN_BEFORE, "win_after": WIN_AFTER,
                "val_loss": best_val, "val_records": [os.path.basename(p) for p in val_paths]}, args.out)
    print(f"saved best checkpoint (val_loss={best_val:.4f}) to {args.out}")


if __name__ == "__main__":
    main()
