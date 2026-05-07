# PredictionMarketBench: Execution-Realistic LOB Backtesting for Prediction Markets

## Source
https://arxiv.org/abs/2602.00133 — "PredictionMarketBench: A SWE-bench-Style Framework for
Backtesting Trading Agents on Prediction Markets" (February 2026)
GitHub: https://github.com/Oddpool/PredictionMarketBench

## Domain
Domain 2 — Quantitative Methods
Domain 4 — Prediction Market Intelligence

## What It Is
A standardised backtesting framework that replays historical limit-order-book and trade data
from prediction markets with maker/taker fee modeling and settlement risk. Provides an
execution-realistic simulator (not just price-series backtesting) with a tool-based agent
interface supporting both classical strategies and tool-calling LLM agents.

## Why It Matters to This System
Our backtest-agent currently validates Sharpe/DSR/PBO/Brier against the 7 sins checklist, but
lacks a LOB-aware execution simulator. PredictionMarketBench addresses exactly this gap: it
models the microstructure (spread, depth, maker/taker fees) that determines actual P&L on
Polymarket. Baseline results are instructive: Bollinger Bands earned positive P&L, the LLM
agent traded too aggressively and suffered settlement losses. This directly validates our
"limit orders only" hard rule — the LLM agent's losses were driven by market-order-style
aggression, not forecasting error.

## What to Do With It
Update agent template: backtest-agent should reference this paper's execution simulator design.
Specifically: add LOB-depth modeling and maker/taker fee accounting to backtest validation
criteria alongside the existing 7-sins checklist.

## Effort to Implement
Medium (1 day to review code and assess portability from Kalshi to Polymarket CLOB format)

## Urgency
This month — implement before Phase 4 paper trading begins

## Raw Notes
- Initial public release uses Kalshi data (4 episodes: Bitcoin daily high, NYC temp, sports)
- Kalshi and Polymarket both use CLOB format — architecture is directly portable
- Three episode types: cryptocurrency threshold, weather, sports (sports excluded by our hard rules)
- RandomAgent loses less than LLM agent due to lower trading intensity — matches our caution
- Paper explicitly models settlement risk (position held to resolution = no exit opportunity)
- Framework on GitHub: github.com/Oddpool/PredictionMarketBench
- SWE-bench-style = standardised episodes + deterministic replay = reproducible comparisons
