# 2026-09-09 — Fix: `background_backfill_worker.py` evaluates at ingest instead of hard-coding `trade_result='pending'`

Step 1 of 3. Baseline capture and the drain are **separate later tasks** — not
touched here. This changes **future inserts only**; no existing row is modified.

Tags: **[V]** verified this session (file:line / command / test), **[I]** inferred.

Code: first-repo `7ae0f2a` — `monitoring/background_backfill_worker.py`,
`tests/test_backfill_ingest_evaluation.py` (new), `tests/test_data_source_write_paths.py`
(inline-SQL copies re-synced to the new INSERT shape).

---

## Part 1 — assessment (before changing)

### Where `'pending'` is written, and the context available

**[V]** `monitoring/background_backfill_worker.py`, `_process_trader_sync()`
(pre-fix lines 305–324). The worker fetches one trader's full history
(`_fetch_all_trades`, capped at 2000 trades) and loops:

```
INSERT OR IGNORE INTO trades ( ... trade_result, data_source )
  VALUES ( ?,?,?,?,?,?,?,?,?,?,?, 0,0,NULL, 'pending','background_backfill' )
```

— `trade_result` is the string literal `'pending'`, always. Immediately after,
a stub `markets` row is upserted `INSERT OR IGNORE ... (market_id, title,
'Unknown', 0, 'background_backfill')` (`resolved=0`).

Context available at the insert point, per row: `trade_id`, `trader_address`,
`condition_id` (= `trade["conditionId"]`, and the value stored as
`trades.market_id`), `title`, `outcome`, `side`, `shares`, `price`, `timestamp`.
**Not** available without a lookup: the market's `resolved` / `winning_outcome` /
`category`.

`condition_id` equals `trades.market_id` and `markets.market_id` (the PK) for
this worker's rows, so the market lookup key is a primary-key lookup.

### Which evaluator

**[V]** `monitoring.trade_evaluator.TradeEvaluator.evaluate_trade(self, trade:
Dict, winning_outcome: str)` (`monitoring/trade_evaluator.py:16`). Read in full:
it reads only `trade.get('outcome_bet') or trade.get('outcome','')`,
`trade.get('side')`, and the `winning_outcome` argument. **No `self.db`, no
`self.client`, no network, no file I/O — pure.** `TradeEvaluator(None, None)` is
safe; the constructor only stores the two unused args. This is the same
evaluator `scripts/backfill_trade_results_geo.py` and
`scripts/evaluate_new_trader_results.py` call, and the one the 2026-08-19 repoint
(`8cfeb8e`) converged on (1,582,064-row zero-disagreement). Calling it in the
loop adds a dict build + a pure function call — **zero I/O beyond the one batch
market lookup.**

### Cost of the market lookup — batch-cached, not per-row

**[V]** Proposed and implemented: one `SELECT market_id, resolved,
winning_outcome FROM markets WHERE market_id IN (...)` per trader, on a
**separate short-lived connection opened and closed before** the write
connection — so the write transaction's shape is byte-for-byte unchanged (first
statement still the INSERT, still one `commit()` per trader). Under WAL a plain
SELECT takes **no write lock** and cannot block the live monitor.

**[V] Batch sizes in practice** (16,321 `background_backfill` traders in
production): median **203 trades / 97 distinct markets** per trader; mean 345 /
169; max at the 2000 cap. So the added lookup is normally **one** SELECT with
~100 bound params (chunk size 900 → one chunk), at most 3 SELECTs for a
2000-market trader. `markets.market_id` is the PK → indexed. Sub-millisecond to
low-ms, against a per-trader budget of 45 s that is already dominated by the
15 s-per-page API fetch. Negligible.

### Fall-through cases — still write `'pending'`

**[V]** The helper `_resolve_ingest_trade_result(trade, market_row)` returns
`'pending'` (unchanged behaviour) when:
- the market is **absent** from `markets` (`market_row is None`) — e.g. a
  geo/elec market no existing trader has touched; the worker then stubs it
  `resolved=0`;
- the market row has **`resolved != 1`**;
- `winning_outcome` is **NULL / '' / 'unknown'** (gate mirrors
  `backfill_trade_results_geo.py`'s `NOT IN ('unknown','')`; `.lower()` here is a
  safe superset — a cased `'Unknown'` also falls through);
- `evaluate_trade` returns **`'invalid'`** (unusable `outcome`/`side` data) — the
  row is left `'pending'` rather than locking in an `'invalid'` verdict at
  ingest.

Only a `'won'` / `'lost'` verdict is written non-pending. **The daily evaluator
(`scripts/backfill_trade_results_geo.py`) is still needed** — this reduces the
inflow, it does not eliminate it.

### STOP conditions — none hit

- *Market lookup needs per-row I/O or a longer write-lock hold?* **No** — one
  batch SELECT on a separate connection closed before the write connection; write
  txn shape unchanged.
