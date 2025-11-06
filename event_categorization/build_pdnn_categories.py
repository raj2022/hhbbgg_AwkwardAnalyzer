#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re, math
import numpy as np
import awkward as ak
import uproot

# -------------------- user defaults --------------------
SR_DEFAULT = 2.0                 # SR: |mgg-125| < SR_DEFAULT (GeV)
CR_DEFAULT = (4.0, 10.0)         # CR: 4 <= |mgg-125| < 10 (GeV)
TREE_NAME  = "selection"         # tree inside each directory

BR_SCORE   = "pDNN_score"
BR_MGG     = "diphoton_mass"
BR_WGT     = "weight_selection"
BR_ISDATA  = "isdata"

USE_SIGMOID_SCORE = False
def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

# -------------------- helpers: directory/type detection --------------------
def is_data_dir(name: str) -> bool:
    n = name.lower()
    return n.startswith("data") or n.startswith("_data")

def is_signal_dir(name: str) -> bool:
    n = name.lower()
    # tighten to avoid false positives
    return (
        "nmssm" in n or
        "gluglutohh" in n or
        "radion" in n or
        "graviton" in n or
        re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
    )

def mass_tag_from_dir(name: str) -> str:
    n = name.lower()
    m = re.search(r"x(\d+)_y(\d+)", n)
    if m: return f"mX{m.group(1)}_mY{m.group(2)}"
    m2 = re.search(r"m(\d+)", n)
    return f"m{m2.group(1)}" if m2 else "combined"

def collect_dirs(fin):
    dirs = []
    for dkey in fin.keys():
        dbase = dkey.split(";")[0]
        obj = fin[dkey]
        if isinstance(obj, uproot.reading.ReadOnlyDirectory) and dbase not in dirs:
            dirs.append(dbase)
    return dirs

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

def concat1(lst):
    if not lst: return np.array([], dtype=float)
    if len(lst) == 1: return ak.to_numpy(lst[0])
    return ak.to_numpy(ak.concatenate(lst, axis=0))

# -------------------- significance & optimization --------------------
def AMS(s, b):
    """AMS = sqrt( 2 * ((s+b) ln(1+s/b) - s) )"""
    if b <= 0.0:
        return 0.0
    return math.sqrt(max(0.0, 2.0 * ((s + b) * math.log(1.0 + s / b) - s)))

def objective(Ss, Bs):
    """We maximize sum(AMS^2) -> minimize negative for greedy selection."""
    return -sum(AMS(s, b)**2 for s, b in zip(Ss, Bs))

def build_edges(scores, s_w, b_w, nmin, min_gain, max_bins):
    """Greedy binning from high score to low.
       Start with base sums (all remaining as 1 'bin'), then try to add bins of size nmin.
       If Δobjective / |objective| >= min_gain, accept; else double nmin."""
    order = np.argsort(scores)[::-1]
    s  = scores[order]
    sw = s_w[order]
    bw = b_w[order]

    N = len(s)
    edges = []
    idx = 0

    base_S = [sw.sum()]
    base_B = [bw.sum()]
    best   = objective(base_S, base_B)

    while (N - idx) >= nmin and len(edges) < max_bins:
        nxt = min(N, idx + nmin)
        S_new = sw[idx:nxt].sum()
        B_new = bw[idx:nxt].sum()

        cand_S = base_S + [S_new]
        cand_B = base_B + [B_new]
        cand   = objective(cand_S, cand_B)
        gain   = (best - cand) / abs(best) if best != 0 else 1.0

        if gain >= min_gain:
            # accept this bin slice; next slice starts at nxt
            edges.append(float(s[nxt - 1]))  # lower edge for this accepted slice
            base_S.append(S_new)
            base_B.append(B_new)
            best = cand
            idx  = nxt
        else:
            nmin *= 2
            if nmin > (N - idx):
                break

    # return in ascending order (lower edges)
    return sorted(edges)

