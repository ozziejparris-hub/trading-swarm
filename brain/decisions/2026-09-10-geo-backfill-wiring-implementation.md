# 2026-09-10 — wiring `backfill_trade_results_geo.py` into daily maintenance: IMPLEMENTED

**Outcome: DONE.** The daily geo/elec pending-result evaluator is now a
registered step in `scripts/daily_maintenance.py`, at `--limit 1000`
(not the assessment's proposed `--limit 200` — see §1 for why). This is
the final part of the three-part plan:

| part | what | commit |
|---|---|---|
| 1 | ingest fix (evaluate backfilled trades at ingest, not hard-`'pending'`) | first-repo `7ae0f2a` |
| 2/3 | pre-drain baseline capture + the 24,390-row historical drain | first-repo `eee49ee` |
| **4 (this doc)** | **wire the daily top-up evaluator** | first-repo `<this commit>` |

Assessment (`2026-09-09-geo-backfill-wiring-decision.md`, `28d898b`) was
**not** redone. Its one open question — "is `--limit 200` right, given
this morning's `check_pending_geo = 460`?" — is answered here from
one cycle of real post-drain data.

Every number below is **[V]** verified this session (command/query given)
or **[I]** inferred. One bounded production write was made: the manual
verification run (§3), `--limit 1000`, 460 rows, idempotent evaluator.

---

## 1. Arrival-rate finding — why `--limit 1000`, not `200`

### The `--limit 200` in the assessment was sized against a stale estimate

The assessment (§"`--limit 200` — the number") sized 200 as "≈ 10× the
~20/day mean arrival". That ~20/day came from the 08-19 prereg's
trade-timestamp basis, which the assessment itself flags as an
undercount of the `background_backfill` channel. This morning's
`check_pending_geo` read **460, ~19 h after the drain took it to 0** —
1.5–2 orders of magnitude above 20/day. That reading had to be
explained before committing to any limit.

### What the 460 actually are  **[V]**

`check_pending_geo` predicate (`audit_invariants.py:305-311`): pending
`trade_result` on `resolved=1`, non-gap, `category IN
('Geopolitics','Elections')` trades.

Cross-referenced every one of the 460 pending `trade_id`s against the
pre-drain manifest (`predrain_geo_drain_manifest_20260909T200756Z.json`,
24,390 rows, captured 2026-09-09 20:07):

| | rows |
|---|---|
| already in the pre-drain manifest (drain missed / re-surfaced) | **0** |
| NOT in the manifest (genuine post-drain arrivals) | **460** |

**The drain was clean — nothing re-surfaced.** All 460 are trades that
entered the predicate *after* 2026-09-09 20:07. Composition:

| parent-market resolution date | markets | pending rows | nature |
|---|---|---|---|
| 2026-09-08 … 2026-09-10 | 23 | **~250** | genuinely newly-resolved markets (06:00 `fast_resolution_check`) |
| 2026-02-18 (one market: "US strikes Iran by January 31, 2026?") | 1 | **182** | old market, `winning_outcome='No'` + `category='Geopolitics'` since Feb; trades (re-)ingested as `'pending'` after the drain |
| 2026-03-09 / 2026-04-04 / 2 singles | 4 | ~28 | same pattern — old resolved markets, historical trades re-ingested pending |

By `data_source`: **289 `background_backfill`, 171 `polymarket_api`.**

So the 460 decompose into:

- **~250 / cycle structural** — pending trades on markets that resolved
  in the last day or two. Recurs every maintenance cycle; magnitude
  scales with how many geo/elec markets resolve in a 24 h window
  (election clusters and post-outage resolution catch-up push it up).
- **~210 / cycle episodic lump** — historical trades on long-resolved
  markets, (re-)inserted with `trade_result='pending'` by
  `background_backfill_worker.py` (the hardcoded-`'pending'` ingest path
  that Part 4 of the assessment flagged as unfixed; 7ae0f2a did not
  fully close it). 182 of the 210 are a single market. Bursty, not a
  steady trickle — depends on which backfill targets the worker
  happens to touch.

### Is 460 a one-off or the daily rate?

**Neither cleanly, and one cycle cannot tell us.** The 460 is exactly
**one maintenance cycle's accumulation** (nothing clears
`check_pending_geo` between 06:00 runs, so 19 h post-drain ≈ one cycle).
The ~250 structural component is one sample; the ~210 lump is bursty.
**The true steady-state rate is not establishable from a single day.**

