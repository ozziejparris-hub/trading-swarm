# Directional Skill Persistence — Pre-Registration

**PRE-REGISTRATION ONLY. Compute nothing, produce no result, write no
analysis code, run no script.** Fixes the method before any computation
exists — the same discipline as
`2026-09-05-directional-skill-prereg.md` (trading-swarm `cf88f8a`) and the
relevance-classifier validation gate sets: this document is committed with
**no results in the tree**, so git history itself proves the criterion
preceded the result.

Context this pre-registration depends on, all already committed:
[2026-09-06-directional-skill-null-calibration.md](2026-09-06-directional-skill-null-calibration.md)
(Step 1 — the harness's per-trader classification is well-calibrated at
~5% under true zero skill),
[2026-09-06-directional-skill-discrepancy-pit-pool-power.md](2026-09-06-directional-skill-discrepancy-pit-pool-power.md)
(Steps 2–3 — the PIT-legal pre-split pool and its power characteristics),
[2026-09-06-directional-skill-exploratory-custody.md](2026-09-06-directional-skill-exploratory-custody.md)
(Part 1 of this arc — the 1B survivorship asymmetry and the
`match_control()` nondeterminism finding, both binding on the control
design below).

---

## The question, fixed first because it is not an implementation detail

**Does directional skill, measured PIT-legally before `T_split`, persist
out-of-sample? Direction in, direction out — NOT direction in, edge out.**

Edge is deliberately excluded from this design. The 2026-09-06 exploratory
figures (by-product of the Step 3 power estimate, NOT pre-registered,
persisted as exploratory in `directional_skill_pit_exploratory_result`)
already indicate directional selection does not concentrate edge — every
group's minimum detectable effect (2.1–2.9pp) exceeds both category cost
floors, and the matched placebo outperformed the cohort's point estimate
in 3 of 4 comparisons. Testing edge persistence on top of direction
persistence in the same pass would repeat the **one-artifact-two-questions
failure this project has now hit five-plus times** (named explicitly by
the task commissioning this document). This test asks one question only.

---

## 1. Selection rule and threshold — fixed now

**Primary selection rule: BH-adjusted classification, not raw.**
Part B found the pre-split raw rate (26.1%) sits close to what every
population tested in this arc has shown regardless of selection —
cohort, placebo, and the full pre-split-unselected population all cluster
in a similar 20–40% range under the raw rule. A raw-rate selection would
not usefully discriminate; it would select roughly one in four of nearly
any population passed through this harness. **BH-adjusted (`bh_correction()`,
α=0.05) is the selection rule** — the project's own established
"required companion, not optional" convention (2026-09-05 prereg §13),
and the more conservative choice.

**Minimum position count: `M_CHOSEN = 10`, reused unchanged.** Not
re-derived, not raised or lowered to change the size of the resulting
pool — same convention as every prior pass in this arc (v2d/v2f/Track
2/decay-prereg/2026-09-05 directional test/Part B).

**Ties at the permutation floor: this is a THRESHOLD rule, not a
ranking, and here is why.** Part B found only **1,340 distinct p-values
across 5,732 classifiable traders**, with **12.5% pinned exactly at the
permutation floor** (`p = 1/1501 = 0.000666`, i.e. their actual statistic
exceeded all 1,500 null draws). A ranking of these traders against each
other would report false precision — the harness genuinely cannot
distinguish among floor-pinned traders at this permutation count. **The
selection is binary (BH-significant / not), not an ordered list.** Every
BH-significant trader is treated identically as "meets the pre-split
directional-skill bar," regardless of how far past the floor their
statistic sits.

---

## 2. Permutation count for the out-of-sample re-classification — fixed now, decided blind

**The already-completed pre-split classification (Part B) used
`REPS=1,500` and is NOT re-run or altered by this decision** — that
result stands as computed.

**For the NEW post-split re-classification step (has this same trader,
now restricted to their post-split positions, ALSO classify as
directionally skilled?), this pre-registration fixes `REPS = 10,000`,
raised from 1,500.** Justification, stated before any post-split number
has been computed:
- Directly addresses the floor-pinning problem quantified in Part B
  (12.5% pinned, only 1,340 distinct p-values at 1,500 reps) — a higher
  rep count gives finer resolution to distinguish among traders whose
  post-split statistic would otherwise also pin at a coarse floor.
