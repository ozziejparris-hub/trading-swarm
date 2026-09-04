# Limit Bridge-Value Correction and Formal Sweep Closure

**Date:** 2026-09-04. Two changes, both in first-repo, both small and
revertible: (1) `backfill_market_dates.py`'s daily candidate selection now
prioritizes the Geo/Elec-tagged sub-population instead of raising `--limit`;
(2) the discovery-gap-closure sweep is declared STOPPED, not paused, and its
outstanding checkpoint/terminal-marker files are committed.

**Tagging: `[V]` verified this session (query/code/log given), `[I]`
inferred and marked as such.** Every claim in the task prompt was checked
against source documents and live DB/code state before being carried
forward — two of the prompt's own figures needed correction (§1, §2).

---

## PART 1 — THE VERIFIED HISTORY CHAIN

| Claim in the prompt | Verdict | Detail |
|---|---|---|
| `--geo-only` deliberately dropped 2026-08-21 because category-scoped selection inherited classification lag | **CONFIRMED** `[V]` | `daily_maintenance.py:402-406` (current code) states it plainly; `2026-08-21-step2-implementation.md` is the commit (`5fcbffe`). Still judged correct today — not being reversed. |
| "Same change set `--limit 2000`" | **CORRECTED** `[V]` | Two separate commits, not one. `5fcbffe` (08-21) dropped `--geo-only` **and raised** `--limit` 500→35000 in the same commit, reasoned from a 16,845/day confirmed-genuine daily-arrival maximum (2026-08-10, rowid-density method) with ~2.08× headroom. A later, separate commit (`2026-08-22-daily-limit-hold.md`) lowered 35000→2000 as an explicit temporary hold once the sweep's live risk became apparent. The daily_maintenance.py comment block merges both rationales into one, which is presumably the source of the prompt's "same change" framing. |
| Sweep paused 2026-08-26/27 pending three prerequisites for segment 5; no segment 5 document exists; checkpoints uncommitted | **CONFIRMED** `[V]` | `2026-08-27-session-summary-0825-0827.md` lines 286-297, verbatim: (a) resume segment 4's list from batch 102 — 16,000 markets materialized but never CLOB-checked; (b) re-key the exclusion derivation on *processed* IDs, not *materialized* ones; (c) implement `max_batches` from launch time per §7's rule. No file in `brain/decisions/` dated after 2026-08-27 mentions "segment 5" or resuming the sweep — checked. `data/checkpoints/segment{3,4}_checkpoint.json` and their terminal markers were untracked in first-repo as of this session. |
| 09-04 lineage doc found 2,000/390,804 = 0.51% daily scan, current-equivalent gap 75.0% vs 67.4% original | **PARTIALLY CORRECTED** `[V]` | 75.0% vs 67.4% confirmed exactly (`2026-09-04-thesis-population-lineage.md:183-190`). The 390,804 denominator does not: it's the *sweep's own* `resolved=0`-scoped predicate. `backfill_market_dates.py`'s actual non-`--geo-only` query has no `resolved` filter (`WHERE end_date IS NULL OR resolution_date IS NULL`). Live count today: **610,784** rows match it. True daily dilution is **2,000/610,784 ≈ 0.33%**, worse than the lineage doc states. The lineage doc's "244-row Geo/Elec-tagged sub-population" is likewise the stricter Q2 census predicate (category + has-trades + gap-clean + dateless-unresolved); the actually-relevant count — what the code's own `--geo-only` query draws — is **499** today `[V, live query]`. Neither correction changes the lineage doc's conclusion; both make the case for a fix stronger, not weaker. |

---

## PART 2 — THE LIMIT DECISION

### 2a. What was 35,000 actually for, and does that context still hold?

35,000 was sized for one purpose: keep the **unscoped, full** backlog from
falling behind its own daily arrival rate once the staged sweep had
*cleared* that backlog down to a steady state. The math (`5fcbffe`,
2026-08-21): a measured daily-arrival maximum of 16,845 rows, ×~2.08
headroom ≈ 35,000. Runtime at the observed 0.19-0.22s/call: 35,000 × ~0.2s
≈ 7,000s (~117 min) — comfortably inside `daily_maintenance.py`'s 3-hour
`DEFAULT_STEP_TIMEOUT` (line 122), with about an hour of margin, no
collision with the single 06:00 daily cron fire.

