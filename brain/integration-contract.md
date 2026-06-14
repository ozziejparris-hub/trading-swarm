# Integration Contract — first-repo ↔ trading-swarm

**Version:** v2.9 — 2026-06-13
**Owner:** Oscar (ozziejparris@gmail.com)

This is the single source of truth for what first-repo exposes and what
trading-swarm agents can rely on. Any agent that queries first-repo MUST
follow this contract. Violations cause silent data corruption that
propagates into research findings and trading signals.

---

## Section 1 — Database

```
Path: /home/parison/projects/first-repo/data/polymarket_tracker.db
Mode: WAL (Write-Ahead Logging)
```

**Connection pattern — copy this exactly:**

```python
import sqlite3

DB_PATH = "/home/parison/projects/first-repo/data/polymarket_tracker.db"

conn = sqlite3.connect(DB_PATH, timeout=30)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
```

**Why WAL:** The database is written to by daily_maintenance.py scripts and
read by research agents concurrently. WAL allows concurrent reads without
blocking writes. Without `busy_timeout`, any write lock causes an immediate
`OperationalError: database is locked` — the 30s timeout lets agents
queue rather than crash.

---

## Section 2 — Mandatory Query Filters

Every research query MUST include ALL of the following filters. Omitting
any one of them introduces contaminated data into research results.

```sql
JOIN markets m ON m.market_id = t.market_id   -- NOT m.condition_id (see warning below)
WHERE tr.research_excluded = 0
  AND t.timestamp <= datetime('now')
  AND m.resolved = 1
  AND m.winning_outcome NOT IN ('unknown', '')
  AND m.winning_outcome IS NOT NULL
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
```

**Why each filter exists:**

> **WARNING: `condition_id` must NEVER be used as a JOIN key to trades.** Empirical validation on 2026-05-20 confirmed `m.market_id = t.market_id` matches 3,541,160/3,541,160 trades (99.999%), while `m.condition_id = t.market_id` matches only 2,241,596 (63%). `condition_id` is a separate Polymarket identifier used for external API resolution lookups only.

| Filter | Reason |
|--------|--------|
| `m.market_id = t.market_id` | Empirically validated join key — matches 99.999% of trades. `condition_id` is a distinct Polymarket field for external API resolution lookups; it is NOT a join key to trades and silently drops 37% of rows if used. |
| `tr.research_excluded = 0` | Excludes bots, wash traders, and thin-sample traders. Including them inflates signal counts and corrupts ELO accuracy metrics. |
| `t.timestamp <= datetime('now')` | 37 future-dated trades exist in the DB from a data import error. They have not resolved yet and pollute forward-looking calculations. |
| `m.resolved = 1` | Only resolved markets have ground truth outcomes. Unresolved markets have no winning_outcome to validate against. |
| `m.winning_outcome NOT IN ('unknown', '')` | 497 markets resolved with outcome='unknown' (no clear resolution). Including them produces Brier score errors and false accuracy signals. |
| `m.winning_outcome IS NOT NULL` | Belt-and-suspenders for NULL entries missed by the NOT IN filter. |
| `m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL` | 166 markets have trade_gap_flag=1 from the April 7-18 server migration. Trades during that window are missing, making position data incomplete for those markets. |

---

## Section 3 — Research Pool

**Current pool sizes:** See `brain/integration-health.json` (updated daily at 06:00 UTC by write_integration_health.py). Never hardcode these numbers — always read them live.

A trader is included in the research pool (`research_excluded = 0`) if ALL
criteria are met:

- `resolved_trades_count >= 20` — enough history for statistically meaningful ELO
- `bot_suspect = 0` — not flagged as automated trading
- `wash_trade_suspect = 0` — not flagged for self-dealing
- `bot_type IS NULL` — not categorised as any known bot pattern

**Do not hardcode the pool size.** Query it live at the start of each run:

```sql
SELECT COUNT(*) FROM traders WHERE research_excluded = 0
```

The pool is refreshed daily at 06:00 UTC by `update_research_exclusions.py`
(Step 0 of `daily_maintenance.py`). Pool size drifts as new traders
accumulate enough resolved trades to qualify, or as bot detection flags
new accounts.

### Traders Table — Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `address` | TEXT | Wallet address (primary key) |
| `research_excluded` | INTEGER | 0 = Pool B (clean); 1 = excluded |
| `resolved_trades_count` | INTEGER | Total resolved trades across all markets |
| `bot_suspect` | INTEGER | 1 = suspected automated trader |
| `wash_trade_suspect` | INTEGER | 1 = suspected wash trader |
| `bot_type` | TEXT | `LP_ARTIFACT`, `THIN_SAMPLE_ARTIFACT`, `ARB_BOT`, or NULL |
| `accuracy_pool` | BOOLEAN | DROPPED 2026-06-05 — written daily but never consumed by any downstream script. Column removed from DB. |
| `comprehensive_elo` | REAL | ELO across all markets |
| `realized_pnl` | REAL | Realized P&L in USD (authoritative — see Section 6b) |
| `geo_elo` | REAL | Market-implied probability ELO for geopolitics+elections trades only |
| `geo_elo_active` | REAL | Recency-decayed geo_elo: geo_elo × 0.5^(days_dormant/180). 180-day half-life. Used for STR-003 signal qualification. Base geo_elo preserved for research. Updated daily by update_geo_elo.py. |
| `geo_elo_oos` | REAL | DROPPED 2026-06-05 — populated by deleted script, zero code references. Column removed from DB. |
| `geo_resolved_trades_count` | INTEGER | Resolved trades in geo/elections markets |
| `geo_directionality_score` | REAL | Fraction of geo capital on dominant side (0=pure LP, 1=fully directional) |
| `geo_accuracy_pool` | BOOLEAN | 1 = Pool C (geopolitics accuracy) |

---

## Section 4 — ELO Tiers

ELO tier thresholds for trader segmentation:

| Tier | Primary Field | Secondary Field | Threshold |
|------|--------------|-----------------|-----------|
| Legendary (geo) | `geo_elo_active` | `geo_elo` | >= 2175 |
| Elite (geo) | `geo_elo_active` | — | > 1800 |
| Strong (comprehensive) | `comprehensive_elo` | — | > 1550 |

**`geo_elo_active` is the primary field for all LEGENDARY tier decisions.** `geo_elo` (without recency decay) is preserved for research comparisons only. Never gate signal generation on `geo_elo >= 2175` — use `geo_elo_active >= 2175`.

**Always pair tier filters with the research exclusion filter:**

```sql
WHERE geo_elo_active >= 2175
  AND research_excluded = 0
```

**Never use** traders tagged with `bot_type IN ('LP_ARTIFACT', 'THIN_SAMPLE_ARTIFACT', 'ARB_BOT')`.
These are measurement artefacts — their ELO scores are not predictive:

| bot_type | Count | Description |
|----------|-------|-------------|
| `LP_ARTIFACT` | ~257 | Liquidity provision artefacts — thousands of positions on a single market, massive negative PnL from LP interactions |
| `THIN_SAMPLE_ARTIFACT` | — | Data sparsity artefacts — too few resolved trades for meaningful ELO |
| `ARB_BOT` | 111 | Coordinated arbitrage wallets (single-market, Nov 2025 geopolitics). ELO 3308–3315 cluster — measurement artefact, not skill. Excluded 2026-05-06. |

**STR-003 geo ELO tier — uses `geo_elo_active`, not `comprehensive_elo`:**

