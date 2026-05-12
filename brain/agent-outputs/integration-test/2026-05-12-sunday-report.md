# Integration Test Report — 2026-05-12 (Tuesday)

## Result: ❌ 8 FAILURES

> **Note:** This is a Tuesday run (task_id: integration-20260512). Regularly scheduled Sunday slot
> was integration-20260510 (prior tmux session present but no report file found).
> This report covers full suite state as of 2026-05-12 15:35 UTC.

## Test Summary
| Metric | Value |
|--------|-------|
| Total tests | 49 |
| Passed | 41 |
| Failed | 8 |
| Pass rate | 83.7% |

---

## ❌ Failures (action required)

### 1. Signal type mismatch — test template vs live bus
- **Suite:** Suite 1 — Signal Bus
- **Test:** `expected_signal_types_present`
- **What failed:** Zero signals with types `elite_convergence_detected`, `validation_requested`,
  or `validation_completed` in the last 7 days. None of these exact type strings exist anywhere
  in the bus.
- **Root cause:** Signal type names evolved after the test template was written.
  Actual types in use: `revalidation_requested` (not `validation_requested`),
  `validation_complete` (not `validation_completed`), `str003_directional_single/convergence`
  and `str004_aggregate_divergence` (replacing `elite_convergence_detected`).
  STR-001 is SUSPENDED so `elite_convergence_detected` was never emitted.
- **Recommended fix:** Update `expected_types` in the test template to:
  ```python
  expected_types = {
      'revalidation_requested',
      'validation_complete',
      'str003_directional_single',
  }
  ```
- **Severity:** MEDIUM — test design gap, not a live system failure. Signal bus is healthy.

---

### 2. Signal-agent: no output in 15 days (no active session)
- **Suite:** Suite 2 — Agent Output Integrity
- **Test:** `signal-agent_output_recent`
- **What failed:** Last signal-agent output file is `2026-04-27-signal-report.md` (15 days ago).
  Cadence limit is 4 hours. Signal-agent has **no active tmux session** in `tmux ls`.
- **Recommended fix:** Spawn signal-agent manually:
  ```bash
  cd ~/trading-swarm && ./scripts/spawn_agent.sh signal-$(date +%Y%m%d) signal-agent 2 "Routine signal scan"
  ```
  Confirm output appears in `brain/agent-outputs/signal-agent/` within 4 hours.
- **Severity:** HIGH — signal pipeline is stalled. New signals have not been generated since
  the second signal run (2026-04-27). Active STR-003 signals are now 15 days old with no rescan.

---

### 3. Quant-research-agent: no output files at expected path
- **Suite:** Suite 2 — Agent Output Integrity
- **Test:** `quant-research-agent_has_output`
- **What failed:** Test scans `brain/agent-outputs/quant-research/*.{md,json}` — zero files at
  directory root. Agent organises output into subdirectories (RQ1.1, RQ2.2, RQ3.2). Most recent
  JSON file across all subdirs is `rq1_1_results.json` from 2026-04-26 (16 days ago, max 72h).
- **Recommended fix (two parts):**
  1. Update test glob to be recursive: `list(output_dir.rglob('*.md')) + list(output_dir.rglob('*.json'))`
  2. quant-research-agent is not running — no tmux session found. Most recent work was RQ1.1
     on 2026-05-01. RQ3.2 results exist but are 16 days old. Schedule next research task.
- **Severity:** HIGH — quant-research is the primary Phase 2 deliverable. RQ1.1 and RQ3.2 are
  the stopping-rule questions. Need to verify results are written up and Phase 2 status assessed.

---

### 4. Backtest-agent: no output in 15 days
- **Suite:** Suite 2 — Agent Output Integrity
- **Test:** `backtest-agent_output_recent`
- **What failed:** Last backtest output is `STR-001-validation-2026-04-27.json` (15 days ago).
  Cadence limit is 168 hours (weekly). No backtest-agent tmux session.
- **Recommended fix:** Backtest-agent runs only when triggered by `revalidation_requested`
  signals. Signals 14-15 (RQ0.1, RQ0.2) were filed 2026-05-07 as `processed` — confirm
  whether backtest-agent was spawned to handle these. If not, check orchestrator respawn logic.
  STR-001b pre-registration is a prerequisite before next strategy retest.
- **Severity:** MEDIUM — backtest-agent is demand-driven. Two revalidation requests from
  2026-05-07 (RQ0.1, RQ0.2) have status `processed` but no corresponding completion signal or
  output file. Investigate whether these tasks were actually dispatched.

---

