# 2026-09-07 — `test_backtest_window_population.py` chronic failure: diagnosis

**Diagnosis only. No fix, no re-baseline, no test/snapshot/function edit, no
register entry.** Scope was: establish what the 5 failing assertions measure,
explain each delta on its own evidence, and rule on whether
`backtest_window_sql()` itself is still correct.

Tagging: **[V]** verified this session (query/command run directly), **[I]**
inferred, **[U]** undetermined — evidence does not distinguish.

---

## VERDICT (read first)

**`backtest_window_sql()` is correct and unchanged. This is authoritative
call (a): the test's hardcoded Section-2 expectations are stale.** None of the
5 failing assertions (T2, T2b, T2c, T2d, T2f) call `backtest_window_sql()`.
They compare a **frozen 2026-07-24 snapshot** against a **live, growing
`resolution_date`-based query** (`old_method_market_ids()`), and every one of
the four numeric deltas is that live query accreting markets under a fixed
reference. The canonical function is anchored on `MAX(trades.timestamp)` and
`resolved=1`, reads `resolution_date` for debug only, and its live population
at `window_start=2025-11-01` has only grown since the freeze (4,712 → 5,361),
with the frozen snapshot a clean subset of it (0 members dropped). **[V]**

**No STOP condition triggered.** `backtest_window_sql()` matches its
specification (column_definitions.py Section 6). The frozen snapshot
`bt_pop_2025-11-01_v1` is intact (exactly 4,712 rows, `sql_version='1'`,
untouched) — so this is **not** call (b) either.

**The `-2` (T2b 54 → 52) is fully explained and is not a population
shrinking.** `false_negatives = snapshot − old` is a set difference with a
frozen minuend and a monotonically growing subtrahend (measured: `left old:
0` across the entire freeze→now period). Two specific markets got a
previously-NULL `resolution_date` backfilled between 2026-07-24 and
2026-08-11, which moved them from `snapshot − old` into `snapshot ∩ old`. The
frozen snapshot itself never changed. **[V]**

---

## Why this test matters (context, not disputed)

`backtest_window_sql()` is the canonical backtest-window population function.
`MASTER_HANDOVER_2026-08-15` §6.8 records that production consumers routinely
bypass it: v2f computes its own `tape_end` (`build_tape_end_map`) and anchors
on `positions`; the directional harness uses entry-time windowing; the
2026-09-06 PIT legal-pool script was the first code to actually call the
canonical function. A permanently-red test on this function would mean no
signal if it genuinely broke. The finding below is that the test's *live
invariant* assertions (T2L-1, T2L-2, T3, T4, T5, T6) do cover the function
and all pass — it is only the *hardcoded-count* assertions that are stale.

---

## PART 1 — What each failing assertion measures

All five live in `run_tests()` SECTION 2, "SNAPSHOT reconciliation". They use
three sets:

- `snapshot` — `SELECT market_id FROM backtest_population_snapshots WHERE
  snapshot_id = 'bt_pop_2025-11-01_v1'`. **Frozen.** 4,712 rows, all
  `generated_at = 2026-07-24T18:54:00Z`, `sql_version = '1'`, `window_start =
  '2025-11-01'`, `window_end = NULL`. Created by `scripts/snapshot_backtest_population.py`
  in commit **`cfbc1cd`** (2026-07-24 19:03:18Z). **[V]**
- `old` — `old_method_market_ids(conn, '2025-11-01')`, i.e. `SELECT market_id
  FROM markets WHERE category IN ('Geopolitics','Elections') AND resolved = 1
  AND resolution_date >= '2025-11-01' AND (trade_gap_flag = 0 OR
  trade_gap_flag IS NULL)`. **Live.** The legacy pre-canonical selector, kept
  in the test only as a before/after foil. Value today: **6,532** (was 5,786
  at freeze). **[V]**
- `snapshot` vs `old` partitions: `agree = snapshot ∩ old`; `false_negatives
  = snapshot − old`; `old_only = old − snapshot`, sub-split by
  `MAX(trades.timestamp)` into `zero_trade` (NULL) and `false_positives`
  (`< '2025-11-01'`).

