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

Inspect Data/MC plots from the merged output using:

```bash
python hhbbgg_Plotter.py
```

> **Known issue, currently blocked.** `plot_stacks.py`'s `dir_to_base()`
> sample-grouping has the same `DDQCDGJET`/`DDQCCDGJets` naming mismatch
> already fixed in the analyzer's `is_dd_template()`, plus a hardcoded,
> manually-maintained `lumi_label()` and hardcoded signal/MC sample lists.
> Fixing these was blocked on the analyzer sample-collision/tree-cycle fix
> above landing first — now unblocked, not yet applied.

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
doubling it on rejection.

**Baseline (pDNN-only, no ttH-killer split):**

```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha_3cats \
  --write-categorized --sigmoid-score
```

**With the ttH-killer pre-split**, using the Tight working point
(ε(ttH)=0.10 → cut=0.401 from the trained model's validation-set scan):

```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_tth_split_tight \
  --write-categorized --sigmoid-score \
  --tth-cut 0.401
```

> **Naming note.** The `--tth-cut` / `--tth-branch` flags require the
> updated version of this script (`categorize_with_tth_split.py`). Either
> replace `build_pdnn_categories.py` with the updated version, keeping the
> same filename, or update the command above to point at the new
> filename — whichever keeps the rest of the pipeline's references
> consistent.

**Outputs:**
- `event_categories.json` — derived category boundaries, now nested per
  mass tag *and* per ttH branch (`tth_low` / `tth_high`) when `--tth-cut`
  is used; a single `"combined"` branch otherwise
- `hhbbgg_analyzer-v2-trees__categorized.root` — input file cloned with
  `cat`/`region` branches added, plus `tth_branch` (0=depleted,
  1=enriched) when `--tth-cut` is used

> **Open item (pDNN):** `--sigmoid-score` applies a sigmoid to
> `pDNN_score` before categorization. This is only correct if the score
> written by `inference_PDnn_updated.py` is a raw logit. If it is already
> a probability in [0, 1] (as `predict_batched()` in that script already
> applies `torch.sigmoid()`/`torch.softmax()` internally, suggesting it
> is), this flag would apply sigmoid twice and should be dropped. Verify
> the range of `pDNN_score` in the analyzer output before relying on
> results from this step. *(To be confirmed -- see follow-up.)*

> **Open item (ttH killer):** `inference_tth_killer.py` already applies
> `sigmoid()` internally (matching how `tth_killer_v2.py` trains with
> `BCEWithLogitsLoss` and evaluates with `torch.sigmoid(...)`), so
> `ttH_killer_score` written to the tree is already a probability in
> [0, 1] -- **do not** additionally sigmoid it downstream. This is
> independent of whatever is decided for `pDNN_score` above; the two
> scores may have different conventions and should be checked
> separately.

> **Open item (cut value):** `--tth-cut 0.401` above is the Tight working
> point from the ttH killer's validation-set scan
> (ε(ttH)=0.10, ε(other resonant H)=0.947). Before adopting it for the
> full categorization, compare the ttH-branch category structure across
> at least the Loose/Medium/Tight cuts (0.924 / 0.682 / 0.401) to confirm
> the split is worth keeping -- see the validation plan discussed
> separately.

> **Open item (systematics — datacard wiring):** the analyzer now produces
> both weight-based and (optionally) folder-based systematic shapes with a
> proper `sample/systematic/region` output structure. Nothing yet
> assembles those into a `combine`-style datacard (shape systematics via
> up/down histogram naming, rate systematics as `lnN` lines) — tracked
> separately, not part of this document's scope yet. Category boundaries
> from `build_edges()` are derived from nominal only; whether the same
> boundaries are reused for every systematic variation or re-derived per
> variation has not yet been decided.

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
              hhbbgg_Plotter.py          (Data/MC validation -- fixes pending,
                       |                  blocked-then-unblocked, not yet applied)
                       v
        build_pdnn_categories.py /       (alpha(score) categorization,
        categorize_with_tth_split.py      optional ttH-killer pre-split
                                          -> cat/region/tth_branch branches)
                       |
                       v
              [not yet built]             (datacard assembly with systematics
                                           -- tracked separately)
```