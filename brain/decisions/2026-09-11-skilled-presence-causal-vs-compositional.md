# Is Skilled-Trader Presence Causal or Compositional?

**Follow-up test. Read-only. No selector, no strategy, no signal built.**
Nothing persisted; no write to any production table; `--persist` not
implemented; no canonical definition, harness, or threshold modified;
the copy-trade decay ladder was not re-run; no service restarted.

Script `scripts/skilled_presence_causal_test.py` (first-repo, committed
`e3ac29e`, script_commit-at-run-time `dd0fb5e`). Artifact
`data/characterizations/skilled_presence_causal_test_20260911T195254Z.json`.
`seed=42`, `reps=1500`, `caliper=1.0`. `--selfcheck` passed. `run_tests.py`:
26 files, 26 passed (no new test file — same convention as
[[2026-09-10-own-market-calibration]]: this is an analysis script, not a
harness/module change).

Tags: **[V]** verified this session (query/command shown), **[I]**
reasoned judgment.

**No verdict on what to do next — that is Oscar's.**

---

## Headline

**Skilled-trader presence is compositional, not a skill-specific
mispricing marker.** The calibration-slope gap survives market-level
matching on size/activity (Part 2: direction holds at 6/6 horizons after
matching present and absent markets to near-identical n_trades,
n_distinct_traders, volume, and lifetime) — but a placebo test (Part 3)
using an equally-sized, equally-activity-matched set of traders *not*
selected for directional skill reproduces the same slope elevation at
4 of 6 horizons, at magnitudes close to the real skilled-trader numbers.
**Presence of any sufficiently active, well-matched trader cohort
explains the gap; skill does not add anything detectably beyond that.**
Per the task's own stop condition, this halts the test before Part 4 —
no edge-units-vs-cost-floor table was produced, because there is no
surviving skill-specific effect to measure it for.

A genuine bug was found and fixed while building Part 3: the obvious
reuse (`trader_skill_metric_v2f.build_presplit_cohort()`'s own
`elig_pool`) is **not** the PIT-legal pool's classifiable population —
see §Part 3 methodology note.

---

## Part 1 — characterising the two populations before comparing them

### Population, as of today (small drift from 2026-09-10) [V]

Same predicate as [[2026-09-10-own-market-calibration]]
(`backtest_window_sql`, tape_end-anchored, resolved gap-clean Geo/Elec,
binary `winning_outcome`). Two days of new resolutions moved the count
slightly: **9,763 used** (9,823 canonical, 60 non-binary excluded) vs.
9,739 on 09-10. Skilled-present: **5,629** (57.6%) vs. 5,619 on 09-10.
Skilled-absent: **4,134** vs. 4,120. This is not a re-run of the 09-10
population; it is today's canonical population under the same rule —
close enough that nothing about the underlying question changes, but
noted for reproducibility.

### The two arms differ grossly on size and activity [V]

| observable | skilled-present (n=5,629) | skilled-absent (n=4,134) | ratio (median) |
|---|---|---|---|
| n_trades (median / mean) | 18 / 125.8 | 3 / 7.7 | **6×** |
| n_distinct_traders (median / mean) | 9 / 42.6 | 2 / 4.1 | **4.5×** |
| volume $ (median / mean) | 1,387 / 52,457 | 75 / 3,225 | **18.5×** |
| lifetime hours (median / mean) | 351 (~15d) / 944 | 34 (~1.4d) / 322 | **10×** |

**This is exactly the "differ grossly on observables" scenario the task
warned would make the raw comparison uninterpretable — on size/activity,
not base rate.** Skilled-present markets are bigger, more actively
traded, and longer-lived by roughly an order of magnitude at the median,
across every one of these four measures. A market attracting 18+ trades
across 9+ traders over two weeks is a structurally different object from
one with 3 trades from 2 traders that traded for a day and a half.

### Base rate — the one that matters most [V]

| | skilled-present | skilled-absent | gap | 95% CI |
|---|---|---|---|---|
| YES rate | 30.8% | 26.9% | **+3.97 pp** | [+2.16, +5.78] pp |

