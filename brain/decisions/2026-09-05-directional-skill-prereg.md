# Directional Skill Test — Pre-Registration (Gómez-Cram Randomised-Direction Benchmark)

**PRE-REGISTRATION ONLY. Compute nothing, produce no result, write no
analysis code.** Fixes the method before any classification exists. Per
`2026-09-05-n0-gap-check.md` (`7aa3fe5`), this runs now because §1(b) of
the canonical metric design currently has nothing established to
attribute, and this test — unlike the decay ladder — does not depend on
the placebo comparison to be informative on its own.

Tags: **[V]** verified this session (query/code run, shown), **[I]**
inferred or a fixed judgment call, marked as such.

---

## Fixed constraint, stated first because it is not an implementation detail

**This test uses POST-SPLIT trades only — positions entered after
`T_SPLIT = 2026-04-01 00:00:00`.** The cohort was selected on PRE-split
performance (`significance-95 + M≥10 + edge≥0.02`, evaluated only on
positions whose market had resolved by `T_split`). Those two windows are
disjoint by construction. Running this test on full trade history —
including the pre-split positions the selection criterion itself
conditioned on — would silently reintroduce exactly the circularity
`2026-09-05-canonical-skill-metric-design.md` §9 named: finding "skill" in
a population selected for showing that same pattern is not a finding, it
is the selection working as designed. The disjoint pre/post split is what
makes this test's result mean anything at all, and this restriction is
fixed here as a constraint on the method, not left as a parameter anyone
could vary later.

---

## Pre-flight — verified before specifying

**1. Bet size coverage, post-split, both populations** [V, live query]:

```
COHORT:  n_positions=3795  NULL entry_shares=0  NULL entry_total_cost=0
PLACEBO: n_positions=2693  NULL entry_shares=0  NULL entry_total_cost=0
```

**100% coverage on both.** The method does not need to degenerate to
equal-weighted — genuine per-position dollar size (`entry_total_cost`) is
available for every position in both populations.

**2. Trades (positions) per trader, post-split — the distribution, not
just the mean** [V, live query]. The mean (3,795/141 ≈ 27) is misleading;
this is heavily right-skewed:

| | p10 | p25 | median | p75 | p90 | p99 | max | ≥10 | ≥20 | ≥30 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Cohort** (n=141) | 1 | 3 | 12 | 37 | 77 | 141 | 191 | 51.8% | 41.8% | 29.8% |
| **Placebo** (n=118) | 1 | 3 | 7 | 23 | 55 | 193 | 230 | 43.2% | 27.1% | 22.0% |

Only about half of cohort traders (and fewer than half of placebo traders)
clear even 10 post-split positions. This directly shapes the minimum
trade-count decision (§6) and the split-half feasibility assessment (§9)
below — a mean of ~27 would have suggested comfortable power; the actual
median of 12 (cohort) / 7 (placebo) does not.

**3. The complementary price — confirmed derivable** [V, live query]:
`positions.outcome` takes exactly two values (`Yes`, `No`) across the
entire post-split cohort population — no third category. `entry_avg_price`
is strictly bounded within `(0.001, 0.999)` — zero positions at or beyond
the `[0,1]` boundary. **`1 − entry_avg_price` is always a well-defined
complementary price for every position**, with no boundary case to
special-case.

---

## The null construction — specified precisely

**Payoff structure, worked through explicitly, because "randomise
direction" is not sign-flipping the recorded PnL number**: buying `Yes` at
price `p`, per dollar invested, profits `(1−p)` if `Yes` resolves and `−p`
otherwise — this is exactly `won − p`, the project's own `edge` quantity.
The counterfactual — buying `No` instead — is entered at the complementary
price; profit per dollar is `won_no − (1−p)`, where `won_no = 1 − won`
(binary, complementary outcomes). Substituting: `won_no − (1−p) = (1−won) − (1−p) = p − won = −(won − p)`.

**This is where the derivation matters**: under the assumption that the
complementary price is exactly `1−p` (no spread), the flipped-direction
profit reduces algebraically to **exactly the negative of the actual
edge**. This is not assumed as a shortcut — it is derived from the payoff
structure, and it only holds because of the specific pricing assumption
made next. The result is a clean, standard construction: a **sign-flip
(Rademacher) randomization** on each position's own `(won − p)` — not an
ad hoc invention, but a recognizable member of the standard permutation-
test family.

