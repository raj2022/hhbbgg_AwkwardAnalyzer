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

### 3.1 Score with the Trained pDNN

Location: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation`

```bash
python inference_PDnn_updated.py \
  -i /eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7/2022postEE/merged/ \
  --recursive
```
eg for the 2024 pDNN score at `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation`:
```bash
 python inference_PDnn_updated.py -i /eos/user/b/bartek/hhbbgg/higgsdna_v7/2024/merged/ --recursive     ````
python

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
- **By default, only the `nominal` subfolder is scored**, plus any flat
  file with no systematic-folder structure at all. Systematic variations
  (`jec_syst_Total_up`, `Smearing_down`, `ScaleEB_Zee_up`, ...) are
  skipped and listed in the log output. Add `--all-systematics` once
  those are needed for the fit *(not yet decided)*.
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

```bash
python inference_tth_killer.py -i /path/to/your/folder \
  --model best_tth_killer.pt \
  --scaler scaler_tth.pkl
```

Run once per sample folder — **the same folders scored in step 3.1** — to
attach the `ttH_killer_score` branch alongside the existing `pDNN_score`
branch in each file. Both branches must be present before step 5, since
the categorization script's ttH-killer pre-split (`--tth-cut`) reads
`ttH_killer_score` directly from the tree.

> **New step.** Previously the ttH killer was trained (step 2) but never
> actually scored onto samples, so `ttH_killer_score` never reached the
> analyzer output. This step closes that gap.

---

## 4. Run the Analyzer

The analyzer performs full sample processing, including data-driven (DD)
background estimation and template fitting.

```bash
python hhbbgg_analyzer_lxplus_par.py \
  --year 2023 --era All \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/scored/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/scored/ \
  --tag DD_CombinedAll
```

- Each `-i` directory is searched **recursively**, handling both the flat
  background/data layout and the nested `<mass_point>/<systematic>/*.parquet`
  signal layout in the same pass.
- **By default, only `nominal` is processed** (plus flat files with no
  systematic-folder structure), matching step 3.1's scoring scope exactly
  — a systematic-variation file that was never scored would otherwise
  crash on the missing `pDNN_score` column. Add `--all-systematics` only
  once step 3.1 has also been rerun with that flag.

**Output:** `outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root`

### 4.1 Validate Data/MC Agreement

Inspect Data/MC plots from the merged output using:

```bash
python hhbbgg_Plotter.py
```

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
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
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
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
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

> **Open item (systematics):** everything above runs on `nominal` only.
> Turning on `--all-systematics` in steps 3.1/3.2/4 makes `pDNN_score` /
> `ttH_killer_score` available in the variation trees, but does not by
> itself wire those into the fit as shape uncertainties, nor revisit
> whether the nominal-derived category boundaries and mass-sculpting
> validation still hold under each variation. Treat as a separate,
> deliberate step once the nominal-only chain is fully validated.

---

## Pipeline Summary

```
pDNN_v2.py / pDNN_v_WC.py     tth_killer_v2.py
        | (train)                    | (train)
        v                            v
inference_PDnn_updated.py  --->  inference_tth_killer.py
 (pDNN_score; nominal-only,     (ttH_killer_score, same folder)
  X>=300/Y>=90, --recursive)
        |                            |
        +-------------+--------------+
                       v
        hhbbgg_analyzer_lxplus_par.py   (merge + DD background + template fit;
                       |                 recursive, nominal-only by default)
                       v
              hhbbgg_Plotter.py          (Data/MC validation)
                       |
                       v
        build_pdnn_categories.py /       (alpha(score) categorization,
        categorize_with_tth_split.py      optional ttH-killer pre-split
                                          -> cat/region/tth_branch branches)
```