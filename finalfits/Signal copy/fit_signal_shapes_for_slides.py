# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import argparse, json, os, re, math
# import numpy as np
# import awkward as ak
# import uproot
# import matplotlib.pyplot as plt

# TREE_NAME  = "selection"
# BR_MGG     = "diphoton_mass"
# BR_SCORE   = "pDNN_score"
# BR_ISDATA  = "isdata"

# # --------- sample helpers ---------
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

# # --------- simple GMM via EM (1D) ---------
# def gmm_em_1d(x, k, max_iter=200, tol=1e-6, seed=123):
#     rng = np.random.default_rng(seed)
#     n = x.size
#     means = np.quantile(x, np.linspace(0.2, 0.8, k))
#     sigmas = np.full(k, 1.5)   # GeV-ish
#     weights = np.full(k, 1.0/k)

#     prev_ll = -np.inf
#     x2 = x[:, None]

#     for _ in range(max_iter):
#         pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
#         num = weights * pdfs
#         den = np.sum(num, axis=1, keepdims=True) + 1e-300
#         r = num / den

#         Nk = r.sum(axis=0) + 1e-300
#         weights = Nk / n
#         means = (r * x2).sum(axis=0) / Nk
#         var = (r * (x2 - means)**2).sum(axis=0) / Nk
#         sigmas = np.sqrt(np.clip(var, 1e-6, None))

#         pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
#         ll = np.sum(np.log(pdfs @ weights + 1e-300))
#         if abs(ll - prev_ll) < tol * (1.0 + abs(prev_ll)):
#             break
#         prev_ll = ll

#     params = {"weights": weights.tolist(),
#               "means":   means.tolist(),
#               "sigmas":  sigmas.tolist(),
#               "logL":    float(prev_ll)}
#     p = 3*k - 1  # params for k-Gaussian mixture; weights sum to 1
#     params["bic"] = float(-2.0*prev_ll + p*np.log(n))
#     return params

# def mixture_pdf(x, params):
#     w = np.array(params["weights"])
#     m = np.array(params["means"])
#     s = np.array(params["sigmas"])
#     x2 = x[:, None]
#     pdfs = (1.0/np.sqrt(2*np.pi)/s) * np.exp(-0.5*((x2 - m)**2)/(s**2))
#     return (pdfs * w).sum(axis=1)

# # --------- plotting/fit helpers (counts space) ---------
# def model_counts(bin_edges, params, n_tot_in_window):
#     centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
#     binw    = np.diff(bin_edges)
#     dens    = mixture_pdf(centers, params)          # 1/GeV
#     return dens * binw * n_tot_in_window            # events per bin

# def chi2_reduced(counts, mu, k):
#     var  = np.maximum(counts, 1.0)                  # Poisson approx, protect zeros
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

# # --------- main ---------
# def main():
#     ap = argparse.ArgumentParser(description="Fit signal mgg shapes per category (points+lines, χ² selection).")
#     ap.add_argument("--root", required=True, help="merged ROOT file (per-sample dirs)")
#     ap.add_argument("--edges-json", default=None,
#                     help="JSON with {'boundaries': {'combined': [e0,e1,...]}}")
#     ap.add_argument("--edges", type=float, nargs="*", default=None,
#                     help="Thresholds (e.g. --edges 0.8002 0.8574). Categories become (-inf,e0], [e0,e1), [e1,inf).")
#     ap.add_argument("--cats", type=int, nargs="*", default=None,
#                     help="Which cat indices to fit (default: all implied by edges)")
#     ap.add_argument("--mgg-min", type=float, default=115.0)
#     ap.add_argument("--mgg-max", type=float, default=135.0)
#     ap.add_argument("--bins", type=int, default=40)
#     ap.add_argument("--kmax", type=int, default=3, help="max Gaussians to try")
#     ap.add_argument("--outdir", default="outputs/signal_fits")
#     args = ap.parse_args()

#     os.makedirs(args.outdir, exist_ok=True)

