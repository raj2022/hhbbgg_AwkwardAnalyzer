#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# -------------------- branches --------------------
TREE_NAME   = "selection"
BR_SCORE    = "pDNN_score"
BR_ISDATA   = "isdata"

# -------------------- directory grouping --------------------
def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys()
            if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base: return tkey
    return None

def group_of(name: str):
    n = name.lower()
    if "tth" in n: return "ttH"
    if "ggh" in n or "vbfh" in n or re.search(r"\bvbf\b", n): return "ggH+VBFH"
    if re.search(r"\bwh\b", n) or re.search(r"\bzh\b", n) or "vh" in n: return "VH"
    return None

# -------------------- utilities --------------------
def hist_weighted(x, w, bins):
    H, _  = np.histogram(x, bins=bins, weights=w)
    H2, _ = np.histogram(x, bins=bins, weights=w*w)
    err   = np.sqrt(np.maximum(H2, 1e-12))
    return H, err

def chi2_reduced(y, mu, npar):
    var = np.maximum(y, 1.0)
    chi2 = np.sum((y - mu)**2 / var)
    ndof = max(len(y) - npar, 1)
    return chi2, chi2/ndof

def centers_from_edges(edges):
    return 0.5*(edges[:-1] + edges[1:])

# -------------------- DCB (for ttH, VH) --------------------
def dcb_density(x, mu, sigma, alphaL, nL, alphaR, nR):
    x = np.asarray(x)
    t  = (x - mu) / sigma
    aL, aR = abs(alphaL), abs(alphaR)
    core   = np.exp(-0.5 * t * t)

    mL = t < -aL
    AL = (nL/aL)**nL * np.exp(-0.5*aL*aL)
    BL = nL/aL - aL
    baseL = np.maximum(BL - t[mL], 1e-12)
    left = np.zeros_like(t); left[mL] = AL * baseL**(-nL)

    mR = t > aR
    AR = (nR/aR)**nR * np.exp(-0.5*aR*aR)
    BR = nR/aR - aR
    baseR = np.maximum(BR + t[mR], 1e-12)
    right = np.zeros_like(t); right[mR] = AR * baseR**(-nR)

    out = core
    out[mL] = left[mL]
    out[mR] = right[mR]
    return out

def dcb_counts_per_bin(bin_edges, N, mu, sigma, aL, nL, aR, nR, oversample=25):
    edges = np.asarray(bin_edges)
    out = np.zeros(len(edges)-1)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        xx = np.linspace(lo, hi, oversample, endpoint=False) + (hi-lo)/(2*oversample)
        dens = dcb_density(xx, mu, sigma, aL, nL, aR, nR)
        out[i] = N * dens.mean() * (hi - lo)
    return out

def fit_dcb_binned(bin_edges, counts, seed_mu=None):
    y = counts.astype(float)
    total = float(y.sum())
    if total <= 0: raise RuntimeError("Empty histogram")

    ctr = centers_from_edges(bin_edges)
    mu0 = seed_mu if seed_mu is not None else ctr[np.argmax(y)]
    sigma0 = max(5.0, (bin_edges[-1]-bin_edges[0])/40.0)  # rough start
    p0 = [total, mu0, sigma0, 1.5, 3.0, 1.5, 3.0]

    def model_dummy(x_dummy, N, mu, sigma, aL, nL, aR, nR):
        return dcb_counts_per_bin(bin_edges, N, mu, sigma, aL, nL, aR, nR, oversample=35)

    popt, _ = curve_fit(
        model_dummy, ctr, y, p0=p0,
        bounds=([0.0, bin_edges[0], 1.0, 0.2, 1.01, 0.2, 1.01],
                [1e12, bin_edges[-1], (bin_edges[-1]-bin_edges[0])/2.0, 10.0, 50.0, 10.0, 50.0]),
        maxfev=30000
    )
    mu_model = model_dummy(None, *popt)
    chi2, chi2ndof = chi2_reduced(y, mu_model, npar=7)
    N, mu, sig, aL, nL, aR, nR = popt
    return {
        "name": "DCB",
        "N": float(N), "mu": float(mu), "sigma": float(sig),
        "alphaL": float(aL), "nL": float(nL), "alphaR": float(aR), "nR": float(nR),
        "chi2": float(chi2), "chi2_over_ndof": float(chi2ndof), "npar": 7
    }, mu_model

