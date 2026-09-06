# Directional Skill Test — Discrepancy Check, PIT-Legal Pool, Power Estimate

Steps 2 and 3 of 4. Prior step:
[2026-09-06-directional-skill-null-calibration.md](2026-09-06-directional-skill-null-calibration.md)
(Step 1, PASSED — the harness classifies zero-skill-by-construction
traders at ~5%, matching its own chance floor; per-trader classification is
sound). This document presents evidence only for Parts A and B/C. **No
verdict on whether to proceed is stated here — that is Oscar's call.**

Reproducibility: three new scripts, all first-repo, this commit —
`scripts/directional_skill_pit_legal_pool.py` (Part B),
`scripts/directional_skill_pit_power_estimate.py` (Part C). Part A required
no new script (re-analysis of already-persisted artifacts via inline
verification, reported below with the exact recomputation shown). Durable
artifacts: `data/characterizations/directional_skill_pit_legal_pool_20260906T160303Z.json`,
`data/characterizations/directional_skill_pit_power_estimate_20260906T160818Z.json`.
Both scripts run with `--selfcheck` in the invocation that produced these
artifacts.

---

## Part A — the 37.3% / 39.2% discrepancy, resolved

**Finding: presentational, not compositional. The placebo set is
unchanged; 39.2% is what the harness's own authoritative field reports.**

`directional_skill_diagnostic.py`'s `classify()` function
(lines 92-99) computes two related but distinct quantities per trader:
- `skilled = actual > null_p95`, where `null_p95 = np.percentile(null, 95)`
  — a continuous, **linearly-interpolated** threshold between order
  statistics.
- `p_value = (sum(null >= actual) + 1) / (len(null) + 1)` — a **discrete,
  rank-based** count over the same 1,500-point null.

`per_trader_and_aggregate()`'s `raw_skilled_count` / `raw_rate` (the
figures the 2026-09-05 result document reports, 39.2% placebo / 26.0%
cohort) are computed from the `skilled` boolean field
(`raw_skilled = sum(1 for v in per_trader.values() if v['skilled'])`,
line 140) — **not** from `p_value < 0.05`. My Step 1 report computed its
own p-value-distribution table using `p_value < 0.05` as a proxy for
"skilled," which is what produced 37.3% instead of 39.2% for the placebo
arm — a difference in which stored field was read, not a different run or
a different placebo membership.

**Exactly one placebo trader accounts for the entire gap**
(`0x1c144e30f405a25f991cbd8baa15d40599090869`, n=183 positions):
`actual=2716.32`, `null_p95` (interpolated) `=2714.58` → `skilled=True`,
but `p_value=0.05063` (≥ 0.05) → not significant under the p-value proxy.
`percentile_rank=95.0` exactly — this trader sits precisely at the
boundary where 75/1,500 null draws are `>= actual` (giving
`p=(75+1)/1501=0.05063`), while the interpolated 95th-percentile order
statistic happens to land fractionally below the actual value. This is a
genuine artifact of two different "95th percentile, one-tailed"
operationalizations disagreeing at the margin on a discrete, finite null —
not a bug that changes which traders are in the placebo set, and not
evidence of a different run. **Zero such mismatches occurred in the
cohort arm** (0/73), which is why cohort's 26.0% matched cleanly under
both readings and only placebo showed the gap.

**Conclusion for Part A's first question**: 39.2% (the 2026-09-05
handover figure) is correct as the harness's own defined output. 37.3%
(my Step 1 report) was a presentational artifact of my own choice of proxy
field, self-flagged as such in that document's own footnote. **This does
not trigger the STOP condition for a composition-affecting discrepancy** —
the placebo's 51 classifiable traders and their underlying data are
identical either way.

**BH-adjusted rate = raw below-0.01 rate: confirmed coincidence, not a
fixed-threshold substitution.** `bh_correction()`
(`directional_skill_diagnostic.py:102-114`) was manually recomputed from
the persisted per-trader p-values (argsort, `thresh = (arange(1,m+1)/m)*alpha`,
step-up rejection) and matches the artifact's `bh_significant` field
exactly: 14/73 cohort, 15/51 placebo. The apparent equality with the raw
`p<0.01` count is a property of where the gaps between consecutive
p-values happen to fall for this specific dataset, not the code using
0.01 anywhere: cohort's BH-critical p-value is 0.00333 and the next
higher (non-rejected) p-value is 0.01332 — any threshold in
`[0.00333, 0.01332)` produces the identical 14-trader count, and 0.01
happens to fall in that interval. Placebo's corresponding gap is
`[0.00866, 0.01932)`. **This is a genuine Benjamini-Hochberg step-up
procedure, verified against a manual recomputation, not a disguised fixed
cutoff.**

