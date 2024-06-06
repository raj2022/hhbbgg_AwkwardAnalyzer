# %%
import os
import uproot
import numpy as np
import matplotlib.pyplot as plt
import hist
import mplhep as hep
from normalisation import getLumi

# Load CMS style including color-scheme
hep.style.use("CMS")

# Function to read histograms
def get_histogram(file_name, hist_name):
    return file_name[hist_name].to_hist()

# Function to read and sum histograms
def sum_histograms(file_name, directories, hist_name):
    hist_sum = None
    for directory in directories:
        hist = file_name[f"{directory}/{hist_name}"].to_hist()
        if hist_sum is None:
            hist_sum = hist
        else:
            hist_sum += hist
    return hist_sum

def stack1d_histograms(uproot_loaded_filename, data_histograms, mc_samples, signal_samples, histogram_names, legend_dict, xtitle_dict, output_directory):
    # List of recommended colors
    histogram_color = ["#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6", "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"]

    for hist_name in histogram_names:

        # List of MC histogram names
        mc_histograms = [f"{mc_sample}/{hist_name}" for mc_sample in mc_samples]
        # Sort MC histograms based on integral values
        sorted_mc_histograms = sorted(mc_histograms, key=lambda x: get_histogram(uproot_loaded_filename, x).sum(), reverse=True)

        # List of signal histogram names
        signal_histograms = [f"{signal_sample}/{hist_name}" for signal_sample in signal_samples]

        # Setup matplotlib figure with ratio plot
        fig, (ax, ax_ratio) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
        fig.subplots_adjust(hspace=0.05)  # Adjust space between main plot and ratio plot

        # Plot data histogram
        data_hist = sum_histograms(uproot_loaded_filename,data_histograms, hist_name)
        data_hist.plot1d(ax=ax, histtype='errorbar', color='black', label=f"Data")

        # Plot MC histograms
        for i, mc_hist_name in enumerate(sorted_mc_histograms):
            mc_hist = get_histogram(uproot_loaded_filename, mc_hist_name)
            mc_hist.plot1d(ax=ax, stack=True, histtype='fill', label=legend_dict[mc_hist_name.split('/')[0]], color=histogram_color[i])

        # Plot signal histograms
        for i, signal_hist_name in enumerate(signal_histograms):
            signal_hist = get_histogram(uproot_loaded_filename, signal_hist_name)
            signal_hist.plot1d(ax=ax, histtype='step', label=legend_dict[signal_hist_name.split('/')[0]], color="red")

        # Plot ratio plot
        mc_stack = sum_histograms(uproot_loaded_filename,mc_samples, hist_name)
        data_values = data_hist.values()
        mc_values = mc_stack.values()
        # Avoid division by zero by replacing zeros in mc_values with a small number
        epsilon = 1e-10  # Small value to prevent division by zero
        safe_mc_values = np.where(mc_values == 0, epsilon, mc_values)
        ratio = data_values / safe_mc_values

        # Handle cases where variances might be None
        data_variances = data_hist.variances()
        if data_variances is None:
            ratio_err = np.zeros_like(ratio)
        else:
            ratio_err = np.sqrt(data_variances) / mc_values
        bin_centers = (data_hist.axes[0].edges[:-1] + data_hist.axes[0].edges[1:]) / 2
        ax_ratio.errorbar(bin_centers, ratio, yerr=ratio_err, fmt='o', color='black')
        ax_ratio.axhline(1, linestyle='--', color='gray')
        ax_ratio.set_ylim(0, 3)
        ax_ratio.set_ylabel('Data / MC')

        # Style
        ax.set_yscale('log')
        ax.set_ylim(0.1,1E8)
        ax.set_xlabel("")
        ax.set_ylabel("Events")
        hep.cms.label("",ax=ax, lumi='{0:.2f}'.format(getLumi()),loc=0,llabel="Work in progress")
        ax.legend(ncol=2,loc='upper right', fontsize=18)

        ax_ratio.set_xlabel(xtitle_dict[hist_name])
        ax_ratio.set_ylabel("Data/MC")

        plt.savefig(f"{output_directory}/{hist_name}.pdf", bbox_inches='tight')

def main():
    # Open the ROOT file
    file_path = "outputfiles/hhbbgg_Analyzer.root"
    uproot_loaded_filename = uproot.open(file_path)

    # List of data histograms
    data_histograms = ["Data_EraE", "Data_EraF", "Data_EraG"]

    # List of MC processes
    mc_samples = ["GGJets", "GJetPt20To40", "GJetPt40", "GluGluHToGG", "VBFHToGG", "VHToGG", "ttHToGG"]

    # List of signal processes
    signal_samples = ["GluGluToHH",]

    # Dictionary for legends
    legend_dict = {"GGJets":r"$\gamma\gamma$+jets", "GJetPt20To40":r"$\gamma$+jets ($20< p_T < 40$)", "GJetPt40":r"$\gamma$+jets ($p_T > 40$)", "GluGluHToGG":r"$gg\rightarrow\,H\rightarrow\gamma\gamma$", "VBFHToGG":r"$VBF\:H\rightarrow\gamma\gamma$", "VHToGG":r"$V\:H\rightarrow\gamma\gamma$", "ttHToGG":r"$t\bar{t}H\rightarrow\gamma\gamma$", "GluGluToHH":r"$gg\rightarrow\,HH$"}

    # List of histogram names to stack
    histogram_names = ["h_reg_preselection_dibjet_mass","h_reg_preselection_diphoton_mass","h_reg_preselection_bbgg_mass"]

    # Dictionary for x-axis title
    xtitle_dict = {"h_reg_preselection_dibjet_mass":r"$m_{b\bar{b}}$ [GeV]","h_reg_preselection_diphoton_mass":r"$m_{\gamma\gamma}$ [GeV]","h_reg_preselection_bbgg_mass":r"$m_{b\bar{b}\gamma\gamma}$ [GeV]"}

    # create the directory to save plots
    output_directory = "stack_plots"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    stack1d_histograms(uproot_loaded_filename, data_histograms, mc_samples, signal_samples, histogram_names, legend_dict, xtitle_dict, output_directory)

if __name__ == "__main__":
    main()

# %%
