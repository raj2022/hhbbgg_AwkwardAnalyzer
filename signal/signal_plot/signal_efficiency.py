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
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
        "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"
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

# Function to read histograms without normalizing
def get_histogram(file, hist_name):
    return file[hist_name].to_hist()

# Preload all histograms to avoid repeated file reads
def get_all_histograms(root_file, X_values, Y_values):
    histograms = {}
    for X_value in X_values:
        histograms[X_value] = {}
        for Y_value in Y_values:
            hist_name = f"NMSSM_X{X_value}_Y{Y_value}/preselection-dibjet_pt"
            histograms[X_value][Y_value] = get_histogram(root_file, hist_name)
    return histograms

# Function to plot signal efficiency for each X value
def plot_signal_efficiency(histograms, X_value, Y_values):
    efficiency = []
    total_integral = sum(np.sum(histograms[X_value][y].values()) for y in Y_values)

    for Y_value in Y_values:
        integral = np.sum(histograms[X_value][Y_value].values())
        eff = integral / total_integral if total_integral > 0 else 0
        print(f"Integral for NMSSM_X{X_value}_Y{Y_value}: {integral}")
        print(f"Normalized Efficiency for Y={Y_value}: {eff}")
        efficiency.append((Y_value, eff))

    # Plot efficiency vs. Y values
    Y_vals, eff_vals = zip(*efficiency)
    plt.figure(figsize=(10, 8))
    plt.plot(Y_vals, eff_vals, marker='o', linestyle='-', color='b', label=f'$m_X$={X_value} GeV')
    plt.xlabel("$m_Y$ [GeV]")
    plt.ylabel("Signal Efficiency")
    plt.xlim(0, 130)  # Set x-axis limit to 130
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')

    # Add CMS Preliminary and integrated luminosity
    hep.cms.text("Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=17, transform=plt.gca().transAxes, ha='right')

    # Add legend and save the plot
    plt.legend(loc='best')
    output_name = f"stack_plots/signal_efficiency_X{X_value}.png"
    plt.savefig(output_name)
    plt.close()

# Function to plot combined signal efficiency for all X values
def plot_combined_signal_efficiency(histograms, X_values, Y_values):
    plt.figure(figsize=(10, 8))

    for X_value in X_values:
        efficiency = []
<<<<<<< HEAD:signal_efficiency.py
        total_integral = sum(np.sum(histograms[X_value][y].values()) for y in Y_values)

        for Y_value in Y_values:
            integral = np.sum(histograms[X_value][Y_value].values())
            eff = integral / total_integral if total_integral > 0 else 0
            efficiency.append((Y_value, eff))

        Y_vals, eff_vals = zip(*efficiency)
        plt.plot(Y_vals, eff_vals, marker='o', linestyle='-', label=f'$m_X={X_value}$ GeV')
=======

        for Y_value in Y_values:
            hist_name = f"NMSSM_X{X_value}_Y{Y_value}/preselection-dibjet_pt"
            hist = get_histogram(root_file, hist_name)

            # Calculate integral of the histogram
            integral = np.sum(hist.values())

            # Calculate efficiency (relative to total integral for this X value)
            total_integral = sum(np.sum(get_histogram(root_file, f"NMSSM_X{X_value}_Y{y}/preselection-dibjet_pt").values()) for y in Y_values)
            if total_integral > 0:
                eff = integral / total_integral
            else:
                eff = 0

            efficiency.append((Y_value, eff))

        # Plot efficiency vs. Y for this X value
        Y_values, eff_values = zip(*efficiency)
        plt.plot(Y_values, eff_values, marker='o', linestyle='-', label=f'$m_X={X_value}$ GeV')
>>>>>>> 12aab03 (oprganised and added variable kinematics):signal/signal_efficiency.py

    plt.xlabel("$m_Y$ (GeV)")
    plt.ylabel("Signal Efficiency")
    plt.xlim(0, 130)  # Set x-axis limit to 130
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')

    # Add CMS Preliminary and integrated luminosity
    hep.cms.text("Preliminary", loc=0, ax=plt.gca())
    plt.text(1.0, 1.02, f'{getLumi():.1f} fb$^{{-1}}$ (13 TeV)', fontsize=17, transform=plt.gca().transAxes, ha='right')

    # Add legend and save the plot
    plt.legend(loc='best')
    output_name = "stack_plots/combined_signal_efficiency.png"
    plt.savefig(output_name)
    plt.savefig(output_name.replace(".png", ".pdf"))
    plt.close()

# Define the X and Y values
X_values = [300, 400, 500, 550, 600, 650, 700]
Y_values = [60, 70, 80, 90, 95, 100, 125]

# Ensure the output directory exists
output_dir = "stack_plots/"
os.makedirs(output_dir, exist_ok=True)

# Load the ROOT file and histograms
file_path = "outputfiles/hhbbgg_analyzerNMSSM-histograms.root"
root_file = uproot.open(file_path)
histograms = get_all_histograms(root_file, X_values, Y_values)

# Loop through each X value and plot signal efficiency
for X_value in X_values:
    plot_signal_efficiency(histograms, X_value, Y_values)

# Plot combined signal efficiency for all X values
plot_combined_signal_efficiency(histograms, X_values, Y_values)

