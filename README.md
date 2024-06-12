# hhbbgg AwkwardAnalyzer
Repository to keep the analyzers using awkward arrays, using skimmer or nanoAOD as input.

### Dependencies
Following packages are needed for the analyzer to work
```
matplotlib
uproot
hist
numpy
mplhep
vector
ROOT
awkward
pandas
```
A virtual environment can be created for this using the following command
```
conda env create -f requirement.yml
```
if available, do it with mamba, it's much faster
```
mamba env create -f requirement.yml
```

For now the analyser can be run normally using python
```
python hhbbgg_Analyzer.py
```
provided that the input directory having one root file for each background is defined with the variable name `inputfilesDir` in `hhbbgg_Analyzer.py`.
This saves a root file in `outputfiles` which contains sample names as directory and all the histograms are saved inside those directories.

To plot the histograms `hhbbgg_Plotter.py` can be used as:
```
python hhbbgg_Plotter.py
```
The plots will be saved in `stack_plots` directory

To add the variable, changes are to be done in `hhbbgg_Analyzer.py`, `binning.py` and `variables.py` file

To plot the histogram of the variable, it has to be added in `histogram_names` list and `xtitle_dict` dictionary in `hhbbgg_Plotter.py` file