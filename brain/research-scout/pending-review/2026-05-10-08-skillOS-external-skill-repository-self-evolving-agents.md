# SkillOS: External Skill Repository with Frozen Executor + Trainable Curator

## Source
https://arxiv.org/abs/2605.06614 — "SkillOS: Learning Skill Curation for Self-Evolving Agents"
(May 2026). HuggingFace Daily Papers, 32 upvotes.

## Domain
Domain 1 — Agent Orchestration

## What It Is
RL framework for self-evolving LLM agents using a dual-component architecture: a Frozen Agent
Executor (retrieves and applies skills without modification) plus a Trainable Skill Curator (RL-
trained to update an external skill repository). Skills are stored as Markdown files that evolve
into richer "meta-skill" documents over time through experience. Earlier trajectories update the
repository; later related tasks evaluate those updates. Demonstrates consistent improvements
over memory-free and static memory baselines across multi-turn agentic and single-turn reasoning
tasks. Curator generalises across different executor models.

## Why It Matters to This System
Our brain/ directory is a manually-maintained skill repository — lessons-learned.md,
reference-library/, strategy-notes/ are all hand-curated "skills" for agents to read before
acting. SkillOS is an automated version of what our training-librarian-agent does manually:
observe outcomes, update the repository, improve future agent performance. Three specific
insights are applicable now: (1) Separating the executor (doesn't touch the skill store) from
the curator (only writes to the skill store) maps cleanly onto our read-only agent design —
agents should never modify brain/ directly, only via the training-librarian; (2) Storing skills
as structured Markdown with meta-skill layers is exactly the format we already use; (3) Grouping
tasks by "skill-relevant dependencies" (related tasks benefit from each other's updates) is
something our feedback-loop-agent could implement — currently it treats every agent run
independently.

## What to Do With It
Monitor for 30 days before acting — wait for code release and practical implementations.
Add to reference library once a companion implementation post appears. The architectural
insights (frozen executor / trainable curator separation) should inform the next iteration of
training-librarian-agent when Phase 3 self-improvement is built.

## Effort to Implement
High (1 week+) — architectural change to training-librarian-agent and feedback-loop-agent.

## Urgency
Backlog — relevant at Phase 3 (self-improvement layer), not blocking Phase 1-2.

## Raw Notes
- Architecture: Frozen Executor + Trainable Skill Curator (RL-trained)
- Skill repository: external Markdown files that evolve into meta-skills over time
- Training: earlier trajectories update repository → later related tasks evaluate updates
- Composite rewards used to train the curator
- Tasks grouped by skill-relevant dependencies (key design decision)
- Generalises across executor models — curator is model-agnostic
- No mention of open-source code release in the abstract
- Paper week: emerging cluster of self-evolving agent papers (also CMU 2605.05724, SkillOS
  2605.06614 all appeared May 8-10 2026). Convergent timing suggests RL-based self-improvement
  is becoming a mainstream research priority, not a niche direction.
