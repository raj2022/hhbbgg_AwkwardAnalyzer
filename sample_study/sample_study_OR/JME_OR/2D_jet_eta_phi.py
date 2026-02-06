import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyarrow.parquet as pq

from matplotlib.colors import LogNorm
import mplhep as hep


# --------------------------------
# Configuration
# --------------------------------
# base_path = "/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/preBPix/"
# base_path = "/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2024/"
base_path = "/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/postEE"
# parquet_files = glob.glob(f"{base_path}/Data_EraE.parquet") # use for the background

data_eras = ["EraE", "EraF", "EraG"]

parquet_files = []
for era in data_eras:
    parquet_files += glob.glob(f"{base_path}/Data_{era}.parquet")

if not parquet_files:
    raise RuntimeError("No Data parquet files found for EraE/F/G")

print("Using data files:")
for pf in parquet_files:
    print("  ", pf)



if not parquet_files:
    raise RuntimeError("No GGJets_MGG-40to80 parquet files found")

jet_indices = range(1, 11)  # jet1 ... jet10

eta_bins = np.linspace(-5.0, 5.0, 101)
phi_bins = np.linspace(-np.pi, np.pi, 101)

eta_all = []
phi_all = []

# --------------------------------
# Read files
# --------------------------------
for pf in parquet_files:
    cols = []
    for i in jet_indices:
        cols += [f"jet{i}_eta", f"jet{i}_phi", f"jet{i}_pt"]

    table = pq.read_table(pf, columns=cols)
    df = table.to_pandas()

    for i in jet_indices:
        eta = df[f"jet{i}_eta"].to_numpy()
        phi = df[f"jet{i}_phi"].to_numpy()
        pt  = df[f"jet{i}_pt"].to_numpy()

        # basic jet sanity: pt > 0 and finite coords
        mask = (pt > 0) & np.isfinite(eta) & np.isfinite(phi)

        eta_all.append(eta[mask])
        phi_all.append(phi[mask])

eta = np.concatenate(eta_all)
phi = np.concatenate(phi_all)

# --------------------------------
# 2D histogram
# --------------------------------
h, _, _ = np.histogram2d(
    eta, phi,
    bins=[eta_bins, phi_bins]
)

# --------------------------------
# Plot
# --------------------------------
# plt.figure(figsize=(6, 5))
# plt.imshow(
#     h.T,
#     origin="lower",
#     aspect="auto",
#     extent=[eta_bins[0], eta_bins[-1], phi_bins[0], phi_bins[-1]]
# )
# plt.colorbar(label="Jets")
# plt.xlabel("Jet η")
# plt.ylabel("Jet φ")
# plt.title(
#     "2023 postBPix – GGJets_MGG-40to80\n"
#     "Jet η–φ (after jet veto, applied at sample level)"
# )

# plt.tight_layout()
# plt.savefig("jet_etaphi_2023postBPix_GGJets_MGG40to80.png")
# plt.close()


plt.figure(figsize=(7, 6))
hep.style.use("CMS")   # CMS typography & spacing

plt.imshow(
    h.T,
    origin="lower",
    aspect="auto",
    interpolation="nearest",
    norm=LogNorm(vmin=1),
    extent=[eta_bins[0], eta_bins[-1], phi_bins[0], phi_bins[-1]],
    cmap="inferno"
)

cbar = plt.colorbar(pad=0.02)
cbar.set_label("Jets per bin", fontsize=12)

plt.xlabel(r"Jet $\eta$", fontsize=13)
plt.ylabel(r"Jet $\phi$", fontsize=13)

# Acceptance / veto boundaries (subtle)
plt.axvline(2.5, color="white", ls="--", lw=1, alpha=0.7)
plt.axvline(-2.5, color="white", ls="--", lw=1, alpha=0.7)

# CMS-style annotation
hep.cms.text("Simulation", loc=0, fontsize=13)
hep.cms.lumitext("2022PostEE", fontsize=12)

# plt.title(
#     # "GGJets_MGG-40to80\n"
#     # "Jet $\eta$–$\phi$ after jet veto (sample level)",
#     fontsize=12
# )

plt.tight_layout()
plt.savefig(
    "jet_etaphi_2022PostEE_GGJets_MGG40to80_CMSstyle.png",
    dpi=300
)
plt.close()


print("Done.")
# --------------------------------