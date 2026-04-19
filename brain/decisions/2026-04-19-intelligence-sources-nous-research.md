# Decision Record: Nous Research — Intelligence Sources Addition

Date: 2026-04-19
Decided by: Oscar
Status: Active
Supersedes: None (addendum to 2026-03-19-intelligence-sources.md)
Review trigger: Same as parent — if approved signals drop below
  20% over 4 weeks, flag for removal.

---

## Decision

Add Nous Research and their CEO Jeffrey Quesnelle to the Tier 2
Twitter/X monitoring list in the research-scout-agent template.

**Added to Tier 2 Twitter:**
- @nousr_computer — Nous Research official account.
  Nous Research is the lab behind the Hermes series of open-weight
  fine-tuned models (Hermes 3 on Llama 3.x), which are among the
  strongest open-source instruction-following and tool-use models
  available. Directly relevant to Tier 2/2.5 model routing decisions
  — a strong Hermes release on a new base model is a candidate
  evaluation for the local model tier.

- @jquesnelle — Jeffrey Quesnelle, CEO of Nous Research.
  Announces model releases and research directions ahead of formal
  blog posts. Monitoring the CEO directly catches Hermes releases
  and agent fine-tuning work before the official feed.

---

## Hermes Agent Relevance

The Hermes models are notable for:
- Superior tool-call / function-calling reliability vs base Llama
- Agentic task instruction following (system prompt adherence)
- Long-context fidelity (important for agent prompt templates)
- Open-weight Apache 2.0 — sovereignty-compatible for local tiers

For this swarm, a new Hermes release on a capable base model
(e.g. Hermes-3 on Llama 4) should be evaluated immediately as
a Tier 2 or Tier 2.5 candidate. The research-scout-agent should
escalate via signals.json whenever Nous releases a new Hermes
checkpoint on a base model >= current Tier 2 capability.

---

## Signal Quality Expectations

Expected signal quality: Medium-High (30-60% approval rate).
Nous releases infrequently (~4-6 per year) but when they do
the releases are directly relevant to model routing decisions.
Low volume, high relevance per item.

---

## Alternatives Considered

**@teknium1 (Teknium, Nous Research founder):**
Added to watch list but secondary to @jquesnelle — Teknium is
more research-focused; Jeffrey more ops/release-focused. Both
worth following but @jquesnelle is the primary signal source
for new releases.

**Following Nous HuggingFace directly:**
huggingface.co/NousResearch is Tier 3 (weekly GitHub/HF scan)
for new checkpoint releases. The Twitter accounts give earlier
signal before formal HF posts.
