# HTCondor Command Reference

Quick reference for submitting, monitoring, and managing jobs on the CERN lxplus/Condor batch system.

## Submitting jobs

```bash
condor_submit myjob.sub
```
Submits a job described by a `.sub` file. Prints the assigned `ClusterId` on success — note it down, or grab it later with `condor_q`.

```bash
condor_submit -interactive
```
Starts an interactive session on a worker node — useful for testing environment setup (e.g. confirming `micromamba activate` works on the actual worker) before submitting a real batch job.

---

## Monitoring jobs

```bash
condor_q
```
Lists your own currently queued/running jobs: `OWNER`, `BATCH_NAME`, `SUBMITTED`, `DONE`/`RUN`/`IDLE`/`TOTAL`, `JOB_IDS`.

```bash
condor_q <ClusterId>.<ProcId>
```
Status of one specific job, e.g. `condor_q 9245882.0`.

```bash
condor_q <ClusterId>.0 -af Cmd Args Iwd
```
Shows the actual executable (`Cmd`), its arguments (`Args`), and initial working directory (`Iwd`) for a job — essential for telling apart multiple queued jobs that otherwise look identical in the plain `condor_q` listing.

```bash
condor_q <ClusterId>.0 -af Out Err Log
```
Shows the paths to a job's stdout, stderr, and Condor event log files, as defined in its submit file.

```bash
condor_q <ClusterId>.0 -af RemoteHost RemoteWallClockTime ResidentSetSize_RAW CumulativeSlotTime
```
Live resource usage: which worker node it's on, how long it's run, memory usage.

```bash
condor_history <ClusterId>.0 -af Cmd Args Iwd
```
Same idea as `condor_q -af`, but works for jobs that have already finished (removed from the live queue).

---

## Live output ⚠️

CERN IT deprecated `stream_output`/`stream_error` in the submit file (end of Nov 2025) — job stdout/stderr now only populate the output/error files at job completion, not while running. Use `condor_tail` instead:

```bash
condor_tail <ClusterId>.<ProcId>
```
Shows the current tail of a running job's stdout.

```bash
condor_tail -follow <ClusterId>.<ProcId>
```
Keeps tailing live, like `tail -f`, until you interrupt it (Ctrl+C). This is the closest equivalent to old-style streaming.

```bash
condor_tail -stderr <ClusterId>.<ProcId>
```
Tails stderr instead of stdout.

---

## Removing / managing jobs

```bash
condor_rm <ClusterId>.<ProcId>
```
Removes one specific job.

```bash
condor_rm <ClusterId>.0 <ClusterId2>.0
```
Removes multiple jobs in one call.

```bash
condor_rm <ClusterId>
```
Removes an entire cluster (all ProcIds under that ClusterId, if it was a `queue N` submission).

```bash
condor_rm $(whoami)
```
Removes **all** of your own queued/running jobs — use with caution.

```bash
condor_hold <ClusterId>.<ProcId>
```
Pauses a job without removing it (stays in queue, marked Held).

```bash
condor_release <ClusterId>.<ProcId>
```
Resumes a previously held job.

---

## Submit file essentials (for reference)

```ini
universe                = vanilla
executable              = run_analyzer.sh
request_cpus            = 4
request_memory          = 16GB
+JobFlavour              = "workday"   # espresso(20m)/microcentury(1h)/longlunch(2h)/workday(8h)/tomorrow(1d)/testmatch(3d)/nextweek(1w)

log                     = logs/job_$(ClusterId).log
output                  = logs/job_$(ClusterId).log.out
error                   = logs/job_$(ClusterId).log.err

should_transfer_files   = NO
getenv                  = False

queue
```

Notes:
- `stream_output`/`stream_error` are **no longer valid** — omit them, use `condor_tail` for live progress instead.
- `output`/`error`/`log` files only populate fully once the job finishes (or via `condor_tail` while running).
- `mkdir -p logs` before submitting, or the job will fail if the directory doesn't exist.

---

## Common troubleshooting patterns

**"Why is my job idle and not starting?"**
```bash
condor_q -analyze <ClusterId>.0
```
Explains why a job hasn't matched to a slot yet (resource mismatch, priority, etc.).

**"Which node is my job actually running on?"**
```bash
condor_q <ClusterId>.0 -af RemoteHost
```

**"I submitted the same thing twice by accident — which is which?"**
```bash
condor_q <ClusterId1>.0 -af Cmd Args Iwd
condor_q <ClusterId2>.0 -af Cmd Args Iwd
```
Compare `Args`/`Iwd` between the two to tell them apart before deciding which to `condor_rm`.

**"Job finished/died — what happened?"**
```bash
condor_history <ClusterId>.0 -af ExitCode HoldReason
cat logs/job_<ClusterId>.log      # Condor's own event log — submitted/executing/terminated events
cat logs/job_<ClusterId>.log.err  # your script's actual stderr (only populated after completion)
```