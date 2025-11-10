# import os
# import optparse
# import numpy as np
# import uproot
# import pandas as pd
# import awkward as ak
# from config.utils import lVector
# from normalisation import getXsec, getLumi
# import pyarrow.parquet as pq
# from pyarrow import Table
# import pyarrow

# import argparse
# from pathlib import Path
# import yaml
# from config.config import RunConfig

# # -------------------------------- Command-line arguments ----------------
# ap = argparse.ArgumentParser(description="hhbbgg analyzer (parquet) with multi-era support")
# ap.add_argument("-i", "--inFile",
#                 help="Single ROOT/Parquet file or a directory. If omitted, use config for (year, era).")
# ap.add_argument("--year", required=True, help="e.g. 2022 or 2023")
# ap.add_argument("--era",  required=True, help="e.g. PreEE, PostEE, All")
# args = ap.parse_args()

# # Resolve config & IO locations
# cfg = RunConfig(args.year, args.era)
# in_path = Path(args.inFile).resolve() if args.inFile else cfg.raw_path

# out_dir = cfg.outputs_path
# os.makedirs(out_dir, exist_ok=True)
# print(f"Output directory: {out_dir}")
# #-------------------------------- Helper functions ----------------

# # ---------------- PyROOT ONLY for histograms (separate file) ----------------
# import ROOT
# ROOT.gROOT.SetBatch(True)
# ROOT.TH1.AddDirectory(False)

# def _ensure_1d(a):
#     a = np.asarray(a)
#     return a.ravel()

# def make_th1_pyroot(values, weights, name, title, binning):
#     """
#     Create a ROOT.TH1D and fill it using numpy.histogram.
#     Robust to variable/fixed binning, angular wrap, and boolean inputs.
#     """
#     v  = _ensure_1d(values)
#     w  = None if weights is None else _ensure_1d(weights)

#     # mask non-finite
#     if w is not None:
#         mask = np.isfinite(v) & np.isfinite(w)
#         v = v[mask]; w = w[mask]
#     else:
#         mask = np.isfinite(v)
#         v = v[mask]

#     # work on a separate copy; never rebind `v` later
#     v2 = v.copy()

#     # helper: angle detection + unwrap
#     def _is_angular_name(s):
#         s = (s or "").lower()
#         return ("phi" in s) or ("deltaphi" in s) or s.endswith("_phi")

#     def _maybe_angle_edges(arr):
#         if arr.size < 2 or not np.isfinite(arr).all():
#             return False
#         rng = float(np.nanmax(arr) - np.nanmin(arr))
#         return (rng <= 2*np.pi + 1e-6) and (np.nanmin(arr) >= -2*np.pi-1e-6) and (np.nanmax(arr) <= 2*np.pi+1e-6)

#     def _unwrap_edges_and_values(edges, vals):
#         e = edges.astype("f8").copy()
#         # make edges strictly increasing by adding 2π after backward jumps
#         for i in range(1, e.size):
#             if e[i] <= e[i-1] - 1e-15:
#                 shift = 2*np.pi * np.ceil((e[i-1] - e[i] + 1e-15)/(2*np.pi))
#                 e[i:] = e[i:] + shift
#         # map values into [e0, e0+2π)
#         e0 = e[0]; two_pi = 2*np.pi
#         vals_out = vals.copy()
#         fm = np.isfinite(vals_out)
#         vals_out[ fm ] = (vals_out[ fm ] - e0) % two_pi + e0
#         return e, vals_out

#     # Build authoritative edges array
#     edges_np = None
#     if isinstance(binning, np.ndarray) or (
#         isinstance(binning, (list, tuple)) and not (
#             len(binning) == 3 and all(np.isscalar(x) for x in binning)
#         )
#     ):
#         # variable edges
#         edges_np = np.asarray(binning, dtype="f8").ravel()
#         edges_np = edges_np[np.isfinite(edges_np)]
#         if edges_np.size < 2:
#             raise ValueError(f"[{name}] Variable bin edges must have length >= 2, got: {edges_np}")

#         if not np.all(np.diff(edges_np) > 0):
#             # try angle-aware unwrap first
#             if _is_angular_name(name) or _maybe_angle_edges(edges_np):
#                 edges_np, v2 = _unwrap_edges_and_values(edges_np, v2)
#             else:
#                 e_sorted_unique = np.unique(edges_np)
#                 if e_sorted_unique.size < 2 or not np.all(np.diff(e_sorted_unique) > 0):
#                     raise ValueError(f"[{name}] Invalid variable bin edges (not strictly increasing): {edges_np}")
#                 print(f"[WARN] {name}: edges not strictly increasing; using sorted unique edges.")
#                 edges_np = e_sorted_unique

#         nb = len(edges_np) - 1
#         h = ROOT.TH1D(name, title, int(nb), edges_np)
#     else:
#         # (nbins, lo, hi)
#         nb, lo, hi = binning
#         nb = int(nb); lo = float(lo); hi = float(hi)
#         if not np.isfinite([lo, hi]).all() or hi <= lo or nb <= 0:
#             raise ValueError(f"[{name}] Invalid (nb, lo, hi): {binning}")
#         h = ROOT.TH1D(name, title, nb, lo, hi)
#         edges_np = np.linspace(lo, hi, nb + 1, dtype="f8")

#     # Quiet bool→uint8 warnings by casting
#     if v2.dtype == np.bool_:
#         v2 = v2.astype("f8")
#     if w is not None and w.dtype == np.bool_:
#         w = w.astype("f8")

#     # Histogram with sanitized edges
#     counts, _ = np.histogram(v2, bins=edges_np, weights=w)
#     if w is None:
#         sumw2 = counts.astype("f8")
#     else:
#         sumw2, _ = np.histogram(v2, bins=edges_np, weights=w * w)

#     # Fill ROOT hist
#     h.Sumw2()
#     for i in range(1, h.GetNbinsX() + 1):
#         c  = float(counts[i - 1])
#         e2 = float(sumw2[i - 1])
#         h.SetBinContent(i, c)
#         h.SetBinError(i, float(np.sqrt(e2) if e2 >= 0 else 0.0))

#     h.SetDirectory(0)
#     return h



# def ensure_dir_in_tfile(tfile, path):
#     """
#     Ensure nested directories exist inside a ROOT.TFile; return the leaf TDirectory.
#     """
#     curr = tfile
#     if not path:
#         return curr
#     for part in path.split('/'):
#         d = curr.GetDirectory(part)
#         curr = d if d else curr.mkdir(part)
#     return curr
# # ---------------------------------------------------------------------------
# def normalize_sample_name(name: str) -> str:
#     """
#     Collapse chunk suffixes and drop obvious year/era tokens so the same MC sample merges.
#     Adjust this to your exact naming scheme if needed.
#     """
#     base = os.path.basename(name)
#     base = re.sub(r"\.(parquet|root)$", "", base, flags=re.IGNORECASE)
#     base = re.sub(r"(_part\d+|_chunk\d+|_\d+of\d+)$", "", base, flags=re.IGNORECASE)
#     base = re.sub(r"[_-]?(2022|2023)(PreEE|PostEE|All)?", "", base, flags=re.IGNORECASE)
#     return base

# #-------------------------------

# def ak_to_numpy_dict(arr: ak.Array) -> dict:
#     """
#     Convert an awkward record array to a dict of numpy arrays, filling Nones and nans.
#     Matches your regional tree writing behavior.
#     """
#     out = {}
#     for key in arr.fields:
#         filled = ak.fill_none(arr[key], -9999)
#         np_arr = ak.to_numpy(filled)
#         if np.issubdtype(np_arr.dtype, np.integer):
#             np_arr = np.nan_to_num(np_arr.astype("int64"), nan=-9999, posinf=999999999, neginf=-999999999)
#         else:
#             np_arr = np.nan_to_num(np_arr, nan=-9999, posinf=999999999, neginf=-999999999)
#         out[key] = np_arr
#     return out

# def concat_field_dicts(dict_list):
#     """
#     Concatenate a list of dict[field->np.ndarray] on axis=0.
#     """
#     out = {}
#     if not dict_list:
#         return out
#     keys = dict_list[0].keys()
#     for k in keys:
#         arrs = [np.asarray(d[k]) for d in dict_list if k in d]
#         if len(arrs) == 0:
#             out[k] = np.array([], dtype=np.float32)
#         elif len(arrs) == 1:
#             out[k] = arrs[0]
#         else:
#             out[k] = np.concatenate(arrs, axis=0)
#     return out
# #---------------------------------------------------

# # ========== Global accumulators across all inputs ==========
# HIST_CACHE = {}     # key: (sample, region, varname) -> ROOT.TH1D (accumulated)
# TREE_ACC   = {}     # key: (sample, region) -> list[dict[field->np.ndarray]]
# PROC_ACC   = {}     # key: sample -> list[dict[field->np.ndarray]]  (processed_events)


# #------------------------------------------------------

# usage = "usage: %prog [options] arg1 arg2"
# parser = optparse.OptionParser(usage)
# parser.add_option(
#     "-i",
#     "--inFile",
#     type="string",
#     dest="inputfiles_",
#     help="Either single input ROOT/Parquet file or a directory of ROOT/Parquet files",
# )
# (options, args) = parser.parse_args()

# if not options.inputfiles_:
#     raise ValueError(
#         "Please provide either an input ROOT/Parquet file or a directory of ROOT/Parquet files using the -i or --inFile option"
#     )
# inputfiles_ = options.inputfiles_

# # to tag signals from filename
# def is_signal_from_name(name: str) -> bool:
#     s = name
#     return any(x in s for x in [
#         "GluGluToHH", "VBFHH", "Radion", "Graviton", "XToHH", "HHTo", "HHTobbgg"
#     ])

# def process_parquet_file(inputfile, out_files):
#      """
#     Process a single parquet file:
#       - build cms_events with derived variables + region flags
#       - accumulate histograms per (sample, region, variable)
#       - accumulate trees per (sample, region)
#       - accumulate full processed_events per sample
#     """
#     print(f"Processing Parquet file: {inputfile}")
#     required_columns = [
#         "run",
#         "lumi",
#         "event",
#         "puppiMET_pt",
#         "puppiMET_phi",
#         "puppiMET_phiJERDown",
#         "puppiMET_phiJERUp",
#         "puppiMET_phiJESDown",
#         "puppiMET_phiJESUp",
#         "puppiMET_phiUnclusteredDown",
#         "puppiMET_phiUnclusteredUp",
#         "puppiMET_ptJERDown",
#         "puppiMET_ptJERUp",
#         "puppiMET_ptJESDown",
#         "puppiMET_ptJESUp",
#         "puppiMET_ptUnclusteredDown",
#         "puppiMET_ptUnclusteredUp",
#         "puppiMET_sumEt",
#         "Res_lead_bjet_pt",
#         "Res_lead_bjet_eta",
#         "Res_lead_bjet_phi",
#         "Res_lead_bjet_mass",
#         "Res_sublead_bjet_pt",
#         "Res_sublead_bjet_eta",
#         "Res_sublead_bjet_phi",
#         "Res_sublead_bjet_mass",
#         "lead_pt","lead_eta",
#         "lead_phi",
#         "lead_mvaID_WP90",
#         "lead_mvaID_WP80",
#         "sublead_pt",
#         "sublead_eta",
#         "sublead_phi",
#         "sublead_mvaID_WP90",
#         "sublead_mvaID_WP80",
#         "weight",
#         "weight_central",
#         "Res_lead_bjet_btagPNetB",
#         "Res_sublead_bjet_btagPNetB",
#         "lead_isScEtaEB",
#         "sublead_isScEtaEB",
#         "Res_HHbbggCandidate_pt",
#         "Res_HHbbggCandidate_eta",
#         "Res_HHbbggCandidate_phi",
#         "Res_HHbbggCandidate_mass",
#         "Res_CosThetaStar_CS",
#         "Res_CosThetaStar_gg",
#         "Res_CosThetaStar_jj",
#         "Res_DeltaR_jg_min",
#         "Res_pholead_PtOverM",
#         "Res_phosublead_PtOverM",
#         "Res_FirstJet_PtOverM",
#         "Res_SecondJet_PtOverM",
#         "lead_mvaID",
#         "sublead_mvaID",
#         "Res_DeltaR_j1g1",
#         "Res_DeltaR_j2g1",
#         "Res_DeltaR_j1g2",
#         "Res_DeltaR_j2g2",
#         "Res_M_X",
#         "Res_DeltaPhi_j1MET",
#         "Res_DeltaPhi_j2MET",
#         "Res_chi_t0",
#         "Res_chi_t1",
#         "lepton1_mvaID",
#         "lepton1_pt",
#         "lepton1_pfIsoId",
#         "n_jets",
#     ]

