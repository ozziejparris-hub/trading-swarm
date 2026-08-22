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
| 1 | Extend `backfill_market_dates.py`'s `_fetch_by_clob` with a `mark_market_resolved()` assertion branch — scope revised 2026-08-21, see amendment note at the end of this document | Nothing (code change) | A dry-run diff artifact + the 317-market correctness pre-check, now a required gate (§B) |
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
- **Step 1's read-only correctness pre-check against the 317-market Q2
  census population (§B item 3, promoted to a gate 2026-08-21) does not
  reproduce the freshly-re-derived expected resolved count, within a
  small tolerance** → stop. Do not proceed to step 2 or step 4. This is
  not hypothetical — it is what happened on the first attempt (a clean
  diff, an inert branch); see the amendment note at the end of this
  document.
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

**Amendment, 2026-08-21 (`d41d02b`) — step 1's scope, revised after its
first stop.** Full account: `2026-08-21-step1-implementation.md`. The
first attempt built the assertion branch exactly as originally specified
here, passed the branch-split dry-run diff cleanly, then failed a
read-only correctness pre-check against the known 317-market Q2 census
population by a wide margin (0 markets classified resolved against a
freshly-re-derived expected ~203). Traced to root cause, not patched
around: `_fetch_by_clob`'s existing success gate —
`if data.get("end_date_iso") or data.get("endDateIso")` — silently
discards a fetched, fully-parsed CLOB response whenever the market's
`end_date_iso` is null, regardless of whether `closed`/`tokens[].winner`
are present and usable. Verified: 316 of 317 markets in the Q2 census
population returned no response through this function at all; direct
sampling of 3 of them confirmed all three are `closed: true` with a real
winning token and `end_date_iso: null` — the response was fetched and
discarded before the new assertion branch (confirmed correct in isolation,
at the unit level) ever saw it.

**Root cause, stated precisely:** the gate conflates two distinct
questions — "did we get a usable date?" and "did we get a usable
response?" — and answers both with the date test. That was correct for
the only caller that existed when it was written (the proxy branch, which
only ever wanted a date) and became wrong the moment a second caller
needed a different thing from the same response. This is the same shape
as the design's own §A finding about `resolution_date` carrying two
meanings in one column — one artifact serving two questions, silently
breaking the newer one the moment it's added.

**The change, added to step 1's scope:** separate the gate from the
fetch. `_fetch_by_clob` returns the parsed response whenever the HTTP call
itself succeeds (a genuine fetch failure — bad status code, malformed
JSON, network error — is still `None`); each caller applies its own
usability test against the returned dict. The proxy branch keeps its
existing `end_date_iso`/`endDateIso` requirement, applied by the proxy
branch itself, exactly where it already runs today — its behavior is
preserved exactly, not merely intended to be. The assertion branch applies
its own test: `closed == true` AND some token has `winner == true`.

**Two alternatives considered and rejected:**
- **A second, dedicated fetch function for the assertion branch.**
  Rejected as duplicative — this project has been consolidating away from
  exactly that pattern (`2026-08-19-trade-evaluator-repoint.md`'s three
  near-identical scripts folded onto one canonical function; the
  discovery-fix assessment's own elegance judgement,
  `2026-08-21-discovery-fix-assessment.md`, choosing to extend
  `backfill_market_dates.py` rather than build a new CLOB-calling script
  from scratch). Two functions making the identical HTTP call for two
  different reasons is the same coherence cost this arc has twice already
  ruled against.
- **A mode flag on the existing function** (e.g.
  `_fetch_by_clob(session, condition_id, require_date=True)`). Smaller
  blast radius than a full separation, but retains the conflation inside
  one function's control flow rather than removing it — the next caller
  with a third requirement would need a third flag, not a third,
  independent test. Rejected in favor of the cleaner separation.

**The verification bar is unchanged and now harder to meet — stated
explicitly, not left implicit.** Item 2 below's requirement that the
proxy branch show ZERO behavioral difference now applies to a refactor of
shared code (the gate moving out of `_fetch_by_clob` and into each
caller), not merely to an additive branch alongside untouched code. The
proxy branch must produce byte-identical decisions across its full
candidate population despite the gate having moved — same markets
touched, same markets skipped, same `end_date` values. If it does not,
that is a stop, not an acceptable consequence of refactoring.

**Deferred items, unchanged by this amendment.** `ORDER BY market_id` and
pacing remain deferred exactly as originally scoped (§C) — `ORDER BY`
belongs to the sweep driver (step 4), since the production invocation's
`--limit` means adding an ordering would change *which* markets are
selected, a real behavioral difference outside a refactor's scope; pacing
is an additive `--sleep` parameter defaulting to the current `0.1s`, so
today's scheduled invocation is unaffected and step 4 can pass `0.25`
explicitly. Neither is affected by the gate-separation change above.

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
       building nothing. **Now a refactor check, not merely an additive
       one** (2026-08-21 amendment, above) — the gate the proxy branch
       depends on has moved out of `_fetch_by_clob` and into the proxy
       branch's own call site; this diff is what proves that move changed
       nothing observable.
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
3. **Read-only correctness pre-check against the 317-market Q2 census
   population — a required gate, not optional.** Added 2026-08-21
   (`d41d02b`), after this exact check — introduced ad hoc, as an
   "additional" item, in step 1's first attempt — is what actually caught
   the inert branch. **The branch-split diff (item 2) passed cleanly on
   that same attempt while the assertion branch had, in practice, zero
   reach — a clean branch-split diff alone would have let an inert change
   ship.** It is necessary but not sufficient: it only proves the
   untouched branch stayed untouched, and says nothing about whether the
   new branch actually does anything when the production-scope candidate
   population happens to exercise it zero or few times (as it did).
   Method: run the modified code's own extraction/classification functions
   (not a reimplementation) against the freshly re-derived Q2 census
   population — re-derive live via `2026-08-20-discovery-gap-sizing-prereg.md`
   §3's predicate, do not hardcode the 08-20 figure of 203/98/16 as
   gospel, since the population drifts. **Required to proceed:** the
   assertion branch's resolved count must land within a small tolerance of
   the freshly-derived expected count, and the indeterminate rate must be
   consistent with the sizing run's ~5% baseline. A materially different
   result — as happened on the first attempt (0 resolved found against an
   expected ~203) — is a stop, per falsification condition 1 (§I, amended
   2026-08-21), not a tweak.
