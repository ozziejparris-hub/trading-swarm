# Polymarket Exchange Upgrade: V2 SDK Mandatory, pUSD Collateral, New CLOB Backend
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket shipped a coordinated exchange upgrade on April 28 2026 (~1 hour downtime at 11:00 UTC). New Exchange contracts, rewritten CLOB backend, and new collateral token (pUSD) were deployed. All integrations must migrate to V2 SDK — no backward compatibility after go-live.
## Action
Verify brain/integration-contract.md reflects V2 SDK endpoints and pUSD collateral. Any agent querying the Polymarket CLOB must be using V2 SDK or calls will fail.
## Verified
Yes — fetched via Claude CLI web search