### The sizing call

- **200 is too small.** Against this one observed cycle it would clear
  200 and leave ~260 to carry into the next day — the backlog *grows*.
  Even against only the ~250 structural component it barely treads
  water with zero outage headroom.
- **There is no historical backlog left to erode** (drain cleared it;
  0 of 460 re-surfaced). A limit that clears a full cycle's arrivals
  plus margin therefore settles `check_pending_geo` toward ~0 each
  morning and then finds only that day's arrivals — it is a **top-up**,
  and cannot "drain a research population" because there is no residual
  population to drain (manifest-verified).
- **`--limit 1000`** is the chosen size:
  - `= BATCH_SIZE` (`backfill_trade_results_geo.py:27`), so a full run
    is exactly one batch → one commit point + one `traders` update.
    The assessment's negligible-runtime/lock analysis (done for 200)
    scales linearly; §3 measured the real run at **13.6 s**.
  - Clears the observed ~460/cycle with ~2× headroom — absorbs a
    resolution cluster, a `background_backfill` burst, or a ~2-day
    maintenance gap (this box's crash history is why that headroom
    matters) without the backlog carrying over.
  - Still unambiguously a top-up: pointed at the *old* 24,390 backlog
    it would have needed ~25 daily runs — but that backlog is gone, so
    in practice it reaches steady state at ~0.
  - It is a **ceiling, not a target**: the script can only ever touch
    genuine current pending arrivals (gap-flagged markets are excluded
    by the predicate). §3's run passed `--limit 1000` and evaluated
    460 — the cap was not reached.

**Not sized to drain anything; sized to hold steady with real margin,
pending a week of readings (§5).**

---

## 2. What was added, and where  **[V]**

`scripts/daily_maintenance.py`, `STEPS` list — one new 4-tuple inserted
**immediately after** `("Evaluate new trader results", …
evaluate_new_trader_results.py, None, True)` and **immediately before**
the existing `("Reconcile geo resolved counts [post-eval]", …)`:

```python
("Evaluate geo/elec pending results (all traders)",
 SCRIPTS_DIR / "backfill_trade_results_geo.py",
 ["--limit", "1000"],
 True)   # non-blocking
```

- **label:** `Evaluate geo/elec pending results (all traders)`
- **script:** `scripts/backfill_trade_results_geo.py` (unchanged — not
  touched)
