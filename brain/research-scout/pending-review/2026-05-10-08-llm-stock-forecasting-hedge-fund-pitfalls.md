# LLM Stock Forecasting from a Hedge Fund Lens: Six Practical Pitfalls

## Source
https://arxiv.org/abs/2605.05211 — "A Review of Large Language Models for Stock Price
Forecasting from a Hedge-Fund Perspective" (Zhang & Zhang, May 2026). arXiv q-fin.CP.

## Domain
Domain 5 — Equities and Futures Intelligence
Domain 2 — Quantitative Methods

## What It Is
Survey of LLM approaches to stock price forecasting organised from a practitioner hedge-fund
perspective. Covers sentiment from news/social media, financial report analysis, tokenised price
series, and multi-agent trading systems. Key contribution: an explicit taxonomy of six
"understated practical pitfalls" that cause academic LLM-finance results to fail in production.

## Why It Matters to This System
The six pitfalls map directly onto our quant-research-agent's validation responsibilities. Three
are already in our 7-sins checklist (lookahead, data snooping, survivorship bias). Three are
underweighted or absent: (1) Evaluation metric fragility — academic metrics (accuracy,
directional accuracy) don't correlate with trading profitability; (2) Illiquidity premia — LLM
sentiment alpha in small/illiquid equities largely disappears at institutional scale; (3)
Horizon design issues — train/test windows that don't reflect realistic rebalancing constraints
inflate apparent alpha. The survey's framing ("stress-test under realistic market frictions") is
identical in spirit to our DSR/PBO requirements but extends them to LLM-specific failure modes.

## What to Do With It
Add to reference library: brain/reference-library/ new file on LLM stock forecasting pitfalls.
Also: review quant-research-agent template to confirm evaluation metric pitfall and horizon
design are explicitly called out — these are not in the current 7-sins checklist.

## Effort to Implement
Low (< 1 hour) — reference library addition and template annotation.

## Urgency
This month — relevant when quant-research-agent moves to Phase 3 LLM-assisted signal research.

## Raw Notes
- Six pitfalls: (1) sentiment analysis fragility, (2) dataset/horizon design issues,
  (3) performance evaluation metric mismatch, (4) data leakage, (5) illiquidity premia,
  (6) predictability limits from market efficiency
- Sentiment fragility: NLP sentiment scores are brittle to domain shift; models trained on
  general text underperform on financial jargon
- Illiquidity premia: alpha found with LLM signals is concentrated in small-cap, high-bid-ask
  spreads — disappears for liquid assets; Polymarket is liquid so less relevant but worth noting
- Horizon design: train/test split must mirror actual rebalancing frequency; daily model
  evaluated on 1-min returns is a common error
- Perspective is hedge fund (institutional), but warnings translate to prediction market context
  where the equivalent is resolution-lag design — if you train on market prices 24h before
  resolution and test on 1h before, that's horizon leakage
