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

Last updated: 2026-06-08
Updated by: performance-analyst-agent (run 6)

### Week of 2026-06-08

#### Prediction Accuracy
```
PRIMARY: geo_elo Pool C (Pool C, geo_accuracy_pool=1, corrected binary Brier formula):
  GEOPOLITICS ONLY (30d):
    Brier score (30d):                0.2400  (vs naive 0.25 — BEATS BASELINE ✅)
    Directional accuracy (30d):       71.30%  (n=108 geo markets)
  ELECTIONS (30d):
    Brier score (30d):                0.2982  (vs naive 0.25 — worse than naive ⚠)
    Directional accuracy (30d):       60.84%  (n=166 elections markets)
    Note: elections pulled down by correlated US state election pairs (NH, MI)
  COMBINED geo+elections (30d):
    Brier score (30d):                0.2753  (n=274 markets with Pool C traders)
    Directional accuracy (30d):       64.96%
  COMBINED geo+elections (7d):
    Brier score (7d):                 0.2558  (n=193 markets with Pool C traders)
    Directional accuracy (7d):        64.77%

  VALIDATED BASELINE (HIGH confidence, n=444):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  ⚠ METHODOLOGY NOTE: Prior week (Jun 1) showed 86.36%/n=22 using a different
    subset. This run uses ALL resolved geo/elections markets with Pool C positions.
    Geopolitics-only (71.3%) is the clean comparable to the system's target edge.
```

#### ELO System Health
```
Total traders (DB):                134,104  (vs 125,451 Jun 1; +6.9%)
True research pool (resolved≥20):    1,738  (vs 1,449 Jun 1 — +20%)
Research pool (research_excluded=0): 18,818  (vs 14,983 Jun 1 — +25.6%)
Pool C (geo_accuracy_pool=1):          504  (vs 177 May 25; note: method change +June maint)
geo_elo LEGENDARY (geo_elo ≥ 2175, clean): 25  ⚠ (vs 47 Jun 1 — BELOW ALERT THRESHOLD 30)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 13  (UNCHANGED — STR-003 capacity stable)
STR-003 qualifying traders (full criteria): 11  (geo_elo_active≥2175, dir≥0.7, pnl criteria)
comprehensive_elo >2175 (research pool):  10  (non-authoritative for signals — see SCL-003)
Elite (comp_elo 1800-2175, research pool): 29
Standard (comp_elo 1200-1800, research pool): 1,434
Active traders (7d):                   2,395  (vs 3,327 Jun 1 — ↓ -28%, 3rd week declining)
Trades executed (7d):                 63,351  (vs 74,068 Jun 1 — ↓ -14.5%)
ELO last updated:              2026-06-08 (daily maintenance + Sunday timer ran Jun 7)
FLAG: legendary_base=25 < alert threshold 30 — contract_violation signal filed
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria):
  Qualifying traders:                     13  (geo_elo_active≥2175, research_excluded=0)
  With full STR-003 criteria (dir≥0.7, pnl): 11
  STR003-005 (Keiko Fujimori YES, Peru):  PENDING (resolution date Jun 7 — not yet in DB)
  STR003-006 (López Aliaga YES, Peru):    PENDING (resolution date Jun 7 — not yet in DB)
  New-criteria historical accuracy:       0 resolved signals yet

STR-003 under old criteria (historical reference):
  STR003-001 (Ramaswamy): CORRECT ✅ | STR003-003 (Warsh): WRONG ✗
  Cumulative old-criteria: 1/2 (50%) — not under new geo_elo criteria, reference only

STR-004:               0/1 (founding case FAIL — Russia/Ukraine ceasefire)
feedback.json:         INTACT (restored — was corrupted May 24, fixed Jun 5 run)
feedback-loop Run 8:   COMPLETE (June 5, feedback-loop-agent — wrote 4 findings)
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 11 qualifying traders, 2 pending Peru signals
STR-004:   HYPOTHESIS — 0/1 founding case failed. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 7 insider_signals tracking, 0 resolved yet.
RQ1.1:     DELAYED to July 1 (pre-registered ✓, RQ0.2 screen required before rerun)
RQ3.2:     INCONCLUSIVE — methodology reframe needed
RQ-EXEC-001: Preliminary results committed June 7 — "execution not supported for LEGENDARY"
RQ-CONTESTED-001: PASS ✅ — QUALIFIED tier 66.3% on 2026 contested geo, n=101 (Jun 5)
```

#### System Resources
```
Estimated API spend (week, Jun 1-Jun 8): ~$1.00  (this run + feedback-loop run 8)
trading-swarm service:            ACTIVE (since 2026-05-22)
polymarket-monitoring:            ACTIVE (auto-restart enabled)
Git commits (past week, Jun 1-Jun 8): ~20  (RQ-EXEC-001, schema-change-log, template fixes,
                                             trader discovery, pre-resolution scan)
Brain directory size:             2.3MB (vs 2.0MB Jun 1 — +15%)
First-repo DB size:               7.9GB (vs ~6.3GB Jun 1 — ↑ +25% ⚠ monitor disk space)
Unresolved past-due geo markets:  137  (resolution sweep lag — Jun 9 maintenance will clear)
RQ0.1/RQ0.2 next due:             2026-06-13
```

