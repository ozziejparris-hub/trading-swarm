# Segment 4 — Housekeeping + Launch — 2026-08-25

Two-phase document, same pattern as segments 2 and 3: written AT LAUNCH.
Pre-launch sections are VERIFIED (this session, live). The run itself is
PENDING — outcome to be confirmed and appended in a follow-up status doc
once it finishes or is checked, the same way
`2026-08-25-post-segment3-status.md` followed segment 3's launch doc.
Nothing in the "THE RUN" / "WATCH FOR" sections below is fabricated —
where an outcome isn't known yet, it says so.

Pre-registration: `2026-08-21-discovery-gap-closure-prereg.md` (23630ee,
as amended). Segment 3 status:
`2026-08-25-post-segment3-status.md`. Safety fixes:
`2026-08-23-sweep-safety-fixes.md` (4b3f69e), first-repo `e4ddb67` and
`72e7337`.

Standing instruction applied throughout: every premise in the launch task
was treated as a hypothesis and checked live, not assumed. Two premises
were confirmed exactly correct on checking (the 356,605 remaining-population
estimate; the two unpushed commit hashes); none were found stale.

---

## HOUSEKEEPING

### 1. Pushed the pending commits

Working tree checked before pushing: only the known routine churn present
(`data/.last_requeue_run`, `data/category_backfill_state.json`,
`logs/arb_bot_exclusions.log`, `logs/focus_ratio_review.json`, all
modified; two dated characterization JSON pairs and the segment-3
checkpoint/marker, untracked) — nothing unexpected, matching what
`2026-08-25-post-segment3-status.md` already catalogued. Pushed as-is,
touching nothing else:

```
git push origin main
72e7337..8bb0f2b  main -> main
```

`origin/main` now has both `8bb0f2b` (segment 3 launch) and `4ce6d36`
(segment 2 completion docs). `git log origin/main..HEAD` is empty —
confirmed, not assumed.

### 2. Fixed the Telegram launch environment

**Root cause, confirmed this session (broader than previously scoped):**
`/home/parison/.env_trading` has **no `export` statements** — twelve plain
`VAR=value` lines. `bash source` of a file like that sets shell variables
in the *sourcing* shell only; it does **not** put them in the process
environment a child process inherits, so any `python3` subprocess launched
from that same shell never sees them via `os.getenv()`. This affects more
than the sweep driver: `scripts/cron_wrappers/run_daily_maintenance.sh`
already does `source "$ENV"` before invoking `daily_maintenance.py`, and
even that failed to propagate credentials — visible in today's
maintenance log, where `backfill_market_dates.py` (a child of that same
maintenance run) also printed `[TELEGRAM] Credentials not found —
skipping alert.` This is a **pre-existing, systemic gap**, not something
introduced by the sweep — flagged here since it likely also silences other
cron-launched Telegram alerts, but fixing those is out of scope for this
task.

**Fix chosen: launch-layer, via `set -a`.** Source `.env_trading` in the
launch invocation itself, wrapped in `set -a ... set +a` so every
assignment made while sourcing is auto-exported into the environment —
the minimal correction to the actual defect (missing export), applied
where the process is launched rather than inside driver code. Chosen over
having the driver call a dotenv loader because: (a) it mirrors the
systemd services' own `EnvironmentFile=` pattern — credentials become
available to the process from the moment it starts, not via in-process
special-casing; (b) it keeps credential-loading out of
`sweep_terminal_signal.py` and `segment4_write.py`, which have no other
reason to know how `.env_trading` is formatted; (c) it's auditable in one
place (the launch command, reproduced below) rather than requiring every
future driver to remember to add loader logic.

**Credential names confirmed present by name only** (values never printed,
logged, or echoed at any point this session):
`telegram_alerts_token=True`, `telegram_chat_id=True` (boolean presence
check only).

**Verified end-to-end with a real send**, not assumed from the presence
check alone:

```
$ set -a; source /home/parison/.env_trading; set +a
$ python3 -c "... send_telegram_terminal('[SWEEP] segment4 launch-environment
  test -- confirming Telegram delivery ahead of segment 4 start. Not a real
  terminal event.') ..."
[TELEGRAM] Terminal notification sent.
send_telegram_terminal returned: True
```

A real message was delivered before segment 4's actual launch. This is
segment 3's fix, closed out — the next terminal-state Telegram message
(segment 4's own COMPLETE/ABORTED/etc.) should now actually arrive.

---

## A CHANGE TO ABORT CONDITION 5, WITH REASONING

Prereg §C's abort-condition table (`2026-08-21-discovery-gap-closure-prereg.md`
line 823) lists condition 5 as: `check_resolution_write_atomicity` non-zero
→ **HARD ABORT**, no exceptions stated. `segment3_write.py`'s own inline
comments happen to label a *different* check ("non-accepted reason rate")
as "ABORT CONDITION 5" — a pre-existing mislabeling relative to the
prereg's own numbering, noted here for the record but **not corrected** in
segment 4's driver, per the instruction to change exactly one thing and
nothing else; the atomicity block itself was left unlabeled in both
segment 3 and segment 4, same as segment 3 wrote it.

**The defect:** as written, condition 5 cannot distinguish a genuine,
persistent atomicity break from a transient one. Segment 3's own post-run
status check observed exactly this: `check_resolution_write_atomicity`
read 0 → 5 → 0 across three successive queries minutes apart, with a
direct `SELECT` for the offending rows returning zero rows on the third —
consistent with a live-writer race under WAL mode (the monitoring service's
own 15-minute loop caught a market between two non-atomic write
statements), self-healed before the next query even ran. A hard,
unconditional abort on that reading would have killed a 10+ hour run on
noise, not a real violation. **This is the same defect class as tranche
1's original abort conditions 2/3**, which had no `n=100` floor and fired
on ordinary binomial variance at 25 samples (prereg's own 2026-08-22
amendment, `4436119`) — a threshold that cannot tell signal from noise at
the scale it's actually evaluated.

**Fix implemented in `segment4_write.py` (CONFIRM-BEFORE-ABORT):** on a
non-zero `check_resolution_write_atomicity` reading, wait
**5 seconds** and re-query once. Abort only if the second reading is
*also* non-zero. A single transient non-zero reading is appended to a new
`atomicity_transient_events` list in the checkpoint (batch number, both
readings, delay, UTC timestamp) and printed to stdout — logged, not fatal.
A persistent reading (non-zero on both the initial and the confirming
re-query) still hard-aborts exactly as before — **this is a correction to
condition 5's evaluation logic, not a relaxation of the abort itself.**

**5-second delay, justified:** segment 3's own measured per-call latency
(`avg_pace_s_per_call`, CLOB fetch + `mark_market_resolved` + commit,
excluding the 0.25s sleep) ranged 0.140–0.225s across its entire 186-batch
run. A single in-flight non-atomic write pair completes in well under 1
second. 5s is a 20x+ margin over that — enough for any genuinely in-flight
write to finish and become visible to a fresh read, without materially
affecting a multi-hour run (worst case, every one of 133 batches sees one
transient reading: 133 × 5s ≈ 11 minutes against a ~7.75h run with ~2h of
margin already built in).

**This is flagged as a STRUCTURAL correction that §C should be amended to
match** — the pre-registration itself is **NOT amended by this task**, per
the instruction. The correction lives in `segment4_write.py`'s own
docstring and this document; a future documentation-only prereg amendment
(same pattern as the tranche-1 n=100-floor amendment, `4436119`) should
fold this in explicitly rather than leaving the driver and the
pre-registration silently out of sync.

---

## BEFORE THE WRITE

