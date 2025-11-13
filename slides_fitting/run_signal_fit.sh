#!/bin/bash
# Usage: ./run_signal_fit.sh X1000_Y90
# Example: ./run_signal_fit.sh X1200_Y95

set -euo pipefail

SIGNAL="$1"

if [ -z "$SIGNAL" ]; then
  echo "❌ Error: please provide a signal name (e.g. X1000_Y90)"
  echo "Usage: ./run_signal_fit.sh X1000_Y90"
  exit 1
fi

# Extract mass numbers for filenames
MASS_X=$(echo "$SIGNAL" | sed -E 's/X([0-9]+)_Y([0-9]+)/\1/')
MASS_Y=$(echo "$SIGNAL" | sed -E 's/X([0-9]+)_Y([0-9]+)/\2/')

# Destination base on EOS
EOS_BASE="/eos/user/s/sraj/www/CUA/HH-bbgg/all_plots/fitting"
EOS_TARGET="${EOS_BASE}/${MASS_X}_${MASS_Y}"

# Local output dirs used by your python scripts (kept)
OUT_MGG="outputs/signal_fits"
OUT_MJJ="outputs/signal_fits_mjj"
OUT_MJJ_BY_MASS="outputs/signal_fits_mjj_by_mass/${MASS_X}"
WS2D_DIR="Signal/SignalWS_2D"
DATACARD_DIR="datacard"

echo "======================================"
echo " Running signal fit for: $SIGNAL"
echo "======================================"

# --- Ensure EOS directory exists now so we can copy after each step ---
echo "▶ Making EOS target dir: ${EOS_TARGET}"
mkdir -p "${EOS_TARGET}"

# Copy index.php if it exists in base EOS path
INDEX_FILE="${EOS_BASE}/index.php"
if [ -f "${INDEX_FILE}" ]; then
  cp -v "${INDEX_FILE}" "${EOS_TARGET}/"
  echo "✅ Copied index.php to ${EOS_TARGET}"
else
  echo "⚠️ No index.php found at ${INDEX_FILE} — skipping copy."
fi

echo "✅ EOS target ready."


# --- 1. Setup CMS environment ---
echo "▶ Setting up CMS environment..."
cmsenv
echo "✅ CMS environment ready."

# --- 2. Run signal mgg fit ---
echo "▶ Fitting signal mgg for $SIGNAL ..."
python3 Signal/fit_signal_shapes_for_slides.py \
  --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --edges 0.6829967608364195 0.6881541571642115 \
  --cats 0 1 2 \
  --mgg-min 115 \
  --mgg-max 135 \
  --outdir "${OUT_MGG}" \
  --only-signal "$SIGNAL"
echo "✅ mgg fit done for $SIGNAL"

# copy mgg outputs if present
if [ -d "${OUT_MGG}" ]; then
  echo "▶ Copying mgg outputs to EOS..."
  rsync -av --delete "${OUT_MGG}/" "${EOS_TARGET}/signal_fits/" || true
  echo "✅ mgg outputs copied to ${EOS_TARGET}/signal_fits/"
else
  echo "⚠️ mgg outdir ${OUT_MGG} not found — skipping copy."
fi

# --- 3. Run signal mjj fit ---
echo "▶ Fitting signal mjj for $SIGNAL ..."
python Signal/fit_signal_mjj_for_slides.py \
  --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --edges-json outputs/categories_alpha_3cats/event_categories.json \
  --mjj-min 90 \
  --mjj-max 180 \
  --outdir "${OUT_MJJ}" \
  --only-signal "$SIGNAL"
echo "✅ mjj fit done for $SIGNAL"

# copy mjj outputs (global) and by-mass if present
if [ -d "${OUT_MJJ}" ]; then
  echo "▶ Copying mjj outputs to EOS..."
  rsync -av --delete "${OUT_MJJ}/" "${EOS_TARGET}/signal_fits_mjj/" || true
  echo "✅ mjj outputs copied to ${EOS_TARGET}/signal_fits_mjj/"
