# Polymarket v3 API migration — old v1/v2 API keys dead as of June 1, 2026; full V2 migration deadline June 30, 2026
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
Old v1/v2 API keys stopped working June 1, 2026, breaking existing bot integrations; v3 keys with new authentication are required. New cursor-based pagination endpoints (GET /markets/keyset, GET /events/keyset) replace offset-based GET /markets and GET /events. Full V2 migration (wallet reconnect, position migration, pUSD collateral, rewritten CLOB backend) is required by June 30, 2026.
## Action
URGENT: audit polymarket observer/monitoring services and any first-repo DB ingestion for v1/v2 key usage and offset-based pagination before the June 30 deadline; update integration-contract.md. Overlaps with pending-review item 2026-06-11 polymarket-v2-exchange-upgrade — escalate rather than re-file.
## Verified
Yes — fetched via Claude CLI web search
