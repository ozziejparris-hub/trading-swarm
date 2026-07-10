# Polymarket Exchange Upgrade V2: New CLOB Backend, pUSD Collateral, Mandatory SDK Migration
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket shipped a coordinated exchange upgrade on April 28 2026 with new Exchange contracts, a rewritten CLOB backend, and a new collateral token (pUSD). All integrations must migrate to the V2 SDK — there is no backward compatibility after go-live. Any agent or script using the old CLOB API is now broken.
## Action
URGENT: Verify all trading-swarm CLOB integration code has migrated to V2 SDK. Check brain/integration-contract.md against current V2 spec. This directly affects Phase 6 execution layer build.
## Verified
Yes — fetched via Claude CLI web search