4. **What a failed diff or failed pre-check means: stop, do not proceed.**
   Per the task's explicit instruction — this is not "investigate and
   adjust the fix until the check passes," it is "a failure means the
   change as specified is wrong, fix it, and re-run the *entire*
   verification bar from a clean baseline, not a delta on top of the
   failed attempt." No partial credit — a diff that's clean on one branch
   but not the other (step 1), clean on 95% of markets but not all (step
   3), or a clean diff paired with a failed correctness pre-check (item 3
   — exactly what happened on the first attempt) does not satisfy this
   bar, per the exact wording Stage 1 already used for itself (§G's
   migration table: "A diff that's clean only on one branch does not
   satisfy this stage").
5. **Test suite**, both changes: `run_tests.py` must show no new failure
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

**Amended 2026-08-22 (`a972731`, `9dc11e3`): the 0.25s figure is the
pacing directive, not the measured per-call cost — those are different
numbers, and both are now known.** Tranche 2 (5,000 candidates, 10
batches, all abort-condition-clear) measured **0.416s/call, averaged
across all ten batches in a tight ±3% band (202.6s–214.0s per 500-row
batch)** — real CLOB round-trip time on top of the deliberate 0.25s
sleep, not sleep-timer drift or an anomaly in one batch. **The 0.25s
pacing directive itself is unchanged** — the measured figure is the
*result* of that pacing plus real API overhead, not a reason to speed it
up or slow it down.

A fresh population count [V] (same predicate, live query,
`2026-08-22-sweep-execution-model.md` §5) returns **513,770** — the
**first time this figure has been below the original 515,491 planning
estimate**, not a concerning decrease: tranches 1 and 2's combined 4,926
resolutions (203 + 4,723) have outpaced organic new-market arrival since
this document was written, exactly the self-shrinking behavior the
resumability design (below) predicted. **Re-projected runtime at the
measured rate: 513,770 × 0.416s ≈ 213,728s ≈ 59.4 hours ≈ 2.5 days** —
not the ~36-hour planning figure. This spans **three nights**, not one,
and materially changes the execution-model and concurrency reasoning
below.

**Amended 2026-08-22 (`b5fd6f4`): a structurally-unresolvable cohort
carved out of the candidate population — a finding about the data, not a
threshold change.**

Segment 1 (the first run under the segmented execution model, above)
paused at batch 12/206 on a batch-level indeterminate rate of 13.6%
(n=500, five times the n=100 floor — a real signal, not the small-sample
noise the floor amendment addressed). Root-caused, not pattern-matched
from one batch: **all 67 of that batch's `no_clob_response` markets share
a precise structural signature — a synthetic `market_id` ending in a long
run of zeros (`...0000000000000000000000000000`), an empty
`condition_id`, an empty `api_id`, and a multi-leg compound-bet title**
(e.g. *"Will United States win on 2026-06-19? AND Will Brazil win on
2026-06-19? AND ..."*) — **combo/parlay markets, never single-outcome
markets CLOB tracks, and permanently incapable of returning a CLOB
response by construction, not transiently unavailable.**

**Scope, quantified [V]:** **15,427 such markets exist in the current
candidate population** (live query: `... AND market_id LIKE
'%0000000000000000000000000000'`, same predicate otherwise). Confirmed
they carry real trade records (`EXISTS (SELECT 1 FROM trades WHERE
trades.market_id = markets.market_id)` returns all 15,427) — they are not
a zero-trade/stub artifact, they are traded positions on a compound bet
type this write path was never meant to resolve. Within segment 1's own
market-id-ordered list, 15,208 of them cluster contiguously across an
estimated 35 more batches (13–47) — continuing unassisted would have
re-tripped the same threshold repeatedly, not once.

**Carved out of the sweep's candidate population.** The exclusion
predicate: `... AND market_id NOT LIKE '%0000000000000000000000000000'`,
added to the sweep's own `(resolved = 0 OR resolved IS NULL) AND
(end_date IS NULL OR resolution_date IS NULL)` predicate everywhere it is
used (population counts, segment materialization, the abort-condition
denominators).

**Why this is not threshold-moving, stated precisely:** the sweep's
predicate is a *proxy* for "might be resolvable via CLOB" — resolved=0
and no recorded date are necessary conditions for a market to still be a
live candidate, but they are not sufficient, and for this cohort the
proxy is simply wrong. These markets were never sweep candidates in the
sense the predicate was designed to capture; they fail the thing the
predicate is a stand-in for, not an edge case of it. **Excluding a
population that provably cannot produce a result is different in kind
from relaxing a threshold to tolerate results already disliked** — the
10%/20% rates, the n=100 floor, and every other abort condition are
unchanged, and continue to apply to the (corrected) candidate population
exactly as before.

**Two alternatives considered and rejected, named so this isn't revisited
as unconsidered:**
- **Processing the cohort at a relaxed threshold** — walking all ~35
  affected batches (~4 hours, ~15,000 CLOB calls) at a loosened
  indeterminate-rate tolerance. Rejected: guaranteed zero yield (every
  call in this cohort returns `no_clob_response` by construction, not by
  chance), for real API cost and wall-clock time, in exchange for
  learning nothing not already established this session.
- **Stepping through manually, expecting ~35 repeated pauses** —
  the most conservative option on its face, but rejected for a specific
  reason: deliberately tripping an abort condition dozens of times on a
  known, understood cause corrodes the threshold's meaning as surely as
  moving the number would. A condition that fires routinely and is
  routinely waved through stops functioning as a signal.

**Verification required before this carve-out is applied — not
pattern-matched from segment 1's 67 rows, per the task that produced
this amendment.** The implementing task must establish, and record
having established:
1. **A sample of the 15,427 genuinely lacks usable identifiers** — not
   assumed from the batch-12 subset alone; drawn fresh from the full
   15,427 and checked for empty `condition_id` and `api_id` directly.
2. **No legitimate, resolvable market is caught by the exclusion
   predicate** — the zero-padded-suffix pattern must be checked against
   a sample for false positives (a real market whose genuine identifier
   happens to end in zeros by coincidence, however unlikely that is for
   a hash-shaped `market_id`).
3. **The predicate is stated exactly** (as above) **and its row count
   re-derived live** at implementation time, not carried forward as
   today's 15,427 without re-checking, since the population continues to
   change.

**A failure at any of these three blocks the carve-out** — it is not
optional verification, it is the condition under which excluding a
population "because it cannot produce a result" is itself established
rather than assumed.

**Revised population and runtime, post-carve-out:** current candidate
population (live, `b5fd6f4`) is **507,956** (513,770 at tranche 2's draw,
minus segment 1's own 5,814 resolutions, which correctly shrank the
self-shrinking set by exactly that amount — confirmed, not merely
expected). **Minus the 15,427-market carve-out: 492,529 candidates.**
**Re-projected runtime at 0.416s/call: 492,529 × 0.416s ≈ 204,892s ≈
56.9 hours ≈ 2.37 days** — modestly less than the pre-carve-out ~59.4
hours, since the excluded cohort was never going to be productive time
regardless.

**A correction to `2026-08-20-discovery-gap-sizing-result.md`'s Q1
estimate, narrow and quantified from existing figures — not
re-sampled.** That document's ~99.3% pooled-O resolved-fraction estimate
(N=510,378, p̂=99.28%, ≈506,700 estimated resolved) was computed over a
population that necessarily included this same combo/parlay cohort
(these are old, structurally-distinct markets, not a recent arrival —
reasonably assumed present in similar count on 08-20 as today, though not
independently re-counted for that date) — and, since all 15,427 have
trade records, they fall within the O stratum (509,585), not Z. **If the
O stratum's non-combo markets retain the observed 99.3% rate and the
combo subset is corrected to its true, structural 0%** (rather than
implicitly averaged in at 99.3%): corrected O-stratum resolved ≈
(509,585 − 15,427) × 0.993 ≈ 490,699, and corrected total estimated
resolved ≈ 491,347 of 510,378 ≈ **96.27%**, versus the reported 99.28% —
**a ≈3.0 percentage point, ≈15,300-market downward correction.** [I —
this assumes the full 15,427 count applied unchanged to the 08-20
population and that they were not disproportionately represented in the
150-market O sample itself; not verified against that sample's actual
membership.] **This does not change any conclusion drawn from that
document.** The boundary check's own finding stands: this is "a real,
large population of resolved-but-unrecorded markets, not an artifact of
where or how this method looked" — 96.3% undiscovered-resolved is still
an overwhelming majority, the age-distribution and ingestion-path
findings are untouched by this correction, and the corrected figure still
supports every downstream decision (the sizing, the staged rollout, the
segmented execution model) made on the strength of "the overwhelming
majority of this population is resolved and undiscovered." Not re-run;
this is a narrow numerical correction to one reported percentage, not a
re-derivation of the underlying result.

**The general lesson, recorded because it will recur:** tranche 2's
seeded random sample would have scattered this cohort at roughly 1.5% per
batch (15,427 of ~510k ≈ 3%, diluted across ten batches of a random
draw) — invisible against a ~3.5–4% baseline. Segment 1's scan-order walk
concentrated it, because `market_id` sorts by shared ID *format*, not by
insertion time — the mechanism is precise (a lexicographic sort
clustering a common suffix), not the vaguer "old markets cluster
together" intuition. **A random sample characterizes the average of a
population, not its shape** — validating a method on a sample and then
executing it in scan order can surface cohorts the validation was never
positioned to see, however large and however carefully the sample was
drawn. This is the **second** dead cohort found this way in this arc,
after the ~98-row, CLOB-purged, 2020-era markets at the head of
`backfill_market_dates.py`'s own insertion-ordered scan (step 2,
2026-08-21) — different root cause each time (purged legacy markets,
then combo/parlay markets never real CLOB markets at all), same
structural lesson: **scan order is a lens a random sample does not use,
and it can show you populations the sample's averaging hid.**

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

**Amended 2026-08-22 (`a972731`, `9dc11e3`): execution mode revised from
a single continuous detached run to chunked, scheduled segments; this
section previously said nothing about `daily_maintenance` concurrency at
all — that gap is closed below.**

#### Execution mode: chunked and scheduled, not one continuous run

At the ~36-hour planning estimate, a single continuous detached run
(`nohup`, per the bullet above) was reasonable — a human could stay
loosely aware of it across roughly one overnight period. **At the
revised ~59.4 hours (three nights), that reasoning no longer holds.**
Reconsidered explicitly, not just noted: a systemd unit with
`Restart=on-failure` was assessed again given the longer runtime and
**still rejected** — not because 60 hours doesn't matter, but because
automatic restart applies no judgment about *whether* restarting
immediately is wise at that moment (e.g. mid-incident, as
`2026-08-22-overnight-incident.md` demonstrated for an unrelated
process), and because the actual per-interruption cost is small enough
(below) that automating the restart buys little.

**Adopted instead: chunked, scheduled segments, launched deliberately —
not a fixed segment-size rule, but bounded by two things that already
exist:** the existing 500-row batch/checkpoint boundary (a segment is
some whole number of batches, chosen at launch time, not mid-batch), and
the concurrency window below (a segment is scheduled to avoid, not
overlap, `daily_maintenance`'s 06:00–~10:00 UTC window). This is the
only execution mode in which a human applies judgment about whether
conditions are currently favorable — abort-condition history, box
health, maintenance-window proximity — at each segment boundary, rather
than committing to one posture (uninterrupted run, or automatic restart)
across 60 unattended hours.

#### Concurrency with `daily_maintenance` — not previously addressed

**This section previously said nothing about `daily_maintenance` at
all.** `daily_maintenance.py` fires at `0 6 * * *` and currently takes
3-4 hours. **Two of its steps are independent writers into the sweep's
own evidence-source family and candidate shape, not one:**

| Step | Writes to `markets`? | Touches the sweep's own rows? |
|---|---|---|
| `resolution_sweep.py` (step 5) | **[V] Yes** — calls into the same assertion-branch-style write path | **Directly** — same `evidence_source="clob"` family, same `resolved=0` candidate shape |
| `Backfill market dates` (step 32, held at `--limit 2000` per `bd672fb`) | **[V] Yes** | **Directly** — its own literal candidate query (no `resolved` filter) overlaps wherever both are still `resolved=0`, and separately re-touches recently-sweep-resolved rows via its `end_date IS NULL` clause (9,122 such rows existed even before tranche 2's writes, `2026-08-22-tranche2-execution.md` pre-flight question 1) |
| `hydrate_stub_markets.py`, `backfill_market_categories.py`, `resolve_legendary_markets.py` | **[V] Yes**, each | Different or narrower populations, same table/row-lock contention |
| `sync_trade_categories.py`, `evaluate_new_trader_results.py`, `reconcile_geo_resolved_counts.py` | **[V] No** | n/a |

**SQLite's actual behavior, checked rather than assumed:** both
`backfill_market_dates.py`'s `_get_connection()` and
`monitoring/database.py` set `PRAGMA journal_mode=WAL` and `PRAGMA
busy_timeout=30000` explicitly [V]. Under WAL, a second writer blocks up
to 30s then raises `database is locked` if still contended — 30s is
generous for the sweep's own short, per-row, immediately-committed
transactions, so **serialization via brief blocking, not errors, is the
expected outcome for the sweep itself.**

**The exposure runs the other way from what this document originally
assumed.** `2026-07-07-silent-failure-audit-FABLE.md` item 3.2 [V]:
roughly 25 daily-maintenance-step scripts call raw `sqlite3.connect()`
with no `busy_timeout` set at all (Python's default is effectively 5s) —
including `update_research_exclusions.py` (step 0, blocking),
`fast_resolution_check.py` (×8 sites), `verify_market_titles.py`,
`sync_trade_categories.py`, `update_geo_elo.py`,
`resync_position_counts.py`, and most snapshot/backfill steps. **If the
sweep holds the write lock, those ~25 scripts are what fails or silently
skips — not the sweep, which simply waits out its 30s timeout.** This is
a pre-existing exposure in the codebase; the sweep does not create it,
but running a sustained, high-frequency writer for 59+ hours makes it
**far more likely to actually fire** than it has been historically.

**Evidence for real dropped writes under contention, not merely benign
retries:** `2026-06-29-overhang-ledger.md` [V] documents `database is
locked` causing `background_pnl_worker.py` (a 5s-timeout writer) to roll
back an entire trader's position-insert batch while still marking the
trader "done" with zero positions persisted — **11 separate days, April
26 through July 5, bursts up to 150/day.** This is a confirmed pattern of
actual failed writes under a different, unhardened writer, not evidence
about the sweep's own (hardened) exposure specifically — cited here as
the real basis for treating lock contention as consequential, in place
of two figures that do not have one.

**Correcting the record:** a "06:01:36" `pnl_worker` lock error and
"~3,874 historical occurrences" were cited earlier in this arc's working
conversation but **could not be independently located** in
`2026-08-19-market-resolution-write-cluster.md`, the O-13/O-15/O-20/O-27
decision docs, or `brain/agent-outputs/` — **not to be treated as
established, and not to be propagated further.** The `overhang-ledger`
citation above stands in their place as the actual verified evidence.

**The WAL-checkpoint step** (`sqlite3 <db> "PRAGMA wal_checkpoint(PASSIVE);"`,
run near the end of `daily_maintenance.py`'s sequence) checkpoints
without blocking concurrent readers/writers but will not truncate WAL
pages held by an open transaction elsewhere. The sweep's own transactions
are short and committed per-row (unconditional `conn.commit()` after
every accepted write, confirmed in the driver both tranches used) — it
does not hold a long-lived open transaction, so **sustained WAL growth
from the sweep's own write pattern specifically is not expected**, and
none was observed across either tranche.

`polymarket-monitoring`'s always-on 15-minute loop is a **third**
independent writer into `markets` (`monitoring/monitor.py`, 2
`UPDATE markets` sites, confirmed by direct grep) — it ran concurrently
throughout both tranches with **zero abort-condition fires or atomicity
violations**, the strongest empirical evidence available that
30s-busy_timeout writers coexist safely with each other. It does not
change the risk profile above: the concern is the ~25 unhardened
maintenance steps, not the hardened always-on services.

#### Daily-step policy during the sweep

**Hold `backfill_market_dates.py`'s daily invocation at `--limit 2000`
through the sweep's actively-running segments; let it run unheld
(restored, or at minimum not held down) on at least one day the sweep is
paused.** Running it held *concurrently* with an active segment adds
brief write-lock contention during a chunk already moving as fast as
safely possible, duplicate CLOB calls the sweep would make anyway on the
same rows (resolved harmlessly by the comparator, but wasteful), and a
second source of `resolved`-flip activity to reason about if an abort
condition fires mid-chunk. But holding it down for the sweep's *entire*
duration is not free either: an unheld run is the first plausible chance
for the untagged-legacy-improvement branch to fire in production, since
the script's own literal (non-`resolved`-filtered) query — unlike every
tranche this arc has scoped to this document's `resolved`-filtered
predicate — can reach already-resolved-but-still-null-`end_date` rows
(9,122 as of tranche 2's pre-flight check, since grown by tranche 2's own
4,723 writes, which also lack `end_date`). The chunked-scheduling model
above already creates gaps between segments; use one of those gap-days to
let the daily step run at full `--limit 2000`, capturing that value
without contending against a live segment. A scheduling decision, not a
code change.

#### Interruption cost is not a deciding factor — closing this off explicitly

Tranche 2's own measured data closes a question the revised runtime might
otherwise reopen: per-batch elapsed time ranged 202.6s–214.0s across all
ten batches; a restart always re-issues the entire interrupted batch's
500 calls from scratch (confirmed both kill tests: `fresh=500,
skipped=0`) — already-written rows correctly no-op via the comparator,
but the wall-clock cost of re-fetching them is not avoided. **Worst case:
~208s (≈3.5 minutes) of redundant work per interruption; best case ~0s**
(a kill landing between batches). Even several worst-case interruptions
across a 59-hour run cost minutes, not hours. **Batch size stays at
500** — a smaller batch would cut worst-case rework proportionally
(~42s at 100 rows) but at five times the checkpoint-write volume for a
total-runtime improvement measured in tens of hours, no meaningful gain.
This was reconsidered given the revised runtime, not merely carried
forward unexamined, and the conclusion is unchanged.

#### The checkpoint skip-list's actual role — a finding from tranche 2, recorded here

Tranche 2's second kill test (`2026-08-22-tranche2-completion.md` §c)
found that the checkpoint's per-market skip list (`resolved_market_ids`)
**cannot structurally fire** under this driver's design: the fixed
sample has no duplicate `market_id`s, batches are non-overlapping fixed
slices, and the loop never re-enters a completed batch — so a
`market_id` already in the skip list can never appear in any batch this
driver will process. **The no-double-write guarantee the skip list was
believed to help provide rests entirely on `mark_market_resolved()`'s own
idempotent same-rank-match comparator logic** — independently confirmed
under a real SIGKILL twice, at two different points in a run (before any
checkpoint existed, and mid-batch with checkpoints already on disk), both
times verified by direct timestamp inspection, not count alone. The
skip-list field remains a more accurate historical record of confirmed-
resolved markets (per its own defect-2 fix,
`2026-08-22-tranche2-driver-fixes.md`) but should not be relied upon, or
described, as an active runtime protection.

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

**Amended 2026-08-22 (`a972731`): unchanged in substance, one note
added.** With execution now chunked across multiple scheduled segments
(above) rather than one continuous run, the backup taken before the
sweep's *first* segment (`markets_20260822_143948.db`, taken for tranche
2) may need refreshing depending on how much time and how many other
writes elapse before the full sweep's first chunk actually starts — per
§G's own "fresh capture immediately before" rule, applied here to mean
before the first sweep segment specifically, not necessarily re-taken
before every subsequent segment.

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

**Amended 2026-08-22 (`4436119`): minimum-sample floor added to
conditions 2 and 3, as an evaluation precondition — the 10%/20% rates
above are unchanged.**

Tranche 1's execution (`2026-08-22-tranche1-execution.md`, `4436119`)
paused at row 25 of 317 when condition 2 fired: 3 indeterminate results in
25 processed rows, 12.0%, crossing the 10% batch threshold. The harness
stopped immediately, as designed. **This was correct behaviour under the
threshold as written, and the harness stopping rather than reasoning past
it is the outcome this document's own protocol wanted** — the sentence
immediately above, "if a threshold turns out to be miscalibrated, that is
itself a finding to report, not a number to move," is exactly what this
amendment does. [V]

The threshold as originally written carries no minimum sample size — it
evaluates on whatever count exists at the first checkpoint, with no floor
below which a reading is recorded but deferred rather than acted on. At
n=25, against a population whose true indeterminate rate is 5.05%
(16/317, established by the 2026-08-20 sizing census and reproduced
exactly by tranche 1's own fresh dry-run this session,
`2026-08-22-tranche1-execution.md` §1), observing 3 or more indeterminates
is an ordinary outcome, not a signal. [V, exact binomial, computed for
this amendment]:

```
X ~ Binomial(n=25, p=0.0505)
P(X=0) = 0.9495^25              ≈ 0.274
P(X=1) = 25 × 0.0505 × 0.9495^24 ≈ 0.364
P(X=2) = C(25,2) × 0.0505² × 0.9495^23 ≈ 0.232
P(X≥3) = 1 − [P(X=0)+P(X=1)+P(X=2)] ≈ 1 − 0.870 ≈ 13.0%
```

Roughly a 1-in-7-8 chance of crossing 10% by pure sampling variance at
n=25, given the true rate is 5.05%. The threshold fired on noise, not
signal — a **miscalibrated threshold**, not a wrong decision to stop on
it once fired.

**This is a correction to the threshold's evaluation precondition, not a
relaxation of the rates.** Legitimate: the threshold structurally could
not distinguish variance from signal below some minimum n, and the
correction would have been correct had it been written this way from the
start. Not legitimate, and not what is done here: raising 10%/20%
themselves, or declaring 12% acceptable because the run happened to stop
at an inconvenient point. **The 10% and 20% rates in the table above are
unchanged.**

**Minimum-sample floor: n = 100, for both condition 2 and condition 3.**
Chosen so a crossing at the floor is itself informative — a low
probability of occurring by chance if the true rate matches the
established 5.05% baseline:

```
Condition 2 (10% batch threshold), n=100, crossing = X ≥ 11:
Poisson approximation, λ = np = 5.05:
P(X≥11 | λ=5.05) ≈ 1.5%   [V, computed for this amendment]

Condition 3 (20% cumulative threshold), n=100, crossing = X ≥ 21:
P(X≥21 | λ=5.05) is vanishingly small (<0.01%) — condition 3's much
larger margin from the 5.05% baseline (20 vs. 10 percentage points)
means the same n=100 floor gives far more headroom there than for
condition 2, which is the binding constraint the floor is sized to.
```

~1.5% at the floor, versus the ~13% actually observed at n=25 this
session — an order-of-magnitude reduction in false-trigger probability,
at a sample size that still allows multiple checkpoints within tranche 1
itself (317 total) and is a small fraction of tranche 2's and the full
sweep's existing 500-row batch size (Batching and resumability, above) —
i.e. this floor changes tranche 1's checkpoint cadence specifically; it
does not change tranche 2's or the full sweep's, which already batch at a
scale comfortably above it.

**Below n=100, the indeterminate rate is recorded and reported at every
checkpoint, but does not by itself trigger a PAUSE or HARD ABORT** —
evaluation of conditions 2 and 3 is deferred until the floor is reached,
not skipped.

**Batch and cumulative are two separate counters, each with its own n=100
floor — an implementation must not substitute one for the other.**
Tranche 1's own harness (`tranche1_write.py`,
`2026-08-22-tranche1-execution.md` §3) tracked a single cumulative tally
and evaluated condition 2 against it, which did not matter at the first
checkpoint (batch and cumulative are numerically identical when only one
checkpoint's worth of data exists) but would produce a wrong answer at any
later checkpoint in a longer run, where the two diverge. **Named as an
implementation defect to fix before tranche 1 resumes or tranche 2 runs —
not fixed by this amendment, which is documentation only.**

**A second implementation defect, named for the same reason:**
`backfill_market_dates.py`'s own assertion-branch `conn.commit()` (its
existing code, unmodified by this arc) is conditional on the CLOB
response also carrying a usable end-date field, which step 1's own
finding (`2026-08-21-step1-implementation.md`, `d41d02b`) established is
commonly absent for already-resolved markets — meaning the production
script's own code path can accept a resolution write via
`mark_market_resolved()` and never call `conn.commit()` for that market's
turn through the loop, leaving the write in an open transaction until
some later iteration's commit happens to flush it. Tranche 1's driver
(`tranche1_write.py`) worked around this defensively, committing
unconditionally after every accepted write, without modifying
`backfill_market_dates.py` itself. **Named here as a defect in that file
to fix before any run that invokes it directly (rather than through a
purpose-built driver) — not fixed by this amendment.**

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

  **Amended 2026-08-22 (`4436119`): tranche 1 executed, paused at row
  25/317 on condition 2 — see the minimum-sample floor amendment above —
  with 16 verified writes landed, and two corrections recorded below.**

  **Scoping correction.** This document's own predicate for tranche 1
  (above) was, and remains, exact and correct. What required correction
  was an assumption elsewhere in this arc that `backfill_market_dates.py`'s
  `--geo-only` flag was equivalent to it, or could be used to invoke it via
  the CLI directly. It is not equivalent: `--geo-only`'s query joins on
  `trades.market_category` (not `markets.category`, which this document's
  predicate uses), applies no `trade_gap_flag` filter at all, and uses
  `end_date IS NULL OR resolution_date IS NULL` (OR) rather than this
  predicate's `AND`. [V, confirmed by reading `get_markets_to_backfill()`
  directly, `2026-08-22-tranche1-execution.md` §2]. Tranche 1 was
  therefore executed via a separate driver script (`tranche1_write.py`)
  built against this document's exact predicate, calling the unmodified
  `_fetch_by_clob`, `_extract_clob_resolution`, and `mark_market_resolved`
  — not via the `--geo-only` CLI flag, which would have processed a
  different, unverified population had it been used, in violation of "do
  not run it unscoped."

  **16 real writes landed before the pause**, all `reason="written"`
  (trivial first-write), zero rejected, zero trigger fires,
  `check_resolution_write_atomicity` = 0 throughout and after. Full
  figures: `2026-08-22-tranche1-execution.md` §5.

  **On the untagged-legacy-improvement branch remaining unfired in
  production.** All 16 writes, and the freshly re-derived dry-run's
  predicted 203, take the trivial first-write branch (`reason="written"`)
  exclusively — not by chance, but structurally. Reading
  `monitoring/resolution_writer.py`'s branch logic directly: the branch
  taken is decided by `prev_resolved` (the market's OLD `resolved` value)
  — `if not prev_resolved: reason = "written"`; every other branch
  (untagged-legacy-improvement, cross-rank overwrite, same-rank
  match/disagreement) requires `prev_resolved` to already be truthy.
  Tranche 1's own selection predicate requires `resolved = 0 OR resolved
  IS NULL`, which excludes every row that could take any branch but the
  trivial one. **The untagged-legacy-improvement branch is therefore
  structurally unreachable for the tranche-1 population — its absence
  here is not evidence of a defect, and should not be read as one.** It
  becomes reachable only in the wider sweep population (which does not
  exclude already-`resolved=1` rows the same way tranche 1's `AND`-based
  predicate does) — if it fires for the first time in production, that is
  where it will happen, not in tranche 1.
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

  **Amended 2026-08-22 (`b5fd6f4`): the Remainder now runs as segments,
  per the execution-mode amendment above — segment 1's results to date.**
  11 batches (5,500 markets) ran clean at **0.0–1.6% indeterminate
  rate — below tranche 2's own ~3.5–4% band**, before batch 12 paused the
  run (see the Pacing section's carve-out amendment for the full root
  cause). **5,814 markets resolved before the stop, every one
  `reason="written"`, zero rejected, zero trigger fires,
  `check_resolution_write_atomicity` = 0 throughout and after, every
  fingerprint delta reconciling exactly against the confirmed-resolved
  count** (`2026-08-22-sweep-segment1.md` §post-write verification). **The
  batch-12 pause was correct behaviour on a real signal, not a defect in
  the segment or the driver** — the same driver, unmodified, that passed
  tranche 2 cleanly, applied to a population segment 1 (walking in
  `market_id` order for the first time, unlike tranche 2's random sample)
  was positioned to discover.

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
   census, not a sample.

   **Amended 2026-08-21 (`d41d02b`): this has already happened once, at
   the read-only pre-check stage (§B item 3), not yet at tranche 1
   itself.** Step 1's first attempt found 0 resolved against an expected
   ~203 (`2026-08-21-step1-implementation.md`), traced to root cause:
   `_fetch_by_clob`'s success gate discarded usable, fully-parsed CLOB
   responses (`closed: true`, a real winning token) whenever `end_date_iso`
   was null, before the new assertion branch — confirmed correct in
   isolation — ever saw them. **The assumption that this script's existing
   CLOB call already returns everything needed has been falsified, once.**
   The response was to widen step 1's scope — separate the gate from the
   fetch (§B amendment, 2026-08-21) — not to abandon the CLOB-by-market_id
   approach, because the failure traced to a specific, narrow, fixable
   cause (a gate written for one caller's needs, silently wrong for a
   second) rather than to any defect in the classification logic itself.

   **What would falsify the approach itself, on a second failure:** if the
   pre-check (or tranche 1) still does not reproduce the expected count
   *after* the gate-separation change — i.e. the assertion branch now
   receives the response but still misclassifies it, or still fails to
   reach the population for a *different* reason than the one just fixed —
   the problem is no longer reach, and the CLOB-by-market_id shape itself
   is in question, not merely this script's plumbing. That would be the
   point to stop and reconsider the shape, not patch a second time.
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

   **Amended 2026-08-22 (`a972731`): a related, not-yet-falsifying
   observation worth tracking, not confused with the disagreement case
   above.** The *cross-rank overwrite* branch (`"written: proposed
   evidence outranks existing"` — CLOB's rank-1 proposal legitimately
   beating an existing rank-2 Gamma value, distinct from same-rank
   disagreement) has fired **zero times across 9,723 candidates** (317 in
   tranche 1, 5,000 in tranche 2, plus tranche 2's own re-attempts) despite
   §A1 predicting a CLOB write should *routinely* outrank an
   already-present Gamma value at scale. This is not evidence of a defect
   — the branch was fabricated and confirmed working correctly in
   isolation (`2026-08-22-tranche2-driver-fixes.md`) — but it is real,
   accumulating evidence about how CLOB and Gamma actually populate
   relative to each other in this codebase's data, not merely an absence
   of opportunity so far. **Not revised here** — §A1's ranking and premise
   are unchanged by this amendment — but named so a 60-hour run's ~40x
   larger volume is read as the test of this specific prediction, one way
   or the other, rather than assumed settled either way.

   **Amended 2026-08-22 (`b5fd6f4`): still zero.** Segment 1's 5,814
   further writes (before its batch-12 pause) add zero further
   occurrences — the branch has now not fired across **15,723 total
   candidates** (317 + 5,000 + 5,814, plus tranche 2's own re-attempts).
   The accumulating zero continues to weigh against §A1's "routine"
   prediction, more so with each session that adds volume without a
   single confirming instance — still not treated as settled, §A1 still
   unrevised here.
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

---

*Amended 2026-08-21: revises step 1's scope in response to its first stop
(`2026-08-21-step1-implementation.md`, `d41d02b`), which built the
assertion branch exactly as originally specified here, passed the
branch-split dry-run diff, and then failed a read-only correctness
pre-check against the known 317-market Q2 census population (0 resolved
found against a freshly-derived expected ~203). Root cause traced to
`_fetch_by_clob`'s existing success gate conflating "did we get a usable
date?" with "did we get a usable response?" — the same one-artifact/
two-questions shape as the design's own §A finding about `resolution_date`.
§A's step 1 row and stop-condition list, and §B, gained the fix (separate
the gate from the fetch; each caller applies its own usability test) and
the reasoning for rejecting two alternatives (a second fetch function;
a mode flag on the existing one). §B's numbered verification list gained
a new item 3, promoting the 317-market read-only correctness pre-check
from an ad hoc addition in the first attempt to a required gate — it is
what caught the inert branch; the clean branch-split diff alone did not.
Existing items renumbered (old 3→4, old 4→5); item 2's proxy-branch
requirement gained an explicit note that it now covers a refactor of
shared code, not merely an additive branch. §I's falsification condition
1 gained a record that its own premise has already been falsified once,
that the response was to widen scope rather than abandon the approach, and
a stated condition for what would falsify the approach itself on a second
failure. §C's thresholds, abort conditions, and staged-rollout tranches;
§E's interpretation rule; §D; §F; §G; and §H are unchanged by this
amendment. Oscar's four directions are unchanged; no restructuring. Step
1's re-attempt itself is not part of this amendment and follows
separately.*

---

*Amended 2026-08-22 (`4436119`), prompted by tranche 1's execution
(`2026-08-22-tranche1-execution.md`): §C's abort conditions gained a
minimum-sample floor (n=100) for conditions 2 and 3, evaluated as a
precondition on when the rate is acted on, not a change to the 10%/20%
rates themselves — those are unchanged, per the statistical justification
now recorded inline (a spurious 10%+ reading at n=25 against the
established 5.05% baseline has ≈13% probability by chance; at the n=100
floor, ≈1.5%). Batch and cumulative indeterminate-rate tracking are now
stated as two separate counters, each with its own floor, since tranche
1's ad hoc harness conflated them (immaterial at its first checkpoint,
would not be at a later one). §C's Staged rollout section gained the
tranche 1 pause record (paused at row 25/317, 16 verified writes landed,
zero trigger fires, zero unpredicted rejections, all `reason="written"`),
a scoping correction (`--geo-only` is not equivalent to this document's
tranche-1 predicate and was not used; a separate driver against the exact
predicate was), and a note that the untagged-legacy-improvement branch's
absence from tranche 1 is structural, not a defect. Two implementation
defects are named for future fixing, not fixed by this amendment: the
harness's batch/cumulative conflation, and a gap in
`backfill_market_dates.py`'s own assertion-branch commit logic (conditional
on a usable end-date being present, worked around defensively in the
driver rather than fixed in that file). §A, §B, §D, §E, §F, §G, §H, and §I
are unchanged by this amendment; the tranche definitions and every other
abort condition are unchanged. This amendment is documentation only — no
code was written, no script was run, tranche 1 was not resumed.*