#     # resolve category edges
#     if args.edges is not None and len(args.edges) > 0:
#         edges = sorted(args.edges)
#     elif args.edges_json:
#         with open(args.edges_json) as f:
#             js = json.load(f)
#         edges = sorted(js["boundaries"].get("combined", []))
#     else:
#         raise RuntimeError("Provide category thresholds with --edges or --edges-json")

#     # Include < first edge and ≥ last edge
#     edges_full = [-np.inf] + edges + [np.inf]
#     n_cats = len(edges_full) - 1

#     if args.cats is None:
#         cats = list(range(n_cats))
#     else:
#         cats = args.cats
#         for c in cats:
#             if c < 0 or c >= n_cats:
#                 raise RuntimeError(f"Requested cat {c} but only 0..{n_cats-1} exist for {len(edges)} edges.")

#     # gather unbinned signal mgg per category
#     cat_values = {c: [] for c in cats}

#     with uproot.open(args.root) as fin:
#         for d in collect_dirs(fin):
#             if not is_signal_dir(d):
#                 continue
#             tdir = fin[d]
#             sel = get_tree_key(tdir, TREE_NAME)
#             if sel is None:
#                 continue
#             tree = tdir[sel]
#             req = {BR_MGG, BR_SCORE, BR_ISDATA}
#             if not req.issubset(set(tree.keys())):
#                 continue

#             arr = tree.arrays([BR_MGG, BR_SCORE, BR_ISDATA], library="ak")
#             isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MGG])
#             mc = (isdata == 0)

#             mgg   = ak.to_numpy(arr[BR_MGG][mc])
#             score = ak.to_numpy(arr[BR_SCORE][mc])

#             for i in cats:
#                 lo = edges_full[i]
#                 hi = edges_full[i+1]
#                 sel_mask = (score >= lo) & (score < hi)
#                 vals = mgg[sel_mask]
#                 if vals.size:
#                     cat_values[i].append(vals)

#     # fit & plot
#     results = {}
#     edges_hist = np.linspace(args.mgg_min, args.mgg_max, args.bins+1)
#     centers = 0.5*(edges_hist[:-1] + edges_hist[1:])
#     typical_binw = (args.mgg_max - args.mgg_min) / args.bins

#     for c in cats:
#         if not cat_values[c]:
#             print(f"[warn] cat={c}: no signal entries found.")
#             continue
#         x = np.concatenate(cat_values[c])
#         in_win = (x >= args.mgg_min) & (x <= args.mgg_max)
#         x_win = x[in_win]
#         if x_win.size == 0:
#             print(f"[warn] cat={c}: no entries in plot window.")
#             continue

#         # histogram in counts (events)
#         H, _ = np.histogram(x_win, bins=edges_hist, density=False)
#         yerr = np.sqrt(np.maximum(H, 1.0))

#         # fit k=1..kmax; compute chi2/ndof; choose best
#         fits = []
#         ks, chi2s = [], []
#         for k in range(1, args.kmax+1):
#             p = gmm_em_1d(x, k)
#             mu = model_counts(edges_hist, p, n_tot_in_window=len(x_win))
#             chi2ndof = chi2_reduced(H, mu, k)
#             fits.append((p, chi2ndof))
#             ks.append(k)
#             chi2s.append(float(chi2ndof))

#         best_params, best_chi2ndof = min(fits, key=lambda t: t[1])
#         best_k = len(best_params["means"])
#         results[c] = {
#             "best_params": best_params,
#             "chi2_over_ndof": float(best_chi2ndof),
#             "scan": {"k": ks, "chi2_over_ndof": chi2s},
#         }

#         # main plot (points + model curves)
#         fig, ax = plt.subplots(figsize=(7,5))
#         ax.errorbar(
#             centers, H, yerr=yerr,
#             fmt='o', ms=3, lw=1, capsize=2,
#             label=f"Simulation (cat={c})", zorder=3
#         )

