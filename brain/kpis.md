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

Last updated: 2026-05-05
Updated by: performance-analyst-agent (first run)

### Week of 2026-05-05

#### Prediction Accuracy
```
ELO QUALIFIED consensus accuracy (7d): 82%  (n=67 markets — HIGH confidence)
ELO ELITE consensus accuracy (7d):    100%  (n=4 markets — LOW confidence)
ELO LEGENDARY resolved markets (7d):    —   (0 qualifying markets)
Brier score proxy (elite, 30d):       0.28  (n=5 markets — borderline acceptable)
vs naive baseline (50%):            +32pp   (QUALIFIED accuracy 82% vs 50% random)
By category:                           —    (category field = "Unknown" for most positions)
Note: Direct position-level Brier scores unreliable at n=2-5 scale.
      ELO consensus accuracy is the primary accuracy metric until n grows.
```

#### ELO System Health
```
Total traders (DB):                 92,228  (vs 53,140 March baseline; +73.5%)
Legendary traders (>2175, full):       432  (⚠ 28x above March baseline ~15)
Legendary traders (research pool):     341  (of 965 research_excluded=0 traders)
Elite traders (1800-2175, full):       904
Max ELO observed:                    3,471
Active traders (trades 7d):            279
Trades executed (7d):                1,048
ELO last updated:                 2026-05-05 (857 research pool traders updated)
```

#### Signal Quality
```
Signals generated (HIGH):              0
Signals generated (MEDIUM):            6  (5 STR-003 pending, 1 legacy STR-001)
Signals resolved with known outcome:   1  (Ramaswamy NO — CORRECT)
Signal accuracy (n=1):              100%  (INSUFFICIENT DATA — do not cite)
Upgrade conditions met (MEDIUM→HIGH):  0
```

#### Strategy Pipeline
```
Strategies submitted (30d):            0  (STR-003 pre-registered April 27)
Strategies validated (30d):            1  (STR-001 — FAILED)
Pass rate:                            0%  (1/1 failed)
Most common failure reason:   LP contamination (legendary traders hold both sides)
RQ1.1 status:             INCONCLUSIVE (n=16, rerun June 1)
RQ3.2 status:             INCONCLUSIVE (n=4, methodology reframe needed)
RQ2.2 status:             INCONCLUSIVE (YES 75% n=13, NO 0% — extend window)
```

#### System Resources
```
Estimated API spend (week):         ~$5.40  (6 Tier 3 runs, 4 Tier 2.5 runs)
Agent tasks completed:                 14+
Agent tasks failed:                      0
Auto-respawns by immune system:          0
CI failures:                             0
Git commits (past week):                23
Brain directory size:                 904KB
Orchestrator status:                HEALTHY
```

#### Week-on-Week Trends
```
Brier score trend:              — (first run, no prior week)
Signal accuracy trend:          — (first run)
Strategy pass rate trend:       — (first run)
Cost trend:                     — (first run)
ELO QUALIFIED accuracy:      82%  (baseline established)
Phase 5 feedback-loop gate:  3/4  (↑ on track)
```

---

## Phase 5 Gate Tracker

Last updated: 2026-05-05

```
Feedback-loop runs: 3/4 complete
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05  ← latest
  Run 4: scheduled 2026-05-11

HIGH confidence findings: 1/3 valid
  ✅ 2026-05-05-ELO-QUALIFIED-001: QUALIFIED 82% accuracy, n=67
  ⏳ Need 2 more with n≥20

Pre-resolution accuracy: 50% / 4 markets
  (unchanged — still accumulating, 10-market minimum not yet reached)

RQ1.1 status:   INCONCLUSIVE (n=16, rerun scheduled June 1)
RQ3.2 status:   INCONCLUSIVE (methodology reframe needed)

Signal accuracy: 1/1 resolved correct
  Ramaswamy NO — validated ✅
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

Last updated by performance-analyst-agent: 2026-05-05

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source
