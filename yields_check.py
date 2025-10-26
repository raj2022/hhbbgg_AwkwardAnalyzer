#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
from pathlib import Path
import math
import glob
import uproot
import numpy as np
import csv
import re
from collections import defaultdict

# -----------------------------
#  Sample → Physics categories
# -----------------------------
# Edit these patterns to match your exact sample names (case-insensitive).
CATEGORY_MAP = [
    ("γ+jets",     [r"^GJet", r"^QCD", r".*QCDPt", r".*GJetPt"]),
    ("γγ+jets",    [r"^GGJets", r".*GGJets"]),
    ("tt+X",       [r"^TT", r"^TTGG", r".*tt.*(GG|toGG)", r".*TT.*"]),
    ("DY",         [r"^DY.*"]),
    ("Vγ",         [r"^(W|Z)G.*", r".*VGamma.*"]),
    ("VV",         [r"^(WW|WZ|ZZ).*", r".*VV.*"]),
    ("Single H",   [r".*HToGG", r".*toGG", r"^GluGluHToGG$", r"^VBFHToGG$", r"^VHToGG$", r"^ttHToGG$"]),
    ("HH → bbγγ",  [r"^GluGluToHH$"]),                   # keep HH under SM backgrounds as in your table
    ("Signals",    [r"^NMSSM_.*", r"^XToHH.*", r"^Radion.*", r"^Graviton.*"]),
    ("Data",       [r"^Data", r"^_Data", r".*Era[A-Z].*"]),
]

# Order used when printing tables
CATEGORY_PRINT_ORDER = [
    "γ+jets","γγ+jets","tt+X","DY","Vγ","VV","Single H","HH → bbγγ","Total SM","Data","Signals"
]

def categorize(sample_name: str) -> str | None:
    for cat, pats in CATEGORY_MAP:
        for pat in pats:
            if re.search(pat, sample_name, flags=re.IGNORECASE):
                return cat
    return None  # unclassified → goes to "Other" if you want

# -----------------------------
#  File discovery
# -----------------------------
def find_root_files(root_input):
    p = Path(root_input)
    if p.is_file():
        return [str(p)]
    if p.is_dir():
        patterns = [
            "**/hhbbgg_analyzer-v2-trees.root",
            "**/*.root",
        ]
        files = []
        for pat in patterns:
            files.extend([str(x) for x in p.glob(pat)])
        files = sorted(set(files), key=lambda x: (0 if x.endswith("hhbbgg_analyzer-v2-trees.root") else 1, x))
        return files
    return sorted(glob.glob(root_input))

# -----------------------------
#  Category aggregation
# -----------------------------
def aggregate_categories(sample_rows, wanted_region: str):
    """
    sample_rows: list of [sample, region, yield, stat_err, n]
    returns: dict category -> (yield, err), plus 'Total SM'
    """
    sums = defaultdict(lambda: {"sumw":0.0, "sumw2":0.0})

    for sample, region, y, e, n in sample_rows:
        if region != wanted_region:
            continue
        cat = categorize(sample)
        if cat is None:
            cat = "Other"
        sums[cat]["sumw"]  += float(y)
        # Add errors in quadrature across *independent* samples
        sums[cat]["sumw2"] += float(e)**2

    # Convert to simple (y, e)
    out = {cat: (rec["sumw"], math.sqrt(rec["sumw2"])) for cat, rec in sums.items()}

    # Total SM excludes Data and BSM "Signals"
    sm_cats = ["γ+jets","γγ+jets","tt+X","DY","Vγ","VV","Single H","HH → bbγγ","Other"]
    total_sm_y  = sum(out.get(c, (0.0,0.0))[0] for c in sm_cats)
    total_sm_e2 = sum(out.get(c, (0.0,0.0))[1]**2 for c in sm_cats)
    out["Total SM"] = (total_sm_y, math.sqrt(total_sm_e2))

    return out

# -----------------------------
#  Formatting helpers
# -----------------------------
def fmt_pm_sci(y, e, sigfigs=2):
    """Format like (A ± B) × 10^N; falls back to plain if small."""
    if y == 0.0:
        return f"{y:.2f} ± {e:.2f}"
    exp = int(np.floor(np.log10(abs(y))))
    # Prefer no scientific notation for |exp| < 3 for readability
    if -2 <= exp <= 2:
        # choose decimals from magnitude
        dec = max(0, 2 - int(np.floor(np.log10(abs(y)))) )
        return f"{y:.{max(dec,2)}f} ± {e:.{max(dec,2)}f}"
    scale = 10.0**exp
    y_s = y/scale
    e_s = e/scale
    fmt = f"({y_s:.{sigfigs}f} ± {e_s:.{sigfigs}f}) × 10^{exp}"
    return fmt

