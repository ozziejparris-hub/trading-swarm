# Session Summary: Server Setup 19 — 2026-06-03

## What Was Fixed

### 1. geo_elo_active Recency Bug — Wrong Timestamp Source
- Was using last **resolved** trade timestamp; active traders with unresolved recent positions showed as dormant
- Fixed to use last **any** geo trade timestamp (resolved or pending)
- Impact: 0xecaa8806 corrected from 54% decay to 94.4% (traded June 2); geo_elo_active now 2255

### 2. geo_elo_active Datetime Parsing Bug — Silent Failure
- `datetime.fromisoformat()` silently failed on SQLite space-separated timestamps (`'2026-05-12 07:31:01'`)
- Added `.replace(' ', 'T')` normalisation before parsing
- Added visible error logging — silent `None` returns replaced with explicit log output

### 3. geo_elo_active Thin-Trade Skip Bug — 2032 Traders Left NULL
- Thin-trade guard (< 5 qualifying trades after price filter) was silently skipping traders who had `geo_elo` but few recent geo trades, leaving `geo_elo_active = NULL`
- Added a separate second pass over all traders with `geo_elo IS NOT NULL`, independent of trade count
- Result: 2032 traders now updated per recalculation (up from 452)

### 4. STR-003 P&L Filter Corrected
- Replaced `realized_pnl > 500` with `realized_pnl != 0.0 AND realized_pnl > -100000`
- Original threshold incorrectly excluded directional traders with modest or negative P&L from genuine market losses
- Example: 0xecaa8806 (geo_elo 2389, 74.4% win rate) was excluded due to -$50K from 2024 election directional losses — not an LP artifact
- Updated in `signal-agent.md` and `integration-contract.md`

### 5. trade_result Backfill for Geo/Elections Markets
- `evaluate_new_trader_results.py` only processes `is_flagged=1` traders; newly reclassified markets were never evaluated
- After category backfill reclassified 11K markets, 6118 traders had pending `trade_result` on 672 resolved geo markets
- New script `backfill_trade_results_geo.py` evaluated 756,484 trades: 267K won, 489K lost, 0 invalid — for 738 traders
- `geo_resolved_trades_count` updated for all affected traders

### 6. 229 ARB_BOT Wallets Excluded
- Jan 12 2026 factory batch: 33 wallets in 8 clusters, identical metrics, 24-minute creation window
- Today's live factory batch: 139 wallets created 2026-06-03 within 16.7 minutes
- May 17 factory batch: 85 wallets
- Perfect arb symmetry trader 0x8e59d10d: 336/336 YES/NO split, 1674 markets
- LP_ARTIFACT 0xf4034309: near-symmetric market maker
- 3 Jan-12 wallets with >500-trade single-market concentration also excluded

### 7. findings.json Cleaned
- Stale strategy-overdue flags marked `EXPIRED`
- Superseded LEGENDARY finding marked `SUPERSEDED`
- Phase 5 Gate 2 correctly reflects 2/3 valid HIGH confidence findings

### 8. feedback.json Restored + Template Hardened (3rd Corruption Incident)
- Restored from git commit `d529c0a`
- Root cause: `research-scout-agent.md` template not guarding against full-file overwrite
- Template now explicitly forbids full-file overwrite; mandates append-only to `scout_cycles` key

## Key Research Findings

- **ELO vs market price on contested markets (0.35–0.65):** ELITE 81.4%, LEGENDARY 79.2%, QUALIFIED 69.6% vs market baseline 50.3%. Registered as HIGH confidence finding `2026-06-03-ELO-VS-MARKET-001`. Phase 5 Gate 2 remains 2/3 (this finding may be the third once formally validated).
- **Time-series stability is broken in 2025-H2:** 2025-H2 accuracy 25% (n=20), 2026 accuracy 54.3% (n=1235) on hardest markets (0.35–0.65 band). Edge is NOT temporally stable — 2025-H2 traders were systematically wrong. Disqualifies using pre-2026 data for signal calibration.
- **Difficulty bucketing:** accuracy degrades as markets get harder. 0.20–0.80 band: 63.4%. 0.45–0.55 band: 52.4% vs 48.0% market baseline. Modest but real edge on hardest markets.
- **comprehensive_elo formula bias confirmed:** 2.3× accumulation advantage for near-certain market specialists over contested-market specialists with identical skill. ROI-based `actual_score` rewards volume on easy markets.
- **geo_elo formula is correct** (uses `expected=price`, penalises easy-market losses more). Bias is specific to `comprehensive_elo`.
- **STR-003 qualifying pool:** 11 traders after all fixes. 0xecaa8806 is the only active 2026 LEGENDARY trader (traded June 2, geo_elo_active 2255).

## Key Decisions

- **comprehensive_elo kept for infrastructure only** — bot detection, Pool B qualification, STR-004. Not used for signal generation at LEGENDARY tier.
- **geo_elo_active is the correct signal qualification metric** — base `geo_elo` preserved for research integrity.
- **P&L filter targets LP artifact signatures only** — exact zero and < -$100K. Directional losses from real positions are not excluded.
- **ARB_BOT detection should be automated as RQ0.2** — today's manual audit found 229 wallets across multiple factory batches. Automation needed.

## Pending — Action Next Session

1. **URGENT: comprehensive_elo formula bias fix (Issue B)** — pre-registration required before any formula changes. Needs: formal pre-registration in `brain/strategy-notes/`, new formula design (difficulty-weighted K factor or price-normalised `actual_score`), full recalculation, validation against contested-market accuracy. Multi-session piece of work. Start with pre-registration.

2. **RQ0.2 automated bot detection** — today's manual audit found 229 ARB_BOT wallets. Need automated detection script: identical metric clusters created within 60-minute windows, perfect YES/NO symmetry, single-market concentration > 500 trades. Add to `daily_maintenance.py` or as weekly cron.

3. **0x2aacd459 trade_result pending investigation** — 114 of 125 resolved geo trades still showing pending after backfill. Markets likely resolved with `winning_outcome='unknown'` or ambiguous outcomes. Trader has $3,492 P&L and government shutdown/budget expertise — worth resolving.

4. **geo_elo LEGENDARY pool dormancy** — all Dec 2025 Haley specialists last traded 153 days ago. 0xecaa8806 is the only active 2026 trader. Monitor Pool C traders approaching 2175 threshold (0xb6fa57 at 2087, 0xfe2d0b at 1531).

5. **Training-librarian file cleanup** — `findings.json`, `decisions/`, and `brain/` directories need periodic cleanup of stale/expired entries. Schedule as monthly librarian task.

6. **Legendary scan still running** — `screen -r legendary_scan`; events_so_far=46,784 as of this morning. Should complete June 4.

7. **Contested market accuracy pre-registration** — difficulty-bucketed accuracy analysis (0.20–0.80 through 0.45–0.55 bands) must be formally pre-registered as `RQ-CONTESTED-001` before any formula changes. Prevents post-hoc methodology selection.

8. **Phase 5 Gate 2 third finding** — currently 2/3. Best candidate: run full `geo_elo` accuracy test on 2026 markets only (not contaminated by 2025-H2 25% result) once more 2026 markets resolve.

9. **Integration contract update** — v1.9 documents `market_category` backfill as running via `verify_market_titles.py` daily, but actual backfill was one-time via `backfill_market_categories.py`. Needs correction. Also needs `geo_elo_active` bug fixes documented in Section 8 changelog.
