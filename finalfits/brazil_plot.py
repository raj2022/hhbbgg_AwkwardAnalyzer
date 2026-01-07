#!/usr/bin/env python3
"""
brazil_plot_cms_prelim.py — CMS-style Brazil plot with 'CMS Preliminary' header,
61.9 fb^-1 lumi, math-rendered number, and cleaned legend.

Usage example:
 python brazil_plot.py \
   --files datacard/../*.root \
   --masses 90 95 100 125 150 200 300 400 500 600 800 \
   --output brazil_mass1000_cms_prelim.pdf --logy --png
"""
import argparse, glob, re, os
import numpy as np
import uproot
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import NullFormatter, AutoMinorLocator, LogLocator
from matplotlib.lines import Line2D

# ---------------- rcParams: publication-friendly defaults ----------------
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 13,
    "axes.labelsize": 13,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.linewidth": 1.25,
    "figure.dpi": 300,
    "savefig.transparent": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.top": False,
    "ytick.right": False,
    "lines.solid_capstyle": "round",
    "mathtext.fontset": "dejavusans",
})

def parse_args():
    p = argparse.ArgumentParser(description="CMS-style Brazil plot with Preliminary header and 61.9 fb^-1 lumi.")
    p.add_argument("--files", nargs="+", required=True, help="ROOT files or quoted glob.")
    p.add_argument("--masses", nargs="+", type=float, default=None, help="Optional list of masses (same order as files).")
    p.add_argument("--xlabel", default=r"$m_X\ \mathrm{[GeV]}$", help="X axis label (LaTeX ok)")
    p.add_argument("--ylabel", default=r"$95\%\ \mathrm{CL\ limit\ on\ }\sigma\times\mathcal{B}\ \mathrm{[fb]}$", help="Y axis label (LaTeX ok)")
    p.add_argument("--output", default="brazil_mass_paper_cms_prelim.pdf", help="Output filename (prefer .pdf)")
    p.add_argument("--title", default=r"(Spin-0) $X \rightarrow HH \rightarrow \gamma\gamma b\bar{b}$", help="Optional top title text (LaTeX ok)")
    p.add_argument("--logy", action="store_true", help="Log y axis")
    p.add_argument("--cms-label", default="CMS", help="CMS label text")
    # Default lumi set to numeric 61.9 fb^-1 at 13.6 TeV (mathtext)
    p.add_argument("--lumi", default=r"$108.96\ \mathrm{fb}^{-1}\ (13.6\ \mathrm{TeV})$", help="Lumi text (LaTeX ok)")
    p.add_argument("--statonly", action="store_true", help="Add 'STAT ONLY' annotation")
    p.add_argument("--png", action="store_true", help="Also save PNG")
    p.add_argument("--width", type=float, default=9.0, help="Figure width in inches")
    p.add_argument("--height", type=float, default=7.0, help="Figure height in inches")
    p.add_argument("--vlines", nargs="*", type=float, default=[], help="Optional vertical dashed lines at given masses")
    return p.parse_args()

def expand_files(file_args):
    files = []
    for f in file_args:
        if any(ch in f for ch in "*?[]"):
            files += sorted(glob.glob(f))
        else:
            files.append(f)
    files = [os.path.abspath(x) for x in files if os.path.exists(x)]
    if not files:
        raise FileNotFoundError(f"No input files found for {file_args}")
    return files

def infer_mass_from_filename(fname):
    bn = os.path.basename(fname)
    m = re.search(r"(?:mass|m[_-]?|_)?([0-9]+(?:\.[0-9]+)?)", bn, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))
    nums = re.findall(r"([0-9]{1,6}(?:\.[0-9]+)?)", bn)
    return float(nums[-1]) if nums else None

def read_limits_from_file(fname):
    with uproot.open(fname) as f:
        tree = None
        for cand in ("limit", "tree", "limitTree", "limit0"):
            if cand in f:
                obj = f[cand]
                if hasattr(obj, "arrays") or hasattr(obj, "keys"):
                    tree = obj; break
        if tree is None:
            for key in f.keys(recursive=False):
                try:
                    obj = f[key]
                except Exception:
                    continue
                if hasattr(obj, "arrays") or hasattr(obj, "keys"):
                    tree = obj; break
        if tree is None:
            raise RuntimeError(f"No TTree-like object found in {fname}")

        try:
            available = set(list(tree.keys()))
        except Exception:
            available = set(tree.branch_names()) if hasattr(tree, "branch_names") else set()

        if "limit" not in available:
            raise RuntimeError(f"'limit' branch missing in {fname}. Available: {sorted(available)}")

        qname = None
        for qc in ("quantileExpected", "quantile", "quantile0"):
            if qc in available:
                qname = qc; break
        if qname is None:
            raise RuntimeError(f"No quantile branch found in {fname}. Available: {sorted(available)}")

        arr = tree.arrays(["limit", qname], library="np")
        return {"limit": arr["limit"], "quantile": arr[qname]}

