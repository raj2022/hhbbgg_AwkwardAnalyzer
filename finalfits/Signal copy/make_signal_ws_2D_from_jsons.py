#!/usr/bin/env python3
"""
make_signal_ws_2D_from_jsons.py

Reads two JSONs:
 - mgg_json: your existing multi-Gaussian fits for mgg (e.g. outputs/signal_fits/signal_shape_params.json)
 - mjj_json: fits for mjj (e.g. outputs/signal_fits_mjj_fast/xxx.json)

Creates per-category RooWorkspaces containing:
 - RooRealVar mgg, RooRealVar mjj
 - pdf_mgg_c{cat} (RooAddPdf of Gaussians)
 - pdf_mjj_c{cat} (RooAddPdf of Gaussians)  <- if mjj JSON is different, script may need small adaptation
 - RooProdPdf sig_<proc>_c{cat} = pdf_mgg_c{cat} * pdf_mjj_c{cat}

Usage example (from $CMSSW_BASE/src):
  cmsenv
  python3 Signal/make_signal_ws_2D_from_jsons.py \
    --mgg_json outputs/signal_fits/signal_shape_params.json \
    --mjj_json outputs/signal_fits_mjj_fast/signal_mjj.json \
    --year 2018 \
    --proc GluGluToHH \
    --outdir Signal/SignalWS_2D \
    --mgg 100,180 --mjj 60,200 --verbose
"""
import os, sys, json, argparse
try:
    import ROOT
except Exception:
    print("ERROR: could not import ROOT. Run inside cmsenv / with working PyROOT.")
    raise

def import_obj(ws, obj):
    getattr(ws, "import")(obj, ROOT.RooFit.RecycleConflictNodes(True))

def build_gauss_mixture(ws, obs_name, cat, means, sigmas, weights, prefix):
    """Build pdf_{prefix}_c{cat} as RooAddPdf of Gaussians for observable obs_name."""
    # ensure observable exists
    if not ws.var(obs_name):
        # default ranges will be set externally so give wide defaults if needed
        if obs_name == "mgg":
            var = ROOT.RooRealVar("mgg","mgg", 100., 180.)
        else:
            var = ROOT.RooRealVar("mjj","mjj", 20., 400.)
        import_obj(ws, var)
    obs = ws.var(obs_name)
    n = len(means)
    if not (len(sigmas) == n and len(weights) == n):
        raise ValueError(f"Length mismatch for {prefix} components cat{cat}")

    wsum = sum(max(0.0,float(w)) for w in weights)
    wnorm = [max(0.0,float(w))/wsum if wsum>0 else 1.0/n for w in weights]

    comps = ROOT.RooArgList()
    fracs = ROOT.RooArgList()
    for i in range(n):
        mu = ROOT.RooRealVar(f"{prefix}_mu_c{cat}_g{i}","", float(means[i]), obs.getMin(), obs.getMax())
        sigval = max(1e-4, float(sigmas[i]))
        sig = ROOT.RooRealVar(f"{prefix}_sigma_c{cat}_g{i}","", sigval, 1e-4, max((obs.getMax()-obs.getMin()), sigval*50, 1.0))
        g = ROOT.RooGaussian(f"{prefix}_g_c{cat}_g{i}","", obs, mu, sig)
        import_obj(ws, mu); import_obj(ws, sig); import_obj(ws, g)
        comps.add(ws.pdf(g.GetName()))
        if i < n-1:
            frac = ROOT.RooRealVar(f"{prefix}_frac_c{cat}_g{i}","", wnorm[i], 0.0, 1.0)
            import_obj(ws, frac)
            fracs.add(ws.var(frac.GetName()))

    pdfname = f"pdf_{prefix}_c{cat}"
    pdf = ROOT.RooAddPdf(pdfname, "", comps, fracs, True)
    import_obj(ws, pdf)
    return pdfname

