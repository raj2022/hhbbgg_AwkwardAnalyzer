#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, re
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.optimize import curve_fit
from scipy.stats import chi2 as chi2dist

# ----------------- Tree/branches -----------------
TREE_NAME   = "selection"
BR_MGG      = "diphoton_mass"
BR_SCORE    = "pDNN_score"
BR_ISDATA   = "isdata"
BR_MJJ_DEF  = "dijet_mass"   # <- default dijet branch (change with --mjj-branch)

# ----------------- Directory filters -------------
def is_resonant(name: str) -> bool:
    n = name.lower()
    return ("tth" in n) or ("ggh" in n) or ("vbfh" in n) or ("vbf" in n) or ("vh" in n) or re.search(r"\bwh\b|\bzh\b", n)

def is_signal_dir(name: str) -> bool:
    n = name.lower()
    return ("nmssm" in n) or ("radion" in n) or ("graviton" in n) or ("gluglutohh" in n) or (re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None)

def is_nonres_bkg_dir(name: str) -> bool:
    n = name.lower()
    if is_signal_dir(n) or is_resonant(n): return False
    return ("gjets" in n) or ("gjet" in n) or ("gammajet" in n) or ("qcd" in n) or ("multijet" in n) or ("nonres" in n) or ("data" in n) or ("dd_" in n) or ("driven" in n)

def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys() if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base: return tkey
    return None

# ----------------- Weighted hist -----------------
def hist_w(x, w, bins):
    H, _  = np.histogram(x, bins=bins, weights=w)
    H2, _ = np.histogram(x, bins=bins, weights=w*w)
    err = np.sqrt(np.maximum(H2, 1e-12))
    return H, err

# ----------------- Helpers -----------------------
def centers_from_edges(edges):
    return 0.5*(edges[:-1] + edges[1:])

def normalize_density(xx, dens):
    area = np.trapz(dens, xx)
    return dens/area if area > 0 else dens*0.0

def map_to_unit(xx, lo, hi):
    z = (xx - lo)/(hi - lo)
    return np.clip(z, 0, 1)

# --------------- Template families ---------------
def bernstein_density(xx, lo, hi, theta):
    c = np.square(theta)
    n = len(c) - 1
    z = map_to_unit(xx, lo, hi)
    from math import comb
    B = np.zeros_like(xx, dtype=float)
    for k in range(n+1):
        B += c[k] * comb(n, k) * (z**k) * ((1-z)**(n-k))
    return normalize_density(xx, B)

def chebyshev_density(xx, lo, hi, theta):
    z = 2*map_to_unit(xx, lo, hi) - 1.0
    n = len(theta) - 1
    T0, T1 = np.ones_like(z), z
    Ts = [T0, T1]
    for k in range(2, n+1):
        Ts.append(2*z*Ts[-1] - Ts[-2])
    poly = theta[0]*Ts[0]
    for k in range(1, n+1):
        poly += theta[k]*Ts[k]
    dens = np.square(poly) + 1e-12
    return normalize_density(xx, dens)

def exp_poly_density(xx, lo, hi, theta):
    p = np.zeros_like(xx) + theta[0]
    for k in range(1, len(theta)):
        p += theta[k] * (xx**k)
    dens = np.exp(p - np.max(p))
    return normalize_density(xx, dens)

def powerlaw_density(xx, lo, hi, theta):
    p = np.clip(theta[0], 0.1, 10.0)
    base = np.power(np.clip(xx, 1e-6, None), -p)
    series = np.ones_like(xx)
    for k in range(1, len(theta)):
        series += (theta[k]**2) * (xx**k)
    dens = base * series
    return normalize_density(xx, dens)

def laurent_density(xx, lo, hi, theta):
    dens = np.zeros_like(xx)
    for k in range(1, len(theta)+1):
        dens += (theta[k-1]**2) / np.power(np.clip(xx, 1e-6, None), k)
    return normalize_density(xx, dens)

FAMILIES = {
    "bernstein":   bernstein_density,   # available if passed explicitly
    "chebyshev":   chebyshev_density,
    "exponential": exp_poly_density,
    "powerlaw":    powerlaw_density,
    "laurent":     laurent_density,
}

