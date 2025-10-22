#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Headless plotting (prevents Qt/GL errors on lxplus)
import matplotlib
matplotlib.use("Agg")

import os
import argparse
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# ---------------- Plot style (reference-like) ----------------
plt.rcParams.update({
    "figure.figsize": (8.6, 5.9),
    "figure.dpi": 120,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.titlesize": 18,
    "axes.labelsize": 13,
    "legend.fontsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "lines.linewidth": 2.2,
    "savefig.bbox": "tight",
})

# pleasant, high-contrast colors for the X curves (X300..X1000)
X_COLORS = ["#000000", "#D55E00", "#009E73", "#0072B2", "#F0E442", "#CC79A7", "#56B4E9", "#798E52"]
BKG_FACE, BKG_EDGE = "#B0B0B0", "#4D4D4D"

# ---------------- Canonical column names ----------------
MJJGG_COL = "Res_HHbbggCandidate_mass"               # M(jjγγ)
MJJ_CAND  = ["Res_dijet_mass", "mjj", "dijet_mass"]  # M(jj)
MGG_CAND  = ["diphoton_mass", "mgg", "Diphoton_mass", "Hgg_mass"]  # M(γγ)

# photon kinematics (for mgg rebuild)
PHO_LEAD = {"pt": ["lead_pho_pt","lead_pt","pho_lead_pt"],
            "eta":["lead_pho_eta","lead_eta","pho_lead_eta"],
            "phi":["lead_pho_phi","lead_phi","pho_lead_phi"]}
PHO_SUB  = {"pt": ["sublead_pho_pt","sublead_pt","pho_sublead_pt"],
            "eta":["sublead_pho_eta","sublead_eta","pho_sublead_eta"],
            "phi":["sublead_pho_phi","sublead_phi","pho_sublead_phi"]}

def first_present(allcols, cand):
    for c in cand:
        if c in allcols: return c
    return None

def _vec_mgg_from_photons(pt1, eta1, phi1, pt2, eta2, phi2):
    # All inputs are numpy arrays (float64/float32)
    px1, py1 = pt1*np.cos(phi1), pt1*np.sin(phi1)
    px2, py2 = pt2*np.cos(phi2), pt2*np.sin(phi2)
    E1, pz1  = pt1*np.cosh(eta1), pt1*np.sinh(eta1)
    E2, pz2  = pt2*np.cosh(eta2), pt2*np.sinh(eta2)
    E, px, py, pz = E1+E2, px1+px2, py1+py2, pz1+pz2
    m2 = E*E - (px*px + py*py + pz*pz)
    return np.sqrt(np.maximum(m2, 0.0), dtype=np.float64)

def _np(arr):
    """Arrow chunked array -> numpy float64, NaNs where invalid."""
    if arr is None: return None
    a = arr.to_numpy(zero_copy_only=False)
    return a.astype(np.float64, copy=False)

def stream_hist_mtilde(parquet_path, bins, mh, my, debug=False):
    """
    Stream a parquet file and return (hist_counts, entries).
    Computes M̃_X = M(jjγγ) - M(γγ) - M(jj) + mH + mY.
    Uses existing mgg if present; otherwise rebuilds from photon kinematics.
    """
    pf = pq.ParquetFile(parquet_path)
    schema = pf.schema_arrow
    cols_all = set(name for name in schema.names)

    if MJJGG_COL not in cols_all:
        if debug: print(f"[MISS] {parquet_path}: missing {MJJGG_COL}")
        return np.zeros(len(bins)-1, dtype=np.float64), 0

    mjj_col = first_present(cols_all, MJJ_CAND)
    mgg_col = first_present(cols_all, MGG_CAND)

    needed = [MJJGG_COL]
    if mjj_col: needed.append(mjj_col)
    pho_cols = None
    if mgg_col:
        needed.append(mgg_col)
    else:
        # need photon columns to rebuild
        lead_pt  = first_present(cols_all, PHO_LEAD["pt"])
        lead_eta = first_present(cols_all, PHO_LEAD["eta"])
        lead_phi = first_present(cols_all, PHO_LEAD["phi"])
        sub_pt   = first_present(cols_all, PHO_SUB["pt"])
        sub_eta  = first_present(cols_all, PHO_SUB["eta"])
        sub_phi  = first_present(cols_all, PHO_SUB["phi"])
        pho_cols = [lead_pt, lead_eta, lead_phi, sub_pt, sub_eta, sub_phi]
        if not all(pho_cols):
            if debug: print(f"[MISS] {parquet_path}: no mgg and insufficient photon columns")
            return np.zeros(len(bins)-1, dtype=np.float64), 0
        needed.extend(pho_cols)

    # Streaming accumulation
    hist = np.zeros(len(bins)-1, dtype=np.float64)
    n_entries = 0

    for batch in pf.iter_batches(columns=needed, batch_size=200_000):
        tbl = pa.Table.from_batches([batch])
        mjjgg = _np(tbl.column(MJJGG_COL))
        mjj   = _np(tbl.column(mjj_col)) if mjj_col else None

        if mgg_col:
            mgg = _np(tbl.column(mgg_col))
        else:
            pt1  = _np(tbl.column(pho_cols[0])); eta1 = _np(tbl.column(pho_cols[1])); phi1 = _np(tbl.column(pho_cols[2]))
            pt2  = _np(tbl.column(pho_cols[3])); eta2 = _np(tbl.column(pho_cols[4])); phi2 = _np(tbl.column(pho_cols[5]))
            mgg  = _vec_mgg_from_photons(pt1, eta1, phi1, pt2, eta2, phi2)

        if mjj is None:
            if debug: print(f"[WARN] {parquet_path}: mjj missing in streamed batch")
            continue

        mtilde = mjjgg - mgg - mjj + float(mh) + float(my)
        mask = np.isfinite(mtilde)
        if not np.any(mask): 
            continue
        h, _ = np.histogram(mtilde[mask], bins=bins)
        hist += h.astype(np.float64, copy=False)
        n_entries += int(mask.sum())

    return hist, n_entries

