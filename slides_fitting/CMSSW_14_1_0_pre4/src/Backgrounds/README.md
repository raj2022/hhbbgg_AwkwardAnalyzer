
### for non-resoannt bkg:
```bash
python slides_fitting/non-resonant_bkg.py --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/categories_alpha/event_categories.json   --cats 0 1 2   --mgg-min 105 --mgg-max 160 --bins 56   --blind-lo 115 --blind-hi 135   --use-data   --wgt-branch ''   --outdir outputs/nonres_mgg_fits --families exponential bernstein chebyshev powerlaw
```


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


<!-- 

```bash
python slides_fitting/non_resonant_bkg_mjj.py \
  --root outputfiles/merged/DataAll/hhbbgg_analyzer-v2-trees.root \
  --edges-json outputs/categories_alpha/event_categories.json \
  --cats 0 1 2 \
  --mgg-min 105 --mgg-max 160 --mgg-bins 56 \
  --blind-lo 115 --blind-hi 135 \
  --do-mjj --mjj-min 60 --mjj-max 180 --mjj-bins 60 \
  --use-data \
  --wgt-branch '' \
  --outdir outputs/nonres_fits
  ``` -->


```bash
python data/make_data_hists.py  
```


# To create 2D worksapce 
```bash
# python3 Backgrounds/make_bkg_ws_from_jsons.py \
#   --res_mgg_json outputs/res_bkg_fits/resonant_bkg_dcb_params.json \
#   --nonres_mgg_json outputs/nonres_mgg_fits/nonres_mgg_envelope.json \
#   --mjj_json outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json \ # Should be of backgrounds not of the signal
#   --year 2018 --outdir Background/WS_bkg_2D
python3 Backgrounds/make_bkg_ws_from_jsons.py   --res_mgg_json outputs/res_bkg_fits/resonant_bkg_dcb_params.json   --nonres_mgg_json outputs/nonres_mgg_fits/nonres_mgg_envelope.json   --mjj_json outputs/nonres_fits/nonres_envelope_results.json   --year 2018 --outdir Background/WS_bkg_2D
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