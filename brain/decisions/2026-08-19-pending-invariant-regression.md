# 2026-08-19 — `audit_invariants.py` "pending on resolved" regression

Read-only characterization. No repair, backfill, or reconciliation performed.
Every figure below is marked **[V]** (directly verified this session) or
**[I]** (inferred/reasoned, not directly observed). Reproducible via
`scripts/characterize_pending_invariant_regression.py` (first-repo,
committed this session), which regenerates the live counts, the market/
trader overlaps, and the true Objective-2 membership sets used throughout.
Artifact: `data/characterizations/pending_invariant_regression_20260819T172940Z.json`.

---

## Background (as given, now verified)

**[V]** Today's `daily_maintenance.py` step 7 (`audit_invariants.py`, the
pre-ELO gate) recorded, per
`brain/agent-outputs/data-audit/2026-08-19-audit.json` (run at 06:02:09):
"pending on resolved non-gap markets (flagged traders)" = **60,345**
(REGRESSION; was **0**/PASS on 08-18) and "pending on resolved non-gap
geo/elections markets" = **36,213** (REGRESSION; was **24,082** on 08-18).
Gate exited OK regardless (see Q7).

---

## Q1 — What does the invariant actually measure

**[V]** Read directly from `scripts/audit_invariants.py:252-300`. Both
checks are `SELECT COUNT(*) FROM trades tr JOIN markets m ...` — **the unit
is trade rows**, not markets, not positions, not (trader, market) pairs.

- `check_pending_flagged` (line 254): `trades JOIN markets JOIN traders`,
  `trade_result='pending' AND m.resolved=1 AND non-gap AND t.is_flagged=1
  AND t.research_excluded=0`. **No category restriction** — any market.
- `check_pending_geo` (line 281): `trades JOIN markets` only (no traders
  join), `trade_result='pending' AND m.resolved=1 AND non-gap AND
  m.category IN ('Geopolitics','Elections')`. **No trader-flag
  restriction** — every trader, flagged or not, excluded or not.

Live re-derivation (this session, `characterize_pending_invariant_regression.py`):
distinct markets in the geo population = **2,650**; distinct traders =
**1,730**. Confirms these are large, broad row-level counts, not the
narrow market-level population the 92-figure uses.

---

## Q2 — Same population as the 92, at different units?

**[V] No — genuinely different scope, not just different units.**
Compared `check_pending_geo`'s predicate against
`scripts/characterize_pending_resolution_inconsistency.py`:

