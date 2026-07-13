# Integration Test Report — 2026-07-12

## Result: ❌ 7 FAILURES (38/45 passed — 84.4%)

## Test Summary
Total tests: 45
Passed: 38
Failed: 7
Pass rate: 84.4%
Run started: 2026-07-12T23:01:27Z

---

## ❌ Failures (action required)

### FAILURE 1 — CI Pipeline: ModuleNotFoundError in 3 new test files
- **Suite:** 5 — CI Pipeline Integrity
- **Test:** `ci_pipeline_passes`
- **What failed:** Three test files added on 2026-07-10 and 2026-07-11 (`test_brain_writers_atomicity.py`, `test_cross_repo_lock.py`, `test_json_safety.py`) import `orchestrator.orchestrator` and `orchestrator.json_safety` as a Python package, but `orchestrator/__init__.py` does not exist. Pytest cannot collect any tests — 0 tests ran. Separately, `test_json_safety.py:200` has an `F841` lint error (`real_write` assigned but never used).
- **Recommended fix:**
  1. `touch /home/parison/trading-swarm/orchestrator/__init__.py` — makes `orchestrator/` a proper Python package (the 3 new test files will then import correctly)
  2. Remove or use the `real_write` variable at `tests/test_json_safety.py:200` to clear the F841 lint error
- **Severity:** CRITICAL
- **Consecutive failures:** **10th Sunday** — CI has now failed every Sunday since 2026-05-12. Nature of failure changed this week: previous F541/E722 lint errors in `calculate_geo_elo.py` and `run_trader_profiling.py` appear to have been fixed, but 3 new test files added Jul 10-11 introduced two new CI blockers. The 10-week streak means this is SYSTEMIC per Rule 6.
- **Note:** This week 0 tests ran (collection failed); last week 27 tests passed. The test suite grew from 27 to 110 tests (8 files) this week but all execution is blocked.

---

### FAILURE 2 — signal-agent dark for 158.9 hours
- **Suite:** 2 — Agent Output Integrity
- **Test:** `signal-agent_output_recent`
- **What failed:** Last output was `2026-07-06-08-signal-report.md` (158.9 hours ago). Cadence limit is 4 hours. The agent registry confirms `status: "failed"` with `retries: 1` — the orchestrator's immune system has already noted the failure but has not resolved it. STR-003 July signals (including the Peruvian election markets resolved July 7+) remain unscanned and unscored.
- **Recommended fix:** Oscar to manually respawn signal-agent via `scripts/spawn_agent.sh`. The task `signal-202606042140` in the registry is stale (started June 4, failed) — clear it and issue a new scan task.
- **Severity:** CRITICAL
- **Consecutive failures:** **8th+ consecutive Sunday**. SYSTEMIC.

---

### FAILURE 3 — quant-research-agent dark for 821.7 hours (34 days)
- **Suite:** 2 — Agent Output Integrity
- **Test:** `quant-research-agent_output_recent`
- **What failed:** Last output was `geo_elo_findings.md`, written 34+ days ago. Cadence limit is 72 hours. RQ-GEO-ELO-001 Phase 1 (approved by Oscar on 2026-05-25) has never been executed. This directly blocks Phase 5 Gate 4 (RQ1.1 and RQ3.2 validation) and thus blocks all of Phase 6.
- **Recommended fix:** Spawn quant-research-agent with task: execute RQ-GEO-ELO-001 Phase 1. Approved hypothesis exists in `brain/strategy-notes/`. Pre-registration requirement is already satisfied.
- **Severity:** HIGH
- **Consecutive failures:** **6th+ consecutive Sunday**. SYSTEMIC.

---

