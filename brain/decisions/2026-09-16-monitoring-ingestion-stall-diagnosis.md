# 2026-09-16 — Monitoring Ingestion Stall Diagnosis (READ-ONLY)

## TOP-LINE VERDICT — ACTIVE DATA LOSS CONFIRMED

**Part 1's decisive check found the API holds trades the DB does not.** This is not
a quiet market. Magnitude, from 3 sample geo/elec markets that were actively traded
before the 2026-09-12 13:07:20 UTC reboot:

| Market | DB trades since reboot | API trades since reboot | Gap |
|---|---|---|---|
| "Will China invade Taiwan by end of 2026?" (`0xd9fb1184...`) | **0** | **≥500** (API's per-call cap hit; window covers only the last ~58h of the ~99h since reboot — true total is higher) | DB missing the entire post-reboot window |
| "Will Flávio Bolsonaro win the 2026 Brazilian presidential election?" (`0x1a01bf78...`) | **3** (last row 09-13 19:26) | **≥500** (cap hit, spans ~77h) | DB captured well under 1% |
| "Russia x Ukraine ceasefire agreement by December 31, 2026?" (`0x5c19f205...`) | **2** (last row 09-13 16:01) | **97** (exact, not cap-limited) | DB captured ~2% |

5 live API calls were made total (1 gamma-api health check, 1 data-api health check,
3 per-market trade pulls). No writes were made to any table; no signals were sent to
the monitoring process.

This is Oscar's call on remedy. What follows is the mechanism, not a fix.

---

## Part 1 — Is data actually missing, or is the market quiet?

**Missing. Confirmed by direct API comparison above.**

Daily trades ingested into `trades`, last 14 days (`date(timestamp)`, all categories):

| Day | Trades | | Day | Trades |
|---|---|---|---|---|
| 09-02 | 1,056 | | 09-10 | 2,582 |
| 09-03 | 5,415 | | 09-11 | 2,392 |
| 09-04 | 6,910 | | 09-12 | 1,660 *(reboot at 13:07)* |
| 09-05 | 5,643 | | **09-13** | **61** |
| 09-06 | 2,386 | | **09-14** | **46** |
| 09-07 | 1,671 | | **09-15** | **25** |
| 09-08 | 1,843 | | **09-16** | **16** *(partial day)* |
| 09-09 | 3,284 | | | |

Baseline pre-reboot average: ~3,000 trades/day (range 1,056–6,910). Post-reboot: a
~98% collapse, landing exactly on 2026-09-12 13:07:20 — the reboot timestamp, not
some later date. Hourly counts for the last 48h show the same picture: single-digit
trades per hour, many hours with zero, no diurnal pattern suggesting a live market
— it looks like whatever trickles in is landing by chance, not by design.

Live API health check (gamma-api and data-api) both returned HTTP 200 in <0.4s —
network access from this host is fine right now. Network was **not** the blocker at
diagnosis time. (One transient DNS failure was logged during the reboot itself at
2026-09-12 13:08 — see Part 3 — but that was a single startup-time event, not
sustained.)

**Verdict: ingestion is broken, not the market being quiet.**

---

## Part 2 — What is the loop actually doing between cycles?

**Cadence mechanism:** `PolymarketMonitor.__init__` sets `check_interval=900` (15
minutes, `monitoring/monitor.py:67,104`) — matches CLAUDE.md's claim. It is a plain
sleep loop, not a scheduler or cron: after each cycle body finishes (successfully
*or* via a caught exception), `monitoring_loop()` runs `for _ in range(900):
await asyncio.sleep(1)` (`monitor.py:1318-1321`), checking `is_running` each second.

**Actual behavior, reconstructed from `journalctl -u polymarket-monitoring` since
the 2026-09-12 13:07:25 boot (78 cycles observed by 2026-09-16 20:04, not 76 —
close to the catch-up check's count):**

- The large majority of cycles run 75–140 minutes apart (start-to-start), not 15.
- One cycle (#6) took **~4.5 hours** to complete (21:35 09-12 → 02:04 09-13).
- One 10-cycle streak (#11 through #21, 2026-09-13 10:24–13:43) ran at the
  *documented* ~15–20 minute cadence — but **10 of those 11 cycles never logged
  "[OK] Cycle complete."** They hit an exception that was caught by the top-level
  `try/except` in `monitoring_loop()`, which logs `[ERROR] Error in monitoring
  cycle: ...` and falls straight through to the normal 900s sleep without doing the
  rest of the cycle's work. Fast-but-incomplete cycles look identical to fast
  complete cycles in the start-to-start gap; they are not the same thing.
- **12 of 78 cycles overall (~15%) never logged a completion line.**

**Is the gap sleep or work?** Both, at different times. The 900s post-cycle sleep is
real and unconditional. On top of that, cycle *bodies themselves* run long — #2 took
83 minutes, #6 took ~268 minutes, #22 took ~73 minutes — pushing genuine start-to-
start gaps well past 15+15=30 minutes into the 75–140 minute range seen throughout.

**Does monitor.py share the observer's blocking-sqlite3-in-async pattern?**
**Yes.** `check_for_new_trades()` writes new trades via `asyncio.to_thread(self.db.
add_trade, ...)`, and several helper methods (`_batch_update_market_end_dates`,
`_backfill_clob_end_dates`, `_update_activity_timestamp`) open raw `sqlite3`
connections directly rather than going through any shared pool/lock discipline.
These run concurrently, as separate asyncio tasks in the *same process*, alongside
`BackgroundPnLWorker` and `BackgroundBackfillWorker` — both of which also hit the
same SQLite file continuously (visible every ~16 seconds in the journal:
`pnl_worker - INFO - Batch start: 10 traders`).

**Are cycles erroring and retrying?** Confirmed, but bounded, not continuous:
**all 408** `sqlite3.OperationalError: database is locked` errors logged across the
entire 4-day window fall in a single **7.5-hour storm on 2026-09-13, 06:02–13:40
UTC** — exactly overlapping the incomplete-cycle streak (#8, #10, #12–21). Outside
that window, zero lock errors were logged in the monitoring service's own journal.

Important nuance: the baseline ~75–90 minute cadence degradation was **already
present before the lock storm** — cycle #2 (09-12, pre-storm) took 83 minutes with
no lock errors at all. So the DB-lock storm explains the acute 09-13-morning chaos
(and the missing-completion streak) but **does not by itself explain the underlying,
persistent slow cadence present from cycle #1 onward.** What specifically consumes
70–90+ minutes inside an otherwise error-free cycle body was not conclusively
isolated in this pass (see "What was not determined").

**Verdict: the loop is alive, not wedged** — heartbeat lines every 5 minutes
continue right up to the time of this diagnosis (20:02:18 today), and the PID (1228)
has been running continuously since the reboot. It is slow and intermittently
erroring, which is a different problem from hung.

---

## Part 3 — What does a cycle actually fetch?

`check_for_new_trades()` calls:

```python
self.polymarket.get_market_trades(market_id=None, limit=500,
                                   after_timestamp=self.last_trade_timestamp)
```

With `market_id=None`, `PolymarketClient.get_market_trades` (monitoring/
polymarket_client.py:217-255) omits the `market` filter entirely and hits
`GET https://data-api.polymarket.com/trades?limit=500` — **the 500 most recent
trades across the entire Polymarket platform, all markets, all categories, in one
unpaginated call.** The client-side code then filters that batch down to (a) trades
from the ~200-ish already-`is_flagged` traders, and (b) markets that pass the
three-layer category/keyword/AI filter. This fetch strategy predates the reboot —
it is not something that changed at 2026-09-12 13:07; the surrounding code carries a
2026-05-25 `FIX-2` tag unrelated to this incident.

**This is the mechanism that turns Part 2's cadence problem into Part 1's data
loss.** A fixed 500-trade snapshot is adequate when cycles run close to the intended
15-minute spacing, because platform-wide trade volume in 15 minutes apparently fits
inside 500 rows well enough. Once cycle spacing degraded to 75–140 minutes, platform
volume in that widened window vastly exceeds 500 — the API check above shows a
single market alone produced ≥500 trades in under 58 hours. Trades scroll off the
front of the "last 500, platform-wide" window and are gone before any cycle reaches
them. There is no backfill path for this specific loss: `BackgroundBackfillWorker`
only backfills complete history for *newly-flagged* traders, not real-time platform
trades missed during a gap.

The documented ~300 markets/day keyword-filter dropout (`HARD_EXCLUDE_CATEGORIES` /
`_keyword_exclusion_check`, MASTER_HANDOVER_2026-09-05 §6) is a real, separate
narrowing layer applied on top of the 500-row cap — but it was already active before
the reboot and is not what caused the collapse; it just makes the effective sample
even smaller than the raw 500-row cap already implies.

**Fetched-vs-inserted per cycle:** the log does distinguish these (`[OK] Fetched N
recent trades` followed later by `[OK] New trades: X | Already seen: Y | Excluded
(crypto/sports): Z`), but this pass did not tabulate every one of the 78 cycles —
noted below as not fully determined. The structural finding (fixed 500-row,
non-paginated, platform-wide fetch) does not depend on that tabulation.

**Did anything change at the 09-12 reboot itself?** No code-level config or state
read was found that would behave differently after a restart — `check_interval`,
the filter keyword lists, and the fetch strategy are all hardcoded constants. One
transient event was logged exactly at startup: a DNS resolution failure reaching
`gamma-api.polymarket.com` for the initial category-map refresh
(`[CATEGORY MAP] Fetch error at offset 0: ... Failed to resolve
'gamma-api.polymarket.com' ...`, 2026-09-12 13:08). This did not recur and is not
evidence of a persistent network problem — network access was confirmed live during
this diagnosis. Whether that one DNS hiccup and the subsequent cadence degradation
are related was not established.

---

## Part 4 — Downstream consequence

**Geo pending backlog (152→1):** consistent with an empty pipe, not a solved
problem. Since 09-13, ingestion for the sampled geo/elec markets has captured 0–3
trades each over 3+ days against an API showing 97 to 500+ in the same window — far
too little new material to be feeding the backlog, while whatever drains it keeps
running. **Not independently confirmed against the specific 152→1 counter**: the
`markets` table schema in this DB does not have a `pending_resolution` column (the
query attempt against that name failed), so the exact table/counter behind the
152→1 figure was not located in this pass — see "What was not determined." The
directional conclusion (empty pipe) is inferred from the ingestion collapse, not
verified against that specific artifact.

**Stale-data exposure:** anything computed from `trades`/`markets` for the period
2026-09-12 13:07 onward — the canonical population, Pool C, any behavioral/ELO
metric, the Sunday 2026-09-14 03:00 UTC full ELO recalculation, any
`daily_maintenance.py` run in this window — is built on a trades table missing on
the order of 95-98%+ of actual platform activity for that period. These jobs almost
certainly reported success in their own logs; success there means "ran to
completion," not "saw complete data." Which specific committed measurements/decision
documents from this window are consequently unreliable was **not enumerated** in
this pass — flagged below.

**Observer burst-storm correlation:** **not determined.** Searching the observer's
own journal since 2026-09-09 for burst/storm/contention language returned zero
matches, so this could not be confirmed or refuted directly. What is established
from the monitoring side is that the DB-lock error storm was a single bounded
7.5-hour event (09-13 06:02–13:40, Part 2), not a sustained multi-day condition — if
the observer's burst-storm cessation genuinely tracks reduced DB contention from
"less monitor work," it should map onto that same narrow window, not the whole
post-09-13 period. This is inference from the monitoring-side numbers, not a
verified cross-reference against the observer's own records.

---

## Stop conditions — status

- **Part 1 confirms the API holds trades the DB does not** → reported prominently
  above, with counts. This is the headline finding.
- **Loop wedged vs. slow** → not wedged. PID 1228 alive continuously since the
  reboot, heartbeat logging every 5 minutes through the time of this diagnosis,
  cycles continue to start and (mostly) complete. It is slow and intermittently
  error-aborting, not hung.
- **`metric_v2f_oos_result` hash** → not independently re-verified in this pass;
  this diagnosis made no writes to any production table and touched nothing that
  metric depends on, so no action was taken on this condition.

## What was not determined

- The specific root cause of the ~75–90 minute cycle-body duration *outside* the
  09-13 lock-error storm (e.g., cycle #2's 83 minutes, cycle #6's ~4.5 hours) was
  not isolated to a specific line of work (CLOB per-market end-date backfill calls,
  trader re-scan, category-map refresh, or something else). The lock-storm explains
  the 09-13 06:02–13:40 chaos specifically; it does not explain the baseline
  degraded cadence present from cycle #1 onward.
- Full per-cycle "fetched vs. inserted vs. excluded" tabulation across all 78 cycles
  was not built — only the structural mechanism (500-row, unpaginated,
  platform-wide fetch) was established from code + spot API checks.
- The exact table/column behind the reported "152→1" geo pending backlog figure was
  not located (the `markets` table has no `pending_resolution` column); the
  empty-pipe conclusion for that figure is inferential, not directly queried.
- Whether the observer's "burst storm" cessation after 09-13 is causally the same
  story as the monitoring-side lock storm was not confirmed — no burst/storm
  terminology was found in the observer's journal in the searched window.
- Whether the one startup-time DNS resolution failure (2026-09-12 13:08) is related
  to the subsequent cadence degradation was not established either way.
- Which specific already-committed decision documents/measurements (beyond the
  general categories named above) rest on the 09-12–09-16 data gap was not
  individually enumerated.

## Scope adherence

No writes to any production table. No restart, stop, or signal sent to
`polymarket-monitoring` or `polymarket-observer`. 5 live Polymarket API calls made
(reported above). Journal reads scoped to `--since 2026-09-12 13:07:20` (current
boot) throughout, except the one broader `--since 2026-09-09` sweep for observer
burst-storm terminology, which returned no matches and made no state changes.
