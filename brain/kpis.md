# Current KPIs

Last updated: 2026-03-16
Updated by: Oscar (pre-server baseline — manual entry)
Next update: performance-analyst-agent (every Monday 7am)

---

## How This File Works

This file is the single source of truth for system performance
metrics. It is read by the orchestrator weekly summary and by
the performance-analyst-agent as the baseline for trend analysis.

**Writing protocol:**
- performance-analyst-agent overwrites the "Current Week" section
  every Monday before the 8am Telegram report
- It preserves the "Baseline" section permanently —
  never overwrite or delete the baseline block
- All historical weekly values live in
  /brain/agent-outputs/performance-analyst/ — this file
  holds current values only, not history

---

## System Baseline (March 16 2026)

These are the founding numbers. Every future metric is
measured against this starting point. Do not modify.

### Polymarket Trader Database
```
Total traders tracked:          53,140
ELO range:                      300 – 3,500
Active traders (ELO >= 1550):   677
Legendary traders (ELO >= 2175): ~15
Maximum ELO observed:           3,500 (0xb442, 4 closed positions)
Database size:                  1,581 MB
Worker coverage:                99.7%
Closed positions calculated:    951,694
```

### Calibration Baseline (Brier Scores)
```
Traders with Brier scores:      897
Best Brier score:               0.0798  (superforecaster territory)
Brier score range:              0.08 – 0.89
Traders excellent (< 0.10):     388  (superforecaster tier per Tetlock)
Traders good (0.10 – 0.20):     489
Traders acceptable (0.20-0.25): to be measured
Traders below random (> 0.25):  to be measured
System target Brier:            < 0.20 (minimum)
```

### Risk-Adjusted Performance (Sharpe)
```
Traders with Sharpe data:       761
Sharpe range:                   -1.66 – 1.58
```

### Composite Skill Scores (Phase 3b)
```
Traders scored:                 13,021
ABOVE AVERAGE:                  304
AVERAGE:                        12,715
Below average:                  remainder
```

### Behavioral Scores (March 16 fix applied)
```
timing_score coverage:          3,231 traders
patience_score coverage:        2,194 traders
kelly_alignment_score coverage: 1,153 traders
Note: encoding bug fixed 2026-03-16 (utf-8 flag added)
```

### Kelly Criterion Reference Values
```
Recommended fraction:           0.25x – 0.50x full Kelly
Single position cap:            25% of capital
Correlated position cap:        50% of capital
At 2x Kelly:                    growth rate = 0 (do not exceed)
```

### Validation Thresholds (for backtest-agent)
```
Sharpe minimum:                 1.0 (necessary, not sufficient)
Deflated Sharpe Ratio (DSR):    > 0.95 (required)
PBO maximum:                    < 0.10 (required)
Transaction cost assumed:       2% per trade (Polymarket fee)
Minimum trades in backtest:     30
```

### Brier Score Reference Thresholds
```
Excellent:                      < 0.10  (superforecaster per Tetlock)
Good:                           0.10 – 0.20
Acceptable:                     0.20 – 0.25
Random baseline:                0.25  (always predicting 50%)
System target:                  < 0.20 minimum
```

### Known Issues at Baseline (March 16 2026)
```
- trades.notified / completed / was_successful columns are
  write-only — nothing reads them (low priority hygiene task)
- weighted_consensus_system.py deprecated but still called
  by Phase 2 scheduler (code-hygiene-agent task)
- Worker backlog growing ~150-200/hour — monitor trend
```

---

## Current Week

Last updated: 2026-06-29
Updated by: performance-analyst-agent (run 8 — covers 2 weeks, Jun 15–29)

### Week of 2026-06-29

#### Prediction Accuracy
```
PRIMARY: geo_elo Pool C (Pool C, geo_accuracy_pool=1, geo_elo_active weighted,
         resolved_trades_count>=20):
  GEOPOLITICS ONLY (30d):
    Brier score (30d):                0.2168  ✅ BEST ON RECORD (beats naive 0.2264, n=132)
    Directional accuracy (30d):       69.7%   (92/132 correct)
  ELECTIONS (30d):
    Brier score (30d):                0.2234  (worse than naive 0.2096 ⚠, n=315 — improving)
    Directional accuracy (30d):       67.9%   (214/315 correct)
  COMBINED geo+elections (30d):
    Brier score (30d):                0.2214  (naive 0.2146, n=447)
    Directional accuracy (30d):       68.5%
  COMBINED (7d):
    n=8 markets only — insufficient for trend analysis (Brier 0.4084, 50% acc)

  VALIDATED BASELINE (HIGH confidence, n=444):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  TREND: 3 consecutive weeks improvement in both categories.
  Geo 0.2400→0.2213→0.2168, Elections 0.2982→0.2714→0.2234 — elections fastest-improving.
  Combined Brier 0.2214 is approaching target (<0.20) but not yet there.
  Elections still worse than naive — trajectory positive, not yet resolved.
```

