# Session Summary — Server Setup #41
**Dates:** 2026-06-24 → 2026-06-25
**Theme:** Simulation framework safety hardening + full data provenance system (contamination forensic map → provenance schema → migration → harness governance → all 14 write-path patches → 30-test regression suite + test runner). Three pre-existing data-integrity bugs found and fixed as a byproduct. ELO chain investigation mapped (Layer 2 starting point); three behavioral-integration test failures diagnosed and deferred.

---

## CONTEXT
Session #40 closed the canonical-definitions arc (Tier-1 + Tier-2 consumer repointing + drift guard). This session pivoted to the foundational data layer: Oscar's suspicion that the production DB may contain synthetic contamination triggered a forensic investigation, which in turn made the provenance gap (no `data_source` column on any table) the obvious next build. Everything else this session flowed from that: simulation safety first, then provenance schema, then harness, then write paths, then tests.

---

## ARC 1 — SIMULATION FRAMEWORK SAFETY (commit a5f9bb7, Jun 24)

**The problem**: The entire `scripts/simulation/` framework (12 scripts + pipeline runner) defaulted to the production DB (`data/polymarket_tracker.db`) when no `--db-path` argument was passed. Three scripts were writers:
- `seed_test_data.py` and `seed_production_data.py`: inject 500 synthetic traders, 200 markets, ~40,000 trades. `discovery_source = 'live_feed'` — **cryptographically indistinguishable from real insertions**.
- `calculate_elo_simple.py --write-to-db`: explicitly resets `behavioral_modifier`, `advanced_modifier`, and `pnl_modifier` to 1.0 for **all 87K traders** in the target DB. Highest-confidence contamination vector — would silently corrupt the modifier columns system-wide.

The 9 reader scripts were lower-risk but would still operate on production data silently.

**Fix — `scripts/simulation/_sim_db_guard.py`** (93 lines, three-layer defense):
1. `SIM_DB_DEFAULT = 'data/simulation_test.db'` — all 12 scripts now default here, not production.
2. `add_sim_db_args(parser)` / `resolve_sim_db(args)` — shared argument wiring so every script handles `--db-path` consistently.
3. `assert_safe_to_write(db_path)` — hard-refuses any write to the production path unless `--allow-production-write` is explicitly passed. Called by all 3 writer scripts before any DB mutation. Hard exit, not a warning.
4. `run_full_pipeline.py` — propagates `--db-path` through all 7 subprocess stage calls so the guard works end-to-end.

**Patched all 12 scripts + pipeline runner.** Before this commit, running any simulation script bare was a production write. After, the default path is safe and production requires an explicit override.

---

## CONTAMINATION FORENSIC MAP (pre-Arc-2 investigation)

**Written to `brain/decisions/2026-06-24-contamination-forensic-map.md`**. ~80 read-only SQLite queries across all tables, full git history review (~150 commits), and 6 key scripts read. Result filed before any code was changed.

**BOTTOM LINE: The production DB is overwhelmingly REAL.** Oscar's suspicion of large-scale synthetic contamination did not bear out — now evidence-backed, not assumed. Key findings:

- **Cluster A** (114,866 zero-trade traders, 79% of all): Probably real — standard monitoring pattern where discovery precedes trade-history fetch. research_excluded=1, no ELO harm.
- **Cluster D** (~1,346 traders with modifiers at 1.0 after being processed): **AMBIGUOUS, not confirmed contamination**. The fingerprint is WEAK — new traders also default to 1.0; cannot distinguish a calculate_elo_simple clobber from a genuine neutral. Folds into Layer 2 (the reconciler resolves it by construction).
- **Cluster F** (203,031 Dec-11-2025 markets): DEFINITELY REAL — historical Polymarket markets from 2020–2023 with correct condition_ids (2020 election, 2022 NBA, 2023 F1), title-verified.
- **Clusters J/M** (trades and positions): ZERO confirmed synthetic clusters found. Forensic query for simulation-isolated trader/market pairs from Jan 11–14 returned 0.
- **Cluster L** (1,224,209 synthetic closes): DEFINITIVELY LEGITIMATE — computed P&L for open positions in resolved markets. Correctly flagged, not contamination.

**Key insight**: The simulation's address/market_id generation uses `token_hex()` — cryptographically identical format to real ETH addresses and Polymarket condition_ids. Without a provenance column written at insertion time, retroactive identification is impossible. **The provenance gap is the real foundational deliverable — not the contamination result.**

The forensic map also pre-validated the provenance schema design (Section 5 of the map directly matched the implemented schema), making the subsequent build faster.

---

## ARC 2 — DATA PROVENANCE SYSTEM

