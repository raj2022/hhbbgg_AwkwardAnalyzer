import copy

regions=["preselection","selection"]
vardict={
    "dibjet_mass":"dibjet_mass",
    "diphoton_mass":"diphoton_mass",
    "bbgg_mass":"bbgg_mass",
    "dibjet_pt":"dibjet_pt",
    "diphoton_pt":"diphoton_pt",
    "bbgg_pt":"bbgg_pt",
    "lead_pho_pt":"lead_pho_pt",
    "sublead_pho_pt":"sublead_pho_pt"
}

variables_common = {
    "preselection": [
        "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","lead_pho_pt","sublead_pho_pt"
    ]
}

for ireg in regions:
    print(ireg)
    variables_common[ireg] = copy.deepcopy(variables_common["preselection"])


# sr_2b=["csv1","jetpt1","jeteta1","jetphi1","cts"]
# variables_common["SR_2b"] = variables_common["SR_2b"] + sr_2b
