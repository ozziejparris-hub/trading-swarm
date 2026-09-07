# Telegram Remediation — Make It a Bug-Only Channel

**Scope:** implements the fixes named in
[[2026-09-07-telegram-alert-audit]] (`c3d8c6c`). Standard being enforced:
Telegram carries only messages Oscar would act on; silence means nothing
needs attention. Two items explicitly deferred per the task (DB-size
threshold, consolidated digest) — not touched. All code changes committed
to first-repo (`51e3b74`); this document is the decision record.

Tagging: [V]=verified this session (code read/run directly, or a live
query), [I]=inferred.

---

## VERDICT

All six parts implemented and verified. **Not restarted**:
`polymarket-observer.service` needs a restart to load
`monitoring/system_observer.py`/`monitoring/diagnostics.py`'s changes —
this session stopped short of restarting a live production service without
asking first (see the note at the end). `check_canonical_definitions.py`
needs no restart — cron launches a fresh Python process every run, so
tomorrow's 06:00 UTC daily-maintenance run picks up the fix automatically.

**Verified live, today's actual data**: after Part 4a's fix, the
diagnostic engine's `overall_status` is now **WARNING**, not CRITICAL
(`issues: []`, `warnings: ['[DATABASE] Database very large: 19742 MB',
'[DATA_QUALITY] Last trade 2.3h ago']`) — meaning the diagnostic report
would send **zero** messages under the new gate even on its very first
post-restart cycle, not just on repeats. This wasn't assumed; it was
confirmed by re-running `ELOSystemDiagnostics.run_full_diagnostic()`
directly against the live DB after the edit.

---

## PART 1 — Hourly report gate: fixed and proven

**Change** (`monitoring/system_observer.py`): extracted the inline
condition into a static, directly-testable method:

```python
@staticmethod
def _should_send_hourly_report(metrics: Dict) -> bool:
    return metrics.get("health_status") != "healthy" or metrics.get("error_count", 0) > 0
```

(was `metrics.get("status")` — a key `_collect_metrics()` never sets).
The loop now calls `self._should_send_hourly_report(metrics)`.

**Proof it now suppresses** (not assumed): run directly against a
synthetic healthy dict —
```
_should_send_hourly_report({"health_status": "healthy", "error_count": 0}) -> False
```
— and against the exact shape the old bug would have mishandled (a dict
that has a `"health_status"` key but no top-level `"status"` key, which is
what `_collect_metrics()` actually returns) — confirms the fix, not just
that the code compiles. Six cases covered in
`tests/test_telegram_alert_gating.py` §1, including a regression guard
(T1f) that a stray `"status"` key must not influence the gate.

---

## PART 2 — Diagnostic report: gated on CRITICAL + finding-set change

**Persistence choice: a flat JSON file**,
`data/.diagnostic_report_state.json`, not a DB table. Reasons: (a) the
audit found the observer's existing in-memory metrics history
(`PerformanceMonitor.metrics_history`) resets on every restart — a file
survives restarts, which is the whole point; (b) this project already has
a working precedent for exactly this kind of small "last-observed-state"
file (`data/.last_requeue_run`, tracked in git); (c) a DB table would mean
a new writer against the production schema, which is exactly the kind of
change the task's own stop condition warns needs its own decision — a flat
file needs no schema, no migration, no new writer contract.

**Signature normalization**: findings are compared after stripping numeric
tokens (`re.sub(r"\d+(\.\d+)?", "#", text)`), so `"Database very large:
19742 MB"` and `"...19758 MB"` compare equal. Without this, the DB-size
warning's embedded byte count (which changes every single cycle, since the
DB only grows) would make the signature look "changed" every 6 hours
forever — silently defeating the entire point of Part 2 for exactly the
warning Part 4c names.

