import uproot
import pandas as pd


from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score




file_path = '../outputfiles/hhbbgg_analyzer-histograms.root'

sig_treename = 'GluGluToHH'
bkg_treename_1 = 'GGJets'
bkg_treename_2 = 'GJetPt20To40'
bkg_treename_3 = 'GJetPt40'

# keys
keys = [
    'srbbgg-dibjet_mass',
    'srbbgg-diphoton_mass',
    'srbbgg-bbgg_mass',
    'srbbgg-dibjet_pt',
    'srbbgg-diphoton_pt',
    'srbbgg-bbgg_pt',
    'srbbgg-lead_pho_pt',
    'srbbgg-sublead_pho_pt',
    'srbbgg-bbgg_eta',
    'srbbgg-bbgg_phi',
    'srbbgg-lead_pho_eta',
    'srbbgg-lead_pho_phi',
    'srbbgg-sublead_pho_eta',
    'srbbgg-sublead_pho_phi',
    'srbbgg-diphoton_eta',
    'srbbgg-diphoton_phi',
    'srbbgg-dibjet_eta',
    'srbbgg-dibjet_phi',
    'srbbgg-lead_bjet_pt',
    'srbbgg-sublead_bjet_pt',
    'srbbgg-lead_bjet_eta',
    'srbbgg-lead_bjet_phi',
    'srbbgg-sublead_bjet_eta',
    'srbbgg-sublead_bjet_phi',
    'srbbgg-sublead_bjet_PNetB',
    'srbbgg-lead_bjet_PNetB',
    'srbbgg-CosThetaStar_gg',
    'srbbgg-CosThetaStar_jj',
    'srbbgg-CosThetaStar_CS',
    'srbbgg-DeltaR_jg_min',
    'srbbgg-pholead_PtOverM',
    'srbbgg-phosublead_PtOverM',
    'srbbgg-FirstJet_PtOverM',
    'srbbgg-SecondJet_PtOverM',
    'srbbgg-lead_pt_over_diphoton_mass',
    'srbbgg-sublead_pt_over_diphoton_mass',
    'srbbgg-lead_pt_over_dibjet_mass',
    'srbbgg-sublead_pt_over_dibjet_mass',
    'srbbgg-diphoton_bbgg_mass',
    'srbbgg-dibjet_bbgg_mass',
]

file = uproot.open(file_path)

dfs = {}

def read_histograms(treename):
    tree_dfs = {}
    for branch in keys:
        full_key = f"{treename}/{branch}"
        # Check if the key exists in the file
        if full_key in file:
            hist = file[full_key]
            values, _ = hist.to_numpy()  # Extract the histogram contents
            df = pd.DataFrame(values, columns=[branch])
            tree_dfs[branch] = df
        else:
            print(f"{full_key} not found in the file.")
    return tree_dfs

dfs['signal'] = read_histograms(sig_treename)

# Leave background histograms as they are
dfs[bkg_treename_1] = read_histograms(bkg_treename_1)
dfs[bkg_treename_2] = read_histograms(bkg_treename_2)
dfs[bkg_treename_3] = read_histograms(bkg_treename_3)



#for treename, tree_dfs in dfs.items():
#    print(f"\nDataFrames for tree: {treename}")
#    for key, df in tree_dfs.items():
#        print(f"\nDataFrame for {key}:")
#        print(df)
#


#print("\nDataFrame for signal:")
#print(dfs['signal'])



signal_df = dfs['signal']
background_df = dfs[bkg_treename_1]


combined_df = pd.concat([signal_df, background_df], ignore_index=True)


features = [
    'srbbgg-diphoton_mass',
    'srbbgg-dibjet_mass',
    'srbbgg-lead_pho_pt',
    # Add more features as needed
]


X = combined_df[features]
y = combined_df['label']


