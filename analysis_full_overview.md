# Complete analysis summary


WS → datacard → combine


# Complete analysis summary


WS → datacard → combine




to install combine 
```bash
cmsrel CMSSW_14_1_0_pre4
cd CMSSW_14_1_0_pre4/src
cmsenv
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
scram b -j 4
```


If installed 
from the `hhbbgg_AwkwardAnalyzer`:
```bash
cd slides_fitting/
cd CMSSW_14_1_0_pre4/src
cmsenv
```
-  Setup environment 
```bash
cmsenv
voms-proxy-init -voms cms
```
- Activate the virtual env
```bash
mamba activate hhbbgg-awk
```

- Start with the pDNN training, which are trained with the `2022PostEE` parquets, on the training, use the pDNN Score file, `ML_Application/parametrized_DNN/python pDNN_check_working_f.py` has all of the python files and on the files to check the inference we need to do with all folder seperately, `python inference_PDnn.py -i /path/to/your/folder`. On the inference, we run the analyzer,
```bash
 python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/scored/   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/scored/   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/scored/   -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/scored/   --tag DD_CombinedAll
```
the Analyzer contains all processing of the samples which are processed with the DDbkg estimation and Tempelate fit.


the outputs are saved in the `/outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root`. On the saved root files, we check the plots of Data/MC using `python hhbbgg_Plotter.py`

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

- Step 3: STEP 3 — Build 2D Signal Workspaces
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



STEP 6 — Create Datacard
Example structure `datacard/comb_mass1000.txt` (simplified 3-category version):
```bash
imax 3  number of channels
jmax 2  number of backgrounds
kmax *  number of nuisance parameters
---------------------------------
shapes data_obs    ch0 data/data_obs_mass1000.root hist_data_ch0
shapes data_obs    ch1 data/data_obs_mass1000.root hist_data_ch1
shapes data_obs    ch2 data/data_obs_mass1000.root hist_data_ch2
shapes sig_NMSSM   ch0 Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c0.root wsig2d_NMSSM_2018_c0:sig_NMSSM_c0
shapes sig_NMSSM   ch1 Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c1.root wsig2d_NMSSM_2018_c1:sig_NMSSM_c1
shapes sig_NMSSM   ch2 Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c2.root wsig2d_NMSSM_2018_c2:sig_NMSSM_c2
shapes bkg         ch0 Background/WS_bkg_2D/2018/ws_bkg_2018_c0.root ws_bkg_2018_c0:pdf_bkg_c0
shapes bkg         ch1 Background/WS_bkg_2D/2018/ws_bkg_2018_c1.root ws_bkg_2018_c1:pdf_bkg_c1
shapes bkg         ch2 Background/WS_bkg_2D/2018/ws_bkg_2018_c2.root ws_bkg_2018_c2:pdf_bkg_c2
---------------------------------
bin          ch0     ch1     ch2
observation  -1      -1      -1
---------------------------------
bin          ch0   ch0   ch0   ch1   ch1   ch1   ch2   ch2   ch2
process      sig_NMSSM bkg   bkg2   sig_NMSSM bkg   bkg2   sig_NMSSM bkg   bkg2
process      0     1     2     0     1     2     0     1     2
rate         1     1     1     1     1     1     1     1     1
---------------------------------
lumi lnN 1.025 1.025 1.025 1.025 1.025 1.025 1.025 1.025 1.025
```
(Adjust channels or remove ch2 if you’re missing that workspace.)

- STEP 7 — Convert Datacard → Workspace
```bash
text2workspace.py datacard/comb_mass1000.txt -o datacard/comb_mass1000.root
```

Produces:
`datacard/comb_mass1000.root`

- STEP 8 — Run Combine
```bash
combine -M AsymptoticLimits datacard/comb_mass1000.root -n _asymp
```

8a. Observed limit (no toys → less crash-prone)
```bash
combine -M AsymptoticLimits datacard/comb_mass1000.root -m 1000 -n mass1000_obs --verbose 2
```

Output:
`higgsCombine_mass1000_obs.AsymptoticLimits.mH1000.root`


8b. Expected (Asimov, if stable)
```bash
combine -M AsymptoticLimits datacard/comb_mass1000.root -m 1000 -n mass1000_exp -t -1 --expectSignal 0 --verbose 2
```
Output:
`higgsCombine_mass1000_exp.AsymptoticLimits.mH1000.root`

If this segfaults → one of your PDFs can’t generate toys.
→ Fix by checking ranges or missing WS (see below).


STEP 9 — Inspect Combine Results
```bash
python3 - <<'PY'
import ROOT, glob
files = glob.glob("higgsCombine_mass1000_*.AsymptoticLimits*.root")
if not files:
    print("No combine outputs found.")
else:
    for fn in files:
        print("\n>>>", fn)
        f = ROOT.TFile.Open(fn)
        t = f.Get("limit")
        for i, e in enumerate(t):
            print(f"{i}: limit = {e.limit:.5f}")
        f.Close()
PY
```

- Optional sanity checks
Check all WS exist:
```bash
for f in Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c{0,1,2}.root Background/WS_bkg_2D/2018/ws_bkg_2018_c{0,1,2}.root data/data_obs_mass1000.root; do
  [ -f "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

Inspect combined workspace:
```bash
python3 - <<'PY'
import ROOT
f = ROOT.TFile.Open("datacard/comb_mass1000.root")
f.ls()
ws = f.Get("w")
if ws: ws.Print("v")
f.Close()
PY
```

- STEP 10 — Troubleshooting Summary
| Issue                          | Likely Fix                                                            |
| ------------------------------ | --------------------------------------------------------------------- |
| `MISSING FILE` error           | Copy or regenerate the missing signal/background WS                   |
| `Channel ... empty background` | Data bin filled, bkg empty — harmless if only warning                 |
| `Segfault during combine`      | Run **observed** only (no `-t -1`), check WS PDF validity             |
| `Invalid literal in datacard`  | Check formatting — same number of columns in `bin`, `process`, `rate` |
| `RooAbsPdf generate crash`     | Fix WS variable ranges or small sigma values                          |