#     parquet_file = pq.ParquetFile(inputfile)
#     fulltree_ = ak.Array([])

#     for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
#         df = batch.to_pandas()
#         print(f"Processing batch with {len(df)} rows.")
#         tree_ = ak.from_arrow(pyarrow.Table.from_pandas(df))
#         print(f"Parquet file loaded with {len(tree_)} entries  and {len(required_columns)} columns.")

#         # dataset flags and normalisation
#         base = os.path.basename(inputfile)
#         isdata = "Data" in base
#         sigflag = is_signal_from_name(base)
#         if isdata:
#             xsec_ = 1.0
#             lumi_ = 1.0
#         else:
#             xsec_ = float(getXsec(inputfile))
#             lumi_ = float(getLumi()) * 1000.0

#         # zip columns
#         cms_events = ak.zip(
#             {
#                 "run": tree_["run"], 
#                 "lumi": tree_["lumi"], 
#                 "event": tree_["event"],
#                 "puppiMET_pt": tree_["puppiMET_pt"], 
#                 "puppiMET_phi": tree_["puppiMET_phi"],
#                 "puppiMET_phiJERDown": tree_["puppiMET_phiJERDown"], 
#                 "puppiMET_phiJERUp": tree_["puppiMET_phiJERUp"],
#                 "puppiMET_phiJESDown": tree_["puppiMET_phiJESDown"],
#                 "puppiMET_phiJESUp": tree_["puppiMET_phiJESUp"],
#                 "puppiMET_phiUnclusteredDown": tree_["puppiMET_phiUnclusteredDown"],
#                 "puppiMET_phiUnclusteredUp": tree_["puppiMET_phiUnclusteredUp"],
#                 "puppiMET_ptJERDown": tree_["puppiMET_ptJERDown"],
#                 "puppiMET_ptJERUp": tree_["puppiMET_ptJERUp"],
#                 "puppiMET_ptJESDown": tree_["puppiMET_ptJESDown"], 
#                 "puppiMET_ptJESUp": tree_["puppiMET_ptJESUp"],
#                 "puppiMET_ptUnclusteredDown": tree_["puppiMET_ptUnclusteredDown"],
#                 "puppiMET_ptUnclusteredUp": tree_["puppiMET_ptUnclusteredUp"],
#                 "puppiMET_sumEt": tree_["puppiMET_sumEt"],
#                 "lead_bjet_pt": tree_["Res_lead_bjet_pt"], 
#                 "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
#                 "lead_bjet_phi": tree_["Res_lead_bjet_phi"], 
#                 "lead_bjet_mass": tree_["Res_lead_bjet_mass"],
#                 "sublead_bjet_pt": tree_["Res_sublead_bjet_pt"], 
#                 "sublead_bjet_eta": tree_["Res_sublead_bjet_eta"], 
#                 "sublead_bjet_phi": tree_["Res_sublead_bjet_phi"], 
#                 "sublead_bjet_mass": tree_["Res_sublead_bjet_mass"],
#                 "lead_pho_pt": tree_["lead_pt"], 
#                 "lead_pho_eta": tree_["lead_eta"], 
#                 "lead_pho_phi": tree_["lead_phi"],
#                 "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"],
#                 "lead_pho_mvaID_WP80": tree_["lead_mvaID_WP80"],
#                 "sublead_pho_pt": tree_["sublead_pt"], 
#                 "sublead_pho_eta": tree_["sublead_eta"], 
#                 "sublead_pho_phi": tree_["sublead_phi"],
#                 "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
#                 "sublead_pho_mvaID_WP80": tree_["sublead_mvaID_WP80"],
#                 "weight_central": tree_["weight_central"], 
#                 "weight": tree_["weight"],
#                 "lead_bjet_PNetB": tree_["Res_lead_bjet_btagPNetB"],
#                 "sublead_bjet_PNetB": tree_["Res_sublead_bjet_btagPNetB"],
#                 "lead_isScEtaEB": tree_["lead_isScEtaEB"],
#                 "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
#                 "CosThetaStar_CS": tree_["Res_CosThetaStar_CS"], 
#                 "CosThetaStar_gg": tree_["Res_CosThetaStar_gg"],
#                 "CosThetaStar_jj": tree_["Res_CosThetaStar_jj"],
#                 "DeltaR_jg_min": tree_["Res_DeltaR_jg_min"],
#                 "pholead_PtOverM": tree_["Res_pholead_PtOverM"], 
#                 "phosublead_PtOverM": tree_["Res_phosublead_PtOverM"],
#                 "FirstJet_PtOverM": tree_["Res_FirstJet_PtOverM"], 
#                 "SecondJet_PtOverM": tree_["Res_SecondJet_PtOverM"],
#                 "lead_pho_mvaID": tree_["lead_mvaID"], 
#                 "sublead_pho_mvaID": tree_["sublead_mvaID"],
#                 "DeltaR_j1g1": tree_["Res_DeltaR_j1g1"],
#                 "DeltaR_j2g1": tree_["Res_DeltaR_j2g1"],
#                 "DeltaR_j1g2": tree_["Res_DeltaR_j1g2"], 
#                 "DeltaR_j2g2": tree_["Res_DeltaR_j2g2"],
#                 "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
#                 "bbgg_pt": tree_["Res_HHbbggCandidate_pt"],
#                 "bbgg_eta": tree_["Res_HHbbggCandidate_eta"], 
#                 "bbgg_phi": tree_["Res_HHbbggCandidate_phi"],
#                 "MX": tree_["Res_M_X"],
#                 "DeltaPhi_j1MET": tree_["Res_DeltaPhi_j1MET"],
#                 "DeltaPhi_j2MET": tree_["Res_DeltaPhi_j2MET"],
#                 "Res_chi_t0": tree_["Res_chi_t0"], 
#                 "Res_chi_t1": tree_["Res_chi_t1"],
#                 "lepton1_mvaID": tree_["lepton1_mvaID"],
#                 "lepton1_pt": tree_["lepton1_pt"], 
#                 "lepton1_pfIsoId": tree_["lepton1_pfIsoId"],
#                 "n_jets": tree_["n_jets"],
#             },
#             depth_limit=1,
#         )

#         # add flags needed by regions.py
#         # store as small integers (0/1) to simplify comparisons inside masks
#         n_entries = len(tree_)
#         cms_events["signal"] = ak.Array(np.full(n_entries, 1 if sigflag else 0, dtype=np.int8))
#         cms_events["isdata"] = ak.Array(np.full(n_entries, 1 if isdata else 0, dtype=np.int8))

#         out_events = ak.zip(
#             {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]},
#             depth_limit=1,
#         )

#         # 4-vectors
#         dibjet_ = lVector(
#             cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],
#             cms_events["sublead_bjet_pt"], cms_events["sublead_bjet_eta"], cms_events["sublead_bjet_phi"],
#             cms_events["lead_bjet_mass"], cms_events["sublead_bjet_mass"],
#         )
#         diphoton_ = lVector(
#             cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],
#             cms_events["sublead_pho_pt"], cms_events["sublead_pho_eta"], cms_events["sublead_pho_phi"],
#         )
#         cms_events["dibjet_mass"] = dibjet_.mass
#         cms_events["dibjet_pt"]   = dibjet_.pt
#         cms_events["diphoton_mass"] = diphoton_.mass
#         cms_events["diphoton_pt"]   = diphoton_.pt
#         cms_events["dibjet_eta"] = dibjet_.eta
#         cms_events["dibjet_phi"] = dibjet_.phi
#         cms_events["diphoton_eta"] = diphoton_.eta
#         cms_events["diphoton_phi"] = diphoton_.phi

#         # ratios
#         cms_events["lead_pt_over_diphoton_mass"]   = cms_events["lead_pho_pt"]    / cms_events["diphoton_mass"]
#         cms_events["sublead_pt_over_diphoton_mass"] = cms_events["sublead_pho_pt"] / cms_events["diphoton_mass"]
#         cms_events["lead_pt_over_dibjet_mass"]     = cms_events["lead_bjet_pt"]   / cms_events["dibjet_mass"]
#         cms_events["sublead_pt_over_dibjet_mass"]  = cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
#         cms_events["diphoton_bbgg_mass"] = cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
#         cms_events["dibjet_bbgg_mass"]   = cms_events["dibjet_pt"]   / cms_events["bbgg_mass"]

#         # max gamma MVA
#         cms_events["max_gamma_MVA_ID"] = ak.where(
#             cms_events["lead_pho_mvaID"] > cms_events["sublead_pho_mvaID"],
#             cms_events["lead_pho_mvaID"], cms_events["sublead_pho_mvaID"]
#         )

#         # region masks (now that 'signal' and 'isdata' exist)
#         from regions import (
#             get_mask_preselection, get_mask_selection,
#             get_mask_srbbgg, get_mask_srbbggMET,
#             get_mask_crantibbgg, get_mask_crbbantigg, get_mask_crantibbantigg,
#             get_mask_sideband, get_mask_idmva_presel, get_mask_idmva_sideband,
#         )
#         cms_events["preselection"]     = get_mask_preselection(cms_events)
#         cms_events["selection"]        = get_mask_selection(cms_events)
#         cms_events["srbbgg"]           = get_mask_srbbgg(cms_events)
#         cms_events["srbbggMET"]        = get_mask_srbbggMET(cms_events)
#         cms_events["crbbantigg"]       = get_mask_crbbantigg(cms_events)
#         cms_events["crantibbgg"]       = get_mask_crantibbgg(cms_events)
#         cms_events["crantibbantigg"]   = get_mask_crantibbantigg(cms_events)
#         cms_events["sideband"]         = get_mask_sideband(cms_events)
#         cms_events["idmva_presel"]     = get_mask_idmva_presel(cms_events)
#         cms_events["idmva_sideband"]   = get_mask_idmva_sideband(cms_events)

