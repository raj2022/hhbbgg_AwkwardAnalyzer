#!/usr/bin/env python3
"""
Fit mjj per signal mass point and per category using histogram-EM GMM (fast).
Saves one JSON with structure:
{
  "edges": [...],
  "masses": {
     "300": {"used_dirs": [...], "fits": {"0": {...}, "1": {...} } },
     "400": {...}
  }
}
and diagnostic PNGs in outdir/<mass>/.
"""
import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt

# branches (change if your ntuple uses different names)
TREE_NAME  = "selection"
BR_MJJ     = "dibjet_mass"
BR_SCORE   = "pDNN_score"
BR_ISDATA  = "isdata"

# -------------------------------------------------------------------
def is_signal_dir(name: str) -> bool:
    n = name.lower()
    return (
        "nmssm" in n or "radion" in n or "graviton" in n or
        "gluglutohh" in n or re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
    )

def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys()
            if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

# def get_tree_key(tdir, base):
#     for tkey in tdir.keys():
#         if tkey.split(";")[0] == base:
#             return tkey
#     return None

# add or replace with this function
def find_selection_tree(tdir, base=None):
    """
    Find the TTree for 'selection' (prefer exact match).
    Returns a key string like "selection;1" or "subdir;1/selection;1" or None.
    """
    # Candidate names in priority order
    candidates = ["selection", "srbbgg", "srbbggMET", "preselection", "processed_events"]

    # Build a map base->fullkey for quick lookup
    keymap = {k.split(';')[0].lower(): k for k in tdir.keys()}

    # 1) Prefer an exact candidate directly under tdir
    for cand in candidates:
        if cand.lower() in keymap:
            # return that key (e.g. "selection;1")
            return keymap[cand.lower()]

    # 2) If not found directly, check common subdirectories for a TTree named 'selection'
    for sub_key in tdir.keys():
        try:
            subobj = tdir[sub_key]
            # look for 'selection' in this subdir
            for sk in subobj.keys():
                if sk.split(';')[0].lower() == "selection":
                    return f"{sub_key}/{sk}"   # e.g. "srbbgg;1/selection;1"
            # else, if any TTree exists in this subdir prefer candidate names there
            # check for candidate names inside the subdir
            for cand in candidates:
                for sk in subobj.keys():
                    if sk.split(';')[0].lower() == cand.lower():
                        return f"{sub_key}/{sk}"
        except Exception:
            continue

    # 3) Last resort: return any TTree directly (only if nothing else matched)
    for key in tdir.keys():
        try:
            obj = tdir[key]
            if "TTree" in getattr(obj, "classname", ""):
                return key
        except Exception:
            continue

    return None


# -------------------------------------------------------------------
# EM on histogram (fast)
def gmm_em_on_hist(xcenters, counts, k, max_iter=200, tol=1e-6):
    mask = counts > 0
    x = xcenters[mask]
    w = counts[mask].astype(float)
    if w.sum() <= 0:
        # fallback equal weights on centers
        w = np.ones_like(x) / float(max(len(x),1))
    else:
        w /= w.sum()

    # init
    means  = np.quantile(x, np.linspace(0.2, 0.8, k))
    sigmas = np.full(k, 5.0)
    weights= np.full(k, 1.0/k)
    prev_ll = -np.inf
    x2 = x[:, None]

    for _ in range(max_iter):
        pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
        num  = weights * pdfs
        den  = (num).sum(axis=1, keepdims=True) + 1e-300
        r    = num / den
        Nk = (w[:, None] * r).sum(axis=0) + 1e-300
        weights = Nk / Nk.sum()
        means   = (w[:, None] * r * x2).sum(axis=0) / Nk
        var     = (w[:, None] * r * (x2 - means)**2).sum(axis=0) / Nk
        sigmas  = np.sqrt(np.clip(var, 1e-6, None))
        pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
        ll   = (w * np.log((pdfs * weights).sum(axis=1) + 1e-300)).sum()
        if abs(ll - prev_ll) < tol * (1.0 + abs(prev_ll)):
            break
        prev_ll = ll

    params = {
        "weights": weights.tolist(),
        "means":   means.tolist(),
        "sigmas":  sigmas.tolist(),
        "logL":    float(prev_ll)
    }
    p = 3*k - 1
    params["bic"] = float(-2.0*prev_ll + p*np.log(max(1, x.size)))
    return params

