# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import argparse, json, os, re
# import numpy as np
# import awkward as ak
# import uproot
# import matplotlib.pyplot as plt

# TREE_NAME  = "selection"
# BR_MJJ     = "dijet_mass"      # <-- change to your exact mjj branch
# BR_SCORE   = "pDNN_score"
# BR_ISDATA  = "isdata"

# # ---------- sample helpers (same as mgg) ----------
# def is_signal_dir(name: str) -> bool:
#     n = name.lower()
#     return (
#         "nmssm" in n or "radion" in n or "graviton" in n or
#         "gluglutohh" in n or re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
#     )

# def collect_dirs(fin):
#     out = []
#     for k in fin.keys():
#         base = k.split(";")[0]
#         if isinstance(fin[k], uproot.reading.ReadOnlyDirectory):
#             out.append(base)
#     return out

# def get_tree_key(tdir, base):
#     for tkey in tdir.keys():
#         if tkey.split(";")[0] == base:
#             return tkey
#     return None

# # ---------- GMM-by-EM (copy of mgg, but wider sigmas) ----------
# def gmm_em_1d(x, k, max_iter=200, tol=1e-6, seed=123):
#     n = x.size
#     means  = np.quantile(x, np.linspace(0.2, 0.8, k))
#     sigmas = np.full(k, 5.0)  # mjj is wider than mgg
#     weights= np.full(k, 1.0/k)

#     prev_ll = -np.inf
#     x2 = x[:, None]

#     for _ in range(max_iter):
#         pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
#         num  = weights * pdfs
#         den  = np.sum(num, axis=1, keepdims=True) + 1e-300
#         r    = num / den

#         Nk = r.sum(axis=0) + 1e-300
#         weights = Nk / n
#         means   = (r * x2).sum(axis=0) / Nk
#         var     = (r * (x2 - means)**2).sum(axis=0) / Nk
#         sigmas  = np.sqrt(np.clip(var, 1e-6, None))

#         pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
#         ll   = np.sum(np.log(pdfs @ weights + 1e-300))
#         if abs(ll - prev_ll) < tol * (1.0 + abs(prev_ll)):
#             break
#         prev_ll = ll

#     params = {
#         "weights": weights.tolist(),
#         "means":   means.tolist(),
#         "sigmas":  sigmas.tolist(),
#         "logL":    float(prev_ll),
#     }
#     p = 3*k - 1
#     params["bic"] = float(-2.0*prev_ll + p*np.log(n))
#     return params

# def mixture_pdf(x, params):
#     w = np.array(params["weights"])
#     m = np.array(params["means"])
#     s = np.array(params["sigmas"])
#     x2 = x[:, None]
#     pdfs = (1.0/np.sqrt(2*np.pi)/s) * np.exp(-0.5*((x2 - m)**2)/(s**2))
#     return (pdfs * w).sum(axis=1)

# def model_counts(bin_edges, params, n_tot_in_window):
#     centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
#     binw    = np.diff(bin_edges)
#     dens    = mixture_pdf(centers, params)
#     return dens * binw * n_tot_in_window

# def chi2_reduced(counts, mu, k):
#     var  = np.maximum(counts, 1.0)
#     chi2 = np.sum((counts - mu)**2 / var)
#     p    = 3*k - 1
#     ndof = max(len(counts) - p, 1)
#     return chi2 / ndof

# def plot_k_scan(ks, chi2s, best_k, out_path):
#     fig, ax = plt.subplots(figsize=(6,4.2))
#     ax.plot(ks, chi2s, '-o', lw=1.5)
#     ax.axvline(best_k, ls='--', color='k', alpha=0.5)
#     ax.text(0.05, 0.85, rf"Optimum $N_{{gauss}}$ = {best_k}",
#             transform=ax.transAxes)
#     ax.set_xlabel(r"$N_{\mathrm{gauss}}$")
#     ax.set_ylabel(r"$\chi^2/\mathrm{ndof}$")
#     ax.set_xticks(ks)
#     ax.grid(alpha=0.2)
#     fig.tight_layout()
#     fig.savefig(out_path, dpi=150)
#     plt.close(fig)

