# Unlocking the Forecasting Economy: Comprehensive Polymarket Dataset 2020–2026

## Source
https://arxiv.org/abs/2604.20421 — "Unlocking the Forecasting Economy: A Suite of Datasets for
the Full Lifecycle of Prediction Market" (April 2026)
Active dataset: https://polymonitor.club

## Domain
Domain 4 — Prediction Market Intelligence
Domain 2 — Quantitative Methods

## What It Is
First publicly available comprehensive dataset covering the full lifecycle of Polymarket from
October 2020 to March 2026. Contains 770,880 market records, 943,548,464 fill-level trading
records, and 1,988,150 oracle-resolution events across 602,697 traded markets and 2,492,419
distinct trader addresses. Continuously maintained at polymonitor.club.

## Why It Matters to This System
Our polymarket_tracker.db is 1581 MB and tracks individual traders (53,140 traders, 951,694
closed positions). This dataset adds the fill-level microstructure layer we currently lack:
943M fill records means every individual trade, not just resolved positions. This enables
backtesting strategies based on order flow, intraday price dynamics, and LOB evolution —
dimensions unavailable in our current data. The 2,492,419 distinct trader addresses vs our
53,140 tracked traders shows we're covering approximately 2% of all market participants.

## What to Do With It
Monitor for 30 days before acting — first verify if polymonitor.club data is accessible and
whether its schema is compatible with our integration contract. If so, flag to Oscar as a
potential supplement to polymarket_tracker.db for Phase 4 backtest expansion.

## Effort to Implement
Medium (1 day to assess schema compatibility and data transfer; High if full integration
into the DB is needed)

## Urgency
This month — evaluate before Phase 4 paper trading design begins

## Raw Notes
- Dataset covers 602,697 traded markets (our DB covers ~53K traders' positions — much smaller scope)
- Fill-level data (943M records) enables intraday strategy backtesting not possible with our current data
- Case studies in paper: NBA outcome calibration, CPI expectation reconstruction
- Cross-source integration challenge: on-chain + off-chain data merged
- Continuously maintained (not a static snapshot) — active resource
- Oracle-resolution events (1,988,150 records) enable clean ground-truth resolution tracking
- polymonitor.club is the active endpoint — check availability and access terms before using
- Relevant papers to cross-reference: PolyBench (2604.14199) uses a similar data approach