- Matches Gómez-Cram's own original convention (10,000), which the
  project's `REPS=1,500` choice deliberately departed from for
  consistency with `v2d`/`v2f`/Track 2 (2026-09-05 prereg §"Resampling
  parameters") — for a test whose own external benchmark comparison is
  Gómez-Cram's split-half figure (§8 below), matching their resolution
  is directly relevant, not just conventional.
- Computational cost is trivial at this population's size (a few thousand
  traders at most, milliseconds each per Step 1–3's measured runtimes) —
  raising `REPS` is not chasing power the population cannot afford.

**This is a power decision made blind, not a result-chasing one**:
it is fixed here, in a document with no post-split number anywhere in it,
specifically to forestall exactly the pattern the 2026-09-05 prereg's
§17 already named as unacceptable ("a different significance bar, a
different minimum count chosen after seeing a disappointing result").
`REPS=10,000` is not permitted to be lowered back toward 1,500, or raised
further, after any post-split figure exists.

---

## 3. Control / comparison design — fixed to account for 1B and the match_control() finding

**AMENDED 2026-09-06 — see the dated amendment section at the end of
this document for a stratified-reporting fix addressing an activity-level
imbalance found between the persistence cohort and comparison group
(median 28.5 vs. 22.0 post-split positions). The text below is the
ORIGINAL, un-amended §3, preserved as written; the amendment adds
stratified reporting on top of it, it does not replace anything below.**

**The primary design does not use `match_control()` and does not build a
matched-pair placebo. It conditions on post-split survival FIRST, then
compares within that single survival-consistent population — eliminating
1B's asymmetry by construction, and sidestepping the `match_control()`
nondeterminism entirely, because that function is not called.**

Concretely, fixed now:
1. Start from Part B's full PIT-legal classifiable population (5,732
   traders, `n ≥ M_CHOSEN` pre-split, tape_end-anchored via
   `backtest_window_sql()`).
2. Restrict to traders who ALSO have `≥ M_CHOSEN` **post-split** resolved
   positions (a stricter bar than Part B's own "any post-split position"
   survival definition, chosen because this test needs both halves
   individually classifiable, not merely non-empty) — call this the
   **twice-classifiable population**, size to be determined only when
   this test runs.
3. Within the twice-classifiable population only, split by the PRE-split
   BH-classification (§1): **persistence cohort** (pre-split BH-skilled)
   vs. **comparison group** (pre-split not BH-skilled, everyone else in
   the twice-classifiable population).

**This directly repairs 1B**: both groups are now drawn from the
identical survival-conditioned population — neither is implicitly
pre-filtered on an outcome the other was not. There is no artificial
matching step, hence no dependence on `match_control()`'s greedy
nearest-neighbour matcher and no exposure to its `PYTHONHASHSEED`-driven
nondeterminism (1D finding).

**A secondary, optional, explicitly-gated comparison**: if a profile-
matched (position count / market breadth / activity span) comparison
group is later wanted as a robustness check alongside the primary
survival-conditioned design, it **may only use `match_control()`, or any
other set-based greedy matcher, after that function is made
deterministic** — at minimum, replacing `list(some_set)` with
`sorted(some_set)` before shuffling/iterating, and verifying determinism
by re-running the construction in a fresh process (exactly the check that
surfaced the nondeterminism in Part 1D) before any number built on it is
treated as a result. This is a **precondition on the secondary
comparison being run at all**, not a task performed by this document.

---

## 4. Aggregate test — trader × market clustering, fixed now

**The pooled/aggregate significance test for the persistence cohort's
post-split positions WILL use two-way trader × market clustered
bootstrap** (the `weighted_two_way_gap_bootstrap()` /
`weighted_pair_table()` / cap5-weighting machinery already established
elsewhere in the project — `layer0b_deconfound.py`, `layer0c_corrected_metric.py`,
`trader_skill_metric_v2f.py`'s `measure_oos()`), **not** the existing
directional harness's naive per-position-independent pooling (Part 3 of
the Step 2/3 doc found `per_trader_and_aggregate()`'s own aggregate test
treats every position as independent, no clustering, even when many
positions across many traders share the same market).

**The per-trader classification itself is unchanged** — same sign-flip
method (`sign_flip_null()`, `classify()`), same code path, applied to
post-split positions instead of pre-split ones. Cross-trader clustering is
not a per-trader concern (each trader's own null is already computed from
only their own positions); it specifically affects the pooled statistic
across many traders, which is where the fix is scoped.

**Explicit consequence, stated so it is not mistaken for an error
later**: because the aggregate methodology differs from the existing
harness, **this test's aggregate figure will NOT be comparable to the
2026-09-05 pair** (placebo p=0.006 / cohort p=0.214, both computed via the
naive independent-position pooling). Different inference machinery,
different quantity — not a discrepancy to reconcile if the numbers look
different in kind.

---

## 5. SEED handling — fixed now

**`SEED = 42` is retained, re-seeded fresh at every call site, exactly as
the existing harness already does** (Step 1's carried-forward caveat,
respected not fixed, per that document's own instruction). This
preserves continuity/comparability with every prior sign-flip pass in
this arc (`v2d`/`v2f`/Track 2/decay-prereg/`directional_skill_diagnostic.py`)
and is not altered here.

**The `match_control()` `PYTHONHASHSEED` nondeterminism (1D) does not
affect the primary design**, because §3 above does not call
`match_control()`. It becomes relevant only if the optional secondary
matched comparison is later added, and §3 already fixes the precondition
(deterministic sort, verified by a fresh-process re-run) before that
happens.

---

## 6. Success criterion — stated numerically

**AMENDED 2026-09-06 — see the dated amendment section at the end of
this document. The original combined (AND) criterion below is PRESERVED
AS WRITTEN for the record, but is SUPERSEDED by the amendment's split
primary/secondary criteria — use the amendment's outcome enumeration,
not the one below, when this test is run.**

Let **N** = size of the persistence cohort (pre-split BH-skilled traders
within the twice-classifiable population, §3) — unknown until this test
runs, not estimated here.

**Persistence rate** = (number of the N traders whose POST-split
positions ALSO classify as BH-significant, same rule as §1, `REPS=10,000`,
§2) / N.

A **95% CI on the persistence rate** is computed via a trader-clustered
bootstrap over the N cohort members (resampling traders with replacement,
consistent with the two-way clustering already fixed for the aggregate
test in §4, applied here to the persistence-rate statistic itself).

**Outcomes, enumerated in advance, mirroring the 2026-09-05 prereg's own
§14–17 structure**:

1. **Persistence established**: the persistence-rate CI lies entirely
   above the established synthetic-null persistence rate's own CI (§8 —
   non-overlapping, mirroring the 2026-09-05 test's own separation
   criterion of requiring disjoint bars, not just differing point
   estimates) AND the point estimate is at or above Gómez-Cram's 44%
   external reference. → Direction classified pre-split carries genuine
   out-of-sample information. **This does not establish tradeability or
   edge** (§7).
2. **No persistence**: the persistence-rate CI overlaps the established
   synthetic-null CI. → Directional classification pre-split carries no
   out-of-sample information at this test's resolution. **A legitimate,
   valuable, reportable finding**, not a failure, closing the
   retrospective directional-skill question in its entirety if it obtains
   — mirroring the 2026-09-05 prereg's own §16 framing.
3. **Partial / inconclusive**: the persistence-rate CI is disjoint from
   the synthetic-null CI but the point estimate sits below Gómez-Cram's
   44% (or vice versa — CI overlaps null but point estimate is high with
   very wide bounds). → Reported as inconclusive, exactly as computed,
   not resolved by picking one number. Per the 2026-09-05 prereg's own
   §17 rule, adopted here unchanged: **re-running with different
   parameters after seeing a disappointing result is not an acceptable
   resolution.**
4. **Reversal**: the persistence rate is significantly BELOW the
   established synthetic-null rate. → Reported as-is, not adjusted or
   hidden, mirroring the 2026-09-05 result's own "wrong direction"
   framing when the placebo outperformed the cohort.

---

## 7. What this test CANNOT establish — stated explicitly

- **Persistence of direction says nothing about tradeability.** Edge is
  excluded from this design by construction (see "The question" above).
  Even Outcome 1 (persistence established) would not indicate a
  profitable or tradeable signal — the 2026-09-06 exploratory figures
  already show a much larger, better-powered directional cohort's minimum
  detectable effect (2.1–2.9pp) exceeds both category cost floors
  (geopolitics up to 1.0pp, elections up to 2.0pp). A persistent
  direction with an edge too small to clear transaction costs is not
  tradeable; this test cannot and does not speak to that distinction.
- **Not a causal test.** A positive result would not explain *why* some
  traders' direction persists (skill, correlated information sources,
  category-wide structural bias — as the 2026-09-05 result document's own
  Outcome 2 discussion speculated but did not establish) — purely
  descriptive/classificatory.