# # ---------- main ----------
# def main():
#     ap = argparse.ArgumentParser(description="Fit signal mjj shapes per category (GMM, χ² selection).")
#     ap.add_argument("--root", required=True,
#                     help="merged ROOT file (same one you used for mgg)")
#     ap.add_argument("--edges-json", default=None,
#                     help="JSON with {'boundaries': {'combined': [e0,e1,...]}}")
#     ap.add_argument("--edges", type=float, nargs="*", default=None,
#                     help="pDNN thresholds, e.g. --edges 0.80 0.86")
#     ap.add_argument("--cats", type=int, nargs="*", default=None,
#                     help="which cat indices to fit (default: all)")
#     ap.add_argument("--mjj-min", type=float, default=50.0)
#     ap.add_argument("--mjj-max", type=float, default=180.0)
#     ap.add_argument("--bins", type=int, default=120)
#     ap.add_argument("--kmax", type=int, default=5)
#     ap.add_argument("--outdir", default="outputs/signal_fits_mjj")
#     ap.add_argument("--only-signal", default=None,
#                     help="if set, only process signal dirs whose name CONTAINS this substring")
#     args = ap.parse_args()

#     os.makedirs(args.outdir, exist_ok=True)

#     # resolve edges
#     if args.edges is not None and len(args.edges) > 0:
#         edges = sorted(args.edges)
#     elif args.edges_json:
#         with open(args.edges_json) as f:
#             js = json.load(f)
#         edges = sorted(js["boundaries"].get("combined", []))
#     else:
#         raise RuntimeError("Provide category thresholds with --edges or --edges-json")

#     edges_full = [-np.inf] + edges + [np.inf]
#     n_cats = len(edges_full) - 1

#     if args.cats is None:
#         cats = list(range(n_cats))
#     else:
#         cats = args.cats
#         for c in cats:
#             if c < 0 or c >= n_cats:
#                 raise RuntimeError(f"Requested cat {c}, but only 0..{n_cats-1} exist.")

#     # collect events
#     cat_values = {c: [] for c in cats}
#     used_dirs  = []

#     with uproot.open(args.root) as fin:
#         for d in collect_dirs(fin):
#             if args.only_signal and args.only_signal not in d:
#                 continue
#             if not is_signal_dir(d):
#                 continue

#             tdir = fin[d]
#             sel = get_tree_key(tdir, TREE_NAME)
#             if sel is None:
#                 continue
#             tree = tdir[sel]

#             req = {BR_MJJ, BR_SCORE, BR_ISDATA}
#             if not req.issubset(set(tree.keys())):
#                 continue

#             used_dirs.append(d)

#             arr = tree.arrays([BR_MJJ, BR_SCORE, BR_ISDATA], library="ak")
#             isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MJJ])
#             mc = (isdata == 0)

#             mjj   = np.asarray(arr[BR_MJJ][mc])
#             score = np.asarray(arr[BR_SCORE][mc])

#             for i in cats:
#                 lo = edges_full[i]
#                 hi = edges_full[i+1]
#                 sel_mask = (score >= lo) & (score < hi)
#                 vals = mjj[sel_mask]
#                 if vals.size:
#                     cat_values[i].append(vals)

#     if used_dirs:
#         print("[info] using signal dirs:")
#         for d in used_dirs:
#             print("   ", d)
#     else:
#         print("[warn] no signal dirs used!")
#         return

#     # fit
#     results = {}
#     edges_hist = np.linspace(args.mjj_min, args.mjj_max, args.bins+1)
#     centers    = 0.5*(edges_hist[:-1] + edges_hist[1:])
#     typical_bw = (args.mjj_max - args.mjj_min) / args.bins

#     for c in cats:
#         if not cat_values[c]:
#             print(f"[warn] cat={c}: no signal entries.")
#             continue
#         x = np.concatenate(cat_values[c])
#         in_win = (x >= args.mjj_min) & (x <= args.mjj_max)
#         x_win  = x[in_win]
#         if x_win.size == 0:
#             print(f"[warn] cat={c}: no entries in mjj window.")
#             continue

#         H, _ = np.histogram(x_win, bins=edges_hist, density=False)
#         yerr = np.sqrt(np.maximum(H, 1.0))

