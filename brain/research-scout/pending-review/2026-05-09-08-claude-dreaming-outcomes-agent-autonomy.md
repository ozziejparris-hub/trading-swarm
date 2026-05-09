# Claude Managed Agents: Dreaming and Outcomes — Async Self-Improvement Primitives

## Source
https://simonwillison.net/2026/May/6/code-w-claude-2026/ — Simon Willison live blog of
Code w/ Claude 2026 event (May 6, 2026). Anthropic demonstration of two new features:
"Dreaming" (research preview, requires access request) and "Outcomes" (public beta).

## Domain
Domain 1 — Agent Orchestration

## What It Is
Two new Anthropic agent capabilities announced at Code w/ Claude 2026 — distinct from the
Checkpoints/Subagents/Hooks announced earlier in the Claude Agent SDK:
**Dreaming** (research preview): Claude examines its previous sessions overnight, identifies
knowledge gaps, and generates new memory files autonomously (demo produced a
`descent-playbook.md` playbook from post-session analysis). Currently gated — requires
access request.
**Outcomes** (public beta): Developer defines what success looks like; Claude iterates
autonomously until the outcome is achieved, rather than executing a fixed sequence of steps.
Fundamentally different from instruction-following — it's goal-directed iteration.

## Why It Matters to This System
Our feedback-loop-agent (runs weekly) manually implements what "Dreaming" automates:
reviewing past performance, identifying what worked vs. failed, and updating strategy-registry.md.
The Dreaming pattern — post-session review → gap identification → memory synthesis → playbook
generation — is exactly the feedback loop we manually designed. Two implications:
1. **Dreaming**: When gated access opens, evaluate whether integrating it into our feedback-loop
   cycle reduces the manual structure we've built. The demo showed overnight async operation —
   matching our weekly cadence exactly.
2. **Outcomes**: Our current orchestrator.py operates on instruction sequences (spawn agent → await
   output → verify → close). Outcomes-style goal-directed iteration would allow agents to
   self-correct without waiting for the orchestrator's 10-minute check loop. Phase 3 signal-agent
   could be refactored from "run this sequence" to "achieve this calibration threshold."

## What to Do With It
Monitor for 30 days before acting — both features are early-stage (Dreaming gated, Outcomes
public beta). Add a note to brain/decisions/ that this represents Anthropic's endorsement of
the feedback-loop-agent design pattern we independently built. When Dreaming opens generally,
evaluate integration before writing more manual post-session analysis logic.

## Effort to Implement
Low (< 1 hour) to request Dreaming access and document what integration would look like.
High (1 week+) to refactor orchestrator.py to Outcomes-style goal-directed agents — defer
until these features mature.

## Urgency
This month — request Dreaming access now; assess Outcomes for Phase 3 agent redesign.

## Raw Notes
- Dreaming demo: overnight session → produced `descent-playbook.md` autonomously
- Outcomes: "set what success looks like so Claude can iterate and get it done"
- Multi-agent orchestration (also announced at same event): fleets of coordinated agents
  — Commander/Detector/Navigator demo. Public beta. This is separate from the Subagents
  feature in the existing SDK pending-review item.
- Dreaming access request URL: not provided in live blog — check anthropic.com/research
- The pattern Anthropic is converging on: async background agents that improve themselves
  via overnight session analysis — exactly the feedback-loop-agent pattern we built.
  Convergence signal: multiple teams independently arriving at same architecture.
- The "Code w/ Claude" event also confirmed: Claude Code Routines (async automations that
  run on a schedule and deliver PRs) — directly relevant to our cron-based agent spawning.
  These are now a first-class Claude Code feature, not a custom script workaround.
