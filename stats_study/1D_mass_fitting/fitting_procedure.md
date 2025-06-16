# Fitting Procedure
Based on the saved files shape, we saved as root file, which an example for the signal saving are, 

```python
import ROOT
import numpy as np

# Define the ROOT file path
root_file_path = "fitting_results.root"

# Open or create the ROOT file in "UPDATE" mode
root_file = ROOT.TFile(root_file_path, "UPDATE")

# Define histogram bins in ROOT format
hist_fit = ROOT.TH1F("NMSSM_X400_Y125", "Fitted Crystal Ball Shape", len(bins) - 1, bins)

# Fill the histogram with the fitted function values
for i in range(len(bin_centers)):
    hist_fit.SetBinContent(i + 1, fitted_curve_cb[i])  # Set content using y-values from the fit

# Write the histogram to the ROOT file
hist_fit.Write()

# Close the ROOT file
root_file.Close()

print(f"Fitted histogram saved to {root_file_path}")
```


On the corresponding saved shapes of signal, backgrounds(resonant and non-resonant background) in the `.root` file, convert to roofit PDF space something like this:
```python 
import ROOT

# Open the ROOT file
root_file_path = "fitting_results.root"
root_file = ROOT.TFile(root_file_path, "READ")

# List objects in the file
root_file.ls()

# Retrieve the correct histogram
hist_fit = root_file.Get("NMSSM_X400_Y125")

# Verify that the histogram was retrieved correctly
if not hist_fit or not isinstance(hist_fit, ROOT.TH1):
    print("Error: Histogram 'NMSSM_X400_Y125' not found or is not a valid TH1 object!")
    exit()

# Define the observable (diphoton mass)
mass = ROOT.RooRealVar("mgg", "Diphoton Mass (GeV)", 100, 140)

# Convert histogram to a RooFit PDF
roo_hist = ROOT.RooDataHist("NMSSM_X400_Y125", "Fitted Crystal Ball Shape", ROOT.RooArgList(mass), hist_fit)
pdf = ROOT.RooHistPdf("pdf_fit", "Crystal Ball Fit PDF", ROOT.RooArgSet(mass), roo_hist)

# Create a workspace
workspace = ROOT.RooWorkspace("w")
getattr(workspace, "import")(pdf)  # Import the PDF into the workspace
workspace.Write()
workspace.Print()

# Save the workspace into a new ROOT file for Combine
workspace_file = ROOT.TFile("workspace.root", "RECREATE")
workspace.Write()
workspace_file.Close()

print("Workspace saved as workspace.root")
```
It can be further checked in the later cells of this jupyter notebook.
https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/parquest_v3/stats_study/notebook_fitting/background_fit_resonant.ipynb   

