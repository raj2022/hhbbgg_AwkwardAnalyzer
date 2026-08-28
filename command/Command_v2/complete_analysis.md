# Complete Analysis Pipeline: Commands Reference

This document records the full command sequence for the X→YH→bbγγ resonant
search analysis, from pDNN training through event categorization.

---
## 0. Activate the env
as of 08/23/2026, we changed the env to `micromamba` as it faster and also removed cache from the afs:
```bash
micromamba activate hhbbgg-awk
```

---

## 1. Train the Parameterized DNN

Two training entry points are maintained side by side, differing only in
whether correlation-pruned features are used.

**Without correlation-pruned variables**
Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation`

```bash
python pDNN_v_WC.py
```

**With correlation-pruned variables**
Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working`

```bash
python pDNN_v2.py
```

Both save to `outputs/models/`: `best_pdnn.pt`, `scaler.pkl`, `features.json`.
Training grid: X ∈ {300, ..., 1000}, Y ≥ 90 (Y=90 included).

Also produces, per run: ROC/score-distribution/calibration plots, permutation
+ gradient feature importance, correlation-based feature pruning (dropping
redundant feature pairs at |r| ≥ 0.95 on real, non-imputed values, keeping
whichever has higher standalone AUC), and mass-sculpting validation (weighted
KS test comparing the background `diphoton_mass` shape at each pDNN score cut
against no cut).

### 1.1 Extended mass-sculpting validation: m_bb and 2D (m_gg, m_bb)

**Reviewer comment (this session): check pDNN mass sculpting in `m_bb` and
the 2D `(m_gg, m_bb)` plane, not just `m_gg`.** The built-in check above
(`run_mass_sculpting()` in both `pDNN_v2.py`/`pDNN_v_WC.py`) only ever
checks the diphoton-mass proxy -- confirmed directly by reading the source,
`MASS_SCULPT_CANDIDATES` has no `m_bb`/dijet-mass entry at all, and no 2D
check exists anywhere in either script.

**No retraining needed for either addition below** -- `Res_dijet_mass` (the
`m_bb` proxy) is already a member of `FEATURES_CORE` in both training
scripts, so it is already present in the saved `df_te` test split without
any change to the training pipeline itself.

**New, standalone script**: `check_mass_sculpting_mjj_2d.py`, run from the
same directory as whichever training script (`pDNN_v2.py` or
`pDNN_v_WC.py`) was actually used, and imports from that same module by
name -- **confirm the import line matches the training script actually in
use in that directory** before running (`pDNN_Without_Correlation/`'s copy
imports from `pDNN_v_WC`; the correlation-pruned copy would need
`pDNN_v2` instead). Loads the already-saved model/scaler (never refits
either -- `scale_features()`'s refit-and-overwrite behavior is
deliberately never called), reproduces the same TEST split deterministically
(same seed, same `GroupShuffleSplit` calls as the original training run),
and fails loudly (not silently) if the recomputed feature list doesn't
match what was saved to `features.json`, rather than risk evaluating on a
mismatched split.

```bash
python check_mass_sculpting_mjj_2d.py
```

Produces, alongside the existing `MassSculpting/` outputs:
- `mass_sculpting_mjj_shapes` -- the `m_bb` analog of the existing `m_gg`
  background-shape-vs-score-cut overlay, same weighted KS test method
- `mass_sculpting_2d_shapes` -- genuine 2D `(m_gg, m_bb)` background
  histograms, side by side across score cuts, for direct visual inspection
- `mass_sculpting_2d_correlation_vs_cut` -- the background-only
  `m_gg`-`m_bb` Pearson correlation at each score cut, a quantitative check
  for induced 2D correlation that neither 1D marginal would catch alone

**Status: built and tested against a synthetic model with a deliberately
injected sculpting effect (confirmed the KS test and correlation check both
detect a real, known effect, not just that the script runs without
crashing) -- not yet run against real production data.** Treat results from
a real run as the first genuine check, not yet cross-validated against a
second mass point or a second background composition.

**Axis-range fix, applied to the existing `m_gg` check too.** The default,
data-driven x-axis range (`np.nanpercentile(m_bkg, [1, 99])`) was pulling
the plotted lower bound down to ~50 GeV, well below the analysis's actual
SR mass window (95+ GeV) -- purely because the background sample isn't
pre-filtered to that window, not because that range is physically
meaningful to show. Fixed via a new optional `x_min` parameter on
`plot_mass_after_score()` (kept optional, not a hardcoded default, since
the same function is reused for `m_bb`, which has a genuinely different,
wider real range where a fixed 95 GeV bound would be wrong); `95.0` is
passed specifically at the `m_gg` call site in `run_mass_sculpting()`.
Applied identically to both `pDNN_v2.py` and `pDNN_v_WC.py` (confirmed
their `plot_mass_after_score()`/`run_mass_sculpting()` functions are
character-for-character identical, despite the different filenames) and
to the new script's own 2D plot's `m_gg` axis (`mgg_x_min=95.0`, `m_bb`
axis left on its own genuine data-driven range).

---

## 2. Train the ttH Killer

Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/tth_killer`

```bash
python tth_killer_v2.py
```

**Outputs (consumed by step 3.2 below):**
- `best_tth_killer.pt` — best-ValAUC model checkpoint
- `scaler_tth.pkl` — StandardScaler fit on the training split

---

## 3. Score Samples

Both trained networks are applied per sample folder, **in the same folder,
one after the other**, so that both score branches end up in the same
files before the analyzer step. Order matters only in that both must run
before step 4 — they don't depend on each other's output.

**Systematics note:** by default (no `--all-systematics`), only the
`nominal` subfolder is scored — folder-based systematic variations
(`jec_syst_Total_up`, `Smearing_down`, `ScaleEB_Zee_up`, ...) are skipped.
Pass `--all-systematics` to score those too. For a genuine "with
systematics" run, this flag must be passed consistently to **both**
inference scripts (3.1 and 3.2) *and* the analyzer (step 4) — if only the
analyzer gets it, it will read variation-folder files that were never
actually scored and silently fall back to `NaN`-filled `pDNN_score` /
`ttH_killer_score` for them.

### 3.1 Score with the Trained pDNN

Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation`

**Nominal only (default):**
```bash
python inference_PDnn_updated.py \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/ \
  --recursive
```


**With all systematics:**
```bash
python inference_PDnn_updated.py \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/ \
  --recursive --all-systematics
```

Due to space constraints for systematics at the Rachel's EOS area, we are moving to the B2G eos, `/eos/cms/store/group/phys_b2g/HHbbgg/sraj`
the updated command: 

**With all systematics:**
```bash
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/ \
  --recursive --all-systematics
```


(2022postEE example, same flags: `-i /eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7/2022postEE/merged/`)

- `--recursive` is required: samples live in a nested
  `<mass_point>/<systematic>/NOTAG_merged.parquet` structure (one folder
  per signal mass point, one subfolder per systematic variation), not the
  old flat one-file-per-sample layout. Flat background/data files (no
  such nested structure) are handled in the same pass, mixed in with the
  nested signal tree, in the same or a separate `-i` location — no
  signal-specific assumption anywhere in the file-discovery logic.
- `(mass, y)` is auto-detected per file from its own `NMSSM_X###_Y###`
  folder name; background/data files (no such pattern in their path) fall
  back to `--mass-const`/`--y-const`.
- **Mass-grid scope**: only signal points with X >= 300 and Y >= 90 are
  scored (`--min-mass`/`--min-y`, both inclusive, defaults 300/90).
  Out-of-scope points found on disk (e.g. `NMSSM_X700_Y60`) are skipped
  and logged, never touched. Background/data files are always kept
  regardless of this restriction.
- Feature list is loaded from `outputs/models/features.json` (falls back
  to `features_used.json` if present instead).

**Output:** mirrors the input structure under `merged/scored/`, e.g.
`merged/scored/NMSSM_X700_Y500/nominal/NOTAG_merged.parquet`, with
`pDNN_score` (and the resolved `mass`/`y_value`) added as new columns.

#### Checking for missing mass points

Before or after scoring, `check_missing_masses.py` scans a folder of
`NMSSM_X<mass>_Y<y>` subdirectories against the expected 196-point signal
grid (X=300-1000) and reports missing, incomplete, and out-of-grid points:

```bash
python sample_study/Check_missing_mass/Check_missing_masses_folder.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7/2022postEE/merged \
  --require-file NOTAG_merged.parquet
```

`--min-y` (default 90) suppresses known out-of-scope low-Y clutter from the
"extra folders" report, collapsing it into a one-line count instead.

