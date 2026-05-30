# STR-003 Anti-Arb Phase 1 — Arb Contamination Quantification
**Date:** 2026-05-30  
**Analyst:** Claude Code  
**Pre-registration ref:** rq-str003-antiarb-preregistration-2026-05-30.md

---

## Cohort Definition

| Filter | Value |
|--------|-------|
| `geo_elo` | ≥ 2175 (LEGENDARY tier) |
| `geo_directionality_score` | ≥ 0.70 |
| `realized_pnl` | > $500 |
| Market categories | Geopolitics, Elections |
| Trade result | `won` or `lost` (resolved only) |
| Trade gap exclusion | `trade_gap_flag = 0 OR NULL` (Apr 7–18 gap excluded) |

---

## Query 1 — Overall Distribution

| Metric | Count | % of Total |
|--------|-------|------------|
| Total resolved geo trades | 22,850 | 100.0% |
| Price < 0.10 (low-end arb) | 3 | 0.01% |
| Price > 0.80 (high-end arb) | 96 | **0.4%** |
| Price 0.10–0.80 (in-range) | 22,751 | 99.6% |

**Overall arb contamination (price > 0.80): 0.4%**

---

## Query 2 — Per-Trader Breakdown (Top 10 by Arb %)

| Trader | Resolved Trades | Arb Trades (>0.80) | Arb % | geo_elo | PNL ($) |
|--------|----------------|---------------------|-------|---------|---------|
| 0x63d43bbb...34fa2f1 | 106 | 96 | **90.6%** | 3,503.7 | 1,132 |
| 0x2c9d98ff...b6ac57 | 476 | 0 | 0.0% | 3,267.4 | 1,881,790 |
| 0x40173a53...2fb23 | 1,927 | 0 | 0.0% | 5,192.8 | 9,819,713 |
| 0x40f3fcf1...c4e7e | 1,653 | 0 | 0.0% | 3,481.3 | 2,489,813 |
| 0x474ea661...938b | 2,021 | 0 | 0.0% | 4,309.7 | 1,375,933 |
| 0x4c34beb1...1dcce | 1,976 | 0 | 0.0% | 4,313.8 | 5,419,533 |
| 0x4f236528...1e0d3 | 1,889 | 0 | 0.0% | 4,844.1 | 8,225,080 |
| 0x51d2063d...2eaa8 | 1,876 | 0 | 0.0% | 4,961.3 | 6,133,939 |
| 0x55055087...baa5a | 1,917 | 0 | 0.0% | 5,004.3 | 3,653,275 |
| 0x9f162cab...4884d | 2,028 | 0 | 0.0% | 4,609.7 | 6,685,995 |

---

## Key Findings

1. **Arb contamination is highly concentrated.** All 96 arb trades (price > 0.80) come from a single trader: `0x63d4...fa2f1`, who has a 90.6% arb rate across 106 resolved trades.

2. **Overall cohort arb rate is negligible at 0.4%**, driven entirely by one outlier. The remaining LEGENDARY traders show 0% arb in their geo/elections resolved trade history.

3. **The flagged trader is geo_elo LEGENDARY (3,503.7) but very low PNL ($1,132)** — consistent with an arbitrageur collecting near-certain resolution payments rather than a genuine directional predictor.

4. **Below-0.10 contamination is essentially zero** (3 trades, 0.01%) — all arb activity is on the high-price (>0.80) side.

---

## Phase 1 Conclusion

The LEGENDARY geo_elo cohort is **99.6% clean** by the 0.10–0.80 price filter. Applying `AND price BETWEEN 0.10 AND 0.80` to STR-003 trade selection will:
- Eliminate 96 arb trades (all from one trader)
- Retain 22,751 genuine directional trades
- Remove 0.4% of the dataset

**Recommendation for Phase 2:** Apply the price-range filter. Optionally flag or exclude `0x63d4...fa2f1` as a structural outlier in LEGENDARY analyses given its near-pure arbitrage profile.
