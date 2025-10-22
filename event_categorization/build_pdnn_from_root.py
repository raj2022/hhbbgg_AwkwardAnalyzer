#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
from math import sqrt, log

# ---------- user knobs / defaults ----------
SR_DEFAULT = 2.0               # |mgg-125| < SR_DEFAULT (GeV)
CR_DEFAULT = (4.0, 10.0)       # sidebands: |mgg-125| in [lo,hi)
TREE_NAME  = "selection"       # tree name to read per directory
BR_SCORE   = "pDNN_score"
BR_MGG     = "diphoton_mass"
BR_WGT     = "weight_selection"
BR_ISDATA  = "isdata"
# BR_SIGNAL   = "signal"       # not required here; using dir name to separate S/B

# ---------- helpers ----------
def is_data_dir(name: str) -> bool:
    n = name.lower()
    return n.startswith("data") or n.startswith("_data")

def is_signal_dir(name: str) -> bool:
    n = name.lower()
    # adapt if your signal dirs follow a different pattern
    return any(k in n for k in ["nmssm", "gluglutohh", "radion", "graviton", "x"])

def mass_tag_from_dir(name: str) -> str:
    """Derive a mass tag from directory name, e.g. NMSSM_X500_Y150 -> mX500_mY150."""
    n = name.lower()
    m = re.search(r"x(\d+)_y(\d+)", n)  # NMSSM_X500_Y150
    if m:
        return f"mX{m.group(1)}_mY{m.group(2)}"
    m2 = re.search(r"m(\d+)", n)
    return f"m{m2.group(1)}" if m2 else "combined"

def asimov_Z(s, b, sigma_b=0.0):
    if b <= 0:
        return 0.0
    if sigma_b <= 0:
        return sqrt(max(0.0, 2 * ((s + b) * log(1.0 + s / b) - s)))
    # profiled with fractional background uncertainty sigma_b
    sb2 = (sigma_b * b) ** 2
    term1 = (s + b) * log((s + b) * (b + sb2) / (b * b + (s + b) * sb2))
    term2 = (b * b / sb2) * log(1.0 + (sb2 * s) / (b * (b + sb2)))
    return sqrt(max(0.0, 2 * (term1 - term2)))

def objective(Ss, Bs, sigma_b):
    # smaller is better; using -sum(Z_A^2) for the set of bins
    return -sum(asimov_Z(s, b, sigma_b) ** 2 for s, b in zip(Ss, Bs))

def build_edges(scores, s_w, b_w, nmin, min_gain, max_bins, sigma_b):
    """Greedy bin building from high score: add a bin of size nmin if it improves the objective by >= min_gain.
       If not, double nmin and try again. Return ascending list of lower edges."""
    order = ak.argsort(scores, ascending=False)
    s = ak.to_numpy(scores[order])
    sw = ak.to_numpy(s_w[order])
    bw = ak.to_numpy(b_w[order])

    N = len(s)
    edges = []
    idx = 0

    base_S = [sw.sum()]
    base_B = [bw.sum()]
    best = objective(base_S, base_B, sigma_b)

    while (N - idx) >= nmin and len(edges) < max_bins:
        nxt = min(N, idx + nmin)
        S_new = sw[idx:nxt].sum()
        B_new = bw[idx:nxt].sum()

        cand_S = base_S + [S_new]
        cand_B = base_B + [B_new]
        cand = objective(cand_S, cand_B, sigma_b)
        gain = (best - cand) / abs(best) if best != 0 else 1.0

        if gain >= min_gain:
            # accept bin; lower edge is the score of the last event in the slice
            edges.append(float(s[nxt - 1]))
            base_S.append(S_new)
            base_B.append(B_new)
            best = cand
            idx = nxt
        else:
            nmin *= 2
            if nmin > (N - idx):
                break

    return sorted(edges)

def collect_dirs(fin):
    """Return list of directory base keys (without ;1)."""
    dirs = []
    for dkey in fin.keys():
        dbase = dkey.split(";")[0]
        obj = fin[dkey]
        if isinstance(obj, uproot.reading.ReadOnlyDirectory):
            if dbase not in dirs:
                dirs.append(dbase)
    return dirs


