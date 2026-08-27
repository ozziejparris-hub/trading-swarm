# Backup Overlap Guard + Backup-vs-Sweep Scheduling — 2026-08-26

**Provenance.** Dated 2026-08-26 to match the references already made to
this filename from `2026-08-21-discovery-gap-closure-prereg.md` (amendment
`226e01f`) and from the header comment block of
`scripts/cron_wrappers/run_database_backup.sh` (commit `9701d77`). Both of
those landed 2026-08-26 19:46 UTC; this companion document was actually
**written 2026-08-27**, the session that produced it having been cut off
by a usage limit before the file was created. Nothing here changes a
decision made on 08-26 — it records, in one place, what the amendment and
the wrapper comments point at, and adds the guard verification that was
claimed in `9701d77`'s commit message but not committed at the time.

Sources, all verified: `2026-08-26-backup-overlap-investigation.md`
(`03ab7ce`), `2026-08-26-segment4-pacing-diagnostic.md` (`ff360df`),
`2026-08-26-post-segment4-status.md` (`b0a63de`), the amendment
`226e01f`, the guard commit `9701d77`, and a fresh run of the test
harness committed alongside this doc
(`tests/test_backup_overlap_guard.sh`).

---

## 1. The guard as built

### What changed

`scripts/cron_wrappers/run_database_backup.sh` (commit `9701d77`, +51
lines, `backup_database.sh` itself untouched). The entire body is now
behind a **non-blocking** `flock`:

```sh
LOCKFILE="$SWARM/scripts/cron_wrappers/run_database_backup.sh.lock"
exec 200<>"$LOCKFILE"
if ! flock -n 200; then
    HELD_SINCE=$(cat "$LOCKFILE" 2>/dev/null)
    # ... compute elapsed hours from HELD_SINCE ...
    echo "[<ts>] SKIPPED -- backup already running (lock held since ${HELD_SINCE}, ~${ELAPSED_H}h ago). This is a deliberate skip, not a script failure -- see 2026-08-26-backup-guard-and-scheduling.md." >> "$LOG"
    exit 0
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOCKFILE"     # our start time, written only after we hold the lock
```

Design points, each carried over from the investigation's recommendation
(§8–§9 of `2026-08-26-backup-overlap-investigation.md`):

- **`flock`, not a PID file or a `pgrep` check.** The lock is a
  kernel-managed property of the open fd. It is released the instant the
  holder exits for *any* reason — clean exit, `SIGKILL`, OOM kill, or the
  box rebooting — with no on-disk lock *state* to go stale and no cleanup
  code that has to run correctly after a crash. This box has a real crash
  history (the 2026-07-12 orphaned backup; reboot-related `backup_offsite`
  incidents in memory), so "no human has to notice and clear a stale
  lock" is a hard requirement, not a nicety. Same self-healing reasoning
  already used for the sweep's own checkpoint-recency maintenance hold
  (Fix 1).
- **`-n` (non-blocking): a blocked run SKIPS, it does not queue.**
  Because a starved backup has been observed holding for 35.56h, a
  blocking `flock` would let tomorrow's cron pile up behind today's
  still-running instance, and the day after behind *that* — the exact
  cascading shape that caused the 08-25/08-26 incident, just deferred a
  level. Skip-and-log converts an invisible overlap into one visible,
  boring log line and gives the next night's cron a clean shot at the DB.
