# Claude Opus 4.7 Released — Tier 4 Model String Needs Update

## Source
https://www.anthropic.com/claude/opus
https://artificialanalysis.ai/models/claude-opus-4-7

## Domain
Model Capabilities

## What It Is
Anthropic released Claude Opus 4.7 on April 16, 2026. Model ID: `claude-opus-4-7`. Pricing unchanged at $5/$25 per MTok input/output. Key improvement: 64.3% on SWE-bench Pro (vs GPT-5.4 at 57.7%, Gemini 3.1 Pro at 54.2%). New tokenizer uses ~35% more tokens for equivalent text.

## Why It Matters to This System
`brain/model-routing.md` currently specifies `claude-opus-4-6` as the Tier 4 escalation model. That model ID is now one generation behind. The routing document states Tier 4 is used for genuine architectural decisions and 3× Sonnet failures — these are the highest-stakes tasks in the system. Using a stale model for Tier 4 is a silent quality downgrade.

**Important caveat on effective cost:** The new Opus 4.7 tokenizer uses ~35% more tokens for the same fixed text. At $25/MTok output, this means effective cost per task increases despite identical per-token pricing. For a task that previously cost $X with Opus 4.6, it will cost ~$1.35X with Opus 4.7. The 3-failure escalation gate already limits Opus frequency, but this should be noted in model-routing.md.

**Model string update needed in two places:**
1. `brain/model-routing.md` — Tier 4 model string
2. `orchestrator/orchestrator.py` — AGENT_TIER_DEFAULTS dict
3. `scripts/spawn_agent.sh` — if hardcoded model strings exist for Tier 4

## What to Do With It
**Update agent template:** update `brain/model-routing.md` and `orchestrator/orchestrator.py` to replace `claude-opus-4-6` with `claude-opus-4-7` in Tier 4 assignment. Add note about 35% tokenizer overhead in cost section.

## Effort to Implement
Low (< 1 hour) — two string replacements plus documentation note.

## Urgency
**This week** — not blocking any current work (Tier 4 not yet used in production), but should be correct before the orchestrator goes live.

## Raw Notes
- 64.3% SWE-bench Pro (new harder benchmark replacing Verified as frontier measure)
- Stronger coding, vision, complex multi-step tasks vs Opus 4.6
- 2,576px long-edge image support (~3.75 megapixels, 3× resolution of Opus 4.6)
- Pricing: $5/$25 per MTok (unchanged from Opus 4.6)
- Effective cost increase of ~35% per-task due to new tokenizer consuming more tokens
- Prompt caching discount still applies (up to 90% on input)
- Batch API discount still applies (50%)
- Released April 16, 2026
- Claude Mythos (Project Glasswing, 93.9% SWE-bench) still gated to 50 organisations — not yet a consideration for public Tier 4
