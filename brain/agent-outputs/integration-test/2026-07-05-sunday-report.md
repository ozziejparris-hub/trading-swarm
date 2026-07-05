# Integration Test Report — 2026-07-05 (Sunday)

## Result: ❌ 7 FAILURES

## Test Summary
| Metric | Value |
|--------|-------|
| Total tests | 50 |
| Passed | 43 |
| Failed | 7 |
| Pass rate | 86.0% |

---

## ❌ Failures (action required)

### FAILURE 1 — CI Pipeline Failing
- **Test:** `ci_pipeline_passes`
- **Suite:** 5 — CI Pipeline Integrity
- **Severity:** CRITICAL
- **Consecutive Sundays:** 9 (SYSTEMIC — escalate HIGH)
- **Detail:**
  ```
  calculate_geo_elo.py:449,450,479,480,506,507,516,517 — F541 f-string is missing placeholders (8 errors)
  run_trader_profiling.py:271 — E722 do not use bare 'except' (1 error)
  9 total lint errors. 27/27 tests pass.
  ```
- **Recommended fix:**
  1. Open `scripts/calculate_geo_elo.py` and remove the `f` prefix from the 8 literal strings at lines 449, 450, 479, 480, 506, 507, 516, 517 (change `f"..."` → `"..."` where no `{}` placeholders exist)
  2. Open `scripts/run_trader_profiling.py:271` and replace bare `except:` with `except Exception:`
  3. Run `bash ci/run_ci.sh` to confirm clean — this is a 20-minute fix that has been open 9 weeks
- **Escalation:** YES — 9th consecutive Sunday, SYSTEMIC

---

### FAILURE 2 — Signal-Agent Dark 158.9 Hours
- **Test:** `signal-agent_output_recent`
- **Suite:** 2 — Agent Output Integrity
- **Severity:** HIGH
- **Consecutive Sundays:** 7+ (SYSTEMIC — escalate HIGH)
- **Detail:** Last output `2026-06-29-08-signal-report.md` (Jun 29 08:07 UTC). Age: 158.9h. Max cadence: 4h.
- **Context from Jun 29 report:** Signal-agent ran Jun 29 but failed to produce its Jul 6 weekly output. STR003-004 (Putin invasion NO) resolved Jun 30 — outcome needs scoring in strategy-registry.md. STR003-008 (Europe security NO) also resolved Jun 30 — needs scoring. STR003-001 (Newsom) still active, resolves Sept 1.
- **Recommended fix:** Oscar to manually trigger signal-agent run via `bash scripts/spawn_agent.sh signal-agent`. Confirm tmux session alive, Telegram notification fires, output written to `brain/agent-outputs/signal-agent/`. Score STR003-004 and STR003-008 in strategy-registry.md — both resolved Jun 30.
- **Escalation:** YES — 7th consecutive Sunday, SYSTEMIC

---

### FAILURE 3 — Quant-Research-Agent Dark 966.9 Hours (40 days)
- **Test:** `quant-research-agent_output_recent`
- **Suite:** 2 — Agent Output Integrity
- **Severity:** HIGH
- **Consecutive Sundays:** 5+ (SYSTEMIC — escalate HIGH)
- **Detail:** Last output in `GEO-ELO-003/` (May 26). Age: 966.9h. Max cadence: 72h.
- **Context:** RQ-GEO-ELO-001 (geo_elo Phase 1 calculation) was Oscar-approved May 25. Phase 1 has NEVER been executed. Phase 5 Gate 4 (RQ1.1 + RQ3.2) remains BLOCKED. This is the single highest-impact item for Phase 5 completion.
- **Recommended fix:** Spawn quant-research-agent with task: execute RQ-GEO-ELO-001 Phase 1 (compute geo_elo for all traders using Geopolitics + Elections trades only). Pre-registration is already complete. No additional approval needed — Oscar approved May 25. See `brain/strategy-notes/rq-geo-elo-preregistration-2026-05-25.md`.
- **Escalation:** YES — 5th consecutive Sunday, SYSTEMIC

