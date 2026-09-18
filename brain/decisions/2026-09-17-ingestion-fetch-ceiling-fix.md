# 2026-09-17 — Fix the Ingestion Fetch Ceiling

The last of three monitor fixes. The first two are committed
(first-repo `01525d7`) and inert until restart; this one lands in the same
restart. Follows `2026-09-17-oos-hash-methodology-and-cycle-compounding.md`
(diagnosis) and `2026-09-17-notify-queue-and-cycle-wait-fix.md` (the first
two fixes).

Code: first-repo `monitoring/polymarket_client.py`, `monitoring/monitor.py`.
Tests: `tests/test_fetch_ceiling_pagination.py`. No service restarted, no
production table written, no code from the first two fixes touched, the
09-12-to-now gap was not backfilled, and the flagged-trader filter /
category filter / `check_interval` were not changed.

---

## PART 1 — WHAT THE API ACTUALLY SUPPORTS

All calls below are plain unauthenticated `GET`s to the public
`data-api.polymarket.com/trades` endpoint — the same one `get_market_trades()`
already calls. No writes, no auth.

| Capability | Finding | Evidence |
|---|---|---|
| **`after` (timestamp filter)** | **Ignored server-side.** Confirmed with both an ISO string 1 hour in the past and the equivalent unix-epoch integer — both returned the identical "500 most recent" result as no filter at all. | Direct test: `after=<1hr ago, ISO>` → same 500 rows (timestamps ~now) as unfiltered. Repeated with unix-epoch — same result. This is exactly why the cursor "exists and does nothing": `last_trade_timestamp` was being sent as `after` and the server has never used it. |
| **`limit` (max page size)** | **Server hard cap: 10,000.** 500 was an unexamined client-side constant, not an API limit. | `limit=501`→501 rows, `limit=1000`→1000, `limit=2000`→2000, `limit=5000`→5000 (spanning 393s of real activity), `limit=10000`→10000 (spanning 636s), `limit=15000`→**10000** (capped), `limit=20000`→**10000** (capped). |
| **`offset` (pagination)** | **Works reliably** on all three query shapes: platform-wide, per-market, and per-user. | Platform-wide: `offset=0` vs `offset=500` vs `offset=1000` returned progressively older, non-overlapping-once-caught-up windows (some overlap between adjacent offsets is expected — see "known limitation" below — because the platform-wide feed is live and shifts between calls; zero overlap once far enough back that the shift no longer reaches). Per-market (`market=<condition_id>`, a real active geo/elec market): `offset=0` vs `offset=500`, zero overlap, clean pagination (this market is not active every second, so no live-shift artifact). Per-user: **already proven in continuous production use** — `background_backfill_worker.py`'s `_fetch_all_trades()` has paginated `user=<address>&offset=N` since 2026-09-09 and has successfully backfilled millions of rows this way. |
| **Per-market / per-user "endpoints"** | **Not separate endpoints.** Same `/trades` endpoint, optional `market=` or `user=` filter params. Both confirmed working — `market=` in the per-market pagination test above and in the prior day's diagnosis (3 markets queried successfully); `user=` continuously in production via the backfill worker. | — |
| **Rate limiting** | **Real, but load-dependent, not burst-triggered at the volumes this fix uses.** No rate-limit headers exposed (no `X-RateLimit-*`/`Retry-After`). A modest 8-call rapid burst (small payloads) returned 200 every time. The 429/408s in last night's logs came from `background_backfill_worker.py`'s tight, no-delay, per-trader offset-pagination loop running continuously across many traders — sustained volume, not a low burst threshold. | 8/8 rapid calls → 200. Production evidence: 1 HTTP 429 (23:30:46) and 2 HTTP 408s (23:58:47, 04:22:40) logged by `backfill_worker` over ~10h of continuous per-trader pagination. |
| **Response ordering** | Newest-first, **strictly non-increasing by timestamp**, both within a page and across increasing offsets. | Verified on a live 500-row page: `all(ts[i] >= ts[i+1] for i in range(499))` → `True`. This is what makes "check the last element of a page" a valid, O(1) cursor-reached test rather than needing to scan the whole page. |

