# pDNN + ttH-killer Inference Chain — HTCondor GPU Parallelization

Parallelizes the CMS X→YH pDNN scoring + ttH-killer inference chain across
independent HTCondor GPU jobs, instead of running all years/eras serially
on a single core. The original serial approach (`run_full_inference_chain.sh`,
28 sequential steps) was projected at 20–30 days; splitting it into 14
independent Condor jobs (one GPU each) reduces wall time to roughly the
runtime of the single slowest pair, subject to GPU queue availability.

## Contents

| File | Purpose |
|---|---|
| `run_inference_pair.sh` | Condor executable: runs ONE (pDNN scoring → ttH-killer) pair for a single year/era/sample-type input directory. |
| `run_inference_pairs.sub` | HTCondor submit file queuing all 14 independent pairs (legacy multi-`queue` syntax). |
| `run_inference_pairs_v2.sub` | Same 14 pairs, using the modern `queue ... from (...)` table syntax (no deprecation warning). |
| `check_inference_progress.sh` | Diagnostic: reports per-step progress by inspecting `scored/` output folders directly (useful after an interrupted run, e.g. broken SSH pipe). |
| `run_full_inference_chain.sh` | Original serial 28-step script (kept for reference / fallback). |

## The 14 independent pairs

Each pair is a `pDNN scoring → ttH-killer` sequence for one year/era/sample-type.
All 14 are mutually independent and safe to run concurrently:

**Signal (6 pairs):** 2022 preEE, 2022 postEE, 2023 preBPix, 2023 postBPix, 2024, 2025

**Background/data (8 pairs):** 2022 sim preEE, 2022 sim postEE, 2023 sim postBPix,
2023 sim preBPix, 2023 data, 2022 data, 2024 sim, 2024 data

## Usage

```bash
# one-time setup
mkdir -p logs
chmod +x run_inference_pair.sh

# submit all 14 pairs
condor_submit run_inference_pairs_v2.sub

# monitor
condor_q -nobatch
tail -f logs/<label>.out          # live output for one pair, e.g. sig_2022_preEE

# after completion, verify real output was produced (see "Validating output" below)
grep "\[DONE\] Scored" logs/*.out
```

If the whole batch (or one job) needs to be paused without losing progress
(e.g. to fix a shared environment issue — see below), use:

```bash
condor_hold <cluster_id>       # pause
condor_release <cluster_id>    # resume — job restarts from scratch, not mid-file
```

**Do not modify the shared micromamba environment while jobs from it are
running.** A running Python process has already loaded its libraries into
memory; swapping package files on disk mid-run does not affect it, and can
crash it if files are removed out from under an active import. Hold jobs
first, make the change, then release.

## Diagnosing an interrupted run

If a run dies (e.g. SSH connection drops and the driving process wasn't
launched with `nohup`), don't assume progress is lost — check the actual
`scored/` output on disk before rerunning anything:

```bash
bash check_inference_progress.sh
```

This reports, per step: whether a process is still alive, how many
`.parquet` files exist in each expected output folder, and the most
recently modified file across the whole tree (likely the one that was
being written when the run was interrupted — check its size/validity
before trusting it, since a process killed mid-write can leave a
truncated file).

## Known issues and fixes

### 1. GPU allocated but never used (compute capability mismatch)

**Symptom:** `nvidia-smi` inside a running job shows a real GPU memory
allocation (e.g. a `python` process using ~330MiB), but `GPU-Util` stays
at 0% indefinitely, and/or the job log shows:

```
UserWarning: Found GPU0 Tesla V100... which is of compute capability (CC) 7.0.
...
CUDA error: no kernel image is available for execution on the device
CUDA error: CUBLAS_STATUS_ARCH_MISMATCH when calling `cublasCreate(handle)`
```

