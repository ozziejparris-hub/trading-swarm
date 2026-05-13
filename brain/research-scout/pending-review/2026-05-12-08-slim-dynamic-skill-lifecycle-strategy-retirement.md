# SLIM: Dynamic Skill Lifecycle Management — Principled Strategy Retirement and Expansion

## Source
https://arxiv.org/abs/2605.10923 — "Dynamic Skill Lifecycle Management for Agentic Reinforcement Learning" (May 2026). HuggingFace Daily Papers, 10 upvotes.

## Domain
Domain 1 — Agent Orchestration

## What It Is
SLIM manages the lifecycle of skills (externally-stored capabilities) in RL agents using leave-one-skill-out validation to estimate each skill's marginal contribution. Skills are retained if high-value, retired when their value becomes negligible (policy has absorbed them), and expanded when persistent failure indicates a capability gap. SLIM outperforms fixed-library baselines by 7.1 percentage points on ALFWorld and SearchQA.

## Why It Matters to This System
Our strategy-registry.md already tracks ACTIVE/PENDING/SUSPENDED/RETIRED strategy statuses, but transitions are manual and based on qualitative judgment. SLIM's leave-one-skill-out validation maps directly: measure each strategy's marginal contribution to signal accuracy, retire strategies whose marginal contribution is statistically negligible, and trigger new hypothesis pre-registration when existing strategies collectively fail on a new market category. This makes the strategy lifecycle decision-rule explicit rather than subjective. Distinction from SkillOS (filed 2026-05-10): SkillOS is about composing skills from an external repository; SLIM is about when to retire vs expand — the lifecycle governance question.

## What to Do With It
New research direction: propose to quant-research-agent that RQ5 (post-Phase 2) measure marginal strategy contribution — does removing STR-001/STR-002 from the signal independently reduce accuracy? If marginal contribution is negligible, automate retirement trigger. Add SLIM's retirement criterion to the strategy-registry.md template as a field: `marginal_contribution_last_measured`.

## Effort to Implement
Medium (1 day) — adding marginal contribution measurement to backtest workflow; automating retirement trigger in feedback-loop-agent.

## Urgency
This month

## Raw Notes
- Leave-one-skill-out: run agent with and without each skill, measure performance delta
- Retirement trigger: marginal contribution < threshold after N episodes where N is configurable
- Expansion trigger: persistent failure rate > threshold on specific task categories (maps to: new market type where all strategies fail → pre-register new hypothesis)
- "Some skills are absorbed into the policy" = strategy knowledge baked into the model's context after repeated exposure
- Directly maps to our strategy-registry.md ACTIVE→RETIRED transition rules
- Strategy = skill, backtest accuracy = marginal contribution metric, market category = task type
- See also: SkillOS (pending-review/2026-05-10-08-skillOS-external-skill-repository-self-evolving-agents.md)
