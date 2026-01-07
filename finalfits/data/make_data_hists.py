#!/usr/bin/env python3
import os, argparse
import awkward as ak
import uproot
import numpy as np

def find_data_topdir(f):
    keys = [k for k in f.keys()]
    bases = [k.split(";")[0] for k in keys]
    for i,b in enumerate(bases):
        low = b.lower()
        if low.startswith("_data") or low.startswith("data") or low.startswith("_dat"):
            return keys[i]
    for i,b in enumerate(bases):
        if "data" in b.lower():
            return keys[i]
    return None

def open_tree_from_tdir(file_obj, topdir_key, sel_key, tdir_obj):
    if "/" in sel_key:
        parts = sel_key.split("/")
        obj = tdir_obj
        try:
            for p in parts:
                obj = obj[p]
            return obj
        except Exception:
            pass
    try:
        return tdir_obj[sel_key]
    except Exception:
        pass
    sel_base = sel_key.split(";")[0].lower()
    for k in tdir_obj.keys():
        if k.split(";")[0].lower() == sel_base:
            return tdir_obj[k]
    for k in file_obj.keys():
        if k.split(";")[0].lower() == topdir_key.split(";")[0].lower():
            try:
                candidate_tdir = file_obj[k]
                for ck in candidate_tdir.keys():
                    if ck.split(";")[0].lower() == sel_base:
                        return candidate_tdir[ck]
            except Exception:
                continue
    return None

def main():
    ap = argparse.ArgumentParser(description="Produce per-category 2D data counts (.npz) using uproot+awkward (no ROOT).")
    ap.add_argument("--root", required=True)
    ap.add_argument("--outdir", default="data_npz")
    ap.add_argument("--edges", type=float, nargs="*", default=[0.8002240580158556, 0.8574103025311034])
    ap.add_argument("--mgg-lo", type=float, default=115.0)
    ap.add_argument("--mgg-hi", type=float, default=135.0)
    ap.add_argument("--mgg-bins", type=int, default=56)
    ap.add_argument("--mjj-lo", type=float, default=60.0)
    ap.add_argument("--mjj-hi", type=float, default=200.0)
    ap.add_argument("--mjj-bins", type=int, default=140)
    ap.add_argument("--cats", type=int, nargs="*", default=[0,1,2])
    ap.add_argument("--mgg-branch", default="diphoton_mass")
    ap.add_argument("--mjj-branch", default="dibjet_mass")
    ap.add_argument("--score-branch", default="pDNN_score")
    ap.add_argument("--isdata-branch", default="isdata")
    ap.add_argument("--tree", default="Events")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print("Opening:", args.root)
    f = uproot.open(args.root)

    topkey = find_data_topdir(f)
    if topkey is None:
        raise RuntimeError("No data directory found in the ROOT file. Top-level keys: " +
                           ", ".join([k.split(';')[0] for k in f.keys()][:50]))
    print("Using data directory:", topkey)
    tdir = f[topkey]

    # find selection tree
    sel_key = None
    for k in tdir.keys():
        if k.split(";")[0].lower() == "selection":
            sel_key = k; break
    if sel_key is None:
        for k in tdir.keys():
            try:
                sub = tdir[k]
                for sk in sub.keys():
                    if sk.split(";")[0].lower() == "selection":
                        sel_key = f"{k}/{sk}"; break
                if sel_key: break
            except Exception:
                continue
    if sel_key is None:
        raise RuntimeError("Could not find a 'selection' tree under data dir " + topkey)
    print("Found selection tree:", sel_key)

    tree = open_tree_from_tdir(f, topkey, sel_key, tdir)
    if tree is None:
        raise RuntimeError("Could not open selection tree")

    available = set(tree.keys())
    mgg_b = args.mgg_branch if args.mgg_branch in available else (args.mgg_branch.lower() if args.mgg_branch.lower() in available else None)
    mjj_b = args.mjj_branch if args.mjj_branch in available else (args.mjj_branch.lower() if args.mjj_branch.lower() in available else None)
    score_b = args.score_branch if args.score_branch in available else (args.score_branch.lower() if args.score_branch.lower() in available else None)

    if mgg_b is None or mjj_b is None or score_b is None:
        print("Available branch names (first 50):", list(available)[:50])
        missing = [b for b,n in [("mgg", mgg_b), ("mjj", mjj_b), ("score", score_b)] if n is None]
        raise RuntimeError("Missing required branches: " + ", ".join(missing))

    isdata_b = args.isdata_branch if args.isdata_branch in available else None
    if isdata_b is None:
        print("[info] 'isdata' branch not found; assuming all events are data.")
    else:
        print(f"[info] 'isdata' branch found as '{isdata_b}'")

    need = [mgg_b, mjj_b, score_b] + ([isdata_b] if isdata_b else [])
    print("Reading branches:", need)
    arr = tree.arrays(need, library="ak")

    isdata = arr[isdata_b] if isdata_b and isdata_b in arr.fields else ak.ones_like(arr[mgg_b])
    mask_data = (isdata == 1)
    mgg = ak.to_numpy(arr[mgg_b][mask_data])
    mjj = ak.to_numpy(arr[mjj_b][mask_data])
    score = ak.to_numpy(arr[score_b][mask_data])

    edges = sorted(args.edges)
    edges_full = [-1e9] + edges + [1e9]

    # bin edges for 2D hist
    xedges = np.linspace(args.mgg_lo, args.mgg_hi, args.mgg_bins+1)
    yedges = np.linspace(args.mjj_lo, args.mjj_hi, args.mjj_bins+1)

    print(f"Filling 2D histograms for cats {args.cats}, mgg [{args.mgg_lo},{args.mgg_hi}], mjj [{args.mjj_lo},{args.mjj_hi}]")
    for c in args.cats:
        if c < 0 or c >= len(edges_full)-1:
            print(f"[warn] requested cat {c} out of range for edges {edges}. skipping.")
            continue
        lo, hi = edges_full[c], edges_full[c+1]
        selmask = (score >= lo) & (score < hi)
        # no mjj window here — for 2D we usually want full mjj range; if you want a narrow mgg window apply it later
        sel_mgg = mgg[selmask]
        sel_mjj = mjj[selmask]
        counts, xedges_out, yedges_out = np.histogram2d(sel_mgg, sel_mjj, bins=[xedges, yedges])
        outname = os.path.join(args.outdir, f"hist_data_ch{c}.npz")
        np.savez_compressed(outname, counts=counts.astype(int), xedges=xedges_out, yedges=yedges_out, cat=c)
        print("Wrote", outname, "entries:", int(counts.sum()))

    print("Done. Now run the PyROOT converter to write TH2D from these .npz files.")

if __name__ == "__main__":
    main()