### Step 1 — Column Definitions: Section 5 (commits 1efcd90, 1107a28)

Added Section 5 to `monitoring/column_definitions.py`: canonical `data_source` frozensets + `DEFAULT` constants + `ALTER SQL` + `backfill SQL` per table, all governed by the canonical module (no hardcoding in the migration or write paths).

**Per-table canonical value sets:**
- `traders`: `{live_feed, leaderboard, external_seed, manual_watchlist, orphan_repair, simulation, market_scan, resolution_sweep}` — `market_scan` and `resolution_sweep` added in 1107a28 after the write-path audit found two discovery scripts hard-coding them. The `1:1 with discovery_source` contract documented.
- `markets`: `{live_monitoring, historical_backfill, api_refresh, simulation, background_backfill, stub_placeholder}` — `background_backfill` added for gap-fill API inserts distinct from the Dec-2025 one-off.
- `trades`: `{polymarket_api, blockchain_scan, simulation, background_backfill, computed}` — `background_backfill` added for the backfill worker (which was silently mislabeling its corpus as `polymarket_api`).
- `positions`: `{position_tracker, synthetic_resolution, simulation, backfill_historical}` — clean first pass, no additions needed.

### Step 2 — Migration: `scripts/migrate_add_data_source.py` (commit 1efcd90)

Idempotent, dry-run-default. O(1) `ALTER TABLE ADD COLUMN NOT NULL DEFAULT` (SQLite 3.45.1 confirmed schema-only even on 8M-row trades table — no table rewrite). Then a tight evidence-based backfill sequence:

**Backfill strategy — zero guessed rows:**
- `traders` (145,219 rows): `discovery_source` 1:1 → `data_source` (all 5 values verified in canonical frozenset).
- `markets` (536,611 rows): `last_checked` in Dec-11-2025 seed window → `historical_backfill` (202,893 rows); all others → `live_monitoring`.
- `trades` (8,000,574 rows): all → `polymarket_api` (verified no-op against column DEFAULT — the backfill SQL was a safety confirmation).
- `positions` (4,968,328 rows): `is_synthetic_close=1` → `synthetic_resolution` (1,224,805 rows); rest → `position_tracker`.

**Post-migration verification**: every row non-NULL, every value in-set, bucket shapes match the forensic-map projection on all 4 tables. Live `monitor.py` (PID confirmed writing) rode through the 1.2M-row backfill with zero lock contention (WAL mode). Harness 0 CRITICAL; drift guard 0 violations.

### Step 3 — Harness Governance (commit 393a908)

Two Tier-2 invariants added to `scripts/audit_invariants.py`:
- `check_data_source_nulls`: any NULL across the 4 tables = write-path omission (floor: 0).
- `check_data_source_invalid`: any out-of-set value = write-path regression. Builds its `IN`-clause directly from the `cd.DATA_SOURCE_*` frozensets — **the harness and every write path share ONE canonical source**. Same pattern as `check_geo_recon` importing canonical geo-count SQL.

Both pass at 0 immediately post-migration. This makes provenance self-protecting: every subsequent write-path patch was validated by these invariants before being committed.

### Step 4 — Write-Path Patches: Traders (commit e9a0669)

**Origin semantics: first-writer-wins, consistent across all 4 tables.**

Four discovery INSERT paths patched to set `data_source` in parallel with `discovery_source`:
1. `discover_market_participants.py` → `data_source='market_scan'` literal.
2. `discover_leaderboard_traders.py` → `data_source='leaderboard'` literal.
3. `resolution_sweep.py` → `data_source='resolution_sweep'` literal.
4. `add_watched_trader.py` → `data_source='manual_watchlist'` literal + CASE guard in DO UPDATE (upgrades from NULL/`live_feed`, preserves any other existing value).

**`database.py add_or_update_trader` intentionally untouched** — column DEFAULT `live_feed` fires correctly for new rows; DO UPDATE omits both provenance columns so existing `data_source` survives monitor upserts.

### Step 5 — Write-Path Patches: Markets (commit 3617361)

**Pre-existing bug fixed here: refresh_markets.py resolution-state corruption.**

Four markets paths:
1. `database.py update_market` — no change; DEFAULT `live_monitoring` + DO UPDATE already omits `data_source`.
2. `background_backfill_worker.py` — added `data_source='background_backfill'` to stub INSERT OR IGNORE.
3. `backfill_missing_markets.py` — same: `data_source='background_backfill'`.
4. **`refresh_markets.py`** — replaced `INSERT OR REPLACE` with `INSERT ... ON CONFLICT DO UPDATE`. The old `REPLACE` did `DELETE+INSERT`, destroying all unspecified columns — including `data_source`, **`resolved`**, and **`winning_outcome`** — on every refresh run. **Bug #1**: a resolved market that got refreshed had its resolution silently wiped back to `resolved=0, winning_outcome=NULL`. The new DO UPDATE only touches columns refresh legitimately owns (`title`, `category`, `end_date`, `condition_id`, `api_id`, `last_checked`). Provenance and resolution state preserved.

