# Gemma 4 Multi-Token Prediction Drafters — Up to 3x Tier 1/2 Speedup Available Now

## Source
https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/
HN discussion: https://news.ycombinator.com/item?id=48024540 (545 points)
Ollama: version 0.23.1-rc0 (recent merge confirmed in HN thread)

## Domain
Domain 3 — Model Capabilities / Domain 6 — System Architecture

## What It Is
Google released Multi-Token Prediction (MTP) drafters for Gemma 4 on May 5, 2026. Using speculative decoding — a lightweight drafter predicts multiple tokens, the main model verifies in parallel — the technique achieves up to 3x inference speedup with no quality degradation, now available in Ollama via version 0.23.1-rc0 or later.

## Why It Matters to This System
Our Tier 1 (Gemma 4 E2B) and Tier 2 (Gemma 4 E4B) benchmarks are 37.97 tok/s and 14.79 tok/s respectively under Vulkan (OLLAMA_VULKAN=1). AMD hardware has shown 2.5x speedup on AMD MI50s in HN user reports (20 → 50 tok/s). If AMD Radeon 780M iGPU achieves comparable gains, Tier 2 latency could drop from 5.86s to ~2s first token — changing the responsiveness of signal-agent and code-hygiene tasks. Tier 1 at ~90 tok/s would also reduce orchestrator immune system cycle time. This directly improves our most frequent agent operations at zero additional cost.

## What to Do With It
Test immediately: upgrade Ollama to 0.23.1-rc0, identify the MTP variant tags for E2B and E4B (e.g., `gemma4:e2b-mtp`), and benchmark against existing results with `OLLAMA_VULKAN=1`. If speedup ≥ 1.5x on AMD Radeon 780M: update `/etc/systemd/system/ollama.service.d/rocm.conf` to use the MTP variants and record new benchmark baseline in model-routing.md.

## Effort to Implement
Low (< 1 hour) — Ollama version upgrade + benchmark run

## Urgency
Now

## Raw Notes
- Reported HN speedups: RTX A6000 2.75x, dual AMD MI50 2.5x, RTX 3090 ~2.5x
- Ollama command pattern from HN: `ollama run gemma4:31b-coding-mtp-bf16` — implies E2B/E4B variants may be `gemma4:e2b-mtp` or similar; check `ollama list` after 0.23.1-rc0 upgrade
- Caveat: some MTP variants listed as "requires macOS" in Ollama library — must verify Linux/Vulkan support before relying on speedup
- Caveat: quantization degrades acceptance rate (fewer speculative tokens accepted → smaller speedup); our Q4 quantised models may see 1.5-2x rather than 3x
- AMD Day Zero support page timed out — could not confirm specific Radeon 780M MTP guidance; AMD MI50 HN report is closest proxy
- Google confirms "efficient clustering technique in embedder to accelerate E2B/E4B specifically" — suggests the smaller variants have been specially optimized
- Apache 2.0 license — no usage restrictions
- Implementation risk: upgrading Ollama from current 0.22.1 to 0.23.1-rc0 is a release candidate; may introduce instability. Consider testing in isolation before updating production Ollama service.