### FAILURE 4 — backtest-agent dark for 1014.4 hours (42 days)
- **Suite:** 2 — Agent Output Integrity
- **Test:** `backtest-agent_output_recent`
- **What failed:** Last output was `LH-001-validation-v2.md`, written 42+ days ago. Cadence limit is 168 hours (weekly). No STR-003 or later-strategy backtests have been run.
- **Recommended fix:** Backtest-agent requires quant-research output before running (Gate dependency). Fix Failure 3 first; backtest-agent can then pick up quant-research findings.
- **Severity:** HIGH
- **Consecutive failures:** **6th+ consecutive Sunday**. SYSTEMIC.

---

### FAILURE 5 — feedback.json not updated in last 7 days
- **Suite:** 3 — Feedback Loop Integrity
- **Test:** `feedback_updated_recently`
- **What failed:** 0 approved/rejected entries and 0 scout_cycles with dates in the last 7 days. feedback.json has 4 approved and 1 rejected entry (all structurally intact), but none are recent. The feedback-loop-agent has not run since at least 2026-07-05.
- **Recommended fix:** feedback-loop-agent should run weekly (Sunday morning, before this agent). Check cron entry. Last known run was `feedback-loop-agent-20260627` approximately. Schedule or manually trigger Run #11 this week.
- **Severity:** HIGH
- **Consecutive failures:** **4th consecutive Sunday**. SYSTEMIC.

---

### FAILURE 6 — `validation_complete` and `str003_directional_single` absent from signal bus (last 7 days)
- **Suite:** 1 — Signal Bus Integrity
- **Test:** `expected_signal_types_present`
- **What failed:** The last 7 days of signals contain only `revalidation_requested` and `telegram_notification`. Missing: `validation_complete` (feedback-loop-agent not running), `str003_directional_single` (signal-agent dark). Signal bus is active but carrying only scaffolding traffic, not substantive research signals.
- **Recommended fix:** Flows from Failures 2 and 5 — fix signal-agent and feedback-loop-agent to restore these signal types.
- **Severity:** MEDIUM
- **Consecutive failures:** **3rd consecutive Sunday**. SYSTEMIC.

---

### FAILURE 7 — research-scout-agent 1 hour over cadence
- **Suite:** 2 — Agent Output Integrity
- **Test:** `research-scout-agent_output_recent`
- **What failed:** Last output (`2026-07-11-20-us-army-master-sergeant-charged-in-first-federal-p.md`) is 27.0 hours old; cadence limit is 26 hours. 1 hour over threshold.
- **Recommended fix:** Monitor next cycle — if still over, check cron timing. This is likely borderline timing noise on the daily run.
- **Severity:** MEDIUM
- **Consecutive failures:** 1st occurrence (not systemic yet). Monitor.

---

## ✅ Passed Suites

**Suite 1 — Signal Bus (3/4 passed):** Bus is not empty (20 signals). No stuck signals (all pending signals processed within 48h). Validation pipeline complete (all `validation_requested` signals have matching `validation_completed`). Only failure: expected operational signal types missing from last 7 days (see Failure 6).

**Suite 3 — Feedback Loop (3/4 passed):** Feedback file has 5 entries (4 approved, 1 rejected). Rejection reasons are specific (STR-001 reason is 127 chars). No repeated failures detected. Only failure: staleness (no recent entries — see Failure 5).

**Suite 4 — Registry Consistency (3/3 passed):** No phantom tasks (registry matches tmux sessions). No ghost sessions. No stale completed tasks older than 30 days. Registry is clean.

**Suite 5 — CI Pipeline (5/6 passed):** All 4 CI scripts exist and are executable. 110 tests defined across 8 test files (substantial growth from 27 tests last week). CI execution fails before running any tests (see Failure 1).

**Suite 6 — Brain Integrity (14/14 passed):** All 10 critical brain files exist and are non-empty. All 3 JSON files (signals.json, feedback.json, agent_registry.json) are valid JSON. Brain directory is 4.72 MB and growing.

**Suite 7 — Integration Contract (4/4 passed):** DB connected successfully. WAL mode confirmed active. Clean pool: 26,645 traders (min 10,000 — healthy). Clean markets: 223,651 (min 16,000 — dramatically exceeding threshold, up from 92,144 last week). First-repo database is in excellent health.

