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

Last updated: 2026-06-15
Updated by: performance-analyst-agent (run 7)

### Week of 2026-06-15

#### Prediction Accuracy
```
PRIMARY: geo_elo Pool C (Pool C, geo_accuracy_pool=1, geo_elo_active weighted,
         resolved_trades_count>=20):
  GEOPOLITICS ONLY (30d):
    Brier score (30d):                0.2213  (vs naive ~0.25 — BEATS BASELINE ✅ best on record)
    Directional accuracy (30d):       75.9%   (n=79 geo markets, 60/79 correct)
  ELECTIONS (30d):
    Brier score (30d):                0.2714  (vs naive ~0.25 — worse than naive ⚠ but improving)
    Directional accuracy (30d):       66.1%   (n=186 elections markets, 123/186 correct)
  COMBINED geo+elections (30d):
    Brier score (30d):                ~0.256  (n=265 markets with Pool C traders)
    Directional accuracy (30d):       69.1%   (183/265 correct)
  COMBINED (7d):
    n=15 markets only (12 elections, 3 geo) — insufficient for trend analysis

  VALIDATED BASELINE (HIGH confidence, n=444):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  TREND: Both categories improving — Geo 71.3%→75.9%, Elections 60.8%→66.1% week-on-week.
  Geopolitics Brier is best on record (0.2213). Elections still above naive but trajectory positive.
```

#### ELO System Health
```
Total traders (DB):                141,877  (vs 134,104 Jun 8; +5.8%)
True research pool (resolved≥20):    3,902  (vs 1,738 Jun 8 — large jump; manual_watchlist fix + leaderboard discovery)
Research pool (research_excluded=0): 22,224  (vs 18,818 Jun 8 — +18.1%)
Pool C (geo_accuracy_pool=1):        2,875  (vs 504 Jun 8 — reflects June 10 sync_trade_categories fix)
geo_elo LEGENDARY (geo_elo ≥ 2175): 48  ✅ RECOVERED (vs 25 Jun 8 — contract_violation CLEARED)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 24  ✅ (vs 13 Jun 8 — +85% after Sunday ELO recalc)
legendary_clean (geo_elo_active≥2175, pool_c, research_excl=0): 17
near_legendary_clean (geo_elo_active 1800-2174): 22
Elite (comp_elo > 1800, research pool): 151
Standard (comp_elo 1200-1800, research pool): 2,225
Active traders (7d):               ~2,573  (vs 2,395 Jun 8 — slight increase)
Trades executed (7d):              ~80,541  (vs 63,351 Jun 8 — note: DB backfill inflates prev comparison)
Max geo_elo_active:                7,254   (0xecaa8806 — key STR-003 trader)
ELO last updated:                  2026-06-15 (daily maintenance + Sunday timer Jun 14)
Contract violations:               NONE  (legendary_base=48, violation from Jun 8 cleared)
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria):
  Qualifying traders (active, geo_elo_active≥2175): 24  (vs 13 Jun 8 — +85% pool expansion)
  STR003-005 (Keiko Fujimori YES, Peru):   RESOLVED_CORRECT ✅ (scored Jun 11)
  STR003-006 (López Aliaga YES, Peru):     RESOLVED_WRONG ✗ (resolved Jun 7)
  STR003-007 (Iran regime NO, June 30):    ACTIVE (non-scorable — retrospective)
  STR003-008 (EU security NO, June 30):    ACTIVE (non-scorable — retrospective)
  STR003-004 (Putin NO, June 30):          ACTIVE (fails geo_elo threshold — tracked for STR-004)
  Scored accuracy (new geo_elo criteria):  1/4 (25%) — insufficient sample (need n=10)
  Note: Signals STR003-007/008 non-scorable per Fable roadmap §5.1.3 (retrospective discovery)

STR-004:               0/1 (founding case ambiguous — market identity dispute)
feedback-loop Run 10:  COMPLETE (June 5 — wrote 4 findings, confirmed Gate 2)
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 24 qualifying traders (+85% from Jun 8), rescan needed
STR-004:   HYPOTHESIS — 0/1 founding case ambiguous. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 4/7 insider signals correct (57.1% < 60% threshold)
RQ1.1:     DELAYED to July 1 (requires RQ-GEO-ELO-001 Phase 1 first)
RQ3.2:     INCONCLUSIVE — reframe needed
RQ-GEO-ELO-001: APPROVED (May 25) — NOT STARTED (3rd consecutive Sunday gap) ⚠
RQ-EXEC-001: PRELIMINARY — "execution not supported for LEGENDARY"
RQ-CONTESTED-001: PASS ✅ — QUALIFIED tier 66.3% on 2026 contested geo, n=101
```

#### System Resources
```
Estimated API spend (week, Jun 8-Jun 15): ~$2.00  (integration-test, performance-analyst,
                                                      code-hygiene, research-scout)
trading-swarm service:            ACTIVE
polymarket-monitoring:            ACTIVE (auto-restart enabled)
Git commits (past week, Jun 8-15): ~12  (integration-test report, session summaries,
                                          API auth audit, signal-agent template fix,
                                          contract v2.9, code-hygiene report)
Brain directory size:             3.3MB (vs 2.42MB Jun 8 — +36%)
First-repo DB size:               8.9GB (vs 7.9GB Jun 8 — ↑ +12.7% ⚠ monitor disk)
Clean markets (DB):               24,494  (+6,453 since last week — fastest growth on record)
CI pipeline:                      BLOCKED — 7th consecutive Sunday lint failure (9 one-line fixes needed)
Signal-agent:                     DARK — 175h+ (last output Jun 8 — signal rescan OVERDUE)
```

