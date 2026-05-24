# Integration Test Report — 2026-05-24 (Sunday)

## Result: ❌ 6 FAILURES

## Test Summary
Total tests: 45
Passed: 39
Failed: 6
Pass rate: 86.7%

---

## ❌ Failures (action required)

### 1. `signal-agent_output_recent` — CRITICAL
- **Suite:** 2 — Agent Output Integrity
- **What failed:** signal-agent last wrote output 158.8h ago (`brain/agent-outputs/signal-agent/2026-05-18-08-signal-report.md`). Max cadence is 4h. The signal-agent is the core market intelligence layer; 6.6 days of missed monitoring means no new directional positions have been detected, no new signals are flowing through the bus, and the system is effectively blind to current market conditions.
- **Consecutive failures:** 4th Sunday in a row (2026-05-12, 2026-05-14, 2026-05-17, 2026-05-24). **Threshold exceeded — HIGH priority escalation required.**
- **Recommended fix:**
  ```bash
  cd ~/trading-swarm
  ./scripts/spawn_agent.sh signal-$(date +%Y%m%d%H%M) signal-agent 3 "Cadence recovery — silent since 2026-05-18"
  ```
  Confirm output appears in `brain/agent-outputs/signal-agent/` within 4h. Note: agent was briefly active on 2026-05-18 (suggesting it spawned but did not sustain). Investigate whether the respawn logic is keeping it alive between runs or if a persistent failure is causing early exit.
- **Severity:** CRITICAL — 4 consecutive Sundays

---

### 2. `ci_pipeline_passes` — CRITICAL
- **Suite:** 5 — CI Pipeline Integrity
- **What failed:** `tests/test_registry.py::test_feedback_file_structure` fails. Test asserts `"approved" in data` but `brain/feedback.json` currently contains only `{"scout_cycles": [...]}` — the top-level `approved` and `rejected` arrays are absent. All other 26 tests pass. CI exit code: 1.
- **Root cause:** Downstream of failure #5 (feedback.json structure). CI itself is sound; the failure is a data structure problem.
- **Consecutive failures:** 4th Sunday in a row (2026-05-12, 2026-05-14, 2026-05-17, 2026-05-24 — note: different root causes each week but same test failure). **Threshold exceeded — HIGH priority escalation required.**
- **Recommended fix:** Fix the root cause in failure #5 (feedback.json structure). Once `approved` and `rejected` arrays exist in feedback.json, this test will self-heal with no code changes needed. No CI script modification required.
- **Severity:** CRITICAL — immediate escalation required per rule (CI must always be in runnable state)

---

### 3. `feedback_file_has_entries` — HIGH
- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** `brain/feedback.json` contains only `{"scout_cycles": [...]}`. The `approved` and `rejected` top-level arrays are absent. The test expects at least one approved or rejected entry. The feedback loop mechanism — where agents read past approvals and rejections before starting work — is broken. Agents cannot learn from past outcomes.
- **Root cause:** The feedback.json has been corrupted by a prior write that replaced the full structure with scout-cycle-only content. The research-scout-agent appears to be writing its cycle summary to feedback.json without preserving the existing approved/rejected structure. On 2026-05-14 the file was intact (1 rejected, 4 approved). Between 2026-05-14 and 2026-05-17 it was overwritten. It was not restored in the intervening week.
- **Consecutive failures:** 2 consecutive Sundays (2026-05-17, 2026-05-24). The 2026-05-12 report also showed 0 entries, but 2026-05-14 was a PASS — so the corruption is recurrent, not a single incident.
- **Recommended fix:**
  1. Restore `brain/feedback.json` from git history:
     ```bash
     git log --oneline brain/feedback.json
     # find the last clean commit (around 2026-05-14)
     git show <hash>:brain/feedback.json > brain/feedback.json
     git add brain/feedback.json && git commit -m "fix: restore feedback.json — approved/rejected arrays lost to scout overwrite"
     ```
  2. Check `orchestrator/task_templates/research-scout-agent.md` for any reference to `brain/feedback.json` as an output path. The scout should only append to the `scout_cycles` sub-key, never overwrite the full file.
  3. Once restored, run feedback-loop-agent to generate a fresh validation cycle entry.
- **Severity:** HIGH — agents are running without access to prior feedback

---

