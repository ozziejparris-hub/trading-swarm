# 2026-08-20 — Stage 1 implementation: hydrate_stub_markets.py split migration

**Implemented, verified, committed.** Design:
`2026-08-19-canonical-resolution-write-design.md` (`a7bfe5e`, as amended),
§A scope statement, §G Stage 1, summary table row #11. Prior stop:
`2026-08-20-stage1-hydrate-stub-migration.md` (`49f2f89`). Function:
`monitoring/resolution_writer.py` (`first-repo`, unmodified). Migrated
writer: `scripts/hydrate_stub_markets.py` (`first-repo`).

Every claim below is tagged **[V]** (verified this session, command/evidence
given) or **[I]** (inferred).

---

## What changed

`hydrate_stub_markets.py` contained one `UPDATE` statement doing two
operations. Per the amended §A scope statement, it is now split:

- **`is_resolved == 1` (resolution assertion):** migrated to
  `mark_market_resolved(evidence_source="hydration_fill", allow_no_winner=True,
  resolution_event_time=<parsed Gamma end-date/resolutionTime as a real
  datetime>, evidence_detail="outcomePrices>=0.99")`. `resolved`,
  `winning_outcome`, `resolution_date` now flow through the canonical path.
  `end_date`/`category`/`title` are not canonical-path columns (§A/§D) and
  stay a direct `UPDATE`, unchanged.
- **`is_resolved == 0` (scheduled-end-date proxy fill on an open market):**
  **untouched.** Same SQL text, same parameter order, same guard logic as
  before this migration — not modified in any way, per the task's
  constraint.
- **category/title filling:** untouched in both branches, as specified —
  a separate concern, out of scope.

`_parse_date()` (returns an isoformat string, used by the proxy branch and
for logging/`end_date`) is unchanged in output. A new `_parse_date_dt()`
does the identical parse but returns the `datetime` object itself, added
because `mark_market_resolved()`'s `resolution_event_time` parameter is
typed `datetime | None`, not `str | None` — passing a re-parsed string
would either fail the type contract or silently coerce, neither acceptable.
`resolution_event_time` is populated from Gamma's `endDate`/`endDateIso`/
`end_date_iso`/`resolutionTime` fields exactly as before — per the design's
own A2 ranking table, writer #11's use of these fields is classified Rank 1
(true event-time), listed alongside #7/#8, not Rank 2 (proxy) — that
classification only applies when the market has actually resolved, which is
exactly the branch this is scoped to. Write-time never leaks in as
event-time: `resolution_event_time` is `None` only if Gamma's date fields
failed to parse, in which case the row was already filtered out upstream
(`not resolution_date: not_found += 1; continue`) before either branch is
reached.

`monitoring/resolution_writer.py` was **not modified** — no new evidence
source, no comparator change. No other writer was migrated. No trigger was
created.

One commit in `first-repo` (see bottom).

---

## Verification (a): before/after dry-run diff, full population

**Population figures — today vs. yesterday's Stage 1 stop, like-for-like:**

| | Yesterday (`2026-08-20-stage1-hydrate-stub-migration.md`) | Today |
|---|---|---|
| Candidates | 1,258 | 1,258 |
| Already `resolved=1` in candidate pool | 0 | 0 **[V]** |
| Already `winning_outcome` non-null | 0 | 0 **[V]** |
| Live hits (Gamma found) | 8 | 8 |
| — resolved=1 (assertion) | 1 | 1 |
| — resolved=0 (proxy) | 7 | 7 |
| not_found | 1,250 | 1,250 |

**No drift.** Same population, same preconditions (every candidate row
starts `resolved=0`, `winning_outcome IS NULL`, `resolution_date IS NULL`),
same 8 live hits, same split. This also means `mark_market_resolved()`
never had to exercise its rank-comparator logic on this run — every call
landed on the `prev_resolved == False` branch (`accept = True` always) —
noted here rather than implied to be a broader test of the comparator.

**Method — pre-migration behavior extracted from git, not hand-transcribed
[V]:**
```
git log --oneline -3 -- scripts/hydrate_stub_markets.py
  67b173e test: integration test pass — all new June 6-9 features verified
```
Confirmed the working tree at migration start was byte-identical to
`67b173e` (`diff` against `git show 67b173e:...`, zero output) — the exact
commit the Stage 1 stop cited as "no changes since." Copied that version
into `scripts/` (so `DB_PATH`, which is relative to `__file__`, resolves
correctly), ran `--dry-run --limit 2000` against production, captured
stdout in full, deleted the copy.

