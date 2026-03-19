# Decision Record: Model Routing Architecture

Date: 2026-03-19
Decided by: Oscar (Server Pre-Setup Chat 2)
Status: Active
Supersedes: None (first routing document)
Review trigger: After 4 weeks of server operation, or when
  any watch list item reaches open-weight release

---

## Decision

Adopt a five-tier model routing architecture for the trading
swarm. The tiers, their models, and their per-agent assignments
are documented authoritatively in brain/model-routing.md.

The key structural decision is the addition of Tier 2.5
(Claude Haiku 4.5) as a bridge between free local inference
and Sonnet, assigned to integration-test-agent and
research-scout-agent.

---

## Context

Pre-server setup research (March 19 2026) reviewed the full
landscape of available models and routing infrastructure.
The original architecture (Pre-Setup Chat 1) had four tiers
with Qwen3-Coder as Tier 2 and Sonnet as Tier 3. No Haiku
tier existed.

Research confirmed:
- Claude Haiku 4.5 released October 2026, priced $1/$5 per MTok
- Scores 73.3% on SWE-bench Verified — near frontier performance
- Anthropic positions it explicitly for sub-agent orchestration
- 3x cheaper than Sonnet for bounded, well-structured tasks
- Qwen3-Coder-Next confirmed: 80B MoE, 3B active params,
  256K context, >70% SWE-bench, requires ~46GB RAM at Q4

Three new sources were also evaluated:
- Cursor Composer 2: IDE-only, no external API — not applicable
- MiniMax M2.7: cloud-only, Chinese-hosted — fails sovereignty
- Mistral Forge: enterprise training platform — not applicable

---

## Alternatives Considered

**Alternative 1: Keep four tiers, no Haiku**
Rejected. Integration-test and research-scout were slotted to
Qwen (Tier 2) but both have characteristics that make Anthropic
reliability preferable: integration-test output is safety-critical
(a missed failure cascades silently), research-scout runs daily
with structured output requirements. The cost difference between
Haiku and Sonnet for these agents is ~$2/month. Not a meaningful
saving to sacrifice reliability.

**Alternative 2: Use Haiku for all Tier 2 tasks**
Rejected. Signal-agent, code-hygiene, and training-librarian
are genuinely mechanical and run frequently. Paying $1/$5 per
MTok for pattern matching on text files or SQLite queries when
Qwen3-Coder-Next is free and sufficient is unjustified cost.
Local-free is the right tier for these.

**Alternative 3: LiteLLM as routing infrastructure**
Deferred, not rejected. LiteLLM provides unified API across
100+ providers with routing, fallback, and cost tracking.
Confirmed viable for this use case. However, it adds operational
overhead (Redis, Postgres, maintenance) that is not justified
before the system has run for a month and generated real cost
data. Revisit after 4 weeks of server operation when actual
usage patterns are known.

---

## Model String Reference (confirmed correct as of March 2026)

```
claude-haiku-4-5-20251001    Tier 2.5  $1/$5 per MTok
claude-sonnet-4-6            Tier 3    $3/$15 per MTok
claude-opus-4-6              Tier 4    $5/$25 per MTok
```

Previous strings (claude-sonnet-4-5, claude-opus-4-5) referred
to the prior generation and were corrected in spawn_agent.sh
during this session.

---

## Watch List — Triggers for Revisiting This Decision

**DeepSeek V4:**
Leaked benchmarks claim 80%+ SWE-bench Verified with open
weights and trillion-parameter MoE architecture (~37B active).
If released open-weight and verifiably runnable on 128GB RAM,
evaluate as Tier 2 upgrade or Tier 3 cost reduction. Do not
act on leaked benchmarks alone — wait for independent
verification and Unsloth/llama.cpp quantisation support.

**MiniMax M2.7 open weights:**
Currently cloud-only and Chinese-hosted (fails sovereignty).
Benchmarks show Sonnet 4.6 parity at $0.30/$1.20 per MTok —
roughly 10x cheaper than Sonnet. If released as open weights,
sovereignty concern is removed and it becomes a strong Tier 2.5
or Tier 3 candidate. Monitor minimax.io/news.

**Qwen3-Coder-480B local:**
The 480B version achieves Sonnet-comparable coding performance.
At Q2 quantisation via llama.cpp MoE offloading it may be viable
on 128GB RAM. If Unsloth confirms stable Q4 quantisation on
consumer hardware, it could shift several Tier 3 coding tasks
to free local inference. Monitor github.com/unslothai/unsloth.

**LiteLLM revisit trigger:**
If weekly API cost exceeds £50/week after 4 weeks of operation,
evaluate LiteLLM as a routing and cost-optimisation layer.
Key benefit at that scale: prompt caching coordination across
agents and unified spend tracking per agent type.
