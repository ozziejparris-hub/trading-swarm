# 2026-08-22 — Tranche 2 Completion

## VERDICT: TRANCHE 2 COMPLETE. 10/10 batches. Zero aborts. All 4,723 confirmed-resolved markets reconcile exactly against DB ground truth. All proceed criteria MET, except one deliberately-unexercisable sub-requirement, explained below.

Tranche 2 (the fixed 5,000-market sample, `2026-08-21-discovery-gap-closure-prereg.md` §C) is finished, across three script invocations spanning two deliberate SIGKILL tests — one before any checkpoint existed (batch 1,
`2026-08-22-tranche2-execution.md`), one mid-batch-4 with checkpoints already on disk (this session). Both kill tests confirmed **zero double-writes**, verified by direct timestamp inspection, not count alone. One important architectural finding surfaced by the second kill test, reported honestly rather than glossed over: the checkpoint's market-level skip-list can structurally never fire under this driver's current design — explained in full below.

All claims tagged **[V]** verified (ran/read it myself) or **[I]** inferred.

---

## Before resuming

1. **[V] Fresh fingerprint**, committed:
   `data/characterizations/tranche2_execution/tranche2_resume_prewrite_fingerprint_20260822T150254Z.json`
   (first-repo `8ee20d5`). `evidence_source='clob'` = 673 confirmed
   (203 tranche-1 + 470 batch-1), `resolved_markets` = 225,654 (225,184 +
   470), `check_resolution_write_atomicity` = 0. `geo_elec_resolved_gapclean`
   unchanged at 10,792 from before batch 1 — expected, not a discrepancy:
   §C's sweep predicate carries no category filter (unlike tranche 1's),
   and 98% of all markets are `category='Unknown'`, so a 500-row random
   batch landing zero Geo/Elections resolutions is unsurprising.
2. **[V] Checkpoint confirmed intact and parseable** before resuming:
   `batches_completed: 1`, `cumulative_processed: 500`, `resolved_market_ids`
   count 378, matching `2026-08-22-tranche2-execution.md` exactly. Did not
   need to stop — matched expectations.
3. **[V] Driver confirmed at the fixed version**: `git log -1 --oneline`
   on `tranche2_write.py` → `6061a5a`; `git status` clean (no pending
   changes); `ACCEPTED_REASONS` inspected directly in the working-tree
   file, confirmed to contain all four post-fix entries.

---

## The run

**[V]** Launched detached with `-u` this time (`nohup python3 -u ... &
disown`) — the first launch's default block-buffering had hidden all
output until process exit; unbuffered output let this session watch
batch-by-batch progress live via a log-tail monitor.

**Batches 2–10 (4,500 markets) completed across two process invocations**
(the second interrupted by the deliberate kill below, the third completing
the remainder):

| Batch | Fresh | Skipped | Indet. rate | Avg. pace (excl. sleep) | Elapsed |
|---|---|---|---|---|---|
| 1 (prior session) | 500 | 0 | 4.0% | 0.163s | 206.4s |
| 2 | 500 | 0 | 3.0% | 0.164s | 207.1s |
| 3 | 500 | 0 | 3.8% | 0.159s | 204.5s |
| 4 (killed mid-batch, restarted) | 500 | 0 | 2.8% | 0.161s | 205.7s |
| 5 | 500 | 0 | 3.8% | 0.178s | 214.0s |
| 6 | 500 | 0 | 4.0% | 0.175s | 212.3s |
| 7 | 500 | 0 | 3.4% | 0.169s | 209.3s |
| 8 | 500 | 0 | 4.2% | 0.167s | 208.5s |
| 9 | 500 | 0 | 2.6% | 0.170s | 210.2s |
| 10 | 500 | 0 | 4.8% | 0.155s | 202.6s |

Zero abort conditions fired across the entire run (post-fix). Total
processing time (sum of per-batch elapsed, persisted correctly across the
kill/restart boundary): **2,080.8s = 34.7 minutes** — see §g below for
what this means for the full-sweep projection.

