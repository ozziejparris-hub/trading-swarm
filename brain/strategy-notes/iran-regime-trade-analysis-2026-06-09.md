# Iran Regime Fall June 30 — Trade Pattern Analysis
**Date:** 2026-06-09
**Market:** Will the Iranian regime fall by June 30?
**Resolution:** 2026-06-30

## Summary
7 LEGENDARY traders identified on this market. Detailed trade analysis reveals three distinct behaviour archetypes.

## Trader Profiles

### SirHarryOakes — Pure Conviction (geo_elo_active: 2,357)
- Built $11,103 NO position across 8 trades March–May 2026
- Entry range: 0.74–0.96 NO price
- Pattern: steady accumulation + reinforcement as market confirmed view
- Still holding — added $3,000 at 0.95-0.96 in May
- Assessment: Highest signal value. Genuine medium-term conviction.

### randomWalkingShrimp — Steady Accumulator (geo_elo_active: 2,485)
- Built ~$310 NO over 6 trades March 3-5
- Entry range: 0.59-0.64
- No selling — still holding
- Assessment: Clean directional conviction at earlier, cheaper prices.

### Giorgio2 — Switcher (geo_elo_active: 2,323)
- Jan 2: $0.50 YES at 0.10 (exploratory)
- Mar 16: $540 NO at 0.72 (switches to NO)
- Mar 23: Sells $190 NO (partial profit)
- Mar 28: $600 NO at 0.80 (re-enters)
- Assessment: Opportunistic. Switched sides as situation developed. Moderate signal value.

### N0stradumba55 — WRONG Side, Exited (geo_elo_active: 2,554)
- Mar 8-15: $330 YES at 0.30-0.33 (bet regime would fall)
- Mar 21: SOLD all YES at 0.25 — cut losses
- Assessment: ZERO signal value for current NO consensus. This trader bet YES and lost. Their exit does NOT mean they now agree with NO.

### Anonymous 0xec05c — News Trader (geo_elo_active: 2,551)
- Mar 1: Built $60 position in rapid small trades, then SOLD same day
- Mar 2: Re-entered $211, held briefly
- Mar 7: Sold everything at 0.67
- Assessment: Zero net position. Testing liquidity / reacting to news. No lasting conviction.

### CompulsiveGambler — Follower (geo_elo_active: 2,263)
- Apr 2: $356 NO at 0.89 — entered after market already moved
- Assessment: Low signal value — late entry at expensive price.

### The Spirit of Ukraine>UMA — Exited (geo_elo_active: 2,539)
- May 19: SOLD $13,583 NO at 0.95 — large redemption
- Assessment: Was long NO, collected profits. No current position.

## Key Finding
The "7 LEGENDARY traders NO" headline figure overstates consensus:
- Genuine open NO positions: SirHarryOakes, randomWalkingShrimp, Giorgio2 (~3 traders)
- Exited with profit: Spirit of Ukraine (was NO, now flat)
- Wrong side, exited: N0stradumba55 (was YES, lost money)
- News traded, no conviction: Anonymous 0xec05c
- Late follower at high price: CompulsiveGambler

## Implications for System
1. positions_scan.py should filter to CURRENT OPEN positions, not historical trades
2. Need a net_position calculation: sum(BUY shares) - sum(SELL shares) per trader per market
3. Exclude traders with net_position near zero from consensus count
