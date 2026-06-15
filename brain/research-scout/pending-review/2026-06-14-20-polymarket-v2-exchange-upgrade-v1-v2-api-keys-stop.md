# Polymarket V2 Exchange Upgrade: v1/v2 API Keys Stopped Working June 1 2026; Full V1 Shutdown June 30
## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
## Domain
help.polymarket.com
## Summary
Polymarket launched a full exchange upgrade on April 28 2026 with new smart contracts, rewritten CLOB order book, and new collateral token. Old v1/v2 API keys stopped working June 1 2026 — already past as of today (June 14). All integrations must use v3 keys and updated SDK before June 30 2026 when V1 infrastructure permanently shuts down with no backward compatibility.
## Action
URGENT: Verify all Polymarket monitoring agents and bots are on v3 API keys — v1/v2 keys have been broken since June 1. If any agent is using legacy keys it has been failing silently for 13 days.
## Verified
Yes — fetched via Claude CLI web search