| | 92-population | geo-invariant population |
|---|---|---|
| Unit | markets | trade rows (2,650 distinct markets) |
| Scope | canonical **symmetric-diff-only** markets (v2f's implicit population subtracted out) | **any** resolved, non-gap, Geo/Elections market |
| Time bound | `tape_end < T_split` (2026-04-01) | none — DB-wide |
| Trade condition | **every** position's entry trade pending | **any** trade row pending (not restricted to entry trades) |

Ran the actual intersection: of the 92 markets, **all 92 are contained
in** the 2,650-market geo-invariant population (`intersection=92,
pending92-minus-geo=0`). So the 92 is a strict, much-narrower subset of
what the invariant counts — same underlying condition family
(`trade_result='pending' AND resolved=1`), but the invariant is far more
permissive on every axis (time, entry-vs-any-trade, symmetric-diff
restriction). **They are not measuring the same population "at different
units" — the invariant's population structurally contains the 92's, plus
~2,558 markets the 92-script's tighter definition excludes.**

---

## Q3 — Did the check change, or did the data move?

**[V] The data moved; the check did not.**
`git log --oneline -- scripts/audit_invariants.py` — last commit
`fc6c6c5` (2026-07-14), nothing between 08-18 and 08-19. `FLOOR_PENDING_FLAGGED`
and `FLOOR_PENDING_GEO` are hardcoded `0` (lines 53-54), untouched by that
or any later commit. Confirmed by running the exact check functions
(`ai.check_pending_flagged`, `ai.check_pending_geo`) imported directly from
the unmodified module against the live DB — same predicate, real counts.

---

## Q4 — What moved, and by what mechanism

**[V] Two different mechanisms for the two checks — established with
row-level evidence, not assumed.**

**`check_pending_flagged` (0 → 60,345 → back to 0, all within ~35 hours):**
its predicate — `is_flagged=1, research_excluded=0, trade_result='pending',
resolved=1` — is **exactly** the target population documented in
`scripts/evaluate_new_trader_results.py`'s own docstring ("Targets:
is_flagged=1, research_excluded=0, trade_result='pending', in a market
where resolved=1..."). That script runs as **daily_maintenance step 21**,
**after** the audit gate at **step 7**. So every day's audit reads
whatever backlog accumulated since the *previous* day's step 21 finished —
before *that* day's own step 21 clears it again. Live re-check just now
(17:29 UTC, ~9h after today's maintenance completed): **0** — fully
drained, consistent with step 21 having run today. **[I]** Exactly what
accumulated between 08-18's step-21 clear and 08-19's step-7 read cannot be
reconstructed: today's audit ran with `--verbose` off, so `examples: []`
was persisted — no row-level snapshot of the 60,345 exists, and the
population is already gone (evaluated to won/lost). This specific question
is **UNRESOLVED** (see Q6).

**`check_pending_geo` (24,082 → 36,213 peak → 24,704 now — net +622 vs
yesterday's baseline once the same-day peak decays):** **no daily
evaluator exists for this population.** `scripts/backfill_trade_results_geo.py`
exists specifically to close this exact gap — its own docstring: *"evaluate_new_trader_results.py
only processes is_flagged=1 traders. After the category backfill
reclassified ~11K markets, many traders have trade_result='pending' on
resolved geo/elections markets. This script fixes that gap regardless of
is_flagged status."* — but it is **not wired into `daily_maintenance.py`**
(`grep` for it in the maintenance script: no match). This is a **known,
pre-existing, standing gap**, not a new regression. Row-level evidence for
the still-live population: top offenders are a handful of very
high-volume markets — "Will the Iranian regime fall by June 30?" (1,032
pending rows), a Peru presidential-election market (714), an LA mayoral
market (639) — all `resolved=1` with `winning_outcome` set and
`last_checked` in **early July 2026**, i.e. **not** touched today; this
specific backlog has sat undisturbed for well over a month. Data-source
split on the 24,704: **15,719 (63.6%) `background_backfill`**, 8,985
(36.4%) `polymarket_api`. `monitoring/background_backfill_worker.py:305-311`
confirms every backfilled trade is inserted with `trade_result` **hardcoded
to `'pending'`**, never evaluated at ingest time — a real, live-verified
contributing mechanism for the backfill share, independent of the
long-standing live-ingestion gap above.

**Net read:** this is a **genuine, structural, standing gap** in trade-result
evaluation coverage — not a data-corruption event and not new today — that
the audit only started reporting because nothing had previously measured
it this way. It fluctuates day to day depending on backfill/ingestion
timing and where each check's read lands relative to step 21, on a
generally-growing base of never-evaluated historical trades outside the
`is_flagged` fast path.

---

## Q5 — Was 08-18 actually zero?

**[V] Yes, a true zero, not an artifact.** `scripts/audit_invariants.py`'s
`_count()` helper (line 120) does a bare `cur.execute()` / `fetchone()`
with **no exception handling** — a query error would propagate and crash
the whole script (which would show as a maintenance step FAILURE, not a
silent 0). `daily_maintenance.log` shows `audit_invariants.py` exited OK
on both 08-18 and 08-19. The floors are hardcoded constants, unaffected by
data. No evidence of the check being skipped, erroring, or measuring a
different predicate that day (same file, same commit, both days — see Q3).

---

## Q6 — Does it disturb yesterday's PERSISTENT-BOUNDED verdict?

**[V] Partially non-zero — reported precisely, not rounded.**
Re-derived the TRUE Objective-2 populations live (same method as
`characterize_orphan_sell_scope.py`: `build_presplit_cohort` +
`match_control`, not the 295-trader proxy):

| population | n (today) |
|---|---|
| true pre-split cohort | 155 |
| **true OOS survivors** (the actual measured-edge population) | 126 |
| true placebo pool | 155 |
| true placebo survivors | 113 |

(Counts drifted slightly from 08-18's 148/120/148/108 — expected given the
population is defined by current DB state, not a frozen snapshot; not
itself investigated further here, out of scope.)

Intersected against the **currently still-pending** geo-invariant
population (1,730 traders — the `check_pending_flagged` population is
unavailable, see below):

- × true pre-split cohort: **3 traders** (`0x604e4385...`, `0x6bcc2265...`,
  `0xc97b0b2a...`) — **non-zero**.
- × **true OOS survivors** (the set whose post-split edge is actually
  measured for the headline result): **0 — zero overlap.** All 3 cohort
  hits are pre-split-cohort members who did not survive to the OOS
  measurement window, so their pending trades cannot touch the measured
  edge under the current metric definition.
- × true placebo pool: **4 traders** (`0x54b5eacb...`, `0x5c7482fa...`,
  `0x5cfd8811...`, `0x89619f49...`) — non-zero.
- × true placebo survivors (the placebo side of the actual OOS
  comparison): **2 traders** (`0x54b5eacb...`, `0x5cfd8811...`) —
  **non-zero.**

None of these 7 traders' pending markets overlap the disjoint 92-market
population (checked directly).

**So: this does reach cohort/placebo *membership*, and specifically
reaches 2 traders on the *placebo-survivor* side of the actual OOS
comparison — but it does not reach the *treatment* side's measured-edge
population (cohort survivors).** This is a real, if narrow, difference
from yesterday's clean zero-overlap findings and is flagged as such per
the standing instruction, rather than folded into "still disjoint."
Materiality was not assessed here (how many of each trader's markets/
dollars this represents) — that would be the natural next step if this is
picked up.

**[I] UNRESOLVED, separately:** the `check_pending_flagged` population
that spiked to 60,345 this morning cannot be intersected against the
cohort at all — it already self-drained to 0 by the time this
investigation started (see Q4), no row-level snapshot was persisted
(`examples: []`, verbose was off), and there is no other way to
reconstruct which specific trader/market rows it contained. Whether *that*
population touched cohort survivors before being evaluated away is
genuinely unknown and not recoverable from this database. Flagging rather
than assuming either direction.

---

## Q7 — Why didn't the gate block

**[V]** Both checks return tier `2` (`scripts/audit_invariants.py:276,300`).
The gate's exit logic (`main()`, lines 931-950): `sys.exit(2 if n_crit > 0
else 0)`, where `n_crit` counts only tier-1 `CRITICAL` results. Tier-2
`REGRESSION` findings never affect the exit code, by design — confirmed
directly in code, not inferred from behavior. This is the gate working as
designed (block on impossible states, not on regressions), not a bug in
the gate itself — though the gap this investigation surfaced (no daily
evaluator for the geo/elections population, and no visibility into what
the flagged-population spike actually contained) is a legitimate coverage
question for whoever owns tier-2 alerting policy.

---

## Verdict

**Not a single clean bucket — reported as two parts rather than forced
into one, per the standing instruction not to round toward a cleaner
verdict:**

- **`check_pending_flagged` (0→60,345→0): REAL, self-healing, mechanism
  identified (Q4) — but UNRESOLVED on cohort touch**, because the
  population that spiked is no longer reconstructable. Not a code change,
  not corrupted data — a genuine backlog that accumulated and was cleared
  by the system's own daily evaluator, whose cohort-overlap at peak is
  unknown and unknowable from this database.
- **`check_pending_geo` (24,082→36,213→24,704): REAL AND TOUCHING**,
  specifically and narrowly: 3 traders touch the true pre-split cohort,
  4 touch the true placebo pool, **2 of those are placebo *survivors* —
  i.e. inside the population actually used for the OOS comparison's
  placebo side.** It does **not** touch the true cohort *survivors* — the
  treatment side's measured-edge population — so the headline OOS effect
  size itself is not directly implicated. This is a **known, standing,
  pre-existing structural gap** (a missing daily evaluator for the
  non-flagged/all-category population, root-caused in
  `backfill_trade_results_geo.py`'s own docstring to an earlier
  ~11K-market category backfill), not new data corruption from today.

**This does not fully reopen yesterday's PERSISTENT-BOUNDED verdict**
(that verdict was about the disjoint 92-market population, confirmed here
to be a strict subset with zero incremental traders beyond what it already
covered), **but it does mean the placebo side of the actual Objective-2
OOS comparison currently has 2 traders with unevaluated pending trades on
resolved Geo/Elections markets outside the 92/166 populations already
characterized.** Whoever picks this up next should start by assessing
materiality (how many markets/dollars for those 2 + 3 traders) and by
wiring `backfill_trade_results_geo.py` into daily maintenance or
otherwise deciding this gap is acceptable — both currently undecided, out
of scope for this read-only pass.

---

*Generated 2026-08-19. Sources: `scripts/audit_invariants.py` (git history
via `git log --oneline -- scripts/audit_invariants.py`),
`scripts/evaluate_new_trader_results.py`, `scripts/backfill_trade_results_geo.py`,
`monitoring/background_backfill_worker.py`,
`brain/agent-outputs/data-audit/2026-08-18-audit.json` and
`2026-08-19-audit.json`, `logs/daily_maintenance.log` (first-repo),
`data/characterizations/pending_resolution_inconsistency_20260819T170702Z.json`,
and this session's new
`scripts/characterize_pending_invariant_regression.py` →
`data/characterizations/pending_invariant_regression_20260819T172940Z.json`
(first-repo, both committed this session).*
