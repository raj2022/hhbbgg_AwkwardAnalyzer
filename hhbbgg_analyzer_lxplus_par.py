import os
import optparse
import numpy as np
import uproot
import pandas as pd
import awkward as ak
from config.utils import lVector
from normalisation import getXsec, getLumi
import pyarrow.parquet as pq
from pyarrow import Table
import pyarrow

# ---------------- PyROOT ONLY for histograms (separate file) ----------------
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False)

def _ensure_1d(a):
    a = np.asarray(a)
    return a.ravel()

def make_th1_pyroot(values, weights, name, title, binning):
    """
    Create a ROOT.TH1D and fill it using numpy.histogram.
    Robust to variable/fixed binning, angular wrap, and boolean inputs.
    """
    v  = _ensure_1d(values)
    w  = None if weights is None else _ensure_1d(weights)

    # mask non-finite
    if w is not None:
        mask = np.isfinite(v) & np.isfinite(w)
        v = v[mask]; w = w[mask]
    else:
        mask = np.isfinite(v)
        v = v[mask]

    # work on a separate copy; never rebind `v` later
    v2 = v.copy()

    # helper: angle detection + unwrap
    def _is_angular_name(s):
        s = (s or "").lower()
        return ("phi" in s) or ("deltaphi" in s) or s.endswith("_phi")

    def _maybe_angle_edges(arr):
        if arr.size < 2 or not np.isfinite(arr).all():
            return False
        rng = float(np.nanmax(arr) - np.nanmin(arr))
        return (rng <= 2*np.pi + 1e-6) and (np.nanmin(arr) >= -2*np.pi-1e-6) and (np.nanmax(arr) <= 2*np.pi+1e-6)

    def _unwrap_edges_and_values(edges, vals):
        e = edges.astype("f8").copy()
        # make edges strictly increasing by adding 2π after backward jumps
        for i in range(1, e.size):
            if e[i] <= e[i-1] - 1e-15:
                shift = 2*np.pi * np.ceil((e[i-1] - e[i] + 1e-15)/(2*np.pi))
                e[i:] = e[i:] + shift
        # map values into [e0, e0+2π)
        e0 = e[0]; two_pi = 2*np.pi
        vals_out = vals.copy()
        fm = np.isfinite(vals_out)
        vals_out[ fm ] = (vals_out[ fm ] - e0) % two_pi + e0
        return e, vals_out

    # Build authoritative edges array
    edges_np = None
    if isinstance(binning, np.ndarray) or (
        isinstance(binning, (list, tuple)) and not (
            len(binning) == 3 and all(np.isscalar(x) for x in binning)
        )
    ):
        # variable edges
        edges_np = np.asarray(binning, dtype="f8").ravel()
        edges_np = edges_np[np.isfinite(edges_np)]
        if edges_np.size < 2:
            raise ValueError(f"[{name}] Variable bin edges must have length >= 2, got: {edges_np}")

        if not np.all(np.diff(edges_np) > 0):
            # try angle-aware unwrap first
            if _is_angular_name(name) or _maybe_angle_edges(edges_np):
                edges_np, v2 = _unwrap_edges_and_values(edges_np, v2)
            else:
                e_sorted_unique = np.unique(edges_np)
                if e_sorted_unique.size < 2 or not np.all(np.diff(e_sorted_unique) > 0):
                    raise ValueError(f"[{name}] Invalid variable bin edges (not strictly increasing): {edges_np}")
                print(f"[WARN] {name}: edges not strictly increasing; using sorted unique edges.")
                edges_np = e_sorted_unique

        nb = len(edges_np) - 1
        h = ROOT.TH1D(name, title, int(nb), edges_np)
    else:
        # (nbins, lo, hi)
        nb, lo, hi = binning
        nb = int(nb); lo = float(lo); hi = float(hi)
        if not np.isfinite([lo, hi]).all() or hi <= lo or nb <= 0:
            raise ValueError(f"[{name}] Invalid (nb, lo, hi): {binning}")
        h = ROOT.TH1D(name, title, nb, lo, hi)
        edges_np = np.linspace(lo, hi, nb + 1, dtype="f8")

    # Quiet bool→uint8 warnings by casting
    if v2.dtype == np.bool_:
        v2 = v2.astype("f8")
    if w is not None and w.dtype == np.bool_:
        w = w.astype("f8")

    # Histogram with sanitized edges
    counts, _ = np.histogram(v2, bins=edges_np, weights=w)
    if w is None:
        sumw2 = counts.astype("f8")
    else:
        sumw2, _ = np.histogram(v2, bins=edges_np, weights=w * w)

    # Fill ROOT hist
    h.Sumw2()
    for i in range(1, h.GetNbinsX() + 1):
        c  = float(counts[i - 1])
        e2 = float(sumw2[i - 1])
        h.SetBinContent(i, c)
        h.SetBinError(i, float(np.sqrt(e2) if e2 >= 0 else 0.0))

    h.SetDirectory(0)
    return h



