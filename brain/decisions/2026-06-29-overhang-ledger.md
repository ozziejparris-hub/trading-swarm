# Overhang Ledger — Sessions #38–42
**Date:** 2026-06-29  
**Scope:** All deferred/NEXT/Layer-2/LATER items from sessions #38 (2026-06-18) through #42 (2026-06-26), plus the contamination forensic map (2026-06-24).  
**Method:** Each item status was verified against live code and DB — not taken from session text alone.  
**Existing roadmap:** `brain/strategic-roadmap-2026-06-11.md` covers the Phase 5/6/7 arc. `brain/priorities.md` is stale (May 2026, pre-server). This ledger reconciles with the roadmap where items overlap and does not duplicate Phase-level content already there.

---

## OPEN ITEMS (ordered by dependency — what must come before what)

---

### O-0 · ACTIVE ALERT: Pool C Decline (HOT, not from #38–42 arc)
**ITEM:** Pool C dropped 41% since June 20 peak (3,660 → 2,157), sitting 13.7% below the 2,500 alert threshold for ≥2 days. Root cause unknown.  
**SOURCE:** `brain/decisions/2026-06-29-pool-c-decline-investigation.md` (filed today by performance-analyst-agent)  
**STATUS:** OPEN — uninvestigated. Root cause unknown.  
**VERIFIED:** `geo_accuracy_pool=1` count from DB today = 2,157 (confirmed by performance-analyst).  
**DEPENDENCIES:** Blocks nothing in the ELO-rebuild arc (geo_elo and Pool C are independent of comprehensive_elo). But **directly affects signal integrity** and July 1 RQ wave (RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ-EXEC-001 all depend on Pool C). Must be investigated before July 1.  
**RISK/EFFORT:** Unknown until diagnosed. Investigation is read-only. Fix may be trivial or may require maintenance-sequence repair.  
**FROZEN-AREA?** No — geo_elo chain, not comprehensive_elo chain.

---

