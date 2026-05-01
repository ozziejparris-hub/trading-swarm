# US Political Market Signal Quality Watch

Created: 2026-05-01
Trigger: Polymarket US CFTC-regulated platform launch (April 28, 2026)
Review due: mid-June 2026

---

## Background

Polymarket launched a US-specific platform under CFTC regulation on April 28, 2026,
making prediction market trading legally available to US customers for the first time.
A $1M liquidity incentive program accompanied the launch to bootstrap participation.

Oscar is UK-based — direct participation in Polymarket US is not applicable.
However, the signal quality implications affect our research and Phase 6 strategy.

---

## The Sharp Money Influx Risk

US participants entering a previously US-excluded market will include a
disproportionate share of sophisticated bettors:
- Hedge funds with political intelligence operations
- Washington DC insiders with direct access to policy information
- Finance professionals with electoral research resources
- Professional forecasters who were previously blocked from participating

These participants are structurally sharper than the average offshore bettor who
previously dominated US political markets. If elite consensus accuracy on US political
markets was previously above the benchmark partly because these markets were
US-excluded, that edge may compress as institutional-grade US bettors enter the pool.

**Categories at risk:**
- US elections and primaries
- US federal policy (Fed rate decisions, legislative outcomes)
- US regulatory decisions
- US macroeconomic indicators

---

## Recommendation — 30-Day Signal Quality Review

Starting May 2026, flag all US political market categories for signal quality monitoring:

1. Establish baseline: ELO-weighted elite consensus accuracy on US political markets
   from the pre-launch period (before April 28, 2026) using polymarket_tracker.db
2. Track accuracy on the same categories through May and June 2026
3. Compare: if accuracy on US political markets has materially declined relative
   to non-US markets, the sharp money influx is measurable in the data

Review date: mid-June 2026 (approximately 6 weeks post-launch).

**Decision criteria at review:**
- Accuracy decline > 5 percentage points on US political vs baseline: downweight category
- Accuracy decline > 10 percentage points: exclude US political from Phase 6 market selection
- No material change: proceed with full category exposure

---

## Phase 3+ Upgrade Path — WebSocket API

Polymarket US Retail API includes 2 WebSocket endpoints (real-time order book
updates and trade feeds). Our current signal-agent uses polling on the Data API,
introducing latency equal to the polling interval.

Note for Phase 3 architecture planning: when market-builder-agent is designed,
evaluate WebSocket-based monitoring as the signal detection mechanism for
real-time order flow analysis. This would reduce signal latency from minutes
(polling) to near-real-time (seconds), which matters for markets approaching
resolution where sharp money moves quickly.

---

## Source

Research scout finding: brain/research-scout/approved/2026-05-01-08-polymarket-us-cftc-regulated-launch.md
Polymarket announcement: https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