def gather_limits(files):
    masses=[]; medians=[]; m1=[]; p1=[]; m2=[]; p2=[]; obs=[]
    for fn in files:
        ln = read_limits_from_file(fn)
        limits = ln["limit"]; q = ln["quantile"]
        def ex(qv):
            mask = np.isclose(q, qv, atol=1e-6)
            return float(np.mean(limits[mask])) if np.any(mask) else np.nan
        med = ex(0.5); p16 = ex(0.16); p84 = ex(0.84); p025 = ex(0.025); p975 = ex(0.975)
        obs_mask = np.isclose(q, -1.0, atol=1e-6)
        obs_val = float(np.mean(limits[obs_mask])) if np.any(obs_mask) else np.nan
        mass = infer_mass_from_filename(fn)
        if mass is None:
            raise RuntimeError(f"Cannot infer mass from {fn}; use --masses")
        masses.append(mass); medians.append(med); m1.append(p16); p1.append(p84)
        m2.append(p025); p2.append(p975); obs.append(obs_val)
    order = np.argsort(masses)
    return {"masses": np.array(masses)[order],
            "median": np.array(medians)[order],
            "minus1": np.array(m1)[order],
            "plus1": np.array(p1)[order],
            "minus2": np.array(m2)[order],
            "plus2": np.array(p2)[order],
            "observed": np.array(obs)[order]}

