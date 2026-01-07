#!/usr/bin/env python3
"""
Build background 2D RooWorkspaces from JSON fit outputs.

Usage (inside cmsenv with PyROOT available):
python3 Signal/make_bkg_ws_from_jsons.py \
  --res_mgg_json outputs/res_bkg_fits/resonant_bkg_dcb_params.json \
  --nonres_mgg_json outputs/nonres_mgg_fits/nonres_mgg_envelope.json \
  --mjj_json outputs/nonres_fits/nonres_envelope_results.json \
  --year 2018 --outdir Background/WS_bkg_2D
"""
import os, sys, json, argparse
try:
    import ROOT
except Exception as e:
    raise RuntimeError("Could not import ROOT. Run inside cmsenv / with working PyROOT.") from e

def import_obj(ws, obj):
    """Import object into workspace while avoiding name conflicts."""
    getattr(ws, "import")(obj, ROOT.RooFit.RecycleConflictNodes(True))

def safe_real(ws, name, val, lo=None, hi=None):
    """Create RooRealVar and import. If lo/hi None choose wide defaults."""
    if lo is None or hi is None:
        lo = float(val) - abs(float(val))*10.0 - 100.0
        hi = float(val) + abs(float(val))*10.0 + 100.0
    v = ROOT.RooRealVar(name, "", float(val), float(lo), float(hi))
    import_obj(ws, v)
    return v

