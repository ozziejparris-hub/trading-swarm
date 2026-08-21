# 2026-08-21 — `resolution_sweep.py` freshness predicate: FIXED

**All pre-flight measurements matched expectations exactly, no surprises;
implemented, verified, committed.** Context: `2026-08-21-step3-stop.md`
(`5257f80`), `2026-08-21-resolution-sweep-predicate-fix-stop.md`
(`6ab0c75`). Oscar's decision: `COALESCE(resolution_recorded_at,
last_checked)` — the enforced, structurally-guaranteed write-time column
first, the convention-only one as fallback. Every claim tagged **[V]**
(verified this session, command/file:line given) or **[I]** (inferred,
marked explicitly).

---

## Pre-flight — measured before any edit

### (a) Three candidate sets, full population (unscoped — `resolved=1` + the freshness test only, per the task's own literal predicate)

| Set | Predicate | Count |
|---|---|---|
| 1 — current | `resolution_date >= now()-7d` | **140** |
| 2 — naive | `last_checked >= now()-7d` | **215** |
| 3 — proposed | `COALESCE(resolution_recorded_at, last_checked) >= now()-7d` | **216** |

Pairwise symmetric differences [V]:

| | in first, not second | in second, not first |
|---|---|---|
| 1 vs 2 | 10 | 85 |
| 1 vs 3 | 9 | 85 |
| 2 vs 3 | 0 | 1 |

**Matches the stated expectation exactly: Set 3 closely resembles Set 2
(216 vs 215, differ by exactly 1), not Set 1.** With
`resolution_recorded_at` populated on only 13 rows, almost every row
falls through to the fallback, as predicted — the model was not wrong.

**Set 2 vs Set 3, the interesting pair:** Set 3 = Set 2 plus exactly one
row, never fewer. Identified [V]: the one live `hydration_fill` row —
`resolution_recorded_at = 2026-08-20 17:32:09` (accurate, yesterday),
`last_checked = 2025-12-11 11:06:19` (~8 months stale). **This is the
self-healing benefit made concrete**: the naive `last_checked`-only
predicate would have missed this genuine, recent resolution; the
proposed predicate recovers it via the enforced column.

**Set 1 vs Set 3's 9 (not 10) "lost" rows** — one fewer than Set 1 vs Set
2's 10, because that same `hydration_fill` row is also rescued here.
Confirmed [V]: the remaining 9 are all `historical_backfill`,
`resolution_date` in **2026-11 to 2028-11 — the future** — a pre-existing
data-quality artifact (a market flagged `resolved=1` with a nonsensical
future resolution_date, unrelated to this fix), not a genuine loss.
Flagged, not chased further — out of this task's scope.

### (b) The 85 semantically-wrong rows — confirmed to survive, as expected

**[V]** All 85 rows from the prior stop's finding are still present in
Set 3 (`in 3 not 1` = 85, same count, same composition:
`resolution_evidence_source` blank for all — `background_backfill: 22,
historical_backfill: 2, live_monitoring: 61`). Every one enters via the
`last_checked` fallback (`resolution_recorded_at IS NULL` for all 85,
confirmed) — none are rescued or excluded by the COALESCE, exactly as
expected. **Stated explicitly, not left to be discovered later: this is a
known, accepted limitation of the transitional form.** Using
`last_checked` as any part of the predicate inherits its "last touched,
not last resolved" imprecision for every writer that has not migrated to
`mark_market_resolved()`. The fix improves accuracy where the enforced
column exists; it does not and cannot fix the fallback's own imprecision
for legacy writers.

### (c) NULL handling

**[V]** `last_checked` NULL rate across the resolved population:
**0 / 224,981** — never NULL (schema `DEFAULT CURRENT_TIMESTAMP`).
Rows where **both** `resolution_recorded_at` and `last_checked` are NULL,
among resolved markets: **0**. `SELECT COALESCE(NULL, NULL) IS NULL` → 1
(true) — confirming SQLite's semantics: a `WHERE COALESCE(...) >= ?`
comparison against a NULL result is itself NULL, which SQL treats as
non-matching — such a row would be **excluded**, not admitted and not an
error. Moot in today's data (0 such rows) but confirmed safe rather than
assumed.

### (d) Self-healing, quantified

**[V]** `resolution_recorded_at` populated on **13** rows today (12
`gamma`, 1 `hydration_fill` — the two writers migrated to
`mark_market_resolved()` so far: `fast_resolution_check.py`'s Gamma pass
and `hydrate_stub_markets.py`'s assertion branch). **Of Set 3's 216
candidates, 13 (6.0%) resolve via the reliable column; 203 (94.0%) fall
back to `last_checked`.** Today's improvement is real but small in
fraction — a number, not a claim — and grows only as more writers migrate
(step 3, Stage 3, and any future canonical-path migration each add to the
13). Not scheduled here; named as the condition under which the
transitional form becomes unnecessary (see closing note).

### (e) Runtime and output volume

**[V]** Scheduling re-confirmed, correcting the earlier report's own
correction rather than re-introducing the error: `resolution_sweep.py`
runs **only** via `daily_maintenance.py`'s "Resolution sweep" step — no
weekly cron. **The actual scoped query** (the script's own WHERE clause,
including its `trades.market_category IN ('Geopolitics','Elections')`
join with the ≥3-trades/majority-geo `HAVING` clause) currently selects
**8 markets → 57 markets**, a much smaller absolute scale than the
unscoped Set 1→3 comparison above (140→216) because the trades-category
join filters most of the unscoped population out. **57 markets is well
within a scale this script already handles routinely** — each market
triggers one `positions` query and a handful of trader-classification
lookups; 57 vs 8 is a 7x increase in iteration count for step [2/4], not
a change of order of magnitude that risks the daily maintenance window.
Output volume (traders added/promoted) increased from 0 new / 0 promoted
(today's dry run) to 0 new / **5** promoted — a modest, expected increase
consistent with more markets being correctly recognized as resolved.

**All pre-flight measurements matched the stated expectations. No
surprise. Proceeded to the edit.**

---

## The change

Baseline from git, not transcribed [V]:
```
git log --oneline -3 -- scripts/resolution_sweep.py
  e9a0669 feat: wire data_source into all 4 traders write paths
  c6f70ce fix: resolution_sweep stricter category filter — majority geo trades required
  532e0b2 fix: resolution_sweep use trades.market_category instead of markets.category
