# Gamma Slug Fetch — Pre-Filter Residual (Swept)

**Date:** 2026-08-31, 19:29–19:49 UTC. **Type:** live API run; writes only to a new
staging table (`relevance_slug_staging`), touches nothing existing.
**Design:** `2026-08-31-relevance-classifier-design.md` (e601648) §1.1, §1.3, §2.5.
**Pre-filter:** first-repo cb9ee93; `2026-08-31-prefilter-implementation.md` (3fb24af).
**Code:** first-repo `scripts/fetch_relevance_slugs.py`.
**Tagging:** `[V]` verified this session.

---

## SUMMARY

- **COMPLETE.** 266/266 batches, ~20.5 min. **26,506 / 26,506** swept-residual markets
  staged. Outcomes: **found 26,491 (99.943 %)**, **not_found 15 (0.057 %)**,
  **no_slug 0**, **error 0**.
- **`event.slug` non-empty for 26,491 / 99.94 %** — the signal the design rests on is
  present for every market Gamma returned. `market.slug` and `event.title` same 99.94 %.
- Batch size **100** (Gamma's hard max; 120 → HTTP 422). Pacing 3.0–4.3 s/req
  throughout, **no 429s**. No abort condition fired.
- `markets` and `trades` **byte-identical** before/after.
  `check_resolution_write_atomicity = 0`. Terminal marker `COMPLETE` written
  atomically; Telegram fired (`telegram_sent=True`).
- **The unswept residual (43,837 markets) fetch remains OUTSTANDING** — a separate
  run, `--population unswept`, not done here.

---

## BEFORE THE RUN

### 1. Staging table — schema and rationale `[V]`

```sql
CREATE TABLE relevance_slug_staging (
    market_id     TEXT PRIMARY KEY,   -- Gamma conditionId; PK -> idempotent re-run / keyset resume
    outcome       TEXT NOT NULL,      -- 'found' | 'not_found' | 'no_slug' | 'error'
    market_slug   TEXT,               -- Gamma market.slug
    event_slug    TEXT,               -- Gamma events[0].slug   (the design's LLM-stage signal)
    event_title   TEXT,               -- Gamma events[0].title
    n_events      INTEGER,            -- len(events[]); 0 = no parent event
    gamma_closed  INTEGER,            -- Gamma market.closed flag (0/1/NULL) — provenance
    http_status   INTEGER,            -- HTTP status of the batch request that produced this row
    run_id        TEXT NOT NULL,      -- this fetch run
    fetched_at    TEXT NOT NULL       -- ISO8601 UTC
);
```

- **It is NOT `markets`.** No `category`, no `category_source`, no resolution column —
  it stages LLM-stage *inputs* only, keyed by `market_id`.
- **`market_id` PK** → a re-run is `INSERT OR REPLACE` and the keyset cursor resumes
  cleanly; the autoindex is the resume/lookup index.
- **`outcome`** makes coverage *measurable*, not inferred — `not_found` (Gamma has no
  such market), `no_slug` (returned but `event.slug` empty), `error` (batch HTTP/parse
  failure — retried on the next run, since `already_staged()` excludes `outcome='error'`).
- **`n_events` / `gamma_closed` / `http_status` / `run_id` / `fetched_at`** — enough
  to reconstruct which run wrote a row, whether the market was really closed, whether
  its batch errored, and whether it has a parent event.
- No FK to `markets` — consistent with the rest of the schema (no FKs), and staging
  should survive independently.

### 2. `market_id` usable as the Gamma conditionId — verified against the residual set `[V]`

Ran the pre-filter over the swept-Unknown population and checked the **26,506 residual
market_ids** (not the whole population):

| check | result |
|---|---|
| `^0x[0-9a-fA-F]{64}$` (66-char 0x + 64 hex) | **26,506 / 26,506 = 100.00 %** |
| contains a 16×`0` synthetic-padding run | 0 |
| length ≠ 66 | 0 |

`market_id` **is** the conditionId for this population, directly. (The `condition_id`
*column* is populated for only ~1,019 of the swept markets — not needed.)

### 3. Batch size — established empirically `[V]`

Probed `GET gamma-api.polymarket.com/markets?closed=true&condition_ids=…` at
n = 12, 25, 40, 50, 80, 100, 120:

| n | result |
|---|---|
| 12 | HTTP 200, 2.42 s, 12 returned |
| 50 | HTTP 200, 2.74 s, 50 returned |
| **100** | **HTTP 200, 3.08 s, 100 returned** |
| **120** | **HTTP 422** `{"error":"expected array length <= 100"}` |

**The endpoint's hard max is 100 condition_ids per request** — the design's observed
"~12 per request" was conservative. Used **100**. At n = 100 the request is only
~0.7 s slower than n = 12, so 100 is ~8× fewer requests for ~free. This differs from
the design figure and is reported as such.

### 4. Runway `[V]`

| | |
|---|---|
| launch | **2026-08-31 19:29:01 UTC** (Monday) |
| next 03:00 UTC backup | 2026-09-01 03:00:00 UTC |
| maintenance-stop boundary (−30 min) | 2026-09-01 02:30:00 UTC |
| runway to boundary | **~7.0 h** |
| projected run: 266 batches × ~4.6 s (3.1 s req + 1.5 s sleep) | **~20 min** |
| **actual run** | **19:29:01 → 19:49:36 = 20.5 min** |
| margin at completion | **~6.7 h** before the boundary |

No sweep segment or `daily_maintenance` was running (verified). The run finished with
hours of margin; the 03:00 backup is untouched.

### 5. No backup needed — reasoning confirmed, not assumed `[V]`

`scripts/fetch_relevance_slugs.py` issues exactly: `CREATE TABLE IF NOT EXISTS
relevance_slug_staging (…)` and `INSERT OR REPLACE INTO relevance_slug_staging …`.
There is **no** `UPDATE` / `DELETE` / `ALTER` against `markets`, `trades`, or any
pre-existing object anywhere in the script (grep-checked). A new-table insert
allocates fresh pages; it cannot rewrite a page belonging to an existing table.
SQLite is ACID under WAL — a crash mid-batch rolls back that batch's open
transaction; committed batches persist; nothing existing partial-corrupts. The
`(b)` fingerprint below confirms `markets`/`trades` unchanged. Backup skipped
correctly.

---

## THE RUN

`scripts/fetch_relevance_slugs.py --population swept`, launched detached with
`python3 -u` after `set -a; source ~/.env_trading; set +a` (so the Telegram
credentials `telegram_alerts_token` / `telegram_chat_id` reach the process — the gap
fixed 2026-08-25).

- **Keyset cursor on `market_id`**, never LIMIT/OFFSET. The residual `(market_id,
  title)` list is materialised once from a read-only connection and sorted by
  `market_id` (the immutable unique PK); each batch is the next 100 ids `> cursor`;
  the cursor is the largest staged id, persisted after every batch. Resume also skips
  any id already staged with a definitive outcome. There is no window that can slide
  past unexamined rows.
- **Atomic checkpoint** after every batch: `data/checkpoints/slug_fetch_swept_checkpoint.json`,
  written temp-then-`os.replace`.
- **Every response outcome recorded** — 100 rows per batch, `found` / `not_found` /
  `no_slug` / `error`, so coverage is a `GROUP BY outcome`, not an inference.
- **Terminal marker** on every exit path via
  `data/characterizations/sweep_common/sweep_terminal_signal.py` (first-repo 72e7337):
  `write_terminal_marker(status ∈ {COMPLETE, ABORTED, MAINTENANCE-STOPPED, EXCEPTION})`
  + `send_telegram_terminal(...)` — reused, not reimplemented.

### Run results `[V]`

| | |
|---|---|
| status | **COMPLETE** |
| batches | 266 / 266 |
| wall time | 19:29:01 → 19:49:36 UTC (20.5 min) |
| staged | **26,506 / 26,506** |
| `found` | **26,491** (99.943 %) |
| `not_found` | **15** (0.057 %) |
| `no_slug` | **0** |
| `error` | **0** |
| pacing | 3.0–4.3 s/req (one 4.3 s outlier at batch 240); baseline 3.1 s |
| HTTP 429 / rate-limit | **none** |
| `http_status` on every row | 200 |

### Abort conditions — none fired

| condition | threshold | observed | would have meant |
|---|---|---|---|
| HTTP 429 / rate-limit | any | none | PAUSE + report, no aggressive retry |
| `not_found` rate (once n ≥ 100) | > 10 % | **0.057 %** | the `market_id` = conditionId assumption is wrong |
| pacing degradation | > 3× baseline (> 9.3 s/req), sustained 2 batches | max 4.3 s once | Gamma degrading; stop before it worsens |
| within 30 min of 03:00 UTC | 02:30 boundary | finished 19:49, 6.7 h early | clean stop at a batch boundary (MAINTENANCE-STOPPED) |

---

## VERIFICATION

### a. Staging row count and outcomes `[V]`

- **26,506 rows / 26,506 distinct `market_id`** — exactly the residual.
- `found` **26,491 (99.943 %)** · `not_found` **15 (0.057 %)** · `no_slug` **0** ·
  `error` **0**.
- All rows: `run_id = slugfetch-swept-20260831T192901Z`, `http_status = 200`.
- `n_events = 1` for all 26,491 found; `NULL` for the 15 not_found; `n_events = 0`
  (market exists but has no parent event) for **0**.

### b. `markets` and `trades` untouched `[V]`

Fingerprint (category distribution, `category_source` counts, `resolved` count,
`resolution_evidence_source` breakdown, `category_classification_log` row count,
`markets`/`trades` totals) **before vs after → `diff` clean, IDENTICAL**:

| | pre | post |
|---|---|---|
| markets_total | 792,793 | 792,793 |
| trades_total | 12,514,904 | 12,514,904 |
| category distribution (24 values) | *identical* | *identical* |
| `category_source` | NULL 780,826 · legacy 11,967 | *identical* |
| `resolved` | 0→354,181 · 1→438,612 | *identical* |
| `resolution_evidence_source` | NULL 577,954 · clob 214,775 · gamma 63 · hydration_fill 1 | *identical* |
| `category_classification_log` rows | 0 | 0 |

### c. `check_resolution_write_atomicity` `[V]`

`scripts/audit_invariants.py::check_resolution_write_atomicity` against the live DB →
**count = 0** → PASS.

### d. Sample staged rows — actual slug values `[V]`

Found rows (the LLM stage's input):

| `market_id` | `event_slug` | `event_title` |
|---|---|---|
| `0xe8aed51f…` | `cyprus-house-of-representatives-election-winner` | Cyprus House of Representatives Election |
| `0x24da2d85…` | `who-will-be-the-democratic-nominee-in-the-maine-senate-race-on-july-27-…` | Maine Democratic Senate nominee on July … |
| `0x543a09b2…` | `trump-approval-rating-on-march-27` | Trump approval rating on March 27? |
| `0xa0cf22a3…` | `houthis-successfully-target-shipping-by-march-31` | Houthis successfully target shipping by… |
| `0x0ab84b5c…` | `what-will-trump-say-during-remarks-in-michigan-…` | What will Trump say during remarks in Mi… |
| `0x4b6042e5…` | `mlb-mia-phi-2026-08-19` | Miami Marlins vs. Philadelphia Phillies |
| `0x54526322…` | `wta-sabalen-annli-2026-03-20` | Miami Open: Aryna Sabalenka vs Ann Li |
| `0x130393b9…` | `bkaba-bud-dub-2026-05-25` | Buducnost vs. BC Dubai |
| `0x44df6358…` | `xrp-price-on-may-15` | XRP price on May 15? |
| `0x04c3b10f…` | `2-free-app-in-the-us-apple-app-store-on-march-13` | #2 Free App in the US Apple App Store on… |
| `0x5aad6d70…` | `fl1-ang-hac-2026-04-18-player-props` | Angers SCO vs. Le Havre AC - Player Prop |
| `0x5e87ec05…` | `elon-musk-of-tweets-april-14-april-21` | Elon Musk # tweets April 14 - April 21 |

The slug materially sharpens the LLM's input: genuinely-election residuals
(`…-election-winner`, `…-democratic-nominee…`) and geopolitics (`houthis-…-target-
shipping`) resolve almost from the slug alone; the non-geo residuals the title-only
pre-filter could not exclude (`mlb-…`, `wta-…`, `bkaba-…` basketball, `xrp-price-…`,
`…-apple-app-store-…`, `…-player-props`) are now obvious.

**The 15 `not_found`** (id + title from `markets`): 12 are the family
`"Will <TEAM> Qualify to LAN BLAST Bounty 2026 Season 2?"` (esports qualification —
absent from Gamma's `closed=true` view), 2 are `"Another Elon baby …"` (novelty), and
one each: `"Will Brian Hastings Cash the WSOP Main Event 2026?"`, `"Total Internet
Blackout in Iran by June/July 2026?"` (×2 — geo-relevant, but Gamma has no row), a
flights-delayed count. The 15 will reach the LLM stage on **title only**; two of them
are geo-relevant.

### e. Fraction with non-empty `event.slug` — the design's signal `[V]`

| field | non-empty | % of 26,506 |
|---|---:|---:|
| **`event_slug`** | **26,491** | **99.94 %** |
| `market_slug` | 26,491 | 99.94 % |
| `event_title` | 26,491 | 99.94 % |
| (`event.category` non-null) | 0 | 0 % — as expected (ce35996); this is why the classifier exists |

Every market Gamma returned has all three slug fields. The only 0.06 % without them
are the 15 `not_found`.

### f. `run_tests.py` vs baseline `[V]`

**18 files run, 17 passed, 1 failed** — identical to the baseline established in
`2026-08-31-classifier-schema-migration.md` §f and `…prefilter-implementation.md`.
The one failing file is `test_backtest_window_population.py` (5 hardcoded-count-drift
tests), pre-existing and unrelated. `test_relevance_prefilter.py` → PASS (63/63);
`test_sweep_terminal_signal.py` (the reused terminal-marker module) → PASS (19/19).
**No new failure.**

### g. Terminal marker + Telegram `[V]`

- `data/checkpoints/slug_fetch_swept_terminal.json`: `status="COMPLETE"`,
  `batches_completed=266`, `n_batches=266`, `cumulative_processed=26506`,
  `cumulative_tally={"found":26491,"not_found":15}`, `written_at_utc=2026-08-31T19:49:35Z`.
  Written atomically (temp + `os.replace`).
- Log: `[TELEGRAM] Terminal notification sent.` and `… telegram_sent=True`.
  `send_telegram_terminal()` confirmed the send (it returns `False` on any failure and
  never raises).
- Final checkpoint: `last_market_id=0xfffd5296…` (near the lexicographic max),
  266/266.

---

## OUTSTANDING — the unswept residual fetch

**Not done in this task, by scope.** The unswept residual is **43,837 markets**
(`category='Unknown' AND (resolved=0 OR resolved IS NULL)`, RESIDUAL per the
pre-filter). It is a **separate run**:

```
set -a; source ~/.env_trading; set +a
python3 -u scripts/fetch_relevance_slugs.py --population unswept
```

The same script handles it (`--population unswept` switches the WHERE clause and the
checkpoint/marker paths). Note: ~7.3 % of the unswept residual's `market_id`s are
zero-padded synthetic ids that are not real conditionIds (established in the
slug-fetch design work) — the not_found rate on that run will legitimately be higher
than this run's 0.06 %, and the 10 % abort threshold should be read with that in
mind. Projected duration ~34 min (438 batches × ~4.6 s); it must be launched with
enough runway before 02:30 UTC or it will MAINTENANCE-STOP cleanly and resume.

---

## WHAT WAS NOT DONE (scope)

- No LLM stage, no prompt.
- No validation-gate sample drawn.
- No write of `category`, `category_source`, or `category_classification_log`.
- `monitoring/monitor.py`, `scripts/backfill_market_categories.py` (M9),
  `scripts/daily_maintenance.py` untouched. Services never stopped.
- Unswept residual fetch — outstanding (above).
