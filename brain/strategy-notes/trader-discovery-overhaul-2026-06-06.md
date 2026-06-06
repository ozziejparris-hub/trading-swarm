# Trader Discovery Overhaul — 2026-06-06
**Status:** Layer 1 + 2 complete. Layer 3 pending.

## Problem
Current discovery mechanism (discover_leaderboard_traders.py) uses /trades endpoint with 500-trade cap on top-50 markets. Misses:
- Traders in resolved/cold markets (API returns empty)
- Patient traders with few large bets (diluted in busy markets)
- Non-leaderboard traders with high directional skill

Result: 99 genuine directional politics traders identified in external dataset — only 6 in our DB.

## Layer 1 — Immediate (complete 2026-06-06)
Added 3 Tier 1 traders via add_watched_trader.py:
- 0x040f9c05... (Nocthyra) — $208K taker politics P&L, active June 2026
- 0x90fe66a1... (Calythius) — $156K taker politics P&L, active March 2026
- 0xb464061b... (anonymous) — $158K taker politics P&L, active March 2026

## Layer 2 — Parquet Seed (complete 2026-06-06)
195 directional politics traders batch-inserted from vgregoire/polymarket-users.
discovery_source = 'external_seed'
Filters: traded_politics=1, frac_politics>0.5, frac_both_sides<0.25, frac_maker<0.3, n_markets>=15, round_trip_rate<0.15, last_trade>=2025-06-01, pnl_taker_politics>$10K, counterparty_hhi<0.5

## Layer 3 — /holders Endpoint Sweep (pending — next session)
Replace /trades with /holders in resolution-triggered discovery.
The /holders endpoint returns position holders by size, not trade recency.
Works on resolved/cold markets. Paginated. Catches patient traders invisible to /trades.

Implementation: When resolution_sweep.py marks a market resolved=1, call:
GET data-api.polymarket.com/holders?conditionId={condition_id}&limit=500&offset=0
For each wallet returned: run existing geo/trades/volume evaluation.
discovery_source = 'resolution_sweep'

## Integration Contract Impact
New discovery_source values: 'external_seed', 'resolution_sweep', 'holders_sweep'
Section 9 updated in v2.4 to reflect new pool composition.