```
Confirmed working tree byte-identical to `e9a0669` before editing (`diff`
against `git show HEAD:...`, zero output; `sha256sum` match). Copied
verbatim into
`data/characterizations/resolution_sweep_predicate_fix/resolution_sweep_baseline_e9a0669.py`
(committed).

**Predicate only, nothing else touched:**
```diff
 WHERE resolved = 1
-  AND resolution_date >= datetime('now', ?)
-  AND resolution_date <= datetime('now')
+  AND COALESCE(resolution_recorded_at, last_checked) >= datetime('now', ?)
+  AND COALESCE(resolution_recorded_at, last_checked) <= datetime('now')
   AND market_id IN (
```
Plus a 6-line comment above the query explaining the freshness gate and
citing this doc. `ORDER BY resolution_date DESC` — unchanged, per
"touch nothing else": it sorts the *printed* list by event-time, which is
a display concern, not the freshness predicate this task was scoped to.
The `SELECT` column list, the trader-classification logic, the
new/promote/already-flagged accounting, and every other line in the file
are untouched.

---

## Verification

**(b) Before/after selected-market-set comparison, full population, at
the script's own real (scoped) query** — not the unscoped Set 1-3 table,
which is a simplified proxy the pre-flight instructions themselves
specify; this is the actual query the script runs:

| | Count |
|---|---|
| Current (scoped) | 8 |
| Proposed (scoped) | 57 |
| Overlap | 8 |
| Removed | **0** |
| Added | **49** |

**Every one of the original 8 survives — zero regressions in this
specific population.** All 49 added markets are admitted **exclusively**
via the `last_checked` fallback (`resolution_recorded_at IS NULL` for all
49, confirmed by direct query) — none via the reliable column, consistent
with (d)'s finding that only 13 rows anywhere carry
`resolution_recorded_at`, and none of those 13 happen to fall outside
what `last_checked` alone would already have caught in this narrower,
category-joined population. **Every difference is attributable to the
predicate change**: the added 49 are precisely the geo/elections-relevant
subset of the 85 "recently touched, not recently resolved" rows named in
the prior stop, now correctly (if imprecisely, per (b) above) included by
design; no row's inclusion is explained by anything other than the
freshness column swap.

**(c) Dry-run before and after** — the script supports `--dry-run`
natively; ran it, unmodified then modified, both `--days 7`:
- Before: `Markets resolved (last 7d): 8`, `Total qualifying traders: 29`,
  `New: 0`, `Promoted: 0`, `Already flagged: 29`.
- After: `Markets resolved (last 7d): 57`, `Total qualifying traders: 77`,
  `New: 0`, **`Promoted: 5`**, `Already flagged: 72`.
Both runs confirmed `(DRY RUN — no writes)` in their own output. No write
mode was ever invoked.

**(d) `run_tests.py`**: **16 files run, 15 passed, 1 failed
(`test_backtest_window_population.py`, 24 tests, 19 passed)** — matches
the standing baseline exactly, no new failure.

**(e) Confirm no production write**:

| | Before | After |
|---|---|---|
| `resolution_evidence_source='gamma'` | 12 | **12** |
| `resolution_evidence_source='hydration_fill'` | 1 | **1** |
| `check_resolution_write_atomicity` | 0 | **0** |
| `traders WHERE discovery_source='resolution_sweep'` | 0 | **0** |

Unchanged across all four — including the `traders` table itself, this
script's actual write target, confirmed directly rather than inferring
"dry-run means no writes" from the flag alone.

---

## Commit

One commit: `scripts/resolution_sweep.py` (predicate + explanatory
comment only) plus verification artifacts under
`data/characterizations/resolution_sweep_predicate_fix/` (git baseline
copy, pre/post dry-run captures). Cleanly revertible — `git revert`
restores the `resolution_date`-only gate in one step.

---

## Closing note — this is a transitional form, not a destination

The COALESCE predicate is expected to be **retired**, not maintained
indefinitely, once `resolution_recorded_at` coverage is broad enough that
the `last_checked` fallback (and its known 85-row-shaped imprecision) is
no longer load-bearing for this sweep's accuracy. **That condition is
named, not scheduled**: it is reached when every live resolution writer
has migrated to `mark_market_resolved()` (Stage 3 of the canonical arc,
plus step 3 of the discovery-gap closure once its own separate blocker is
resolved) — at which point `resolution_recorded_at` alone, with no
fallback, becomes the correct predicate and this transitional form can be
simplified away. Not proposed as a scheduled follow-up here.

---

*Generated 2026-08-21. Implemented and verified — every pre-flight
measurement matched its stated expectation; every verification gate
passed on the first attempt. No production write occurred at any point
in this session. Sources: `scripts/resolution_sweep.py` (before:
`e9a0669`; after: this session's commit), live DB queries this session
(three-candidate-set measurement, symmetric differences, self-healing
row identification, NULL-rate confirmation, scoped before/after
comparison), `run_tests.py` output, `2026-08-21-step3-stop.md`
(`5257f80`), `2026-08-21-resolution-sweep-predicate-fix-stop.md`
(`6ab0c75`), `2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`)
(all trading-swarm except the first-repo script cited).*
