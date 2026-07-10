# Polymarket CLOB API Changes: Rate Limits Raised, Cancel Max 1000 Orders, Builder Code Header
## Source
https://docs.polymarket.com/changelog
## Domain
docs.polymarket.com
## Summary
POST /order and DELETE /order rate limits raised to 120000 per 10 minutes (200/s sustained). Cancel requests now accept up to 1000 order IDs per call. POST /deposit and POST /withdraw accept a new X-Builder-Code header for attribution; omitting it returns a warning but still succeeds. Relayer POST /submit now returns immediately without transactionHash.
## Action
Update brain/integration-contract.md to reflect new rate limits and cancel-order max. No blocking issue — changes are backward-compatible except the transactionHash removal from submit response.
## Verified
Yes — fetched via Claude CLI web search
