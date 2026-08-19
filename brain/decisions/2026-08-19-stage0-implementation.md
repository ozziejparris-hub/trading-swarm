# 2026-08-19 — Stage 0 implementation: canonical resolution write path

**This is a write task against production schema — executed, not
proposed.** Design: `2026-08-19-canonical-resolution-write-design.md`
(`73ca92e`) §C, D, E, G. Trigger evidence:
`2026-08-19-canonical-design-open-questions.md` (`c75a906`) Q3. Every
claim tagged **[V]** (verified — command/output given) or **[I]**
(inferred). All six verifications passed; nothing here required stopping.

**Scope discipline, confirmed at the end:** exactly the four things
asked for — schema, trigger, function, invariant. No writer migrated.
`trg_require_recorded_at` not created. No CI lint rule built. No backfill.

---

## Safety

**Backup, WAL-safe, before any schema change [V]:**
`python3 scripts/backup_database.py`, run detached (`nohup ... & disown`)
given the ~16GB production DB and the box's two crashes this month. Uses
`Connection.backup()` (the online backup API), not a file copy — safe
against a live WAL-mode writer.

```
[BACKUP] Running online backup of data/polymarket_tracker.db to backups/markets_20260819_204109.db...
[BACKUP] Verifying integrity of backups/markets_20260819_204109.db...
[OK] Backup created: backups/markets_20260819_204109.db
     Size: 16413.1 MB
```

**Backup location:** `backups/markets_20260819_204109.db`. Integrity
verified by the script's own `PRAGMA integrity_check` returning `ok`
before proceeding — not merely a file-exists check.

---

## What was built

### 1. Schema (design §D)

Ran a committed, idempotent migration script,
`scripts/migrate_stage0_resolution_columns.py` (dry-run first, confirmed
the plan, then executed for real):

```sql
ALTER TABLE markets ADD COLUMN resolution_recorded_at TIMESTAMP;
ALTER TABLE markets ADD COLUMN resolution_evidence_source TEXT
    CHECK (resolution_evidence_source IN
           ('clob','gamma','manual_verified','hydration_fill')
           OR resolution_evidence_source IS NULL);
ALTER TABLE markets ADD COLUMN resolution_evidence_detail TEXT;
```

