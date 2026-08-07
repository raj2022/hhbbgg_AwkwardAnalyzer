# #!/bin/bash

# echo "Starting the Analyzer script"
# echo "============================="

# # Running with DD bkg estimation adn tempelate fitting
# python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All \
#   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/ \
#   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/ \
#   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/ \
#   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/ \
#   --tag DD_CombinedAll

# echo "Analyzer script completed."



# echo "Starting the plotter"
# hhbbgg_Plotter.py
# echo "Plotter script completed"

# # moving the plotter from stacks plot to the folder

# DEST_DIR=~/sraj/www/CUA/HH-bbgg/all_plots/Data_MC

# echo "Starting plot copy process..."

# # Check if the destination directory exists
# if [ ! -d "$DEST_DIR" ]; then
#     echo "Destination folder not found. Creating: $DEST_DIR"
#     mkdir -p "$DEST_DIR"
# else
#     echo "Destination folder already exists: $DEST_DIR"
# fi


# # Copy index.php to the destination folder
# echo "Copying index.php to $DEST_DIR..."
# cp "$DEST_DIR/index.php" "$DEST_DIR"


# # Copy stack_plots folder
# echo "Copying stack_plots/ to $DEST_DIR..."
# cp -r stack_plots/ "$DEST_DIR/"


# echo "✅ All files copied successfully!"






#!/usr/bin/env bash
# ============================================================================
# run_full_pipeline.sh
#
# End-to-end driver for the X->YH->bbgg resonant search pipeline, covering
# everything built/fixed in this conversation:
#   1. Train pDNN
#   2. Train ttH killer
#   3. Score samples with both networks
#   4. Run the analyzer
#   5. Validate Data/MC
#   6. Event categorization
#
# Run with:  bash run_full_pipeline.sh
# Or select a single stage:  bash run_full_pipeline.sh score_pdnn
#
# NOTE ON OPEN ITEMS (not silently resolved by this script -- see the
# Analysis_Commands.md doc for full detail):
#   - --sigmoid-score for pDNN in step 6: only correct if pDNN_score is a
#     raw logit. Verify before trusting categorization results.
#   - --tth-cut 0.401 in step 6b: Tight working point, not yet validated
#     against Loose/Medium alternatives.
#   - --all-systematics is OFF throughout (nominal-only), as decided.
# ============================================================================
set -euo pipefail

# ----------------------------------------------------------------------------
# Paths -- edit these to match your setup
# ----------------------------------------------------------------------------
PDNN_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working"
PDNN_WC_DIR="${PDNN_DIR}/pDNN_Without_Correlation"
TTH_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/tth_killer"
ANALYZER_DIR="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer"
CATEGORIZATION_DIR="${ANALYZER_DIR}/event_categorization"

# Sample locations to score (edit/add as needed; signal and background can
# live in entirely different directories, see below)
SIGNAL_MERGED_DIR="/eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7/2022postEE/merged"
# Add more -i targets here if background/data live elsewhere, e.g.:
# BACKGROUND_DIR="/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/scored"

# Analyzer inputs (already-scored folders, one -i per era)
ANALYZER_INPUTS=(
  "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/scored/"
  "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/scored/"
  "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/scored/"
  "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/scored/"
)

TAG="DD_CombinedAll"
ANALYZER_TREE_ROOT="outputfiles/merged/${TAG}/hhbbgg_analyzer-v2-trees.root"

TTH_CUT_TIGHT="0.401"   # eps(ttH)=0.10; see open item above before adopting

STAGE="${1:-all}"

run_stage() {
  local name="$1"
  if [[ "$STAGE" == "all" || "$STAGE" == "$name" ]]; then
    return 0
  fi
  return 1
}

# ----------------------------------------------------------------------------
# 1. Train the pDNN (correlation-pruned version; swap in pDNN_v_WC.py /
#    PDNN_WC_DIR for the without-correlation entry point instead)
# ----------------------------------------------------------------------------
if run_stage train_pdnn; then
  echo "=== [1] Training pDNN (${PDNN_DIR}) ==="
  (cd "${PDNN_DIR}" && python pDNN_v2.py)
