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

Last updated: 2026-07-20
Updated by: performance-analyst-agent (run 11)

### Week of 2026-07-20

#### Prediction Accuracy
```
⚠ CONTEXT: Brier deterioration this week is primarily an artefact of the Jun 30
  Iran cluster (130+ markets, Pool C bullish, resolved No) dominating the 30d window,
  NOT underlying calibration decay. O-37 quarantine (84 synthetic markets removed
  2026-07-19) also shifts some historical pool_c calibration baselines.

PRIMARY: geo_elo Pool C (geo_accuracy_pool=1, contested mkts only):
  GEOPOLITICS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.3643  ⚠ Iran-cluster artefact (n=94)
    Directional accuracy (30d):       36.8%   ⚠ Iran-cluster artefact
    NOTE: Jun30 cluster dominates (130/145 resolved markets). Pool C systematically
          bullish on Iran-escalation outcomes that resolved No. Expect recovery
          to ~0.25 range as Jun30 markets age out of 30d window (~Jul 30).
  GEOPOLITICS (7d, contested):
    n=0 markets — genuine market lull post-Jun30 cluster resolution
  ELECTIONS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.3670  ⚠ includes 2028 nomination markets
    Directional accuracy (30d):       32.0%   (n=46)
    NOTE: Sessions notes (Jul 19) flag elections calibration for re-check post
          O-37 quarantine — some synthetic elections markets now removed.
  ELECTIONS (7d, contested):
    n=7 markets only — insufficient for trend

  VALIDATED BASELINE (HIGH confidence, unchanged):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)
```

#### ELO System Health
```
Total traders (DB):                ~155,000+
True research pool (resolved≥20):  16,289   (vs 16,262 Jul 13 — +0.2%)
Research pool (research_excluded=0): 29,303  (vs 26,646 Jul 13 — +10%)
Pool C (geo_accuracy_pool=1):       3,223   ↑ (vs 3,212 Jul 13)
geo_elo LEGENDARY (geo_elo ≥ 2175):   62    (vs 80 Jul 13 — ↓18 from O-37)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 17  (vs 26 Jul 13 — ↓9)
  NOTE: Drop in legendary_active/base is partly structural (O-37 quarantine removed
        17 traders whose ENTIRE geo_elo history was synthetic, up to elo_active=2541).
        Pool is CLEANER not weaker. Some residual drop from dormancy decay.
legendary_clean (geo_elo_active≥2175, pool_c, research_excl=0): 13 (vs 14 Jul 13)
near_legendary_clean (geo_elo_active 1800-2174): 28 (vs 38 Jul 13 — also O-37 affected)
Active traders (7d, all):          614  (vs 2,486 Jul 13 — sharp drop)
Pool C geo activity (7d):          8 traders, 8 trades (vs 226/1,245 Jul 13 — ⚠ monitor)
Closest to LEGENDARY threshold:    elo_active=2148 (0xc624... 27 pts from threshold)
Writer A Sunday ELO run (Jul 20):  26,942 updated, 0 failed — confirmed clean
Clean markets (DB):                223,791  (vs 223,651 Jul 13)
O-37 quarantine (Jul 19):          84 synthetic markets, 965,542 trades flagged
Contract violations (Section 9):   NONE — all thresholds met ✅
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria, gate-valid signals):
  Qualifying traders (legendary_clean): 13  (vs 14 Jul 13)
  Gate-valid scored accuracy:          2/5 = 40%  (FROZEN — signal-agent dark 7d)
  STR003-004 (Putin NO):               DB UNRESOLVED ⚠ (21 days overdue)
  New signals this week:               NONE
  Signal-agent status:                 Dark since Jul 13 (7 days)
  Gate 3 risk:                         HIGH — frozen at 40%, n=5, need 60% on n=10
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 13 clean LEGENDARY, Gate 3 FROZEN at 40%
STR-004:   HYPOTHESIS — 0/1. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 4/7 insider signals correct (57.1%)
RQ-GEO-ELO-001: NOT STARTED ⚠⚠⚠ — 8 WEEKS, GATE 4 PERMANENTLY BLOCKED
RQ1.1:     BLOCKED — depends on RQ-GEO-ELO-001
RQ3.2:     INCONCLUSIVE — reframe needed
ELO Arc:   Stage 3 COMPLETE (Jul 20 Sunday run confirmed clean)
Edge Expt: B4 active (order book), B1 next (ELO baseline proven clean post O-37)
O-37:      CLOSED — 84 synthetic markets / 965,542 trades quarantined (Jul 19)
```

