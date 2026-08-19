#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_weight_rate_systematics.py

Computes region-wide (srbbgg) rate systematics for the weight-based
systematic family (Pileup, TriggerSF, PreselSF, ElectronVetoSF, and the
8-way b-tag SF components) directly from the analyzer's histogram
output.

WHY REGION-WIDE, NOT PER-CATEGORY: the weight-systematic Up/Down columns
never made it into the analyzer's TREE output (confirmed directly --
only the HISTOGRAM output has them, since cms_events, not out_events,
carries those columns internally, and only cms_events feeds histogram
filling). Getting genuine per-category ratios would require a targeted
analyzer re-run with that gap fixed. Decided instead, for now, to use a
single region-wide ratio applied uniformly across every category for a
given mass point -- standard practice for this class of systematic,
since weight-type variations (pileup reweighting, SF corrections) are
generally not correlated with the pDNN score the way object-level
(JEC/JER/Scale/Smearing) systematics are.

Usage:
    python compute_weight_rate_systematics.py \\
      --hist-file outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-histograms.root \\
      --sample NMSSM_X600_Y300 \\
      --region srbbgg \\
      --variable diphoton_mass
"""

import argparse
import glob
import sys

import uproot
import numpy as np

WEIGHT_SYSTEMATICS = [
    "Pileup",
    "TriggerSF",
    "PreselSF",
    "ElectronVetoSF",
    "bTagSF_hf",
    "bTagSF_lf",
    "bTagSF_cferr1",
    "bTagSF_cferr2",
    "bTagSF_hfstats1",
    "bTagSF_hfstats2",
    "bTagSF_lfstats1",
    "bTagSF_lfstats2",
    "bTagSF_jes",
]


def find_hist(f, sample, systematic, region, variable):
    """Locate a histogram key matching sample/systematic/region/variable,
    tolerant of the exact key-naming/cycle-number conventions uproot
    uses. Returns None if not found (never raises -- caller decides how
    to handle a missing variant)."""
    target_path = f"{sample}/{systematic}/{region}/{variable}"
    for k in f.keys():
        base = k.split(";")[0]
        if base == target_path:
            return f[k]
    return None


def integral(hist_obj):
    """Sum of bin contents (including under/overflow, since we want the
    genuine total weighted yield, not just what happens to land in the
    visible binning range)."""
    values, _ = hist_obj.to_numpy(flow=True)
    return float(np.sum(values))


def main():
    ap = argparse.ArgumentParser(
        description="Compute region-wide weight-based rate systematics from histogram output."
    )
    ap.add_argument("--hist-file", required=True,
                     help="Path to the histogram ROOT file (single file, or a glob "
                          "pattern in quotes to search multiple per-run files).")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--region", default="srbbgg")
    ap.add_argument("--variable", default="diphoton_mass",
                     help="Any histogrammed variable works for a yield ratio -- "
                          "this just needs to be one that was actually filled.")
    ap.add_argument("--out-json", default=None,
                     help="Optional: write the computed ratios to a JSON file.")
    args = ap.parse_args()

    hist_files = sorted(glob.glob(args.hist_file))
    if not hist_files:
        print(f"[ERROR] No files matched: {args.hist_file}")
        sys.exit(1)

    nominal_integral = None
    variant_integrals = {}  # syst_name -> {"Up": val, "Down": val}
    source_file = {}

    for path in hist_files:
        try:
            f = uproot.open(path)
        except Exception as e:
            print(f"[WARN] Could not open {path}: {type(e).__name__}: {e}")
            continue

        h_nom = find_hist(f, args.sample, "nominal", args.region, args.variable)
        if h_nom is not None:
            v = integral(h_nom)
            if nominal_integral is None:
                nominal_integral = v
                source_file["nominal"] = path
            elif abs(v - nominal_integral) > 1e-6:
                print(f"[WARN] nominal integral differs between {source_file['nominal']} "
                      f"({nominal_integral}) and {path} ({v}) -- using the first one found; "
                      f"if these genuinely differ, the histogram files may not be a clean "
                      f"disjoint split (same sample appearing in more than one run's output).")

        for syst_name in WEIGHT_SYSTEMATICS:
            for direction in ("Up", "Down"):
                h = find_hist(f, args.sample, f"{syst_name}{direction}", args.region, args.variable)
                if h is not None:
                    v = integral(h)
                    variant_integrals.setdefault(syst_name, {})[direction] = v
                    source_file[f"{syst_name}{direction}"] = path

    if nominal_integral is None:
        print(f"[ERROR] Could not find a nominal histogram for "
              f"{args.sample}/nominal/{args.region}/{args.variable} in any of "
              f"{len(hist_files)} file(s) searched. Confirm --sample/--region/--variable "
              f"are correct, and that this sample was actually processed with "
              f"--all-systematics.")
        sys.exit(1)

    if nominal_integral <= 0:
        print(f"[ERROR] Nominal integral is {nominal_integral} (<=0) -- cannot compute "
              f"meaningful ratios from this.")
        sys.exit(1)

    print(f"[INFO] Nominal integral ({args.sample}/{args.region}/{args.variable}): "
          f"{nominal_integral:.6f}  (from {source_file['nominal']})")
    print()

    results = {}
    for syst_name in WEIGHT_SYSTEMATICS:
        variants = variant_integrals.get(syst_name, {})
        if "Up" not in variants or "Down" not in variants:
            missing = [d for d in ("Up", "Down") if d not in variants]
            print(f"[WARN] {syst_name}: missing {missing} variant(s) -- skipped. "
                  f"(Was --all-systematics used, and did this sample's schema have "
                  f"this systematic's weight columns?)")
            continue
        ratio_up = variants["Up"] / nominal_integral
        ratio_down = variants["Down"] / nominal_integral
        results[syst_name] = {"kappa_up": ratio_up, "kappa_down": ratio_down}
        # Combine lnN asymmetric syntax is "kappaDown/kappaUp"
        print(f"  {syst_name:20s}  lnN   {ratio_down:.4f}/{ratio_up:.4f}")

    if not results:
        print("[WARN] No weight systematics were successfully computed. Nothing to write.")
        sys.exit(0)

    if args.out_json:
        import json
        with open(args.out_json, "w") as fh:
            json.dump({
                "sample": args.sample,
                "region": args.region,
                "variable": args.variable,
                "nominal_integral": nominal_integral,
                "systematics": results,
            }, fh, indent=2)
        print(f"\n[OK] Wrote {args.out_json}")


if __name__ == "__main__":
    main()
    
    
    
    