STR-003 signal qualification uses `geo_elo_active >= 2175`. `geo_elo_active` is the recency-decayed version of `geo_elo` — it down-weights traders who have been dormant for 6+ months so that stale high ELO scores do not generate signals. See Section 3 for formula.

---

## Section 5 — Active Strategies

| Strategy | Status | Notes |
|----------|--------|-------|
| LH-001 | CONDITIONAL_PASS | Lifecycle heuristic insider detection. Watchlist trigger only — not a trading signal. Pooled p=0.0160, r=0.208. Blocking items remain before PASS upgrade (see strategy-registry.md). |
| STR-001 | SUSPENDED | LP contamination — liquidity provider trades inflate signal counts |
| STR-001b | SUSPENDED | 0 qualifying signals after STR-001 fix |
| STR-002 | EXPERIMENTAL | Accumulating pre-resolution accuracy data (n=4 as of 2026-05-05) |
| STR-003 | EXPERIMENTAL | Primary strategy: single legendary geo trader (`geo_elo_active >= 2175`, `geo_directionality_score >= 0.7`, `realized_pnl != 0.0 AND realized_pnl > -100000`, `research_excluded = 0`, signal trade price BETWEEN 0.10 AND 0.80) with ≥95% of capital on one side. Max 5 concurrent GEOPOLITICS/ELECTIONS markets (not platform-wide). Bidirectional holders excluded. P&L filter: realized_pnl != 0.0 AND realized_pnl > -100000 — removes exact-zero redemption accounts and spread-compression LPs (< -$100K). Does not exclude legitimate directional traders with modest or negative P&L from correct directional losses. **STR-003 signals must weight by archetype × domain — see Section 11. YIELD_HARVESTERs must never contribute to signals.** |
| STR-004 | HYPOTHESIS | Capital-weighted legendary aggregate signal: when capital-weighted aggregate of legendary traders diverges from market price by ≥20pp, fires as signal. Pre-registered 2026-05-08. Founding case resolved NO (n=1). Needs 9 more resolved signals. |

**STR-003 — Concurrent Market Count Exclusions (added v1.7, 2026-05-29):**

Concurrent market count excludes:
- Markets where `resolved = 0 AND resolution_date < datetime('now', '-180 days')`
  (unresolved for 6+ months — template/stale markets)
- Markets where `markets.category NOT IN ('Geopolitics','Elections')`

> **Note:** Category filtering uses `markets.category` (the markets table column), NOT `trades.market_category` (the denormalized column in the trades table). `trades.market_category` is a snapshot synchronized daily by sync_trade_categories.py — use `markets.category` via JOIN for authoritative category values. See Section 6c for architecture rule.

Rationale: Stale unresolved markets contain no actionable information.
A trader holding a 2025 template position is not actively trading that market.
Decision: Oscar, 2026-05-29.

### STR-003 Signal Canonical Schema

All STR-003 signals must carry the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `signal_id` | TEXT | e.g. STR003-005 |
| `status` | TEXT | See status values below |
| `market_id` | TEXT | Polymarket market_id |
| `market_title` | TEXT | Human-readable title |
| `direction` | TEXT | YES or NO |
| `registered_at` | TEXT | ISO datetime of signal registration |
| `signal_date` | TEXT | Date string |
| `key_traders` | LIST | List of trader addresses |
| `trader_elos_at_registration` | DICT | {address: geo_elo_active} at registration time |
| `market_price_at_registration` | REAL | Market price at signal time |
| `legendary_count` | INTEGER | Count of qualifying LEGENDARY traders |
| `signal_credibility_score` | REAL | Computed credibility score |
| `signal_credibility_tier` | TEXT | e.g. STRONG, MODERATE, WEAK |
| `outcome_correct` | BOOLEAN or NULL | NULL until resolved |
| `resolved_at` | TEXT or NULL | ISO datetime of resolution |
| `scored_at` | TEXT or NULL | ISO datetime scoring was applied |
| `notes` | TEXT | Free-text notes |

**Status values:** `ACTIVE` | `PENDING_RESOLUTION` | `RESOLVED_CORRECT` | `RESOLVED_WRONG` | `ACTIVE_BELOW_THRESHOLD` | `RETIRED`

### STR-003 Current Signal Status (as of 2026-06-11)

| Signal ID | Status | Description |
|-----------|--------|-------------|
| STR003-001 | ACTIVE_BELOW_THRESHOLD | — |
| STR003-003 | RESOLVED_WRONG | Warsh Fed |
| STR003-004 | ACTIVE | Putin invasion NO — resolves June 30 |
| STR003-005 | RESOLVED_CORRECT | Keiko Peru YES — scored 2026-06-11 (Polymarket 97%) |
| STR003-006 | RESOLVED_WRONG | López Aliaga YES |
| STR003-007 | ACTIVE | Iran regime fall NO — resolves June 30 |
| STR003-008 | ACTIVE | European security guarantee NO — resolves June 30 |
| STR003-009 | RESOLVED_WRONG | Graham SC NO |

**Scored accuracy: 1/4 (25%)** — STR003-005 correct; STR003-003, STR003-006, STR003-009 wrong.

### Pre-Registered Research

All pre-registration documents are in `brain/strategy-notes/`. No experiment may run without prior approval.

| RQ ID | Filed | Implement | Description |
|-------|-------|-----------|-------------|
| RQ-POOL-QUALITY-001 | 2026-06-10 | 2026-07-01 | LEGENDARY pool quality filter: ≥30 geo trades, ≥10 distinct markets, no single market >40% concentration |
| RQ-EXT-001a/b/c | 2026-06-10 | 2026-08-01 | External dataset discovery validation — re-run 2026-08-01 |
| RQ-SECTOR-001 | 2026-06-10 | 2026-07-01 | Sector rotation signal hypothesis |
| RQ-EXEC-001 | 2026-06-10 | 2026-07-01 | Executive decision signal hypothesis |
| RQ-LH-001 | 2026-06-10 | 2026-07-01 | Lifecycle heuristic upgrade |
| RQ-CONTESTED-001 | 2026-06-10 | 2026-07-01 | Comprehensive ELO on contested markets validation |
| RQ1.1 | 2026-06-10 | 2026-07-01 | ELO in period T predicts Brier in T+1 (Phase 5 gate) |

Agents must read `brain/strategy-registry.md` before generating any
signals — strategies change status frequently and the registry is
authoritative.

---

## Section 6 — Known Data Quality Issues

These are permanent fixtures in the dataset. Do not try to fix them —
they are handled by the query filters in Section 2.

| Issue | Count | Cause | Mitigation |
|-------|-------|-------|------------|
| `trade_gap_flag = 1` markets | 166 | April 7-18 server migration — trades missing | Filter: `trade_gap_flag = 0 OR NULL` |
| `winning_outcome = 'unknown'` markets | 497 | Markets resolved without a clear outcome | Filter: `NOT IN ('unknown', '')` |
| Future-dated trades | 37 | Data import error | Filter: `timestamp <= datetime('now')` |
| ~~`trades.market_id` stores condition_id~~ | — | **Assumption was wrong** — corrected 2026-05-20. `trades.market_id` joins to `markets.market_id` (99.999% match). See Section 2 warning. |

---

## Section 6b — Resolved Data Quality Issues (fixed, documented for context)

