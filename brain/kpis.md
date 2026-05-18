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

Last updated: 2026-05-18
Updated by: performance-analyst-agent (run 3)

### Week of 2026-05-18

#### Prediction Accuracy
```
ELO QUALIFIED consensus accuracy (latest clean-pool):  63.16% (n=57 — May 7 authoritative)
ELO QUALIFIED consensus accuracy (7d window, May 11):  92% (n=12 — feedback-loop)
Brier score (elite positions, 7d):    0.3128 (unchanged — no new feedback-loop run this week)
vs naive baseline (50%):             -0.0628 (artefact: STR-004 founding case, 2 markets)
Active traders (7d, trades table):     963    (RECOVERED from 22 on May 13 — monitoring gap resolved)
Trades executed (7d):               42,509   (normal trading volume confirmed)
Note: No new feedback-loop-agent accuracy run this week. Most recent Brier is from May 13.
      QUALIFIED accuracy on clean pool (63.16%) is the primary metric.
```

#### ELO System Health
```
Total traders (DB):                110,548  (vs 96,051 May 13; +15.1% — possible backfill)
Legendary traders (>2175, research_excl=0):  235  (⚠ pool inflation — see below)
Elite traders (1800-2175, research_excl=0):  339  (⚠ pool inflation)
Research pool (research_excluded=0):       7,852  (⚠ INFLATED — maintenance script bug)
Research pool (EXPLICIT CLEAN CRITERIA):     104  (⚠ CRITICAL DROP from 493 on May 13)
Max ELO observed:                         4,305.1 (⚠ JUMPED from 3,471 — new cluster suspected)
Traders with ELO > 3,500 (research_excl=0):   39  (⚠ potential new ARB_BOT cluster)
Trades executed (7d):               42,509   (RECOVERED — May 13 dip was monitoring gap)
ELO last updated:                2026-05-18 (daily maintenance running)
⚠ CRITICAL: update_research_exclusions.py is setting research_excluded=0 for 7,748 traders
  who fail resolved_trades_count>=20. Explicit criteria must be used for ALL research queries.
```

#### Signal Quality
```
STR-003 signals active (MEDIUM):       4  (all 5 days unrescanned — spawn signal-agent)
STR-003 resolved (cumulative):         1/1 (100%, Ramaswamy NO — CORRECT, n=1 insufficient)
STR-004 resolved (cumulative):         0/1 (0%, founding case FAIL — stop criterion not met)
Upgrade conditions met (MEDIUM→HIGH):  0
Signal-agent last run:           2026-05-13 (5 days ago — STALLED)
Near-term resolution:            Putin invasion by June 2026 (~13 days remaining)
feedback.json:                   RESTORED from git d529c0a (was corrupted by research-scout)
```

#### Strategy Pipeline
```
Strategies submitted (30d):            0  (none new)
Strategies validated (30d):            0  (no backtest-agent run)
Pass rate:                            N/A
RQ1.1 status:             INCONCLUSIVE (n=16, rerun June 1 — pre-register OVERDUE May 20)
RQ3.2 status:             INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome)
RQ2.2 status:             MEDIUM confidence — YES 61.1% (n=18), NO 77.8% (n=9)
RQ0.1:                    PASSED 2026-05-13. Next due 2026-06-13 — bring forward (high-ELO cluster)
RQ0.2:                    PASSED 2026-05-13. Next due 2026-06-13 — bring forward (high-ELO cluster)

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
Estimated API spend (week, May 13-18):  ~$1.50  (training-librarian + integration-test + this run)
Agent tasks completed:              3   (training-librarian, integration-test, performance-analyst)
Agent tasks failed:                  0
Auto-respawns by immune system:      0
CI failures:                         1  (test_feedback_file_structure — resolved by restoration)
Git commits (past week, May 11-18): ~25  (Ollama loop, tier corrections, template fixes)
Brain directory size:             ~1.1MB (growing)
Integration test pass rate:       86.7%  (39/45 May 17 — improved from 83.7%)
First-repo log directory:           495MB (growing — ELO recalc logs uncompressed, 2+ weeks)
Orphaned worktrees:                  16  (pending Oscar approval to remove)
feedback.json:            RESTORED from git d529c0a (research-scout path routing bug)
```

#### Week-on-Week Trends
```
ELO QUALIFIED accuracy (clean-pool):  63.16% stable (no new run) — HOLDING
ELO QUALIFIED accuracy (7d window):   92% (May 11, last measured) — HOLDING
Brier score trend:                    0.3128 (May 13, artefact) → no new data
Explicit clean pool:                  493 (May 13) → 104 (May 18)  ↓↓ CRITICAL
Research_excluded=0 pool:             604 (May 13) → 7,852 (May 18)  ↑ MISLEADING
Max ELO:                              3,471 (May 13) → 4,305 (May 18)  ↑ SUSPICIOUS
Active traders (7d):                  22 (May 13) → 963 (May 18)  ↑ (gap resolved)
Signal accuracy trend:                1/1 STR-003 ✓ | 0/1 STR-004 ✗ — too small
Phase 5 Gate 1:                       ✅ COMPLETE (6/4 runs)
Phase 5 Gate 2:                       1/3 HIGH findings (unchanged)
Phase 5 Gate 3:                       50%/4 markets (stalled — pre-res scan not running since May 10)
Phase 5 Gate 4:                       Inconclusive → rerun June 1 (pre-register by May 20)
```

### Previous Week (2026-05-13 — for reference)

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

Last updated: 2026-05-18 (performance-analyst-agent run 3)

```
Feedback-loop runs: 6/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday — feedback.json was corrupted; restored pre-run)
  Note:  feedback.json restored from git d529c0a before today's run

HIGH confidence findings: 1/3 valid
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED — contaminated pool (82% was artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57 (clean 493-trader pool)
  ⏳ Need 2 more with n≥20
  ⚠ BLOCKER: Explicit clean pool has collapsed from 493 → 104 (May 18).
    Root cause: update_research_exclusions.py setting research_excluded=0 too broadly.
    Must fix before next finding can be computed reliably.

Pre-resolution accuracy: 50% / 4 markets
  (unchanged — no new resolved pre-resolution signals since May 5)
  (pre-res scan stalled since May 10 — 8 days missed)
  Gate needs: 60% accuracy across 10+ resolved markets

RQ1.1 status:   INCONCLUSIVE (n=16, rerun scheduled June 1)
  ⚠ Pre-register methodology OVERDUE — deadline was 2026-05-20 (2 days away).
  Use elo_period1_cutoff for point-in-time ELO.
RQ3.2 status:   INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome prediction)

Signal accuracy:
  STR-003: 1/1 resolved correct (Ramaswamy NO ✅ 2026-05-02)
  STR-004: 0/1 resolved correct (Russia/Ukraine ceasefire ✗ 2026-05-08 — crowd correct)
  4 STR-003 signals pending resolution (unrescanned 5 days — spawn signal-agent TODAY)
  Near-term: Putin invades by June 2026 (ELO 3323, resolves ~June 30, ~13 days)
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
