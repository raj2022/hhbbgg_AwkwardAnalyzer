# fittings 

### Signal fitting 
to run the signal fitting for mgg
```bash
python slides_fitting/fit_signal_shapes_for_slides.py   --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges 0.8002240580158556 0.8574103025311034   --cats 0 1 2   --mgg-min 115 --mgg-max 135 --bins 120 --kmax 5   --outdir outputs/signal_fits
```
to run the signal fitting for mjj
```bash
python slides_fitting/fit_signal_mjj_for_slides.py   --root merged_run3_signals.root   --edges-json outputfiles/pdnn_edges.json   --mjj-min 50 --mjj-max 180   --outdir outputs/si
gnal_fits_mjj
```

### Resonant background
to run for resoanant bkg
```bash
python slides_fitting/fit_resonant_backgrounds.py --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --edges-json outputs/categories_alpha_3cats/event_categories.json   --cats 0 1 2   --mgg-min 115 --mgg-max 135 --bins 60   --outdir outputs/res_bkg_fits
```