#### Week-on-Week Trends
```
Brier (geopolitics, 30d):            0.2400 (Jun 8) → 0.2213 (Jun 15) ↑ BEST ON RECORD
Brier (elections, 30d):              0.2982 (Jun 8) → 0.2714 (Jun 15) ↑ IMPROVING
Combined accuracy (30d):             64.96% (Jun 8) → 69.1% (Jun 15) ↑
Legendary ACTIVE (geo_elo_active≥2175): 13 (Jun 8) → 24 (Jun 15) ↑ +85% RECOVERED
Legendary BASE (geo_elo≥2175):          25 (Jun 8) → 48 (Jun 15) ↑ CONTRACT VIOLATION CLEARED
Legendary CLEAN:                         9 (Jun 11) → 17 (Jun 15) ↑
True research pool (resolved≥20):   1,738 (Jun 8) → 3,902 (Jun 15) ↑ (+124%)
Pool C (geo_accuracy_pool):           504 (Jun 8) → 2,875 (Jun 15) ↑ (prior was under-counted)
Active traders (7d):               2,395 → ~2,573 ↑ slight
Phase 5 Gate 1:                    ✅ COMPLETE (10+/4 runs)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5 — 3+/3 HIGH findings)
Phase 5 Gate 3:                    1/4 correct STR-003 (STALLED — needs signal rescan + June 30 scoring)
Phase 5 Gate 4:                    BLOCKED on RQ-GEO-ELO-001 → RQ1.1 (July 1)
```

### Previous Week (2026-06-08 — for reference)

#### Prediction Accuracy
```
Geopolitics Brier (30d):             0.2400  (beats naive ✅, n=108)
Directional accuracy (geo, 30d):     71.3%
Elections Brier (30d):               0.2982  (worse than naive ⚠, n=166)
Directional accuracy (elections):    60.84%
Combined (30d):                      64.96%
```

#### ELO System Health
```
Total traders (DB):                134,104
Research pool (EXPLICIT CLEAN):      1,738  (research_excluded=0, resolved≥20, bot IS NULL)
geo_elo LEGENDARY (geo_elo ≥ 2175):     25  ⚠ (below alert threshold 30 — contract violation)
geo_elo_active LEGENDARY:               13
Pool C (geo_accuracy_pool=1):          504
Active traders (7d):                 2,395
Trades executed (7d):               63,351
```

---

## Phase 5 Gate Tracker

Last updated: 2026-06-15 (performance-analyst-agent run 7)

```
Gate 1 — Feedback-loop runs: 10+/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday)
  Run 8: 2026-06-05 ✅ COMPLETE (wrote 4 new findings; Phase 5 Gate 2 confirmed)
  Runs 9-10: prior runs, gate confirmed

Gate 2 — HIGH confidence findings: 3+/3 ✅ GATE MET (confirmed 2026-06-05)
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED (contaminated pool, 82% artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57
  ✅ 2026-06-01-GEO-ELO-ACCURACY-001: Pool C 86.36%, n=22 geo 30-day markets
  ✅ 2026-06-03-ELO-VS-MARKET-001: ELO vs market price contested markets, n=746
  ✅ 2026-06-05-CONTESTED-ACCURACY-2026-001: RQ-CONTESTED-001 PASS — QUALIFIED 66.3%, n=101
  ✅ 2026-06-05-POOL-C-GEO-FULL-2026-001: Pool C full 2026 70.7%, LEGENDARY 79.6%, n=444

Gate 3 — Pre-resolution accuracy: 1/4 correct STR-003 signals — IN PROGRESS (SLOW)
  Gate needs: 60% accuracy across 10+ resolved markets
  Scored signals (geo_elo_active criteria):
    STR003-005 (Keiko Peru YES): RESOLVED_CORRECT ✅ (Jun 11)
    STR003-006 (Aliaga Peru YES): RESOLVED_WRONG ✗
    STR003-003 (Warsh NO): RESOLVED_WRONG ✗
    STR003-009 (Graham SC NO): RESOLVED_WRONG ✗
  Current accuracy: 1/4 (25%) — insufficient sample for gate assessment
  June 30 cluster (3 signals resolving): STR003-004 (Putin), STR003-007 (Iran†), STR003-008 (EU†)
  †Non-scorable (retrospective discovery)
  Next checkpoint: 2026-07-01 (after June 30 scoring)
  NOTE: Gate 3 at risk. Need 6+ correct from remaining scorable signals to reach 60%.

Gate 4 — RQ1.1 + RQ3.2:
  RQ1.1: BLOCKED until RQ-GEO-ELO-001 Phase 1 completes. Scheduled July 1.
    ⚠ RQ-GEO-ELO-001 Phase 1 NOT STARTED — 3rd consecutive Sunday gap. Oscar-approved May 25.
    Risk: If RQ-GEO-ELO-001 not started this week, July 1 deadline at risk.
  RQ3.2: INCONCLUSIVE (methodology reframe needed — extend RQ2.2 to outcome)

Signal accuracy (June 15):
  STR-003 (geo_elo_active criteria, scored): 1/4 (25%) — insufficient for stop condition
  STR-003 legendary pool: 24 active traders (was 13 Jun 8 — +85% after Sunday ELO recalc)
  STR-004: 0/1 founding case ambiguous (market identity dispute). 9 more signals needed.
  Putin invades by June 2026: resolves June 30 (15 days). Record outcome in strategy-registry.md.
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

Last updated by performance-analyst-agent: 2026-06-15

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source

⚠ DEPENDENCY NOTE: RQ-GEO-ELO-001 Phase 1 is the prerequisite for RQ1.1 rerun.
  RQ-GEO-ELO-001 was Oscar-approved May 25 and has NOT been executed.
  July 1 RQ1.1 deadline is at risk if Phase 1 not completed by June 22.
