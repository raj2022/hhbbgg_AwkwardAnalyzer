#!/usr/bin/env bash
# workspace_condor_wrapper.sh
#
# Executed BY EACH CONDOR JOB on a worker node. One job = one (mX, year)
# pair -- NOT a full mX value across all three years, since
# run_multiyear_workspaces.sh processes years sequentially within a
# single invocation. Splitting by year too (not just mX) means each job
# only does 1/3 of the work and all (mX, year) pairs can run genuinely
# in parallel, rather than each mX job still taking as long as a full
# 3-year sequential build.
#
# Arguments (from the .sub file's "arguments" line, driven by
# workspace_condor_args.txt):
#   $1 = mass_x, e.g. "450"
#   $2 = year, e.g. "2022", "2023", or "2024" (single year only)
#
# Activation sequence confirmed directly from the user's own
# run_analyzer.sh (already used successfully in a non-interactive
# context) -- copied verbatim, not guessed.

set -eo pipefail

MASS_X="$1"
YEAR="$2"

echo "[workspace_condor_wrapper.sh] Starting on host: $(hostname)"
echo "[workspace_condor_wrapper.sh] Date: $(date)"
echo "[workspace_condor_wrapper.sh] mass_x=${MASS_X}, year=${YEAR}"

# --- Activate the micromamba environment ---
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk

BASE_DIR="/afs/cern.ch/user/s/sraj/Analysis/finalfit_hhbbgg"

case "$YEAR" in
  2022) CATS_JSON="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022_mc_boundary_catchall/event_categories.json" ;;
  2023) CATS_JSON="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023_mc_boundary_catchall/event_categories.json" ;;
  2024) CATS_JSON="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024_mc_boundary_catchall/event_categories.json" ;;
  *) echo "[ERROR] Unrecognized year: ${YEAR}"; exit 1 ;;
esac

cd "${BASE_DIR}" || { echo "[ERROR] Could not cd to base dir: ${BASE_DIR}"; exit 1; }

bash run_multiyear_workspaces.sh --mass-x "${MASS_X}" --years "${YEAR}" \
  --score-transform ftilde \
  --categories-json-override "${YEAR}=${CATS_JSON}"
EXIT_CODE=$?

echo "[workspace_condor_wrapper.sh] Finished: mass_x=${MASS_X}, year=${YEAR}, exit_code=${EXIT_CODE}"
exit ${EXIT_CODE}