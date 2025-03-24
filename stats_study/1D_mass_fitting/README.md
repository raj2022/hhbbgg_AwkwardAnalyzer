# 1D mass fitting 
Fitting of the signal and background with different functions and on the fitted function we are trying to preare a datacard. Further, on the datacard we run combine tool to get the limit.

<span style="color: red;">Error:</span>
Combine is asking of data observed or the toy data(asimov) for the limit extraction. 
-> We can provide data for specific mass either diphoton mass($m_{\gamma\gamma}$) or dibjet mass.

for the  `1D Mass Fitting`, here are the detail descriptions:

# **CMS Combine Datacard Preparation**
This guide explains how to prepare a **CMS Combine** datacard for multiple signal and background processes, generate the necessary ROOT files, and run the statistical analysis.

---

## **1️⃣ Structure of the Datacard**
Create a datacard named **`datacard.txt`** with multiple signals and backgrounds.

```plaintext
imax 1  # Number of categories (1 bin)
jmax 7  # Number of processes (e.g., 3 signals + 4 backgrounds)
kmax *  # Number of nuisance parameters

-------------------------------------------------
# Observed data
bin                cat1
observation        -1  # Use Asimov dataset

-------------------------------------------------
# Signal and Background Processes
bin                cat1         cat1         cat1         cat1         cat1         cat1         cat1         cat1
process            sig1         sig2         sig3         bkg1         bkg2         bkg3         bkg4         bkg5
process            0            1            2            3            4            5            6            7
rate               1.0          1.0          1.0          1.0          1.0          1.0          1.0          1.0  

-------------------------------------------------
# Systematic Uncertainties
lumi       lnN     1.025        1.025        1.025        -            -            -            -            -
sigNorm1   lnN     1.10         -            -            -            -            -            -            -
sigNorm2   lnN     -            1.10         -            -            -            -            -            -
sigNorm3   lnN     -            -            1.10         -            -            -            -            -
bkgNorm1   lnN     -            -            -            1.10         -            -            -            -
bkgNorm2   lnN     -            -            -            -            1.15         -            -            -
bkgNorm3   lnN     -            -            -            -            -            1.20         -            -
bkgNorm4   lnN     -            -            -            -            -            -            1.25         -
bkgNorm5   lnN     -            -            -            -            -            -            -            1.30

-------------------------------------------------
# Shape-based Analysis (histograms from ROOT)
shapes * cat1 fit_shapes.root $PROCESS $PROCESS_$SYSTEMATIC
```

# Creating the ROOT File for Combine

```python
import ROOT

# Open a new ROOT file
fout = ROOT.TFile("fit_shapes.root", "RECREATE")

# Create histograms for signals and backgrounds
hist_sig1 = ROOT.TH1F("sig1", "Signal 1", len(bins)-1, bins)
hist_sig2 = ROOT.TH1F("sig2", "Signal 2", len(bins)-1, bins)
hist_sig3 = ROOT.TH1F("sig3", "Signal 3", len(bins)-1, bins)
hist_bkg1 = ROOT.TH1F("bkg1", "Background 1", len(bins)-1, bins)
hist_bkg2 = ROOT.TH1F("bkg2", "Background 2", len(bins)-1, bins)
hist_bkg3 = ROOT.TH1F("bkg3", "Background 3", len(bins)-1, bins)
hist_bkg4 = ROOT.TH1F("bkg4", "Background 4", len(bins)-1, bins)
hist_bkg5 = ROOT.TH1F("bkg5", "Background 5", len(bins)-1, bins)

# Fill histograms with fit results
for i in range(len(bins)-1):
    hist_sig1.SetBinContent(i+1, signal1_y[i])  # Replace with signal1 fit values
    hist_sig2.SetBinContent(i+1, signal2_y[i])  # Replace with signal2 fit values
    hist_sig3.SetBinContent(i+1, signal3_y[i])  # Replace with signal3 fit values
    hist_bkg1.SetBinContent(i+1, background1_y[i])  # Replace with background1 fit values
    hist_bkg2.SetBinContent(i+1, background2_y[i])  # Replace with background2 fit values
    hist_bkg3.SetBinContent(i+1, background3_y[i])  # Replace with background3 fit values
    hist_bkg4.SetBinContent(i+1, background4_y[i])  # Replace with background4 fit values
    hist_bkg5.SetBinContent(i+1, background5_y[i])  # Replace with background5 fit values

# Write histograms to file
fout.Write()
fout.Close()
```

# Convert the Datacard to a Workspace
```bash
text2workspace.py datacard.txt -o workspace.root
```

# Running ```combine```
###  Expected Limit Calculation
```bash
combine -M AsymptoticLimits -d workspace.root
```
###  Signal Strength Fit (μ)
```bash
combine -M MaxLikelihoodFit -d workspace.root --saveShapes --saveWithUncertainties
```
### Goodness of Fit (GOF) Test
```bash
combine -M GoodnessOfFit -d workspace.root --algo=saturated
```

Once the ```combine``` command runs, extract the expected 95% CL Upper Limit and plot it.
```bash
import ROOT

# Open combine result file
f = ROOT.TFile("higgsCombineTest.AsymptoticLimits.mH120.root")
tree = f.Get("limit")

# Get expected limits
exp_limits = [entry.limit for entry in tree]

# Print results
print(f"Expected 95% CL Upper Limits: {exp_limits}")
```
