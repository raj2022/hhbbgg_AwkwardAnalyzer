# # plot_stacks_multiyear.py

# import os, re
# import numpy as np
# import matplotlib
# matplotlib.use("Agg")

# import uproot
# import matplotlib.pyplot as plt
# import mplhep as hep
# from cycler import cycler

# from hist import Hist, Stack
# import boost_histogram as bh

# from variables import vardict, regions as REGION_LIST, variables_common
# from normalisation import getLumi

# # ------------------- Styling -------------------
# hep.style.use("CMS")
# plt.rcParams["axes.prop_cycle"] = cycler(
#     color=[
#         "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
#         "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd",
#     ]
# )

# # ------------------- Axis titles -------------------
# xaxis_titles = {
#     "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
#     "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
#     "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
#     "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
#     "diphoton_pt": r"$p_T^{\gamma\gamma}$ [GeV]",
#     "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
# }

# blind_vars = ["dibjet_mass", "diphoton_mass"]

# # ------------------- Lumi label -------------------
# def lumi_label(years):
#     return f"{sum(getLumi(y) for y in years):.2f}"

# # ------------------- Safe hist ops -------------------
# def ensure_weight_hist(h_in: Hist) -> Hist:
#     axes = []
#     for ax in h_in.axes:
#         edges = getattr(ax, "edges", None)
#         if edges is not None:
#             axes.append(bh.axis.Variable(edges))
#         else:
#             axes.append(bh.axis.Regular(ax.size, ax.edges[0], ax.edges[-1]))
#     h_out = Hist(*axes, storage=bh.storage.Weight())
#     view_out = h_out.view()
#     view_in = h_in.view()
#     view_out.value[...] = view_in.value
#     view_out.variance[...] = (
#         view_in.variance if view_in.variance is not None else view_in.value
#     )
#     return h_out

# def add_hist_safe(a: Hist | None, b: Hist) -> Hist:
#     b = ensure_weight_hist(b)
#     if a is None:
#         return b
#     a = ensure_weight_hist(a)
#     a += b
#     return a

# # ------------------- Ratio (UNCHANGED from original) -------------------
# def get_ratio(hist_a, hist_b):
#     edges_a = hist_a.axes.edges[0]
#     edges_b = hist_b.axes.edges[0]
#     if not np.array_equal(edges_a, edges_b):
#         raise ValueError("Histogram binning mismatch")

#     a = np.where(hist_a.values() < 0, 0.0, hist_a.values())
#     b = np.where(hist_b.values() < 0, 0.0, hist_b.values())

#     ea = np.sqrt(a)
#     eb = np.sqrt(b)

#     ratio = np.divide(a, b, out=np.zeros_like(a), where=b != 0)

#     ratio_hist = Hist(hist_a.axes[0], storage=bh.storage.Double())
#     ratio_hist[...] = ratio

#     with np.errstate(divide="ignore", invalid="ignore"):
#         ra = np.divide(ea, a, out=np.zeros_like(ea), where=a != 0)
#         rb = np.divide(eb, b, out=np.zeros_like(eb), where=b != 0)

#     ratio_err = ratio * np.sqrt(ra**2 + rb**2)
#     return ratio_hist, ratio_err

# # ------------------- Blinding -------------------
# def blind_data(hist, blind, start_blind=110, stop_blind=130):
#     if not blind:
#         return hist
#     h = hist.copy()
#     for i in range(h.axes[0].size):
#         c = h.axes[0].centers[i]
#         if start_blind <= c <= stop_blind:
#             h[i] = 0.0
#     return h

# # ------------------- ROOT helpers -------------------
# def list_top_dirs(upfile):
#     out = []
#     for key in upfile.keys():
#         name = key.split(";")[0]
#         try:
#             if hasattr(upfile[name], "keys"):
#                 out.append(name)
#         except KeyError:
#             pass
#     return out

# def dir_to_base(name: str) -> str | None:
#     if re.search(r"(^|_)Data(_|$)", name, re.IGNORECASE):
#         return "Data"

