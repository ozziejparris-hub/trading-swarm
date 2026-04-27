# Research Query Standards
Last updated: 2026-04-26
Source: Data integrity audit findings

## Mandatory Filters for All Research Queries

Every query joining traders to trades to markets must include:

### Join Key
JOIN markets m ON m.market_id = t.market_id
-- Never use condition_id as join key — misses 12,584 trades

### Trader Filter  
WHERE tr.research_excluded = 0
-- Excludes: LP artifacts, thin-sample artifacts, 
-- wash trade suspects, bot suspects, <20 resolved trades,
-- ELO <= 300

### Timestamp Filter
AND t.timestamp <= datetime('now')
-- Excludes 37 future-dated trades (market expiry timestamps
-- ingested as trade timestamps)

### Resolution Filter
AND m.resolved = 1
AND m.winning_outcome NOT IN ('unknown', '')
AND m.winning_outcome IS NOT NULL
-- Excludes 497 markets with unknown resolution (4.5%)

## Clean Research Pool (as of 2026-04-26)
Total traders: 86,816
research_excluded = 0: 6,829
Legendary (ELO > 2175, not excluded): run query to confirm

## Known Data Issues
See reports/data_integrity_audit_20260426.md in first-repo

## ELO Point-in-Time Note
comprehensive_elo is a batch-recalculated retrospective score.
It cannot be used as a point-in-time metric for RQ1.1.
RQ1.1 requires ELO to be recomputed on filtered trade sets.
This is Fix 3 — not yet implemented.

## Gap Period Warning
Markets resolving April 7–18, 2026 have incomplete trade data
due to server migration (UM890 Pro setup). Near-zero trade
collection during this window: 1–6 trades/day vs 500+ normal.
These markets are flagged with trade_gap_flag=1 in the markets table.
Exclude from time-series analysis with:
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
