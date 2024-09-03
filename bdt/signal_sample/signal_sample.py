# signal with similar kinematics and training
import os
import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, roc_curve, auc
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import matplotlib.pyplot as plt
import seaborn as sns
from torchsummary import summary

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


# file path
signal_files_lowX_lowY = [
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y60/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y70/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y60/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y70/preselection"),
]
background=[
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GJetPt40/preselection")
]


keys = [
#     'dibjet_mass',
    # 'diphoton_mass',
    'bbgg_mass',
    'dibjet_pt',
    'diphoton_pt',
    'bbgg_pt',
    # 'lead_pho_pt',
    # 'sublead_pho_pt',
    'bbgg_eta',
    'bbgg_phi',
    'lead_pho_eta',
    'lead_pho_phi',
    'sublead_pho_eta',
    'sublead_pho_phi',
    'diphoton_eta',
    'diphoton_phi',
    'dibjet_eta',
    'dibjet_phi',
    'lead_bjet_pt',
    'sublead_bjet_pt',
    'lead_bjet_eta',
    'lead_bjet_phi',
    'sublead_bjet_eta',
    'sublead_bjet_phi',
    'sublead_bjet_PNetB',
    'lead_bjet_PNetB',
    'CosThetaStar_gg',
    'CosThetaStar_jj',
    'CosThetaStar_CS',
    'DeltaR_jg_min',
    'pholead_PtOverM',
    'phosublead_PtOverM',
    'FirstJet_PtOverM',
    'SecondJet_PtOverM',
    # 'lead_pt_over_diphoton_mass',
    # 'sublead_pt_over_diphoton_mass',
    # 'lead_pt_over_dibjet_mass',
    # 'sublead_pt_over_dibjet_mass',
    'diphoton_bbgg_mass',
    'dibjet_bbgg_mass',
    # 'weight_preselection',
    'weight_preselection',
]




dfs = {}


# Loop through each file and load the corresponding dataframe
for file, key in files:
    with uproot.open(file) as f:
        dfs[key] = f[key].arrays(keys, library="pd")



signal_df_1 = dfs["/NMSSM_X300_Y60/preselection"]
signal_df_2 = dfs["/NMSSM_X300_Y70/preselection"]
signal_df_3 = dfs["/NMSSM_X400_Y60/preselection"]
signal_df_4 = dfs["/NMSSM_X400_Y70/preselection"]


background_df_1 = dfs["/GGJets/preselection"]
background_df_1 = dfs["/GGJets/preselection"]
background_df_2 = dfs["/GJetPt20To40/preselection"]
background_df_3 = dfs["/GJetPt40/preselection"]

print(f'----------------------------------------------')
print('========printing Signal samples=======')
print('singal df NMSSM_X300_Y60', signal_df_1.shape)
print('singal df NMSSM_X300_Y70', signal_df_2.shape)
print('singal df NMSSM_X400_Y60', signal_df_3.shape)
print('singal df NMSSM_X400_Y70', signal_df_4.shape)

print(f'----------------------------------------------')
print('========printing Background samples=======')
print('background_df_1 ', background_df_1.shape)
print('background_df_2', background_df_2.shape)
print('background_df_3 ', background_df_3.shape)

print("Total Background")
background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)
print('background_df', background_df.shape)

background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)
print('background_df', background_df.shape)

print('===============================================')
print("Total background shape", background_df.shape)
print("Total signal shape", signal_df.shape)