**How the complementary price is obtained — fixed now, not left to
implementation**: **derived as `1 − entry_avg_price`, not looked up from
the tape.** A tape lookup for the opposing outcome's price would reintroduce
exactly the thinness and endogeneity problems the feasibility read already
found for the Part-1 fair-price benchmark (§1 of that doc), and B4's
order-book mid-price — the one candidate that could supply an independent
observed price — covers 3.57% of Geopolitics+Elections markets, disjoint
from this cohort, per the inventory. Derivation from the recorded price is
the only broadly-available option.

**What that assumption costs — stated, not hidden**: it assumes zero
bid-ask spread between the `Yes` and `No` sides (`p_yes + p_no = 1`
exactly). In reality a real counterfactual `No`-side entry would likely
have cost slightly *more* than `1−p` (spread). This makes the null's
"flipped" outcomes artificially cheap — i.e., **the null is generous, not
stingy, on the flip side**, which biases this test toward requiring
*more* evidence to call a trader skilled, not less (a real trader must
clear a null inflated by unrealistically-favorable counterfactual
pricing). **This is a conservative bias, and its rough magnitude is
already established by this project's own prior work**: `trader_skill_metric_v2f.py`'s
cost-floor construction puts the spread at `0.001–0.02`
(`SPREAD_LO, SPREAD_HI`) — the same, already-cited figure used throughout
this arc, not a new assumption invented here.

