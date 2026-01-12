#!/usr/bin/env python3
# ============================================================
# make_templates.py
#
# Systematic template production for HH → bbγγ
# Parquet-based, analyzer-schema-complete version
#
# SAFE, FINAL VERSION
# ============================================================

import argparse
from pathlib import Path

import numpy as np
import awkward as ak
import pyarrow.parquet as pq
import ROOT

from config.utils import lVector
from config.config import RunConfig

# ---------------- ROOT setup ----------------
ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False)

# ---------------- Helpers ----------------
def ensure_dir(rootfile, path):
    curr = rootfile
    for p in path.split("/"):
        d = curr.GetDirectory(p)
        curr = d if d else curr.mkdir(p)
    curr.cd()

def make_th1(values, weights, name, binning):
    v = np.asarray(values)
    w = np.asarray(weights)
    m = np.isfinite(v) & np.isfinite(w)
    v, w = v[m], w[m]

    if isinstance(binning, (list, tuple)):
        nb, lo, hi = binning
        h = ROOT.TH1D(name, name, nb, lo, hi)
        edges = np.linspace(lo, hi, nb + 1)
    else:
        edges = np.asarray(binning, dtype="f8")
        h = ROOT.TH1D(name, name, len(edges) - 1, edges)

    c, _  = np.histogram(v, bins=edges, weights=w)
    e2, _ = np.histogram(v, bins=edges, weights=w * w)

    h.Sumw2()
    for i in range(1, h.GetNbinsX() + 1):
        h.SetBinContent(i, c[i - 1])
        h.SetBinError(i, np.sqrt(e2[i - 1]))

    return h

# ---------------- Analysis definitions ----------------
from regions import (
    get_mask_preselection,
    get_mask_selection,
)

from variables import vardict, variables_common
from binning import binning

ACTIVE_REGIONS = ["preselection", "selection"]

# ---------------- Systematics ----------------
SYSTEMATICS = [
    "nominal",
    "jec_syst_Total_up",
    "jec_syst_Total_down",
    "jer_syst_up",
    "jer_syst_down",
    "ScaleEE2G_IJazZ_up",
    "ScaleEE2G_IJazZ_down",
    "Smearing2G_IJazZ_up",
    "Smearing2G_IJazZ_down",
]

# ---------------- Required Parquet Columns ----------------
REQUIRED_COLUMNS = [
    "run","lumi","event",

    # photons
    "lead_pt","lead_eta","lead_phi",
    "sublead_pt","sublead_eta","sublead_phi",
    "lead_mvaID_WP90","lead_mvaID_WP80",
    "sublead_mvaID_WP90","sublead_mvaID_WP80",
    "lead_isScEtaEB","sublead_isScEtaEB",

    # jets
    "Res_lead_bjet_pt","Res_lead_bjet_eta","Res_lead_bjet_phi","Res_lead_bjet_mass",
    "Res_sublead_bjet_pt","Res_sublead_bjet_eta","Res_sublead_bjet_phi","Res_sublead_bjet_mass",
    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
    "Res_lead_bjet_PNetRegPtRawRes","Res_sublead_bjet_PNetRegPtRawRes",

    # HH
    "Res_HHbbggCandidate_mass",
    "Res_HHbbggCandidate_pt",
    "Res_HHbbggCandidate_eta",
    "Res_HHbbggCandidate_phi",

    # topology
    "Res_CosThetaStar_CS",
    "Res_CosThetaStar_gg",
    "Res_CosThetaStar_jj",
    "Res_DeltaR_jg_min",
    "Res_DeltaPhi_j1MET",
    "Res_DeltaPhi_j2MET",
    "Res_chi_t0",
    "Res_chi_t1",

    # leptons
    "lepton1_mvaID",
    "lepton1_pfIsoId",
    "lepton1_pt",

    "n_jets",
    "weight",
]