#         fits = []
#         ks, chi2s = [], []
#         for k in range(1, args.kmax+1):
#             p = gmm_em_1d(x_win, k)
#             mu = model_counts(edges_hist, p, n_tot_in_window=len(x_win))
#             chi2ndof = chi2_reduced(H, mu, k)
#             fits.append((p, chi2ndof))
#             ks.append(k); chi2s.append(float(chi2ndof))

#         best_params, best_chi2 = min(fits, key=lambda t: t[1])
#         best_k = len(best_params["means"])
#         results[c] = {
#             "best_params": best_params,
#             "chi2_over_ndof": float(best_chi2),
#             "scan": {"k": ks, "chi2_over_ndof": chi2s},
#         }

#         # plot
#         fig, ax = plt.subplots(figsize=(7,5))
#         ax.errorbar(centers, H, yerr=yerr,
#                     fmt='o', ms=3, lw=1, capsize=2,
#                     label=f"Signal (cat={c})", zorder=3)

#         xx = np.linspace(args.mjj_min, args.mjj_max, 1200)
#         for p, c2 in fits:
#             k = len(p["means"])
#             yy = mixture_pdf(xx, p) * typical_bw * len(x_win)
#             lbl = rf"$N_{{gaus}}={k}$; $\chi^2/\mathrm{{ndof}}={c2:.3g}$"
#             ax.plot(xx, yy, lw=1.5, label=lbl, zorder=2)

#         ax.set_xlabel(r"$m_{jj}$ [GeV]")
#         ax.set_ylabel("Events")
#         ax.set_title(r"Signal $m_{jj}$")
#         ax.legend(frameon=False)
#         ax.grid(alpha=0.2)
#         fig.tight_layout()
#         out_png = os.path.join(args.outdir, f"sig_mjj_cat{c}.png")
#         fig.savefig(out_png, dpi=150)
#         plt.close(fig)
#         print("Wrote", out_png)

#         out_scan = os.path.join(args.outdir, f"sig_mjj_cat{c}_chi2scan.png")
#         plot_k_scan(ks, chi2s, best_k, out_scan)
#         print("Wrote", out_scan)

#     # save json
#     out_json = os.path.join(args.outdir, "signal_mjj_params.json")
#     with open(out_json, "w") as f:
#         json.dump({"edges": edges, "fits": results, "used_dirs": used_dirs}, f, indent=2)
#     print("Saved", out_json)

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt

TREE_NAME  = "selection"
BR_MJJ     = "dijet_mass"      # <-- change if needed
BR_SCORE   = "pDNN_score"
BR_ISDATA  = "isdata"

# --------------------------------------------------
def is_signal_dir(name: str) -> bool:
    n = name.lower()
    return (
        "nmssm" in n or "radion" in n or "graviton" in n or
        "gluglutohh" in n or re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
    )

def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys()
            if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

# ---------- EM on HISTOGRAM (fast) ----------
def gmm_em_on_hist(xcenters, counts, k, max_iter=200, tol=1e-6):
    """xcenters: (nbins,), counts: (nbins,)"""
    # throw away empty bins to speed up
    mask = counts > 0
    x = xcenters[mask]
    w = counts[mask].astype(float)
    w /= w.sum()  # normalize for stability

    n = x.size
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
        r    = num / den  # (n,k)
        # weight by counts
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

    return {
        "weights": weights.tolist(),
        "means":   means.tolist(),
        "sigmas":  sigmas.tolist(),
        "logL":    float(prev_ll),
    }

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

