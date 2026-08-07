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

# ttH-killer score branch, expected to already be attached to each sample's
# tree the same way pDNN_score was (per-event, written out after training).
BR_TTH     = "ttH_killer_score"

# Branch labels used everywhere below. "low" = ttH-depleted (kept as the
# analysis's primary signal-region branch), "high" = ttH-enriched (split
# off so ttH contamination is confined to, and constrained within, its own
# branch rather than diluted across every category).
TTH_LOW  = "tth_low"   # ttH-killer score < cut  -> ttH-depleted
TTH_HIGH = "tth_high"  # ttH-killer score >= cut -> ttH-enriched
TTH_ALL  = "combined"  # used when --tth-cut is not given (no split at all)

USE_SIGMOID_SCORE = False
def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

# -------------------- helpers: directory/type detection --------------------
def is_data_dir(name: str) -> bool:
    n = name.lower()
    return n.startswith("data") or n.startswith("_data")

def is_signal_dir(name: str) -> bool:
    n = name.lower()
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

# -------------------- ttH-killer branch split --------------------
def tth_branch_mask(tth_score_np, cut):
    """Return boolean mask: True where event falls in the ttH-enriched
    ("high") branch, i.e. ttH-killer score >= cut. False = ttH-depleted."""
    return tth_score_np >= cut

def branch_labels(cut):
    """Which branch keys are active for this run."""
    if cut is None:
        return [TTH_ALL]
    return [TTH_LOW, TTH_HIGH]

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
    """Greedy category-boundary search, implementing the exact 6-step
    B2G-24-001 procedure:

      1. Sort events by score, descending.
      2. Candidate SR = the next `nmin` highest-scoring events among those
         NOT YET assigned to an accepted SR.
      3. Compare summed AMS^2 significance with the currently-accepted SRs
         only ("before") vs. accepted SRs + this candidate ("after").
      4. If the relative improvement is >= min_gain, ACCEPT this SR, move
         on to the next remaining events, and reset nmin back to its
         starting value for the next SR search.
      5/6. If improvement is insufficient, double nmin and retry from the
         same starting point; keep doubling until an improvement is found
         or too few events remain.

    This function is branch-agnostic: it is called once per (tag, ttH
    branch) pair, on whatever events already belong to that branch. The
    ttH-killer split happens upstream, when events are bucketed; nothing
    about the edge-building logic itself changes between branches.
    """
    order = np.argsort(scores)[::-1]
    s, sw, bw = scores[order], s_w[order], b_w[order]
    N = len(s)

    nmin_start = nmin
    edges: list = []
    accepted_S: list = []
    accepted_B: list = []
    idx = 0

    def significance(acc_S, acc_B):
        return objective(acc_S, acc_B) if acc_S else 0.0

    while (N - idx) >= 1 and len(edges) < max_bins:
        this_nmin = min(nmin, N - idx)
        nxt = idx + this_nmin
        S_new = sw[idx:nxt].sum()
        B_new = bw[idx:nxt].sum()

        best = significance(accepted_S, accepted_B)
        cand = objective(accepted_S + [S_new], accepted_B + [B_new])
        gain = (best - cand) / abs(best) if best != 0 else 1.0

        if gain >= min_gain:
            edges.append(float(s[nxt - 1]))
            accepted_S.append(S_new)
            accepted_B.append(B_new)
            idx = nxt
            nmin = nmin_start
        else:
            nmin *= 2
            if nmin > (N - idx):
                break

    return sorted(edges)

