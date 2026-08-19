# 2026-08-19 — pre-registration: wiring `backfill_trade_results_geo.py` into `daily_maintenance.py`

**This is a pre-registration only. Nothing in this document has been
executed.** `daily_maintenance.py` is unmodified, `backfill_trade_results_geo.py`
has not been run (dry or live), and no production data has been touched.
Every claim below is tagged **[V]** (verified this session, command/file:line
given) or **[I]** (inferred, explicitly marked). Findings recorded here
only, per the standing instruction.

**Read this before running anything.**

---

## Background, verified before use

**[V]** `check_pending_geo` currently reads **24,707** (live re-check just
now, same predicate as `scripts/audit_invariants.py:281-300`) — consistent
with the 24,704 reading in `2026-08-19-pending-invariant-regression.md`
(`9fb436d`), small drift expected from live traffic. That doc established
this is a **known, standing gap**: `backfill_trade_results_geo.py` exists
specifically to evaluate this population but was never wired into
`daily_maintenance.py`. `2026-08-19-placebo-pending-exposure.md` (`02ca3e6`)
established the harm shape: a `trade_result='pending'` entry trade drops
the position **entirely** out of both `build_presplit_cohort` and
`measure_oos` — thinning, not corrupting.

**[V] One background claim in this task's own framing needed correction
before use, per the standing "verify, don't propagate" rule:** item 8's
premise states "TradeEvaluator's two callers [are] in neither crontab nor
maintenance." Checked directly — `grep -n "evaluate_new_trader_results"
scripts/daily_maintenance.py` → line 68, **it is wired**, as step 21
("Evaluate new trader results"). Only the *other* `TradeEvaluator` caller,
`scripts/backfill_trade_results.py`, is confirmed unwired (absent from
both `daily_maintenance.py` and `crontab -l`). The pattern named in item 8
still holds — remediation scripts left unwired is real and recurring —
but the specific claim about evaluate_new_trader_results.py was wrong and
is corrected here rather than repeated.

---

## 1. Sequence position and justification

**[V] Proposed: insert as a new step between the current step 21
("Evaluate new trader results") and step 22 ("Reconcile geo resolved
counts [post-eval]"), becoming the new step 22.** Everything from the old
step 22 onward shifts down by one (old 22→23 … old 29→30; 30 steps total).

Confirmed the current step list and numbering directly against
`scripts/daily_maintenance.py:32-81` (`STEPS`) and today's
`logs/daily_maintenance.log` (`[N/29]` labels match 1:1). Step 7 is
"Integrity audit (pre-ELO gate)" (`audit_invariants.py --alert`); step 21
is "Evaluate new trader results"; step 22 is "Reconcile geo resolved
counts [post-eval]", whose own comment
(`scripts/daily_maintenance.py:69-72`) already states its purpose:
*"evaluate_new_trader_results flips pending→won/lost on geo trades,
changing geo_resolved_trades_count. Running here ensures the next
morning's audit opens on a clean reconciled state."*

**Why after step 7, not before:** required by the task, and independently
justified — `check_pending_geo` must keep reading the true backlog. A
remediation step placed before step 7 would make the invariant report
whatever the remediation just cleared, regardless of whether the
remediation actually worked that day (subprocess failure, DB lock,
timeout) — a green check that proves nothing, the exact failure mode
already flagged for `check_pending_flagged`/step 21 (see §2).

**Why specifically before step 22, not appended at the end (new step 30):**
step 22 already exists to reconcile `geo_resolved_trades_count` after
step 21's writes. If the new backfill step runs before it, step 22's
reconciliation also picks up the new step's writes in the same pass —
one settlement point for both remediation steps, matching the existing
design intent of step 22 rather than adding a second, redundant
reconciliation at the end of the run. Appending at position 30 would mean
`geo_resolved_trades_count` is stale for every trader the new step
touches until the *next* day's step 6 reconcile — a full day of drift for
no reason, avoidable by ordering.

**What runs either side of the new step 22:** step 21 "Evaluate new trader
results" (`evaluate_new_trader_results.py`, non-blocking) immediately
before; step 23 (old 22) "Reconcile geo resolved counts [post-eval]"
(`reconcile_geo_resolved_counts.py`, non-blocking) immediately after.

---

## 2. The ordering defect — does this reproduce it?

**[V] Yes, necessarily, and this is stated plainly rather than
downplayed.** `check_pending_flagged` (audit at step 7) and
`evaluate_new_trader_results.py` (remediation at step 21) already exhibit
exactly the sawtooth the task describes: the step-7 audit reads whatever
backlog accumulated since *yesterday's* step 21 ran; step 21 clears it
later the *same* day; a run that dies between steps 7 and 21 leaves an
uncleared backlog sitting behind a recorded PASS from that morning's
audit, undetected until the next audit run 24h later. Directly observed
this exact pattern for `check_pending_flagged` on 2026-08-19: 0 (08-18
audit) → 60,345 (08-19 audit, before step 21 ran) → 0 (after step 21 +
later same-day draining) — see `2026-08-19-pending-invariant-regression.md`
Q4.

Placing the new geo-backfill step at position 22 (after step 7, after
step 21) **reproduces this identically** for `check_pending_geo`: the
step-7 audit will always read the backlog accumulated since the
*previous* day's step 22 ran, not the current day's. There is no ordering
choice that avoids this while still satisfying requirement #1 (remediation
after the gate) — running remediation before the audit is the only way to
make the audit read post-remediation state, and that is the manufactured-green-check
failure mode requirement #1 exists to prevent. **The sawtooth is an
accepted, documented tradeoff of gating-before-remediating, not an
oversight.** What differs from the existing `check_pending_flagged`
pattern: `check_pending_geo`'s remediation (new step 22) is far
downstream of the gate (step 7) — 15 steps apart, vs. `check_pending_flagged`'s
remediation (step 21) being 14 steps downstream of its own gate read at
step 7. Materially the same distance; no meaningful difference in
sawtooth-window duration between the two checks.

---

## 3. Success criterion, fixed before running

**[V] Do not pre-register "expect 0."** Confirmed by direct query:
organic new-pending-on-already-resolved geo/elec trades (trade timestamp
within the last 14 days, i.e. trades that would keep landing even after
the historical backlog is cleared) — **7, 5, 15, 1, 2** across 5
non-zero days in the last 14, **30 total, ≈2.1/day average, with several
zero-days**. This trade-timestamp basis almost certainly **undercounts**
the true steady-state inflow: it misses trades ingested via
`background_backfill_worker.py` for newly-discovered traders (which carry
old trade timestamps but land in the DB "today"), and the fingerprint in
`2026-08-19-pending-invariant-regression.md` recorded **106 new traders**
discovered in a single 24h window recently. The magnitude of that second
channel's contribution to `check_pending_geo` specifically has **not**
been measured — flagged as the dominant source of uncertainty in the N
below, not glossed over.

**Proposed criterion:**
> `check_pending_geo` falls below **N = 300** within **D = 7 days** of the
> step being wired into `daily_maintenance.py`, and remains within **±20%
> of its own value** (not re-climbing past 300) across **K = 5**
> consecutive daily audit readings.

**Justification for N = 300:** the observed organic trade-timestamp-basis
rate (≈2/day, up to 15 on a busy day) would need to run for **2-3 weeks
uninterrupted** to reach 300 — generous headroom over the *known* channel.
It is deliberately **not** tightened further because the *unmeasured*
new-trader-backfill channel could plausibly add more per day than the
organic channel alone; 300 is chosen to comfortably tolerate that unknown
without being large enough to hide a real failure (300 is still **98.8%**
below the current 24,707 reading — nowhere close to "the backlog just
didn't clear").

**What would count as the wiring having FAILED:**
- `check_pending_geo` has **not** dropped below 300 by day 7, OR
- it drops below 300 initially but is trending back up across the K=5
  readings (not just noisy — a sustained climb), OR
- the new step's own `daily_maintenance.log` entries show it exiting
  non-zero, being skipped, or timing out on 2+ of the 7 days (the step is
  non-blocking, so a silent per-day failure would not otherwise surface —
  this must be checked explicitly, not inferred from the maintenance run's
  overall exit code).

**Explicit next step if N=300 turns out wrong either way:** after the
first week of real daily readings, re-derive N from the *actual* observed
post-clearance daily inflow (now measurable directly) rather than this
session's estimate — this pre-registration's N is a starting hypothesis,
not a permanent target.

---

## 4. Blast radius — before/after measurements to take

**[V] This is a population change, not hygiene, and the result of record
will not reproduce identically afterward. That is accepted here because
the cause is known and documented — unlike the unattributable
2026-08-16 drift.**

**"Before" values — taken from today's live state, not the task's cited
figures, which have already drifted (flagged per the standing "verify,
don't propagate" rule rather than carried forward uncorrected):**

| measurement | task-cited (08-16) | actual, verified today (2026-08-19) |
|---|---|---|
| canonical population | 6,842 | **6,899** (`characterize_pending_resolution_inconsistency.py`, today's run) |
| v2f implicit population | 6,588 | **6,646** |
| symmetric diff | 254 | **253** |
| pending-resolution series (92-population) | — | **92** (today's reading; series is 88→103→92, non-monotonic — see `2026-08-19-pending-invariant-regression.md`) |
| no-FIFO-close series | — | **161** (stable 08-18→08-19) |
| placebo positions / traders (persisted 08-15) | 2,569 / 110 | unchanged — persisted, not live; live re-derivation today gives **155 / 113** true cohort/placebo-survivor counts (drifted from the 08-15 148/120/148/108 figures already, independent of this change) |
| `0x5cfd8811...` stuck positions | — | **26** total (28.9% of their footprint), **9 post-split** |
| cohort qualifying / surviving | 148 / 120 | **155 / 126** (today's live re-derivation) |

**Measurements to re-take after the first backfill run (dry-run counts
first, then live-run actuals, then the standing metric re-derivations):**

1. `backfill_trade_results_geo.py --dry-run` output: predicted won/lost/invalid
   split and traders-affected count, compared against the live run's
   actual split after it commits.
2. `scripts/characterize_pending_invariant_regression.py` re-run — new
   `check_pending_geo`/`check_pending_flagged` live counts.
3. `scripts/characterize_pending_resolution_inconsistency.py` re-run — new
   canonical/v2f/symmetric-diff/92-population counts. **Predicted
   direction:** the 92-population should **shrink or stay flat**, never
   grow — clearing pending trades can only move markets out of the
   "all-entry-trades-pending" definition, never into it.
4. `scripts/characterize_no_fifo_close_markets.py` re-run — the 161
   population is a structurally disjoint mechanism (orphan SELLs, not
   pending trade_results); **predicted: unchanged**, and a nonzero change
   here would itself be a signal something unexpected happened.
5. `scripts/characterize_placebo_pending_exposure.py` re-run (or its
   successor once these 2 traders' stuck positions are evaluated) —
   `0x5cfd8811...`'s 26 stuck positions (9 post-split) should now have
   real `trade_result` values and enter `measure_oos` for the first time;
   **the true placebo survivor edge is expected to move**, direction
   already characterised as mixed/offsetting between the 2 traders (see
   `2026-08-19-placebo-pending-exposure.md` Q5) — not re-predicted more
   precisely here, since re-predicting the exact shift would itself be
   close to recomputing the placebo, out of scope for a pre-registration.
6. Cohort qualifying/surviving counts (`build_presplit_cohort` /
   `true_oos_survivors`, live re-derivation) — expected to shift by some
   amount as newly-evaluated positions can change `n_pairs`, `ci_lo_t`,
   and `shrunk_mean` for any trader whose stuck positions get resolved.

**This is not attempted to be minimized.** The point of measuring before
and after, and publishing both, is that the shift is attributable to a
known, documented mechanism (clearing a specific, characterised backlog)
rather than an unexplained drift discovered after the fact — the failure
mode `2026-08-16`'s reproducibility audit was built to catch.

---

## 5. Safety

**[V]** Before the first run (dry or live): **WAL-safe online backup**
via `scripts/backup_database.py` — confirmed it uses SQLite's online
backup API (`source_conn.backup(dest_conn)`, `backup_database.py:36-39`,
comment: *"safe against a live WAL-mode writer, unlike a raw file copy
which can capture a torn/inconsistent snapshot mid-write"*) followed by an
integrity check (`PRAGMA integrity_check`) before accepting the backup —
this is the correct tool per CLAUDE.md's standing instruction, not a raw
file copy.

**[V]** First live run: **manual, detached, observed** —
`nohup python3 scripts/backfill_trade_results_geo.py > logs/geo_backfill_first_run.log 2>&1 & disown`,
not run inline in an interactive session that could be interrupted by a
disconnect. Justified by: two box crashes in the last month (per this
task's own framing, consistent with the 2026-08-18 93-minute unclean-shutdown
event already characterised), and this touches tens of thousands of rows
in a single run (24,707 trades, `UPDATE trades SET trade_result = ...`
batched at 1,000/commit per `backfill_trade_results_geo.py:96-108`, so a
mid-run crash loses at most one uncommitted batch, not the whole run — WAL
+ per-batch commit means a crash mid-run is recoverable by simply
re-running the script, since its `WHERE trade_result = 'pending' OR ... IS NULL`
predicate is naturally idempotent over already-evaluated rows).

**[V] Sequencing:** dry-run first (`--dry-run`, read-only, prints the
predicted won/lost/invalid split and traders-affected count without
writing) → compare against the blast-radius predictions in §4 → only if
that comparison looks sane, live run (backed up, detached, observed to
completion) → only after the live run completes cleanly AND the §6
verification passes, wire the step into `daily_maintenance.py`'s `STEPS`
list at the position specified in §1.

---

## 6. Non-tautological verification

**[V]** A `daily_maintenance.log` line reading `OK` for the new step is
**not sufficient evidence** — the script could run, touch zero rows (e.g.
if a WHERE-clause typo silently matched nothing), and still exit 0.
Required, falsifiable checks:

1. **The invariant count must move.** Re-run
   `characterize_pending_invariant_regression.py` immediately before and
   after the live run; `check_pending_geo` must drop by an amount
   consistent with the dry-run's predicted total (won + lost + invalid
   counts, since `invalid` trades also leave `trade_result='pending'` and
   so also leave the invariant's count, per `backfill_trade_results_geo.py`'s
   own `evaluate_trade()` returning `'invalid'` rather than leaving the
   column untouched). A count that doesn't move, or moves by a
   wildly different amount than predicted, means the wiring did not do
   what it claims regardless of exit code.
2. **The before/after population figures in §4 must change in the
   predicted direction** — specifically: the 92-population must not grow;
   the 161-population must stay exactly unchanged (a disjoint mechanism);
   `0x5cfd8811...`'s stuck-position count must drop to (close to) 0.
3. **Traders-affected count must match between dry-run and live-run** —
   the dry-run's `[DRY RUN] Traders affected: N` line compared directly
   against the live run's `Traders updated : N` line (`backfill_trade_results_geo.py:82,124`).
   A mismatch means the population shifted between the two runs (expected
   to be small/explainable given live trading continues) or something is
   non-deterministic in a way worth understanding before trusting the
   step daily.

A run that reports OK but fails any of 1-3 is treated as **not verified**,
regardless of exit code, and blocks wiring the step into `daily_maintenance.py`
until understood.

---

## 7. Rollback

**[V]** If the first run produces an unexpected population change, an
error, or a count moving the wrong direction:

1. **Do not wire the step into `daily_maintenance.py`.** The pre-registration's
   phase-2 wiring step is explicitly gated on the first manual run
   completing cleanly (§5) — an unexpected result means that gate was not
   cleared, full stop.
2. **Restore from the pre-run backup** (`scripts/backup_database.py`'s
   output under `backups/`) if the unexpected change looks like data
   corruption rather than a merely-surprising-but-correct evaluation
   result — distinguish the two by checking whether the affected
   `trade_result` values are internally consistent with
   `position.outcome == market.winning_outcome` (the same empirically-verified
   rule from `2026-08-19-placebo-pending-exposure.md`, 0 exceptions across
   350,008 positions) rather than restoring reflexively on any surprise.
3. **If the result is surprising but internally consistent** (e.g. the
   won/lost split is very different from the dry-run's prediction because
   real trading happened in between, or a much larger `invalid` count than
   expected surfaces a data-quality issue in `outcome_bet`/`side`
   population) — do not restore; instead write a follow-up characterisation
   doc (same convention as this arc) before deciding whether to proceed,
   rather than either silently accepting it or reflexively reverting.
4. **If a hard error/crash occurs mid-run** — per §5, this is recoverable
   without restore: `backfill_trade_results_geo.py`'s predicate is
   idempotent over already-evaluated rows (only matches `trade_result =
   'pending' OR trade_result IS NULL`), so simply re-running it picks up
   exactly where the crash left off. Restore is reserved for corruption,
   not for a resumable interruption.

---

## 8. What this does not fix

**[V] This wires one script. It does not address the pattern.** Confirmed
this session: `backfill_trade_results.py` (the other `TradeEvaluator`
caller) remains unwired in both `daily_maintenance.py` and `crontab -l`.
`run_tests.py` has no trigger of its own outside of `daily_maintenance.py`
calling it directly (`run_test_suite()`, `daily_maintenance.py:86-130`) —
functionally wired, but only as a hardcoded call inside another script,
not as an independently schedulable/auditable unit. This is the third
instance of the same shape in this arc alone (the corrected item-8 claim
in "Background" above notwithstanding) — a remediation or verification
script exists, is documented, and is not invoked by anything on a
schedule until someone notices the gap by chance (as
`backfill_trade_results_geo.py` was, via the pending-invariant
regression investigation). **This pre-registration deliberately does not
propose a general fix for the pattern** — that is a separate,
larger-scope question (an inventory of all standalone scripts vs. what
actually runs them) that should be raised on its own, not folded into a
single-script wiring decision.

---

## Summary — what happens next, and only after this is read

1. Read this document. Nothing below happens until it is reviewed.
2. `python3 scripts/backup_database.py` (WAL-safe, verified backup).
3. `python3 scripts/backfill_trade_results_geo.py --dry-run` — compare
   output against §4's predictions.
4. If sane: `nohup python3 scripts/backfill_trade_results_geo.py >
   logs/geo_backfill_first_run.log 2>&1 & disown` — manual, detached,
   observed to completion.
5. Run the §6 non-tautological verification. If it fails, follow §7.
6. If it passes: add the new step to `scripts/daily_maintenance.py`'s
   `STEPS` list at the position specified in §1 (between "Evaluate new
   trader results" and "Reconcile geo resolved counts [post-eval]"),
   `non_blocking=True`.
7. Track `check_pending_geo` daily for `D=7` days / `K=5` readings against
   the §3 criterion (N=300). Re-derive N from real post-clearance data
   once available, rather than treating this session's estimate as final.
8. Raise the broader "unwired remediation scripts" pattern (§8) as its own
   item, separately.

---

*Generated 2026-08-19. Sources: `scripts/daily_maintenance.py` (STEPS list
lines 32-81, run_test_suite lines 86-130), `scripts/backfill_trade_results_geo.py`
(full read), `scripts/backup_database.py` (lines 28-64),
`scripts/audit_invariants.py` (check_pending_geo lines 279-300),
`2026-08-19-pending-invariant-regression.md` (`9fb436d`),
`2026-08-19-placebo-pending-exposure.md` (`02ca3e6`), `crontab -l`, live
DB queries against `data/polymarket_tracker.db` (organic-inflow 14-day
trade-timestamp query, canonical/v2f population re-derivation via
`characterize_pending_resolution_inconsistency.py`). No code changed, no
script executed beyond read-only queries and the pre-existing committed
characterization scripts.*
