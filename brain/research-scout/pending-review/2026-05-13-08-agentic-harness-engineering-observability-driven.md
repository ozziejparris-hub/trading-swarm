# Agentic Harness Engineering: Observability-Driven Automatic Evolution of Agent Harnesses

## Source
https://arxiv.org/abs/2604.25850 — "Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses" (Carnegie Mellon, April 2026). HuggingFace Daily Papers, high engagement.

## Domain
Domain 1 — Agent Orchestration + Domain 6 — System Architecture

## What It Is
A framework for automatically improving agent harnesses (the scaffolding that structures prompts, handles input/output, manages tool calls) using observability data from failed runs. Instead of manually redesigning harnesses, the system learns what failures are caused by harness issues (vs agent reasoning failures) and iteratively improves them. The key insight: harness design is learnable, not manual.

## Why It Matters to This System
Signal-agent needs to run stably (Priority 2). Its harness is the prompt template + output format + error handling in orchestrator/task_templates/signal-agent.md. If signal-agent crashes, times out, or outputs malformed JSON, the immune system catches it but doesn't automatically improve the harness. This paper shows how observability (which you already have via agent_registry.json and immune system logs) can drive automatic harness improvements. Specific relevance: when signal-agent fails, instead of Oscar manually tweaking the prompt, the framework could surface "output_format_error in 40% of signal-agent runs → recommend adding explicit JSON structure example to prompt."

## What to Do With It
Discussion topic for quant-research-agent or orchestrator improvements: "Could we adapt the observability-driven harness evolution approach to automatically improve signal-agent's prompt template based on immune system failure logs?" This is not urgent, but valuable once signal-agent is stable (post-Priority 2). Add to reference library: brain/reference-library/agent-orchestration-OMC.md (append section on observability-driven harness iteration).

## Effort to Implement
Medium (1-2 days) — would require: (1) parsing agent_registry.json failure logs by failure type, (2) mapping failure types to harness components, (3) generating harness suggestions. Not blocking Phase 2.

## Urgency
Backlog — relevant post-signal-agent stability, for Phase 3 self-improvement work

## Raw Notes
- CMU paper, same institution as the specialist-agents lineage-feedback work (both from April-May 2026)
- Key finding: heterogeneous action spaces and voluminous trajectories make manual harness engineering the current bottleneck
- Framework includes: failure attribution (which harness component caused the failure), candidate generation (what to change), and validation
- Code: not mentioned as released, but approach is straightforward to adapt
- Related to your orchestrator's immune system — you already have the observability data, just need the evolution logic
- Distinct from the CMU specialist-agents paper: that's about research loop, this is about harness scaffolding
