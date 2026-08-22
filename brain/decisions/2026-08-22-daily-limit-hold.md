# 2026-08-22 — Daily Backfill Limit Hold (2,000, Temporary)

## THE CHANGE

**[V]** `daily_maintenance.py`'s invocation of `backfill_market_dates.py`
lowered from `--limit 35000` to `--limit 2000`. `--geo-only` stays dropped
(the scope widening from step 2, commit `5fcbffe`, was correct and is
permanent — only the volume is held down). `backfill_market_dates.py`'s own
script default (`--limit`, `default=1000`) is untouched; this change is
scoped to the daily_maintenance invocation only. One commit, first-repo
`scripts/daily_maintenance.py`, cleanly revertible (a single-line diff on
the `extra_args` list plus an explanatory comment).

**[V] Baseline confirmed from git, not transcribed:** `git log -1 --oneline
-- scripts/daily_maintenance.py` at the start of this task returned
`5fcbffe feat: discovery-gap closure step 2 -- drop --geo-only, raise daily
limit to 35000` — matching the prompt's claim that this is the last commit
to touch the file, and that `35000` (not `500`) was the value in place. Step
2's own commit is not reverted or amended; this is a new, forward commit on
top of it, so the history stays legible: 500 → 35000 (5fcbffe) → 2000 (this
commit) → 35000 again, later, once the staged sweep has run.

## WHY 2,000, SPECIFICALLY

Today's progress check (first-repo `cefabdd`, trading-swarm `8293054`)
established that the widened step has **never actually executed** — it
sits at position 32 of 33 in `daily_maintenance.py`'s sequence, and
yesterday's run stalled in step 12 (`backfill_transaction_hashes.py`, DNS
outage) before ever reaching it. Its next scheduled fire was
2026-08-23 06:00:01 UTC, which would have been its first live run at
`--limit 35000` — unattended, with no backup, no tranche gating, no
checkpointing, and none of the pre-registration's (§C) seven abort
thresholds. At the observed dry-run rates it would plausibly resolve
**~22,600 markets** in that one run. Oscar's decision: hold the volume down
now, run the tranches deliberately, revisit the steady-state limit
afterwards.

2,000 was chosen over the pre-widening value (500) for a specific reason
tied to the scan's own structure, not just "smaller than 35000":
`backfill_market_dates.py`'s candidate query is an insertion-ordered scan,
and its first ~98 rows are a **permanently-dead prefix** — 2020-era markets
CLOB has purged (confirmed by direct `curl` as genuine 404s during step 2's
investigation, 2026-08-21). At `--limit 500`, that fixed 98-row dead prefix
consumes **~20% of the daily budget** before any productive work happens.
At `--limit 2000`, the same fixed 98 rows dilute to **~5%** — a materially
better ratio of productive-to-wasted calls for the same per-call cost,
without yet trusting the full 35,000-row scale this step has never been
timed at.

2,000 also gives a **meaningful first live sample** of the widened step's
real behaviour — large enough to see resolution activity at a rate worth
inspecting, small enough that the write stays bounded and recoverable if
anything about the widened scope (no `--geo-only`) behaves differently at
production scale than the 5,000-candidate dry run predicted.

**This is a temporary setting, not the steady-state value.** 35,000 was
derived from a measured, density-validated recent daily-arrival maximum
(16,845 rows/day, 2026-08-10, via the rowid-density method documented in
step 2's implementation) with ~2x headroom, and remains the intended
steady-state limit once the staged sweep has run and the backlog this step
exists to clear is no longer competing with same-day arrivals for the daily
budget.

## PROJECTED BEHAVIOUR OF TOMORROW'S RUN (2026-08-23 06:00:01 UTC)

**[V]** Candidate population at this session's baseline capture (first-repo
`cefabdd`, `presweep_baseline_fingerprint_20260822T121745Z.json`, sourced
from today's progress-check fork, not re-derived here): **527,617**
eligible rows under `backfill_market_dates.py`'s own predicate (`end_date
IS NULL OR resolution_date IS NULL`, no `--geo-only`). This population will
grow slightly by tomorrow's run (organic daily arrivals; +3,207 was the
one-day delta observed between the pre-registration's 08-21 AM figure and
today's), but at 527,617+ candidates against a 2,000-row limit, **the limit
is the binding constraint** — the projection below does not depend on the
exact population size.

- **Candidates processed:** 2,000 (the limit; population is >250x that, so
  the cap binds).
- **Expected markets updated:** 2,000 × 95.8% ≈ **~1,916**, using step 2's
  own 5,000-candidate live dry-run rate (`updated=4790/5000` = 95.8% —
  verified against the dry-run artifact directly during today's progress
  check, not taken from this prompt uncritically).
- **Expected markets resolved:** ~1,916 × 67.4% ≈ **~1,291**, using the same
  dry-run's `resolved_accepted=3229` of `updated=4790` = 67.4%.
- **Projected runtime:** 2,000 × 0.19–0.22s/call ≈ **380–440 seconds, ~6.3–
  7.3 minutes** (~7 minutes) — the rate is `step2-implementation.md`'s own
  observed per-call rate, not an invented figure, and well inside the
  step's 3-hour default timeout (`DEFAULT_STEP_TIMEOUT`, no override for
  this step) with wide margin.
- **First ~98 candidates (the dead prefix):** ~4.9% of the 2,000-row
  budget, matching the "~5%" dilution target above.

## VERIFICATION

- **[V] (a)** Baseline confirmed from `git log`, not transcribed — see
  above.
- **[V] (b)** The change is present in the scheduled path: cron fires
  `0 6 * * * /home/parison/trading-swarm/scripts/cron_wrappers/run_daily_maintenance.sh`
  (confirmed via `crontab -l`), and that wrapper invokes
  `python3 scripts/daily_maintenance.py` with **no arguments** — it does
  not pass or override `--limit`. The 2,000 value takes effect purely from
  the edited `extra_args` list inside `daily_maintenance.py` itself.
- **[V] (c)** See "Projected behaviour" above.
- **[V] (d)** `python3 run_tests.py` re-run after the edit: no new
  failure introduced — see run output; result matches the standing
  baseline (16 files, 15 passing, `test_backtest_window_population.py`
  19/24, pre-existing population-count drift unrelated to this change).
- **[V] (e)** No production write occurred from this change. The change is
  a single edit to a Python source file (`Edit` tool only) — the script
  was never executed, `daily_maintenance.py` was not run, and no
  sweep/tranche was triggered. The production DB's WAL/shm files continued
  to advance in this window only because the always-on
  `polymarket-monitoring` service (15-minute loop) was writing
  independently of this task, as it does continuously — unrelated to and
  unaffected by this edit.

## CONSTRAINTS HONOURED

No production writes triggered by this task. `daily_maintenance.py`, the
sweep, and no tranche were run. `backfill_market_dates.py`,
`fast_resolution_check.py`, `hydrate_stub_markets.py`, and
`system_observer.py` were not touched. One commit, a single-line functional
diff (`extra_args=["--limit", "2000"]`) plus an explanatory comment block,
cleanly revertible.

## EXPLICIT STATEMENT

**This is temporary, pending the staged sweep.** 2,000 is a holding value
for the daily invocation only, chosen to dilute the dead-prefix tax and
produce a first bounded, recoverable live sample of the widened step.
**35,000 remains the intended steady-state limit** and should be restored
once the staged sweep (pre-registration §C: backup, tranche 1 against the
317-market census, tranche 2 seeded 5,000-market sample with a
kill-and-resume test, then the full sweep at 0.25s pacing with checkpointing
and the seven abort thresholds) has run and cleared the backlog this step
exists to address.
