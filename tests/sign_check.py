import ROOT

# Open the ROOT file
file_path = "../../../output_root/NMSSM/NMSSM_X300_Y100.root"
root_file = ROOT.TFile.Open(file_path)

# Access the tree inside DiphotonTree/data_125_13TeV_NOTAG
tree = root_file.Get("DiphotonTree/data_125_13TeV_NOTAG")

# Define masses (mX, mH, mY) for the X-Y pair. These should be known from your analysis.
mX = 300  # Example value for mX (GeV)
mH = 125  # Higgs mass (GeV)
mY = 100  # Example value for mY (GeV)

# Loop over the entries in the tree
for entry in tree:
    # Get jet eta values
    jet1_eta = entry.jet1_eta
    jet2_eta = entry.jet2_eta

    # Calculate the boost factor
    boost_factor =  mX / (mH + mY)

    # Determine the hemisphere of jets
    if jet1_eta * jet2_eta < 0:
        hemisphere = "Opposite"
    else:
        hemisphere = "Same"

    # Classify based on the boost factor and the hemisphere
    if boost_factor <= 2:
        category = "lowX lowY / midX midY / highX highY (boost-factor <= 2)"
    elif 1.5 < boost_factor <= 3:
        category = "midX lowY / highX midY (1.5 < boost-factor <= 3)"
    elif 2.5 < boost_factor <= 5:
        category = "highX lowY (2.5 < boost-factor <= 5)"
    else:
        category = "Unclassified"

    # Print the result
    print(f"Boost factor: {boost_factor:.2f}, Hemisphere: {hemisphere}, Category: {category}")

# Close the file
root_file.Close()

