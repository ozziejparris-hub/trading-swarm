# RQ-ILS-001 — Information Leakage Score Market Filter (Pre-Registration)
**Pre-registered:** 2026-06-06
**Status:** FUTURE — requires implementation
**Source:** arXiv 2605.00493 (ForesightFlow)

## Hypothesis
Markets with high Information Leakage Score (ILS) — where early order flow strongly predicts resolution — are better candidates for STR-003 signals than low-ILS markets. Filtering or weighting signals by market-level information quality could improve STR-003 accuracy.

## Why This Matters
Current STR-003 fires on any geo/elections market where a LEGENDARY trader takes a position. ILS would let us prioritise markets where informed trading is more detectable.

## Implementation Path
1. Implement ILS calculation: for each market, measure correlation between early order flow direction and resolution outcome
2. Add ILS score to markets table
3. Test: does geo_elo LEGENDARY accuracy improve when restricted to high-ILS markets?

## Defer Until
July 1 2026 — after RQ-CONTESTED-001 validation and formula changes settled.
