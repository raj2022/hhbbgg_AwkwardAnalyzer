## Setup `HiggsDNA` 
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




```bash
mamba activate higgs-dna
voms-proxy-init --rfc --voms cms -valid 192:00
python /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/2024_parquet_production/tag15/HiggsDNA/higgs_dna/scripts/run_analysis.py --json-analysis My_Json_400.json --dump /afs/cern.ch/user/s/sraj/private/output/  --fiducialCuts store_flag --Smear-sigma-m --applyCQR  --nano-version 12 --executor vanilla_lxplus --queue espresso
```





## References:
1. Instructions: https://indico.cern.ch/event/1499924/contributions/6478750/attachments/3053886/5398744/For_Hgg_v3_production-2.pdf
2. 