---

## The second kill test — mid-batch-4, with checkpoints already on disk

**[V] Killed at 15:12:08 UTC**, SIGKILL, roughly 100 seconds into batch 4
(after batches 2 and 3 had each completed and checkpointed —
`last_updated_utc` on the checkpoint at kill time read `15:10:12Z`, ~2
minutes before the kill, confirming the kill did not land during an
active checkpoint write).

### a. Loaded the existing checkpoint — confirmed by the exact log line

**[V]**
```
[TRANCHE2-WRITE] RESUMING from checkpoint: batches_completed=3, cumulative_processed=1500, resolved_so_far=1321
```
— the checkpoint-loading branch, not the "starting fresh" branch batch
1's test exercised.

### b. Resumed at the correct batch

**[V]** Immediately followed by:
```
[TRANCHE2-WRITE] === Batch 4/10 (500 markets in slice) ===
```
— `range(batches_completed, n_batches)` = `range(3, 10)` correctly began
at batch 4 (index 3), skipping batches 1–3 entirely, exactly as designed.

### c. Markets in the skip list are skipped — checked directly, found NOT exercisable here, reported honestly

**[V] `fresh=500, skipped=0` for batch 4's restart** — the skip-list
mechanism was **not observably exercised** by this test. This is not a
failure of the fix; it is a structural property of the driver's design,
worth stating plainly rather than assumed away:

The fixed 5,000-market sample has no duplicate `market_id`s
(`random.sample()` draws without replacement), and batches are
non-overlapping, fixed 500-row slices of that list in a fixed order. The
loop (`for batch_num in range(batches_completed, n_batches)`) never
re-enters a batch once it is marked complete. Given both properties
together: **a `market_id` already present in `resolved_market_ids` (from
some earlier, completed batch) can never appear again in any batch slice
this driver will ever process** — the two sets are disjoint by
construction. The `if market_id in resolved_ids: skip` check is
therefore, under this driver's current architecture, **evaluated 5,000
times across a full tranche and can never be true.**

What *does* protect against double-writes when a batch is killed and
restarted (as batch 4 was) is a **different mechanism**: re-entering the
*same* batch slice from its own start and relying on
`mark_market_resolved()`'s own idempotent same-rank-match comparator to
safely no-op the markets already written before the kill — exactly the
mechanism batch 1's kill test proved, and this test reproduces at a
different point in the run (see (d)). The `resolved_market_ids` field
remains useful — it is a more accurate *record* of which markets are
confirmed resolved, now correctly populated per defect 2's fix (verified
below) — but its *runtime skip-checking* role is currently unreachable.
Reported as found, not claimed as demonstrated when it was not.

### d. Markets written mid-batch before the kill were re-attempted and correctly no-op'd — verified by timestamp, not count alone