#     n = re.sub(r"(2022|2023|2024)", "", name)
#     n = re.sub(r"(preEE|postEE|preBPix|postBPix|Era[A-Z]|merged|NOTAG)", "", n)
#     n = re.sub(r"__+", "_", n).strip("_")

#     patterns = {
#         "GGJets": r"GGJets",
#         "GluGluHToGG": r"GluGluHToGG",
#         "VBFHToGG": r"VBFHToGG",
#         "VHToGG": r"VHToGG",
#         "ttHToGG": r"ttHToGG",
#         "DDQCDGJET": r"DDQCDGJET|GGJets_(high|low)_Rescaled",
#         "TTGG": r"TTGG",
#         "TTG": r"TTG",
#     }

#     for base, pat in patterns.items():
#         if re.search(pat, n, re.IGNORECASE):
#             return base

#     if n.startswith("NMSSM_"):
#         return n

#     return None

# def group_by_base_all_years(root_files):
#     groups = {}
#     for year, up in root_files.items():
#         for d in list_top_dirs(up):
#             base = dir_to_base(d)
#             if base is None:
#                 continue
#             groups.setdefault(base, [])
#             groups[base].append((year, d))
#     return groups

# def get_histogram(upfile, path, label=None):
#     h = Hist(upfile[path])
#     if label:
#         h.name = label
#     return h

# # ------------------- Plotter -------------------
# def stack1d_histograms(root_files, years, output_dir, blind=False):

#     groups = group_by_base_all_years(root_files)

#     mc_bases = [
#         "GGJets", "GluGluHToGG", "VBFHToGG",
#         "VHToGG", "ttHToGG", "DDQCDGJET",
#         "TTGG", "TTG"
#     ]

#     jobs = [(r, v) for r in REGION_LIST for v in variables_common[r]]

#     for region, var in jobs:
#         hname = vardict[var]

#         # -------- Data --------
#         data_hist = None
#         for year, d in groups.get("Data", []):
#             up = root_files[year]
#             path = f"{d}/{region}/{hname}"
#             if path in up:
#                 data_hist = add_hist_safe(
#                     data_hist,
#                     get_histogram(up, path, "Data")
#                 )
#         if data_hist is None:
#             continue

#         # -------- MC --------
#         mc_merged = []
#         for base in mc_bases:
#             hsum = None
#             for year, d in groups.get(base, []):
#                 up = root_files[year]
#                 path = f"{d}/{region}/{hname}"
#                 if path in up:
#                     hsum = add_hist_safe(
#                         hsum,
#                         get_histogram(up, path, base)
#                     )
#             if hsum is not None:
#                 hsum.name = base
#                 mc_merged.append(hsum)
#         if not mc_merged:
#             continue

#         # -------- Plot --------
#         dyn_w = max(11, int(1.5 * len(mc_merged)))
#         fig, (ax, ax_ratio) = plt.subplots(
#             2, 1, figsize=(dyn_w, 12),
#             gridspec_kw={"height_ratios": [3, 1]},
#             sharex=True
#         )
#         fig.subplots_adjust(hspace=0.05)

#         do_blind = blind and (var in blind_vars)
#         data_plot = blind_data(data_hist, do_blind)

#         data_plot.plot(
#             ax=ax, histtype="errorbar",
#             yerr=True, xerr=True,
#             color="black", label="Data",
#             flow="sum"
#         )

#         Stack(*mc_merged).plot(
#             ax=ax, stack=True,
#             histtype="fill",
#             flow="sum",
#             sort="yield"
#         )

#         mc_sum = None
#         for h in mc_merged:
#             mc_sum = add_hist_safe(mc_sum, h)

#         ratio, rerr = get_ratio(data_hist, mc_sum)
#         ratio_plot = blind_data(ratio, do_blind)

#         ratio_plot.plot(
#             ax=ax_ratio,
#             histtype="errorbar",
#             yerr=rerr, xerr=True,
#             color="black",
#             flow="sum"
#         )

