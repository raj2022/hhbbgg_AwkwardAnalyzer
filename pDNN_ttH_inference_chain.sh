#!/usr/bin/env bash
# ============================================================================
# run_full_inference_chain.sh
#
# Runs the full pDNN + ttH-killer inference chain across all 2022/2023 sim
# and data samples, in order. Stops immediately on the first failure
# (set -e) rather than silently continuing with missing/incomplete input
# for later steps.
#
# Usage:
#   nohup bash run_full_inference_chain.sh > /afs/cern.ch/user/s/sraj/inference_chain.log 2>&1 &
#   disown
#
# Monitor with:
#   tail -f /afs/cern.ch/user/s/sraj/inference_chain.log
# ============================================================================
set -eo pipefail

TTH_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/tth_killer"
PDNN_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Verifies that a "scored" subfolder exists under the given input directory
# and contains at least one parquet file, before handing it to ttH-killer
# inference. Exits the whole script if not -- proceeding with a missing or
# empty scored/ folder would either crash inference_ttH_killer.py deep
# inside its own run or, worse, silently process zero files.
check_scored_folder() {
    local scored_dir="$1"
    if [ ! -d "$scored_dir" ]; then
        log "[ERROR] Expected scored/ folder not found: $scored_dir"
        log "[ERROR] The preceding pDNN step may have failed or written output elsewhere. Aborting."
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

log "=== Activating hhbbgg-awk environment ==="
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk

# ----------------------------------------------------------------------------
# Step 1: pDNN scoring, 2022 preEE sim
# ----------------------------------------------------------------------------
log "=== [1/16] pDNN scoring: 2022 preEE sim ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/ \
  --recursive --all-systematics
log "=== [1/16] Done ==="

# ----------------------------------------------------------------------------
# Step 2: ttH-killer on 2022 preEE (consumes step 1's output)
# ----------------------------------------------------------------------------
log "=== [2/16] ttH-killer: 2022 preEE ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [2/16] Done ==="

# ----------------------------------------------------------------------------
# Step 3: pDNN scoring, 2022 postEE sim
# ----------------------------------------------------------------------------
log "=== [3/16] pDNN scoring: 2022 postEE sim ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/ \
  --recursive --all-systematics
log "=== [3/16] Done ==="

# ----------------------------------------------------------------------------
# Step 4: ttH-killer on 2022 postEE (consumes step 3's output)
# ----------------------------------------------------------------------------
log "=== [4/16] ttH-killer: 2022 postEE ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [4/16] Done ==="

# ----------------------------------------------------------------------------
# Step 5: pDNN scoring, 2023 postBPix sim
# ----------------------------------------------------------------------------
log "=== [5/16] pDNN scoring: 2023 postBPix sim ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/ \
  --recursive --all-systematics
log "=== [5/16] Done ==="

# ----------------------------------------------------------------------------
# Step 6: ttH-killer, 2023 postBPix sim (consumes step 5's output)
# ----------------------------------------------------------------------------
log "=== [6/16] ttH-killer: 2023 postBPix sim ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [6/16] Done ==="

# ----------------------------------------------------------------------------
# Step 7: pDNN scoring, 2023 preBPix sim
# ----------------------------------------------------------------------------
log "=== [7/16] pDNN scoring: 2023 preBPix sim ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/ \
  --recursive --all-systematics
log "=== [7/16] Done ==="

# ----------------------------------------------------------------------------
# Step 8: ttH-killer, 2023 preBPix sim (consumes step 7's output)
# ----------------------------------------------------------------------------
log "=== [8/16] ttH-killer: 2023 preBPix sim ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [8/16] Done ==="

# ----------------------------------------------------------------------------
# Step 9: pDNN scoring, 2023 data
# ----------------------------------------------------------------------------
log "=== [9/16] pDNN scoring: 2023 data ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/ \
  --recursive --all-systematics
log "=== [9/16] Done ==="

# ----------------------------------------------------------------------------
# Step 10: ttH-killer, 2023 data (consumes step 9's output)
# ----------------------------------------------------------------------------
log "=== [10/16] ttH-killer: 2023 data ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [10/16] Done ==="

# ----------------------------------------------------------------------------
# Step 11: pDNN scoring, 2022 data
# ----------------------------------------------------------------------------
log "=== [11/16] pDNN scoring: 2022 data ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/ \
  --recursive --all-systematics
log "=== [11/16] Done ==="

# ----------------------------------------------------------------------------
# Step 12: ttH-killer, 2022 data (consumes step 11's output)
# ----------------------------------------------------------------------------
log "=== [12/16] ttH-killer: 2022 data ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [12/16] Done ==="

# ----------------------------------------------------------------------------
# Step 13: pDNN scoring, 2024 sim
# ----------------------------------------------------------------------------
log "=== [13/16] pDNN scoring: 2024 sim ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/ \
  --recursive --all-systematics
log "=== [13/16] Done ==="

# ----------------------------------------------------------------------------
# Step 14: ttH-killer, 2024 sim (consumes step 13's output)
# ----------------------------------------------------------------------------
log "=== [14/16] ttH-killer: 2024 sim ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [14/16] Done ==="

# ----------------------------------------------------------------------------
# Step 15: pDNN scoring, 2024 data
# ----------------------------------------------------------------------------
log "=== [15/16] pDNN scoring: 2024 data ==="
cd "$PDNN_DIR"
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/ \
  --recursive --all-systematics
log "=== [15/16] Done ==="

# ----------------------------------------------------------------------------
# Step 16: ttH-killer, 2024 data (consumes step 15's output)
# ----------------------------------------------------------------------------
log "=== [16/16] ttH-killer: 2024 data ==="
check_scored_folder "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/scored/"
cd "$TTH_DIR"
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
log "=== [16/16] Done ==="

log "=== FINAL CHECK: confirming all scored/ folders are present ==="
for d in \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/scored/" \
  "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/scored/"
do
    if [ -d "$d" ]; then
        n=$(find "$d" -name "*.parquet" | wc -l)
        log "  [OK] $d ($n parquet files)"
    else
        log "  [MISSING] $d"
    fi
done

log "=== ALL STEPS COMPLETE ==="