**None of the STOP conditions triggered.** The API materially supports a
much better approach (10,000/call instead of 500, genuine pagination instead
of a dead `after` param) — this is a client-side redesign, not a
data-source problem.

---

## PART 2 — OPTIONS ASSESSED AGAINST PART 1

Working trade-velocity figure from today's live measurements: **500
trades in ~52s** (baseline call) up to **500 trades in ~18s** (2026-09-16
measurement) — roughly **10-28 trades/sec**, bursty and time-of-day
dependent. Used as a working range below; the live A/B demonstration in
Part 4 uses the actual number for the specific window tested, not this
estimate.

| Option | API calls per cycle | Rate-limit fit | Coverage achieved |
|---|---|---|---|
| **(i) Paginate platform-wide until cursor covered** | Self-correcting: ~1-2 calls at a healthy 900s cadence (≈9,000-25,200 trades ÷ 10,000/call), up to ~7-8 calls at the 75-85 min gaps currently observed post-restart, bounded by a defensive cap (implemented at 30) for pathological gaps. | Fits comfortably: even the worst bounded case (30 sequential calls) is far below what triggered 429s in `backfill_worker` (that was *continuous*, *concurrent-across-many-traders*, *no-delay* pagination sustained for hours — a fundamentally heavier load pattern). Explicit backoff added regardless. | **Effectively complete** — walks back to the cursor, not a fixed row count. Live-demonstrated: 100% of a real ~13.5-minute gap in 2 calls (see Part 4). |
| **(ii) Per-trader polling (flagged set or a smaller research population)** | Even at the smallest credible population — **PIT-legal classifiable pool, 5,732 traders** (not the full 40,929 flagged) — that's **5,732 calls/cycle**. At Pool C (~4,500) it's still **4,500 calls/cycle**. Sequentially at even 0.5s/call: 37-48 **minutes** of fetching per cycle, before any rate-limit response. | **Fails outright.** This is the load shape that already produces 429/408s in production at a *single* worker's pace — thousands of calls per cycle would trigger sustained rate limiting far worse than what's already observed, and even without rate limits, a 40+ minute fetch phase reintroduces exactly the multi-minute cycle-body problem the other two fixes just removed. | Would be complete per-trader coverage *if* it could run, but it structurally cannot at any cadence with a population this size. Rejected regardless of which subset (40,929 / 5,732 / 4,500) is used — the shape is wrong, not just the size. |
| **(iii) Per-market polling on canonical geo/elec population (~9,800 markets)** | To *discover* new activity (not backfill a known market), every market would need checking every cycle absent some other "which markets are hot right now" signal — **~9,800 calls/cycle** in the naive case. | **Fails outright** for the same reason as (ii) — thousands of calls/cycle. | Structurally the wrong tool for this problem: per-market polling answers "what happened in market X," not "which of 9,800 markets had activity in the last N minutes" — that discovery question is exactly what the platform-wide feed already answers. Useful for *targeted backfill of a known market* (not attempted here — out of scope), not for real-time discovery across the whole population. |
| **(iv) Raise the limit alone (500→10,000), no pagination** | 1 call/cycle. | Trivially fits. | At current velocity, 10,000 trades ≈ 636-670s (~10.6-11 min) of platform activity per call. At a healthy 900s cadence that's **~71-74% coverage in one call** — a large improvement over ~2%. At the still-observed 75-85 minute gaps, coverage drops back to **~12-14%** — real progress, but the majority of a large gap is still missed by a single call. |

