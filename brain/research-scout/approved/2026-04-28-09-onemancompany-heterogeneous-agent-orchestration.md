# OneManCompany (OMC) — Self-Organising Heterogeneous Agent Framework

## Source
https://arxiv.org/abs/2604.22446
arXiv:2604.22446 — "From Skills to Talent: Organising Heterogeneous Agents as a Real-World Company" (HuggingFace daily papers, 57 upvotes)

## Domain
Agent Orchestration

## What It Is
Proposes OneManCompany (OMC), a framework treating agents as portable "Talent" identities with skills, tools, and runtime configs. A dynamic "Talent Market" allows runtime agent reconfiguration. An Explore-Execute-Review (E²R) Tree Search unifies planning, execution, and evaluation in a hierarchical loop. Achieves 84.67% on PRDBench, +15.48pp over previous state of the art.

## Why It Matters to This System
**Phase 3+ self-improvement architecture reference:** Our current system uses a static 14-agent pool with fixed routing. OMC's Talent Market concept addresses exactly the limitation we'll face in Phase 3 (self-improvement): agents with complementary capabilities need to be dynamically assembled for novel tasks rather than statically assigned. The E²R Tree Search decompose-then-aggregate pattern is a more principled version of our current "spawn → check output → escalate" loop.

**Not for Phase 2 (too early):** Current priority is running one agent stably. OMC is architectural research for the Phase 3+ redesign of the orchestrator. Surfaced now so it's available when Phase 3 agent self-improvement design begins.

**Specific transferable concept — E²R loop:** The Explore-Execute-Review loop formalises what our immune system does informally. The "Review" phase's systematic outcome aggregation bottom-up could improve how the orchestrator synthesises agent outputs across tasks.

## What to Do With It
"Add to reference library: create brain/reference-library/agent-orchestration-OMC.md summarising OMC architecture. Review when designing Phase 3 self-improvement agent. Not actionable before Phase 3."

## Effort to Implement
High (1 week+ if adopting as Phase 3 architecture; Low for reference library entry only)

## Urgency
Backlog

## Raw Notes
- 84.67% PRDBench success rate vs 69.19% previous SOTA — significant improvement
- "Portable agent identities" (Talent) vs our fixed agent types — more flexible
- "Talent Market: community-driven recruitment system enabling dynamic reconfiguration during execution" — useful for handling novel task types in Phase 3
- "Formal guarantees on termination and deadlock freedom" — our current immune system handles this pragmatically; OMC has theoretical backing
- Paper claims generality across domains via cross-domain case studies — suggests the architecture is not domain-specific
- HuggingFace upvotes: 57 — moderate community interest
