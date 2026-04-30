# ADEMA: Knowledge-State Orchestration for Long-Horizon Agent Tasks

## Source
https://arxiv.org/abs/2604.25849
arXiv:2604.25849 — "ADEMA: A Knowledge-State Orchestration Architecture for Long-Horizon Knowledge Synthesis"

## Domain
Agent Orchestration

## What It Is
Architecture for preventing "knowledge state drift" in long-horizon LLM agent tasks — where accumulated evidence degrades across rounds, intermediate commitments stay implicit, and interruptions fracture the evidence chain. Proposes eight mechanisms: explicit epistemic bookkeeping, heterogeneous dual-evaluator governance, adaptive task-mode switching, reputation-shaped resource allocation, checkpoint-resumable persistence, segment-level memory condensation, artifact-first assembly, and final-validity checking with safe fallback.

## Why It Matters to This System
**Addresses the exact failure mode our long-running agents hit.** The quant-research-agent runs multi-step statistical tasks that can take hours. Between orchestrator check cycles, the agent can lose track of which hypotheses have been tested, what intermediate results mean, and what the current task state is — exactly what ADEMA calls "knowledge state drift." The current immune system checks whether output files exist, but does not check whether the agent has maintained coherent epistemic state across its run.

**Three immediately transferable mechanisms:**

1. **Checkpoint-resumable persistence** — quant-research-agent tasks that run >4h currently hit the orchestrator timeout (immune system kills them). ADEMA's checkpoint pattern would allow the orchestrator to resume mid-task rather than restart from scratch. The paper's 60-run test found that removing checkpoint/resume was the only configuration producing invalid runs — it's the most load-bearing mechanism.

2. **Segment-level memory condensation** — relevant for how the training-librarian-agent handles large reference library files. Instead of re-reading entire files each cycle, condense segments and track evidence pointers.

3. **Heterogeneous dual-evaluator governance** — a more principled version of our immune system. The immune system currently checks file existence; dual evaluation checks whether the content produced is epistemically valid.

**Complements OMC (already in reference library):** OMC addresses multi-agent coordination (who does what); ADEMA addresses within-task knowledge management (how agents maintain coherent state over time). They solve different problems.

## What to Do With It
"Add to reference library: create brain/reference-library/adema-knowledge-state-orchestration.md. Review when designing Phase 3 self-improvement loop and when addressing the >4h agent timeout problem in orchestrator.py. Specifically: evaluate checkpoint-resumable persistence pattern for quant-research-agent task templates."

## Effort to Implement
High (1 week+ to implement checkpoint pattern in orchestrator; Low for reference library entry)

## Urgency
Backlog

## Raw Notes
- Eight mechanisms identified, tested via "fixed 60-run mechanism matrix" (ablation across configurations)
- Checkpoint/resume is the single most critical mechanism — only configuration producing invalid runs when removed
- Dual evaluation and segment synthesis function as "supporting mechanisms shaping trajectory discipline"
- "Artifact-first assembly" means building outputs incrementally with verifiable intermediate artifacts — analogous to writing intermediate JSON results rather than just a final report
- Problem framing: "knowledge states drift across rounds, intermediate commitments remain implicit, interruption fractures the evolving evidence chain" — this is the exact failure mode in quant-research-agent multi-step tasks
- No code repo mentioned in abstract — architecture paper, not a framework release
- Phase 3 priority: design orchestrator's knowledge management before self-improvement runs
