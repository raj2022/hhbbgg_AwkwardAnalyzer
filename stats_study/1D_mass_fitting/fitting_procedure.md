# Fitting Procedure
Based on the saved files shape, we saved as root file:

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