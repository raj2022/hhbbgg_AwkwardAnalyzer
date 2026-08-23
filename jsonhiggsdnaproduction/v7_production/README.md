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
# ... run Section 0 + Section 2 commands inside this session ...
# Ctrl+B, D to detach
```
Reattach (same node it started on):
```bash
tmux ls
tmux attach -t nmssm_<era>
```
`nohup ... & disown` does **not** survive session end on lxplus9 (`logind` kills it anyway).

---

## 2. Submission

```bash
# Validate campaign tags before submitting -- read-only, safe to run any time
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era> --dry-run

# Submit for real (resumable -- safe to Ctrl+C and rerun)
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era>

# Check status any time, from any node, without touching a run in progress
python3 submission/tools_HHbbgg/produce_xtoyh_signal_mc_2024_robust.py --era <era> --check
```
`<era>` is one of: `2022preEE`, `2022postEE`, `2023preBPix`, `2023postBPix`. Always pass it
explicitly.

---

## 3. Monitoring

```bash
# Overall job status
condor_q -submitter <user>

# Held jobs -- reason is always generic, need the .err for the real cause
condor_q -submitter <user> -held -af ClusterId ProcId HoldReason

# Get the real error for one held job
ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null
tail -30 $(ls .higgs_dna_vanilla_lxplus/*/jobs/*.<clusterid>.<procid>.err 2>/dev/null)

# Is the submission script still alive? (local node only)
pgrep -af produce_xtoyh_signal_mc_2024_robust

# Check other nodes if not found locally (lxplus round-robins)
for node in lxplus947 lxplus960 lxplus982 lxplus990 lxplus994; do
    echo "=== $node ==="
    ssh -o StrictHostKeyChecking=accept-new $node.cern.ch "pgrep -af produce_xtoyh_signal_mc_2024_robust" 2>/dev/null
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
# Does a dataset resolve at all?
dasgoclient -query="dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM"

# How many files does it actually have?
dasgoclient -query="file dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/<CAMPAIGN>/NANOAODSIM" | wc -l

# Wildcard search if the exact campaign tag is unknown/might have changed
dasgoclient -query="dataset=/NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>_TuneCP5_13p6TeV_madgraph-pythia8/*/NANOAODSIM"
```

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
    '<era>:NMSSM_X<mX>_Y<mY>',
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
print('still present:', '<era>:NMSSM_X<mX>_Y<mY>' in s['submitted'])
"
```

---

## 8. Merge / postprocess

```bash
python scripts/postprocessing/prepare_output_file.py \
    --input  /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/ \
    --output /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/ \
    --merge --syst --varDict submission/tools_HHbbgg/variations_mc.json
```
Confirm output landed:
```bash
find /eos/cms/store/group/phys_b2g/HHbbgg/<user>/HiggsDNA_v7_dask/<year>/sim/<era>/merged/ -maxdepth 2 | head -30
```

---

## 9. Known open issues (2026-08-23)

- **2023preBPix / 2023postBPix**: `jerc_jet_pnetNu_syst` crashes (`IndexError: map::at`) --
  `jer_version` dict hardcodes `JRV2`, actual `_PNet`-suffixed JER files use `JRV3`. Local
  workaround already applied in `produce_one_mc.py` (`update_json_config()`, falls back to
  plain `jerc_jet_syst` for `"2023" in year`). Confirmed producing complete, correct output.
  Real fix (`jer_version` JRV2→JRV3) belongs upstream, not yet applied there.
- **`mX=1000, mY=700` (2022postEE only)**: 0 files in DBS, confirmed twice. Excluded from
  `NMSSM_Samples`. Fine in the other three eras.
- **`mX=240, mY=100`**, **`mX=450, mY=125`** (2022postEE): 0 files in DBS, confirmed. Excluded.
- **`mX=1000, mY=150`**: file count far below neighbors (2 vs 15-22) at 2022postEE/2023preBPix;
  normal at 2022preEE/2023postBPix. Event-count comparison still pending -- file count alone
  doesn't confirm a real deficit.