| Assert | Exact computation | Population, plain terms | Expected value — source | Ever verified correct? |
|---|---|---|---|---|
| **T2** | `len(snapshot & old) == 4658` | Markets in *both* the frozen tape_end population *and* today's legacy resolution_date filter | Hardcoded literal `SNAPSHOT_AGREE_WITH_OLD = 4658`, added in `cfbc1cd`, never changed | **No.** Captured from the `cfbc1cd` run. Only cross-check is the internal sum `4658 + 54 == 4712`. |
| **T2b** | `len(snapshot - old) == 54` | Frozen-population markets the legacy filter *misses* today (early / NULL `resolution_date`) — "false negatives" | Hardcoded literal `SNAPSHOT_FALSE_NEGATIVES = 54`, `cfbc1cd`, unchanged | **Partially.** "excludes 54 markets" also appears in `BACKTEST_WINDOW_RATIONALE` (column_definitions.py, same era) — a documentation cross-witness at freeze. Never re-verified. |
| **T2c** | `old_only = old - snapshot`; `zero_trade = {m ∈ old_only : MAX(trades.timestamp) IS NULL}`; `len(zero_trade) == 555` | Legacy-filter markets not in the frozen population that have **no trades** — structurally dropped by the canonical INNER JOIN | Hardcoded literal `SNAPSHOT_ZERO_TRADE = 555`, `cfbc1cd`, unchanged | **No.** Test-only literal; internal sum cross-check only. |
| **T2d** | `false_positives = {m ∈ old_only : tape_end IS NOT NULL AND tape_end < '2025-11-01'}`; `len(false_positives) == 573` | Legacy-filter markets not in the frozen population whose **real last trade predates the window** — the `resolution_date`-is-wrong / bulk-backfill-contaminated class | Hardcoded literal `SNAPSHOT_FALSE_POSITIVES = 573`, `cfbc1cd`, unchanged | **Partially.** "573 (9.9%) are false positives" also stated in `BACKTEST_WINDOW_RATIONALE`. Never re-verified against ground truth (nobody hand-confirmed the 573 are genuinely mis-stamped). |
| **T2f** | assertion `len(agree) + len(zero_trade) + len(false_positives) == len(old)` | Reconciliation identity: *every* legacy-filter market is either in the frozen population, or trade-less, or a pre-window false positive | Not a literal — a derived identity. RHS `len(old)` is **live**. | The identity held with 0 remainder *at freeze only*. It silently assumes no in-window market is ever marked resolved after 2026-07-24. |

**Provenance is fully established — no STOP condition on that axis.** Every
expected value entered the tree in a single commit, `cfbc1cd`, on the same
day the snapshot was frozen. `git log -S` confirms none of the five constants
has been edited since. **[V]** They are a point-in-time capture of one run,
not an independently-derived or externally-validated reference.

---

## PART 2 — Each delta, on its own evidence

Backups of the `markets` table exist at `backups/markets_20260724_205305.db`
(≈2 h after the snapshot freeze), `..._20260820_182435.db` (pre-sweep), and
`..._20260825_201521.db` (post-sweep segment 4). Recomputing `old` against
each: **[V]**

| As of | `len(old)` | `agree` | `false_neg` |
|---|---|---|---|
| 2026-07-24 (freeze) | 5,786 | 4,658 | 54 |
| 2026-08-20 (pre-sweep) | 6,053 | **4,660** | **52** |
| 2026-08-25 (post-seg4) | 6,335 | 4,660 | 52 |
| **2026-09-07 (now)** | **6,532** | **4,660** | **52** |

`old` grew **+746** freeze→now, and the growth is **purely additive**:
`entered old: 746, left old: 0`. Decomposition of the +746:

| Bucket | Δ | tape_end | in the frozen snapshot? |
|---|---|---|---|
| `agree` | **+2** | ≥ window | yes |
| `zero_trade` (T2c) | **+20** | none | no |
| `false_positives` (T2d) | **+75** | `< '2025-11-01'` | no |
| **`in_window`** (asserted by *nothing*) | **+649** | `≥ '2025-11-01'` | no |

`+2 + 20 + 75 + 649 = 746`. **[V]**

