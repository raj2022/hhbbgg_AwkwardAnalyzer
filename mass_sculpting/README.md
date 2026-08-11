# Mass Sculpting Validation

Physics validation check within `pDNN_v2.py` that verifies the trained
pDNN does not sculpt (introduce a fake peak, edge, or otherwise non-trivial
feature into) the smoothly-falling background diphoton-mass spectrum.
Sculpting would compromise the background-only hypothesis the final fit
relies on, since the background shape is assumed smooth and independent
of category.

For the full methodology (weighted KS test, effective sample size,
interpretation caveats) and a ready-to-use LaTeX writeup for analysis
notes, see `mass_sculpting.tex`. This README covers the practical
side: what runs, where outputs land, and how to interpret them quickly.

---

## What It Does

1. Picks whichever mass-proxy column is actually present in the test
   split (`diphoton_mass`, `mgg`, `CMS_hgg_mass`, ..., checked in that
   order — see `Config.MASS_SCULPT_CANDIDATES`).
2. For each score cut in `Config.SCORE_CUTS` (default
   `0.0, 0.3, 0.5, 0.7, 0.9`), compares the background mass shape with no
   cut against the shape after that cut, using a **weighted** two-sample
   Kolmogorov–Smirnov test (`scipy.stats.ks_2samp` does not support event
   weights, so a manual implementation is used — see `weighted_ks_2samp()`).
3. Produces a signal/background efficiency table and rejection-power
   curve across the same score cuts.
4. Saves three plots and the full numerical results (see below).

`cut_0.0` is a built-in closure test — comparing the no-cut sample to
itself must return `D = 0`, `p = 1` exactly. If it doesn't, something is
wrong with the test itself, not the physics.

---

## Where It Lives in the Code

All in `pDNN_v2.py`, Section 14 ("Physics Validation"):

| Function | Role |
|---|---|
| `_find_mass_sculpt_column()` | Selects the available mass-proxy column |
| `weighted_ks_2samp()` | The weighted KS test (D statistic, effective-sample-size p-value) |
| `plot_mass_after_score()` | Background mass-shape overlay across score cuts |
| `run_mass_sculpting()` | Orchestrates the above; called once from `main()` |

## How to Run It

It runs automatically as part of the full pDNN training pipeline — no
separate invocation needed:

```bash
python pDNN_v2.py
```

`run_mass_sculpting()` is called near the end of `main()`, using the
already-trained model's test-split predictions. There is currently no
standalone entry point to re-run *only* this check without retraining —
if that's needed (e.g. to validate a checkpoint without retraining from
scratch), it would need a small wrapper script loading the saved model
(`outputs/models/best_pdnn.pt`) and scaler, then calling
`run_mass_sculpting()` directly.

## Outputs

Everything lands under `Config.OUTPUT_DIR` (default `"outputs"`,
resolved relative to wherever `pDNN_v2.py` is run from):

```
outputs/
├── plots/
│   └── MassSculpting/
│       ├── mass_sculpting_shapes.{png,pdf}      background shape overlay
│       ├── efficiency_vs_score.{png,pdf}        signal/background efficiency vs. cut
│       └── efficiency_ratio_vs_score.{png,pdf}  rejection power vs. cut (log scale)
└── logs/
    └── metrics.json     numerical results, under the "mass_sculpting" key
```

`metrics.json`'s `"mass_sculpting"` → `"ks_tests"` holds one entry per
score cut (`cut_0.0` ... `cut_0.9`), each with `ks_stat`, `p_value`,
`n_eff_no_cut`, `n_eff_this_cut` — the exact numbers that belong in an
analysis-note table (see `mass_sculpting.tex` for a ready-made one).

`"mass_sculpting"` → `"per_group_efficiency_at_0.5"` additionally breaks
signal/background efficiency down per `(mass, y)` group at a fixed
score ≥ 0.5, if `mass`/`y_value` columns are present in the test split.

---

## How to Read the Results

- **Read `D`, not `p`, as the primary number.** With `n_eff` typically in
  the $10^4$–$10^5$ range, the KS test is extremely sensitive — a
  formally tiny p-value does not by itself mean the sculpting is
  physically significant. `D` (bounded on $[0,1]$, directly interpretable
  as the maximum shape deviation) is the number to judge against your
  group's tolerance.
- **`cut_0.0` must show `D=0, p=1` exactly.** If it doesn't, treat every
  other result as suspect and debug the test itself first.
- **Inspect `mass_sculpting_shapes.png` directly**, not just the `D`
  values — a mild, gradual softening across the whole spectrum reads very
  differently from a sharp localized feature at one specific mass, even
  if both happen to produce a similar `D`.
- There is currently no team-agreed quantitative pass/fail threshold for
  `D` — results should be reported alongside that context, not as a
  standalone verdict.

---

## Known Caveat — Confirm Before Trusting Current Output

**Two independent occurrences of the same underlying bug, both now fixed:**

1. `inference_PDnn_updated.py` (used to score the merged analyzer output)
   had a mixed-precision (CUDA autocast / float16) bug that silently
   quantized `pDNN_score` near the top of its range — confirmed via a
   periodic "comb" pattern in the score distribution's tail and values
   round-tripping exactly through `np.float16`. Fixed by upcasting logits
   to float32 before `sigmoid`/`softmax`.
2. **This file's own `predict_batched()`** — which generates `test_probs`
   for every evaluation in this script, including mass sculpting, the ROC
   curve, and the score-distribution plots — had the **identical** bug,
   independently: `sigmoid()` was being called *inside* the `autocast`
   context. Found while writing this README (verifying the code before
   documenting it, rather than assuming it was fine because a sibling
   script's version of the bug had already been fixed elsewhere) and
   fixed the same way: logits upcast to float32, sigmoid moved outside
   the autocast context.

**Any mass-sculpting output — plots or `metrics.json` — generated before
this fix landed reflects float16-quantized scores and should be treated
as unreliable, not just imprecise.** Re-run `python pDNN_v2.py` end to
end to regenerate trustworthy results. There is no way to tell from the
saved files alone whether a given `outputs/` directory predates the fix —
if in doubt, check `Config.INIT_WEIGHT_STD`-adjacent training logs for a
timestamp, or simply regenerate.