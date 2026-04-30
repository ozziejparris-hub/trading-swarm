# Architectural Heterogeneity Reduces Artificial Consensus in Multi-Agent Forecasting

## Source
arXiv:2604.26561 — "Preserving Disagreement: Architectural Heterogeneity and Coherence Validation in Multi-Agent Policy Simulation"
Author: Ariel Sela
120 deliberations across two policy scenarios
Submitted: April 2026

## Domain
Domain 1 — Agent Orchestration
(Secondary: Domain 2 — Quantitative Methods — ensemble forecasting methods)

## What It Is
Multi-agent deliberation systems where all agents use the same underlying LLM tend to converge artificially on one answer — not because of genuine agreement but because identical models reason identically. This paper tests two interventions: (1) assigning different 7-9B models to each agent role instead of copies of the same model; (2) using a frontier model to validate that each agent's reasoning actually reflects its assigned perspective. Key result: architectural heterogeneity reduced first-choice concentration from 70.9% to 46.1% in one scenario and 46.0% to 22.9% in another — statistically significant. Coherence validation had mixed effects: it helped in unambiguous scenarios but paradoxically increased clustering on genuinely competitive options.

## Why It Matters to This System
This system's signal-agent currently aggregates trader predictions as a crowd. In Phase 3+, if multiple AI agents are used to generate independent forecasts (analogous to the Superforecasting aggregation model), this finding directly applies: running N copies of the same Sonnet model produces N correlated predictions with artificial consensus, not genuine diversity. The paper provides empirical validation for using the different local models (Gemma 4 E2B for fast assessment, Gemma 4 E4B for detailed reasoning, Haiku for structured output) to generate independent forecasts on the same question before aggregating — rather than running the same model multiple times. This is a concrete implementation principle for any Phase 3+ ensemble forecasting approach.

## What to Do With It
Add to reference library: new section on multi-agent forecast aggregation principles. Flag for quant-research-agent: when RQ3.2 (crowd vs elite divergence) is extended to AI agent ensembles, use architecturally distinct models per agent to avoid correlated outputs. Do not act on this before Phase 3 — it's a future architecture decision.

## Effort to Implement
Low to document. Medium to implement (requires adding multi-model ensemble step to forecasting pipeline in Phase 3+).

## Urgency
Backlog — not actionable until Phase 3+ multi-agent forecasting pipeline exists.

## Raw Notes
Coherence validation finding is important and counter-intuitive: using a frontier model to check whether each agent's reasoning aligns with its assigned role *increased* clustering on genuinely close decisions. The mechanism: coherence validation amplifies high-coherence evaluators, which in competitive scenarios pushes toward the dominant option. This is a warning against naive "filter for quality" steps in multi-agent aggregation pipelines — filtering can destroy diversity.

The 70.9% → 46.1% concentration reduction is the headline stat, but the negative result from three Delphi approaches (structured deliberation methods that failed to improve diversity) is equally important: not all multi-agent coordination improves forecasting.

Direct relevance to RQ3.2: if elite traders converge partly because they share similar model structures (information sources, reasoning patterns), then the elite consensus signal may capture a correlated error as much as a genuine edge. This is an additional confound to test in RQ3.2 analysis.
