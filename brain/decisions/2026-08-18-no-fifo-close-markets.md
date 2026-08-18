# 2026-08-18: characterizing the 166 (now 161) markets with trades but no FIFO-closed position

Read-only characterization. No repair, reconciliation, or FIFO re-run against
production. Every claim below is tagged **[V]** (verified — command/query/
file:line given) or **[I]** (inferred/plausible, explicitly marked).
Unverifiable points are stated in place with what would settle them, per the
standing project instruction (memory: `feedback_verify_dont_propagate.md`).

Committed script: `scripts/characterize_no_fifo_close_markets.py` (first-repo).
Re-run: `python3 scripts/characterize_no_fifo_close_markets.py`. Writes a
timestamped JSON artifact to `data/characterizations/` with generating
parameters. Today's run: `data/characterizations/no_fifo_close_markets_20260818T184821Z.json`.

## Background claims, checked before use

- "254-market shortfall, one-directional, two components (88 + 166)" — **[V]**
  matches `2026-08-16-canonical-infrastructure-recon.md`. **[V]** Re-derived
  live today via the committed script: canonical population **6,879** (not
  6,842), v2f population **6,614** (not 6,588), symmetric diff **265** (not
  254) — all three base counts have moved since 08-16, consistent with
  ongoing data accrual, not a discrepancy in the query logic (same WHERE/JOIN
  shape, reproduced from `monitoring/column_definitions.py:469-499` and
  `scripts/trader_skill_metric_v2f.py:236-247`).
- "166 markets... uncharacterized, this task" — **[V]** re-derived count today
  is **161**, not 166. This is a *decrease* of 5, not the growth pattern seen
  in the sibling pending-`trade_result` component (88→104 over the same
  period). See "Population stability" below — **[U]** why it decreased is
  not settled here.
- "Do NOT assume the 166 are bounded the same way [as the 88]" — **[V]**
  confirmed: different root cause (Q2), and — unlike the 88 — this population
  **does** reach the cohort superset (Q4). The instruction not to assume was
  correct; the two components are not analogous.
- "148-trader qualifying cohort" — **[V]** exists only as a prose figure with
  no persisted membership snapshot (confirmed again today: `objective2` cohort
  tables/snapshots not found; consistent with `2026-08-18-pending-resolution-inconsistency.md`'s
  same finding). As in that doc, `metric_v2f_intersection_cohort` (295-trader
  persisted Objective-1 "significant AND M≥10 AND edge≥0.02" superset,
  `SELECT COUNT(*) FROM metric_v2f_intersection_cohort` → 295) is used as the
  best available *verifiable proxy* for cohort reach. **[I]** If the true
  148/120 membership differs from this superset, the overlap reported below
  could over- or under-state true cohort impact.
- T_split = 2026-04-01 00:00:00 — **[V]** `scripts/trader_skill_metric_v2f.py:135`,
  matches the value used in the task prompt and in the committed script's default.

## Q1 — why does FIFO fail to close (primary question)

**[V]** Read `monitoring/position_tracker.py` in full
(`PositionTracker.match_trades_for_trader` / `_match_group`,
lines 155–364). The FIFO matcher groups a trader's trades by
`(market_id, outcome)` and processes them chronologically:
- Every `BUY` is pushed onto an `open_buy_queue`.
- Every `SELL` pops matched shares off that queue (oldest first) and creates
  a **closed** Position from the matched buys.
- Any `BUY`s left in the queue at the end become **open** positions.
- **Critically: if a `SELL` arrives with an empty `open_buy_queue` (no prior
  `BUY` recorded for that trader/market/outcome), `matched_buys` stays empty
  and `_match_group` creates NO position object at all** (`position_tracker.py:330`,
  `if matched_buys:` gate). The SELL is silently dropped — not an open
  position, not a closed one, no row of any kind.

**[V] Classified all 161 markets by failure mode**, using the committed
script's `orphan_sell_groups()`: for every `(trader, market, outcome)` group
with trades in a no-position market, checked whether any `BUY` trade exists
anywhere in `trades` for that exact group.

