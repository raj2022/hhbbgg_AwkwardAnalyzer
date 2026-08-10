# hhbbgg AwkwardAnalyzer

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
  argument parser