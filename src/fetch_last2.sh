#!/bin/bash
set -uo pipefail
BASE="https://physionet.org/files/ltstdb/1.0.0"
OUT="/data/qt/ltstdb/ltstdb/1.0.0"
SHA="/data/qt/ltstdb_sha256.txt"
for r in s20641 s20651; do
  exp=$(grep -E "[[:space:]]$r\.dat$" "$SHA" | awk '{print $1}')
  for attempt in 1 2 3 4 5; do
    act=$(sha256sum "$OUT/$r.dat" 2>/dev/null | awk '{print $1}')
    [ "$exp" = "$act" ] && break
    rm -f "$OUT/$r.dat"
    curl -sf -o "$OUT/$r.dat" "$BASE/$r.dat"
    for e in hea atr sta stb stc ari 16a; do curl -sf -o "$OUT/$r.$e" "$BASE/$r.$e" 2>/dev/null || true; done
  done
done
ok=0
for r in s20641 s20651; do
  exp=$(grep -E "[[:space:]]$r\.dat$" "$SHA" | awk '{print $1}')
  act=$(sha256sum "$OUT/$r.dat" 2>/dev/null | awk '{print $1}')
  [ "$exp" = "$act" ] && ok=$((ok+1))
done
echo "DONE_LAST2 ok=$ok/2"