---

## Suite Details

### Suite 1 — Signal Bus Integrity (3/4)

| Test | Result | Detail |
|------|--------|--------|
| signal_bus_not_empty | ✅ PASS | 20 signals in bus |
| no_stuck_signals | ✅ PASS | All signals processed |
| expected_signal_types_present | ❌ FAIL | Missing: `validation_complete`, `str003_directional_single` |
| validation_pipeline_complete | ✅ PASS | All validation requests have completions |

Recent signal types found (last 7 days): `revalidation_requested`, `telegram_notification`

---

### Suite 2 — Agent Output Integrity (6/10)

| Agent | Recency | File Size |
|-------|---------|-----------|
| signal-agent | ❌ 158.9h (max 4h) | ✅ 9,960 bytes |
| quant-research-agent | ❌ 821.7h (max 72h) | ✅ 3,641 bytes |
| backtest-agent | ❌ 1,014.4h (max 168h) | ✅ 16,548 bytes |
| research-scout-agent | ❌ 27.0h (max 26h) | ✅ 1,265 bytes |
| performance-analyst-agent | ✅ 160.9h (max 168h) | ✅ 15,268 bytes |

---

### Suite 3 — Feedback Loop Integrity (3/4)

| Test | Result | Detail |
|------|--------|--------|
| feedback_file_has_entries | ✅ PASS | 4 approved, 1 rejected |
| feedback_updated_recently | ❌ FAIL | 0 entries in last 7 days |
| rejection_reasons_specific | ✅ PASS | All rejection reasons specific |
| no_repeated_failures | ✅ PASS | No repeated failures |

---

### Suite 4 — Registry Consistency (3/3)

| Test | Result | Detail |
|------|--------|--------|
| no_phantom_tasks | ✅ PASS | Registry matches tmux sessions |
| no_ghost_sessions | ✅ PASS | No ghost sessions |
| registry_not_stale | ✅ PASS | Registry is clean |

Active registry tasks: 2 (`signal-202606042140` status=failed, `integration-20260712` status=running)

---

### Suite 5 — CI Pipeline Integrity (5/6)

| Test | Result | Detail |
|------|--------|--------|
| ci/run_ci.sh exists+executable | ✅ PASS | OK |
| ci/lint.sh exists+executable | ✅ PASS | OK |
| ci/run_tests.sh exists+executable | ✅ PASS | OK |
| ci/validate_backtest.py exists+executable | ✅ PASS | OK |
| ci_pipeline_passes | ❌ FAIL | ModuleNotFoundError: `orchestrator/__init__.py` missing; F841 lint in test_json_safety.py:200 |
| test_suite_has_coverage | ✅ PASS | 110 tests across 8 test files |

CI error detail:
```
tests/test_brain_writers_atomicity.py — ModuleNotFoundError: No module named 'orchestrator'
tests/test_cross_repo_lock.py — ModuleNotFoundError: No module named 'orchestrator'
tests/test_json_safety.py — ModuleNotFoundError: No module named 'orchestrator'
tests/test_json_safety.py:200 — F841 local variable 'real_write' assigned but never used
```
Three new test files added 2026-07-10/07-11 require `orchestrator/__init__.py` to exist (the orchestrator directory is not yet a Python package). This is a two-line fix.

---

### Suite 6 — Brain Integrity (14/14)

| Test | Result | Detail |
|------|--------|--------|
| signals.json exists | ✅ PASS | 69,590 bytes |
| feedback.json exists | ✅ PASS | 44,012 bytes |
| priorities.md exists | ✅ PASS | 6,548 bytes |
| kpis.md exists | ✅ PASS | 16,472 bytes |
| definition_of_done.md exists | ✅ PASS | 2,089 bytes |
| model-routing.md exists | ✅ PASS | 24,299 bytes |
| research-directions.md exists | ✅ PASS | 76,241 bytes |
| ml-in-finance-notes.md exists | ✅ PASS | 26,423 bytes |
| lopez-de-prado-notes.md exists | ✅ PASS | 39,101 bytes |
| ernest-chan-algo-trading-notes.md exists | ✅ PASS | 48,759 bytes |
| json_valid signals.json | ✅ PASS | Valid JSON |
| json_valid feedback.json | ✅ PASS | Valid JSON |
| json_valid agent_registry.json | ✅ PASS | Valid JSON |
| brain_has_content | ✅ PASS | 4.72 MB |