#         ax_ratio.axhline(1, linestyle="--", color="gray")
#         ax_ratio.set_ylim(0, 3)
#         ax_ratio.set_ylabel("Data / MC")
#         ax_ratio.set_xlabel(xaxis_titles.get(var, var.replace("_", " ")))

#         ax.set_yscale("log")
#         ax.set_ylim(0.1, 1e8)
#         ax.set_ylabel("Events")

#         hep.cms.label(
#             "",
#             ax=ax,
#             lumi=lumi_label(years),
#             loc=0,
#             llabel="Work in progress",
#             com=13.6
#         )

#         ax.legend(ncol=2, fontsize=16)
#         ax.set_xlabel("")

#         outdir = os.path.join(output_dir, region)
#         os.makedirs(outdir, exist_ok=True)

#         plt.tight_layout()
#         plt.savefig(os.path.join(outdir, f"{var}.pdf"), bbox_inches="tight")
#         plt.savefig(os.path.join(outdir, f"{var}.png"), bbox_inches="tight")
#         plt.close()

#         print(f"[OK] {region}/{var}")

# # ------------------- main -------------------
# def main():

#     YEARS = ["2022", "2023"]   # <<< CHANGE HERE

#     root_files = {
#         "2022": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2022_All/hhbbgg_analyzer-v2-histograms.root"),
#         "2023": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/2023_All/hhbbgg_analyzer-v2-histograms.root"),
#         "2024": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2024_All/hhbbgg_analyzer-v2-histograms.root"),
#     }

#     root_files = {y: root_files[y] for y in YEARS}

#     tag = "-".join(y[2:] for y in YEARS)
#     outdir = f"stack_plots/{tag}"
#     os.makedirs(outdir, exist_ok=True)

#     stack1d_histograms(root_files, YEARS, outdir, blind=False)

# if __name__ == "__main__":
#     main()


# plot_stacks_multiyear.py

import os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")

import uproot
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler

from hist import Hist, Stack
import boost_histogram as bh

from variables import vardict, regions as REGION_LIST, variables_common

# ============================================================
# Styling (UNCHANGED)
# ============================================================
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
        "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd",
    ]
)

# ============================================================
# Lumi (EXPLICIT, label only)
# ============================================================
LUMI_2022 = {
    "C": 5.0104,
    "D": 2.9700,
    "E": 5.8070,
    "F": 17.7819,
    "G": 3.0828,
}
LUMI_2023 = {
    "C": 17.794,  # preBPix
    "D": 9.451,   # postBPix
}

def total_lumi(years):
    lumi = 0.0
    if "2022" in years:
        lumi += sum(LUMI_2022.values())
    if "2023" in years:
        lumi += sum(LUMI_2023.values())
    return lumi

# ============================================================
# Legend map (RESTORED)
# ============================================================
legend = {
    "Data": "Data",
    "GGJets": r"$\gamma\gamma$+jets",
    "GluGluHToGG": r"$gg\to H\to\gamma\gamma$",
    "VBFHToGG": r"$VBF\,H\to\gamma\gamma$",
    "VHToGG": r"$V\,H\to\gamma\gamma$",
    "ttHToGG": r"$t\bar t H\to\gamma\gamma$",
    "TTGG": r"$t\bar t + \gamma\gamma$",
    "TTG": r"$t\bar t \to \gamma$",
    "DDQCDGJET": r"DDQCDGJET",
    "NMSSM_X500_Y150": r"$NMSSM_{500,150}$",
}

# ============================================================
# Axis titles (UNCHANGED)
# ============================================================
xaxis_titles = {
    "bbgg_eta": r"$\eta_{b\bar{b}\gamma\gamma}$",
    "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
    "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
}

blind_vars = ["diphoton_mass", "dibjet_mass"]

# ============================================================
# Histogram utilities (UNCHANGED)
# ============================================================
def ensure_weight_hist(h):
    axes = []
    for ax in h.axes:
        axes.append(bh.axis.Variable(ax.edges))
    hout = Hist(*axes, storage=bh.storage.Weight())
    vout = hout.view()
    vin = h.view()
    vout.value[...] = vin.value
    vout.variance[...] = (
        vin.variance if vin.variance is not None else vin.value
    )
    return hout

