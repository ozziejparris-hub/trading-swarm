# Polymarket US API Now Live — REST + WebSocket + Python SDK, No Geoblocking
## Source
https://www.quantvps.com/blog/polymarket-us-api-available
## Domain
quantvps.com
## Summary
Public US APIs and SDKs are live via the developer portal: 20+ REST endpoints, WebSocket feeds for live market and private updates, official Python SDKs. US users no longer geoblocked. Public endpoints allow 60 req/min; WebSocket has virtually no rate limit. Coincides with CFTC-regulated Polymarket US launch.
## Action
Confirm polymarket-observer service is using Python SDK (not raw HTTP) to benefit from maintained V2 compatibility. Review whether WebSocket feeds should replace any polling loops in data collection.
## Verified
Yes — fetched via Claude CLI web search
