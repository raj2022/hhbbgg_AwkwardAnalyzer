```bash
python event_categorization/build_pdnn_categories.py \
  --root outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
  --sr-sigma 2.0 --cr-sidebands 4 10 \
  --nmin 50 --min-gain 0.005 --max-bins 2 \
  --alpha-bins 60 \
  --outdir outputs/categories_alpha_3cats \
  --write-categorized --sigmoid-score

```




with preselection and ttG: [edges α-method] combined: [0.6488002028418868, 0.6622506022306672]
earlier it was with selection:  [0.8002240580158556 0.8574103025311034]
- new with all files in postEE: [0.6829967608364195 0.6881541571642115]