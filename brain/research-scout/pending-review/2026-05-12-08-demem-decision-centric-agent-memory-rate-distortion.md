# DeMem: Decision-Centric Agent Memory via Rate-Distortion Theory

## Source
https://arxiv.org/abs/2605.10870 — "Remember the Decision, Not the Description" (May 2026). arXiv cs.AI.

## Domain
Domain 1 — Agent Orchestration

## What It Is
DeMem introduces a rate-distortion framework for agent memory that retains only the distinctions between past experiences that affect future decisions, discarding everything that wouldn't change what the agent does next. It proves an "exact forgetting boundary" and derives a "memory-distortion frontier" characterizing optimal tradeoffs, then implements an online memory learner with near-minimax regret guarantees. Results show consistent gains over salience-based and relevance-based memory approaches under equal memory budgets.

## Why It Matters to This System
Our feedback.json currently stores complete strategy descriptions, backtest reports, and cycle summaries — information-rich but not decision-optimized. The DeMem insight reframes the question: what in feedback.json actually changes what quant-research-agent or signal-agent does next cycle? If two strategy outcomes share the same decision implication ("don't retry STR-001 without larger sample"), the system retains one, not both. This maps directly to improving how our agents query and use feedback.json, and how training-librarian-agent prunes lessons-learned.md. The principle also applies to signals.json retention: old processed signals that didn't change routing decisions are noise.

## What to Do With It
Add to reference library: create brain/reference-library/agent-memory-architectures.md incorporating DeMem's core principle alongside the ADEMA knowledge-state work already approved. When training-librarian-agent next reviews lessons-learned.md, apply the decision-centric filter: does this lesson change what any agent would do differently? If not, it should be compressed or removed.

## Effort to Implement
Low (< 1 hour) — principle adoption requires no code, just documentation update. Full DeMem implementation would be Medium.

## Urgency
This month

## Raw Notes
- Key theoretical result: retaining "decision conflict" distinctions is necessary and sufficient for optimal memory under budget constraint
- DeMem is an online learner — no batch pre-processing of historical data needed
- Tested on synthetic diagnostics and conversational benchmarks
- Practical application to feedback.json design:
  - Keep: entries that caused an agent to take a different action than default
  - Compress: entries that all point to the same decision implication
  - Discard: entries about events that resolved without any decision consequence
- The weekly training-librarian pass is a natural time to apply decision-centric pruning
- Related approved finding: ADEMA knowledge-state orchestration (brain/research-scout/approved/2026-04-29-08-adema-knowledge-state-orchestration.md)
