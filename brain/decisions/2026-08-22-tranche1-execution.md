# 2026-08-22 — Tranche 1 Execution: PAUSED at 25/317

## STATUS: TRANCHE 1 INCOMPLETE. TRANCHE 2 BLOCKED.

This was the first production write of the discovery-gap-closure arc's
resolution-assertion branch. It ran, produced 16 real, verified-correct
writes, and then **paused itself** per the pre-registration's own abort
protocol (`2026-08-21-discovery-gap-closure-prereg.md`, 60a1529, §C) when
the batch-level indeterminate rate crossed 10% at row 25 of 317. This is a
**PAUSE**, not a hard abort, and not evidence of a code defect — but per
the task's explicit instruction ("stop immediately and report if any
[abort condition] fires"), the run was stopped rather than continued on
judgment, and none of the four proceed-to-tranche-2 criteria can be
declared fully met with 292 of 317 candidates unprocessed. **Tranche 2 does
not run from this state.**

All claims below tagged **[V]** verified (ran/read it myself) or **[I]**
inferred.

---

## 0. Carried forward from the prior checkpoint (not redone)

- **[V]** Pre-write fingerprint captured and committed: `first-repo`
  `a2b4b82`,
  `data/characterizations/tranche1_execution/tranche1_prewrite_fingerprint_20260822T123313Z.json`.
  This capture also corrected a predicate inconsistency in the morning's
  session-start baseline artifact (`cefabdd`): that artifact's 527,617
  candidate-population figure used `backfill_market_dates.py`'s literal
  non-`geo-only` query, which lacks the `resolved=0` filter §C's own
  predicate specifies. Corrected figure: 518,698 (the 8,919-row difference
  is entirely `resolved=1` markets that still have a null `end_date`/
  `resolution_date` — not data loss, a different predicate).
- **[V]** WAL-safe backup complete and integrity-verified:
  `backups/markets_20260822_123342.db`, 16,542.5 MB, exit code 0.

