# DeepSeek V4 Open Weights Released — Tier 3 Cost Reduction Trigger

## Source
https://artificialanalysis.ai/articles/deepseek-is-back-among-the-leading-open-weights-models-with-v4-pro-and-v4-flash
https://api-docs.deepseek.com/news/news260424
https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro

## Domain
Model Capabilities

## What It Is
DeepSeek released V4-Pro (1.6T total / 49B active params) and V4-Flash (284B total / 13B active params) on April 24, 2026. Both are MIT-licensed open weights on HuggingFace. Both support 1M token context windows. V4-Flash scores 79.0% on SWE-bench Verified vs Claude Sonnet 4.6's 79.6% — within 1 percentage point at 34x lower API cost.

## Why It Matters to This System
`brain/model-routing.md` explicitly states: **"Halt all Tier 3 cost optimisation decisions until V4 drops."** That trigger has now fired.

**V4-Flash API pricing:** $0.14 input / $0.28 output per MTok
**Claude Sonnet 4.6 pricing:** $3.00 input / $15.00 output per MTok
**Output cost ratio:** 53x cheaper. For quant-research and backtest agents that produce long outputs, this is the most significant cost change available.

**Benchmark parity confirmed:**
- DeepSeek V4-Flash: 79.0% SWE-Bench Verified
- Claude Sonnet 4.6: 79.6% SWE-Bench Verified
- Gap: 0.6 percentage points — within noise, functionally equivalent

**V4-Pro** at $1.74/$3.48 per MTok scores 80.6% SWE-Bench — slightly above Sonnet 4.6, at roughly half Sonnet's input cost and ~80% cheaper output. Ranked #2 open-weight model.

**Local inference:** V4-Flash at 284B total params requires ~142GB RAM at Q4 quantisation — not runnable on the UM890 Pro (96GB DDR5). V4-Pro (1.6T params) also not locally viable. The cost reduction opportunity is API-only.

**OpenAI-compatible API endpoint** at api.deepseek.com — same pattern as Kimi K2.6. Can be tested in `spawn_agent.sh` without code changes by swapping the base URL and model string.

**Combined with Kimi K2.6** (already in strategy-notes, $0.60/$2.50 per MTok, similar benchmarks): there are now two V4-level Sonnet alternatives for Tier 3 evaluation, both cheaper.

## What to Do With It
**Discuss with Oscar before proceeding** — schedule a benchmark comparison run:
1. Take 3 representative quant-research tasks (mixed: statistical reasoning, code generation, structured output)
2. Run identically against Sonnet 4.6, V4-Flash, and Kimi K2.6
3. Score on: output correctness, JSON format adherence, template following, multi-step reasoning
4. If V4-Flash passes all 3 task types: update `brain/model-routing.md` Tier 3 assignment and `orchestrator/orchestrator.py` AGENT_TIER_DEFAULTS dict

Note: Sovereignty requirements — DeepSeek is Chinese-hosted API. Same data governance question as MiniMax. For research and backtesting agents (no live wallet or position data), this may be acceptable. For any agent that handles wallet addresses or live position data, maintain Anthropic API. Oscar decides the sovereignty line.

## Effort to Implement
Low (< 1 hour) for benchmark test — API endpoint swap only. Medium (1 day) if sovereignty review required.

## Urgency
**Now** — this is the model routing watch list's highest-priority trigger. The model-routing.md freeze on Tier 3 optimisation explicitly lifts when V4 drops.

## Raw Notes
- MIT license confirmed — commercial use permitted
- 1M token context window — matches Sonnet 4.6's 1M window for large brain/ injections
- V4 built from ground up for 1M context (not bolted on) — 10% KV cache vs DeepSeek V3.2
- V4-Pro: 27% of single-token inference FLOPs vs V3.2 — efficient despite size
- VentureBeat: "near state-of-the-art intelligence at 1/6th the cost of Opus 4.7, GPT-5.5"
- Cache hit pricing: V4-Flash $0.028/MTok vs Sonnet $0.30/MTok (same ~90% cache discount structure)
- API docs: api-docs.deepseek.com/news/news260424
