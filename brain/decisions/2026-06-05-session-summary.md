# Session Summary: Server Setup 21 — 2026-06-05

## What Was Fixed

### 1. CopyTradeDetector Lazy-Init (OOM Kill Root Cause)
- `UnifiedELOSystem.__init__` was eagerly instantiating `CopyTradeDetector`, which built an O(n²) correlation matrix over all traders at startup
- This triggered a 56+ min runtime during daily maintenance and caused OOM kills before `apply_full_elo_modifiers` could complete
- Fixed to lazy-init: correlation matrix only computed when `_load_network_data()` is explicitly called

### 2. apply_full_elo_modifiers executemany Fix
- 15,000 individual `UPDATE` + per-row retry loops replaced with a single `executemany` + commit-level retry
- Runtime: 56 minutes → 3.5 seconds
- Daily maintenance now completes cleanly in ~2.4 hours

### 3. Positions Composite Index
- `CREATE INDEX idx_positions_status_trader ON positions(status, trader_address)` added
- Eliminates temporary B-tree sort on 3.75M rows during `_load_pnl_data` GROUP BY

### 4. fast_resolution_check.py CLOB Stale Market Second Pass
- Gamma 20K cap was missing markets with `resolution_date` older than late-2025
- New second pass queries CLOB API for markets where `resolution_date > 7 days ago` and `resolved=0`
- Limit 200/run; runs after the existing Gamma bulk pass

### 5. STR003-006 López Aliaga Market Category Fixed
- Market category was `Unknown`; corrected to `Elections`
- 1 market record and 3,946 trade records updated

### 6. Automated ARB_BOT Detection
- `scripts/detect_arb_bots.py` created with three detection patterns:
  - Pattern A: identical metric clusters (same ELO / win-rate within tight tolerances)
  - Pattern B: symmetric arb — YES/NO mirror positions, threshold 3%
  - Pattern C: single-market concentration
- Added to `daily_maintenance.py` as non-blocking Step 2
- 2 new ARB_BOT wallets excluded on first run: `0xa7a52f`, `0xf28360`

### 7. Codebase Audit and Cleanup
- 67 orphaned / superseded / one-time scripts archived to `scripts/archive/` (not deleted)
- 3 vestigial DB columns dropped: `geo_elo_oos`, `accuracy_pool`, `copyable_edge`
- `accuracy_pool` re-creation code disabled in `update_research_exclusions.py`
- `behavioral_modifier` conflict resolved: `integrate_behavioral_elo.py` disabled in `system_observer.py` — silently discarded by `apply_full_elo_modifiers.py`; intentional until RQ-CONTESTED-001 July 2026
- `wash_trade_suspect` dead writer documented

### 8. Trading-Swarm Crossover Audit
- `integration-contract.md` bumped to v2.1:
  - `accuracy_pool` + `geo_elo_oos` documented as dropped columns
  - Section 6c corrected: `verify_market_titles.py` does not backfill categories
- `strategy-registry.md`, `runbook.md`, `findings.json` updated to reference `detect_arb_bots.py` instead of archived scripts

### 9. RQ-CONTESTED-001 Pre-Registered
- Difficulty-weighted `comprehensive_elo` formula change formally pre-registered in `brain/strategy-notes/` before any implementation
- Rerun date: July 1, 2026 (needs ~30 qualifying 2026 contested markets; currently ~10)

### 10. 0x2aacd459 Investigation — System Correct
- `geo_elo` 1,548, `geo_accuracy_pool` 1, `directionality` 0.958
- 372 unresolved geo trades confirmed to be active open positions, not a data error

## Key Research Findings

- **Phase 5 Gate 2: MET — 3/3 HIGH confidence findings** (feedback-loop Run #10)
  - `2026-06-05-CONTESTED-ACCURACY-2026-001`: QUALIFIED tier 66.3% on 2026 contested markets (n=101), +11.1pp above market baseline — Gate 2 qualifying finding
  - `2026-06-05-POOL-C-GEO-FULL-2026-001`: Pool C 70.7% on all 2026 geo/elections markets (n=444)
  - LEGENDARY tier collapses to 49.2% on contested markets — confirms `comprehensive_elo` contamination, formally documented
- Maker/taker backfill completed: 10,000+ trades labeled, all confirmed takers (0 makers)
- Daily maintenance now completes cleanly in ~2.4 hours (was OOM-killing mid-run)

## Key Decisions

- **`comprehensive_elo` formula change deferred to July 1** — RQ-CONTESTED-001 pre-registration filed; insufficient 2026 contested market data until then
- **`behavioral_modifier` intentionally disabled** — not applied in daily pipeline; creates silent data loss if re-enabled without coordination with `apply_full_elo_modifiers.py`
- **Archive-first cleanup** — 67 scripts moved not deleted, preserving recovery option
- **`first-repo` + `trading-swarm` treated as single system** for audit purposes going forward

## Pending — Next Session

1. **Peru elections resolve June 7** → `score_str003_signals.py` auto-scores June 8 — first STR-003 accuracy data point under geo_elo criteria
2. **Phase 5 Gate 3**: pre-resolution accuracy ≥60% across 10+ markets — currently 50%/4 markets (stalled)
3. **Phase 5 Gate 4**: RQ1.1 AND RQ3.2 both passed — July 1 rerun
4. **RQ-CONTESTED-001 rerun** — July 1 (needs ~30 qualifying 2026 contested markets, currently ~10)
5. **`comprehensive_elo` difficulty-weighted K factor** — AFTER July 1 validation
6. **Maker/taker scan redesign** — targeted transaction hash lookup approach (block-range scan too slow)
7. **Training-librarian cleanup** — `findings.json`, `decisions/` stale entries
8. **LH-001 blocking item 2 failed** — insider signal accuracy 57.1% < 60% threshold
9. **STR-001 revalidation overdue** (39 days) but blocked — STR-001b has 0 qualifying historical signals
10. **Integration contract Section 9 expected ranges** — update to reflect current pool sizes post-audit