### 3.2 Score with the Trained ttH Killer

Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/tth_killer`

**Nominal only (default) — input is the pDNN-scored `scored/` folder from 3.1:**
```bash
python inference_ttH_killer.py \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/scored/ \
  --recursive \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
```

**With all systematics:**
```bash
python inference_ttH_killer.py \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
```
after storage update:
```bash
python inference_ttH_killer.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/ \
  --recursive --all-systematics \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
```

Run once per sample folder — **the same folders scored in step 3.1** — to
attach the `ttH_killer_score` branch alongside the existing `pDNN_score`
branch in each file. Files are updated **in place** by default (both
scores end up in the same file); pass `--output` to instead mirror into a
separate directory. Both branches must be present before step 5, since
the categorization script's ttH-killer pre-split (`--tth-cut`) reads
`ttH_killer_score` directly from the tree.

We have created the file `pDNN_ttH_inference_chain.sh`, can submit all file for DNN and ttH at once 
from `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer`
```bash
bash pDNN_ttH_inference_chain.sh 
```
---

## 4. Run the Analyzer

The analyzer performs full sample processing, including data-driven (DD)
background estimation, weight-based systematic histogram filling, and
template fitting.

**Nominal only (default):**
```bash
python hhbbgg_analyzer_with_systematics.py \
  --config-years 2024 --era All \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/data/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/sim/scored/ \
  --tag DD_2024
```

**With all systematics** (requires 3.1 and 3.2 above to have also been run
with `--all-systematics`, so the variation-folder files actually carry
real `pDNN_score`/`ttH_killer_score` values):
```bash
python hhbbgg_analyzer_with_systematics.py \
  --config-years 2024 --era All \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/data/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/sim/scored/ \
  --tag DD_2024 \
  --all-systematics
```

(2022–2023 example, same flags: replace `-i` with the per-era
`preEE/postEE/preBPix/postBPix` `scored/` directories and
`--config-years 2022,2023`.)

**Example to run for 2022 PostEE, preEE:**
```bash
# --- 2022 preEE ---
python -u hhbbgg_analyzer_with_systematics.py \
  --config-years 2022 --era preEE \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/preEE/merged/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/scored/ \
  --tag DD_2022preEE \
  --all-systematics

# --- 2022 postEE ---
python -u hhbbgg_analyzer_with_systematics.py \
  --config-years 2022 --era postEE \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/scored/ \
  --tag DD_2022postEE \
  --all-systematics
  ``` 

for 2023:
# --- 2023 preBPix ---
```bash
python -u hhbbgg_analyzer_with_systematics.py \
  --config-years 2023 --era preBPix \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2023/sim/preBPix/merged/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/scored/ \
  --tag DD_2023preBPix \
  --all-systematics

# --- 2022 postEE ---
```bash
python -u hhbbgg_analyzer_with_systematics.py \
  --config-years 2023 --era postBPix \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2023/sim/postBPix/merged/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/ \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/scored/ \
  --tag DD_2023postBPix \
  --all-systematics
  ``` 
> **Filename/flag note.** This document uses `hhbbgg_analyzer_lxplus_par.py`
> with `--config-years` (plural), matching the script's actual `argparse`
> definition and everything fixed/tested in this conversation. A
> differently-named copy (`hhbbgg_analyzer_multiple.py`) using
> `--config-year` (singular) has also been seen in practice — confirm
> which file is actually deployed before relying on either flag name; the
> two are not confirmed to be the same script.

- Each `-i` directory is searched **recursively**, handling both the flat
  background/data layout and the nested `<mass_point>/<systematic>/*.parquet`
  signal layout in the same pass.
- **Sample identity** is resolved per file, not from the leaf filename
  alone: falls back to the nearest non-systematic parent directory (e.g.
  `NMSSM_X700_Y500`, `DDQCCDGJets`) whenever the basename is a generic
  placeholder like `NOTAG_merged` — every file in the newer HiggsDNA-style
  production is named identically, so basename-only naming would silently
  collide unrelated samples onto the same output path. The old flat
  convention (unique, descriptive basenames) is unaffected.
- **Systematic dimension**: histogram and tree output paths are now
  `sample/systematic/region[/variable]`, with `"nominal"` as an explicit
  value. Weight-based systematics (`Pileup`, `TriggerSF`, `PreselSF`,
  `ElectronVetoSF`, and the 8-way b-tag SF family) are filled
  automatically for every nominal-folder MC file — no flag needed, no new
  input files required, histograms only (not duplicated as full event
  trees, since kinematics are identical to nominal). `--all-systematics`
  additionally processes the folder-based (JEC/JER/Smearing/Scale)
  variation directories, each getting its own single pass at that
  folder's own label with the nominal weight (object-level and
  weight-level systematics are evaluated independently, not combined).
- `weight_central` is not used anywhere in this script's weight
  computation (confirmed to have no role in this pipeline's
  normalization) — systematic-varied weights are applied by direct
  substitution into the same `weight × xsec × lumi` formula nominal uses,
  swapping in `weight_<syst>Up/Down` for `weight`.
- By default (no `--all-systematics`), only `nominal` is processed (plus
  flat files with no systematic-folder structure) — a systematic-variation
  file that was never scored would otherwise crash on the missing
  `pDNN_score` column.

### 4.0 Output structure, resumability, and the trees/histograms split (this session)

**Critical, confirmed-live bugs and fixes -- read before running a real
`--all-systematics` job.** The analyzer's output structure changed twice
this session, both times in direct response to a real crash, not as a
design preference:

**Round 1 -- single output file crashed under `--all-systematics`.**
Originally, ONE `hhbbgg_analyzer-v2-trees.root` was opened once for the
entire run and every sample streamed into it. Confirmed live crash:
```
struct.error: 'i' format requires -2147483648 <= number <= 2147483647
```
`2147483647` is exactly `2^31-1` -- `uproot`'s classic-ROOT-format write
cascade uses 32-bit integers for internal file offsets, which overflow
once a single output file crosses roughly 2GB. Nominal-only output never
hit this (too small); the ~15x volume increase from
`--all-systematics` does. **Fix: one tree file per sample** --
`hhbbgg_analyzer-v2-trees__<sample>.root`.

**Round 2 -- per-sample splitting alone was not fine-grained enough.** A
second live crash showed the mechanism more precisely: it is NOT a hard
"file > 2GB" ceiling -- files well over 2GB (`GGJets_MGG-80_Rescaled.root`
at 3.2GB, `GluGluHtoGG.root` at 2.8GB) completed successfully. The crash
specifically happens when a NEW internal directory needs creating (a
not-yet-seen sample/systematic/region combination) AFTER the file has
already grown past the offset limit -- further writes to an
ALREADY-existing directory are just appends, which don't hit this code
path even at large size. A large background MC sample with many
systematic variations can exceed the limit within its OWN file, once a
later systematic needs fresh directories. **Fix: split by
`(sample, systematic)` instead of sample alone** --
`hhbbgg_analyzer-v2-trees__<sample>__<systematic>.root`. Since each input
parquet file already corresponds to exactly one systematic (folder
structure `<mass_point>/<systematic>/*.parquet`), this maps naturally
onto existing per-file boundaries.

**Histogram output has its OWN, separate bug, fixed independently.**
Unlike trees, histogram output was never split -- it stayed one file,
`hhbbgg_analyzer-v2-histograms.root`, written via `ROOT.TFile(...,
"RECREATE")`. `RECREATE` truncates any existing file. `HIST_CACHE` (the
in-memory accumulator) only ever knows about whatever samples THIS
invocation processed. Consequence, confirmed live: running a second,
targeted invocation to fill in one missing sample **silently overwrote
and destroyed** the full histogram file from the earlier, larger run --
no warning, no error, just gone. **Fix: unique, timestamped filename per
run** -- `hhbbgg_analyzer-v2-histograms__<YYYYMMDD_HHMMSS>.root`. Every
invocation now writes its own file; nothing is silently destroyed. If you
lost a histogram file this way before this fix and have no earlier
backup, it is not recoverable from the file itself -- must be
regenerated by rerunning that scope of samples.

**Resumability: skip-if-already-done for tree output.** Since a real run
can span many hours and may need interrupting/resubmitting, each
`(sample, systematic)` group's output file is checked before
reprocessing: if it already exists AND is genuinely readable (opened
and `.keys()` called, not just checked for existence), it is skipped.
Existence alone is deliberately NOT trusted -- the group that was
mid-write when a crash happened has a partial file on disk that
`uproot.recreate()` never finalized, and would be silently left corrupt
forever if skipped on existence alone. Re-running the exact same full
command after a crash will automatically pick up only what's missing.

