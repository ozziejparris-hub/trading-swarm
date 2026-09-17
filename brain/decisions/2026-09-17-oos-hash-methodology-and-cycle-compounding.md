# 2026-09-17 — oos_result Hash Methodology Resolved; Cycle-Body Compounding Diagnosed (READ-ONLY)

No fixes, restarts, config changes, table writes, or profiler/debugger attachment.
One live read-only GET to Polymarket's public Data API (quantifying platform trade
velocity, Part 2's dropped-trades question — same precedent as the 2026-09-09
diagnosis's "5 live API calls"). `check_canonical_definitions.py`-style direct
`SELECT`s and pure-function imports (`build_keyword_where()`) only; no script was
run that writes to any table.

---

## PART 1 — THE HASH: METHODOLOGY ARTIFACT. TABLE UNCHANGED.

**Verdict up front: `metric_v2f_oos_result` has not changed.** Every field is
bit-identical to the 2026-09-09 pre-drain snapshot. Yesterday's "mismatch" was
two different, both-valid serialisations of the same unchanged table, compared
against each other by mistake.

### Where each hash actually comes from

- **`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`** —
  first recorded 2026-09-09, `brain/decisions/2026-09-09-predrain-baseline-capture.md`
  (line 16, first-repo commit `281c0f9`). It was then hardcoded as
  `OOS_RESULT_SHA_EXPECTED` in **first-repo `c9619a4`** (2026-09-10 19:16:54 UTC,
  `scripts/copy_trade_decay_diagnostic.py`) and **`b81e2f6`** (2026-09-10 20:49:43
  UTC, `scripts/own_market_calibration.py`), then imported from
  `own_market_calibration.py` into `scripts/elo_tier_causal_test.py` and
  `scripts/skilled_presence_causal_test.py`. **All four of these are the
  project's actual stop-condition gates** — each does `sha_before =
  oos_result_sha(args.db); if sha_before != OOS_RESULT_SHA_EXPECTED: sys.exit(3)`.
  Note: this is 2026-09-10, not 2026-09-11 as this task's framing assumed — see
  "correction to the stated premise" below.

- **`b58d6606f109bd318d524a35a5b1c38b92fa5996c85fbeea45d18ba3ee4ec4db`** — never
  appears anywhere in the committed record before yesterday
  (`2026-09-16-monitoring-ingestion-stall-diagnosis.md`, this session's own
  prior addendum). It is the output of `capture_predrain_objective2_membership.py`'s
  internal `_oos_result_hash()` (first-repo `281c0f9`, 2026-09-09, **never
  modified since — one commit total**), which hashes `json.dumps(rows,
  sort_keys=True, default=str)` of the same `SELECT`. That function only
  compares its own before-vs-after within a single run — it has **never**
  referenced or been checked against `021be40a` in its own code. Running it
  live today is what produced `b58d6606…` in yesterday's check.

**Correction to the stated premise:** no document dated 2026-09-11 describing
"two different serialisations recorded in the same session" was found. The
phrases "sqlite3 -list" and "JSON-rows guard hash" do not appear anywhere in
either repo before today. The two hashes are real and both traceable, but not
via the specific 09-11 session claimed — they come from two different scripts
committed 2026-09-09 and 2026-09-10 respectively, each computing its own
digest for its own purpose, never cross-checked against each other by anyone
until yesterday's task did so by accident.

### Recomputed both ways today, live, off the current unmodified table

```
sqlite3 -list <db> "SELECT * FROM metric_v2f_oos_result ORDER BY kind;" | sha256sum
  -> 021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e   MATCHES

python: SELECT kind,n_positions,n_traders,point_gap,ci_lo,ci_hi,spec_version,
        generated_at,generator_commit ... ORDER BY kind -> json.dumps(rows,
        sort_keys=True, default=str) -> sha256
  -> b58d6606f109bd318d524a35a5b1c38b92fa5996c85fbeea45d18ba3ee4ec4db   MATCHES
