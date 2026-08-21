# 2026-08-21 — pre-registration: closing the resolution-discovery gap

**PRE-REGISTRATION ONLY. Nothing in this document has been implemented.**
No writer modified, no sweep run, no market resolved, no measurement
recomputed. Every operational detail below (pacing, batch size, thresholds,
table names, verification bar) is fixed **before** any of it runs, per the
task's own instruction. Every claim tagged **[V]** (verified this
session — command/file:line given) or **[I]** (inferred, marked
explicitly). Source of the accepted recommendation:
`2026-08-21-discovery-fix-assessment.md` (`391db02`). Supporting:
`2026-08-20-discovery-gap-sizing-result.md`,
`2026-08-20-discovery-gap-thesis-intersection.md`,
`2026-08-19-canonical-resolution-write-design.md` (as amended).

---

## A. Scope and sequence

Five operations, strictly ordered, each gating the next:

| # | Operation | Gates on | Produces |
|---|---|---|---|
| 1 | Extend `backfill_market_dates.py`'s `_fetch_by_clob` with a `mark_market_resolved()` assertion branch | Nothing (code change) | A dry-run diff artifact (§B) |
| 2 | Widen candidate scope (drop `--geo-only`) | Step 1's diff passing | Updated invocation, no data written yet |
| 3 | Extract `closedTime` in `fast_resolution_check.py`'s Gamma pass | Nothing (independent code change, can run in parallel with 1-2) | A dry-run diff artifact (§B) |
| 4 | One-time catch-up sweep | Steps 1-3's diffs all passing, backup taken, tranche 1 clean | Hundreds of thousands of `resolved=1` writes (§C) |
| 5 | Second measurement (recomputation) | Step 4 complete, `evaluate_new_trader_results.py` has run at least once post-sweep so `trade_result` flips from `pending` | Two new figures, permanently separate from the result of record (§E) |

**Steps 1 and 3 are independent of each other** (different files, different
functions) and may be verified in parallel, but **both** must pass their
dry-run bar before step 4 begins — step 4 is the one irreversible,
consequential action in this plan, and it should not run against
partially-verified code.

**What stops the sequence partway, stated now, not improvised during:**

- **Step 1 or 3's dry-run diff shows any behavioral difference on the
  untouched branch(es)** → stop. Do not proceed to step 4. Fix the code,
  re-run the diff from scratch, do not patch around a partial failure.
- **Step 2's widened query, run in `--dry-run` mode, returns a population
  wildly inconsistent with this document's stated estimate (515,491 [V],
  §C)** — e.g., off by more than an order of magnitude — → stop. That means
  either this document's understanding of the schema is wrong or the DB
  has changed materially since this was written; re-derive before
  proceeding, do not adjust the estimate after the fact to match.
- **Backup fails integrity check** (§C) → stop. Do not sweep without a
  verified-good backup in hand.
- **Tranche 1 (§C) does not reproduce the sizing run's known census** →
  stop, diagnose, do not proceed to tranche 2 or the full remainder.
- **Any abort condition (§C) fires during the sweep** → stop the sweep
  process, do not resume until diagnosed. The checkpoint mechanism (§C)
  means a stopped sweep loses no more than one batch of progress.
- **Step 4 does not reach a state where `evaluate_new_trader_results.py`
  has processed the newly-resolved population** before step 5 is attempted
  → step 5 does not run. The recomputation is meaningless against
  `trade_result` values still sitting at `pending` — this is the exact
  mechanism `2026-08-20-discovery-gap-thesis-intersection.md` Q3
  established structurally excludes the 203 from the published figures
  today.

---

## B. Verification bar for steps 1-3

**Same standard as Stages 1 and 2 of the canonical arc** (§G,
`2026-08-19-canonical-resolution-write-design.md`; methodology precedent:
`2026-08-19-trade-evaluator-repoint.md`'s three-part verification).

1. **Pre-change behavior extracted from git, not hand-transcribed.**
   Before editing either file, capture the *current* `_fetch_by_clob`
   (`backfill_market_dates.py:62-78`) and the *current*
   `batch_update_resolved_markets`'s Gamma-fetch/parse block
   (`fast_resolution_check.py`, around the `resolution_event_time=None`
   call site, line ~279) via `git show HEAD:<path>` into a committed
   baseline artifact — not retyped from memory or from this document's own
   paraphrase of the code, which could silently drift from what's actually
   in the file.
2. **Before/after dry-run diff, full candidate population, both files
   separately:**
   - **Step 1 (`backfill_market_dates.py`):** run the *unmodified* script
     in `--dry-run` mode against today's full (or `--geo-only`, whichever
     is being verified) candidate population, capturing every decision per
     market (`end_date` written / not, and — new — `closed`/`winner`
     detected or not). Then run the *modified* script in `--dry-run` mode
     against the identical candidate population (same DB snapshot — no
     writes have happened between the two runs, so this is guaranteed).
     **Required result, split by branch:**
     - **Proxy branch (markets where `closed != true` in the CLOB
       response): ZERO behavioral difference from before.** Same
       `end_date` value computed, same market set touched, same market set
       skipped. This is the load-bearing check — the task's own
       instruction singles this out because a defect here would mean the
       extension broke the thing that already works, which is worse than
       building nothing.
     - **New assertion branch (markets where `closed == true`): the ONLY
       observable change.** Before: not_found/no-op (the field was never
       read). After: a `mark_market_resolved()` call recorded, with its
       `accepted`/`reason`/`evidence_source="clob"` logged per market, no
       actual write (dry-run).
   - **Step 3 (`fast_resolution_check.py`):** same shape — before/after
     diff over the Gamma bulk-fetch candidate population, confirming (a)
     `resolution_date` computed differently **only** where `closedTime` is
     present in the fetched response (previously always `None`,
     i.e. write-time via the 3-tier fallback; now the true event-time), and
     (b) every other field (`resolved`, `winning_outcome`,
     `evidence_source`) is byte-for-byte identical before/after — this
     change touches exactly one argument
     (`resolution_event_time=None` → `resolution_event_time=<parsed
     closedTime>`) in one call site and nothing else.
