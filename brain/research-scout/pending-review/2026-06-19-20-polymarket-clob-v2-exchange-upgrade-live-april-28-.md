# Polymarket CLOB V2 Exchange Upgrade Live — April 28, 2026
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket shipped a coordinated CLOB V2 upgrade on April 28, 2026: new Exchange contracts, rewritten CLOB backend, and new pUSD collateral token (USDC-backed ERC-20 on Polygon). V1 SDK has no backward compatibility with production CLOB V2 — all integrations must migrate before the June 30, 2026 cutover. API rate limits increased (CLOB POST /order now 120k/10min).
## Action
URGENT: Verify all agent data-collection and order-submission scripts are on V2 SDK before June 30 cutover. Update integration-contract.md with new endpoint specs and pUSD collateral token details.
## Verified
Yes — fetched via Claude CLI web search
