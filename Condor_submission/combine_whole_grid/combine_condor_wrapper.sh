#!/usr/bin/env bash
# combine_condor_wrapper.sh
#
# Executed BY EACH CONDOR JOB on a worker node. Arguments (from the .sub
# file's "arguments" line, driven by combine_condor_args.txt):
#   $1 = mass_tag, e.g. "mX600_mY300"
#   $2 = years, comma-separated, e.g. "2022,2023" or "2022,2023,2024"
#
# Sets up ONLY cmsenv (confirmed sufficient for run_multiyear_combine.sh
# itself -- NOT the mamba hhbbgg-awk environment, which is only needed
# for the earlier workspace-building steps, already complete by the
# time this runs).

set -u

MASS_TAG="$1"
YEARS_CSV="$2"
YEARS_SPACE="${YEARS_CSV//,/ }"

BASE_DIR="/afs/cern.ch/user/s/sraj/Analysis/finalfit_hhbbgg"
CMSSW_SRC="/eos/home-s/sraj/Work_/CUA_20--/Analysis/finalfit_hhbbgg/CMSSW_14_1_0_pre4/src"

CATS_2022="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022_mc_boundary_catchall/event_categories.json"
CATS_2023="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023_mc_boundary_catchall/event_categories.json"
CATS_2024="/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024_mc_boundary_catchall/event_categories.json"

echo "[INFO] Job starting: mass_tag=${MASS_TAG}, years=${YEARS_SPACE}"
echo "[INFO] Running on host: $(hostname)"

cd "${CMSSW_SRC}" || { echo "[ERROR] Could not cd to CMSSW src area: ${CMSSW_SRC}"; exit 1; }
source /cvmfs/cms.cern.ch/cmsset_default.sh
eval `scramv1 runtime -sh`
echo "[INFO] cmsenv done. which combine: $(which combine 2>&1)"

cd "${BASE_DIR}" || { echo "[ERROR] Could not cd to base dir: ${BASE_DIR}"; exit 1; }

CATS_ARGS=""
for Y in ${YEARS_SPACE}; do
  case "$Y" in
    2022) CATS_ARGS="${CATS_ARGS} --categories-json-override 2022=${CATS_2022}" ;;
    2023) CATS_ARGS="${CATS_ARGS} --categories-json-override 2023=${CATS_2023}" ;;
    2024) CATS_ARGS="${CATS_ARGS} --categories-json-override 2024=${CATS_2024}" ;;
  esac
done

bash run_multiyear_combine.sh --mass-tag "${MASS_TAG}" --years ${YEARS_SPACE} --skip-impacts ${CATS_ARGS}
EXIT_CODE=$?

echo "[INFO] Job finished: mass_tag=${MASS_TAG}, years=${YEARS_SPACE}, exit_code=${EXIT_CODE}"
exit ${EXIT_CODE}