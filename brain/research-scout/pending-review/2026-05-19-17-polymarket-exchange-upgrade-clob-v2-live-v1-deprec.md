# Polymarket Exchange Upgrade — CLOB V2 Live, V1 Deprecated, pUSD Migration
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
CLOB V2 went live April 28 2026; legacy V1 SDKs and V1-signed orders are no longer supported on production and resting orders must be re-created with V2 signing. Polymarket is migrating collateral from USDC.e to Polymarket USD (pUSD), a standard ERC-20 on Polygon backed 1:1 by USDC. GET /markets/keyset max limit is now 100; POST /submit no longer returns transactionHash.
## Action
Audit any direct CLOB API integration for V1 references; update signing to V2; monitor pUSD migration impact on position and collateral tracking in first-repo.
## Verified
Yes — fetched via Claude CLI web search
