# Grok 4.3 — Potential Tier 3 Cost Reduction Candidate

## Source
https://artificialanalysis.ai/articles/xai-launches-grok-4-3-with-improved-agentic-performance-and-lower-pricing
https://openrouter.ai/x-ai/grok-4.3

## Domain
Domain 3 — Model Capabilities

## What It Is
xAI (US) released Grok 4.3 on April 30 2026. Proprietary model, 1M token context, priced at $1.25 input / $2.50 output per MTok. AI Intelligence Index score: 53 (vs Claude 57, Kimi K2.6 54, GPT-5.5 60). SWE-bench trails Claude Opus 4.7 by ~14 percentage points. Agentic performance improved significantly: 300+ Elo points on GDPval-AA vs Grok 4.20. Throughput: 189.9 tok/s.

## Why It Matters to This System
At $2.50/MTok output, Grok 4.3 is 6x cheaper than Sonnet 4.6 ($15/MTok output) and 10x cheaper than Opus 4.7 ($25/MTok output). If it can reliably handle Tier 3 tasks (quant-research, backtest, market-builder), the output cost reduction is material. Sovereignty is cleared: xAI is a US company. The agentic performance improvement (+300 Elo on GDPval-AA) is directly relevant to multi-step agent tasks. The risk: SWE-bench trails Opus 4.7 by ~14 points, which may put it at or below Sonnet 4.6 (79.6%) — insufficient for tasks requiring multi-file statistical reasoning. Not currently on watch list.

## What to Do With It
Monitor for 30 days before acting — add to model-routing.md watch list section. Once independent benchmark comparisons vs Sonnet 4.6 are published, evaluate as Tier 3 cost reduction candidate. No immediate action needed.

## Effort to Implement
Low — add to watch list now; benchmark evaluation is 1 day when warranted

## Urgency
This month (watch list addition only)

## Raw Notes
- Company: xAI (US) — sovereignty cleared
- Architecture: proprietary, size undisclosed
- Context: 1M tokens
- Pricing: $1.25 input / $2.50 output per MTok (OpenRouter rate confirmed)
  vs Sonnet 4.6: $3/$15 — Grok 4.3 is 2.4x cheaper input, 6x cheaper output
  vs Haiku 4.5: $1/$5 — Grok 4.3 is 1.25x more expensive input, 2x cheaper output
- Intelligence Index: 53 — below Sonnet 4.6 cluster (~55-57 estimated)
- SWE-bench: ~14 points below Opus 4.7 (~87%) → estimated ~73%, below Sonnet (79.6%)
- Key risk: if SWE-bench ~73%, fails the Tier 3 minimum floor (set at Sonnet 79.6%)
- Agentic improvement: +300 Elo on GDPval-AA — may be strong on tool-use tasks
  even if raw coding benchmark is lower
- NOT open-weight — API only
- Released April 30 2026; 395 HN points
- Potential use case: Tier 2.5 replacement for Haiku 4.5 at lower output cost
  if quality is above Haiku on structured tasks
