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

Last updated: 2026-06-01
Updated by: performance-analyst-agent (run 5)

### Week of 2026-06-01

#### Prediction Accuracy
```
PRIMARY: geo_elo Pool C (30d geo/elections markets):
  geo_elo accuracy (30d):              86.36%  (n=22 — Pool C, geo_accuracy_pool=1)
  geo_elo Brier (30d):                 0.1222  (vs naive 0.25 — EXCELLENT, below 0.20 target ✅)
  geo markets resolved (7d):               0   (thin window — 0 geo resolutions this week)

SECONDARY: comprehensive_elo Elite tier (7d binary all markets):
  Directional accuracy (7d):           74.39%  (n=82 binary markets, elite ELO-weighted consensus)
  Brier score (7d):                    0.2354  (vs naive 0.25 — near random; calibration not done)
  Legendary tier accuracy (30d):       35.92%  (n=119 pairs — ⚠ WORSE THAN RANDOM, FLAG-001)
  Note: comprehensive_elo Legendary tier contaminated — artefact accounts entering clean pool.
        geo_elo (86.36%) is the authoritative accuracy metric for geopolitics.
```

#### ELO System Health
```
Total traders (DB):                125,451  (vs 119,090 May 25; +5.3%)
Legendary (>2175, EXPLICIT CLEAN):      11  (vs 5 May 25 — ⚠ cluster partially entered pool)
Elite (1800-2175, EXPLICIT CLEAN):      81  (vs 9 May 25 — large jump, monitoring needed)
Standard (1200-1800, EXPLICIT CLEAN): 1,250  (vs 988 May 25)
Research pool (EXPLICIT CLEAN):       1,449  (vs 1,135 May 25 — +27.7%)
Research pool (research_excluded=0): 14,983  (vs 11,970 May 25 — +25.2%)
Pool C (geo_accuracy_pool=1):           177  (authoritative geo_elo pool)
geo_elo LEGENDARY (geo_elo > 2175):      47  (in Pool B; 26 in Pool C)
STR-003 qualifying traders:              12  (geo_elo≥2175, directionality≥0.7, pnl>500)
Max ELO (explicit clean pool):        3,325  (⚠ 0x2aacd459 — 20 resolved trades — FLAG-001)
Max ELO cap formula:          1500 + (resolved_trades_count × 150) — applied 2026-05-31
Max ELO in DB (all traders):          3,919  (ELO cap applied 2026-05-31, down from 5,115)
Active traders (7d):                  3,327  (vs 5,115 May 25 — ↓ -35%, investigate)
Trades executed (7d):                74,068  (vs 117,768 May 25 — ↓ -37%)
ELO last updated:             2026-06-01 (daily maintenance + Sunday timer active)
```

#### Signal Quality
```
STR-003 (geo_elo criteria — NEW as of May 31):
  Qualifying traders:                     12  (geo_elo≥2175, directionality≥0.7, pnl>500)
  Active signals (geo_elo):               0   (first run June 1 08:00 UTC — PENDING)
  Previous signals (comprehensive_elo):   INVALID under new criteria

STR-003 historical accuracy (old criteria — for reference):
  STR003-003 (Trump/Warsh):    WRONG (scored May 31 — Trump DID nominate Warsh Apr 4)
  STR003-001 (Ramaswamy):      CORRECT (scored May 2)
  Cumulative old-criteria:     1/2 (50%) — insufficient, n<10

STR-004 resolved:              0/1 (0%, founding case FAIL — Russia/Ukraine ceasefire)
feedback.json:                 ⚠ CORRUPTED (3rd incident) — shows only scout_cycles data
feedback-loop Run 8:           Status unclear — may have been blocked by corruption
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL → migrated to geo_elo criteria (May 31). 0 signals, first scan June 1.
STR-004:   HYPOTHESIS — 0/1 founding case failed. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 7 insider_signals tracking, 0 resolved yet.
RQ1.1:     DELAYED to July 1 (n=10 qualifying, minimum 30 — signal rq1_1_insufficient_n filed)
RQ3.2:     INCONCLUSIVE — methodology reframe needed (extend RQ2.2 to outcome)
RQ0.2:     ⚠ BRING FORWARD — screen ELO >3000 cluster BEFORE July 1 RQ1.1 rerun
GEO-ELO-003 OOS: CONDITIONAL (pending backtest-agent validation)

Maker/taker pipeline:  DEPLOYED (Polygon RPC, Etherscan, polygon_maker_taker.py)
                       Legendary scan running (background screen session)
STR-003 anti-arb filter: ACTIVE (entry_price BETWEEN 0.10 AND 0.80)
```

#### System Resources
```
Estimated API spend (week, May 25-Jun 1): ~$1.00  (this run + minimal other usage)
trading-swarm service:            ACTIVE (since 2026-05-22 03:00)
polymarket-monitoring:            ACTIVE (auto-restart enabled, since May 31)
Agent tasks completed:            1   (performance-analyst this run)
Auto-respawns by immune system:   0
Git commits (past week, May 25-Jun 1): ~30+  (maker/taker pipeline, ELO cap, signal
                                               templates, STR-003 anti-arb, market dates,
                                               geo_elo daily update, score_str003_signals.py)
Brain directory size:             2.0MB (stable)
First-repo log directory:         65MB (log archiving working — was 604MB)
First-repo DB size:               ~6.3GB (4x baseline of 1.6GB in ~10 weeks)
Integration test pass rate:       86.7%  (39/45 May 24 — flat, 4 systemic failures persist)
```

