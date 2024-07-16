import pickle
from ROOT import TFile
from root_pandas import read_root

def addbdtscore(infile,tree):
    ifile = open("discriminator_resolved.pickle")
    model = pickle.load(ifile)

    # vars_to_load_ = ['MET','METSig','Jet1Pt', 'Jet1Eta', 'Jet1Phi','Jet2Pt', 'Jet2Eta', 'Jet2Phi','DiJetMass','DiJetPt', 'DiJetEta','DiJetPhi','nJets','met_Phi']
    vars_to_load = ['MET', 'METPhi', 'pfMetCorrSig', 'Jet1Pt', 'Jet1Eta', 'Jet1Phi', 'Jet1deepCSV', 'Jet2Pt', 'Jet2Eta', 'Jet2Phi','Jet2deepCSV', 'Jet3Pt', 'Jet3Eta', 'Jet3Phi', 'Jet3deepCSV', 'dRJet12','dPhiJet12', 'dEtaJet12', 'M_Jet1Jet2', 'pT_Jet1Jet2', 'eta_Jet1Jet2', 'phi_Jet1Jet2', 'prod_cat', 'Njets_PassID','M_Jet1Jet3', 'dPhiJet13', 'JetHT', 'rJet1PtMET', 'ratioPtJet21', 'dPhi_jetMET']
    
    if not ("SR" in tree or "SBand" in tree):vars_to_load_[0]="RECOIL"
    df = read_root(infile,tree,columns=vars_to_load_)
    #df=df[vars_to_load_]
    print df[:1]
    out=model.decision_function(df).ravel()
    
    print out[:10]
    return out