**That context no longer holds.** The premise was a cleared backlog. The
sweep never cleared it — segment 5 never ran, and this closure formally
stops the sweep rather than resuming it (Part 3). The backlog today
(610,784 `[V]`) is larger than the ~515,000-ish full population the sweep
started against, not smaller — the unscoped query's replacement for
`--geo-only` also pulls in ~218,000 rows that are already `resolved=1` but
merely missing dates, which the original sizing never counted. Raising to
35,000 unattended today would also reopen the exact risk the 2026-08-22
hold was written to avoid: a large, unreviewed batch of `mark_market_resolved()`
writes with none of the sweep's tranche gating, checkpointing, or abort
thresholds — nothing has changed in the 13 days since that hold to make
that safer now.

**Conclusion: 35,000 is not the right number, and no other larger number
is either, absent the sweep infrastructure the hold assumed would exist by
the time this fired.** The right fix is not a bigger flat limit.

### 2b. Limit vs. ordering — which actually restores exhaustive Geo/Elec coverage?

The lineage doc's finding is specific: the highest-priority Geo/Elec
sub-population lost *exhaustive daily coverage* when `--geo-only`'s filter
was dropped and replaced by an unscoped, unordered `LIMIT` scan
(`get_markets_to_backfill()`, `scripts/backfill_market_dates.py:186-205`,
confirmed no `ORDER BY` in either branch `[V]`).

Raising the limit does not restore that property — it only raises the
*odds* of incidental overlap. A plain `LIMIT` with no `ORDER BY` over a
610,784-row pool returns whatever the query planner's natural scan order
produces; at 35,000 that's ≈5.7% of the pool per call, still an incomplete,
non-guaranteed draw of the 499 Geo/Elec-tagged rows, and one that competes
every day with everything else in the unscoped pool for the same budget.
There's also a standing historical note against changing this query's
selection order: `2026-08-21-discovery-gap-closure-prereg.md`'s amendment
deferred adding `ORDER BY market_id` — but that was scoped explicitly to
a byte-identical-diff verification bar for a refactor in flight at the
time, not a standing prohibition on ever ordering the query. It does not
bind this change.

Ordering does restore the property directly: draw the Geo/Elec-tagged
candidates first (reusing the existing `--geo-only` query, which already
has an index-usable join), then fill remaining budget from the general
pool. At **499** tagged candidates against a **2,000** budget, this
guarantees 100% same-day coverage of the sub-population regardless of how
large the unscoped pool grows — the property `--geo-only` used to
guarantee, without reintroducing the filter's blind spot, since
unclassified/newly-classified markets still fall through to the general
pool for the rest of the budget.

**Recommendation: keep `--limit` at 2000, add priority ordering.** Ordering
is what the sweep's own root-cause finding calls for; a limit increase is a
separate, much larger-blast-radius decision (unattended write volume) that
the sweep's incompletion specifically leaves unjustified. Not defaulting to
the comment's 35,000 because it's written down — its premise didn't survive
the sweep's actual outcome.

### 2c. What was applied

`scripts/backfill_market_dates.py::get_markets_to_backfill()`: the
non-`--geo-only` branch now draws the Geo/Elec-tagged query first (up to
`limit` rows), then fills any remaining budget from the general
`end_date IS NULL OR resolution_date IS NULL` pool, excluding markets
already drawn. `--geo-only`'s own standalone behavior is untouched.
`scripts/daily_maintenance.py`'s comment block is rewritten to retire the
"35000 once the sweep has run" framing and point at this document instead
of `2026-08-22-daily-limit-hold.md` for the current reasoning; the
`extra_args=["--limit", "2000"]` call site itself is unchanged.

Verified this session, read-only: at `--limit 2000` today, the priority
query draws all 499 Geo/Elec-tagged candidates, and they occupy the first
499 rows of the combined 2,000-row result — confirmed by direct execution
of `get_markets_to_backfill()` against the live DB with no writes (no
`--dry-run`-only code path was touched; the function only issues `SELECT`s).
`run_tests.py` shows the same 5 pre-existing failures in
`test_backtest_window_population.py` before and after this change (a
population-drift artifact against a frozen snapshot, unrelated to this
script) — no new failure.

### 2d. What tomorrow's 06:00 run will actually do

