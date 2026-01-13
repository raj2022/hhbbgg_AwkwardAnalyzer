#!/usr/bin/env python3
"""
make_signal_ws_2D_from_jsons_syst.py

Build 2D signal RooWorkspaces (mgg × mjj) with parametric shape systematics.

Systematics implemented:
  - mgg scale   → mean
  - mgg smear  → width
  - mjj JEC    → mean
  - mjj JER    → width

JSON inputs:
  - mgg_json  : outputs/signal_fits/signal_shape_params.json
  - mjj_json  : outputs/signal_fits_mjj_by_mass/signal_mjj_params_by_mass.json
  - syst_json : outputs/systematics/signal_kappas.json
"""

import os
import json
import argparse
import ROOT

ROOT.gROOT.SetBatch(True)

# -----------------------------------------------------------------------------
def import_obj(ws, obj):
    getattr(ws, "import")(obj, ROOT.RooFit.RecycleConflictNodes(True))

# -----------------------------------------------------------------------------
def parse_fitobj(fitobj):
    """Extract means, sigmas, weights from fit JSON."""
    if "best_params" in fitobj:
        fitobj = fitobj["best_params"]

    means   = fitobj["means"]
    sigmas  = fitobj["sigmas"]
    weights = fitobj.get("weights", [1.0] * len(means))

    wsum = sum(weights)
    weights = [w / wsum for w in weights]

    return means, sigmas, weights

# -----------------------------------------------------------------------------
def build_gauss_mixture(
    ws, obs, cat,
    means, sigmas, weights,
    prefix,
    theta_mu,
    theta_sig,
    kappa_mu,
    kappa_sig
):
    """
    Build RooAddPdf of Gaussians with parametric mean/width systematics.
    """

    comps = ROOT.RooArgList()
    fracs = ROOT.RooArgList()

    obs_range = obs.getMax() - obs.getMin()

    for i, (m, s, w) in enumerate(zip(means, sigmas, weights)):

        # nominal parameters
        mu0 = ROOT.RooRealVar(
            f"{prefix}_mu0_c{cat}_g{i}", "", m,
            obs.getMin(), obs.getMax()
        )
        sig0 = ROOT.RooRealVar(
            f"{prefix}_sig0_c{cat}_g{i}", "", s,
            1e-4, obs_range
        )
        import_obj(ws, mu0)
        import_obj(ws, sig0)

        # parametric systematics
        mu = ROOT.RooFormulaVar(
            f"{prefix}_mu_c{cat}_g{i}",
            "@0*(1 + @1*@2)",
            ROOT.RooArgList(mu0, theta_mu, ROOT.RooConst(kappa_mu))
        )
        sig = ROOT.RooFormulaVar(
            f"{prefix}_sig_c{cat}_g{i}",
            "@0*(1 + @1*@2)",
            ROOT.RooArgList(sig0, theta_sig, ROOT.RooConst(kappa_sig))
        )
        import_obj(ws, mu)
        import_obj(ws, sig)

        g = ROOT.RooGaussian(
            f"{prefix}_g_c{cat}_g{i}", "", obs, mu, sig
        )
        import_obj(ws, g)
        comps.add(ws.pdf(g.GetName()))

        if i < len(weights) - 1:
            frac = ROOT.RooRealVar(
                f"{prefix}_frac_c{cat}_g{i}", "", weights[i], 0., 1.
            )
            import_obj(ws, frac)
            fracs.add(frac)

    pdf = ROOT.RooAddPdf(
        f"pdf_{prefix}_c{cat}", "", comps, fracs, True
    )
    import_obj(ws, pdf)
    return pdf

