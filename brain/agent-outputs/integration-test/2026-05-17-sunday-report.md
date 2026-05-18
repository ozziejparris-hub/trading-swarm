# Integration Test Report — 2026-05-17

## Result: ❌ 6 FAILURES

## Test Summary
Total tests: 45
Passed: 39
Failed: 6
Pass rate: 86.7%

---

## ❌ Failures (action required)

### 1. `feedback_file_has_entries` — CRITICAL
- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** `brain/feedback.json` has been overwritten by research-scout-agent with a scout cycle summary object. The file now contains: `{"scout_cycles_completed": 15, "last_cycle_date": "2026-05-17", "findings_surfaced": 5, "findings_approved": 0, "findings_dismissed": 0, "cycle_summary": "..."}`. The top-level `approved`, `rejected`, and `data_integrity_gates` keys are absent.
- **Root cause:** research-scout-agent is writing its cycle summary to `brain/feedback.json` instead of its own output directory (`brain/agent-outputs/research-scout/` or `brain/research-scout/`). This is a path routing bug, most likely in the Qwen3-Coder 30B-A3B prompt template for research-scout.
- **Impact:** All approved/rejected strategy entries and data integrity gates are destroyed. Agents that read feedback.json before starting (per system design) are now reading garbage. The CI test `test_feedback_file_structure` fails as a result.
- **Recommended fix:**
  1. **Immediately:** Restore feedback.json from git history — `git log --oneline brain/feedback.json` then `git show <hash>:brain/feedback.json > brain/feedback.json` to recover the last valid version.
  2. **Find the bug:** Check `orchestrator/task_templates/research-scout-agent.md` for any reference to `brain/feedback.json` as an output path. The scout should write only to `brain/research-scout/pending-review/` and update `brain/feedback.json`'s `scout_cycles` sub-key — not overwrite the entire file.
  3. **Fix the template:** The output path for cycle summaries must be `brain/research-scout/approved/` or appending to `scout_cycles` array inside `feedback.json` — never `json.dump` to the top-level file.
- **Consecutive failures:** 2 Sundays (May 12: empty, May 17: corrupted). **ESCALATE if this recurs next Sunday.**

