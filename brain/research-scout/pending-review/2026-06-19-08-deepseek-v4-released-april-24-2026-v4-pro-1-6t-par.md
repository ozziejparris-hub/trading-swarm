# DeepSeek V4 released April 24 2026 — V4-Pro (1.6T params) and V4-Flash (284B), both MIT open-weight
## Source
https://deepseek.ai/deepseek-v4
## Domain
deepseek.ai
## Summary
DeepSeek shipped V4-Pro (1.6T total / 49B active) and V4-Flash (284B total / 13B active) on April 24 2026 under MIT license. Both expose 1M-token context and 384K max output. V4-Pro claims 27% of V3.2 single-token FLOPs and 10% of its KV cache at 1M context. Framed as a stable preview; production-stable version expected later in 2026.
## Action
V4-Flash at 284B total / 13B active may fit UM890 Pro (96GB DDR5) quantized; benchmark against Haiku 4.5 on Tier 2.5 tasks (integration-test, research-scout, code-hygiene) before routing update.
## Verified
Yes — fetched via Claude CLI web search
