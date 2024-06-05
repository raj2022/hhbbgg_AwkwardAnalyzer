
import os
import uproot
from ROOT import TFile, gDirectory
import awkward as ak
from config.utils import lVector, VarToHist
from normalisation import  getXsec, getLumi

integrated_luminosities = {
   "Data_EraE": 5.8070,
   "Data_EraF": 17.7819,
   "Data_EraG": 3.0828
}

def runOneFile(inputfile, outputrootfile):
   isdata=False
   if "Data"  in inputfile.split("/")[-1]:
      isdata=True
      xsec_ =  1
      lumi_ = 1
   else:
      xsec_ = getXsec(inputfile)
      lumi_ = getLumi()
   print ("Status of the isdata flag:", isdata)
   mycache = uproot.LRUArrayCache("500 MB")

   file_=uproot.open(inputfile)

   print ("root file opened: ", inputfile)
   print(file_.keys())

   fulltree_=ak.ArrayBuilder()
   niterations=0
   for tree_ in uproot.iterate(file_["DiphotonTree/data_125_13TeV_NOTAG"], ["run", "lumi", "event", "lead_pt", "lead_eta", "lead_phi","sublead_pt", "sublead_eta", "sublead_phi","weight","weight_central",], step_size=50000):
      print ("Tree length for iteratiion ", len(tree_), (niterations))
      niterations=niterations+1
      cms_events = ak.zip({"run":tree_["run"],"lumi":tree_["lumi"],"event": tree_["event"],"lead_pt":tree_["lead_pt"], "lead_eta":tree_["lead_eta"], "lead_phi":tree_["lead_phi"], "sublead_pt":tree_["sublead_pt"], "sublead_eta":tree_["sublead_eta"], "sublead_phi":tree_["sublead_phi"],"weight_central":tree_["weight_central"],"weight":tree_["weight"]},depth_limit=1)
      out_events = ak.zip({"run":tree_["run"],"lumi":tree_["lumi"],"event": tree_["event"]},depth_limit=1)

      diJet_mass = lVector(cms_events["lead_pt"], cms_events["lead_eta"], cms_events["lead_phi"],cms_events["sublead_pt"],cms_events["sublead_eta"],cms_events["sublead_phi"])
      cms_events["dijet_mass"] = diJet_mass

      from regions import get_mask_preselection
      cms_events["mask_preselection"]   = get_mask_preselection(cms_events)

      out_events["weight_preselection"] = cms_events["weight"]
      out_events["dijet_mass"] = cms_events["dijet_mass"]
      out_events["preselection"] = cms_events["mask_preselection"]
      out_events["weight_central"] = cms_events["weight_central"]

      out_events["weight_preselection"] = out_events.weight_preselection*xsec_*lumi_/out_events.weight_central

      fulltree_=ak.concatenate([out_events,fulltree_],axis=0)

   from variables import vardict, regions, variables_common
   from binning import binning
   print ("Making histograms")
   outputrootfile.cd()
   outputrootfileDir =  inputfile.split("/")[-1].replace(".root","")
   gDirectory.mkdir(outputrootfileDir)
   for ireg in regions:
      thisregion  = fulltree_[fulltree_[ireg]==True]
      thisregion_ = thisregion[~(ak.is_none(thisregion))]
      weight_ = "weight_"+ireg
      for ivar in variables_common[ireg]:
         hist_name_ = "h_reg_"+ireg+"_"+vardict[ivar]
         h = VarToHist(thisregion_[ivar], thisregion_[weight_], hist_name_, binning[ireg][ivar])
         outputrootfile.cd(outputrootfileDir)
         h.Write()
   print ("Done")

inputfilesDir = '/Users/ptiwari/cmscern/eos/DoNotSync/hhtobbgg/HiggsDNA_root/v1/Run3_2022postEE_merged'
output_dir = "outputfiles"
if not os.path.exists(output_dir):
   os.makedirs(output_dir)

inputfiles = [f"{inputfilesDir}/{infile_}" for infile_ in os.listdir(inputfilesDir) if infile_.endswith('.root')]
output_rootfile = TFile(f"{output_dir}/hhbbgg_Analyzer.root","RECREATE")

def main():
   for infile_ in inputfiles:
      runOneFile(infile_, output_rootfile)
   # runOneFile(inputfiles[0], output_dir)
if __name__ == "__main__":
   main()
