# daily_maintenance flock guard — self-overlap + external probe, verified offline, deployed for tomorrow's 06:00 run

**Date:** 2026-09-21. Guards `scripts/cron_wrappers/run_daily_maintenance.sh` only, per scope. A corpus
content extraction run (PID 102652, started 2026-09-21T16:16:00 UTC) was in progress throughout this task
and was not stopped, signalled, or modified — confirmed running at both the start and the end (below).

---

## Part 1 — what was actually proposed on 5 September

**Correction to how this task was briefed: the proposal is in §6 ("KNOWN DEFECTS, LIVE AND UNFIXED"),
not §5.** Direct quote, `MASTER_HANDOVER_2026-09-05.md:347-350`:

> "**The eight remaining unguarded cron wrappers** — only the backup wrapper has a `flock` guard;
> `run_daily_maintenance.sh` is named as the next and highest-priority target (it runs 2-10h daily
> against a growing window), never implemented."

§5 ("WHAT WAS BUILT AND IS LIVE") is where the *already-shipped* backup guard and the backup-vs-sweep
incident are actually described. This is a real citation error in how the task was briefed, not a
material misrepresentation of the proposal's content — everything else about it (highest-priority
target, the reason given, "never implemented") matches the source exactly. Flagging per the task's own
instruction to report discrepancies, not treating it as a stop condition: the substance is intact, only
the section number is wrong.

**The backup-vs-sweep starvation incident** (§5's own reference, full account in
`2026-08-21-discovery-gap-closure-prereg.md:811-866`, sourced from
`2026-08-26-backup-overlap-investigation.md` / `2026-08-26-backup-guard-and-scheduling.md`): SQLite's
Online Backup API restarts its copy whenever a page it already copied is found modified in the source —
structurally incompatible with a continuously-writing source. The 2026-08-25 backup instance ran
**35.56h**, starved by the discovery-gap sweep's sustained writes, and a fresh 2026-08-26 instance
launched **on top of it** — nothing then stopped a second cron-fired instance from starting on a still-
running one. This double-overlap drove I/O contention that fired the sweep's own segment-4 pacing abort
at batch 101/133. Two fixes: (b) a scheduling rule so sweep segments finish before 03:00 UTC, and (c) the
`flock` guard on `run_database_backup.sh` — the backstop, not the primary fix.

**The existing flock guard on the backup wrapper** (`scripts/cron_wrappers/run_database_backup.sh:38-56`),
quoted in full:

```bash
LOCKFILE="$SWARM/scripts/cron_wrappers/run_database_backup.sh.lock"
exec 200<>"$LOCKFILE"
if ! flock -n 200; then
    HELD_SINCE=$(cat "$LOCKFILE" 2>/dev/null)
    NOW_EPOCH=$(date -u +%s)
    if [ -n "$HELD_SINCE" ] && HELD_EPOCH=$(date -u -d "$HELD_SINCE" +%s 2>/dev/null); then
        ELAPSED=$(( NOW_EPOCH - HELD_EPOCH ))
        ELAPSED_H=$(awk "BEGIN { printf \"%.2f\", $ELAPSED/3600 }")
        echo "[...] SKIPPED -- backup already running (lock held since ${HELD_SINCE}, ~${ELAPSED_H}h ago)..." >> "$LOG"
    else
        echo "[...] SKIPPED -- backup already running (lock held by another instance; its start time could not be read)..." >> "$LOG"
    fi
    exit 0
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOCKFILE"
```

Verified live, not assumed: ran `tests/test_backup_overlap_guard.sh` this session — **27/27 assertions
pass**, deterministic, including the SIGKILL-survival case. The backup wrapper's guard works exactly as
documented. This is the proven template Part 4 follows.

**The 2026-09-13 daily_maintenance audit** (`2026-09-13-daily-maintenance-audit.md:167-193`), quoted:

> "**No overlap has ever occurred, in 106 days of continuous log history (2026-05-31 → today).** A strict
> `[timestamp] Starting|Finished` state machine over the full 707,562-line log found **87 "Starting" and
> 87 "Finished" markers, perfectly 1:1 paired, zero anomalies**"

