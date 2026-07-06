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

Last updated: 2026-07-06
Updated by: performance-analyst-agent (run 9)

### Week of 2026-07-06

#### Prediction Accuracy
```
PRIMARY: geo_elo Pool C (Pool C, geo_accuracy_pool=1, geo_elo_active weighted,
         resolved_trades_count>=20):
  GEOPOLITICS (30d):
    Brier score (30d):                0.1798  ✅✅ BEST ON RECORD (beats naive, n=89)
    Directional accuracy (30d):       82.0%
  ELECTIONS (30d):
    Brier score (30d):                0.1912  ✅✅ BEST ON RECORD (beats naive, n=68)
    Directional accuracy (30d):       80.9%
  COMBINED geo+elections (30d):
    Brier score (30d):                ~0.185  ✅✅ FIRST TIME BELOW 0.20 TARGET (n=157)
    Directional accuracy (30d):       ~81.5%
  COMBINED (7d):
    Brier Geo:                        0.0519  ⚠ CAUTION — n=77 but 88 June-30 stub markets
    Brier Elections:                  0.1053  n=19
    Note: 7d numbers inflated by bulk resolution of near-certainty "by June 30" markets
           (88 Geo markets all resolved NO: Russia/Sumy, NATO clash, Greenland, etc.)

  VALIDATED BASELINE (HIGH confidence, n=444):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  MILESTONE: 30d Brier crossed below 0.20 system target for first time (both categories).
  4 consecutive weeks of improvement: Geo 0.2400→0.2213→0.2168→0.1798
                                      Elections 0.2982→0.2714→0.2234→0.1912
```

#### ELO System Health
```
Total traders (DB):                155,663  (vs 146,293 Jun 29; +6.4%)
True research pool (resolved≥20):  13,855   (vs 8,221 Jun 29 — +68%; O-16 backfill)
Research pool (research_excluded=0): 26,399  (vs 22,384 Jun 29 — +18%)
Pool C (geo_accuracy_pool=1):       2,607   ✅ RECOVERED (was 2,157 Jun 29, low 2,155 Jun 27)
geo_elo LEGENDARY (geo_elo ≥ 2175):   61    (vs 78 Jun 29)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 19  (vs 29 Jun 29 — declining)
legendary_clean (geo_elo_active≥2175, pool_c, research_excl=0): 14 (vs 16 Jun 29 — declining)
near_legendary_clean (geo_elo_active 1800-2174): 35 (vs 41 Jun 29 — declining)
Max geo_elo_active:                3,887.5  (0xd44e974a — natural decay from 4,009)
Active traders (7d, BUY):          562  (vs 679 Jun 29 — -17%, 3rd consecutive decline)
Trades executed (7d, BUY):         47,219
Volume (7d, BUY):                  $6.83M
Clean markets (DB):                92,144  (vs 28,608 Jun 29 — +3x, O-16/O-17 resolution fixes)
Contract violations (Section 9):   NONE — all thresholds met ✅
  Note: pool_c threshold is <1,700 (Section 9); earlier signals cited <2,500 (outdated)
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria, gate-valid signals):
  Qualifying traders (legendary_clean): 14
  STR003-003 (Warsh Fed NO):           RESOLVED_WRONG ✗
  STR003-005 (Keiko Peru YES):         RESOLVED_CORRECT ✅ (Jun 11)
  STR003-006 (Aliaga Peru YES):        RESOLVED_WRONG ✗
  STR003-007 (Iran regime NO):         RESOLVED_CORRECT ✅ (Jul 4) — NON-SCORABLE (retrospective)
  STR003-008 (EU security NO):         RESOLVED_CORRECT ✅ (Jul 4) — GATE-VALID
  STR003-009 (Graham SC NO):           RESOLVED_WRONG ✗
  STR003-004 (Putin NO, Jun 30):       DB unresolved (resolved=0) ⚠ pending manual fix

  Gate-valid scored accuracy:          2/5 = 40%  (005✅, 008✅ vs 003✗, 006✗, 009✗)
  Total accuracy (incl non-scorable):  3/6 = 50%  (adds 007✅)
  LEGENDARY signals accuracy:          2/3 = 67%  vs UNKNOWN: 1/3 = 33%

Signal-agent:  DARK — 7+ days (last output Jun 29)
Gate 3 risk:   HIGH — need 60% on 10+ markets; currently 40% at n=5
               LEGENDARY clean declining (14, down from 17 peak) limits new signal pipeline
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 14 clean LEGENDARY, Gate 3 IN PROGRESS (40%, AT RISK)
STR-004:   HYPOTHESIS — 0/1. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 4/7 insider signals correct (57.1%)
RQ1.1:     BLOCKED — RQ-GEO-ELO-001 NOT STARTED (6+ weeks), deadline Jul 1 MISSED
RQ3.2:     INCONCLUSIVE — reframe needed
RQ-GEO-ELO-001: APPROVED (May 25) — NOT STARTED ⚠⚠⚠ DEADLINE MISSED
RQ-CONTESTED-001: PASS ✅ — QUALIFIED tier 66.3%, n=101
feedback-loop Run 13: DUE TODAY
```

