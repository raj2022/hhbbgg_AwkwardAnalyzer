<!-- # hhbbgg AwkwardAnalyzer

Analysis framework for the X→YH→bbγγ resonant search, using
[awkward-array](https://awkward-array.org/)-based processing of
skimmed/NanoAOD-derived samples. Covers pDNN and ttH-killer network
scoring, event processing (histograms + trees, with a full systematic
dimension), Data/MC validation, and score-based event categorization.

For the complete, up-to-date command sequence with explanations of every
flag, see **`Analysis_Commands.md`** in this repository — that document is
the maintained source of truth for the pipeline and is kept in sync with
the scripts as they change. This README gives an overview and quick
reference; anything here that conflicts with `Analysis_Commands.md` should
be resolved in favor of the latter.

---

## Installation

```bash
git clone https://github.com/raj2022/hhbbgg_AwkwardAnalyzer.git
cd hhbbgg_AwkwardAnalyzer
```

Three environment managers are referenced across this project's history
(`conda`, `mamba`, `micromamba`) — **pick one and confirm the environment
file it reads actually exists and is current** (`requirement.yaml` and
`environment.yml` have both been referenced; verify which is real before
relying on either):

```bash
# conda / mamba (faster)
mamba env create -f requirement.yaml
conda activate hhbbgg-awk

# micromamba (lightweight alternative)
curl -Ls https://micro.mamba.pm/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
micromamba create -f environment.yml
micromamba activate hhbbgg-awk
```

**Dependencies:** `matplotlib`, `uproot`, `hist`, `numpy`, `mplhep`,
`vector`, `root`, `awkward`, `pandas`, `pyarrow`.

---

## Pipeline Overview

```
pDNN training  →  ttH-killer training  →  score samples (both networks)
     →  run the analyzer  →  validate Data/MC  →  event categorization
     →  [datacard + fit — not yet built, tracked separately]
```

Full commands, flags, and the reasoning behind each design decision are
in `Analysis_Commands.md`. Summary below.

### 1–2. Train the networks
```bash
python pDNN_v2.py          # parameterized DNN (with correlation pruning)
python tth_killer_v2.py    # ttH-killer network
```

### 3. Score samples
Both networks are applied to the same sample folders, one after the
other. By default only the `nominal` subfolder is scored (systematic
variations are opt-in via `--all-systematics`, and must be requested
consistently across every stage below if used):
```bash
python inference_PDnn_updated.py -i <merged_sample_dir> --recursive
python inference_ttH_killer.py -i <merged_sample_dir>/scored/ --recursive \
  --model best_tth_killer.pt --scaler scaler_tth.pkl
```

### 4. Run the analyzer
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-years <year(s)> --era <era> \
  -i <scored_signal_dir> -i <scored_data_dir> -i <scored_background_dir> \
  --tag <run_tag>
```

> **Flag-name warning.** Different copies of this script in active use
> have used `--year`, `--config-year` (singular), and `--config-years`
> (plural) — all three appear across this repository's own history,
> including within this README. **Confirm which flag the copy you are
> actually running accepts** (`python hhbbgg_analyzer_lxplus_par.py --help`)
> before trusting any example command, here or elsewhere. This has caused
> real failed runs; it is not a cosmetic inconsistency.

Output: `outputfiles/merged/<tag>/hhbbgg_analyzer-v2-trees.root` and
`-histograms.root`. Histogram/tree paths inside these files are structured
`sample/systematic/region[/variable]`, with `nominal` as an explicit value.

### 5. Validate Data/MC agreement
```bash
python hhbbgg_Plotter.py --root outputfiles/merged/<tag>/hhbbgg_analyzer-v2-histograms.root
```

### 6. Event categorization
```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/<tag>/hhbbgg_analyzer-v2-trees.root \
  --outdir <outdir> --write-categorized --per-mass
```
An optional ttH-killer pre-split variant exists at
`event_categorization/event_categorization_tth.py` (adds `--tth-cut`).

---

## Output Storage Conventions

Analyzer output is written to `outputfiles/merged/<tag>/`. Some existing
per-year/combined outputs on `/afs`:

| Tag | Path |
|---|---|
| 2022 (All) | `outputfiles/merged/2022_All/hhbbgg_analyzer-v2-histograms.root` |
| 2023 (All) | `outputfiles/merged/2023_All/hhbbgg_analyzer-v2-histograms.root` |
| 2024 (All) | `outputfiles/2024_All/` |

**Verify these paths still exist and still correspond to output produced
by the current version of the analyzer before relying on them** —
significant fixes have landed in the analyzer since any of these may have
last been produced (sample-name resolution, tree-cycle handling, the
systematic dimension); older files at these paths may predate those fixes
and should not be treated as current.

---

## Adding Variables / Regions

- New variables: `binning.py`, `variables.py`, and
  `hhbbgg_analyzer_lxplus_par.py` (where the variable is computed/read).
- ParticleNet-regressed mass additions: also touch `regions.py`.
- New sample/file names: add to `normalisation.py` (cross-section/lumi
  lookup) and to the plotting script's sample-grouping logic.

---

## Known Open Items

- **`--year` / `--config-year` / `--config-years` flag-name
  inconsistency** across different deployed copies of the analyzer —
  needs a single confirmed answer, not per-command guessing.
- **VH background** (`WmHToGG`/`WpHToGG`/`ZHToGG`) not currently combined
  in the Plotter's sample grouping — tracked separately.
- **Datacard/fit stage** does not exist yet in this repository as
  reviewed; the pipeline currently ends at event categorization.
- See `Analysis_Commands.md`'s "Open item" callouts for the complete,
  current list (working-point validation, systematics-in-datacard
  wiring, category-boundary freeze-vs-per-systematic decision).

---

## Legacy / Unverified

The following are referenced in this repository's history but were **not
part of the verification and fixes described in `Analysis_Commands.md`**.
Treat any command below as unconfirmed until independently checked —
listed here for completeness, not as a recommendation to use as-is:

- `hhbbgg_Analyzer.py` — original `.root`-input analyzer
  (`python hhbbgg_Analyzer.py -i <dir_or_file>`)
- `hhbbgg_Analyzer_parquet.py` — original `.parquet`-input analyzer,
  distinct from `hhbbgg_analyzer_lxplus_par.py`
  (`python hhbbgg_Analyzer_parquet.py -i <dir>`)
- `make_templates.py` — referenced for systematics template production
  (`python make_templates.py --year <year> <sample_dir>`); not reviewed,
  not confirmed to still exist or function
- The historical "segfault fix" note pointing at
  `hhbbgg_analyzer_lxplus_par.py -i ~/public/samples/VBFHToGG.parquet` —
  predates the `-i`/`--recursive`/`--config-years` interface described
  above; the single-file invocation style may no longer match the current
  argument parser -->





# hhbbgg_AwkwardAnalyzer

Awkward-array analysis framework for the CMS Run 3 search for a resonance X decaying to YH, with H → γγ and Y → bb (X → YH → bbγγ; B2G-25-010, AN-25-133).

The framework takes skimmed, NanoAOD-derived samples (produced with HiggsDNA) through neural-network scoring, event selection, histogramming, Data/MC validation and score-based event categorization. Data periods covered: 2022 (pre/postEE), 2023 (pre/postBPix), 2024 and 2025.

> **Branch:** `2026_working`. A datacard and fit stage is not part of this repository.
> **Coming back after a break?** Read [Quick start](#quick-start), then [Status log](#status-log).

---

## Contents

1. [Quick start](#quick-start)
2. [Pipeline at a glance](#pipeline-at-a-glance)
3. [Installation and environment](#installation-and-environment)
4. [Workflow, step by step](#workflow-step-by-step)
5. [Merging the analyzer output](#merging-the-analyzer-output)
6. [Inputs, outputs and paths](#inputs-outputs-and-paths)
7. [Conventions](#conventions)
8. [Checks to run before trusting an output](#checks-to-run-before-trusting-an-output)
9. [Troubleshooting](#troubleshooting)
10. [Glossary](#glossary)
11. [Status log](#status-log)
12. [Known limitations](#known-limitations)
13. [Contact](#contact)

---

## Quick start

```bash
# 1. environment (interactive lxplus)
micromamba activate hhbbgg-awk
python3 -c "import awkward, uproot, hist, torch; print('OK')"

# 2. go to the repository
cd <path-to>/hhbbgg_AwkwardAnalyzer && git status && git log --oneline -5

# 3. see which jobs are running or finished
condor_q
condor_history -limit 10

# 4. check the latest merged output is healthy
python3 check_merge.py --base <merged-output-dir> --dup-check
```

The authoritative command sequence is `Analysis_Commands.md`. This README explains the structure and the pitfalls; it does not replace that file.

---

## Pipeline at a glance

```text
 HiggsDNA parquet (signal MC, background MC, data)
            │
            ▼
 [1] Train ─ pDNN_v2.py, tth_killer_v2.py ──► model files
            │
            ▼
 [2] Score ─ inference_PDnn_updated.py, inference_ttH_killer.py ──► scored parquet
            │
            ▼
 [3] Analyze ─ hhbbgg_analyzer_lxplus_par.py ──► per-period trees + histograms
            │
            ▼
 [4] Merge ─ era combination, bkg/data merge ──► DD_<period>, DD_<year>_trees
            │
       ┌────┴─────────────┐
       ▼                  ▼
 [5] Validate        [6] Categorize
 hhbbgg_Plotter.py   build_pdnn_categories.py ──► event_categories.json
                          │
                          ▼
                 (fit stage: separate repository)
```

| Stage | Purpose | Entry point | Needs | Produces |
|---|---|---|---|---|
| 1. Train | pDNN and ttH-killer classifiers | `pDNN_v2.py`, `tth_killer_v2.py` | scored-ready parquet | model files |
| 2. Score | evaluate both networks on every sample | `inference_PDnn_updated.py`, `inference_ttH_killer.py` | parquet, models | parquet with scores |
| 3. Analyze | selection, trees, histograms, systematics | `hhbbgg_analyzer_lxplus_par.py` | scored parquet | ROOT trees and histograms |
| 4. Merge | combine eras, merge background and data | see [Merging](#merging-the-analyzer-output) | analyzer output | `DD_*` folders |
| 5. Validate | Data/MC agreement | `hhbbgg_Plotter.py` | merged histograms | plots |
| 6. Categorize | score-based categories per mass point | `event_categorization/build_pdnn_categories.py` | merged trees | `event_categories.json` |

---

## Installation and environment

```bash
git clone https://github.com/raj2022/hhbbgg_AwkwardAnalyzer.git
cd hhbbgg_AwkwardAnalyzer
git checkout 2026_working
micromamba env create -f <environment-file>.yml     # first time only
micromamba activate hhbbgg-awk
```

<!-- TO FIX BEFORE PUBLISHING: the current README refers to both `requirement.yaml`
     and `environment.yml`. Keep one, delete the other, and put its real name above. -->

Use `micromamba`, not `conda`: `conda activate` can leave no environment active without printing an error. Always verify with the import test in the Quick start.

### Activation inside HTCondor jobs

Batch jobs have no interactive shell setup. Use exactly this sequence in the job wrapper:

```bash
export MAMBA_EXE='/eos/user/s/sraj/software/bin/micromamba'
export MAMBA_ROOT_PREFIX='/eos/user/s/sraj/software/micromamba'
eval "$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX")"
micromamba activate hhbbgg-awk
```

Both details matter: `MAMBA_ROOT_PREFIX` must end in `/micromamba`, and `--root-prefix` must be passed to the shell hook. If either is missing the job fails with `Cannot activate, prefix does not exist at: '.../envs/hhbbgg-awk'`, and the path in that message is not the one that is actually wrong.

### Terminal fix

If `clear` or ncurses programs fail with terminfo errors, add `export TERMINFO=/usr/share/terminfo` to `~/.bashrc`.

---

## Workflow, step by step

Run `python3 <script> --help` for the options of any script. Option names have differed between script versions (for example `--year`, `--config-year`, `--config-years`), so do not copy flags from old logs without checking.

### 1. Train the networks

```bash
python3 pDNN_v2.py        <options>
python3 tth_killer_v2.py  <options>
```

- pDNN: parameterised in (mX, mY); balanced signal and background per mass group.
- ttH-killer: separate classifier to suppress ttH. Working points are Loose, Medium and Tight. Fill in the cut values for the current training here: `<Loose / Medium / Tight>`.
- Retrain whenever the b-tag treatment, the input variables or the data periods change.

### 2. Score the samples

```bash
python3 inference_PDnn_updated.py  <options>
python3 inference_ttH_killer.py    <options>
```

- Only the `nominal` systematic is scored by default.
- `--min-y` sets the lowest mY scored. A lower value (for example 70) is needed for the extended mY range. If scores were produced with an older value, the downstream categories silently collapse to one or two bins.

### 3. Run the analyzer

```bash
python3 hhbbgg_analyzer_lxplus_par.py  <options>
```

Output goes under `outputfiles/merged/<tag>/` or, for the current runs, `run_All/merged/`. 2022 and 2023 are processed per era; 2024 and 2025 are not split by era. Jobs are normally submitted through HTCondor.

### 4. Merge

See [Merging the analyzer output](#merging-the-analyzer-output).

### 5. Validate Data/MC agreement

```bash
python3 hhbbgg_Plotter.py  <options>
```

### 6. Categorize events

```bash
python3 event_categorization/build_pdnn_categories.py \
    --root <era-combined trees directory> \
    --sr-sigma 2.0 --cr-sidebands 4 10 --nmin 50 --min-gain 0.05 --max-bins 5 \
    --alpha-bins 60 --tth-killer-cut 0.682 --per-mass \
    --boundary-bkg-source mc --add-catchall-bin --write-categorized \
    --systematic nominal