#         # copy selected fields to out_events
#         keys_to_copy = [
#             # puppiMET
#             "puppiMET_pt","puppiMET_phi","puppiMET_phiJERDown","puppiMET_phiJERUp",
#             "puppiMET_phiJESDown","puppiMET_phiJESUp","puppiMET_phiUnclusteredDown","puppiMET_phiUnclusteredUp",
#             "puppiMET_ptJERDown","puppiMET_ptJERUp","puppiMET_ptJESDown","puppiMET_ptJESUp",
#             "puppiMET_ptUnclusteredDown","puppiMET_ptUnclusteredUp","puppiMET_sumEt",
#             # photons/jets
#             "lead_pho_pt","lead_pho_eta","lead_pho_phi",
#             "sublead_pho_pt","sublead_pho_eta","sublead_pho_phi",
#             "lead_bjet_pt","lead_bjet_eta","lead_bjet_phi",
#             "sublead_bjet_pt","sublead_bjet_eta","sublead_bjet_phi",
#             # masses/kin
#             "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta","bbgg_phi",
#             # NR vars
#             "DeltaPhi_j1MET","DeltaPhi_j2MET","Res_chi_t0","Res_chi_t1",
#             "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId","n_jets",
#             # weights
#             "weight_central",
#             # extra
#             "dibjet_eta","dibjet_phi","diphoton_eta","diphoton_phi",
#             "lead_bjet_PNetB","sublead_bjet_PNetB",
#             "pholead_PtOverM","phosublead_PtOverM","FirstJet_PtOverM","SecondJet_PtOverM",
#             "CosThetaStar_CS","CosThetaStar_jj","CosThetaStar_gg","DeltaR_jg_min",
#             "lead_pt_over_diphoton_mass","sublead_pt_over_diphoton_mass",
#             "lead_pt_over_dibjet_mass","sublead_pt_over_dibjet_mass",
#             "diphoton_bbgg_mass","dibjet_bbgg_mass",
#             "lead_pho_mvaID_WP90","lead_pho_mvaID_WP80","sublead_pho_mvaID_WP90","sublead_pho_mvaID_WP80",
#             "lead_pho_mvaID","sublead_pho_mvaID","max_gamma_MVA_ID",
#             # region flags
#             "preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband",
#             "idmva_sideband","idmva_presel",
#             # ΔR
#             "DeltaR_j1g1","DeltaR_j2g1","DeltaR_j1g2","DeltaR_j2g2",
#             # also store flags used by regions if you want them in trees:
#             "signal","isdata",
#         ]
#         for k in keys_to_copy:
#             out_events[k] = cms_events[k]

#         # per-region weights (guard against divide-by-zero by replacing non-finite weight_central)
#         wc = ak.to_numpy(out_events["weight_central"])
#         wc = np.where(np.isfinite(wc) & (wc != 0.0), wc, 1.0)
#         base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_) / wc
#         base_w = np.where(np.isfinite(base_w), base_w, 0.0)

#         for r in ["preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband","idmva_sideband","idmva_presel"]:
#             out_events["weight_"+r] = base_w
            
#         # ---------- Accumulate "processed_events" (full) per sample ----------
#         PROC_ACC.setdefault(sample_name_norm, []).append(ak_to_numpy_dict(out_events))

#         # ---------- Per-region: accumulate hists + regional trees ----------
#         for ireg in regions:
#             thisregion = out_events[out_events[ireg] == True]
#             thisregion_ = thisregion[~(ak.is_none(thisregion))]

#             weight_ = "weight_" + ireg

#             # --- Histograms: accumulate in memory
#             for ivar in variables_common[ireg]:
#                 hist_name_ = f"{vardict[ivar]}"
#                 vals = ak.to_numpy(thisregion_[ivar])
#                 wts  = ak.to_numpy(thisregion_[weight_])
#                 if wts is not None:
#                     wts = np.where(np.isfinite(wts), wts, 0.0)
#                 h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])

#                 key = (sample_name_norm, ireg, hist_name_)
#                 if key not in HIST_CACHE:
#                     acc = h.Clone(f"{hist_name_}__acc")
#                     acc.Reset()
#                     acc.SetDirectory(0)
#                     HIST_CACHE[key] = acc
#                 HIST_CACHE[key].Add(h)
#                 del h

#             # --- Trees: accumulate chunks per (sample, region)
#             tree_data_ = ak_to_numpy_dict(thisregion_)
#             TREE_ACC.setdefault((sample_name_norm, ireg), []).append(tree_data_)

# # ========== CLI / IO discovery / final write-out ==========

# def main():
#     ap = argparse.ArgumentParser(description="hhbbgg analyzer (parquet) with multi-era support + per-sample merge")
#     ap.add_argument(
#         "-i", "--inFile", action="append",
#         help="Single ROOT/Parquet file or a directory. Can be given multiple times to merge across folders/eras."
#     )
#     ap.add_argument("--year", required=True, help="e.g. 2022 or 2023")
#     ap.add_argument("--era",  required=True, help="e.g. PreEE, PostEE, All")
#     ap.add_argument("--tag", default=None, help="If multiple -i are given, outputs go to outputfiles/merged/<tag>")
#     args = ap.parse_args()

#     cfg = RunConfig(args.year, args.era)

#     # Resolve input paths
#     in_paths = []
#     if args.inFile:
#         for ip in args.inFile:
#             in_paths.append(Path(ip).resolve())
#     else:
#         in_paths.append(cfg.raw_path)

#     # Choose output dir
#     if len(in_paths) > 1:
#         merged_root = cfg.outputs_root / "merged"
#         merged_name = args.tag or "AllInputs"
#         out_dir = merged_root / merged_name
#     else:
#         out_dir = cfg.outputs_path
#     os.makedirs(out_dir, exist_ok=True)

#     # Build input file list
#     inputfiles = []
#     for path in in_paths:
#         if path.is_file():
#             if str(path).lower().endswith(".parquet"):
#                 inputfiles.append(str(path))
#             elif str(path).lower().endswith(".root"):
#                 print(f"[WARN] ROOT file detected and skipped in parquet analyzer: {path}")
#             else:
#                 print(f"[WARN] Unrecognized input (skipped): {path}")
#         else:
#             # add parquet files
#             pf = [str(p) for p in sorted(path.glob("*.parquet"))]
#             if not pf:
#                 # warn if only ROOTs are present (this script is parquet-only)
#                 roots = [str(p) for p in sorted(path.glob("*.root"))]
#                 if roots:
#                     print(f"[WARN] Only .root found in {path}, parquet analyzer will skip them.")
#             inputfiles.extend(pf)

#     if not inputfiles:
#         raise FileNotFoundError(f"No .parquet files found in: {', '.join(str(p) for p in in_paths)}")

#     print(f"[INFO] Will process {len(inputfiles)} parquet file(s).")
#     # Process files
#     xsec_lumi_cache = {}
#     for infile_ in inputfiles:
#         process_parquet_file(infile_, xsec_lumi_cache)

#     # Prepare output files (write once)
#     hist_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-histograms.root")
#     tree_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-trees.root")

#     hist_tfile = ROOT.TFile(hist_file_path, "RECREATE")  # PyROOT for histograms
#     tree_upfile = uproot.recreate(tree_file_path)        # uproot for trees
#     out_files = {"hist": hist_tfile, "tree": tree_upfile}

#     # ---------- Write accumulated histograms grouped by Sample/Region ----------
#     print("[INFO] Writing accumulated histograms...")
#     for (sample, region, varname), h in HIST_CACHE.items():
#         dir_path = f"{sample}/{region}"
#         ensure_dir_in_tfile(out_files["hist"], dir_path).cd()
#         h_clone = h.Clone(varname)
#         h_clone.SetDirectory(ROOT.gDirectory)
#         h_clone.Write()
#         del h_clone

#     # ---------- Write accumulated trees ----------
#     print("[INFO] Writing accumulated trees (regional + processed_events)...")
#     # Regional trees
#     for (sample, region), chunks in TREE_ACC.items():
#         merged = concat_field_dicts(chunks)
#         out_files["tree"][f"{sample}/{region}"] = merged

#     # Full processed_events per sample
#     for sample, chunks in PROC_ACC.items():
#         merged = concat_field_dicts(chunks)
#         out_files["tree"][f"{sample}/processed_events"] = merged

#     # Close files
#     out_files["tree"].close()
#     out_files["hist"].Write()
#     out_files["hist"].Close()
#     print(f"[OK] Wrote trees to:      {tree_file_path}")
#     print(f"[OK] Wrote histograms to: {hist_file_path}")

# if __name__ == "__main__":
#     main()

            
# #### Changes made above of this one


# #         print(f"Total number of events in fulltree_: {len(fulltree_)}")
# #         if len(fulltree_) == 0:
# #             print("WARNING: fulltree_ is empty! Initializing.")
# #             fulltree_ = out_events
# #         else:
# #             fulltree_ = ak.concatenate([fulltree_, out_events], axis=0)
# #         print(f"Finished processing {len(fulltree_)} total events from {inputfile}")

# #     # ---------------- Write processed flat tree via uproot ----------------
# #     print(f"Writing {len(fulltree_)} events to ROOT file (trees).")
# #     numpy_compatible_tree = {
# #         key: ak.to_numpy(fulltree_[key]).astype("int64")
# #         if "int" in str(fulltree_[key].type)
# #         else ak.to_numpy(fulltree_[key])
# #         for key in fulltree_.fields
# #     }
# #     out_files["tree"]["processed_events"] = numpy_compatible_tree
# #     print("Saved processed data to ROOT file (trees).")

# #     # ---------------- Make histograms and regional trees ----------------
# #     from variables import vardict, regions, variables_common
# #     from binning import binning

# #     print("Making histograms and trees")
# #     sample_name = os.path.basename(inputfile).replace(".parquet", "").replace(".root", "")

# #     # Hist file: create /Sample/<region>
# #     ensure_dir_in_tfile(out_files["hist"], sample_name)

# #     for ireg in regions:
# #         thisregion = fulltree_[fulltree_[ireg] == True]
# #         thisregion_ = thisregion[~(ak.is_none(thisregion))]
# #         weight_ = "weight_" + ireg

# #         # --- Histograms with PyROOT (under Sample/Region) ---
# #         region_dir = ensure_dir_in_tfile(out_files["hist"], f"{sample_name}/{ireg}")
# #         for ivar in variables_common[ireg]:
# #             hist_name_ = f"{vardict[ivar]}"
# #             vals = ak.to_numpy(thisregion_[ivar])
# #             wts  = ak.to_numpy(thisregion_[weight_])
# #             if wts is not None:
# #                 wts = np.where(np.isfinite(wts), wts, 0.0)
# #             h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])
# #             region_dir.cd()
# #             h.Write()
# #             del h

# #         # --- Regional TTrees via uproot ---
# #         tree_data_ = {
# #             key: (
# #                 np.nan_to_num(
# #                     ak.to_numpy(ak.fill_none(thisregion_[key], -9999)).astype("int64"),
# #                     nan=-9999, posinf=999999999, neginf=-999999999
# #                 )
# #                 if np.issubdtype(
# #                     ak.to_numpy(ak.fill_none(thisregion_[key], -9999)).dtype, np.integer
# #                 )
# #                 else np.nan_to_num(
# #                     ak.to_numpy(ak.fill_none(thisregion_[key], -9999)),
# #                     nan=-9999, posinf=999999999, neginf=-999999999
# #                 )
# #             )
# #             for key in thisregion_.fields
# #         }
# #         out_files["tree"][f"{sample_name}/{ireg}"] = tree_data_

# #     print("Done")

# # # ---------------- Output files (separate writers!) ----------------
# # output_dir = "outputfiles"
# # os.makedirs(output_dir, exist_ok=True)

# # # hist_file_path = os.path.join(output_dir, "hhbbgg_analyzer-v2-histograms.root")
# # # tree_file_path = os.path.join(output_dir, "hhbbgg_analyzer-v2-trees.root")
# # hist_file_path = os.path.join(out_dir, f"hhbbgg_analyzer-v2-histograms_{cfg.year}_{cfg.era}.root")
# # tree_file_path = os.path.join(out_dir, f"hhbbgg_analyzer-v2-trees_{cfg.year}_{cfg.era}.root")


# # hist_tfile = ROOT.TFile(hist_file_path, "RECREATE")  # PyROOT for histograms
# # tree_upfile = uproot.recreate(tree_file_path)        # uproot for trees

# # out_files = {"hist": hist_tfile, "tree": tree_upfile}

# # # ---------------- Inputs ----------------
# # # if os.path.isfile(inputfiles_):
# # #     inputfiles = [inputfiles_]
# # # else:
# # #     inputfiles = [
# # #         os.path.join(inputfiles_, f)
# # #         for f in os.listdir(inputfiles_)
# # #         if f.endswith(".parquet") or f.endswith(".root")
# # #     ]

