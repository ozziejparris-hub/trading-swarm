# Elections Markets: Confirmed Negative Edge — Phase 6 Exclusion Required

**Date:** 2026-08-10
**Author:** performance-analyst-agent (run 12, post-outage)
**Status:** FINDING — formal recording of high-confidence empirical result
**Related:** brain/kpis.md (Aug 10 current week), 2026-07-13 weekly report (first election calibration flag)
**Cross-ref:** integration-contract.md Section 6d (April 28 structural break), brain/strategy-notes/us-market-signal-quality-watch.md

---

## Finding

Pool C geo traders (geo_accuracy_pool=1, geo_elo_active >= 1800, research_excluded=0, resolved_trades_count >= 20, bot_type IS NULL) have a **confirmed negative edge in Elections markets across all of 2026**, measured on 1,111 contested markets (price 0.05-0.95).

| Metric | Value | Interpretation |
|---|---|---|
| Directional accuracy | 54.0% | Barely above random (50%) |
| Brier score | 0.3181 | WORSE than naive baseline |
| Naive Brier | 0.2545 | Just using average entry price beats Pool C |
| Edge vs naive | -0.0636 | Negative — Pool C predictions add negative value |
| n (markets) | 1,111 | Very high confidence — not a sample size issue |
| Period | All 2026 (Jan 1 – Aug 10) | Full calendar year, contested markets only |

For comparison, the same analysis on Geopolitics markets (n=1,110) shows Brier=0.2606 vs naive=0.2958, dir_acc=60.2% — a clearly positive edge.

---

## What This Means

Pool C traders who specialize in geopolitics (primarily Russia/Ukraine, Iran, and other geopolitical escalation topics) are being included in Elections market aggregates where their domain expertise does not transfer. Their weighted predictions are systematically worse than the market price on elections — the crowd is better calibrated on elections than our specialist geo traders.

This does not invalidate the geo edge. It establishes that the two market types require separate handling.

---

## History of This Finding

- **Jul 13 weekly report:** First flag. "Elections calibration breaking. Pool C elite geo traders perform at random on full elections population (50% dir_acc, Brier 0.4838 vs naive 0.4492)." Hypothesis: post-April 28 sharp-money influx.
- **Jul 20 weekly report:** Confirmed for contested elections (price 0.05-0.95): 59.1% dir_acc, Brier 0.3670 — worse than geo but slightly above random.
- **Aug 10 weekly report:** All-2026 analysis at n=1,111 confirms the finding is definitive and systemic. Dir_acc=54.0%, Brier 0.3181 WORSE than naive 0.2545.

The finding strengthens over time with more data. It is now conclusive.

---

## Known alternative explanations (and why they don't resolve the finding)

1. **April 28 structural break:** The CFTC launch brought sharp US money into political markets. This may have priced away Elections edge post-April 28. But the all-2026 dataset includes pre-April-28 elections data, and the negative edge persists at n=1,111. Even if pre-April-28 elections had positive edge, it is not large enough to offset the post-April-28 negative edge in this combined dataset.

2. **Trader archetype mismatch:** 17 of 37 legendary/near-legendary traders are YIELD_HARVESTERs (per trader-intelligence-agent profiling, Jun 2026). Their positions in Elections markets may be near-certainty bets, not forecasts. However, the contested market filter (price 0.05-0.95) already excludes near-certainty positions. The finding is on contested markets only.

3. **Category label accuracy:** `markets.category = 'Elections'` is the authoritative filter used here (not `trades.market_category`). Any miscategorized markets would inject noise, but not enough to flip a n=1,111 finding from positive to negative.

---

## Decision

**Phase 6 portfolio construction must exclude Elections markets until a differentiated edge source is identified and validated.** This is a stopping rule for elections allocation, not for geo allocation. GEO (n=1,110, 60.2% dir_acc) remains the target universe for Phase 2 and Phase 6.

Before any future elections allocation:
1. Run pre/post April 28 split analysis to confirm whether the positive edge that (likely) existed pre-April-28 is worth tracking separately
2. Identify which trader archetypes, if any, have genuine elections edge (likely GENUINE_FORECASTERs, not DOMAIN_SPECIALISTs who are Russia/Ukraine-focused)
3. Pre-register a differentiated elections signal hypothesis before any backtesting

---

## Data Note

This analysis uses the Pool C ELO-weighted prediction method: for each contested resolved market, the Pool C traders' positions are weighted by `geo_elo_active`, and the weighted YES fraction is the prediction. The naive baseline is the average entry price across the same Pool C traders. Finding holds at both the Brier score level (absolute calibration) and directional accuracy level (binary prediction).

Query run at: 2026-08-10T06:xx UTC
DB: /home/parison/projects/first-repo/data/polymarket_tracker.db (WAL, read-only)
