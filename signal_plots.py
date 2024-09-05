import os
import sys
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
sys.path.append("../hhbbgg_AwkwardAnalyzer")
import matplotlib
import uproot
from hist import Hist
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler
from normalisation import getLumi

matplotlib.use("Agg")
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2",
        "#832db6", "#a96b59", "#e76300", "#b9ac70",
        "#717581", "#92dadd",
    ]
)

plt.rcParams.update({
    "axes.labelsize": 22,
    "axes.titlesize": 22,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "xtick.major.width": 2.0,
    "ytick.major.width": 2.0,
    "xtick.minor.width": 1.5,
    "ytick.minor.width": 1.5,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "legend.fontsize": 16,
    "figure.figsize": (12, 10),
    "lines.linewidth": 3.5,
    "axes.edgecolor": "black",
    "axes.linewidth": 2.0,
    "grid.color": "black",
    "grid.linestyle": "-",
    "grid.linewidth": 0.1,
    "axes.labelweight": "bold",
})

legend_labels = {
    "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
    "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
    "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
    "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
    "diphoton_pt": r"$p_{T}^{\gamma\gamma}$ [GeV]",
    "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
}

variables = [
    "dibjet_pt",
    "dibjet_mass",
    "diphoton_mass",
    "diphoton_pt",
    "bbgg_mass",
    "bbgg_pt",
]

# Define X and Y ranges for each category
low_X_values = [300, 400]
low_Y_values = [60, 70]

mid_X_values = [500, 550]
mid_Y_values = [80, 90]

high_X_values = [600, 650, 700]
high_Y_values = [95, 100]

# Combinations of X and Y ranges for 9 combinations
combinations = {
    "lowX_lowY": {"X_values": low_X_values, "Y_values": low_Y_values},
    "lowX_midY": {"X_values": low_X_values, "Y_values": mid_Y_values},
    "lowX_highY": {"X_values": low_X_values, "Y_values": high_Y_values},
    "midX_lowY": {"X_values": mid_X_values, "Y_values": low_Y_values},
    "midX_midY": {"X_values": mid_X_values, "Y_values": mid_Y_values},
    "midX_highY": {"X_values": mid_X_values, "Y_values": high_Y_values},
    "highX_lowY": {"X_values": high_X_values, "Y_values": low_Y_values},
    "highX_midY": {"X_values": high_X_values, "Y_values": mid_Y_values},
    "highX_highY": {"X_values": high_X_values, "Y_values": high_Y_values},
}

def get_histogram(file, hist_name, hist_label=None, normalize=False):
    try:
        histogram = file[hist_name].to_hist()
    except KeyError:
        print(f"Histogram {hist_name} not found in file.")
        return None
    if normalize:
        integral = np.sum(histogram.values())
        if integral > 0:
            histogram = histogram / integral
    if hist_label is not None:
        histogram.label = hist_label
    return histogram

def plot_histograms(histograms, xlabel, ylabel, output_name, x_limits=None):
    plt.figure(figsize=(10, 8))
    for hist in histograms:
        if hist is not None:
            plt.step(hist.axes.centers[0], hist.values(), where="mid", label=legend_labels.get(hist.label, hist.label))
    plt.xlabel(xlabel, fontsize=20)
    plt.ylabel(ylabel, fontsize=20)
    if x_limits:
        plt.xlim(x_limits)
    plt.legend()
    plt.grid(True)
    hep.cms.text("Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=18, transform=plt.gca().transAxes, ha='right')
    plt.savefig(output_name)
    plt.close()

x_axis_limits = {
    "dibjet_mass": (50, 200),
    "diphoton_mass": (50, 180),
    "bbgg_mass": (150, 800),
    "dibjet_pt": (30, 500),
    "diphoton_pt": (30, 500),
    "bbgg_pt": (50, 1000),
}

def process_X_group(root_file, X_value, Y_values, variables, output_dir, normalize=False):
    for variable in variables:
        histograms = []
        for Y_value in Y_values:
            mass_point = f"NMSSM_X{X_value}_Y{Y_value}"
            hist_name = f"{mass_point}/preselection-{variable}"
            hist = get_histogram(root_file, hist_name, f"Y={Y_value}", normalize=normalize)
            histograms.append(hist)
        suffix = "_normalized" if normalize else ""
        plot_histograms(histograms, f"{legend_labels[variable]}", "Entries", f"{output_dir}/NMSSM_X{X_value}_{variable}.png", x_limits=x_axis_limits.get(variable))

def process_mass_point(root_file, mass_point, variables):
    histograms = []
    for variable in variables:
        hist_name = f"{mass_point}/preselection-{variable}"
        unnormalized_hist = get_histogram(root_file, hist_name, f"{mass_point} {variable}", normalize=False)
        normalized_hist = get_histogram(root_file, hist_name, f"{mass_point} {variable}", normalize=True)
        if unnormalized_hist is not None:
            histograms.append((unnormalized_hist, normalized_hist))
    return histograms

def plot_both_histograms(histograms, variable, mass_point, output_dirs, x_limits=None):
    unnormalized_output_dir, normalized_output_dir = output_dirs
    for unnormalized_hist, normalized_hist in histograms:
        if unnormalized_hist is not None:
            unnormalized_output = f"{unnormalized_output_dir}{mass_point}_{variable}_unnormalized.png"
            normalized_output = f"{normalized_output_dir}{mass_point}_{variable}_normalized.png"
            plot_histograms([unnormalized_hist], f"{legend_labels[variable]}", "Entries", unnormalized_output, x_limits)
            plot_histograms([normalized_hist], f"{legend_labels[variable]}", "Entries (Normalized)", normalized_output, x_limits)

# Define base output directories
base_output_dir = "stack_plots/"

file_path = "outputfiles/hhbbgg_analyzerNMSSM-histograms.root"
root_file = uproot.open(file_path)


# Process and plot for each X-Y combination
for combination_name, config in combinations.items():
    unnormalized_output_dir = f"{base_output_dir}/{combination_name}/unnormalized/"
    normalized_output_dir = f"{base_output_dir}/{combination_name}/normalized/"
    
    os.makedirs(unnormalized_output_dir, exist_ok=True)
    os.makedirs(normalized_output_dir, exist_ok=True)
    
    # Loop through each X value and corresponding Y values to create histograms
    for X_value in config["X_values"]:
        process_X_group(
            root_file=root_file,
            X_value=X_value,
            Y_values=config["Y_values"],
            variables=variables,
            output_dir=unnormalized_output_dir,
            normalize=False
        )
        process_X_group(
            root_file=root_file,
            X_value=X_value,
            Y_values=config["Y_values"],
            variables=variables,
            output_dir=normalized_output_dir,
            normalize=True
        )

print("All plots have been generated and saved in their respective directories.")

