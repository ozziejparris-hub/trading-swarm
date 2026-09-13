# Auditing daily_maintenance.py

Read-only. First whole-pipeline audit of the project's central scheduled
process — 30 weekday / 32 Sunday steps, 2-10+ hours daily, calling most
of `scripts/`. No fixes, no wiring, no restarts, no writes to any
production table. `metric_v2f_oos_result` sha256 checked throughout:
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` —
unchanged.

**No step triggers the literal stop condition** ("a re-run would
corrupt or double-count"). **The 2026-09-12 crash left no inconsistent
state** — established directly, not assumed; see Part 1. One real,
distinct bug was found that is NOT corruption or double-counting but
IS a permanent, self-reinforcing completeness gap unrelated to any
crash — `backfill_market_categories.py` (Part 2) — flagged prominently
below because it is the single most concrete "will not self-correct"
finding in this audit, even though it falls outside the stop
condition's specific wording.

---

## Part 1 — what the 09-12 crash left behind

**Verdict: nothing is inconsistent. This is the good outcome, established
directly.**

The run died at `[3527/4482]` inside step 12, **"Backfill transaction
hashes"** (`scripts/backfill_transaction_hashes.py --tier pool_c`,
28,800s/8h budget) — confirmed by locating the exact crash-point line in
`logs/daily_maintenance.log` and cross-referencing the script that emits
`fetched=... matched=... Updated=...` in that format. This step
backfills `trades.transaction_hash` for Pool C (`geo_accuracy_pool = 1`)
traders, fetching each trader's recent trades from the Polymarket Data
API and matching them against DB rows missing a hash.

**Commit granularity: per-row, immediately.** Reading the script
directly (`backfill_transaction_hashes.py:158-165`): every single
matched trade gets its own `UPDATE ... SET transaction_hash = ?` followed
immediately by `db_conn.commit()`, inside the per-trader loop. There is
no batching and no end-of-run transaction — each write is durable
(WAL mode) the instant it happens.

**Idempotent by construction.** The matching query
(`backfill_transaction_hashes.py:138-148`) is gated
`AND (transaction_hash IS NULL OR transaction_hash = '')` — a trade that
already has a hash can never be matched or re-written again. Re-running
the exact same 4,482-trader list from trader #1, as happens every day
regardless of the previous day's outcome (see below), is safe: traders
1-3526 (already hashed and committed on 09-12) simply produce zero new
matches on 09-13; traders 3527-4482 (never reached before the crash) get
processed for the first time.

**No persisted cursor — the whole trader list is re-fetched from
`geo_accuracy_pool = 1` at the start of every run**, with no
checkpoint file anywhere in the script. This means the ~955 traders
never reached on 09-12 were **not** "resumed" in any deliberate sense —
they were simply reprocessed along with everyone else when the entire
step ran again from #1 on 09-13, exactly as it does every day. The
mechanism that made this safe is the idempotent WHERE-clause, not any
resume logic — there is none.

**Confirmed: nothing is currently inconsistent as a result of the
crash.** Every row committed before 07:58 UTC on 09-12 remains correctly
persisted; every trader never reached got a normal processing
opportunity on 09-13 (and would on any subsequent day, for as long as
they remain in Pool C).

**One honest caveat, not a finding of inconsistency**: the Data API this
script calls "returns recent trades only (~last few days)," per its own
docstring. A trade made by one of the 955 delayed traders in the narrow
window between roughly 09-11 and 09-12 could theoretically have aged out
of the API's retention window by the time 09-13's run reached that
trader, permanently missing its one-time hash-capture opportunity. Given
the daily cadence (~24h) is small relative to the stated retention
(~3-7 days), this is very unlikely to have mattered in practice, and no
evidence of it was sought or found — named for completeness, not as a
confirmed gap.

---

## Part 2 — resumability across all steps

**Process-level resume mechanism: none. Confirmed by reading the code,
not just citing the 09-12 evidence.** `daily_maintenance.py`'s `main()`
always calls `build_steps(weekday)` and iterates from step 1 — no
`--resume` flag, no step-number marker file, no read of any prior run's
exit point anywhere in the file. The only "resume"-adjacent text in the
file is an unrelated comment about a different, already-closed sweep
project. **No document states a process-level resume was ever a design
intent** — the closest related text (a sweep-checkpoint-recency comment
block, lines 20-45) explains why a lock/sentinel file was rejected for a
*different* concern (a separate sweep process holding "Backfill market
dates"), reasoning that "a bare lock does not survive this box's crash
history" — that reasoning is about a different mechanism for a
different purpose, not a rejected daily_maintenance-level resume design.

**Full per-step table** (idempotency verified against each script's own
write logic, not inferred from log behavior):

| Step | Writes | Commit granularity | Idempotent | Checkpoint | Mid-kill consequence |
|---|---|---|---|---|---|
| Update research exclusions | `traders` exclusion flags | 4 commits | Yes — recomputed fresh each run | No | Self-correcting |
| Sync trade categories | `markets`/`trades` category sync | 1 commit | Yes — own comment confirms WHERE-gated | No | None |
| Detect ARB_BOT patterns | `traders.bot_type` | not fully verified | Yes (flag recompute) | No | Low |
| Promote high-P&L traders | `traders.is_flagged` | 1 commit | Yes | No | Low |
| Resolution sweep | `INSERT ... ON CONFLICT DO NOTHING`, `traders` | per-50-row batch | **Yes, explicit conflict-safe** | No | ≤49 rows delayed, no duplicates possible |
| Reconcile geo resolved counts (×2) | `traders.geo_resolved_trades_count` | 1 commit | Yes — canonical recompute | No | None |
| Integrity audit (pre-ELO gate) | none (read-only gate) | N/A | N/A | No | None |
| Canonical definitions drift | none (read-only gate) | N/A | N/A | No | None |
| Update geo ELO scores | `traders.geo_elo*` | not conclusively resolved (no explicit `.commit()` string found) | Yes — recompute-and-set | No | Low |
| Score insider signals | `UPDATE`s existing `insider_signals` rows only, no INSERT | 2 commits | Yes | No | None; also structurally moot — writer stale 4+ months (cross-ref Part 4) |
| Score STR-003 signals | STR-003 scoring fields | not fully verified | Presumed yes | No | Low |
| **Backfill transaction hashes** | `trades.transaction_hash` | **per-row, immediate** | **Yes** — WHERE-gated | No | **None — the 09-12 crash step, see Part 1** |
| Label maker/taker roles | `trades.is_taker` | 2 commits | Yes — by trade_id | No | Low |
| Verify market titles | `markets.title` | 1 commit | Yes — overwrite | No | None |
| **Backfill market categories** | `markets.category`, `trades.market_category` | per-batch transaction; checkpoint written **after** commit | **Partially — see prominent flag below** | Yes, but its own arithmetic is wrong for a shrinking result set | **Permanent skip-drift on any mixed batch, independent of crashes** |
| Fetch new market resolutions | `markets.resolved`/fields | 5 commits | Yes — idempotently re-derived | No | Low |
| Register STR-002 signals | `INSERT OR IGNORE INTO str002_signals` | 2 commits | **Yes, explicit** — own docstring | No | None |
| Enrich STR-002 metadata | `str002_signals` fields | 2 commits | Presumed yes | No | Low |
| Score STR-002 signals | `str002_signals` fields | 1 commit | Presumed yes | No | Low |
| Resolve LEGENDARY trader markets | LEGENDARY resolution fields | 1 commit | Presumed yes | No | Low |
| Evaluate new trader results | `trades.trade_result` | 1 commit | **Yes** — `WHERE trade_result='pending'` | No | None |
| Evaluate geo/elec pending results | `trades.trade_result`, `traders.geo_resolved_trades_count` | batched | **Yes** — same pending-guard pattern | No | None |
| Reconcile geo resolved counts [post-eval] | same | same | Yes | No | None |
| Requeue resolved market traders | `traders` requeue fields | 1 commit | Yes — `last_checked`-gated | No | Low |
| Apply full ELO modifiers | ELO modifier columns | 1 commit | Yes — recompute-and-set | No | Low |
| Resync position counts | count columns | 1 commit | Yes — resync | No | None |
| Detect counter-signals | none (read-only; alert path separately broken, see the built-never-connected sweep) | N/A | N/A | No | None |
| Snapshot ELO scores | `elo_snapshots` | 2 commits | **Yes, explicit** — own docstring: append-only, `INSERT OR IGNORE`, composite PK | No (not needed) | None |
| Snapshot order books | `order_book_snapshots` | 1 commit | **Yes** — `INSERT OR IGNORE` | No | None |
| Write integration health | `brain/integration-health.json` | file overwrite | Yes | No | Worst case: stale file |
| Discover leaderboard traders (Sun) | `INSERT ... ON CONFLICT DO NOTHING` | 3 commits | **Yes, best-designed in the file** — re-derives known addresses from live DB every run, logs skips as "(resume)" | No file, self-resuming by construction | **None — even its documented historical SIGKILL was safe** |
| Sync trade categories [full, weekly] (Sun) | same as daily variant | 1 commit | Yes | No | None |
| Run test suite | `tests/LATEST_TEST_RESULTS.md` | file overwrite | Yes | No | None |
| Deduplicate trades table (Sun) | `DELETE ... WHERE rowid NOT IN (SELECT MIN(rowid)...)` | single statement | Yes — 0 rows on a clean re-run | No | None |
| WAL checkpoint | none (WAL merge) | N/A | Yes | No | None |
| Backfill market dates | `markets.end_date`/`resolution_date` | 2 commits | Yes | Gated by a separate sweep-recency check (not crash-resume) | Low |
| Hydrate stub markets | stub `markets` metadata | 2 commits | Yes — fills NULLs | No | None |

**Flagged prominently: `backfill_market_categories.py` has a real,
unfixed correctness bug that happens on ordinary operation, not only
after a crash.** Its pagination (`fetch_batch()`) uses SQL `OFFSET` over
`WHERE category='Unknown'` — a result set that **shrinks** every time a
row gets successfully classified within the same run. Its checkpoint
(`data/category_backfill_state.json`) advances `last_processed_offset`
by the raw batch size fetched, not by how many rows remained
`'Unknown'` after classification. Any batch containing a mix of
classified and still-unclassified rows causes the unclassified ones to
drift permanently out of future query windows — this happens on **every
normal batch with a mix**, crash or not; a crash between the DB commit
and the checkpoint write just adds one more unit of the identical drift
that already occurs on ordinary successful runs. **This is a
completeness gap (rows silently never revisited again), not corruption
or double-counting** — the `UPDATE` itself is safely re-appliable if a
row is ever reached — so it does not meet the stop condition's literal
wording, but it is the one step in this entire audit that will not
self-correct on its own, ever, for the specific rows it skips.

**No step was found where a mid-run kill leaves state the next day's
run would not correct** — the crash-specific finding is that the *only*
category of harm found across all 30-32 steps is the pre-existing,
crash-independent `backfill_market_categories.py` drift, not a
crash-recovery failure.

---

## Part 3 — the overlap question

**No overlap has ever occurred, in 106 days of continuous log history
(2026-05-31 → today).** A strict `[timestamp] Starting|Finished` state
machine over the full 707,562-line log found **87 "Starting" and 87
"Finished" markers, perfectly 1:1 paired, zero anomalies** — no case of
a new "Starting" arriving while a previous run was still open, and no
unterminated run except the correctly-represented 09-12 crash (one
"Starting" with no matching "Finished," then 09-13 proceeds normally).

**A raw substring count found 93 "Starting" occurrences, not 87 — the
extra 6 are not real overlaps.** They are the same buffering/ordering
artifact identified independently in Part 5 below: a per-trader progress
line from `backfill_transaction_hashes.py`'s prior-day run gets glued,
with no intervening newline, onto the *next* day's "Starting
daily-maintenance" line, because the child's stdout flush and the
parent's own buffered flush land in the file adjacent to each other by
coincidence of timing, not by actual concurrent execution. Confirmed
across 6 occurrences (2026-06-29, 07-13, 08-08, 08-11, one via an
API-error line, and 09-13) — always the same script, always cosmetic,
never a second live process.

**Invocation mechanism: cron, not systemd.** `crontab -l` (parison
user): `0 6 * * * /home/parison/trading-swarm/scripts/cron_wrappers/run_daily_maintenance.sh`.
No systemd timer exists for maintenance (the Sunday full-ELO recalc, by
contrast, IS a systemd timer — see the CLAUDE.md correction from
earlier today — the two mechanisms are different).

**No locking mechanism exists — confirmed today, not just cited from
MASTER_HANDOVER_2026-09-05.** `run_daily_maintenance.sh` sources the
env file, changes directory, and runs
`python3 scripts/daily_maintenance.py >> "$LOG" 2>&1` — no `flock`, no
PID file, no `pgrep` check. Grepping `daily_maintenance.py` itself for
lock-related terms found one incidental, unrelated comment. Contrasted
directly against `run_database_backup.sh`, which **does** have a
documented `flock -n` guard, added specifically because of a real
2026-08-25/26 incident where a stuck 35.56-hour backup run allowed a
second instance to launch on top of it. `run_daily_maintenance.sh` has
no equivalent guard — the MASTER_HANDOVER finding stands, unaddressed,
as of today.

**Overlap arithmetic**: cron fires exactly 24h apart with no
`Persistent=true`-style catch-up mechanism (there's no systemd timer
here to have one). The observed maximum runtime, ~12.3h (a Sunday), is
under half the 24h cadence — geometrically, only a runtime exceeding
~24h could cause an overlap from cadence alone, and nothing close to
that has been observed.

**The known "database is locked" contention (27 occurrences, clustered
in the leaderboard-discovery/transaction-hash-backfill window) is fully
explained by daily_maintenance colliding with the separately-scheduled,
always-live 15-minute `monitor.py` loop — not by two daily_maintenance
instances.** Given the confirmed absence of any historical overlap, the
only other live writer that could produce this contention is the
independent monitoring loop, and the contention's own shape (hours-long
clustering during maintenance's heaviest write steps, not short bursts
at a day-boundary) is consistent with that explanation and not with a
brief two-maintenance-runs collision.

---

## Part 4 — the steps themselves

**Current count, verified precisely from `build_steps()`: 30 steps on a
weekday, 32 on Sunday** (2 Sunday-only: "Discover leaderboard traders,"
"Sync trade categories [full, weekly]"). Including the 4 always-run
trailing tracked actions (test suite, WAL checkpoint, backfill market
dates, hydrate stub markets) plus Sunday's dedup action: **34 tracked
weekday, 37 Sunday** — matches today's live banner exactly (`36/37 OK`).

**Growth trajectory** (5 points across 45 commits since 2026-03-20):
`03e75b0` (2026-03-20): 2 steps → `631a2f6` (2026-06-05): 16 →
`764839b` (2026-07-09): 29 → `5fcbffe` (2026-08-21): 29 → today: 30.
This confirms the task's "19-20 vs 29" framing — 29 was the July/August
plateau; growth has nearly stopped since (29→30 in ~7 weeks, vs 2→29 in
the prior ~4 months). Two existing tests reference step counts
(`test_maintenance_banner_honesty.py` uses illustrative fixture
numbers into a pure function, not asserting reality;
`test_weekly_full_sync_gate.py` reads `len(STEPS)` dynamically at test
time) — **neither is a stale hardcoded assumption**, both remain valid
regardless of future step-count changes.

**Step-by-step consumer check: no new orphaned-output step found**,
beyond the two the 2026-09-13 built-never-connected sweep already
named (`detect_counter_signals.py` step 27, Shape 4; `score_insider_signals.py`
step 10, scoring a dead pipeline — both cross-referenced, not
re-derived). Every other step's output was traced to a live consumer —
notably, the STR-002/STR-003 signal pipeline has a real cross-repo
consumer in trading-swarm's `orchestrator.py` and
`run_feedback_loop_agent.py`, confirming it is not an orphan.

**Runtime trend — the two known giants, plus several newly-identified
growers:**
- **Discover leaderboard traders**: stable, ~19,100s→18,100s avg, max
  30,255.8s (8.4h).
- **Backfill transaction hashes**: grew **5.9x** (1,876s→11,073s avg),
  tracking `geo_accuracy_pool`'s growth from 177→4,495 traders.
- **New findings, not previously flagged**: Register STR-002 signals
  (**27x** growth, 9.2s→247.9s), Requeue resolved market traders (**25x**,
  0.7s→18.7s, small absolute), Snapshot order books (**17x**,
  15.0s→255.2s), Fetch new market resolutions (**8.3x**, 32.5s→269.1s),
  Backfill market dates (**4.4x**, 124.6s→553.5s), Backfill market
  categories (0.0s→84.1s avg — an emerging backlog, consistent with
  Part 2's skip-drift finding above), Update geo ELO scores and Apply
  full ELO modifiers (~5-6x, still small absolute).
- **Counter-trend**: Verify market titles got *faster* over time
  (0.18x, 3,412s→614s avg) — a backlog clearing, the one step trending
  the right direction.
- **One-off anomaly, not a trend**: Evaluate new trader results spiked
  to 5,293.3s once against a normal ~46.8s average — a single outlier
  day, not investigated further.

**Moot work**: checked every step script against the specific
tables already known to be frozen/stale (`event_cluster_labels`,
`dilution_guard_signals`, `trader_categories`) — zero additional
matches found beyond the already-known `score_insider_signals.py` case.

---

## Part 5 — the logging gap

**Corrected understanding — the earlier characterization ("stdout is
captured and discarded for passing steps") was wrong, and this audit
found the real mechanism.** Reading `run_step()`
(`daily_maintenance.py:270-307`) directly: it calls
`subprocess.run(cmd, cwd=..., env=env, timeout=timeout)` with **no**
`capture_output` or `stdout=` argument at all — the child's stdout is
**inherited directly**, not captured, not discarded.

**What actually happens**: `daily_maintenance.py`'s own `print()` calls
are block-buffered (no `PYTHONUNBUFFERED` set anywhere in its
environment setup), so its own step-header/footer lines
("`[N/32] label`", "`--- Step: X ---`", "`OK (Ns)`") sit in its own
large, long-lived buffer and are physically written to the log file only
when that buffer fills or the whole process exits — while **each short-
lived child subprocess flushes its own, much smaller buffer at its own
process exit**, which happens far sooner. The result: a step's genuine
printed output can land **physically earlier in the log file** than the
"--- Step: X ---" header that logically precedes it, making it look
(to a human reading top-to-bottom) as if the output is missing, when it
is actually present elsewhere, chronologically displaced.

**Confirmed concretely, not just theorized**: today's step 22
("Evaluate geo/elec pending results") appears in the log with nothing
between its script-name line and "OK (14.4s)" — but the script's own
"Fetching pending trades..." / "Found 51 pending trades to evaluate."
lines **do exist in the log**, ~1,900 lines *before* the header line
they logically belong to (line 705592 vs. 707481). The same mechanism,
in the same script family, independently produced the 6 "phantom
overlap" artifacts found in Part 3 (a prior day's per-trader progress
line glued onto the next day's "Starting" line with no newline between
them).

**What is lost as a result**: nothing is *discarded* — but the log is
**unreliable for reconstructing exact timing or for a human scanning
top-to-bottom to find a given step's own output**, since it can be
buried thousands of lines away from its header. Numbers computed via
`time.time()` inside `daily_maintenance.py` itself (the "OK (Ns)"
durations) are unaffected, since those are constructed strings printed
by the parent, not raw child passthrough — but any step's own
self-reported counts (like step 22's won/lost/invalid, or step 12's
running fetched/matched totals) require a full-log grep by content, not
a look at the position immediately following that step's header, to
find.

**Steps that DO explicitly capture and reformat child output**: the
test suite, dedup, and WAL-checkpoint actions use `capture_output=True`
and re-print a constructed summary (e.g., "PASS — ALL TESTS PASSED
(198.7s)") rather than raw passthrough — for those, the *summary* is a
reliable record, but the child's full raw output beyond what's
explicitly extracted is genuinely not retained anywhere.

**Is there a reason not to capture it?** Nothing found suggesting a
deliberate reason (no secrets-in-output or volume concern documented
anywhere) — this reads as an unexamined default (subprocess.run's
inherited-stdout behavior, combined with never setting
`PYTHONUNBUFFERED`) rather than a considered choice.

---

## What was not determined

- Exact commit mechanism for "Update geo ELO scores" — no explicit
  `.commit()` string was found in a first pass; presumed autocommit or a
  wrapper, not conclusively resolved.
- Several steps' idempotency is "presumed yes" based on the general
  recompute-and-set pattern rather than independently proven by reading
  every line of every script (Detect ARB_BOT patterns, Score STR-003
  signals, Enrich/Score STR-002 metadata, Resolve LEGENDARY trader
  markets, Backfill market dates, Hydrate stub markets) — flagged as
  "presumed," not verified to the same depth as the steps explicitly
  marked "Yes, explicit."
- Whether `backfill_transaction_hashes.py`'s Data API retention window
  actually caused any specific trade to permanently miss its hash
  (Part 1's caveat) — not investigated, considered unlikely given the
  cadence-vs-retention math, not confirmed absent.
- Whether Pool C membership itself changed between 09-12 and 09-13 in a
  way that could have dropped one of the 955 delayed traders out of the
  list entirely (a data-completeness edge case, not corruption) — not
  checked.
- The `backfill_market_categories.py` skip-drift bug's cumulative
  scale — how many rows have actually drifted out of reach to date —
  was not quantified this pass; only the mechanism was confirmed.
- Whether `backfill_transaction_hashes.py`'s own buffering artifact
  (the cause of the 6 phantom-overlap log lines) could, under different
  timing, ever risk genuine data misattribution rather than merely
  cosmetic log confusion — not independently verified as always safe.

No remediation is proposed for any of the above beyond naming the
mechanism — what to fix, and in what order, is Oscar's call.
