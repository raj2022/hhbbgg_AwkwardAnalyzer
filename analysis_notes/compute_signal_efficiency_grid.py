#!/usr/bin/env python3
"""
Compute signal efficiency = srbbgg_yield / preselection_yield across the
full NMSSM (mX, mY) mass grid, combining 2022+2023+2024.

Definitions (per user confirmation):
  - preselection yield: weight_preselection, summed over the
    'preselection' tree, no additional cuts.
  - srbbgg yield: weight_srbbgg, summed over the 'srbbgg' tree, RAW
    (no |mgg-125|<2 GeV cut applied) -- matches Table 16's convention,
    NOT the tight true-SR convention used in Eq. 15/16 / Sec 11.7.
  - efficiency = srbbgg_yield / preselection_yield, per mass point.

Run inside the `hhbbgg-awk` micromamba environment on lxplus:
    micromamba activate hhbbgg-awk
    python3 compute_signal_efficiency_grid.py
"""

import glob
import os
import re

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

# Petroff-style palette, consistent with other plots in this analysis
PETROFF_COLORS = ["#3f90da", "#ffa90e", "#bd1f01", "#832db6", "#94a4a2",
                   "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"]


def discover_nmssm_points():
    points = set()
    pattern = re.compile(r"^NMSSM_X(\d+)_Y(\d+)$")
    for year_dir in YEAR_DIRS.values():
        files = glob.glob(os.path.join(year_dir, f"{FILE_PREFIX}NMSSM_X*__*.root"))
        for fpath in files:
            base = os.path.basename(fpath)
            if not (base.endswith("__nominal.root") or base.endswith("__flat.root")):
                continue
            sample = base[len(FILE_PREFIX):]
            sample = re.sub(r"__(nominal|flat)\.root$", "", sample)
            m = pattern.match(sample)
            if m:
                points.add((int(m.group(1)), int(m.group(2))))
    return sorted(points)


def find_sample_file(year_dir, sample_name):
    for suffix in ("nominal", "flat"):
        candidate = os.path.join(year_dir, f"{FILE_PREFIX}{sample_name}__{suffix}.root")
        if os.path.exists(candidate):
            return candidate
    return None


def get_region_tree(root_file_path, region):
    f = uproot.open(root_file_path)
    keys = f.keys()
    region_keys = [k for k in keys if k.split(";")[0].endswith(f"/{region}")]
    if not region_keys:
        return None
    return f[region_keys[0]]


def sum_weighted_yield(root_file_path, region, weight_branch):
    tree = get_region_tree(root_file_path, region)
    if tree is None or tree.num_entries == 0:
        return 0.0, 0
    branches = tree.keys()
    if weight_branch not in branches:
        return 0.0, 0
    w = tree[weight_branch].array(library="np")
    return float(w.sum()), len(w)


def combine_years(sample_name, region, weight_branch):
    total = 0.0
    total_n = 0
    missing = []
    for year, year_dir in YEAR_DIRS.items():
        fpath = find_sample_file(year_dir, sample_name)
        if fpath is None:
            missing.append(year)
            continue
        yld, n = sum_weighted_yield(fpath, region, weight_branch)
        total += yld
        total_n += n
    return total, total_n, missing


def main():
    points = discover_nmssm_points()
    print(f"Discovered {len(points)} NMSSM mass points.\n")

    results = {}
    for mx, my in points:
        sample_name = f"NMSSM_X{mx}_Y{my}"
        presel_yield, presel_n, presel_missing = combine_years(
            sample_name, "preselection", "weight_preselection")
        srbbgg_yield, srbbgg_n, srbbgg_missing = combine_years(
            sample_name, "srbbgg", "weight_srbbgg")

        if presel_yield <= 0:
            eff = float("nan")
        else:
            eff = srbbgg_yield / presel_yield

        results[(mx, my)] = {
            "presel_yield": presel_yield, "presel_n": presel_n,
            "srbbgg_yield": srbbgg_yield, "srbbgg_n": srbbgg_n,
            "efficiency": eff,
            "presel_missing": presel_missing, "srbbgg_missing": srbbgg_missing,
        }

        flag = ""
        if presel_missing or srbbgg_missing:
            flag = f"  <-- missing years: presel={presel_missing}, srbbgg={srbbgg_missing}"
        print(f"mX={mx:5d} mY={my:4d}  presel={presel_yield:10.4g}  "
              f"srbbgg={srbbgg_yield:10.4g}  eff={eff:.4f}{flag}")

    # ---- write a flat CSV/table for reference ----
    with open("signal_efficiency_grid.csv", "w") as f:
        f.write("mX,mY,preselection_yield,srbbgg_yield,efficiency\n")
        for (mx, my), r in sorted(results.items()):
            f.write(f"{mx},{my},{r['presel_yield']:.6g},{r['srbbgg_yield']:.6g},{r['efficiency']:.6f}\n")
    print("\nWrote signal_efficiency_grid.csv")

    # ---- plot: efficiency vs mY, one line per mX ----
    mx_values = sorted(set(mx for mx, my in results))
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, mx in enumerate(mx_values):
        my_vals = sorted(my for (x, my) in results if x == mx)
        eff_vals = [results[(mx, my)]["efficiency"] for my in my_vals]
        color = PETROFF_COLORS[i % len(PETROFF_COLORS)]
        ax.plot(my_vals, eff_vals, marker="o", markersize=3, linewidth=1.2,
                color=color, label=f"$m_X$={mx}")

    ax.set_xlabel(r"$m_Y$ [GeV]")
    ax.set_ylabel("Efficiency (srbbgg / preselection)")
    ax.set_title("Signal efficiency across the NMSSM mass grid\n"
                  "(srbbgg tree, no mgg cut, combining 2022+2023+2024)",
                  fontsize=10, weight="bold")
    ax.legend(fontsize=6, ncol=3, loc="best")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("signal_efficiency_vs_mY.png", dpi=200, facecolor="white")
    plt.close(fig)
    print("Wrote signal_efficiency_vs_mY.png")

    # ---- second plot: efficiency vs mX, one line per mY ----
    my_values = sorted(set(my for mx, my in results))
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, my in enumerate(my_values):
        mx_vals = sorted(mx for (mx, y) in results if y == my)
        eff_vals = [results[(mx, my)]["efficiency"] for mx in mx_vals]
        color = PETROFF_COLORS[i % len(PETROFF_COLORS)]
        ax.plot(mx_vals, eff_vals, marker="o", markersize=3, linewidth=1.2,
                color=color, label=f"$m_Y$={my}")

    ax.set_xlabel(r"$m_X$ [GeV]")
    ax.set_ylabel("Efficiency (srbbgg / preselection)")
    ax.set_title("Signal efficiency across the NMSSM mass grid\n"
                  "(srbbgg tree, no mgg cut, combining 2022+2023+2024)",
                  fontsize=10, weight="bold")
    ax.legend(fontsize=6, ncol=3, loc="best")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("signal_efficiency_vs_mX.png", dpi=200, facecolor="white")
    plt.close(fig)
    print("Wrote signal_efficiency_vs_mX.png")


if __name__ == "__main__":
    main()