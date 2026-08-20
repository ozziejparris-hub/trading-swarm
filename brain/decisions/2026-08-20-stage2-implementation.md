# 2026-08-20 — Stage 2 implementation: `batch_update_resolved_markets`, behaviour-preserving

**Implemented, verified, committed.** Design:
`2026-08-19-canonical-resolution-write-design.md` (as amended), §A4
policy, §G Stage 2, summary table row #3. Blocking questions:
`2026-08-20-stage2-stop.md` (`d2fe369`). Stage 1 precedent:
`2026-08-20-stage1-implementation.md` (`0f9ade8`). Function:
`monitoring/resolution_writer.py` (`bc9e889`, read, not modified).
Migrated writer: `scripts/fast_resolution_check.py::batch_update_resolved_markets`
(previously `0a5891c`).

Every claim below is tagged **[V]** (verified this session, command/evidence
given) or **[I]** (inferred).

---

## What changed

`batch_update_resolved_markets` kept every existing guard, per §A4 policy 1
(migration is behaviour-preserving):

- **`if is_resolved: already_resolved += 1; continue` — kept, unchanged.**
  `mark_market_resolved()` is only called for rows this guard lets through
  (i.e. rows already confirmed `resolved=0` at the point of the call).
  Legacy-tag backfill for the ~1,600+ already-resolved-untagged rows
  remains explicitly out of scope, deferred to the separate pre-registered
  backfill task (§A4 policy 2) — not touched by this commit.
- **`if winner:` — kept, unchanged.** `extract_winner()` returning `None`
  still results in no canonical call and no write, exactly as before.
  `allow_no_winner` is not passed (defaults `False`) — irrelevant in
  practice since the call only happens when `winner` is truthy.
- **The direct `UPDATE ... SET resolved = 1, winning_outcome = ?,
  resolution_date = COALESCE(resolution_date, ?), last_checked = ?`
  replaced** with `mark_market_resolved(evidence_source="gamma",
  resolution_event_time=None, winning_outcome=winner,
  evidence_detail="outcomePrices>=0.99")`, followed by a separate direct
  `UPDATE markets SET last_checked = ?` (not a canonical-path column,
  stays a direct write, unchanged), both committed together.
  `resolution_event_time` is always `None` — the Stage 2 stop's Q1
  established this writer never holds a true Gamma event-time.
- **The `COALESCE(resolution_date, ?)` patch (`0a5891c`) is retired** —
  not replaced by a different mechanism, but by one confirmed
  behaviourally identical for this writer's inputs (Q1: `resolution_event_time=None`
  always, so the canonical three-tier fallback reduces to "keep existing
  `resolution_date` if non-null, else write-time" — the same rule the
  COALESCE patch encoded).
- **Only `batch_update_resolved_markets` touched.** `run_stale_clob_pass`,
  `run_recent_overdue_pass`, `run_external_seed_pass` (writers #4/#5/#6,
  Stage 3) are untouched — confirmed by the diff below covering only this
  one function plus the new import line.

`monitoring/resolution_writer.py` was **not modified**. No other writer
migrated. No trigger created. No `backfill_verified` value or CHECK
constraint change — that remains the backfill task's own pre-registration,
per §A4 policy 3, not touched here.

One commit in `first-repo` (see bottom).

---

## Verification (a): before/after dry-run diff, full candidate population

