import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import erf
import uproot
import awkward as ak
from vector import Array as awk
import os
import argparse

# Define the Crystal Ball PDF
def crystalball_pdf(x, alpha, n, mu, sigma):
    A = (n / abs(alpha)) ** n * np.exp(-alpha**2 / 2)
    B = n / abs(alpha) - abs(alpha)
    C = (n / abs(alpha)) * (1 / (n - 1)) * np.exp(-alpha**2 / 2)
    D = np.sqrt(np.pi / 2) * (1 + erf(alpha / np.sqrt(2)))
    N = 1 / (sigma * (C + D))
    z = (x - mu) / sigma
    pdf = np.where(
        z > -alpha,
        N * np.exp(-0.5 * z**2),
        N * A * (B - z)**-n
    )
    return pdf

# Define the fitting function
def fit_crystalball(data, bins):
    bin_centers = (bins[:-1] + bins[1:]) / 2
    initial_params = [1.5, 5, np.mean(data), np.std(data)]
    params, _ = curve_fit(crystalball_pdf, bin_centers, np.histogram(data, bins=bins, density=True)[0], p0=initial_params)
    return params, bin_centers

# Define the lVector function
def lVector(pt1, eta1, phi1, pt2, eta2, phi2, mass1=0, mass2=0):
    lvec_1 = awk(
        ak.zip({"pt": pt1, "eta": eta1, "phi": phi1, "mass": ak.full_like(pt1, mass1)})
    )
    lvec_2 = awk(
        ak.zip({"pt": pt2, "eta": eta2, "phi": phi2, "mass": ak.full_like(pt2, mass2)})
    )
    lvec_ = lvec_1 + lvec_2
    return lvec_

# Main function
def main(input_file, output_dir, mass_min, mass_max):
    # Tree name is constant
    tree_name = "DiphotonTree/data_125_13TeV_NOTAG/"

    # Extract file name and set output paths
    root_file_name = os.path.basename(input_file).replace(".root", "")
    png_path = os.path.join(output_dir, f"{root_file_name}_CrystalBall_Fit.png")
    pdf_path = os.path.join(output_dir, f"{root_file_name}_CrystalBall_Fit.pdf")

    # Load the ROOT file and tree
    with uproot.open(input_file) as file:
        tree = file[tree_name]
        lead_pho_pt = tree["lead_pt"].array(library="ak")
        lead_pho_eta = tree["lead_eta"].array(library="ak")
        lead_pho_phi = tree["lead_phi"].array(library="ak")
        sublead_pho_pt = tree["sublead_pt"].array(library="ak")
        sublead_pho_eta = tree["sublead_eta"].array(library="ak")
        sublead_pho_phi = tree["sublead_phi"].array(library="ak")

    # Compute the diphoton Lorentz vector
    diphoton_ = lVector(
        lead_pho_pt,
        lead_pho_eta,
        lead_pho_phi,
        sublead_pho_pt,
        sublead_pho_eta,
        sublead_pho_phi,
    )
    diphoton_mass = ak.to_numpy(diphoton_.mass)

    # Filter mass range
    filtered_mass = diphoton_mass[(diphoton_mass >= mass_min) & (diphoton_mass <= mass_max)]

    # Define histogram bins
    bins = np.linspace(mass_min, mass_max, 100)

    # Fit the Crystal Ball function
    params, bin_centers = fit_crystalball(filtered_mass, bins)
    fitted_curve_cb = crystalball_pdf(bin_centers, *params)

    # Prepare the parameter text
    param_text = (
        f"Fitting parameters:\n"
        f"$\\alpha$ = {params[0]:.3f}\n"
        f"$n$ = {params[1]:.3f}\n"
        f"$\\mu$ = {params[2]:.3f}\n"
        f"$\\sigma$ = {params[3]:.3f}"
    )

    # Plot and save the histogram and fit
    plt.figure(figsize=(8, 6))
    plt.hist(filtered_mass, bins=bins, density=True, alpha=0.2, color="c", label="Diphoton Mass Data")
    plt.plot(bin_centers, fitted_curve_cb, "b-", label="Crystal Ball Fit")
    plt.gca().text(
        0.10, 0.95, param_text,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.3", edgecolor="blue", facecolor="white")
    )
    plt.xlabel("Diphoton Mass (GeV)")
    plt.ylabel("Density")
    plt.title(f"Crystal Ball Fit to Diphoton Mass ({mass_min}-{mass_max} GeV)")
    plt.legend()
    plt.savefig(png_path)
    plt.savefig(pdf_path)
    plt.show()

    print(f"Plots saved as:\nPNG: {png_path}\nPDF: {pdf_path}")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fit Crystal Ball function to diphoton mass")
    parser.add_argument("-i", "--input", required=True, help="Path to the input ROOT file")
    parser.add_argument("-o", "--output", required=True, help="Directory to save output plots")
    parser.add_argument("--mass_min", type=float, default=100, help="Minimum mass range")
    parser.add_argument("--mass_max", type=float, default=140, help="Maximum mass range")
    args = parser.parse_args()

    main(args.input, args.output, args.mass_min, args.mass_max)

