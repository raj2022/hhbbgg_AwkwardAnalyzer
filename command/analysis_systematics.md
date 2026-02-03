# Analysis Sytematics
- setup env
```bash
cd slides_fitting/CMSSW_14_1_0_pre4/src
cmsenv
mamba activate hhbbgg-awk   # Do not change the order of cmsenv and env activation. 
```

After having nominal processing throught the anlyzer, do not touch it. 


- To run on the complete dataset for three years:
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

On the merged folder after HiggsDNA and systematics: run over the folder 
# To Run the systematics
```bash
python make_templates.py \
  --year 2022 \
  /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/
```
it will save the output at:
```bash
outputfiles/2022_All/systematics/histograms.root
```
Directory Structure: 
```bash
outputfiles/
└── 2022_postEE/
    ├── baseline/
    │   ├── hhbbgg_analyzer-v2-histograms.root
    │   └── hhbbgg_analyzer-v2-trees.root
    └── systematics/
        └── histograms.root

```

```bash
histograms.root
 ├── NMSSM_X300_Y100/
 │    ├── selection/
 │    │    ├── bbgg_mass
 │    │    ├── bbgg_mass__jec_syst_Total_up
 │    │    └── ...
 │    └── preselection/
 ├── NMSSM_X350_Y150/
 │    └── ...
 └── ...
```

- Verify ROOT file content 
```bash
root -l outputfiles/2022_All/systematics/histograms.root
_file0->ls();
_file0->GetDirectory("NMSSM_X1000_Y125")->ls();
_file0->GetDirectory("NMSSM_X1000_Y125/preselection")->ls();

```


for each NMSSM point you now have:
* nominal
* JEC up/down
* JER up/down
* photon scale up/down
* photon smearing up/down
That is full object-level systematics. 

- Histogram-based combine
 using `shapes * * histograms.root $PROCESS $PROCESS__$SYSTEMATIC`


FINAL SYSTEMATICS MODEL
* mgg (sum of Gaussians)
* ScaleEE2G → mean only
* Smearing2G → width only
* mjj (DoubleCB-like, but Gaussian mixture here)
* JEC → mean + width
* JER → width only

Object-level systematic templates are produced only to extract kappas for the parametric signal model; they are not passed to Combine as shape variations.

Abstract kappas from the root file
```bash
python signal/extract_signal_kappas.py
```
saved at output/systematics/signal_kappas.json

If you ever want a per-mass-point file:
```bash
python3 Signal/extract_signal_kappas.py \
  --mX 1000 \
  --mY 125 \
  --outfile outputs/systematics/signal_kappas.json
```

for systematics:

```bash
python3 Signal/make_signal_ws_2D_from_jsons_syst.py \
  --mgg_json outputs/signal_fits/signal_shape_params.json \
  --mjj_json outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json \
  --syst_json outputs/systematics/signal_kappas.json \
  --mass 1000 \
  --year 2018 \
  --proc NMSSM \
  --outdir Signal/SignalWS_2D \
  --mgg 115,135 \
  --mjj 50,200 
```

#### Must do checks
```bash
root -l ws_signal2D_NMSSM_2018_c0.root
```
```bash
w->Print("v");

```

You must see:
```bash
CMS_scale_ee
CMS_smear_ee
CMS_jec
CMS_jer
```
and formula vars like:
```bash
mgg_mu_syst_c0_g0
mjj_sig_syst_c0_g0
```

- Next Step:

*   Datacard
```bash
imax 2
jmax 1
kmax *

# shapes: ch0
shapes sig    ch0  Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c0.root wsig2d_NMSSM_2018_c0:sig_NMSSM_c0
shapes bkg    ch0  Background/WS_bkg_2D/2018/ws_bkg_2018_c0.root ws_bkg_2018_c0:pdf_bkg_c0
shapes data_obs ch0  data/data_obs_mass1000_rdh.root hist_data_ch0

# shapes: ch1
shapes sig    ch1  Signal/SignalWS_2D/2018/ws_signal2D_NMSSM_2018_c1.root wsig2d_NMSSM_2018_c1:sig_NMSSM_c1
shapes bkg    ch1  Background/WS_bkg_2D/2018/ws_bkg_2018_c1.root ws_bkg_2018_c1:pdf_bkg_c1
shapes data_obs ch1  data/data_obs_mass1000_rdh.root hist_data_ch1

bin          ch0    ch1
observation  -1     -1

bin             ch0   ch0   ch1   ch1
process         sig   bkg   sig   bkg
process         0     1     0     1
rate            1.0   1.0   1.0   1.0

# ---------------------------------
# Signal shape systematics (2D parametric)
# ---------------------------------
# CMS_scale_ee   shape   1   -   1   -
# CMS_smear_ee  shape   1   -   1   -
# CMS_jec       shape   1   -   1   -
# CMS_jer       shape   1   -   1   -

# ---------------------------------
# Parametric signal shape nuisances
# ---------------------------------
CMS_scale_ee  param  0  1
CMS_smear_ee  param  0  1
CMS_jec       param  0  1
CMS_jer       param  0  1

# ---------------------------------
# Normalization uncertainty
# ---------------------------------
lumi lnN 1.025 - 1.025 -

```

Inside CMSSW 
```bash
cmsenv
```
from `src` directory
- Convert datacard to RooWorkspace
```bash
text2workspace.py datacard/400/comb_mass_syst_400.txt -o datacard/400/comb_mass_syst_400.root
``` 