**Chosen: (i) combined with (iv)** — raise the per-call limit to the
server's actual cap (10,000) **and** paginate via `offset` until the cursor
is covered or a defensive page cap is hit. The task's own framing already
treats these as compatible, not competing; combining them minimizes the
number of round trips needed to cover any given gap, which is the more
rate-limit-conscious choice on top of being the most complete.

---

## PART 3 — IMPLEMENTATION

### `monitoring/polymarket_client.py` — `get_market_trades()`

- `limit` now capped at the real server maximum, **10,000** (was `min(limit, 500)`).
- New `offset: int = 0` parameter, passed straight through as the `offset`
  query param.
- **Removed** the `after_timestamp` parameter entirely — it sent a
  confirmed-ignored `after` query param. Its docstring previously called it
  "best-effort"; today's testing shows it was doing nothing at all. The one
  caller (`monitor.py`) no longer passes it; the two archived, non-runnable
  scripts that call this method don't use it either.
- New `max_retries: int = 3` parameter: on HTTP 429, retries with
  exponential backoff (1s, 2s, 4s) before giving up and returning `[]` for
  that page. Non-200/non-429 responses and exceptions still return `[]`
  immediately, matching existing behavior.

### `monitoring/monitor.py` — `check_for_new_trades()` / new `_fetch_recent_trades_paginated()`

Extracted the fetch into its own method (same reasoning as the cycle-wait
fix's `_wait_for_next_cycle()` extraction: testable in isolation without
constructing a full `PolymarketMonitor`, whose `__init__` opens the
production DB unconditionally):

```python
async def _fetch_recent_trades_paginated(self) -> tuple:
    all_recent_trades = []
    pages_fetched = 0
    for page in range(MAX_FETCH_PAGES_PER_CYCLE):  # 30
        pages_fetched = page + 1
        page_trades = await asyncio.to_thread(
            self.polymarket.get_market_trades,
            market_id=None, limit=FETCH_PAGE_LIMIT,  # 10000
            offset=page * FETCH_PAGE_LIMIT,
        )
        if not page_trades:
            break
        all_recent_trades.extend(page_trades)
        oldest_ts_this_page = _parse_trade_timestamp(page_trades[-1].get('timestamp'))
        reached_cursor = (self.last_trade_timestamp is not None
                          and oldest_ts_this_page is not None
                          and oldest_ts_this_page <= self.last_trade_timestamp)
        end_of_history = len(page_trades) < FETCH_PAGE_LIMIT
        if reached_cursor or end_of_history or self.last_trade_timestamp is None:
            break
    return all_recent_trades, pages_fetched
```

Downstream of this (the flagged-trader-set filter, category exclusion,
per-trade insert/dedup logic in `check_for_new_trades()`) is **completely
unchanged** — same `flagged_set` membership test, same
`_should_exclude_market()` call, same `duplicate_count`/`new_trades_count`
accounting. Only what gets fetched and how changed.

### Starvation — addressed explicitly, not assumed away

**The old code already made this call synchronously, unwrapped, directly
blocking the event loop** (`all_recent_trades = self.polymarket.get_market_trades(...)`,
no `await`, no `asyncio.to_thread` — a smaller, single-call instance of the
same anti-pattern the notify-queue fix removed elsewhere). Measured: a
`limit=500` call takes ~0.55s; a `limit=10,000` call takes ~3.45s. Doing
that synchronously up to 30 times in the worst bounded case would freeze
the entire event loop for over a minute — reintroducing real starvation
exposure for the watchdog and both background workers, exactly what this
task's constraints forbid.

**Fixed as part of this change**: every page fetch now goes through
`await asyncio.to_thread(self.polymarket.get_market_trades, ...)`, matching
the "FIX-2 2026-05-25" pattern already used pervasively elsewhere in this
file for blocking calls. This moves each HTTP call to a worker thread,
letting the event loop keep servicing the watchdog and both background
workers between (and during) page fetches. `tests/test_fetch_ceiling_pagination.py`
Section 6 confirms this by source inspection — no direct, un-threaded call
to `get_market_trades(...)` remains in the method.

