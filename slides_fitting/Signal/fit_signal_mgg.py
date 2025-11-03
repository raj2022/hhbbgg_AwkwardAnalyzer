#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, argparse
import numpy as np
import uproot, awkward as ak
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# -----------------------------------
# Config / branches
# -----------------------------------
TREE_NAME  = "selection"
BR_MGG     = "diphoton_mass"
BR_CAT     = "cat"
BR_REGION  = "region"            # not strictly needed for signal fits, but kept for flexibility
BR_WEIGHT  = "weight_selection"

# -----------------------------------
# Which directories are "signal"?
# -----------------------------------
_SIG_KEYS = ("nmssm", "radion", "graviton", "gluglutohh")  # add more if needed

def is_signal_dir(name: str) -> bool:
    n = name.lower()
    if any(k in n for k in _SIG_KEYS):
        return True
    # also accept bare "mX###_mY###" or "mx###_my###"
    if re.search(r"m[x_]\d+\s*[_]\s*m[y_]\d+", n):
        return True
    return False

def collect_dirs(fin):
    out = []
    for k in fin.keys():
        base = k.split(";")[0]
        obj  = fin[k]
        if isinstance(obj, uproot.reading.ReadOnlyDirectory):
            out.append(base)
    return out

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

# -----------------------------------
# Models: sums of Gaussians
# -----------------------------------
def gauss(x, mu, sigma):
    return np.exp(-0.5*((x - mu)/np.maximum(sigma,1e-6))**2) / (np.maximum(sigma,1e-6)*np.sqrt(2*np.pi))

def make_sum_of_gaussians(n):
    """
    Returns a function f(x, *theta) that is a sum of n Gaussians with:
      - n means (mu_i),
      - n widths (sigma_i > 0),
      - n-1 independent fractions (last is 1 - sum others),
    and an overall normalization A.
    Parameter order: [A, mu1..mun, sigma1..sigman, f1..f_{n-1}]
    Fractions are constrained inside the function.
    """
    def model(x, *theta):
        A = theta[0]
        mu = np.array(theta[1:1+n])
        sg = np.array(theta[1+n:1+2*n])
        if n == 1:
            frac = np.array([1.0])
        else:
            raw = np.array(theta[1+2*n:1+2*n+(n-1)])
            # squash to (0,1) and renormalize
            ftmp = 1/(1+np.exp(-raw))
            # cap sum to <1
            s = np.sum(ftmp)
            if s >= 1.0:
                ftmp = ftmp/(s+1e-6)*0.999
            frac = np.concatenate([ftmp, [1.0-np.sum(ftmp)]])
        y = np.zeros_like(x, dtype=float)
        for i in range(n):
            y += frac[i]*gauss(x, mu[i], np.abs(sg[i]))
        return A*np.maximum(y, 0.0)
    return model

def chi2_ndof(y_obs, y_exp, yerr, npar):
    mask = (yerr > 0)
    num  = np.sum(((y_obs[mask]-y_exp[mask])/yerr[mask])**2)
    ndof = max(1, np.sum(mask) - npar)
    return num/ndof

