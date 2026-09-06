# Directional Skill Persistence Test — Real Result (A1×B2)

Runs [2026-09-06-directional-skill-persistence-prereg.md](2026-09-06-directional-skill-persistence-prereg.md)
(trading-swarm `7743740`) **including both** dated amendments: the
2026-09-06 amendment (`a4b6494`, split primary/secondary criterion,
stratified reporting) and **Amendment 2026-09-06b** (`7ae1845`, §8 null
established by an alternative route, fixed at 0%). Part 1 of this task
(the amendment) was committed first, with no results in the tree, per
the pre-registration's own git-provable-ordering discipline; Part 2 (this
result) is a separate, later commit.

**RESULT: named outcome cell A1×B2.** Persistence is established against
this test's own (fixed) null. The comparison against Gómez-Cram's 44%
external benchmark is unresolved (CI straddles it) — not a failure, an
expected outcome at this N per the amendment's own reasoning. **No
verdict on what to do next — that is Oscar's.**

Reproducibility: `scripts/directional_skill_persistence_test.py`
(first-repo `6e69bc8`, updated from the S8-gate version at `ea1140e` to
use the amended fixed null), run with `--selfcheck`. Durable artifact:
`data/characterizations/directional_skill_persistence_20260906T195734Z.json`
(`status: "COMPLETED"`).

---

## The null used (Amendment 2026-09-06b, verified not recomputed)

Per the amendment, this run does **not** attempt the S8 gate's originally
specified split-half method again. It verifies, via `--selfcheck`, that
the cited REPS-effect artifact (first-repo `6dc0bf5`) still shows
**BH-adjusted classification = 0 in all 36 tested cells** (3 independent
synthetic draws × 4 REPS values × 3 groups) — confirmed, 0/36 non-zero —
then uses the fixed null point **0.0** directly for the primary-axis
comparison. No synthetic construction, no `split_half()` call, no
`MIN_ADEQUATE_DENOMINATOR` gate appears in this run.

---

## Pre-registered parameters, applied exactly as fixed

- Selection rule: BH-adjusted, `M_CHOSEN=10` (§1). `REPS=10,000` for
  post-split re-classification (§2), applied via the same documented
  `directional_skill_diagnostic.REPS` module-attribute override as the
  first S8-gate attempt — source file unedited. `SEED=42` (harness,
  re-seeded per call site), `BOOTSTRAP_SEED=20260907` (new, for the
  trader-clustered persistence-rate CI, S6) — both recorded.
- Population: twice-classifiable = 753, cohort (N) = 146, comparison =
  607, PIT-legal classifiable = 5,732 — verified against the committed
  artifacts, exact match, no STOP triggered.
- Control design (§3): no `match_control()` call anywhere — the two
  groups are the real, pre-split-BH-classification-defined subsets of the
  twice-classifiable population, exactly as fixed.
- Aggregate test (§4): two-way trader × market clustered bootstrap
  (`weighted_two_way_gap_bootstrap()`/`weighted_pair_table()`/
  `WEIGHT_FNS['cap5']`, unchanged, `reps=GATE_REPS_LOCAL=1500`,
  `seed=42` — the established v2f convention for this specific
  machinery, not overridden).

---

## Real post-split classification

| group | n classifiable | raw skilled | raw rate | BH skilled | BH rate |
|---|---|---|---|---|---|
| persistence-cohort | 146 | 63 | 43.2% | **54** | **37.0%** |
| comparison-group | 607 | 154 | 25.4% | **113** | **18.6%** |

## Persistence rate + trader-clustered bootstrap CI

| | point | CI | n |
|---|---|---|---|
| **persistence rate (cohort)** | **0.3699** | **[0.2945, 0.4521]** | 146 |
| comparison-group post-split BH rate, context | 0.1862 | [0.1549, 0.2175] | 607 |

## Primary axis (A1/A2/A3, vs. the fixed null of 0%)

**A1 — established.** Real CI lower bound (0.2945) is strictly greater
than the fixed null point (0.0) — the CI excludes the null. Per Amendment
2026-09-06b, A3 (reversal) is structurally unreachable under this null
(a bounded proportion cannot fall below a null fixed at the statistic's
own floor) and was never a live possibility for this run, by construction
of the null, not by any property of the real data.

## Secondary axis (B1/B2/B3, vs. Gómez-Cram's 44%)

**B2 — UNRESOLVED.** The real CI `[0.2945, 0.4521]` straddles 0.44 (lower
bound below it, upper bound above it). Per the 2026-09-06 amendment's own
framing: this is **not inconclusive for the test as a whole and not a
failure** — it is a real, primary-criterion-clearing finding (A1) whose
comparison to a *different population's* external benchmark happens to
be unresolved at this N. Exactly the outcome the amendment's own
closed-form CI-width estimate (~8pp at N≈146, a rate near 40%) predicted
before any result existed.

## Named outcome cell: **A1 × B2**

Per the amendment's six-cell table: *"Persistence established against
this test's own null; external-benchmark comparison unresolved at this
N — not inconclusive, a real finding with a flagged resolution limit."*

---

## Aggregate test (§4) — two-way trader × market clustered bootstrap

**Explicitly NOT comparable to the 2026-09-05 p=0.006/p=0.214 pair**
(different inference machinery, per §4).

| group | point_gap | CI | n_pairs |
|---|---|---|---|
| persistence-cohort | 0.0115 | [-0.0151, 0.0362] | 3,025 |
| comparison-group, context | **0.0210** | **[0.0044, 0.0376]** | 10,827 |

