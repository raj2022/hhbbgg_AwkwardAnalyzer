# V7 HiggsDNA Sample Production — 2022 & 2023 (Custom EOS Layout)

HiggsDNA link: https://gitlab.cern.ch/cms-analysis/general/HiggsDNA/-/tree/HHbbgg_v7_parquet_dask?ref_type=heads

---

## 0. Setting up HiggsDNA (latest update, v7 branch)

```bash
git clone https://gitlab.cern.ch/cms-analysis/general/HiggsDNA.git
cd HiggsDNA
git fetch origin
git switch --track origin/HHbbgg_v7_parquet_dask   # preferred working branch
pip install -e .[dev,test]
cd higgs_dna/
python scripts/pull_files.py --all
```

- `git switch --track origin/HHbbgg_v7_parquet_dask` checks out the `HHbbgg_v7_parquet_dask` branch and sets it to track the remote, so `git pull` works normally afterward.
- `pip install -e .[dev,test]` installs HiggsDNA in editable mode along with its `dev` and `test` extras — run this from the top-level `HiggsDNA/` directory (where `pyproject.toml` lives).
- `python scripts/pull_files.py --all` (run from inside `higgs_dna/`) pulls down auxiliary files (corrections, metaconditions, etc.) that the analysis needs but aren't tracked directly in git.
- All sample-production commands in the sections below assume you're sitting in this `higgs_dna/` directory afterward.

---

## How to produce samples

Custom output layout used in this guide:

```
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/data/preEE/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/data/postEE/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/data/preBPix/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/data/postBPix/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/sim/preEE/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/sim/postEE/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/sim/preBPix/
/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/sim/postBPix/
```

NMSSM signal samples follow the same `<year>/sim/<era>/` convention (Section 3).

---

## 1. Edit `produce_all_data.py`

File: `higgs_dna/submission/tools_HHbbgg/produce_all_data.py`

**a) Output base directory** (top of file):
```python
outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/"
extra_dir = ""
```

**b) Filter to only 2022/2023** — add right after the `samples = [ ... ]` list closes:
```python
allowed_years = ["2022preEE", "2022postEE", "2023preBPix", "2023postBPix"]
samples = [s for s in samples if s["year"] in allowed_years]
```

**c) Update `parent_dir` construction** in the submission loop:
```python
for sample in samples:
    year_folder = sample['year'][:4]   # "2022" or "2023"
    era_folder = sample['year'][4:]    # "preEE", "postEE", "preBPix", "postBPix"
    parent_dir = outbase_dir + "/" + year_folder + "/data/" + era_folder + "/" + extra_dir
```

---

## 2. Edit `produce_all_mc.py`

File: `higgs_dna/submission/tools_HHbbgg/produce_all_mc.py`

Same three edits, using `sim` instead of `data`:

**a)**
```python
outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/"
extra_dir = ""
```

**b)** After the `samples = [ ... ]` list:
```python
allowed_years = ["2022preEE", "2022postEE", "2023preBPix", "2023postBPix"]
samples = [s for s in samples if s["year"] in allowed_years]
```

**c)** In the submission loop (~line 1021):
```python
for sample in samples:
    year_folder = sample['year'][:4]
    era_folder = sample['year'][4:]
    parent_dir = outbase_dir + "/" + year_folder + "/sim/" + era_folder + "/" + extra_dir
```

---

## 3. NMSSM Signal Sample Production (separate script)

Centrally-produced NMSSM `X→YH→bbγγ` signal points aren't part of the standard background
`samples` list baked into `produce_all_mc.py` — they're submitted with a dedicated,
mass-grid-specific script (e.g. `produce_xtoyh_signal_mc_2024.py`), built per the pattern
below. Same output-directory convention as background MC (`<year>/sim/<era>/`).

### 3a. Confirmed dataset naming pattern

Verified against real resolved xrootd paths (not guessed) for `mX=1000`, and independently
re-confirmed via a live DAS existence check for `mX=300` — all 10/10 points resolved:

```
/NMSSM_XtoYHto2B2G_MX-{mX}_MY-{mY}_TuneCP5_13p6TeV_madgraph-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM
```

This is the **2022postEE** campaign (`Run3Summer22EENanoAODv12`, nano version `12`) — every
sample checked so far has been postEE specifically, not preEE. If/when preEE or 2023 NMSSM
points are needed, this campaign tag will need reconfirming against real resolved files for
that era before trusting the pattern — don't assume it carries over unchanged.

### 3b. Template script

```python
import os
import subprocess

# Initialize VOMS proxy
print("Initializing VOMS proxy...")
subprocess.run("voms-proxy-init --rfc --voms cms -valid 192:00", shell=True, check=True)

outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/" + os.environ['USER'] + "/HiggsDNA_v7_dask/"
extra_dir = ""

# Full (mX, mY) grid intended for this analysis, respecting the phase-space
# constraint mY < mX - mH. Uncomment/fill in mX blocks as each is confirmed
# in DAS (see 3a) -- don't submit an mX block you haven't pre-flight-checked.
NMSSM_Samples = {
    300: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],
    # 350: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200],
    # 400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    # 450: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300],
    # 500: [50, 60, 70, 80, 90, 95, 100, 150, 170, 200, 250, 300, 350],  # 125 excluded: v2-v2 vs v2-v4 mismatch, needs checking
    # 550: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    # 600: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    # 650: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    # 700: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    # 750: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    # 800: [60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],  # 50 excluded: v2-v2 vs v2-v4 mismatch
    # 850: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    # 900: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    # 950: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],  # verified against real resolved files
}

CAMPAIGN = "Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2"

samples = []
for mX, mY_list in NMSSM_Samples.items():
    for mY in mY_list:
        samples.append({
            "keyword": f"NMSSM_X{mX}_Y{mY}",
            "cmsdas": f"/NMSSM_XtoYHto2B2G_MX-{mX}_MY-{mY}_TuneCP5_13p6TeV_madgraph-pythia8/{CAMPAIGN}/NANOAODSIM",
            "year": "2022postEE",   # era-qualified -- see 3c, bare "2022" is rejected
            "nano": "12",
        })

print(f"Total samples in grid: {len(samples)}")

# --- Pre-flight check: confirm every dataset actually exists in DAS before
#     submitting anything. Catches a wrong campaign tag for an unverified
#     mX block before it wastes a Condor submission cycle.
print("\nChecking dataset existence in DAS (this may take a few minutes)...")
missing = []
for sample in samples:
    result = subprocess.run(
        f"dasgoclient -query=\"dataset={sample['cmsdas']}\"",
        shell=True, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        missing.append(sample["keyword"])
        print(f"  [MISSING] {sample['keyword']}: {sample['cmsdas']}")
    else:
        print(f"  [OK]      {sample['keyword']}")

if missing:
    print(f"\n{len(missing)} of {len(samples)} datasets did not resolve in DAS:")
    for k in missing:
        print(f"  - {k}")
    print("\nNot submitting any jobs -- fix these before rerunning.")
    raise SystemExit(1)

print("\nAll datasets confirmed in DAS. Proceeding with submission.\n")

# --- Submission ---
for sample in samples:
    year_folder = sample['year'][:4]   # "2022"
    era_folder = sample['year'][4:]    # "postEE"
    parent_dir = outbase_dir + "/" + year_folder + "/sim/" + era_folder + "/" + extra_dir

    print(f"Creating directory: {parent_dir}")
    os.makedirs(parent_dir, exist_ok=True)
    os.chmod(parent_dir, 0o777)

    command = f"python submission/tools_HHbbgg/produce_one_mc.py --keyword {sample['keyword']} --cmsdas {sample['cmsdas']} --parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']}   --memory 30GB "
    print(f"Executing: {command}")
    subprocess.run(command, shell=True, check=True)

print("All jobs have been executed successfully.")
```

### 3c. `--year` must be era-qualified

`produce_one_mc.py`'s `--year` argument only accepts:
```
2022postEE, 2022preEE, 2023postBPix, 2023preBPix, 2024, 2025, 2018, 2017, 2016preVFP, 2016postVFP
```
A bare `"2022"` fails immediately with `argparse` error `invalid choice: '2022'` — hit this
in practice on the first submission attempt. Every signal-production `samples` entry must
use the full era-qualified string (`"2022postEE"`), same as the background data/MC scripts
already do in Sections 1–2. Worth double-checking this on any new per-signal-grid script
written from scratch, since it's an easy thing to abbreviate by habit.

### 3d. Status (per era -- last updated 2026-08-23)

**2022postEE** -- essentially complete. All mX blocks (240, 280, 300, 320, 350, 400, 450, 500,
550, 600, 750, 800, 850, 900, 950, `1000` minus `mY=700`) submitted and confirmed via `--check`
with real chunk output. Only 2 confirmed real gaps remain (`X240_Y100`, `X450_Y125`, both
zero-file upstream DAS gaps, not pipeline issues) -- see "Known upstream NMSSM production
gaps". Signal-MC merge (Section 8) confirmed working and run against this era.

**2022preEE** -- partially submitted (`X1000`, `X240`, partial `X280`). Not yet run to
completion; picks up cleanly via resume logic whenever revisited.

**2023preBPix** -- full grid submission in progress. Hit and fixed two real, distinct
problems along the way: (1) the `micromamba`/`conda` env issue (3j) caused a large cascading
failure batch, since resolved by relaunching with `micromamba activate higgs-dna`; (2) the
JRV2/JRV3 JER bug (Section 9) caused every sample requesting `jerc_jet_pnetNu_syst` to fail --
local workaround applied in `produce_one_mc.py`, **confirmed fully working** (not just
"didn't crash") on a real previously-failing sample (`NMSSM_X350_Y100`) -- complete, correctly
structured output including every expected systematic variation subfolder. Full grid (all mX
blocks) launched with the workaround in place; not yet confirmed complete via `--check`.

**2023postBPix** -- full grid submission also launched, same JRV2/JRV3 workaround already in
place (patch is year-conditional on `"2023" in year`, so it applies to both eras identically
with no separate edit needed). Not yet confirmed complete via `--check`.

**mX blocks status** (applies across all four eras, since `NMSSM_Samples` is shared): all of
240, 280, 300, 320, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000
have been DAS-validated and are active in the grid at some point during today's session.
`X500_Y125`/`X800_Y50` (the historical `v2-v2` vs. `v2-v4` version-mismatch note) resolved
cleanly under the standard `CAMPAIGN` string in `--dry-run` -- no override was needed, though
this was only confirmed at the dataset-name level (same caveat as any `--dry-run` result, see
3h).

### 3e. Executor fix: `produce_one_mc.py` was using `dask/lxplus`, not `vanilla_lxplus`

`produce_one_mc.py`'s `run_analysis()` originally issued:
```
--executor dask/lxplus --queue workday --chunk 3000 --memory 30GB --debug --skipbadfiles --nano-version {n} --timeout 500
```
while `produce_one_data.py` (confirmed via direct grep on the live file, not assumed) uses the
simpler:
```
--executor vanilla_lxplus --queue workday --memory 30GB --debug --nano-version {n} --timeout 500
```

