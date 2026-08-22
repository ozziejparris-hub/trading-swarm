# 2026-08-22 — Sweep Segment 1: STOPPED at batch 12/206 on a real, explained signal

## VERDICT: ABORT CONDITION 2 FIRED — CORRECTLY, ON SIGNAL, NOT NOISE. STOPPED PER PROTOCOL. THE REMAINING SEGMENTS ARE BLOCKED PENDING A DECISION ON HOW TO HANDLE A NEWLY-DISCOVERED, ~15,400-MARKET STRUCTURALLY-UNRESOLVABLE COHORT.

Segment 1 processed 12 of 206 planned batches (6,000 of 103,000 markets)
before pausing itself on a batch-level indeterminate-rate spike. This is
**not** a repeat of tranche 1's early pause (which was small-sample noise
at n=25, since resolved by the n=100 floor amendment). This is a
**real, large, well-explained signal at n=500 — five times the floor** —
and root-cause analysis this session identified exactly why: segment 1's
market_id scan order concentrated an entire cluster of combo/parlay
markets (synthetic IDs, no real `condition_id`, structurally incapable of
ever returning a CLOB response) into one stretch of the population. That
stretch is large (~15,400 markets, spanning an estimated 35 more batches)
— continuing past this point without a decision would trip the same
condition repeatedly, not once.

All claims tagged **[V]** verified (ran/read it myself) or **[I]** inferred.

---

## Before the write

1. **[V] Fresh backup**: `backups/markets_20260822_160034.db`, 16,550.6
   MB, integrity-verified, exit 0 — taken before any of segment 1's
   writes, superseding the 14:39 backup which predated tranche 2.
2. **[V] Fresh fingerprint**, committed:
   `data/characterizations/sweep_segment1/segment1_prewrite_fingerprint_20260822T160533Z.json`
   (first-repo `05bb860`).
3. **[V] Maintenance-window runway, computed explicitly:**

   ```
   Current time:        2026-08-22 16:03:33 UTC
   Next maintenance fire: 2026-08-23 06:00:01 UTC
   Runway:               13h 56m 28s = 50,188s = 13.941h

   Target margin:        2h = 7,200s
   Processing budget:    50,188 - 7,200 = 42,988s
   At 0.416s/call:       42,988 / 0.416 ≈ 103,336 calls
   In whole 500-batches:  floor(103,336 / 500) = 206 batches = 103,000 markets

   Projected processing time: 103,000 × 0.416s = 42,848s = 11.902h
   Projected finish:     2026-08-23 03:57:41 UTC
   Actual margin:        50,188 - 42,848 = 7,340s ≈ 2.04h
   ```

   Segment 1 was sized to **206 batches (103,000 markets)**, projected to
   finish with ~2 hours to spare before the next maintenance fire.
4. **[V] Daily-step hold, confirmed and reported, not changed.** Segment
   1's projected finish (~03:58 UTC) is comfortably before tomorrow's
   06:00 fire — a clean ~2h gap with no active segment running during
   the maintenance window. Per §C's daily-step policy, this makes
   tomorrow a "paused day" for the sweep. **Recommendation, not
   executed:** let `backfill_market_dates.py`'s daily invocation run
   unheld (restored from `--limit 2000`) for tomorrow's run specifically,
   capturing the untagged-legacy-improvement branch's first plausible
   production exercise without contending against an active segment.
   `daily_maintenance.py` was not modified, per this task's constraints.
   **This recommendation is now moot in one sense** — segment 1 stopped
   far short of its projected finish (12/206 batches, ~2,529s elapsed vs.
   ~42,848s projected), so the "paused day" condition holds even more
   comfortably than planned, with much larger margin than the 2h
   originally computed.

---

## The run

**[V]** Population: SS C's predicate (513,770) minus the 5,000 tranche-2
sample market_ids. **Exclusion method, stated exactly:** a
`market_id NOT IN (...)` clause against the full 5,000-ID list from
`tranche2_sample_5000.json`, combined with `ORDER BY market_id ASC LIMIT
103000` in one query, executed once (`segment1_materialize.py`) and
persisted to `segment1_list.json` before any write — same seed/resume-
drift reasoning as tranche 2's own fixed-sample approach: `market_id` is
not insertion-ordered, so a live re-query after a restart could shift
which markets fall inside the boundary. Of the 5,000 excluded IDs, 277
were still live candidates at draw time — exactly matching tranche 2's
own final open+indeterminate+no_clob_response tally (95+30+152=277),
confirming the exclusion correctly removed exactly the markets tranche 2
had just finished checking, not an approximation.

