import os
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import uproot
from hist import Hist
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from normalisation import getLumi
from cycler import cycler

# Load CMS style including color-scheme
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da",
        "#ffa90e",
        "#bd1f01",
        "#94a4a2",
        "#832db6",
        "#a96b59",
        "#e76300",
        "#b9ac70",
        "#717581",
        "#92dadd",
    ]
)
plt.rcParams.update({
    "axes.labelsize": 16,  # X/Y labels size
    "axes.titlesize": 20,  # Title size
    "xtick.labelsize": 14,  # X-axis tick label size
    "ytick.labelsize": 14,  # Y-axis tick label size
    "legend.fontsize": 14,  # Legend font size
    "figure.figsize": (10, 8),  # Figure size
    "lines.linewidth": 2.5,  # Line width
    "axes.edgecolor": "black",  # Make axes edges black
    "axes.linewidth": 1.5,  # Thicker axes
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

# Function to read histograms and normalize them
def get_histogram(file, hist_name):
    histogram = file[hist_name].to_hist()
    
    # Normalize the histogram by its integral
    integral = np.sum(histogram.values())
    if integral > 0:
        histogram = histogram / integral
    
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
    
    # Add "CMS Preliminary" and integrated luminosity outside the plot box
    hep.cms.text("CMS Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=17,
             transform=plt.gca().transAxes, ha='right')

    plt.savefig(output_name)
    plt.close()

# Function to plot signal efficiency for a fixed X
def plot_signal_efficiency(root_file, X_value, Y_values):
    efficiency = []
    for Y_value in Y_values:
        mass_point = f"NMSSM_X{X_value}_Y{Y_value}"
        hist_name = f"{mass_point}/preselection-dibjet_pt"
        hist = get_histogram(root_file, hist_name)
        
        # Calculate total integral for all Y values
        total_integral = sum(np.sum(get_histogram(root_file, f"NMSSM_X{X_value}_Y{y}/preselection-dibjet_pt").values()) for y in Y_values)
        
        # Calculate efficiency for this Y
        integral = np.sum(hist.values())
        if total_integral > 0:
            eff = integral / total_integral
        else:
            eff = 0
        
        efficiency.append((Y_value, eff))
    
    # Plot efficiency vs. Y
    Y_values, eff_values = zip(*efficiency)
    plt.figure(figsize=(10, 8))
    plt.plot(Y_values, eff_values, marker='o', linestyle='-', color='b')
    plt.xlabel("Y value")
    plt.ylabel("Signal Efficiency")
    plt.title(f"Signal Efficiency for X={X_value}")
    plt.grid(True)
    
    # Add "CMS Preliminary" and integrated luminosity outside the plot box
    hep.cms.text("CMS Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=17,
             transform=plt.gca().transAxes, ha='right')

    output_name = f"stack_plots/signal_efficiency_X{X_value}.png"
    plt.savefig(output_name)
    plt.close()

# Define the X and Y values and variables to process
X_values = [300, 400, 500, 550, 600, 650, 700]
Y_values = [60, 70, 80, 90, 95, 100]

# Ensure the output directory exists
output_dir = "stack_plots/"
os.makedirs(output_dir, exist_ok=True)

# Load the ROOT file
file_path = "outputfiles/hhbbgg_analyzerNMSSM-histograms.root"
root_file = uproot.open(file_path)

# Loop through each X value and plot the signal efficiency
for X_value in X_values:
    plot_signal_efficiency(root_file, X_value, Y_values)