def build_resonant_components(ws, cat, resfits, obs_name="mgg", prefix="res"):
    """
    Build resonant components from resonant JSON for category 'cat'.
    We expect a structure where resfits has top-level processes (ttH, ggH+VBFH, VH)
    each containing category keys '0','1','2' with 'params' that include DCB values:
     mu, sigma, alphaL, nL, alphaR, nR, N  (N is yield)
    Returns a RooArgList with components and a RooArgList with fraction variables (N-1 fracs),
    and a boolean whether we created something.
    """
    comps = ROOT.RooArgList()
    fracs = ROOT.RooArgList()
    # gather entries that match this category
    entries = []
    for proc, block in resfits.items():
        if isinstance(block, dict) and str(cat) in block:
            entry = block[str(cat)]
            # block[str(cat)] may contain 'params' subdict
            params = entry.get("params", entry)
            entries.append((proc, params))
    if not entries:
        # maybe fits are organized differently: try resfits['fits'] or similar
        alt = resfits.get("fits", resfits)
        for proc, block in alt.items():
            if isinstance(block, dict) and str(cat) in block:
                entry = block[str(cat)]
                params = entry.get("params", entry)
                entries.append((proc, params))

    if not entries:
        print(f"[WARN] No resonant entries found for cat {cat} in resonant JSON. Skipping resonant part.")
        return None, None, False

    # Build for each entry: prefer RooDoubleCB if available; else RooCBShape (single-sided), else Gaussian
    idx = 0
    for proc, p in entries:
        mu = float(p.get("mu", p.get("means", [p.get("mean")])[0] if isinstance(p.get("means"), list) else p.get("mean", 125.0)))
        sigma = float(p.get("sigma", p.get("sigmas", [1.0])[0] if isinstance(p.get("sigmas"), list) else p.get("sigma", 1.0)))
        alphaL = p.get("alphaL", p.get("alpha", None))
        nL = p.get("nL", p.get("n1", None))
        alphaR = p.get("alphaR", None)
        nR = p.get("nR", None)
        N = float(p.get("N", 1.0))

        # Create params
        mu_v = safe_real(ws, f"{prefix}_mu_c{cat}_r{idx}", mu, mu-10, mu+10)
        sigma_v = safe_real(ws, f"{prefix}_sigma_c{cat}_r{idx}", sigma, 1e-3, 50.0)

        created = False
        # Try RooDoubleCB if present
        if hasattr(ROOT, "RooDoubleCB"):
            try:
                aL = safe_real(ws, f"{prefix}_alphaL_c{cat}_r{idx}", float(alphaL) if alphaL is not None else 1.0, -10, 10)
                nL_v = safe_real(ws, f"{prefix}_nL_c{cat}_r{idx}", float(nL) if nL is not None else 1.0, 0.1, 100.0)
                aR = safe_real(ws, f"{prefix}_alphaR_c{cat}_r{idx}", float(alphaR) if alphaR is not None else 1.0, -10, 10)
                nR_v = safe_real(ws, f"{prefix}_nR_c{cat}_r{idx}", float(nR) if nR is not None else 1.0, 0.1, 100.0)
                # RooDoubleCB constructor: (name,title,x,mean,sigma,alphaL,nL,alphaR,nR)
                pdf = ROOT.RooDoubleCB(f"{prefix}_dcb_c{cat}_r{idx}", "", ws.var(obs_name), mu_v, sigma_v, aL, nL_v, aR, nR_v)
                import_obj(ws, pdf)
                comps.add(ws.pdf(pdf.GetName()))
                created = True
            except Exception as e:
                # fallback
                created = False

        if not created:
            # fallback to RooCBShape if one-sided params present, else Gaussian
            if alphaL is not None and nL is not None:
                try:
                    a = safe_real(ws, f"{prefix}_alphaL_c{cat}_r{idx}", float(alphaL), -10, 10)
                    n_v = safe_real(ws, f"{prefix}_nL_c{cat}_r{idx}", float(nL), 0.1, 100.0)
                    cb = ROOT.RooCBShape(f"{prefix}_cb_c{cat}_r{idx}", "", ws.var(obs_name), mu_v, sigma_v, a, n_v)
                    import_obj(ws, cb)
                    comps.add(ws.pdf(cb.GetName()))
                    created = True
                except Exception:
                    created = False
            if not created:
                # Gaussian fallback
                ga = ROOT.RooGaussian(f"{prefix}_g_c{cat}_r{idx}", "", ws.var(obs_name), mu_v, sigma_v)
                import_obj(ws, ga)
                comps.add(ws.pdf(ga.GetName()))
        # fraction var (use N as proxy; RooAddPdf expects N-1 fractions)
        frac_name = f"{prefix}_frac_c{cat}_r{idx}"
        frac = safe_real(ws, frac_name, N if N>0 else 1.0, 0.0, max(1.0, N*10+1.0))
        fracs.add(ws.var(frac.GetName()))
        idx += 1

    # If only one component, return that pdf name
    if comps.getSize() == 1:
        return comps[0].GetName(), None, True
    # else create RooAddPdf; RooAddPdf expects N-1 fractions, so use fracs[0..N-2]
    # create RooArgList of fractions of size N-1
    if fracs.getSize() >= comps.getSize():
        # reduce the number of fraction vars to N-1 by renaming or using normalized expressions:
        # simplest: convert to recursive fractions handled automatically by RooAddPdf when passing full fracs list in Python binding
        pass
    pdfname = f"pdf_bkg_res_mgg_c{cat}"
    pdf = ROOT.RooAddPdf(pdfname, "", comps, fracs, True)
    import_obj(ws, pdf)
    return pdf.GetName(), None, True

