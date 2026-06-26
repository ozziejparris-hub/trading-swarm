# Data Provenance / Contamination Forensic Map
**Date**: 2026-06-24  
**Status**: FOUNDATIONAL — do not act on findings without reading Section 4 (Blast Radius) first  
**Scope**: All tables — traders, markets, trades, positions, plus all ancillary tables  
**Constraint**: READ-ONLY investigation. No data was modified.

---

## Executive Summary

The production database (`data/polymarket_tracker.db`, 11.2 GB, ~10.6M rows across all tables) is predominantly real Polymarket data. **No large-scale synthetic trader/trade injection was found to have persisted.** The primary contamination vector is the simulation framework (scripts/simulation/) which, before today's guard commit (a5f9bb7, Jun 24 2026), defaulted to the production DB without protection. The investigation found no surviving simulation-seeded traders or trades, but cannot prove with certainty they were never injected — the evidence is consistent with either (a) simulations were run against a now-deleted separate file, or (b) simulations ran against production and `clear_simulation_data()` was called before data accumulated.

The most actionable finding is the **provenance gap**: the system has no durable `data_source` column on any table, making it impossible to audit future insertions without repeating this investigation.

---

## 1. CONTAMINATION SOURCES (Full History)

### Source 1: Simulation Seeders — scripts/simulation/
**Mechanism**: `seed_test_data.py` (added Jan 8, 2026) and `seed_production_data.py` (added Jan 12, 2026)  
**Exposure window**: Jan 8, 2026 → Jun 24, 2026 (today — guard added in commit a5f9bb7)  
**Why dangerous**: Both scripts called `Database()` with no `db_path` argument. `Database.__init__` defaults to `data/polymarket_tracker.db` (line 35 of monitoring/database.py). Any invocation without `--db-path simulation_test.db` wrote to production.  
**What it writes**: traders (random `0x` + token_hex(20) addresses), markets (random 0x + token_hex(32) IDs), trades linking sim traders to sim markets. Discovery_source defaults to `live_feed` — **indistinguishable from real monitoring insertions by that field alone**.  
**Scale if ran with production config**: 500 traders, 200 markets, ~40,000 trades (experiments/configs/config_production.json)

**Sub-source: calculate_elo_simple.py --write-to-db**  
Explicitly resets `behavioral_modifier`, `advanced_modifier`, `pnl_modifier` to 1.0 for ALL traders in the DB (lines 177–182). The guard commit message says this was possible against production. **This is the highest-confidence contamination vector — it would corrupt modifier columns silently.**

**Current guard state (post a5f9bb7)**: All scripts now default to `data/simulation_test.db`. Writers call `assert_safe_to_write()` which hard-refuses production unless `--allow-production-write` is explicitly passed.

### Source 2: Historical Market Backfill — Dec 11, 2025
**Mechanism**: Mass insertion of ~203,031 historical Polymarket markets in a single operation  
**Evidence**: `last_checked` distribution shows 200,663 markets inserted in the 11 AM UTC hour on 2025-12-11 alone  
**Content**: Real Polymarket markets from 2020–2023 era (2020 US election, COVID vaccines, 2022–2023 NBA/soccer matches, etc.) with correct condition_ids  
**Confidence**: **DEFINITELY REAL** — titles match known historical Polymarket markets; pre-simulation era  
**Issue**: ~197,815 of these are unresolved with no winning_outcome. They are real markets whose resolution data was never backfilled (resolved on Polymarket before monitoring was comprehensive).

