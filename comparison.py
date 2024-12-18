import os
import pandas as pd
import uproot
import matplotlib.pyplot as plt

# V1 file
v1_signal_sample_NMSSM_X300 = [("../../output_root/NMSSM/NMSSM_X300_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_signal_sample_NMSSM_X400 = [("../../output_root/NMSSM/NMSSM_X400_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_signal_sample_NMSSM_X500 = [("../../output_root/NMSSM/NMSSM_X500_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_signal_sample_NMSSM_X600 = [("../../output_root/NMSSM/NMSSM_X600_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_signal_sample_NMSSM_X700 = [("../../output_root/NMSSM/NMSSM_X700_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]

v1_data_sample_EraE = [("../../output_root/Data_EraE.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_data_sample_EraF  = [("../../output_root/Data_EraF.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v1_data_sample_EraG  = [("../../output_root/Data_EraG.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
#v1_signal_sample_NMSSM_X1200 = [("outputfiles/hhbbgg_analyzer-trees.root", "/NMSSM_X1200_Y60/preselection")]
## V2 files  ../../output_root/NMSSM/
v2_signal_sample_NMSSM_X300 = [("../../output_root/v1_v2_comparison/NMSSM_X300_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_signal_sample_NMSSM_X400 = [("../../output_root/v1_v2_comparison/NMSSM_X400_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_signal_sample_NMSSM_X500 = [("../../output_root/v1_v2_comparison/NMSSM_X500_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_signal_sample_NMSSM_X600 = [("../../output_root/v1_v2_comparison/NMSSM_X600_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_signal_sample_NMSSM_X700 = [("../../output_root/v1_v2_comparison/NMSSM_X700_Y60.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
#v2_signal_sample_NMSSM_X300 = [("outputfiles/hhbbgg_analyzer_v2-trees.root", "/NMSSM_X300_Y60/preselection")]
v2_data_sample_EraE = [("../../output_root/v2_production/backgrounds/Data_EraE.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_data_sample_EraF  = [("../../output_root/v2_production/backgrounds/Data_EraF.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
v2_data_sample_EraG  = [("../../output_root/v2_production/backgrounds/Data_EraG.root", "DiphotonTree/data_125_13TeV_NOTAG/")]
#v2_signal_sample_NMSSM_X600 = [("outputfiles/hhbbgg_analyzer_v2-trees.root", "/NMSSM_X600_Y60/preselection")]
#v2_signal_sample_NMSSM_X800 = [("outputfiles/hhbbgg_analyzer_v2-trees.root", "/NMSSM_X800_Y60/preselection")]
#v2_signal_sample_NMSSM_X1000 = [("outputfiles/hhbbgg_analyzer_v2-trees.root", "/NMSSM_X1000_Y60/preselection")]
#v2_signal_sample_NMSSM_X1200 = [("outputfiles/hhbbgg_analyzer_v2-trees.root", "/NMSSM_X1200_Y60/preselection")]
# Columns to be loaded
keys = [
    'pt', 'Res_dijet_pt', 'dijet_pt', 'jet1_pt', 'diphoton_pt', 'bbgg_pt', 'bbgg_eta', 'bbgg_phi',
    'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi', 'diphoton_eta',
    'diphoton_phi', 'dibjet_eta', 'dibjet_phi', 'lead_bjet_pt', 'sublead_bjet_pt',
    'lead_bjet_eta', 'lead_bjet_phi', 'sublead_bjet_eta', 'sublead_bjet_phi',
    'sublead_bjet_PNetB', 'lead_bjet_PNetB', 'CosThetaStar_gg', 'CosThetaStar_jj',
    'CosThetaStar_CS', 'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    'weight_preselection', 'bbgg_mass', 'FirstJet_PtOverM', 'SecondJet_PtOverM',
    'diphoton_bbgg_mass', 'dibjet_bbgg_mass', 'lead_pho_eta', 'lead_pho_mvaID', 'sublead_pho_mvaID',
]

# Function to load the number of events and plot the data for a specific variable
def load_and_plot(file_key_list, variable):
    for file, key in file_key_list:
        try:
            with uproot.open(file) as f:
                tree = f[key]  # Access the tree at the specified key

                # Get the number of events
                num_events = tree.num_entries
                print(f"File: {file}, Key: {key}, Number of events: {num_events}")

                # Extract the variable data
                data = tree[variable].array(library="np")  # Returns a numpy array

                # Plot the variable data
                plt.figure(figsize=(8, 6))
                plt.hist(data, bins=50, range=(data.min(), data.max()), histtype='step', linestyle='-', color='blue')
                plt.title(f"Histogram of {variable} for {file}")
                plt.xlabel(variable)
                plt.ylabel("Frequency")
                plt.grid(True)
                plt.show()

        except Exception as e:
            print(f"Error loading {file} with key {key} or reading variable {variable}: {e}")

# Example usage for plotting 'dibjet_pt' for each sample

# Load and plot for v1 signal samples
load_and_plot(v1_signal_sample_NMSSM_X300, 'pt')
load_and_plot(v1_signal_sample_NMSSM_X400, 'pt')
load_and_plot(v1_signal_sample_NMSSM_X500, 'pt')
load_and_plot(v1_signal_sample_NMSSM_X600, 'pt')
load_and_plot(v1_signal_sample_NMSSM_X700, 'pt')

# Load and plot for v1 data samples
load_and_plot(v1_data_sample_EraE, 'pt')
load_and_plot(v1_data_sample_EraF, 'pt')
load_and_plot(v1_data_sample_EraG, 'pt')

# Load and plot for v2 signal samples

load_and_plot(v2_signal_sample_NMSSM_X300, 'pt')
load_and_plot(v2_signal_sample_NMSSM_X400, 'pt')
load_and_plot(v2_signal_sample_NMSSM_X500, 'pt')
load_and_plot(v2_signal_sample_NMSSM_X600, 'pt')
load_and_plot(v2_signal_sample_NMSSM_X700, 'pt')
## Load and plot for v2 data samples
#
load_and_plot(v2_data_sample_EraE, 'pt')
load_and_plot(v2_data_sample_EraF, 'pt')
load_and_plot(v2_data_sample_EraG, 'pt')