**[V]** 264 markets were fetched, classified `resolved`, and written
(each with this driver's unconditional `conn.commit()`) in the ~100
seconds before the kill — confirmed directly: `resolution_evidence_source='clob'`
count went 1,616 → 1,880 during that window, with the last write landing
at `15:12:07.735110`, 0.35s before the kill signal.

After the restart, **zero of those 264 markets had their
`resolution_recorded_at` timestamp changed** by the third invocation's
re-processing of batch 4 (checked directly, same method as batch 1's
test: querying for any `resolution_recorded_at` after the restart's
15:13:41 launch time among the pre-kill window's market set — none
found). All 264 were correctly reclassified `"no-op: same-rank value
matches existing"` on re-attempt. Exact reconciliation: cumulative
`no-op` count across the whole tranche = 356 = 92 (batch 1's kill
artifact) + 264 (this kill's artifact) — precisely accounted for, no
unexplained residual.

### e. Checkpoint survival — the atomic rename was exercised, but not *by* this kill

**[V]** The checkpoint on disk after the kill was valid, parseable JSON,
correctly reflecting batch 3's state (not corrupted). But **this specific
kill did not land during an active checkpoint write** — the last
checkpoint write (batch 3's) completed and was confirmed on disk
(`last_updated_utc: 15:10:12Z`) roughly two minutes before the SIGKILL at
15:12:08, which landed deep inside batch 4's row-processing loop, nowhere
near a `write_checkpoint()` call. The atomic write-to-temp-then-`os.replace`
mechanism itself was exercised nine times over the course of this run
(once per completed batch, 2 through 10) and never produced a corrupt or
partial checkpoint file at any of those points — but no kill in either
test happened to land *during* one of those windows specifically. Stated
plainly rather than claimed as proven: the atomic-rename's crash-safety
under a kill *during* the rename itself remains unexercised by either
test in this arc so far, though `os.replace` is POSIXly atomic by
construction and not something this driver's own logic could partially
apply.

---

## Abort conditions — live, none fired

**[V]** All six conditions were evaluable throughout (500-row batches
clear the n≥100 floor for both batch and cumulative checks on every
batch). Batch indeterminate rates ranged 2.6%–4.8%; cumulative ranged
3.4%–4.0% — both comfortably under their 10%/20% thresholds throughout.
Zero trigger fires. `check_resolution_write_atomicity` = 0 at every
checkpoint and in the final direct check. Non-whitelisted-reason rate:
0% at every checkpoint — every accepted/no-op outcome across all 10
batches was either `"written"` or `"no-op: same-rank value matches
existing"`, both whitelisted post-fix. Pacing never approached 1.0s/call
(excl.-sleep average 0.155–0.178s/call throughout).

---

## Proceed criteria — individually

| # | Criterion | Status |
|---|---|---|
| 1 | All 10 batches complete | **MET.** 10/10, `cumulative_processed: 5000/5000`. |
| 2 | Checkpoint accurate and uncorrupted throughout | **MET.** Valid JSON at every check; `cumulative_tally['resolved']` (4,723) matches DB ground truth (`evidence_clob` delta) exactly — see §a below. |
| 3 | The second kill-and-resume exercised the checkpoint-loading path and behaved as specified | **MET for (a) and (b)** (checkpoint loaded, correct batch resumed) **and (d)** (no double-write, verified by timestamp) **and, with the honest caveat above, (c)** — the skip-list mechanism was found to be structurally unreachable under this driver's design rather than "not working"; the underlying no-double-write guarantee it exists to support is provided by a different, verified mechanism. **(e) is unresolved** — the atomic-rename's behavior under a kill *during* the rename itself remains untested by either kill test in this arc, though nothing here suggests it would fail. |
| 4 | Zero trigger fires, zero atomicity violations | **MET.** Zero fires; 0 throughout and after. |
| 5 | Indeterminate rate consistent with the ~5% baseline | **MET.** Final cumulative: (30+152)/(4723+95+30+152) = 182/5000 = 3.6% — on baseline. |
| 6 | No unpredicted rejection patterns under the corrected whitelist | **MET.** Only `"written"` and `"no-op: same-rank value matches existing"` appeared across all 5,000 processed rows; zero occurrences of any of the five PAUSE-classified reasons (including zero same-rank disagreements). |

**Five of six criteria fully met; the sixth (kill-and-resume) is met on
every sub-point actually testable, with one honestly-reported structural
limitation (the skip-list's within-batch reachability) that reflects a
property of the current design, not a failure discovered by testing.
Nothing here blocks tranche 2 from having served its stated purpose.**
Whether to proceed to the full sweep remains a separate decision, out of
this task's scope, per its own constraints.

---

## Post-write verification

### a. Evidence-source delta and sample rows

**[V]** `resolution_evidence_source='clob'`: **673 → 4,926**, delta
**+4,253** this run. Cross-checked against DB ground truth two ways:
`resolved_markets` moved 225,654 → 229,907 (+4,253, exact match), and the
whole-tranche total (203 pre-tranche-2 → 4,926 final = +4,723) matches
the checkpoint's own `cumulative_tally['resolved']` (4,723) exactly.
Five sample rows from this run's final batch:

| market_id (truncated) | resolved | winning_outcome | resolution_date | resolution_recorded_at | evidence_source | evidence_detail |
|---|---|---|---|---|---|---|
| 0x4d8a0e49... | 1 | Under | 2026-08-22 15:38:04.27 | 2026-08-22 15:38:04.27 | clob | token.winner |
| 0x8ef828ea... | 1 | Up | 2026-08-22 15:38:03.89 | 2026-08-22 15:38:03.89 | clob | token.winner |
| 0x0ccccb16... | 1 | Down | 2026-08-22 15:38:03.51 | 2026-08-22 15:38:03.51 | clob | token.winner |
| 0xa1ce91a9... | 1 | No | 2026-08-22 15:38:03.12 | 2026-08-22 15:38:03.12 | clob | token.winner |
| 0xfac1970f... | 1 | Over | 2026-08-22 15:38:02.74 | 2026-08-22 15:38:02.74 | clob | token.winner |

Notably, this sample shows winning outcomes beyond binary Yes/No
("Under", "Up", "Down", "Over") — expected, since §C's sweep predicate
(unlike tranche 1's Geo/Elections-scoped one) draws from the full market
population, which includes crypto-price and sports-total markets with
non-binary outcome tokens.

### b. Branch-firing counts across all 10 batches

**[V]** **4,367 `"written"` (trivial first-write). 356 `"no-op: same-rank
value matches existing"` — but this figure is a checkpoint-bookkeeping
artifact of the two kill tests, not 356 independently-occurring benign
re-confirmations in normal operation: 92 trace to batch 1's kill (markets
written by the killed process but never recorded in any checkpoint,
so their "written" event was never counted anywhere and they surface only
as a "no-op" on their next, correct, safe detection) and 264 trace to
this session's batch-4 kill, for the identical reason. 92 + 264 = 356,
exactly.** Zero cross-rank overwrite, zero untagged-legacy-improvement,
zero same-rank disagreement.

**On the cross-rank overwrite question specifically, asked directly:**
it did **not** fire — not once, across all 5,000 processed candidates in
this tranche, on top of zero occurrences in tranche 1. The design
document's own framing (SS C abort condition 6: "a CLOB write is
*expected* to occasionally outrank an already-present Gamma value")
predicts this should be a routine, unremarkable occurrence at
sufficient scale — 5,000 candidates across two tranches has not produced
one yet. This is not itself concerning (nothing here suggests the branch
is broken — it was fabricated and confirmed working correctly in
isolation during the driver-fix verification session,
`2026-08-22-tranche2-driver-fixes.md`) but it does mean the *prediction*
that it should be routine remains unconfirmed by production data through
9,723 total resolution-assertion candidates (317 + 5,000, tranches 1 and
2 combined) so far. Worth watching in the full sweep, not treated as
settled.

### c. Atomicity

**[V]** `check_resolution_write_atomicity`: **0**, checked after every
batch (10 checks) and in a final direct check post-completion.

### d. Trigger

**[V]** `trg_resolved_no_unresolve` present, unchanged, did not fire —
zero exceptions across all 5,000 processed rows.

### e. Post-write fingerprint vs. this run's pre-write capture (`8ee20d5`)

| Metric | Pre-resume (`8ee20d5`, 15:02) | Post-completion | Delta | Attributable? |
|---|---|---|---|---|
| traders | 171,540 | 171,540 | 0 | n/a |
| trades | 11,663,146 | (not re-captured; background growth, unrelated) | — | No — background monitoring, consistent with every prior fingerprint in this arc |
| positions | 7,692,511 | (not re-captured) | — | No — background |
| markets | 745,069 | 745,069 | 0 (no new markets created by this write) | n/a |
| resolved markets | 225,654 | 229,907 | **+4,253** | **Yes — exact match to this run's evidence_clob delta** |
| Geo/Elec resolved+gap-clean | 10,792 | 10,792 | 0 | n/a — expected (no category filter in this tranche's predicate; see "before resuming" §1) |
| `resolution_evidence_source='clob'` | 673 | 4,926 | **+4,253** | **Yes — exact match** |
| `resolution_evidence_source='gamma'` | 12 | 12 | 0 | n/a, untouched |
| `resolution_evidence_source='hydration_fill'` | 1 | 1 | 0 | n/a, untouched |
| `check_resolution_write_atomicity` | 0 | 0 | 0 | Clean throughout |

**Every resolution-specific delta is exactly attributable to this run's
4,253 new writes; the whole-tranche total (4,723) reconciles exactly
against the checkpoint's own count. No count decrease anywhere.**

### f. Test suite

**[V]** `run_tests.py` re-run after completion. **File-level baseline
unchanged: 16 files, 15 passed, 1 failed
(`test_backtest_window_population.py`), same as every prior checkpoint
this arc.**

**T2f did NOT move this time: still 6,273** — same as after tranche 1's
completion. This is the correct, expected, fully-attributable result, not
stale data or a re-run against the wrong state (the writes were confirmed
landed via direct DB queries *before* this test run started). **Traced to
root cause, not accepted at face value:** `test_backtest_window_population.py`
is itself scoped to `category IN ('Geopolitics', 'Elections')` (confirmed
by reading the test file directly, line 172). Tranche 2's sample was
drawn from §C's category-unrestricted predicate (pre-flight question 1,
`2026-08-22-tranche2-execution.md`) — and, confirmed independently via
the DB fingerprint (`geo_elec_resolved_gapclean` unchanged at 10,792,
both before and after this run), **none of tranche 2's 4,723 newly-
resolved markets happen to be Geo/Elections category.** A test scoped to
that category showing zero movement when nothing in that category
changed is exactly correct — two independent measurements (the test's own
result and the DB fingerprint) agree, not a coincidence being waved away.

### g. Pacing and the full-sweep projection, re-derived

**[V]** Observed pacing, averaged across all 10 batches (5,000 calls):
**2,080.8s / 5,000 = 0.416s/call**, including the 0.25s sleep. This is
the number that matters for a runtime projection, not the
"avg_pace_s_per_call" figure logged per batch (0.155–0.178s), which
**excludes the sleep** (it measures only the CLOB fetch/processing time,
timed before the `time.sleep(SLEEP)` call) — disclosed here so this
distinction isn't silently conflated with a slower true rate.

**Re-deriving the full-sweep projection from this fuller data** (10
batches, consistent throughout, not batch 1's single data point):
against today's candidate population (~518,495, per
`2026-08-22-tranche2-execution.md`'s pre-flight question 1, itself
already several hours stale and growing) at 0.416s/call:
518,495 × 0.416s ≈ 215,690s ≈ **59.9 hours ≈ 2.5 days** — **not the
~36-hour estimate** the pre-registration's planning-stage 0.25s/call
assumption produced. The observed per-call rate (0.416s) is **66% higher**
than the planning assumption (0.25s), driven entirely by real CLOB
API round-trip time on top of the deliberate sleep, consistent across
all 10 batches (elapsed-per-batch ranged only 202.6–214.0s, a tight
±3% band — this is a stable, well-characterized rate, not a fluke).
**The full sweep's runtime estimate should be revised to ~60 hours before
it is scheduled**, not left at the original 36-hour planning figure.

---

## What this closes out

Tranche 2 has done what it was for: scale and mechanics are now tested,
twice, under a real SIGKILL, at two different points in a run (before and
after a checkpoint exists) — the no-double-write guarantee held both
times, verified by direct timestamp inspection, not inferred from counts
alone. One real architectural property was found and reported plainly
rather than glossed over: the checkpoint's skip-list cannot be
demonstrated to skip anything under the current non-overlapping-batch
design, though the correctness it exists to protect is provided by a
different, independently-verified mechanism. The full-sweep runtime
estimate needs revising upward, materially, before any decision to run
it. Neither the full sweep nor any further tranche was started here, per
this task's own constraints.
