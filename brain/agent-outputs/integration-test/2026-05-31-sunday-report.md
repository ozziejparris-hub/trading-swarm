# Integration Test Report — 2026-05-31

**Agent:** integration-test-agent (Tier 3 — claude-sonnet-4-6)
**Task ID:** integration-20260531
**Started:** 2026-05-31T23:00:01Z
**Completed:** 2026-05-31T23:30Z

---

## Result: ❌ 7 FAILURES

## Test Summary

| Metric | Value |
|--------|-------|
| Total tests | 45 |
| Passed | 38 |
| Failed | 7 |
| Pass rate | 84.4% |

---

## Escalation Required

Three tests have now breached the 3-consecutive-Sunday escalation threshold.
Telegram alert to orchestrator bot is required before Monday begins.

| Test | Consecutive Failures | Threshold | Action |
|------|---------------------|-----------|--------|
| `ci_pipeline_passes` | 5th Sunday | 3 Sundays | 🚨 HIGH priority escalation |
| `expected_signal_types_present` | 5th Sunday | 3 Sundays | 🚨 HIGH priority escalation |
| `feedback_file_has_entries` | 4th Sunday (since May-14 minus May-13 pass) | 3 Sundays | 🚨 HIGH priority escalation |

---

## ❌ Failures (action required)

### 1. `ci_pipeline_passes` — CRITICAL (5th consecutive)

- **Suite:** 5 — CI Pipeline Integrity
- **What failed:** `tests/test_registry.py::test_feedback_file_structure` fails. The test asserts `"approved" in data` but `brain/feedback.json` contains only `{"scout_cycles": [...]}`. All other 26 tests pass. CI exit code: 2.
- **Root cause:** `brain/feedback.json` was overwritten by research-scout-agent in May with only scout cycle data, destroying the `approved` and `rejected` top-level arrays. This is the same root cause as failures 2 and 3. CI itself (scripts, linting, other tests) is fully healthy.
- **Recommended fix:**
  Restore feedback.json structure manually. The approved/rejected arrays can be reconstructed from git history:
  ```bash
  git log --oneline brain/feedback.json
  # Identify the last clean commit (around 2026-05-13)
  git show <commit>:brain/feedback.json > /tmp/feedback_backup.json
  # Merge scout_cycles from current file with approved/rejected from backup
  ```
  Then add `"approved": []` and `"rejected": []` as top-level keys alongside the existing `scout_cycles` key if git history shows the arrays were empty.
- **Consecutive failures:** 5th Sunday (May-12, May-14, May-17, May-24, May-31). HIGH priority escalation required — threshold breached two Sundays ago.
- **Severity:** CRITICAL — CI is the validation gate for all agent code. This test must pass before any agent Python output can be trusted.

---

### 2. `feedback_file_has_entries` — CRITICAL (4th consecutive since May-14)

- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** `feedback.json` has 0 approved entries, 0 rejected entries. Only `scout_cycles` key present. Same structural corruption as above.
- **Root cause:** Same as failure #1 — research-scout-agent wrote only scout cycle data to feedback.json, overwriting the approved/rejected arrays.
- **Impact:** All agents that read feedback.json before starting (per system design) are reading a file with no learning history. The system cannot benefit from past approval/rejection decisions.
- **Recommended fix:** Same as failure #1 — restore `approved` and `rejected` arrays.
- **Consecutive failures:** 4th Sunday (May-14, May-17, May-24, May-31). Escalation required.
- **Severity:** CRITICAL — the feedback loop is one of the core learning mechanisms of the swarm.

---

### 3. `feedback_updated_recently` — HIGH

- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** 0 entries in the `approved` or `rejected` arrays in the last 7 days. The most recent scout cycle is dated 2026-05-18 (13 days ago) — outside the 7-day window.
- **Root cause:** Downstream of failure #2. With the feedback.json structure broken, no approved/rejected entries are being written.
- **Consecutive failures:** 4th Sunday (May-14, May-17, May-24, May-31).
- **Severity:** HIGH — the feedback loop has been frozen for 4 weeks.

---

### 4. `signal-agent_output_recent` — HIGH (5th consecutive)

- **Suite:** 2 — Agent Output Integrity
- **What failed:** Signal-agent last output was `2026-05-25-08-signal-report.md`, approximately **158.9 hours ago (6.6 days)**. Cadence threshold is 4 hours.
- **Context:** Signal-agent ran a full rescan on 2026-05-25 at 08:00 UTC and has not produced output since. The 4-hour cadence assumes continuous operation; the agent is likely not running in a tmux session (registry shows only this integration-test task as active).
- **Recommended fix:**
  ```bash
  ./scripts/spawn_agent.sh signal-$(date +%Y%m%d%H%M) signal-agent 3 "Cadence recovery — silent since 2026-05-25"
  ```