**[V]** Driver (`segment1_write.py`, committed `first-repo` `05bb860`)
imports `ACCEPTED_REASONS` and `atomicity_count` directly from
`tranche2_write.py` (the fixed driver, `6061a5a`) rather than redefining
them — confirmed via a direct import smoke-test before launch, returning
the same four-item whitelist. `tranche2_write.py` was not modified.
Launched detached: `nohup python3 -u segment1_write.py > logs/... 2>&1 &
disown`.

---

## What happened

**[V]** Batches 1–11 ran cleanly, indeterminate rate 0.0%–1.6% per batch
— **notably lower** than tranche 2's ~3.5–4% band, itself worth noting as
part of watch-item (c) below. Batch 12 (markets 5,501–6,000 of the
segment): `tally={'resolved': 424, 'open': 8, 'indeterminate': 1,
'no_clob_response': 67}`, **batch_indet_rate=13.6%**, crossing the 10%
batch threshold (n=500, five times the 100-row floor — this crossing is
not attributable to small-sample variance the way tranche 1's first pause
was). The run stopped itself immediately, as designed:
```
[SEGMENT1-WRITE] ABORTED
[SEGMENT1-WRITE] Abort reason: ABORT CONDITION 2 (batch >10%, floor met): batch_indet_rate=13.6% in batch 12
[SEGMENT1-WRITE] Batches completed: 12/206
[SEGMENT1-WRITE] Cumulative processed: 6000/103000
```

### Root cause, identified and quantified this session

**[V]** All 67 of batch 12's `no_clob_response` markets share a distinct
`market_id` pattern — a long suffix of zeros
(`...0000000000000000000000000000`), confirmed by direct comparison: 67
zero-padded IDs in the batch, 67 no-CLOB-responses, exact 1:1 match.
Inspecting these markets directly: **empty `condition_id`, empty
`api_id`, `category='Unknown'`, and titles that are multi-leg compound
bets** — e.g. *"Will United States win on 2026-06-19? AND Will Brazil win
on 2026-06-19? AND Will Türkiye win on 2026-06-19? AND Will Morocco win on
2026-06-19? AND Will Netherlands win on 2026-06-20?"* — **combo/parlay
markets, not real single-outcome CLOB-tracked markets.** They have no
real `condition_id` for `_fetch_by_clob()` to query, and their synthetic
`market_id` is not a value CLOB's API recognizes — they are **structurally
incapable of ever returning a CLOB response**, not transiently
unavailable and not ambiguous the way a genuine "indeterminate"
classification is.

**Quantified, not left as a one-batch anomaly:** **[V] 15,427 such
markets exist in the full candidate population** (live query, same
predicate). Within segment 1's own 103,000-market list specifically,
**15,208 of them cluster in a contiguous run from index 6,000 to
23,094** — because `market_id` sorts these together (their common
zero-padded suffix format sorts adjacent to itself), not because scan
order correlates with insertion time the way the task prompt's framing
suggested; the mechanism is real but the specific reason is a shared ID
*format*, not age. **This span covers batches 13 through 47 — an
estimated 35 more batches** would have been dominated by this cohort
(the 15,208-row cluster is ~89% of that specific 17,094-row window),
almost certainly re-tripping the same 10% batch threshold repeatedly, not
as noise but as an accurate, correct signal every time, for as long as
the scan remained inside that cluster.

**This is the same *shape* of finding as the previously-documented
"permanently-dead ~98-row CLOB-purged prefix" from step 2's own
investigation (2020-era markets CLOB has purged) — but a different root
cause (combo/parlay markets that were never real CLOB markets, not
purged legacy ones) and roughly 157x larger in scale (15,427 vs. ~98).**
That earlier, smaller instance was "accepted, not skipped — named
follow-up, not fixed" given its size. This one is large enough (~3% of
the total candidate population) that walking through it under the
current per-batch threshold is not practical without a decision.

---

## Abort conditions — which fired, which didn't