# ---- expected counts from a density (midpoint integration) ----
def expected_counts(bin_edges, dens_callable, N):
    out = np.zeros(len(bin_edges)-1)
    for i in range(len(out)):
        lo, hi = bin_edges[i], bin_edges[i+1]
        xm = 0.5*(lo+hi)
        out[i] = dens_callable(xm) * (hi-lo) * N
    s = out.sum()
    if s > 0: out *= (N/s)
    return out

# --------------- Fit one family@order on sidebands ---------------
def fit_family(bin_edges, y, family, order, blind_lo=None, blind_hi=None):
    centers = centers_from_edges(bin_edges)
    Ntot = float(y.sum())

    # sideband mask: if blind_lo/hi not provided -> use all bins
    if (blind_lo is None) or (blind_hi is None):
        sb_mask = np.ones_like(centers, dtype=bool)
    else:
        sb_mask = (centers <= blind_lo) | (centers >= blind_hi)

    if sb_mask.sum() < (order + 1):
        raise RuntimeError("Too few bins to constrain this order")

    xx_dense = np.linspace(bin_edges[0], bin_edges[-1], 1500)
    dens_fun = FAMILIES[family]

    npar_shape = order + 1
    theta0 = np.zeros(npar_shape)
    if family == "exponential":
        theta0[0] = 0.0
        if npar_shape >= 2: theta0[1] = -0.02
    elif family in ("powerlaw", "laurent"):
        theta0[:] = 0.5

    def model_counts(theta):
        dens_vals = dens_fun(xx_dense, bin_edges[0], bin_edges[-1], np.asarray(theta))
        dens_at = lambda x: np.interp(x, xx_dense, dens_vals, left=0.0, right=0.0)
        mu = expected_counts(bin_edges, dens_at, Ntot)
        return mu

    def model_for_cf(_x, *theta):
        return model_counts(theta)[sb_mask]

    popt, _ = curve_fit(model_for_cf, centers[sb_mask], y[sb_mask], p0=theta0, maxfev=40000)

    mu_all = model_counts(popt)
    var = np.maximum(y, 1.0)
    chi2 = np.sum(((y - mu_all)**2 / var)[sb_mask])
    ndof = max(int(sb_mask.sum()) - npar_shape, 1)
    chi2ndof = chi2/ndof

    return {
        "family": family, "order": int(order),
        "theta": list(map(float, np.asarray(popt).tolist())),
        "chi2": float(chi2), "chi2_over_ndof": float(chi2ndof),
        "ndof": int(ndof), "npar": int(npar_shape)
    }, mu_all

# --------------- Order selection per family ----------------------
def pick_order_by_deltaNLL(records):
    rec = sorted(records, key=lambda r: r["order"])
    if not rec: return None
    choice = rec[0]
    for i in range(1, len(rec)):
        prev, cur = rec[i-1], rec[i]
        d2NLL = cur["chi2"] - prev["chi2"]
        dk    = (cur["npar"] - prev["npar"])
        if dk <= 0: continue
        pval = 1.0 - chi2dist.cdf(d2NLL, dk)
        if pval >= 0.5:
            choice = prev
            break
        choice = cur
    choice = min(rec, key=lambda r: r["chi2"]/max(r["ndof"],1)) if choice is None else choice
    return choice

# --------------- Plot style -------------------------------------
def rootish(ax):
    from matplotlib.ticker import AutoMinorLocator
    for s in ax.spines.values():
        s.set_linewidth(1.0); s.set_color("black")
    ax.tick_params(direction="in", which="both", top=True, right=True,
                   length=4, width=1.0, color="black", labelsize=10)
    ax.tick_params(which="minor", length=2)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))