| Issue | Resolved | Detail |
|-------|----------|--------|
| Position duplication — BST/UTC timezone mismatch | 2026-05-05 | April 18-20 server migration imported positions twice due to 1-hour BST/UTC offset. 38,630 duplicate rows removed. Post-cleanup totals: 1,026,810 positions total, 73,910 open, 952,900 closed. Dedup guard now in place. |
| `traders.total_pnl` never written | 2026-05-05 | Column existed but the monitor.py UPDATE only wrote `realized_pnl`. Fixed: `total_pnl` now set to `realized_pnl` in every P&L update (unrealized_pnl is a permanent placeholder at 0.0). **Use `realized_pnl` for all P&L queries — it is the authoritative column.** |
| manual_watchlist deadlock | 2026-06-11 | Circular dependency: research_excluded=1 blocked evaluate_new_trader_results.py → trades stuck at 'pending' → resolved_trades_count stayed NULL → re-excluded each daily run. Fix: evaluate_new_trader_results.py now includes grace period for manual_watchlist/external_seed traders with NULL resolved_trades_count. 14/17 manual_watchlist traders unblocked. 612 trades scored (529W/83L). |

### Research Pools (maintained by update_research_exclusions.py)

#### Pool A — Accuracy/Validation Pool

> **Note:** Pool A (accuracy_pool) was dropped 2026-06-05. No replacement defined. Use Pool B filter (research_excluded=0, resolved_trades_count>=20, bot_type IS NULL) for accuracy validation queries.

#### Pool B — General Research Pool
Filter: `research_excluded = 0`
Requirements: `resolved_trades_count >= 20`, `bot_type IS NULL`, `wash/bot suspect = 0`
Used for: All ELO queries, signal generation, quant-research queries
Current size: Read live from `brain/integration-health.json`
Updated by: `update_research_exclusions.py`

> **⚠️ WARNING — Pool B contamination risk:** `research_excluded = 0` alone is NOT sufficient for research queries. 13,000+ leaderboard-discovered traders with `resolved_trades_count < 20` are in Pool B by design (validated by discover_leaderboard_traders.py criteria). Any accuracy calculation MUST add `AND resolved_trades_count >= 20` explicitly. Using `research_excluded = 0` without this filter will silently include thin-sample traders and inflate accuracy metrics.
>
> **Authoritative research filter:**
> ```sql
> WHERE research_excluded = 0
>   AND resolved_trades_count >= 20
>   AND bot_type IS NULL
> ```

#### Pool C — Geopolitics Accuracy Pool
Filter: `geo_accuracy_pool = 1`
Subset of traders with:
- `geo_elo IS NOT NULL` (market-implied probability ELO on geo/elections trades)
- `geo_resolved_trades_count >= 5`
- `geo_directionality_score IS NOT NULL`
- `bot_type IS NULL`, wash/bot suspect = 0

Used for:
- geo_elo tier accuracy validation
- STR-003 signal qualification
- Out-of-sample geopolitics prediction validation

Current size: Query live — `SELECT COUNT(*) FROM traders WHERE geo_accuracy_pool = 1`
Updated by: `update_research_exclusions.py`

---

## Section 6c — Open Data Quality Issues (known, mitigated)

### Architecture Rule: trades.market_category

> **`trades.market_category` is a STALE SNAPSHOT from ingestion time. `markets.category` is the AUTHORITATIVE current categorisation.**
>
> `sync_trade_categories.py --incremental` runs daily as Step 0b (non-blocking) to keep `trades.market_category` in sync with `markets.category`. A full sync completed 2026-06-10 corrected 176,748 mismatches (+145,092 geo trades gained, -31,479 lost, net +113,613), restoring Pool C from 402 to 2,835.
>
> **Never use `trades.market_category` as authoritative.** Always join to `markets.category` for any category-based filtering. New markets still enter with `category = 'Unknown'` in the markets table until manually reclassified — the daily sync propagates whatever value is in `markets.category`, so if a market is Unknown there it will be Unknown in trades too.

| Issue | Affected rows | Cause | Mitigation |
|-------|--------------|-------|------------|
| `trades.market_category = 'Unknown'` historically | ~81% of trades | Denormalized column not kept in sync with markets.category since ingestion | Step 0b sync_trade_categories.py runs daily. Use `markets.category` via JOIN for authoritative values. STR-003 concurrent market count uses `markets.category`. |

### Architecture Rule: trade_result field

> **`trade_result` values are strings: `'won'`, `'lost'`, `'pending'` — NEVER integers 0/1.**
>
> Any query filtering on trade outcomes must use string comparison, not integer. Using `trade_result = 1` or `trade_result = 0` will silently return zero rows — no error is raised.

### Bot Exclusion History (resolved — documented for context)

| Date | Bot type | Address | Count | Action |
|------|----------|---------|-------|--------|
| 2026-05-05 | `LP_ARTIFACT` | (multiple) | ~257 | Flagged via single-market position heuristic (>1000 positions, <3 distinct markets). `research_excluded=1`, ELO recalculated. |
| 2026-05-06 | `ARB_BOT` | (multiple) | 111 | Coordinated arbitrage wallets with ELO 3308–3315 cluster (Nov 2025 geopolitics). `research_excluded=1`, ELO recalculated. |
| 2026-06-10 | `single_market_concentration` | 0x44a1159b | 1 | `research_excluded=1` — 60 trades all in 1 market. |
| 2026-06-10 | `LP_ARTIFACT` | 0xf0d3c90f | 1 | Two-sided market maker, geo_directionality_score=0.529. `bot_type=LP_ARTIFACT`. |

Pool after 2026-05-06 exclusions: **493 traders** (down from 857 on 2026-04-30). Pool has since grown substantially as new traders accumulate resolved trades — read live from `brain/integration-health.json`.

**Legendary tier impact (2026-05-06):** 384 → 151 legendary traders (comprehensive_elo > 2175) after ARB_BOT removal. The 3308–3315 cluster was the primary driver of the previous legendary count. Remaining 151 are legitimate.

---

## Section 7 — Daily Maintenance Schedule

Agents should not query the database during the maintenance window
(06:00–06:30 UTC) to avoid read contention during writes.

The actual step order is defined in `first-repo/scripts/daily_maintenance.py`.
Steps marked **(non-blocking)** log a WARNING on failure and continue; steps marked **(blocking)** abort maintenance on failure.