- **Consecutive failures:** 5th Sunday. Same cadence failure as prior weeks.
- **Severity:** HIGH — signal-agent is the primary market monitoring mechanism.

---

### 5. `quant-research-agent_output_recent` — HIGH

- **Suite:** 2 — Agent Output Integrity
- **What failed:** Most recent quant-research output is `geo_elo_oos_findings.md` from approximately **126.9 hours ago (5.3 days)**. Cadence threshold is 72 hours.
- **Context:** The GEO-ELO-003 OOS study was completed; a validation signal was written to the `pending` section of signals.json on 2026-05-26. That validation has been processed (status: `processed`, 2026-05-27). Quant-research-agent appears to be waiting for backtest-agent to action the GEO-ELO-003 OOS validation before proceeding to the next research task (geo_elo Phase 1, which has Oscar approval from 2026-05-25).
- **Recommended fix:** Confirm backtest-agent has the GEO-ELO-003 OOS pending validation in its queue. Then spawn quant-research-agent to begin geo_elo Phase 1 (calculate geo_elo for all traders using Geopolitics + Elections trades — approved hypothesis from brain/strategy-notes/rq-geo-elo-preregistration-2026-05-25.md).
- **Consecutive failures:** 1st occurrence at this level. Prior reports had quant-research within cadence.
- **Severity:** HIGH — research pipeline has stalled.

---

### 6. `research-scout-agent_output_recent` — HIGH (2nd consecutive)

- **Suite:** 2 — Agent Output Integrity
- **What failed:** Most recent output is `2026-05-19-17-polymarket-exchange-upgrade-clob-v2-live-v1-deprec.md`, approximately **293.1 hours ago (12.2 days)**. Cadence threshold is 26 hours.
- **Context:** 4 pending-review files from the 2026-05-18 scout cycle remain in `brain/research-scout/pending-review/` unreviewed. The agent has not run since May 19. These are actionable findings: DeepSeek V4 preview, ForesightFlow score framework, per-market order flow, Polymarket CLOB v2 exchange upgrade.
- **Recommended fix:** Spawn research-scout-agent for a new daily cycle.
- **Consecutive failures:** 2nd Sunday (May-24, May-31).
- **Severity:** HIGH — the 4 unreviewed findings may include time-sensitive intelligence (especially Polymarket CLOB v2 deprecation of v1).

---

### 7. `expected_signal_types_present` — MEDIUM (5th consecutive, test spec issue)

- **Suite:** 1 — Signal Bus Integrity
- **What failed:** Expected signal types `revalidation_requested`, `validation_complete`, `str003_directional_single` are absent from the signal bus in the last 7 days.
- **Root cause (previously identified):** These are old type names from an earlier version of the signal spec. The system now uses: `validation_requested`, `hypothesis_ready`, `rescan_complete`, `rq1_1_insufficient_n`, `str003_active`. The test specification has not been updated to match the evolved signal type vocabulary.
- **Recommended fix:** Update the `expected_types` set in the integration-test task template to match current signal types:
  ```python
  expected_types = {
      'validation_requested',
      'rescan_complete',
      'str003_active',
  }
  ```
- **Consecutive failures:** 5th Sunday. This is a test specification bug, not a system failure. However, per escalation rules, it requires HIGH priority escalation after 3 consecutive Sundays. Oscar should confirm the fix and approve the template update.
- **Severity:** MEDIUM as a system concern. The signal bus itself is functioning correctly with evolved type names.

---

## ✅ Passed Suites

### Suite 1 — Signal Bus (3/4 passed)
Signal bus is operational with 1 completed validation signal, 3 pending-section entries, 1 rescan log entry, and 4 active STR003 signals. No signals stuck >48h in the main `signals` array. **Note:** `rq1_1_insufficient_n` in the `pending` section has status `pending` for ~100 hours (timestamp 2026-05-27T17:41:38Z) — this is an informational signal about rescheduling RQ1.1 to 2026-07-01 and does not require immediate processing, but should be acknowledged by the orchestrator.

### Suite 2 — Agent Outputs (7/10 passed)
Backtest-agent and performance-analyst-agent are within cadence and producing substantive work. Backtest delivered LH-001-validation-v2.md (16,548 bytes) and performance-analyst delivered 2026-05-25-weekly.md (33,289 bytes) within the 168-hour window. Three agents (signal, quant-research, research-scout) are outside cadence.

### Suite 3 — Feedback Loop (2/4 passed)
No vague rejection reasons, no repeated failures — both trivially true given the structural corruption. The mechanics of the feedback system are sound; only the data file is compromised.

### Suite 4 — Registry Consistency (3/3 passed)
Registry is clean. One active task (this integration-test run). No phantom tasks, no ghost tmux sessions, no stale completed entries.