**Stated honestly, as instructed: this guard fixes a precautionary risk, not a live, observed problem
for daily_maintenance itself.** Nothing in 106 days shows daily_maintenance overlapping itself. What
*is* live (Part 2) is two separate, real collision risks this guard is built to close before they
produce daily_maintenance's own first overlap — not a response to one that already happened.

---

## Part 2 — the full schedule, and where collisions are

**Crontab** (`crontab -l`, parison user) and **systemd timers** (`systemctl list-timers --all`):

| job | mechanism | schedule | typical runtime | max observed | lock-guarded | touches DB / Ollama / network |
|---|---|---|---|---|---|---|
| `run_database_backup.sh` | cron | `0 3 * * *` | ~7-12 min | 35.56h (starved, pre-guard) | **yes** (flock) | DB (read), network (offsite? no — local disk) |
| `run_daily_maintenance.sh` | cron | `0 6 * * *` | 4.6-7.7h (today: 4.6h; 09-20: 7.2h) | not bounded before this task | **yes, as of this commit** | DB (read/write), network |
| `polymarket-sunday-elo.timer` | **systemd** | Sun 03:00 UTC | 123.7→174.4 min, growing | 174.4 min (09-20) | no | DB (read/write) |
| `run_changelog_monitor.sh` | cron | `0 7 * * 1` | 5-7s | 7s | no | network (Polymarket API), DB (none observed) |
| `run_feedback_loop.sh` | cron | `0 7 * * 1` | 2-4s | 4s | no | DB (read), network (Telegram) |
| `legendary_positions_scan.py` (direct, no wrapper) | cron | `30 7 * * 1` | seconds-low minutes | not measured this session | no | DB (read) |
| `backup_offsite.sh` | cron | `0 2 * * *` | ~8-11.5 min, slowly growing (70G→75G over 10 days) | 11.5 min (09-21) | no | DB (file-level copy) |
| `weekly_resolution_sweep.sh` | cron | `30 3 * * 0` | ~2 min (this week) | not tracked over time | no | DB (write, `FastResolutionChecker`) |
| `polymarket-monitoring.service` / `polymarket-observer.service` | systemd, **continuous** | always-on | n/a | n/a | n/a (not a scheduled job) | DB (continuous read/write) |
| (paused, not currently scheduled) `run_code_hygiene.sh`, `run_training_librarian.sh`, `run_integration_test.sh`, `run_performance_analyst.sh`, `run_research_scout.sh` (×2 lines), `run_signal_agent.sh`, `run_trader_intelligence.sh` | cron (commented out) | various | n/a — not running | n/a | no | n/a while paused |

**Reconciling "the eight remaining unguarded cron wrappers" against today's actual inventory — another
discrepancy worth stating plainly:** neither of the two natural readings of "eight" matches cleanly.
Counting wrapper *files* under `scripts/cron_wrappers/` excluding the already-guarded backup gives
**10** (all predate 2026-09-05). Counting *currently active* crontab lines excluding backup and
daily_maintenance gives **3** wrapper-based jobs (`changelog_monitor`, `feedback_loop`, plus
daily_maintenance itself was the 4th before this task) — 6 of the 10 wrapper files are for the Tier-3
agents paused 2026-07-15/2026-08-31, before or around the same time as the 09-05 document, so they
shouldn't have inflated an "eight" count either way. I can't reconstruct exactly how "eight" was arrived
at from what's on disk today. What I can state with confidence, verified directly rather than inherited:
**after this task, the currently-*active*, collision-relevant unguarded jobs are the six in the table
above minus daily_maintenance** (changelog_monitor, feedback_loop, positions_scan, backup_offsite,
weekly_resolution_sweep, and the polymarket-sunday-elo systemd timer) — not "seven" by either count I can
construct. Reporting this rather than forcing the number to fit.

**One-line risk assessment for each of those six** (not guarded in this task, per scope):

- `run_changelog_monitor.sh` — 5-7s runtime, weekly: negligible collision surface with anything.
- `run_feedback_loop.sh` — 2-4s runtime, weekly: negligible collision surface with anything.
- `legendary_positions_scan.py` — read-only DB scan, weekly, low volume: low risk, unmeasured runtime is the only gap.
- `backup_offsite.sh` — daily, ~8-11.5min and slowly growing with DB size: currently clear of both 03:00 and 06:00 windows by a wide margin, but unguarded and worth a growth-trend check eventually.
- `weekly_resolution_sweep.sh` — **already overlaps `polymarket-sunday-elo.timer` every week it runs** (03:30 start, ELO still running until ~05:52-05:54 recently) — a live, currently-happening concurrent-DB-write pair, not a projection; out of scope to fix here but the more urgent of the six.
- `polymarket-sunday-elo.timer` — see below; the most urgent of all seven jobs in this table, guard explicitly out of scope per the task ("Do NOT modify the Sunday ELO timer — report the collision").

