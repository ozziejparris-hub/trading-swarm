# Claude Agent SDK: Native Subagents, Hooks, and Checkpoints Now Available

## Source
https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously
Anthropic blog post — "Enabling Claude Code to work more autonomously" (May 2026)

## Domain
Domain 1 — Agent Orchestration
Domain 6 — System Architecture

## What It Is
Anthropic has shipped three native autonomy features in the Claude Agent SDK (formerly Claude
Code SDK): (1) Checkpoints — automatic state saves before each change, reversible via /rewind;
(2) Subagents — parallel task delegation within a session (spin up backend agent while main agent
builds frontend); (3) Hooks — automated triggers at specific lifecycle points (e.g., run test
suite after code changes). The SDK now officially supports custom agentic workflows.

## Why It Matters to This System
We built our orchestration layer manually: tmux sessions as agents, spawn_agent.sh for delegation,
orchestrator.py's immune system as the hook layer, git worktrees for isolation. The Claude Agent
SDK now offers native versions of all three patterns. Two implications: (1) Our architecture is
validated — we independently converged on the same three primitives Anthropic shipped; (2) Long-term
migration path exists — once the SDK matures, portions of orchestrator.py could be replaced by
native SDK hooks, reducing maintenance burden. The checkpoint/rewind pattern also informs how
we should think about agent state recovery when the immune system detects failure.

## What to Do With It
Monitor for 30 days before acting — the SDK is new and production stability is unproven.
Discuss with Oscar before proceeding: at what point does native SDK replace our custom tmux/
worktree orchestration? For now, document the convergence as validation of our architecture.

## Effort to Implement
High (1 week+ to migrate orchestrator patterns to native SDK — not a priority now)

## Urgency
Backlog — note it now, revisit after Phase 3 is stable

## Raw Notes
- "Claude Agent SDK" is the renamed Claude Code SDK — confirmed same underlying system
- Hooks specifically: "automatically trigger actions at specific points" = our orchestrator.py loop
- Subagents = parallel task delegation = our multi-tmux + worktree pattern
- Checkpoints = auto state-save before change = no equivalent in our current setup (gap to note)
- Article mentions Sonnet 4.5 as "new default model" — our system correctly uses Sonnet 4.6
- VS Code native extension also released (beta) — not relevant for server/headless setup
- The convergence signal: three independent teams (Anthropic, OpenAI Codex, our swarm) all
  arrived at spawn/delegate/stop as the core orchestration primitives