**The comparison group's aggregate CI excludes zero (significant,
positive); the persistence cohort's does not.** This is the same
"wrong direction" pattern already on record throughout this arc (the
2026-08-15 result of record's placebo, the 2026-09-05 directional test's
placebo, and the 2026-09-06 exploratory figures all showed the
non-selected comparison group performing as well as or better than the
selected group on some measure). Reported as computed, not adjudicated.

---

## Stratified breakdown (Amendment 2, bins fixed in advance)

| bin | cohort n | cohort BH-skilled | cohort rate | comparison n | comparison BH-skilled | comparison rate |
|---|---|---|---|---|---|---|
| [10,14) | 27 | 11 | 40.7% | 148 | 29 | 19.6% |
| [14,23) | 29 | 13 | 44.8% | 164 | 29 | 17.7% |
| [23,46) | 43 | 14 | 32.6% | 145 | 26 | 17.9% |
| [46,83) | 27 | 10 | 37.0% | 94 | 17 | 18.1% |
| [83,∞) | 20 | 6 | 30.0% | 56 | 12 | 21.4% |

**The pooled headline rate (37.0% cohort / 18.6% comparison) is reported
alongside this breakdown, not instead of it, per the amendment.**

**Per Amendment 2's own explicit instruction**: the cohort/comparison gap
is checked against whether it is "confined to the high-activity strata"
— it is **not**. The cohort's rate exceeds the comparison group's rate in
**every one of the five bins** (roughly 11–27 percentage points higher
in each), not concentrated in `[46,83)` or `[83,∞)`. **Reported as such,
not resolved by picking the pooled figure, per the amendment's own rule.**

---

## What was not determined

- **What the A1×B2 result means for tradeability or profitability.**
  §7 of the pre-registration is explicit and unaffected by this result:
  persistence of direction says nothing about edge, and the 2026-09-06
  exploratory figures already show a similarly-shaped cohort's minimum
  detectable effect exceeds both category cost floors. Not re-examined
  here — edge was not computed anywhere in this run.
- **Why the aggregate test (§4) and the per-trader persistence rate point
  in different directions for the cohort** — the cohort clears its own
  per-trader persistence bar (37.0%, A1) while its pooled aggregate
  statistic does not exclude zero, mirroring exactly the tension the
  2026-09-05 result document's own Open Question 3 flagged as possible
  and unresolvable without computing. Not investigated further here.
- **Whether the stratified gap being present in every bin reflects a
  genuine, activity-independent effect or some other unmeasured
  confound** — reported as a fact about the five reported numbers, not
  tested statistically (no formal homogeneity test across strata was
  run), and not interpreted causally.
- **Whether B2 would resolve to B1 or B3 with more data** — not
  projected or estimated; the amendment fixed this as an expected,
  named, non-failure outcome at this N, not a problem to be extrapolated
  past.
- **§8's structural point** (that a well-calibrated null on zero-skill
  data is nearly empty by construction, making the split-half method's
  denominator possibly unfixable rather than merely underpowered) is
  recorded in the amendment as a finding, not re-tested or re-examined
  in this run.

---

## OBSERVATION LOG

*Per the task's rules: every entry is UNREGISTERED and UNTESTED. None is
a finding. Nothing here changes, qualifies, softens, or strengthens the
A1×B2 result above. No additional computation was run to develop any
entry — each reports only what was visible in data already produced by
the pre-registered computation above.*

1. **The cohort/comparison persistence-rate gap is not confined to
   high-activity strata** (already reported as a required part of the
   stratified result above) **and, within the cohort itself, shows no
   clear monotonic trend with post-split position count** — rates by
   bin (lowest to highest activity) run 40.7%, 44.8%, 32.6%, 37.0%,
   30.0%: a mild overall decline from the second-lowest to the highest
   bin, not a rise, and not monotonic in between. **Why it might
   matter**: if persistence rose sharply with activity, that would be
   the clean signature of an activity-power artifact rather than a
   trader-level property; the absence of a rising trend is mildly against
   that explanation, though far from a formal test of it. **What would
   settle it**: a pre-registered test of trend (e.g., a monotonicity or
   linear-trend test across the five strata, on both groups) — not run
   here, and not proposed as a next step, only named as what the
   question would require.
2. **No data on category (Geopolitics vs. Elections), distinct market
   count, entry-price range, or execution-dimension quantities (entry
   timing, market age at entry) was observed in this run.** The loaded
   position data carries `entry_ts` and `price` per position, but
   neither was aggregated, binned, or examined against persistence
   anywhere in this script. **Why it might matter**: these are exactly
   the watch-points the standing objective (identify profitable traders,
   rate them continuously) would need answered before treating A1×B2 as
   forward-usable. **What would settle it**: a separate, pre-registered
   analysis joining `markets.category`, per-trader market counts, entry
   price, and market-age-at-entry against the persistence-cohort/
   comparison-group split already computed here — not attempted, and
   would be new computation.
3. **A prospectively-observable candidate exists in principle** (pre-split
   BH classification itself is knowable before `T_split`, and by
   definition is what separates the persistence cohort from the
   comparison group) — but whether it constitutes a usable forward
   selector depends entirely on the edge question this test explicitly
   does not answer (§7). **What would settle it**: a separately
   pre-registered edge-persistence test, deliberately not run here per
   the "one-artifact-two-questions" scoping this whole arc was built to
   avoid.
