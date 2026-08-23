# 2026-08-23 — sweep safety fixes: hold mechanism + terminal signal

**CODE CHANGES. NO production writes.** Segment 3 not launched.
Pre-registration: `2026-08-21-discovery-gap-closure-prereg.md` (`23630ee`,
as amended) — §C daily-step policy, execution mode. Survey:
`2026-08-23-sweep-inhibitor-survey.md` (`752cdbd`). first-repo commits:
`e4ddb67` (Fix 1), `72e7337` (Fix 2), built on `b3f4aea`.

---

## Recency window: 1800 seconds (30 minutes)

**Chosen to reuse an already-battle-tested constant, not invent a new
one.** It is exactly `segment2_write.py`'s own `MAINTENANCE_STOP_MARGIN` —
the sweep driver already stops itself 30 minutes before the next 06:00
fire. A live segment writes a checkpoint roughly once per batch: tranche
2 measured 202.6–214.0s/batch (~208s) across all ten of its batches, a
tight ±3% band. **30 minutes is ~8.6x that observed cadence** — real
margin against one slow batch, not a hair trigger — while still short
enough that a dead sweep can suppress the daily step for **at most half
an hour, never days.**

**Boundary, stated exactly:** the comparison is strict `<` — a checkpoint
exactly 1800.0s old is STALE (the step runs), not active. Ties resolve
toward running the step, consistent with the fail-open requirement below:
this check must never be the reason a daily step silently stops running.

---

## Fix 1: checkpoint-recency hold

**`scripts/daily_maintenance.py`** (`e4ddb67`). Two new pure(ish) functions,
`_sweep_checkpoint_age_seconds()` and `_sweep_recently_active()`, both
accepting explicit `checkpoint_glob`/`now` parameters for direct testing
without touching real files or real time. The "Backfill market dates" step
now checks `_sweep_recently_active()` before running; if active, it prints
a SKIPPED line with the checkpoint path and age and does **not** add to
`failed_steps` — it counts toward the OK total, distinguishable in the log
from `OK (Xs)` but not reported as a failure.

**Source of truth: each checkpoint's own `last_updated_utc` field**, not
filesystem mtime — every sweep driver to date (`tranche2_write.py`,
`segment1_write.py`, `segment2_write.py`) already writes this field on
every batch, and using it (rather than mtime) means an unrelated file
copy/rsync can't masquerade as recent activity. The glob
(`data/checkpoints/segment*_checkpoint.json`) picks up **any** segment's
checkpoint, present or future, and uses whichever is freshest.

**Fail-open, exactly as specified, at two layers:**
1. Any single checkpoint that's missing, not valid JSON, or missing/wrong-
   typed `last_updated_utc` is skipped (not raised) inside the age-scan
   loop — it doesn't poison the check for other checkpoints.
2. If **no** checkpoint yields a usable age at all — no files match, or
   every match is bad — `_sweep_recently_active()` returns
   `active=False`, i.e. **the step runs.** A second, outer guard
   (`except Exception: return False, None, None`) makes this the return
   value for literally any unexpected failure in the helper, not just the
   anticipated ones.

**Only this one step is held.** No change was made to
`resolution_sweep.py` — the survey (`752cdbd`) established it reads
`markets` and writes `traders`, never touches `markets.resolved`, and
already carries a 30s `busy_timeout`. It needs no hold and got none.

---

## Fix 2: terminal marker + Telegram-on-exit

**`data/characterizations/sweep_common/sweep_terminal_signal.py`**
(`72e7337`, new file). Two functions:

- **`write_terminal_marker(marker_path, status, batches_completed,
  n_batches, cumulative_processed, cumulative_tally, reason=None)`** —
  atomic (temp file + `os.replace`) JSON marker, same pattern as the
  per-batch checkpoint. `status` is validated against the driver's own
  existing vocabulary (`COMPLETE`, `ABORTED`, `MAINTENANCE-STOPPED`,
  `STOPPED (incomplete)`, plus the one new state, `EXCEPTION`) — an
  invalid status raises `ValueError` rather than being written, since a
  wrong marker is worse than none. **Distinct from the checkpoint by
  design:** the checkpoint says how far a run got; this says *why* it
  stopped, which a checkpoint frozen at batch 87 cannot express on its
  own (still running? paused for the night? dead?).

