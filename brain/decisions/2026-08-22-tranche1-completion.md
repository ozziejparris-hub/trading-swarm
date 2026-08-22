# 2026-08-22 — Tranche 1 Completion

## VERDICT: TRANCHE 1 COMPLETE. 203 / 98 / 16 — EXACT MATCH TO THE KNOWN ANSWER. ALL FOUR PROCEED CRITERIA MET.

Tranche 1 (the 317-market Q2 census population,
`2026-08-21-discovery-gap-closure-prereg.md` §C) is finished across two
script invocations: `tranche1_write.py` (16 writes, paused at row 25/317
on the pre-amendment abort condition, `2026-08-22-tranche1-execution.md`,
`4436119`) and `tranche1_resume.py` (this session, 301 remaining rows,
zero aborts, complete). **Combined, deduplicated result: 203 resolved, 98
open, 16 no-CLOB-response, 0 true indeterminate — an exact match to the
independently-established 2026-08-20 sizing census (203/98/16), zero
drift.** This is tranche 1's whole purpose (§I falsification condition 1)
and it was met cleanly.

All claims tagged **[V]** verified (ran/read it myself) or **[I]** inferred.

---

## 1. Batch/cumulative fix and its practical consequence

**[V]** `tranche1_resume.py` (committed `first-repo` `316172d`) separates
the two counters per the amended §C (`7614ed7`):

- **Condition 2 (batch, 10%, n≥100 floor): never evaluable for tranche
  1, and this run does not attempt to evaluate it.** §C defines condition
  2 as "rolling over the **last completed batch**," and the standard
  batch size is 500 markets. Tranche 1's total population (317) is
  smaller than one batch — it will never produce a completed 500-row
  batch, so there is never a "last completed batch" for condition 2 to
  apply to. The driver logs this explicitly at every checkpoint
  (`[condition 2 (batch) N/A -- tranche 1 < 500-row batch size, never
  completes a batch]`) rather than silently omitting it.
