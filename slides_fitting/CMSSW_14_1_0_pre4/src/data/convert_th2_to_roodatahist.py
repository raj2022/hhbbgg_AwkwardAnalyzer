#!/usr/bin/env python3
import ROOT, sys, os
ROOT.gROOT.SetBatch(True)

in_root = "data/data_obs_mass1000.root"
out_root = "data/data_obs_mass1000_rdh.root"   # output file with RooDataHists
hist_names = ["hist_data_ch0", "hist_data_ch1"]  # extend if needed

# Set these to the exact RooRealVar names and ranges used in your workspaces
mgg_name, mgg_lo, mgg_hi = "mgg", 115.0, 135.0
mjj_name, mjj_lo, mjj_hi = "mjj", 60.0, 200.0

# open input
f_in = ROOT.TFile.Open(in_root, "READ")
if not f_in or f_in.IsZombie():
    raise RuntimeError("Could not open input file " + in_root)

# create output file (RECREATE)
os.makedirs(os.path.dirname(out_root) or ".", exist_ok=True)
f_out = ROOT.TFile.Open(out_root, "RECREATE")
if not f_out or f_out.IsZombie():
    raise RuntimeError("Could not open output file " + out_root)

# Define RooRealVars with same names/ranges as your workspaces
mgg = ROOT.RooRealVar(mgg_name, mgg_name, mgg_lo, mgg_hi)
mjj = ROOT.RooRealVar(mjj_name, mjj_name, mjj_lo, mjj_hi)

for hname in hist_names:
    h = f_in.Get(hname)
    if not h:
        print(f"[WARN] {hname} not found in {in_root}. Skipping.")
        continue
    # verify it's a 2D histogram
    if not h.InheritsFrom("TH2"):
        print(f"[WARN] {hname} is not TH2 (class {h.ClassName()}). Skipping.")
        continue

    # IMPORTANT: Clone the histogram so RooDataHist doesn't take ownership of original TFile object
    h_clone = h.Clone(f"{hname}_clone")
    # Create RooDataHist from TH2
    arglist = ROOT.RooArgList(mgg, mjj)
    rd = ROOT.RooDataHist(hname, hname, arglist, h_clone)

    # write RooDataHist to output file
    f_out.cd()
    rd.Write(hname)
    print(f"[OK] Wrote RooDataHist '{hname}' with integral {rd.sumEntries()} to {out_root}")

f_out.Close()
f_in.Close()
print("Done.")
