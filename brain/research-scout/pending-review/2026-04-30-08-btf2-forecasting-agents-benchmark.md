# BTF-2: Benchmark for Evaluating Strategic Reasoning in Forecasting Agents

## Source
arXiv:2604.26106 — "Evaluating Strategic Reasoning in Forecasting Agents"
Authors: Tom Liptay, Dan Schwarz, Rafael Poyiadzi, Jack Wildman, Nikos I. Bosse
Submitted: April 28, 2026

## Domain
Domain 2 — Quantitative Methods

## What It Is
BTF-2 (Bench to the Future 2) is a pastcasting benchmark of 1,417 questions with a frozen 15-million-document corpus enabling reproducible offline forecasting evaluation. It can detect Brier score accuracy differences as fine as 0.004. The authors built a composite forecaster that outperforms individual frontier models by 0.011 Brier score, with the edge coming primarily from pre-mortem analysis of blind spots and explicit black swan consideration. Key failure modes identified: models are systematically poor at assessing political/business leader intent and estimating whether stated commitments will be executed on.

## Why It Matters to This System
Two direct connections. First, BTF-2's offline evaluation methodology mirrors exactly what this system needs: reproducible forecasting benchmarks against historical events without contaminating future predictions. The 15-million-document frozen corpus approach is architecturally analogous to how quant-research-agent should backtest against resolved Polymarket markets — frozen, reproducible, no lookahead. Second, the pre-mortem technique (explicitly reasoning about where your forecast is most likely wrong before finalising) is a concrete prompt engineering improvement for the quant-research-agent template. The identified frontier model failure modes (leader intent, commitment execution probability) are category flags for Polymarket markets involving political actors — quant-research-agent should apply higher uncertainty priors to those market types.

## What to Do With It
New research direction: Add BTF-2 to reference library and incorporate two changes into quant-research-agent template: (a) add explicit "pre-mortem blind spot check" step before finalising any probability estimate; (b) flag political/business-leader-intent markets as higher-uncertainty category requiring elevated Brier score thresholds before accepting signal confidence.

Separately: the 0.011 Brier score improvement from ensemble > individual frontier model is directly consistent with RQ3.2 (crowd/elite divergence). Worth noting in RQ3.2 theoretical grounding file.

## Effort to Implement
Medium (1 day) — add to reference library, update quant-research-agent template, update RQ3.2 grounding notes.

## Urgency
This week — quant-research-agent will run RQ3.2 soon; having the pre-mortem technique available before that run improves output quality.

## Raw Notes
Key findings verbatim from abstract:
- "detects subtle accuracy differences (0.004 Brier score) and distinguishes where different agents excel—specifically between research versus judgment capabilities"
- Superior forecaster advantage: "pre-mortem analysis of its blind spots and consideration of black swans"
- Expert human forecasters identified systematic failures: assessing political/business leader motivations; evaluating probability leaders execute on stated commitments; modeling how institutional processes function

The benchmark is publicly available (pastcasting dataset with historical corpus). Could be used directly to evaluate this swarm's forecasting accuracy in Phase 2-3 before going live on fresh markets.