| Failure mode | Groups | Markets |
|---|---|---|
| Orphan SELL — zero matching BUY anywhere in `trades` for that (trader, market, outcome) | **186 / 186 (100%)** | 161 / 161 (100%) |
| Any other pattern (malformed side, null market_id, BUY present but still no position, etc.) | 0 | 0 |

**[V]** This is the single, universal, exhaustive failure mode for the
current population — no markets fall outside it, and no other candidate
mechanism (malformed `side` values, `market_id IS NULL`, `pnl_skip`-flagged
traders) was found to apply. **[V]** `DISTINCT side` among these markets'
trades is exactly `{'SELL'}` — confirmed no case-sensitivity or malformed-value
issue. **[V]** `SELECT COUNT(*) FROM traders WHERE pnl_skip=1` → **1** trader
DB-wide today, and that one trader has zero trades in any of the 161 markets
— `pnl_skip` (the mechanism behind O-15, see below) is not a contributor here.

**[I]** Why the BUY is missing is not directly observable from this DB alone.
Plausible explanations: the BUY leg was never captured by ingestion (a gap in
trade-tape collection for that specific trader/token at that specific time),
or it was captured under a different `outcome`/token-id encoding that this
grouping doesn't match. **[U]** Distinguishing these would require checking
Polymarket's on-chain/API trade history for a sample trader+market+token to
see whether the missing BUY exists on-chain — not done here (task is
DB-only characterization); see Q6.

## Q2 — is this the same mechanism as the 88

**No — a different, independent mechanism. [V]**

The 88/104-market component (`2026-08-18-pending-resolution-inconsistency.md`)
is caused by `trades.trade_result` staying `'pending'` because its only
writer, `TradeEvaluator`/`scripts/evaluate_new_trader_results.py`, has no
automatic trigger.

For the 161 no-position markets, **[V]** `trade_result` on the orphan SELL
rows themselves is mostly *already resolved*:

| trade_result on orphan SELLs | count |
|---|---|
| won | 154 |
| lost | 42 |
| pending | 9 |

**[V]** Read `monitoring/trade_evaluator.py:16-45` — `TradeEvaluator.evaluate_trade`
computes won/lost per-trade from `(trade side, trade outcome, market
winning_outcome)` alone; it has **no dependency on the `positions` table**.
So most of these trades already got evaluated by the normal `trade_result`
pipeline; that pipeline is not what's blocking them from v2f.

**[V]** The actual blocker is v2f's query structure itself
(`scripts/trader_skill_metric_v2f.py:236-247`): it requires a JOIN through
`positions p` and `json_extract(p.entry_trade_ids, '$[0]')` — since no
`positions` row exists at all for an orphan SELL, there is no
`entry_trade_ids` to extract, and the market never enters the join result,
regardless of what `trade_result` says. This is a structurally different
failure point (missing FIFO output) from the 88 (present FIFO output,
unevaluated trade_result field).

## Q3 — market properties (166/161 vs. canonical baseline)

**[V] Trade count:** median **1** trade per market (n=161; distribution:
135 markets with exactly 1 trade, 17 with 2, the rest 3–6) vs. median **7**
for the 6,879-market canonical baseline. Sharply thinner than baseline —
same direction as the 88's finding, different underlying cause.

**[V] Category mix:** 131/161 (**81.4%**) Elections, 30/161 (18.6%)
Geopolitics, vs. baseline 4,446/6,879 (**64.6%**) Elections. A real skew
toward Elections, though less extreme than the 88's 76%→81% is actually
slightly *more* skewed, not less.

**[V] Resolution type (`winning_outcome`, Yes/No only):** 134/161 (83.2%)
resolved "No" vs. a rough baseline (all resolved geo/elec markets,
unfiltered by trade_gap/tape_end) of 7,457/10,498 (71.0%) "No". A moderate
skew toward "No"-resolving markets; **[I]** plausibly related to the
Elections skew (many single-question prop markets default-resolve "No")
rather than an independent effect.