def mixture_pdf(x, params):
    w = np.array(params["weights"])
    m = np.array(params["means"])
    s = np.array(params["sigmas"])
    x2 = x[:, None]
    pdfs = (1.0/np.sqrt(2*np.pi)/s) * np.exp(-0.5*((x2 - m)**2)/(s**2))
    return (pdfs * w).sum(axis=1)

def model_counts(bin_edges, params, n_tot):
    centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    binw    = np.diff(bin_edges)
    dens    = mixture_pdf(centers, params)
    return dens * binw * n_tot

def chi2_reduced(counts, mu, k):
    var  = np.maximum(counts, 1.0)
    chi2 = np.sum((counts - mu)**2 / var)
    p    = 3*k - 1
    ndof = max(len(counts) - p, 1)
    return chi2 / ndof

# -------------------------------------------------------------------
def extract_mass_from_dir(dname):
    """
    Try multiple regex patterns to extract primary mass number.
    Returns string mass (e.g. "300") or None if not found.
    """
    name = dname
    # Pattern X300_Y125, NMSSM_X300_Y125 etc
    m = re.search(r"[xX](\d{2,4})[_\-]?y(\d{2,4})", name)
    if m:
        return m.group(1)
    # Pattern like _X500_
    m2 = re.search(r"[Xx](\d{2,4})", name)
    if m2:
        return m2.group(1)
    # fallback: look for numeric token
    m3 = re.search(r"(\d{3,4})", name)
    if m3:
        return m3.group(1)
    return None

