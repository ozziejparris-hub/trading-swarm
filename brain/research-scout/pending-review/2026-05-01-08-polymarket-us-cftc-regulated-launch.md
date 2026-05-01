# Polymarket US Launches as CFTC-Regulated Platform — Structural Market Change

## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
https://www.quantvps.com/blog/polymarket-us-api-available
https://www.bitget.com/news/detail/12560605388635

## Domain
Prediction Market Intelligence

## What It Is
Alongside the April 28 V2 infrastructure upgrade (already covered in cycle 1), Polymarket launched a US-specific platform regulated by the CFTC, making prediction market trading legally available to US customers for the first time. The US Retail API provides 23 REST endpoints and 2 WebSocket endpoints across Markets, Orders, Events, Portfolio, and Account operations. Polymarket added a $1 million liquidity incentive program to bootstrap the new market.

## Why It Matters to This System
The cycle 1 finding covered the V2 technical breaking changes. This is a distinct structural event with different implications:

**1. Liquidity shift:** US participants entering a previously US-excluded market will materially increase order book depth on high-profile political and economic markets. More liquidity = tighter spreads = better fill quality for Phase 6 limit orders. The Kelly sizing math changes if spread costs drop significantly.

**2. Participant pool change:** The new US user base will likely include a higher proportion of sharp, well-resourced bettors (hedge funds, DC insiders, finance professionals) who were previously excluded. This could reduce exploitable mispricings in US political markets — directly relevant to market selection strategy.

**3. AI agent competitive pressure:** CFTC regulation creates a legal path for institutional-grade automated trading in the US. Expect professional quant shops to enter Polymarket US. The window for non-institutional agents to exploit market inefficiencies before institutional capital arrives may be narrowing.

**4. Market data richness:** US Retail API adds WebSocket endpoints — real-time event streams that our current read-only Data API polling doesn't provide. Phase 3+ could upgrade to WebSocket-based signal detection without the latency of polling intervals.

## What to Do With It
Discuss with Oscar before proceeding — two separate questions:
1. **Geographic access:** Is Oscar trading from a jurisdiction that now qualifies for Polymarket US? If so, Phase 6 live trading may need to migrate to the CFTC-regulated platform.
2. **Market selection filter:** Flag US political markets (elections, policy, congressional) for manual review over next 30 days — assess whether increased US participation is improving or worsening the signal quality edge.

Also: note in `brain/strategy-notes/research-directions.md` that the WebSocket API now exists as a future upgrade path for signal-agent's market monitoring latency.

## Effort to Implement
Low (< 1 hour) to annotate research-directions.md. Medium (1 day) if Oscar decides the jurisdiction question requires legal research.

## Urgency
This month — no immediate action needed, but Phase 6 planning should account for the new regulatory structure before finalising the trading setup.

## Raw Notes
- HeartBeats API (launched January 2026) added for professional market makers — confirms institutional interest predates US launch
- Post-only orders available since January 2026 — confirms Polymarket is building for sophisticated traders
- $1M liquidity program: likely temporary incentive to attract early US participants
- CFTC regulation: prediction markets are classified as derivatives contracts under CFTC jurisdiction
- Polymarket US vs Polymarket (offshore): separate platforms with different collateral (pUSD for V2 offshore, separate settlement for US)
- WebSocket endpoints: real-time order book updates and trade feeds — far lower latency than polling Data API
- Kimi K2.6 and DeepSeek V4 APIs are both cheaper than Haiku for research — but unrelated to this finding