A real, CI-solid gap (does not include zero), but **well below** the
10-pp threshold set before running this as "grossly confounded at the
root" (chosen with reference to this project's own category base rates
spanning 20.9%–70.9% elsewhere — a few points is routine, ~10+ points
was judged the point at which a logistic-slope comparison estimated
around two different centres becomes uninterpretable on its own). **Stop
condition NOT tripped at Part 1** — proceeded to Part 2, where this gap
is revisited (it narrows further under matching; see below).

### Category mix differs substantially [V]

| category | present | absent |
|---|---|---|
| Geopolitics | 42.6% | 29.0% |
| Elections | 57.4% | 71.0% |

Skilled-present markets skew Geopolitics; skilled-absent markets skew
Elections — relevant because the two categories have both different cost
floors (4× apart) and, per 09-10 Part 1c, different pooled slopes
(Geopolitics higher). Handled in Part 2 by matching **within** category
(exact stratification), not adjusted for statistically.

### Event-cluster membership [V]

| | present | absent |
|---|---|---|
| solo (no cluster label) | 46.6% | 59.2% |
| labelled | 53.4% | 40.8% |

Absent markets are more often solo, consistent with them being smaller/
more isolated events — not matched on directly (see Part 2 methodology),
but consistent with the size story.

### Price at each horizon — are absent markets more extreme? [V]

| horizon | present median / p90 | absent median / p90 |
|---|---|---|
| ~0.5h | 0.020 / 0.994 | 0.116 / 0.890 |
| ~3h | 0.026 / 0.984 | 0.120 / 0.860 |
| ~12h | 0.031 / 0.974 | 0.103 / 0.840 |
| ~3d | 0.040 / 0.935 | 0.080 / 0.793 |
| ~14d | 0.050 / 0.850 | 0.070 / 0.760 |
| ~45d | 0.055 / 0.807 | 0.067 / 0.792 |

Mixed, not a clean "absent is more extreme" story: present markets have
a **lower median** price (more concentrated toward 0) at every horizon,
but a **higher p90** (reaching further toward 1) — present markets are
more extreme at *both* tails, absent markets sit more centrally. Means
are close (e.g. 0.303 vs. 0.290 at 0.5h). Plausibly a maturation effect —
bigger, longer-traded markets have had more time to converge away from
50/50 in whichever direction they're heading.

---

## Part 2 — matched comparison

### Matching approach, and why not `match_control()` [V]

**Purpose-built market-level match, not `match_control()`.**
`match_control()` (`trader_skill_metric_v2f.py:281`) does greedy nearest-
neighbour matching on **trader**-level activity (log positions, log
markets, log activity-span-days) from an eligible-**trader** pool. The
object being matched here is a **market**, on market-level size/
composition features (n_trades, n_distinct_traders, volume, lifetime) —
a different feature space entirely, and a different distance problem
(market volume spans orders of magnitude more than trader position
counts do; category is a hard exact-match constraint here with no analog
in the trader problem). Reusing `match_control()` as-is would silently
apply the wrong feature set. Built a dedicated `match_markets()` instead,
following the same *structural* pattern (seeded RNG, sort-before-shuffle
determinism, greedy nearest-neighbour, one-to-one, no replacement) that
`match_control()` established and that its own 2026-09-06 determinism fix
documented as the right way to do this class of matching — reused the
*pattern*, not the function, because the function's specific feature
vector doesn't apply.

