# Signal study


## Turn-on problem
to plot the signal:
```bash
python signal_turn_on.py \
  --sig-tpl "../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet" \
  --bkg-file "../../output_root/v3_production/samples/postEE/GGJets.parquet" \
  --y 150 --xmin 300 --xmax 1000 --xstep 100 \
  --ellipse --save \
  --outdir "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN" \
  --debug


  ```
