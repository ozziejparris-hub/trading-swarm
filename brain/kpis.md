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

Last updated: 2026-05-25
Updated by: performance-analyst-agent (run 4)

### Week of 2026-05-25

#### Prediction Accuracy
```
Directional accuracy (7d window):    50.2%  (n=333 markets — all "Unknown" category, context below)
Directional accuracy (30d window):   58.2%  (n=1,071 markets — approaching 60% gate)
Elite tier accuracy (30d):           62.9%  (n=132 — ABOVE 60% Phase 5 gate ✓)
Legendary tier accuracy (30d):       53.5%  (n=99 — at baseline, consistent with LP pattern)
Standard tier accuracy (30d):        58.0%  (n=840 — below gate)
Brier score (7d):                    0.4133 (vs naive 0.25 — 7d batch context: all "Unknown" category)
Brier score (30d):                   0.3181 (vs naive 0.25 — worse than random, pool dilution effect)
ELO QUALIFIED authoritative (May 7): 63.16% (n=57 — historical clean pool, most comparable metric)
Active traders (7d):                  5,115  (+430% from 963 — real volume surge confirmed)
Trades executed (7d):               117,768  (+177% from 42,509)
Markets resolved (7d):               1,750   (significant increase)
Note: 7d accuracy (50.2%) driven by pool expansion (493→1,135 traders) and missing category data
      (99.95% of recent markets = "Unknown"). Elite tier at 30d is the cleanest edge signal.
```

#### ELO System Health
```
Total traders (DB):                119,090  (vs 110,548 May 18; +7.7%)
Legendary traders (>2175, CLEAN):        5  (explicit pool; 11,970 have research_excluded=0)
Elite traders (1800-2175, CLEAN):        9  (explicit pool)
Standard (1200-1800, CLEAN):           988  (explicit pool)
Research pool (research_excluded=0): 11,970  (⚠ still 10.5x the explicit pool)
Research pool (EXPLICIT CLEAN):      1,135  (✅ RECOVERED from 104 on May 18)
Max ELO (explicit clean pool):       2,469.1 (no suspicious >3,500 in clean pool today)
ELO >3,500 cluster:           CONFIRMED via May 24 session (~4,655 max) — new accounts from
                              Sunday leaderboard discovery. NOT in clean pool yet
                              (fail resolved_trades_count>=20). Screen via RQ0.2 before June 1.
ELO last updated:                2026-05-25 (daily maintenance running)
Note: research_excluded=0 alone now returns 11,970 (10.5x explicit clean pool of 1,135).
      ALWAYS add explicit criteria: AND resolved_trades_count>=20 AND bot_suspect=0
      AND wash_trade_suspect=0 AND bot_type IS NULL
```

#### Signal Quality
```
STR-003 signals active (MEDIUM):       4  (all 7 days unrescanned — 4th consecutive Sunday missed)
STR-003 resolved (cumulative):         1/1 (100%, Ramaswamy NO — CORRECT, n=1 insufficient)
STR-004 resolved (cumulative):         0/1 (0%, founding case FAIL — stop criterion not met)
Upgrade conditions met (MEDIUM→HIGH):  0
Signal-agent last run:           2026-05-18 (7 days ago — CRITICAL STALL, 4th Sunday)
Near-term resolution:            Putin invasion by June 2026 (~8 days remaining)
feedback.json:                   ⚠ Corrupted as of May 24 integration test; intact May 25 06:00
                                   3rd corruption incident — template fix needed
```

#### Strategy Pipeline
```
Strategies submitted (30d):            1  (LH-001 — CONDITIONAL_PASS)
Strategies validated (30d):            1  (LH-001 — confirmed twice May 21-22)
Pass rate:                          100%  (n=1)
LH-001 status:            CONDITIONAL_PASS — primary validation via insider_signals (7 records)
RQ1.1 status:             INCONCLUSIVE (n=16, rerun JUNE 1 — pre-registration FILED ✓)
RQ3.2 status:             INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome)
RQ2.2 status:             MEDIUM confidence — YES 61.1% (n=18), NO 77.8% (n=9)
RQ0.1:                    PASSED 2026-05-13. Next due 2026-06-13 — bring forward (ELO cluster)
RQ0.2:                    PASSED 2026-05-13. Next due 2026-06-13 — BRING FORWARD (screen >3,500
                          cluster BEFORE June 1 RQ1.1 rerun)

STR-003 — Single Legendary Directional Signal
  Status:   EXPERIMENTAL
  Basis:    RQ2.2 extended — YES 61.1% (n=18), NO 77.8% (n=9) at 95% threshold
  Sample:   n=1 resolved (insufficient). Need 19 more.
  Putin market:  ~8 days to June 2026 resolution — rescan URGENT

STR-004 — Capital-Weighted Legendary Aggregate Signal
  Status:   HYPOTHESIS — founding case FAILED
  Founding: Russia/Ukraine ceasefire Q2 2026 — RESOLVED NO 2026-05-08
            8 traders, $1.74M, 55.7% YES vs 7% crowd. Crowd correct.
  Accuracy: 0/1 (0%) — stop criterion at <50% on n=10. Need 9 more.

LH-001 — Lifecycle Heuristic Insider Detection
  Status:   CONDITIONAL_PASS
  Basis:    Pooled p=0.0160, r=0.208 (small-medium). N=2 events insufficient.
  Path:     Track 7 insider_signals records to resolution (need ≥60% on ≥5)
```

