# Directional Skill Persistence Test — Run (Oscar-Approved 2026-09-06)

Executes
[2026-09-06-directional-skill-persistence-prereg.md](2026-09-06-directional-skill-persistence-prereg.md)
(trading-swarm `7743740`) **including** its dated amendment
(`a4b6494` — split primary/secondary success criterion, stratified
reporting by post-split position count). Approved by Oscar 2026-09-06.

**RESULT: STOPPED AT THE §8 PREREQUISITE GATE.** No real persistence
rate, aggregate test, or stratified breakdown was computed. Per the
pre-registration's own §8 sequencing and the task's explicit instruction,
this is reported and halted, not worked around. **No verdict on what to
do next — that is Oscar's.**

Reproducibility: `scripts/directional_skill_persistence_test.py`
(first-repo `ea1140e`), run with `--selfcheck`. Durable artifact:
`data/characterizations/directional_skill_persistence_20260906T191615Z.json`
(`status: "STOPPED_AT_S8_GATE"`).

---

## Pre-registered parameters, applied exactly as fixed

- Selection rule: BH-adjusted, `M_CHOSEN=10`, threshold not ranking (§1).
- `REPS=10,000` for post-split re-classification (§2) — applied via a
  documented runtime override of `directional_skill_diagnostic.REPS`
  (a module-level constant `per_trader_and_aggregate()`/`split_half()`
  read directly; Python resolves it from the module's own namespace at
  call time, so rebinding the attribute changes what the **unmodified**
  imported functions read, without editing the committed script's
  source). `MIN_SPLIT_HALF=20`, `ALPHA=0.05`, harness `SEED=42` untouched.
- Population: twice-classifiable = 753, cohort (N) = 146, comparison =
  607, PIT-legal classifiable = 5,732 — all read from the already-
  committed artifacts, verified to match exactly (no STOP triggered on
  this check).
- Control design (§3): no `match_control()` call anywhere in this
  script — the twice-classifiable population's two groups (real
  pre-split BH classification) are used directly, exactly as the
  pre-registration fixes.

---

## §8 hard gate: synthetic zero-skill null on the actual twice-classifiable population

**Construction**: real post-split positions for all 753 twice-
classifiable traders (`load_post_split_positions()`, imported unchanged;
28,563 positions), each position's side drawn **once** at random
(`SYNTH_SEED=20260906`, recorded), identical to Step 1's validated
method. Selfcheck (300-position resample) confirmed the
`flip × real_weighted_edge` identity exactly, 0 mismatches.

### Per-trader + aggregate classification under zero skill (REPS=10,000)

| group | n classifiable | raw skilled | raw rate | BH skilled | BH rate | aggregate skilled? |
|---|---|---|---|---|---|---|
| synthetic-cohort | 146 | 5 | 3.4% | **0** | **0.0%** | No (54.8th pctile) |
| synthetic-comparison | 607 | 30 | 4.9% | **0** | **0.0%** | No (80.8th pctile) |
| synthetic-pooled | 753 | 35 | 4.6% | **0** | **0.0%** | No (79.0th pctile) |

Raw rates sit close to the ~5% theoretical chance floor, consistent with
Step 1's calibration finding. **BH-adjusted classification is zero in
every group** — no false discoveries survive FDR control at this REPS
and population size (see Observation Log, item 1, for an unregistered
note on what this suggests about `REPS=10,000`'s effect on BH beyond
resolving the floor-pinning problem it was raised to fix).

### The S8 gate check itself: split-half persistence denominators

Replicates Step 1's own failed split-half method (`split_half()`,
imported unchanged, `MIN_SPLIT_HALF=20`), on the ACTUAL twice-classifiable
population instead of Step 1's small frozen 338-trader set:

| group | n eligible (≥20 positions) | classified skilled on half A (**denominator**) | persistence numerator | rate |
|---|---|---|---|---|
| synthetic-cohort | 98 | **6** | 0 | 0.0% |
| synthetic-comparison | 343 | **16** | 0 | 0.0% |
| synthetic-pooled | 441 | **15** | 1 | 6.7% |

**Compare to Step 1's failure**: cohort=2, placebo=1, pooled=5 (all on a
124-classifiable-trader population). This run's population is ~6x larger
(753 vs 124), and the denominators improved accordingly (6, 16, 15 vs 2,
1, 5) — **but the cohort-specific denominator (6) remains single-digit**,
the exact order of magnitude that defined Step 1's failure.