# -----------------------------------------------------------------------------
def make_ws(cat, mgg_fit, mjj_fit, syst, args):

    ws = ROOT.RooWorkspace(
        f"wsig2d_{args.proc}_{args.year}_c{cat}"
    )

    # observables
    mgg = ROOT.RooRealVar("mgg", "mgg", *args.mgg_range)
    mjj = ROOT.RooRealVar("mjj", "mjj", *args.mjj_range)
    import_obj(ws, mgg)
    import_obj(ws, mjj)

    # ---------------- nuisances ----------------
    th_mgg_scale = ROOT.RooRealVar("CMS_scale_ee",  "", 0, -5, 5)
    th_mgg_smear = ROOT.RooRealVar("CMS_smear_ee",  "", 0, -5, 5)
    th_jec       = ROOT.RooRealVar("CMS_jec",       "", 0, -5, 5)
    th_jer       = ROOT.RooRealVar("CMS_jer",       "", 0, -5, 5)

    nuisances = [th_mgg_scale, th_mgg_smear, th_jec, th_jer]

    # for t in nuisances:
    #     import_obj(ws, t)
    #     constr = ROOT.RooGaussian(
    #         f"{t.GetName()}_constraint", "",
    #         t, ROOT.RooConst(0), ROOT.RooConst(1)
    #     )
    #     import_obj(ws, constr)

    
    for t in nuisances:
        import_obj(ws, t)

    ws.defineSet(
        "nuisances",
        "CMS_scale_ee,CMS_smear_ee,CMS_jec,CMS_jer"
    )

    ws.defineSet(
    "globalObservables",
    ""
    )


    
    
    
    # ---------------- mgg PDF ----------------
    mgg_means, mgg_sigmas, mgg_weights = parse_fitobj(mgg_fit)
    pdf_mgg = build_gauss_mixture(
        ws, mgg, cat,
        mgg_means, mgg_sigmas, mgg_weights,
        "mgg",
        theta_mu  = th_mgg_scale,
        theta_sig = th_mgg_smear,
        kappa_mu  = syst["mgg_scale"],
        kappa_sig = syst["mgg_smear"]
    )

    # ---------------- mjj PDF ----------------
    mjj_means, mjj_sigmas, mjj_weights = parse_fitobj(mjj_fit)
    pdf_mjj = build_gauss_mixture(
        ws, mjj, cat,
        mjj_means, mjj_sigmas, mjj_weights,
        "mjj",
        theta_mu  = th_jec,
        theta_sig = th_jer,
        kappa_mu  = syst["mjj_jec_mu"],
        kappa_sig = syst["mjj_jer_sig"]
    )

    # ---------------- 2D signal PDF ----------------
    sig = ROOT.RooProdPdf(
        f"sig_{args.proc}_c{cat}", "",
        ROOT.RooArgList(
            ws.pdf(pdf_mgg.GetName()),
            ws.pdf(pdf_mjj.GetName())
        )
    )
    import_obj(ws, sig)

    return ws

# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mgg_json", required=True)
    ap.add_argument("--mjj_json", required=True)
    ap.add_argument("--syst_json", required=True)
    ap.add_argument("--mass", required=True)
    ap.add_argument("--year", required=True)
    ap.add_argument("--proc", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--mgg", required=True)
    ap.add_argument("--mjj", required=True)
    args = ap.parse_args()

    args.mgg_range = list(map(float, args.mgg.split(",")))
    args.mjj_range = list(map(float, args.mjj.split(",")))

    mgg_all  = json.load(open(args.mgg_json))
    mjj_all  = json.load(open(args.mjj_json))
    syst_all = json.load(open(args.syst_json))

    if "masses" not in mjj_all or args.mass not in mjj_all["masses"]:
        raise RuntimeError(f"Mass {args.mass} not found in mjj JSON")

    mjj_mass = mjj_all["masses"][args.mass]

    os.makedirs(args.outdir, exist_ok=True)

    for c in mgg_all["fits"]:
        if c not in mjj_mass:
            continue

        ws = make_ws(
            int(c),
            mgg_all["fits"][c],
            mjj_mass[c],
            syst_all[c],
            args
        )

        out = f"{args.outdir}/ws_signal2D_{args.proc}_{args.year}_c{c}.root"
        fout = ROOT.TFile.Open(out, "RECREATE")
        ws.Write()
        fout.Close()

        print(f"[OK] wrote {out}")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
