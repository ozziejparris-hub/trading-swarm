# Polymarket Resolution-Zone Price Dynamics: Terminal-Jump and Boundary Depth Asymmetry

## Source
https://arxiv.org/abs/2605.10400 — "Resolution-Aware Perpetual Futures on Binary Prediction Markets: An Empirical Risk-Design Framework Using Polymarket Data" (May 2026). arXiv q-fin. Uses PMXT v2 archive, 13,115 resolved Polymarket markets, calendar week 2026-04-21 to 2026-04-27.

## Domain
Domain 4 — Prediction Market Intelligence

## What It Is
The paper analyses Polymarket orderbook microstructure during resolution zones using tick-level data on 13,115 markets. Key empirical findings: (1) "boundary depth asymmetry" — the orderbook is structurally thinner on one side as markets approach resolution, (2) "terminal-jump bad-debt" — prices exhibit non-continuous jumps during the final minutes before resolution that standard margin models cannot accommodate, (3) standard basis-only funding fails for bounded-event underlyings. The paper's stated purpose is perpetual futures design, but the microstructure data is independently valuable.

## Why It Matters to This System
Our current strategies (STR-001, STR-002) treat Polymarket prices as approximately continuous. This paper provides empirical evidence that prices in resolution zones behave discontinuously — thin books, large jumps. For a trading system, this implies two things: (1) positions held through the final resolution window face elevated slippage and jump risk not captured by normal backtesting; (2) the "boundary depth asymmetry" pattern — that one side of the book thins predictably before resolution — may itself be a detectable signal. If YES votes systematically thin before true-resolving markets and NO votes thin before false-resolving markets, this is measurable edge.

## What to Do With It
New research direction: propose to quant-research-agent that RQ_NEW test resolution-zone orderbook thinning as a pre-resolution signal. Specifically: in the 24 hours before resolution, does the YES/NO depth ratio predict the resolution direction? Pre-register hypothesis before running. Also: add a rule to backtest agent — any strategy holding positions into the final resolution window must be flagged for this slippage risk.

## Effort to Implement
Medium (1 day) — requires Polymarket orderbook data (available via PMXT v2 archive, see companion finding 2026-05-12-08-pmxt-unified-prediction-market-sdk-free-data-archive.md).

## Urgency
This month

## Raw Notes
- Dataset: PMXT v2 archive, April 21-27 2026, 13.7 billion tick events, 110,828 markets raw, 13,115 after quality filter
- Empirical finding: "terminal-jump magnitude" is predictable but large
- Empirical finding: "boundary depth asymmetry" passes their structural test
- Three of five materiality tests failed (suggesting the derivative design is premature)
- Directly tradeable implication: orderbook thinning as a signal is NOT in our current strategy notes — this is a new direction
- Exit timing rule: strategy templates should include a flag for whether the strategy ever holds positions into the final 24h before resolution, and if so, what the risk adjustment is
- PMXT v2 archive (archive.pmxt.dev) is the data source needed to replicate this analysis on our own question
- Note: the paper itself is rated "non-deployable" for its futures design, but the microstructure findings are empirical and replicable