# # if in_path.is_file():
# #     inputfiles = [str(in_path)]
# # else:
# #     inputfiles = [str(p) for p in sorted(in_path.glob("*.parquet"))] + \
# #                  [str(p) for p in sorted(in_path.glob("*.root"))]
# #     if not inputfiles:
# #         raise FileNotFoundError(f"No .parquet or .root files found in: {in_path}")



# # # ---------------- Main ----------------
# # def main():
# #     for infile_ in inputfiles:
# #         process_parquet_file(infile_, out_files)

# #     out_files["tree"].close()
# #     out_files["hist"].Write()
# #     out_files["hist"].Close()
# #     print(f"Wrote trees to {tree_file_path}")
# #     print(f"Wrote histograms to {hist_file_path}")

# # if __name__ == "__main__":
# #     main()



#NEW 


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import os
# import re
# import argparse
# from pathlib import Path

# import numpy as np
# import uproot
# import pandas as pd
# import awkward as ak
# import pyarrow.parquet as pq
# from pyarrow import Table
# import pyarrow
# import yaml

# from config.utils import lVector
# from normalisation import getXsec, getLumi
# from config.config import RunConfig

# # ---------------- PyROOT ONLY for histograms (separate file) ----------------
# import ROOT
# ROOT.gROOT.SetBatch(True)
# ROOT.TH1.AddDirectory(False)

# # ---------------- Helpers ----------------
# def _ensure_1d(a):
#     a = np.asarray(a)
#     return a.ravel()

# def make_th1_pyroot(values, weights, name, title, binning):
#     v  = _ensure_1d(values)
#     w  = None if weights is None else _ensure_1d(weights)

#     if w is not None:
#         mask = np.isfinite(v) & np.isfinite(w)
#         v = v[mask]; w = w[mask]
#     else:
#         mask = np.isfinite(v)
#         v = v[mask]

#     v2 = v.copy()

#     def _is_angular_name(s):
#         s = (s or "").lower()
#         return ("phi" in s) or ("deltaphi" in s) or s.endswith("_phi")

#     def _maybe_angle_edges(arr):
#         if arr.size < 2 or not np.isfinite(arr).all():
#             return False
#         rng = float(np.nanmax(arr) - np.nanmin(arr))
#         return (rng <= 2*np.pi + 1e-6) and (np.nanmin(arr) >= -2*np.pi-1e-6) and (np.nanmax(arr) <= 2*np.pi+1e-6)

#     def _unwrap_edges_and_values(edges, vals):
#         e = edges.astype("f8").copy()
#         for i in range(1, e.size):
#             if e[i] <= e[i-1] - 1e-15:
#                 shift = 2*np.pi * np.ceil((e[i-1] - e[i] + 1e-15)/(2*np.pi))
#                 e[i:] = e[i:] + shift
#         e0 = e[0]; two_pi = 2*np.pi
#         vals_out = vals.copy()
#         fm = np.isfinite(vals_out)
#         vals_out[ fm ] = (vals_out[ fm ] - e0) % two_pi + e0
#         return e, vals_out

#     if isinstance(binning, np.ndarray) or (
#         isinstance(binning, (list, tuple)) and not (
#             len(binning) == 3 and all(np.isscalar(x) for x in binning)
#         )
#     ):
#         edges_np = np.asarray(binning, dtype="f8").ravel()
#         edges_np = edges_np[np.isfinite(edges_np)]
#         if edges_np.size < 2:
#             raise ValueError(f"[{name}] Variable bin edges must have length >= 2, got: {edges_np}")

#         if not np.all(np.diff(edges_np) > 0):
#             if _is_angular_name(name) or _maybe_angle_edges(edges_np):
#                 edges_np, v2 = _unwrap_edges_and_values(edges_np, v2)
#             else:
#                 e_sorted_unique = np.unique(edges_np)
#                 if e_sorted_unique.size < 2 or not np.all(np.diff(e_sorted_unique) > 0):
#                     raise ValueError(f"[{name}] Invalid variable bin edges (not strictly increasing).")
#                 print(f"[WARN] {name}: edges not strictly increasing; using sorted unique edges.")
#                 edges_np = e_sorted_unique

#         nb = len(edges_np) - 1
#         h = ROOT.TH1D(name, title, int(nb), edges_np)
#     else:
#         nb, lo, hi = binning
#         nb = int(nb); lo = float(lo); hi = float(hi)
#         if not np.isfinite([lo, hi]).all() or hi <= lo or nb <= 0:
#             raise ValueError(f"[{name}] Invalid (nb, lo, hi): {binning}")
#         h = ROOT.TH1D(name, title, nb, lo, hi)
#         edges_np = np.linspace(lo, hi, nb + 1, dtype="f8")

#     if v2.dtype == np.bool_:
#         v2 = v2.astype("f8")
#     if w is not None and w.dtype == np.bool_:
#         w = w.astype("f8")

#     counts, _ = np.histogram(v2, bins=edges_np, weights=w)
#     if w is None:
#         sumw2 = counts.astype("f8")
#     else:
#         sumw2, _ = np.histogram(v2, bins=edges_np, weights=w * w)

#     h.Sumw2()
#     for i in range(1, h.GetNbinsX() + 1):
#         c  = float(counts[i - 1])
#         e2 = float(sumw2[i - 1])
#         h.SetBinContent(i, c)
#         h.SetBinError(i, float(np.sqrt(e2) if e2 >= 0 else 0.0))

#     h.SetDirectory(0)
#     return h


# def detect_year_era_from_name(path: str):
#     name = os.path.basename(path).lower()
#     year = "2022" if "2022" in name else ("2023" if "2023" in name else None)
#     era = None
#     if year == "2022":
#         if "preee" in name:  era = "PreEE"
#         if "postee" in name: era = "PostEE"
#     elif year == "2023":
#         if "prebpix" in name:  era = "preBPix"
#         if "postbpix" in name: era = "postBPix"
#     return year, era


# def ensure_dir_in_tfile(tfile, path):
#     curr = tfile
#     if not path:
#         return curr
#     for part in path.split('/'):
#         d = curr.GetDirectory(part)
#         curr = d if d else curr.mkdir(part)
#     return curr

# def normalize_sample_name(name: str) -> str:
#     base = os.path.basename(name)
#     base = re.sub(r"\.(parquet|root)$", "", base, flags=re.IGNORECASE)
#     base = re.sub(r"(_part\d+|_chunk\d+|_\d+of\d+)$", "", base, flags=re.IGNORECASE)
#     # base = re.sub(r"[_-]?(2022|2023)(PreEE|PostEE|All)?", "", base, flags=re.IGNORECASE)
#     base = re.sub(r"[_-]?(2022|2023)(PreEE|PostEE|All|preBPix|postBPix)?", "", base, flags=re.IGNORECASE)
#     return base

# def ak_to_numpy_dict(arr: ak.Array) -> dict:
#     out = {}
#     for key in arr.fields:
#         filled = ak.fill_none(arr[key], -9999)
#         np_arr = ak.to_numpy(filled)
#         if np.issubdtype(np_arr.dtype, np.integer):
#             np_arr = np.nan_to_num(np_arr.astype("int64"), nan=-9999, posinf=999999999, neginf=-999999999)
#         else:
#             np_arr = np.nan_to_num(np_arr, nan=-9999, posinf=999999999, neginf=-999999999)
#         out[key] = np_arr
#     return out

# def concat_field_dicts(dict_list):
#     out = {}
#     if not dict_list:
#         return out
#     keys = dict_list[0].keys()
#     for k in keys:
#         arrs = [np.asarray(d[k]) for d in dict_list if k in d]
#         if len(arrs) == 0:
#             out[k] = np.array([], dtype=np.float32)
#         elif len(arrs) == 1:
#             out[k] = arrs[0]
#         else:
#             out[k] = np.concatenate(arrs, axis=0)
#     return out

# ## dtypes before writing to avoid out of range in 32-bit
# def sanitize_for_uproot(d: dict) -> dict:
#     """
#     Make arrays uproot-safe:
#       * ints -> int64
#       * uints -> int64 (may clip negatives if any appear after cast, but we don't expect them)
#       * floats -> float64
#       * bool -> int8
#       * forbid object dtypes
#     Also ensure finite values (replace NaN/Inf).
#     """
#     out = {}
#     for k, v in d.items():
#         a = np.asarray(v)
#         if a.dtype == np.bool_:
#             a = a.astype(np.int8, copy=False)
#         elif a.dtype.kind == "u":  # unsigned ints
#             a = a.astype(np.int64, copy=False)
#         elif a.dtype.kind == "i":  # signed ints
#             a = a.astype(np.int64, copy=False)
#         elif a.dtype.kind == "f":  # floats
#             a = a.astype(np.float64, copy=False)
#         elif a.dtype.kind == "O":
#             raise TypeError(f"Branch '{k}' has object dtype; not supported in ROOT trees.")
#         # replace non-finites with sentinels
#         if a.dtype.kind in ("i", "u"):
#             a = np.nan_to_num(a, nan=-9999, posinf=999999999, neginf=-999999999)
#         else:
#             a = np.nan_to_num(a, nan=-9999.0, posinf=9.999e306, neginf=-9.999e306)
#         out[k] = a
#     return out


# # ---------------- Global accumulators ----------------
# HIST_CACHE = {}   # (sample, region, varname) -> TH1D
# TREE_ACC   = {}   # (sample, region) -> [dict(field->np.ndarray)]
# PROC_ACC   = {}   # sample -> [dict(field->np.ndarray)]

# # ---------------- Utils ----------------
# def is_signal_from_name(name: str) -> bool:
#     s = name
#     return any(x in s for x in [
#         "GluGluToHH", "VBFHH", "Radion", "Graviton", "XToHH", "HHTo", "HHTobbgg"
#     ])
    
# def is_dd_template(path: str) -> bool:
#     """Return True for DD fake-γ templates (rescaled parquet files)."""
#     b = os.path.basename(path).lower()
#     return any(k in b for k in (
#         "ddqcdgjet_rescaled",
#         "ggjets_low_rescaled",
#         "ggjets_high_rescaled",
#         "ddqcdgjet",   # generic catch-all
#     ))

# # Which column to use for DD event weights if not 'weight'
# DD_WEIGHT_COLUMNS = ("weight", "evt_weight", "w", "fake_weight")

# def _get_dd_weight_col(all_columns) -> str:
#     """Find the name of the event-weight column in DD files."""
#     cols = set(map(str, all_columns))
#     for c in DD_WEIGHT_COLUMNS:
#         if c in cols:
#             return c
#     raise KeyError(
#         "No DD weight column found in DD template. "
#         f"Tried: {', '.join(DD_WEIGHT_COLUMNS)}; available: {sorted(cols)}"
#     )