#         xx = np.linspace(args.mgg_min, args.mgg_max, 1200)
#         for p, chi2ndof in fits:
#             k = len(p["means"])
#             yy = mixture_pdf(xx, p) * typical_binw * len(x_win)  # events per "typical" bin
#             lbl = rf"$N_{{gaus}}={k}$; $\chi^2/\mathrm{{ndof}}={chi2ndof:.3g}$"
#             ax.plot(xx, yy, lw=1.5, label=lbl, zorder=2)

#         ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
#         ax.set_ylabel("Events")
#         ax.set_title(rf"Signal $m_{{\gamma\gamma}}$")
#         ax.legend(frameon=False)
#         ax.grid(alpha=0.2)
#         fig.tight_layout()
#         out_png = os.path.join(args.outdir, f"sig_mgg_cat{c}.png")
#         fig.savefig(out_png, dpi=150)
#         plt.close(fig)
#         print("Wrote", out_png)

#         # chi2 scan plot
#         out_scan = os.path.join(args.outdir, f"sig_mgg_cat{c}_chi2scan.png")
#         plot_k_scan(ks, chi2s, best_k, out_scan)
#         print("Wrote", out_scan)

#     # save params
#     out_json = os.path.join(args.outdir, "signal_shape_params.json")
#     with open(out_json, "w") as f:
#         json.dump({"edges": edges, "fits": results}, f, indent=2)
#     print("Saved", out_json)

# if __name__ == "__main__":
#     main()





# #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re, math
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt

TREE_NAME  = "selection"
BR_MGG     = "diphoton_mass"
BR_SCORE   = "pDNN_score"
BR_ISDATA  = "isdata"

# --------- sample helpers ---------
def is_signal_dir(name: str) -> bool:
    n = name.lower()
    return (
        "nmssm" in n or "radion" in n or "graviton" in n or
        "gluglutohh" in n or re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
    )

def collect_dirs(fin):
    out = []
    for k in fin.keys():
        base = k.split(";")[0]
        if isinstance(fin[k], uproot.reading.ReadOnlyDirectory):
            out.append(base)
    return out

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

# --------- simple GMM via EM (1D) ---------
def gmm_em_1d(x, k, max_iter=200, tol=1e-6, seed=123):
    rng = np.random.default_rng(seed)
    n = x.size
    # init means by quantiles
    means = np.quantile(x, np.linspace(0.2, 0.8, k))
    sigmas = np.full(k, 1.5)  # GeV-ish
    weights = np.full(k, 1.0/k)

    prev_ll = -np.inf
    x2 = x[:, None]

    for _ in range(max_iter):
        # E-step: responsibilities
        pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
        num = weights * pdfs
        den = np.sum(num, axis=1, keepdims=True) + 1e-300
        r = num / den

        # M-step
        Nk = r.sum(axis=0) + 1e-300
        weights = Nk / n
        means = (r * x2).sum(axis=0) / Nk
        var = (r * (x2 - means)**2).sum(axis=0) / Nk
        sigmas = np.sqrt(np.clip(var, 1e-6, None))

        # log-likelihood
        pdfs = (1.0/np.sqrt(2*np.pi)/sigmas) * np.exp(-0.5*((x2 - means)**2)/(sigmas**2))
        ll = np.sum(np.log(pdfs @ weights + 1e-300))
        if abs(ll - prev_ll) < tol * (1.0 + abs(prev_ll)):
            break
        prev_ll = ll

    params = {"weights": weights.tolist(),
              "means":   means.tolist(),
              "sigmas":  sigmas.tolist(),
              "logL":    float(prev_ll)}
    # BIC kept for reference
    p = 3*k - 1
    params["bic"] = float(-2.0*prev_ll + p*np.log(n))
    return params

def mixture_pdf(x, params):
    w = np.array(params["weights"])
    m = np.array(params["means"])
    s = np.array(params["sigmas"])
    x2 = x[:, None]
    pdfs = (1.0/np.sqrt(2*np.pi)/s) * np.exp(-0.5*((x2 - m)**2)/(s**2))
    return (pdfs * w).sum(axis=1)

