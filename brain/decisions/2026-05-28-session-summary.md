# Session Summary: Server Setup 14 — 2026-05-28

## What Was Built

### 1. contract_violation Signal Spam Fixed
- Orchestrator was firing every cycle on unhandled `contract_violation` signal type
- Added handler to `orchestrator/orchestrator.py` with 24-hour rate limiting
- State persists via `brain/contract_violation_state.json`
- Stale signals cleared from `brain/signals.json`

### 2. Log Cleanup — 449MB Freed
- Deleted 8 old ELO recalculation logs from April–May 2026
- `logs/` directory reduced from 608MB to 159MB

### 3. Resolution Sweep — Critical Bug Fixed
- Was using `markets.category` (sparsely populated, only 166 rows)
- Fixed to use `trades.market_category` subquery (correct source)
- Added majority filter: ≥ 3 geo trades AND ≥ 50% of all trades
- Result: sweep now finds 519 geopolitics markets (was 1)
- 60-day backfill run: 62 traders promoted to active monitoring pool
- These traders were in DB but excluded — now correctly flagged
- Default 7-day window unchanged — backfill was a one-time 60-day run

## Key Decisions

- **STR-003 concurrent markets fix deprioritised** — all qualified LEGENDARY traders have 0 geo trades in the last 30 days (dormant Haley specialists). Fixing the criterion won't help until new 2026 geo traders emerge.
- Resolution sweep fix is higher value than STR-003 criterion change.
- `markets.category` is unreliable — always use `trades.market_category`.

## Next Session Priorities

1. Calculate geo_elo for the 62 newly promoted traders as their markets resolve
2. Test Tier 2.5 → Tier 3 handoff on a real production research task
3. STR-003 concurrent markets criterion (lower priority — dormant pool)
4. Monitor whether promoted traders accumulate enough geo trades for geo_elo
5. July 1 — RQ1.1 rerun with extended Period 2 to September 1
