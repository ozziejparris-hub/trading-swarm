# Information Aggregation with AI Agents in Prediction Markets

## Source
https://arxiv.org/abs/2604.20050
arXiv:2604.20050 — "Information Aggregation with AI Agents" (Spyros Galanis)

## Domain
Quantitative Methods + Prediction Market Intelligence

## What It Is
Controlled experiment placing LLM agents as traders in a prediction market where each agent receives a private signal. Measures information aggregation quality by log error of the final price. Key findings: aggregation works in simple information structures, breaks down with complexity, smarter agents outperform, and — counterintuitively — performance feedback worsens both aggregation quality and profitability.

## Why It Matters to This System
**Validates the ELO approach:** The paper's finding that "smarter AI agents outperform at aggregation and generate higher profits" is the LLM-agent equivalent of our ELO hypothesis. Our system bets that high-ELO traders (empirically smarter/better-calibrated forecasters) aggregate information more effectively than the market as a whole. This paper provides controlled experimental support for that premise.

**Critical finding for feedback-loop-agent design:** "Performance feedback paradoxically worsens both aggregation quality and profitability." In our architecture, the feedback-loop-agent provides performance signals back to the trading system. If this finding generalises, feeding raw accuracy metrics back into signal-weighting could degrade signal quality rather than improve it. The mechanism matters: agents who receive feedback may over-anchor on past performance rather than current private signals. This should inform how feedback-loop-agent injects historical performance data — as a soft prior rather than a hard weight.

**Relevant to RQ3.2 test design:** Our hypothesis is that elite consensus outperforms raw market price precisely because elite traders are better at higher-order reasoning about other traders' knowledge. This paper shows that "increasing information complexity has a significant negative impact" on aggregate accuracy — consistent with the idea that markets with many unsophisticated traders fail to aggregate complex signals, leaving an exploitable gap for elite forecasters.

## What to Do With It
"New research direction: add note to RQ3.2 hypothesis file in strategy-notes — this paper provides theoretical grounding. Also note in feedback-loop-agent template: avoid injecting raw accuracy feedback as hard weights; use as soft Bayesian prior to prevent over-anchoring."

## Effort to Implement
Low (< 1 hour — annotation to existing files only)

## Urgency
This month

## Raw Notes
- Experiment uses controlled LLM trading in simulated prediction market — not Polymarket data, controlled setting
- "Cheap talk communication, market duration adjustments, and strategic prompting produce no meaningful effects" — consistent with our focus on position data over discourse signals
- The complexity-breakdown finding suggests that markets with more heterogeneous information structures (e.g., geopolitical events with many private information sources) are harder to predict — calibrate market selection criteria accordingly
- Paper does not test ELO-style persistent skill measurement, but the "smarter agent" proxy is the closest available analogue in controlled conditions