def parse_fitobj(fitobj):
    """Normalize fitobj to contain 'means','sigmas','weights' keys. Accepts your mgg JSON structure."""
    # If nested (like {"best_params": {...}}) unpack it
    if isinstance(fitobj, dict) and "best_params" in fitobj:
        params = fitobj["best_params"]
    else:
        params = fitobj
    means = params.get("means")
    sigmas = params.get("sigmas")
    weights = params.get("weights", [1.0]*len(means) if means else None)
    if means is None or sigmas is None:
        raise ValueError("Fit object missing 'means' or 'sigmas'")
    return means, sigmas, weights

def make_2d_ws_for_cat(cat, mgg_fitobj, mjj_fitobj, year, proc, outdir, mgg_range, mjj_range):
    wsname = f"wsig2d_{proc}_{year}_c{cat}"
    ws = ROOT.RooWorkspace(wsname, wsname)

    # create observables with specified ranges
    mgg = ROOT.RooRealVar("mgg","mgg", float(mgg_range[0]), float(mgg_range[1]))
    mjj = ROOT.RooRealVar("mjj","mjj", float(mjj_range[0]), float(mjj_range[1]))
    import_obj(ws, mgg); import_obj(ws, mjj)

    # build pdfs
    mgg_means, mgg_sigmas, mgg_weights = parse_fitobj(mgg_fitobj)
    mjj_means, mjj_sigmas, mjj_weights = parse_fitobj(mjj_fitobj)

    pdf_mgg = build_gauss_mixture(ws, "mgg", cat, mgg_means, mgg_sigmas, mgg_weights, "mgg")
    pdf_mjj = build_gauss_mixture(ws, "mjj", cat, mjj_means, mjj_sigmas, mjj_weights, "mjj")

    # product
    p_mgg = ws.pdf(pdf_mgg)
    p_mjj = ws.pdf(pdf_mjj)
    prod = ROOT.RooProdPdf(f"sig_{proc}_c{cat}", f"sig_{proc}_c{cat}", ROOT.RooArgList(p_mgg, p_mjj))
    import_obj(ws, prod)

    # save
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, f"ws_signal2D_{proc}_{year}_c{cat}.root")
    fout = ROOT.TFile.Open(outfile, "RECREATE")
    if fout.IsZombie():
        raise IOError("Could not open output file " + outfile)
    ws.Write()
    fout.Close()
    print(f"[OK] wrote {outfile} (workspace: {wsname})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mgg_json", required=True)
    ap.add_argument("--mjj_json", required=True)
    ap.add_argument("--year", default="2018")
    ap.add_argument("--proc", default="GluGluToHH")
    ap.add_argument("--outdir", default="SignalWS_2D")
    ap.add_argument("--mgg", default="100,180")
    ap.add_argument("--mjj", default="60,200")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.mgg_json):
        print("ERROR: mgg_json not found:", args.mgg_json); sys.exit(2)
    if not os.path.isfile(args.mjj_json):
        print("ERROR: mjj_json not found:", args.mjj_json); sys.exit(2)

    with open(args.mgg_json) as f: mgg_data = json.load(f)
    with open(args.mjj_json) as f: mjj_data = json.load(f)

    mgg_fits = mgg_data.get("fits", mgg_data)
    mjj_fits = mjj_data.get("fits", mjj_data)

    mgg_range = tuple(map(float, args.mgg.split(",")))
    mjj_range = tuple(map(float, args.mjj.split(",")))

    for cat_str, mgg_fitobj in sorted(mgg_fits.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        if cat_str not in mjj_fits:
            print(f"[WARN] category {cat_str} in mgg but not in mjj - skipping")
            continue
        mjj_fitobj = mjj_fits[cat_str]
        cat = int(cat_str) if cat_str.isdigit() else cat_str
        if args.verbose: print(f"[INFO] Building 2D ws for cat {cat}")
        outdir_year = os.path.join(args.outdir, str(args.year))
        make_2d_ws_for_cat(cat, mgg_fitobj, mjj_fitobj, args.year, args.proc, outdir_year, mgg_range, mjj_range)

if __name__ == "__main__":
    main()