else
  echo "⚠️ mjj outdir ${OUT_MJJ} not found — skipping copy."
fi

# If your mjj script writes a per-mass subdir (you referenced it later), copy that too:
if [ -d "${OUT_MJJ_BY_MASS}" ]; then
  echo "▶ Copying mjj-by-mass outputs (${OUT_MJJ_BY_MASS}) to EOS..."
  rsync -av --delete "${OUT_MJJ_BY_MASS}/" "${EOS_TARGET}/signal_fits_mjj_by_mass/${MASS_X}/" || true
  echo "✅ mjj-by-mass outputs copied to ${EOS_TARGET}/signal_fits_mjj_by_mass/${MASS_X}/"
else
  echo "ℹ️ No mjj-by-mass dir ${OUT_MJJ_BY_MASS} found (this may be normal)."
fi

# --- 4. Create 2D signal workspace ---
echo "▶ Creating 2D signal workspace for $SIGNAL ..."
python3 Signal/make_signal_ws_2D_from_jsons.py \
  --mgg_json "${OUT_MGG}/signal_shape_params.json" \
  --mjj_json "${OUT_MJJ_BY_MASS}/signal_mjj_params.json" \
  --year 2018 \
  --proc NMSSM \
  --outdir "${WS2D_DIR}" \
  --mgg 115,135 \
  --mjj 90,180 \
  --verbose
echo "✅ 2D workspace created for $SIGNAL"

# copy WS2D if present
if [ -d "${WS2D_DIR}" ]; then
  echo "▶ Copying 2D workspace files to EOS..."
  rsync -av --delete "${WS2D_DIR}/" "${EOS_TARGET}/SignalWS_2D/" || true
  echo "✅ 2D workspace copied to ${EOS_TARGET}/SignalWS_2D/"
else
  echo "⚠️ ${WS2D_DIR} not found — skipping copy."
fi

# --- 5. Convert datacard to workspace ---
echo "▶ Creating datacard workspace for ${MASS_X}_${MASS_Y} ..."
text2workspace.py "${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}.txt" -o "${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}_${MASS_Y}.root"
echo "✅ Datacard workspace created: ${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}_${MASS_Y}.root"

# copy datacard workspace
if [ -e "${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}_${MASS_Y}.root" ]; then
  mkdir -p "${EOS_TARGET}/datacard"
  cp -v "${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}_${MASS_Y}.root" "${EOS_TARGET}/datacard/"
  echo "✅ Datacard workspace copied to ${EOS_TARGET}/datacard/"
else
  echo "⚠️ Datacard root file not found — skipping copy."
fi

# --- 6. Run combine limit ---
echo "▶ Running combine for ${MASS_X}_${MASS_Y} ..."
combine -M AsymptoticLimits "${DATACARD_DIR}/${MASS_X}/comb_mass${MASS_X}_${MASS_Y}.root" -n _asymp
echo "✅ Combine done for ${MASS_X}_${MASS_Y}"

# copy combine output (the combine tool creates files in the working dir with names containing _asymp)
echo "▶ Collecting combine output files..."
# collect matching files produced by combine and copy them if they exist
shopt -s nullglob
COMB_FILES=(higgsCombine*_asymp*.root *.log *.txt)
if [ ${#COMB_FILES[@]} -gt 0 ]; then
  mkdir -p "${EOS_TARGET}/combine_outputs"
  for f in "${COMB_FILES[@]}"; do
    cp -v "$f" "${EOS_TARGET}/combine_outputs/" || true
  done
  echo "✅ Combine outputs copied to ${EOS_TARGET}/combine_outputs/"
else
  echo "ℹ️ No combine output files found in current directory matching patterns — skipping."
fi
shopt -u nullglob

echo "======================================"
echo "✅ All steps completed for $SIGNAL"
echo "Output datacard: ${DATACARD_DIR}/comb_mass${MASS_X}_${MASS_Y}.root"
echo "EOS copy location: ${EOS_TARGET}"
echo "======================================"
