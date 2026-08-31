# Classifier Provenance — Schema Migration (applied)

**Date:** 2026-08-31 ~18:37 UTC. **Type:** production schema change, applied.
**Design:** `2026-08-31-relevance-classifier-design.md` (e601648, as amended), §2.7.
**Migration artifact / revert tool:** `first-repo/scripts/migrate_add_category_source.py`
(idempotent; `--dry-run`, `--revert`). Modelled on
`first-repo/scripts/migrate_stage0_resolution_columns.py`.
**Tagging:** `[V]` verified this session.

---

## SUMMARY

Applied — one transaction (`BEGIN IMMEDIATE … COMMIT`, exit 0) against the live
18 GB `data/polymarket_tracker.db` with `busy_timeout=60000`; monitoring never
stopped (write window ~seconds):

1. **`ALTER TABLE markets ADD COLUMN category_source TEXT`** with a `CHECK` limiting it
   to `{'llm_relevance_v1','deterministic_slug_v1','gamma_event','legacy'}` or NULL —
   nullable, no default.
2. **`CREATE TABLE category_classification_log`** — 8 columns per §2.7, `PRIMARY KEY
   (market_id, run_id)`, append-only.
3. **Backfill** `category_source = 'legacy'` where `category IN
   ('Geopolitics','Elections')` — **11,967 rows updated / 11,967 expected**.

All seven verifications pass. No new test failure. `check_resolution_write_atomicity
= 0`. `trg_resolved_no_unresolve` intact, did not fire. Category distribution,
`resolved` counts, and `resolution_evidence_source` breakdown are byte-identical
before and after.

---

## SAFETY — backup (hard gate)

**Pre-checks `[V]`:**
- No backup running. The nightly `flock` lock file held only the string
  `2026-08-31T03:00:01Z` (last cron run's start stamp; that run finished 03:07 per
  `logs/backup.log`). The only live process on the lock was a sandbox artifact in
  `/tmp/tmp.*`, not a backup.
- Nothing heavy writing: no sweep segment, no `daily_maintenance`, no manual
  ELO/backfill job. Only `pnl_worker` (P&L recompute, ~1 small write / 15 s). Last
  new-market write `last_checked` was 15:23 and last new trade 16:35 — i.e. trade
  ingestion was already quiet hours before the migration.
- Disk: 1.2 TB free.
- `PRAGMA quick_check(3)` on the source → `ok`.

**Backup taken `[V]`:**
- Command: `python3 scripts/backup_database.py` — `sqlite3.Connection.backup()`
  (Online Backup API, WAL-safe), then `PRAGMA integrity_check`.
- File: **`first-repo/backups/markets_20260831_183602.db`**, 18,129.1 MB.
- sha256: `de621776b67ad8ede77cf5b5315874f5210818a027b9b7232ff573818fa35d49`
- Elapsed 18:36:02 → ~18:39:40 (~3.5 min). **No starvation.**
- Integrity verified **three ways**: (i) the script's own `PRAGMA integrity_check` →
  `ok` (it deletes the file and exits 1 otherwise); (ii) independent
  `PRAGMA quick_check(5)` → `ok`; (iii) independent detached full
  `PRAGMA integrity_check` → `ok`.
- Content fingerprint of the backup matches the live pre-state: `markets` 792,793 ·
  geo/elec 11,967 · `resolved=1` 438,612 · `evidence_source='clob'` 214,775 · no
  `category_source` column · no `category_classification_log`.

Backup was completed and integrity-verified **before** any schema statement ran.

---

## THE MIGRATION AS APPLIED

Executed via `sqlite3 data/polymarket_tracker.db ".read migration.sql"`, exit 0:

