# hhbbgg AwkwardAnalyzer
Repository to keep the analyzers using awkward arrays, using skimmer or nanoAOD as input.

### Dependencies
Following packages are needed for the analyzer to work
```
matplotlib
uproot
hist
numpy
mplhep
vector
root
awkward
pandas
pyarrow
```
A virtual environment can be created for this using the following command
```
conda env create -f requirement.yaml
```
if available, do it with mamba, it's much faster
```
mamba env create -f requirement.yaml
```
To use the framework, the environment created by conda has to be activated every time. It can be done as follows:
```
conda activate hhbbgg-awk
```
For now the analyzer can be run normally using python

#### with `.root` file
```
python hhbbgg_Analyzer.py -i <Input root file directory OR single root file>
```
provided that the input directory having one root file for each background is defined with the variable name `inputfilesDir` in `hhbbgg_Analyzer.py`.
This saves a root file in `outputfiles` which contains sample names as directory and all the histograms are saved inside those directories.

#### with `.parquet` file
```
python hhbbgg_Analyzer_parquet.py -i <Input root file directory OR single root file>
```
e.g. with all file moved in this `NMSSM_v2`
```
python hhbbgg_Analyzer_parquet.py -i ../../output_root/v2_production_central/
```

To plot the histograms `hhbbgg_Plotter.py` can be used as:
```
python hhbbgg_Plotter.py
```
The plots will be saved in `stack_plots` directory

To add the variable, changes are to be done in `hhbbgg_Analyzer.py`, `binning.py` and `variables.py` file

To plot the histogram of the variable, it has to be added in `histogram_names` list and `xtitle_dict` dictionary in `hhbbgg_Plotter.py` file


### Fixing issues of seg fault on lxplus
with files `hhbbgg_analyzer_lxplus_par.py`, it fixes the seg fault.  
```bash
python hhbbgg_analyzer_lxplus_par.py -i ~/public/samples/VBFHToGG.parquet
```


# Quickstart
```bash
# 1. Clone the repository
git clone https://github.com/raj2022/hhbbgg_AwkwardAnalyzer.git
cd hhbbgg-AwkwardAnalyzer

# 2. Install micromamba (lightweight, recommended)
curl -Ls https://micro.mamba.pm/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"

# 3. Create the environment
micromamba create -f environment.yml

# 4. Activate the environment
micromamba activate hhbbgg-awk

# 5. Run the analyzer (example with .root file)
python hhbbgg_Analyzer.py -i <input_root_file_or_dir>
```

## Changes according to `Era`

### Single era/year (use config)
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2022 --era PostEE
```

This will:
* Read Parquet files from the path defined in datasets.yaml
* Write outputs to:
```bash
outputfiles/2022/PostEE/
  ├─ hhbbgg_analyzer-v2-histograms.root
  └─ hhbbgg_analyzer-v2-trees.root
```

### Override input path manually
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2022 --era PostEE \
  -i /afs/cern.ch/user/s/sraj/public/samples
```
### combine everything (2022 + 2023, all eras)
Provide `-i` multiple times:
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix \
  --tag CombinedAll
```
### For individual eras
#### 2022 only
```bash
# 2022 PreEE (C+D)
python hhbbgg_analyzer_lxplus_par.py \
  --year 2022 --era PreEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE \
  --tag Y2022_PreEE

# 2022 PostEE (E+F+G)
python hhbbgg_analyzer_lxplus_par.py \
  --year 2022 --era PostEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE \
  --tag Y2022_PostEE
```
#### 2023 only

```bash
# 2023 preBPix (Era C)
python hhbbgg_analyzer_lxplus_par.py \
  --year 2023 --era preBPix \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix \
  --tag Y2023_preBPix

# 2023 postBPix (Era D)
python hhbbgg_analyzer_lxplus_par.py \
  --year 2023 --era postBPix \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix \
  --tag Y2023_postBPix
```

### drive from `datasets.yaml` (no `-i`)
If you wired `RunConfig` to use `cfg.raw_paths` when `-i` isn’t given, you can run:
```bash
# From YAML: 2022 (PreEE+PostEE)
python hhbbgg_analyzer_lxplus_par.py --year 2022 --era All --tag Combined2022

# From YAML: 2023 (preBPix+postBPix)
python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All --tag Combined2023
```




### With DD sample:

#### Combine DD (2022 + 2023, all eras)
with only a file
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/DDQCDGJET_Rescaled.parquet \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/DDQCDGJET_Rescaled.parquet \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/DDQCDGJET_Rescaled.parquet \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/DDQCDGJET_Rescaled.parquet \
  --tag DD_CombinedAll
```
with whole folder
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/ \
  --tag DD_CombinedAll
```

For individual eras

#### 2022 only
```bash
# 2022 PreEE
python hhbbgg_analyzer_lxplus_par.py \
  --year 2022 --era PreEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/DDQCDGJET_Rescaled.parquet \
  --tag DD_Y2022_PreEE

# 2022 PostEE
python hhbbgg_analyzer_lxplus_par.py \
  --year 2022 --era PostEE \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/DDQCDGJET_Rescaled.parquet \
  --tag DD_Y2022_PostEE
```
#### 2023 only 
```bash
# 2023 preBPix
python hhbbgg_analyzer_lxplus_par.py \
  --year 2023 --era preBPix \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/DDQCDGJET_Rescaled.parquet \
  --tag DD_Y2023_preBPix

# 2023 postBPix
python hhbbgg_analyzer_lxplus_par.py \
  --year 2023 --era postBPix \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/DDQCDGJET_Rescaled.parquet \
  --tag DD_Y2023_postBPix
```




## For Changing variables
- Change variables in these variables.
* `binning.py`
* `hhbbgg_analyzer_lxplus_par.py`
* `variables.py`

## For including file name:
 - Inlcude the file name or similar structure in the `normalisation.py`
 - further include it the Plotter, `hhbbgg_Plotter.py`
 

