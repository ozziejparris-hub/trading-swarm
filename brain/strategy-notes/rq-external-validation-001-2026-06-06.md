# RQ-EXT-001 — External Dataset Validation of Pool C and STR-003 Assumptions
**Date:** 2026-06-06
**Status:** PRE-REGISTERED — do not implement changes until Peru signals resolve
**Source data:** vgregoire/polymarket-users (HuggingFace, CC-BY 4.0)
  Located: /home/parison/projects/first-repo/data/external/

## Key Findings from Cross-Reference (2026-06-06)

### Finding 1 — geo_directionality_score is a poor LP filter
Correlation between geo_directionality_score and frac_both_sides (external): -0.135
Pool C traders with geo_directionality_score >= 0.7: mean frac_both_sides = 0.510
Conclusion: Our directionality filter is nearly ineffective at excluding LP traders.

### Finding 2 — 0xecaa8806 is primarily a market maker
frac_maker: 0.763 | frac_both_sides: 0.740 | n_maker_trades: 27,736 / 36,356 total
Year-by-year geo/elections directionality: 2024=0.535, 2025=0.501, 2026=0.630
pnl_taker_total: $224,925 (positive — taker trades ARE profitable)
pnl_maker_total: $198,384 (also positive — significant LP income)
Conclusion: Our primary STR-003 signal generator is a sophisticated market maker with modest directional edge, not a pure conviction trader as assumed.

### Finding 3 — P&L discrepancy explained
Our realized_pnl for 0xecaa8806: $13,171 | External pnl_resolved_total: $378,057
Gap explained by: external dataset covers from 2022-11-21; our DB starts from 2024-01-05.
Missing 13+ months of trading history. P&L formula is correct; data completeness is the issue.

### Finding 4 — High-value missing traders are inactive
Top 20 politics P&L traders not in our DB: all last traded Oct-Nov 2024 (2024 US election).
Pre-date our monitoring system by 12+ months. Not recoverable without full historical backfill.

### Finding 5 — frac_both_sides methodology concern
External mean frac_both_sides for Pool C = 0.513
This means >50% of Pool C traders hold both YES and NO simultaneously on average.
However: the external dataset covers V1 exchange only (until April 2026).
Post-V2 behaviour may differ. Cannot assume V1 patterns apply to 2026 signals.

## Research Questions Pre-Registered

RQ-EXT-001a: Does Pool C consensus accuracy remain above 60% when filtered to traders with pnl_taker_politics > $1,000 (pure directional P&L, excluding LP income)?

RQ-EXT-001b: Does geo_elo accuracy improve or degrade when Pool C is filtered by frac_both_sides < 0.3 (low LP contamination)?

RQ-EXT-001c: What is the correlation between geo_elo and pnl_taker_politics in the external dataset? If geo_elo is capturing taker skill, correlation should be positive.

## Key Decision Gate
Do NOT change Pool C definition, geo_directionality_score threshold, or STR-003 criteria until:
1. Peru signals (STR003-005, STR003-006) resolve June 7 and are scored June 8
2. RQ-EXT-001a/b/c are formally run and results reviewed
3. At minimum 20 additional geo markets resolve in 2026 for sample stability

## Data Availability
user_pnl_summary.parquet: /home/parison/projects/first-repo/data/external/ (495MB)
user_features.parquet: /home/parison/projects/first-repo/data/external/ (768MB)
Coverage: Nov 2022 - Mar 2026 (V1 exchange only)
Licence: CC-BY 4.0
