#!/usr/bin/env python3
"""
Produce the Sec 11.6 validation plot: data vs simulation pDNN_score
distributions in the diphoton mass sideband, for the mass hypothesis
actually baked into the current production (mX=600, mY=100), combining
2022+2023+2024.

Run inside the `hhbbgg-awk` micromamba environment on lxplus:
    micromamba activate hhbbgg-awk
    python3 plot_pdnn_score_validation.py

Outputs: pdnn_score_validation_sideband_mX600_mY100.png
"""

import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot

YEAR_DIRS = {
    "2022": "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2022_combined_trees",
    "2023": "/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2023_combined_trees",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024",
}

FILE_PREFIX = "hhbbgg_analyzer-v2-trees__"
REGION = "sideband"
WEIGHT_BRANCH = "weight_sideband"
SCORE_BRANCH = "pDNN_score"
MASS_LABEL = "mX=600 GeV, mY=100 GeV"

# SM background processes (same set used for Tables 16/17), plus the two
# data-driven-rescaled samples -- DDQCDGJets_Rescaled is known (from earlier
# checks) to have an EMPTY sideband tree, so it will just contribute zero;
# left in the list so that's visible/logged rather than silently omitted.
MC_PROCESSES = {
    "DDQCDGJets": (["DDQCDGJets_Rescaled"], "#94a4a2"),
    "$\\gamma\\gamma$+jets (raw)": (["GGJets_MGG-80"], "#3f90da"),
    "ggH": (["GluGluHtoGG"], "#ffa90e"),
    "VBFH": (["VBFHtoGG"], "#bd1f01"),
    "VH": (["VHtoGG", "WmHtoGG", "WpHtoGG", "ZHtoGG"], "#832db6"),
    "ttH": (["ttHtoGG"], "#a96b59"),
    "bbH": (["bbHtoGG"], "#e76300"),
}

N_BINS = 20
BIN_EDGES = np.linspace(0.0, 1.0, N_BINS + 1)
BIN_CENTERS = 0.5 * (BIN_EDGES[:-1] + BIN_EDGES[1:])


def find_sample_file(year_dir, sample_name):
    for suffix in ("nominal", "flat"):
        candidate = os.path.join(year_dir, f"{FILE_PREFIX}{sample_name}__{suffix}.root")
        if os.path.exists(candidate):
            return candidate
    return None


def find_data_files(year_dir):
    pattern = os.path.join(year_dir, f"{FILE_PREFIX}Data*__*.root")
    files = glob.glob(pattern)
    return [f for f in files if f.endswith("__nominal.root") or f.endswith("__flat.root")]


def get_region_tree(root_file_path, region):
    f = uproot.open(root_file_path)
    keys = f.keys()
    region_keys = [k for k in keys if k.split(";")[0].endswith(f"/{region}")]
    if not region_keys:
        return None
    return f[region_keys[0]]


def histogram_weighted(root_file_path, region, weight_branch, score_branch):
    """Return (hist_counts, hist_sumw2) for this file, or (None, None)."""
    tree = get_region_tree(root_file_path, region)
    if tree is None or tree.num_entries == 0:
        return None, None
    branches = tree.keys()
    if weight_branch not in branches or score_branch not in branches:
        return None, None
    w = tree[weight_branch].array(library="np")
    s = tree[score_branch].array(library="np")
    if len(s) == 0:
        return None, None
    counts, _ = np.histogram(s, bins=BIN_EDGES, weights=w)
    sumw2, _ = np.histogram(s, bins=BIN_EDGES, weights=w ** 2)
    return counts, sumw2


def histogram_data(root_file_path, region, score_branch):
    tree = get_region_tree(root_file_path, region)
    if tree is None or tree.num_entries == 0:
        return None
    branches = tree.keys()
    if score_branch not in branches:
        return None
    s = tree[score_branch].array(library="np")
    if len(s) == 0:
        return None
    counts, _ = np.histogram(s, bins=BIN_EDGES)
    return counts


