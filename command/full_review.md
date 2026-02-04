```bash
cd slides_fitting/CMSSW_14_1_0_pre4/src/
cmsenv
mamba activate hhbbgg-awk
```

- `pDNN` for the `.parquet` file
```bash
cd ML_Application/parametrized_DNN/
python pDNN_check_working_f.py
```
-  To run on the complete dataset for three years:
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
