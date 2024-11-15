# NanoAOD to Parquet Production (v2)

To produce `.parquet` files, follow the instructions provided in the [manual](https://higgs-dna.readthedocs.io/en/latest/index.html) and the tutorial available [here](https://indico.cern.ch/event/1360961/contributions/5777678/attachments/2788218/4861762/HiggsDNA_tutorial.pdf).

---

## Instructions to Produce `.parquet` Files

### 1. Higgs DNA Installation

#### a. Clone the HiggsDNA Repository
```bash
# Clone the repository (choose the appropriate branch)
git clone --branch HHbbgg_v2_parquet ssh://git@gitlab.cern.ch:7999/cms-analysis/general/HiggsDNA.git
cd HiggsDNA
```
#### b. Set Up the Environment
```bash
# Create the Conda environment
conda env create -f environment.yml

# (Optional) Faster setup using mamba
mamba env create -f environment.yml

# Activate the environment and install dependencies
conda activate higgs-dna
pip install -e .[dev]

# Download necessary files
python scripts/pull_files.py --all
```
### c. Set Up Voms Proxy
```bash
# Initialize VOMS proxy
voms-proxy-init --voms cms --valid 192:00
voms-proxy-init --rfc --voms cms --valid 192:00

# Verify proxy
voms-proxy-info -all

# Test grid certificates
grid-proxy-init -debug -verify
```


### 2. Running the Analysis

#### Basic Command
```bash
python run_analysis.py --json-analysis YourJson.js --dump output_test
```
##### Full Command Example
```bash
python scripts/run_analysis.py \
  --json-analysis My_Json_1.json \
  --dump ../../../output_parquet/v2_production/ \
  --doFlow_corrections --fiducialCuts store_flag --skipCQR \
  --Smear_sigma_m --doDeco --executor futures --skipbadfiles
```
#### Submitting Jobs
```bash
# Submitting jobs with the vanilla executor
python scripts/run_analysis.py \
  --json-analysis My_Json_1.json \
  --dump ../../../output_parquet/ \
  --skipCQR --executor vanilla_lxplus --queue espresso

# Using absolute paths
python scripts/run_analysis.py \
  --json-analysis /afs/cern.ch/user/s/sraj/Analysis/My_Json_1.json \
  --dump /afs/cern.ch/user/s/sraj/Analysis/output_parquet \
  --skipCQR --executor vanilla_lxplus --queue espresso
```

## Workflow Overview

### Key Files
```bash
- base.py: Base workflow for Hgg analysis.
- HHbbgg.py: Inherits from base.py and defines HHbbggProcessor.
```
### Notes
```bash
# Ensure setuptools compatibility
pip install setuptools==65.0.1
```
Converting `.parquet` to `.root`
```bash
python3 prepare_output_file.py --input [path_to_output_dir] --merge --root --ws --syst --cats --args "--do_syst"
```

#### Example Conversion Command
```bash
python3 prepare_output_file.py \
  --input ../../../output_parquet \
  --merge --root --ws --syst --cats --args "--do_syst"
```


## Background Production
V2 README file: https://gitlab.cern.ch/hhbbgg/docs/-/tree/v2_ReadMe/v2?ref_type=heads
List of samples used to produce postEE backgrounds files
https://gitlab.cern.ch/hhbbgg/docs/-/blob/v2_ReadMe/dataset_lists_parquet_v1.md?ref_type=heads

## Background production 
Resonant and non-Resonant background production as provided samples in [here](https://gitlab.cern.ch/hhbbgg/docs/-/blob/v2_ReadMe/dataset_lists_parquet_v1.md?ref_type=heads#background-samples), with Non-Resonant samples containing, GGJEts, GJetPt20To40, GJetPt40, and resonant samples as GluGluHToGG, VHToGG, VBFHToGG, and ttHToGG.

Complete overview of commands are
```text
git clone --branch HHbbgg_v2_parquet ssh://git@gitlab.cern.ch:7999/cms-analysis/general/HiggsDNA.git
mamba activate higgs-dna
cd HiggsDNA && pip install -e .[dev]
python scripts/pull_files.py --all
voms-proxy-init --rfc --voms cms -valid 192:00
python fetch.py -i samples.txt -w Yolo
```
```bash
python scripts/run_analysis.py --json-analysis path_to_runner.json --dump path_to_out_directory --doFlow_corrections --fiducialCuts store_flag --skipCQR --Smear_sigma_m --doDeco --executor futures --skipbadfiles
```
Instructions:
* Use --skipbadfiles only for simulation
* Use --executor futures for parallel execution
* The default number of workers for --executor futures is 12, can be increased by specifying --workers <num>
*  —-executor also has iterative option, better for debugging
Use scripts/postprocessing/prepare_output_file.py to account for proper normalisation after b-tagging
* shape SF is applied
* If systematics not included:
python scripts/postprocessing/prepare_output_file.py --input path_to_out_directory --merge
* If systematics included:
python scripts/postprocessing/prepare_output_file.py --input path_to_out_directory --merge --syst -- varDict path_to_variation.json
* This will create path_to_out_directory/merge folder with merged parquet files for each samples and systematics

### Producing Background Files
```bash
# JSON configuration
# HHbbgg_xrootd.json: https://gitlab.cern.ch/hhbbgg/HiggsDNA/-/blob/master/tests/HHbbgg_xrootd.json
# Samples: https://gitlab.cern.ch/hhbbgg/HiggsDNA/-/blob/master/tests/samples_v12_HHbbgg_xrootd.json
```
#### Example Command
```bash
cd tests
python ../scripts/run_analysis.py \
  --json-analysis HHbbgg_xrootd.json \
  --dump ../../../../output_parquet/ \
  --skipCQR --executor futures
```
## Samples information

## Additional Resources
1. HiggsDNA Workflow Documentation: https://gitlab.cern.ch/hhbbgg/HiggsDNA#worfklow
2. Grid Computing Guide: https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid
3. VOMS Proxy Documentation: https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideRunningGridPrerequisites#Test_your_grid_certificate
4. V2 Parquet Files README: https://gitlab.cern.ch/hhbbgg/docs/-/tree/v2_ReadMe/v2?ref_type=heads#command-line
5. Sample List: https://docs.google.com/spreadsheets/d/1ZRDUpvrSmNhIzPpfc5R__G4OeucyvEmDi4EaeL0DVk/edit?gid=0#gid=0
6. Instruction Slides: https://indico.cern.ch/event/1451222/contributions/6208287/attachments/2959259/5210616/HHtobbgg_meeting_20241101.pdf

