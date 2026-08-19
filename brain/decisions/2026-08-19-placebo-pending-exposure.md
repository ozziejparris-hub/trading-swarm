# 2026-08-19 — materiality of the 2 placebo-survivor traders in the pending-invariant regression

Read-only. No repair, no re-running of the thesis result, no change to
`daily_maintenance.py` or `backfill_trade_results_geo.py`. Every claim
tagged **[V]** (verified — command/query/file:line given) or **[I]**
(inferred, explicitly marked). Findings recorded here only, per the
standing instruction.

Committed script: `scripts/characterize_placebo_pending_exposure.py`
(first-repo). Re-run: `python3 scripts/characterize_placebo_pending_exposure.py`.
Writes a timestamped JSON artifact to `data/characterizations/`. Today's
run: `data/characterizations/placebo_pending_exposure_20260819T173821Z.json`.

---

## Q1 — Identify

**[V]** The 2 traders, from
`2026-08-19-pending-invariant-regression.md`'s Q6 (re-confirmed live this
session, same result):

```
0x54b5eacb474921051d62ad0f6ae2f4fc31b92e90
0x5cfd881133ff44d1f7b81ea8a819a30dfc39ca1b
```

Persisted for future diffing at
`data/characterizations/placebo_pending_exposure_20260819T173821Z.json`
(`traders` key) alongside every figure below.

---

## Q2 — Per-trader materiality

**[V]** "Full footprint" = every position in the Geopolitics/Elections,
non-gap, `resolved=1`, `entry_avg_price IS NOT NULL` population for that
trader — the exact shape `build_presplit_cohort`/`measure_oos` query
(`trader_skill_metric_v2f.py:236-247,315-330`), minus their `trade_result`
restriction, so it includes both evaluated and stuck-pending positions.

| trader | positions (total) | markets (total) | stuck (pending) | stuck markets | stuck % positions | stuck % markets |
|---|---|---|---|---|---|---|
| `0x54b5eacb...` | 21 | 15 | 2 | 1 | **9.5%** | **6.7%** |
| `0x5cfd8811...` | 90 | 78 | 26 | 22 | **28.9%** | **28.2%** |

**These are not the same shape of exposure, per yesterday's lesson.**
`0x54b5eacb...` has a small footprint overall (21 positions) and a small,
single-market stuck exposure (2 positions, same market — see Q6 detail).
`0x5cfd8811...` has a much larger footprint (90 positions, 78 markets) and
nearly **a third of it** is currently stuck-pending — this is the trader
that carries essentially all of the material exposure identified here.

---

## Q3 — Share of the placebo

**[V]** Against the persisted `metric_v2f_oos_result` reference (`kind='placebo'`,
2026-08-15, generator commit `eaeabbc`): n=2,569 positions, 110 traders.
(No row-level snapshot exists in that table — only aggregates — so "share"
below is today's live re-derivation of what these 2 traders' evaluated
positions look like now, not a lookup into the exact 08-15 computation;
flagged, not glossed over.)

- 2 traders / 110 = **1.8%** of the placebo's trader count.
- Their currently-evaluated (already counted) positions: 19 + 64 = **83**
  = **3.2%** of the persisted 2,569.
- Their **stuck-pending** positions: 2 + 26 = **28** = **1.09%** of the
  persisted 2,569.

---

## Q4 — What the stuck state does to the edge

**[V] Drops out entirely — does not enter with a wrong or missing outcome.**
Both `build_presplit_cohort` (line 245) and `measure_oos` (line 326) join
the position's entry trade via `json_extract(p.entry_trade_ids, '$[0]')`
and filter `t.trade_result IN ('won', 'lost')`. A position whose entry
trade has `trade_result='pending'` fails that filter and is **excluded from
the query result set entirely** — it never reaches the pandas DataFrame
the edge/gap is computed over. This is the **same harm shape as the
no-FIFO-close markets** (thinning: reduces n, does not inject a biased
value) — a different specific gate (`trade_result` filter, not
`position_tracker.py`'s FIFO-close logic) producing the same qualitative
effect. Confirmed by code inspection, not by re-running the pipeline.

---

## Q5 — Direction, if determinable

**[V] Determinable — unlike the orphan-SELL case, these positions have real
entry prices.** Derived the win/lose rule empirically before applying it:
across all **350,008** currently-evaluated positions in this population,
`position.outcome == market.winning_outcome` predicts `trade_result='won'`
with **zero exceptions** (`characterize_placebo_pending_exposure.py`'s
`verify_empirical_rule`). Applied that verified rule to the 28 stuck
positions (all resolved, `winning_outcome` set for all 28 — fully
determinable, no undetermined cases):

| trader | counterfactual won | counterfactual lost | mean counterfactual edge |
|---|---|---|---|
| `0x54b5eacb...` | 0 | 2 | **-0.451** |
| `0x5cfd8811...` | 22 | 4 | **+0.077** |

**The two traders point in opposite directions.** `0x54b5eacb...`'s 2
stuck positions would both have been losses (a bad EU-tariffs bet entered
twice at 0.76 and 0.14 that resolved "Yes" against a "No" position) —
including them would pull the placebo **down**. `0x5cfd8811...`'s 26
stuck positions are dominated by high-confidence favourite bets ("Nothing
Ever Happens"-style No positions on Iran-strike/Iran-regime-collapse
markets at prices 0.82-0.99, mostly correct) that would mostly have
**won** — including them would pull the placebo **up**, and this trader's
26 positions numerically dominate the pair's combined 28.

Combined, simple unweighted mean across all 28: **+0.0396** (script
output, `combined_stuck_simple_mean_edge_UNWEIGHTED`). This is **not** the
metric's actual point estimate — the real calculation is a cap5-weighted,
two-way trader×market clustered bootstrap
(`weighted_two_way_gap_bootstrap`, `trader_skill_metric_v2d.py:175`), not
a flat mean over raw positions — reported here only as an
order-of-magnitude illustration, per the task's instruction not to
recompute the placebo.

---

## Q6 — Pre-split or post-split

**[V]** Both boundaries checked, kept separate (they answer different
questions and use different anchors in the codebase itself —
`presplit_by_tape_end` is market-level `tape_end <= T_split`, matching
`build_presplit_cohort`'s own qualification boundary; `postsplit_by_entry_timestamp`
is position-level `entry_timestamp > T_split`, matching `measure_oos`'s own
edge-measurement boundary):

| trader | stuck (n) | pre-split by tape_end | post-split by entry_timestamp |
|---|---|---|---|
| `0x54b5eacb...` | 2 | 2 | 0 |
| `0x5cfd8811...` | 26 | 14 | 9 |

`0x54b5eacb...`'s entire stuck exposure is pre-split (both positions in
the same single market, entered April 2025, resolved before T_split) —
this can only affect **placebo qualification** (whether/how they matched
into the pool), not the measured edge.

