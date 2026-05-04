# Kimi K2.6 — New Leading Open-Weight Model from Moonshot AI

## Source
https://huggingface.co/moonshotai/Kimi-K2.6
https://artificialanalysis.ai/articles/kimi-k2-6-the-new-leading-open-weights-model

## Domain
Domain 3 — Model Capabilities

## What It Is
Moonshot AI (Beijing) released Kimi K2.6 on April 20 2026 under MIT license (with a revenue threshold clause above $20M/month revenue or 100M MAU). It is a 1T-parameter MoE model with 32B active per token, 256K context, native multimodal (text/image/video), INT4 native quantization, and ships with day-0 support on OpenRouter, Cloudflare Workers AI, vLLM, and SGLang. Benchmarks: SWE-bench Pro 58.6%, HLE-tools 54.0%, AI Intelligence Index 54 (vs Claude 57, GPT-5.5 at 60). Unsloth v0.1.37-beta (April 23) reports it as runnable.

## Why It Matters to This System
K2.6 is the current open-weight frontier model, sitting above DeepSeek V3.2 and approaching Opus 4.7 on coding benchmarks. The DeepSeek V4 sovereignty decision (May 2) established that Chinese-hosted APIs are blocked. K2.6 has the same nationality (Chinese lab) but is open-weight and hosted by US providers including OpenRouter and Cloudflare Workers AI — this is the same distinction that cleared MiniMax M2.7 (open weights + US-hosted = sovereignty cleared). If K2.6 via OpenRouter passes benchmark quality at competitive pricing, it becomes a Tier 3 alternative at lower cost than Sonnet 4.6. Critical question for Oscar: does OpenRouter-hosted Kimi K2.6 clear the sovereignty bar, or is the Chinese lab origin itself the blocker regardless of hosting?

## What to Do With It
Discuss with Oscar before proceeding — the sovereignty question (Chinese lab vs Chinese hosting) needs a clear ruling before any evaluation benchmark is run.

If sovereignty cleared: run 3-task benchmark against Sonnet 4.6 on quant-research-style tasks. Compare output quality, format adherence, and API pricing on OpenRouter.

## Effort to Implement
Low to Medium — benchmark itself is 1 day once sovereignty question resolved

## Urgency
This month

## Raw Notes
- Model: 1T total / 32B active, MoE with 384 experts (8 routed + 1 shared), MLA attention
- Context: 256,144 tokens
- License: MIT with revenue/MAU clause (effectively MIT at our scale)
- Local inference on 96GB UM890 Pro: NOT VIABLE. Full INT4 weight storage ~500GB
  (1T params × 0.5 bytes/param). KTransformers can offload experts but would be slow.
  Unsloth "runnable" note likely refers to hardware with 4×80GB GPUs or equivalent.
- Cloud API options: OpenRouter, Cloudflare Workers AI, Baseten — all US-hosted
- Pricing: not publicly disclosed at time of writing — check OpenRouter for current rates
- Agentic claims: "4,000+ tool calls, 12+ hour continuous runs, 300 parallel sub-agents"
  — relevant for orchestration patterns but unverified
- Latent Space (AINews) covered April 20 2026 release, highlighted as "world's leading open model"
- DeepSeek sovereignty ruling precedent: Chinese-hosted API blocked; open-weight may be different
- Successor context: Kimi K2.5 → K2.6 is a capability refresh, same architecture
