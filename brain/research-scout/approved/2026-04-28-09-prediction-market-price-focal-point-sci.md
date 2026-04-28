# Prediction Market Prices as Coordination Mechanisms — Signal Credibility Index

## Source
https://arxiv.org/abs/2604.24147
arXiv:2604.24147 — "Price as Focal Point: Prediction Markets, Conditional Reflexivity, and the Politics of Common Knowledge" (Maksym Nechepurenko)

## Domain
Prediction Market Intelligence + Quantitative Methods

## What It Is
Empirical analysis using 2024 U.S. presidential election data arguing that prediction market prices function as coordination devices rather than pure forecasts. Introduces a Signal Credibility Index (SCI) using microstructure metrics to predict when price movements gain behavioural traction. Key finding: "the most visible market produced the least accurate forecasts" — social authority and epistemic reliability systematically diverge.

## Why It Matters to This System
**Directly supports the core bet of RQ3.2:** The finding that high-visibility markets are less accurate (because they attract coordination-driven, not information-driven, trading) is exactly why following raw market price is insufficient. Elite traders who ignore the "focal point" function of market price and trade on private signals are the ones with genuine edge. Our ELO system is designed to identify exactly this population.

**Signal Credibility Index (SCI) methodology:** The paper introduces SCI as a composite of microstructure metrics predicting when a price signal carries epistemic weight vs. coordination weight. If the methodology is sound, this could become a filter in market-builder-agent's market selection logic — prefer markets where SCI is high (price reflects information, not coordination). This would reduce the noise from markets where elite positioning is a coordination play rather than a forecasting edge.

**Warning for signal timing:** The reflexivity argument implies that tracking and following elite positioning can itself become a coordination mechanism once the system is large enough — the very act of front-running elite moves contributes to the focal-point problem. Relevant for Phase 6 position sizing limits.

## What to Do With It
"Add to reference library: create brain/reference-library/prediction-market-coordination.md summarising SCI methodology and reflexivity argument. Note in research-directions.md under RQ3.2 that market selection should prefer high-SCI markets (epistemic, not coordination-driven). Flag reflexivity risk for Phase 6 position sizing discussion with Oscar."

## Effort to Implement
Medium (1 day — reference library entry + annotation to research-directions.md)

## Urgency
This month

## Raw Notes
- Uses 2024 US presidential election data — strong empirical basis for prediction markets specifically
- "Signal Credibility Index incorporates microstructure metrics" — specific metrics not fully described in abstract; full paper needed to assess implementability
- Conditional reflexivity concept: a market price becomes self-fulfilling if enough actors treat it as authoritative, even if it started as a forecast
- Cross-platform consensus mentioned as a predictor of SCI — Polymarket vs Kalshi vs Manifold price divergence may itself be a signal quality indicator
- Author: Maksym Nechepurenko — track this researcher for follow-up work
