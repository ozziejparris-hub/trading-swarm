# Integration Test Report — 2026-06-14

**Agent:** integration-test-agent (Tier 3 — claude-sonnet-4-6)
**Task ID:** integration-20260614
**Started:** 2026-06-14T23:00:01Z
**Completed:** 2026-06-14T23:20Z

---

## Result: ❌ 6 FAILURES

## Test Summary

| Metric | Value |
|--------|-------|
| Total tests | 45 |
| Passed | 39 |
| Failed | 6 |
| Pass rate | 86.7% |

---

## Escalation Required

| Test | Consecutive Failures | Action |
|------|---------------------|--------|
| `ci_pipeline_passes` | 7th Sunday | 🚨 HIGH priority Telegram escalation |
| `expected_signal_types_present` | 7th Sunday | 🚨 HIGH priority Telegram escalation (test spec + timezone bug, not real failure) |
| `quant-research-agent_output_recent` | 3rd Sunday | 🚨 HIGH priority Telegram escalation (systemic threshold reached) |
| `signal-agent_output_recent` | 5th+ Sunday | 🚨 HIGH priority Telegram escalation (ongoing) |

---

## ❌ Failures (action required)

### 1. `ci_pipeline_passes` — CRITICAL (7th consecutive)

- **Suite:** 5 — CI Pipeline Integrity
- **What failed:** CI lint step fails. Two lint errors in two files:
  - `scripts/calculate_geo_elo.py`: 8 × F541 (f-strings missing placeholders) at lines 449, 450, 479, 480, 506, 507, 516, 517. Same as last week.
  - `scripts/run_trader_profiling.py`: 1 × E722 (bare `except:`) at line 271. **New this week.**
- **Context:** 27/27 pytest tests still pass. Only lint blocks CI. The F541 errors are literal markdown strings with unnecessary `f""` prefix (cosmetic). The E722 bare except is a new issue introduced into run_trader_profiling.py since last week's audit.
- **Recommended fix:**
  ```bash
  # F541 — remove f prefix from 8 literal strings in calculate_geo_elo.py
  # lines 449, 450, 479, 480, 506, 507, 516, 517:
  # e.g.  f"| Metric | Value |"  →  "| Metric | Value |"

  # E722 — replace bare except in run_trader_profiling.py:271:
  # except:  →  except Exception:
  ```
  Nine one-line fixes. Run `bash ci/run_ci.sh` to confirm clean.
- **Severity:** CRITICAL — CI is the validation gate for all agent code. 7th consecutive Sunday. Two lint sources now.

---

### 2. `expected_signal_types_present` — MEDIUM (7th consecutive — compound issue)

- **Suite:** 1 — Signal Bus Integrity
- **What failed:** Test reports 0 signal types in last 7 days. Expected: `{revalidation_requested, validation_complete, str003_directional_single}`.
- **Root cause (two issues):**
  1. **Timezone comparison bug:** All signal timestamps use 'Z' suffix (e.g., `2026-06-12T20:04:35Z`). The test uses `datetime.utcnow()` (naive) and compares with `datetime.fromisoformat()` results (timezone-aware), raising a silent `TypeError` for every signal. All are skipped → empty set.
  2. **Stale spec names:** Even with the bug fixed, the expected type names are from an earlier spec version. Actual types present in the last 7 days (verified with correct tz-aware comparison): `{contract_fresh, contract_violation, telegram_notification}`.
- **Signal bus reality:** The bus IS active. Three signal types from three agents in 7 days: `contract_fresh` from code-hygiene-agent (June 12, 2 days ago), `contract_violation` and `telegram_notification` from performance-analyst-agent (June 8, 6 days ago).
- **Recommended fix (Oscar approval required):**
  1. Fix timezone comparison in integration test template: use `datetime.now(timezone.utc)` and `ts_str.replace('Z', '+00:00')` before `fromisoformat()`.
  2. Update `expected_types` set:
     ```python
     expected_types = {
         'directional_signal_detected',   # active market signals
         'contract_fresh',                # contract health from code-hygiene
         'telegram_notification',         # escalation signals
     }
     ```
- **Severity:** MEDIUM — signal bus is functioning correctly. Two compound test defects.

---

### 3. `signal-agent_output_recent` — HIGH (5th+ consecutive, worsening)

