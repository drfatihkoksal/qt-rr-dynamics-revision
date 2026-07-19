#!/bin/bash
# Resumable, modestly-parallel downloader for LTST DB (essential files only).
# PhysioNet's https server rate-limits aggregate throughput to ~150-300KB/s
# regardless of connection count (confirmed empirically; general internet
# egress from this host is >10MB/s), so this will take multiple hours.
set -uo pipefail

BASE="https://physionet.org/files/ltstdb/1.0.0"
OUT="/data/qt/ltstdb/ltstdb/1.0.0"
mkdir -p "$OUT"

RECS=$(curl -s "$BASE/RECORDS")
EXTS="hea dat atr ari sta stb stc stf nts cnt 16a"

joblist=$(mktemp)
for r in $RECS; do
  for e in $EXTS; do
    echo "$BASE/$r.$e $OUT/$r.$e"
  done
done > "$joblist"

total=$(wc -l < "$joblist")
echo "Total files to fetch: $total"

fetch_one() {
  url="$1"; out="$2"
  if [ -s "$out" ]; then return 0; fi
  curl -sf -C - -o "$out" "$url" 2>/dev/null
  if [ ! -s "$out" ]; then rm -f "$out"; fi
}
export -f fetch_one

cat "$joblist" | xargs -P 4 -L 1 bash -c 'fetch_one "$1" "$2"' _
rm -f "$joblist"

got=$(find "$OUT" -type f | wc -l)
echo "DONE_LTSTDB got=$got / expected~$total"