def combine_mc_process(sample_names):
    total_counts = np.zeros(N_BINS)
    total_sumw2 = np.zeros(N_BINS)
    missing = []
    for year, year_dir in YEAR_DIRS.items():
        found_any = False
        for sample_name in sample_names:
            fpath = find_sample_file(year_dir, sample_name)
            if fpath is None:
                continue
            counts, sumw2 = histogram_weighted(fpath, REGION, WEIGHT_BRANCH, SCORE_BRANCH)
            if counts is None:
                continue
            found_any = True
            total_counts += counts
            total_sumw2 += sumw2
        if not found_any:
            missing.append(year)
    return total_counts, total_sumw2, missing


def combine_data():
    total_counts = np.zeros(N_BINS)
    for year, year_dir in YEAR_DIRS.items():
        for fpath in find_data_files(year_dir):
            counts = histogram_data(fpath, REGION, SCORE_BRANCH)
            if counts is not None:
                total_counts += counts
    return total_counts


def main():
    mc_hists = {}
    for label, (sample_names, color) in MC_PROCESSES.items():
        counts, sumw2, missing = combine_mc_process(sample_names)
        mc_hists[label] = (counts, sumw2, color)
        total = counts.sum()
        flag = f"  <-- EMPTY/MISSING in region '{REGION}': {missing or 'all years, zero entries'}" if total == 0 else ""
        print(f"{label:20s}  total weighted yield in sideband = {total:.4g}{flag}")

    data_counts = combine_data()
    print(f"{'Data':20s}  total entries in sideband = {data_counts.sum():.0f}")

    # ---- Build stacked MC ----
    labels_with_yield = [(lbl, mc_hists[lbl][0], mc_hists[lbl][2])
                          for lbl in MC_PROCESSES if mc_hists[lbl][0].sum() > 0]
    # sort smallest-to-largest so the biggest component sits at the bottom of the stack
    labels_with_yield.sort(key=lambda x: x[1].sum())

    fig, (ax_main, ax_ratio) = plt.subplots(
        2, 1, sharex=True, figsize=(7, 6.5),
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
    )

    bottom = np.zeros(N_BINS)
    mc_total = np.zeros(N_BINS)
    mc_total_sumw2 = np.zeros(N_BINS)
    for lbl, counts, color in labels_with_yield:
        ax_main.bar(BIN_CENTERS, counts, width=(BIN_EDGES[1] - BIN_EDGES[0]),
                    bottom=bottom, color=color, edgecolor="black", linewidth=0.3,
                    label=lbl)
        bottom += counts
        mc_total += counts
    for lbl in MC_PROCESSES:
        mc_total_sumw2 += mc_hists[lbl][1]
    mc_total_err = np.sqrt(mc_total_sumw2)

    # MC stat uncertainty band
    ax_main.bar(BIN_CENTERS, 2 * mc_total_err, width=(BIN_EDGES[1] - BIN_EDGES[0]),
                bottom=mc_total - mc_total_err, color="none", hatch="////",
                edgecolor="gray", linewidth=0, label="MC stat. unc.")

    # Data points with Poisson errors
    data_err = np.sqrt(data_counts)
    ax_main.errorbar(BIN_CENTERS, data_counts, yerr=data_err, fmt="o",
                      color="black", markersize=4, label="Data", zorder=10)

    ax_main.set_ylabel("Events")
    ax_main.set_title(f"pDNN score validation, sideband ({MASS_LABEL}), 2022+2023+2024",
                       fontsize=10, weight="bold")
    ax_main.legend(fontsize=7, ncol=2)
    ax_main.set_yscale("log")

    # ---- Ratio panel ----
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mc_total > 0, data_counts / mc_total, np.nan)
        ratio_err = np.where(mc_total > 0, data_err / mc_total, np.nan)
    ax_ratio.errorbar(BIN_CENTERS, ratio, yerr=ratio_err, fmt="o", color="black", markersize=4)
    ax_ratio.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax_ratio.set_ylim(0, 2)
    ax_ratio.set_xlabel("pDNN score")
    ax_ratio.set_ylabel("Data / MC")

    fig.tight_layout()
    out_path = "pdnn_score_validation_sideband_mX600_mY100_raw_ggjets.png"
    fig.savefig(out_path, dpi=220, facecolor="white")
    plt.close(fig)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()