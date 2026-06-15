# Decision Record — Phase 5 Gate 3 Risk and Research Pipeline Urgency

**Date:** 2026-06-15
**Author:** performance-analyst-agent (run 7)
**Status:** ASSESSMENT — requires Oscar review

---

## Context

Phase 5 Gate 3 requires ≥60% pre-resolution accuracy across 10+ resolved markets (STR-002/STR-003). As of June 15, 2026, the system has 4 scored signals with 1/4 correct (25%). Gate 4 requires RQ1.1 + RQ3.2 both passed; RQ1.1 is scheduled July 1 but is blocked on RQ-GEO-ELO-001 Phase 1 which has not been executed despite Oscar approval on May 25 (21 days ago).

---

## Assessment: Gate 3 Is At Risk

**Current state:** 1/4 scored STR-003 signals (25%). Minimum needed for gate: 60% across 10+ markets. With 4 signals scored, we need 6 correct from 6 remaining *scorable* signals to reach 60% on 10 total.

**Scorable signals pending:**
- STR003-004 (Putin invades NO) — resolves June 30. Fails geo_elo threshold (trader geo_elo_active = 842.5 < 2175) so may not count toward the formal STR-003 geo_elo gate
- STR003-007 (Iran NO) — resolves June 30. NON-SCORABLE (retrospective discovery per Fable §5.1.3)
- STR003-008 (EU security NO) — resolves June 30. NON-SCORABLE (retrospective discovery)
- STR003-001 (Newsom NO) — resolves September 1. Fails geo_elo threshold.

**Interpretation:** If we use only signals that meet full geo_elo_active criteria, we have effectively 0 additional scorable signals before September. Gate 3 cannot be met under the strict criteria without new signal generation.

**Signal generation capacity has improved:** Legendary_active jumped 13→24 (June 14 Sunday ELO recalc). Signal-agent must rescan immediately to find new positions.

---

## Assessment: Gate 4 Timeline Requires Immediate Action

**Dependency chain:**
1. RQ-GEO-ELO-001 Phase 1 (calculate geo_elo for all traders) → ~3.5h compute
2. RQ-GEO-ELO-001 Phase 2 (re-run accuracy check with new geo_elo tiers) → ~1h
3. RQ-GEO-ELO-001 Phase 3 (propose STR-003 update) → ~30min
4. RQ0.2 screening pass using updated geo_elo
5. RQ1.1 rerun (July 1 deadline) — needs updated geo_elo to compute per-trader ELO in period T
6. RQ3.2 methodology reframe

Total compute: ~5h quant-research time + scheduling overhead. If not started by June 19, the July 1 deadline for RQ1.1 is mathematically impossible.

---

## Recommended Actions for Oscar

1. **THIS WEEK:** Spawn quant-research-agent to execute RQ-GEO-ELO-001 Phase 1 (Oscar already approved May 25). Pre-registration exists at `brain/strategy-notes/rq-geo-elo-preregistration-2026-05-25.md`. No further approval needed — this is executing an already-approved hypothesis.

2. **THIS WEEK:** Spawn signal-agent to: (a) score Peru outcomes, (b) rescan for new signals with expanded legendary_active pool (24 traders), (c) monitor June 30 cluster.

3. **CONSIDER:** Review Gate 3 scoring rules. If STR003-007/008 (Iran/EU security) are excluded from scoring due to retrospective discovery but the directional calls are proving correct (Iran regime has not fallen, market at 0%), there may be a case for a revised methodology that credits the underlying analytical process while excluding the specific signals. This is a judgment call for Oscar.

4. **DECISION PENDING:** Does the Gate 3 assessment use any STR-003 signal that qualifies under the NEW geo_elo_active criteria, or specifically only signals registered through register_signal.py after the standard was established? If retrospective signals count, Iran (STR003-007) being directionally correct helps Gate 3. If not, Gate 3 may require a timeline extension.

---

## Implications for Phase 6 Timing

If Gate 4 (RQ1.1 + RQ3.2) passes July 1 and Gate 3 accumulates sufficient scorable signals from the expanded legendary pool (June 30 onward), Phase 6 entry could occur late July/August 2026. If either gate slips, Phase 6 moves to Q3 2026 or later.

The next 15 days (June 15-30) are the most consequential week-pair in the system's history: the first multi-signal scoring cluster, the largest legendary pool ever available for signal generation, and the July 1 Gate 4 deadline approaching.
