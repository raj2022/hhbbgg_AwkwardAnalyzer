#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, os, glob, json
import numpy as np
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
import ROOT
ROOT.gROOT.SetBatch(True); ROOT.TH1.AddDirectory(False)

# ------------------------ I/O helpers ------------------------
def expand_inputs(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += sorted(glob.glob(os.path.join(p, "*.parquet")))
        else:
            out += sorted(glob.glob(p))
    return out

def cat_col(paths, col, dtype="f8"):
    acc = []
    for p in paths:
        schema = set(pq.read_schema(p).names)
        if col not in schema:
            raise KeyError(f"{col} not in {p} (has: {sorted(schema)[:8]} ...)")
        t = pq.read_table(p, columns=[col]).to_pandas()[col].to_numpy(dtype)
        acc.append(t)
    return np.concatenate(acc) if acc else np.array([], dtype=dtype)

def cat_opt(paths, col, dtype="f8"):
    """Return concatenated column or None if any file lacks it."""
    acc = []
    for p in paths:
        schema = set(pq.read_schema(p).names)
        if col not in schema:
            return None
        t = pq.read_table(p, columns=[col]).to_pandas()[col].to_numpy(dtype)
        acc.append(t)
    return np.concatenate(acc) if acc else None

# ------------------------ histogram util ------------------------
def make_hist(vals, weights=None, nbins=50, lo=-0.98, hi=1.0, name="h"):
    h = ROOT.TH1F(name, f";#gamma MVA ID;A.U.", nbins, lo, hi)
    h.Sumw2()
    v = np.asarray(vals, dtype="f8")
    m = np.isfinite(v)
    v = v[m]
    if weights is None:
        w = np.ones_like(v, dtype="f8")
    else:
        w = np.asarray(weights, dtype="f8")
        w = w[m]
        w = np.where(np.isfinite(w), w, 0.0)
    counts, edges = np.histogram(v, bins=nbins, range=(lo, hi), weights=w)
    errs2, _      = np.histogram(v, bins=edges, weights=w*w)
    for i in range(1, nbins+1):
        h.SetBinContent(i, float(counts[i-1]))
        h.SetBinError(i,   float(np.sqrt(errs2[i-1])))
    if h.Integral() > 0:
        h.Scale(1.0/h.Integral())
    return h

def hist_to_arrays(h):
    nb = h.GetNbinsX()
    x = np.array([h.GetBinCenter(i) for i in range(1, nb+1)], dtype="f8")
    y = np.array([h.GetBinContent(i) for i in range(1, nb+1)], dtype="f8")
    e = np.array([h.GetBinError(i)   for i in range(1, nb+1)], dtype="f8")
    return x, y, e

# ------------------------ fitting + plotting ------------------------
def fit_hist(h, fit_rng=(-0.95, 0.98),
             model="[0]*exp([1]*x + [2]*x*x + [3]*x*x*x)"):
    """
    Default model: A * exp(b1 x + b2 x^2 + b3 x^3)  (positive-definite)
    """
    if h.Integral() <= 0 or h.GetEntries() == 0:
        return None
    f = ROOT.TF1("f_"+h.GetName(), model, fit_rng[0], fit_rng[1])

    # Seeds & sensible limits for photon-ID shapes
    f.SetParameters(0.1, -2.5, 0.0, 0.0)   # [0]=A, [1]=b1, [2]=b2, [3]=b3
    f.SetParLimits(0, 1e-6, 10.0)          # keep amplitude positive
    f.SetParLimits(1, -10.0, 0.0)          # negative slope
    f.SetParLimits(2, -5.0,  5.0)
    f.SetParLimits(3, -5.0,  5.0)

    h.Fit(f, "RSQ")  # R: use range, S: store result, Q: quiet
    return f

def draw_with_pull(ax_top, ax_bot, h, f, title, ymax=None, logy=False):
    x, y, e = hist_to_arrays(h)
    ax_top.errorbar(x, y, yerr=e, fmt="D", ms=4, lw=1, color="k", label=r"$\gamma$ MVA IDs")
    xs = np.linspace(h.GetXaxis().GetXmin(), h.GetXaxis().GetXmax(), 400)
    ys = np.array([f.Eval(xv) for xv in xs], dtype="f8") if f is not None else np.zeros_like(xs)
    ax_top.plot(xs, ys, lw=2, label="PDF" if f is not None else "no fit")
    ax_top.set_title(title); ax_top.set_ylabel("A.U."); ax_top.legend(frameon=False, loc="upper right")

    # y-axis control
    if ymax is None:
        fbin = np.array([f.Eval(xv) for xv in x], dtype="f8") if f is not None else np.zeros_like(x)
        ymax = 1.20 * float(np.nanmax([y.max() if y.size else 0.0,
                                       fbin.max() if f is not None else 0.0, 1e-3]))
    ax_top.set_ylim(1e-5 if logy else 0.0, ymax)
    if logy:
        ax_top.set_yscale("log")

    # pull
    if f is not None:
        fbin = np.array([f.Eval(xv) for xv in x], dtype="f8")
        with np.errstate(divide='ignore', invalid='ignore'):
            pull = (y - fbin) / np.where(e>0, e, np.inf)
    else:
        pull = np.zeros_like(x)
    ax_bot.axhline(0.0, lw=1, color="gray")
    ax_bot.plot(x, pull, lw=1.5)
    ax_bot.set_xlabel(r"$\gamma$ MVA ID"); ax_bot.set_ylabel("Pull"); ax_bot.set_ylim(-3.0, 3.0)
    ax_bot.grid(True, alpha=0.3)

# ------------------------ main ------------------------
def main():
    ap = argparse.ArgumentParser(description="Plot & fit photon MVA ID (EB/EE) with pull panels")
    ap.add_argument("-i","--inputs", nargs="+", required=True,
                    help="Parquet files or directories (DD template and/or fakes)")
    ap.add_argument("--which", choices=["lead","sublead","max","min"], default="max",
                    help="Which photon MVA to use")
    ap.add_argument("--nbins", type=int, default=50)
    ap.add_argument("--out", default="fit_mvaid")  # prefix for outputs
    ap.add_argument(
        "--model",
        default="[0]*exp([1]*x + [2]*x*x + [3]*x*x*x)",
        help='TF1 model; default is positive exp(poly3). '
             'You can pass e.g. "expo(0)+pol2(2)"'
    )
    ap.add_argument("--fit-min", type=float, default=-0.95, help="fit range min")
    ap.add_argument("--fit-max", type=float, default=0.98,  help="fit range max")
    ap.add_argument("--ymax",    type=float, default=None,  help="force y-axis max (A.U.)")
    ap.add_argument("--logy",    action="store_true",       help="log scale on top pads")
    args = ap.parse_args()

    paths = expand_inputs(args.inputs)
    if not paths:
        raise FileNotFoundError("No parquet inputs found.")

    # required columns
    lead_mva = cat_col(paths, "lead_mvaID")
    sub_mva  = cat_col(paths, "sublead_mvaID")

    # EB flags (optional → if missing, we’ll make an inclusive plot only)
    leadEB = cat_opt(paths, "lead_isScEtaEB")
    subEB  = cat_opt(paths, "sublead_isScEtaEB")

    # event weights (optional)
    weights = cat_opt(paths, "weight")

    # choose variable and EB/EE masks using the EB flag of the chosen photon
    if args.which == "lead":
        mva = lead_mva
        if leadEB is None:
            eb_mask = np.ones_like(mva, dtype=bool); ee_mask = np.zeros_like(mva, dtype=bool)
        else:
            eb_mask = (leadEB == 1); ee_mask = (leadEB == 0)

    elif args.which == "sublead":
        mva = sub_mva
        if subEB is None:
            eb_mask = np.ones_like(mva, dtype=bool); ee_mask = np.zeros_like(mva, dtype=bool)
        else:
            eb_mask = (subEB == 1); ee_mask = (subEB == 0)

    elif args.which == "max":
        idx_lead_is_max = (lead_mva >= sub_mva)
        mva = np.where(idx_lead_is_max, lead_mva, sub_mva)
        if (leadEB is None) or (subEB is None):
            eb_mask = np.ones_like(mva, dtype=bool); ee_mask = np.zeros_like(mva, dtype=bool)
        else:
            phoEB = np.where(idx_lead_is_max, leadEB, subEB)  # EB flag of the photon that supplies MAX
            eb_mask = (phoEB == 1); ee_mask = (phoEB == 0)

    else:  # "min"
        idx_lead_is_min = (lead_mva <= sub_mva)
        mva = np.where(idx_lead_is_min, lead_mva, sub_mva)
        if (leadEB is None) or (subEB is None):
            eb_mask = np.ones_like(mva, dtype=bool); ee_mask = np.zeros_like(mva, dtype=bool)
        else:
            phoEB = np.where(idx_lead_is_min, leadEB, subEB)  # EB flag of the photon that supplies MIN
            eb_mask = (phoEB == 1); ee_mask = (phoEB == 0)

    def pick(vals, w, m):
        if w is None: return vals[m], None
        return vals[m], w[m]

    mva_EB, w_EB = pick(mva, weights, eb_mask)
    mva_EE, w_EE = pick(mva, weights, ee_mask)

    # Histograms
    hEB = make_hist(mva_EB, weights=w_EB, nbins=args.nbins, name="h_EB")
    hEE = make_hist(mva_EE, weights=w_EE, nbins=args.nbins, name="h_EE")

    # Fits
    fit_rng = (args.fit_min, args.fit_max)
    fEB = fit_hist(hEB, fit_rng=fit_rng, model=args.model)
    fEE = fit_hist(hEE, fit_rng=fit_rng, model=args.model)

    # ---- Plot (two columns: EB | EE, each with a pull panel) ----
    fig = plt.figure(figsize=(12, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[3,1], hspace=0.06, wspace=0.28)
    axEB_top = fig.add_subplot(gs[0,0]); axEB_bot = fig.add_subplot(gs[1,0], sharex=axEB_top)
    axEE_top = fig.add_subplot(gs[0,1]); axEE_bot = fig.add_subplot(gs[1,1], sharex=axEE_top)

    draw_with_pull(axEB_top, axEB_bot, hEB, fEB, r"EB: $\gamma$ MVA", ymax=args.ymax, logy=args.logy)
    draw_with_pull(axEE_top, axEE_bot, hEE, fEE, r"EE: $\gamma$ MVA", ymax=args.ymax, logy=args.logy)

    pdf_out = f"{args.out}.pdf"
    png_out = f"{args.out}.png"
    fig.tight_layout(); fig.savefig(pdf_out); fig.savefig(png_out, dpi=180)
    print(f"[OK] Saved plots: {pdf_out}, {png_out}")

    # ---- Save hist+fits to ROOT file ----
    froot = ROOT.TFile(f"{args.out}.root", "RECREATE")
    hEB.Write(); hEE.Write()
    if fEB: fEB.Write("f_EB")
    if fEE: fEE.Write("f_EE")
    froot.Close()
    print(f"[OK] Wrote ROOT objects to: {args.out}.root")

    # Save fitted parameters (if any) for later reuse
    out_json = {
        "which": args.which,
        "model": args.model,
        "fit_range": list(fit_rng),
        "EB": {f"p{i}": fEB.GetParameter(i) for i in range(fEB.GetNpar())} if fEB else None,
        "EE": {f"p{i}": fEE.GetParameter(i) for i in range(fEE.GetNpar())} if fEE else None,
    }
    with open(f"{args.out}.json","w") as jf:
        json.dump(out_json, jf, indent=2)
    print(f"[OK] Saved fit params: {args.out}.json")

if __name__ == "__main__":
    main()
