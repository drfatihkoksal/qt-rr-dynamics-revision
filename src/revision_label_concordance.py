"""Cross-lead concordance audit for LTST DB ST-episode labels."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import wfdb

from episodes import parse_ltstdb_episodes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path,
                    default=Path("revision_work/data/ltstdb_verified"))
    ap.add_argument("--protocol", default="stb", choices=("sta", "stb", "stc"))
    ap.add_argument("--out-dir", type=Path, default=Path("revision_work/audit"))
    args = ap.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    records = [x.strip() for x in (args.data_dir / "RECORDS").read_text().splitlines()
               if x.strip()]
    rows = []
    for record in records:
        episodes, _ = parse_ltstdb_episodes(str(args.data_dir / record), args.protocol)
        boundaries = sorted({v for ep in episodes for v in (ep["onset"], ep["offset"])})
        for start, stop in zip(boundaries[:-1], boundaries[1:]):
            if stop <= start:
                continue
            mid = (start + stop) / 2
            active = {ep["lead"]: ep["kind"] for ep in episodes
                      if ep["onset"] <= mid < ep["offset"]}
            if not active:
                continue
            kinds = set(active.values())
            status = ("single_active_lead" if len(active) == 1 else
                      "concordant_multilead" if len(kinds) == 1 else
                      "discordant_multilead")
            rows.append({"record": record, "subject_id": record[:-1],
                         "start_sample": start, "stop_sample": stop,
                         "duration_s": (stop-start)/250.0,
                         "active_leads": ";".join(map(str, sorted(active))),
                         "active_labels": ";".join(f"L{k}:{active[k]}" for k in sorted(active)),
                         "concordance_status": status,
                         "consolidated_label": next(iter(kinds)) if len(kinds) == 1 else "discordant"})
    segments = pd.DataFrame(rows)
    segments.to_csv(args.out_dir / f"cross_lead_segments_{args.protocol}.csv", index=False)
    summary = segments.groupby(["concordance_status", "consolidated_label"], as_index=False).agg(
        segments=("record", "size"), records=("record", "nunique"),
        subjects=("subject_id", "nunique"), duration_s=("duration_s", "sum"))
    summary.to_csv(args.out_dir / f"cross_lead_concordance_{args.protocol}.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
