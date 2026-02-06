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



the outputs are saved in the `/outputfiles/merged/hhbbgg_analyzer-v2-trees.root`. On the saved root files, we check the plots of Data/MC using `python hhbbgg_Plotter.py`

To get the cat numbers, we run using
```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_alpha_3cats \
  --write-categorized --sigmoid-score
```



# Working on the fitting 

- STEP 1 — Fit Signal mgg
from `src` directory inside the CMSSW_14_1_0_pre4
```bash
python3 Signal/fit_signal_shapes_for_slides.py \
    --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
    --edges 0.6488002028418868 0.6622506022306672 \
    --cats 0 1 2 \
    --mgg-min 115 \
    --mgg-max 135 \
    --outdir outputs/signal_fits \
    --only-signal X1000_Y125
```
Produces: `outputs/signal_fits/signal_shape_params.json`


- Step 2 - Fit Signal mjj (per mass point)
--- Can also use the edge number like above
```bash
python Signal/fit_signal_mjj_for_slides.py\
    --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root\
    --edges-json outputs/categories_alpha_3cats/event_categories.json\   
    --mjj-min 50\
    --mjj-max 180\
    --outdir outputs/signal_fits_mjj\
    --only-signal X1000_Y125

  ```
Produces:

`outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json`

Per-mass fits, e.g.
`outputs/signal_fits_mjj_by_mass/1000/signal_mjj_params.json`

PNG diagnostics per mass and category.



for non-resonant(m_jj and mgg):
```bash
python Backgrounds/non_resonant_bkg_mgg_mjj.py \
    --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
    --edges-json outputs/categories_alpha/event_categories.json \
    --cats 0 1 2 \
    --mgg-min 105 \
    --mgg-max 160 \
    --mgg-bins 56 \
    --blind-lo 115 \
    --blind-hi 135 \
    --do-mjj \
    --mjj-min 60 \
    --mjj-max 180 \
    --mjj-bins 56 \
    --use-data \
    --wgt-branch '' \
    --outdir outputs/nonres_fits

```



### Resonant background
to run for resoanant bkg: $m_{\gamma\gamma}$
```bash
python Backgrounds/fit_resonant_backgrounds.py --root ../../../outputfiles
/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root --edges-json outputs/categories_alpha_3cats/event_categories.json --cats 0 1 2 --mgg-min 115 --mgg-max 135 --bins 60 --outdir outputs/res_bkg_fits/
```
to run the resonant bkg: $m_{jj}$
- Use only MC (`isdata==0`):
```bash
python Backgrounds/fit_resonant_mjj.py --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root  --edges-json outputs/categories_alpha_3cats/event_categories.json --cats 0 1 2 --mjj-min 90 --mjj-max 200 --bins 45 --us
e-isdata
```
-  Include all entries (ignore `isdata`):
```bash
python Backgrounds/fit_resonant_mjj.py --root ../../../outputfiles/merged/
DD_CombinedAll/hhbbgg_analyzer-v2-trees.root  --edges-json outputs/categories_alpha_3cats/event_categories.json --cats 0 1 2 --mjj-min 90 --mjj-max 200 --bins 45 
```



STEP 3 — Build 2D Signal Workspaces
For a given mass point (e.g. 1000 GeV):
```bash
python3 Signal/make_signal_ws_2D_from_jsons.py \
  --mgg_json outputs/signal_fits/signal_shape_params.json \
  --mjj_json outputs/signal_fits_mjj_by_mass/1000/signal_mjj_params.json \
  --year 2018 \
  --proc NMSSM \
  --outdir Signal/SignalWS_2D \
  --mgg 115,135 --mjj 115,135 \
  --verbose
```
Produces:
```bash
Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c0.root
Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c1.root
Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c2.root
```
If any category is missing signal events, a file may be missing `(e.g. _c2.root)`.
Either remove that category from your datacard or build a dummy workspace.



- STEP 4 — Fit Backgrounds

Using your two background JSONs ( `nonres_mgg_envelope.json, resonant_bkg_dcb_params.json`):
```bash
python3 Backgrounds/make_bkg_ws_from_jsons.py \
  --res_mgg_json outputs/res_bkg_fits/resonant_bkg_dcb_params.json \
  --nonres_mgg_json outputs/nonres_mgg_fits/nonres_mgg_envelope.json \
  --mjj_json outputs/nonres_fits/nonres_envelope_results.json \
  --year 2018 \
  --outdir Background/WS_bkg_2D \
  --verbose
```
Produces:
```bash
Background/WS_bkg_2D/2018/ws_bkg_2018_c0.root
Background/WS_bkg_2D/2018/ws_bkg_2018_c1.root
Background/WS_bkg_2D/2018/ws_bkg_2018_c2.root
```

- STEP 5 — Prepare Data Histograms
5a. Extract data histograms from your merged ROOT file
```bash
python3 data/make_data_hists.py \
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --edges 0.8002240580158556 0.8574103025311034 \
  --mjj-lo 115 --mjj-hi 135 \
  --bins 40 --cats 0 1 2 \
  --outdir data/data_npz
```
Produces:
`data/data_npz/data_ch0.npz`, `data_ch1.npz`, etc.

5b. Convert `.npz` histograms → ROOT TH1
```bash
python3 data/npz_to_root_hist.py \
  --in-dir data/data_npz \
  --out-root data/data_obs_mass1000.root
```
Produces:
`data/data_obs_mass1000.root` containing histograms:
```bash
hist_data_ch0, hist_data_ch1, hist_data_ch2
```


convert the 2D to 1D as combine cannot run with 2D. 
```bash
python3 data/convert_th2_to_roodatahist.py
```


# Impact plot plotting

-  Step 0 — Convert datacard → workspace
```bash
text2workspace.py datacard/400/comb_mass_syst_400.txt \
  -o datacard/400/comb_mass_syst_400.root
```
This creates:
```bash
comb_mass_syst_400.root
```
- Step 1 — Initial fit (NOW this will work)
```bash
combineTool.py -M Impacts \
  -d datacard/400/comb_mass_syst_400.root \
  -m 400 \
  --robustFit 1 \
  --rMin 0 --rMax 5 \
  --freezeParameters allBkg \
  --doInitialFit
```

- Step 2 — Per-nuisance fits
```bash
combineTool.py -M Impacts \
  -d datacard/400/comb_mass_syst_400.root \
  -m 400 \
  --robustFit 1 \
  --rMin 0 --rMax 5 \
  --freezeParameters allBkg \
  --doFits \
  --parallel 8
```
- Step 3 — Collect impacts
```bash
combineTool.py -M Impacts \
  -d datacard/400/comb_mass_syst_400.root \
  -m 400 \
  -o impacts_mass400.json
```
- Step 4 — Plot
```bash
plotImpacts.py -i impacts_mass400.json -o impacts_mass400
```




# To Run the systematics
```bash
python make_templates.py \
  --year 2022 \
  /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/NMSSM_X300_Y100/
```
