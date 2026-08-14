# Complete Analysis Pipeline: Commands Reference

This document records the full command sequence for the X→YH→bbγγ resonant
search analysis, from pDNN training through event categorization.

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

---

## 4. Run the Analyzer

The analyzer performs full sample processing, including data-driven (DD)
background estimation, weight-based systematic histogram filling, and
template fitting.

**Nominal only (default):**
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-years 2024 --era All \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/data/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/sim/scored/ \
  --tag DD_2024
```

**With all systematics** (requires 3.1 and 3.2 above to have also been run
with `--all-systematics`, so the variation-folder files actually carry
real `pDNN_score`/`ttH_killer_score` values):
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-years 2024 --era All \
  -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/data/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_parquet/Run3_2024/sim/scored/ \
  --tag DD_2024_AllSyst \
  --all-systematics
```

(2022–2023 example, same flags: replace `-i` with the per-era
`preEE/postEE/preBPix/postBPix` `scored/` directories and
`--config-years 2022,2023`.)

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

**Output:** `outputfiles/merged/<tag>/hhbbgg_analyzer-v2-trees.root` and
`-histograms.root`.

### 4.1 Validate Data/MC Agreement

Inspect Data/MC plots from the merged output using `hhbbgg_Plotter.py`:

**Nominal (default):**
```bash
python hhbbgg_Plotter.py \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-histograms.root
```

**A specific systematic** (e.g. to inspect a weight-based variation's
shape, or a folder-based one if `--all-systematics` was used upstream):
```bash
python hhbbgg_Plotter.py \
  --root outputfiles/merged/DD_2024_AllSyst/hhbbgg_analyzer-v2-histograms.root \
  --systematic PileupUp
```

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

**Baseline (pDNN-only, no ttH-killer split) -- `event_categorization/build_pdnn_categories.py`:**

```bash
python event_categorization/build_pdnn_categories.py \
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
python event_categorization/event_categorization_tth.py \
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

> **Open item (cut value):** `--tth-cut 0.401` above is the Tight working
> point from the ttH killer's validation-set scan
> (ε(ttH)=0.10, ε(other resonant H)=0.947). Before adopting it for the
> full categorization, compare the ttH-branch category structure across
> at least the Loose/Medium/Tight cuts (0.924 / 0.682 / 0.401) to confirm
> the split is worth keeping -- see the validation plan discussed
> separately.

> **Open item (systematics — datacard wiring):** the analyzer now produces
> both weight-based and (optionally) folder-based systematic shapes with a
> proper `sample/systematic/region` output structure, and both
> categorization scripts can now correctly read any single systematic via
> `--systematic`. Nothing yet assembles these into a `combine`-style
> datacard (shape systematics via up/down histogram naming, rate
> systematics as `lnN` lines) — tracked separately, not part of this
> document's scope yet. Category boundaries from `build_edges()` are
> still derived from nominal only per run; whether the same boundaries
> are reused for every systematic variation or re-derived per variation
> (running the categorization script once per systematic) has not yet
> been decided.



### ttH Killer implementation(fixed)
Table from the ttH script:


| WP     | cut   | ε(ttH) | ε(oth. H) |
|--------|-------|--------|-----------|
| Loose  | 0.924 | 0.500  | 0.997     |
| Medium | 0.682 | 0.200  | 0.978     |
| Tight  | 0.401 | 0.100  | 0.947     |


```bash
python categorize_events.py \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.05 --max-bins 5 \
  --alpha-bins 60 \
  --tth-killer-cut 0.682 \
  --per-mass \
  --outdir outputs/categories_tth_medium \
  --write-categorized --systematic nominal
  ```

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
        hhbbgg_analyzer_lxplus_par.py   (merge + DD background + weight-based
                       |                 systematics (automatic) + optional
                       |                 --all-systematics (folder-based);
                       |                 output: sample/systematic/region)
                       v
              hhbbgg_Plotter.py          (Data/MC validation; systematic-
                       |                  aware via --systematic, DD-naming
                       |                  fixed; lumi_label/sample lists
                       |                  still hardcoded, deferred)
                       v
        build_pdnn_categories.py /       (alpha(score) categorization,
        event_categorization_tth.py       optional ttH-killer pre-split;
                                          --systematic + collect_dirs bugs
                                          fixed in both -> cat/region/
                                          tth_branch branches)
                       |
                       v
              [not yet built]             (datacard assembly with systematics
                                           -- tracked separately)
```