- **Does not extend to the consensus test, the copy-trade decay ladder,
  or any other pre-registered-but-unrun component from prior arcs** — out
  of scope here, exactly as the 2026-09-05 prereg scoped itself.
- **Does not, by itself, revalidate the harness's calibration at this
  test's specific new parameterisation** (post-split population, `REPS=10,000`).
  Step 1 established the harness's per-trader classification is
  well-calibrated at ~5% under true zero skill for the ORIGINAL
  parameterisation (`REPS=1,500`, the frozen 338-trader cohort/placebo
  population). Whether that calibration still holds at `REPS=10,000` on
  the much larger twice-classifiable population has not been checked —
  see §8's prerequisite.

---

## 8. Gómez-Cram external benchmark, and the unestablished in-house null

Gómez-Cram's own split-half persistence figure: **44%**, cited throughout
this arc as the external reference (2026-09-05 result document: both
populations there landed at 58.3%/60.0%, "somewhat above it," on
denominators of 12/20 explicitly flagged as too small to weigh heavily).

**The 2026-09-06 null calibration (Step 1) attempted a zero-skill
split-half persistence check and could NOT establish a clean null**:
its synthetic-zero-skill population's split-half-eligible subsample
produced denominators of **1, 2, and 5** across the three groups tested
(synthetic-cohort, synthetic-placebo, synthetic-pooled) — far too small
to report a stable chance-floor persistence rate. **This test's own
persistence null therefore remains unestablished.**