- **Suite:** 2 — Agent Output Integrity
- **What failed:** signal-agent last output `2026-06-08-08-signal-report.md`, **158.9 hours ago** (threshold: 4h).
- **Context:** The signal-agent task `signal-202606042140` is now marked `failed` in the registry (was `respawning` last week — cleaned up via commit b15e4eb). No signal-agent session is active. Most recent output June 8 was 158.9h ago; last week was 73.2h ago — gap is widening. No regular cadence agent is spawned to fill this.
- **Recommended fix:** Spawn signal-agent for regular cadence:
  ```bash
  cd /home/parison/trading-swarm
  ./scripts/spawn_agent.sh signal-$(date +%Y%m%d%H%M) signal-agent 3 "Regular cadence recovery — score Peru election outcomes (STR003-005/006 resolved June 7), run STR-003 rescan"
  ```
  Note: Peru signals (STR003-005 Keiko Fujimori, STR003-006 López Aliaga) resolved June 7 and remain unscored — LEGENDARY geo_elo signals, first validation opportunity.
- **Severity:** HIGH — primary market monitoring is dark. Worsening week-on-week.

---

### 4. `quant-research-agent_output_recent` — HIGH (3rd consecutive — systemic threshold)

- **Suite:** 2 — Agent Output Integrity
- **What failed:** Most recent quant-research output `geo_elo_findings.md`, **149.7 hours ago** (~June 8, threshold: 72h).
- **Context:** Improved from 294.9h last week — geo_elo_findings.md was produced around June 8, indicating some activity. However 149.7h still far exceeds the 72h threshold. Approved hypothesis RQ-GEO-ELO-001 (Phase 1: full geo_elo calculation, Oscar-approved 2026-05-25) has not been executed. This is the 3rd consecutive Sunday failure, crossing the systemic-issue threshold.
- **Output directory snapshot:** GEO-ELO-001 (May 25), GEO-ELO-003 (May 26), LH-001 (May 20), RQ1.1 (May 1), RQ2.2 (Apr 26), RQ3.2 (Apr 26). Research pipeline not advancing.
- **Recommended fix:** Spawn quant-research-agent:
  ```bash
  cd /home/parison/trading-swarm
  ./scripts/spawn_agent.sh research-$(date +%Y%m%d%H%M) quant-research-agent 3 "RQ-GEO-ELO-001 Phase 1: Calculate geo_elo for all traders using Geopolitics+Elections trades. Pre-reg: brain/strategy-notes/rq-geo-elo-preregistration-2026-05-25.md. Oscar-approved 2026-05-25."
  ```
- **Severity:** HIGH — research pipeline stalled 6+ days. Phase 5 Gate 4 (RQ1.1 + RQ3.2) requires completed research. 3rd consecutive Sunday = systemic escalation.

---

### 5. `backtest-agent_output_recent` — MEDIUM (2nd consecutive, worsening significantly)

- **Suite:** 2 — Agent Output Integrity
- **What failed:** Most recent backtest output `LH-001-validation-v2.md`, **342.4 hours ago** (~May 29, threshold: 168h).
- **Context:** Worsened from 174.5h last week to 342.4h this week — doubled without new output. The LH-001 (information-leakage hypothesis) was the last backtest produced. GEO-ELO-003 OOS validation signal is processed (status `processed` in pending array). No active backtest task outstanding. Backtest-agent appears to have gone dormant after completing LH-001 work.
- **Recommended fix:** Monitor until next research output triggers a backtest. If no new output by Jun 21 (next Sunday), spawn backtest-agent to process the GEO-ELO OOS validation queue. The `pending` array in signals.json has an `OOS validation complete — CONDITIONAL result` entry worth actioning.
- **Severity:** MEDIUM — 2nd Sunday, no active backtest task blocked. Escalate if 3rd Sunday.

---

### 6. `feedback_updated_recently` — MEDIUM (3rd consecutive)

- **Suite:** 3 — Feedback Loop Integrity
- **What failed:** 0 entries written to feedback.json (approved, rejected, or scout_cycles) in last 7 days. Most recent scout_cycle: 2026-05-13 (32 days ago). Most recent approved/rejected entry: 2026-04-27 (48 days ago).
- **Context:** Research-scout is clearly active (5 files in pending-review from today, 4 approved items from June 6-8). However, none of the scout runs are writing `scout_cycle` entries to feedback.json. The 14 existing scout_cycles stop at May 13. This is a logging gap — agent runs successfully but misses the feedback.json update step.
- **Recommended fix:** Verify the scout_cycle logging step in the research-scout-agent task template. The next scout run should explicitly append a `scout_cycle` entry to feedback.json. Check whether the Jun 6-7 approved files (now 8 days old) have any corresponding log entries.
- **Severity:** MEDIUM — 3rd consecutive Sunday. Feedback.json integrity passes; the system isn't forgetting what it knows, but the learning audit trail is degrading.

