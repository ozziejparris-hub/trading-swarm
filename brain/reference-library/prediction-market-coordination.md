# Prediction Market Coordination Theory — Why Markets Fail and Where Edge Exists

**Audience:** quant-research-agent, market-intelligence-agent, signal-agent. Read when designing signal thresholds, selecting markets, or interpreting divergence between elite positions and market price.

---

## Markets as Coordination Devices, Not Pure Forecasts
**Source:** arXiv:2604.24147 — "Price as Focal Point" (Nechepurenko)

### The Core Finding

Prediction market prices function as **coordination devices** as much as forecasting mechanisms. When a price becomes socially authoritative — widely visible, widely trusted — traders anchor to it independent of their private information. The result: high-visibility markets are *less* accurate than low-visibility markets because they attract coordination-driven trading that pushes prices toward social consensus rather than epistemic truth.

**Empirical basis:** 2024 US presidential election prediction markets. The most visible market (highest volume, widest coverage) produced the least accurate forecasts across the election period.

### Signal Credibility Index (SCI)

A composite microstructure metric predicting when a price movement carries **epistemic weight** (reflects private information) vs **coordination weight** (reflects traders anchoring to the current price as a focal point).

- High SCI = price movement is information-driven → signals from this market are more reliable
- Low SCI = price movement is coordination-driven → elite positioning may be noise, not signal

**Implication for market selection:** Prefer high-SCI markets for research and signal detection. Low-SCI markets may show apparent elite divergence from price that is actually a coordination artefact, not an informational edge.

**Cross-platform SCI proxy:** When Polymarket and Kalshi price the same event differently, at least one is coordination-driven. Large cross-platform divergence is a potential SCI signal — the market where elite-to-crowd divergence is highest is more likely to be the epistemically-driven one.

### Reflexivity Warning for Phase 6

The reflexivity argument: once our system is large enough that following elite moves moves the market, the system itself becomes a coordination mechanism. The very act of front-running elite positioning contributes to the focal-point problem at scale.

**Implication for Phase 6 position sizing:** There is a scale limit above which following elite signals degrades their quality by making the following visible. Position sizing limits and execution timing both affect this. Do not ignore reflexivity when setting Phase 6 capital limits.

---

## Information Aggregation Failures and the ELO Premise
**Source:** arXiv:2604.20050 — "Information Aggregation with AI Agents" (Galanis)

### The Controlled Experiment

LLM agents placed as traders in a prediction market where each agent receives a private signal. Measures information aggregation quality by log error of final price. Key findings:

1. **Aggregation works in simple structures** — when information is straightforward, markets efficiently aggregate it
2. **Aggregation breaks with complexity** — more heterogeneous information structures degrade aggregate accuracy
3. **Smarter agents outperform** — the LLM-agent equivalent of our ELO hypothesis
4. **Performance feedback worsens aggregation** — providing accuracy feedback to agents degrades both aggregation quality and profitability

### Why This Validates the ELO Premise

"Smarter AI agents outperform at aggregation and generate higher profits" — this is experimental support for the core system bet: high-ELO traders (empirically better-calibrated forecasters) aggregate information more effectively than the crowd. The market fails precisely because most traders are not this good.

**Complexity-breakdown implication:** Markets with many unsophisticated traders fail to aggregate complex signals (geopolitical events, multi-step policy decisions) — this is where the exploitable gap for elite forecasters is largest. Calibrate market selection toward complex, low-visibility markets.

### Critical Finding for Feedback-Loop-Agent Design

**Performance feedback paradox:** When agents receive their own accuracy scores and use them to update their behaviour, aggregate quality *falls*. The mechanism: agents over-anchor on past performance rather than current private signals.

**Direct implication:** feedback-loop-agent must inject historical accuracy data as **soft Bayesian priors** on signal weighting, not as hard multipliers. Raw accuracy scores fed back as hard weights will degrade signal quality, not improve it. This was already noted in lessons-learned.md (2026-04-29) — this reference provides the theoretical backing.

---

## Design Rules Derived From These Papers

1. **Market selection:** Prefer low-visibility, high-complexity markets where coordination effects are weakest and private information aggregation is highest.

2. **SCI as filter:** When cross-platform divergence is available (Polymarket vs Kalshi on same event), prefer the market with higher ELO-elite-to-crowd divergence as the epistemically-driven signal source.

3. **Feedback loop design:** Historical accuracy data into signal weighting must be soft prior, not hard weight. Do not hard-multiply signal confidence by feedback-loop accuracy percentages.

4. **Phase 6 scale limit:** Monitor for reflexivity signs — if following elite signals moves the market price before position entry is complete, the system has reached the coordination threshold. Reduce position size or shift to earlier entry signals.

5. **RQ3.2 design note:** When testing elite consensus vs market price accuracy, prefer markets that were low-visibility at time of signal — high-visibility markets will understate the edge because coordination has already partially closed the gap.

---

## Quick Reference

| Concept | Implication |
|---------|-------------|
| High-visibility = low accuracy | Prefer quiet, low-volume markets for signal work |
| SCI high = epistemic price movement | Trust elite divergence more |
| SCI low = coordination price movement | Be skeptical of apparent edge |
| Complexity → aggregation breakdown | Geopolitics/macro > sports/crypto for ELO edge |
| Feedback → degraded aggregation | Soft priors only in feedback-loop-agent |
| Reflexivity at scale | Position size limits matter at Phase 6 |
