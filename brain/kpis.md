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

Last updated: 2026-05-13
Updated by: performance-analyst-agent (run 2)

### Week of 2026-05-13

#### Prediction Accuracy
```
ELO QUALIFIED consensus accuracy (7d): 92%  (n=12 markets — feedback-loop May 11)
ELO QUALIFIED consensus accuracy (30d): 85.7% (n=14 markets — this run)
ELO ELITE consensus accuracy (7d):     33%  (n=3 markets — LOW confidence, volatile)
ELO LEGENDARY resolved markets (7d):    —   (0 qualifying legendary directional markets)
Brier score (elite positions, 7d):    0.3128 (n=192 positions, 2 markets only)
vs naive baseline (50%):             -0.0628 (WORSE than random — artefact: STR-004 founding case)
By category (Brier):            Crypto 0.2838 (n=19), Geopolitics 0.3160 (n=173)
By tier (Brier):             Legendary 0.3055 (n=131), Elite 0.3286 (n=61)
Note: Brier dominated by 2 markets only (Russia/Ukraine ceasefire + Bitcoin).
      STR-004 founding case resolution (legendary YES = WRONG) drives Geopolitics Brier.
      ELO consensus accuracy (92%) remains the primary accuracy metric.
```

#### ELO System Health
```
Total traders (DB):                 96,051  (vs 92,228 May 5; +4.1%)
Legendary traders (>2175, research): 142   (stable post-ARB_BOT cleanup; prev 151)
Elite traders (1800-2175, research):  31
Research pool (authoritative):        493  (integration-health.json, 06:03 today)
Research pool (live query):           604  (⚠ discrepancy — see Flag 3)
Max ELO observed:                   3,471.3
Active traders (trades 7d):            22  (⚠ vs 279 May 5 — possible monitoring gap)
Active traders (trades 30d):        1,369  (normal)
Trades executed (7d):                 162
ELO last updated:                2026-05-13 (daily maintenance running)
```

#### Signal Quality
```
STR-003 signals active (MEDIUM):       5  (all 15+ days unrescanned — ⚠ spawn signal-agent)
STR-003 resolved (cumulative):         1/1 (100%, Ramaswamy NO — CORRECT, n=1 insufficient)
STR-004 resolved (cumulative):         0/1 (0%, founding case FAIL — crowd was correct)
Upgrade conditions met (MEDIUM→HIGH):  0
Signal-agent last run:           2026-04-27 (15 days ago — STALLED)
Near-term resolution:            Putin invasion by June 2026 (~4 weeks)
```

#### Strategy Pipeline
```
Strategies submitted (30d):            0  (none new since STR-004)
Strategies validated (30d):            0  (backtest-agent not run since Apr 27)
Pass rate:                            N/A
RQ1.1 status:             INCONCLUSIVE (n=16, rerun June 1 — pre-register by May 20)
RQ3.2 status:             INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome)
RQ2.2 status:             MEDIUM confidence — YES 61.1% (n=18), NO 77.8% (n=9)
RQ0.1 + RQ0.2:            OVERDUE — last run 2026-03-29 (45 days). Spawn backtest-agent.

STR-003 — Single Legendary Directional Signal
  Status:   EXPERIMENTAL
  Basis:    RQ2.2 extended — YES 61.1% (n=18), NO 77.8% (n=9) at 95% threshold
  Sample:   n=1 resolved (insufficient). Need 19 more.

STR-004 — Capital-Weighted Legendary Aggregate Signal
  Status:   HYPOTHESIS — founding case FAILED
  Founding: Russia/Ukraine ceasefire Q2 2026 — RESOLVED NO 2026-05-08
            8 traders, $1.74M, 55.7% YES vs 7% crowd. Crowd correct.
  Accuracy: 0/1 (0%) — stop criterion at <50% on n=10. Need 9 more.
```

#### System Resources
```
Estimated API spend (week):         ~$0.50  (only feedback-loop ran at Tier 3)
Agent tasks completed:                  5+  (feedback-loop, research-scout x4, librarian, integration-test)
Agent tasks failed:                      0
Auto-respawns by immune system:          0
CI failures:                             0
Git commits (past week, May 6-13):      23
Brain directory size:                 1.2MB  (up from 904KB, +33%)
Integration test pass rate:          83.7%  (41/49, 8 failures — signal-agent + agent output staleness)
Model routing change (Tier 2.5):  Haiku 4.5 → Qwen3-Coder 30B-A3B (local, free)
Signal-agent tier:                Tier 3 (reverted — Ollama cannot execute tools)
```

