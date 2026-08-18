# 2026-08-18 — Characterizing the `markets.resolved=1` / `trades.trade_result='pending'` inconsistency

Read-only characterization. No repair, backfill, or reconciliation performed.
Standing project instruction applied throughout: every statement below is
tagged **[V]** (verified — command/query/file:line given) or **[I]**
(inferred/plausible, explicitly marked). Unverifiable points are stated in
place with what would settle them. This document is the only findings
artifact for this task — nothing was written to agent memory.

**Background claims in the task prompt — checked, not assumed:**
- "88 markets... 2026-08-16 recon" — **[V]** confirmed against
  `2026-08-16-canonical-infrastructure-recon.md:135-144`, which gives the
  exact population definition reused below.
- "Today's census reproduced... got 101" — **[V]** confirmed against
  `2026-08-18-system-state-census.md` row 1 (canonical=6,877, diff=263,
  pending=101, ad-hoc, timestamped ~18:01 UTC today per that doc's own
  generation time).
- "the other component is 166 markets with trades but no FIFO-closed
  position" — **[V]** matches the recon doc exactly (166/254, 65.4%).
- "edge = won - entry_price requires a closed position" — **[I]**
  plausible restatement of why `trade_result IN ('won','lost')` gates v2f's
  population (`scripts/trader_skill_metric_v2f.py:245`); not independently
  re-derived from the edge formula itself, out of scope here.
- "148-trader qualifying cohort" — **[V]** exists as a *prose* figure
  (`2026-08-15-skill-metric-rebuild.md:39`, `2026-08-16-session-summary.md`)
  but **[V]** has **no persisted membership snapshot** — confirmed again
  today (`2026-08-16-session-summary.md:33`; no table/file found matching
  it in this investigation either, see Q5). The number itself was not
  re-derived from a query in this task; treat it as a documented-but-
  unpinned figure, not independently reproduced here.
- T_split = 2026-04-01 00:00:00 — **[V]** `scripts/trader_skill_metric_v2f.py:135`.

---

## Q1 — Current count and rate

**Committed script:** `scripts/characterize_pending_resolution_inconsistency.py`
(first-repo). Re-derives the canonical population
(`monitoring/column_definitions.py:469-499`, `backtest_window_sql`'s actual
WHERE/JOIN shape) and the v2f implicit population
(`scripts/trader_skill_metric_v2f.py:236-247`'s WHERE clause), reports the
pending-entry-trade subset of their symmetric difference, and writes a
timestamped JSON artifact recording its generating parameters (window_end,
db path, run timestamp). Re-run with:
```
python3 scripts/characterize_pending_resolution_inconsistency.py [--window-end "2026-04-01 00:00:00"] [--no-window]
```

**[V] Run at 2026-08-18T18:28:36Z** (artifact:
`data/characterizations/pending_resolution_inconsistency_20260818T182836Z.json`,
first-repo, window_end = T_split, matching the 08-16/08-18 methodology
exactly): canonical population = **6,878**, v2f population = 6,614,
symmetric diff = **264**, pending-inconsistency count = **103**.

This does not exactly match the 08-18 census's ad-hoc 101 (nor 08-16's 88)
— **[V]** and that is expected, not a discrepancy to explain away: this run
was ~27 minutes after the census's ~18:01Z reading, and the count grew by
+2 in that interval (canonical grew by only +1 over the same interval,
meaning at least one market already in the canonical population
transitioned into the pending-inconsistent state, not merely a new
canonical market appearing already-pending). Net growth across all three
observed points (88 → 101 → 103, over ~2 days then ~27 minutes) has been
monotonically upward with no observed decrease. **[I]** A +2 change in 27
minutes is far too fast to be explained by an infrequent manual backfill
script's cadence (see Q3) — it is much more consistent with the
continuously-running live monitor writing `resolved=1` on markets whose
trades have never been evaluated, at the live loop's own ~15-minute cadence
addressed in Q3.

