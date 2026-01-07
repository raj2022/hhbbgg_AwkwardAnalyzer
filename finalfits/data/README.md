
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

# Helper: create data/data_obs_mass1000.root (if not present)
If you haven’t made the data histograms yet, run this script (adapt paths / branches if your ntuple uses different branch names). It will create data/data_obs_mass1000.root containing hist_data_ch0/1/2.


Not from `cmsenv`, from simple python, from ``hhbbgg_Analyzer` folder:

```bash
python3 slides_fitting/CMSSW_15_0_16/src/data/make_data_hists.py --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root
```
mv the `data_npz` folder to the data in `slides_fitting/CMSSW_15_0_16/src/data/`.

from the `src`, run:
```bash
cmsenv
python3 data/npz_to_root_hist.py --in-dir data/data_npz --out-root data/data_obs_mass1000.root
```


now we have to convert the 2D to 1D as combine cannot run with 2D. 
```bash
python3 data/convert_th2_to_roodatahist.py
```