def make_brazil_plot(data, args):
    m = np.array(data["masses"], dtype=float)
    med = np.array(data["median"], dtype=float)
    low1 = np.array(data["minus1"], dtype=float)
    high1 = np.array(data["plus1"], dtype=float)
    low2 = np.array(data["minus2"], dtype=float)
    high2 = np.array(data["plus2"], dtype=float)
    # observed intentionally omitted

    # defensive sort
    order = np.argsort(m)
    m = m[order]; med = med[order]
    low1 = low1[order]; high1 = high1[order]
    low2 = low2[order]; high2 = high2[order]

    # Figure + reserved top for header
    # top_margin = 0.88
    top_margin = 0.90
    fig, ax = plt.subplots(figsize=(args.width, args.height))
    # fig.subplots_adjust(left=0.12, right=0.96, top=top_margin, bottom=0.12)
    fig.subplots_adjust(left=0.12, right=0.96, top=top_margin, bottom=0.12)


    # Colors (CMS-like)
    color_68 = "#4CAF50"   # green
    color_95 = "#FFEB3B"   # yellow
    grid_color = "#efefef"

    # filled bands (smooth fill_between)
    ax.fill_between(m, low2, high2, facecolor=color_95, edgecolor='none', zorder=1, alpha=1.0)
    ax.fill_between(m, low1, high1, facecolor=color_68, edgecolor='none', zorder=2, alpha=1.0)

    # expected median (dashed + open markers)
    ax.plot(m, med, linestyle='--', color='k', linewidth=1.9, zorder=5)
    ax.plot(m, med, linestyle='None', marker='o', markeredgecolor='k', markerfacecolor='white', markersize=5, zorder=6)

    # vertical dashed lines (optional)
    for vl in (args.vlines or []):
        ax.axvline(vl, color='0.6', linestyle='--', linewidth=0.9, zorder=0)

    # labels
    ax.set_xlabel(args.xlabel, fontsize=14, labelpad=10)
    ax.set_ylabel(args.ylabel, fontsize=14, labelpad=12)
    if args.logy:
        ax.set_yscale('log')

    # grid & ticks
    ax.grid(which='major', linestyle=':', linewidth=0.6, color=grid_color, alpha=0.95)
    ax.grid(which='minor', linestyle=':', linewidth=0.4, color=grid_color, alpha=0.6)
    ax.minorticks_on()
    ax.tick_params(which='major', length=6, width=1.05)
    ax.tick_params(which='minor', length=3, width=0.8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.4); spine.set_color('k')

    # header: CMS (bold) + Preliminary (italic) left; lumi numeric on right; title centered
    # baseline_y = min(0.94, top_margin + 0.02)
    baseline_y = 0.92
    x0 = 0.12
    # CMS bold
    fig.text(x0, baseline_y, args.cms_label, fontsize=26, fontweight='bold', ha='left', va='baseline')
    # Preliminary italic immediately to the right
    prelim_x = x0 + 0.1
    fig.text(prelim_x, baseline_y, "Preliminary", fontsize=14, style='italic', ha='left', va='baseline')
    # lumi (mathtext) rendered as provided; ensure user passes math-ready string or default does
    fig.text(0.98, baseline_y, args.lumi, fontsize=14, ha='right', va='baseline')
    # optional centered title below baseline
    if args.title:
        fig.text(0.5, baseline_y - 0.03, args.title, fontsize=14, ha='center', va='baseline')

    if args.statonly:
        ax.text(0.72, 0.72, "STAT ONLY", transform=ax.transAxes,
                fontsize=13, fontweight='bold', ha='center', color='0.15')

    # Legend: expected median, ±1σ, ±2σ — no observed curve
    patch_68 = Patch(facecolor=color_68, edgecolor='none', label=r'Expected limit $\pm1\sigma$')
    patch_95 = Patch(facecolor=color_95, edgecolor='none', label=r'Expected limit $\pm2\sigma$')
    median_handle = Line2D([0],[0], color='k', linestyle='--', linewidth=1.6, label=r'Expected 95% upper limit')
    handles = [median_handle, patch_68, patch_95]
    leg = ax.legend(handles=handles, loc='upper right',
                    frameon=True, facecolor='white', framealpha=0.98,
                    fontsize=11, borderpad=0.4, handlelength=1.2, handletextpad=0.6)
    leg.get_frame().set_edgecolor('lightgray'); leg.get_frame().set_linewidth(0.6)

    # x ticks
    ax.set_xticks(m)
    if len(m) > 10:
        ax.set_xticklabels([str(int(x)) for x in m], rotation=30, ha='right', fontsize=10)
    else:
        ax.set_xticklabels([str(int(x)) for x in m], fontsize=11)

    # y axis: set limits and ticks; for log scale use LogLocator for minor ticks
    if args.logy:
        data_ymin = np.nanmin(low2) if np.isfinite(np.nanmin(low2)) else 1e-3
        data_ymax = np.nanmax(high2) if np.isfinite(np.nanmax(high2)) else 1e3
        data_ymin = max(1e-12, data_ymin)
        ymin = max(1e-2, data_ymin * 0.5)
        ymax = min(1e4, data_ymax * 2.0)
        if ymin >= ymax:
            ymin, ymax = 1e-2, 1e4
        ax.set_ylim(ymin, ymax)

        decade_min = int(np.floor(np.log10(ymin)))
        decade_max = int(np.ceil(np.log10(ymax)))
        decades = [10.0**i for i in range(decade_min, decade_max+1)]
        ax.set_yticks(decades)
        ax.set_yticklabels([r"$10^{{{}}}$".format(int(np.log10(d))) for d in decades], fontsize=11)
        # use LogLocator for minor ticks on log axis
        ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10), numticks=12))
        ax.yaxis.set_minor_formatter(NullFormatter())
    else:
        ymin = np.nanmin(low2) if np.isfinite(np.nanmin(low2)) else None
        ymax = np.nanmax(high2) if np.isfinite(np.nanmax(high2)) else None
        if ymin is not None and ymax is not None and ymin > 0 and ymax > 0:
            ax.set_ylim(ymin * 0.6, ymax * 2.0)
        else:
            ax.autoscale(enable=True)

    # tight layout excluding header area
    # plt.tight_layout(rect=(0, 0, 1, top_margin - 0.01))

    # save outputs
    outdir = os.path.dirname(args.output)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)
    pdf_out = args.output if args.output.lower().endswith('.pdf') else os.path.splitext(args.output)[0] + '.pdf'
    # fig.savefig(pdf_out, dpi=300, bbox_inches='tight', pad_inches=0.05)
    fig.savefig(pdf_out, dpi=300)
    print(f"Saved PDF: {pdf_out}")
    if args.png:
        png_out = os.path.splitext(pdf_out)[0] + '.png'
        fig.savefig(png_out, dpi=600)
        # fig.savefig(png_out, dpi=600, bbox_inches='tight', pad_inches=0.02)
        print(f"Saved PNG: {png_out}")
    plt.close(fig)

def main():
    args = parse_args()
    files = expand_files(args.files)

    if args.masses:
        if len(args.masses) != len(files):
            raise ValueError("Number of masses must match number of files.")
        data = {"masses": [], "median": [], "minus1": [], "plus1": [], "minus2": [], "plus2": []}
        for f, mval in zip(files, args.masses):
            ln = read_limits_from_file(f)
            limits = ln["limit"]; q = ln["quantile"]
            def ex(qv):
                mask = np.isclose(q, qv, atol=1e-6)
                return float(np.mean(limits[mask])) if np.any(mask) else np.nan
            data["masses"].append(float(mval)); data["median"].append(ex(0.5))
            data["minus1"].append(ex(0.16)); data["plus1"].append(ex(0.84))
            data["minus2"].append(ex(0.025)); data["plus2"].append(ex(0.975))
        order = np.argsort(data["masses"])
        for k in data: data[k] = np.array(data[k])[order]
    else:
        data = gather_limits(files)

    make_brazil_plot(data, args)

if __name__ == "__main__":
    main()