# # ---------------- Core processing ----------------
# def process_parquet_file(inputfile, cli_year, cli_era, xsec_lumi_cache=None):
#     """
#     Process a single parquet file and accumulate:
#       - histograms per (sample, region, variable)
#       - regional trees per (sample, region)
#       - full processed_events per sample
#     """
#     print(f"[INFO] Processing Parquet file: {inputfile}")
#     required_columns = [
#         "run",
#         "lumi",
#         "event",
#         "puppiMET_pt",
#         "puppiMET_phi",
#         "puppiMET_phiJERDown",
#         "puppiMET_phiJERUp",
#         "puppiMET_phiJESDown",
#         "puppiMET_phiJESUp",
#         "puppiMET_phiUnclusteredDown",
#         "puppiMET_phiUnclusteredUp",
#         "puppiMET_ptJERDown",
#         "puppiMET_ptJERUp",
#         "puppiMET_ptJESDown",
#         "puppiMET_ptJESUp",
#         "puppiMET_ptUnclusteredDown",
#         "puppiMET_ptUnclusteredUp",
#         "puppiMET_sumEt",
#         "Res_lead_bjet_pt",
#         "Res_lead_bjet_eta",
#         "Res_lead_bjet_phi",
#         "Res_lead_bjet_mass",
#         "Res_sublead_bjet_pt",
#         "Res_sublead_bjet_eta",
#         "Res_sublead_bjet_phi",
#         "Res_sublead_bjet_mass",
#         "lead_pt",
#         "lead_eta",
#         "lead_phi",
#         "lead_mvaID_WP90",
#         "lead_mvaID_WP80",
#         "sublead_pt",
#         "sublead_eta",
#         "sublead_phi",
#         "sublead_mvaID_WP90",
#         "sublead_mvaID_WP80",
#         "weight",
#         "weight_central",
#         "Res_lead_bjet_btagPNetB",
#         "Res_sublead_bjet_btagPNetB",
#         "lead_isScEtaEB",
#         "sublead_isScEtaEB",
#         "Res_HHbbggCandidate_pt",
#         "Res_HHbbggCandidate_eta",
#         "Res_HHbbggCandidate_phi",
#         "Res_HHbbggCandidate_mass",
#         "Res_CosThetaStar_CS",
#         "Res_CosThetaStar_gg",
#         "Res_CosThetaStar_jj",
#         "Res_DeltaR_jg_min",
#         "Res_pholead_PtOverM",
#         "Res_phosublead_PtOverM",
#         "Res_FirstJet_PtOverM",
#         "Res_SecondJet_PtOverM",
#         "lead_mvaID",
#         "sublead_mvaID",
#         "Res_DeltaR_j1g1",
#         "Res_DeltaR_j2g1",
#         "Res_DeltaR_j1g2",
#         "Res_DeltaR_j2g2",
#         "Res_M_X",
#         "Res_DeltaPhi_j1MET",
#         "Res_DeltaPhi_j2MET",
#         "Res_chi_t0",
#         "Res_chi_t1",
#         "lepton1_mvaID",
#         "lepton1_pt",
#         "lepton1_pfIsoId",
#         "n_jets",
#     ]

#     parquet_file = pq.ParquetFile(inputfile)

#     base = os.path.basename(inputfile)
#     sample_name_raw = base.replace(".parquet", "").replace(".root", "")
#     sample_name_norm = normalize_sample_name(sample_name_raw)

#     isdata = "Data" in base
#     sigflag = is_signal_from_name(base)
#     isdd   = is_dd_template(base)


    
#     det_year, det_era = detect_year_era_from_name(inputfile)
#     use_year = det_year or str(cli_year)
#     use_era  = det_era  or str(cli_era) 

#     if xsec_lumi_cache is None:
#         xsec_lumi_cache = {}
#     if inputfile not in xsec_lumi_cache:
#         if isdata or isdd:
#             # No σ×L scaling for data or DD templates
#             xsec_lumi_cache[inputfile] = (1.0, 1.0)
#         else:
#             # det_year, det_era = detect_year_era_from_name(inputfile)
#             # use_year = det_year or str(cli_year)   # fallback to CLI if detection failed
#             # use_era  = det_era  or str(cli_era)
            
#             xsec_lumi_cache[inputfile] = (float(getXsec(inputfile)), 
#                                           float(getLumi(use_year, use_era)) * 1000.0,      # lumi in pb^-1
#                                           )      
#     xsec_, lumi_ = xsec_lumi_cache[inputfile]
#     # print(f"[NORM] sample={os.path.basename(inputfile)} xsec={xsec_} pb, lumi={lumi_/1000.0:.3f} fb^-1 ({det_year or cli_year} {det_era or cli_era})")
#     print(f"[NORM] sample={os.path.basename(inputfile)} xsec={xsec_} pb, "
#       f"lumi={lumi_/1000.0:.3f} fb^-1 ({use_year} {use_era}) "
#       f"[flags: data={isdata} dd = {isdd}]") 


#     # region utils & plotting config
#     from regions import (
#         get_mask_preselection,
#         get_mask_selection,
#         get_mask_srbbgg,
#         get_mask_srbbggMET,
#         get_mask_crantibbgg, 
#         get_mask_crbbantigg, 
#         get_mask_crantibbantigg,
#         get_mask_sideband,
#         get_mask_idmva_presel, 
#         get_mask_idmva_sideband,
#     )
#     from variables import vardict, regions, variables_common
#     from binning import binning

#     for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
#         df = batch.to_pandas()
#         print(f"[INFO] Batch rows: {len(df)}")
#         tree_ = ak.from_arrow(pyarrow.Table.from_pandas(df))

#         cms_events = ak.zip(
#             {
#                 "run": tree_["run"], "lumi": tree_["lumi"],
#                 "event": tree_["event"],
#                 "puppiMET_pt": tree_["puppiMET_pt"],
#                 "puppiMET_phi": tree_["puppiMET_phi"],
#                 "puppiMET_phiJERDown": tree_["puppiMET_phiJERDown"],
#                 "puppiMET_phiJERUp": tree_["puppiMET_phiJERUp"],
#                 "puppiMET_phiJESDown": tree_["puppiMET_phiJESDown"],
#                 "puppiMET_phiJESUp": tree_["puppiMET_phiJESUp"],
#                 "puppiMET_phiUnclusteredDown": tree_["puppiMET_phiUnclusteredDown"],
#                 "puppiMET_phiUnclusteredUp": tree_["puppiMET_phiUnclusteredUp"],
#                 "puppiMET_ptJERDown": tree_["puppiMET_ptJERDown"],
#                 "puppiMET_ptJERUp": tree_["puppiMET_ptJERUp"],
#                 "puppiMET_ptJESDown": tree_["puppiMET_ptJESDown"],
#                 "puppiMET_ptJESUp": tree_["puppiMET_ptJESUp"],
#                 "puppiMET_ptUnclusteredDown": tree_["puppiMET_ptUnclusteredDown"],
#                 "puppiMET_ptUnclusteredUp": tree_["puppiMET_ptUnclusteredUp"],
#                 "puppiMET_sumEt": tree_["puppiMET_sumEt"],
#                 "lead_bjet_pt": tree_["Res_lead_bjet_pt"], 
#                 "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
#                 "lead_bjet_phi": tree_["Res_lead_bjet_phi"], 
#                 "lead_bjet_mass": tree_["Res_lead_bjet_mass"],
#                 "sublead_bjet_pt": tree_["Res_sublead_bjet_pt"],
#                 "sublead_bjet_eta": tree_["Res_sublead_bjet_eta"],
#                 "sublead_bjet_phi": tree_["Res_sublead_bjet_phi"],
#                 "sublead_bjet_mass": tree_["Res_sublead_bjet_mass"],
#                 "lead_pho_pt": tree_["lead_pt"], 
#                 "lead_pho_eta": tree_["lead_eta"], 
#                 "lead_pho_phi": tree_["lead_phi"],
#                 "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"], 
#                 "lead_pho_mvaID_WP80": tree_["lead_mvaID_WP80"],
#                 "sublead_pho_pt": tree_["sublead_pt"], 
#                 "sublead_pho_eta": tree_["sublead_eta"], 
#                 "sublead_pho_phi": tree_["sublead_phi"],
#                 "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
#                 "sublead_pho_mvaID_WP80": tree_["sublead_mvaID_WP80"],
#                 "weight_central": tree_["weight_central"],
#                 "weight": tree_["weight"],
#                 "lead_bjet_PNetB": tree_["Res_lead_bjet_btagPNetB"], 
#                 "sublead_bjet_PNetB": tree_["Res_sublead_bjet_btagPNetB"],
#                 "lead_isScEtaEB": tree_["lead_isScEtaEB"],
#                 "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
#                 "CosThetaStar_CS": tree_["Res_CosThetaStar_CS"],
#                 "CosThetaStar_gg": tree_["Res_CosThetaStar_gg"], 
#                 "CosThetaStar_jj": tree_["Res_CosThetaStar_jj"],
#                 "DeltaR_jg_min": tree_["Res_DeltaR_jg_min"],
#                 "pholead_PtOverM": tree_["Res_pholead_PtOverM"],
#                 "phosublead_PtOverM": tree_["Res_phosublead_PtOverM"],
#                 "FirstJet_PtOverM": tree_["Res_FirstJet_PtOverM"], 
#                 "SecondJet_PtOverM": tree_["Res_SecondJet_PtOverM"],
#                 "lead_pho_mvaID": tree_["lead_mvaID"],
#                 "sublead_pho_mvaID": tree_["sublead_mvaID"],
#                 "DeltaR_j1g1": tree_["Res_DeltaR_j1g1"],
#                 "DeltaR_j2g1": tree_["Res_DeltaR_j2g1"],
#                 "DeltaR_j1g2": tree_["Res_DeltaR_j1g2"],
#                 "DeltaR_j2g2": tree_["Res_DeltaR_j2g2"],
#                 "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
#                 "bbgg_pt": tree_["Res_HHbbggCandidate_pt"],
#                 "bbgg_eta": tree_["Res_HHbbggCandidate_eta"],
#                 "bbgg_phi": tree_["Res_HHbbggCandidate_phi"],
#                 "MX": tree_["Res_M_X"],
#                 "DeltaPhi_j1MET": tree_["Res_DeltaPhi_j1MET"],
#                 "DeltaPhi_j2MET": tree_["Res_DeltaPhi_j2MET"],
#                 "Res_chi_t0": tree_["Res_chi_t0"],
#                 "Res_chi_t1": tree_["Res_chi_t1"],
#                 "lepton1_mvaID": tree_["lepton1_mvaID"],
#                 "lepton1_pt": tree_["lepton1_pt"], 
#                 "lepton1_pfIsoId": tree_["lepton1_pfIsoId"],
#                 "n_jets": tree_["n_jets"],
#             },
#             depth_limit=1,
#         )

#         n_entries = len(tree_)
#         cms_events["signal"] = ak.Array(np.full(n_entries, 1 if sigflag else 0, dtype=np.int8))
#         cms_events["isdata"] = ak.Array(np.full(n_entries, 1 if isdata else 0, dtype=np.int8))
#         cms_events["isdd"]   = ak.Array(np.full(n_entries, 1 if isdd   else 0, dtype=np.int8))

#         out_events = ak.zip({"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]}, depth_limit=1)

#         dibjet_ = lVector(
#             cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],
#             cms_events["sublead_bjet_pt"], cms_events["sublead_bjet_eta"], cms_events["sublead_bjet_phi"],
#             cms_events["lead_bjet_mass"], cms_events["sublead_bjet_mass"],
#         )
#         diphoton_ = lVector(
#             cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],
#             cms_events["sublead_pho_pt"], cms_events["sublead_pho_eta"], cms_events["sublead_pho_phi"],
#         )
#         cms_events["dibjet_mass"] = dibjet_.mass
#         cms_events["dibjet_pt"]   = dibjet_.pt
#         cms_events["diphoton_mass"] = diphoton_.mass
#         cms_events["diphoton_pt"]   = diphoton_.pt
#         cms_events["dibjet_eta"] = dibjet_.eta
#         cms_events["dibjet_phi"] = dibjet_.phi
#         cms_events["diphoton_eta"] = diphoton_.eta
#         cms_events["diphoton_phi"] = diphoton_.phi

#         cms_events["lead_pt_over_diphoton_mass"]    = cms_events["lead_pho_pt"]     / cms_events["diphoton_mass"]
#         cms_events["sublead_pt_over_diphoton_mass"] = cms_events["sublead_pho_pt"]  / cms_events["diphoton_mass"]
#         cms_events["lead_pt_over_dibjet_mass"]      = cms_events["lead_bjet_pt"]    / cms_events["dibjet_mass"]
#         cms_events["sublead_pt_over_dibjet_mass"]   = cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
#         cms_events["diphoton_bbgg_mass"] = cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
#         cms_events["dibjet_bbgg_mass"]   = cms_events["dibjet_pt"]   / cms_events["bbgg_mass"]

