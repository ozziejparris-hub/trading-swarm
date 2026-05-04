# DeepSeek V4 Local Inference Path — Q2 GGUF May Fit UM890 Pro

## Source
https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro
https://api-docs.deepseek.com/news/news260424
HN: DeepClaude (agent loop with V4 Pro) — 408 points, May 3 2026

## Domain
Domain 3 — Model Capabilities

## Prior History (read before acting)
V4 was escalated in cycle 1 (scout-20260427). Sovereignty decision made 2026-05-02:
"Remain on claude-sonnet-4-6. Chinese-hosted API not acceptable. Revisit if open-weights
non-Chinese hosted version released." (signals.json, completed entry)
This finding addresses ONLY the local inference path — not the API. These are separate questions.

## What It Is
DeepSeek V4-Flash (284B total / 13B active MoE, MIT license) is available as GGUF quantizations
on HuggingFace and is Ollama-compatible. At Q2 quantization, V4-Flash requires ≈71GB RAM —
potentially fitting in UM890 Pro's 96GB DDR5 alongside the two existing Ollama models.
Previous dismissal estimated 142GB (Q4). Q2 halves that estimate.

## Why It Matters to This System
The sovereignty decision blocked the Chinese-hosted API. Local inference via downloaded weights
is different: data never leaves the server, and HuggingFace is US-hosted. The "revisit if
open-weights non-Chinese hosted" condition from the May 2 decision has been met.

If V4-Flash runs locally: Tier 3 tasks move to zero marginal cost (same as Tier 1/2 today).
At ~15 tok/s Vulkan eval (similar to Gemma E4B benchmark), latency would be acceptable for
non-realtime quant-research and backtest tasks. This changes the economics of Phase 3+ substantially.

V4-Pro at $1.74/$3.48 per MTok via API (5x cheaper output than Sonnet) remains sovereignty-blocked.
Do not re-evaluate the API path — that decision stands.

DeepClaude (github.com/aattaran/deepclaude, 408 HN points) confirms V4 Pro works in Claude Code
agent loop style via Anthropic API compatibility — validating integration patterns if local succeeds.

## What to Do With It
Discuss with Oscar before proceeding — specific question: is local inference via downloaded
MIT-licensed weights acceptable given DeepSeek's Chinese origin?

If yes: check RAM headroom → attempt V4-Flash Q2 GGUF pull via Ollama →
benchmark 3 Tier 3 tasks → decide on routing.

## Effort to Implement
Low (< 1 hour to attempt pull and RAM check) / Medium (1 day for full benchmark)

## Urgency
This week — local inference path is new information not present in cycle 1 decision

## Raw Notes
V4-Flash: 284B total / 13B active MoE, MIT license
Q2 GGUF RAM estimate: 284B × 2 bits / 8 = 71GB minimum
UM890 Pro: 96GB DDR5 total; existing Gemma E2B (7.2GB) + E4B (9.6GB) loaded = ~17GB
Remaining headroom: 79GB — enough for V4-Flash Q2 if expert offloading works
Caution: MoE expert loading behaviour in Ollama may require more RAM than theoretical minimum
Sovereignty precedent: MiniMax M2.7 open weights noted as clearing sovereignty blocker (model-routing.md)
API pricing for reference: V4-Flash $0.14/$0.28 per MTok; V4-Pro $1.74/$3.48 (API blocked)
Anthropic API compatible — if local inference validated, zero integration code change needed