### Source 3: Jan 12–13, 2026 Trader Discovery Spike
**Mechanism**: Large-scale monitoring run discovering 1,447 traders on Jan 12, 510 on Jan 13  
**Evidence**: Commit `a1c2769` explicitly calls out "exclude 3 Jan-12 ARB_BOT wallets + LP_ARTIFACT market maker"; commit `cbd322a` "exclude 30 ARB_BOT wallets from Jan 12 2026 batch — coordinated wallet factory"  
**Confidence**: **DEFINITELY REAL** — confirmed as real Polymarket coordinated wallet factory events, classified post-hoc as ARB_BOTs  
**Note**: All Jan 12 traders have `discovery_source = 'live_feed'`. 675 of 1,447 are zero-trade (inserted before their trade history was fetched — standard monitoring behavior for batch discoveries).

### Source 4: Leaderboard Discovery Spikes (Feb 2026 – ongoing)
**Mechanism**: `discover_leaderboard_traders.py` runs against Polymarket API  
**Largest spike**: May 17, 2026 — 10,828 traders (6,716 with trades, 3,889 zero-trade)  
**Confidence**: **DEFINITELY REAL** — these are real Polymarket traders scraped from market participant lists

### Source 5: External Seed Import — Jun 6, 2026
**Mechanism**: 195 traders imported from `data/external/user_features.parquet` and `user_pnl_summary.parquet` (HuggingFace dataset)  
**Evidence**: All 195 traders have `first_seen = '2026-06-06'`, `discovery_source = 'external_seed'`  
**Confidence**: **DEFINITELY REAL** — these are real Polymarket traders from a public/research dataset

### Source 6: Synthetic Close Backfill — backfill_synthetic_closes.py
**What it is**: NOT fake data — it computes P&L for open positions in resolved markets where no explicit SELL trade exists  
**Scale**: 1,224,209 positions have `is_synthetic_close = 1`  
**Confidence**: **LEGITIMATE COMPUTATION** — flags positions that were closed at market resolution rather than by SELL trade; required for correct P&L  

### Source 7: Archive Migration Scripts — scripts/archive/migrate_*.py
**What they do**: Schema migrations (`migrate_add_positions.py`, `migrate_add_comprehensive_elo.py`, `migrate_add_trade_outcomes.py`) — these are ALTER TABLE / index creation operations, not bulk data insertion. They do not write synthetic data rows.

### Source 8: CSV Import — scripts/archive/update_database_from_csvs.py
**What it does**: Imports behavioral analysis results (Kelly scores, patience scores, etc.) from CSV files exported by the analysis pipeline. Writes to existing trader rows only — updates, not inserts. Not a synthetic data source.

---

## 2. SYNTHETIC FINGERPRINT CATALOG