### Step 6 — Write-Path Patches: Trades (commit d780611)

**Pre-existing bug fixed here: backfill corpus mislabeled.**

1. `background_backfill_worker.py` trades INSERT — added `data_source='background_backfill'`. Previously fell through to DEFAULT `polymarket_api`, silently mislabeling the **entire backfill corpus**. **Bug #2**: every trade fetched by the background backfill worker was tagged as coming from the live Polymarket API rather than from a historical fill. Now distinguishable.
2. `database.py add_trade` — no patch needed; DEFAULT `polymarket_api` + `IntegrityError`-return-on-conflict preserves origin both directions (first-writer-wins by construction).

### Step 7 — Write-Path Patches: Positions (commit 791dbf5)

**Most serious pre-existing bugs found and fixed here: all 4 positions paths used INSERT OR REPLACE.**

`INSERT OR REPLACE` does `DELETE+INSERT`, so **every column not explicitly listed reverts to its DEFAULT** on every cycle. For positions this meant:
- `is_synthetic_close` (DEFAULT 0): **reverted from 1→0 on every 15-minute cycle** for 1.2M+ synthetic-close positions. The correct synthetic flag was being silently erased and had to be recomputed next run.
- `data_source`: wiped back to DEFAULT `position_tracker` regardless of what was set at insertion.
- `created_at`: reset to the current timestamp on every upsert — meaning positions had no stable insertion time.

**Bug #3** (the most serious): this was happening on every cycle across all 4 positions write paths (`position_tracker.py`, `background_pnl_worker.py`, `backfill_synthetic_closes.py`, `database.py insert_position`). All 4 converted to `ON CONFLICT DO UPDATE` with verified column coverage:
- 10 mutable exit/PnL/status fields explicitly in DO UPDATE (nothing frozen that should update).
- `data_source`, `is_synthetic_close`, `created_at`, `entry_timestamp` **intentionally omitted** (preserved by construction).
- `backfill_synthetic_closes.py` gets a CASE guard: upgrades `position_tracker→synthetic_resolution`, never downgrades. `is_synthetic_close` in DO UPDATE because backfill is the authority for that flag.

Post-patch: 0 `INSERT OR REPLACE` remaining in any positions path. All 10 mutable fields still update correctly (UPSERT didn't freeze anything it shouldn't).

---

## TEST INFRASTRUCTURE

### `tests/test_data_source_write_paths.py` — 30 tests (commits bf266e9, d780611, 791dbf5)

Built incrementally alongside the write-path batches. Tests exercise real write paths against guarded temp DBs that mirror the full production schema (production DB path-equality assertion as guard). Three staged additions:

- **T1–T10** (10 cases, 14 assertions): all markets + traders write paths. Covers PROVENANCE-ON-INSERT (background_backfill_worker, backfill_missing_markets, refresh_markets, database.update_market, all 4 traders paths), ORIGIN-PRESERVATION (refresh on existing historical_backfill market; refresh on resolved market; update_market DO UPDATE; stub-then-live-update chain), and HARNESS INTEGRATION (check_data_source_nulls + check_data_source_invalid both return 0 on a fully-populated test DB).
- **T11–T15** (5 tests for trades): add_trade DEFAULT; backfill full path; conflict preservation both directions; **T15 REGRESSION LOCK** — asserts `background_backfill` AND rejects `polymarket_api` for the backfill worker. Would FAIL on pre-patch code.
- **T16–T23** (8 tests for positions): **T20 REGRESSION LOCK** — synthetic position survives a tracker UPSERT (both `is_synthetic_close` AND `data_source` preserved); would FAIL on old OR-REPLACE code. T21 locks created_at preservation. T22 verifies mutable fields still update. T23 locks the CASE guard (no downgrade, correct upgrade).

All 30 pass. All three regression locks would fail on the pre-patch code — the tests are honest.

### `run_tests.py` — subprocess test runner (commit 6da148c)

Discovers `tests/test_*.py` via glob, runs each as a subprocess with a 300s per-file timeout. Parses test counts from each file's summary output. Reports per-file pass/fail + aggregate summary. Exit code 0 only if all files pass — failure propagation proven (tested explicitly). Flags:
- `--verbose`: full output for all files (default: quiet, summary only).
- `--skip=file.py`: exclude files from a run without removing them from discovery. Used to gate `test_behavioral_integration.py` from automation since it calls `analyze_all_traders()` on a cold cache in subprocess context.