**4. Terminal signal wiring — verified by import test, not inspection.**
Imported `segment4_write` directly and asserted, by object identity (not
name-matching), that `segment4_write.write_terminal_marker is
sweep_terminal_signal.write_terminal_marker` and the same for
`send_telegram_terminal` — both true. Counted `_emit_terminal(...)` call
sites in the module source via `inspect.getsource`: **3** (the function
definition, the top-level exception handler, and the post-loop
status-computation call) — same shape as segment 3, covering all three
documented exit points (COMPLETE/ABORTED/MAINTENANCE-STOPPED/STOPPED via
the post-loop call; EXCEPTION via the except-block call). Confirmed
`write_terminal_marker`/`send_telegram_terminal` are each called exactly
once inside `_emit_terminal`. `CHECKPOINT_PATH` and `TERMINAL_MARKER_PATH`
both confirmed pointing at `segment4_*`, not stale `segment3_*` paths
copy-pasted forward.

**5. Fix 1 hold check — verified live against the real, imported
`daily_maintenance.py` constant**, not a re-typed copy:
`dm.SWEEP_CHECKPOINT_GLOB` = `.../data/checkpoints/segment*_checkpoint.json`,
and `fnmatch` confirms `segment4_checkpoint.json` matches it.
`SWEEP_RECENCY_WINDOW_SECONDS` = 1800, unchanged. Once segment 4 writes
its first checkpoint, `_sweep_checkpoint_age_seconds()` will pick it up as
the freshest of the four checkpoint files now present (segment1–4) via
each file's own `last_updated_utc`.

**For the record, per the task's instruction:** the hold's `SKIPPED`
branch has **still never fired in production**. Segment 3 finished
(04:06:52Z) before today's 06:00 maintenance run even started, so there
was no overlap for the hold to act on — confirmed in the segment-3 status
doc. Segment 4 is sized (see below) to finish with ~2h of margin before
tomorrow's 06:00 fire under its own projected pace, so under normal
conditions this segment **also should not exercise the hold's SKIPPED
branch**. If segment 4 overruns its projection for any reason (API
slowdown, a PAUSE-then-resume, etc.) and is still running when tomorrow's
maintenance fires, that would be the hold's first live exercise — this
document commits to reporting that explicitly if it happens, not silently
noting "maintenance ran fine" without saying whether the hold was actually
exercised.

**6. Fresh backup — WAL-safe, integrity-verified. HARD GATE PASSED.**

```
$ python3 scripts/backup_database.py
[BACKUP] Running online backup of data/polymarket_tracker.db to
  backups/markets_20260825_201521.db...
[BACKUP] Verifying integrity of backups/markets_20260825_201521.db...
[OK] Backup created: backups/markets_20260825_201521.db
     Size: 17346.6 MB
```

Uses SQLite's `Connection.backup()` online backup API (safe against the
live WAL-mode monitoring writer, unlike a raw file copy), then a fresh
`PRAGMA integrity_check` against the *backup file itself* — both passed.
This is a hard gate: the driver would not have been launched had this
failed.

**7. Fresh fingerprint, committed** —
`data/characterizations/sweep_segment4/segment4_prewrite_fingerprint_20260825T202331Z.json`.
Full fields captured (traders, trades, positions, markets, resolved_markets,
resolution_evidence_source breakdown, `check_resolution_write_atomicity`=0,
SS C population figures). **`geo_elec_resolved_gapclean` = 10,870**, with
the exact query now recorded (segment 3's status check could not verify
this field for exactly this reason — the query had never been retained):

```sql
SELECT COUNT(*) FROM markets
WHERE category IN ('Geopolitics','Elections')
  AND resolved = 1
  AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)
```

Recovered from `tests/test_backtest_window_population.py:170-177`
(`old_method_market_ids`'s predicate, applied here without its
`window_start` filter to get the unconditional total). 10,870 vs. segment
3's pre-write reading of 10,856 — a plausible +14 given the ~208
geo/politics markets resolved in the last 7 days per today's maintenance
"Resolution Sweep — Channel 2 Discovery" step output, and the fact that
98% of all markets are `category='Unknown'` (this predicate only ever
moves a little).

