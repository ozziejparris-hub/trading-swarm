# Polymarket Exchange Upgrade April 28 2026 — V2 CLOB, pUSD collateral, mandatory SDK migration
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket completed a coordinated exchange upgrade on April 28 2026: new smart contracts, rewritten CLOB backend, and pUSD (ERC-20, 1:1 USDC-backed) replacing USDC.e as collateral. V1 SDK fully deprecated — V2 migration mandatory. POST /submit now returns immediately with {transactionID, state} only (transactionHash removed); cancel batch limit raised to 1000 order IDs per request.
## Action
Phase 7 V2 CLOB execution layer must target post-April-28 contracts and pUSD; order submission logic must handle stateless submit response (no transactionHash field).
## Verified
Yes — fetched via Claude CLI web search