# -----------------------------
#  Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Read yields from existing ROOT trees (no reprocessing).")
    ap.add_argument("-i","--input", required=True,
                    help="ROOT file, directory, or glob (e.g. outputfiles/*.root)")
    ap.add_argument("--region", default="preselection",
                    help="Region tree to read (default: preselection)")
    ap.add_argument("--outdir", default="yields",
                    help="Folder to save CSVs (default: yields)")
    ap.add_argument("--csv", default=None,
                    help='Per-sample CSV filename (default: yields_<region>.csv inside --outdir)')
    ap.add_argument("--categories-csv", default=None,
                    help='Per-category CSV filename (default: yields_categories_<region>.csv in --outdir)')
    ap.add_argument("--strict", action="store_true",
                    help="Error if a file has no <sample>/<region> trees (otherwise skip with a warning).")
    ap.add_argument("--print-table", action="store_true",
                    help="Print a pretty table like the analysis note.")
    args = ap.parse_args()

    files = find_root_files(args.input)
    if not files:
        raise FileNotFoundError(f"No ROOT files found from: {args.input}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_csv_samples = Path(args.csv) if args.csv else (outdir / f"yields_{args.region}.csv")
    out_csv_cats    = Path(args.categories_csv) if args.categories_csv else (outdir / f"yields_categories_{args.region}.csv")

    # -------- Per-sample accumulation --------
    totals = {}  # sample -> dict(sumw, sumw2, n, src)
    def add(sample, sumw, sumw2, n, src_file):
        acc = totals.setdefault(sample, {"sumw":0.0, "sumw2":0.0, "n":0, "src":src_file})
        acc["sumw"]  += float(sumw)
        acc["sumw2"] += float(sumw2)
        acc["n"]     += int(n)

    region = args.region
    wbranch = f"weight_{region}"

    for fpath in files:
        try:
            f = uproot.open(fpath)
        except Exception as e:
            print(f"[WARN] Could not open ROOT file: {fpath} ({e})")
            continue

        classmap = f.classnames()
        region_paths = [k for k, cls in classmap.items() if cls == "TTree" and k.split(";")[0].endswith(f"/{region}")]
        if not region_paths:
            msg = f"[{'ERR' if args.strict else 'WARN'}] No */{region} trees in {fpath}"
            print(msg)
            if args.strict:
                raise RuntimeError(msg)
            continue

        for tkey in region_paths:
            treename = tkey.split(";")[0]
            sample = treename.split("/")[0]
            tree = f[treename]

            branches = set(tree.keys())
            if wbranch not in branches:
                print(f"[WARN] {treename}: '{wbranch}' not found — assuming unit weights.")
                nent = tree.num_entries
                add(sample, sumw=nent, sumw2=nent, n=nent, src_file=fpath)
                continue

            arrs = tree.arrays([wbranch], library="np")
            w = np.asarray(arrs[wbranch], dtype="f8")
            w = np.where(np.isfinite(w), w, 0.0)

            sumw  = float(w.sum())
            sumw2 = float((w*w).sum())
            n     = int(w.size)
            add(sample, sumw, sumw2, n, fpath)

    # -------- Write per-sample CSV --------
    rows = []
    for sample, rec in sorted(totals.items()):
        y  = rec["sumw"]
        e  = math.sqrt(rec["sumw2"]) if rec["sumw2"] >= 0.0 else 0.0
        n  = rec["n"]
        rows.append([sample, region, y, e, n])

    with open(out_csv_samples, "w", newline="") as fp:
        wcsv = csv.writer(fp)
        wcsv.writerow(["sample", "region", "yield", "stat_err", "n_events"])
        wcsv.writerows(rows)
    print(f"[OK] Wrote per-sample yields to: {out_csv_samples}")

    # -------- Aggregate to categories --------
    cat = aggregate_categories(rows, region)

    # Write per-category CSV
    with open(out_csv_cats, "w", newline="") as fp:
        wcsv = csv.writer(fp)
        wcsv.writerow(["category", "region", "yield", "stat_err"])
        # Keep a nice deterministic order in the CSV too
        cats_in_csv = sorted(cat.keys(), key=lambda c: (CATEGORY_PRINT_ORDER.index(c) if c in CATEGORY_PRINT_ORDER else 999, c))
        for c in cats_in_csv:
            y, e = cat[c]
            wcsv.writerow([c, region, y, e])
    print(f"[OK] Wrote per-category yields to: {out_csv_cats}")

    # -------- Optional pretty table printout --------
    if args.print_table:
        print("\nTable: Yields after {}:\n".format(region))
        for c in CATEGORY_PRINT_ORDER:
            if c in cat:
                y, e = cat[c]
                print(f"{c:<15}  {fmt_pm_sci(y, e)}")
        # Also show any uncategorized leftovers
        leftovers = sorted(set(cat.keys()) - set(CATEGORY_PRINT_ORDER))
        for c in leftovers:
            y, e = cat[c]
            print(f"{c:<15}  {fmt_pm_sci(y, e)}")

    print(f"[INFO] Samples found: {len(rows)}   (from {len(files)} ROOT file(s))")

if __name__ == "__main__":
    main()






# To run 
# - Per-sample CSV only (original behavior):
# python yields_check.py -i outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root --region preselection
# With categories and pretty table:
#  python yields_check.py -i outputfiles/merged/DD_CombinedAll/ --region preselection --print-table