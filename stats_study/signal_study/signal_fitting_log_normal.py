import numpy as np
import scipy.stats as stats
import uproot
import matplotlib.pyplot as plt

# Load the ROOT file and the tree
file_path = "../../../../output_root/v1_v2_comparison/NMSSM_X300_Y60.root"
tree_name = "DiphotonTree/data_125_13TeV_NOTAG/"
with uproot.open(file_path) as file:
    tree = file[tree_name]
    data = tree["pt"].array(library="np")

# Create a histogram
bins = 500
hist, bin_edges = np.histogram(data, bins=bins, density=True)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

# Fit with a log-normal distribution
shape, loc, scale = stats.lognorm.fit(data, floc=0)  # Fit data
fitted_curve = stats.lognorm.pdf(bin_centers, shape, loc=loc, scale=scale)

# Plot the histogram and fit
plt.figure(figsize=(8, 6))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, fitted_curve, "r-", label="Log-Normal Fit")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("Log-Normal Fit to pt")
plt.legend()
plt.show()

# Print fit parameters
print(f"Fitted Log-Normal Parameters: Shape={shape}, Loc={loc}, Scale={scale}")

from scipy.stats import crystalball

# Fit with Crystal Ball function
params = crystalball.fit(data)
fitted_curve_cb = crystalball.pdf(bin_centers, *params)

# Plot the histogram and Crystal Ball fit
plt.figure(figsize=(8, 6))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, fitted_curve_cb, "b-", label="Crystal Ball Fit")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("Crystal Ball Fit to pt")
plt.legend()
plt.show()

# Print fit parameters
print(f"Fitted Crystal Ball Parameters: {params}")


from sklearn.neighbors import KernelDensity

# Perform KDE
kde = KernelDensity(bandwidth=5, kernel='gaussian')
kde.fit(data.reshape(-1, 1))
kde_curve = np.exp(kde.score_samples(bin_centers.reshape(-1, 1)))

# Plot KDE
plt.figure(figsize=(8, 6))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, kde_curve, "r-", label="KDE Fit")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("KDE Fit to pt")
plt.legend()
plt.show()

import numpy as np
from scipy.optimize import curve_fit

# Define a Double-Sided Log-Normal Function
def double_sided_lognormal(x, mu1, sigma1, mu2, sigma2, scale1, scale2):
    left = np.where(x < mu1, scale1 * np.exp(-((np.log(x + 1e-5) - mu1) ** 2) / (2 * sigma1 ** 2)), 0)
    right = np.where(x >= mu1, scale2 * np.exp(-((np.log(x + 1e-5) - mu2) ** 2) / (2 * sigma2 ** 2)), 0)
    return left + right

# Fit the Double-Sided Log-Normal
params, cov = curve_fit(double_sided_lognormal, bin_centers, hist,
                        p0=[2, 0.5, 5, 0.5, 0.01, 0.01])  # Initial guesses for parameters

# Generate the fit curve
fitted_curve_dsln = double_sided_lognormal(bin_centers, *params)

# Plot the fit
plt.figure(figsize=(8, 6))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, fitted_curve_dsln, "r-", label="Double-Sided Log-Normal Fit")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("Double-Sided Log-Normal Fit to pt")
plt.legend()
plt.show()

# Print fit parameters
print(f"Double-Sided Log-Normal Parameters:\n mu1={params[0]:.3f}, sigma1={params[1]:.3f}, mu2={params[2]:.3f}, sigma2={params[3]:.3f}, scale1={params[4]:.3f}, scale2={params[5]:.3f}")



# Define a Custom Function (Gaussian + Exponential Tail)
def gaussian_exponential(x, amp1, mu, sigma, amp2, decay):
    gaussian = amp1 * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
    exponential = amp2 * np.exp(-decay * x)
    return gaussian + exponential

# Fit the Custom Function
params_custom, cov_custom = curve_fit(gaussian_exponential, bin_centers, hist,
                                      p0=[0.01, 100, 50, 0.005, 0.01])  # Initial guesses

