"""End-to-end per-record pipeline: delineate beats -> parse episodes -> fit
individualized hysteresis-corrected QT-RR baseline -> label + compute
residuals for every beat (episode-stratified). Works for both EDB and
LTST DB given the right parser/config. Produces one long-format CSV.
"""
import argparse
import glob
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from beat_extraction import load_model, extract_beats
from baseline_fit import select_tau_and_fit, rr_smoothed
from episodes import parse_ltstdb_episodes, parse_edb_episodes, intervals_to_mask


def label_episodes(n, samples, episodes_for_lead, min_duration_s, fs):
    """Returns (label array of str/None, episode_id array of int/-1,
    kept_episode_spans list) for beats indexed by `samples` (sorted)."""
    label = np.array([None] * n, dtype=object)
    epi_id = np.full(n, -1, dtype=int)
    kept_spans = []
    eid = 0
    for ep in episodes_for_lead:
        dur_s = (ep["offset"] - ep["onset"]) / fs
        if dur_s < min_duration_s:
            continue
        mask = (samples >= ep["onset"]) & (samples <= ep["offset"])
        if mask.sum() == 0:
            continue
        label[mask] = ep["kind"]
        epi_id[mask] = eid
        kept_spans.append((ep["onset"], ep["offset"], ep["kind"], eid))
        eid += 1
    return label, epi_id, kept_spans


def assign_matched_baseline(n, samples, label, kept_spans, fs):
    """For each kept episode span, tag a same-duration non-episode/clean
    window elsewhere in the record as 'matched_baseline' (best-effort;
    skips if no clean run of sufficient length is found nearby)."""
    is_free = label == None  # noqa: E711
    is_available = is_free.copy()
    matched_label = np.array([None] * n, dtype=object)
    matched_id = np.full(n, -1, dtype=int)
    for onset, offset, kind, eid in kept_spans:
        dur_samples = offset - onset
        free_idx = np.where(is_available)[0]
        if len(free_idx) == 0:
            continue
        center_guess = onset
        pos = np.searchsorted(samples[free_idx], center_guess)
        for delta in range(0, len(free_idx)):
            for cand in (pos + delta, pos - delta):
                if cand < 0 or cand >= len(free_idx):
                    continue
                start_i = free_idx[cand]
                s0 = samples[start_i]
                end_i = np.searchsorted(samples, s0 + dur_samples)
                if end_i >= n:
                    continue
                window_idx = np.arange(start_i, min(end_i, n))
                if len(window_idx) == 0:
                    continue
                if is_available[window_idx].all():
                    matched_label[window_idx] = "matched_baseline"
                    matched_id[window_idx] = eid
                    # Match without replacement so long or episode-rich
                    # records cannot recycle the same baseline evidence.
                    is_available[window_idx] = False
                    break
            else:
                continue
            break
    return matched_label, matched_id


def process_record(record_path, record_id, dataset, lead_idx, model, device,
                    fs, protocol="stb", quality_lead_map=None):
    df = extract_beats(record_path, lead_idx, model, device, fs=fs)
    df = df.reset_index(drop=True)
    n = len(df)
    samples = df["sample"].values

    if dataset == "ltstdb":
        episodes, qbad = parse_ltstdb_episodes(record_path, protocol=protocol)
    elif dataset == "edb":
        episodes, qbad = parse_edb_episodes(record_path)
    else:
        raise ValueError(dataset)

    eps_lead = [e for e in episodes if e["lead"] == lead_idx]
    bad_intervals = qbad.get(lead_idx, [])
    sig_len = int(samples[-1]) + 10 if n else 0
    bad_mask_full = intervals_to_mask(sig_len, bad_intervals)
    beat_bad = np.array([bad_mask_full[s] if s < sig_len else True for s in samples])

    valid_beat = (df["beat_symbol"] == "N").values & (~df["qt_ms"].isna().values) & (~beat_bad)

    df_v = df[valid_beat].reset_index(drop=True)
    samples_v = df_v["sample"].values
    n_v = len(df_v)

    label, epi_id, _ = label_episodes(n_v, samples_v, eps_lead, min_duration_s=0, fs=fs)
    # placeholder min_duration=0 here; final filtering applied by caller once tau is known

    clean_nonepisode = df_v[label == None].copy()  # noqa: E711
    fit = select_tau_and_fit(clean_nonepisode)
    if fit is None:
        return None

    min_dur_s = fit["tau"] * 1.5
    label, epi_id, kept_spans = label_episodes(n_v, samples_v, eps_lead, min_dur_s, fs)

    matched_label, matched_id = assign_matched_baseline(
        n_v, samples_v, label, kept_spans, fs)

    rrs = rr_smoothed(df_v["rr_ms"].values, fit["tau"])
    pred_qt = np.exp(fit["intercept"] + fit["slope"] * np.log(np.clip(rrs, 1, None)))
    resid_ms = df_v["qt_ms"].values - pred_qt

    final_label = np.where(label != None, label, matched_label)  # noqa: E711
    final_id = np.where(label != None, epi_id, matched_id)  # noqa: E711

    out = pd.DataFrame(dict(
        record=record_id, dataset=dataset, lead=lead_idx,
        sample=samples_v, rr_ms=df_v["rr_ms"].values, qt_ms=df_v["qt_ms"].values,
        qt_sigma_ms=df_v["qt_sigma_ms"].values, rr_smoothed_ms=rrs,
        pred_qt_ms=pred_qt, resid_ms=resid_ms, abs_resid_ms=np.abs(resid_ms),
        episode_type=final_label, episode_id=final_id,
        tau_s=fit["tau"], baseline_cv_r2=fit["cv_r2"], baseline_full_r2=fit["full_r2"],
        baseline_n_beats=fit["n_beats"],
    ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["ltstdb", "edb"], required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--protocol", default="stb")
    ap.add_argument("--exclude-records", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    exclude = set(x for x in args.exclude_records.split(",") if x)

    model, device = load_model()

    with open(os.path.join(args.data_dir, "RECORDS")) as f:
        records = [l.strip() for l in f if l.strip()]
    records = [r for r in records if r not in exclude]
    if args.limit:
        records = records[:args.limit]

    all_out = []
    for rid in records:
        path = os.path.join(args.data_dir, rid)
        hea = path + ".hea"
        if not os.path.exists(hea):
            print(f"SKIP {rid}: no header")
            continue
        with open(hea) as f:
            first = f.readline().split()
        n_leads = int(first[1]) if len(first) > 1 else 2
        for lead_idx in range(min(n_leads, 3)):
            try:
                res = process_record(path, rid, args.dataset, lead_idx, model, device,
                                      fs=250.0, protocol=args.protocol)
            except Exception as e:
                print(f"FAIL {rid} lead{lead_idx}: {e}")
                continue
            if res is None:
                print(f"SKIP {rid} lead{lead_idx}: baseline fit failed (too few clean beats)")
                continue
            all_out.append(res)
            n_epi = (res.episode_type.isin(["ischemic", "rate_related"])).sum()
            print(f"OK {rid} lead{lead_idx}: n={len(res)} tau={res.tau_s.iloc[0]}s "
                  f"cv_r2={res.baseline_cv_r2.iloc[0]:.3f} episode_beats={n_epi}")

    if not all_out:
        print("no records processed successfully")
        return
    full = pd.concat(all_out, ignore_index=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    full.to_csv(args.out, index=False)
    print(f"saved {len(full)} beat-rows from {full.record.nunique()} records to {args.out}")


if __name__ == "__main__":
    main()