### 4. `research-scout-agent_output_recent` — HIGH
- **Suite:** 2 — Agent Output Integrity
- **What failed:** research-scout-agent last wrote output 125.1h ago (`brain/research-scout/pending-review/2026-05-19-17-*.md`). Max cadence is 26h (daily + buffer). The daily research pulse has been silent for 5+ days.
- **Consecutive failures:** 1st occurrence (was PASSING on 2026-05-17 at 2.9h). New failure this week.
- **Context:** The 4 files written on 2026-05-19 remain in `pending-review/` unreviewed (DeepSeek V4 preview, ForesightFlow score framework, per-market order flow, Polymarket CLOB v2 exchange upgrade). These are actionable findings that have not been processed.
- **Recommended fix:** Respawn research-scout-agent:
  ```bash
  cd ~/trading-swarm
  ./scripts/spawn_agent.sh scout-$(date +%Y%m%d%H%M) research-scout-agent 2.5 "Cadence recovery — silent since 2026-05-19"
  ```
  Also note: the 4 pending-review items from 2026-05-19 need human review, particularly the Polymarket CLOB v2 upgrade (exchange infrastructure change with potential protocol impact).
- **Severity:** HIGH — daily intelligence gathering has lapsed; pending findings unreviewed

---

### 5. `quant-research-agent_output_recent` — MEDIUM
- **Suite:** 2 — Agent Output Integrity
- **What failed:** quant-research-agent last wrote output 99.2h ago (`brain/agent-outputs/quant-research/LH-001/lh001_methodology.md`, 2026-05-20). Max cadence is 72h. Overdue by 27.2h.
- **Consecutive failures:** 2nd Sunday with this failure (2026-05-17: 512.2h; quant-research did run on 2026-05-20 for LH-001, so the cadence improved but is again overdue). The associated backtest task `backtest-lh001-v3-20260521` has been in `respawning` state since 2026-05-21 with 1 retry — 3+ days stuck. The registry shows it's waiting for a V3 backtest run that hasn't completed.
- **Recommended fix:**
  - Check the status of `backtest-lh001-v3-20260521`: the task has been respawning for 3 days. If the retry failed silently, resolve the registry entry and respawn quant-research-agent to continue LH-001 work.
  - The registry entry should be investigated: `cat ~/trading-swarm/logs/agent_logs/backtest-lh001-v3-20260521.log | tail -50`
- **Severity:** MEDIUM — LH-001 work was recently active; this is a cadence slip, not a prolonged outage

---

