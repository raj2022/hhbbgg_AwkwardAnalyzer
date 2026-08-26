# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# hhbbgg_Plotter.py

# Data/MC validation stack plots from the analyzer's merged histogram output.

# Reads sample/systematic/region/variable histogram paths (matching
# hhbbgg_analyzer_lxplus_par.py's output structure, which now includes an
# explicit systematic dimension -- "nominal" by default, or any
# weight-based/folder-based systematic label the analyzer produced).
# """
# import os, re
# import numpy as np
# import matplotlib
# matplotlib.use("Agg")
# import argparse

# import uproot
# from hist import Hist, Stack
# import boost_histogram as bh
# import matplotlib.pyplot as plt
# import mplhep as hep
# from cycler import cycler
# from normalisation import getLumi

# # --- import the SAME maps your analyzer used ---
# from variables import vardict, regions as REGION_LIST, variables_common  # <- key change

# # If you have a year/era-aware getLumi, replace this label.
# def lumi_label():
#     return "34.65"  # fb^-1 for 2022 only
#     # return "27.76"  # fb^-1 for 2023 only
#     # return "108.96"  # fb^-1 for 2024 only
#     # return 62.31  # fb^-1 for 2022-2023
#     # return "171.37"  # fb^-1 for 2022-2024

# # ------------------- Styling -------------------
# hep.style.use("CMS")
# plt.rcParams["axes.prop_cycle"] = cycler(
#     color=[
#         "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
#         "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd",
#     ]
# )

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
#     vals = np.asarray(h_in.values(), dtype="f8")
#     vars_ = h_in.variances()
#     vars_ = np.zeros_like(vals, dtype="f8") if vars_ is None else np.asarray(vars_, dtype="f8")
#     view = h_out.view()
#     view.value[...] = vals
#     view.variance[...] = vars_
#     return h_out

# def add_hist_safe(a: "Hist | None", b: Hist) -> Hist:
#     b = ensure_weight_hist(b)
#     if a is None:
#         return b
#     a = ensure_weight_hist(a)
#     a += b
#     return a

# # ------------------- ROOT helpers -------------------
# def list_top_dirs(upfile):
#     out = []
#     for key in upfile.keys():
#         name = key.split(";")[0]
#         try:
#             obj = upfile[name]
#             if hasattr(obj, "keys"):
#                 out.append(name)
#         except KeyError:
#             continue
#     return out


# def dir_to_base(name: str) -> "str | None":
#     n = name

#     # ------------------
#     # DATA (any era / year / merge)
#     # ------------------
#     if re.search(r'(^|_)Data(_|$)', n, re.IGNORECASE):
#         return "Data"

#     # ------------------
#     # Normalize name (remove era / year / merge noise)
#     # ------------------
#     n_clean = n
#     n_clean = re.sub(r"(2022|2023|2024)", "", n_clean, flags=re.IGNORECASE)
#     n_clean = re.sub(r"(preEE|postEE|preBPix|postBPix)", "", n_clean, flags=re.IGNORECASE)
#     n_clean = re.sub(r"(Era[A-Z])", "", n_clean, flags=re.IGNORECASE)
#     n_clean = re.sub(r"(merged|NOTAG)", "", n_clean, flags=re.IGNORECASE)
#     n_clean = re.sub(r"__+", "_", n_clean).strip("_")

#     # ------------------
#     # DD QCD (ALL variants)
#     # ------------------
#     # Regex instead of a fixed substring list, since the DD QCD+GJet
#     # template's naming varies across productions -- e.g.
#     # "DDQCDGJET_Rescaled" (2022, single C) vs "DDQCCDGJets" (2024,
#     # double C, no _Rescaled suffix). Mirrors the same fix applied to
#     # hhbbgg_analyzer_lxplus_par.py's is_dd_template(); a plain
#     # n.startswith("DDQCDGJET") check silently misses the newer naming.
#     if re.search(r"ddqc+dgjets?", n, re.IGNORECASE) or re.search(r"GGJets_(high|low)_Rescaled", n, re.IGNORECASE):
#         return "DDQCDGJET"

#     # ------------------
#     # Common MC bases (regex containment)
#     # ------------------
#     mc_patterns = {
#         "GGJets": r"GGJets",
#         "GJetPt20To40": r"GJet.*20.*40",
#         "GJetPt40": r"GJet.*40",
#         "GluGluHToGG": r"GluGluHToGG",
#         "VBFHToGG": r"VBFHToGG",
#         # FIXED: previously only matched the literal 2022/2023-style
#         # combined "VHToGG" name, silently dropping the 2024+ production's
#         # WmHtoGG/WpHtoGG/ZHtoGG (three separate directories, no combined
#         # "VHToGG" ever exists there) -- confirmed these three samples
#         # were completely absent from every 2024 Data/MC stack plot as a
#         # result. Same underlying naming-convention gap already fixed in
#         # normalisation.py's getXsec() and common/io_utils.py's
#         # is_resonant_bkg_dir()/group_of(); this is the third independent
#         # occurrence of it. All four variants combine into one "VHToGG"
#         # base so 2022/2023 (single combined sample) and 2024+ (three
#         # separate samples, summed) both land in the same stacked
#         # component.
#         "VHToGG": r"VHToGG|WmHToGG|WpHToGG|ZHToGG",
#         "ttHToGG": r"ttHToGG",
#         "TTGG": r"TTGG",
#         "TTG": r"TTG",
#         "QCD_PT-30to40": r"QCD.*30.*40",
#         "QCD_PT-30toInf": r"QCD.*30.*Inf",
#         "QCD_PT-40toInf": r"QCD.*40.*Inf",
#     }