---

### FAILURE 4 — Backtest-Agent Dark 846.4 Hours (35 days)
- **Test:** `backtest-agent_output_recent`
- **Suite:** 2 — Agent Output Integrity
- **Severity:** HIGH
- **Consecutive Sundays:** 5+ (SYSTEMIC — escalate HIGH)
- **Detail:** Last output `LH-001-validation-v2.md` (May 31). Age: 846.4h. Max cadence: 168h.
- **Context:** GEO-ELO-003 OOS verdict exists in `brain/agent-outputs/quant-research/GEO-ELO-003/` (May 26) but the corresponding backtest-agent validation report has never been written to the output directory. The pending `validation_requested` signal for `geo_eos` is marked "processed" but no formal output file exists.
- **Recommended fix:** Backtest-agent should write formal OOS validation verdict for GEO-ELO-003 to `brain/agent-outputs/backtest-agent/GEO-ELO-003-oos-validation.md`. This requires confirming whether the May 26 quant-research findings constitute a sufficient basis for the verdict, or whether additional analysis is needed.
- **Escalation:** YES — 5th consecutive Sunday, SYSTEMIC

---

### FAILURE 5 — Research-Scout Output 63.0 Hours (Cadence Breach)
- **Test:** `research-scout-agent_output_recent`
- **Suite:** 2 — Agent Output Integrity
- **Severity:** MEDIUM
- **Consecutive Sundays:** 1 (not systemic)
- **Detail:** Last output Jul 3 08:01 (63.0h ago). Max cadence: 26h. Scout ran Thursday Jul 3 but did not run Friday Jul 4 or Saturday Jul 5.
- **Context:** Two findings filed Jul 3 (per-market information leakage, Polymarket US retail API changes). Scout is operational — this is a timing issue not a dormancy issue.
- **Recommended fix:** Scout should resume normal daily cadence. No structural fix needed — verify cron schedule is running and scout is not stuck. Last output is substantive (873 bytes). Not urgent.

---