# ----------------- Plot helper (ratio, blinding-aware) ----------
def plot_with_ratio(
    varlabel, cat_idx, centers, H, Herr, bin_edges,
    best_fam, best_rec, best_mu, family_shapes, args,
    blind_lo=None, blind_hi=None, out_png=None
):
    fig = plt.figure(figsize=(7, 6))
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.05)
    ax  = fig.add_subplot(gs[0])
    rax = fig.add_subplot(gs[1], sharex=ax)
    rootish(ax); rootish(rax)

    # shaded blinded window if requested
    if (blind_lo is not None) and (blind_hi is not None):
        for a in (ax, rax):
            a.axvspan(blind_lo, blind_hi, color="gray", alpha=0.22, lw=0, zorder=0)

    # show points outside blind; else all points
    if (blind_lo is not None) and (blind_hi is not None):
        mask_pts = (centers < blind_lo) | (centers > blind_hi)
    else:
        mask_pts = np.ones_like(centers, dtype=bool)

    label_pts = "Data (sideband fit)" if args.use_data else "Simulation (sideband fit)"
    ax.errorbar(centers[mask_pts], H[mask_pts], yerr=Herr[mask_pts],
                fmt='o', ms=3, lw=0.8, color='black', ecolor='black',
                label=label_pts, zorder=2)

    # best curve (smooth)
    xx = np.linspace(bin_edges[0], bin_edges[-1], 1500)
    dens = FAMILIES[best_fam](xx, bin_edges[0], bin_edges[-1], np.array(best_rec["theta"]))
    yy  = dens * (bin_edges[-1] - bin_edges[0]) / (len(bin_edges)-1) * H.sum()
    ax.plot(xx, yy, '-', color='C1', lw=2.0,
            label=f"{best_fam}, n={best_rec['order']} (best)", zorder=3)

    # overlays for same family — SKIP n=4 and n=5
    for n, mu in sorted(family_shapes[best_fam].items()):
        if n in (best_rec["order"], 4, 5): continue
        yys = np.interp(xx, centers, mu)
        ax.plot(xx, yys, lw=1.0, alpha=0.6, color='C2', label=f"{best_fam}, n={n}", zorder=1)

    ax.set_xlim(bin_edges[0], bin_edges[-1])
    ax.set_ylabel("Events")
    ax.set_title(f"Non-resonant background — {varlabel} — cat={cat_idx}")
    ax.legend(frameon=True, facecolor="white", edgecolor="lightgray", fontsize=9, ncol=2)
    ax.grid(alpha=0.2)

    # ratio (Data / Fit) — no legend
    den = np.maximum(best_mu, 1e-9)
    ratio = H / den
    ratio_err = Herr / den
    msk = (den > 0) & mask_pts

    rax.errorbar(centers[msk], ratio[msk], yerr=ratio_err[msk],
                 fmt='o', ms=3, lw=0.8, color='black', ecolor='black')
    rax.axhline(1.0, color='C1', lw=1.2)
    if np.any(msk):
        lo = np.nanpercentile(ratio[msk], 2)
        hi = np.nanpercentile(ratio[msk], 98)
        pad = 0.05 * (hi - lo if hi > lo else 0.2)
        rax.set_ylim(max(0.5, lo - pad), min(1.5, hi + pad))
    else:
        rax.set_ylim(0.5, 1.5)

    xlab = r"$m_{\gamma\gamma}$ [GeV]" if varlabel == "mγγ" else r"$m_{jj}$ [GeV]"
    rax.set_ylabel("Data / fit")
    rax.set_xlabel(xlab)
    rax.grid(alpha=0.2)

    fig.tight_layout()
    if out_png:
        fig.savefig(out_png, dpi=150)
        plt.close(fig)

