# 2026-08-19 — write-path census

Read-only. No writer investigated in depth, no fix proposed, no duplicate
cluster assessed for agreement. This is a map, not an audit. Every claim
tagged **[V]** (verified — grep/read this session) or **[I]** (inferred).

**Method [V]:** wrote `scripts/scan_write_paths.py` (first-repo, committed
— see bottom) — walked both repos' `.py` files, regex-matched `INSERT [OR
x] INTO`, `UPDATE ... SET`, `DELETE FROM` against all 60 table names read
live from `data/polymarket_tracker.db`'s own schema, captured file:line +
a 300-char snippet per match (296 raw matches, reproduced exactly on
re-run).
Cross-checked invocation against `daily_maintenance.py`'s `STEPS` list,
`crontab -l`, the three `polymarket-*` systemd units, and — because a
script can be *invoked by import* rather than as a subprocess — whether
each candidate is imported by `monitor.py`/`system_observer.py`/`main.py`.
**Limitation, stated plainly:** regex-on-source-text misses dynamically
constructed table/column names (e.g. `f"UPDATE {table} SET ..."`) and
anything built via an ORM-style abstraction this codebase doesn't appear
to use. Treated as a best-effort, not exhaustive, first pass — the
absence of a hit is not proof of absence.

---

## Writers by table

Full detail for the 4 highest-traffic tables and the 11 secondary
operational tables. The ~45 one-shot research/characterization tables
(`metric_v2*`, `layer0*`, `price_convention_audit_*`, `elo_formula_audit_*`,
`geo_elo_derivation_audit*`, `dilution_guard_signals*`) are each written by
**exactly one** file (`scan_writers.py` confirmed: 1 file per table for
all of them) — grouped in their own section below rather than repeated 45
times, since they share one characterization: single generating script,
manual invocation only, no enforcement.

### `markets`

| Writer | Columns | Canonical? | Invocation | Enforcement |
|---|---|---|---|---|
| `monitoring/database.py:518` `INSERT` | market_id, title, category, end_date, resolved, winning_outcome, resolution_date, last_checked, condition_id | own inline (Database wrapper method) | live — called from `monitor.py`'s ingest loop (service: `polymarket-monitoring`) | convention-only |
| `monitoring/database.py:551` `UPDATE` (mark resolved) | resolved, winning_outcome, resolution_date, last_checked | own inline | live, same service | convention-only |
| `monitoring/monitor.py:219,274` `UPDATE` | end_date, resolution_date (`COALESCE`-guarded) | own inline | live, `polymarket-monitoring` | convention-only |
| `monitoring/background_backfill_worker.py:328` `INSERT OR IGNORE` | market_id, title, category='Unknown', resolved=0, data_source | own inline | live, `polymarket-monitoring` (per-new-trader worker) | convention-only |
| `scripts/fast_resolution_check.py` — **4 separate resolution-write sites** (lines 265, 385, 495, 592) | resolved, winning_outcome, resolution_date, last_checked | own inline, **inconsistent within itself** — line 265 sets `resolution_date = ?` directly; lines 385/495/592 use `COALESCE(resolution_date, ?)` | scheduled — `daily_maintenance.py` step 16, **and** separately via `weekly_resolution_sweep.sh` (Sun 03:30 cron) calling the same class's methods with different params | convention-only |
| `scripts/fetch_market_resolutions.py:162` `UPDATE` | resolved, winning_outcome, resolution_date (no COALESCE), last_checked | own inline | no live call site found (absent from `daily_maintenance.py`, crontab, service imports) | convention-only |
| `scripts/backfill_o16_tier1.py:224,234` / `backfill_o16_tier2.py:213,223` (2 sites each) | resolved, winning_outcome, resolution_date (`COALESCE`), data_source, last_checked | own inline | no live call site found | convention-only |
| `scripts/legendary_positions_scan.py:304,314` | resolved, winning_outcome, resolution_date (`COALESCE`), last_checked | own inline | **cron**, Mon 07:30, direct crontab entry (not via `daily_maintenance.py`) | convention-only |
| `scripts/resolve_legendary_markets.py:210,215` | resolved, winning_outcome, resolution_date (`COALESCE`), last_checked | own inline | scheduled — `daily_maintenance.py` step 20 | convention-only |
| `scripts/hydrate_stub_markets.py:200` | resolution_date (`COALESCE`), end_date (`COALESCE`), resolved (`CASE`) | own inline | scheduled — `daily_maintenance.py`, post-test-suite step | convention-only |
| `scripts/fix_expired_unresolved.py:93` | resolved=1, winning_outcome, resolution_date=`datetime('now')` (**no COALESCE**) | own inline | no live call site found | convention-only |
| `scripts/backfill_missing_markets.py:135` `INSERT OR IGNORE` | market_id, title, category, end_date, resolved, winning_outcome, condition_id, resolution_date, last_checked, data_source | own inline | no live call site found | convention-only |
| `scripts/refresh_markets.py:230,272` `DELETE FROM markets` (unconditional, whole table) then `INSERT` | full row | own inline | no live call site found | convention-only |
| `scripts/backfill_clob_token_ids.py:109` | clob_token_id_yes, clob_token_id_no | own inline | no live call site found | convention-only |
| `scripts/backfill_market_categories.py:200` | category | own inline | scheduled — `daily_maintenance.py` step 15 (daily `--limit 50`) **and** step 224 weekly `--full-sync` variant (Sunday) | convention-only |
| `scripts/backfill_market_dates.py:227` | end_date, resolution_date (`COALESCE`) | own inline | scheduled — `daily_maintenance.py`, post-test-suite step | convention-only |
| `scripts/backfill_market_ids.py:192` | market_id (rekey by condition_id) | own inline | no live call site found | convention-only |
| `scripts/clean_database.py:209` `DELETE` | row deletion, join-filtered | own inline | no live call site found | convention-only |
| `scripts/normalize_market_dates.py:66` | dynamic `{col}` (date normalization) | own inline, **column name interpolated via f-string** (not in the regex-safe set — confirms the method's blind spot) | no live call site found | convention-only |
| `scripts/quarantine_o37_synthetic_markets.py:157` | trade_gap_flag, flag_reason | own inline | no live call site found (one-off O-37 remediation, already run) | convention-only |
| `scripts/verify_market_titles.py:162` | title | own inline | scheduled — `daily_maintenance.py` step 14 | convention-only |
| `monitoring/column_definitions.py:360` | data_source (one-off historical backfill UPDATE, embedded as a string constant) | n/a — appears to be a one-time-run constant, not a regularly-executed statement | unclear, not itself invoked as a script | convention-only |

### `traders`

| Writer | Columns | Canonical? | Invocation | Enforcement |
|---|---|---|---|---|
| `monitoring/database.py:73` `write_elo_result` | comprehensive_elo, base_category_elo, behavioral_modifier, advanced_modifier, pnl_modifier, kelly_alignment_score, patience_score, timing_score, elo_last_updated | **canonical helper** | called by `apply_full_elo_modifiers.py` (daily_maintenance step 24) and `elo_bridge.py`'s `full_elo_recalculation` (Sunday timer) | convention-only for *whether* callers use it (see write-path-architecture-recon, `59a2aee`) |
| `monitoring/elo_bridge.py:242` `_batch_store_elo_results` (Writer D) | comprehensive_elo, base_category_elo, behavioral_modifier, advanced_modifier, pnl_modifier, elo_last_updated — **6 of the 9 canonical columns, raw SQL, not via write_elo_result** | own inline (non-canonical) | **no live call site** — see `2026-08-19-elo-write-architecture-recon.md`; already known | convention-only |
| `monitoring/database.py:286` `INSERT` | address, total_trades, successful_trades, win_rate, total_volume, is_flagged, last_updated | own inline | live, `polymarket-monitoring` (new trader discovery) | convention-only |
| `monitoring/background_pnl_worker.py:352` | realized_pnl, avg_roi, roi_percentage, (+ more per snippet) | own inline | live, `polymarket-monitoring` (imported into `monitor.py`) | convention-only |
| `monitoring/monitor.py:1175` | realized_pnl, total_pnl, avg_roi (+ more) | own inline | live, `polymarket-monitoring` | convention-only |
| `monitoring/trader_statistics.py:317` | realized_pnl, avg_roi, total_invested, closed_positions (+ more) | own inline | **[I]** not confirmed live-scheduled this session — flagged, not chased | convention-only |
| `scripts/backfill_synthetic_closes.py:145` | realized_pnl, avg_roi, roi_percentage (+ more) | own inline | no live call site found | convention-only |
| `scripts/reconcile_trader_aggregates.py:366` | total_trades, successful_trades, resolved_trades_count (+ more) | own inline | no live call site found | convention-only |
| **P&L aggregate cluster above — 5 independent writers of overlapping `realized_pnl`/`avg_roi`/related columns, no shared helper.** See Duplicate Logic §1. |
| `scripts/update_research_exclusions.py` — 6 separate `UPDATE` sites (bot_type, research_excluded, is_flagged across lines 54, 75, 122, 137, 153, 172, 182) | bot_type, research_excluded, is_flagged | **closest thing to a canonical state machine** for this cluster | scheduled — `daily_maintenance.py` step 1 | convention-only |
| `scripts/detect_arb_bots.py:141` | bot_type='ARB_BOT', research_excluded=1, bot_suspect=1 | own inline, **writes around the step-1 state machine directly** | scheduled — `daily_maintenance.py` step 3 | convention-only |
| `scripts/promote_high_pnl_traders.py:19` | is_flagged=1, research_excluded=0 | own inline, same pattern | scheduled — `daily_maintenance.py` step 4 | convention-only |
| `scripts/resolution_sweep.py:241` | is_flagged=1, research_excluded=0, last_updated | own inline, same pattern | scheduled — `daily_maintenance.py` step 5 | convention-only |
| `scripts/set_manual_research_exclusion.py` | research_excluded, manual_override, manual_exclusion_reason | own inline (the deliberate manual-override tool, O-23) | manual CLI only, by design | convention-only |
| **Flag-state cluster — 5 files writing `is_flagged`/`research_excluded`/`bot_type` outside a single owner.** See Duplicate Logic §3. |
| `scripts/update_geo_elo.py:290,326` | geo_elo, geo_directionality_score, geo_resolved_trades_count, geo_elo_active | own inline (own pure `_compute_geo_elo`, separate from `comprehensive_elo`'s formula) | scheduled — `daily_maintenance.py` step 9 | **partial** — `check_geo_elo_range`/`check_geo_pool_sanity` are tier-1 gating |
| `scripts/quarantine_o37_synthetic_markets.py:208,225` | geo_elo, geo_directionality_score, geo_resolved_trades_count, geo_elo_active (sets AND separately nulls the same set) | own inline | no live call site found (one-off, already run) | convention-only |
| `scripts/reconcile_geo_resolved_counts.py:76` | geo_resolved_trades_count via `cd.GEO_RESOLVED_TRADES_COUNT_SQL` | **canonical shared SQL fragment** (`monitoring/column_definitions.py`) | scheduled — `daily_maintenance.py` steps 6 and 22 (pre- and post-eval) | **tier-1 gating** — `check_geo_recon` compares stored vs. recomputed |
| `scripts/backfill_trade_results_geo.py:119` | geo_resolved_trades_count via the same `cd.GEO_RESOLVED_TRADES_COUNT_SQL` | canonical shared SQL fragment | manual CLI only (pre-registration pending, `9610f99`) | same tier-1 check applies once run |
| `scripts/resync_position_counts.py:23,36` | closed_positions, open_positions | own inline | scheduled — `daily_maintenance.py` step 25 | convention-only |
| `scripts/requeue_resolved_market_traders.py:139` | pnl_last_updated=NULL | own inline | scheduled — `daily_maintenance.py` step 23 | convention-only |
| `scripts/evaluate_new_trader_results.py:71` | resolved_trades_count (recomputed from `trades.trade_result`) | own inline (full recompute, not incremental) | scheduled — `daily_maintenance.py` step 21 | convention-only |
| `scripts/add_watched_trader.py`, `discover_leaderboard_traders.py`, `discover_market_participants.py`, `resolution_sweep.py:217` — 4 separate `INSERT INTO traders` sites, same core column set (address, total_trades, successful_trades, win_rate, total_volume, is_flagged, discovery_source) | own inline each | `discover_leaderboard_traders.py` scheduled Sunday-only (`daily_maintenance.py`); `add_watched_trader.py` manual CLI; `discover_market_participants.py` no live call site found; `resolution_sweep.py` scheduled daily (step 5) | convention-only |
| `analysis/analysis_scheduler.py:461` | specialist_category (subquery from `trader_categories`) | own inline | service-driven — imported by `monitoring/system_observer.py` (`polymarket-observer`) | convention-only |
| `monitoring/column_definitions.py:115-116,353` | geo_accuracy_pool (reset+populate), data_source (one-off) | mixed — the geo_accuracy_pool pair are named canonical-SQL constants (`POOL_C_*_SQL`), referenced elsewhere | **[I]** invocation of these specific constants not traced to a single call site this session | `check_geo_pool_sanity` (tier-1) covers `geo_accuracy_pool` |
| `trading-swarm/orchestrator/ollama_agent_loop.py` | geo_elo, geo_directionality_score, geo_resolved_trades_count, bot_type, research_excluded — **gated by an explicit write-allowlist + row cap** | n/a (this file is *itself* the enforcement layer for whatever calls through it) | **[I]** not traced to what triggers this agent loop — see "worth investigating" | **real enforcement, but scoped to agent-proposed SQL only** — see Enforcement note below |
| `trading-swarm/brain/agent-outputs/quant-research/GEO-ELO-003/geo_elo_oos_validation.py:105-107` | geo_elo_oos (a column not written anywhere else found) | own inline, `executemany` | no live call site found — looks like a one-off research artifact | convention-only |

### `trades`

| Writer | Columns | Canonical? | Invocation | Enforcement |
|---|---|---|---|---|
| `monitoring/database.py:343` `INSERT` | full row | own inline | live, `polymarket-monitoring` | convention-only |
| `monitoring/background_backfill_worker.py:306` `INSERT OR IGNORE` | trade_id, trader_address, market_id, market_title, market_category, outcome, outcome_bet, shares, price, side, timestamp, trade_result='pending' (hardcoded), data_source | own inline | live, `polymarket-monitoring` | convention-only |
| `monitoring/database.py:467` `update_notified`; `monitoring/system_observer.py:1165` (separate site, same column) | notified | own inline, **two independent writers of the same single column** | both live (`polymarket-monitoring`, `polymarket-observer`) | convention-only |
| `monitoring/database.py:661` `update_trade_result` | trade_result | **canonical wrapper method** | called by `evaluate_new_trader_results.py` (step 21) | convention-only |
| `scripts/backfill_trade_results_geo.py:104` | trade_result | own inline `UPDATE` (does **not** call `db.update_trade_result()` — evaluation now goes through canonical `TradeEvaluator`, but the write statement itself is a duplicate of the wrapper method, not a call to it) | manual CLI only | convention-only |
| `scripts/backfill_transaction_hashes.py:161` | transaction_hash | own inline | scheduled — `daily_maintenance.py` step 12 | convention-only |
| `scripts/polygon_event_scanner.py:423` | transaction_hash, is_taker | own inline | **[I]** invocation not confirmed this session | convention-only |
| `scripts/polygon_maker_taker.py:235` | is_taker | own inline | scheduled — `daily_maintenance.py` step 13 | convention-only |
| `scripts/backfill_market_categories.py:204`, `scripts/sync_trade_categories.py:110` | market_category | own inline, **two separate sync mechanisms for the same column** (daily incremental + weekly full-sync, per the O-2 backstop design noted in `daily_maintenance.py`'s own comments) | both scheduled (`daily_maintenance.py` steps 2 and 15, plus Sunday `--full-sync` variant) | `check_unknown_category` (tier-2) covers drift |
| `scripts/daily_maintenance.py:139` `DELETE` (dedup) | row-level dedup by `(trader_address, market_id, outcome, timestamp, shares, price)` | own inline | scheduled — `daily_maintenance.py`'s own post-test-suite step | convention-only |
| `scripts/clean_database.py:193`, `scripts/quick_fixes/clean_orphaned_records.py:55` | row deletion | own inline each | no live call site found (either) | convention-only |
| `monitoring/column_definitions.py:367` | data_source (one-off backfill UPDATE) | n/a | not itself invoked as a script | convention-only |

### `positions`

| Writer | Columns | Canonical? | Invocation | Enforcement |
|---|---|---|---|---|
| `monitoring/position_tracker.py:518` `INSERT` | full row (FIFO-matched entry) | own inline — **the primary/intended position-construction path** | live, `polymarket-monitoring` (imported by `monitor.py` and `background_pnl_worker.py`) | convention-only |
| `monitoring/database.py:390` `INSERT` | full row | own inline, **second independent INSERT-position path** | **[I]** caller not confirmed this session — flagged | convention-only |
| `monitoring/background_pnl_worker.py:284` `INSERT` | full row | own inline, **third independent INSERT-position path** | live, `polymarket-monitoring` | convention-only |
| `scripts/backfill_synthetic_closes.py:84` `INSERT` | full row | own inline, **fourth independent INSERT-position path** | no live call site found | convention-only |
| **Position-construction cluster — 4 independent `INSERT INTO positions` implementations.** See Duplicate Logic §2. |
| `monitoring/position_tracker.py:366` `apply_synthetic_closes` | status='closed', exit_avg_price (1.0/0.0 via direct `position.outcome == winning_outcome` compare), exit_shares, exit_timestamp, is_synthetic_close | own inline — **third independent win/loss determination** (named already in the trade-evaluator convergence doc, `e059b71`) | live, via `background_pnl_worker.py` | convention-only |
| `scripts/fix_expired_unresolved.py:58` | status='closed', exit_avg_price = `CASE WHEN outcome='{win}' THEN 1.0 ELSE 0.0 END`, exit_total_received | own inline — **a fourth, textually-interpolated reimplementation of the same win/loss compare**, string-formatted directly into the SQL rather than parameterized | no live call site found | convention-only |
| `scripts/fix_expired_unresolved.py:257` | pnl_last_updated=NULL, pnl_update_priority=1 (this one on `traders`, requeue side-effect) | own inline | no live call site found | convention-only |
| `scripts/clean_database.py:198`, `scripts/quick_fixes/clean_orphaned_records.py:79` | row deletion | own inline each | no live call site found (either) | convention-only |
| `monitoring/column_definitions.py:373` | data_source='synthetic_resolution' (one-off) | n/a | not itself invoked as a script | convention-only |
| `monitoring/elo_bridge.py` (3 sites, lines 39/119/786 in snippet) | positions refresh, calls into `position_tracker`/`background_pnl_worker` rather than writing directly | delegates | live (Sunday timer) + manual (`--quick-update` CLI) | convention-only |

### Secondary operational tables

| Table | Writers | Canonical? | Invocation | Enforcement |
|---|---|---|---|---|
| `monitoring_status` | `monitor.py:1052` (`INSERT OR REPLACE`, id/last_activity/process_id); `diagnose_activity_tracking.py:135` (last_activity) | own inline | monitor.py live; diagnose_* looks like a one-off diagnostic tool, no live call site found | convention-only |
| `insider_signals` | `detect_insider_activity.py:676` INSERT; `score_insider_signals.py:130` UPDATE (outcome_correct, resolved_at, information_value); `system_observer.py:3310,3364` UPDATE (alerted only) | own inline each | `detect_insider_activity.py` **service-driven** — imported by `system_observer.py:3234` (`polymarket-observer`), not a standalone schedule; `score_insider_signals.py` scheduled `daily_maintenance.py` step 10 | convention-only |
| `insider_clusters` | `detect_insider_activity.py:704` INSERT; `system_observer.py:3335,3382` UPDATE (alerted only) | own inline | same as above | convention-only |
| `str002_signals` | `register_str002_signals.py:184` INSERT OR IGNORE; `enrich_str002_metadata.py:112` UPDATE (has_proven_trader, regime, event_cluster); `score_str002_signals.py:95` UPDATE (outcome_correct, winning_outcome, edge_at_entry, resolved_at, scored_at) | own inline each | all three scheduled — `daily_maintenance.py` steps 17/18/19 | convention-only |
| `trader_categories` | `analysis/analysis_scheduler.py:452` INSERT OR REPLACE | own inline | service-driven, `polymarket-observer` | convention-only |
| `monitor_state` | `monitoring/database.py:264` INSERT ... ON CONFLICT DO UPDATE (key/value store) | canonical-shaped (single wrapper, upsert) | live, `polymarket-monitoring` | convention-only |
| `order_book_snapshots` | `scripts/snapshot_order_books.py:155` INSERT OR IGNORE | own inline | scheduled — `daily_maintenance.py` step 28 | convention-only (has dedicated regression test, `test_snapshot_order_books_none_mid.py`, but that's a unit test, not a DB-level invariant) |
| `elo_shadow` | `scripts/compute_elo_shadow.py:139` INSERT OR REPLACE | own inline (shadow-comparison tool, ELO arc Stage 1 artifact) | no live call site found | convention-only |
| `elo_snapshots` | `scripts/snapshot_elo_scores.py:129` INSERT OR IGNORE | own inline | scheduled — `daily_maintenance.py` step 27 | convention-only |
| `event_cluster_labels` | `scripts/build_event_cluster_labels.py:356` INSERT OR IGNORE | own inline | no live call site found | convention-only |
| `backtest_population_snapshots` | `scripts/snapshot_backtest_population.py:113` INSERT OR IGNORE | own inline | no live call site found | convention-only |

### Research/characterization tables (grouped)

**[V]** All of the following have **exactly one writer file each** (confirmed by the scan: 1 file per table), matching the table name to its generating script 1:1 — `metric_v2_*` ↔ `trader_skill_metric_v2.py`, `metric_v2b_*` ↔ `..._v2b.py`, and so on through `v2f`; `layer0*` ↔ `layer0_forward_accuracy.py`/`layer0b_deconfound.py`/`layer0c_*`; `price_convention_audit_*` ↔ `price_convention_audit.py`; `elo_formula_audit_*` ↔ `elo_formula_audit.py`; `geo_elo_derivation_audit*` ↔ `geo_elo_derivation_audit.py`; `dilution_guard_signals*` ↔ `verify_dilution_guard.py`. **Shared characterization for all of them:** own inline logic (each script is self-contained), **manual invocation only** (none appear in `daily_maintenance.py` or `crontab`), **convention-only enforcement** (none are covered by `audit_invariants.py`, which only checks `traders`/`markets`/`trades`/`positions`). This is expected and appropriate for one-shot research artifacts — noted for completeness, not flagged as a defect class.

---

## 1. Duplicate logic clusters

- **Win/loss determination — 4 independent implementations**, not 3: `monitoring/trade_evaluator.py` (canonical, `TradeEvaluator.evaluate_trade`); `scripts/backfill_trade_results_geo.py`'s former local copy (now repointed onto canonical, `8cfeb8e`); `monitoring/position_tracker.py`'s `apply_synthetic_closes` (compares `position.outcome`/`winning_outcome` directly, no `invalid` guard); and **newly found this session**, `scripts/fix_expired_unresolved.py:58`'s inline `CASE WHEN outcome='{win}' THEN 1.0 ELSE 0.0 END`, string-interpolated directly into SQL — a fourth, unnamed-until-now member of this cluster.
- **Market resolution write (`resolved`/`winning_outcome`/`resolution_date`/`last_checked`)** — at least **9 files**, no shared helper: `monitoring/database.py`, `fast_resolution_check.py` (4 internal sites, inconsistent `COALESCE` usage even within itself), `fetch_market_resolutions.py`, `backfill_o16_tier1.py`/`tier2.py` (2 sites each), `legendary_positions_scan.py`, `resolve_legendary_markets.py`, `hydrate_stub_markets.py`, `fix_expired_unresolved.py`, `backfill_missing_markets.py`.
- **Position construction (`INSERT INTO positions`)** — 4 independent implementations: `position_tracker.py` (primary), `monitoring/database.py`, `background_pnl_worker.py`, `backfill_synthetic_closes.py`.
- **Trader P&L aggregate recomputation (`realized_pnl`/`avg_roi`/related)** — 5 independent implementations: `background_pnl_worker.py`, `monitor.py`, `trader_statistics.py`, `backfill_synthetic_closes.py`, `reconcile_trader_aggregates.py`.
- **Trader flag-state (`is_flagged`/`research_excluded`/`bot_type`)** — one deliberate state machine (`update_research_exclusions.py`) plus 3 other files writing the same columns directly around it: `detect_arb_bots.py`, `promote_high_pnl_traders.py`, `resolution_sweep.py` (+ the deliberate manual-override tool, `set_manual_research_exclusion.py`, which is a different, documented case).
- **`traders` row creation (`INSERT INTO traders`)** — 4 sites with near-identical core column sets: `discover_leaderboard_traders.py`, `discover_market_participants.py`, `add_watched_trader.py`, `resolution_sweep.py`.
- **`geo_resolved_trades_count`** — partially converged: `reconcile_geo_resolved_counts.py` and `backfill_trade_results_geo.py` both use the shared `cd.GEO_RESOLVED_TRADES_COUNT_SQL` fragment; `update_geo_elo.py` and `quarantine_o37_synthetic_markets.py` write it as part of their own larger `UPDATE` without confirmed use of that fragment.
- **`market_category`/`trades.market_category` sync** — two mechanisms (`backfill_market_categories.py` daily-limited, `sync_trade_categories.py` daily-incremental + weekly-full), by explicit design (the O-2 backstop noted in `daily_maintenance.py`'s own comments) rather than accidental duplication — named for completeness since it's still two code paths toward one column.
- **`trades.notified`** — two independent writers, `monitoring/database.py` and `monitoring/system_observer.py`.

## 2. Orphan writers (no live call site found)

`monitoring/elo_bridge.py`'s Writer D (`_batch_store_elo_results`/`_process_trader_chunk`/`quick_elo_update_for_traders`) — already known. Newly catalogued this session, all confirmed absent from `daily_maintenance.py`, `crontab -l`, and import into `monitor.py`/`system_observer.py`/`main.py`:
`scripts/fetch_market_resolutions.py`, `scripts/backfill_o16_tier1.py`, `scripts/backfill_o16_tier2.py`, `scripts/fix_expired_unresolved.py`, `scripts/backfill_missing_markets.py`, `scripts/refresh_markets.py`, `scripts/backfill_clob_token_ids.py`, `scripts/backfill_market_ids.py`, `scripts/normalize_market_dates.py`, `scripts/quarantine_o37_synthetic_markets.py` (one-off, already run — expected to be dormant), `scripts/clean_database.py`, `scripts/quick_fixes/clean_orphaned_records.py`, `scripts/discover_market_participants.py`, `scripts/reconcile_trader_aggregates.py`, `scripts/backfill_synthetic_closes.py`, `scripts/compute_elo_shadow.py`, `scripts/build_event_cluster_labels.py`, `scripts/snapshot_backtest_population.py`, `scripts/diagnose_activity_tracking.py`, `trading-swarm/brain/agent-outputs/quant-research/GEO-ELO-003/geo_elo_oos_validation.py`.

## 3. Unscheduled remediation scripts

`backfill_trade_results.py` — already known (interactive `input()` prompt, no aggregate recompute). By the same shape (exists specifically to fix/backfill a known gap, not currently invoked by anything scheduled):
`backfill_o16_tier1.py`, `backfill_o16_tier2.py` (named O-16 remediation), `fix_expired_unresolved.py`, `backfill_missing_markets.py`, `backfill_clob_token_ids.py`, `backfill_market_ids.py`, `backfill_synthetic_closes.py`, `normalize_market_dates.py`, `reconcile_trader_aggregates.py`.

## 4. Partial-column writers

- **Writer D** (already known) — 6 of 9 canonical ELO columns, raw SQL, no live trigger.
- **`monitoring/elo_bridge.py`'s canonical path itself** writes the same 9-column group via `write_elo_result` — not partial, listed here only to contrast with Writer D directly above it in the same file.
- **`scripts/quarantine_o37_synthetic_markets.py`** writes `geo_elo`, `geo_directionality_score`, `geo_resolved_trades_count`, `geo_elo_active` together (matches `update_geo_elo.py`'s own column group) — not obviously partial, but it's a *second* place this exact 4-column group gets written, worth naming alongside the geo_resolved_trades_count entry in §1.
- **`scripts/backfill_trade_results_geo.py`** writes `trades.trade_result` via its own inline `UPDATE` rather than calling `monitoring/database.py`'s `update_trade_result()` wrapper — a single-column case, but it means the "canonical" wrapper for this column has a sibling that bypasses it even after this session's evaluator repoint.

## 5. Write-time vs. event-time

- `elo_last_updated` — `datetime.now()`/`str(datetime.now())` at write time, already characterized in the ELO write-architecture recon (T-separated legacy format, 22,558 rows, Stage-5 backfill never run).
- `markets.last_checked` — stamped `datetime.now()`/`datetime('now')` at write time across nearly every market-resolution writer in §"markets" above; used elsewhere in this arc as a *proxy* for "when was this market last touched," which is only event-time-adjacent by convention, not by guarantee.
- `traders.backfill_attempted` (`background_backfill_worker.py:256,411`) — write-time stamp recording when the backfill *attempt* happened, which is arguably correct here (it is an attempt-time column, not pretending to be something else) — named for completeness, not flagged as a defect.
- `traders.pnl_last_updated` — set to `datetime('now')` in `monitoring/database.py:1307` on write, and separately **cleared to `NULL`** by `requeue_resolved_market_traders.py` and `fix_expired_unresolved.py:257` as a "needs reprocessing" signal — so this single column is overloaded as both a timestamp and a boolean-ish work-queue flag, depending on which writer touched it last.
- `resolution_date` — the known, already-documented case (O-17 co-write fix, mutable, `COALESCE`-guarded in most but not all of the 9+ writers in the resolution cluster above — see §6).

## 6. Mutable columns with no audit trail

- `markets.resolution_date` — known example, restated with new evidence: of the 9+ writers found this session, **most** guard with `COALESCE(resolution_date, ?)` (preserve-if-set), but `monitoring/database.py:551`, `fetch_market_resolutions.py:162`, and `fast_resolution_check.py:265` (one of that file's own 4 sites) write it **unconditionally**, overwriting any existing value with no record of what it was before. No co-written provenance/timestamp column exists anywhere in this cluster.
- `markets.category` — known example (already the subject of the daily-incremental/weekly-full sync split); no audit column recording prior category or which sync path last touched it.
- `markets.winning_outcome` — same shape as `resolution_date`: writers overwrite directly, no provenance.
- `traders.bot_type` — set by at least 3 independent writers (`update_research_exclusions.py`, `detect_arb_bots.py`, and implicitly clearable per the state-machine's own `CLEAR_SQL`) with no record of which classifier set it or when.
- `traders.research_excluded`/`is_flagged` — mutated by 5 files (§1); `manual_override`/`manual_exclusion_reason` on `set_manual_research_exclusion.py`'s path is the **one** case in this whole census with an explicit provenance field for *why* a value was set — worth noting as the positive counter-example, not just negative findings.

---

## Worth investigating (ranked, one line each — not investigated further here)

1. **`trading-swarm/orchestrator/ollama_agent_loop.py`** contains a real write-allowlist + row-cap guard for agent-proposed `UPDATE traders` statements (geo_elo/geo_directionality_score/geo_resolved_trades_count/bot_type/research_excluded only) — what triggers this agent loop, and does it ever actually run, was not traced this session.
2. **Market resolution has 9+ independent writers with inconsistent `COALESCE` discipline, including within the single most-relied-on file (`fast_resolution_check.py`, 4 sites, 1 unconditional)** — the highest-count duplicate cluster found, on a column the entire time-series-integrity story (O-36, this arc) already depends on.
3. **Trader P&L aggregates have 5 independent recomputation implementations** with no shared helper and no invariant coverage at all.
4. **`scripts/fix_expired_unresolved.py:58`** is a previously-unnamed 4th implementation of win/loss determination, string-interpolating the winning outcome directly into SQL rather than parameterizing it.
5. **`geo_elo_oos_validation.py`** (trading-swarm, quant-research folder) writes a `traders.geo_elo_oos` column found nowhere else in this census — unclear if anything reads it, or whether it's a stale one-off.
6. **`monitoring/trader_statistics.py`'s P&L writer** and **`polygon_event_scanner.py`** — invocation not confirmed live or dormant this session; both assumed live-adjacent given their location in `monitoring/`, not verified.
7. **`monitoring/database.py`'s second `INSERT INTO positions` path** (line 390) — caller not identified this session; unclear whether it's dead code or a real third position-construction entry point beyond `position_tracker.py` and `background_pnl_worker.py`.
8. **`traders.pnl_last_updated` is overloaded** as both a write-time timestamp and a NULL-means-"needs reprocessing" work-queue signal, set by different writers for different purposes.

---

## Closing count

**[V]** Total distinct writer entries catalogued in the per-table tables
above (core + secondary tables; excludes the ~45 grouped research-table
writers, each already stated as 1-per-table): **approximately 95**
individual writer sites across `markets` (22), `traders` (26), `trades`
(12), `positions` (13), and the 11 secondary operational tables (~22
combined) — plus 1 writer each for the ~45 research/characterization
tables not itemized individually.

- **Canonical (goes through a named shared helper/formula):** 4 —
  `write_elo_result` callers (ELO columns), `TradeEvaluator` callers
  (trade_result), `cd.GEO_RESOLVED_TRADES_COUNT_SQL` callers
  (geo_resolved_trades_count, 2 of its ~4 writers), `monitor_state`'s
  single upsert wrapper. Everything else identified — the large majority —
  is own-inline logic.
- **Scheduled** (appears in `daily_maintenance.py`'s `STEPS`, a systemd
  timer, a direct crontab entry, or is service-driven via import into
  `monitor.py`/`system_observer.py`): roughly half of the core-table
  writers; the other half — concentrated in `markets` and `traders` — have
  **no live call site found** (§2) or are **manual-only remediation
  scripts** (§3).
- **With any enforcement at all** (a tier-1/tier-2 `audit_invariants.py`
  check, a dedicated unit test, or the one agent-write-allowlist found):
  a small minority. Confirmed tier-1/2 coverage exists for: `geo_elo`
  range/pool sanity, `geo_resolved_trades_count` reconciliation,
  `trades.market_category` drift, and the 5 `comprehensive_elo` OBSERVE
  checks (which, per the ELO recon, gate nothing regardless of count).
  **Every other cluster named in this census — market resolution, position
  construction, P&L aggregates, flag-state, win/loss determination outside
  `trade_result` itself — has no DB-level enforcement of any kind.**
  Convention-only is the answer for the large majority of writers
  catalogued here, stated explicitly per the task's instruction rather
  than left implied.

---

*Generated 2026-08-19. Method and raw match data:
`scripts/scan_write_paths.py` (first-repo, committed this session) →
`data/characterizations/write_path_census_20260819T183316Z.json`. Sources:
`sqlite3 .tables` against `data/polymarket_tracker.db`,
`scripts/daily_maintenance.py`, `crontab -l`, `systemctl cat
polymarket-*.timer/.service`, `scripts/audit_invariants.py`,
`2026-08-19-elo-write-architecture-recon.md` (`59a2aee`),
`2026-08-19-trade-evaluator-convergence.md` (`e059b71`),
`2026-08-19-trade-evaluator-repoint.md` (`3f7fd1b`). No code changed, no
writer investigated beyond what its own source states, no duplicate
cluster assessed for agreement.*