#### System Resources
```
Estimated API spend (7d Jul 13-20): ~$1-2  (performance-analyst + routine agents)
trading-swarm orchestrator:        ACTIVE
polymarket-monitoring:             ACTIVE
Git commits (trading-swarm, 7d): ~20 (session summaries, ELO arc docs, O-37 ledger)
Git commits (first-repo, 7d):    ~15 (ELO arc 1-3, B4 order book, O-37 quarantine)
Brain directory size:              6.9MB (vs 6.1MB Jul 13 — +13%)
First-repo DB:                     ~14GB
CI pipeline:                       FAILING — 10th+ consecutive Sunday (__init__.py + lint)
Signal-agent:                      DARK — 7 days (last output Jul 13)
Quant-research:                    DARK — 8+ weeks (RQ-GEO-ELO-001 never executed)
Backtest-agent:                    DARK
B4 (order book):                   ACTIVE (capturing; 1,105/1,159 markets with tokens)
```

#### Week-on-Week Trends
```
Brier (geo, 30d contested):     0.2552 (Jul 13) → 0.3643 (Jul 20) ↓ ⚠ Iran-cluster artefact
Brier (elections, 30d contested): 0.3855 (Jul 13) → 0.3670 (Jul 20) ↑ slight
Legendary ACTIVE (geo_elo_active≥2175): 26→17 ↓↓ (O-37 + decay)
Legendary CLEAN:                        14→13 ↓ (1 trader decayed below threshold)
NEAR_LEGENDARY clean:                   38→28 ↓↓ (O-37 recomputation)
True research pool (resolved≥20):       16,262→16,289 ↑ marginal
Pool C:                                  3,212→3,223 ↑ marginal
Active traders (7d):                     2,486→614 ↓↓ (sharp — monitor)
Pool C geo activity (7d):                226 traders→8 traders ↓↓ (monitor)
Phase 5 Gate 1:                    ✅ COMPLETE (14+ runs)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5)
Phase 5 Gate 3:                    2/5 = 40% (FROZEN — signal-agent dark, STR003-004 unresolved)
Phase 5 Gate 4:                    BLOCKED — RQ-GEO-ELO-001 8 weeks unexecuted
O-37:                              ✅ CLOSED (Jul 19) — 17 fake LEGENDARY traders removed
```

### Previous Week (2026-07-13 — for reference)

#### Prediction Accuracy
```
⚠ METHODOLOGY CORRECTION THIS WEEK:
  Prior analyses used uppercase 'YES'/'NO' case comparison vs actual 'Yes'/'No' in DB.
  Current numbers use correct case matching and contested-market filter (price 0.05-0.95).
  Previous weekly Brier figures are NOT comparable. Recomputation recommended.

PRIMARY: geo_elo Pool C (geo_accuracy_pool=1, geo_elo_active>=1800, contested mkts only):
  GEOPOLITICS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.2552  (beats naive 0.3723, edge=+0.117, n=48)
    Directional accuracy (30d):       70.8%
  ELECTIONS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.3855  (beats naive 0.5216, edge=+0.136, n=22)
    Directional accuracy (30d):       59.1%
  ELECTIONS (30d, ALL markets — WARNING):
    Brier score (30d):                0.4838  ❌ WORSE THAN NAIVE 0.4492 (n=32)
    Directional accuracy (30d):       50.0%  — random baseline
  GEO (7d, contested):
    Brier score (7d):                 0.0936  ⚠ n=3 only, insufficient for trend
    Directional accuracy (7d):        100%

  VALIDATED BASELINE (HIGH confidence, unchanged):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  KEY FINDING: Geo edge is solid (70.8% dir_acc, contested). Elections is near-random
  on full population — post-April-28 sharp money may have priced away the edge.
  Investigation required before Phase 6 elections allocation.
```

