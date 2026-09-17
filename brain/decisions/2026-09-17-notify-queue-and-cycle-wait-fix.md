# 2026-09-17 — Fix the Notify Queue and the Cycle-Wait Sleep Pattern

Follows: `2026-09-17-oos-hash-methodology-and-cycle-compounding.md` (first-repo
`cd40505`), which diagnosed but did not fix these two mechanisms. The 500-row
platform-wide fetch ceiling is explicitly **not** touched — that is a
separate, later decision.

Code changes: first-repo `monitoring/monitor.py`, `monitoring/database.py`,
`monitoring/background_backfill_worker.py`. Tests: `tests/test_notify_queue_batch_drain.py`,
`tests/test_monitoring_loop_wait_shutdown.py`. No service was restarted, no
production table was written to, no fetch limit / `check_interval` / filter
was touched, and the Telegram notification path was not revived.

---

## PART 1 — WHAT `notified` ACTUALLY GATES

**Verdict: the notification path monitor.py drives is functionally dead.**
Nothing in the live system consumes the seen/unseen distinction it marks.
This clears the way for a root-cause fix, not just a narrower read-side
filter — exactly the branch the task asked to determine before touching
anything.

### Every reader of `trades.notified`, enumerated

Grepped `\bnotified\b` across both repos (`.py` files only). Results:

| File | Role | Live? |
|---|---|---|
| `monitoring/database.py` `get_unnotified_trades()` / `mark_trade_notified()` | the read/write pair | **yes** — called every cycle where `new_trades > 0` |
| `monitoring/monitor.py` `notify_new_trades()` | the only caller of the pair above | **yes** |
| `monitoring/background_backfill_worker.py` | writes `notified=0` at insert (never reads it) | **yes** (this is the feed, see below) |
| `monitoring/system_observer.py` `_check_high_value_trades()` | reads `WHERE (tr.notified = 0 OR tr.notified IS NULL)`, writes `notified=1` after alerting | **no — dead since 2026-05-20** (see below) |
| `analysis/test_calibration_analysis.py`, `analysis/test_regret_analysis.py`, `tests/test_backfill_ingest_evaluation.py`, `tests/test_data_source_write_paths.py` | `notified BOOLEAN DEFAULT 0` in fixture schema / literal copies of the backfill-worker INSERT | schema-only; no test asserts on the *value* of `notified` |
| `docs/database_reference.py` | a stale copy of `database.py`'s methods | **never imported anywhere** — not live code |

**No reader exists anywhere else in either repo** (first-repo or
trading-swarm) — no report, dashboard, agent, or query depends on
`notified` distinguishing seen from unseen.

### `system_observer.py::_check_high_value_trades()` — confirmed dead