**Bucketing:** by `tape_end` (`MAX(trades.timestamp)` per market), **not**
`markets.resolution_date` — **[V]** `resolution_date` is documented
elsewhere (O-36, the `resolution_date` COALESCE-guard work) as unreliable
and mutable with no audit trail, so it is not used as an ordering key here.
`tape_end` is a reliable, append-only signal for "when trading on this
market last happened," though it is *not* strictly a resolution timestamp
either — see the caveat below.

Monthly buckets of the 103 pending markets (by `tape_end`, all necessarily
< T_split = 2026-04-01 by construction of the window):
```
2024-06:1  2024-07:9  2024-09:4  2024-10:6  2024-11:2  2025-01:1  2025-02:3
2025-03:2  2025-04:14 2025-06:1  2025-07:1  2025-08:1  2025-09:6  2025-10:12
2025-11:20 2025-12:3  2026-01:4  2026-02:4  2026-03:9
```
**[V]** This is spread across 19 months from mid-2024 through March 2026,
with two bursts (2025-04: 14, 2025-11: 20 — together 33% of the set) but
**not** concentrated near the T_split boundary (2026-03 has only 9 of 103).
**Finding: this is broad historical residue plus continued accrual, not a
recent-onset phenomenon.** The framing "growth of ~13 over two days
suggesting active production" in the task prompt is **[I]** partially
right (there is measurable, fast ongoing accrual — see the 27-minute delta
above) but **[V]** wrong if read as "the underlying markets are recent" —
most of the affected markets' last trading activity is over a year old;
what's active is the *writer* creating new inconsistencies, not the
markets themselves.

---

## Q2 — Which side is wrong

**[V] Directly checked, not inferred:** for 2 of the 103 pending markets,
fetched live state from the public Polymarket Gamma API (read-only GET,
network reachable from this environment):

| market_id | DB winning_outcome | API `closed` | API `umaResolutionStatus` | API `outcomePrices`/`outcomes` | Agreement |
|---|---|---|---|---|---|
| `0x025b3399...93ae` (api_id 631443, "Will Trump say... Egypt summit?") | No | true | resolved | `["0","1"]` / `["Yes","No"]` | **[V]** DB's "No" matches API's No=1 exactly |
| `0xabc5dea0...de807` (api_id 534972, "Will Loren Taylor win the Oakland mayoral race?") | No | true | resolved | `["0","1"]` / `["Yes","No"]` | **[V]** matches |

**Finding: 2/2 sampled markets genuinely resolved on Polymarket; `markets.resolved=1` is a true positive in both cases. `trades.trade_result='pending'` is stale — the trades were simply never evaluated, not because the market didn't resolve.**

**[I]** This is a small sample (n=2 of 103, chosen as the first market and
one from the largest 2025-11 burst-adjacent region, not a randomized draw)
— treat as strong directional evidence, not a proven population-wide
claim. **A third sample checked without an `api_id`**
(`0xd8d7ffaf...a3b6c4`) — **[V]** its `resolution_date` is exactly
`2026-03-31 00:00:00`, a suspiciously round value one day before T_split;
**[UNVERIFIABLE-HERE]** whether this is a real resolution timestamp or a
synthetic/default fill — the market has no `api_id` to cross-check against
the live API by this path; settling it would require locating the
market by `condition_id` or title against the Gamma/CLOB API directly, not
attempted further here (out of budget for this task).

**What would fully settle Q2 for the whole population:** run the same
live-API cross-check against a random (not first-N) sample of, say, 20 of
the 103 markets, ideally stratified by whether `api_id` is present.

---

## Q3 — What writes each field

**`markets.resolved`** — **[V]** grep-confirmed write sites (`UPDATE
markets SET resolved`):
- `monitoring/database.py:552` (`update_market_resolution`) — **[UNVERIFIABLE-HERE]** no caller found via grep for this specific method name in this pass; may be dead code or called via a bound-method pattern this grep missed. Not chased further.
- `scripts/fetch_market_resolutions.py:163`
- `scripts/fast_resolution_check.py:266,386,496,593` (4 sites — this is `FastResolutionChecker`, the class run by the weekly cron below)
- `scripts/backfill_o16_tier1.py:225,235`
- `scripts/backfill_o16_tier2.py:214,224`
- `scripts/fix_expired_unresolved.py:93`