#### Prediction Accuracy
```
⚠ METHODOLOGY CORRECTION THIS WEEK:
  Prior analyses used uppercase 'YES'/'NO' case comparison vs actual 'Yes'/'No' in DB.
  Current numbers use correct case matching and contested-market filter (price 0.05-0.95).
  Previous weekly Brier figures are NOT comparable. Recomputation recommended.

PRIMARY: geo_elo Pool C (geo_accuracy_pool=1, geo_elo_active>=1800, contested mkts only):
  GEOPOLITICS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.2552  (beats naive 0.3723, edge=+0.117, n=48)
    Directional accuracy (30d):       70.8%
  ELECTIONS (30d, contested price 0.05-0.95):
    Brier score (30d):                0.3855  (beats naive 0.5216, edge=+0.136, n=22)
    Directional accuracy (30d):       59.1%
  ELECTIONS (30d, ALL markets — WARNING):
    Brier score (30d):                0.4838  ❌ WORSE THAN NAIVE 0.4492 (n=32)
    Directional accuracy (30d):       50.0%  — random baseline
  GEO (7d, contested):
    Brier score (7d):                 0.0936  ⚠ n=3 only, insufficient for trend
    Directional accuracy (7d):        100%

  VALIDATED BASELINE (HIGH confidence, unchanged):
    Pool C full 2026 accuracy:        70.7%  (2026-06-05-POOL-C-GEO-FULL-2026-001)
    LEGENDARY geo_elo tier:           79.6%  (n=49 markets)

  KEY FINDING: Geo edge is solid (70.8% dir_acc, contested). Elections is near-random
  on full population — post-April-28 sharp money may have priced away the edge.
  Investigation required before Phase 6 elections allocation.
```

#### ELO System Health
```
Total traders (DB):                ~155,000+
True research pool (resolved≥20):  16,262   (vs 13,855 Jul 6 — +17%)
Research pool (research_excluded=0): 26,646  (vs 26,399 Jul 6 — +1%)
Pool C (geo_accuracy_pool=1):       3,212   ↑ RECOVERING (vs 2,607 Jul 6, +23%)
geo_elo LEGENDARY (geo_elo ≥ 2175):   80    (vs 61 Jul 6 — +31%)
geo_elo LEGENDARY (geo_elo_active ≥ 2175): 26  (vs 19 Jul 6 — recovering)
legendary_clean (geo_elo_active≥2175, pool_c, research_excl=0): 14 (FLAT — 4th week)
near_legendary_clean (geo_elo_active 1800-2174): 38 (vs 35 Jul 6 — slight recovery)
Max geo_elo_active:                3,798.8  (0xd44e974a — decaying from 4,118.7)
Active traders (7d, all):          2,486  (vs 562 Jul 6 — recovery)
Pool C active (7d, BUY):           226 traders, 1,245 buys, $189K volume
Legendary active this week:        5 unique traders, 10 trades
Top 2 ELO holders dormant since:   June 22 (3+ weeks)
Clean markets (DB):                223,651  (vs 92,144 Jul 6 — +142% O-16/O-17 pipeline)
Contract violations (Section 9):   NONE — all thresholds met ✅
```

#### Signal Quality
```
STR-003 (geo_elo_active criteria, gate-valid signals):
  Qualifying traders (legendary_clean): 14
  Gate-valid scored accuracy:          2/5 = 40%  (005✅, 008✅ vs 003✗, 006✗, 009✗)
  Total accuracy (incl non-scorable):  3/6 = 50%  (adds 007✅)
  LEGENDARY vs non-LEGENDARY:          2/3 = 67%  vs 1/3 = 33% (tier distinction validated)
  Signal-agent status:                 DARK 159+ hours (8th consecutive Sunday failure)
  New signals this week:               NONE (signal-agent dark)
  Gate 3 risk:                         HIGH — frozen at 40%, n=5
```

