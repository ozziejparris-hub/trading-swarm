# Quantitative Research Directions

## Purpose
This file gives the quant-research-agent directional nudges
before starting any research session. These are open questions
to investigate, not frameworks to copy. Your job is to find
which approaches have measurable edge specifically in prediction
markets — most traditional equity research methods will not
transfer directly without adaptation.

Read this before starting any new research phase. Add your
findings back to this file over time so it compounds.

---

## Direction 1 — Trader Behaviour Factors
Prediction markets are driven by people, not algorithms.
Understanding trader behaviour patterns may reveal edge.

Questions worth investigating:
- Do high-ELO traders (>1800) show measurable momentum?
  i.e. when they enter a position, does price continue moving
  in their direction for a predictable window?
- Is there a "smart money" timing signal — do legendary traders
  (ELO >2175) consistently enter earlier than the market moves?
- Do elite traders cluster around specific market categories
  (geopolitical, economic, sports) or are they generalist?
- What is the relationship between position size and ELO score?
  Do better traders size up on higher-conviction markets?
- Is there a meaningful difference between traders who enter
  early vs traders who enter late in a market's lifespan?

Relevant data: traders table (ELO scores), trades table
(timestamps, sizes), markets table (resolution dates)

---

## Direction 2 — Market Pricing Factors
Prediction market prices may be systematically mispriced
in detectable, exploitable ways.

Questions worth investigating:
- Are markets with low elite trader participation consistently
  mispriced relative to markets with high participation?
- Do prices overreact or underreact to external news events?
  Is there a mean-reversion opportunity after sharp moves?
- Are tail-risk markets (trading below 5 cents or above 95)
  systematically over or underpriced relative to true probability?
- Do related markets (same topic, different outcomes) price
  correlated events consistently or are there arbitrage gaps?
- Is there a time-decay pattern — do prices drift toward
  50 cents or toward resolution as expiry approaches?

Relevant data: markets table (prices over time),
trades table (volume patterns), positions table (P&L outcomes)

---

## Direction 3 — Momentum and Timing Factors
Price movement patterns may be predictable in short windows.

Questions worth investigating:
- After a sharp price move (>10% in 24 hours), what is the
  probability of continuation vs reversal?
- Is there a volume signal — does high volume confirm moves
  or is it a contrarian indicator in prediction markets?
- Do prices move predictably around external event dates
  (elections, Fed meetings, economic releases)?
- Is there an opening/closing pattern — do prices behave
  differently when a market first opens vs final 20% of life?
- Does momentum from one related market predict moves
  in correlated markets with a measurable lag?

Relevant data: trades table (timestamps, prices, volumes)

---

## Direction 4 — Quality and Calibration Factors
How well does the existing system predict outcomes?
Improving calibration is the highest-value near-term research.

Questions worth investigating:
- What is the current Brier score of ELO-based predictions
  across all resolved markets? (Phase 1 priority)
- Which ELO ranges are best calibrated and which are worst?
  Are legendary traders more or less calibrated than elite?
- Are predictions better calibrated for certain market types
  (political vs economic vs sports vs crypto)?
- Does calibration improve or degrade as markets approach
  resolution date?
- What simple adjustments to ELO-based probability estimates
  would most improve Brier score?

Relevant data: traders table (ELO), markets table
(resolution outcomes), positions table (prediction vs outcome)

---

## Direction 5 — Composite Scoring
Combining multiple signals may outperform any single factor.

Questions worth investigating:
- What combination of trader behaviour + price momentum +
  calibration factors produces the strongest predictive signal?
- Is a simple equal-weighted composite better or worse than
  a weighted composite optimised on historical data?
- Does adding more factors improve or degrade signal quality?
  At what point does complexity hurt performance?
- Can a single composite score reliably rank markets by
  expected edge from highest to lowest?

Note: build single-factor models first and validate each
before attempting composite models. Composites built on
unvalidated factors compound errors, not signal.

---

## Direction 6 — Risk and Correlation Factors
Understanding portfolio-level risk matters as much as
finding individual market edge.

Questions worth investigating:
- How correlated are related prediction markets?
  (e.g. do US election state markets move together?)
- What is the historical maximum drawdown of following
  elite trader signals without position sizing rules?
- Does Kelly criterion position sizing improve risk-adjusted
  returns vs flat position sizing?
- Are there market categories that act as natural hedges
  against each other?
- What is the tail risk profile — how often do high-confidence
  signals (multiple legendary traders converging) fail?

Relevant data: positions table (P&L, drawdowns),
markets table (categories, correlations)

---

## Direction 7 — Reinforcement Learning for Position Sizing
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: can an agent learn optimal position sizing
by treating each trade as a sequential decision with a reward
signal, rather than using fixed Kelly criterion rules?

Questions worth investigating:
- Can a simple RL agent learn to size positions better than
  fixed Kelly criterion on your Polymarket data?
- What reward signal best captures trading quality —
  pure P&L, risk-adjusted returns, or Brier improvement?
- Do legendary traders (ELO >2175) implicitly follow
  Kelly-optimal sizing, or do they systematically deviate?
- Is there a detectable sizing pattern before high-conviction
  markets vs uncertain markets?

Start simple: Q-learning with discrete position sizes
(small/medium/large) before attempting deep RL.
Validate each step with backtest-agent before proceeding.

---

## Direction 8 — Inverse Reinforcement Learning
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: what objective function are your best
traders actually optimising for? It may not be pure P&L.

Your legendary traders (ELO >2175) are expert demonstrations.
IRL attempts to recover their implicit reward function from
observed behaviour — position sizing, entry timing, market
selection, exit decisions.

Questions worth investigating:
- Do elite traders optimise for Sharpe ratio, pure returns,
  or something else entirely?
- Is there a detectable difference between what legendary
  traders optimise vs elite traders (ELO 1800-2175)?
- Can the inferred reward function be used to score new
  markets before entering — "would a legendary trader
  take this position?"

Note: this is advanced research. Do not start here.
Complete Directions 1-4 first. IRL requires clean
behavioural data from completed markets only.

---

## Direction 9 — Regime Detection
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: do your ELO signals and quant models
remain valid across different market regimes, or do they
degrade when market dynamics shift?

Questions worth investigating:
- Are there detectable regime shifts in Polymarket —
  periods where elite trader signals stop predicting outcomes?
- Do certain market categories (political vs economic)
  have different regime characteristics?
- Can a Hidden Markov Model detect regime changes in
  real-time before signal quality degrades?
- Should position sizing or signal thresholds adjust
  dynamically based on detected regime?

This protects your system from deploying strategies
in conditions where they no longer have edge.


## What Has Already Been Investigated
(Update this section as research completes)

- Nothing completed yet. Phase 1 (Brier score calibration)
  is the starting point.

---

## What Has Failed or Been Ruled Out
(Update this section as experiments conclude)

- Nothing ruled out yet.

---

## Compounding Notes
As the quant-research-agent completes phases, add key findings
here as one-line summaries so future research sessions start
with accumulated knowledge rather than from zero.

Example format:
- 2026-03-01: ELO >2175 traders show 340ms average entry
  advantage over market price movement. See phase-1-results.md
