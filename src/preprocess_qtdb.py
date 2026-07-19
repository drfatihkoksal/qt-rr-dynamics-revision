"""Preprocess QTDB (signal 0 = MLII-like lead, native 250Hz) into per-record
npz files, for each available manual annotator (q1c always; q2c for the 11
dually-annotated records used later for the calibration benchmark).
"""
import os
import sys
import numpy as np
import wfdb

sys.path.insert(0, os.path.dirname(__file__))
from common import parse_waves, build_dense_labels, group_beats

QTDB_DIR = "/data/qt/qtdb/1.0.0"
OUT_DIR = "/data/qt/data_processed/qtdb"
FS = 250

os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(QTDB_DIR, "RECORDS")) as f:
    records = [l.strip() for l in f if l.strip()]

def process_one(rid, annotator):
    path = os.path.join(QTDB_DIR, rid)
    ann_path = f"{path}.{annotator}"
    if not os.path.exists(ann_path):
        return None
    rec = wfdb.rdrecord(path, channels=[0])
    sig = rec.p_signal[:, 0].astype(np.float32)
    ann = wfdb.rdann(path, annotator)
    waves = parse_waves(ann)
    if len(waves) == 0:
        return None
    dense = build_dense_labels(len(sig), waves)
    beats = group_beats(waves, fs=FS)
    if len(beats) == 0:
        return None
    beat_arr = np.full((len(beats), 7), -1, dtype=np.int64)
    for i, b in enumerate(beats):
        beat_arr[i] = [b["qrs_onset"], b["qrs_offset"], b["qrs_peak"],
                        b["p_onset"] if b["p_onset"] is not None else -1,
                        b["p_offset"] if b["p_offset"] is not None else -1,
                        b["t_onset"] if b["t_onset"] is not None else -1,
                        b["t_offset"] if b["t_offset"] is not None else -1]
    return sig, dense, beat_arr

n_ok, n_fail, total_beats = 0, 0, 0
for rid in records:
    out = process_one(rid, "q1c")
    if out is None:
        n_fail += 1
        print(f"SKIP {rid} (q1c)")
        continue
    sig, dense, beat_arr = out
    np.savez_compressed(os.path.join(OUT_DIR, f"{rid}.q1c.npz"),
                         signal=sig, dense=dense, beats=beat_arr, fs=FS)
    n_ok += 1
    total_beats += len(beat_arr)

    out2 = process_one(rid, "q2c")
    if out2 is not None:
        sig2, dense2, beat_arr2 = out2
        np.savez_compressed(os.path.join(OUT_DIR, f"{rid}.q2c.npz"),
                             signal=sig2, dense=dense2, beats=beat_arr2, fs=FS)

print(f"QTDB preprocessing done: {n_ok} ok, {n_fail} failed, {total_beats} beats total (q1c)")