```sql
PRAGMA busy_timeout = 60000;
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- (1) provenance column. CHECK references only the new column, mirroring the
--     resolution_evidence_source precedent (also added via ALTER ADD COLUMN).
ALTER TABLE markets ADD COLUMN category_source TEXT
  CHECK (category_source IN
           ('llm_relevance_v1','deterministic_slug_v1','gamma_event','legacy')
         OR category_source IS NULL);

-- (2) append-only sidecar log. Types follow this DB's snapshot/log convention
--     (elo_snapshots / backtest_population_snapshots / event_cluster_labels):
--     identity + timestamp columns TEXT NOT NULL, composite PK, no CHECKs.
CREATE TABLE category_classification_log (
    market_id         TEXT NOT NULL,   -- markets.market_id (TEXT PK); no FK (rest of schema uses none)
    decided_category  TEXT NOT NULL,   -- 'Geopolitics' | 'Elections' | 'NotRelevant' (design §2.8 vocab)
    method            TEXT NOT NULL,   -- cascade stage: 'deterministic_slug_v1' | 'llm_relevance_v1'
    model_version     TEXT,            -- NULL for deterministic rows; e.g. 'qwen3-coder:30b-a3b-q4_K_M'
    confidence        TEXT,            -- 'HIGH'/'LOW' (M9 vocab) for LLM; NULL for deterministic
    inputs_hash       TEXT,            -- hex digest of 'title|market_slug|event_slug|event_title'
    run_id            TEXT NOT NULL,   -- batch id; part of PK so re-runs append, not collide
    classified_at     TEXT NOT NULL,   -- ISO8601 UTC string (snapshot-table convention)
    PRIMARY KEY (market_id, run_id)
);

-- (3) legacy backfill. SET touches category_source ONLY; 'resolved' is not in the
--     SET list, so trg_resolved_no_unresolve does not fire.
UPDATE markets
SET category_source = 'legacy'
WHERE category IN ('Geopolitics','Elections');

COMMIT;
```

### Type / constraint decisions

- **`category_source` — CHECK added.** The Stage-0 precedent
  (`resolution_evidence_source TEXT CHECK (… IN (…) OR … IS NULL)`) proves
  `ALTER TABLE ADD COLUMN` accepts a CHECK referencing only the new column in this
  SQLite (3.45.1). The CHECK is satisfiable by every existing row (all NULL). It was
  verified to **actually reject** a bad value on the live DB (`UPDATE … SET
  category_source='bogus_value'` → `Error: CHECK constraint failed`). The four allowed
  values are exactly §2.7's; `NULL` = "never classified" (the state of 780,826 rows).
- **`category_classification_log` — no CHECKs, all-`TEXT`, composite PK.** This matches
  every existing append-only table in the DB (`elo_snapshots`,
  `backtest_population_snapshots`, `event_cluster_labels`, `order_book_snapshots`),
  none of which carry CHECKs. `market_id / decided_category / method / run_id /
  classified_at` are `NOT NULL` (a log row is meaningless without them);
  `model_version / confidence / inputs_hash` are nullable (a deterministic-stage
  decision legitimately has no model or confidence). `confidence` is `TEXT` not `REAL`
  because the local LLM path (M9) emits `HIGH`/`LOW`, not probabilities.
  `classified_at` is `TEXT` (ISO8601) matching the snapshot-table timestamp
  convention. `(market_id, run_id)` PK → re-runs append rather than collide; SQLite
  builds `sqlite_autoindex_category_classification_log_1` for it.
- **No FK** `markets(market_id) → category_classification_log(market_id)`: the rest of
  the schema uses no foreign keys, and an append-only decision log should outlive any
  individual market row.

### The backfill UPDATE — exact statement

```sql
UPDATE markets SET category_source = 'legacy'
WHERE category IN ('Geopolitics','Elections');
```

Touches `category_source` **only**. `category`, `resolved`, `winning_outcome`,
`resolution_date`, `resolution_recorded_at`, `resolution_evidence_source`,
`resolution_evidence_detail` are **not** in the SET list. `last_checked` is not set
(its `DEFAULT CURRENT_TIMESTAMP` applies on INSERT only). **Rows updated: 11,967**
(against 11,967 expected). `legacy` rows that are NOT geo/elec: **0**.

---

## VERIFICATION

### a. Schema objects exist with correct types / constraints `[V]`

`markets` (tail of `SELECT sql FROM sqlite_master WHERE name='markets'`):
```
… resolution_evidence_detail TEXT, category_source TEXT
  CHECK (category_source IN
           ('llm_relevance_v1','deterministic_slug_v1','gamma_event','legacy')
         OR category_source IS NULL))
```
`PRAGMA table_info(markets)` → `19|category_source|TEXT|0||0` (nullable, no default,
not PK).

`category_classification_log`:
```
CREATE TABLE category_classification_log (
    market_id TEXT NOT NULL, decided_category TEXT NOT NULL, method TEXT NOT NULL,
    model_version TEXT, confidence TEXT, inputs_hash TEXT,
    run_id TEXT NOT NULL, classified_at TEXT NOT NULL,
    PRIMARY KEY (market_id, run_id)
)
```
`PRAGMA table_info` → notnull=1 on cols 0,1,2,6,7; notnull=0 on 3,4,5; PK members
`market_id` (pk 1), `run_id` (pk 2). Index `sqlite_autoindex_category_classification_log_1`.