#### Week-on-Week Trends
```
geo_elo accuracy (30d geo markets):   NEW METRIC — 86.36% (n=22) ✅
Brier geo_elo (30d):                  NEW METRIC — 0.1222 ✅ (below 0.20 target)
Directional accuracy 7d (elite):      74.39% (Jun 1, n=82) — methodology comparable to 50.2% May 25
Legendary tier accuracy (comp_elo):   46.0% (May 25) → 35.92% (Jun 1) ↓↓ deteriorating
Explicit clean pool:               1,135 (May 25) → 1,449 (Jun 1) ↑ +28%
Pool C (geo):                        177 (Jun 1)
Max ELO (clean pool):              2,469.1 (May 25) → 3,325 (Jun 1) ↑ ⚠ new cluster entered
Active traders (7d):               5,115 (May 25) → 3,327 (Jun 1) ↓ -35%
Trades (7d):                     117,768 (May 25) → 74,068 (Jun 1) ↓ -37%
STR-003 signals:                       4 (old criteria) → 0 (geo_elo migration) ↓ reset
NEW HIGH finding:                  2026-06-01-GEO-ELO-ACCURACY-001 written
Phase 5 Gate 1:                    ✅ COMPLETE (7+/4 runs)
Phase 5 Gate 2:                    1/3 valid (+1 NEW finding today = potentially 2/3)
Phase 5 Gate 3:                    50%/4 markets (stalled — pre-res scan stalled)
Phase 5 Gate 4:                    INCONCLUSIVE → July 1 (RQ1.1 delayed)
```

### Previous Week (2026-05-25 — for reference)

#### Prediction Accuracy
```
Directional accuracy (7d window):   50.2%  (n=333 markets — all "Unknown" category)
Directional accuracy (30d window):  58.2%  (n=1,071 markets)
Elite tier accuracy (30d):          62.9%  (n=132 — ABOVE 60% gate)
Brier score (7d):                   0.4133 (all "Unknown" category context)
ELO QUALIFIED authoritative:        63.16% (n=57 — May 7, clean 493-trader pool)
Active traders (7d):                 5,115  (+430% from 963)
Trades executed (7d):              117,768
```

#### ELO System Health
```
Total traders (DB):                119,090
Research pool (EXPLICIT CLEAN):      1,135  (recovered from 104 on May 18)
Max ELO (explicit clean pool):     2,469.1  (no suspicious >3,500 yet)
ELO >3,500 cluster:                WARNED — Sunday leaderboard discovery, not yet in clean pool
```

---

## Phase 5 Gate Tracker

Last updated: 2026-06-01 (performance-analyst-agent run 5)

```
Feedback-loop runs: 7+/4 ✅ GATE MET
  Run 1: 2026-04-25
  Run 2: 2026-04-27
  Run 3: 2026-05-05
  Run 4: 2026-05-05 (clean pool revalidation)
  Run 5: 2026-05-07 (manual — clean pool confirmed, 493 genuine traders)
  Run 6: 2026-05-11 (cron, Monday)
  Run 7: 2026-05-18 (cron, Monday — feedback.json restored pre-run)
  Run 8: Status UNCLEAR — feedback.json CORRUPTED (3rd incident) as of May 24-25.
         Restore feedback.json and re-run before next week's report.

HIGH confidence findings: 1/3 valid + 1 NEW THIS WEEK (pending Gate 2 confirmation)
  ❌ 2026-05-05-ELO-QUALIFIED-001: INVALIDATED — contaminated pool (82% was artefact)
  ✅ 2026-05-07-ELO-QUALIFIED-002: QUALIFIED 63.16% accuracy, n=57 (clean 493-trader pool)
  ✅ 2026-06-01-GEO-ELO-ACCURACY-001: geo_elo Pool C 86.36% accuracy, n=22 geo markets
     (Brier 0.1222 — GOOD tier per Tetlock) — written this run
  ⏳ Need 1 more with n≥20 for Gate 2 completion
  ACTION: Spawn feedback-loop-agent Run 8 (pool=1,449, pool C=177) — can produce
          remaining finding this week

Pre-resolution accuracy: 50% / 4 markets
  (unchanged — pre-res scan stalled since May 10)
  Gate needs: 60% accuracy across 10+ resolved markets
  STR-002 stalled — no new resolved signals in 22 days

RQ1.1 status:   INCONCLUSIVE → DELAYED to July 1, 2026
  Signal filed: rq1_1_insufficient_n (n=10 qualifying, minimum 30)
  ✅ Pre-registration FILED (rq1-1-rerun-pre-registration-june2026.md)
  ⚠ Screen ELO >3000 cluster via RQ0.2 BEFORE July 1 run
RQ3.2 status:   INCONCLUSIVE (methodology reframe — extend RQ2.2 to outcome prediction)

Signal accuracy (June 1):
  STR-003 (geo_elo criteria): 0 signals as of June 1 06:00 UTC. First scan: June 1 08:00.
  STR-003 (old criteria, historical): 1/2 correct (Ramaswamy ✅, Warsh ✗ — scored May 31)
  STR-004: 0/1 resolved correct (Russia/Ukraine ceasefire ✗ — founding case failed)
  Putin invades by June 2026: resolves June 30. Needs fresh geo_elo rescan.
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
              RQ0.2     PASSED          2026-03-29  2026-03-29
              RQ2.2     INCONCLUSIVE    2026-04-26  — (extend to 14/30d window)
──────────────────────────────────────────────────────────────
```

Last updated by performance-analyst-agent: 2026-06-01

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source
