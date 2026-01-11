<!-- ## Setup `HiggsDNA` 
- use tag [HHbbgg_NanoAODv15](https://gitlab.cern.ch/cms-analysis/general/HiggsDNA/-/tree/HHbbgg_NanoAODv15?ref_type=heads)
```bash
git clone --branch HHbbgg_NanoAODv15 ssh://git@gitlab.cern.ch:7999/cms-analysis/general/HiggsDNA.git
```
- Install and activate higgs-dna environment using conda/mamba/micromamba; micromamba is much faster
- Install the package: `cd HiggsDNA && pip install -e .[dev]`
-  Download necessary files: `python higgs_dna/scripts/pull_files.py --all`
- If your institute cluster does not have eos access, clone the repository in lxplus, pull_files and transfer necessary files to institute cluster
- Authenticate your grid certificate (for xrootd usage): `voms-proxy-init --rfc --voms cms -valid 192:00`
- Fetch the xrootd links for the samples: `python higgs_dna/scripts/samples/fetch_datasets.py -i samples.txt -w Yolo`
* `samples_2024.txt` contains dataset name and DAS name
* This will produce a samples.json file specifying the dataset name and the xrootd link for the samples


 -->


# V4 Production 
- Setup HiggsDNA
```bash
git clone ssh://git@gitlab.cern.ch:7999/cms-analysis/general/HiggsDNA.git
cd HiggsDNA
git fetch origin
git checkout tags/HHbbgg_v4_parquet -b HHbbgg_v4_parquet
mamba create -n higgs-dna_hhbbgg_v4 python=3.12 xrootd
mamba activate higgs-dna_hhbbgg_v4
pip install -e .[dev,test]
cd higgs_dna
python scripts/pull_files.py --all
```






## job submission  from private
- Activate environment
```bash
mamba activate higgs-dna
voms-proxy-init --rfc --voms cms -valid 192:00
```
- use script `submit_job.py`
```bash
python ./submit_job.py --input.json --ouput_dir
```
e.g.
```bash
python ./submit_job.py My_Json_300.json /eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2023_postBPix/
```


that would be (when we run from private afs area)
```bash
python /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/parquet_production_v3/HiggsDNA/higgs_dna/scripts/run_analysis.py --json-analysis My_Json_300.json --dump /eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2023_postBPix/ --doFlow-corrections --fiducialCuts store_flag --Smear-sigma-m --doDeco --executor vanilla_lxplus --queue workday --memory 10000 --timeout 300 --nano-version 12
```




```bash
mamba activate higgs-dna
voms-proxy-init --rfc --voms cms -valid 192:00
python /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/2024_parquet_production/tag15/HiggsDNA/higgs_dna/scripts/run_analysis.py --json-analysis My_Json_400.json --dump /afs/cern.ch/user/s/sraj/private/output/  --fiducialCuts store_flag --Smear-sigma-m --applyCQR  --nano-version 12 --executor vanilla_lxplus --queue espresso # if we want a quick output
```


## File storage
* Backgrounds and data: `/eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v4/Run3_2024`
* Signal: `/eos/user/b/bsahu/HiggsDNA_v4PrelimProd/2024/merged/`


## References:
1. Instructions: https://indico.cern.ch/event/1499924/contributions/6478750/attachments/3053886/5398744/For_Hgg_v3_production-2.pdf
2. v4 Instructions: https://indico.cern.ch/event/1590752/contributions/6805177/attachments/3178875/5654008/InstructionsFor2024HHbbggProduction_20251121.pdf 
3. 