# --------- plotting/fit helpers (counts space) ---------
def model_counts(bin_edges, params, n_tot_in_window):
    """Expected counts per bin from a PDF mixture."""
    centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    binw    = np.diff(bin_edges)
    dens    = mixture_pdf(centers, params)          # 1/GeV
    return dens * binw * n_tot_in_window            # events per bin

def chi2_reduced(counts, mu, k):
    """Compute χ²/ndof using Poisson variance ~ N; protect zeros."""
    var  = np.maximum(counts, 1.0)
    chi2 = np.sum((counts - mu)**2 / var)
    p    = 3*k - 1                                  # params for k-Gaussian mixture
    ndof = max(len(counts) - p, 1)
    return chi2 / ndof

def plot_k_scan(ks, chi2s, best_k, out_path):
    fig, ax = plt.subplots(figsize=(6,4.2))
    ax.plot(ks, chi2s, '-o', lw=1.5)
    ax.axvline(best_k, ls='--', color='k', alpha=0.5)
    ax.text(0.05, 0.85, rf"Optimum $N_{{gauss}}$ = {best_k}",
            transform=ax.transAxes)
    ax.set_xlabel(r"$N_{\mathrm{gauss}}$")
    ax.set_ylabel(r"$\chi^2/\mathrm{ndof}$")
    ax.set_xticks(ks)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

