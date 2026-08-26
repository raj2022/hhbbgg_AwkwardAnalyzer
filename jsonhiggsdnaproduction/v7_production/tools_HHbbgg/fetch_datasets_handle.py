#!/usr/bin/env python
"""
Handle large nanoAOD files in the DAS system.

Same input/output interface as higgs_dna/scripts/samples/fetch_datasets.py, but:
  - Parses JSON output from dasgoclient --json to get per-file nevents metadata.
  - If a file's nevents > 1.5 * threshold, splits it via split_nanoaod.py.
  - Replaces the large-file path with the resulting split-file paths in the output JSON.
  - Supports a --dry-run mode.
  - Uses native Python logging instead of HiggsDNA's logger module.

Requirements / dependencies:
  - /cvmfs/cms.cern.ch/common/dasgoclient  (for DAS queries)
  - split_nanoaod.py (for splitting large files; needs ROOT and numpy)
  - Valid grid proxy:  setexp  (or voms-proxy-init --voms cms)

Test example:
  python fetch_datasets_handle.py -i samples_mc_2022postEE_GluGlutoHH_kl-1p00_kt-1p00_c2-0p00.txt --dry-run

Author: tools_HHbbgg
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Native logging (replaces higgs_dna.utils.logger_utils) ────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fetch_datasets_handle")

# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

# xrootd prefixes for different regions (mirrors fetch_datasets.py)
XROOTD_PFX = {
    "Americas": "root://cmsxrootd.fnal.gov/",
    "Eurasia":  "root://xrootd-cms.infn.it/",
    "Yolo":     "root://cms-xrd-global.cern.ch/",
}

# Location of the split script and its output cache
_HERE = os.path.dirname(os.path.abspath(__file__))
SPLIT_SCRIPT = os.path.join(_HERE, "split_nanoaod.py")
SPLIT_CACHE_DIR = os.path.join(_HERE, "split_nanoaod_cache")

DEFAULT_THRESHOLD = 20_000       # split when nevents > 1.5 × this
DEFAULT_SPLIT_EVENTS = 20_000    # max events per split output file
DASGOCLIENT = "/cvmfs/cms.cern.ch/common/dasgoclient"

# Python interpreter with ROOT bindings (needed by split_nanoaod.py).
# On lxplus the system python3.9 ships with ROOT; conda envs may have their own.
_PYTHON_WITH_ROOT = "python3.9" if os.path.exists("/usr/bin/python3.9") else "python3"


# ═══════════════════════════════════════════════════════════════════════
#  Argument parsing  (same interface as fetch_datasets.py + extras)
# ═══════════════════════════════════════════════════════════════════════

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch datasets from DAS with automatic large-file splitting."
    )

    parser.add_argument(
        "-i", "--input", required=True,
        help="Input .txt file listing datasets (same format as fetch_datasets.py).",
    )
    parser.add_argument(
        "-w", "--where", default="Eurasia",
        choices=["Americas", "Eurasia", "Yolo"],
        help="Region for choosing xrootd prefix (grid mode).",
    )
    parser.add_argument(
        "-x", "--xrootd", default=None,
        help="Override xrootd prefix (e.g. 'root://cmsxrootd.fnal.gov/').",
    )
    parser.add_argument(
        "--dbs-instance", dest="instance", default="prod/global",
        choices=["prod/global", "prod/phys01", "prod/phys02", "prod/phys03"],
        help="DBS instance passed to dasgoclient.",
    )

    # ── new / handle-specific arguments ──────────────────────────────
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Query DAS and show which files would be split, but do not actually split.",
    )
    parser.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD,
        help=f"Event-count threshold (default: {DEFAULT_THRESHOLD}). "
             f"Files with nevents > 1.5 × threshold are split.",
    )
    parser.add_argument(
        "--split-events", type=int, default=DEFAULT_SPLIT_EVENTS,
        help=f"Maximum events per output split file (default: {DEFAULT_SPLIT_EVENTS}).",
    )
    parser.add_argument(
        "--no-split", action="store_true",
        help="Disable splitting entirely — behaves like the original fetch_datasets.py.",
    )
    parser.add_argument(
        "--max-files", type=int, default=None,
        help="Limit to first N files per dataset (useful for quick tests).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG-level logging.",
    )

    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════
#  Input-file reader  (same logic as fetch_datasets.read_input_file)
# ═══════════════════════════════════════════════════════════════════════

def read_input_file(input_txt: str) -> List[Tuple[str, str]]:
    """Parse the dataset definition file.

    Parameters
    ----------
    input_txt : str
        Path to a text file where each non-blank, non-comment line is
        ``<short_name>  <dataset_path_or_local_dir>``.

    Returns
    -------
    list[tuple[str, str]]
        Ordered list of (short_name, path) pairs.
    """
    fset: List[Tuple[str, str]] = []
    with open(input_txt, "r") as fp:
        for i, line in enumerate(fp, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(None, 1)
            if len(parts) != 2:
                logger.warning("Line %d in '%s' is malformed, skipping: '%s'",
                               i, input_txt, stripped)
                continue
            fset.append((parts[0], parts[1]))
    return fset


# ═══════════════════════════════════════════════════════════════════════
#  DAS query helpers
# ═══════════════════════════════════════════════════════════════════════

def query_das_files(dataset: str, dbs_instance: str) -> List[dict]:
    """Run ``dasgoclient … --json`` and return a list of parsed JSON dicts.

    Parameters
    ----------
    dataset : str
        CMS dataset path, e.g. ``/…/NANOAODSIM``.
    dbs_instance : str
        DBS instance name (``prod/global``, ``prod/phys03``, …).

    Returns
    -------
    list[dict]
        One dict per output line (each dict contains a ``"file"`` key with
        the array of file records).
    """
    private = "" if not dataset.endswith("/USER") else " instance=prod/phys03"
    cmd = (
        f"{DASGOCLIENT} "
        f"-query='instance={dbs_instance} file dataset={dataset}{private}' "
        f"--json"
    )
    logger.debug("Running dasgoclient: %s", cmd)

    for attempt in range(1, 4):
        try:
            output = subprocess.check_output(
                cmd, shell=True, universal_newlines=True, timeout=60
            )
            break
        except subprocess.TimeoutExpired:
            logger.warning("dasgoclient timeout (attempt %d/3) for '%s'", attempt, dataset)
        except subprocess.CalledProcessError as exc:
            logger.error("dasgoclient failed for '%s': %s", dataset, exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error querying '%s': %s", dataset, exc)
            return []
    else:
        logger.error("dasgoclient timed out 3 times for '%s', giving up.", dataset)
        return []

    # dasgoclient --json outputs a JSON array, one file record per line:
    #     [
    #     {...json...} ,
    #     {...json...} ,
    #     ...
    #     ]
    # We join all lines and parse as a single JSON array for robustness.
    results: List[dict] = []
    raw = output.strip()
    if not raw:
        return results
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            results = parsed
        elif isinstance(parsed, dict):
            results = [parsed]
    except json.JSONDecodeError:
        # Fallback: parse line-by-line, stripping array brackets and commas
        logger.debug("JSON array parse failed, falling back to line-by-line parsing")
        for line in raw.splitlines():
            line = line.strip()
            if not line or line in ("[", "]"):
                continue
            # Remove trailing comma (with optional whitespace before it)
            line = line.rstrip().rstrip(",").rstrip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Could not parse DAS JSON line: %s…  (%s)", line[:120], exc)
    return results


def extract_file_metadata(das_results: List[dict]) -> List[dict]:
    """Pull ``name`` and ``nevents`` from every file record in *das_results*.

    Parameters
    ----------
    das_results : list[dict]
        Raw output of :func:`query_das_files`.

    Returns
    -------
    list[dict]
        List of ``{"name": str, "nevents": int}``.
    """
    files: List[dict] = []
    for entry in das_results:
        for rec in entry.get("file", []):
            name = rec.get("name", "")
            if name:
                files.append({
                    "name": name,
                    "nevents": int(rec.get("nevents", 0)),
                })
    return files


# ═══════════════════════════════════════════════════════════════════════
#  Splitting logic
# ═══════════════════════════════════════════════════════════════════════

def _split_cache_subdir(file_path: str) -> str:
    """Build a deterministic cache subdirectory for a given xrootd file path.

    Example: ``/store/mc/…/NANOAODSIM/130X_…/50000/abc.root`` →
    ``split_nanoaod_cache/…/NANOAODSIM/130X_…/50000/abc/``
    """
    # Strip leading slash and xrootd prefix (if present) to get the LFN.
    clean = file_path
    for pfx in XROOTD_PFX.values():
        if clean.startswith(pfx):
            clean = clean[len(pfx):]
            break
    # Strip leading "/store" so we don't have an extra empty segment.
    clean = clean.lstrip("/")
    return os.path.join(SPLIT_CACHE_DIR, os.path.dirname(clean), Path(clean).stem)


def split_one_file(remote_url: str, output_dir: str, max_events: int,
                   dry_run: bool = False) -> List[str]:
    """Split a single remote nanoAOD file by shelling out to *split_nanoaod.py*.

    Parameters
    ----------
    remote_url : str
        Full xrootd URL of the file to split.
    output_dir : str
        Local directory that will receive the ``*_partN_of_M.root`` files.
    max_events : int
        Maximum events per output chunk.
    dry_run : bool
        If True, only log the action; return a placeholder path.

    Returns
    -------
    list[str]
        Absolute paths to the produced split ``.root`` files (may be empty
        on failure).
    """
    if dry_run:
        logger.info("[DRY-RUN] Would split: %s  →  %s  (max %s evt/file)",
                    remote_url, output_dir, max_events)
        return [os.path.join(output_dir, "DRY_RUN_PLACEHOLDER.root")]

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        _PYTHON_WITH_ROOT, SPLIT_SCRIPT,
        remote_url,
        output_dir,
        "-m", str(max_events),
        "--force",
    ]
    logger.info("Launching split: %s", " ".join(cmd))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    except subprocess.TimeoutExpired:
        logger.error("split_nanoaod timed out (2 h) for '%s'", remote_url)
        return []
    except Exception as exc:
        logger.error("Unexpected error running split_nanoaod on '%s': %s", remote_url, exc)
        return []

    if proc.returncode != 0:
        logger.error("split_nanoaod returned %d for '%s'. stderr: %s",
                     proc.returncode, remote_url, proc.stderr[-500:])
        return []

    # Collect produced root files.
    split_files = sorted(Path(output_dir).glob("*.root"))
    paths = [str(f.resolve()) for f in split_files]
    if not paths:
        logger.error("split_nanoaod ran successfully but produced no .root files in '%s'",
                     output_dir)
    else:
        logger.info("Split produced %d file(s) in '%s'", len(paths), output_dir)
    return paths


# ═══════════════════════════════════════════════════════════════════════
#  Per-dataset worker (called in parallel)
# ═══════════════════════════════════════════════════════════════════════

def fetch_and_handle_one(name: str, dataset: str, xrd: str, dbs_instance: str,
                          threshold: int, split_events: int, no_split: bool,
                          dry_run: bool, max_files: Optional[int] = None
                          ) -> Tuple[str, List[str], dict]:
    """Fetch file list for *one* DAS dataset and split overlarge files.

    Returns
    -------
    (name, file_paths, stats)
        *name* – short dataset name.
        *file_paths* – final list of file paths (original + split replacements).
        *stats* – summary dict with keys ``total``, ``large``, ``split``, ``kept``.
    """
    logger.info("─" * 60)
    logger.info("Dataset '%s'  →  %s", name, dataset)

    das_results = query_das_files(dataset, dbs_instance)
    if not das_results:
        logger.warning("Zero DAS results for '%s'", name)
        return name, [], {"total": 0, "large": 0, "split": 0, "kept": 0}

    file_meta = extract_file_metadata(das_results)
    if max_files is not None:
        file_meta = file_meta[:max_files]

    threshold_cut = 1.5 * threshold
    stats = {"total": len(file_meta), "large": 0, "split": 0, "kept": 0}
    final_paths: List[str] = []

    for fi in file_meta:
        fname = fi["name"]          # e.g. /store/mc/…/file.root
        nevents = fi["nevents"]
        full_url = xrd + fname

        if (not no_split) and nevents > threshold_cut:
            stats["large"] += 1
            logger.info("LARGE FILE: nevents=%d > %.0f  →  %s", nevents, threshold_cut, fname)

            out_dir = _split_cache_subdir(full_url)
            split_paths = split_one_file(full_url, out_dir, split_events, dry_run)

            if split_paths:
                final_paths.extend(split_paths)
                stats["split"] += len(split_paths)
            else:
                logger.warning("Splitting failed, keeping original file: %s", full_url)
                final_paths.append(full_url)
                stats["kept"] += 1
        else:
            final_paths.append(full_url)
            stats["kept"] += 1

    logger.info("Dataset '%s' summary: total=%d  large=%d  split_out=%d  kept=%d",
                name, stats["total"], stats["large"], stats["split"], stats["kept"])
    return name, final_paths, stats


# ═══════════════════════════════════════════════════════════════════════
#  Orchestration
# ═══════════════════════════════════════════════════════════════════════

def fetch_all_datasets(fset: List[Tuple[str, str]], xrd: str, dbs_instance: str,
                       threshold: int, split_events: int, no_split: bool,
                       dry_run: bool, max_files: Optional[int] = None
                       ) -> Dict[str, List[str]]:
    """Parallelised entry point — mirrors ``get_dataset_dict_grid``.

    Returns
    -------
    dict
        ``{short_name: [file_path, …]}`` preserving input order.
    """
    fdict: Dict[str, List[str]] = {}
    all_stats: Dict[str, dict] = {}

    with ThreadPoolExecutor() as executor:
        future_map = {}
        for sname, dset in fset:
            fut = executor.submit(
                fetch_and_handle_one,
                sname, dset, xrd, dbs_instance,
                threshold, split_events, no_split, dry_run, max_files,
            )
            future_map[fut] = sname

        for future in as_completed(future_map):
            sname = future_map[future]
            try:
                name_out, paths, stats = future.result()
                fdict[name_out] = paths
                all_stats[name_out] = stats
            except Exception as exc:
                logger.error("Unhandled error for dataset '%s': %s", sname, exc, exc_info=True)
                fdict[sname] = []

    # Preserve original input order.
    ordered: Dict[str, List[str]] = {}
    for sname, _ in fset:
        ordered[sname] = fdict.get(sname, [])

    # Print a concise overall summary.
    total_files = sum(s["total"] for s in all_stats.values())
    total_large = sum(s["large"] for s in all_stats.values())
    total_split = sum(s["split"] for s in all_stats.values())
    logger.info("═" * 60)
    logger.info("GRAND TOTAL: %d files in %d dataset(s)", total_files, len(fset))
    if not no_split:
        logger.info("  • %d file(s) above threshold  →  %d split file(s) produced",
                    total_large, total_split)
    if dry_run:
        logger.info("  (DRY RUN — no files were actually split)")

    return ordered


# ═══════════════════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    args = get_args()

    # --- logging level -------------------------------------------------
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    # --- validate input ------------------------------------------------
    if not args.input.endswith(".txt"):
        logger.error("Input file must end with '.txt', got '%s'", args.input)
        sys.exit(1)

    if not os.path.exists(args.input):
        logger.error("Input file not found: '%s'", args.input)
        sys.exit(1)

    fset = read_input_file(args.input)
    if not fset:
        logger.error("No valid (name, path) entries found in '%s'.", args.input)
        sys.exit(1)

    logger.info("Loaded %d dataset(s) from '%s'", len(fset), args.input)
    for sname, dset in fset:
        logger.info("  %s  →  %s", sname, dset)

    # --- xrootd prefix -------------------------------------------------
    xrd = XROOTD_PFX.get(args.where, "")
    if args.xrootd:
        xrd = args.xrootd
    logger.info("xrootd prefix: '%s'  |  DBS instance: %s  |  region: %s",
                xrd, args.instance, args.where)

    if args.dry_run:
        logger.info("***  DRY-RUN MODE  —  no splitting will be performed  ***")

    if args.no_split:
        logger.info("Splitting DISABLED (--no-split).")
    else:
        logger.info("Splitting ENABLED: nevents > %.0f  →  split into ≤%d evt chunks",
                    1.5 * args.threshold, args.split_events)
    if args.max_files:
        logger.info("Limiting to first %d file(s) per dataset (--max-files).", args.max_files)

    # --- fetch ---------------------------------------------------------
    t_start = time.monotonic()
    fdict = fetch_all_datasets(
        fset, xrd, args.instance,
        args.threshold, args.split_events, args.no_split,
        args.dry_run, args.max_files,
    )
    elapsed = time.monotonic() - t_start
    logger.info("Fetch+handle finished in %.1f s", elapsed)

    if not fdict or all(len(v) == 0 for v in fdict.values()):
        logger.error("No files collected — nothing to write.")
        sys.exit(1)

    # --- write output JSON (same naming convention as fetch_datasets) --
    output_json = Path(args.input).with_suffix(".json")
    try:
        with open(output_json, "w") as fp:
            json.dump(fdict, fp, indent=4)
        n_files = sum(len(v) for v in fdict.values())
        logger.info("✓  Written %d file paths across %d dataset(s) to '%s'",
                    n_files, len(fdict), output_json)
    except Exception as exc:
        logger.error("Failed to write JSON output '%s': %s", output_json, exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
