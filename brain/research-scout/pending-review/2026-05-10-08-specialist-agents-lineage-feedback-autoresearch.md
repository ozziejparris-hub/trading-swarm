# CMU Specialist Agents: Lineage Feedback Turns Failures into Recipe Edits

## Source
https://arxiv.org/abs/2605.05724 — "Auto Research with Specialist Agents Develops Effective and
Non-Trivial Training Recipes" (May 2026, Carnegie Mellon University). HuggingFace Daily Papers,
12 upvotes. Related: Karpathy autoresearch (github.com/karpathy/autoresearch, 42K stars).

## Domain
Domain 1 — Agent Orchestration

## What It Is
CMU paper demonstrating a fully autonomous research loop where specialist agents partition a
recipe search space and share trial lineage. Over 1,797 trials with no human intervention, the
system turns every evaluator outcome — including crashes, budget overruns, size failures, and
accuracy-gate misses — into structured "lineage feedback" that informs subsequent proposal
generation. Results: 38.7% improvement on NanoChat-D12, 4.59% wallclock reduction on CIFAR-10.

## Why It Matters to This System
Our feedback.json is a simple approved/rejected ledger. The lineage feedback pattern here is
richer: every failure type is labelled and fed back as structured context for the next agent
run, not just a binary outcome. The specific failure labels (crashes, budget overruns, size
failures, accuracy-gate misses) map almost exactly to the failure modes our orchestrator already
tracks (timeout, output missing, CI validation fail). This paper shows how to use those failure
labels productively rather than just retrying. The specialist-agent partitioning also directly
validates our approach of assigning domain-specific agents rather than a single general agent.

## What to Do With It
Add to reference library: new file brain/reference-library/cmu-specialist-agents-autoresearch.md
covering the lineage feedback design. Also: consider enriching feedback.json schema to log failure
type (timeout/missing-output/validation-fail/format-error) rather than just approved/rejected —
makes feedback-loop-agent's analysis more useful.

## Effort to Implement
Low (< 1 hour) — reference library addition; feedback.json schema enrichment is Medium (1 day).

## Urgency
This week — reference library file should be added before feedback-loop-agent's next run.

## Raw Notes
- 1,797 total trials, zero human interventions during search
- Lineage feedback: evaluator outcomes (including crashes) → structured labels → next proposal
- Specialist agents partition recipe surfaces, share trial lineage across specialisations
- Auditable trajectory: proposals + code diffs + experiments + failure labels all logged
- Architecture-domain audit of 157 submissions with documented program rewrites
- Distinct from Karpathy autoresearch: Karpathy's loop is single-agent, one metric, one GPU.
  CMU's adds specialist decomposition and structured failure feedback across multiple domains.
- Code: not mentioned as open-source in abstract
- Paper emerged same week as SkillOS (2605.06614) — convergent thinking on agent self-improvement
