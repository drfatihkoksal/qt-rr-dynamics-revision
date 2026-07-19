"""Shared utilities: WFDB annotation parsing, beat extraction, windowing.

Annotation convention (LUDB, QTDB): a wave is encoded as three consecutive
events '(' onset -> {p, N, t, u} peak/fiducial -> ')' offset. Onset/offset are
sometimes missing (unpaired peak, or a lone boundary). We parse defensively
and drop anything that doesn't resolve to a clean (onset, peak, offset, class)
triplet.
"""
import numpy as np
import wfdb

WAVE_CLASS = {"p": 1, "N": 2, "t": 3}  # background = 0; 'u' (U-wave) ignored
N_CLASSES = 4


def parse_waves(ann):
    """Return list of dicts: {onset, peak, offset, cls} sorted by onset.

    Onset may be None: QTDB does not annotate a T-wave onset, only its peak
    ('t') and offset (')'); a bare peak with no preceding unconsumed '(' is
    kept with onset=None rather than dropped.
    """
    waves = []
    pending_onset = None
    awaiting = None  # dict(onset, peak, cls) once a peak symbol is seen
    for samp, sym in zip(ann.sample, ann.symbol):
        if sym == "(":
            pending_onset = samp
        elif sym in WAVE_CLASS:
            awaiting = dict(onset=pending_onset, peak=int(samp), cls=sym)
            pending_onset = None
        elif sym == ")":
            if awaiting is not None:
                waves.append(dict(onset=(int(awaiting["onset"]) if awaiting["onset"] is not None else None),
                                   peak=awaiting["peak"], offset=int(samp), cls=awaiting["cls"]))
            awaiting = None
    return waves


def build_dense_labels(sig_len, waves):
    lab = np.zeros(sig_len, dtype=np.int64)
    for w in waves:
        c = WAVE_CLASS[w["cls"]]
        onset = w["onset"] if w["onset"] is not None else w["peak"]
        on = max(0, onset)
        off = min(sig_len, w["offset"] + 1)
        if off > on:
            lab[on:off] = c
    return lab


def group_beats(waves, p_search_ms=400, t_search_ms=700, fs=250):
    """Group waves into PQRST beats anchored on each QRS ('N').

    Returns list of beat dicts with qrs_onset/offset/peak (always present) and
    optional p_onset/p_offset/t_onset/t_offset (None if not found nearby).
    """
    qrs_list = [w for w in waves if w["cls"] == "N"]
    p_list = [w for w in waves if w["cls"] == "p"]
    t_list = [w for w in waves if w["cls"] == "t"]
    p_search = int(p_search_ms * fs / 1000)
    t_search = int(t_search_ms * fs / 1000)

    beats = []
    for q in qrs_list:
        if q["onset"] is None or q["offset"] is None:
            continue  # QRS must have both boundaries to anchor a beat window
        beat = dict(qrs_onset=q["onset"], qrs_offset=q["offset"], qrs_peak=q["peak"])
        # nearest preceding P wave whose offset precedes this QRS onset
        best_p = None
        for p in p_list:
            if p["offset"] <= q["onset"] and (q["onset"] - p["offset"]) <= p_search:
                if best_p is None or p["offset"] > best_p["offset"]:
                    best_p = p
        if best_p is not None:
            beat["p_onset"] = best_p["onset"]
            beat["p_offset"] = best_p["offset"]
        else:
            beat["p_onset"] = None
            beat["p_offset"] = None
        # nearest following T wave whose peak follows this QRS offset
        # (T onset is not annotated in QTDB, so match on peak, not onset)
        best_t = None
        for t in t_list:
            if t["peak"] >= q["offset"] and (t["peak"] - q["offset"]) <= t_search:
                if best_t is None or t["peak"] < best_t["peak"]:
                    best_t = t
        if best_t is not None:
            beat["t_onset"] = best_t["onset"]
            beat["t_offset"] = best_t["offset"]
        else:
            beat["t_onset"] = None
            beat["t_offset"] = None
        beats.append(beat)
    return beats


def resample_signal(sig, fs_in, fs_out):
    if fs_in == fs_out:
        return sig
    import scipy.signal as sps
    n_out = int(round(len(sig) * fs_out / fs_in))
    return sps.resample(sig, n_out)


def rescale_time(x, fs_in, fs_out):
    return x * (fs_out / fs_in)
