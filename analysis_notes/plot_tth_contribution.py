#!/usr/bin/env python3
"""
Compute the residual ttH contribution across the full (mX, mY) mass grid,
using each mass hypothesis's OWN pDNN category thresholds from
event_categories.json (not the fixed ttH-killer WP cuts) -- since ttH
itself doesn't have a mass, this shows how much ttH leaks into "any
accepted category" purely because the threshold itself shifts per
hypothesis, mirroring exactly how the Sec 11.7 signal/background yield
table was built.

Definitions (matching categorize_events.py / the Sec 11.7 table):
  - SR: |mgg-125| < 2 GeV cut applied on top of the srbbgg tree.
  - Weight branch: weight_srbbgg.
  - ttH "contribution" at a given (mX, mY, year) = sum of weight_srbbgg
    for ttH SR events with pDNN_score >= min(edges) for that mass point
    -- i.e. landing in ANY accepted category, not just the tightest one.

Shown per year separately (category boundaries differ by year), plus a
combined-years total.

Run inside the `hhbbgg-awk` micromamba environment on lxplus:
    micromamba activate hhbbgg-awk
    python3 plot_tth_contribution_grid.py
"""

import glob
import json
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

CATEGORY_JSON = {
    "2022": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022/event_categories.json",
    "2023": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023/event_categories.json",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024/event_categories.json",
}

FILE_PREFIX = "hhbbgg_analyzer-v2-trees__"
TREE_NAME = "srbbgg"
BR_WGT = "weight_srbbgg"
BR_SCORE = "pDNN_score"
BR_MGG = "diphoton_mass"
SR_LO, SR_HI = 123.0, 127.0

SAMPLE_NAME = "ttHtoGG"


def find_sample_file(year_dir, sample_name):
    for suffix in ("nominal", "flat"):
        candidate = os.path.join(year_dir, f"{FILE_PREFIX}{sample_name}__{suffix}.root")
        if os.path.exists(candidate):
            return candidate
    return None


def get_srbbgg_tree(root_file_path):
    f = uproot.open(root_file_path)
    keys = f.keys()
    tree_keys = [k for k in keys if k.split(";")[0].endswith(f"/{TREE_NAME}")]
    if not tree_keys:
        return None
    return f[tree_keys[0]]


def load_ttH_sr_data(year_dir):
    """Return (mgg, score, weight) arrays for ttH's SR-selected events in
    this year, or None if unavailable."""
    fpath = find_sample_file(year_dir, SAMPLE_NAME)
    if fpath is None:
        return None
    tree = get_srbbgg_tree(fpath)
    if tree is None or tree.num_entries == 0:
        return None
    branches = tree.keys()
    if not {BR_MGG, BR_SCORE, BR_WGT}.issubset(branches):
        return None
    mgg = tree[BR_MGG].array(library="np")
    score = tree[BR_SCORE].array(library="np")
    w = tree[BR_WGT].array(library="np")
    in_sr = (mgg >= SR_LO) & (mgg <= SR_HI)
    return score[in_sr], w[in_sr]


def main():
    # cache ttH SR score/weight per year (same data reused for every mass point)
    ttH_sr_data = {}
    for year, year_dir in YEAR_DIRS.items():
        ttH_sr_data[year] = load_ttH_sr_data(year_dir)
        if ttH_sr_data[year] is None:
            print(f"[{year}] WARNING: could not load ttH SR data.")
        else:
            score, w = ttH_sr_data[year]
            print(f"[{year}] ttH SR events: {len(score)}, total weight: {w.sum():.4g}")

    # load boundaries per year
    boundaries_per_year = {}
    for year, path in CATEGORY_JSON.items():
        with open(path) as f:
            boundaries_per_year[year] = json.load(f)["boundaries"]

    # union of all mass points across years
    all_points = set()
    for b in boundaries_per_year.values():
        for key in b:
            all_points.add(key)

    results = {}  # (mx, my) -> {year: yield or None}
    for mass_tag in sorted(all_points):
        # parse mX###_mY### -> (mx, my)
        try:
            mx_part, my_part = mass_tag.split("_")
            mx = int(mx_part.replace("mX", ""))
            my = int(my_part.replace("mY", ""))
        except Exception:
            continue

        per_year_yield = {}
        for year in YEAR_DIRS:
            edges = boundaries_per_year[year].get(mass_tag)
            if edges is None or ttH_sr_data[year] is None:
                per_year_yield[year] = None
                continue
            score, w = ttH_sr_data[year]
            lowest_edge = min(edges)
            sel = score >= lowest_edge
            per_year_yield[year] = float(w[sel].sum())

        results[(mx, my)] = per_year_yield

    # ---- CSV ----
    with open("tth_contribution_grid.csv", "w") as f:
        f.write("mX,mY,2022,2023,2024,combined\n")
        for (mx, my), per_year in sorted(results.items()):
            vals = [per_year[y] for y in YEAR_DIRS]
            combined = sum(v for v in vals if v is not None)
            row = [str(mx), str(my)]
            for v in vals:
                row.append(f"{v:.6g}" if v is not None else "")
            row.append(f"{combined:.6g}")
            f.write(",".join(row) + "\n")
    print("\nWrote tth_contribution_grid.csv")

    # ---- heatmaps: one per year, plus combined ----
    def plot_heatmap(values_by_point, title, out_path):
        mx_values = sorted(set(mx for mx, my in values_by_point))
        my_values = sorted(set(my for mx, my in values_by_point))
        mx_index = {mx: i for i, mx in enumerate(mx_values)}
        my_index = {my: j for j, my in enumerate(my_values)}

        grid = np.full((len(mx_values), len(my_values)), np.nan)
        for (mx, my), val in values_by_point.items():
            if val is not None:
                grid[mx_index[mx], my_index[my]] = val

        fig, ax = plt.subplots(figsize=(0.42 * len(my_values) + 2.2, 0.32 * len(mx_values) + 2.2))
        masked = np.ma.masked_invalid(grid)
        cmap = plt.cm.magma.copy()
        cmap.set_bad(color="#e8e8e8")
        vmax = np.nanmax(grid) if np.isfinite(np.nanmax(grid)) else 1.0
        im = ax.imshow(masked, cmap=cmap, aspect="auto", origin="lower", vmin=0, vmax=vmax)

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
        ax.set_title(title, fontsize=10, weight="bold")

        for i in range(len(mx_values)):
            for j in range(len(my_values)):
                val = grid[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.2g}", ha="center", va="center",
                            fontsize=5, color="white" if val < 0.5 * vmax else "black")

        cbar = fig.colorbar(im, ax=ax, label="ttH residual yield (weighted)")
        cbar.ax.tick_params(labelsize=8)
        fig.tight_layout()
        fig.savefig(out_path, dpi=200, facecolor="white")
        plt.close(fig)
        print(f"Wrote {out_path}")

    for year in YEAR_DIRS:
        values = {pt: per_year[year] for pt, per_year in results.items()}
        plot_heatmap(values, f"ttH residual contribution across mass grid -- {year}\n"
                              f"(mass-hypothesis-specific pDNN threshold, any category)",
                     f"tth_contribution_heatmap_{year}.png")

    combined_values = {}
    for pt, per_year in results.items():
        vals = [v for v in per_year.values() if v is not None]
        combined_values[pt] = sum(vals) if vals else None
    plot_heatmap(combined_values, "ttH residual contribution across mass grid -- combined 2022+2023+2024\n"
                                   "(mass-hypothesis-specific pDNN threshold, any category)",
                 "tth_contribution_heatmap_combined.png")


if __name__ == "__main__":
    main()