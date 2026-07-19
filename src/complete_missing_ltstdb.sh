#!/bin/bash
# Resume-and-verify: for each of the 14 new records, download every needed file
# and loop until its .dat matches the published SHA256. Uses curl -C - to resume
# partial files (the earlier pass skipped non-empty partials, leaving truncated
# .dat). Verifies against SHA256SUMS.txt.
set -uo pipefail
BASE="https://physionet.org/files/ltstdb/1.0.0"
OUT="/data/qt/ltstdb/ltstdb/1.0.0"
SHA="/data/qt/ltstdb_sha256.txt"
RECS="s20141 s20201 s20211 s20221 s20231 s20241 s20501 s20521 s20531 s20541 s20621 s20631 s20641 s20651"
EXTS="hea dat atr sta stb stc ari 16a"

dat_ok() {
  local r=$1
  local exp act
  exp=$(grep -E "[[:space:]]$r\.dat$" "$SHA" | awk '{print $1}')
  act=$(sha256sum "$OUT/$r.dat" 2>/dev/null | awk '{print $1}')
  [ -n "$exp" ] && [ "$exp" = "$act" ]
}

for pass in 1 2 3 4 5 6 7 8; do
  pending=""
  for r in $RECS; do
    if dat_ok "$r"; then continue; fi
    pending="$pending $r"
  done
  [ -z "$pending" ] && { echo "ALL_VERIFIED pass=$pass"; break; }
  echo "pass $pass, pending:$pending"
  # resume each pending record's files, 6-way across records
  echo $pending | tr ' ' '\n' | xargs -P 6 -I{} bash -c '
    r="{}"; BASE="'"$BASE"'"; OUT="'"$OUT"'"
    for e in '"$EXTS"'; do
      curl -sf -C - -o "$OUT/$r.$e" "$BASE/$r.$e" 2>/dev/null || true
    done
  '
done

# final report
ok=0; bad=""
for r in $RECS; do dat_ok "$r" && ok=$((ok+1)) || bad="$bad $r"; done
echo "DONE_COMPLETE verified_dat=$ok/14 bad:$bad"
