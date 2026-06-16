# Polymarket Exchange Upgrade April 28 2026: pUSD Migration + SDK v2 Required
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket migrated collateral from USDC.e to pUSD (ERC-20 on Polygon, 1:1 USDC backed) on April 28 2026. All existing order books were cleared during maintenance and v1 SDK clients no longer work — v2 endpoints required for all CLOB interactions.
## Action
Verify any Phase 7 CLOB execution layer design targets v2 endpoints and pUSD. Update integration-contract.md if agent interfaces or DB schemas assume USDC.e as collateral token.
## Verified
Yes — fetched via Claude CLI web search
