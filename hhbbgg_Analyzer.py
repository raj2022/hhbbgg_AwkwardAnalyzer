# %%
import os
import uproot
import vector
from ROOT import TFile, gDirectory
import awkward as ak
from config.utils import lVector, VarToHist
from normalisation import  getXsec, getLumi

def runOneFile(inputfile, outputrootfile):
   isdata=False
   if "Data"  in inputfile.split("/")[-1]:
      isdata=True
      xsec_ =  1
      lumi_ = 1
   else:
      xsec_ = getXsec(inputfile)
      lumi_ = getLumi()*1000
   print ("Status of the isdata flag:", isdata)
   mycache = uproot.LRUArrayCache("500 MB")

   file_=uproot.open(inputfile)

   print ("root file opened: ", inputfile)
   print(file_.keys())

   fulltree_=ak.ArrayBuilder()
   niterations=0
   for tree_ in uproot.iterate(file_["DiphotonTree/data_125_13TeV_NOTAG"], ["run", "lumi", "event",
                                    "lead_bjet_pt", "lead_bjet_eta", "lead_bjet_phi", "lead_bjet_mass",
                                    "sublead_bjet_pt", "sublead_bjet_eta", "sublead_bjet_phi", "sublead_bjet_mass",
                                    "lead_pt", "lead_eta", "lead_phi", "lead_mvaID_WP90",
                                    "sublead_pt", "sublead_eta", "sublead_phi", "sublead_mvaID_WP90",
                                    "weight","weight_central",],
                                    step_size=10000
                              ):
      print ("Tree length for iteratiion ", len(tree_), (niterations))
      niterations=niterations+1
      cms_events = ak.zip({"run":tree_["run"],"lumi":tree_["lumi"],"event": tree_["event"],
                           "lead_bjet_pt":tree_["lead_bjet_pt"], "lead_bjet_eta":tree_["lead_bjet_eta"], "lead_bjet_phi":tree_["lead_bjet_phi"], "lead_bjet_mass":tree_["lead_bjet_mass"],
                           "sublead_bjet_pt":tree_["sublead_bjet_pt"], "sublead_bjet_eta":tree_["sublead_bjet_eta"], "sublead_bjet_phi":tree_["sublead_bjet_phi"],"sublead_bjet_mass":tree_["sublead_bjet_mass"],
                           "lead_pho_pt":tree_["lead_pt"], "lead_pho_eta":tree_["lead_eta"], "lead_pho_phi":tree_["lead_phi"], "lead_pho_mvaID_WP90":tree_["lead_mvaID_WP90"],
                           "sublead_pho_pt":tree_["sublead_pt"], "sublead_pho_eta":tree_["sublead_eta"], "sublead_pho_phi":tree_["sublead_phi"],"sublead_pho_mvaID_WP90":tree_["sublead_mvaID_WP90"],
                           "weight_central":tree_["weight_central"],"weight":tree_["weight"]},
                           depth_limit=1
                        )
      out_events = ak.zip({"run":tree_["run"],"lumi":tree_["lumi"],"event": tree_["event"]},depth_limit=1)

      dibjet_ = lVector(cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],cms_events["sublead_bjet_pt"],cms_events["sublead_bjet_eta"],cms_events["sublead_bjet_phi"])
      diphoton_ = lVector(cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],cms_events["sublead_pho_pt"],cms_events["sublead_pho_eta"],cms_events["sublead_pho_phi"])

      cms_events["dibjet_mass"] = dibjet_.mass
      cms_events["diphoton_mass"] = diphoton_.mass
      cms_events["bbgg_mass"] = (dibjet_+diphoton_).mass


      from regions import get_mask_preselection
      cms_events["mask_preselection"]   = get_mask_preselection(cms_events)
      out_events["preselection"] = cms_events["mask_preselection"]
      out_events["lead_pho_pt"] = cms_events["lead_pho_pt"]
      out_events["sublead_pho_pt"] = cms_events["sublead_pho_pt"]
      out_events["dibjet_mass"] = cms_events["dibjet_mass"]
      out_events["diphoton_mass"] = cms_events["diphoton_mass"]
      out_events["bbgg_mass"] = cms_events["bbgg_mass"]
      out_events["weight_central"] = cms_events["weight_central"]
      out_events["weight_preselection"] = cms_events["weight"]*xsec_*lumi_/out_events.weight_central

      fulltree_=ak.concatenate([out_events,fulltree_],axis=0)

   from variables import vardict, regions, variables_common
   from binning import binning
   print ("Making histograms")
   outputrootfileDir =  inputfile.split("/")[-1].replace(".root","")
   for ireg in regions:
      thisregion  = fulltree_[fulltree_[ireg]==True]
      thisregion_ = thisregion[~(ak.is_none(thisregion))]
      weight_ = "weight_"+ireg
      for ivar in variables_common[ireg]:
         hist_name_ = "h_reg_"+ireg+"_"+vardict[ivar]
         outputrootfile[f"{outputrootfileDir}/{hist_name_}"] = VarToHist(thisregion_[ivar], thisregion_[weight_], hist_name_, binning[ireg][ivar])
   print ("Done")

inputfilesDir = '/Users/ptiwari/cmscern/eos/DoNotSync/hhtobbgg/HiggsDNA_root/v1/Run3_2022postEE_merged'
output_dir = "outputfiles"
if not os.path.exists(output_dir):
   os.makedirs(output_dir)

inputfiles = [f"{inputfilesDir}/{infile_}" for infile_ in os.listdir(inputfilesDir) if infile_.endswith('.root')]
outputrootfile = uproot.recreate(f"{output_dir}/hhbbgg_Analyzer.root")

def main():
   for infile_ in inputfiles:
      runOneFile(infile_, outputrootfile)
   # runOneFile(inputfiles[0], outputrootfile)
if __name__ == "__main__":
   main()

# %%