`0x5cfd8811...` has exposure on **both** sides: 14 pre-split-qualifying
positions and 9 post-split positions that would, if evaluated, enter the
**actual measured OOS edge** directly (`entry_timestamp` after
2026-04-01 — e.g. the "Will Keiko Fujimori win..." and several
Iran/Russia-conflict markets from April-May 2026). The counts don't sum to
26 because the two classifications use different anchors (market-level
tape_end vs this trader's own position-level entry time) — both are
reported as computed, not reconciled into one number.

---

## Q7 — Would it move the comparison

**[V] Exposure is small in aggregate; the reader should weigh the split
by direction and by trader, not the raw total alone.** 28 positions
against the placebo's persisted n=2,569 is **1.09%** of the raw position
count. The placebo's CI is [-0.0210, +0.0461] around a point estimate of
+0.0127 — a width of ~0.067; 28 positions is a small fraction of the 2,569
that CI was built from.

**Caveat on what "1.09%" means:** the actual metric weights by
(trader, market) pair with a cap5 weight function (`min(n_pair_positions, 5)`,
`trader_skill_metric_v2c.py:190`), not raw position count, so 1.09% of
positions is not identical to 1.09% of the bootstrap's effective weight —
computing the exact weight share would mean re-running
`weighted_two_way_gap_bootstrap` on an augmented dataset, which is
explicitly out of scope here (task instruction: do not recompute the
placebo). As an upper-bound proxy on raw scale, it stays small either way:
`0x5cfd8811...`'s 22 new (trader,market) pairs would mostly enter at
weight 1-2 each (most of their stuck markets have 1 position, a few have
2 — see script output — well under the cap5 ceiling), so their pair-level
weight contribution is not inflated relative to their position count.

**Directionally, the two traders substantially offset each other** — one
trader's exposure would pull down, the other's (larger) exposure would
pull up. This is not the same failure mode as a single-direction bias; it
looks more like noise than a systematic push on the placebo's point
estimate, though with n this small any characterization of "noise vs
signal" is itself uncertain and not something this pass attempts to
resolve statistically.

---

## Verdict: **NEGLIGIBLE**, with one flagged caveat

**Aggregate scale:** 28 stuck positions against the placebo's persisted
2,569 (1.09%) is too small to plausibly be the dominant driver of where
the placebo's point estimate or CI sits. Not zero, not silently
dismissed — quantified, and it is small.

**Direction:** the two traders' exposure points in opposite directions
(`0x54b5eacb...` down, `0x5cfd8811...` up) and does not read as a
consistent bias in either direction on the aggregate.

**The one thing this verdict does not erase:** `0x5cfd8811...` individually
has **28.9%** of their own placebo-relevant footprint currently stuck and
unevaluated, with 9 of those 26 positions falling **post-split** — i.e.
directly inside the measured-edge window, not just the qualification
window. If this specific trader's contribution is ever examined
individually (rather than only in aggregate), that 28.9% figure is the one
that matters, not the 1.09%-of-placebo aggregate figure. Both are true
simultaneously and are reported as such, per the instruction not to
collapse trader-level and population-level materiality into one number.

**What would close the gap:** running `backfill_trade_results_geo.py` (or
wiring it into `daily_maintenance.py`, per the prior doc's open
recommendation) would evaluate these 28 positions for real and let the
metric's actual weighted computation include them, rather than leaving
their materiality as an estimate — not attempted here, per the read-only
constraint.

---

*Generated 2026-08-19. Sources: `2026-08-19-pending-invariant-regression.md`
(this arc's prior doc), `scripts/trader_skill_metric_v2f.py` (build_presplit_cohort
line 236, measure_oos line 315, T_SPLIT constant line 135),
`scripts/trader_skill_metric_v2d.py` (weighted_pair_table line 164,
weighted_two_way_gap_bootstrap line 175), `scripts/trader_skill_metric_v2c.py`
(WEIGHT_FNS['cap5'] line 190), `metric_v2f_oos_result` (persisted 2026-08-15,
generator commit `eaeabbc`), and this session's new
`scripts/characterize_placebo_pending_exposure.py` (first-repo) →
`data/characterizations/placebo_pending_exposure_20260819T173821Z.json`
(first-repo, both committed this session).*
