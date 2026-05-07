# PolyBench: Only 2 of 7 LLMs Achieve Positive Returns on Polymarket

## Source
https://arxiv.org/abs/2604.14199 — "PolyBench: Benchmarking LLM Forecasting and Trading
Capabilities on Live Prediction Market Data" (published April 2026)

## Domain
Domain 4 — Prediction Market Intelligence
Domain 2 — Quantitative Methods

## What It Is
PolyBench evaluates 7 state-of-the-art LLMs on 38,666 binary Polymarket markets across 4,997 events,
combining live order-book snapshots with real-time news streams. Metrics include directional accuracy,
Confidence-Weighted Return, APY, and Sharpe ratio using execution-realistic LOB simulation.

## Why It Matters to This System
Only MiMo-V2-Flash (17.6% CWR) and Gemini-3-Flash (6.2% CWR) achieved positive returns.
The other five models—including larger, higher-parameter models—lost money despite expressing high
stated confidence. This directly informs how our quant-research-agent should reason about market
positions: overconfidence is the key failure mode, not capability. Our ELO/Brier system already
tracks calibration — PolyBench validates that calibration is the right signal to chase.
The LOB-aware evaluation methodology is more rigorous than anything in our current backtest pipeline.

## What to Do With It
New research direction: quant-research-agent should study the MiMo-V2-Flash methodology (what made
it win) before Phase 2 begins. Specifically: how it handles uncertainty quantification and position
sizing relative to confidence. Add paper to reference library under prediction-market-intelligence.

## Effort to Implement
Low (< 1 hour to read and extract methodology insights; Medium if we adapt the LOB evaluation
approach for our backtest-agent)

## Urgency
This week — directly relevant to Phase 2 research design

## Raw Notes
- Code and dataset available at PolyBench GitHub repo (linked in paper)
- 36,165 total predictions made across 7 models
- Evaluation window: Feb 6–12, 2026; resolution through Feb 21, 2026
- Key failure pattern: high stated confidence + wrong direction = large losses
- MiMo-V2-Flash is an open-weight model from MIMO — worth checking for Tier 2 candidate status
- Gemini-3-Flash 6.2% CWR — cheaper cloud model outperforms larger expensive ones
- This is distinct from Prediction Arena (arXiv 2604.07355, filed 2026-05-03) — different paper,
  different methodology, different models tested