### Suite 5 — CI Pipeline (5/6 passed)
All 4 CI scripts (run_ci.sh, lint.sh, run_tests.sh, validate_backtest.py) exist and are executable. 27 tests in the test suite. CI infrastructure is fully sound — failure is purely from the feedback.json structure bug.

### Suite 6 — Brain Integrity (14/14 passed)
All 10 critical brain files exist and are non-empty. All 3 JSON files are valid. Brain directory is 1.38 MB. No corruption detected. Brain is healthy.

### Suite 7 — Integration Contract (4/4 passed)
Database is connectable and in WAL mode. Clean pool: **16,455 traders** (threshold 450) — substantial growth from the 493 baseline set on 2026-05-07, reflecting normal trader onboarding. Clean markets: **16,162** (threshold 11,000). Integration contract is satisfied with significant headroom.

---

## Suite Details

### Suite 1 — Signal Bus Integrity

| Test | Result | Detail |
|------|--------|--------|
| `signal_bus_not_empty` | ✅ PASS | 1 signal in main `signals` array |
| `no_stuck_signals` | ✅ PASS | 0 pending signals in main array |
| `expected_signal_types_present` | ❌ FAIL | Missing: revalidation_requested, validation_complete, str003_directional_single (old type names — test spec stale) |
| `validation_pipeline_complete` | ✅ PASS | No unmatched validation requests |

**Notable:** `rq1_1_insufficient_n` signal (pending section, status: pending, 2026-05-27) informs orchestrator that RQ1.1 has been rescheduled to 2026-07-01 due to only 10 traders meeting both period requirements (minimum: 30). This is correct behaviour — Period 2 (April–June 2026) has not accumulated enough resolved markets. No action needed until July.

**STR003 signal outcomes:**
- STR003-001 (Newsom 2026 dropout NO): unresolved
- STR003-002 (UN Security Council NO): unresolved, stale market flag still active (pending Oscar decision from 2026-05-18)
- STR003-003 (Kevin Warsh Fed chair NO): **INCORRECT** — Trump nominated Warsh on 2026-04-04. outcome_correct=0. First STR-003 outcome scored: WRONG.
- STR003-004 (Putin invades June 2026 NO): unresolved, counter-signal present (YES 12,967 vs NO 7,191)

---

### Suite 2 — Agent Output Integrity

| Agent | Recency | Size | Last Output |
|-------|---------|------|-------------|
| signal-agent | ❌ FAIL (158.9h, max 4h) | ✅ PASS | 2026-05-25-08-signal-report.md |
| quant-research-agent | ❌ FAIL (126.9h, max 72h) | ✅ PASS | geo_elo_oos_findings.md |
| backtest-agent | ✅ PASS (6.4h, max 168h) | ✅ PASS | LH-001-validation-v2.md |
| research-scout-agent | ❌ FAIL (293.1h, max 26h) | ✅ PASS | 2026-05-19-17-polymarket-exchange-upgrade-clob-v2-live-v1-deprec.md |
| performance-analyst-agent | ✅ PASS (6.4h, max 168h) | ✅ PASS | 2026-05-25-weekly.md |

---

### Suite 3 — Feedback Loop Integrity

| Test | Result | Detail |
|------|--------|--------|
| `feedback_file_has_entries` | ❌ FAIL | 0 approved, 0 rejected (approved/rejected arrays absent) |
| `feedback_updated_recently` | ❌ FAIL | 0 entries in last 7 days; last scout_cycle: 2026-05-18 (13 days ago) |
| `rejection_reasons_specific` | ✅ PASS | No rejections to evaluate |
| `no_repeated_failures` | ✅ PASS | No rejections to evaluate |

---

### Suite 4 — Registry Consistency

| Test | Result | Detail |
|------|--------|--------|
| `no_phantom_tasks` | ✅ PASS | 1 running task (this integration-test), session confirmed active |
| `no_ghost_sessions` | ✅ PASS | integration-test-agent-integration-20260531 is registered |
| `registry_not_stale` | ✅ PASS | 0 tasks older than 30 days |

---

### Suite 5 — CI Pipeline Integrity

| Test | Result | Detail |
|------|--------|--------|
| `ci/run_ci.sh` exists+executable | ✅ PASS | OK |
| `ci/lint.sh` exists+executable | ✅ PASS | OK |
| `ci/run_tests.sh` exists+executable | ✅ PASS | OK |
| `ci/validate_backtest.py` exists+executable | ✅ PASS | OK |
| `ci_pipeline_passes` | ❌ FAIL | 1 failed, 26 passed; test_feedback_file_structure fails |
| `test_suite_has_coverage` | ✅ PASS | 27 tests (above 6 minimum) |

---

### Suite 6 — Brain Integrity

