# Integration Contract — first-repo ↔ trading-swarm

**Version:** 1.0 — 2026-05-05
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
JOIN markets m ON m.condition_id = t.market_id   -- NOT m.market_id
WHERE tr.research_excluded = 0
  AND t.timestamp <= datetime('now')
  AND m.resolved = 1
  AND m.winning_outcome NOT IN ('unknown', '')
  AND m.winning_outcome IS NOT NULL
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
```

**Why each filter exists:**

| Filter | Reason |
|--------|--------|
| `m.condition_id = t.market_id` | `trades.market_id` stores the condition_id, NOT the market's primary key. Using `m.market_id` returns wrong or no rows — this is the single most common silent bug. |
| `tr.research_excluded = 0` | Excludes bots, wash traders, and thin-sample traders. Including them inflates signal counts and corrupts ELO accuracy metrics. |
| `t.timestamp <= datetime('now')` | 37 future-dated trades exist in the DB from a data import error. They have not resolved yet and pollute forward-looking calculations. |
| `m.resolved = 1` | Only resolved markets have ground truth outcomes. Unresolved markets have no winning_outcome to validate against. |
| `m.winning_outcome NOT IN ('unknown', '')` | 497 markets resolved with outcome='unknown' (no clear resolution). Including them produces Brier score errors and false accuracy signals. |
| `m.winning_outcome IS NOT NULL` | Belt-and-suspenders for NULL entries missed by the NOT IN filter. |
| `m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL` | 166 markets have trade_gap_flag=1 from the April 7-18 server migration. Trades during that window are missing, making position data incomplete for those markets. |

---

## Section 3 — Research Pool

**Current clean pool: 857 traders** (as of 2026-04-30)

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

**Never use** traders tagged with `bot_type IN ('LP_ARTIFACT', 'THIN_SAMPLE_ARTIFACT')`.
These are artefacts of liquidity provision and data sparsity — their ELO
scores are not predictive.

---

## Section 5 — Active Strategies

| Strategy | Status | Notes |
|----------|--------|-------|
| STR-001 | SUSPENDED | LP contamination — liquidity provider trades inflate signal counts |
| STR-001b | SUSPENDED | 0 qualifying signals after STR-001 fix |
| STR-002 | EXPERIMENTAL | Accumulating pre-resolution accuracy data (n=4 as of 2026-05-05) |
| STR-003 | PENDING_REVIEW | Primary strategy: single legendary trader ≥95% directional, min $2,000 stake, max 2 concurrent markets, bidirectional holders excluded |

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
| `trades.market_id` stores condition_id | All rows | Schema design | Join: `m.condition_id = t.market_id` |

---

## Section 6b — Resolved Data Quality Issues (fixed, documented for context)

| Issue | Resolved | Detail |
|-------|----------|--------|
| Position duplication — BST/UTC timezone mismatch | 2026-05-05 | April 18-20 server migration imported positions twice due to 1-hour BST/UTC offset. 38,630 duplicate rows removed. Post-cleanup totals: 1,026,810 positions total, 73,910 open, 952,900 closed. Dedup guard now in place. |
| `traders.total_pnl` never written | 2026-05-05 | Column existed but the monitor.py UPDATE only wrote `realized_pnl`. Fixed: `total_pnl` now set to `realized_pnl` in every P&L update (unrealized_pnl is a permanent placeholder at 0.0). **Use `realized_pnl` for all P&L queries — it is the authoritative column.** |

---

## Section 6c — Open Data Quality Issues (known, no fix yet applied)

### LP Artifact Contamination in Research Pool (⚠ action needed)

The research pool (`research_excluded = 0`) contains ~267 LP artifact traders that were
NOT caught by existing bot detection. These traders have:

- Thousands of positions (6,000–6,600+) on a single market
- `bot_suspect = 0`, `bot_type = NULL` — not flagged
- Massive negative realized_pnl (−$1.2B to −$1.4B per trader) from LP interactions
- `pnl_modifier = 0.4` (floor), pulling their comprehensive_elo to the floor ~447

**Affected markets (high-volume LP markets in positions table):**
- "Will Iran recognize Iran by June 2025?" — 619,196 positions / 182 traders
- "USA ceasefire agreement before December 2025?" — ~60,000 positions / 30 traders
- "Will Haley drop out of 2027 race before January?" — ~48,000 positions / 44 traders

**ELO impact:** The bimodal distribution (267 traders at ELO 400–600) is this LP contamination,
not genuine underperformers. Top ELO traders (3200–3471) are legitimate: 6–15 distinct markets,
120–187 total positions.

**Fix pending Oscar approval:**
```sql
-- Flag single-market LP artifact traders (> 1000 positions, < 3 distinct markets)
UPDATE traders
SET research_excluded = 1,
    bot_type = 'LP_ARTIFACT'