**A timing gap to be transparent about:** the pre-write fingerprint was
captured at 12:33:13 UTC; the write itself did not actually run until
14:15 UTC (visible directly in the written rows' timestamps below), a gap
of ~1h42m caused by a session usage-limit checkpoint between those two
steps. §G requires the fingerprint be captured "immediately before" the
write; that requirement was not strictly met here due to the pause. This
means the raw `traders`/`trades`/`positions`/`markets` deltas reported in
§5e below include ~1h42m of ordinary background service activity (the
always-on `polymarket-monitoring` loop), not only this write's effect. The
**resolution-specific** deltas (evidence_source, resolved-market counts,
candidate-population shrinkage) remain cleanly attributable to this write
alone, verified by exact arithmetic (§5a, §5e).

---

## 1. Live re-derivation of the expected answer

**[V]** Re-ran the tranche-1/Q2-census predicate fresh
(`2026-08-20-discovery-gap-sizing-prereg.md` §3 SQL, unchanged) via a new,
distinctly-named copy of the established `q2_census_precheck.py` pattern —
`data/characterizations/tranche1_execution/tranche1_dryrun_precheck.py`
(logic byte-identical to the original; not overwriting step 1's original
verification artifact, per §G "durable, timestamped" convention).
Read-only (`mode=ro` connection, `dry_run=True` throughout).

**Population: 317 — unchanged from 08-20/08-21.**

| | 08-20 sizing result | Today (fresh, this session) |
|---|---|---|
| Population | 317 | 317 |
| Resolved | 203 | 203 |
| Open | 98 | 98 |
| No CLOB response / indeterminate | 16 | 16 (0 true-indeterminate + 16 no_clob_response) |
| `mark_market_resolved(dry_run=True)` on resolved | — | accepted=203, rejected=0, all `reason="written"` |

**Zero drift.** Today's figures are an exact reproduction of 08-20/08-21,
not merely "consistent with" — same population size, same three-way split.
This rules out both hypotheses the task asked me to distinguish between:
there is no population movement to explain (would show up as a changed
count) and no code-defect signal (would show up as a different
classification split or a rejected/flagged `mark_market_resolved` result).
Full detail: `tranche1_dryrun_precheck_result.json` (committed,
`first-repo` `43e268b`).

**A structural finding worth stating precisely, not just for this run:**
reading `monitoring/resolution_writer.py`'s branch logic directly (lines
157–186), the comparator branch taken is decided entirely by
`prev_resolved` (the market's OLD `resolved` value) — `if not prev_resolved:
reason = "written"` (trivial first-write); every other branch
(untagged-legacy-improvement, cross-rank overwrite, same-rank
match/disagreement) requires `prev_resolved` to already be truthy. Tranche
1's own selection predicate requires `(resolved = 0 OR resolved IS NULL)`
— **every row in this population is therefore structurally guaranteed to
take the trivial first-write branch, and no other branch is reachable for
this population, regardless of run outcome.** This differs from an
expectation stated in the task prompt (that this might be "the first time
the untagged-legacy branch may actually WRITE") — that branch requires an
already-`resolved=1` row with a NULL `evidence_source`, which tranche 1's
predicate excludes by construction. If that branch fires for the first
time, it will be in the wider sweep population (which uses an OR-based
date-null predicate, not tranche 1's AND-based one, and does not exclude
already-resolved rows the same way) — not here.

---

## 2. Scoping — exactly how

**[V] `--geo-only` was NOT used and would have been wrong.** Read
`backfill_market_dates.py`'s `get_markets_to_backfill()` directly: the
`--geo-only` flag's query joins `trades.market_category` (not
`markets.category`), has no `trade_gap_flag` filter at all, and uses
`end_date IS NULL OR resolution_date IS NULL` (OR, not the tranche-1
predicate's AND). None of these match §C's tranche-1 definition. Running
the raw CLI with `--geo-only --limit N` would have processed a different,
unverified population — explicitly prohibited ("Do NOT run it unscoped").

**What was actually run instead:** a new, narrowly-scoped driver script
(`tranche1_write.py`, committed `first-repo` `43e268b`) that:
- Selects candidates via the **exact** tranche-1 SQL from
  `2026-08-20-discovery-gap-sizing-prereg.md` §3: `category IN
  ('Elections','Geopolitics') AND (trade_gap_flag = 0 OR trade_gap_flag IS
  NULL)`, intersected with `(resolved = 0 OR resolved IS NULL) AND
  resolution_date IS NULL AND end_date IS NULL` — the same predicate
  already used, read-only, by `step1_verification_v2/q2_census_precheck.py`
  and this session's dry-run (§1).
- Imports and calls, **unmodified**: `_get_connection`, `_fetch_by_clob`,
  `_extract_clob_resolution` from `scripts/backfill_market_dates.py`, and
  `mark_market_resolved` from `monitoring/resolution_writer.py`. No
  production file was edited; this is a new file reusing existing,
  unmodified functions, matching the precedent this arc already
  established for exactly this scoping problem.
- Pacing: `time.sleep(0.25)` per call, per §C (not the script's 0.1s
  default).
- Ran in the foreground, observed directly (not detached/`nohup`) — short
  enough (317 calls) that direct observation was preferable, per the task.

**One deliberate deviation from the underlying script's own behavior,
disclosed:** `tranche1_write.py` calls `conn.commit()` unconditionally
after every accepted `mark_market_resolved()` write. Reading
`backfill_market_dates.py`'s own assertion-branch code (lines 272–316)
directly: its `conn.commit()` (line 309) is nested inside `if
assert_end_date_str:` — conditional on the CLOB response also carrying a
usable end-date field. Step 1's own finding (`2026-08-21-step1-implementation.md`,
d41d02b) is that already-resolved CLOB markets commonly have `end_date_iso:
None`. Read literally, that means the production script's own assertion
branch can accept a resolution write via `mark_market_resolved()` and never
call `conn.commit()` for that specific market's turn through the loop — the
write would sit in Python's default deferred-transaction mode until some
*later* iteration's commit (for a market that does have an end date)
happens to flush it, or risk being lost via an implicit rollback if the
connection closes first. This harness avoids that risk entirely by
committing every accepted write immediately, unconditionally. `backfill_market_dates.py`
itself was not touched — this is worth naming as a follow-up for that file,
not fixed here.

---

## 3. Abort-condition monitoring — live, and what fired

Checked every 25 processed rows (`CHECK_EVERY=25` in `tranche1_write.py`),
not only at the end. One honest limitation of this harness, disclosed: it
tracks a single **cumulative** indeterminate rate rather than separately
tracking a rolling last-batch-of-25 rate (condition 2) and a
whole-run-cumulative rate (condition 3) as two distinct numbers. At the
first checkpoint (row 25) these are numerically identical by construction
(only one checkpoint's worth of data exists yet), so this did not affect
the correctness of the stop decision made here — but it would need fixing
before a longer, multi-checkpoint run (tranche 2 or the full sweep).

**What happened, in order:**
1. Pre-write `check_resolution_write_atomicity` check: **[V] 0** — cleared
   before any call was issued.
2. Population re-derived at write time: **[V] 317** (unchanged from §1,
   issued within the same minute).
3. Rows 1–25 processed: `{'resolved': 16, 'open': 6, 'indeterminate': 0,
   'no_clob_response': 3}`. Pacing: 0.218s/call (within budget). Atomicity:
   still 0. `mark_market_resolved`: accepted=16, rejected=0, reasons=
   `{'written': 16}` — 100% trivial branch, exactly as predicted in §1.
4. At row 25: indeterminate rate (indeterminate + no_clob_response, over
   classifiable rows) = 3/25 = **12.0%**, crossing **abort condition 2**'s
   10% batch threshold.
5. **[V] Run paused itself, as designed.** No further calls issued. This is
   explicitly the "plausible noise, not necessarily a defect" case §C's own
   justification for condition 2 anticipated — 12.0% at n=25 is well within
   the range the sizing run's own stratified sampling already observed
   (§C: "comfortably inside the highest single stratum observed there
   (O-newest tercile, 12%)"), and the full-population dry-run in §1 (n=317)
   found the true no-CLOB-response rate to be 16/317 = 5.05%, close to
   baseline — strongly suggesting this is small-sample noise from an
   unlucky first 25 rows, not a shift in the underlying rate. **This is an
   inference, not a re-verified fact** — the remaining 292 candidates were
   not processed, so the true rate over the full tranche after resuming is
   not yet known.

**No other condition fired.** Trigger did not fire (0 exceptions, `trg_resolved_no_unresolve`
confirmed present and unchanged post-write). No rejection reason other
than `"written"` appeared. Pacing stayed well under 1.0s/call throughout.

---

## 4. Proceed criteria — individually, as instructed

| # | Criterion | Status |
|---|---|---|
| 1 | Resolved count within a small tolerance of the freshly-derived expected count (203) | **NOT YET EVALUABLE.** Only 16/203 expected resolved markets have been processed (7.9%). The tranche is incomplete; this criterion cannot be assessed until it finishes. |
| 2 | Indeterminate rate consistent with the ~5% baseline | **NOT MET, as measured at the pause point** (12.0% over the first 25 rows vs. ~5% baseline) — though §1's full-population dry-run this session (5.05%, n=317) suggests the true rate is on baseline and this is small-sample noise. Cannot be confirmed without resuming. |
| 3 | Zero trigger fires | **MET.** Confirmed zero fires; trigger intact pre- and post-write. |
| 4 | Zero unpredicted rejection patterns | **MET.** Only `reason="written"` appeared; zero rejected; matches the structural prediction in §1. |

**2 of 4 met, 1 not met (pending re-evaluation), 1 not yet evaluable. Per
the task's own rule ("If any is NOT MET, tranche 2 is blocked"), tranche 2
is blocked.** This is a pause-for-review outcome, not a failure verdict —
the pre-registration's own language for condition 2 anticipates exactly
this kind of early-batch noise — but it is not this session's call to
resume and re-evaluate unilaterally; that is what "PAUSE — wait for manual
review" means.

---

## 5. Post-write verification

### a. Evidence-source delta and sample rows

**[V]** `resolution_evidence_source='clob'`: **0 → 16**, an exact match to
`accepted=16`. Five of the sixteen written rows, sampled directly:

| market_id (truncated) | resolved | winning_outcome | resolution_date | resolution_recorded_at | evidence_source | evidence_detail |
|---|---|---|---|---|---|---|
| 0x11176fe7... | 1 | No | 2026-08-22 14:15:59.352090 | 2026-08-22 14:15:59.352090 | clob | token.winner |
| 0x005aa3a9... | 1 | Yes | 2026-08-22 14:15:54.019236 | 2026-08-22 14:15:54.019236 | clob | token.winner |
| 0x14102086... | 1 | No | 2026-08-22 14:16:01.248440 | 2026-08-22 14:16:01.248440 | clob | token.winner |
| 0x13badb4b... | 1 | No | 2026-08-22 14:16:00.853600 | 2026-08-22 14:16:00.853600 | clob | token.winner |
| 0x17979176... | 1 | No | 2026-08-22 14:16:02.802709 | 2026-08-22 14:16:02.802709 | clob | token.winner |

`resolution_date == resolution_recorded_at` for every sampled row — correct
per `mark_market_resolved`'s 3-tier fallback (`resolution_event_time=None`
was passed throughout, per §C, and there was no prior `resolution_date` to
preserve since this population's predicate requires it NULL going in — so
every write falls through to write-time).

### b. Branch-firing counts

**[V]** All 16 accepted writes: `reason="written"` (trivial first-write).
**Zero** untagged-legacy-improvement, **zero** cross-rank overwrite,
**zero** same-rank match, **zero** same-rank disagreement. Per §1's
structural finding, this is not merely what happened — it is what *must*
happen for this specific population, every time, by construction of its
own selection predicate. Prior production runs (this codebase's history)
have also only ever exercised the trivial branch; this run does not change
that record. The other branches remain unexercised in production.

### c. Atomicity

**[V]** `check_resolution_write_atomicity` (audit_invariants.py's exact
query: `resolution_recorded_at IS NOT NULL AND resolution_evidence_source
IS NULL`): **0**, both mid-run (checked at row 25) and in a fresh
post-write check.

### d. Trigger

**[V]** `trg_resolved_no_unresolve` present and unchanged
(`sqlite_master` query, body identical to prior sessions' checks). Did not
fire — no exception was raised or caught during any of the 16 writes.

### e. Post-write fingerprint vs. the pre-write capture (`a2b4b82`)

| Metric | Pre-write (12:33) | Post-write (14:16) | Delta | Attributable to this write? |
|---|---|---|---|---|
| traders | 171,540 | 171,540 | 0 | n/a |
| trades | 11,663,141 | 11,663,142 | +1 | **No** — background monitoring, ~1h42m elapsed (§0) |
| positions | 7,689,429 | 7,692,507 | +3,078 | **No** — background monitoring/position-tracking activity over the same elapsed window; not investigated further, out of scope here, flagged for awareness (a large jump relative to only +1 new trade, plausibly a FIFO position-tracker catch-up batch, not re-derived this session) |
| markets | 745,066 | 745,067 | +1 | **No** — background monitoring |
| resolved markets | 224,981 | 224,997 | **+16** | **Yes — exact match to this write** |
| Geo/Elec resolved+gap-clean | 10,589 | 10,605 | **+16** | **Yes — exact match; all 16 written rows are Geo/Elections, gap-clean, by construction of the tranche-1 predicate** |
| `resolution_evidence_source='clob'` | 0 | 16 | **+16** | **Yes — exact match** |
| `resolution_evidence_source='gamma'` | 12 | 12 | 0 | n/a, untouched |
| `resolution_evidence_source='hydration_fill'` | 1 | 1 | 0 | n/a, untouched |
| `check_resolution_write_atomicity` | 0 | 0 | 0 | Clean throughout |
| Q2/tranche-1 candidate population | 317 | 301 | **-16** | **Yes — exact match: only the 16 successfully-resolved rows left the candidate set; the 6 "open" and 3 "no_clob_response" rows from the processed 25 remain candidates, since their `end_date`/`resolution_date` are still NULL** |

**No count decrease anywhere.** Every resolution-specific delta is exactly
+16 or -16, precisely matching what 16 successful writes should produce —
no more, no less. The non-resolution baseline counts moved only from
ordinary concurrent background activity during the ~1h42m gap disclosed in
§0, not from this write.

### f. Test suite

**[V]** `run_tests.py` re-run after the write. **File-level baseline
unchanged: 16 files, 15 passed, 1 failed
(`test_backtest_window_population.py`, 19/24)** — matches the standing
baseline exactly, no new file-level failure.

**Per §D, the reason WAS checked, not accepted as "still failing, same as
before":**

| | Before this write (this morning) | After this write |
|---|---|---|
| T2 (agree) | Expected 4658, got 4660 | Expected 4658, got 4660 (unchanged) |
| T2b (false negatives) | Expected 54, got 52 | Expected 54, got 52 (unchanged) |
| T2c (zero-trade) | Expected 555, got 550 | Expected 555, got 550 (unchanged) |
| T2d (genuine false positives) | Expected 573, got 582 | Expected 573, got **585** (+3) |
| T2f (reconciliation: old-method total) | 6070 | **6086** (+16) |

**T2f's old-method total moved by exactly +16 — a precise match to this
write's resolved-market count.** This is strong, specific evidence that
the movement is attributable to tranche 1's write, not noise or something
else: these 16 markets previously had `resolution_date IS NULL` (excluded
from the "old method"'s resolution_date-based count entirely); after the
write, all 16 have a real `resolution_date` (write-time, per the 3-tier
fallback, §5a) and are now counted by the old method for the first time,
growing its raw total by exactly 16. This is exactly what §D predicted:
"the live side of that comparison will genuinely change after the sweep...
this is expected, not a regression."

**Not fully reconciled, disclosed rather than glossed over:** T2d's own
visible bucket grew by only +3, not +16 — the other 13 of the 16 newly-
resolved markets moved the "old total" without a matching movement in any
of T2/T2b/T2c either (all three stayed byte-identical). This means 13 of
the 16 are landing in some part of the old-method total this test doesn't
break out into one of its four named buckets, or in a combination not
visible from the summary output alone. I did not trace this further — it
would require reading `test_backtest_window_population.py`'s bucketing
logic directly, which is out of scope for this execution task. What can
be stated confidently: the movement is fully consistent with this write in
direction and magnitude (+16 exactly on the total), the file-level
pass/fail baseline is unchanged, and nothing about this pattern resembles
a new, unattributable regression.

---

## 6. What this means for next steps

**Tranche 1 is paused, not failed, not aborted.** 16 correct, verified
production writes exist. The most likely explanation for the pause is
small-sample noise in the first 25 of 317 rows — the full-population
dry-run this session found 5.05%, on baseline — but that is not yet
re-confirmed against a live write of the full tranche, and per the task's
own protocol this is exactly the kind of judgment call that requires
manual review before resuming, not an autonomous continue decision. Two
options exist for a future session, named here, neither taken:
(a) resume `tranche1_write.py` against the now-shrunk 301-candidate
population (structurally correct — it will simply re-derive the smaller
set live and continue, per §C's resumability design), or
(b) treat the 25-row sample as sufficient evidence the pause was noise and
proceed directly to a fresh, larger tranche-1 completion attempt.
Neither is executed here. **Tranche 2 remains blocked either way** until
tranche 1 completes and all four proceed criteria are re-evaluated against
the completed run.