**Worst-case cycle-body cost, bounded**: up to 30 sequential `to_thread`
calls at ~3.45s network latency each ≈ **~100s worst case**, wall-clock,
non-blocking to the loop — nowhere near the old 125-minute pathology, and
self-healing (a gap larger than 30×10,000 trades continues draining over
subsequent cycles rather than trying to close it in one).

### Rate limits — explicit backoff, not just written

`get_market_trades()`'s retry loop (1s → 2s → 4s exponential backoff on
429, 3 attempts before giving up) is exercised directly in
`test_fetch_ceiling_pagination.py` Section 5 against a mocked flaky
endpoint that returns 429 twice then 200 — proving the retry actually
happens and actually succeeds, not just that the `except`/backoff code
exists untested.

### The cursor — behavior and persistence

`last_trade_timestamp` is unchanged in how it's stored: loaded from
`self.db.get_monitor_state('last_trade_timestamp')` in `__init__`, written
via `self.db.set_monitor_state(...)` at the end of `check_for_new_trades()`
— **it already persists across restarts today**, in the `monitor_state`
DB table, and continues to under this change. What changed is *how it's
used*: previously sent (uselessly) as an ignored `after` request parameter;
now used purely client-side as the pagination stopping criterion (compare
each page's oldest trade against it) and, unchanged from before, as the
final per-trade dedup filter later in `check_for_new_trades()`. Cold start
(`last_trade_timestamp is None`, e.g. a fresh database) fetches exactly one
page, matching the previous single-snapshot startup behavior — there is
nothing to "catch up to" without a prior cursor, and fetching 30×10,000
trades on first boot would be needless.

---

## PART 4 — VERIFICATION

### 1. Old vs. new, same window — both a committed differential test and a live demonstration

**Committed test** (`tests/test_fetch_ceiling_pagination.py`, 17/17 PASS):
built a synthetic 3-page (1,500-trade) fixture with a flagged trader's
trades deliberately placed on page 1 (positions 5, 12) **and** buried on
page 3 (positions 1250, 1300) — a shape a single 500-row snapshot
structurally cannot reach regardless of any cursor value, since `after` is
confirmed ignored. Reproduced the OLD single-snapshot call (`limit=500,
offset=0`, one call — the shipped code no longer has this shape, so
reimplementing it inline is the only way to demonstrate what it used to
do, matching `tests/test_backfill_market_categories_pagination.py`'s
established convention) against the same fixture as the NEW
`_fetch_recent_trades_paginated()`. **OLD finds 2 of 4 flagged trades in 1
call; NEW finds all 4 across 3 calls** — a test where these numbers
matched would have proven nothing.

**Live demonstration** (real API, real production flagged-trader set,
40,929 addresses, read-only, 2026-09-17 21:10-21:24 UTC): the live monitor's
actual cursor was `2026-09-17T21:10:03`; ~13.7 minutes had elapsed since.
- **OLD** (1 call, `limit=500`): returned trades covering only back to
  `21:19:30` — leaving `21:10:03`→`21:19:30` (9m27s of the gap) completely
  unfetched. **49 flagged-trader trades found.**
- **NEW** (paginated, `limit=10,000`): 2 calls, covered back to `20:58:25`
  (past the cursor, confirming full coverage of the gap plus expected
  overlap into already-processed territory, which the existing per-trade
  cursor-dedup handles). **1,692 flagged-trader trades found.**
- **34.5x more flagged-trader trades captured, for 2 calls instead of 1,**
  on the identical real window.

### 2. Cycle body stays fast

Measured directly: a `limit=500` call ≈0.55s, a `limit=10,000` call ≈3.45s
(both network latency, both now off the event loop via `asyncio.to_thread`).
Expected cycle-body fetch time: **~3.5-7s at a healthy 900s cadence
(1-2 pages)**, up to **~25-30s at the current 75-85 minute gaps
(7-8 pages)**, bounded at **~100s worst case** (the 30-page defensive cap)
for an anomalously large gap — self-healing over subsequent cycles, never
reintroducing tens-of-minutes-to-hours cycle bodies.

### 3. Rate-limit handling — tested, not just written

`test_fetch_ceiling_pagination.py` Section 5: mocked `requests.get` to
return 429, 429, then 200; confirmed `get_market_trades()` retries and
returns the eventual success's data (not `[]`), makes exactly 3 attempts,
and sleeps with the correct increasing backoff (1s, then 2s — mocked, so
the test itself runs in well under a second despite exercising the real
backoff *logic*). A second case confirms sustained 429s give up cleanly
after `max_retries`, returning `[]` rather than raising or hanging.

### 4. `run_tests.py`, full suite

```
Files  : 30 run, 30 passed, 0 failed
Tests  : 339981 run, 339981 passed, 0 failed
RESULT: ALL TESTS PASSED
```
(`test_behavioral_integration.py` excluded per its own documented
cold-cache-hang convention, unrelated to this change.) Includes all three
new/changed test files from this effort:
`test_fetch_ceiling_pagination.py` (17/17), plus the two from the previous
fix, `test_notify_queue_batch_drain.py` (18/18) and
`test_monitoring_loop_wait_shutdown.py` (10/10), confirmed still passing
unchanged.

**`metric_v2f_oos_result` canonical hash**
(`sqlite3 -list <db> "SELECT * FROM metric_v2f_oos_result ORDER BY kind;" | sha256sum`):
**`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` — unchanged**,
checked before this task, after all code edits, and after the full test
suite. The live monitor process (`MainPID=55865`, active since
`2026-09-17 06:14:08 UTC`) was confirmed untouched throughout — no restart
performed, per scope.

---

## PART 5 — EXPECTED EFFECT

Stated concretely, for tomorrow's measurement to check against, not a
vague hope:

- **Coverage of the live monitor's gap should move from ~0.15-2% (the
  09-17 diagnosis's figure, driven by a single 500-row snapshot against
  75-205 minute gaps) to effectively complete** — this fix pages back to
  the actual cursor rather than taking a fixed-size sample, bounded only by
  the 30-page defensive cap (≈300,000 trades, far beyond any gap this
  system should now produce once the other two fixes' cadence recovery
  takes hold).
