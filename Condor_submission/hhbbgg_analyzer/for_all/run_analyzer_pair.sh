#!/usr/bin/env bash
# =============================================================================
# run_analyzer_pair.sh
#
# Runs ONE hhbbgg_analyzer_with_systematics.py invocation for a single
# year/era, with a fixed, shared output base directory
# (/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/run_All/)
# via the script's --outdir flag, instead of the default AFS-relative
# "outputfiles" directory.
#
# Arguments (all positional; use the literal string NONE for any input
# that doesn't apply to a given job, e.g. no data for a 2022 PreEE-only
# signal+background run):
#   $1  TAG          output tag, e.g. "DD_2022preEE"
#   $2  ERA          PreEE | PostEE | preBPix | postBPix | All
#   $3  YEARS        --config-years value, e.g. "2022"
#   $4  SIGNAL_DIR   signal input directory, or NONE
#   $5  BKG_DIR      background (sim) input directory, or NONE
#   $6  DATA_DIR     data input directory, or NONE
#
# ACTION ITEM: ANALYZER_DIR below is assumed to match the naming pattern
# used elsewhere in this project (TTH_DIR/PDNN_DIR under
# /afs/cern.ch/user/s/sraj/Analysis/...) but has NOT been directly
# confirmed. Update it to wherever hhbbgg_analyzer_with_systematics.py,
# regions.py, variables.py, binning.py, config/, and normalisation.py
# actually live before submitting.
# =============================================================================
set -eo pipefail

TAG="$1"
ERA="$2"
YEARS="$3"
SIGNAL_DIR="$4"
BKG_DIR="$5"
DATA_DIR="$6"

ANALYZER_DIR="/afs/cern.ch/user/s/sraj/private"
OUTDIR="/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/run_All/"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${TAG}] $*"
}

log "=== Starting on host $(hostname) ==="

log "=== Activating hhbbgg-awk environment ==="
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk

cd "$ANALYZER_DIR"

# Build the -i flag list, skipping any input marked NONE.
INPUT_ARGS=()
for dir in "$SIGNAL_DIR" "$BKG_DIR" "$DATA_DIR"; do
    if [ "$dir" != "NONE" ]; then
        INPUT_ARGS+=(-i "$dir")
    fi
done

if [ "${#INPUT_ARGS[@]}" -eq 0 ]; then
    log "[ERROR] No valid input directories given (all three were NONE). Aborting."
    exit 1
fi

log "=== Running analyzer: tag=${TAG} era=${ERA} years=${YEARS} ==="
log "    inputs: ${INPUT_ARGS[*]}"
log "    outdir: ${OUTDIR}"

python hhbbgg_analyzer_with_systematics.py \
  "${INPUT_ARGS[@]}" \
  --config-years "${YEARS}" \
  --era "${ERA}" \
  --tag "${TAG}" \
  --outdir "${OUTDIR}" \
  --all-systematics

log "=== DONE: ${TAG} ==="