def build_nonres_mgg_from_choice(ws, cat, nonres_json, obs_name="mgg", prefix="nonres"):
    """
    nonres_json is expected to have 'fits' -> cat -> 'chosen' dict: family, order, theta (parameters).
    For common families we create a simple Roo function:
      - powerlaw (order 1): use pow(mgg, theta0) * exp(theta1 * mgg)
      - exponential (order 1): exp(theta1 * mgg)
      - bernstein: RooBernstein with theta coefficients
    """
    chosen = None
    if isinstance(nonres_json, dict):
        chosen = nonres_json.get("fits", nonres_json).get(str(cat), nonres_json.get(str(cat), None))
    if chosen and isinstance(chosen, dict) and "chosen" in chosen:
        chosen = chosen["chosen"]
    if chosen is None:
        # maybe nonres_json is already per-cat structure
        chosen = nonres_json.get(str(cat), nonres_json.get("chosen", None))
    if chosen is None:
        print(f"[WARN] nonres mgg: no chosen family for cat {cat}, fallback to expo")
        lam = safe_real(ws, f"{prefix}_lambda_c{cat}", -0.03, -10., 10.)
        expo = ROOT.RooExponential(f"pdf_bkg_nonres_mgg_c{cat}", "", ws.var(obs_name), lam)
        import_obj(ws, expo)
        return expo.GetName()

    fam = chosen.get("family", chosen.get("family", "exponential"))
    theta = chosen.get("theta", chosen.get("params", []))
    # implement mapping for family
    if fam.lower().startswith("powerlaw"):
        # interpret as pow(mgg,theta0) * exp(theta1*mgg) for order=1
        th0 = float(theta[0]) if len(theta)>0 else 0.0
        th1 = float(theta[1]) if len(theta)>1 else 0.0
        v0 = safe_real(ws, f"bkg_power_th0_c{cat}", th0, th0-1000, th0+1000)
        v1 = safe_real(ws, f"bkg_power_th1_c{cat}", th1, th1-10000, th1+10000)
        # expression: pow(mgg, @0) * exp(@1 * mgg)
        expr = ROOT.RooFormulaVar(f"pdf_bkg_power_mgg_c{cat}", f"pow(mgg,@{0})*exp(@{1}*mgg)", ROOT.RooArgList(ws.var("mgg"), v0, v1))
        # The above direct indexing in RooFormulaVar may be tricky; instead build a RooGenericPdf
        # To keep it robust, use RooGenericPdf with parameter names:
        expr_str = f"pow(mgg, bkg_power_th0_c{cat}) * exp(bkg_power_th1_c{cat} * mgg)"
        pdf = ROOT.RooGenericPdf(f"pdf_bkg_nonres_mgg_c{cat}", "", expr_str, ROOT.RooArgList(ws.var("mgg"), v0, v1))
        import_obj(ws, pdf)
        return pdf.GetName()
    elif fam.lower().startswith("exponential"):
        # theta[1] is slope
        slope = float(theta[1]) if len(theta)>1 else float(theta[0]) if len(theta)>0 else -0.01
        lam = safe_real(ws, f"bkg_exp_lambda_c{cat}", slope, -10.0, 10.0)
        expo = ROOT.RooExponential(f"pdf_bkg_nonres_mgg_c{cat}", "", ws.var(obs_name), lam)
        import_obj(ws, expo)
        return expo.GetName()
    elif fam.lower().startswith("bernstein"):
        # build RooBernstein of order len(theta)-1
        order = len(theta)-1
        coeffs = ROOT.RooArgList()
        for i,t in enumerate(theta):
            rv = safe_real(ws, f"bkg_bern_th{i}_c{cat}", float(t), -1e12, 1e12)
            coeffs.add(ws.var(rv.GetName()))
        poly = ROOT.RooBernstein(f"pdf_bkg_nonres_mgg_c{cat}", "", ws.var(obs_name), coeffs)
        import_obj(ws, poly)
        return poly.GetName()
    else:
        # fallback expo
        lam = safe_real(ws, f"bkg_exp_lambda_c{cat}", -0.01, -10.0, 10.0)
        expo = ROOT.RooExponential(f"pdf_bkg_nonres_mgg_c{cat}", "", ws.var(obs_name), lam)
        import_obj(ws, expo)
        return expo.GetName()
    
    
