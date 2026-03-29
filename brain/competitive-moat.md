# Competitive Moat

Last updated: 2026-03-28
Maintained by: Oscar (review quarterly)

---

## Purpose

This document exists so every agent understands what makes this
system genuinely different from competing tools before making any
build decision. Agents that don't understand the moat will build
things that erode it — duplicating what already exists in the
ecosystem rather than deepening what makes this system unique.

Read this before proposing any new agent, tool, or capability.
Ask: does this deepen the moat or does it duplicate what
170+ existing Polymarket tools already do?

---

## The Competitive Landscape

As of March 2026 there are 170+ tools in the Polymarket ecosystem.
The most relevant competitors in the smart money tracking space:

**Polycool** — tracks top 0.5% of wallets by win rate and PnL.
Real-time Telegram alerts. Free tier. Focused on alerting, not
analysis depth.

**HashDive** — Smart Score (-100 to 100) based on historical
performance, open trades, and stability. Whale tracking, candlestick
charts with RSI/MACD, insider finder for anomalous new wallet trades.

**PolyIntel** — Real-time Telegram alerts every 10 minutes.
Whale movement detection, insider activity scoring, portfolio tracking.

**Polysights** — 30+ custom metrics, AI-generated summaries,
insider finder flagging anomalous new wallet trades.

**PolyMaster** — AI analytics with whale tracking and predictive
modelling for advanced traders.

These tools are real competitors. They are well-funded, have
active user bases, and are improving rapidly. Do not pretend
they don't exist.

---

## What Every Competitor Does

All of the above share a common architecture:
- Real-time monitoring of large trades / whale movements
- Simple performance metrics (win rate, PnL, position size)
- Alert-first design: notify users when something happens
- Snapshot-based: what is happening right now

This is the commodity layer of smart money tracking.
It exists, it works, it is freely available.

---

## What This System Does Differently

### 1. Depth of ELO methodology

Competitors use simple win rate and PnL. This system uses
a multi-dimensional ELO with six behavioural modifiers:
- Kelly alignment score (are they sizing bets correctly?)
- Patience score (do they hold through volatility or panic?)
- Timing score (do they enter at good prices?)
- Risk-adjusted returns (Sharpe, not just raw PnL)
- Brier score calibration (are their probabilities accurate?)
- Composite skill score (multi-dimensional synthesis)

A trader with a high win rate but poor Kelly alignment is
being rated differently from a trader with a lower win rate
but excellent calibration. No competitor does this.

### 2. Scale of trader database

64,792 traders tracked with full position and trade history.
951,694 closed positions analysed. This dataset took months
to build and grows daily. A competitor starting today cannot
replicate this history — they can only start from now.

The historical depth is the moat. 18 months of ELO history
on 64k traders is a genuinely different product from
"who made the biggest bet this week."

### 3. Longitudinal tracking

This system tracks trader skill over time, not just
current performance. A trader who was elite 6 months ago
but has declined recently is tracked differently from a
trader whose skill is stable or improving. No competitor
tracks ELO trajectory — they show current score only.

### 4. Pre-resolution intelligence

The pre-resolution intelligence layer (built March 2026)
identifies where elite traders are positioned before markets
resolve. The divergence signal — where smart money consensus
differs significantly from market price — is not available
in any competing tool as of March 2026.

### 5. Self-improving architecture

The feedback loop (feedback-loop-agent, findings.json,
strategy-registry.md) means the system gets more accurate
over time. Competitors are static — their algorithms don't
improve from their own predictions. This system validates
every signal against actual outcomes and adjusts weighting.

### 6. Wash trading and bot filtering

The system is building explicit detection for wash traders
and automated bots that corrupt signal quality. Competitors
include wash traders in their leaderboards because they
don't filter for this. A clean, calibrated trader pool is
a more valuable signal source than a raw one.

---

## The Core Moat in One Sentence