### FAILURE 6 — Feedback Loop Not Updated in 54 Days
- **Test:** `feedback_updated_recently`
- **Suite:** 3 — Feedback Loop Integrity
- **Severity:** MEDIUM
- **Consecutive Sundays:** 3+ (tracking from Jun 28 report)
- **Detail:** Most recent entry in `feedback.json` is scout_cycle dated 2026-05-12 (54 days ago). No feedback entries since mid-May. Feedback-loop-agent last ran June 5 (Run #10) but did not write a new scout_cycle entry.
- **Context:** Run #10 filed findings and met Phase 5 Gate 2. The feedback file's `scout_cycles` array tracks research-scout runs, which stopped updating after May 12. Research-scout should be updating this log each cycle — current cycles are being written to signals.json only.
- **Recommended fix:** Research-scout-agent should write a scout_cycle entry to `feedback.json` after each run (same pattern as cycles 1-13 through May 12). Feedback-loop-agent should run again before end of week (Run #11) to verify Jun 30 signals scored correctly and update feedback.json.

---

### FAILURE 7 — Expected Signal Types Absent in Last 7 Days
- **Test:** `expected_signal_types_present`
- **Suite:** 1 — Signal Bus Integrity
- **Severity:** MEDIUM
- **Detail:** No `revalidation_requested`, `validation_complete`, or `str003_directional_single` signals in the last 7 days (since Jun 28). Last 7 days had only: `integration_test_critical`, `telegram_notification`, `contract_stale`, `contract_violation`.
- **Context:** This failure is derivative of the signal-agent and feedback-loop dormancy (Failures 2 and 6). When those agents resume, expected signal types will reappear. Not independently actionable.
- **Recommended fix:** Resolves automatically when signal-agent and feedback-loop-agent resume normal operation.

---

## ✅ Passed Suites

| Suite | Tests | Result |
|-------|-------|--------|
| 1 — Signal Bus | 4 | 3/4 PASS — bus active, no stuck signals, validation pipeline intact |
| 2 — Agent Output | 15 | 11/15 PASS — performance-analyst barely within window (160.9/168h) |
| 3 — Feedback Loop | 4 | 3/4 PASS — entries exist, rejection reasons specific, no repeated failures |
| 4 — Registry Consistency | 3 | 3/3 PASS — no phantoms, no ghosts, no stale completed tasks |
| 5 — CI Pipeline | 6 | 5/6 PASS — all scripts present and executable, 27 tests pass |
| 6 — Brain Integrity | 14 | 14/14 PASS — all critical files present, all JSON valid, 3.94 MB |
| 7 — Integration Contract | 4 | 4/4 PASS — WAL mode, clean_pool=30,096, clean_markets=92,144 |

---

## Suite Details

### Suite 1 — Signal Bus Integrity

| Test | Result | Detail |
|------|--------|--------|
| signal_bus_not_empty | ✅ PASS | Multiple active signals in bus |
| no_stuck_signals | ✅ PASS | No signals with status=pending >48h (note: 2026-07-04 contract_violation has no status field — see observations) |
| expected_signal_types_present | ❌ FAIL | Missing: revalidation_requested, validation_complete, str003_directional_single |
| validation_pipeline_complete | ✅ PASS | No unmatched processed validation_requests |

**Note on 2026-07-04 contract_violation:** Training-librarian filed a contract_violation signal (pool_c=2,463 < 2,500) with no `status` field and no `processed_at`. This signal is technically unprocessed. Orchestrator should process it and mark pool_c investigation as pending.

### Suite 2 — Agent Output Integrity

| Agent | Dir Exists | Recent | Non-Empty | Age | Max |
|-------|-----------|--------|-----------|-----|-----|
| signal-agent | ✅ | ❌ FAIL | ✅ | 158.9h | 4h |
| quant-research-agent | ✅ | ❌ FAIL | ✅ | 966.9h | 72h |
| backtest-agent | ✅ | ❌ FAIL | ✅ | 846.4h | 168h |
| research-scout-agent | ✅ | ❌ FAIL | ✅ | 63.0h | 26h |
| performance-analyst-agent | ✅ | ✅ PASS | ✅ | 160.9h | 168h |

### Suite 3 — Feedback Loop Integrity

| Test | Result | Detail |
|------|--------|--------|
| feedback_file_has_entries | ✅ PASS | 1 rejected, 4 approved, 13 scout_cycles, 1 data_integrity_gate |
| feedback_updated_recently | ❌ FAIL | Last entry: 2026-05-12 (54 days ago, 0 entries in last 7 days) |
| rejection_reasons_specific | ✅ PASS | STR-001 reason is detailed (>20 chars) |
| no_repeated_failures | ✅ PASS | No duplicate rejection descriptions |

### Suite 4 — Registry Consistency

| Test | Result | Detail |
|------|--------|--------|
| no_phantom_tasks | ✅ PASS | Running task integration-20260705 has active tmux session |
| no_ghost_sessions | ✅ PASS | No unregistered tmux sessions beyond orchestrator |
| registry_not_stale | ✅ PASS | No completed tasks >30 days in active_tasks |

**Note:** `signal-202606042140` (status: failed) remains in active_tasks — this is not a running task so doesn't trigger phantom check, but the stale failed entry may warrant archival.

### Suite 5 — CI Pipeline Integrity

| Test | Result | Detail |
|------|--------|--------|
| ci/run_ci.sh exists_and_executable | ✅ PASS | OK |
| ci/lint.sh exists_and_executable | ✅ PASS | OK |
| ci/run_tests.sh exists_and_executable | ✅ PASS | OK |
| ci/validate_backtest.py exists_and_executable | ✅ PASS | OK |
| ci_pipeline_passes | ❌ FAIL | 9 lint errors (8×F541 calculate_geo_elo.py, 1×E722 run_trader_profiling.py) |
| test_suite_has_coverage | ✅ PASS | 27 tests in 2 test files |

### Suite 6 — Brain Directory Integrity

All 10 critical files present and non-empty:
- `brain/signals.json` ✅ (58,220 bytes)
- `brain/feedback.json` ✅ (44,012 bytes)
- `brain/priorities.md` ✅ (6,548 bytes)
- `brain/kpis.md` ✅ (16,363 bytes)
- `brain/definition_of_done.md` ✅ (2,089 bytes)
- `brain/model-routing.md` ✅ (24,299 bytes)
- `brain/strategy-notes/research-directions.md` ✅ (76,241 bytes)
- `brain/reference-library/ml-in-finance-notes.md` ✅ (26,423 bytes)
- `brain/reference-library/lopez-de-prado-notes.md` ✅ (39,101 bytes)
- `brain/reference-library/ernest-chan-algo-trading-notes.md` ✅ (48,759 bytes)

All 3 JSON files valid. Brain total: **3.94 MB**.

### Suite 7 — Integration Contract (first-repo)

| Test | Result | Detail |
|------|--------|--------|
| contract_db_connectable | ✅ PASS | Connected to polymarket_tracker.db |
| contract_wal_mode | ✅ PASS | journal_mode=wal |
| contract_clean_pool | ✅ PASS | clean_pool=30,096 (≥10,000) |
| contract_clean_markets | ✅ PASS | clean_markets=92,144 (≥16,000) |

**Operational alert (not a test):** pool_c=2,463 (below 2,500 threshold). Partial recovery from Jun 27 low of 2,155 but still below minimum. Root cause unknown since Jun 27. Contract Section 8 is stale — uncovered commits from Jun 25 (database.py data_source) and Jun 29 (daily_maintenance.py test-runner) need v2.14 changelog entry.

---

## Consecutive Failure Tracker

| Failure | Jun 14 | Jun 28 | Jul 5 | Status |
|---------|--------|--------|-------|--------|
| CI lint | 7th | 8th | **9th** | SYSTEMIC |
| signal-agent cadence | 5th+ | 6th+ | **7th+** | SYSTEMIC |
| quant-research cadence | 3rd | 4th+ | **5th+** | SYSTEMIC |
| backtest-agent cadence | (4th+) | 4th+ | **5th+** | SYSTEMIC |
| feedback_updated_recently | 1st | 2nd | **3rd** | SYSTEMIC |

All 5 tracked failures are now SYSTEMIC (≥3 consecutive Sundays). Escalation to Oscar required.

---

## System Health Assessment

The system's structural integrity is sound — all brain files are intact, the database is healthy, CI scripts are present, JSON is valid, and the registry correctly reflects the single running task. The integration contract remains satisfied with dramatically improved market and trader counts (92,144 clean markets vs 16,000 minimum).

However, the operational layer remains critically understaffed. Four of five production agents are either dark or behind cadence. The core research pipeline (quant-research → backtest) has been stalled for 40+ days, blocking Phase 5 Gate 4 (RQ-GEO-ELO-001 Phase 1 never executed despite Oscar approval on May 25). The CI lint block entering its 10th week is a trivial fix — 9 lines of code across 2 files — that has compounded as a psychological signal that the system is "broken" each time an agent runs CI.

The most important single action this week: **fix the CI lint** (20 minutes), then **execute RQ-GEO-ELO-001 Phase 1** (the approved quant-research run that directly unblocks Phase 5 Gate 4). The signal-agent rescan for July (scoring STR003-004 and STR003-008 from Jun 30 resolution) is also overdue and needed before feedback-loop-agent can score those signals in Run #11.

The database health is encouraging — clean_pool has grown to 30,096 (up from ~22,000 in June) and clean_markets has surged to 92,144, reflecting strong data accumulation. Pool C's continued sub-threshold position (2,463 < 2,500) needs root-cause investigation but is not blocking current operations.

---

*Report generated: 2026-07-05 23:00 UTC | Agent: integration-test-agent | Task: integration-20260705 | Model: claude-sonnet-4-6 (Tier 3)*
