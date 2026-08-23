# HiggsDNA Repo — Changes Made (2026-08-22/23 session)

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

---

## 2. `submission/tools_HHbbgg/fetch_datasets_handle.py`, `split_nanoaod.py`

**Not something changed this session** -- confirmed via file timestamp (`01:02`, predating
the first production run of the day at `02:05`) that `fetch_datasets_handle.py` was already
copied in and wired up (via `produce_one_mc.py`'s `fetch_datasets()` already pointing at it)
*before* this session started. Originally assumed this was a fix applied tonight; corrected
once the timestamp evidence came in. No action needed here -- these files were already in
place.

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
```