# -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Fit signal mjj per mass and per category (fast hist-EM).")
    ap.add_argument("--root", required=True, help="merged ROOT file with per-sample dirs")
    ap.add_argument("--edges", type=float, nargs="*", default=None, help="pDNN threshold edges")
    ap.add_argument("--edges-json", default=None, help="JSON with {'boundaries': {'combined': [...]}}")
    ap.add_argument("--cats", type=int, nargs="*", default=None)
    ap.add_argument("--mjj-min", type=float, default=50.0)
    ap.add_argument("--mjj-max", type=float, default=200.0)
    ap.add_argument("--bins", type=int, default=150)
    ap.add_argument("--kmax", type=int, default=3)
    ap.add_argument("--outdir", default="outputs/signal_fits_mjj_by_mass")
    ap.add_argument("--only-signal", default=None)
    ap.add_argument("--max-events", type=int, default=200000)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # resolve edges
    if args.edges is not None and len(args.edges) > 0:
        edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            js = json.load(f)
        edges = sorted(js["boundaries"].get("combined", []))
    else:
        raise RuntimeError("Provide category thresholds with --edges or --edges-json")

    edges_full = [-np.inf] + edges + [np.inf]
    n_cats = len(edges_full) - 1
    if args.cats is None:
        cats = list(range(n_cats))
    else:
        cats = args.cats

    # collect mjj per (mass,cat)
    mass_cat_vals = {}   # dict: mass -> {cat: [arrays...]}
    mass_dirs = {}       # mass -> list of dirs used

    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            if args.only_signal and args.only_signal not in d:
                continue
            if not is_signal_dir(d):
                continue
            mass = extract_mass_from_dir(d)
            if mass is None:
                # skip if we cannot identify mass
                continue
            tdir = fin[d]
            # sel = find_selection_tree(tdir, TREE_NAME)
            # if sel is None:
            #     continue
            # # normalize path for uproot access: replace ';' occurrences and join with '/'
            # sel_parts = sel.split('/')
            # # convert tokens like "selection;1" to "selection"
            # sel_path = "/".join([p.split(';')[0] for p in sel_parts])
            # # open the tree via uproot using full path relative to the ROOT file:
            # # then open tree using uproot at file-level:
            # #-----------------
            # # try:
            # #     topdir_name = d
            # # except NameError:
            # #     topdir_name = None
            # #     for k in f.keys():
            # #         if k.split(';')[0] == sel_parts_clean[0]:
            # #             topdir_name = k.split(';')[0]
            # #             break
            # #     if topdir_name is None:
            # #         for k in f.keys():
            # #             try:
            # #                 if f[k] is tdir:
            # #                     topdir_name = k.split(';')[0]
            # #                     break
            # #             except Exception:
            # #                 continue
            # #     if topdir_name is None:
            # #         topdir_name = sel_parts_clean[0]

            # topdir_name = d
                    
            # # Build the path to the TTree. Use only the final tree name under the topdir.
            # full_path = "/".join([topdir_name, sel_parts_clean[-1]])  # e.g. "NMSSM_X300_Y125/selection"

            # # Try opening the tree via uproot. If that fails use a fallback that navigates objects.
            # try:
            #     tree = f[full_path]
            # except Exception:
            #     try:
            #         # locate the exact top-level key (with ;N)
            #         topkey = [k for k in f.keys() if k.split(';')[0] == topdir_name][0]
            #         tdir_obj = f[topkey]
            #         if len(sel_parts_clean) > 1:
            #             # nested: subdir -> tree
            #             subkey = [k for k in tdir_obj.keys() if k.split(';')[0] == sel_parts_clean[-2]][0]
            #             tree_key = [k for k in tdir_obj[subkey].keys() if k.split(';')[0] == sel_parts_clean[-1]][0]
            #             tree = tdir_obj[subkey][tree_key]
            #         else:
            #             # direct child
            #             tree_key = [k for k in tdir_obj.keys() if k.split(';')[0] == sel_parts_clean[-1]][0]
            #             tree = tdir_obj[tree_key]
            #     except Exception as e_open:
            #         print("[ERROR] failed to open tree at", full_path, "fallback error:", e_open)
            #         continue

            # # Read needed branches
            # arr = tree.arrays([BR_MJJ, BR_SCORE, BR_ISDATA], library="ak")
            # isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MJJ])
            # mc = (isdata == 0)

            # mjj = ak.to_numpy(arr[BR_MJJ][mc])
            # score = ak.to_numpy(arr[BR_SCORE][mc])
            
            # --- robust open: replace previous sel/topdir code with this block ---
            sel = find_selection_tree(tdir, TREE_NAME)
            print(f"[DEBUG] sample={d} -> sel={sel}")
            if sel is None:
                continue

            # sel may be "selection;1" or "subdir;1/selection;1" -> use last token first
            sel_last = sel.split('/')[-1]           # "selection;1"
            sel_base = sel_last.split(';')[0]       # "selection"

            # Try opening the tree directly from the top-level directory object tdir
            try:
                tree = tdir[sel_last]
            except Exception:
                # Fallback: open via the file object `fin`
                try:
                    # find the top-level key with ;N suffix that matches this sample `d`
                    topkey = [k for k in fin.keys() if k.split(';')[0] == d][0]
                    tdir_obj = fin[topkey]
                    if '/' in sel:
                        # nested: e.g. "preselection;1/selection;1"
                        sub_token, last_token = sel.split('/')
                        sub_base = sub_token.split(';')[0]
                        last_base = last_token.split(';')[0]
                        subkey = [k for k in tdir_obj.keys() if k.split(';')[0] == sub_base][0]
                        tree_key = [k for k in tdir_obj[subkey].keys() if k.split(';')[0] == last_base][0]
                        tree = tdir_obj[subkey][tree_key]
                    else:
                        # direct child under tdir_obj
                        tree_key = [k for k in tdir_obj.keys() if k.split(';')[0] == sel_base][0]
                        tree = tdir_obj[tree_key]
                except Exception as e_open:
                    print("[ERROR] failed to open tree for sample", d, "sel=", sel, "fallback error:", e_open)
                    continue

            # Read needed branches
            arr = tree.arrays([BR_MJJ, BR_SCORE, BR_ISDATA], library="ak")
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MJJ])
            mc = (isdata == 0)

            mjj = ak.to_numpy(arr[BR_MJJ][mc])
            score = ak.to_numpy(arr[BR_SCORE][mc])
            # --- end of replacement block ---

            # ----------------
            # tree = f[f"{topdir}/{sel_path}"]   # or adapt if you use tdir[...] directly
            # # tree = tdir[sel]
            # req = {BR_MJJ, BR_SCORE, BR_ISDATA}
            # if not req.issubset(set(tree.keys())):
            #     continue
            # arr = tree.arrays([BR_MJJ, BR_SCORE, BR_ISDATA], library="ak")
            # isdata = arr[BR_ISDATA]
            # mc = (isdata == 0)
            # mjj = ak.to_numpy(arr[BR_MJJ][mc])
            # score = ak.to_numpy(arr[BR_SCORE][mc])

            if mass not in mass_cat_vals:
                mass_cat_vals[mass] = {c: [] for c in cats}
                mass_dirs[mass] = []
            mass_dirs[mass].append(d)

            for c in cats:
                lo, hi = edges_full[c], edges_full[c+1]
                mask = (score >= lo) & (score < hi)
                vals = mjj[mask]
                if vals.size:
                    mass_cat_vals[mass][c].append(vals)

    if not mass_cat_vals:
        print("[ERROR] no signal masses found or matched by pattern; check directory names or adjust extract_mass_from_dir()")
        return

    print("[INFO] found masses:", sorted(mass_cat_vals.keys()))

    # For each mass, per category run histogram EM fits (1..kmax) and choose best by chi2/ndof
    out = {"edges": edges, "masses": {}}
    bin_edges = np.linspace(args.mjj_min, args.mjj_max, args.bins+1)
    centers = 0.5*(bin_edges[:-1] + bin_edges[1:])
    typical_binw = (args.mjj_max - args.mjj_min)/args.bins

    for mass, catmap in sorted(mass_cat_vals.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        print(f"[INFO] processing mass {mass} ...")
        mass_out = {"used_dirs": mass_dirs.get(mass, []), "fits": {}}
        mass_dir = os.path.join(args.outdir, str(mass))
        os.makedirs(mass_dir, exist_ok=True)

        for c in cats:
            arrs = catmap.get(c, [])
            if not arrs:
                print(f"  [WARN] mass {mass} cat {c}: no arrays")
                continue
            x_all = np.concatenate(arrs)
            if x_all.size > args.max_events:
                # downsample random subset to speed fitting
                idx = np.random.choice(x_all.size, args.max_events, replace=False)
                x = x_all[idx]
            else:
                x = x_all
            x = x[(x >= args.mjj_min) & (x <= args.mjj_max)]
            if x.size == 0:
                print(f"  [WARN] mass {mass} cat {c}: no events in window")
                continue

            counts, _ = np.histogram(x, bins=bin_edges, density=False)
            fits = []; ks=[]; chi2s=[]
            for k in range(1, args.kmax+1):
                p = gmm_em_on_hist(centers, counts, k)
                mu = model_counts(bin_edges, p, n_tot=len(x))
                chi2ndof = chi2_reduced(counts, mu, k)
                fits.append((p, chi2ndof)); ks.append(k); chi2s.append(float(chi2ndof))

            best_params, best_chi2 = min(fits, key=lambda t: t[1])
            best_k = len(best_params["means"])
            mass_out["fits"][str(c)] = {
                "best_params": best_params,
                "chi2_over_ndof": float(best_chi2),
                "scan": {"k": ks, "chi2_over_ndof": chi2s}
            }

            # plot summary for this mass and cat
            fig, ax = plt.subplots(figsize=(7,5))
            yerr = np.sqrt(np.maximum(counts, 1.0))
            ax.errorbar(centers, counts, yerr=yerr, fmt='o', ms=3, lw=1, capsize=2, label=f"mass={mass}, cat={c}")
            xx = np.linspace(args.mjj_min, args.mjj_max, 1200)
            for p, chi2ndof in fits:
                yy = mixture_pdf(xx, p) * typical_binw * len(x)
                ax.plot(xx, yy, lw=1.2, label=f"k={len(p['means'])}, χ2/nd={chi2ndof:.2f}")
            ax.set_xlabel("mjj [GeV]"); ax.set_ylabel("Events")
            ax.set_title(f"Signal mjj — mass {mass} GeV, cat {c}")
            ax.legend(frameon=False); ax.grid(alpha=0.2); fig.tight_layout()
            png = os.path.join(mass_dir, f"sig_mjj_mass{mass}_cat{c}.png")
            fig.savefig(png, dpi=130); plt.close(fig)
            print(f"  [OK] wrote plot {png}")

            # write chi2 scan plot
            scan_png = os.path.join(mass_dir, f"sig_mjj_mass{mass}_cat{c}_chi2scan.png")
            plt.figure(figsize=(6,4)); plt.plot(ks, chi2s, '-o'); plt.axvline(best_k, ls='--'); plt.xlabel('k'); plt.ylabel('chi2/nd'); plt.grid(alpha=0.2)
            plt.tight_layout(); plt.savefig(scan_png, dpi=120); plt.close()
            print(f"  [OK] wrote scan {scan_png}")

        out["masses"][str(mass)] = mass_out
        # write per-mass JSON as well (useful)
        with open(os.path.join(mass_dir, "signal_mjj_params.json"), "w") as f:
            json.dump({"edges": edges, "fits": mass_out["fits"], "used_dirs": mass_out["used_dirs"]}, f, indent=2)
        print(f"[INFO] wrote per-mass JSON: {os.path.join(mass_dir, 'signal_mjj_params.json')}")

    # write full JSON
    out_json = os.path.join(args.outdir, "signal_mjj_params_by_mass.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2)
    print("[DONE] wrote", out_json)

if __name__ == "__main__":
    main()
