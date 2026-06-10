# RQ-POOL-QUALITY-001 — LEGENDARY Pool Quality Filter
**Pre-registered:** 2026-06-10
**Status:** PENDING IMPLEMENTATION (July 1 2026)
**Author:** Oscar + Claude (Session #30)

## Hypothesis
Current LEGENDARY qualification (geo_elo_active >= 2175, geo_accuracy_pool = 1) admits
traders whose ELO is built on near-certainty position accumulation rather than genuine
forecasting skill. A minimum market diversity filter would remove these without affecting
genuine forecasters.

## Evidence from Session #30
- 0x44a1159b: 60 geo trades, effectively 1 market (Judy Shelton Fed chair NO @ 0.96-0.97)
  → research_excluded=1 applied immediately as data quality exclusion
- 0x9aa516ed, 0xd684df32, 0xe0bc6311: 65-169 trades, thin market diversity, near-1.0
  directionality — likely near-certainty traders
- Ceasefire cluster (8 traders): ELO built on single-theme volume
- 0xe7499538: yield harvester on China tail-risk, not directional forecaster

## Proposed Filter Criteria (to be validated)
LEGENDARY qualification requires ALL of:
1. geo_elo_active >= 2175 (existing)
2. geo_accuracy_pool = 1 (existing)
3. geo_resolved_trades_count >= 30 (raises bar from implicit ~10)
4. COUNT(DISTINCT market_id) >= 10 across resolved geo trades
5. No single market > 40% of total geo resolved trades (concentration cap)
6. At least 2 of 6 domains with >= 3 resolved trades (diversity requirement)

## What This Would Change
- Removes near-certainty accumulators from STR-003 signal generation
- Does NOT change geo_elo calculation (score preserved for all traders)
- Annotation-only until July 1 — do not apply retroactively to existing signals

## Rerun Date
July 1 2026 — alongside RQ-SECTOR-001, RQ-EXEC-001, RQ-LH-001

## Decision Gate
Implement if: filter removes >0 current LEGENDARY traders AND those traders have
<65% accuracy on contested markets (0.35-0.65 price band)
Do not implement if: filter would remove genuine forecasters with strong contested accuracy