# ----------------- Main -----------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Non-resonant sideband fits for mgg (blinded) and mjj (unblinded).")
    ap.add_argument("--root", required=True)
    ap.add_argument("--edges-json")
    ap.add_argument("--edges", type=float, nargs="*")
    ap.add_argument("--cats", type=int, nargs="*")

    # mgg config (blinded)
    ap.add_argument("--mgg-min", type=float, default=105.0)
    ap.add_argument("--mgg-max", type=float, default=160.0)
    ap.add_argument("--mgg-bins", type=int, default=56)
    ap.add_argument("--blind-lo", type=float, default=115.0)
    ap.add_argument("--blind-hi", type=float, default=135.0)

    # mjj config (no blinding)
    ap.add_argument("--do-mjj", action="store_true", help="Also fit dijet mass.")
    ap.add_argument("--mjj-branch", default=BR_MJJ_DEF)
    ap.add_argument("--mjj-min", type=float, default=60.0)
    ap.add_argument("--mjj-max", type=float, default=180.0)
    ap.add_argument("--mjj-bins", type=int, default=60)

    ap.add_argument("--wgt-branch", default="weight", help="'' to use unit weights")
    ap.add_argument("--use-data", action="store_true", help="Fit sidebands on DATA (default MC if absent)")
    ap.add_argument("--outdir", default="outputfiles/nonres_fits")
    ap.add_argument("--families", nargs="*", default=["exponential","chebyshev","powerlaw","laurent"])
    ap.add_argument("--order-max", type=int, default=5)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # category edges
    if args.edges: edges = sorted(args.edges)
    elif args.edges_json:
        with open(args.edges_json) as f:
            edges = sorted(json.load(f)["boundaries"]["combined"])
    else:
        raise SystemExit("Provide --edges or --edges-json")

    edges_full = [-np.inf] + edges + [np.inf]
    cats = list(range(len(edges_full)-1)) if args.cats is None else args.cats

    # book collections
    per_cat_mgg = {c: [] for c in cats}
    per_cat_mjj = {c: [] for c in cats} if args.do_mjj else None
    used_dirs = []

    with uproot.open(args.root) as fin:
        for d in collect_dirs(fin):
            if not is_nonres_bkg_dir(d):
                continue
            tdir = fin[d]
            sel = get_tree_key(tdir, TREE_NAME)
            if sel is None:
                print(f"[info] skipping '{d}': no '{TREE_NAME}' tree")
                continue
            tree = tdir[sel]

            # figure out which branches exist
            tree_keys = set(tree.keys())

            needed = {BR_MGG, BR_SCORE}
            if args.do_mjj: needed.add(args.mjj_branch)
            if args.wgt_branch: needed.add(args.wgt_branch)

            # don't require BR_ISDATA; we handle it gracefully
            if not needed.issubset(tree_keys):
                missing = sorted(list(needed - tree_keys))
                print(f"[info] skipping '{d}': missing branches {missing}")
                continue

            # read arrays (include isdata if present)
            read_fields = list(needed | ({BR_ISDATA} if BR_ISDATA in tree_keys else set()))
            arr = tree.arrays(read_fields, library="ak")

            def as_np(x): return ak.to_numpy(x) if isinstance(x, ak.Array) else np.asarray(x)

            mgg   = as_np(arr[BR_MGG])
            score = as_np(arr[BR_SCORE])

            if args.wgt_branch and args.wgt_branch in arr.fields:
                w = as_np(arr[args.wgt_branch])
            else:
                w = np.ones_like(mgg, dtype=float)

            # decide data vs MC mask
            dir_is_data = ("data" in d.lower())
            if BR_ISDATA in arr.fields:
                isdata = as_np(arr[BR_ISDATA])
            elif dir_is_data:
                isdata = np.ones_like(mgg, dtype=int)
            else:
                isdata = np.zeros_like(mgg, dtype=int)

            use_mask = (isdata == 1) if args.use_data else (isdata == 0)

            # mgg window
            win_g = (mgg >= args.mgg_min) & (mgg <= args.mgg_max)
            sel_mask_g = use_mask & win_g

            mgg_s, score_s, w_s = mgg[sel_mask_g], score[sel_mask_g], w[sel_mask_g]

            if mgg_s.size == 0:
                mode = "DATA" if args.use_data else "MC"
                print(f"[warn] '{d}': no entries after selection in {mode} mode (mgg window).")
                continue

            # fill per-category (mgg)
            for c in cats:
                lo, hi = edges_full[c], edges_full[c+1]
                m = (score_s >= lo) & (score_s < hi)
                if np.any(m):
                    per_cat_mgg[c].append((mgg_s[m], w_s[m]))

            # mjj (optional)
            if args.do_mjj:
                if args.mjj_branch not in arr.fields:
                    print(f"[info] '{d}': skipping mjj (branch '{args.mjj_branch}' missing)")
                else:
                    mjj_all = as_np(arr[args.mjj_branch])
                    win_j = (mjj_all >= args.mjj_min) & (mjj_all <= args.mjj_max)

                    # alignment checks
                    if win_j.shape != mgg.shape or use_mask.shape != mgg.shape:
                        raise RuntimeError("Internal mask size mismatch between arrays.")

                    sel_mask_j = use_mask & win_j

                    # reuse score_s, w_s but with mjj window; need their mjj-window slices
                    # Build combined (use_mask & win_j) then subset original score, w, mjj
                    mjj_s = mjj_all[sel_mask_j]
                    score_j = score[sel_mask_j]
                    w_j = w[sel_mask_j]

                    if mjj_s.size == 0:
                        mode = "DATA" if args.use_data else "MC"
                        print(f"[warn] '{d}': no entries after selection in {mode} mode (mjj window).")
                    else:
                        for c in cats:
                            lo, hi = edges_full[c], edges_full[c+1]
                            m = (score_j >= lo) & (score_j < hi)
                            if np.any(m):
                                per_cat_mjj[c].append((mjj_s[m], w_j[m]))

            used_dirs.append(d)

    all_results = {"mgg": {}, "mjj": {} if args.do_mjj else None, "used_dirs": used_dirs, "edges": edges}

    # ------------- helper to run envelope + plot -------------
    def fit_plot_variable(varname, per_cat, vmin, vmax, nbins, blind=None):
        results = {}
        bin_edges = np.linspace(vmin, vmax, nbins+1)
        centers  = centers_from_edges(bin_edges)
        for c in cats:
            if not per_cat[c]:
                print(f"[warn] {varname}: cat={c}: no entries.")
                continue
            x = np.concatenate([xi for (xi, wi) in per_cat[c]])
            w = np.concatenate([wi for (xi, wi) in per_cat[c]])
            H, Herr = hist_w(x, w, bin_edges)

            family_records = {}
            family_shapes  = {}
            for fam in args.families:
                trials, shapes = [], {}
                for n in range(1, args.order_max+1):
                    try:
                        pars, mu = fit_family(
                            bin_edges, H, fam, n,
                            None if blind is None else blind[0],
                            None if blind is None else blind[1]
                        )
                        trials.append(pars); shapes[n] = mu
                    except Exception:
                        continue
                if not trials:
                    continue
                best = pick_order_by_deltaNLL(trials)
                family_records[fam] = {"best": best, "all": trials}
                family_shapes[fam]  = shapes

            if not family_records:
                print(f"[warn] {varname}: cat={c}: no successful fits.")
                continue

            best_fam = min(
                family_records.items(),
                key=lambda kv: kv[1]["best"]["chi2"]/max(kv[1]["best"]["ndof"],1)
            )[0]
            best_rec = family_records[best_fam]["best"]
            best_mu  = family_shapes[best_fam][best_rec["order"]]

            results[c] = {
                "range": [float(vmin), float(vmax)],
                "bin_edges": bin_edges.tolist(),
                "families": family_records,
                "chosen": {"family": best_fam, **best_rec}
            }

            # plot
            out_png = os.path.join(args.outdir, f"nonres_{varname}_cat{c}.png")
            plot_with_ratio(
                "mγγ" if varname=="mgg" else "mjj",
                c, centers, H, Herr, bin_edges,
                best_fam, best_rec, best_mu, family_shapes, args,
                None if blind is None else blind[0],
                None if blind is None else blind[1],
                out_png
            )
            print("Wrote", out_png)
        return results

    # ---- run mgg (blinded) ----
    all_results["mgg"] = fit_plot_variable(
        "mgg", per_cat_mgg, args.mgg_min, args.mgg_max, args.mgg_bins,
        blind=(args.blind_lo, args.blind_hi)
    )

    # ---- run mjj (unblinded) ----
    if args.do_mjj:
        all_results["mjj"] = fit_plot_variable(
            "mjj", per_cat_mjj, args.mjj_min, args.mjj_max, args.mjj_bins,
            blind=None  # no blinding
        )

    # save everything
    out_json = os.path.join(args.outdir, "nonres_envelope_results.json")
    with open(out_json, "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved", out_json)

if __name__ == "__main__":
    main()