### b. Backfill count + no other movement `[V]`

- `category_source='legacy'` rows: **11,967** — equal to the geo/elec row count and
  to §2.7's figure. `legacy` rows outside geo/elec: **0**. `category_source`
  distribution: `NULL` 780,826 + `legacy` 11,967 = 792,793 = total.
- Fingerprint diff (immediately-pre vs post): **IDENTICAL**. Unchanged:

  | | pre | post |
  |---|---|---|
  | `markets` total | 792,793 | 792,793 |
  | `trades` total | 12,514,902 | 12,514,902 |
  | `category` distribution | Unknown 778,987 / Elections 7,937 / Geopolitics 4,030 / … | *identical, all 24 values* |
  | `resolved` | 0→354,181 · 1→438,612 | 0→354,181 · 1→438,612 |
  | `resolution_evidence_source` | NULL 577,954 · clob 214,775 · gamma 63 · hydration_fill 1 | *identical* |
  | geo/elec | 11,967 | 11,967 |
  | `winning_outcome` non-NULL | 438,489 | 438,489 |
  | `resolution_date` non-NULL | 441,790 | 441,790 |

  `diff` of those lines → *"IDENTICAL — no movement in category / resolved / evsrc /
  counts"*.

### c. Existing writers unaffected `[V]`

Exercised the real code against a scratch DB built from the live (migrated) schema:

- **INSERT path** — `monitoring.database.Database.update_market()` on a brand-new
  `market_id`: row inserted, `category_source` defaulted to `NULL`, no error.
- **UPDATE path** — `Database.update_market()` again on the same id (its
  `INSERT … ON CONFLICT DO UPDATE`): title updated, `category_source` still `NULL`,
  no error.
- **Canonical resolution UPDATE** — `monitoring.resolution_writer.mark_market_resolved()`:
  `ResolutionWriteResult(accepted=True, …)`, row → `resolved=1, winning_outcome='Yes',
  resolution_evidence_source='clob'`, `category_source` still `NULL`. Works on the
  migrated schema and neither reads nor touches the new column.
- **Live-DB write acceptance post-ALTER**: canary `INSERT` + `DELETE` on
  `category_classification_log` on the real 18 GB DB → succeeded (1 row in, 0 after).
- Live `PRAGMA quick_check(3)` after everything → `ok`.

### d. `check_resolution_write_atomicity` `[V]`

`scripts/audit_invariants.py::check_resolution_write_atomicity` against the live
migrated DB → **count = 0**, examples = `[]`. (Also seen as `0` in a full
`audit_invariants.py` run — see g.)

### e. `trg_resolved_no_unresolve` intact and did not fire `[V]`

- Present in the post-migration schema (`SELECT … WHERE type='trigger'` → 1 row;
  DDL unchanged).
- On the scratch migrated schema: `UPDATE markets SET resolved=0` on a `resolved=1`
  row → `Error: stepping, resolved cannot transition from 1 to 0 (19)` — **fires
  correctly.**
- `UPDATE markets SET category_source='legacy'` on a `resolved=1` row → **succeeds**,
  row stays `resolved=1` — trigger does **not** fire (it is `BEFORE UPDATE OF
  resolved`; the backfill never lists `resolved`). This is exactly the shape of the
  production backfill statement.

### f. `run_tests.py` — baseline before vs after `[V]`

| | BEFORE (`tests/LATEST_TEST_RESULTS.md`, run 2026-08-31 08:47) | AFTER (post-migration) |
|---|---|---|
| Files | 17 non-hanging run, **16 passed, 1 failed** | 17 run, **16 passed, 1 failed** |
| Failing file | `test_backtest_window_population.py` (24 tests, 19 pass, **5 fail**) | `test_backtest_window_population.py` (24 tests, 19 pass, **5 fail**) |
| Failing tests | T2, T2b, T2c, T2d, T2f | T2, T2b, T2c, T2d, T2f — **same, identical "got" values** (4660 / 52 / 578 / 643) |
| Tests | 339,731 run, 5 failed | 339,715 run, 5 failed |

