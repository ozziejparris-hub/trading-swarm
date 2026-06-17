# DeepSeek V4-Pro (1.6T params, MIT open weights) and V4-Flash (284B) released in preview April 24 2026
## Source
https://www.sitepoint.com/deepseek-v4-released-whats-new-in-the-latest-model-2026/
## Domain
sitepoint.com
## Summary
DeepSeek released V4-Pro (1.6T params) and V4-Flash (284B) on April 24 2026, both MIT-licensed open weights, callable via API and downloadable from HuggingFace. Both have 1M-token context and use Engram conditional memory technology. Currently in preview; no stable release date announced. Legacy deepseek-chat and deepseek-reasoner API aliases retire July 24 2026.
## Action
Watch-list trigger: V4-Pro at 1.6T params likely too large for UM890 Pro (96GB DDR5). V4-Flash at 284B warrants a GGUF quant size check — if a Q2_K_XL fits within available headroom, benchmark against Haiku 4.5 on Tier 2.5 tasks. Oscar decides on routing update per existing MiniMax M2.7 decision process.
## Verified
Yes — fetched via Claude CLI web search
