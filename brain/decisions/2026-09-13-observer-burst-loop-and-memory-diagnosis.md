# Observer burst-flush loop, generic_error clusters, memory growth, SIGTERM hang — read-only diagnosis

Tagging: [V]=verified this session (code/log read, or direct query), [I]=inferred from evidence, not directly observed, [U]=undetermined.

Scope: read-only. The observer (PID 1229, current boot, up since 2026-09-12 13:07:25) was not signalled, restarted, or attached to. All reads were `journalctl -u polymarket-observer -b 0` (current boot only, per instruction not to grep the multi-boot journal), `logs/monitoring.log`, `logs/daily_maintenance.log`, and static reads of `monitoring/*.py`. No production table was written. `metric_v2f_oos_result` sha256 checked before and after: `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` — **unchanged**.

**No active data loss or corruption found.** The errors below are retried-and-skipped failures with an explicit recovery path (see Part 1), not corruption.

---

## Summary — one root-cause cluster, not four unrelated faults

All four symptoms trace to the same pair of mechanisms:

1. **The database experiences real, ongoing write-lock contention** (`database is locked`, [V] — 6,195 occurrences in `logs/monitoring.log`'s full history, 27 today, concentrated in the heaviest maintenance-write windows).
2. **The observer's own code makes this contention worse for itself**: dozens of synchronous `sqlite3.connect(..., timeout=30.0)` calls are made directly inside `async def` coroutines, with no thread-executor offload — so a single lock wait can block the *entire* single-threaded asyncio event loop for up to 30 real seconds [V, code-read].

That single design pattern explains the burst-flush loop (Part 2), plausibly explains the SIGTERM hangs (Part 4), and is aggravated into a genuine memory leak by a second, independent bug: a pruning method that exists but is **never called** (Part 3). The generic_error clusters (Part 1) are the real, legitimate exhaust of all of this — not noise.

---

## PART 1 — What are the 1,122 errors

**Two parallel, independent detectors run over the same log tail**, both wired into `monitoring/system_observer.py::_log_monitor_loop` (`monitoring/system_observer.py:361-430`):

- **Primary: `ErrorParser`** (`monitoring/error_parser.py`) → printed as `"[OBSERVER] Detailed error detected: {error_type or 'Unknown'}"`. Current-boot count: **454**, all typed `Unknown` [V] — `ErrorParser.parse_log_line()` recognizes a level tag (ERROR/WARNING/CRITICAL) and extracts component/timestamp/context, but its `error_type` extraction evidently doesn't match the shapes seen (mostly plain `- ERROR -` logging-module lines), so it always falls through to `'Unknown'`. This is not a broken classifier so much as an incomplete one — it correctly detects *that* something failed, not *what kind*.
- **Fallback: `LogMonitor.detect_errors()`** (`monitoring/log_monitor.py:124-172`) → printed as `"[OBSERVER] Error detected: {type}"`. Only reached when `parse_detailed_error()` returns `None`. Current-boot distribution:
  - `generic_error`: **1,122**
  - `traceback`: **407**
  - `timeout`: **102**

**`generic_error` is confirmed to be the broadest bucket, and it is checked FIRST, not last** [V, code-read, `log_monitor.py:57-65,142-170`]:
```python
self.error_patterns = {
    'generic_error': re.compile(r'ERROR.*', re.IGNORECASE),   # checked first
    'critical': re.compile(r'CRITICAL.*', re.IGNORECASE),
    'traceback': re.compile(r'Traceback.*'),
    ...
}
...
for pattern_name, pattern in self.error_patterns.items():
    if pattern.search(line):
        ...
        return error_info   # first match wins, no continue-to-more-specific
```
Because dict iteration is insertion order and the function returns on the *first* match, `generic_error` (`ERROR.*`, case-insensitive, matches anywhere in the line) shadows `critical` and `api_error` for any line that happens to also contain the substring "error" — which most exception-class-name lines do (`ValueError`, `KeyError`, etc. all end in `...Error`). It is functionally a catch-all for "line contains the word error and isn't a bare Traceback header or a timeout message," not a true "could not classify" fallback with a distinct code path — there is no explicit "unmatched" branch; a truly non-matching line just returns `None` and is silently dropped (not counted, not printed).

**Ground truth — the underlying `logs/monitoring.log` content is a real, legitimate, and previously-undocumented operational problem**, not test noise or corrupted lines [V, direct read]:
```
2026-09-13 13:23:08,163 - pnl_worker - ERROR - Position insert failed for 0x5cc27909
2026-09-13 13:23:38,281 - pnl_worker - ERROR - Trader update failed for 0x5cc27909
2026-09-13 13:23:49,407 - monitoring.monitor - ERROR - Error in monitoring cycle: database is locked
2026-09-13 13:23:49,407 - monitoring.monitor - ERROR - Full traceback:
2026-09-13 13:24:08,398 - pnl_worker - ERROR - Failed for 0x5cc27909
...
2026-09-13 13:35:42,248 - pnl_worker - ERROR - [PNL WORKER] Skipping 0x058623... after 5 consecutive failures. Will retry on next service restart.
2026-09-13 13:35:52,289 - pnl_worker - ERROR - Failed to persist pnl_skip for 0x0586236e: database is locked
```
- **Component name**: present and consistent (`pnl_worker`, `monitoring.monitor`).
- **Stack trace**: `monitoring.monitor` prints a literal `"Full traceback:"` header line (the actual multi-line traceback that follows was not individually pulled apart here, but its presence is confirmed).
- **HTTP status**: none — these are SQLite errors (`database is locked`), not network/API errors.
- **Distribution is a mix, dominated by one cause**: `database is locked` accounts for the majority of what's driving both `generic_error` and `Detailed error detected: Unknown` during the maintenance-heavy afternoon window (27 occurrences today, clustered 12:50–13:40 UTC — squarely inside the "Discover leaderboard traders" maintenance step, see Part 2). The rest is `pnl_worker`'s per-trader `Failed for 0x...` / `Position insert failed` / `Trader update failed` retry noise, which is downstream of the same lock contention.
- **Not data loss**: `pnl_worker` has an explicit skip-and-retry contract — "Skipping ... after 5 consecutive failures. Will retry on next service restart" (18 such skip events today) — so affected traders' P&L updates are deferred, not lost, pending a `polymarket-monitoring` restart. This is a real gap worth Oscar's attention (see Part 5) but is not corruption.

---

## PART 2 — What is the loop doing: verdict (a)/(c), not (b)

**Verdict: a genuine runaway/starvation pattern — asyncio timers backing up behind synchronous blocking calls, then firing in a burst once the block clears. Not simple output buffering.**

Evidence against pure buffering-artifact (b):
- Timestamps *within* one burst are not bit-identical — they step forward in small increments (e.g. `14:24:58.417095` → `.418367` → `.419411`), consistent with real, fast, back-to-back execution (low-single-digit milliseconds between log lines), not a single write() flush of pre-generated text.
- `_health_check_loop` (`monitoring/system_observer.py:285-359`) always executes `await asyncio.sleep(60)` — in **both** the success path (line 353) and the exception path (line 355-359). There is no code path that skips or shortens the sleep. Ruled out: (c) "an exception handler that continues without sleeping" for *this* loop specifically.
- The health-check counter timestamp is the moment `print()` executes after `await self.health_checker.check_all()` returns — i.e. it is an **event-time** stamp (computed at execution), not a value read out of stored data. A burst of 26–33 of these sharing one wall-clock second means 26–33 real calls to `check_all()` executed back-to-back, each of which should have been preceded by a real 60-second sleep.

**Mechanism identified, code-grounded**: `HealthChecker.check_all()` (`monitoring/health_checker.py:949+`) runs eleven checks per cycle — six called as plain synchronous methods, five as `await self.check_X()` — but **every one of them, sync or "async," opens its own `sqlite3.connect(self.db_path, timeout=30.0)`** [V — confirmed via grep across `health_checker.py`, `system_observer.py`, `diagnostics.py`]. `sqlite3` has no native async support; wrapping a blocking DB call in `async def` does not make it non-blocking. `timeout=30.0` is SQLite's busy-handler retry window — under write contention, that call can block the *entire* single-threaded process, synchronously, in a C extension, for up to 30 real seconds, once per sub-check, with no `run_in_executor`/`asyncio.to_thread` offload anywhere.

The same shape exists in `_log_monitor_loop` (`system_observer.py:361-430`): `for line in self.log_monitor.tail_logs(follow=False): ...` iterates synchronously with `await` calls only inside the body when an alert actually fires (most are currently silenced, see Part 5 — so most lines in a backlog are processed with **no yield point at all**). If `monitoring.log`'s growth ever outpaces one 2-second poll cycle (`await asyncio.sleep(2)` at line 426), the next cycle's backlog is proportionally larger, compounding.

While either loop is stuck synchronously — inside a 30-second `sqlite3` busy-wait, or churning a large backlog of log lines with no await — the shared asyncio event loop cannot advance *any* other coroutine's timer, including `_health_check_loop`'s `sleep(60)`. Once the block clears, every timer that should have fired during the stall fires immediately, back-to-back: this is the burst.

**Interval finding — corrects the progression check's estimate.** The prior report's "94 bursts ≈ every 15 minutes" conflated intra-burst microsecond entries with distinct burst events. Re-clustered (gap > 5s = new burst) [V]: there are **21 distinct burst events** in the current boot, not 94. Their spacing is **not** a stable 15-minute cadence and does **not** match the monitor's 15-minute poll:

| Period | Burst-to-burst gap |
|---|---|
| `09-12 14:25` → `09-13 10:11` (11 bursts) | 79–167 min, median ~104 min |
| `09-13 10:11` → `09-13 13:55` (10 bursts) | 24.5–39.5 min, median ~26 min |

**The burst rate roughly quadrupled starting at 10:10:34 UTC today** [V] — which is the exact start of `daily_maintenance.py` step 31, "Discover leaderboard traders" (cumulative timeline reconstructed from step durations: starts `10:00:48`, runs **13,218.3s / 3h40m18s**, ends `13:41:06` — verified against the independently-timestamped test-suite step, which the reconstruction places at `13:45:41`, matching `tests/LATEST_TEST_RESULTS.md`'s recorded run time exactly). All ten of the shorter-interval bursts fall inside or immediately after this step's window. This step is a long, presumably write-heavy trader-discovery pass; the correlation with `database is locked` errors appearing in the same window (Part 1) supports write contention, not the 15-minute poll, as the trigger.

**Not resolved by the reboot.** The pre-reboot occurrence (#3161–#3314+, 2026-09-12 03:05:19, recorded in `2026-09-12-session-summary.md` but never diagnosed) and this boot's 21 bursts are the same mechanism, observed twice.

---

## PART 3 — The memory question: confirmed unbounded accumulator, and it is fed directly by Part 2

Current single-point reading: observer RSS **249.2 MB** (`ps`, this session). No in-process RSS history exists — `HealthChecker.check_memory_usage()` (`health_checker.py:332`) checks the **monitoring** process's memory (`target_pid = pid or self.monitoring_pid`), never the observer's own. The observer does not monitor itself. External history is limited to what a prior session recorded in `brain/decisions/2026-09-07-session-summary.md`: an 11.6 GB peak after **2h16m of CPU time** on a long-lived process; the process restarted 45 minutes later peaked at only 378.9 MB; a fresh restart sat at 168 MB. **This shape — growth that tracks uptime, not a single spike — is diagnostic in itself**, and points away from a one-shot allocation and toward a slow, monotonic accumulator.

**Found the accumulator.** `monitoring/error_parser.py`:
```python
class ErrorParser:
    def __init__(self):
        self.error_history: List[ErrorDetail] = []
        self.error_groups: Dict[str, List[ErrorDetail]] = defaultdict(list)

    def add_error(self, error: ErrorDetail):
        ...
        existing_errors.append(error)          # or self.error_groups[signature] = [error]
        self.error_history.append(error)        # <-- unconditional, no bound

    def clear_old_errors(self, hours: int = 24):
        cutoff = datetime.now() - timedelta(hours=hours)
        self.error_history = [e for e in self.error_history if e.timestamp >= cutoff]
        self.error_groups = defaultdict(list)
        for error in self.error_history:
            self.error_groups[error.signature].append(error)
```
`add_error()` is called once per detected error via `LogMonitor.detect_errors_wrapped → error_parser.add_error()` (`log_monitor.py:376`) — this is the exact code path behind every "Detailed error detected" line (454 today, on this boot alone). Each `ErrorDetail` carries the full message, a parsed stack trace list, and a context dict — not a small object.

**`clear_old_errors()` exists, is correctly implemented, and is never called** [V — exhaustive grep for `clear_old_errors` and `error_parser.error_history` across `monitoring/*.py` and `scripts/*.py`]. `LogMonitor.clear_old_errors()` (`log_monitor.py:480`) correctly delegates to it, but nothing in `system_observer.py`, `run_system_observer.py`, or any script ever calls either. This is dead code guarding against exactly the failure mode observed. (By contrast, `LogMonitor.error_history` itself — a *different* attribute, at `log_monitor.py:49` — is a `deque(maxlen=1000)` and is correctly bounded; and `PerformanceMonitor.metrics_history` in `diagnostics.py:491-547`, named as a suspect in the 2026-09-07 write-up, is also correctly self-trimming to a 24-hour window on every call. Neither of those is the leak. `ErrorParser.error_history`/`error_groups` is.)

**Yes — the burst behaviour plausibly, directly feeds the growth**, mechanistically, not just by rough arithmetic: every burst is, definitionally, a spike in `add_error()` calls (454 `Detailed error detected` events across ~21 bursts today ≈ ~22 per burst on this boot), each permanently retained in two structures (`error_history` and `error_groups`) for the remaining lifetime of the process. More uptime → more bursts → more retained `ErrorDetail` objects, with nothing ever evicting them except a process restart. This is consistent with the 2h16m-CPU-time process reaching 11.6 GB while a 45-minute-old process sat at 378.9 MB.

**Verdict: the burst loop (Part 2) and the memory growth (Part 3) are two distinct bugs that compound each other, not one fault.** Part 2 (blocking DB calls starving the event loop) determines *how often* and *how large* the error-detection bursts are. Part 3 (the never-called pruning method) determines that *none* of what those bursts detect is ever released. Fixing only one would reduce, but not eliminate, the growth.

---

## PART 4 — The SIGTERM hang: plausible mechanism identified, not proven

`SystemObserver._signal_handler` (`system_observer.py:112-115`):
```python
def _signal_handler(self, signum, frame):
    print("\n[OBSERVER] Received shutdown signal, stopping...")
    self.running = False
```
This is trivial and non-blocking — it does not itself explain a hang. **The candidate mechanism is the same one from Part 2**: Python's registered signal handler only runs when the interpreter next checks for pending signals, which does not happen while the single main thread is inside a blocking C-level call — such as `sqlite3`'s busy-timeout wait. Every DB read in `health_checker.py` and most in `system_observer.py` uses `sqlite3.connect(self.db_path, timeout=30.0)`. If SIGTERM arrives while the process is inside one of these waits, `self.running = False` cannot take effect until that call returns (lock acquired, or the 30-second busy-timeout expires and raises `OperationalError`) and control returns to a point in the loop that re-checks `self.running`.

The systemd unit (`polymarket-observer.service`) sets **`TimeoutStopSec=30`**, `KillMode=mixed` — almost exactly the same window as the DB busy-timeout. A stop request landing during one of these waits has a real chance of losing that race, needing SIGKILL. This is consistent with the pattern: two hangs 2026-09-12 (`06:45:21`, `06:45:57`, shortly before the crash), two hangs 2026-09-07 (`18:23:35`, `19:09:29`, one of which was the 11.6 GB process), all previously recorded but never explained (`2026-09-07-session-summary.md:394-400`, `2026-09-12-session-summary.md:56-69`).

**What was checked and ruled out**: no non-daemon-thread pattern was found — this is a single asyncio event loop, not a multi-threaded design, so "non-daemon thread" isn't the shape of the risk here; the risk is a synchronous call blocking the *one* thread that both runs the event loop and would run the signal handler. No explicit `asyncio.Task` cancellation-suppression (`except asyncio.CancelledError: pass` swallowing shutdown) was found in the loops read.

**What was not determined**: no hang was captured live during this session (none occurred), so this is inferred from code shape plus the 30-second coincidence, not observed directly via a stack sample at hang time — which this task's scope (no attaching, no signalling) correctly forbids obtaining. A `py-spy dump`-equivalent at the moment of a live hang, taken by someone willing to accept the risk of an invasive attach, would confirm or refute this directly; that is a decision for Oscar.

---

## PART 5 — What is at risk if it wedges

**Alerting that would stop firing:**
- **The health-check non-healthy-transition alert is live, not silenced.** `TelegramHealthBot.send_health_alert()` (`telegram_health_bot.py:70-91`) has no "final Telegram cut" gate — only a 10-minute per-status rate limit. Unlike the hourly/startup/legendary/daily/weekly reports (confirmed silenced 2026-09-09 in the same file's config), a WARNING→CRITICAL transition would currently reach Telegram. If the observer wedges, this goes dark with no other channel behind it.
- **Per-error alerting** (`send_detailed_error_alert`, `send_error_alert`, `send_known_issue_alert`) — same file, same lack of a silence gate found — would also stop.
- **The 6-hourly comprehensive/change-gated diagnostic report** (`"[OBSERVER] Comprehensive diagnostics: every 6h"`) would stop running, not just stop alerting.
- **Auto-restart of `polymarket-monitoring` on death** is also owned by `_health_check_loop` (`system_observer.py:322-350`, the once-per-hour-limited restart logic). A wedged observer means the core 15-minute monitor loop has **no automatic recovery** if it dies while the observer is stuck — this is a materially larger risk than lost alerting, since it compounds with the very `database is locked` contention already documented in Part 1.

**Data loss / inconsistency:** none identified as a direct effect of the observer wedging. The observer's own DB usage, everywhere read in this session, is short-lived, mostly `SELECT`-only connections opened and closed per call. The `database is locked` errors originate from `pnl_worker` and `monitoring.monitor` (the monitoring side), not from the observer holding a lock — no evidence the observer is a *cause* of contention, only a *victim* of it via its own blocking-call design (Part 2/4). **Not fully verified**: whether every one of the dozens of `sqlite3.connect(...)` call sites in `system_observer.py` closes its connection on every exception path was not exhaustively traced (see below).

**Bottom line for urgency**: a wedge costs (a) a live health-degradation alert channel, (b) automatic monitoring-service recovery, and (c) the 6-hourly diagnostic — while the underlying `database is locked` condition it would have been surfacing keeps happening regardless, silently, with only `pnl_worker`'s own "will retry on restart" self-log as a record. That combination — losing the auto-restart safety net at the same time the DB contention that could kill the monitored process is most active — is a real, not merely cosmetic, risk.

---

## What was not determined

- **No live hang was captured this session** (none occurred) — Part 4's mechanism is inferred from code shape and timing coincidence, not confirmed by a stack sample at the moment of a hang.
- **`ErrorDetail`'s per-object size** was not measured (no memory profiler was attached, per scope) — the 11.6 GB figure is real (prior session's own `journalctl`/systemd read) but this session did not independently size how many thousands of accumulated `ErrorDetail` objects it would take to reach that, only that the accumulation is unbounded and the rate is burst-linked.
- **Whether every `sqlite3.connect()` call site in `system_observer.py` closes on every exception path** was not exhaustively traced — only the general pattern (open, use, close) was confirmed at the sites read. A leaked open connection under WAL mode was not ruled out as a secondary contributor to lock contention.
- **What specifically made monitoring.log's write rate high enough, at 10:10:34 today, to shift the burst cadence from ~100 min to ~26 min** was correlated to the "Discover leaderboard traders" maintenance step by time-window overlap and by co-occurring `database is locked` errors, but the step's own write pattern was not read in detail — the causal chain (step → DB writes → lock waits → observer stalls → burst) is plausible and evidence-consistent, not proven line-by-line.
- **Whether `error_groups`/`error_history` is the *sole* contributor to the 11.6 GB figure, or one of several**, was not established — only that it is a confirmed, unbounded, uptime-correlated accumulator directly fed by the observed burst mechanism, and no other unbounded accumulator was found in the code read this session.

No fix is proposed here beyond naming the two mechanisms (blocking DB calls on the event loop; the dead `clear_old_errors()` pruning path). The remedy is Oscar's call.
