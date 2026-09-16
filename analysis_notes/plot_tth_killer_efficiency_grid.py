#!/usr/bin/env python3
"""
Compute NMSSM signal efficiency at each ttH-killer working point across
the FULL (mX, mY) mass grid, combining 2022+2023+2024, and produce
heatmap figures (mY on x-axis, mX on y-axis) for each working point and
selection stage -- for an appendix answering the convenor's question:
"have you checked the signal efficiency across all resonant masses?"

Run inside the `hhbbgg-awk` micromamba environment on lxplus:
    micromamba activate hhbbgg-awk
    python3 plot_tth_killer_efficiency_grid.py

Outputs:
    tth_killer_efficiency_grid.csv       full numeric table, all points
    tth_killer_eff_heatmap_preselection_Loose.png   (and Medium/Tight)
    tth_killer_eff_heatmap_srbbgg_Loose.png         (and Medium/Tight)
"""

import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import uproot

YEAR_DIRS = {
    "2022": "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2022_combined_trees",
    "2023": "/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2023_combined_trees",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024",
}

FILE_PREFIX = "hhbbgg_analyzer-v2-trees__"
SCORE_BRANCH = "ttH_killer_score"

WORKING_POINTS = {
    "Loose": 0.924,
    "Medium": 0.682,
    "Tight": 0.401,
}

REGIONS = {
    "preselection": "weight_preselection",
    "srbbgg": "weight_srbbgg",
}


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


def region_score_and_weight(root_file_path, region, weight_branch):
    tree = get_region_tree(root_file_path, region)
    if tree is None or tree.num_entries == 0:
        return None, None
    branches = tree.keys()
    if weight_branch not in branches or SCORE_BRANCH not in branches:
        return None, None
    w = tree[weight_branch].array(library="np")
    s = tree[SCORE_BRANCH].array(library="np")
    return w, s


def efficiency_for_point(mx, my, region, weight_branch):
    sample_name = f"NMSSM_X{mx}_Y{my}"
    total_weight = 0.0
    passing_weight = {wp: 0.0 for wp in WORKING_POINTS}
    missing = []

    for year, year_dir in YEAR_DIRS.items():
        fpath = find_sample_file(year_dir, sample_name)
        if fpath is None:
            missing.append(f"{year}:no-file")
            continue
        w, s = region_score_and_weight(fpath, region, weight_branch)
        if w is None:
            missing.append(f"{year}:no-{region}-or-no-score-branch")
            continue
        total_weight += float(w.sum())
        for wp_name, cut in WORKING_POINTS.items():
            mask = s < cut
            passing_weight[wp_name] += float(w[mask].sum())

    if total_weight == 0:
        return None, missing

    effs = {wp: (passing_weight[wp] / total_weight) for wp in WORKING_POINTS}
    return effs, missing


def plot_heatmap(region, wp_name, results, points, out_path):
    mx_values = sorted(set(mx for mx, my in points))
    my_values = sorted(set(my for mx, my in points))
    mx_index = {mx: i for i, mx in enumerate(mx_values)}
    my_index = {my: j for j, my in enumerate(my_values)}

    grid = np.full((len(mx_values), len(my_values)), np.nan)
    for (mx, my), eff in results.items():
        if eff is not None:
            grid[mx_index[mx], my_index[my]] = eff * 100.0

    fig, ax = plt.subplots(figsize=(0.42 * len(my_values) + 2.2, 0.32 * len(mx_values) + 2.2))
    masked = np.ma.masked_invalid(grid)
    cmap = plt.cm.viridis.copy()
    cmap.set_bad(color="#e8e8e8")
    im = ax.imshow(masked, cmap=cmap, aspect="auto", origin="lower", vmin=0, vmax=100)

    ax.set_xticks(np.arange(-0.5, len(my_values), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(mx_values), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", length=0)

    ax.set_xticks(range(len(my_values)))
    ax.set_xticklabels(my_values, rotation=90, fontsize=7)
    ax.set_yticks(range(len(mx_values)))
    ax.set_yticklabels(mx_values, fontsize=7)
    ax.set_xlabel(r"$m_Y$ [GeV]", fontsize=10)
    ax.set_ylabel(r"$m_X$ [GeV]", fontsize=10)
    ax.set_title(f"NMSSM signal efficiency (%) -- {wp_name} WP, {region}",
                 fontsize=10, weight="bold")

    for i in range(len(mx_values)):
        for j in range(len(my_values)):
            val = grid[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        fontsize=5.5, color="white" if val < 55 else "black")

    cbar = fig.colorbar(im, ax=ax, label="Efficiency (%)")
    cbar.ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    points = discover_nmssm_points()
    print(f"Discovered {len(points)} NMSSM mass points.\n")

    # results[region][wp_name][(mx,my)] = efficiency (or None)
    all_results = {region: {wp: {} for wp in WORKING_POINTS} for region in REGIONS}

    csv_rows = []
    for region, weight_branch in REGIONS.items():
        print(f"=== region = {region} ===")
        for mx, my in points:
            effs, missing = efficiency_for_point(mx, my, region, weight_branch)
            for wp_name in WORKING_POINTS:
                all_results[region][wp_name][(mx, my)] = effs[wp_name] if effs else None
            if effs:
                csv_rows.append((mx, my, region, effs["Loose"], effs["Medium"], effs["Tight"], missing))
            else:
                csv_rows.append((mx, my, region, None, None, None, missing))

    with open("tth_killer_efficiency_grid.csv", "w") as f:
        f.write("mX,mY,region,eff_Loose,eff_Medium,eff_Tight,missing_years\n")
        for mx, my, region, l, m, t, missing in csv_rows:
            l_s = f"{l:.6f}" if l is not None else ""
            m_s = f"{m:.6f}" if m is not None else ""
            t_s = f"{t:.6f}" if t is not None else ""
            missing_s = ";".join(missing) if missing else ""
            f.write(f"{mx},{my},{region},{l_s},{m_s},{t_s},{missing_s}\n")
    print("\nWrote tth_killer_efficiency_grid.csv")

    for region in REGIONS:
        for wp_name in WORKING_POINTS:
            out_path = f"tth_killer_eff_heatmap_{region}_{wp_name}.png"
            plot_heatmap(region, wp_name, all_results[region][wp_name], points, out_path)


if __name__ == "__main__":
    main()