**[V]** At least 6 distinct files, 10 call sites. **[V]**
`scripts/weekly_resolution_sweep.sh` (cron: `30 3 * * 0`, i.e. every Sunday
03:30, confirmed via `crontab -l`) runs `FastResolutionChecker` — one of
the writers to `resolved` — on a real recurring schedule.

**`trades.trade_result`** — **[V]** exactly one write method exists:
`monitoring/database.py:655` (`update_trade_result`, single `UPDATE trades
SET trade_result = ? WHERE trade_id = ?`). **[V]** Its only callers, found
by grepping for `update_trade_result(`, are `monitoring/trade_evaluator.py:90`
(inside `TradeEvaluator.evaluate_market_trades`) and
`scripts/evaluate_new_trader_results.py:64`. **[V]** `TradeEvaluator` is
only *instantiated* (grep for `TradeEvaluator(`) in two scripts:
`scripts/backfill_trade_results.py:31` and
`scripts/evaluate_new_trader_results.py:28`. **[V]** Neither script appears
in `crontab -l`, nor in `scripts/daily_maintenance.py` (grepped directly,
zero matches for `backfill_trade_results`).

**Finding: `trade_result` currently has no automatic or scheduled trigger anywhere in this system.** It is written only when a human manually runs
`backfill_trade_results.py`, `backfill_trade_results_geo.py`, or
`evaluate_new_trader_results.py`. `resolved`, by contrast, is written
continuously by the live monitor path and weekly by cron. **[I]** This
asymmetry — one writer continuous/scheduled, the other manual-only — is
the most likely mechanism for a gap that both exists historically (19
months of backlog) and keeps growing in near-real-time (the 27-minute
delta in Q1). **[UNVERIFIABLE-HERE]** the exact date `backfill_trade_results.py`
or `evaluate_new_trader_results.py` was last actually *run* (not just last
*edited* — `git log` only shows last code change: 2026-06-22 for
`backfill_trade_results_geo.py`, 2026-06-11 for
`evaluate_new_trader_results.py`); no execution log for either was found
under `~/trading-swarm/logs/`. Settling this would need either a run-log
convention for these scripts (none currently exists) or asking whoever
last ran them.

---

## Q4 — Transient or permanent

**[V]** Could not diff against the exact 08-16 88-market ID list — it was
never persisted to a committed file (the recon doc's `canonical_markets.txt`
/ `v2f_implicit_markets.txt` were scratch files, not found in this repo or
trading-swarm). This limits how precisely churn-vs-monotonic can be
established.

What is established: **[V]** three point-in-time counts, all from the same
canonical-population methodology, taken 08-16 (88), 08-18 ~18:01Z (101),
08-18 ~18:28Z (103) — strictly increasing, no observed decrease at any of
the three checkpoints. Combined with Q3's finding that the sole writer
which *clears* the inconsistency (`TradeEvaluator`) has no scheduled
trigger, **[I] this leans PERSISTENT, not TRANSIENT-BENIGN**: nothing in
the system currently converges these markets back to a consistent state on
its own. A timing-artifact/self-resolving story would require some
automatic process periodically re-evaluating trade results, and no such
process was found (Q3).

**[UNVERIFIABLE-HERE]**: whether the population ever *shrinks* between
manual runs of the backfill scripts (i.e., true confirmation that it is
monotonic absent human intervention, vs. occasionally reduced by an
undiscovered path). Settling this needs either a repeated run of the
committed Q1 script over the coming days/weeks, or historical log evidence
of when `backfill_trade_results*.py` was last actually executed.

---

## Q5 — Effect on thesis population

**[V]** All 103 pending markets, by construction of the window used
(`tape_end < T_split`), fall inside the canonical pre-split window.

**[V] Trader overlap, directly queried:** 65 distinct traders hold
positions in the 103 pending markets (`SELECT DISTINCT trader_address FROM
positions WHERE market_id IN (...)`). The `metric_v2f_intersection_cohort`
table (295 traders, persisted 2026-08-15T19:36:56Z, commit `eaeabbc` — the
Objective-1 "significant AND M≥10 AND edge≥0.02" cohort, which the
Objective-2 148-pre-split/120-post-split cohort and its matched placebo are
both drawn from) has **zero** overlap with those 65 traders — verified by
set intersection, `len(overlap) == 0`.

