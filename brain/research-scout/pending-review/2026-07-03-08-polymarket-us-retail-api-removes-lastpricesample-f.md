# Polymarket US Retail API removes lastPriceSample field (breaking change, July 2 2026)
## Source
https://docs.polymarket.us/changelog
## Domain
docs.polymarket.us
## Summary
As of July 2, 2026 (Retail API v0.0.62), Polymarket US removed lastPriceSample from the market-data WebSocket and REST endpoints (bbo, book). Integrations should switch to longQuote/shortQuote, which carry equivalent data.
## Action
Grep trading-swarm's Polymarket API integration code for lastPriceSample usage and migrate to longQuote/shortQuote if found.
## Verified
Yes — fetched via Claude CLI web search
