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

X_values = [300, 400, 500, 550, 600, 650, 700]
Y_values = [60, 70, 80, 90, 95, 100]
variables = [
    "dibjet_pt",
    "dibjet_mass",
    "diphoton_mass",
    "diphoton_pt",
    "bbgg_mass",
    "bbgg_pt",
]

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

def plot_combined_histograms(histograms, xlabel, ylabel, output_name, x_limits=None, log_scale=False):
    plt.figure(figsize=(12, 10))
    for hist in histograms:
        if hist is not None:
            plt.step(hist.axes.centers[0], hist.values(), where="mid", label=legend_labels.get(hist.label, hist.label))
    plt.xlabel(xlabel, fontsize=20)
    plt.ylabel(ylabel, fontsize=20)
    if x_limits:
        plt.xlim(x_limits)
    if log_scale:
        plt.yscale('log')
    plt.legend()
    plt.grid(True, which='both', linestyle='-', linewidth=0.1)
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

def process_X_group(root_file, X_value, Y_values, variables, output_dirs, normalize=False, log_scale=False):
    for variable in variables:
        histograms = []
        for Y_value in Y_values:
            mass_point = f"NMSSM_X{X_value}_Y{Y_value}"
            hist_name = f"{mass_point}/preselection-{variable}"
            hist = get_histogram(root_file, hist_name, f"Y={Y_value}", normalize=normalize)
            histograms.append(hist)
        suffix = "_normalized" if normalize else "_unnormalized"
        log_suffix = "_log" if log_scale else ""
        plot_combined_histograms(histograms, f"{legend_labels[variable]}", "Entries" if not normalize else "Entries (Normalized)", f"{output_dirs}{X_value}_{variable}{suffix}{log_suffix}.png", x_limits=x_axis_limits.get(variable), log_scale=log_scale)

output_dir = "stack_plots/combined_plots/"
unnormalized_output_dir = f"{output_dir}/unnormalized/"
normalized_output_dir = f"{output_dir}/normalized/"
log_scaled_output_dir = f"{output_dir}/log_scaled/"

os.makedirs(unnormalized_output_dir, exist_ok=True)
os.makedirs(normalized_output_dir, exist_ok=True)
os.makedirs(log_scaled_output_dir, exist_ok=True)

file_path = "outputfiles/hhbbgg_analyzerNMSSM-histograms.root"
root_file = uproot.open(file_path)

for X_value in X_values:
    process_X_group(root_file, X_value, Y_values, variables, unnormalized_output_dir, normalize=False)
    process_X_group(root_file, X_value, Y_values, variables, normalized_output_dir, normalize=True)
    process_X_group(root_file, X_value, Y_values, variables, log_scaled_output_dir, normalize=False, log_scale=True)
    process_X_group(root_file, X_value, Y_values, variables, log_scaled_output_dir, normalize=True, log_scale=True)

