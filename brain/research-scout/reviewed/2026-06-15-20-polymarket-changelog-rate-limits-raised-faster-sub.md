# Polymarket Changelog: Rate Limits Raised, Faster /submit Response, New /withdraw Endpoint
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
Recent changelog: burst/sustained rate limits raised on CLOB POST /order and DELETE /order; POST /submit now returns immediately with transactionID only (transactionHash removed); new /withdraw endpoint for bridging to EVM chains, Solana, and Bitcoin.
## Action
Remove any code relying on transactionHash in /submit response. Note raised rate limits when designing CLOB execution layer order pacing.
## Verified
Yes — fetched via Claude CLI web search
