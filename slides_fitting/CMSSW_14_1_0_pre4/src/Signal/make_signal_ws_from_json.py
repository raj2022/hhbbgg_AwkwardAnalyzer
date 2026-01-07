#!/usr/bin/env python3
"""
make_signal_ws_from_json.py

Read a JSON of fitted signal shapes (multi-Gaussian components for mgg)
and produce one ROOT file per category containing a RooWorkspace with:
  - RooRealVar "mgg"
  - component Gaussians named "mgg_g_c{cat}_g{i}"
  - fraction RooRealVar "mgg_frac_c{cat}_g{i}" (for N-1 components)
  - RooAddPdf "pdf_mgg_c{cat}"

Usage (example):
  cmsenv
  python3 Signal/make_signal_ws_from_json.py \
    --json outputs/signal_fits/signal_shape_params.json \
    --year 2018 \
    --proc GluGluToHH \
    --outdir Signal/SignalWS_mgg \
    --mgg 100,180

Author: ChatGPT (adapted for your flashggFinalFit-style workflow)
"""
import os
import sys
import json
import argparse
import math

try:
    import ROOT
except Exception as e:
    print("ERROR: could not import ROOT. Run this script inside a cmsenv / with a working PyROOT.")
    raise

def import_obj(ws, obj):
    """Helper to import RooFit objects into RooWorkspace safely (recycle names)."""
    # Use RecycleConflictNodes to reduce errors when re-using variable names
    getattr(ws, "import")(obj, ROOT.RooFit.RecycleConflictNodes(True))

def build_mgg_multigaus(ws, cat, means, sigmas, weights, mgg_range):
    """
    Build multi-Gaussian RooAddPdf inside ws for category `cat`.
    Returns the name of the created pdf.
    """
    # Ensure an 'mgg' observable is present
    if not ws.var("mgg"):
        mgg = ROOT.RooRealVar("mgg", "mgg", float(mgg_range[0]), float(mgg_range[1]))
        import_obj(ws, mgg)
    mgg = ws.var("mgg")

    n = len(means)
    if not (len(sigmas) == n and len(weights) == n):
        raise ValueError("Length mismatch between means/sigmas/weights for category %s" % str(cat))

    # Normalize weights to fractions for initial values
    wsum = sum(max(0.0, float(w)) for w in weights)
    if wsum <= 0:
        wnorm = [1.0 / n] * n
    else:
        wnorm = [max(0.0, float(w)) / wsum for w in weights]

    # Prepare lists for components and fractions
    comps = ROOT.RooArgList()
    fracs = ROOT.RooArgList()

    for i in range(n):
        mu_name = f"mgg_mu_c{cat}_g{i}"
        sig_name = f"mgg_sigma_c{cat}_g{i}"
        gaus_name = f"mgg_g_c{cat}_g{i}"

        mu_val = float(means[i])
        sigma_val = float(sigmas[i]) if float(sigmas[i]) > 0 else 1e-3

        # create RooRealVar for mean and sigma with sensible ranges
        mu = ROOT.RooRealVar(mu_name, "", mu_val, mgg.getMin(), mgg.getMax())
        # sigma lower bound small positive; upper bound = full mgg range (sane)
        sig_upper = max( (mgg.getMax()-mgg.getMin()), sigma_val*50.0, 1.0 )
        sigma = ROOT.RooRealVar(sig_name, "", sigma_val, 1e-4, sig_upper)

        # create gaussian
        gaus = ROOT.RooGaussian(gaus_name, "", mgg, mu, sigma)

        # import and add to componets
        import_obj(ws, mu)
        import_obj(ws, sigma)
        import_obj(ws, gaus)
        comps.add(ws.pdf(gaus_name))

        # For N components we only create N-1 fraction RooRealVars (RooAddPdf expects that)
        if i < n - 1:
            frac_name = f"mgg_frac_c{cat}_g{i}"
            frac_val = float(wnorm[i])
            frac = ROOT.RooRealVar(frac_name, "", frac_val, 0.0, 1.0)
            import_obj(ws, frac)
            fracs.add(ws.var(frac_name))

    pdf_name = f"pdf_mgg_c{cat}"
    pdf = ROOT.RooAddPdf(pdf_name, "", comps, fracs, True)
    import_obj(ws, pdf)
    return pdf_name