# -----------------------------------
# Main
# -----------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Fit signal m_gg shapes per category with sums of Gaussians; choose N by chi2/ndof."
    )
    ap.add_argument("--root", required=True, help="categorized ROOT (has cat, region, weight)")
    ap.add_argument("--outdir", default="outputs/signal_fits")
    ap.add_argument("--cats", type=int, nargs="*", default=[0,1,2], help="categories to fit")
    ap.add_argument("--mgg-min", type=float, default=115.0)
    ap.add_argument("--mgg-max", type=float, default=140.0)
    ap.add_argument("--bins", type=int, default=50)
    ap.add_argument("--max-gauss", type=int, default=5, choices=[1,2,3,4,5])
    ap.add_argument("--use-weights", action="store_true", help="use weight_selection for histogram weights")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # binning & centers
    edges   = np.linspace(args.mgg_min, args.mgg_max, args.bins+1)
    centers = 0.5*(edges[:-1]+edges[1:])
    width   = edges[1]-edges[0]

    # open file, get signal dirs
    with uproot.open(args.root) as fin:
        dirs = [d for d in collect_dirs(fin) if is_signal_dir(d)]
        if not dirs:
            raise SystemExit("No signal-like directories found in the ROOT file.")

        # book JSON results
        results = {}

        for dname in dirs:
            tdir = fin[dname]
            tkey = get_tree_key(tdir, TREE_NAME)
            if tkey is None:
                print(f"[skip] {dname}: no '{TREE_NAME}' tree.")
                continue
            tree = tdir[tkey]
            fields = set(tree.keys())
            if not {BR_MGG, BR_CAT}.issubset(fields):
                print(f"[skip] {dname}: required branches missing.")
                continue
            branches = [BR_MGG, BR_CAT]
            if args.use_weights and (BR_WEIGHT in fields):
                branches.append(BR_WEIGHT)
            arr = tree.arrays(branches, library="ak")

            mgg = ak.to_numpy(arr[BR_MGG])
            cat = ak.to_numpy(arr[BR_CAT])
            w   = ak.to_numpy(arr[BR_WEIGHT]) if (args.use_weights and BR_WEIGHT in arr.fields) else np.ones_like(mgg)

            # restrict to fit window
            in_win = (mgg >= args.mgg_min) & (mgg < args.mgg_max)
            mgg = mgg[in_win]; cat = cat[in_win]; w = w[in_win]

            # per category
            for c in args.cats:
                cat_sel = (cat == c)
                if not np.any(cat_sel):
                    print(f"[{dname}] cat={c}: no entries in window.")
                    continue

                xvals = mgg[cat_sel]
                wvals = w[cat_sel]

                # histogram (normalized to unity for shape fit)
                H, _ = np.histogram(xvals, bins=edges, weights=wvals)
                H = H.astype(float)
                Hint = np.sum(H)
                if Hint <= 0:
                    print(f"[{dname}] cat={c}: empty histogram.")
                    continue
                Hnorm = H / (Hint*width)  # convert to a density (pdf-like)
                yerr  = np.sqrt(np.maximum(H,1.0)) / (Hint*width)  # Poisson error propagated to density

                # Try N = 1..max
                trial_info = []
                for n in range(1, args.max_gauss+1):
                    f = make_sum_of_gaussians(n)

                    # initial guesses
                    A0 = np.max(Hnorm)
                    mu0 = np.linspace(124.5, 125.5, n)
                    sg0 = np.full(n, 1.2)
                    if n == 1:
                        p0 = [A0] + list(mu0) + list(sg0)
                    else:
                        fr0 = [0.9] + [0.1/(n-1)]*(n-1)   # will get squashed internally; still helpful
                        # map fractions to inverse-sigmoid space
                        raw = [np.log(f/(1-f)) for f in fr0[:-1]]
                        p0 = [A0] + list(mu0) + list(sg0) + raw

                    try:
                        popt, pcov = curve_fit(
                            f, centers, Hnorm, p0=p0, sigma=np.maximum(yerr, 1e-9),
                            absolute_sigma=True, maxfev=10000
                        )
                        yfit = f(centers, *popt)
                        npar = len(popt)
                        chi2 = chi2_ndof(Hnorm, yfit, np.maximum(yerr, 1e-9), npar)
                        trial_info.append((n, popt, yfit, chi2))
                    except Exception as e:
                        # fitting failed; skip this N
                        continue

                if not trial_info:
                    print(f"[{dname}] cat={c}: no successful fits.")
                    continue

                # select best by chi2/ndof
                trial_info.sort(key=lambda z: z[3])
                best_n, best_popt, best_yfit, best_chi2 = trial_info[0]

                # store params
                key = f"{dname}__cat{c}"
                results[key] = {
                    "N_gauss": best_n,
                    "chi2_ndof": float(best_chi2),
                    "params": list(map(float, best_popt)),
                    "param_order": "A, mu1..muN, sigma1..sigmaN, raw_f1..raw_f_{N-1} (fractions are internal, last=1-sum)"
                }

                # make plot with all tested N and highlight best
                fig, ax = plt.subplots(figsize=(7.2,5.4))
                # data points (density)
                ax.errorbar(centers, Hnorm, yerr=yerr, fmt="o", ms=4, lw=1.2, c="k", label="Simulation (density)")

                # draw all fits (light), and the best (bold)
                cmap = plt.get_cmap("tab10")
                for i,(n,popt,yfit,chi2v) in enumerate(trial_info):
                    ls = "-" if n==best_n else "--"
                    lw = 2.5 if n==best_n else 1.2
                    lab = fr"N$_{{gauss}}$={n}: $\chi^2$/ndof={chi2v:.3g}"
                    ax.plot(centers, yfit, ls=ls, lw=lw, color=cmap(i%10), label=lab, zorder=(5 if n==best_n else 2))

                ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
                ax.set_ylabel("Events / (bin·area)  (unit normalized)")
                ax.set_title(f"{dname} — cat={c}")
                ax.set_xlim(args.mgg_min, args.mgg_max)
                ax.grid(alpha=0.25)
                ax.legend(fontsize=9, frameon=False)
                fig.tight_layout()

                out_png = os.path.join(args.outdir, f"sigfit__{dname.replace('/','_')}__cat{c}.png")
                fig.savefig(out_png, dpi=160)
                plt.close(fig)
                print(f"[ok] Wrote {out_png}  (best N={best_n}, chi2/ndof={best_chi2:.3g})")

        # write JSON summary
        out_json = os.path.join(args.outdir, "signal_shape_params.json")
        with open(out_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[ok] Wrote {out_json}")

if __name__ == "__main__":
    main()



#python fit_signal_mgg.py \
#   --root outputs/categories_alpha/hhbbgg_analyzer-v2-trees__categorized.root \
#   --cats 0 1 2 \
#   --mgg-min 115 --mgg-max 140 --bins 50 \
#   --max-gauss 5 \
#   --use-weights \
#   --outdir outputs/signal_fits
