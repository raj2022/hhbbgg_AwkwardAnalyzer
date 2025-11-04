
### for non-resoannt bkg:
```bash
python slides_fitting/non-resonant_bkg.py --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/categories_alpha/event_categories.json   --cats 0 1 2   --mgg-min 105 --mgg-max 160 --bins 56   --blind-lo 115 --blind-hi 135   --use-data   --wgt-branch ''   --outdir outputs/nonres_mgg_fits --families exponential bernstein chebyshev powerlaw
```


for non-resonant(m_jj):
```bash
python slides_fitting/non_resonant_bkg_mjj.py   --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/categories_alpha/event_categories.json   --cats 0 1 2   --mgg-min 105 --mgg-max 160 --mgg-bins 56   --blind-lo 115 --blind-hi 135   --do-mjj --mjj-min 60 --mjj-max 180 --mjj-bins 60   --use-data   --wgt-branch '' --outdir outputs/nonres_fits
```



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
  ```
