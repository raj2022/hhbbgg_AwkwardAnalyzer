to run the signal fitting for mgg
```bash
python slides/fit_signal_shapes_for_slides.py   --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges 0.8002240580158556 0.8574103025311034   --cats 0 1 2   --mgg-min 115 --mgg-max 135 --bins 120 --kmax 5   --outdir outputs/signal_fits
```

to run for resoanant bkg
```bash
python slides/fit_resonant_backgrounds.py  
 --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/ca
tegories_alpha/event_categories.json   --cats 0 1 2   --mgg-min 115 --mgg-max 135 --bins 60   --o
utdir outputs/res_bkg_fits
```


for non-resoannt bkg:
```bash
python slides/non-resonant_bkg.py --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/categories_alpha/event_categories.json   --cats 0 1 2   --mgg-min 105 --mgg-max 160 --bins 56   --blind-lo 115 --blind-hi 135   --use-data   --wgt-branch ''   --outdir outputs/nonres_mgg_fits --families exponential bernstein chebyshev powerlaw
```


for non-resonant(m_jj):
python slides/non_resonant_bkg_mjj.py   --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-tree
s.root   --edges-json outputs/categories_alpha/event_categories.json   --cats 0
 1 2   --mgg-min 105 --mgg-max 160 --mgg-bins 56   --blind-lo 115 --blind-hi 13
5   --do-mjj --mjj-min 60 --mjj-max 180 --mjj-bins 60   --use-data   --wgt-bran
ch ''   --outdir outputs/nonres_fits




python slides/non_resonant_bkg_mjj.py \
  --root outputfiles/merged/DataAll/hhbbgg_analyzer-v2-trees.root \
  --edges-json outputs/categories_alpha/event_categories.json \
  --cats 0 1 2 \
  --mgg-min 105 --mgg-max 160 --mgg-bins 56 \
  --blind-lo 115 --blind-hi 135 \
  --do-mjj --mjj-min 60 --mjj-max 180 --mjj-bins 60 \
  --use-data \
  --wgt-branch '' \
  --outdir outputs/nonres_fits