**Gate**:
```python
if overall_status != 'CRITICAL':
    return False
if previous_signature is None:
    return True
return current_signature != previous_signature
```
Persisted **every cycle**, whether or not a send happens — so a later
transition (issue clears, then a different issue appears) is compared
against the actual last-observed state, not just the last time an alert
fired.

**Duplicate message removed**: the separate `"🚨 CRITICAL SYSTEM ISSUES
DETECTED"` second message that used to fire alongside every CRITICAL
report is gone — `_send_diagnostic_report` is now the only call.

**Verified** (`tests/test_telegram_alert_gating.py` §2, 8 cases): fresh
run with no persisted state sends; an identical CRITICAL set repeating
does NOT send (this is the literal 228-cycles-of-noise case); a genuinely
new issue sends; a previously-reported issue clearing while another
remains CRITICAL still counts as changed and sends; a WARNING-only cycle
never sends regardless of novelty; a HEALTHY cycle never sends.

**Explicit design tradeoff, not fixed further**: recovering from CRITICAL
to WARNING/HEALTHY does **not** itself produce an "all clear" message —
the gate's first condition (`overall_status != 'CRITICAL' → no send`)
blocks it. This is the task's literal spec (Part 2 lists three bullet
conditions that combine this way), not an oversight; flagged here and again
in "what was not determined" since it's a real, deliberate limitation of
the chosen design, not a bug.

---

## PART 3 — check_canonical_definitions.py: fixed and change-gated

**Credential fix**: added
```python
from dotenv import load_dotenv
load_dotenv("/home/parison/.env_trading")
```
inside `send_telegram_alert()`, matching `audit_invariants.py:1001`
exactly. Confirmed this is the *only* sender across both repos with this
specific gap (audit Part 2).

**Change detection**: `violation_signature()` builds a sorted
`(relative_path, message)` list — **deliberately excludes line number**,
so a violation whose line shifted because of an unrelated edit elsewhere
in the file isn't treated as "new." Persisted to
`data/.canonical_drift_state.json`. `should_alert()` fires only if
violations exist AND the signature changed since the last observed run.

**Verified live, not just unit-tested** — ran the actual script twice:
```
$ python3 scripts/check_canonical_definitions.py --alert     # first run, no prior state
...
[TELEGRAM] Alert sent.
$ python3 scripts/check_canonical_definitions.py --alert     # second run, same 7 violations
...
[check_canonical_definitions] unchanged from last observed run — suppressing alert
```
Confirmed the credentials genuinely weren't already present in the
executing shell (`env | grep telegram_alerts_token` → empty) before
running this, so the successful send is attributable to the new
`load_dotenv()` call, not an accidental pre-existing export.

**The 7 violations themselves were not touched** — `data/
.canonical_drift_state.json` now holds their real current signature, so
the *next* change (fixed or new) is what will actually alert.

---

## PART 4 — False alarms retired

**(a) `integrate_behavioral_elo.py` existence check.** Removed from
`monitoring/diagnostics.py`'s `analysis_scripts` dict, with an inline
comment recording why and when. **Checked the other four entries against
the live repo before removing anything** (per the stop condition):

| Entry | Path | Status |
|---|---|---|
| Behavioral Analysis | `analysis/trading_behavior_analysis.py` | EXISTS |
| Weighted Metrics | `analysis/calculate_weighted_metrics.py` | EXISTS |
| Performance Analysis | `analysis/trader_performance_analysis.py` | EXISTS |
| ELO Verification | `scripts/simulation/verify_elo_rankings.py` | EXISTS |

Only the one entry named in the task was missing; no stop condition
triggered here.

**(b) ELO coverage metric.** Removed the `"ELO coverage: {...}%"` line from
`_send_diagnostic_report`'s message body (`system_observer.py`). **Other
consumers checked first** (`grep -rn "elo_coverage"` across both repos):
exactly one other reference, inside `diagnostics.py`'s own
`check_elo_calculation_health()` — two `issues`/`warnings` branches
(`< 0.5` / `< 0.8` thresholds) that were already permanently unreachable
(the value is structurally always ≥100%, confirmed live: 194,415/66,972 =
290.3%). Not touched — removing dead branches that were never asked about
risks scope creep beyond "remove from the diagnostic report"; noted here
so it's visible rather than silently left.