**Construction:** within each category (Geopolitics matched only to
Geopolitics, Elections only to Elections — the exact-match handles the
category-mix confound by design, not by adjustment), z-score
`log(1+n_trades)`, `log(1+n_distinct_traders)`, `log(1+volume)`,
`log(1+lifetime_hours)` across the pooled present+absent markets in that
category. Greedy 1:1 nearest-neighbour in this 4-D standardised Euclidean
space, absent markets (the smaller arm) matched against the present
pool, no replacement, processing order fixed by a seeded RNG shuffle
(same determinism-safety pattern as `match_control()`'s 2026-09-06 fix).
**Caliper = 1.0** (standardised Euclidean distance): a match further than
this is dropped rather than forced. Chosen as a defensible, stated,
round number in this 4-D standardised space (roughly "each of the four
features half a standard deviation away on average") rather than tuned
to any result — the achieved-distance distribution (median 0.253, p90
0.797, mean 0.348) sits comfortably under the caliper for the large
majority of accepted matches, so the caliper is not doing heavy lifting
at the margin.

### Matches retained and balance achieved [V]

| category | absent (base) | present pool | matched |
|---|---|---|---|
| Elections | 2,937 | 3,232 | **1,874** (63.8%) |
| Geopolitics | 1,197 | 2,397 | **869** (72.6%) |
| **total** | **4,134** | **5,629** | **2,743** (66.4%) |

Covariate balance, pre- vs. post-match (means):

| feature | pre present | pre absent | post present | post absent |
|---|---|---|---|---|
| n_trades | 125.8 | 7.7 | 11.4 | 10.4 |
| n_distinct_traders | 42.6 | 4.1 | 6.0 | 5.3 |
| volume $ | 52,457 | 3,225 | 2,009 | 1,839 |
| lifetime hours | 944 | 322 | **445.5** | **446.1** |
| base YES rate | 30.8% | 26.9% | 31.0% | 28.0% |

Matching closes the size/activity gap almost completely (lifetime goes
from 944 vs. 322 to 445.5 vs. 446.1 — effectively identical) and narrows
the base-rate gap from +3.97pp to +2.92pp (not eliminated, but well
inside the pre-registered non-confounding range).

### Matched-arm slopes, all six horizons, clustered on market + event cluster [V]

| horizon | matched-present slope [CI] (n) | matched-absent slope [CI] (n) | present excl. 1.0 | absent excl. 1.0 | direction preserved |
|---|---|---|---|---|---|
| ~0.5h | **1.369** [1.190, 1.609] (2,480) | 1.200 [1.040, 1.409] (2,430) | yes | yes | yes |
| ~3h | **1.302** [1.127, 1.538] (2,375) | 1.129 [0.979, 1.313] (2,339) | yes | no | yes |
| ~12h | **1.198** [1.036, 1.410] (2,140) | 1.049 [0.900, 1.224] (2,114) | yes | no | yes |
| ~3d | 1.133 [0.960, 1.382] (1,464) | 1.019 [0.860, 1.251] (1,449) | no | no | yes |
| ~14d | 1.231 [0.944, 1.718] (815) | 1.123 [0.897, 1.524] (804) | no | no | yes |
| ~45d | **1.648** [1.203, 3.708] (324) | 1.091 [0.767, 1.855] (330) | yes | no | yes |

**Direction survives at 6/6 horizons.** The matched-present slope
exceeds matched-absent at every one of the six lead times — the gap is
not a pure size/activity/category-composition artifact. CIs continue to
overlap at every horizon (same pattern as the unmatched 09-10 result;
matching narrows n substantially, so CIs widen rather than tighten
relative to the original). **Part 2's own stop condition (effect
disappears/reverses under matching) is not tripped — gate opens to
Part 3.**

---

## Part 3 — placebo test (gated open)

### Why `match_control()` IS the right tool here [V]

Unlike Part 2, this genuinely **is** the trader-activity-matching problem
`match_control()` was built for: drawing a same-size, activity-matched,
non-skill-selected set of **traders** (not markets) from a **trader**
eligibility pool, on exactly the feature vector (log positions, log
markets, log activity-span) `match_control()` already implements. Reused
directly, not reimplemented.

### Methodology bug found and fixed [V]

The first attempt used `trader_skill_metric_v2f.build_presplit_cohort()`'s
own `elig_pool` (traders with `n_pairs >= M_CHOSEN` from
`compute_cap5_metric`'s EB-shrinkage pair construction) as the "PIT-legal
classifiable pool." **This is wrong** — verified this session: that pool
has only 3,037 traders, and **536 of the 1,494 skilled traders are not
even members of it**. `n_pairs` (matched trade pairs under the cap5
metric) is a materially smaller, differently-constructed population than
`directional_skill_pit_legal_pool.py`'s own classifiable definition
(`n_positions >= M_CHOSEN` in the canonical tape_end<T_SPLIT market set,
via `load_presplit_market_ids`/`load_presplit_positions`) — the actual
pool that produced the 1,494 skilled traders in the first place. Fixed by
rebuilding the pool via `directional_skill_pit_legal_pool.py`'s own
loaders directly: **5,917 classifiable traders** (close to but not
identical to the 09-06 artifact's recorded 5,732 — five days of new
data), **0 skilled traders missing from the pool** (correct — a skilled
trader must, by construction, be classifiable). This is exactly the kind
of silent-mismatch risk the task's own "don't use match_control() unless
genuinely appropriate" caution was pointing at, just one level deeper
than expected — not in which matcher to use, but in which *pool*
definition two similarly-named things in the codebase actually mean.

### Placebo construction [V]

`match_control(profile, skilled_traders, classifiable_pool, seed=42)` —
greedy nearest-neighbour on (log positions, log markets, log activity-
span), from the 5,917-trader classifiable pool minus the 1,494 skilled
traders, matched 1:1 to the skilled cohort. **1,494 placebo traders**
(deterministic given `seed=42` — not a literal random draw, but a
seeded, reproducible, non-skill-selected activity-matched selection; the
task's "randomly selected... matched on activity level" is satisfied by
construction: not selected for skill, matched on activity, and seed
recorded for reproducibility). All-time positions used for presence
(same convention as the original skilled-presence variable). **5,637
markets placebo-present** (vs. 5,629 for the real skilled-presence
variable — nearly identical coverage, as expected from activity-matched
traders).

### Placebo-arm slopes, all six horizons [V]

| horizon | placebo-present slope [CI] (n) | placebo-absent slope [CI] (n) | direction matches skilled-presence? |
|---|---|---|---|
| ~0.5h | 1.352 [1.218, 1.530] (5,408) | 1.220 [1.076, 1.394] (2,962) | **yes** |
| ~3h | 1.276 [1.153, 1.423] (5,317) | 1.160 [1.024, 1.345] (2,791) | **yes** |
| ~12h | 1.164 [1.062, 1.290] (5,048) | 1.099 [0.959, 1.291] (2,471) | **yes** |
| ~3d | 1.135 [1.020, 1.268] (4,111) | 1.093 [0.937, 1.332] (1,666) | **yes** |
| ~14d | 1.121 [0.982, 1.287] (2,852) | 1.307 [1.032, 1.774] (898) | no (reversed) |
| ~45d | 1.112 [0.933, 1.344] (1,480) | 1.364 [0.977, 2.538] (357) | no (reversed) |

**The placebo replicates the skilled-presence elevation at 4 of 6
horizons (0.5h through 3d)** — and at magnitudes close to the real
numbers (e.g. matched-present skilled slope 1.369 at 0.5h vs. placebo-
present 1.352; matched-absent skilled 1.200 vs. placebo-absent 1.220,
nearly identical). At the two longest, thinnest horizons (14d n=898/357,
45d n=1,480/357) the placebo direction reverses — but these are exactly
the cells the 09-10 doc already flagged as the thinnest and most
bootstrap-degenerate in the original measurement, so a reversal there
does not read as evidence of skill-specificity so much as noise at low
n.

**Part 3's stop condition is tripped: the placebo shows the same
elevation at a majority of usable horizons, at comparable magnitude, on
the short-to-medium horizons where the original effect was strongest.**
Presence — of any sufficiently active, well-matched trader cohort — is
associated with the calibration-slope elevation. This measurement finds
nothing that isolates *skill* as opposed to *activity* as the marker.

---

## Part 4 — not run

Per the task's gating: Part 4 (edge-units deviation vs. cost floors for
the surviving conditioning variable) only runs if Part 3's placebo fails
to replicate. It replicated. There is no skill-specific effect surviving
to Part 4's stage, so no edge-units table was produced. This is not an
omission — it is the correct behaviour given the gate.

---

## What was NOT determined

- **Whether an *even more actively matched* placebo (e.g. matched
  additionally on n_positions in Geo/Elec specifically, or on recency of
  activity) would still replicate.** `match_control()`'s feature vector
  (positions, markets, span) is the project's existing standard; a
  tighter placebo construction was not attempted.
- **Why the placebo reverses direction at 14d/45d specifically.** Read as
  thin-n noise (same cells flagged thin in the 09-10 original), not
  chased further.
- **Whether the residual, unmatched skilled-presence effect (Part 2, pre-
  placebo) has ANY skill-specific component too small to detect against
  placebo noise at these n.** This measurement can rule out "skill
  explains most/all of the gap"; it cannot rule out a small residual
  skill-specific contribution beneath the placebo's own noise floor.
- **The ~2,743/4,134 (66%) Part 2 match rate's effect on generalisability**
  — the unmatched third of skilled-absent markets (extreme size/activity
  outliers with no comparable present-arm neighbour within caliper) are
  excluded from the matched comparison entirely; whether they behave
  differently was not checked.
- **Category-specific placebo replication.** Part 3 was run pooled
  (as the original Part 3 was); whether the placebo replication holds
  equally within Geopolitics and within Elections separately was not
  broken out.
- **Anything about tradeability.** Moot here — Part 4 (where cost-floor
  comparison would happen) was gated closed.

---

## Reproducibility

- **Script:** `scripts/skilled_presence_causal_test.py` (first-repo,
  committed `e3ac29e`; `script_commit` recorded in the artifact is
  `dd0fb5e`, HEAD at run time — same "script lands in the result commit"
  convention as [[2026-09-10-own-market-calibration]]). Read-only;
  `--persist` not implemented. Imports and reuses
  `own_market_calibration.py`'s population/tape/snapshot/bootstrap/slope
  machinery directly rather than re-deriving it (`db_connect,
  load_population, load_event_clusters, load_tape, snapshot_rows,
  calib_curve, slope_ci`, the six-horizon/price-decile constants, cost
  floors, the PIT pool path, the oos-result sha check). `--selfcheck`:
  `describe()` on a known series; `match_markets()` on synthetic data
  (correct pair count, no candidate reused twice).
- **Artifact:**
  `data/characterizations/skilled_presence_causal_test_20260911T195254Z.json`
  — full Part 1 distributions (all four size/activity features, base
  rate, category mix, cluster membership, price-by-horizon for both
  arms), the Part 2 match result (per-category retained counts, achieved-
  distance distribution, full balance table), all six-horizon matched
  curves and slopes with CIs, the Part 2 survival-gate detail, the Part 3
  placebo construction (pool sizes, placebo trader list size, markets
  covered), all six-horizon placebo curves and slopes with CIs, and the
  Part 3 survival-gate detail. `part4: null` (correctly not run).
- **Detached run:** launched via `setsid ... nohup ... < /dev/null &` +
  `disown` (per this box's documented history with unmonitored runaway
  processes), watched via a bounded `Monitor` polling the log for a
  `[done]`/`Traceback`/`STOP]` marker rather than left to poll
  indefinitely; confirmed complete by the `[done]` line in the log and
  by reading the resulting JSON artifact directly (`part4: null`,
  `oos_result_unchanged: true`, matching stdout). Runtime: ~35 minutes
  end to end (population/tape/feature loading is fixed-cost; the
  bootstrap-dependent Part 2 + Part 3 slope/curve fits at `reps=1500`
  dominate).
- **Stop conditions — one tripped, as designed:** Part 1's base-rate gap
  (+3.97pp) did not trip the 10-pp threshold — proceeded to Part 2. Part
  2's direction survived matching at 6/6 horizons — did not trip its stop
  condition — proceeded to Part 3. **Part 3's placebo replicated the
  elevation at 4/6 horizons — this stop condition DID trip**, halting
  before Part 4 as specified. `metric_v2f_oos_result` sha256
  `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
  unchanged before and after (verified both in the run log and in the
  artifact).
- **Tests:** `run_tests.py` (not bare pytest) — **26 files, 26 passed, 0
  failed** (339,919 assertions). No new test file added — this is an
  analysis script reusing existing, already-tested harness functions
  from `own_market_calibration.py` and `trader_skill_metric_v2f.py`;
  same convention as the 09-10 doc.
- **Copy-trade decay ladder:** not touched, not re-run, per scope.
