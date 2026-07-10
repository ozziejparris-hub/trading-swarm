# Polymarket Exchange Upgrade — V2 SDK Mandatory, New CLOB Rate Limits, pUSD Collateral
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
April 28 2026 upgrade: new Exchange contracts, rewritten CLOB backend, pUSD collateral token. POST /submit now returns immediately with {transactionID, state:STATE_NEW} and transactionHash removed. CLOB POST/DELETE /order rate limits raised to 200/s sustained; DELETE /orders now accepts up to 1000 order IDs per request. X-Builder-Code header (bytes32 hex) added to deposit/withdraw. No backward compatibility — all integrations must migrate to V2 SDK.
## Action
Phase 7 CLOB execution layer must target V2 SDK only. Audit orchestrator/task_templates/ for any hardcoded V1 endpoint assumptions. No action needed pre-Phase 7 but flag for execution layer design.
## Verified
Yes — fetched via Claude CLI web search