fi

# ----------------------------------------------------------------------------
# 2. Train the ttH killer
# ----------------------------------------------------------------------------
if run_stage train_tth; then
  echo "=== [2] Training ttH killer (${TTH_DIR}) ==="
  (cd "${TTH_DIR}" && python tth_killer_v2.py)
fi

# ----------------------------------------------------------------------------
# 3.1 Score samples with the trained pDNN
#     nominal-only, X>=300/Y>=90 by default; add --all-systematics later
# ----------------------------------------------------------------------------
if run_stage score_pdnn; then
  echo "=== [3.1] Scoring with pDNN (${PDNN_WC_DIR}) ==="
  (cd "${PDNN_WC_DIR}" && python inference_PDnn_updated.py \
    -i "${SIGNAL_MERGED_DIR}" \
    --recursive)

  echo "--- Checking for missing mass points ---"
  (cd "${PDNN_WC_DIR}" && python check_missing_masses.py \
    -i "${SIGNAL_MERGED_DIR}" \
    --require-file NOTAG_merged.parquet)
fi

# ----------------------------------------------------------------------------
# 3.2 Score samples with the trained ttH killer
#     Same folders scored in 3.1, so ttH_killer_score lands alongside
#     pDNN_score in the same files.
# ----------------------------------------------------------------------------
if run_stage score_tth; then
  echo "=== [3.2] Scoring with ttH killer (${TTH_DIR}) ==="
  (cd "${TTH_DIR}" && python inference_tth_killer.py \
    -i "${SIGNAL_MERGED_DIR}" \
    --model best_tth_killer.pt \
    --scaler scaler_tth.pkl)
fi

# ----------------------------------------------------------------------------
# 4. Run the analyzer (recursive, nominal-only by default)
# ----------------------------------------------------------------------------
if run_stage analyzer; then
  echo "=== [4] Running analyzer ==="
  cd "${ANALYZER_DIR}"
  input_args=()
  for d in "${ANALYZER_INPUTS[@]}"; do
    input_args+=(-i "$d")
  done
  python hhbbgg_analyzer_lxplus_par.py \
    --year 2023 --era All \
    "${input_args[@]}" \
    --tag "${TAG}"
fi

# ----------------------------------------------------------------------------
# 4.1 Validate Data/MC agreement
# ----------------------------------------------------------------------------
if run_stage plotter; then
  echo "=== [4.1] Data/MC validation ==="
  (cd "${ANALYZER_DIR}" && python hhbbgg_Plotter.py)
fi

# ----------------------------------------------------------------------------
# 5. Event categorization
# ----------------------------------------------------------------------------
if run_stage categorize_baseline; then
  echo "=== [5a] Categorization (pDNN-only baseline) ==="
  (cd "${ANALYZER_DIR}" && python event_categorization/build_pdnn_categories.py \
    --root "${ANALYZER_TREE_ROOT}" \
    --sr-sigma 2.0 --cr-sidebands 4 10 \
    --nmin 50 --min-gain 0.005 --max-bins 2 \
    --alpha-bins 60 \
    --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha_3cats \
    --write-categorized --sigmoid-score)
fi

if run_stage categorize_tth_split; then
  echo "=== [5b] Categorization (ttH-killer pre-split, Tight WP) ==="
  (cd "${ANALYZER_DIR}" && python event_categorization/build_pdnn_categories.py \
    --root "${ANALYZER_TREE_ROOT}" \
    --sr-sigma 2.0 --cr-sidebands 4 10 \
    --nmin 50 --min-gain 0.005 --max-bins 2 \
    --alpha-bins 60 \
    --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_tth_split_tight \
    --write-categorized --sigmoid-score \
    --tth-cut "${TTH_CUT_TIGHT}")
fi

echo "=== Pipeline stage(s) complete: ${STAGE} ==="

