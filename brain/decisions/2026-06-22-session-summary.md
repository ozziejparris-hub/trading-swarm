# Session Summary — Server Setup #39
**Dates:** 2026-06-22 (evening) → 2026-06-23
**Theme:** Built the canonical definitions module and repointed all 6 Tier-1 data-integrity consumers — converting the Session #38 provenance blueprint from documentation into structurally-enforced code. Diagnosed and fixed the root cause of recurring morning CRITICALs.

---

## STARTUP STATE (return from weekend)
Came back to find weekend maintenance had FAILED at step 6 (integrity audit, exit 2) — the harness correctly hard-aborted before ELO. LEGENDARY had drifted to 23, Pool C to 3504.

ROOT CAUSE of the weekend failure: update_research_exclusions.py (Step 0 in maintenance) still carried the OLD pool gate (geo_resolved>=5, no geo_elo_active floor, wrong NULL handling). Running daily, it overwrote the corrected pool every morning. Classic competing-writer disease. Also found sync_trade_categories.py crashing daily (exit 2) — argparse --incremental needed nargs='?'.

FIX (commit 8d90447): synced update_research_exclusions.py gate to canonical; fixed sync_trade_categories argparse. Re-gated pool → Pool C 1854, LEGENDARY 14 (clean, 0 below floor).

---

## THE CORE WORK: CANONICAL DEFINITIONS MODULE + TIER-1 REPOINTING

### Why (the gap from Session #38)
Session #38 documented the provenance blueprint in the integration contract (Markdown, trading-swarm repo) while the code lives in first-repo. That's documentation, not enforcement — the same "fact in two places" disease one level up. Oscar identified this. The fix: a single importable module in first-repo that both writers and the harness import, making divergence structurally impossible.

### CC survey — the disease at full scale
Investigation found the LEGENDARY/pool gate copy-pasted across ~16 scripts, ~8 WRONG:
- 6 scripts use raw geo_elo instead of geo_elo_active → dormant decayed traders still counted LEGENDARY (41 at raw geo_elo vs 13 at geo_elo_active)
- score_str003_signals.py uses raw geo_elo with NO pool check — SIGNAL-INTEGRITY finding
- Plus 4 definition disagreements: reconcile's >=5 re-gate, NULL-handling divergence, update_geo_elo's price-filtered count, resolved_trades_count m.resolved=1 discrepancy

### The module (commit 17f8d62): monitoring/column_definitions.py
Single canonical source. Sections: SQL fragments (GEO_RESOLVED_TRADES_COUNT_SQL no-price-filter, RESOLVED_TRADES_COUNT_SQL no m.resolved filter); gate constants (GEO_ELO_POOL_SANITY_FLOOR=500, GEO_ELO_LEGENDARY=2175, NEAR_LEGENDARY=1800, ELITE=1400, QUALIFIED=1000, POOL_C_MIN_RESOLVED_TRADES=10, POOL_C_GATE_WHERE, POOL_C_POPULATE_SQL, LEGENDARY_GATE_WHERE, POOL_C_SANITY_VIOLATION_WHERE); pure functions (compute_win_rate, compute_geo_elo_active, derive_tier); atomic refresh_pool_c(conn). Self-test: 17 assertions pass.

### Tier-1 repointing — all 6 consumers, one at a time, harness-verified + committed each:
1. reconcile_geo_resolved_counts.py (fd54def): CORRECT_COUNT_SQL→cd fragment; partial >=5 evict-only re-gate→cd.refresh_pool_c (BEHAVIOR FIX: old only evicted, never populated). Pool C 1854→1883, LEGENDARY 14→15 (0x44a1159b legitimately crossed to 10 distinct markets).
2. update_research_exclusions.py (d7e1bfb): →cd.refresh_pool_c, killed the NULL-handling bug. Both maintenance pool writers now identical.
3. update_geo_elo.py (235b8dd) — HIGHEST VALUE: fixed the line-319 price-filtered geo count (the daily re-corruption source) → canonical no-filter standalone query; BUNDLED stale-detection price-filter drop (else self-lock freezes ELO updates); PRESERVED price filter in _fetch_qualifying_trades (ELO scoring) + new-traders eligibility. LEGENDARY 15→13 active = legitimate decay (2 dormant traders).
4. backfill_trade_results_geo.py (093ee85): inline subquery→cd.GEO_RESOLVED_TRADES_COUNT_SQL. This was the script that drifted the previous morning.
5. reconcile_trader_aggregates.py (0fa8112): win_rate→cd.compute_win_rate (deleted dead stub, cap-counter equivalence proven); resolved_trades_count documented as logically-equivalent bulk-CTE performance variant (NOT literally imported — 144K traders, correlated subquery would be too slow). Established principle: module defines MEANING; consumers may implement differently for performance if logically equivalent + documented.
6. audit_invariants.py (2b83c07) — THE KEYSTONE: check_geo_recon→cd.GEO_RESOLVED_TRADES_COUNT_SQL, check_geo_pool_sanity→cd.POOL_C_SANITY_VIOLATION_WHERE. Output byte-for-byte identical before/after. Harness now checks against the EXACT definitions writers use → harness-vs-writer divergence structurally impossible.

---

## THE 2026-06-23 MORNING CRITICAL — diagnosed and permanently fixed

Overnight maintenance (first full run with all 6 repoints) COMPLETED clean (exit 0) — the repoints work together in the live flow. But morning harness showed 1 CRITICAL: geo_resolved_trades_count mismatch = 3 (later 7 via full reconcile).