def add_hist_safe(a, b):
    b = ensure_weight_hist(b)
    if a is None:
        return b
    a = ensure_weight_hist(a)
    a += b
    return a

# ============================================================
# Ratio (IDENTICAL to original)
# ============================================================
def get_ratio(hist_a, hist_b):
    a = np.where(hist_a.values() < 0, 0.0, hist_a.values())
    b = np.where(hist_b.values() < 0, 0.0, hist_b.values())

    ea = np.sqrt(a)
    eb = np.sqrt(b)

    ratio = np.divide(a, b, out=np.zeros_like(a), where=b != 0)
    ratio_hist = Hist(hist_a.axes[0], storage=bh.storage.Double())
    ratio_hist[...] = ratio

    with np.errstate(divide="ignore", invalid="ignore"):
        ra = np.divide(ea, a, out=np.zeros_like(ea), where=a != 0)
        rb = np.divide(eb, b, out=np.zeros_like(eb), where=b != 0)

    ratio_err = ratio * np.sqrt(ra**2 + rb**2)
    return ratio_hist, ratio_err

def blind_data(hist, blind, lo=110, hi=130):
    if not blind:
        return hist
    h = hist.copy()
    for i in range(h.axes[0].size):
        c = h.axes[0].centers[i]
        if lo <= c <= hi:
            h[i] = 0.0
    return h

# ============================================================
# ROOT helpers (MINIMAL CHANGE)
# ============================================================
def list_top_dirs(up):
    return [k.split(";")[0] for k in up.keys()
            if hasattr(up[k.split(";")[0]], "keys")]

# def dir_to_base(name):
#     if re.search(r"(^|_)Data(_|$)", name):
#         return "Data"
#     n = re.sub(r"(2022|2023|preEE|postEE|preBPix|postBPix|Era[A-Z])", "", name)
#     for k in legend:
#         if k in n:
#             return k
#     return None
def dir_to_base(name):
    n = name.lower()

    if "data" in n:
        return "Data"

    patterns = {
        "GGJets": "ggjets",
        "GluGluHToGG": "glugluhtogg",
        "VBFHToGG": "vbfhtogg",
        "VHToGG": "vhtogg",
        "ttHToGG": "tthtogg",
        "TTGG": "ttgg",
        "TTG": "ttg",
        "DDQCDGJET": "ddqcdgjet",
    }

    for base, pat in patterns.items():
        if pat in n:
            return base

    # NMSSM signals
    if "nmssm" in n:
        return "_".join(name.split("_")[:3])

    return None


def group_all_years(root_files):
    groups = {}
    for year, up in root_files.items():
        for d in list_top_dirs(up):
            base = dir_to_base(d)
            if base:
                groups.setdefault(base, []).append((year, d))
    return groups

