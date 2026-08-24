# NMSSM Signal Production — Command Reference

Companion to the full narrative guide (`higgsdna_2022_2023_production_guide.md`) -- this file
is commands only, no explanation. See the full guide for *why* each of these matters.

Working directory for all commands below:
```
/afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/v7_parquet_production/HiggsDNA/higgs_dna
```
(the HiggsDNA repo -- distinct from this `hhbbgg_AwkwardAnalyzer` repo where this README lives)

---

## 0. Every new session, in this exact order

```bash
micromamba activate higgs-dna
python3 -c "import coffea" && echo "coffea OK"
voms-proxy-init --rfc --voms cms -valid 192:00
voms-proxy-info
```
⚠️ `conda activate higgs-dna` fails silently (`EnvironmentNameNotFound`) and causes a
cascading `ModuleNotFoundError: No module named 'coffea'` on every subsequent sample. Always
`micromamba`, never `conda`, for this env.

---

## 1. Long/unattended runs -- `tmux.service`, not `nohup`

```bash
systemctl --user start tmux.service
tmux new -s nmssm_<era>
# ... run Section 0 + Section 2/2b commands inside this session ...
# Ctrl+B, D to detach
```
Reattach (same node it started on):
```bash
tmux ls
tmux attach -t nmssm_<era>
```
`nohup ... & disown` does **not** survive session end on lxplus9 (`logind` kills it anyway).

---

## 2. Submission -- 2022/2023 (`produce_xtoyh_signal_mc_2024_robust.py`, `--era`)

```bash
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era> --dry-run
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era>
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era> --check
```
`<era>` is one of: `2022preEE`, `2022postEE`, `2023preBPix`, `2023postBPix`. Always pass it
explicitly. Dataset naming: `NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8`
(underscored).

## 2b. Submission -- 2024/2025 (`produce_nmssm_2024_2025.py`, `--year`) -- separate script

```bash
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year <year> --dry-run
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year <year>
python3 submission/tools_HHbbgg/produce_nmssm_2024_2025.py --year <year> --check
```
`<year>` is `2024` or `2025` (NOT era-qualified, unlike 2022/2023). `--nano 15`
(NanoAODv15), not 12. Dataset naming is **different**:
`NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8` (hyphenated).
2024 and 2025 share the exact same underlying dataset (confirmed -- no separate 2025 MC
production exists), split automatically by event ID inside `produce_one_mc.py` based on
`--year` alone -- no `--split-mc` CLI flag exists or is needed.
Shares `nmssm_submission_state.json` with the 2022/2023 script; `state_key` prefixes
(`"2024:..."`, `"2025:..."`) keep everything separated, `--check` works the same way.

⚠️ **Unconditional caveat**: `jet_systematics_json.py` explicitly warns 2024/2025 JER is
preliminary and output "should not be used for a final physics result." Applies regardless of
anything else being correct.

---

## 3. Monitoring

```bash
# Overall job status
condor_q -submitter <user>

# Held jobs -- reason is always generic, need the .err (or .out -- see below) for the real cause
condor_q -submitter <user> -held -af ClusterId ProcId HoldReason

# Get the real error for one held job
ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null
tail -30 $(ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null)

# If .err has no Traceback (just warnings): check .out instead -- the real
# error can be there, especially for correction-lookup failures
cat .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.out | tail -30

# Is the submission script still alive? (local node only)
pgrep -af produce_xtoyh_signal_mc_2024_robust
pgrep -af produce_nmssm_2024_2025

# Check other nodes if not found locally (lxplus round-robins)
for node in lxplus947 lxplus960 lxplus976 lxplus982 lxplus990 lxplus994; do
    echo "=== $node ==="
    ssh -o StrictHostKeyChecking=accept-new $node.cern.ch "pgrep -af produce_xtoyh_signal_mc_2024_robust; pgrep -af produce_nmssm_2024_2025" 2>/dev/null
done

# Is a found PID actually alive, or stuck?
\ps -o pid,stat,etime,pcpu,cmd -p <pid>     # STAT: S/R = alive, T = stuck, kill -9 it
kill -9 <pid>                                # -9 specifically -- plain kill can hang forever
```

---

## 4. Completeness check (per sample, real proof beyond "some output exists")

```bash
bash submission/tools_HHbbgg/find_files_resubmit_jobs_no_surviving_events.sh \
    .higgs_dna_vanilla_lxplus/<analysis_name>_<timestamp>/jobs/AN-<keyword>.sh \
    /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/<keyword>/
```
Find the right `.sh` first:
```bash
find .higgs_dna_vanilla_lxplus/ -name "*<keyword>*.sh"
```

---

## 5. Recursive output count (bypasses `countCondorOutputs.py`'s false-negative)

```bash
find /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/<keyword>/ -iname "*Events_0*" | wc -l
```

---

## 6. DAS checks

```bash
# 2022/2023 naming (underscored)
dasgoclient -query="dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM"

# 2024/2025 naming (hyphenated, Par- prefix)
dasgoclient -query="dataset=/NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM"

# How many files does it actually have?
dasgoclient -query="file dataset=<full dataset path above>" | wc -l

# Wildcard search if the exact campaign tag is unknown/might have changed
dasgoclient -query="dataset=<dataset path with */NANOAODSIM instead of CAMPAIGN>"
```
Confirmed real campaign strings:
- `2022preEE`: `Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2`
- `2022postEE`: `Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2`
- `2023preBPix`: `Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v2`
- `2023postBPix`: `Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2`
- `2024`/`2025` (shared): `RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2`

