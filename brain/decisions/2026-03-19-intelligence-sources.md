# Decision Record: Research Scout Intelligence Sources

Date: 2026-03-19
Decided by: Oscar (Server Pre-Setup Chat 2)
Status: Active
Supersedes: None (first sources document)
Review trigger: If research-scout-agent self-assessments
  show repeated low approval rate from Oscar over 4 weeks

---

## Decision

Expand the research-scout-agent's monitored sources with
five additions, verified against track record before committing:

**Added to Tier 1 (daily):**
- Hugging Face Daily Papers (huggingface.co/papers)
  Curated by @_akhaliq. Pre-filters arXiv to the papers that
  actually matter. 440K Twitter followers, decade-long curation
  track record. Karpathy publicly endorsed it as the standard
  for arXiv paper discovery. Replaces raw arXiv scanning with
  a pre-filtered digest — same signal, less noise.

**Added to Tier 1 Twitter:**
- @_akhaliq — the person behind the HuggingFace daily papers feed.
  Monitoring the account catches papers before they reach the feed.

**Added to Tier 2 Substacks:**
- Latent Space (latent.space) — swyx and Alessio
  200K+ subscribers, top 10 US tech podcast, technical AI
  engineering focus. Covers agent frameworks, model infra, and
  Claude Code developments directly relevant to swarm architecture.
  Endorsed by Karpathy and Andrej-adjacent ML community.

- Ahead of AI (magazine.sebastianraschka.com) — Sebastian Raschka
  168K subscribers, LLM research engineer, weekly deep dives.
  Published the definitive technical tour of DeepSeek V3→V3.2
  architecture (cited in today's research). Covers model
  architecture, quantisation, and practical implementation at
  exactly the level of depth useful for local model tier decisions
  and quant-research methods. Apache 2.0 focused — open weights.

**Added to Tier 3 GitHub:**
- huggingface.co/deepseek-ai — DeepSeek release announcements
- github.com/unslothai/unsloth — quantisation updates for
  local model viability assessment

---

## Alternatives Considered

**@swyx Twitter (separate from Latent Space substack):**
Rejected as duplicate. Latent Space the substack covers the
same ground more densely. Adding the Twitter account would
create redundant signals about the same content.

**General AI hype accounts (>5 posts/day):**
Rejected categorically. Volume without signal dilutes the
research-scout's filtering capacity. Oscar's attention is
the scarcest resource. The scout's job is aggressive filtering,
not comprehensive coverage.

**Additional quant finance substacks:**
Deferred. The existing reference library (Lopez de Prado, Chan,
Tetlock, Poundstone) covers the foundational quant material.
Additional substacks in this space tend to repeat these sources
rather than extend them. Revisit if quant-research-agent
identifies specific knowledge gaps not covered by the library.

---

## Signal Quality Expectations

The research-scout-agent's self-assessment protocol (every
7 cycles) should track approval rates per source. Expected
signal quality ranking based on track record:

High signal (expect >60% of surfaced items approved):
- HuggingFace daily papers / @_akhaliq
- @karpathy
- Ahead of AI (Raschka)

Medium signal (expect 30-60% approved):
- Latent Space
- @lopezdeprado
- arXiv cs.AI filtered through HF papers

Lower signal (monitor, adjust filter aggressively):
- Raw arXiv scanning (now supplemented by HF papers filter)
- General Twitter / Hacker News

If any source consistently produces <20% approval after
4 weeks, remove it from the active monitoring list and
log the removal in this decisions directory.
