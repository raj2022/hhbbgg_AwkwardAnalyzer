#!/usr/bin/env python3
"""
Plot a heatmap per year: mY on x-axis, mX on y-axis, cell color/value =
number of AMS2-selected categories for that mass point.

Run inside the `hhbbgg-awk` micromamba environment (needs matplotlib and
numpy, both standard in that env):
    micromamba activate hhbbgg-awk
    python3 plot_category_count_heatmaps.py

Outputs three PNG files in the current directory:
    category_count_heatmap_2022.png
    category_count_heatmap_2023.png
    category_count_heatmap_2024.png
"""

import json
import re

import matplotlib
matplotlib.use("Agg")  # no display needed on lxplus
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# CMS "Petroff" palette (first 5 colors), for consistency with the rest of
# the analysis's plotting style. One solid color per discrete category
# count (1-5) rather than a continuous colormap, since this is categorical
# data, not a continuous quantity.
PETROFF_COLORS = ["#3f90da", "#ffa90e", "#bd1f01", "#832db6", "#94a4a2"]

YEAR_FILES = {
    "2022": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022/event_categories.json",
    "2023": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023/event_categories.json",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024/event_categories.json",
}

MASS_POINT_RE = re.compile(r"^mX(\d+)_mY(\d+)$")


def load_counts(path):
    with open(path) as f:
        data = json.load(f)
    boundaries = data["boundaries"]
    counts = {}
    for key, b in boundaries.items():
        m = MASS_POINT_RE.match(key)
        if not m:
            continue
        mx, my = int(m.group(1)), int(m.group(2))
        counts[(mx, my)] = len(b)
    return counts


def plot_heatmap(year, counts, out_path):
    mx_values = sorted(set(mx for mx, my in counts))
    my_values = sorted(set(my for mx, my in counts))

    # grid: rows = mX (y-axis), cols = mY (x-axis)
    grid = np.full((len(mx_values), len(my_values)), np.nan)
    mx_index = {mx: i for i, mx in enumerate(mx_values)}
    my_index = {my: j for j, my in enumerate(my_values)}

    for (mx, my), n_cat in counts.items():
        grid[mx_index[mx], my_index[my]] = n_cat

    plt.rcParams.update({
        "font.family": "sans-serif",
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
    })

    fig, ax = plt.subplots(figsize=(0.42 * len(my_values) + 2.2, 0.32 * len(mx_values) + 2.2))
    masked = np.ma.masked_invalid(grid)

    # Discrete colormap: one solid color per integer category count 1-5.
    cmap = mcolors.ListedColormap(PETROFF_COLORS)
    cmap.set_bad(color="#e8e8e8")  # missing mass points (e.g. absent 2024 sample)
    bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(masked, cmap=cmap, norm=norm, aspect="auto", origin="lower")

    # thin white gridlines separating each cell
    ax.set_xticks(np.arange(-0.5, len(my_values), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(mx_values), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

    ax.set_xticks(range(len(my_values)))
    ax.set_xticklabels(my_values, rotation=90, fontsize=7)
    ax.set_yticks(range(len(mx_values)))
    ax.set_yticklabels(mx_values, fontsize=7)
    ax.set_xlabel(r"$m_Y$ [GeV]", fontsize=10)
    ax.set_ylabel(r"$m_X$ [GeV]", fontsize=10)
    ax.set_title(f"AMS2 category count \u2014 {year}", fontsize=11, weight="bold")

    # annotate each cell with the number (skip NaN/missing points);
    # text color chosen per-category for readability against its own fill
    text_colors = {1: "white", 2: "#333333", 3: "white", 4: "white", 5: "#333333"}
    for i in range(len(mx_values)):
        for j in range(len(my_values)):
            val = grid[i, j]
            if not np.isnan(val):
                ax.text(
                    j, i, int(val),
                    ha="center", va="center",
                    fontsize=6.5,
                    color=text_colors.get(int(val), "black"),
                    fontweight="medium",
                )

    cbar = fig.colorbar(im, ax=ax, ticks=[1, 2, 3, 4, 5], label="Number of categories")
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label("Number of categories", fontsize=9)

    for spine in ax.spines.values():
        spine.set_visible(True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=220, facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}  ({len(counts)} mass points, "
          f"{len(mx_values)} mX values x {len(my_values)} mY values)")


def main():
    for year, path in YEAR_FILES.items():
        counts = load_counts(path)
        out_path = f"category_count_heatmap_{year}.png"
        plot_heatmap(year, counts, out_path)


if __name__ == "__main__":
    main()