Ran the **migrated** script `--dry-run --limit 2000` against production
the same way, captured stdout in full.

```
diff pre_dryrun_output.txt post_dryrun_output.txt
EXIT CODE: 0
```

**Byte-for-byte identical**, zero lines of difference, across all 1,258
candidate rows — the 1,250 `not_found` rows, the 7 proxy-branch rows, and
the 1 assertion-branch row. This is not incidental: dry-run mode never
calls `mark_market_resolved()` at all in the migrated script (its own
`dry_run` flag guards that call, but the computed `resolution_date`,
`resolved`, `winning_outcome`, `category`, `title_update` values feeding
the print line are identical upstream of either branch) — the print
statement in dry-run mode is untouched code, so this diff is clean by
construction, not by chance. The construction argument is why zero
divergence was expected; the diff is what actually confirms it happened.

---

## Verification (b): backup + live write

**Backup — online backup API, integrity-verified [V]:**
```
python3 scripts/backup_database.py
[BACKUP] Running online backup of data/polymarket_tracker.db to backups/markets_20260820_172308.db...
[BACKUP] Verifying integrity of backups/markets_20260820_172308.db...
[OK] Backup created: backups/markets_20260820_172308.db
     Size: 16453.4 MB
```
Location: `first-repo/backups/markets_20260820_172308.db` (17,252,634,624
bytes). `PRAGMA integrity_check` returned `ok` before the script would have
reported success — a failing check deletes the backup file and returns
non-zero, per `backup_database.py`'s own logic; it did not.

**Live write — run once, detached, observed [V]:**
```
nohup python3 scripts/hydrate_stub_markets.py --limit 2000 > live_write_output.txt 2>&1 &
disown
```
Full output captured. Final line:
```
[HYDRATE] Done — updated=8, not_found=1250, errors=0, total=1258
```
Matches the dry-run prediction exactly (`updated=8`, `not_found=1250`,
`errors=0`). No `[HYDRATE] ERROR updating ...` lines (which would indicate
an exception, including a trigger `ABORT`). No `mark_market_resolved() did
not accept` line (the one new log line this migration adds, for the case
where the canonical path rejects/flags — did not fire, consistent with the
pre-write state check below).

---

## Verification (c): assertion-branch row actually tagged

**Pre-write state of the one assertion-branch market
(`0xf8dbde8b6e038775a673947e59da2de15a2127272b50b9877400fdbf7cfc3026`)
[V]:** `resolved=0`, `winning_outcome` NULL, `resolution_date` NULL,
`resolution_recorded_at` NULL, `resolution_evidence_source` NULL,
`end_date` already `2028-11-07 00:00:00` (set by an earlier, unrelated
market-creation writer — not this script, not this migration).

**Post-write state [V]:**
```
resolved                    = 1
winning_outcome              = No
resolution_date               = 2028-11-07 00:00:00+00:00
resolution_recorded_at        = 2026-08-20 17:32:09.117500
resolution_evidence_source    = hydration_fill
resolution_evidence_detail    = outcomePrices>=0.99
end_date                     = 2028-11-07 00:00:00   (unchanged — already set)
```
This is **the first production write ever made through
`mark_market_resolved()`.** Confirmed by direct query, not assumed from the
script's exit code. `resolution_recorded_at` is a real write-time
timestamp (today, at the moment the script ran) — distinct from
`resolution_date`, which carries the true Gamma event-time
(`2028-11-07`) per `resolution_event_time` being non-null on this call,
exactly the split the schema (§D) exists to make legible.

---

## Verification (d): proxy-branch rows NOT tagged

All 7 proxy-branch markets checked directly **[V]**:

```
market_id (truncated)   resolved  winning_outcome  resolution_date              resolution_recorded_at  resolution_evidence_source
0xef89a2e4...            0                          2025-04-12T12:00:00+00:00   NULL                     NULL
0xbb57ccf5...             0                          2026-07-31T12:00:00+00:00   NULL                     NULL
0xad01e2b4...             0                          2025-05-31T12:00:00+00:00   NULL                     NULL
0xdf8e2dc5...             0                          2026-10-04T00:00:00+00:00   NULL                     NULL
0xb669c8c0...             0                          2025-11-03T10:00:00+00:00   NULL                     NULL
0xa7abe7ea...             0                          2026-12-31T00:00:00+00:00   NULL                     NULL
0xcd264046...             0                          2026-12-06T00:00:00+00:00   NULL                     NULL
```