| Source | Fingerprint | Distinguishable from real? |
|--------|-------------|---------------------------|
| Simulation traders | Address: `0x` + 40 hex chars (token_hex(20)) | **NO** — identical format to real ETH addresses |
| Simulation traders | discovery_source = `live_feed` | **NO** — same as real live-feed traders |
| Simulation traders | is_flagged = 1 for elite/good tiers | **WEAK** — real traders can also have is_flagged=1 |
| Simulation markets | market_id: `0x` + 64 hex chars (token_hex(32)) | **NO** — identical format to real Polymarket condition_ids |
| Simulation markets | Titles from templates (Elections/Geopolitics/Sports/etc.) | **MOSTLY NO** — real Polymarket markets use same topics |
| Simulation markets | No associated real Polymarket trades (random IDs can't match on-chain activity) | **YES** — if a market has no trades, it MIGHT be simulation; but many real markets also have 0 trades |
| Simulation trades | trade_id: `0x` + 64 hex chars (token_hex(32)) | **NO** — same format |
| Simulation trades | transaction_hash: NULL (no on-chain tx exists for sim trades) | **WEAK** — 77% of real trades also lack transaction_hash in our DB |
| Simulation ELO reset | behavioral_modifier = 1.0 exactly | **WEAK** — new traders also have 1.0 (default); 8% of active traders have this value |
| Leaderboard traders | discovery_source = `leaderboard` | **YES** — clear, legitimate |
| External seed traders | discovery_source = `external_seed` | **YES** — clear, legitimate |
| Orphan repair traders | discovery_source = `orphan_repair` | **YES** — 12 traders, legitimate |
| Synthetic closes | positions.is_synthetic_close = 1 | **YES** — clearly flagged, legitimate computation |

**Key ambiguity**: The simulation's address and market_id generation is cryptographically indistinguishable from real ETH addresses. Without a provenance column written at insertion time, there is no reliable retroactive way to identify simulation rows.

---

## 3. FULL FORENSIC SWEEP — All Tables

### Table: traders (144,933 rows)

**Cluster A: Zero-trade traders — 114,866 rows (79.2% of all traders)**
- Evidence: total_trades = 0
- Breakdown: 97,394 live_feed, 17,470 leaderboard, 1 external_seed, 1 manual_watchlist
- **CONFIDENCE: PROBABLY REAL** — Zero trades is normal in this system. Live monitoring discovers traders when they appear in another trader's trade data, before fetching their own history. Leaderboard scrapes return addresses without trade histories. The 79% zero-trade rate is high but consistent with monitoring pattern where discovery precedes trade history import.
- ELO impact: None — zero-trade traders have comprehensive_elo = 1500 (default) and are excluded from research pool

**Cluster B: 7 zero-trade traders in clean research pool — 7 rows**
- Evidence: total_trades = 0 AND research_excluded = 0
- **CONFIDENCE: AMBIGUOUS** — Should be excluded. Likely recent discoveries not yet processed by update_research_exclusions.py. Low harm.

**Cluster C: Jan 12, 2026 ARB_BOT batch — 147 rows with bot_type = 'ARB_BOT'**
- Evidence: Explicit git commits naming these; all have total_trades > 100; discovery_source = live_feed
- **CONFIDENCE: DEFINITELY REAL** — confirmed coordinated wallet factory, research_excluded = 1

**Cluster D: Possible simulate ELO modifier reset — ~2,400–2,700 active traders with modifiers at 1.0**
- 2,427/30,067 active traders: behavioral_modifier = 1.0
- 2,709/30,067 active traders: advanced_modifier = 1.0
- Of these, 1,081 have never had elo_last_updated set (recently added, not yet processed)
- 1,346 have been updated but modifier is still 1.0
- **CONFIDENCE: AMBIGUOUS** — some fraction could be from calculate_elo_simple --write-to-db reset; some are genuinely new/unprocessed traders. Cannot distinguish without run timestamps.

**Cluster E: orphan_repair traders — 12 rows**
- All have first_seen prior to Nov 2025 (2025-08-10 to 2025-11-03)
- discovery_source = orphan_repair
- **CONFIDENCE: PROBABLY REAL** — added by a repair process to fix orphaned trade references

### Table: markets (536,611 rows)

**Cluster F: Dec 11, 2025 historical backfill — ~203,031 rows**
- Time window: 2025-12-11 11:00–23:59 UTC (200,663 in the 11 AM hour alone)
- Evidence: Titles span 2020–2023 era (2020 election, 2022 NBA, 2023 F1)
- **CONFIDENCE: DEFINITELY REAL** — real Polymarket historical markets, correct condition_ids
- Issue: 197,815 of these have resolved = 0 (no resolution data backfilled)

**Cluster G: No-trade markets — 134,859 rows**
- ~130,087 from Dec 11 2025 backfill (real historical markets never traded in our monitoring period)
- ~3,765 from April 1, 2026 update (confirmed real: NBA/F1/sports 2023 markets)
- **CONFIDENCE: PROBABLY REAL** — markets from historical eras before monitoring started; no trades because monitoring began after they resolved

**Cluster H: 2 orphaned trades (trades referencing non-existent markets)**
- market_ids: 0x1d4b27b06b2d5ffab2b641c017ddfa772c663528fefa89f756e2b8ee670b1830 and 0x6be8870079db61fc52ae61f57256e91734d5ce3071a41d174ccb88bffc1a047d
- **CONFIDENCE: AMBIGUOUS** — could be markets that were deleted after trades were recorded, or data corruption. Very small.

**Cluster I: Duplicate market titles (multiple IDs, same title)**
- Multiple condition_ids with title "Will Iran recognize Iran by June 2025?", "Yankees vs Giants - {team} wins?", etc.
- These are real Polymarket phenomena — the same event can have multiple markets with the same title but different condition_ids
- **CONFIDENCE: PROBABLY REAL** — Polymarket legitimately creates multiple markets with similar/identical titles for different contract parameters
- The `{team}` placeholder in titles like "Yankees vs Giants - {team} wins?" is confirmed real: these markets have trades going back to August 2025 (before simulation existed)

**Note on simulation market evidence**: Despite an intensive search, no confirmed simulation-only markets were found persisting in production. The 0 result from the query "Jan 11-14 traders exclusively in Jan 11-14-first-seen markets" is strong evidence that simulation data (if ever injected) was cleaned up.

### Table: trades (7,965,286 rows)

**Cluster J: No confirmed synthetic trade clusters found**
- Trade volume during Jan 8-14 simulation development: 8,144–11,094 trades/day — consistent with normal monitoring rate
- Transaction hash coverage during Jan 8-14: 37-46% (matches overall DB average of 23%)
- No date period shows a sudden spike consistent with bulk synthetic insertion (except for real live monitoring spikes tied to market activity)

**Cluster K: Trades with no transaction_hash — 6,110,632 rows (76.7%)**
- **CONFIDENCE: PROBABLY REAL** — the transaction hash backfill (`backfill_transaction_hashes.py`) was only partially completed. Real Polygon/CLOB trades exist without hash records in our system.

### Table: positions (4,968,328 rows)

**Cluster L: Synthetic closes — 1,224,209 rows with is_synthetic_close = 1**
- **CONFIDENCE: DEFINITIVELY LEGITIMATE** — computed P&L for positions in resolved markets without explicit SELL trades. Not contamination. 1,224,201 of these have actual non-zero realized_pnl.

**Cluster M: No orphaned positions found**
- 0 positions reference non-existent traders
- 0 positions reference non-existent markets
- Foreign key integrity is clean

### Other Tables

| Table | Rows | Assessment |
|-------|------|------------|
| elo_snapshots | ~(daily snapshots) | REAL — daily snapshots of real ELO scores |
| str002_signals | (signal registry) | REAL — derived from real market observations |
| insider_signals | (detected patterns) | REAL — derived from real trade patterns |
| insider_clusters | (cluster detections) | REAL — derived from real trade patterns |
| order_book_snapshots | (CLOB snapshots) | REAL — fetched from Polymarket CLOB API |
| monitor_state | KV store | REAL — monitoring state |
| monitoring_status | 1 row | REAL — monitoring health |
| trader_categories | (derived) | REAL — computed from real trades |

---

## 4. BLAST RADIUS RANKING

### Tier 1 — ACTIVE HARM (ELO pipeline corrupted right now)

**Risk: ELO modifier reset from calculate_elo_simple --write-to-db**
- Impact: behavioral_modifier, advanced_modifier, pnl_modifier reset to 1.0 for all 87K traders
- Affected rows: 2,427–2,709 active traders show unexplained 1.0 modifiers after being processed
- Harm: ELO scores lose modifier differentiation → elite trader pool signals degraded
- **PROBABILITY OF HAVING OCCURRED: MEDIUM** — the commit message explicitly warned this was possible before today's guard
- Detection: Compare modifier distribution against expected distribution from behavioral analysis. Traders with elo_last_updated set but behavioral_modifier = 1.0 exactly are suspicious.

### Tier 2 — POTENTIAL HARM (if simulation data persists)

**Risk: Simulation traders in ELO / research pool**
- Simulation traders would have artificially constructed win rates (designed to produce 42%–58% win rates by tier)
- They would pass most ELO input gates (non-zero trades, resolved markets with outcomes)
- Impact: False ELO signals if simulation-resolved markets fed ELO deltas
- **PROBABILITY: LOW** — forensic query returned 0 simulation-isolated trader/market pairs from Jan 11-14

**Risk: 7 zero-trade traders in clean research pool**
- Impact: Minimal — they have comprehensive_elo = 1500 (default), contributing only noise to averages
- Fix: run update_research_exclusions.py (already in daily maintenance)

### Tier 3 — INERT / NEGLIGIBLE

**Risk: 114,859 zero-trade research_excluded traders**
- Impact: NONE — they are already excluded from all analysis pools

**Risk: 134,859 no-trade historical markets**
- Impact: NONE for ELO (no trades = no ELO deltas). Potential noise in market count statistics.

**Risk: 197,815 resolved=0 historical markets with no winning_outcome**
- Impact: NONE for ELO (unresolved markets don't generate ELO updates). They inflate market count statistics.

**Risk: 2 orphaned trades**
- Impact: NEGLIGIBLE — 2 rows referencing non-existent markets. They are excluded from ELO and P&L calculations automatically.

**Risk: 1,224,209 synthetic closes**
- Impact: ZERO contamination risk — these are legitimate computed P&L entries, correctly flagged.

---

## 5. PROVENANCE SCHEMA PROPOSAL

### Proposed Schema Addition

Add a `data_source` column to all four core tables. This makes provenance knowable forever — no future investigation required.

```sql
-- traders table
ALTER TABLE traders ADD COLUMN data_source TEXT DEFAULT 'live_feed';
-- Allowed values: live_feed, leaderboard, external_seed, manual_watchlist, 
--                 orphan_repair, simulation (new), backfill, blockchain_scan

-- markets table
ALTER TABLE markets ADD COLUMN data_source TEXT DEFAULT 'live_monitoring';
-- Allowed values: live_monitoring, historical_backfill, simulation (new), 
--                 manual_entry, api_refresh, stub_placeholder

-- trades table
ALTER TABLE trades ADD COLUMN data_source TEXT DEFAULT 'polymarket_api';
-- Allowed values: polymarket_api, blockchain_scan, simulation (new), 
--                 backfill_import, computed

-- positions table (is_synthetic_close already handles the key flag; add for completeness)
ALTER TABLE positions ADD COLUMN data_source TEXT DEFAULT 'position_tracker';
-- Allowed values: position_tracker, backfill_historical, simulation (new)
```

### Backfill Strategy for Existing Rows

**traders**: Already partially implemented via `discovery_source` column. Map:
- discovery_source `live_feed` → data_source `live_feed` (includes unverified sim traders)
- discovery_source `leaderboard` → data_source `leaderboard`
- discovery_source `external_seed` → data_source `external_seed`
- discovery_source `manual_watchlist` → data_source `manual_watchlist`
- discovery_source `orphan_repair` → data_source `orphan_repair`

**markets**: No existing provenance field. Backfill by time window:
- `last_checked` ≈ 2025-12-11: data_source = `historical_backfill`
- All others first seen during live monitoring windows: data_source = `live_monitoring`
- Cannot backfill historical vs simulation without additional evidence

**trades**: No existing provenance field. Conservative default:
- All existing rows: data_source = `polymarket_api` (best assumption)
- Rows added by blockchain_scan (`backfill_transaction_hashes.py`): data_source = `blockchain_scan`

**positions**: 
- is_synthetic_close = 1: data_source = `synthetic_resolution`
- is_synthetic_close = 0: data_source = `position_tracker`

### Forward Policy

All write paths must set data_source at insertion time:
1. **monitoring/monitor.py** (live feed): data_source = `live_feed`
2. **discover_leaderboard_traders.py**: data_source = `leaderboard`
3. **discover_market_participants.py**: data_source = `live_monitoring`
4. **scripts/simulation/ (if ever run against production)**: data_source = `simulation`
5. **backfill scripts**: data_source = `backfill`
6. **external imports**: data_source = `external_seed`

The `_sim_db_guard.py` guard ensures simulation scripts default to `simulation_test.db`. If `--allow-production-write` is ever used, the simulation scripts should be updated to set data_source = `simulation` so those rows are permanently flagged.

---

## 6. KEY UNCERTAINTIES AND WHAT WOULD RESOLVE THEM

| Question | Current confidence | What would resolve it |
|----------|-------------------|----------------------|
| Was simulate_production ever run against production DB? | LOW — no persistent evidence found | Check OS-level bash history or process logs for invocations of seed_production_data.py without --db-path |
| Were ELO modifiers reset by calculate_elo_simple? | MEDIUM — suspicious 1.0 counts | Run behavioral analysis fresh; compare output to current DB modifier values |
| Are the 7 zero-trade clean-pool traders simulation artifacts? | LOW — 7 rows is very small | Run update_research_exclusions.py (should clean them automatically) |
| Are the 2 orphaned trades from simulation? | LOW — could be normal data gaps | Check market_ids against Polymarket API directly |
| Did the simulation clear_simulation_data() run clean up injected rows? | UNKNOWN — no log evidence | Check if simulation_test.db or any backup from Jan 2026 exists |

---

## 7. SUMMARY TABLE OF ALL CLUSTERS

| Cluster | Table | Size | Confidence | ELO Harm | Notes |
|---------|-------|------|------------|----------|-------|
| A | traders | 114,866 | Probably Real | None | Zero-trade but research_excluded |
| B | traders | 7 | Ambiguous | Low | Zero-trade in clean pool — fix: run update_research_exclusions |
| C | traders | 147 | Definitely Real | None | ARB_BOT wallets, correctly excluded |
| D | traders | ~1,346 | Ambiguous | Medium | Modifiers = 1.0 after update — possible calculate_elo_simple reset |
| E | traders | 12 | Probably Real | None | orphan_repair, pre-Nov 2025 |
| F | markets | 203,031 | Definitely Real | None | Historical backfill, no trades needed |
| G | markets | 134,859 | Probably Real | None | No-trade historical markets |
| H | trades | 2 | Ambiguous | None | Orphaned trades — market reference broken |
| I | markets | ~50+ | Probably Real | None | Duplicate-title markets from Polymarket itself |
| J | trades | 0 confirmed | N/A | None | No confirmed synthetic trade clusters |
| K | trades | 6,110,632 | Probably Real | None | Missing tx_hash — normal incomplete backfill |
| L | positions | 1,224,209 | Definitely Legitimate | None | Synthetic closes — correct computation |
| M | positions | 0 | N/A | None | No orphaned positions |

---

## 8. RECOMMENDED NEXT STEPS (design, not execution — separate session)

1. **Add data_source columns** to all 4 tables (migration script, ~20 min)
2. **Update all write paths** to set data_source (monitoring, discovery scripts, simulation guard)
3. **Investigate Cluster D** — re-run behavioral analysis and check if modifier output matches DB; if not, a reset occurred and the analysis must be re-applied
4. **Create simulation_test.db** — seeding it now confirms the simulation framework works without production risk
5. **Resolve Cluster B** — run update_research_exclusions.py to clean 7 zero-trade clean-pool stragglers
6. **Consider resolving orphaned trades (Cluster H)** — 2 rows, check market IDs against Polymarket API and either link or delete

---

*Investigation conducted: 2026-06-24. Queries executed: ~80+ read-only SQLite queries. Git history reviewed: full commit log (~150 commits). Scripts read: seed_test_data.py, seed_production_data.py, _sim_db_guard.py, database.py (write paths), backfill_synthetic_closes.py, and archive migration scripts.*
