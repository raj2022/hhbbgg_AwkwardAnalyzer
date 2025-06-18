import ROOT

# Open the ROOT file containing signal and background histograms
root_file_path = "fitting_results.root"
root_file = ROOT.TFile(root_file_path, "READ")

# Define the observable (diphoton mass)
mass = ROOT.RooRealVar("mgg", "Diphoton Mass (GeV)", 100, 140)

# Retrieve and convert signal histogram
hist_signal = root_file.Get("NMSSM_X400_Y125")  # Signal
if not hist_signal:
    print("Signal histogram not found!")
roo_hist_signal = ROOT.RooDataHist("hist_signal", "Signal Histogram", ROOT.RooArgList(mass), hist_signal)
pdf_signal = ROOT.RooHistPdf("pdf_signal", "Signal PDF", ROOT.RooArgSet(mass), roo_hist_signal)

# Retrieve and convert background histograms
backgrounds = ["GGJets", "GJetPt40", "GJetPt20To40", "VBFHToGG", "VHToGG", "ttHToGG"]
pdf_backgrounds = []
coefficients = []

# Initialize a list to store all histograms for calculating n_expected
all_histograms = [hist_signal]

for i, name in enumerate(backgrounds):
    hist = root_file.Get(name)
    if not hist:
        print(f"Warning: Histogram {name} not found in ROOT file!")
        continue

    roo_hist = ROOT.RooDataHist(f"hist_bg_{i}", f"{name} Histogram", ROOT.RooArgList(mass), hist)
    pdf_bg = ROOT.RooHistPdf(f"pdf_bg_{i}", f"{name} PDF", ROOT.RooArgSet(mass), roo_hist)

    pdf_backgrounds.append(pdf_bg)

    # Background fractions (free parameters)
    coef = ROOT.RooRealVar(f"coef_bg_{i}", f"Fraction of {name}", hist.Integral(), 0, 1e6)
    coefficients.append(coef)

    # Add histogram to the list for expected data calculation
    all_histograms.append(hist)

# Create summed background model (if multiple backgrounds exist)
if len(pdf_backgrounds) > 1:
    pdf_bkg = ROOT.RooAddPdf("pdf_bkg", "Total Background PDF", ROOT.RooArgList(*pdf_backgrounds), ROOT.RooArgList(*coefficients))
elif len(pdf_backgrounds) == 1:
    pdf_bkg = pdf_backgrounds[0]
else:
    raise RuntimeError("No valid background histograms found!")

# Calculate total number of expected events for the Asimov dataset
n_expected = sum(hist.Integral() for hist in all_histograms)
asimov_data = pdf_bkg.generate(ROOT.RooArgSet(mass), int(n_expected))

# Create a workspace and import all objects
workspace = ROOT.RooWorkspace("w")
getattr(workspace, "import")(pdf_signal)
getattr(workspace, "import")(pdf_bkg)
getattr(workspace, "import")(asimov_data, ROOT.RooFit.Rename("data_obs"))  # Import Asimov dataset as "data_obs"

# Save workspace
workspace_file = ROOT.TFile("workspace.root", "RECREATE")
workspace.Write()
workspace_file.Close()

print("Workspace saved as workspace.root")
