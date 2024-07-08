# %%
import os
import uproot
import dask.dataframe as dd
import mplhep as hep
from plothist import make_hist, plot_data_model_comparison
from binning import binning
import matplotlib.pyplot as plt
from cycler import cycler
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
# hep.style.use("CMS")



# Function to read histograms
def get_histogram(file_name, histogram_name, binning):
    histogram = make_hist(file_name[histogram_name], bins=binning[0], range=binning[1:])
    return histogram


# Function to read and sum histograms
def sum_histograms(histograms):
    return sum(histograms)


def stack1d_trees(
    file_name,
    regions,
    data_samples,
    mc_samples,
    signal_samples,
    histogram_names,
    legend_dict,
    xaxis_titles,
    output_directory,
):
    # Process each region
    for region in regions:
        for histogram_name in histogram_names:
            # Load and sum data histograms
            data_hist = sum_histograms(
                [
                    get_histogram(file_name, f"{sample}/{region}/{histogram_name}", binning[region][histogram_name])
                    for sample in data_samples
                ]
            )

            # Load MC and signal histograms
            stacked_components = [
                get_histogram(file_name, f"{sample}/{region}/{histogram_name}", binning[region][histogram_name])
                for sample in mc_samples
            ]
            unstacked_components = [
                get_histogram(file_name, f"{sample}/{region}/{histogram_name}", binning[region][histogram_name])
                for sample in signal_samples
            ]

            # Plot the comparison
            fig, ax_main, ax_comparison = plot_data_model_comparison(
                data_hist=data_hist,
                stacked_components=stacked_components,
                stacked_labels=[legend_dict[sample] for sample in mc_samples],
                unstacked_components=unstacked_components,
                xlabel=xaxis_titles[histogram_name],
                ylabel = "Events",
                comparison="ratio",
            )

            # Show the plot
            plt.show()


def main():
    # Open the ROOT file
    file_path = "outputfiles/hhbbgg_analyzer-trees.root"
    file_name = uproot.open(file_path)
    file_ddf  = dd.read_root(file_path)
    print(file_ddf)
    # List of data histograms
    data_samples = ["Data_EraE", "Data_EraF", "Data_EraG"]

    # List of MC processes
    mc_samples = [
        "GGJets",
        "GJetPt20To40",
        "GJetPt40",
        "GluGluHToGG",
        "VBFHToGG",
        "VHToGG",
        "ttHToGG",
    ]

    # List of signal processes
    signal_samples = [
        "GluGluToHH",
    ]

    # Dictionary for legends
    legend_dict = {
        "GGJets": r"$\gamma\gamma$+jets",
        "GJetPt20To40": r"$\gamma$+jets ($20< p_T < 40$)",
        "GJetPt40": r"$\gamma$+jets ($p_T > 40$)",
        "GluGluHToGG": r"$gg\rightarrow\,H\rightarrow\gamma\gamma$",
        "VBFHToGG": r"$VBF\:H\rightarrow\gamma\gamma$",
        "VHToGG": r"$V\:H\rightarrow\gamma\gamma$",
        "ttHToGG": r"$t\bar{t}H\rightarrow\gamma\gamma$",
        "GluGluToHH": r"$gg\rightarrow\,HH$",
    }

    # List of regions names
    regions = ["preselection", "srbbgg", "srbbggMET", "crantibbgg", "crbbantigg"]
    # List of variable names
    histogram_names = [
        "dibjet_mass",
    ]

    # Dictionary for x-axis titles
    xaxis_titles = {
        "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
    }

    # create the tdirectory to save plots
    output_directory = "stack_plots"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    stack1d_trees(
        file_name,
        regions,
        data_samples,
        mc_samples,
        signal_samples,
        histogram_names,
        legend_dict,
        xaxis_titles,
        output_directory,
    )


if __name__ == "__main__":
    main()

# %%
