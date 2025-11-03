#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from matplotlib import lines as mlines


TREE_NAME, BR_MGG, BR_SCORE, BR_ISDATA = "selection", "diphoton_mass", "pDNN_score", "isdata"

def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys() if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

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

# ---- numerically safe double-sided Crystal Ball density ----
def dcb_density(x, mu, sigma, alphaL, nL, alphaR, nR):
    x = np.asarray(x)
    t  = (x - mu) / sigma
    aL, aR = abs(alphaL), abs(alphaR)

    core   = np.exp(-0.5 * t * t)

    # left tail mask
    mL = t < -aL
    AL = (nL/aL)**nL * np.exp(-0.5*aL*aL)
    BL = nL/aL - aL
    baseL = np.maximum(BL - t[mL], 1e-12)  # clip to avoid negative/zero
    left  = np.empty_like(t); left[:] = 0.0
    left[mL] = AL * baseL**(-nL)

    # right tail mask
    mR = t > aR
    AR = (nR/aR)**nR * np.exp(-0.5*aR*aR)
    BR = nR/aR - aR
    baseR = np.maximum(BR + t[mR], 1e-12)
    right = np.empty_like(t); right[:] = 0.0
    right[mR] = AR * baseR**(-nR)

    out = core
    out[mL] = left[mL]
    out[mR] = right[mR]
    return out

def fit_dcb_counts(bin_edges, counts, seed_mu=125.0):
    centers = 0.5*(bin_edges[:-1] + bin_edges[1:])
    y = counts.astype(float)
    total = float(y.sum())
    if total <= 0: raise RuntimeError("Empty histogram")

    mu0 = seed_mu
    w = centers - mu0
    sigma0 = max(1.2, np.sqrt(np.average(w*w, weights=np.maximum(y,0))+1e-6))
    p0 = [total, mu0, sigma0, 1.5, 3.0, 1.5, 3.0]

    def model(xc, N, mu, sigma, aL, nL, aR, nR):
        bw = np.mean(np.diff(bin_edges))
        return N * dcb_density(xc, mu, sigma, aL, nL, aR, nR) * bw

    popt, _ = curve_fit(
        model, centers, y, p0=p0,
        bounds=([0.0, 120.0, 0.3, 0.2, 1.01, 0.2, 1.01],
                [1e12, 130.0, 10.0,10.0, 50.0,10.0, 50.0]),
        maxfev=20000
    )
    N, mu, sigma, aL, nL, aR, nR = popt
    bw = np.mean(np.diff(bin_edges))
    mu_counts = dcb_density(centers, mu, sigma, aL, nL, aR, nR)*bw*N

    var = np.maximum(y, 1.0)
    chi2 = np.sum((y - mu_counts)**2 / var)
    ndof = max(len(y) - 7, 1)
    return {
        "model":"DCB","N":float(N),"mu":float(mu),"sigma":float(sigma),
        "alphaL":float(aL),"nL":float(nL),"alphaR":float(aR),"nR":float(nR),
        "chi2_over_ndof": float(chi2/ndof)
    }, mu_counts

