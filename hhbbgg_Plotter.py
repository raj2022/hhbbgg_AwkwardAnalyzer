# %%
import os
import matplotlib
matplotlib.use('Agg')
import uproot
from hist import Hist, Stack, intervals
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from normalisation import getLumi

# Load CMS style including color-scheme
hep.style.use("CMS")

# Function to read histograms
def get_histogram(file_name, hist_name):
    return Hist(file_name[hist_name])


# Function to read and sum histograms
def sum_histograms(histograms):
    return sum(histograms)

# Function to return histogram ratio
def get_ratio(hist_a, hist_b):
    # Extract the bin edges and contents
    edges_a = hist_a.axes.edges[0]
    edges_b = hist_b.axes.edges[0]
    if not np.array_equal(edges_a, edges_b):
        raise ValueError("Histograms have different binning")
    # Extract the counts
    counts_a = hist_a.values()
    counts_b = hist_b.values()
    # Compute the errors for each histogram
    errors_a = np.sqrt(counts_a)  # Assuming Poisson statistics
    errors_b = np.sqrt(counts_b)  # Assuming Poisson statistics

    # Compute the ratio with handling of division by zero
    ratio_counts = np.divide(counts_a, counts_b, out=np.zeros_like(counts_a, dtype=float), where=counts_b!=0)
    ratio_hist = Hist(hist_a.axes[0])
    ratio_hist[...] = ratio_counts

    # Compute the relative errors
    with np.errstate(divide='ignore', invalid='ignore'):
        relative_errors_a = np.divide(errors_a, counts_a, out=np.zeros_like(errors_a, dtype=float), where=counts_a!=0)
        relative_errors_b = np.divide(errors_b, counts_b, out=np.zeros_like(errors_b, dtype=float), where=counts_b!=0)
    # Propagate the errors for the ratio
    ratio_errors = ratio_counts * np.sqrt(relative_errors_a**2 + relative_errors_b**2)

    return ratio_hist, ratio_errors

def stack1d_histograms(uproot_loaded_filename, data_samples, mc_samples, signal_samples, histogram_names, legend_dict, xtitle_dict, output_directory):
    for hist_name in histogram_names:
        fig, (ax, ax_ratio) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
        fig.subplots_adjust(hspace=0.05)  # Adjust space between main plot and ratio plot

        # Plot data histogram
        data_histogram = sum_histograms([get_histogram(uproot_loaded_filename,f"{data_sample}/{hist_name}") for data_sample in data_samples])
        data_histogram.plot(ax=ax, stack=False, histtype='errorbar', yerr=True, xerr=True, color='black', label=f"Data", flow="sum")

        # Plot MC histograms as stack
        mc_stack = Stack(*[get_histogram(uproot_loaded_filename,f"{mc_sample}/{hist_name}") for mc_sample in mc_samples])
        mc_stack[::-1].plot(ax=ax, stack=True, histtype='fill', label=legend_dict.values(),flow="sum")

        # Plot signal histograms
        for signal_sample in signal_samples:
            signal_histogram = get_histogram(uproot_loaded_filename,f"{signal_sample}/{hist_name}")
            signal_histogram.plot(ax=ax, histtype='step',yerr=True, xerr=True, label=legend_dict[signal_sample], color="red")

        # Plot ratio plot
        ratio, error = get_ratio(data_histogram,sum_histograms(mc_stack))
        ratio.plot(ax=ax_ratio, histtype='errorbar', yerr=error, xerr=True, color='black', flow="sum")
        ax_ratio.axhline(1, linestyle='--', color='gray')
        ax_ratio.set_ylim(0, 3)
        ax_ratio.set_ylabel('Data / MC')

        # Style
        # x_axis_bining = data_histogram.axes.edges[0]
        # ax.set_xlim(min(x_axis_bining), max(x_axis_bining))
        ax.set_yscale('log')
        ax.set_ylim(0.1,1E8)
        ax.set_xlabel("")
        ax.set_ylabel("Events")
        hep.cms.label("",ax=ax, lumi='{0:.2f}'.format(getLumi()),loc=0,llabel="Work in progress")
        ax.legend(ncol=2,loc='upper right', fontsize=18)
        ax_ratio.set_xlabel(xtitle_dict[hist_name.split("-")[-1]])
        ax_ratio.set_ylabel("Data/MC")

        # Save plots
        plot_reg_name = hist_name.split("-")[0]
        # check and create plot directory
        if not os.path.exists(f"{output_directory}/{plot_reg_name}"): os.makedirs(f"{output_directory}/{plot_reg_name}")
        plot_var_name = hist_name.split("-")[-1]
        plt.savefig(f"{output_directory}/{plot_reg_name}/{plot_var_name}.pdf", bbox_inches='tight')
        plt.savefig(f"{output_directory}/{plot_reg_name}/{plot_var_name}.png", bbox_inches='tight')
        plt.close()


