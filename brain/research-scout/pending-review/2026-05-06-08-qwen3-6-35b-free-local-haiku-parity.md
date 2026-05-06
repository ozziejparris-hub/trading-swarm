# Qwen3.6-35B-A3B — Free Local Model Matching Haiku 4.5 on SWE-Bench

## Source
https://huggingface.co/Qwen/Qwen3.6-35B-A3B
Released: April 2026 (Alibaba Qwen team)

## Domain
Domain 3 — Model Capabilities

## What It Is
Qwen3.6-35B-A3B is a 35B-parameter open-weight MoE model (3B active per token) released April 2026 under an open license. It achieves 73.4% on SWE-bench Verified — matching Claude Haiku 4.5 (~73.3%) — with 280 quantized GGUF variants available on HuggingFace, including community Ollama support. Context window: 262K tokens native.

## Why It Matters to This System
Research-scout-agent and integration-test-agent are currently routed to Haiku 4.5 (Tier 2.5, $1/$5 per MTok) because they require Anthropic reliability over local models. Qwen3.6-35B-A3B at 73.4% SWE-bench parity with Haiku, running locally for free, could eliminate the API cost for these daily and weekly tasks entirely. At ~20GB for Q4 quantisation, it fits the UM890 Pro's 96GB DDR5 with headroom for concurrent Gemma processes. The 262K context window handles our full agent prompt injection (priorities.md + model-routing.md + agent template).

## What to Do With It
Queue for evaluation after MiniMax M2.7 benchmark completes (already in progress this week). Run the same 3 Tier 2.5 benchmark tasks (integration-test, research-scout, code-hygiene) against Haiku 4.5 baseline. Priority decision: if output format adherence ≥ Haiku and latency < 30s, route research-scout-agent and integration-test-agent to Qwen3.6-35B-A3B, saving ~$2-5/week in API calls.

## Effort to Implement
Medium (1 day) — GGUF pull, Ollama configuration, benchmark run, routing update

## Urgency
This month (after MiniMax M2.7 evaluation completes)

## Raw Notes
- Full benchmarks: SWE-bench Verified 73.4%, MMLU-Pro 85.2%, GPQA Diamond 86.0%, AIME26 92.7%
- Gemma4-26B-A4B comparison: Gemma scores only 17.4% SWE-bench vs 73.4% for Qwen3.6 — confirms Gemma is correctly assigned Tier 1/2, not Tier 2.5
- Multimodal: supports images and video — not needed for current tasks but adds future capability for market chart analysis
- MoE architecture: 35B total / 3B active → memory footprint similar to a dense 7-10B model during inference
- Q4 quant ~20GB — check Unsloth for optimized quantisation or use community GGUF from HuggingFace
- Thinking mode ON by default — must pass `--think=false` equivalent for Tier 2.5 classification tasks (same rule as Gemma 4 E2B/E4B)
- vLLM standard serve requires 8 GPUs for full 262K context; for shorter contexts (our typical agent prompts ~8-32K), single-machine CPU/Vulkan inference via Ollama is viable
- Sovereignty: Apache 2.0 or similar open-weight license, running locally — no Chinese-hosted API concern (data never leaves server)
- Competitor comparison: Qwen3.5-35B-A3B scores 70.0% SWE-bench — Qwen3.6 adds 3.4pp improvement
- Do not evaluate until MiniMax M2.7 benchmarking is complete — avoid overloading Oscar with simultaneous model routing decisions
