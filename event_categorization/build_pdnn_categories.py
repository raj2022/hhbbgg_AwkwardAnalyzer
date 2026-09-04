#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pdnn_categories.py

Data-driven (sideband-based) event categorization for the X -> YH -> bb-gg-gamma
resonant search, using the trained pDNN score and the alpha(score) sideband
transfer method (per B2G-24-001).

--------------------------------------------------------------------------
WHAT THIS SCRIPT DOES
--------------------------------------------------------------------------
1. Reads the merged analyzer output (hhbbgg_analyzer_lxplus_par.py's
   `<tag>/hhbbgg_analyzer-v2-trees.root`), classifying each top-level
   sample directory as signal, background MC, or data by name.
2. Builds alpha(score) = (background MC yield in SR) / (background MC
   yield in CR), a per-score-bin transfer factor, from background MC.
3. Reweights CR *data* sidebands into an SR background estimate via
   alpha(score) -- this is what makes the background estimate data-driven
   rather than purely MC-based.
4. Runs a greedy category-boundary search (`build_edges()`) that sorts
   events by score and accepts new signal-region bins one at a time,
   each accepted only if it improves summed AMS^2 significance over the
   currently-accepted bins alone (not a fixed grand total -- see that
   function's docstring for the full 6-step procedure and the bug it
   fixes relative to earlier versions).
5. Writes the resulting per-tag score thresholds to `event_categories.json`.
6. Optionally (`--write-categorized`) clones the input ROOT file with
   `cat` (category index, or -99 if uncategorized) and `region`
   (1 = signal region, 0 = control region, -1 = neither) branches added
   to every event.

--------------------------------------------------------------------------
INPUT ASSUMPTIONS
--------------------------------------------------------------------------
- `--root` points at a ROOT file with the CURRENT analyzer output layout:
  `<sample>/<systematic>/<region>` (e.g. "NMSSM_X700_Y500/nominal/selection"),
  NOT the older flat `<sample>/<region>` layout. Only ONE systematic
  (`--systematic`, default "nominal") is read/written per invocation --
  see `--systematic`'s help text for why this is a deliberate scope
  limit, not an oversight.
- Each sample's `selection` tree must carry `pDNN_score`, `diphoton_mass`,
  `weight_selection`, and `isdata` (BR_SCORE/BR_MGG/BR_WGT/BR_ISDATA below).
- Sample role (signal / background MC / data) is inferred from the
  top-level directory NAME (`is_signal_dir()`, `is_data_dir()`) -- there
  is no explicit "is this MC or data" flag read from the tree itself
  beyond the `isdata` branch, which is used for the SR/CR data-vs-MC
  split within a directory already classified as data-bearing.
- `pDNN_score` is assumed to already be a probability in [0, 1] UNLESS
  `--sigmoid-score` is passed, in which case a sigmoid is applied first
  (for a model that instead writes raw logits). Confirm which is true
  for your `pDNN_score` before trusting results either way -- passing
  this flag when the score is already a probability silently degrades
  category separation by applying sigmoid twice.
- OPTIONAL ttH-killer cut (`--tth-killer-cut`): if passed, every event
  (signal, background MC, and data alike) is required to satisfy
  ttH_killer_score < CUT before anything else -- confirmed directly from
  a validated efficiency-vs-cut study that this is the correct direction
  (lower score = less ttH-like), with Loose/Medium/Tight working points
  at cuts 0.924/0.682/0.401 (ttH efficiency 50%/20%/10%, signal efficiency
  99.7%/97.8%/94.7%). NOT applied by default (None), for backward
  compatibility with files that predate this branch -- when explicitly
  given, directories missing the ttH_killer_score branch are skipped with
  a clear warning, the same pattern already used for other required
  branches below, rather than silently proceeding without the cut.

--------------------------------------------------------------------------
OUTPUT
--------------------------------------------------------------------------
outputs/categories_alpha/  (or --outdir)
    event_categories.json          per-tag score thresholds ("combined",
                                    or "mX###_mY###" per mass point with
                                    --per-mass), plus the SR/CR window
                                    definitions used to derive them
    <input>__categorized.root      (only with --write-categorized) input
                                    file cloned with cat/region branches
                                    added, for the one --systematic
                                    requested

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
    python categorize_events.py \\
      --root outputfiles/merged/DD_2024/hhbbgg_analyzer-v2-trees.root \\
      --sr-sigma 2.0 --cr-sidebands 4 10 \\
      --nmin 50 --min-gain 0.05 --max-bins 5 \\
      --alpha-bins 60 \\
      --tth-killer-cut 0.682 \\
      --outdir outputs/categories_2024 \\
      --write-categorized --systematic nominal

