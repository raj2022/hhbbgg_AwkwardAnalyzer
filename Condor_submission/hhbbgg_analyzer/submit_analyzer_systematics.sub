# ============================================================================
# submit_analyzer.sub
#
# Runs the analyzer as a Condor batch job -- fully independent of any
# lxplus login session, so you can close your laptop, switch machines,
# and check back later from anywhere.
#
# Submit with:  condor_submit submit_analyzer.sub
# Monitor with: condor_q
#               tail -f logs/analyzer.out   (live progress)
# ============================================================================

universe                = vanilla
executable              = run_analyzer.sh

# --- Resources ---
# CPU-only (no GPU needed here, unlike the pDNN inference job).
#
# BUMPED from the nominal-only run's 8GB/"tomorrow": this run processes
# every confirmed systematic-variation subfolder per sample (jec_syst_
# Total_up/down, jer_syst_up/down, ScaleEB_*, ScaleEE_*, Smearing_up/
# down, on top of nominal) via --all-systematics -- roughly an order of
# magnitude more data read and processed than before. 16GB/"testmatch"
# (3 days) is a reasonable, conservative starting point given that
# increase, not a precisely measured requirement -- if this run
# comfortably finishes with memory to spare, these can be tuned back
# down for future submissions; if it gets OOM-killed or hits the time
# limit, that's real evidence for the next value, not a guess.
request_cpus              = 4
request_memory             = 16GB
+JobFlavour                = "testmatch"

# --- Logging ---
# Create the logs/ folder before submitting: mkdir -p logs
log                       = logs/analyzer_$(ClusterId).log
output                    = logs/analyzer_$(ClusterId).log.out
error                     = logs/analyzer_$(ClusterId).log.err

# --- Environment / file transfer ---
# AFS and EOS are both directly accessible on CERN worker nodes -- no
# file transfer directives needed.
should_transfer_files     = NO
getenv                    = False

queue