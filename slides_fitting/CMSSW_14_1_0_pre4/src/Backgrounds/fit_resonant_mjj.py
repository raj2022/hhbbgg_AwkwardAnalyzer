#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resonant/non-resonant mjj fits per category with robust IO, optional weights,
stable models, and JSON-serializable outputs.

Key features
------------
- Weight branch is OPTIONAL. If absent (or --wgt-branch ''), unit weights are used.
- --score-branch and --tree-name are configurable.
- Prints which branches are missing per directory (no silent skips).
- Chebyshev model uses stabilized exponentiation to avoid overflow.
- All outputs are JSON-serializable (no numpy scalars/arrays).
- Optional DCB for "resonant-groups".
- Envelope models: exponential, Bernstein (1..N), Chebyshev-log (1..N), exp+gauss.
"""

import argparse, json, os, re, math
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import scipy.special as sps
from typing import Dict, Any, List, Tuple

# -------------------- helpers --------------------
def to_py(x):
    """Convert numpy scalars/arrays to pure-Python types for JSON."""
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, (list, tuple)):
        return [to_py(v) for v in x]
    if isinstance(x, dict):
        return {k: to_py(v) for k, v in x.items()}
    return x

def safe_norm(arr, Ntarget):
    """Rescale arr to sum=Ntarget without inf/nan problems."""
    s = np.nansum(arr)
    if not np.isfinite(s) or s <= 0:
        return np.zeros_like(arr)
    return arr * (Ntarget / s)

def centers_from_edges(edges):
    edges = np.asarray(edges, dtype=float)
    return 0.5*(edges[:-1] + edges[1:])

def hist_weighted(x, w, bins):
    H, _  = np.histogram(x, bins=bins, weights=w)
    H2, _ = np.histogram(x, bins=bins, weights=w*w)
    err   = np.sqrt(np.maximum(H2, 1e-12))
    return H.astype(float), err.astype(float)

def chi2_reduced(y, mu, npar):
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    var = np.maximum(y, 1.0)                       # Poisson-ish floor
    chi2 = float(np.sum((y - mu)**2 / var))
    ndof = max(int(len(y) - npar), 1)
    return chi2, chi2/ndof

# -------------------- ROOT structure --------------------
def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys()
            if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

def group_of(name: str):
    n = name.lower()
    if "tth" in n:
        return "ttH"
    if "ggh" in n or "vbfh" in n or re.search(r"\bvbf\b", n):
        return "ggH+VBFH"
    # broaden VH matching (WH, WPlusH, WMinusH, ZH, VH)
    if re.search(r"\bwh\b", n) or re.search(r"\bzh\b", n) or "vh" in n or "wplush" in n or "wminush" in n:
        return "VH"
    return None

# -------------------- DCB (resonant) --------------------
def dcb_density(x, mu, sigma, alphaL, nL, alphaR, nR):
    x = np.asarray(x, dtype=float)
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

def dcb_counts_per_bin(bin_edges, N, mu, sigma, aL, nL, aR, nR, oversample=35):
    edges = np.asarray(bin_edges, dtype=float)
    out = np.zeros(len(edges)-1, dtype=float)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        xx = np.linspace(lo, hi, oversample, endpoint=False) + (hi-lo)/(2*oversample)
        dens = dcb_density(xx, mu, sigma, aL, nL, aR, nR)
        out[i] = dens.mean() * (hi - lo)
    return safe_norm(out, N)

def fit_dcb_binned(bin_edges, counts, seed_mu=None, maxfev=30000):
    y = counts.astype(float)
    total = float(np.sum(y))
    if total <= 0:
        raise RuntimeError("Empty histogram for DCB fit")
    ctr = centers_from_edges(bin_edges)
    mu0 = seed_mu if seed_mu is not None else float(ctr[np.argmax(y)])
    sigma0 = max(5.0, (bin_edges[-1]-bin_edges[0])/40.0)
    p0 = [total, mu0, sigma0, 1.5, 3.0, 1.5, 3.0]
    def model_dummy(_x, N, mu, sigma, aL, nL, aR, nR):
        return dcb_counts_per_bin(bin_edges, N, mu, sigma, aL, nL, aR, nR, oversample=45)
    popt, _ = curve_fit(lambda xx, N, mu, sig, aL, nL, aR, nR: model_dummy(None, N, mu, sig, aL, nL, aR, nR),
                        ctr, y, p0=p0,
                        bounds=([0.0, bin_edges[0], 1.0, 0.2, 1.01, 0.2, 1.01],
                                [1e12, bin_edges[-1], (bin_edges[-1]-bin_edges[0])/2.0, 10.0, 50.0, 10.0, 50.0]),
                        maxfev=maxfev)
    mu_model = model_dummy(None, *popt)
    chi2, chi2ndof = chi2_reduced(y, mu_model, npar=7)
    N, mu, sig, aL, nL, aR, nR = [to_py(v) for v in popt]
    return {
        "name": "DCB",
        "N": float(N), "mu": float(mu), "sigma": float(sig),
        "alphaL": float(aL), "nL": float(nL), "alphaR": float(aR), "nR": float(nR),
        "chi2": float(chi2), "chi2_over_ndof": float(chi2ndof), "npar": 7
    }, mu_model

# -------------------- Envelope models --------------------
def expo_counts_per_bin(edges, N, lam):
    edges = np.asarray(edges, dtype=float)
    out = np.zeros(len(edges)-1, dtype=float)
    E0, E1 = edges[0], edges[-1]
    denom = np.exp(lam*E1) - np.exp(lam*E0) if abs(lam) > 1e-12 else (E1 - E0)
    if not np.isfinite(denom) or abs(denom) < 1e-300:
        return np.zeros_like(out)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        if abs(lam) < 1e-12:
            out[i] = (hi - lo) / (E1 - E0)
        else:
            out[i] = (np.exp(lam*hi) - np.exp(lam*lo)) / (lam * denom)
    return safe_norm(out, N)

def bernstein_basis(z, degree):
    z = np.asarray(z, dtype=float)
    n = degree
    out = np.zeros((n+1, z.size), dtype=float)
    for k in range(n+1):
        out[k] = sps.binom(n, k) * (z**k) * ((1.0 - z)**(n-k))
    return out

def bernstein_counts_per_bin(edges, N, *w_sq_args):
    edges = np.asarray(edges, dtype=float)
    degree = len(w_sq_args) - 1
    out = np.zeros(len(edges)-1, dtype=float)
    lo, hi = edges[0], edges[-1]
    weights = np.array(w_sq_args, dtype=float)**2
    wsum = np.sum(weights)
    wnorm = (weights / wsum) if wsum > 0 else np.ones_like(weights)/len(weights)
    for i in range(len(out)):
        a, b = edges[i], edges[i+1]
        z = np.linspace(a, b, 35, endpoint=False) + (b-a)/70.0
        zz = (z - lo) / (hi - lo)
        basis = bernstein_basis(zz, degree)  # (deg+1, npoints)
        dens = np.dot(wnorm, basis)
        out[i] = float(np.mean(dens) * (b-a))
    return safe_norm(out, N)

def chebyshev_counts_per_bin(edges, N, *a_coeffs):
    """
    Density ~ exp(poly_chebyshev(zz)), zz in [-1,1], with stabilized exponentiation.
    """
    edges = np.asarray(edges, dtype=float)
    out = np.zeros(len(edges)-1, dtype=float)
    a = edges[0]; b = edges[-1]
    degree = len(a_coeffs) - 1
    a_coeffs = np.asarray(a_coeffs, dtype=float)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        z = np.linspace(lo, hi, 45, endpoint=False) + (hi-lo)/90.0
        zz = 2.0*(z - a)/(b - a) - 1.0
        # Chebyshev basis
        T0 = np.ones_like(zz)
        if degree == 0:
            poly = a_coeffs[0]*T0
        else:
            T1 = zz.copy()
            Ts = [T0, T1]
            for k in range(2, degree+1):
                Ts.append(2*zz*Ts[-1] - Ts[-2])
            Ts = np.array(Ts[:degree+1])
            poly = np.dot(a_coeffs, Ts)
        # stabilize exp
        m = float(np.max(poly))
        dens = np.exp(np.clip(poly - m, -50, 50))  # clip for extra safety
        out[i] = float(np.mean(dens) * (hi-lo))
    return safe_norm(out, N)

def exp_plus_gauss_counts_per_bin(edges, N, lam, w_peak, mu, sigma):
    w = 1.0/(1.0 + np.exp(-w_peak))  # logistic in (0,1)
    edges = np.asarray(edges, dtype=float)
    out = np.zeros(len(edges)-1, dtype=float)
    for i in range(len(out)):
        lo, hi = edges[i], edges[i+1]
        zz = np.linspace(lo, hi, 35, endpoint=False) + (hi-lo)/70.0
        exp_d = np.exp(np.clip(lam*zz, -80, 80))
        gaus  = np.exp(-0.5*np.clip(((zz-mu)/sigma)**2, 0, 1e6))/(abs(sigma)*np.sqrt(2*np.pi))
        dens = (1.0-w)*exp_d + w*gaus
        out[i] = float(np.mean(dens) * (hi-lo))
    return safe_norm(out, N)

def fit_envelope(edges, counts, max_bern_deg=3, max_cheby_deg=3):
    """
    Try: expo, bernstein (1..max_bern_deg), chebyshev (1..max_cheby_deg), exp+gauss.
    Returns: (best_params_dict, best_model_counts, tried_list_without_mu_arrays)
    """
    y = counts.astype(float)
    Ntot = float(np.sum(y))
    ctr = centers_from_edges(edges)
    candidates: List[Tuple[str, Dict[str, Any], np.ndarray]] = []

    # Exponential
    try:
        def model_expo(_x, N, lam): return expo_counts_per_bin(edges, N, lam)
        p0 = [Ntot, -0.005]
        popt, _ = curve_fit(lambda x, N, lam: model_expo(None, N, lam), ctr, y, p0=p0, maxfev=20000)
        mu = model_expo(None, *popt)
        chi2, chi2ndof = chi2_reduced(y, mu, npar=2)
        pars = {"N":float(to_py(popt[0])), "lam":float(to_py(popt[1])),
                "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof), "npar":2, "score":0.5*chi2+1.0}
        candidates.append(("expo", pars, mu))
    except Exception:
        pass

    # Bernstein
    for deg in range(1, max_bern_deg+1):
        try:
            p0 = [Ntot] + [1.0]*(deg+1)
            def model_bern(_x, *pars): return bernstein_counts_per_bin(edges, *pars)
            popt, _ = curve_fit(lambda x, *pars: model_bern(None, *pars), ctr, y, p0=p0, maxfev=40000)
            mu = model_bern(None, *popt)
            chi2, chi2ndof = chi2_reduced(y, mu, npar=(deg+2))
            pars = {"N":float(to_py(popt[0])), "degree":deg,
                    **{f"w_{k}": float(to_py(popt[1+k])) for k in range(deg+1)},
                    "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof), "npar":deg+2, "score":0.5*chi2+0.5*(deg+2)}
            candidates.append((f"bern_{deg}", pars, mu))
        except Exception:
            pass

    # Chebyshev (log-density)
    for deg in range(1, max_cheby_deg+1):
        try:
            p0 = [Ntot] + [0.0]*(deg+1)
            def model_cheby(_x, *pars): return chebyshev_counts_per_bin(edges, *pars)
            popt, _ = curve_fit(lambda x, *pars: model_cheby(None, *pars), ctr, y, p0=p0, maxfev=40000)
            mu = model_cheby(None, *popt)
            chi2, chi2ndof = chi2_reduced(y, mu, npar=(deg+2))
            pars = {"N":float(to_py(popt[0])), "degree":deg,
                    **{f"a_{k}": float(to_py(popt[1+k])) for k in range(deg+1)},
                    "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof), "npar":deg+2, "score":0.5*chi2+0.5*(deg+2)}
            candidates.append((f"cheby_{deg}", pars, mu))
        except Exception:
            pass

    # exp + gauss
    try:
        def model_mix(_x, N, lam, wpk, mu, sig): return exp_plus_gauss_counts_per_bin(edges, N, lam, wpk, mu, sig)
        mid = 0.5*(edges[0]+edges[-1])
        p0 = [Ntot, -0.005, 0.0, mid, max(5.0, (edges[-1]-edges[0])/20.0)]
        bounds = ([0.0, -1.0, -6.0, edges[0],  1.0],
                  [1e12,  1.0,  6.0, edges[-1], (edges[-1]-edges[0])/2.0])
        popt, _ = curve_fit(lambda x, N, lam, w, m, s: model_mix(None, N, lam, w, m, s),
                            ctr, y, p0=p0, bounds=bounds, maxfev=40000)
        mu = model_mix(None, *popt)
        chi2, chi2ndof = chi2_reduced(y, mu, npar=5)
        pars = {"N":float(to_py(popt[0])), "lam":float(to_py(popt[1])), "w_logit":float(to_py(popt[2])),
                "mu":float(to_py(popt[3])), "sigma":float(to_py(popt[4])),
                "chi2":float(chi2), "chi2_over_ndof":float(chi2ndof), "npar":5, "score":0.5*chi2+2.5}
        candidates.append(("exp_plus_gauss", pars, mu))
    except Exception:
        pass

    if not candidates:
        raise RuntimeError("Envelope fit failed (no successful candidates).")

    # pick best by score
    best = min(candidates, key=lambda t: t[1]["score"])
    name, pars, mu = best
    pars["name"] = name

    # Only keep compact info for "tried" (no mu arrays)
    tried = [{"name": n, "params": p} for (n, p, _mu) in candidates]
    return pars, mu, tried

# -------------------- main --------------------
def main():
    ap = argparse.ArgumentParser(description="Fit dijet mass per category (resonant or envelope).")
    ap.add_argument("--root", required=True)
    ap.add_argument("--edges-json")
    ap.add_argument("--edges", type=float, nargs="*")
    ap.add_argument("--cats", type=int, nargs="*")
    ap.add_argument("--tree-name", default="selection")
    ap.add_argument("--score-branch", default="pDNN_score")
    ap.add_argument("--mjj-branch", default="dibjet_mass")
    ap.add_argument("--wgt-branch", default="weight", help="Set to '' for unit weights")
    ap.add_argument("--use-isdata", action="store_true", help="If present, keep only isdata==0 (MC) when 'isdata' branch exists.")
    ap.add_argument("--mjj-min", type=float, default=60.0)
    ap.add_argument("--mjj-max", type=float, default=200.0)
    ap.add_argument("--bins", type=int, default=45)
    ap.add_argument("--outdir", default="outputs/res_bkg_mjj_fits")
    ap.add_argument("--resonant-groups", default="", help="Comma-separated list: e.g. 'ggH+VBFH' or 'ttH,VH'")
    ap.add_argument("--max-bern-deg", type=int, default=3)
    ap.add_argument("--max-cheby-deg", type=int, default=3)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Resolve category edges
    if args.edges:
        edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            edges = sorted(json.load(f)["boundaries"]["combined"])
    else:
        raise SystemExit("Provide --edges or --edges-json")
    edges_full = [-np.inf] + edges + [np.inf]
    cats = list(range(len(edges_full)-1)) if args.cats is None else args.cats

    # Binning for mjj
    bin_edges = np.linspace(args.mjj_min, args.mjj_max, args.bins+1)

    # Resonant groups validation
    resonant_groups = [g.strip() for g in args.resonant_groups.split(",") if g.strip()]
    allowed_groups = {"ttH", "ggH+VBFH", "VH"}
    for g in resonant_groups:
        if g not in allowed_groups:
            raise SystemExit(f"Unknown resonant group '{g}'. Allowed: {sorted(allowed_groups)}")

    grouped = {g:{c:[] for c in cats} for g in ["ttH","ggH+VBFH","VH"]}
    used_dirs: List[str] = []

    # Read ROOT
    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            grp = group_of(d)
            if grp is None:
                continue
            tdir = fin[d]
            sel = get_tree_key(tdir, args.tree_name)
            if sel is None:
                print(f"[skip] dir={d} missing tree '{args.tree_name}'")
                continue
            tree = tdir[sel]

            required = {args.mjj_branch, args.score_branch}
            optional = set()
            if args.wgt_branch:
                optional.add(args.wgt_branch)
            if args.use_isdata and "isdata" in tree.keys():
                optional.add("isdata")

            present = set(tree.keys())
            missing_req = required - present
            if missing_req:
                print(f"[skip] dir={d} missing required branches: {sorted(missing_req)}")
                continue

            read_keys = list(required | (optional & present))
            arr = tree.arrays(read_keys, library="ak")

            # isdata filter (only MC)
            if args.use_isdata and "isdata" in arr.fields:
                arr = arr[arr["isdata"] == 0]

            # Convert after alignment
            mjj_all   = ak.to_numpy(arr[args.mjj_branch])
            score_all = ak.to_numpy(arr[args.score_branch])
            if args.wgt_branch and args.wgt_branch in arr.fields:
                w_all = ak.to_numpy(arr[args.wgt_branch])
            else:
                w_all = np.ones_like(mjj_all, dtype=float)

            # Basic cleaning
            valid = np.isfinite(mjj_all) & np.isfinite(score_all)
            if not np.any(valid):
                print(f"[skip] dir={d} has no valid entries after finite check")
                continue
            mjj_all, score_all, w_all = mjj_all[valid], score_all[valid], w_all[valid]

            # mjj window
            win = (mjj_all >= args.mjj_min) & (mjj_all <= args.mjj_max)
            if not np.any(win):
                used_dirs.append(d)
                continue
            mjj_all, score_all, w_all = mjj_all[win], score_all[win], w_all[win]

            # accumulate per category
            for c in cats:
                lo, hi = edges_full[c], edges_full[c+1]
                m = (score_all >= lo) & (score_all < hi)
                if np.any(m):
                    grouped[grp][c].append((mjj_all[m].astype(float), w_all[m].astype(float)))

            used_dirs.append(d)

    # Fit & plot
    results: Dict[str, Any] = {}
    for grp in ["ttH","ggH+VBFH","VH"]:
        results[grp] = {}
        for c in cats:
            if not grouped[grp][c]:
                print(f"[warn] {grp} cat={c}: no mjj entries.")
                continue

            x = np.concatenate([xi for (xi, wi) in grouped[grp][c]]).astype(float)
            w = np.concatenate([wi for (xi, wi) in grouped[grp][c]]).astype(float)
            H, yerr = hist_weighted(x, w, bin_edges)

            # Choose model
            if grp in resonant_groups:
                try:
                    p, model_counts = fit_dcb_binned(bin_edges, H)
                    store = {"model": "DCB", "params": to_py(p), "entries": float(np.sum(H)),
                             "nbins": int(H.size), "model_counts": to_py(model_counts)}
                except Exception as e:
                    print(f"[error] DCB fit failed for {grp} cat={c}: {e}")
                    try:
                        p, model_counts, tried = fit_envelope(bin_edges, H,
                                                              max_bern_deg=args.max_bern_deg,
                                                              max_cheby_deg=args.max_cheby_deg)
                        store = {"model": p["name"], "params": to_py(p), "entries": float(np.sum(H)),
                                 "nbins": int(H.size), "tried": to_py(tried),
                                 "fallback_from": "DCB", "model_counts": to_py(model_counts)}
                    except Exception as e2:
                        print(f"[error] Fallback envelope failed for {grp} cat={c}: {e2}")
                        store = {"model": "FAILED", "entries": float(np.sum(H)), "nbins": int(H.size)}
            else:
                try:
                    p, model_counts, tried = fit_envelope(bin_edges, H,
                                                          max_bern_deg=args.max_bern_deg,
                                                          max_cheby_deg=args.max_cheby_deg)
                    store = {"model": p["name"], "params": to_py(p), "entries": float(np.sum(H)),
                             "nbins": int(H.size), "tried": to_py(tried), "model_counts": to_py(model_counts)}
                except Exception as e:
                    print(f"[error] Envelope fit failed for {grp} cat={c}: {e}")
                    try:
                        p, model_counts = fit_dcb_binned(bin_edges, H)
                        store = {"model": "DCB", "params": to_py(p), "entries": float(np.sum(H)),
                                 "nbins": int(H.size), "fallback_from": "envelope",
                                 "model_counts": to_py(model_counts)}
                    except Exception as e2:
                        print(f"[error] Fallback DCB failed for {grp} cat={c}: {e2}")
                        store = {"model": "FAILED", "entries": float(np.sum(H)), "nbins": int(H.size)}

            results[grp][c] = store

            # ---- plotting ----
            fig, ax = plt.subplots(figsize=(7,5))
            ax.errorbar(centers_from_edges(bin_edges), H, yerr=yerr, fmt='^', ms=4, lw=0.8,
                        ecolor='black', elinewidth=0.8, capsize=0, label="Simulation")

            xx = np.linspace(args.mjj_min, args.mjj_max, 1200)
            if "model_counts" in store:
                yy_bins = np.asarray(store["model_counts"], dtype=float)
                yy = np.interp(xx, centers_from_edges(bin_edges), yy_bins)
            else:
                yy = np.zeros_like(xx)

            ax.plot(xx, yy, lw=1.2, label=f"Model: {store.get('model','')}")
            ax.legend(loc="upper right", frameon=True, fontsize=9)

            pm = store.get("params", {})
            info_lines = []
            if isinstance(pm, dict) and "chi2_over_ndof" in pm:
                info_lines.append(rf"$\chi^2/\mathrm{{ndof}} = {pm['chi2_over_ndof']:.2f}$")
            info_lines.append(f"Model: {store.get('model','')}")
            if isinstance(pm, dict) and "N" in pm:
                info_lines.append(rf"$N = {pm['N']:.0f}$")
            if isinstance(pm, dict) and "degree" in pm:
                info_lines.append(f"deg = {pm['degree']}")
            ax.text(0.03, 0.97, "\n".join(info_lines), transform=ax.transAxes, ha="left", va="top",
                    fontsize=9, bbox=dict(facecolor="white", edgecolor="black", linewidth=0.7, pad=4, alpha=1.0))

            ax.set_xlabel(r"$m_{jj}$ [GeV]")
            ax.set_ylabel("Events")
            ax.set_title(f"{grp} background — mjj, cat={c}")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            out_png = os.path.join(args.outdir, f"mjj_{grp}_cat{c}.png")
            fig.savefig(out_png, dpi=150)
            plt.close(fig)
            print("Wrote", out_png)

    # Save JSON (pure Python types)
    out_json = os.path.join(args.outdir, "mjj_res_bkg_params.json")
    payload = {
        "edges": to_py(edges),
        "fits": to_py(results),
        "used_dirs": to_py(used_dirs),
        "mjj_branch": args.mjj_branch,
        "score_branch": args.score_branch,
        "tree_name": args.tree_name,
        "resonant_groups": to_py(resonant_groups),
        "mjj_range": [float(args.mjj_min), float(args.mjj_max)],
        "nbins": int(args.bins)
    }
    with open(out_json, "w") as f:
        json.dump(payload, f, indent=2)
    print("Saved", out_json)

if __name__ == "__main__":
    main()