--------------------------------------------------------------------------
FIXED (this pass): --write-categorized crash on per-(sample, systematic)
files whose one contained systematic isn't the one requested.
--------------------------------------------------------------------------
CONFIRMED, real, reproducible bug: for a file like
hhbbgg_analyzer-v2-trees__GluGluHtoGG__ScaleEB_Zee_down.root (this
pipeline's one-systematic-per-file convention -- the file genuinely
contains ONLY "ScaleEB_Zee_down", no "nominal" at all), the
--write-categorized loop's systematic-detection logic fell through to
treating the sample directory as flat/legacy (no systematic layer),
since "nominal" wasn't found as an immediate child via naive
`[k.split(";")[0] for k in in_dir_obj.keys()]`. That naive check is
fooled by a real, confirmed uproot behavior: a directory's .keys()
returns every NESTED descendant as a slash-joined path, not just true
immediate children -- e.g. GluGluHtoGG.keys() returns both
"ScaleEB_Zee_down;1" (the subdirectory itself, correctly caught by the
existing hasattr() guard) AND "ScaleEB_Zee_down/srbbgg;1" (which DOES
resolve to a genuine tree, so hasattr() passes it through). That
slash-joined key then got passed directly as a tree NAME into
mktree("ScaleEB_Zee_down/srbbgg", ...) in the generic "copy any other
tree as-is" fallback -- corrupting uproot's internal free-space
bookkeeping and crashing the entire run partway through with:
    RuntimeError: segment of data to release overlaps one already
    marked as free: releasing [2378, 2721) but [2684, 2721) is free
-- losing every not-yet-processed sample's categorized output.

