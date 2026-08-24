# 2026-08-24 — sweep segment 3: launch (write in progress, verification pending)

Pre-registration: `2026-08-21-discovery-gap-closure-prereg.md` (23630ee,
as amended). Segment 2: `2026-08-23-post-segment2-status.md`. Survey:
`2026-08-23-sweep-inhibitor-survey.md` (752cdbd). Safety fixes:
`2026-08-23-sweep-safety-fixes.md` (4b3f69e), first-repo `e4ddb67` /
`72e7337`.

**Filename date note:** the launch prompt referenced
`2026-08-23-sweep-segment3.md` and described "today's maintenance" as
06:00:01–15:43:48 — that is 2026-08-23's run. This session's actual clock
is 2026-08-24 (2026-08-24's maintenance already ran and finished
06:00:01–09:48:55, hours before this session started at 17:08). The
prompt appears to have been drafted a day before this task was executed.
Filed under today's actual date for consistency with the rest of the
corpus; the drift is flagged here rather than silently absorbed, and it
materially changes the runway arithmetic below (see there).

**STATUS: segment 3 launched cleanly at 2026-08-24T17:16:01Z, detached,
running. Batch 1/186 verified healthy (this document). The segment needs
~10.75h to finish — everything under §ABORT CONDITIONS / §WATCH FOR /
§POST-WRITE VERIFICATION in the launch prompt cannot be answered yet and
is marked PENDING below, not fabricated. A follow-up check after the
segment finishes (projected ≈2026-08-25T03:57Z) or aborts is required to
close this out, the same two-phase pattern segment 2 used
(`2026-08-22-sweep-segment1.md`/launch → `2026-08-23-post-segment2-status.md`/verification).**

---

## Before the write

### 1. Terminal signal wired — confirmed, not merely available

`data/characterizations/sweep_common/sweep_terminal_signal.py` existed
but was imported by nothing (confirmed via the safety-fixes doc's own
grep, zero hits, and independently re-confirmed here: `grep -rn
"sweep_terminal_signal" data/characterizations/sweep_segment2/` →
nothing). `segment3_write.py` now imports
`write_terminal_marker`/`send_telegram_terminal` and calls both at three
exit points, matching the module's own documented `CALL PATTERN`
exactly:

- **Normal/abort/maintenance-stop completion** — a single `_emit_terminal()`
  call right after the batch loop, using the same `status` computation
  segment2_write.py already had (`COMPLETE` / `ABORTED` /
  `MAINTENANCE-STOPPED` / `STOPPED (incomplete)`).
- **Unhandled exception** — a new top-level `try/except Exception`
  wrapping the entire batch loop (segment2_write.py had no such wrapper
  at all), writing `status="EXCEPTION"` with the exception type/message
  as `reason`, then re-raising — the marker is in addition to the crash,
  not a replacement for it, per the module's own guarantee language.

Verified by direct import test (not just reading the diff): loaded
`segment3_write.py` as a module and confirmed
`write_terminal_marker.__module__` / `send_telegram_terminal.__module__`
both resolve to `sweep_terminal_signal`, and that
`TERMINAL_MARKER_PATH` (`data/checkpoints/segment3_terminal_marker.json`)
does not collide with the daily-maintenance hold's checkpoint glob
(`segment*_checkpoint.json`) — the marker filename does not end in
`_checkpoint.json`, so it cannot be misread as a fresh checkpoint by Fix
1's recency check.

**What changed in the driver, stated exactly, per the task's own
instruction:** `segment3_write.py` is otherwise byte-for-byte structurally
identical to `segment2_write.py` — same batching, pacing, abort
conditions, checkpoint format, imports from `tranche2_write.py`. The only
functional addition is the terminal-signal wiring described above (one
import line, one `TERMINAL_MARKER_PATH` constant, one `_emit_terminal()`
helper, one `try/except Exception` wrapper, two call sites). Path
constants were renamed segment2→segment3; no other logic line differs.

### 2. Hold active — confirmed by reading the wired code, not asserted

Read `scripts/daily_maintenance.py` directly (not inferred from the prior
doc): `_sweep_recently_active()` (line 96) is called at line 433, inside
`main()`'s executed step sequence, immediately before the "Backfill
market dates" step's `run_step()` call (line 440) — it is in the
scheduled path, not a dead helper. `SWEEP_CHECKPOINT_GLOB` (line 48) is
`data/checkpoints/segment*_checkpoint.json`, which matches
`segment3_checkpoint.json` (confirmed via the glob pattern directly — no
segment-number allowlist, any `segmentN_checkpoint.json` qualifies) and
reads each checkpoint's own `last_updated_utc` field, which
`segment3_write.py`'s `write_checkpoint()` writes on every batch
(confirmed: batch 1's checkpoint has
`"last_updated_utc": "2026-08-24T17:19:40Z"`). If segment 3 is still
running at a future 06:00 fire, this step will see a checkpoint under
1800s old and skip — this is fix 1's first live exercise if it fires (see
§WATCH FOR item d, PENDING).

### 3. Fresh backup — hard gate, passed