### O-1 · Wire `run_tests.py` into daily maintenance
**ITEM:** Add `run_tests.py --skip test_behavioral_integration.py` to `daily_maintenance.py`, writing results to `tests/LATEST_TEST_RESULTS.md`. Non-blocking. NOT Telegram.  
**SOURCE:** Sessions #41 (deferred), #42 (deferred again with "unblocked" note)  
**STATUS:** OPEN — **NOW UNBLOCKED**. Verified: `daily_maintenance.py` contains zero references to `run_tests`, `LATEST_TEST_RESULTS`, or test automation. All 8 behavioral-integration tests are genuinely green (fixed in #42, commit `bd82fd7`). The `--skip test_behavioral_integration.py` flag is needed because that file calls `analyze_all_traders()` on a cold cache in subprocess context (39-minute hang, removed in commit `c736558`).  
**DEPENDENCIES:** Blocked nothing; unblocked now. Independent of Layer 2.  
**RISK/EFFORT:** Small. ~10-line change to `daily_maintenance.py`. No frozen-area contact.  
**FROZEN-AREA?** No.

---

### O-2 · Category cache teardown — Teardown 2
**ITEM:** Decide and implement: drop-and-JOIN vs keep-and-refresh for `trades.market_category` / `trades.title` denormalised cache. Currently ~133K Unknown values and growing.  
**SOURCE:** Sessions #38, #39, #40 (all listed as "Teardown 2, carried")  
**STATUS:** OPEN. **WORSENING** — harness shows 133,497 Unknown vs floor 122,417 → **REGRESSION** (was called "SHRINKING" in session #39, but harness contradicts this as of today).  
**VERIFIED:** Harness output 2026-06-29: `trades.market_category='Unknown' where market.category is known = 133,497, floor 122,417, status REGRESSION`. Count grew from ~122K to ~133K despite `sync_trade_categories.py` running daily.  
**DEPENDENCIES:** Independent of ELO rebuild arc. Can be done any time. Does not block or unblock anything.  
**RISK/EFFORT:** Medium. The architectural decision (drop vs refresh) is the key step; implementation follows from it. Performance concern at 8M+ trades table.  
**FROZEN-AREA?** No.

**REFRAME 2026-07-09 — this was never the classification backlog; it's a structurally non-self-healing sync gap, and it's much worse than last measured.** Two sessions today converged on this from opposite directions: O-22's fix work (below) characterized the *actual* market-classification backlog and found it's small (4,398 markets remaining, not 133K/138K) — the ~133K/138K figure being tracked under O-2 all along was never that backlog. It's `audit_invariants.py::check_unknown_category`: the count of **trades** whose cached `trades.market_category` is stuck at `'Unknown'` while the parent `markets.category` is already correctly classified — a `sync_trade_categories.py` drain problem, not a classification problem.

- **Current count: 276,285** (was 138,608 as recently as the 2026-07-06 run). **Confirmed root cause of the jump:** `sync_trade_categories.py --incremental` (the only mode wired into `daily_maintenance.py`, via the "Sync trade categories" step) only fixes trades with `timestamp >= now-7days`. Directly queried: **276,254 of 276,285 (99.99%) are older than 7 days** — permanently outside that window. `--full-sync` (the mode that would fix them) **is scheduled nowhere** — no cron, no daily_maintenance step. Once a trade ages out of the incremental window without syncing, it is stuck at `Unknown` forever regardless of what happens to the market row.
- **The jump 138,608 → 275,903 happened between the 2026-07-06 and 2026-07-07 daily_maintenance runs** — correlates directly with the O-16 Tier-2 backfill (first-repo `3b80369`) landing a large batch of old-timestamp trades tied to markets that already carried real categories. Confirms the mechanism: any bulk import/backfill of old markets recreates this gap, and nothing currently closes it.
- **Not cosmetic.** Breakdown by parent-market category: **215,575 Elections + 60,692 Geopolitics** (+18 US-current-affairs). Consumers that filter on `tr.market_category IN ('Geopolitics','Elections')` **directly** (not joined through `markets.category`) are silently excluding these trades: `update_geo_elo.py`'s `geo_elo_active` recency calc (lines 252 & 316 — feeds Pool C / LEGENDARY-active counts), `detect_insider_activity.py`, `calibrate_composite_threshold.py`, `system_observer.py`'s geo-trade queries, and `calibration_analysis.py`'s per-category calibration curves (stale trades get bucketed as "Unknown," diluting category-specific calibration accuracy). **Verified clean, for the record:** the core `geo_elo`/`geo_directionality_score` computation and the canonical `GEO_RESOLVED_TRADES_COUNT_SQL` all join and filter on `markets.category` — not the stale column — so base geo_elo itself was never affected (consistent with `audit_invariants`'s T1 `geo_resolved_trades_count mismatch` check reading PASS/0 throughout).
- **FIX (scoped, not applied — first thing next session, with a backup):**
  1. **Order matters.** Run the O-22 market-classification backfill first (it classifies parent markets still sitting at `Unknown`), *then* `sync_trade_categories.py --full-sync`. `--full-sync` only propagates an already-correct `markets.category` down to `trades.market_category` — it does nothing for trades whose parent market is itself still unclassified.
  2. `--full-sync` confirmed safe/idempotent by direct code read: its WHERE clause (`t.market_category != m.category AND m.category IS NOT NULL AND t.market_category IS NOT NULL`) only ever selects genuinely-mismatched rows — a correctly-categorized trade cannot be touched. Batched (10K rows/commit), WAL-safe, no timeout/resumability built in but no external I/O in the hot loop either — expect low minutes for ~276K rows, not hours. Take a DB backup first regardless, per standing policy.
  3. **Recurrence fix (do this too, not just the one-time drain):** make bulk-import/backfill scripts trigger a targeted `trades.market_category` sync for the market_ids they touch (closes the mechanism that caused the 07-06→07-07 jump), plus schedule `--full-sync` as a periodic backstop (weekly, e.g. alongside the Sunday full ELO recalc) to catch anything the source-side fix misses. Widening the incremental window alone does not fix this — any bulk backfill of old markets will always produce trades older than any fixed window.
  4. **Verification after the run:** (a) the `Unknown`-trade-with-known-market-category count → 0; (b) `audit_invariants.py`'s `check_unknown_category` T2 line → PASS; (c) no previously-correct trade altered (`t.market_category != m.category AND t.market_category != 'Unknown'` count stays 0 before and after — proven structurally by the WHERE clause, confirm empirically anyway); (d) `sync_trade_categories.py`'s own pre-count reports `gaining_geo ≈ 276,267`, `losing_geo ≈ 0`.
- **ELO-arc precursor:** this cleans real inputs (`geo_elo_active`, insider/STR-002/STR-003 signal scoring, calibration) feeding into the frozen-area migration design (`2026-07-06-elo-arc-design-FABLE.md`) — do it before that migration's `write_elo_result` consolidation lands. Does **not** touch the base `geo_elo`/`geo_directionality_score` computation, which was already clean.
- **DEPENDENCIES (updated):** No longer fully independent — feeds ELO-arc input cleanliness (see above) and should land before Stage 1 of that migration. O-22 (below) is now a soft prerequisite (market-classify-first ordering).
- **RISK/EFFORT (updated):** Small-medium for the one-time drain (safe, scoped, ~276K rows). Medium for the recurrence fix (touches whichever bulk-import scripts write `markets.category`).

---

### O-3 · Timestamp normalization — Teardown 3
**ITEM:** Normalise mixed timestamp formats across 4 tables: `traders.elo_last_updated` (23,440 rows with wrong format), `markets.end_date` (2,719 non-canonical), `markets.resolution_date` (2,534 non-canonical). `positions.*` and `trades.timestamp` are already clean.  
**SOURCE:** Sessions #38, #39 (Teardown 3, carried)  
**STATUS:** OPEN. **WORSENING** — harness shows 28,693 mixed vs floor 24,996 → **REGRESSION**. All growth is in `traders.elo_last_updated` (23,440 vs floor 23,163) and markets dates.  
**VERIFIED:** Harness 2026-06-29: `timestamp mixed formats = 28,693, floor 24,996, REGRESSION`. Per-column breakdown: `traders.elo_last_updated` non-canonical 23,440; `markets.end_date` non-canonical 2,719; `markets.resolution_date` non-canonical 2,534.  
**DEPENDENCIES:** Independent. New traders added daily drift the count upward (elo_last_updated written by `apply_full_elo_modifiers.py` with T-sep format, while canonical is space-sep — or vice-versa; verify before fixing). No ELO chain contact.  
**RISK/EFFORT:** Small-medium. One-time backfill SQL + writer fix to prevent re-accumulation.  
**FROZEN-AREA?** No — but `elo_last_updated` is written by `apply_full_elo_modifiers.py` (a frozen-area-adjacent script). Check the format the writer uses before patching the data.

**UPDATE 2026-07-06 — FOLDED INTO THE ELO MIGRATION, no longer a standalone workstream.** The `markets.resolution_date`/`end_date`/`last_checked` portion of this item was fixed today as part of the O-16 backfill fix (commit `ebbb69c`) — 137,323 values normalized via `scripts/normalize_market_dates.py`, generator fixed. The one remaining driver, `traders.elo_last_updated` (23,518 non-canonical, confirmed the entire remaining O-3 count as of today), is generated by `apply_full_elo_modifiers.py:152`'s `datetime.now().isoformat()` — Writer B, the exact script the ELO-arc design (`2026-07-06-elo-arc-design-FABLE.md`, corrected commit `6495006`) rewrites. **Generator fix lands in that design's Stage 2** (the new atomic write helper uses canonical space-separated format); **one-time backfill of the existing 23.5K rows lands in Stage 5.** No separate O-3 fix is needed or should be scheduled — it rides the ELO migration end to end. See O-6/O-7 below.

---

### O-4 · Dead-column cleanup and API-column rename
**ITEM:**  
- **Drop 4 dead columns on `traders` table:** `unrealized_pnl`, `total_pnl`, `roi_percentage`, `weighted_win_rate`  
  - `weighted_win_rate` confirmed dead in #42: only `integrate_behavioral_elo.py` writes it, nothing reads it from DB  
  - `unrealized_pnl`, `total_pnl`: pre-drop audit needed — `analysis/trader_performance_analysis.py` reads both from `traders`  
  - `roi_percentage`: `monitoring/diagnostics.py` reads it from `traders` (lines 394–396) — must update before dropping  
- **Rename 4 API columns:** `wallet_creation_date → api_wallet_creation_date`, `true_wallet_age_days → api_true_wallet_age_days`, `funding_wallet → api_funding_wallet`, `is_contract_wallet → api_is_contract_wallet`  
**SOURCE:** Sessions #38 (blueprint), #39 (carried), #40, #41, #42 (weighted_win_rate added)  
**STATUS:** OPEN. All 8 columns (4 dead + 4 API) confirmed present in DB; none dropped or renamed. `roi_percentage` confirmed read by `diagnostics.py FROM traders`; `unrealized_pnl`/`total_pnl` confirmed read by `trader_performance_analysis.py`. Pre-drop audit NOT complete — readers must be updated before any drop.  
**VERIFIED:** `python3 -c "... PRAGMA table_info(traders)"` confirms all 8 columns exist with original names (2026-06-29).  
**DEPENDENCIES:** Pre-drop readers audit must precede the drop. API rename is independent and safe (no scoring reads them per session #38). Dead-column drop should come after competing-writer teardown (O-6) since some writers target these columns.  
**RISK/EFFORT:** Medium. The rename is small and safe. The drop requires auditing ~4 reading scripts and updating or retiring them.  
**FROZEN-AREA?** No — dead columns have no ELO chain contact.

---

### O-5 · Competing-writer teardown (non-ELO columns)
**ITEM:** Remove competing writers for columns where `reconcile_trader_aggregates.py` is now canonical:  
- `successful_trades`: `monitoring/trader_statistics.py:302` still writes it (resolution_based won_trades) — competes with reconciler  
- `total_trades` / `total_volume`: `trader_statistics.py` carries forward existing values  
- `open_positions` / `closed_positions` on `traders`: `monitoring/monitor.py:1180-1181` writes both on every 15-min cycle — competes with reconciler  
- `specialisation_ratio`: `analysis/analysis_scheduler.py` writes from `trader_categories` (the source-of-truth table); `reconcile_trader_aggregates.py` ALSO writes it. Both paths may produce different values depending on execution order.  
**SOURCE:** Sessions #38 (full competing-writer map), #39, #40 (all listed as pending teardown)  
**STATUS:** OPEN. Confirmed live by grep:  
- `trader_statistics.py:302` writes `successful_trades=stats['resolution_based']['won_trades']`  
- `monitor.py:1180-1181` writes `closed_positions = ?, open_positions = ?`  
- `analysis_scheduler.py:469-470` writes `specialisation_ratio` from `trader_categories`  
**DEPENDENCIES:** Blocked by nothing. But teardown should precede running the reconciler as a daily cron job (currently reconciler runs deliberately/manually until competing writers are removed — session #38 standing rule). Should also precede Layer 2 (O-7) to reduce writer confusion during ELO rebuild.  
**RISK/EFFORT:** Medium. Monitor.py is production-critical; `trader_statistics.py` is less so. Each neutralization needs grep-verify-harness-commit cycle.  
**FROZEN-AREA?** No — these are Layer-1 aggregate columns, not ELO chain.

**UPDATE 2026-07-06 — SEQUENCING CORRECTED, CONSOLIDATED into the ELO-arc design.** The original assumption ("O-5 should precede Layer 2 to reduce writer confusion") was checked against what the canonical ELO formula actually reads and found too broad. `trader_statistics.successful_trades`, `monitor.py`'s `traders.open/closed_positions` columns, and `analysis_scheduler.specialisation_ratio` are **not read by any ELO formula path** — none of them block O-7. Verified: the confidence-cap gate reads `closed_positions` from `pnl_cache`/the `positions` table directly (`apply_full_elo_modifiers.py:177-178`), never from the contested `traders.closed_positions` column. **The only real O-5-adjacent precursor to O-7 is `resolved_trades_count`** (feeds the soft cap and thin-sample gates) — its sole non-canonical writer is dead Writer C (`integrate_behavioral_elo.py:196`), so deleting Writer C (already needed per O-6/O-7 below) makes it single-writer for free. Full analysis in `2026-07-06-elo-arc-design-FABLE.md` §7. **The rest of O-5 (the three items above) proceeds independently, whenever convenient, on its own merits — it no longer gates Layer 2.**

---

### O-6 · `comprehensive_elo` competing-writer teardown (ELO daily path — Path A vs B)
**ITEM:** The DAILY path (`scripts/apply_full_elo_modifiers.py`) applies only `pnl_modifier` to `comprehensive_elo` for traders with closed positions (~35/cycle). It reads `base_category_elo` or the current `comprehensive_elo` as its base, applies a pnl damping multiplier, and writes back a new `comprehensive_elo`. This is a different formula from the Sunday full recalc in `elo_bridge.py` (which re-derives all modifiers from trades). The two paths diverge between Sunday runs. This is the **Path A vs Path B** problem, confirmed and named in session #42.  
Active `comprehensive_elo` writers confirmed by grep:  
1. `monitoring/elo_bridge.py` (Sunday full recalc) — uses `UnifiedELOSystem.get_trader_global_elo()` + behavioral cache  
2. `scripts/apply_full_elo_modifiers.py` (daily) — reads stored `base_category_elo`/`comprehensive_elo`, applies pnl damping  
3. `scripts/integrate_behavioral_elo.py` (on-demand) — writes `comprehensive_elo` directly (lines 254 + 601)  
**SOURCE:** Sessions #40, #41, #42 (all three explicitly name this)  
**STATUS:** **INVESTIGATED-COMPLETE (2026-06-29, session tonight).** The diagnostic is done; no code changes made. Key findings:

- **Behavioral not in `comprehensive_elo` is INTENTIONAL (RQ-CONTESTED-001, documented 2026-06-05).** `monitoring/system_observer.py:2956–2977` explicitly disables a behavioral writer with the note: *"silently discarded by apply_full_elo_modifiers.py which overwrites comprehensive_elo without reading it. Intentionally disabled until comprehensive_elo formula is redesigned (RQ-CONTESTED-001, July 2026)."* This is not a new discovery — it was a known design decision.

- **Proven mechanism:** Writer A (Sunday ELO, `full_elo_recalculation`) writes `comprehensive_elo = base × behavioral × pnl` at ~04:17 UTC Sunday for all 22,650 flagged traders. Writer B (`apply_full_elo_modifiers.py`, daily_maintenance step 24) runs every day at ~08:46 UTC and overwrites `comprehensive_elo = base × pnl` for the ~20,035 traders with ≥1 closed position. Writer B does NOT write `behavioral_modifier`, so that column retains Sunday's 1.4 value while `comprehensive_elo` is stripped to base×pnl — the source of the "stored 1.4 but applied 1.0" apparent contradiction.

- **Empirical proof:** 17,685/17,685 (100%) flagged non-excluded traders satisfy `|comp_elo − base × pnl| < 1.0`. DB timestamps confirm: June 28 04:16 UTC (2,471 traders, Sunday ELO) vs June 29 08:46:35 UTC (20,035 traders, Writer B). Writer B is the last writer.

- **Two documented fix options for O-7:** (a) Remove Writer B from daily_maintenance (Sunday's write becomes permanent); (b) Make Writer B read `behavioral_modifier` from DB and incorporate it alongside P&L. Full spec in `brain/decisions/2026-06-29-comprehensive-elo-writer-map.md` Section 7 (corrected) and Section 9 (root-cause report).

**DEPENDENCIES:** **Directly blocks Layer 2 (O-7).** Diagnostic is now complete; the design choice (option a vs b) must be made as part of O-7.  
**RISK/EFFORT:** Diagnostic done (zero effort remaining). Design decision = small; implementation = medium.  
**FROZEN-AREA?** YES — directly touches `comprehensive_elo`. All changes here need output-neutral proof (same pattern as session #42's `bd82fd7` approach).

**STATUS UPDATE 2026-07-06 — remains INVESTIGATED-COMPLETE; the design decision this item deferred to O-7 has now been made.** See O-7 below — CONSOLIDATED into `2026-07-06-elo-arc-design-FABLE.md`. Also newly confirmed today: **Writer D** (`elo_bridge.py`'s `quick_elo_update_for_traders`, this doc's writer #4 not listed above at the time) **is dead** — its only production call site was inside `check_market_resolutions()`, deleted by the O-13 stall-fix commit `ca30c07` (2026-07-02), an unintended side effect of that unrelated fix. Independently re-verified 2026-07-06 (grepped every caller in both repos, every write to `comprehensive_elo`, full crontab/systemd/deploy for any reachable path) — confirmed zero exceptions. **The live writer set collapsed from 4 (or effectively 3, Writer C already dead) to exactly 2: A (Sunday) + B (daily).** This materially simplified the O-7 design.

---

### O-7 · Layer 2 ELO chain reconciler
**ITEM:** Build a single-writer reconciler for `comprehensive_elo` and its full chain (`base_category_elo`, `behavioral_modifier`, `advanced_modifier`, `pnl_modifier`, `kelly_alignment_score`, `patience_score`, `timing_score`). Must:  
1. Resolve Path A vs Path B formula — pick canonical and discard the other  
2. Add `comprehensive_elo` harness coverage to `audit_invariants.py` (currently ZERO coverage confirmed)  
3. Enforce single-writer semantics for the ELO chain  
4. Resolves Cluster D (~1,346 traders with modifiers at 1.0 after being processed — ambiguous per forensic map) by re-deriving all values from trade history  
**SOURCE:** Sessions #38 (full spec), #39, #40, #41, #42 (all four list it as "the big next piece"). Forensic map Section 4 Tier 1.  
**STATUS:** OPEN. No code exists. `scripts/reconcile_trader_aggregates.py` is the Layer 1 reconciler (simple aggregate columns). No Layer 2 equivalent exists. `comprehensive_elo` harness checks: 0 (confirmed by reading 2026-06-29 audit JSON — no checks targeting this column).  
**DEPENDENCIES:**  
- **Blocked by:** O-6 (must understand/resolve the daily-path behavior before designing the reconciler)  
- **Unblocked by completion of:** O-5 (non-ELO competing writers removed), O-6 (daily path behavior resolved), test suite green (DONE, #42)  
- **Unlocks:** ELO recalc unfreeze (the standing freeze since session #38). Until Layer 2 is done + harness clean, `recalculate_comprehensive_elo.py` stays frozen.  
**RISK/EFFORT:** Large. Complex orchestration of `UnifiedELOSystem` + `TradingBehaviorAnalyzer`. The session summaries flag this consistently as "complex, fresh session." Behavioral data now populated (#42), removing one blocker.  
**FROZEN-AREA?** YES — this IS the frozen area. Must be ELO-output-neutral at every intermediate step. Same discipline as session #42 (byte-identical avg/range verification before/after).  
**DOWNSTREAM IMPACT CONFIRMED (2026-06-30):** STR-002's ELITE/QUALIFIED tier-gating reads `comprehensive_elo` directly (`scripts/pre_resolution_intelligence.py`) and is measurably degraded by the missing behavioral component — see `2026-06-30-str002-thesis-cell-analysis.md`. This is no longer an abstract data-quality concern; it's a live strategy underperforming partly because of it. Strengthens the case for prioritizing O-7.

**STATUS CHANGE 2026-07-06 — DESIGN COMPLETE, CONSOLIDATED. Plan of record: `brain/decisions/2026-07-06-elo-arc-design-FABLE.md` (built commit `11f1a51`, corrected commit `6495006`), pending Oscar's review.** This item — the full O-7 spec (canonical formula, single-writer architecture, harness coverage, Cluster D note) — is now designed end to end:
- **Canonical formula** (item 1): Writer B's dampened-additive-gains structure extended with a bounded, shared-weight behavioral delta (`W_beh`, scales both the multiplicative and bonus halves together) — not Writer A's multiplicative compounding. Full worked examples and rejected-alternatives reasoning in the design doc §2.
- **Behavioral re-incorporation** (this item's open question, and RQ-CONTESTED-001's core ask): behind a Stage-0 read-only validation study; ships even if the answer is "no signal" (`W_beh=0`, architecture still lands).
- **Single-writer architecture + harness** (items 2–3): one pure formula function, one atomic full-column write helper (kills the "columns from different writers at different times" artifact class structurally), 9 harness invariants incl. a formula-reproducibility check that mechanically enforces single-writer semantics going forward.
- **Cluster D** (item 4): explicitly scoped OUT of this design (§8) — unifying *how* comprehensive_elo is computed is this item's job; *who* gets one (the ~100K non-flagged scope gap) is deliberately deferred to its own item post-migration, to avoid confounding population diffs during the migration itself.
- **Migration path** (new, not originally scoped in this item): 6 staged, individually-reversible steps — Stage 0 (precursors, no frozen-area contact) → Stage 1 (shadow computation) → Stage 2 (Writer B onto canonical plumbing, output-neutral) → Stage 3 (Writer A onto canonical plumbing + soft cap/floor activate) → Stage 4 (the one-constant behavioral flip) → Stage 5 (cleanup + unfreeze). Full detail in the design doc §5.
- **Verification discipline held**: the design's own "Stage 2 is provably output-neutral" claim was independently re-verified against live code and the live DB before being banked, and was found false as originally written (a bonus-scaling bug affecting 85% of the population, plus a 9-trader soft-cap discrepancy) — caught and fixed same day (commit `6495006`). The corrected claim is now genuinely, term-for-term verified.

**Next-session entry point:** Stage 0 — **0c** (delete dead Writer C, `integrate_behavioral_elo.py`; dead code removal, no frozen-area output change) and **0b** (behavioral validation study, read-only) can start as soon as Oscar has reviewed the design doc. **0a** (waiting for the O-15 backlog drain — see O-15 below — to plateau, so ELO-migration baselines aren't measured against a moving pnl_modifier input) gates the shadow-computation stage (Stage 1) that follows. None of Stage 0 touches the frozen area in a way that changes ELO output.

---

### O-8 · `insert_position` dedup edge case (latent, non-blocking)
**ITEM:** `database.py insert_position` uses a conflict key of `(market_id, outcome, entry_timestamp)`. Two positions sharing the same market/outcome/entry_timestamp but different exit/PnL data will collide on insert. Identified as a latent data-integrity edge case. Not known to be triggering in production.  
**SOURCE:** Session #41 (identified as a latent edge case, explicitly deferred as non-blocking)  
**STATUS:** OPEN (latent). No fix applied. No evidence it has triggered. But with 5M+ positions and the OR-REPLACE → ON-CONFLICT-DO-UPDATE migration (#41), the dedup semantics are cleaner now; this is about the conflict key itself being too narrow.  
**DEPENDENCIES:** Independent. Non-blocking. Could be addressed as part of any positions write-path work.  
**RISK/EFFORT:** Small (add a unique constraint or widen the conflict key). Low urgency.  
**FROZEN-AREA?** No.

---

### O-9 · trading-swarm data-layer audit
**ITEM:** Run the same Phase 2–style invariant diagnostic on the `trading-swarm` repo's brain/ data layer (signals.json, findings.json, strategy-registry.md, agent-output files). Identify the writer-count / fact-in-multiple-places disease in the swarm's own data structures.  
**SOURCE:** Sessions #38, #39, #40 (all carry "trading-swarm data-layer audit — same diagnostic applied to second repo")  
**STATUS:** **CLOSED 2026-07-07** — folded into and superseded by the Fable silent-failure audit's Class 6 (`2026-07-07-silent-failure-audit-FABLE.md`), which mapped the full trading-swarm ↔ first-repo write/read topology (3 code paths: `calculate_geo_elo.py`, `orchestrator/ollama_agent_loop.py`, read-only research scripts) and found real issues — see O-24 (agent write-allowlist prefix-match) below. No separate swarm-internal-only invariant scan was built; the cross-repo connection was judged the higher-leverage surface and is now covered.  
**DEPENDENCIES:** Independent of ELO rebuild. Can be done any time. Useful before scaling the swarm.  
**RISK/EFFORT:** Medium (mostly investigation/research; fixing findings is separate). Read-only diagnostic.  
**FROZEN-AREA?** No.

---

### O-10 · Composite scorer (Phase 3b) scheduling decision
**ITEM:** `analysis_scheduler.py run_phase_3b_composite_scores()` runs whenever `analysis_scheduler.py` is called. It's not wired into `daily_maintenance.py`. With behavioral data now fully populated (#42, ~22K traders with kelly/patience/timing scores), the composite scorer now produces real differentiation (not uniform 7.5/15 neutral midpoints). The open question: should Phase 3b run on a scheduled cadence (daily, weekly) or remain on-demand?  
**SOURCE:** Session #42 ("Composite scorer Phase 3b behavioral differentiation restored") — raised implicitly because the behavioral data fix now makes scheduling worthwhile.  
**STATUS:** OPEN (decision). Not wired into maintenance. Phase 3b runs on-demand only.  
**DEPENDENCIES:** Unblocked (#42 fixed the behavioral data that was making scores uniform). Independent of ELO rebuild.  
**RISK/EFFORT:** Small once decided. Weekly seems natural (behavioral data refreshes Sunday; composite can run Monday).  
**FROZEN-AREA?** No.

---

### O-11 · Phase 4 swarm tending — research-scout backlog
**ITEM:** 40+ items have accumulated in `brain/research-scout/pending-review/` (June 14–June 29). Multiple items repeat across daily runs (same papers appearing in 3–5 separate daily batches without being triaged). Agent output backlog also exists across feedback-loop, training-librarian, performance-analyst, and signal-agent.  
**SOURCE:** Session #40 and later (Phase 4 swarm tending was in the #38 NEXT list as "later sessions"). Research-scout was the most visible backlog as of June 29.  
**STATUS:** OPEN. Verified: `brain/research-scout/pending-review/` contains 40+ distinct files from 2026-06-14 through 2026-06-29. Notable repeating items:  
- `when-do-markets-fully-process-public-information` (appears in 5+ daily batches — high relevance to detection latency item in strategic roadmap §5.1.2)  
- `foresightflow-information-leakage-score-framework` (appears 4+ times)  
- `polymarket-exchange-upgrade-v2-sdk` (actionable — affects execution layer)  
- `deepseek-v4` / `prediction-markets-underperform-baselines` (strategic interest)  
**DEPENDENCIES:** Independent of ELO rebuild. Triage session needed (human review + approve/dismiss/archive). Dedup is the first step (remove repeated filings of the same paper before reviewing).  
**RISK/EFFORT:** Small per item; medium as a batch. Best handled as a dedicated triage session.  
**FROZEN-AREA?** No.

---

### O-12 · Resolution-collection ID-routing gap (permanent-loss class)
**ITEM:** Some `market_id`s are unroutable through any resolution-collection path: CLOB returns empty, Gamma doesn't recognize the hex ID, and there is no `api_id`/`condition_id` to fall back to the fast path. Example: Putin market `0x657195fda8...`, `last_checked` 2026-04-01 — 90 days stale as of today. These markets can **never** be collected as things stand — this is a **permanent loss**, distinct from the cap-latency gap fixed today in commit `6c08afc` (round-robin rotation for the recent-overdue resolution pass, first-repo), which addresses staleness from throughput limits, not unroutable IDs. Likely cause: a V1/V2 market identifier format mismatch.  
**ALSO FOLDED IN:** Monitoring-service Gamma-null observability (warn on markets with no `api_id`/`condition_id`) — scoped earlier today but deferred; rather than tracking separately, it's the natural detection mechanism for this item, so it's folded into O-12's scope.  
**SOURCE:** Identified 2026-06-29/30 alongside the round-robin rotation fix (`6c08afc`, first-repo).  
**STATUS:** OPEN — uninvestigated. Needs its own investigation: (1) characterize how many markets are affected, (2) determine why their IDs don't route through CLOB or Gamma, (3) determine whether backfilling `api_id`/`condition_id`, or adding a V1 resolution path, resolves it.  
**DEPENDENCIES:** Independent of the ELO rebuild arc. No frozen-area contact.  
**RISK/EFFORT:** Unknown until characterized — investigation is read-only to start. NOT urgent (affects a subset of markets), but real and currently silent (no observability until the Gamma-null warning above is built).  
**FROZEN-AREA?** No.

---

### O-13 · Monitoring service blocking-call stall (event-loop starvation during resolution scans)
**ITEM:** `check_market_resolutions()` (`monitoring/trader_analyzer.py:121`) is a synchronous function called directly from the async main loop (`monitoring/monitor.py:1261`). Its up-to-300,437 sequential per-market HTTP calls run with no `await`/yield, blocking the entire asyncio event loop for the scan's full duration — starving every other scheduled async task (`pnl_worker`, `watchdog`, `backfill_worker`) until the scan finishes. On July 1 the scan had been blocking the loop for 73+ minutes and was only 12% complete (37,160/300,437) when the concurrent power outage hit.
**SOURCE:** Discovered during July 1 power-outage forensics (house power loss, ~02:54–07:26 UTC). Initially misread as a file-logging failure — `logs/monitoring.log` (the `logging`-module output) goes silent for the scan's duration, but the systemd journal keeps showing `[RESOLUTION] Checking market...` lines throughout, because those come from `print()` calls inside the blocking function, which bypass the stalled event loop by writing straight to stdout.
**STATUS:** INVESTIGATED — design complete, including a removal-safety checklist, not yet implemented. Full duty-cycle/scope/redundancy analysis in `brain/decisions/2026-07-01-o13-monitoring-blocking-stall-design.md`. Key findings: (1) full scan at current 300,437-market scope is now an estimated ~10.4h, an ~82% event-loop-blocked duty cycle every 2.5h meta-cycle; (2) 78.4% of scan scope is O-12-class unroutable markets (no `api_id`/`condition_id`) that provably return no data every run; (3) **all 21 completed runs in the retained journal (May 21–Jun 5) resolved zero markets**, extended by DB-forensic evidence (a unique `winning_outcome = name.lower()` signature) to **~7 months of zero output — last successful resolution 2025-12-11**, a one-time 15-market batch, nothing since; (4) `scripts/fast_resolution_check.py` (run daily via `daily_maintenance.py`) already covers the same market population with correct rotation and CLOB fallback, and its own docstring describes itself as the fix for exactly this per-market approach; post-resolution P&L/ELO work is independently duplicated by `requeue_resolved_market_traders.py` → background P&L worker → `evaluate_new_trader_results.py` → `apply_full_elo_modifiers.py` (confirmed via direct comparison of query criteria, not assumed). **The duplication claim was verified, not assumed**: the doc's §5b checklist found exactly one real (but tiny, 0.24%-of-scope = 724 markets) coverage gap — markets with an `api_id`/`condition_id` but no date field, reachable only by the bulk Gamma pass's 50K-recency cap — flagged as the one open pre-removal verification step (a handful of live API spot-checks) rather than assumed safe. **Recommendation: remove the call (`monitor.py:1261`) and retire `check_market_resolutions()`, not async-ify it** — offload/chunking (`run_in_executor` / `asyncio.sleep(0)` yields) is documented as a fallback if the team prefers a staged rollout. Also surfaced and resolved: a second synchronous blocking call (`scan_for_successful_traders()` at `monitor.py:1237`) shares the same `cycle_count % 10 == 0` branch and compounds the stall — checked against `promote_high_pnl_traders.py` and confirmed **not** redundant (it's the sole new-trader-discovery path; the P&L-promotion script only updates traders already in the DB), so its fix is offload (`run_in_executor`, matching the existing precedent at `monitor.py:802`), not removal.
**DEPENDENCIES:** Independent of the ELO rebuild arc. No frozen-area contact — this is a monitoring-service concurrency issue, not an ELO-chain issue.
**RISK/EFFORT:** Low-Medium now that the design is scoped. Real production impact confirmed: the watchdog meant to catch problems is itself starved (not "unscheduled" — it's a correctly-scheduled asyncio task that can't get CPU time back while the sync call holds the single event-loop thread) during the stall, so the monitor is effectively blind to its own health for the scan's full duration. Implementation (removal + the one-line `scan_for_successful_traders` fix) is a same-session task for next time, not a same-session design task — that's what this entry is closing out.
**FROZEN-AREA?** No.

**IMPLEMENTED 2026-07-02 (commit `ca30c07`) — with a bonus effect on the ELO arc, discovered 2026-07-06.** The `check_market_resolutions()` removal took out `quick_elo_update_for_traders`'s only production call site along with it (it sat inside the deleted function's post-resolution "Step 3" block) — an unintended side effect, not a deliberate ELO change. This killed **Writer D**, one of `comprehensive_elo`'s competing writers, for free. Independently re-verified 2026-07-06 as part of the O-7 design work (see O-7 above) — confirmed zero remaining production callers anywhere in either repo. The live ELO-writer set is now exactly 2 (A + B), not 4, which materially simplified the O-7 design.

---

### O-14 · Offsite backup mount silently failing since June 20 (ext4 label truncation)
**ITEM:** `/mnt/backup` was not mounting via `fstab`'s `LABEL=polymarket-backup` entry — `backup_offsite.sh` had effectively been running against an unmounted mount point.
**SOURCE:** Identified and resolved 2026-07-01 during backup-system investigation.
**STATUS:** RESOLVED (2026-07-01). Root cause is NOT a truncated/accidental label as first suspected — ext4 volume labels are hard-capped at 16 characters, and `"polymarket-backup"` is 17 chars. `e2label` always silently truncated it to `"polymarket-backu"` (confirmed by re-attempting the set, which reproduced the same truncation). `fstab`'s `LABEL=polymarket-backup` could therefore never match, so mount-by-label silently no-op'd (exit 0, nothing mounted) on every boot from June 20 through July 1, surviving 3 reboots — a structural fstab bug, not a disk/mount race.
**FIX:** Switched `fstab` from `LABEL=` to `UUID=299b7d20-68a9-40c3-b3ee-513529ee689b` (immune to the 16-char constraint). `/etc/fstab` backed up first (`fstab.bak-20260701`). Confirmed mounted post-fix: 916G total, 850G free. A full offsite backup ran successfully afterward (brain synced, DB backup complete, 14-day pruning working, 23G used on the drive).
**VERIFIED:** `df -h /mnt/backup` shows 916G/850G free; `backup_offsite.sh` completed end-to-end with no errors.
**FOLLOW-UP (low-priority):** Confirm after the next reboot that the UUID-based `nofail` entry auto-mounts cleanly — expected to work since UUID has no length constraint, but not yet observed across a reboot.
**STILL OPEN (separate, not investigated):** A doubled-cron-entry anomaly — `backup_offsite` wrapper possibly firing twice since June 14. Minor, not yet investigated; not part of this item's scope.
**DEPENDENCIES:** Independent of the ELO rebuild arc. No frozen-area contact.
**RISK/EFFORT:** None remaining — fix applied and verified.
**FROZEN-AREA?** No.

---

### O-15 · [SLOT LOST] `background_pnl_worker.py` naive/aware datetime bug — needs a proper entry
**ITEM:** A user-observed bug in `background_pnl_worker.py:410` — a naive-vs-timezone-aware `datetime` comparison — self-limits via the `pnl_skip` circuit breaker, affecting roughly 1,504 addresses since April 2026. **This slot number (O-15) and the bug itself were referenced by the user on 2026-07-01 as something discussed in an earlier session, but no matching entry, session summary, or investigation exists anywhere in trading-swarm or first-repo** — searched all `brain/decisions/*.md` session summaries and the ledger itself; the only related-but-different findings are a `background_pnl_worker.py` `failed_traders`-dict-reset bug (session summary 2026-06-01, a different bug) and the position-table `INSERT OR REPLACE` fix (session summary 2026-06-25, also different). **The original O-15 investigation is genuinely lost — not fabricated, not recoverable from anything currently in either repo.** Recording this placeholder so the slot isn't silently reused and the bug description survives even without its original investigation. Needs a real read-only investigation next session: confirm the exact naive/aware comparison at `background_pnl_worker.py:410`, characterize the 1,504-address figure against live data, and determine whether the `pnl_skip` circuit breaker is fully containing the blast radius or just delaying it.
**SOURCE:** User-reported 2026-07-01, description only — no prior doc found.
**STATUS:** OPEN — not investigated by any session with a document trail. Placeholder only.
**DEPENDENCIES:** Unknown until investigated — `background_pnl_worker.py` touches trader P&L, so plausibly adjacent to the ELO/signal-accuracy arc, not confirmed.
**RISK/EFFORT:** Unknown until investigated.
**FROZEN-AREA?** Unknown until investigated.

**RESOLVED 2026-07-06 (first-repo commit `54f3d77`).** Investigated, root-caused, fixed, and rolled out same day: the naive/aware bug is in `position_tracker.py:94`, `close_position()`'s `exit_timestamp − self.entry_timestamp` (aware `resolution_date`-derived timestamps subtracted against naive `trades.timestamp`-derived ones) — proven via live traceback, 7,218 occurrences in `monitoring.log`, 1,419/1,420 logged `pnl_skip=1` events directly attributable. Because the exception fired before the position-persist step, it silently aborted writing **all** of that trader's positions for the cycle, not just the offending one — confirmed as the direct mechanism behind "BUY trades with no position record" growing ~17K/day. Fix: `close_position()` strips `tzinfo` from both sides before subtracting (lossless, all timestamps are UTC). Rollout staged, not blind: 8 confirmed-affected traders reset and reprocessed live first (all succeeded, no re-fail), then the remaining 1,413 bulk-reset. **All 1,421 previously-permanently-excluded traders are now `pnl_skip=0`** and self-healing via the normal background P&L worker cadence — not an active generator anymore, but the backlog it left behind (part of the ~482K "BUY trades no position" count) drains gradually as traders get reprocessed, not in one shot. **This is why O-7's Stage 0a waits on this drain plateauing** before ELO-migration baselines are taken — `pnl_modifier`'s input data is moving right now. Watch the harness count next session (see session summary).

---

### O-16 · Resolution under-collection gap, quantified (194,216 markets, static historical backlog)
**ITEM:** `check_market_resolutions` removal (O-13) rested on `fast_resolution_check.py`'s 4-pass pipeline being an adequate replacement. That pipeline has its own gap, now measured in full: **194,216 markets** (100% with a routable `api_id`/`condition_id` — not O-12 class) sit `resolved = 0` with `end_date` >7 days in the past and `resolution_date` still `NULL`, structurally unreachable by any of the 4 passes (Pass 1 can't see them — no `endDate` field on Gamma's side at all; Pass 3 hard-requires `resolution_date IS NOT NULL`, which these never get). A live 40-market spot-check (read-only Gamma calls) found a **95% hit rate** — the large majority are already resolved on Polymarket, just never written back. Extrapolated: **~184,000-194,000 genuinely-resolved markets currently missing locally.**
**SOURCE:** Follow-up to O-13's §5b spot-check (which found the same pattern in a 724-market subsegment). Full quantification: `brain/decisions/2026-07-01-o16-resolution-collection-gap-quantified.md`.
**STATUS:** INVESTIGATED (read-only, 2026-07-01) — measurement + design, no fix implemented yet. **Key verdict: STATIC, not growing.** 194,215 of 194,216 (99.9995%) share `data_source = 'historical_backfill'` and an identical frozen `last_checked` (2025-12-11) — a one-time import artifact, the same date as O-13's forensic "last successful resolution" finding. Live-monitoring-sourced markets are unaffected at scale (1 stuck vs 24,333 clean) — the current, ongoing pipeline is healthy; this is backlog debt, not an active leak. **Not a "nobody cares" population**: 62,407 of the 194,216 (32%) have a trade from a flagged, non-research-excluded trader; 19,084 of 22,390 such traders (85%) have exposure to at least one stuck market — this touches the large majority of the tracked/scored trader pool, relevant to ELO/signal accuracy (cross-ref RQ-CONTESTED-001, O-0). **Separately confirmed and quantified**: Gamma's `/markets` list endpoint now hard-errors past offset ~2,100 (`"offset too large, use /markets/keyset"`), so Pass 1's real reach is ~2,100 closed markets per run, not the 50,000 the code assumes (~95.8% shortfall) — a real, additional finding, but not the cause of the 194,216 backlog (those are excluded by the missing `endDate` sort key, not the cap).
**FOLLOW-UP (2026-07-01, same day, doc §6-7):** **Confirmed the generator is dormant, not just quiet** — traced every write path touching `end_date`/`resolution_date` and found the co-write guarantee (`resolution_date` always populated whenever `end_date` is first set) was added repo-wide by commits `4cdd190`/`446bcde` on 2026-05-31; zero new instances of the 194,216's pattern have appeared since (verified: 0 rows with `last_checked` after that date). **A one-time backfill is a permanent fix — no code fix required first.** Investigated the widened 3-row (not 1) live-monitoring exception: all 3 share one `last_checked` (2026-01-12), predating the May 31 fix; the one currently-overdue member is an O-12-class unroutable-ID fluke (28 real trades, but neither Gamma nor CLOB recognizes its `condition_id`), not a leak. **Separately found a different, currently-active, small-scale generator** (182 rows and slowly growing) that silently breaks `requeue_resolved_market_traders.py`'s `resolution_date`-filtered requeue — **fully mechanized, corrected, and designed as O-17 below** (this entry's original attribution to `resolve_legendary_markets.py`/`legendary_positions_scan.py` as the primary cause was incomplete; see O-17 for the corrected root cause). Not part of the 194,216. **Backfill design scoped and ready**: ~2.6-5hr runtime at light concurrency (measured: 2.17 req/s sequential → 20.5 req/s at concurrency 10, 0 errors in test batches), resumable via the existing `resolved=0` filter (no new progress table needed), Gamma per-ID endpoint confirmed working (30/30 fresh sample, 95+/95 overall), plain `UPDATE` only (no `INSERT OR REPLACE` risk — confirmed absent from the `markets` table's writers), new `data_source='gamma_backfill_2026-07-01'` for provenance, prioritized by the 62,407/5,883/125,926 trader-relevance tiers (Tier 1 alone ≈ 1.6hr).
**DEPENDENCIES:** Independent of the ELO rebuild arc structurally, but the flagged-trader overlap (§3 of the doc) makes it relevant to the ELO/signal-accuracy arc as a candidate contributing factor — not causally established here. Builds on and closes out the open question O-13 §5b left partially unquantified at system scale.
**RISK/EFFORT:** Medium, and now fully scoped. Ready to implement this week: (1) the bounded one-time backfill per the design above — highest leverage given the 85% trader overlap; (2) O-17 below (separately scoped); (3) fix the `run_recent_overdue_pass`/`run_stale_clob_pass` handoff so markets that age past 7 days unresolved don't become permanently orphaned (low current urgency, real structural bug, could recur); (4) lower-priority — migrate `fast_resolution_check.py` to Gamma's `/markets/keyset` pagination to recover Pass 1's intended reach.
**FROZEN-AREA?** No.

---

### O-17 · `resolution_date` co-write gap — 3 files, 5 broken call sites, currently active
**ITEM:** 182 markets (and growing, ~1-57/day) have `resolved = 1` (correctly resolved, `winning_outcome` set) but `resolution_date` still `NULL` — this silently breaks `requeue_resolved_market_traders.py:76`'s `resolution_date`-filtered query, meaning **traders in these markets never get requeued for P&L recalculation.** Full mechanism, fix design, backfill, test plan, and full-codebase audit: `brain/decisions/2026-07-01-o17-resolution-date-cowrite-gap-design.md`.
**SOURCE:** Found during O-16's same-day follow-up (§6.4), then re-investigated and corrected same day after the user asked for the mechanism to be confirmed precisely rather than taken on the first pattern-match.
**STATUS:** INVESTIGATED (read-only, 2026-07-01), fix designed, not yet applied. **Corrected root-cause attribution**: the O-16 §6.4 note named `resolve_legendary_markets.py`/`legendary_positions_scan.py` as the generator; re-reading every candidate write path end to end found the **actual dominant mechanism is 3 of the 4 passes in `fast_resolution_check.py` itself** (`run_recent_overdue_pass:492-499`, `run_stale_clob_pass:383-389`, `run_external_seed_pass:588-595`, all scheduled daily, category-unrestricted) — confirmed by matching a sampled market's `end_date`/`last_checked` signature and by 118 of 182 affected rows being `category='Unknown'` (World Cup markets), outside `legendary_positions_scan.py`'s geo-category scope. `legendary_positions_scan.py`'s `_resolve_one_market` (lines 304, 314, weekly) is a real secondary generator (its query isn't `resolution_date`-gated). `resolve_legendary_markets.py` (lines 210, 215, daily) has the identical missing-column bug but is **currently self-protected/inert** — its own input query requires `resolution_date IS NOT NULL`, so it cannot produce a new NULL row today, only if that filter is ever loosened. **Impact-scope correction**: not LEGENDARY-specific — of the 182, only 27 (15%) are LEGENDARY-linked; 147 (81%) are linked to the general flagged/clean trader pool. **Why 3 new scripts all missed the same fix**: all three were written 9-14 days *after* the 2026-05-31 co-write-convention commits (`4cdd190`/`446bcde`) — not an audit miss, new code that never inherited a convention that was never encoded as a shared helper, lint rule, or test. **Full-codebase audit (12 candidate writers)**: 7 broken, all concentrated in exactly these 3 files; every other resolution writer (`database.py`'s canonical functions, `fix_expired_unresolved.py`, `fetch_market_resolutions.py`, `hydrate_stub_markets.py`) is correct.
**FIX (designed, not applied):** add `resolution_date = COALESCE(resolution_date, ?)` to all 5 broken `UPDATE` statements (one extra bound param each), matching the exact idiom already established in `monitor.py`/`database.py`. Separately: a single-statement retroactive backfill for the existing 182 (`UPDATE markets SET resolution_date = last_checked WHERE resolved = 1 AND resolution_date IS NULL` — no API calls needed, `last_checked` is already the correct detection-time proxy) — should run *before* the generator fix, since it's what actually restores visibility to `requeue_resolved_market_traders.py` for the 147/27 affected traders; the generator fix only stops new rows joining. **Larger-scope recommendation**: extract a shared `Database.mark_market_resolved()` helper so a hypothetical 6th script can't reproduce this a third time — scoped, not designed in full.
**TEST:** two-part — (1) per-call-site unit test asserting `resolution_date` gets written on a mocked resolve, (2) end-to-end test asserting `requeue_resolved_market_traders.py` actually catches the market afterward (the real contract this bug breaks, not just the column). Full pseudocode in the design doc §4.
**DEPENDENCIES:** Independent of the ELO rebuild arc structurally, but affects P&L requeue timeliness for the flagged trader pool broadly (not narrowly LEGENDARY) — relevant to ELO/signal accuracy. Independent of O-16's backfill (different rows, different mechanism) but should be sequenced alongside it as part of the same maintenance-quality push.
**RISK/EFFORT:** Low. 5 one-line SQL changes + 1 backfill statement + 2 tests. No frozen-area contact. Ready to implement the moment `daily_maintenance.py` (PID 6794, currently running) finishes.
**FROZEN-AREA?** No.

---

### O-18 · Pre-bug NULL `resolution_date` rows (historical, static, distinct from O-17)
**ITEM:** 55 markets (corrected from an initial 60 estimated 2026-07-01) have `resolved = 1` but `resolution_date` still `NULL`, with `last_checked < 2026-06-05` — outside the O-17 co-write-bug window. These predate the bug and have a **distinct root cause**: not an active generator leak (that's O-17), but historical rows that were never revisited after being set. Breakdown: 50 rows from the 2025-12-11 `historical_backfill` import (`last_checked` = import time, off by months from any real resolution date — do NOT use as a backfill proxy); 4 rows from a 2026-01-12 `live_monitoring` batch (one with `winning_outcome='unknown'`, unexplained); 1 isolated 2026-04-28 `live_monitoring` anomaly (also missing `end_date`, a third distinct signature). Connected to O-16's 194,216-row backlog only by the shared `2025-12-11`/`historical_backfill` signature — not the same mechanism, likely an INSERT-time gap in the historical importer rather than a co-write gap.
**SOURCE:** First flagged (unledgered) in the 2026-07-01 session summary during O-17 backfill scoping. Properly ledgered and quantified 2026-07-02: `brain/decisions/2026-07-02-o18-pre-bug-null-resolution-dates.md` (includes the current 55 market_ids for future diffing).
**STATUS:** OPEN — quantified only, not investigated further. **Drift note (verified benign):** the 60→55 count change overnight was diffed exactly against two prior-day DB backups and traced to `scripts/backfill_market_dates.py` — an existing, already-safe (COALESCE-based) `resolution_date` writer not previously catalogued in O-17's 12-writer audit — legitimately draining 5 rows via its normal `end_date`-proxy backfill during today's maintenance run. Not corruption; no action needed, but note for O-17's deferred shared-helper work.
**FIX:** Not designed. **Do NOT blanket-backfill with `last_checked`** (proven wrong for the 50-row Dec-11 group). Needs a per-row approach if picked up: re-fetch each from Gamma individually rather than any bulk heuristic; separately explain the `winning_outcome='unknown'` row and the NULL-`end_date` anomaly.
**DEPENDENCIES:** Independent of O-16/O-17/the ELO rebuild arc. No frozen-area contact.
**RISK/EFFORT:** Low urgency (55 rows, static, not growing from any known active generator — though `backfill_market_dates.py` may continue to organically shrink it). Investigation-only effort if picked up.
**FROZEN-AREA?** No.

---

## 2026-07-07 additions (O-19 through O-29)

**Context:** two sessions today. Morning: orientation + verification of the Fable silent-failure audit's headline finding (O-7.1). Afternoon: Claude Fable ran a systematic 7-class silent-failure audit across both repos (`brain/decisions/2026-07-07-silent-failure-audit-FABLE.md`, committed `a8c07f2`) — its own synthesis is worth stating up front as standing guidance, not just a one-off finding: **almost every guard in this system tests presence, nothing tests absence or liveness.** Work that silently stops happening (a step that no-ops, a writer that stops firing, a backlog that stops draining) and columns that silently lose their last reader are both invisible to the current harness by construction. Most of O-22 through O-29 below are instances of that one theme. Keep it in mind when triaging future findings — "does this check for absence, not just wrong presence?" is now a standing design question for any new harness invariant.

---

### O-19 · `backup_database.py` corrupts backups taken while services are running — RESOLVED 2026-07-09 (commit `2e27c2f`, first-repo)
**ITEM:** `scripts/backup_database.py` does a raw `shutil.copy2` of the live `.db` file. The database runs in WAL mode with a continuously-active writer (the monitoring service, 24/7 by design). A plain filesystem copy of a WAL-mode DB under concurrent write load is not crash-consistent — it can capture a torn page mid-write.  
**SOURCE:** Discovered 2026-07-07 during the O-7.1 fix's mandated pre-write backup step. The first backup attempt (`backups/markets_20260707_211327.db`) **failed `PRAGMA integrity_check`**: `database disk image is malformed`, `invalid page number`. A second backup taken via SQLite's online backup API (`sqlite3 <db> ".backup <path>"`, WAL-safe) verified clean and was used for the O-7.1 write.  
**STATUS:** **RESOLVED 2026-07-09.** `backup_database.py` now uses the WAL-safe online backup API instead of `shutil.copy2`, and runs `PRAGMA integrity_check` on the resulting file **before** reporting success — the unconditional `[OK]` on a raw copy is gone. Failure path verified: a corrupt/incomplete backup reports `[ERROR]`, it does not false-report `[OK]` and does not crash the script.  
**NOTE:** the **nightly cron backup** was already using a safe method and was never affected by this bug — this fix specifically closes the gap in the **ad-hoc pre-write** backup path (the one invoked by hand before a DB-writing operation, per CLAUDE.md's backup-first policy), which is what O-7.1's mandated pre-write step exposed on 2026-07-07.  
**FOLLOW-UP STILL NEEDED:** spot-check existing files in `backups/` for restorability (`PRAGMA integrity_check` against each, cheap) to scope how much of the *existing* fleet (backups taken before this fix) is actually damaged — the fix prevents new corrupt backups, it does not retroactively validate old ones.  
**DEPENDENCIES:** None remaining. Closed.  
**RISK/EFFORT:** None remaining.  
**FROZEN-AREA?** No.

---

### O-20 · Stage-0a plateau has two live growth mechanisms — don't call it yet
**ITEM:** The "BUY trades with no position record" metric (the Stage-0a gate for the ELO-migration arc, see O-7) is **not plateauing** — it grew intraday on 2026-07-07: 481,997 (06:00) → 493,783 (21:08) → 496,447 (21:22) → 498,661 (21:32). Prior sessions only sampled this at the daily 06:00 maintenance snapshot, which masked the intraday trend. Two confirmed mechanisms, independent of the O-15 pnl_worker datetime-bug fix and independent of each other:  
**Mechanism 1 (dominant, self-limiting):** `background_backfill_worker.py` discovers previously-untracked traders (`total_trades > 0 AND 0 local trade records`) and bulk-inserts their full historical trade set in one shot (674,862 trades / 2,577 traders on 2026-07-07 alone) — but it **never resets `pnl_last_updated`**, so newly-backfilled traders aren't flagged for priority reprocessing by the pnl_worker; they wait for their own natural staleness cycle. Proven: **100% of the 2,594 traders backfilled today (2,594/2,594) currently have zero position rows.** Bounded, though: the candidate pool (`total_trades>0 AND 0 local records`) dropped from 13,436 to 10,999 over the same day — draining, not growing, roughly ~4 more days at today's rate.  
**Mechanism 2 (smaller, recurring, genuinely stuck — not just lag):** `background_pnl_worker.py:263-336` wraps a trader's *entire* position-insert batch in one try/except with a single commit. If any one INSERT throws (confirmed live cause: `sqlite3.OperationalError: database is locked`), the whole batch rolls back — but `mark_trader_pnl_updated` still fires unconditionally afterward, so the trader is marked "done" with zero positions ever persisted. Architecturally the same failure shape as the original O-15 bug (one bad record voids the whole trader's batch), different trigger. Not a one-off: `Position insert failed` fired on **11 separate days from April 26 through July 5** (bursts up to 150/day), quiet the last two days.  
**SOURCE:** 2026-07-07, read-only investigation requested after independently verifying (and correcting the severity of) the Fable audit's O-7.1 finding — see O-21. Fable's original framing implied the O-16 backfill cohort was "hidden" from the drain entirely; verification found the ordinary 24h staleness rotation *does* eventually sweep them (position counts on backfilled markets more than halved within hours during the same session), so O-7.1 only explains ~12% of the current gap. These two mechanisms explain the rest.  
**STATUS:** OPEN — both mechanisms characterized, neither fixed (read-only investigation, as scoped). **This gates the ELO-arc's Stage 0a** (see O-7): do not baseline migration diffs against `pnl_modifier`/position data while this input is still actively moving.  
**FIX (not designed in detail, natural shape noted):** Mechanism 1's structural fix mirrors O-21's own fix pattern — `background_backfill_worker.py` should reset `pnl_last_updated = NULL` after a successful backfill, the same signal-the-downstream-consumer principle O-21 just restored for the resolution-requeue path. Mechanism 2 needs the same per-item try/except O-15's fix pattern established (catch per-position, not per-batch) plus surfacing "trader marked updated with 0 positions persisted" as a harness-visible event rather than a log-only exception.  
**WATCH:** sample the metric at multiple points across the day, not just 06:00 (that's what caught this). Don't call the plateau until Mechanism 1's contribution visibly tapers (watch the 10,999-candidate pool drain) **and** a few more days pass with no new Mechanism-2 clusters.  
**DEPENDENCIES:** Gates Stage 0a of the ELO-migration critical path (O-7). Independent of O-19/O-21 otherwise.  
**RISK/EFFORT:** Investigation done; both fixes are small (one-line + a refactor of the persist-loop's exception granularity) but not yet applied.  
**FROZEN-AREA?** No — pnl_worker/backfill_worker are not part of the frozen `comprehensive_elo` chain, but the metric they produce feeds Stage 0a's gate decision.

---

### O-21 · Requeue event-time gate — FIXED 2026-07-07 (commit `f5fae64`, first-repo)
**ITEM:** This is the Fable audit's finding 7.1, independently re-verified (and its severity corrected — see O-20's SOURCE note) before fixing, same day. `requeue_resolved_market_traders.py` gated newly-resolved-market detection on `resolution_date` (event-time). The O-16 backfills (193,520 markets, Tier-1 + Tier-2) wrote **historical** resolution dates (2020–2026, median well in the past) — structurally, at most 1 of those 193,520 markets could ever have passed an event-time gate on any day since insertion, confirmed by direct query. `legendary_positions_scan.py`'s two resolution-writers had the identical class of gap on a different axis: they never stamped `last_checked` at all (only `resolution_date`), which would have broken a naive switch to a `last_checked` gate for markets resolved via that (weekly) path.  
**STATUS:** **RESOLVED 2026-07-07.** Both fixed together: (1) `legendary_positions_scan.py` now co-stamps `last_checked` at both write sites, matching the convention already used in `resolve_legendary_markets.py`; (2) `requeue_resolved_market_traders.py`'s gate switched from `resolution_date` to `last_checked` (write-time). Verified: full suite 73/73 green, plus a standalone script (not added to the permanent suite) proving both fixes against synthetic data shaped exactly like the real bug, including a negative control confirming the *old* gate provably would have missed the same backfill-shaped market. Ran `requeue_resolved_market_traders.py --force` once (idempotent, one-time catch-up): **8,971 traders** requeued; background P&L worker confirmed picking them up immediately post-run.  
**SIDE EFFECT:** Surfaced O-19 (the pre-write backup this fix required turned out to be corrupted).  
**SEVERITY CORRECTION FOR THE RECORD:** Fable's original framing treated this as the primary blocker for the O-15/Stage-0a plateau signal. Independent verification found the ordinary 24-hour staleness rotation in `background_pnl_worker.py` sweeps *all* traders regardless of this gate (it's a prioritization-delay bug, not a structural block) — position counts on affected markets were already draining fast before the fix landed. The real Stage-0a blocker is O-20's two mechanisms, only ~12% attributable to this bug. Don't re-cite this fix alone as sufficient grounds to declare the plateau reached.  
**DEPENDENCIES:** None remaining. Closed.  
**RISK/EFFORT:** None remaining.  
**FROZEN-AREA?** No.

---

### O-22 · `backfill_market_categories.py` limit-comparison bug — daily no-op — RESOLVED 2026-07-09 (commit `96b7900`, first-repo)
**ITEM:** Line ~245 compares the script's **lifetime** cumulative state-file total (`total_classified + total_skipped`, currently 17,584) against the **per-run** `--limit 50` passed by `daily_maintenance.py`'s Step 15. Since the lifetime total passed 50 long ago, the comparison is true on the very first check of every run — the step exits immediately, every day, `exit 0`, logged as "OK (0.0s)". It has been structurally incapable of doing work for an unknown but likely long stretch.  
**SOURCE:** Fable silent-failure audit, 2026-07-07, finding 7.7 (`2026-07-07-silent-failure-audit-FABLE.md`).  
**STATUS:** **RESOLVED 2026-07-09.** Comparison switched from the lifetime state-file total to a per-run counter. **Confirmed the no-op empirically before fixing:** `logs/category_backfill.log` shows 4 consecutive automated daily runs (2026-07-06 through 2026-07-09) each logging "Resuming from offset=17584" immediately followed by "Reached --limit 50, stopping" — zero markets processed, zero offset movement, across 4 days. A manual dry-run after the fix landed (2026-07-09, same session) shows real batches processing from that same offset. **This item is separate from O-2** (see O-2's reframe above) — clarified during this same fix: the ~133K/138K figure tracked under O-2 was never this script's classification backlog.  
**ACTUAL BACKLOG CHARACTERIZED (smaller than assumed):** `backfill_market_categories.py` only targets a keyword-filtered subset of `markets.category='Unknown'` (geopolitics/election-sounding titles) — **21,982 in scope**, of which 17,584 already processed lifetime (11,001 classified, 6,583 correctly confirmed Unknown). **Remaining: 4,398** — not 133K, not the 594K raw `Unknown` count. At the fixed `--limit 50`/run/day, drains in **~88 days (~3 months)**. The `--limit` is a local Ollama call (`qwen3-coder:30b` on localhost, not an external rate limit) — the 50/day figure is a conservative default, not a hard ceiling; could be raised if faster drain is wanted, well within the step's 3h default subprocess budget. The other ~572K genuinely-`Unknown` markets (sports/crypto/entertainment, correctly `Unknown` per the classification prompt's own definition) are cosmetic — nothing downstream needs them reclassified.  
**DEPENDENCIES:** None remaining for this item. Soft-feeds O-2's fix ordering (classify markets before running O-2's `--full-sync`, since sync can't propagate a category a market doesn't have yet).  
**RISK/EFFORT:** None remaining.  
**FROZEN-AREA?** No.

---

### O-23 · Manual research exclusions silently reverted by the daily state machine (Fable 2.5)
**ITEM:** `update_research_exclusions.py`'s `CLEAR_SQL` re-includes any `research_excluded=1` trader with `resolved_trades_count >= 20` and no `bot_suspect`/`wash_trade_suspect`/`bot_type` flag set — i.e., **any manual exclusion lacking a durable flag gets silently reverted within 24 hours** of the next daily run.  
**SOURCE:** Fable silent-failure audit, finding 2.5, verified live 2026-07-07: trader `0x44a1159b` — manually excluded 2026-06-10, still documented as excluded in `brain/integration-contract.md` §6c — is confirmed back at `research_excluded=0`, `bot_type=NULL`, `resolved_trades_count=148` as of today. **Back in the research pool for ~4 weeks** with nobody aware. (`0xf0d3c90f`, excluded the same week, survived only because it received a durable `bot_type=LP_ARTIFACT` tag.) Same investigation surfaced that `wash_trade_audit.py` (the sole writer of `wash_trade_suspect`) is archived — wash-trade detection has been permanently frozen at 57 stale flags, recorded only in a code comment, nowhere in any doc an agent or future session would read.  
**STATUS:** OPEN. Not fixed.  
**FIX (designed, not applied):** give `update_research_exclusions.py` a durable manual-override mechanism the state machine never touches — e.g. a dedicated `bot_type='MANUAL_EXCLUDE'` value, or a separate `manual_override` column excluded from `CLEAR_SQL`'s WHERE clause. Re-exclude `0x44a1159b` durably once the mechanism exists. Update `integration-contract.md` §6c to match reality. Separately: decide whether to restore `wash_trade_audit.py` or formally retire the wash-detection axis (needs Oscar's judgment either way — see Fable audit's "needs judgment" list).  
**DEPENDENCIES:** None. No frozen-area contact.  
**RISK/EFFORT:** Small. **FIX-NOW candidate.**  
**FROZEN-AREA?** No — but touches `research_excluded`, an input to every research/signal query pool definition; get it right.

---

### O-24 · Ollama agent write-allowlist is prefix-matched, not fully anchored (Fable 6.1)
**ITEM:** `trading-swarm/orchestrator/ollama_agent_loop.py`'s SQL write-allowlist (lines ~54-71, checked at line ~293) matches queries by regex prefix, e.g. `^\s*UPDATE\s+traders\s+SET\s+geo_elo\b`. This matches `UPDATE traders SET geo_elo=1500, comprehensive_elo=9999 WHERE ...` — a local LLM agent has a live, allowlist-sanctioned write path into **`comprehensive_elo`, the frozen ELO column**, via a smuggled second assignment, bounded only by the 50,000-row write cap. The allowlist also permits bare `ALTER TABLE traders ADD COLUMN` (schema drift by agent, and DDL explicitly skips the row-count guard) and references `accuracy_pool` (a column dropped 2026-06-05) and `trader_notes` (a table that has never existed in the schema) — stale entries in both directions.  
**SOURCE:** Fable silent-failure audit, finding 6.1.  
**STATUS:** OPEN. Not fixed.  
**FIX (stopgap, designed but not applied):** tighten each allowlist regex to reject additional comma-separated assignments (match up to the `=` value, then require the statement end there before `WHERE`, rejecting any bare `,` outside a quoted string); delete the `accuracy_pool`, `trader_notes`, and `ALTER TABLE` entries. **Proper fix (larger, not scoped for FIX-NOW):** replace raw-SQL agent writes with named, parameterized operations that route through the same canonical write helpers first-repo uses internally — regex-allowlisting arbitrary SQL text against an LLM's output is structurally unwinnable as a long-term posture.  
**DEPENDENCIES:** Directly relevant to ELO-arc safety (O-7) — a write path into `comprehensive_elo` that bypasses the frozen-area discipline should be closed before Stage 1 (shadow computation) makes that column's integrity load-bearing for migration diffs.  
**RISK/EFFORT:** Stopgap is small (regex tightening + dead-entry removal). **FIX-NOW candidate** for the stopgap; the named-operations rebuild is separate, larger, structural work (see O-29).  
**FROZEN-AREA?** Adjacent — doesn't touch `comprehensive_elo` today, but is a live path that could.

---

### O-25 · `hydrate_stub_markets.py` has no rotation — same 200 markets grinding daily (Fable 7.6)
**ITEM:** The query (`WHERE m.resolution_date IS NULL ... LIMIT 200`, no ordering, no attempted-marker) fetches the same 200 unfindable markets every single day. Confirmed in the retained daily-maintenance log: **≥7 consecutive `[HYDRATE] Done — updated=0, not_found=200` runs.** The thousands of stub markets behind those first 200 in insertion order are never reached. This is the exact pattern the O-13 round-robin fix (commit `6c08afc`, first-repo) already solved for the resolution-scan class of problem — just not applied here.  
**SOURCE:** Fable silent-failure audit, finding 7.6.  
**STATUS:** OPEN. Not fixed.  
**FIX (not yet designed in detail; pattern exists):** apply the same rotation/attempt-marker approach as `6c08afc` — e.g. order by `last_checked ASC NULLS FIRST` and stamp an attempt timestamp on every pass (success or not-found), so the query naturally advances through the backlog instead of re-fetching the same head every day.  
**DEPENDENCIES:** None. No frozen-area contact.  
**RISK/EFFORT:** Small-medium — needs the rotation column/logic, not just a query tweak.  
**FROZEN-AREA?** No.

---

### O-26 · Daily maintenance's "all steps succeeded" banner is unconditional (Fable 4.1)
**ITEM:** `daily_maintenance.py`'s completion banner (`=== MAINTENANCE COMPLETE === ... all steps succeeded ===`) is a hardcoded string, printed regardless of any non-blocking step's failure, the test suite's outcome, or the final two post-steps' return values (which are discarded, not checked). Anyone — human or an AI orientation session — grepping the log for health is told "succeeded" even when it didn't.  
**SOURCE:** Fable silent-failure audit, finding 4.1. Directly an instance of the audit's synthesis theme (presence-tested, not liveness/correctness-tested).  
**STATUS:** OPEN. Not fixed. **We have been trusting this banner all month** as a first-pass health signal in orientation sessions.  
**FIX (small, not yet applied):** derive the banner from an actual outcomes list — print `N steps, M failed: [names]` and exit nonzero if any blocking-tier concern occurred, including non-blocking-step failures and test-suite failure.  
**DEPENDENCIES:** None. No frozen-area contact.  
**RISK/EFFORT:** Small. Natural to bundle with O-27 (same file, same session).  
**FROZEN-AREA?** No.

---

### O-27 · `daily_maintenance.py`'s `run_step()` has no subprocess timeout (Fable 3.1) — RESOLVED 2026-07-09 (commit `764839b`, first-repo)
**ITEM:** `run_step()` (the function every one of the 29+ daily-maintenance steps runs through) calls `subprocess.run()` with no `timeout=`. Any single step — a hung RPC call, a network stall, a slow query — can block the entire maintenance run indefinitely with no ceiling.  
**SOURCE:** Fable silent-failure audit, finding 3.1, cross-referenced against known hang incidents.  
**STATUS:** **RESOLVED 2026-07-09.** `run_step()` now takes an optional `timeout=` param passed to `subprocess.run()`; `subprocess.TimeoutExpired` (child already killed by `subprocess.run()` itself) logs a WARNING with step name + budget and returns `False`, routed through the existing non_blocking/blocking handling exactly like a non-zero exit code — verified directly against a mocked `TimeoutExpired` for both the non-blocking-continue and blocking-abort paths, no pipeline freeze in either.  
**EVIDENCE CORRECTION FOR THE RECORD:** this entry's original framing ("~80-minute maintenance hangs," "step 12 normally runs ~15-50min") was stale. 35 days of actual step-duration history (`logs/daily_maintenance.log`) showed `Backfill transaction hashes` (step 12) routinely running **2-3h** now (6883-10714s over the last 10 runs), not 15-50min, with a historical worst case of 6.39h (22996.8s) during a 2026-06-09/06-12 RPC incident. `Label maker/taker roles` (step 13) was in fact rock-stable, never exceeding 4min (239.6s) in 35 runs.  
**THIRD OFFENDER FOUND:** `Discover leaderboard traders` (Sunday-only weekly step) wasn't named in the original finding but the duration history proved it belongs on this list — all 3 successful runs took 5.45-7.19h, and its very first run (2026-05-31) was **manually SIGKILLed (exit -9) after 4.43h**: someone already hit this exact hang, by hand, before there was a budget to catch it.  
**BUDGETS APPLIED (evidence-based, each cleared with headroom above its own historical worst-case-that-still-succeeded):** Backfill transaction hashes → 8h; Discover leaderboard traders → 10h; Label maker/taker roles → 30min. `DEFAULT_STEP_TIMEOUT = 3h` applied to the remaining 27 steps via `run_step()`'s default parameter — sized above the highest historical max among any unbudgeted step (`Verify market titles`, 2.0h once, same RPC incident window).  
**VERIFIED:** AST-parses clean; full test suite 73/73 passed, no regression.  
**DEPENDENCIES:** None remaining. Closed.  
**RISK/EFFORT:** None remaining.  
**FROZEN-AREA?** No.

---

### O-28 · Harness coverage gaps — 6 missing invariants + 2 broken existing checks (Fable 5.5, 5.1, 5.2)
**ITEM:** Three distinct problems with `audit_invariants.py`, all found 2026-07-07:  
1. **(5.5) Zero coverage for every recent burn class.** No standing invariant exists for: (a) `resolved=1 AND resolution_date IS NULL` (the O-17/O-18 class); (b) `resolved=0 AND end_date < -7d AND resolution_date IS NULL` (the O-16 class — would catch regrowth, including via any future writer bug like the one O-21 just fixed); (c) `pnl_skip=1` count (the O-15 class — floor-0 check would have alerted around 50 instead of 1,421); (d) open positions on resolved markets (the O-7.1/O-21 class — 8,971 was the real number today, no check would have caught it building up); (e) writer-liveness / max-write-age per governed column (the `behavioral_modifier` 7-month-silent-writer class); (f) maintenance-run freshness (a sentinel older than ~26h with no corresponding Telegram alert — would catch step-1 crashes and full hangs uniformly, superseding the need to guess at every individual failure mode).  
2. **(5.1) The timestamp-format check tests the wrong thing on 3 axes.** It defines "canonical" per-column as *whichever format is currently the majority* rather than against `integration-contract.md` §16's actual space-separated standard — for `elo_last_updated` and `positions.entry/exit_timestamp` this is backwards (T-sep is "protected" as canonical, the opposite of the documented standard). It's also a binary `%T%` test blind to microsecond/timezone variants. And its headline status is computed from the **summed total** across columns, so one column's improvement can mask another's regression — confirmed live 2026-07-07: `elo_last_updated` was individually over its own per-column floor (a REGRESSION, visible only in the detail payload) while the headline read PASS because the O-16 fix's improvement to `resolution_date`/`end_date` more than offset it in the sum.  
3. **(5.2) Floors never ratchet down.** Several Tier-3 floors are set far above current reality — e.g. `FLOOR_API_NO_LOCAL=114,047` vs an actual count around 11,000-13,000 as of today (O-20) — leaving an 8-10× silent-regression margin before the check would ever fire.  
**SOURCE:** Fable silent-failure audit, findings 5.1, 5.2, 5.5 — the audit's own top-priority "add harness coverage" tier.  
**STATUS:** OPEN. Not fixed — design work, not yet implemented.  
**FIX (scoped, not applied):** (1) the six invariants above, each a small COUNT-based check, retro-covering O-15/16/17/18/O-7.1 as a class; (2) rebuild the timestamp check against `column_definitions.py`'s canonical definitions (space-sep, matching contract §16) with per-column gating so no column's regression can hide inside a sum; (3) move floors from hardcoded constants to a git-tracked JSON that auto-ratchets downward after N consecutive clean days, so every improvement permanently tightens the net instead of just resetting the baseline once.  
**DEPENDENCIES:** None structurally, but this is explicitly the audit's highest-leverage prevention work — most future silent-failure classes this system will produce look like the ones already on this ledger, and these checks would catch the *next* instance of each automatically instead of requiring another manual audit.  
**RISK/EFFORT:** Medium — six small checks plus one check rebuild plus one infra change (floor storage). No frozen-area contact (does not touch `comprehensive_elo` coverage, which rides the separate ELO-arc design's own 9 invariants).  
**FROZEN-AREA?** No.

---

### O-29 · Convention-enforcement layer — shared write helpers + drift-guard rules (structural)
**ITEM:** The multi-writer-drift class (O-6's `comprehensive_elo` history, O-17's resolution co-write gap, and now O-21's near-identical gap on `legendary_positions_scan.py`) keeps recurring because conventions live in comments and doc sections, not in code that mechanically enforces them. Two specific deferred pieces of structural work:  
1. **`Database.mark_market_resolved()` shared helper** — O-17 scoped this (a single function all 8 `resolved=1` writers route through) but deferred the extraction. O-21 just patched `legendary_positions_scan.py` ad hoc (two inline `UPDATE` statements edited directly) rather than routing it through a shared helper — the fix is correct today but a 9th writer, or a 10th, can still reproduce the same gap tomorrow. Extracting the helper now would make this whole class structurally impossible to recur, not just fixed for the writers that happen to have been audited so far.  
2. **Shared `connect()` + `db_now()` helpers, plus drift-guard rules** — a `connect()` wrapper baking in WAL + `busy_timeout` (many scripts still `sqlite3.connect()` without either, discovered during the O-7.1 verification work when a manual query hit `database is locked` on first attempt); a `db_now()` helper enforcing the canonical timestamp format at every write site (`resolve_legendary_markets.py`/`database.py` currently bind raw `datetime.now()` — space-sep-with-microseconds, non-canonical per contract §16 — while others use `strftime` correctly). Backed by new rules in the existing `check_canonical_definitions.py` drift-guard (already runs daily, already scans 252 files) banning raw `sqlite3.connect()` without `busy_timeout` and raw `datetime.now()`/`.isoformat()` as SQL bind-params in `scripts/`.  
**SOURCE:** O-17 (original helper deferral), Fable silent-failure audit Class 2 (multi-writer convention drift, full writer census), and today's O-21 fix (which needed exactly this and didn't have it).  
**STATUS:** OPEN. Scoped, not implemented.  
**DEPENDENCIES:** None blocking. Worth sequencing before the *next* multi-writer column gets touched (candidates already visible: O-25's hydrate rotation, any future resolution-writer).  
**RISK/EFFORT:** Medium — mostly mechanical extraction of existing logic into shared functions, plus drift-guard rule additions (small, the infrastructure already exists and runs daily).  
**FROZEN-AREA?** No — but this is the exact discipline the frozen `comprehensive_elo` area's own single-writer requirement (O-7) depends on generalizing correctly to the rest of the schema.

---

## RESOLVED ITEMS (struck — evidence cited)

~~**Behavioral integration tests 2, 5, 6 (test_behavioral_integration.py)**~~  
**RESOLVED in session #42** (commit `bd82fd7` fixed the write-back gap; commits `436f6a7`, `c736558` fixed the tests). All 8 tests green on real data. No xfail markers; no lowered bars. Confirmed by running the suite.

~~**1,113-trader `weighted_win_rate`/`resolved_trades_count=0` consistency rows**~~  
**RESOLVED (no-action)** in session #42. Confirmed one-time stale artifact on `research_excluded` traders; no active competing writer; no downstream harm. Explicitly closed.

~~**STR-002 scoring loop (Gate 3 blocker)**~~  
**RESOLVED** — `scripts/score_str002_signals.py` exists and has been running since 2026-06-15. Evidence: `brain/agent-outputs/str002-scoring/` contains outputs from 2026-06-15 through 2026-06-29. This was the strategic roadmap's "single highest-leverage unbuilt item" as of June 11; it was built between sessions #37 and #38.

~~**Wire `check_canonical_definitions.py` into daily maintenance**~~  
**RESOLVED** — confirmed in `scripts/daily_maintenance.py` line 38: `("Canonical definitions drift", SCRIPTS_DIR / "check_canonical_definitions.py", ["--alert"], True)`. The drift guard runs as a standing maintenance step.

~~**Simulation framework safety (production DB guard)**~~  
**RESOLVED in session #41** (commit `a5f9bb7`). All 12 simulation scripts default to `simulation_test.db`; 3 writer scripts hard-refuse production without `--allow-production-write`. Cluster D contamination vector closed.

~~**Behavioral snapshot column staleness (kelly/patience/timing ~1% populated)**~~  
**RESOLVED in session #42** (commit `bd82fd7`). Sunday recalc now writes back all three snapshot columns from the behavioral cache — same UPDATE that already computes them, zero new computation. Coverage: ~1% → ~99%. False 'Low behavioral coverage' Telegram alarm eliminated.

~~**Cluster B: 7 zero-trade traders in clean research pool**~~  
**RESOLVED** — handled automatically by `update_research_exclusions.py` which runs as Step 0 of daily maintenance. Harness 2026-06-29 shows 0 CRITICAL for this check.

~~**`integrate_behavioral_elo.py` as Layer 2 prerequisite question**~~  
**RESOLVED (confirmed NOT a prerequisite)** — session #42 investigation found the Sunday full recalc re-derives `behavioral_modifier` entirely from raw trades via `TradingBehaviorAnalyzer` every cycle. The snapshot columns (`kelly_alignment_score` etc.) are NOT inputs to the ELO chain. Running `integrate_behavioral_elo.py` is unnecessary compute, not a prerequisite.

~~**Tier-2 read-side consumer repointing (14 scripts, geo_elo → geo_elo_active)**~~  
**RESOLVED in session #40** (commits 4c7832e, 3919946, d5b7003, 73174e0, 8755f5b). All 14 scripts repointed. Drift guard verified clean (0 violations across 243 Python files).

~~**STR003-008 phantom LEGENDARY annotation**~~  
**RESOLVED in session #40** — annotated in `signals.json` with `corrected_legendary_count=1`, `phantom_legendary=[0xe0f1e775]`. Signal direction/status unchanged; basis honest for June 30 resolution.

---

## NO-LONGER-RELEVANT ITEMS

~~**`update_research_exclusions.py` old pool gate (competing-writer disease)**~~  
**NO-LONGER-RELEVANT** — fixed in session #39 (commit `d7e1bfb`). Gate synced to canonical. The morning CRITICALs this caused are resolved.

~~**`sync_trade_categories.py` argparse `--incremental` crash**~~  
**NO-LONGER-RELEVANT** — fixed in session #39 (commit `8d90447`). Script runs cleanly.

~~**~96K unflagged pending-on-resolved general population backlog**~~  
**STATUS CHANGED** — this was a "secondary" item from session #38. The harness now tracks `pending on resolved non-gap markets (flagged traders) = 275 (REGRESSION, floor 0)` and `pending on resolved non-gap geo/elections = 5,273 (REGRESSION, floor 0)`. The large general-population backlog figure from session #38 referred to a different scope (non-flagged traders). The harness Tier-2 floor at 0 means any new pendings are flagged. Not a deferred action item but a standing harness watch.

---

## OPEN HARNESS REGRESSIONS (not in deferred list, but visible today)

These appeared in the 2026-06-29 audit output and were not explicit deferred items from #38–42. Noting for completeness:

| Check | Count | Floor | Status |
|-------|-------|-------|--------|
| `pending on resolved non-gap markets (flagged traders)` | 275 | 0 | REGRESSION |
| `pending on resolved non-gap geo/elections markets` | 5,273 | 0 | REGRESSION |
| `BUY trades with no position record` | 363,285 | 275,254 | REGRESSION (growing) |
| `total_invested vs SUM(entry_total_cost) mismatch >5%` | 104 | 0 | REGRESSION |

The `BUY trades with no position record` regression (363K vs 275K floor) is notably large and growing. May warrant investigation alongside competing-writer teardown work.

---

## CRITICAL PATH ANALYSIS

**SUPERSEDED 2026-07-06 — see O-7's entry above for the current plan of record.** The chain below (O-5 → O-6 → O-7) was this ledger's original sequencing guess from session #38–42, written before the O-7 design existed. It is kept for history but is **no longer accurate**: O-6 is investigated-complete (was already true), and O-7 now has a full staged design (`2026-07-06-elo-arc-design-FABLE.md`) that verified against live code exactly what feeds the canonical formula — most of O-5 turned out not to gate it at all. **Corrected critical path, as of 2026-07-06:**

```
[REVIEW]  Oscar reviews 2026-07-06-elo-arc-design-FABLE.md (corrected, commit 6495006)
                         |
[STAGE 0c]  Delete dead Writer C (integrate_behavioral_elo.py) — dead code, no output change
[STAGE 0b]  Behavioral validation study (read-only) — picks W_beh before launch
[STAGE 0a]  Wait for O-15 backlog drain to plateau — gates Stage 1 (shadow computation)
                         |
[STAGE 1]  Shadow computation, delta report — human reviews
[STAGE 2]  Writer B onto canonical plumbing (output-neutral, verified byte-identical)
[STAGE 3]  Writer A onto canonical plumbing + soft cap/floor activate — writer disease dead here
[STAGE 4]  Enable behavioral (one constant) — the actual RQ-CONTESTED-001 fix ships
[STAGE 5]  Cleanup, O-3 backfill, unfreeze recalculate_comprehensive_elo.py
```

**What turned out to be independent of the ELO arc (does NOT gate O-7, contrary to the original guess):** `trader_statistics.successful_trades`, `monitor.py`'s `traders.open/closed_positions` writers, `analysis_scheduler.specialisation_ratio` — none read by any ELO formula path (verified in the design doc §7). These remain worth doing on their own merits, just not as a Layer-2 precondition.

**What actually precedes Layer 2 (corrected):**
1. Writer C deletion (folds into Stage 0c) — the only non-canonical writer of `resolved_trades_count`, an actual ELO-formula input.
2. Backlog drain plateau (Stage 0a) — pnl_modifier's input data is moving right now, and as of 2026-07-07 this is **not just the O-15 self-heal** (see O-20): two additional live mechanisms are still growing/moving the "BUY trades with no position record" metric intraday. O-7.1 (O-21, fixed 2026-07-07) closed one small contributor (~12% of the gap); O-20's two mechanisms remain open. Do not baseline until O-20 is resolved or its growth demonstrably tapers — see O-20 for the specific metric to watch and why.

Below this line: the original (now-superseded) session #38–42 analysis, kept for history.

<details>
<summary>Original critical path analysis (2026-06-29, superseded — click to expand)</summary>

```
[NOW — O-0]  Pool C decline investigation (HOT, blocks July 1 RQ wave)
                         |
[SMALL — O-1]  Wire run_tests.py into maintenance (unblocked, ~10 lines)
                         |
[PARALLEL — O-2, O-3]  Category cache (O-2) and timestamp normalization (O-3)
                         |  (independent of ELO arc, can run any time)
[DECISION — O-10]  Composite scorer cadence decision (tiny; behavioral data now good)
                         |
[MEDIUM — O-5]  Competing-writer teardown (non-ELO): successful_trades, 
                open/closed_positions, specialisation_ratio
                         |  (clears the field before entering frozen area)
[MEDIUM — O-6]  Understand + resolve the daily-path (apply_full_elo_modifiers) 
                vs Sunday-path (elo_bridge) formula divergence (Path A vs B).
                         |  ← THIS IS THE GATE INTO O-7
[LARGE — O-7]  Layer 2 ELO chain reconciler: canonical formula, single writer,
                harness coverage, ELO unfreeze.
                         |
[UNFREEZE]  Run recalculate_comprehensive_elo.py on corrected data
```

**What is independent of the Layer 2 arc (can run any time without touching frozen area):**
- O-0 Pool C investigation (actually urgent)
- O-1 run_tests.py wiring
- O-2 Category cache teardown
- O-3 Timestamp normalization
- O-4 Dead-column drop and API rename (but needs pre-drop reader audit first)
- O-8 insert_position dedup fix
- O-9 trading-swarm data-layer audit
- O-10 Composite scorer scheduling decision
- O-11 Research-scout triage
- O-12 Resolution-collection ID-routing gap (permanent-loss class)
- O-13 Monitoring service blocking-call stall (event-loop starvation during resolution scans)
- O-14 Offsite backup mount fix (RESOLVED)

**What specifically precedes Layer 2:**
1. O-5 (non-ELO competing writers) — removes noise before the frozen-area build  
2. O-6 (ELO daily-path investigation) — the conceptual prerequisite; must understand what `apply_full_elo_modifiers` does and decide whether to freeze it, reroute it, or absorb it into the reconciler

**The natural next-session sequence:**
1. Investigate Pool C decline (O-0) — time-sensitive before July 1
2. Wire run_tests.py (O-1) — quick win, unblocked
3. One of: O-2 (category cache), O-3 (timestamps), or O-4 (dead-column pre-drop audit) — progress on the independent arc
4. O-5 (competing writer teardown, non-ELO) — clears the way
5. O-6 → O-7 (Layer 2) — the big goal

</details>

---

*Ledger last updated: 2026-07-09 — O-27 RESOLVED (first-repo `764839b`) — run_step() subprocess timeout applied, evidence-based budgets, third offender (Discover leaderboard traders) found and fixed alongside the two named steps; the original "~80-minute"/"15-50min" framing corrected against actual step-duration history. Earlier: 2026-07-07 — O-19 through O-29 added (backup corruption, Stage-0a dual growth mechanisms, O-7.1 requeue fix closed, and the Fable silent-failure audit's fix-now/harness/structural backlog folded in); O-9 closed (superseded by Fable audit Class 6). Earlier: 2026-07-01 (O-14 added and RESOLVED — offsite backup mount fix, ext4 label-truncation root cause). Earlier same day: O-13 added — monitoring service blocking-call stall, discovered during July 1 power-outage forensics. Earlier: 2026-06-30, O-12 added — resolution-collection ID-routing gap, permanent-loss class. Earlier: 2026-06-29, O-6 updated with INVESTIGATED-COMPLETE findings. All statuses verified against live code and DB.*