Fixed via a new immediate_children() helper (generalizing the same
filtering collect_dirs() already does for top-level sample directories
down to this sample-subdirectory level too), plus a new explicit
"mismatched systematic, not flat -- skip this file" branch, verified
directly against a real synthetic file reproducing the exact confirmed
structure. See immediate_children()'s and the write-categorized loop's
own comments below for full detail.
"""

import argparse, json, os, re, math
from pathlib import Path
import numpy as np
import awkward as ak
import uproot

# -------------------- user defaults --------------------
SR_DEFAULT = 2.0                 # SR: |mgg-125| < SR_DEFAULT (GeV)
CR_DEFAULT = (4.0, 10.0)         # CR: 4 <= |mgg-125| < 10 (GeV)
TREE_NAME  = "srbbgg"             # tree inside each directory -- confirmed
                                   # as the analysis's actual signal region
                                   # (not "selection", a looser upstream
                                   # cut). Fixed here after discovering my
                                   # own local copy of this file had never
                                   # actually incorporated this change --
                                   # every fix shipped after it was applied
                                   # on top of a version still targeting
                                   # "selection", silently routing srbbgg
                                   # trees down the copy-as-is fallback
                                   # path (no cat/region added) instead of
                                   # the real categorization path.

BR_SCORE      = "pDNN_score"
BR_MGG        = "diphoton_mass"
# FIXED, confirmed real inconsistency: was "weight_selection", a
# leftover from before TREE_NAME (above) was corrected to "srbbgg" --
# the same class of incomplete fix TREE_NAME's own comment already
# warns happened once before. Confirmed directly from the analyzer's
# own weight-assignment code (hhbbgg_analyzer_with_systematics.py)
# that this was NOT producing a wrong number: every region's own
# "weight_"+r column is assigned from the SAME underlying array before
# region-filtering happens (`for r in [..., "srbbgg", ...]:
# ak.with_field(..., syst_w, "weight_"+r)`), so "weight_selection" and
# "weight_srbbgg" are currently byte-identical inside the srbbgg tree.
# This is a coincidence of the current analyzer structure, not a
# guarantee -- if the analyzer's weight computation is ever changed to
# apply anything genuinely region-specific, this mismatch would
# silently read the wrong (but still-present, no missing-field
# warning) value with no visible error at all. Fixed by matching
# TREE_NAME, exactly as it should have been updated the first time. No
# change in existing event_categories.json output is expected from
# this fix alone.
BR_WGT        = "weight_srbbgg"
BR_ISDATA     = "isdata"
BR_TTH_KILLER = "ttH_killer_score"

USE_SIGMOID_SCORE = False
def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

# -------------------- helpers: directory/type detection --------------------
def is_data_dir(name: str) -> bool:
    n = name.lower()
    return n.startswith("data") or n.startswith("_data")

def is_signal_dir(name: str) -> bool:
    n = name.lower()
    return (
        "nmssm" in n or
        "gluglutohh" in n or
        "radion" in n or
        "graviton" in n or
        re.search(r"\bx\d{2,4}_y\d{2,4}\b", n) is not None
    )

def mass_tag_from_dir(name: str) -> str:
    n = name.lower()
    m = re.search(r"x(\d+)_y(\d+)", n)
    if m: return f"mX{m.group(1)}_mY{m.group(2)}"
    m2 = re.search(r"m(\d+)", n)
    return f"m{m2.group(1)}" if m2 else "combined"

def immediate_children(directory):
    """Return only TRUE, immediate child names of a directory-like uproot
    object -- NOT every nested key .keys() returns.

    CONFIRMED, real, reproducible bug this fixes: a directory's .keys()
    returns every nested descendant as a slash-joined path, not just its
    genuine immediate children -- e.g. for a real file containing ONLY
    the "ScaleEB_Zee_down" systematic (no "nominal" at all, matching
    this pipeline's one-systematic-per-file naming convention,
    hhbbgg_analyzer-v2-trees__<sample>__<systematic>.root),
    GluGluHtoGG.keys() returns BOTH "ScaleEB_Zee_down;1" (the
    subdirectory itself) AND every one of its region trees as
    slash-joined paths ("ScaleEB_Zee_down/srbbgg;1", etc.), flattened
    into one list rather than true immediate children only. Confirmed
    directly against a real production file.

    This is the SAME underlying uproot behavior collect_dirs() already
    works around for TOP-LEVEL sample directories -- generalized here so
    the identical fix also applies one level down, at the
    sample-subdirectory level, where it was previously missing.

    Without this fix, --write-categorized's systematic-detection logic
    would fall through to treating a mismatched-systematic file as
    flat/legacy, then iterate its slash-joined keys directly -- passing
    a string like "ScaleEB_Zee_down/srbbgg" straight into mktree() as if
    it were a plain tree name. This corrupted uproot's internal
    free-space bookkeeping and crashed the entire run partway through
    with:
        RuntimeError: segment of data to release overlaps one already
        marked as free: releasing [2378, 2721) but [2684, 2721) is free
    -- losing every not-yet-processed sample's categorized output, the
    same category of failure the hasattr() guard a few lines below was
    already built to prevent for the DIRECTORY-vs-TREE case, just not
    for this SLASH-JOINED-KEY case.
    """
    candidates = set()
    for k in directory.keys():
        base = k.split(";")[0]
        top = base.split("/")[0]
        if top:
            candidates.add(top)
    return sorted(candidates)

def collect_dirs(fin):
    """Return only TRUE top-level sample directory names.

    `fin.keys()` (non-recursive) in this uproot version still returns
    every nested key, not just top-level ones -- and every intermediate
    directory (e.g. "sample/nominal") is itself a ReadOnlyDirectory, so a
    naive "is this a directory" filter treats every systematic
    subdirectory as if it were its own separate top-level sample. That
    caused two real problems: double-counting a sample's nominal data
    (once correctly, once via the spurious nested entry), and in the
    worse case, silently reading a DIFFERENT systematic's tree into the
    bucket for --systematic nominal (since the spurious entry's own
    children don't contain a "nominal" subdirectory to descend into, so
    the descent logic falls back to treating the spurious entry itself as
    the target). Only keep the first path segment of each key.

    Candidate names are deduplicated via string parsing FIRST, so each
    unique top-level name is opened at most once -- not once per nested
    key -- avoiding the same "many individual file opens" issue already
    fixed in plot_stacks.py's list_top_dirs().
    """
    candidates = set()
    for dkey in fin.keys():
        dbase = dkey.split(";")[0]
        top = dbase.split("/")[0]
        if top:
            candidates.add(top)

    tops = []
    for top in sorted(candidates):
        obj = fin[top]
        if isinstance(obj, uproot.reading.ReadOnlyDirectory):
            tops.append(top)
    return tops

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

def concat1(lst):
    if not lst: return np.array([], dtype=float)
    if len(lst) == 1: return ak.to_numpy(lst[0])
    return ak.to_numpy(ak.concatenate(lst, axis=0))

# -------------------- significance & optimization --------------------
def AMS(s, b):
    """AMS = sqrt( 2 * ((s+b) ln(1+s/b) - s) )"""
    if b <= 0.0:
        return 0.0
    return math.sqrt(max(0.0, 2.0 * ((s + b) * math.log(1.0 + s / b) - s)))

def objective(Ss, Bs):
    """We maximize sum(AMS^2) -> minimize negative for greedy selection."""
    return -sum(AMS(s, b)**2 for s, b in zip(Ss, Bs))

def build_edges(scores, s_w, b_w, nmin, min_gain, max_bins, tie_tol=1e-4):
    """Greedy category-boundary search, implementing the exact 6-step
    B2G-24-001 procedure:

      1. Sort events by score, descending.
      2. Candidate SR = the next `nmin` highest-scoring events among those
         NOT YET assigned to an accepted SR.
      3. Compare summed AMS^2 significance with the currently-accepted SRs
         only ("before") vs. accepted SRs + this candidate ("after").
      4. If the relative improvement is >= min_gain, ACCEPT this SR, move
         on to the next remaining events, and reset nmin back to its
         starting value for the next SR search.
      5/6. If improvement is insufficient, double nmin and retry from the
         same starting point; keep doubling until an improvement is found
         or too few events remain.

    NOTE: this fixes a previous bug where the "before" baseline was fixed
    to the grand total of ALL events and never shrank as SRs were
    accepted, causing every accepted SR's yield to be double-counted in
    the objective (once inside the permanent "everything" total, once as
    its own bin). That inflated the acceptance gain on nearly every
    candidate and did not correspond to genuine disjoint-bin significance.

    FIXED (this pass, round 2): the round-1 tie-extension fix used EXACT
    floating-point equality (s[nxt-1] == s[nxt]) to detect tie groups.
    Confirmed via a real run that this does not match the actual failure
    mode: near the score ceiling, events don't share bit-identical
    float32 values -- they're spread across many distinct values
    differing only in the last representable digits (~1e-7, float32's
    precision limit near 1.0), a direct consequence of how a saturated
    sigmoid output is stored, not genuine ties. A real run with the
    exact-equality version still produced boundaries like
    [0.9999995231628418, 0.9999996423721313, 0.9999997615814209,
    0.9999998807907104, 1.0] -- five "distinct" values that are all
    practically the same cut. Switched to a tolerance-based comparison
    (tie_tol, default 1e-4) so events within that tolerance of each
    other are correctly treated as one effective tie group, regardless
    of exact float32 representation.
    """
    order = np.argsort(scores)[::-1]
    s, sw, bw = scores[order], s_w[order], b_w[order]
    N = len(s)

    nmin_start = nmin
    edges: list = []
    accepted_S: list = []
    accepted_B: list = []
    idx = 0

    def significance(acc_S, acc_B):
        # "before" with nothing accepted yet contributes zero significance.
        return objective(acc_S, acc_B) if acc_S else 0.0

    while (N - idx) >= 1 and len(edges) < max_bins:
        this_nmin = min(nmin, N - idx)
        nxt = idx + this_nmin
        # Extend past any (near-)tie group straddling the cutoff -- see
        # docstring. s is sorted descending, so s[nxt-1] >= s[nxt] always.
        while nxt < N and (s[nxt - 1] - s[nxt]) < tie_tol:
            nxt += 1
        S_new = sw[idx:nxt].sum()
        B_new = bw[idx:nxt].sum()

        best = significance(accepted_S, accepted_B)
        cand = objective(accepted_S + [S_new], accepted_B + [B_new])
        gain = (best - cand) / abs(best) if best != 0 else 1.0

        if gain >= min_gain:
            edges.append(float(s[nxt - 1]))
            accepted_S.append(S_new)
            accepted_B.append(B_new)
            idx = nxt
            nmin = nmin_start  # reset for the next SR search (per step 2)
        else:
            nmin *= 2
            if nmin > (N - idx):
                break

    return sorted(edges)

# -------------------- alpha(pDNN): CR -> SR transfer --------------------
def make_alpha(score_sr_mc, w_sr_mc, score_cr_mc, w_cr_mc, nbins=60):
    lo = float(np.min([np.min(score_sr_mc), np.min(score_cr_mc)]))
    hi = float(np.max([np.max(score_sr_mc), np.max(score_cr_mc)]))
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = -5.0, 5.0
    edges = np.linspace(lo, hi, nbins + 1)

    h_sr, _ = np.histogram(score_sr_mc, bins=edges, weights=w_sr_mc)
    h_cr, _ = np.histogram(score_cr_mc, bins=edges, weights=w_cr_mc)

    eps = 1e-9
    alpha = (h_sr + eps) / (h_cr + eps)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, alpha, (lo, hi)

def eval_alpha(x, centers, alpha, lohi):
    lo, hi = lohi
    return np.interp(np.clip(x, lo, hi), centers, alpha)

# -------------------- main --------------------
def resolve_input_files(root_arg: str):
    """Resolve --root into a list of ROOT files to process.

    Handles the analyzer's per-sample output split (a real, confirmed
    fix for a 2GB uproot-write-cascade crash under --all-systematics --
    struct.error: 'i' format requires -2147483648 <= number <=
    2147483647, hit mid-run once systematics pushed a single monolithic
    tree file's size past uproot's 32-bit file-offset limit). The
    analyzer now writes one file per sample instead:
    hhbbgg_analyzer-v2-trees__<sample>.root.

    - If root_arg is a file: return [root_arg] (also covers the old,
      pre-fix single-file layout unchanged).
    - If root_arg is a directory: glob for hhbbgg_analyzer-v2-trees__*.root
      (new layout). If none found, fall back to a single
      hhbbgg_analyzer-v2-trees.root in that directory (old layout), so
      this doesn't break against outputs produced before this fix.
    """
    p = Path(root_arg) if not isinstance(root_arg, Path) else root_arg
    if p.is_file():
        return [str(p)]
    if p.is_dir():
        per_sample = sorted(p.glob("hhbbgg_analyzer-v2-trees__*.root"))
        if per_sample:
            print(f"[INFO] --root is a directory: found {len(per_sample)} per-sample tree file(s).")
            return [str(f) for f in per_sample]
        legacy = p / "hhbbgg_analyzer-v2-trees.root"
        if legacy.is_file():
            print(f"[INFO] --root is a directory: no per-sample files found, "
                  f"falling back to legacy single file: {legacy}")
            return [str(legacy)]
        raise FileNotFoundError(
            f"--root '{root_arg}' is a directory but contains neither "
            f"hhbbgg_analyzer-v2-trees__*.root (new layout) nor "
            f"hhbbgg_analyzer-v2-trees.root (legacy layout)."
        )
    raise FileNotFoundError(f"--root '{root_arg}' is neither a file nor a directory.")


def main():
    ap = argparse.ArgumentParser(description="Sideband-based (data-driven) pDNN categorization using AMS and α(score).")
    ap.add_argument("--root", required=True,
                     help="Either a single merged ROOT file (old layout), or a directory "
                          "containing per-sample hhbbgg_analyzer-v2-trees__<sample>.root files "
                          "(current analyzer output layout, after the 2GB-crash fix).")
    ap.add_argument("--sr-sigma", type=float, default=SR_DEFAULT, help="SR: |mgg-125| < SR_SIGMA (GeV)")
    ap.add_argument("--cr-sidebands", type=float, nargs=2, default=list(CR_DEFAULT),
                    help="CR: |mgg-125| in [LO, HI) (GeV)")
    ap.add_argument("--nmin", type=int, default=20, help="min events per candidate bin")
    ap.add_argument("--min-gain", type=float, default=0.05,
                     help="min relative improvement in summed AMS^2 to accept a new SR "
                          "(e.g. 0.05 = 5%%, per B2G-24-001 step 4)")
    ap.add_argument("--max-bins", type=int, default=10, help="max SR bins")
    ap.add_argument("--outdir", default="outputs/categories_alpha")
    ap.add_argument("--per-mass", action="store_true", help="derive per-mass edges for signal dirs")
    ap.add_argument("--write-categorized", action="store_true", help="clone ROOT and add cat/region branches")
    ap.add_argument("--alpha-bins", type=int, default=60, help="nbins for α(score)")
    ap.add_argument("--sigmoid-score", action="store_true", help="apply sigmoid to pDNN_score (if logits)")
    ap.add_argument("--tth-killer-cut", type=float, default=None,
                     help="If set, require ttH_killer_score < CUT for every event (signal, "
                          "background MC, and data alike) before anything else -- confirmed "
                          "direction (lower score = less ttH-like) and working points from a "
                          "validated efficiency study: Loose=0.924 (ttH eff 50%%), "
                          "Medium=0.682 (ttH eff 20%%, signal eff 97.8%%), Tight=0.401 (ttH "
                          "eff 10%%, signal eff 94.7%%). Not applied by default, for backward "
                          "compatibility with files that predate this branch.")
    ap.add_argument("--systematic", default="nominal",
                     help="Which systematic's trees to read (default: nominal). The analyzer's "
                          "output structure is sample/systematic/region -- this selects the "
                          "middle segment. Category boundaries are derived from, and "
                          "--write-categorized only processes, this ONE systematic; whether "
                          "boundaries should be frozen on nominal and reused elsewhere, or "
                          "re-derived per systematic, is an open decision (tracked separately) "
                          "not resolved by this flag alone.")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    if args.sigmoid_score:
        global USE_SIGMOID_SCORE
        USE_SIGMOID_SCORE = True

    sr_lo = 125.0 - args.sr_sigma
    sr_hi = 125.0 + args.sr_sigma
    cr_lo, cr_hi = args.cr_sidebands

    apply_tth_cut = args.tth_killer_cut is not None
    if apply_tth_cut:
        print(f"[INFO] ttH-killer cut ENABLED: requiring ttH_killer_score < {args.tth_killer_cut}")

    input_files = resolve_input_files(args.root)

    # -------- read & collect (across ALL input files) --------
    # buckets/shared_bg/counters now accumulate across every file in
    # input_files, not just one -- required since the analyzer's
    # per-sample output split means signal/background/data are now
    # spread across many files instead of one, and the whole point of
    # this pooling is combining them before deriving category boundaries.
    buckets = {}
    def ensure(tag):
        if tag not in buckets:
            buckets[tag] = dict(S_sr_scores=[], S_sr_w=[])
        return buckets[tag]

    shared_bg = dict(
        B_sr_scores_mc=[], B_sr_w_mc=[],
        B_cr_scores_mc=[], B_cr_w_mc=[],
        D_cr_scores=[], D_cr_w=[]
    )

    n_used = n_skipped_no_tree = n_skipped_missing_fields = n_skipped_no_tth = 0
    n_files_total_dirs = 0

    for root_file in input_files:
        with uproot.open(root_file) as fin:
            dir_bases = collect_dirs(fin)
            n_files_total_dirs += len(dir_bases)
            for dbase in dir_bases:
                tdir = fin[dbase]

                # Analyzer output is now sample/systematic/region, not the old
                # sample/region -- descend into the requested systematic
                # subdirectory first. A directory with no such subdirectory at
                # all (e.g. a genuinely flat/legacy file) falls back to
                # looking directly in tdir, so this doesn't break against
                # older-structure files.
                if args.systematic in [k.split(";")[0] for k in tdir.keys()]:
                    systdir = tdir[args.systematic]
                else:
                    systdir = tdir

                sel_key = get_tree_key(systdir, TREE_NAME)
                if sel_key is None:
                    n_skipped_no_tree += 1
                    continue

                tree = systdir[sel_key]
                tfields = set(tree.keys())
                needed = {BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA}
                if not needed.issubset(tfields):
                    n_skipped_missing_fields += 1
                    continue
                if apply_tth_cut and BR_TTH_KILLER not in tfields:
                    n_skipped_no_tth += 1
                    continue
                n_used += 1

                read_branches = [BR_SCORE, BR_MGG, BR_WGT, BR_ISDATA]
                if apply_tth_cut:
                    read_branches.append(BR_TTH_KILLER)
                arr = tree.arrays(read_branches, library="ak")
                mgg   = arr[BR_MGG]
                score = arr[BR_SCORE]
                wgt   = arr[BR_WGT]
                isdata = arr[BR_ISDATA] if BR_ISDATA in arr.fields else ak.zeros_like(mgg)

                mc   = (isdata == 0)
                data = (isdata != 0)

                in_sr = (mgg >= sr_lo) & (mgg <= sr_hi)
                absd  = np.abs(ak.to_numpy(mgg) - 125.0)
                in_cr = (absd >= cr_lo) & (absd < cr_hi)

                # ttH-killer cut, applied uniformly across signal/background/
                # data before anything else -- confirmed direction is
                # "lower score = less ttH-like", so pass = score < cut.
                if apply_tth_cut:
                    tth_pass = arr[BR_TTH_KILLER] < args.tth_killer_cut
                    in_sr = in_sr & tth_pass
                    in_cr = in_cr & tth_pass

                score_np = ak.to_numpy(score)
                if USE_SIGMOID_SCORE:
                    score_np = sigmoid(score_np)
                w_np = ak.to_numpy(wgt)

                if is_data_dir(dbase):
                    dsel = ak.to_numpy(in_cr[data])
                    shared_bg["D_cr_scores"].append(score_np[data][dsel])
                    shared_bg["D_cr_w"].append(np.ones_like(score_np[data][dsel]))
                elif is_signal_dir(dbase):
                    tag = "combined"
                    if args.per_mass:
                        tag = mass_tag_from_dir(dbase)
                    dest = ensure(tag)
                    ssel = ak.to_numpy(in_sr[mc])
                    dest["S_sr_scores"].append(score_np[mc][ssel])
                    dest["S_sr_w"].append(w_np[mc][ssel])
                else:
                    ssel = ak.to_numpy(in_sr[mc])
                    csel = ak.to_numpy(in_cr[mc])
                    shared_bg["B_sr_scores_mc"].append(score_np[mc][ssel])
                    shared_bg["B_sr_w_mc"].append(w_np[mc][ssel])
                    shared_bg["B_cr_scores_mc"].append(score_np[mc][csel])
                    shared_bg["B_cr_w_mc"].append(w_np[mc][csel])

    # Summary printed ONCE, after all input files -- moved out of the
    # per-file loop (a real bug from the multi-file restructuring: it
    # was printing once per file with len(dir_bases) reflecting only
    # the LAST file's directory count, not the true cumulative total,
    # while n_used/n_skipped_* are genuinely cumulative -- producing a
    # confusing, incorrect-looking ratio if left inside the loop).
    print(f"[INFO] systematic='{args.systematic}': used {n_used}/{n_files_total_dirs} sample "
          f"directories across {len(input_files)} file(s) ({n_skipped_no_tree} had no "
          f"'{TREE_NAME}' tree under this systematic, {n_skipped_missing_fields} were "
          f"missing required branches"
          + (f", {n_skipped_no_tth} were missing '{BR_TTH_KILLER}' with --tth-killer-cut set)" if apply_tth_cut else ")"))
    if n_used == 0:
        print(f"[WARN] No usable trees found for systematic='{args.systematic}' -- check "
              f"the spelling matches what the analyzer actually wrote (e.g. 'nominal'), "
              f"and that --root points at file(s) produced by the current analyzer version "
              f"(sample/systematic/region structure, not the older sample/region layout).")

    # -------- build edges with α(score) --------
    # Background MC and data are shared across every tag (see shared_bg
    # above) -- computed once here, then reused for every tag's alpha(score)
    # and boundary search, rather than being tag-specific.
    Bsr_mc = concat1(shared_bg["B_sr_scores_mc"]); Bsrw_mc = concat1(shared_bg["B_sr_w_mc"])
    Bcr_mc = concat1(shared_bg["B_cr_scores_mc"]); Bcrw_mc = concat1(shared_bg["B_cr_w_mc"])
    Dcr    = concat1(shared_bg["D_cr_scores"]);    Dcrw    = concat1(shared_bg["D_cr_w"])

    if Bsr_mc.size == 0 or Bcr_mc.size == 0 or Dcr.size == 0:
        print(f"[WARN] Shared background/data pool is empty or incomplete "
              f"(B_sr={Bsr_mc.size}, B_cr={Bcr_mc.size}, D_cr={Dcr.size}) -- "
              f"every tag below will be skipped as a result.")

    results = {}
    for tag, d in buckets.items():
        Sscore = concat1(d["S_sr_scores"]); Sw = concat1(d["S_sr_w"])

        if Sscore.size == 0 or Dcr.size == 0 or Bsr_mc.size == 0 or Bcr_mc.size == 0:
            print(f"[warn] Tag '{tag}': insufficient inputs for α-method; skipping.")
            continue

        centers, alpha, lohi = make_alpha(Bsr_mc, Bsrw_mc, Bcr_mc, Bcrw_mc, nbins=args.alpha_bins)
        Bscore = Dcr
        Bw     = eval_alpha(Dcr, centers, alpha, lohi) * Dcrw

        edges = build_edges(
            scores=np.concatenate([Sscore, Bscore]),
            s_w=np.concatenate([Sw, np.zeros_like(Bw)]),
            b_w=np.concatenate([np.zeros_like(Sw), Bw]),
            nmin=args.nmin,
            min_gain=args.min_gain,
            max_bins=args.max_bins
        )
        results[tag] = edges
        print(f"[edges α-method] {tag}: {edges}")

    # -------- write JSON --------
    out_json = os.path.join(args.outdir, "event_categories.json")
    payload = {
        "boundaries": results,
        "sr_mgg_window_GeV": args.sr_sigma,
        "cr_mgg_sidebands_GeV": list(args.cr_sidebands),
        "tth_killer_cut": args.tth_killer_cut
    }
    with open(out_json, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out_json}")

    # -------- optional: categorized ROOT copy (uproot-5 safe) --------
    # Produces ONE categorized output PER input file, matching the
    # analyzer's own per-sample split -- not just for consistency, but
    # because writing everything back into a single combined output
    # would risk reintroducing the exact same uproot 2GB write-cascade
    # crash this whole restructuring exists to avoid.
    if args.write_categorized:
        for root_file in input_files:
            out_root = os.path.join(
                args.outdir,
                os.path.basename(root_file).replace(".root", "__categorized.root")
            )
            with uproot.open(root_file) as fin, uproot.recreate(out_root) as fout:

                for dbase in collect_dirs(fin):
                    try:
                        fout.mkdir(dbase)
                    except Exception:
                        pass

                def write_tree(out_dir, tname: str, arrays_np: dict):
                    clean = {}
                    for k, v in arrays_np.items():
                        arr = np.asarray(v)

                        if arr.dtype == np.dtype("O"):
                            raise RuntimeError(f"Branch '{tname}:{k}' has object dtype — convert jagged arrays to fixed numpy arrays first.")

                        if arr.ndim != 1:
                            raise RuntimeError(f"Branch '{tname}:{k}' is not 1-D (ndim={arr.ndim}).")

                        if np.issubdtype(arr.dtype, np.integer):
                            amin = arr.min() if arr.size else 0
                            amax = arr.max() if arr.size else 0
                            if amin < np.iinfo(np.int32).min or amax > np.iinfo(np.int32).max:
                                print(f"[warn] Branch '{tname}:{k}' requires int64 range ({amin}..{amax}). Keeping int64.")
                                clean[k] = arr.astype(np.int64)
                            else:
                                clean[k] = arr.astype(np.int32)
                            continue

                        if np.issubdtype(arr.dtype, np.floating):
                            clean[k] = arr.astype(np.float32)
                            continue

                        if arr.dtype == np.bool_:
                            clean[k] = arr.astype(np.uint8)
                            continue

                        clean[k] = arr

                    branch_types = {k: v.dtype for k, v in clean.items()}
                    out_tree = out_dir.mktree(tname, branch_types)
                    out_tree.extend(clean)

                n_copied_samples = 0
                for dbase in collect_dirs(fin):
                    in_dir_obj = fin[dbase]
                    sample_out_dir = fout[dbase]

                    # Analyzer output is now sample/systematic/region -- descend
                    # into the requested systematic subdirectory before looking
                    # for trees, same as the boundary-fitting loop above. Only
                    # this ONE systematic is copied into the categorized output
                    # for now; writing cat/region-tagged copies of every
                    # systematic is blocked on the still-open
                    # frozen-vs-per-systematic-boundaries decision.
                    #
                    # FIXED (this pass): child_names is now computed via
                    # immediate_children() instead of naive
                    # [k.split(";")[0] for k in in_dir_obj.keys()] -- the naive
                    # version was fooled by slash-joined nested keys (see
                    # immediate_children()'s docstring), which caused a real,
                    # confirmed crash for any per-(sample, systematic) file
                    # whose one systematic isn't the one requested (e.g.
                    # GluGluHtoGG__ScaleEB_Zee_down.root under --systematic
                    # nominal). Also added a third, explicit branch below for
                    # exactly that mismatched-systematic case -- skip cleanly
                    # instead of falling through to the flat/legacy branch.
                    child_names = immediate_children(in_dir_obj)

                    if args.systematic in child_names:
                        syst_in_dir = in_dir_obj[args.systematic]
                        try:
                            out_dir = sample_out_dir.mkdir(args.systematic)
                        except Exception:
                            out_dir = sample_out_dir[args.systematic]
                    elif TREE_NAME in child_names:
                        # Genuinely flat/legacy: region trees sit directly
                        # under the sample, no systematic subdirectory layer
                        # at all -- confirmed this case still exists (older-
                        # convention files) and must keep working unchanged.
                        syst_in_dir = in_dir_obj
                        out_dir = sample_out_dir
                    else:
                        # FIXED, confirmed real case: this sample directory
                        # HAS subdirectory structure, but it's neither the
                        # requested systematic nor a flat/legacy layout --
                        # this pipeline's one-systematic-per-file convention
                        # means a file like
                        # hhbbgg_analyzer-v2-trees__GluGluHtoGG__ScaleEB_Zee_down.root
                        # genuinely contains ONLY that one systematic, which
                        # may not be the one requested via --systematic.
                        # Previously this fell through to the flat/legacy
                        # branch above, which then iterated slash-joined
                        # nested keys as if they were plain tree names -- see
                        # immediate_children()'s docstring for the crash this
                        # caused. Skip this file/sample entirely for this run
                        # instead -- there is nothing here that matches what
                        # was requested.
                        print(f"[INFO] '{dbase}': available "
                              f"subdirector{'y is' if len(child_names) == 1 else 'ies are'} "
                              f"{child_names}, not the requested systematic "
                              f"'{args.systematic}' -- skipping this file/sample "
                              f"for this run (not an error -- this file simply "
                              f"doesn't contain that systematic's data).")
                        continue

                    n_copied_samples += 1

                    for tkey in syst_in_dir.keys():
                        tbase = tkey.split(";")[0]
                        tree  = syst_in_dir[tkey]

                        # Guard against tkey resolving to a nested
                        # ReadOnlyDirectory rather than an actual TTree --
                        # confirmed as a real, live crash: uproot's .keys()
                        # can surface nested-directory keys alongside leaf
                        # tree keys (the same underlying behavior already
                        # handled for collect_dirs() elsewhere in this
                        # script), and a directory object has no .arrays()
                        # method. Previously this reached tree.arrays()
                        # unconditionally in the "copy any other tree
                        # as-is" fallback below, crashing the ENTIRE
                        # --write-categorized run uncaught partway through
                        # -- meaning every sample after the failing one
                        # never got its categorized output written at all.
                        # Skip loudly instead of crashing, so one
                        # unexpected key can't take down the whole run.
                        #
                        # FIXED (this pass): the printed path used to
                        # hardcode {args.systematic} regardless of which
                        # branch actually ran above (misleading once the
                        # flat/legacy branch was taken) -- now prints the
                        # real key path directly instead.
                        if not hasattr(tree, "arrays"):
                            print(f"[WARN] '{dbase}/{tkey}' is not a tree "
                                  f"(got {type(tree).__name__}) -- skipping this key, not "
                                  f"copying it into the categorized output.")
                            continue

                        if (
                            tbase != TREE_NAME
                            or (BR_SCORE not in tree.keys())
                            or (BR_MGG   not in tree.keys())
                        ):
                            arrays_np = tree.arrays(library="np")
                            write_tree(out_dir, tbase, arrays_np)
                            continue

                        arr = tree.arrays(library="ak")
                        score_np = ak.to_numpy(arr[BR_SCORE])
                        if USE_SIGMOID_SCORE:
                            score_np = 1.0 / (1.0 + np.exp(-score_np))
                        mgg_np   = ak.to_numpy(arr[BR_MGG])

                        sr_mask = np.abs(mgg_np - 125.0) < args.sr_sigma
                        lo, hi  = args.cr_sidebands
                        cr_mask = (np.abs(mgg_np - 125.0) >= lo) & (np.abs(mgg_np - 125.0) < hi)

                        # Same ttH-killer cut as the boundary-fitting loop above,
                        # applied here too so the categorized output file is
                        # consistent with the edges that were actually derived
                        # from cut events -- an event failing the cut gets no
                        # region/category assignment at all (stays at the
                        # -1/-99 default), same treatment as an event outside
                        # both the SR and CR windows entirely.
                        if apply_tth_cut:
                            if BR_TTH_KILLER in tree.keys():
                                tth_np = ak.to_numpy(tree.arrays([BR_TTH_KILLER], library="ak")[BR_TTH_KILLER])
                                tth_pass = tth_np < args.tth_killer_cut
                                sr_mask = sr_mask & tth_pass
                                cr_mask = cr_mask & tth_pass
                            else:
                                print(f"[warn] '{dbase}': --tth-killer-cut set but '{BR_TTH_KILLER}' "
                                      f"not found in this tree -- no events here will be assigned to "
                                      f"any region (safer than silently skipping the cut).")
                                sr_mask = np.zeros_like(sr_mask)
                                cr_mask = np.zeros_like(cr_mask)

                        tag = "combined"
                        if args.per_mass and is_signal_dir(dbase):
                            tag = mass_tag_from_dir(dbase)
                        edges = results.get(tag)
                        if edges is None:
                            edges = results.get("combined", [])
                            if args.per_mass and is_signal_dir(dbase):
                                print(f"[warn] No per-mass edges for tag '{tag}' (dir '{dbase}'); "
                                      f"falling back to 'combined' edges.")
                            elif args.per_mass and not edges:
                                print(f"[warn] '{dbase}': background/data has no single mass "
                                      f"identity, and no shared 'combined' edges exist under "
                                      f"--per-mass (only per-mass signal tags do) -- SR events in "
                                      f"this directory will NOT get a cat/region assignment (stay "
                                      f"at the -99/-1 default). This reflects an open design "
                                      f"question: background/data currently carries a single "
                                      f"pDNN_score (scored at one reference mass point, not "
                                      f"per-signal-hypothesis), so there is no principled single "
                                      f"set of edges to apply to it across the whole per-mass grid.")

                        cat    = np.full(len(score_np), -99, np.int16)
                        region = np.full(len(score_np),  -1, np.int8)
                        for i, thr in enumerate(edges):
                            sel = (score_np >= thr) & sr_mask
                            cat[sel]    = i
                            region[sel] = 1
                        # Events scoring below every derived boundary are
                        # deliberately left at cat=-99 (excluded), NOT
                        # folded into a catch-all category. This matches
                        # common/io_utils.py's score_to_category() -- the
                        # pipeline's own documented shared source of truth
                        # for this exact mapping -- and the AMS boundary
                        # search's own logic: build_edges() only accepts a
                        # new SR when it improves combined sensitivity by
                        # >=5%, so events left over once it stops are
                        # exactly the ones that optimization already
                        # judged not worth a dedicated category.
                        #
                        # A catch-all category (cat = len(edges)) was
                        # tried here previously, reasoning that excluding
                        # these events looked like lost signal acceptance.
                        # That reasoning didn't account for
                        # score_to_category() already being a deliberate,
                        # separately-validated design choice -- it fixed a
                        # real, previously-caught bug (fit_signal_shapes_
                        # for_slides.py / fit_signal_mjj_for_slides.py once
                        # used the opposite convention, silently shifting
                        # every category index by one; caught via a real
                        # 122-million chi2/ndof outlier). The catch-all
                        # addition here silently reintroduced that same
                        # mismatch from the other direction: every
                        # downstream shape fit silently skipped the
                        # catch-all category with no error at all, most
                        # visibly for mX1000_mY300 (2 categories under the
                        # catch-all convention; the shape fit only ever
                        # attempted category 0). Reverted -- do not
                        # re-add without also updating score_to_category()
                        # and every one of its consumers to match.
                        cat[cr_mask]    = -1
                        region[cr_mask] = 0

                        arrays_np = tree.arrays(library="np")
                        arrays_np["cat"]    = cat
                        arrays_np["region"] = region
                        write_tree(out_dir, tbase, arrays_np)

            print(f"Wrote {out_root} ({n_copied_samples} sample(s), systematic='{args.systematic}')")


if __name__ == "__main__":
    main()