**Method — pre-migration behavior extracted from git, not hand-transcribed
[V]:** confirmed the working tree's baseline was `0a5891c` (`git log
--oneline -1 -- scripts/fast_resolution_check.py`), copied
`git show 0a5891c:scripts/fast_resolution_check.py` into `scripts/`
(temporary filename, so `Path(__file__).parent.parent` resolves correctly
for `monitoring/database.py` and `data/polymarket_tracker.db`), and ran a
harness that calls exactly `fetch_all_resolved_markets()` then
`batch_update_resolved_markets(resolved_markets, test_mode=True)` — Stage
2's scope only, none of the other three passes in this file. Ran the same
harness against the migrated script the same way. Deleted the temporary
copy after use.

```
diff pre_output.txt post_output.txt
EXIT CODE: 0
```

**Byte-for-byte identical**, zero lines of difference.

**Candidate/live-hit counts, both runs [V]:**
```
Resolved markets from API: 2100
[OK] Markets updated: 9
Already resolved: 1617
Not found in database: 474
API requests made: 22
```
`9 + 1617 + 474 = 2100`. Slightly different from the Stage 2 stop's
same-day read-only simulation (8 new / 1618 already-resolved) — expected
minor drift (Gamma's most-recent-2100 window moves as new markets close);
not a discrepancy in method, just the clock moving between two live reads
taken roughly two hours apart. **The Gamma pagination ceiling (§H
amendment) is confirmed again as the effective population bound:** the
fetch stops with `[ERROR] API request failed: 422` at `offset=2100` on
every run today, exactly as the design's amended §H states.

**Why this diff is clean by construction, not chance:** `mark_market_resolved()`
is called only inside `if not test_mode:` in the migrated code — in
`test_mode=True` (dry-run) it is never invoked at all, so dry-run behavior
is untouched code, identical to the pre-migration script's dry-run branch.
The diff confirms this held, it doesn't merely rely on the argument.

---

## Verification (b): no legacy backfill occurred

**Pre-write [V]:**
```
resolution_evidence_source  COUNT(*)
(NULL)                       738142
hydration_fill               1
```
Zero `'gamma'`-tagged rows before this run (expected — Stage 3 forward is
the first writer to use `evidence_source="gamma"`; Stage 1 used
`hydration_fill`).

**Post-write [V]:**
```
resolution_evidence_source  COUNT(*)
(NULL)                       738133
gamma                        9
hydration_fill               1
```
`resolution_evidence_source = 'gamma'` count is **exactly 9** — matching
the run's own `[OK] Markets updated: 9` figure precisely, **not** the
1,617 already-resolved rows also present in this run's Gamma window. NULL
count dropped by exactly 9 (738,142 → 738,133), confirming none of the
1,617 already-resolved-untagged rows were touched, read-write or
otherwise altered. **The guard held. No legacy backfill leaked.**

---

## Verification (c): backup

```
python3 scripts/backup_database.py
[BACKUP] Running online backup of data/polymarket_tracker.db to backups/markets_20260820_182435.db...
[BACKUP] Verifying integrity of backups/markets_20260820_182435.db...
[OK] Backup created: backups/markets_20260820_182435.db
     Size: 16454.6 MB
```
Location: `first-repo/backups/markets_20260820_182435.db`
(17,253,928,960 bytes). `PRAGMA integrity_check` returned `ok` before
success was reported — a failing check deletes the file and returns
non-zero; it did not. **[V]**

---

## Verification (d): live run, manual, observed, detached

```
nohup python3 run_live.py > live_output.txt 2>&1 &
disown
```
(`run_live.py` calls exactly `fetch_all_resolved_markets()` then
`batch_update_resolved_markets(resolved_markets, test_mode=False)` against
the migrated `scripts/fast_resolution_check.py` — Stage 2 scope only.)
Full output captured, final section:
```
[OK] Markets updated: 9
Already resolved: 1617
Not found in database: 474
API requests made: 22
[OK] Database updated successfully
```
Matches the dry-run prediction exactly. No `[WARN] mark_market_resolved()
did not accept ...` lines (the one new log line this migration adds) — all
9 canonical calls were accepted, consistent with every one landing on the
`prev_resolved == False` unconditional-accept branch. **[V]**

---

## Verification (e): written rows tagged correctly

All 9 rows queried directly **[V]**:
```
resolved=1, winning_outcome set (Yes/No), resolution_date == resolution_recorded_at
(both = this run's write-time, since resolution_event_time=None and
prev_resolution_date was NULL for every one of these genuinely-new
resolutions — the canonical three-tier fallback's final resort, matching
what the retired COALESCE patch would also have written),
resolution_evidence_source = 'gamma',
resolution_evidence_detail = 'outcomePrices>=0.99'.
```
All 9 confirmed correctly tagged — the first production writes through
`mark_market_resolved()` with `evidence_source="gamma"`.

---

## Verification (f): `check_resolution_write_atomicity`

```
python3 scripts/audit_invariants.py --verbose
  [○] T0  OBSERVE   0  [resolution-stage0/OBSERVE] resolution_recorded_at set without resolution_evidence_source
```
**0**, as required. **[V]**

---

## Verification (g): `trg_resolved_no_unresolve` did not fire

The live run's captured output contains exactly one `[ERROR]` line — the
expected Gamma pagination-ceiling 422 at fetch time (`offset=2100`), not a
database or trigger error. **Zero** `[ERROR] Error processing market ...`
lines (the exception handler around each market's processing, which would
catch a trigger `ABORT`). No row processed this run started `resolved=1`
(the hard-skip guard, confirmed preserved in (a)/(b) above, ensures every
call to `mark_market_resolved()` this run had `prev_resolved=False`), so
the trigger's `1 -> 0` condition was never a live possibility on this run
— consistent with, not merely inferred from, the absence of errors. **[V]**

---

## Verification (h): `run_tests.py`

```
Files  : 16 run, 15 passed, 1 failed
Tests  : 339700 run, 339695 passed, 5 failed
  FAILURES: test_backtest_window_population.py (19/24 passing)