---

## ✅ Passed Suites

### Suite 1 — Signal Bus (3/4 passed)
Signal bus is active and communicating. 7 signals total (6 processed, 1 completed). No stuck pending signals in either the main array or the pending array. The bus has been active in the last 7 days with 3 signal types from 3 different agents: `contract_fresh` (code-hygiene, June 12), `contract_violation` + `telegram_notification` (performance-analyst, June 8). The `expected_signal_types_present` failure is a test defect, not a bus failure.

### Suite 2 — Agent Outputs (7/10 passed)
Research-scout-agent **PASSES** this week after 3 consecutive failures — 5 fresh files in `brain/research-scout/pending-review/` from today's scan (arxiv papers 2605-00493, 2605-02287, 2606-07811 plus Polymarket API and V2 upgrade items). Performance-analyst is within cadence (160.9h of 168h allowed; 2026-06-08-weekly.md written on schedule). All output files that exist are substantive in size.

### Suite 3 — Feedback Loop (3/4 passed)
Feedback.json structurally intact: 4 approved, 1 rejected, 14 scout_cycles. Rejection reason for STR-001 is specific (127 chars). No repeated failures. The staleness is a logging gap in the scout cycle audit trail, not structural corruption.

### Suite 4 — Registry Consistency (3/3 passed) — FULL PASS
Registry is clean and accurate. 2 tasks: `integration-20260614` (running, tmux confirmed active) and `signal-202606042140` (failed — correctly resolved from respawning state via commit b15e4eb). No phantom tasks, no ghost sessions, no stale completed entries.

### Suite 5 — CI Pipeline (5/6 passed)
All 4 CI scripts exist and are executable. Test suite: 27/27 passed. Test coverage well above threshold (27 vs ≥6). Only the lint gate blocks CI.

### Suite 6 — Brain Integrity (14/14 passed) — FULL PASS
All 10 critical brain files exist and are non-empty. All 3 JSON files parse correctly. Brain directory: **2.42 MB** (growing). Notable file sizes: `brain/strategy-notes/research-directions.md` 74.5KB (grew from 65KB last week); `brain/signals.json` 37.6KB (grew from 25KB); `brain/agent-outputs/integration-test/` accumulating.

| File | Size |
|------|------|
| brain/signals.json | 37,561 bytes |
| brain/feedback.json | 44,012 bytes |
| brain/priorities.md | 6,548 bytes |
| brain/kpis.md | 14,401 bytes |
| brain/definition_of_done.md | 2,089 bytes |
| brain/model-routing.md | 24,299 bytes |
| brain/strategy-notes/research-directions.md | 74,480 bytes |
| brain/reference-library/ml-in-finance-notes.md | 26,423 bytes |
| brain/reference-library/lopez-de-prado-notes.md | 37,853 bytes |
| brain/reference-library/ernest-chan-algo-trading-notes.md | 48,421 bytes |

### Suite 7 — Integration Contract (4/4 passed) — FULL PASS, STRONG GROWTH
Database healthy and growing rapidly this week:

| Test | Result | Detail |
|------|--------|--------|
| `contract_db_connectable` | ✅ PASS | Connected: polymarket_tracker.db |
| `contract_wal_mode` | ✅ PASS | journal_mode=wal |
| `contract_clean_pool` | ✅ PASS | 24,674 traders (threshold ≥10,000; +2,752 from last week's 21,922) |
| `contract_clean_markets` | ✅ PASS | 24,494 markets (threshold ≥16,000; +6,453 from last week's 18,041) |

Clean markets grew +6,453 in one week — the fastest single-week growth yet. Research data foundation is excellent.

---

## Suite Details

### Suite 1 — Signal Bus Integrity

| Test | Result | Detail |
|------|--------|--------|
| `signal_bus_not_empty` | ✅ PASS | 7 signals in bus |
| `no_stuck_signals` | ✅ PASS | 0 stuck pending signals (main array: all processed/completed; pending array: 2 items with processed/approved status) |
| `expected_signal_types_present` | ❌ FAIL | Test bug: timezone-naive vs timezone-aware comparison silently skips all signals. Actual recent types (tz-aware): {contract_fresh, contract_violation, telegram_notification} |
| `validation_pipeline_complete` | ✅ PASS | No unmatched validation_requested signals with `processed` status |

**Signal bus activity (last 7 days, actual):**

| Age | Type | From | Status |
|-----|------|------|--------|
| 2 days | contract_fresh | code-hygiene-agent | processed |
| 6 days | contract_violation | performance-analyst-agent | processed |
| 6 days | telegram_notification | performance-analyst-agent | processed |

**STR003 signal tracker:**

| Signal | Market | Direction | Outcome | Notes |
|--------|--------|-----------|---------|-------|
| STR003-005 | Keiko Fujimori wins 2026 Peru | YES | ❓ Unscored | Resolved June 7 — score immediately |
| STR003-006 | López Aliaga wins 2026 Peru | YES | ❓ Unscored | Resolved June 7 — score immediately |
| STR003-001 | Newsom dropout before Sept | NO | ❓ Pending | Resolves 2026-09-01 |
| STR003-004 | Putin invades by June 2026 | NO | ❓ Pending | Resolves 2026-06-30 (imminent) |
| STR003-003 | Trump nominates Warsh | NO | ❌ WRONG | Resolved 2026-04-04 |

---

### Suite 2 — Agent Output Integrity

| Agent | Recency | Size | Age | Threshold | Most Recent File |
|-------|---------|------|-----|-----------|-----------------|
| signal-agent | ❌ FAIL | ✅ PASS | 158.9h | max 4h | 2026-06-08-08-signal-report.md |
| quant-research-agent | ❌ FAIL | ✅ PASS | 149.7h (~6.2d) | max 72h | geo_elo_findings.md |
| backtest-agent | ❌ FAIL | ✅ PASS | 342.4h (~14.3d) | max 168h | LH-001-validation-v2.md |
| research-scout-agent | ✅ PASS | ✅ PASS | 3.0h | max 26h | 2026-06-14-20-arxiv-2606-07811... |
| performance-analyst-agent | ✅ PASS | ✅ PASS | 160.9h | max 168h | 2026-06-08-weekly.md |

---

### Suite 3 — Feedback Loop Integrity

| Test | Result | Detail |
|------|--------|--------|
| `feedback_file_has_entries` | ✅ PASS | 4 approved, 1 rejected, 14 scout_cycles |
| `feedback_updated_recently` | ❌ FAIL | 0 entries in last 7 days; last scout_cycle 2026-05-13 (32 days ago) |
| `rejection_reasons_specific` | ✅ PASS | All rejection reasons ≥20 chars (STR-001: 127 chars) |
| `no_repeated_failures` | ✅ PASS | No duplicate rejection descriptions |

---

### Suite 4 — Registry Consistency

| Test | Result | Detail |
|------|--------|--------|
| `no_phantom_tasks` | ✅ PASS | 1 running task (integration-20260614) — tmux session confirmed active |
| `no_ghost_sessions` | ✅ PASS | No sessions outside registry |
| `registry_not_stale` | ✅ PASS | 0 completed tasks older than 30 days |

**Registry state:** 2 tasks. `signal-202606042140` now correctly `failed` (resolved from `respawning` via commit b15e4eb — zombie cleaned up). `integration-20260614` running (this session).

---

### Suite 5 — CI Pipeline Integrity

| Test | Result | Detail |
|------|--------|--------|
| `ci/run_ci.sh` exists+executable | ✅ PASS | OK |
| `ci/lint.sh` exists+executable | ✅ PASS | OK |
| `ci/run_tests.sh` exists+executable | ✅ PASS | OK |
| `ci/validate_backtest.py` exists+executable | ✅ PASS | OK |
| `ci_pipeline_passes` | ❌ FAIL | Lint: 8×F541 in calculate_geo_elo.py + **new** 1×E722 in run_trader_profiling.py:271. Tests: 27/27 passed. |
| `test_suite_has_coverage` | ✅ PASS | 27 tests (threshold: ≥6) |

**New this week:** E722 bare `except:` at `scripts/run_trader_profiling.py:271` — not present in last week's audit. A new lint source was introduced this week.

---

### Suite 6 — Brain Integrity: 14/14 PASS (see above)

### Suite 7 — Integration Contract: 4/4 PASS (see above)

---

## Consecutive Failure Tracking

| Test | May-12 | May-13 | May-14 | May-17 | May-24 | May-31 | Jun-07 | Jun-14 | Streak | Action |
|------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| `ci_pipeline_passes` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **7** | 🚨 ESCALATE |
| `expected_signal_types_present` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **7** | 🚨 ESCALATE (test bug) |
| `signal-agent_output_recent` | ❌ | ✅ | — | ❌ | ❌ | ❌ | ❌ | ❌ | **5+** | 🚨 ESCALATE |
| `quant-research-agent_output_recent` | — | — | — | — | ✅ | ❌ | ❌ | ❌ | **3** | 🚨 ESCALATE |
| `feedback_updated_recently` | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | **3** | Monitor → ESCALATE next |
| `backtest-agent_output_recent` | — | — | — | — | — | — | ❌ | ❌ | **2** | Watch |
| `feedback_file_has_entries` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | **FIXED** | ✅ |
| `research-scout-agent_output` | — | — | — | — | ❌ | ❌ | ❌ | ✅ | **RESET** | ✅ |

---

## Phase 5 Gate Status

| Gate | Criteria | Status | Evidence |
|------|----------|--------|----------|
| 1 | feedback-loop-agent ≥4 weekly runs | ✅ MET | Run #10 completed 2026-06-05 (10 runs total) |
| 2 | findings.json ≥3 HIGH confidence findings | ✅ MET | RQ-CONTESTED-001 (n=101), Pool C geo (n=444), QUALIFIED geo (n=167) |
| 3 | Pre-resolution accuracy ≥60% (STR-002, 10+ markets) | ⏳ Monitoring | Peru signals (STR003-005/006) unscored; Putin (STR003-004) resolves June 30 |
| 4 | RQ1.1 and RQ3.2 both passed | ⏳ Blocked | RQ1.1 rescheduled 2026-07-01 (insufficient n). RQ3.2 passed. |

**Gates 1 and 2 met. Gates 3 and 4 blocking Phase 6.**

---

## System Health Assessment

The swarm is structurally sound — all brain files intact, all JSON valid, database growing strongly (+6,453 clean markets in a week), and the registry is clean. The most meaningful positive development this week is the research-scout RESET: after three consecutive output failures, the scout ran today and produced five new items in pending-review (three arxiv papers and two Polymarket API developments). The code-hygiene-agent's `contract_fresh` signal on June 12 confirms at least one agent is running on schedule and communicating through the signal bus. The performance-analyst continues its Monday cadence (2026-06-08-weekly.md within 168h window).

However, three structural issues persist unchanged from last week. The CI lint gate is in its 7th consecutive failed Sunday — now with a second lint file (E722 in run_trader_profiling.py) joining the original F541 cluster in calculate_geo_elo.py. These are nine trivially-fixable lines that have now blocked the validation gate for 49 days. The signal-agent has been dark for 158.9 hours — the Peru election signals (Keiko Fujimori and López Aliaga, both resolved June 7) remain unscored, meaning the first LEGENDARY geo_elo signal validation is sitting uncompleted for the second week in a row. And the quant-research pipeline, though slightly improved (149.7h vs 294.9h last week), has crossed the 3-Sunday threshold and is now a systemic issue requiring escalation.

The `feedback_updated_recently` failure entering its third consecutive week is a quiet compounding risk: research-scout is running and producing output, but the scout_cycle audit log in feedback.json stopped updating May 13 (32 days ago). Agents that read feedback.json before starting will see an increasingly stale picture of what the system has learned.

**Recommended Monday morning sequence:**
1. Fix CI lint (9-line edit: F541×8 in calculate_geo_elo.py + E722×1 in run_trader_profiling.py) — 7th week, 49-day blockage
2. Score Peru election outcomes (Keiko/López Aliaga, resolved June 7) — first LEGENDARY geo_elo signal validation
3. Spawn signal-agent for regular cadence + STR-003 rescan + Putin market (resolves June 30)
4. Spawn quant-research-agent for RQ-GEO-ELO-001 Phase 1 (approved hypothesis, Oscar-approved May 25)
5. Fix research-scout feedback.json logging — next scout run must write scout_cycle entry
6. Update integration test template: fix timezone comparison + update expected_types set (Oscar approval)