`dask/lxplus` starts a Dask scheduler/client in the foreground Python process, which must stay
alive and connected for the *entire* chunked run (not just submission) to coordinate work
across HTCondor-backed Dask workers -- this is what was keeping the terminal tied up for the
full duration of each sample, not just the submission step. `vanilla_lxplus` submits chunked
Condor jobs and returns once they're queued, matching how data behaves.

**Fix applied** (edit `submission/tools_HHbbgg/produce_one_mc.py`, inside `run_analysis()`):
- `f"--executor dask/lxplus "` → `f"--executor vanilla_lxplus "`
- Removed `f"--chunk 3000 "` (Dask-specific, meaningless under `vanilla_lxplus`)
- Removed `f"--skipbadfiles "` (a distributed-run safeguard for exactly the failure mode
  `dask/lxplus` is exposed to; not needed once back on the synchronous model)

Confirmed working in production: printed command for `NMSSM_X300_Y50` showed
`--executor vanilla_lxplus` with no `--chunk`/`--skipbadfiles`, submitted `18 job(s) submitted
to cluster 9208527`, and the script moved on to the next sample (`NMSSM_X300_Y60`) immediately
without blocking.

⚠️ **Scope of this change:** `run_analysis()` is shared code -- `produce_all_mc.py` (background
MC) also calls `produce_one_mc.py`, so this edit affects **all** MC production through this
script, not just NMSSM signal. If background MC needs `dask/lxplus` for its own reasons (e.g.
larger per-sample file counts benefiting from Dask's dynamic work-stealing), this should be
revisited as a parametrized `executor` argument instead of a blanket edit, so signal and
background can use different executors independently.

### 3f. Running the full grid unattended -- use `tmux.service`, NOT bare `nohup`+`disown`

⚠️ **Correction, confirmed the hard way:** an earlier version of this guide recommended
`nohup ... & disown` as sufficient to survive closing your laptop. **It is not, on lxplus9
nodes.** Confirmed directly: a `nohup`'d, `disown`'d process, run overnight, was silently
killed when the originating SSH session fully closed -- the log stopped cold mid-sample with
no error, no trace, and `pgrep` showed nothing running on that node afterward. This matches
`systemd-logind`'s `KillUserProcesses=yes` behavior on modern RHEL/AlmaLinux-based systems:
when your last login session for a user ends, **every process that user owns gets killed**,
including background/`disown`ed ones -- `nohup` only protects against the *shell* trying to
kill its children on hangup, not against `logind` cleaning up the whole session's process tree.

**The correct fix, specific to lxplus9:**
```bash
systemctl --user start tmux.service
tmux new -s nmssm_run
```
This starts your `tmux` server as a **user-level systemd unit**, living outside your login
session's scope entirely -- explicitly exempt from the `KillUserProcesses` cleanup. Inside the
new session:
```bash
cd /path/to/HiggsDNA/higgs_dna
micromamba activate higgs-dna          # NOT conda activate -- see Section 3j
python3 -c "import coffea" && echo "coffea OK"
voms-proxy-init --rfc --voms cms -valid 192:00
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era 2022postEE
```
`Ctrl+B, D` to detach. Reattach later (from the **same node** it started on -- the round-robin
caveat below still applies to `tmux` specifically) with:
```bash
tmux attach -t nmssm_run
```
`tmux ls` shows all your active sessions; `tmux kill-session -t <name>` removes one cleanly.

⚠️ Confirmed by mistake once already: launching from the wrong directory (e.g. an EOS output
directory instead of `higgs_dna/`) fails immediately and loudly (`can't open file ...` --
Python can't resolve the relative script path) -- harmless since nothing runs, but always
double check `pwd` before launching a long unattended run.

**On the round-robin/networked-path point** (kept from the earlier version, still true): the
log file and `nmssm_submission_state.json` live under `/eos/home-.../`, networked and visible
from any lxplus node -- so `cat`/`tail -f nmssm_full.log` and `--check` work from anywhere,
even though you can't `tmux attach` to a session except from the exact node it started on. If
you land on a different node next login, checking output/state directly is still fully
possible; only *reattaching to watch it live* requires the original node (or an SSH hop to it,
see 6f).

✅ **Resume/dedup gap fixed** -- see Section 3h. The plain (non-`_robust`) script still has no
resume logic (a crash-and-rerun resubmits everything); use `produce_xtoyh_signal_mc_2024_robust.py`
for any run you don't want to babysit or might need to interrupt and resume.

### 3g. Output directory structure -- one subfolder per systematic variation, plus `nominal/`

Per-sample output is **not** flat. See Section 6d for the full confirmed structure and how it
affects both `countCondorOutputs.py` and the completeness-check script's arguments.

### 3h. Hardened version: `produce_xtoyh_signal_mc_2024_robust.py`

A drop-in replacement for the plain submission script, adding three things the original
lacked:

1. **Resume/dedup via `nmssm_submission_state.json`**, written after every single sample
   (not just at the end). A killed/crashed run, rerun with the same command, skips everything
   already recorded as submitted and only attempts what's left -- no duplicate Condor jobs.
2. **One failed sample doesn't kill the batch.** The original's `subprocess.run(...,
   check=True)` raised on any non-zero exit, stopping the entire remaining loop. The robust
   version wraps each submission in `try`/`except`, logs the failure to
   `state["failed"]`, and continues to the next sample. Failed samples are automatically
   retried on the next plain rerun.
3. **Two read-only modes, safe to run in a second terminal while a real submission is in
   flight** (neither touches `nmssm_submission_state.json` or submits anything):
   - `--check` -- reports real EOS output status (via the same recursive check as 6d/6c, not
     `countCondorOutputs.py`'s single-level glob) for every sample in `state["submitted"]`.
     If no state file exists yet (e.g. checking output from a run made with the plain script),
     falls back to checking every sample currently defined in `NMSSM_Samples` instead, with a
     printed note explaining the fallback -- can't distinguish never-submitted from
     still-running from failed in that fallback mode, only has-output vs. no-output.
   - `--dry-run` -- DAS-checks every sample currently in `NMSSM_Samples` (including
     already-submitted ones) and reports which resolve, with zero side effects. Use this to
     validate a newly-uncommented mX block's `CAMPAIGN` tag before actually submitting it.

```bash
# Normal submission (resumable) -- launch inside tmux (Section 3f), not bare nohup
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era 2022postEE

# Check output status any time, from any node, without touching the run above
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era 2022postEE --check

# Validate a newly-uncommented mX block before submitting it for real
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era 2022postEE --dry-run
```

Known remaining limitation: `--check`/the state file only confirm *submission* succeeded, not
that the resulting Condor jobs actually completed cleanly -- that's still what Section 6's
`.err` reading and the completeness-check script (6c) are for.

### 3i. Multi-era support -- `--era` flag and composite `state_key` format

Extended to submit against any of the four eras from one script, not just `2022postEE`:
```python
CAMPAIGNS = {
    "2022preEE":    "Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "2022postEE":   "Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2",
    "2023preBPix":  "Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v2",
    "2023postBPix": "Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
}
```
`--era` defaults to `2022postEE` -- running with no flag is unchanged from before this was
added. Always pass `--era` explicitly anyway once you're juggling multiple eras; relying on
the default silently is exactly the kind of thing that's easy to get wrong later.

**State file entries changed from bare keywords to `era:keyword`** (e.g.
`"2022postEE:NMSSM_X300_Y50"`), so the same mass point can be tracked independently across all
four eras without collision. **Legacy entries from before this change are migrated
automatically on load** -- any bare keyword with no `:` is assumed `2022postEE` (the only era
that existed before multi-era support), so old state files work with no manual editing.

⚠️ **Known cosmetic bug, not yet fixed:** the `"Resuming: N already submitted, M previously
failed"` line printed at startup, and the final `"Done. N submitted total, M failed"` summary,
both read `state["submitted"]`/`state["failed"]` **globally across all eras**, not filtered to
the `--era` you're actually running. A `preBPix` run will report submitted/failed counts that
include `postEE`/`preEE`'s totals mixed in -- don't read these two lines as era-specific
without cross-checking with `--check --era <name>`, which *is* correctly filtered.

⚠️ **`--check`'s fallback mode (no state file) is also not era-aware in the same way** -- if
`NMSSM_Samples` on the machine you're checking from doesn't match what was actually
uncommented when a given era was submitted, you'll see a wall of
`[?] ... not in current NMSSM_Samples grid for this era, can't locate` for every entry that
doesn't match today's uncommented blocks. This is expected, not a bug -- it just means the grid
active *right now* differs from what was active *at submission time*; the real per-sample
result is still correctly reported for whatever *does* match.

### 3j. `micromamba activate`, not `conda activate` -- silent env failure, cascading crashes

⚠️ **Critical, caused a ~237-sample cascading failure once already.** The `higgs-dna`
environment was migrated from `conda` to `micromamba` at some point. Running
`conda activate higgs-dna` in a fresh terminal/`tmux` session **fails outright**
(`EnvironmentNameNotFound`) but does **not** stop you from continuing -- it silently leaves no
environment active, `python3`/`coffea` then resolve to whatever bare system Python exists (if
any), and **every single sample submitted from that point on fails identically** with
`ModuleNotFoundError: No module named 'coffea'`, one after another, no exceptions, until
someone notices.

**Always run this, exactly, as the first two commands in any new session, before touching the
submission script:**
```bash
micromamba activate higgs-dna
python3 -c "import coffea" && echo "coffea OK"
```
If `coffea OK` doesn't print, stop -- do not proceed to `voms-proxy-init` or the submission
script until this is fixed. `conda env list` will show `higgs-dna` doesn't exist under `conda`
at all, which is the fastest way to confirm this is the actual cause if you see the
`ModuleNotFoundError` cascade happening again.

---

## 4. Sign up in the spreadsheet

Before running, claim the 2022/2023 sample(s) you're producing (background *and* signal) in
the shared spreadsheet so submissions aren't duplicated.

---

## 5. Run from the `higgs_dna` directory

```bash
cd HiggsDNA/higgs_dna
```

Confirm a valid grid proxy (the script also does this itself, but good to check interactively first):
```bash
voms-proxy-init --rfc --voms cms -valid 192:00
```

Launch production:
```bash
python submission/tools_HHbbgg/produce_all_data.py
python submission/tools_HHbbgg/produce_all_mc.py
python submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024.py   # NMSSM signal grid, Section 3
```

Each script iterates only over its filtered sample list, creates the corresponding
`.../2022/data/preEE/`, `.../2022/sim/postEE/`, etc. directories on EOS, writes a
`runner_data_<year>_<keyword>.json` / `runner_mc_<year>_<keyword>.json` config per sample,
and submits the HTCondor jobs via `scripts/run_analysis.py`.

---

## 6. Monitor and find failed jobs

### 6a. Locating the actual job files (`vanilla_lxplus` executor)

`run_analysis.py --executor vanilla_lxplus` (via `LXPlusVanillaSubmitter` in
`higgs_dna/submission/lxplus.py`) does **not** write `.sub`/`.sh`/log files into
`submission/tools_HHbbgg/` or anywhere obvious near the scripts themselves. It creates a
hidden, per-invocation directory in whatever your **current working directory** was when you
ran the submission (i.e. `higgs_dna/`, if you followed Section 5):

```
higgs_dna/.higgs_dna_vanilla_lxplus/<analysis_name>_<YYYYMMDD_HHMMSS>/jobs/
```

`<analysis_name>` gets a timestamp suffix appended automatically
(`f"{analysis_name}_{date}_{time}"` in `lxplus.py`), so **every single sample submission gets
its own uniquely-named subdirectory** -- for the NMSSM signal grid, that means one such
directory per `(mX, mY)` point, not one for the whole batch.

Find every `.sub` file produced by a run (no depth limit needed -- the real files sit 4
levels deep from `higgs_dna/`, one level past a naive `-maxdepth 3` search):
```bash
find higgs_dna/.higgs_dna_vanilla_lxplus/ -iname "*.sub"
```

Each `jobs/` directory contains, per sample:
- `<tag>.sh` -- the submit wrapper (this is the `<submit_script.sh>` the monitoring script
  in 6b wants)
- `<tag>.sub` -- the actual HTCondor submit file (same basename, `.sub` instead of `.sh`)
- `<tag>.<clusterid>.<jobid>.out` / `.err` -- per-chunk logs, one pair per Condor job in that
  sample's cluster (job IDs `0`-`N-1`, matching the `condor_q` `JOB_IDS` column, e.g.
  `9208527.0-17` for an 18-chunk sample)

### 6b. Reading `.err` files -- warnings vs. real failures

Most `.err` files will have a small, uniform size (harmless boilerplate). If one stands out as
much larger, read it before assuming anything's wrong -- what actually matters is whether it
contains **`Traceback`**, not its size:

```bash
cat .higgs_dna_vanilla_lxplus/<analysis_name>_<timestamp>/jobs/<tag>.<clusterid>.<jobid>.err
```

Confirmed harmless, expected noise (seen repeatedly in real production `.err` files, not an
error): `RuntimeWarning: divide by zero encountered in divide` / `invalid value encountered in
divide` (a numpy/awkward ratio hitting 0/0 for some events -- expected, guarded downstream) and
`UserWarning: torch.distributed.reduce_op is deprecated` (a PyTorch API deprecation notice from
the ttH-killer/pDNN inference step). A larger `.err` from these alone is not a sign of failure
-- only `Traceback` is.

### 6c. Completeness check -- confirmed working, with a worked example

```bash
bash submission/tools_HHbbgg/find_files_resubmit_jobs_no_surviving_events.sh <submit_script.sh> <output_parquet_dir>
```
- `<submit_script.sh>` — the `.sh` wrapper found per 6a (**not** the `.sub` directly; the
  script derives and separately checks for the matching `.sub` alongside it).
- `<output_parquet_dir>` — the **sample-level** output directory, e.g.
  `.../postEE/NMSSM_X300_Y50/` — **not** the `postEE/` parent. The script checks
  `$OUTPUT_DIR/nominal/${uuid}*Events*.parquet` internally, so it needs to already be pointed
  at the specific sample.

**What it actually checks:** completeness of the `nominal` tree only -- one parquet expected
per input ROOT file, matched by UUID extracted from that job's input JSON. It does **not**
check the systematic-variation subfolders (`ScaleEB_Zee_down/`, etc. -- see 6d). For any
apparently-missing nominal output, it cross-references that job's `.out` log for the phrase
"No surviving events" and correctly skips flagging it if that's the (legitimate) explanation.

**Worked example**, confirmed against real output:
```bash
bash submission/tools_HHbbgg/find_files_resubmit_jobs_no_surviving_events.sh \
    .higgs_dna_vanilla_lxplus/runner_mc_2022postEE_NMSSM_X300_Y50_20260822_020549/jobs/AN-NMSSM_X300_Y50.sh \
    /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask/2022/sim/postEE/NMSSM_X300_Y50/
```
```
🔍 Scanning for missing .parquet files using .../AN-NMSSM_X300_Y50.sh...
✅ Total missing: 0
```
`Total missing: 0` on the first fully-completed NMSSM signal sample -- first genuine
end-to-end confirmation the executor fix (Section 3e), DAS naming pattern (3a), and output
directory structure (6d) all hold up in practice, not just in theory.

If it reports missing jobs instead, resubmit with the printed command:
```bash
python3 submission/tools_HHbbgg/resubmit_jobs.py <submit_script.sub> "<space-separated job ids>"
```
(commented out inside the monitoring script itself -- it only prints the command, doesn't
auto-run it.)

### 6d. Output directory structure -- confirm before pointing 6c at a sample

Real per-sample output is **not** flat -- one subfolder per systematic variation, plus
`nominal/`:
```
.../postEE/NMSSM_X300_Y50/
    nominal/<uuid>_Events_0-N.parquet          (one per input file -- what 6c checks)
    ScaleEB_Zee_down/<uuid>_Events_0-N.parquet
    ScaleEB_Zee_up/...
    ScaleEB_Zmmg_down/...  ScaleEB_Zmmg_up/...
    ScaleEE_Zmmg_down/...  ScaleEE_Zmmg_up/...
    (additional variation folders depending on the sample's systematics list)
```
One sample submission can also spawn **several separate Condor clusters** -- one per
systematic-variation split, not just one for the whole sample. Don't be surprised by a much
higher `condor_q` job count than a naive "1 sample = 1 cluster" expectation (confirmed: 6
clusters / 104 total jobs in flight for only 2-3 samples mid-run at once).

### 6e. Silent-failure bug: a sample can fail before ever reaching Condor, with no clear error (root cause confirmed, fix below)

Found while diagnosing `NMSSM_X1000_Y700` producing no `.higgs_dna_vanilla_lxplus/` job
directory at all despite having passed DAS pre-flight. Root cause is in
`produce_one_mc.py` itself, confirmed against source (`submission/tools_HHbbgg/produce_one_mc.py`):

```python
def fetch_datasets(sample_file, dbs_instance='prod/global', region='Yolo'):
    command = f"python scripts/samples/fetch_datasets.py -i {sample_file} -w {region} --dbs-instance {dbs_instance}"
    os.system(command)          # return code never checked

def update_json_config(keyword, year, split_mc=False):
    ...
    config["samplejson"] = f"samples_mc_{year}_{keyword}.json"   # just writes the filename,
                                                                  # never checks it was produced
```

If `fetch_datasets.py` resolves **zero files** (or fails outright), `fetch_datasets()`
doesn't stop anything -- `os.system()`'s return code is discarded. `update_json_config()`
then writes a *reference* to the expected `samples_mc_<year>_<keyword>.json` into the runner
config regardless of whether that file actually exists. The pipeline proceeds straight to
`run_analysis.py`, which then fails trying to load a `samplejson` that was never written --
**before** ever reaching the `vanilla_lxplus` submission step, so no job directory, no Condor
cluster, nothing in `condor_q` at all. Confirmed in practice, running `produce_one_mc.py`
directly for the affected sample:
```
WARNING   Zero DAS results for 'NMSSM_X1000_Y700'
...
ERROR     No files collected — nothing to write.
Choosing runner_mc_template.json
python scripts/run_analysis.py --json-analysis runner_mc_2022postEE_NMSSM_X1000_Y700.json ...
```
The `ERROR` line prints, but nothing acts on it -- execution continues straight into building
and printing the `run_analysis.py` command anyway.

**Diagnosis workflow for a sample with no job directory:** check which intermediate file
stage stopped, in order:
```bash
ls -la samples_mc_<year>_<keyword>.txt samples_mc_<year>_<keyword>.json runner_mc_<year>_<keyword>.json 2>&1
```
- Only `.txt` exists → `fetch_datasets()` failed or produced zero files (this case).
- `.txt` + `samples_mc_...json` exist, no `runner_mc_...json` → `update_json_config()` failed.
- All three exist, no `.higgs_dna_vanilla_lxplus/` dir for this sample → `run_analysis.py`
  itself crashed during processor/metaconditions setup, before reaching submission.

**Root cause confirmed -- it's specifically `produce_one_mc.py`'s `os.system()` call, not
which fetch script it runs.**

`fetch_datasets_handle.py` (`submission/tools_HHbbgg/`, adopted from a colleague's setup,
`bsahu`'s copy at `/eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/submission/tools_HHbbgg/`)
was already in place *before* the `NMSSM_X1000_Y700` failure happened -- confirmed by file
timestamp (01:02) predating the first production run of the day (02:05). Initially assumed
this script itself was the fix; **directly tested and confirmed otherwise**:
```bash
python submission/tools_HHbbgg/fetch_datasets_handle.py \
    -i samples_mc_2022postEE_NMSSM_X1000_Y700.txt -w Americas --dbs-instance prod/global
echo "Exit code: $?"
```
```
WARNING   Zero DAS results for 'NMSSM_X1000_Y700'
...
ERROR     No files collected — nothing to write.
Exit code: 1
```
`fetch_datasets_handle.py` behaves **correctly** -- it detects zero files and exits 1. The bug
is entirely in how `produce_one_mc.py` calls it:
```python
def fetch_datasets(sample_file, dbs_instance='prod/global', region='Yolo'):
    command = f"python submission/tools_HHbbgg/fetch_datasets_handle.py -i {sample_file} -w {region} --dbs-instance {dbs_instance}"
    os.system(command)   # exit code 1 computed correctly by the script above, then discarded here
```
`os.system()` gets a real, correct, non-zero exit code back and does nothing with it.
`fetch_datasets()` returns `None` regardless of success or failure, so `main()` has no way to
know anything went wrong and proceeds straight into `update_json_config()` /
`run_analysis()` anyway.

**The actual fix -- apply in `produce_one_mc.py`:**
```python
def fetch_datasets(sample_file, dbs_instance='prod/global', region='Yolo'):
    command = f"python submission/tools_HHbbgg/fetch_datasets_handle.py -i {sample_file} -w {region} --dbs-instance {dbs_instance}"
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"fetch_datasets_handle.py failed (exit code {result.returncode}) for "
            f"{sample_file} -- aborting before submission. Check DAS for this dataset directly."
        )
```
Confirm `subprocess` is imported at the top of `produce_one_mc.py` (it already imports `os`;
add `import subprocess` alongside it if not already present). Not yet applied to the live
file as of this writing -- do this before trusting any further production runs to catch a
zero-file dataset the way `Y700` should have been caught.

⚠️ **Everything produced so far today ran with `fetch_datasets_handle.py` already active but
this control-flow fix *not* applied** -- X300, X850, X900, X950, X1000, and the X320/350/400
batch. The improved script gives a clearer log message on failure, but doesn't stop the
pipeline by itself. `--check` (6c/3h) remains the right tool to catch any sample in these
batches that silently failed this way -- it doesn't depend on which fetch script ran.

### 6f. Diagnosing held Condor jobs -- generic hold reason, need the `.err` for the real cause

```bash
condor_q -submitter <user> -held -af ClusterId ProcId HoldReason
```
Almost always prints the same unhelpful generic reason:
```
The job attribute OnExitHold expression '(ExitBySignal == true) || (ExitCode != 0)' evaluated to TRUE
```
This just means the job's own script exited non-zero -- tells you nothing about *why*. The
`Iwd` field (`condor_q -held -af ClusterId ProcId Iwd`) points at the **schedd's internal
spool** (`/var/lib/condor/spool/...`), not browsable from lxplus -- not useful here.

**Get the real error** the same way as 6a -- locate the job's `.sh`/`.err` files directly:
```bash
ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null
tail -30 $(ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null)
```
`tail -30`, not the full file -- the actual Python `Traceback`/exception sits at the *end*;
the beginning is often just noise (deprecation warnings, harmless `RuntimeWarning`s per 6b).

⚠️ Run this from `higgs_dna/` itself -- confirmed losing significant time to this exact
mistake: if your prompt shows you're already inside `.higgs_dna_vanilla_lxplus/` or a
`postEE`/`preBPix` output directory, the glob silently returns nothing (searching a
`.higgs_dna_vanilla_lxplus/` nested inside itself, or the wrong tree entirely). Check `pwd`
first if a glob that should obviously match comes back empty.

### 6g. Cross-node process management -- lxplus round-robins, `pgrep` only sees the local node

`pgrep -af produce_xtoyh_signal_mc_2024_robust` only shows processes on **the node you're
currently on**. Since lxplus round-robins your SSH connection across many physical nodes
(`lxplus947`, `lxplus960`, `lxplus982`, `lxplus990`, `lxplus994`, ... -- all seen in one
session), a process launched from a previous login can be completely invisible from your
current one, even though it's still running (or, worse, stuck).

**Check specific nodes directly via SSH, without fully logging in:**
```bash
ssh -o StrictHostKeyChecking=accept-new <node>.cern.ch "pgrep -af produce_xtoyh_signal_mc_2024_robust" 2>/dev/null
```
(`-o StrictHostKeyChecking=accept-new` avoids an interactive host-key confirmation prompt that
would otherwise hang a loop over several nodes, exactly as it did the first time this was run
without the flag)

**Loop over a handful of recently-used nodes if you don't know which one:**
```bash
for node in lxplus947 lxplus960 lxplus982 lxplus990 lxplus994; do
    echo "=== $node ==="
    ssh -o StrictHostKeyChecking=accept-new $node.cern.ch "pgrep -af produce_xtoyh_signal_mc_2024_robust" 2>/dev/null
done
```

**Checking whether a found process is actually alive, or a zombie:**
```bash
\ps -o pid,stat,etime,pcpu,cmd -p <pid>
```
(the leading `\` bypasses a possible `ps auxf` shell alias -- see 6h) `STAT` column: `S`/`R` =
genuinely alive; `T` = stopped, doing nothing, safe to `kill -9`. Confirmed in practice: a
process stuck on an interactive prompt (passphrase, `y/n` confirmation) with a detached/dead
controlling terminal shows exactly this `T` state, `0.0% CPU`, indefinitely -- `/proc/<pid>/fd/`
listing only stdin/stdout/stderr pointing at a `pty`, with **no** open sockets/files, confirms
it's blocked on terminal input with nowhere for that input to come from, not doing real work.

**Killing:** use `-9` specifically. Confirmed in practice: plain `kill` (SIGTERM) can leave a
process stuck in `T` state for hours if it's blocked reading from a dead terminal --
`kill -9 <pid>` (SIGKILL) cannot be ignored or blocked, guaranteed to actually terminate it.

### 6h. `ps` alias collision -- `ps -o ... -p ...` conflicts with an aliased `ps auxf`

Many lxplus accounts have `ps` aliased (`alias ps='ps auxf'`, check with `type ps`/`alias | grep ps`).
Running `ps -o pid,stat,... -p <pid>` on top of that alias produces:
```
error: conflicting format options
```
Fix: bypass the alias for one call with a leading backslash, or use `pgrep -a` instead (never
aliased):
```bash
\ps -o pid,stat,etime,pcpu,cmd -p <pid>
pgrep -af <pattern>          # equivalent info, no alias risk at all
```

### 6i. Stale `state["submitted"]` entries -- marked submitted, but nothing on Condor, no output

Can happen if a process gets killed (6f/`logind`) *after* `produce_one_mc.py` returns
successfully but *before* its Condor jobs actually land/complete, or in rarer cases if the
outer wrapper's `subprocess.run()` call succeeds while something deeper silently failed.
Symptom: `--check` reports `[OK]`-looking entries as tracked, but `condor_q` shows nothing for
those samples and EOS has no real output.

**Confirm before removing anything** -- check `condor_q` for the samples in question:
```bash
condor_q -submitter <user> | grep -i "<date the batch was submitted>"
```
If genuinely nothing shows up for that date/those samples, they're stale. **Remove
surgically** -- never blanket-clear `state["submitted"]`, only the specific confirmed-stale
keys:
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)

stale = [
    '<era>:NMSSM_X<mX>_Y<mY>',
    # ... one line per confirmed-stale key
]

before = len(s['submitted'])
s['submitted'] = [k for k in s['submitted'] if k not in stale]
print(f'Removed {before - len(s[\'submitted\'])} of {len(stale)} targeted entries')

with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```
**Always re-read the file after writing**, don't assume the write succeeded -- confirmed once
that a first attempt silently didn't persist (working directory or copy-paste issue), and only
a fresh read after the fact caught it:
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)
print('still present:', '<era>:NMSSM_X<mX>_Y<mY>' in s['submitted'])
"
```

### 6j. Opposite problem: state file *under*-counting real progress after running from multiple
terminals/nodes concurrently -- full recovery process

**Symptom:** samples that are genuinely complete (real output on EOS) or actively running on
Condor show up as "not yet submitted" -- a subsequent run would try to resubmit them.

**Root cause (confirmed, now fixed -- see 10g):** the submission script used to load
`nmssm_submission_state.json` **once** into memory at startup and hold that copy for the
entire run. Running the same script from two different lxplus nodes at the same time (easy to
do without realizing it -- the round-robin means separate terminals/logins routinely land on
different physical nodes) means each process's in-memory copy goes stale relative to what the
*other* process is writing. Whichever process's final save happens last overwrites the whole
file with its own stale snapshot -- silently erasing anything the other process added.
**Confirmed hitting this for real**: state claimed only `53` `2024` samples submitted; real
count (recovered via the process below) was `203` -- `150` genuinely-real samples had gone
invisible to state tracking (`68` already fully complete on EOS, `85` still actively running
on Condor).

**Two-stage recovery, in order:**

**Stage 1 -- reconcile against real EOS output** (catches samples that finished completely):
```bash
python3 -c "
import json
from pathlib import Path

with open('nmssm_submission_state.json') as f:
    s = json.load(f)

outbase = '/eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/'
added = 0
for sample_dir in Path(outbase).iterdir():
    if not sample_dir.is_dir():
        continue
    keyword = sample_dir.name
    n_files = len(list(sample_dir.rglob('*Events_0*')))
    state_key = f'<year_or_era>:{keyword}'
    if n_files > 0 and state_key not in s['submitted']:
        s['submitted'].append(state_key)
        added += 1
        print(f'Added missing entry: {state_key} ({n_files} files)')

print(f'Total added: {added}')
with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```
⚠️ **Threshold caveat, confirmed real**: this checks only "at least 1 file exists" -- catches
genuinely-complete samples, but ALSO catches samples only *partway* through processing.
Confirmed real examples from this exact recovery: entries with only `1`, `16`, and `17` files
(vs. the typical `300`-`500+` for a genuinely complete sample) got incorrectly marked
`submitted` by this stage alone. **Always eyeball the printed file counts** -- anything
suspiciously low needs manual removal afterward (see "cleanup" below), or it gets permanently
skipped by future runs despite not actually being done.

**Stage 2 -- reconcile against real in-flight Condor jobs** (catches samples still running,
which have zero output yet and so are invisible to Stage 1):
```bash
# First, confirm bare condor_q (no -submitter) is safely scoped to just you on
# this schedd -- only needed once:
condor_q | awk '{print $1}' | sort -u
# every row should show only your username, plus table-formatting rows (OWNER, Total, --)

python3 -c "
import json, subprocess

result = subprocess.run('condor_q -af Cmd', shell=True, capture_output=True, text=True)
lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]

keywords = set()
for line in lines:
    if line.startswith('AN-') and line.endswith('.sh'):
        keyword = line[len('AN-'):-len('.sh')]
        keywords.add(keyword)

print(f'Found {len(keywords)} distinct in-flight sample keywords on Condor')

with open('nmssm_submission_state.json') as f:
    s = json.load(f)

added = 0
for keyword in sorted(keywords):
    state_key = f'<year_or_era>:{keyword}'
    if state_key not in s['submitted']:
        s['submitted'].append(state_key)
        added += 1
        print(f'Added in-flight entry: {state_key}')

print(f'Total added: {added}')
with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```
⚠️ **This blindly prefixes every found keyword with one hardcoded year/era** -- only safe when
everything currently in your Condor queue genuinely belongs to that one year/era (sanity-check
`condor_q -af Cmd | sort -u | wc -l` against the expected sample count first). If multiple
eras/years are truly in flight simultaneously, this needs to attribute jobs to the correct
year/era individually, not assume one blanket prefix.

⚠️ **`condor_q -submitter <user>` unexpectedly returned nothing at all** on one node tonight,
despite real jobs existing and bare `condor_q` (no flag) showing them correctly scoped to just
this user already. Not fully root-caused -- if you hit the same empty-result symptom, fall
back to bare `condor_q` after the one-time scoping confirmation above.

⚠️ **`condor_q -af JobBatchName` returns nothing useful** -- confirmed the default-displayed
`BATCH_NAME` column (`ID: 9236033`) is just the auto-generated cluster ID, not a real name,
since no batch name is ever explicitly set at submission. Use `-af Cmd` instead and extract
the keyword from the `.sh` filename pattern (`AN-<keyword>.sh`), as shown above.

**Cleanup -- remove any suspiciously-low-file-count entries Stage 1 added:**
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)
suspicious = ['<year_or_era>:NMSSM_X###_Y###']  # fill in from Stage 1's own printed output
before = len(s['submitted'])
s['submitted'] = [k for k in s['submitted'] if k not in suspicious]
print(f'Removed {before - len(s[\"submitted\"])} suspicious entries')
with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```

**Verify the recovery actually worked:**
```bash
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year <year> --dry-run
```
"Resuming" count should now match reality. Confirmed in practice: went from a false `53` to a
correct `203`, cross-checked against the real remaining-samples count (`70` = `273 - 203`,
matched exactly what `--dry-run` independently reported).

---

## 7. Additional sanity checks

```bash
python submission/tools_HHbbgg/countCondorOutputs.py /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/data/preEE/
python submission/tools_HHbbgg/checkCondorErrors.py <condor_log_dir>/
```
- `countCondorOutputs.py` counts how many `*Events_0*` output files exist.
- `checkCondorErrors.py` scans `.err`/`.out` logs for `Traceback` (needs resubmission) or
  `No surviving events` (fine, nothing to do).

Run these per era/subfolder, since output is now split by preEE / postEE / preBPix / postBPix
(and per mass point for NMSSM signal).

⚠️ **`countCondorOutputs.py` false negative for NMSSM signal output.** It globs
`<dir>/*Events_0*` -- one directory level. Signal output actually sits **two** levels deep,
one subfolder per systematic variation (see Section 6d):
`<dir>/<sample>/<variation>/<uuid>_Events_0-N.parquet`. Pointing the script at a sample
directory that has real, valid output can still print `0 ...condor jobs produced output` --
this is the glob missing the files, not a sign anything failed. Confirmed in practice: a
sample with dozens of real parquet files across multiple variation subfolders still reported
zero.

**Workaround -- count recursively instead:**
```bash
find /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask/2022/sim/postEE/NMSSM_X300_Y50/ -iname "*Events_0*" | wc -l
```
`countCondorOutputs.py` itself should ideally be patched to recurse (`find` instead of a
single-level `ls` glob) so it reflects reality for this output structure -- not yet done.

**Also check `condor_q` before trusting either output count as "finished":**
```bash
condor_q -submitter sraj
```
Zero output files with jobs still `idle`/`running` in `condor_q` is completely expected --
wait for completion before treating a low/zero count as a failure. Only chase it further
(`checkCondorErrors.py`, held-job investigation) once `condor_q` shows 0 idle/running for
that sample.

---

## 8. Merge / postprocess

⚠️ **The commands below without `--syst --varDict` were never independently verified working
-- treat them with caution.** `prepare_output_file.py` (`scripts/postprocessing/`) is a large,
multi-purpose script (category-based ROOT tree building, `trees2ws.py` calls for `finalfit`
workspaces) -- **not** a simple "combine chunk files into one" tool the way the bare
`--input <dir> --merge` invocation implies. The confirmed-working invocation, provided by a
colleague's real working example and independently confirmed running on this analysis's own
`postEE` output, needs `--output` and, for signal MC with systematic variations, `--syst
--varDict` as well:

**Confirmed working (NMSSM signal, per era):**
```bash
python scripts/postprocessing/prepare_output_file.py \
    --input  /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask/2022/sim/postEE/ \
    --output /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask/2022/sim/postEE/ \
    --merge --syst --varDict submission/tools_HHbbgg/variations_mc.json
```

⚠️ **CONFIRMED, do not do this: `--input` pointed at a single sample directory instead of the
full era directory.** Tried as a shortcut to merge just one newly-added sample without
re-merging the whole era -- produces a garbled cartesian product of every variation folder
paired against every other variation folder (`.../NMSSM_X350_Y200/ScaleEB_Zee_up/jer_syst_up`,
`.../ScaleEB_Zee_up/ScaleEB_Zee_down`, etc.), almost all resulting in `FileNotFoundError`, with
a handful of coincidental "successes" that produce **wrong**, not just missing, output.

**Root cause**: `merge_parquet.py` (called internally by `prepare_output_file.py`) assumes a
fixed two-level directory depth beneath `--input` -- sample name, then variation name (true at
the era level: `<era>/<sample>/<variation>/`). Pointing `--input` directly at one sample
directory removes the outer (sample-name) level, so the script misinterprets each
variation-name folder as if it were a sample name, then looks one level deeper inside it for a
second variation -- producing the nonsensical cross-product seen above.

**If this happens**: don't trust anything written under the target `merged/` directory from
that run -- delete it and rerun with the full era-level `--input` before trusting the output:
```bash
rm -rf /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/<year>/<era>/merged
```
**No per-sample merge shortcut exists** with this tool as currently structured -- always
re-merge the full era, even to add just one newly-completed sample.
`--input`/`--output` can be the same directory -- merged output lands in a `merged/`
subdirectory nested inside it, not mixed with the raw per-job chunks. Repeat once per
`<year>/sim/<era>/` directory for the other three eras once each is confirmed complete via
Section 6c/3h's `--check`.

Once run, verify real output landed before trusting it:
```bash
find /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask/2022/sim/postEE/merged/ -maxdepth 2 | head -30
```

**Data and background MC** -- the commands below are the *previously documented* pattern
(no `--output`/`--syst`/`--varDict`), carried over from before this section was corrected.
**Not independently confirmed the same way the signal command above was** -- verify against a
real working example (the way the signal command was confirmed) before trusting these for
anything that matters:
```bash
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/data/preEE/   --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/data/postEE/  --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/data/preBPix/ --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/data/postBPix/ --merge

python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/sim/preEE/   --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2022/sim/postEE/  --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/sim/preBPix/ --merge
python scripts/postprocessing/prepare_output_file.py --input /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2023/sim/postBPix/ --merge
```

---

## 9. Known bug: `jerc_jet_pnetNu_syst` crashes for `2023preBPix`/`2023postBPix` --
`jer_version` hardcodes `JRV2`, actual files use `JRV3`

Discovered while diagnosing why `2023preBPix` samples showed as `held` on Condor with no
useful error from `produce_one_mc.py` itself.

### 9a. Symptom

Jobs go `held` (`condor_q -held`, generic `OnExitHold` reason, see 6f). The real error, only
visible in the per-job `.err` file:
```
File ".../systematics/jet_systematics_json.py", line 554, in jerc_jet
    eval_dict[input.name] for input in ceval_jer[jer_ptres_tag].inputs
IndexError: map::at

Exception: Failed processing file: WorkItem(dataset='NMSSM_X350_Y60', ...)
```

### 9b. Root cause, traced through the actual code

`systematics/factories.py` registers:
```python
"jerc_jet_pnetNu": partial(jerc_jet, pt=None, apply_jec=True, apply_jer=True, reg="PNetRegressionPlusNeutrino")
```
`systematics/jet_systematics_json.py` builds the JER lookup tag from a hardcoded
`jer_version` dict:
```python
jer_version = {
    ...
    "2023preBPix": "Summer23Prompt23_RunCv1234_JRV2_MC",
    "2023postBPix": "Summer23BPixPrompt23_RunD_JRV2_MC",
    ...
}
jer = jer_version[year]
algo = "AK4PFPuppi" + reg   # regression-aware corrections load a *different* file
                             # (regFlag="_PNet"/"_UParT" -> jet_jerc_PNet.json.gz),
                             # this part of the code is correct
jer_ptres_tag = f"{jer}_PtResolution_{algo}"
```
**File selection is correct** -- `regFlag` logic correctly resolves to `jet_jerc_PNet.json.gz`
when `reg` contains `"PNet"`/`"UParT"`, and that file genuinely contains the needed
regression-aware correction. **The version string is wrong.** Confirmed directly by loading
both real files and listing every `PtResolution` correction name present:

`2023_Summer23/jet_jerc_PNet.json.gz` (preBPix) -- all entries `JRV3`:
```
Summer23Prompt23_RunCv1234_JRV3_MC_PtResolution_AK4PFPuppi
Summer23Prompt23_RunCv1234_JRV3_MC_PtResolution_AK4PFPuppiPNetRegression
Summer23Prompt23_RunCv1234_JRV3_MC_PtResolution_AK4PFPuppiPNetRegressionPlusNeutrino
Summer23Prompt23_RunCv1234_JRV3_MC_PtResolution_AK4PFPuppiUParTRegression
Summer23Prompt23_RunCv1234_JRV3_MC_PtResolution_AK4PFPuppiUParTRegressionPlusNeutrino
... (same set repeated for RunCv123, RunCv4)
```
`2023_Summer23BPix/jet_jerc_PNet.json.gz` (postBPix) -- same pattern, `JRV3`, `RunD`.

The **plain, non-`_PNet`** file (`jet_jerc.json.gz`) genuinely does use `JRV2` for both eras,
matching what's hardcoded -- which is exactly why plain `jerc_jet`/`jerc_jet_syst` (no `reg`)
work fine everywhere, and why `2022preEE`/`2022postEE` (confirmed running cleanly all night
with the identical `jerc_jet_pnetNu_syst` systematic active) aren't affected -- their `_PNet`
files apparently still use whatever version the code already expects.

**Supporting evidence this is a real, sanctioned upstream change, not a stale local pull:**
both years' `changes.md` (shipped alongside the JSONs, from the official JME POG MRs) describe
a **2026-06-05** reorganization: *"Split JER nominal and up/down SF tags... Homogeneous content
(formula and arguments) for all years"* -- consistent with a version-bump/schema change, not a
physics recalibration. Not 100% certain this rules out any numerical difference between JRV2
and JRV3, but reasonably strong supporting evidence the fix below doesn't silently change
results.

### 9c. The real fix (belongs in shared code, not applied there yet)

```python
"2023preBPix": "Summer23Prompt23_RunCv1234_JRV3_MC",     # was JRV2
"2023postBPix": "Summer23BPixPrompt23_RunD_JRV3_MC",       # was JRV2
```
One line each in `jet_version`. **This is shared code** (`jet_systematics_json.py`) affecting
every analysis using this HiggsDNA branch, not just NMSSM signal production -- filed as an
issue for whoever owns this file rather than applied unilaterally. Not yet confirmed merged.

### 9d. Local workaround applied -- unblocks 2023 production now, doesn't touch shared code

Since `produce_one_mc.py` (submission/tools_HHbbgg/) is fully owned by this analysis's own
production scripts, patched `update_json_config()` there instead of touching the shared JME
correction logic. Inserted right after the existing year-conditional bTag substitution block:
```python
if "2023" in year:
    # Temporary workaround: jer_version hardcodes JRV2, but the _PNet-suffixed
    # JER files for 2023preBPix/2023postBPix use JRV3, causing
    # jerc_jet_pnetNu_syst to crash with IndexError: map::at.
    # Falls back to plain jerc_jet_syst (no PNet regression) until fixed upstream.
    if "jerc_jet_pnetNu_syst" in config["corrections"][keyword]:
        idx = config["corrections"][keyword].index("jerc_jet_pnetNu_syst")
        config["corrections"][keyword][idx] = "jerc_jet_syst"
```
**Confirmed working, not just "didn't crash"** -- `NMSSM_X350_Y100` (one of the samples that
previously crashed with this exact error) ran through cleanly with this patch in place, and
its actual output directory shows a complete, correctly-structured set of systematic
variations, not just a bare `nominal/`:
```
jec_AK8_syst_Total_down/  jer_AK8_syst_up/   ScaleEB_Zee_up/     ScaleEE_Zmmg_down/
jec_AK8_syst_Total_up/    jer_syst_down/     ScaleEB_Zmmg_down/  ScaleEE_Zmmg_up/
jec_syst_Total_down/      jer_syst_up/       ScaleEB_Zmmg_up/    Smearing_down/
jec_syst_Total_up/        nominal/           ScaleEE_Zee_down/   Smearing_up/
jer_AK8_syst_down/        ScaleEB_Zee_down/  ScaleEE_Zee_up/
```
Both JEC and JER (up/down), all four energy-scale variations, `Smearing`, and the AK8 fatjet
variants are all present -- exactly what's expected once `jerc_jet_pnetNu_syst` is swapped for
plain `jerc_jet_syst`, nothing missing beyond the PNet-regression-specific variant itself. Safe
to trust across the rest of `2023preBPix`/`2023postBPix` production while the real upstream fix
(9c) is pending review.

⚠️ **This is a physics-content change, not just a bugfix** -- 2023preBPix/postBPix samples
produced with this workaround have JEC applied *without* PNet-regression-plus-neutrino
awareness for JER, unlike 2022's samples (which get the full regression-aware treatment). Not
a blocker for getting production unstuck, but worth remembering when comparing 2022 vs. 2023
systematics later, and worth re-running affected 2023 samples once the real fix (9c) lands
upstream, rather than treating this workaround as permanent.

---

## 10. NMSSM production for 2024/2025 -- separate script, several real differences from 2022/2023

⚠️ **Same upstream JER caveat as Section 9, but stronger and unconditional for these two
years** -- `jet_systematics_json.py` (~line 166) explicitly warns *"Current 2024 and 2025 JER
are preliminary, 2023PostBPix is used! These ntuples should not be used for a final physics
result!"* This applies regardless of anything below being technically correct -- production
runs and produces real output, but that output carries this caveat unconditionally. Confirm
this is acceptable (pipeline validation: fine; a final result: not) before relying on it.

### 10a. Why a separate script, not an extension of the 2022/2023 one

Several confirmed, real differences didn't fit the 2022/2023 script's assumptions cleanly
enough to bolt on with a flag:

- **Dataset naming is different.** Hyphenated
  `NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8`, not the
  underscored `NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>` used for 2022/2023. Confirmed directly via
  `dasgoclient` -- the underscored convention returns nothing for 2024/2025 at all, which
  initially (wrongly) looked like the dataset simply didn't exist yet.
- **`--year` is not era-qualified** for these two years -- plain `"2024"`/`"2025"`, confirmed
  from `produce_one_mc.py`'s own `--year` argparse `choices` list (no `2024preXYZ`-style
  split the way 2022/2023 have `preEE`/`postEE`).
- **NanoAOD version is v15**, not v12 (`--nano 15`).
- **2024 and 2025 share the exact same physical dataset** -- confirmed, not just inferred:
  no separate 2025 MC production exists. Both years are the same underlying events, split by
  event ID (even → 2024, odd → 2025) via an **automatic**, year-triggered mechanism inside
  `update_json_config()` -- confirmed present via direct `grep` on the real deployed
  `produce_one_mc.py`. **Not** a CLI flag -- `--split-mc` does **not** exist as an argument on
  the deployed script (confirmed the hard way: passing it produces
  `error: unrecognized arguments: --split-mc` from `produce_one_mc.py`'s own argparse). An
  earlier draft of the new script incorrectly tried to pass this flag, based on a stale local
  copy of the code that had it as an explicit CLI option -- corrected once the real deployed
  file's argparse usage line proved it wrong.

### 10b. Real confirmed campaign string

```
RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2
```
Confirmed via `dasgoclient` for `MX-1000/MY-125` specifically (both `NANOAODSIM` and
`MINIAODSIM` tiers exist together under this campaign), and matches the naming convention
already used for other processes (ggHH, VBF, ttH, backgrounds) in this repo's own
`produce_all_mc.py` -- good internal consistency, not a one-off.

### 10c. Confirmed grid -- all 273 candidate points resolved

Starting point: two confirmed mass points (`MX-1000/MY-125` via direct `dasgoclient`,
`MX-750`'s 15 `mY` points via a real file listing at the MiniAOD tier). Full phase-space
envelope (matching 2022/2023's grid structure) added as commented-out candidates, then
validated block by block via `--dry-run` -- **273/273 resolved cleanly** for both `2024` and
`2025` independently (each run separately, both returning the same count against the same
underlying dataset, exactly as expected given 10a's shared-dataset confirmation).

### 10d. Status (2026-08-23)

Full 273-sample grid submitted for both `2024` and `2025`. One test sample
(`NMSSM_X240_Y50`, 2024) confirmed reaching real Condor submission cleanly (24 jobs, cluster
`9236032`) before the full grid was launched -- same incremental-validation discipline as
2022/2023. Not yet confirmed complete via `--check`; not yet confirmed that individual jobs
run cleanly through actual coffea processing the way `X350_Y100` was for the JRV2/JRV3
workaround (2023's crash only showed up once jobs actually ran, not at submission time --
worth remembering here too before assuming 273/273 `--dry-run` + one clean submission means
the whole grid is guaranteed problem-free).

### 10e. Commands

```bash
# Validate before submitting
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year 2024 --dry-run
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year 2025 --dry-run

# Submit (inside tmux, given the scale -- see Section 3f)
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year 2024
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year 2025

# Check status -- same STATE_FILE as the 2022/2023 script, state_key prefixes
# ("2024:...", "2025:...") keep everything cleanly separated
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year 2024 --check
```
Shares `nmssm_submission_state.json` with the 2022/2023 script -- no separate state file,
`--check` works the same way across both scripts.

### 10f. Real bug hit on first actual submission -- same class as Section 9, but two hardcoded
version strings wrong, not one

First 160-job batch: 0 completed, 6 held, after ~50 minutes. Held job `.err` showed no
Traceback (just a harmless deprecation warning) -- `.out` had the real error:
```
ERROR [ jerc_jet ] No JEC correction:
  Summer24Prompt24_V3_MC_L1L2L3Res_AK4PFPuppiPNetRegressionPlusNeutrino
  - Year: 2024 - Era: MC - Level: L1L2L3Res
```
Traced exactly the same way as Section 9: `jec_version["2024"]["MC"]` hardcodes
`"Summer24Prompt24_V3_MC"`. Loaded the real file (`2024_Summer24/jet_jerc_PNet.json.gz`)
directly and listed all 375 correction names -- every one is **`V5`**, not `V3`, not even `V4`.

**Second, separate bug found while checking the same file**: `jer_version["2024"]` hardcodes
`"Summer24Prompt24_JRV1_MC"`, but every real JER entry in the file is **`JRV2`**. Hadn't
crashed yet only because the JEC error killed the job before ever reaching the JER lookup --
confirmed real and would have failed identically once JEC was fixed.

**Real fix (2 lines, not yet applied upstream):**
```python
jec_version["2024"]["MC"] = "Summer24Prompt24_V5_MC"    # was V3
jer_version["2024"] = "Summer24Prompt24_JRV2_MC"          # was JRV1
```
2025's equivalent entries not yet independently checked against a real file the same way.

**Local workaround** (broadened from Section 9d's pattern -- this time covers all 8
regression-aware systematic names, confirmed via `factories.py`: `jerc_jet_pnet(Nu)(_syst)`,
`jerc_jet_upart(Nu)(_syst)`), applied in `produce_one_mc.py`'s `update_json_config()`:
```python
if "2024" in year or "2025" in year:
    regression_to_plain = {
        "jerc_jet_pnet": "jerc_jet", "jerc_jet_pnetNu": "jerc_jet",
        "jerc_jet_upart": "jerc_jet", "jerc_jet_upartNu": "jerc_jet",
        "jerc_jet_pnet_syst": "jerc_jet_syst", "jerc_jet_pnetNu_syst": "jerc_jet_syst",
        "jerc_jet_upart_syst": "jerc_jet_syst", "jerc_jet_upartNu_syst": "jerc_jet_syst",
    }
    for coll_name in ("corrections", "systematics"):
        coll = config.get(coll_name, {}).get(keyword, [])
        for old_name, new_name in regression_to_plain.items():
            if old_name in coll:
                coll[coll.index(old_name)] = new_name
```
Filed as an addendum to the existing 2023 GitLab issue (same bug class, same file, easier for
whoever picks it up to see both together) rather than a fresh issue.

### 10g. Separate, unrelated bug found the same night: concurrent runs silently losing state

Discovered while running `produce_nmssm_2024_2025.py` from multiple lxplus nodes at once
(easy to do without intending to -- the round-robin lands separate terminal sessions on
different physical nodes automatically). The script held its state-file snapshot in memory
for the whole run; the last process to save overwrote the file with its own stale copy,
silently erasing another process's real progress. **Full recovery process (reconciling
against real EOS output + real in-flight Condor jobs) is documented in Section 6j** -- worth
reading in full if this happens again, since it took two separate reconciliation passes plus
manual cleanup of a few false positives to fully recover.

**Real fix, applied** (not just a workaround) -- `produce_nmssm_2024_2025.py`'s state handling
was rewritten so every check and every write re-reads fresh from disk at that exact moment,
rather than trusting a long-lived in-memory copy:
```python
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"submitted": [], "failed": []}

def is_already_submitted(state_key):
    return state_key in load_state()["submitted"]

def mark_submitted(state_key):
    current = load_state()
    if state_key not in current["submitted"]:
        current["submitted"].append(state_key)
    if state_key in current["failed"]:
        current["failed"].remove(state_key)
    with open(STATE_FILE, "w") as f:
        json.dump(current, f, indent=2)
```
Shrinks the race window from "the whole batch duration" (hours) down to milliseconds around
a single read-modify-write. Not a true lock -- EOS/AFS file locking is unreliable across
different client nodes anyway, which is exactly the situation that caused this bug in the
first place, so a lock wouldn't have reliably helped even if added. A small residual race
still exists (two processes could each see "not submitted" in the same instant and both
submit), but that only produces a harmless duplicate submission -- matching output filenames
just get overwritten -- never the silent data *loss* this fix actually targets.

⚠️ **`produce_xtoyh_signal_mc_2024_robust.py` (2022/2023) has the identical
stale-in-memory-state pattern and has NOT been patched the same way** -- it simply hasn't been
run concurrently across nodes yet the way the 2024/2025 script was. Worth applying the same
fix there before it gets hit by the same bug.

### 10h. Confirmed, recurring gap: `condor_submit` failures slip past `produce_one_mc.py`'s
exit-code check undetected

**Symptom, seen twice** for `2024:NMSSM_X400_Y170` (once) and `2024:NMSSM_X650_Y350` (once,
same night): script prints `[OK] ... submitted.` and records the sample as `submitted` in
state, but the job directory contains only `.sh`/`.sub` files -- no `.err`/`.out` at all,
meaning `condor_submit` never actually created any real Condor jobs. Terminal output at the
time showed `ERROR: Failed to create proc` printed between `Submitting job(s)..` and the
script's own success line.

**Why the existing return-code checks (1b/1c in the changelog) don't catch this**: those check
whether the outer `subprocess.run(command, shell=True, check=True)` call for the *whole*
`produce_one_mc.py` invocation returned non-zero. Apparently `produce_one_mc.py` itself still
exits 0 even when the `condor_submit` step inside it partially or fully fails -- the failure
is happening at a layer underneath what the existing checks actually verify.

**Confirmed real, not a one-off**: happened twice in one session, both times recoverable only
by manually noticing the job directory had no `.err`/`.out` files, removing the falsely-marked
`state["submitted"]` entry, and resubmitting:
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)
before = len(s['submitted'])
s['submitted'] = [k for k in s['submitted'] if k not in ('<state_key_1>', '<state_key_2>')]
print(f'Removed: {before - len(s[\"submitted\"])}')
with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```

**Real fix, not yet implemented**: `run_analysis()` (inside `produce_one_mc.py`) needs to
verify the actual number of Condor jobs created after `condor_submit` returns -- e.g. parsing
`condor_submit`'s own stdout for the "N job(s) submitted to cluster M" confirmation line, or
querying `condor_q` immediately after and checking the cluster genuinely has the expected job
count -- rather than trusting the process's exit code alone, which this confirms is
insufficient on its own.

---

## Pre-flight checklist

- [ ] Write access confirmed on `/eos/cms/store/group/phys_b2g/HHbbgg/sraj/`
- [ ] Valid VOMS proxy (run `voms-proxy-init` interactively *before* backgrounding anything)
- [ ] Spreadsheet updated with claimed samples (background and signal)
- [ ] `produce_all_data.py` and `produce_all_mc.py` edited as in Steps 1–2
- [ ] For NMSSM signal: `--year` is era-qualified (`"2022postEE"`, not `"2022"`) — Section 3c
- [ ] For NMSSM signal: use `--dry-run` (robust script) to validate a new mX block's DAS
      naming pattern before submitting it for real — Section 3h
- [ ] For NMSSM signal: `produce_one_mc.py` uses `--executor vanilla_lxplus`, not `dask/lxplus`
      (confirm with `grep -n "executor\|chunk\|skipbadfiles"` before a large run) — Section 3e
- [ ] Prefer `produce_xtoyh_signal_mc_2024_robust.py` over the plain script for any run you
      might need to interrupt/resume — Section 3h
- [ ] **`micromamba activate higgs-dna`, NOT `conda activate`** — as the first command in any
      new session, followed by `python3 -c "import coffea" && echo "coffea OK"` before doing
      anything else. `conda activate` fails silently and has caused large cascading batches of
      failures — Section 3j
- [ ] Always pass `--era` explicitly, even though it defaults to `2022postEE` — Section 3i.
      The startup "Resuming: N submitted, M failed" line and the final "Done." summary are
      **not** filtered per-era; use `--check --era <name>` for a trustworthy per-era count.
- [ ] Full-grid/long runs launched inside `systemctl --user start tmux.service` +
      `tmux new -s <name>`, **not** bare `nohup ... & disown` — Section 3f. Confirmed `nohup`+
      `disown` alone does NOT survive session end on lxplus9 (`logind`'s
      `KillUserProcesses=yes` kills it anyway); run from and inside `higgs_dna/` itself (not
      `~/` or elsewhere) so relative paths resolve correctly.
- [ ] `voms-proxy-init` **interactively, before** launching anything backgrounded/`tmux`'d — a
      passphrase prompt with no attached terminal hangs the process indefinitely in a `T`
      (stopped) state rather than failing loudly — Section 6g
- [ ] When checking output: use `--check` (robust script) or a recursive
      `find ... -iname "*Events_0*"`, not `countCondorOutputs.py` alone — Section 6d, known
      false-negative for the nested per-variation output structure
- [ ] For a real completeness check (not just "some output exists"): locate the `.sh`/`.sub`
      under `.higgs_dna_vanilla_lxplus/<analysis_name>_<timestamp>/jobs/` and run
      `find_files_resubmit_jobs_no_surviving_events.sh` — Section 6a–6c
- [ ] For held Condor jobs: `condor_q -held -af ClusterId ProcId HoldReason` only gives a
      generic reason — get the real cause from the job's `.err` file directly, `tail -30` not
      the whole file — Section 6f
- [ ] `fetch_datasets()` in `produce_one_mc.py` checks `fetch_datasets_handle.py`'s exit code
      and raises on failure (`subprocess.run(..., check-equivalent)`, not bare `os.system()`) —
      confirmed the script itself already exits 1 correctly on zero files, but the caller
      discards it — Section 6e. Applied and verified working (both directions tested).
- [ ] For a sample with no `.higgs_dna_vanilla_lxplus/` job directory at all: check
      `samples_mc_*.txt/.json` and `runner_mc_*.json` to see which stage silently failed —
      Section 6e. Don't assume it's a pipeline bug; check DAS file count directly first
      (`dasgoclient -query="file dataset=..."`) — see "Known upstream NMSSM production gaps"
- [ ] Before trusting a stale-looking `[?]`/no-output result: check for a stale
      `state["submitted"]` entry (6i) or, for 2023 specifically, the JRV2/JRV3 JER bug
      (Section 9) before assuming it's a new upstream gap
- [ ] If a submission count looks suspiciously LOW (e.g. after running from multiple
      terminals/nodes concurrently): reconcile against real EOS output + real in-flight
      Condor jobs before trusting it or resubmitting — Section 6j. Confirmed real: lost
      150 genuinely-real samples this way in one night.
- [ ] A process launched from a previous login may be on a **different lxplus node** than your
      current session — `pgrep` only sees the local node; check other nodes via SSH before
      concluding nothing is running — Section 6g
- [ ] For 2024/2025: use `produce_nmssm_2024_2025.py`, NOT the 2022/2023 script — different
      dataset naming convention, `--nano 15`, `--year` not era-qualified — Section 10. The
      unconditional "not for final physics" JER warning applies regardless of anything else
      being correct.
- [ ] Run submission scripts from `higgs_dna/`, not from inside `tools_HHbbgg/`

---

## B-tagging uncertainties

B-tag scale factors and their uncertainties are included automatically for MC — no extra flag needed.

- `runner_mc_template.json` lists a b-tag corrector in both `corrections` (central SF applied
  as an event weight) and `systematics` (up/down SF variations computed and stored as weight
  variations).
- `produce_one_mc.py` swaps in the year-appropriate tagger automatically:
  - 2022 / 2023 → `bTagMultiFixedWP_PNetAK4LMTXTXXT` (ParticleNet, fixed working point)
  - 2016 / 2017 / 2018 → `bTagMultiFixedWP_UParTAK4LMTXTXXT_Run2_v15`
- Data jobs carry no b-tag corrector (`runner_data_template.json` has none) — b-tag SFs only
  correct MC to match data, so this is expected.
- Unlike JEC/JER/energy-scale systematics (listed in `variations_mc.json`, which produce
  separate shifted parquet trees), the b-tag uncertainty is a **weight-level** systematic:
  it doesn't create extra trees, it shows up as extra weight branches
  (e.g. `weight_bTagMultiFixedWP_PNetAK4LMTXTXXT_up` / `_down`) alongside the nominal weight
  in the same output parquet file.

### About `bTagSF_hf` / `bTagSF_lf` / `bTagSF_cferr1` / `bTagSF_cferr2` / `bTagSF_hfstats1` / `bTagSF_hfstats2` / `bTagSF_lfstats1` / `bTagSF_lfstats2` / `bTagSF_jes` warnings

If a postprocessing/merge check reports these as "not present -- skipped entirely", that's
expected and not an error. These decorrelated source names belong to a *different* b-tag
corrector — `bTagShapeSF` (continuous shape reweighting) — which is **not invoked anywhere
in this branch's default workflow**. Confirmed: no JSON config in the repo references its
registry names (`deepJet_bTagShapeSF`, `PNet_bTagShapeSF`, `ParT_bTagShapeSF`).

Your production uses `bTagMultiFixedWP_PNetAK4LMTXTXXT` (fixed working point) instead, whose
systematic sources are named `correlated` / `<year>` (uncorrelated), split into
`btagSFlight` (light-flavor) and `btagSFbc` (heavy-flavor) weights — e.g.
`weight_btagSFlight_correlatedUp/Down`, `weight_btagSFbc_2022postEEUp/Down`. That's the real
b-tag uncertainty content in your output; it's just under different column names than the
shape-method sources the check was looking for.

**Decision (as of the multi-era discussion with Bisnupriya):** stay on the correlated/
uncorrelated scheme, not the shape-breakdown one, and this warning is expected noise given
that choice — see the two points below before reconsidering.

1. Official BTV recommendation for multi-era analyses (from the
   [BTV performance-calibration wiki](https://btv-wiki.docs.cern.ch/PerformanceCalibration/SFUncertaintiesAndCorrelations/#ak4-working-point-based-sfs-fixedwp-sfs)):
   > "More than one data-taking era is analyzed: A breakdown of SFb/c and SFlight into
   > up/down_correlated/uncorrelated is to be used." This is what's actually prescribed for
   > our situation — not a simplified fallback relative to the full decorrelated breakdown.
2. HiggsDNA MR !789 (Mintu's breakdown-uncertainty work) adds a `_unct_breakdown` registry
   variant only for `UParTAK4` and `robustParticleTransformer` — **not for PNetAK4**, which
   is what 2022/2023 production actually uses. Even once merged, adopting the breakdown would
   only be possible for 2024/2025, leaving 2022/2023 on correlated/uncorrelated regardless —
   an inconsistent granularity across the dataset, not an improvement.

**`PNet_bTagShapeSF` — added to `runner_mc_template.json`, documented here, not (yet) applied
in the live template file.** Recorded as guidance in case the breakdown decision above is
revisited later, or the shape method is wanted for some other reason:

`PNet_bTagShapeSF` is the correct pairing here (not `deepJet_bTagShapeSF` or `ParT_bTagShapeSF`)
because the fixed-WP corrector already in use, `bTagMultiFixedWP_PNetAK4LMTXTXXT`, tags with
`mva_name="particleNet"` — so the shape corrector needs to read the same discriminant
(`btagPNetB`) to be consistent.

```json
"corrections": {
    "GluGluToHH": ["jerc_jet_pnetNu_syst", "jerc_fatjet_syst", "Pileup", "Smearing", "ElectronVetoSF", "LoosePhoIDSF", "PreselSF", "TriggerSF", "bTagMultiFixedWP_UParTAK4LMTXTXXT", "PNet_bTagShapeSF"]
},
"systematics": {
    "GluGluToHH": ["Pileup", "ScaleEB_Zmmg", "ScaleEE_Zmmg", "ScaleEB_Zee", "ScaleEE_Zee", "Smearing", "ElectronVetoSF", "LoosePhoIDSF", "PreselSF", "TriggerSF", "bTagMultiFixedWP_UParTAK4LMTXTXXT", "LHEScale", "LHEPdf", "PNet_bTagShapeSF"]
}
```

Since this is in the shared template (used for every year 2016–2025 by `update_json_config()`
in `produce_one_mc.py`), it would apply to all years, not just 2022/2023, if ever added for real.

⚠️ **Known limitation if adopted later:** `bTagShapeSF`'s own code explicitly exits with an
error if `particleNet_shape` is requested for `2016preVFP` / `2016postVFP` / `2017` / `2018`
(ParticleNet shape SFs aren't implemented for Run 2 in this branch). If/when Run 2 samples
are produced with this template, that job will fail on this correction and need
`deepJet_bTagShapeSF` (or `ParT_bTagShapeSF`) substituted in for those years instead.

## DAS command reference -- every dasgoclient pattern used in this production

Compiled from actual use throughout this production, not a generic reference -- each command
below is exactly what was run, with the specific question it answers.

### 1. Does a dataset exist at all?
```bash
dasgoclient -query="dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM"
```
Returns the dataset name if it exists, empty if not. This is what `--dry-run` uses internally
for every sample in the grid. **Does not tell you if the dataset is usable** -- an `INVALID`
dataset still returns its name here. Existence at this level is necessary but not sufficient.

### 2. How many files does it have? (the check that first surfaces `INVALID` datasets)
```bash
dasgoclient -query="file dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM" | wc -l
```
Returns a file count. **Silently excludes invalid datasets** -- an `INVALID` dataset returns
`0` here with no indication why, indistinguishable at this level from "never produced." This
is the query `fetch_datasets_handle.py` relies on internally, which is why an `INVALID`
dataset produces a clean `RuntimeError` abort rather than a silent failure (see Section 6e).

### 3. The definitive check -- is it actually usable, and why not if it isn't?
```bash
dasgoclient -query="dataset dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM" -json | python3 -m json.tool | grep -i "access\|status"
```
Run this **first**, before anything else, on any sample showing zero files. Prints
`"dataset_access_type": "INVALID"` or `"VALID"` directly -- the single fastest way to tell a
genuine gap from a deliberate exclusion (see "Known upstream NMSSM production gaps" below).
Saves the entire CLI-vs-web-UI detour that was needed the first time this was diagnosed.

### 4. Real event count, not just file count
```bash
dasgoclient -query="dataset dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM" -json | python3 -m json.tool | grep -i "nevents"
```
Use this before treating a low file count as a real deficit -- confirmed directly that file
count and event count don't always track together (`mX=1000, mY=150`: 2 files but 78,000
events, matching neighbors with 15/22 files almost exactly). One query, no HiggsDNA run
needed, settles the question that would otherwise require a full production attempt.

### 5. Wildcard search when the exact campaign tag is unknown or might have changed
```bash
dasgoclient -query="dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/*/NANOAODSIM"
```
Used this to resolve the historical `X500_Y125`/`X800_Y50` version-mismatch note (`v2-v2` vs
`v2-v4`) -- returns every campaign this dataset has ever been produced under, whatever the
real current tag is, rather than guessing.

### 6. Discovering an unfamiliar naming convention (used for 2024/2025)
```bash
dasgoclient -query="dataset=/NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/*/NANOAODSIM"
dasgoclient -query="dataset=/NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/*/*AODSIM"
```
2024/2025 uses a genuinely different, hyphenated dataset naming convention from 2022/2023
(confirmed directly, not assumed) -- the second query (`*AODSIM` instead of `NANOAODSIM`
specifically) also catches MiniAOD-only datasets, useful for checking which processing tiers
actually exist before assuming NanoAOD is available.

### Diagnostic order, given everything learned tonight

For any sample showing zero files or otherwise looking wrong:
1. Command 3 (`access_type`) **first** -- settles `INVALID` vs. genuinely-need-to-investigate
   immediately, before spending time on anything else.
2. If `VALID` but file count still looks low relative to neighbors: Command 4 (`nevents`) --
   settles real deficit vs. chunking artifact.
3. Only if both come back clean (`VALID`, comparable event count) and the pipeline still can't
   fetch it: worth checking the DAS web UI directly and/or `--dbs-instance` alternatives, since
   at that point something genuinely unusual is going on worth escalating.

---

## Known upstream NMSSM production gaps (not pipeline bugs)

### Root cause, found and confirmed for every zero-file case hit so far: `dataset_access_type: INVALID`

Every "zero files" gap encountered across this entire production (five confirmed cases, listed
below) traces to exactly the same mechanism: **the dataset was deliberately invalidated in
DBS by central production**, not a genuine absence of data, a DBS bug, or a `dasgoclient`
flakiness issue -- despite it initially looking like all three of those in turn while this was
being diagnosed.

**The definitive, one-command check** for any future "zero files" sample:
```bash
dasgoclient -query="dataset dataset=<full dataset path>" -json | python3 -m json.tool | grep -i "access_type"
```
- `"dataset_access_type": "INVALID"` -> deliberately excluded by central production. Not
  fixable by retry, different `--dbs-instance`, waiting, or any pipeline-side change. Exclude
  from `NMSSM_Samples` and move on -- this is the expected, correct outcome, not a bug.
- `"dataset_access_type": "VALID"` combined with genuinely zero files -> that *would* be a real
  anomaly worth escalating; not what's been found in any case so far.

**Why this took several wrong turns to actually find**, worth understanding so it's faster
next time: `dasgoclient -query="file dataset=..."` and the `filesummaries` service both
silently exclude invalid datasets by default, returning a bare `0` with no indication *why* --
indistinguishable at first glance from "never produced," "still processing," or "transient DBS
issue." The DAS **web UI's raw file listing**, however, can still show the underlying files
that exist in storage even for an invalidated dataset (confirmed directly: 6 real files with
real sizes shown for a dataset whose CLI/summary query said zero) -- which is what made this
initially look like a CLI-vs-web-UI inconsistency or a stuck DBS republish, before checking
`dataset_access_type` directly settled it. The invalidation flag is the actual, complete
explanation; the file listing discrepancy is just a side effect of it.

### Confirmed `INVALID` datasets (12, as of 2026-08-25)

| mX | mY | Era | Confirmed via |
|---|---|---|---|
| 1000 | 700 | 2022postEE | `dataset_access_type: INVALID` |
| 240 | 100 | 2022postEE | `dataset_access_type: INVALID` |
| 450 | 125 | 2022postEE | `dataset_access_type: INVALID` |
| 800 | 500 | 2023preBPix | `dataset_access_type: INVALID` |
| 950 | 300 | 2023preBPix | `dataset_access_type: INVALID` |
| 700 | 550 | 2022preEE | `dataset_access_type: INVALID` |
| 750 | 150 | 2022preEE | `dataset_access_type: INVALID` |
| 350 | 200 | 2023postBPix | `dataset_access_type: INVALID` |
| 700 | 500 | 2023postBPix | `dataset_access_type: INVALID` |
| 800 | 50 | 2024 | `dataset_access_type: INVALID` -- first confirmed 2024 case, same root cause, different naming convention (`NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-800-MY-50...`) |
| 500 | 125 | 2024 | `dataset_access_type: INVALID` -- caught despite passing `--dry-run`'s surface-level `[OK]` (dataset *name* resolves in DAS even though it's invalid and has 0 files) -- worth remembering `--dry-run`'s `[OK]` only confirms the dataset name exists, not that it's valid/populated; spot-checking access_type on samples that look fine is still worthwhile |
| 850 | 250 | 2022preEE | `dataset_access_type: INVALID` |

All twelve: excluded from `NMSSM_Samples` (see 3d/10), so the robust script's retry logic
doesn't keep chasing them. Do not resubmit -- an `INVALID` flag is not expected to change.

**Two false alarms, checked and cleared (2026-08-25)** -- worth recording so they aren't
re-flagged and re-investigated later: `2022preEE:NMSSM_X350_Y200` (12 files) and
`2022postEE:NMSSM_X700_Y95` (11 files) both looked low at first glance, but neighbor
comparison showed they're consistent with normal point-to-point variation, not a deficit --
`X350_Y170` (a neighbor of the first) has only 4 files, and `X700_Y90`/`Y100` (neighbors of
the second) have 12/20 -- both `VALID`, not `INVALID`. Always check at least one neighbor
before concluding a lowish file count is a real gap, the same lesson as the still-open
`X1000_Y150` question below.

**Spread across all four eras** -- 2022postEE (3), 2022preEE (2), 2023preBPix (2),
2023postBPix (2). Nine points across all four eras, no obvious pattern in mX or mY values
shared between them -- consistent with routine, scattered invalidation during central
production/reprocessing rather than a systematic gap tied to any particular mass region.

### RESOLVED: `mX=1000, mY=150` -- file-count "deficit" was a chunking artifact, not a real gap

Originally flagged as suspicious: only **2 files** vs. 15 (`mY=125`) and 22 (`mY=170`) --
superficially the same shape as the original `mX=600, mY=150` "Signal Yield Anomaly" finding.

**Checked and fully resolved, 2026-08-24:**
- `dataset_access_type`: **VALID** for all three (`mY=125`, `mY=150`, `mY=170`) -- ruled out
  the invalidation explanation (Section above) for this case.
- Real event counts (`nevents` from DBS `filesummaries`, not file count):

| mY | Files | Events |
|---|---|---|
| 125 | 15 | 77,310 |
| 150 | 2 | 78,000 |
| 170 | 22 | 75,000 |

All three within ~4% of each other. `mY=150`'s low file count was purely a **chunking
artifact** -- its MC happened to be packed into 2 large files (~39,000 events each) rather than
many smaller ones, not a genuine event-level deficit. **No real production gap here.**

**Scope of this resolution, worth being precise about:** this specifically refutes the
file-count-based concern for `mX=1000, mY=150`. It does **not** retroactively invalidate the
*original* `mX=600, mY=150` finding from the AN/status-update deck -- that one was based on
actual measured preselection yields from real HiggsDNA output (a direct measurement), a
meaningfully stronger claim than DAS file count. This case is a useful, concrete illustration
of exactly why file count alone is an unreliable proxy for event count, and worth remembering
that lesson before flagging a similar-looking pattern as suspicious in the future -- check
`nevents` directly (one `dasgoclient` query, no HiggsDNA run needed) before assuming a low
file count means a real deficit.

### Consolidated report, if/when reporting to whoever owns central NMSSM production

Given the root cause is now understood (deliberate invalidation, not a gap), a report is lower
priority than originally thought -- these datasets were excluded on purpose by whoever manages
central production, presumably for a real reason (bad conditions, superseded reprocessing,
etc.). Worth a brief informational note rather than a bug report: nine NMSSM signal mass
points across all four eras (2022preEE, 2022postEE, 2023preBPix, 2023postBPix) are currently
`INVALID` in DBS -- confirming this is expected/known (rather than an oversight) would close
this out completely.

---


- The `--year` value passed downstream to `produce_one_data.py` / `produce_one_mc.py`
  (used for metaconditions like `Era2022_v1` and JEC corrections like `jec_pnetNu_Data2022`)
  is unaffected by the output-path edits in Sections 1–2 — it still uses the full string
  (`2022preEE`, `2023postBPix`, etc.). Only the **output path** was changed there. For the
  NMSSM signal script (Section 3), the era-qualified string is required for the command to
  run at all (Section 3c), not just for path construction.
- Output parquet filenames are derived from each input NanoAOD file's UUID, so splitting
  preEE/postEE and preBPix/postBPix (and per-mass-point for signal) into separate subfolders
  avoids any naming collisions and keeps era-level provenance visible in the directory structure.
- NMSSM signal dataset names are **not** guessed from a general convention — each mX block's
  campaign tag should be confirmed either against real resolved xrootd file paths (as done for
  mX=1000) or a live `dasgoclient` pre-flight check (as done for mX=300, Section 3d) before
  submitting. Different mass points can land in different production campaigns/hashes; don't
  assume uniformity across the full mX grid.