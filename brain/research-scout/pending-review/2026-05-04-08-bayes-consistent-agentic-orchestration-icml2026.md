# Bayes-Consistent Agentic Orchestration — ICML 2026 Position Paper

## Source
https://arxiv.org/abs/2605.00742 — "Position: Agentic AI Orchestration Should Be Bayes-Consistent" (accepted ICML 2026)

## Domain
Domain 1 — Agent Orchestration

## What It Is
An ICML 2026 position paper arguing that multi-agent orchestration layers should maintain calibrated probabilistic beliefs over task-relevant unknowns, update those beliefs based on agent outcomes, and make routing/tool-selection decisions via utility functions — not heuristics. Key claim: making individual LLMs Bayesian is hard, but applying Bayesian principles at the control layer is achievable and high-value.

## Why It Matters to This System
The orchestrator currently uses fixed tier assignments and rule-based escalation (3× failure → Tier 4). A Bayes-consistent extension would:
1. Maintain a belief distribution over "which tier will succeed at this task type" based on historical outcomes from agent_registry.json
2. Update that distribution after each completed run (success/failure/timeout logged)
3. Route dynamically based on expected utility rather than static tier rules

This is a Phase 3+ improvement, not immediate. But the design principle is relevant now: as feedback.json accumulates task outcomes, the orchestrator could learn which agent types perform better on which task categories — without requiring manual tier reassignment by Oscar.

The paper connects directly to what feedback.json + agent_registry.json already capture. The data infrastructure for a Bayesian orchestrator layer exists; the algorithm does not yet.

## What to Do With It
Add to reference library: create brain/reference-library/agent-orchestration-design.md as a new entry summarising Bayes-consistent orchestration, Karpathy autoresearch patterns, and OpenClaw orchestration learnings. This consolidates orchestration design principles in one reference file for future orchestrator improvements.
Monitor for 30 days before acting on implementation.

## Effort to Implement
High (1 week+) — requires redesigning escalation logic in orchestrator.py and building outcome tracking into agent_registry.json schema

## Urgency
Backlog — relevant for Phase 3 orchestrator improvements, not current Phase 2 priorities

## Raw Notes
Core argument: apply Bayesian decision theory at the orchestration/control layer, not throughout the LLM itself
Maintain calibrated probability beliefs over task-relevant unknowns
Update beliefs iteratively based on agent action outcomes and human-AI interactions
Use utility functions to connect beliefs to action selection (tool choice, expert routing, resource allocation)
ICML 2026 acceptance signals this is becoming a mainstream framework principle, not fringe research
Practical connection: orchestrator.py's current 3-failure escalation is a crude proxy for Bayesian fallback; this gives it a principled theoretical foundation
Data already exists: feedback.json (approved/rejected), agent_registry.json (retries, status), brain/kpis.md (weekly performance trends) — sufficient for a simple Bayesian update loop
Relevant future question: should the orchestrator maintain per-task-type priors, or per-agent-type priors, or both?
