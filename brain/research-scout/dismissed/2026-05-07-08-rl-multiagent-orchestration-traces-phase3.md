# RL for LLM Multi-Agent Systems via Orchestration Traces: Phase 3 Design Intelligence

## Source
https://arxiv.org/abs/2605.02801 — "Reinforcement Learning for LLM-based Multi-Agent Systems
through Orchestration Traces" (May 2026, very recent)

## Domain
Domain 1 — Agent Orchestration

## What It Is
A systematic survey and taxonomy of how reinforcement learning can optimise multi-agent LLM
coordination. Introduces "orchestration traces" — temporal interaction graphs capturing agent
spawning, delegation, tool use, communication, aggregation, and stopping decisions — as the
shared object for RL-based learning. Covers 84 papers across reward design, credit assignment,
and orchestration decision optimisation. Connects to deployed systems: Kimi Agent Swarm,
OpenAI Codex, Anthropic Claude Code.

## Why It Matters to This System
Our Phase 3 self-improvement design depends on feedback-loop-agent improving the swarm over
time. This survey provides the theoretical framework for doing that systematically. Two specific
gaps identified in the literature are directly relevant to our design choices:
1. No RL methods exist for agent stopping decisions — our immune system timeout (4h hard cutoff)
   is hand-coded; this suggests there's no proven alternative, so our approach is defensible.
2. Credit assignment is sparse at the message level — we assign feedback at the task level via
   feedback.json, which aligns with the "team-level" credit family (one of 8 identified), the
   most tractable for our current setup.

## What to Do With It
Add to reference library: create reference-library/rl-multiagent-orchestration-survey.md
Specifically: extract the 8 reward families and 5 orchestration sub-decisions as a checklist
for designing the Phase 3 feedback-loop improvements.

## Effort to Implement
Low (< 1 hour to read and extract the checklist; Medium if implemented as a design template)

## Urgency
This month — read before designing Phase 3 feedback-loop improvements

## Raw Notes
- Artifact released: 84-entry tagged paper pool + 32-record exclusion log + minimal JSON schema
  for replayable orchestration traces
- Eight reward families: covers parallelism speedup, aggregation quality, and 6 others
- Five orchestration sub-decisions: when to spawn, delegate, communicate, aggregate, stop
- Key gap: no existing RL method for stopping decisions — our 4h timeout is the state of the art
- Industrial connections: authors explicitly reference Claude Code's orchestration patterns
- Survey methodology: systematic, not cherry-picked — exclusion log available for verification
- "Orchestration trace" as a concept directly parallels our agent_registry.json tracking
