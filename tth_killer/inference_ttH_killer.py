#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inference_tth_killer.py

Attaches a `ttH_killer_score` branch to every ROOT file in a sample folder,
using the trained ttH-killer DNN (tth_killer_v2.py / best_tth_killer.pt +
scaler_tth.pkl). Mirrors inference_PDnn.py's interface and in-place-attach
behavior: run once per sample folder, after pDNN scoring, so that both
`pDNN_score` and `ttH_killer_score` end up in the same trees before the
analyzer/categorization steps.

Usage:
    python inference_tth_killer.py -i /path/to/your/folder

Assumes each ROOT file has the same directory/tree layout as the training
and categorization scripts: TREE_NAME="selection" inside per-sample
directories. Files are updated in place (write to a temp file, then
atomically replace).
"""

import argparse, os, glob, pickle, tempfile
import numpy as np
import awkward as ak
import uproot
import torch
import torch.nn as nn

TREE_NAME = "selection"

# Must match the feature list used in tth_killer_v2.py training exactly —
# same order, same names, same handling of missing branches.
FEATURES = [
    "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
    "Res_lead_bjet_eta", "Res_sublead_bjet_eta",
    "Res_DeltaR_jg_min", "Res_DeltaR_j1g1", "Res_DeltaR_j2g2",
    "Res_CosThetaStar_gg", "Res_CosThetaStar_jj",
    "n_jets", "n_leptons", "puppiMET_pt",
    "Res_chi_t0", "Res_chi_t1",
    "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TTHKiller(nn.Module):
    """Must match the architecture in tth_killer_v2.py exactly, or the
    saved state_dict won't load."""
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).view(-1)


def load_model(model_path, scaler_path):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler not found: {scaler_path}")

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    model = TTHKiller(len(FEATURES)).to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()
    return model, scaler


def score_tree(tree, model, scaler):
    """Read FEATURES from a tree, score with the trained model, return a
    float32 numpy array of ttH-killer scores, one per event."""
    present = [f for f in FEATURES if f in tree.keys()]
    missing = [f for f in FEATURES if f not in tree.keys()]
    if missing:
        print(f"    [warn] missing features (filled with 0): {missing}")

    n = tree.num_entries
    X = np.zeros((n, len(FEATURES)), dtype="float32")

    if present:
        arr = tree.arrays(present, library="ak")
        for i, feat in enumerate(FEATURES):
            if feat in present:
                X[:, i] = np.nan_to_num(
                    ak.to_numpy(arr[feat]).astype("float32"), nan=0.0
                )

    Xs = scaler.transform(X).astype("float32")
    with torch.no_grad():
        logits = model(torch.tensor(Xs, dtype=torch.float32, device=DEVICE))
        score = torch.sigmoid(logits).cpu().numpy().astype("float32")
    return score


def _clean_branch(arr):
    """Cast to ROOT/uproot-safe dtypes; return None for unsupported
    (jagged/object/non-1D) branches so the caller can skip them."""
    a = np.asarray(arr)
    if a.dtype == np.dtype("O") or a.ndim != 1:
        return None
    if np.issubdtype(a.dtype, np.integer):
        return a.astype(np.int32)
    if np.issubdtype(a.dtype, np.floating):
        return a.astype(np.float32)
    if a.dtype == np.bool_:
        return a.astype(np.uint8)
    return a


def process_file(fpath, model, scaler):
    print(f"[scoring] {fpath}")
    with uproot.open(fpath) as fin:
        dir_bases = []
        for dkey in fin.keys():
            dbase = dkey.split(";")[0]
            obj = fin[dkey]
            if isinstance(obj, uproot.reading.ReadOnlyDirectory) and dbase not in dir_bases:
                dir_bases.append(dbase)

        fd, tmp_path = tempfile.mkstemp(suffix=".root", dir=os.path.dirname(fpath) or ".")
        os.close(fd)

        try:
            with uproot.recreate(tmp_path) as fout:
                for dbase in dir_bases:
                    try:
                        fout.mkdir(dbase)
                    except Exception:
                        pass

                for dkey in fin.keys():
                    obj = fin[dkey]
                    if not isinstance(obj, uproot.reading.ReadOnlyDirectory):
                        continue
                    dbase = dkey.split(";")[0]
                    out_dir = fout[dbase]

                    for tkey in obj.keys():
                        tbase = tkey.split(";")[0]
                        tree = obj[tkey]

                        arrays_np = tree.arrays(library="np")

                        if tbase == TREE_NAME:
                            if tree.num_entries > 0:
                                arrays_np["ttH_killer_score"] = score_tree(tree, model, scaler)
                            else:
                                arrays_np["ttH_killer_score"] = np.zeros(0, dtype="float32")

                        clean = {}
                        for k, v in arrays_np.items():
                            c = _clean_branch(v)
                            if c is None:
                                print(f"    [warn] skipping unsupported branch '{tbase}:{k}' "
                                      f"(jagged/object/non-1D)")
                                continue
                            clean[k] = c

                        if not clean:
                            continue

                        branch_types = {k: v.dtype for k, v in clean.items()}
                        out_tree = out_dir.mktree(tbase, branch_types)
                        out_tree.extend(clean)

            os.replace(tmp_path, fpath)
            print(f"    [ok] ttH_killer_score attached")
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


def main():
    ap = argparse.ArgumentParser(
        description="Attach ttH_killer_score branch to each ROOT file in a sample folder "
                    "(in place), mirroring inference_PDnn.py's interface."
    )
    ap.add_argument("-i", "--input-dir", required=True,
                     help="folder of ROOT files to score (updated in place)")
    ap.add_argument("--model", default="best_tth_killer.pt",
                     help="path to trained ttH-killer checkpoint")
    ap.add_argument("--scaler", default="scaler_tth.pkl",
                     help="path to the StandardScaler pickle from training")
    ap.add_argument("--pattern", default="*.root",
                     help="glob pattern for files to process within input-dir")
    args = ap.parse_args()

    print(f"[INFO] Using device: {DEVICE}")
    model, scaler = load_model(args.model, args.scaler)

    files = sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))
    if not files:
        print(f"[warn] no files matching '{args.pattern}' in {args.input_dir}")
        return

    for fpath in files:
        process_file(fpath, model, scaler)

    print(f"\n[INFO] Done. Scored {len(files)} file(s) in {args.input_dir}")


if __name__ == "__main__":
    main()