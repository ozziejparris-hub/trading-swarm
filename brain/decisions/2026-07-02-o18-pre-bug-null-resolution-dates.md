# O-18 — Pre-bug NULL `resolution_date` rows, quantified and ledgered

**Date:** 2026-07-02
**Method:** Verified against live DB + two prior-day backups (`polymarket_tracker_2026-07-01.db` 18:17, `polymarket_tracker_2026-07-02.db` 03:00), not taken from memory of last night's session.

---

## What this is

55 markets (corrected from the 60 estimated 2026-07-01, see drift note below) have `resolved = 1` (a winning outcome is set) but `resolution_date` is still `NULL`, and `last_checked < 2026-06-05` (i.e. outside the O-17 co-write-bug window — these predate that bug and are **not** part of it). Filter used:

```sql
SELECT * FROM markets
WHERE resolved = 1 AND resolution_date IS NULL AND last_checked < '2026-06-05'
```

**Distinct root cause from O-17.** O-17 was an active *generator* bug (3 passes in `fast_resolution_check.py` + legendary scripts, all missing the `resolution_date` co-write on new writes since ~June 9-14). O-18 rows are **historical** — set once, never revisited by any generator, most tracing to a single import event. Connected to O-16's 194,216-row backlog only by sharing the same `2025-12-11` / `historical_backfill` signature — not the same mechanism.

## Breakdown (55 total, verified 2026-07-02)

| Sub-population | Count | Signature |
|---|---|---|
| 2025-12-11 `historical_backfill` import | 50 | `last_checked` = import timestamp (11:0x–11:2x UTC that day), not a real check time — off by months from any real resolution date |
| 2026-01-12 batch | 4 | `data_source='live_monitoring'`, one row has `winning_outcome='unknown'` (`0x2d2d5357...`) rather than Yes/No — a distinct, unexplained anomaly worth a closer look if this item is ever picked up |
| 2026-04-28 isolated anomaly | 1 | `data_source='live_monitoring'`, `end_date` is also `NULL` (the only row in the 55 missing end_date entirely) — different signature again from both other groups |

**Do NOT blanket-backfill with `last_checked`** — for the 50-row Dec-11 group this is proven wrong (import time ≠ resolution time, the exact mistake the O-17 backfill scoping deliberately excluded these rows to avoid). The 5-row remainder needs its own per-row judgment call, not a formula.

## Drift note: 60 → 55 overnight (2026-07-01 to 2026-07-02) — VERIFIED BENIGN

Last night's count was 60. Diffed exactly against both the 2026-07-01 18:17 backup (post O-17 fix commit) and the 2026-07-02 03:00 backup (pre-maintenance): **both show 60**, confirming the drift happened during today's 06:00 maintenance run, not before.

Exact diff identified the 5 rows that left:
```
0xe226982316ce20de2e72dfd693a2caa0829ae20c612746534b24a4d700d366c3
0xdfa4be9c6786791072da61477fe3938ee78c8edc2b2e6154239996ab1bc96ae9
0xe16434167950f68d49ae10091a8be8cb6087d24b0a8128debb87499547429c5a
0xdf103c45f308d3ee2a5e3ec5c9afac925a8ece13e83f5b818583e326b5ca127f
0xdc7ff8e7d1bf22e6b9f372b3122bf553ed7bfedebc500e76e61aab35d9ebdb8e
```

All 5 are 2025-12-11 `historical_backfill` rows. Before/after comparison shows: `end_date` was rewritten from the old space-separated format to Gamma's normalized ISO format, and `resolution_date` was set equal to the new `end_date` — **`last_checked` did not change** (still 2025-12-11). This is the signature of `scripts/backfill_market_dates.py`, confirmed by reading its source: it queries `WHERE end_date IS NULL OR resolution_date IS NULL LIMIT ?` (no `resolved` filter, so it processes O-18 rows too), re-fetches the market from Gamma/CLOB, and writes `resolution_date = COALESCE(resolution_date, end_date)` — already non-destructive, already correct. It ran as a maintenance step today (162.9s) and happened to match/update 5 of the 55 candidate rows via its `LIMIT`-bounded batch.

**Verdict: benign.** Not corruption — a previously-uncatalogued (14th) `resolution_date` writer that was already safe, slowly draining this population using `end_date` as a proxy (a better proxy than `last_checked` for these rows, though still unverified against Polymarket's actual resolution timestamp). Worth a note for whenever O-17's deferred `mark_market_resolved()` helper work happens — this script should be added to that call-site inventory even though it isn't broken.

## Current 55 market_ids (2026-07-02, for future diffing)

See companion file: `2026-07-02-o18-market-ids.txt` in this directory.

## Status / Next steps (not done here — read-only investigation)

- OPEN — not investigated beyond this quantification/ledgering pass.
- Needs, if picked up: (1) explain the 2026-01-12 `winning_outcome='unknown'` row, (2) explain the 2026-04-28 NULL-end_date anomaly, (3) decide a per-row resolution strategy for the 50-row Dec-11 group (likely: re-fetch each from Gamma individually rather than any bulk heuristic).
- **FROZEN-AREA?** No.
