# Decision Record — ELO Calibration Drift Investigation Required

**Date:** 2026-05-05  
**Raised by:** performance-analyst-agent (weekly analysis)  
**Status:** OPEN — requires quant-research-agent investigation before June 1 RQ1.1 rerun  
**Priority:** HIGH

---

## Finding

March 16 baseline: ~15 legendary traders (ELO > 2175) across 53,140 traders.  
May 5 current: 432 legendary traders in full active pool (elo_last_updated within 7 days), 341 in research pool (research_excluded=0) across 92,228 total.

This is a **28x increase** in legendary trader count relative to baseline — from 0.03% of all traders to 0.47%.

---

## Why It Matters

1. **RQ1.1 methodology:** Tests whether Period 1 ELO predicts Period 2 Brier score. If the ELO scale has shifted, the correlation measurement may be comparing different populations across periods.

2. **RQ3.2 methodology:** Tests whether legendary consensus beats market price. If "legendary" now includes 432 traders instead of 15, the consensus signal is measuring a materially different group.

3. **STR-003 signal:** The `ELO > 2175` threshold filters legendary traders for directional signals. If the legendary pool has expanded 28x, the expected quality of any individual signal is lower.

4. **STR-001b validation:** Was waiting for more qualifying signals. With 432 legendary traders vs 15, there may now be sufficient exclusive convergence cases to backtest.

---

## Likely Causes to Investigate

1. **ELO modifier activation** — findings.json notes that early ELO runs used modifiers frozen at 1.0x. When behavioral_modifier, advanced_modifier, and pnl_modifier were activated, all scores were multiplied upward. Quantify this effect.

2. **Database composition change** — new traders entering the DB from May 2026 may be disproportionately active/high-volume (e.g., captured from high-ELO markets first).

3. **Recalibration of base ELO** — check if `apply_full_elo_modifiers.py` was rerun with different parameters between March and May.

---

## Investigation Steps for quant-research-agent

1. Query `elo_period1_cutoff` distribution: how many traders had ELO > 2175 as of Period 1 cutoff (2026-04-01)?
2. Query `comprehensive_elo` distribution: how many traders have ELO > 2175 now?
3. For each legendary trader in current pool: what was their `elo_period1_cutoff`? Were they already legendary in Period 1?
4. Check the ELO modifier values: `SELECT AVG(behavioral_modifier), AVG(advanced_modifier), AVG(pnl_modifier) FROM traders WHERE comprehensive_elo > 2175;` — if modifiers are significantly >1.0, that explains the inflation.
5. If modifier inflation is confirmed: recommend recalibrating legendary threshold to top 0.03% percentile (≈28 traders at current 92K total) rather than absolute cutoff of 2175.

---

## Decision Required

**From Oscar:** After quant-research-agent completes investigation, decide whether to:

**Option A:** Recalibrate the legendary threshold to maintain the same population percentile (top 0.03% → new ELO cutoff calculated from current distribution)  
**Option B:** Accept the current threshold (2175) and treat the expanded pool as a different but valid definition of "legendary"  
**Option C:** Create a new "elite_elite" tier (e.g., ELO > 3000) that matches the March baseline population more closely

This decision affects STR-003 signal quality, STR-001b backtest scope, and RQ1.1/RQ3.2 rerun design.

---

## Deadline

Before June 1 RQ1.1 rerun. The rerun methodology depends on whether the threshold is recalibrated.

---

*Raised by: performance-analyst-agent | 2026-05-05T12:30:00Z*
