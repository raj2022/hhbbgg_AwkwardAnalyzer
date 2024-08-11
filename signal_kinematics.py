# Singal kinematics 
#Plot mass and pt for each mass point. Kinematics for each mass point.
#Compare shape and the normalisation(nomal histogram" histogram by total integral, make the area under the histograms as 1
#  For each X make the plot of two variables : mass and  pt
#	This will have many Y points (60,70,80,90,95,100).
#	For X=300,Y=60 and then divide by its own integral to get the shape. Divide by weight central
#
#Do it similarly for All mass point
#
#Signal efficiency: instead of diving the histogram by own integral divide by integral of all. Focus on Mass of X(Mjj) or take pt(mgg)
#X =300 y=60 signal sample. 


import os
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import matplotlib
import uproot
from hist import Hist
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler
from normalisation import getLumi

# Fix disk quota error for matplotlib
matplotlib.use("Agg")

# Load CMS style including color-scheme
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2",
        "#832db6", "#a96b59", "#e76300", "#b9ac70",
        "#717581", "#92dadd",
    ]
)
plt.rcParams.update({
    "axes.labelsize": 16,
    "axes.titlesize": 20,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "figure.figsize": (10, 8),
    "lines.linewidth": 2.5,
    "axes.edgecolor": "black",
    "axes.linewidth": 1.5,
})

# Legend label formatting
legend_labels = {
    "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
    "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
    "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
    "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
    "diphoton_pt": r"$p_{T}^{\gamma\gamma}$ [GeV]",
    "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
}

# Function to read and normalize histograms
def get_histogram(file, hist_name, hist_label=None):
    histogram = file[hist_name].to_hist()
    integral = np.sum(histogram.values())
    if integral > 0:
        histogram = histogram / integral
    if hist_label is not None:
        histogram.label = hist_label
    return histogram

# Function to plot histograms
def plot_histograms(histograms, xlabel, ylabel, output_name):
    plt.figure(figsize=(10, 8))
    for hist in histograms:
        plt.step(hist.axes.centers[0], hist.values(), where="mid", label=legend_labels.get(hist.label, hist.label))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    hep.cms.text("CMS Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=17, transform=plt.gca().transAxes, ha='right')
    plt.savefig(output_name)
    plt.close()

# Function to process a mass point
def process_mass_point(root_file, mass_point, variables):
    histograms = []
    for variable in variables:
        hist_name = f"{mass_point}/preselection-{variable}"
        hist = get_histogram(root_file, hist_name, f"{mass_point} {variable}")
        histograms.append(hist)
    return histograms

# Function to process and plot for each X with varying Y
def process_X_group(root_file, X_value, Y_values, variables):
    for variable in variables:
        histograms = []
        for Y_value in Y_values:
            mass_point = f"NMSSM_X{X_value}_Y{Y_value}"
            hist_name = f"{mass_point}/preselection-{variable}"
            hist = get_histogram(root_file, hist_name, f"Y={Y_value}")
            histograms.append(hist)
        output_name = f"stack_plots/NMSSM_X{X_value}_{variable}.png"
        plot_histograms(histograms, f"{legend_labels[variable]}", "Entries", output_name)

# Define the mass points in the ROOT file and variables to process
mass_points = [
    "NMSSM_X300_Y100", "NMSSM_X400_Y80", "NMSSM_X550_Y100", "NMSSM_X600_Y80", "NMSSM_X700_Y100",
    "NMSSM_X300_Y60", "NMSSM_X400_Y90", "NMSSM_X550_Y60", "NMSSM_X600_Y90", "NMSSM_X700_Y60",
    "NMSSM_X300_Y70", "NMSSM_X400_Y95", "NMSSM_X550_Y70", "NMSSM_X600_Y95", "NMSSM_X700_Y70",
    "NMSSM_X300_Y80", "NMSSM_X500_Y100", "NMSSM_X550_Y80", "NMSSM_X650_Y100", "NMSSM_X700_Y80",
    "NMSSM_X300_Y90", "NMSSM_X500_Y60", "NMSSM_X550_Y90", "NMSSM_X650_Y60", "NMSSM_X700_Y90",
    "NMSSM_X300_Y95", "NMSSM_X500_Y70", "NMSSM_X550_Y95", "NMSSM_X650_Y70", "NMSSM_X700_Y95",
    "NMSSM_X400_Y100", "NMSSM_X500_Y80", "NMSSM_X600_Y100", "NMSSM_X650_Y80", "NMSSM_X400_Y60",
    "NMSSM_X500_Y90", "NMSSM_X600_Y60", "NMSSM_X650_Y90", "NMSSM_X400_Y70", "NMSSM_X500_Y95",
    "NMSSM_X600_Y70", "NMSSM_X650_Y95"
]

variables = [
    "dibjet_pt",
    "dibjet_mass",
    "diphoton_mass",
    "diphoton_pt",
    "bbgg_mass",
    "bbgg_pt",
]

X_values = [300, 400, 500, 550, 600, 650, 700]
Y_values = [60, 70, 80, 90, 95, 100]

# Ensure the output directory exists
output_dir = "stack_plots/"
os.makedirs(output_dir, exist_ok=True)

# Load the ROOT file
file_path = "outputfiles/hhbbgg_analyzerNMSSM-histograms.root"
root_file = uproot.open(file_path)

# Process and plot for each mass point and each X with varying Y
for mass_point in mass_points:
    for variable in variables:
        histograms = process_mass_point(root_file, mass_point, [variable])
        output_name = f"{output_dir}{mass_point}_{variable}.png"
        plot_histograms(histograms, f"{legend_labels[variable]}", "Entries", output_name)

# Process and plot for each X with varying Y
for X_value in X_values:
    process_X_group(root_file, X_value, Y_values, variables)

