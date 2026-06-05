# RQ-CONTESTED-001 — Contested Market Accuracy Pre-Registration
**Pre-registered:** 2026-06-05
**Approved by:** Oscar
**Status:** PRE-REGISTERED

## Hypothesis
ELO tier consensus accuracy on genuinely contested markets (average entry price 0.35-0.65) provides meaningful signal above the market price baseline. If confirmed, this justifies difficulty-weighted modifications to the comprehensive_elo formula.

## Motivation
On 2026-06-03, manual analysis showed:
- Market price baseline on 0.35-0.65 markets: 50.3% (n=1,255) — essentially random
- ELITE tier accuracy: 81.4% (n=274)
- LEGENDARY tier accuracy: 79.2% (n=288)  
- QUALIFIED tier accuracy: 69.6% (n=184)
However time-series decomposition revealed instability: 2025-H2 accuracy was 25% (n=20) vs 2026 accuracy 54.3% (n=1,235). Edge is NOT temporally stable in the historical data.

## Research Question
Do ELO tiers show statistically significant accuracy above market price baseline specifically on genuinely contested markets (0.35-0.65 price band), measured out-of-sample on 2026 markets only?

## Methodology (pre-specified, no post-hoc changes permitted)
1. Filter: resolved=1, winning_outcome IN (Yes,No), trade_gap_flag=0, category NOT IN (Sports,Crypto,Entertainment), resolution_date >= 2026-01-01
2. Difficulty filter: AVG(entry_price) BETWEEN 0.35 AND 0.65 per market
3. Minimum 3 traders per market from research pool (research_excluded=0, resolved_trades_count>=20, bot_type IS NULL)
4. Measure: directional accuracy of capital-weighted consensus vs market price
5. Tiers: LEGENDARY (comprehensive_elo>2175), ELITE (>1800), QUALIFIED (>1550)
6. Baseline: market price accuracy on same market set
7. Significance threshold: accuracy > 60% AND n >= 30 markets

## Pass Criteria
ALL of the following must hold:
- At least one tier achieves >= 60% accuracy on 2026 contested markets (n>=30)
- At least one tier beats market price baseline by >= 5pp
- Results consistent across Q1 2026 and Q2 2026 sub-periods (no single-quarter distortion)

## Fail Criteria (halt formula changes)
- No tier exceeds 55% on 2026 contested markets
- Market price baseline >= any ELO tier on contested markets
- n < 30 markets for all tiers (insufficient data — defer to Q3 2026)

## If Passed
Pre-register a specific comprehensive_elo formula modification:
- Difficulty-weighted K factor: K_adjusted = K * (1 - |price - 0.5| * 2)
  This gives K at price=0.5 (maximum weight) and K*0 at price=0 or 1
  Effectively: contested market wins/losses count full, easy market wins/losses count less
- Run full ELO recalculation with new formula
- Validate: does difficulty-weighted ELO improve contested market accuracy vs baseline?

## Data Requirements
- Minimum 30 resolved 2026 geo/elections markets at 0.35-0.65 price band with ELITE+ participation
- Currently: ~10 qualifying 2026 markets (as of 2026-06-03) — likely sufficient by Q3 2026
- Re-run date: 2026-07-01 (alongside RQ1.1 rerun)

## Notes
- comprehensive_elo formula bias confirmed: 2.3x accumulation advantage for easy-market specialists
- geo_elo uses correct probability-ELO formula (expected=price) — no difficulty weighting needed there
- This RQ applies ONLY to comprehensive_elo modification, not geo_elo
