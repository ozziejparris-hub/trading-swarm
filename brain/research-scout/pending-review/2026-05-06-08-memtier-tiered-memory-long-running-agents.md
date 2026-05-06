# MEMTIER — Tiered Memory Architecture for Long-Running Autonomous Agents

## Source
https://arxiv.org/abs/2605.03675
"MEMTIER: Tiered Memory Architecture and Retrieval Bottleneck Analysis for Long-Running Autonomous AI Agents"
arXiv preprint (under review, May 6 2026)

## Domain
Domain 1 — Agent Orchestration

## What It Is
MEMTIER identifies that flat-file memory systems cause a 14 percentage-point degradation in tool-execution success rates over 72-hour continuous operation windows. It proposes a tripartite architecture: structured episodic storage (JSONL) → weighted retrieval engine → asynchronous consolidation daemon that promotes facts to a semantic tier, with a PPO-based policy for retrieval weight optimization. Designed for the OpenClaw agent runtime. Achieves +33pp improvement on LongMemEval-S benchmark, running on a 6GB GPU laptop.

## Why It Matters to This System
Our swarm runs continuously (orchestrator every 10 minutes, agents hours-long). The 14pp degradation finding is directly applicable: as agents accumulate more brain/ files and feedback.json grows, flat-file memory lookup degrades. The async consolidation daemon pattern maps exactly to what training-librarian-agent does manually — periodically consolidating episodic agent outputs into the reference library. MEMTIER formalizes this as a retrievable architecture. The OpenClaw connection is notable — OpenClaw is already on our watch list for agent orchestration patterns.

## What to Do With It
Add to reference library: create `brain/reference-library/memtier-tiered-memory.md` with key patterns extracted. Relevant for Phase 3 orchestrator redesign — specifically the feedback.json and brain/agent-outputs/ consolidation problem. Do not implement now (Phase 2 not yet begun); file for training-librarian-agent to review when reference library is next updated.

## Effort to Implement
High (1 week+) — full architectural adoption would require restructuring brain/ memory retrieval

## Urgency
Backlog

## Raw Notes
- Five-component architecture: (1) JSONL episodic store, (2) weighted retrieval engine using 5 signals, (3) cognitive weight update loop via attention attribution, (4) async consolidation daemon (episodic → semantic promotion), (5) PPO policy for retrieval weight optimization
- LongMemEval-S results: Acc=0.382, F1=0.412 with Qwen2.5-7B on 6GB GPU (full-context baseline: 0.050)
- Single-session recall: 0.686-0.714 with semantic pre-population — this is the pattern we already do manually (pre-loading reference library into prompts)
- Paper is under review — performance metrics "pending finalization"; treat with caution until published
- OpenClaw connection: designed for OpenClaw runtime (same framework referenced in our agent-orchestration-OMC.md reference library file — the OneManCompany pattern)
- PPO training not applicable to our API-based system — but the ARCHITECTURE PATTERN (tiered episodic → semantic consolidation) is the actionable insight
- The 72-hour degradation finding validates our orchestrator's immune system design (catching degraded agents, forcing restart) — our current mitigation
- Practical implication for current phase: brain/feedback.json is currently flat — as it grows to hundreds of entries, retrieval for agents who "read feedback.json before starting" will degrade. Consider semantic indexing at ~500 entries.