`backups/markets_20260824_170855.db`, 16711.9 MB. Script output:
`[BACKUP] Verifying integrity of ...` → `[OK] Backup created`. The
backup script (`scripts/backup_database.py`) runs `PRAGMA
integrity_check` against the backup file itself as part of its own
process (confirmed by reading the script: line 47) — this is not a
same-process assumption, the check ran against the actual backup
artifact. WAL-safe: the script performs an online backup (sqlite3 backup
API) against the live, WAL-mode DB; no service was stopped.

### 4. Fresh fingerprint — committed

`data/characterizations/sweep_segment3/segment3_prewrite_fingerprint_20260824T171210Z.json`,
committed in `8bb0f2b`. Full field snapshot (traders, trades, positions,
markets, resolved_markets, geo/elec gap-clean, evidence_source
breakdown, atomicity, SS C population raw/post-carveout/post-exclusion)
captured before any write this session.

### 5. Runway arithmetic — corrected, not "tighter than yesterday"

**The launch prompt's premise does not hold, checked directly rather than
assumed.** Current time when computed: `2026-08-24T17:12:10Z`. Next
`06:00:00Z` fire: `2026-08-25T06:00:00Z`. Runway: **46,069.4s = 12.797h**
— this is **longer than segment 2's 9.04h runway, not tighter**, by
about 3.76h. The reason: 2026-08-24's own daily_maintenance run had
already started and finished (`06:00:01Z`–`09:48:55Z`, per
`logs/daily_maintenance.log`) hours before this session began at 17:08Z
— the "15:43:48" finish time and "today's maintenance" framing in the
prompt describe 2026-08-23's run, one calendar day earlier than this
session's actual clock. Sized on the measured runway, not the assumed
shape, per the prompt's own fallback instruction ("size down rather than
assuming last night's shape" — here the correction runs the other
direction: size is *not* constrained tighter than segment 2, so segment 3
is allowed to be larger).

```
runway_seconds        = 46,069.4   (12.797h)
target_margin_seconds =  7,200     (2h, same convention as segment 2)
budget_seconds         = 38,869.4
measured_rate_s_per_call = 0.416   (tranche 2's measured figure, per the amended prereg)
budget_calls           = 93,436.1
batches_floor (÷500)   = 186
segment_size_markets   = 93,000
projected_processing_s = 38,688.0  (10.747h)
projected_finish_utc   = 2026-08-25T03:56:58Z
actual_margin_hours    = 2.05      (vs. next fire, matching segment 2's own 2.051h margin almost exactly)
```

Full arithmetic committed in the fingerprint JSON above, not just this
prose.

---

## The run

### Candidate population

`data/characterizations/sweep_segment3/segment3_materialize.py`
(committed `8bb0f2b`), live query (not derived from segment 1's original
103,000-row materialized list — that list's un-walked tail, 21,292 rows,
flows back into this live query naturally since it was never
list-excluded):

```
SS C predicate population (raw, unexcluded):  448,876
combo/parlay cohort within raw population:      15,549   (in-SQL exclusion this time, not a post-filter)
post-carveout population:                      433,327
already-processed exclusion (union, 0 overlap): 71,500   (tranche2 5,000 + segment1-walked 6,000 + segment2 60,500)
FINAL candidate population:                    432,009
```

**Against the amended ~427,000 figure: +5,009 (+1.2%).** Consistent with
organic new-market arrival in the ~1.5 days since that figure was set
(`2026-08-23-post-segment2-status.md`), not a predicate or exclusion
defect — the combo/parlay count itself also grew (15,208/15,427 at
segment 2's materialization time → 15,549 now), the same direction and
roughly the same relative magnitude, which is the expected signature of
organic arrival rather than a logic error.

**One caveat, named rather than silently absorbed:** tranche 1's ~123
still-unresolved markets (open/indeterminate/no_clob_response, of 326
walked) are **not** list-excluded here — tranche 1 queried live with a
category-scoped predicate (Elections/Geopolitics + trade-joined +
gap-clean) that is now stale against the current `resolved` state, and no
fixed id enumeration survives from that run to exclude by. These ~123
markets may reappear in segment 3's 93,000-row list and get reprocessed.
This is accepted as harmless, not ignored: `mark_market_resolved()`'s own
`resolved=0` selection guard makes a re-attempt idempotent (confirmed
today, batch 1: 34 of 496 resolved-classification rows returned
`"no-op: same-rank value matches existing"`, a member of
`ACCEPTED_REASONS`, not a rejection) — worst case a few dozen redundant
CLOB calls out of 93,000, not a correctness risk.

### Sizing

Batches: **186** (185 full batches of 500 + one exact 500, since
93,000/500 = 186.0 exactly). Projected wall time: **38,688s ≈ 10.75h**,
finishing ≈`2026-08-25T03:57Z`, ≈2.05h before the next 06:00 fire.

### Launch

```
nohup python3 -u data/characterizations/sweep_segment3/segment3_write.py \
  > logs/discovery_gap_sweep_segment3_20260824T171601Z.log 2>&1 &
disown
```

Confirmed detached: `ps -o pid,ppid,pgid,sid,stat` shows PID 28660,
**PPID=1** (reparented to init), independent of the launching shell's
session — will survive this Claude Code session ending, unlike segment
2's `bkl2qudts` monitor task which died with its launching session and
left only `[killed]`. This process is a plain detached OS process, not a
harness-tracked background task, and is not subject to that failure mode.

**0.25s pacing, 500-row batches, atomic checkpoint per batch to
`data/checkpoints/segment3_checkpoint.json`** — all confirmed live in
batch 1's actual checkpoint (see below).

### First-batch health check (completed this session)

```
Batch 1/186 done: fresh=500 skipped=0
  tally={'resolved': 496, 'open': 2, 'indeterminate': 2, 'no_clob_response': 0}
  batch_indet_rate=0.4% [EVALUATED]  cum_indet_rate=0.4% [EVALUATED]
  avg_pace=0.178s/call  atomicity=0
Checkpoint: batches_completed=1, cumulative_processed=500,
  cumulative_accepted=462, cumulative_rejected=34,
  cumulative_reasons={'no-op: same-rank value matches existing': 34, 'written': 462}
  last_updated_utc=2026-08-24T17:19:40Z
```

0.4% indeterminate rate is inside segment 2's clean 0.0–1.6% band (see
§WATCH FOR item a below — one data point, not yet a segment-level
finding). Atomicity 0. Pace 0.178s/call this batch — faster than the
0.416s planning figure, which was a multi-batch average; not itself a
concern (no abort condition compares single-batch pace to 0.416s, only
the >1.0s/call sustained-degradation threshold). Batch 2 was confirmed
running (`pgrep`) immediately after.