---

*Amended 2026-08-22 (`a972731`, `9dc11e3`), prompted by tranche 2's
completion and the resulting execution-model assessment: §C's Pacing
section gained the measured per-call rate (0.416s, ±3% across ten
batches, versus the 0.25s planning figure — the pacing directive itself
is unchanged), a fresh population count (513,770, the first reading below
the original 515,491 estimate, attributable to tranches 1+2's own 4,926
writes), and a re-projected runtime (~59.4 hours, up from ~35.8). §C's
Batching and resumability section, previously silent on
`daily_maintenance` entirely, gained: an execution-mode change from one
continuous detached run to chunked, scheduled segments (a systemd unit
was reconsidered given the longer runtime and rejected again, for
reasons specific to the automatic-restart tradeoff, not merely carried
forward); a concurrency accounting naming two independent
`daily_maintenance` writers into the sweep's own evidence-source family
(`resolution_sweep.py` step 5 and the held `backfill_market_dates.py`
step 32, not one); a finding that the real exposure runs toward roughly
25 unhardened (no-`busy_timeout`) daily-maintenance scripts, not toward
the sweep itself; a citation to `2026-06-29-overhang-ledger.md` as the
verified evidence for real dropped writes under contention, replacing two
specific figures ("06:01:36," "~3,874 occurrences") that could not be
independently located and are recorded as unverified rather than
propagated; a daily-step policy (held during active segments, unheld on
at least one paused day, to preserve the untagged-legacy-improvement
branch's first plausible production exercise); a closed-off finding that
interruption cost (~208s worst case) is not a deciding factor and batch
size stays at 500; and a recorded finding that the checkpoint skip-list
cannot structurally fire under this driver's design, with the actual
no-double-write guarantee resting on `mark_market_resolved()`'s
comparator, confirmed twice under real SIGKILL. §C's Backup section gained
one note about refreshing the backup before the sweep's first segment
specifically, unchanged in substance otherwise. §I's falsification
condition 3 gained a tracked, not-yet-falsifying observation: the
cross-rank-overwrite branch has fired zero times across 9,723 candidates
despite §A1 predicting it routine — named for the full sweep's much
larger volume to actually test, §A1 itself unrevised. §A, §B, §D, §E, §F,
§G, and §H are unchanged; the tranche definitions, the n=100 floor, the
abort thresholds, and §E's interpretation rule are all unchanged. This
amendment is documentation only — no code was written, no sweep was
started.*

---

*Amended 2026-08-22 (`b5fd6f4`), prompted by segment 1's batch-12 pause:
§C's Pacing section gained a carve-out of a structurally-unresolvable
combo/parlay market cohort from the candidate population — 15,427
markets, a precise signature (zero-padded synthetic `market_id`, empty
`condition_id` and `api_id`, multi-leg compound-bet titles), confirmed to
carry real trade records (so they fall in the sizing result's O stratum,
not Z), permanently incapable of returning a CLOB response by
construction. Recorded as a finding about the data — the sweep's
predicate is a proxy for "might be resolvable," and for this cohort the
proxy is wrong — not a threshold change; the 10%/20% rates and n=100
floor are untouched. Two alternatives (relaxed-threshold processing;
manual step-through expecting repeated pauses) considered and rejected,
both for corroding the threshold's meaning as surely as moving it would.
A three-part verification requirement (usable-identifier sampling, false-
positive check, live re-derivation of the exact predicate and count) is
specified as a precondition the implementing task must establish, not
assume from segment 1's 67 rows — failure on any part blocks the
carve-out. Population and runtime revised: 507,956 (post-segment-1) minus
15,427 = 492,529 candidates, ≈56.9 hours at 0.416s/call. A narrow,
figures-only correction to `2026-08-20-discovery-gap-sizing-result.md`'s
Q1 estimate is recorded (≈99.3% → ≈96.3% pooled-O resolved-fraction,
≈15,300 fewer estimated resolved markets) — not a re-sampling, and does
not change that document's conclusion, which remains an overwhelming
majority of the population resolved-and-undiscovered. The general lesson
(a random sample characterizes a population's average, not its shape;
scan order can surface what a validating sample's averaging hid) is
recorded, noting this is the second such cohort found this way, after the
~98-row CLOB-purged 2020-era prefix. §C's Staged rollout section gained
segment 1's results to date: 11 clean batches (0.0–1.6% indeterminate,
below tranche 2's baseline), 5,814 markets resolved before the pause, all
`reason="written"`, zero trigger fires, atomicity clean throughout, every
delta reconciling — and a statement that the pause was correct behaviour
on a real signal, not a defect. §I's cross-rank-overwrite tracking note
updated: still zero, now across 15,723 total candidates; §A1 still
unrevised. §A, §B, §D, §E, §F, §G, and §H are otherwise unchanged; the
tranche definitions, the n=100 floor, the abort thresholds, and §E's
interpretation rule are all unchanged. This amendment is documentation
only — no code was written, no sweep was resumed; the carve-out's
implementation follows separately.*