def concat1(lst):
    """Concatenate a list of Awkward 1-D arrays into a 1-D NumPy array."""
    if not lst:
        return np.array([], dtype=float)
    if len(lst) == 1:
        return ak.to_numpy(lst[0])
    return ak.to_numpy(ak.concatenate(lst, axis=0))


def get_tree_key(tdir, wanted):
    """Find a tree key in a directory matching wanted base name (strip ;1)."""
    for tkey in tdir.keys():
        if tkey.split(";")[0] == wanted:
            return tkey
    return None

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Optimize pDNN SR bins from merged ROOT (selection trees)")
    ap.add_argument("--root", required=True, help="path to hhbbgg_analyzer-v2-trees.root")
    ap.add_argument("--sr-sigma", type=float, default=SR_DEFAULT, help="SR: |mgg-125| < SR_SIGMA (GeV)")
    ap.add_argument("--cr-sidebands", type=float, nargs=2, default=list(CR_DEFAULT),
                    help="CR: |mgg-125| in [LO, HI) GeV")
    ap.add_argument("--nmin", type=int, default=20, help="minimum events per candidate SR bin")
    ap.add_argument("--min-gain", type=float, default=0.05, help="minimum relative improvement per added bin")
    ap.add_argument("--max-bins", type=int, default=10, help="max number of SR bins to create")
    ap.add_argument("--sigma-b", type=float, default=0.0, help="fractional background uncertainty in Asimov Z")
    ap.add_argument("--outdir", default="outputs/categories")
    ap.add_argument("--per-mass", action="store_true", help="derive edges per mass tag from directory names")
    ap.add_argument("--write-categorized", action="store_true",
                    help="write cat/region back to a copy of the ROOT file")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # SR / CR windows
    sr_lo = 125.0 - args.sr_sigma
    sr_hi = 125.0 + args.sr_sigma
    cr_lo, cr_hi = args.cr_sidebands

    # ---- read & collect MC S/B arrays in SR window ----
    with uproot.open(args.root) as fin:
        dir_bases = collect_dirs(fin)

        buckets = {}  # tag -> dict with S/B scores and weights
        def ensure(tag):
            if tag not in buckets:
                buckets[tag] = dict(S_scores=[], S_w=[], B_scores=[], B_w=[])
            return buckets[tag]

        for dbase in dir_bases:
            tdir = fin[dbase]
            sel_key = get_tree_key(tdir, TREE_NAME)
            if sel_key is None:
                continue

            # read only required branches (skip if missing any)
            tree = tdir[sel_key]
            tfields = set(tree.keys())
            needed = {BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA}
            if not needed.issubset(tfields):
                # quietly skip files lacking any needed branch
                continue

            arr = tree.arrays([BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA], library="ak")

            mgg   = arr[BR_MGG]
            score = arr[BR_SCORE]
            wgt   = arr[BR_WGT]
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(mgg)
            mc = (isdata == 0)

            in_sr = (mgg >= sr_lo) & (mgg <= sr_hi)

            # per-mass or combined tag
            tag = "combined"
            if args.per_mass and is_signal_dir(dbase):
                tag = mass_tag_from_dir(dbase)

            dest = ensure(tag)
            if is_data_dir(dbase):
                # data not used in optimization
                continue
            elif is_signal_dir(dbase):
                dest["S_scores"].append(score[mc & in_sr])
                dest["S_w"].append(wgt[mc & in_sr])
            else:
                dest["B_scores"].append(score[mc & in_sr])
                dest["B_w"].append(wgt[mc & in_sr])

    # ---- build edges per tag ----
    results = {}
    for tag, d in buckets.items():
        if not d["S_scores"] or not d["B_scores"]:
            continue
        # Sscore = ak.to_numpy(ak.flatten(ak.concatenate(d["S_scores"]))) if len(d["S_scores"]) > 1 else ak.to_numpy(d["S_scores"][0])
        # Sw     = ak.to_numpy(ak.flatten(ak.concatenate(d["S_w"])))      if len(d["S_w"])      > 1 else ak.to_numpy(d["S_w"][0])
        # Bscore = ak.to_numpy(ak.flatten(ak.concatenate(d["B_scores"]))) if len(d["B_scores"]) > 1 else ak.to_numpy(d["B_scores"][0])
        # Bw     = ak.to_numpy(ak.flatten(ak.concatenate(d["B_w"])))      if len(d["B_w"])      > 1 else ak.to_numpy(d["B_w"][0])
        Sscore = concat1(d["S_scores"])
        Sw     = concat1(d["S_w"])
        Bscore = concat1(d["B_scores"])
        Bw     = concat1(d["B_w"])

        edges = build_edges(
            scores=np.concatenate([Sscore, Bscore]),
            s_w=np.concatenate([Sw, np.zeros_like(Bw)]),
            b_w=np.concatenate([np.zeros_like(Sw), Bw]),
            nmin=args.nmin,
            min_gain=args.min_gain,
            max_bins=args.max_bins,
            sigma_b=args.sigma_b
        )
        results[tag] = edges
        print(f"[edges] {tag}: {edges}")

    # ---- write JSON ----
    out_json = os.path.join(args.outdir, "event_categories.json")
    payload = {
        "boundaries": results,
        "sr_mgg_window_GeV": args.sr_sigma,
        "cr_mgg_sidebands_GeV": [cr_lo, cr_hi],
    }
    with open(out_json, "w") as fjson:
        json.dump(payload, fjson, indent=2)
    print(f"Wrote {out_json}")

    # ---- optional: write categorized ROOT copy ----
    # if args.write_categorized:
    #     out_root = os.path.join(
    #         args.outdir,
    #         os.path.basename(args.root).replace(".root", "__categorized.root")
    #     )
    #     with uproot.open(args.root) as fin, uproot.recreate(out_root) as fout:
    #         # mirror directory structure
    #         dir_bases = collect_dirs(fin)
    #         for dbase in dir_bases:
    #             fout.mkdir(dbase)

    #         for dkey in fin.keys():
    #             dbase = dkey.split(";")[0]
    #             tdir = fin[dkey]

    #             for tkey in tdir.keys():
    #                 tbase = tkey.split(";")[0]
    #                 tree = tdir[tkey]

    #                 # copy non-selection trees verbatim
    #                 if tbase != TREE_NAME or BR_SCORE not in tree.keys() or BR_MGG not in tree.keys():
    #                     fout[f"{dbase}/{tbase}"] = tree.arrays(library="np")
    #                     continue

    #                 # selection: add cat/region
    #                 arr = tree.arrays(library="ak")
    #                 score = ak.to_numpy(arr[BR_SCORE])
    #                 mgg   = ak.to_numpy(arr[BR_MGG])

    #                 sr_mask = np.abs(mgg - 125.0) < args.sr_sigma
    #                 lo, hi = args.cr_sidebands
    #                 cr_mask = (np.abs(mgg - 125.0) >= lo) & (np.abs(mgg - 125.0) < hi)

    #                 # choose edges (per-mass for signal dirs if requested)
    #                 tag = "combined"
    #                 if args.per_mass and is_signal_dir(dbase):
    #                     tag = mass_tag_from_dir(dbase)
    #                 edges = results.get(tag) or results.get("combined", [])

    #                 cat = np.full(len(score), -99, np.int16)
    #                 region = np.full(len(score), -1, np.int8)

    #                 for i, thr in enumerate(edges):
    #                     sel = (score >= thr) & sr_mask
    #                     cat[sel] = i
    #                     region[sel] = 1

    #                 cat[cr_mask] = -1
    #                 region[cr_mask] = 0

    #                 # write original branches + new ones
    #                 # data_np = {k: ak.to_numpy(v) for k, v in tree.arrays(library="ak").items()}
    #                 # data_np["cat"] = cat
    #                 # data_np["region"] = region
    #                 # fout[f"{dbase}/{tbase}"] = data_np
    #                 data_np = tree.arrays(library="np")  # dict[str, np.ndarray]
    #                 data_np["cat"] = cat
    #                 data_np["region"] = region
    #                 fout[f"{dbase}/{tbase}"] = data_np

    #     print(f"Wrote {out_root}")
        

if __name__ == "__main__":
    main()