The one failing file is a **pre-existing** hardcoded-count reconciliation drift
(`Expected 4658, got 4660`, …) that moves with live data and predates this session.
**No new failure** — commit not blocked. (`test_behavioral_integration.py` was
`--skip`ped per `run_tests.py`'s own documented "always hangs in automation" note; it
passed interactively in the baseline.)

### g. `daily_maintenance.py` markets-touching steps `[V]`

Individual steps in dry-run / bounded mode (a full run was **not** done — it would
have run M9, which the task forbids touching, and would write category values):

| Step | Result |
|---|---|
| `sync_trade_categories.py --dry-run` | exit 0 — "Trades to update: 2 … DRY RUN - no changes made" |
| `resolution_sweep.py --dry-run` | completed clean, full per-market breakdown, no writes |
| `resolve_legendary_markets.py --limit 3 --dry-run` | exit 0 — "3 checked, 0 would update [DRY-RUN]" |
| `reconcile_geo_resolved_counts.py --dry-run` | exit 0 — "0 traders would change; Pool C 3919, LEGENDARY 10" (unchanged) |
| `verify_market_titles.py --dry-run` | opened the migrated DB and began scanning with no schema error; its markets SQL is `SELECT … FROM markets m` and `UPDATE markets SET title=? WHERE condition_id=?` — explicit columns, so an additive nullable column is inert. Full run time-capped, no error observed. |
| `audit_invariants.py` (full, read-only) | 26 invariants — **15 PASS / 5 REGRESSION / 0 CRITICAL / 6 OBSERVE**, exit 0 — **byte-identical** to this morning's 06:02 `daily_maintenance` audit (`2026-08-31-audit.json`). Migration caused zero change to any invariant. |
| `check_canonical_definitions.py` (full, read-only) | exit 0. The `geo_elo >= 2175` hardcode warnings are pre-existing code-lint in `trader_skill_metric_v2*.py`, unrelated to schema. |

**Services** (`polymarket-monitoring`, `polymarket-observer`, `trading-swarm`) were
**never stopped** and were `active` throughout and after.

---

## REVERT

SQLite is **3.45.1**, so `ALTER TABLE … DROP COLUMN` is available. Tested on a scratch
copy of the migrated schema: clean, `markets` back to 19 columns, log table gone,
`trg_resolved_no_unresolve` untouched, exit 0.

**Primary — the migration script (idempotent):**
```
cd /home/parison/projects/first-repo
python3 scripts/backup_database.py          # optional pre-revert safety copy
python3 scripts/migrate_add_category_source.py --revert --dry-run   # preview
python3 scripts/migrate_add_category_source.py --revert
```
which runs, in one transaction:
```sql
DROP TABLE category_classification_log;
ALTER TABLE markets DROP COLUMN category_source;   -- 'legacy' values vanish with the column
```

**Backfill-only revert** (keep the column and table, undo the `legacy` writes):
```sql
UPDATE markets SET category_source = NULL WHERE category_source = 'legacy';
```

**Disaster revert** (restore the whole DB to the pre-migration snapshot):
```
systemctl stop polymarket-monitoring polymarket-observer      # (needs sudo)
cp first-repo/backups/markets_20260831_183602.db first-repo/data/polymarket_tracker.db
#   sha256(backup) = de621776b67ad8ede77cf5b5315874f5210818a027b9b7232ff573818fa35d49
systemctl start polymarket-monitoring polymarket-observer
```
This loses any monitoring writes between 18:36 and the restore; given ingestion was
already quiet, that window is near-empty, but the `--revert` script is the cleaner
path and needs no service stop.

**Git:** the DB is not in git. The committed artifact is
`first-repo/scripts/migrate_add_category_source.py` (first-repo) + this record
(trading-swarm). `git revert` of the script commit removes the script; it does **not**
touch the DB — use `--revert` or the backup for that.

---

## WHAT WAS NOT DONE (scope)

- No classifier, pre-filter, or prompt built.
- `monitoring/monitor.py`, `scripts/backfill_market_categories.py` (M9), and
  `scripts/daily_maintenance.py` not modified.
- No `category` value written or changed — only `category_source`, only `'legacy'`,
  only on already-classified rows.
- No `audit_invariants.py` assertion added for "every geo/elec row has a non-NULL
  `category_source`" — the design flags it as a follow-up; adding it now is a separate
  change.
- The full detached `PRAGMA integrity_check` of the *source* DB was not run (it is
  hours-long on 18 GB); `quick_check` on the source returned `ok` before and after,
  and the backup passed a full `integrity_check`.