- **`send_telegram_terminal(message)`** — established this session by
  reading `monitoring/telegram_bot.py` directly rather than assuming an
  interface: it's an async `TelegramNotifier` class built for a
  long-lived, bidirectional polling bot (`/start`, `/status`, `/stop`
  command handlers) — too much machinery to spin up and tear down once
  per process exit. **Used the actual established synchronous pattern
  instead**, found in `scripts/audit_invariants.py`'s
  `send_telegram_alert()`/`_send_telegram_async()`: a plain
  `asyncio.run(...)` wrapper around `python-telegram-bot`'s
  `Bot.send_message`, reading `telegram_alerts_token`/`telegram_chat_id`
  from the environment — the same credentials that script already uses
  (confirmed present in `/home/parison/.env_trading` this session, values
  not read or logged).

**Guaranteed never to raise** — the entire body is inside one
`try/except Exception`; any failure (missing credentials, network error,
Telegram API error, an import error) is caught, logged to stderr, and the
function returns `False`. Guaranteed by construction, verified in Section
4 of the test file below by simulating both a successful and a failing
send with `asyncio.run` monkeypatched — **no real network call is made
anywhere in this suite, regardless of whether real credentials happen to
be present in the environment.**

**Not wired into `segment2_write.py`.** That segment already ran to
completion (`b3f4aea`) before this module existed. Retrofitting a
finished, already-committed driver after the fact would misstate what
code actually produced segment 2's results — this project's own
reproducibility discipline (prereg §G: "committed... before it runs")
treats that as a hard line, not a style preference. This module is for
the **next** segment driver (not created, not launched by this task) to
import at its three exit points — normal completion, an abort-condition
break, and a top-level `except Exception` around the batch loop — exactly
as demonstrated in the test file.

**SIGKILL limitation, stated plainly, in the module's own docstring and
here again:** a hard kill (SIGKILL, power loss, an OOM-kill) gives the
process no chance to run any exit code, including everything in this
module. No marker is written, no Telegram message is sent. Nothing in
userspace can trap SIGKILL, and this module does not claim otherwise. The
absence of **both** a terminal marker and a recent checkpoint (Fix 1's own
recency check) is itself the signal a hard kill leaves behind — a human
or automated watcher must read "no marker, stale checkpoint" as "probably
killed," not wait for a report a hard kill made impossible.

---

## Verification

### Fix 1

**a. Baseline from git, not transcribed.** `git show
b3f4aea:scripts/daily_maintenance.py` captured to a scratch file before
any edit;
`grep -c '_sweep_recently_active\|_sweep_checkpoint_age_seconds\|SWEEP_RECENCY_WINDOW'`
returned **0** — none of it existed pre-fix.

