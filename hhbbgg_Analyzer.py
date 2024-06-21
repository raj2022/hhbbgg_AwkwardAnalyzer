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
    if "Data" in inputfile.split("/")[-1]:
        isdata = True
        xsec_ = 1
        lumi_ = 1
    else:
        xsec_ = getXsec(inputfile)
        lumi_ = getLumi() * 1000
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
            "lead_bjet_pt",
            "lead_bjet_eta",
            "lead_bjet_phi",
            "lead_bjet_mass",
            "sublead_bjet_pt",
            "sublead_bjet_eta",
            "sublead_bjet_phi",
            "sublead_bjet_mass",
            "lead_pt",
            "lead_eta",
            "lead_phi",
            "lead_mvaID_WP90",
            "sublead_pt",
            "sublead_eta",
            "sublead_phi",
            "sublead_mvaID_WP90",
            "weight",
            "weight_central",
            "lead_bjet_btagPNetB",
            "sublead_bjet_btagPNetB",
            "lead_isScEtaEB",
            "sublead_isScEtaEB",
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
                "lead_bjet_pt": tree_["lead_bjet_pt"],
                "lead_bjet_eta": tree_["lead_bjet_eta"],
                "lead_bjet_phi": tree_["lead_bjet_phi"],
                "lead_bjet_mass": tree_["lead_bjet_mass"],
                "sublead_bjet_pt": tree_["sublead_bjet_pt"],
                "sublead_bjet_eta": tree_["sublead_bjet_eta"],
                "sublead_bjet_phi": tree_["sublead_bjet_phi"],
                "sublead_bjet_mass": tree_["sublead_bjet_mass"],
                "lead_pho_pt": tree_["lead_pt"],
                "lead_pho_eta": tree_["lead_eta"],
                "lead_pho_phi": tree_["lead_phi"],
                "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"],
                "sublead_pho_pt": tree_["sublead_pt"],
                "sublead_pho_eta": tree_["sublead_eta"],
                "sublead_pho_phi": tree_["sublead_phi"],
                "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
                "weight_central": tree_["weight_central"],
                "weight": tree_["weight"],
                "lead_bjet_PNetB": tree_["lead_bjet_btagPNetB"],
                "sublead_bjet_PNetB": tree_["sublead_bjet_btagPNetB"],
                "lead_isScEtaEB": tree_["lead_isScEtaEB"],
                "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
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

        cms_events["dibjet_mass"] = dibjet_.mass
        cms_events["dibjet_pt"] = dibjet_.pt
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"] = diphoton_.pt
        cms_events["bbgg_mass"] = (dibjet_ + diphoton_).mass
        cms_events["bbgg_pt"] = (dibjet_ + diphoton_).pt
        cms_events["bbgg_eta"] = (dibjet_ + diphoton_).eta
        cms_events["bbgg_phi"] = (dibjet_ + diphoton_).phi
        # Adding new variables
        cms_events["dibjet_eta"] = dibjet_.eta
        cms_events["dibjet_phi"] = dibjet_.phi
        cms_events["diphoton_eta"] = diphoton_.eta
        cms_events["diphoton_phi"] = diphoton_.phi

        from regions import get_mask_preselection, get_mask_selection

        cms_events["mask_preselection"] = get_mask_preselection(cms_events)
        cms_events["mask_selection"] = get_mask_selection(cms_events)

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
        # Adding new variable
        out_events["dibjet_eta"] = cms_events["dibjet_eta"]
        out_events["dibjet_phi"] = cms_events["dibjet_phi"]
        out_events["diphoton_eta"] = cms_events["diphoton_eta"]
        out_events["diphoton_phi"] = cms_events["diphoton_phi"]

        out_events["lead_bjet_PNetB"] = cms_events["lead_bjet_PNetB"]
        out_events["sublead_bjet_PNetB"] = cms_events["sublead_bjet_PNetB"]

        out_events["preselection"] = cms_events["mask_preselection"]
        out_events["selection"] = cms_events["mask_selection"]

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
    "hist": uproot.recreate(f"{output_dir}/hhbbgg_analyzer-histograms.root"),
    "tree": uproot.recreate(f"{output_dir}/hhbbgg_analyzer-trees.root"),
}


def main():
    for infile_ in inputfiles:
        runOneFile(infile_, outputrootfile)


if __name__ == "__main__":
    main()

# %%