#     for base, pat in mc_patterns.items():
#         if re.search(pat, n_clean, re.IGNORECASE):
#             return base

#     # ------------------
#     # NMSSM signals (keep exact)
#     # ------------------
#     if n_clean.startswith("NMSSM_"):
#         return n_clean

#     return None


# def group_by_base(upfile):
#     groups = {}
#     for d in list_top_dirs(upfile):
#         base = dir_to_base(d)
#         if base is None:
#             continue
#         groups.setdefault(base, []).append(d)
#     return {k: sorted(v) for k, v in groups.items()}


# def list_top_dirs_from_keys(all_keys) -> list:
#     """Extract top-level directory names by parsing an already-fetched
#     recursive key listing, instead of opening each top-level directory
#     individually via `upfile[name]` (see list_top_dirs above).

#     This is the actual fix for the multi-minute (or longer) hang: the
#     per-sample count hasn't grown, but each individual `upfile[name]`
#     open now has to materialize a directory object whose internal subtree
#     is ~4 levels deep and ~14x bigger (sample -> systematic -> region ->
#     variable, with weight-based systematics added). Over AFS/EOS, that
#     made each of the ~N individual opens dramatically slower even though
#     nothing else about the code changed. Parsing pre-fetched key strings
#     instead does zero additional file access.
#     """
#     tops = set()
#     for k in all_keys:
#         base = k.split(";")[0]
#         top = base.split("/")[0]
#         if top:
#             tops.add(top)
#     return sorted(tops)


# def group_by_base_from_keys(all_keys) -> dict:
#     groups = {}
#     for d in list_top_dirs_from_keys(all_keys):
#         base = dir_to_base(d)
#         if base is None:
#             continue
#         groups.setdefault(base, []).append(d)
#     return {k: sorted(v) for k, v in groups.items()}

# # ------------------- Read hist -------------------
# def get_histogram(upfile, path: str, label=None) -> Hist:
#     # path: Sample/Systematic/Region/<vardict[var]>
#     h = Hist(upfile[path])
#     if label is not None:
#         h.name = label
#     return h

# def sum_hist_list(hlist):
#     out = None
#     for h in hlist:
#         out = add_hist_safe(out, h)
#     return out

# # ------------------- Blinding & ratio -------------------
# def blind_data(hist, blind, start_blind=122, stop_blind=128):
#     if not blind:
#         return hist
#     blinded = hist.copy()
#     for b in range(blinded.axes[0].size):
#         c = blinded.axes[0].centers[b]
#         if start_blind <= c <= stop_blind:
#             blinded[b] = 0.0
#     return blinded

# def get_ratio(hist_a, hist_b):
#     edges_a = hist_a.axes.edges[0]
#     edges_b = hist_b.axes.edges[0]
#     if not np.array_equal(edges_a, edges_b):
#         raise ValueError("Histograms have different binning")
#     a = np.where(hist_a.values() < 0, 0.0, hist_a.values())
#     b = np.where(hist_b.values() < 0, 0.0, hist_b.values())
#     ea = np.sqrt(a)
#     eb = np.sqrt(b)
#     ratio = np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)
#     ratio_hist = Hist(hist_a.axes[0], storage=bh.storage.Double())
#     ratio_hist[...] = ratio
#     with np.errstate(divide="ignore", invalid="ignore"):
#         ra = np.divide(ea, a, out=np.zeros_like(ea, dtype=float), where=a != 0)
#         rb = np.divide(eb, b, out=np.zeros_like(eb, dtype=float), where=b != 0)
#     ratio_err = ratio * np.sqrt(ra**2 + rb**2)
#     return ratio_hist, ratio_err

# # ------------------- Config -------------------
# blind_vars = ["dibjet_mass", "diphoton_mass"]

