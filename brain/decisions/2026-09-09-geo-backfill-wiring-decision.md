# 2026-09-09 — wiring `backfill_trade_results_geo.py` into daily maintenance: assessment + HALT

**Outcome: HALTED at Part 3 (wiring not performed).** Part 1 clears — the
script is safe. Part 2 does **not** clear: an unbounded run drains the entire
24,390-row `check_pending_geo` backlog to zero in a single pass. That trips
**STOP CONDITION 3** ("Part 2 shows it would clear the backlog in one run —
that is a drain, and a drain needs its own decision"). Per the task's own
halt instruction, `daily_maintenance.py` was **not modified**, nothing was
run against production except one read-only `--dry-run`, and no drain was
performed. This document is the assessment plus a recommended sequence for
Oscar.

Every claim is tagged **[V]** (verified this session, file:line or command
given) or **[I]** (inferred, marked). No production data was written.

Supersedes nothing; extends `2026-08-19-geo-backfill-wiring-prereg.md`
(`9fb436d`-era) with today's live numbers and a corrected step-order map
(the step list has grown since that doc).

---

## Part 1 — script assessment (`scripts/backfill_trade_results_geo.py`, full read)

### What it does / writes / to which columns

**[V]** `fetch_pending_trades()` (lines 45-68) selects trades where
`trade_result = 'pending' OR trade_result IS NULL`, joined to `markets`,
filtered to: `m.resolved = 1`, `m.winning_outcome IS NOT NULL AND NOT IN
('unknown','')`, `m.category IN ('Geopolitics','Elections')`, non-gap
(`trade_gap_flag = 0 OR IS NULL`), `t.timestamp <= datetime('now')`.
Optional `LIMIT :limit` (no `ORDER BY` — see caveats).

**[V]** For each row it calls `monitoring.trade_evaluator.TradeEvaluator
.evaluate_trade(trade, winning_outcome)` → returns `"won" | "lost" |
"invalid"`. That method (read in full, `monitoring/trade_evaluator.py:16-51`)
is a **pure function** of the trade dict + the `winning_outcome` string:
no DB handle, no network, no filesystem. The `TradeEvaluator(None, None)`
construction at line 34 is deliberate and safe.

**[V]** Writes, in order:
1. `UPDATE trades SET trade_result = ? WHERE trade_id = ?` — one row at a
   time (lines 103-106). Only column touched: `trades.trade_result`.
2. After all batches: `UPDATE traders SET geo_resolved_trades_count =
   (<cd.GEO_RESOLVED_TRADES_COUNT_SQL>) WHERE address IN (<N placeholders>)`
   (lines 117-122), one placeholder per distinct affected trader. Only
   column touched: `traders.geo_resolved_trades_count`. The recompute
   fragment is the canonical one from `monitoring/column_definitions.py:51`
   — the same fragment `audit_invariants.check_geo_recon` and
   `reconcile_geo_resolved_counts.py` use, so no writer-vs-checker
   divergence.

### Idempotent?

**[V] Yes, on both axes.**
- *Safe to run twice:* after a row is evaluated it holds
  `won`/`lost`/`invalid`, so it no longer matches `trade_result = 'pending'
  OR IS NULL`. A second run finds only what arrived since. `evaluate_trade`
  is deterministic given the same `(trade row, winning_outcome)`.
- *Safe to run daily:* it only ever touches pending/NULL rows; a
  correctly-evaluated `won`/`lost` is never revisited or flipped.
- *Crash-safe:* per-batch commit (1,000) + WAL means a mid-run crash loses
  at most one uncommitted batch; re-running resumes naturally via the same
  predicate.

### Batching / unbounded IN clauses

**[V] The trade writes are batched and safe.** `BATCH_SIZE = 1000` (line
27); `conn.commit()` after each batch (line 111); each `UPDATE` is a
single-row `WHERE trade_id = ?`. No `IN (...)` over trade IDs. This is
**not** the stranded-markets remediation pattern (that built large `IN`
lists of market IDs in the working path and was flagged unsafe for exactly
that) — confirmed by reading both.

**[V] One technically-unbounded IN clause exists, at the tail:** the single
`UPDATE traders ... WHERE address IN (<N placeholders>)` at line 121, N =
distinct affected traders. Today's dry-run: **N = 1,996** for the whole
backlog. SQLite here is **3.45.1** (`sqlite3 --version`), whose
`SQLITE_MAX_VARIABLE_NUMBER` default is 32,766, so 1,996 is comfortably
safe and a bounded `--limit` run is trivially safe (N ≤ limit). It would
only raise `too many SQL variables` above ~32k distinct traders in one run
— not reachable at any realistic limit, but recorded because it is the one
place the script does not bound its own input.

### `--limit`, and behaviour without one

**[V]** `--limit` exists (line 141, `type=int, default=None`). With no
limit the fetch returns **all** matching rows and processes them in
1,000-row batches with a commit between each. It is not one giant
transaction — but it is a **full one-pass drain** of whatever matches
(see Part 2). `--limit 0` is falsy and behaves as "no limit". There is
**no `ORDER BY`**, so a `--limit N` run takes an arbitrary N rows (SQLite
natural order ≈ rowid) — fine for a recurring top-up (it reaches all rows
across days), but there is no "oldest-first" guarantee.

### Has it ever been run?

**[V] Partially — interactively, ~June 2026, outcome unknown.**
`~/.bash_history` lines 57 and 434 both contain a bare
`python3 scripts/backfill_trade_results_geo.py` (no `--dry-run`, no
`--limit`); line 434 sits just above the line-450/451 commit of `093ee85`
(2026-06-22). So the command *was typed at least twice*, before the
2026-08-19 repoint (`8cfeb8e`) that swapped its local win/loss logic for
the canonical `TradeEvaluator`.
**[V] No output, exit status, or timestamp is recoverable** — `bash_history`
captures none of that, there is no `logs/geo_backfill_first_run.log` or any
other execution signature in any file under `logs/` (grep for its stdout
strings: no match), it is **not** in `crontab -l`, and **not** in any
systemd unit.
**[I]** `2026-08-19-pending-invariant-regression.md` Q4 independently shows
the backlog "sat undisturbed for well over a month" with `last_checked` in
early July — consistent with the June runs having happened and nothing
having touched this population since. The current backlog is therefore
"regrown / never-drained", not "never attempted".

Behaviour is nonetheless **established without a production write**: the
`--dry-run` path (lines 86-94) returns before any `cursor.execute` write —
verified by reading it — and ran cleanly this session (Part 2). The
evaluator itself has documented zero-disagreement convergence across
1,582,064 already-evaluated rows (`2026-08-19-trade-evaluator-convergence.md`).
**STOP CONDITION 2 is therefore not tripped** ("never executed AND
behaviour cannot be established without running against production" — the
second half is false).

### WAL / write-lock on the 20 GB DB

**[V]** `data/polymarket_tracker.db` is **20 GB** (`ls -lh`). The script
opens with `PRAGMA journal_mode=WAL` (already the DB's permanent mode) and
`PRAGMA busy_timeout=30000` (lines 39-40).
- The fetch is a **read**; under WAL it does not block the live monitor's
  writers.
- **Bounded `--limit 200` run:** ≤200 single-row UPDATEs + 1 batch commit +
  1 small `traders` UPDATE. Negligible WAL growth, one commit point.
- **Unbounded run:** ~24,390 UPDATEs across ~25 commit points; WAL grows
  between commits and is reclaimed by autocheckpoint / the maintenance
  WAL-checkpoint step. Each commit can contend with a monitor write lock
  for up to 30 s; single-row PK UPDATEs are sub-millisecond, so realistic
  added latency is seconds total, not hours — but ~25 contention points
  against a live writer is precisely why a full drain belongs in a
  detached, observed run (prereg §5), not inside maintenance.
- This session's `--dry-run` over the full 24,390 rows returned in well
  under the 600 s guard (near-instant after the fetch) with the live
  monitor running and unaffected.

### Affected by the stranded-markets `last_checked` defect?

**[V] Independent of it.** The script's query references
`trade_result`, `m.resolved`, `m.winning_outcome`, `m.category`,
`m.trade_gap_flag`, `t.timestamp` — and **not** `last_checked` anywhere.
It neither reads nor writes that column and shares no code path with the
stranded-markets remediation.

### Part 1 verdict: **CLEARS.**

Batched, has `--limit`, idempotent, deterministic evaluator, read-only
dry-run, no `last_checked` coupling. The lone caveat (unbounded tail
`IN` clause, safe to ~32k traders/run) does not rise to a stop condition.

---

## Part 2 — what it would actually clear (dry-run + query, no writes)

**[V]** `check_pending_geo` live count now (same predicate as
`audit_invariants.py:306-311`): **24,390**. (Task cited 24,644; prereg
cited 24,707 on 08-19. Normal live drift.)

**[V]** `python3 scripts/backfill_trade_results_geo.py --dry-run`:
```
Found 24390 pending trades to evaluate.
[DRY RUN] Would write: won=12376, lost=12014, invalid=0
[DRY RUN] Traders affected: 1996
```

| question | answer |
|---|---|
| rows it would evaluate | **24,390** — 100% of the `check_pending_geo` backlog |
| would resolve | **24,390** (12,376 won + 12,014 lost) |
| would leave pending | **0** |
| invalid | **0** |
| traders affected | **1,996** |

**[V] Why 0 remain:** the script's fetch predicate is a strict superset of
the audit's, adding `winning_outcome NOT IN (NULL,'unknown','')` and
`timestamp <= now`. A direct query for geo/elec pending rows on resolved
non-gap markets with an *unusable* `winning_outcome` returns **0**, and
`invalid = 0` from the dry-run confirms every row has a populated
`outcome_bet`/`outcome` and `side`. So right now there is no geo-pending
row the script cannot evaluate. (In general, rows that *could* survive a
run: geo/elec `resolved=1` markets whose `winning_outcome` is still
NULL/`unknown`/`''`, or trades stamped in the future — currently none.)

**[V] Provenance of the 24,390:** 14,424 (59.1%) `background_backfill`,
9,966 (40.9%) `polymarket_api`. (Prereg 08-19: 63.6% / 36.4%.) The
`background_backfill` share is the live, ongoing source — see Part 4.

### Shape: **one-run drain, not a daily top-up.**

An unbounded invocation clears the entire historical backlog in a single
pass. That is a large one-off operation with a different risk profile from
a bounded daily top-up:

- It is a **research-population change**, not hygiene. Prereg §4/§6
  established that clearing this backlog moves the Objective-2 OOS
  cohort/placebo measurements (it reaches 3 pre-split-cohort traders and
  **2 placebo *survivors***, per `2026-08-19-pending-invariant-regression.md`
  Q6). The result of record will not reproduce identically afterward. That
  shift must be measured before/after **deliberately** (prereg §4 lists the
  six characterization re-runs), not absorbed silently.
- The burst-load history on this system (backup-vs-sweep starvation) is the
  stated reason a drain "needs its own batching and timing — a decision for
  Oscar."

**→ STOP CONDITION 3 is met. Wiring was not performed. The drain was not
run.**

### If it were wired at `--limit 200` anyway (why that is still wrong *now*)

A `--limit 200` daily step, run while the 24,390 historical rows are still
pending, evaluates ~20 new arrivals + ~180 historical rows per day — i.e.
it **drains the historical backlog as an unsupervised side effect** over
~120–135 days, moving the same cohort/placebo blast radius as the one-shot
drain but spread thin enough that nobody runs the prereg §4 verification.
And it changes nothing operator-visible in the meantime: the step-7 audit
still reads a 24k+ backlog for months, so the one surviving Telegram alert
keeps firing. A bounded daily step is only coherent **after** the backlog
is at ~0.

---

## Part 3 — wiring: NOT DONE. Recommended sequence for Oscar.

`daily_maintenance.py` is **unchanged**. No test was added (the test task
is downstream of "Parts 1 and 2 clear"; Part 2 did not).

### Recommended sequence

1. **Drain first, deliberately** (Oscar's call): `backup_database.py`
   (WAL-safe online backup + integrity check) → `--dry-run`, compare to
   §4 predictions → `nohup python3 scripts/backfill_trade_results_geo.py >
   logs/geo_backfill_first_run.log 2>&1 & disown` (detached, observed) →
   run the prereg §6 non-tautological verification (invariant count must
   move by ~the dry-run total; the 92-population must not grow; the
   161-population must stay exactly unchanged; dry-run vs live
   traders-affected must match). The `--limit` flag also lets the drain be
   sharded across a few supervised runs (e.g. `--limit 5000` ×5) if a
   single ~24k pass is judged too much contention against the live writer.
2. **Then wire the daily top-up**, once the backlog is at ~0.

### Recommended step placement (unchanged in intent from prereg §1; step
### numbers re-derived against today's `STEPS` list)

Insert a new entry **immediately after** `("Evaluate new trader results",
SCRIPTS_DIR / "evaluate_new_trader_results.py", None, True)`
(`daily_maintenance.py:166`) and **immediately before** `("Reconcile geo
resolved counts [post-eval]", …)` (`:171`). In today's list that is step 21
→ new step 22, everything after shifts down one (base list currently 29
steps; `build_steps(6)` appends the two Sunday steps after).

```python
    ("Evaluate new trader results",        SCRIPTS_DIR / "evaluate_new_trader_results.py", None, True),
    # All-geo/elec pending-result evaluator — the non-flagged counterpart to the
    # step above (which only touches is_flagged=1 traders). Closes the standing
    # gap root-caused in 2026-08-19-pending-invariant-regression.md Q4: no daily
    # evaluator existed for the check_pending_geo population. --limit 200 is a
    # top-up, NOT a drain — the historical backlog was cleared separately
    # (see 2026-09-09-geo-backfill-wiring-decision.md). Non-blocking: settlement
    # pass, not a gate. Batched at 1000/commit; default 3h budget is ample.
    ("Evaluate geo/elec pending results (all traders)", SCRIPTS_DIR / "backfill_trade_results_geo.py", ["--limit", "200"], True),
    # Settles geo counts after post-audit evaluation. …
    ("Reconcile geo resolved counts [post-eval]",  SCRIPTS_DIR / "reconcile_geo_resolved_counts.py", None, True),
```

**Why here:**

- **After the step-7 audit gate** (`audit_invariants.py --alert`) — so
  `check_pending_geo` keeps reading the *true* backlog. A remediation step
  before the gate produces a green check that proves only that the
  remediation ran, not that the population is healthy (the exact failure
  mode the gate-before-remediate ordering exists to prevent). This does
  reproduce the `check_pending_flagged` sawtooth for `check_pending_geo`
  (see Part 4) — accepted, documented, unavoidable given requirement #1.
- **Immediately before "Reconcile geo resolved counts [post-eval]"** —
  that reconcile already exists to settle `geo_resolved_trades_count` after
  step 21's writes, using the same `cd.GEO_RESOLVED_TRADES_COUNT_SQL` this
  script's own tail update uses. Placing the new step just before it means
  one settlement point covers both evaluators; appending at the end of the
  run instead would leave `geo_resolved_trades_count` stale for ~1,996
  traders until the *next* day's step-6 reconcile.
- **Adjacent to "Evaluate new trader results"** — that script is the
  `is_flagged=1` pending-result evaluator (`evaluate_new_trader_results.py`
  docstring: "Targets: is_flagged=1, research_excluded=0,
  trade_result='pending', … resolved=1 …"). The new step is the *same
  operation* for the complementary population — every geo/elec trader
  regardless of `is_flagged`. A reader expects the two pending-evaluators
  side by side.
- **After the resolution-producing steps** — step 16
  `fast_resolution_check.py` and step 20 `resolve_legendary_markets.py`
  both land newly-resolved markets earlier in the same run, so their
  `winning_outcome`s are already present and the new step evaluates
  same-day resolutions rather than waiting 24h.
- **`non_blocking=True`** (4-tuple `(label, path, args, True)`) — a DB
  lock, evaluator exception, or timeout logs a WARNING and the run
  continues. It is a settlement pass; the morning's `reconcile #1`
  (step 6) is the real gate. Matches the flag on its neighbours (steps
  21 and 22 are both non-blocking).
- **No explicit timeout** — inherits `DEFAULT_STEP_TIMEOUT = 10800` (3h).
  A `--limit 200` run is sub-minute (this session's dry-run over 122×
  that many rows was near-instant post-fetch). No override needed;
  matches unbudgeted neighbours.

### `--limit 200` — the number

- Mean arrival ≈ **20/day** (~600/month, task figure; the prereg's
  trade-timestamp-only basis gave ~2/day but explicitly undercounts the
  `background_backfill` channel — 59% of the backlog, and 106 new traders
  seen in one 24 h window).
- **200 ≈ 10× the mean.** It absorbs (a) a multi-day maintenance outage
  (this box's crash history; the late-July/early-August gap was ~2 weeks)
  and (b) a `background_backfill` burst day, without unbounded growth.
- **200 is not a drain at any scale:** pointed at a 24k backlog it needs
  ~120 daily runs to clear it — categorically a top-up. Post-drain, with
  ~20/day arriving, it never approaches the cap.
- Runtime and lock cost at 200 rows are negligible (Part 1).
- If Oscar wants **zero** incidental erosion of the historical population
  before the deliberate drain, set `--limit 25–30` (≈ arrival rate, holds
  the line only). Not recommended as the steady state — it has no
  outage-catch-up headroom.

### Test (recommended, not added)

Follow `tests/test_weekly_full_sync_gate.py` exactly (the existing
step-registration test pattern — it inspects `dm.build_steps(weekday)` /
`dm.STEPS` and asserts label / script `.name` / `extra_args` /
`non_blocking`). New file `tests/test_geo_backfill_step_registered.py`
asserting, for a non-Sunday weekday: the
`"Evaluate geo/elec pending results (all traders)"` step is present, its
script is `backfill_trade_results_geo.py`, `extra_args == ["--limit","200"]`,
`non_blocking is True`, and it sits at an index between
`"Evaluate new trader results"` and
`"Reconcile geo resolved counts [post-eval]"`. Run via `python3 run_tests.py`
(not bare pytest). **Not written this session** — gated on the wiring,
which is halted.

---

## Part 4 — what this does NOT fix (for the record)

### `background_backfill_worker.py` hardcoded `trade_result='pending'` at ingest — NOT fixed

**[V]** `monitoring/background_backfill_worker.py:304-312`:
`INSERT OR IGNORE INTO trades (… trade_result, data_source) VALUES
(…, 'pending', 'background_backfill')` — `trade_result` is the literal
`'pending'`; `market_category` is the literal `'Unknown'`. Trades are never
evaluated at ingest. This is **59.1% of the current backlog** and is the
live mechanism that keeps refilling `check_pending_geo`. Wiring the daily
evaluator treats this symptom once a day; the ingest path keeps creating it.

**Fixing it at ingest is feasible — propose only, not implemented** (scope:
"Do NOT modify background_backfill_worker.py"):
- At insert the worker has `conditionId`. It could look up
  `markets.resolved` / `markets.winning_outcome` / `markets.category` for
  that id (one indexed SELECT per distinct market per batch, cached), and
  if the market is resolved with a usable outcome, call the **pure**
  `TradeEvaluator.evaluate_trade(trade_dict, winning_outcome)` (import only
  — no new deps, no API client) and insert the real `won`/`lost` instead of
  `'pending'`. ~20–40 lines + a test.
- It is an **optimisation, not a replacement**: the market may not be in
  `markets` yet (the worker also inserts stub markets), or may resolve
  *after* the trade is ingested. Those cases still land as `'pending'` and
  still need the daily evaluator. So the daily step is required regardless;
  the ingest fix would just shrink the daily step's load and the
  audit-time sawtooth amplitude.
- Owner decision: worth doing, separately, after the drain + daily step are
  in and the residual daily inflow is measured.

### Does the invariant's floor of 0 become achievable? — NO, it stays aspirational

**[V]** With the evaluator at step 22 and `audit_invariants.py` at step 7,
every morning's audit reads a full day of arrivals accumulated since the
*previous* run of step 22 — the identical sawtooth already documented for
`check_pending_flagged`, which Oscar accepted on 2026-09-09 in
`config/accepted_failures.json` as *"a within-cycle backlog gauge, not a
zero-floor invariant … oscillates … returns to 0 on many days."*
`FLOOR_PENDING_GEO = 0` (`audit_invariants.py:78`, comment "stays 0 as long
as daily evaluation keeps pace") is structurally unreachable while any
geo-pending trade can arrive between step 22 and the next step 7.

What *does* change once the drain + daily top-up are in place:
`check_pending_geo` stops sitting at 24k-and-growing and instead
oscillates ~0 to low-hundreds with no trend — the same shape as
`check_pending_flagged`.

**Register status:** there is currently **no** `accepted_failures.json`
entry for `audit_invariants::pending on resolved non-gap geo/elections
markets` (only the *flagged* sibling, `review_by` 2026-12-01). So there is
nothing to "review sooner" yet. **Recommendation (Oscar's call, not done
here — scope forbids touching the floor or the register):** once the drain
lands and ~2 weeks of post-clearance daily readings exist, decide whether
`check_pending_geo` gets the same disposition as `check_pending_flagged` —
a register entry describing it as a within-cycle gauge, or moving the audit
step after step 22, or changing the floor semantics. Until then it
correctly keeps alerting, because today it genuinely is 24k over floor with
an upward trend.

---

## What was NOT determined

- **Outcome of the ~June 2026 interactive runs** (`bash_history` 57, 434):
  no logs, no exit status, no timestamps; and they predate the 2026-08-19
  evaluator repoint, so even a known-good outcome then would not fully
  characterise today's code. Established instead via the read-only dry-run
  + the evaluator's separate convergence testing.
- **True steady-state daily arrival rate.** 20/day is an estimate from the
  ~600/month figure. The `background_backfill` channel (59% of the backlog)
  has never been measured as a per-day geo-pending inflow. Only a real
  post-drain week of daily readings will pin it — at which point `--limit
  200` should be re-checked against observed peak days.
- **won/lost split stability.** 12,376 / 12,014 / 0 is one point-in-time
  dry-run; a later live run's split will differ slightly as trading
  continues and more markets resolve.
- **Live write-lock contention under real load.** The dry-run performed no
  writes; a bounded write run's actual contention with the 15-minute
  monitor has not been observed.
- **Blast radius on the Objective-2 OOS cohort/placebo populations** from
  clearing these 24,390 rows. Prereg §4/§6 lists the six measurements to
  take; none were re-run here. This is part of why the drain is Oscar's
  decision, not a maintenance-step side effect.
- **Whether any `--limit N` run's arbitrary row selection (no `ORDER BY`)
  ever systematically strands a subset** across many daily runs. Unlikely
  (SQLite natural order drifts as rows are updated out of the set), but not
  proven.

### Side observation (not in scope, not acted on)

`scripts/compare_trade_evaluators.py:35` does `from
scripts.backfill_trade_results_geo import evaluate_trade` — a symbol the
2026-08-19 repoint (`8cfeb8e`) **removed**. That helper script now fails at
import. Flagging only.

---

*Generated 2026-09-09. Sources: `scripts/backfill_trade_results_geo.py`
(full read), `monitoring/trade_evaluator.py` (full read),
`monitoring/column_definitions.py:51`,
`monitoring/background_backfill_worker.py:290-320`,
`scripts/daily_maintenance.py` (STEPS list :132-179, run loop),
`scripts/evaluate_new_trader_results.py:1-60`,
`scripts/audit_invariants.py:66-79,300-324`, `config/accepted_failures.json`,
`tests/test_weekly_full_sync_gate.py`, `~/.bash_history`, `crontab -l`,
`sqlite3 --version`, live read-only queries + one `--dry-run` against
`data/polymarket_tracker.db` (20 GB). `2026-08-19-geo-backfill-wiring-prereg.md`,
`2026-08-19-pending-invariant-regression.md`,
`2026-08-19-trade-evaluator-convergence.md`,
`2026-09-09-final-telegram-cut.md`. No code changed; no production write.*
