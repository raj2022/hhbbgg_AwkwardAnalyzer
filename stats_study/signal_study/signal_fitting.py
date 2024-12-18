import numpy as np
import scipy.optimize as opt
import uproot
import matplotlib.pyplot as plt

# Gaussian function
def gaussian(x, amplitude, mean, stddev):
    return amplitude * np.exp(-((x - mean) ** 2) / (2 * stddev ** 2))

# Function to evaluate the fit quality
def calculate_ssr(y_obs, y_fit):
    return np.sum((y_obs - y_fit) ** 2)

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

# Define initial guesses for the fit
initial_guesses = [
    [1.0, np.mean(data), np.std(data)],  # Default guess
    [0.8, np.mean(data) * 0.9, np.std(data) * 1.1],
    [1.2, np.mean(data) * 1.1, np.std(data) * 0.9],
    [1.0, np.mean(data) + 10, np.std(data) * 1.2],
]

best_fit_params = None
best_ssr = np.inf
fits = []

# Try different initial parameters
for idx, p0 in enumerate(initial_guesses):
    try:
        # Fit the histogram data
        popt, _ = opt.curve_fit(gaussian, bin_centers, hist, p0=p0)
        # Calculate the fitted curve and SSR
        fitted_curve = gaussian(bin_centers, *popt)
        ssr = calculate_ssr(hist, fitted_curve)
        fits.append((popt, ssr))
        
        # Update the best fit if necessary
        if ssr < best_ssr:
            best_ssr = ssr
            best_fit_params = popt
    except RuntimeError:
        print(f"Fit {idx + 1} did not converge for parameters: {p0}")

# Plot the histogram and all fits
plt.figure(figsize=(10, 7))
plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")
for idx, (popt, _) in enumerate(fits):
    plt.plot(bin_centers, gaussian(bin_centers, *popt), label=f"Fit {idx + 1}")
plt.xlabel("pt")
plt.ylabel("Density")
plt.title("Gaussian Fits to pt")
plt.legend()
plt.show()

# Print the best-fit parameters
if best_fit_params is not None:
    print(f"Best fit parameters: Amplitude={best_fit_params[0]}, Mean={best_fit_params[1]}, Stddev={best_fit_params[2]}")
    print(f"Best SSR: {best_ssr}")
else:
    print("No fit converged.")