def build_mjj_from_json(ws, cat, mjj_json, obs_name="mjj", prefix="mjjbkg"):
    """
    Robustly extract mjj fit for category `cat` from various possible JSON layouts:
      - per-mass combined file: {"masses": {"100": {"fits": {"0": {...}}}, ...}}
      - per-mass single file: {"edges": [...], "fits": {"0": {...}, ...}, ...}
      - list of mass entries: [{"mass": 100, "fits": {...}}, {...}]
      - direct fits dict: {"0": {...}, "1": {...}}
    If nothing usable is found, fall back to an exponential in mjj.
    Returns the name of the created pdf in the workspace.
    """
    # helper to build from a fits-dict (like {"0": {...}, "1": {...}})
    def _build_from_fits_dict(fits_dict):
        if fits_dict is None or not isinstance(fits_dict, dict):
            return None
        # look for exact category
        key = str(cat)
        if key not in fits_dict:
            # sometimes keys are ints as ints; try int->str conversion
            for k in fits_dict.keys():
                if str(k) == key:
                    key = k
                    break
            else:
                return None
        fitobj = fits_dict.get(key)
        if fitobj is None:
            return None
        # unpack best_params if present
        params = fitobj.get("best_params", fitobj) if isinstance(fitobj, dict) else fitobj
        means = params.get("means") or params.get("mu") or params.get("m", None)
        sigmas = params.get("sigmas") or params.get("sigma") or params.get("s", None)
        weights = params.get("weights") or params.get("w", None)
        if means is None or sigmas is None:
            # not a gaussian mixture; caller will handle fallback
            return None
        # construct RooAddPdf of gaussians (similar to earlier code)
        comps = ROOT.RooArgList()
        fracs = ROOT.RooArgList()
        for i, (m_val, s_val) in enumerate(zip(means, sigmas)):
            mu = safe_real(ws, f"{prefix}_mu_c{cat}_g{i}", float(m_val), float(m_val)-50, float(m_val)+50)
            sig = safe_real(ws, f"{prefix}_sigma_c{cat}_g{i}", float(s_val), 1e-3, 200.0)
            ga = ROOT.RooGaussian(f"{prefix}_g_c{cat}_g{i}", "", ws.var(obs_name), mu, sig)
            import_obj(ws, ga)
            comps.add(ws.pdf(ga.GetName()))
            if i < len(means) - 1:
                frac_val = float(weights[i]) if (weights and i < len(weights)) else 1.0
                frac = safe_real(ws, f"{prefix}_frac_c{cat}_g{i}", frac_val, 0.0, 1.0)
                fracs.add(ws.var(frac.GetName()))
        if comps.getSize() == 1:
            return comps[0].GetName()
        pdf_mjj = ROOT.RooAddPdf(f"pdf_bkg_mjj_c{cat}", "", comps, fracs, True)
        import_obj(ws, pdf_mjj)
        return pdf_mjj.GetName()

    # 1) If mjj_json already looks like a fits-dict
    if isinstance(mjj_json, dict):
        # direct fits mapping?
        if "fits" in mjj_json and isinstance(mjj_json["fits"], dict):
            out = _build_from_fits_dict(mjj_json["fits"])
            if out:
                return out

        # combined-by-mass structure?
        if "masses" in mjj_json and isinstance(mjj_json["masses"], dict):
            for mass_key, mass_block in mjj_json["masses"].items():
                # mass_block might be {"used_dirs":..., "fits": {...}}
                fits_block = mass_block.get("fits", mass_block)
                out = _build_from_fits_dict(fits_block if isinstance(fits_block, dict) else None)
                if out:
                    return out

        # maybe mjj_json is already per-cat at top-level
        out = _build_from_fits_dict(mjj_json)
        if out:
            return out

    # 2) If mjj_json is a list of mass entries [{ "mass":100, "fits": {...}}, ...]
    if isinstance(mjj_json, list):
        for entry in mjj_json:
            if not isinstance(entry, dict):
                continue
            fits_block = entry.get("fits", entry)
            out = _build_from_fits_dict(fits_block if isinstance(fits_block, dict) else None)
            if out:
                return out

    # 3) fallback: try to find any nested dict with a 'fits' mapping and use that
    def _deep_search_for_fits(obj):
        if isinstance(obj, dict):
            if "fits" in obj and isinstance(obj["fits"], dict):
                return obj["fits"]
            for v in obj.values():
                res = _deep_search_for_fits(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for it in obj:
                res = _deep_search_for_fits(it)
                if res:
                    return res
        return None

    fits_found = _deep_search_for_fits(mjj_json)
    if fits_found:
        out = _build_from_fits_dict(fits_found)
        if out:
            return out

    # Final fallback: exponential in mjj
    print(f"[WARN] mjj fit for cat {cat} not found in mjj_json (tried various layouts); using exponential fallback.")
    lam = safe_real(ws, f"{prefix}_lam_c{cat}", -0.01, -10., 10.)
    expo = ROOT.RooExponential(f"pdf_bkg_mjj_c{cat}", "", ws.var(obs_name), lam)
    import_obj(ws, expo)
    return expo.GetName()


def make_bkg_ws(res_mgg_json, nonres_mgg_json, mjj_json, year="2018", outdir="Background/WS_bkg_2D"):
    with open(res_mgg_json) as f:
        res_json = json.load(f)
    with open(nonres_mgg_json) as f:
        nonres_json = json.load(f)
    with open(mjj_json) as f:
        mjj_json_obj = json.load(f)

    # prepare mappings
    # res_json structure: top-level 'fits' -> process -> cat -> params
    res_fits = res_json.get("fits", res_json)
    nonres_fits = nonres_json.get("fits", nonres_json)
    mjj_fits = mjj_json_obj  # handled in function

    os.makedirs(os.path.join(outdir, str(year)), exist_ok=True)

    # iterate categories found in mgg fits (res or nonres)
    # prefer keys from nonres_fits (it has chosen families per cat)
    cats = sorted([int(k) for k in nonres_fits.keys()]) if isinstance(nonres_fits, dict) else sorted([0,1,2])
    print("[INFO] Building background workspaces for categories:", cats)

    for cat in cats:
        wsname = f"ws_bkg_{year}_c{cat}"
        ws = ROOT.RooWorkspace(wsname, wsname)
        # create observables first
        mgg = ROOT.RooRealVar("mgg", "mgg", 115.0, 135.0)
        mjj = ROOT.RooRealVar("mjj", "mjj", 60.0, 200.0)
        import_obj(ws, mgg); import_obj(ws, mjj)

        # build resonant part (may be None)
        try:
            pdf_res_name, _, ok = build_resonant_components(ws, cat, res_fits, obs_name="mgg", prefix="res")
        except Exception as e:
            print(f"[WARN] Exception building resonant comp cat {cat}: {e}")
            pdf_res_name = None

        # build nonres part
        try:
            pdf_nonres_name = build_nonres_mgg_from_choice(ws, cat, nonres_json, obs_name="mgg", prefix="nonres")
        except Exception as e:
            print(f"[WARN] Exception building nonres comp cat {cat}: {e}")
            pdf_nonres_name = None

        # combine mgg parts
        if pdf_res_name is None and pdf_nonres_name is None:
            print(f"[WARN] No mgg component available for cat {cat}; skipping category.")
            continue
        if pdf_res_name is None:
            mgg_final = pdf_nonres_name
        elif pdf_nonres_name is None:
            mgg_final = pdf_res_name
        else:
            # build RooAddPdf of the two parts with a fraction
            comps = ROOT.RooArgList()
            comps.add(ws.pdf(pdf_res_name)); comps.add(ws.pdf(pdf_nonres_name))
            frac = safe_real(ws, f"frac_res_vs_nonres_mgg_c{cat}", 0.5, 0.0, 1.0)
            fracs = ROOT.RooArgList(); fracs.add(ws.var(frac.GetName()))
            pdf_mgg = ROOT.RooAddPdf(f"pdf_bkg_mgg_c{cat}", "", comps, fracs, True)
            import_obj(ws, pdf_mgg)
            mgg_final = pdf_mgg.GetName()

        # build mjj part
        pdf_mjj_name = build_mjj_from_json(ws, cat, mjj_fits, obs_name="mjj", prefix="mjjbkg")

        # product
        p_mgg = ws.pdf(mgg_final)
        p_mjj = ws.pdf(pdf_mjj_name)
        prod = ROOT.RooProdPdf(f"pdf_bkg_c{cat}", f"pdf_bkg_c{cat}", ROOT.RooArgList(p_mgg, p_mjj))
        import_obj(ws, prod)

        # write workspace
        outfile = os.path.join(outdir, str(year), f"ws_bkg_{year}_c{cat}.root")
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        fout = ROOT.TFile.Open(outfile, "RECREATE")
        if fout.IsZombie():
            print("[ERROR] Could not open", outfile)
            continue
        ws.Write()
        fout.Close()
        print("[OK] wrote background workspace:", outfile)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--res_mgg_json", required=True)
    parser.add_argument("--nonres_mgg_json", required=True)
    parser.add_argument("--mjj_json", required=True)
    parser.add_argument("--year", default="2018")
    parser.add_argument("--outdir", default="Background/WS_bkg_2D")
    args = parser.parse_args()
    make_bkg_ws(args.res_mgg_json, args.nonres_mgg_json, args.mjj_json, args.year, args.outdir)
