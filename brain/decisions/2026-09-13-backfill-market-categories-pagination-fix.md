# Fixing backfill_market_categories.py's OFFSET pagination skip-drift

Follows: the daily_maintenance.py audit (trading-swarm, this session's
audit doc, `brain/decisions/2026-09-13-daily-maintenance-audit.md`),
which found and flagged this bug but did not fix it (read-only audit).
This task fixes exactly the one mechanism named there.

Code change: first-repo `scripts/backfill_market_categories.py`. Tests:
`tests/test_backfill_market_categories_pagination.py`, wired into
`run_tests.py` via the standard glob. **One small, real verification run
was executed against production** (`--limit 20`), per this task's
explicit instruction — this is the one task in this recent run of audits
where a live write was directed and appropriate, not a violation of the
usual read-only default.

---

## Part 1 — confirming and quantifying the bug before changing anything

**The audit's characterization is correct in every detail. Quoting both
mechanisms directly from the pre-fix code:**

`fetch_batch()` (original):
```python
def fetch_batch(conn: sqlite3.Connection, offset: int, batch_size: int) -> list[dict]:
    keyword_clause = build_keyword_where()
    sql = f"""
        SELECT market_id, title
        FROM markets
        WHERE category = 'Unknown'
          AND title IS NOT NULL
          AND {keyword_clause}
        ORDER BY market_id
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(sql, (batch_size, offset)).fetchall()
```

The checkpoint write (original, three call sites — success, Ollama-call
failure, and commit failure — all identical):
```python
state["last_processed_offset"] = offset + len(markets)
```

`offset` always advances by the raw count of rows *fetched*, never by
the count of rows that actually left `WHERE category='Unknown'`. Since
every successful classification removes a row from that set, any batch
containing a mix of classified and still-Unknown rows causes the
still-Unknown ones to permanently fall below the next `OFFSET` value —
found on ordinary successful runs, not only crashes, exactly as the
audit stated. **Additionally established this pass, extending the
audit's finding**: the same drift also occurs, even more severely, on
an Ollama-call failure or a commit failure — those paths advance the
offset by the *full* batch size while *zero* rows leave the set,
guaranteeing every row in that batch is permanently skipped with no
classification attempt ever made.

**Checkpoint file read (before any change)**:
```json
{"last_processed_offset": 20564, "total_classified": 12205, "total_skipped": 8339, "errors": 1}
```

**Quantified drift** — a direct query replicating the exact predicate
`fetch_batch()` uses, checking how many currently-matching rows sit at
a position below the live offset:

