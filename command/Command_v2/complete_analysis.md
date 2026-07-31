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
python inference_PDnn.py -i /path/to/your/folder
```

Run once per sample folder to attach the `pDNN_score` branch to each file.

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
> written by `inference_PDnn.py` is a raw logit. If it is already a
> probability in [0, 1], this flag would apply sigmoid twice and should
> be dropped. Verify the range of `pDNN_score` in the analyzer output
> before relying on results from this step. *(To be confirmed — see
> follow-up.)*

> **Open item (ttH killer):** `inference_tth_killer.py` already applies
> `sigmoid()` internally (matching how `tth_killer_v2.py` trains with
> `BCEWithLogitsLoss` and evaluates with `torch.sigmoid(...)`), so
> `ttH_killer_score` written to the tree is already a probability in
> [0, 1] — **do not** additionally sigmoid it downstream. This is
> independent of whatever is decided for `pDNN_score` above; the two
> scores may have different conventions and should be checked
> separately.

> **Open item (cut value):** `--tth-cut 0.401` above is the Tight working
> point from the ttH killer's validation-set scan
> (ε(ttH)=0.10, ε(other resonant H)=0.947). Before adopting it for the
> full categorization, compare the ttH-branch category structure across
> at least the Loose/Medium/Tight cuts (0.924 / 0.682 / 0.401) to confirm
> the split is worth keeping — see the validation plan discussed
> separately.

---

## Pipeline Summary

```
pDNN_v2.py / pDNN_v_WC.py     tth_killer_v2.py
        │ (train)                    │ (train)
        ▼                            ▼
inference_PDnn.py  ──────►  inference_tth_killer.py
   (pDNN_score)          (ttH_killer_score, same folder)
        │                            │
        └─────────────┬──────────────┘
                       ▼
        hhbbgg_analyzer_lxplus_par.py   (merge + DD background + template fit)
                       │
                       ▼
              hhbbgg_Plotter.py          (Data/MC validation)
                       │
                       ▼
        build_pdnn_categories.py        (α(score) categorization,
                                          optional ttH-killer pre-split
                                          → cat/region/tth_branch branches)
```