**Establishing it is a PREREQUISITE for this test, not a parallel task.**
Reasoning: Step 1's calibration ran on the frozen 338-trader
cohort/placebo population (124 classifiable), which is why its
split-half subsample was so small. Part B's PIT-legal population is
**far larger** (5,732 classifiable pre-split), and this test's own
twice-classifiable population (§3) will be smaller than that but likely
still substantially larger than 338. **The same synthetic-zero-skill
construction method validated in Step 1** (real positions, each
position's side drawn once at random, seed recorded, run through the
identical harness unmodified) **applied to this test's own
twice-classifiable population** should produce comfortably larger
denominators and a usable in-house persistence null — but this has not
been attempted, checked, or estimated in any way here. **Without it, a
real persistence-rate result could only be judged against Gómez-Cram's
external figure (a different population, different market, different
methodology) — not against this test's own chance floor**, and Outcome 1
above explicitly requires clearing BOTH. **Sequencing, fixed now**: the
synthetic-null-on-the-actual-twice-classifiable-population step must be
completed and its own denominators checked for adequacy BEFORE the real
persistence number is computed — if that prerequisite step also produces
denominators too small to trust (as Step 1's did), that is reported and
this test does not proceed to computing a real persistence rate until
Oscar decides how to resolve it, per this project's standing rule against
computing decision-carrying numbers without an established null.

---

## Reproducibility

- **Intended script** (not created by this pre-registration, matching the
  2026-09-05 prereg's own convention of naming the script before it
  exists): `scripts/directional_skill_persistence_test.py`, to be
  committed alongside the eventual result, importing
  `per_trader_and_aggregate()`, `sign_flip_null()`, `classify()`,
  `bh_correction()` unchanged from `directional_skill_diagnostic.py`, and
  `weighted_two_way_gap_bootstrap()` / `weighted_pair_table()` /
  `WEIGHT_FNS['cap5']` unchanged from `trader_skill_metric_v2d.py`/`v2f.py`
  for the §4 clustered aggregate.
- **Seed**: `42`, re-seeded per call site, unchanged (§5).
- **Reps**: pre-split classification `1,500` (already computed, Part B,
  not re-run); post-split re-classification `10,000` (§2, fixed here).
- **Selection rule**: BH-adjusted, `M_CHOSEN=10`, threshold not ranking
  (§1).
- **Population**: Part B's PIT-legal classifiable population, restricted
  to the twice-classifiable subset (§3) — to be derived from
  `data/characterizations/directional_skill_pit_legal_pool_20260906T160303Z.json`
  plus a fresh post-split position count, not yet computed.
- **Durable artifact**: `data/characterizations/directional_skill_persistence_<UTC-timestamp>.json`
  — per-trader pre-split and post-split classification, the persistence
  rate and its clustered-bootstrap CI, the twice-classifiable population
  membership (trader-level, per the Objective-1 pattern named in 1D —
  not aggregates only), the prerequisite synthetic-null result (§8) and
  its own denominators, and this run's git commit.
- **`--selfcheck`**, consistent with `trader_skill_metric_v2*` convention.
- **Prerequisite gate**: §8's synthetic-null-on-the-actual-population step
  must run and its denominators checked before the real persistence
  number is computed — sequenced as one script with an early-exit gate,
  or two scripts run in sequence, either is acceptable; not run at all
  until Oscar approves this document.

---

## Open questions (explicitly deferred — not answered by this document)

1. What N (persistence cohort size) and what twice-classifiable
   population size actually result from §3's restriction — unknowable
   without computing. **RESOLVED 2026-09-06 (first-repo `1d34ced`,
   counts only, no post-split classification): twice-classifiable
   population = 753, N (persistence cohort) = 146, comparison group =
   607. A post-split-activity imbalance was found between the two groups
   (median 28.5 vs. 22.0 positions) — addressed by the stratified-
   reporting amendment at the end of this document, not by any
   adjustment to the population itself.**
2. Whether §8's prerequisite synthetic-null step will itself produce
   adequate denominators on the twice-classifiable population, or repeat
   Step 1's small-denominator problem at a different scale.
3. Whether the harness's calibration (Step 1's ~5% finding) holds
   unchanged at `REPS=10,000` on this new population — not re-checked,
   only assumed continuous with Step 1's finding at the original
   parameterisation.
