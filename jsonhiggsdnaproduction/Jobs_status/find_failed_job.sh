#!/usr/bin/env bash

BASE_DIR="/afs/cern.ch/user/s/sraj/private/.higgs_dna_vanilla_lxplus"
DATE_TAG="20260109"

SUCCESS_PATTERN="Successfully completed|Return code 0|Finished processing"

> failed_jobs.txt
> failed_jobs_with_reason.txt

for d in ${BASE_DIR}/My_Json_*_${DATE_TAG}_*; do
  [ -d "$d/jobs" ] || continue

  for sub in "$d"/jobs/*.sub; do
    base=$(basename "$sub" .sub)
    out="$d/jobs/$base.out"
    err="$d/jobs/$base.err"

    reason=""

    # Case 1: missing logs
    if [[ ! -f "$out" || ! -f "$err" ]]; then
      reason="missing_log"
    # Case 2: non-empty error file
    elif [[ -s "$err" ]]; then
      reason="non_empty_err"
    # Case 3: output exists but never finished
    elif ! grep -Eq "$SUCCESS_PATTERN" "$out"; then
      reason="no_success_marker"
    fi

    if [[ -n "$reason" ]]; then
      echo "$sub" >> failed_jobs.txt
      echo "$sub  $reason" >> failed_jobs_with_reason.txt
    fi
  done
done

echo "Done."
echo "Total failed jobs: $(wc -l < failed_jobs.txt)"
