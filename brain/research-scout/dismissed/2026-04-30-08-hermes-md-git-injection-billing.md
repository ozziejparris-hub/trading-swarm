# HERMES.md Bug Reveals Claude Code Injects Git History Into Agent Prompts
<!-- DISMISSED 2026-04-30: spawn_agent.sh audited — no git history injection. Claude CLI invoked via -p (print mode), not interactive; no git-status auto-injection in this mode. No "HERMES.md" string in any commit message; billing routing bug does not apply. Git history contains no sensitive data. Concern is real for interactive Claude Code sessions but does not apply to this swarm's agent-spawning architecture. -->

## Source
https://github.com/anthropics/claude-code/issues/53262
Hacker News discussion: 1,099 points, 468 comments (top story today)

## Domain
Domain 6 — System Architecture

## What It Is
A reproducible bug in Claude Code (v2.1.119) where the case-sensitive string "HERMES.md" in any recent git commit message triggers incorrect billing routing (bypasses Max plan quota, bills to pay-as-you-go). Root cause: Claude Code automatically includes recent git commit messages in its system prompt, and an internal server-side routing rule matches "HERMES.md" specifically. The bug is a side-effect of a broader architectural fact: every Claude Code session has recent git history injected into its context automatically.

## Why It Matters to This System
Two implications. First, the billing risk: if Oscar is on the Max plan and any commit in a worktree contains "HERMES.md" in its message, the session silently burns pay-as-you-go credits. This is highly unlikely but costs $200+ per occurrence per the bug report. Second, and more architecturally significant: **all agents spawned via Claude Code in this swarm have recent git commit history injected into their prompts automatically**. That means every research-scout, quant-research, or backtest agent session carries commit metadata as context overhead. Malicious or excessively verbose commit messages could inflate token costs or inject unintended instructions. This swarm's commit messages are currently clean and well-formatted, but the injection surface exists.

## What to Do With It
Discuss with Oscar before proceeding. Two actions:
1. Verify whether the swarm's agents are invoked via API key (pay-as-you-go) or via Max plan — if API key, billing routing bug is irrelevant.
2. Audit `scripts/spawn_agent.sh` to confirm whether Claude Code CLI is injecting git history into agent prompts and whether this should be suppressed with `--no-git` flag or equivalent. Keep commit messages short and free of filenames matching internal Anthropic identifiers.

## Effort to Implement
Low (< 1 hour) — audit spawn script, add flag if needed, confirm billing mode.

## Urgency
Now — active bug, Anthropic has not publicly confirmed a fix as of 2026-04-30.

## Raw Notes
Reproduction confirmed by multiple users. Case-sensitive: "hermes.md" (lowercase) does NOT trigger. "AGENTS.md", "README.md" do NOT trigger. Committed "HERMES.md" file on disk with a clean commit message also does NOT trigger — it's specifically the commit message text.

The deeper finding: Claude Code reads `git log --oneline` (approximately) and prepends it to the system prompt. Token cost scales with repo commit history depth. For the trading swarm, every spawned agent session could be carrying tens or hundreds of lines of commit log overhead. Worth measuring.

Issue was closed (unclear if Anthropic fixed or just closed). Monitor for changelog entry in next Claude Code release.
