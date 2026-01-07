# fittings 

### Signal fitting 
to run the signal fitting for mgg
```bash
python3 Signal/fit_signal_shapes_for_slides.py \
    --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
    --edges 0.8002240580158556 0.8574103025311034\
    --cats 0 1 2 \
    --mgg-min 115 \
    --mgg-max 135 \
    --outdir outputs/signal_fits \
    --only-signal X1000_Y125
```
<!-- to run the signal fitting for mjj
```bash
python Signal/fit_signal_mjj_for_slides.py --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root --edges 0.8002240580158556 0.8574103025311034   --cats 0 1 2   --mjj-min 115 --mjj-max 135 --bins 120 --kmax 3   --outdir outputs/signal_fits --max-events 10000
``` -->
```bash
cmsenv
```

# python3 Signal/fit_signal_mjj_for_slides.py \
#   --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
#   --edges-json outputs/categories/event_categories.json \
#   --mjj-min 115 --mjj-max 135 \
#   --bins 120 --kmax 3 \
#   --outdir outputs/signal_fits_mjj_by_mass \
#   --max-events 100000 \
#   --only-signal NMSSM
# ```

- with edges json
```bash
python Signal/fit_signal_mjj_for_slides.py \
    --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
    --edges-json outputs/categories_alpha_3cats/event_categories.json \   # Can also use the edge number like above
    --mjj-min 50 \
    --mjj-max 180 \
    --outdir outputs/signal_fits_mjj \
    --only-signal X1000_Y125
```
- With edges

```bash
python3 Signal/fit_signal_mjj_for_slides.py  \
 --root ../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
 --edges 0.8002240580158556 0.8574103025311034  \
--mjj-min 50 --mjj-max 200   --bins 120 --kmax 3  \
--outdir outputs/signal_fits_mjj_by_mass  \
--max-events 100000 --only-signal X1000_Y125
```

From the signal folder:
```bash
python3 make_signal_ws_from_json.py   --json ../outputs/signal_fits/signal_shape_params.json   --year 2018   --proc NMSSM   --outdir Signal/SignalWS_mgg   --mgg 100,180   --verbose
```

# To create signal workspace (1D)
```bash
cmsenv
python3 Signal/make_signal_ws_from_json.py \
  --json outputfiles/signal_mgg.json \
  --year 2018 \
  --proc NMSSM \
  --outdir Signal/SignalWS_mgg \
  --mgg 100,180

```



# Create 2D signal workspaces for chosen mass
Use the `make_signal_ws_2D_from_jsons.py` script. Since your mjj JSON is a combined-by-mass file, call the script with `--mass 1000` (or point directly to the per-mass file). Two equivalent ways:
A) Point at the combined-by-mass JSON + `--mass 1000`:
```bash
python3 Signal/make_signal_ws_2D_from_jsons.py \
  --mgg_json outputs/signal_fits/signal_shape_params.json \
  --mjj_json outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json \
  --mass 1000 \
  --year 2018 \
  --proc NMSSM \
  --outdir Signal/SignalWS_2D \
  --mgg 115,135 --mjj 50, 200\
  --verbose
```
B) Or point at the per-mass JSON directly:
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

