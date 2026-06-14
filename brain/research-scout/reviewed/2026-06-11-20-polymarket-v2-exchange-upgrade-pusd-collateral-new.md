# Polymarket V2 Exchange Upgrade — pUSD Collateral, New CLOB Backend (April 28, 2026)
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
polymarket
## Summary
Polymarket completed its V2 exchange upgrade on April 28, 2026, migrating from USDC.e to pUSD (ERC-20, backed 1:1 by USDC on Polygon) and rewriting the CLOB backend. No backward compatibility with pre-V2 integrations — all SDKs and integrations required migration. Rate limits also raised: CLOB POST /order now 200/s burst.
## Action
Verify integration-contract.md and first-repo DB connector are using pUSD (not USDC.e) and V2 CLOB endpoints; confirm pre-resolution observer scripts have not broken post-cutover.
## Verified
Yes — fetched via Claude CLI web search
