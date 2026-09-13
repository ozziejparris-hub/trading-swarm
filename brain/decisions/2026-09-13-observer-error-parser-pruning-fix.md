# Wiring up ErrorParser's pruning — fix for the observer's unbounded memory growth

Follows: `trading-swarm` `db82c9b`,
[`2026-09-13-observer-burst-loop-and-memory-diagnosis.md`](2026-09-13-observer-burst-loop-and-memory-diagnosis.md).
Read that first — this document only covers the one mechanism it scoped
for a fix: `ErrorParser`'s unbounded `error_history`/`error_groups`.

Code change: `first-repo` `monitoring/system_observer.py` (`_health_check_loop`).
Tests: `first-repo` `tests/test_error_parser_pruning.py`, wired into `run_tests.py`
(discovered automatically via the `tests/test_*.py` glob — no runner change needed).
**The observer was not restarted, signalled, or touched at runtime.**

---

## Part 1 — Confirming the diagnosis before changing anything

Re-verified independently, not inherited from the prior document:

- **`ErrorParser.add_error()` (`monitoring/error_parser.py:214-240`) is unconditionally unbounded on both structures** — confirmed by re-reading the method. It appends to `self.error_history` (a plain `list`) on every call with no filtering, and to `self.error_groups[signature]` (a `defaultdict(list)`) either by creating a new single-element list or appending to an existing one — no size or age check anywhere in the method.
- **`clear_old_errors()` has no callers.** Exhaustive grep (`grep -rn "clear_old_errors" monitoring/*.py scripts/*.py`) finds exactly three lines in the whole codebase: the two method *definitions* (`error_parser.py:350`, `log_monitor.py:480`) and one internal delegation (`log_monitor.py:488`, where `LogMonitor.clear_old_errors()` calls `self.error_parser.clear_old_errors(hours)`). Nothing in `system_observer.py`, `run_system_observer.py`, or any script under `scripts/` calls either method. Confirmed dead code, exactly as diagnosed.
- **`LogMonitor.error_history` is bounded, and is a different attribute from `ErrorParser.error_history`.** `log_monitor.py:49`: `self.error_history = deque(maxlen=1000)`. Its own `clear_old_errors()` (`log_monitor.py:490-495`) additionally re-filters this deque by age before rebuilding it with the same `maxlen=1000` — belt-and-suspenders on top of an already-bounded structure. Not the leak.
- **`PerformanceMonitor.metrics_history` self-trims on every call.** `diagnostics.py:543-547`: `collect_metrics()` appends one small dict, then immediately re-filters `self.metrics_history` to the last 24 hours, every single call. Not the leak.
- **Checked for other unbounded accumulators beyond what the diagnosis covered.** Grepped `self.<attr> = []` / `= {}` / `= defaultdict(...)` across every module `system_observer.py` imports (`health_checker.py`, `telegram_health_bot.py`, `error_classifier.py`, `diagnostics.py`, `performance_baselines.py`, `failure_age.py`):
  - `HealthChecker.check_history` (`health_checker.py:53`) — bounded: appended then truncated to the last 100 (`health_checker.py:1043-1045`). Not a leak.
  - **`TelegramHealthBot.last_alert_time` (`telegram_health_bot.py:65`) — found to be unbounded, and NOT covered by the original diagnosis or by this fix.** Most of its keys are fixed, small-cardinality strings (`health_{status}`, `'error'`, `issue_{issue_type}`, `'monitoring_freeze'` — at most a handful of distinct values ever). But `send_detailed_error_alert()` (`telegram_health_bot.py:904`) builds `alert_key = f"detailed_{error.signature[:50]}"` — a key space that grows with every distinct error signature ever seen — and nothing ever evicts entries from this dict. Per-entry footprint is much smaller than an `ErrorDetail` (one string key + one datetime, no message/stack-trace/context), so this alone would not plausibly explain the 11.6 GB figure, but it is a real, separate, unbounded accumulator in a different class.
  - **Per explicit instruction from the operator, this was reported and intentionally left unfixed** — this document's fix targets `ErrorParser` only, as scoped. `last_alert_time` remains open for a future, separately-scoped task.

**No point on which the diagnosis was wrong was found.** Proceeding with the fix as scoped.

---

## Part 2 — The fix

One line added to `monitoring/system_observer.py`, inside `SystemObserver._health_check_loop`, at the top of its `try:` block (before the PID-refresh logic that already runs there every cycle):

```python
while self.running:
    try:
        # Prune ErrorParser's unbounded error_history/error_groups here, not in
        # the 2s log-monitor loop: this is in-memory-only (no I/O), so the 60s
        # cadence is plenty for a 24h retention window, and calling it every 2s
        # would just rebuild the same structures 30x more often for no benefit.
        # See brain/decisions/2026-09-13-observer-burst-loop-and-memory-diagnosis.md.
        self.log_monitor.clear_old_errors()

        # Refresh PID from file on every cycle so stale startup PID never blocks detection
        current_pid = self._read_monitoring_pid_from_file()
        ...
```