# -------------------- Envelope models (ggH+VBFH, for mjj) --------------------
# 1) Pure exponential: f(x) ~ exp(lam x)
def expo_counts_per_bin(edges, N, lam):
    out = np.zeros(len(edges)-1)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        if abs(lam) < 1e-10:
            out[i] = N * (hi - lo) / (edges[-1] - edges[0])
        else:
            out[i] = N * (np.exp(lam*hi) - np.exp(lam*lo)) / (lam*(np.exp(lam*edges[-1]) - np.exp(lam*edges[0])))
    # renormalize to exactly N
    out *= (N / out.sum()) if out.sum() > 0 else 0.0
    return out

# 2) First-order non-negative polynomial via Bernstein(1) on [lo,hi]
def bern1_counts_per_bin(edges, N, c0_sq, c1_sq):
    lo, hi = edges[0], edges[-1]
    c0, c1 = c0_sq**2, c1_sq**2  # ensure non-negative coefficients
    out = np.zeros(len(edges)-1)
    for i in range(len(out)):
        a, b = edges[i], edges[i+1]
        z = np.linspace(a, b, 25, endpoint=False) + (b-a)/50.0
        zz = (z - lo)/(hi - lo)
        dens = c0*(1-zz) + c1*zz
        out[i] = dens.mean()*(b-a)
    out *= (N / out.sum()) if out.sum() > 0 else 0.0
    return out

# 3) Exponential + Gaussian "peaking"
def exp_plus_gauss_counts_per_bin(edges, N, lam, w_peak, mu, sigma):
    w = 1.0/(1.0 + np.exp(-w_peak))  # logistic to keep in (0,1)
    out = np.zeros(len(edges)-1)
    tot = 0.0
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        zz = np.linspace(lo, hi, 35, endpoint=False) + (hi-lo)/70.0
        exp_d = np.exp(lam*zz)
        gaus  = np.exp(-0.5*((zz-mu)/sigma)**2)/(sigma*np.sqrt(2*np.pi))
        dens = (1.0-w)*exp_d + w*gaus
        out[i] = dens.mean()*(hi-lo)
        tot += out[i]
    out *= (N / tot) if tot > 0 else 0.0
    return out

def fit_envelope(edges, counts, which="ggH+VBFH"):
    """Try expo, bern1, and exp+gauss; choose by (chi2/2 + 0.5*dof)."""
    y = counts.astype(float)
    Ntot = float(y.sum())
    ctr = centers_from_edges(edges)

    candidates = []

    # Expo
    def model_expo(_x, N, lam):
        return expo_counts_per_bin(edges, N, lam)
    try:
        p0 = [Ntot, -0.005]  # gentle falling
        popt, _ = curve_fit(lambda x, N, lam: model_expo(None, N, lam), ctr, y, p0=p0, maxfev=20000)
        mu = model_expo(None, *popt)
        chi2, chi2ndof = chi2_reduced(y, mu, npar=2)
        score = 0.5*chi2 + 0.5*2   # NLL≈chi2/2 + 0.5*dof
        candidates.append(("expo", {"N":float(popt[0]), "lam":float(popt[1]),
                                    "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof),
                                    "npar":2, "score":float(score)}, mu))
    except Exception:
        pass

    # Bern(1)
    def model_bern(_x, N, c0s, c1s):
        return bern1_counts_per_bin(edges, N, c0s, c1s)
    try:
        popt, _ = curve_fit(lambda x, N, c0s, c1s: model_bern(None, N, c0s, c1s),
                            ctr, y, p0=[Ntot, 1.0, 0.8], maxfev=25000)
        mu = model_bern(None, *popt)
        chi2, chi2ndof = chi2_reduced(y, mu, npar=3)
        score = 0.5*chi2 + 0.5*3
        candidates.append(("bern1", {"N":float(popt[0]), "c0_sq":float(popt[1]),
                                     "c1_sq":float(popt[2]), "chi2":float(chi2),
                                     "chi2_over_ndof":float(chi2ndof),
                                     "npar":3, "score":float(score)}, mu))
    except Exception:
        pass

    # Exp + Gaussian
    def model_mix(_x, N, lam, wpk, mu, sig):
        return exp_plus_gauss_counts_per_bin(edges, N, lam, wpk, mu, sig)
    try:
        mid = 0.5*(edges[0]+edges[-1])
        p0 = [Ntot, -0.005, 0.0, mid, (edges[-1]-edges[0])/20.0]
        bounds = ([0.0, -1.0, -6.0, edges[0],  5.0],
                  [1e12,  1.0,  6.0, edges[-1], (edges[-1]-edges[0])/2.0])
        popt, _ = curve_fit(lambda x, N, lam, w, m, s: model_mix(None, N, lam, w, m, s),
                            ctr, y, p0=p0, bounds=bounds, maxfev=40000)
        mu = model_mix(None, *popt)
        chi2, chi2ndof = chi2_reduced(y, mu, npar=5)
        score = 0.5*chi2 + 0.5*5
        candidates.append(("exp_plus_gauss", {
            "N":float(popt[0]), "lam":float(popt[1]), "w_logit":float(popt[2]),
            "mu":float(popt[3]), "sigma":float(popt[4]),
            "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof),
            "npar":5, "score":float(score)}, mu))
    except Exception:
        pass

    if not candidates:
        raise RuntimeError("Envelope fit failed for ggH+VBFH.")
    # choose the model with minimum penalized score
    best = min(candidates, key=lambda t: t[1]["score"])
    name, pars, mu = best
    pars["name"] = name
    return pars, mu, candidates