#         cms_events["max_gamma_MVA_ID"] = ak.where(
#             cms_events["lead_pho_mvaID"] > cms_events["sublead_pho_mvaID"],
#             cms_events["lead_pho_mvaID"], cms_events["sublead_pho_mvaID"]
#         )

#         from regions import (
#             get_mask_preselection, get_mask_selection,
#             get_mask_srbbgg, get_mask_srbbggMET,
#             get_mask_crantibbgg, get_mask_crbbantigg, get_mask_crantibbantigg,
#             get_mask_sideband, get_mask_idmva_presel, get_mask_idmva_sideband,
#         )
#         from variables import vardict, regions, variables_common
#         from binning import binning

#         cms_events["preselection"]   = get_mask_preselection(cms_events)
#         cms_events["selection"]      = get_mask_selection(cms_events)
#         cms_events["srbbgg"]         = get_mask_srbbgg(cms_events)
#         cms_events["srbbggMET"]      = get_mask_srbbggMET(cms_events)
#         cms_events["crbbantigg"]     = get_mask_crbbantigg(cms_events)
#         cms_events["crantibbgg"]     = get_mask_crantibbgg(cms_events)
#         cms_events["crantibbantigg"] = get_mask_crantibbantigg(cms_events)
#         cms_events["sideband"]       = get_mask_sideband(cms_events)
#         cms_events["idmva_presel"]   = get_mask_idmva_presel(cms_events)
#         cms_events["idmva_sideband"] = get_mask_idmva_sideband(cms_events)

#         keys_to_copy = [
#             "puppiMET_pt","puppiMET_phi","puppiMET_phiJERDown","puppiMET_phiJERUp",
#             "puppiMET_phiJESDown","puppiMET_phiJESUp","puppiMET_phiUnclusteredDown","puppiMET_phiUnclusteredUp",
#             "puppiMET_ptJERDown","puppiMET_ptJERUp","puppiMET_ptJESDown","puppiMET_ptJESUp",
#             "puppiMET_ptUnclusteredDown","puppiMET_ptUnclusteredUp","puppiMET_sumEt",
#             "lead_pho_pt","lead_pho_eta","lead_pho_phi",
#             "sublead_pho_pt","sublead_pho_eta","sublead_pho_phi",
#             "lead_bjet_pt","lead_bjet_eta","lead_bjet_phi",
#             "sublead_bjet_pt","sublead_bjet_eta","sublead_bjet_phi",
#             "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta","bbgg_phi",
#             "DeltaPhi_j1MET","DeltaPhi_j2MET","Res_chi_t0","Res_chi_t1",
#             "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId","n_jets",
#             "weight_central",
#             "dibjet_eta","dibjet_phi","diphoton_eta","diphoton_phi",
#             "lead_bjet_PNetB","sublead_bjet_PNetB",
#             "pholead_PtOverM","phosublead_PtOverM","FirstJet_PtOverM","SecondJet_PtOverM",
#             "CosThetaStar_CS","CosThetaStar_jj","CosThetaStar_gg","DeltaR_jg_min",
#             "lead_pt_over_diphoton_mass","sublead_pt_over_diphoton_mass",
#             "lead_pt_over_dibjet_mass","sublead_pt_over_dibjet_mass",
#             "diphoton_bbgg_mass","dibjet_bbgg_mass",
#             "lead_pho_mvaID_WP90","lead_pho_mvaID_WP80","sublead_pho_mvaID_WP90","sublead_pho_mvaID_WP80",
#             "lead_pho_mvaID","sublead_pho_mvaID","max_gamma_MVA_ID",
#             "preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband",
#             "idmva_sideband","idmva_presel",
#             "DeltaR_j1g1","DeltaR_j2g1","DeltaR_j1g2","DeltaR_j2g2",
#             "signal","isdata", "isdd",
#         ]
#         out_events = ak.zip({k: cms_events[k] for k in keys_to_copy} | {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]}, depth_limit=1)

#         # wc = ak.to_numpy(out_events["weight_central"])
#         # wc = np.where(np.isfinite(wc) & (wc != 0.0), wc, 1.0)
#         # base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_) / wc
#         # base_w = np.where(np.isfinite(base_w), base_w, 0.0)
#         # for r in ["preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband","idmva_sideband","idmva_presel"]:
#         #     out_events = ak.with_field(out_events, base_w, "weight_"+r)
#         # ---------------- Build event weights ----------------
#         if isdata:
#             # Unit weight for real data
#             base_w = np.ones(len(tree_), dtype="f8")

#         elif isdd:
#             # DD template: read per-event weight directly
#             try:
#                 dd_wname = _get_dd_weight_col(tree_.fields)
#                 dd_w = ak.to_numpy(tree_[dd_wname])
#             except Exception:
#                 dd_wname = _get_dd_weight_col(df.columns)
#                 dd_w = df[dd_wname].to_numpy()
#             base_w = np.where(np.isfinite(dd_w), dd_w, 0.0)

#         else:
#             # MC: σ×L normalization
#             wc = ak.to_numpy(out_events["weight_central"])
#             wc = np.where(np.isfinite(wc) & (wc != 0.0), wc, 1.0)
#             base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_) / wc
#             base_w = np.where(np.isfinite(base_w), base_w, 0.0)

#         # Attach per-region weights
#         for r in ["preselection","selection","srbbgg","srbbggMET",
#                 "crbbantigg","crantibbgg","crantibbantigg",
#                 "sideband","idmva_sideband","idmva_presel"]:
#             out_events = ak.with_field(out_events, base_w, "weight_"+r)


#         PROC_ACC.setdefault(sample_name_norm, []).append(ak_to_numpy_dict(out_events))

#         for ireg in regions:
#             thisregion = out_events[out_events[ireg] == True]
#             thisregion_ = thisregion[~(ak.is_none(thisregion))]
#             weight_ = "weight_" + ireg

#             for ivar in variables_common[ireg]:
#                 hist_name_ = f"{vardict[ivar]}"
#                 vals = ak.to_numpy(thisregion_[ivar])
#                 wts  = ak.to_numpy(thisregion_[weight_])
#                 if wts is not None:
#                     wts = np.where(np.isfinite(wts), wts, 0.0)
#                 h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])

#                 key = (sample_name_norm, ireg, hist_name_)
#                 if key not in HIST_CACHE:
#                     acc = h.Clone(f"{hist_name_}__acc")
#                     acc.Reset()
#                     acc.SetDirectory(0)
#                     HIST_CACHE[key] = acc
#                 HIST_CACHE[key].Add(h)
#                 del h

#             tree_data_ = ak_to_numpy_dict(thisregion_)
#             TREE_ACC.setdefault((sample_name_norm, ireg), []).append(tree_data_)

# def ensure_dir(upfile, path):
#     """Create nested directories explicitly for Uproot writing."""
#     curr = upfile
#     if not path:
#         return curr
#     parts = [p for p in path.split("/") if p]
#     for p in parts:
#         # mkdir returns the subdirectory; if it exists, __getitem__ returns it
#         curr = curr.mkdir(p) if p not in curr.keys() else curr[p]
#     return curr

# def write_tree_chunked(upfile, full_path, merged, step=200_000):
#     """
#     Create directories explicitly, create a tree with a *simple name* (no slashes),
#     and stream data in chunks. `merged` must be sanitized.
#     """
#     if not merged:
#         return

#     # Split "sample/region" into directory + short tree name
#     parts = [p for p in full_path.split("/") if p]
#     treename = parts[-1]
#     dirpath  = "/".join(parts[:-1])

#     # Ensure the directory exists
#     wdir = ensure_dir(upfile, dirpath)

#     # Enforce 1D, consistent lengths, and map to explicit string types
#     first_key = next(iter(merged))
#     n = len(merged[first_key])
#     for k, v in merged.items():
#         a = np.asarray(v)
#         if a.ndim != 1:
#             raise ValueError(f"Branch '{k}' is not 1D (shape={a.shape}).")
#         if len(a) != n:
#             raise ValueError(f"Branch length mismatch: '{k}' has {len(a)} vs {n}.")

#     # Use explicit ROOT-friendly type strings (avoid dtype inference pitfalls)
#     def _branch_type(a):
#         a = np.asarray(a)
#         if a.dtype == np.bool_:
#             return "int8"
#         if a.dtype.kind in ("i", "u"):
#             return "int64"
#         if a.dtype.kind == "f":
#             return "float64"
#         raise TypeError(f"Unsupported dtype for branch: {a.dtype}")

#     types = {k: _branch_type(v) for k, v in merged.items()}

#     # Create an empty tree with a *short name*, no slashes
#     tree = wdir.mktree(treename, types)

#     # Stream the data
#     step = min(step, n if n else step)
#     for start in range(0, n, step):
#         stop  = min(start + step, n)
#         piece = {k: v[start:stop] for k, v in merged.items()}
#         tree.extend(piece)



# # ---------------- Entry point ----------------
# def main():
#     ap = argparse.ArgumentParser(description="hhbbgg analyzer (parquet) with multi-era support + per-sample merge")
#     ap.add_argument("-i","--inFile", action="append",
#                     help="Single parquet file or a directory. Can be given multiple times to merge across folders/eras.")
#     ap.add_argument("--year", required=True, help="e.g. 2022 or 2023")
#     ap.add_argument("--era",  required=True, help="e.g. PreEE, PostEE, All")
#     ap.add_argument("--tag", default=None, help="If multiple -i are given, outputs go to outputfiles/merged/<tag>")
#     args = ap.parse_args()

#     cfg = RunConfig(args.year, args.era)

#     in_paths = []
#     if args.inFile:
#         for ip in args.inFile:
#             in_paths.append(Path(ip).resolve())
#     else:
#         in_paths.append(cfg.raw_path)

#     # Choosing output directory
#     if len(in_paths) > 1:
#         merged_root = cfg.outputs_root / "merged"
#         merged_name = args.tag or f"{cfg.year}_{cfg.era}"
#         out_dir = merged_root / merged_name
#     else:
#         out_dir = cfg.outputs_path
#     os.makedirs(out_dir, exist_ok=True)
    
#     # Discover parquet files in all input paths
#     inputfiles = []
#     for path in in_paths:
#         if path.is_file():
#             if str(path).lower().endswith(".parquet"):
#                 inputfiles.append(str(path))
#             else:
#                 print(f"[WARN] Non-parquet file skipped: {path}")
#         else:
#             inputfiles.extend([str(p) for p in sorted(path.glob("*.parquet"))])

#     if not inputfiles:
#         raise FileNotFoundError(f"No .parquet files found in: {', '.join(str(p) for p in in_paths)}")

#     print(f"[INFO] Will process {len(inputfiles)} parquet file(s).")

#     xsec_lumi_cache = {}
#     for infile_ in inputfiles:
#         process_parquet_file(infile_, cfg.year, cfg.era, xsec_lumi_cache)
        
#     hist_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-histograms.root")
#     tree_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-trees.root")

#     hist_tfile = ROOT.TFile(hist_file_path, "RECREATE")
#     tree_upfile = uproot.recreate(tree_file_path)
#     out_files = {"hist": hist_tfile, "tree": tree_upfile}

#     print("[INFO] Writing accumulated histograms...")
#     for (sample, region, varname), h in HIST_CACHE.items():
#         dir_path = f"{sample}/{region}"
#         ensure_dir_in_tfile(out_files["hist"], dir_path).cd()
#         h_clone = h.Clone(varname)
#         h_clone.SetDirectory(ROOT.gDirectory)
#         h_clone.Write()
#         del h_clone

#     print("[INFO] Writing accumulated trees...")
#     for (sample, region), chunks in TREE_ACC.items():
#         merged = concat_field_dicts(chunks)
#         merged = sanitize_for_uproot(merged)
#         # out_files["tree"][f"{sample}/{region}"] = merged
#         write_tree_chunked(out_files["tree"], f"{sample}/{region}", merged, step=100_000)

