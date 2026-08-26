#!/usr/bin/env python3
"""
plot_signal_efficiency.py

Relative signal efficiency across the (mX, mY) grid: the fraction of
events surviving from a baseline stage (default: "preselection") to
the final signal-region stage (default: "srbbgg"), using the sibling
region trees already confirmed present under each mass point's
"{sample}/{systematic}/{region}" structure (e.g.
"NMSSM_X600_Y300/nominal/srbbgg").

This is RELATIVE efficiency (selection stage -> SR stage), not
efficiency relative to total generated events -- that would need the
total-generated/genEventSumw count, which isn't read here (location
not yet confirmed in this pipeline).

Produces two plots: a line plot (efficiency vs mY, one line per mX)
and a 2D heatmap (mX vs mY grid).

Usage:
    python plot_signal_efficiency.py \
        --analyzer-root-base /path/to/outputfiles/merged/DD_2024 \
        --mass-x 600 1000 \
        --out-line signal_eff_lines.png \
        --out-heatmap signal_eff_heatmap.png
"""

import argparse
import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
import uproot

CMS_BLUE = "#3f90da"
CMS_ORANGE = "#ffa90e"
CMS_RED = "#bd1f01"
CMS_GRAY = "#94a4a2"
CMS_PURPLE = "#832db6"
CMS_BROWN = "#a96b59"
PALETTE = [CMS_BLUE, CMS_ORANGE, CMS_RED, CMS_PURPLE, CMS_BROWN, CMS_GRAY]

LUMI_FB = 108.96
CM_ENERGY_TEV = 13.6