# -------------------- alpha(pDNN): CR -> SR transfer --------------------
def make_alpha(score_sr_mc, w_sr_mc, score_cr_mc, w_cr_mc, nbins=60):
    """Build α(score) = (MC_bkg_SR / MC_bkg_CR)(score), as binned ratio."""
    # define range from MC distributions
    lo = float(np.min([np.min(score_sr_mc), np.min(score_cr_mc)]))
    hi = float(np.max([np.max(score_sr_mc), np.max(score_cr_mc)]))
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = -5.0, 5.0
    edges = np.linspace(lo, hi, nbins + 1)

    h_sr, _ = np.histogram(score_sr_mc, bins=edges, weights=w_sr_mc)
    h_cr, _ = np.histogram(score_cr_mc, bins=edges, weights=w_cr_mc)

    eps = 1e-9
    alpha = (h_sr + eps) / (h_cr + eps)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, alpha, (lo, hi)

def eval_alpha(x, centers, alpha, lohi):
    lo, hi = lohi
    return np.interp(np.clip(x, lo, hi), centers, alpha)

# -------------------- main --------------------
def main():
    ap = argparse.ArgumentParser(description="Sideband-based (data-driven) pDNN categorization using AMS and α(score).")
    ap.add_argument("--root", required=True, help="merged ROOT file with per-sample directories")
    ap.add_argument("--sr-sigma", type=float, default=SR_DEFAULT, help="SR: |mgg-125| < SR_SIGMA (GeV)")
    ap.add_argument("--cr-sidebands", type=float, nargs=2, default=list(CR_DEFAULT),
                    help="CR: |mgg-125| in [LO, HI) (GeV)")
    ap.add_argument("--nmin", type=int, default=20, help="min events per candidate bin")
    ap.add_argument("--min-gain", type=float, default=0.01, help="min relative improvement (e.g. 0.01 = 1%)")
    ap.add_argument("--max-bins", type=int, default=10, help="max SR bins")
    ap.add_argument("--outdir", default="outputs/categories_alpha")
    ap.add_argument("--per-mass", action="store_true", help="derive per-mass edges for signal dirs")
    ap.add_argument("--write-categorized", action="store_true", help="clone ROOT and add cat/region branches")
    ap.add_argument("--alpha-bins", type=int, default=60, help="nbins for α(score)")
    ap.add_argument("--sigmoid-score", action="store_true", help="apply sigmoid to pDNN_score (if logits)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    if args.sigmoid_score:
        global USE_SIGMOID_SCORE
        USE_SIGMOID_SCORE = True

    sr_lo = 125.0 - args.sr_sigma
    sr_hi = 125.0 + args.sr_sigma
    cr_lo, cr_hi = args.cr_sidebands

    # -------- read & collect --------
    with uproot.open(args.root) as fin:
        dir_bases = collect_dirs(fin)

        # Per tag (combined / mass-tag)
        buckets = {}
        def ensure(tag):
            if tag not in buckets:
                buckets[tag] = dict(
                    S_sr_scores=[], S_sr_w=[],
                    B_sr_scores_mc=[], B_sr_w_mc=[],
                    B_cr_scores_mc=[], B_cr_w_mc=[],
                    D_cr_scores=[], D_cr_w=[]
                )
            return buckets[tag]

        for dbase in dir_bases:
            tdir = fin[dbase]
            sel_key = get_tree_key(tdir, TREE_NAME)
            if sel_key is None:
                continue

            tree = tdir[sel_key]
            tfields = set(tree.keys())
            needed = {BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA}
            if not needed.issubset(tfields):
                continue

            arr = tree.arrays([BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA], library="ak")
            mgg   = arr[BR_MGG]
            score = arr[BR_SCORE]
            wgt   = arr[BR_WGT]
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(mgg)

            mc   = (isdata == 0)
            data = (isdata != 0)

            in_sr = (mgg >= sr_lo) & (mgg <= sr_hi)
            absd  = np.abs(ak.to_numpy(mgg) - 125.0)
            in_cr = (absd >= cr_lo) & (absd < cr_hi)

            # score to numpy (+ optional sigmoid)
            score_np = ak.to_numpy(score)
            if USE_SIGMOID_SCORE:
                score_np = sigmoid(score_np)
            w_np = ak.to_numpy(wgt)

            tag = "combined"
            if args.per_mass and is_signal_dir(dbase):
                tag = mass_tag_from_dir(dbase)
            dest = ensure(tag)

            if is_data_dir(dbase):
                # data: only CR input (unit weights unless you prefer w_np[data])
                dsel = ak.to_numpy(in_cr[data])
                dest["D_cr_scores"].append(score_np[data][dsel])
                dest["D_cr_w"].append(np.ones_like(score_np[data][dsel]))
            elif is_signal_dir(dbase):
                ssel = ak.to_numpy(in_sr[mc])
                dest["S_sr_scores"].append(score_np[mc][ssel])
                dest["S_sr_w"].append(w_np[mc][ssel])
            else:
                # MC backgrounds feed alpha SR/CR
                ssel = ak.to_numpy(in_sr[mc])
                csel = ak.to_numpy(in_cr[mc])
                dest["B_sr_scores_mc"].append(score_np[mc][ssel])
                dest["B_sr_w_mc"].append(w_np[mc][ssel])
                dest["B_cr_scores_mc"].append(score_np[mc][csel])
                dest["B_cr_w_mc"].append(w_np[mc][csel])

    # -------- build edges with α(score) --------
    results = {}
    for tag, d in buckets.items():
        Sscore = concat1(d["S_sr_scores"]); Sw = concat1(d["S_sr_w"])
        Bsr_mc = concat1(d["B_sr_scores_mc"]); Bsrw_mc = concat1(d["B_sr_w_mc"])
        Bcr_mc = concat1(d["B_cr_scores_mc"]); Bcrw_mc = concat1(d["B_cr_w_mc"])
        Dcr    = concat1(d["D_cr_scores"]);    Dcrw    = concat1(d["D_cr_w"])

        if Sscore.size == 0 or Dcr.size == 0 or Bsr_mc.size == 0 or Bcr_mc.size == 0:
            print(f"[warn] Tag '{tag}': insufficient inputs for α-method; skipping.")
            continue

        centers, alpha, lohi = make_alpha(Bsr_mc, Bsrw_mc, Bcr_mc, Bcrw_mc, nbins=args.alpha_bins)
        # background scores from data (CR) reweighted to SR
        Bscore = Dcr
        Bw     = eval_alpha(Dcr, centers, alpha, lohi) * Dcrw

        edges = build_edges(
            scores=np.concatenate([Sscore, Bscore]),
            s_w=np.concatenate([Sw, np.zeros_like(Bw)]),
            b_w=np.concatenate([np.zeros_like(Sw), Bw]),
            nmin=args.nmin,
            min_gain=args.min_gain,
            max_bins=args.max_bins
        )
        results[tag] = edges
        print(f"[edges α-method] {tag}: {edges}")

    # -------- write JSON --------
    out_json = os.path.join(args.outdir, "event_categories.json")
    payload = {
        "boundaries": results,
        "sr_mgg_window_GeV": args.sr_sigma,
        "cr_mgg_sidebands_GeV": list(args.cr_sidebands)
    }
    with open(out_json, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out_json}")

    
    
    
    
       # -------- optional: categorized ROOT copy (uproot-5 safe) --------
    if args.write_categorized:
        out_root = os.path.join(
            args.outdir,
            os.path.basename(args.root).replace(".root", "__categorized.root")
        )
        with uproot.open(args.root) as fin, uproot.recreate(out_root) as fout:

            # 1) Mirror top-level directories (samples) once.
            for dkey in fin.keys():
                obj = fin[dkey]
                dbase = dkey.split(";")[0]
                if isinstance(obj, uproot.reading.ReadOnlyDirectory):
                    try:
                        fout.mkdir(dbase)  # create empty directory in output
                    except Exception:
                        # if it already exists in the brand-new file (unlikely), just ignore
                        pass

            # Helper to write a tree (dict[str, np.ndarray]) into a directory
            def write_tree(out_dir, tname: str, arrays_np: dict):
                clean = {}
                for k, v in arrays_np.items():
                    arr = np.asarray(v)
                    
                    if arr.dtype == np.dtype("O"):
                        raise RuntimeError(f"Branch '{tname}:{k}' has object dtype — convert jagged arrays to fixed numpy arrays first.")
                    
                    if arr.ndim != 1:
                        raise RuntimeError(f"Branch '{tname}:{k}' is not 1-D (ndim={arr.ndim}).")

                    if np.issubdtype(arr.dtype, np.integer):
                        # if values fit int32, cast; otherwise keep int64 but warn
                        amin = arr.min() if arr.size else 0
                        amax = arr.max() if arr.size else 0
                        if amin < np.iinfo(np.int32).min or amax > np.iinfo(np.int32).max:
                            # if you truly need int64, keep it (uproot supports int64), but warn
                            print(f"[warn] Branch '{tname}:{k}' requires int64 range ({amin}..{amax}). Keeping int64.")
                            clean[k] = arr.astype(np.int64)
                        else:
                            clean[k] = arr.astype(np.int32)
                        continue

                    # floats: downcast to float32 to reduce surprises (but keep float64 if you must)
                    if np.issubdtype(arr.dtype, np.floating):
                        # you can choose to keep float64; float32 is usually fine for weights etc.
                        clean[k] = arr.astype(np.float32)
                        continue

                    # bool -> uint8
                    if arr.dtype == np.bool_:
                        clean[k] = arr.astype(np.uint8)
                        continue

                    # other numeric dtypes (like fixed-width) pass through
                    clean[k] = arr  
                    
                branch_types = {k: v.dtype for k, v in clean.items()}
                out_tree = out_dir.mktree(tname, branch_types)
                out_tree.extend(clean)

            # 2) Loop directories/trees and write
            for dkey in fin.keys():
                in_dir_obj = fin[dkey]
                if not isinstance(in_dir_obj, uproot.reading.ReadOnlyDirectory):
                    continue  # safety: only process directories

                dbase = dkey.split(";")[0]
                out_dir = fout[dbase]  # WritableDirectory (we created it above)

                for tkey in in_dir_obj.keys():
                    tbase = tkey.split(";")[0]
                    tree  = in_dir_obj[tkey]

                    # Copy non-selection trees verbatim
                    if (
                        tbase != TREE_NAME
                        or (BR_SCORE not in tree.keys())
                        or (BR_MGG   not in tree.keys())
                    ):
                        arrays_np = tree.arrays(library="np")
                        write_tree(out_dir, tbase, arrays_np)
                        continue

                    # selection: compute cat/region and write
                    arr = tree.arrays(library="ak")
                    score_np = ak.to_numpy(arr[BR_SCORE])
                    if USE_SIGMOID_SCORE:
                        score_np = 1.0 / (1.0 + np.exp(-score_np))
                    mgg_np   = ak.to_numpy(arr[BR_MGG])

                    sr_mask = np.abs(mgg_np - 125.0) < args.sr_sigma
                    lo, hi  = args.cr_sidebands
                    cr_mask = (np.abs(mgg_np - 125.0) >= lo) & (np.abs(mgg_np - 125.0) < hi)

                    tag = "combined"
                    if args.per_mass and is_signal_dir(dbase):
                        tag = mass_tag_from_dir(dbase)
                    edges = results.get(tag) or results.get("combined", [])

                    cat    = np.full(len(score_np), -99, np.int16)
                    region = np.full(len(score_np),  -1, np.int8)
                    for i, thr in enumerate(edges):
                        sel = (score_np >= thr) & sr_mask
                        cat[sel]    = i
                        region[sel] = 1
                    cat[cr_mask]    = -1
                    region[cr_mask] = 0

                    arrays_np = tree.arrays(library="np")
                    arrays_np["cat"]    = cat
                    arrays_np["region"] = region
                    write_tree(out_dir, tbase, arrays_np)

        print(f"Wrote {out_root}")
 


    # # -------- optional: categorized ROOT copy --------
    # if args.write_categorized:
    #     out_root = os.path.join(
    #         args.outdir,
    #         os.path.basename(args.root).replace(".root", "__categorized.root")
    #     )
    #     with uproot.open(args.root) as fin, uproot.recreate(out_root) as fout:
    #         dir_bases = collect_dirs(fin)
    #         for dbase in dir_bases:
    #             try:
    #                 fout.mkdir(dbase)
    #             except Exception:
    #                 pass

    #         for dkey in fin.keys():
    #             dbase = dkey.split(";")[0]
    #             in_dir  = fin[dkey]
    #             out_dir = fout[dbase]

    #             # for tkey in in_dir.keys():
    #             #     tbase = tkey.split(";")[0]
    #             #     tree  = in_dir[tkey]

    #             #     # copy non-selection trees verbatim
    #             #     if tbase != TREE_NAME or (BR_SCORE not in tree.keys()) or (BR_MGG not in tree.keys()):
    #             #         out_dir[tbase] = tree.arrays(library="np")
    #             #         continue
                
    #             for tkey in in_dir.keys():
    #                 tbase = tkey.split(";")[0]
    #                 tree  = in_dir[tkey]

    #                 # copy non-selection trees verbatim
    #                 if tbase != TREE_NAME or (BR_SCORE not in tree.keys()) or (BR_MGG not in tree.keys()):
    #                     arrays_np = tree.arrays(library="np")
    #                     out_dir.mktree(tbase, {k: v.dtype for k, v in arrays_np.items()})
    #                     out_dir[tbase].extend(arrays_np)
    #                     continue

    #                 # selection: add cat/region
    #                 arr = tree.arrays(library="ak")
    #                 score_np = ak.to_numpy(arr[BR_SCORE])
    #                 if USE_SIGMOID_SCORE:
    #                     score_np = sigmoid(score_np)
    #                 mgg_np = ak.to_numpy(arr[BR_MGG])

    #                 sr_mask = np.abs(mgg_np - 125.0) < args.sr_sigma
    #                 lo, hi = args.cr_sidebands
    #                 cr_mask = (np.abs(mgg_np - 125.0) >= lo) & (np.abs(mgg_np - 125.0) < hi)

    #                 tag = "combined"
    #                 if args.per_mass and is_signal_dir(dbase):
    #                     tag = mass_tag_from_dir(dbase)
    #                 edges = results.get(tag) or results.get("combined", [])

    #                 cat = np.full(len(score_np), -99, np.int16)
    #                 region = np.full(len(score_np), -1, np.int8)
    #                 for i, thr in enumerate(edges):
    #                     sel = (score_np >= thr) & sr_mask
    #                     cat[sel] = i
    #                     region[sel] = 1
    #                 cat[cr_mask] = -1
    #                 region[cr_mask] = 0

    #                 arrays_np = tree.arrays(library="np")
    #                 arrays_np["cat"] = cat
    #                 arrays_np["region"] = region

    #                 out_dir.mktree(tbase, {k: v.dtype for k, v in arrays_np.items()})
    #                 out_dir[tbase].extend(arrays_np)


    #                 arr = tree.arrays(library="ak")
    #                 score_np = ak.to_numpy(arr[BR_SCORE])
    #                 if USE_SIGMOID_SCORE:
    #                     score_np = sigmoid(score_np)
    #                 mgg_np   = ak.to_numpy(arr[BR_MGG])

    #                 sr_mask = np.abs(mgg_np - 125.0) < args.sr_sigma
    #                 lo, hi  = args.cr_sidebands
    #                 cr_mask = (np.abs(mgg_np - 125.0) >= lo) & (np.abs(mgg_np - 125.0) < hi)

    #                 # choose edges (per-mass for signal dirs if requested)
    #                 tag = "combined"
    #                 if args.per_mass and is_signal_dir(dbase):
    #                     tag = mass_tag_from_dir(dbase)
    #                 edges = results.get(tag) or results.get("combined", [])

    #                 cat    = np.full(len(score_np), -99, np.int16)
    #                 region = np.full(len(score_np),  -1, np.int8)
    #                 for i, thr in enumerate(edges):
    #                     sel = (score_np >= thr) & sr_mask
    #                     cat[sel]    = i
    #                     region[sel] = 1
    #                 cat[cr_mask]    = -1
    #                 region[cr_mask] = 0

    #                 data_np = tree.arrays(library="np")
    #                 data_np["cat"]    = cat
    #                 data_np["region"] = region
    #                 out_dir[tbase]    = data_np

    #     print(f"Wrote {out_root}")

if __name__ == "__main__":
    main()
