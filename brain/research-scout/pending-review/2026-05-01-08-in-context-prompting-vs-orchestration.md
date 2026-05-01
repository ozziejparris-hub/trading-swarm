# In-Context Prompting Outperforms Agent Orchestration for Procedural Tasks

## Source
https://arxiv.org/abs/2604.27891
arXiv:2604.27891 — "In-Context Prompting Obsoletes Agent Orchestration for Procedural Tasks" (submitted April 30, 2026, preprint)

## Domain
Agent Orchestration

## What It Is
Preprint comparing orchestration frameworks (LangGraph, CrewAI, Google ADK, OpenAI Agents SDK) against a single LLM with the full procedure embedded in its system prompt. Tested across 200 conversations in 3 procedural domains (travel booking, Zoom support, insurance claims). In-context approach scored 4.53–5.00 vs orchestrated 4.17–4.84, with orchestrated systems failing 2x more often (17–24% vs 5–11.5% failure rates).

## Why It Matters to This System
Direct relevance to three of our agents with well-defined procedural task structures:

**integration-test-agent:** Runs 6 fixed test suites in a defined sequence. Its task structure is entirely procedural — if a single Haiku call with the full test procedure in the system prompt achieves lower failure rates than the current template-spawned worktree approach, this could simplify the integration-test architecture significantly.

**signal-agent:** Queries SQLite, applies ELO filter, writes JSON — entirely procedural. Currently spawned via `scripts/spawn_agent.sh` into a worktree. If the task can be completed reliably via in-context prompt, it avoids the overhead of worktree creation.

**code-hygiene-agent:** Scans files, matches patterns, writes report — also procedural. Same case as signal-agent.

**Counter-argument (why this probably doesn't apply to our orchestrator):** The paper's scope is explicitly "procedural tasks" — defined workflows with predictable branching. Our orchestrator's routing, respawning, and escalation logic is non-procedural (it must reason about agent failure modes, interpret ambiguous signals, make judgment calls). The paper does not claim in-context prompting replaces orchestration for complex, non-procedural workflows.

**Architectural implication:** For the next time a new agent is being designed (Phase 3+), default to testing an in-context single-call approach before defaulting to worktree orchestration. The overhead of worktree setup and tmux management may not be justified for procedural agents.

## What to Do With It
Monitor for 30 days before acting — this is a preprint with significant limitations:
- Only 3 domains tested, all customer service style (not quant research)
- LLM-as-judge evaluation method introduces circularity risk
- No multi-step or stateful tasks tested

If the paper gets peer review acceptance or replication, revisit with Oscar whether integration-test-agent should be restructured as a single in-context call. Not worth acting on preprint alone given our current system is working.

## Effort to Implement
Low to evaluate (< 1 hour: run integration-test task as single in-context call and compare to current output). Medium if restructuring proceeds.

## Urgency
Backlog — monitor until peer-reviewed. Flag for Phase 3 architectural review.

## Raw Notes
- Paper authored by team at [unnamed institution], submitted April 30 — very fresh, no citations yet
- LangGraph was the best-performing orchestration framework tested — still underperformed in-context baseline
- Failure definition: "task not completed within conversation" — matches our immune system's file-existence check heuristic
- Does not address cost — orchestration overhead may matter more than quality at scale
- Benchmark gap may close as frontier models improve further — but implies current Haiku-tier models already sufficient for procedural tasks
- No evaluation of tasks requiring tool use across multiple external systems simultaneously (our agents do this)
- Procedural task definition: "a defined procedure with predictable branches" — excludes our quant-research and backtest agents by design