```
06:00 UTC daily (19 steps):
  Step  0:  update_research_exclusions.py          [blocking]  — refreshes research pool
  Step  0b: sync_trade_categories.py --incremental [non-blocking]  — syncs trades.market_category from markets.category (NEW Session #30)
  Step  1:  promote_high_pnl_traders.py            [non-blocking]  — updates accuracy_pool flags
  Step  2:  resolution_sweep.py --days 7           [non-blocking]  — broad market resolution sweep
  Step  3:  update_geo_elo.py                      [non-blocking]  — updates geo_elo_active scores
  Step  4:  score_insider_signals.py               [non-blocking]  — scores insider_signals records
  Step  5:  score_str003_signals.py                [non-blocking]  — scores open STR-003 signals
  Step  6:  backfill_transaction_hashes.py --tier pool_c [non-blocking]  — fills tx hashes for Pool C trades
  Step  7:  polygon_maker_taker.py --backfill --limit 500 [non-blocking]  — labels maker/taker roles
  Step  8:  verify_market_titles.py                [non-blocking]  — verifies and updates market titles only — does NOT backfill categories
  Step  9:  fast_resolution_check.py               [blocking]  — marks newly resolved markets (50K ceiling)
  Step 10:  evaluate_new_trader_results.py         [non-blocking]  — evaluates recently resolved trader positions
  Step 10c: hydrate_stub_markets.py --limit 200    [non-blocking]  — populates positions data for stub markets (NEW Session #27)
  Step 11:  requeue_resolved_market_traders.py     [blocking]  — queues ELO recalculation for resolved markets
  Step 12:  apply_full_elo_modifiers.py            [blocking]  — applies ELO adjustments
  Step 13:  resolve_legendary_markets.py --limit 50 [non-blocking]  — resolves outstanding legendary markets (NEW Session #29)
  Step 14:  resync_position_counts.py              [blocking]  — syncs position counts
  Step 15:  write_integration_health.py            [blocking]  — writes brain/integration-health.json
  Step 16:  detect_arb_bots.py                     [non-blocking]  — detects arb bot patterns
  Step 19:  snapshot_elo_scores.py                 [non-blocking]  — appends daily ELO snapshot for all Pool C traders (NEW Session #31)
  Step 20:  snapshot_order_books.py                [non-blocking]  — captures CLOB order book depth + YES price for all active signal markets. Also fires at signal registration (snapshot_type='registration') via register_signal.py.
  Post:     WAL checkpoint (PASSIVE)               — clears accumulated WAL pages
  Post:     backfill_market_dates.py --geo-only --limit 500  — backfills end_date/resolution_date for geo markets

06:00 UTC Sundays only (appended to daily run):
  discover_leaderboard_traders.py  — scans top geo markets for new participants [non-blocking]
  Trade dedup                       — removes duplicate trade rows

03:00 UTC Sundays only (separate systemd timer: polymarket-sunday-elo.timer):
  recalculate_comprehensive_elo.py  — full ELO recalculation (expensive, separate timer)
```

> **Note:** `recalculate_comprehensive_elo.py` does NOT run inside `daily_maintenance.py`. It runs via a dedicated systemd timer (`polymarket-sunday-elo.timer`) at 03:00 UTC on Sundays to avoid contention with daily maintenance.
>
> **Daily backfill chain:** Step 0b sync_trade_categories → Step 9 fast_resolution_check (50K) → Step 10c hydrate_stub_markets (200/day) → Step 13 resolve_legendary_markets (50/day) → Post backfill_market_dates (500/day geo-only).

---

## Section 6d — Structural Break: April 28 2026

**All calibrations must be reported pre/post April 28 2026.**

April 28 2026 is a hard structural-break date for this system. Polymarket migrated to the V2 CLOB exchange, introduced pUSD collateral, launched publicly in the US (CFTC-regulated), and experienced a sharp-money influx. The platform that existed before April 28 is materially different from the one that exists after it.

Implications:
- Any accuracy calibration spanning this date is suspect — do not pool pre/post data without explicit regime adjustment
- 2025-H2 data (25% LEGENDARY accuracy on contested markets) reflects the old regime and should not be used for forward calibrations
- All RQ results should note whether their data window spans the break date
- The external parquet dataset (vgregoire/polymarket-users) covers V1/older data — treat as pre-break

This is not a data quality issue to be fixed — it is a permanent structural feature of the dataset.

## Section 8 — Change Log

### v2.9 — 2026-06-13

**Pool sizes (live DB query 2026-06-13):**
- clean_pool: 18,910 (research_excluded=0)
- true_research_pool: 3,837 (research_excluded=0, resolved_trades_count≥20, bot_type IS NULL)
- clean_markets: 24,184
- pool_c: 2,851 (geo_accuracy_pool=1) — was 2,848
- legendary_base: 48 (geo_elo≥2175, research_excluded=0)
- legendary_active: 25 (geo_elo_active≥2175, research_excluded=0)
- legendary_clean: 18 (geo_elo_active≥2175, geo_accuracy_pool=1, research_excluded=0, bot_type IS NULL)
- near_legendary_clean: 21 (geo_elo_active 1800–2174, geo_accuracy_pool=1, research_excluded=0, bot_type IS NULL)

**Structural changes:**
- Signal registration utility (register_signal.py) documented — Section 13 added
- Canonical 20-field signal schema formalised — market_price_at_registration and trader_archetypes_at_registration required fields
- Market-relative edge scoring defined: edge_at_entry formula, forward-only, null for legacy signals 001-009
- Order book capture infrastructure documented — Section 14 added (SCL-009: order_book_snapshots table, markets.clob_token_id_yes/no columns)
- Offsite backup infrastructure documented — Section 15 added (1TB USB /mnt/backup, 02:00 UTC daily)
- Provisional scoring rule added (Polymarket price >0.95 AND volume >$10M)
- Step 20 snapshot_order_books.py added to Section 7 maintenance schedule
- Section 9 expected ranges updated to live 2026-06-13 values

**Impact on agents:** Signal-agent must use register_signal.py — direct writes to signals.json prohibited. All agents reading Section 9 thresholds should update alert logic to 2026-06-13 values.

---

### v2.8 — 2026-06-11 (Session #31)

**Pool sizes (live DB query 2026-06-11):**
- clean_pool: 18,530 (research_excluded=0)
- true_research_pool: 3,796 (research_excluded=0, resolved_trades_count≥20, bot_type IS NULL)
- clean_markets: 23,569
- pool_c: 2,848 (geo_accuracy_pool=1)
- legendary_base: 31 (geo_elo≥2175, research_excluded=0)
- legendary_active: 16 (geo_elo_active≥2175, research_excluded=0)
- legendary_clean: 9 (geo_elo_active≥2175, geo_accuracy_pool=1, research_excluded=0, bot_type IS NULL)
- near_legendary_clean: 18 (geo_elo_active 1800–2174, geo_accuracy_pool=1, research_excluded=0, bot_type IS NULL)

