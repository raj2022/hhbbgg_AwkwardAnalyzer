# binning.py
#
# Histogram binning definitions per region, for plotting the analyzer's
# output. Each region's binning is derived from binning["preselection"]
# via copy.deepcopy(), so region-specific overrides (e.g. srbbggMET's
# met_variables) layer on top of a shared base -- fixing an entry in
# "preselection" propagates to every region that copies from it, which
# is every region defined in this file.
#
# --------------------------------------------------------------------------
# FIXED IN THIS PASS (all four confirmed before changing)
# --------------------------------------------------------------------------
# 1. dibjet_mass: [33, 0, 180] -> [80, 0, 800]. The old range only
#    covers up to 180 GeV, but this analysis's M_Y grid spans 90-800 GeV
#    -- every mass point above ~180 GeV would have its dibjet_mass
#    signal peak pushed almost entirely into the overflow bin, making it
#    effectively invisible in any plot. Since every region's binning is
#    deepcopy'd from preselection, fixing it once here fixes it
#    everywhere. NOTE: a single fixed range/bin-width is a compromise
#    across the whole grid -- coarser than ideal for low-M_Y points,
#    but no longer hides high-M_Y points in the overflow bin. Widen
#    further or move to per-mass-point binning if finer detail is
#    needed at the low-mass end.
# 2. DeltaPhi_j1MET / DeltaPhi_j2MET: [10, 100, 110] -> [20, 0, 3.14].
#    A DeltaPhi (angular separation) variable ranges [0, pi] -- [100,110]
#    is not a physically valid range for any angular quantity and was
#    confirmed as a bug, not an intentional choice.
# 3. lepton1_mvaID: [100, 0, 100] -> [20, -1, 1], matching the existing
#    convention already used for photon mvaID scores in this same file
#    (lead_pho_mvaID / sublead_pho_mvaID: [20, -1, 1]). MVA discriminant
#    scores in this framework are consistently in [-1, 1]; [0, 100] was
#    confirmed as a bug.
# 4. lepton1_pfIsoId: [100, 0, 100] -> [7, 0, 7]. PF isolation ID is a
#    small discrete working-point flag (CMS convention: typically 0-6),
#    not a continuous 0-100 quantity; confirmed as a bug. Double-check
#    the exact valid range (0-6 vs a different max) for your specific
#    lepton flavor/data-taking era before treating this as final --
#    this is a reasonable best-effort fix, not independently verified
#    against a specific POG recommendation.
#
# --------------------------------------------------------------------------
# NOT CHANGED -- lower confidence, not confirmed
# --------------------------------------------------------------------------
# Res_chi_t0 / Res_chi_t1: [100, 0, 100] left as-is -- plausible for a
# chi-squared-like top-reconstruction quantity, not flagged as
# confidently wrong the way the four above were.
# --------------------------------------------------------------------------

import copy

binning = {}
binning["preselection"] = {
    "dibjet_mass": [80, 0, 800],   # FIXED: was [33, 0, 180] -- too narrow for M_Y up to 800 GeV
    "diphoton_mass": [25, 95, 180],    # avoiding the turn-on issues for the mass below MX<95GeV
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
    "sublead_bjet_PNetRegPtRawRes":[10, 0, 1],
    "lead_bjet_PNetRegPtRawRes":[10, 0, 1],
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
    "max_gamma_MVA_ID":[20, -1, 1],
    # "puppiMET_pt": [20, 100, 200],
    # "puppiMET_phi":[10, -3.14, 3.14],
    # "puppiMET_phiJERDown":[10, -3.14, 100],
    # "puppiMET_phiJERUp":[100, -3.14, 3.14],
    # "puppiMET_phiJESDown":[100, -3.14, 3.14],
    # "puppiMET_phiJESUp":[100, -3.14, 3.14],
    # "puppiMET_phiUnclusteredDown":[100, -3.14, 3.14],
    # "puppiMET_phiUnclusteredUp":[100, -3.14, 3.14],
    # "puppiMET_phiJERDown":[100, -3.14, 3.14],
    # "puppiMET_ptJERDown":[100, 0, 100],
    # "puppiMET_ptJERUp":[100, 0, 100],
    # "puppiMET_ptJESDown":[100, 0, 100],
    # "puppiMET_ptJESUp":[100, 0, 100],
    "DeltaPhi_j1MET":[20, 0, 3.14],   # FIXED: was [10, 100, 110] -- not a valid angular range
    "DeltaPhi_j2MET":[20, 0, 3.14],   # FIXED: same issue as above
    "Res_chi_t0":[100,0,100],
    "Res_chi_t1":[100,0,100],
    "lepton1_mvaID":[20, -1, 1],   # FIXED: was [100, 0, 100] -- MVA scores in this framework are [-1,1] (matches lead_pho_mvaID convention above)
    "lepton1_pt":[100,0,100],
    "lepton1_pfIsoId":[7, 0, 7],   # FIXED: was [100, 0, 100] -- PF iso ID is a small discrete flag, not continuous; double-check exact valid range for your era/flavor
    "n_jets":[10,0,15], # changed binning from 100 to 15.
    "pDNN_score":[20,0,1],
    "ttH_killer_score":[20,0,1],
    # Additional BTV variables can be added here
    "Njets2p5":[10,0,15],
    "HT":[20,0,1000],
    "n_leptons":[10,0,10],
}

binning["selection"] = copy.deepcopy(binning["preselection"])
binning["srbbgg"] = copy.deepcopy(binning["preselection"])
binning["srbbggMET"] = copy.deepcopy(binning["preselection"])
met_variables = {
                #  "puppiMET_pt": [20, 100, 200],
                #  "puppiMET_phi":[10, -3.14, 3.14],
                #  "puppiMET_phiJERDown":[10, -3.14, 100],
                #  "puppiMET_phiJERUp":[100, -3.14, 3.14],
                #  "puppiMET_phiJESDown":[100, -3.14, 3.14],
                #  "puppiMET_phiJESUp":[100, -3.14, 3.14],
                #  "puppiMET_phiUnclusteredDown":[100, -3.14, 3.14],
                #  "puppiMET_phiUnclusteredUp":[100, -3.14, 3.14],
                #  "puppiMET_phiJERDown":[100, -3.14, 3.14],
                #  "puppiMET_ptJERDown":[100, 0, 100],
                #  "puppiMET_ptJERUp":[100, 0, 100],
                #  "puppiMET_ptJESDown":[100, 0, 100],
                #  "puppiMET_ptJESUp":[100, 0, 100],
                     }
binning["srbbggMET"].update(met_variables)
binning["crantibbgg"] = copy.deepcopy(binning["preselection"])
binning["crbbantigg"] = copy.deepcopy(binning["preselection"])
binning["crantibbantigg"] = copy.deepcopy(binning["preselection"])
binning["sideband"] = copy.deepcopy(binning["preselection"])
binning["idmva_sideband"] = copy.deepcopy(binning["preselection"])
binning["idmva_presel"] = copy.deepcopy(binning["preselection"])