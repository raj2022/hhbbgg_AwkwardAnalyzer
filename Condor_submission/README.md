# Condor Submission — hhbbgg Analyzer

Runs `hhbbgg_analyzer_with_systematics.py` as an HTCondor batch job,
independent of any lxplus login session — survives closing your laptop,
switching machines, or reconnecting to a different lxplus node than the
one you submitted from.

---

## Files

| File | Purpose |
|---|---|
| `run_analyzer.sh` | The actual wrapper Condor executes on a worker node: activates the conda environment, `cd`s to the working directory, runs the analyzer. |
| `submit_analyzer.sub` | HTCondor submit description: resources, log file locations. |

---

## Required setup — dependencies that must sit alongside the analyzer script

`hhbbgg_analyzer_with_systematics.py` is not self-contained. Confirmed by
direct trial and error (see "Debugging history" below), it needs the
following in the **same directory** it's run from:

```
private/                              (or wherever you run from)
├── hhbbgg_analyzer_with_systematics.py
├── regions.py
├── binning.py
├── variables.py
├── normalisation.py
└── config/                           <- a PACKAGE (directory), not a
    ├── __init__.py                      single file -- copy the whole
    ├── utils.py                         thing with `cp -r`, not
    └── config.py                        individual files
```

Copy everything over:
```bash
cd /afs/cern.ch/user/s/sraj/private
cp /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/regions.py .
cp /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/binning.py .
cp /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/variables.py .
cp /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/normalisation.py .
cp -r /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/config .
```

**Verify imports resolve before submitting a job** (catches a missing
dependency in seconds instead of after a Condor queue wait):
```bash
python -c "
from config.utils import lVector
from config.config import RunConfig
from normalisation import getXsec, getLumi
from regions import get_mask_preselection
from variables import vardict
from binning import binning
print('all imports OK')
"
```

---

## Submitting

```bash
mkdir -p logs
chmod +x run_analyzer.sh
condor_submit submit_analyzer.sub
```

Note the cluster ID printed (e.g. `1 job(s) submitted to cluster 9167838.`)
— you'll need it to check logs and history for *this specific* run.

---

## Monitoring

```bash
condor_q                          # DONE / RUN / IDLE / HELD status
condor_tail <ClusterId>           # stream a RUNNING job's live stdout
                                   # directly from the worker node --
                                   # works even before anything's been
                                   # flushed to the local log file
condor_tail -follow <ClusterId>   # same, but keeps following
```

Log files use `$(ClusterId)` in their names, so each submission gets its
own set rather than overwriting the previous run's:
```bash
cat logs/analyzer_<ClusterId>.log.out   # script's own stdout
cat logs/analyzer_<ClusterId>.log.err   # errors / tracebacks
cat logs/analyzer_<ClusterId>.log       # Condor's own job event log
```

**Direct progress signal, independent of stdout**: watch the actual
output file appear/grow:
```bash
watch -n 30 'ls -la /afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024/'
```

**After it finishes**, get the real exit status (jobs disappear from
`condor_q` once done — completed *or* failed — so `condor_q` alone can't
tell you which):
```bash
condor_history <ClusterId> -long | grep -i 'ExitCode\|HoldReason\|RemoveReason\|JobStartDate\|CompletionDate'
```
`ExitCode = 0` means success; anything else, check `.log.err`.

---

## Debugging history — real issues hit and fixed, in order

Kept here so the same mistakes aren't rediscovered from scratch next time.

1. **`ADDR2LINE: unbound variable`, job dies in ~6-10 seconds.**
   Conda's own `activate-binutils_linux-64.sh` activation hook references
   a variable that isn't always pre-defined. Originally attempted fix
   (dropping `-u` from this script's own `set -euo pipefail`) was
   **not fully sufficient** — a `source`d script can independently
   re-enable strict mode for the whole shell session regardless of the
   caller's own flags. Actual fix: pre-define the variable so it's never
   "unbound" in the first place —
   `export ADDR2LINE="${ADDR2LINE:-}"` before sourcing `conda.sh`.

2. **Job disappears from `condor_q` right after resubmitting, "can't
   find anything in the logs."**
   The original submit file used static log filenames
   (`logs/analyzer.out`, etc.) — every resubmission silently overwrote
   the previous run's logs. Fixed by using `$(ClusterId)` in the log
   paths, so every submission gets uniquely-named logs.

3. **`ModuleNotFoundError: No module named 'config'`, job runs ~72
   seconds before dying** (i.e. gets past conda activation and starts
   the analyzer, then fails on the first local import).
   The analyzer imports `from config.utils import lVector` and
   `from config.config import RunConfig` — a local **package**
   (directory), not just single-file modules like `regions.py`/
   `binning.py`. Only the single-file dependencies had been copied to
   the run directory; the `config/` package was missed. Fixed by
   copying the whole directory (`cp -r`) alongside the single files.

**General lesson embedded in all three**: a "job fails almost
immediately" symptom can have very different root causes depending on
*how long* it ran before dying — check `TimeExecute`/`JobStartDate` vs
`CompletionDate` in `condor_history -long`, since a 6-second death (env
setup) and a 72-second death (script started, hit an import) point to
completely different places to look.