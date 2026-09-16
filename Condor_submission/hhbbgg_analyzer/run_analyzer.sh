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

# --- Activate the conda environment ---
# NOTE: my earlier fix (dropping -u from this script's own `set` line)
# was NOT actually sufficient -- confirmed by cluster 9167757 still
# hitting the identical ADDR2LINE error afterward. Root cause: conda's
# activate-binutils_linux-64.sh hook is SOURCED, not executed as a
# subprocess, so if IT internally uses `set -u` (or a `${VAR:?msg}`-style
# strict expansion), that changes the GLOBAL shell state independent of
# whatever flags this outer script started with -- my own `set` line
# doesn't control that. Real fix: pre-define the specific variable the
# hook references, so it's never "unbound" regardless of the hook's own
# strict-mode settings.
export ADDR2LINE="${ADDR2LINE:-}"
source /eos/user/s/sraj/software/miniforge3/etc/profile.d/conda.sh
conda activate hhbbgg-awk

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
python hhbbgg_analyzer_with_systematics.py \
  --config-years 2024 --era All \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/data/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/sim/scored/ \
  --tag DD_2024

echo "[run_analyzer.sh] Done: $(date)"