def make_ws_for_category(cat, best_params, year, proc, outdir, mgg_range):
    """
    Create a RooWorkspace for a single category and write it to a ROOT file.
    """
    wsname = f"wsig_{proc}_{year}_c{cat}"
    ws = ROOT.RooWorkspace(wsname, wsname)

    # Accept input best_params either as { 'means':[...], 'sigmas':[...], 'weights':[...]} OR
    # { 'best_params': { ... } } (matching some JSON layouts)
    params = best_params.get("best_params", best_params) if isinstance(best_params, dict) else best_params

    means = params.get("means")
    sigmas = params.get("sigmas")
    weights = params.get("weights", [1.0]*len(means) if means else None)

    if not (means and sigmas):
        raise ValueError(f"Category {cat}: JSON missing 'means' or 'sigmas' in provided params")

    # Build multi-gaussians
    pdf_mgg_name = build_mgg_multigaus(ws, cat, means, sigmas, weights, mgg_range)

    # Optional: if user provided a 'yield' value in params, create a RooRealVar for it
    if "yield" in params:
        yname = f"y_{proc}_c{cat}"
        yval = float(params["yield"])
        y = ROOT.RooRealVar(yname, "", yval)
        import_obj(ws, y)

    # Save
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, f"ws_signal_{proc}_{year}_c{cat}.root")
    fout = ROOT.TFile.Open(outfile, "RECREATE")
    if fout.IsZombie():
        raise IOError(f"Could not open output file {outfile} for writing")
    ws.Write()
    fout.Close()
    print(f"[OK] wrote {outfile} (workspace: {wsname}; pdf: {pdf_mgg_name})")

def parse_args():
    p = argparse.ArgumentParser(description="Export multi-Gaussian mgg signal fits to RooWorkspaces")
    p.add_argument("--json", required=True, help="Path to signal JSON (e.g. outputs/signal_fits/signal_shape_params.json)")
    p.add_argument("--year", default="2018", help="Year label (used in output workspace names)")
    p.add_argument("--proc", default="GluGluToHH", help="Process label used in workspace/filenames")
    p.add_argument("--outdir", default="SignalWS_mgg", help="Directory to write output root workspaces")
    p.add_argument("--mgg", default="100,180", help="Range for mgg as 'lo,hi' (default: 100,180)")
    p.add_argument("--verbose", action="store_true", help="Verbose prints")
    return p.parse_args()

def main():
    args = parse_args()

    # Basic checks
    if not os.path.isfile(args.json):
        print(f"ERROR: JSON file not found: {args.json}")
        sys.exit(2)

    try:
        mgg_range = tuple(map(float, args.mgg.split(",")))
        if len(mgg_range) != 2 or mgg_range[0] >= mgg_range[1]:
            raise ValueError()
    except Exception:
        print("ERROR: --mgg must be 'lo,hi' with lo < hi, e.g. --mgg 100,180")
        sys.exit(2)

    # Load JSON
    with open(args.json) as jf:
        data = json.load(jf)

    # JSON layout flexibility:
    # If top-level has "fits" key (as in your example), use that dict.
    # Otherwise, allow the user to pass a dict with categories directly.
    if isinstance(data, dict) and "fits" in data and isinstance(data["fits"], dict):
        fits = data["fits"]
    else:
        # Allow legacy formats where the file is already { "0": {...}, "1": {...} }
        fits = data

    if not fits:
        print("ERROR: no fits found in JSON. Check the file format.")
        sys.exit(2)

    outdir_year = os.path.join(args.outdir, str(args.year))
    print(f"Writing workspaces into: {outdir_year}")

    # Iterate categories
    for cat_str, fitobj in sorted(fits.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else x[0]):
        try:
            cat = int(cat_str)
        except Exception:
            # if category names are not integers, keep them as strings but use them in filenames
            cat = cat_str
        if args.verbose:
            print(f"[INFO] Building workspace for category {cat}")

        make_ws_for_category(cat, fitobj, args.year, args.proc, outdir_year, mgg_range)

    print("[DONE] All workspaces written.")

if __name__ == "__main__":
    main()
