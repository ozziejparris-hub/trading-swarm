# Session Summary — Server Setup #38
**Date:** 2026-06-18
**Theme:** Foundational data-integrity rebuild — diagnosing and curing the root-cause disease behind months of recurring bugs.

---

## STARTUP STATE (carried from #37)
LEGENDARY pool showed 25 (overnight maintenance surfaced new qualifiers from #37's backlog clear). geo_resolved_trades_count still stale (0x9f162cab=2028, unchanged — nothing baked overnight). Confirmed ELO recalc had NOT run. Began with the deferred geo reconciliation, which expanded into a full-system foundational rebuild at Oscar's direction.

---

## PART 1 — geo_resolved_trades_count ROOT CAUSE + FIX

### The bug (directed CC investigation)
update_geo_elo.py (Writer B, daily) stored `n = len(trades)` into geo_resolved_trades_count; the field must hold COUNT(DISTINCT market_id). A trader with 2028 trades across 5 geo markets stored 2028. SELF-LOCKING: stale-detection used `HAVING COUNT(trade_id) > stored`, so once 2028 was written, 2028>2028=FALSE → never recomputed. This is why #37's backfill didn't stick — Writer B would overwrite it daily and then lock it.

### The gate truth
Pool C gate was `geo_resolved_trades_count >= 5` (NOT >=10 as previously assumed) — and because the field stored trade-count not distinct-markets, the gate was TRIVIALLY passed. LEGENDARY had been admitting traders with as few as 1-4 distinct geo markets but many trades in them.

### Fixes (commit dac9b2b)
- update_geo_elo.py line 296: store `len(set(market_ids))` not `len(trades)`
- line 120: stale-detection → `COUNT(DISTINCT market_id)`
- ELO math unaffected (still uses all qualifying trades; only stored count changed)

### Reconciliation (commit af6fafb, scripts/reconcile_geo_resolved_counts.py)
One-time recompute of geo_resolved_trades_count to distinct-markets for all traders (no price filter — count gates eligibility, not scoring). Pool C 4046→3450, LEGENDARY 25→22 (3 traders with 4 distinct markets dropped).

### Decision: price filter
Price filter (0.10-0.80) belongs in ELO SCORING, not in the eligibility COUNT. Count = distinct resolved geo markets regardless of price.

---

## PART 2 — THRESHOLD RAISE + CATEGORY UNIFICATION (commit 5ec00a1)

### Threshold >= 5 → >= 10
Corrected pool distribution was bimodal: 9 traders at 5-9 distinct markets (thin tail, luck-dominated — several at exactly 5 markets with ~2000 trades), 13 at 16-243 (genuine forecasters). Natural gap at 9-16. Raised Pool C gate to >= 10. Pool C 3450→1816, LEGENDARY 22→13.
- Auto-requalification confirmed: gate is daily reset-and-recompute; traders re-enter automatically when they cross 10 distinct markets (self-lock now fixed so the stale-check fires on new markets).
- Decision rationale: signal QUALITY over quantity. A trader with 5 resolved markets can't be distinguished from luck. 13 traders with genuine multi-market records > 22 where 9 are coin-flips.

### Category source unified to m.category (markets table, authoritative)
All 4 geo-category filters in update_geo_elo.py changed tr.market_category → m.category (new_traders L95, stale-detection L114, _fetch_qualifying_trades L140, plus the gate). Previously used denormalized trades.market_category (122,170 rows out of sync), risking count drift between admission/recompute/reconciliation.

---

## PART 3 — THE CORE DIAGNOSIS (Oscar's central concern)

Oscar identified the real problem: every session finds a "glaring issue," patches it, moves on — months of symptom-patching. Demanded full-system diagnosis of WHY the pattern recurs before any further fixes. Agreed phases: 2 (invariant discovery), 3 (taxonomy), 4 (harness), 5 (foundational fixes), 6 (contract-as-registry). First-repo today; trading-swarm next. No matter the cost.

### PHASE 2 — 23-INVARIANT DIAGNOSTIC (directed CC, 23 min)
Full report: 23 violated invariants — 2 CRITICAL, 5 high, 9 medium, 7 low. Across 4 categories: format (timestamps/scales), identifier (JOIN keys), source-vs-derived (cached aggregates vs recompute), cross-table duplication (denormalized caches).

### PHASE 3 — TAXONOMY
23 violations collapse to TWO diseases + ONE structural mistake:
- **Disease A:** Denormalized caches with no back-propagation (cached category/title on trades/positions never refreshed).
- **Disease B:** Aggregate columns updated by MULTIPLE uncoordinated writers, some accumulating instead of recomputing.
- **Structural mistake C:** API-sourced aggregates living in same columns as locally-computed ones — ELO engine read API total_trades as K-factor basis against local outcomes → geo_elo crashed to -28,861.
Root of all: same fact stored multiple places/formats, no single source of truth, no sync, no detection, all failures SILENT.

### PROVENANCE PRINCIPLE (key architectural decision)
Local trades = source of truth for everything computed/decided (ELO, pool, signals, win-rate-in-scoring). API figures = reference-only, rename api_*, NEVER fed into computation. Only score traders whose trades we have locally. Consequence accepted: ~114K API-only traders become non-evaluable until ingested (parked for future ingestion-expansion).

---

## PART 4 — CRITICAL BUGS NEUTRALIZED

### Critical #1: corrupted geo_elo in live pool (commit af6fafb)
13 pool members with geo_elo_active < 500 (corrupted by API-vs-local mismatch in the active-ELO decay; spectrum extends into 500-800 band too). NONE were LEGENDARY-tier (corruption pushed scores DOWN), so no active signal impact. Added `geo_elo_active >= 500` sanity floor to POOL_C_POPULATE_SQL — durable in daily gate, self-maintaining, becomes harness invariant. Pool C 1816→1803.
**VERIFICATION LESSON: CC showed the diff but did NOT write the file the first time — caught by grep. Re-applied, grep-verified bytes on disk, THEN committed. Always grep-verify CC writes before committing.**

### Critical #2: pending-on-resolved trades
Signal-relevant backlog cleared via fixed evaluation: evaluate_new_trader_results.py (1,780 trades/18 traders) + backfill_trade_results_geo.py (729 trades, 375W/354L/190 traders). ~96K unflagged general-population backlog deferred (those traders not in pools/signals).

---

## PART 5 — THE HARNESS (Phase 4, commit e72fd5e)

scripts/audit_invariants.py (READ-ONLY, 18 checks, 3 tiers):
- Tier 1 (floor=0, CRITICAL if violated): impossible states + JOIN-fix regression + geo recon + pool sanity floor
- Tier 2 (floor=current, REGRESSION if grows): pending-on-resolved, category-Unknown, timestamp formats
- Tier 3 (structural baselines, alert on >10% change): API-vs-local, BUY-no-position, volume outliers
Writes JSON to brain/agent-outputs/data-audit/. Flags: --alert (Telegram), --verbose.
Baseline at build: 3 CRITICAL (successful>total 338, win_rate>1 892, specialisation>1 75), 0 REGRESSION, 15 PASS.

---

## PART 6 — PROVENANCE CLASSIFICATION (Phase 6 blueprint, directed CC)

Full 41-column (37 governed) classification — THE foundational document:
- LOCAL-AUTHORITATIVE (24): reconciler/ELO-engine own; each with canonical recompute definition
- DERIVED-FROM-DERIVED (4): win_rate, geo_elo_active, geo_accuracy_pool, research_excluded (dependency order)
- API-REFERENCE (4): wallet_creation_date, true_wallet_age_days, funding_wallet, is_contract_wallet → rename api_*
- DEAD/DUPLICATE (3): unrealized_pnl, total_pnl, roi_percentage → drop
- OPERATIONAL (2): pnl_skip, backfill_attempted

RED FLAGS (the disease quantified): comprehensive_elo 4 writers (incl. simulation script that can clobber production), open/closed_positions 4 each, research_excluded/geo_accuracy_pool/geo_resolved_trades_count 3 each, total_trades/total_volume 2 from different sources.

---

## PART 7 — LAYER 1 RECONCILER (commit 9dc07e7)

scripts/reconcile_trader_aggregates.py — SINGLE authoritative writer for simple-aggregate columns, recomputed from local trades/positions (never accumulating):
total_trades, successful_trades, resolved_trades_count, total_volume, total_invested (SUM entry_total_cost WHERE status='closed'), avg_roi, realized_pnl, closed/open_positions, win_rate (fraction, capped 1.0), specialisation_ratio (recomputed max_cat/total, bounded [0,1]).
- Honors pnl_skip (preserves PnL columns for 578 permanently-failed traders)
- Does NOT touch ELO chain (Layer 2) or geo columns (already done)
- Leaves DEAD columns for next-session drop
Result: 143,076 traders reconciled, all 3 CRITICALs → 0.

### Single-writer neutralizations (win_rate)
win_rate had 3 production writers on 2 scales with 2 denominators — guaranteed regression. Neutralized: trader_analyzer.py (=0 placeholder), trader_statistics.py ×2 (percentage scale, distinct denominator). database.py add_or_update_trader: win_rate UPSERT preserves existing on NULL. Reconciler now sole win_rate writer. Full writer set audited (simulation/dead/in-memory confirmed harmless).

### Decisions taken
- 0x44a1159b (LEGENDARY discrepancy from #37): RESOLVED — already correctly excluded by >=10 gate (9 distinct markets, 85% of trades in one market = the single-market-concentration v2.7 flagged). No action; the principled gate now does what the manual flag used to.
- wash_trade_suspect 57 frozen traders: zeroed (archived writer shouldn't permanently gate; research_excluded re-derives next maintenance).

---

## PART 8 — IMMUNE SYSTEM WIRED IN (commit b30c5ff)

audit_invariants.py wired into daily_maintenance.py as pre-ELO gate:
- Exit 2 on Tier-1 CRITICAL → maintenance HARD ABORTS before update_geo_elo (corruption never reaches ELO)
- Exit 0 on PASS or REGRESSION-only → Telegram alert sent, run continues
- Placement: after preprocessing, before geo-ELO
- READ-ONLY: detects + alerts, never repairs. Reconciler repairs (run deliberately, NOT yet daily — deferred until competing writers removed).
Confirmed exits 0 now (won't abort tonight).

### Harness refinement
total_invested check initially disagreed with reconciler (all-positions vs closed-only) → 17,085 false positives. Fixed harness to match canonical definition (closed-only) + exclude pnl_skip. Final: **18/18 PASS, 0 CRITICAL, 0 REGRESSION.**
This disagreement was itself an instance of the disease (same fact, two definitions) in our own tooling — drove the definition-locking rule.

---

## PART 9 — CONTRACT AS REGISTRY (Phase 6, commits bdfad6f + 56ba861)

Integration contract v2.11 → v2.12. New Section 18:
- 18.1 Core principle (local=truth, API=reference)
- 18.2 The disease (writer-count red flags)
- 18.3 Column authority registry (37 columns, canonical definitions from reconciler)
- 18.4 Single-writer enforcement status (honest: win_rate done; successful_trades/total_trades/total_volume have competing writers pending; specialisation_ratio wrong at source; ELO chain pending)
- 18.5 KEY LESSON: harness invariants must be definition-locked to contract (three-way agreement rule)
- 18.5.1 KNOWN GAP: canonical defs live in trading-swarm Markdown while code lives in first-repo — documentation not enforcement, same-commit rule unenforceable across repos. PLANNED FIX: extract to first-repo/monitoring/column_definitions.py, both reconciler + harness import from it (turns governance rule into interpreter constraint).
- 18.6 The immune system

---

## FINAL STATE
- LEGENDARY pool = 13 (all 16-243 distinct geo markets, clean, defensible)
- Pool C = 1803
- Harness: 18/18 PASS, 0 CRITICAL, 0 REGRESSION, wired into maintenance
- Layer 1 reconciler: deployed, 143K traders correct, single win_rate writer
- ELO recalc: STILL FROZEN — do not run until Layer 2 (ELO chain reconciler) done + harness clean on corrected ELO
- Backups: markets_20260618_141057.db, _191607.db (pre-mutation checkpoints)

## COMMITS (first-repo, all pushed)
dac9b2b (geo distinct-markets fix), 5ec00a1 (>=10 + category unification), af6fafb (geo_elo_active>=500 floor + reconcile script), e72fd5e (harness), 9dc07e7 (Layer 1 reconciler + neutralizations), b30c5ff (harness wired into maintenance)
## COMMITS (trading-swarm, pushed)
bdfad6f (contract v2.11 Section 18), 56ba861 (v2.12 Section 18.5.1)

---

## NEXT SESSION — PRIORITY ORDER (nothing missed)

### TOP PRIORITY — finish the foundational rebuild (first-repo)
1. **Single canonical definitions module** (addresses 18.5.1 cross-repo gap): create first-repo/monitoring/column_definitions.py with every LOCAL-AUTHORITATIVE + DERIVED column's canonical recompute as importable constants. reconcile_trader_aggregates.py + audit_invariants.py both import from it. Contract 18.3 changes to point at the module. Do FIRST (alongside teardown — both touch these definitions).
2. **Layer 2 reconciler — the ELO chain:** comprehensive_elo + base_category_elo + behavioral/advanced/pnl modifiers + kelly/patience/timing/weighted_win_rate scores. Needs UnifiedELOSystem + TradingBehaviorAnalyzer orchestration. Complex/risky — fresh session.
3. **Competing-writer teardown:** remove the competing writers so reconciler is genuinely sole writer (not just runs-last):
   - successful_trades: trader_statistics.py update_trader_win_rate also writes it
   - total_trades / total_volume: trader_statistics passthrough + discover_* + trader_analyzer API path
   - comprehensive_elo: 4 writers incl. simulation/calculate_elo_simple.py (the simulation clobber risk)
   - open/closed_positions: 4 writers each
   - research_excluded (3), geo_accuracy_pool (3)
   - specialisation_ratio: fix analysis_scheduler.py to write correct max_cat/total formula (currently writes unbounded ELO-divergence) — fix at SOURCE, not just overwrite
4. **Drop 3 DEAD columns** (unrealized_pnl, total_pnl, roi_percentage) — after confirming nothing reads them.
5. **Rename 4 API columns to api_*** (wallet_creation_date, true_wallet_age_days, funding_wallet, is_contract_wallet) — no scoring reads them, safe.
6. **THEN run ELO recalc** on corrected data + re-validate active STR-003 signals against corrected pool.

### SECONDARY (first-repo cleanup)
7. Clear remaining ~96K unflagged pending-on-resolved + ensure daily eval keeps pace (harness Tier-2 will show if it doesn't).
8. Timestamp normalization (Teardown 3): elo_last_updated T-sep/space (44,694), markets end_date/resolution_date remnants (945+880), positions intra-table split. Harness tracks at floor.
9. Category cache decision (Teardown 2): drop-and-JOIN vs keep-and-refresh for trades.market_category/title (122,417 Unknown, growing). Performance decision at 7.7M trades.
10. successful_trades>actual+5 population (608) — investigate alongside teardown.

### THEN — trading-swarm data-layer audit (same diagnostic applied to second repo)
11. Run the Phase 2-style invariant discovery on trading-swarm's brain/ data layer.

### SIGNAL/RESEARCH ITEMS (carried, time-gated)
12. STR003-004 invalid basis: key trader 0xdffc6760 = geo_elo 811, pool=0, 1 distinct market. Signal rested on phantom qualification. Dead Dec-2025 market; downweight-not-invalidate. Flag for review, do not auto-invalidate.
13. 0xfa323e PARTIAL weight promotion (non-redemption trader, realized_pnl=$0 despite wins) — minor, resolved 96→131 in #37, promotion not yet actioned.
14. June 30: Score STR003-004/007/008 correlated cluster; RQ-CORRELATION-001.
15. July 1: RQ wave (RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001); pre-register RQ-VPIN-001, sign-randomization, RQ-ILS-001; STR-002 thesis-cell analysis.
16. Mid-July: Peru ONPE oracle → confirm STR003-005 + score 5 LEGENDARY STR-002 Peru signals. Maine RCV result.

### STANDING
- ELO recalc stays FROZEN until Layer 2 done + harness clean.
- Reconciler run deliberately (not daily) until competing writers removed; must run LAST to win until then.
- grep-verify CC file writes before committing.
- Use directed CC investigation prompts for multi-step work.
- Both repos pushed clean (runtime state not committed).
- Backup-checkpoint before large mutations (monitor writes concurrently).