`resolution_date` got its proxy fill exactly as before (direct write,
untouched code path). `resolution_recorded_at` and
`resolution_evidence_source` are NULL on every one of the 7 — they did not
go through `mark_market_resolved()`, and are not tagged as if they had.
The split did not leak.

---

## Verification (e): `check_resolution_write_atomicity`

```
python3 scripts/audit_invariants.py --verbose
  [○] T0  OBSERVE   0  [resolution-stage0/OBSERVE] resolution_recorded_at set without resolution_evidence_source
```
**0**, as required. **[V]**

---

## Verification (f): `trg_resolved_no_unresolve` did not fire

The trigger raises `RAISE(ABORT, ...)` on any `resolved: 1 -> 0` write,
which surfaces as a `sqlite3` exception. The live run's own
`try/except Exception` block around every write logs
`[HYDRATE] ERROR updating {market_id}: {e}` on any exception, including a
trigger abort. **Zero such lines appeared** (`errors=0` in the final
summary, confirmed by grep over the full captured output). **[V]** No row
in this run was already `resolved=1` before being written to (every
candidate started `resolved=0`, confirmed in verification (a)'s
precondition check), so the trigger's `WHEN` clause was never even a live
possibility on this run — consistent with, not merely inferred from, the
absence of errors.

---

## Verification (g): `run_tests.py`

```
Files  : 16 run, 15 passed, 1 failed
Tests  : 339700 run, 339695 passed, 5 failed
  FAILURES: test_backtest_window_population.py (19/24 passing)
```
**Matches the stated baseline exactly** (16 files, 15 passing,
`test_backtest_window_population.py` 19/24) — same file, same 5 sub-test
failures (T2, T2b, T2c, T2d, T2f), same pass count. **No new failure.**
`test_mark_market_resolved.py` — the suite that exercises
`mark_market_resolved()`'s own comparator — passed, unaffected (expected,
since that function was not modified). **[V]**

---

## Scale — stated plainly, not oversold

**This migration's live production exercise of the canonical path is one
row.** 8 markets had a live Gamma hit in today's full-population run; 7 of
those are the (unmigrated, unchanged) proxy branch; exactly **1** row
(`0xf8dbde8b...`) actually called `mark_market_resolved()` and got written
by it. That row's `prev_resolved` was `False`, so the call landed on the
simplest accept branch (`"written"`, no rank comparison, no same-rank
tie-break) — this run does **not** exercise the ranking comparator (A1/A2),
the same-rank disagreement path (§B), or a rejection/no-op outcome. Stage
1's purpose, per §G, is to prove the path works end-to-end at minimum
stakes — it does, verified above — not to validate the comparator's
harder branches at volume. Those remain untested in production until a
later stage's migration (§G Stage 3/4) puts a same-rank or cross-rank
collision in front of the function for real.

The other 1,250 candidates returned `not_found` from Gamma — unrelated to
this migration, already flagged as an open question in the design's
2026-08-20 amendment (§H open questions: the 8-in-1,258 live-hit rate).

---

## Reversibility

`git revert` the one `first-repo` commit below. The proxy branch reverts
to identical direct-write behavior (it never changed). The one migrated
row (`0xf8dbde8b...`) keeps its `resolution_recorded_at` /
`resolution_evidence_source` / `resolution_evidence_detail` values after a
revert (the schema isn't reverted, only the writer) — this is the same
"harmless, new columns stay populated for rows already written" property
§G's Stage 1 row always specified for this migration, now realized for one
real row instead of zero.

---

## Commits

- `first-repo`: migrates `scripts/hydrate_stub_markets.py`'s assertion
  branch to `mark_market_resolved()`; proxy branch, category/title logic,
  and `monitoring/resolution_writer.py` untouched.
- `trading-swarm`: this document.

*Generated 2026-08-20. No code outside `scripts/hydrate_stub_markets.py`
was written or modified. `monitoring/resolution_writer.py` was read, not
edited. No other writer migrated. No trigger created.*
