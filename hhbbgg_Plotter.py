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
import os, re, glob
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
from normalisation import getLumi

# FIXED: the previous lumi_label() was a hardcoded, manually-commented
# single value -- a real, confirmed risk, not just an inconvenience: a
# bare `return` statement makes everything textually after it in that
# function unreachable, WHETHER OR NOT it's commented. If someone ever
# uncommented a different candidate line without also commenting out the
# original, the function would silently keep returning the OLD value
# with no error at all -- a wrong luminosity label on a real,
# already-published-looking plot. Replaced with a real computation via
# getLumi(), matching the exact (year, era) pairs already confirmed
# correct earlier this session (e.g. 2022 PreEE+PostEE = 34.6521,
# matching the documented full-2022 value exactly).
YEAR_ERAS = {
    "2022": ["PreEE", "PostEE"],
    "2023": ["preBPix", "postBPix"],
    "2024": ["All"],
    "2025": ["All"],
}


def compute_combined_lumi(years):
    """Real combined luminosity for a list of years, summing every
    sub-era's own getLumi() call -- not a hardcoded guess."""
    total = 0.0
    for year in years:
        eras = YEAR_ERAS.get(year)
        if eras is None:
            raise ValueError(f"compute_combined_lumi: no known era list for year {year!r}. "
                              f"Known years: {sorted(YEAR_ERAS.keys())}.")
        for era in eras:
            total += getLumi(year, era)
    return total


def extract_years_from_path(path):
    """Best-effort, COSMETIC-ONLY year detection from a --root file path
    (e.g. 'DD_2022_combined/...' -> ['2022']) -- used only when --years
    wasn't given directly, so an ad hoc --root call still has a real
    chance at a correct label instead of silently falling back to a
    stale default. Never used for anything affecting actual histogram
    content -- only the displayed lumi text."""
    years = []
    for y in re.findall(r"202[2-5]", path):
        if y not in years:
            years.append(y)
    return years

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
    n_clean = re.sub(r"(2022|2023|2024|2025)", "", n_clean, flags=re.IGNORECASE)
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
        # Missing bbHtoGG, adding on 09/21/2026
        "bbHtoGG": r"bbH.*ToGG",
        
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
    "bbHToGG": r"$bbH\to\gamma\gamma$",
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
def resolve_year_to_root_file(base_dir, year):
    """Try, in order, every naming convention seen across this pipeline's
    real output so far, and return the best match -- printing exactly
    which pattern matched so a wrong guess is never silent.

    Order: an explicit, already-named single file (no timestamp,
    typically produced by an explicit `hadd` into a fixed name) is
    preferred over a timestamped one, since an explicit name usually
    means someone deliberately finalized it. If only timestamped files
    exist for a year (e.g. it hasn't been explicitly combined into one
    named file yet), the most RECENT one is used by actual mtime, not
    filename/alphabetical sort -- the same lesson already confirmed
    necessary once this session for toy-file selection, which defaulted
    to alphabetical order and silently picked a stale file instead of
    the newest one.
    """
    candidates_exact = [
        os.path.join(base_dir, f"DD_{year}_combined", "hhbbgg_analyzer-v2-histograms.root"),
        os.path.join(base_dir, f"DD_{year}", "hhbbgg_analyzer-v2-histograms.root"),
    ]
    for path in candidates_exact:
        if os.path.isfile(path):
            return path, "exact"

    candidates_glob = [
        os.path.join(base_dir, f"DD_{year}_combined", "hhbbgg_analyzer-v2-histograms__*.root"),
        os.path.join(base_dir, f"DD_{year}", "hhbbgg_analyzer-v2-histograms__*.root"),
    ]
    for pattern in candidates_glob:
        matches = glob.glob(pattern)
        if matches:
            latest = max(matches, key=os.path.getmtime)
            return latest, "latest-timestamped"

    return None, None