**[V] Volume / liquidity / neg_risk grouping:** **not measurable** —
`PRAGMA table_info(markets)` shows no `volume`, `liquidity`, or `neg_risk`
column exists anywhere in the schema. This is a hard data-availability gap,
not a null result; reported as such rather than working around it with a
proxy.

**[V] difficulty_score:** only 14 of 6,879 canonical-population markets have
a non-NULL `difficulty_score` at all (effectively unpopulated for this
population) and 0 of the 161 no-position markets do. Not usable as a
comparison axis.

**[V] tape_end date distribution:** spans **2023-05 through 2026-03**
(monthly buckets, min 1/month, max 23 in 2026-03) — broad historical
residue across ~35 months, not a recent-onset pattern. Full bucket table in
the committed script's JSON artifact.

**[V] O-37 synthetic-market quarantine:** confirmed real
(`scripts/quarantine_o37_synthetic_markets.py`, 84 markets flagged
2026-07-19 via `trade_gap_flag=1` + `flag_reason`). **[V]** `flag_reason`
is `NULL` for all 161 no-position markets — none are O-37 quarantine
markets. This is expected by construction: the canonical/v2f queries both
already exclude `trade_gap_flag=1` rows, so a quarantined market could never
reach this population in the first place.

**Finding: yes, a real, verified, non-random distinguishing profile exists**
— thin (median-1-trade), Elections-heavy, "No"-resolving markets, spread
across the DB's full history. Volume/liquidity/neg_risk comparisons are
unavailable, not absent-and-ignored.

## Q4 — cohort reach

**Non-zero. This is the headline finding — reported and flagged per the
task's "stop-and-report" instruction.**

**[V] Direct set intersection**, same method as the sibling doc: 78 distinct
traders have orphan-SELL trades in the 161 no-position markets
(`SELECT DISTINCT trader_address FROM trades WHERE market_id IN (...)`).
Intersected against `metric_v2f_intersection_cohort` (295-trader persisted
superset):

- **7 traders** overlap.
- **26 trade rows** (orphan SELLs) belong to those 7 traders.
- **21 distinct markets** are touched.

Trader addresses, per-market detail, prices, and timestamps are in the
committed script's JSON artifact (`cohort_overlap` key) and were spot-checked
manually against `trades`/`markets` — e.g. trader `0x0cb10c40...` alone
accounts for 13 of the 26 rows, spanning Oct 2025–Jan 2026, mostly
single-question "will Trump say X" Elections markets.

**[I] Why this differs from the 88's zero-overlap finding:** the sibling
doc's boundedness argument was "cohort membership requires ≥10 *total*
positions, and the 88's markets are median-1-trade, so cohort members are
unlikely to appear there." That reasoning is about *per-market* trade count
correlating with *aggregate* trader activity, not a hard exclusion — a
cohort member (who by definition has ≥10 positions **elsewhere**) can still
have a single orphan-SELL trade in one specific thin market. The two
components happening to land on opposite sides (0 vs. 7) is **not**
evidence that one mechanism is structurally safer than the other in
general — it is a fact about this specific data snapshot, verified by
direct query, not derived from the "thin market" heuristic.