# legend = {
#     "Data": "Data",
#     "GGJets": r"$\gamma\gamma$+jets $\times 1.4$",
#     "GJetPt20To40": r"$\gamma$+jets ($20< p_T < 40$)",
#     "GJetPt40": r"$\gamma$+jets ($p_T > 40$)",
#     "GluGluHToGG": r"$gg\to H\to\gamma\gamma$",
#     "VBFHToGG": r"$VBF\,H\to\gamma\gamma$",
#     "VHToGG": r"$V\,H\to\gamma\gamma$",
#     "ttHToGG": r"$t\bar t H\to\gamma\gamma$",
#     "DDQCDGJET": r"DDQCDGJET",
#     "TTGG": r"$t\bar t + \gamma\gamma$",
#     "TTG": r"$t\bar t \to \gamma$",
#     # signals
#     "NMSSM_X400_Y100": r"$NMSSM\_X_{400}\_Y_{100}\times 10$",
#     "NMSSM_X400_Y125": r"$NMSSM\_X_{400}\_Y_{125}\times 10$",
#     "NMSSM_X400_Y150": r"$NMSSM\_X_{400}\_Y_{150}\times 10$",
#     "NMSSM_X500_Y100": r"$NMSSM\_X_{500}\_Y_{100}\times 10$",
#     "NMSSM_X500_Y125": r"$NMSSM\_X_{500}\_Y_{125}\times 10$",
#     "NMSSM_X500_Y150": r"$NMSSM\_X_{500}\_Y_{150}\times 10$",
# }

# # Optional pretty x-axis names (fallback to raw var if missing)
# xaxis_titles = {
#     "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
#     "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
#     "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
#     "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
#     "diphoton_pt": r"$p_T^{\gamma\gamma}$ [GeV]",
#     "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
#     # ... add more if you want
# }

# # ------------------- Plotter -------------------
# def stack1d_histograms(up, output_dir, systematic="nominal", blind=True):
#     import time

#     # Single bulk read of every key in the file, done ONCE. This is the
#     # actual fix for the hang: everything else below (sample grouping,
#     # path-existence checks) is derived from this one in-memory result via
#     # pure string parsing, instead of each doing its own individual file
#     # access. The old code called `upfile[name]` separately for every
#     # top-level sample directory (in list_top_dirs) AND did a separate
#     # `path in up` check per region/variable/sample combination later --
#     # both patterns are fine on a small local file, but over AFS/EOS, with
#     # weight-based systematics now adding ~14x more histogram objects per
#     # MC sample (automatic, independent of --all-systematics), those many
#     # small individual lookups compounded into a very long stall.
#     t1 = time.time()
#     print("[INFO] Reading full path list from ROOT file (one-time bulk read, "
#           "may take a moment on a large/remote file)...")
#     raw_keys = up.keys(recursive=True)
#     print(f"[INFO] Read {len(raw_keys)} total keys in {time.time() - t1:.1f}s")

#     # Strip ROOT cycle suffixes (";1", ";2", ...) so membership checks below
#     # match the same cycle-agnostic semantics as `path in up` (which
#     # matches the latest cycle of a path regardless of its number).
#     all_paths = {k.rsplit(";", 1)[0] if ";" in k else k for k in raw_keys}

#     t0 = time.time()
#     print("[INFO] Grouping sample directories...")
#     groups = group_by_base_from_keys(raw_keys)  # base -> [concrete dirs]
#     print(f"[INFO] Found {sum(len(v) for v in groups.values())} sample directories "
#           f"across {len(groups)} bases ({time.time() - t0:.1f}s)")

#     data_base = "Data"
#     mc_bases = ["GGJets",
#                 # "GJetPt20To40",
#                 # "GJetPt40",
#                 "GluGluHToGG",
#                 "VBFHToGG",
#                 "VHToGG",
#                 "ttHToGG",
#                 "DDQCDGJET",
#                 # "QCD_PT-30to40",
#                 # "QCD_PT-30toInf",
#                 # "QCD_PT-40toInf",
#                 "TTGG",
#                 "TTG"]
#     signal_bases = [
#                     "NMSSM_X400_Y100",
#                     # "NMSSM_X400_Y125",
#                     # "NMSSM_X400_Y150",
#                     # "NMSSM_X500_Y100",
#                     # "NMSSM_X500_Y125",
#                     # "NMSSM_X500_Y150"
#                     ]

#     # Build jobs from the analyzer's truth: region -> list of variables
#     jobs = [(reg, var) for reg in REGION_LIST for var in variables_common[reg]]
#     n_jobs = len(jobs)
#     n_plotted = n_skipped = 0
#     t_loop = time.time()

#     for job_i, (region, var) in enumerate(jobs, start=1):
#         hname = vardict[var]  # <-- the key fix: use vardict[var] on disk

#         elapsed = time.time() - t_loop
#         avg = elapsed / job_i
#         eta = avg * (n_jobs - job_i)
#         print(f"[{job_i}/{n_jobs}] {region}/{var}  "
#               f"(elapsed {elapsed:.0f}s, ~{eta:.0f}s remaining)", flush=True)

#         # --- data
#         data_hist = None
#         for d in groups.get(data_base, []):
#             path = f"{d}/{systematic}/{region}/{hname}"
#             if path in all_paths:
#                 data_hist = add_hist_safe(data_hist, get_histogram(up, path, legend["Data"]))
#         if data_hist is None:
#             # nothing to draw in this region/var (for this systematic)
#             n_skipped += 1
#             continue

