# NanoAOD to Parquet Production(v2)

To produce .parquet files, follow the instructions provided in the [manual](https://higgs-dna.readthedocs.io/en/latest/index.html) and the tutorial available [here](https://indico.cern.ch/event/1360961/contributions/5777678/attachments/2788218/4861762/HiggsDNA_tutorial.pdf).

## Instructions to Produce .parquet File

### 1. Higgs DNA Installation

1. **Clone the HiggsDNA Repository**
   - You can use either the main [HiggsDNA project](https://gitlab.cern.ch/HiggsDNA-project/HiggsDNA) or the [hhbbgg branch](https://gitlab.cern.ch/hhbbgg/HiggsDNA):
     ```bash
     git clone --branch HHbbgg_v2_parquet ssh://git@gitlab.cern.ch:7999/cms-analysis/general/HiggsDNA.git
     cd HiggsDNA
     ```

2. **Set Up the Environment**
   - Create the Conda environment:
     ```bash
     conda env create -f environment.yml
     ```
     - If available, use `mamba` for faster setup:
       ```bash
       mamba env create -f environment.yml
       ```
   - Activate the environment and install the necessary packages:
     ```bash
     conda activate higgs-dna
     pip install -e .[dev] # Install additional development dependencies
     ```
   - Download necessary files:
	```bash
	python scripts/pull_files.py --all
	```

3. **Set Up Voms Proxy (if not already done)**
   - Follow the instructions provided [here](https://uscms.org/uscms_at_work/computing/getstarted/get_grid_cert.shtml).
   - Setup `VOMS`:
	```bash
	voms-proxy-init --voms cms --valid 192:00
    voms-proxy-init --rfc --voms cms -valid 192:00
	```
   - To check the proxy:
	```bash
	voms-proxy-info -all
	```
   - To test the grid certificates:
	```bash
	grid-proxy-init -debug -verify 
	```

4. **Run the Analysis**
   - Basic command line:
     ```bash
     python run_analysis.py --json-analysis YourJson.js --dump output_test
     ```
   - Command line "ready to go" (in the `tests/` directory). Following the instruction as provided in, https://indico.cern.ch/event/1451222/contributions/6208287/attachments/2959259/5210616/HHtobbgg_meeting_20241101.pdf:
    
    ```bash
        python scripts/run_analysis.py --json-analysis My_Json_1.json --dump ../../../output_parquet/v2_production/ --doFlow_corrections --fiducialCuts store_flag --skipCQR --Smear_sigma_m --doDeco --executor futures --skipbadfiles
    ```

    - Jobs to submit, more information can be found: https://higgs-dna.readthedocs.io/en/latest/postprocessing.html
    ```bash
    python scripts/run_analysis.py --json-analysis My_Json_1.json --dump ../../../output_parquet/ --skipCQR --executor vanilla_lxplus --queue espresso
    ```
    With complete path 
    ```bash
    python scripts/run_analysis.py --json-analysis /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/higgsDNA_prav/HiggsDNA_v1_setup/My_Json_1.json --dump /afs/cern.ch/user/s/sraj/Analysis/output_parquet --skipCQR --executor vanilla_lxplus --queue espresso
    ```
## Workflow

The workflow is based on the files found in `higgsdna/workflows/`. This is where the systematics, scale factors, MVA, and selection cuts are applied. The base workflow used for the Hgg analysis is `base.py`. 

The `HHbbgg.py` file defines the HHbbgg processor (`HHbbggProcessor`), which inherits from the Hgg processor (`HggProcessor`).

- **`HHbbgg.py`**: This workflow inherits directly from the base processor (the main processor for Hgg analysis). All functions defined in the base workflow are inherited and do not need to be re-implemented in `HHbbgg`, except for the `process` function.

- **`higgs_dna/workflows/__init__.py`**: This file is where the processors are defined with names recognized by `run_analysis.py`.

**NOTE** Sometimes, we have error in configuration due to mismtach of `setuptools`
```bash
pip install setuptools==65.0.1
```
To convert `.parquet` to root we can follow this [step](https://higgs-dna.readthedocs.io/en/latest/postprocessing.html). All the steps can be performed in one go with a command more or less like this:
```bash
python3 prepare_output_file.py --input [path to output dir] --merge --root --ws --syst --cats --args "--do_syst"
```
Example to convert to `.parquet` to merged folder
```bash
 python3 prepare_output_file.py --input ../../../output_parquet  --merge --root --ws --syst --cats --args "--do_syst"
 ```
Produced root files are named as `merged.parquet`, to convert into root, we are using these two shell scripts, [filename_change.sh](https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/main/jsonhiggsdnaproduction/filename_change.sh) and [run_conversion.sh](https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/main/jsonhiggsdnaproduction/run_conversion.sh) 

Further, to convert to `.root` files, eg:-
```bash
python scripts/postprocessing/convert_parquet_to_root.py ../../../output_parquet/merged/NMSSM_X400_Y70/nominal/NOTAG_merged.parquet ../../../output_root/NMSSM/NMSSM_X400_Y70.root mc
```
**NOTE** sometimes we have name error of `NOTAG`
On lxplus
```bash
conda activate higgs-dna
cd /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/higgsDNA_prav
cd HiggsDNA_v1_setup # Can enter HiggsDNA_v1_setup_0 as well
```
## Production of background files
On the production of background files, the `.json` file can be found [here](https://gitlab.cern.ch/hhbbgg/HiggsDNA/-/blob/master/tests/HHbbgg_xrootd.json?ref_type=heads) and all of the samples are present [here](https://gitlab.cern.ch/hhbbgg/HiggsDNA/-/blob/master/tests/samples_v12_HHbbgg_xrootd.json?ref_type=heads)

To run the smaple with the above `.json` files, we can run the command
```bash
# Make sure you are in the hhbbgg/HiggsDNA folder
cd tests
python ../scripts/run_analysis.py --json-analysis HHbbgg_xrootd.json --dump ../../../../output_parquet/ --skipCQR --executor futures
```
## Samples information
V2 README file: https://gitlab.cern.ch/hhbbgg/docs/-/tree/v2_ReadMe/v2?ref_type=heads
List of samples used to produce postEE backgrounds files
https://gitlab.cern.ch/hhbbgg/docs/-/blob/v2_ReadMe/dataset_lists_parquet_v1.md?ref_type=heads
## References:
1. https://gitlab.cern.ch/hhbbgg/HiggsDNA#worfklow
2. https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid#BasicGrid
3. https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookXrootdService 
4. https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideRunningGridPrerequisites#Test_your_grid_certificate