#### ELO System Health
```
Total traders (DB):                146,293  (vs 141,877 Jun 15; +3.1%)
True research pool (resolved≥20):    8,221  (vs 3,902 Jun 15 — +111% jump; large market resolution volume)
Research pool (research_excluded=0): 22,384  (vs 22,224 Jun 15 — stable)
Pool C (geo_accuracy_pool=1):        2,157  ⚠ CONTRACT VIOLATION (threshold 2,500; peaked 3,660 Jun 20)
geo_elo LEGENDARY (geo_elo ≥ 2175):    78   (vs 48 Jun 15 — +63%)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 29  (vs 24 Jun 15 — +21%)
legendary_clean (geo_elo_active≥2175, pool_c, research_excl=0): 16 (vs 17 Jun 15)
near_legendary_clean (geo_elo_active 1800-2174): 41 (vs 22 Jun 15 — +86% ✅)
Inactive LEGENDARY clean (14+ days no trades): 10 of 16 = 62.5% DORMANT ⚠
Max geo_elo_active:                4,009  (0xd44e974a — last trade Jun 20)
Active traders (7d):               679  (vs ~2,573 Jun 15 — sharp drop; investigate)
Trades executed (7d):              66,710  (vs ~80,541 Jun 15 — -17%)
ELO last updated:                  2026-06-27 (daily maintenance — Jun 29 maintenance pending)
Contract violations:               pool_c=2,157 BELOW threshold 2,500 ⚠ (flagged Jun 27)
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria):
  Qualifying traders (active, geo_elo_active≥2175, pool_c): 16 clean
  LEGENDARY with active geo/elections positions: 16
  STR003-005 (Keiko Fujimori YES, Peru):   RESOLVED_CORRECT ✅ (scored Jun 11)
  STR003-006 (López Aliaga YES, Peru):     RESOLVED_WRONG ✗
  STR003-007 (Iran regime NO, June 30):    ACTIVE — resolving TODAY (non-scorable)
  STR003-008 (EU security NO, June 30):    ACTIVE — resolving TODAY (scorable ✅)
  STR003-004 (Putin NO, June 30):          ACTIVE — resolving TODAY (not scorable — fails geo_elo)
  Scored accuracy:                         1/4 (25%) — June 30 adds 1 scorable outcome
  Signal-agent:                            DARK — 14 days (last output Jun 15)

STR-004:               0/1 (founding case ambiguous)
feedback-loop Run 11:  COMPLETE (June 22) — Run 12 due today (Monday)
Gate 3 risk:           HIGH — 62.5% LEGENDARY dormancy limits new signal generation
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 16 clean LEGENDARY, June 30 scoring event TODAY
STR-004:   HYPOTHESIS — 0/1. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 4/7 insider signals correct (57.1%)
RQ1.1:     BLOCKED — RQ-GEO-ELO-001 NOT STARTED (5 weeks), July 1 deadline TOMORROW
RQ3.2:     INCONCLUSIVE — reframe needed
RQ-GEO-ELO-001: APPROVED (May 25) — NOT STARTED ⚠⚠ DEADLINE TOMORROW
RQ-CONTESTED-001: PASS ✅ — QUALIFIED tier 66.3%, n=101
```