```sql
SELECT COUNT(*) FROM (
    SELECT market_id FROM markets
    WHERE category='Unknown' AND title IS NOT NULL AND (<keyword clause>)
    ORDER BY market_id LIMIT 20564
)
```
→ **20,564** — every single one of them, meaning the offset had already
outpaced the entire currently-matching set up to that position. Total
rows matching the same predicate (`category='Unknown' AND title IS NOT
NULL AND <keyword filter>`): **30,315**. **67.8% of the addressable
backlog was already permanently unreachable** before this fix — cross-
validated against the checkpoint's own arithmetic: `12,205 classified +
8,339 skipped + ~20 (the one error-batch, unclassified) ≈ 20,564`,
consistent to within one batch.

Total `category='Unknown'` markets with no keyword filter applied:
**864,515** — the keyword-filtered, addressable-by-this-script subset
(30,315) is a small fraction of the full Unknown population; see Part 4
for why that distinction matters to the effect statement.

---

## Part 2 — the fix

**Chosen: keyset pagination on `market_id` (`WHERE market_id > last_seen_market_id`), not the task's suggested "always take the first N" (OFFSET 0 every time).**

**Why "always OFFSET 0" was rejected, not just accepted at face value**:
`market_id` is `TEXT PRIMARY KEY`, and it is a content-hash-shaped string
(`0x00000977...`), confirmed by direct inspection — **not sequential,
not chronological, not correlated with insertion order**. Under a
"always take the first N by `market_id` order" scheme, any market whose
titles genuinely and correctly resolve to `Unknown` (the 40.6%
historical skip rate: 8,339 of 20,544 processed so far) stays in the
matching set forever and keeps sorting into the same low position on
every future run. With enough such rows sitting at the front of the
hash-ordered list — plausible given the ~40% skip rate — "always take
the first N" would converge to endlessly re-evaluating the same
already-rejected rows and **never make forward progress into the rest
of the 30,315-row backlog at all**. This is a different, but equally
real, failure mode from the one being fixed, so it was rejected in favor
of a scheme that guarantees forward progress regardless of how many rows
in a given batch get classified versus skipped.

**The fix**: `fetch_batch()` now takes `after_market_id` (`str | None`)
instead of `offset` (`int`), and the query becomes `WHERE ... AND
market_id > ? ... ORDER BY market_id LIMIT ?` (or no `market_id`
predicate at all when `after_market_id is None`, i.e. the very first
batch). After processing each batch — success, Ollama failure, or
commit failure, matching the original code's practice of always
advancing past a bad batch rather than retrying it forever — the cursor
advances to `markets[-1]["market_id"]`: the highest `market_id` actually
fetched in that batch, regardless of what happened to each individual
row. Since `market_id` values are never reused or renumbered, this
cursor cannot be invalidated by rows entering or leaving the matching
set around it, unlike a position count.

**One additional, deliberate design element beyond the literal ask,
justified explicitly**: when a fetch returns zero rows (the cursor has
reached the current end of the matching set), the cursor is reset to
`None` — wrapping back to the beginning — rather than left pinned at
that value forever. Reasoning: `market_id` being a non-chronological
hash means a *newly created* market entering `category='Unknown'`
tomorrow could sort to any position, including "behind" wherever the
cursor currently sits. Without a wrap, such a market would be
permanently unreachable the moment the cursor passes its position —
reintroducing a version of the same "some rows never get processed"
problem this fix exists to close, just via new arrivals instead of
shrinking-set drift. This does not happen soon in practice (the cursor
is nowhere near the current end of a 30,315-row set), so it does not
affect the near-term verification below, but it closes a gap that pure
forward-only keyset pagination would otherwise carry indefinitely.

**Ordering with the concurrently-writing live monitor**: no other code
in either repository writes `markets.category` (confirmed by grep, and
consistent with the relevance classifier's own docstring, which
explicitly defers that responsibility elsewhere and was never picked
up — see the 2026-09-13 built-never-connected sweep). There is
therefore no other writer this step's `UPDATE` statements could race
against for the specific column they touch; the monitor's own,
unrelated writes are handled by SQLite's normal WAL concurrency and the
existing `busy_timeout=30000`, unaffected by this fix. **A row could in
principle be processed twice** — via the wraparound once the whole set
has been swept, or via a rare manual state-file reset — and this **does
not matter**, because `apply_classifications()`'s `UPDATE ... WHERE
market_id = ?` statements are unconditional overwrites: applying the
same classification twice sets the same value twice, with no counter or
side effect that accumulates. Confirmed directly in Part 3, Section 3.

**The checkpoint**: `last_processed_offset` is **not migrated, not kept
for appearance — deliberately dropped**. `load_state()` now reads
`last_seen_market_id` (defaulting to `None`) and explicitly ignores any
`last_processed_offset` key found in an old-format state file. A
pre-existing checkpoint written before this fix has no value that could
be meaningfully translated into a `market_id` cursor — the old field
recorded a position in a set shape that no longer exists in the new
scheme. Starting `last_seen_market_id` at `None` is not a fallback of
convenience; it is the *only* way to reach the 20,564 rows the bug had
already made permanently unreachable, which is the entire point of this
fix. `total_classified`, `total_skipped`, and `errors` are preserved
as-is — they are informational lifetime counters, not part of the
pagination mechanism, and are unaffected by the schema change.

**Constraints respected**: batch size (`DEFAULT_BATCH_SIZE`),
`KEYWORD_FILTER`, `CLASSIFY_PROMPT`, `call_ollama()`, and
`apply_classifications()`'s classification decision logic were not
touched — confirmed by `git diff`, which shows changes only in
`load_state()`, `fetch_batch()`'s pagination mechanism, and `main()`'s
cursor bookkeeping. `daily_maintenance.py`'s invocation
(`["--limit", "50"]`, step "Backfill market categories") was not
touched.

---

## Part 3 — verification

**1. Bug reproduced** (`tests/test_backfill_market_categories_pagination.py`,
Section 1): a 10-row in-memory fixture (`m01`..`m10`, lexically ordered,
mirroring `market_id`'s `TEXT PRIMARY KEY` shape), using a local
reimplementation of the *original* OFFSET-based `fetch_batch()` (the
shipped code no longer contains this logic, so reproducing the bug
requires keeping the old shape inline in the test, clearly labeled as
such). Batch 1 (`offset=0`) fetches `m01..m05`; simulating a mixed
outcome (`m01`, `m03` reclassified out, `m02`/`m04`/`m05` stay Unknown)
shrinks the set to 8 rows. Batch 2 (`offset=5`) against the new 8-row
ordering returns `m08, m09, m10` — **`m06` and `m07` are fetched in
neither batch**, reproducing the exact skip the audit described, on a
fixture small enough to reason about by hand.

**2. Fix demonstrated** (Section 2): the identical fixture and identical
mixed-outcome simulation run through the actual shipped
`bmc.fetch_batch()`. All of `m06`-`m10` are reached; every `market_id`
across all batches appears exactly once; `m01`/`m03` (reclassified after
batch 1) correctly never resurface in any later batch. A test that
could pass regardless of which pagination logic ran would prove
nothing — Section 1's assertions are written against the *old* logic
specifically and fail if pointed at the fix (verified: an earlier draft
of one assertion had a slicing bug that initially failed even against
the correct fix, catching a mistake in the test itself before the
assertion was corrected — the test process itself functioned as
intended).

**3. Idempotency confirmed** (Section 3): `apply_classifications()`
applied twice, back to back, to the same market with the same
classification result. Both applications report `classified=1,
skipped=0`; `markets.category` and `trades.market_category` both read
`'Geopolitics'` after the first application and are unchanged (not
corrupted, not double-counted anywhere outside the function's own
return value, which isn't persisted) after the second.

**4. Live verification run against production** (`--limit 20`, one
batch — small, per the task's explicit instruction not to run a large
backfill):

| | Before | After |
|---|---|---|
| `category='Unknown'` + keyword-matching total | 30,315 | 30,305 |
| Checkpoint | `{"last_processed_offset": 20564, "total_classified": 12205, "total_skipped": 8339, "errors": 1}` | `{"last_seen_market_id": "0x001ea672...731175e85", "total_classified": 12215, "total_skipped": 8349, "errors": 1}` |

10 markets classified (`Geopolitics`/`Elections`, all `HIGH` confidence),
10 skipped (remained `Unknown`, correctly — titles like weather/sports/
entertainment that matched a keyword coincidentally, e.g. "highest
temperature in Warsaw," "LoL: EDward Gaming vs Team WE"). Spot-checked
two classified rows directly against both `markets.category` and
`trades.market_category`: both correctly updated to `Geopolitics`.

**All 20 processed rows were drawn from the previously-permanently-
unreachable set** — confirmed by capturing the first 30 `market_id`s in
keyword-matching-`Unknown` order *before* the run (all guaranteed to sit
below the old `offset=20564`, since 30 ≪ 20,564) and observing the run's
new cursor (`0x001ea672...`) exactly matches the 20th entry of that
captured list. **The drifted rows are now reachable — demonstrated, not
asserted.**

**Stop condition check — classification behavior unchanged, confirmed
by construction, not just by absence of contrary evidence**: `git diff`
on this change touches only `load_state()`, `fetch_batch()`'s
pagination predicate, and `main()`'s cursor tracking. `call_ollama()`,
`CLASSIFY_PROMPT`, `KEYWORD_FILTER`, and `apply_classifications()`'s
decision logic (`confidence != "HIGH" or category not in (...)`) are
byte-for-byte unchanged. The live run's classifications (10
Geopolitics/Elections, 10 correctly-still-Unknown) are what the
identical prompt/model/parsing code would have produced for these
titles regardless of how they were selected — nothing about *how* a
fetched row gets classified changed, only *which* rows get fetched.

Full test suite (`run_tests.py`, `--skip=test_behavioral_integration.py`)
run after the change: **27/27 files passed, 339,936/339,936 individual
tests passed**, including the new file
(`test_backfill_market_categories_pagination.py`, 10/10). No
regressions. `metric_v2f_oos_result` sha256 re-checked immediately
after the live verification run and again before this commit: unchanged
(`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`) —
expected, since this fix touches only `markets.category` and
`trades.market_category`.

---

## Part 4 — the honest effect statement

**How many previously-unreachable rows does this restore?** 20,564 at
the moment the bug was measured (Part 1); 20,544 remain after this
session's own small (`--limit 20`) verification run touched the first
20 of them. All are now reachable by the ordinary daily
`daily_maintenance.py` step going forward, with no special recovery
action needed — the fix is self-healing by design, exactly as scoped.

**Does this change the ~19-32/day throughput?** **No — and it isn't
supposed to.** `daily_maintenance.py` invokes this step with `["--limit",
"50"]`, unmodified by this fix. The fix changes **which** ~50
markets get evaluated each day (a correct, monotonically-advancing
sweep instead of one that silently strands most of the backlog below an
ever-rising, effectively-arbitrary cutoff), not **how many**. The
per-day pace is set entirely by `--limit` and this fix does not touch
it, per the explicit constraint.

**Is the backlog now genuinely finite and shrinking, or still
effectively unbounded at this rate?** For the specific, keyword-filtered
subset this script can ever address (30,305 rows remaining as of this
run): at up to 50/day, clearing the *current* snapshot of that subset
is **~606 days (~1.66 years)** — a large but now genuinely finite,
monotonically-decreasing number, which it was **not** before this fix
(20,564 of those rows would never have been reached at all, at any
rate, indefinitely). **Whether it stays finite in practice depends on
how fast new keyword-matching `Unknown` markets are created** — that
arrival rate was not measured this pass; if new matching markets appear
faster than 50/day on average, the backlog would still grow net-of-
clearance regardless of this fix, which only guarantees no row is
permanently stranded, not that the queue shrinks to zero.

**This script's addressable backlog is not the same number the task's
own framing referenced.** `category='Unknown'` with no keyword filter
stands at **864,515** markets database-wide — the 30,315 figure this
script can ever touch is a filtered subset (titles matching one of 38
political/geopolitical keywords) of a much larger, structurally
different population, most of which is presumably genuinely non-
political and was never in scope for this script regardless of the
pagination bug. This fix restores this script's ability to do the job
it was built for, on the population it was built to cover — it does not
and cannot address the much larger unfiltered `Unknown` count, which is
a separate, unrelated problem (the relevance-classifier gap named
elsewhere in this project's record).

---

## What was not determined

- The rate at which new keyword-matching `category='Unknown'` markets
  are created — needed to know whether the ~606-day clearance estimate
  is realistic or optimistic; not measured this pass.
- Whether any of the 20,544 still-stranded rows (beyond the 20 touched
  in the live verification run) have titles that would classify
  differently today than they would have on the day they first became
  stuck (e.g. an ambiguous election that has since resolved and no
  longer reads as politically live) — not checked; irrelevant to this
  fix's correctness (classification is decided fresh each time a row is
  actually evaluated, regardless of when it first entered the backlog),
  but worth naming as a reason the *content* of what gets reclassified
  going forward may differ subtly from what it would have been had the
  bug never existed.