Competitors tell you who bet big today.
This system tells you which traders have been demonstrably
skilled across hundreds of markets over 18+ months,
how their skill is changing, and where they are
positioned before the next resolution.

---

## What Agents Should Build

Capabilities that deepen the moat:
- Anything that improves ELO calibration
- Anything that cleans the trader pool (wash trading, bots)
- Anything that improves pre-resolution signal quality
- Anything that tracks trader skill trajectory over time
- Anything that validates signals against actual outcomes
- Category specialisation tracking (do specialists outperform generalists?)
- Informed trader detection improvements (Columbia 5-criteria model)

Capabilities that don't deepen the moat (don't build these):
- Simple whale alerts (Polycool already does this)
- Basic win rate leaderboards (HashDive already does this)
- Real-time price monitoring without ELO context
- Generic news sentiment analysis without trader signal integration
- Anything a 1-person team could replicate in a week

---

## Regulatory Risk Awareness

As of March 2026:
- Polymarket partnered with Palantir for AI trade surveillance
- Columbia/Haifa academic paper identified $143M in informed trading
- US lawmakers proposing legislation targeting prediction markets
- Israeli military reservist indicted for Polymarket insider trading
- Kalshi growing rapidly with CFTC oversight ($50B annualised volume)

Implications for build decisions:
- Anonymous wallet operation is correct and important
- Mullvad VPN before any trading activity (already planned)
- Do not build anything that creates a footprint linking
  trading activity to personal identity
- Kalshi integration is Phase 7 priority — regulatory
  risk concentration in a single platform is a vulnerability
- If Polymarket becomes inaccessible to UK users, Kalshi
  is the primary fallback (plan this in Phase 7)

---

## Backlog — Capabilities to Build When Appropriate

These are genuine gaps identified through competitive research.
They are not immediate priorities but should be built in order
as the system matures:

**Phase 3 (data integrity, before ELO validation):**
- RQ0.1: Wash trading contamination audit
- RQ0.2: Bot and automated trader detection

**Phase 3 (research questions):**
- RQ2.4: Do category specialists outperform generalists
  in their specialist categories? Track specialisation
  ratio per trader (% of trades in top 2 categories).

**Phase 4 (signal generation):**
- Informed trader detection upgrade: implement Columbia
  5-criteria model (cross-sectional bet size, within-trader
  bet size, profitability, pre-event timing, directional
  concentration) to replace simple fresh-wallet detection.
- Entry timing analysis: how quickly does market price
  respond to legendary trader position entry? This
  determines the practical value of the signal.

**Phase 5 (paper trading):**
- Arbitrage monitoring: track Polymarket/Kalshi price
  divergence on equivalent markets as an intelligence
  feed. $40M in documented arbitrage profits 2024-2025.

**Phase 4-5 (signal generation / paper trading):**
- Unusual Whales MCP: congressional trading feed as
  independent pre-resolution signal. Politicians trading
  defence stocks before military events, biotech before
  FDA decisions etc. Cross-validates elite trader consensus
  without relying on ELO system. API key required.
  unusualwhales.com/public-api

**Phase 7 (expansion):**
- Kalshi integration: full trader universe analysis,
  cross-platform signal correlation, regulatory fallback.
- Network analysis: graph-based wash trading detection
  using Columbia cluster methodology.
- News processing layer: real-time information aggregation
  for geopolitics and economics markets. Dual purpose —
  informs pre-resolution bet timing AND generates content.
  Same infrastructure serves both use cases. Build after
  signal quality is validated and category edge is clear.
- Unusual Whales MCP full integration: options flow, dark
  pool, institutional 13F filings as smart money signals
  for equities expansion. Same ELO analytical framework
  applied to options informed money flow.

---

## Review Schedule

Review this document quarterly or after any major
competitive development (new tool launch, regulatory
change, platform policy update). research-scout-agent
should flag competitive developments that affect this
document.
