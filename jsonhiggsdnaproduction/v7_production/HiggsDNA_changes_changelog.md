# HiggsDNA Repo — Changes Made (2026-08-22 through 08-24 session)

Personal record of everything actually changed in the `HiggsDNA` repo
(`submission/tools_HHbbgg/`) during this session. Scoped to HiggsDNA only -- doc/README
changes live separately in `hhbbgg_AwkwardAnalyzer/jsonhiggsdnaproduction/`.

Confidence levels used below:
- **CONFIRMED (tested)** -- applied, and independently proven working via a real terminal
  test that specifically exercised the change (not just "ran without crashing elsewhere").
- **CONFIRMED (applied)** -- verified present in the live file via direct inspection
  (`sed`/`grep`), but not independently stress-tested against the specific failure mode it's
  meant to guard against.
- **RECOMMENDED, not confirmed applied** -- discussed and given as exact code, but no terminal
  output ever confirmed it actually landed in the live file. Check before assuming it's there.

---

## 1. `submission/tools_HHbbgg/produce_one_mc.py`

### 1a. Executor: `dask/lxplus` → `vanilla_lxplus` — **CONFIRMED (tested)**

`run_analysis()`'s command string changed from:
```python
f"--executor dask/lxplus "
f"--chunk 3000 "
f"{memoryLine}"
f"--debug "
f"--skipbadfiles "
```
to:
```python
f"--executor vanilla_lxplus "
f"{memoryLine}"
f"--debug "
```
(`--chunk`/`--skipbadfiles` removed entirely -- both Dask-specific, meaningless under
`vanilla_lxplus`.) The old `dask/lxplus` block was kept as a commented-out block above the new
one, for reference -- can be deleted for tidiness, purely cosmetic either way.

**Reason:** `dask/lxplus` starts a Dask scheduler in the foreground process that must stay
alive for the entire chunked run -- this, not the submission step itself, was what kept
terminals tied up for a sample's full processing duration. `vanilla_lxplus` submits and
returns once jobs are queued, matching `produce_one_data.py`'s existing pattern.

**Tested:** confirmed via real production runs (`X850_Y50` and many others) showing the new
command string executing and submitting cleanly.

### 1b. `fetch_datasets()` -- check subprocess return code, raise on failure — **CONFIRMED (tested)**

Before:
```python
def fetch_datasets(sample_file, dbs_instance='prod/global', region='Yolo'):
    command = f"python submission/tools_HHbbgg/fetch_datasets_handle.py -i {sample_file} -w {region} --dbs-instance {dbs_instance}"
    os.system(command)
```
After:
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
Requires `import subprocess` added near the top of the file (confirmed not already present,
added alongside the existing `import os`).

**Reason:** `fetch_datasets_handle.py` itself already correctly detects a zero-file dataset and
exits 1 -- but `os.system()`'s return code was being silently discarded, so a genuinely-missing
dataset (e.g. `NMSSM_X1000_Y700`, `NMSSM_X240_Y100`, `NMSSM_X450_Y125` -- all confirmed 0 files
in DBS) produced no error at all: no job directory, no Condor submission, nothing -- just
silent absence, only discoverable via a completeness check days later.

**Tested both directions:**
- Zero-file case (`NMSSM_X1000_Y700`): confirmed raises `RuntimeError` cleanly, execution
  stops before `run_analysis.py` is ever invoked.
- Real-data case (`NMSSM_X300_Y50`): confirmed runs through normally, submits to Condor as
  usual -- the change doesn't interfere with the success path.

### 1c. `run_analysis()` -- same return-code check pattern — **RECOMMENDED, not confirmed applied**

Discussed and given as:
```python
result = subprocess.run(command, shell=True)
if result.returncode != 0:
    raise RuntimeError(
        f"run_analysis.py failed (exit code {result.returncode}) for {keyword} -- "
        f"check condor_q, some jobs may have already been submitted before the failure."
    )
```
in place of the bare `os.system(command)` at the end of `run_analysis()`. **Never independently
verified this was actually applied to the live file** -- no terminal output confirmed it the
way 1a/1b were confirmed. Check `grep -n "subprocess.run\|os.system" submission/tools_HHbbgg/produce_one_mc.py`
before assuming this landed.

### 1d. 2023 JRV2/JRV3 JER workaround — **CONFIRMED (tested)**