**b. Proves it skips.** `tests/test_sweep_checkpoint_recency.py` T2:
a synthetic checkpoint 5 minutes old → `active=True`, correct path
reported, age ≈300s. Also demonstrated against the **real** default glob
path (not the test's temp dir): wrote a throwaway
`data/checkpoints/segment99_checkpoint.json` with a fresh timestamp,
called `_sweep_recently_active()` with its real default arguments →
`active=True, age=0.1s`, then deleted the throwaway file immediately
(`git status` confirms no trace left behind).

**c. Proves it runs — no checkpoint, stale, and malformed, all three.**
T1 (no checkpoint at all), T3 (45 minutes old, beyond the window), T4
(literally `"{not valid json at all"` — the fail-open guarantee,
demonstrated directly: no exception raised, `active=False`), T4b (valid
JSON missing the `last_updated_utc` field), T4c (valid JSON, unparseable
timestamp string). All five → `active=False`, step runs, no exception in
any case.

**d. Proves the test would fail against the pre-fix code — not merely
asserted.** Dynamically loaded the exact pre-fix baseline file (`git show
b3f4aea:...` from item a) as a live Python module and called
`_sweep_recently_active()` on it: `AttributeError: module 'dm_baseline'
has no attribute '_sweep_recently_active'`. There is no function to call
against the old code — the strongest form of "would fail" available.

**e. Not run via daily_maintenance.** Every proof above calls the check
functions directly (unit-style), with a scratch temp directory or a
single throwaway file for the real-path demonstration. `daily_maintenance.py`
itself was never executed as a subprocess for this verification.

### Fix 2

**f. Baseline from git.** The module and its directory
(`data/characterizations/sweep_common/`) did not exist before this task —
new file, first commit `72e7337`. `import sweep_terminal_signal` against
any pre-fix checkout fails with `ModuleNotFoundError` — there is no old
module for a test to run against, the same shape of proof as Fix 1's item
d.

**g. Completion marker on normal exit.** `tests/test_sweep_terminal_signal.py`
T1: `write_terminal_marker(..., status="COMPLETE", batches_completed=121,
n_batches=121, cumulative_processed=60500, cumulative_tally={...})` —
confirmed written atomically (no leftover `.tmp`), confirmed byte-for-byte
readable back from disk, confirmed `written_at_utc` present.

**h. Abort marker on a simulated threshold fire.** T2: simulated
`status="ABORTED"` with the literal shape of a real abort reason string
(`"ABORT CONDITION 3 (cumulative >20%, floor met): cum_indet_rate=23.4%
after batch 45"`) — confirmed the reason is recorded verbatim, confirmed
`batches_completed < n_batches` distinguishes it structurally from a
completion marker. T2d: an invalid status string is rejected
(`ValueError`), not silently written.

**i. Unhandled exception still produces a marker.** T3: a driver-shaped
`try: ... except Exception as exc: write_terminal_marker(...); raise`
around a function that raises `KeyError("token.winner")` (standing in for
a real, unanticipated bug — not an abort condition) — confirmed the
marker is written **before** the exception re-propagates (T3b: the
exception is not swallowed, it still reaches the outer catch), and the
marker's `reason` field contains the actual exception type and message
(T3c).

**j. Telegram send failure does not affect the run — simulated.** T4b/T4c:
`sts.asyncio.run` monkeypatched to a function that raises
`ConnectionError` — `send_telegram_terminal()` catches it internally,
returns `False`, and **does not raise** out to the caller. Guaranteed by
the function's own single `try/except Exception` wrapping its entire
body — verified directly, not inferred from reading the code alone.

**k. No per-batch Telegram traffic.** T5/T5b: `send_telegram_terminal` is
defined exactly once in the module and is **never called from within the
module itself** — it exists purely as a library function for an external
caller to invoke once per exit. There is no loop construct anywhere in
this file, so there is structurally nowhere for a per-batch call site to
exist.

**Also verified, not requested but necessary given real credentials exist
on this box:** every Telegram-touching test monkeypatches `asyncio.run`
before it can be reached, so **no real message was sent by this task's
test suite**, regardless of whether real `telegram_alerts_token`/
`telegram_chat_id` are present in the environment (they are — confirmed
present in `/home/parison/.env_trading`, values not read).

### Both

**l. `run_tests.py`.** Baseline: 16 files, 15 passing, 19/24 in
`test_backtest_window_population.py`. After Fix 1: **17 files run, 16
passed, 1 failed** (only `test_backtest_window_population.py`, the
pre-existing failure, unchanged shape). After Fix 2: **18 files run, 17
passed, 1 failed** — same single pre-existing failure. Exactly +1 file
per fix, both new files passing 100%, **zero new failures.**

**m. No production DB write — verified against the actual write target,
not inferred.** `data/polymarket_tracker.db`'s mtime did shift during this
session (1787514597 → 1787514956, ~6 minutes), but this is **not**
attributable to this task: `logs/monitoring.log`'s tail shows
`background_pnl_worker` actively processing batches every ~10 seconds
throughout the exact window this work was done (`polymarket-monitoring`
is a live, always-on systemd service per CLAUDE.md, confirmed running
this whole session) — that background service, not this task, accounts
for the DB's continuous mtime drift. Stronger, structural evidence:
`grep -n "sqlite3\|\.db\b"` against every file this task touched or
created (`scripts/daily_maintenance.py`'s diff,
`data/characterizations/sweep_common/sweep_terminal_signal.py`,
`tests/test_sweep_checkpoint_recency.py`,
`tests/test_sweep_terminal_signal.py`) returns **zero references to the
database at all** — none of this task's code opens a SQLite connection,
so it structurally cannot have written to it, independent of any mtime
coincidence.

**n. Production code otherwise untouched.** `git diff --stat` against
`scripts/backfill_market_dates.py`, `monitoring/resolution_writer.py`,
`scripts/fast_resolution_check.py`, and (checked additionally, since it's
the concrete driver referenced throughout this task)
`data/characterizations/sweep_segment2/segment2_write.py` — all four
**empty**, confirmed via both `git diff --stat` and `git status -s`.

---

## Verdict

**Both fixes pass verification in full — nothing stopped.** Recorded per
the task's own instruction: since neither fix failed, there is no partial
report to give.

**Does this unblock segment 3, or does anything else stand in the way?**
Both fixes are ready to be used by segment 3's driver when it's created
(a separate task — not done here, per the constraint not to launch
segment 3): the daily-maintenance hold is live now, unconditionally, for
any future segment's checkpoint; the terminal-signal module is committed
and tested, waiting to be imported at segment 3's three exit points the
way `tests/test_sweep_terminal_signal.py` demonstrates. **Segment 3 itself
was not launched, per instruction, and nothing here creates or schedules
it.**
