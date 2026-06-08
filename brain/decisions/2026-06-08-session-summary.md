# Session Summary: Server Setup #27 — 2026-06-08

## Peru Signals — Still Pending
- STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES) not yet scored
- Important context discovered: these are RUNOFF markets (overall winner), not first round
- First round: Keiko won (17.17%), Sánchez 2nd (12%), López Aliaga 3rd — eliminated
- STR003-006 (López Aliaga YES) will resolve INCORRECT — first confirmed wrong STR-003 signal
- STR003-005 (Keiko YES) still live — runoff count ongoing, Keiko at 78.5% market price
- Markets not officially resolved on Polymarket as of session end

## External Seed Trader Scoring Pipeline — 3 Blockers Fixed

Three independent blockers preventing 195 external_seed traders from getting resolved_trades_count:

**Blocker 1 (Stub markets):** 5,929 markets with NULL resolution_date created as stubs when trades imported. hydrate_stub_markets.py created — fetches Gamma API metadata for stub markets. Added to daily_maintenance.py Step 10c at --limit 200/day. ~2,700 markets hydrated manually today across multiple passes.

**Blocker 2 (20K cap):** fast_resolution_check.py had 20,000 market ceiling — raised to 50,000. New external_seed targeted pass added (checks known market IDs from external_seed trades with past resolution dates, limit 100/run).

**Blocker 3 (is_flagged=0):** 175/195 external_seed traders had is_flagged=0 — excluded from evaluate_new_trader_results.py which requires is_flagged=1. Fixed via direct UPDATE.

**Result after fixes:** 15 Pool B eligible traders (resolved_trades_count >= 20), max 38 resolved trades, avg 4.3 resolved trades. Progress continuing via daily maintenance.

## geo_elo Analysis
- Pool C: 402 traders (down from 477 — directionality recalculated from clean state, 809 traders missing directionality due to positions table gaps)
- geo_legendary: 44 (geo_elo >= 2175), active_legendary: 11
- Accuracy: LEGENDARY 77.8%, ELITE 75.9%, QUALIFIED 69.7%, Below 48.9% (n=28,030 trades)
- calculate_geo_elo.py SCL-002 bug fixed: accuracy_pool → geo_accuracy_pool (was crashing at Phase 3)
- geo_elo correctly excludes P&L — pure accuracy metric. P&L gate pre-registered as RQ-PNLGATE-001 as separate future filter.

## NEG_RESOLVED Pattern Explained
Six traders with high pnl_taker_politics but negative pnl_resolved_politics investigated.

**Pattern:** hybrid taker/maker traders — profitable directional taker trades ($52K–$114K) offset by loss-making market-making operations (−$103K to −$214K maker P&L). Implied open position gap ≈ $0 for 4/6 — all positions settled, not a cutoff artefact.

**Decision:** use pnl_taker_politics (not pnl_resolved_politics) for candidate screening.

Traders added: Veythoris (0xaae6b4), Lioren (0x1699e1), Sylvaren (0x0833b2), anonymous (0x6d20b9).

Deferred: 2 traders with large implied open position gaps ($54K–$66K).

## Schema Propagation Audit
Full audit of first-repo scripts/ and monitoring/ against all SCL entries.

**Result:** Only 1 violation found — scripts/verify_market_titles.py:43 using `comprehensive_elo > 2175` instead of `geo_elo >= 2175 AND geo_accuracy_pool = 1`. Fixed.

SCL-003 marked PROPAGATION COMPLETE.

**Key finding:** trades.market_id stores conditionId hex — `JOIN ON m.condition_id = t.market_id` is CORRECT in first-repo scripts. SCL-001/004 were template documentation issues, not live code bugs.

## Research
- RQ-PNLGATE-001 pre-registered: P&L gate as secondary STR-003 filter. geo_elo correlates with pnl_taker_politics at only +0.138. Defer until July 1.
- integration-contract.md updated to v2.5: Pool C hydration state documented, alert threshold loosened to <350 during hydration.

## Traders Added Today
- Veythoris, Lioren, Sylvaren, anonymous (4 NEG_RESOLVED resolved)
- Total across June 6–8: 211 traders (195 external_seed + 16 manual_watchlist)

## Pending Next Session
- Score Peru signals once Polymarket resolves markets (STR003-005, STR003-006)
- STR003-006 will be first confirmed wrong signal — document and analyse
- Continue hydration: ~3,100 stub markets remaining, 200/day via maintenance
- 0x9d31ca01 (Samurai12) — 72% maker, still not added, needs verification
- 0xc05587 and 0xe0fd1b — 2 deferred NEG_RESOLVED traders, large implied open gaps
- Fix Sunday ELO service file permanently (log permissions)
- Layer 3: /holders endpoint sweep implementation
- RQ-EXT-001a/b/c after Peru resolution
- Legacy template INVESTIGATE items (run_research_scout.sh, duplicate preregistrations, ollama_agent_loop.py)
