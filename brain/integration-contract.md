# Integration Contract — first-repo ↔ trading-swarm

**Version:** v2.6 — 2026-06-09
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

**Current clean pool:** See `brain/integration-health.json` (updated daily at 06:00 UTC by write_integration_health.py). Never hardcode this number — always read it live.

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

| Tier | Field | Threshold |
|------|-------|-----------|
| Legendary | `comprehensive_elo` | > 2175 |
| Elite | `comprehensive_elo` | > 1800 |
| Strong | `comprehensive_elo` | > 1550 |

**Always pair tier filters with the research exclusion filter:**

```sql
WHERE comprehensive_elo > 1800
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

STR-003 signal qualification uses `geo_elo_active >= 2175` (not `geo_elo >= 2175` and not `comprehensive_elo >= 2175`). `geo_elo_active` is the recency-decayed version of `geo_elo` — it down-weights traders who have been dormant for 6+ months so that stale high ELO scores do not generate signals. See Section 3 for formula.

---

## Section 5 — Active Strategies

| Strategy | Status | Notes |
|----------|--------|-------|
| LH-001 | CONDITIONAL_PASS | Lifecycle heuristic insider detection. Watchlist trigger only — not a trading signal. Pooled p=0.0160, r=0.208. Blocking items remain before PASS upgrade (see strategy-registry.md). |
| STR-001 | SUSPENDED | LP contamination — liquidity provider trades inflate signal counts |
| STR-001b | SUSPENDED | 0 qualifying signals after STR-001 fix |
| STR-002 | EXPERIMENTAL | Accumulating pre-resolution accuracy data (n=4 as of 2026-05-05) |
| STR-003 | EXPERIMENTAL | Primary strategy: single legendary geo trader (`geo_elo_active >= 2175`, `geo_directionality_score >= 0.7`, `realized_pnl != 0.0 AND realized_pnl > -100000`, `research_excluded = 0`, signal trade price BETWEEN 0.10 AND 0.80) with ≥95% of capital on one side. Max 5 concurrent GEOPOLITICS/ELECTIONS markets (not platform-wide). Bidirectional holders excluded. P&L filter: realized_pnl != 0.0 AND realized_pnl > -100000 — removes exact-zero redemption accounts and spread-compression LPs (< -$100K). Does not exclude legitimate directional traders with modest or negative P&L from correct directional losses. |
| STR-004 | HYPOTHESIS | Capital-weighted legendary aggregate signal: when capital-weighted aggregate of legendary traders diverges from market price by ≥20pp, fires as signal. Pre-registered 2026-05-08. Founding case resolved NO (n=1). Needs 9 more resolved signals. |

**STR-003 — Concurrent Market Count Exclusions (added v1.7, 2026-05-29):**

Concurrent market count excludes:
- Markets where `resolved = 0 AND resolution_date < datetime('now', '-180 days')`
  (unresolved for 6+ months — template/stale markets)
- Markets where `markets.category NOT IN ('Geopolitics','Elections')`

> **Note:** Category filtering uses `markets.category` (the markets table column), NOT `trades.market_category` (the denormalized column in the trades table). These are distinct fields. The trades table's `market_category` is 81% 'Unknown' due to a data quality issue — see Section 6c. Always join to the markets table to get the authoritative category.

Rationale: Stale unresolved markets contain no actionable information.
A trader holding a 2025 template position is not actively trading that market.
Decision: Oscar, 2026-05-29.

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

## Section 6c — Open Data Quality Issues (known, no fix yet applied)

| Issue | Affected rows | Cause | Mitigation |
|-------|--------------|-------|------------|
| `trades.market_category = 'Unknown'` | ~81% of trades (≈4.5M / 5.5M) | The `market_category` column in the trades table is denormalized from the market record at insert time. Most markets have `category = 'Unknown'` in the markets table because category backfill from the Gamma API is incomplete. | Use `markets.category` via JOIN for any category-based filtering (NOT `trades.market_category`). STR-003 concurrent market count uses `markets.category` as authoritative. The one-time category backfill was performed by backfill_market_categories.py (run 2026-06-03, classified 11,001 Unknown markets). verify_market_titles.py runs daily but only verifies/updates titles — it does NOT perform category backfill. No ongoing automated category backfill exists; new markets enter with Unknown category until manually reclassified. |

### Bot Exclusion History (resolved — documented for context)

| Date | Bot type | Count | Action |
|------|----------|-------|--------|
| 2026-05-05 | `LP_ARTIFACT` | ~257 | Flagged via single-market position heuristic (>1000 positions, <3 distinct markets). `research_excluded=1`, ELO recalculated. |
| 2026-05-06 | `ARB_BOT` | 111 | Coordinated arbitrage wallets with ELO 3308–3315 cluster (Nov 2025 geopolitics). `research_excluded=1`, ELO recalculated. |

Pool after both exclusions: **493 traders** (down from 857 on 2026-04-30). Pool has since grown substantially as new traders accumulate resolved trades — read live from `brain/integration-health.json`.

**Legendary tier impact:** 384 → 151 legendary traders (ELO > 2175) after ARB_BOT removal. The 3308–3315 cluster was the primary driver of the previous legendary count. Remaining 151 are legitimate.

---

## Section 7 — Daily Maintenance Schedule

Agents should not query the database during the maintenance window
(06:00–06:30 UTC) to avoid read contention during writes.

The actual step order is defined in `first-repo/scripts/daily_maintenance.py`.
Steps marked **(non-blocking)** log a WARNING on failure and continue; steps marked **(blocking)** abort maintenance on failure.

```
06:00 UTC daily:
  Step  0: update_research_exclusions.py       — refreshes research pool [blocking]
  Step  1: promote_high_pnl_traders.py         — updates accuracy_pool flags [non-blocking]
  Step  2: resolution_sweep.py                 — broad market resolution sweep [non-blocking]
  Step  3: update_geo_elo.py                   — updates geo_elo_active scores [non-blocking]
  Step  4: score_insider_signals.py            — scores insider_signals records [non-blocking]
  Step  5: score_str003_signals.py             — scores open STR-003 signals [non-blocking]
  Step  6: backfill_transaction_hashes.py      — fills tx hashes for Pool C trades [non-blocking]
  Step  7: polygon_maker_taker.py              — labels maker/taker roles [non-blocking]
  Step  8: verify_market_titles.py             — verifies and updates market titles only — category backfill is not automated [non-blocking]
  Step  9: fast_resolution_check.py            — marks newly resolved markets [blocking]
  Step 10: evaluate_new_trader_results.py      — evaluates recently resolved trader positions [non-blocking]
  Step 11: requeue_resolved_market_traders.py  — queues ELO recalculation for resolved markets [blocking]
  Step 12: apply_full_elo_modifiers.py         — applies ELO adjustments [blocking]
  Step 13: resync_position_counts.py           — syncs position counts [blocking]
  Step 14: write_integration_health.py         — writes brain/integration-health.json [blocking]
  Post:    WAL checkpoint (PASSIVE)            — clears accumulated WAL pages
  Post:    backfill_market_dates.py            — backfills end_date/resolution_date for geo markets [non-blocking]

