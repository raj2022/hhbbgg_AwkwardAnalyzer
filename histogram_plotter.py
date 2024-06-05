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

def stack1d_histograms(uproot_loaded_filename, data_histograms, mc_samples, signal_samples, histogram_names, legend_dict, output_directory):
    """
    Function to plot stacked histograms.

    Parameters:
        data_histograms (list): List of data histograms.
        mc_samples (list): List of MC histograms.
        histogram_names (list): List of histogram names to stack.
    """

    # List of recommended colors
    histogram_color = ["#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6", "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"]

    for hist_name in histogram_names:

        # List of MC histogram names
        mc_histograms = [f"{mc_sample}/{hist_name}" for mc_sample in mc_samples]
        # Sort MC histograms based on integral values
        sorted_mc_histograms = sorted(mc_histograms, key=lambda x: get_histogram(uproot_loaded_filename, x).sum(), reverse=True)

        # List of signal histogram names
        signal_histograms = [f"{signal_sample}/{hist_name}" for signal_sample in signal_samples]
        # # Sort MC histograms based on integral values
        # sorted_mc_histograms = sorted(signal_histograms, key=lambda x: get_histogram(uproot_loaded_filename, x).sum(), reverse=True)

        # Setup matplotlib figure
        fig, ax = plt.subplots()

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


        # Style
        ax.set_xlabel("Dijet Mass [GeV]")
        ax.set_ylabel("Events")
        ax.legend()
        # hep.cms.label()
        '{0:.1f}'.format(getLumi())
        hep.cms.label("",lumi='{0:.2f}'.format(getLumi()),loc=0,llabel="Work in progress")


        plt.savefig(f"{output_directory}/{hist_name}.pdf", bbox_inches='tight')
        # Show the plot
        # plt.show()

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

    legend_dict = {"GGJets":r"$\gamma\gamma$+jets", "GJetPt20To40":r"$\gamma$+jets ($20< p_T < 40$)", "GJetPt40":r"$\gamma$+jets ($p_T > 40$)", "GluGluHToGG":r"$gg\rightarrow\,H\rightarrow\gamma\gamma$", "VBFHToGG":r"$VBF\:H\rightarrow\gamma\gamma$", "VHToGG":r"$V\:H\rightarrow\gamma\gamma$", "ttHToGG":r"$t\bar{t}H\rightarrow\gamma\gamma$", "GluGluToHH":r"$gg\rightarrow\,HH$"}

    # List of histogram names to stack
    histogram_names = ["h_reg_preselection_dijet_mass"]

    # create the directory to save plots
    output_directory = "stack_plots"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    stack1d_histograms(uproot_loaded_filename, data_histograms, mc_samples, signal_samples, histogram_names, legend_dict, output_directory)

if __name__ == "__main__":
    main()

# %%
