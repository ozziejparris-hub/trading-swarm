# BTF-2: Benchmark for Evaluating Strategic Reasoning in Forecasting Agents

**Source:** arXiv:2604.26106 — "Evaluating Strategic Reasoning in Forecasting Agents"
**Authors:** Tom Liptay, Dan Schwarz, Rafael Poyiadzi, Jack Wildman, Nikos I. Bosse
**Added:** 2026-04-30 (approved from research-scout cycle 4)
**Relevant phases:** Phase 2–3 (immediately actionable for quant-research-agent)

---

## What BTF-2 Is

A pastcasting benchmark of 1,417 questions with a frozen 15-million-document corpus.
Resolution is reproducible and offline — no lookahead possible because the corpus is frozen.
Detection sensitivity: 0.004 Brier score (can distinguish very small accuracy improvements).

The benchmark is publicly available. Can be used to evaluate swarm forecasting accuracy
in Phase 2–3 before going live on fresh markets.

---

## Key Findings

### The Winning Technique: Pre-Mortem Analysis

The composite forecaster that outperformed individual frontier models by 0.011 Brier
score derived its edge primarily from:

1. **Pre-mortem analysis of blind spots** — explicitly reasoning about where your
   forecast is most likely wrong *before* finalising it
2. **Explicit black swan consideration** — asking what low-probability, high-impact
   events could invalidate the forecast

0.011 Brier score improvement may sound small, but the benchmark detects differences
as fine as 0.004 — this is a statistically significant edge.

### Systematic Frontier Model Failure Modes

Expert human forecasters identified these as systematic weaknesses in frontier LLMs:

1. **Assessing political / business leader motivations** — models are poor at
   predicting what individual leaders will actually do vs what they say
2. **Probability that stated commitments get executed** — "will X actually follow
   through on their announced plan?"
3. **Modelling how institutional processes function** — bureaucratic, legislative, and
   corporate processes are poorly modelled

These failure modes map directly to Polymarket market categories. See category flags below.

### Ensemble > Individual

- Ensemble of frontier models outperforms any single model by 0.011 Brier score
- This is consistent with RQ3.2 (crowd vs elite divergence): a group of calibrated
  forecasters outperforms an individual expert
- The key: ensemble members must have diverse reasoning, not just diverse random seeds.
  See architectural-heterogeneity-forecasting.md for the empirical validation of this.

---

## Category Flags for Polymarket Markets

Markets where quant-research-agent and signal-agent should apply **elevated uncertainty
priors** and require higher Brier score thresholds before accepting signal confidence:

| Category | Flag | Reason |
|---|---|---|
| Political leader decisions | HIGH UNCERTAINTY | Models systematically fail at leader motivation |
| "Will X follow through on Y?" | HIGH UNCERTAINTY | Commitment execution probability is hard to model |
| Legislative/regulatory outcomes | HIGH UNCERTAINTY | Institutional processes poorly modelled |
| Elections | STANDARD | Well-studied, better-calibrated |
| Macroeconomic indicators | STANDARD | Process-driven, less leader-intent dependent |
| Geopolitical events | HIGH UNCERTAINTY | Leader intent + institutional process combined |

---

## The Pre-Mortem Step

Before finalising any probability estimate, run this explicit check:

1. **State your forecast and confidence interval**
2. **List the top 3 ways this forecast could be wrong** (not just unlikely — specifically
   where your reasoning chain might have a blind spot)
3. **Consider one black swan** — a low-probability event that would dramatically change
   the outcome if it occurred
4. **If any item on the list changes your confidence materially — update before finalising**

This step is now required in quant-research-agent template (Rules section).

---

## Relation to RQ3.2

The 0.011 Brier improvement from ensemble > individual provides external empirical
grounding for RQ3.2's hypothesis that elite consensus outperforms market price.
The mechanism is the same: aggregating calibrated, independent viewpoints reduces
individual forecaster error. Key distinction: BTF-2 uses LLM ensembles; RQ3.2 uses
human trader ELO tiers. The underlying mathematical principle is identical.

When writing RQ3.2 theoretical grounding documentation, cite BTF-2 as external
validation of the aggregation-beats-individual principle, with the caveat that
diversity of reasoning (not just diversity of agents) is what drives the edge.

---

## Benchmark Access

Dataset: publicly available pastcasting questions with historical corpus.
Practical use: in Phase 2–3, run swarm forecasts against BTF-2 resolved questions
as an additional calibration benchmark beyond polymarket_tracker.db.
