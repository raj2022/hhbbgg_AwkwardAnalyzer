#!/usr/bin/env python3
import os, glob, argparse
import numpy as np
import ROOT
import ctypes

def is_uniform_edges(edges, rtol=1e-8, atol=1e-12):
    # check if consecutive widths are equal (within tolerance)
    widths = np.diff(edges)
    return np.allclose(widths, widths[0], rtol=rtol, atol=atol)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default="data_npz")
    ap.add_argument("--out-root", default="data/data_obs_mass1000.root")
    ap.add_argument("--hist-prefix", default="hist_data_ch")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_root) or ".", exist_ok=True)
    fout = ROOT.TFile.Open(args.out_root, "RECREATE")
    if fout.IsZombie():
        raise RuntimeError("Could not open output root file")

    files = sorted(glob.glob(os.path.join(args.in_dir, "*.npz")))
    if not files:
        print("[WARN] no npz files found in", args.in_dir)
    for fn in files:
        data = np.load(fn)
        counts = data["counts"]      # shape: (nx, ny)
        xedges = data["xedges"].astype(float)
        yedges = data["yedges"].astype(float)
        # infer channel
        basename = os.path.basename(fn)
        ch = int(data["cat"]) if "cat" in data else int(''.join(filter(str.isdigit, basename)) or 0)

        nx = counts.shape[0]
        ny = counts.shape[1]
        name = f"{args.hist_prefix}{ch}"

        # Create TH2D: try uniform-edge constructor first
        try:
            if is_uniform_edges(xedges) and is_uniform_edges(yedges):
                xlow = float(xedges[0])
                xup  = float(xedges[-1])
                ylow = float(yedges[0])
                yup  = float(yedges[-1])
                hist = ROOT.TH2D(name, name, nx, xlow, xup, ny, ylow, yup)
            else:
                # non-uniform bins -> create ctypes arrays of doubles and pass them
                x_c = (ctypes.c_double * len(xedges))(*[float(v) for v in xedges])
                y_c = (ctypes.c_double * len(yedges))(*[float(v) for v in yedges])
                # TH2D(name,title, nbinsx, xbins_ptr, nbinsy, ybins_ptr)
                hist = ROOT.TH2D(name, name, nx, x_c, ny, y_c)
        except TypeError as e:
            # fallback: try forcing ctypes route explicitly
            x_c = (ctypes.c_double * len(xedges))(*[float(v) for v in xedges])
            y_c = (ctypes.c_double * len(yedges))(*[float(v) for v in yedges])
            hist = ROOT.TH2D(name, name, nx, x_c, ny, y_c)

        # Fill bin contents (ROOT bins start at 1)
        for i in range(nx):
            for j in range(ny):
                hist.SetBinContent(i+1, j+1, float(counts[i, j]))

        hist.GetXaxis().SetName("mgg")
        hist.GetYaxis().SetName("mjj")
        hist.Write("", ROOT.TObject.kOverwrite)
        print("Wrote", name, "sum=", counts.sum())
    fout.Close()
    print("Finished writing", args.out_root)

if __name__ == "__main__":
    main()