**Finding: the inconsistency does not touch a single trader or position in
the cohort that produces the metric's result of record.** This is not a
coincidence given Q6 below: the pending markets are overwhelmingly
1-trade/thin markets, and cohort membership requires M≥10 positions — thin
single-trade markets are structurally unlikely to be where a cohort
member's qualifying volume comes from.

**Caveat, per the background-claims check above:** the 148/120 cohort
itself has no persisted membership snapshot; this check used the 295-trader
Objective-1 intersection cohort (which *is* persisted and is the superset
both Objective-2 cohorts are drawn from) as the best available verifiable
proxy. **[I]** If the true 148/120 membership differs from a straightforward
subset of the 295, that would need the actual snapshot to confirm — which,
per `2026-08-16-session-summary.md:33`, doesn't exist. Given zero overlap
with the full 295-trader superset, though, overlap with any subset of it is
also necessarily zero — so this caveat does not weaken the finding.

---

## Q6 — Directional risk

**[V] Tested three properties, not just eyeballed:**

**Trade count** (`SELECT COUNT(*) FROM trades WHERE market_id=...`,
grouped): pending markets — median **1**, mean **1.73**, max 7, min 1
(n=103). Canonical baseline (all 6,879 canonical-population markets) —
median **7**, mean **47.74**. **58.3%** of pending markets have exactly 1
trade, vs **13.8%** of the baseline population.

**Category:** pending — Elections 78 (75.7%), Geopolitics 25 (24.3%).
Baseline — Elections 4,446 (64.6%), Geopolitics 2,433 (35.4%). Pending
markets are over-represented in Elections by ~11 points.

**Finding: YES, there is a clear, verified, non-random distinguishing
property.** Pending-inconsistency markets are strongly skewed toward
extremely thin (mostly single-trade) Elections markets. **The conditioning
on clean closure (trade_result IN ('won','lost')) is not selecting a random
slice of the canonical population — it is disproportionately excluding
very-low-activity markets.** This is consistent with, and likely explains,
Q5's zero-overlap finding: cohort members (M≥10 positions) are unlikely to
be the traders whose single trade sits in one of these thin markets.

**Not tested** (budget): liquidity/volume fields, resolution type,
neg_risk grouping. **[UNVERIFIABLE-HERE]** whether these add anything
beyond what trade-count and category already show — flagged, not chased.

---

## VERDICT: PERSISTENT-BOUNDED

**Permanent** (Q3/Q4: no automatic writer clears `trade_result='pending'`
once `resolved=1` is set; the count has only grown across all three
observed checkpoints, including a same-day 27-minute window). **Confined
outside the thesis population** (Q5: verified zero overlap between the 65
traders holding positions in the 103 affected markets and the 295-trader
cohort superset that the metric's 120-trader OOS cohort and matched
placebo are drawn from — so 0 positions and 0 traders of the result of
record are touched). The boundary is not incidental: Q6 shows the affected
markets are systematically thin (median 1 trade vs. 7 baseline) and
Elections-skewed, which is mechanically why cohort members (who by
definition have M≥10 qualifying positions) don't appear among them.

**What would upgrade this to PERSISTENT-TOUCHING or downgrade it to
UNRESOLVED:** if a future, larger-sample repeat of the Q1 script (or a
direct API cross-check per Q2) ever finds a pending market with a trader
who newly qualifies for the cohort (cohort membership is not static run to
run), or if the growth mechanism in Q3/Q4 is later found to include a path
that could touch higher-activity markets, this verdict should be
re-checked — it is a statement about the DB as observed 2026-08-18T18:28Z,
not a structural guarantee.

---

## Not investigated (explicitly out of scope for characterization)

No repair, backfill, or reconciliation of any kind was performed or
recommended here, per the task's read-only instruction — this document
characterizes the inconsistency; it does not propose or evaluate a fix.