- *Fix needs local re-implementation of evaluation?* **No** — the canonical
  `TradeEvaluator.evaluate_trade` is called verbatim. The helper only does the
  resolved/usable **gate** (the same gate `backfill_trade_results_geo.py`'s SQL
  `WHERE` already expresses), not evaluation.

---

## Part 2 — what changed

`monitoring/background_backfill_worker.py`:

1. `from .trade_evaluator import TradeEvaluator`; module-level
   `_INGEST_EVALUATOR = TradeEvaluator(None, None)`.
2. New module-level pure function `_resolve_ingest_trade_result(trade,
   market_row) -> str` — the resolved/usable gate + the canonical evaluator call;
   returns `'won'`/`'lost'`/`'pending'`.
3. New method `_fetch_market_resolutions(condition_ids) -> {market_id:
   (resolved, winning_outcome)}` — one chunked (900) batch SELECT on its own
   short-lived connection.
4. In `_process_trader_sync`: after `_fetch_all_trades`, before the write
   connection opens, build `market_res = self._fetch_market_resolutions({...})`
   from the batch's `conditionId`s.
5. In the insert loop: `trade_result = _resolve_ingest_trade_result(trade,
   market_res.get(condition_id))`; the INSERT's `VALUES` literal `'pending'`
   becomes a bound `?` fed that value. Column list, `INSERT OR IGNORE`, and the
   trailing `'background_backfill'` literal are unchanged.

**Not changed:** `batch_size` (1 trader/cycle), the single `conn.commit()` per
trader, the transaction shape, `_build_batch`'s discovery query, `_fetch_all_trades`,
the `markets` stub upsert, the `market_category='Unknown'` hard-code (a separate
O-2/O-30 issue; `category` is not needed for evaluation). No existing row is read
for modification — `INSERT OR IGNORE` cannot alter a stored row on `trade_id` /
`transaction_hash` collision.

`tests/test_data_source_write_paths.py`: the two inline copies of the worker's
INSERT SQL (T14, T15 — both assert on `data_source`, not `trade_result`) re-synced
to the new `?`-for-`trade_result` shape so their "exact SQL from the worker"
claim stays true. No assertion changed; suite still 30/30.

---

## Part 3 — verification (all via `run_tests.py`)

New file `tests/test_backfill_ingest_evaluation.py` — **29 checks, 29 pass**.
Exercises the **actual worker code** (`BackgroundBackfillWorker._process_trader_sync`
with a monkey-patched `_fetch_all_trades`) against a throwaway temp DB; a guard
assertion rejects the production path at temp-DB creation.

### 1. Correctness — new path == `TradeEvaluator.evaluate_trade()`

**[V]** Six `(outcome, side, winning_outcome) → expected` cases (BUY match/miss,
SELL match/miss, multi-outcome): for each, `evaluate_trade` directly == expected,
**and** `_resolve_ingest_trade_result` == `evaluate_trade`. Plus the full worker
path: seed a resolved market (`winning_outcome='No'`), ingest a `bet Yes / BUY`
trade → stored row is **`'lost'`**, `data_source` still `'background_backfill'`.

### 2. Non-tautology — still writes `'pending'`

**[V]** Helper falls through to `'pending'` for: market `None`, `resolved=0`,
`winning_outcome` NULL / `''` / `'unknown'`, and an `'invalid'` verdict (empty
bet). Full worker path: unresolved seeded market → `'pending'`; **absent** market
(never seeded; worker stubs it `resolved=0`) → `'pending'`; resolved market with
`winning_outcome='unknown'` → `'pending'`. Mixed batch (one resolved + one
unresolved leg, same run): resolved leg → `'won'`, unresolved leg → `'pending'`.

### 3. No existing row changed

**[V]** Seed a market that resolves the trade to `'lost'`, and a **pre-existing**
`trades` row for the same computed `trade_id` stored as `'won'` /
`data_source='polymarket_api'`. Run the worker over an API trade with that
`trade_id`. After: `trade_result` still `'won'`, `data_source` still
`'polymarket_api'`, full row dict identical before/after. Sanity: a genuinely-new
trade in the same run/market **is** evaluated (`'lost'`).

### Full suite

**[V]** `python3 run_tests.py --skip=test_behavioral_integration.py` →
**23 files run, 23 passed, 0 failed. RESULT: ALL TESTS PASSED.** Includes
`test_data_source_write_paths.py` 30/30 and `test_o15_naive_aware_datetime.py`
9/9 (both also exercise `_process_trader_sync`).

### Pending geo/elections count — unchanged by this commit

**[V]** `check_pending_geo` predicate → **24,390** rows, both before and after
(the change is code-only; no data migration, no existing row touched; the diff is
`.py` files). Reporting the number, not asserting an exact match — a few rows of
live drift are expected on any given read.

---

## Part 4 — expected effect going forward

### Fraction of future backfilled trades evaluated at ingest