- **args:** `["--limit", "1000"]`
- **non_blocking:** `True` (4-tuple; a lock, evaluator exception, or
  timeout logs a WARNING and the run continues — it is a settlement
  pass, the morning's step-6 `reconcile #1` is the real gate)
- **timeout:** none specified → inherits `DEFAULT_STEP_TIMEOUT` (3 h),
  matching its unbudgeted neighbours
- **position:** base daily step (in `STEPS`, not appended by
  `build_steps(6)`), so it runs every weekday including Sunday

**Placement rationale** (unchanged from the assessment's Part 3):
after the step-7 `audit_invariants --alert` gate so `check_pending_geo`
keeps reading the true backlog each morning; immediately before the
post-eval reconcile so one `cd.GEO_RESOLVED_TRADES_COUNT_SQL`
settlement point covers both this evaluator's and
`evaluate_new_trader_results.py`'s `geo_resolved_trades_count` writes;
adjacent to `evaluate_new_trader_results.py` (its `is_flagged=1`
counterpart); after the resolution-producing steps 16
(`fast_resolution_check`) and 20 (`resolve_legendary_markets`) so
same-day resolutions are caught.

**No other step's label, script, args, order, or flags were changed.**
Diff is the new comment block + the one tuple. Confirmed by reading the
edited region (`daily_maintenance.py:166-186`).

### New test — `tests/test_geo_backfill_step_registered.py`  **[V]**

Follows `tests/test_weekly_full_sync_gate.py` exactly (inspects
`dm.build_steps(weekday)` / `dm.STEPS`; no subprocess, no DB). 16
assertions, all pass:

- T1 step present on a normal weekday
- T2 script is `backfill_trade_results_geo.py`
- T3 `extra_args == ["--limit", "1000"]`
- T4 `non_blocking is True`
- T5a-d ordered strictly between, and immediately adjacent to, both
  `"Evaluate new trader results"` and
  `"Reconcile geo resolved counts [post-eval]"`
- T6 present on every weekday 0-6 (base step, not weekly-gated)
- T7 appears exactly once

`run_tests.py` picks it up automatically (`tests/test_*.py` glob),
taking the suite from 24 files to 25.

---

## 3. Verification results  **[V]**

### Manual run — `python3 scripts/backfill_trade_results_geo.py --limit 1000`

| | |
|---|---|
| rows fetched / evaluated | **460** (cap 1000 not reached) |
| won | **243** |
| lost | **217** |
| **invalid** | **0** ✓ |
| traders updated (`geo_resolved_trades_count`) | 160 |
| elapsed | **13.6 s** (1 batch commit + 1 `traders` update) |
| `check_pending_geo` before → after | **460 → 0** |

### Lock contention / monitor heartbeat

- Run window 15:58:29–15:58:43 UTC. `pnl_worker` "Batch start" lines
  continued at their normal ~15 s cadence straight through
  (…15:58:13, 15:58:28, 15:58:44…) — **no gap**.
- `[WATCHDOG] Heartbeat — monitor alive` fired at 15:55:36 (before) and
  **16:00:49 (after)** — unbroken.
- No `database is locked` / `busy` / `OperationalError` in
  `polymarket-monitoring` logs over the window. **No contention.**

### Result of record unchanged

`sqlite3 data/polymarket_tracker.db "SELECT * FROM metric_v2f_oos_result" | sha256sum`
= **`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`**
— identical before and after the run. `backfill_trade_results_geo.py`
writes only `trades.trade_result` and `traders.geo_resolved_trades_count`;
`metric_v2f_oos_result` is not in its path.

### Backup

No new backup taken for the manual run: the automated
`database-backup` cron produced a clean, integrity-checked 20 GB
snapshot **today at 03:03 UTC**
(`data/backups/polymarket_tracker_2026-09-10.db`), before any of this
session's writes, and the run is a bounded idempotent evaluator pass
(the assessment's Part 1 establishes it is crash-safe and re-runnable).

### `run_tests.py`

**25 files run, 25 passed, 0 failed** (339,909 assertions).
`test_geo_backfill_step_registered.py` — 16/16 PASS.
`test_weekly_full_sync_gate.py` (the pattern this test follows) still
25/25. No pre-existing test regressed. The maintenance banner's
"Run test suite" step, which failed 09-08/09-09 and first passed
09-10, still passes with the new file added.

---

## 4. Expected steady state — for the record

Once this step runs nightly, **on a typical morning
`check_pending_geo` (the step-7 audit reading, and the one remaining
Telegram alert's subject) should read a few hundred and trend nowhere**
— it is a within-cycle backlog gauge, identical in shape to
`check_pending_flagged`:

- **Normal:** ~0 immediately after step 22 each night; climbs back to
  low-hundreds by the next 06:00 audit as new markets resolve and
  `background_backfill` re-ingests historical rows. A morning reading of
  **roughly 100–600, with no multi-day upward trend**, is healthy.
- **A problem** is: a sustained climb across several mornings (e.g.
  >1,000 and rising) — that means arrivals now exceed `--limit 1000`
  per cycle and the step can no longer keep pace; **or** the step
  showing `FAILED`/`WARNING` in the maintenance banner for consecutive
  days (evaluator erroring, or lock timeouts); **or** `invalid > 0` on
  a real run (markets resolving with an unusable `winning_outcome`).
- The `won`/`lost` split will drift run to run; it is not a health
  signal.

### Does the audit invariant's floor of 0 become achievable? — **NO, still aspirational.**

`FLOOR_PENDING_GEO = 0` (`audit_invariants.py:78`) stays structurally
unreachable. The evaluator is **step 22**; the audit is **step 7**.
Every morning's audit reads a full day of arrivals accumulated since
the *previous* night's step 22, before this step clears them. That
step-7-reads / step-22-clears **sawtooth is structural** — the same one
Oscar already accepted for `check_pending_flagged` on 2026-09-09
("a within-cycle backlog gauge, not a zero-floor invariant … returns to
0 on many days"). What changed today is only that `check_pending_geo`
now *has* an evaluator behind it, so it oscillates ~0→few-hundred
instead of sitting at 24k-and-growing.

**Not touched here (scope):** the `FLOOR_PENDING_GEO` value, and the
absence of an `accepted_failures.json` entry for
`audit_invariants::pending on resolved non-gap geo/elections markets`.
Recommendation stands from the assessment: after ~2 weeks of
post-wiring readings, Oscar decides whether `check_pending_geo` gets the
same register disposition as its flagged sibling, or the audit step
moves after step 22. Until then it correctly keeps alerting on genuine
growth.

---

## 5. What was NOT determined

- **True steady-state daily arrival rate.** One post-drain cycle
  (460 rows: ~250 structural + ~210 one-market re-ingestion lump) is
  not enough to fix a mean or a peak. `--limit 1000` was sized to hold
  steady with ~2× headroom over this single reading, **not** from a
  distribution. **Revisit after ~1 week of nightly readings**: pull the
  per-run "Found N pending trades" line from `daily_maintenance.log`
  and the each-morning `check_pending_geo`; if runs regularly exceed
  ~700 or the morning gauge trends up, raise the limit (or fix the
  ingest path — next bullet). If they sit well under, 1000 is harmless
  (it just fetches fewer rows).
- **Whether the ~210-row historical-re-ingestion lump recurs.** It is
  driven by `background_backfill_worker.py` inserting historical trades
  on already-resolved markets as `'pending'`. It may have been a
  one-off catch-up on 2026-09-10, or it may recur whenever the worker
  touches an old geo market. `7ae0f2a` was meant to evaluate at ingest
  but 289/460 arrivals were still `background_backfill` — **the ingest
  path is not fully closed.** Not investigated here (scope: do not
  modify `background_backfill_worker.py`). If the lump recurs weekly,
  the ingest fix is the real remedy and the daily step's limit
  shouldn't be inflated to compensate.
- **`won`/`lost` split stability** — 243/217 this run; will vary.
- **Behaviour under a genuinely large arrival day** (>1000 in one
  cycle). The step would clear 1000 and leave the remainder for the
  next night; no run at that scale has been observed.
- **Interaction with a same-night `background_backfill` burst mid-run**
  — the step reads its pending set once at the top; rows the worker
  inserts during the ~14 s run are picked up the next night, not this
  one. Not a correctness issue (idempotent), just latency.

---

## 6. Scope adherence

- No unbounded drain run — the one production write was `--limit 1000`,
  which fetched 460.
- `backfill_trade_results_geo.py` — **not modified.**
- `background_backfill_worker.py` — **not modified.**
- `audit_invariants.py` `FLOOR_PENDING_GEO` and register entries —
  **not touched.**
- Canonical-drift check's residual violation
  (`characterize_legendary_overlap_recompute.py`) — **not touched.**
- No STOP condition tripped: arrival rate was characterisable well
  enough to size a hold-steady limit; the manual run showed
  `invalid=0`, no lock contention, unbroken heartbeat; the edit adds a
  step without altering any existing one.

---

*Generated 2026-09-10. Sources: `scripts/daily_maintenance.py` (edited
region), `scripts/backfill_trade_results_geo.py` (full read),
`scripts/audit_invariants.py:60-82,300-324`,
`tests/test_weekly_full_sync_gate.py`,
`tests/test_geo_backfill_step_registered.py` (new),
`data/characterizations/predrain_geo_drain_manifest_20260909T200756Z.json`,
live read-only queries + one `--limit 1000` run against
`data/polymarket_tracker.db`, `polymarket-monitoring` journal.
Extends `2026-09-09-geo-backfill-wiring-decision.md` (`28d898b`).*