4. Whether a secondary matched-control comparison (§3) will be built at
   all, and if so, whether `match_control()`'s nondeterminism will be
   fixed by the time it is — both left to a future decision, not decided
   here.

---

---

## Amendment 2026-09-06 — split success criterion (§6) + activity-imbalance stratification (§3)

Made in
`2026-09-06-external-dataset-scoping-and-prereg-amendment.md`, alongside
an unrelated read-only scoping question (external dataset — verdict: it
cannot contribute to this test; see that document). **Both amendments
below are BLIND: neither references, depends on, or was informed by any
post-split classification, p-value, persistence rate, or other
outcome-dependent quantity.** Both are justified entirely from counts
already committed before this amendment — N=146 (first-repo `1d34ced`)
and the post-split position-count *distribution* (a structural count, not
an outcome) from the same commit. The original §3 and §6 text above is
preserved, not deleted; this section is additive and, where it conflicts
with the original §6 outcome enumeration, supersedes it as stated at each
pointer above.

### Amendment 1 — §6, success criterion split into primary + secondary

**Why now, on the record before any result exists**: N=146 was unknown
when this document was drafted — its own Open Question 1. Now that it is
known, a standard closed-form approximation shows the original §6's
combined AND-criterion (CI clears the in-house null *and* the point
estimate is at/above Gómez-Cram's 44%) has a foreseeable failure mode at
this specific N: for a persistence rate near 40%, `SE ≈ √(p(1-p)/N) ≈
√(0.4·0.6/146) ≈ 0.0405`, giving a 95% CI half-width of
`≈ 1.96 × 0.0405 ≈ 0.079` — **≈8 percentage points**, wide enough to
straddle 44% routinely even when the point estimate clearly clears the
in-house chance floor. Under the original wording, such a result would
fall to old-Outcome-3 ("inconclusive") — understating a result that is
actually decisive against this test's own null, merely ambiguous against
a *different population's* external benchmark. This reasoning is fixed
here, blind, precisely so a later result cannot be read as having
motivated the split.

**The two comparisons, reported separately, from here forward:**

**(A) PRIMARY — persistence established against this test's own null**
(§8's synthetic-null prerequisite). A CI-vs-CI relationship between the
persistence-rate CI and the synthetic-null CI is exhaustively one of
three mutually exclusive states — no fourth state is possible, so no
"inconclusive" bucket is needed on this axis:
- **A1 — established**: persistence-rate CI lies entirely above the
  synthetic-null CI (disjoint, mirroring the 2026-09-05 test's own
  separation criterion).
- **A2 — no persistence**: the two CIs overlap. Directional
  classification pre-split carries no out-of-sample information at this
  test's resolution — a legitimate, valuable, reportable finding, not a
  failure (unchanged from the original §6 Outcome 2).
- **A3 — reversal**: persistence-rate CI lies entirely below the
  synthetic-null CI. **Kept intact, unchanged in substance from the
  original §6 Outcome 4** — reported as-is, not adjusted or hidden.

**(B) SECONDARY — relative to the Gómez-Cram 44% external benchmark**
(§8). Always computed and reported alongside (A), never in place of it;
decision-relevant only when paired with A1, since a result that does not
even clear its own in-house null gains nothing from comparing favourably
to an unrelated population's benchmark:
- **B1 — at or above benchmark**: persistence-rate CI's lower bound is
  at or above 44%.
- **B2 — UNRESOLVED**: the CI straddles 44%. **This is the amendment's
  central fix — B2 is reported as unresolved relative to this specific
  external comparison, NOT as "inconclusive" for the test as a whole,
  and NOT as a failure.** The two populations and methodologies differ
  regardless (Gómez-Cram's own population, their 10,000-permutation
  count vs. this test's own construction) — B2 at N=146 is an expected,
  named outcome, not a surprise to be explained away later.
- **B3 — below benchmark**: the CI's upper bound is below 44%.

**Six named combinations, each stated in advance:**

| | A1 (established) | A2 (no persistence) | A3 (reversal) |
|---|---|---|---|
| **B1 (≥44%)** | Strongest form: persistence established, matches Gómez-Cram. | Reported for context only; B-axis is not decision-relevant without A1. | Reported for context only. |
| **B2 (unresolved)** | Persistence established against this test's own null; external-benchmark comparison unresolved at this N — **not inconclusive**, a real finding with a flagged resolution limit. | Not decision-relevant. | Not decision-relevant. |
| **B3 (<44%)** | Persistence established against this test's own null; below Gómez-Cram's population rate. Still a real, primary-criterion-clearing finding. | Not decision-relevant. | Not decision-relevant. |

Per the original §6's own rule, retained unchanged: **re-running with
different parameters after seeing a disappointing result on either axis
is not an acceptable resolution.**

### Amendment 2 — §3, stratified reporting for the post-split activity imbalance

**Finding motivating this fix** (first-repo `1d34ced`, counts only): the
persistence cohort (146 traders) trades more post-split than the
comparison group (607 traders) — median 28.5 vs. 22.0 post-split
positions, mean 45.4 vs. 36.1. More positions per trader means more
power to clear the per-trader significance bar for the same underlying
tendency, so a persistence-rate difference between the two groups could
be manufactured by activity level alone rather than by any real
difference in directional persistence.

**Fixed now, before any computation:**
- The persistence rate **WILL be reported stratified by post-split
  position count**, using five pre-specified bins, for both the
  persistence cohort and the comparison group:
  **`[10,14)`, `[14,23)`, `[23,46)`, `[46,83)`, `[83,∞)`.**
- **Bin justification**: boundaries are taken directly from the
  already-committed, pooled twice-classifiable population's post-split
  count distribution (`directional_skill_twice_classifiable_population_20260906T170928Z.json`:
  median 23, p25 14, p75 46, p90 82.8, max 359; floor 10 by construction,
  since `M_CHOSEN=10` is the population's own minimum) — a structural
  count computed with no direction or outcome information, so choosing
  bins from it is blind. Quartile-spaced from the floor through p75
  (`[10,14)`, `[14,23)`, `[23,46)`, three roughly equal-population bins),
  then finer through p90 (`[46,83)`) and a final open-ended tail bin
  (`[83,∞)`, capturing up to the observed max of 359) — the tail is where
  the activity-power effect would show up most sharply, so it is isolated
  rather than folded into a single "high" bucket.
- **The headline (pooled) persistence rate is reported alongside the
  stratified breakdown, never instead of it** — both numbers appear in
  the same result, neither substitutes for the other.
- **If the stratified breakdown shows the cohort/comparison difference is
  confined to the high-activity strata (`[46,83)`, `[83,∞)`), that is
  reported as such and NOT resolved by picking the pooled figure.** No
  weighting, re-balancing, or activity-adjustment is added to the
  persistence-rate calculation itself — stratified reporting makes the
  issue visible without pre-judging whether it matters, per the task's
  explicit instruction that a correction would be a modelling choice made
  without knowing whether one is needed.

---

**No verdict on whether to proceed to this test is stated here — that is
Oscar's, after reading this document.**