**Cause:** recent PyTorch wheels built against **CUDA 13.0** dropped
support for Volta (`sm_70`) GPUs entirely (Tesla V100 / V100S, common in
CERN's batch GPU pool). The CUDA-13 build simply has no compiled kernels
for this architecture — every real tensor operation fails.

Critically, **this failure can be silent**: `inference_PDnn_updated.py`
and `inference_ttH_killer.py` catch per-file errors internally and keep
going, so the job can exit with `ExitCode = 0` while having scored **zero
real rows** across every file. Always check actual row counts (see
"Validating output" below) — a clean exit code alone does not mean the
run succeeded.

**Fix:** PyTorch itself still supports Volta on its **CUDA 12.6** build;
only the CUDA-13 variant dropped it. Reinstall the same (or any recent)
PyTorch version against the `cu126` wheel index instead of the default:

```bash
micromamba activate hhbbgg-awk
pip uninstall torch torchvision torchaudio -y
pip install torch --index-url https://download.pytorch.org/whl/cu126 --break-system-packages
```

Verify before resubmitting anything:

```bash
python3 -c "
import torch
print('torch:', torch.__version__, '| cuda build:', torch.version.cuda)
print('supported archs:', torch.cuda.get_arch_list())
"
```

`sm_70` must appear in the printed architecture list. (Note:
`torch.cuda.is_available()` and a real `.cuda()` tensor op can only be
tested where a GPU is actually attached — plain lxplus login nodes have
no GPU, so this check needs to run inside a Condor job via
`condor_ssh_to_job`, not on the login node directly.)

### 2. Job held: cgroup memory limit exceeded

**Symptom:**

```
condor_q -held -af ClusterId ProcId HoldReason
9314166 12 Error from slot1_1@...: Job has gone over cgroup memory limit of 9000 megabytes.
Last measured usage: 14326 megabytes. Consider resubmitting with a higher request_memory.
```

**Cause:** `--all-systematics` scoring across a full mass grid can use
significantly more memory than a conservative initial `request_memory`
estimate — one background/data pair measured ~14.3GB actual usage against
an 8GB request.

**Fix:** raise the held job's memory request and release it (no need to
resubmit from scratch or touch other jobs):

```bash
condor_qedit <cluster_id>.<proc_id> RequestMemory 20000
condor_release <cluster_id>.<proc_id>
```

For future submissions, `run_inference_pairs_v2.sub`'s `request_memory`
should be set generously (≥16–20GB) given this measured footprint, rather
than tuned tightly per pair.

### 3. Foreground run killed by a broken SSH pipe

**Symptom:** `client_loop: send disconnect: Broken pipe` in your terminal,
and the driving script is gone.

**Cause:** running a long job in the foreground (no `nohup`) means a
`SIGHUP` from a dropped SSH connection kills the whole process tree.

**Fix:** always launch long-running drivers backgrounded and detached:

```bash
nohup bash <script>.sh > <script>.log 2>&1 &
disown
```

If a run was already lost this way, use `check_inference_progress.sh` to
find exactly where it stopped before deciding whether/how to resume.

## Validating output

Because failures in this pipeline can be silent (see Known Issue #1), always
confirm real rows were produced, not just a clean exit:

```bash
grep "\[DONE\] Scored" logs/*.out
```

Every line should read `Scored N file(s), M total rows` with **M > 0**.
Compare against `condor_history <cluster_id> -af ClusterId ProcId JobStatus ExitCode`
for exit codes, but treat `ExitCode = 0` as necessary, not sufficient — a
job can exit cleanly while having silently failed to score anything.

For a final spot-check on data quality (not just row counts), sample the
actual score columns from a freshly-written file:

```bash
python3 -c "
import pandas as pd
f = '<path to a scored .parquet file from this run>'
df = pd.read_parquet(f, columns=['pDNN_score', 'ttH_killer_score'])
print(df.describe())
print('rows:', len(df))
"
```

Both columns should show a real spread of values between 0 and 1 (not
all-NaN, all-zero, or all-identical), and the total row count should
match what's reported in `[DONE] Scored ... total rows`.

## Environment

All jobs activate a shared micromamba environment (`hhbbgg-awk`) from EOS:

```bash
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk
```

Confirmed working PyTorch build for this environment: `torch==2.14.0+cu126`
(any recent PyTorch release built against the `cu126` index should retain
Volta support — see Known Issue #1 before upgrading to a CUDA-13 build).