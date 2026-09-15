#!/usr/bin/env bash
# generate_combine_condor_args.sh
#
# Discovers every real (mX, mY) point that has datacards built for the
# relevant year(s), for both the 2022+2023 and 2022+2023+2024
# combinations, and writes one line per job to combine_condor_args.txt:
#
#   <mass_tag> <years_comma_separated>
#
# e.g.:
#   mX600_mY300 2022,2023
#   mX600_mY300 2022,2023,2024
#
# Only includes a point in a given combination if EVERY required year's
# own datacard actually exists -- this is the same intersection logic
# used earlier tonight, just written out to a file instead of driving
# an inline loop, so run_combine_condor.sub can queue directly from it.

set -u
INVOKE_DIR="$(pwd)"
cd /afs/cern.ch/user/s/sraj/Analysis/finalfit_hhbbgg

MX_VALUES="300 320 350 400 450 500 550 600 650 700 750 800 850 900 950 1000"
ARGS_FILE="${INVOKE_DIR}/combine_condor_args.txt"
> "$ARGS_FILE"

TOTAL_2223=0
TOTAL_222324=0

for MX in $MX_VALUES; do
  MY_2022=$(ls outdir_2022/datacards/datacard_mX${MX}_mY*_cat0.txt 2>/dev/null | grep -oP 'mY\K[0-9]+' | sort -n)
  MY_2023=$(ls outdir_2023/datacards/datacard_mX${MX}_mY*_cat0.txt 2>/dev/null | grep -oP 'mY\K[0-9]+' | sort -n)
  MY_2024=$(ls outdir/datacards/datacard_mX${MX}_mY*_cat0.txt 2>/dev/null | grep -oP 'mY\K[0-9]+' | sort -n)

  MY_2223=$(comm -12 <(echo "$MY_2022") <(echo "$MY_2023"))
  MY_222324=$(comm -12 <(echo "$MY_2223") <(echo "$MY_2024"))

  for MY in $MY_2223; do
    echo "mX${MX}_mY${MY} 2022,2023" >> "$ARGS_FILE"
    TOTAL_2223=$((TOTAL_2223 + 1))
  done
  for MY in $MY_222324; do
    echo "mX${MX}_mY${MY} 2022,2023,2024" >> "$ARGS_FILE"
    TOTAL_222324=$((TOTAL_222324 + 1))
  done
done

echo "[INFO] Wrote ${ARGS_FILE}: ${TOTAL_2223} 2022+2023 job(s), ${TOTAL_222324} 2022+2023+2024 job(s), $((TOTAL_2223 + TOTAL_222324)) total."