# Polymarket CTF Exchange V2 Upgrade — Breaking API Changes

## Source
https://help.polymarket.com/en/articles/14762452-polymarket-exchange-upgrade-april-28-2026
https://docs.polymarket.com/changelog

## Domain
Prediction Market Intelligence + System Architecture

## What It Is
Polymarket is deploying a complete exchange overhaul on April 28, 2026 at ~11:00 UTC — roughly 21 hours from this filing. The upgrade includes new CTF Exchange contracts, a rewritten CLOB backend, a new collateral token (pUSD), and a fully incompatible v2 API.

## Why It Matters to This System
**IMMEDIATE RISK:** Any code in this repo that signs Polymarket orders or calls the CLOB API will break at cutover. Three specific breaking changes:

1. **EIP-712 domain version**: must change from `"1"` to `"2"`. V1-signed orders are rejected after cutover with no fallback.
2. **Pagination endpoints**: `GET /markets` and `GET /events` (offset-based) replaced by `GET /markets/keyset` and `GET /events/keyset` (cursor-based). Offset queries will break.
3. **POST /submit response**: no longer returns `transactionHash` in the immediate response — callers must poll `GET /transaction/{id}` for the hash.

The `market-builder-agent` template and any existing Polymarket API connector code must be updated before this agent goes live. The current system is not yet live (trading-swarm service not started), which is the only reason this is not a production incident. The migration window closes tomorrow.

The Polymarket SDK has a hot-swap mechanism that auto-migrates on latest versions — if `market-builder-agent` uses the official Python SDK pinned to latest, the pagination and submit changes may be handled automatically. The EIP-712 domain version bump requires explicit code change regardless.

## What to Do With It
**Discuss with Oscar before proceeding** — audit `orchestrator/task_templates/` for any market-builder-agent template that includes Polymarket API call patterns. Update to v2 SDK and v2 endpoint patterns before this agent is ever spawned. The official migration guide is at https://docs.polymarket.com/v2-migration

Secondary: check `scripts/spawn_agent.sh` for any hardcoded Polymarket API references.

## Effort to Implement
Medium (1 day) — SDK migration plus template audit. Low risk if using official SDK on latest; higher risk if any code manually constructs EIP-712 signatures.

## Urgency
**NOW** — cutover is April 28, 2026 ~11:00 UTC (tomorrow)

## Raw Notes
- New collateral token: pUSD (replacing USDC)
- Faster order matching in new CLOB backend
- Smart contract wallet support added
- New issue filed against nautilus_trader re: CTF Exchange V2 breaking changes (github.com/nautechsystems/nautilus_trader/issues/3844) — confirms third-party integrations affected
- Polymarket API previously geoblocked in US; now available US-side as of early 2026 — broader API audience makes this upgrade more disruptive
- Source: bitcoin.com/news, help.polymarket.com, github.com/nautechsystems
