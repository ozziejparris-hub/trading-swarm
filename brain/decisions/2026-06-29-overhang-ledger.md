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

---

### O-3 · Timestamp normalization — Teardown 3
**ITEM:** Normalise mixed timestamp formats across 4 tables: `traders.elo_last_updated` (23,440 rows with wrong format), `markets.end_date` (2,719 non-canonical), `markets.resolution_date` (2,534 non-canonical). `positions.*` and `trades.timestamp` are already clean.  
**SOURCE:** Sessions #38, #39 (Teardown 3, carried)  
**STATUS:** OPEN. **WORSENING** — harness shows 28,693 mixed vs floor 24,996 → **REGRESSION**. All growth is in `traders.elo_last_updated` (23,440 vs floor 23,163) and markets dates.  
**VERIFIED:** Harness 2026-06-29: `timestamp mixed formats = 28,693, floor 24,996, REGRESSION`. Per-column breakdown: `traders.elo_last_updated` non-canonical 23,440; `markets.end_date` non-canonical 2,719; `markets.resolution_date` non-canonical 2,534.  
**DEPENDENCIES:** Independent. New traders added daily drift the count upward (elo_last_updated written by `apply_full_elo_modifiers.py` with T-sep format, while canonical is space-sep — or vice-versa; verify before fixing). No ELO chain contact.  
**RISK/EFFORT:** Small-medium. One-time backfill SQL + writer fix to prevent re-accumulation.  
**FROZEN-AREA?** No — but `elo_last_updated` is written by `apply_full_elo_modifiers.py` (a frozen-area-adjacent script). Check the format the writer uses before patching the data.

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
**STATUS:** OPEN. Not done. `brain/agent-outputs/data-audit/` contains first-repo DB harness outputs only. No swarm-layer invariant scan has been built or run.  
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
**STATUS:** OPEN — root cause identified, not yet investigated further (frequency across other restarts, typical scan duration) or fixed. Confirmed via code read (`monitor.py:1261` calls the sync `def check_market_resolutions` with no executor/thread offload) and log cross-reference (file-logger gap 01:40:59→02:54:13 on July 1 lines up exactly with the scan's blocking window; journal shows the process alive and mid-scan throughout).
**DEPENDENCIES:** Independent of the ELO rebuild arc. No frozen-area contact — this is a monitoring-service concurrency issue, not an ELO-chain issue.
**RISK/EFFORT:** Medium. Real production impact: the watchdog meant to catch problems is itself unscheduled during the stall, so the monitor is effectively blind to its own health for the scan's full duration. Fix direction (not scoped today): offload the blocking scan to `run_in_executor`/a thread pool, or chunk the market list with periodic `await asyncio.sleep(0)` yields between batches. Needs its own design pass — not a same-session fix.
**FROZEN-AREA?** No.

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

**If Layer 2 is the goal, here is the dependency ordering:**

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

**What specifically precedes Layer 2:**
1. O-5 (non-ELO competing writers) — removes noise before the frozen-area build  
2. O-6 (ELO daily-path investigation) — the conceptual prerequisite; must understand what `apply_full_elo_modifiers` does and decide whether to freeze it, reroute it, or absorb it into the reconciler

**The natural next-session sequence:**
1. Investigate Pool C decline (O-0) — time-sensitive before July 1
2. Wire run_tests.py (O-1) — quick win, unblocked
3. One of: O-2 (category cache), O-3 (timestamps), or O-4 (dead-column pre-drop audit) — progress on the independent arc
4. O-5 (competing writer teardown, non-ELO) — clears the way
5. O-6 → O-7 (Layer 2) — the big goal

---

*Ledger last updated: 2026-07-01 (O-13 added — monitoring service blocking-call stall, discovered during July 1 power-outage forensics). Earlier: 2026-06-30, O-12 added — resolution-collection ID-routing gap, permanent-loss class. Earlier: 2026-06-29, O-6 updated with INVESTIGATED-COMPLETE findings. All statuses verified against live code and DB.*