---

## Part B — PIT-legal selection pool

**Tape_end anchoring — which code path is used, reported as asked, not
changed.** Neither existing script anchors on the project's canonical
population definition:
- `directional_skill_diagnostic.py`'s `load_post_split_positions()`
  filters on `p.entry_timestamp > T_SPLIT` — **position entry time**, not
  market conclusion time. It does not reference `tape_end` or
  `monitoring/column_definitions.py` at all.
- `trader_skill_metric_v2f.py`'s `build_presplit_cohort()` **does** anchor
  on `tape_end`, but via its own `build_tape_end_map()`
  (`trader_skill_metric_v2d.py:268`, `SELECT market_id, MAX(timestamp)...
  GROUP BY market_id`) — a separately-maintained duplicate of the same
  computation, not a call to `column_definitions.backtest_window_sql()`.
  It also does not apply the canonical `m.resolved = 1` filter that
  `BACKTEST_WINDOW_BASE_WHERE` includes; it only requires `tape_end IS NOT
  NULL AND tape_end <= t_split`.

This task's new script, `directional_skill_pit_legal_pool.py`, calls
`monitoring.column_definitions.backtest_window_sql()` directly — the
first of these three to do so. This is a choice made for this task's own
new query, not a change to either existing script.

### Population

| | count |
|---|---|
| pre-split markets (tape_end < T_SPLIT, canonical query) | 7,297 |
| pre-split resolved positions in those markets | 204,963 |
| **distinct traders with ≥1 pre-split resolved position** | **18,478** |

### Position-count distribution per trader (all 18,478)

| median | mean | p10 | p25 | p75 | p90 | max |
|---|---|---|---|---|---|---|
| 5 | 11.1 | 1 | 2 | 12 | 22 | 766 |

Heavily right-skewed — the mean (11.1) sits well above the median (5),
consistent with this project's prior findings elsewhere that a mean alone
would conceal this shape.

### Minimum count and classifiability

`M_CHOSEN = 10` reused unchanged from the harness's own convention (not
adjusted, per the task's explicit instruction). **5,732 / 18,478** traders
clear it.

### Per-trader classification (identical harness function, unmodified)

| classifiable | raw skilled | raw rate | BH skilled | BH rate |
|---|---|---|---|---|
| 5,732 | 1,494 | **26.1%** | 1,178 | **20.6%** |

