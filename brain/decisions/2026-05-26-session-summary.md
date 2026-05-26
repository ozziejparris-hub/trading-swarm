# Session Summary: Server Setup 12 — 2026-05-26

## What Was Built

### 1. System Health Confirmed — All Fixes Holding
- No DB locks or freezes since May 25 restart
- Fix 1+2+3 all verified working
- Daily maintenance completed in 47 minutes (vs 7.4 hours last Sunday)
- Pool C intact at 435 traders, geo_elo correctly populated

### 2. Tier 2.5 → Tier 3 Handoff Pipeline Validated
- Full end-to-end test: Tier 2.5 queried DB, wrote handoff file, Tier 3 spawned automatically via `--handoff` flag, produced strategic output
- No manual intervention required at any point
- Token consumption significantly reduced for Tier 3
- Test task: geo_elo pool status → STR-003 viability assessment
- Key finding: 21 qualified LEGENDARY traders, 4% per-market participation rate

### 3. RQ-GEO-ELO-003 Out-of-Sample Validation Complete
- LEGENDARY OOS: 9.4% (2 traders, 1 market — statistically unreliable)
- QUALIFIED OOS: 58.7% across 4 markets — 15pp degradation from in-sample
- Failure condition fired but result not meaningful (data sparsity)
- Conclusion: data maturity issue, not methodology failure
- Need 20+ resolved OOS geo markets with LEGENDARY representation

### 4. STR-003 Participation Rate Investigation
- All 21 geo_elo LEGENDARY traders stopped trading Dec 31 2025
- They are Haley market specialists, dormant since January 2026
- 562 active Pool B traders in 2026 geo markets — not yet scored
- 29 Pool B traders ready for geo_elo calculation (>= 5 resolved geo trades)

### 5. Pool Expansion — Three New Discovery/Scoring Improvements
- geo_elo calculated for 29 newly-eligible Pool B traders via CC
- **Resolution sweep** (`scripts/resolution_sweep.py`) — NEW script
  - Sweeps all significant traders from recently-resolved geo markets
  - 7 traders promoted from Ukraine ceasefire market ($187K–$2M positions)
  - Added to `daily_maintenance.py` as step 2b (7-day default window)
- **Insider signals outcome scoring** (`scripts/score_insider_signals.py`) — NEW
  - Added `outcome_correct`, `resolved_at`, `information_value`, `scored_at` columns
  - Added to `daily_maintenance.py` as step 2c
  - Current accuracy: 50% raw (3/6 resolved), weighted +0.041

### 6. Mitts/Ofir Composite Insider Score — Full Implementation
- Five signals implemented: cross-sectional bet size, within-trader anomaly, entry price contrarianism, pre-resolution timing, directional concentration
- Hard disqualification: `entry_price > 0.80` (filters arb bets)
- Composite score columns added to `insider_signals` table
- 3 of 7 existing signals disqualified as arb bets (IDs 1, 2, 7)
- 2 high-conviction signals identified (IDs 3, 5 — Iran bets, both wrong)
- Cluster detector tightened: geopolitics only, $50K minimum, composite >= 0.35
- Historical calibration on 179,204 trades: optimal threshold 0.45 (59.4% win rate)
- `MIN_COMPOSITE_SCORE` raised from 0.30 to 0.45
- Live 30-day backtest: 0 signals at calibrated threshold (correct — no noise)

### 7. Pattern Recognition Agent Concept Documented
- Added to `research-directions.md` as CONCEPT
- Prerequisites: Phase 5 gates, 3 months pattern data, pre-registration framework
- Status: do not build until Phase 5

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Handoff pattern works — use for all future Tier 3 spawns with pre-computed data | Validated end-to-end; reduces Tier 3 token cost |
| geo_elo LEGENDARY pool is dormant (Haley traders) — need 2026 geo markets to resolve | All 21 stopped trading Dec 31 2025 |
| Resolution sweep is now permanent infrastructure — runs daily, 7-day window | Caught 7 traders from Ukraine ceasefire market immediately |
| Composite score threshold 0.45 is data-driven, not intuition-based | Calibrated on 179,204 historical trades |
| Blockchain wallet creation date and funding source = next major detection improvement | Current signals miss wallet-cluster correlations |
| Do not run insider signals live until 100+ resolved outcomes for proper calibration | Only 6 resolved currently — too few |

---

## Next Session Priorities

1. Investigate Polygon blockchain API for wallet creation dates and funding sources
2. Wallet cluster correlation using funding source linkage
3. Calculate geo_elo for 562 active 2026 Pool B traders as their markets resolve
4. STR-003 concurrent markets criterion — all qualified traders hold 15–1,626 markets
5. June 1 — RQ1.1 rerun (pre-registered, Phase 5 gate, 6 days away)
