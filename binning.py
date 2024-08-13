import copy

binning = {}
binning["preselection"] = {
    "dibjet_mass": [33, 50, 180],
    "diphoton_mass": [25, 50, 180],
    "bbgg_mass": [45, 150, 800],
    "dibjet_pt": [25, 30, 500],
    "diphoton_pt": [25, 30, 500],
    "bbgg_pt": [25, 50, 1000],
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
    "dibjet_bbgg_mass": [20, -1, 2],
    "lead_pho_mvaID_WP90": [2, 0, 1],
    "sublead_pho_mvaID_WP90": [2, 0, 1],
    "lead_pho_mvaID_WP80": [2, 0, 1],
    "sublead_pho_mvaID_WP80": [2, 0, 1],
    "lead_pho_mvaID": [20, -1, 1],
    "sublead_pho_mvaID": [20, -1, 1],
}

binning["selection"] = copy.deepcopy(binning["preselection"])
binning["srbbgg"] = copy.deepcopy(binning["preselection"])
binning["srbbggMET"] = copy.deepcopy(binning["preselection"])
met_variables = {"puppiMET_pt": [20, 100, 200],
                 "puppiMET_phi":[10, -3.14, 3.14],
                 "puppiMET_phiJERDown":[10, -3.14, 100],
                 "puppiMET_phiJERUp":[100, -3.14, 3.14],
                 "puppiMET_phiJESDown":[100, -3.14, 3.14],
                 "puppiMET_phiJESUp":[100, -3.14, 3.14],
                 "puppiMET_phiUnclusteredDown":[100, -3.14, 3.14],
                 "puppiMET_phiUnclusteredUp":[100, -3.14, 3.14],
                 "puppiMET_phiJERDown":[100, -3.14, 3.14],
                 "puppiMET_ptJERDown":[100, 0, 100],
                 "puppiMET_ptJERUp":[100, 0, 100],
                 "puppiMET_ptJESDown":[100, 0, 100],
                 "puppiMET_ptJESUp":[100, 0, 100],
                     }
binning["srbbggMET"].update(met_variables)
binning["crantibbgg"] = copy.deepcopy(binning["preselection"])
binning["crbbantigg"] = copy.deepcopy(binning["preselection"])
