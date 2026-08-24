#!/usr/bin/env python3
"""
summarize_signal_mc_counts.py

Signal MC event counts (raw and weighted) per category, per mass point,
across the grid. Pure simulation -- no data is ever read, no blinding
concern at all.

Reads event_categories.json for each mass point's category score
boundaries (same convention as fit_resonant_mjj.py / etc. -- handles
both the flat-list and dict-with-"combined" JSON shapes), then reads
that mass point's own signal MC tree and bins events by score using the
SAME score_to_category logic already used elsewhere in this pipeline
(np.searchsorted, matching common.io_utils's score_to_category).

FULL-GRID SUPPORT (this pass): --mass-x now accepts multiple values or
can be omitted entirely to auto-discover every mX present in
--analyzer-root-base, the same way --mass-y already auto-discovers per
mX when omitted. Both levels can be combined freely: an explicit
--mass-x list with auto-discovered --mass-y per point, an explicit
--mass-y list applied across every discovered --mass-x, or full
auto-discovery on both (omit both flags) for the whole grid in one run.

Usage:
    # Single mass point (original usage, unchanged)
    python summarize_signal_mc_counts.py \
        --categories-json /path/to/event_categories.json \
        --analyzer-root-base /path/to/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024 \
        --mass-x 600 \
        [--mass-y 300 350 ...]   # omit to auto-discover every mY for this mX
        [--wgt-branch weight_selection]
        [--score-branch pDNN_score]
        [--out-csv summary.csv]

    # Multiple explicit mX values
    python summarize_signal_mc_counts.py \
        --categories-json /path/to/event_categories.json \
        --analyzer-root-base /path/to/.../DD_2024 \
        --mass-x 600 1000 \
        --out-csv summary_600_1000.csv

    # Whole grid, fully auto-discovered
    python summarize_signal_mc_counts.py \
        --categories-json /path/to/event_categories.json \
        --analyzer-root-base /path/to/.../DD_2024 \
        --out-csv summary_full_grid.csv
"""

import argparse
import csv
import glob
import json
import os
import re

import numpy as np
import uproot


def score_to_category(score, edges):
    """Same convention as common.io_utils.score_to_category, used
    throughout this pipeline's fitting scripts -- kept identical here
    rather than re-derived, so category assignment matches exactly."""
    edges = np.asarray(edges)
    return np.searchsorted(edges, score, side="right") - 1


def load_boundaries(categories_json_path):
    with open(categories_json_path) as f:
        data = json.load(f)
    return data["boundaries"]


def edges_for_tag(boundaries, mass_tag):
    raw = boundaries.get(mass_tag)
    if raw is None:
        return None
    edges = raw["combined"] if isinstance(raw, dict) else raw
    return sorted(edges)


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