**[V]** Of all 5.63 M `background_backfill` trades ever inserted, **50.6%
(2,851,405)** are on markets that are *now* `resolved=1` with a usable
`winning_outcome`; 49.4% on not-yet-resolved markets; **0** on absent markets,
**0** with an unusable outcome.

**[V]** Of the current 24,390-row geo/elec pending backlog, the parent market's
`data_source` is `live_monitoring` for 20,285 (83%), `historical_backfill` /
`gamma_backfill_*` for ~3,885, and **only 220 (0.9%)** are worker-stubbed
(`data_source='background_backfill'`). So **~99% of pending rows are in markets
that already existed in `markets`** (populated by the live monitor / market
backfills that run independently of this worker) — i.e. at ingest the resolution
lookup would have **found the row**.

**[I] Estimate:** for newly-discovered traders (whose histories are
overwhelmingly *old* trades on *long-resolved* geo/elec markets), the large
majority of their backfilled geo/elec trades will now be evaluated at ingest.
The exact fraction depends on category mix and how stale each discovered
trader's history is; it cannot be pinned without post-deployment observation.

### What still lands `'pending'`

1. **Market not yet in `markets` at ingest** — a geo/elec market no existing
   trader has touched. Small (≈0.9% proxy above). The worker stubs it
   `resolved=0`; a later market-hydration / resolution job fills `resolved=1`;
   the daily evaluator then catches the trade. **Transient.**
2. **Market present but `resolved=0` at ingest** (resolution lag — the trade
   was ingested in the window between the market's real resolution and our DB
   recording it, or the trade is on a genuinely still-open market). Caught later
   when `resolved` flips + an evaluator runs. **Transient** (open-market case is
   correct/permanent until it resolves).
3. **`winning_outcome` NULL/unknown** — 0 for geo/elec today; a real
   possibility for disputed markets. **Transient** (usually).
4. **The live-monitor ingest path (`data_source='polymarket_api'`) is
   unchanged by this fix** — ~40% of the current backlog. Those trades are
   normally on not-yet-resolved markets (you trade before resolution), so
   starting `'pending'` there is expected flow, not a leak; they clear when the
   market resolves and an evaluator runs.

### Static, shrinking, or still growing?

**[I] Still growing, but materially slower, and the residual growth is now
dominated by *transient* rows (cleared once their market resolves + an evaluator
runs) rather than *permanent* ones.**

The pathological inflow this fixes: `background_backfill` ingesting **old trades
on already-resolved geo/elec markets** and stamping them `'pending'` forever
(no non-flagged evaluator runs — `backfill_trade_results_geo.py` is unwired).
That contribution — the geo-drain audit's Part 4 Candidate A finding (72% of
pre-split pending rows are `background_backfill` provenance) — **stops** at the
source. What remains is resolution-lag and market-absent rows, which are
self-clearing once the market's `resolved` flag lands and any evaluator touches
them, plus the untouched live-monitor path.

**The existing 24,390-row backlog is not affected by this commit** (that is the
drain's job). But for that drain, the target is now a **finite set that is no
longer being fed by the dominant channel** — not a fast-moving target.

---

## What was NOT determined

- **The exact post-fix inflow rate** to the geo/elec pending backlog. The 50.6%
  "resolved at now" figure is a whole-history snapshot, not the ingest-moment
  fraction for *future* discoveries; only observation over the weeks after
  deployment will pin the new rate.
- **How often a geo/elec market is absent from `markets` at the moment the
  worker ingests a trade on it.** Proxied at ≈0.9% by worker-stub provenance
  among the current backlog (a lower bound: a stub later hydrated keeps
  `data_source='background_backfill'` by first-writer-wins, but a market first
  created by another path after the worker wanted it would not be counted).
- **Resolution-lag window size** — how long between a market's true resolution
  and our DB setting `resolved=1` (related to the O-36 LATE-biased detection
  bug). Rows ingested in that window still land `'pending'`; the window's
  duration was not measured here.
- **Interaction with the live-monitor ingest path.** This fix is scoped to the
  backfill worker only; whether `monitoring/monitor.py` / `database.add_trade`
  should get the same treatment is a separate question, not assessed.
- **Behaviour under a genuinely cased `'Unknown'` winning_outcome.** None exist
  in production today (verified); the helper's `.lower()` gate handles it safely
  (→ `'pending'`) but that path is untested against real data because there is
  none.

---

*Generated 2026-09-09. Sources: `monitoring/background_backfill_worker.py`
(full read), `monitoring/trade_evaluator.py:16-53`, `monitoring/database.py`
(`get_connection`), `tests/test_data_source_write_paths.py`,
`tests/test_backfill_ingest_evaluation.py` (new, 29/29),
`python3 run_tests.py --skip=test_behavioral_integration.py` (23/23),
live read-only queries against `data/polymarket_tracker.db` (20 GB),
`2026-09-09-geo-drain-blast-radius.md` (ebdf1f1),
`2026-09-09-geo-backfill-wiring-decision.md` (28d898b). No drain, no wiring,
no existing row modified.*