---

### Suite 7 — Integration Contract / first-repo (4/4)

| Test | Result | Detail |
|------|--------|--------|
| contract_db_connectable | ✅ PASS | Connected to polymarket_tracker.db |
| contract_wal_mode | ✅ PASS | journal_mode=wal |
| contract_clean_pool | ✅ PASS | 26,645 traders (min 10,000) |
| contract_clean_markets | ✅ PASS | 223,651 markets (min 16,000) |

Note: clean_markets surged from 92,144 (Jul 5) to 223,651 (+141K in one week). Clean pool grew from 30,096 to 26,645 (slight decrease — possible new research_excluded flags). Both metrics remain well above contract minimums.

---

## Consecutive Failure Tracker

| Failure | Jun 28 | Jul 5 | Jul 12 | Status |
|---------|--------|-------|--------|--------|
| CI pipeline | 8th | 9th | **10th** | SYSTEMIC — CRITICAL |
| signal-agent cadence | 6th+ | 7th+ | **8th+** | SYSTEMIC — CRITICAL |
| quant-research cadence | 4th+ | 5th+ | **6th+** | SYSTEMIC — HIGH |
| backtest-agent cadence | 4th+ | 5th+ | **6th+** | SYSTEMIC — HIGH |
| feedback_updated_recently | 2nd | 3rd | **4th** | SYSTEMIC — HIGH |
| expected_signal_types_present | 1st | 2nd | **3rd** | SYSTEMIC — MEDIUM |
| research-scout cadence | — | — | **1st** | WATCH |

All 6 tracked recurring failures are now SYSTEMIC. New this week: the CI failure changed character (no longer F541 lint errors — those appear fixed — now import errors from new test files added Jul 10-11).

---

## System Health Assessment

The system's structural layer is in good shape. Brain integrity is 100% — all 10 critical files present and valid. The integration contract is comfortably satisfied with 223,651 clean markets (14× the minimum), and the signal bus is structurally sound with no stuck signals. Registry is clean and consistent with actual tmux state.

The operational layer tells a different story. Six of seven tracked failure categories are now SYSTEMIC, meaning they have persisted through three or more consecutive Sundays. The CI pipeline has now failed for ten consecutive Sundays — a record — and this week's failure has a different cause than the previous nine: three new test files added on 2026-07-10 and 2026-07-11 import `orchestrator` as a Python package, but `orchestrator/__init__.py` does not exist. The old lint errors (F541 and E722) may have been fixed, but two new blockers took their place. The fix is `touch orchestrator/__init__.py` plus removing one unused variable — under five minutes of work.

The research pipeline (signal-agent → quant-research → backtest) has been effectively frozen since early June. The signal-agent is in the registry as `status: failed`; no new STR-003 signals have been scored since July 6; RQ-GEO-ELO-001 Phase 1 (approved May 25) remains unexecuted; and backtest-agent hasn't run in 42 days. This chain is the primary blocker for Phase 5 Gate 4 and thus all of Phase 6.

The single clearest priority for the week ahead: (1) fix CI in five minutes (`touch orchestrator/__init__.py` + remove one variable), then (2) manually respawn the signal-agent, then (3) execute RQ-GEO-ELO-001 Phase 1. The database is healthy, the brain is intact, the registry is clean — the infrastructure is ready. The bottleneck is agent execution.

---

*Report generated: 2026-07-12 23:05 UTC | Agent: integration-test-agent | Task: integration-20260712 | Model: claude-sonnet-4-6 (Tier 3)*
