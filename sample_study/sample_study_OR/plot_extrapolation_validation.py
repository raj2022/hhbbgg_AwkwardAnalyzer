import os
import glob
import numpy as np
import awkward as ak
import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (8, 8)
plt.rcParams["font.size"] = 12

# =====================================================
# Configuration
# =====================================================
BASE_DIR = "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE"

OUTDIR = os.path.join(BASE_DIR, "plots_extrapolation_postEE")
os.makedirs(OUTDIR, exist_ok=True)

# Binning
NJET_BINS = np.arange(0, 9, 1)        # 0–8 jets
HT_BINS   = np.linspace(0, 1000, 21)  # 0–1000 GeV

# =====================================================
# File collection
# =====================================================
data_files = sorted(glob.glob(os.path.join(BASE_DIR, "Data_Era*.parquet")))

mc_files = [
    f for f in glob.glob(os.path.join(BASE_DIR, "*.parquet"))
    if not os.path.basename(f).startswith("Data_")
    and not os.path.basename(f).startswith("NMSSM_")  # exclude signal
]

print("\n▶ Data files:")
for f in data_files:
    print("  ", os.path.basename(f))

print("\n▶ MC files:")
for f in mc_files:
    print("  ", os.path.basename(f))

# =====================================================
# Physics variables (ANALYZER-CONSISTENT)
# =====================================================
def compute_njets(events):
    # Use analyzer-defined jet multiplicity
    return events.Njets2p5

def compute_ht(events):
    # HT = sum of jet pt from jet1_pt ... jet10_pt
    ht = ak.zeros_like(events.event)

    for i in range(1, 11):
        pt_name = f"jet{i}_pt"
        if pt_name in events.fields:
            pt = events[pt_name]
            ht = ht + ak.where(pt > 0, pt, 0)

    return ht

def get_weights(events):
    if "weight" in events.fields:
        return events.weight
    return ak.ones_like(events.event)

# =====================================================
# Histogram filling
# =====================================================
def fill_hist(files, bins, varfunc):
    hist = np.zeros(len(bins) - 1)
    err2 = np.zeros(len(bins) - 1)

    for f in files:
        events = ak.from_parquet(f)

        values  = ak.to_numpy(varfunc(events))
        weights = ak.to_numpy(get_weights(events))

        h,  _ = np.histogram(values, bins=bins, weights=weights)
        h2, _ = np.histogram(values, bins=bins, weights=weights**2)

        hist += h
        err2 += h2

    return hist, np.sqrt(err2)

# =====================================================
# Plotting
# =====================================================
def plot_data_mc_ratio(
    data, data_err,
    mc, mc_err,
    bins, xlabel, name
):
    centers = 0.5 * (bins[1:] + bins[:-1])

    fig, (ax, rax) = plt.subplots(
        2, 1,
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True
    )

    # --- Top pad: Data vs MC ---
    ax.errorbar(
        centers, data,
        yerr=data_err,
        fmt="o", color="black",
        label="Data"
    )

    ax.step(
        bins[:-1], mc,
        where="post",
        color="steelblue",
        label="MC"
    )

    ax.fill_between(
        bins[:-1],
        mc - mc_err,
        mc + mc_err,
        step="post",
        color="steelblue",
        alpha=0.3
    )

    ax.set_ylabel("Events")
    ax.set_ylim(0, max(data.max(), mc.max()) * 1.4)
    ax.legend()
    ax.text(
        0.02, 0.93,
        "PostEE\nData / MC extrapolation",
        transform=ax.transAxes
    )

    # --- Bottom pad: Ratio ---
    ratio = np.divide(
        data, mc,
        out=np.zeros_like(data),
        where=mc > 0
    )

    ratio_err = ratio * np.sqrt(
        (data_err / np.maximum(data, 1e-9))**2 +
        (mc_err / np.maximum(mc, 1e-9))**2
    )

    rax.errorbar(
        centers, ratio,
        yerr=ratio_err,
        fmt="o", color="black"
    )

    rax.axhline(1.0, linestyle="--", color="gray")
    rax.set_ylabel("Data / MC")
    rax.set_xlabel(xlabel)
    rax.set_ylim(0.5, 1.5)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f"{name}.pdf"))
    plt.savefig(os.path.join(OUTDIR, f"{name}.png"))
    plt.close()

# =====================================================
# Run
# =====================================================
print("\n▶ Filling Njets histograms")
data_nj, data_nj_err = fill_hist(data_files, NJET_BINS, compute_njets)
mc_nj,   mc_nj_err   = fill_hist(mc_files,   NJET_BINS, compute_njets)

plot_data_mc_ratio(
    data_nj, data_nj_err,
    mc_nj, mc_nj_err,
    NJET_BINS,
    xlabel="Jet multiplicity (Njets2p5)",
    name="DataMC_ratio_Njets_postEE"
)

print("▶ Filling HT histograms")
data_ht, data_ht_err = fill_hist(data_files, HT_BINS, compute_ht)
mc_ht,   mc_ht_err   = fill_hist(mc_files,   HT_BINS, compute_ht)

plot_data_mc_ratio(
    data_ht, data_ht_err,
    mc_ht, mc_ht_err,
    HT_BINS,
    xlabel="H$_T$ [GeV]",
    name="DataMC_ratio_HT_postEE"
)

print("\n✅ All postEE extrapolation plots produced successfully")
print(f"📁 Output directory: {OUTDIR}")
