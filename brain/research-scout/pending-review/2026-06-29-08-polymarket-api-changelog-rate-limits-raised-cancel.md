# Polymarket API Changelog: Rate Limits Raised, Cancel Batch Cap 1000, Builder Attribution Header
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
CLOB POST /order rate limit raised to 120,000/10 min (200/s sustained); DELETE /orders raised to 2,000/10s burst. Cancel requests now capped at 1,000 order IDs per call. New X-Builder-Code header accepted on POST /deposit and /withdraw; absent header returns a warning, malformed header returns 400.
## Action
Update integration-contract.md with new rate limits and cancel batch cap. Ensure any order management code splits cancellation batches at ≤1000.
## Verified
Yes — fetched via Claude CLI web search
