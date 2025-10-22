#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plot m_gg in the control region (region==0) per pDNN category.

Usage example:
  python plot_mgg_per_category.py \
    --root outputs/categories_alpha/hhbbgg_analyzer-v2-trees__categorized.root \
    --cats 0 1 2 \
    --mc-overlay --logy

Notes:
- Expects the ROOT file to contain per-sample directories; each has a tree named "selection"
  with branches: diphoton_mass (mgg), cat, region (0=CR,1=SR), isdata, weight_selection (optional).
- If a category has no DATA in CR, the plot will automatically fall back to showing MC (if --mc-overlay).
"""

import os
import argparse
import numpy as np
import uproot
import awkward as ak
import matplotlib.pyplot as plt

# --- branches / names ---
TREE_NAME   = "selection"
BR_MGG      = "diphoton_mass"
BR_CAT      = "cat"
BR_REGION   = "region"        # 0=CR, 1=SR (from categorization script)
BR_ISDATA   = "isdata"
BR_WEIGHT   = "weight_selection"

# --- detect data vs MC by directory name (matches your file structure) ---
def is_data_dir(name: str) -> bool:
    n = name.lower()
    return n.startswith("data") or n.startswith("_data")

def collect_dirs(fin):
    """Return list of top-level directory bases (drop ';1')."""
    dirs = []
    for dkey in fin.keys():
        base = dkey.split(";")[0]
        obj  = fin[dkey]
        if isinstance(obj, uproot.reading.ReadOnlyDirectory):
            dirs.append(base)
    return dirs

def get_tree_key(tdir, base):
    """Find the key for a tree with a given base name (strip ';1')."""
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

def autodetect_categories(fin, max_scan=10):
    """Scan a few directories to collect distinct 'cat' values present in the file."""
    cats = set()
    scanned = 0
    for dkey in fin.keys():
        if scanned >= max_scan:
            break
        tdir = fin[dkey]
        sel_key = get_tree_key(tdir, TREE_NAME)
        if sel_key is None:
            continue
        tree = tdir[sel_key]
        if {BR_CAT}.issubset(set(tree.keys())):
            arr = tree.arrays([BR_CAT], library="ak")
            if BR_CAT in arr.fields:
                vals = np.unique(ak.to_numpy(arr[BR_CAT]))
                for v in vals:
                    if v != -99:  # ignore uncategorized if present
                        cats.add(int(v))
            scanned += 1
    return sorted(cats)

def main():
    ap = argparse.ArgumentParser(description="Plot mgg in CR (region==0) per category")
    ap.add_argument("--root", required=True,
                    help="categorized ROOT (…__categorized.root), or the same file if cat/region were added in-place")
    ap.add_argument("--outdir", default="outputs/mgg_plots")
    ap.add_argument("--cats", type=int, nargs="*", default=None,
                    help="categories to plot (default: auto-detect present cats)")
    ap.add_argument("--bins", type=int, default=60)
    ap.add_argument("--mgg-min", type=float, default=105.0)
    ap.add_argument("--mgg-max", type=float, default=160.0)
    ap.add_argument("--mc-overlay", action="store_true",
                    help="overlay summed MC in CR (weighted)")
    ap.add_argument("--logy", action="store_true")
    ap.add_argument("--sr-sigma", type=float, default=2.0,
                    help="paint reference SR band ±sr_sigma around 125 GeV")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # histogram binning
    edges = np.linspace(args.mgg_min, args.mgg_max, args.bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])

    with uproot.open(args.root) as fin:
        dir_bases = collect_dirs(fin)

        # Auto-detect categories if not provided
        if args.cats is None:
            args.cats = autodetect_categories(fin)
            if not args.cats:
                print("[warn] Could not auto-detect categories; defaulting to [0,1,2].")
                args.cats = [0, 1, 2]
            else:
                print("[info] Auto-detected categories:", args.cats)

        for cat in args.cats:
            # accumulate data-CR in this category
            data_vals = []

            # (optional) accumulate MC-CR (weighted)
            mc_vals = []
            mc_wgts = []

            for dbase in dir_bases:
                tdir = fin[dbase]
                sel_key = get_tree_key(tdir, TREE_NAME)
                if sel_key is None:
                    continue
                tree = tdir[sel_key]

                tfields = set(tree.keys())
                needed = {BR_MGG, BR_CAT, BR_REGION, BR_ISDATA}
                if not needed.issubset(tfields):
                    # skip directories lacking required branches
                    continue

                # read minimal branches (+ weight if we’ll use it)
                branches = [BR_MGG, BR_CAT, BR_REGION, BR_ISDATA]
                use_wgt = args.mc_overlay and (BR_WEIGHT in tfields)
                if use_wgt:
                    branches.append(BR_WEIGHT)

                arr = tree.arrays(branches, library="ak")

                # masks
                isdata = arr[BR_ISDATA]
                in_cr  = (arr[BR_REGION] == 2)
                in_cat = (arr[BR_CAT] == cat)

                # data (unweighted)
                if is_data_dir(dbase):
                    vals = ak.to_numpy(arr[BR_MGG][in_cr & in_cat])
                    if vals.size:
                        data_vals.append(vals)

                # MC (weighted)
                elif args.mc_overlay:
                    vals = ak.to_numpy(arr[BR_MGG][in_cr & in_cat & (isdata == 0)])
                    if vals.size:
                        if use_wgt:
                            w = ak.to_numpy(arr[BR_WEIGHT][in_cr & in_cat & (isdata == 0)])
                        else:
                            w = np.ones_like(vals)
                        mc_vals.append(vals)
                        mc_wgts.append(w)

            # quick counts
            n_data = 0 if not data_vals else sum(len(v) for v in data_vals)
            n_mc   = 0 if not mc_vals else sum(len(v) for v in mc_vals)
            print(f"[cat {cat}] Data CR events={n_data}; MC CR events={n_mc}")

            # make hist(s)
            H_data = None
            if data_vals:
                H_data, _ = np.histogram(np.concatenate(data_vals), bins=edges)

            H_mc = None
            if args.mc_overlay and mc_vals:
                H_mc, _ = np.histogram(np.concatenate(mc_vals), bins=edges,
                                       weights=np.concatenate(mc_wgts))

            # plot
            fig, ax = plt.subplots(figsize=(7.0, 5.0))
            plotted = False

            if H_data is not None:
                ax.errorbar(centers, H_data, yerr=np.sqrt(np.maximum(H_data, 1.0)),
                            fmt="o", ms=4, lw=1, label="Data (CR)", zorder=3)
                plotted = True

            if H_mc is not None:
                ax.step(edges[:-1], H_mc, where="post", lw=2, label="MC (CR, weighted)", zorder=2)
                plotted = True

            if not plotted:
                ax.text(0.5, 0.5, "No CR events in this category",
                        transform=ax.transAxes, ha="center", va="center")

            # cosmetics
            ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
            ax.set_ylabel("Events / bin")
            ax.set_title(f"$m_{{\gamma\gamma}}$ in CR per category — cat={cat}")
            if args.logy:
                ax.set_yscale("log")

            # mark the Higgs mass and SR window (for reference)
            mH = 125.0
            ax.axvline(mH, ls="--", alpha=0.5)
            ax.axvspan(mH - args.sr_sigma, mH + args.sr_sigma,
                       color="grey", alpha=0.15, label=f"SR (±{args.sr_sigma:g} GeV)")

            ax.set_xlim(args.mgg_min, args.mgg_max)
            ax.legend()
            ax.grid(alpha=0.2)

            out_png = os.path.join(args.outdir, f"mgg_CR_cat{cat}.png")
            fig.tight_layout()
            fig.savefig(out_png, dpi=150)
            plt.close(fig)
            print("Wrote", out_png)

if __name__ == "__main__":
    main()