DIAGNOSIS: NOT a Tier-1 hole — definitions are all consistent. The drift came from an INTERACTION: sync_trade_categories.py (now working after the argparse fix) reclassifies markets overnight; when a market flips to Geopolitics/Elections, it changes geo_resolved_trades_count for traders who traded it — but update_geo_elo's stale-detector keys on new TRADES, not category flips, so it misses them. Also evaluate_new_trader_results (runs post-audit) flips geo trades pending→won/lost, changing counts after the audit already ran. All 3 flagged traders: +1 drift, not LEGENDARY, pool-safe, zero signal impact.

FIX (commit c9e9f0f): bracket maintenance with TWO reconcile_geo_resolved_counts runs:
- Reconcile #1 [pre-audit]: after Resolution sweep, before Integrity audit (BLOCKING). Catches category-reclassification drift so the gate opens clean.
- Reconcile #2 [post-eval]: after Evaluate new trader results (NON-BLOCKING). Settles post-audit evaluation drift so next morning opens clean.
Chosen over reordering the pipeline (which carried dependency risk — resolve_legendary_markets needs post-audit geo_elo_active). Drift window proven fully closed: after reconcile #2 no step touches trade_result/category; the 15-min monitor only adds PENDING trades (don't count toward won/lost). ~10s x2, negligible cost.

---

## FINAL STATE (session close)
- Pool C ~1896, LEGENDARY 16 active (grew over the 22-23 span via legitimate qualification + decay recompute on corrected data)
- Harness: 0 CRITICAL. REGRESSIONs (all known/deferred): market_category Unknown ~128K (Teardown 2, now SHRINKING as sync_trade_categories works), timestamp mixed ~26K (Teardown 3), total_invested pnl_skip mismatch ~20 (pnl_skip-preserved, benign), pending-on-resolved ~1 (clears daily)
- Traders grew to 144,444 (weekend+ ingestion)
- Both services running. Server moved rooms 2026-06-19 (clean shutdown/restart, same IP).

## COMMITS THIS SESSION (first-repo, all pushed)
8d90447 (gate sync + argparse), 17f8d62 (column_definitions.py), fd54def (#1), d7e1bfb (#2), 235b8dd (#3), 093ee85 (#4), 0fa8112 (#5), 2b83c07 (#6 keystone), c9e9f0f (maintenance self-healing bracket)
## COMMITS (trading-swarm)
contract v2.13 (Section 18.5.1: gap RESOLVED, Tier-1 complete, Tier-2 scoped)

---

## NEXT SESSION — TIER 2 (the read-side signal/scan sweep)
Repoint ~13-14 read-side scripts to cd.LEGENDARY_GATE_WHERE / cd.derive_tier, fixing the 6 that use raw geo_elo instead of geo_elo_active.

PRIORITY — score_str003_signals.py (SIGNAL-INTEGRITY): uses raw geo_elo, no pool check. After repointing, MUST re-validate every active STR-003 signal — key traders may not be genuinely LEGENDARY under the corrected geo_elo_active gate (the 41-vs-13 gap means signals may rest on dormant/decayed traders treated as LEGENDARY).

Tier-2 scripts: score_str003_signals, register_signal, signal_credibility, detect_counter_signals, legendary_positions_scan, resolve_legendary_markets, backfill_transaction_hashes, polygon_event_scanner, polygon_maker_taker, pre_resolution_intelligence, verify_market_titles, system_observer (missing research_excluded/bot_type), snapshot_elo_scores (→cd.derive_tier), evaluate_new_trader_results (m.resolved=1 review).

These are READ-side — they produce wrong reads (treating ~41 as LEGENDARY vs 13-16 genuine) but can't cause harness CRITICALs or corrupt the pool. Lower destabilization risk than Tier 1, but the geo_elo→geo_elo_active fix is materially important for signal accuracy.

## REMAINING REBUILD (later sessions, carried from #38)
- Layer 2 reconciler: ELO chain (comprehensive_elo + 4 modifiers + behavior scores) — needs UnifiedELOSystem/TradingBehaviorAnalyzer orchestration, complex
- Competing-writer teardown: successful_trades/total_trades/total_volume (trader_statistics still writes P&L fields directly), comprehensive_elo 4 writers incl simulation clobber risk, open/closed_positions 4 each; fix analysis_scheduler specialisation_ratio formula at source
- Drop 3 DEAD columns (unrealized_pnl, total_pnl, roi_percentage); rename 4 API columns to api_*
- THEN full ELO recalc on corrected data (STILL FROZEN until Layer 2 done + harness clean)
- Teardown 2 (category cache: drop-and-JOIN vs refresh, 128K Unknown shrinking) + Teardown 3 (timestamp normalization)
- trading-swarm data-layer audit (same diagnostic, second repo)

## SIGNAL/RESEARCH ITEMS (carried, time-gated)
- STR003-004 invalid basis: 0xdffc6760 = geo_elo 811, pool=0, 1 distinct market; downweight-not-invalidate, flag for review
- 0xfa323e PARTIAL weight promotion (non-redemption trader) — minor, not yet actioned
- June 30: score STR003-004/007/008 cluster; RQ-CORRELATION-001
- July 1: RQ wave (RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001); pre-register RQ-VPIN-001, sign-randomization, RQ-ILS-001; STR-002 thesis-cell analysis
- Mid-July: Peru ONPE oracle → confirm STR003-005 + score 5 LEGENDARY STR-002 Peru signals; Maine RCV

## STANDING
- ELO recalc FROZEN until Layer 2 done + harness clean (update_geo_elo incremental daily geo update is NOT the frozen recalc)
- grep-verify CC writes before committing; directed CC prompts for investigation; one-at-a-time repoint with harness check + commit
- Both repos pushed clean (runtime state not committed: data/.last_requeue_run, logs/*.log, brain JSONs)
- Module principle (contract 18.5.1): definitions live ONCE in column_definitions.py; consumers import; performance variants allowed if documented + logically equivalent
