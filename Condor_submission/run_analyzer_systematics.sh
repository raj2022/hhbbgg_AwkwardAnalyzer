#!/usr/bin/env bash
# ============================================================================
# run_analyzer.sh
#
# Wrapper executed BY CONDOR on a worker node -- runs completely
# independently of any lxplus login session, so it survives closing your
# laptop, switching machines, or reconnecting to a different lxplus node
# than the one you submitted from.
# ============================================================================
set -eo pipefail

echo "[run_analyzer.sh] Starting on host: $(hostname)"
echo "[run_analyzer.sh] Date: $(date)"

# --- Activate the micromamba environment ---
# (Migrated off the old miniforge3/conda install, which was corrupted
# and moved aside to miniforge3_broken. micromamba is a standalone
# binary, no base-env/profile-script dependency.)
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk

# --- Move to the working directory ---
# NOTE: switched from /afs/.../private (home AFS volume, 10GB quota --
# confirmed as the cause of the "Disk quota exceeded" failure on the
# histogram-writing step; this job's real output size, ~20GB+, cannot
# fit there regardless of cleanup) to Analysis/hhbbgg_AwkwardAnalyzer
# (a SEPARATE AFS volume with its own, much larger quota -- confirmed
# already holding 246GB there without issue). This also avoids the
# separate dependency-copying complexity from before, since the
# correctly-fixed regions.py/binning.py/normalisation.py/config/ already
# live here directly.
cd /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer
echo "[run_analyzer.sh] Working directory: $(pwd)"
echo "[run_analyzer.sh] Python: $(which python)"

# --- Pre-flight check ---
# Fail immediately and clearly if the script isn't actually here, rather
# than discovering it hours later buried in a Condor error log once the
# job finally gets scheduled.
if [ ! -f "hhbbgg_analyzer_with_systematics.py" ]; then
  echo "[run_analyzer.sh] [ERROR] hhbbgg_analyzer_with_systematics.py not found in $(pwd)."
  echo "[run_analyzer.sh] Copy it here before submitting, or edit this script's cd path."
  exit 1
fi

# --- Run the analyzer ---
# Update the -i paths / --tag below if they differ from your actual setup.
#
# --all-systematics ADDED: confirmed directly via --help that the
# analyzer defaults to nominal-only, and every systematic-variation file
# (jec_syst_Total_up/down, jer_syst_up/down, ScaleEB_*, ScaleEE_*,
# Smearing_up/down -- all confirmed present on disk under
# /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/<sample>/)
# would have been silently skipped without this flag, defeating the
# entire point of this run after the systematics pDNN scoring just
# completed. The --help text also notes systematic-variation files
# never scored by inference_PDnn.py lack a pDNN_score column and would
# crash this script -- confirm the completed scoring covers every
# systematic folder actually present before relying on this running
# cleanly all the way through.
#
# FIXED: every block below (including this commented 2024 one) was
# missing the trailing "\" after --all-systematics, so --skip-trees was
# being parsed as a SEPARATE shell command rather than part of this one.
# In the block that was actually active (2022 preEE, below), this meant
# the analyzer ran WITHOUT --skip-trees -- which triggered the
# skip-if-tree-output-already-exists resumability path in main() for
# every (sample, systematic) group (since trees from an earlier run
# already existed and were readable), so process_parquet_file() never
# ran for any file, HIST_CACHE stayed empty the whole run, and the
# histogram ROOT file was written out empty (695 bytes, zero
# histograms) with no error. All four blocks below now have the
# missing backslash added.
# python -u hhbbgg_analyzer_with_systematics.py \
#   --config-years 2024 --era All \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2024/merged/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/scored/ \
#   --tag DD_2024 \
#   --all-systematics \
#   --skip-trees

# --- 2022 preEE ---
# python -u hhbbgg_analyzer_with_systematics.py \
#   --config-years 2022 --era PreEE \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/preEE/merged/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/scored \
#   --tag DD_2022preEE \
#   --all-systematics \
#   --skip-trees

# --- 2022 postEE ---
# python -u hhbbgg_analyzer_with_systematics.py \
#   --config-years 2022 --era PostEE \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/scored/ \
#   --tag DD_2022postEE \
#   --all-systematics \
#   --skip-trees

# for 2023:
# --- 2023 preBPix ---
# python -u hhbbgg_analyzer_with_systematics.py \
#   --config-years 2023 --era preBPix \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2023/sim/preBPix/merged/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/ \
#   -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/scored/ \
#   --tag DD_2023preBPix \
#   --all-systematics \
#   --skip-trees

# --- 2023 postBPix ---
python -u hhbbgg_analyzer_with_systematics.py \
  --config-years 2023 --era postBPix \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2023/sim/postBPix/merged/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/scored/ \
  --tag DD_2023postBPix \
  --all-systematics \
  --skip-trees

echo "[run_analyzer.sh] Done: $(date)"