- **Logged, not silent, not alerted.** Standing practice in this codebase
  is that a deliberate hold must say so in the log ("This is a deliberate
  skip, not a script failure"). Telegram alerting from cron-launched
  scripts is currently broken by the export-propagation gap in
  `run_daily_maintenance.sh` (per `2026-08-26-post-segment4-status.md`),
  so wiring an alert here would silently do nothing today; revisit once
  that unrelated gap is fixed.
- **Lockfile path:** `scripts/cron_wrappers/run_database_backup.sh.lock`,
  one lock per script identity, committed-tree-adjacent. (The
  investigation floated `/tmp` or a `data/.locks/` dir; the wrapper as
  shipped keeps it next to the script. A leftover lock *file* with no
  live holder is not locked, so its location does not affect correctness
  — only tidiness.)

### Skip-line format (exact)

Observed from the harness, holder seeded 35h in the past:

```
[2026-08-27T22:01:25Z] SKIPPED -- backup already running (lock held since 2026-08-26T11:01:25Z, ~35.00h ago). This is a deliberate skip, not a script failure -- see 2026-08-26-backup-guard-and-scheduling.md.
```

If `HELD_SINCE` is empty or unparseable, the wrapper falls back to a
variant that drops the elapsed-time clause ("lock held by another
instance; its start time could not be read").

### Production status

Live since `9701d77`. Crontab line `0 3 * * *
.../run_database_backup.sh` points at the working-tree file directly. It
ran once on the allow path at **2026-08-27T03:00:01Z** (lockfile stamped
`2026-08-27T03:00:01Z` — that write happens only after `flock -n`
succeeds — and `backup.log` shows completion at 03:03:07Z, exit 0). No
sweep segment was running that night, so the blocked path has not yet
fired in production; it is covered by the harness below.

---

## 2. Verification

### Isolation — no real backup is ever run

The wrapper derives `LOG`, `LOCKFILE`, and the backup-script path
entirely from its `SWARM=` line (line 4). The harness
(`tests/test_backup_overlap_guard.sh`) copies the wrapper into a fresh
`mktemp -d` root with **that one line rewritten** to point at the temp
root; every other line runs verbatim. A stub `scripts/backup_database.sh`
in the temp root replaces the real ~18 GB `sqlite3 .backup` — it appends
a marker line and exits 0. Lock holders are `setsid` subshells that open
the temp lockfile, `flock` it, and idle; they are killed by
process-group. **The production DB, the production `backup.log`, and the
production lockfile are never touched.**

### Results — 27/27 assertions pass, deterministic across 4 consecutive runs

| # | Scenario | What it proves | Key assertions |
|---|---|---|---|
| **A** | **Blocked path.** Lockfile seeded 5h in the past, held by a live `setsid` holder; run the wrapper. | A second instance skips immediately instead of stacking. | exits 0; `backup.log` gets `SKIPPED -- backup already running (lock held since <seeded-ts>, ~5.00h ago)…`; elapsed-hours clause present and ≈ 5h; **stub backup NOT invoked**; no `Starting` line. |
| **B** | **Allow path.** No lock held; run the wrapper. | Normal nights are unaffected. | exits 0; stub backup invoked; `Starting` + `Finished database-backup (exit: 0)` logged; no `SKIPPED`; lockfile now holds a fresh `YYYY-MM-DDThh:mm:ssZ` stamp written post-acquire. |
| **C** | **Reacquire after clean exit.** Run B's env a second time. | A clean exit leaves the lock free — no self-deadlock. | exits 0; stub invoked again; two `Finished` lines total. |
| **D** | **SIGKILL survival.** Holder seeded 2h ago; confirm it blocks the wrapper (skips); then `kill -9` the holder (no `SIGTERM`, no cleanup hook) and rerun. | The property that chose `flock` over a PID file — demonstrated, not asserted. Hard-killed holder ⇒ lock auto-releases. | pre-kill run skips, stub not invoked; post-kill run exits 0, **stub invoked**, `Starting` logged; the stale holder timestamp is overwritten on reacquire. |
| **E** | **Negative control.** Same blocked scenario as A, run against the **pre-guard** wrapper (`9701d77^`) relocated identically. | Test A actually depends on the guard — it is not vacuously green. | pre-guard source contains no `flock`; run exits 0 but **invokes the backup anyway despite the held lock**; emits no `SKIPPED` line; proceeds straight to `Starting`. |

Run it:

```sh
bash tests/test_backup_overlap_guard.sh      # exit 0 iff all assertions pass
```

Full captured output of the run that accompanies this doc is in the
session's scratchpad (`guard_test_run.log`); it is reproducible offline
at any time with the command above and needs no DB, no network, and no
privileges.

---

## 3. The scheduling rule and its arithmetic

*Reproduced from amendment `226e01f` §b (lines 835–852 of the prereg).
The numbers below were re-checked for internal consistency when this
document was written; they match.*

**Rule: a sweep segment must finish before the `0 3 * * *` backup fires,
not cross it.**

- **Sweep rate, clean and uncontended** (segment 3, its own logged
  figures): 39,022.5 s / 93,000 markets = **0.4196 s/market** =
  **209.8 s per 500-market batch**.
- **Margin:** the same **1800 s** already used for the maintenance-stop
  boundary (`MAINTENANCE_STOP_MARGIN`).
- **Therefore a segment must stop no later than `02:30:00 UTC`** (03:00
  backup minus the 1800 s margin).
- **The cap is launch-time-dependent, not a fixed batch count:**

  ```
  max_batches = floor( (seconds from launch to the next 02:30:00 UTC) / 209.8 )
  ```

- **Worked against this arc's three recorded launch times:**

  | Launch (UTC) | Seconds to next 02:30:00 UTC | `max_batches` |
  |---|---|---|
  | 17:15:37 | 33,263 | **158** |
  | 20:24:28 | 21,932 | **104** |
  | 20:59:32 | 19,828 | **94** |

  All three are materially smaller than segment 3's 186 batches or
  segment 4's planned 133 — which is why segment 4, launched 20:59:32 and
  planned for 133, was structurally set up to still be writing when the
  03:00 backup fired.

- **A flat "~10-hour segment" does not fit this rule.** A 10 h segment
  requires launching by **16:30:00 UTC**; all three recorded launches are
  later than that. The remedy is a per-launch batch cap, not a fixed
  wall-clock segment length.

**Not implemented here.** `max_batches` is not wired into any driver —
that is segment 5's task. This document records the formula and the
inputs so segment 5 cannot be launched without applying it.

---

## 4. Alternatives considered and rejected

### 4a. Guard mechanism (from investigation §8)

| Option | Why not chosen |
|---|---|
| **`flock -n`** *(adopted)* | Kernel-released on any exit incl. crash/OOM/reboot; no stale state, no expiry to tune, no post-crash cleanup code. Matches the checkpoint-recency precedent already in the codebase. |
| PID file + `kill -0` liveness check | Not self-healing without care: a hard kill leaves the PID file behind; a recycled PID on a long-uptime box makes the naive check falsely report "still running" forever. Correct version needs PID **and** cmdline/start-time matching — more moving parts, same result. |
| `pgrep`/`ps` "is a copy already running" | Self-healing like `flock`, but has a TOCTOU race (two instances check before either registers) and silently breaks if the script is renamed, invoked differently, or wrapped. Simplest to write, weakest guarantee. |

### 4b. What a blocked run does (from investigation §9)

| Option | Why not chosen |
|---|---|
| **Skip + log line** *(adopted)* | Visible, single, boring; tomorrow's cron gets a clean DB. |
| Silent skip | This investigation stack has repeatedly had to dig silent backup gaps out of logs after the fact; a silent daily-backup skip is exactly that failure shape. |
| Telegram alert on skip | Cron-launched Telegram is currently broken (export-propagation gap in `run_daily_maintenance.sh`); an alert would no-op today while implying the condition is visible. Revisit after that gap is fixed. |
| Queue (blocking `flock`, no `-n`) | A holder can run 24–48 h; a second instance waits behind it, a third cron lands behind *that* — the cascading pileup that caused this incident, deferred one level. |

### 4c. Scheduling approach

| Option | Why not chosen |
|---|---|
| **Shorter, launch-time-capped segments** *(adopted)* | Keeps every segment fully clear of the backup window with no change to the backup job or the sweep's own maintenance-stop logic; the cap arithmetic is simple and auditable. |
| Pause the sweep for the backup window, resume after | Adds a second stop/resume path to the driver on top of the existing maintenance-stop boundary; the backup's own duration is now highly variable (minutes to 35 h), so "resume after" has no reliable trigger. |
| Move the backup off `03:00` | The `03:00` slot is deliberately between the auto-reboot window and market open; every other candidate slot collides with either monitoring activity or `run_daily_maintenance.sh` at `06:00`. Moving it trades a known-managed collision for an unmanaged one. |

---

## 5. Follow-ups explicitly out of scope here

### The eight other unguarded cron wrappers

Investigation §10 checked all nine active `cron_wrappers/*.sh` plus the
two first-repo cron lines: **none** contain `flock`, a lockfile, or a PID
check. Only `run_database_backup.sh` is fixed by `9701d77`. The other
eight, with their intervals and observed durations:

| Wrapper | Schedule | Observed duration | Assessed exposure |
|---|---|---|---|
| `run_daily_maintenance.sh` | `0 6 * * *` (24 h) | ~2.1 h – 9.7 h over the last two weeks | Inside 24 h every time checked, but **no protection if it degraded the way the backup job did**. Highest-priority of the eight. |
| `run_feedback_loop.sh` | `0 7 * * 1` (7 d) | minutes | Low at current scale |
| `run_changelog_monitor.sh` | `30 7 * * 1` (7 d) | minutes | Low |
| `run_code_hygiene.sh` | `0 20 * * 5` (7 d) | minutes | Low |
| `run_training_librarian.sh` | `0 9 * * 6` (7 d) | minutes | Low |
| `run_performance_analyst.sh` | `0 6 * * 1` (7 d) | minutes | Low |
| `run_signal_agent.sh` | `0 8 * * 1` (7 d) | minutes | Low |
| `run_trader_intelligence.sh` | `15 7 * * 1` (7 d) | minutes | Low |

Plus the two first-repo cron lines: `backup_offsite.sh` (`0 2 * * *`,
~7–8 min observed — low) and `weekly_resolution_sweep.sh` (`30 3 * * 0`,
completes within minutes — low). `run_integration_test.sh` and
`run_research_scout.sh` also lack a guard but are PAUSED in crontab.

**Not touched in this task.** If/when addressed, the pattern is
mechanical: the same `flock -n` block, one lock per script identity. The
`run_daily_maintenance.sh` case is the one worth doing first.

### Sunday clustering (distinct from self-overlap)

`backup_database.sh` fires `03:00` daily; `weekly_resolution_sweep.sh`
fires `03:30` Sundays only; `polymarket-sunday-elo.service` fires `03:00`
Sundays only. Given how often the backup now runs past `03:30`, **Sundays
have three DB-touching jobs inside one half-hour.** A per-script overlap
guard does not address cross-job collision. Worth a separate look.

One positive precedent on this box: `polymarket-sunday-elo.service` is a
systemd `Type=oneshot` timer unit, and systemd already refuses to start a
unit still active when its timer refires — free self-overlap protection
that none of the cron-invoked scripts have. Noted, not proposed as a
wholesale migration.

---

## 6. The `avg_pace` measurement gap (recorded, not fixed)

From amendment `226e01f` and `2026-08-26-segment4-pacing-diagnostic.md`:

ABORT CONDITION 7's `avg_pace` (checkpoint-recorded seconds/call) is
measured in `segment*_write.py` from **immediately before the CLOB
fetch** to **immediately after `mark_market_resolved()` +
`conn.commit()`** for any market classified `resolved` — i.e. it times
CLOB latency and the local DB write **as one number**. Combined with the
driver's own `PRAGMA busy_timeout=30000`, write-lock contention against
another writer produces *exactly the same signal* as a slow CLOB API:
silent slowdown, no exception, no distinguishing log line.

Condition 7 **fired correctly** on segment 4 (pacing sustained above
1.0 s/call for two batches) and correctly stopped the run — but its label
pointed at "pacing"/CLOB, while the actual cause was local write-lock
contention with the overlapping backup instance. That was only
established after the fact by cross-referencing `backup.log` and `sar`,
not from anything condition 7 itself recorded.

**Specified, not implemented:** split `avg_pace` into two
separately-accumulated, separately-logged timers — one wrapping only the
CLOB fetch call(s), one wrapping only `mark_market_resolved()` +
`conn.commit()` — so a future occurrence is attributable from the segment
log alone. Left for the segment 5 work or a dedicated driver change.

---

## What this document does NOT do

- Does **not** launch segment 5.
- Does **not** implement `max_batches` in any driver (segment 5's task).
- Does **not** add a guard to the other eight wrappers.
- Does **not** modify the sweep driver or `daily_maintenance.py`.
- Does **not** change `backup_database.sh` (only its wrapper was
  touched, in `9701d77`).
