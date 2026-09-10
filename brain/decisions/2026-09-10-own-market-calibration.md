# Own-Market Calibration, and Where This Project's Traders Sit In It

**PREMISE TEST. Read-only. No selector, no cohort, no placebo — this
deliberately abandons trader selection.** Nothing persisted; no write to
any production table; `--persist` never passed; no canonical definition,
harness, or threshold modified; the copy-trade decay ladder was not
re-run.

Script `scripts/own_market_calibration.py` (first-repo, committed with
this result). Artifact
`data/characterizations/own_market_calibration_20260910T204249Z.json`. `seed=42`,
`reps=1500`, `T_SPLIT=2026-04-01 00:00:00`. `--selfcheck` passed.

Tags: **[V]** verified this session (query/command shown), **[I]**
reasoned judgment.

**No verdict on what to do next — that is Oscar's.**

---

## Headline

- **This project's own Geo/Elec markets are miscalibrated in the
  *direction* the external literature predicts — logistic recalibration
  slope > 1 (prices compressed toward 50%; longshots slightly overpriced,
  favourites slightly underpriced) — but in the *opposite shape*: the
  slope is highest near resolution (~1.29 at ~30 min out) and *falls*
  with time to resolution (~1.12–1.15 at days-to-weeks), against arXiv
  2602.19520's predicted *rise* from 0.99 to 1.32.** Reported as the
  finding; not reconciled.
- **The statistically solid deviations are the small-magnitude,
  large-n ones at the price extremes** — bucket [0, 0.1) overpriced by
  ~0.6–1.1 pp, bucket [0.9, 1.0) underpriced by ~1–3 pp — comparable to,
  not several times, the cost floors. The large mid-price deviations
  (+0.10 to +0.18) are all thin-n with CIs that span zero at reps=1500.
  **The large-effect scenario (~+0.06 at p≈0.80) does not appear at any
  cell where n supports it.**
- **Part 2 refutes the simple reconciling hypothesis.** ~81% of OOS
  entry volume sits in exactly the two price-extreme buckets where the
  solid calibration deviation lives — traders are *not* disjoint from
  the miscalibration. But in those cells the *entry-weighted* edge
  (`won − entry_price`, order ±0.3–3 pp, mixed sign, dragged by the rare
  large loss in a near-certain bucket) is a smaller, noisier quantity
  than the one-signed *price-weighted* deviation (−0.9 to +2.2 pp).
  Volume-weighting the deviation over where traders enter gives
  **0.0131** — at the Geopolitics floor-hi, below the Elections floor-hi.
- **Part 3 (gate open):** markets where a PIT-legally-identified
  directionally-skilled trader took a position are *more* miscalibrated
  (higher slope) than markets where none did, at every horizon — used
  strictly as a **conditioning variable on mispricing, not a copy
  signal** (see the framing note).

---

## Part 0 — the price definition (fixed before any calibration result)