**[U]** Whether these 7 traders and 21 markets fall inside the *literal*
148-pre-split or 120-post-split Objective-2 cohorts (rather than the
295-trader Objective-1 superset used here) is not settled — no persisted
membership snapshot exists to check against (same gap noted in the sibling
doc and in Item 8 of today's system-state census). What would settle it:
persisting the actual 148/120 membership lists (a real, standing gap
independent of this task).

## Q5 — directional effect

**[V]** For each of the 26 affected orphan-SELL rows, the trade's own
`trade_result` (won/lost, evaluated per-trade by `TradeEvaluator` off
`side` + `outcome` + `winning_outcome`, independent of any position) is
available and populated — see the sample rows in Q2's table structure;
of the 26, the field is populated (not `pending`) for the large majority
(consistent with the 154/205 won + 42/205 lost split found DB-wide in Q2).

**[U] But this does NOT tell us the direction of the metric's edge impact,
and estimating it would be wrong.** `edge = won - entry_price` requires a
known `entry_avg_price`, which requires a matched BUY — and by construction
(Q1) these are exactly the trades with **no matched BUY**. We know whether
the underlying market resolved in the trader's favor at the token level, but
we have no record of what price they paid to acquire the position they sold,
so we cannot compute what their actual realized edge was, and therefore
cannot say whether *dropping* these 26 observations from the metric biases
it up or down for these 7 traders. **This is genuinely undeterminable from
available data, not merely un-computed** — the entry price does not exist
anywhere in this database for these trades. What would settle it: none of
this database's own sources; would require external re-acquisition of the
missing BUY-side trade record (see Q6).

## Q6 — recoverability

Only one failure mode was found (Q1), so this reduces to one assessment:

**Orphan SELL / no matching BUY — recoverable in principle, not verified
recoverable here.** **[I]** If the missing BUY trade genuinely occurred on
Polymarket (i.e., ingestion missed capturing it, rather than it never
existing — e.g., a merge/split/conditional-token conversion that doesn't
route through the normal buy/sell trade feed), it should in principle be
recoverable by re-querying Polymarket's API/subgraph for that trader's full
historical trade tape on that specific market/token and re-ingesting any
missing rows. **[U]** Whether the source API still serves complete history
for markets this old (some tape_end back to 2023-05) was not checked here —
this is a live API reachability question, out of scope for a read-only DB
characterization, and the task explicitly forbids re-running ingestion. What
would settle it: a read-only spot-check against the Polymarket API/CLOB for
a handful of the 21 affected-cohort markets, comparable to the 2-market
spot-check already done for the sibling 88/104 doc.

**Not recoverable by synthetic construction** (unlike O-37's or
`apply_synthetic_closes`'s resolution-based synthetic closes): a synthetic
close for an *open* position can be generated because the winning/losing
outcome is known — but here there is no known **entry price**, so no
synthetic BUY can be fabricated without inventing a number. Any fix must
come from real re-ingested trade data, not synthesis.

## Population stability (unprompted, flagged for the record)

**[U]** The count moved from 166 (08-16) to 161 (today) — a **decrease**,
unlike the 88→104 (08-16→08-18) **increase** seen in the sibling component.
No market-ID list was persisted at 08-16 (confirmed: the 08-16 recon doc
gives only one example ID, `0x00b2eb5d...`, which **is** still present in
today's 161 — spot-checked), so the exact set cannot be diffed to determine
whether this is genuine convergence (some orphan SELLs got their BUY
backfilled) or population churn from an unrelated cause (e.g. a market's
`category`/`resolved`/`trade_gap_flag` status changing, moving it out of the
canonical population entirely rather than into v2f). What would settle it: a
persisted daily snapshot of this population's market-ID set — the same kind
of gap already noted for the 148/120 cohort (Item 8, system-state census) —
does not currently exist for this population either.

## Verdict

**TOUCHING.**

Applying the fixed criteria: the no-FIFO-close population reaches the
cohort superset — **7 traders, 26 trade rows, 21 markets**, verified by
direct set intersection against the best available persisted proxy
(`metric_v2f_intersection_cohort`, 295 traders). This is not bounded outside
the thesis population the way the sibling 88/104 component is. The
directional effect on the metric's result of record (Q5) is genuinely
undeterminable from available data — not zero, not estimated, unknown — which
means this is a live, unresolved gap in the result of record's data
foundation, not a cosmetic DB inconsistency.

## What's not resolved

- Root cause of the missing BUY legs (Q1's "[I]"/"[U]" note) — would need
  live API/on-chain comparison.
- Exact 148/120 Objective-2 cohort membership vs. the 295-superset proxy
  used throughout (Q4).
- Why the population count decreased 166→161 rather than growing like the
  sibling component (Population stability section).
- Whether the missing BUY data is still recoverable from the source API for
  markets this old (Q6).