#         # --- MC (sum eras per base)
#         mc_merged = []
#         for base in mc_bases:
#             hsum = None
#             for d in groups.get(base, []):
#                 path = f"{d}/{systematic}/{region}/{hname}"
#                 if path in all_paths:
#                     hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
#             if hsum is not None:
#                 hsum.name = legend.get(base, base)
#                 mc_merged.append(hsum)
#         if not mc_merged:
#             n_skipped += 1
#             continue

#         # --- signals (only in SRs)
#         signal_hists = []
#         if region in ("srbbgg","srbbgg_EBEB","srbbgg_mixed","srbbgg_EEEE","srbbggMET", "preselection", "selection"):
#             for base in signal_bases:
#                 hsum = None
#                 for d in groups.get(base, []):
#                     path = f"{d}/{systematic}/{region}/{hname}"
#                     if path in all_paths:
#                         hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
#                 if hsum is not None:
#                     hsum.name = legend.get(base, base)
#                     signal_hists.append(hsum)

#         n_plotted += 1
#         # --- figure
#         dyn_w = max(11, int(1.5*len(mc_merged)))
#         fig, (ax, ax_ratio) = plt.subplots(
#             2, 1, figsize=(dyn_w, 12),
#             gridspec_kw={"height_ratios":[3,1]}, sharex=True
#         )
#         fig.subplots_adjust(hspace=0.05)

#         # data (blind if requested)
#         do_blind = blind and (var in blind_vars)
#         data_plot = blind_data(data_hist, do_blind, start_blind=110, stop_blind=130)
#         data_plot.plot(ax=ax, stack=False, histtype="errorbar",
#                        yerr=True, xerr=True, color="black", label="Data", flow="sum")

#         # MC stack
#         Stack(*mc_merged).plot(ax=ax, stack=True, histtype="fill", flow="sum", sort="yield")

#         # signal overlays
#         for s in signal_hists:
#             s.plot(ax=ax, histtype="step", yerr=False, xerr=False, label=s.name, color="red")

#         # ratio
#         mc_sum = sum_hist_list(mc_merged)
#         ratio, rerr = get_ratio(data_hist, mc_sum)
#         ratio_plot = blind_data(ratio, do_blind, start_blind=110, stop_blind=130)
#         ratio_plot.plot(ax=ax_ratio, histtype="errorbar", yerr=rerr, xerr=True, color="black", flow="sum")
#         ax_ratio.axhline(1, linestyle="--", color="gray")
#         ax_ratio.set_ylim(0, 3)
#         ax_ratio.set_ylabel("Data / MC")
#         ax_ratio.set_xlabel(xaxis_titles.get(var, var.replace("_"," ")))

#         # style
#         ax.set_yscale("log")
#         ax.set_ylim(0.1, 1e8)
#         ax.set_ylabel("Events")
#         hep.cms.label("", ax=ax, lumi=lumi_label(), loc=0, llabel="Work in progress", com=13.6)
#         ax.legend(ncol=2, loc="upper right", fontsize=16)
#         ax.set_xlabel("")

#         # save
#         outdir = os.path.join(output_dir, systematic, region)
#         os.makedirs(outdir, exist_ok=True)
#         plt.tight_layout()
#         plt.savefig(os.path.join(outdir, f"{var}.pdf"), bbox_inches="tight")
#         plt.savefig(os.path.join(outdir, f"{var}.png"), bbox_inches="tight")
#         plt.close()
#         print(f"[OK] {systematic}/{region}/{var}")

#     total = time.time() - t_loop
#     print(f"[DONE] systematic={systematic}: plotted {n_plotted}, skipped {n_skipped} "
#           f"(no data/MC found) out of {n_jobs} region/variable jobs, in {total:.0f}s")

# def main():
#     ap = argparse.ArgumentParser(description="Data/MC validation stack plots from the analyzer's merged histogram output.")
#     ap.add_argument("--root", default="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-histograms.root",
#                      help="Path to the merged histogram ROOT file.")
#     ap.add_argument("--systematic", default="nominal",
#                      help="Which systematic's histograms to plot (default: nominal). "
#                           "Matches the systematic label the analyzer wrote, e.g. "
#                           "'nominal', 'PileupUp', 'jec_syst_Total_up'.")
#     ap.add_argument("--outdir", default="stack_plots",
#                      help="Output directory; plots are written to <outdir>/<systematic>/<region>/<var>.{png,pdf}")
#     ap.add_argument("--blind", action="store_true",
#                      help="Blind the signal-mass window in dibjet_mass/diphoton_mass plots (default: unblinded).")
#     args = ap.parse_args()

#     up = uproot.open(args.root)
#     os.makedirs(args.outdir, exist_ok=True)
#     stack1d_histograms(up, args.outdir, systematic=args.systematic, blind=args.blind)

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hhbbgg_Plotter.py