### Delta 1 — `agree` 4658 → 4660 (+2)

The two markets are **[V]**:

- `0xd50e6c773c…` — "Will Brian Cillessen win the 2026 New Mexico Governor Republican primary election?"
- `0xf96a84e1a8…` — "Will Belinda Robertson win the 2026 New Mexico Governor Republican primary election?"

Backup trace of both rows:

| Date | `resolved` | `resolution_date` | `end_date` |
|---|---|---|---|
| 2026-07-24 | 1 | **NULL** | `2026-06-02 00:00:00` |
| 2026-08-11 | 1 | `2026-06-02T00:00:00+00:00` | `2026-06-02T00:00:00+00:00` |
| now | 1 | `2026-06-02T00:00:00+00:00` | `2026-06-02T00:00:00+00:00` |

At freeze both were `resolved=1` with `resolution_date IS NULL`, so the
legacy filter's `resolution_date >= '2025-11-01'` clause excluded them → they
sat in `snapshot − old` (false negatives). Between 2026-07-24 and 2026-08-11
a backfill **co-wrote `resolution_date` from the existing `end_date`** (with
an ISO-8601 `+00:00` reformat; `resolution_recorded_at` and
`resolution_evidence_source` remain NULL, `data_source` unchanged
`historical_backfill`, `last_checked` unchanged `2025-12-11`). `2026-06-02` ≥
`2025-11-01`, so the legacy query now includes them, moving both from
`false_negatives` into `agree`. **Mechanism: the `resolution_date` NULL-fill
/ `end_date`→`resolution_date` co-write family (O-16/O-17 lineage,
COALESCE-guarded).** Pre-dates the discovery-gap sweep — the 2026-08-20
pre-sweep backup already shows `agree=4660`. **[V]** Not sweep-attributable.
This delta reflects the *legacy method getting more accurate* (these two
genuinely concluded in-window and were wrongly excluded before), not drift in
a harmful direction.

### Delta 2 — `false_negatives` 54 → 52 (−2)

**Not a population shrinking — a set difference contracting.**
`false_negatives = snapshot − old`, with `snapshot` frozen at 4,712 and `old`
growing monotonically (`left old: 0`, measured). The two markets that left
are exactly the two NM-primary markets from Delta 1: they entered `old`, so
they left `snapshot − old`. Confirmed directly: `fneg(freeze) − fneg(now) =
{0xd50e6c773c…, 0xf96a84e1a8…}`, and `fneg(now) − fneg(freeze) = {}` (nothing
entered). **[V]** `snapshot` is unchanged — T1 (`len(snapshot) == 4712`) and
T2e (`agree + false_neg == 4712`) both still pass. The task's framing ("a
population defined by an accumulating condition should not shrink") does not
apply: this is `frozen ∖ growing`, which shrinks by construction each time
the growing set absorbs a frozen member. The remaining 52 are all
`resolution_date` in `2025-09-15 … 2025-10-31` (all `< '2025-11-01'`),
`resolved=1`, gap-clean, `resolution_recorded_at` NULL — the stable
false-negative class the tape_end method exists to rescue (Russia-advance /
Zelenskyy-Putin-meet / Dutch-coalition markets).

### Delta 3 — `zero_trade` 555 → 575 (+20)

20 markets newly in `old`, not in the frozen snapshot, with **zero trades**
(so `backtest_window_sql()`'s INNER JOIN drops them structurally — verified:
`zero_trade ∩ live canonical = 0`). Profile of the 575 **[V]**: `data_source`
= `gamma_backfill_tier2_2026-07-06` (254), `live_monitoring` (241),
`historical_backfill` (80); 45 have `resolution_date` in 2026-08 and 33 carry
`resolution_recorded_at` in 2026-08 with `resolution_evidence_source='clob'`.
**Mechanism: resolution detection catching up on trade-less geo/elec
markets** — a mix of the tier-2 gamma backfill population and Aug CLOB
resolution passes (some in the discovery-gap-sweep window) marking
never-traded markets `resolved=1` with a recent `resolution_date`. They
inflate the legacy `resolution_date` population and are correctly invisible
to the canonical function.

### Delta 4 — `false_positives` 573 → 648 (+75)