| File | Result | Size |
|------|--------|------|
| brain/signals.json | ✅ PASS | 12,956 bytes |
| brain/feedback.json | ✅ PASS | 388 bytes (valid JSON, but structurally incomplete) |
| brain/priorities.md | ✅ PASS | 6,548 bytes |
| brain/kpis.md | ✅ PASS | 15,470 bytes |
| brain/definition_of_done.md | ✅ PASS | 2,089 bytes |
| brain/model-routing.md | ✅ PASS | 23,986 bytes |
| brain/strategy-notes/research-directions.md | ✅ PASS | 59,298 bytes |
| brain/reference-library/ml-in-finance-notes.md | ✅ PASS | 26,423 bytes |
| brain/reference-library/lopez-de-prado-notes.md | ✅ PASS | 37,853 bytes |
| brain/reference-library/ernest-chan-algo-trading-notes.md | ✅ PASS | 48,421 bytes |
| JSON valid — signals.json | ✅ PASS | Valid JSON |
| JSON valid — feedback.json | ✅ PASS | Valid JSON |
| JSON valid — agent_registry.json | ✅ PASS | Valid JSON |
| Brain directory total | ✅ PASS | 1.38 MB |

---

### Suite 7 — Integration Contract

| Test | Result | Detail |
|------|--------|--------|
| `contract_db_connectable` | ✅ PASS | Connected to polymarket_tracker.db |
| `contract_wal_mode` | ✅ PASS | journal_mode=wal |
| `contract_clean_pool` | ✅ PASS | 16,455 traders (threshold: ≥450) |
| `contract_clean_markets` | ✅ PASS | 16,162 markets (threshold: ≥11,000) |

---

## Consecutive Failure Tracking

| Test | May-12 | May-13 | May-14 | May-17 | May-24 | May-31 | Streak | Status |
|------|--------|--------|--------|--------|--------|--------|--------|--------|
| `ci_pipeline_passes` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 4 | 🚨 ESCALATE |
| `expected_signal_types_present` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 4 | 🚨 ESCALATE |
| `feedback_file_has_entries` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 4 | 🚨 ESCALATE |
| `feedback_updated_recently` | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | 2 | Monitor |
| `signal-agent_output_recent` | ❌ | ✅ | — | ❌ | ❌ | ❌ | 3+ | 🚨 ESCALATE |
| `research-scout-agent_output_recent` | — | — | — | — | ❌ | ❌ | 2 | Monitor |
| `quant-research-agent_output_recent` | — | — | — | — | ✅ | ❌ | 1 | Watch |

---

## Phase 5 Gate Status

As of this report, assessed against the 4 integration gate criteria:

| Gate | Criteria | Status |
|------|----------|--------|
| 1 | feedback-loop-agent ≥4 weekly runs | ⏳ Unknown — feedback.json data compromised |
| 2 | findings.json ≥3 HIGH confidence findings | ✅ 11 HIGH findings confirmed |
| 3 | Pre-resolution accuracy ≥60% (STR-002, 10+ markets) | ⏳ Monitoring ongoing |
| 4 | RQ1.1 and RQ3.2 both passed | ❌ RQ1.1 rescheduled to 2026-07-01; RQ3.2 status unknown |

Gate 2 is the only confirmed-met criterion. None of the four gates are fully satisfied. Do not advance to Phase 5.

---

## System Health Assessment

The infrastructure layer of the swarm is solid this week: the database is healthy, brain files are intact, the backtest-agent delivered the LH-001 v2 validation, and the performance-analyst produced the weekly report. The integration contract has significant headroom on both clean trader pool (16,455 vs 450 threshold) and clean markets (16,162 vs 11,000 threshold).

However, the swarm's communication and learning mechanisms remain broken for the fifth consecutive week. The feedback.json structural corruption — first identified on 2026-05-17 — has not been repaired, meaning the CI gate has been blocked for over two weeks and agents are starting each session without access to historical approval/rejection learning. Three agents (signal, research-scout, quant-research) are outside their cadence windows, suggesting the orchestrator is not actively spawning new tasks. The system is producing good individual outputs when manually triggered, but the autonomous weekly rhythm has stalled.

The one notable new development this week: STR003-003 (Kevin Warsh Fed chair, direction NO) resolved **incorrect** on 2026-04-04. This is the first STR-003 signal outcome scored, and it was wrong. With STR003-004 (Putin June 2026 NO) also showing a counter-signal with larger position size, the STR-003 signal quality requires monitoring before Phase 6. The STR-002 concurrent market problem (all 21 verified legendary traders disqualified by excessive concurrent markets) identified on 2026-05-25 also remains unresolved.

**Priority for Monday:** Fix feedback.json (5-minute git restore, unblocks CI and agents). Then spawn signal-agent and research-scout-agent. The swarm has the tools — the plumbing just needs reconnecting.
