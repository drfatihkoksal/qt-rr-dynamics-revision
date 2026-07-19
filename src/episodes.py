"""Parse ST-episode and signal-quality annotations for LTST DB and EDB into a
common representation: list of dicts
  {lead, onset, offset, kind}
where kind in {"ischemic", "rate_related"} for LTST DB, or {"ischemic"} only
for EDB (EDB does not distinguish rate-related ST changes; see decisions.md).
Axis-shift / conduction-change markers are parsed but excluded (kind=None).

Also provides quality-mask builders returning, per lead, a list of
(start, end) sample intervals that are noisy/unreadable and must be excluded.
"""
import re
import numpy as np
import wfdb

# ---------------------------------------------------------------- LTST DB ---

def parse_ltstdb_episodes(record_path, protocol="stb"):
    """protocol in {'sta','stb','stc'}. Returns (episodes, quality_bad_intervals)
    episodes: list of dict(lead, onset, offset, kind) kind in {ischemic, rate_related}
    quality_bad_intervals: dict lead -> list of (start,end) sample tuples (noise/unreadable)
    """
    ann = wfdb.rdann(record_path, protocol)
    episodes = []
    quality_bad = {0: [], 1: [], 2: []}
    open_stack = {}  # lead -> dict(onset, kind)
    open_urd = None
    for samp, aux in zip(ann.sample, ann.aux_note):
        aux = aux.strip("\x00").strip()
        if not aux:
            continue
        if aux.startswith("( urd") or aux == "( urd":
            open_urd = int(samp)
            continue
        if aux.startswith("urd") and aux.endswith(")"):
            if open_urd is not None:
                for ld in (0, 1, 2):
                    quality_bad[ld].append((open_urd, int(samp)))
            open_urd = None
            continue
        if aux.startswith("noi"):
            # isolated noise mark; treat as a short bad interval (+-2s)
            for ld in (0, 1, 2):
                quality_bad[ld].append((int(samp) - 500, int(samp) + 500))
            continue
        if aux.startswith("GRST") or aux.startswith("LRST"):
            continue

        m = re.match(r"^\(?(a)?(rt)?st(\d)([+-]?\d*)\)?$", aux)
        if m is None:
            continue
        is_extrema = m.group(1) == "a"
        is_rate = m.group(2) == "rt"
        lead = int(m.group(3))
        is_begin = aux.startswith("(")
        is_end = aux.endswith(")")

        if is_extrema:
            continue  # midpoint marker, not a boundary
        kind = "rate_related" if is_rate else "ischemic"
        if is_begin:
            open_stack[lead] = dict(onset=int(samp), kind=kind)
        elif is_end:
            if lead in open_stack and open_stack[lead]["kind"] == kind:
                episodes.append(dict(lead=lead, onset=open_stack[lead]["onset"],
                                      offset=int(samp), kind=kind))
                del open_stack[lead]
    return episodes, quality_bad


# ------------------------------------------------------------------- EDB ---

EDB_QUALITY_MAP = {
    0x00: "cc", 0x01: "nc", 0x02: "cn", 0x03: "nn",
    0x11: "uc", 0x12: "un", 0x20: "cu", 0x21: "nu", 0x33: "uu",
}


def parse_edb_episodes(record_path):
    """Returns (episodes, quality_bad_intervals) analogous to LTST DB.
    Only real ST episodes (uppercase 'ST') are kept as kind='ischemic';
    axis-shift artifacts (lowercase 'st') and T-wave episodes are excluded
    from the episode list, per decisions.md.
    """
    ann = wfdb.rdann(record_path, "atr")
    episodes = []
    open_stack = {}
    quality_state = {0: "c", 1: "c"}
    quality_bad = {0: [], 1: []}
    bad_start = {0: None, 1: None}

    for samp, sym, sub, aux in zip(ann.sample, ann.symbol, ann.subtype, ann.aux_note):
        if sym == "~":
            code = EDB_QUALITY_MAP.get(sub, "cc")
            new_state = {0: code[0], 1: code[1]}
            for ld in (0, 1):
                was_bad = quality_state[ld] != "c"
                is_bad = new_state[ld] != "c"
                if is_bad and not was_bad:
                    bad_start[ld] = int(samp)
                elif not is_bad and was_bad:
                    if bad_start[ld] is not None:
                        quality_bad[ld].append((bad_start[ld], int(samp)))
                    bad_start[ld] = None
            quality_state = new_state
            continue

        aux = aux.strip("\x00").strip()
        if not aux:
            continue
        m = re.match(r"^(\()?([Aa])?(ST|st)(\d)([+-]{1,2})(\d*)(\))?$", aux)
        if m is None:
            continue
        is_begin = m.group(1) == "("
        is_extrema = m.group(2) is not None
        is_axis = m.group(3) == "st"
        lead = int(m.group(4))
        is_end = m.group(7) == ")"
        if is_extrema:
            continue
        if is_axis:
            continue  # axis-shift artifact, not a real ST episode
        if is_begin:
            open_stack[lead] = int(samp)
        elif is_end:
            if lead in open_stack:
                episodes.append(dict(lead=lead, onset=open_stack[lead],
                                      offset=int(samp), kind="ischemic"))
                del open_stack[lead]
    for ld in (0, 1):
        if bad_start[ld] is not None:
            quality_bad[ld].append((bad_start[ld], ann.sample[-1]))
    return episodes, quality_bad


def intervals_to_mask(sig_len, intervals):
    mask = np.zeros(sig_len, dtype=bool)
    for s, e in intervals:
        s = max(0, int(s)); e = min(sig_len, int(e))
        if e > s:
            mask[s:e] = True
    return mask