Pooled aggregate (all 204,963 positions, all 18,478 traders, per
`per_trader_and_aggregate`'s own pooling convention): `actual=-5,220,278`,
`null_p95=+2,984,481`, `percentile_rank=0.07` — **not skilled**, and
deeply negative rather than merely non-significant. Unselected populations
pooled dollar-weighted over this many positions produce a large negative
sum; not investigated further here.

### P-value resolution at these smaller position counts

| n classifiable | p<0.05 | p<0.01 | p<0.001 | distinct p-values | pinned at floor (p=1/1501=0.000666) |
|---|---|---|---|---|---|
| 5,732 | — (see raw/BH above) | — | — | **1,340** | **716 (12.5%)** |

Only 1,340 distinct p-values occur across 5,732 classifiable traders —
**a selector built on this pool can threshold traders into bands, but
cannot finely rank them**; many traders share identical p-values by
construction (small `n` bounds the number of distinct achievable
sign-flip sums). 12.5% sit exactly at the permutation floor
(`1/1501 = 0.000666`, i.e. their actual statistic exceeded all 1,500 null
draws) and are mutually indistinguishable from each other at this rep
count — consistent with, and reproducing at similar magnitude, the ~15%
floor-pinning caveat carried forward from Step 1 (cohort 15.1%, placebo
13.7%, checked directly against the 2026-09-05 artifact as part of this
task).

### Survival into the post-split window

| | qualified (skilled, pre-split) | survived (any post-split resolved position) | survival rate |
|---|---|---|---|
| raw-skilled | 1,494 | **711** | 47.6% |
| BH-skilled | 1,178 | **504** | 42.8% |

**Scope note, not an error**: these counts are far larger than "the
original: 148 qualified, 120 survived" referenced in the task. That figure
comes from a *different* selection — `build_presplit_cohort()`'s
`intersection` (significance-95 **and** shrunk mean edge ≥ `EFFECT_BAR`
(0.02)) — a materially stricter bar than this Part B pool, which applies
only the directional sign-flip classification at `n≥10`, with no edge-
magnitude requirement and no restriction to a pre-matched cohort/placebo
pair. The two pipelines are not directly comparable in scale; both are
reported as computed.

**Observation, not adjudicated**: the pre-split raw rate here (26.1%) is
close to the post-split cohort's 2026-09-05 raw rate (26.0%), and the
pre-split BH rate (20.6%) sits at the prereg's own "meaningful" (≥20%)
threshold — the same elevated range seen in every population this test
has been run against so far (pre-split unselected, post-split cohort,
post-split placebo, all roughly 20-40%), never near the ~5% chance floor
except under the Step 1 synthetic zero-skill construction. Reported as a
pattern across this task's and Step 1's combined evidence; not
interpreted here.

### Stop condition check

711 (raw) and 504 (BH) both far exceed the 30-trader threshold. **Stop
condition NOT triggered — proceeding to Part C.**

---

## Part C — power estimate

Machinery: `measure_oos()` (`trader_skill_metric_v2f.py:315`, imported
unmodified) — two-way trader×market clustered bootstrap
(`weighted_two_way_gap_bootstrap`), cap5 weighting
(`weighted_pair_table`/`WEIGHT_FNS['cap5']`), same as the result of
record. Matched placebo built via `match_control()` (imported unmodified,
same greedy nearest-neighbour matcher used for the original 2026-09-05
placebo), matched against the presplit eligible pool
(`build_presplit_cohort()`'s `elig_pool`, `n_pairs ≥ M_CHOSEN`), same
seed (`42`). No minimum count, restriction, or weighting was adjusted.

**Selfcheck note**: `elig_pool` filters on cap5 trader-market *pairs* ≥
`M_CHOSEN`, while Part B's survivor lists filter on raw *position* count ≥
`M_CHOSEN` — different units of count. 234/711 raw survivors and 149/504
BH survivors fall outside `elig_pool` under the pair-count definition
(expected: a trader can have several positions in one market, which is
several positions but one pair) — reported, not treated as a failure. All
survivors have at least one presplit profile row (0 missing in both
groups), which is what `match_control()` actually requires.

### Measured out-of-sample edge, both cohorts and their matched placebos

| group | n traders (input) | n traders (survived, in measurement) | n positions | point gap | CI | width |
|---|---|---|---|---|---|---|
| raw cohort | 711 | 711 | 10,453 | +0.0090 | [-0.0127, +0.0290] | 4.2pp |
| raw matched placebo | 711 | 368 | 5,841 | +0.0099 | [-0.0155, +0.0358] | 5.1pp |
| BH cohort | 504 | 504 | 7,733 | +0.0029 | [-0.0237, +0.0259] | 5.0pp |
| BH matched placebo | 504 | 280 | 4,478 | +0.0161 | [-0.0133, +0.0446] | 5.8pp |
| **result of record** | 120 | 120 | 3,032 | **+0.0316** | **[-0.0088, +0.0710]** | **8.0pp** |

Placebo group traders drop from the matched input count (711/504) to a
smaller surviving count in the measurement (368/280) because matching is
done on presplit activity profile, and not every matched control has a
qualifying post-split resolved position — the same kind of attrition the
cohort side experiences going from presplit-qualified to post-split-
surviving, reported in Part B.

Neither projected width (4.2pp, 5.0pp) **exceeds** the result of record's
~8.0pp — both are narrower, driven by the larger trader/position counts
(711/504 vs 120, 10,453/7,733 vs 3,032). Reported as computed; the "state
plainly if it exceeds ~8pp" condition does not apply here.

### Minimum detectable effect (half-CI-width proxy) vs. category cost floors

This is a practical half-width proxy for "how large a true effect would
need to be to sit outside a zero-centered interval of this width" — not a
formal power simulation with an assumed alternative, and is labelled as
an approximation in the script and here.

| group | MDE (half-width) |
|---|---|
| raw cohort | 0.0209 (2.09pp) |
| raw placebo | 0.0257 (2.57pp) |
| BH cohort | 0.0248 (2.48pp) |
| BH placebo | 0.0289 (2.89pp) |

Category cost floors (cited as given, not recomputed): geopolitics
0.0005–0.010 (0.05–1.0pp), elections 0.0056–0.020 (0.56–2.0pp).

**Every group's MDE (2.09–2.89pp) exceeds the upper bound of both
category cost-floor ranges (1.0pp geopolitics, 2.0pp elections).** Even
with a substantially larger, better-powered PIT-legal cohort than the
result of record, this measurement cannot reliably distinguish a true
edge sitting at the top of either category's own cost floor from zero.
Stated plainly, per the task's instruction, as a legitimate finding: a
tighter CI than the result of record does not, on its own, translate into
power to detect an effect as small as this project's own established
transaction-cost floor.

**Observation, not adjudicated**: in 3 of 4 comparisons, the matched
placebo's point estimate is equal to or larger than the cohort's (raw:
0.0099 vs 0.0090; BH: 0.0161 vs 0.0029) — the same directional pattern
already seen in the 2026-09-05 result of record and the pre-split rate
comparison in Part B above. Reported, not interpreted.

---

## What this task did NOT determine

- **Part A**: why `np.percentile`'s interpolated threshold and the
  rank-based p-value formula disagree at this specific boundary was
  explained mechanically, but no broader audit of how often this
  boundary case recurs across other runs in the project was performed.
- **Part B**: whether the ~20–26% elevated classification rate seen across
  every population tested so far (pre-split unselected, post-split
  cohort, post-split placebo) reflects a structural, category-wide
  directional bias (as speculated, not established, in the 2026-09-05
  result document's Outcome 2 discussion) was not investigated — only
  observed and reported as a recurring pattern.
- **Part B**: the 1,340-distinct-p-value / 12.5%-floor-pinned finding was
  reported but not resolved — no attempt was made to increase `REPS`
  (explicitly out of scope: "do not adjust... the restriction... to
  produce a larger pool or a tighter interval," and Step 1's carried-
  forward caveats say this is to be respected, not fixed, in this task).
- **Part C**: the MDE figures are a half-CI-width proxy, not a formal
  statistical power calculation against a specified alternative
  hypothesis or simulated effect size — flagged as an approximation
  throughout.
- **Part C**: whether the observed placebo-exceeds-cohort pattern in 3 of
  4 groups is noise at this sample size or a genuine, repeating feature
  was not tested statistically here (no CI-on-the-difference was
  computed); only the two groups' own individual CIs are reported.
- **No STOP condition was triggered** in Parts A, B, or C: the PIT
  restriction was applied without modifying the harness (a new loader
  function was added, feeding the same unmodified classification
  functions, exactly as Step 1 did for the synthetic calibration); Part
  A's discrepancy resolved to a presentational artifact, not a
  composition change; no computed figure here contradicts the
  2026-09-05 handover or the Step 1 calibration document (all cited
  figures — 39.2%/26.0%, the 15%/15.1%/13.7% floor-pinning, +0.0316
  CI[-0.0088,+0.0710] — match on recomputation); and the ≥30-trader
  survival threshold between Parts B and C was cleared with a wide
  margin (711/504), so Part C proceeded.

---

**Bottom line, evidence only, no verdict**: the 37.3%/39.2% gap is a
presentational artifact in a downstream report, not a change to the
placebo population, and the BH-adjusted figures are genuine step-up
results whose apparent alignment with a 0.01 cutoff is coincidental. A
PIT-legal (tape_end-anchored, pre-split-only) directional-skill pool
exists at meaningful scale — 1,494 raw / 1,178 BH-adjusted skilled
traders pre-split, 711 / 504 of whom survive into the post-split window
with a qualifying position — clearing the 30-trader stop threshold by a
wide margin. Measuring out-of-sample edge on these larger cohorts with
the identical two-way-clustered, cap5-weighted, EB-adjacent machinery used
for the result of record produces a *tighter* CI (4.2–5.8pp vs. the
record's 8.0pp) but a minimum detectable effect (2.1–2.9pp) that still
exceeds both category cost floors' upper bounds (1.0pp geopolitics, 2.0pp
elections) — and the matched placebo outperforms the cohort in 3 of 4
comparisons, the same directional pattern already on record. These are
the numbers; the interpretation and any decision to proceed are Oscar's.
