import copy
binning={}
binning["preselection"]={"dibjet_mass":[25,80,180],
                "diphoton_mass":[25,80,180],
                "bbgg_mass":[25,150,500],
                "dibjet_pt":[25,30,180],
                "diphoton_pt":[25,30,180],
                "bbgg_pt":[25,30,500],
                "lead_pho_pt":[25,35,200],
                "sublead_pho_pt":[25,25,200],
                # "metphi":[40,-3.14,3.14],
                # "jetpt0":[50,0,1000.],
                # "jetpt1":[50,0,1000.],
                # "jetphi0":[70,-3.5,3.5],
                # "jetphi1":[70,-3.5,3.5],

                # "jeteta0":[50,-2.5,2.5],
                # "jeteta1":[50,-2.5,2.5],

                # "csv0": [20,0,1.],
                # "csv1": [20,0,1.],

                # "nTrueInt": [50,0,100.],

                # "nJetLoose":[5,0,5],
                # "nEleLoose":[3,0,3],

                # "min_dphi_jet_met":[50,-5,5],
                # "nMuLoose":[2,0,2],
                # "ntau":[2,0,2],
                # "npho":[2,0,2],

                # "cts":[100,-1,1],

                # "lead_pho_pt":[100,0,200],
                # "sublead_pho_pt":[100,0,200],

                # "mupt0":[100,0,200],
                # "mupt1":[100,0,200],

                # 'eleeta0':[70,-3.5,3.5],
                # 'eleeta1':[70,-3.5,3.5],

                # 'mueta0':[70,-3.5,3.5],
                # 'mueta1':[70,-3.5,3.5],

                # 'Zee_mass': [100,50,150],
                # 'Zmumu_mass': [100,50,150],

                # 'Zee_pt': [100,0,400],
                # 'Zmumu_pt': [100,0,400],

                # 'Zee_recoil':[100,0,1000],
                # 'Zmumu_recoil':[100,0,1000],
                # 'recoil_Wenu0':[100,0,1000],
                # 'recoil_Wmunu0':[100,0,1000],
                # 'mt_Wenu0':[100,0,1000],
                # 'mt_Wmunu0':[100,0,1000],

}

binning["selection"] =copy.deepcopy(binning["preselection"])