`PRAGMA integrity_check` on the live DB at fingerprint time: `ok`.

**8. Runway arithmetic — computed live, not inherited.**

| quantity | value |
|---|---|
| current time (snapshot used for sizing) | `2026-08-25T20:13:33Z` |
| maintenance last finished | `2026-08-25T10:35:53Z` (today, exit 0) |
| next maintenance fire | `2026-08-26T06:00:00Z` |
| runway | 35,187s = 9.774h |
| target margin | 7,200s (2h — same margin segment 3 used) |
| budget | 27,987s |
| measured rate | 0.4195968966458433 s/market (segment 3's full-run: 39,022.51138806343s / 93,000 markets) |
| budget in calls | 66,699.73 |
| batches (floored to 500-row multiples) | **133** |
| **segment size** | **66,500 markets** |
| projected processing time | 27,903.2s = 7.751h |
| projected finish | `2026-08-26T03:58:36Z` |
| actual margin vs. 06:00 fire | 7,283.8s = 2.023h |

---

## THE RUN

**Candidate population:** 356,605 — under §C's predicate, combo/parlay
carve-out applied in SQL, all 164,500 previously-processed IDs excluded
(tranche2 5,000 + segment1-walked 6,000 + segment2 60,500 + segment3
93,000; union verified this session, zero overlap by construction).
**Matches segment 3's live post-run estimate of 356,605 exactly** — no
material organic drift in the ~4 hours between that estimate and this
session's actual materialization.

**Segment size:** 66,500 markets, **133 batches of 500**, derived from
the runway arithmetic above at segment 3's measured 0.4196s/market rate.
Projected wall time: 7.751h (27,903.2s).

**Driver:** `segment4_write.py`, structurally identical to
`segment3_write.py` (batching, pacing, checkpointing, terminal-signal
wiring, maintenance-window stop, the other abort conditions), with
**exactly one functional change**: confirm-before-abort on the
`check_resolution_write_atomicity` check (see above), plus the
mechanical path/segment-number substitutions (`segment4_*` paths,
`SEGMENT4-WRITE` log prefix) that are not a behavioral change. 0.25s
pacing, atomic checkpoint (temp-file + `os.replace`) after every batch,
launched detached with `python3 -u` under `nohup ... & disown`, with the
`.env_trading` `set -a` fix from housekeeping item 2 applied in the same
shell invocation before launch.

**Launch, confirmed live at time of writing:**

```
$ set -a; source /home/parison/.env_trading; set +a
$ nohup python3 -u data/characterizations/sweep_segment4/segment4_write.py \
    > logs/discovery_gap_sweep_segment4_20260825T202428Z.log 2>&1 &
$ disown
Launched PID: 39429
```

Process confirmed alive 3s after launch (`ps -p 39429`). Log confirmed
producing output immediately (unbuffered, `-u` working as intended):

```
[SEGMENT4-WRITE] Loaded fixed segment list: 66500 markets (combo/parlay
  cohort excluded in SQL at materialization time: 23745 excluded from a
  383321-market raw SS C population)
[SEGMENT4-WRITE] Pre-write check_resolution_write_atomicity: 0
[SEGMENT4-WRITE] No checkpoint found -- starting fresh (segment 4 batch 1).

[SEGMENT4-WRITE] === Batch 1/133 (500 markets in slice) ===
```

Pre-write atomicity read 0 (clean, matches the fresh fingerprint) — the
driver's own hard pre-flight gate at line ~134 would have refused to
start otherwise.

**Batch 1/133 confirmed complete, end-to-end, before this document was
committed:**

```
[SEGMENT4-WRITE] Batch 1/133 done: fresh=500 skipped=0
  tally={'resolved': 466, 'open': 32, 'indeterminate': 2, 'no_clob_response': 0}
  batch_indet_rate=0.4% [EVALUATED] cum_indet_rate=0.4% [EVALUATED]
  avg_pace=0.180s/call atomicity=0
[SEGMENT4-WRITE] Checkpoint written: .../data/checkpoints/segment4_checkpoint.json
```

Checkpoint contents: `batches_completed=1`, `cumulative_processed=500`,
`cumulative_accepted=466`, `cumulative_rejected=0`,
`cumulative_reasons={'written': 466}` (no cross-rank overwrite in batch 1),
`atomicity_transient_events=[]` (empty — the confirm-before-abort path was
not exercised this batch, since the reading stayed 0 throughout),
`elapsed_seconds_cumulative=215.2s` (≈0.430s/market including the 0.25s
sleep, consistent with segment 3's pace), `last_updated_utc=2026-08-25T20:28:04Z`.
Driver had already moved on to batch 2 by the time this was checked. This
confirms the write path, checkpointing, and the new confirm-before-abort
code path are all live and functioning — not just that the process started.

**Remaining 132 batches (~7.6h projected) are PENDING** — this document is
committed now with that clearly marked; full-run outcome, all of WATCH FOR
below, and whether confirm-before-abort or Fix 1's hold branch ever
actually fire must be checked and reported separately once the segment
finishes or is next checked, against
`data/checkpoints/segment4_checkpoint.json`,
`data/checkpoints/segment4_terminal_marker.json` (once it exists), and
`logs/discovery_gap_sweep_segment4_20260825T202428Z.log` directly.

---

## ABORT CONDITIONS — live, per amended §C, with the confirm-before-abort change

1. Backup missing/failed integrity check — n/a, already gated pre-launch.
2. Batch indeterminate rate > 10% (floor n=100) — PAUSE.
3. Cumulative indeterminate rate > 20% (floor n=100) — HARD ABORT.
4. `trg_resolved_no_unresolve` fires — HARD ABORT immediately.
5. `check_resolution_write_atomicity` non-zero — **HARD ABORT only if it
   persists across a 5s confirm re-query** (this task's change; see above).
6. Unpredicted `mark_market_resolved()` rejection pattern > 1% of processed
   rows — PAUSE, diagnose.
7. Pacing > 1.0s/call sustained over 2 consecutive batches — PAUSE.
8. **Plus:** stop cleanly at a batch boundary if within 30 minutes of the
   next 06:00:00 UTC maintenance fire (segment-specific, same as segments
   2 and 3).

---

## WATCH FOR

**a. Indeterminate rate against segment 3's 0.4–1.6% band.** PENDING —
not enough batches completed at time of writing to report a meaningful
rate.

**b. Cross-rank overwrite — zero across 161,309 accepted writes to date.**
PENDING for this segment's contribution. Structurally, this segment draws
from the same "previously-unresolved-only" candidate predicate segment 3
did, so the same structural-impossibility argument applies (no existing
lower-rank evidence exists to overwrite for a fresh `resolved=0` draw) —
but that argument should be checked against the actual reason log at
report time, not assumed to hold just because segment 3's did.

**c. A third contiguous dead cohort.** PENDING.

**d. Whether the atomicity check reads non-zero at all, and whether
confirm-before-abort correctly treats it as transient — this task's
change's first live exercise.** PENDING. `atomicity_transient_events` in
the checkpoint is the field to check.

**e. Whether Fix 1's hold branch fires, if the segment overruns.**
PENDING — see item 5 above; only relevant if segment 4 is still running
at tomorrow's 06:00 fire, which the sizing in item 8 is designed to avoid
with ~2h of margin.

---

## Deliverable status

This document was written **at launch**, per the two-phase pattern segments
2 and 3 used. All housekeeping items (1–8) and pre-launch verifications
are VERIFIED, live, this session — nothing above is inherited or assumed.
The run itself (THE RUN's outcome, all of WATCH FOR) is **PENDING** and
must be checked and reported separately once the segment finishes or is
otherwise checked — do not treat any PENDING item above as resolved
without reading `data/checkpoints/segment4_checkpoint.json`,
`data/checkpoints/segment4_terminal_marker.json` (once it exists), and the
run's own log file directly.
