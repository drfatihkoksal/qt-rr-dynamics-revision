"""Preprocess LUDB (lead ii, resampled 500Hz->250Hz) into per-record npz files
with a dense 4-class label array and a beat table (QRS-anchored PQRST groups).
"""
import os
import sys
import numpy as np
import wfdb

sys.path.insert(0, os.path.dirname(__file__))
from common import parse_waves, build_dense_labels, group_beats, resample_signal, rescale_time

LUDB_DIR = "/data/qt/ludb/1.0.1"
OUT_DIR = "/data/qt/data_processed/ludb"
FS_OUT = 250

os.makedirs(OUT_DIR, exist_ok=True)

with open("/data/qt/ludb/1.0.1/RECORDS") as f:
    records = [l.strip() for l in f if l.strip()]

n_ok, n_fail = 0, 0
total_beats = 0
for rid in records:
    path = os.path.join(LUDB_DIR, rid)
    rid = os.path.basename(rid)
    try:
        rec = wfdb.rdrecord(path, channel_names=["ii"])
        sig = rec.p_signal[:, 0].astype(np.float32)
        fs_in = rec.fs
        ann = wfdb.rdann(path, "ii")
    except Exception as e:
        print(f"SKIP {rid}: {e}")
        n_fail += 1
        continue

    waves = parse_waves(ann)
    if len(waves) == 0:
        n_fail += 1
        continue

    sig_rs = resample_signal(sig, fs_in, FS_OUT).astype(np.float32)
    scale = FS_OUT / fs_in
    waves_rs = [dict(onset=(int(round(w["onset"] * scale)) if w["onset"] is not None else None),
                      peak=int(round(w["peak"] * scale)),
                      offset=int(round(w["offset"] * scale)),
                      cls=w["cls"]) for w in waves]
    dense = build_dense_labels(len(sig_rs), waves_rs)
    beats = group_beats(waves_rs, fs=FS_OUT)

    beat_arr = np.full((len(beats), 7), -1, dtype=np.int64)
    for i, b in enumerate(beats):
        beat_arr[i] = [b["qrs_onset"], b["qrs_offset"], b["qrs_peak"],
                        b["p_onset"] if b["p_onset"] is not None else -1,
                        b["p_offset"] if b["p_offset"] is not None else -1,
                        b["t_onset"] if b["t_onset"] is not None else -1,
                        b["t_offset"] if b["t_offset"] is not None else -1]

    np.savez_compressed(os.path.join(OUT_DIR, f"{rid}.npz"),
                         signal=sig_rs, dense=dense, beats=beat_arr, fs=FS_OUT)
    n_ok += 1
    total_beats += len(beats)

print(f"LUDB preprocessing done: {n_ok} ok, {n_fail} failed, {total_beats} beats total")
