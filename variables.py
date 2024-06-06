import copy
#regions=["SR_1b", "SR_2b", "ZeeCR_2b", "ZeeCR_1b", "ZmumuCR_2b", "ZmumuCR_1b", "TopenuCR_2b", "TopenuCR_1b", "TopmunuCR_2b", "TopmunuCR_1b", "WenuCR_2b", "WenuCR_1b", "WmunuCR_2b", "WmunuCR_1b"]
regions=["preselection"]

vardict={"dibjet_mass":"dibjet_mass",
        "diphoton_mass":"diphoton_mass",
        "bbgg_mass":"bbgg_mass",
        #  "metphi":"METPhi",
        #  "jetpt0":"Jet1Pt",
        #  "jetpt1":"Jet2Pt",
        #  "jeteta0":"Jet1Eta",
        #  "jeteta1":"Jet2Eta",
        #  "jetphi0":"Jet1Phi",
        #  "jetphi1":"Jet2Phi",
        #  "csv0":"Jet1deepCSV",
        #  "csv1":"Jet2deepCSV",


        #  "recoil_Wmunu0":"Recoil",
        #  "recoil_Wenu0":"Recoil",
        #  "Zmumu_recoil":"Recoil",
        #  "Zee_recoil":"Recoil",
        #  "recoil_WmunuPhi0":"RecoilPhi",
        #  "recoil_WenuPhi0":"RecoilPhi",
        #  "Zee_recoilPhi":"RecoilPhi",
        #  "Zmumu_recoilPhi":"RecoilPhi",

        #  "nTrueInt":"nPV",

        #  "nJetLoose":"nJets",
        #  "nEleLoose":"NEle",

        #  "cts":"ctsValue",
        #  "nJetb":"nBJets",
        #  "pfpatCaloMETPt":"pfpatCaloMETPt",

        #  #"pfpatCaloMETPhi":"pfpatCaloMETPhi",
        #  #"pfTRKMETPt":"pfTRKMETPt",
        #  #"pfTRKMETPhi":"pfTRKMETPhi",

        #  "nMuLoose":"NMu",
        #  "ntau":"NTau",
        #  "npho":"nPho",
        #  "min_dphi_jet_met":"min_dPhi",

        #  "mupt0":"lep1_pT",
        #  "mupt1":"lep2_pT",
        #  "mueta0":"lep1_eta",
        #  "mueta1":"lep2_eta",

        #  "elept0":"lep1_pT",
        #  "elept1":"lep2_pT",
        #  "eleeta0":"lep1_eta",
        #  "eleeta1":"lep2_eta",

        #  "mt_Wmunu0":"Wmass",
        #  "mt_Wenu0":"Wmass",
        #  "pt_Wmunu0":"WpT",
        #  "pt_Wenu0":"WpT",
        #  "Zee_mass":"Zmass",
        #  "Zmumu_mass":"Zmass",
        #  "Zmumu_pt":"ZpT",
        #  "Zee_pt":"ZpT"
}


variables_common={"preselection":["dibjet_mass","diphoton_mass","bbgg_mass"]}

# for ireg in regions:
#         print(ireg)
#         variables_common[ireg] = copy.deepcopy(variables_common["dijet_mass"])


# sr_2b=["csv1","jetpt1","jeteta1","jetphi1","cts"]
# variables_common["SR_2b"] = variables_common["SR_2b"] + sr_2b


# ZeeCR_2b=["elept0","elept1","eleeta0","eleeta1","Zee_mass","Zee_pt","Zee_recoil"]
# variables_common["ZeeCR_3j"] = variables_common["ZeeCR_3j"] + sr_2b + ZeeCR_2b

# ZmumuCR_2b=["mupt0","mupt1","mueta0","mueta1","Zmumu_mass","Zmumu_pt","Zmumu_recoil"]
# variables_common["ZmumuCR_3j"] = variables_common["ZmumuCR_3j"] + sr_2b + ZmumuCR_2b

# ZeeCR_1b     = variables_common["ZeeCR_2j"]   + ZeeCR_2b ## electron variables will be same
# ZmumuCR_1b   = variables_common["ZmumuCR_2j"] + ZmumuCR_2b ## muon variables will be same


# TopenuCR_2b=["elept0","eleeta0","mt_Wenu0","recoil_Wenu0"]
# variables_common["TopenuCR_2b"] = variables_common["TopenuCR_2b"] + TopenuCR_2b + sr_2b

# TopmunuCR_2b=["mupt0", "mueta0", "mt_Wmunu0", "recoil_Wmunu0"]
# variables_common["TopmunuCR_2b"] = variables_common["TopmunuCR_2b"] + TopmunuCR_2b + sr_2b

# WenuCR_1b=variables_common["WenuCR_1b"] + TopenuCR_2b
# WmunuCR_1b=variables_common["WmunuCR_1b"] + TopmunuCR_2b


#variables_common["SR_2b"].append("csv1")
#variables_common["SR_2b"].append("jetpt1")
#variables_common["SR_2b"].append("jeteta1")
