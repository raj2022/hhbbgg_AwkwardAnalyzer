#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inference_ttH_killer.py

Attaches a `ttH_killer_score` column to already-pDNN-scored Parquet files,
using the trained ttH-killer DNN (tth_killer_v2.py / best_tth_killer.pt +
scaler_tth.pkl). Mirrors inference_PDnn.py's conventions exactly (recursive
parquet discovery, nominal-only default, memory-safe chunked scoring) so
both networks are scored the same way, in the same pipeline position.

IMPORTANT -- pipeline ordering:
    This script expects to run on the OUTPUT of inference_PDnn.py's
    `scored/` folder (which already has pDNN_score attached), not on raw
    pre-scoring ntuples. Point -i at the scored/ directory directly, e.g.:

        python inference_ttH_killer.py \
            -i /eos/.../merged/scored/ \
            --recursive \
            --model best_tth_killer.pt --scaler scaler_tth.pkl

    By default, files are updated IN PLACE (pDNN_score and ttH_killer_score
    end up in the same file, matching Analysis_Commands.md's step 3.2),
    written via a temp file + atomic replace so a failed run never leaves a
    half-written file behind. Pass --output to instead mirror the input
    structure into a separate directory, leaving the scored/ input
    untouched.

Usage:
    python inference_ttH_killer.py -i /path/to/scored/folder --recursive
"""

from __future__ import annotations

import argparse
import gc
import os
import pickle
import re
import tempfile
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import pyarrow as pa
import pyarrow.parquet as pq

# -----------------------------------------------------------------------
# Must match tth_killer_v2.py's training feature list exactly -- same
# order, same names. Not independently re-verified here; carried over
# as-is from the previously-confirmed-correct version of this script.
# -----------------------------------------------------------------------
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
BATCH_SIZE = 16384
CHUNK_SIZE = 100_000

# Same systematic-variation/mass-point conventions as inference_PDnn.py,
# duplicated (not imported) so this script has no hard dependency on the
# pDNN working directory.
SYSTEMATIC_VARIATION_RE = re.compile(r"(_up|_down)$", re.IGNORECASE)


def classify_systematic(file_path: Path):
    """Returns 'nominal', the matched variation folder name, or None (no
    systematic-folder evidence at all -- a flat file, always kept)."""
    parts = [file_path.parent.name] + [p.name for p in file_path.parents]
    for part in parts:
        if part.lower() == "nominal":
            return "nominal"
    for part in parts:
        if SYSTEMATIC_VARIATION_RE.search(part):
            return part
    return None


# -----------------------------------------------------------------------
# Model
# -----------------------------------------------------------------------
class TTHKiller(nn.Module):
    """Must match the architecture in tth_killer_v2.py exactly, or the
    saved state_dict won't load."""
    def __init__(self, d: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).view(-1)


def load_model(model_path: str, scaler_path: str):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler not found: {scaler_path}")

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    model = TTHKiller(len(FEATURES)).to(DEVICE)
    try:
        state = torch.load(model_path, map_location=DEVICE, weights_only=True)
    except TypeError:
        # older PyTorch doesn't support weights_only
        state = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.eval()
    return model, scaler


@torch.no_grad()
def score_batch(X_scaled: np.ndarray, model: nn.Module) -> np.ndarray:
    """Score an already-scaled feature matrix in batches, returning
    sigmoid probabilities in [0, 1]."""
    out = []
    X_t = torch.from_numpy(X_scaled)
    n = X_t.shape[0]
    for i in range(0, n, BATCH_SIZE):
        xb = X_t[i:i + BATCH_SIZE].to(DEVICE, non_blocking=True)
        logits = model(xb)
        prob = torch.sigmoid(logits)
        out.append(prob.detach().cpu())
    return torch.cat(out).numpy().astype("float32") if out else np.zeros(0, dtype="float32")


# -----------------------------------------------------------------------
# Scoring
# -----------------------------------------------------------------------
def score_parquet_file(file_path: Path, out_path: Path, model, scaler, chunk_size: int = CHUNK_SIZE):
    """Memory-safe parquet scoring: read, score, write chunk-by-chunk,
    matching inference_PDnn.py's approach. Adds ttH_killer_score without
    touching any existing columns (including pDNN_score, if present)."""
    parquet_file = pq.ParquetFile(file_path)
    schema_names = set(parquet_file.schema.names)

    if "pDNN_score" not in schema_names:
        print(f"  [warn] {file_path.name}: no pDNN_score column found -- expected this file "
              f"to already be pDNN-scored (see module docstring on pipeline ordering).")

    missing_features = [f for f in FEATURES if f not in schema_names]
    if missing_features:
        print(f"  [warn] {file_path.name}: missing features (filled with 0): {missing_features}")

    writer = None
    for batch in parquet_file.iter_batches(batch_size=chunk_size):
        df = batch.to_pandas()

        X = np.zeros((len(df), len(FEATURES)), dtype="float32")
        for i, feat in enumerate(FEATURES):
            if feat in df.columns:
                X[:, i] = np.nan_to_num(df[feat].to_numpy(dtype="float32"), nan=0.0)

        X_scaled = scaler.transform(X).astype("float32")
        df["ttH_killer_score"] = score_batch(X_scaled, model)

        table = pa.Table.from_pandas(df, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(out_path, table.schema)
        writer.write_table(table)

        del df, X, X_scaled, table
        gc.collect()

    if writer is not None:
        writer.close()


def collect_parquet_files(root: Path, pattern: str, all_systematics: bool = False):
    """Recursive discovery, restricted to 'nominal' (+ flat files with no
    systematic-folder structure) unless all_systematics is set -- same
    default as inference_PDnn.py."""
    all_files = sorted(root.rglob(pattern))
    all_files = [f for f in all_files if f.is_file()]
    if all_systematics:
        return all_files

    kept, skipped = [], set()
    for fp in all_files:
        syst = classify_systematic(fp)
        if syst is None or syst == "nominal":
            kept.append(fp)
        else:
            skipped.add(syst)
    if skipped:
        print(f"[INFO] restricting to 'nominal' (pass --all-systematics to also score "
              f"{len(all_files) - len(kept)} file(s) under systematic-variation folders): "
              f"{sorted(skipped)}")
    return kept


def main():
    ap = argparse.ArgumentParser(
        description="Attach ttH_killer_score to already-pDNN-scored Parquet files, "
                    "mirroring inference_PDnn.py's conventions."
    )
    ap.add_argument("-i", "--input", required=True,
                     help="Folder of already-pDNN-scored parquet files (typically the "
                          "scored/ output of inference_PDnn.py)")
    ap.add_argument("-o", "--output", default=None,
                     help="Output folder. Default: update files IN PLACE (temp file + "
                          "atomic replace) so pDNN_score and ttH_killer_score end up in "
                          "the same file. If set, mirrors the input structure into this "
                          "directory instead, leaving the input untouched.")
    ap.add_argument("--model", default="best_tth_killer.pt", help="Trained ttH-killer checkpoint")
    ap.add_argument("--scaler", default="scaler_tth.pkl", help="StandardScaler pickle from training")
    ap.add_argument("--pattern", default="*.parquet", help="Glob pattern for input files")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--all-systematics", action="store_true",
                     help="Also score files under systematic-variation subfolders. "
                          "Default: nominal only (matching inference_PDnn.py).")
    args = ap.parse_args()

    inp_dir = Path(args.input).expanduser().resolve()
    if not inp_dir.is_dir():
        raise ValueError(f"Input is not a folder: {inp_dir}")

    print(f"[INFO] Using device: {DEVICE}")
    model, scaler = load_model(args.model, args.scaler)
    print(f"[INFO] Loaded model ({args.model}) and scaler ({args.scaler}), {len(FEATURES)} features")

    if args.recursive:
        files = collect_parquet_files(inp_dir, args.pattern, all_systematics=args.all_systematics)
    else:
        files = sorted(f for f in inp_dir.glob(args.pattern) if f.is_file())

    if not files:
        print(f"[WARN] No files matched pattern '{args.pattern}' in {inp_dir}"
              + ("" if args.recursive else " (pass --recursive to search subfolders)"))
        return

    print(f"[INFO] Found {len(files)} file(s). Scoring...")

    in_place = args.output is None
    out_root = None if in_place else Path(args.output).expanduser().resolve()
    if out_root is not None:
        out_root.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    for fp in files:
        tmp_path = None
        try:
            if in_place:
                fd, tmp_name = tempfile.mkstemp(suffix=".parquet", dir=str(fp.parent))
                os.close(fd)
                tmp_path = Path(tmp_name)
                score_parquet_file(fp, tmp_path, model, scaler)
                os.replace(tmp_path, fp)
                tmp_path = None  # successfully moved, nothing left to clean up
                out_fp = fp
            else:
                rel = fp.relative_to(inp_dir)
                out_fp = out_root / rel
                out_fp.parent.mkdir(parents=True, exist_ok=True)
                score_parquet_file(fp, out_fp, model, scaler)

            row_count = pq.ParquetFile(out_fp).metadata.num_rows
            total_rows += row_count
            print(f"  {fp.name:40s} -> {out_fp}  ({row_count} rows)")

        except Exception as e:
            print(f"  [ERROR] {fp}: {e}")
            if tmp_path is not None and tmp_path.exists():
                os.remove(tmp_path)

    print(f"[DONE] Scored {len(files)} file(s), {total_rows} total rows.")
    if in_place:
        print("[OUT ] Files updated in place (pDNN_score + ttH_killer_score together).")
    else:
        print(f"[OUT ] Output folder: {out_root}")


if __name__ == "__main__":
    main()