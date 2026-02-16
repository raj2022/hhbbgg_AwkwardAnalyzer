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
- If adding particleNet regrressed masss 
* `regions.py`

## For including file name:
 - Inlcude the file name or similar structure in the `normalisation.py`
 - further include it the Plotter, `hhbbgg_Plotter.py`
 

## 2024
- To run only the 2024 signal samples
```bash
python hhbbgg_analyzer_lxplus_par.py --year 2024 -i /eos/user/b/bsahu/HiggsDNA_v4PrelimProd/2024/merged/NMSSM-XtoYH-MX-300-MY-100/NOTAG_merged.parquet
``` 

- To run on the complete dataset for three years:
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-year 2024 \
  -i /eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/v4_production/2024 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/ \
  --tag DD_CombinedAll
```


-  To Run only 2022
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-year 2022 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/preEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/postEE/
```
-  To Run only 2023
```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-year 2023 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/preBPix/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/postBPix/
```

- To run only 2024:
```bash
 python hhbbgg_analyzer_lxplus_par.py \
 --config-year 2024 \
 -i /eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/sample_final_nominal/2024 
 ```


# To Run the systematics
```bash
python make_templates.py \
  --year 2022 \
  /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/NMSSM_X300_Y100/
```



# To read files from central B2G directories:
```
python hhbbgg_analyzer_lxplus_par.py --config-year 2023 --era postBPix \
-i /eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v3/Run3_2023/sim/postBPix \
--datasets GGJets_MGG-80,VHtoGG --tag Y2023_PostBPix 
```

# To Run systematics from the nominal parquet files:
```bash
#step 1: Run the AwkwardAnalyzer using hhbbgg_analyzer_lxplus_par_systematics_v1.py file

python hhbbgg_analyzer_lxplus_par_systematics_v1.py --config-year 2022 --era PreEE \
-i /eos/user/b/bsinghal/analysis/output/2022preEE/merged/ --tag Y2022_PreEE

python hhbbgg_analyzer_lxplus_par_systematics_v1.py --config-year 2022 --era PostEE \
-i /eos/user/b/bartek/hhbbgg/systematics_v3/2022_postEE/merged/ --tag Y2022_PostEE

#step 2: similar to the previous script, this will create the root files.
#The Tdirectory format in the histogram root file is changed.
```

```bash
hhbbgg_analyzer-v2-histograms.root
  \u2514\u2500 Sample name
  \u2514\u2500 regions  
  \u2514\u2500 weight (name of weight columns)
  \u2514\u2500 variables
```
```bash
#The output file can be found:
/eos/user/b/bsahu/B2G_25_010_AwkwardAnalyzer/updated_central/hhbbgg_AwkwardAnalyzer/systematics_noBin_changed_outputfiles

#step 3: make plot of the sytematics using makeplot_syst.py:
python3 script_by_python.py -i 2022_postEE/hhbbgg_analyzer-v2-histograms.root \
--base NMSSM_X500_Y150_nominal --sel preselection --hist dibjet_mass  \
-o MX500_MY150_bb_mass --outdir 500_150_bb_pngs_presel  --pdfdir 500_150_bb_pdfs_presel\
--year 2022postEE --lumi 26.67

# This step will create two directories: 500_150_bb_pdfs_presel & 500_150_bb_pngs_presel for pdfs and png files, respectively. 
```



# Files storage for year and combined
Files after processed through `analyzer`
* 2022 : `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2022_All/hhbbgg_analyzer-v2-histograms.root`
* 2023:`/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2023_All/hhbbgg_analyzer-v2-histograms.root`
* 2024: `/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/2024_All`
* Combined_all =