# ---------------- Core processing ----------------
def process_systematic(signal_dir, syst, fout):

    signal_name = signal_dir.name
    syst_dir = signal_dir / syst
    files = sorted(syst_dir.rglob("*.parquet"))

    if not files:
        print(f"[WARN] No parquet files in {syst_dir}")
        return

    print(f"[INFO] Systematic: {signal_name}/{syst} ({len(files)} files)")

    for pf in files:
        pqf = pq.ParquetFile(pf)

        for batch in pqf.iter_batches(batch_size=20000, columns=REQUIRED_COLUMNS):
            tree = ak.from_arrow(batch)

            # -------- base event --------
            ev = ak.zip(
                {
                    # photons
                    "lead_pho_pt": tree["lead_pt"],
                    "lead_pho_eta": tree["lead_eta"],
                    "lead_pho_phi": tree["lead_phi"],
                    "lead_pho_mvaID_WP90": tree["lead_mvaID_WP90"],
                    "lead_pho_mvaID_WP80": tree["lead_mvaID_WP80"],
                    "lead_isScEtaEB": tree["lead_isScEtaEB"],

                    "sublead_pho_pt": tree["sublead_pt"],
                    "sublead_pho_eta": tree["sublead_eta"],
                    "sublead_pho_phi": tree["sublead_phi"],
                    "sublead_pho_mvaID_WP90": tree["sublead_mvaID_WP90"],
                    "sublead_pho_mvaID_WP80": tree["sublead_mvaID_WP80"],
                    "sublead_isScEtaEB": tree["sublead_isScEtaEB"],

                    # jets
                    "lead_bjet_pt": tree["Res_lead_bjet_pt"],
                    "lead_bjet_eta": tree["Res_lead_bjet_eta"],
                    "lead_bjet_phi": tree["Res_lead_bjet_phi"],
                    "lead_bjet_mass": tree["Res_lead_bjet_mass"],
                    "lead_bjet_PNetB": tree["Res_lead_bjet_btagPNetB"],
                    "lead_bjet_PNetRegPtRawRes": tree["Res_lead_bjet_PNetRegPtRawRes"],

                    "sublead_bjet_pt": tree["Res_sublead_bjet_pt"],
                    "sublead_bjet_eta": tree["Res_sublead_bjet_eta"],
                    "sublead_bjet_phi": tree["Res_sublead_bjet_phi"],
                    "sublead_bjet_mass": tree["Res_sublead_bjet_mass"],
                    "sublead_bjet_PNetB": tree["Res_sublead_bjet_btagPNetB"],
                    "sublead_bjet_PNetRegPtRawRes": tree["Res_sublead_bjet_PNetRegPtRawRes"],

                    # HH
                    "bbgg_mass": tree["Res_HHbbggCandidate_mass"],
                    "bbgg_pt": tree["Res_HHbbggCandidate_pt"],
                    "bbgg_eta": tree["Res_HHbbggCandidate_eta"],
                    "bbgg_phi": tree["Res_HHbbggCandidate_phi"],

                    # topology
                    "CosThetaStar_CS": tree["Res_CosThetaStar_CS"],
                    "CosThetaStar_gg": tree["Res_CosThetaStar_gg"],
                    "CosThetaStar_jj": tree["Res_CosThetaStar_jj"],
                    "DeltaR_jg_min": tree["Res_DeltaR_jg_min"],
                    "DeltaPhi_j1MET": tree["Res_DeltaPhi_j1MET"],
                    "DeltaPhi_j2MET": tree["Res_DeltaPhi_j2MET"],
                    "Res_chi_t0": tree["Res_chi_t0"],
                    "Res_chi_t1": tree["Res_chi_t1"],

                    # leptons
                    "lepton1_mvaID": tree["lepton1_mvaID"],
                    "lepton1_pfIsoId": tree["lepton1_pfIsoId"],
                    "lepton1_pt": tree["lepton1_pt"],

                    "n_jets": tree["n_jets"],
                    "weight": tree["weight"],
                },
                depth_limit=1,
            )

            # -------- derived objects --------
            dibjet = lVector(
                ev.lead_bjet_pt, ev.lead_bjet_eta, ev.lead_bjet_phi,
                ev.sublead_bjet_pt, ev.sublead_bjet_eta, ev.sublead_bjet_phi,
                ev.lead_bjet_mass, ev.sublead_bjet_mass,
            )
            diphoton = lVector(
                ev.lead_pho_pt, ev.lead_pho_eta, ev.lead_pho_phi,
                ev.sublead_pho_pt, ev.sublead_pho_eta, ev.sublead_pho_phi,
            )

            ev["dibjet_mass"] = dibjet.mass
            ev["dibjet_pt"]   = dibjet.pt
            ev["dibjet_eta"]  = dibjet.eta
            ev["dibjet_phi"]  = dibjet.phi

            ev["diphoton_mass"] = diphoton.mass
            ev["diphoton_pt"]   = diphoton.pt
            ev["diphoton_eta"]  = diphoton.eta
            ev["diphoton_phi"]  = diphoton.phi

            # aliases + ratios
            ev["lead_pho_mvaID"]    = ev.lead_pho_mvaID_WP90
            ev["sublead_pho_mvaID"] = ev.sublead_pho_mvaID_WP90

            ev["max_gamma_MVA_ID"] = ak.where(
                ev.lead_pho_mvaID > ev.sublead_pho_mvaID,
                ev.lead_pho_mvaID,
                ev.sublead_pho_mvaID,
            )

            ev["FirstJet_PtOverM"]   = ev.lead_bjet_pt / ev.dibjet_mass
            ev["SecondJet_PtOverM"]  = ev.sublead_bjet_pt / ev.dibjet_mass
            ev["pholead_PtOverM"]    = ev.lead_pho_pt / ev.diphoton_mass
            ev["phosublead_PtOverM"] = ev.sublead_pho_pt / ev.diphoton_mass

            ev["dibjet_bbgg_mass"]   = ev.dibjet_pt / ev.bbgg_mass
            ev["diphoton_bbgg_mass"] = ev.diphoton_pt / ev.bbgg_mass

            ev["lead_pt_over_diphoton_mass"]    = ev.lead_pho_pt / ev.diphoton_mass
            ev["sublead_pt_over_diphoton_mass"] = ev.sublead_pho_pt / ev.diphoton_mass
            ev["lead_pt_over_dibjet_mass"]      = ev.lead_pho_pt / ev.dibjet_mass
            ev["sublead_pt_over_dibjet_mass"]   = ev.sublead_pho_pt / ev.dibjet_mass

            # -------- regions --------
            ev["preselection"] = get_mask_preselection(ev)
            ev["selection"]    = get_mask_selection(ev)

            # -------- histograms --------
            for region in ACTIVE_REGIONS:
                sel = ev[ev[region]]
                if len(sel) == 0:
                    continue

                ensure_dir(fout, f"{signal_name}/{region}")
                gdir = fout.GetDirectory(f"{signal_name}/{region}")
                gdir.cd()

                for var in variables_common[region]:
                    hname = vardict[var]
                    if syst != "nominal":
                        hname += f"__{syst}"

                    h = make_th1(
                        ak.to_numpy(sel[var]),
                        ak.to_numpy(sel["weight"]),
                        hname,
                        binning[region][var],
                    )

                    h.SetDirectory(gdir)
                    h.Write(hname, ROOT.TObject.kOverwrite)
                    del h

# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True)
    ap.add_argument("--era", default="All")
    ap.add_argument("input_dir")
    args = ap.parse_args()

    cfg = RunConfig(args.year, args.era)
    base_dir = Path(args.input_dir).resolve()

    outdir = Path(cfg.outputs_path) / "systematics"
    outdir.mkdir(parents=True, exist_ok=True)

    fout = ROOT.TFile(str(outdir / "histograms.root"), "RECREATE")

    signal_dirs = sorted(
        d for d in base_dir.iterdir()
        if d.is_dir() and d.name.startswith("NMSSM_")
    )

    print(f"[INFO] Found {len(signal_dirs)} signal points")

    for sigdir in signal_dirs:
        print(f"[INFO] Processing signal: {sigdir.name}")
        for syst in SYSTEMATICS:
            process_systematic(sigdir, syst, fout)

    if fout.GetListOfKeys().GetSize() == 0:
        raise RuntimeError("[FATAL] ROOT file is empty — histograms were not written!")

    fout.Close()
    print("[OK] All signal points processed successfully")

if __name__ == "__main__":
    main()