#### System Resources
```
Estimated API spend (2w Jun 15-29): ~$2-3  (integration-test ×2, feedback-loop ×1,
                                             training-librarian ×1, code-hygiene ×2,
                                             research-scout ×1, performance-analyst ×1)
trading-swarm orchestrator:       ACTIVE (since Jun 28 07:54 UTC — ⚠ verify with Oscar)
polymarket-monitoring:            ACTIVE
Git commits (trading-swarm, 7d): 9
Git commits (first-repo, 7d):    20+  (data provenance + Tier-2 canonical defs migration)
Brain directory size:             4.4MB (vs 3.3MB Jun 15 — +33%)
First-repo DB size:               11GB (vs 8.9GB Jun 15 — +23.6% ⚠ monitor disk)
Clean markets (DB):               28,608  (+4,114 since Jun 15)
CI pipeline:                      BLOCKED — 8th consecutive Sunday lint failure
Signal-agent:                     DARK — 14+ days (last output Jun 15)
Quant-research:                   DARK — 34 days (last output ~May 26)
Backtest-agent:                   DARK — 29 days (last output May 31)
```

#### Week-on-Week Trends
```
Brier (geopolitics, 30d):            0.2400 (Jun 8) → 0.2213 (Jun 15) → 0.2168 (Jun 29) ↑↑ BEST RECORD
Brier (elections, 30d):              0.2982 (Jun 8) → 0.2714 (Jun 15) → 0.2234 (Jun 29) ↑↑ BEST RECORD
Combined accuracy (30d):             64.96% (Jun 8) → 69.1% (Jun 15) → 68.5% (Jun 29) → stable
Legendary ACTIVE (geo_elo_active≥2175): 13 (Jun 8) → 24 (Jun 15) → 29 (Jun 29) ↑
Legendary CLEAN:                         9 (Jun 11) → 17 (Jun 15) → 16 (Jun 29) → stable
NEAR_LEGENDARY clean:                   18 (Jun 8) → 22 (Jun 15) → 41 (Jun 29) ↑↑ +86%
True research pool (resolved≥20):   1,738 (Jun 8) → 3,902 (Jun 15) → 8,221 (Jun 29) ↑↑
Pool C (geo_accuracy_pool):           504 (Jun 8) → 2,875 (Jun 15) → 2,157 (Jun 29) ↓ DECLINING
Active traders (7d):               2,395 → ~2,573 → 679 ↓↓ INVESTIGATE
Phase 5 Gate 1:                    ✅ COMPLETE (12+/4 runs, last run Jun 22)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5 — 3+/3 HIGH findings)
Phase 5 Gate 3:                    1/5 scorable (STALLED — June 30 adds 1)
Phase 5 Gate 4:                    BLOCKED — RQ-GEO-ELO-001 deadline TOMORROW
```

### Previous Week (2026-06-15 — for reference)

#### Prediction Accuracy
```
Geopolitics Brier (30d):             0.2213  (beats naive ✅, n=79)
Elections Brier (30d):               0.2714  (worse than naive ⚠, n=186)
Combined Brier (30d):                ~0.256  (n=265)
Combined accuracy (30d):             69.1%
```

#### ELO System Health
```
Total traders (DB):                141,877
True research pool (resolved≥20):    3,902  (research_excluded=0, resolved≥20, bot IS NULL)
geo_elo LEGENDARY (geo_elo ≥ 2175):     48
geo_elo_active LEGENDARY:               24
Pool C (geo_accuracy_pool=1):        2,875
legendary_clean:                        17
near_legendary_clean:                   22
Active traders (7d):                ~2,573
Trades executed (7d):              ~80,541
```

---

## Phase 5 Gate Tracker

Last updated: 2026-06-29 (performance-analyst-agent run 8)

