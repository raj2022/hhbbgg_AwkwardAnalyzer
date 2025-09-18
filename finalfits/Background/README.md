# Background Modelling

Please see the [original documentation](https://github.com/cms-analysis/flashggFinalFit/tree/higgsdnafinalfit/Background) for the `Background` package. This package is a fork of the original `Background` package with some additional functionality. Some of the original documentation is still relevant and is included below. Experienced users may wish to skip to the [Running the tool](#running-the-tool) section, although there are several important changes to the input arguments.


This is where the background model is determined. This is the only package yet to be pythonised for the new Final Fits. We have introduced a new mode for running the fTest `fTestParallel` which creates a separate job per analysis category. These jobs can then be submitted in parallel, greatly speeding up the process!

The S+B plotting functionalities in this package have for now been depleted. You can produce the traditional blinded signal + bkg model plots using the `../Plots/makeSplusBModelPlot.py` script (see the `Plots` package for mode details). The `fTestParallel` will by default still produce the standard multipdf style plots.

The new `fTestParallel` method for running the background scripts is only configured for use on true data. Please refer to an older version of Final Fits to run the background modelling on pseudo-data, generated using the background simulation samples. This functionality will be added ASAP!

## Setup

The background modelling package still needs to be built with it's own makefiles. Please note that there will be verbose warnings from BOOST etc, which can be ignored. So long as the `make` commands finish without error, then the compilation happened fine.:

```
cd ${CMSSW_BASE}/src/flashggFinalFit/Background
cmsenv
make
```

If it fails, first try `make clean` and then `make` again. 

## Background f-Test

Takes the output of flashgg (`allData.root`) and outputs a `RooMultiPdf` for each analysis category. The `RooMultiPdf` contains a large collection of background model pdfs from different functions families including exponential functions. Bernstein polynomials, Laurent series and power law functions. In the final fit, the choice of background model pdf from this collection is treated as an additional discrete nuisance parameter (discrete profiling method). This fTest determine which functions are included in the `RooMultiPdf` by requiring some (weak) goodness-of-fit constaint. Note, the normalisation and shape parameters of the background functions are still free to float in the final fit.

The new functionality performs the fTest in parallel for each analysis category:
```bash
python3 RunBackgroundScripts.py --inputConfig config_test.py --mode fTestParallel (--printOnly)
```

Similar to the signal scripts the options are steered using an input config file e.g.:
```python
_year = "2022+2023"
_cwd = "path/to/flashggFinalFit"

backgroundScriptCfg = {
    # Setup
    "inputWS": f"{_cwd}/Trees2WS/inputs/bbgg/ws_TTH/",
    "procs": "TTH",  # for resonant (use PROCNAME naming convention)
    'cats':'auto', # auto: automatically inferred from input ws
    "catOffset": 0,  # add offset to category numbers (useful for categories from different allData.root files)
    "analysis": 'bbgg',
    "ext": "tth",
    "year": "%s" % _year, # Use specific year for datacard; 'combined' for merging all years in category (for plots)
    "massPoints": "125",  # e.g. "120,125,130"

    # Photon shape systematics
    "scales": "Scale", # separate nuisance per year
    "scalesCorr": "", # correlated across years
    "scalesGlobal": "", # affect all processes equally, correlated across years
    "smears": "Smearing", # separate nuisance per year

    # Job submission options
    "batch": 'local',  # [condor,SGE,IC,local]
    "queue": "espresso",  # for condor e.g. microcentury

    # Manually set variable names
    "weightName": 'weight_tot',
}
```

The output is a ROOT file containing the `RooMultiPdf`'s for each analysis category in `outdir_{ext}`. These are your background models (which must be copied across to the `Combine` directory when you get to the final fits step). In addition the standard fTest plots are produced in the `outdir_{ext}/bkgfTest-Data` directory, where the numbering matches the `catOffset` for each category (see the submission scripts).

## Running the tool

The `RunBackgroundScripts.py` script is used to submit the background modelling jobs. The script is configured using an input config file with the expected name `config_{proc}.py` (e.g. `config_tth.py` for ttH). For every resonant background type, several commands must be executed. In contrast, the non-resonant background requires only one command to run. 

### Resonant Background

The complete workflow contains four resonant background processes: ttH, ggH, VBF, and VH. The steps outlined below must be repeated for every resonant background process.

#### fTest
First, run the **fTest** to determine the optimal background model for each category. For ttH, the command may look like this:
```bash
python3 RunBackgroundScripts.py \
--inputConfig config_tth.py \
--mode fTestParallel \
--fitType 2D \
--resonant \
--modeOpts="--doPlots --threshold 5" \
--logLevel INFO
```

The `--modeOpts` argument is used to pass additional options to the `fTestParallel` mode. The `--doPlots` option will produce the standard fTest plots. The `--threshold` option is used to set the threshold for the fTest. The `--skipWV` option is used to skip the "wrong vertex" categorization, which we wish to exclude from the fitting at the moment. 

Other options in the `--modeOpts` argument include:
- `--mggLow`, `--mggHigh`: set the range of the $m_{\gamma\gamma}$ fit
- `--mjjLow`, `--mjjHigh`: set the range of the $m_{jj}$ fit
- `--binWidthMgg`, `--binWidthMjj`: set the bin width for the $m_{\gamma\gamma}$ and $m_{jj}$ fits (replaces `--nBins`)

For 1D fits, use the respective bin width and range options in `modeOpts`. For 2D fits, both `mgg` and `mjj` bin widths and ranges may be set simultaneously. The idea is to avoid running 1D fits separately then manually collecting them into a 2D workspace when custom binning is required.


The `--fitType` option is used to set the observable we are fitting. Setting it to `mgg` will fit the $m_{\gamma\gamma}$ distribution, while setting it to `mjj` will fit the $m_{jj}$ distribution. Setting it to `2D` will fit both observables separately.

**Note:** The `--nBins` option has been superceeded by the `--m{gg,jj}BinWidth` options. Bin number is computed as `nBins = floor((high - low) / binWidth)` as to ensure integer bin numbers. If the fit range is not divisible by the bin width, the actual bin width will be slightly larger than the requested bin width. 

#### Photon Shape Systematics

The photon shape systematics calculation is initiated with the `RunBackgroundScripts.py` controller script. At this moment, we exclude this step from the background modelling on account of a lack of systematics in the Parquet files. This documentation will be updated as soon as these systematics become available. 

#### Resonant Background Fit

The final step is to run the **resonant background fit**. For ttH, the command may look like this:
```bash
python3 RunBackgroundScripts.py \
--inputConfig config_tth.py \
--mode resonantFit \
--modeOpts="--doPlots --skipSystematics --replacementThreshold 0 --template NGauss" \
--resonant \
--fitType 2D \
--groupBackgroundFitJobsByCat \
--logLevel INFO
```

If your Parquet file does not contain systematic-varied trees, you should keep the `--skipSystematics` option. The `--replacementThreshold` option is used to set the threshold for the replacement of the background model. The code has been modified to interpret a zero value as "no replacement" rather than the hardcoded default value.

The `--fitType` option (`mgg`, `mjj`, or `2D`) is used to set the observable we are fitting. Setting it to `2D` will fit both observables separately.

Not listed in the above command is the `--noClean` option. This option is used to skip the cleaning of the output directory from plots and fitted workspaces. This is useful if you are want to keep the output of the previous run for whatever reason, such as when chaining multiple 1D fits together. 

The `--template` option in the `modeOpts` argument is used to set the template for the `mjj` model. It will not control the `mgg` model since it only uses an NGaussian template. The options for `--template` are:
- `NGauss` (stable)
- `Exp+NGauss`
- `Exp+Gauss`
- `Exp` (stable)
- `Voigtian`
- `NVoigtian`
- `NBernstein` (stable)
- `Gauss+NBernstein`
- `Novosibirsk`
- `GaussTimesExp` (stable)
- `DCB` (stable)
- `DCB+Gauss` (stable)
- `DCB+Voigtian`
Please note that most of these options are experimental and may not work as expected. 

Other options in the `--modeOpts` argument include:
- `--mggLow`, `--mggHigh`: set the range of the $m_{\gamma\gamma}$ fit
- `--mjjLow`, `--mjjHigh`: set the range of the $m_{jj}$ fit
- `--mggBinWidth`, `--mjjBinWidth`: set the bin width for the $m_{\gamma\gamma}$ and $m_{jj}$ fits (replaces `--nBins`)
- `--doPlots`: produce the standard plots
- `--skipSystematics`: skip the photon shape systematics
- `--replacementThreshold`: set the threshold for the replacement of the background model
- `--template`: set the template for the `mjj` model (see above for options)
- `--minimizerMethod`: Scipy minimizer method, e.g. "TNC," "BFGS," "Powell," "Nelder-Mead," etc.

**Note:** The `--nBins` option has been superceeded by the `--m{gg,jj}BinWidth` options. Bin number is computed as `nBins = floor((high - low) / binWidth)` as to ensure integer bin numbers. If the fit range is not divisible by the bin width, the actual bin width will be slightly larger than the requested bin width. 

You can use `--mggName` and `--mjjName` to set the names of the $m_{\gamma\gamma}$ and $m_{jj}$ variables, respectively. The default names are `mass` for $m_{\gamma\gamma}$ and `Res_mjj_regressed` for $m_{jj}$. 

## Resonant Background Packager

Once all resonant background models have been created, run the **resonant background packager** to combine the resonant background models into a single workspace. The command may look like this:
```bash
python3 RunPackager.py \
--cats cat0,cat1,cat2 \
--exts tth,vh,vbf,ggh \
--mergeYears \
--batch local \
--massPoints 125 \
--logLevel INFO
```

The example above is for a single mass point (125 GeV) and three categories (cat0, cat1, cat2). 

### Non-Resonant Background

Independent of the resonant background fitting, the non-resonant background fitting must be performed. Since we build the non-resonant background model by fitting the $m_{\gamma\gamma}$ data sidebands, there is only one step to this process.

You may find it useful to rebuild the non-resonant background model, especially when moving to a new system or version of the code. 
```bash
make clean && make -j 8
```

The non-resonant background model is built using the `RunBackgroundScripts.py` script. The command may look like this:
```bash
python3 RunBackgroundScripts.py \
--inputConfig config_bbgg.py \
--mode fTestParallel \
--fitType 2D \
--modeOpts="--mggLow 100 --mggHigh 180 --mjjLow 80 --mjjHigh 190 --mggBinWidth 2 --mjjBinWidth 10" \
--logLevel INFO
```

The `--fitType` option (`mgg`, `mjj`, or `2D`) is used to set the observable we are fitting. Setting it to `2D` will fit both `mgg` and `mjj` separately.

The `--modeOpts` argument is used to pass additional options to the `fTestParallel` mode. The `--mggLow`, `--mggHigh`, `--mjjLow`, and `--mjjHigh` options are used to set the range of the $m_{\gamma\gamma}$ and $m_{jj}$ fits. The `--mggBinWidth` and `--mjjBinWidth` options are used to set the bin width for the $m_{\gamma\gamma}$ and $m_{jj}$ fits.

**Note:** The `--nBins` option has been superceeded by the `--m{gg,jj}BinWidth` options. Bin number is computed as `nBins = floor((high - low) / binWidth)` as to ensure integer bin numbers. If the fit range is not divisible by the bin width, the actual bin width will be slightly larger than the requested bin width.

Diphoton and dijet mass variable names may be set using the `--mggName` and `--mjjName` options, respectively. The default names are `mass` for $m_{\gamma\gamma}$ and `Res_mjj_regressed` for $m_{jj}$. If you have different variable names in your workspace, you can specify them as follows:
```bash
python3 RunBackgroundScripts.py \
--inputConfig config_bbgg.py \
--mode fTestParallel \
--fitType 2D \
--mggName my_mgg_variable \
--mjjName my_mjj_variable
```


### Plotting

It is useful to inspect the plots produced by the background modelling before moving on. Especially when categories have low statistics, fits can fail and may produce unexpectedly poor final limits. In such cases of low-statistics categories failing to converge, it is recommended to *explore* excluding that particular category of that process if the replacement map is not in use. That being said, consider excluding the category of a process as a last resort and a temporary solution.

After building all signal and background models, you can plot all the models together with the following script:
```bash
pushd ../Plots
  for cat in {cat0,cat1,cat2}; do python3 makeMultipdfPlot.py --inputWSFile ../Background/outdir_bbgg/CMS-HGG_multipdf_${cat}.root --cat ${cat} --ext bbgg --mass 125.38 --inputSignalWSFile ../Signal/outdir_bbgg_2022postEE/signalFit/output/CMS-HGG_sigfit_bbgg_al2022_GGHH_all2022_${cat}.root; done
popd
```

Modify the script to fit your needs (i.e. year, category, etc.).

### To do list

 * Pseudodata functionality

 * As mentioned above you can now plot the blinded S+B model plots from the compiled datacard using `../Plots/makeSplusBModelPlot.py` script. We should add a dedicated plotting script in the `Background` package ASAP.

 * The output background models have a prefit normalization which matches the total number of events in the category `RooDataSets`. For categories with high S/B, the prefit normalization (which includes S) will be over-estimating the size of the background. When you then run the expected results (which throws an asimov toy from the pre-fit signal and background models) you will subsequently under-estimate the true sensitivity. This artifact only becomes noticable when dealing with categories with very high S/B, and importantly does NOT affect the observed results since the background model normalisation is floated in the final fit. For now, before running the expected scans you can run a S+B bestfit to data and subsequently throw the asimov toy from the postfit background model. At some point we should change the normalisation in the background modelling to interpolate from the sidebands only, rather than using the absolute event yield. 

 * Pythonize everything to make the code more accessible.

 * Add systematics-handling for Mjj resonant background model building. (see `resonantFinalModel.py`)
 
 * Update resonant background packager for 2D and mjj fits. (low importance)

 * Speed up plot archiver (spawn new process? multithread?)






## References:
1. https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit/-/tree/higgsdnafinalfit/Background?ref_type=heads