def main():
    ap = argparse.ArgumentParser(description="Fit resonant bkg (ttH, ggH+VBFH, VH) with DCB per category.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--edges-json")
    ap.add_argument("--edges", type=float, nargs="*")
    ap.add_argument("--cats", type=int, nargs="*")
    ap.add_argument("--mgg-min", type=float, default=115.0)
    ap.add_argument("--mgg-max", type=float, default=135.0)
    ap.add_argument("--bins", type=int, default=60)
    ap.add_argument("--outdir", default="outputfiles/res_bkg_fits")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.edges: edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f: edges = sorted(json.load(f)["boundaries"]["combined"])
    else: raise SystemExit("Provide --edges or --edges-json")

    edges_full = [-np.inf] + edges + [np.inf]
    cats = list(range(len(edges_full)-1)) if args.cats is None else args.cats

    bin_edges = np.linspace(args.mgg_min, args.mgg_max, args.bins+1)
    centers = 0.5*(bin_edges[:-1] + bin_edges[1:])
    typical_bw = (args.mgg_max - args.mgg_min)/args.bins

    grouped = {g:{c:[] for c in cats} for g in ["ttH","ggH+VBFH","VH"]}
    used_dirs = []

    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            grp = group_of(d)
            if grp is None: continue
            tdir = fin[d]; sel = get_tree_key(tdir, TREE_NAME)
            if sel is None: continue
            tree = tdir[sel]
            if not {BR_MGG,BR_SCORE,BR_ISDATA}.issubset(set(tree.keys())): continue

            arr = tree.arrays([BR_MGG, BR_SCORE, BR_ISDATA], library="ak")
            isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(arr[BR_MGG])
            mc = (isdata == 0)
            mgg   = ak.to_numpy(arr[BR_MGG][mc])
            score = ak.to_numpy(arr[BR_SCORE][mc])

            for c in cats:
                lo,hi = edges_full[c], edges_full[c+1]
                m = (score >= lo) & (score < hi) & (mgg >= args.mgg_min) & (mgg <= args.mgg_max)
                if m.any(): grouped[grp][c].append(mgg[m])

            used_dirs.append(d)

    results = {}
    for grp in ["ttH","ggH+VBFH","VH"]:
        results[grp] = {}
        for c in cats:
            if not grouped[grp][c]:
                print(f"[warn] {grp} cat={c}: no entries."); continue
            x = np.concatenate(grouped[grp][c])
            H,_ = np.histogram(x, bins=bin_edges, density=False)
            yerr = np.sqrt(np.maximum(H,1.0))

            p, _ = fit_dcb_counts(bin_edges, H)      # <-- p is already the flat params dict
            results[grp][c] = {"nbins": int(H.size), "entries": int(H.sum()), "params": p}

            # # --- plotting (fixed: no nested ['params']) ---
            # fig, ax = plt.subplots(figsize=(7,5))
            # ax.errorbar(centers, H, yerr=yerr, fmt='o', ms=3, lw=1, capsize=2,
            #             label=f"{grp} (cat={c})", zorder=3)
            # xx = np.linspace(args.mgg_min, args.mgg_max, 1200)
            # yy = dcb_density(xx, p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"]) \
            #      * typical_bw * p["N"]
            # lab = (r"DCB: $\mu={:.2f}$, $\sigma={:.2f}$, "
            #        r"$\alpha_L={:.2f}$, $n_L={:.1f}$, "
            #        r"$\alpha_R={:.2f}$, $n_R={:.1f}$, "
            #        r"$\chi^2/\mathrm{{ndof}}={:.3g}$").format(
            #             p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"], p["chi2_over_ndof"])
            # ax.plot(xx, yy, lw=1.6, label=lab, zorder=2)
            # ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]"); ax.set_ylabel("Events")
            # ax.set_title(f"{grp} resonant background — cat={c}")
            # ax.legend(frameon=False, fontsize=9); ax.grid(alpha=0.2)
            # fig.tight_layout()
            # out_png = os.path.join(args.outdir, f"resbkg_{grp}_cat{c}.png")
            # fig.savefig(out_png, dpi=150); plt.close(fig)
            # print("Wrote", out_png)
             
             # --- plotting (legend fixed: Simulation then Parametric Model) ---
            
            # --- plotting (boxed legend + boxed parameter text) ---
            # --- unified boxed legend with parameter text ---
            fig, ax = plt.subplots(figsize=(7,5))

            # data points
            eb = ax.errorbar(
                centers, H, yerr=yerr, fmt='o', ms=3, lw=1, capsize=2,
                color="#1f77b4", label="Simulation", zorder=3
            )

            # smooth DCB curve
            xx = np.linspace(args.mgg_min, args.mgg_max, 1200)
            yy = dcb_density(xx, p["mu"], p["sigma"], p["alphaL"], p["nL"], p["alphaR"], p["nR"]) \
                * typical_bw * p["N"]
            ln, = ax.plot(xx, yy, lw=2.0, color="#e66101", label="Parametric Model", zorder=2)

            # parameter text (as legend entry)
            # param_txt = (r"$\mu = {:.2f}$, $\sigma = {:.2f}$, "
            #             r"$\alpha_L = {:.2f}$, $n_L = {:.1f}$, "
            #             r"$\alpha_R = {:.2f}$, $n_R = {:.1f}$, "
            #             r"$\chi^2/\mathrm{{ndof}} = {:.2f}$"
            #             ).format(p["mu"], p["sigma"], p["alphaL"], p["nL"],
            #                     p["alphaR"], p["nR"], p["chi2_over_ndof"])

            param_lines = [
                rf"$\mu={p['mu']:.2f}$, $\sigma={p['sigma']:.2f}$",
                rf"$\alpha_L={p['alphaL']:.2f}$, $n_L={p['nL']:.1f}$",
                rf"$\alpha_R={p['alphaR']:.2f}$, $n_R={p['nR']:.1f}$",
                rf"$\chi^2/\mathrm{{ndof}}={p['chi2_over_ndof']:.2f}$",
            ]
            
            
            # empty handle (so param text appears inside legend box)
            dummy_rows = [mlines.Line2D([], [], linestyle='none', marker=None, label=s) for s in param_lines]


            # combined legend
            ax.legend(
                handles = [eb.lines[0], ln] + dummy_rows,
                labels  = ["Simulation", "Parametric Model"] + param_lines,
                loc="upper left",
                bbox_to_anchor=(0.02, 0.98),
                frameon=True,
                facecolor="white",
                edgecolor="lightgray",
                framealpha=1.0,
                fontsize=10,
                handlelength=1.5,
                labelspacing=0.6,
                borderpad=0.6
            )

            # styling
            ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
            ax.set_ylabel("Events")
            ax.set_title(f"{grp} resonant background — cat={c}")
            ax.grid(alpha=0.25)
            fig.tight_layout()

            out_png = os.path.join(args.outdir, f"resbkg_{grp}_cat{c}.png")
            fig.savefig(out_png, dpi=150)
            plt.close(fig)
            print("Wrote", out_png)




    out_json = os.path.join(args.outdir, "resonant_bkg_dcb_params.json")
    with open(out_json, "w") as f:
        json.dump({"edges": edges, "fits": results, "used_dirs": used_dirs}, f, indent=2)
    print("Saved", out_json)

if __name__ == "__main__":
    main()