# Generate the fit curve
fitted_curve_custom = gaussian_exponential(bin_centers, *params_custom)

# Plot the fit
plt.figure(figsize=(8, 6))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, fitted_curve_custom, "b-", label="Gaussian + Exponential Fit")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("Custom Fit to pt")
plt.legend()
plt.show()

# Print fit parameters
print(f"Custom Fit Parameters:\n amp1={params_custom[0]:.3f}, mu={params_custom[1]:.3f}, sigma={params_custom[2]:.3f}, amp2={params_custom[3]:.3f}, decay={params_custom[4]:.3f}")


# Calculate SSR for each fit
ssr_dsln = np.sum((hist - double_sided_lognormal(bin_centers, *params)) ** 2)
ssr_custom = np.sum((hist - gaussian_exponential(bin_centers, *params_custom)) ** 2)

print(f"SSR for Double-Sided Log-Normal: {ssr_dsln:.3f}")
print(f"SSR for Custom Function: {ssr_custom:.3f}")



print(f"---------------Working with KDE----------")
from sklearn.neighbors import KernelDensity
import matplotlib.pyplot as plt
import numpy as np

# Define a function to plot KDE with different bandwidths
def plot_kde(data, bandwidths=[1, 5, 10], kernel='gaussian'):
    plt.figure(figsize=(10, 6))
    bins = 50
    hist, bin_edges = np.histogram(data, bins=bins, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    for bw in bandwidths:
        # Create KDE model with the specified bandwidth and kernel
        kde = KernelDensity(bandwidth=bw, kernel=kernel)
        kde.fit(data.reshape(-1, 1))
        kde_curve = np.exp(kde.score_samples(bin_centers.reshape(-1, 1)))

        # Plot the KDE
        plt.plot(bin_centers, kde_curve, label=f'KDE bw={bw}')

    # Plot the histogram
    plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
    plt.xlabel("pt")
    plt.ylabel("Density")
    plt.title(f"KDE Fit with Different Bandwidths ({kernel} Kernel)")
    plt.legend()
    plt.show()

# Plot KDE with different bandwidths and the Gaussian kernel
plot_kde(data, bandwidths=[1, 5, 10], kernel='gaussian')


from sklearn.neighbors import KernelDensity
import numpy as np

# Function to find the optimal bandwidth for KDE
def find_optimal_bandwidth(data, bandwidth_range=(0.1, 50), num_points=100):
    bandwidths = np.linspace(bandwidth_range[0], bandwidth_range[1], num_points)
    log_likelihoods = []
    
    for bw in bandwidths:
        kde = KernelDensity(bandwidth=bw, kernel='gaussian')
        kde.fit(data.reshape(-1, 1))
        log_likelihood = kde.score_samples(data.reshape(-1, 1)).sum()
        log_likelihoods.append(log_likelihood)
    
    # Find the bandwidth with the highest log-likelihood
    optimal_bw = bandwidths[np.argmax(log_likelihoods)]
    print(f"Optimal bandwidth found: {optimal_bw:.3f}")
    return optimal_bw

# Find the optimal bandwidth for the data
optimal_bw = find_optimal_bandwidth(data, bandwidth_range=(0.1, 50), num_points=100)


# Plot KDE with the optimal bandwidth
kde = KernelDensity(bandwidth=optimal_bw, kernel='gaussian')
kde.fit(data.reshape(-1, 1))
kde_curve = np.exp(kde.score_samples(bin_centers.reshape(-1, 1)))

# Plot the histogram and the KDE fit
plt.figure(figsize=(10, 6))
plt.hist(data, bins=50, density=True, alpha=0.6, color="g", label="Data")
plt.plot(bin_centers, kde_curve, 'r-', label=f'KDE Fit (bw={optimal_bw:.2f})')
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("KDE Fit to pt with Optimal Bandwidth")
plt.legend()
plt.show()