```

- The script processes every mass point present under `--root`. It has no mY range option; that range is fixed at the scoring step.
- Use `--boundary-bkg-source mc`. The default (`data`) searches category boundaries with a very small control-region data sample and, for most of the mass grid, returns one degenerate boundary pinned at the minimum score of that sample.
- Keep `--min-gain 0.05`. Lower values give the sparse corners more categories but push the whole grid toward the maximum number of bins.
- `--tth-killer-cut 0.682` is the Medium working point of the previous training. Update it after retraining.
- Output: `event_categories.json`, with mass tags under the `"boundaries"` key. The number of categories for a mass tag is `len(edges)`; the last edge is the lower bound of the top category, not a cap.

---

## Merging the analyzer output

After the analyzer jobs finish, the per-era outputs are combined:

1. **Era combination (2022 and 2023 only).** `DD_2022preEE` + `DD_2022postEE` → `DD_2022_trees`; `DD_2023preBPix` + `DD_2023postBPix` → `DD_2023_trees`. 2024 and 2025 are used directly from `DD_2024/` and `DD_2025/`.
2. **Histograms.** One merged histogram file per year in `DD_<year>/`. If several timestamped files are present, record which one is current.
3. **Background and data only.** `merge_bkg_data_files.py` produces the `bkg_data_only` files used as `--root` by the fitting scripts.
4. **Submission.** The tree merge is submitted with `condor_submit submit_tree_merge.sub` (directory `output_processing/`). Follow it with `condor_q <cluster>` and, afterwards, `condor_history <cluster>`.
5. **Verification.** Always run `check_merge.py` on the result (see below).

---

## Inputs, outputs and paths

All paths on CERN EOS/AFS. `<base>` = `/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/run_All/merged`.

| Item | Location |
|---|---|
| Per-era analyzer output | `<base>/DD_2022preEE`, `DD_2022postEE`, `DD_2023preBPix`, `DD_2023postBPix` |
| Per-year output (no era split) | `<base>/DD_2024`, `<base>/DD_2025` |
| Era-combined trees | `<base>/DD_2022_trees`, `<base>/DD_2023_trees` |
| Merged histograms | `<base>/DD_<year>/hhbbgg_analyzer-v2-histograms*.root` |
| Signal MC parquet | `/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/HiggsDNA_v7_dask_merged/<year>/sim/<era>/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet` |
| Background MC and data parquet | `/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/output_parquet/Run3_<year>/{data,sim}/` |
| Analyzer trees, AFS copy | `/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/merged` |

ROOT file structure: `<sample>/<systematic>/<tree>`. Systematics available: `nominal`, `ScaleEB_Zee`, `ScaleEB_Zmmg`, `ScaleEE_Zee`, `ScaleEE_Zmmg` (each `_up/_down`), `Smearing_up/down`, `jec_syst_Total_up/down`, `jer_syst_up/down`.

Older folders (`outputfiles/DD_2022_combined_trees`, `outputfiles/merged/DD_<year>`) predate the extended mY range and the rescoring. Do not use them for new work.

---

## Conventions

- **Luminosity (fb⁻¹):** 2022 = 34.65, 2023 = 27.64, 2024 = 109.82, 2025 = 111.19; total 283.30. The per-era values live in `normalisation.py`; keep every script consistent with it.
- **Luminosity weight:** applied once, in the per-event weight. Do not apply it a second time downstream.
- **Cross sections:** matched by lower-cased sample name with `_` and `-` removed, so dictionary keys must be written without underscores, hyphens or capitals.
- **Variable name:** the reconstructed mass variable M̃_X is `Res_M_X` in the ntuples only.
- **Blinding:** the analysis is blinded. Do not look at data in the signal region.

---

## Checks to run before trusting an output

| Check | How |
|---|---|
| No broken files | `check_merge.py` reports zero-size or unreadable ROOT files |
| Era combination is lossless | combined entries = preEE + postEE (same for 2023), per sample/systematic/tree |
| No duplicated data events | `check_merge.py --dup-check` (run, lumi, event) |
| Same statistics as the previous run | `check_merge.py --ref <old merged dir>`; investigate any ratio that is not 1 |
| Categories are not degenerate | no mass tag with a single edge pinned at the minimum score; every tag keeps the `0.0` catch-all edge |
| Scores cover the full mY range | lowest mY present in each mX equals the intended `--min-y` |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Cannot activate, prefix does not exist at '.../home-s/...'` in a Condor job | wrong `MAMBA_ROOT_PREFIX` or missing `--root-prefix` | use the exact activation block above |
| `conda activate` does nothing | conda cannot see the env | use `micromamba activate` |
| Random `Errno 5` or `Errno 71` on EOS | transient EOS failure | rerun the failed job; the analyzer has retry wrappers |
| Most mass points have one degenerate category | scores made with an old `--min-y`, or boundary search on sparse data | rescore, and use `--boundary-bkg-source mc` |
| Cross section reads 1.0 for a sample | key in the cross-section table never matches the normalised sample name | rewrite the key without `_`, `-`, spaces or capitals |
| `getLumi` returns 1.0 or raises | unknown year or era string | use `2022`–`2025` and valid era names |
| Merged job exits 0 but the file is short | interrupted write | `check_merge.py`; resubmit that period |
| Pasted multi-line heredoc is cut off in the terminal | terminal truncation | deliver long files as base64: `echo "<b64>" | base64 -d > file` |