`_sweep_recently_active()` evaluates to inactive today (segment 4's
checkpoint is ~9.6 days past its 1,800s recency window), so the backfill
step runs unconditionally, as it has every day since 08-23. It will draw
2,000 candidates total: the 499 Geo/Elec-tagged rows currently outstanding
(100% of them, versus 0% guaranteed and a ~0.33%-of-pool incidental chance
under yesterday's unordered scan), then 1,501 rows from the general pool.
Expected runtime is materially unchanged from today (~2000 × 0.2s ≈ 400s,
~7 minutes), well inside the 3-hour step timeout.

---

## PART 3 — SWEEP CLOSURE

**The discovery-gap-closure sweep is STOPPED. Not paused, not pending
segment 5 — closed.**

**What it achieved:** 215,887 markets resolved via the sweep's CLOB-driven
tranche/segment passes (tranche 1-2 + segments 1-4). Of those, 267
(142 Elections, 125 Geopolitics) reached the target categories — 0.12% of
the sweep's own output (`2026-09-04-thesis-population-lineage.md:126-165`).
The original 2026-08-20 finding (203 markets, the Q2 census population) is
fully closed: 203/203 resolved, categorized, gap-clean, and in the
canonical population — closed specifically by Tranche 1 (08-22), which is
an almost entirely disjoint story from the 215,887-market sweep: the 203
were already correctly tagged before the sweep touched them, while the
sweep's real target — the ~510k `Unknown`-category backlog — needed a
classifier that then failed its own recall gate
(`2026-09-03-gate-result.md`, `2026-09-04-gate-recall-diagnosis.md`).

**What it cost, and the wrong turn:** eleven days of infrastructure work
(08-20 sizing finding → 08-27 sweep pause → 08-30 category-reach diagnosis
→ classifier arc → gate failure 09-03/09-04) moved the canonical thesis
population by only ~242 markets, out of ~500 total growth over the same
window. The full wrong-turn analysis, including the specific finding that
the classification-throughput check determining the sweep's payoff was
cheap and available 9 days before it was actually run — after, not before,
the 231,000-market scope-widening it should have gated — is in
`2026-09-04-thesis-population-lineage.md` and is not restated here.

**The three segment-5 prerequisites (§1 above) are moot.** There is no
segment 5. A future reader finding `2026-08-27-session-summary-0825-0827.md`
should not treat (a) resuming segment 4's list, (b) re-keying the exclusion
derivation, or (c) implementing launch-time `max_batches` as open work —
this document supersedes that state. The 16,000-market segment-4 gap named
in prerequisite (a) is now a permanent, accepted gap in the sweep's
coverage, not a pending item.

**What remains genuinely useful from the arc, independent of the sweep's
outcome:**
- The canonical resolution write path, `monitoring/resolution_writer.py::mark_market_resolved()` — live, imported by `backfill_market_dates.py`, real production code (see `[[project_canonical_resolution_write_path]]`).
- The `resolution_evidence_source` provenance column, used throughout this arc's own verification.
- `data/characterizations/sweep_common/sweep_terminal_signal.py`, the terminal-signal module, with a committed test (`tests/test_sweep_terminal_signal.py`).
- The `flock` overlap guard — narrower than it might sound: it lives on `~/trading-swarm/scripts/cron_wrappers/run_database_backup.sh` (`2026-08-26-backup-guard-and-scheduling.md`), guarding backup/sweep I/O contention, not on the segment drivers or on `run_daily_maintenance.sh` itself. Extending it there (item (f) of the 08-27 summary) was never implemented and is not part of this closure — noted so it isn't silently forgotten, but it is not a segment-5-style prerequisite for anything, since nothing further is being resumed.

## PART 4 — WHAT REMAINS UNCOMMITTED / ACTIONED

`data/checkpoints/segment3_checkpoint.json`, `segment3_terminal_marker.json`,
`segment4_checkpoint.json`, `segment4_terminal_marker.json` (first-repo)
are committed alongside this closure so the sweep's record is complete
rather than sitting untracked. `data/checkpoints/slug_fetch_*` files
belong to the separate classifier/slug-fetch arc (`2026-08-31-slug-fetch.md`,
`2026-09-01-slug-fetch-unswept.md`) and are out of scope here.

No production DB write occurred from either change in this document: the
`backfill_market_dates.py` edit only changes which `SELECT` runs before the
existing write path; it was verified read-only this session. `markets`,
`trades`, `category`, and `category_source` are untouched by this change
set — the only DB access performed this session was `SELECT`/read
verification queries and the pre-existing test suite.
