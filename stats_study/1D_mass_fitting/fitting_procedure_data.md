# Fitting procedure with data
On the fitting with the data instead of Asimov data, 

The data fitted as rooworkspace after filling the histogram in `ROOT` has been described in here, 
https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/parquest_v3/stats_study/notebook_fitting/data_fit.ipynb

further, we created this datacard, https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/parquest_v3/stats_study/1D_mass_fitting/Datacards/datacard_data.txt
```bash
imax 1  number of channels
jmax 5  number of backgrounds
kmax *  number of nuisance parameters (systematics)

shapes * * workspace.root w:$PROCESS
shapes data_obs * fitting_results_data.root w:data_obs

bin        bin1
observation -1


bin             bin1        bin1        bin1        bin1        bin1        bin1
process         pdf_GGJets  pdf_GJetPt40  pdf_GJetPt20To40  pdf_VBFHToGG  pdf_VHToGG  pdf_ttHToGG
process         0        1         2         3         4         5
rate            100      50        30        10        5         3


lumi      lnN    1.025      1.025     1.025     1.025     1.025     1.025
bkg_norm  lnN    1.10      1.15      1.20      1.10      1.15      1.20
```
we included the `fitting_results_data.root` as the observed data.

The file ran using,
```bash
text2workspace.py datacard.txt -o workspace.root
```

We further run the statistical analysis using combine. 

* For fitting diagonistics
```bash
combine -M FitDiagnostics workspace.root \
  --saveShapes --saveWithUncertainties --saveNormalizations \
  -n _fit_realdata
```
This is performing a maximum likelihood fit. on the output diagonistics, we save post-fit shapes and uncertainties.

The goodness of fit can be found using:
```bash

combine -M GoodnessOfFit workspace.root \
  --algo=saturated -n _gof
```
The significance can be checked as:
```bash
combine -M Significance workspace.root -n _signif
```
On the limit setting, we have
``` bash
combine -M AsymptoticLimits workspace.root -n _limit
```
## Problem/issues
The output coming as follow:
```bash
(base) [sraj@lxplus988 datacard]$ combine -M AsymptoticLimits workspace.root -n _limit
 <<< Combine >>> 
 <<< v10.2.1 >>>
>>> Random number generator seed is 123456
>>> Method used is AsymptoticLimits
Caught exception ERROR: channel bin1 factorized to zero.
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ ls
combine_logger.out                                   higgsCombine_gof.GoodnessOfFit.mH120.root
datacard.txt                                         higgsCombine_limit.AsymptoticLimits.mH120.root
fitDiagnostics_fit_realdata.root                     higgsCombine_signif.Significance.mH120.root
fitting_results_data.root                            workspace.root
higgsCombine_fit_realdata.FitDiagnostics.mH120.root
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ 
(base) [sraj@lxplus988 datacard]$ combine -M AsymptoticLimits -d workspace.root
 <<< Combine >>> 
 <<< v10.2.1 >>>
>>> Random number generator seed is 123456
>>> Method used is AsymptoticLimits
Caught exception ERROR: channel bin1 factorized to zero.
(base) [sraj@lxplus988 datacard]$ 
```
Combine sees all expected events (signal + background) are zero in ``bin1`, so it cannot perform a meaningful limit calculation.

According to chatGPT, this could be reason behind it:
Histograms exist, but they have zero or near-zero content, so normalization to expected rates (like 100, 50, 30) gets zeroed out.


`RooHistPdf::shapeBkg_pdf_ttHToGG_bin1 = 9.17991e-05` This value is extremely small. Others are similar (~1e-4), which implies your RooDataHists may have:
Sparse or flat shapes
Misaligned binning compared to the expected observable




