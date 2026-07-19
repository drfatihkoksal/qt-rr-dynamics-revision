#!/bin/bash
# Parallel resumable downloader for LTST DB and EDB from PhysioNet.
set -uo pipefail

download_db() {
  local db=$1
  local outdir=$2
  mkdir -p "$outdir"
  base="https://physionet.org/files/$db/1.0.0"

  # top-level metadata files
  for f in RECORDS ANNOTATORS SHA256SUMS.txt LICENSE.txt README ANNOTATORS.txt; do
    curl -sf -o "$outdir/$f" "$base/$f" 2>/dev/null
  done

  recs=$(curl -s "$base/RECORDS")
  echo "$recs" > "$outdir/RECORDS"

  # build list of all needed file extensions per record; probe common ones
  exts="hea dat atr ari qrs stj sta"
  jobfile=$(mktemp)
  for r in $recs; do
    for e in $exts; do
      echo "$base/$r.$e|$outdir/$r.$e" >> "$jobfile"
    done
  done

  cat "$jobfile" | xargs -P 6 -I{} bash -c '
    url="${1%%|*}"; out="${1##*|}";
    if [ ! -s "$out" ]; then
      curl -sf -o "$out" "$url" || rm -f "$out"
    fi
  ' _ {}
  rm -f "$jobfile"
  echo "DONE $db"
}

download_db "$1" "$2"
