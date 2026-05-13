# PMXT: "CCXT for Prediction Markets" — Unified Trading SDK + Free Historical Data Archive

## Source
https://github.com/pmxt-dev/pmxt — MIT-licensed Python library, v2.40.5 (May 9, 2026), 1.7k stars, 191 forks, 219 releases.
Free data archive: https://archive.pmxt.dev/Polymarket
Tutorial: https://agentbets.ai/guides/pmxt-python-library-tutorial/

## Domain
Domain 4 — Prediction Market Intelligence + Domain 6 — System Architecture

## What It Is
PMXT is an open-source unified API for trading and data access across 10+ prediction market exchanges (Polymarket Global, Polymarket US, Kalshi, Limitless, Metaculus, Smarkets, Hyperliquid, and more), modeled directly on CCXT. The free archive at archive.pmxt.dev provides hourly Parquet snapshots of Polymarket orderbook data with tick-level events from 2026-04-13 onward, millisecond timestamps, covering 110,828+ distinct markets.

## Why It Matters to This System
Our current setup uses a custom-built polymarket_tracker.db and bespoke Python scripts tied to Polymarket's API directly. PMXT offers three compounding advantages: (1) cross-platform signal comparison — Kalshi and Polymarket price divergence on the same event is a potential alpha source not currently tracked; (2) the free Parquet archive gives quant-research-agent access to tick-level historical data for backtesting without relying solely on our local DB; (3) unified API means Phase 6 order execution could support both Polymarket and Kalshi via one library, reducing integration surface. The MCP/Market Data Watch List in the task template explicitly flags this category as highest priority ahead of Phase 4-5.

## What to Do With It
Discuss with Oscar before proceeding — evaluate as: (a) supplementary data source for quant-research-agent backtests using the free Parquet archive, and (b) Phase 4-5 execution layer candidate to route limit orders via unified API. Check whether PMXT's Polymarket integration conflicts with or complements the existing monitoring system.

## Effort to Implement
Medium (1 day) — pip install pmxt + read integration-contract.md to confirm no sovereignty issues with MIT-licensed library.

## Urgency
This week

## Raw Notes
- `pip install pmxt`
- Private key required for Polymarket trading (fits wallet anonymity model — key stays local)
- Kalshi requires RSA key
- Archive data: hourly Parquet, 2026-04-13 onward, free
- Research papers (arXiv:2605.10400) are already using PMXT v2 archive for Polymarket empirical analysis at scale (13,115 resolved markets in 1 week)
- Recent velocity: v2.40.5 released May 9 2026, 219 total releases = actively maintained
- Not an MCP server but Python SDK; integration path is direct import into agent code
- File as type "tool_discovery" in brain/findings.json when Oscar approves
