# Data Driven Background estimation
Instructions given at : https://gitlab.cern.ch/cms-analysis/general/HiggsDNA/-/blob/master/higgs_dna/scripts/HHbbgg_DD_Estimate.py?ref_type=heads
* `YAML file`: https://gitlab.cern.ch/hhbbgg/docs/-/blob/master/v1/samples_v1_Run3_2022postEE.yaml?ref_type=heads


# Fitting `mvaID`
Use your fake-γ samples only (DDQCD / QCD / GJets):
- 
```bash
`python idmva_fitting.py \
  -i DDQCDGJET_Rescaled.parquet GGJets_low_Rescaled.parquet GGJets_high_Rescaled.parquet \
  --var lead_mvaID --nbins 40 --out fit_2023preBPix_lead
  ```
or with plain MC:
-
```bash
 python fit_fakegamma_mvaid.py \
  -i QCD_PT-30ToInf.parquet QCD_PT-40ToInf.parquet GJetPt40.parquet GGJets.parquet \
  --var sublead_mvaID --out fit_2023preBPix_sublead
  ```



## Instruction
```bash
ipython3 higgs_dna/scripts/HHbbgg_DD_Estimate.py -- -i 22postEE.yaml  -o ../../../output_parquet/data_driven_bkg/ --run-era Run3_2022postEE
```



- Fit the max photon MVA (default), splitting EB vs EE:
```bash
python fit_mvaid.py \
  -i /path/to/DD_CombinedAll/*.parquet \
  --which max \
  --out fit_maxMVA
```
- Fit the min photon MVA (often used in the DD method):
```bash
python fit_mvaid.py \
  -i /path/to/DD_CombinedAll/*.parquet \
  --which min \
  --out fit_minMVA
```

To use a different functional form:
```bash
python fit_mvaid.py -i DD/*.parquet --which max --model "pol3" --out fit_pol3
```
* Example to run it:
```bash
python idmva_fitting.py -i ../../output_root/v3_production/samples/preBPix/DDQCDGJET_Rescaled.parquet --which min --fit-min -0.70 --ymax 0.1
```