#     for sample, chunks in PROC_ACC.items():
#         merged = concat_field_dicts(chunks)
#         merged = sanitize_for_uproot(merged)
#         # out_files["tree"][f"{sample}/processed_events"] = merged
#         write_tree_chunked(out_files["tree"], f"{sample}/processed_events", merged, step=100_000)

#     out_files["tree"].close()
#     out_files["hist"].Write()
#     out_files["hist"].Close()
#     print(f"[OK] Wrote trees to:      {tree_file_path}")
#     print(f"[OK] Wrote histograms to: {hist_file_path}")
    

# if __name__ == "__main__":
#     main()
    
    
# ## To Do: we need to work on the kiling part


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import argparse
from pathlib import Path

import numpy as np
import uproot
import awkward as ak
import pyarrow.parquet as pq
import pyarrow

from config.utils import lVector
from normalisation import getXsec, getLumi
from config.config import RunConfig

#time
import time
start = time.time()  # Start time here

# ---------------- PyROOT ONLY for histograms (separate file) ----------------
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False)

# ---------------- Helpers ----------------
def _ensure_1d(a):
    a = np.asarray(a)
    return a.ravel()

def make_th1_pyroot(values, weights, name, title, binning):
    v  = _ensure_1d(values)
    w  = None if weights is None else _ensure_1d(weights)

    if w is not None:
        mask = np.isfinite(v) & np.isfinite(w)
        v = v[mask]; w = w[mask]
    else:
        mask = np.isfinite(v)
        v = v[mask]

    v2 = v.copy()

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
        for i in range(1, e.size):
            if e[i] <= e[i-1] - 1e-15:
                shift = 2*np.pi * np.ceil((e[i-1] - e[i] + 1e-15)/(2*np.pi))
                e[i:] = e[i:] + shift
        e0 = e[0]; two_pi = 2*np.pi
        vals_out = vals.copy()
        fm = np.isfinite(vals_out)
        vals_out[ fm ] = (vals_out[ fm ] - e0) % two_pi + e0
        return e, vals_out

    if isinstance(binning, np.ndarray) or (
        isinstance(binning, (list, tuple)) and not (
            len(binning) == 3 and all(np.isscalar(x) for x in binning)
        )
    ):
        edges_np = np.asarray(binning, dtype="f8").ravel()
        edges_np = edges_np[np.isfinite(edges_np)]
        if edges_np.size < 2:
            raise ValueError(f"[{name}] Variable bin edges must have length >= 2, got: {edges_np}")

        if not np.all(np.diff(edges_np) > 0):
            if _is_angular_name(name) or _maybe_angle_edges(edges_np):
                edges_np, v2 = _unwrap_edges_and_values(edges_np, v2)
            else:
                e_sorted_unique = np.unique(edges_np)
                if e_sorted_unique.size < 2 or not np.all(np.diff(e_sorted_unique) > 0):
                    raise ValueError(f"[{name}] Invalid variable bin edges (not strictly increasing).")
                print(f"[WARN] {name}: edges not strictly increasing; using sorted unique edges.")
                edges_np = e_sorted_unique

        nb = len(edges_np) - 1
        h = ROOT.TH1D(name, title, int(nb), edges_np)
    else:
        nb, lo, hi = binning
        nb = int(nb); lo = float(lo); hi = float(hi)
        if not np.isfinite([lo, hi]).all() or hi <= lo or nb <= 0:
            raise ValueError(f"[{name}] Invalid (nb, lo, hi): {binning}")
        h = ROOT.TH1D(name, title, nb, lo, hi)
        edges_np = np.linspace(lo, hi, nb + 1, dtype="f8")

    if v2.dtype == np.bool_:
        v2 = v2.astype("f8")
    if w is not None and w.dtype == np.bool_:
        w = w.astype("f8")

    counts, _ = np.histogram(v2, bins=edges_np, weights=w)
    if w is None:
        sumw2 = counts.astype("f8")
    else:
        sumw2, _ = np.histogram(v2, bins=edges_np, weights=w * w)

    h.Sumw2()
    for i in range(1, h.GetNbinsX() + 1):
        c  = float(counts[i - 1])
        e2 = float(sumw2[i - 1])
        h.SetBinContent(i, c)
        h.SetBinError(i, float(np.sqrt(e2) if e2 >= 0 else 0.0))

    h.SetDirectory(0)
    return h


def detect_year_era_from_name(path: str):
    name = os.path.basename(path).lower()
    year = "2022" if "2022" in name else ("2023" if "2023" in name else None)
    era = None
    if year == "2022":
        if "preee" in name:  era = "PreEE"
        if "postee" in name: era = "PostEE"
    elif year == "2023":
        if "prebpix" in name:  era = "preBPix"
        if "postbpix" in name: era = "postBPix"
    return year, era


def ensure_dir_in_tfile(tfile, path):
    curr = tfile
    if not path:
        return curr
    for part in path.split('/'):
        d = curr.GetDirectory(part)
        curr = d if d else curr.mkdir(part)
    return curr

def normalize_sample_name(name: str) -> str:
    base = os.path.basename(name)
    base = re.sub(r"\.(parquet|root)$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"(_part\d+|_chunk\d+|_\d+of\d+)$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"[_-]?(2022|2023)(PreEE|PostEE|All|preBPix|postBPix)?", "", base, flags=re.IGNORECASE)
    return base

def ak_to_numpy_dict(arr: ak.Array) -> dict:
    out = {}
    for key in arr.fields:
        filled = ak.fill_none(arr[key], -9999)
        np_arr = ak.to_numpy(filled)
        if np.issubdtype(np_arr.dtype, np.integer):
            np_arr = np.nan_to_num(np_arr.astype("int64"), nan=-9999, posinf=999999999, neginf=-999999999)
        else:
            np_arr = np.nan_to_num(np_arr, nan=-9999, posinf=999999999, neginf=-999999999)
        out[key] = np_arr
    return out

def sanitize_for_uproot(d: dict) -> dict:
    """
    Make arrays uproot-safe (explicit types, finite values).
    """
    out = {}
    for k, v in d.items():
        a = np.asarray(v)
        if a.dtype == np.bool_:
            a = a.astype(np.int8, copy=False)
        elif a.dtype.kind in ("u", "i"):
            a = a.astype(np.int64, copy=False)
        elif a.dtype.kind == "f":
            a = a.astype(np.float64, copy=False)
        elif a.dtype.kind == "O":
            raise TypeError(f"Branch '{k}' has object dtype; not supported in ROOT trees.")
        if a.dtype.kind in ("i", "u"):
            a = np.nan_to_num(a, nan=-9999, posinf=999999999, neginf=-999999999)
        else:
            a = np.nan_to_num(a, nan=-9999.0, posinf=9.999e306, neginf=-9.999e306)
        out[k] = a
    return out

# ---------------- Global caches/handles ----------------
HIST_CACHE   = {}   # (sample, region, varname) -> TH1D
TREE_HANDLES = {}   # (sample, region) -> uproot Tree handle (created once, extended per batch)
PROC_TREE    = {}   # sample -> uproot Tree handle for processed_events

# ---------------- Utils ----------------
def is_signal_from_name(name: str) -> bool:
    s = name
    return any(x in s for x in [
        "GluGluToHH", "NMSSM"
    ])

def is_dd_template(path: str) -> bool:
    b = os.path.basename(path).lower()
    return any(k in b for k in (
        "ddqcdgjet_rescaled",
        "ggjets_low_rescaled",
        "ggjets_high_rescaled",
        "ddqcdgjet",
    ))

DD_WEIGHT_COLUMNS = ("weight", "evt_weight", "w", "fake_weight")

def _get_dd_weight_col(all_columns) -> str:
    cols = set(map(str, all_columns))
    for c in DD_WEIGHT_COLUMNS:
        if c in cols:
            return c
    raise KeyError(
        "No DD weight column found in DD template. "
        f"Tried: {', '.join(DD_WEIGHT_COLUMNS)}; available: {sorted(cols)}"
    )

def _ensure_tree(upfile, treedir, treename, first_piece):
    """
    Ensure directory exists inside the uproot file and create a tree with explicit types.
    `treedir` like 'Sample' (no slashes in `treename`).
    """
    curr = upfile
    if treedir:
        for part in [p for p in treedir.split("/") if p]:
            curr = curr.mkdir(part) if part not in curr.keys() else curr[part]

    def _btype(a):
        a = np.asarray(a)
        if a.dtype == np.bool_:        return "int8"
        if a.dtype.kind in ("i", "u"): return "int64"
        if a.dtype.kind == "f":        return "float64"
        raise TypeError(f"Unsupported dtype for branch: {a.dtype}")

    types = {k: _btype(v) for k, v in first_piece.items()}
    return curr.mktree(treename, types)

