# Backup Overlap Investigation — 2026-08-25 Anomaly + Guard Spec (2026-08-26)

Read-only investigation. Nothing implemented — Part 2 specifies a fix for
a future task to build. All figures below are VERIFIED against
`trading-swarm/logs/backup.log` (full history, April onward), `journalctl`,
`sysstat` (`/var/log/sysstat/sa25`, `sa26`), `last reboot`, `crontab -l`,
`systemctl cat`, and direct file checks, except where marked INFERRED or
SPECULATIVE. One premise in the task is corrected below (§3).

## Part 1 — why did the 2026-08-25 backup take >24h

### Summary finding

**It was slow, not stuck** — confirmed by `sar` disk-I/O telemetry showing
sustained, escalating write activity for hours, not an idle/blocked
process. The best-supported mechanism is SQLite's documented Online
Backup API behavior under a continuously-writing source (§3), compounded
by an unguarded second backup instance launching on top of the first the
next morning (§2). The **root trigger** — why *this* backup, out of many,
fell behind badly enough to still be running 24h later in the first
place — cannot be fully pinned down from available evidence; see the
"what remains unresolved" note at the end of §2.

### 1. Baseline duration, and how it has trended as the DB grew

Full history parsed from `backup.log`'s bracketed `[timestamp] Starting/
Finished database-backup` wrapper lines (present from 2026-05-05 onward;
before that, only bare completion lines exist, no duration data). **90
clean single-day runs, plus exactly 2 that were never closed out before
the next day's cron fired** (07-12 and 08-25 — see §6).

| month | n | median | max | count >1800s (30min) |
|---|---|---|---|---|
| 2026-05 | 25 | 16s | 6,668s (1.85h) | 1 |
| 2026-06 | 29 | 101s | 140s | 0 |
| 2026-07 | 20 | 439s | 11,012s (3.06h) | 6 |
| 2026-08 | 16 | 1,503s | 41,602s (11.56h)* | 7 |

(*2026-08 max as computed by simple sequential pairing attributes this to
the wrong instance — see the corrected attribution below.)

Overall distribution (n=90 clean pairs): min 11s, p25 62s, **median 115s**,
p75 420s, p90 5,168s, p95 11,053s, max (clean, non-overlap) 31,361s
(8.71h, 2026-08-13).

**DB size over the same period: 1.6GB (Apr 22) → 6.9GB (Jun 1) → 11.3GB
(Jul 1) → 15.4GB (Jul 24) → 16.4GB (Aug 13) → 18.4GB (Aug 25/26)** — an
~11x growth. The duration trend tracks this closely and non-linearly:
median duration is flat and trivial (16-101s) through May-June while the
DB was small, then grows sharply through July (439s median, 6 separate
runs over 30 minutes, up to 3h) and August (1,503s median, 7 runs over 30
minutes even before counting the two anomalies) — **this job has been
getting steadily less "fits in a few minutes" and more "occasionally
takes hours" for two months, well before the 08-25 event**, tracking DB
growth, not a step change that appeared out of nowhere on 08-25.

### 2. Reconstructing the night of 2026-08-25 — corrected timeline

The task's framing describes "the second backup's start... 11+ hours
after segment 4 aborted." Re-deriving this precisely from `backup.log`,
matching each `OK — backup created` line to the specific instance that
produced it (the script computes its target filename from `date
+%Y-%m-%d` at its own start time, so the file name unambiguously
identifies which invocation produced it — this is more reliable than
assuming first-to-start-finishes-first, which coincidentally also holds
here but isn't the reasoning to trust in general):

```
2026-08-25 03:00:01Z  Starting database-backup   (instance A)
2026-08-26 03:00:01Z  Starting database-backup   (instance B) — A still has not logged Finished
2026-08-26 14:33:23Z  OK — backup created: polymarket_tracker_2026-08-25.db (18G)  [instance A's output]
2026-08-26 14:33:23Z  Finished database-backup (exit: 0)                            [instance A]
2026-08-26 14:33:32Z  OK — backup created: polymarket_tracker_2026-08-26.db (18G)  [instance B's output]
2026-08-26 14:33:32Z  Finished database-backup (exit: 0)                            [instance B]
```

- **Instance A (the 08-25 backup): 03:00:01 → 14:33:23 the *next* day =
  128,002s = 35.56 hours.**
- **Instance B (the 08-26 backup, launched on top of A): 03:00:01 →
  14:33:32 = 41,611s = 11.56 hours.**

**What else was running:** Segment 3 (`logs/discovery_gap_sweep_
segment3_*.log`) completed at **2026-08-25T04:06:52Z**, i.e. it was still
writing to the live DB for the first ~66 minutes of instance A's run.
Segment 3's own pacing stayed completely flat through its own completion
(established in the prior diagnostic, ff360df) — it was not visibly
affected by instance A during that overlap window. Segment 4 then
launched at **2026-08-25T20:24:28Z**, i.e. roughly 17.5 hours *after*
instance A had already started and was presumably still running/stalled
— segment 4 ran the rest of that night against a source DB that a
backup process had already been contending with for most of a day.
Instance B's launch (**2026-08-26T03:00:01Z**) landed almost exactly on
segment 4's own pacing-degradation onset (established at ~03:00-03:09Z
in the prior diagnostic).

**`sar` confirms real, escalating disk-write activity, not an idle
process**, both mornings:

- **2026-08-25** (`sa25`, instance A's first ~9.3h): `bwrtn/s` (blocks
  written/sec) climbs from 2,799 at 03:00:01 to 120-145K through
  03:10-04:00, then jumps to **716,108 at 04:10** and **1,319,198 at
  04:20** — right after segment 3 finished (04:06:52) — and stays in the
  ~800K-1.3M range continuously through at least 12:20 (the last sample
  checked). `%iowait` rises from near-zero to 5-8.7%.
- **2026-08-26** (`sa26`, instance B's start): `bwrtn/s` jumps from
  ~333K at 03:00:01 to **946,332 by 03:10:25** and stays at 920K-988K
  through 04:10 — i.e. roughly **6-9x higher than what segment 3
  experienced during its own overlap with instance A** the morning
  before. `%iowait` rises from ~2.8% to 6.3-10.2%, `%system` CPU roughly
  doubles (6.7%→11-12%).

This is the quantitative reason segment 3 sailed through unaffected while
segment 4 didn't: segment 3's overlap window (Aug 25 morning) had
moderate I/O pressure (100-145K bwrtn/s) that hadn't yet escalated;
segment 4's overlap window (Aug 26 morning) started already at ~6-9x that
level, because it was a *second* backup piling onto a source DB an
already-24-hour-old backup had been grinding against continuously.

**What remains unresolved:** why instance A specifically fell behind
this badly on this specific night — as opposed to any other night with a
comparably-sized DB and comparable write volume — is not fully
determinable from available logs. `sar` proves *slow, sustained,
escalating* I/O, which rules out "hung/idle," but does not by itself
prove *why* the backup needed that much I/O rather than finishing in the
20-30 minutes recent same-sized-DB runs typically take (2026-08-23:
17,408 MB, 24.36h... actually already anomalous too — see §6, this
pattern had already started before 08-25). Settling the exact trigger
would require live process/lock instrumentation at the time, which
doesn't exist retroactively.

### 3. What mechanism could stall an online backup — correcting a premise

The task attributes the mechanism to `scripts/backup_database.py`'s
`Connection.backup()`. **That file is not what the cron job runs.** The
actual chain is: crontab `0 3 * * *` → `trading-swarm/scripts/
cron_wrappers/run_database_backup.sh` → `trading-swarm/scripts/
backup_database.sh`, which calls the **`sqlite3` CLI's `.backup` dot-command**
(`sqlite3 "$DB_SOURCE" ".backup '$BACKUP_FILE'"`) — a different script,
in a different repo, from the Python one named in the prompt.
`first-repo/scripts/backup_database.py` (which does use
`sqlite3.Connection.backup()`, writing to a different path,
`backups/markets_*.db`) exists but is not on this cron path; it appears
to be a separate, manually-invoked utility.

This distinction matters less than it sounds, because **the CLI's
`.backup` command and the Python `Connection.backup()` method are both
thin wrappers around the same underlying C API** (`sqlite3_backup_init` /
`_step` / `_finish`), so the semantics the task asks about apply to
either wrapper equally.

**The documented behavior (SQLite's Online Backup API):** the backup
process copies the source database page-by-page. If a page it has
*already copied* is modified in the source before the backup finishes,
the backup is **restarted** on the next step rather than silently
continuing with a stale copy. Per SQLite's own documentation of this API:
if the source is modified on every single step, **the backup may never
complete**. This is the load-bearing fact for this incident: **segment 3
was still writing when instance A started, and after segment 3 finished,
the ordinary 15-minute monitoring loop and other live writers continued
touching the DB continuously** — a backup racing a source that keeps
changing under it does not degrade gracefully to "slow," it can be made
to restart indefinitely by construction. **If this mechanism is what
happened here, the sweep (or any sustained writer) and the backup are
not merely coincident but structurally hostile to each other** — exactly
as the task's Q3 asked to state plainly if true. The `sar` data (§2) is
consistent with this (sustained, escalating I/O rather than one clean
pass), though it cannot distinguish "restarting repeatedly" from
"progressing very slowly through an ever-growing 18GB source" at the
resolution available.

### 4. Stuck vs. slow

**Slow, with real ongoing work — not stuck/idle.** `sar` (§2) shows
sustained, high, and *escalating* disk-write throughput for hours on both
mornings, correlated in time with each instance's start. There is no
window of near-zero I/O that would indicate a deadlocked or waiting
process. (No historical `ps`/lock-state snapshot exists to see the
`sqlite3` process directly — this conclusion rests on the I/O signature,
which is a reasonable but indirect proxy.)

### 5. Did it produce a valid backup?

**Yes, both files are present, correctly sized, and pass integrity
check.** Both `data/backups/polymarket_tracker_2026-08-25.db` and
`polymarket_tracker_2026-08-26.db` exist, each exactly 18,296,168,448
bytes (~17.0 GiB), consistent with the live DB's size at the time. The
script's own logic only prints "OK — backup created" after running
`PRAGMA integrity_check` and requiring `ok` (otherwise it deletes the
file and logs an ERROR) — both did. Independently re-run this session:
`PRAGMA integrity_check` on both files returns **`ok`**. This was a slow
backup, not a corrupt one.

### 6. Has this happened before?

**Yes, once, in a materially different form** — 2026-07-12. Scanning the
full log for "a start with no Finished line before the next day's start"
finds exactly two: 2026-07-12 and 2026-08-25.

The 07-12 instance is a **different failure mode**: it never logged a
"Finished" line **at all**, ever (not even 24h+ later) — it simply
vanished mid-run. A stale `polymarket_tracker_2026-07-12.db-journal` file
(1,024 bytes, timestamped Jul 12 03:00) still sits in `data/backups/`,
which is the signature of a rollback-journal-mode write that was
interrupted before commit or rollback — i.e., **the process was killed,
not merely slow**. `last reboot` shows a boot at **2026-07-12 19:00**,
16 hours after the backup started — consistent with (but not proof of) a
crash/instability event that morning that both orphaned the backup and
necessitated a later reboot that day. `sysstat` doesn't retain data back
that far (`/var/log/sysstat/` only goes back to `sa18`, i.e. ~9 days),
so this can't be corroborated with I/O telemetry the way 08-25 could be.

So: **this is not the first time a backup instance failed to complete on
schedule, but it is the first time one did so by running very slowly to
a valid completion rather than by being killed outright.** Beyond these
two full failures, the "clean pairing" duration table in §1 already
shows this job has been trending toward multi-hour completions with
increasing frequency since July — the 08-25 event is the extreme end of
an already-visible trend, not an isolated black swan.

---

## Part 2 — overlap guard specification (not implemented)

### 7. Confirmed: no overlap protection exists

Read `trading-swarm/scripts/backup_database.sh` and its wrapper
`run_database_backup.sh` in full: no `flock`, no PID file, no
"already running" check anywhere. Cron itself does not prevent
overlapping invocations of the same line either — it will happily fire a
fresh `run_database_backup.sh` every 24h regardless of whether the
previous one is still alive. This is exactly what allowed instance B to
launch on top of instance A on 08-26.

### 8. Guard options assessed

| approach | mechanism | stale-lock-after-a-hard-crash behavior |
|---|---|---|
| **flock** | `flock -n` on a dedicated lock file/fd, held for the script's lifetime | **Self-healing by construction.** The lock is a kernel-managed property of an open file descriptor, tied to the holding process. If that process dies for *any* reason — clean exit, SIGKILL, OOM kill, or the whole box rebooting — the kernel releases the lock immediately (on reboot, the fd simply no longer exists). There is no on-disk "lock file content" to go stale; a leftover lock *file* with no live holder is not locked. Nothing to clean up, ever. |
| **PID file + liveness check** | write PID on start, check `kill -0 $PID` (or `/proc/$PID`) on the next run before proceeding | **Not self-healing without extra care.** A hard kill leaves the PID file behind with no matching process — the naive check (does *any* process have this PID) correctly says "dead" *unless* the PID has been recycled by an unrelated process in the meantime, which is rare but real on a long-uptime box, and would falsely report "still running" indefinitely (a true stale-lock scenario with no expiry). Getting this fully right requires matching the recorded PID *and* command line/start time, not just PID existence — more moving parts than flock, for the same result. |
| **pgrep/ps-based "is a copy already running" check** | shell out to check the process table for a matching command line before starting | Self-healing in the same sense as flock (no persistent artifact to go stale), but has a TOCTOU race (two instances could both check before either has registered) and is fragile to the script being renamed, invoked differently, or run under a wrapper that changes the visible command line — silently defeating the check. Simplest to write, weakest guarantee. |

### Recommendation: `flock`

Same reasoning that favored checkpoint-recency over a lock/sentinel file
for the sweep's own maintenance hold (Fix 1, cited in
`daily_maintenance.py`'s own comments): **this box has a real crash
history** (the 07-12 orphaned backup, prior reboot-related incidents
noted in memory for `backup_offsite.sh`), so whatever guard is chosen
must not require a human to notice and clear a stale lock after a crash.
`flock` is the only one of the three that provides this for free, with
no expiry window to tune and no cleanup code to get right. Concretely
(specification only): wrap the existing script body in
`flock -n <lockfile> || exit 0` (non-blocking — see §9 for why not
blocking), using a lock file path that lives outside the repo's own
churn (e.g. under `/tmp` or a dedicated `data/.locks/` directory), one
lock per script identity.

### 9. What a blocked run should do

**Skip, with a clear log line — not silent, not alert, not queue.**

- **Not silent**: this codebase's own standing practice (per the
  memory record of this session's prior work and Fix 1's own comment
  block) is that a deliberate hold must say so explicitly in the log —
  "This is a deliberate hold, not a step failure" is the exact existing
  precedent to reuse verbatim in spirit. A silent skip of a daily backup
  is exactly the shape of failure this investigation stack has
  repeatedly had to dig out of logs after the fact.
- **Not alert**: Telegram alerting from cron-launched scripts is
  currently broken by the export-propagation gap in
  `run_daily_maintenance.sh` (established in the 2026-08-26 post-segment-4
  status doc) — wiring an alert here would silently do nothing today,
  giving false confidence that the condition is visible when it isn't.
  Fix the guard now with a log line; revisit alerting once the unrelated
  export-propagation gap is actually fixed, rather than making this
  guard depend on it.
- **Not queue**: given §1's finding that this job has been trending
  toward multi-hour and occasionally multi-day completions as the DB has
  grown, a blocking/queueing guard (`flock` without `-n`) risks a second
  instance waiting behind a first that itself takes 24-48h, then a third
  cron firing lands behind *that* — the exact cascading-pileup shape
  that produced this incident, just deferred one level. Skip-and-log
  converts an invisible overlap into a visible, single, boring log line
  and tomorrow's cron gets a clean shot at the same DB instead of
  compounding the queue.

### 10. Other cron/timer jobs with the same exposure

**Every cron-invoked wrapper on this box has zero overlap protection** —
checked all nine `cron_wrappers/*.sh` scripts plus the two first-repo
cron lines (`backup_offsite.sh`, `weekly_resolution_sweep.sh`): none
contain `flock`, a lockfile, or a PID check. This is a systemic gap, not
specific to the backup script. Risk by job, using observed durations
against each job's own interval:

- **`backup_database.sh`** (`0 3 * * *`, 24h interval): **confirmed
  real exposure** — this incident, plus 07-12.
- **`run_daily_maintenance.sh`** (`0 6 * * *`, 24h interval): observed
  range ~2.1h-9.7h across the last two weeks of `daily_maintenance.log`,
  comfortably inside 24h every time checked — **no overlap observed, but
  no protection exists if it were ever to degrade the way the backup
  job has.**
- **`backup_offsite.sh`** (`0 2 * * *`, 24h interval): observed ~7-8
  minutes on 2026-08-26 — low risk at current scale.
- **Weekly jobs** (`feedback_loop`, `changelog_monitor`, `code_hygiene`,
  `training_librarian`, `performance_analyst`, `signal_agent`,
  `trader_intelligence`, `legendary_positions_scan.py`,
  `weekly_resolution_sweep.sh`): 7-day interval gives comfortable
  headroom; `weekly_resolution_sweep.sh`'s own log shows it completing
  well within minutes. Low risk generically, not individually
  duration-audited beyond that spot check.

**A second, distinct risk this check surfaced**: **Sunday clustering.**
`backup_database.sh` fires at 03:00 every day *including* Sunday;
`weekly_resolution_sweep.sh` fires at 03:30 *only* on Sunday
(`30 3 * * 0`); and the systemd-timer-driven `polymarket-sunday-elo.service`
fires at 03:00 *only* on Sunday. Given §1's finding that the backup job
has recently often still been running well past 03:30, **Sundays
currently have three separate DB-touching jobs landing within the same
half hour** — this is a cross-job collision risk, distinct from (and not
fixed by) a self-overlap guard on any single script. Worth a separate
look, out of scope here.

One positive precedent: `polymarket-sunday-elo.service` is a systemd
`Type=oneshot` unit on a timer, not a cron line — systemd's default
behavior already refuses to start a unit that is still active when its
timer fires again, so **that one job already has free, built-in
self-overlap protection** that none of the cron-invoked scripts have.
Not proposing a wholesale migration here, just noting the existing
precedent on this exact box.

---

## Part 3 — the measurement gap (recorded, not fixed)

Restating and formalizing the finding from the prior pacing diagnostic
(`2026-08-26-segment4-pacing-diagnostic.md`, ff360df) as its own
standing item, since it is central to why this investigation was needed
at all:

**`segment4_write.py`'s `avg_pace` (and therefore ABORT CONDITION 7)
times CLOB fetch latency and the local `mark_market_resolved()` +
`conn.commit()` write together, as one number**, because `call_elapsed`
is measured from before the CLOB HTTP call to after the DB commit for
any market classified `resolved` (~475-496 of every 500 markets in the
degraded batches). Combined with `PRAGMA busy_timeout=30000` on the
driver's DB connection, **lock contention manifests purely as silent
slowdown — never an exception, never a distinguishable log line** — the
same signal a genuinely slow CLOB API would produce. Abort condition 7
fired and correctly stopped the run, but its own diagnostic label
("pacing") could not and did not distinguish "CLOB is slow" from "we are
waiting on a write lock," and this investigation had to reconstruct the
real cause from an entirely separate log (`backup.log`) and system
telemetry (`sar`) rather than from anything the sweep driver itself
recorded.

**What splitting the metric would require** (specification only, not
implemented): two separately-accumulated timers per call — one wrapping
only the `_fetch_by_clob()` call(s), one wrapping only the
`mark_market_resolved()` + `conn.commit()` call — each averaged and
logged per batch independently (e.g. `avg_clob_pace` and
`avg_commit_pace`), with ABORT CONDITION 7's threshold check applied to
whichever side it's actually meant to bound (or split into two separate
conditions with their own thresholds). This would have let this specific
incident be diagnosed from the segment 4 log alone, in minutes, instead
of requiring this cross-system reconstruction.