---

## Glossary

| Term | Meaning |
|---|---|
| X, Y, H | resonance, its lighter partner, and the 125 GeV Higgs boson |
| (mX, mY) | mass point of the signal hypothesis |
| pDNN | parameterised neural network taking (mX, mY) as inputs |
| ttH-killer | classifier trained to reject ttH background |
| SR / CR | signal region / control (sideband) region |
| mγγ, mjj | diphoton and dijet invariant masses |
| M̃_X | reduced X mass built from the dijet-diphoton system |
| DD | data-driven background sample |
| era | data-taking sub-period (2022 pre/postEE, 2023 pre/postBPix) |
| WP | working point (Loose, Medium, Tight) |

---

## Status log

Add a dated line after each significant step. Newest first.

| Date | State |
|---|---|
| 2026-10-25 | Analyzer rerun finished. Tree merge submitted (`submit_tree_merge.sub`, cluster 9595160, 2 jobs). Next: run `check_merge.py` on the result. |
| open | Background MC statistics are exactly half of the earlier run (2022, every background sample). The era merge is not the cause. Cause not yet found. |
| open | pDNN and ttH-killer retraining on 2022–2025 after the Medium b-tag requirement. |
| open | `pDNN_v_WC.py` still rescales 2025 to 110.37 fb⁻¹; should be 111.19 (or import `normalisation.py`). |

---

## Known limitations

- **Output freshness.** Outputs previously listed for 2022, 2023 and 2024 predate recent analyzer fixes. Regenerate them before use.
- **Legacy scripts.** `hhbbgg_Analyzer.py`, `hhbbgg_Analyzer_parquet.py` and `make_templates.py` are kept for reference only and have not been validated with the current workflow.
- **Fit stage.** No datacard or fit code is included.

---

## Contact

Maintainer: Shivam Raj (CMS, B2G HH→bbγγ group). Questions and bug reports: open a GitHub issue on this repository.