#!/usr/bin/env bash
# =============================================================================
# run_inference_pair.sh
#
# Runs ONE (pDNN scoring -> ttH-killer) pair, for one year/era/sample-type
# input directory. Designed to be the Condor "executable" for a single job;
# run_full_inference_chain.sh's 14 independent pairs (6 signal + 8 bkg/data)
# each become one Condor job using this script, instead of running all 28
# steps serially on a single core.
#
# Arguments (all positional, all required):
#   $1  LABEL        short identifier for logging, e.g. "sig_2022_preEE"
#   $2  PDNN_INPUT   input directory for inference_PDnn_updated.py
#   $3  SCORED_DIR   the scored/ subfolder expected to exist afterward
#                     (used by check_scored_folder before running ttH-killer)
#
# Everything else (TTH_DIR, PDNN_DIR, model/scaler paths, micromamba setup)
# is fixed below to match run_full_inference_chain.sh's original values --
# edit these once here rather than in 14 separate submit-file argument lists.
#
# Exits non-zero on any failure (set -e), which Condor will record as a
# non-zero exit code in the job's .log file -- check that per-job rather
# than assuming success just because the job finished.
# =============================================================================
set -eo pipefail

LABEL="$1"
PDNN_INPUT="$2"
SCORED_DIR="$3"

TTH_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/tth_killer"
PDNN_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${LABEL}] $*"
}

check_scored_folder() {
    local scored_dir="$1"
    if [ ! -d "$scored_dir" ]; then
        log "[ERROR] Expected scored/ folder not found: $scored_dir"
        log "[ERROR] The pDNN step may have failed or written output elsewhere. Aborting."
        exit 1
    fi
    local nfiles
    nfiles=$(find "$scored_dir" -name "*.parquet" | wc -l)
    if [ "$nfiles" -eq 0 ]; then
        log "[ERROR] scored/ folder exists but contains no parquet files: $scored_dir"
        exit 1
    fi
    log "[OK] Found $nfiles parquet file(s) in $scored_dir"
}

log "=== Starting on host $(hostname), GPU(s): ${CUDA_VISIBLE_DEVICES:-none reported} ==="

log "=== Activating hhbbgg-awk environment ==="
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk

log "=== [pDNN] scoring: ${PDNN_INPUT} ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i "${PDNN_INPUT}" \
  --recursive --all-systematics
log "=== [pDNN] Done ==="

log "=== [ttH-killer]: ${SCORED_DIR} ==="
check_scored_folder "${SCORED_DIR}"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i "${SCORED_DIR}" \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [ttH-killer] Done ==="

log "=== PAIR COMPLETE: ${LABEL} ==="