def ensure_dir_in_tfile(tfile, path):
    """
    Ensure nested directories exist inside a ROOT.TFile; return the leaf TDirectory.
    """
    curr = tfile
    if not path:
        return curr
    for part in path.split('/'):
        d = curr.GetDirectory(part)
        curr = d if d else curr.mkdir(part)
    return curr
# ---------------------------------------------------------------------------

usage = "usage: %prog [options] arg1 arg2"
parser = optparse.OptionParser(usage)
parser.add_option(
    "-i",
    "--inFile",
    type="string",
    dest="inputfiles_",
    help="Either single input ROOT/Parquet file or a directory of ROOT/Parquet files",
)
(options, args) = parser.parse_args()

if not options.inputfiles_:
    raise ValueError(
        "Please provide either an input ROOT/Parquet file or a directory of ROOT/Parquet files using the -i or --inFile option"
    )
inputfiles_ = options.inputfiles_

# to tag signals from filename
def is_signal_from_name(name: str) -> bool:
    s = name
    return any(x in s for x in [
        "GluGluToHH", "VBFHH", "Radion", "Graviton", "XToHH", "HHTo", "HHTobbgg"
    ])

def process_parquet_file(inputfile, out_files):
    print(f"Processing Parquet file: {inputfile}")
    required_columns = [
        "run",
        "lumi",
        "event",
        "puppiMET_pt",
        "puppiMET_phi",
        "puppiMET_phiJERDown",
        "puppiMET_phiJERUp",
        "puppiMET_phiJESDown",
        "puppiMET_phiJESUp",
        "puppiMET_phiUnclusteredDown",
        "puppiMET_phiUnclusteredUp",
        "puppiMET_ptJERDown",
        "puppiMET_ptJERUp",
        "puppiMET_ptJESDown",
        "puppiMET_ptJESUp",
        "puppiMET_ptUnclusteredDown",
        "puppiMET_ptUnclusteredUp",
        "puppiMET_sumEt",
        "Res_lead_bjet_pt",
        "Res_lead_bjet_eta",
        "Res_lead_bjet_phi",
        "Res_lead_bjet_mass",
        "Res_sublead_bjet_pt",
        "Res_sublead_bjet_eta",
        "Res_sublead_bjet_phi",
        "Res_sublead_bjet_mass",
        "lead_pt","lead_eta",
        "lead_phi",
        "lead_mvaID_WP90",
        "lead_mvaID_WP80",
        "sublead_pt",
        "sublead_eta",
        "sublead_phi",
        "sublead_mvaID_WP90",
        "sublead_mvaID_WP80",
        "weight",
        "weight_central",
        "Res_lead_bjet_btagPNetB",
        "Res_sublead_bjet_btagPNetB",
        "lead_isScEtaEB",
        "sublead_isScEtaEB",
        "Res_HHbbggCandidate_pt",
        "Res_HHbbggCandidate_eta",
        "Res_HHbbggCandidate_phi",
        "Res_HHbbggCandidate_mass",
        "Res_CosThetaStar_CS",
        "Res_CosThetaStar_gg",
        "Res_CosThetaStar_jj",
        "Res_DeltaR_jg_min",
        "Res_pholead_PtOverM",
        "Res_phosublead_PtOverM",
        "Res_FirstJet_PtOverM",
        "Res_SecondJet_PtOverM",
        "lead_mvaID",
        "sublead_mvaID",
        "Res_DeltaR_j1g1",
        "Res_DeltaR_j2g1",
        "Res_DeltaR_j1g2",
        "Res_DeltaR_j2g2",
        "Res_M_X",
        "Res_DeltaPhi_j1MET",
        "Res_DeltaPhi_j2MET",
        "Res_chi_t0",
        "Res_chi_t1",
        "lepton1_mvaID",
        "lepton1_pt",
        "lepton1_pfIsoId",
        "n_jets",
    ]

    parquet_file = pq.ParquetFile(inputfile)
    fulltree_ = ak.Array([])

    for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
        df = batch.to_pandas()
        print(f"Processing batch with {len(df)} rows.")
        tree_ = ak.from_arrow(pyarrow.Table.from_pandas(df))
        print(f"Parquet file loaded with {len(tree_)} entries  and {len(required_columns)} columns.")

        # dataset flags and normalisation
        base = os.path.basename(inputfile)
        isdata = "Data" in base
        sigflag = is_signal_from_name(base)
        if isdata:
            xsec_ = 1.0
            lumi_ = 1.0
        else:
            xsec_ = float(getXsec(inputfile))
            lumi_ = float(getLumi()) * 1000.0

        # zip columns
        cms_events = ak.zip(
            {
                "run": tree_["run"], 
                "lumi": tree_["lumi"], 
                "event": tree_["event"],
                "puppiMET_pt": tree_["puppiMET_pt"], 
                "puppiMET_phi": tree_["puppiMET_phi"],
                "puppiMET_phiJERDown": tree_["puppiMET_phiJERDown"], 
                "puppiMET_phiJERUp": tree_["puppiMET_phiJERUp"],
                "puppiMET_phiJESDown": tree_["puppiMET_phiJESDown"],
                "puppiMET_phiJESUp": tree_["puppiMET_phiJESUp"],
                "puppiMET_phiUnclusteredDown": tree_["puppiMET_phiUnclusteredDown"],
                "puppiMET_phiUnclusteredUp": tree_["puppiMET_phiUnclusteredUp"],
                "puppiMET_ptJERDown": tree_["puppiMET_ptJERDown"],
                "puppiMET_ptJERUp": tree_["puppiMET_ptJERUp"],
                "puppiMET_ptJESDown": tree_["puppiMET_ptJESDown"], 
                "puppiMET_ptJESUp": tree_["puppiMET_ptJESUp"],
                "puppiMET_ptUnclusteredDown": tree_["puppiMET_ptUnclusteredDown"],
                "puppiMET_ptUnclusteredUp": tree_["puppiMET_ptUnclusteredUp"],
                "puppiMET_sumEt": tree_["puppiMET_sumEt"],
                "lead_bjet_pt": tree_["Res_lead_bjet_pt"], 
                "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
                "lead_bjet_phi": tree_["Res_lead_bjet_phi"], 
                "lead_bjet_mass": tree_["Res_lead_bjet_mass"],
                "sublead_bjet_pt": tree_["Res_sublead_bjet_pt"], 
                "sublead_bjet_eta": tree_["Res_sublead_bjet_eta"], 
                "sublead_bjet_phi": tree_["Res_sublead_bjet_phi"], 
                "sublead_bjet_mass": tree_["Res_sublead_bjet_mass"],
                "lead_pho_pt": tree_["lead_pt"], 
                "lead_pho_eta": tree_["lead_eta"], 
                "lead_pho_phi": tree_["lead_phi"],
                "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"],
                "lead_pho_mvaID_WP80": tree_["lead_mvaID_WP80"],
                "sublead_pho_pt": tree_["sublead_pt"], 
                "sublead_pho_eta": tree_["sublead_eta"], 
                "sublead_pho_phi": tree_["sublead_phi"],
                "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
                "sublead_pho_mvaID_WP80": tree_["sublead_mvaID_WP80"],
                "weight_central": tree_["weight_central"], 
                "weight": tree_["weight"],
                "lead_bjet_PNetB": tree_["Res_lead_bjet_btagPNetB"],
                "sublead_bjet_PNetB": tree_["Res_sublead_bjet_btagPNetB"],
                "lead_isScEtaEB": tree_["lead_isScEtaEB"],
                "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
                "CosThetaStar_CS": tree_["Res_CosThetaStar_CS"], 
                "CosThetaStar_gg": tree_["Res_CosThetaStar_gg"],
                "CosThetaStar_jj": tree_["Res_CosThetaStar_jj"],
                "DeltaR_jg_min": tree_["Res_DeltaR_jg_min"],
                "pholead_PtOverM": tree_["Res_pholead_PtOverM"], 
                "phosublead_PtOverM": tree_["Res_phosublead_PtOverM"],
                "FirstJet_PtOverM": tree_["Res_FirstJet_PtOverM"], 
                "SecondJet_PtOverM": tree_["Res_SecondJet_PtOverM"],
                "lead_pho_mvaID": tree_["lead_mvaID"], 
                "sublead_pho_mvaID": tree_["sublead_mvaID"],
                "DeltaR_j1g1": tree_["Res_DeltaR_j1g1"],
                "DeltaR_j2g1": tree_["Res_DeltaR_j2g1"],
                "DeltaR_j1g2": tree_["Res_DeltaR_j1g2"], 
                "DeltaR_j2g2": tree_["Res_DeltaR_j2g2"],
                "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
                "bbgg_pt": tree_["Res_HHbbggCandidate_pt"],
                "bbgg_eta": tree_["Res_HHbbggCandidate_eta"], 
                "bbgg_phi": tree_["Res_HHbbggCandidate_phi"],
                "MX": tree_["Res_M_X"],
                "DeltaPhi_j1MET": tree_["Res_DeltaPhi_j1MET"],
                "DeltaPhi_j2MET": tree_["Res_DeltaPhi_j2MET"],
                "Res_chi_t0": tree_["Res_chi_t0"], 
                "Res_chi_t1": tree_["Res_chi_t1"],
                "lepton1_mvaID": tree_["lepton1_mvaID"],
                "lepton1_pt": tree_["lepton1_pt"], 
                "lepton1_pfIsoId": tree_["lepton1_pfIsoId"],
                "n_jets": tree_["n_jets"],
            },
            depth_limit=1,
        )

        # add flags needed by regions.py
        # store as small integers (0/1) to simplify comparisons inside masks
        n_entries = len(tree_)
        cms_events["signal"] = ak.Array(np.full(n_entries, 1 if sigflag else 0, dtype=np.int8))
        cms_events["isdata"] = ak.Array(np.full(n_entries, 1 if isdata else 0, dtype=np.int8))

        out_events = ak.zip(
            {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]},
            depth_limit=1,
        )

        # 4-vectors
        dibjet_ = lVector(
            cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],
            cms_events["sublead_bjet_pt"], cms_events["sublead_bjet_eta"], cms_events["sublead_bjet_phi"],
            cms_events["lead_bjet_mass"], cms_events["sublead_bjet_mass"],
        )
        diphoton_ = lVector(
            cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],
            cms_events["sublead_pho_pt"], cms_events["sublead_pho_eta"], cms_events["sublead_pho_phi"],
        )
        cms_events["dibjet_mass"] = dibjet_.mass
        cms_events["dibjet_pt"]   = dibjet_.pt
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"]   = diphoton_.pt
        cms_events["dibjet_eta"] = dibjet_.eta
        cms_events["dibjet_phi"] = dibjet_.phi
        cms_events["diphoton_eta"] = diphoton_.eta
        cms_events["diphoton_phi"] = diphoton_.phi

        # ratios
        cms_events["lead_pt_over_diphoton_mass"]   = cms_events["lead_pho_pt"]    / cms_events["diphoton_mass"]
        cms_events["sublead_pt_over_diphoton_mass"] = cms_events["sublead_pho_pt"] / cms_events["diphoton_mass"]
        cms_events["lead_pt_over_dibjet_mass"]     = cms_events["lead_bjet_pt"]   / cms_events["dibjet_mass"]
        cms_events["sublead_pt_over_dibjet_mass"]  = cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
        cms_events["diphoton_bbgg_mass"] = cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
        cms_events["dibjet_bbgg_mass"]   = cms_events["dibjet_pt"]   / cms_events["bbgg_mass"]

        # max gamma MVA
        cms_events["max_gamma_MVA_ID"] = ak.where(
            cms_events["lead_pho_mvaID"] > cms_events["sublead_pho_mvaID"],
            cms_events["lead_pho_mvaID"], cms_events["sublead_pho_mvaID"]
        )

        # region masks (now that 'signal' and 'isdata' exist)
        from regions import (
            get_mask_preselection, get_mask_selection,
            get_mask_srbbgg, get_mask_srbbggMET,
            get_mask_crantibbgg, get_mask_crbbantigg, get_mask_crantibbantigg,
            get_mask_sideband, get_mask_idmva_presel, get_mask_idmva_sideband,
        )
        cms_events["preselection"]     = get_mask_preselection(cms_events)
        cms_events["selection"]        = get_mask_selection(cms_events)
        cms_events["srbbgg"]           = get_mask_srbbgg(cms_events)
        cms_events["srbbggMET"]        = get_mask_srbbggMET(cms_events)
        cms_events["crbbantigg"]       = get_mask_crbbantigg(cms_events)
        cms_events["crantibbgg"]       = get_mask_crantibbgg(cms_events)
        cms_events["crantibbantigg"]   = get_mask_crantibbantigg(cms_events)
        cms_events["sideband"]         = get_mask_sideband(cms_events)
        cms_events["idmva_presel"]     = get_mask_idmva_presel(cms_events)
        cms_events["idmva_sideband"]   = get_mask_idmva_sideband(cms_events)

        # copy selected fields to out_events
        keys_to_copy = [
            # puppiMET
            "puppiMET_pt","puppiMET_phi","puppiMET_phiJERDown","puppiMET_phiJERUp",
            "puppiMET_phiJESDown","puppiMET_phiJESUp","puppiMET_phiUnclusteredDown","puppiMET_phiUnclusteredUp",
            "puppiMET_ptJERDown","puppiMET_ptJERUp","puppiMET_ptJESDown","puppiMET_ptJESUp",
            "puppiMET_ptUnclusteredDown","puppiMET_ptUnclusteredUp","puppiMET_sumEt",
            # photons/jets
            "lead_pho_pt","lead_pho_eta","lead_pho_phi",
            "sublead_pho_pt","sublead_pho_eta","sublead_pho_phi",
            "lead_bjet_pt","lead_bjet_eta","lead_bjet_phi",
            "sublead_bjet_pt","sublead_bjet_eta","sublead_bjet_phi",
            # masses/kin
            "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta","bbgg_phi",
            # NR vars
            "DeltaPhi_j1MET","DeltaPhi_j2MET","Res_chi_t0","Res_chi_t1",
            "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId","n_jets",
            # weights
            "weight_central",
            # extra
            "dibjet_eta","dibjet_phi","diphoton_eta","diphoton_phi",
            "lead_bjet_PNetB","sublead_bjet_PNetB",
            "pholead_PtOverM","phosublead_PtOverM","FirstJet_PtOverM","SecondJet_PtOverM",
            "CosThetaStar_CS","CosThetaStar_jj","CosThetaStar_gg","DeltaR_jg_min",
            "lead_pt_over_diphoton_mass","sublead_pt_over_diphoton_mass",
            "lead_pt_over_dibjet_mass","sublead_pt_over_dibjet_mass",
            "diphoton_bbgg_mass","dibjet_bbgg_mass",
            "lead_pho_mvaID_WP90","lead_pho_mvaID_WP80","sublead_pho_mvaID_WP90","sublead_pho_mvaID_WP80",
            "lead_pho_mvaID","sublead_pho_mvaID","max_gamma_MVA_ID",
            # region flags
            "preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband",
            "idmva_sideband","idmva_presel",
            # ΔR
            "DeltaR_j1g1","DeltaR_j2g1","DeltaR_j1g2","DeltaR_j2g2",
            # also store flags used by regions if you want them in trees:
            "signal","isdata",
        ]
        for k in keys_to_copy:
            out_events[k] = cms_events[k]

        # per-region weights (guard against divide-by-zero by replacing non-finite weight_central)
        wc = ak.to_numpy(out_events["weight_central"])
        wc = np.where(np.isfinite(wc) & (wc != 0.0), wc, 1.0)
        base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_) / wc
        base_w = np.where(np.isfinite(base_w), base_w, 0.0)

        for r in ["preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband","idmva_sideband","idmva_presel"]:
            out_events["weight_"+r] = base_w

        print(f"Total number of events in fulltree_: {len(fulltree_)}")
        if len(fulltree_) == 0:
            print("WARNING: fulltree_ is empty! Initializing.")
            fulltree_ = out_events
        else:
            fulltree_ = ak.concatenate([fulltree_, out_events], axis=0)
        print(f"Finished processing {len(fulltree_)} total events from {inputfile}")

    # ---------------- Write processed flat tree via uproot ----------------
    print(f"Writing {len(fulltree_)} events to ROOT file (trees).")
    numpy_compatible_tree = {
        key: ak.to_numpy(fulltree_[key]).astype("int64")
        if "int" in str(fulltree_[key].type)
        else ak.to_numpy(fulltree_[key])
        for key in fulltree_.fields
    }
    out_files["tree"]["processed_events"] = numpy_compatible_tree
    print("Saved processed data to ROOT file (trees).")

    # ---------------- Make histograms and regional trees ----------------
    from variables import vardict, regions, variables_common
    from binning import binning

    print("Making histograms and trees")
    sample_name = os.path.basename(inputfile).replace(".parquet", "").replace(".root", "")

    # Hist file: create /Sample/<region>
    ensure_dir_in_tfile(out_files["hist"], sample_name)

    for ireg in regions:
        thisregion = fulltree_[fulltree_[ireg] == True]
        thisregion_ = thisregion[~(ak.is_none(thisregion))]
        weight_ = "weight_" + ireg

        # --- Histograms with PyROOT (under Sample/Region) ---
        region_dir = ensure_dir_in_tfile(out_files["hist"], f"{sample_name}/{ireg}")
        for ivar in variables_common[ireg]:
            hist_name_ = f"{vardict[ivar]}"
            vals = ak.to_numpy(thisregion_[ivar])
            wts  = ak.to_numpy(thisregion_[weight_])
            if wts is not None:
                wts = np.where(np.isfinite(wts), wts, 0.0)
            h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])
            region_dir.cd()
            h.Write()
            del h

        # --- Regional TTrees via uproot ---
        tree_data_ = {
            key: (
                np.nan_to_num(
                    ak.to_numpy(ak.fill_none(thisregion_[key], -9999)).astype("int64"),
                    nan=-9999, posinf=999999999, neginf=-999999999
                )
                if np.issubdtype(
                    ak.to_numpy(ak.fill_none(thisregion_[key], -9999)).dtype, np.integer
                )
                else np.nan_to_num(
                    ak.to_numpy(ak.fill_none(thisregion_[key], -9999)),
                    nan=-9999, posinf=999999999, neginf=-999999999
                )
            )
            for key in thisregion_.fields
        }
        out_files["tree"][f"{sample_name}/{ireg}"] = tree_data_

    print("Done")

# ---------------- Output files (separate writers!) ----------------
output_dir = "outputfiles"
os.makedirs(output_dir, exist_ok=True)

hist_file_path = os.path.join(output_dir, "hhbbgg_analyzer-v2-histograms.root")
tree_file_path = os.path.join(output_dir, "hhbbgg_analyzer-v2-trees.root")

hist_tfile = ROOT.TFile(hist_file_path, "RECREATE")  # PyROOT for histograms
tree_upfile = uproot.recreate(tree_file_path)        # uproot for trees

out_files = {"hist": hist_tfile, "tree": tree_upfile}

# ---------------- Inputs ----------------
if os.path.isfile(inputfiles_):
    inputfiles = [inputfiles_]
else:
    inputfiles = [
        os.path.join(inputfiles_, f)
        for f in os.listdir(inputfiles_)
        if f.endswith(".parquet") or f.endswith(".root")
    ]

# ---------------- Main ----------------
def main():
    for infile_ in inputfiles:
        process_parquet_file(infile_, out_files)

    out_files["tree"].close()
    out_files["hist"].Write()
    out_files["hist"].Close()
    print(f"Wrote trees to {tree_file_path}")
    print(f"Wrote histograms to {hist_file_path}")

if __name__ == "__main__":
    main()
