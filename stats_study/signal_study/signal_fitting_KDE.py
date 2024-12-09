import numpy as np
import scipy.stats as stats
import uproot
import matplotlib.pyplot as plt
from sklearn.neighbors import KernelDensity

# Load the ROOT file and the tree
file_path = "../../../../output_root/v1_v2_comparison/NMSSM_X300_Y60.root"
tree_name = "DiphotonTree/data_125_13TeV_NOTAG/"
with uproot.open(file_path) as file:
    tree = file[tree_name]
    data = tree["pt"].array(library="np")

# Define a function to plot KDE with different bandwidths
def plot_kde(data, bandwidths=[1, 5, 10], kernel='gaussian'):
    plt.figure(figsize=(10, 6))
    bins = 500
    hist, bin_edges = np.histogram(data, bins=bins, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Define a list of colors for the KDE curves
    colors = ['r', 'b', 'm']  # Red, Blue, Magenta (adjustable)

    for i, bw in enumerate(bandwidths):
        # Create KDE model with the specified bandwidth and kernel
        kde = KernelDensity(bandwidth=bw, kernel=kernel)
        kde.fit(data.reshape(-1, 1))
        kde_curve = np.exp(kde.score_samples(bin_centers.reshape(-1, 1)))

        # Plot the KDE with the specified color
        plt.plot(bin_centers, kde_curve, label=f'KDE bw={bw}', color=colors[i % len(colors)])

    # Plot the histogram
    plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
    plt.xlabel("pt")
    plt.ylabel("Density")
    plt.title(f"KDE Fit with Different Bandwidths ({kernel} Kernel)")
    plt.legend()
    plt.show()

# Plot KDE with different bandwidths and the Gaussian kernel
plot_kde(data, bandwidths=[1, 5, 10], kernel='gaussian')

