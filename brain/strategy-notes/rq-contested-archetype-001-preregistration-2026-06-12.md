# RQ-CONTESTED-ARCHETYPE-001 Pre-registration
**Filed:** 2026-06-12
**Run date:** 2026-07-01 (Wave 2 of July research cycle)
**Filed by:** Oscar (strategic roadmap session, Fable analysis)

## Hypothesis
geo_elo LEGENDARY accuracy on contested markets (0.35–0.65 price range), filtered to
GENUINE_FORECASTER and DOMAIN_SPECIALIST archetypes only (excluding YIELD_HARVESTERs
and VOLUME_SPECIALISTs), is significantly higher than the unfiltered LEGENDARY
accuracy figure.

## Motivation
The current geo_elo LEGENDARY accuracy figures (67–78%) aggregate ALL geo trades
including near-certainty entries from YIELD_HARVESTERs. The honest question for
STR-003's premise is: what is the accuracy of genuinely directional, skilled traders
on contested markets where there is real uncertainty? This number does not currently
exist and is the single most informative number the system could produce for
validating STR-003's core thesis.

Identified by Fable strategic analysis 2026-06-11 as a must-run RQ for July 1.

## Methodology
```sql
-- Contested markets only (price between 0.35 and 0.65 at trade time)
-- Archetype filter: GENUINE_FORECASTER + DOMAIN_SPECIALIST only
-- Pool C traders only (geo_accuracy_pool = 1)
-- Post April 28 2026 data only (structural break date)
-- Minimum 10 geo resolved trades per trader

SELECT
    archetype,
    COUNT(*) as n_trades,
    COUNT(DISTINCT trader_address) as n_traders,
    AVG(CASE WHEN trade_result = 'won' THEN 1.0 ELSE 0.0 END) as accuracy,
    AVG(difficulty_score) as avg_difficulty
FROM trades t
JOIN markets m ON m.market_id = t.market_id
JOIN traders tr ON tr.address = t.trader_address
LEFT JOIN (SELECT address, archetype FROM trader_profiles) tp ON tp.address = tr.address
WHERE tr.geo_accuracy_pool = 1
    AND tr.research_excluded = 0
    AND tr.bot_type IS NULL
    AND tr.geo_resolved_trades_count >= 10
    AND tp.archetype IN ('GENUINE_FORECASTER', 'DOMAIN_SPECIALIST')
    AND m.resolved = 1
    AND m.category IN ('Geopolitics', 'Elections')
    AND t.trade_result IN ('won', 'lost')
    AND t.timestamp > '2026-04-28'
    -- Difficulty/contested filter: use difficulty_score or approximate via market price
    AND (m.difficulty_score >= 0.35 OR m.difficulty_score IS NULL)
GROUP BY archetype
ORDER BY accuracy DESC
```

Note: trader_profiles is currently in brain/trader-profiles/_index.json, not a DB table.
Quant-research-agent will need to join via Python rather than pure SQL.

## Pre-registered outcome thresholds
- **PASS:** Archetype-filtered LEGENDARY accuracy >= 70% on contested markets, n >= 30
- **FAIL:** Accuracy < 55% on adequate sample — fundamentally challenges STR-003 premise
- **INCONCLUSIVE:** n < 30 — report and rerun August 1

## What this unlocks
- Direct validation of STR-003's core premise (not just correlation between ELO and accuracy)
- Informs archetype weighting in SCS (how much weight DOMAIN_SPECIALIST gets vs GENUINE_FORECASTER)
- Inputs to Phase 7 position sizing (calibration layer needs this number)

## Non-interference with existing registrations
Does not overlap with RQ-CONTESTED-001 (difficulty-weighted K factor — different question).
Does not overlap with GEO-ELO-001/003 (those are unfiltered pool accuracy questions).