### `test_behavioral_integration.py` tests 3+4 rewrite (commit c736558)

Tests 3 and 4 previously called `UnifiedELOSystem` methods that triggered `analyze_all_traders()` on a cold in-memory cache — loading all 8M trades + per-trader metrics = **~39-minute hang in every subprocess invocation**. Rewrites both tests to query stored DB values directly (same pattern as the other 6 sub-tests), removing the `UnifiedELOSystem` dependency entirely:

- **Test 3** (minimum_sample_filter): two-sided filter check — (a) qualified pool ≥1,000 traders, (b) top-20 unfiltered includes under-threshold traders (non-vacuous), (c) top-20 WITH filter has zero under-threshold traders (no leakage). Suite now completes in ~0.25s.
- **Test 4** (behavioral_elo_modifier): three assertions against stored `behavioral_modifier` — (a) ≥1,400 kelly-scored traders have non-neutral modifier (scale check, baseline 1,480 verified), (b) modifier range within [0.75, 1.50], (c) bidirectional (both boost and suppress exist).

**Note**: 3 pre-existing failures remain in tests 2, 5, 6 — these were failing in the original code but were unreachable due to the hang. See Deferred section below.

---

## ELO CHAIN INVESTIGATION (deferred — but fully mapped)

Investigated the full `comprehensive_elo` chain before the session closed. Not built yet — but the map is complete and is the Layer 2 starting point:

**4 writers to `comprehensive_elo`:**
1. `migrate_add_comprehensive_elo.py` — schema migration, sets initial default.
2. `update_comprehensive_elo.py` — the primary recalculation script (FROZEN since session #38).
3. `calculate_elo_simple.py` — simulation script; resets modifiers to 1.0 (now guarded by `_sim_db_guard.py`).
4. `update_database_from_csvs.py` — CSV import path writing behavioral analysis results.

**Two formula paths in the ELO chain:**
- **Path A**: multiplicative combination of base ELO × behavioral_modifier × advanced_modifier × pnl_modifier.
- **Path B**: additive-dampened formula — base ELO + weighted sum of behavioral/advanced/pnl deltas, with a damping factor to limit modifier influence.

Both paths exist in the codebase; the Layer 2 reconciler needs to resolve which is canonical and enforce single-writer semantics. ELO chain is **recomputable from source** (trade history is immutable), so the reconciler can be built as a regenerative single writer rather than a patch.

**Harness gap**: `audit_invariants.py` has ZERO `comprehensive_elo` coverage. Layer 2 will add this as the first act.

**Cluster D closes by construction**: the ~1,346 traders with modifiers at 1.0 after being processed — ambiguous in the forensic map — will be resolved when the reconciler re-derives all modifiers from trade history. The reconciler is the answer, not further forensic investigation.

---

## DEFERRED: BEHAVIORAL-INTEGRATION TEST FAILURES + OPEN QUESTIONS

Three tests in `test_behavioral_integration.py` fail for real reasons (diagnosed, not stale thresholds except #5):

**Test 5 (ROI cap 500%)** — STALE assertion. Real long-shot traders hit 2,444% ROI (legitimate — small positions on low-probability markets). The 500% cap is too tight. Fix: widen the assertion. Minor.

**Test 2 (kelly score coverage 4.8%)** + **Test 6 (weighted_win_rate coverage 0.5%)** — REAL ISSUE. `integrate_behavioral_elo.py` has not been run on the current trader population. Most kelly scores and weighted_win_rate values in the DB are from a prior run against an older, now-excluded trader set. The behavioral layer is largely unpopulated for the active pool. This is directly relevant to Layer 2: the ELO chain consumes behavioral modifier inputs.

**Test 6 also exposed a data consistency bug**: 1,113 traders have `weighted_win_rate` set but `resolved_trades_count = 0`. This is impossible (weighted win rate requires resolved trades). An old write set one column; a later op reset the other without clearing. Competing-writer disease in the behavioral columns — same disease the provenance work diagnosed and cured in positions.

**Open question for next session**: 
1. How to handle tests 2+6 — `xfail`/known-issue markers to keep the suite honest-but-not-red vs. fix the behavioral integration now vs. investigate the consistency bug first?
2. Is running `integrate_behavioral_elo.py` on the current population a Layer 2 prerequisite?
3. Wire `run_tests.py` into maintenance with file-based results (`tests/LATEST_TEST_RESULTS.md`, non-blocking, NOT Telegram — Oscar's preference stated this session).

Pre-commit hook + auto-fix automation deferred (too complex for now — Oscar's call).

---

## FOUNDATIONAL SEQUENCE TO ELO UNFREEZE (updated)
1. [DONE] Simulation safety guard (`_sim_db_guard.py`, all 12 scripts patched)
2. [DONE] Provenance schema: Section 5 frozensets + `migrate_add_data_source.py` + harness invariants + all 14 write-path patches + 30-test regression suite + `run_tests.py`
3. [DONE] Three pre-existing data-integrity bugs fixed: refresh_markets resolution-wipe (Bug #1), backfill_worker trades mislabel (Bug #2), all-4-positions OR-REPLACE synthetic-close/provenance-wipe (Bug #3)
4. [NEXT] Resolve behavioral-integration test question: xfail vs. fix; likely run `integrate_behavioral_elo.py` on current population
5. Wire `run_tests.py` into maintenance (file-based results, non-blocking)
6. Layer 2 ELO chain reconciler: resolve Path A vs B formula, add `comprehensive_elo` harness coverage, build single-writer reconciler (resolves Cluster D, closes competing-writer disease for ELO)
7. Competing-writer teardown: `weighted_win_rate`/`resolved_trades_count` consistency bug + remaining behavioral columns
8. **THEN** unfreeze ELO recalc

---

## COMMITS THIS SESSION (first-repo, all pushed)
| Hash | Description |
|------|-------------|
| `a5f9bb7` | defensive: simulation framework safety — production DB guard (13 files, 3 writers protected) |
| `1efcd90` | feat: data provenance — governed data_source column + migration (4 tables, 8M+ rows) |
| `393a908` | feat: harness governance — check_data_source_nulls + check_data_source_invalid |
| `1107a28` | feat: close Section 5 frozensets — market_scan, resolution_sweep, background_backfill values |
| `e9a0669` | feat: wire data_source into all 4 traders write paths |
| `3617361` | feat: wire data_source into markets write paths + fix refresh_markets resolution-wipe bug |
| `bf266e9` | test: data_source write-path regression suite T1–T10 (10 cases, 14 assertions) |
| `d780611` | feat: wire data_source into trades write paths + T11–T15 (fixes backfill mislabel bug) |
| `791dbf5` | feat: wire data_source into positions write paths + T16–T23 (fixes OR-REPLACE wipe bug) |
| `6da148c` | feat: add subprocess test runner run_tests.py |
| `c736558` | fix: rewrite tests 3+4 in test_behavioral_integration.py (removes 39-min hang) |

trading-swarm: contamination forensic map (`brain/decisions/2026-06-24-contamination-forensic-map.md`)

---

## FINAL STATE
- 11.2 GB production DB: every row in traders/markets/trades/positions has a non-NULL, in-set `data_source`. Provenance is now a permanent queryable column — the 80-query forensic investigation is a one-time event.
- Three data-integrity bugs fixed as a byproduct of provenance enforcement (refresh resolution-wipe, backfill mislabel, OR-REPLACE synthetic-flag-wipe).
- 30 regression tests lock all 3 fixed bugs + all write-path origin semantics. Any regression trips a test.
- `run_tests.py` provides a clean subprocess runner with correct exit codes for automation.
- Simulation framework safe: all 12 scripts default to `simulation_test.db`; writers hard-refuse production without explicit flag.
- ELO recalc FROZEN. Harness 0 CRITICAL. Drift guard 0 violations.

## STANDING
- **ELO recalc FROZEN** until Layer 2 + harness clean.
- **data_source means ORIGIN everywhere (first-writer-wins)** — never overwrite provenance on upsert.
- **Testing now embedded in workflow**: patch → test → commit. Don't manufacture passing tests — green by fixing the assertion (if genuinely stale) or the real issue (never by lowering the bar).
- **Do not guess rows**: backfill strategy must be evidence-based (the `discovery_source` 1:1 pattern, the Dec-11 time window) — not default-filling unknown rows with a plausible value.
- Three standing protections: harness (data integrity + provenance), maintenance self-healing (geo-count drift), drift guard (definition regression).

## NEXT — Signal/research time-gates (carried)
- June 30: STR003-008 resolves (annotated basis: 1 genuine LEGENDARY); score STR003-004/007/008; RQ-CORRELATION-001.
- July 1: RQ wave (RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001); pre-register RQ-VPIN-001, RQ-ILS-001; STR-002 thesis-cell analysis.
- Mid-July: Peru ONPE oracle → STR003-005 confirm + 5 LEGENDARY STR-002 Peru signals; Maine RCV.