```
**Matches the stated baseline exactly** — same file, same 5 sub-test
failures (T2, T2b, T2c, T2d, T2f), same pass count. **No new failure.**
`test_mark_market_resolved.py` passed, unaffected (expected, the function
itself was not modified). **[V]**

---

## Verification (i): branch coverage — stated plainly

**9 rows exercised the canonical path this run.** All 9 hit the same
branch Stage 1's single row hit: `prev_resolved == False` →
unconditional accept (`reason = "written"`) — no rank comparison, no
same-rank tie-break, no untagged-legacy-improvement path. This is because
the hard-skip guard (kept, per §A4) ensures `mark_market_resolved()` is
never called on a row this writer's own logic has already determined is
`resolved=1` — the exact design intent of §A4 policy 1. The other
branches remain unexercised in production by this writer:

- **Cross-rank overwrite** (a Rank-1 `clob` write outranking an existing
  Rank-2 `gamma` value) — not possible from this writer alone; requires
  Stage 3's CLOB passes to be migrated and to encounter a market this
  writer already tagged.
- **Same-rank match / same-rank disagreement** (two Rank-2 writers hitting
  the same market) — not exercised. The 1,617 already-resolved rows in
  this run's Gamma window never reached `mark_market_resolved()` at all
  (stopped by the hard-skip guard before the call), so even a same-rank
  collision with a *prior* Gamma-sourced write did not get a chance to
  fire this run. This will not become live-testable until either a future
  Stage 4 (`resolve_legendary_markets.py`/`legendary_positions_scan.py`)
  migration or a future run of this same migrated writer encounters a
  market **this writer itself** already tagged `'gamma'` in a prior run —
  which, given the hard-skip guard, can only happen if a market's
  `resolved` flag somehow reset to 0 after being tagged (not expected
  under `trg_resolved_no_unresolve`).
- **Untagged-legacy improvement** — explicitly and deliberately *not*
  exercised, by design (§A4, verification (b) above). This is the one
  branch this migration was specifically built to avoid triggering.

**No broader validation of the comparator is implied by this run.** Stage
1 validated the trivial accept branch on 1 row; this run validates the
same branch at 9 rows, and additionally validates — for the first time —
that the hard-skip guard correctly prevents `mark_market_resolved()` from
ever seeing the 1,617 rows it should not see. The ranking comparator's
harder branches (cross-rank, same-rank match, same-rank disagreement)
remain entirely unexercised in production and won't be until Stage 3/4.

---

## Weighing the "runs unattended" constraint

This writer executes nightly as `daily_maintenance.py` step 6
(`--stale-limit 500`), unsupervised. The next scheduled run will execute
this migrated code with nobody watching. What was verified today bounds
the risk of that: the dry-run diff proves the migration is behaviorally
inert relative to the pre-migration writer (same counts, same guard
behavior, same write values on the 9 genuinely-new resolutions), and the
live run's own tag-count check (verification (b)) proves the guard that
matters most for an unattended context — "don't touch the 1,617
already-resolved rows" — held in production, not just in the dry-run
simulation. The one thing tomorrow's unattended run *could* newly
encounter that today's didn't: a market that both this writer and a
same-rank writer touch in the same window with genuinely *different*
winning_outcome values (the same-rank-disagreement branch) — unexercised
today, and, per the branch-coverage statement above, not something this
verification can rule out for tomorrow.

---

## Reversibility

`git revert` the one `first-repo` commit below. Reverting restores the
direct `UPDATE`/COALESCE path exactly as it was at `0a5891c`. The 9 rows
already tagged `resolution_evidence_source='gamma'` /
`resolution_recorded_at` keep those values after a revert (the schema
isn't reverted, only the writer) — same "harmless, new columns stay
populated for rows already written" property Stage 1 established.

---

## Commits

- `first-repo`: migrates `scripts/fast_resolution_check.py::batch_update_resolved_markets`
  to `mark_market_resolved()`, hard-skip and winner guards preserved,
  `last_checked` kept as a direct write. `run_stale_clob_pass`,
  `run_recent_overdue_pass`, `run_external_seed_pass`, and
  `monitoring/resolution_writer.py` untouched.
- `trading-swarm`: this document.

*Generated 2026-08-20. No code outside `scripts/fast_resolution_check.py`
was written or modified. `monitoring/resolution_writer.py` was read, not
edited. No other writer migrated. No trigger created. No
`backfill_verified` / CHECK constraint change made.*
