#!/usr/bin/env python3
"""Quick diagnostic: inspect real SR/CR event counts and pDNN_score
distribution for one background MC sample and one data era, across
multiple candidate regions (selection, srbbgg, srbbggMET), to check
which region categorize_events.py should actually be reading from."""
import sys
import uproot
import numpy as np

REGIONS_TO_CHECK = ["selection", "srbbgg", "srbbggMET"]

def inspect(label, path):
    print(f"=== {label}: {path} ===")
    try:
        f = uproot.open(path)
    except Exception as e:
        print(f"  FAILED to open: {type(e).__name__}: {e}")
        return
    keys = f.keys()
    for region in REGIONS_TO_CHECK:
        sel_keys = [k for k in keys if k.split(";")[0].split("/")[-1] == region]
        if not sel_keys:
            print(f"  [{region}] not found in this file")
            continue
        tree = f[sel_keys[0]]
        fields = set(tree.keys())
        needed = {"pDNN_score", "diphoton_mass"}
        if not needed.issubset(fields):
            print(f"  [{region}] missing required branches")
            continue
        arr = tree.arrays(["pDNN_score", "diphoton_mass"], library="np")
        mgg = arr["diphoton_mass"]
        score = arr["pDNN_score"]
        sr = np.abs(mgg - 125.0) < 2.0
        cr = (np.abs(mgg - 125.0) >= 4.0) & (np.abs(mgg - 125.0) < 10.0)
        print(f"  [{region}] total={len(mgg)}  in SR={sr.sum()}  in CR={cr.sum()}")
        if sr.sum() > 0:
            print(f"    pDNN_score in SR: min={score[sr].min():.4f} max={score[sr].max():.4f} mean={score[sr].mean():.4f}")
        if cr.sum() > 0:
            print(f"    pDNN_score in CR: min={score[cr].min():.4f} max={score[cr].max():.4f} mean={score[cr].mean():.4f}")
    print()

def inspect_signal_saturation(path, nmin=50):
    print(f"=== Signal saturation check: {path} ===")
    try:
        f = uproot.open(path)
    except Exception as e:
        print(f"  FAILED to open: {type(e).__name__}: {e}")
        return
    keys = f.keys()
    for region in REGIONS_TO_CHECK:
        sel_keys = [k for k in keys if k.split(";")[0].split("/")[-1] == region]
        if not sel_keys:
            continue
        tree = f[sel_keys[0]]
        fields = set(tree.keys())
        if not {"pDNN_score", "diphoton_mass"}.issubset(fields):
            continue
        arr = tree.arrays(["pDNN_score", "diphoton_mass"], library="np")
        mgg = arr["diphoton_mass"]
        score = arr["pDNN_score"]
        sr = np.abs(mgg - 125.0) < 2.0
        s_sr = score[sr]
        if len(s_sr) == 0:
            print(f"  [{region}] no SR events")
            continue
        sorted_desc = np.sort(s_sr)[::-1]
        nth_score = sorted_desc[min(nmin, len(sorted_desc)) - 1]
        n_at_ceiling = int((s_sr >= 0.9999).sum())
        print(f"  [{region}] SR events: {len(s_sr)}  score at ceiling (>=0.9999): {n_at_ceiling}")
        print(f"    score of the {nmin}th-highest-ranked event: {nth_score:.6f}  (this predicts the FIRST boundary build_edges() would pick)")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 diagnose_categories.py <bkg_mc_file> <data_file> [signal_file]")
        print("   or: python3 diagnose_categories.py --signal-only <signal_file> [<signal_file> ...]")
        sys.exit(1)
    if sys.argv[1] == "--signal-only":
        for sig_path in sys.argv[2:]:
            inspect_signal_saturation(sig_path)
    else:
        if len(sys.argv) < 3:
            print("Usage: python3 diagnose_categories.py <bkg_mc_file> <data_file> [signal_file]")
            sys.exit(1)
        inspect("Background MC", sys.argv[1])
        inspect("Data", sys.argv[2])
        if len(sys.argv) >= 4:
            inspect_signal_saturation(sys.argv[3])