# -------------------- alpha(pDNN): CR -> SR transfer --------------------
def make_alpha(score_sr_mc, w_sr_mc, score_cr_mc, w_cr_mc, nbins=60):
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
    ap = argparse.ArgumentParser(description="Sideband-based (data-driven) pDNN categorization using AMS and alpha(score), "
                                              "with an optional orthogonal ttH-killer pre-split.")
    ap.add_argument("--root", required=True, help="merged ROOT file with per-sample directories")
    ap.add_argument("--sr-sigma", type=float, default=SR_DEFAULT, help="SR: |mgg-125| < SR_SIGMA (GeV)")
    ap.add_argument("--cr-sidebands", type=float, nargs=2, default=list(CR_DEFAULT),
                    help="CR: |mgg-125| in [LO, HI) (GeV)")
    ap.add_argument("--nmin", type=int, default=20, help="min events per candidate bin")
    ap.add_argument("--min-gain", type=float, default=0.05,
                     help="min relative improvement in summed AMS^2 to accept a new SR "
                          "(e.g. 0.05 = 5%%, per B2G-24-001 step 4)")
    ap.add_argument("--max-bins", type=int, default=10, help="max SR bins")
    ap.add_argument("--outdir", default="outputs/categories_alpha")
    ap.add_argument("--per-mass", action="store_true", help="derive per-mass edges for signal dirs")
    ap.add_argument("--write-categorized", action="store_true", help="clone ROOT and add cat/region branches")
    ap.add_argument("--alpha-bins", type=int, default=60, help="nbins for alpha(score)")
    ap.add_argument("--sigmoid-score", action="store_true", help="apply sigmoid to pDNN_score (if logits)")

    # --- new: ttH-killer pre-split (Option B) ---
    ap.add_argument("--tth-branch", default=BR_TTH,
                     help="ttH-killer score branch name in each tree (default: %(default)s)")
    ap.add_argument("--tth-cut", type=float, default=None,
                     help="ttH-killer working-point cut. If given, events are split into "
                          "'tth_low' (score < cut, ttH-depleted) and 'tth_high' (score >= cut, "
                          "ttH-enriched) BEFORE pDNN categorization; the existing edge-building "
                          "algorithm then runs independently, unmodified, in each branch. "
                          "If omitted, behaves exactly as before (single 'combined' branch).")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    if args.sigmoid_score:
        global USE_SIGMOID_SCORE
        USE_SIGMOID_SCORE = True

    sr_lo = 125.0 - args.sr_sigma
    sr_hi = 125.0 + args.sr_sigma
    cr_lo, cr_hi = args.cr_sidebands

    tth_cut = args.tth_cut
    active_branches = branch_labels(tth_cut)
    if tth_cut is not None:
        print(f"[INFO] ttH-killer pre-split ENABLED: branch='{args.tth_branch}', cut={tth_cut:.4f} "
              f"(low=depleted <{tth_cut:.4f}, high=enriched >={tth_cut:.4f})")
    else:
        print("[INFO] ttH-killer pre-split DISABLED (no --tth-cut given); running single combined branch, "
              "identical to the original pDNN-only categorization.")

    # -------- read & collect --------
    with uproot.open(args.root) as fin:
        dir_bases = collect_dirs(fin)

        # buckets are now keyed by (tag, ttH_branch)
        buckets = {}
        def ensure(tag, branch):
            key = (tag, branch)
            if key not in buckets:
                buckets[key] = dict(
                    S_sr_scores=[], S_sr_w=[],
                    B_sr_scores_mc=[], B_sr_w_mc=[],
                    B_cr_scores_mc=[], B_cr_w_mc=[],
                    D_cr_scores=[], D_cr_w=[]
                )
            return buckets[key]

        for dbase in dir_bases:
            tdir = fin[dbase]
            sel_key = get_tree_key(tdir, TREE_NAME)
            if sel_key is None:
                continue

            tree = tdir[sel_key]
            tfields = set(tree.keys())
            needed = {BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA}
            if tth_cut is not None:
                needed = needed | {args.tth_branch}
            if not needed.issubset(tfields):
                if tth_cut is not None and args.tth_branch not in tfields:
                    print(f"[warn] '{dbase}': missing ttH-killer branch '{args.tth_branch}'; skipping.")
                continue

            read_fields = [BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA]
            if tth_cut is not None:
                read_fields.append(args.tth_branch)

            arr = tree.arrays(read_fields, library="ak")
            mgg   = arr[BR_MGG]
            score = arr[BR_SCORE]
            wgt   = arr[BR_WGT]
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(mgg)

            mc   = (isdata == 0)
            data = (isdata != 0)
            mc_np   = ak.to_numpy(mc)
            data_np = ak.to_numpy(data)

            in_sr = (mgg >= sr_lo) & (mgg <= sr_hi)
            absd  = np.abs(ak.to_numpy(mgg) - 125.0)
            in_cr = (absd >= cr_lo) & (absd < cr_hi)
            in_sr_np = ak.to_numpy(in_sr)
            in_cr_np = in_cr  # already numpy (built from ak.to_numpy(mgg))

            score_np = ak.to_numpy(score)
            if USE_SIGMOID_SCORE:
                score_np = sigmoid(score_np)
            w_np = ak.to_numpy(wgt)

            # ttH-killer branch assignment (per-event, before anything else)
            if tth_cut is not None:
                tth_score_np = ak.to_numpy(arr[args.tth_branch])
                is_high = tth_branch_mask(tth_score_np, tth_cut)  # True -> ttH-enriched
            else:
                is_high = np.zeros(len(score_np), dtype=bool)  # unused when no split

            tag = "combined"
            if args.per_mass and is_signal_dir(dbase):
                tag = mass_tag_from_dir(dbase)

            for branch in active_branches:
                if tth_cut is None:
                    branch_sel_all = np.ones(len(score_np), dtype=bool)
                else:
                    branch_sel_all = (is_high if branch == TTH_HIGH else ~is_high)

                dest = ensure(tag, branch)

                if is_data_dir(dbase):
                    dsel = in_cr_np[data_np] & branch_sel_all[data_np]
                    dest["D_cr_scores"].append(score_np[data_np][dsel])
                    dest["D_cr_w"].append(np.ones_like(score_np[data_np][dsel]))
                elif is_signal_dir(dbase):
                    ssel = in_sr_np[mc_np] & branch_sel_all[mc_np]
                    dest["S_sr_scores"].append(score_np[mc_np][ssel])
                    dest["S_sr_w"].append(w_np[mc_np][ssel])
                else:
                    ssel = in_sr_np[mc_np] & branch_sel_all[mc_np]
                    csel = in_cr_np[mc_np] & branch_sel_all[mc_np]
                    dest["B_sr_scores_mc"].append(score_np[mc_np][ssel])
                    dest["B_sr_w_mc"].append(w_np[mc_np][ssel])
                    dest["B_cr_scores_mc"].append(score_np[mc_np][csel])
                    dest["B_cr_w_mc"].append(w_np[mc_np][csel])

    # -------- build edges with alpha(score), per (tag, branch) --------
    # results[tag][branch] = edges
    results = {}
    for (tag, branch), d in buckets.items():
        Sscore = concat1(d["S_sr_scores"]); Sw = concat1(d["S_sr_w"])
        Bsr_mc = concat1(d["B_sr_scores_mc"]); Bsrw_mc = concat1(d["B_sr_w_mc"])
        Bcr_mc = concat1(d["B_cr_scores_mc"]); Bcrw_mc = concat1(d["B_cr_w_mc"])
        Dcr    = concat1(d["D_cr_scores"]);    Dcrw    = concat1(d["D_cr_w"])

        if Sscore.size == 0 or Dcr.size == 0 or Bsr_mc.size == 0 or Bcr_mc.size == 0:
            print(f"[warn] Tag '{tag}' / branch '{branch}': insufficient inputs for alpha-method; skipping.")
            continue

        centers, alpha, lohi = make_alpha(Bsr_mc, Bsrw_mc, Bcr_mc, Bcrw_mc, nbins=args.alpha_bins)
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
        results.setdefault(tag, {})[branch] = edges
        print(f"[edges alpha-method] tag='{tag}' branch='{branch}': {edges}")

    # -------- write JSON --------
    out_json = os.path.join(args.outdir, "event_categories.json")
    payload = {
        "boundaries": results,          # results[tag][branch] = [edges]
        "sr_mgg_window_GeV": args.sr_sigma,
        "cr_mgg_sidebands_GeV": list(args.cr_sidebands),
        "tth_split": {
            "enabled": tth_cut is not None,
            "branch_name": args.tth_branch if tth_cut is not None else None,
            "cut": tth_cut,
        },
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

            for dkey in fin.keys():
                obj = fin[dkey]
                dbase = dkey.split(";")[0]
                if isinstance(obj, uproot.reading.ReadOnlyDirectory):
                    try:
                        fout.mkdir(dbase)
                    except Exception:
                        pass

            def write_tree(out_dir, tname: str, arrays_np: dict):
                clean = {}
                for k, v in arrays_np.items():
                    arr = np.asarray(v)

                    if arr.dtype == np.dtype("O"):
                        raise RuntimeError(f"Branch '{tname}:{k}' has object dtype — convert jagged arrays to fixed numpy arrays first.")

                    if arr.ndim != 1:
                        raise RuntimeError(f"Branch '{tname}:{k}' is not 1-D (ndim={arr.ndim}).")

                    if np.issubdtype(arr.dtype, np.integer):
                        amin = arr.min() if arr.size else 0
                        amax = arr.max() if arr.size else 0
                        if amin < np.iinfo(np.int32).min or amax > np.iinfo(np.int32).max:
                            print(f"[warn] Branch '{tname}:{k}' requires int64 range ({amin}..{amax}). Keeping int64.")
                            clean[k] = arr.astype(np.int64)
                        else:
                            clean[k] = arr.astype(np.int32)
                        continue

                    if np.issubdtype(arr.dtype, np.floating):
                        clean[k] = arr.astype(np.float32)
                        continue

                    if arr.dtype == np.bool_:
                        clean[k] = arr.astype(np.uint8)
                        continue

                    clean[k] = arr

                branch_types = {k: v.dtype for k, v in clean.items()}
                out_tree = out_dir.mktree(tname, branch_types)
                out_tree.extend(clean)

            for dkey in fin.keys():
                in_dir_obj = fin[dkey]
                if not isinstance(in_dir_obj, uproot.reading.ReadOnlyDirectory):
                    continue

                dbase = dkey.split(";")[0]
                out_dir = fout[dbase]

                for tkey in in_dir_obj.keys():
                    tbase = tkey.split(";")[0]
                    tree  = in_dir_obj[tkey]

                    required_ok = (
                        tbase == TREE_NAME
                        and BR_SCORE in tree.keys()
                        and BR_MGG   in tree.keys()
                        and (tth_cut is None or args.tth_branch in tree.keys())
                    )
                    if not required_ok:
                        arrays_np = tree.arrays(library="np")
                        write_tree(out_dir, tbase, arrays_np)
                        continue

                    read_fields = [BR_SCORE, BR_MGG]
                    if tth_cut is not None:
                        read_fields.append(args.tth_branch)

                    arr = tree.arrays(read_fields, library="ak")
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

                    tag_results = results.get(tag, results.get("combined", {}))

                    if tth_cut is not None:
                        tth_score_np = ak.to_numpy(arr[args.tth_branch])
                        is_high = tth_branch_mask(tth_score_np, tth_cut)
                        tth_branch_arr = np.where(is_high, 1, 0).astype(np.int8)  # 0=low/depleted, 1=high/enriched
                    else:
                        is_high = np.zeros(len(score_np), dtype=bool)
                        tth_branch_arr = np.zeros(len(score_np), dtype=np.int8)

                    cat    = np.full(len(score_np), -99, np.int16)
                    region = np.full(len(score_np),  -1, np.int8)

                    for branch_name, branch_is_high in ((TTH_LOW, False), (TTH_HIGH, True)) if tth_cut is not None else ((TTH_ALL, None),):
                        edges = tag_results.get(branch_name)
                        if edges is None:
                            fallback = results.get("combined", {}).get(branch_name, [])
                            edges = fallback
                            if edges and args.per_mass and is_signal_dir(dbase):
                                print(f"[warn] No per-mass edges for tag='{tag}' branch='{branch_name}' "
                                      f"(dir '{dbase}'); falling back to 'combined' edges.")

                        if tth_cut is None:
                            branch_mask = np.ones(len(score_np), dtype=bool)
                        else:
                            branch_mask = (is_high if branch_is_high else ~is_high)

                        for i, thr in enumerate(edges or []):
                            sel = (score_np >= thr) & sr_mask & branch_mask
                            cat[sel]    = i
                            region[sel] = 1

                    cat[cr_mask]    = -1
                    region[cr_mask] = 0

                    arrays_np = tree.arrays(library="np")
                    arrays_np["cat"]        = cat
                    arrays_np["region"]     = region
                    if tth_cut is not None:
                        arrays_np["tth_branch"] = tth_branch_arr  # 0=depleted, 1=enriched
                    write_tree(out_dir, tbase, arrays_np)

        print(f"Wrote {out_root}")


if __name__ == "__main__":
    main()