# --------------------------------------------------
def main():
    ap = argparse.ArgumentParser("fast mjj signal fit (hist-EM)")
    ap.add_argument("--root", required=True)
    ap.add_argument("--edges", type=float, nargs="*", default=None)
    ap.add_argument("--edges-json", default=None)
    ap.add_argument("--cats", type=int, nargs="*", default=None)
    ap.add_argument("--mjj-min", type=float, default=50.0)
    ap.add_argument("--mjj-max", type=float, default=180.0)
    ap.add_argument("--bins", type=int, default=120)
    ap.add_argument("--kmax", type=int, default=3, help="no need >3 for mjj")
    ap.add_argument("--outdir", default="outputs/signal_fits_mjj_fast")
    ap.add_argument("--only-signal", default=None)
    ap.add_argument("--max-events", type=int, default=80000,
                    help="downsample per category to this many events")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # edges
    if args.edges:
        edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            js = json.load(f)
        edges = sorted(js["boundaries"]["combined"])
    else:
        raise RuntimeError("need --edges or --edges-json")

    edges_full = [-np.inf] + edges + [np.inf]
    n_cats = len(edges_full) - 1
    cats = list(range(n_cats)) if args.cats is None else args.cats

    # collect
    cat_vals = {c: [] for c in cats}
    used_dirs = []

    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            if args.only_signal and args.only_signal not in d:
                continue
            if not is_signal_dir(d):
                continue
            tdir = fin[d]
            key  = get_tree_key(tdir, TREE_NAME)
            if key is None:
                continue
            tree = tdir[key]
            req = {BR_MJJ, BR_SCORE, BR_ISDATA}
            if not req.issubset(set(tree.keys())):
                continue

            used_dirs.append(d)
            arr = tree.arrays([BR_MJJ, BR_SCORE, BR_ISDATA], library="ak")
            isdata = arr[BR_ISDATA]
            mc = (isdata == 0)
            mjj   = ak.to_numpy(arr[BR_MJJ][mc])
            score = ak.to_numpy(arr[BR_SCORE][mc])

            for c in cats:
                lo, hi = edges_full[c], edges_full[c+1]
                mask = (score >= lo) & (score < hi)
                vals = mjj[mask]
                if vals.size:
                    cat_vals[c].append(vals)

    # fit
    results = {}
    bin_edges = np.linspace(args.mjj_min, args.mjj_max, args.bins+1)
    centers   = 0.5*(bin_edges[:-1] + bin_edges[1:])

    for c in cats:
        if not cat_vals[c]:
            print(f"[warn] cat {c}: empty")
            continue

        x = np.concatenate(cat_vals[c])
        # optional downsample
        if x.size > args.max_events:
            idx = np.random.choice(x.size, args.max_events, replace=False)
            x = x[idx]

        x = x[(x >= args.mjj_min) & (x <= args.mjj_max)]
        counts, _ = np.histogram(x, bins=bin_edges, density=False)

        fits = []
        ks, chi2s = [], []
        for k in range(1, args.kmax+1):
            p = gmm_em_on_hist(centers, counts, k)
            mu = model_counts(bin_edges, p, len(x))
            chi2ndof = chi2_reduced(counts, mu, k)
            fits.append((p, chi2ndof))
            ks.append(k); chi2s.append(float(chi2ndof))

        best_params, best_chi2 = min(fits, key=lambda t: t[1])
        best_k = len(best_params["means"])
        results[c] = {
            "best_params": best_params,
            "chi2_over_ndof": float(best_chi2),
            "scan": {"k": ks, "chi2_over_ndof": chi2s},
        }

        # quick plot
        fig, ax = plt.subplots(figsize=(7,5))
        yerr = np.sqrt(np.maximum(counts, 1.0))
        ax.errorbar(centers, counts, yerr=yerr, fmt="o", ms=3, lw=1, capsize=2,
                    label=f"Signal (cat={c})")
        xx = np.linspace(args.mjj_min, args.mjj_max, 1200)
        for p, c2 in fits:
            yy = mixture_pdf(xx, p) * (args.mjj_max - args.mjj_min)/args.bins * len(x)
            ax.plot(xx, yy, lw=1.2, label=rf"k={len(p['means'])}, $\chi^2/ndof$={c2:.2f}")
        ax.set_xlabel(r"$m_{jj}$ [GeV]"); ax.set_ylabel("Events")
        ax.set_title(f"Signal mjj, cat {c}")
        ax.legend(frameon=False); ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, f"sig_mjj_cat{c}.png"), dpi=130)
        plt.close(fig)

    with open(os.path.join(args.outdir, "signal_mjj_params.json"), "w") as f:
        json.dump({"edges": edges, "fits": results, "used_dirs": used_dirs}, f, indent=2)
    print("[done] wrote", os.path.join(args.outdir, "signal_mjj_params.json"))

if __name__ == "__main__":
    main()
