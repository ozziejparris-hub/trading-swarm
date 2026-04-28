# The Anatomy of a Decentralised Prediction Market — Polymarket Microstructure

## Source
https://arxiv.org/abs/2604.24366
arXiv:2604.24366 — "The Anatomy of a Decentralized Prediction Market" (Philipp D. Dubach)

## Domain
Prediction Market Intelligence + Quantitative Methods

## What It Is
Empirical study of Polymarket's order book using 30 billion order-book events captured over 52 days from the public WebSocket feed across 600 pre-registered markets, joined to on-chain trade records. Establishes eight stylised facts about Polymarket microstructure: spread premiums on longshots, uniform-geometric depth distribution, diverse maker wallets with concentrated tail activity, category-level spread variation, and predictable depth decay approaching resolution.

## Why It Matters to This System
**Critical data pipeline finding:** Trade direction inferred from Polymarket's public order-book feed agrees with on-chain OrderFilled ground truth only ~59% of the time — barely above random chance (50%). This means any signal-agent logic that infers trade direction from the order-book WebSocket feed is getting the direction wrong 41% of the time. The on-chain OrderFilled event stream is required for accurate direction labelling.

**Three additional implications:**
1. **Spread structure on longshots:** Longshot contracts have premium spreads — directly affects Kelly sizing for low-probability markets. Costs are higher than mid-market prices suggest.
2. **Depth decay near resolution:** Order book depth decays predictably as resolution approaches — relevant to timing exit signals and liquidity risk modelling.
3. **Wash trading is low:** Median 1% self-counterparty share — meaningfully lower than unregulated crypto. Polymarket order flow is more legitimate than feared; this does not require a heavy wash-trade filter in signal design.

## What to Do With It
"New research direction: add RQ-MICRO-1 to research-directions.md — validate that signal-agent uses on-chain OrderFilled events (not order-book feed) for all trade direction inference. If currently using order-book feed, file bug with market-builder-agent to switch to on-chain data source before Phase 4."

## Effort to Implement
Low (< 1 hour to check current signal-agent data source; Medium (1 day) to switch data source if wrong)

## Urgency
This week

## Raw Notes
- 52-day capture period, 600 markets, stratified panel design
- Tick-level order-book combined with authoritative blockchain data — methodology is sound
- Category variation in spreads: meaningful difference between politics, crypto, sports markets
- 50ms median data ingestion latency with extended tails — relevant for any real-time signal work
- Eight stylised facts are a useful baseline for quant-research-agent when designing limit-order execution in Phase 6
- Wash trading stat (1%) validates using Polymarket data without aggressive self-trade filtering