### `polymarket-sunday-elo.timer` — projected collision with daily_maintenance

Full runtime history from `logs/sunday_elo.log` (first-repo), all six measured weeks since the figure the
task cited:

| date | runtime (min) | ended (UTC) | margin to 06:00 |
|---|---:|---|---:|
| 2026-08-09 | 123.7 | 05:03:45 | 56.3 min |
| 2026-08-16 | 132.8 | 05:12:53 | 47.1 min |
| 2026-08-23 | 145.1 | 05:25:12 | 34.8 min |
| 2026-08-30 | 144.0 | 05:24:06 | 35.9 min |
| 2026-09-06 | *(no completion — see below)* | — | — |
| 2026-09-13 | 172.8 | 05:52:53 | 7.1 min |
| 2026-09-20 | 174.4 | 05:54:33 | 5.4 min |

**2026-09-06 has a "Starting" line with zero output after it, not a missing log entry.** Investigated
rather than left unexplained: `journalctl` shows `polymarket-sunday-elo.service: Main process exited,
code=killed, status=15/TERM` at `Sep 06 03:00:00`, and `last reboot -F` confirms a system reboot at
`Sun Sep 6 03:00:54 2026` — an unattended-upgrades scheduled reboot window (the same ~03:00-03:01 pattern
recurs across `last reboot`'s full history: Aug 21, Jul 18, Jul 4, Jun 5, May 22, all ~03:00). The ELO
service was killed by the OS reboot roughly one second after the timer fired, not by any collision with
another job. Unrelated to this task's guard; noted so the gap in the trend table isn't mistaken for a
data problem.

**Linear fit on the five clean data points** (weeks since 2026-08-09, runtime in minutes):
`runtime = 123.90 + 8.79 × weeks` (R² = 0.962 — a strong, not coincidental, trend). Solving for
runtime = 180 min (the point a 03:00 start reaches 06:00): **weeks ≈ 6.38 → 2026-09-22**, i.e. inside
the *current* week. Projected onto the actual next three Sundays:

| Sunday | projected runtime | projected end | margin to 06:00 |
|---|---:|---|---:|
| **2026-09-27** | **185.4 min** | **06:05** | **−5.4 min (projected to cross)** |
| 2026-10-04 | 194.2 min | 06:14 | −14.2 min |
| 2026-10-11 | 203.0 min | 06:23 | −23.0 min |

**On current trend, the very next Sunday (2026-09-27) is projected to be the first time
`polymarket-sunday-elo.timer` overlaps `run_daily_maintenance.sh` directly** — not a distant, hypothetical
future date. Both write to the same SQLite database, and 2026-09-20's daily_maintenance run alone (no
Sunday-ELO overlap that day) already caused a lock storm on its own. This is the most urgent finding in
this inventory. Per scope, the Sunday ELO timer itself is not modified here — the flock guard shipped in
Part 4 means that if this collision does occur, `run_daily_maintenance.sh` will not itself double-run,
but it does nothing to prevent contention *from* the ELO job, since that timer has no guard and this task
does not add one.

---

## Part 3 — design

**Two distinct purposes, both served by the same lockfile and the same kernel primitive (flock), not two
separate mechanisms:**

**(a) Self-overlap.** A second `run_daily_maintenance.sh` invocation (cron-fired or manual) must refuse
while one is in progress. Served by `flock -n` on a dedicated lockfile, held via an open file descriptor
for the wrapper's entire lifetime — released by the kernel the instant the holder exits for any reason.