Data/MC validation stack plots from the analyzer's merged histogram output.

Reads sample/systematic/region/variable histogram paths (matching
hhbbgg_analyzer_lxplus_par.py's output structure, which now includes an
explicit systematic dimension -- "nominal" by default, or any
weight-based/folder-based systematic label the analyzer produced).
"""
import os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import argparse

import uproot
from hist import Hist, Stack
import boost_histogram as bh
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler
from normalisation import getLumi

# --- import the SAME maps your analyzer used ---
from variables import vardict, regions as REGION_LIST, variables_common  # <- key change

# If you have a year/era-aware getLumi, replace this label.
def lumi_label():
    return "34.65"  # fb^-1 for 2022 only
    # return "27.76"  # fb^-1 for 2023 only
    # return "108.96"  # fb^-1 for 2024 only
    # return 62.31  # fb^-1 for 2022-2023
    # return "171.37"  # fb^-1 for 2022-2024

# ------------------- Styling -------------------
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
        "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd",
    ]
)

# ------------------- Safe hist ops -------------------
def ensure_weight_hist(h_in: Hist) -> Hist:
    axes = []
    for ax in h_in.axes:
        edges = getattr(ax, "edges", None)
        if edges is not None:
            axes.append(bh.axis.Variable(edges))
        else:
            axes.append(bh.axis.Regular(ax.size, ax.edges[0], ax.edges[-1]))
    h_out = Hist(*axes, storage=bh.storage.Weight())
    vals = np.asarray(h_in.values(), dtype="f8")
    vars_ = h_in.variances()
    vars_ = np.zeros_like(vals, dtype="f8") if vars_ is None else np.asarray(vars_, dtype="f8")
    view = h_out.view()
    view.value[...] = vals
    view.variance[...] = vars_
    return h_out

def add_hist_safe(a: "Hist | None", b: Hist) -> Hist:
    b = ensure_weight_hist(b)
    if a is None:
        return b
    a = ensure_weight_hist(a)
    a += b
    return a

# ------------------- ROOT helpers -------------------
def list_top_dirs(upfile):
    out = []
    for key in upfile.keys():
        name = key.split(";")[0]
        try:
            obj = upfile[name]
            if hasattr(obj, "keys"):
                out.append(name)
        except KeyError:
            continue
    return out


def dir_to_base(name: str) -> "str | None":
    n = name

    # ------------------
    # DATA (any era / year / merge)
    # ------------------
    # FIXED, confirmed real bug: the original regex (^|_)Data(_|$) required
    # an underscore or end-of-string immediately after "Data", so it never
    # matched this production's actual per-era naming convention --
    # "DataE"/"DataF"/"DataG" (era letter appended directly, no separator,
    # confirmed directly from a real 2022preEE file's top-level directory
    # "DataF_NOTAG_merged"). Every single Data directory was silently
    # classified as base=None and dropped by group_by_base_from_keys(),
    # meaning data_hist stayed None for every region/variable and EVERY
    # plot job was skipped -- confirmed as the entire cause of an empty
    # stack_plots/ output, not a partial or cosmetic issue. A simple
    # case-insensitive prefix check is robust to this and every other
    # Data naming variant seen in this pipeline (Data_EraE, bare "Data",
    # etc.), with no false-positive risk against any real MC/signal base
    # name in this analysis (none of them start with "data").
    if n.lower().startswith("data"):
        return "Data"

    # ------------------
    # Normalize name (remove era / year / merge noise)
    # ------------------
    n_clean = n
    n_clean = re.sub(r"(2022|2023|2024)", "", n_clean, flags=re.IGNORECASE)
    n_clean = re.sub(r"(preEE|postEE|preBPix|postBPix)", "", n_clean, flags=re.IGNORECASE)
    n_clean = re.sub(r"(Era[A-Z])", "", n_clean, flags=re.IGNORECASE)
    n_clean = re.sub(r"(merged|NOTAG)", "", n_clean, flags=re.IGNORECASE)
    n_clean = re.sub(r"__+", "_", n_clean).strip("_")

    # ------------------
    # DD QCD (ALL variants)
    # ------------------
    # Regex instead of a fixed substring list, since the DD QCD+GJet
    # template's naming varies across productions -- e.g.
    # "DDQCDGJET_Rescaled" (2022, single C) vs "DDQCCDGJets" (2024,
    # double C, no _Rescaled suffix). Mirrors the same fix applied to
    # hhbbgg_analyzer_lxplus_par.py's is_dd_template(); a plain
    # n.startswith("DDQCDGJET") check silently misses the newer naming.
    if re.search(r"ddqc+dgjets?", n, re.IGNORECASE) or re.search(r"GGJets_(high|low)_Rescaled", n, re.IGNORECASE):
        return "DDQCDGJET"

    # ------------------
    # Common MC bases (regex containment)
    # ------------------
    mc_patterns = {
        "GGJets": r"GGJets",
        "GJetPt20To40": r"GJet.*20.*40",
        "GJetPt40": r"GJet.*40",
        "GluGluHToGG": r"GluGluHToGG",
        "VBFHToGG": r"VBFHToGG",
        # FIXED: previously only matched the literal 2022/2023-style
        # combined "VHToGG" name, silently dropping the 2024+ production's
        # WmHtoGG/WpHtoGG/ZHtoGG (three separate directories, no combined
        # "VHToGG" ever exists there) -- confirmed these three samples
        # were completely absent from every 2024 Data/MC stack plot as a
        # result. Same underlying naming-convention gap already fixed in
        # normalisation.py's getXsec() and common/io_utils.py's
        # is_resonant_bkg_dir()/group_of(); this is the third independent
        # occurrence of it. All four variants combine into one "VHToGG"
        # base so 2022/2023 (single combined sample) and 2024+ (three
        # separate samples, summed) both land in the same stacked
        # component.
        "VHToGG": r"VHToGG|WmHToGG|WpHToGG|ZHToGG",
        "ttHToGG": r"ttHToGG",
        "TTGG": r"TTGG",
        "TTG": r"TTG",
        "QCD_PT-30to40": r"QCD.*30.*40",
        "QCD_PT-30toInf": r"QCD.*30.*Inf",
        "QCD_PT-40toInf": r"QCD.*40.*Inf",
    }

    for base, pat in mc_patterns.items():
        if re.search(pat, n_clean, re.IGNORECASE):
            return base

    # ------------------
    # NMSSM signals (keep exact)
    # ------------------
    if n_clean.startswith("NMSSM_"):
        return n_clean

    return None


def group_by_base(upfile):
    groups = {}
    for d in list_top_dirs(upfile):
        base = dir_to_base(d)
        if base is None:
            continue
        groups.setdefault(base, []).append(d)
    return {k: sorted(v) for k, v in groups.items()}


def list_top_dirs_from_keys(all_keys) -> list:
    """Extract top-level directory names by parsing an already-fetched
    recursive key listing, instead of opening each top-level directory
    individually via `upfile[name]` (see list_top_dirs above).

    This is the actual fix for the multi-minute (or longer) hang: the
    per-sample count hasn't grown, but each individual `upfile[name]`
    open now has to materialize a directory object whose internal subtree
    is ~4 levels deep and ~14x bigger (sample -> systematic -> region ->
    variable, with weight-based systematics added). Over AFS/EOS, that
    made each of the ~N individual opens dramatically slower even though
    nothing else about the code changed. Parsing pre-fetched key strings
    instead does zero additional file access.
    """
    tops = set()
    for k in all_keys:
        base = k.split(";")[0]
        top = base.split("/")[0]
        if top:
            tops.add(top)
    return sorted(tops)


def group_by_base_from_keys(all_keys) -> dict:
    groups = {}
    for d in list_top_dirs_from_keys(all_keys):
        base = dir_to_base(d)
        if base is None:
            continue
        groups.setdefault(base, []).append(d)
    return {k: sorted(v) for k, v in groups.items()}

# ------------------- Read hist -------------------
def get_histogram(upfile, path: str, label=None) -> Hist:
    # path: Sample/Systematic/Region/<vardict[var]>
    h = Hist(upfile[path])
    if label is not None:
        h.name = label
    return h

def sum_hist_list(hlist):
    out = None
    for h in hlist:
        out = add_hist_safe(out, h)
    return out

# ------------------- Blinding & ratio -------------------
def blind_data(hist, blind, start_blind=122, stop_blind=128):
    if not blind:
        return hist
    blinded = hist.copy()
    for b in range(blinded.axes[0].size):
        c = blinded.axes[0].centers[b]
        if start_blind <= c <= stop_blind:
            blinded[b] = 0.0
    return blinded

def get_ratio(hist_a, hist_b):
    edges_a = hist_a.axes.edges[0]
    edges_b = hist_b.axes.edges[0]
    if not np.array_equal(edges_a, edges_b):
        raise ValueError("Histograms have different binning")
    a = np.where(hist_a.values() < 0, 0.0, hist_a.values())
    b = np.where(hist_b.values() < 0, 0.0, hist_b.values())
    ea = np.sqrt(a)
    eb = np.sqrt(b)
    ratio = np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)
    ratio_hist = Hist(hist_a.axes[0], storage=bh.storage.Double())
    ratio_hist[...] = ratio
    with np.errstate(divide="ignore", invalid="ignore"):
        ra = np.divide(ea, a, out=np.zeros_like(ea, dtype=float), where=a != 0)
        rb = np.divide(eb, b, out=np.zeros_like(eb, dtype=float), where=b != 0)
    ratio_err = ratio * np.sqrt(ra**2 + rb**2)
    return ratio_hist, ratio_err

# ------------------- Config -------------------
blind_vars = ["dibjet_mass", "diphoton_mass"]

legend = {
    "Data": "Data",
    "GGJets": r"$\gamma\gamma$+jets $\times 1.4$",
    "GJetPt20To40": r"$\gamma$+jets ($20< p_T < 40$)",
    "GJetPt40": r"$\gamma$+jets ($p_T > 40$)",
    "GluGluHToGG": r"$gg\to H\to\gamma\gamma$",
    "VBFHToGG": r"$VBF\,H\to\gamma\gamma$",
    "VHToGG": r"$V\,H\to\gamma\gamma$",
    "ttHToGG": r"$t\bar t H\to\gamma\gamma$",
    "DDQCDGJET": r"DDQCDGJET",
    "TTGG": r"$t\bar t + \gamma\gamma$",
    "TTG": r"$t\bar t \to \gamma$",
    # signals
    "NMSSM_X400_Y100": r"$NMSSM\_X_{400}\_Y_{100}\times 10$",
    "NMSSM_X400_Y125": r"$NMSSM\_X_{400}\_Y_{125}\times 10$",
    "NMSSM_X400_Y150": r"$NMSSM\_X_{400}\_Y_{150}\times 10$",
    "NMSSM_X500_Y100": r"$NMSSM\_X_{500}\_Y_{100}\times 10$",
    "NMSSM_X500_Y125": r"$NMSSM\_X_{500}\_Y_{125}\times 10$",
    "NMSSM_X500_Y150": r"$NMSSM\_X_{500}\_Y_{150}\times 10$",
}

# Optional pretty x-axis names (fallback to raw var if missing)
xaxis_titles = {
    "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
    "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
    "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
    "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
    "diphoton_pt": r"$p_T^{\gamma\gamma}$ [GeV]",
    "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
    # ... add more if you want
}

# ------------------- Plotter -------------------
def stack1d_histograms(up, output_dir, systematic="nominal", blind=True):
    import time

    # Single bulk read of every key in the file, done ONCE. This is the
    # actual fix for the hang: everything else below (sample grouping,
    # path-existence checks) is derived from this one in-memory result via
    # pure string parsing, instead of each doing its own individual file
    # access. The old code called `upfile[name]` separately for every
    # top-level sample directory (in list_top_dirs) AND did a separate
    # `path in up` check per region/variable/sample combination later --
    # both patterns are fine on a small local file, but over AFS/EOS, with
    # weight-based systematics now adding ~14x more histogram objects per
    # MC sample (automatic, independent of --all-systematics), those many
    # small individual lookups compounded into a very long stall.
    t1 = time.time()
    print("[INFO] Reading full path list from ROOT file (one-time bulk read, "
          "may take a moment on a large/remote file)...")
    raw_keys = up.keys(recursive=True)
    print(f"[INFO] Read {len(raw_keys)} total keys in {time.time() - t1:.1f}s")

    # Strip ROOT cycle suffixes (";1", ";2", ...) so membership checks below
    # match the same cycle-agnostic semantics as `path in up` (which
    # matches the latest cycle of a path regardless of its number).
    all_paths = {k.rsplit(";", 1)[0] if ";" in k else k for k in raw_keys}

    t0 = time.time()
    print("[INFO] Grouping sample directories...")
    groups = group_by_base_from_keys(raw_keys)  # base -> [concrete dirs]
    print(f"[INFO] Found {sum(len(v) for v in groups.values())} sample directories "
          f"across {len(groups)} bases ({time.time() - t0:.1f}s)")

    data_base = "Data"
    mc_bases = ["GGJets",
                # "GJetPt20To40",
                # "GJetPt40",
                "GluGluHToGG",
                "VBFHToGG",
                "VHToGG",
                "ttHToGG",
                "DDQCDGJET",
                # "QCD_PT-30to40",
                # "QCD_PT-30toInf",
                # "QCD_PT-40toInf",
                "TTGG",
                "TTG"]
    signal_bases = [
                    "NMSSM_X400_Y100",
                    # "NMSSM_X400_Y125",
                    # "NMSSM_X400_Y150",
                    # "NMSSM_X500_Y100",
                    # "NMSSM_X500_Y125",
                    # "NMSSM_X500_Y150"
                    ]

    # Build jobs from the analyzer's truth: region -> list of variables
    jobs = [(reg, var) for reg in REGION_LIST for var in variables_common[reg]]
    n_jobs = len(jobs)
    n_plotted = n_skipped = 0
    t_loop = time.time()

    for job_i, (region, var) in enumerate(jobs, start=1):
        hname = vardict[var]  # <-- the key fix: use vardict[var] on disk

        elapsed = time.time() - t_loop
        avg = elapsed / job_i
        eta = avg * (n_jobs - job_i)
        print(f"[{job_i}/{n_jobs}] {region}/{var}  "
              f"(elapsed {elapsed:.0f}s, ~{eta:.0f}s remaining)", flush=True)

        # --- data
        data_hist = None
        for d in groups.get(data_base, []):
            path = f"{d}/{systematic}/{region}/{hname}"
            if path in all_paths:
                data_hist = add_hist_safe(data_hist, get_histogram(up, path, legend["Data"]))
        if data_hist is None:
            # nothing to draw in this region/var (for this systematic)
            n_skipped += 1
            continue

        # --- MC (sum eras per base)
        mc_merged = []
        for base in mc_bases:
            hsum = None
            for d in groups.get(base, []):
                path = f"{d}/{systematic}/{region}/{hname}"
                if path in all_paths:
                    hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
            if hsum is not None:
                hsum.name = legend.get(base, base)
                mc_merged.append(hsum)
        if not mc_merged:
            n_skipped += 1
            continue

        # --- signals (only in SRs)
        signal_hists = []
        if region in ("srbbgg","srbbgg_EBEB","srbbgg_mixed","srbbgg_EEEE","srbbggMET", "preselection", "selection"):
            for base in signal_bases:
                hsum = None
                for d in groups.get(base, []):
                    path = f"{d}/{systematic}/{region}/{hname}"
                    if path in all_paths:
                        hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
                if hsum is not None:
                    hsum.name = legend.get(base, base)
                    signal_hists.append(hsum)

        n_plotted += 1
        # --- figure
        dyn_w = max(11, int(1.5*len(mc_merged)))
        fig, (ax, ax_ratio) = plt.subplots(
            2, 1, figsize=(dyn_w, 12),
            gridspec_kw={"height_ratios":[3,1]}, sharex=True
        )
        fig.subplots_adjust(hspace=0.05)

        # data (blind if requested)
        do_blind = blind and (var in blind_vars)
        data_plot = blind_data(data_hist, do_blind, start_blind=110, stop_blind=130)
        data_plot.plot(ax=ax, stack=False, histtype="errorbar",
                       yerr=True, xerr=True, color="black", label="Data", flow="sum")

        # MC stack
        Stack(*mc_merged).plot(ax=ax, stack=True, histtype="fill", flow="sum", sort="yield")

        # signal overlays
        for s in signal_hists:
            s.plot(ax=ax, histtype="step", yerr=False, xerr=False, label=s.name, color="red")

        # ratio
        mc_sum = sum_hist_list(mc_merged)
        ratio, rerr = get_ratio(data_hist, mc_sum)
        ratio_plot = blind_data(ratio, do_blind, start_blind=110, stop_blind=130)
        ratio_plot.plot(ax=ax_ratio, histtype="errorbar", yerr=rerr, xerr=True, color="black", flow="sum")
        ax_ratio.axhline(1, linestyle="--", color="gray")
        ax_ratio.set_ylim(0, 3)
        ax_ratio.set_ylabel("Data / MC")
        ax_ratio.set_xlabel(xaxis_titles.get(var, var.replace("_"," ")))

        # style
        ax.set_yscale("log")
        ax.set_ylim(0.1, 1e8)
        ax.set_ylabel("Events")
        hep.cms.label("", ax=ax, lumi=lumi_label(), loc=0, llabel="Work in progress", com=13.6)
        ax.legend(ncol=2, loc="upper right", fontsize=16)
        ax.set_xlabel("")

        # save
        outdir = os.path.join(output_dir, systematic, region)
        os.makedirs(outdir, exist_ok=True)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"{var}.pdf"), bbox_inches="tight")
        plt.savefig(os.path.join(outdir, f"{var}.png"), bbox_inches="tight")
        plt.close()
        print(f"[OK] {systematic}/{region}/{var}")

    total = time.time() - t_loop
    print(f"[DONE] systematic={systematic}: plotted {n_plotted}, skipped {n_skipped} "
          f"(no data/MC found) out of {n_jobs} region/variable jobs, in {total:.0f}s")

def main():
    ap = argparse.ArgumentParser(description="Data/MC validation stack plots from the analyzer's merged histogram output.")
    ap.add_argument("--root", default="/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-histograms.root",
                     help="Path to the merged histogram ROOT file.")
    ap.add_argument("--systematic", default="nominal",
                     help="Which systematic's histograms to plot (default: nominal). "
                          "Matches the systematic label the analyzer wrote, e.g. "
                          "'nominal', 'PileupUp', 'jec_syst_Total_up'.")
    ap.add_argument("--outdir", default="stack_plots",
                     help="Output directory; plots are written to <outdir>/<systematic>/<region>/<var>.{png,pdf}")
    ap.add_argument("--blind", action="store_true",
                     help="Blind the signal-mass window in dibjet_mass/diphoton_mass plots (default: unblinded).")
    args = ap.parse_args()

    up = uproot.open(args.root)
    os.makedirs(args.outdir, exist_ok=True)
    stack1d_histograms(up, args.outdir, systematic=args.systematic, blind=args.blind)

if __name__ == "__main__":
    main()