75 markets newly in `old`, not in the frozen snapshot, that **have trades but
whose real `tape_end` is `< '2025-11-01'`** — the exact "`resolution_date` is
wrong" class the tape_end anchor was designed to filter. Verified excluded
from the canonical result: `false_positives ∩ live canonical = 0`. Profile of
the 648 **[V]**: `data_source` mostly `live_monitoring` (514) +
`historical_backfill` (108); `last_checked` clusters on **`2026-04-01`
(266)** and **`2026-06-04` (122)** — the *two bulk-backfill events named
verbatim in `BACKTEST_WINDOW_RATIONALE`* (2026-04-01 16:19:1X and 2026-06-04
21:36:39) — plus 58 with `resolution_recorded_at` in 2026-08 (`clob`).
**Mechanism: more of the April/June bulk-backfill-contaminated markets having
`resolved=1` asserted over time, plus the Aug CLOB/sweep pass asserting
resolution on old-tape markets.** Growth here is expected and benign — it is
the canonical function's filter doing its job against a widening
contamination set.

### Delta 5 — the hidden `+649` that breaks T2f

T2f fails `4660 + 575 + 648 != 6532` — a remainder of **649**. These are
markets in `old`, not in the frozen snapshot, with `tape_end ≥ '2025-11-01'`
— **genuinely in-window markets that concluded and were marked resolved after
the 2026-07-24 freeze.** All 649 are in today's live canonical result
(`in_window ⊆ live canonical`, 0 missing). **[V]** Profile: `resolution_date`
224 in 2026-08 / 124 in 2026-09; `resolution_recorded_at` 164 in Aug / 133 in
Sep; evidence `clob` (289) / `gamma` (8) / none (352). They are exactly why
live `backtest_window_sql('2025-11-01')` returns 5,361 vs the frozen 4,712.
T2f's identity `agree + zero_trade + false_positives == len(old)` assumes
every `old` member is in the frozen snapshot or trade-less or pre-window —
an assumption that expires the instant any new in-window market resolves, and
6 weeks + a 215,887-row discovery-gap sweep have resolved a lot of them.

---

## PART 3 — Is `backtest_window_sql()` itself still correct?

**Yes. It is producing the population it is specified to produce, and nothing
in the last month changed its output beyond legitimate growth.**

Evidence:

1. **Code unchanged.** `BACKTEST_WINDOW_SQL_VERSION = "1"`. The function,
   `BACKTEST_WINDOW_TAPE_END_CTE`, and `BACKTEST_WINDOW_BASE_WHERE` have not
   been touched since `8470e8b` (2026-07-23) / `cfbc1cd` (2026-07-24).
   `git log` shows no commit to `monitoring/column_definitions.py`'s backtest
   section in the last month. **[V]**
2. **No version skew with the snapshot.** The frozen snapshot records
   `sql_version = '1'` — identical to the live definition. **[V]**
3. **Structural self-test passes.** `python3 monitoring/column_definitions.py`
   Section 6: all 11 checks OK — INNER JOIN on `tape_end` (zero-trade markets
   drop structurally), half-open `<` on `window_end`, inclusive `>=` on
   `window_start`, `resolved = 1`, category via `markets.category`,
   `trade_gap_flag` exclusion, `resolution_date` carries the DO-NOT-FILTER
   comment. **[V]**
4. **Live behaviour tests pass.** T3 monotonic across 4 window starts
   (6,090 ≥ 5,361 ≥ 4,381 ≥ 3,326); T6 half-open boundary; T2L-1 / T2L-2 live
   reconciliation invariants; T4 / T5 non-tautological regression guards
   (2024 Harris/Obama/Haley markets excluded; Nov-2025 Venezuela/Zelenskyy/
   Babis markets included). **[V]**
5. **Direct spec checks.** `zero_trade ∩ canonical = 0` (INNER JOIN correct);
   `false_positives ∩ canonical = 0` (`tape_end < window_start` correctly
   excluded); `in_window ⊆ canonical`, 0 missing (all genuinely in-window
   markets returned); **`snapshot ⊆ live canonical`, 0 of 4,712 dropped** —
   the function has only ever added markets since the freeze, never removed
   one. **[V]**