---

## Abort conditions (live, per amended §C, unchanged) — PENDING

Unchanged from segment 2's driver: backup gate, batch/cumulative
indeterminate-rate thresholds (10%/20%, n=100 floor each), trigger fire,
atomicity non-zero, unpredicted-rejection rate, pacing degradation, plus
the segment-specific 30-min-before-06:00 clean stop. **None can be
evaluated as "did it fire" until the segment finishes or aborts** — this
section is a specification confirmation (the code is unchanged from
segment 2's, itself already verified against this table), not a report of
outcomes. Outcomes: PENDING.

## Watch for — PENDING (one data point so far, not a verdict)

- **a. Indeterminate rate vs. segment 2's clean band (0.0–1.6%).** Batch
  1: 0.4%, inside the band. Cumulative segment verdict: PENDING (186
  batches to go).
- **b. Cross-rank overwrite — zero across 69,998 accepted writes so far.**
  Not traceable until the run produces its own accepted-write log; batch
  1's 462 accepted writes were not individually inspected for this
  branch this session. PENDING — check at completion via the same
  `grep -c "outranks existing"` method the prior status docs used.
- **c. A third contiguous dead cohort.** PENDING — requires the full
  per-batch `no_clob_response` history across all 186 batches; batch 1
  had 0.
- **d. Whether the hold actually fires if the segment is still running at
  06:00.** PENDING and material: segment 3 is projected to finish
  ≈03:57Z, ~2h before the fire, so under normal operation this may again
  go unexercised, the same outcome segment 2 had. If a batch runs long
  and the segment is still active at 06:00, `_sweep_recently_active()`
  will see this segment's checkpoint (confirmed wired, §2 above) and this
  would be fix 1's first live exercise — to be reported explicitly if it
  happens, not silently absorbed into "maintenance ran fine."

## Post-write verification — PENDING, all items

a–i (evidence_source=clob delta, branch-firing counts,
`check_resolution_write_atomicity`, `trg_resolved_no_unresolve`,
post-write fingerprint diff, `run_tests.py` with T2f traced, observed
pacing / remaining-segments re-derivation, terminal marker contents,
completion-checkpoint commit) **all require the segment to finish or
abort first.** None are answered here — a follow-up check after
`2026-08-25T03:57Z` (or after an abort, whichever is first) is required
to close this document out, matching the launch/verification split
segment 2 used.

---

## Constraints — honored

Only segment 3 was launched (no segment 4 scoped or started).
`daily_maintenance.py` and `mark_market_resolved()` were read, not
modified — the only production-directory file touched was reading
`scripts/daily_maintenance.py` to confirm the hold's wiring; no edits.
`daily_maintenance` itself was not run. All new/changed files are under
`data/characterizations/sweep_segment3/`, `data/checkpoints/`, and this
decision doc.

## What's next

This session is not staying open ~10.75h to watch the run complete.
Segment 3 is a fully detached OS process (PPID=1) and will run to
completion, abort, or the 06:00 maintenance-window stop on its own. A
follow-up check (this session resumed, or a fresh one, after
≈2026-08-25T03:57Z) must read `logs/discovery_gap_sweep_segment3_20260824T171601Z.log`,
`data/checkpoints/segment3_checkpoint.json`, and
`data/checkpoints/segment3_terminal_marker.json` to complete every PENDING
item above before segment 4 (if any) is scoped.
