# Agent Orchestration — Architectural Patterns for Multi-Agent Systems

**Audience:** Orchestrator redesign, Phase 3 self-improvement planning. Not required reading for Phase 1-2.

---

## OneManCompany (OMC) — Heterogeneous Agent Framework
**Source:** arXiv:2604.22446 — "From Skills to Talent: Organising Heterogeneous Agents as a Real-World Company"

### Core Architecture

**Talent Identity:** Each agent in OMC carries a portable identity with skills, tools, and runtime configuration. Unlike fixed agent pools (our current 14-agent static pool), Talent identities can be dynamically composed and reconfigured for novel tasks.

**Talent Market:** A community-driven recruitment system enabling runtime agent reconfiguration during execution. When a task requires capabilities not available in the current active pool, the Talent Market assembles a new combination on-the-fly. This is the direct architectural upgrade from our current static AGENT_TIER_DEFAULTS dictionary.

**E²R Tree Search (Explore-Execute-Review):** A unified hierarchical loop formalising what our immune system does informally:
- *Explore* — decompose task into subtasks, identify required agent capabilities
- *Execute* — spawn agents, run subtasks in appropriate worktrees
- *Review* — aggregate outcomes bottom-up, determine if task goal is met

Performance: 84.67% PRDBench vs 69.19% previous SOTA (+15.48pp).

### Relevance to Trading Swarm

**Phase 3+ orchestrator redesign target:** Our current immune system performs an informal version of E²R — spawn → check output (file existence only) → escalate. OMC's Review phase does systematic outcome aggregation rather than binary file checks. When Phase 3 self-improvement design begins, E²R is the reference architecture.

**What OMC solves that we haven't built:** Static 14-agent pool cannot handle novel task types without manual addition of new templates. The Talent Market addresses this — Phase 3 agents that generate new hypotheses will need to spawn agent types that don't exist yet.

**When NOT to apply:** Phase 1-2. Current priority is running one agent stably. OMC is over-engineering for a system that hasn't validated its first signal.

---

## Agentic Harness Engineering — Observability-Driven Harness Improvement
**Source:** arXiv:2604.25850 — "Agentic Harness Engineering" (CMU, April 2026)

### Core Insight

Agent harnesses (prompt templates, output formats, tool call structures) are the primary bottleneck in multi-agent system reliability — and they are learnable, not fixed. Observability data from failed runs can drive automatic harness improvement rather than manual debugging.

**Failure attribution:** The framework distinguishes harness failures (wrong output format in template, missing context) from agent reasoning failures (model limitation). Our immune system currently catches both as "task failed" without attribution.

**Harness improvement loop:**
1. Parse failure logs by failure type (output_format_error, timeout, malformed_json, etc.)
2. Map failure type to harness component (prompt section, output template, tool spec)
3. Generate harness modification candidates
4. Validate candidates on held-out task samples

### Relevance to Trading Swarm

**Immediate application target — signal-agent:** When signal-agent crashes or outputs malformed JSON, the failure type (format error vs reasoning error) is currently unattributed. If 40% of signal-agent failures are output_format_error, that's a harness fix, not a model tier upgrade.

**Data already available:** agent_registry.json failure logs + immune system output contain the observability data the framework requires. The evolution logic is the missing piece.

**Timeline:** Post-Priority 2 (after signal-agent runs stably for ≥2 weeks). Build harness improvement after knowing what the stable failure mode distribution looks like.

### Implementation Notes
- Not released as code — approach is directly adaptable from the paper's methodology
- Related: OMC E²R Review phase (above) — same observability-driven feedback principle at task level; harness engineering applies it at template level

---

## How to Use These References

**For orchestrator loop redesign (Phase 3):** Start with E²R as the structural template. Replace our binary immune system checks with Review-phase outcome aggregation.

**For signal-agent stabilisation (Phase 2):** Apply harness engineering methodology to attribute failure types in agent_registry.json before deciding whether to change prompt templates or escalate model tier.

**For novel task handling (Phase 3+):** Talent Market assembly concept — if a new strategy requires agents that don't exist, build the capability composition rather than adding another static template.