Inside `update_json_config()`, inserted right after the existing `("2022", "2023")` bTag
substitution block:
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
**Confirmed via `sed -n '120,140p'` showing the real inserted block, correct indentation.**
**Confirmed tested:** `NMSSM_X350_Y100` (a sample that previously crashed with
`IndexError: map::at`) ran through completely, producing a full, correctly-structured output
directory (`nominal/` + every expected JEC/JER/Scale/Smearing/AK8 variation subfolder).

⚠️ **This is a physics-content change, not a pure bugfix** -- affected 2023 samples get JEC
without PNet-regression-plus-neutrino awareness for JER specifically, unlike 2022 samples. Real
fix belongs in `jet_systematics_json.py`'s `jer_version` dict (see Section 3 below) -- not
applied there; this is a local, scoped workaround only.

### 1e. 2024 JEC/JER version mismatch — **NOT a code change** (see Section 2b instead)

⚠️ **Important correction to avoid confusion later**: a broadened version of the 1d-style
code patch (`regression_to_plain` dict, swapping all 8 regression-aware systematic names --
`jerc_jet_pnet(Nu)(_syst)`, `jerc_jet_upart(Nu)(_syst)` -- to their plain equivalents for
`"2024"`/`"2025"` in year) was **discussed and given as exact code, but deliberately NOT
applied**. A colleague's suggestion (verified before use, see Section 2b) turned out to fix
the same symptom with zero code changes -- a file swap instead. If you're reading this later
and see references to a `regression_to_plain` patch elsewhere in this session's notes, that
approach was superseded, not layered on top of the file fix. `produce_one_mc.py`'s
`update_json_config()` has **no 2024/2025-specific block** -- only the `"2023" in year` block
from 1d exists there. Confirm with:
```bash
grep -n 'if "2024"\|if "2025"' submission/tools_HHbbgg/produce_one_mc.py
```
Expect this to return nothing related to `regression_to_plain` -- if it does, something
unexpected happened and this note is out of date.

---

## 2. `submission/tools_HHbbgg/fetch_datasets_handle.py`, `split_nanoaod.py`