def unit_hist_from_counts(counts):
    s = counts.sum()
    if s > 0: counts = counts / s
    return counts

def main():
    ap = argparse.ArgumentParser(description="Memory-safe M̃_X plotter with GGJets overlay.")
    ap.add_argument("--sig-tpl", required=True, help="Signal parquet template with {m} and {y}.")
    ap.add_argument("--bkg-file", type=str, default=None,
                    help="Background parquet, e.g. ../../output_root/v3_production/samples/postEE/GGJets.parquet")
    ap.add_argument("--y", type=int, default=150)
    ap.add_argument("--xmin", type=int, default=300)
    ap.add_argument("--xmax", type=int, default=1000)
    ap.add_argument("--xstep", type=int, default=100)
    ap.add_argument("--mh", type=float, default=125.0)
    ap.add_argument("--mt-min", type=float, default=200.0)
    ap.add_argument("--mt-max", type=float, default=1200.0)
    ap.add_argument("--nbins", type=int, default=200)
    ap.add_argument("--ellipse", action="store_true")
    ap.add_argument("--outdir", type=str, default=".")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    # sanitize possible typos in path (trailing comma/space)
    if args.bkg_file:
        args.bkg_file = args.bkg_file.strip().rstrip(",")

    bins   = np.linspace(args.mt_min, args.mt_max, args.nbins + 1)
    centers = 0.5*(bins[:-1] + bins[1:])
    x_vals = list(range(args.xmin, args.xmax + 1, args.xstep))

    fig, ax = plt.subplots()

    # ---------- Background (streamed, hatched fill) ----------
    if args.bkg_file and os.path.exists(args.bkg_file):
        b_counts, b_entries = stream_hist_mtilde(args.bkg_file, bins, args.mh, args.y, debug=args.debug)
        if b_entries > 0:
            b_norm = unit_hist_from_counts(b_counts)
            ax.fill_between(centers, b_norm, step="mid",
                            facecolor=BKG_FACE, edgecolor=BKG_EDGE,
                            hatch="///", linewidth=1.5, alpha=0.35, label=r"$\gamma\gamma$+jets")
            if args.debug:
                print(f"[BKG] {args.bkg_file} entries={b_entries:,}")
        else:
            print(f"[WARN] Background produced no entries: {args.bkg_file}")
    else:
        if args.bkg_file:
            print(f"[WARN] Background file not found: {args.bkg_file}")

    # ---------- Signals (each file streamed) ----------
    total_entries = 0
    found_any = False

    for i, X in enumerate(x_vals):
        fpath = args.sig_tpl.format(m=X, y=args.y)
        if not os.path.exists(fpath):
            if args.debug: print(f"[MISS] X={X}, Y={args.y}: {fpath}")
            continue

        counts, n_ent = stream_hist_mtilde(fpath, bins, args.mh, args.y, debug=args.debug)
        if n_ent == 0:
            if args.debug: print(f"[X={X}] no entries.")
            continue

        h_norm = unit_hist_from_counts(counts)
        color = X_COLORS[i % len(X_COLORS)]
        ax.step(centers, h_norm, where="mid", color=color, linewidth=2.2, label=f"X{X}")

        total_entries += n_ent
        found_any = True
        if args.debug:
            print(f"[SIG] X={X}: entries={n_ent:,}")

    if not found_any:
        print("[INFO] No signal histograms produced — check paths/columns.")
        return

    # ---------- Cosmetics (match the reference) ----------
    ax.set_title(r"$X \rightarrow YH$", pad=12)
    ax.set_xlim(args.mt_min, args.mt_max)
    ax.set_xlabel(r"reduced 4-body mass $\tilde{M}_X$ [GeV]")
    ax.set_ylabel("unit normalized")

    leg = ax.legend(title=f"Y{args.y}", ncols=2, frameon=True, loc="upper right")
    leg.get_title().set_fontsize(14)

    if args.ellipse:
        ymax = ax.get_ylim()[1]
        ell = Ellipse(xy=(300, 0.92*ymax), width=85, height=0.36*ymax,
                      edgecolor="black", facecolor="none",
                      linestyle=(0, (5, 5)), linewidth=2.0)
        ax.add_patch(ell)

    ax.margins(x=0.02, y=0.05)
    plt.tight_layout()

    if args.save:
        os.makedirs(args.outdir, exist_ok=True)
        tag = f"Y{args.y}_X{args.xmin}to{args.xmax}"
        png = os.path.join(args.outdir, f"MtildeX_likeRef_stream_{tag}.png")
        pdf = png.replace(".png", ".pdf")
        plt.savefig(png, dpi=600)
        plt.savefig(pdf)
        print(f"[Saved] {png}\n[Saved] {pdf}")

    # Do not plt.show() on headless nodes
    # plt.show()

if __name__ == "__main__":
    main()
