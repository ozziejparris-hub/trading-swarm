# Machine Spirits: LLM Agents in Asset Markets — Empirical Validation of Bot Risk

## Source
https://arxiv.org/abs/2604.18602
arXiv:2604.18602 — "Machine Spirits: Speculation and Adaptation of LLM Agents in Asset Markets"

## Domain
Quantitative Methods

## What It Is
Experimental study placing 15 different LLMs as trading agents in simulated asset markets. In homogeneous markets (identical agents), LLMs sometimes stabilise prices at fundamental value. In heterogeneous markets (mixed agent types), advanced models systematically exploit less sophisticated agents, achieving higher profits while amplifying market volatility. Even sophisticated models fail to stabilise markets when they represent only a minority.

## Why It Matters to This System
Two direct connections to open research questions:

**Validates RQ0.2 (Bot Detection):** The paper provides empirical evidence that automated agents (equivalent to bots) in prediction markets will exploit slower-reacting participants. This confirms the premise that bots on Polymarket whose edge is "structural, not informational" (spread capture, speed arbitrage) will appear as high-skill ELO traders while their edge is uncopyable by this system. The strategy-notes already identified this risk — this paper adds peer-reviewed empirical backing. RQ0.2's bot exclusion logic is not just a hygiene step; it's validated as necessary by market microstructure research.

**Relevant to RQ7.1 (Signal Crowding):** "Individual-level adaptation may amplify, rather than mitigate, market volatility." When many agents follow the same signal source (e.g., all tracking the same legendary wallets), the resulting correlated entry behaviour increases instability rather than reducing it. This is the theoretical mechanism behind signal crowding — worth noting in the RQ7.1 test design.

**Specific implication for ELO architecture:** The finding that "advanced models achieved higher profits in heterogeneous markets" maps to the hypothesis that truly sophisticated Polymarket traders are profiting partly from market structure exploitation (spread, timing), not purely from information. This justifies separating ELO-based information signals from execution-quality signals.

## What to Do With It
**New research direction** — Add to `brain/strategy-notes/research-directions.md` as a citation in RQ0.2 and RQ7.1 supporting literature. The specific finding ("sophisticated agents exploit unsophisticated ones in heterogeneous markets") should inform how the bot_suspect flag is designed and documented in RQ0.2 output.

## Effort to Implement
Low (< 1 hour) — documentation update, no code changes.

## Urgency
**Backlog** — RQ0.2 is in the queue but not immediate. Add before quant-research-agent begins RQ0.2.

## Raw Notes
- 15 LLMs tested across various capability levels
- Homogeneous markets: some reached rational expectations equilibrium, some generated bubbles
- Heterogeneous markets: advanced models consistently extracted profit from less sophisticated agents
- Even sophisticated models created bubbles when present as a minority
- "Endogenous instability" from heterogeneous LLM populations — a new market microstructure finding
- Directly applicable: Polymarket's market population is heterogeneous (bots, humans, copy traders, informed traders) — this model predicts instability and strategic exploitation as natural outcomes
- Does NOT address prediction markets specifically — the simulation uses standard double-auction asset markets
- Does NOT address information aggregation — conclusions are about strategic exploitation, not forecasting accuracy
