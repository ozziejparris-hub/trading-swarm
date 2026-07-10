# Polymarket US API: portfolio positions endpoint now paginated, Historical Positions API added, liquidity incentives cut
## Source
https://docs.polymarket.us/changelog
## Domain
docs.polymarket.us
## Summary
As of July 1-2 2026, GET /v1/portfolio/positions now returns max 100 positions per page (previously unpaginated) — non-paginating callers silently get only the first page. A new Historical Positions API (as_of_time/as_of_date params) was added for point-in-time queries. Separately, liquidity rewards were cut (politics markets $500->$250/day per event).
## Action
Check whether trader-intelligence-agent or any position-fetching script calls /v1/portfolio/positions without handling pagination — could silently under-report positions for wallets with 100+ open positions.
## Verified
Yes — fetched via Claude CLI web search