**The price for a market at lead time `h` is the `trades.price` of the
LAST trade at or before `(tape_end − h)`, normalised to P(Yes):**
`p_yes = price` if that trade's `outcome` is `'Yes'`, else `1 − price`
(`trades.price` is P(the trade's own outcome) — established in
trading-swarm `3c22b0c`). A market contributes to lead time `h` iff it
was trading at `tape_end − h` (tape duration ≥ h).

**Justification (no reference to any calibration output):**
- **Anchor = `tape_end` (`MAX(trades.timestamp)`), not `resolution_date`.**
  O-36: `resolution_date` has ~11% logically-impossible values;
  `tape_end`-anchored lag is 100% coverage with zero negative-lag
  artifacts.
- **Last trade at a stated lead time, not a VWAP window.** The median
  market in this population has **8 trades over its whole life** (p25 =
  3), so a window is mostly a single price anyway, and a volume-weighted
  average would silently weight by an endogenous quantity.
- **"The market's price" is not one number** for a market that traded
  for weeks. Calibration-at-lead-time needs exactly this: the last
  observable price `h` before the tape ended.
- Lead-time ladder `h ∈ {0.5 h, 3 h, 12 h, 3 d, 14 d, 45 d}` — spans the
  range the literature says matters (sub-hour → beyond a month),
  spacing chosen from the tape-duration distribution (below), fixed
  before computing any rate.

---

## Part 1 — calibration of the canonical population's own markets

### Population **[V]**

Predicate: `monitoring.column_definitions.backtest_window_sql` with an
early `window_start`, i.e.
`markets.resolved = 1 AND markets.category IN ('Geopolitics','Elections')
AND (markets.trade_gap_flag = 0 OR IS NULL)`, anchored on the
`tape_end` CTE (`SELECT market_id, MAX(timestamp) FROM trades GROUP BY
market_id`), restricted to `winning_outcome IN ('Yes','No')`.

| | count |
|---|---|
| canonical resolved gap-clean Geo/Elec markets | **9,799** (3,599 Geopolitics + 6,200 Elections) |
| non-binary `winning_outcome` (Down/Up/Under/named-candidate…) — **excluded** (P(Yes) not defined in a multi-way book) | 60 |
| **used** | **9,739** (2,835 resolved YES = **29.1%**, 6,904 resolved NO = 70.9%) |
| with an `event_cluster_labels.cluster_id` | 4,693 |
| no cluster label → treated as a singleton cluster | 5,046 |

Tape-duration distribution (`tape_end − first_trade`, hours): p25 16.4,
median 142.6 (~6 d), p75 737.6 (~31 d), p90 2,106 (~88 d). **14.9% of
markets never reach 1 h of trading**; 25.5% exceed 30 days.

### 1a — pooled logistic recalibration slope, per lead time

Fit `P(y = 1) = sigmoid(b0 + b1 · logit(p_yes))` by weighted IRLS;
`b1` = recalibration slope; CI via two-way clustered bootstrap
(`reps=1500`, clustered on `event_cluster` **and** `market`).

| lead time `h` | n markets | n clusters | **slope b1** | 95% CI | CI excl. 1.0? |
|---|---|---|---|---|---|
| ~0.5 h | 8,356 | 7,202 | **1.293** | [1.196, 1.417] | yes |
| ~3 h | 8,094 | 6,952 | **1.228** | [1.135, 1.331] | yes |
| ~12 h | 7,506 | 6,406 | **1.140** | [1.052, 1.238] | yes |
| ~3 d | 5,767 | 4,808 | **1.123** | [1.031, 1.231] | yes |
| ~14 d | 3,745 | 3,112 | **1.155** | [1.031, 1.305] | yes |
| ~45 d | 1,836 | 1,523 | **1.149** | [0.983, 1.386] | no (thin) |

External prediction (arXiv 2602.19520): ~0.99 at 0–1 h **rising** to
~1.32 beyond a month.

**Direction agrees** — slope > 1 at every lead time, CI excluding 1.0 at
five of six; prices are compressed toward 50% (longshots slightly
overpriced, favourites slightly underpriced), i.e. underconfidence, as
the external political-market finding says.

**Shape disagrees** — this project's pooled slope *falls* from 1.29 at
~30 min to ~1.12–1.16 at days-to-weeks and is flat thereafter; it is
**highest near resolution**, the reverse of the external 0.99 → 1.32
*rise*. Reported as a discrepancy with the external literature — which,
per the task's own premise, disagrees with itself — **not reconciled**.
(No committed *project* finding is contradicted: every prior project
measurement is entry-weighted; this is price-weighted.)

### 1b — the calibration curve is concentrated at the price extremes

Realised YES rate per price decile, deviation `= realised − mean p_yes`
in edge units, two-way clustered bootstrap CI. Full per-decile tables
for all six lead times are in the artifact; the pattern at every lead
time:

| price decile | n (h≈0.5h) | p_yes mean | realised YES rate | deviation (edge units) | 95% CI |
|---|---|---|---|---|---|
| **[0.0, 0.1)** | 4,745 (≈57% of pop) | 0.015 | 0.006 | **−0.0089** | [−0.0123, −0.0050] |
| [0.1, 0.9) — eight buckets | ~200–420 each | — | — | point estimates −0.06 … +0.13, no pattern | **all span zero** |
| **[0.9, 1.0)** | 1,439 (≈17% of pop) | 0.979 | 0.990 | **+0.0106** | [−0.0001, +0.0177] |

Deviation in the extremes, by lead time (the two buckets that carry the
slope):

| lead time | [0.0, 0.1) dev [CI] (n) | [0.9, 1.0) dev [CI] (n) |
|---|---|---|
| ~0.5 h | −0.0089 [−0.0123, −0.0050] (4,745) | +0.0106 [−0.0001, +0.0177] (1,439) |
| ~3 h | −0.0079 [−0.0119, −0.0031] (4,506) | +0.0103 [−0.0039, +0.0208] (1,122) |
| ~12 h | −0.0053 [−0.0104, +0.0007] (4,205) | +0.0120 [−0.0054, +0.0233] (948) |
| ~3 d | −0.0059 [−0.0122, +0.0016] (3,374) | **+0.0221 [+0.0021, +0.0349]** (617) |
| ~14 d | −0.0087 [−0.0161, +0.0014] (2,206) | +0.0224 [−0.0083, +0.0423] (308) |
| ~45 d | −0.0057 [−0.0174, +0.0108] (1,072) | +0.0296 [−0.0233, +0.0506] (125) |

The slope > 1 is **driven almost entirely by these two extreme,
well-populated buckets**; the eight middle deciles hold ~200–420 markets
each and every one has a deviation CI that spans zero at reps=1500. The
overpriced-longshot effect (bucket 0) is CI-solid only at the shortest
lead times (0.5 h, 3 h); the underpriced-favourite effect (bucket 9) is
CI-solid at ~3 d. **All solid deviations are ≈ 0.006–0.022 in edge
units — comparable to the cost floors, not several times them.**

### 1c — per category (cost floors differ 4×)

| lead time | Geopolitics slope [CI] (floor 0.0005–0.010) | Elections slope [CI] (floor 0.0056–0.020) |
|---|---|---|
| ~0.5 h | **1.455** [1.260, 1.735] | 1.227 [1.105, 1.369] |
| ~3 h | **1.384** [1.219, 1.583] | 1.160 [1.053, 1.289] |
| ~12 h | 1.204 [1.066, 1.391] | 1.114 [1.002, 1.241] |
| ~3 d | 1.177 [1.022, 1.365] | 1.106 [0.987, 1.259] |
| ~14 d | 1.147 [0.953, 1.422] | 1.169 [1.015, 1.371] |
| ~45 d | 1.307 [1.010, 1.850] | 1.095 [0.923, 1.355] |

Geopolitics carries the higher slope at the short lead times (1.46 / 1.38
at 0.5 h / 3 h, CI well above 1) and shows the same near-resolution peak
and decline; Elections is milder (~1.1–1.2, CI marginal on 1.0 at the
longer horizons). The 4× cost-floor difference means the same slope is
"worse" for Elections, but Elections' deviations are the weaker of the
two.

### 1d — cells whose deviation CI excludes ±(category cost-floor lower bound)

| lead time | category | price decile | deviation [CI] | n | clears floor-hi too? | note |
|---|---|---|---|---|---|---|
| ~0.5 h | Geopolitics | [0.0, 0.1) | −0.0111 [−0.0152, −0.0051] | 1,938 | yes (\|dev\| > 0.010) | **solid** |
| ~3 h | Geopolitics | [0.0, 0.1) | −0.0097 [−0.0153, −0.0026] | 1,857 | no | **solid** |
| ~3 h | Geopolitics | [0.9, 1.0) | +0.0198 [+0.0022, +0.0290] | 459 | no | **solid-ish** (\|dev\| ≈ 2× geo floor-hi) |
| ~3 h | Geopolitics | [0.8, 0.9) | +0.1000 [+0.0182, +0.1495] | 117 | yes | **THIN** (n = 117) |
| ~12 h | Geopolitics | [0.3, 0.4) | +0.1805 [+0.0178, +0.3444] | 95 | yes | **THIN** (n = 95) |
| ~45 d | Geopolitics | [0.9, 1.0) | +0.0510 [+0.0320, +0.0723] | **14** | yes | **VERY THIN** (n = 14 — bootstrap unreliable) |

**The gate is OPEN** — Part 3 runs. But the deviations that clear the
floor **with defensible n** (> 400) are all Geopolitics, at the price
extremes, magnitude **≈ 0.010–0.020 in edge units** — right at the
Geopolitics cost-floor upper bound, below the Elections one. **The
large-effect scenario (~+0.06 at p ≈ 0.80) does not appear at any cell
where n supports it**; every p ∈ [0.5, 0.9) bucket with n > 200 has a
deviation CI spanning zero. **No Elections cell clears its own floor.**

---

## Part 2 — where the traders actually are

OOS positions (post-`T_SPLIT`, binary Geo/Elec, gap-clean): **151,360
positions, ≈ $100.75 M volume**. Each binned to a `(price decile ×
time-to-resolution band)` cell by its `p_yes` at entry and its
`tape_end − entry_timestamp`. `entry_weighted_edge` = the
project-standard `won − entry_avg_price` (the trader's *own* outcome's
price), volume-weighted per cell.

### 2a — entry volume by price decile and by TTR band

| price decile | share of OOS volume |
|---|---|
| **[0.0, 0.1)** | **≈ 58%** |
| **[0.9, 1.0)** | **≈ 22%** |
| [0.1, 0.9) — eight deciles | ≈ 19% combined |

| TTR band at entry | share of OOS volume | n positions |
|---|---|---|
| 0–1 h | ≈ 6% | 3,437 |
| 1–6 h | ≈ 14% | 5,245 |
| 6–24 h | ≈ 5% | 8,243 |
| 1–7 d | ≈ 41% | 36,472 |
| 7–30 d | ≈ 22% | 49,604 |
| > 30 d | ≈ 12% | 48,536 |

**~81% of trader entry volume is in the two price-extreme buckets — the
same two buckets that carry the solid Part 1 calibration deviation.**

### 2b — overlap, quantified

| metric | value |
|---|---|
| Pearson( \|deviation\| , volume-fraction ) across cells | **−0.221** |
| volume-weighted mean \|deviation\| | **0.0131** |
| plain (unweighted) mean \|deviation\| | **0.0227** |
| OOS volume fraction in cells whose *pooled* Part 1 deviation CI excludes ±geo-floor-lo (0.0005) | **0.255** |
| OOS volume fraction in cells whose *pooled* Part 1 deviation CI excludes ±elec-floor-lo (0.0056) | **0.000** |

The Pearson correlation is negative but **dominated by the many thin
mid-price cells** (large \|deviation\| point estimate, ≈ zero volume);
the *mass* of both distributions is in the extremes, where they
coincide. Volume-weighting roughly **halves** the average deviation
(0.0131 vs 0.0227). The three pooled cells that clear the geo floor-lo
and hold volume: `0–1 h × [0.0, 0.1)` (4.7 % of volume), `1–6 h × [0.0,
0.1)` (7.9 %), `1–7 d × [0.9, 1.0)` (12.9 %) — total **25.5 %** of OOS
volume. **Zero** OOS volume sits in a cell whose deviation CI clears the
Elections floor-lo.

### 2c — the entry-weighted vs price-weighted gap, in the cells that hold the volume

| cell (TTR band × decile) | OOS vol share | n pos | entry-weighted edge (`won − entry_price`) | Part 1 price-weighted deviation [CI] |
|---|---|---|---|---|
| 1–7 d × [0.0, 0.1) | 22.9 % | 13,054 | **−0.0069** | −0.0059 [−0.0122, +0.0031] |
| 7–30 d × [0.0, 0.1) | 12.3 % | 21,423 | **−0.0307** | −0.0087 [−0.0158, −0.0019] |
| 1–7 d × [0.9, 1.0) | 12.9 % | 5,681 | **+0.0054** | +0.0221 [+0.0072, +0.0387] |
| > 30 d × [0.0, 0.1) | 7.2 % | 35,037 | **+0.0229** | −0.0057 [−0.0143, +0.0073] |
| 1–6 h × [0.0, 0.1) | 7.9 % | 1,270 | +0.0026 | −0.0079 [−0.0119, −0.0031] |
| 0–1 h × [0.0, 0.1) | 4.7 % | 1,630 | +0.0014 | −0.0089 [−0.0123, −0.0050] |

**Plainly: the cells with the largest solid calibration deviation ARE
the cells where traders enter.** ~81 % of OOS volume is in the two
price-extreme deciles; the solid Part 1 deviations are in those same two
deciles. The simple **"miscalibration lives where nobody trades"
reconciling hypothesis is refuted** — the deviation and the entry
density are not disjoint, they coincide on the mass.

What reconciles the project's entry-weighted nulls with a non-zero
price-weighted deviation is **the weighting itself**: in the same cells,
the entry-weighted edge (`won − entry_price`, order ±0.003–0.03,
mixed sign, dragged around by the rare catastrophic loss in a
near-certain bucket) is a small and noisier quantity than the
price-weighted deviation (order −0.009 to +0.022, one-signed per
bucket). Volume-weighting the deviation over where traders actually
enter gives **0.0131** — at the Geopolitics floor-hi, below the
Elections floor-hi. Traders are in the right cells; entry-weighting
lands them near zero anyway.

---

## Part 3 — calibration conditioned on directionally-skilled-trader presence

**CRITICAL FRAMING.** Skilled-trader presence is used here as a
**conditioning variable on market mispricing, NOT as a copy signal.**
The 2026-09-10 copy-trade decay result stands: there is **no
demonstrable edge to inherit from a trader's entry**. This asks a
different question — whether the *presence* of a PIT-legally-identified
directionally-skilled trader *marks* a mispriced market — and the answer
is actionable at one's **own** entry time and price, which copying is
not. This is not the copy thesis and must not be read as reviving it.

Instrument: the PIT-legal directional-skill pool
(`directional_skill_pit_legal_pool_20260906T160303Z.json`,
`raw_skilled_traders`, the harness calibrated at ~5% raw / BH=0 across 36
zero-skill cells on 2026-09-06). A population market is "skilled-present"
iff ≥ 1 of those traders holds any position in it.

| | count |
|---|---|
| PIT-legal `raw_skilled_traders` | 1,494 |
| population markets with ≥ 1 skilled-trader position | 5,619 of 9,739 (57.7 %) |

Slope, skilled-present vs skilled-absent, per lead time (two-way
clustered bootstrap; no stratum was thin; per-cell curves in the
artifact):

| lead time | skilled-present slope [CI] (n) | skilled-absent slope [CI] (n) | present CI excl. 1.0 | absent CI excl. 1.0 |
|---|---|---|---|---|
| ~0.5 h | **1.400** [1.258, 1.584] (5,355) | 1.178 [1.041, 1.347] (3,001) | yes | yes |
| ~3 h | **1.310** [1.192, 1.470] (5,244) | 1.122 [0.990, 1.297] (2,850) | yes | no |
| ~12 h | **1.197** [1.089, 1.336] (4,989) | 1.049 [0.907, 1.225] (2,517) | yes | no |
| ~3 d | **1.169** [1.059, 1.312] (4,094) | 1.037 [0.885, 1.242] (1,673) | yes | no |
| ~14 d | **1.175** [1.036, 1.354] (2,857) | 1.123 [0.900, 1.491] (888) | yes | no |
| ~45 d | 1.174 [0.994, 1.424] (1,489) | 1.074 [0.781, 1.757] (347) | no (marginal) | no |

**Skilled-present markets carry a higher recalibration slope at every
lead time. The present-slope CI excludes 1.0 at five of six horizons;
the absent-slope CI excludes 1.0 at only one (~0.5 h). But the present
and absent CIs overlap at every horizon** (e.g. 0.5 h: [1.258, 1.584]
vs [1.041, 1.347]) — the present-minus-absent gap is a **consistent
direction across all six lead times, not a per-horizon-significant
difference**. Whether this is skilled traders selecting into mispriced
markets, or a compositional artifact (skilled-present markets are the
majority — 58 % — and plausibly larger, longer-lived, or a different
market-type mix), is **not resolved** by this measurement. Used only as
stated: a marker on the market, evaluable at one's own entry price — not
a copy signal.

---

## What was NOT determined

- **Whether the mid-price-decile deviations are real.** In this
  population buckets [0.1, 0.9) hold ~200–450 markets each at short lead
  times and fewer at long ones; their deviation CIs span zero at
  reps=1500. The large point estimates (+0.10 to +0.18) are not
  distinguishable from noise.
- **Why the slope shape disagrees with the external literature**
  (falling here, rising there). Candidates not chased: the 29% YES base
  rate and its interaction with the logit-linear form; this population's
  market-type mix (many short-lived "will X say Y this week" markets);
  the tape-end anchor vs the external studies' clock. Reported as a
  discrepancy, not reconciled.
- **Whether Part 3's present-vs-absent slope gap is causal or
  compositional.** Skilled-present markets are the majority and are
  plausibly larger / longer-lived / different in type; this measurement
  does not control for that.
- **The sign question.** A calibration deviation is exploitable in
  either direction (take the cheap side); deviations are reported
  signed, and "excludes the cost floor" means the CI clears ±floor.
- **Anything about tradeability net of execution.** This is a
  descriptive calibration measurement — no slippage, no fill model, no
  size. A deviation clearing a cost floor is necessary, not sufficient.
- **Whether "presence" should be all-time or post-split.** All-time
  positions were used (the question is whether the market is the kind
  that attracts a skilled trader, not a timing signal).
- **Coverage at ~45 d.** Only ~1,836 markets trade that long; the
  ~45 d row and its per-category splits are the thinnest and most
  bootstrap-degenerate.

---

## Reproducibility

- **Script:** `scripts/own_market_calibration.py` (first-repo,
  committed with this result). Read-only; `--persist` never passed.
  Reuses the project's two-way clustered-bootstrap pattern
  (`np.bincount(rng.integers(...))` multipliers on the two cluster
  dimensions, `seed=42`, `reps=1500`), matching
  `weighted_two_way_gap_bootstrap`. Logistic slope by weighted IRLS
  (2 params), bootstrapped identically. `--selfcheck`: p_yes ∈ [0,1];
  hand-vs-vectorised rate identity; slope ≈ 1.0 on synthetic
  perfectly-calibrated data.
- **Artifact:**
  `data/characterizations/own_market_calibration_20260910T204249Z.json` — the price
  definition string, the anchor, all bucket boundaries (price deciles,
  the six lead times, the six TTR bands), seeds, `reps`, per-cell `n`
  and `n_clusters`, every calibration curve, every slope + CI, the
  Part 1 cost-floor-clearing cell list, the full Part 2 cell grid with
  entry-weighted edges and the overlap statistics, and Part 3's
  present/absent curves and slopes.
- **Stop conditions — none tripped:** the price definition was fixed
  structurally, with no reference to any calibration output;
  `metric_v2f_oos_result` sha256
  `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
  unchanged before and after; Part 1's deviations are **not** entirely
  within the cost floors (the gate opened, Part 3 ran); no figure
  contradicts a *committed project* finding — the project's nulls are
  entry-weighted, this is price-weighted, and the task's own premise is
  that the two can differ.
- **Tests:** `run_tests.py` (not bare pytest) — **25 files, 25 passed,
  0 failed** (339,909 assertions). The new script adds no test file and
  touches no existing module; the suite is unchanged and green.
- **`script_commit` in the artifact** is `1f43424` (HEAD at run time);
  the script itself lands in the result commit (parent `1f43424`).