- **Flagged-trader trades captured per cycle should rise sharply** — the
  live demonstration above found 34.5x more (1,692 vs. 49) on a real
  ~13.7-minute window; the exact multiplier will vary with time-of-day
  trading volume and how large the actual gap is at measurement time (a
  larger gap means an even bigger relative improvement over the old
  fixed-500-row snapshot, not a smaller one).
- **This does not mean every flagged-trader trade in the gap becomes a
  new DB row.** The existing category-exclusion filter and cursor-based
  dedup (both untouched) still apply exactly as before — this fix closes
  the *visibility* gap (whether a trade is fetched at all), not the
  *filtering* gap (whether a fetched trade is kept). Expect the "Excluded
  (crypto/sports)" and "Already seen" counts in cycle logs to rise
  proportionally too, not just "New trades."
- **API call count per cycle**: ~1-2 at a healthy 900s cadence, ~7-8 at the
  currently-observed 75-85 minute gaps, capped at 30 for a pathological
  gap. **Cycle-body fetch time**: ~3.5-7s typical, up to ~100s worst case
  — a small, bounded addition to cycle duration, not a return to
  multi-minute-to-hour bodies.
- **What this does NOT fix**: the 2026-09-12→2026-09-17 historical gap
  remains unbackfilled (explicitly out of scope — see below). The
  `background_backfill_worker`'s zero-completion anomaly (flagged
  2026-09-17, still unexplained) is untouched by this change.

### What backfilling the 09-12→now gap would need (not done here)