### 5. Performance-analyst-agent: output 3 hours over weekly threshold
- **Suite:** Suite 2 — Agent Output Integrity
- **Test:** `performance-analyst_output_recent`
- **What failed:** Last output `2026-05-05-weekly.md` is 171 hours old (limit: 168h). The agent
  has an active tmux session (`performance-analyst-agent-analyst-20260511`) but no new output file.
- **Recommended fix:** Verify that the analyst-20260511 session completed and produced output to
  the correct directory. If the session is stale or wrote to a wrong path, re-spawn. Check that the
  Monday run landed correctly — `tmux attach -t performance-analyst-agent-analyst-20260511`.
- **Severity:** LOW — 3-hour slip on a weekly agent. Likely ran Monday and is barely over threshold.
  Active tmux session suggests it may be in progress.

---

### 6. Feedback loop: approved/rejected not updated in 13 days
- **Suite:** Suite 3 — Feedback Loop Integrity
- **Test:** `feedback_updated_recently`
- **What failed:** Last entry in `approved` or `rejected` arrays is 2026-04-29. Test requires
  an entry within 7 days. Scout cycles ARE being updated in feedback.json (most recent:
  2026-05-12 today), but the test only checks `approved` and `rejected` arrays.
- **Root cause (two-part):**
  1. Test design gap — scout_cycles are active feedback entries but the test ignores them.
  2. Genuine gap — no strategy approvals or rejections since 2026-04-29. STR-001b has not been
     pre-registered; feedback-loop-agent has not run a new validation cycle since April 25.
- **Recommended fix:**
  - Update test to include `scout_cycles` in recency check (scout_cycles[].cycle_date).
  - More importantly: feedback-loop-agent should have completed 2+ weekly cycles by now but only
    1 cycle is on record (2026-04-25). Run feedback-loop-agent (needed for Phase 5 gate: 4+ cycles).
- **Severity:** MEDIUM — Phase 5 gate requires 4+ feedback-loop-agent cycles. Currently at 1/4.

---

### 7. Ghost tmux sessions: 9 sessions with no registry entry
- **Suite:** Suite 4 — Registry Consistency
- **Test:** `no_ghost_sessions`
- **What failed:** 9 tmux sessions exist with no corresponding `running` task in agent_registry.json:
  ```
  code-hygiene-agent-hygiene-20260508           (4 days old)
  integration-test-agent-integration-20260510   (2 days old)
  performance-analyst-agent-analyst-20260511    (1 day old)
  research-scout-scout-20260508                 (4 days old)
  research-scout-scout-20260509                 (3 days old)
  research-scout-scout-20260510                 (2 days old)
  research-scout-scout-20260511                 (1 day old)
  research-scout-scout-20260512                 (today)
  training-librarian-agent-librarian-20260509   (3 days old)
  ```
- **Recommended fix:** Kill completed sessions and ensure orchestrator prunes sessions on
  task completion. For now, safely kill known-complete sessions:
  ```bash
  tmux kill-session -t code-hygiene-agent-hygiene-20260508
  tmux kill-session -t integration-test-agent-integration-20260510
  # Verify performance-analyst is actually done before killing
  tmux kill-session -t research-scout-scout-20260508
  tmux kill-session -t research-scout-scout-20260509
  tmux kill-session -t research-scout-scout-20260510
  tmux kill-session -t training-librarian-agent-librarian-20260509
  ```
  Add orchestrator teardown: `tmux kill-session -t {session}` in the task-completion handler.
- **Severity:** MEDIUM — ghost sessions indicate registry drift. research-scout-scout-20260512
  is today's session and may still be running; do not kill it.

---

### 8. CI pipeline failing: `flake8` not installed
- **Suite:** Suite 5 — CI Pipeline Integrity
- **Test:** `ci_pipeline_passes`
- **What failed:** `ci/run_ci.sh` exits non-zero. Root cause: `flake8: command not found`.
  The 27 unit tests pass. Backtest validation is skipped (no file provided). Only lint fails.
- **Recommended fix:**
  ```bash
  pip install flake8
  ```
  Or update `ci/lint.sh` to check availability first and skip gracefully:
  ```bash
  if ! command -v flake8 &>/dev/null; then
    echo "⚠️  flake8 not installed — skipping lint"
    exit 0
  fi
  ```
  Installing flake8 is preferred — the lint step is a real quality gate.
- **Severity:** HIGH — CI cannot complete. No agent code changes can be validated until fixed.
  This must be resolved before any agent produces Python file changes.

---

## ✅ Passed Suites

**Suite 1 — Signal Bus (3/4 passed):** Signal bus is active with 17 signals. No signals stuck
in `pending` (the pending array is empty). Validation routing is consistent for processed
requests. One test failed due to type name mismatch (see above).