#### Week-on-Week Trends
```
Brier (geopolitics, 30d):            NEW METHODOLOGY — 0.2400 ✅ (beats naive 0.25)
Brier (combined geo+elec, 30d):      0.2753 (worse than naive — elections pairs effect)
Pool C validated baseline (full 2026): 70.7% accuracy, n=444 (HIGH confidence ✅)
Legendary ACTIVE (geo_elo_active≥2175): 13 (Jun 1) → 13 (Jun 8) → STABLE ✅
Legendary BASE (geo_elo≥2175, clean):   47 (Jun 1) → 25 (Jun 8) → ⚠ BELOW ALERT
Research pool (resolved≥20):          1,449 (Jun 1) → 1,738 (Jun 8) ↑ +20%
Pool C (geo_accuracy_pool):             477 → 504 ↑ +5.7%
Active traders (7d):               3,327 → 2,395 ↓ -28% (3rd consecutive decline)
Trades (7d):                      74,068 → 63,351 ↓ -14.5%
Phase 5 Gate 1:                    ✅ COMPLETE (7+/4 runs)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5 — 3+/3 HIGH findings)
Phase 5 Gate 3:                    50%/4 markets (STALLED — 29+ days)
Phase 5 Gate 4:                    INCONCLUSIVE → July 1 (RQ1.1 delayed)
```

### Previous Week (2026-06-01 — for reference)

#### Prediction Accuracy
```
geo_elo accuracy (30d):              86.36%  (n=22 — small sample, Pool C subset)
geo_elo Brier (30d):                 0.1222  (vs naive 0.25 — high due to small sample)
Directional accuracy (7d, elite):    74.39%  (n=82 binary, different methodology)
Brier score (7d, elite):             0.2354
```

#### ELO System Health
```
Total traders (DB):                125,451
Research pool (EXPLICIT CLEAN):      1,449  (research_excluded=0, resolved≥20, bot IS NULL)
geo_elo LEGENDARY (geo_elo ≥ 2175):     47  (clean pool)
geo_elo_active LEGENDARY:               13
Pool C (geo_accuracy_pool=1):          177  (note: may have been under-counted pre-June maintenance)
Active traders (7d):                 3,327
Trades executed (7d):               74,068
```

---

## Phase 5 Gate Tracker

Last updated: 2026-06-08 (performance-analyst-agent run 6)

```
Gate 1 — Feedback-loop runs: 8+/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday)
  Run 8: 2026-06-05 ✅ COMPLETE (wrote 4 new findings; Phase 5 Gate 2 confirmed)

Gate 2 — HIGH confidence findings: 3+/3 ✅ GATE MET (confirmed 2026-06-05)
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED (contaminated pool, 82% artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57
  ✅ 2026-06-01-GEO-ELO-ACCURACY-001: Pool C 86.36%, n=22 geo 30-day markets
  ✅ 2026-06-03-ELO-VS-MARKET-001: ELO vs market price contested markets, n=746
  ✅ 2026-06-05-CONTESTED-ACCURACY-2026-001: RQ-CONTESTED-001 PASS — QUALIFIED 66.3%, n=101
  ✅ 2026-06-05-POOL-C-GEO-FULL-2026-001: Pool C full 2026 70.7%, LEGENDARY 79.6%, n=444

Gate 3 — Pre-resolution accuracy: 50% / 4 markets — STALLED (29+ days)
  Gate needs: 60% accuracy across 10+ resolved markets
  STR003-005 and STR003-006 (Peru, Jun 4 signals) PENDING — await Jun 9 resolution sweep
  Next checkpoint: 2026-06-15

Gate 4 — RQ1.1 + RQ3.2:
  RQ1.1: DELAYED to July 1, 2026
    Pre-registration FILED (rq1-1-rerun-pre-registration-june2026.md)
    ⚠ Run RQ0.2 screen (due June 13) BEFORE July 1 rerun
  RQ3.2: INCONCLUSIVE (methodology reframe needed — extend RQ2.2 to outcome)

Signal accuracy (June 8):
  STR-003 (geo_elo_active criteria): 2 active signals filed Jun 4 (Peru) — pending resolution
  STR-003 (old criteria): 1/2 (Ramaswamy ✅, Warsh ✗) — reference only, fails new criteria
  STR-004: 0/1 (Russia/Ukraine ✗ — founding case failed). 9 more signals needed.
  Putin invades by June 2026: resolves June 30. Included in 137 past-due unresolved.
```

---

## Research Phase Tracker

Tracks progress through the formal research questions.
Updated by performance-analyst-agent as phases complete.

```
Phase         RQ        Status          Started     Completed
──────────────────────────────────────────────────────────────
Phase 1       RQ1.1     INCONCLUSIVE    2026-04-26  — (rerun July 1, n=10<30, pre-registered ✓)
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
              RQ0.2     PASSED          2026-03-29  2026-03-29 (next run due 2026-06-13)
              RQ2.2     INCONCLUSIVE    2026-04-26  — (extend to 14/30d window)
              RQ-EXEC-001 PRELIMINARY  2026-06-07  — (execution hypothesis not supported for LEGENDARY)
              RQ-CONTESTED-001 PASS    2026-06-05  2026-06-05 (QUALIFIED 66.3%, n=101)
──────────────────────────────────────────────────────────────
```

Last updated by performance-analyst-agent: 2026-06-08

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source
