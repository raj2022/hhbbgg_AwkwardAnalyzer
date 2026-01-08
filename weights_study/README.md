
### Plots weights variable
```bash
python weights_study.py   -i ../../output_root/v4_production/2024/GGJets_MGG-80.parquet   -o GGJets_weight_plots
```

### Compare plots for weights
python compare_weights_overlay.py \
  --ref /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/NMSSM_X300_Y100/nominal/NOTAG_merged.parquet \
  --var /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/NMSSM_X300_Y100/jer_syst_down/NOTAG_merged.parquet \
  -o NMSSM_X300_Y100_JER_overlay