- **Condition 3 (cumulative, 20%, n≥100 floor): the sole live guard
  protecting this run.** Seeded with run 1's tally (25 processed: 16
  resolved, 6 open, 0 indeterminate, 3 no_clob_response) before processing
  any new row, since condition 3 is defined over "the whole sweep so far"
  — i.e. the whole tranche-1 execution across both script invocations, not
  just this one. The floor (cumulative n≥100) was crossed at combined row
  100/326 (this run's row 75/301); condition 3 became live and was
  evaluated at every checkpoint from there on. It never came close to
  firing — the cumulative rate ranged 12.0% (just above floor, n=50,
  below the n=100 floor so not yet evaluated) down to a stable 5.0–6.0%
  band once past the floor, ending at 5.8% (19/326) — consistent with the
  ~5% baseline throughout.

**So: which condition actually protected this run?** Condition 3 alone.
Condition 2 was structurally inapplicable to tranche 1 from the start —
not a gap in this run's coverage, a property of tranche 1 being smaller
than one batch. This distinction matters for tranche 2 (5,000 candidates,
10 batches of 500 per §C): there, condition 2 *will* become evaluable
repeatedly, batch by batch, and must be tracked as a genuinely separate,
resetting-per-batch counter — not implicitly covered by condition 3
continuing to hold.

---

## 2. The resume

**[V] Scope confirmed, not assumed.** Re-derived the tranche-1 population
live at resume time via §3's exact predicate: **301**, matching
`317 − 16 (already resolved) = 301` exactly. The 16 already-written
markets had left the candidate set by construction (their
`resolution_date`/`end_date` are no longer both NULL), confirmed directly
rather than inferred from the write count alone.

**[V]** Used the unmodified `_get_connection`, `_fetch_by_clob`,
`_extract_clob_resolution` (`scripts/backfill_market_dates.py`) and
`mark_market_resolved` (`monitoring/resolution_writer.py`) — same as
`tranche1_write.py`, not reimplemented. `backfill_market_dates.py` was not
modified; its assertion-branch commit gap (conditional on a usable
end-date being present) remains worked around defensively via an
unconditional `conn.commit()` in the driver, exactly as before.

**[V]** Pacing: 0.25s/call. 301 calls, observed directly (foreground, not
detached). Elapsed: 120.4s (~2.0 minutes — somewhat longer than the ~75s
estimate, consistent with real per-call CLOB round-trip time on top of the
0.25s sleep; recent-pace readings stayed 0.13–0.23s/call throughout,
comfortably under the 1.0s/call abort threshold).

---

## 3. Live abort-condition monitoring — nothing fired

**[V]** Checked every 25 rows (12 checkpoints across the run). At no
point did any condition fire:

- Trigger (`trg_resolved_no_unresolve`): zero exceptions caught, zero
  fires.
- `check_resolution_write_atomicity`: **0** at every checkpoint and at
  the end.
- Condition 3 (cumulative, once n≥100): stayed in a 5.0–9.0% band from
  the point the floor was crossed onward — never approached 20%.
- Non-`"written"` reasons: **zero** at every checkpoint. All 187 new
  accepted writes this run took `reason="written"` — the only branch
  structurally reachable for this population (§1 of
  `2026-08-22-tranche1-execution.md`).
- Pacing: recent-pace never exceeded 0.23s/call.

---

## 4. Proceed criteria — individually

| # | Criterion | Status |
|---|---|---|
| 1 | Total resolved across both partial runs within a small tolerance of the freshly-derived expected 203 | **MET.** 203 resolved, exactly — not "within tolerance of," an exact match. |
| 2 | Final indeterminate rate consistent with the ~5% baseline (expected ~16) | **MET.** 16 no-CLOB-response, 0 true indeterminate — 16/317 = 5.05%, exactly the established baseline rate, and the same absolute count (16) as the 08-20 sizing census. |
| 3 | Zero trigger fires | **MET.** Confirmed zero across both runs (16 + 187 writes). |
| 4 | Zero unpredicted rejection patterns | **MET.** All 203 accepted writes across both runs: `reason="written"`, zero rejected. |

**All four criteria met.** Nothing blocks tranche 2 on tranche-1's own
merits. (Whether to actually run tranche 2 is a separate decision, not
made here — this task's scope was tranche 1's completion only, per its
own constraints below.)

---

## 5. Post-write verification

### a. Evidence-source delta and sample rows

**[V]** `resolution_evidence_source='clob'`: **16 → 203**, delta **+187**
— exactly this run's new accepted-write count (`accepted` this invocation
= 187, per the driver's own standalone tally, see §6 methodology note).
Five newly-written rows from this run, sampled directly:

| market_id (truncated) | resolved | winning_outcome | resolution_date | resolution_recorded_at | evidence_source | evidence_detail |
|---|---|---|---|---|---|---|
| 0x1c711cdf... | 1 | No | 2026-08-22 14:29:28.332525 | 2026-08-22 14:29:28.332525 | clob | token.winner |
| 0x1d2b3415... | 1 | No | 2026-08-22 14:29:28.734850 | 2026-08-22 14:29:28.734850 | clob | token.winner |
| 0x1e3b73f9... | 1 | No | 2026-08-22 14:29:29.116823 | 2026-08-22 14:29:29.116823 | clob | token.winner |
| 0x1f78a023... | 1 | No | 2026-08-22 14:29:29.499904 | 2026-08-22 14:29:29.499904 | clob | token.winner |
| 0x2064296b... | 1 | No | 2026-08-22 14:29:29.888458 | 2026-08-22 14:29:29.888458 | clob | token.winner |

`resolution_date == resolution_recorded_at` throughout, correct per
`mark_market_resolved`'s 3-tier fallback (no prior value existed for any
of these, `resolution_event_time=None` passed throughout — falls to
write-time).

### b. Branch-firing counts, across this run and combined

**[V] This run (187 new accepted writes): 187 `"written"`, 0 other.**
**Combined across both runs (203 total accepted writes): 203
`"written"`, 0 other.** Zero untagged-legacy-improvement, zero cross-rank
overwrite, zero same-rank match, zero same-rank disagreement, in either
run or combined — structurally guaranteed by the population's own
predicate (§1 of `2026-08-22-tranche1-execution.md`), not merely
observed.

### c. Atomicity

**[V]** `check_resolution_write_atomicity`: **0**, checked at every
25-row checkpoint throughout this run and in a fresh post-write check.

### d. Trigger

**[V]** `trg_resolved_no_unresolve` present, unchanged, did not fire —
zero exceptions across all 203 writes (16 + 187).

### e. Post-write fingerprint vs. `a2b4b82`

| Metric | Pre-write (`a2b4b82`, 12:33) | Post-completion (now) | Delta | Attributable to tranche 1? |
|---|---|---|---|---|
| traders | 171,540 | 171,540 | 0 | n/a |
| trades | 11,663,141 | 11,663,142 | +1 | No — background monitoring (unchanged since the first partial run's check) |
| positions | 7,689,429 | 7,692,507 | +3,078 | No — background activity, all of it had already occurred by the first partial run's post-write check (`2026-08-22-tranche1-execution.md` §5e); zero further movement since |
| markets | 745,066 | 745,067 | +1 | No — background monitoring |
| resolved markets | 224,981 | 225,184 | **+203** | **Yes — exact match to the combined resolved count** |
| Geo/Elec resolved+gap-clean | 10,589 | 10,792 | **+203** | **Yes — exact match** |
| `resolution_evidence_source='clob'` | 0 | 203 | **+203** | **Yes — exact match** |
| `resolution_evidence_source='gamma'` | 12 | 12 | 0 | n/a, untouched |
| `resolution_evidence_source='hydration_fill'` | 1 | 1 | 0 | n/a, untouched |
| `check_resolution_write_atomicity` | 0 | 0 | 0 | Clean throughout |
| Q2/tranche-1 candidate population | 317 | 114 | **-203** | **Yes — exact match: 114 = 98 open + 16 no_clob_response, the markets that did not resolve** |

**Every resolution-specific delta is exactly ±203 — no more, no less.**
No count decrease anywhere. Non-resolution baseline counts are unchanged
from the first partial run's own post-write check (§5e of
`2026-08-22-tranche1-execution.md`) — meaning all of that background
growth happened during the ~1h42m gap disclosed there, and nothing further
moved during this resume.