**Suite 2 — Agent Output Integrity (6/10 passed):** Research-scout is healthy — produced output
today at 08:05 UTC (most recent: `2026-05-12-08-polymarket-resolution-zone-price-dynamics.md`,
3380 bytes). All agents with output have non-empty files meeting minimum size thresholds.

**Suite 3 — Feedback Loop Integrity (3/4 passed):** The one rejection (STR-001) has a
specific, detailed reason (98 words). No repeated failures. Feedback file is non-empty (5 entries).

**Suite 4 — Registry Consistency (2/3 passed):** No phantom tasks — the one `running` registry
entry (integration-20260512) has a valid matching tmux session. No stale completed tasks > 30 days.

**Suite 5 — CI Pipeline (5/6 passed):** All 4 CI scripts exist and are executable. 27 tests
pass (21 in test_market_filter.py + 6 in test_registry.py). Only lint fails due to missing tool.

**Suite 6 — Brain Integrity (14/14 passed):** All 10 critical brain files exist and are
non-empty (smallest: definition_of_done.md at 2089 bytes, largest: ernest-chan-notes at 48421 bytes).
All 3 JSON files parse cleanly. Brain directory: 1.2 MB total.

**Suite 7 — Integration Contract (4/4 passed):** First-repo DB fully accessible.
- WAL mode: active ✓
- Clean pool: 603 traders (threshold ≥450) ✓ — up from 493 at last contract check
- Clean markets: 12,203 (threshold ≥11,000) ✓

---

## Suite Details

### Suite 1 — Signal Bus Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal_bus_not_empty | ✅ PASS | 17 signals in bus |
| no_stuck_signals | ✅ PASS | No pending signals; pending array is empty |
| expected_signal_types_present | ❌ FAIL | Missing: elite_convergence_detected, validation_requested, validation_completed — type names evolved |
| validation_pipeline_complete | ✅ PASS | No unmatched validation_requested (type not used; system uses revalidation_requested) |

### Suite 2 — Agent Output Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal-agent_output_directory_exists | ✅ PASS | Directory present |
| signal-agent_output_recent | ❌ FAIL | Last output 360h ago (max: 4h). No active tmux session. |
| signal-agent_output_non_empty | ✅ PASS | 11,338 bytes |
| quant-research-agent_output_directory_exists | ✅ PASS | Directory present |
| quant-research-agent_has_output | ❌ FAIL | No *.md or *.json at root (subdirs only: RQ1.1, RQ2.2, RQ3.2) |
| backtest-agent_output_directory_exists | ✅ PASS | Directory present |
| backtest-agent_output_recent | ❌ FAIL | Last output 360h ago (max: 168h) |
| backtest-agent_output_non_empty | ✅ PASS | 4,757 bytes |
| research-scout-agent_output_directory_exists | ✅ PASS | Directory present |
| research-scout-agent_output_recent | ✅ PASS | Last output 7.5h ago (max: 26h) |
| research-scout-agent_output_non_empty | ✅ PASS | 3,380 bytes |
| performance-analyst-agent_output_directory_exists | ✅ PASS | Directory present |
| performance-analyst-agent_output_recent | ❌ FAIL | Last output 171h ago (max: 168h) — 3h over |
| performance-analyst-agent_output_non_empty | ✅ PASS | 23,484 bytes |

### Suite 3 — Feedback Loop Integrity
| Test | Result | Detail |
|------|--------|--------|
| feedback_file_has_entries | ✅ PASS | 1 rejected, 4 approved |
| feedback_updated_recently | ❌ FAIL | Last approved/rejected: 2026-04-29 (13 days ago) |
| rejection_reasons_specific | ✅ PASS | STR-001 rejection reason: 98 words, highly specific |
| no_repeated_failures | ✅ PASS | No duplicate rejected strategies |

### Suite 4 — Registry Consistency
| Test | Result | Detail |
|------|--------|--------|
| no_phantom_tasks | ✅ PASS | 1 running task; tmux session confirmed present |
| no_ghost_sessions | ❌ FAIL | 9 tmux sessions with no registry entry |
| registry_not_stale | ✅ PASS | No completed tasks > 30 days in active_tasks |

### Suite 5 — CI Pipeline Integrity
| Test | Result | Detail |
|------|--------|--------|
| ci/run_ci.sh_exists_and_executable | ✅ PASS | OK |
| ci/lint.sh_exists_and_executable | ✅ PASS | OK |
| ci/run_tests.sh_exists_and_executable | ✅ PASS | OK |
| ci/validate_backtest.py_exists_and_executable | ✅ PASS | OK |
| ci_pipeline_passes | ❌ FAIL | flake8 not found; tests pass (27/27); lint blocks CI exit |
| test_suite_has_coverage | ✅ PASS | 27 tests (21 + 6) ≥ 6 threshold |