def find_signal_tree_file(analyzer_root_base, mass_x, mass_y):
    sample = f"NMSSM_X{mass_x}_Y{mass_y}"
    candidates = [
        os.path.join(analyzer_root_base, f"hhbbgg_analyzer-v2-trees__{sample}.root"),
        os.path.join(analyzer_root_base, f"hhbbgg_analyzer-v2-trees__{sample}__nominal.root"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def discover_mass_y_values(analyzer_root_base, mass_x):
    pattern = os.path.join(analyzer_root_base, f"hhbbgg_analyzer-v2-trees__NMSSM_X{mass_x}_Y*.root")
    y_values = []
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        m = re.search(rf"NMSSM_X{mass_x}_Y(\d+(?:\.\d+)?)", base)
        if m and m.group(1) not in y_values:
            y_values.append(m.group(1))
    return sorted(y_values, key=float)


def get_tree_count(root_path, sample, systematic, region, wgt_branch):
    """Returns (raw_count, weighted_count) for a given region tree, or
    (None, None) if the tree doesn't exist in this file."""
    full_path = f"{sample}/{systematic}/{region}"
    with uproot.open(root_path) as f:
        if full_path not in f:
            return None, None
        tree = f[full_path]
        n_raw = tree.num_entries
        if wgt_branch in tree.keys():
            w = tree[wgt_branch].array(library="np")
            w = w[np.isfinite(w)]
            n_weighted = float(np.sum(w))
        else:
            n_weighted = float(n_raw)
        return n_raw, n_weighted


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analyzer-root-base", required=True)
    ap.add_argument("--mass-x", nargs="+", required=True, help="One or more mX values.")
    ap.add_argument("--mass-y", nargs="*", default=None,
                     help="Specific mY values; omit to auto-discover per mX.")
    ap.add_argument("--systematic", default="nominal")
    ap.add_argument("--denominator-region", default="preselection",
                     help="Baseline stage tree name (default: preselection).")
    ap.add_argument("--numerator-region", default="srbbgg",
                     help="Final-stage tree name (default: srbbgg).")
    ap.add_argument("--wgt-branch", default="weight_selection")
    ap.add_argument("--out-line", default="signal_efficiency_lines.png")
    ap.add_argument("--out-heatmap", default="signal_efficiency_heatmap.png")
    args = ap.parse_args()

    # results[mx][my] = (raw_eff, weighted_eff)
    results = {}

    for mass_x in args.mass_x:
        mass_y_values = args.mass_y
        if not mass_y_values:
            mass_y_values = discover_mass_y_values(args.analyzer_root_base, mass_x)
            print(f"[INFO] mX={mass_x}: auto-discovered {len(mass_y_values)} mY value(s): {mass_y_values}")

        results[mass_x] = {}
        for mass_y in mass_y_values:
            sample = f"NMSSM_X{mass_x}_Y{mass_y}"
            tree_path = find_signal_tree_file(args.analyzer_root_base, mass_x, mass_y)
            if tree_path is None:
                print(f"[WARN] {sample}: no tree file found -- skipped.")
                continue

            n_denom_raw, n_denom_w = get_tree_count(
                tree_path, sample, args.systematic, args.denominator_region, args.wgt_branch)
            n_num_raw, n_num_w = get_tree_count(
                tree_path, sample, args.systematic, args.numerator_region, args.wgt_branch)

            if n_denom_raw is None or n_num_raw is None:
                print(f"[WARN] {sample}: denominator or numerator tree "
                      f"('{args.denominator_region}'/'{args.numerator_region}') not found -- skipped.")
                continue
            if n_denom_raw == 0:
                print(f"[WARN] {sample}: denominator ('{args.denominator_region}') has 0 events -- "
                      f"efficiency undefined, skipped.")
                continue

            eff_raw = n_num_raw / n_denom_raw
            eff_weighted = n_num_w / n_denom_w if n_denom_w > 0 else float("nan")
            results[mass_x][mass_y] = (eff_raw, eff_weighted)
            print(f"[INFO] {sample}: {args.denominator_region}={n_denom_raw}, "
                  f"{args.numerator_region}={n_num_raw}, "
                  f"raw_eff={eff_raw:.4f}, weighted_eff={eff_weighted:.4f}")

    # --- Line plot: efficiency vs mY, one line per mX ---
    hep.style.use("CMS")
    fig, ax = plt.subplots(figsize=(9, 7))
    for i, mass_x in enumerate(args.mass_x):
        my_vals = sorted(results[mass_x].keys(), key=float)
        if not my_vals:
            continue
        eff_vals = [results[mass_x][my][0] for my in my_vals]  # raw efficiency
        color = PALETTE[i % len(PALETTE)]
        ax.plot([float(y) for y in my_vals], eff_vals, marker="o", color=color,
                linewidth=2, markersize=6, label=f"$m_X$={mass_x} GeV")

    ax.set_xlabel(r"$m_Y$ [GeV]", fontsize=15)
    ax.set_ylabel(f"Efficiency ({args.denominator_region} \u2192 {args.numerator_region})", fontsize=13)
    ax.tick_params(axis="both", labelsize=12)
    ax.legend(loc="best", fontsize=11, frameon=True, framealpha=0.9, edgecolor="0.7")
    try:
        hep.cms.label(ax=ax, text="Preliminary", data=False,
                       lumi=LUMI_FB, com=CM_ENERGY_TEV, fontsize=13)
    except TypeError:
        hep.cms.label(ax=ax, label="Preliminary", data=False,
                       lumi=LUMI_FB, com=CM_ENERGY_TEV, fontsize=13)
    fig.tight_layout()
    fig.savefig(args.out_line, dpi=200, bbox_inches="tight")
    print(f"[Saved] {args.out_line}")
    plt.close(fig)

    # --- Heatmap: mX (rows) vs mY (columns), color = efficiency ---
    all_my = sorted({my for mx in results for my in results[mx]}, key=float)
    all_mx = args.mass_x
    grid = np.full((len(all_mx), len(all_my)), np.nan)
    for i, mx in enumerate(all_mx):
        for j, my in enumerate(all_my):
            if my in results[mx]:
                grid[i, j] = results[mx][my][0]

    # CMS-styled, consistent with the line plot above -- an AN-ready
    # heatmap needs the same mplhep treatment, not a plain matplotlib
    # default (the original version of this plot lacked this).
    fig2, ax2 = plt.subplots(figsize=(max(9, len(all_my) * 0.7), max(5, len(all_mx) * 0.9)))
    im = ax2.imshow(grid, cmap="viridis", aspect="auto", vmin=0,
                     vmax=np.nanmax(grid) if np.any(~np.isnan(grid)) else 1)
    ax2.set_xticks(range(len(all_my)))
    ax2.set_xticklabels(all_my, rotation=45, fontsize=11)
    ax2.set_yticks(range(len(all_mx)))
    ax2.set_yticklabels(all_mx, fontsize=12)
    ax2.set_xlabel(r"$m_Y$ [GeV]", fontsize=15)
    ax2.set_ylabel(r"$m_X$ [GeV]", fontsize=15)
    ax2.tick_params(axis="both", which="both", length=0)  # grid cells don't need tick marks

    for i in range(len(all_mx)):
        for j in range(len(all_my)):
            if not np.isnan(grid[i, j]):
                ax2.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center",
                          fontsize=10, color="white" if grid[i, j] < 0.6 * np.nanmax(grid) else "black")

    cbar = fig2.colorbar(im, ax=ax2, shrink=0.8)
    cbar.set_label(f"Efficiency ({args.denominator_region} \u2192 {args.numerator_region})", fontsize=12)
    cbar.ax.tick_params(labelsize=10)

    try:
        hep.cms.label(ax=ax2, text="Preliminary", data=False,
                       lumi=LUMI_FB, com=CM_ENERGY_TEV, fontsize=13)
    except TypeError:
        hep.cms.label(ax=ax2, label="Preliminary", data=False,
                       lumi=LUMI_FB, com=CM_ENERGY_TEV, fontsize=13)

    fig2.tight_layout()
    fig2.savefig(args.out_heatmap, dpi=200, bbox_inches="tight")
    print(f"[Saved] {args.out_heatmap}")


if __name__ == "__main__":
    main()