**[V]** Condition 2 (batch, 10%, n≥100 floor) fired, correctly, at batch
12. **This is not the same situation as tranche 1's original pause** —
that one was resolved by adding a minimum-sample floor because n=25 could
not distinguish noise from signal; here, n=500 (5x the floor) produced a
result so far outside the baseline range that it demanded investigation
rather than dismissal, and investigation found a real, quantifiable
cause, not statistical variance. **No amendment to the threshold itself
is implied by this event** — the threshold did its job.

No other condition fired: zero trigger fires, `check_resolution_write_atomicity`
= 0 throughout (12 checks) and after, zero reasons outside the
whitelist (`cumulative_reasons: {'written': 5814}` — no rejections, no
no-ops, no disagreements), pacing stayed 0.146–0.193s/call (excl. sleep),
well under 1.0s/call. Cumulative indeterminate rate at the point of
stopping: 1.8% (177/9,930 wait — computed from `cum_tally`:
(36+69)/(5814+81+36+69) = 105/6000 = 1.75%), still on the low side, since
11 clean batches diluted batch 12's spike.

---

## Watch-for items

### a. Cross-rank overwrite branch

**[V] Still zero.** All 5,814 accepted writes this segment: `reason="written"`
— no `"written: proposed evidence outranks existing"` observed.
Combined with tranches 1+2 (9,723 candidates), the branch has now not
fired across **15,723 total resolution-assertion candidates**. The
accumulating-zero observation from the pre-registration's amended §I
grows larger, not smaller — still not treated as settled, but the sample
size against §A1's "should be routine" prediction keeps growing without
a single confirming instance.

### b. Untagged-legacy branch

**[V] Confirmed does not fire, as expected.** Zero occurrences of
`"written: existing value has no recorded evidence_source (pre-canonical),
proposal accepted"` — consistent with §C's resolved-filtered predicate
structurally excluding every row that could take this branch, same
reasoning verified for tranches 1 and 2.

### c. Does the population behave like tranche 2's sample?

**[V] No — and the divergence is now root-caused, not merely observed.**
Batches 1–11 (5,500 markets, before the spike) ran at 0.0–1.6%
indeterminate rate, *below* tranche 2's ~3.5–4% band; batch 12 spiked to
13.6%, far above it. **Tranche 2 drew a seeded random sample, which
smooths cluster effects like this one across the whole run** (the
~15,400 combo markets would appear scattered, a handful per batch, never
concentrated); **segment 1 walks in `market_id` order, which is exactly
where this specific cluster's shared ID format causes it to concentrate.**
This is precisely the divergence the task's watch-item anticipated,
though the mechanism (ID-format clustering under lexicographic sort, not
insertion-time correlation) is more specific than "scan order is
insertion order" assumed. **Material, explained, and actionable** — not
a reason to distrust the driver or the comparator, but a reason the
*population itself* is not uniform in the way a random sample suggested
it might be.

---

## Post-write verification

### a. Evidence-source delta and sample rows

**[V]** `resolution_evidence_source='clob'`: **4,926 → 10,740**, delta
**+5,814**, exact match to the checkpoint's `cumulative_accepted`. Five
sample rows:

| market_id (truncated) | resolved | winning_outcome | resolution_date | resolution_recorded_at | evidence_source | evidence_detail |
|---|---|---|---|---|---|---|
| 0x00001032... | 1 | Up | 2026-08-22 16:07:07.07 | 2026-08-22 16:07:07.07 | clob | token.winner |
| 0x00002296... | 1 | Down | 2026-08-22 16:07:07.47 | 2026-08-22 16:07:07.47 | clob | token.winner |
| 0x00002547... | 1 | Down | 2026-08-22 16:07:07.87 | 2026-08-22 16:07:07.87 | clob | token.winner |
| 0x0000256a... | 1 | Down | 2026-08-22 16:07:08.26 | 2026-08-22 16:07:08.26 | clob | token.winner |
| 0x00005e9c... | 1 | Down | 2026-08-22 16:07:08.69 | 2026-08-22 16:07:08.69 | clob | token.winner |

("Up"/"Down" outcomes — consistent with this segment's low-`market_id`
range being dominated by crypto-price markets, another population
characteristic worth noting for future segments' timing/rate planning:
different market_id ranges may have systematically different market
*types*, not just different resolution rates.)

### b. Branch-firing counts

**[V] 5,814 `"written"`, 0 everything else.** Zero cross-rank overwrite
(watch-item a), zero untagged-legacy (watch-item b), zero same-rank
match or disagreement (unsurprising — this segment, unlike tranche 2, was
not re-attempting any previously-touched market).

