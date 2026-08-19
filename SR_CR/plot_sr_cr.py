#!/usr/bin/env python3
"""
plot_sr_cr.py

Plots the combined background diphoton_mass shape (broad "selection"
region) with the Signal Region (SR) and Control Region (CR) windows
shaded, matching the definitions in
event_categorization/build_pdnn_categories.py's defaults:
    SR: |Mgg - 125| < sr_sigma        (default sr_sigma = 2.0 GeV)
    CR: cr_lo <= |Mgg - 125| < cr_hi  (default (cr_lo, cr_hi) = (4, 10) GeV)

Usage:
    python3 plot_sr_cr.py \
      --hist-file /path/to/hhbbgg_analyzer-v2-histograms__<timestamp>.root \
      --region selection --sr-sigma 2.0 --cr-lo 4 --cr-hi 10 \
      --out sr_cr_definition
"""
import argparse
import json
import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Same 10-sample combined-background list used throughout this session's
# rate-systematics computation (compute_weight_rate_systematics.py) --
# excludes the raw GGJets_MGG-80 in favor of the _Rescaled data-driven
# template, to avoid double-counting the non-resonant continuum.
DEFAULT_BKG_SAMPLES = [
    "GluGluHtoGG", "VBFHtoGG", "WmHtoGG", "WpHtoGG", "ZHtoGG",
    "bbHtoGG", "ttHtoGG", "TTGG",
    "GGJets_MGG-80_Rescaled", "DDQCDGJets_Rescaled",
]


def extract_combined_hist(hist_file, region, variable, samples, systematic="nominal"):
    f = uproot.open(hist_file)
    keys = f.keys()

    combined_values = None
    edges = None
    found_samples = []
    for s in samples:
        prefix = f"{s}/{systematic}/{region}/{variable}"
        matching = [k for k in keys if k.startswith(prefix)]
        if not matching:
            continue
        h = f[matching[0]]
        values, e = h.to_numpy(flow=False)
        if combined_values is None:
            combined_values = values.copy()
            edges = e
        else:
            combined_values += values
        found_samples.append(s)

    if combined_values is None:
        raise RuntimeError(
            f"No histograms found for region='{region}', variable='{variable}', "
            f"systematic='{systematic}' among samples: {samples}"
        )

    print(f"[INFO] Combined {len(found_samples)}/{len(samples)} sample(s): {found_samples}")
    print(f"[INFO] {len(combined_values)} bins, range [{edges[0]}, {edges[-1]}]")
    return edges, combined_values


def make_plot(edges, values, sr_sigma, cr_lo, cr_hi, out_prefix, region_label="selection"):
    edges = np.asarray(edges)
    values = np.asarray(values)
    centers = 0.5 * (edges[:-1] + edges[1:])

    sr_lo_edge, sr_hi_edge = 125 - sr_sigma, 125 + sr_sigma
    cr1_lo, cr1_hi = 125 - cr_hi, 125 - cr_lo
    cr2_lo, cr2_hi = 125 + cr_lo, 125 + cr_hi

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.stairs(values, edges, color="#3f90da", linewidth=2,
              label=f"Combined background (MC), {region_label} region")
    ax.fill_between(centers, 0, values, step="mid", color="#3f90da", alpha=0.15)

    ax.axvspan(sr_lo_edge, sr_hi_edge, color="#bd1f01", alpha=0.25,
               label=rf"SR: $|M_{{\gamma\gamma}}-125|<{sr_sigma:g}$ GeV")
    ax.axvspan(cr1_lo, cr1_hi, color="#ffa90e", alpha=0.25,
               label=rf"CR: ${cr_lo:g}\leq|M_{{\gamma\gamma}}-125|<{cr_hi:g}$ GeV")
    ax.axvspan(cr2_lo, cr2_hi, color="#ffa90e", alpha=0.25)

    ax.set_xlabel(r"$M_{\gamma\gamma}$ [GeV]", fontsize=14)
    ax.set_ylabel("Events / bin", fontsize=14)
    ax.set_xlim(edges[0], edges[-1])
    ax.set_ylim(0, values.max() * 1.15)
    ax.legend(fontsize=11, loc="upper right", frameon=True)
    ax.set_title("Signal Region (SR) and Control Region (CR) definitions", fontsize=13)
    ax.tick_params(labelsize=11)

    plt.tight_layout()
    plt.savefig(f"{out_prefix}.png", dpi=200)
    plt.savefig(f"{out_prefix}.pdf")
    print(f"[OK] Wrote {out_prefix}.png / {out_prefix}.pdf")


def main():
    ap = argparse.ArgumentParser(description="Plot the SR/CR diphoton_mass window definitions.")
    ap.add_argument("--hist-file", required=True,
                     help="Path to the merged analyzer histogram ROOT file "
                          "(e.g. hhbbgg_analyzer-v2-histograms__<timestamp>.root).")
    ap.add_argument("--region", default="selection",
                     help="Which region's diphoton_mass shape to plot (default: "
                          "'selection', broad enough to show both SR and CR windows "
                          "within one spectrum -- 'srbbgg' is already SR-cut, so it "
                          "would not show the sidebands at all).")
    ap.add_argument("--variable", default="diphoton_mass")
    ap.add_argument("--systematic", default="nominal")
    ap.add_argument("--samples", nargs="*", default=DEFAULT_BKG_SAMPLES,
                     help="Background samples to sum (default: the same 10-sample "
                          "combined-background list used for rate systematics).")
    ap.add_argument("--sr-sigma", type=float, default=2.0,
                     help="SR window: |Mgg-125| < sr_sigma (GeV). Matches "
                          "build_pdnn_categories.py's --sr-sigma default.")
    ap.add_argument("--cr-lo", type=float, default=4.0)
    ap.add_argument("--cr-hi", type=float, default=10.0)
    ap.add_argument("--out", default="sr_cr_definition",
                     help="Output filename prefix (writes <out>.png and <out>.pdf).")
    args = ap.parse_args()

    edges, values = extract_combined_hist(
        args.hist_file, args.region, args.variable, args.samples, args.systematic
    )
    make_plot(edges, values, args.sr_sigma, args.cr_lo, args.cr_hi, args.out,
              region_label=args.region)


if __name__ == "__main__":
    main()