def gather_across_sources(sources, base, systematic, region, hname, label):
    """Sum matching histograms across ALL sources (one source per input
    --root file) -- this is what lets multiple separate files (e.g. one
    per year) be combined at PLOT TIME, with no intermediate merged file
    ever written to disk. Confirmed working via direct testing: MC bases
    sum correctly across files (weighted yields add exactly), and Data
    sums correctly even when each year uses a completely different
    directory naming convention (e.g. "DataC_NOTAG_merged" for 2022 vs
    "DataCv1EG0_NOTAG_merged" for 2023) -- since summing is driven by the
    RESOLVED base name ("Data"), not the raw directory name, this needs
    no special-casing per year."""
    hsum = None
    for up, all_paths, groups in sources:
        for d in groups.get(base, []):
            path = f"{d}/{systematic}/{region}/{hname}"
            if path in all_paths:
                hsum = add_hist_safe(hsum, get_histogram(up, path, label))
    return hsum


def stack1d_histograms(sources, output_dir, lumi_value, systematic="nominal", blind=True):
    """sources: list of (up, all_paths, groups) tuples, one per --root
    file passed on the command line. Supports exactly one source
    (unchanged, original single-file behavior) or multiple (new:
    combines them at plot time, e.g. one file per year, without ever
    writing an intermediate merged file to disk)."""
    import time

    print(f"[INFO] Plotting from {len(sources)} source file(s).")
    for i, (up, all_paths, groups) in enumerate(sources):
        print(f"[INFO]   source {i+1}: {sum(len(v) for v in groups.values())} sample "
              f"directories across {len(groups)} bases")

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
                # Adding bbHtoGG on 09/21/2026
                "bbHtoGG",
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

        # --- data (summed across every source) ---
        data_hist = gather_across_sources(sources, data_base, systematic, region, hname, legend["Data"])
        if data_hist is None:
            n_skipped += 1
            continue

        # --- MC (summed across every source, per base) ---
        mc_merged = []
        for base in mc_bases:
            hsum = gather_across_sources(sources, base, systematic, region, hname, legend.get(base, base))
            if hsum is not None:
                hsum.name = legend.get(base, base)
                mc_merged.append(hsum)
        if not mc_merged:
            n_skipped += 1
            continue

        # --- signals (only in SRs, summed across every source) ---
        signal_hists = []
        if region in ("srbbgg","srbbgg_EBEB","srbbgg_mixed","srbbgg_EEEE","srbbggMET", "preselection", "selection"):
            for base in signal_bases:
                hsum = gather_across_sources(sources, base, systematic, region, hname, legend.get(base, base))
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
        hep.cms.label("", ax=ax, lumi=f"{lumi_value:.2f}", loc=0, llabel="Work in progress", com=13.6)
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
    ap.add_argument("--root", action="append", default=[],
                     help="Path to a merged histogram ROOT file. Repeatable -- pass "
                          "multiple times to combine several files' Data/MC AT PLOT "
                          "TIME, with no intermediate merged file ever written to disk. "
                          "Can be combined with --years below; use whichever is more "
                          "convenient, or both together.")
    ap.add_argument("--years", default=None,
                     help="Comma-separated years to auto-discover and combine, e.g. "
                          "'2022,2023' or '2022,2023,2024' or just '2023'. For each "
                          "year, looks for (in order): DD_<year>_combined/"
                          "hhbbgg_analyzer-v2-histograms.root, DD_<year>/"
                          "hhbbgg_analyzer-v2-histograms.root, then falls back to the "
                          "most RECENT (by modification time, not filename) "
                          "hhbbgg_analyzer-v2-histograms__*.root under either directory "
                          "if no explicitly-named file exists yet. Prints exactly which "
                          "file was picked for each year -- always check this rather "
                          "than trusting it silently, in case discovery guesses wrong.")
    ap.add_argument("--base-dir", default=".",
                     help="Base directory containing the DD_<year>[_combined] "
                          "subdirectories, used only with --years.")
    ap.add_argument("--systematic", default="nominal",
                     help="Which systematic's histograms to plot (default: nominal). "
                          "Matches the systematic label the analyzer wrote, e.g. "
                          "'nominal', 'PileupUp', 'jec_syst_Total_up'.")
    ap.add_argument("--outdir", default="stack_plots",
                     help="Output directory; plots are written to <outdir>/<systematic>/<region>/<var>.{png,pdf}")
    ap.add_argument("--blind", action="store_true",
                     help="Blind the signal-mass window in dibjet_mass/diphoton_mass plots (default: unblinded).")
    ap.add_argument("--lumi", type=float, default=None,
                     help="Explicitly set the displayed luminosity (fb^-1), skipping "
                          "auto-detection entirely. Use this when plotting from --root "
                          "path(s) that don't contain a recognizable year, or to "
                          "override the computed value for any reason.")
    args = ap.parse_args()

    explicit_root_paths = list(args.root)
    detected_years = set()
    root_paths = []

    # Explicit --root paths: best-effort year extraction, for the lumi
    # label only -- never affects which histograms actually get read.
    for p in explicit_root_paths:
        root_paths.append(p)
        found = extract_years_from_path(p)
        if found:
            detected_years.update(found)
        else:
            print(f"[WARN] Could not auto-detect a year from --root path '{p}' for the "
                  f"luminosity label -- pass --lumi explicitly if the auto-computed "
                  f"value (based only on whatever other years WERE detected) is wrong.")

    if args.years:
        years = [y.strip() for y in args.years.split(",") if y.strip()]
        print(f"[INFO] --years given: resolving {years} under base dir '{args.base_dir}'...")
        for year in years:
            path, how = resolve_year_to_root_file(args.base_dir, year)
            if path is None:
                raise SystemExit(
                    f"[ERROR] Could not find a histogram file for year {year} under "
                    f"'{args.base_dir}' -- tried DD_{year}_combined/ and DD_{year}/, "
                    f"both the exact filename and any hhbbgg_analyzer-v2-histograms__*.root. "
                    f"Check --base-dir is correct, or pass the file directly via --root instead."
                )
            print(f"[INFO]   {year} -> {path}  (matched via: {how})")
            root_paths.append(path)
            detected_years.add(year)  # authoritative -- --years gives the exact year, no extraction needed

    if not root_paths:
        raise SystemExit("[ERROR] No input files -- pass at least one --root, or use --years with --base-dir.")

    if args.lumi is not None:
        lumi_value = args.lumi
        print(f"[INFO] Using explicitly given --lumi {lumi_value} fb^-1 (auto-detection skipped).")
    else:
        if not detected_years:
            raise SystemExit(
                "[ERROR] Could not determine which year(s) are being plotted (no --years "
                "given, and no year could be auto-detected from any --root path) -- pass "
                "--lumi <value> explicitly, or use --years instead of raw --root paths."
            )
        sorted_years = sorted(detected_years)
        lumi_value = compute_combined_lumi(sorted_years)
        print(f"[INFO] Computed combined luminosity for {sorted_years}: {lumi_value:.4f} fb^-1 "
              f"(pass --lumi explicitly to override this).")

    import time
    sources = []
    for root_path in root_paths:
        t1 = time.time()
        print(f"[INFO] Reading full path list from {root_path} (one-time bulk read, "
              f"may take a moment on a large/remote file)...")
        up = uproot.open(root_path)
        raw_keys = up.keys(recursive=True)
        print(f"[INFO] Read {len(raw_keys)} total keys in {time.time() - t1:.1f}s")
        # Strip ROOT cycle suffixes (";1", ";2", ...) so membership checks
        # match the same cycle-agnostic semantics as `path in up`.
        all_paths = {k.rsplit(";", 1)[0] if ";" in k else k for k in raw_keys}
        groups = group_by_base_from_keys(raw_keys)
        sources.append((up, all_paths, groups))

    os.makedirs(args.outdir, exist_ok=True)
    stack1d_histograms(sources, args.outdir, lumi_value, systematic=args.systematic, blind=args.blind)

if __name__ == "__main__":
    main()