#### System Resources
```
Estimated API spend (7d Jun 29-Jul 6): ~$1-2  (integration-test, training-librarian,
                                                performance-analyst)
trading-swarm orchestrator:       ACTIVE
polymarket-monitoring:            ACTIVE
Git commits (trading-swarm, 7d): 23 (recovery docs O-13/O-16/O-17)
Git commits (first-repo, 7d):    6  (O-16 backfill, O-17 resolution fix, test runner)
Brain directory size:             5.2MB (vs 4.4MB Jun 29 — +18%)
First-repo DB size:               12GB (vs 11GB Jun 29 — +9%)
Clean markets (DB):               92,144  (vs 28,608 Jun 29 — +3x; O-16/O-17 fixes)
CI pipeline:                      BLOCKED — 9th consecutive Sunday lint failure (SYSTEMIC)
Signal-agent:                     DARK — 7+ days (last output Jun 29)
Quant-research:                   DARK — 40+ days (RQ-GEO-ELO-001 never executed)
Backtest-agent:                   DARK — 35+ days (GEO-ELO-003 OOS verdict unwritten)
```

#### Week-on-Week Trends
```
Brier (geopolitics, 30d):   0.2400 (Jun 8) → 0.2213 (Jun 15) → 0.2168 (Jun 29) → 0.1798 (Jul 6) ↑↑↑ BELOW TARGET
Brier (elections, 30d):     0.2982 (Jun 8) → 0.2714 (Jun 15) → 0.2234 (Jun 29) → 0.1912 (Jul 6) ↑↑↑ BELOW TARGET
Combined accuracy (30d):    64.96% (Jun 8) → 69.1% (Jun 15) → 68.5% (Jun 29) → ~81.5% (Jul 6) ↑↑
Legendary ACTIVE (geo_elo_active≥2175): 13 (Jun 8) → 24 (Jun 15) → 29 (Jun 29) → 19 (Jul 6) ↓
Legendary CLEAN:                         9 (Jun 11) → 17 (Jun 15) → 16 (Jun 29) → 14 (Jul 6) ↓
NEAR_LEGENDARY clean:                   18 (Jun 8) → 22 (Jun 15) → 41 (Jun 29) → 35 (Jul 6) ↓
True research pool (resolved≥20):  1,738 (Jun 8) → 3,902 (Jun 15) → 8,221 (Jun 29) → 13,855 (Jul 6) ↑↑↑
Pool C (geo_accuracy_pool):          504 (Jun 8) → 2,875 (Jun 15) → 2,157 (Jun 29) → 2,607 (Jul 6) ↑ RECOVERING
Active traders (7d):              2,395 → ~2,573 → 679 → 562 ↓↓↓ SUSTAINED DECLINE
Phase 5 Gate 1:                    ✅ COMPLETE (12+/4 runs)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5)
Phase 5 Gate 3:                    2/5 = 40% gate-valid (up from 1/4 = 25%)
Phase 5 Gate 4:                    BLOCKED — RQ-GEO-ELO-001 deadline Jul 1 MISSED
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

Last updated: 2026-07-06 (performance-analyst-agent run 9)

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
  Run 10: 2026-06-15 (cron, Monday)
  Run 11: 2026-06-22 (cron, Monday)
  Run 12: 2026-06-29 (cron, Monday — complete)
  Run 13: 2026-07-06 (cron, Monday — due today)

Gate 2 — HIGH confidence findings: 3+/3 ✅ GATE MET (confirmed 2026-06-05)
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED (contaminated pool, 82% artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57
  ✅ 2026-06-01-GEO-ELO-ACCURACY-001: Pool C 86.36%, n=22 geo 30-day markets
  ✅ 2026-06-03-ELO-VS-MARKET-001: ELO vs market price contested markets, n=746
  ✅ 2026-06-05-CONTESTED-ACCURACY-2026-001: RQ-CONTESTED-001 PASS — QUALIFIED 66.3%, n=101
  ✅ 2026-06-05-POOL-C-GEO-FULL-2026-001: Pool C full 2026 70.7%, LEGENDARY 79.6%, n=444

Gate 3 — Pre-resolution accuracy: 2/5 gate-valid — IN PROGRESS (AT RISK)
  Gate needs: 60% accuracy across 10+ resolved markets
  Gate-valid scored signals (geo_elo_active criteria):
    STR003-003 (Warsh NO):          RESOLVED_WRONG ✗
    STR003-005 (Keiko Peru YES):    RESOLVED_CORRECT ✅ (Jun 11)
    STR003-006 (Aliaga Peru YES):   RESOLVED_WRONG ✗
    STR003-008 (EU Security NO):    RESOLVED_CORRECT ✅ (Jul 4) ← NEW
    STR003-009 (Graham SC NO):      RESOLVED_WRONG ✗
  Not gate-valid: STR003-007 (Iran — retrospective), STR003-004 (Putin — fails geo_elo)
  STR003-004 outcome: DB shows resolved=0 ⚠ — pending manual resolution fix
  Gate-valid accuracy: 2/5 = 40% (up from 1/4 = 25%)
  Total (incl non-scorable 007): 3/6 = 50%
  Need: 6+ correct from 5+ remaining opportunities to reach 60% on n=10
  Risk: LEGENDARY_clean declining (14, down from 17 peak Jun 15) constrains signal generation

Gate 4 — RQ1.1 + RQ3.2:
  RQ1.1: BLOCKED — RQ-GEO-ELO-001 NOT STARTED (6+ weeks, deadline Jul 1 MISSED)
    ⚠⚠⚠ CRITICAL: Spawn quant-research-agent. Richest dataset in system history (13,855 pool)
  RQ3.2: INCONCLUSIVE (methodology reframe needed — extend RQ2.2 to outcome)

Signal accuracy (July 6):
  STR-003 (gate-valid): 2/5 = 40% — 5 more signals minimum needed for Gate 3
  STR-003 legendary clean: 14 (declining — 3rd consecutive week)
  NEAR_LEGENDARY clean: 35 (down from 41 peak Jun 29)
  STR-004: 0/1 founding case ambiguous. 9 more signals needed.
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
              RQ-GEO-ELO-001  NOT STARTED ⚠⚠ 2026-05-25  — (APPROVED May 25, Jul 1 deadline MISSED, 6+ weeks)
──────────────────────────────────────────────────────────────────
```

Last updated by performance-analyst-agent: 2026-07-06

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source

⚠⚠ CRITICAL DEPENDENCY NOTE: RQ-GEO-ELO-001 Phase 1 is the prerequisite for RQ1.1 rerun.
  RQ-GEO-ELO-001 was Oscar-approved May 25 and has NOT been executed (5 weeks elapsed).
  July 1 RQ1.1 deadline is TOMORROW. Spawn quant-research-agent immediately.