### c. Atomicity

**[V] 0**, checked after every one of the 12 batches and in a final
direct check.

### d. Trigger

**[V]** `trg_resolved_no_unresolve` present, unchanged, did not fire.

### e. Post-write fingerprint

| Metric | Pre-write (`05bb860`, 16:05) | Post-stop | Delta | Attributable? |
|---|---|---|---|---|
| resolved markets | 229,907 | 235,721 | **+5,814** | **Yes — exact match** |
| Geo/Elec resolved+gap-clean | 10,792 | 10,792 | 0 | Expected — no category filter, same reasoning as tranche 2 |
| `resolution_evidence_source='clob'` | 4,926 | 10,740 | **+5,814** | **Yes — exact match** |
| `resolution_evidence_source='gamma'` | 12 | 12 | 0 | Untouched |
| `resolution_evidence_source='hydration_fill'` | 1 | 1 | 0 | Untouched |
| `check_resolution_write_atomicity` | 0 | 0 | 0 | Clean throughout |

No count decrease anywhere; every resolution-specific delta is exactly
+5,814.

### f. Test suite

**[V]** `run_tests.py` re-run after the stop. **File-level baseline
unchanged: 16 files, 15 passed, 1 failed
(`test_backtest_window_population.py`).**

**T2f did not move — still 6,273, same as after tranche 2.** Traced to
root cause, not accepted at face value: `test_backtest_window_population.py`
is scoped to `category IN ('Geopolitics', 'Elections')` (confirmed by
reading the test file, same finding as tranche 2's own §f). Segment 1's
6,000 writes — crypto-price markets ("Up"/"Down" outcomes) and combo/
parlay bets, per the sample rows and root-cause analysis above — landed
entirely outside that category, independently confirmed by
`geo_elec_resolved_gapclean` staying flat at 10,792 both before and after.
Two independent measurements agreeing on zero movement, for a population
segment 1 has not yet reached the relevant category rows of, not an
unexplained non-result.

### g. Pacing and remaining-runtime projection

**[V]** Batches 1–12 averaged 0.146–0.193s/call (excl. sleep) — consistent
with tranche 2's 0.155–0.178s band, no material pacing drift. Batch-level
elapsed times were not logged for batches with a spike in
`no_clob_response` at a different rate than tranche 2 (a no-response
classification may resolve faster than a full round-trip through
`_extract_clob_resolution`, though this was not separately measured this
session).

**Re-derived remaining-runtime projection:** with only 12/206 batches of
segment 1 complete, and the run stopped for a substantive population
finding rather than a mechanical one, **a clean "segments remaining"
projection is premature** until a decision is made on how to handle the
~15,400-market combo cluster. If that cluster is walked through at the
current pace with no special handling, expect the abort condition to
fire repeatedly across batches 13–47 (see root cause above) — **not a
runtime question yet, a policy question first.**

---

## What this means for the remaining segments

**The full sweep is blocked, not because anything is broken, but because
a real population characteristic was found that the current per-batch
threshold cannot pass through unassisted, and pushing through it
mechanically would mean stopping and restarting roughly every batch for
the next ~35 batches — impractical, and exactly the "changing a
threshold to keep a run going" pattern the pre-registration warns
against if handled by just raising the number.**

Options for a future decision, named here, none executed:
1. **Carve out the combo/parlay population explicitly**, similar to the
   accepted-but-named ~98-row CLOB-purged prefix from step 2 — exclude
   markets matching this ID pattern (or, more robustly, empty
   `condition_id`) from the sweep's candidate predicate entirely, on the
   documented basis that they cannot structurally resolve via this path,
   and track them as a separate, acknowledged population (~15,427
   markets, ~3% of the current total) rather than silently walking
   through them.
2. **Process the cluster as its own deliberately-scoped mini-segment**
   with a knowingly-relaxed or disabled batch-level indeterminate
   threshold for that specific, pre-identified range, since the "why" is
   now known and documented, not a mystery to be cautious about.
3. **Leave the threshold and predicate untouched and manually step
   through** batches 13–47 expecting repeated pauses, treating each as
   confirmed-benign given this session's root-cause finding — the most
   conservative option, but the least practical for a run meant to
   proceed with limited supervision.

No recommendation is finalized here — that is the next decision, not
this task's to make unilaterally, given its own scope ("do not modify
production code... do not run more than segment 1").
