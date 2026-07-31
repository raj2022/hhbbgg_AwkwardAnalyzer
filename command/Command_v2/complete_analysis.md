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

---

## 3. Score Samples with the Trained pDNN

Inference is run separately per sample folder using `inference_PDnn.py`, located at:

`/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation`

```bash
python inference_PDnn.py -i /path/to/your/folder
```

Run once per sample folder to attach the `pDNN_score` branch to each file.

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
the α(score) sideband transfer method (per B2G-24-001).

```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha_3cats \
  --write-categorized --sigmoid-score
```

**Outputs:**
- `event_categories.json` — derived category boundaries per mass tag
- `hhbbgg_analyzer-v2-trees__categorized.root` — input file cloned with
  `cat`/`region` branches added (only written with `--write-categorized`)

> **Open item:** `--sigmoid-score` applies a sigmoid to `pDNN_score` before
> categorization. This is only correct if the score written by
> `inference_PDnn.py` is a raw logit. If it is already a probability in
> [0, 1], this flag would apply sigmoid twice and should be dropped.
> Verify the range of `pDNN_score` in the analyzer output before relying on
> results from this step. *(To be confirmed — see follow-up.)*

---

## Pipeline Summary

```
pDNN_v2.py / pDNN_v_WC.py   (train)
        │
        ▼
inference_PDnn.py            (score each sample folder)
        │
        ▼
hhbbgg_analyzer_lxplus_par.py (merge + DD background + template fit)
        │
        ▼
hhbbgg_Plotter.py             (Data/MC validation)
        │
        ▼
build_pdnn_categories.py      (α(score) categorization → cat/region branches)
```