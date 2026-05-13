# Decision Record — 2026-05-13

**Type:** Alert + Interpretation  
**Raised by:** performance-analyst-agent (weekly run 2)  
**Status:** Pending Oscar action

---

## Issue 1 — Agent Pipeline Stall (HIGH)

Signal-agent, quant-research-agent, and backtest-agent have all been stalled for 12–15 days as of 2026-05-13. The integration test (2026-05-12, 83.7% pass rate) flagged signal-agent and quant-research-agent as HIGH severity failures.

**Immediate actions required:**
1. Spawn signal-agent at Tier 3: `./scripts/spawn_agent.sh signal-$(date +%Y%m%d) signal-agent 3 "Routine signal scan and rescan"`
   - Rationale: Putin invasion market resolves June 2026 (~4 weeks). 5 STR-003 signals unrescanned.
2. Spawn backtest-agent to process RQ0.1 + RQ0.2 revalidation requests (filed 2026-05-07, unprocessed)
   - Rationale: Monthly data integrity gates are 45 days overdue.
3. Schedule quant-research-agent for RQ1.1 pre-registration by 2026-05-20
   - Rationale: RQ1.1 rerun due June 1. Pre-registration must precede the run.

---

## Issue 2 — Brier Score 0.3128 Interpretation

The 7-day Brier score is 0.3128 (worse than 0.25 naive baseline), arising entirely from 2 markets:
- Russia/Ukraine ceasefire (STR-004 founding case failure — legendary YES bets wrong)
- Bitcoin >$75K (split position outcomes)

**Decision:** Do not treat this as a systemic calibration failure. The ELO QUALIFIED consensus accuracy (92% at 7d, 85.7% at 30d) is improving and confirms the signal edge is real. The Brier metric at n=2 markets is not informative.

**Threshold for concern:** If Brier > 0.25 (worse than random) persists for 3+ consecutive weekly runs across ≥5 unique markets, then initiate ELO recalibration investigation. That threshold has not been met.

---

## Issue 3 — Research Pool Discrepancy (MEDIUM)

Live DB query returns 604 traders with research_excluded=0, but integration-health.json (06:03 today) shows authoritative pool = 493. 111 traders are tagged research_excluded=0 without meeting explicit criteria.

**Decision:** Use integration-health.json value (493) as authoritative for research calculations until code-hygiene-agent investigates the discrepancy. All research queries should add explicit criteria filters in addition to research_excluded=0.

**Action:** Add to next code-hygiene-agent task queue.