**Structural changes:**
- Full contract rewrite top-to-bottom — all stale numbers replaced
- Section 7 updated to full 19-step maintenance schedule (Steps 0b, 10c, 13, 19 documented)
- Section 9 validation query extended: legendary_clean and near_legendary_clean added; expected ranges updated to live values
- Section 10.2 pool sizes updated to live values
- Section 10.3 trader-intelligence-agent output path added
- Section 11 added: Trader Archetypes (4 archetype definitions from Session #30 profiling)
- Section 12 added: Temporal State Layer (elo_snapshots table, snapshot_elo_scores.py)

**Architecture rules added (Section 6c, Section 10):**
- trades.market_category is a STALE SNAPSHOT — sync_trade_categories.py runs daily as Step 0b; always use markets.category via JOIN
- trade_result values are strings 'won'/'lost'/'pending' — never integers
- elo_snapshots table: append-only daily snapshots, PRIMARY KEY (snapshot_date, address)

**Fixes and exclusions:**
- manual_watchlist deadlock fixed: 14/17 traders unblocked, 612 trades scored (529W/83L)
- 0x44a1159b excluded: research_excluded=1, single_market_concentration (60 trades, 1 market)
- 0xf0d3c90f excluded: bot_type=LP_ARTIFACT (two-sided market maker, directionality=0.529)

**STR-003 signal update:**
- STR003-005 (Keiko Peru YES) scored RESOLVED_CORRECT 2026-06-11
- Scored accuracy: 1/4 (25%) — 1 correct (005), 3 wrong (003, 006, 009)
- Pre-registered research documented in Section 5 (RQ-POOL-QUALITY-001, RQ-EXT-001a/b/c, July 1 RQs)

**Impact on agents:** All agents — update alert thresholds to new pool sizes. STR-003 signal generation must respect archetype weights (Section 11). Snapshot-based temporal queries should use elo_snapshots table (Section 12).

---

### v2.7 — 2026-06-10 (Session #30)

**BREAKING — Pool size changes (update all agent alert thresholds)**
- Pool C: 402 → 2,835 (sync_trade_categories.py backfill corrected 176,748 mismatches)
- LEGENDARY active clean: 11 → 22 (post-recalc, post-exclusions)
- NEAR_LEGENDARY clean: 21 traders (geo_elo_active 1800–2174)
- ELITE clean: 1,394 traders (1400–1799, avg 20 trades — thin samples)

**New script: sync_trade_categories.py**
- Location: first-repo/scripts/sync_trade_categories.py
- Purpose: syncs trades.market_category from authoritative markets.category
- Daily maintenance: Step 0b (--incremental, non-blocking) — runs BEFORE update_geo_elo.py
- Full sync completed 2026-06-10: +145,092 geo trades gained, -31,479 lost, net +113,613
- Run --full-sync manually after any large Polymarket category reclassification event

**Architecture rule (propagate to all agents):**
trades.market_category is a STALE SNAPSHOT from ingestion time.
markets.category is the AUTHORITATIVE current categorisation.
sync_trade_categories.py --incremental runs daily (Step 0b) to keep these in sync.
Never use trades.market_category as authoritative without confirming sync is current.

**New infrastructure: trader profile store**
- Location: trading-swarm/brain/trader-profiles/{full_address}.json (37 profiles)
- Index: brain/trader-profiles/_index.json
- Schema: archetype, tier, signal_weight, domain_strengths, domain_blindspots, trusted_domains, discounted_domains, behavioural_flags, notable_calls, watch_items
- Generation script: trading-swarm/scripts/run_trader_profiling.py (Sonnet, API)
- Weekly maintenance: trader-intelligence-agent (Monday 07:15 UTC)

**New agent: trader-intelligence-agent**
- Template: orchestrator/task_templates/trader-intelligence-agent.md (679 lines, Fable 5)
- Cron wrapper: scripts/cron_wrappers/run_trader_intelligence.sh
- Schedule: Monday 07:15 UTC (between feedback-loop 07:00 and positions-scan 07:30)
- Tier: 3 (Sonnet)
- Purpose: delta detection, archetype drift, new trader discovery, position intelligence

**Trader archetype findings:**
From profiling 37 LEGENDARY + NEAR_LEGENDARY traders:
- GENUINE_FORECASTER: 4 — diverse markets, real directional calls, FULL weight
- DOMAIN_SPECIALIST: 13 — genuine edge in 1-2 domains (Russia_UKR dominant), DOMAIN_ONLY
- YIELD_HARVESTER: 17 — near-certainty positions, NOT forecasting, EXCLUDE
- VOLUME_SPECIALIST: 3 — single-theme ELO, narrow applicability
Raw ELO rank is a poor signal quality proxy. STR-003 must weight by archetype x domain.

**Trader exclusions:**
- 0x44a1159b: research_excluded=1, reason=single_market_concentration
- 0xf0d3c90f: bot_type=LP_ARTIFACT (two-sided market maker, directionality=0.529)

**system_observer.py fixes:**
- Column corrected: t.geo_elo → t.geo_elo_active (canonical)
- Threshold corrected: >= 2500 → >= 2175 for LEGENDARY badge
- NEAR_LEGENDARY tier added: geo_elo_active 1800-2174, badge 🌟
- Query WHERE extended to capture Pool C traders with comprehensive_elo < 2000

**Pre-registered research:**
- RQ-POOL-QUALITY-001: LEGENDARY pool quality filter (minimum market diversity). Filed: brain/strategy-notes/RQ-POOL-QUALITY-001.md. Implement: July 1 2026

**STR-003 signal scoring:**
- STR003-006 (López Aliaga YES): WRONG — resolved_at 2026-06-04
- STR003-009 (Graham SC NO): WRONG — Graham won 59.1%, resolved_at 2026-06-09
- STR003-005 (Keiko Peru YES): PENDING at close of session (scored CORRECT 2026-06-11)

**Market backfill hygiene (confirmed functioning):**
Daily chain: Step 0b sync_trade_categories → Step 9 fast_resolution_check (50K) →
Step 10c hydrate_stub_markets (200/day, ~3338 remaining) → Step 13 resolve_legendary_markets
(50/day) → Post backfill_market_dates (500/day geo-only)

---

### Historical changelog (v1.0 – v2.6)

| Date | Change | Impact on agents |
|------|--------|-----------------|
| 2026-04-30 | Research pool corrected to 857 traders | All queries using `research_excluded = 0` |
| 2026-04-30 | `trade_gap_flag` filter added to ELO queries | All ELO-based queries |
| 2026-04-30 | Analysis modules fixed (were returning 1.0x neutral multiplier) | ELO modifier accuracy |
| 2026-05-05 | `resync_position_counts.py` added as Step 13 of daily maintenance | Position count data |
| 2026-05-05 | This contract created | All agents querying first-repo |
| 2026-05-05 | Position dedup fix: 38,630 BST/UTC duplicate rows removed. Totals: 73,910 open, 952,900 closed | Position-derived P&L and ELO queries |
| 2026-05-05 | `traders.total_pnl` now written by monitor.py (was always 0). Use `realized_pnl` for P&L — it is authoritative | Any query on `total_pnl` |
| 2026-05-05 | LP artifact contamination identified (~257 traders). `bot_type=LP_ARTIFACT`, `research_excluded=1`, ELO recalculated | ELO distribution queries |
| 2026-05-06 | ARB_BOT exclusion: 111 coordinated arb wallets (ELO 3308–3315 cluster) excluded. Pool 857 → 493. Legendary tier 384 → 151 | All ELO-tier queries; legendary signal thresholds |
| 2026-05-07 | Contract updated to v1.1: pool size, alert threshold, bot_type list, Section 6c resolved | All agents |
| 2026-05-14 | Pool size removed from contract — now read live from integration-health.json. Alert threshold lowered to 440. | All agents reading pool size |
| 2026-05-20 | **Critical JOIN key correction (v1.3):** `m.market_id = t.market_id` is the correct join (99.999% match, 3,541,160/3,541,160 trades). Previous contract specified `m.condition_id = t.market_id` — this only matches 63% of trades. `condition_id` is a Polymarket external API identifier, NOT a join key. Warning added to Section 2; Section 6 row corrected. | All agents — update any query using the old join immediately |
| 2026-05-25 | Contract updated to v1.5: Pool A/B/C documented in Section 6b; traders column table added to Section 3 (includes geo_elo, geo_resolved_trades_count, geo_directionality_score, geo_accuracy_pool); geo_accuracy_pool column added to first-repo DB; STR-003 updated to use geo_elo >= 2175 + geo_directionality_score >= 0.7. Pool C size: 435 traders. | All agents querying geo ELO or geopolitics markets |
| 2026-05-29 | Contract updated to v1.6: STR-003 gains `realized_pnl > 500` filter in Section 5. Two LP artifact patterns identified: (1) geo_elo >= 2175 traders with realized_pnl = $0.00 exactly (redemption accounts, not directional), (2) geo_elo >= 2175 traders with realized_pnl < -$100,000 (spread-compression LPs — high ELO from volume not skill). | All agents generating STR-003 signals |
| 2026-05-29 | Contract updated to v1.7: STR-003 concurrent market count exclusion policy documented in Section 5 — stale unresolved markets (resolved=0, resolution_date older than 180 days) and non-Geo/Elections markets excluded from portfolio count. Decision: Oscar, 2026-05-29. | All agents generating STR-003 signals |
| 2026-06-02 | geo_elo_active column added — recency-weighted geo_elo for STR-003 qualification. Formula: geo_elo × 0.5^(days_dormant/180). Does not replace base geo_elo. Updated daily by update_geo_elo.py. Contract version v1.8. | STR-003 signal qualification now uses geo_elo_active >= 2175 |
| 2026-06-02 | Contract updated to v1.9 (full audit). Section 3: geo_elo_oos column added to traders table; Pool C hardcode removed (query live). Section 4: geo_elo_active tier note added for STR-003. Section 5: STR-003 qualification now explicitly references geo_elo_active >= 2175; LH-001 (CONDITIONAL_PASS) and STR-004 (HYPOTHESIS) added. Section 6c: market_category Unknown issue documented (81% of trades, backfill in progress). Section 7: full step list updated to match actual daily_maintenance.py (15 daily steps + Sunday extras); recalculate_comprehensive_elo.py correctly noted as separate systemd timer. Section 9: expected ranges updated to reflect current pool sizes. | All agents |
| 2026-06-05 | Contract v2.0: Pool B contamination warning added. 13K+ leaderboard traders with <20 resolved trades correctly included in Pool B by design but must be filtered explicitly in research queries. | All research queries — add `resolved_trades_count >= 20` explicitly |
| 2026-06-05 | v2.1: accuracy_pool and geo_elo_oos documented as dropped. Section 6c corrected — verify_market_titles.py does not backfill categories. Pool A removed. | All agents |
| 2026-06-06 | v2.2: Section 9 expected ranges updated to reflect post-audit pool sizes. Pool C 477 (was 272), LEGENDARY active 15 (was 13), clean markets 17,447. | All agents running startup validation |
| 2026-06-06 | v2.3: Section 10 added — Canonical Agent Definitions. Single source of truth for ELO thresholds, pool filters, output paths, STR-003 criteria, and known metric limitations. | All agents |
| 2026-06-06 | v2.4: Section 9 updated — 195 external_seed traders added from vgregoire/polymarket-users parquet. Three Tier 1 directional traders added via add_watched_trader.py (Nocthyra, Calythius, anonymous). /holders endpoint identified as superior discovery mechanism for resolved markets — Layer 3 implementation pending. | All agents running startup validation |
| 2026-06-08 | v2.5: Section 9 updated — Pool C temporarily 402 (down from ~477). geo_directionality_score recalculated from clean state; 809 traders with geo_elo have NULL directionality due to incomplete positions table coverage for newly hydrated markets. Pool C will recover and grow as hydrate_stub_markets.py pipeline populates positions data. LEGENDARY active 11 (down from 15, same cause). geo_legendary total (geo_elo >= 2175): 44. Three scoring pipeline blockers fixed for external_seed traders. calculate_geo_elo.py SCL-002 propagation fixed. | All agents running startup validation |
| 2026-06-09 | v2.6: legendary_positions_scan.py added. Weekly Monday 07:30 UTC cron. Covers all open geo/elections markets with LEGENDARY trader positions, regardless of resolution date. Filters: stale prices excluded, overdue markets excluded (>7 day grace). Training-librarian Responsibility 9 added. | All agents |

---

## Section 9 — Validation Query

Run this at agent startup to confirm the contract is satisfied before
executing any research queries. Alert if results are outside expected ranges.

```sql
SELECT
  (SELECT COUNT(*)
   FROM traders
   WHERE research_excluded = 0)                          AS clean_pool,

  (SELECT COUNT(*)
   FROM traders
   WHERE research_excluded = 0
     AND resolved_trades_count >= 20
     AND bot_type IS NULL)                               AS true_research_pool,

  (SELECT COUNT(*)
   FROM markets
   WHERE resolved = 1
     AND (trade_gap_flag = 0
          OR trade_gap_flag IS NULL))                    AS clean_markets,

  (SELECT COUNT(*)
   FROM traders
   WHERE geo_accuracy_pool = 1)                         AS pool_c,

  (SELECT COUNT(*)
   FROM traders
   WHERE geo_elo >= 2175
     AND research_excluded = 0)                         AS legendary_base,

  (SELECT COUNT(*)
   FROM traders
   WHERE geo_elo_active >= 2175
     AND research_excluded = 0)                         AS legendary_active,

  (SELECT COUNT(*)
   FROM traders
   WHERE geo_elo_active >= 2175
     AND geo_accuracy_pool = 1
     AND research_excluded = 0
     AND bot_type IS NULL)                              AS legendary_clean,

  (SELECT COUNT(*)
   FROM traders
   WHERE geo_elo_active BETWEEN 1800 AND 2174
     AND geo_accuracy_pool = 1
     AND research_excluded = 0
     AND bot_type IS NULL)                              AS near_legendary_clean,

  (SELECT journal_mode
   FROM pragma_journal_mode())                          AS wal_mode;
```

**Expected results (as of 2026-06-13):**

| Column | Expected | Alert if |
|--------|----------|----------|
| `clean_pool` | ≈ 18,910 | < 15,000 |
| `true_research_pool` | ≈ 3,837 | < 3,000 |
| `clean_markets` | ≈ 24,184 | < 20,000 |
| `pool_c` | ≈ 2,851 | < 2,500 |
| `legendary_base` | ≈ 48 | < 15 or > 200 |
| `legendary_active` | ≈ 25 | < 5 or > 100 |
| `legendary_clean` | ≈ 18 | < 5 |
| `near_legendary_clean` | ≈ 21 | < 5 |
| `wal_mode` | `wal` | ≠ `wal` |

If any alert condition is triggered, write a `contract_violation` signal
to `brain/signals.json` and halt — do not proceed with research queries
on a database that fails the contract check.

---

## Section 10 — Canonical Agent Definitions

> **CRITICAL:** All agent templates must use these definitions. Do not hardcode thresholds in templates — reference this section. When any value here changes, update ALL affected templates.

### 10.1 — ELO Tier Thresholds

| Tier | Metric | Threshold | Notes |
|------|--------|-----------|-------|
| LEGENDARY (geo) | `geo_elo_active` | >= 2175 AND `geo_accuracy_pool = 1` | **Primary metric.** Use for geopolitics/elections research and STR-003 signals. `geo_elo_active` is the recency-decayed field — not base `geo_elo`. |
| LEGENDARY (comprehensive) | `comprehensive_elo` | >= 2175 | No proven edge on contested markets (0.35-0.65). Do NOT use for signal generation. Use for bot detection and Pool B qualification only. |
| ELITE | `comprehensive_elo` | > 1800 | With `research_excluded = 0 AND bot_type IS NULL` |
| QUALIFIED | `comprehensive_elo` | > 1550 | With `research_excluded = 0 AND bot_type IS NULL` |

### 10.2 — Research Pool Filters

| Pool | Filter | Size (approx) | Use for |
|------|--------|---------------|---------|
| Pool B (research) | `research_excluded = 0 AND resolved_trades_count >= 20 AND bot_type IS NULL` | ≈ 3,837 | All accuracy calculations, ELO research |
| Pool C (geo) | `geo_accuracy_pool = 1` | ≈ 2,851 | geo_elo accuracy, STR-003 qualification |
| ⚠️ WARNING | `research_excluded = 0` alone | ≈ 18,910 | INSUFFICIENT — includes 13K+ leaderboard traders with <20 resolved trades |

### 10.3 — Agent Output Paths

| Agent | Primary output | Writes to findings.json? |
|-------|---------------|--------------------------|
| feedback-loop-agent | brain/agent-outputs/feedback-loop/ | YES — primary writer |
| performance-analyst-agent | brain/agent-outputs/performance-analyst/ | YES — can write |
| training-librarian-agent | brain/agent-outputs/training-librarian/ | YES — maintains/cleans |
| research-agent | brain/agent-outputs/research/ | NO — signals via signals.json (type: finding_ready) |
| quant-research-agent | brain/agent-outputs/quant-research/ | NO — siloed |
| research-scout-agent | brain/research-scout/ | NO — external reference only |
| signal-agent | brain/signals.json | NO — signal bus only |
| backtest-agent | brain/agent-outputs/backtest-agent/ | NO — strategy validation |
| legendary-positions-scan | brain/agent-outputs/positions-scan/ | NO — standalone research tool |
| trader-intelligence-agent | brain/agent-outputs/trader-intelligence/ | NO — writes brain/trader-profiles/{address}.json |

### 10.4 — STR-003 Qualification Criteria (authoritative)
```
geo_elo_active >= 2175
AND geo_directionality_score >= 0.7
AND realized_pnl != 0.0 AND realized_pnl > -100000
AND research_excluded = 0
AND entry_price BETWEEN 0.10 AND 0.80
AND market.category IN ('Geopolitics', 'Elections')
AND >= 95% of trader's capital on one side
AND archetype NOT IN ('YIELD_HARVESTER')    -- see Section 11
AND signal_weight != 'EXCLUDE'              -- see Section 11
```

### 10.5 — Known Metric Limitations

| Metric | Limitation | Impact |
|--------|-----------|--------|
| `comprehensive_elo` | 2.3x accumulation bias toward easy-market specialists | Do not use for signal generation on contested markets |
| `geo_elo_active` | legendary_clean = 18; near_legendary_clean = 21. Pool quality filter (RQ-POOL-QUALITY-001) pending July 1 to enforce min market diversity. | Validate pool quality before July 1 RQs run |
| `research_excluded = 0` alone | Includes 13K+ leaderboard traders with <20 resolved trades | Always add `AND resolved_trades_count >= 20` |
| `trades.market_category` | Stale snapshot from ingestion — daily sync keeps it current but use `markets.category` via JOIN for authoritative values | Always JOIN to markets table |
| `trade_result` | String field: 'won'/'lost'/'pending' — integer comparisons return zero rows silently | Use string literals only |

---

## Section 11 — Trader Archetypes

From profiling 37 LEGENDARY + NEAR_LEGENDARY traders (Session #30, 2026-06-10).
Profiles stored in `brain/trader-profiles/{address}.json` (37 files + `_index.json`).
Maintained weekly by trader-intelligence-agent (Monday 07:15 UTC).

**Raw ELO rank is a poor signal quality proxy. STR-003 must weight signals by archetype × domain.**

### Archetype Definitions

| Archetype | Count | Signal Weight | Description |
|-----------|-------|---------------|-------------|
| `GENUINE_FORECASTER` | 4 | **FULL** | Diverse markets, real directional calls across multiple domains. Highest quality signal source. |
| `DOMAIN_SPECIALIST` | 13 | **DOMAIN_ONLY** | Genuine edge in 1-2 specific domains (Russia/Ukraine dominant in current pool). Signal weight applies within trusted domains only — ignore signals outside those domains. |
| `YIELD_HARVESTER` | 17 | **EXCLUDE** | Takes near-certainty positions at 0.92–0.99 probability. Not forecasting — capturing residual yield. High ELO is a measurement artefact of near-certainty accuracy, not predictive skill. |
| `VOLUME_SPECIALIST` | 3 | **NARROW** | Single-theme high ELO with narrow applicability. Evaluate individually before including in any signal. |

### Signal Generation Rules

- **YIELD_HARVESTERs** must NEVER contribute to STR-003 signals. Their positions do not carry predictive information.
- **EXCLUDE-weight** traders must be filtered out before any signal aggregation step.
- **DOMAIN_SPECIALIST** signals are valid only in `trusted_domains` from their profile — consult `brain/trader-profiles/{address}.json` before including.
- **GENUINE_FORECASTERs** carry full weight across all qualifying markets.

### Archetype Field in trader-profiles

Each profile JSON includes:
```json
{
  "archetype": "DOMAIN_SPECIALIST",
  "signal_weight": "DOMAIN_ONLY",
  "trusted_domains": ["Russia_UKR", "Elections_LatAm"],
  "discounted_domains": ["Economics", "Science"],
  "behavioural_flags": []
}
```

The `signal_weight` field is the canonical gate for inclusion in STR-003. Always read the profile before including a LEGENDARY trader in a signal.

---

## Section 12 — Temporal State Layer

As of 2026-06-11, an immutable daily snapshot table exists for tracking ELO evolution over time.

### elo_snapshots Table

```
Table: elo_snapshots
Purpose: Append-only daily snapshots of all Pool C traders (geo_accuracy_pool=1)
Updated by: snapshot_elo_scores.py — Step 19 of daily_maintenance.py (non-blocking)
```

**Schema:**

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_date` | TEXT | ISO date string (YYYY-MM-DD) |
| `address` | TEXT | Trader wallet address |
| `geo_elo` | REAL | Base geo ELO at snapshot time |
| `geo_elo_active` | REAL | Recency-decayed geo ELO at snapshot time |
| `comprehensive_elo` | REAL | Comprehensive ELO at snapshot time |
| `geo_accuracy_pool` | INTEGER | Pool C membership flag (1/0) |
| `research_excluded` | INTEGER | Research exclusion flag (1/0) |
| `bot_type` | TEXT | Bot classification or NULL |
| `geo_resolved_trades_count` | INTEGER | Resolved geo trades at snapshot time |
| `geo_directionality_score` | REAL | Directionality score at snapshot time |
| `tier` | TEXT | LEGENDARY / NEAR_LEGENDARY / ELITE / etc. |
| `archetype` | TEXT | Trader archetype at snapshot time (from trader-profiles) |

**PRIMARY KEY:** `(snapshot_date, address)`

### Critical Rules

> **APPEND-ONLY — never UPDATE or DELETE existing rows.** The elo_snapshots table is a historical record. Any correction to a past snapshot must be documented in a decision record, not applied retroactively.
>
> **One row per trader per day.** snapshot_elo_scores.py is idempotent — running twice on the same day inserts once (INSERT OR IGNORE).

### Query Pattern for Temporal Analysis

```python
# Get ELO trajectory for a trader
cursor.execute("""
    SELECT snapshot_date, geo_elo_active, tier, archetype
    FROM elo_snapshots
    WHERE address = ?
    ORDER BY snapshot_date ASC
""", (address,))

# Get all LEGENDARY traders on a specific date
cursor.execute("""
    SELECT address, geo_elo_active, archetype
    FROM elo_snapshots
    WHERE snapshot_date = ?
      AND tier = 'LEGENDARY'
      AND research_excluded = 0
    ORDER BY geo_elo_active DESC
""", (target_date,))
```

### Use Cases

- Track individual trader ELO drift over weeks/months
- Audit which traders were LEGENDARY at signal registration time
- Validate that archetype classifications are stable vs. drifting
- Input for RQ1.1 (ELO in period T predicts Brier in T+1) — Phase 5 gate

---

## Section 13 — Signal Registration Protocol

All STR-003 signals MUST be registered via:

```bash
python3 /home/parison/projects/first-repo/scripts/register_signal.py
```

**Direct writes to signals.json are PROHIBITED.** They cause schema drift.

The utility atomically:
- Fetches `market_price_at_registration` from CLOB at exact registration moment
- Captures registration order-book snapshot (`snapshot_type='registration'`)
- Looks up trader `geo_elo_active` and `archetype` at registration (point-in-time)
- Computes `signal_credibility_score`
- Generates next sequential `signal_id`
- Validates 20-field canonical schema
- Writes atomically under file lock

### Canonical Signal Schema (20 required fields)

```
signal_id, strategy, status, market_id, market_title, direction, registered_at,
key_traders, trader_elos_at_registration, trader_archetypes_at_registration,
market_price_at_registration, event_cluster, correlated_with, legendary_count,
signal_credibility_score, signal_credibility_tier, outcome_correct, edge_at_entry,
resolved_at, scored_at, notes
```

**`market_price_at_registration`: MANDATORY.** Captured at registration moment only.
Capturing it later = hindsight contamination = `edge_at_entry` is meaningless.
Source: CLOB `/markets/{condition_id}` → `tokens[outcome='Yes'].price`

**`edge_at_entry`:** forward-only metric. Null for legacy signals (001-009) that predate
the registration utility. Computed at scoring time:
```
YES signal: edge = outcome_correct - market_price_at_registration
NO signal:  edge = outcome_correct - (1 - market_price_at_registration)
```
Positive edge = signal correctly identified underpriced side.
Near-zero edge = market already knew; signal adds no information.

**Provisional scoring rule:** A signal may be scored provisionally when Polymarket
price > 0.95 AND volume > $10M AND oracle resolution is delayed. Provisional scores
must be flagged `provisional: true` in signals.json and confirmed/revised at official
oracle resolution.

---

## Section 14 — Order Book Capture Infrastructure

```
Table: order_book_snapshots
Purpose: Historical CLOB book depth for Phase 6 paper trading fill simulation.
```

> **Book history CANNOT be backfilled — every missed day is permanently lost.**

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `market_id` | TEXT | Polymarket market_id |
| `snapshot_ts` | TEXT | ISO datetime of snapshot |
| `signal_id` | TEXT | Associated signal (NULL for daily snapshots) |
| `snapshot_type` | TEXT | `'registration'` or `'daily'` |
| `direction` | TEXT | YES or NO |
| `token_id` | TEXT | CLOB token ID for this side |
| `bids_json` | TEXT | JSON array of bid levels |
| `asks_json` | TEXT | JSON array of ask levels |
| `mid_price` | REAL | Arithmetic mean of best bid/ask |
| `spread` | REAL | Best ask − best bid |
| `bid_depth_10` | REAL | Total bid volume within 10 ticks |
| `ask_depth_10` | REAL | Total ask volume within 10 ticks |
| `clob_market_price_yes` | REAL | Authoritative YES price from CLOB `/markets/{condition_id}` |

**PRIMARY KEY:** `(market_id, snapshot_ts, direction)`

**`clob_market_price_yes`:** authoritative YES price from CLOB `/markets/{condition_id}`.
This is the correct price for market-relative calculations.

**`mid_price`:** arithmetic mean of best bid/ask. **UNRELIABLE for near-resolved markets**
where book is empty (bid=0.001, ask=0.999 gives mid=0.5 with no information).
Always use `clob_market_price_yes` for price-based analysis.

### markets Table Additions (SCL-009)

| Column | Type | Description |
|--------|------|-------------|
| `clob_token_id_yes` | TEXT | YES outcome token ID for CLOB book endpoint |
| `clob_token_id_no` | TEXT | NO outcome token ID for CLOB book endpoint |

Populated by: `scripts/backfill_clob_token_ids.py`

**Lookup:** CLOB `/markets/{condition_id}` primary (exact match).
Gamma `conditionIds` fallback with match verification — Gamma silently returns
unrelated markets for unrecognised IDs; always verify returned `conditionId` matches.

---



### 14b — Resolution Semantics (UMA Oracle)

Polymarket resolves via the UMA Optimistic Oracle, NOT by price. Critical distinction:

- **ended** (past end_date, price ~0.99): trading stopped or near-stopped, but NOT resolved.
  A market can sit in this state for hours (undisputed) to days (disputed: 24-48h debate +
  ~48h UMA vote).
- **resolved/finalized** (closed=true AND a token has winner=true): UMA has finalized.
  ONLY THIS state is authoritative for scoring.

SCORING RULE: Never infer resolution from price. A market at 0.99 is NOT resolved.
Score ONLY when CLOB /markets/{condition_id} returns closed=true AND a token has winner=true.
The winning token outcome (Yes/No) is the ground truth.

PROVISIONAL EXCEPTION (existing rule, Section 13): price>0.95 + vol>$10M may be scored
provisional:true and flagged, then confirmed/revised at oracle finalization. Used for Peru
STR003-005. This is the ONLY case where pre-finalization price informs a score, and it is
always explicitly flagged.

Resolution scripts (fast_resolution_check.py recent_overdue + stale passes) correctly check
closed AND winner token before marking resolved — they will NOT false-resolve an ended-but-
unfinalized market.

OPEN AUDIT ITEM: Historical synthetic-resolution closes (early system, pre-API-redemption-
events) used different logic. A retrospective audit comparing historical resolutions against
UMA winner outcomes is pending (separate session).



### API Authentication Note (audited 2026-06-14)
POLYMARKET_API_KEY is loaded from ~/.env_trading and sent as Bearer/X-API-Key headers
on Gamma API requests. Gamma is a public API and ignores these headers — zero auth
failures observed in monitoring logs. No action needed.

V3 migration (June 1, 2026): old V1/V2 keys for authenticated order placement are
dead. Our read stack (Gamma, CLOB, Data API) is entirely public/unauthenticated and
unaffected. V3 key requirement is a Phase 7 concern (order placement only).

Offset pagination in polymarket_client.py hits gamma-api.polymarket.com/markets —
Gamma's own endpoint, not Polymarket V3 REST API. Gamma offset pagination works.
Data API (data-api.polymarket.com/trades) also unaffected by V3 changes.

Audit conclusion: all read endpoints functioning correctly post-V3 migration.

## Section 15 — Backup Infrastructure

**Offsite backup:** 1TB USB drive mounted at `/mnt/backup`
(`LABEL=polymarket-backup`, ext4, added to `/etc/fstab` with `nofail` flag).

**Script:** `/home/parison/projects/first-repo/scripts/backup_offsite.sh`
**Schedule:** 02:00 UTC daily (crontab)

### What It Backs Up

| Item | Method | Destination |
|------|--------|-------------|
| `polymarket_tracker.db` | WAL checkpoint + gzip | `/mnt/backup/polymarket-backups/{date}/` |
| `brain/` | incremental rsync (`--delete`) | `/mnt/backup/polymarket-backups/brain-latest/` |

**Retention:** 14 days of DB snapshots. Brain is always current (rsync --delete).
**Log:** `/home/parison/trading-swarm/logs/backup_offsite.log`

> **The DB and elo_snapshots history are IRREPLACEABLE.** The external parquet dataset
> covers only V1/older data. Gamma backfill has known caps. If the DB is lost, years
> of trade history and all temporal snapshots are gone permanently.
