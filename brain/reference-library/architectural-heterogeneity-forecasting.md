# Architectural Heterogeneity in Multi-Agent Forecasting

**Source:** arXiv:2604.26561 — "Preserving Disagreement: Architectural Heterogeneity and Coherence Validation in Multi-Agent Policy Simulation"
**Author:** Ariel Sela
**Added:** 2026-04-30 (approved from research-scout cycle 4)
**Relevant phases:** Phase 3+ (ensemble forecasting design); RQ3.2 confound (immediately)

---

## The Core Finding

Multi-agent systems where all agents use the **same underlying LLM** produce artificial
consensus — not genuine agreement. The models reason identically, so they converge to the
same answer regardless of whether that answer is correct.

**Empirical result:** Architectural heterogeneity (assigning different models to each
agent role) reduced first-choice concentration from:
- 70.9% → 46.1% in scenario 1
- 46.0% → 22.9% in scenario 2

Both reductions are statistically significant. 120 deliberations tested.

---

## The Counter-Intuitive Finding: Coherence Validation Backfires

Using a frontier model to check whether each agent's reasoning aligns with its assigned
role *increased* clustering on genuinely competitive decisions.

**Mechanism:** Coherence validation amplifies high-coherence evaluators. In ambiguous
scenarios, this pushes the ensemble toward the dominant option even when genuine
uncertainty exists. The result is an ensemble that appears confident but is overfit
to a single perspective.

**Warning:** Naive "filter for quality" steps in multi-agent aggregation pipelines can
destroy the diversity that makes ensembles valuable. Only apply coherence filtering when
you're certain the task has an objectively correct framing — not when genuine uncertainty
exists.

---

## Application to This System

### Phase 3+ Ensemble Forecasting (Future)

When multiple AI agents are used to generate independent forecasts on the same Polymarket
question, do NOT run N copies of the same Sonnet model. Use architecturally distinct models:

| Agent Role | Model | Rationale |
|---|---|---|
| Fast initial assessment | Gemma 4 E2B (Tier 1) | Low-cost, different architecture |
| Detailed reasoning | Gemma 4 E4B (Tier 2) | Larger local model, still distinct |
| Structured synthesis | Claude Haiku (Tier 2.5) | API-backed, different training |
| Final calibration check | Claude Sonnet (Tier 3) | Most capable, final override only |

This matches the existing model routing tiers and adds a justification for why the
tiered approach is correct beyond just cost optimisation.

### RQ3.2 Confound (Immediately Relevant)

If elite traders share similar information sources, social networks, or reasoning
patterns, the "elite consensus" signal may capture **correlated error** rather than
genuine predictive edge. The elite traders might be reasoning identically (like copies
of the same LLM) rather than independently.

**This is an additional confound to test in RQ3.2 analysis:**
- Does elite consensus accuracy degrade when traders share obvious information sources?
- Are the legendary traders in each market actually independent, or are some following
  each other's signals (the 102 copy-traders already identified)?
- Does excluding copy-traders (RQ5.2) reduce or increase apparent consensus accuracy?

Document this confound in the RQ3.2 theoretical grounding file.

---

## What This Is NOT

This finding does NOT say:
- All multi-agent systems are bad
- You should always use heterogeneous models
- Consensus is always wrong

It says: when you want **genuine diversity** in your ensemble, architectural heterogeneity
produces it. When you want **speed and consistency**, homogeneous models are fine.

For this system: the signal aggregation step (combining multiple trader signals) already
benefits from the natural diversity of human traders. The AI agent layer (Phase 3+) should
mirror this by using architecturally distinct models for the same reason.
