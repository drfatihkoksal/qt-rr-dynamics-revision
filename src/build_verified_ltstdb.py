"""Build a checksum-verified LTST DB view without modifying source mirrors."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


MAIN = Path("ltstdb/ltstdb/1.0.0")
MIRROR = Path("LTSTDB_ISCHEMIC")
OUT = Path("revision_work/data/ltstdb_verified")
ESSENTIAL = ("hea", "dat", "atr", "sta", "stb", "stc")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    expected = {}
    for line in (MAIN / "SHA256SUMS.txt").read_text().splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2:
            expected[fields[1].lstrip("*")] = fields[0]
    records = [x.strip() for x in (MAIN / "RECORDS").read_text().splitlines() if x.strip()]
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [MAIN, MIRROR]
    downloaded = Path("revision_work/s20011.dat.download")
    failures = []
    audit = []
    for record in records:
        for ext in ESSENTIAL:
            name = f"{record}.{ext}"
            candidates = [root / name for root in sources]
            if name == "s20011.dat":
                candidates.insert(0, downloaded)
            chosen = None
            for candidate in candidates:
                if candidate.exists() and digest(candidate) == expected.get(name):
                    chosen = candidate
                    break
            if chosen is None:
                failures.append(name)
                continue
            target = OUT / name
            if target.exists() or target.is_symlink():
                target.unlink()
            os.link(chosen, target)
            audit.append((name, str(chosen), expected[name]))
    for name in ("RECORDS", "SHA256SUMS.txt"):
        target = OUT / name
        if target.exists():
            target.unlink()
        os.link(MAIN / name, target)
    audit_path = OUT / "verified_sources.tsv"
    audit_path.write_text("file\tsource\tsha256\n" + "\n".join("\t".join(x) for x in audit) + "\n")
    if failures:
        raise RuntimeError("Missing or checksum-invalid essential files: " + ", ".join(failures))
    print(f"Verified {len(audit)} essential files for {len(records)} records in {OUT}")


if __name__ == "__main__":
    main()