**(b) External probe.** Other jobs need to reliably ask "is maintenance running?" without blocking. Today
this need is filled by `scripts/corpus_content_extractor.py`'s `maintenance_in_progress()` — a heuristic
that tails `logs/daily_maintenance.log` looking for an unmatched "Starting" marker. Served by the *same*
lockfile the guard already holds: `flock -n LOCKFILE -c true` — exit 0 (lock acquired) means free, exit 1
means held. Non-blocking by construction (`-n`), side-effect-free beyond creating the lockfile if it
doesn't exist, and uses the actual kernel-held lock state rather than a second, weaker signal that could
in principle disagree with it (a log line and the true lock state are two different things; a kernel
`flock` query on the *same* file the guard holds cannot disagree with itself).

**Requirements, addressed:**

- **Kernel advisory locking (flock), not a lockfile-existence check or PID file.** A lockfile left behind
  by a SIGKILLed run would block every subsequent run silently and forever — the worst failure mode for a
  daily job. `flock`'s auto-release-on-exit property is demonstrated, not assumed (Part 5, test D).
- **A refused run is logged visibly, with timestamp and reason** — the same `[ISO8601] SKIPPED -- ...
  (lock held since <ts>, ~Nh ago)` line the backup wrapper already uses, into the same
  `logs/daily_maintenance.log` the corpus reader's heuristic and any human operator already watch.