# -------------------- main --------------------
def main():
    ap = argparse.ArgumentParser(description="Fit mjj per category: ttH/VH with DCB; ggH+VBFH with PDF envelope.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--edges-json")
    ap.add_argument("--edges", type=float, nargs="*")
    ap.add_argument("--cats", type=int, nargs="*")
    ap.add_argument("--mjj-branch", default="dijet_mass", help="Branch name for m_jj")
    ap.add_argument("--wgt-branch", default="weight", help="Weight branch ('' for unit weights)")
    ap.add_argument("--mjj-min", type=float, default=60.0)
    ap.add_argument("--mjj-max", type=float, default=200.0)
    ap.add_argument("--bins", type=int, default=45)
    ap.add_argument("--outdir", default="outputfiles/res_bkg_mjj_fits")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # resolve category edges
    if args.edges:
        edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            edges = sorted(json.load(f)["boundaries"]["combined"])
    else:
        raise SystemExit("Provide --edges or --edges-json")

    edges_full = [-np.inf] + edges + [np.inf]
    cats = list(range(len(edges_full)-1)) if args.cats is None else args.cats

    bin_edges = np.linspace(args.mjj_min, args.mjj_max, args.bins+1)
    ctr = centers_from_edges(bin_edges)

    # accumulators per group×cat
    grouped = {g:{c:[] for c in cats} for g in ["ttH","ggH+VBFH","VH"]}
    used_dirs = []

    # read
    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            grp = group_of(d)
            if grp is None: continue
            tdir = fin[d]
            sel = get_tree_key(tdir, TREE_NAME)
            if sel is None: continue
            tree = tdir[sel]

            needed = {args.mjj_branch, BR_SCORE, BR_ISDATA}
            if args.wgt_branch: needed.add(args.wgt_branch)
            if not needed.issubset(set(tree.keys())):
                continue

            arr = tree.arrays(list(needed), library="ak")
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[args.mjj_branch])
            mc = (isdata == 0)

            mjj   = ak.to_numpy(arr[args.mjj_branch][mc])
            score = ak.to_numpy(arr[BR_SCORE][mc])
            w     = ak.to_numpy(arr[args.wgt_branch][mc]) if args.wgt_branch and args.wgt_branch in arr.fields else np.ones_like(mjj)

            # cats/windows
            win = (mjj >= args.mjj_min) & (mjj <= args.mjj_max)
            mjj, score, w = mjj[win], score[win], w[win]

            for c in cats:
                lo, hi = edges_full[c], edges_full[c+1]
                m = (score >= lo) & (score < hi)
                if m.any():
                    grouped[grp][c].append((mjj[m], w[m]))

            used_dirs.append(d)

    # fit & plot
    results = {}
    for grp in ["ttH","ggH+VBFH","VH"]:
        results[grp] = {}
        for c in cats:
            if not grouped[grp][c]:
                print(f"[warn] {grp} cat={c}: no mjj entries.")
                continue

            x = np.concatenate([xi for (xi, wi) in grouped[grp][c]])
            w = np.concatenate([wi for (xi, wi) in grouped[grp][c]])

            H, yerr = hist_weighted(x, w, bin_edges)

            if grp in ("ttH","VH"):
                p, mu = fit_dcb_binned(bin_edges, H)
                results[grp][c] = {"model": "DCB", "params": p, "entries": float(H.sum()), "nbins": int(H.size)}
            else:
                p, mu, cand = fit_envelope(bin_edges, H)
                results[grp][c] = {"model": p["name"], "params": p, "entries": float(H.sum()),
                                   "nbins": int(H.size), "tried": cand}

            # ---- plotting (ROOT-ish) ----
            fig, ax = plt.subplots(figsize=(7,5))
            ax.errorbar(ctr, H, yerr=yerr, fmt='^', ms=4, lw=0.8, color='black',
                        ecolor='black', elinewidth=0.8, capsize=0, label="Simulation")
            xx = np.linspace(args.mjj_min, args.mjj_max, 1200)
            # draw the chosen model as smooth curve (bin-normalized for visual)
            bw = (args.mjj_max-args.mjj_min)/args.bins
            if grp in ("ttH","VH"):
                yy = dcb_density(xx, p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"]) * bw * p["N"]
                line_lbl = "Parametric Model (DCB)"
            else:
                if p["name"] == "expo":
                    yy = expo_counts_per_bin(np.linspace(args.mjj_min, args.mjj_max, args.bins+1), p["N"], p["lam"])
                    # interpolate to a smooth curve for looks
                    yy = np.interp(xx, ctr, yy)
                    line_lbl = "Envelope: exp"
                elif p["name"] == "bern1":
                    yy = bern1_counts_per_bin(np.linspace(args.mjj_min, args.mjj_max, args.bins+1), p["N"], p["c0_sq"], p["c1_sq"])
                    yy = np.interp(xx, ctr, yy)
                    line_lbl = "Envelope: poly(1)"
                else:
                    yy = exp_plus_gauss_counts_per_bin(np.linspace(args.mjj_min, args.mjj_max, args.bins+1),
                                                       p["N"], p["lam"], p["w_logit"], p["mu"], p["sigma"])
                    yy = np.interp(xx, ctr, yy)
                    line_lbl = "Envelope: exp+gauss"

            ax.plot(xx, yy, color='black', lw=1.2, label=line_lbl)
            ax.legend(loc="upper right", frameon=True, facecolor="white",
                      edgecolor="black", fontsize=9)

            # info box (χ2, model, N)
            inf = (rf"$\chi^2/\mathrm{{ndof}} = {p['chi2_over_ndof']:.2f}$" "\n"
                   rf"Model: {('DCB' if grp in ('ttH','VH') else p['name'])}" "\n"
                   rf"$N = {p['N']:.0f}$")
            ax.text(0.03, 0.97, inf, transform=ax.transAxes, ha="left", va="top",
                    fontsize=9, bbox=dict(facecolor="white", edgecolor="black", linewidth=0.7, pad=4, alpha=1.0))

            ax.set_xlabel(r"$m_{jj}$ [GeV]")
            ax.set_ylabel("Events")
            ax.set_title(f"{grp} resonant background — mjj, cat={c}")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            out_png = os.path.join(args.outdir, f"mjj_{grp}_cat{c}.png")
            fig.savefig(out_png, dpi=150)
            plt.close(fig)
            print("Wrote", out_png)

    # save JSON
    out_json = os.path.join(args.outdir, "mjj_res_bkg_params.json")
    with open(out_json, "w") as f:
        json.dump({"edges": edges, "fits": results, "used_dirs": used_dirs,
                   "mjj_branch": args.mjj_branch}, f, indent=2)
    print("Saved", out_json)

if __name__ == "__main__":
    main()