# --------- main ---------
def main():
    ap = argparse.ArgumentParser(description="Fit signal mgg shapes per category (points+lines, χ² selection).")
    ap.add_argument("--root", required=True, help="merged ROOT file (per-sample dirs)")
    ap.add_argument("--edges-json", default=None,
                    help="JSON with {'boundaries': {'combined': [e0,e1,...]}}")
    ap.add_argument("--edges", type=float, nargs="*", default=None,
                    help="Thresholds (e.g. --edges 0.8002 0.8574). Categories become (-inf,e0], [e0,e1), [e1,inf).")
    ap.add_argument("--cats", type=int, nargs="*", default=None,
                    help="Which cat indices to fit (default: all implied by edges)")
    ap.add_argument("--mgg-min", type=float, default=115.0)
    ap.add_argument("--mgg-max", type=float, default=135.0)
    ap.add_argument("--bins", type=int, default=40)
    ap.add_argument("--kmax", type=int, default=3, help="max Gaussians to try")
    ap.add_argument("--outdir", default="outputfiles/signal_fits")
    ap.add_argument("--only-signal", default=None,
                    help="If set, only process directories whose names CONTAIN this substring (e.g. nmssm_X400_Y125).")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # resolve category edges
    if args.edges is not None and len(args.edges) > 0:
        edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            js = json.load(f)
        edges = sorted(js["boundaries"].get("combined", []))
    else:
        raise RuntimeError("Provide category thresholds with --edges or --edges-json")

    # Include < first edge and ≥ last edge
    edges_full = [-np.inf] + edges + [np.inf]
    n_cats = len(edges_full) - 1

    if args.cats is None:
        cats = list(range(n_cats))
    else:
        cats = args.cats
        for c in cats:
            if c < 0 or c >= n_cats:
                raise RuntimeError(f"Requested cat {c} but only 0..{n_cats-1} exist for {len(edges)} edges.")

    # gather unbinned signal mgg per category
    cat_values = {c: [] for c in cats}
    used_dirs = []

    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            if args.only_signal and args.only_signal not in d:
                continue
            if not is_signal_dir(d):
                continue

            tdir = fin[d]
            sel = get_tree_key(tdir, TREE_NAME)
            if sel is None:
                continue
            tree = tdir[sel]
            req = {BR_MGG, BR_SCORE, BR_ISDATA}
            if not req.issubset(set(tree.keys())):
                continue

            used_dirs.append(d)
            arr = tree.arrays([BR_MGG, BR_SCORE, BR_ISDATA], library="ak")
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MGG])
            mc = (isdata == 0)

            mgg   = ak.to_numpy(arr[BR_MGG][mc])
            score = ak.to_numpy(arr[BR_SCORE][mc])

            for i in cats:
                lo = edges_full[i]
                hi = edges_full[i+1]
                sel_mask = (score >= lo) & (score < hi)
                vals = mgg[sel_mask]
                if vals.size:
                    cat_values[i].append(vals)

    if used_dirs:
        print("[info] Using the following signal directories:")
        for d in used_dirs:
            print("   [signal]", d)
    else:
        print("[warn] No matching signal directories found with current filters.")
        return

    # fit & plot
    results = {}
    edges_hist = np.linspace(args.mgg_min, args.mgg_max, args.bins+1)
    centers = 0.5*(edges_hist[:-1] + edges_hist[1:])
    typical_binw = (args.mgg_max - args.mgg_min) / args.bins

    for c in cats:
        if not cat_values[c]:
            print(f"[warn] cat={c}: no signal entries found.")
            continue
        x = np.concatenate(cat_values[c])
        in_win = (x >= args.mgg_min) & (x <= args.mgg_max)
        x_win = x[in_win]
        if x_win.size == 0:
            print(f"[warn] cat={c}: no entries in plot window.")
            continue

        # histogram in counts (events)
        H, _ = np.histogram(x_win, bins=edges_hist, density=False)
        yerr = np.sqrt(np.maximum(H, 1.0))

        # fit k=1..kmax; compute chi2/ndof; choose best
        fits = []
        ks, chi2s = [], []
        for k in range(1, args.kmax+1):
            p = gmm_em_1d(x, k)
            mu = model_counts(edges_hist, p, n_tot_in_window=len(x_win))
            chi2ndof = chi2_reduced(H, mu, k)
            fits.append((p, chi2ndof))
            ks.append(k)
            chi2s.append(float(chi2ndof))

        best_params, best_chi2ndof = min(fits, key=lambda t: t[1])
        best_k = len(best_params["means"])
        results[c] = {
            "best_params": best_params,
            "chi2_over_ndof": float(best_chi2ndof),
            "scan": {"k": ks, "chi2_over_ndof": chi2s},
        }

        # main plot (points + model curves)
        fig, ax = plt.subplots(figsize=(7,5))
        ax.errorbar(
            centers, H, yerr=yerr,
            fmt='o', ms=3, lw=1, capsize=2,
            label=f"Simulation (cat={c})", zorder=3
        )

        xx = np.linspace(args.mgg_min, args.mgg_max, 1200)
        for p, chi2ndof in fits:
            k = len(p["means"])
            yy = mixture_pdf(xx, p) * typical_binw * len(x_win)  # events per "typical" bin
            lbl = rf"$N_{{gaus}}={k}$; $\chi^2/\mathrm{{ndof}}={chi2ndof:.3g}$"
            ax.plot(xx, yy, lw=1.5, label=lbl, zorder=2)

        ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
        ax.set_ylabel("Events")
        ax.set_title(rf"Signal $m_{{\gamma\gamma}}$")
        ax.legend(frameon=False)
        ax.grid(alpha=0.2)
        fig.tight_layout()
        out_png = os.path.join(args.outdir, f"sig_mgg_cat{c}.png")
        fig.savefig(out_png, dpi=150)
        plt.close(fig)
        print("Wrote", out_png)

        # chi2 scan plot
        out_scan = os.path.join(args.outdir, f"sig_mgg_cat{c}_chi2scan.png")
        plot_k_scan(ks, chi2s, best_k, out_scan)
        print("Wrote", out_scan)

    # save params
    out_json = os.path.join(args.outdir, "signal_shape_params.json")
    with open(out_json, "w") as f:
        json.dump({"edges": edges, "fits": results, "used_dirs": used_dirs}, f, indent=2)
    print("Saved", out_json)

if __name__ == "__main__":
    main()