* Parses the signal and background RooWorkspaces
* Registers all nuisance parameters
* Must be rerun after any datacard change


and validate nuisances are seen by combine
```bash
combine -M FitDiagnostics datacard/400/comb_mass_syst_400.root \
  -t -1 --expectSignal 1 --saveShapes
```
then 
```bash
root -l datacard/400/comb_mass_syst_400.root
```

```bash
w->Print("v");
```

```bash
fit_s->Print("v")
```
there should be:
```bash
CMS_scale_ee
CMS_smear_ee
CMS_jec
CMS_jer
```

- Basic model sanity check (nuisances visible)
Check that Combine can parse the model and see all parameters.

```bash
combine -M MultiDimFit \
  -d datacard/400/comb_mass_syst_400.root \
  --algo none \
  -n _checkModel
```

* No scans or profiling
* Confirms model builds successfully
* `r` floating freely (may hit boundary — expected at this stage)

- Nuisance wiring check (floating POI)
Verify that parametric systematics are connected and do not crash the likelihood.
```bash
combine -M MultiDimFit \
  -d datacard/400/comb_mass_syst_400.root \
  --algo none \
  --setParameterRanges r=0,5 \
  -n _checkNuis
```
* Combine runs without underflow or covariance errors
* `r` may hit the boundary (normal before normalization is fixed)

- Background-only fit validation
Ensure the analytic background model is well-behaved and positive-definite.
```bash
combine -M FitDiagnostics \
  -d datacard/400/comb_mass_syst_400.root \
  --expectSignal 0 \
  -n _fd_bonly

```
* This is mandatory
* Must converge before any further statistical inference
* Failures here indicate a background PDF issue

- Frozen-POI nuisance validation (no robustFit)
Validate that nuisance parameters are active and constrained when the signal strength is fixed.
```bash
combine -M FitDiagnostics \
  -d datacard/400/comb_mass_syst_400.root \
  --setParameters r=1 \
  --freezeParameters r \
  --saveShapes \
  -n _fd_r1
```
* Do not use `--robustFit` at this stage
* Check nuisance values and uncertainties in fit_s

- Likelihood scan of an individual nuisance
Demonstrate that a given nuisance parameter produces a smooth likelihood profile.
Example (JEC)

```bash
combine -M MultiDimFit \
  -d datacard/400/comb_mass_syst_400.root \
  --redefineSignalPOIs CMS_jec \
  --freezeParameters r \
  --setParameters r=1 \
  --algo grid --points 41 \
  -n _scanCMSjec
```
* Should produce a parabolic likelihood curve
* Confirms Up/Down propagation via parametric modeling

- Expected limits (final physics result)
Compute expected 95% CL upper limits under the background-only hypothesis.

```bash
combine -M AsymptoticLimits \
  -d datacard/400/comb_mass_syst_400.root \
  --run blind \
  -n _exp
```

- Signal-plus-background FitDiagnostics
Inspect post-fit shapes and correlations once normalization is fixed.
```bash
combine -M AsymptoticLimits \
  -d datacard/400/comb_mass_syst_400.root \
  --run blind \
  -n _exp

```
* Run only after background and signal models are finalized

* Produces pre-fit and post-fit shapes



```bash
combine -M FitDiagnostics \
  -d datacard/400/comb_mass_syst_400.root \
  --setParameters r=1 \
  --freezeParameters r \
  --robustFit 1
```


- Summamry
```bash
Systematic uncertainties are included in the datacard as parametric nuisance parameters. Template-based shape systematics are not used; instead, systematic effects are encoded directly in the parametric signal model and constrained via Gaussian priors.

Here is the  conceptual summary:

• Object-level systematics (JEC, JER, photon scale/smear) are produced at the histogram level.
• These histograms are used only to extract fractional variations (κ values).
• The signal model is fully parametric and implemented in a 2D RooWorkspace (mgg × mjj).
• Systematic uncertainties are encoded as Gaussian-constrained nuisance parameters inside the signal PDF.
• No Up/Down shape templates are used in Combine.
• The datacard declares only param nuisances, and Combine reads their effect directly from the signal workspace.

```





### Total Analysis overview
```bash
Parquet → Analyzer → ROOT trees
        → category definition
        → 1D signal fits (mgg)
        → 1D signal fits (mjj)
        → 2D signal WS
        → background WS
        → data histograms
        → datacard
        → text2workspace
        → combine
```


## Summary:

```bash
python make_templates.py \
  --year 2022 \
  /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2022_postEE/merged/NMSSM_X300_Y100/

python3 Signal/extract_signal_kappas.py \
  --mX 1000 \
  --mY 125 \
  --outfile outputs/systematics/signal_kappas.json


  python3 Signal/make_signal_ws_2D_from_jsons_syst.py \
  --mgg_json outputs/signal_fits/signal_shape_params.json \
  --mjj_json outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json \
  --syst_json outputs/systematics/signal_kappas.json \
  --mass 1000 \
  --year 2018 \
  --proc NMSSM \
  --outdir Signal/SignalWS_2D \
  --mgg 115,135 \
  --mjj 50,200 

text2workspace.py datacard/400/comb_mass_syst_400.txt -o datacard/400/comb_mass_syst_400.root


combine -M FitDiagnostics datacard/400/comb_mass_syst_400.root \
  -t -1 --expectSignal 1 --saveShapes

combine -M AsymptoticLimits \
  -d datacard/400/comb_mass_syst_400.root \
  --run blind \
  -n _exp


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