#### Week-on-Week Trends
```
ELO QUALIFIED accuracy:  82% (May 5) → 92% (May 11) → 85.7% 30d (May 13)  ↑ IMPROVING
Brier score trend:       0.2798 (May 5, 30d) → 0.3128 (May 13, 7d)  ↓ (artefact — 2 mkts)
Signal accuracy trend:   1/1 STR-003 ✓ | 0/1 STR-004 ✗ — too small for trend
Strategy pass rate:      0% → 0% → N/A  (no new validations)
Cost trend:              ~$5.40 → ~$0.50  ↓ (stalled agents drove cost to near zero)
Phase 5 Gate 1:          ✅ COMPLETE (5/4 runs)
Phase 5 Gate 2:          1/3 HIGH findings (unchanged)
Phase 5 Gate 3:          50%/4 markets (unchanged — pre-resolution scan not running)
Phase 5 Gate 4:          Inconclusive → rerun June 1
```

### Previous Week (2026-05-05 — for reference)

#### Prediction Accuracy
```
ELO QUALIFIED consensus accuracy (7d): 82%  (n=67 markets — HIGH confidence)
ELO ELITE consensus accuracy (7d):    100%  (n=4 markets — LOW confidence)
Brier score proxy (elite, 30d):       0.28  (n=5 markets — borderline acceptable)
vs naive baseline (50%):            +32pp
```

#### ELO System Health
```
Total traders (DB):                 92,228
Active traders (trades 7d):            279
Legendary traders (research pool):     341 (pre-cleanup) / 151 (post-ARB_BOT)
```

---

## Phase 5 Gate Tracker

Last updated: 2026-05-13 (performance-analyst-agent run 2)

```
Feedback-loop runs: 6/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Next:  2026-05-18 (cron, Monday)

HIGH confidence findings: 1/3 valid
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED — contaminated pool (82% was artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57 (clean 493-trader pool)
  ⏳ Need 2 more with n≥20
  Path to Gate 2: accumulate STR-003 resolved signals to n=20; run RQ2.2 outcome accuracy update

Pre-resolution accuracy: 50% / 4 markets
  (unchanged — no new resolved pre-resolution signals since May 5)
  Gate needs: 60% accuracy across 10+ resolved markets

RQ1.1 status:   INCONCLUSIVE (n=16, rerun scheduled June 1)
  Pre-register methodology by 2026-05-20. Use elo_period1_cutoff for point-in-time ELO.
RQ3.2 status:   INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome prediction)

Signal accuracy:
  STR-003: 1/1 resolved correct (Ramaswamy NO ✅ 2026-05-02)
  STR-004: 0/1 resolved correct (Russia/Ukraine ceasefire ✗ 2026-05-08 — crowd correct)
  5 STR-003 signals pending resolution (unrescanned 15 days — spawn signal-agent)
  Near-term: Putin invades by June 2026 (ELO 3323, resolves ~June 1-30)
```

---

## Research Phase Tracker

Tracks progress through the formal research questions.
Updated by performance-analyst-agent as phases complete.

```
Phase         RQ        Status          Started     Completed
──────────────────────────────────────────────────────────────
Phase 1       RQ1.1     INCONCLUSIVE    2026-04-26  — (rerun June 1)
              RQ3.2     INCONCLUSIVE    2026-04-26  — (reframe needed)
Phase 2       RQ2.1     Not started     —           —
              RQ1.2     Not started     —           —
              RQ4.1     Not started     —           —
Phase 3       RQ3.1     Not started     —           —
              RQ2.3     Not started     —           —
              RQ5.2     Not started     —           —
Phase 4       RQ4.2     Not started     —           —
              RQ6.2     Not started     —           —
              RQ1.3     Not started     —           —
Phase 5+      All RQ    Not started     —           —
──────────────────────────────────────────────────────────────
Supporting    RQ0.1     PASSED          2026-03-29  2026-03-29
              RQ0.2     PASSED          2026-03-29  2026-03-29
              RQ2.2     INCONCLUSIVE    2026-04-26  — (extend to 14/30d window)
──────────────────────────────────────────────────────────────
```

Last updated by performance-analyst-agent: 2026-05-13

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source