def main():
    # Open the ROOT file
    file_path = "outputfiles/hhbbgg_analyzer-histograms.root"
    uproot_loaded_filename = uproot.open(file_path)

    # List of data histograms
    data_samples = ["Data_EraE", "Data_EraF", "Data_EraG"]

    # List of MC processes
    mc_samples = ["GGJets", "GJetPt20To40", "GJetPt40", "GluGluHToGG", "VBFHToGG", "VHToGG", "ttHToGG"]

    # List of signal processes
    signal_samples = ["GluGluToHH",]

    # Dictionary for legends
    legend_dict = {"GGJets":r"$\gamma\gamma$+jets", "GJetPt20To40":r"$\gamma$+jets ($20< p_T < 40$)", "GJetPt40":r"$\gamma$+jets ($p_T > 40$)", "GluGluHToGG":r"$gg\rightarrow\,H\rightarrow\gamma\gamma$", "VBFHToGG":r"$VBF\:H\rightarrow\gamma\gamma$", "VHToGG":r"$V\:H\rightarrow\gamma\gamma$", "ttHToGG":r"$t\bar{t}H\rightarrow\gamma\gamma$", "GluGluToHH":r"$gg\rightarrow\,HH$"}

    # List of regions naames
    regions = [
        "preselection", "selection"
    ]
    #List of variable names
    variable_names = [
        "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta", "bbgg_phi", "lead_pho_pt","sublead_pho_pt","dibjet_pt"
    ]
    histogram_names = [f"{region}-{variable_name}" for region in regions for variable_name in variable_names]

    # Dictionary for x-axis titles
    xaxis_titles = {
        "dibjet_mass":r"$m_{b\bar{b}}$ [GeV]","diphoton_mass":r"$m_{\gamma\gamma}$ [GeV]",
        "bbgg_mass":r"$m_{b\bar{b}\gamma\gamma}$ [GeV]","lead_pho_pt":r"lead $p_T^{\gamma}$ [GeV]",
        "sublead_pho_pt":r"sublead $p_T^{\gamma}$ [GeV]","dibjet_pt":r"$p_T^{b\bar{b}}$ [GeV]",
        "dibjet_pt":r"$p_{T}^{b\bar{b}}$ [GeV]","diphoton_pt":r"$p_{T}^{\gamma\gamma}$ [GeV]",
        "bbgg_pt":r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]","bbgg_eta":r"$\eta^{b\bar{b}\gamma\gamma}$ [GeV]",
        "bbgg_phi":r"$\phi^{b\bar{b}\gamma\gamma}$ [GeV]", "lead_pho_eta":r"lead $\eta^{\gamma}$ [GeV]", 
        "lead_pho_phi":r"lead $\phi^{\gamma}$ [GeV]", "sublead_pho_eta":r"sublead $\eta^{\gamma}$ [GeV]", 
        "sublead_pho_phi":r"sublead $\phi^{\gamma}$ [GeV]"
    }

    # create the tdirectory to save plots
    output_directory = "stack_plots"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    stack1d_histograms(uproot_loaded_filename, data_samples, mc_samples, signal_samples, histogram_names, legend_dict, xaxis_titles, output_directory)

if __name__ == "__main__":
    main()

    # %%
