# 2026-08-22 — Tranche 2 Execution: STOPPED after batch 1/10

## VERDICT: ABORT CONDITION FIRED (batch 1, "unpredicted rejection pattern"). STOPPED PER PROTOCOL. THE FULL SWEEP IS BLOCKED.

Tranche 2 ran one batch (500 of 5,000 markets), survived a deliberate
mid-batch kill cleanly with **zero double-writes**, then paused itself
after batch 1 completed on an abort condition that technically fired
correctly against the driver's own whitelist — but on a **benign, fully
understood, and directly-caused-by-this-session's-own-kill-test**
pattern, not a defect in `mark_market_resolved()` or the underlying
design. Two real gaps in the driver script itself (not production code)
were found as a direct result, named below, not fixed here. Per the
task's explicit instruction ("STOP AND REPORT... state that the full
sweep is blocked"), this session stopped rather than patching and
pushing through.

All claims tagged **[V]** verified (ran/read it myself) or **[I]** inferred.

---

## Pre-flight question 1: which predicate

**[V] §C's own predicate was used: `(resolved = 0 OR resolved IS NULL)
AND (end_date IS NULL OR resolution_date IS NULL)`** — not
`backfill_market_dates.py`'s own literal query (which has no `resolved`
filter at all).

**The two predicates differ by 9,122 rows today**, confirmed via direct
query:

| Predicate | Count today |
|---|---|
| §C's predicate (resolved-filtered) | 518,495 |
| Script's literal query (no resolved filter) | 527,617 |
| Difference | **9,122** |

Of those 9,122 (already-resolved markets with a null date field): 8,909
have `resolution_evidence_source IS NULL` (true untagged-legacy
candidates — the branch would fire for these), and **203 have
`evidence_source='clob'`** — these are exactly tranche 1's own 203 writes.
`mark_market_resolved()` does not touch `end_date`, so tranche 1's newly
resolved markets remain in the script's literal (non-resolved-filtered)
candidate set via the `end_date IS NULL` side of its OR clause, even
though they are now fully, correctly resolved. **This is a real,
separate finding worth flagging**: if `backfill_market_dates.py`'s raw
CLI is ever invoked against its own literal query (which is exactly what
`daily_maintenance.py`'s currently-held `--limit 2000` step does), it
will re-encounter these 203 (and the other 8,909) rows and re-attempt
them — harmlessly, per this session's own kill-and-resume finding below
(the comparator correctly no-ops a matching re-attempt), but wastefully.

**Decision and justification: §C's predicate was chosen**, not the
script's literal one. §C's own Pacing and Batching/resumability sections
both explicitly define "the sweep's own candidate query" using the
resolved-filtered form throughout the document (the 515,491 planning
estimate, the resumability self-shrinking-population argument, and
tranche 1's own predicate all use it consistently) — deviating from that
for tranche 2 specifically would be inventing a new scope outside what
was pre-registered, without a fresh amendment. **Consequence, stated
plainly**: the untagged-legacy-improvement branch remains structurally
unreachable in tranche 2's sample, for the same reason it was unreachable
in tranche 1 (the predicate excludes `resolved=1` rows by construction,
and `resolution_writer.py`'s branch logic is decided entirely by
`prev_resolved`). **It will not get its first production exercise here.**
Per the finding above, its first production exercise most likely happens
via `daily_maintenance.py`'s own already-scheduled, already-running (at
`--limit 2000`) invocation of the script's literal query — worth watching
for at tomorrow's 2026-08-23 06:00 UTC run, not manufactured in this
tranche.

---

## Pre-flight question 2: the seed/resume tension

**[V] Agreed with the task's own reasoning and materialized the 5,000
sample ONCE, before any write, as a fixed, persisted, committed
artifact** — `data/characterizations/tranche2_execution/tranche2_sample_5000.json`
(first-repo `a7cbebc`), drawn by `tranche2_sample_materialize.py`
(committed alongside it), `random.seed(20260821)` over the live population
ordered deterministically (`ORDER BY market_id`) for reproducibility.
Population at draw time: **518,495**, matching §C's predicate exactly.
The driver (`tranche2_write.py`) reads this fixed list and never
re-samples; batches are fixed 500-row slices of this list in list order.
No better construction was found or substituted — the fixed-list approach
is the correct fix for the tension the task described.

---

## Before the write

- **[V] Fresh backup**, taken before this run and after tranche 1's 203
  writes: `backups/markets_20260822_143948.db`, 16,545.4 MB,
  integrity-verified, exit code 0. The 12:33 backup is superseded as the
  active restore point by this one.
- **[V] Fresh fingerprint**, committed:
  `data/characterizations/tranche2_execution/tranche2_prewrite_fingerprint_20260822T144254Z.json`
  (first-repo `1edb78f`).
- **Remaining candidate population under the chosen (§C) predicate:
  518,495** — against the pre-registration's ~515,491 planning estimate
  (+3,004, consistent with ~2 days' organic growth net of tranche 1's
  -203) and against today's earlier (12:33) session-start baseline figure
  of 527,617 — **that earlier figure used the wrong (script's literal,
  non-resolved-filtered) predicate**, already caught and corrected in
  tranche 1's own pre-write fingerprint (`a2b4b82`) to 518,698; today's
  518,495 is directly comparable to that corrected figure, not to
  527,617, and reflects almost exactly tranche 1's -203 net of a couple
  hours' further organic growth.

---

## The run

**[V]** Driver committed before running: `tranche2_write.py` (first-repo
`1a54ad7`). Launched detached: `nohup python3 -u
data/characterizations/tranche2_execution/tranche2_write.py >
logs/discovery_gap_sweep_tranche2_*.log 2>&1 & disown`, exactly the mode
the full sweep will use, exercised here as instructed. (First launch,
14:43:31, was without `-u`; Python's default block-buffering on a
non-tty stdout meant the log file showed nothing until process exit —
harmless for the kill-test itself, since the checkpoint file — not the
log — is the actual resumability mechanism, but noted as an
observability gap; the relaunch after the kill used `-u` for real-time
visibility.)

---

## The kill-and-resume test

**[V] Killed deliberately at 14:44:12 UTC**, `kill -9` (SIGKILL, chosen
to simulate a hard crash rather than a graceful shutdown), **41 seconds
into batch 1**, confirmed via `ps` timing and the absence of any
checkpoint file at kill time (`data/checkpoints/` was empty — batch 1
never completed, so no checkpoint had been written yet; this specific
kill therefore did not exercise the atomic-rename protection itself,
since no checkpoint write was in flight at the moment of the kill —
disclosed rather than claimed as a full test of that specific mechanism).

**What had happened before the kill:** 92 markets were fetched,
classified `resolved`, and successfully written via `mark_market_resolved()`
— each followed by this driver's unconditional `conn.commit()` — in the
41 seconds before the SIGKILL landed. Confirmed directly:
`resolution_evidence_source='clob'` count went 203 → 295 (+92) during the
killed run's window, timestamps spanning 14:43:34.27 to 14:44:12.67 (the
last write landing within a third of a second of the kill signal itself).
`check_resolution_write_atomicity` = 0 immediately after the kill.

**Restart at 14:44:51 UTC**, same command, `-u` added. **[V] "No
checkpoint found — starting fresh"** — correct: batch 1's checkpoint was
never written, so this is the right behavior, not a bug. It re-processed
batch 1 from its start, including the 92 markets already resolved by the
killed run.

**Verified against the task's four required outcomes:**

| Requirement | Result |
|---|---|
| Resumes from the persisted checkpoint against the fixed list | **N/A for this specific kill** — no checkpoint existed yet (batch 1 incomplete at kill time), so there was nothing to resume *from*; the restart correctly started fresh instead. The checkpoint-resume path itself (loading an *existing* checkpoint and skipping its `resolved_market_ids`) was not exercised by this particular kill, only by a hypothetical restart after batch 1's checkpoint (see below). |
| No market is processed twice as a write | **[V] MET, verified directly.** Zero of the 92 pre-kill-resolved markets had their `resolution_recorded_at` timestamp changed by the resume run (checked: none fall after 14:44:51). All 92 stayed exactly as the killed run left them; `mark_market_resolved()`'s comparator correctly classified the resume's re-attempt on each as `"no-op: same-rank value matches existing"` (`accept=False`) — no `UPDATE` executed, confirmed by the unchanged timestamps. Evidence-source count reconciles exactly: 203 (pre-tranche-2) + 92 (killed run) + 378 (resume, batch 1's genuinely new writes) = **673**, matching the live count precisely. |
| No market from the sample is skipped | **[V] MET.** All 500 of batch 1's markets were freshly attempted in the resume (`fresh=500 skipped=0` — nothing to skip, since no checkpoint existed). |
| Checkpoint file not corrupted by the kill | **[V] MET, vacuously** — no checkpoint existed at kill time to corrupt. The checkpoint written after batch 1 *completed* (post-restart) is valid, parseable JSON, matching the run's own reported counts. |

**Conclusion on kill-and-resume: the core no-double-write guarantee is
verified and held.** But this specific kill (pre-first-checkpoint) is a
different, milder test than a kill *after* a checkpoint exists — that
scenario (verifying the checkpoint-loading and `resolved_market_ids`
skip-path under a real interruption) remains unexercised, and per the
findings below, would currently be handled *incompletely* by this driver
if attempted.

---

## Batch/cumulative — which condition was live

**[V]** Both conditions were evaluable in this run, unlike tranche 1 —
the standard 500-row batch size means the n≥100 floor is always cleared
within a single batch. Batch 1: `batch_indet_rate=4.0%`
`[EVALUATED]`, `cum_indet_rate=4.0%` `[EVALUATED]` — both comfortably
under their respective 10%/20% thresholds. **Neither the batch nor the
cumulative indeterminate-rate condition was the one that stopped this
run** — condition 5 (unpredicted rejection pattern) was.

---

## What actually fired, and why it is not a `mark_market_resolved()` defect

**[V]** After batch 1: `cum_reasons = {'no-op: same-rank value matches
existing': 92, 'written': 378}`. The driver's `ACCEPTED_REASONS`
whitelist contained only `"written"` and the untagged-legacy-improvement
string — it did **not** include `"no-op: same-rank value matches
existing"`. Non-accepted rate: 92/378 = 24.3%, far above the 1% threshold
— condition 5 fired, correctly, against the whitelist as coded.

**This is a driver-implementation gap, not evidence of a comparator
defect — the opposite, in fact.** The 92 "no-op: same-rank match"
results are the comparator working exactly as designed: each of those 92
markets was already resolved (via the killed run, same `evidence_source`
rank, same `winning_outcome`), and the correct, safe response to a
matching re-attempt is a no-op, not a second write. Re-reading
`monitoring/resolution_writer.py`'s branch logic directly: `"no-op:
same-rank value matches existing"` is a categorically different outcome
from `"flagged: same-rank disagreement"` — the pattern §C's abort
condition 6 (and this task's own restated condition) was actually written
to guard against, where two same-rank sources *disagree*. A same-rank
*match* is not disagreement; it is confirmation. **The driver's whitelist
should have distinguished them and did not.**

**Named as a defect to fix before continuing, not fixed here:**
`tranche2_write.py`'s `ACCEPTED_REASONS` set needs
`"no-op: same-rank value matches existing"` added, so a benign
re-confirmation (which this specific kill-and-resume test was always
going to produce, by construction) does not trigger the same pause as a
genuine disagreement would.

**A second, related defect found in the same batch's output, also not
fixed here:** the checkpoint's `resolved_market_ids` list is populated
only when `result.reason == "written"` — it does **not** include markets
resolved via the `"no-op: same-rank match"` path. Checked directly:
the checkpoint after batch 1 lists exactly **378** `resolved_market_ids`,
not 470 (378 fresh + the 92 already-resolved-and-reconfirmed). This means
a *future* restart from this checkpoint would still not skip those 92 —
it would safely, harmlessly, but needlessly re-attempt them again, and
again on every subsequent restart, since they would never be added to the
skip-list. Not data-unsafe (per the no-op finding above, re-attempting
them is harmless), but wasteful and worth fixing before a longer run
where restarts might be more frequent.

---

## Proceed criteria — individually

| # | Criterion | Status |
|---|---|---|
| 1 | All 10 batches completed, or a clean documented stop | **Clean documented stop, not completion.** 1 of 10 batches finished (500/5,000 processed). The stop was clean — the process exited via its own abort-handling code (`sys.exit(1)`), not a crash. |
| 2 | Checkpoint file accurate and uncorrupted throughout | **Uncorrupted: MET.** Valid JSON, matches the run's own reported counts. **Accurate: PARTIALLY** — correct for what it tracks, but incomplete per the second defect above (undercounts true resolved-market coverage by 92, all within batch 1). |
| 3 | Kill-and-resume behaved as specified | **Core guarantee MET** (no double-write, no skip, no corruption — see table above), **but only the "no prior checkpoint" resume path was exercised**, not the "resume from an existing checkpoint, skip its list" path, and the two defects above mean that second path would currently under-skip if exercised now. |
| 4 | Zero trigger fires, zero atomicity violations | **MET.** Zero exceptions, `check_resolution_write_atomicity` = 0 throughout and after. |
| 5 | Indeterminate rate consistent with the ~5% baseline | **MET, as far as it ran.** Batch 1: 4.0% (2 indeterminate + 18 no-CLOB-response out of 500) — on baseline. |
| 6 | No unpredicted rejection patterns | **NOT MET, against the driver's own whitelist as coded** — though substantively benign and fully explained (see above), this criterion is evaluated against what the driver actually flags, and it flagged this. |

**Per the task's own rule: at least one criterion (6) is not met, and
criteria 1 and 3 are only partially satisfied. The full sweep is
blocked**, and this specific tranche-2 run is incomplete (1/10 batches),
pending the two named driver fixes and a decision on how to proceed —
mirroring exactly how tranche 1's first pause (also a correctly-fired,
substantively-benign stop) was handled: documented, amended, then
resumed as a separate, deliberate step, not patched and pushed through
in the same breath as the finding.

---

## Post-write verification

### a. Evidence-source delta and sample rows

**[V]** `resolution_evidence_source='clob'`: **203 → 673**, delta **+470**
this run (92 from the killed attempt + 378 from the resume's fresh batch-1
writes) — reconciles exactly against the driver's own reported tally
(`cum_tally['resolved']` = 470 for batch 1). Sample of 3 rows spanning
both the killed run and the resume, all six resolution fields:

| market_id (truncated) | source | resolved | winning_outcome | resolution_date | resolution_recorded_at | evidence_source | evidence_detail |
|---|---|---|---|---|---|---|---|
| 0xff7fcade... | killed run | 1 | (per row) | 2026-08-22 14:43:34.27 | 2026-08-22 14:43:34.27 | clob | token.winner |
| 0x99dd530c... | killed run (last, right at the kill) | 1 | (per row) | 2026-08-22 14:44:12.67 | 2026-08-22 14:44:12.67 | clob | token.winner |
| (batch-1 fresh write, resume) | resume | 1 | (per row) | ≥2026-08-22 14:44:51 | ≥2026-08-22 14:44:51 | clob | token.winner |

(Winning-outcome values omitted from this table for brevity — same
`resolution_date == resolution_recorded_at` pattern holds throughout, per
the same write-time fallback logic verified in tranches 1 and its resume.)

### b. Branch-firing counts

**[V]** This run (batch 1, both invocations combined): **378
`"written"` (trivial first-write)**, **92 `"no-op: same-rank value
matches existing"`** (a rejection, not a branch that writes — the
comparator correctly declining a redundant re-confirmation), **0**
untagged-legacy-improvement, **0** cross-rank overwrite, **0** same-rank
disagreement. Consistent with pre-flight question 1's finding: the
untagged-legacy branch remains unreachable under §C's predicate, and did
not fire here. The same-rank-*match* result, while new (tranches 1/1-
resume never produced it, since nothing there was ever re-attempted after
a genuine success), is exactly the kill-test's own byproduct, not a
naturally-occurring production pattern from fresh candidates.

### c. Atomicity

**[V]** `check_resolution_write_atomicity`: **0**, checked after the
kill, after the resume's batch 1, and in a final direct check. Clean
throughout.

### d. Trigger

**[V]** `trg_resolved_no_unresolve` present, unchanged, did not fire —
confirmed via `sqlite_master` and zero caught exceptions across all
writes (92 + 378).

### e. Post-write fingerprint

Not captured as a full table here — this run is incomplete (1/10
batches) and the intent was to capture a post-completion fingerprint once
the full 5,000-row run finished. What is confirmed: `evidence_clob`
203→673 (+470, exact match to combined killed-run + resume-batch-1
writes), `check_resolution_write_atomicity` = 0 (unchanged), no count
decreases observed anywhere in the spot-checks above. A full comparative
table against the `1edb78f` pre-write capture should be produced once
this tranche actually completes.

### f. Test suite

**Not re-run this session** — the run is incomplete and paused; per §D's
own framing (the live reconciliation numbers are expected to keep moving
with every real write), re-running now would only capture an intermediate
state 1/10 of the way through tranche 2, which is not a meaningful
checkpoint to reconcile against. Deferred to whenever this tranche is
next resumed and completed.

### g. Pacing and runtime

**[V]** Batch 1 average pace: **0.163s/call**, comfortably under the
0.25s target and the 1.0s/call abort threshold — consistent with tranche
1's observed 0.13–0.23s/call range. Batch 1 wall time: 206.4s (~3.4
minutes) for 500 calls at 0.25s sleep + real API round-trip — in line
with the ~21-minute-for-10-batches projection (206.4s × 10 ≈ 2,064s ≈
34.4 minutes if every batch behaved identically, somewhat above the ~21
minute estimate; the original estimate may have understated per-call
overhead beyond the 0.25s sleep itself, similar to tranche 1's own
resume taking 120.4s against a ~75s estimate). Worth revisiting the
36-hour full-sweep projection with this more complete per-batch timing
data once tranche 2 actually completes.

---

## What this means for next steps

Not decided here, per the task's own scope (documentation of what
happened, not further action). Two things are true simultaneously and
both need to be held: **the write path and the kill-resume safety
guarantee both worked correctly** (zero double-writes, zero data damage,
zero trigger fires, atomicity clean throughout) — and **the driver's own
monitoring logic has two named gaps** that should be fixed before this
tranche is resumed or the full sweep is attempted, so a future restart
does not need to redundantly re-litigate already-settled markets and so
a benign no-op-match pattern does not repeatedly halt a longer run the
way it did here.
