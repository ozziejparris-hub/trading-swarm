# Polymarket Exchange Upgrade April 28 2026: V2 SDK, pUSD collateral, rewritten CLOB backend
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket shipped new Exchange contracts, a rewritten CLOB backend, and a new collateral token (pUSD) on April 28 2026. All integrations were required to migrate to the V2 SDK before go-live; no backward compatibility after cutover. The POST /submit endpoint now returns immediately with {transactionID, state: 'STATE_NEW'} — transactionHash field removed.
## Action
Verify our CLOB execution layer (Phase 7 dependency) is built against V2 SDK and pUSD collateral. If any code references the old transactionHash field from /submit, update it.
## Verified
Yes — fetched via Claude CLI web search