#### Strategy Pipeline
```
STR-003:   EXPERIMENTAL — 14 clean LEGENDARY, Gate 3 FROZEN at 40%
STR-004:   HYPOTHESIS — 0/1. 9 more signals needed.
LH-001:    CONDITIONAL_PASS — 4/7 insider signals correct (57.1%)
RQ-GEO-ELO-001: NOT STARTED ⚠⚠⚠ — 7 WEEKS, Jul 1 deadline MISSED
RQ1.1:     BLOCKED — depends on RQ-GEO-ELO-001
RQ3.2:     INCONCLUSIVE — reframe needed
ELO Arc:   Stage 0 COMPLETE (W_beh=0 — Jul 12); Stage 1 queued
```

#### System Resources
```
Estimated API spend (7d Jul 6-13): ~$1-2  (training-librarian + performance-analyst)
trading-swarm orchestrator:        ACTIVE (06:00 cycle clean this morning)
polymarket-monitoring:             ACTIVE
Git commits (trading-swarm, 7d): ~20 (ELO arc docs, signals.json safe-write, O-14)
Git commits (first-repo, 7d):    ~12 (safe-write 8 writers, health_checker, Stage 0c)
Brain directory size:              6.1MB (vs 5.2MB Jul 6 — +17%)
First-repo DB size:                14GB (vs 12GB Jul 6 — +17%)
Clean markets (DB):                223,651 (vs 92,144 Jul 6 — +142%; O-16/O-17 pipeline)
CI pipeline:                       FAILING — 10th consecutive Sunday (NEW: __init__.py)
Signal-agent:                      DARK — 159+ hours (8th Sunday failure)
Quant-research:                    DARK — 34 days
Backtest-agent:                    DARK — 42 days
ELO Arc Stage 0:                   ✅ COMPLETE (W_beh=0 accepted)
signals.json safe-write:           ✅ COMPLETE (all 8 writers → json_safety.py)
```

#### Week-on-Week Trends
```
Brier (geopolitics, 30d contested):  ~[prior¹] → ~[prior¹] → ~[prior¹] → 0.2552 (Jul 13)
Brier (elections, 30d contested):    ~[prior¹] → ~[prior¹] → ~[prior¹] → 0.3855 (Jul 13)
¹ Not comparable — prior numbers used different methodology
Legendary ACTIVE (geo_elo_active≥2175): 13→24→29→19→26 ↑ (recovering)
Legendary CLEAN:                         9→17→16→14→14 → (flat)
NEAR_LEGENDARY clean:                   18→22→41→35→38 ↑ (recovering)
True research pool (resolved≥20):  1,738→3,902→8,221→13,855→16,262 ↑↑↑
Pool C (geo_accuracy_pool):          504→2,875→2,157→2,607→3,212 ↑ RECOVERING
Active traders (7d):              ~2,395→2,573→679→562→2,486 ↑ RECOVERY
Phase 5 Gate 1:                    ✅ COMPLETE (12+/4 runs)
Phase 5 Gate 2:                    ✅ COMPLETE (confirmed Jun 5)
Phase 5 Gate 3:                    2/5 = 40% gate-valid (FROZEN)
Phase 5 Gate 4:                    BLOCKED — RQ-GEO-ELO-001 Jul 1 deadline MISSED (7 wks)
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

### Previous Week (2026-07-06 — for reference)

#### Prediction Accuracy
```
⚠ NOTE: Previous Brier methodology used different case comparison and included
   near-certainty stub markets. Numbers are not comparable to Jul 13 figures.