`clear_old_errors()` itself was **not touched** — it was already correct.

**Call site: `_health_check_loop`, not `_log_monitor_loop`.**

- `_log_monitor_loop` runs on a 2-second cadence (`asyncio.sleep(2)`, `system_observer.py:426`). Calling a 24-hour-window prune every 2 seconds is 30x more often than the window's own granularity requires — wasteful for no benefit, exactly as the task framed it.
- `_health_check_loop` runs on a 60-second cadence and already does other cheap, unconditional per-cycle bookkeeping (the PID-file re-read at the very next line). Adding one more zero-I/O call to the front of the same `try:` block is a natural fit, not a new pattern.
- **On the "inherits the 30s stall" concern**: `_health_check_loop` is also the loop diagnosed as capable of stalling for up to 30s per cycle (via `HealthChecker.check_all()`'s synchronous `sqlite3.connect(timeout=30.0)` calls, per the burst-loop diagnosis). Placing the prune call here does **not** make that stall worse or longer — `clear_old_errors()` does no I/O of its own (confirmed in Part 1: it's a list comprehension over in-memory objects, nothing else), so it adds negligible wall time to whatever the iteration was already going to take, whether that iteration runs on time or as part of a post-stall burst. It also does not need to run on a strict schedule: if a stall delays this iteration, the prune simply runs a little late next time control returns — harmless for a 24-hour retention window.
- Placed *before* the PID-refresh and health-check logic (not after), so pruning happens unconditionally every iteration regardless of what the rest of that iteration does — including if something later in the same `try:` block raises, since a `try`/`except` around this loop still sleeps 60s either way (see the burst-loop diagnosis's Part 2 for the confirmed unconditional-sleep exception handler).

**Confirmed cheap.** `clear_old_errors()` does two list comprehensions and a dict rebuild, no I/O — Part 3's Section 5 test times a full prune of a 2,000-entry history (roughly 4x the 454-errors-per-boot figure observed the day this bug was diagnosed) at well under one second, in practice sub-millisecond on this box. At any realistic scale for this system this is not a source of new blocking.

**Retention window: kept at the existing default, 24 hours.** Not changed, and deliberately not investigated for a "better" value — `hours=24` is `clear_old_errors()`'s own default, already correct code per the task's constraint not to rewrite it. The observer's own consumers depend on a real history window to function: `add_error()`'s own dedup/grouping logic increments an existing group's occurrence counter only when a same-signature error is added while history for it still exists (`error_parser.py:224-234`) — too short a window would cause daily-cadence repeats to be treated as brand-new errors every time instead of recognized recurrences, which is exactly the grouping behavior `get_top_errors()`/`get_error_summary()` (used to build the observer's diagnostic reports) rely on. 24 hours covers at least one full day-night cycle of this system's own periodic jobs (the 15-minute monitor poll, the 06:00 daily maintenance run, the Sunday full ELO recalc), which is the natural grain for "is this the same recurring problem" — shortening it was out of scope and not justified by anything found this session.