#### System Resources
```
Estimated API spend (week, May 18-25): ~$0.50  (this run only — few agents active)
Agent tasks completed:              1   (performance-analyst this run)
Agent tasks stuck/orphaned:         1   (backtest-lh001-v3 — 4 days respawning, ORPHAN)
Auto-respawns by immune system:     0
CI failures:                        6   (signal-agent stall, feedback.json, research-scout,
                                        quant-research, signal types — 86.7% pass rate)
Git commits (past week, May 18-25): ~15  (monitoring fixes, Telegram, spawn_agent.sh,
                                         database.py connection fix, backfill spam fix)
Brain directory size:             ~1.7MB (growing)
Integration test pass rate:       86.7%  (39/45 May 24 — flat, 4 systemic failures persist)
First-repo log directory:           604MB (growing — +109MB/week accelerating)
Monitoring freezes:                  2   (May 22, May 24 — Fix 1 applied, Fix 2 pending)
Duplicate trades flagged:        8,988   (newly identified, under investigation)
Sunday maintenance duration:      7.4h   (leaderboard discovery 6.3h — optimisation needed)
```

#### Week-on-Week Trends
```
Directional accuracy (7d window):    50.2% (May 25, n=333) — pool+category change context
Directional accuracy (30d window):   58.2% (May 25, n=1,071) — approaching 60% gate
Elite tier accuracy (30d):           62.9% (May 25, n=132) — ABOVE 60% gate ✓
ELO QUALIFIED authoritative:         63.16% (May 7, historical — most comparable metric)
Explicit clean pool:                  104 (May 18) → 1,135 (May 25)  ↑↑ RECOVERED
Research_excluded=0 pool:           7,852 (May 18) → 11,970 (May 25)  ↑ still inflated
Max ELO (clean pool):               4,305 (May 18) → 2,469.1 (May 25)  ↓ cluster excluded
Active traders (7d):                  963 (May 18) → 5,115 (May 25)   ↑↑ volume surge
Trades (7d):                       42,509 (May 18) → 117,768 (May 25) ↑↑ +177%
Signal accuracy trend:                1/1 STR-003 ✓ | 0/1 STR-004 ✗ — too small
Phase 5 Gate 1:                       ✅ COMPLETE (6/4 runs)
Phase 5 Gate 2:                       1/3 HIGH findings (pool clean — unblocked for first time)
Phase 5 Gate 3:                       50%/4 markets (stalled — pre-res scan stalled since May 10)
Phase 5 Gate 4:                       Inconclusive → rerun June 1 (pre-registration FILED ✓)
```

### Previous Week (2026-05-18 — for reference)

#### Prediction Accuracy
```
ELO QUALIFIED consensus accuracy (latest clean-pool):  63.16% (n=57 — May 7 authoritative)
ELO QUALIFIED consensus accuracy (7d window, May 11):  92% (n=12 — feedback-loop)
Brier score (elite positions, 7d):    0.3128 (unchanged — no new feedback-loop run this week)
Active traders (7d):                    963  (RECOVERED from 22 on May 13)
```

#### ELO System Health
```
Total traders (DB):                110,548
Research pool (EXPLICIT CLEAN):       104  (⚠ CRITICAL — now resolved)
Max ELO observed:                   4,305.1 (⚠ suspicious cluster — now excluded from clean pool)
```

---

## Phase 5 Gate Tracker

Last updated: 2026-05-25 (performance-analyst-agent run 4)

```
Feedback-loop runs: 6/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday — feedback.json restored pre-run)
  Note:  Run 8 due today (May 25) — feedback.json must be confirmed intact first.
         Pool is clean (1,135 traders) — unblocked for Gate 2 attempt.

HIGH confidence findings: 1/3 valid
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED — contaminated pool (82% was artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57 (clean 493-trader pool)
  ⏳ Need 2 more with n≥20
  ✅ BLOCKER RESOLVED: Pool recovered to 1,135 (was 104 on May 18).
     Spawn feedback-loop-agent this week — pool clean, Gate 2 attempt unblocked.

Pre-resolution accuracy: 50% / 4 markets
  (unchanged — no new resolved pre-resolution signals since May 5)
  (pre-res scan stalled since May 10 — 15 days missed as of May 25)
  Gate needs: 60% accuracy across 10+ resolved markets

RQ1.1 status:   INCONCLUSIVE (n=16, rerun scheduled June 1)
  ✅ Pre-registration FILED (files: rq1-1-preregistration-2026-06-01.md,
     rq1-1-rerun-pre-registration-june2026.md). Met May 20 deadline.
  Run June 1. Pool now 1,135 — should exceed n=30 minimum.
  ⚠ Screen ELO >3,500 cluster via RQ0.2 BEFORE June 1 run.
RQ3.2 status:   INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome prediction)

Signal accuracy:
  STR-003: 1/1 resolved correct (Ramaswamy NO ✅ 2026-05-02)
  STR-004: 0/1 resolved correct (Russia/Ukraine ceasefire ✗ 2026-05-08 — crowd correct)
  4 STR-003 signals pending resolution (unrescanned 7 days — spawn signal-agent TODAY)
  Near-term: Putin invades by June 2026 (ELO 3323, resolves ~June 30, ~8 days remaining)
```

---

## Research Phase Tracker

Tracks progress through the formal research questions.
Updated by performance-analyst-agent as phases complete.

```
Phase         RQ        Status          Started     Completed
──────────────────────────────────────────────────────────────
Phase 1       RQ1.1     INCONCLUSIVE    2026-04-26  — (rerun June 1, pre-registered ✓)
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

Last updated by performance-analyst-agent: 2026-05-25

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source