**Not something changed this session** -- confirmed via file timestamp (`01:02`, predating
the first production run of the day at `02:05`) that `fetch_datasets_handle.py` was already
copied in and wired up (via `produce_one_mc.py`'s `fetch_datasets()` already pointing at it)
*before* this session started. Originally assumed this was a fix applied tonight; corrected
once the timestamp evidence came in. No action needed here -- these files were already in
place.

### 2b. `systematics/JSONs/POG/JME/2024_Summer24/jet_jerc_PNet.json.gz` — **replaced, CONFIRMED (tested)**

Real fix for the 2024 JEC/JER version mismatch (1e). The file that had been auto-pulled into
this area was version-mismatched with the code (`V5`/`JRV2` in the file vs. `V3`/`JRV1`
hardcoded in `jec_version`/`jer_version`). A colleague's copy, pinned to `V3`/`JRV1` -- the
version the code actually expects -- was verified directly (loaded and inspected before
copying, confirmed correction names literally say `V3`/`JRV1`) then copied over:
```bash
cp /eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/systematics/JSONs/POG/JME/2024_Summer24/jet_jerc_PNet.json.gz \
   systematics/JSONs/POG/JME/2024_Summer24/
```
**Tested:** local `futures`-executor run of `NMSSM_X240_Y50` (2024) confirmed the
`ERROR [ jerc_jet ] No JEC correction: ...` that crashed 100% of jobs before is gone after
this swap. **Not yet confirmed** via a real Condor-submitted job completing end to end and
producing output on EOS -- the local test hit an unrelated `SIGKILL`/OOM (expected for a
memory-heavy full JEC/JER+regression run on a shared login node; the real submission path
requests dedicated 30GB per job via Condor and shouldn't hit this).

⚠️ This file is presumably subject to being auto-overwritten again by a future
`pull_files.py --all` run, the same way it got out of sync in the first place -- worth
re-verifying the version any time that script is rerun for 2024/2025.

### 2c. `systematics/JSONs/bTagEff/2024_Summer24/HHbbgg.json` — **added, new file, not previously present**

Didn't exist at all before this session for 2024. Copied from the same colleague's working
area:
```bash
mkdir -p systematics/JSONs/bTagEff/2024_Summer24
cp /eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/systematics/JSONs/bTagEff/2024_Summer24/HHbbgg.json \
   systematics/JSONs/bTagEff/2024_Summer24/
```
Not independently verified this is actually needed/used yet (production hadn't gotten far
enough to exercise a b-tag-efficiency-dependent code path before hitting the JEC error above)
-- copied proactively based on the colleague's stated list of required files, not because a
specific error demonstrated its necessity. Worth confirming it's actually read once a 2024
job completes successfully.

### 2d. `submission/tools_HHbbgg/produce_nmssm_2024_2025.py` — **new file, not an edit to existing code**

Entirely new script, built this session specifically for 2024/2025 (kept separate from the
2022/2023 script -- see the full guide's Section 10 for the reasoning: different dataset
naming convention, `--nano 15` not 12, `--year` not era-qualified, no `--split-mc` CLI flag).
Shares `nmssm_submission_state.json` with the existing 2022/2023 script via `state_key`
prefix (`"2024:..."`/`"2025:..."`). Full source lives in this session's outputs, not
reproduced here -- this changelog only tracks changes to *existing* HiggsDNA files.

---

## 3. NOT changed -- filed as an issue instead, deliberately

`higgs_dna/systematics/jet_systematics_json.py`, `jer_version` dict:
```python
"2023preBPix": "Summer23Prompt23_RunCv1234_JRV2_MC",   # should be JRV3
"2023postBPix": "Summer23BPixPrompt23_RunD_JRV2_MC",     # should be JRV3
```
This is the *real* fix for the JRV2/JRV3 bug (Section 1d works around it locally instead).
**Deliberately not applied** -- this is shared code affecting every analysis on this HiggsDNA
branch (background MC included), not owned by this analysis's own scripts. Filed as a GitLab
issue instead of editing directly; supporting evidence (both years' `changes.md`, dated
2026-06-05, describing a JER tag reorganization) included in the issue text.

**Addendum filed to the same issue (2026-08-24):** the analogous 2024 bug (1e/2b) --
`jec_version["2024"]["MC"]` should be `"Summer24Prompt24_V5_MC"` (was `V3`),
`jer_version["2024"]` should be `"Summer24Prompt24_JRV2_MC"` (was `JRV1`) -- **if** the
upstream fix direction is "update the code to match the newer files," rather than "pin the
files back to what the code expects" (which is what was actually done locally instead, see
2b). Worth flagging to whoever picks up the issue that both directions are valid and someone
should decide which one becomes the permanent fix.

`higgs_dna/submission/tools_HHbbgg/produce_one_mc.py`, `detect_year_era_from_name()`:
missing `"2025"` branch discussed early in this session (would silently fall back to CLI
default year for a 2025 filename) -- **never confirmed as actually applied**. Not urgent given
no 2025 production has happened yet, but worth checking/adding before it's needed.

---

## Quick self-check commands, next time you sit down to this

```bash
# Confirm 1a (executor)
grep -n "vanilla_lxplus\|dask/lxplus" submission/tools_HHbbgg/produce_one_mc.py

# Confirm 1b (fetch_datasets return-code check)
grep -n -A5 "def fetch_datasets" submission/tools_HHbbgg/produce_one_mc.py

# Confirm 1c (run_analysis return-code check) -- NOT independently confirmed, check for real
grep -n -A5 "os.system(command)\|subprocess.run(command" submission/tools_HHbbgg/produce_one_mc.py

# Confirm 1d (JRV2/JRV3 workaround)
grep -n -A8 'if "2023" in year' submission/tools_HHbbgg/produce_one_mc.py

# Confirm 3 (upstream fix still not applied)
grep -n "2023preBPix\|2023postBPix" higgs_dna/systematics/jet_systematics_json.py | grep JRV

# Confirm 2b (2024 JEC/JER file swap -- should show V3/JRV1, not V5/JRV2)
python3 -c "
import gzip, json
with gzip.open('systematics/JSONs/POG/JME/2024_Summer24/jet_jerc_PNet.json.gz') as f:
    data = json.load(f)
print([c['name'] for c in data.get('corrections', []) if 'L2L3Residual' in c['name']][:1])
"

# Confirm 2c (b-tag efficiency file present)
ls -la systematics/JSONs/bTagEff/2024_Summer24/HHbbgg.json

# Confirm 1e (no 2024/2025 code patch was actually applied -- should return nothing)
grep -n 'if "2024"\|if "2025"' submission/tools_HHbbgg/produce_one_mc.py
```