---

## 7. Removing stale `state["submitted"]` entries (marked submitted, but no real output)

**Always confirm before removing** -- check DAS/`condor_q`/output directory first, per Sections
3-6. Never blanket-clear; always target specific confirmed-stale keys.

```bash
python3 -c "
import json

with open('nmssm_submission_state.json') as f:
    s = json.load(f)

stale = [
    '<era_or_year>:NMSSM_X<mX>_Y<mY>',
    # ... one per confirmed-stale key
]

before = len(s['submitted'])
s['submitted'] = [k for k in s['submitted'] if k not in stale]
print(f'Removed {before - len(s[\"submitted\"])} of {len(stale)} targeted entries')

with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```
Verify it actually took:
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)
print('still present:', '<era_or_year>:NMSSM_X<mX>_Y<mY>' in s['submitted'])
"
```
To clear ALL entries for one era/year at once (e.g. before a full resubmit after a fix):
```bash
python3 -c "
import json
with open('nmssm_submission_state.json') as f:
    s = json.load(f)
prefix = '<era_or_year>:'   # e.g. '2024:'
s['submitted'] = [k for k in s['submitted'] if not k.startswith(prefix)]
s['failed'] = [k for k in s['failed'] if not k.startswith(prefix)]
with open('nmssm_submission_state.json', 'w') as f:
    json.dump(s, f, indent=2)
"
```

---

## 8. Merge / postprocess

Merged output now goes to a **separate top-level directory**, not nested inside the raw
per-sample tree (moved there 2026-08-24 for cleaner browsing/eventual raw-chunk cleanup):
```bash
python scripts/postprocessing/prepare_output_file.py \
    --input  /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/ \
    --output /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask_merged/<year>/<era>/ \
    --merge --syst --varDict submission/tools_HHbbgg/variations_mc.json
```
Confirm output landed:
```bash
find /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask_merged/<year>/<era>/ -maxdepth 2 | head -30
```
`postEE`'s merged output was moved from the old nested location via:
```bash
mv /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/2022/sim/postEE/merged \
   /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask_merged/2022/postEE
```
(EOS same-namespace `mv` is a fast rename, not a byte copy)

---

## 9. Known open issues (updated 2026-08-24)

- **2023preBPix / 2023postBPix**: `jerc_jet_pnetNu_syst` crashes (`IndexError: map::at`) --
  `jer_version` dict hardcodes `JRV2`, actual `_PNet`-suffixed JER files use `JRV3`. Local
  workaround applied in `produce_one_mc.py` (`update_json_config()`, falls back to plain
  `jerc_jet_syst` for `"2023" in year`). Confirmed producing complete, correct output. Real
  fix (`jer_version` JRV2→JRV3) filed as a GitLab issue, not applied upstream yet.

- **2024 (likely 2025 too)**: bigger version of the same bug class -- **two** hardcoded
  version strings stale, not one: `jec_version["2024"]["MC"]` hardcoded `V3` (real file has
  `V5`), `jer_version["2024"]` hardcoded `JRV1` (real file has `JRV2`). Broke all 8
  regression-aware systematics (`jerc_jet_pnet(Nu)(_syst)`, `jerc_jet_upart(Nu)(_syst)`).
  **Actual fix used (not a code patch)**: a colleague's copy of `jet_jerc_PNet.json.gz`
  (`/eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/systematics/JSONs/POG/JME/2024_Summer24/`)
  is pinned to `V3`/`JRV1` -- matching what the code expects -- confirmed directly before
  copying. Simpler than patching `jec_version`/`jer_version` forward to `V5`/`JRV2`, since it
  needed zero code changes:
  ```bash
  cp /eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/systematics/JSONs/POG/JME/2024_Summer24/jet_jerc_PNet.json.gz \
     systematics/JSONs/POG/JME/2024_Summer24/
  ```
  Also needed for 2024 -- a missing b-tag efficiency file:
  ```bash
  mkdir -p systematics/JSONs/bTagEff/2024_Summer24
  cp /eos/user/b/bsahu/HiggsDNA_v7_dask/HiggsDNA/higgs_dna/systematics/JSONs/bTagEff/2024_Summer24/HHbbgg.json \
     systematics/JSONs/bTagEff/2024_Summer24/
  ```
  Confirmed via local `futures`-executor test: the `No JEC correction` error is gone after
  the file swap. Not yet confirmed via a full Condor-submitted job actually completing --
  the local interactive test hit an unrelated `SIGKILL`/OOM (expected on a shared login node
  running full JEC/JER+regression locally; the real submission path requests dedicated 30GB
  per job and should not hit this).

- **`mX=1000, mY=700` (2022postEE only)**: 0 files in DBS, confirmed twice. Excluded from
  `NMSSM_Samples`. Fine in the other three eras.
- **`mX=240, mY=100`**, **`mX=450, mY=125`** (2022postEE): 0 files in DBS, confirmed. Excluded.
- **`mX=1000, mY=150`**: file count far below neighbors (2 vs 15-22) at 2022postEE/2023preBPix;
  normal at 2022preEE/2023postBPix. Event-count comparison still pending -- file count alone
  doesn't confirm a real deficit.