# %%
import os
import optparse
import uproot
import awkward as ak
from config.utils import lVector, VarToHist
from normalisation import getXsec, getLumi

usage = "usage: %prog [options] arg1 arg2"
parser = optparse.OptionParser(usage)
parser.add_option(
    "-i",
    "--inFile",
    type="string",
    dest="inputfiles_",
    help="Either single input ROOT file or a directory of ROOT files",
)
(options, args) = parser.parse_args()

if not options.inputfiles_:
    raise ValueError(
        "Please provide either an input ROOT file or a directory of ROOT files using the -i or --inFile option"
    )
inputfiles_ = options.inputfiles_


def runOneFile(inputfile, outputrootfile):
    isdata = False
    isSignal = False
    if "Data" in inputfile.split("/")[-1]:
        isdata = True
        xsec_ = 1
        lumi_ = 1
    else:
        xsec_ = getXsec(inputfile)
        lumi_ = getLumi() * 1000
    if "GluGluToHH" in inputfile.split("/")[-1]:
        isSignal = True

    print("Status of the isdata flag:", isdata)
    # mycache = uproot.LRUArrayCache("500 MB")

    file_ = uproot.open(inputfile)

    print("root file opened: ", inputfile)
    print(file_.keys())

    fulltree_ = ak.ArrayBuilder()
    niterations = 0
    for tree_ in uproot.iterate(
        file_["DiphotonTree/data_125_13TeV_NOTAG"],
        [
            "run",
            "lumi",
            "event",
            "puppiMET_pt",
            "puppiMET_phi",
            "puppiMET_phiJERDown",
            "puppiMET_phiJERUp",
            "puppiMET_phiJESDown",
            "puppiMET_phiJESUp",
            "puppiMET_phiUnclusteredDown",
            "puppiMET_phiUnclusteredUp",
            "puppiMET_ptJERDown",
            "puppiMET_ptJERUp",
            "puppiMET_ptJESDown",
            "puppiMET_ptJESUp",
            "puppiMET_ptUnclusteredDown",
            "puppiMET_ptUnclusteredUp",
            "puppiMET_sumEt",
            "Res_lead_bjet_pt",
            "Res_lead_bjet_eta",
            "Res_lead_bjet_phi",
            "Res_lead_bjet_mass",
            "Res_sublead_bjet_pt",
            "Res_sublead_bjet_eta",
            "Res_sublead_bjet_phi",
            "Res_sublead_bjet_mass",
            "lead_pt",
            "lead_eta",
            "lead_phi",
            "lead_mvaID_WP90",
            "lead_mvaID_WP80",  # tight PhotonID? or is it loose?
            "sublead_pt",
            "sublead_eta",
            "sublead_phi",
            "sublead_mvaID_WP90",
            "sublead_mvaID_WP80",
            "weight",
            "weight_central",
            "Res_lead_bjet_btagPNetB",
            "Res_sublead_bjet_btagPNetB",
            "lead_isScEtaEB",
            "sublead_isScEtaEB",
            "Res_HHbbggCandidate_pt",
            "Res_HHbbggCandidate_eta",
            "Res_HHbbggCandidate_phi",
            "Res_HHbbggCandidate_mass",
            "Res_CosThetaStar_CS",
            "Res_CosThetaStar_gg",
            "Res_CosThetaStar_jj",
            "Res_DeltaR_jg_min",
            "Res_pholead_PtOverM",
            "Res_phosublead_PtOverM",
            "Res_FirstJet_PtOverM",
            "Res_SecondJet_PtOverM",
            "lead_mvaID",
            "sublead_mvaID",
            "Res_DeltaR_j1g1",
            "Res_DeltaR_j2g1",
            "Res_DeltaR_j1g2",
            "Res_DeltaR_j2g2",
            "Res_M_X",
            ## Adding other variables
            # "pholead_PtOverM",
            # "phosublead_PtOverM",
            # "FirstJet_PtOverM",
            # "SecondJet_PtOverM",
            # "CosThetaStar_CS",
            # "CosThetaStar_gg",
            # "CosThetaStar_jj",
            # "DeltaR_j1g1",
            # "DeltaR_j2g1",
            # "DeltaR_j1g2",
            # "DeltaR_j2g2",
            # "DeltaR_j2g2",

        ],
        step_size=10000,
    ):
        print("Tree length for iteratiion ", len(tree_), (niterations))
        niterations = niterations + 1
        cms_events = ak.zip(
            {
                "run": tree_["run"],
                "lumi": tree_["lumi"],
                "event": tree_["event"],
                "puppiMET_pt": tree_["puppiMET_pt"],
                "puppiMET_phi": tree_["puppiMET_phi"],
                "puppiMET_phiJERDown": tree_["puppiMET_phiJERDown"],
                "puppiMET_phiJERUp": tree_["puppiMET_phiJERUp"],
                "puppiMET_phiJESDown": tree_["puppiMET_phiJESDown"],
                "puppiMET_phiJESUp": tree_["puppiMET_phiJESUp"],
                "puppiMET_phiUnclusteredDown": tree_["puppiMET_phiUnclusteredDown"],
                "puppiMET_phiUnclusteredUp": tree_["puppiMET_phiUnclusteredUp"],
                "puppiMET_ptJERDown": tree_["puppiMET_ptJERDown"],
                "puppiMET_ptJERUp": tree_["puppiMET_ptJERUp"],
                "puppiMET_ptJESDown": tree_["puppiMET_ptJESDown"],
                "puppiMET_ptJESUp": tree_["puppiMET_ptJESUp"],
                "puppiMET_ptUnclusteredDown": tree_["puppiMET_ptUnclusteredDown"],
                "puppiMET_ptUnclusteredUp": tree_["puppiMET_ptUnclusteredUp"],
                "puppiMET_sumEt": tree_["puppiMET_sumEt"],
                "lead_bjet_pt": tree_["Res_lead_bjet_pt"],
                "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
                "lead_bjet_phi": tree_["Res_lead_bjet_phi"],
                "lead_bjet_mass": tree_["Res_lead_bjet_mass"],
                "sublead_bjet_pt": tree_["Res_sublead_bjet_pt"],
                "sublead_bjet_eta": tree_["Res_sublead_bjet_eta"],
                "sublead_bjet_phi": tree_["Res_sublead_bjet_phi"],
                "sublead_bjet_mass": tree_["Res_sublead_bjet_mass"],
                "lead_pho_pt": tree_["lead_pt"],
                "lead_pho_eta": tree_["lead_eta"],
                "lead_pho_phi": tree_["lead_phi"],
                "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"],
                "lead_pho_mvaID_WP80": tree_["lead_mvaID_WP80"],
                "sublead_pho_pt": tree_["sublead_pt"],
                "sublead_pho_eta": tree_["sublead_eta"],
                "sublead_pho_phi": tree_["sublead_phi"],
                "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
                "sublead_pho_mvaID_WP80": tree_["sublead_mvaID_WP80"],
                "weight_central": tree_["weight_central"],
                "weight": tree_["weight"],
                "lead_bjet_PNetB": tree_["Res_lead_bjet_btagPNetB"],
                "sublead_bjet_PNetB": tree_["Res_sublead_bjet_btagPNetB"],
                "lead_isScEtaEB": tree_["lead_isScEtaEB"],
                "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
                "CosThetaStar_CS": tree_["Res_CosThetaStar_CS"],
                "CosThetaStar_gg": tree_["Res_CosThetaStar_gg"],
                "CosThetaStar_jj": tree_["Res_CosThetaStar_jj"],
                "DeltaR_jg_min": tree_["Res_DeltaR_jg_min"],
                "pholead_PtOverM": tree_["Res_pholead_PtOverM"],
                "phosublead_PtOverM": tree_["Res_phosublead_PtOverM"],
                "FirstJet_PtOverM": tree_["Res_FirstJet_PtOverM"],
                "SecondJet_PtOverM": tree_["Res_SecondJet_PtOverM"],
                "lead_pho_mvaID": tree_["lead_mvaID"],
                "sublead_pho_mvaID": tree_["sublead_mvaID"],
                "DeltaR_j1g1": tree_["Res_DeltaR_j1g1"],
                "DeltaR_j2g1": tree_["Res_DeltaR_j2g1"],
                "DeltaR_j1g2": tree_["Res_DeltaR_j1g2"],
                "DeltaR_j2g2": tree_["Res_DeltaR_j2g2"],
                "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
                "bbgg_pt": tree_["Res_HHbbggCandidate_pt"],
                "bbgg_eta": tree_["Res_HHbbggCandidate_eta"],
                "bbgg_phi": tree_["Res_HHbbggCandidate_phi"],
                "MX": tree_["Res_M_X"],

            },
            depth_limit=1,
        )
        out_events = ak.zip(
            {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]},
            depth_limit=1,
        )

        dibjet_ = lVector(
            cms_events["lead_bjet_pt"],
            cms_events["lead_bjet_eta"],
            cms_events["lead_bjet_phi"],
            cms_events["sublead_bjet_pt"],
            cms_events["sublead_bjet_eta"],
            cms_events["sublead_bjet_phi"],
            cms_events["lead_bjet_mass"],
            cms_events["sublead_bjet_mass"],
        )
        diphoton_ = lVector(
            cms_events["lead_pho_pt"],
            cms_events["lead_pho_eta"],
            cms_events["lead_pho_phi"],
            cms_events["sublead_pho_pt"],
            cms_events["sublead_pho_eta"],
            cms_events["sublead_pho_phi"],
        )
        cms_events["signal"] = isSignal
        cms_events["dibjet_mass"] = dibjet_.mass
        cms_events["dibjet_pt"] = dibjet_.pt
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"] = diphoton_.pt
#        cms_events["bbgg_mass"] = (dibjet_ + diphoton_).mass
#        cms_events["bbgg_pt"] = (dibjet_ + diphoton_).pt
#        cms_events["bbgg_eta"] = (dibjet_ + diphoton_).eta
#        cms_events["bbgg_phi"] = (dibjet_ + diphoton_).phi
        # Adding new variables
        cms_events["dibjet_eta"] = dibjet_.eta
        cms_events["dibjet_phi"] = dibjet_.phi
        cms_events["diphoton_eta"] = diphoton_.eta
        cms_events["diphoton_phi"] = diphoton_.phi
        # ----------------------------
        cms_events["lead_pt_over_diphoton_mass"] = (
            cms_events["lead_pho_pt"] / cms_events["diphoton_mass"]
        )
        cms_events["sublead_pt_over_diphoton_mass"] = (
            cms_events["sublead_pho_pt"] / cms_events["diphoton_mass"]
        )
        cms_events["lead_pt_over_dibjet_mass"] = (
            cms_events["lead_bjet_pt"] / cms_events["dibjet_mass"]
        )
        cms_events["sublead_pt_over_dibjet_mass"] = (
            cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
        )

        cms_events["diphoton_bbgg_mass"] = (
            cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
        )
        cms_events["dibjet_bbgg_mass"] = (
            cms_events["dibjet_pt"] / cms_events["bbgg_mass"]
        )

        from regions import (
            get_mask_preselection,
            get_mask_selection,
            get_mask_srbbgg,
            get_mask_srbbggMET,
            get_mask_crantibbgg,
            get_mask_crbbantigg,
        )

        cms_events["mask_preselection"] = get_mask_preselection(cms_events)
        cms_events["mask_selection"] = get_mask_selection(cms_events)
        cms_events["mask_srbbgg"] = get_mask_srbbgg(cms_events)
        cms_events["mask_srbbggMET"] = get_mask_srbbggMET(cms_events)
        cms_events["mask_crbbantigg"] = get_mask_crbbantigg(cms_events)
        cms_events["mask_crantibbgg"] = get_mask_crantibbgg(cms_events)

        # Adding puppi MET and associated variables
        out_events["puppiMET_pt"] = cms_events["puppiMET_pt"]
        out_events["puppiMET_phi"] = cms_events["puppiMET_phi"]

        out_events["puppiMET_phiJERDown"] = cms_events["puppiMET_phiJERDown"]
        out_events["puppiMET_phiJERUp"] = cms_events["puppiMET_phiJERUp"]
        out_events["puppiMET_phiJESDown"] = cms_events["puppiMET_phiJESDown"]
        out_events["puppiMET_phiJESUp"] = cms_events["puppiMET_phiJESUp"]
        out_events["puppiMET_phiUnclusteredDown"] = cms_events[
            "puppiMET_phiUnclusteredDown"
        ]
        out_events["puppiMET_phiUnclusteredUp"] = cms_events[
            "puppiMET_phiUnclusteredUp"
        ]
        out_events["puppiMET_ptJERDown"] = cms_events["puppiMET_ptJERDown"]
        out_events["puppiMET_ptJERUp"] = cms_events["puppiMET_ptJERUp"]
        out_events["puppiMET_ptJESDown"] = cms_events["puppiMET_ptJESDown"]
        out_events["puppiMET_ptJESUp"] = cms_events["puppiMET_ptJESUp"]
        out_events["puppiMET_ptUnclusteredDown"] = cms_events["puppiMET_ptUnclusteredDown"]
        out_events["puppiMET_ptUnclusteredUp"] = cms_events["puppiMET_ptUnclusteredUp"]
        out_events["puppiMET_sumEt"] = cms_events["puppiMET_sumEt"]
        ###--------------
        out_events["lead_pho_pt"] = cms_events["lead_pho_pt"]
        # Adding new variable
        out_events["lead_pho_eta"] = cms_events["lead_pho_eta"]
        out_events["lead_pho_phi"] = cms_events["lead_pho_phi"]
        out_events["sublead_pho_pt"] = cms_events["sublead_pho_pt"]
        # Adding new variable
        out_events["sublead_pho_eta"] = cms_events["sublead_pho_eta"]
        out_events["sublead_pho_phi"] = cms_events["sublead_pho_phi"]
        # Adding bjet variables
        out_events["lead_bjet_pt"] = cms_events["lead_bjet_pt"]
        out_events["lead_bjet_eta"] = cms_events["lead_bjet_eta"]
        out_events["lead_bjet_phi"] = cms_events["lead_bjet_phi"]
        out_events["sublead_bjet_pt"] = cms_events["sublead_bjet_pt"]
        out_events["sublead_bjet_eta"] = cms_events["sublead_bjet_eta"]
        out_events["sublead_bjet_phi"] = cms_events["sublead_bjet_phi"]
        # --------------
        out_events["dibjet_mass"] = cms_events["dibjet_mass"]
        out_events["diphoton_mass"] = cms_events["diphoton_mass"]
        out_events["bbgg_mass"] = cms_events["bbgg_mass"]
        out_events["dibjet_pt"] = cms_events["dibjet_pt"]
        out_events["diphoton_pt"] = cms_events["diphoton_pt"]
        out_events["bbgg_pt"] = cms_events["bbgg_pt"]
        out_events["bbgg_eta"] = cms_events["bbgg_eta"]
        out_events["bbgg_phi"] = cms_events["bbgg_phi"]
        out_events["weight_central"] = cms_events["weight_central"]
        out_events["weight_preselection"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        out_events["weight_selection"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        out_events["weight_srbbgg"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        out_events["weight_srbbggMET"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        out_events["weight_crbbantigg"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        out_events["weight_crantibbgg"] = (
            cms_events["weight"] * xsec_ * lumi_ / out_events.weight_central
        )
        # Adding new variable
        out_events["dibjet_eta"] = cms_events["dibjet_eta"]
        out_events["dibjet_phi"] = cms_events["dibjet_phi"]
        out_events["diphoton_eta"] = cms_events["diphoton_eta"]
        out_events["diphoton_phi"] = cms_events["diphoton_phi"]

        out_events["lead_bjet_PNetB"] = cms_events["lead_bjet_PNetB"]
        out_events["sublead_bjet_PNetB"] = cms_events["sublead_bjet_PNetB"]
        # ------------------------------------------------
        out_events["pholead_PtOverM"] = cms_events["pholead_PtOverM"]
        out_events["phosublead_PtOverM"] = cms_events["phosublead_PtOverM"]
        out_events["FirstJet_PtOverM"] = cms_events["FirstJet_PtOverM"]
        out_events["SecondJet_PtOverM"] = cms_events["SecondJet_PtOverM"]
        # ------------------------------------------------
        out_events["CosThetaStar_CS"] = cms_events["CosThetaStar_CS"]
        out_events["CosThetaStar_jj"] = cms_events["CosThetaStar_jj"]
        out_events["CosThetaStar_gg"] = cms_events["CosThetaStar_gg"]
        out_events["DeltaR_jg_min"] = cms_events["DeltaR_jg_min"]
        # ------------------------------------------------
        out_events["lead_pt_over_diphoton_mass"] = cms_events[
            "lead_pt_over_diphoton_mass"
        ]
        out_events["sublead_pt_over_diphoton_mass"] = cms_events[
            "sublead_pt_over_diphoton_mass"
        ]
        out_events["lead_pt_over_dibjet_mass"] = cms_events["lead_pt_over_dibjet_mass"]
        out_events["sublead_pt_over_dibjet_mass"] = cms_events[
            "sublead_pt_over_dibjet_mass"
        ]
        out_events["diphoton_bbgg_mass"] = cms_events["diphoton_bbgg_mass"]
        out_events["dibjet_bbgg_mass"] = cms_events["dibjet_bbgg_mass"]

        #--------------------------------------------------

        out_events["lead_pho_mvaID_WP90"] = cms_events["lead_pho_mvaID_WP90"]
        out_events["lead_pho_mvaID_WP80"] = cms_events["lead_pho_mvaID_WP80"]
        out_events["sublead_pho_mvaID_WP90"] = cms_events["sublead_pho_mvaID_WP90"]
        out_events["sublead_pho_mvaID_WP80"] = cms_events["sublead_pho_mvaID_WP80"]
        out_events["lead_pho_mvaID"] = cms_events["lead_pho_mvaID"]
        out_events["sublead_pho_mvaID"] = cms_events["sublead_pho_mvaID"]

        #--------------------------------------------------
        #--------------------------------------------------
        out_events["preselection"] = cms_events["mask_preselection"]
        out_events["selection"] = cms_events["mask_selection"]
        out_events["srbbgg"] = cms_events["mask_srbbgg"]
        out_events["srbbggMET"] = cms_events["mask_srbbggMET"]
        out_events["crantibbgg"] = cms_events["mask_crantibbgg"]
        out_events["crbbantigg"] = cms_events["mask_crbbantigg"]
## Adding deltaR(j,g)

        out_events["DeltaR_j1g1"] = cms_events["DeltaR_j1g1"]
        out_events["DeltaR_j2g1"] = cms_events["DeltaR_j2g1"]
        out_events["DeltaR_j1g2"] = cms_events["DeltaR_j1g2"]
        out_events["DeltaR_j2g2"] = cms_events["DeltaR_j2g2"]

        #---------------------------------------------------
        #---------------------------------------------------
        out_events["MX"] = cms_events["MX"]

        fulltree_ = ak.concatenate([out_events, fulltree_], axis=0)

    from variables import vardict, regions, variables_common
    from binning import binning

    print("Making histograms and trees")
    outputrootfileDir = inputfile.split("/")[-1].replace(".root", "")
    for ireg in regions:
        thisregion = fulltree_[fulltree_[ireg] == True]
        thisregion_ = thisregion[~(ak.is_none(thisregion))]
        weight_ = "weight_" + ireg
        for ivar in variables_common[ireg]:
            hist_name_ = ireg + "-" + vardict[ivar]
            outputrootfile["hist"][f"{outputrootfileDir}/{hist_name_}"] = VarToHist(
                thisregion_[ivar], thisregion_[weight_], hist_name_, binning[ireg][ivar]
            )
        tree_data_ = thisregion_[
            [key for key in thisregion_.fields if key not in regions]
        ]
        outputrootfile["tree"][f"{outputrootfileDir}/{ireg}"] = tree_data_
    print("Done")


output_dir = "outputfiles"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if os.path.isfile(inputfiles_):
    inputfiles = [inputfiles_]
else:
    inputfiles = [
        f"{inputfiles_}/{infile_}"
        for infile_ in os.listdir(inputfiles_)
        if infile_.endswith(".root")
    ]

outputrootfile = {
    "hist": uproot.recreate(f"{output_dir}/hhbbgg_analyzer_v2-histograms.root"),
    "tree": uproot.recreate(f"{output_dir}/hhbbgg_analyzer_v2-trees.root"),
}


def main():
    for infile_ in inputfiles:
        runOneFile(infile_, outputrootfile)


if __name__ == "__main__":
    main()

# %%
