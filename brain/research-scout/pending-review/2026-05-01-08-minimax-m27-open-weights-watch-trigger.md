# MiniMax M2.7 Released as Open Weights — Tier 2.5 Candidate

## Source
https://huggingface.co/MiniMaxAI/MiniMax-M2.7
https://huggingface.co/unsloth/MiniMax-M2.7-GGUF
https://www.minimax.io/news/minimax-m27-en
https://unsloth.ai/docs/models/minimax-m27

## Domain
Model Capabilities

## What It Is
MiniMax released M2.7 as open weights on HuggingFace on April 12, 2026 (MIT license). It is a sparse MoE model — 230B total parameters, 10B active per token, 256 experts, 200K context window. Unsloth has published quantised GGUFs including UD-Q2_K_XL at 75.3GB — within the server's 96GB DDR5 RAM.

## Why It Matters to This System
`brain/model-routing.md` lists MiniMax M2.7 as an explicit watch trigger: *"If released open-weight, priority evaluation — compatible API means zero integration cost. Sovereignty blocker remains until open weights confirmed."*

**Both blockers are now cleared:**
- Sovereignty: open weights on HuggingFace (MIT license) — no Chinese-hosted API required
- Hardware: UD-Q2_K_XL quantisation (75.3GB) fits the UM890 Pro's 96GB DDR5 RAM

**Benchmarks:**
- SWE-Pro: 56.22% (matches GPT-5.3-Codex)
- Terminal Bench 2: 57.0%
- ELO on GDPval-AA: 1495 — highest among open-weight models
- MoE architecture: inference speed scales to ~10B dense model (only 10B params active per token)

**Compatibility:** MiniMax announced Anthropic-compatible API in its API docs (April update). If the local Ollama runner also supports it, this could be a drop-in replacement at Tier 2.5 with zero code changes in `spawn_agent.sh`.

**Cost implication:** If viable locally, replaces Haiku 4.5 calls for integration-test and research-scout agents at $0 cost instead of $1/$5 per MTok. Weekly cadence integration-test alone would cost ~$0 vs current ~$0.50/week — marginal, but the sovereignty and offline-capability gains are the real prize.

## What to Do With It
Discuss with Oscar before proceeding — hardware viability confirmed, sovereignty cleared. Propose a benchmark comparison:
1. Pull `unsloth/MiniMax-M2.7-GGUF` at UD-Q2_K_XL variant via Ollama or llama.cpp
2. Run server RAM usage baseline first — confirm 75.3GB fits with OS overhead
3. Run 3 representative Tier 2.5 tasks (integration-test structured output, research-scout relevance filter, a simple code-hygiene scan)
4. Score on: output format adherence, reasoning quality, latency vs Haiku 4.5
5. If latency < 30s and output quality ≥ Haiku: update `brain/model-routing.md` and `orchestrator/orchestrator.py` AGENT_TIER_DEFAULTS

## Effort to Implement
Low (< 1 hour) for benchmark test. Medium (1 day) if Ollama GGUF setup requires manual configuration.

## Urgency
This week — the watch list trigger has fired. Hardware requirements confirmed viable. Do not defer past Phase 2 start.

## Raw Notes
- UD-IQ1_M variant (60.7GB) also fits but with "measurable quality loss" per Unsloth docs
- UD-Q2_K_XL (75.3GB) is labelled "sweet spot for 96GB workstations" by Unsloth
- Q4 target (140GB) exceeds server RAM — not viable
- MoE inference: only 10B params activated per token — throughput much faster than parameter count suggests
- Unsloth page: https://unsloth.ai/docs/models/minimax-m27
- Self-improvement capability: model can perform 30-50% of RL research workflow autonomously — relevant for Phase 3 self-improvement planning
- Model-routing.md note to update: "Update April 2026: M2.7 claims Anthropic-compatible API... Sovereignty blocker remains until open weights confirmed." — that condition is now met.
- Secondary check: does the model handle the 200K context window well at Q2 quantisation? The reference library injections in quant-research tasks can be large.