```

Both baselines reproduce exactly, today, from the live table. **One matches
`021be40a…`, the other matches `b58d6606…` — the discrepancy is methodological,
confirmed, not assumed.**

### Confirming the table is unchanged (not just "both hashes happen to reproduce")

Diffed every stored field against the committed pre-drain snapshot
(`data/characterizations/predrain_table_snapshots_20260909T201245Z/metric_v2f_oos_result.sql`),
at full double precision, not the ~10-decimal figures quoted in prose docs:

| field | 09-09 snapshot | today (live table) | identical? |
|---|---|---|---|
| cohort point_gap | 0.0315983580923187012 | 0.0315983580923187 | yes (same double) |
| cohort ci_lo | -0.00881147179033795607 | -0.008811471790337956 | yes |
| cohort ci_hi | 0.0710126418085990501 | 0.07101264180859905 | yes |
| placebo point_gap | 0.0127065403076488392 | 0.01270654030764884 | yes |
| placebo ci_lo | -0.0210094439314383769 | -0.021009443931438377 | yes |
| placebo ci_hi | 0.0461439972587876293 | 0.04614399725878763 | yes |
| n_positions, n_traders, spec_version, generated_at, generator_commit | 3032/120, 2569/110, SKILLV2F-2026-08-15-v1, 2026-08-15T19:36:56.852700+00:00, eaeabbc (both rows) | identical | yes |

Parsed both representations as Python floats and compared bit-for-bit
(`float(snapshot_str) == live_value`): **all six floats identical.** The
apparent digit differences are sqlite's `.dump` full-precision text format vs.
Python's shortest-round-trip `repr()` for the *same* IEEE-754 double — not a
data difference.

### Canonical serialisation — and the actual finding requested

**The project's four active stop-condition scripts agree with each other**:
`own_market_calibration.py` defines `oos_result_sha()` as
`hashlib.sha256(subprocess.check_output(["sqlite3", db_path, "SELECT * FROM
metric_v2f_oos_result"])).hexdigest()`; `copy_trade_decay_diagnostic.py` defines
an identical duplicate with the same docstring comment ("Exactly the
stop-condition definition... Shelled out so the digest matches that pinned
value byte-for-byte"); `elo_tier_causal_test.py` and
`skilled_presence_causal_test.py` both import `oos_result_sha,
OOS_RESULT_SHA_EXPECTED` from `own_market_calibration.py` rather than
reimplementing it. **This shell/`sqlite3`-based method is canonical** — it's
the one every actual gate checks against.

**The one script that disagrees is `capture_predrain_objective2_membership.py`**,
which implements its own JSON-rows Python hash for a self-contained
before/after check, unrelated to and never compared against the pinned
constant. **That disagreement is itself the finding the task asked to
surface**: nothing in either script, or in any doc, flags that these are two
different, incompatible digests of the same table. It cost nothing
functionally yesterday (the mismatched script's hash was never actually
checked against `021be40a` by any of the four real gates — they call their own
canonical function, not the JSON-rows one), but it is a live trap for any
future manual check, exactly as this task's own framing anticipated. Future
checks should call `own_market_calibration.oos_result_sha(db_path)` (or the
literal `sqlite3 <db> "SELECT * FROM metric_v2f_oos_result" | sha256sum`)
specifically, not any script's ad hoc internal hash.

**Part 1 clears. Table unchanged. Proceeding to Part 2.**

---

## PART 2 — THE COMPOUNDING SLOWDOWN

### (a) The cycle-wait — confirmed from code, `monitoring/monitor.py`

```python
# line 1318-1321, monitoring_loop()
for _ in range(self.check_interval):      # check_interval = 900
    if not self.is_running:
        break
    await asyncio.sleep(1)

# line 1339-1341, _watchdog_loop() — separate asyncio task
while self.is_running:
    await asyncio.sleep(300)              # single wait, 5 minutes
```

Confirmed: the cycle-wait is exactly 900 separate `await` round-trips; the
heartbeat is exactly one. This asymmetry — one held perfectly all night, the
other degraded — is real and is in the code, not inferred.

**What a single `asyncio.sleep(900)` would fix:** it would remove 899 of the
900 chances for the wait itself to be delayed by loop contention, collapsing
the wait's own exposure to starvation to (at most) one wakeup delay — matching
the heartbeat's proven robustness. It would very plausibly bring the
post-cycle wait itself much closer to the intended 900s.

**What it would NOT fix:** the cycle *body*. The wait only starts after
`check_for_new_trades()` / `notify_new_trades()` finish. Last night those
bodies ran 2s, 49m, 82m, 125m — all before any wait begins. A single-sleep fix
changes nothing about that number; total cycle-to-cycle gap (body + wait)
would still be dominated by the body once it's in the tens-of-minutes range.

### (b) The growing cycle bodies — mechanism found, read from code + logs only

**Root cause: `notify_new_trades()` (`monitor.py:992-1026`) runs an unbounded,
unfiltered `get_unnotified_trades()` query, and only ever drains it when a live
cycle happens to see `new_trades_count > 0`.**

```python
# monitoring_loop(), line 1231-1232 — the gate:
if new_trades > 0:
    await self.notify_new_trades()

# database.py:474-485 — the query, NO time bound, NO source filter:
SELECT trade_id, trader_address, market_title, outcome, shares, price, side, timestamp
FROM trades
WHERE notified = 0
ORDER BY timestamp DESC

# monitor.py:1024-1026 — drained ONE ROW AT A TIME:
for trade in unnotified_trades:
    await asyncio.to_thread(self.db.mark_trade_notified, trade['trade_id'])

# database.py:462-472 — each call opens its own connection, commits, closes:
def mark_trade_notified(self, trade_id):
    conn = self.get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE trades SET notified = 1 WHERE trade_id = ?", (trade_id,))
    conn.commit(); conn.close()
```

**Who feeds the backlog:** `background_backfill_worker.py:396-402` inserts
every backfilled historical trade with `notified` **hardcoded to `0`**:
```python
INSERT OR IGNORE INTO trades (..., side, timestamp, notified, completed,
    was_successful, trade_result, data_source)
VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0,NULL,?,'background_backfill')
```
`get_unnotified_trades()` has no `data_source` filter, so every one of these
backfilled rows — hundreds to thousands per newly-flagged trader, inserted
continuously in the background — sits in the same queue as genuine live
trades, waiting for whichever cycle next happens to trigger a drain.

**Directly observed, from the journal, exact numbers — this is not
inference:**

| Cycle (PID 52386, last night) | `new_trades` | notify triggered? | "Processing N trade notifications" | cycle-body duration |
|---|---|---|---|---|
| #1 20:15:29 | 0 | no | — | 2s |
| #2 21:45:09 | 1 | yes | **54,425** | 48m39s |
| #3 23:55:18 | 2 | yes | **88,062** (+33,637) | 81m57s |
| #4 02:36:00 | 1 | yes | **117,639** (+29,577) | 124m54s |
| #5 06:00:44 | 4 | yes | **143,829** (+26,190) | killed mid-drain at 06:13:38 (unrelated external restart) |

The backlog size at the start of each notify call tracks the cycle-body
duration almost exactly (≈53–64ms/row, rising slightly across the run — the
per-row cost itself degrading too, consistent with worsening contention, on
top of the backlog simply growing). **This is the compounding mechanism**:
cycle #1 had `new_trades=0` so never drained anything; the backlog kept
growing in the background between the widening gaps; every subsequent
triggering cycle inherited an even larger undrained pile, took even longer to
drain it, which left even more time for the next pile to grow before the
*next* trigger — self-reinforcing within one process's lifetime.

**Why a restart "resets" it — precisely, not just empirically:** the backlog
lives in the `trades.notified` column, which is NOT cleared by a process
restart. What actually happened this morning: the fresh process's very first
cycle (06:15:29) had `new_trades=3 > 0`, so it triggered `notify_new_trades()`
immediately and drained the **entire inherited 117,376-row backlog** (the tail
of what PID 52386 never finished draining) in one 58-minute cycle body. Every
cycle since has shown `Processing N` **exactly equal to that same cycle's own
`new_trades` count** (3=3, 3=3, 6=6, 2=2, 2=2, 2=2, 11=11) — zero carryover,
because the backlog was fully drained at 06:15:47 and has stayed near zero
since. Restart doesn't clear the mechanism; it just happened to be followed
almost immediately by a drain, which is what actually reset the visible
number.

**Separate, unresolved observation surfaced by this same check (not chased
further, per scope — logs only):** `background_backfill_worker.py` has logged
**zero** `Backfilled ...` completion lines since the restart (06:14:08 →
present, ~9h45m), versus 1,164 such lines in the ~10h before the restart. It
logged "Backfill queue: 567 traders awaiting fetch" once at startup and then
went silent — no further progress lines, no `Failed for ...` error lines
either. This is consistent with (and explains) why today's `notify_new_trades()`
numbers show zero backfill contribution — but *why* the worker has produced
nothing for 9h45m was not established from logs alone, and instrumenting
further would require live-process inspection, which is out of scope here.
**Flagged as a distinct anomaly for separate follow-up, not conflated with the
notify-queue mechanism above.**

---

## THE 493 DROPPED TRADES

Confirmed directly from the raw log for last night's cycle #1
(20:15:29–20:15:31): `Monitoring 40734 flagged traders...` → `[OK] Fetched 500
recent trades` → **`Found 7 trades from flagged traders`** → all 7 then hit the
keyword-exclusion filter → `New trades: 0 | Already seen: 0 | Excluded: 7`.

The accounting for the other 493: they are simply **not from any of the
40,734 flagged traders** — dropped at `monitor.py:844-852`'s `flagged_set`
membership test, before the exclusion/dedup logic (which only ever sees the 7)
runs at all. This is the intended design (only track already-known traders),
not a bug, but the consequence compounds with cadence and platform velocity.

**Quantifying the consequence — one live measurement (Data API, read-only
GET, `https://data-api.polymarket.com/trades?limit=500`, 2026-09-17 ~15:59
UTC):** the 500 most recent platform-wide trades spanned **18 seconds**
wall-clock (1789660779 → 1789660797 Unix epoch). Extrapolated:

- Platform rate at that moment: ≈500/18 ≈ 27.8 trades/second.
- In a 200-minute (12,000s) gap, the platform would generate ≈**333,000**
  trades.
- The fetch only ever returns the most recent 500. **≈500/333,000 ≈ 0.15% of
  a 200-minute window's platform volume is visible to any single fetch** —
  99.85% has already scrolled off the top before the next cycle can look.

This single sample is a snapshot, not a day-long average — platform trade
velocity is plausibly bursty and time-of-day dependent, and this reading may
be on the high end (or not). Even discounting it by an order of magnitude
(500 trades per ~3 minutes instead of 18 seconds — a generously slow
assumption), a 200-minute window would still generate ≈33,000 trades against
the same 500-row cap: **≈1.5% visibility**, not 0.15%. Under any plausible
rate this task's own framing is right to call it "close to hopeless": ingestion
depends on a flagged trader's trade landing inside whichever 500-row snapshot
happens to be fetched at the exact moment a (highly irregular, 90–205-minute)
cycle fires, against a platform generating that many trades in well under a
minute.

---

## PART 3 — CATEGORY BACKLOG: DEFINITIONAL MISMATCH, NOT A REAL SPIKE

Re-measured using **the exact predicate from the 2026-09-13 pagination-fix doc**
(`brain/decisions/2026-09-13-backfill-market-categories-pagination-fix.md`,
first-repo `scripts/backfill_market_categories.py`'s own `build_keyword_where()`,
imported and run live rather than retyped, to avoid transcription error):

```sql
SELECT COUNT(*) FROM markets
WHERE category = 'Unknown' AND title IS NOT NULL AND (<keyword clause from build_keyword_where()>)
```

| Reading | Predicate | Count |
|---|---|---|
| 2026-09-13 (committed, `2026-09-13-backfill-market-categories-pagination-fix.md`) | keyword-matching, addressable | **30,315** |
| 2026-09-17 (this check, same predicate, live) | keyword-matching, addressable | **31,143** (+828 over 4 days, ≈207/day) |
| 2026-09-17 (yesterday's report, and re-confirmed just now) | `category='Unknown'`, **no keyword filter** | 885,356 → **885,359** |

**The reported "864,417 → 885,356, ~21,000/day" jump compared the wrong two
numbers.** 864,417/885,356/885,359 are all readings of the *unfiltered*
`category='Unknown'` population (per the 09-13 doc's own words: "the
keyword-filtered, addressable-by-this-script subset (30,315) is a small
fraction of the full Unknown population"). That unfiltered figure was **never
the addressable backlog** — it includes every market that has never been
touched by this specific script's keyword-matching classifier at all,
including titles the script would correctly and permanently leave `Unknown`
(sports, weather, etc. — the 09-13 doc's own ~40% observed skip rate). Its
day-to-day drift tracks total new-market creation platform-wide, not this
backlog's completion progress.

**Using the actual addressable predicate, the real backlog moved 30,315 →
31,143 in four days — ~207/day, not ~21,000/day.** This is a modest, plausible
net-inflow rate (new keyword-matching markets being created faster than the
paused/slow classifier is clearing them), not a spike, and not evidence of
anything newly broken. No 2026-09-16 addressable-predicate reading was found
in the committed record to place a third point on this trend — only the
09-13 and 09-17 readings above exist under the correct predicate.

---

## WHAT WAS NOT DETERMINED

- **The exact source/session of the "864,417" figure** quoted in this task's
  framing as "yesterday['s]" reading was not located verbatim in the committed
  record. It is consistent in *scale* with the unfiltered `category='Unknown'`
  count (which is what this task's own re-measurement instruction implicitly
  assumed it was, and which this document confirms), but its precise origin
  (which command, which session) was not tracked down.
- **Why `background_backfill_worker` has logged zero completions in ~9h45m**
  since this morning's restart, despite starting normally and reporting a
  567-trader queue. Not diagnosable from logs alone without live-process
  inspection, which is out of this task's scope.
- **Whether today's still-long cycle-wait gaps (~75–85 minutes, cycle bodies
  now fast at 3–20s) are driven by `pnl_worker` alone**, now that
  `background_backfill_worker` appears to be contributing nothing. `pnl_worker`
  is confirmed still active (continuous "Batch start: 10 traders" every
  ~14s), but its exposure was not isolated the way the notify-queue mechanism
  was for last night's run — this task's evidence supports "the wait is still
  starved," not "by which specific worker, in what proportion," post-restart.
  A remedy is out of scope; naming the mechanism precisely enough to attribute
  proportional blame between the two workers was not completed.
- **The exact per-row cost breakdown** of `notify_new_trades()`'s drain (SQLite
  per-transaction commit/fsync overhead vs. event-loop-starvation queueing
  delay) was not separated quantitatively — the observed ~53–64ms/row is
  consistent with both contributing, in unknown proportion.
- **Whether platform trade velocity (measured once, live, at 18s/500 trades)
  is representative of a typical hour** vs. a momentary burst was not
  established; only the single live sample exists in this pass.

## Scope adherence

Read-only throughout. No code, config, or production-table writes; no
restarts or signals sent to either service; no profiler/debugger attached to
the running monitor. One live read-only GET to Polymarket's public Data API
(`/trades?limit=500`, unauthenticated, no different in kind from the 2026-09-09
diagnosis's precedent) for the platform-velocity quantification in the
dropped-trades section. `build_keyword_where()` was imported and called as a
pure function (no DB write) to reproduce Part 3's predicate exactly rather
than retype it. The `capture_predrain_objective2_membership.py`/
`own_market_calibration.py` hash logic was replicated inline (SELECT + hash),
never executed as a full script, so no `data/characterizations/` artifact was
written and no `--persist` path was touched.
