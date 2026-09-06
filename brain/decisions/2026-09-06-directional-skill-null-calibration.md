# Directional Skill Test — Null Calibration Check

Task: decide between (a) this population genuinely contains far more
skilled traders than Polymarket at large, or (b) the randomisation null as
implemented is mis-specified and every trader's p-value is inflated — the
two explanations for the 2026-09-05 result (`2026-09-05-directional-skill-
result.md`, `cf88f8a` prereg): placebo classified-skilled at 39.2% raw /
29.4% BH vs a ~5% chance floor and Gómez-Cram's ~3% population rate. This
document presents evidence only. **No verdict on (a) vs (b) is stated
here — that call is Oscar's.**

Reproducibility: committed script `scripts/directional_skill_diagnostic.py`
(first-repo `b141351`, unmodified — its functions `load_post_split_positions`,
`per_trader_and_aggregate`, `split_half`, `sign_flip_null`, `classify`,
`bh_correction` are imported, not reimplemented, by this task's script).
New script: `scripts/directional_skill_null_calibration.py` (first-repo, this
commit). Durable artifact:
`data/characterizations/directional_skill_null_calibration_20260906T154414Z.json`.
Run with `--selfcheck` (400 synthetic positions re-derived from source
columns, 0 mismatches) in the same invocation that produced the artifact.

---

## Part 0 — located, with commits and paths

- **Diagnostic script**: `scripts/directional_skill_diagnostic.py`,
  committed at first-repo `b1413512191eb72ff15367fed924d54aa956ce79`
  ("feat: directional skill test -- placebo separates ahead of cohort").
- **Per-trader outputs persisted**: yes. The durable artifact
  `data/characterizations/directional_skill_20260905T161232Z.json` (also
  committed in `b141351`) contains a `per_trader` dict per arm
  (`cohort`, `placebo`), keyed by trader address, each entry holding
  `actual`, `null_p95`, **`p_value`**, `skilled`, `percentile_rank`,
  `n_positions`, `bh_significant`. **Per-trader p-values were persisted,
  not just aggregate rates** — Part 1 below re-tabulates them directly
  from this artifact, no regeneration needed, no STOP condition triggered.
- **Pre-registration**: `brain/decisions/2026-09-05-directional-skill-
  prereg.md` (trading-swarm `cf88f8a7f0cdea3d5dcba6846f29e00959bb9d56`).
  Result write-up: `brain/decisions/2026-09-05-directional-skill-result.md`
  (same trading-swarm history).
- **Randomisation implementation** (`sign_flip_null()`,
  `directional_skill_diagnostic.py:77-89`):
  - **Permutations**: `REPS = 1500` (module constant, line 46), matching
    the project's existing `v2d`/`v2f`/Track 2/decay-prereg convention per
    the prereg's own stated rationale — not Gómez-Cram's 10,000.
  - **Held fixed per replicate**: each position's `weighted_edge` magnitude
    (`(won − price) × cost`, computed once from the DB, not re-drawn).
  - **Randomised**: an independent fair-coin sign (`rng.integers(0,2,size=n)*2-1`)
    per position, per replicate, applied to that position's own
    `weighted_edge` — a per-position Rademacher sign-flip, not a
    position-count-weighted or trader-level flip.
  - **RNG seeding**: `np.random.default_rng(seed)` where `seed` is the
    project-wide constant `SEED = 42` (imported from
    `trader_skill_metric_v2f.py:131`), recorded in the artifact's top-level
    `seed` field. **Fact worth flagging explicitly, since Part 0 asks for
    it**: `SEED` is the *same literal value* passed into every call to
    `sign_flip_null()` throughout the script — once per classifiable
    trader (cohort loop), once per classifiable trader (placebo loop),
    once for the pooled aggregate test (each arm), and once per trader per
    half in `split_half()`. Each call constructs a **fresh** `default_rng(42)`
    (line 82), so the RNG is re-seeded to the identical starting state at
    every call site. This means two traders with the same position count
    `n` receive an identical null draw *sequence* (not identical null
    *values*, since the underlying `weighted_edges` differ) — a property of
    the harness as committed, not something this task changed. Whether
    this materially affects calibration is addressed empirically in Part 2,
    since the calibration run below reuses this exact seeding behaviour
    unchanged.

---

## Part 1 — p-value distribution (from the persisted 2026-09-05 artifact)

n = 73 (cohort, classifiable), 51 (placebo, classifiable), 124 (combined).

| arm | n | p<0.05 | p<0.01 | p<0.001 | frac p>0.5 (uniform expects ~0.50) | mean p given p>0.5 (uniform expects ~0.75) |
|---|---|---|---|---|---|---|
| cohort | 73 | 26.0% | 19.2% | 15.1% | 45.2% | 0.766 |
| placebo | 51 | 37.3% | 29.4% | 13.7% | 31.4% | 0.781 |
| combined | 124 | 30.6% | 23.4% | 14.5% | 39.5% | 0.771 |

(`p<0.05` rates match the artifact's own `raw_rate` figures — 26.0%
cohort / 39.2%... note: `below_rate[0.05]` for placebo here is 37.3%, not
39.2% — the artifact's `raw_rate` uses the `actual > null_p95` threshold
directly, this table uses `p_value < 0.05`; these are two slightly
different operationalisations of the same 95th-percentile bar and diverge
by a percentage point or two at these sample sizes because the null is a
1500-point empirical distribution, not a continuous one. Both are reported
here rather than reconciled.)

**Tail concentration**: both arms show far more p<0.05 (26–37%) than the
~5% a well-specified null would produce by chance, and placebo exceeds
cohort at every threshold.

**Upper-region (p>0.5) check**: under a well-specified null this region
should hold ~50% of the mass and be roughly flat within itself (mean ≈
0.75). Both arms fall short of the 50% mass figure (45.2% cohort, 31.4%
placebo, 39.5% combined) — i.e., *fewer* points sit above the median than
a uniform null would produce, meaning the leftward shift is not confined
to the extreme tail; it is pulling mass out of the upper half too.
Conditional on landing above 0.5, however, the mean (0.766–0.781) sits
close to the 0.75 a uniform distribution on (0.5, 1] would produce — the
shape within the upper half is not obviously distorted, only its total
share of the mass is reduced.

Per the task's own instruction, this is reported as indicative, not
decisive, on its own.

---

## Part 2 — synthetic zero-skill calibration (decisive)

**Construction**: real post-split positions for both frozen trader lists
(`cohort_trader_list` / `control_trader_list`, 169 each, from
`track2_ci_power_20260905T104945Z.json`), loaded via
`load_post_split_positions()` imported unchanged from
`directional_skill_diagnostic.py` — identical SQL, identical filters,
identical columns. For each position, one fair-coin sign was drawn **once**
(`np.random.default_rng(SYNTH_SEED)`, not per null replicate) and applied
to that position's `(won, price)` pair exactly as the prereg's own
flipped-payoff derivation specifies (flip → `won_no = 1-won`,
`price_no = 1-price`; unflipped → unchanged). This yields a population
whose realised direction is independent of outcome by construction, while
every other structural input (market, timing, price, size) is untouched.

- **Seed recorded**: `SYNTH_SEED = 20260906` for the cohort-ID population,
  `20260907` for the control-ID population (offset by 1, both recorded in
  the artifact's `synth_seed_cohort` / `synth_seed_control` fields) — a
  new, task-specific seed, distinct from the harness's own `SEED=42`,
  which remains untouched and is still used unmodified inside
  `sign_flip_null()` for null generation on top of this synthetic data.
- **Full eligible population, no sampling**: both frozen lists (338
  traders total) run in full; runtime was a few seconds, no runtime
  constraint encountered, no sample-size approval needed.
- **No harness modification**: `per_trader_and_aggregate()`, `split_half()`,
  `sign_flip_null()`, `classify()`, `bh_correction()` are imported from
  `directional_skill_diagnostic.py` and called with no changes to their
  code. **One adaptation was made, and is reported as required**: the
  synthetic input frame's `weighted_edge` column is overwritten with the
  synthetic (post-flip) value before being handed to these functions —
  the frame's other columns (`trader`, `market_id`, `price`, `cost`,
  `entry_ts`) are untouched. This is a change to the *input data*, not to
  the harness code path. A second scoping decision, also reported: results
  are given per-arm (synthetic-cohort using the cohort trader-ID list,
  synthetic-placebo using the control trader-ID list — directly
  row-comparable to the 2026-09-05 table) **and** pooled (both arms
  concatenated into one 338-trader population, since the cohort/placebo
  distinction has no remaining meaning once direction has been
  randomised) — reporting both rather than choosing one.

### Classification rates

| population | classifiable | raw skilled | raw rate | BH skilled | BH rate |
|---|---|---|---|---|---|
| synthetic-cohort | 73 | 3 | **4.1%** | 0 | **0.0%** |
| synthetic-placebo | 51 | 4 | **7.8%** | 0 | **0.0%** |
| synthetic-pooled | 124 | 7 | **5.6%** | 0 | **0.0%** |

Compare to this test's stated ~5% chance floor and the 2026-09-05 real
figures (cohort 26.0%/19.2%, placebo 39.2%/29.4%).

### Pooled aggregate significance test

| population | actual | null p95 | percentile rank | p-value | skilled? |
|---|---|---|---|---|---|
| synthetic-cohort | −53,368.56 | 179,105.25 | 34.47 | 0.656 | NO |
| synthetic-placebo | −42,685.87 | 54,419.73 | 11.80 | 0.882 | NO |
| synthetic-pooled | −96,054.43 | 191,143.67 | 21.60 | 0.784 | NO |

None of the three synthetic populations clears its own 95th-percentile
bar. Compare to the real run: placebo p=0.006 (99.47th pctile, SKILLED),
cohort p=0.214 (78.67th pctile, not skilled).

### Split-half persistence

| population | eligible (≥20) | skilled on half A | also on half B | rate |
|---|---|---|---|---|
| synthetic-cohort | 59 | 2 | 0 | 0.0% |
| synthetic-placebo | 32 | 1 | 0 | 0.0% |
| synthetic-pooled | 91 | 5 | 0 | 0.0% |

Reported as-is, including the small denominators (2, 1, 5) — at this size
a single trader's classification would move the rate by 20–100 points, so
this figure is close to uninformative on its own even though it is
reported per the task's requirement. It does not reproduce the real run's
58.3–60.0% figures, but the denominators here are far too small to treat
that gap as established. Compare to the real run's 60.0% (cohort, n=20)
and 58.3% (placebo, n=12), both near or above Gómez-Cram's 44% external
reference.

---

## Part 3 — clustering (report only, not changed)

The harness treats every position as an independent unit at every level
where randomisation happens:
- Per-trader null (`sign_flip_null()` called per trader,
  `directional_skill_diagnostic.py:128`): flips only that trader's own
  positions, no cross-trader clustering question arises here by
  construction.
- **Pooled aggregate null** (`directional_skill_diagnostic.py:143`):
  concatenates every classifiable trader's positions in the arm and flips
  each position's sign **independently**, with no adjustment for traders
  sharing the same market (a market that resolves one way pushes every
  trader holding a position in it in a correlated direction). This is a
  plain per-position independent sign-flip, **not** the two-way
  trader × market clustered bootstrap used elsewhere in this project —
  e.g. `two_way_cluster_bootstrap()` in `scripts/layer0c_corrected_metric.py:173`
  and `scripts/layer0b_deconfound.py:257`, and referenced as the
  established convention in `scripts/trader_skill_metric_v2f.py:74`
  ("two-way trader x market clustered, cap5-weighted -- the same
  machinery"). The directional-skill harness does not use this machinery
  for its pooled test.
- **Split-half** (`directional_skill_diagnostic.py:186-187`): same
  per-position independent flip, applied within each trader's own half.

This is a factual code reference, not a fix — the harness is reported as
committed, unchanged.

---

## What this task did NOT determine

- **Whether (a) or (b) explains the 2026-09-05 result.** Not adjudicated,
  per the task's instruction — Oscar's call.
- **Why the pooled aggregate test disagrees in direction from the
  per-trader rate**, both in the real run (cohort clears 26% per-trader
  but fails its own aggregate bar) and structurally in general — not
  investigated here; flagged only, per the 2026-09-05 result doc's own
  Open Question 3.
- **Whether the reduced upper-region mass in Part 1 (39.5% vs ~50%
  expected) reflects a property of this specific population's real p-value
  distribution or something about how the empirical (1500-point) null
  discretises p-values near the boundary** — not investigated; the
  discrepancy between `raw_rate` (actual > null_p95) and
  `below_rate[0.05]` (p_value < 0.05) noted in Part 1 suggests some of this
  may be discretisation, but this was not traced further.
- **Whether the fixed reuse of `SEED=42` across every `sign_flip_null()`
  call (same starting RNG state per call, noted in Part 0) has any
  material effect on calibration independent of what Part 2 already
  shows.** Part 2's result was produced using this exact seeding,
  unmodified, and came back near the theoretical chance floor — but no
  separate ablation (e.g., re-running Part 2 with per-call-unique seeds)
  was attempted, since the task instructed no harness modification.
- **The clustering finding in Part 3 was not corrected or quantified** —
  only located and reported, per the task's explicit instruction not to
  attempt a fix.
- **No sampling was needed** (full 338-trader population ran in seconds),
  so the runtime-approval fallback path was not exercised.
- **No STOP condition was triggered**: per-trader p-values were persisted
  (Part 0), the harness accepted synthetic input with only the documented,
  reported data-substitution adaptation (no code change), full-population
  runtime was trivial, and no computed figure contradicted a number stated
  in the 2026-09-05 handover or its pre-registration (the 26.0%/19.2%/
  39.2%/29.4%/0.214/0.006/60.0%/58.3% figures quoted above all match the
  result doc verbatim).

---

**Bottom line, evidence only, no verdict**: fed a population that is
zero-skill by construction through the unmodified harness, classification
rates land at 4.1%/7.8%/5.6% (raw) and 0.0% (BH-adjusted) — close to the
test's own ~5% stated chance floor — and none of the three synthetic
populations' pooled aggregate statistics clear their own 95th-percentile
bar. The real 2026-09-05 placebo, run through the identical code path,
came back at 39.2%/29.4% and cleared its own aggregate bar at p=0.006.
Split-half persistence on the synthetic populations came back near zero,
against real-run figures of 58–60%, but on denominators (1–5) too small to
weigh heavily. The p-value distribution (Part 1) shows a shift extending
into the upper half of the distribution, not confined to the tail. The
pooled aggregate test does not account for trader × market clustering
(Part 3), unlike other machinery already established in this project.
These are the numbers; the interpretation is Oscar's.
