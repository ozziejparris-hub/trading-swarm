# Decision Record: Elections Calibration Investigation Required

**Date:** 2026-07-13
**Author:** performance-analyst-agent (run 10)
**Status:** OPEN — investigation triggered, decision pending

---

## Observation

Pool C elite geo traders (geo_elo_active ≥ 1800, Pool C, price filter 0.05–0.95, 30d window) show:

**Geopolitics (contested):** Brier 0.2552, dir_acc 70.8%, n=48. Solid, beats naive by 11.7pp.

**Elections (contested only):** Brier 0.3855, dir_acc 59.1%, n=22. Marginally above random, beats naive 0.5216 by 13.6pp.

**Elections (ALL markets):** Brier 0.4838 vs naive 0.4492 — **WORSE THAN NAIVE**. Dir_acc = 50.0%. n=32.

## Significance

The elections full-population result is alarming: Pool C's best traders are statistically worse than the market price at predicting elections outcomes. This cannot be explained by sample size alone (n=32 is meaningful). Two hypotheses:

1. **Post-April-28 structural break**: Polymarket launched CFTC-regulated under V2 on April 28 2026, with sharp-money influx (hedge funds, DC insiders). Elections markets — particularly US political markets — may now have sufficient informed capital to price efficiently, eliminating the exploitable mispricing that geo_elo captured.

2. **Geo_elo misspecification**: The geo_elo model conflates geopolitics (hard to price, few experts) and elections (easier to price, more public information). The geo_elo accuracy (79.6% LEGENDARY) is driven by geopolitics, not elections. Elections may never have been a reliable signal category.

## Required Analysis

- Split elections markets pre/post April 28 2026 and recompute directional accuracy for each window.
- If the break is post-April-28 only → attribute to sharp-money influx; elections may recover if trading volume normalizes.
- If elections was always weak (pre-April-28 also random) → elections is a bad signal category; remove from Phase 6 scope.

## Phase 6 Implication

Phase 6 portfolio construction currently assumes geo + elections scope. If elections calibration is broken, Phase 6 should be geo-only until elections calibration is demonstrated over ≥60 contested markets.

**Decision to be made by Oscar after analysis.** Do not allocate capital to elections markets until this is resolved.

## Action

1. Quant-research-agent: run elections calibration pre/post April 28 2026 split analysis
2. If post-April-28 elections accuracy < 55% consistently: file decision record to remove elections from Phase 6 scope
3. If pre-April-28 accuracy was also weak: retire elections from research pipeline

**Priority:** HIGH — blocks Phase 6 scope definition.