**Upstream data changes named in the task — effect on the canonical
function:**

- **Discovery-gap sweep's 215,887 resolutions (2026-08-22 – 08-26):** adds
  `resolved=1` + `resolution_date` to many markets. `backtest_window_sql()`
  ignores `resolution_date` entirely and only gains a market if that market
  also has `tape_end ≥ window_start`. Newly-resolved *in-window* markets
  (the +649) are correct additions; newly-resolved trade-less or old-tape
  markets are correctly not added. No unintended effect. **[V]**
- **`resolution_date` clobber fix (`2026-08-19-resolution-date-clobber-fix.md`)
  and `resolution_sweep.py` COALESCE-predicate change
  (`2026-08-21-resolution-sweep-predicate-fix.md`):** both touch
  `resolution_date` / freshness-gate semantics only. The canonical function
  reads neither. Zero effect on its output; they *are* the driver of Deltas
  1, 3, 4 in the *legacy* `old` query. **[V]/[I]**
- **195,625 stranded markets with unset `last_checked`
  (`2026-09-07-stranded-markets-figure-reconciliation.md`):**
  `backtest_window_sql()` does not reference `last_checked`; neither does the
  test's `old_method`. No direct dependency. Shared upstream cause only — the
  same clob-resolved population is what is now getting `resolution_date`
  stamped and entering `old`. **[V]**

**No STOP condition. The function is behaving correctly; only the test's
hardcoded expectations are stale.**

---

## PART 4 — What is authoritative

**(a) — the test's hardcoded expectations are stale; the frozen snapshot and
the function are both fine.**

- Ruled out **(b)**: `snapshot` is exactly 4,712 rows, `sql_version='1'`,
  single `generated_at`, and T1 + T2e pass. Not tampered, not mis-captured
  for what it is (a frozen instance).
- Ruled out **(c)**: Part 3 — function unchanged, spec-conformant, output
  grew only by legitimate in-window additions, frozen snapshot is a clean
  subset of live output.