06:00 UTC Sundays only (appended to daily run):
  Step 15: discover_leaderboard_traders.py     — scans top geo markets for new participants [non-blocking]
  Post:    Trade dedup                         — removes duplicate trade rows

03:00 UTC Sundays only (separate systemd timer: polymarket-sunday-elo.timer):
  recalculate_comprehensive_elo.py             — full ELO recalculation (expensive, separate timer)
```

> **Note:** `recalculate_comprehensive_elo.py` does NOT run inside `daily_maintenance.py`. It runs via a dedicated systemd timer (`polymarket-sunday-elo.timer`) at 03:00 UTC on Sundays to avoid contention with daily maintenance.

---

## Section 10 — Canonical Agent Definitions

> **CRITICAL:** All agent templates must use these definitions. Do not hardcode thresholds in templates — reference this section. When any value here changes, update ALL affected templates.

### 10.1 — ELO Tier Thresholds

| Tier | Metric | Threshold | Notes |
|------|--------|-----------|-------|
| LEGENDARY (geo) | `geo_elo` | >= 2175 AND `geo_accuracy_pool = 1` | Use for geopolitics/elections research and STR-003 signals. Primary accuracy metric. |
| LEGENDARY (comprehensive) | `comprehensive_elo` | >= 2175 | No proven edge on contested markets (0.35-0.65). Do NOT use for signal generation. Use for bot detection and Pool B qualification only. |
| ELITE | `comprehensive_elo` | > 1800 | With `research_excluded = 0 AND bot_type IS NULL` |
| QUALIFIED | `comprehensive_elo` | > 1550 | With `research_excluded = 0 AND bot_type IS NULL` |

### 10.2 — Research Pool Filters

| Pool | Filter | Size (approx) | Use for |
|------|--------|---------------|---------|
| Pool B (research) | `research_excluded = 0 AND resolved_trades_count >= 20 AND bot_type IS NULL` | ~1,712 | All accuracy calculations, ELO research |
| Pool C (geo) | `geo_accuracy_pool = 1` | ~402 (recovering — see Section 9 note) | geo_elo accuracy, STR-003 qualification |
| ⚠️ WARNING | `research_excluded = 0` alone | ~15,083 | INSUFFICIENT — includes 13K+ leaderboard traders with <20 resolved trades |

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

### 10.4 — STR-003 Qualification Criteria (authoritative)
```
geo_elo_active >= 2175
AND geo_directionality_score >= 0.7
AND realized_pnl != 0.0 AND realized_pnl > -100000
AND research_excluded = 0
AND entry_price BETWEEN 0.10 AND 0.80
AND market.category IN ('Geopolitics', 'Elections')
AND >= 95% of trader's capital on one side
```

### 10.5 — Known Metric Limitations

| Metric | Limitation | Impact |
|--------|-----------|--------|
| `comprehensive_elo` | 2.3x accumulation bias toward easy-market specialists | Do not use for signal generation on contested markets |
| `geo_elo` | Pool C temporarily 402 (down from 477) — 809 traders have NULL geo_directionality_score due to hydration gap; will recover as hydrate_stub_markets.py populates positions data | Validate July 1 per RQ-CONTESTED-001 |
| `research_excluded = 0` alone | Includes 13K+ leaderboard traders with <20 resolved trades | Always add `AND resolved_trades_count >= 20` |
| `trades.market_category` | 81% Unknown — denormalized field | Always use `markets.category` via JOIN |

---

## Section 8 — Change Log

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
| 2026-06-09 | v2.6: legendary_positions_scan.py added. Weekly Monday 07:30 UTC cron. Covers all open geo/elections markets with LEGENDARY trader positions, regardless of resolution date. Filters: stale prices excluded, overdue markets excluded (>7 day grace). Training-librarian Responsibility 9 added. |
| 2026-06-08 | v2.5: Section 9 updated — Pool C temporarily 402 (down from ~477). geo_directionality_score recalculated from clean state; 809 traders with geo_elo have NULL directionality due to incomplete positions table coverage for newly hydrated markets. Pool C will recover and grow as hydrate_stub_markets.py pipeline populates positions data. LEGENDARY active 11 (down from 15, same cause). geo_legendary total (geo_elo >= 2175): 44. Three scoring pipeline blockers fixed for external_seed traders. calculate_geo_elo.py SCL-002 propagation fixed. | All agents running startup validation |

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
     AND resolved_trades_count >= 20)                    AS true_research_pool,

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

  (SELECT journal_mode
   FROM pragma_journal_mode())                          AS wal_mode;
```