**No SQLite `ALTER TABLE ADD COLUMN` limitation encountered** — the task
flagged this as a possible stop condition. Tested in an isolated scratch
DB before touching production (SQLite 3.45.1, this box's version): a
`CHECK` constraint referencing only the new column itself (not other
columns, no non-constant expressions) is accepted by `ADD COLUMN`
cleanly, existing rows receive `NULL` for the new column (which
trivially satisfies `... OR resolution_evidence_source IS NULL`), and the
constraint is genuinely enforced going forward (confirmed: a direct
`UPDATE ... SET resolution_evidence_source = 'bogus'` was rejected with
`CHECK constraint failed`, a valid value was accepted). **No deviation
from the design was required.**

**No backfill performed, per design §D and this task's explicit
instruction** — confirmed empirically post-migration: all 735,451 rows
have `NULL` in all three new columns.

### 2. Trigger (design §G, tested at `c75a906` Q3)

Created via the same migration script, exact SQL from the source report,
no variant:

```sql
CREATE TRIGGER trg_resolved_no_unresolve
BEFORE UPDATE OF resolved ON markets
WHEN OLD.resolved = 1 AND NEW.resolved = 0
BEGIN
    SELECT RAISE(ABORT, 'resolved cannot transition from 1 to 0');
END;
```

### 3. Function (design §C)

New module: `monitoring/resolution_writer.py` — `mark_market_resolved()`
and `ResolutionWriteResult`, matching the design's signature exactly
(parameters, dataclass fields, returns-never-raises-for-routine-rejection,
`dry_run` passthrough, INFO/WARNING logging).

**Placed in `monitoring/`**, alongside `monitoring/trade_evaluator.py` —
the existing precedent for a canonical single-purpose write helper in
this codebase — so that E's promotion condition ("zero direct writes
outside `mark_market_resolved()`'s own module") has an unambiguous module
boundary to check against.

**Called by nothing** — confirmed by construction (no other file imports
it; this task did not touch any of the 13 writers).

**One interpretation the design's prose does not spell out verbatim,
resolved rather than stopping on, with reasoning recorded in the module's
own docstring:** A1's ranking table lists `hydration_fill` (writer #11)
in the same row as `gamma`/`manual_verified` (both explicitly Rank 2) —
the most direct textual reading is that all three share Rank 2, with no
special-cased comparator behavior for `hydration_fill` beyond the generic
same-rank policy. Implemented that way. This is not a case where "the
design cannot be implemented as specified" — the ranking table's own
"Writers using it" column already places #11 at Rank 2 — it's a case
where the design states the rank via a table row rather than a
standalone sentence, and the interpretation is unambiguous once the
table is read as the source of truth. Recorded explicitly rather than
silently assumed.

**A second interpretation, also recorded rather than assumed silently:**
an existing `resolved=1` row with `resolution_evidence_source IS NULL`
(a legacy or non-canonical write) has no rank the design's tables define.
Implemented as: treated as lower-ranked than any real evidence source, so
a canonical-path proposal can always improve on an untagged legacy value.
This is the only reading consistent with the migration sequence's own
Stage 2–5 intent (writers are migrated one at a time; every migrated
writer's first canonical call will necessarily target rows the
*previous*, non-canonical version of that same writer already resolved,
untagged — the function must be able to accept and tag them, or no
writer could ever be migrated without a data-repair step the design
never asks for).

### 4. Invariant (design §E)

Added `check_resolution_write_atomicity` to `scripts/audit_invariants.py`,
registered in `ALL_CHECKS`, following the file's existing tier-0 pattern
exactly (same shape as the five `check_comp_elo_*` functions):

```sql
SELECT COUNT(*) FROM markets
WHERE resolution_recorded_at IS NOT NULL
  AND resolution_evidence_source IS NULL
```

Tier 0 / OBSERVE — `determine_status()` hardcodes `tier == 0` to always
return `"OBSERVE"`, matching the existing convention exactly, not a new
mechanism.

**Promotion condition recorded in the docstring, verbatim as design §E
specifies, in code rather than left in prose only:** promotion to Tier 1
/ CRITICAL is gated on a re-run of `scripts/scan_write_paths.py`
reporting zero direct `UPDATE markets SET
(resolved|winning_outcome|resolution_date)` statements outside
`monitoring/resolution_writer.py` — i.e., Migration Stage 5 verified
complete by the same tooling that produced the 13-writer map. The
docstring explicitly states this is the concrete answer the ELO arc's own
design specified in prose ("gating from end of Stage 3") and never wired
into this file's tier logic — naming the precedent so this check doesn't
quietly join the ELO arc's five permanently-OBSERVE checks by omission.

---

## Verification

### a. Schema

**[V]** Confirmed via `sqlite3 .schema markets` (production): all three
columns present, correct types, `CHECK` constraint present verbatim.
Confirmed via direct query: all 735,451 existing rows have `NULL` in all
three new columns (no backfill occurred).

**Exercised a real writer's INSERT path against a scratch copy of the
post-migration schema, not production** — copied only the `CREATE TABLE
markets` / index / trigger DDL (no data) into a fresh scratch DB, then
called the *actual* `monitoring.database.Database.update_market()`
method (a writer with zero knowledge of the three new columns) against
it: the INSERT succeeded, the new columns correctly defaulted to `NULL`.
Also exercised an existing resolution-writer's `UPDATE` shape
(`fast_resolution_check.py`'s COALESCE-guarded pattern) against the same
scratch schema on the freshly-inserted row: succeeded, resolved
0→1 cleanly, new columns remained untouched/`NULL`, no trigger
interference (a `BEFORE UPDATE OF resolved` trigger with `WHEN OLD.resolved=1
AND NEW.resolved=0` cannot fire on an INSERT or on a 0→1 transition, by
construction — confirmed, not merely assumed).

### b. Trigger — non-tautological, against live production, rolled back

**[V]** Ran three explicit-transaction tests directly against
`data/polymarket_tracker.db`, each wrapped in `BEGIN`/`ROLLBACK` (never
`COMMIT`) so no production data was permanently changed by the
verification itself:

```
test market (resolved=1): 0xe3b423dfad8c22ff75c989
test market (resolved=0): 0x7333b6e016f7f60d86f15f
TEST 1 PASSED: 1->0 transition BLOCKED -- resolved cannot transition from 1 to 0
  post-test value (should still be 1): 1
TEST 2 PASSED: 0->1 transition succeeded
  post-test value (should still be 0, since we rolled back): 0
TEST 3 PASSED: 1->1 no-op re-write succeeded
```

**Why this would not pass if the trigger were absent:** Test 1 explicitly
checks for `sqlite3.IntegrityError` being raised by the `UPDATE`
statement. Without the trigger, that statement has nothing to raise an
error — it would simply succeed, silently setting `resolved=0`, and the
test's `except IntegrityError` branch (which prints `PASSED`) would never
execute; the code path that prints `FAILED: ... transition SUCCEEDED`
would run instead. The test is written to fail loudly in that case, not
to pass either way.

### c. Function — unit tests, and falsifiability demonstrated

**[V]** `tests/test_mark_market_resolved.py`, 9 test groups / 26
assertions, run against a fresh in-memory SQLite DB (never production):
**26 passed, 0 failed.** Covers: first write always accepted; higher
rank (`clob`) overwrites lower rank (`gamma`); lower rank does **not**
overwrite higher rank, value provably unchanged; same-rank matching value
is a silent no-op, value unchanged; same-rank **differing** value is
flagged (`reason == "flagged: same-rank disagreement"`), **not**
overwritten, first-recorded value retained; `dry_run=True` reports what
would happen but makes no write; an untagged legacy `resolved=1` row is
improvable by any real evidence source; `winning_outcome=None` rejected
unless `allow_no_winner=True`; the 3-tier `resolution_date` fallback
(true event-time used when given; an existing proxy value preserved when
not; write-time used only when neither exists).

**Falsifiability demonstrated, not asserted** — ran the same 26
assertions again with `EVIDENCE_RANK["clob"]` and `["gamma"]` values
swapped (a deliberately inverted comparator), via
`python3 tests/test_mark_market_resolved.py --demonstrate-failure`:
**19 passed, 7 failed** — the rank-comparison tests (T2, T3) and the
reason-string assertions in T4/T5 (whose branches depend on which side
of the comparison wins) fail exactly as expected when the ranking logic
is broken, proving the test suite is not vacuously true.

**One test-authoring bug found and fixed during this verification,
recorded rather than silently corrected:** an early version of T9
compared a stored SQLite value (read back as a Python `str`, since
`sqlite3`'s default datetime adapter is write-only) against the original
`datetime` object passed in — a type-comparison bug in the *test*, not in
`mark_market_resolved()`. Diagnosed by inspecting the actual stored value
(`'2026-03-15 12:00:00'`, matching `str(event_time)` exactly) before
concluding the function itself was correct and fixing the test's
comparison, not the function.

### d. Invariant

**[V]** `check_resolution_write_atomicity(cur, verbose=True)` called
directly: `count=0`, `tier=0`, `examples=[]` (as expected — nothing has
called `mark_market_resolved()` yet, so `resolution_recorded_at` is
`NULL` on every row and the check's own precondition, `resolution_recorded_at
IS NOT NULL`, matches nothing). Confirmed registered in `ALL_CHECKS`.
`determine_status(0, 0, 0)` returns `"OBSERVE"`.

**Full integration confirmed, not just the isolated function call:** ran
`python3 scripts/audit_invariants.py --verbose` end-to-end against
production. Total checks went from 25 to 26; OBSERVE count went from 5 to
6; the new check appears in the written report
(`brain/agent-outputs/data-audit/2026-08-19-audit.json`) with
`status: "OBSERVE"`. Tier-1 `CRITICAL` count unaffected (0) — the pre-ELO
gate's own pass/fail behavior is unchanged by this addition.

### e. `run_tests.py`

**[V]** Full run, ~140s:

```
Files  : 16 run, 15 passed, 1 failed
Tests  : 339,700 run, 339,695 passed, 5 failed
  FAIL  test_backtest_window_population.py  (24 tests, 19 passed)
  PASS  test_mark_market_resolved.py
```

**16 files, not the stated baseline of 15** — expected, not a deviation:
`run_tests.py` glob-discovers every `tests/test_*.py` file, and this
task added one (`test_mark_market_resolved.py`), which passed. The
**known failure is byte-for-byte identical to baseline**
(`test_backtest_window_population.py`, 19/24, same file, same count).
**No new failure.**

### f. `daily_maintenance.py`'s markets-touching steps

**[V]** A full `daily_maintenance.py` run takes ~2.7 hours (this
session's own earlier observation) — per the task's own fallback
instruction, ran the individual steps that touch `markets` in
`--dry-run`/`--test` mode instead, each against live production data,
each confirmed to make **no** production writes:

| Script (daily_maintenance step) | Mode | Result |
|---|---|---|
| `fast_resolution_check.py` (step 16) | `--test --limit 20` | All 4 internal passes ran; 103.3s; stale-CLOB pass resolved 15/128 candidates *in test mode only*; exit 0 |
| `resolve_legendary_markets.py` (step 20) | `--limit 20 --dry-run` | 10 checked, 0 resolved on API, exit 0 |
| `hydrate_stub_markets.py` (post-test-suite step) | `--limit 20 --dry-run` | 20 processed, exit 0 |
| `backfill_market_categories.py` (step 15) | `--limit 20 --dry-run` | 20 classified (dry-run), exit 0 |
| `resolution_sweep.py` (step 5) | `--days 7 --dry-run` | ran cleanly, showed real dry-run output, exit 0 |

**Not exercised: `verify_market_titles.py` (step 14)** — has no `--limit`
flag and would run against the full ~733K-row table unbounded; skipped
as disproportionate for a verification pass, named rather than silently
omitted. It touches only `title`, not the three resolution columns this
Stage 0 change is about.

**Confirmed no unintended production writes resulted from any of these
five runs:** `resolution_recorded_at IS NOT NULL` count still `0` and
total `markets` row count still `735,451` after all five ran. **One
minor, pre-existing-pattern side effect, named rather than hidden:**
`backfill_market_categories.py`'s own checkpoint file
(`data/category_backfill_state.json`) advanced its resume-offset by 20
rows even in `--dry-run` mode — a property of that script's own
checkpoint design (dry-run protects the `markets` table, not its own
progress-tracking state), unrelated to this Stage 0 change, and the same
file was already showing routine daily-churn modifications before this
verification ran.

---

## What did not implement cleanly as specified

**Nothing required stopping.** Two places where the design's prose
under-specifies an exact mechanical detail were resolved via the most
directly textually-supported reading rather than treated as a blocker —
both recorded in `monitoring/resolution_writer.py`'s own docstring (not
just here) so a future reader hits the reasoning at the point of the
ambiguity, not only in this session's writeup:

1. `hydration_fill`'s exact numeric rank (A1 lists it in the Rank-2 row's
   "Writers using it" column, not as a separate labeled tier) — resolved
   as Rank 2, tied with `gamma`/`manual_verified`, no special-cased
   comparator branch.
2. The rank of an existing, untagged (`resolution_evidence_source IS
   NULL`) `resolved=1` row — not explicitly given a rank anywhere in the
   design text — resolved as lower than every real evidence source, the
   only reading consistent with the migration sequence (§G) being able to
   proceed writer-by-writer at all.

The SQLite `ALTER TABLE ADD COLUMN` + `CHECK` constraint concern the task
explicitly flagged as a possible stop condition **did not materialize** —
tested empirically before touching production, worked cleanly.

---

## Summary

| Item | Status |
|---|---|
| Backup | `backups/markets_20260819_204109.db`, 16,413.1 MB, integrity-verified |
| Schema | 3 columns added, nullable, `CHECK` constraint enforced, zero backfill |
| Trigger | `trg_resolved_no_unresolve` created, non-tautologically verified against live production (rolled back) |
| Function | `monitoring/resolution_writer.py`, called by nothing, 26/26 unit tests pass, falsifiability demonstrated |
| Invariant | `check_resolution_write_atomicity`, Tier 0/OBSERVE, count=0, promotion condition in the docstring as code, not prose-only |
| Verification (a)–(f) | All six passed; no new test failures; no unintended production writes from any verification step |
| Scope | Exactly the 4 things asked for; no writer migrated; `trg_require_recorded_at` not created; no CI lint rule built; no backfill |

---

*Generated 2026-08-19. Sources: `2026-08-19-canonical-resolution-write-design.md`
(`73ca92e`), `2026-08-19-canonical-design-open-questions.md` (`c75a906`),
`scripts/migrate_stage0_resolution_columns.py`,
`monitoring/resolution_writer.py`, `tests/test_mark_market_resolved.py`,
`scripts/audit_invariants.py`, live production DB queries and
transaction-rolled-back trigger tests, a scratch-schema writer-path test
(no production data), and full `run_tests.py` / `audit_invariants.py`
runs. Backup at `backups/markets_20260819_204109.db`.*
