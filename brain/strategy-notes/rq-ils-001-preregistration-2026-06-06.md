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

## ForesightFlow paper review (2026-06-16)
arXiv 2605.00493 (Nechepurenko, May 2026) — the ILS framework paper.
Key: ILS quantifies per-market front-loading of private information on Polymarket.
High ILS = informed trading visibly precedes public resolution events on that market.

Connection to STR-002 redesign:
- ILS as a MARKET SELECTION FILTER on STR-002 signal registration
- Hypothesis: STR-002 signals on high-ILS markets should show positive edge;
  signals on low-ILS markets are noise (yield-harvesting, not informed trading)
- This adds a third gate alongside trader-quality (proven) and market-uncertainty (contested):
  PROVEN TRADER + CONTESTED MARKET + HIGH ILS = strongest possible STR-002 signal

Pre-registration task (before July 1):
1. Understand ILS calculation — can we compute it from our trades table?
   (Need: pre-resolution trade sequence, timing relative to resolution, position size)
2. Pre-register RQ formally: "ILS-filtered STR-002 signals show positive edge vs unfiltered"
3. Wave 1 or Wave 2 depending on data availability
