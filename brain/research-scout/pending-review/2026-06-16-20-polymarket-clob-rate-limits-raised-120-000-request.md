# Polymarket CLOB rate limits raised: 120,000 requests / 10 min on order endpoints
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
Rate limits on CLOB trading endpoints were raised significantly: POST/DELETE /order now allows 120,000 requests per 10 minutes (200/s sustained); POST/DELETE /orders allows 2,000 per 10s burst (200/s). Max order IDs per cancel request raised to 1,000. Builder leaderboard and volume endpoints now return a builderCode string per entry.
## Action
No immediate action. File in integration-contract.md for Phase 7 CLOB execution layer build — higher rate limits reduce throttling risk at scale.
## Verified
Yes — fetched via Claude CLI web search