# ---------------- Core processing ----------------
def process_parquet_file(inputfile, cli_year, cli_era, xsec_lumi_cache=None, out_files=None):
    if out_files is None:
        raise RuntimeError("out_files must be provided to stream trees.")
    print(f"[INFO] Processing Parquet file: {inputfile}")

    required_columns = [
        "run",
        "lumi",
        "event",
        # puppi variable
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
        "lead_pt",
        "lead_eta",
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
        "Res_lead_bjet_PNetRegPtRawRes",     # Adding particle net regressed varaible
        "Res_sublead_bjet_PNetRegPtRawRes",   # Adding particle net regressed varaible
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
        #pDNN Score
        "pDNN_score",
    ]

    parquet_file = pq.ParquetFile(inputfile)

    base = os.path.basename(inputfile)
    sample_name_raw = base.replace(".parquet", "").replace(".root", "")
    sample_name_norm = normalize_sample_name(sample_name_raw)

    isdata = "Data" in base
    sigflag = is_signal_from_name(base)
    isdd   = is_dd_template(base)

    det_year, det_era = detect_year_era_from_name(inputfile)
    use_year = det_year or str(cli_year)
    use_era  = det_era  or str(cli_era)

    if xsec_lumi_cache is None:
        xsec_lumi_cache = {}
    if inputfile not in xsec_lumi_cache:
        if isdata or isdd:
            xsec_lumi_cache[inputfile] = (1.0, 1.0)
        else:
            xsec_lumi_cache[inputfile] = (
                float(getXsec(inputfile)),
                float(getLumi(use_year, use_era)) * 1000.0,  # pb^-1
            )
    xsec_, lumi_ = xsec_lumi_cache[inputfile]
    print(f"[NORM] sample={os.path.basename(inputfile)} xsec={xsec_} pb, "
          f"lumi={lumi_/1000.0:.3f} fb^-1 ({use_year} {use_era}) "
          f"[flags: data={isdata} dd={isdd}]")

    # region utils & plotting config
    from regions import (
        get_mask_preselection, get_mask_selection,
        get_mask_srbbgg, get_mask_srbbggMET,
        get_mask_crantibbgg, get_mask_crbbantigg, get_mask_crantibbantigg,
        get_mask_sideband, get_mask_idmva_presel, get_mask_idmva_sideband,
    )
    from variables import vardict, regions, variables_common
    from binning import binning

    for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
        print(f"[INFO] Batch rows: {batch.num_rows}")
        tree_ = ak.from_arrow(batch)

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
                "lead_bjet_PNetRegPtRawRes": tree_["Res_lead_bjet_PNetRegPtRawRes"],    # Adding particle net regressed varaible 
                "sublead_bjet_PNetRegPtRawRes":tree_["Res_sublead_bjet_PNetRegPtRawRes"], # Adding particle net regressed varaible
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
                "pDNN_score":tree_["pDNN_score"],
            },
            depth_limit=1,
        )

        n_entries = len(tree_)
        cms_events["signal"] = ak.Array(np.full(n_entries, 1 if sigflag else 0, dtype=np.int8))
        cms_events["isdata"] = ak.Array(np.full(n_entries, 1 if isdata else 0, dtype=np.int8))
        cms_events["isdd"]   = ak.Array(np.full(n_entries, 1 if isdd   else 0, dtype=np.int8))

        # 4-vectors and derived
        dibjet_ = lVector(
            cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],
            cms_events["sublead_bjet_pt"], cms_events["sublead_bjet_eta"], cms_events["sublead_bjet_phi"],
            cms_events["lead_bjet_mass"], cms_events["sublead_bjet_mass"],
        )
        diphoton_ = lVector(
            cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],
            cms_events["sublead_pho_pt"], cms_events["sublead_pho_eta"], cms_events["sublead_pho_phi"],
        )
        cms_events["dibjet_mass"]   = dibjet_.mass
        cms_events["dibjet_pt"]     = dibjet_.pt
        cms_events["dibjet_eta"]    = dibjet_.eta
        cms_events["dibjet_phi"]    = dibjet_.phi
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"]   = diphoton_.pt
        cms_events["diphoton_eta"]  = diphoton_.eta
        cms_events["diphoton_phi"]  = diphoton_.phi

        cms_events["lead_pt_over_diphoton_mass"]    = cms_events["lead_pho_pt"]    / cms_events["diphoton_mass"]
        cms_events["sublead_pt_over_diphoton_mass"] = cms_events["sublead_pho_pt"] / cms_events["diphoton_mass"]
        cms_events["lead_pt_over_dibjet_mass"]      = cms_events["lead_bjet_pt"]   / cms_events["dibjet_mass"]
        cms_events["sublead_pt_over_dibjet_mass"]   = cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
        cms_events["diphoton_bbgg_mass"] = cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
        cms_events["dibjet_bbgg_mass"]   = cms_events["dibjet_pt"]   / cms_events["bbgg_mass"]

        cms_events["max_gamma_MVA_ID"] = ak.where(
            cms_events["lead_pho_mvaID"] > cms_events["sublead_pho_mvaID"],
            cms_events["lead_pho_mvaID"], cms_events["sublead_pho_mvaID"]
        )

        # region flags
        from regions import (
            get_mask_preselection, 
            get_mask_selection,
            get_mask_srbbgg, 
            get_mask_srbbggMET,
            get_mask_crantibbgg,
            get_mask_crbbantigg, 
            get_mask_crantibbantigg,
            get_mask_sideband,
            get_mask_idmva_presel,
            get_mask_idmva_sideband,
        )
        from variables import vardict, regions, variables_common
        from binning import binning

        cms_events["preselection"]   = get_mask_preselection(cms_events)
        cms_events["selection"]      = get_mask_selection(cms_events)
        cms_events["srbbgg"]         = get_mask_srbbgg(cms_events)
        cms_events["srbbggMET"]      = get_mask_srbbggMET(cms_events)
        cms_events["crbbantigg"]     = get_mask_crbbantigg(cms_events)
        cms_events["crantibbgg"]     = get_mask_crantibbgg(cms_events)
        cms_events["crantibbantigg"] = get_mask_crantibbantigg(cms_events)
        cms_events["sideband"]       = get_mask_sideband(cms_events)
        cms_events["idmva_presel"]   = get_mask_idmva_presel(cms_events)
        cms_events["idmva_sideband"] = get_mask_idmva_sideband(cms_events)

        # build out_events record with all needed fields
        keys_to_copy = [
            "puppiMET_pt","puppiMET_phi","puppiMET_phiJERDown","puppiMET_phiJERUp",
            "puppiMET_phiJESDown","puppiMET_phiJESUp","puppiMET_phiUnclusteredDown","puppiMET_phiUnclusteredUp",
            "puppiMET_ptJERDown","puppiMET_ptJERUp","puppiMET_ptJESDown","puppiMET_ptJESUp",
            "puppiMET_ptUnclusteredDown","puppiMET_ptUnclusteredUp","puppiMET_sumEt",
            "lead_pho_pt","lead_pho_eta","lead_pho_phi",
            "sublead_pho_pt","sublead_pho_eta","sublead_pho_phi",
            "lead_bjet_pt","lead_bjet_eta","lead_bjet_phi",
            "sublead_bjet_pt","sublead_bjet_eta","sublead_bjet_phi",
            "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta","bbgg_phi",
            "DeltaPhi_j1MET","DeltaPhi_j2MET","Res_chi_t0","Res_chi_t1",
            "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId","n_jets",
            "weight_central",
            "dibjet_eta","dibjet_phi","diphoton_eta","diphoton_phi",
            "lead_bjet_PNetB","sublead_bjet_PNetB","lead_bjet_PNetRegPtRawRes","sublead_bjet_PNetRegPtRawRes",
            "pholead_PtOverM","phosublead_PtOverM","FirstJet_PtOverM","SecondJet_PtOverM",
            "CosThetaStar_CS","CosThetaStar_jj","CosThetaStar_gg","DeltaR_jg_min",
            "lead_pt_over_diphoton_mass","sublead_pt_over_diphoton_mass",
            "lead_pt_over_dibjet_mass","sublead_pt_over_dibjet_mass",
            "diphoton_bbgg_mass","dibjet_bbgg_mass",
            "lead_pho_mvaID_WP90","lead_pho_mvaID_WP80","sublead_pho_mvaID_WP90","sublead_pho_mvaID_WP80",
            "lead_pho_mvaID","sublead_pho_mvaID","max_gamma_MVA_ID",
            "preselection","selection","srbbgg","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband",
            "idmva_sideband","idmva_presel",
            "DeltaR_j1g1","DeltaR_j2g1","DeltaR_j1g2","DeltaR_j2g2",
            "signal","isdata","isdd",
            "pDNN_score",
        ]
        out_events = ak.zip(
            {k: cms_events[k] for k in keys_to_copy} |
            {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]},
            depth_limit=1
        )

        # event weights
        if isdata:
            base_w = np.ones(len(tree_), dtype="f8")
        elif isdd:
            dd_wname = _get_dd_weight_col(tree_.fields)
            dd_w = ak.to_numpy(tree_[dd_wname])
            base_w = np.where(np.isfinite(dd_w), dd_w, 0.0)
        else:
            wc = ak.to_numpy(out_events["weight_central"])
            wc = np.where(np.isfinite(wc) & (wc != 0.0), wc, 1.0)
            # base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_) / wc 
            base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_)
            base_w = np.where(np.isfinite(base_w), base_w, 0.0)

        # attach per-region weights
        for r in ["preselection","selection","srbbgg","srbbggMET",
                  "crbbantigg","crantibbgg","crantibbantigg",
                  "sideband","idmva_sideband","idmva_presel"]:
            out_events = ak.with_field(out_events, base_w, "weight_"+r)

        # --- stream processed_events (per-sample) ---
        proc_piece = ak_to_numpy_dict(out_events)
        proc_piece = sanitize_for_uproot(proc_piece)
        if sample_name_norm not in PROC_TREE:
            PROC_TREE[sample_name_norm] = _ensure_tree(
                out_files["tree"],
                treedir   = f"{sample_name_norm}",
                treename  = "processed_events",
                first_piece = proc_piece,
            )
        PROC_TREE[sample_name_norm].extend(proc_piece)

        # --- per-region: histograms + trees (streamed) ---
        for ireg in regions:
            thisregion = out_events[out_events[ireg] == True]
            thisregion = thisregion[~(ak.is_none(thisregion))]

            weight_ = "weight_" + ireg

            # histograms
            for ivar in variables_common[ireg]:
                hist_name_ = f"{vardict[ivar]}"
                vals = ak.to_numpy(thisregion[ivar])
                wts  = ak.to_numpy(thisregion[weight_])
                if wts is not None:
                    wts = np.where(np.isfinite(wts), wts, 0.0)
                h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])

                key = (sample_name_norm, ireg, hist_name_)
                if key not in HIST_CACHE:
                    acc = h.Clone(f"{hist_name_}__acc")
                    acc.Reset()
                    acc.SetDirectory(0)
                    HIST_CACHE[key] = acc
                HIST_CACHE[key].Add(h)
                del h

            # regional trees (stream)
            tree_piece = ak_to_numpy_dict(thisregion)
            tree_piece = sanitize_for_uproot(tree_piece)
            key = (sample_name_norm, ireg)
            if key not in TREE_HANDLES:
                TREE_HANDLES[key] = _ensure_tree(
                    out_files["tree"],
                    treedir   = f"{sample_name_norm}",
                    treename  = ireg,
                    first_piece = tree_piece,
                )
            TREE_HANDLES[key].extend(tree_piece)

        # free batch-scope arrays
        del tree_, cms_events, out_events, proc_piece, tree_piece

# ---------------- Entry point ----------------
def main():
    ap = argparse.ArgumentParser(description="hhbbgg analyzer (parquet) with multi-era support + per-sample merge")
    ap.add_argument("-i","--inFile", action="append",
                    help="Single parquet file or a directory. Can be given multiple times to merge across folders/eras.")
    ap.add_argument("--year", required=True, help="e.g. 2022 or 2023")
    ap.add_argument("--era",  required=True, help="e.g. PreEE, PostEE, All")
    ap.add_argument("--tag", default=None, help="If multiple -i are given, outputs go to outputfiles/merged/<tag>")
    args = ap.parse_args()

    cfg = RunConfig(args.year, args.era)

    # discover inputs
    in_paths = []
    if args.inFile:
        for ip in args.inFile:
            in_paths.append(Path(ip).resolve())
    else:
        in_paths.append(cfg.raw_path)

    if len(in_paths) > 1:
        merged_root = cfg.outputs_root / "merged"
        merged_name = args.tag or f"{cfg.year}_{cfg.era}"
        out_dir = merged_root / merged_name
    else:
        out_dir = cfg.outputs_path
    os.makedirs(out_dir, exist_ok=True)

    inputfiles = []
    for path in in_paths:
        if path.is_file():
            if str(path).lower().endswith(".parquet"):
                inputfiles.append(str(path))
            else:
                print(f"[WARN] Non-parquet file skipped: {path}")
        else:
            inputfiles.extend([str(p) for p in sorted(path.glob("*.parquet"))])

    if not inputfiles:
        raise FileNotFoundError(f"No .parquet files found in: {', '.join(str(p) for p in in_paths)}")

    print(f"[INFO] Will process {len(inputfiles)} parquet file(s).")

    # open outputs
    hist_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-histograms.root")
    tree_file_path = os.path.join(out_dir, "hhbbgg_analyzer-v2-trees.root")
    hist_tfile = ROOT.TFile(hist_file_path, "RECREATE")
    tree_upfile = uproot.recreate(tree_file_path)
    out_files = {"hist": hist_tfile, "tree": tree_upfile}

    # process files (streaming trees per batch)
    xsec_lumi_cache = {}
    for infile_ in inputfiles:
        process_parquet_file(infile_, cfg.year, cfg.era, xsec_lumi_cache, out_files)

    # write accumulated histograms
    print("[INFO] Writing accumulated histograms...")
    for (sample, region, varname), h in HIST_CACHE.items():
        dir_path = f"{sample}/{region}"
        ensure_dir_in_tfile(out_files["hist"], dir_path).cd()
        h_clone = h.Clone(varname)
        h_clone.SetDirectory(ROOT.gDirectory)
        h_clone.Write()
        del h_clone

    # close outputs once
    out_files["tree"].close()
    out_files["hist"].Write()
    out_files["hist"].Close()
    print(f"[OK] Wrote trees to:      {tree_file_path}")
    print(f"[OK] Wrote histograms to: {hist_file_path}")

if __name__ == "__main__":
    main()


end = time.time()
print(f"Execution time: {end - start:.4f} seconds")
