#!/bin/bash
# Clean serial fetch (no resume) of the 5 records whose .dat became corrupt
# under -C - resume. Deletes and re-GETs fresh, verifies against SHA256, up to
# 4 attempts each.
set -uo pipefail
BASE="https://physionet.org/files/ltstdb/1.0.0"
OUT="/data/qt/ltstdb/ltstdb/1.0.0"
SHA="/data/qt/ltstdb_sha256.txt"
RECS="s20531 s20541 s20631 s20641 s20651"
for r in $RECS; do
  exp=$(grep -E "[[:space:]]$r\.dat$" "$SHA" | awk '{print $1}')
  for attempt in 1 2 3 4; do
    act=$(sha256sum "$OUT/$r.dat" 2>/dev/null | awk '{print $1}')
    [ "$exp" = "$act" ] && break
    rm -f "$OUT/$r.dat"
    curl -sf -o "$OUT/$r.dat" "$BASE/$r.dat"
    for e in hea atr sta stb stc ari 16a; do
      curl -sf -o "$OUT/$r.$e" "$BASE/$r.$e" 2>/dev/null || true
    done
  done
done
ok=0; bad=""
for r in $RECS; do
  exp=$(grep -E "[[:space:]]$r\.dat$" "$SHA" | awk '{print $1}')
  act=$(sha256sum "$OUT/$r.dat" 2>/dev/null | awk '{print $1}')
  [ "$exp" = "$act" ] && ok=$((ok+1)) || bad="$bad$r "
done
echo "DONE_FETCH5 ok=$ok/5 bad: $bad"