- **Exit code: 75 (`EX_TEMPFAIL`, sysexits.h — "temporary failure, indicating something that is not
  really an error"), not 0.** This is a deliberate difference from the backup wrapper, which exits 0 on
  skip because repeated nightly backup skips are an explicitly accepted outcome of that guard's own
  design. A refused *daily_maintenance* run is not similarly tolerable — it means research_exclusions,
  geo backfill, and the audit steps silently don't run for a day — so its exit code should be
  distinguishable from a genuine completed run by anything that later inspects it, not just by grepping
  the log.
- **Telegram: yes, on every refusal, no change-gating.** `monitoring/failure_age.py`'s register/reconcile
  machinery was considered and rejected for this specific signal: it is built to classify persistent,
  content-keyed findings across runs and suppress ones a human has explicitly marked accepted (exactly
  the pattern behind the 2026-09-09 Telegram cut's "keep as little as possible" policy) — the wrong shape
  for a boolean daily gate event. Unlike a slowly-drifting metric, each additional day maintenance is
  refused is independently bad, not a repeat of the same news, so per-event alerting (not aged/suppressed
  after the first) is the correct choice here, and refusals are expected to be extremely rare (Part 1: zero
  in 106 days), so the volume risk the 09-09 cut was managing doesn't apply. Sent via
  `TELEGRAM_AGENTS_TOKEN`/`TELEGRAM_CHAT_ID` — the same credentials `scripts/polymarket_changelog_monitor.py`
  and `scripts/run_feedback_loop_agent.py` already use for trading-swarm-originated alerts (not
  first-repo's separate `telegram_alerts_token`, which is a different bot/channel for a different
  subsystem). Best-effort (`|| true`): a failed Telegram send must never change the wrapper's own exit
  code.
- **Lock file location and permissions:** `$SWARM/scripts/cron_wrappers/run_daily_maintenance.sh.lock` —
  same directory and `<wrapper-name>.lock` naming convention as the backup guard, for consistency.
  Permissions inherit from `exec 200<>` and the process umask (`0002` on this box), producing `-rw-rw-r--`
  — identical to the backup wrapper's existing lock file; no special hardening needed or done, matching
  precedent deliberately rather than by oversight.
- **How (b) is exposed:** documented here and in the wrapper's own comment block as the exact command
  (`flock -n "$LOCKFILE" -c true; echo $?`), not shipped as a new script file in this task. Scope was
  explicit — "IMPLEMENT on `run_daily_maintenance.sh` only" — and the lockfile the probe reads is a direct
  byproduct of that one file's guard, so a correct, complete probe needs no code of its own beyond that
  one documented invocation. Part 7 covers what adopting it in the corpus reader's *next* run would
  involve.

---

## Part 4 — implementation

`scripts/cron_wrappers/run_daily_maintenance.sh` — full diff logic (see the file itself for the complete,
commented version): `.env_trading` is now sourced *before* the guard (needed for the Telegram credentials
in the refusal path; harmless reordering, nothing about *when* or *what* maintenance runs changed). The
flock guard is inserted immediately after, following the backup wrapper's structure exactly — same
`exec 200<>`, same held-since-timestamp reporting, same log-line shape — with the two deliberate
differences from Part 3 (exit 75 instead of 0; a Telegram send on refusal). Everything after the guard
(`cd "$REPO"`, the `python3 scripts/daily_maintenance.py` invocation, the Starting/Finished log lines, the
final `exit $EXIT_CODE`) is **byte-for-byte unchanged** — maintenance's own steps, schedule, and behavior
are untouched, as scoped.

---

## Part 5 — proof, against a stand-in, never production

`tests/test_daily_maintenance_overlap_guard.sh` — directly modeled on `tests/test_backup_overlap_guard.sh`
(reused, not reinvented, wherever it applies), extended with an ALERT PATH and a PROBE scenario the backup
guard didn't need. **Isolation:** the wrapper is copied into a fresh `mktemp -d` root with its `SWARM=`,
`REPO=`, and `ENV=` lines rewritten to temp paths (every other line runs verbatim); `.env_trading` is a
temp stub with fake Telegram credentials; `curl` itself is shadowed on `PATH` by a stub that logs
invocations instead of calling the real API; `scripts/daily_maintenance.py` is replaced by a stand-in that
appends a marker line and exits 0 — **the "stand-in script that mimics maintenance"** the task asked for,
used for the ALLOW-PATH/REACQUIRE scenarios. For the lock-holding scenarios (BLOCKED, SIGKILL, PROBE), a
second, more direct stand-in is used — a `setsid` subshell that opens the temp lockfile, `flock -x`s it,
and idles — mimicking maintenance *holding the lock* specifically, independent of what the invoked script
does, exactly matching the backup test's proven `start_holder()` pattern.

**Results: 33/33 assertions pass.**

1. **START ONE, START A SECOND** (scenario A): second run refused, exits **75**, log line reads
   `SKIPPED -- daily-maintenance already running (lock held since <ts>, ~5.0Xh ago)`, `daily_maintenance.py`
   never invoked, no "Starting" line — and **exactly one** Telegram alert is sent, containing the
   configured bot token and the text "daily_maintenance REFUSED".
2. **SIGKILL THE HOLDER** (scenario D — **the critical test**): a holder is seeded 2h ago, a run against
   it is confirmed refused, then the holder receives `kill -9` (no SIGTERM, no cleanup hook). The very
   next run: exits 0, **the stand-in maintenance script is invoked**, "Starting" is logged, and the
   lockfile's stale 2h-old timestamp is overwritten with a fresh one — the lock released immediately and
   completely, with zero cleanup code needed. This is exactly the property a lockfile-existence
   implementation fails, silently, and it is demonstrated here, not merely asserted.
3. **NORMAL SINGLE RUN** (scenario B): acquires (lockfile stamped with a fresh ISO8601 timestamp),
   invokes the stand-in, logs Starting/Finished with exit 0, releases (scenario C confirms a second clean
   run reacquires normally) — and sends **zero** Telegram alerts, both on the first run and after a second
   clean run (scenario C).
4. **THE PROBE** (scenario P): the documented `flock -n LOCKFILE -c true` one-liner reports
   `NOT_IN_PROGRESS` before anything holds the lock, `IN_PROGRESS` while a holder holds it (no false
   negative), returns in single-digit milliseconds while blocked (non-blocking, not a slow poll), and
   `NOT_IN_PROGRESS` again once the holder is gone (no false positive).
5. **ALERT PATH**: covered inline in A/B/C/D above rather than as a separate scenario — exactly one alert
   per refusal (A: 1, D: still 1 after the SIGKILL-recovery run, not 2), zero alerts across three separate
   normal runs (B, C ×2).

**One incidental finding, not a guard defect:** the cleanup trap in both this test suite and
`tests/test_backup_overlap_guard.sh` (the template it's modeled on) appends each `mktemp -d` root to a
`ROOTS` array *inside* `make_env()`, which every call site invokes via command substitution
(`root="$(make_env)"`) — a subshell, so the append never reaches the parent shell's array and `cleanup()`'s
`rm -rf` loop has nothing to remove. Harmless (fresh unique temp dirs every run, no collision, no
correctness impact on any assertion — confirmed leftover `/tmp/bkguard.*` dirs from re-running the backup
test this session, cleaned up manually) but worth fixing where I could touch it: `test_daily_maintenance_overlap_guard.sh`'s
`ROOTS+=(...)` now happens at each call site instead, and cleanup was reverified to actually remove its
temp dirs. `test_backup_overlap_guard.sh` itself was left untouched (out of scope — this task guards
`run_daily_maintenance.sh` only).

---

## Part 6 — tomorrow's 06:00 run

**Confirmed, without touching production:**

- `bash -n` on the real, deployed `scripts/cron_wrappers/run_daily_maintenance.sh` — syntax OK.
- The real lockfile path (`scripts/cron_wrappers/run_daily_maintenance.sh.lock`) did not exist before
  this task (the guard is new) and a non-blocking probe against it now confirms it is genuinely free — no
  stale lock.
- **What I deliberately did NOT do:** invoke the real wrapper end-to-end against its real `SWARM`/`REPO`/
  `LOG` paths, even with a stubbed `daily_maintenance.py`, because doing so would append a real
  Starting/Finished pair to the *production* `logs/daily_maintenance.log` at an off-schedule time — the
  exact file `scripts/corpus_content_extractor.py`'s currently-running `maintenance_in_progress()` heuristic
  is watching live. A spurious entry there risks confusing that heuristic mid-run, which the task
  explicitly protects ("Do NOT touch the corpus reader... leave it"). Confidence that the *real* file
  works comes instead from: the syntax check above, the real-lockfile-path probe above, and
  `tests/test_daily_maintenance_overlap_guard.sh`'s 33/33 pass against the byte-identical script content
  (only `SWARM=`/`REPO=`/`ENV=` differ; the guard logic under test is unmodified). This is what "never
  against production" requires, not a partial workaround of it.

**What tomorrow morning's check should look for**, in order:

1. `logs/daily_maintenance.log`: a `[2026-09-22T06:00:0XZ] Starting daily-maintenance` line, and later a
   matching `Finished daily-maintenance (exit: N)` line — **no `SKIPPED` line** between them, under normal
   conditions (nothing should be holding the lock at 06:00 barring an actual stuck prior-day run, which
   this guard exists to catch if it happens).
2. `scripts/cron_wrappers/run_daily_maintenance.sh.lock`: its content should be a fresh
   `2026-09-22T06:00:0XZ` timestamp (overwritten at acquire), not the placeholder empty file this task
   left behind.
3. A probe run any time after the expected finish (`flock -n scripts/cron_wrappers/run_daily_maintenance.sh.lock -c true; echo $?`)
   should print `0` — lock released, not held.
4. If a `SKIPPED` line *does* appear: confirm exactly one Telegram message arrived in the trading-swarm
   agents channel around that timestamp, reading "daily_maintenance REFUSED (overlap guard) — lock held
   since \<ts\>, ~Nh ago."

---

## Part 7 — the corpus reader: untouched, and what switching it would involve

**Not touched.** PID 102652 confirmed running at the start of this task and confirmed running now (end of
this task) — see the final health check below. Its `maintenance_in_progress()` (log-tail heuristic) is
exactly as it was.

**What switching it to the new probe would involve, for its *next* run:** replace the tail-read-and-scan
of `logs/daily_maintenance.log` for `MAINTENANCE_START_MARKER`/`MAINTENANCE_FINISH_MARKER` substrings with
either (a) a `subprocess.run(["flock", "-n", str(LOCKFILE), "-c", "true"])` call, checking the return code,
or (b) — cleaner, since the corpus reader is a long-lived Python process rather than a one-shot shell
script — Python's own `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` opened directly against
`/home/parison/trading-swarm/scripts/cron_wrappers/run_daily_maintenance.sh.lock`, catching
`BlockingIOError` for "in progress" and releasing immediately otherwise — no subprocess spawn per check,
same kernel primitive. Either removes the current heuristic's two real weaknesses: coupling to
`daily_maintenance.log`'s exact marker text (a format change elsewhere would silently break the probe),
and the file's unbounded size forcing a chunked, widen-and-retry tail read. This is a small, self-contained
change (~15-20 lines, replacing `maintenance_in_progress()`'s body only) — not implemented now, per scope.

---

## Corpus run confirmation

- **Start of this task:** PID 102652, elapsed 52:30, RSS 30,368 KB — running.
- **End of this task:** PID 102652, elapsed 1:02:11, RSS 30,668 KB, `corpus_content_state.json`
  `{"processed": 50, "failed": 0}` — running, healthy, unaffected by anything in this task.