Geopolitics Brier (30d, prior method):  0.1798  (n=89, inflated by Jun-30 stubs)
Elections Brier (30d, prior method):    0.1912  (n=68, inflated by Jun-30 stubs)
Combined accuracy (30d, prior method):  ~81.5%
```

#### ELO System Health
```
Total traders (DB):                155,663
True research pool (resolved≥20):   13,855
geo_elo LEGENDARY (geo_elo ≥ 2175):    61
geo_elo_active LEGENDARY:               19
Pool C (geo_accuracy_pool=1):        2,607
legendary_clean:                        14
near_legendary_clean:                   35
Active traders (7d, BUY):              562
Clean markets (DB):                 92,144
```

---

## Phase 5 Gate Tracker

Last updated: 2026-07-20 (performance-analyst-agent run 11)

```
Gate 1 — Feedback-loop runs: 14+/4 ✅ GATE MET
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
  Run 13: 2026-07-06 (cron, Monday — completed)
  Run 14: 2026-07-13 (cron, Monday — completed)
  Run 15: 2026-07-20 (cron, Monday — due today)

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
    STR003-008 (EU Security NO):    RESOLVED_CORRECT ✅ (Jul 4)
    STR003-009 (Graham SC NO):      RESOLVED_WRONG ✗
  Not gate-valid: STR003-007 (Iran — retrospective), STR003-004 (Putin — fails geo_elo)
  STR003-004 outcome: DB shows resolved=0 ⚠ — 21 days overdue, needs manual fix
  Gate-valid accuracy: 2/5 = 40% (FROZEN since Jul 4)
  Total (incl non-scorable 007): 3/6 = 50%
  Need: 6+ correct from 5+ remaining to reach 60% on n=10
  Risk: LEGENDARY_clean now 13 (post O-37 quarantine), signal-agent dark 7d
  O-37 note: 17 fake LEGENDARY traders removed (scores were entirely synthetic)
             Pool is CLEANER — remaining 13 are all real

Gate 4 — RQ1.1 + RQ3.2:
  RQ1.1: BLOCKED — RQ-GEO-ELO-001 NOT STARTED (8 weeks, deadline Jul 1 MISSED)
    ⚠⚠⚠ CRITICAL: Spawn quant-research-agent. Richest dataset ever (16,289 pool, 223K markets)
  RQ3.2: INCONCLUSIVE (methodology reframe needed — extend RQ2.2 to outcome)

Signal accuracy (July 20):
  STR-003 (gate-valid): 2/5 = 40% — FROZEN (signal-agent dark 7d; no new signals)
  STR-003 legendary clean: 13 (post O-37 quarantine — 17 synthetic traders removed)
  NEAR_LEGENDARY clean: 28 (vs 38 Jul 13 — affected by O-37 recomputation)
  STR-004: 0/1 founding case ambiguous. 9 more signals needed.
  LEGENDARY tier accuracy: 2/3 = 67% vs non-LEGENDARY 1/3 = 33% — tier signal validated
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

Last updated by performance-analyst-agent: 2026-07-20

Stopping rules (halt all research if either fails):
- RQ1.1: ELO has no predictive validity → redesign ELO system
- RQ3.2: Markets efficient vs elite consensus → pivot edge source

⚠⚠ CRITICAL DEPENDENCY NOTE: RQ-GEO-ELO-001 Phase 1 is the prerequisite for RQ1.1 rerun.
  RQ-GEO-ELO-001 was Oscar-approved May 25 and has NOT been executed (7 weeks elapsed).
  Dataset is now the richest in system history (16,262 true_research_pool, 223,651 clean markets).
  Spawn quant-research-agent immediately. Each additional week delays Gate 4 by 1 week.

NEW FINDING (Jul 13): Elections calibration breaking. Pool C elite geo traders perform at
  random on full elections population (50% dir_acc, Brier 0.4838 vs naive 0.4492).
  Only contested elections (price 0.05-0.95): 59.1% dir_acc (weak but above random).
  Hypothesis: post-April-28 sharp-money influx pricing away elections edge.
  Action: pre/post April 28 split analysis required before Phase 6 portfolio allocation.

ELO ARC STAGE 3 COMPLETE (Jul 20): Writers A+B both on canonical formula. Sunday
  canonical run confirmed clean (26,942 updated, 0 failed). B1 edge experiment next.

ELO ARC STAGE 0 COMPLETE (Jul 12): W_beh=0 — behavioral ELO weighting adds no accuracy
  improvement.

O-37 CLOSED (Jul 19): 84 synthetic markets / 965,542 trades quarantined. 17 fake
  LEGENDARY traders removed (entire geo_elo history was synthetic). 0 Pool-C exposure.
  LEGENDARY pool is cleaner post-quarantine.