- The stale values are `SNAPSHOT_AGREE_WITH_OLD = 4658`,
  `SNAPSHOT_FALSE_NEGATIVES = 54`, `SNAPSHOT_ZERO_TRADE = 555`,
  `SNAPSHOT_FALSE_POSITIVES = 573`. All four describe the relationship
  between the frozen snapshot and the **live** `resolution_date` query *as it
  stood on 2026-07-24*. The comment above them ("fixed facts … will never
  legitimately change … if they do, the table was tampered with") is only
  true of the snapshot-only facts (`len(snapshot)`, `agree + false_neg ==
  len(snapshot)`), which is why T1 and T2e still pass. Everything that also
  depends on `old` moves whenever a geo/elec market is marked resolved with a
  `resolution_date ≥ 2025-11-01`.

### Is a count-based test the right design here? No.

T2 / T2b / T2c / T2d assert **exact integers** against `frozen_snapshot ⊕
live_growing_query`. That composite is guaranteed to drift as the database
accrues resolutions — it fails forever by construction, which is what has
happened for weeks. The irony: commit `cfbc1cd`'s own message says *"The bug
was … hardcoding an exact count against that moving query — not the
population moving,"* and then it added four more hardcoded counts against a
half-live composite.

**Proposed (not implemented) redesign:**

1. **Delete** the four hardcoded-count checks (T2, T2b, T2c, T2d) and the
   `SNAPSHOT_AGREE_WITH_OLD / _FALSE_NEGATIVES / _ZERO_TRADE /
   _FALSE_POSITIVES` constants.
2. **Keep** the assertions that are genuinely immutable or already
   invariant-shaped, all of which pass today:
   - T1: `len(snapshot) == 4712` (snapshot-only fact — legitimately fixed).
   - T2e: `agree_snap + false_neg_snap == len(snapshot)` (partition identity
     of the frozen set).
   - T2L-1 / T2L-2: the live reconciliation identities — these are the
     count-free form of T2f and already exist.
   - T3 / T6: monotonicity and half-open boundary.
   - T4 / T5: the non-tautological before/after regression guards (the part
     that actually protects the canonical function's discriminating power).
3. **Add** two cheap structural invariants that would catch a real
   regression without a moving target:
   - `snapshot ⊆ canonical_live` — every frozen market still selected by the
     live query (catches a market silently dropping out, e.g. losing its
     trades or being re-categorised). Passes today, 0 missing.
   - `len(canonical_live) >= SNAPSHOT_COUNT` — already present as T1b; keep.
4. **If a numeric regression guard is still wanted**, assert a **lower
   bound** that only ever moves on a deliberate, commented re-baseline —
   never an equality against a live set.

Re-baselining the existing four constants to today's numbers is **not**
recommended: it buys a few weeks of green and then fails identically. The
fix is to stop asserting equality against a live-composite count.

---

## What was NOT determined

1. **The exact writer/script and timestamp** that filled the two NM-primary
   `resolution_date` NULLs. Narrowed to the window **2026-07-24 → 2026-08-11**
   and to the mechanism (**`end_date` → `resolution_date` co-write with
   ISO-8601 `+00:00` reformat, COALESCE-guarded, `resolution_recorded_at`
   left NULL**). The specific job (an O-16/O-17 backfill pass vs.
   `backfill_market_dates.py` vs. a `fast_resolution_check.py` branch) was
   not pinned. **[U]**
2. **Row-level attribution** of the `+20` / `+75` / `+649` to specific causes
   (discovery-gap sweep vs. tier-2 gamma backfill vs. routine live
   monitoring). Only aggregate `data_source` and `resolution_recorded_at`
   month profiles were established; each bucket is a mix. **[U]**
3. **Whether `4658` and `555` were ever independently correct.** No external
   ground truth exists for them; only the internal sums `4658 + 54 == 4712`
   and `4658 + 555 + 573 == 5786` were ever satisfied, and those are
   self-consistency, not validation. `54` and `573` at least had a
   same-era documentation cross-witness in `BACKTEST_WINDOW_RATIONALE`. **[U]**
4. **The absolute floor** a redesigned lower-bound guard should assert — that
   needs a deliberate re-baseline decision and is out of scope for a
   diagnosis.
5. **Why the test has been skipped in reports for weeks** rather than fixed —
   organisational, not technical; noted in the task premise, not
   investigated here.

---

## Appendix — commands run this session (all read-only)

- `python3 tests/test_backtest_window_population.py` — current failure set
  (19/24 pass; T2/T2b/T2c/T2d/T2f fail; `len(old)` in T2f message = 6,532).
- `python3 monitoring/column_definitions.py` — Section 6 structural self-test,
  all OK.
- Set math (frozen snapshot vs live `old` vs live `backtest_window_sql`) via
  `sqlite3 file:…?mode=ro`: `agree=4660`, `false_neg=52`, `zero_trade=575`,
  `false_pos=648`, `in_window=649`, `old=6532`, `canonical_live=5361`,
  `snapshot ⊆ canonical_live` (0 missing).
- Same `old` recomputation against `backups/markets_20260724_205305.db`,
  `…_20260820_182435.db`, `…_20260825_201521.db` — established `entered old:
  746, left old: 0` freeze→now and isolated the two NM-primary movers.
- Backup trace of the two mover rows across 8 `markets` snapshots
  (2026-07-24 → 2026-08-31).
- `git log -S` on each of the five `SNAPSHOT_*` constants — all introduced in
  `cfbc1cd`, none edited since.

*Generated 2026-09-07. Diagnosis only — no file modified in either repo, no
production write, no register entry. Sources: `tests/test_backtest_window_population.py`,
`monitoring/column_definitions.py` (§6 + `backtest_window_sql`),
`scripts/snapshot_backtest_population.py`, live DB + `backups/markets_*.db`
(read-only), `git log`/`git show` on `cfbc1cd` and `8470e8b`,
`MASTER_HANDOVER_2026-08-15` §6.8, `2026-08-19-resolution-date-clobber-fix.md`,
`2026-08-21-resolution-sweep-predicate-fix.md` (+ its `-stop`),
`2026-09-04-limit-restore-and-sweep-closure.md`,
`2026-09-07-stranded-markets-figure-reconciliation.md`.*