**Merging back to one file per output type, once a run (or its
resumed continuations) is fully done:**
```bash
cd outputfiles/merged/<tag>
hadd hhbbgg_analyzer-v2-trees.root hhbbgg_analyzer-v2-trees__*.root
hadd hhbbgg_analyzer-v2-histograms.root hhbbgg_analyzer-v2-histograms__*.root
```
`hadd` is ROOT's own native merge tool (real C++ ROOT, not `uproot`) and
does not share `uproot`'s 32-bit write-cascade limitation -- this is the
standard, correct way to get back to one convenient file for downstream
use after writing in safe-sized pieces. Keep the per-sample/per-run
pieces after merging (don't delete) as a safety net in case a merge
needs re-running or one sample needs re-checking in isolation.

**Caution when mixing old (round-1) and new (round-2) tree filenames in
the same output directory.** Samples completed under the OLD
`<sample>.root` naming (no systematic suffix) will NOT be recognized by
the new skip-check (which looks for `<sample>__<systematic>.root`), and
`categorize_events.py`'s glob would pick up BOTH old and new files for
the same sample if both are left in place -- silently double-counting
that sample's events downstream. Move old-scheme files to a separate
location before resuming under the new scheme:
```bash
mkdir -p ../<tag>_round1_completed
for f in hhbbgg_analyzer-v2-trees__*.root; do
  # old scheme has exactly one "__"; new scheme has two
  [ "$(echo "$f" | grep -o '__' | wc -l)" -eq 1 ] && mv "$f" ../<tag>_round1_completed/
done
```

**`--skip-trees` / `--skip-histograms`: run the two output types in
separate passes.** Added so a "trees now, histograms later" workflow
(faster for filling in remaining samples, since it skips the
histogram-filling work) doesn't require manually commenting out code:
```bash
# Trees only (this pass, e.g. to finish remaining backgrounds)
python hhbbgg_analyzer_with_systematics.py ... --all-systematics --skip-histograms

# Histograms only, once ALL trees are complete -- run as ONE invocation
# covering every sample together (not split per sample like the trees
# were), so HIST_CACHE accumulates everything into a single output file
# and no hadd is needed for histograms at all in this case:
python hhbbgg_analyzer_with_systematics.py ... --all-systematics --skip-trees
```
Passing BOTH flags together raises an immediate error (would process
every file for zero output). Passing NEITHER (the default) does both in
one pass, unchanged from the original behavior.

**Output (updated):** `outputfiles/merged/<tag>/hhbbgg_analyzer-v2-trees__<sample>__<systematic>.root`
(many files) and `hhbbgg_analyzer-v2-histograms__<timestamp>.root` (one
per invocation) -- merge with `hadd` as shown above to get back the
familiar single `hhbbgg_analyzer-v2-trees.root` /
`hhbbgg_analyzer-v2-histograms.root` for downstream use.

```bash
cd outputfiles/merged/DD_2024
hadd hhbbgg_analyzer-v2-trees.root hhbbgg_analyzer-v2-trees__*.root
hadd hhbbgg_analyzer-v2-histograms.root hhbbgg_analyzer-v2-histograms__*.root
```

### 4.1 Validate Data/MC Agreement

Inspect Data/MC plots from the merged output using `hhbbgg_Plotter.py`:

**Nominal (default):**
```bash
python hhbbgg_Plotter.py \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-histograms.root
```
e.g. this is for only with preEE
```bash
(hhbbgg-awk) [sraj@lxplus950 hhbbgg_AwkwardAnalyzer]$ python hhbbgg_Plotter.py --root outputfiles/merged/DD_2022preEE/hhbbgg_analyzer-v2-histograms__20260826_200635.root 
```
**A specific systematic** (e.g. to inspect a weight-based variation's
shape, or a folder-based one if `--all-systematics` was used upstream):
```bash
python hhbbgg_Plotter.py \
  --root outputfiles/merged/DD_2024_AllSyst/hhbbgg_analyzer-v2-histograms.root \
  --systematic PileupUp
```


# Doc update: §4.1 Validate Data/MC Agreement -- multi-file and auto-discovery support

**Insert after the existing `--root`/`--systematic` examples, before "Other
flags."** This supersedes the earlier §4.3.1 recommendation to pre-`hadd`
histogram files together before plotting -- that recipe is still valid if
you need a genuine single combined file for some other downstream purpose,
but for `hhbbgg_Plotter.py` specifically, it's no longer necessary: the
plotter can now read and combine multiple files directly.

### Plotting multiple years/eras together, without pre-merging

`hhbbgg_Plotter.py`'s `--root` argument is now repeatable, and combines
whatever files you pass at PLOT TIME -- summing matching Data/MC bases
across all of them, with no intermediate merged file ever written to
disk:

```bash
python hhbbgg_Plotter.py \
  --root DD_2022_combined/hhbbgg_analyzer-v2-histograms.root \
  --root DD_2023_combined/hhbbgg_analyzer-v2-histograms.root
```

Confirmed working correctly even when different years use completely
different real-data directory naming (`DataC_NOTAG_merged` for 2022 vs
`DataCv1EG0_NOTAG_merged` for 2023, per §4.3) -- summing is driven by
the resolved base name ("Data"), not the raw directory name, so no
special-casing per year is needed.

### Auto-discovery by year: `--years` / `--base-dir`

For the common case of "just plot these years together," `--years`
resolves each year to its histogram file automatically, so you don't
need to remember or type out the exact file path each time:

```bash
# Only 2023
python hhbbgg_Plotter.py --years 2023 --base-dir outputfiles

# 2022 + 2023
python hhbbgg_Plotter.py --years 2022,2023 --base-dir outputfiles

# 2022 + 2023 + 2024
python hhbbgg_Plotter.py --years 2022,2023,2024 --base-dir outputfiles

# Only 2024
python hhbbgg_Plotter.py --years 2024 --base-dir outputfiles
```

For each requested year, `--years` looks for (in order):
1. `<base-dir>/DD_<year>_combined/hhbbgg_analyzer-v2-histograms.root`
2. `<base-dir>/DD_<year>/hhbbgg_analyzer-v2-histograms.root`
3. If neither exists yet, the most RECENT (by actual modification time,
   not filename) `hhbbgg_analyzer-v2-histograms__*.root` under either
   directory.

**Discovery is loud, not silent** -- it always prints exactly which
file was picked for each year and which rule matched (`exact` vs.
`latest-timestamped`), e.g.:
```
[INFO] --years given: resolving ['2022', '2023'] under base dir 'outputfiles'...
[INFO]   2022 -> outputfiles/DD_2022_combined/hhbbgg_analyzer-v2-histograms.root  (matched via: exact)
[INFO]   2023 -> outputfiles/DD_2023_combined/hhbbgg_analyzer-v2-histograms.root  (matched via: exact)
```
Always check this line before trusting the resulting plots -- a wrong
`--base-dir`, or an unexpected directory-naming convention for a given
year, would show up here immediately rather than silently plotting the
wrong (or no) data.

### Pointing at one specific file still works exactly as before

`--years` is purely additive -- it doesn't change or replace the plain
`--root` usage:
```bash
# A single, specific file -- unaffected by any of the above
python hhbbgg_Plotter.py --root outputfiles/DD_2024/hhbbgg_analyzer-v2-histograms.root
```

### Mixing explicit files with auto-discovery

`--root` and `--years` can be combined in the same call -- useful for
adding one extra or non-standard file alongside auto-discovered years:
```bash
python hhbbgg_Plotter.py \
  --root outputfiles/some_special_one_off_file.root \
  --years 2024 --base-dir outputfiles
```

### Status

Auto-discovery logic (`resolve_year_to_root_file()`) confirmed via
direct testing against a realistic mixed directory structure (some
years with an explicit, already-`hadd`'d filename; a year with only
timestamped files still present) -- correctly picks the exact-named
file when present, and correctly picks the genuinely newest
timestamped file by modification time (not alphabetical/filename
order) when it isn't. The multi-file summing logic
(`gather_across_sources()`) is confirmed via direct testing with real
synthetic multi-year fixtures: MC weighted yields sum exactly across
files, and Data sums correctly across files even when each year uses a
different real-data naming convention. The full plotting pipeline
(matplotlib figure generation, real `variables.py`/`normalisation.py`
integration) has not been run end-to-end outside the real analysis
environment -- confirm a real run reproduces the same plots as before
for the single-file case before relying on the multi-file case for
anything final.


---
> **Note (§4.0):** `--root` above assumes the merged, single-file
> histogram output (`hadd`'d from `hhbbgg_analyzer-v2-histograms__*.root`
> per §4.0) -- `hhbbgg_Plotter.py` itself was not changed and still
> expects one file, not a directory of per-run pieces.

Other flags: `--outdir` (default `stack_plots/`, nested as
`<outdir>/<systematic>/<region>/<var>.{png,pdf}`), `--blind` (blinds the
signal-mass window in `dibjet_mass`/`diphoton_mass`; off by default).

**Fixed since the last pass through this document** (previously listed as
"known issue, blocked" — now applied):
- **Critical path-structure break**: histogram paths were still
  `sample/region/variable`, missing the `systematic` segment the
  analyzer now writes (`sample/systematic/region/variable`). Every
  `path in up` lookup was silently failing — not a crash, just every
  plot showing "nothing to draw." Fixed by threading a `--systematic`
  CLI argument (default `"nominal"`) through every path construction.
- **`dir_to_base()`'s DD-template regex** now matches `DDQCCDGJets`
  (2024 naming) as well as `DDQCDGJET_Rescaled` (2022 naming), mirroring
  the identical fix already applied to the analyzer's `is_dd_template()`.
- **A separate, previously-unnoticed bug found while testing the above**:
  the `GGJets_(high|low)_Rescaled` DD-template check used `re.match`,
  which anchors to the start of the string — silently failing on any
  era-prefixed name (`2022_preEE_GGJets_high_Rescaled`), misclassifying
  that DD template as a plain `GGJets` background instead. Changed to
  `re.search`.
- `--root`, `--outdir`, `--blind` are now proper CLI arguments instead of
  hardcoded values in `main()`.

**Still deferred, not yet applied** (lower priority, flagged but
intentionally not bundled into the above):
- `lumi_label()` is still a hardcoded, manually-commented single value
  per year/era combination — easy to silently plot with the wrong
  luminosity if the wrong line is left uncommented. Should eventually be
  computed the same way the analyzer does (`getLumi(year, era)`),
  CLI/config-driven rather than hand-edited source.
- `mc_bases` / `signal_bases` are still hardcoded, manually-maintained
  lists (most of the 196-point signal grid is commented out). Could
  auto-discover `NMSSM_*` bases from the file's own top-level directories
  instead of requiring manual upkeep per mass point.

### 4.2 Multi-year (2022/2023) analyzer fixes -- found when actually running the eras this session, not caught by the 2024-only testing that preceded it

**Read before running `--config-years 2022` or `2023` for the first time.** All
three of these were confirmed live, on real 2022postEE production data, not
found by inspection -- the §4 "2022-2023 example, same flags" note as written
before this pass would reproduce the crash below exactly.

**1. Hard crash: `Res_lead_bjet_btagUParTAK4B` doesn't exist for 2022/2023.**
```
awkward.errors.FieldNotFoundError: no field 'Res_lead_bjet_btagUParTAK4B'
in record with 71 fields
```
The UParT b-tag discriminant columns (`Res_lead_bjet_btagUParTAK4B`,
`Res_sublead_bjet_btagUParTAK4B`) are genuinely 2024/2025-only in the real
production schema -- confirmed directly, not assumed. The analyzer's own code
comment already said *"for 2024 and 2025"*, but the columns were still
listed in `required_columns` unconditionally, with no year/schema gate at
all. **Fixed**: checked per-file against the parquet schema (`has_upart`),
exactly mirroring the pattern the script already used for
`ttH_killer_score` -- falls back to `NaN` for both branches when absent,
uses the real values unchanged when present (2024/2025).

**2. Year-specific uncorrelated b-tag SF weight columns were never actually
found for 2022/2023 -- a naming bug, not a genuine missing-upstream-data
gap.** The analyzer was constructing column names like
`weight_btagSFbc_2022Up`, but the real production schema (confirmed
directly from a full branch list off a real 2022postEE file) uses
`weight_btagSFbc_2022postEEUp` -- the sub-era is baked into the branch
name, not just the year. Every 2022/2023 file was silently printing
`[WARN] ... missing year-specific uncorrelated b-tag SF column(s)`, even
though the columns were sitting right there under a slightly different
name. **Fixed**: new `weight_column_era_suffix(year, era)` mapping,
producing `2022preEE`/`2022postEE`/`2023preBPix`/`2023postBPix` for
2022/2023 (2024/2025 unaffected -- those still use the year alone, which
was already correct). Confirmed the corrected construction matches the
real schema exactly.

**This same fix also resolves the correlated-vs-uncorrelated systematic
question directly, with no further work needed.** `bTagSF_bc_correlated`/
`bTagSF_light_correlated` (in `WEIGHT_SYSTEMATICS`) already use one FIXED
nuisance name regardless of year/era -- so `combineCards.py` naturally
treats them as one shared, correlated uncertainty across every era, exactly
as intended. The uncorrelated pair only needed its constructed name to
actually vary per sub-era (which it now does, via the fix above) for
Combine to correctly treat `2022preEE`'s and `2022postEE`'s uncorrelated
components as genuinely independent nuisances rather than accidentally
sharing a name. The STRUCTURE was already right; only the uncorrelated
branch's name construction was wrong.

**3. Weight-systematic missing-column warnings were firing on every
non-nominal (folder-based systematic) file, not just nominal ones --
noisy, not incorrect.** `Pileup`/`TriggerSF`/`PreselSF`/`ElectronVetoSF`/
`bTagSF_*` are only ever actually USED for nominal-folder files (see §4's
own description of `systematic_passes` -- object-level variation folders
reuse the nominal weight). The missing-column check itself, though, ran
unconditionally for every file, so a file like
`NMSSM_X1000_Y100/ScaleEB_Zee_down/NOTAG_merged.parquet` would print
`[WARN] missing weight-systematic column(s) for [...]` even though those
columns were never expected to exist there in the first place, and their
absence has zero effect on that file's actual processing. **Fixed**: both
the general and the per-flavor b-tag warning now only print when
`folder_systematic == "nominal"` -- a genuine missing-column gap on an
actual nominal file still prints exactly as before; the noise on every
other systematic-variation file is gone.

**Updated `hhbbgg_analyzer_with_systematics.py` reflecting all three fixes,
verified via unit tests against the real column names and log output from
this session, available on request.**



---
# Doc updates: multi-era combination (2022, 2023) -- insert into Complete Analysis Pipeline: Commands Reference

## Update 1 -- add to §4.1's "Fixed since the last pass through this document" list

- **`dir_to_base()`'s Data-directory detection missed the real per-era
  naming convention entirely.** The original regex, `(^|_)Data(_|$)`,
  requires an underscore or end-of-string immediately after "Data" --
  but this production's real convention is `DataE`/`DataF`/`DataG`
  (2022) and `DataCv1EG0`/`DataDv2EG1`-style (2023) -- an era/version
  letter glued on directly, no separator. Confirmed as a complete,
  not partial, failure: every single Data directory in a real
  2022preEE histogram file was silently classified as `base=None` and
  dropped by `group_by_base_from_keys()`, meaning `data_hist` stayed
  `None` for every one of 806 region/variable jobs and **zero plots
  were ever written**, with no error at all. Fixed: `n.lower().
  startswith("data")` -- a simple, case-insensitive prefix check,
  confirmed correct against every real Data naming variant seen across
  both years with no false-positive risk against any real MC/signal
  base name in this analysis (none start with "data").

## Update 2 -- add a warning to §4.0's `hadd`-based merge guidance

**`hadd` has a confirmed, reproducible failure mode on real tree data
from this pipeline -- do not treat it as unconditionally safe for tree
merging anymore.** While merging 2022 preEE+postEE tree output,
`hadd` entered what looks like an unbounded internal `TObjArray`-
resizing loop merging `GGJets_MGG-80_Rescaled`'s tree files:
```
Error in <TObjArray::At>: index 117 out of bounds (size: 117)
... (dozens of times) ...
Error in <TObjArray::At>: index 234 out of bounds (size: 234)
... (dozens more) ...
```
`117 -> 234` is an exact doubling -- consistent with some internal
ROOT structure growing without the merge ever completing. The process
never terminated on its own and had to be killed manually; the target
output file was left at 0 bytes. This was reproduced **identically
writing to local `/tmp`**, ruling out EOS/network flakiness (the cause
of a separate, earlier corruption incident in this pipeline's bias-test
work) as the explanation. Both source files were independently
confirmed healthy and readable, with byte-identical branch names and
counts (101, confirmed via both `uproot` and ROOT's own `rootls`) --
ruling out a schema mismatch too. **The exact root cause inside `hadd`'s
C++ implementation was never identified.**

**Fix: a new tool, `uproot_hadd_replacement.py` (standalone) /
`combine_trees_across_eras.py` (the full multi-file, era-aware
combination tool, see §4.3 below) -- reads both trees' full contents
via `uproot` and writes the concatenated result via `uproot`'s own
tree writer, entirely bypassing `hadd`'s C++ merge code.** This is the
exact same `uproot`-native read/write pattern this pipeline's own
analyzer already uses successfully (`write_tree_chunked()` in
`hhbbgg_analyzer_with_systematics.py`) -- not a new, unproven approach.
Confirmed working on the exact real file pair that broke `hadd`: every
region matched exactly (`srbbgg`: `5651+15810=21461`, confirmed
correct; every other region -- `preselection`, `crantibbgg`, etc. --
also confirmed exact). **For merging TREE output specifically, use this
tool instead of `hadd` going forward.** `hadd` remains fine for
HISTOGRAM output (the `DDQCDGJets_Rescaled` tree file, by contrast,
merged via `hadd` with a confirmed-correct entry count with no issue at
all -- this is not a blanket "never use `hadd`" finding, just a
confirmed real failure on at least one real file, with no known way to
predict in advance which files might trigger it).

## Update 3 -- new section, insert after §4.2

### 4.3 Multi-era combination (2022, 2023): histograms and trees

Once both sub-eras of a year are fully processed (§4.2), combining them
requires two SEPARATE combination steps -- histograms (for
`hhbbgg_Plotter.py` validation) and trees (for categorization, §5) --
because `build_pdnn_categories.py` reads exclusively from tree output,
never histograms. Combining histograms does nothing to help
categorization; they must each be combined independently.

**Both combination steps share the same underlying risk, confirmed
directly, not assumed: background and data for 2022 (and 2023) are
processed from a FLAT, non-era-split directory, meaning the exact same
physical Data files get reprocessed independently under both era
labels.** Confirmed via direct comparison of the two eras' output:

- **2022**: both `preEE` and `postEE` show the identical five
  directories -- `DataC_NOTAG_merged`, `DataD_NOTAG_merged`,
  `DataE_NOTAG_merged`, `DataF_NOTAG_merged`, `DataG_NOTAG_merged`.
- **2023**: both `preBPix` and `postBPix` show the identical twelve
  directories -- `DataCv1EG0_NOTAG_merged` through
  `DataDv2EG1_NOTAG_merged`.

**Background and signal MC do NOT have this problem** -- each
sub-era's MC is a genuinely distinct sample, correctly lumi-scaled per
event (`weight x xsec x getLumi(year, era)`), and confirmed to sum
correctly to the true full-year value (e.g. 2022 `preEE` + `postEE`
lumi: `7.9804 + 26.6717 = 34.6521 fb^-1`, matching the analysis's own
documented full-2022 luminosity). Only DATA needs special handling.

#### 4.3.1 Combining histograms

Since histogram output nests all samples inside one file
(`sample/systematic/region/variable`), the duplicate-Data problem must
be fixed by DELETING the duplicate directories from a copy of one
era's file, before `hadd`-ing that copy against the other era's
untouched original:

```bash
# 1. Copy one era's file (never operate on the original)
cp DD_2022postEE/hhbbgg_analyzer-v2-histograms__<timestamp>.root \
   hhbbgg_analyzer-v2-histograms__2022postEE_nodata.root

# 2. Dry-run first -- confirm it finds exactly the known duplicate names
python delete_duplicate_data.py \
  --file hhbbgg_analyzer-v2-histograms__2022postEE_nodata.root \
  --exclude-prefix Data --dry-run

# 3. Delete for real
python delete_duplicate_data.py \
  --file hhbbgg_analyzer-v2-histograms__2022postEE_nodata.root \
  --exclude-prefix Data

# 4. hadd the untouched era against the deduplicated copy
hadd DD_2022_combined/hhbbgg_analyzer-v2-histograms.root \
  DD_2022preEE/hhbbgg_analyzer-v2-histograms__<timestamp>.root \
  hhbbgg_analyzer-v2-histograms__2022postEE_nodata.root
```

`delete_duplicate_data.py` uses `TDirectory::Delete("name;*")` directly
-- touches only the handful of objects being removed, not the
~148,000 total keys a real histogram file can contain, so it finishes
in seconds regardless of file size. Confirmed working end-to-end on
real 2022 and 2023 files -- deletion verified via re-opening the file
afterward and confirming the target names are genuinely gone, not just
assumed. Note: classic ROOT-format deletion marks keys removed without
reclaiming the underlying bytes -- the file's on-disk size will not
shrink. This is a storage cost only, not a correctness issue (`hadd`
navigates via the key table, not raw bytes).

**Verify after `hadd`**: confirm the combined file shows exactly the
expected number of `Data*` directories (5 for 2022, 12 for 2023),
matching the untouched era's own count -- not double, not zero.

#### 4.3.2 Combining trees

Tree output is split one file per `(sample, systematic)`, with **no
year or era in the filename at all** -- the same filename
(`hhbbgg_analyzer-v2-trees__<sample>__<systematic>.root`) is produced
independently by each era's analyzer run. This means the correct
handling is different, and actually simpler, than the histogram case:

- **Background/signal**: the same filename in both eras' directories
  represents genuinely different events -- concatenate via merge (see
  §4.0 Update 2 above for why this uses `uproot`, not `hadd`).
- **Data**: since each sample already lives in its own separate file
  (no in-file surgery needed), the fix is simply to take Data tree
  files from ONE designated era only, and skip the other era's copies
  entirely -- omission, not deletion.

**Tool: `combine_trees_across_eras.py`**, handling both cases in one
pass:
```bash
python combine_trees_across_eras.py \
  --era-a DD_2022preEE --era-b DD_2022postEE \
  --outdir DD_2022_combined_trees \
  --data-source-era a --dry-run   # always dry-run first
```
Drop `--dry-run` once the plan looks correct. Prints, for every
concatenated sample: `era-A entries + era-B entries` vs. the actual
written combined count, flagging `MATCH`/`MISMATCH` directly -- not a
separate manual check.

**Real finding from this process, worth checking for on any future
year's combination too**: comparing which sample+systematic files
exist in only ONE era (not both) surfaced `7` signal mass points for
2022 that were completely absent (every systematic AND nominal) from
one sub-era. Cross-referencing against direct `dasgoclient
dataset_access_type` checks split these into two genuinely different
categories:
- **5 confirmed PERMANENT upstream gaps** (dataset itself `INVALID` in
  DAS, nothing to recover): `X1000_Y700` (2022postEE), `X450_Y125`
  (2022postEE), `X700_Y550` (2022preEE), `X750_Y150` (2022preEE),
  `X850_Y250` (2022preEE, confirmed via this exact process).
- **2 confirmed RECOVERABLE gaps** -- the dataset itself is `VALID`
  with real files in DAS (`X350_Y200`: 12 files in `2022preEE`;
  `X700_Y95`: 11 files in `2022postEE`), yet absent from this
  pipeline's own processed tree output. This points to a gap in *our*
  processing (never submitted, or silently failed) rather than a
  physics/production limitation -- resubmission for both is the
  correct fix, not documenting them as permanent. **A name resolving
  in DAS is not the same as the dataset being valid and populated --
  worth checking `dataset_access_type` directly, not just whether a
  query returns a name, for any future gap investigation.**

**Also confirmed on 2023**: the same duplicate-Data pattern, and the
same `hadd` failure (see §4.0 Update 2) on at least one real file
(`GGJets_MGG-80_Rescaled`) -- resolved the same way, via
`uproot_hadd_replacement.py`.
---


## 5. Event Categorization

Derive score-based category boundaries from the merged analyzer output using
the α(score) sideband transfer method (per B2G-24-001), with an optional
orthogonal ttH-killer pre-split ("Option B": split events into
ttH-depleted / ttH-enriched branches first, then run the existing
AMS-optimized categorization independently within each branch).

The category-boundary search itself (`build_edges()`) implements the exact
6-step procedure: sort by score descending, define each new candidate SR from
the next `--nmin` highest-scoring *remaining* events, accept it only if
summed AMS² improves by >= `--min-gain` over the currently-accepted SRs alone
(not a fixed grand total), resetting `--nmin` after each acceptance and
doubling it on rejection. Identical in both scripts below.

**`--sigmoid-score` is RESOLVED: do not pass it.** Confirmed directly from
a Data/MC stack plot of `pDNN_score` -- the distribution spans exactly
[0.0, 1.0] with real physics structure at both edges, meaning
`inference_PDnn_updated.py`'s output is already a probability
(`predict_batched()` applies `torch.sigmoid()`/`torch.softmax()`
internally). Passing `--sigmoid-score` on top would apply sigmoid a
second time, compressing the whole distribution toward 0.5 and
destroying the separation power visible in that plot. Both commands
below have had the flag removed accordingly. Separately, `ttH_killer_score`
is also already a probability in [0, 1] (`inference_tth_killer.py` applies
`sigmoid()` internally, matching `tth_killer_v2.py`'s
`BCEWithLogitsLoss` training) — neither script here applies any
additional transform to it, which is correct as-is.

> **These two examples are early, historical reference only** --
> predate the `srbbgg`/tie-tolerance/catch-all-category fixes described
> below, and use a different `--max-bins`/`--min-gain`/`--outdir`
> convention than what the analysis actually settled on. **For the
> current, correct command, see "ttH Killer implementation (fixed)"
> further down this section** -- that is the one actually validated
> end-to-end (real, sensible category boundaries; real, non-zero yields
> in every category) and should be used as the template going forward,
> not either of the two below.

**Baseline (pDNN-only, no ttH-killer split) -- `event_categorization/build_pdnn_categories.py`:**

```bash
python event_categorization/build_pdnn_categories.py  \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha_3cats \
  --write-categorized
```

**With the ttH-killer pre-split -- `event_categorization/event_categorization_tth.py`**
(confirmed filename; the earlier "`categorize_with_tth_split.py`" naming
note below was a placeholder guess, now corrected), using the Tight
working point (ε(ttH)=0.10 → cut=0.401 from the trained model's
validation-set scan):

```bash
python event_categorization/build_pdnn_categories.py  \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_tth_split_tight \
  --write-categorized \
  --tth-cut 0.401
```

**Fixed in both scripts since the last pass through this document**
(both had independently-introduced copies of the same three bugs, since
neither reused a shared helper module -- each was audited and fixed
separately, then verified end to end against a fake file matching the
analyzer's real `sample/systematic/region` output structure):
- **`collect_dirs()` nested-path pollution**: non-recursive `fin.keys()`
  in this uproot version still returns every nested key, and every
  intermediate directory (e.g. `sample/nominal`) is itself a
  `ReadOnlyDirectory` -- so every systematic subdirectory was being
  treated as its own separate "sample." In the worst case this caused
  silent cross-systematic contamination, not just double-counting: a
  spurious `sample/PileupUp` entry has no `nominal` child to descend
  into, so the (now-fixed) systematic-descent logic fell back to reading
  *that* entry directly -- silently mixing PileupUp-systematic events
  into what was requested as `--systematic nominal`. Fixed identically in
  both scripts: top-level names derived via first-path-segment string
  parsing, deduplicated before any file access.
- **Stale `sample/region` tree-access assumption**: both scripts looked
  for the `selection` tree directly inside the sample directory. Since
  the analyzer now writes `sample/systematic/region`, this either found
  nothing (main scoring loop -- silent skip) or crashed outright
  (`--write-categorized`'s copy loop, calling `.arrays()` on what's now a
  subdirectory object). Fixed by adding `--systematic` (default
  `nominal`) to both scripts, descending into it before any tree lookup.
- **Loud diagnostics added**: both scripts now print
  `[INFO] systematic='...': used N/M sample directories (...)` so a wrong
  `--systematic` value, or a file from the older analyzer structure,
  fails visibly instead of silently producing empty or wrong results.
  Worth checking this line first after any run.

**Fixed later this session, in `categorize_events.py` specifically
(confirmed as a real, silent bug -- not caught by the fixes above,
since it doesn't crash or error at all):**
- **`TREE_NAME` was hardcoded to `"selection"`, not `"srbbgg"`** -- the
  analysis's actual, intended signal region. `"selection"` is a real,
  much looser upstream cut, not the signal region. This was NOT a typo
  caught immediately: since `"selection"` is a genuinely valid tree name
  that exists in every sample's output, the script ran without error,
  produced plausible-looking boundaries, and even wrote `cat`/`region`
  columns successfully -- the wrongness was entirely silent, only
  caught by directly comparing `selection`-region vs. `srbbgg`-region
  statistics for the same sample and noticing they were very different
  pools of events. **Every example in this section now uses `srbbgg`
  correctly** -- if working from an older copy of `categorize_events.py`
  or `build_pdnn_categories.py`, confirm `TREE_NAME = "srbbgg"` directly
  in the source before trusting any output.
- **Severe `pDNN_score` saturation at the top of the range, combined
  with a raw event-count-based `--nmin`, produced degenerate,
  non-informative category boundaries** -- confirmed directly:
  thousands of SR events sharing (or differing only in the last few
  representable `float32` digits from) the exact same score near 1.0,
  meaning a cutoff defined purely by event count landed arbitrarily
  inside that saturated cluster, producing boundaries like
  `[0.9999995, 0.9999996, 0.9999997, 0.9999998, 1.0]` that don't
  actually separate anything. **Fixed in `build_edges()`**: candidate
  bins now extend past any near-tie group (within a small tolerance,
  `tie_tol`, default `1e-4`, not exact float equality -- the real
  saturated cluster was distinct-but-adjacent `float32` values, not
  bit-identical ones) before accepting a boundary, so the entire
  saturated spike becomes one legitimate top category instead of being
  split arbitrarily. Confirmed working: the same real data that
  previously produced degenerate boundaries now produces genuinely
  distinct ones (e.g. `[0.921, 0.998, 0.99998]`) with the ORIGINAL,
  small `--nmin 50` -- no need to artificially inflate `--nmin` as a
  workaround once this fix is in place.
- **SR events scoring below the lowest derived boundary were silently
  left uncategorized (`cat=-99`) and excluded from the fit entirely**,
  not folded into any real category -- confirmed as a real loss of
  signal-region acceptance whenever `build_edges()` found fewer
  boundaries than `--max-bins` (common with sparser per-mass-point
  statistics). **Fixed**: added a catch-all lowest category (index
  `len(edges)`) that captures every SR event not already assigned to a
  boundary-defined category, so `--max-bins` fewer-than-requested
  boundaries genuinely still means "N usable categories, plus one
  catch-all," never "some real signal-region acceptance silently
  discarded."
- **`--write-categorized`'s copy loop could crash the entire run
  uncaught partway through**, losing every not-yet-processed sample's
  categorized output: `AttributeError: 'ReadOnlyDirectory' object has
  no attribute 'arrays'`, confirmed as a real, live crash. Root cause:
  `uproot`'s `.keys()` can surface nested-directory keys alongside leaf
  tree keys (the same underlying behavior the `collect_dirs()` fix
  above already handles elsewhere), and the copy-loop's fallback path
  (for any tree that isn't the main target) called `.arrays()`
  unconditionally without first confirming the key actually resolved to
  a tree rather than a directory. **Fixed**: an explicit
  `hasattr(tree, "arrays")` check before any `.arrays()` call, skipping
  with a loud `[WARN]` instead of crashing the whole run if a key
  doesn't resolve to a genuine tree.

**Outputs (from `--outdir`):**
- `event_categories.json` — derived category boundaries, nested per mass
  tag *and* per ttH branch (`tth_low` / `tth_high`) when `--tth-cut` is
  used (event_categorization_tth.py only); a single `"combined"` branch
  otherwise
- `<input>__categorized.root` — input file cloned with `cat`/`region`
  branches added, plus `tth_branch` (0=depleted, 1=enriched) when
  `--tth-cut` is used. Only the ONE requested `--systematic` is copied
  into this output (see the open item below on frozen-vs-per-systematic
  boundaries) -- other systematics present in the input are not carried
  into the categorized copy.

> **Open item (cut value) — RESOLVED, differently than this example
> shows.** The working point actually adopted for all downstream
> systematics/datacard work is **Medium (`--tth-killer-cut 0.682`,
> `--tth-cut` equivalent)**, not Tight (0.401) as shown in the example
> above — Medium roughly halves remaining ttH contamination relative to
> Loose for only a 3-point signal-efficiency cost, and matches the
> standard default-vs-specialized convention for this kind of pre-split.
> The Tight-WP example above predates that decision; kept here as a
> working syntax reference, not as the recommended cut value.

> **Open item (systematics — datacard wiring): now real, ongoing work,
> tracked in a separate, dedicated document
> (`Fitting_Commands_Systematics.md`), not just a future item.** Rate
> (weight-based) and shape (mgg + mjj object-level) systematics have
> both been computed and wired into a real signal workspace and datacard
> for one test mass point (`mX600_mY300`), verified end-to-end through a
> real `AsymptoticLimits` result and a real, sensible impact plot. See
> that document for the full procedure, the real bugs found while
> building it (including a category-boundary-computation bug and a
> `normalisation.py` branching-ratio bug, both described below in a
> new §6.5/§6.6), and what's still genuinely open (scaling to the full
> grid, per-category rate systematics, per-component shape shifts,
> per-component background). Category boundaries from `build_edges()`
> are still derived from nominal only per run, unresolved as stated
> below.



### ttH Killer implementation(fixed)
Table from the ttH script:


| WP     | cut   | ε(ttH) | ε(oth. H) |
|--------|-------|--------|-----------|
| Loose  | 0.924 | 0.500  | 0.997     |
| Medium | 0.682 | 0.200  | 0.978     |
| Tight  | 0.401 | 0.100  | 0.947     |


```bash
python event_categorization/build_pdnn_categories.py  \
  --root outputfiles/merged/DD_2024/ \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.05 --max-bins 5 \
  --alpha-bins 60 \
  --tth-killer-cut 0.682 \
  --per-mass \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha  \
  --write-categorized --systematic nominal
  ```

**`--root` now also accepts a directory (this session), not just a single
file** -- `resolve_input_files()` auto-detects the analyzer's per-sample
tree output (§4.0): pass the merged output directory directly
(`outputfiles/merged/DD_2024/`) and it globs for
`hhbbgg_analyzer-v2-trees__*.root`, processing all of them together
without needing to `hadd` first:
```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_2024/ \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.05 --max-bins 5 \
  --alpha-bins 60 \
  --tth-killer-cut 0.682 --per-mass \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha \
  --write-categorized --systematic nominal
```
Falls back to a single `hhbbgg_analyzer-v2-trees.root` in that directory
if no per-sample files are found there (e.g. after `hadd`), so both the
raw multi-file and the merged single-file layouts work unchanged. When
given a directory, `--write-categorized` produces one categorized output
PER INPUT FILE rather than one combined file -- both for consistency with
the analyzer's own per-sample split, and to avoid reintroducing the same
2GB write-cascade risk (§4.0) in the categorized copies themselves.

### 5.1 Signal MC event counts per category, per mass point (whole-grid cross-check)

Location: `event_categorization/summarize_signal_mc_counts.py`

Independent, read-only cross-check of what `build_pdnn_categories.py`
(above) actually put where -- reads the SAME `event_categories.json`
boundaries and the analyzer's own signal MC tree output, re-derives each
event's category via the identical `score_to_category()` convention used
throughout the fitting pipeline, and reports raw (MC statistics) and
weighted (physics yield) counts per category, flagging any category
below a configurable low-MC-statistics threshold (default 10 raw
events). Pure simulation, no data read at all -- no blinding concern.

**Extended this session for whole-grid use**: `--mass-x` now accepts
multiple values, or can be omitted entirely to auto-discover every mX
present in `--analyzer-root-base` -- the exact same auto-discovery
pattern `--mass-y` already used per mX. Confirmed via direct testing
(synthetic filenames, no ROOT dependency needed for the discovery logic
itself): mX values sort numerically, not alphabetically (`450 < 600 <
1000`, not the alphabetical `1000 < 450 < 600` a naive string sort would
give), and non-signal files (`GluGluHtoGG`, the merged background+data
file) are correctly never mistaken for a signal mass point.

```bash
# Whole grid, fully auto-discovered
python event_categorization/summarize_signal_mc_counts.py \
  --categories-json slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha/event_categories.json \
  --analyzer-root-base outputfiles/merged/DD_2024 \
  --out-csv outputfiles/yields/signal_mc_counts_full_grid.csv
```

**Confirmed working on the real grid**: auto-discovered 16 mX values
(`300, 320, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900,
950, 1000`), correctly sorted numerically. `mX=240` is correctly absent
-- consistent with, not contradicting, the confirmed zero-file
production gap already tracked in `Fitting_Commands_Systematics.md` for
that mass point; its absence here is expected, not a bug in this script.

Single-mass-point usage (original, unchanged) and an explicit-subset
usage are both still supported:
```bash
# One mass point only (original usage)
python event_categorization/summarize_signal_mc_counts.py \
  --categories-json .../event_categories.json \
  --analyzer-root-base outputfiles/merged/DD_2024 \
  --mass-x 600 \
  --out-csv summary_mX600.csv

# Explicit subset of mX values, mY still auto-discovered per point
python event_categorization/summarize_signal_mc_counts.py \
  --categories-json .../event_categories.json \
  --analyzer-root-base outputfiles/merged/DD_2024 \
  --mass-x 600 1000 \
  --out-csv summary_600_1000.csv
```

**Output CSV columns** (one row per mass-point/category pair):
`mass_x, mass_y, mass_tag, category, n_categories_total, raw_mc_events,
weighted_yield` -- `mass_x`/`mass_y` added as their own columns this
session (previously only encoded inside `mass_tag`) specifically so a
full-grid CSV can be filtered/pivoted by mass point directly, without
string-parsing `mass_tag`.

**Status: extended and unit-tested (discovery logic + full end-to-end
binning against synthetic ROOT trees, both verified against hand-computed
expected values), confirmed running successfully against the real,
full 16-mX production grid.** The `[SUMMARY]` low-MC-statistics flag
listing from that real run has not yet been reviewed here -- worth
pulling the tail of that output (total mass points processed, full
flagged-category list) before treating the grid as clean.

---

## 6. Fixes from the regions.py / binning.py / VH audit (this session)

Confirmed and fixed against the actual production framework (HiggsDNA
source, checked directly rather than assumed) before the next analyzer
re-run:

- **`regions.py`**: every region mask now explicitly requires
  `(dibjet_mass > 0) & (diphoton_mass > 0)` -- previously only
  `preselection` had this, and `-9999`-style reconstruction-failure
  sentinels were confirmed passing straight through `selection` and
  `srbbgg` into downstream analysis. Also: the
  `PNetRegPtRawRes > 0.2605` cuts (present in `srbbgg`, `srbbggMET`,
  `crantibbgg`, `sideband`) were confirmed as a genuine bug via HiggsDNA's
  own source (`PNetRegPtRawRes` is an mbb-regression input feature,
  never a cut variable anywhere in that framework) -- fixed per-region
  (deleted where redundant with an existing correct `PNetB` cut;
  restored a correct, previously-commented-out `PNetB` cut in
  `crbbantigg`, where it had been the *only* active requirement).
  Confirmed via a direct functional test with a synthetic
  `awkward.Array` that the original `srbbgg` mask produced **zero**
  surviving events on realistic data due to this bug, and the fixed
  version does not.
- **`binning.py`**: `dibjet_mass` widened from `[33, 0, 180]` to
  `[80, 0, 800]` (every region inherits this via `copy.deepcopy`, so one
  fix propagates everywhere) -- the M_Y grid spans 90-800 GeV, and the
  old range hid every high-mass signal point in the overflow bin. Also
  fixed: `DeltaPhi_j1MET`/`j2MET` (`[10,100,110]` -> `[20,0,3.14]`, not a
  valid angular range), `lepton1_mvaID` (`[100,0,100]` -> `[20,-1,1]`,
  matching this file's own photon-mvaID convention), `lepton1_pfIsoId`
  (`[100,0,100]` -> `[7,0,7]`, a discrete flag, not continuous).
- **`normalisation.py`**: VH cross-section lookup fixed for the 2024+
  `WmHtoGG`/`WpHtoGG`/`ZHtoGG` naming convention (previously only
  matched the 2022/2023-style combined `VHToGG` name, silently returning
  xsec=1.0 for the split-sample years).
- **`hhbbgg_Plotter.py`**: same VH naming gap, independently present a
  third time in `mc_patterns["VHToGG"]` -- fixed to combine all four
  naming variants into one stacked component, verified against 8 test
  cases including confirming no false-positive collision with
  `GluGluHToGG`/`VBFHToGG`/`ttHToGG`.

**Important**: none of these fixes are retroactive -- they only affect
runs *after* being deployed. The existing merged tree/histogram output
predates all four and should not be trusted for `dibjet_mass` shape,
`srbbgg`-region yields, or VH background until a fresh analyzer run has
picked these up.

### 6.5 A SEPARATE, later-found `normalisation.py` bug -- not the naming-match issue above

Distinct from the case-sensitivity/naming-match VH bug fixed earlier in
this section: `WmHtoGG`/`WpHtoGG`/`ZHtoGG`'s cross-section entries were
missing the `* BR_HToGG` (H→γγ branching ratio) multiplication that
every other H→γγ process in the same lookup table has -- inflating
these three samples' effective yield by `1/BR_HToGG`, roughly 440x.
Found via a real, physically implausible result: `ZHtoGG` showing as
44% of the total combined background, when its production cross-section
is ~20x smaller than `GluGluHtoGG`'s (which showed as 0.2%). Fixed:
```python
("wmhtogg",     0.647 * BR_HToGG),
("wphtogg",      1.021 * BR_HToGG),
("zhtogg",          0.9079 * BR_HToGG),
```
**Retroactive impact, same caution as above**: any histogram/tree output
predating this fix that includes these three samples is wrong and needs
regenerating -- for the full grid whenever it's next touched, not just
the one test point this was found on. Full detail, including the exact
symptom and how it was traced, in `Fitting_Commands_Systematics.md`.

### 6.6 Categorized (`--write-categorized`) output goes stale independently, on its OWN schedule

A fix to `normalisation.py` (§6.5) or any other change to a sample's
underlying tree data does **NOT** automatically update any existing
`--write-categorized` output (§5) built from the old data -- that
output is a genuinely separate, cloned copy of each sample's tree, with
`cat`/`region` columns added at the time `--write-categorized` was run,
and it has no mechanism to know its own inputs later changed.

**Confirmed as a real, live consequence**, not hypothetical: computing
a resonant-vs-non-resonant background composition from categorized
output produced `ZHtoGG` = 437.49 (should be ~1.77 post-§6.5-fix) --
the categorized copy simply predated the fix and was never regenerated,
silently serving ~250x-too-large values with no error or warning at
all. **Whenever tree data changes for any reason (a normalisation fix,
a fresh analyzer run, anything), `--write-categorized` needs re-running
before trusting anything computed from its output** -- worth checking
the categorized file's own timestamp against the tree files it reads
from, the same discipline `Fitting_Commands_Systematics.md` §6 already
recommends for `resbkg_fits`/`data_npz` against `event_categories.json`.

## 7. Running the analyzer as a Condor batch job

For long, unattended runs that survive closing your laptop or switching
machines -- see `README.md` / `run_analyzer.sh` / `submit_analyzer.sub`
(separate files, not reproduced here) for the full setup and debugging
history. Summary of what was needed, in case any of it recurs:

- **Dependencies**: the analyzer does local imports (`from config.utils
  import lVector`, `from regions import ...`, `from binning import
  binning`, `from normalisation import getXsec, getLumi`) resolved
  relative to the working directory at runtime -- `regions.py`,
  `binning.py`, `variables.py`, `normalisation.py`, and the whole
  `config/` package must all sit alongside the analyzer script wherever
  it's actually run from.
- **conda + `set -u`**: conda's own activation hooks (specifically
  `binutils_linux-64`'s, referencing `$ADDR2LINE`) are incompatible with
  bash's `set -u` -- fixed by pre-defining the variable before
  activation, not by toggling `-u` on the wrapper script (which alone
  was not sufficient, since the hook is `source`d and can independently
  affect global shell state).
- **AFS quota**: this analysis's real output size (~20GB+ trees) does
  not fit in a 10GB home-AFS quota -- must run from a location backed by
  larger storage (in this case, `Analysis/` resolves through a symlink
  to EOS, which comfortably holds it).
- **`--all-systematics` must be explicit in the submitted command, and
  is easy to silently omit** -- confirmed directly via
  `hhbbgg_analyzer_with_systematics.py --help`: without it, the analyzer
  defaults to nominal-only, meaning a completed, verified systematics
  scoring pass (step 3 above) would be entirely wasted for a Condor
  submission that forgot this one flag. Before submitting, confirm the
  actual `run_analyzer.sh` being used has it, not just this document.
- **Condor resource sizing**: `request_memory`/`+JobFlavour` should be
  bumped from a nominal-only run's `8GB`/`"tomorrow"` (1 day) once
  `--all-systematics` is added -- confirmed roughly an order-of-magnitude
  increase in data read/processed per sample (every JEC/JER/Scale/
  Smearing variation folder on top of nominal, all confirmed present on
  disk for e.g. `NMSSM_X350_Y100` under
  `/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/`).
  `16GB`/`"testmatch"` (3 days) is a reasonable, conservative starting
  point for the full-systematics run, not a precisely measured
  requirement -- if a real run comfortably finishes with room to spare,
  tune back down for future submissions; if it gets OOM-killed or hits
  the time limit, that's real evidence for the next value.
- **Real crash risk, from the analyzer's own `--help` text**: a
  systematic-variation file that was never actually scored (steps 3.1/
  3.2 above, `--all-systematics` on both) has no `pDNN_score` column and
  will crash the analyzer rather than being silently skipped. Confirm
  the completed scoring genuinely covers every systematic subfolder
  present on disk for every sample before submitting a long Condor run
  on the assumption it will finish cleanly.
- **The 2GB write-cascade crash (see §4.0) will also happen under Condor,
  not just interactively** -- the fixes in §4.0 (per-sample-and-systematic
  tree splitting, unique-per-run histogram filenames, resumability) apply
  identically whether the analyzer runs in a Condor job or an interactive
  shell. A Condor job that dies from this crash leaves genuinely usable
  partial output behind (every already-closed `(sample, systematic)` tree
  file is valid) -- resubmitting the same command will resume via the
  skip-check rather than starting over, so a crash mid-run is a delay,
  not a full restart.
- **Running the tail end interactively instead of via Condor** is
  reasonable once only a few samples remain (faster to monitor, no queue
  wait) but interactive lxplus nodes have much tighter CPU/time limits
  than Condor batch nodes AND no auto-restart on an SSH drop -- run
  inside `tmux`/`screen` even for a "quick" interactive finish, so a
  dropped connection doesn't lose progress:
  ```bash
  tmux new -s analyzer_resume
  # inside tmux: micromamba activate hhbbgg-awk, cd to the analyzer dir, run the command
  # Ctrl+b then d to detach; tmux attach -t analyzer_resume to reconnect
  ```

---

## Pipeline Summary

```
pDNN_v2.py / pDNN_v_WC.py     tth_killer_v2.py
        | (train)                    | (train)
        v                            v
inference_PDnn_updated.py  --->  inference_ttH_killer.py
 (pDNN_score; nominal by         (ttH_killer_score, same folder,
  default, X>=300/Y>=90,          in place by default)
  --recursive, optional
  --all-systematics)
        |                            |
        +-------------+--------------+
                       v
        hhbbgg_analyzer_with_systematics.py   (merge + DD background + weight-based
                       |                 systematics (automatic) + optional
                       |                 --all-systematics (folder-based);
                       |                 output: per-(sample,systematic) tree
                       |                 files + per-run histogram file, see
                       |                 §4.0 -- hadd to merge before downstream use)
                       v
              hhbbgg_Plotter.py          (Data/MC validation; systematic-
                       |                  aware via --systematic, DD-naming
                       |                  fixed; lumi_label/sample lists
                       |                  still hardcoded, deferred; expects
                       |                  the merged single histogram file)
                       v
        build_pdnn_categories.py /       (alpha(score) categorization, srbbgg
        event_categorization_tth.py /     region (was wrongly "selection"),
        categorize_events.py              tie-tolerant boundaries, catch-all
                                          category, crash-guarded copy loop;
                                          --systematic + collect_dirs bugs
                                          fixed in all three -> cat/region/
                                          tth_branch branches; --root now
                                          accepts the per-sample tree
                                          directory directly, no hadd needed;
                                          re-run whenever underlying tree
                                          data changes, see §6.6)
                       |
                       +---> summarize_signal_mc_counts.py  (independent,
                       |      read-only signal-MC raw/weighted count
                       |      cross-check per category per mass point --
                       |      whole-grid capable (see §5.1); optional,
                       |      not required for the pipeline to proceed)
                       v
        Fitting_Commands_Systematics.md   (datacard assembly WITH real rate +
        (separate document, finalfit_hhbbgg   shape systematics -- verified
        pipeline)                          end-to-end for one mass point via
                                           a real AsymptoticLimits result and
                                           a real, sensible impact plot; NOT
                                           yet scaled to the full grid)
```