# ============================================================
# Plotter (STRUCTURE IDENTICAL TO ORIGINAL)
# ============================================================
def stack1d_histograms(root_files, years, output_dir, blind=False):

    groups = group_all_years(root_files)

    mc_bases = [
        "GGJets", "GluGluHToGG", "VBFHToGG",
        "VHToGG", "ttHToGG",
        "DDQCDGJET", "TTGG", "TTG",
    ]
    signal_bases = ["NMSSM_X500_Y150"]

    jobs = [(r, v) for r in REGION_LIST for v in variables_common[r]]

    for region, var in jobs:
        hname = vardict[var]

        # ---------------- Data ----------------
        data_hist = None
        for y, d in groups.get("Data", []):
            up = root_files[y]
            path = f"{d}/{region}/{hname}"
            if path in up:
                data_hist = add_hist_safe(data_hist, Hist(up[path]))
        if data_hist is None:
            continue

        # ---------------- MC ----------------
        mc_hists = []
        for base in mc_bases:
            hsum = None
            for y, d in groups.get(base, []):
                up = root_files[y]
                path = f"{d}/{region}/{hname}"
                if path in up:
                    hsum = add_hist_safe(hsum, Hist(up[path]))
            if hsum is not None:
                hsum.name = legend[base]
                mc_hists.append(hsum)
        if not mc_hists:
            continue

        # ---------------- Signal ----------------
        sig_hists = []
        for base in signal_bases:
            hsum = None
            for y, d in groups.get(base, []):
                up = root_files[y]
                path = f"{d}/{region}/{hname}"
                if path in up:
                    h = Hist(up[path]) 
                    hsum = add_hist_safe(hsum, h)
            if hsum is not None:
                hsum.name = legend[base]
                sig_hists.append(hsum)

        # ---------------- Plot ----------------
        fig, (ax, axr) = plt.subplots(
            2, 1, figsize=(12, 12),
            gridspec_kw={"height_ratios": [3, 1]},
            sharex=True
        )
        fig.subplots_adjust(hspace=0.02)

        do_blind = blind and (var in blind_vars)
        data_plot = blind_data(data_hist, do_blind)

        data_plot.plot(
            ax=ax, histtype="errorbar",
            yerr=True, xerr=True,
            color="black", label="Data",
            flow="sum"
        )

        Stack(*mc_hists).plot(
            ax=ax, stack=True,
            histtype="fill",
            flow="sum",
            sort="yield"
        )

        # for s in sig_hists:
        #     s.plot(ax=ax, histtype="step", linewidth=2, color="red")
        for s in sig_hists:
            s.plot(
                ax=ax, histtype="step",
                linewidth=2, linestyle="--",
                color="red", label=s.name
            )

        mc_sum = None
        for h in mc_hists:
            mc_sum = add_hist_safe(mc_sum, h)

        ratio, rerr = get_ratio(data_hist, mc_sum)
        ratio_plot = blind_data(ratio, do_blind)

        ratio_plot.plot(
            ax=axr, histtype="errorbar",
            yerr=rerr, xerr=True,
            color="black",
            flow="sum"
        )

        axr.axhline(1, ls="--", color="gray")
        axr.set_ylim(0, 3)
        axr.set_ylabel("Data / MC")
        axr.set_xlabel(xaxis_titles.get(var, var))

        ax.set_yscale("log")
        ax.set_ylim(0.1, 1e8)
        ax.set_ylabel("Events")
        ax.set_xlabel("")


        hep.cms.label(
            "",
            ax=ax,
            lumi=f"{total_lumi(years):.2f}",
            llabel="Work in progress",
            com=13.6
        )

        # ax.legend(ncol=2, fontsize=14)
        handles, labels = ax.get_legend_handles_labels()

        seen = set()
        uniq_h, uniq_l = [], []
        for h, l in zip(handles, labels):
            if l not in seen:
                uniq_h.append(h)
                uniq_l.append(l)
                seen.add(l)

        # ax.legend(uniq_h, uniq_l, ncol=2, fontsize=14)
        ax.legend(
            uniq_h,
            uniq_l,
            loc="upper right",
            ncol=2,
            fontsize=14,
            frameon=False
        )



        outdir = os.path.join(output_dir, region)
        os.makedirs(outdir, exist_ok=True)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"{var}.pdf"))
        plt.savefig(os.path.join(outdir, f"{var}.png"))
        plt.close()

        print(f"[OK] {region}/{var}")

# ============================================================
# main
# ============================================================
# # ------------------- main -------------------
def main():

    YEARS = ["2022", "2023"]   # <<< CHANGE HERE

    root_files = {
        "2022": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2022_All/hhbbgg_analyzer-v2-histograms.root"),
        "2023": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2023_All/hhbbgg_analyzer-v2-histograms.root"),
        "2024": uproot.open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2024_All/hhbbgg_analyzer-v2-histograms.root"),
    }

    root_files = {y: root_files[y] for y in YEARS}

    tag = "-".join(y[2:] for y in YEARS)
    outdir = f"stack_plots/{tag}"
    os.makedirs(outdir, exist_ok=True)

    stack1d_histograms(root_files, YEARS, outdir, blind=False)

if __name__ == "__main__":
    main()