### f. Test suite

**[V]** `run_tests.py` re-run after completion. **File-level baseline
unchanged: 16 files, 15 passed, 1 failed
(`test_backtest_window_population.py`, 19/24)** — matches the standing
baseline exactly, no new file-level failure.

**T2f's old-method reconciliation total tracked every write across all
three checkpoints, exactly:**

| Checkpoint | T2d (visible bucket) | T2f old-method total | Delta from prior |
|---|---|---|---|
| Before any tranche-1 write | Expected 573, got 582 | 6070 | — |
| After run 1 (16 writes) | Expected 573, got 585 | 6086 | **+16**, exact match to run 1's write count |
| After run 2 / this completion (187 more writes) | Expected 573, got 639 | 6273 | **+187**, exact match to run 2's write count |

**6086 + 187 = 6273 — exact.** Across both tranche-1 writes combined, the
old-method total moved by +203 from its pre-tranche-1 baseline (6070 →
6273), precisely matching the combined 203 resolved-market count. This is
the third consecutive confirmation (pre-write, after-run-1, after-run-2)
that this test's live-reconciliation movement is fully attributable to
tranche 1's writes and nothing else — not accepted as "still failing,
same as before" at any checkpoint, traced and reconciled each time, per
§D of the pre-registration.

### g. Reconciliation against the known answer — tranche 1's whole purpose

**[V] Exact match.** 203 resolved / 98 open / 16 indeterminate (no-CLOB-
response) against the 2026-08-20 sizing census's independently-established
203 / 98 / 16 — not "within tolerance," identical on every figure. Two
independent verification paths confirm this, not one:

1. **Direct SQL against the live DB** (not the script's own printed
   tally): `resolution_evidence_source='clob'` = 203; current tranche-1
   candidate population = 114 = 317 − 203.
2. **Deduplicated script-level accounting**: run 1's 16 distinct resolves
   (never revisited, since resolved markets leave the candidate set) plus
   run 2's own complete, single-pass snapshot of all 301 remaining
   candidates (187 resolved / 98 open / 0 indeterminate / 16
   no_clob_response) = 203 / 98 / 16 / 0 combined.

**A methodology note, disclosed rather than glossed over:** the driver's
own printed "combined" tally (seeded with run 1's raw counts, then summed
against run 2's running totals) over-reports `open` (104, not 98) and
`no_clob_response` (19, not 16) by exactly 9 — the count of markets that
were classified `open`/`no_clob_response` in run 1 and were then, by
design (§C's resumability mechanism), correctly re-queried and
re-classified in run 2. Both classification *attempts* for those 9
markets are real and legitimately logged, but summing both counts them
twice in a "total classification" sense. The correct combined figure
supersedes the earlier, not-yet-resolved classification with the later
one — which is exactly what run 2's own standalone tally already is,
since it covers 100% of the markets that remained unresolved after run 1.
**This is a reporting artifact in how the two runs' printed tallies were
naively combined, not a data-integrity issue** — no market was written to
twice, no write was lost, and every number reported above as the
"combined, deduplicated" figure was independently cross-checked directly
against the live DB (method 1) before being trusted.

---

## 6. What this closes out, and what remains open

Tranche 1 is done, cleanly, with the exact expected answer. Per §C, this
clears tranche 1's own gate for proceeding to tranche 2 — all four
criteria met (§4). **Tranche 2 was explicitly out of scope for this task
and was not started; it remains a separate decision.** The batch/
cumulative distinction clarified here (§1) will matter directly once
tranche 2 runs, since that population (5,000 candidates, 10×500-row
batches) is large enough for condition 2 to actually become live and
evaluable, unlike tranche 1.

Named, not fixed, per the pre-registration's own amendment
(`7614ed7`) and unchanged by this completion: the harness's earlier
batch/cumulative conflation (now fixed in `tranche1_resume.py`, but
`tranche1_write.py` itself is left as-is, a record of what actually ran)
and `backfill_market_dates.py`'s own conditional-commit gap in its
assertion branch (still worked around defensively in the driver, that
file still not modified).
