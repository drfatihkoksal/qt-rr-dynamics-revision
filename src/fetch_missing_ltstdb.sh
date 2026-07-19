#!/bin/bash
# Targeted download of the 14 LTST DB records absent from the merged source.
# Essential files only (hea, dat, atr, sta, stb, stc, ari, 16a).
set -uo pipefail
BASE="https://physionet.org/files/ltstdb/1.0.0"
OUT="/data/qt/ltstdb/ltstdb/1.0.0"
mkdir -p "$OUT"
RECS="s20141 s20201 s20211 s20221 s20231 s20241 s20501 s20521 s20531 s20541 s20621 s20631 s20641 s20651"
EXTS="hea dat atr sta stb stc ari 16a"
joblist=$(mktemp)
for r in $RECS; do for e in $EXTS; do echo "$BASE/$r.$e $OUT/$r.$e"; done; done > "$joblist"
fetch_one() {
  url="$1"; out="$2"
  if [ -s "$out" ]; then return 0; fi
  curl -sf -C - -o "$out" "$url" 2>/dev/null || rm -f "$out"
}
export -f fetch_one
cat "$joblist" | xargs -P 8 -L 1 bash -c 'fetch_one "$1" "$2"' _
rm -f "$joblist"
echo "DONE_MISSING got_dat=$(ls $OUT/s2014*.dat $OUT/s202*.dat $OUT/s205*.dat $OUT/s206*.dat 2>/dev/null | wc -l)"
