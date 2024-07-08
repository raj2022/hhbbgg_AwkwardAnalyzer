import copy

binning = {}
binning["preselection"] = {
    "dibjet_mass": [25, 80, 180],
    "diphoton_mass": [25, 80, 180],
    "bbgg_mass": [25, 150, 500],
    "dibjet_pt": [25, 30, 180],
    "diphoton_pt": [25, 30, 180],
    "bbgg_pt": [25, 30, 500],
    "bbgg_eta": [10, -3, 3],
    "bbgg_phi": [10, -3.14, 3.14],
    "lead_pho_pt": [25, 35, 200],
    "lead_pho_eta": [10, -3, 3],
    "lead_pho_phi": [10, -3.14, 3.14],
    "sublead_pho_pt": [25, 25, 200],
    "sublead_pho_eta": [10, -3, 3],
    "sublead_pho_phi": [10, -3.14, 3.14],
    "dibjet_eta": [10, -3, 3],
    "dibjet_phi": [10, -3.14, 3.14],
    "diphoton_eta": [10, -3, 3],
    "diphoton_phi": [10, -3.14, 3.14],
    # ------------bjet
    "lead_bjet_pt": [25, 35, 200],
    "lead_bjet_eta": [10, -3, 3],
    "lead_bjet_phi": [10, -3.14, 3.14],
    "sublead_bjet_pt": [25, 25, 200],
    "sublead_bjet_eta": [10, -3, 3],
    "sublead_bjet_phi": [10, -3.14, 3.14],
    "lead_bjet_PNetB": [10, 0, 1],
    "sublead_bjet_PNetB": [10, 0, 1],
    "CosThetaStar_gg": [10, 0, 1],
    "CosThetaStar_CS": [10, 0, 1],
    "CosThetaStar_jj": [10, 0, 1],
    "DeltaR_jg_min": [20, 0, 4],
    "pholead_PtOverM": [20, 0, 4],
    "phosublead_PtOverM": [20, 0, 4],
    "FirstJet_PtOverM": [10, 0, 2.5],
    "SecondJet_PtOverM": [20, 0, 2.5],
    "lead_pt_over_diphoton_mass": [20, 0, 4],
    "sublead_pt_over_diphoton_mass": [20, 0, 3.5],
    "lead_pt_over_dibjet_mass": [20, 0, 4],
    "sublead_pt_over_dibjet_mass": [20, 0, 2],
    "diphoton_bbgg_mass": [20, 0, 1],
    "dibjet_bbgg_mass": [20, 0, 2],
}

binning["srbbgg"] = copy.deepcopy(binning["preselection"])
binning["srbbggMET"] = copy.deepcopy(binning["preselection"])
met_variables = {"puppiMET_pt": [50, 100, 1000], "puppiMET_phi": [10, -3.14, 3.14]}
binning["srbbggMET"].update(met_variables)
binning["crantibbgg"] = copy.deepcopy(binning["preselection"])
binning["crbbantigg"] = copy.deepcopy(binning["preselection"])
