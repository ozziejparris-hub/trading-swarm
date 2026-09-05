# Directional Skill Test — Result

Pre-registration: `brain/decisions/2026-09-05-directional-skill-prereg.md`
(trading-swarm `cf88f8a`). Diagnostic script:
`scripts/directional_skill_diagnostic.py` (first-repo, this run's commit
below). Every threshold restated below is copied from the pre-registration
before any result appears, and none was adjusted after seeing output.

**Framing, stated up front per the task's own instruction**: the thesis is
explicitly fluid at this stage. Nothing below is softened. A null, or a
result that runs the opposite direction from what the thesis would want,
is reported exactly as computed.

---

## Thresholds restated, before any result

- **Significance bar**: a trader (or a pooled population) is classified
  **SKILLED** iff their actual dollar-weighted directional statistic
  exceeds the **95th percentile, one-tailed**, of their own 1,500-replicate
  sign-flip null.
- **Minimum trade count**: **10** post-split positions to be individually
  classifiable (reusing `M_CHOSEN`); **20** for the split-half subsample
  (so each half clears 10). Below the minimum: excluded from
  classification, reported separately, never folded into the rate's
  denominator.
- **Evidence-rate bands**: classified-skilled rate **≤10%** = unimpressive
  (near this test's own ~5% chance floor); **≥20%** = meaningful; **10–20%**
  = suggestive only, resolved by the separation check below.
- **Separation criterion (§12)**: cohort's classified-skilled rate must
  exceed placebo's by **≥10 percentage points, AND** cohort's pooled
  aggregate must clear its own 95th-percentile bar **while placebo's does
  not**. **Both required — either alone is partial, not separation.**
- **Multiple-comparison handling**: **Benjamini-Hochberg** (FDR, α=0.05)
  reported alongside the **raw** (uncorrected) rate — raw is primary
  (comparable to Gómez-Cram's own reported figure), BH is a required
  companion, not optional.

---

## Scoping verification — post-split only, honoured and checked, not assumed

The script asserts, not merely states, that every position in both
populations postdates `T_SPLIT`:

```
cohort:  n_positions=3795  n_traders=141  min(entry_timestamp)=2026-04-01T04:31:53
placebo: n_positions=2693  n_traders=118  min(entry_timestamp)=2026-04-01T00:04:41
T_SPLIT = 2026-04-01 00:00:00
```

Both minimums postdate `T_SPLIT` (by 4h32m and 4m41s respectively — the
placebo's tightest margin is under five minutes, the closest either
population comes to the boundary). The script's own `assert` would have
halted the run had either population's minimum entry timestamp fallen at
or before `T_SPLIT` — this is a hard check in the code, not a description
of intent. **Scoping confirmed: no pre-split position entered either
computation.**

---

## Reproducibility

- **Committed script**: `scripts/directional_skill_diagnostic.py`
  (first-repo, committed alongside this result).
- **Seed**: `42`. **Reps**: `1,500`.
- **Population**: frozen `cohort_trader_list` / `control_trader_list` from
  `data/characterizations/track2_ci_power_20260905T104945Z.json`, read
  directly, not re-derived.
- **Durable artifact**:
  `data/characterizations/directional_skill_20260905T161232Z.json` — full
  per-trader results, both aggregates, both split-half results, parameters,
  and this run's git commit.

---

## Per-trader classification, both populations

| | frozen | zero-position | below min (1–9) | classifiable (≥10) | raw skilled | raw rate | BH skilled | BH rate |
|---|---|---|---|---|---|---|---|---|
| **Cohort** | 169 | 28 | 68 | **73** | 19 | **26.0%** | 14 | **19.2%** |
| **Placebo** | 169 | 51 | 67 | **51** | 20 | **39.2%** | 15 | **29.4%** |

**The exclusion is substantial and stated plainly, not buried**: only
43.2% of the cohort's frozen 169 traders (73/169) and 30.2% of the
placebo's (51/169) were even classifiable — the rest either never
survived to have any post-split OOS position (28 cohort / 51 placebo,
matching Track 2's own presplit-to-surviving counts exactly) or fell
short of the 10-position minimum (68 cohort / 67 placebo).

Both raw rates individually clear the **≥20% meaningful** band. The
cohort's BH-adjusted rate (19.2%) sits just under the meaningful band, in
the ambiguous 10–20% zone; the placebo's BH-adjusted rate (29.4%) clears
meaningful under either correction.

**The placebo's classified-skilled rate is higher than the cohort's, on
both the raw and the BH-adjusted measure.**

---

## Aggregate (pooled) test, both populations

| | actual (dollar-weighted) | own null's 95th pctile | percentile rank | p-value | skilled? |
|---|---|---|---|---|---|
| **Cohort** | 90,101.00 | 174,136.68 | 78.67 | 0.214 | **NO** |
| **Placebo** | 92,238.40 | 59,780.76 | 99.47 | 0.006 | **YES** |

**The cohort and placebo's actual pooled statistics are nearly identical
in magnitude** (90,101 vs 92,238) — but the placebo's own null distribution
is much narrower, so a similar-sized actual result reads as decisively
non-random for the placebo and does not for the cohort. [I, not
independently investigated further here, per the pre-registration's own
scope]: this is consistent with the cohort's post-split positions carrying
more concentrated or larger-variance dollar sizing than the placebo's, but
that is offered as a plausible reading, not a verified cause.

**A genuine internal tension in the cohort's own result, reported honestly
rather than resolved by picking one number**: the cohort's per-trader raw
rate (26.0%) sits in the "meaningful" band in isolation, while the same
cohort's pooled aggregate test does **not** clear its own significance bar
at all (78.67th percentile, well short of 95th). Per-trader classification
and the pooled aggregate disagree in what they say about the cohort — this
is exactly the tension the pre-registration's Open Question 3 flagged as
possible and unresolvable without running the test.

---

## The discriminating comparison — cohort vs. placebo (primary output)

```
raw rate difference (cohort − placebo):  −13.2 percentage points
BH rate difference (cohort − placebo):   −10.2 percentage points
condition A (rate diff ≥ +10pp):          FALSE
condition B (cohort aggregate skilled AND placebo aggregate NOT skilled): FALSE
SEPARATION: FALSE
```

**Not merely "no separation" — the difference runs the opposite direction
from what §1(b) needed.** The placebo's classified-skilled rate exceeds
the cohort's by 13.2 points (raw) / 10.2 points (BH-adjusted) — both
comfortably past the 10-point margin that would have counted as separation
*in the cohort's favor*, except in the wrong direction. And on the
aggregate test specifically, the placebo clears its own significance bar
while the cohort does not — the exact reverse of what condition B
required.

---

## Split-half persistence — indicative only, on a small subsample

| | eligible (≥20 positions) | skilled on half A | also skilled on half B | persistence rate |
|---|---|---|---|---|
| **Cohort** | 59/169 (34.9%) | 20 | 12 | **60.0%** |
| **Placebo** | 32/169 (18.9%) | 12 | 7 | **58.3%** |

Gómez-Cram's own external reference figure: **44%**. Both populations here
sit somewhat above it. **This comparison is indicative, not decisive, per
the pre-registration's own caveat**: the denominators (20 and 12
respectively) are small enough that a single trader's classification
flipping either way would move the reported rate by 5–8 percentage points.
No conclusion about beating or matching the 44% benchmark should be drawn
from these counts alone. Consistent with the aggregate/rate results above,
the cohort does not out-persist the placebo here either (60.0% vs 58.3% —
close, within what this sample size could distinguish).

---

## Verdict against the four enumerated outcomes

1. Cohort shows directional skill and separates from placebo — **NO**
   (separation is false, and the direction is reversed).
2. **Cohort shows directional skill but the placebo matches it — the
   closest fit, and the actual result is stronger than "matches": the
   placebo does not merely match the cohort, it exceeds it** on every
   facet tested (raw rate, BH-adjusted rate, and the aggregate
   significance test the cohort itself fails to clear).
3. Neither shows directional skill — **NO**. Both populations' raw
   classification rates clear the "meaningful" (≥20%) band in isolation,
   and the placebo's pooled aggregate is clearly significant (p=0.006).
   There is elevated skill-like signal in this data — it is just not
   concentrated in the cohort the presplit selection produced.
4. Too noisy to distinguish — **NO**. The discriminating comparison is
   unambiguous in direction on every measure computed; this is not a
   power problem, it is a clear result running the wrong way.

**Outcome 2 (the pre-registration's §15) obtains, in its strongest form.**
Quoting that outcome's own text, verbatim, since this is exactly what it
was written to cover: **"the cohort's presplit selection captured nothing
distinctive... whatever directional pattern this test detects is not
special to the cohort; it would appear in any comparably-constructed
population drawn from this category... This would directly undermine the
original thesis — that skilled traders exist and are specifically
identifiable — even though this test's statistical detection of
'skill-like' PnL patterns technically succeeded."** Here the placebo does
not merely appear comparably skilled — it appears *more* skilled than the
population specifically selected to be edge-positive presplit. Nothing in
this result rescues the thesis as originally framed; per the task's own
instruction, this is reported as information that redirects the project,
not softened as a near-miss.

---

## The dollar-weighted basis — explicit, so this is not mistaken for a bug later

Every number above uses `Σ (won_i − entry_avg_price_i) × entry_total_cost_i`
— dollar-cost-weighted, per the pre-registration's own specification, to
hold bet size fixed as Gómez-Cram's method requires. **This is not the
project's `cap5` position-count-weighted mean edge** (the quantity behind
`+0.0316`/`+0.0208` elsewhere in this arc) — the two are not comparable,
by design, and a future session finding these numbers don't reconcile with
a cap5-weighted mean edge on the same population is seeing the intended
difference in convention, not a bug.

**One additional transparency note, not a re-specification**: the
pre-registration's formula weights by `entry_total_cost` (dollar cost),
which differs from true realized dollar profit (which would scale by
`entry_shares`, since a position's real payoff is `shares × (won − p)`,
not `cost × (won − p)`) by a factor of the entry price itself. This was
computed exactly as the pre-registration specifies — the formula was
fixed before this run and was not altered here — but is flagged plainly so
a reader distinguishes "cost-weighted directional statistic, as
pre-registered" from "true realized dollar PnL," which are not identical
quantities.

---

## Constraints honored

- No component was re-specified, re-parameterised, or re-run after seeing
  its result.
- No write to `metric_v2f_*` or any other production table.
- The copy-trade decay ladder was not computed; that pre-registration
  stands un-run.
- Nothing was approximated where the specification could be followed
  exactly; the one departure named above (cost- vs. share-weighting) was
  present in the pre-registration's own formula, not introduced here.

---

**Bottom line: the discriminating comparison fails, in the direction that
undermines the thesis rather than merely failing to confirm it. The
placebo — built to be a null for the cohort's presplit edge selection —
shows more evidence of directional-skill-like PnL patterns than the
cohort does, on every measure this pre-registration specified: classified-
skilled rate (raw and FDR-adjusted), the pooled aggregate significance
test, and split-half persistence. This is Outcome 2 of the pre-registered
four, and per that outcome's own text, it directly undermines the original
thesis that skilled traders exist in this cohort and are specifically
identifiable.**