WHERE address IN (
    SELECT trader_address
    FROM positions
    GROUP BY trader_address
    HAVING COUNT(*) > 1000 AND COUNT(DISTINCT market_id) < 3
)
AND research_excluded = 0;
```
After applying: re-run `recalculate_comprehensive_elo.py` to clean up the ELO distribution.

### ELO Recalculation Needed Post-Dedup

ELO was last recalculated at 2026-05-05T13:54 UTC. The position dedup fix was applied at
2026-05-05T19:29 UTC. The current ELO scores reflect the pre-dedup positions table.
Impact is limited to traders active during April 18–20 migration window, but a full
recalculation should run before the next Sunday scheduled recalc (or manually via
`python scripts/recalculate_comprehensive_elo.py`).

---

## Section 7 — Daily Maintenance Schedule

Agents should not query the database during the maintenance window
(06:00–06:30 UTC) to avoid read contention during writes.

```
06:00 UTC daily:
  Step 0: update_research_exclusions.py     — refreshes research pool
  Step 1: fast_resolution_check.py          — marks newly resolved markets
  Step 2: requeue_resolved_market_traders.py — queues ELO recalculation
  Step 3: apply_full_elo_modifiers.py        — applies ELO adjustments
  Step 4: resync_position_counts.py          — syncs position counts (added 2026-05-05)

06:00 UTC Sundays only:
  Step 5: recalculate_comprehensive_elo.py   — full ELO recalculation (expensive)
```

---

## Section 8 — Change Log

| Date | Change | Impact on agents |
|------|--------|-----------------|
| 2026-04-30 | Research pool corrected to 857 traders | All queries using `research_excluded = 0` |
| 2026-04-30 | `trade_gap_flag` filter added to ELO queries | All ELO-based queries |
| 2026-04-30 | Analysis modules fixed (were returning 1.0x neutral multiplier) | ELO modifier accuracy |
| 2026-05-05 | `resync_position_counts.py` added as Step 4 of daily maintenance | Position count data |
| 2026-05-05 | This contract created | All agents querying first-repo |
| 2026-05-05 | Position dedup fix: 38,630 BST/UTC duplicate rows removed. Totals: 73,910 open, 952,900 closed | Position-derived P&L and ELO queries |
| 2026-05-05 | `traders.total_pnl` now written by monitor.py (was always 0). Use `realized_pnl` for P&L — it is authoritative | Any query on `total_pnl` |
| 2026-05-05 | LP artifact contamination identified in research pool (~267 traders). ELO bimodal distribution is this artifact, not real underperformers. Pending fix (see Section 6c) | ELO distribution queries |

---

## Section 9 — Validation Query

Run this at agent startup to confirm the contract is satisfied before
executing any research queries. Alert if results are outside expected ranges.

```sql
SELECT
  (SELECT COUNT(*)
   FROM traders
   WHERE research_excluded = 0)            AS clean_pool,

  (SELECT COUNT(*)
   FROM markets
   WHERE resolved = 1
     AND (trade_gap_flag = 0
          OR trade_gap_flag IS NULL))      AS clean_markets,

  (SELECT journal_mode
   FROM pragma_journal_mode())             AS wal_mode;
```

**Expected results:**

| Column | Expected | Alert if |
|--------|----------|----------|
| `clean_pool` | 857–1100 | < 800 (pool shrank unexpectedly) |
| `clean_markets` | ≥ 11,491 | < 11000 (markets missing) |
| `wal_mode` | `wal` | ≠ `wal` (WAL disabled — risk of read contention) |

If any alert condition is triggered, write a `contract_violation` signal
to `brain/signals.json` and halt — do not proceed with research queries
on a database that fails the contract check.
