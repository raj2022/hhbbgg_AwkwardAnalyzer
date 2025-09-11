# Signal modelling

Please see the [original documentation](https://github.com/cms-analysis/flashggFinalFit/tree/higgsdnafinalfit/Signal) for the `Signal` package. This package is a fork of the original `Signal` package with some additional functionality. Some of the original documentation is still relevant and is included below. 

There are a number of steps to perform when constructing the signal model (described below). It is recommended to construct a signal model for each year separately. This allows to keep track of both the year-dependent resolution effects and the year-dependent systematic uncertainties. Each step up to the packaging is ran using the `RunSignalScripts.py` script, which takes as input a config file e.g.:

```python
# Config file: options for signal fitting

_year = '2022+2023'

signalScriptCfg = {
  # Setup
  'inputWSDir': 'path/to/Trees2WS/inputs/bbgg/ws_GGHH/',
  'procs':'auto', # if auto: inferred automatically from filenames
  'cats': 'auto',
  'ext':'bbgg_%s'%_year,
  'analysis':'bbgg', # To specify which replacement dataset mapping (defined in ./python/replacementMap.py)
  'year':'%s'%_year, # Use 'combined' if merging all years: not recommended
  'massPoints':'125', #'120,125,130',

  #Photon shape systematics  
  'scales':'Scale', # separate nuisance per year
  'scalesCorr':'', # correlated across years
  'scalesGlobal':'', # affect all processes equally, correlated across years
  'smears':'Smearing', # separate nuisance per year

  # Job submission options
  'batch':'local', # ['condor','SGE','IC','local']
  'queue':'espresso',

  # Manually set variable names
  'weight_name': 'weight_tot',
}
```
The basic command for using `RunSignalScripts.py` is the following:
```bash
python3 RunSignalScripts.py --inputConfig {config_file}.py --mode {mode} --modeOpts="{list of options for specific mode}" --jobOpts="{list of options for job submission}"
```
To simply print the job scripts without submitting then add the option: `--printOnly`. You can then go to the respective `outdir_{ext}/{mode}/jobs` directory to run the individual scripts locally (great for testing and debugging!)

In this new final fits package we have introduced a number of additional options which were not previously available. Firstly, you can now run the signal model for a single mass point: the polynominal defining the mass dependence on the fit parameters is set to a constant. Additionally, you can skip the splitting into the right vertex (RV) and wrong vertex (WV) scenarios (in fact the fraction of WV events for anything but ggH 0J is ~0, so the general rule of thumb is that it is okay to skip the splitting). In the new package the minimizer has been replaced with `scipy.minimize`, which means we no longer require the specialised ROOT class for the simultaneous signal fit for different mass points. For developers of this package you can find the Python class which performs the signal fit in `tools.simultaneousFit`. A simple application of this is shown in `simpleFit.py`. The construction of the final signal model is done using the Python class in `tools.finalModel.py`


## Running the tool 

### Signal F-Test

Test for determining the optimal number of gaussians to use in signal model. If you want to use the Double Crystal Ball (DCB) + Gaussian function for the models then you can skip the F-test.

```bash
python3 RunSignalScripts.py \
--inputConfig config_bbgg.py \
--mode fTest \
--modeOpts="--doPlots" \
--logLevel INFO
```

This will create a separate job per analysis category, which outputs a json file (`./outdir_{ext}/fTest/json`) specifying the optimal number of Gaussians for each signal process for both the RV (right-vertex) and WV (wrong-vertex) scenarios. The optimal number of gaussians is chosen as the number which minimises the reduced chi2.

In general, we only need to know the shape for the signal processes which have a sizeable contribution in a given category. By default the fTest script will only calculate the optimal number of Gaussians for the 5 signal processes in a category with the highest sum of weights. The other signal processes are set to (nRV,nWV)=(1,1). To toggle this number add the option `--nProcsToFTest X` into the `--modeOpts` string, where X will replace 5. To determine the optimum for all signal processes then set X = -1.

To produce the fTest plots then add `--doPlots` to the `--modeOpts` string. For other options when running `fTest`, see `./scripts/fTest`

#### 2D Fitting F-Test

There are two new options required for the 2D fTest: `--fitType` and `--template`.

When running the fTest, the default behavior is to fit $m_{\gamma\gamma}$, which has a default variable name `mass`. The `--fitType` option controls whether `RunSignalScripts.py` runs fTest on $m_{\gamma\gamma}$, $m_{jj}$, or both (2D). The allowed values for `--fitType` are `mgg`, `mjj`, and `2D`. The default is `mgg`. 

The `--template` option is required when running the 2D fTest. The `--template` option specifies the template function for the `mjj` fit. You do not use `--template` to control the `mgg` fit. The allowed values for `--template` are:

- `Gauss+NBernstein`: 1 Gaussian + Nth order Bernstein polynomial. Default. F-Test will determine the optimal value of N.
- `Exp+NGauss`: Exponential + N Gaussians. F-Test will determine the optimal number of Gaussians.
- `NBernstein`: Nth order Bernstein polynomial. F-Test will determine the optimal value of N.
- `Gauss+NBernstein`: 1 Gaussian + Nth order Bernstein polynomial. F-Test will determine the optimal value of N.
- `NGauss`: N Gaussians. F-Test will determine the optimal number of Gaussians. This is what we did for the $m_{\gamma\gamma}$ fits!
- `Exp+Gauss`: Exponential + Single Gaussian. F-Test is not relevant for this template, but it will exit gracefully, anticipating future scripts that test all templates.
- `Exp`: Exponential function. F-Test is not relevant for this template, but it will exit gracefully, anticipating future scripts that test all templates.

Let's look at a couple examples:

```bash
python3 RunSignalScripts.py \
--inputConfig config_bbgg.py \
--mode fTest \
--fitType mjj \
--modeOpts="--doPlots --template Exp+NGauss --nGaussMax 6" \
--logLevel INFO
```

The command above will run the fTest on only the $m_{jj}$ distribution using the `Exp+NGauss` template. The fTest will determine the optimal number of Gaussians to use in the fit. The `--doPlots` option will produce plots of the fits. By default, Bernsteins and Gaussians are tested from order 1 to order 5. The maximum for Bernsteins and Gaussians is controled by the `--nBernMax` and `--nGaussMax` options. The command above instructs FinalFit to try six different PDFs: An exponential plus 1 Gaussian, an exponential plus 2 Gaussians, ...3, ...4, ...5, and an exponential plus 6 Gaussians. Notice that we must specify these options in the `--modeOpts` string.

```bash
python3 RunSignalScripts.py \
--inputConfig config_bbgg.py \
--mode fTest \
--fitType 2D \
--modeOpts="--doPlots" \
```

Notice we did not specify the template in the command above. Consequently, the script will use the default template, `Gauss+NBernstein`, for the $m_{jj}$ fits. The fTest will determine the optimal number of Gaussians to use in the fit. The `--doPlots` option will produce plots of the fits.

Additional options in `modeOpts` are:
- `--mggLow`, `--mggHigh`: Set the range of the $m_{\gamma\gamma}$ fit. Default is 100-180 GeV.
- `--mjjLow`, `--mjjHigh`: Set the range of the $m_{jj}$ fit. Default is 80-190 GeV.
- `--mggBinWidth`, `--mjjBinWidth`: Set the bin width for the $m_{\gamma\gamma}$ and $m_{jj}$ fits. Default is 2 GeV.
- `--nGaussMax`: Set the maximum number of Gaussians to test. Default is 5. Only valid for fits with dynamic number of Gaussians.

**Note:** The `--nBins` option has been superceeded by the `--m{gg,jj}BinWidth` options. Bin number is computed as `nBins = floor((high - low) / binWidth)` as to ensure integer bin numbers. If the fit range is not divisible by the bin width, the actual bin width will be slightly larger than the requested bin width.

## Photon systematics

For calculating the effect of the photon systematics on the mean, width and rate of the signal spectrum.
```bash
python3 RunSignalScripts.py --inputConfig config_tutorial_2022preEE.py --mode calcPhotonSyst
```
This will again create a separate job per category, where the output is a pandas dataframe stored as a `.pkl` file. The dataframe contains the constants which describe how the systematics (specified in the `config` file) affect the mean, sigma and rate of each signal process. The final model construction will lift these constants directly from the `.pkl` files (replaced the monolithic `.dat` files in the old Final Fits).

If you do not wish to account for the photon systematics then this step can be skipped completely. Since we do not have access to Parquet files with the photon systematics, we skip this step temporarily. Documentation for running the photon systematics in our analysis will be added once they become available. 

For other options when running `calcPhotonSyst`, see `./scripts/calcPhotonSyst` and add whatever you need to the `--modeOpts` string.

## Final model construction

We may now run the actual fit:

```bash
python3 RunSignalScripts.py \
--inputConfig config_bbgg.py \
--mode signalFit \
--modeOpts="--doPlots --skipSystematics --replacementThreshold 0" \
--groupSignalFitJobsByCat \
--logLevel INFO
```

The `groupSignalFitJobsByCat` option will create a submission script per category. If removed, the default is to have a single script per process x category (which can be a very large number!). The output is a separate ROOT file for each process x category containing the signal fit workspace.

There are many different options for running the `signalFit` which can be added to the `--modeOpts` string. These are defined in `./scripts/signalFit`:

 * `--doPlots`: plot interpolation of signal model, the various normalisation inputs and the shape pdf split into its individual components.
 * `--useDiagonalProcForShape`: use the shape of the diagonal process in the category (requires running the `getDiagProc` mode first).
 * `--beamspotWidthMC X` and `--beamspotWidthData Y`: change the beamspot width values for MC and data [cm] for when reweighting the MC to match the data beamspot distribution. You can skip this reweighting using the option `--skipBeamspotReweigh'. Default is set to the 2022 (postEE) values.
 * `--useDCB`: use DCB + 1 Gaussian as pdf instead of N Gaussians.
 * `--doVoigtian`: replace all Gaussians in the signal model with Voigtians (used for Higgs total width studies).
 * `--skipVertexScenarioSplit`: skip splitting the pdf into the RV and WV scenario and instead fit all events together.
 * `--skipZeroes`: skip generating signal models for (proc,cat) with 0 events.
 * `--skipSystematics`: skip adding photon systematics to signal models. Use if have not ran the `calcPhotonSyst` mode.
 * `--useDiagonalProcForSyst`: takes the systematic constants from diagonal process (requires running the `getDiagProc` mode first). Useful if the MC statistics are low which can lead to dubious values for systematics constants.
 * `--replacementThreshold`: change the threshold number of entries with which to use replacement dataset. Default = 100
 * `--MHPolyOrder`: change the order of the polynomial which defines the MH dependence of fit parameters. Default is a linear interpolation (1). If using only one mass point then this is automatically set to 0.
 * `minimizerMethod` and `minimizerTolerance`: options for scipy minimize, used for fit
 * `--mggLow`, `--mggHigh`: Set the range of the $m_{\gamma\gamma}$ fit. Default is 100-180 GeV.
 * `--mjjLow`, `--mjjHigh`: Set the range of the $m_{jj}$ fit. Default is 80-190 GeV.
 * `--mggBinWidth`, `--mjjBinWidth`: Set the bin width for the $m_{\gamma\gamma}$ and $m_{jj}$ fits. Default is 2 GeV.
 * `--nGaussMax`: Set the maximum number of Gaussians to test. Default is 5. Only valid for fits with dynamic number of Gaussians.

**Note:** The `--nBins` option has been superceeded by the `--m{gg,jj}BinWidth` options. Bin number is computed as `nBins = floor((high - low) / binWidth)` as to ensure integer bin numbers. If the fit range is not divisible by the bin width, the actual bin width will be slightly larger than the requested bin width.

## Signal model plots

Run on the packaged signal models to produce this kind of [plot](http://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/HIG-19-015/CMS-PAS-HIG-19-015_Figure_012-a.pdf). 
```
python3 RunPlotter.py --procs all --years 2016,2017,2018 --cats cat0 --ext packaged
```
The options are defined in `RunPlotter.py`. Use `--cats all` to plot the sum of all analysis categories in `./outdir_{ext}` directory.

To weight the categories according to their respective (S/S+B) then you can use the `--loadCatWeight X` option, where X is the output json file of `../Plots/getCatInfo.py`.