### 6. `expected_signal_types_present` — MEDIUM
- **Suite:** 1 — Signal Bus Integrity
- **What failed:** Expected signal types not seen in the last 7 days: `revalidation_requested`, `validation_complete`, `str003_directional_single`. Only signal type present in the bus: `validation_requested` (LH-001, status=completed).
- **Consecutive failures:** 4th Sunday in a row (2026-05-12, 2026-05-14, 2026-05-17, 2026-05-24). **Threshold exceeded — HIGH priority escalation required.**
- **Context:** This failure reflects system maturity rather than malfunction. `revalidation_requested` requires strategies to be in `approved` state in feedback.json (which is broken — see failure #3). `str003_directional_single` requires STR-003 to be developed. `validation_complete` was not emitted as a separate signal — the completion was embedded as fields on the original signal. These signal types may need to be updated to match current system conventions.
- **Recommended fix:** After restoring feedback.json and respawning signal-agent, this test should begin self-healing. Separately, consider revising the expected signal type list to match current conventions — `validation_completed_at` is embedded in signals rather than emitted as a separate event. The expected type `validation_complete` may be a stale name.
- **Severity:** MEDIUM — no immediate system breakdown, but indicates signalling conventions have drifted from test expectations

---

## ✅ Passed Suites

**Suite 1 — Signal Bus (3/4):** Bus is not empty; no signals stuck >48h (the single LH-001 validation_requested signal has status=completed, processed 2026-05-20). Validation routing check passes technically (no signals in 'processed' state to cross-reference).

**Suite 2 — Agent Outputs (7/10):** backtest-agent (73.4h vs 168h max, 5,749 bytes), performance-analyst-agent (160.9h vs 168h max, 28,036 bytes), and all non-empty file checks pass for all 5 agents.

**Suite 3 — Feedback Loop (3/4):** Rejection reason quality and repeated-failure checks pass vacuously (no rejected entries exist). Scout cycle from 2026-05-18 counts as a recent feedback entry.

**Suite 4 — Registry (3/3):** No phantom tasks (only integration-20260524 is status=running, and its tmux session is confirmed active). No ghost sessions. No stale completed tasks. Note: backtest-lh001-v3-20260521 is status=respawning (not running), so not subject to phantom check — but it has been in this state for 3 days.

**Suite 5 — CI Pipeline (5/6):** All 4 CI scripts (run_ci.sh, lint.sh, run_tests.sh, validate_backtest.py) exist and are executable. 27 tests in the suite (well above minimum 6). CI infrastructure is sound.

**Suite 6 — Brain Integrity (14/14):** All 10 critical brain files present and non-empty. All 3 JSON files parse cleanly. Brain directory: 1.6MB.

**Suite 7 — Integration Contract (4/4):** DB connectable (WAL mode confirmed). Clean pool: 14,390 (≥450 threshold — NOTE: see health assessment re: unexpectedly high count). Clean markets: 14,941 (≥11,000 threshold). No contract violation signal written.

---

## Suite Details

### Suite 1 — Signal Bus Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal_bus_not_empty | ✅ PASS | 1 signal in bus |
| no_stuck_signals | ✅ PASS | No signals in pending state |
| expected_signal_types_present | ❌ FAIL | Missing: revalidation_requested, validation_complete, str003_directional_single |
| validation_pipeline_complete | ✅ PASS | No unmatched validation requests (technical pass) |

### Suite 2 — Agent Output Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal-agent_output_recent | ❌ FAIL | 158.8h since last output (max 4h) |
| signal-agent_output_non_empty | ✅ PASS | 13,919 bytes |
| quant-research-agent_output_recent | ❌ FAIL | 99.2h since last output (max 72h) |
| quant-research-agent_output_non_empty | ✅ PASS | 12,787 bytes |
| backtest-agent_output_recent | ✅ PASS | 73.4h (max 168h) |
| backtest-agent_output_non_empty | ✅ PASS | 5,749 bytes |
| research-scout-agent_output_recent | ❌ FAIL | 125.1h since last output (max 26h) |
| research-scout-agent_output_non_empty | ✅ PASS | 818 bytes |
| performance-analyst-agent_output_recent | ✅ PASS | 160.9h (max 168h) |
| performance-analyst-agent_output_non_empty | ✅ PASS | 28,036 bytes |

### Suite 3 — Feedback Loop Integrity
| Test | Result | Detail |
|------|--------|--------|
| feedback_file_has_entries | ❌ FAIL | 0 approved, 0 rejected (arrays absent from JSON) |
| feedback_updated_recently | ✅ PASS | scout_cycle 2026-05-18 within 7 days |
| rejection_reasons_specific | ✅ PASS | No rejected entries to assess |
| no_repeated_failures | ✅ PASS | No repeated failures detected |

### Suite 4 — Registry Consistency
| Test | Result | Detail |
|------|--------|--------|
| no_phantom_tasks | ✅ PASS | All running-status tasks have active tmux sessions |
| no_ghost_sessions | ✅ PASS | No unregistered tmux sessions |
| registry_not_stale | ✅ PASS | No completed tasks >30 days old |

### Suite 5 — CI Pipeline Integrity
| Test | Result | Detail |
|------|--------|--------|
| ci/run_ci.sh exists and executable | ✅ PASS | OK |
| ci/lint.sh exists and executable | ✅ PASS | OK |
| ci/run_tests.sh exists and executable | ✅ PASS | OK |
| ci/validate_backtest.py exists and executable | ✅ PASS | OK |
| ci_pipeline_passes | ❌ FAIL | test_feedback_file_structure fails: assert 'approved' in data |
| test_suite_has_coverage | ✅ PASS | 27 tests (min 6) |

### Suite 6 — Brain Integrity
| Test | Result | Detail |
|------|--------|--------|
| brain_file_exists_signals.json | ✅ PASS | 3,094 bytes |
| brain_file_exists_feedback.json | ✅ PASS | 388 bytes (valid JSON, wrong structure) |
| brain_file_exists_priorities.md | ✅ PASS | 6,548 bytes |
| brain_file_exists_kpis.md | ✅ PASS | 13,438 bytes |
| brain_file_exists_definition_of_done.md | ✅ PASS | 2,089 bytes |
| brain_file_exists_model-routing.md | ✅ PASS | 23,986 bytes |
| brain_file_exists_research-directions.md | ✅ PASS | 54,676 bytes |
| brain_file_exists_ml-in-finance-notes.md | ✅ PASS | 26,423 bytes |
| brain_file_exists_lopez-de-prado-notes.md | ✅ PASS | 37,853 bytes |
| brain_file_exists_ernest-chan-algo-trading-notes.md | ✅ PASS | 48,421 bytes |
| json_valid_signals.json | ✅ PASS | Valid JSON |
| json_valid_feedback.json | ✅ PASS | Valid JSON (wrong schema, not corrupt) |
| json_valid_agent_registry.json | ✅ PASS | Valid JSON |
| brain_has_content | ✅ PASS | 1.6MB |

### Suite 7 — Integration Contract (first-repo)
| Test | Result | Detail |
|------|--------|--------|
| contract_db_connectable | ✅ PASS | Connected: /home/parison/projects/first-repo/data/polymarket_tracker.db |
| contract_wal_mode | ✅ PASS | journal_mode=wal |
| contract_clean_pool | ✅ PASS | clean_pool=14,390 (≥450) |
| contract_clean_markets | ✅ PASS | clean_markets=14,941 (≥11,000) |

---

## Consecutive Failure Tracking

| Test | 2026-05-12 | 2026-05-14 | 2026-05-17 | 2026-05-24 | Consecutive | Action |
|------|-----------|-----------|-----------|-----------|-------------|--------|
| signal-agent_output_recent | ❌ | ❌ | ❌ | ❌ | **4** | 🚨 ESCALATE |
| ci_pipeline_passes | ❌ | ❌ | ❌ | ❌ | **4** | 🚨 ESCALATE |
| expected_signal_types_present | ❌ | ❌ | ❌ | ❌ | **4** | 🚨 ESCALATE |
| feedback_file_has_entries | ❌ | ✅ | ❌ | ❌ | 2 | Monitor |
| quant-research_output_recent | ✅ | ❌ | ❌ | ❌ | 3 | 🚨 ESCALATE |
| research-scout_output_recent | ✅ | ✅ | ✅ | ❌ | 1 | Monitor |

Three tests have exceeded the 3-consecutive-Sunday escalation threshold. Five of the six failures this week are either new or recurring systemic issues, not transient failures.

---

## System Health Assessment

The system's structural health (brain files, CI scripts, registry, DB contract) remains intact — 14 brain integrity checks and all 4 contract checks pass cleanly. The infrastructure built in Phase 1 is holding. However, the operational layer has three persistent problems that have now crossed the 3-Sunday escalation threshold.

The most critical pattern: **signal-agent has been effectively non-functional for four weeks**. It ran briefly on 2026-05-18 (producing one output) but has not sustained cadence in any week this test suite has run. This is the core market intelligence agent — without it, no new directional signals enter the bus, and the market monitoring capability the system was built to provide is dormant. Four Sundays of CRITICAL failure on the same agent with no resolution is the clearest indication that something structural is preventing stable operation, not a transient spawn failure.

The **feedback.json corruption** is a recurring data integrity problem. The file was intact on 2026-05-14 (1 rejected, 4 approved) and corrupted between then and 2026-05-17. It was not restored in the following week. This means for two weeks, every agent that reads feedback.json before starting — per system design — has been reading an incomplete file. The `approved/rejected` learning signal is completely absent. This also drives the CI failure: the CI test suite knows what feedback.json should look like, and it's been wrong for two consecutive weeks.

One notable anomaly in this week's data: the **integration contract clean_pool count** is 14,390 — previously expected to be ~493 after LP_ARTIFACT and ARB_BOT exclusions were applied. The `research_excluded` filter is returning nearly all traders as eligible. This warrants investigation — either the `research_excluded` column was added but not backfilled with the expected exclusions, or the exclusion list was reset. This does not affect the threshold test (which passes at ≥450), but if the clean pool is artificially large, research queries may be including noise traders that should be excluded.

**Escalation required:** Three tests at 3+ consecutive Sundays, plus one CRITICAL rule trigger (CI pipeline failing). Telegram alert to orchestrator bot warranted for all three systemic failures, with signal-agent and CI as the primary tickets.

---

## Escalation Summary

The following should be raised with HIGH priority via Telegram orchestrator alert:

1. **[SYSTEMIC] signal-agent dead — 4th consecutive Sunday** — Signal-agent has not sustained cadence since the system launched. Brief spawn on 2026-05-18 did not result in continuous operation. Core market monitoring is inactive.

2. **[SYSTEMIC] CI pipeline broken — 4th consecutive Sunday** — `test_feedback_file_structure` failing. Root cause: feedback.json missing approved/rejected arrays. Fix requires restoring the file from git history, not code changes.

3. **[SYSTEMIC] expected_signal_types — 4th consecutive Sunday** — Bus contains only `validation_requested` type. Missing: `revalidation_requested`, `validation_complete`, `str003_directional_single`. Partially a maturity issue; partially a consequence of signal-agent and feedback loop being inactive.

4. **[NEW] research-scout silent 5+ days** — 4 pending-review findings from 2026-05-19 are unprocessed, including a Polymarket CLOB v2 exchange upgrade notice.

---

*Report generated: 2026-05-24T23:01Z*
*Agent: integration-test-agent (Tier 3 — claude-sonnet-4-6)*
*Task ID: integration-20260524*
*Suites run: 7 of 7*
