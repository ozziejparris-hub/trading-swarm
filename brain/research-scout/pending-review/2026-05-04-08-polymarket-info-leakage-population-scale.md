# Information Leakage at Population Scale: Polymarket 2020-2026

## Source
https://arxiv.org/abs/2605.00459 — "Information Leakage at Population Scale: An Evaluation of the Polymarket Insider-Relevant Subpopulation, 2020-2026"
https://arxiv.org/abs/2605.00493 — "ForesightFlow: An Information Leakage Score Framework for Prediction Markets" (companion methodology paper)

## Domain
Domain 4 — Prediction Market Intelligence

## What It Is
A 6-year empirical study of 12,708 Polymarket markets measuring systematic information leakage prior to resolution events using the ForesightFlow ILS-dl (Information Leakage Score, deadline variant). Key finding: post-2024 regulatory_formal markets show near-zero information leakage, while regulatory_announcement markets retain significant leakage. Only 0.7% of markets yielded computable ILS scores.

## Why It Matters to This System
Two direct connections:

1. **RQ3.2 (elite consensus vs market price):** The finding that regulatory_formal markets show near-zero leakage post-2024 is potentially significant — US political markets under CFTC regulation (launched April 28 2026) may fall into this category, meaning elite traders have less advance information advantage in that specific category. This reinforces the "US market signal quality watch" already in strategy-notes and suggests separating regulatory market categories in any elite-vs-market analysis.

2. **Category design for signal-agent:** The regulatory_formal vs regulatory_announcement split is a meaningful taxonomy. If signal-agent is monitoring price moves pre-resolution, it should apply different sensitivity thresholds by category type. Regulatory_announcement markets (earnings, FDA approvals) have higher leakage risk — signals there may be informed rather than noise.

The companion ForesightFlow paper's finding that all 24 documented Polymarket insider trading cases fell outside their original methodology's scope is a sobering reminder: simple price-move detection is insufficient for insider identification. Method limitations documented in code released publicly.

## What to Do With It
New research direction: propose to quant-research-agent to classify markets in polymarket_tracker.db by regulatory category (formal vs announcement vs other) before running RQ3.2. This is a pre-stratification step, not a new hypothesis — it improves existing research design.
Add both papers to reference library: brain/reference-library/prediction-market-coordination.md (append section on information leakage empirics).

## Effort to Implement
Low (< 1 hour) — pre-registration addition to RQ3.2 design, reference library update

## Urgency
This week — relevant to RQ3.2 pre-registration which is upcoming per priorities.md

## Raw Notes
Study covers 12,708 Polymarket markets, 2020–2026
ILS-dl uses hazard-decay baseline correction + Weibull duration modeling
Only 88 of 12,708 markets (0.7%) yielded computable scores — the 99.3% failure rate is due to resolution semantics, not computational problems
Post-2024 regulatory_formal markets: near-zero leakage (implies CFTC enforcement effect)
Regulatory_announcement markets: significant negative leakage values remain
ForesightFlow insider case inventory: 32 suspect markets, 1 analyzable under framework
Key methodological limitation: resolution-anchored proxies fail to distinguish informed vs noise
Code and market classification typology released publicly — could be adapted for polymarket_tracker.db
Murphy decomposition connection to proper scoring rules — aligns with Brier score framework already in use