**Resampling parameters, fixed now**:
- **Reps: 1,500`** (`GATE_REPS_LOCAL`), not Gómez-Cram's 10,000. Justified
  on two grounds: (a) consistency — every bootstrap CI this project has
  produced (`v2d`, `v2f`, Track 2, the decay pre-registration) uses this
  same rep count, and this test's output should be directly comparable in
  precision/convention to everything already committed; (b) adequacy — a
  simple per-position sign-flip null (not a two-way cluster resample) at
  1,500 replicates comfortably resolves a one-tailed 95th-percentile bar
  (§10), which needs far less resolution than a p-value near a
  multiple-testing-corrected extreme tail would.
- **Seed: `42`**, matching the whole `v2d`/`v2f`/Track 2/decay-prereg
  lineage.
- **Flip granularity: per POSITION, not per raw trade.** A position is the
  natural unit of one directional bet in this project's own convention
  (matching how `entry_avg_price`/`measure_oos`/the whole edge machinery
  already treats it) — flipping individual raw `BUY` trades independently
  would risk splitting one directional decision (filled across several
  trades at slightly different prices) into inconsistently,
  independently-randomized fragments, which is not what "randomise
  direction" is asking.

**A deliberate, named departure from this project's existing edge
machinery**: `weighted_pair_table`'s `cap5` weighting caps influence by
**position count** per trader-market pair, not by dollar size — it does
not, and was never meant to, hold "size" fixed in Gómez-Cram's sense. This
test does **not** reuse that weighting scheme. Each position's weight in
both the actual statistic and the null is its own `entry_total_cost`
(dollars), unmodified and uncapped — because "hold sizes fixed" is the
defining feature of the method being implemented here, and the project's
existing cap5 convention answers a different question (pattern-level edge
across positions, size-blind). This is stated explicitly so it is not
mistaken for an oversight when this test's numbers do not match a cap5-
weighted mean edge on the same population.

---

## What is tested

**6. Per-trader classification.** Minimum post-split positions to be
classifiable: **10** — reusing `M_CHOSEN`, the exact same minimum-sample
threshold already established throughout the `v2d`/`v2f` lineage for
"significance-95" classification, rather than inventing a new number. Per
§2, this includes 51.8% of the cohort (73/141) and 43.2% of the placebo
(51/118). **Traders below 10 positions are excluded from per-trader
classification and reported separately** (count and fraction) — not
silently dropped, and not folded into the classification rate's
denominator.

For each classifiable trader: actual statistic = `Σ (won_i − p_i) × cost_i`
over their post-split positions; null = the same sum with each position's
sign independently flipped, fair coin, per replicate, 1,500 replicates.
Classified **SKILLED** iff the actual statistic exceeds the **95th
percentile** (one-tailed) of that trader's own null distribution —
reusing this project's existing "sig95" convention (`ci_lo_t > 0` /
"provably better than the market," already established in `v2d`'s own
threshold-derivation objective) rather than a new bar.

**7. Aggregate (pooled) test — reported alongside per-trader, not instead
of it.** Pools every post-split position from every surviving cohort
trader (all 141, including those below the 10-position minimum — their
positions still count toward the pooled sum even though they are not
individually classified) into one actual statistic and one 1,500-replicate
null, tested the same way. **These answer different questions and neither
substitutes for the other**: per-trader classification gives a rate
directly comparable to Gómez-Cram's own ~3%/44% figures; the aggregate
test is more powerful for detecting a small average effect but says
nothing about how skill is distributed across individuals (a few large
traders could carry a positive aggregate result on their own).

**8. Cohort versus placebo on the identical test — a primary output, not
secondary.** Both facets are reported:
- **Rate comparison**: classified-skilled rate, cohort vs. placebo, at the
  identical 10-position minimum and 95th-percentile bar.
- **Strength comparison**: each population's own pooled aggregate statistic
  (§7) against its own null, reported as where the actual value falls
  within its own null distribution (percentile rank) — cohort's and
  placebo's standing compared directly, not just their pass/fail status.

This is the discriminating comparison this test exists to make: the cohort
and placebo currently show statistically indistinguishable **edge**
(`2026-09-05-n0-gap-check.md`, gap `−0.0072`, CI straddling zero). If the
cohort separates from the placebo on **direction** while edge does not
separate, that is direct evidence the cohort's (whatever remains of its)
profitability is directional and the placebo's is not — §1(b)'s question,
answered without needing the gap to exist.

**9. Split-half persistence — feasibility assessed honestly, not
specified where it cannot run.** Gómez-Cram's own method: split each
trader's events randomly in half, classify independently on each half,
report the fraction skilled-on-one-half also skilled-on-the-other (their
figure: 44%). Applying the same 10-position minimum **per half** would
require ≥20 total positions — **41.8% of the cohort (59 traders), 27.1% of
the placebo (32 traders)**, per §2's table. **This test is feasible only on
that restricted subsample, not on the full 141/118-trader populations** —
attempting it on traders with, say, 10–19 total positions would leave as
few as 5 per half, underpowered by this test's own minimum-count logic
applied to itself. **Fixed here: split-half persistence runs only on the
≥20-position subsample (59 cohort / 32 placebo traders); for every trader
below that, it is deferred, not attempted, and not silently approximated
on too little data.**

---

## Thresholds, fixed now

**10. Significance bar**: 95th percentile, one-tailed, of the trader's own
(or the pooled population's own) 1,500-replicate null — stated above, not
repeated as a separate number; reuses the existing project "sig95"
convention.

**11. What classified-skilled rate counts as evidence.** Two external
anchors, both real: this test's own **chance floor** (~5%, the false-
positive rate a one-tailed 95th-percentile bar produces under a true null,
by construction) and Gómez-Cram's own **~3% unselected-population rate**.
This cohort is *not* an unselected population — it was pre-filtered for
presplit outperformance — so it should show a materially higher rate than
either anchor if any of that presplit quality persists. Fixed:
- **≤10% (roughly twice the chance floor): unimpressive** — statistically
  close to what an unselected population tested the same way would show by
  chance alone; the presplit selection would have captured nothing
  detectable in this test.
- **≥20% (roughly four times the chance floor, well above triple
  Gómez-Cram's population rate): meaningful** — the presplit selection is
  carrying forward into post-split, individually-classifiable directional
  performance at a rate a chance/unselected population would not produce.
- **10–20%: suggestive but not decisive on its own** — resolved by the
  cohort-vs-placebo comparison (§12), not by this rate in isolation.

**12. What cohort-vs-placebo difference counts as separation.** Fixed:
the cohort's classified-skilled rate must exceed the placebo's by **at
least 10 percentage points** (absolute — roughly two chance-floor units of
margin), **and** the cohort's pooled aggregate statistic (§7) must clear
its own 95th-percentile bar while the placebo's own aggregate does **not**
clear its own. **Both conditions together = separation. Either alone =
partial, reported as such, not forced into a binary call** — mirroring
Track 2's own precedent that a non-orthogonal result should be reported as
mixed, not collapsed into a false clean split.

**13. Multiple-comparison handling across the classifiable per-trader
tests (up to 141 cohort, 118 placebo).** Fixed: report the **raw**
(uncorrected) classification count and rate as the primary figure — this
is what is directly comparable to Gómez-Cram's own reported rate, which is
not evidenced here to have used a different correction — **and** a
**Benjamini-Hochberg (FDR) adjusted** count and rate as a required
companion, not an optional robustness check. **Benjamini-Hochberg, not
Bonferroni**: this is a population-*rate*-estimation question ("what
fraction of this cohort is skilled"), the same class of question the
fund-manager-skill literature (Barras/Scaillet/Wermers-style false-
discovery-rate approaches) addresses with FDR control, not a single
confirmatory hypothesis test where Bonferroni's much stricter, single-
discovery guarantee would be the right tool and would needlessly discard
power here. **A large gap between the raw and FDR-adjusted rates is
itself informative and must be reported, not resolved by picking one.**

---

## Outcomes, enumerated in advance

**14. Cohort shows directional skill and separates from placebo** (§12,
both conditions met) → §1(b) has a subject. The canonical metric design
proceeds on the premise that directional skill exists and is specific to
this cohort, not a generic feature of any similarly-constructed population
in this category.

**15. Cohort shows directional skill but the placebo matches it** (rate
and/or aggregate result comparable, §12 not met) → **the cohort's
presplit selection captured nothing distinctive.** This does not mean "no
skill exists anywhere" — it means whatever directional pattern this test
detects is not special to the cohort; it would appear in any comparably-
constructed population drawn from this category (e.g., a structural,
category-wide directional bias in how Geopolitics/Elections markets price
or resolve, unrelated to any individual trader's judgment). **This would
directly undermine the original thesis** — that skilled traders exist and
are specifically identifiable — even though this test's statistical
detection of "skill-like" PnL patterns technically succeeded.

**16. Neither cohort nor placebo shows directional skill** → the null is
total, exactly per the canonical design's §1(a): nothing downstream (the
decay ladder, the earliness components) can rescue this. **Stated
plainly, this is a legitimate, valuable, reportable finding** — not a
failure of this test.

**17. Too noisy to distinguish** (classification rates and aggregate
percentiles too close to their own chance floors, or their confidence
intervals too wide, to call any of 14–16). **What would make it
conclusive, stated now**: a larger post-split sample — which, given the
skew in §2, means either waiting for more positions to accrue naturally
as time passes and more markets resolve, or restricting to the higher-
count subsample (trading breadth for depth, the same tradeoff already
named in §9). **Re-running with different parameters (a different
significance bar, a different minimum count chosen after seeing a
disappointing result) is explicitly not an acceptable resolution** —
mirroring Track 2's and the decay pre-registration's own identical rule.
An inconclusive result under this pre-registration's fixed parameters is
reported as inconclusive.

---

## Reproducibility

- **Committed script**: `scripts/directional_skill_diagnostic.py`
  (first-repo `scripts/`, matching `track2_ci_power_diagnostic.py`'s
  naming/location convention; not created by this pre-registration, named
  here so the eventual result document can point to it).
- **Seed**: `42`. **Reps**: `1,500`.
- **Population**: the frozen `cohort_trader_list` / `control_trader_list`
  (169 traders each) from
  `data/characterizations/track2_ci_power_20260905T104945Z.json` — read
  from that artifact, not re-derived.
- **`T_SPLIT = "2026-04-01 00:00:00"`**, unchanged, hardcoded — the post-
  split-only constraint stated at the top of this document.
- **Minimum trade count**: 10 (per-trader classification), 20 (split-half
  subsample).
- **Classification bar**: 95th percentile, one-tailed, per trader and
  pooled.
- **Multiple-comparison correction**: Benjamini-Hochberg, reported
  alongside the raw rate.
- **Durable artifact**: `data/characterizations/directional_skill_<UTC-timestamp>.json`
  — per-trader classification results (statistic, null distribution
  summary, classified/not, included/excluded-by-minimum), the pooled
  aggregate result for cohort and placebo, the raw and FDR-adjusted rates
  for both populations, the split-half subsample result where computed,
  and the git commit of this script and of `trader_skill_metric_v2f.py`
  at run time.
- **Parameters recorded, not re-derived silently on a later run**: all of
  the above, plus the exact SQL predicates for the post-split position
  query (identical to `measure_oos`'s own: category, `entry_avg_price` not
  null, `trade_result`, gap-clean, `entry_timestamp > T_SPLIT`).

---

## Open questions (explicitly deferred — not answered by this document)

1. Whether the Benjamini-Hochberg-adjusted rate will differ materially
   from the raw rate — only answerable by running the test.
2. Whether the true `Yes`/`No` spread for *this specific* cohort's markets
   actually falls within the `0.001–0.02` range `v2f`'s cost-floor work
   established in a different context (Objective 1's cost analysis), or
   differs materially for this population — inherited, not independently
   re-verified here.
3. Whether per-trader classification and the pooled aggregate result will
   agree in direction, or whether a small number of large-position traders
   will dominate the aggregate while few individuals clear the per-trader
   bar (or the reverse) — genuinely unknowable without computing.
4. Whether the ≥20-position split-half subsample (59 cohort / 32 placebo
   traders) will itself have adequate power once actually run — feasibility
   is assessed here; actual power is not.