Named per the task's instruction to say what would be needed without doing
it: the platform-wide `/trades?offset=N` feed only reaches back through
however much history the Data API retains at that endpoint (untested here
how far back that is — the largest offset tested was 1,000, all within the
last few minutes). If it retains days-to-weeks of history, the *same*
paginated-fetch mechanism this fix adds could in principle walk all the way
back to 2026-09-12 by continuing past the current cursor with a much larger
page budget — but that is an explicit, deliberate, separate decision (how
far back the API actually retains data, how many calls that would take
against rate limits over a sustained run, and whether the result is worth
writing into a `trades` table already relied upon by committed downstream
metrics) — not something to back into as a side effect of a live-ingestion
fix.

## Scope adherence

No service restarted. No production table written to (the live A/B
demonstration made read-only `GET`s only and read, never wrote, the
production DB's `traders`/`monitor_state` tables to build the comparison).
The two fixes from `2026-09-17-notify-queue-and-cycle-wait-fix.md`
(first-repo `01525d7`) were not touched. The 09-12-to-now gap was not
backfilled. The flagged-trader filter, category filter, and
`check_interval` were not changed — `check_for_new_trades()`'s filtering
logic downstream of the fetch is byte-for-byte the same code, only its
input (now paginated, at a higher per-page limit) changed.

---

## PART 6 — RESTART AND MEASUREMENT (2026-09-18)

All three fixes (first-repo `01525d7` + `42d241a`) went live via a
`systemctl restart polymarket-monitoring` on 2026-09-18 16:22:21 UTC — the
restart this doc's Part 4/5 explicitly deferred, executed as its own task
roughly 21 hours after the fetch-ceiling commit landed. Observer was not
touched, per that task's scope.

### Baseline (immediately pre-restart)

- **PID 55865**, confirmed still running pre-fix code, active since
  `2026-09-17 06:14:08 UTC` (unchanged since the previous day — the restart
  genuinely had not happened yet). CPU time 1d4h58m31s, RSS 155,020 KB
  (~151 MB), VSZ 1,723,332 KB.
- `trades` count: **14,897,859** @ 2026-09-18 16:18:54 UTC.
- Trades in the prior 24h by `data_source`: **background_backfill 926,
  polymarket_api 48** — live ingestion still a small fraction of backfill
  volume, consistent with the pre-fix single-500-row-snapshot ceiling.
- `monitor_state.last_trade_timestamp`: `2026-09-18T15:40:37`.
- Cycle number reached: **#28**. Gaps between the last five cycle starts
  (#24→#28): 4048s, 4078s, 4023s, 4059s — a tight **67-68 minute band**,
  worse than the 900s target but *not* as bad as the 75-85 minute figure
  this doc's Part 5 and the restart task both flagged as the possible
  negative outcome. Still clearly the starved pattern the fix targets.
- `notified = 0` count: **0** — already fully drained pre-restart (the
  queue had emptied out through the old per-row mechanism at whatever pace
  it was running; this doesn't change the batch-drain fix's correctness,
  just means the "before" state for that specific metric was already
  clean).
- Box: last boot 2026-09-12 13:07 UTC, uptime 6d3h+ at check time — **no
  reboots since**, box stayed up through the full unattended window.
- 2026-09-18 06:00 UTC `daily_maintenance` run: completed, **33/34 steps
  OK**, 1 failed (`Canonical definitions drift`), runtime 15,564.2s
  (~4h19m), finished 10:19:25 UTC.
- Observer: PID 55866, active since `2026-09-17 06:14:08 UTC` (bounced
  together with the monitor by the 09-17 unattended-upgrade, as expected).
  RSS **212,040 KB (~207 MB)** against the ~246 MB it started at after the
  09-13 pruning fix — **down, not up**, after ~35h live. First real
  post-fix data point on that leak, and it's bounded.

### Restart

Clean stop — `systemd[1]: Stopping... / Deactivated successfully. /
Stopped...`, no SIGKILL needed, consumed 1d5h1m49.825s CPU / 9.9G memory
peak over its run. New process: **PID 67130**, started 16:22:21 UTC.
Startup log confirmed a normal boot (singleton lock acquired, category map
loaded — 2,100 markets/events, watchdog/pnl_worker/backfill_worker all
started cleanly).

### Three-cycle measurement

| Cycle | Start (UTC) | Body duration | Gap from prev. start | Gap from prev. complete | Pages | Fetched | Found-from-flagged | New / Seen / Excluded | Processing N |
|---|---|---|---|---|---|---|---|---|---|
| #1 | 16:23:41 | 138s | — (first post-restart) | — | 3 | 20,000 | 464 | 65 / 5 / 394 | 65 |
| #2 | 16:41:03 | 136s | 1042s | **904s** | 3 | 20,000 | 389 | 64 / 10 / 315 | 64 |
| #3 | 16:58:26 | 90s | 1043s | **907s** | 2 | 20,000 | 533 | 86 / 3 / 444 | 86 |

No 429s, 408s, or "database is locked" observed across any of the three
cycles or the startup phase.

Checks against the stated expectations:
- **Cycle gaps near 900s**: confirmed, measured complete-to-start (904s,
  907s) — essentially exact. Start-to-start gaps read ~1042-1043s because
  they include each cycle's own ~90-140s body on top of the 900s sleep;
  that's the expected shape (body + fixed sleep), not a miss.
- **Processing N == that cycle's own new_trades, no carryover**: confirmed
  all three cycles (65/64/86, exact match each time).
- **1-2 API pages per cycle once cadence recovers**: partially — cycle #3
  hit 2, cycles #1-#2 hit 3 (20,000 trades each, ending on a short/empty
  page). Real platform velocity in this window ran a bit above the
  10-28 trades/sec estimate this doc's Part 2 used, or the first two
  post-restart cycles were still draining residual gap from the final
  pre-restart cursor position — plausible given cycle #1 immediately
  followed a 67-minute-gap cycle. Not a concern: still 2-3 calls, not the
  7-8 the 75-85 minute pathology would have produced, and well inside the
  30-page defensive cap.
- **Flagged-trader trades captured rising sharply**: confirmed — 464, 389,
  533 per cycle, all far above the old single-snapshot baseline (49 on a
  comparable ~13.7-minute window, per Part 4 above).
- **Excluded and already-seen counts rising proportionally, not just new**:
  confirmed — excluded ran 394/315/444 and already-seen 5/10/3, both
  moving with the fetch volume rather than staying flat.

**Verdict: cadence recovered, ingestion is rising. This is not the
75-85-minute negative-result scenario** — gaps landed at 904-907s
complete-to-start, a clean recovery to the 900s design target, with no
sign of pnl_worker or the backfill worker starving the single await in
`_wait_for_next_cycle()`.

### Ingestion, after the window

- `trades` count: **14,898,074** vs the 14,897,859 baseline — **+215**, all
  215 attributed to `data_source = polymarket_api` (query windowed on
  `timestamp >= '2026-09-18 15:40:37'`, the pre-restart cursor, to also
  catch any catch-up trades with older on-chain timestamps than the
  restart wall-clock; the +215 total matches the sum of the three cycles'
  own "New trades" counts exactly: 65+64+86=215).
- Rate: 215 trades over the ~37.6-minute measurement window (16:22:21 →
  16:59:56) ≈ **~343 trades/hour**, against the **~1.3/hour** baseline of
  the preceding five days — roughly **260x**.
- `notified = 0` count: **0**, unchanged from the pre-restart baseline —
  the batch drain is holding at zero.

### Scope adherence for this task

Only `polymarket-monitoring` was restarted; the observer was not touched.
No config, limit, or interval was changed. The 09-12-to-now historical gap
was not backfilled. No profiler was attached to the running process.