**(c) Database-size warning.** Threshold **not changed** (confirmed).
Verified directly what Part 2's gate now does with it: since it's a
`warning`, not an `issue`, it never independently triggers a send (the
gate requires `overall_status == 'CRITICAL'`); when a send *does* happen
for another reason, the warning still appears in the message body in full
(the message-builder's warnings section is untouched) — visible without
being an alert trigger on its own, exactly as the task specified.

---

## PART 5 — Unconditional digests paused

Commented out (not deleted) in `system_observer.py`'s `run()` task list:
```python
# PAUSED 2026-09-07 (bug-only Telegram channel remediation) — daily
# report (23:00 UTC unconditional digest, no health gate) and
# weekly report loop. Purely informational scheduled sends have no
# place on a channel meant to carry only actionable findings.
# Reversible: uncomment the two lines below. Ledger:
# brain/decisions/2026-09-07-telegram-remediation.md Part 5.
# asyncio.create_task(self._daily_report_loop()),
# asyncio.create_task(self._weekly_report_loop()),
```
Matches the `138c03b` precedent (dated PAUSED comment, reversible,
ledgered). Startup print lines updated to say `PAUSED 2026-09-07` instead
of `enabled`, so the observer's own startup log is honest about what's
running. The two loop functions themselves are untouched (kept intact,
each now carries a `NOT CURRENTLY SCHEDULED` docstring note) — re-enabling
is exactly uncommenting the two task lines.

**Not touched, per scope**: the health-check loop (correctly gated),
`audit_invariants.py`, and every event-driven alert (insider detection,
consensus positions/exits, legendary trades, trend alerts).

---

## PART 6 — Verification: what Telegram would send today

**Diagnostic report (6h loop)**: **zero** sends expected today.
`overall_status` is now WARNING (Part 4a's fix removed the only issue),
and WARNING never sends under the new gate regardless of novelty —
confirmed by re-running the real diagnostics engine against the live DB
after the edit, not assumed from the code alone.

**Hourly report**: expected **~0**, occasionally 1, matching the 96.2%
HEALTHY rate the audit measured over the last 7 days of real per-minute
health checks — confirmed the live observer's health check is currently
reporting HEALTHY continuously (checked journalctl's most recent ~25
entries, all HEALTHY, as of this session).

**`check_canonical_definitions.py`** (once daily, 06:00 UTC cron): **zero**
sends expected tomorrow, since this session's run already persisted the
current 7-violation signature — tomorrow's run will see the identical set
(unless someone edits those 6 files first) and suppress.

**Not zero — one sender still fires, and this is expected, not a leftover
bug**: **`audit_invariants.py`**, unchanged by this task per its own
scope. Today's actual daily-maintenance run (visible in
`logs/daily_maintenance.log`) found 5 REGRESSION-tier invariants (stale
timestamp formats, `data_source` not canonical, `total_invested` mismatch,
etc. — the same chronic set the 2026-09-07 status check reported this
morning) and its alert **did** send. This sender was explicitly named in
Part 5 as staying as-is (it already gates correctly — it only ever sends
when something is actually wrong), so it will keep firing daily for as
long as those regressions remain open. **Whether `audit_invariants.py`
itself re-sends the same regressions identically every day (the same noise
pattern this task eliminated elsewhere) was not assessed — out of scope,
not touched.**

**Senders remaining live and what each now alerts on:**

| Sender | Fires on |
|---|---|
| `audit_invariants.py` | Any REGRESSION/CRITICAL data invariant (unchanged) |
| `check_canonical_definitions.py` | A **changed** hardcoded-threshold violation set (fixed + gated this session) |
| Hourly report | Non-healthy `health_status`, or `error_count > 0` (fixed this session) |
| Diagnostic report | `overall_status == CRITICAL` AND the finding set changed (fixed this session) |
| Health-check loop | Any non-healthy status transition (unchanged, already correct) |
| Log-monitor / error alerts | Detected error patterns (unchanged, event-driven) |
| Insider detection, consensus positions/exits, legendary trades, trend alerts | Detected real-world patterns (unchanged, event-driven) |
| Monitoring-freeze alert | `minutes_since_activity > 45` (unchanged) |
| `orchestrator.py` (trading-swarm) | Per-call-site conditions, not re-audited this session |
| `run_feedback_loop_agent.py`, `polymarket_changelog_monitor.py` | Weekly cron reports (unchanged, not in scope of "bug-only" — these are trading-swarm's own weekly summaries, not part of this task) |

**Remain silent, deliberately, per scope**: `monitor.py`'s elite-trader
feed (`elo_bot`/`telegram` = `None` since 2026-01-27 — a product decision,
not re-enabled), `background_pnl_worker.py`'s PNL-skip alert (same
lineage), `detect_counter_signals.py`/`register_signal.py` print-only
stubs (unfinished features, not wired), `analysis_scheduler.py` (not
invoked anywhere).

---

## What changed and where (summary)

| File | Change |
|---|---|
| `monitoring/system_observer.py` | Hourly gate key fix + extracted static method; diagnostic-report change-detection (signature/persistence/gate methods); removed duplicate CRITICAL message; removed ELO-coverage line from diagnostic message; paused daily/weekly report task creation (commented, dated) |
| `monitoring/diagnostics.py` | Removed the `'ELO Integration'` stale-file-check entry |
| `scripts/check_canonical_definitions.py` | Added `load_dotenv()`; added violation-signature change-detection |
| `tests/test_telegram_alert_gating.py` | New — 20 tests, 3 sections, negative controls throughout |
| `data/.canonical_drift_state.json` | New — persisted violation signature (real data: today's 7 violations) |
| `data/.diagnostic_report_state.json` | Not yet created — written lazily on the observer's first post-restart diagnostic cycle |

Committed: first-repo `51e3b74`. Full suite via `run_tests.py`: 21 files,
20 passed, 1 pre-existing unrelated failure
(`test_backtest_window_population.py` — same chronic failure every run
this week, not touched).

**Not restarted**: `polymarket-observer.service` must be restarted for
`system_observer.py`/`diagnostics.py`'s changes to take effect (the running
process has the old code loaded in memory). `check_canonical_definitions.py`
needs no restart (fresh subprocess every cron run). Restarting a live
production service wasn't authorized by this task's scope, so it was not
done — flagged for a decision rather than assumed.

---

## What was not determined

- Whether `audit_invariants.py` has its own noise problem (re-sending
  identical regressions daily) — explicitly out of scope for this task
  (Part 5 named it as staying as-is), not assessed.
- Whether `trading-swarm/orchestrator/orchestrator.py`'s `send_telegram`
  call sites are themselves well-gated — only its credential path was
  previously verified (the earlier audit); not re-examined here.
- The design tradeoff named in Part 2 (no "all clear" message when a
  CRITICAL condition fully resolves) is a known, deliberate limitation of
  the literal spec as given, not something this session chose to fix
  further or was asked to.
- Whether `data/.diagnostic_report_state.json`'s first real write (after
  the next observer restart) behaves as tested — verified via direct
  function calls and a live dry-run of the diagnostics engine, but the
  actual persisted-file round-trip inside the running `polymarket-observer`
  process was not observed end-to-end (the service hasn't been restarted
  yet).
- Whether restarting `polymarket-observer.service` now is wanted — these
  changes are inert until it restarts; this decision is Oscar's, asked
  separately rather than assumed.