def discover_mass_x_values(analyzer_root_base):
    """Same auto-discovery pattern as discover_mass_y_values(), one
    level up: scans for every distinct mX present in the tree filenames,
    rather than requiring it to be specified. This is what makes a
    whole-grid run possible without hand-listing every mX value."""
    pattern = os.path.join(analyzer_root_base, "hhbbgg_analyzer-v2-trees__NMSSM_X*_Y*.root")
    x_values = []
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        m = re.search(r"NMSSM_X(\d+(?:\.\d+)?)_Y", base)
        if m and m.group(1) not in x_values:
            x_values.append(m.group(1))
    return sorted(x_values, key=float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categories-json", required=True)
    ap.add_argument("--analyzer-root-base", required=True,
                     help="Directory containing hhbbgg_analyzer-v2-trees__NMSSM_X*_Y*.root files.")
    ap.add_argument("--mass-x", nargs="*", default=None,
                     help="Specific mX value(s); omit to auto-discover every mX found in "
                          "--analyzer-root-base (whole-grid run).")
    ap.add_argument("--mass-y", nargs="*", default=None,
                     help="Specific mY value(s), applied to every --mass-x being processed; "
                          "omit to auto-discover all mY for each mX independently.")
    ap.add_argument("--tree", default="srbbgg")
    ap.add_argument("--systematic", default="nominal",
                     help="Systematic-variation subdirectory the tree lives under, e.g. "
                          "'nominal' (default). Confirmed live: this pipeline's analyzer "
                          "output nests every region tree under "
                          "'{sample}/{systematic}/{region}', not as a flat top-level tree "
                          "-- e.g. 'NMSSM_X600_Y300/nominal/srbbgg', not 'srbbgg'.")
    ap.add_argument("--score-branch", default="pDNN_score")
    ap.add_argument("--wgt-branch", default="weight_selection")
    ap.add_argument("--low-stat-threshold", type=int, default=10,
                     help="Flag any category with fewer than this many raw MC events (default 10).")
    ap.add_argument("--out-csv", default=None, help="Optional: also write results to this CSV path.")
    args = ap.parse_args()

    boundaries = load_boundaries(args.categories_json)

    mass_x_values = args.mass_x
    if not mass_x_values:
        mass_x_values = discover_mass_x_values(args.analyzer_root_base)
        print(f"[INFO] Auto-discovered {len(mass_x_values)} mX value(s): {mass_x_values}")
    if not mass_x_values:
        print("[ERROR] No mX values found or specified -- nothing to do.")
        return

    csv_rows = []
    low_stat_flags = []
    n_mass_points_processed = 0

    for mass_x in mass_x_values:
        mass_y_values = args.mass_y
        if not mass_y_values:
            mass_y_values = discover_mass_y_values(args.analyzer_root_base, mass_x)
            print(f"[INFO] Auto-discovered {len(mass_y_values)} mY value(s) for mX={mass_x}: {mass_y_values}")

        if not mass_y_values:
            print(f"[WARN] mX={mass_x}: no mY values found or specified -- skipped.")
            continue

        for mass_y in mass_y_values:
            mass_tag = f"mX{mass_x}_mY{mass_y}"
            edges = edges_for_tag(boundaries, mass_tag)
            if edges is None:
                print(f"[WARN] {mass_tag}: not found in {args.categories_json} -- skipped.")
                continue

            tree_path = find_signal_tree_file(args.analyzer_root_base, mass_x, mass_y)
            if tree_path is None:
                print(f"[WARN] {mass_tag}: no signal MC tree file found (checked both naming "
                      f"conventions in {args.analyzer_root_base}) -- skipped.")
                continue

            with uproot.open(tree_path) as f:
                sample = f"NMSSM_X{mass_x}_Y{mass_y}"
                full_tree_path = f"{sample}/{args.systematic}/{args.tree}"
                if full_tree_path not in f:
                    print(f"[WARN] {mass_tag}: tree '{full_tree_path}' not found in {tree_path} -- skipped.")
                    continue
                tree = f[full_tree_path]
                fields = [args.score_branch]
                has_weight = args.wgt_branch in tree.keys()
                if has_weight:
                    fields.append(args.wgt_branch)
                arr = tree.arrays(fields, library="np")

            score = arr[args.score_branch]
            weight = arr[args.wgt_branch] if has_weight else np.ones_like(score)
            if not has_weight:
                print(f"[WARN] {mass_tag}: weight branch '{args.wgt_branch}' not found -- "
                      f"weighted yields below are actually just raw counts (weight=1).")

            finite = np.isfinite(score) & np.isfinite(weight)
            score, weight = score[finite], weight[finite]

            cat_idx = score_to_category(score, edges)
            # n_categories = len(edges), NOT len(edges)-1 -- confirmed
            # directly against categorize_events.py's real, authoritative
            # category-assignment loop (cat[score >= edges[i]] = i for each
            # threshold in ascending order): each edge value is the START
            # of its own category, not a histogram-style bin boundary.
            # len(edges) thresholds => len(edges) distinct valid categories
            # (cat=0 .. cat=len(edges)-1), with events below the LOWEST
            # edge excluded entirely, never folded into a category. The
            # old "-1" here silently dropped the TOP category from every
            # multi-edge mass point, and produced zero categories (100%
            # of events reported "excluded") for every single-edge one --
            # confirmed as the full explanation for a real run showing
            # many mass points with genuine 9,000-17,000 MC events all
            # falling "outside every boundary."
            n_cats = len(edges)

            print(f"\n{mass_tag}  ({n_cats} categories, {len(score)} total finite MC event(s))")
            for c in range(n_cats):
                m = cat_idx == c
                n_raw = int(np.sum(m))
                yield_weighted = float(np.sum(weight[m]))
                flag = ""
                if n_raw < args.low_stat_threshold:
                    flag = f"  <-- LOW MC STATS (< {args.low_stat_threshold})"
                    low_stat_flags.append((mass_tag, c, n_raw))
                print(f"    cat{c}: raw={n_raw:5d}   weighted_yield={yield_weighted:10.4f}{flag}")
                csv_rows.append({
                    "mass_x": mass_x, "mass_y": mass_y, "mass_tag": mass_tag,
                    "category": c, "n_categories_total": n_cats,
                    "raw_mc_events": n_raw, "weighted_yield": yield_weighted,
                })

            n_uncategorized = int(np.sum(cat_idx < 0)) + int(np.sum(cat_idx >= n_cats))
            if n_uncategorized:
                print(f"    [note] {n_uncategorized} event(s) fell outside all category "
                      f"boundaries (score below the first edge or above the last) -- excluded above.")

            n_mass_points_processed += 1

    print(f"\n[SUMMARY] Processed {n_mass_points_processed} mass point(s) across "
          f"{len(mass_x_values)} mX value(s): {mass_x_values}")

    if low_stat_flags:
        print(f"[SUMMARY] {len(low_stat_flags)} (mass point, category) pair(s) below "
              f"{args.low_stat_threshold} raw MC events:")
        for mass_tag, c, n_raw in low_stat_flags:
            print(f"    {mass_tag} cat{c}: {n_raw} raw MC event(s)")
    else:
        print(f"[SUMMARY] No category fell below {args.low_stat_threshold} raw MC events.")

    if args.out_csv and csv_rows:
        with open(args.out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\n[Saved] {args.out_csv}")


if __name__ == "__main__":
    main()