**Expected results (as of 2026-06-08):**

| Column | Expected | Alert if |
|--------|----------|----------|
| `clean_pool` | ≈ 15,083 (grows daily as traders qualify). **2026-06-06: 195 traders added via external_seed (vgregoire/polymarket-users parquet). These are directional politics specialists with pnl_taker_politics > $10K, frac_both_sides < 0.25, frac_maker < 0.3, frac_politics > 0.5, n_markets >= 15, last_trade >= 2025-06-01. Trade histories pending backfill. ELO scores will populate over next 24-48 hours.** | < 10,000 (unexpected shrinkage — check integration-health.json alerts array) |
| `true_research_pool` | ≈ 1,712 (research_excluded=0 AND resolved_trades_count>=20). **2026-06-06: 195 external_seed traders not yet counted here — trade histories pending backfill, resolved_trades_count will not reach ≥20 threshold until backfill completes.** | < 1,500 (unexpected shrinkage) |
| `clean_markets` | ≈ 17,447 (grows as markets resolve) | < 16,000 (markets missing) |
| `pool_c` | ≈ 402 (geo_accuracy_pool=1). **2026-06-08: temporarily reduced from ~477. geo_directionality_score was recalculated from a clean state on 2026-06-08; 809 traders with geo_elo have NULL directionality due to incomplete positions table coverage for newly hydrated markets. Pool C will recover and grow beyond 477 as hydrate_stub_markets.py pipeline populates positions data.** | < 350 (unexpected shrinkage beyond hydration shortfall) |
| `legendary_base` | ≈ 44 (geo_elo >= 2175, research_excluded=0) | < 30 or > 200 (tier contamination or mass exclusion) |
| `legendary_active` | ≈ 11 (geo_elo_active >= 2175, research_excluded=0). **2026-06-08: temporarily down from 15 — same cause as Pool C reduction. geo_directionality_score NULL for 809 traders due to hydration gap; affected traders' geo_elo_active will recover as positions data is populated.** | < 5 (too few for STR-003 signals) or > 100 (recency decay not applied) |
| `wal_mode` | `wal` | ≠ `wal` (WAL disabled — risk of read contention) |

If any alert condition is triggered, write a `contract_violation` signal
to `brain/signals.json` and halt — do not proceed with research queries
on a database that fails the contract check.