### 2. `feedback_updated_recently` — CRITICAL
- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** 0 feedback entries in last 7 days. Direct consequence of the feedback.json corruption in failure #1. No approved or rejected entries exist in the file.
- **Recommended fix:** Restore feedback.json (see failure #1). After restoration, run feedback-loop-agent to generate a new validation cycle entry.
- **Note:** feedback-loop-agent state (`feedback_loop_state.json`) shows 6 runs completed (last 2026-05-13). The runs are happening — the data is being destroyed by the scout overwrite.

### 3. `signal-agent_output_recent` — CRITICAL
- **Suite:** 2 — Agent Output Integrity
- **What failed:** signal-agent last wrote output 105.7h ago (`2026-05-13-14-signal-report.md`). Max cadence is 4h. Signal-agent is the core market intelligence layer; 4.4 days of missed monitoring means active signals are stale and no new directional positions have been detected.
- **Current signals:** 4 active STR-003 signals all dated 2026-04-27 (20 days old). All remain MEDIUM confidence with upgrade conditions unmet. No fresh scan since May 13.
- **Recommended fix:** Respawn signal-agent immediately:
  ```bash
  cd ~/trading-swarm && ./scripts/spawn_agent.sh signal-$(date +%Y%m%d%H%M) signal-agent 3 "Routine signal scan — cadence recovery"
  ```
  Confirm output appears in `brain/agent-outputs/signal-agent/` within 4 hours. Check tmux session is alive with `tmux ls`.
- **Consecutive failures:** 2 Sundays (May 12: 360h stale, May 17: 105.7h stale). **ESCALATE if this recurs next Sunday.**

### 4. `quant-research-agent_output_recent` — HIGH
- **Suite:** 2 — Agent Output Integrity
- **What failed:** quant-research-agent last produced output 512.2h ago (21 days), exceeding the 72h limit. Most recent file is `rq2_2_results.json`. Phase 2 research is severely stalled.
- **Phase gate impact:** RQ1.1 and RQ3.2 are Phase 5 gate blockers (per priorities.md). Neither has been completed. The system cannot progress to live trading without these two validations. 21 days of inactivity on the primary research deliverable is a critical blocker.
- **Recommended fix:**
  1. Check what RQ2.2 produced: `cat brain/agent-outputs/quant-research/rq2_2_results.json`
  2. Review whether quant-research has a pending pre-registration hypothesis in `brain/strategy-notes/` awaiting approval
  3. If no blocker: spawn quant-research-agent for RQ1.1 (ELO persistence): `./scripts/spawn_agent.sh quant-$(date +%Y%m%d) quant-research-agent 3 "RQ1.1 — ELO persistence: does ELO in period T predict Brier in T+1?"`
- **Consecutive failures:** 2 Sundays (May 12: no output at all, May 17: 512h stale).

### 5. `ci_pipeline_passes` — HIGH
- **Suite:** 5 — CI Pipeline Integrity
- **What failed:** `tests/test_registry.py::test_feedback_file_structure` fails. Test asserts `"approved" in data` but feedback.json now contains scout cycle keys. CI exit code 1. All other 26 tests pass.
- **Root cause:** Downstream of feedback.json corruption (failure #1).
- **Recommended fix:** Restoring feedback.json (failure #1 fix) will resolve this automatically. No code change needed.

### 6. `expected_signal_types_present` — MEDIUM
- **Suite:** 1 — Signal Bus Integrity
- **What failed:** None of the three expected signal types (`revalidation_requested`, `validation_complete`, `str003_directional_single`) appear in the last 7 days. The signal bus has 19 total signals, but all relevant ones are >10 days old.
- **Root cause:** Signal-agent has not run since May 13 (failure #3). No new signals means expected types fall outside the 7-day window.
- **Recommended fix:** Respawning signal-agent (failure #3 fix) will produce fresh str003 signals and trigger revalidation_requested within the week. This test will self-heal once signal-agent is running.

---

## ✅ Passed Suites

**Suite 1 — Signal Bus (3/4 passing):** Bus is healthy with 19 signals. No signals stuck in pending. All processed validation requests have matching completions. Only failure is the 7-day recency window.

**Suite 2 — Agent Outputs (8/10 passing):** backtest-agent, research-scout-agent, and performance-analyst-agent all within cadence and producing substantive output. Research-scout produced output 2.9h before this test ran (healthy). Performance-analyst weekly report is 108h old (within 168h limit).

**Suite 3 — Feedback Loop (2/4 passing):** Vague rejection reasons and repeated failure checks pass vacuously (no rejection data exists due to corruption). These passing tests provide no signal — the corruption is the root problem.

**Suite 4 — Registry Consistency (3/3 passing):** Registry is clean. Only active task is this integration-test session itself. No phantom tasks, no ghost sessions, no stale completed entries.

**Suite 5 — CI Pipeline (5/6 passing):** All four CI scripts exist and are executable. 27 tests in the test suite (above 6 minimum). CI failure is purely from feedback.json corruption — the CI infrastructure itself is sound.

**Suite 6 — Brain Integrity (14/14 passing):** All 10 critical brain files exist and are non-empty. All JSON files parse cleanly (feedback.json is valid JSON — just wrong structure). Brain directory is 1.01MB. Reference library intact.

**Suite 7 — Integration Contract (4/4 passing):** DB connection established. WAL mode active. Clean trader pool: 11,847 (well above 450 threshold — threshold should be reviewed upward). Clean markets: 13,191 (above 11,000 threshold).

---

## Suite Details

### Suite 1 — Signal Bus Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal_bus_not_empty | ✅ PASS | 19 signals in bus |
| no_stuck_signals | ✅ PASS | All signals processed/completed/active/resolved — none pending >48h |
| expected_signal_types_present | ❌ FAIL | Missing in last 7 days: revalidation_requested, validation_complete, str003_directional_single |
| validation_pipeline_complete | ✅ PASS | All validation_requested signals have matching completions |

### Suite 2 — Agent Output Integrity
| Test | Result | Detail |
|------|--------|--------|
| signal-agent_output_recent | ❌ FAIL | 105.7h since last output (max 4h) — file: 2026-05-13-14-signal-report.md |
| signal-agent_output_non_empty | ✅ PASS | 11,041 bytes |
| quant-research-agent_output_recent | ❌ FAIL | 512.2h since last output (max 72h) — file: rq2_2_results.json |
| quant-research-agent_output_non_empty | ✅ PASS | 641 bytes |
| backtest-agent_output_recent | ✅ PASS | 107.9h (max 168h) — 2026-05-13-RQ0-data-integrity-gates.json |
| backtest-agent_output_non_empty | ✅ PASS | 4,048 bytes |
| research-scout-agent_output_recent | ✅ PASS | 2.9h (max 26h) — 2026-05-17-12-arxiv-quantitative-finance.md |
| research-scout-agent_output_non_empty | ✅ PASS | 1,022 bytes |
| performance-analyst-agent_output_recent | ✅ PASS | 108.0h (max 168h) — 2026-05-13-weekly.md |
| performance-analyst-agent_output_non_empty | ✅ PASS | 27,954 bytes |

### Suite 3 — Feedback Loop Integrity
| Test | Result | Detail |
|------|--------|--------|
| feedback_file_has_entries | ❌ FAIL | feedback.json overwritten with scout cycle data — 0 approved, 0 rejected |
| feedback_updated_recently | ❌ FAIL | 0 feedback entries in last 7 days (data destroyed) |
| rejection_reasons_specific | ✅ PASS | No rejections exist (vacuously true) |
| no_repeated_failures | ✅ PASS | No repeated failures (vacuously true) |

### Suite 4 — Registry Consistency
| Test | Result | Detail |
|------|--------|--------|
| no_phantom_tasks | ✅ PASS | 1 running task matches active tmux session |
| no_ghost_sessions | ✅ PASS | No unregistered tmux sessions (excluding orchestrator) |
| registry_not_stale | ✅ PASS | No completed tasks older than 30 days |

### Suite 5 — CI Pipeline Integrity
| Test | Result | Detail |
|------|--------|--------|
| ci/run_ci.sh executable | ✅ PASS | Exists and executable |
| ci/lint.sh executable | ✅ PASS | Exists and executable |
| ci/run_tests.sh executable | ✅ PASS | Exists and executable |
| ci/validate_backtest.py executable | ✅ PASS | Exists and executable |
| ci_pipeline_passes | ❌ FAIL | test_registry.py::test_feedback_file_structure — feedback.json lacks 'approved' key |
| test_suite_has_coverage | ✅ PASS | 27 tests (min 6) |

### Suite 6 — Brain Directory Integrity
| Test | Result | Detail |
|------|--------|--------|
| brain_file_exists_signals.json | ✅ PASS | 30,132 bytes |
| brain_file_exists_feedback.json | ✅ PASS | 459 bytes (valid JSON, wrong structure — see Suite 3) |
| brain_file_exists_priorities.md | ✅ PASS | 6,548 bytes |
| brain_file_exists_kpis.md | ✅ PASS | 12,302 bytes |
| brain_file_exists_definition_of_done.md | ✅ PASS | 2,089 bytes |
| brain_file_exists_model-routing.md | ✅ PASS | 23,986 bytes |
| brain_file_exists_research-directions.md | ✅ PASS | 50,953 bytes |
| brain_file_exists_ml-in-finance-notes.md | ✅ PASS | 26,423 bytes |
| brain_file_exists_lopez-de-prado-notes.md | ✅ PASS | 37,853 bytes |
| brain_file_exists_ernest-chan-algo-trading-notes.md | ✅ PASS | 48,421 bytes |
| json_valid_signals.json | ✅ PASS | Valid JSON |
| json_valid_feedback.json | ✅ PASS | Valid JSON (wrong structure — detected in Suite 3) |
| json_valid_agent_registry.json | ✅ PASS | Valid JSON |
| brain_has_content | ✅ PASS | 1.01 MB |

### Suite 7 — Integration Contract
| Test | Result | Detail |
|------|--------|--------|
| contract_db_connectable | ✅ PASS | Connected to polymarket_tracker.db |
| contract_wal_mode | ✅ PASS | journal_mode=wal |
| contract_clean_pool | ✅ PASS | clean_pool=11,847 (expected >=450) |
| contract_clean_markets | ✅ PASS | clean_markets=13,191 (expected >=11,000) |

---

## System Health Assessment

The system is in a partially degraded state with one high-severity data corruption issue that requires immediate manual intervention. The infrastructure layer is solid: CI scripts are executable, the DB is healthy and WAL-mode active, the brain files are intact, and the registry is clean with no phantom or ghost sessions. Three agents ran successfully this week — backtest-agent, research-scout-agent, and performance-analyst-agent are all within cadence and producing substantive output.

The critical problem is `brain/feedback.json`, which has been overwritten by research-scout-agent with a scout cycle summary. This is a path routing bug in the research-scout task template: the agent is treating feedback.json as its own output file, destroying the approval/rejection memory that all other agents depend on. Because feedback-loop-agent ran 6 cycles (last May 13) but the data was overwritten, the actual learning memory is more substantial than the file currently shows — it exists in git history and can be recovered. The CI failure is entirely downstream of this corruption.

The second concern is two agents that are significantly outside cadence. Signal-agent has not produced output in 4.4 days (designed for 4-hour cycles), meaning active signals are stale. Quant-research-agent has been idle for 21 days — this is a direct blocker to Phase 2 and Phase 5 gate criteria, since RQ1.1 and RQ3.2 remain unvalidated. Neither of these requires infrastructure fixes; both require a manual `spawn_agent.sh` call.

In summary: one action requires Oscar's manual file restoration (feedback.json from git), and two require spawning stalled agents (signal-agent, quant-research-agent). If these three actions are taken before Monday morning, the system will be fully operational entering the week.

## Improvements Since Last Report (May 12)
- signals.json: was empty → now has 19 signals ✅
- CI scripts: permission denied → all executable ✅
- DB: was malformed → healthy, WAL-mode, 13,191 clean markets ✅
- Registry: had phantom tasks → fully clean ✅
- feedback-loop-agent: 1 run → 6 runs (feedback_loop_state.json) ✅

## Consecutive Failure Watch
| Test | May 12 | May 17 | Status |
|------|--------|--------|--------|
| signal-agent_output_recent | ❌ FAIL | ❌ FAIL | **2 consecutive — watch** |
| quant-research output | ❌ FAIL | ❌ FAIL | **2 consecutive — watch** |
| feedback_updated_recently | ❌ FAIL | ❌ FAIL | **2 consecutive — watch** |
| feedback_file_has_entries | ✅ PASS* | ❌ FAIL | New failure — CRITICAL severity |

*May 12: feedback.json had correct structure but empty entries

Note: May 13 and May 14 reports were produced by a local Tier 2 model which fabricated results — excluded from consecutive failure tracking per model-routing.md commit history.