**Not touched, per explicit scope constraints:**
- The `generic_error` classifier-shadowing issue (`log_monitor.py`'s `error_patterns` dict ordering) — cosmetic mislabeling, not a memory or correctness bug, left alone.
- Every `sqlite3.connect(..., timeout=30.0)` call site — the blocking-call mechanism behind the burst loop and the SIGTERM hang. Bigger blast radius, separate task.
- `TelegramHealthBot.last_alert_time` — see Part 1's new finding above; reported, not fixed, per the operator's explicit scope decision.

---

## Part 3 — Verification (`tests/test_error_parser_pruning.py`, run via `run_tests.py`)

23 checks, all passing. All three required demonstrations are covered:

**1. Prune actually drops old entries from both structures, no orphaned keys** (Section 1, T1a–T2e):
Built a 4-error `ErrorParser` state: one signature with only an old (30h) instance, one signature with both an old (30h) and a recent (1h) instance, and one signature with only a recent instance. After `clear_old_errors(hours=24)`:
- `error_history` drops from 4 to 2 (only the recent instances survive).
- The fully-expired signature's key is **absent** from `error_groups` entirely — not present as an empty list. This was checked explicitly (`old_only.signature not in p.error_groups`) because an empty-list-but-present key would itself be a slow, permanent, if smaller, leak (one dict key that never goes away). The rebuild (`error_groups = defaultdict(list)` then repopulate from the pruned `error_history`) does not produce this — confirmed correct.
- The partially-expired signature's group correctly shrinks to just its one surviving instance.
- A blanket check (`all(len(v) > 0 for v in p.error_groups.values())`) confirms no empty-valued keys exist anywhere after a prune.

**2. Non-tautology — grown without the call, bounded with it** (Section 2, T3a–T3d):
The same `ErrorParser`, run through 500 `add_error()` calls with 30-hour-old timestamps (a stand-in for days of unattended accumulation), asserted to hold all 500 in both structures *before* `clear_old_errors()` is called — proving the growth is real, not something the test setup already prevented. Then `clear_old_errors(hours=24)` is called on the *same* object, and both structures are asserted to drop to zero. A test that passed regardless of whether the method ran would not have distinguished these two states; this one explicitly asserts the "before" state grew, which only a test that could fail on the unfixed code proves anything.

**3. Grouping/dedup still works correctly after a prune** (Section 3, T4a–T5d):
Two scenarios, matching the two ways a signature can emerge from a prune:
- *Fully expired*: a signature with only an old instance, pruned to nothing, then a new occurrence arrives. Confirmed it starts a fresh single-entry group (not appended to a stale reference, not silently dropped, not erroring), with `occurrences == 1` on the new representative — not inflated by the count that existed before expiry.
- *Partially expired*: a signature with one old and one recent instance (occurrence counter reaches 2 on the original head before the prune, confirmed). After pruning, the recent instance is the sole survivor and becomes the group's new head. A third occurrence is added, and is confirmed to append correctly to the surviving group (`[sig_b_recent, sig_b_newest]`) — proving `error_groups[signature][0]` still resolves to a *live*, mutation-tracking object after the rebuild, not a stale reference into the discarded pre-prune list. Its occurrence counter increments from its own baseline (1 → 2), which is `add_error()`'s existing, unmodified behavior (only the group's head element accumulates a running count) — worth calling out explicitly because it is easy to mis-assert here: an early version of this test wrongly expected the counter to continue the *pre-prune* cumulative total, and the test itself caught that as a real failure before the assertion was corrected. The code was right; the first draft of the test was wrong about it.

Additional coverage, not required but added for completeness:
- Section 4 (T6a–T6c) asserts the wiring itself by reading `_health_check_loop`'s and `_log_monitor_loop`'s source (`inspect.getsource`) — confirms the call is present in the former and absent from the latter, and that `LogMonitor.clear_old_errors` is untouched.
- Section 5 (T7a–T7b) times a prune over 2,000 entries (well above the observed 454-per-boot rate) and confirms it completes in well under a second, backing the "does not itself block" claim in Part 2.

Run standalone: `python3 tests/test_error_parser_pruning.py` → 23/23 pass. Run via the project's runner: `python3 run_tests.py` picks it up automatically via the `tests/test_*.py` glob, no runner changes needed.

---

## Part 4 — What this does and does not fix

**Fixes:** the unbounded growth of `ErrorParser.error_history` and `ErrorParser.error_groups`. Once the observer restarts and runs with this change, those two structures will be re-bounded to a rolling 24-hour window every ~60 seconds instead of growing for the process's entire lifetime.

**Does NOT fix, explicitly:**
- **The burst-flush loop itself** (blocking `sqlite3.connect(timeout=30.0)` calls made synchronously inside `async def` coroutines, starving the single-threaded event loop and causing `asyncio.sleep(60)` timers to back up and fire in bursts). This fix does not touch any `sqlite3` call. The bursts will continue to happen at whatever cadence DB contention produces them; they will simply no longer leave behind unbounded amounts of retained `ErrorDetail` state afterward.
- **The SIGTERM hang.** Same root mechanism (a blocking C-level call preventing the interpreter from acting on a delivered signal) as the burst loop. Entirely untouched by this change.
- **`TelegramHealthBot.last_alert_time`** — the second unbounded accumulator found during Part 1's verification pass, reported but explicitly left unfixed at the operator's direction (see Part 1).
- **The `generic_error` classifier-shadowing cosmetic issue** — untouched, as scoped.

**The fix is inert until the observer restarts.** `self.error_parser` is constructed once, at process start (`LogMonitor.__init__` → `ErrorParser()`), and the newly-added call only prunes whatever accumulates *after* this code is running. It does not retroactively shrink whatever `error_history`/`error_groups` already hold in the live process's memory right now. **The observer was not restarted as part of this task**, per explicit scope — and its last four restarts (2026-09-07 ×2, 2026-09-12 ×2) each hung on SIGTERM and required a SIGKILL, a pattern the companion diagnosis document explains but does not resolve. Restarting it remains Oscar's call, separately from this fix landing in the source tree.

**Stated expectation, to check against after a restart happens:** once the observer is restarted (whenever that is decided) and runs with this change, its RSS should **stop growing past a stable ceiling instead of climbing indefinitely with uptime**. It should not immediately look small — a freshly-restarted process, per the diagnosis's own prior data point, sits around 168–250 MB baseline before any errors accumulate — but where the pre-fix process reached 11.6 GB after roughly 2h16m of uptime on a bad day (and only 378.9 MB after 45 minutes, consistent with roughly-linear growth over time), the post-fix process should plateau within, at most, a 24-hour retention window's worth of accumulated `ErrorDetail` objects at the system's observed error rate (454 detected errors in ~25 hours on the day this was diagnosed) and hold roughly steady from there, indefinitely, regardless of how long the process stays up. A restarted process still climbing well past that order of magnitude, or still tracking uptime linearly over multiple days, would mean either this fix isn't reaching a live `error_parser` instance as expected, or a different accumulator (plausibly `last_alert_time`, or something not yet found) is also contributing meaningfully.
