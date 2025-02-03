import os
import re
from scipy.interpolate import interp1d
import uproot
import awkward as ak
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from scipy.optimize import curve_fit
import argparse

# Apply CMS Style
hep.style.use("CMS")

# Define the Double-Sided Crystal Ball function
def double_sided_crystalball(x, alpha1, n1, alpha2, n2, mu, sigma):
    z = (x - mu) / sigma
    A1 = (n1 / abs(alpha1)) ** n1 * np.exp(-alpha1 ** 2 / 2)
    A2 = (n2 / abs(alpha2)) ** n2 * np.exp(-alpha2 ** 2 / 2)
    B1 = n1 / abs(alpha1) - abs(alpha1)
    B2 = n2 / abs(alpha2) - abs(alpha2)

    pdf = np.where(
        z < -alpha1,
        A1 * (B1 - z) ** -n1,
        np.where(
            z > alpha2,
            A2 * (B2 + z) ** -n2,
            np.exp(-0.5 * z ** 2),
        ),
    )
    return pdf / np.trapz(pdf, x)

# Define fitting function
def fit_double_sided_crystalball(data, bins):
    bin_centers = (bins[:-1] + bins[1:]) / 2
    hist_vals, _ = np.histogram(data, bins=bins, density=True)
    initial_params = [1.5, 5, 1.5, 5, np.mean(data), np.std(data)]
    params, _ = curve_fit(double_sided_crystalball, bin_centers, hist_vals, p0=initial_params)
    return params, bin_centers

def find_fwhm(x, y):
    """Find Full Width at Half Maximum (FWHM)"""
    max_val = np.max(y)
    half_max = max_val / 2

    # Find where the curve is equal to half max (by brute force)
    indices = np.where((y[:-1] - half_max) * (y[1:] - half_max) < 0)[0]  # Find zero-crossings

    if len(indices) >= 2:
        # Get the x values at the crossing points
        x_fwhm_low = x[indices[0]]
        x_fwhm_high = x[indices[1]]
    else:
        x_fwhm_low, x_fwhm_high = np.nan, np.nan  # Return NaN if no valid crossing points

    return x_fwhm_low, x_fwhm_high

# Extract X and Y from the input file path
def extract_x_y_from_path(input_file):
    # Extract X and Y using regular expressions
    match = re.search(r"X(\d+)_Y(\d+)", input_file)
    if match:
        x_value = match.group(1)
        y_value = match.group(2)
        return x_value, y_value
    else:
        return None, None

# Main function
def main(input_file, output_dir, mass_min, mass_max):

    file_basename = os.path.splitext(os.path.basename(input_file))[0]

    # Load the ROOT file and extract variables
    tree_name = "DiphotonTree/data_125_13TeV_NOTAG/"

    with uproot.open(input_file) as file:
        tree = file[tree_name]
        dijet_mass = tree["Res_dijet_mass"].array(library="ak")

    print("file read successfully!")

    diphoton_mass_np = ak.to_numpy(dijet_mass)
    filtered_mass = diphoton_mass_np[(diphoton_mass_np >= mass_min) & (diphoton_mass_np <= mass_max)]
    bins = np.linspace(mass_min, mass_max, 50)

    # Perform fit
    params_dscb, bin_centers = fit_double_sided_crystalball(filtered_mass, bins)
    fitted_dscb = double_sided_crystalball(bin_centers, *params_dscb)

    # Compute FWHM
    x_fwhm_low, x_fwhm_high = find_fwhm(bin_centers, fitted_dscb)
    fwhm_value = x_fwhm_high - x_fwhm_low

    # Compute chi-squared
    hist_vals, _ = np.histogram(filtered_mass, bins=bins, density=True)
    errors = np.sqrt(hist_vals)
    errors[errors == 0] = 1
    chi2_val = np.sum(((hist_vals - fitted_dscb) / errors) ** 2)
    dof = len(bin_centers) - len(params_dscb)
    chi2_dscb = chi2_val / dof if dof > 0 else 0

    # Plot results
    plt.figure(figsize=(8, 8))
    plt.errorbar(bin_centers, hist_vals, fmt="o", color="black", markersize=5, label="Simulation", markerfacecolor='none')
    plt.plot(bin_centers, fitted_dscb, "b-", linewidth=2, label="Parametric model")

    # Highlight the FWHM region
    plt.fill_between(bin_centers, 0, fitted_dscb, where=(bin_centers >= x_fwhm_low) & (bin_centers <= x_fwhm_high), color='gray', alpha=0.2, label="FWHM Region")


    plt.ylim(bottom=0)  # Set the y-axis to start from 0
    hep.cms.label(data=False, lumi=13.6, loc=0, fontsize=12, label="Preliminary")
    plt.xlabel(r"$m_{jj}$ [GeV]", fontsize=14)
    plt.ylabel(r"Events / (%.1f GeV)" % (bins[1] - bins[0]), fontsize=14)
    plt.legend(fontsize=11, loc="upper right", frameon=False)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.xlim(mass_min, mass_max)

    # Extract X and Y from the input file path
    x_value, y_value = extract_x_y_from_path(input_file)

    # If X and Y are found, add them as text to the plot
    if x_value and y_value:
        plt.text(0.05, 0.95, f"X = {x_value}, Y = {y_value}", transform=plt.gca().transAxes, fontsize=12, verticalalignment="top", color="blue")

   # Save plot with dynamic filename
    plot_filename = f"{output_dir}/{file_basename}_DSCB_Fit_bkg_Dibjet_mass"
    plt.savefig(f"{plot_filename}.png")
    plt.savefig(f"{plot_filename}.pdf")
   # plt.show()
    print(f"saved output at {output_dir}")
    print(f"FWHM: {fwhm_value:.2f} GeV")
    # Print Fit Parameters
    print(f"Fitted DSCB Parameters:")
    print(f"  Alpha1 = {params_dscb[0]:.3f},  N1 = {params_dscb[1]:.3f}")
    print(f"  Alpha2 = {params_dscb[2]:.3f},  N2 = {params_dscb[3]:.3f}")
    print(f"  Mu = {params_dscb[4]:.3f},  Sigma = {params_dscb[5]:.3f}")
    print(f"Chi-squared / dof: {chi2_dscb:.2f}")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fit Crystal Ball function to diphoton mass")
    parser.add_argument("-i", "--input", required=True, help="Path to the input ROOT file")
    parser.add_argument("-o", "--output", required=True, help="Directory to save output plots")
    parser.add_argument("--mass_min", type=float, default=100, help="Minimum mass range")
    parser.add_argument("--mass_max", type=float, default=140, help="Maximum mass range")
    args = parser.parse_args()


    main(args.input, args.output,  args.mass_min, args.mass_max)
