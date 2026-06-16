# Session Summary — Server Setup #36
**Date:** 2026-06-16

---

## System Health (startup)
Both services running. Backup ran 02:00 UTC (12G).
ELO snapshots: 6 days (2848→2931). Pool C +53 to 2,931 — explained: ELO recalc
moved 43 existing traders into Pool C, 10 genuine new ELITE entrants (1434-1537
geo_elo). Not an artifact. LEGENDARY count unchanged at 21.

---

## STR-002 Auto-Scored Overnight (4 new signals)
Now 7 total scored, 1/7 correct (14%). Gate 3: PENDING (7/10).

New scores:
- STR002-0005 [LEGENDARY] Iran peace deal June 7 NO → CORRECT (edge +0.050)
- STR002-0006 [QUALIFIED] Lebanon ceasefire NO → WRONG (edge -0.001)
- STR002-0016 [QUALIFIED] Israel airspace YES → WRONG (edge -0.18)
- STR002-0028 [QUALIFIED] Iran airspace YES → WRONG (edge -0.01)

Stratification (7 scored):
  LEGENDARY / PROVEN / NEAR_RESOLVED:  1/1 correct | edge +0.050
  QUALIFIED / unproven / MID:          0/2 correct | edge -0.505
  QUALIFIED / unproven / NEAR_RESOLVED: 0/4 correct | edge -0.010

Key finding: 1 LEGENDARY correct but on NEAR_RESOLVED market (mkt price 0.05).
Thesis cell (proven + contested) still entirely unscored — all pending resolution.
Conclusion: too early to draw conclusions, but QUALIFIED pattern consistent with
prior analysis (noise). Watch for thesis-cell signals resolving next.

---

## Thin Market Activity Filter (register_str002_signals.py)
Added minimum activity gate to signal registration:
  Threshold: ≥200 trades OR ≥50,000 notional (shares × price)
  Rationale: divergence on a $10K market is noise; divergence on a $500K market
  is potentially signal. All 30 current signals pass (thinnest: 584 trades, $105K).
  Zero duplicate titles found — title→market_id mapping is clean.
Commit dbead6b.

---

## Telegram Alert Noise Fix (5K notifications)
system_observer.py (_check_legendary_trades):
  - Threshold raised: ELITE/NEAR_LEGENDARY/leaderboard-discovery removed
  - Now fires ONLY on TRUE LEGENDARY (geo_elo_active≥2175, pool=1,
    research_excluded=0, bot_type IS NULL) + watched list
  - Minimum position: shares≥500 (dust trades suppressed)
  - Estimated ~90% reduction in alert volume

pre_resolution_intelligence.py:
  - Per-signal Telegram alerts suppressed entirely (was 20+/day)
  - Results still written to scan JSON for STR-002 pipeline
  - Dry-run mode unchanged

Alert policy now:
  ALWAYS: STR-003 signal fired, LEGENDARY counter-signal reversal,
           system CRITICAL, maintenance failure
  NEVER:  ELITE trades, NEAR_LEGENDARY trades, pre-res scan per-signal,
          hourly HEALTHY status

Observer restarted to pick up changes. Commit 109da29.

---

## Research Scout Review
5 items archived (all from June 14 evening run):
- ForesightFlow (arXiv 2605.00493): ILS as STR-002 market selection filter.
  Updated RQ-ILS-001 placeholder with connection to VPIN/informed-flow direction.
- 4 duplicates of previously-reviewed items: straight to reviewed/.

---

## External Literature Research Session
Full synthesis in brain/strategy-notes/research-synthesis-2026-06-16.md.

Key findings:
1. Core thesis validated: 3% of traders drive Polymarket price discovery
   (Gomez-Cram et al. arXiv 2605.02287). Our LEGENDARY pool (0.6%) is MORE
   selective than this threshold. ELITE (7%) may contain genuine skill worth
   retaining in research — confirmed retained (203 ELITE, 22 NEAR_LEGENDARY).

2. Informed-flow > smart-money: the signal is INFORMATION, not INTELLIGENCE.
   Detectable via timing + VPIN order-flow imbalance, not ELO alone.
   $143M in identified informed-trading profits on Polymarket (Harvard 2026).
   This is the highest-value future build direction.

3. Kelly deferral confirmed correct: literature requires 1000s of trades to
   apply Kelly safely. We have 4 thesis-cell signals. Phase 7 deferral stands.
   Fractional Kelly (quarter) is the right parameter when we eventually size.

4. Brier → log-likelihood: DECIDED (see below).

## Two Immediate Decisions Made

✅ Log-likelihood over Brier for Phase 6 calibration layer.
Documented in calibration-metric-decision-2026-06-16.md. Brier
over-encourages extreme probability predictions — misleads exactly in our
near-resolved-heavy signal distribution.

✅ ELITE confirmed retained in research pool.
203 ELITE + 22 NEAR_LEGENDARY in research pool. Alert suppression is
LEGENDARY-only, not a research exclusion.

## Three Builds Deferred (July+, require pre-registration)
1. RQ-VPIN-001: informed-flow signal (VPIN + SCL-009 books + ILS + maker/taker)
2. Sign-randomization skill validation (Gomez-Cram methodology on LEGENDARY pool)
3. Fractional Kelly parameter (Phase 7, already in deferral notes)

---

## Pending — Next Sessions

### Tomorrow (June 17):
1. Fed markets resolve — 6 ELITE signals auto-score (all NEAR_RESOLVED, expect ~0 edge)
2. Check maintenance logged counter-signal detector + STR-002 steps cleanly

### Coming days:
3. Maine RCV final result (any day — score 3 ELITE + 2 QUALIFIED STR-002 signals)
4. Counter-signal detector: 6 snapshot days now, 7 minimum (June 18 earliest)

### June 30:
5. Score STR003-004/007/008 correlated cluster
6. RQ-CORRELATION-001 on cluster outcome

### July 1 wave:
7. RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001
8. Pre-register RQ-VPIN-001 (informed-flow signal)
9. Pre-register sign-randomization skill validation
10. RQ-ILS-001 proper pre-registration
11. STR-002 thesis-cell analysis (proven + contested vs QUALIFIED control)

### Mid-July:
12. Peru ONPE oracle → confirm STR003-005 + score 5 LEGENDARY STR-002 signals

---

## Pool Status (end of session)
| Metric | Value |
|--------|-------|
| Pool C | 2,931 |
| LEGENDARY active clean | 18 |
| ELITE in research pool | 203 |
| NEAR_LEGENDARY in research pool | 22 |
| ELO snapshots | Day 6 (June 11-16) |
| STR-002 registered | 30 signals, 7 scored (14% acc, 10 clusters) |
| STR-002 thesis cell | 4 signals still pending |
| STR-003 active | 3 signals resolving June 30 |
| Telegram noise | Fixed (LEGENDARY-only, ~90% reduction) |
| Thin-market filter | Active (≥200 trades OR ≥50K notional) |
| Integration contract | v2.10 |
| Research synthesis | Complete — 2 decisions, 3 deferred |
