# Polymarket CLOB Rate Limits Raised to 120,000 requests/10 min (200/s sustained)
## Source
https://docs.polymarket.com/changelog
## Domain
polymarket
## Summary
POST /order and DELETE /order now allow 120,000 per 10 minutes (200/s sustained); POST /orders and DELETE /orders allow 2,000/10s burst. DELETE /orders batch ceiling raised to 1,000 order IDs per call.
## Action
Update rate-limit guard logic in Phase 7 execution layer; current limits are no longer the bottleneck for order throughput.
## Verified
Yes — fetched via Claude CLI web search