### Suite 6 — Brain Directory Integrity
| Test | Result | Detail |
|------|--------|--------|
| brain_file_exists_signals.json | ✅ PASS | Valid (502 lines) |
| brain_file_exists_feedback.json | ✅ PASS | Valid (480 lines) |
| brain_file_exists_priorities.md | ✅ PASS | 6,548 bytes |
| brain_file_exists_kpis.md | ✅ PASS | 10,659 bytes |
| brain_file_exists_definition_of_done.md | ✅ PASS | 2,089 bytes |
| brain_file_exists_model-routing.md | ✅ PASS | 20,097 bytes |
| brain_file_exists_research-directions.md | ✅ PASS | 47,990 bytes |
| brain_file_exists_ml-in-finance-notes.md | ✅ PASS | 26,423 bytes |
| brain_file_exists_lopez-de-prado-notes.md | ✅ PASS | 37,853 bytes |
| brain_file_exists_ernest-chan-algo-trading-notes.md | ✅ PASS | 48,421 bytes |
| json_valid_signals.json | ✅ PASS | Valid JSON |
| json_valid_feedback.json | ✅ PASS | Valid JSON |
| json_valid_agent_registry.json | ✅ PASS | Valid JSON |
| brain_has_content | ✅ PASS | Brain directory: 1.2 MB |

### Suite 7 — Integration Contract (first-repo)
| Test | Result | Detail |
|------|--------|--------|
| contract_db_connectable | ✅ PASS | Connected: polymarket_tracker.db |
| contract_wal_mode | ✅ PASS | journal_mode=wal |
| contract_clean_pool | ✅ PASS | clean_pool=603 (expected ≥450) — note: up from 493 at last check |
| contract_clean_markets | ✅ PASS | clean_markets=12,203 (expected ≥11,000) |

---

## System Health Assessment

The brain, data contract, and research-scout pipeline are all healthy. Suite 6 and Suite 7
are clean sweeps, which means the memory layer and first-repo integration are in good shape.
Research-scout produced output today and has active sessions confirming daily cadence is holding.

The concerning pattern is **agent dormancy across three operational agents.** Signal-agent has no
active tmux session and has not produced output in 15 days — the signal pipeline is stalled.
Quant-research has no session and last wrote files 11-16 days ago. Backtest-agent has no
session and last ran 15 days ago. These three agents together form the core research-to-signal
pipeline, and all three are idle simultaneously. The system's research layer is not cycling.

The CI failure (`flake8 not found`) is a blocking quality gate issue. Until resolved, no agent
that produces Python files can be validated through CI. This is a one-command fix but needs to
be done before any new agent work begins.

Ghost tmux sessions (9 total) indicate the orchestrator teardown path is not killing sessions
on completion. This is manageable but will compound over time. A session accumulation of this
size after only a few weeks of operation suggests it needs a cleanup hook added to the
orchestrator's task-completion handler.

The signal bus type mismatch and feedback recency gap are both partially test design issues —
the test template was written before the signal taxonomy evolved, and scout_cycles being
excluded from the feedback recency check means active daily work (13 cycles logged) is not
counted as "feedback updated." These are worth fixing in the test template before next Sunday.

**Priority actions before Monday:**
1. `pip install flake8` — unblock CI (5 minutes)
2. Spawn signal-agent — restart signal pipeline (10 minutes)
3. Kill stale ghost sessions — clean registry (5 minutes)
4. Review quant-research RQ1.1 and RQ3.2 results — determine Phase 2 status
5. Schedule feedback-loop-agent run — currently 1/4 cycles needed for Phase 5 gate

---

## Escalation Status

| Condition | Triggered? | Action |
|-----------|-----------|--------|
| CI pipeline failing | YES | `pip install flake8` — fix immediately |
| Signal bus stuck signals > 48h | NO | — |
| Brain JSON files corrupt | NO | — |
| Registry ghost sessions | YES | Kill 8 known-complete sessions |
| CRITICAL severity failures | NO | — |

No Telegram alert triggered. CI failure is HIGH but manageable without escalation —
it is a missing tool, not a broken test. Ghost sessions are registry drift, not unknown processes.

---

*Report generated: 2026-05-12T15:35:00Z by integration-test-agent (task: integration-20260512)*
*Model: claude-sonnet-4-6 (Tier 3)*
*Next scheduled run: Sunday 2026-05-17 23:00 UTC*