**Adequacy judgment, stated explicitly** (the pre-registration itself did
not fix a numeric floor, delegating this judgment per its own text: "if
that prerequisite step also produces denominators too small to trust...
this test does not proceed... until Oscar decides"): this run used
**`MIN_ADEQUATE_DENOMINATOR=10`** as the floor for treating a denominator
as usable, documented in the script rather than picked ad hoc — comparable
to `MIN_SPLIT_HALF=20`'s own order of magnitude and clearly above Step
1's demonstrated failure range (1–5). **The synthetic-cohort denominator
(6) falls below this floor.** Comparison (16) and pooled (15) clear it,
but the cohort-specific null — the one the real persistence cohort (N=146)
would actually need to be judged against — does not.

**Gate result: INADEQUATE. STOPPED, per the pre-registration's own
sequencing and the task's explicit instruction. Not adjusted, not
enlarged, not routed around by substituting the comparison or pooled
group's better-powered denominator for the cohort's own.**

---

## What was not computed (a direct consequence of the S8 stop, not a separate limitation)

- **The real persistence rate** (post-split BH-reclassification rate
  among the 146 real persistence-cohort traders) — not computed.
- **Its trader-clustered bootstrap CI** — not computed.
- **The primary axis (A1/A2/A3 vs. the in-house null) and secondary axis
  (B1/B2/B3 vs. Gómez-Cram 44%)** — neither evaluated; **no named outcome
  cell exists for this run.**
- **The §4 two-way trader × market clustered aggregate test** on the
  persistence cohort's real post-split positions — not computed.
- **The Amendment 2 stratified breakdown** (five bins, cohort vs.
  comparison) — not computed; the activity-imbalance concern that
  motivated it remains unaddressed by data, though item 2 in the
  Observation Log below reports an incidental, unregistered signal
  consistent with it, seen at the S8 stage.

**All of the above are exactly what the pre-registration's own §8
sequencing withholds until the gate clears.** This is not an incomplete
run — it is the run's correct, pre-specified stopping point.

---

## What was not determined

- **Whether `MIN_ADEQUATE_DENOMINATOR=10` is the right floor.** No
  standard threshold was specified anywhere upstream; 10 was chosen and
  documented in this run's script, not derived from a formal power
  calculation. A different, defensible choice (e.g., a floor of 5, or of
  20 matching `MIN_SPLIT_HALF` itself) could move the gate result —
  reported so Oscar can judge the choice directly rather than accept it
  silently.
- **Whether a larger REPS, a different (non-split-half) null construction,
  or simply waiting for more post-split data to accrue would resolve the
  cohort's specific denominator problem.** Not investigated — the task
  explicitly forbids adjusting the construction to enlarge denominators
  within this run; any such change is a decision for Oscar, not this
  script.
- **Whether the `null_persistence_rate_cohort_denominator_form` figure
  reported alongside the gate** (the synthetic-cohort's own post-split
  BH-skilled rate, 0/146, CI degenerate at 0.0) **would itself have served
  as an adequate null even though the split-half denominator did not** —
  reported in the artifact for completeness, but the pre-registration's
  own text frames the split-half method specifically as what needed
  re-establishing (it explicitly names Step 1's *split-half* persistence
  check as the failed attempt), so this run treated the split-half
  denominator as the controlling gate check, not this alternative figure.
  Whether that reading is the correct one is not this script's call to
  make unilaterally — noted for Oscar.
- **Whether the BH=0 result at REPS=10,000 (Observation Log item 1)
  reflects a genuine, intended tightening from raising REPS, or an
  artifact worth separately investigating before this test is re-approved
  at a later date** — flagged, not resolved.

---

## OBSERVATION LOG

*Per the task's explicit rules: every entry below is UNREGISTERED and
UNTESTED. None of them is a finding. Nothing here changes, qualifies,
softens, or strengthens the §8 gate result above — that result stands as
computed, full stop. No additional analysis was run to develop any entry
below; each reports only what was directly visible in the course of the
pre-registered §8 computation.*

**This log is necessarily sparse.** Because the run stopped at the §8
gate, none of the REAL post-split classification, persistence rate,
aggregate test, or stratified breakdown exists — most of the task's
suggested watch-points (persistence concentration by category/market
count/activity span/entry price; stratification-bin patterns; execution-
dimension signals distinct from direction) have no data to observe them
in, from this run. What follows is limited to what the §8 computation
itself surfaced.

1. **BH-adjusted classification was exactly zero in all three synthetic
   groups (cohort, comparison, pooled) at `REPS=10,000`**, despite raw
   rates near the expected ~5% chance floor (3.4–4.9%). By contrast, the
   original 2026-09-05 test (`REPS=1,500`) found BH rates of 19.2%
   (cohort) and 29.4% (placebo) on populations selected similarly. This
   might mean raising `REPS` from 1,500 to 10,000 did more than resolve
   the floor-pinning problem it was raised to fix (§2's justification) —
   it may have substantially tightened the empirical 95th-percentile
   threshold's precision, reducing Monte-Carlo-noise-driven false
   positives that a coarser (1,500-rep) null was more prone to. **What
   would settle it**: a pre-registered check running the SAME zero-skill
   synthetic construction at both `REPS=1,500` and `REPS=10,000` on an
   identical population, holding everything else fixed, to isolate
   whether the BH-rate drop is a `REPS` effect specifically (this is new
   computation, not run here).
2. **Split-half eligibility (≥20 post-split positions) differs by group
   in the direction Amendment 2 already flagged**: 98/146 (67.1%) of the
   cohort vs. 343/607 (56.5%) of the comparison group were split-half
   eligible. This is a second, independent surface of the same activity
   imbalance the population count already established (median 28.5 vs.
   22.0 post-split positions) — not a new finding, but a confirmation
   that it shows up structurally even in the prerequisite-gate
   computation, before any real classification was attempted. **What
   would settle whether it matters for the real test**: Amendment 2's own
   stratified breakdown, once the §8 gate clears.
3. **No signal on the execution dimension (entry timing, market age at
   entry) was observed** — this script does not load or compute either
   quantity anywhere; `load_post_split_positions()`'s output carries
   `entry_ts` but no market-age-at-entry derivation, and none was
   computed here. Components 2 and 3 of the canonical skill metric
   design (absolute/relative earliness) remain exactly as untested as
   `MASTER_HANDOVER_2026-09-05.md` §7 already states. **What would settle
   it**: those components' own, separately pre-registered tests — not
   attempted or sketched here.
4. **No trader-level property observable prospectively was identified**
   in this run, because no real persistence outcome exists yet to
   correlate one against. **What would settle it**: once the §8 gate
   question is resolved (by Oscar, on a larger dataset, a different null
   construction, or an accepted denominator floor) and a real persistence
   rate is computed, a natural next unregistered look — not run here —
   would be whether persistence co-occurs with any pre-split-observable
   trait (category mix, position-count tier, activity span) among the
   146 cohort members specifically.