```
Gate 1 — Feedback-loop runs: 12+/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday)
  Run 8: 2026-06-05 ✅ COMPLETE (wrote 4 new findings; Phase 5 Gate 2 confirmed)
  Run 9: 2026-06-08 (cron, Monday)
  Run 10: 2026-06-15 (cron, Monday — confirmed gate met)
  Run 11: 2026-06-22 (cron, Monday — confirmed gate met)
  Run 12: 2026-06-29 (cron, Monday — due today)

Gate 2 — HIGH confidence findings: 3+/3 ✅ GATE MET (confirmed 2026-06-05)
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED (contaminated pool, 82% artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57
  ✅ 2026-06-01-GEO-ELO-ACCURACY-001: Pool C 86.36%, n=22 geo 30-day markets
  ✅ 2026-06-03-ELO-VS-MARKET-001: ELO vs market price contested markets, n=746
  ✅ 2026-06-05-CONTESTED-ACCURACY-2026-001: RQ-CONTESTED-001 PASS — QUALIFIED 66.3%, n=101
  ✅ 2026-06-05-POOL-C-GEO-FULL-2026-001: Pool C full 2026 70.7%, LEGENDARY 79.6%, n=444

Gate 3 — Pre-resolution accuracy: 1/4-5 correct STR-003 signals — IN PROGRESS (AT RISK)
  Gate needs: 60% accuracy across 10+ resolved markets
  Scored signals (geo_elo_active criteria):
    STR003-005 (Keiko Peru YES): RESOLVED_CORRECT ✅ (Jun 11)
    STR003-006 (Aliaga Peru YES): RESOLVED_WRONG ✗
    STR003-003 (Warsh NO): RESOLVED_WRONG ✗
    STR003-009 (Graham SC NO): RESOLVED_WRONG ✗
    STR003-008 (EU Security NO): RESOLVING TODAY ← score Jun 30/Jul 1
  Not scorable: STR003-004 (Putin — fails geo_elo), STR003-007 (Iran — retrospective)
  Current scored accuracy: 1/4 (25%); will be 1/5 or 2/5 after Jun 30
  NOTE: Gate 3 at serious risk. 62.5% LEGENDARY dormancy limits new signal generation.
        Need 6+ correct outcomes from ~5+ remaining opportunities to reach 60% on n=10.
        Structural concern: 3 of 4 scored signals WRONG — DOMAIN analysis needed.

Gate 4 — RQ1.1 + RQ3.2:
  RQ1.1: BLOCKED — RQ-GEO-ELO-001 NOT STARTED (5 weeks elapsed, deadline TOMORROW Jul 1)
    ⚠⚠ CRITICAL: If not started today, July 1 deadline is missed. Spawn quant-research-agent.
  RQ3.2: INCONCLUSIVE (methodology reframe needed — extend RQ2.2 to outcome)

Signal accuracy (June 29):
  STR-003 (geo_elo_active criteria, scored): 1/4 (25%) — insufficient for stop condition
  STR-003 legendary clean: 16 traders (62.5% dormant — signal pipeline constrained)
  NEAR_LEGENDARY clean: 41 (nearly doubled since Jun 15 — pipeline growing)
  STR-004: 0/1 founding case ambiguous. 9 more signals needed.
  Putin/Iran/EU Security: ALL resolving June 30. Record outcomes in strategy-registry.md.
```

---

## Research Phase Tracker

Tracks progress through the formal research questions.
Updated by performance-analyst-agent as phases complete.

```
Phase         RQ              Status          Started     Completed
──────────────────────────────────────────────────────────────────
Phase 1       RQ1.1           BLOCKED         2026-04-26  — (rerun July 1; requires RQ-GEO-ELO-001 first)
              RQ3.2           INCONCLUSIVE    2026-04-26  — (reframe needed)
Phase 2       RQ2.1           Not started     —           —
              RQ1.2           Not started     —           —
              RQ4.1           Not started     —           —
Phase 3       RQ3.1           Not started     —           —
              RQ2.3           Not started     —           —
              RQ5.2           Not started     —           —
Phase 4       RQ4.2           Not started     —           —
              RQ6.2           Not started     —           —
              RQ1.3           Not started     —           —
Phase 5+      All RQ          Not started     —           —
──────────────────────────────────────────────────────────────────
Supporting    RQ0.1           PASSED          2026-03-29  2026-03-29
              RQ0.2           PASSED          2026-03-29  2026-03-29 (rerun with updated geo_elo after RQ-GEO-ELO-001)
              RQ2.2           INCONCLUSIVE    2026-04-26  — (extend to 14/30d window)
              RQ-EXEC-001     PRELIMINARY     2026-06-07  — (execution not supported for LEGENDARY)
              RQ-CONTESTED-001 PASS           2026-06-05  2026-06-05 (QUALIFIED 66.3%, n=101)
              RQ-GEO-ELO-001  NOT STARTED ⚠  2026-05-25  — (APPROVED May 25, 3rd Sunday gap, July 1 deadline)
──────────────────────────────────────────────────────────────────
```

Last updated by performance-analyst-agent: 2026-06-29

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source

⚠⚠ CRITICAL DEPENDENCY NOTE: RQ-GEO-ELO-001 Phase 1 is the prerequisite for RQ1.1 rerun.
  RQ-GEO-ELO-001 was Oscar-approved May 25 and has NOT been executed (5 weeks elapsed).
  July 1 RQ1.1 deadline is TOMORROW. Spawn quant-research-agent immediately.