Its only call site is commented out:
```python
# Re-enabled 2026-06-11 -- Phase 5 Gate 2 met June 5
# High value trades disabled (noise) -- legendary trades enabled (signal)
# await self._check_high_value_trades()
```
`git log -S "self.telegram = None" -- monitoring/monitor.py` traces this to
before that: the call was commented out in `65deb21` (2026-05-20, "feat:
disable individual trader trade alerts pre-Phase 5"), predating even the
2026-09-09 final Telegram cut. `grep` for `_check_high_value_trades(` finds
no other call site in either repo. **It has not executed since 2026-05-20.**

### What `notify_new_trades()` does with a trade beyond marking it

Read the function directly:
```python
async def notify_new_trades(self):
    unnotified_trades = await asyncio.to_thread(self.db.get_unnotified_trades)
    if not unnotified_trades:
        return
    trades_by_trader = {}                       # bundled in-memory
    for trade in unnotified_trades:
        trades_by_trader.setdefault(trade['trader_address'], []).append(trade)
    trader_stats_map = {}
    for trader in trades_by_trader.keys():
        stats = await asyncio.to_thread(self.db.get_trader_stats, trader)
        if stats:
            trader_stats_map[trader] = stats     # computed, then NEVER used
    # Telegram notifications disabled - Observer handles all notifications
    for trade in unnotified_trades:
        await asyncio.to_thread(self.db.mark_trade_notified, trade['trade_id'])
```
`trader_stats_map` is built (one DB read per unique trader) and then never
logged, stored, or returned — pure discarded work. No Telegram message is
sent (explicit comment). `self.elo_bot` is not called from this function at
all — the elite-trader alert block lives in `check_for_new_trades()`, gated
`if self.elo_bot:`, and `self.elo_bot = None` is hardcoded unconditionally in
`__init__` (confirmed still present today; `git log -S "self.telegram = None"`
traces it to `8c21517`/`423b3b5`, both 2026-01-27, "small monitoring
fix"/"telegram monitoring feed removed" — same day, not 2026-09-11 as one
earlier reference assumed).

**So: the 143,829 row-by-row updates observed overnight set a flag nothing
in the live system reads for any purpose.** This is stated plainly per the
task's own instruction — it changes the fix from "filter the queue" to a
root-cause fix, because there is no live behavior a structural change could
break.

---

## PART 2 — THE FIX: (ii) insert-side + (iii) batch drain. Not (i) alone.

**Chosen: (ii) + (iii), not (i).**

- **(ii) Fix at insert** — `background_backfill_worker.py`'s `INSERT OR
  IGNORE` now writes `notified=1` instead of the previous hardcoded `0`.
  Backfilled history is not new activity; notifying about it was always
  meaningless (Part 1), so it should never have entered the queue as
  "unseen" in the first place. This is the root-cause half: it stops the
  queue from being fed by anything but genuine new live-cycle trades going
  forward.
- **(iii) Batch the drain** — `notify_new_trades()`'s per-row loop
  (`for trade in unnotified_trades: await asyncio.to_thread(mark_trade_notified, ...)`,
  one connection+commit+close per row) is replaced by a single
  `Database.mark_all_unnotified_as_notified()` doing one
  `UPDATE trades SET notified = 1 WHERE notified = 0` and returning the row
  count. This is the defense-in-depth half: regardless of what future code
  might insert a `notified=0` row (a new writer, a schema migration
  default, anything not yet anticipated), draining it is now O(1), not
  O(n) at ~55–64ms/row. The compounding mechanism (bigger backlog → longer
  drain → more time for backlog to grow before the next drain) cannot
  recur even if something someday reintroduces a large `notified=0`
  population.

**Why not (i) alone, or (i) in addition:** (i) — filtering
`get_unnotified_trades()` by `data_source`/time — was rejected as
insufficient on its own, exactly per its own stated downside: "leaves the
rows accumulating forever with `notified=0`." Once (iii) makes the drain
O(1) regardless of size, that downside stops mattering — a filter narrows
*what* gets marked, but (iii) already makes *how much* irrelevant to cost.
Adding (i) on top of (ii)+(iii) would be redundant: (ii) already stops
backfill from contributing, and (iii) neutralizes the cost of anything
that does still get in. Nothing about (i) closes a gap (ii)+(iii) leaves
open.

**What each rejected/partial option would have left unaddressed:**
- (i) alone: the accumulated backlog keeps existing forever with
  `notified=0` (never marked, never cleaned up) — cosmetically wrong, and
  still O(n) to drain the one time something *does* read it (e.g., if
  `_check_high_value_trades()` were ever revived, per Part 1's note that
  reviving it is explicitly out of scope but not impossible someday).
- (ii) alone, no batch: the *rate* of new backlog growth drops to near-zero
  (confirmed: 0 `Backfilled` completions logged since this morning's
  restart, so backfill isn't contributing today regardless), but the
  drain mechanism itself would still be O(n) per row — any future source of
  volume (a resumed backfill worker, a burst of live trades) could still
  reproduce the exact compounding pattern.
- (iii) alone, no insert fix: the drain becomes fast regardless of size, but
  backfilled rows would still sit as `notified=0` until the next drain,
  semantically implying "this backfilled history hasn't been seen yet" when
  it was never new to begin with — correct performance, wrong meaning.

### What happens to the existing accumulated `notified=0` rows

**Drained once, in whichever cycle next calls `notify_new_trades()`, via the
new batched `UPDATE` — not left alone, not filtered out permanently.**
Checked the live production count at the time of this fix: **0** rows
currently sit at `notified=0` (the backlog was already fully drained by the
still-running pre-fix code, most recently confirmed 15:58:53 UTC per
yesterday's diagnosis, and `background_backfill_worker` has logged zero
completions since the restart — see Part 5). Section 5 of
`tests/test_notify_queue_batch_drain.py` proves the mechanism directly on a
seeded 305-row mixed-source backlog (300 `background_backfill` + 5
`polymarket_api`, matching the real backlog's shape): one call to
`mark_all_unnotified_as_notified()` clears all 305 rows in a single
statement, regardless of source.

---

## PART 3 — THE CYCLE-WAIT SLEEP

Replaced `monitoring_loop()`'s
`for _ in range(self.check_interval): await asyncio.sleep(1)` with a new
method, `_wait_for_next_cycle()`:

```python
async def _wait_for_next_cycle(self):
    try:
        await asyncio.wait_for(self._stop_event.wait(), timeout=self.check_interval)
    except asyncio.TimeoutError:
        pass  # normal case: check_interval elapsed with no stop request
```

**Chosen approach: `asyncio.wait_for` on an `asyncio.Event`**, not a
cancellable task. Reasoning: `wait_for` schedules exactly one timer
(`loop.call_later`, the same underlying primitive as `asyncio.sleep`) and
suspends on the event's internal waiter list — a single wakeup opportunity,
matching the watchdog's proven `asyncio.sleep(300)` pattern, while still
resolving immediately the moment `.set()` is called. A cancellable task
would need the same event (or an equivalent signal) to know *when* to
cancel, plus explicit `CancelledError` handling at the call site — strictly
more moving parts for the identical guarantee.

**Preserving prompt shutdown:** `self._stop_event = asyncio.Event()` is
created in `__init__`, `.set()` in both `request_stop()` (the in-process
Telegram-command path — dead today per Part 1's finding that Telegram is
disabled, kept for reversibility) and `stop()` (the path
`monitoring/main_telegram_safe.py`'s `finally` block actually calls),
`.clear()` in `start()`. `is_running` is untouched — still set/read exactly
as before; the event is additive, not a replacement.

Extracted the wait into its own method specifically so it's unit-testable
without constructing a full `PolymarketMonitor` (whose `__init__`
unconditionally calls `Database()` with no path override — i.e. opens the
production DB file — plus live `PolymarketClient`, `TraderAnalyzer`,
`BackgroundPnLWorker`, `BackgroundBackfillWorker`).

---

## PART 4 — VERIFICATION

### 1. Queue fix — `tests/test_notify_queue_batch_drain.py`, 18/18 PASS

- **Section 1** reproduces the OLD per-row drain using
  `Database.mark_trade_notified` (left in place, unchanged, called in a
  loop exactly as `notify_new_trades()`'s removed code did) against 500
  seeded `notified=0` rows, counting `get_connection()` calls via an
  instance-level wrapper: **500 connections for 500 rows** (T1b).
- **Section 2** proves the NEW `mark_all_unnotified_as_notified()` does the
  identical end-state work (T2d: 0 rows remain unnotified) in **1
  connection regardless of N** (T2b) — the differential the task asked
  for; a test that passed either way would have proven nothing, so the
  connection *count* (not wall-clock timing, which would be flaky) is the
  assertion.
- **Section 3** confirms `notify_new_trades()`'s source now calls
  `mark_all_unnotified_as_notified` and no longer calls the per-row
  `mark_trade_notified`, while still computing the same
  `Processing`/`Bundled into`/`trader_stats_map` output as before (T3a–c) —
  proving only queue-entry and drain changed, not what a notification does,
  per the task's explicit constraint.
- **Section 4** exercises the REAL `BackgroundBackfillWorker._process_trader_sync()`
  code path (not a reimplementation) and confirms a freshly backfilled row
  is inserted with `notified=1` and never appears in
  `get_unnotified_trades()` (T4a–d).
- **Section 5** seeds a 305-row mixed-`data_source` backlog (matching the
  real ~143k backlog's shape) and confirms one batch call drains all of
  it (T5a–c) — the "drained once" answer to Part 2's explicit question,
  demonstrated, not asserted.

### 2. Sleep fix — `tests/test_monitoring_loop_wait_shutdown.py`, 10/10 PASS

- **Section 1** confirms structurally, via source inspection with the
  docstring stripped out first (so prose describing the *old* pattern in
  backticks doesn't produce a false positive): no `range(` remains in
  `_wait_for_next_cycle()`'s executable code, exactly one
  `asyncio.wait_for(` call site, and it waits on `self._stop_event` with
  `timeout=self.check_interval` (T1a–c); `monitoring_loop()` itself no
  longer contains the old loop pattern (T1d).
- **Section 2** confirms the normal case: with no stop request, the wait
  lasts approximately the full `check_interval` (test-scale 0.2s, not
  production 900s) (T2a).
- **Section 3 — the shutdown test named explicitly in this task**: starts
  the wait with `check_interval=300` (a bare `asyncio.sleep(300)` here
  would hang the test for 5 minutes), calls `request_stop()` 0.05s in, and
  asserts the wait ends in **under 1 second**, not anywhere near 300s
  (T3a) — this is the property the old 900-round-trip loop had that a
  naive single-sleep fix would have traded away; confirmed not traded
  away here.
- **Section 4** repeats Section 3 for the async `stop()` method
  specifically — the actual path `monitoring/main_telegram_safe.py`'s
  `finally` block calls at process shutdown — with the same result (T4a–b).
- **Section 5** is a sanity check that an *unrelated* `asyncio.Event` does
  not wake the wait early (T5a) — ruling out a test that would pass
  vacuously regardless of which event fired.

### 3. Confirm nothing that reads `notified` broke

Per Part 1's reader list: the only other reader
(`system_observer.py::_check_high_value_trades()`) is dead and untouched by
this change. Section 6 of `test_notify_queue_batch_drain.py` additionally
confirms its exact query predicate (`WHERE (tr.notified = 0 OR tr.notified
IS NULL)` joined against `comprehensive_elo`/trade-size/time-window
conditions) correctly does **not** match a backfilled trade under the new
scheme (`notified=1` from insert) — consistent behavior if that dead code
were ever revived, not a regression this fix introduces (T6a).

### 4. `run_tests.py`, full suite

```
Files  : 29 run, 29 passed, 0 failed
Tests  : 339964 run, 339964 passed, 0 failed
RESULT: ALL TESTS PASSED
```
(`test_behavioral_integration.py` excluded per `run_tests.py`'s own
documented convention — cold-cache hang in subprocess automation,
unrelated to this change.) Includes the two new test files above.

**`metric_v2f_oos_result` canonical hash** (`sqlite3 -list <db> "SELECT *
FROM metric_v2f_oos_result ORDER BY kind;" | sha256sum`, the method
established in the previous diagnosis as what the project's actual
stop-condition gates use): **`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
— unchanged**, checked after all code edits and after running the full
test suite. None of this task's changes touch the production DB (all test
fixtures are temp files, verified distinct from the production path by
assertion in each test's DB-creation helper).

---

## PART 5 — WHAT THIS DOES AND DOES NOT FIX

- These two fixes address the **compounding** (growing cycle bodies, via
  the notify-queue mechanism) and the **wait** (the 900-round-trip
  cycle-wait). They do **not** address the 500-row platform-wide fetch,
  which the 2026-09-17 diagnosis measured as the actual ingestion
  ceiling — **≈0.15% of a 200-minute window's platform trade volume**
  visible to any single fetch. That is a separate, later decision, and
  was explicitly out of scope here (fetch limit, `check_interval`, and the
  flagged-trader filter were none of them touched).
- **Cadence should recover toward the configured 900s** once these fixes
  are live (no more multi-hour cycle bodies from backlog drains, and the
  wait itself no longer loses time to 900 separate starvation-exposed
  wakeups) — **but ingestion volume will remain low** until the fetch
  ceiling itself is addressed. Fixing the symptom that was making a bad
  situation worse is not the same as fixing the underlying ingestion gap.
- **The fixes are inert until the monitor process restarts.** Confirmed:
  `polymarket-monitoring.service` is still `MainPID=55865`, active since
  `2026-09-17 06:14:08 UTC` — the same process from this morning's
  unattended-upgrade-triggered restart, running the pre-fix code in memory.
  No restart was performed as part of this task, per scope. Last night's
  restart (of the *previous* process, PID 52386 → 55865) was clean — a
  normal `Stopping...Deactivated successfully...Stopped` sequence, no
  `SIGKILL` fallback — unlike the observer's forced kill in the same
  event window. Nothing in this task's changes affects that behavior
  either way, since the OS-level `SIGTERM` that produced the clean stop
  does not currently pass through any of the code touched here (no
  in-process signal handler intercepts it; the process dies before
  `is_running`/`_stop_event` would ever matter for that specific path;
  `_stop_event` only matters for the in-process `request_stop()`/`stop()`
  callers).
- **`background_backfill_worker`'s zero completions in ~10h remains an
  open, unexplained anomaly**, first flagged in the 2026-09-17 diagnosis,
  and is explicitly not addressed or further investigated here per scope.

## Scope adherence

No service restarted. No production table written to (all fixtures are
temp files; the production DB was only read, to confirm the current
`notified=0` count and the canonical `metric_v2f_oos_result` hash before
and after). Fetch limit, `check_interval`, and `check_for_new_trades()`'s
filters were not touched. The Telegram notification path was not revived —
`request_stop()`'s docstring/behavior is unchanged beyond the added
`_stop_event.set()`, and no code was added that would cause `self.telegram`
or `self.elo_bot` to become non-`None`. `background_backfill_worker`'s
zero-completion anomaly was not investigated.