3. **What a failed diff means: stop, do not proceed.** Per the task's
   explicit instruction — this is not "investigate and adjust the fix
   until the diff passes," it is "a failed diff means the change as
   specified is wrong, fix it, and re-run the *entire* diff from a clean
   baseline, not a delta on top of the failed attempt." No partial
   credit — a diff that's clean on one branch but not the other (step 1) or
   clean on 95% of markets but not all (step 3) does not satisfy this bar,
   per the exact wording Stage 1 already used for itself (§G's migration
   table: "A diff that's clean only on one branch does not satisfy this
   stage").
4. **Test suite**, both changes: `run_tests.py` must show no new failure
   against the standing baseline (16 files, 15 passing, 19/24 in
   `test_backtest_window_population.py`) — this baseline is expected to
   still hold *before* the sweep (step 4); it is explicitly expected to
   change *after* the sweep, see §D.

---

## C. The sweep — the consequential part

### Pacing

**0.25s/call, not the script's current 0.1s.** This is a deliberate choice
against speed, stated with reasoning: this is the first unattended,
multi-hour, hundreds-of-thousands-of-calls run this codebase has made
against a live third-party API without a human watching in real time. The
0.25s figure is not novel — it is the codebase's own existing convention
(`fast_resolution_check.py`'s stale-CLOB pass, `discovery_gap_sizing.py`'s
527-call census), chosen here specifically **because** it is the
established, already-battle-tested pacing, not because it was computed
fresh for this task. `backfill_market_dates.py`'s own 0.1s was written for
a script whose candidate pool was expected to be small (376/day,
`--geo-only`) — that assumption no longer holds once scope is widened
(§ below), and the faster pacing was never validated against a
sustained, six-figure-call run.

**Expected runtime at 0.25s/call, one-time catch-up:**
515,491 candidates [V] (live query, this session:
`SELECT COUNT(*) FROM markets WHERE (resolved = 0 OR resolved IS NULL) AND
(end_date IS NULL OR resolution_date IS NULL)`) × 0.25s ≈ **35.8 hours**,
consistent with the assessment's ~36-hour estimate and the population
range (513k-524k) cited there. This will have grown further by the time
step 4 actually runs — the pre-sweep fingerprint (§G) records the actual
population size at run time, not this document's figure, which is a
planning estimate only.

### Batching and resumability

**The box has crashed three times in the last month — this must survive
that, not merely tolerate a clean restart.**

- **Runs detached**, not attached to an interactive terminal session —
  `nohup`/equivalent, writing stdout/stderr to a dedicated log file
  (`logs/discovery_gap_sweep_<timestamp>.log`), so a disconnected SSH
  session or terminal close does not kill it. This does not protect
  against an actual OS-level crash or reboot — nothing can, short of a
  systemd unit with `Restart=on-failure`, which is not proposed here since
  this is a one-off, not a permanent service.
- **Fixed batch size: 500 markets per batch** (matching
  `backfill_market_dates.py`'s existing per-100 progress-print
  granularity, scaled up slightly for a run this long) — after each batch:
  commit (already the per-row commit pattern the script uses today, so no
  change needed there), then write an **atomic checkpoint file**
  (`data/checkpoints/discovery_gap_sweep_checkpoint.json`, written via
  write-to-temp-then-`os.rename` so a crash mid-write cannot corrupt the
  last-known-good checkpoint) recording: batches completed, markets
  processed, updated/not-found/indeterminate/error counts (cumulative and
  this-batch), elapsed wall time, last `market_id` processed, and the
  current pacing actually observed (to catch API slowdown early).
- **Resumability is structural, not bespoke.** The candidate query is
  `WHERE (resolved = 0 OR resolved IS NULL) AND (end_date IS NULL OR
  resolution_date IS NULL)` — every successful `mark_market_resolved()`
  write flips `resolved` to 1 (or, for the small subset where only
  `end_date`/proxy fields get filled without a resolution, narrows via the
  date-null clause), which **removes that row from the candidate set on
  any subsequent invocation**, live, with no separate offset/cursor
  bookkeeping required for correctness. This is the same self-shrinking
  pattern the O-16 tier1/tier2 historical backfills already relied on. On
  a crash, the sweep is simply re-invoked from scratch — it will re-derive
  the (now-smaller) candidate set live and continue, at the cost of
  re-issuing not-yet-successful lookups (not-found/indeterminate rows,
  which don't shrink the candidate set), not at the cost of re-doing
  already-successful writes. The checkpoint file is for **observability
  and abort-condition evaluation** (below), not for correctness of
  resumption.
- **No `ORDER BY`.** The two known no-progress bugs in this codebase
  (`hydrate_stub_markets.py`, confirmed this session; and
  `backfill_market_dates.py`'s own existing query, un-audited for this
  specific property) both stem from an unordered candidate query combined
  with a population that doesn't shrink on failure. Here the population
  **does** shrink on success (per above), so the specific "same rows
  forever" failure mode does not apply the same way — but a stable
  `ORDER BY market_id` should still be added so that batch boundaries are
  deterministic and checkpoint/resume progress is legible in the log
  (batch N always covers the same slice of the *remaining* population, not
  an unpredictable one), not for correctness.

### Backup

**Before the sweep begins, not before step 1's code change** (the code
change writes nothing; the sweep does). `python3 scripts/backup_database.py`
— already does exactly what's needed [V], read this session:
`sqlite3.Connection.backup()` (the online backup API, safe against a live
WAL-mode writer per the script's own comment), followed by
`PRAGMA integrity_check` on the backup file, with the backup deleted and
the run reported as failed if the check does not return `ok`. **Confirm
the backup completes and passes integrity check before proceeding to
tranche 1** — this is itself an abort condition (below).

### Abort conditions, fixed in advance

Evaluated **after every batch** (500 markets, per above), not only at the
end — a 36-hour run must be interruptible mid-way if something is wrong,
not left to run to completion on faith.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Backup missing or failed integrity check | n/a — binary gate | **Do not start.** |
| 2 | Indeterminate rate, rolling over the last completed batch | **> 10%** (batch-level) | **PAUSE** — stop issuing new calls, do not mark as failed, wait for manual review. This is roughly 2x the sizing run's Q2-census rate (5.05%, 16/317 [V], `2026-08-20-discovery-gap-sizing-result.md`) and comfortably inside the highest single stratum observed there (O-newest tercile, 12%), so an isolated batch crossing 10% is plausible noise, not necessarily a defect — hence pause-and-review, not hard abort. |
| 3 | Indeterminate rate, cumulative across the whole sweep so far | **> 20%** | **HARD ABORT.** This is roughly 4x the sizing run's census baseline and still comfortably below the sizing pre-registration's own 30% inconclusive-census-unusable threshold (`2026-08-20-discovery-gap-sizing-prereg.md` §9) — crossing it means the method itself may not be behaving as the sizing run characterized it, not just batch noise. |
| 4 | `trg_resolved_no_unresolve` fires (any count > 0, checked via `sqlite_master`/journal or an explicit try/except around the write path surfacing the `RAISE(ABORT, ...)`) | **Any single fire** | **HARD ABORT immediately.** This trigger should structurally never fire given every establishing writer (including the new assertion branch) requires `resolved=0` in its own candidate selection (§G of the design doc) — a fire means something outside this plan's model of the write path is happening. |
| 5 | `check_resolution_write_atomicity` (audit_invariants.py, the `[resolution-stage0/OBSERVE]` line), re-run manually mid-sweep | **Non-zero** | **HARD ABORT.** Currently 0 [V, confirmed this session's earlier status check] — any non-zero count means something wrote `resolution_recorded_at` without going through `mark_market_resolved()`, live, during the sweep window. |
| 6 | `mark_market_resolved()` rejection pattern not predicted by this document | Any `reason` value other than `"written"` / `"written: existing value has no recorded evidence_source (pre-canonical), proposal accepted"` appearing at a rate materially above isolated/occasional (**> 1% of processed rows in a batch**) | **PAUSE, diagnose.** Per the assessment and the design doc's own A1 "rank-timing wrinkle" note, a CLOB (Rank 1) write is *expected* to occasionally outrank an already-present Gamma (Rank 2) value — that specific pattern (`"written: proposed evidence outranks existing"`) is allowed and expected, not an abort trigger. What **is** unpredicted and should pause the run: a same-rank disagreement (`"flagged: same-rank disagreement"`) at nontrivial volume, since no other live CLOB writer currently competes with this one for the same candidates. |
| 7 | Observed pacing degrades materially (checkpoint-recorded actual seconds/call rises above **1.0s**, 4x the target) | Sustained over 2 consecutive batches | **PAUSE.** Likely API-side rate-limiting or throttling — continuing at a degraded, unplanned pace changes the runtime estimate materially and should be a deliberate decision, not silent drift. |

**All thresholds above are fixed now.** Changing any of them during the
run to keep it going is exactly the kind of after-the-fact adjustment this
document exists to prevent — if a threshold turns out to be miscalibrated,
that is itself a finding to report, not a number to move.

### Staged rollout

**Do not sweep 515k rows as the first action.** Two tranches before the
remainder:

- **Tranche 1 — the 317-market Q2 census population itself**, exact
  predicate: `category IN ('Elections','Geopolitics') AND (trade_gap_flag
  = 0 OR trade_gap_flag IS NULL)` intersected with the sweep's own
  candidate query. **Justification:** this is the one population whose
  correct answer is already known — 203 resolved, 98 open, 16
  indeterminate [V], `2026-08-20-discovery-gap-sizing-result.md`. Running
  the new code against a population with a known answer is a correctness
  check the rest of the sweep cannot provide: if the new assertion branch
  writes fewer than 203 as `resolved=1` (allowing for the population
  having drifted slightly since 08-20 — re-derive the expected count
  live, do not hardcode 203 as gospel if the underlying 317-set has
  changed), or if the indeterminate rate is far from ~5%, that is a code
  defect, not sampling noise, and must be resolved before tranche 2.
  **What tranche 1 must show to proceed:** resolved count within a small
  tolerance of the freshly-re-derived expected count (not the stale 08-20
  figure), indeterminate rate consistent with the ~5% baseline (not
  triggering abort condition 2), zero trigger fires, zero unpredicted
  rejection patterns.
- **Tranche 2 — a 5,000-market random sample** of the remaining candidate
  population (seeded, e.g. `random.seed(20260821)`, matching this
  project's own convention of a fixed, documented seed for any sampling
  step). **Justification:** large enough to be statistically meaningful
  against the batch-level abort thresholds above (10 batches of 500, at
  ~21 minutes total at 0.25s/call — fast enough to review same-day before
  committing to a multi-day run), small enough to bound blast radius while
  still exercising checkpoint/resume mechanics and real API behavior at a
  scale tranche 1 (317, one batch) does not. **What tranche 2 must show to
  proceed:** all abort conditions clear across all 10 batches, checkpoint
  file correctly reflects cumulative state, a deliberate kill-and-resume
  test (kill the process mid-batch, confirm restart picks up correctly via
  the shrinking-candidate-set mechanism) performed once during this
  tranche specifically to validate the resumability claim before trusting
  it for 36 hours unattended.
- **Remainder** — the full candidate population minus tranches 1 and 2
  (already removed from the candidate set by their own successful writes),
  run only after both tranches pass cleanly.

---

## D. What the sweep changes downstream

**Stated plainly, per the task's instruction: this is the most
consequential write this project has made.** `resolved=1` on several
hundred thousand rows (bounded above by ~515,491, the current candidate
population [V]; the true resolved fraction is estimated, not certain — Q1
of the sizing result gives a point estimate of ~99.3% of the dateless
population already resolved on CLOB, so the realistic expectation is that
the large majority of successfully-processed rows convert) changes:

- **The canonical backtest population directly**
  (`monitoring/column_definitions.py::backtest_window_sql()`) — every
  Geopolitics/Elections market among the newly-resolved rows that also
  clears the `trade_gap_flag` and `tape_end >= window_start` clauses
  **enters** the canonical population for the first time. Per
  `2026-08-20-discovery-gap-thesis-intersection.md` Q1/Q2, at minimum the
  203 already-characterized markets qualify structurally (164 pre-`T_split`,
  39 post) — the true number after a full unscoped sweep is larger and
  unknown until measured (only the 317-market Geo/Elections census stratum
  was fully characterized; the sweep reaches the full ~515k population,
  most of which is currently `category='Unknown'` and would need
  `backfill_market_categories.py` to also classify it before entering the
  Geo/Elections-scoped canonical population — see the assessment's
  growth-rate finding).
- **`test_backtest_window_population.py`'s reconciliation numbers** — the
  standing 19/24 baseline compares a frozen snapshot against live
  reconciliation counts; the live side of that comparison will genuinely
  change after the sweep. This is **expected, not a regression** — the
  test file's own `[SECTION 2L]` live-reconciliation tests are already
  designed to hold under a growing live population; only the frozen-vs-live
  gap-count tests (`T2`-`T2f`) are expected to report different numbers,
  and per §B this is not itself a pass/fail gate on the sweep, but must be
  re-examined afterward, not silently accepted as "still failing, same as
  before" without checking whether the *reason* changed.
- **`trade_result`**, via `evaluate_new_trader_results.py` (daily
  maintenance step 21, per `2026-08-20-discovery-gap-thesis-intersection.md`
  Q3's own finding that this is exactly the gate keeping the 203 invisible
  today) — flips `pending` → `won`/`lost` for every trade on a
  newly-resolved market, for `is_flagged=1, research_excluded=0` traders.
  This is what step 5's recomputation depends on; it is also what feeds
  P&L, ELO, and every other trade-outcome-dependent computation for the
  general population, not just the v2f cohort.
- **The full downstream chain already documented in
  `2026-08-19-market-resolution-write-cluster.md` Q6** for writer #3
  (the same evidence-source family this sweep uses): `requeue_resolved_market_traders.py`
  → background P&L worker (synthetic closes) → `evaluate_new_trader_results.py`
  → `apply_full_elo_modifiers.py` — i.e. comprehensive ELO, geo ELO, and
  P&L aggregates for every trader touching a newly-resolved market, not
  only the v2f cohort/placebo.
- **A specific precedent worth re-checking, not re-verified this
  session:** the O-16/silent-failure-audit finding
  (`2026-07-07-silent-failure-audit-FABLE.md` item 7.1) that
  `requeue_resolved_market_traders.py:76`'s date-gate
  (`resolution_date > last_run`) silently dropped the entire O-16 backfill
  because those backfills wrote **historical** resolution dates, always
  older than `last_run`. **[I], reasoned but not re-traced this
  session:** this sweep's `resolution_date` will, for the large majority
  of markets (which have never been visited by `backfill_market_dates.py`'s
  proxy branch before, given prior `--geo-only` scoping), fall through
  `mark_market_resolved()`'s 3-tier fallback to **write-time** (today's
  date), not a historical date — which would make `resolution_date >
  last_run` **true**, the opposite failure direction from the O-16 case.
  This should mean the O-16 requeue-miss shape does not recur here — but
  this reasoning has not been checked against the live code this session
  and should be confirmed, not assumed, before or during tranche 2.
- **`check_pending_flagged`/`check_pending_geo`** (audit_invariants.py,
  Tier 2) — a mass `resolved=1` flip is exactly the shape of input that
  produced the documented 0→60,345→0 spike in
  `2026-08-19-pending-invariant-regression.md` (self-healing within ~35
  hours, but with no row-level snapshot of the 60,345 ever persisted) —
  that spike's root mechanism was characterized as self-healing but not
  fully settled. A sweep of this size should expect and
  budget for a large, possibly-alarming movement in these Tier-2 checks,
  and treat it as expected volume, not automatically as a new incident —
  but should also not assume it's benign without checking, given the prior
  spike's cause remains open.
- **Objective 1 of `trader_skill_metric_v2f.py`** (the 360-trader
  significance-95/M≥10 cohort, `metric_v2f_intersection_cohort`) draws
  from the same `won`/`lost`-filtered `entries_df` as Objective 2 — it
  will also shift after the sweep. **Out of scope for step 5's named
  recomputation** (which is Objective 2 only, per the task), named here
  only so it isn't mistaken for untouched.

---

## E. The second measurement

**Oscar's decision, recorded exactly as instructed: option (c).** The
result of record — cohort +0.0316, CI [-0.0088, +0.0710], n=3,032;
placebo +0.0127, CI [-0.0210, +0.0461], n=2,569 — **stands, permanently,
unmodified, not superseded.** Confirmed still present, untouched, in the
live DB as of this session [V]:
`SELECT * FROM metric_v2f_oos_result` returns exactly these two rows,
`generated_at=2026-08-15T19:36:56`, `generator_commit=eaeabbc` — nobody has
re-persisted over it since. **The recomputation is a second, separately
named measurement. Both figures stand permanently, side by side.**

### Protecting the result of record — a mechanical requirement, not optional

`trader_skill_metric_v2f.py`'s own `main()` does
`DROP TABLE IF EXISTS metric_v2f_oos_result` before recreating it
(`trader_skill_metric_v2f.py:449`, [V] read this session) — **running the
existing `--persist` flag unmodified, as-is, would destroy the original
row.** This is fixed here, before it happens: the recomputation run
**must not** invoke the stock `--persist` path against the live
production tables. Instead:

1. Confirm (again, immediately before step 5) that
   `metric_v2f_oos_result` and `metric_v2f_intersection_cohort` still hold
   exactly their current, pre-sweep content — a repeat of the query above.
2. Run the pipeline's own functions (`build_presplit_cohort`,
   `match_control`, `measure_oos`) **exactly as-is, unmodified** — no
   `--persist` flag, same pattern `discovery_gap_thesis_intersection.py`
   already used successfully for a read-only reproduction.
3. Persist the results to **new, distinctly-named tables** —
   `metric_v2f_oos_result_corrected` and
   `metric_v2f_intersection_cohort_corrected` (or an equivalent
   `run_label`-tagged scheme) — never reusing or dropping the original
   table names. This is bookkeeping to satisfy "both figures stand
   permanently," not a re-specification of the metric itself; the
   underlying computation (`T_SPLIT`, `SEED`, cap5 weighting, two-way
   clustered bootstrap, `GATE_REPS_LOCAL` repetitions) is byte-for-byte
   the same code path.

### Exact specification — nothing re-specified

- **`T_SPLIT = "2026-04-01 00:00:00"`** — unchanged, hardcoded module
  constant, not passed as an argument, so there is no way to accidentally
  vary it.
- **`SEED = 42`** — unchanged, the script's own default; the recomputation
  invocation passes no `--seed` override.
- **Metric: cap5-weighted pair table, `per_trader_t_ci`, two-way
  trader×market clustered bootstrap** (`weighted_two_way_gap_bootstrap`,
  `reps=GATE_REPS_LOCAL`) — unchanged, same functions, same call sites
  (`measure_oos`, called once per cohort/placebo, same as the original
  run).
- **`M_CHOSEN=10`, `EFFECT_BAR=0.02`** — unchanged.
- **If the pipeline cannot run unchanged** — e.g. a schema change made by
  steps 1-4 breaks a query inside `build_presplit_cohort`/`measure_oos`,
  or a function signature has drifted since 08-15 — **that is a finding to
  report, not a license to adjust the method to make it run.** Stop, report
  exactly what broke and why, and treat the recomputation as blocked until
  a separate, explicitly-scoped fix (not a silent adjustment inside this
  exercise) resolves it.

### What is reported

- Both point estimates (cohort, placebo) and both CIs — result-of-record
  and corrected, side by side, never one replacing the other in any
  document, table, or dashboard that references this thesis going forward.
- **The delta**, cohort and placebo separately, **with its own
  uncertainty** — not just a point-to-point difference. The bootstrap
  already produces a distribution for each measurement; the delta's CI
  should be derived from the same resampled distributions (paired
  where the underlying trader/position sets overlap, not a naive
  independent-CI subtraction) — the exact delta-CI construction is
  specified at recomputation time, using the bootstrap's own resampled
  values already being generated, not a new statistical method invented
  post hoc.
- **The cohort-vs-placebo gap, under each measurement** — (cohort point −
  placebo point) computed twice, once per measurement, so the "does the
  gap narrow" question (below) has a single, unambiguous number on each
  side.

### The interpretation rule — fixed now, before any corrected number exists

**Stated expectation, in writing, before the measurement:** per
`2026-08-20-discovery-gap-thesis-intersection.md` Q6 [V], the affected
cohort positions' own mean edge is **+0.00056** against the published
cohort headline of **+0.0316** (roughly 1/56th) — essentially flat. The
affected placebo positions' own mean edge is **+0.01143** against the
published placebo headline of **+0.0127** — close to it. **The expected
direction, fixed here: the corrected cohort-vs-placebo gap NARROWS**
relative to the result-of-record gap (+0.0316 − +0.0127 = +0.0189),
because the newly-folded-in cohort evidence is weak while the
newly-folded-in placebo evidence is comparable to its own headline.

**What each outcome means, fixed now so none of them can be rationalized
after the fact:**

- **Gap narrows, as predicted** → the original measurement was inflated by
  non-random population thinning (traders/positions systematically
  excluded from the cohort side more than the placebo side, or excluded
  with systematically different edge). **Report by how much** — the
  narrowing's magnitude relative to the original gap (+0.0189), not just
  its direction, and whether the corrected cohort CI still excludes zero
  (the thesis's own significance bar) after the correction.
- **Gap holds** (within the delta-CI's own uncertainty of zero movement)
  → the thinning was not materially distorting the result. **This is a
  real, reportable robustness finding** — the thesis result survives a
  test it has not previously had, and that should be stated as
  a positive finding for the thesis, not a null result to bury.
- **Gap widens** → **unexpected, contrary to the pre-registered
  prediction.** Requires diagnosis before acceptance, not celebration —
  specifically: re-check whether cohort qualification changed
  more than expected (§F — new qualifiers entering via the M≥10 boundary
  could shift the cohort's composition, not just its measured edge on
  existing positions), before treating a widened gap as a genuine
  strengthening of the thesis. **Do not report a widened gap as
  confirmation of the thesis without first ruling out a
  compositional-change explanation.**

**Explicitly, per instruction: no re-specification of any parameter above
to obtain a preferred outcome, under any of the three cases. If a gate
elsewhere in this document fails (§A, §B, §C), stop and report — the
absence of a corrected number is itself a reportable outcome, not a
reason to loosen a threshold.**

---

## F. Cohort membership

**The corrected population may change WHO qualifies, not just the
measured edge.** Per `2026-08-20-discovery-gap-thesis-intersection.md` Q5
[V, stated as an upper bound there], 46 traders are upper-bound candidates
to newly cross `M≥10` if the 164 pre-`T_split`-relevant markets among the
203 were resolved and counted — one trader goes from **zero** presence in
the current presplit-eligible population to an upper-bound 26 markets. A
sweep reaching the full ~515k population (not just the 203) will produce
a real, not upper-bounded, version of this effect at a scale not yet
measured.

**The reproducibility gap this closes, named explicitly:** `main()`'s
`--persist` path writes `metric_v2f_oos_result` (aggregate stats only —
`kind, n_positions, n_traders, point_gap, ci_lo, ci_hi`) and
`metric_v2f_intersection_cohort` (Objective 1's population, not Objective
2's OOS cohort/placebo) — **the actual OOS cohort (`oos_cohort`) and
placebo (`control_cohort`) trader-ID sets computed in `main()` at lines
~413-416 are local Python variables never persisted anywhere.** This is
confirmed as the exact mechanism `2026-08-16-result-of-record-reproducibility-audit.md`
already diagnosed as making the 08-15 result unreproducible at the
trader-membership level, even though the aggregate numbers are pinned.

**Fixed requirement for step 5: persist cohort/placebo membership.** In
the same process, same DB snapshot, same run as the corrected measurement
(§E) — after computing `oos_cohort` and `control_cohort` via the
pipeline's own unmodified functions — write two new tables,
`metric_v2f_oos_cohort_membership_corrected` and
`metric_v2f_oos_placebo_membership_corrected` (trader address, one row
each, tagged with the same `generated_at`/`generator_commit` used for
§E's result tables). **This is additive instrumentation around the
unchanged pipeline, not a modification of it** — it persists values
`main()` already computes and holds in memory, touching no line of the
metric-computation logic itself, so it does not conflict with §E's "nothing
re-specified" requirement.

**What is reported:** the corrected cohort/placebo trader lists in full
(committed JSON artifact, per §G), and a **before/after membership diff**
against the *current* live re-derivation of the same cohort (i.e. run the
unmodified pipeline once more, read-only, immediately before the sweep, to
capture a same-day "before" membership snapshot — not the stale 08-15
148/120 figures, which are already known to be unreproducible per the
audit, but a fresh baseline taken as close to the sweep as possible so the
diff isolates the sweep's effect, not accumulated DB drift). Report: which
traders are newly present in the OOS cohort, which are newly present in
the placebo, and the overlap with Q5's 46-trader upper-bound candidate
list (how many of those 46 actually crossed `M≥10` for real, once the
sweep provides real `won`/`lost` outcomes instead of Q5's synthetic-label
approximation).

---

## G. Reproducibility

Every decision-carrying number in this exercise comes from a committed,
parameterized script writing a durable, timestamped JSON artifact with its
generating parameters and seed recorded — the same discipline already
applied throughout this arc (`discovery_gap_sizing.py`,
`discovery_gap_thesis_intersection.py`, both first-repo, both committed
alongside their result docs). Specifically:

- **The extended `backfill_market_dates.py`** (step 1) and the sweep
  driver (step 4) are one script, or a clearly-linked pair, committed
  before tranche 1 runs — not written ad hoc during the sweep.
- **Every batch's checkpoint** (§C) is itself a durable artifact,
  retained after the sweep completes (not deleted), forming a full audit
  trail of the run — not just the final summary.
- **Step 5's recomputation** writes its own timestamped JSON (matching
  `--json-out`'s existing convention in `trader_skill_metric_v2f.py`) in
  addition to the new DB tables (§E, §F) — belt and suspenders, consistent
  with how the result of record itself is documented in three places
  (the live DB table, the committed JSON, and this arc's markdown docs).

**Pre-sweep DB fingerprint, persisted as a baseline before step 4 begins**
(same dimensions as this session's own standing status-check pattern, plus
the fields this specific exercise needs):

| Metric | Value at pre-registration time [V] |
|---|---|
| traders | 171,461 |
| trades | 11,639,259 |
| positions | 7,673,355 |
| markets | 741,846 |
| resolved markets | 224,981 |
| Geo/Elec resolved+gap-clean | 10,589 |
| `resolution_evidence_source='clob'` | 0 |
| `resolution_evidence_source='gamma'` | 12 |
| `resolution_evidence_source='hydration_fill'` | 1 |
| Dateless-unresolved candidate population (sweep's own predicate) | 515,491 |
| Q2 canonical-relevance census population | 317 |
| `metric_v2f_oos_result` (cohort/placebo rows) | unchanged since 2026-08-15T19:36:56, `eaeabbc` |

**This table is a planning-time snapshot, not the operational baseline.**
The actual pre-sweep fingerprint must be re-captured, live, immediately
before step 4 begins (via the same query pattern), since population counts
grow continuously (~5,108 new markets/day observed in this session's prior
status check) and days may pass between this document's approval and the
sweep's execution.

---

## H. What this does not do

- **`hydrate_stub_markets.py`'s two defects are a separate track** —
  identifier fallback and `closedTime` field-name fix, per the assessment's
  shape A. Cheap, already fully diagnosed (`2026-08-20-open-smells-register.md`
  item 2), reaches a disjoint population (external_seed traders' markets
  only, zero overlap with the 203 [V], confirmed in the assessment). Not
  scheduled by this document; may proceed independently, on its own
  verification track, without blocking or being blocked by anything above.
- **Stage 3 of the canonical arc is untouched.** Migrating
  `fast_resolution_check.py`'s three CLOB sibling passes (`#4/#5/#6` —
  `run_stale_clob_pass`, `run_recent_overdue_pass`, `run_external_seed_pass`)
  to call `mark_market_resolved()` in place is separate work, not part of
  this pre-registration. Step 3 above (extracting `closedTime`) touches
  the **Gamma** bulk pass (`#3`, already migrated in Stage 2), not these
  three.
- **Shape D (upstream ingestion-time date fetch) is named, not
  scheduled.** The assessment identified this as a real, bounded,
  cheap complement (~21 min/day at the observed new-market rate) that
  would stop *future* dateless-market creation — it is not designed here,
  has no code change proposed, and is explicitly out of scope for this
  pre-registration per the task's non-goals.
- **Gamma keyset pagination (shape B as originally specified) is
  rejected**, per the assessment: no cost bound (scales with Gamma's
  global catalog, not this project's own population), no completion
  guarantee (the underlying `endDate` sort-key tie-ordering problem
  persists regardless of pagination depth). Not part of this plan in any
  form other than the narrow, already-approved `closedTime` extraction
  (step 3), which requires no pagination change at all.

---

## I. What would falsify the plan

Outcomes that would mean the **approach** is wrong, not merely that this
particular run needs a retry or a parameter tweak:

1. **Tranche 1 (the known 317-market census) does not reproduce
   approximately 203 resolved / 98 open / ~16 indeterminate**, after
   accounting for population drift since 08-20. If the new code path,
   run against a population whose answer is already known, produces a
   materially different result, the extension to `_fetch_by_clob` is
   built on a wrong assumption about the CLOB response shape or the
   comparator logic — not a sampling artifact, since this is a full
   census, not a sample. This would falsify the specific implementation,
   and likely the assumption (carried from the assessment) that this
   script's existing CLOB call already returns everything needed.
2. **The indeterminate rate at scale (tranche 2 or the full sweep) is
   systematically far above the sizing run's ~5%** (not just an isolated
   batch — see abort condition 3's 20% cumulative threshold) — this would
   falsify the sizing run's own generalization claim (that 527 sampled
   CLOB calls characterize the full population's behavior), meaning the
   whole cost/coverage model in the accepted assessment was built on an
   unrepresentative sample.
3. **`mark_market_resolved()`'s comparator produces same-rank
   disagreements (`"flagged: same-rank disagreement"`) at real, nontrivial
   volume** — this would mean CLOB's Rank-1 declarations disagree with
   already-recorded Rank-2 (Gamma) values often enough to matter, which
   would falsify A1's premise that a direct CLOB declaration and an
   algorithmic Gamma price-inference should agree in the overwhelming
   majority of cases. A high rate here is a finding about the underlying
   evidence sources, not a code bug to patch around.
4. **The corrected cohort/placebo gap widens materially** (§E) — this
   doesn't falsify the discovery-gap-closure plan itself, but it would
   falsify the specific mechanistic prediction (thin-population inflation)
   this document commits to in writing, and per §E must trigger diagnosis
   before any claim that the thesis result strengthened.
5. **`trg_resolved_no_unresolve` or `check_resolution_write_atomicity`
   ever fires/goes non-zero during the sweep** (abort conditions 4-5) —
   this would falsify the canonical design's own claim (§G of the design
   doc) that every establishing writer's `resolved=0` candidate-selection
   guard structurally prevents the transition the trigger forbids; it
   would mean either this sweep's implementation doesn't actually respect
   that guard, or some other, unaccounted-for writer is active
   concurrently.
6. **A widened-scope run's actual candidate population is not, in fact,
   dominated by markets outside `--geo-only`'s reach** — i.e. if removing
   `--geo-only` doesn't materially increase the candidate pool beyond
   ~360-376/day, this would falsify the assessment's growth-rate finding
   (that category-classification lag, not the discovery mechanism itself,
   was suppressing the geo-scoped population's visible growth) and mean
   the widening step accomplishes less than expected.

---

*Generated 2026-08-21. Pre-registration only — no code written, no
production write made, no market resolved. Sources: this session's live
DB queries (candidate population, current `metric_v2f_oos_result` /
`metric_v2f_intersection_cohort` content, current `[resolution-stage0/OBSERVE]`
invariant count, DB fingerprint), `scripts/backfill_market_dates.py`,
`scripts/fast_resolution_check.py`, `scripts/trader_skill_metric_v2f.py`
(all read this session, first-repo), `scripts/backup_database.py`,
`monitoring/resolution_writer.py`,
`2026-08-21-discovery-fix-assessment.md` (`391db02`),
`2026-08-20-discovery-gap-sizing-result.md`,
`2026-08-20-discovery-gap-sizing-prereg.md`,
`2026-08-20-discovery-gap-thesis-intersection.md`,
`2026-08-19-canonical-resolution-write-design.md`,
`2026-08-19-market-resolution-write-cluster.md`,
`2026-08-19-trade-evaluator-repoint.md`,
`2026-08-16-result-of-record-reproducibility-audit.md`,
`2026-08-15-skill-metric-rebuild.md`,
`2026-08-19-pending-invariant-regression.md`,
`2026-07-07-silent-failure-audit-FABLE.md` (all trading-swarm). No writer
modified, no schema touched, no data repaired, no measurement recomputed.*
