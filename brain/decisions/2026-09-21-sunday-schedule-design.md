# Sunday schedule — design and verification (no changes made)

**Date:** 2026-09-21. Design-only, per scope — nothing in crontab, systemd, any wrapper, or any lock was
changed. A corpus content extraction run (PID 102652) was in progress throughout and was not touched;
confirmed running at the start (1:15:46 elapsed) and at the end (below) of this task. **This document is
for Oscar's approval; nothing here is live.**

---

## Correction to the framing this task opened with

The task's DEADLINE section states the concern as "`polymarket-sunday-elo.timer` is projected to overlap
`run_daily_maintenance.sh` on Sunday 2026-09-27." That framing understates what's actually happening.
**Three jobs are already colliding, for real, on the last two actual Sundays — not projected, observed:**

| pair | 2026-09-13 | 2026-09-20 |
|---|---|---|
| `run_database_backup.sh` vs `polymarket-sunday-elo.timer` | both start 03:00:01; backup runs until 06:05:39, ELO until 05:52:53 — **~169 min concurrent** | backup until 06:21:32, ELO until 05:54:33 — **~174 min concurrent** |
| `run_database_backup.sh` vs `run_daily_maintenance.sh` | maintenance starts 06:00:01 while backup is still running — **5.6 min overlap** | maintenance starts 06:00:01 while backup is still running — **21.5 min overlap** |

`run_database_backup.sh`'s own runtime history (`logs/backup.log`) shows Sunday durations of 180.6 min
(08-23), 18.4 min (08-30, an outlier — see below), 185.6 min (09-13), 201.5 min (09-20) — a night that used
to take 60-130 **seconds** now regularly runs 3+ hours specifically because it starts at the same 03:00:00
second as `polymarket-sunday-elo.timer`. This is the same starvation mechanism already documented for the
backup-vs-sweep incident (SQLite's Online Backup API restarts its copy whenever a page it already copied
is modified in the source — a continuously-writing concurrent process starves it by construction), now
recurring from the routine Sunday job cluster itself, not from the (now-stopped) discovery-gap sweep. This
was not previously flagged anywhere I could find. **Flagging prominently, as instructed for findings this
significant, and folding it into the design below** — a layout that only fixes ELO-vs-maintenance while
leaving backup running concurrently with ELO would leave the currently-worse problem unaddressed.

---

## Part 1 — every job that touches Sunday (Sat 22:00 → Mon 08:00)

Schedules verified against the scheduler itself, not inherited:

| job | mechanism | verified schedule | runtime: recent / trend | DB writes | lock-guarded |
|---|---|---|---|---|---|
| `backup_offsite.sh` | cron | `0 2 * * *` (`crontab -l`) | ~7-11.5 min, slowly growing with DB size (70G→75G over 10 days) | file-level copy (read) | no |
| `run_database_backup.sh` | cron | `0 3 * * *` | **highly volatile, no clean fit** (11s→41,602s across history; recent Sundays 180.6-201.5 min, see above) | Online Backup API (read, but restart-on-modified-page makes it effectively contend with concurrent writers) | **yes** (`bfdf9d6`-adjacent guard, pre-existing, verified working — self-overlap only) |
| `polymarket-sunday-elo.timer` | **systemd** | `systemd-analyze calendar`: "Sun \*-\*-\* 03:00:00 UTC", next elapse confirmed **2026-09-27 03:00:00 UTC** | linear fit, **R²=0.962**: `123.90 + 8.79×weeks` (weeks since 2026-08-09); 123.7→174.4 min over 6 clean weeks | writes `comprehensive_elo`, `geo_elo`, etc. (Part 2) | no |
| `weekly_resolution_sweep.sh` | cron | `30 3 * * 0` | **history not reconstructable** — no per-run timestamps in its own log, cron's journal records only invocation not completion. One reliable point: ~2 min (2026-09-20, from cron-invocation-to-file-mtime). 12 runs logged; volume resolved trending down (244→0), consistent with backlog exhaustion, but duration inference from that is not verified, only plausible. | writes market resolutions via `FastResolutionChecker` | no |
| `run_daily_maintenance.sh` | cron | `0 6 * * *` | weekday: 2.3-6.0h, no strong trend. **Sunday-specific: linear fit R²=0.114 — essentially no trend, dominated by noise** (345-739 min across 7 Sundays; driven by the Sunday-only `discover_leaderboard_traders.py` step, 10h budget) | reads ELO output (Part 2), writes research_exclusions, Pool B/C flags | **yes**, since `bfdf9d6` (this session's prior task) — self-overlap only, refuses with exit 75 |
| `run_feedback_loop.sh` | cron | `0 7 * * 1` | 2-4s, flat | reads DB (Telegram send) | no |
| `run_changelog_monitor.sh` | cron | `30 7 * * 1` | 5-8s, flat | no | no |
| `legendary_positions_scan.py` (direct) | cron | `30 7 * * 1` | not independently measured | reads DB | no |
| (reboot window) | unattended-upgrades | conditional, see Part 3 | 54s to complete once triggered | none directly; kills whatever else is running | n/a |

**Two genuine data gaps, reported rather than forced:** `weekly_resolution_sweep.sh`'s runtime history could
not be reconstructed — its own log has no per-run timestamps and cron's journal only logs invocation, not
completion; only one data point is trustworthy. `run_database_backup.sh`'s full history is too volatile
(spans 11 seconds to 693 minutes, with large spikes on non-Sunday days too, e.g. 2026-08-13 Thursday at
522.7 min) to fit any trend honestly — the recent-Sunday pattern above is real and directly relevant, but
it is reported as an observed recent value, not a projected trend line the way ELO's clean fit is.

---

## Part 2 — dependencies

**(1) Does ELO read what the resolution sweep writes? Yes.** `analysis/unified_elo_system.py:529-538`:

```python
# Get resolved markets from DATABASE (not API - API returns 0, DB has 2480!)
...
WHERE resolved = 1
...
resolved_markets_db = {row[0]: str(row[1]).lower() for row in cursor.fetchall()}
```

This query runs **once, near the start** of the ELO recalculation, loading a fixed snapshot of every
market's resolution status before the (up to 174-minute, growing) per-trader processing loop begins.
`weekly_resolution_sweep.sh` (03:30) starts 30 minutes after ELO (03:00) and writes new resolutions via
`FastResolutionChecker` for the run's duration. **Concurrently as configured today, any market the sweep
resolves after ELO's snapshot query but before ELO finishes is silently treated as still-unresolved for
this week's ELO computation** — not corrupted, but incomplete: that market's contribution is deferred to
next week's full recalculation rather than reflected this week. This matches the task's own framing
exactly: **the correct fix is order (sweep completes, then ELO reads), not merely spacing** them apart at
different clock times that could still race if either one's runtime grows past the gap.

**(2) Does daily_maintenance consume what ELO writes? Yes.** `scripts/update_research_exclusions.py`
(daily_maintenance's Step 0, every day) filters directly on ELO-written columns:

```
:58:  AND comprehensive_elo < 700
:79:  AND comprehensive_elo BETWEEN 1500 AND 3500
:344: geo_accuracy_pool (Pool C): {...} traders  (geo_elo IS NOT NULL, geo_resolved>=10, geo_elo_active>=500, no bot/wash)
```

**Severity is lower than (1):** `comprehensive_elo`/`geo_elo` only change on Sundays (the full recalc's
cadence), so Monday-through-Saturday's daily_maintenance *already* runs every single day against
"whichever Sunday was most recent" — that is the system's normal, already-accepted operating mode, not a
special failure case. If Sunday's own maintenance ran before Sunday's ELO finished, it would use the
*previous* Sunday's values for one day — one cycle stale, self-correcting the following Sunday, not
incorrect in the way (1) can be. **Verified precisely on the read side (exact line numbers above); the
write side is inferred from the ELO recalc's own log output ("Full ELO recalculation complete: N
updated") and matching column names, not independently traced to the exact `UPDATE` statement — flagged
as inferred, not verified, in case that distinction matters later.**

**(3) Does anything consume maintenance's own Sunday output before Monday?** No discrete scheduled job in
the Sat22:00-Mon08:00 window was found reading daily_maintenance's Sunday output before Monday's 07:00/07:30
jobs — those run the day after, well past even maintenance's worst observed Sunday finish (18:18,
2026-08-30). The continuously-running `polymarket-monitoring`/`polymarket-observer` services read live,
regardless of schedule, but are not discrete "jobs" in the scheduling sense this question is about.
**Genuinely independent**, stated as clearly as the two real dependencies above.

**STOP CONDITION check:** neither dependency makes a layout produce *incorrect* results, only *late* or
*one-cycle-stale* ones, for the reasons given per dependency. Not triggered. Both dependencies do inform
the design below: **order** (sweep → ELO), not just spacing, and a design that gives ELO and Sunday's
maintenance a real, not-nominal, margin.

---

## Part 3 — the reboot window

**Configuration** (`/etc/apt/apt.conf.d/50unattended-upgrades`, `/etc/apt/apt.conf.d/20auto-upgrades`),
quoted:

```
APT::Periodic::Unattended-Upgrade "1";
Unattended-Upgrade::Allowed-Origins { "${distro_id}:${distro_codename}-security"; };
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
```

**Mechanism, traced precisely via `/var/log/unattended-upgrades/unattended-upgrades.log`:**
`apt-daily-upgrade.timer` fires daily at `*-*-* 6:00` + up to 60min random delay
(`RandomizedDelaySec=60m`). If it installs a package that sets `/var/run/reboot-required` (kernel,
`linux-image-generic`, etc.), a persistent daemon (`unattended-upgrades.service`, running
`unattended-upgrade-shutdown --wait-for-signal` continuously since boot) schedules a `shutdown -r` for the
**next** occurrence of 03:00 UTC — not the same day. Example, quoted directly:

```
2026-09-05 06:10:03,245 WARNING Found /var/run/reboot-required, rebooting
2026-09-05 06:10:03,249 WARNING Shutdown msg: b"Reboot scheduled for Sun 2026-09-06 03:00:00 UTC, ..."
```

**Frequency and days:** 9 reboot-required events found across the full log history (2026-05-06 through
2026-09-12), scheduling reboots for Thu 05-07, Fri 05-22, Fri 06-05, Sat 07-04, Sat 07-18, Mon 08-10,
Fri 08-21, Sun 09-06, Sun 09-13. **8 actually executed as boots** (confirmed via `last reboot -F`); the
09-13 one did not — a separate, unrelated reboot at 2026-09-12 13:07:19 UTC (secureboot/dbx key update)
already cleared the pending reboot-required flag before 03:00 arrived, so the scheduled auto-reboot had
nothing left to do. **Answering the question directly: 03:00 is not every day, and not every Sunday — it
is conditional, firing only when that morning's unattended-upgrade actually installed something requiring
a restart.** Of the 8 real auto-reboots, exactly 1 (2026-09-06) landed on a Sunday — roughly 1 in 8,
consistent with "whenever a qualifying update lands" rather than any weekday-targeted pattern.

**Only one of these 8 reboots is confirmed to have killed a scheduled job this task cares about**
(2026-09-06, `polymarket-sunday-elo.timer`, SIGTERM at 03:00:00, per `journalctl`). The other 7 landed on
non-Sunday, non-critical-window days as far as this task's job inventory goes.

**Tradeoff, not decided here, per instruction:** automatic reboot at 03:00 keeps the box current on
security patches (including kernel CVEs) without manual intervention, on a box that otherwise runs
continuous, unattended monitoring. Against that: it has now demonstrably killed at least one scheduled
job mid-run (the 09-06 ELO recalculation), and every Sunday auto-reboot risk stacks on top of whatever
else this design puts in the 03:00 window. Disabling `Automatic-Reboot` would remove that risk entirely
but leave security patches installed-but-inactive until a manual reboot, on a box handling live trading
data. This is Oscar's call, not made here.

---

## Part 4 — timeline simulation

Committed: `scripts/sunday_schedule_simulation.py`. Not a one-off calculation — re-runnable with
`--layout {current,chain_fixed_time,recommended}`, `--weeks N`, `--json`. Growth models and their
justification are documented in the script's own module docstring (summarized in Part 1 above); nothing
in the fits is invented — every constant traces to the data quoted there.

**`--layout current`, week 0 (2026-09-27):**

```
polymarket-sunday-elo.timer  <->  run_database_backup.sh (Sun)      185.4 min overlap
polymarket-sunday-elo.timer  <->  weekly_resolution_sweep.sh          2.0 min overlap
polymarket-sunday-elo.timer  <->  run_daily_maintenance.sh (Sun)      5.4 min overlap
run_database_backup.sh (Sun) <->  weekly_resolution_sweep.sh          2.0 min overlap
run_database_backup.sh (Sun) <->  run_daily_maintenance.sh (Sun)     21.5 min overlap
```

**9 overlaps at week 0 already, not "first occurring 2026-09-27"** — because, per the correction above,
backup-vs-ELO and backup-vs-maintenance are *already real*, and the simulation (correctly) shows them
persisting and, in ELO's case, growing (`run_daily_maintenance.sh (Sun)` overlap grows from 5.4 min at
week 0 to 110.9 min by week 12). This matches, and sharpens, the task's own DEADLINE framing — the ELO
overlap the task named is real and growing; it is not the only one, or the first one.

Four more overlaps appear every week regardless of Sunday, unrelated to this task's redesign: Monday's
`run_daily_maintenance.sh` (typically finishing ~10:15-10:40) overlapping the 07:00/07:30 Monday jobs —
**pre-existing, present in every layout tested including the recommended one, out of scope** (all three
are read-only or non-DB-touching against maintenance's writes, a materially lower-severity kind of
overlap than the Sunday write-vs-write cluster this task is about).

---

## Part 5 — proposed layout

**(a) STAGGER** — move each job's clock time apart, keeping today's independent-cron structure. Simple to
reason about and revert. **Rejected as the primary fix**: Part 4's own `chain_fixed_time` run (below)
demonstrates concretely that any fixed-time gap erodes as ELO's runtime keeps growing at ~8.79 min/week —
a stagger chosen today to clear this week's numbers starts colliding again within weeks, and would need
re-tuning on the same cadence Part 6 proposes automating anyway. Also doesn't establish the Part 2
ORDER requirement on its own — two independently-scheduled jobs at different times can still race if
either one's runtime varies enough, only spacing not sequencing.

**(b) CHAIN** — one wrapper (`sunday_db_chain.sh`) runs `weekly_resolution_sweep.sh` →
`polymarket-sunday-elo.timer`'s payload → `run_database_backup.sh`'s payload, strictly sequentially,
closing both the Part 2 order dependency and the backup-vs-ELO starvation this task found. **Tested in the
simulator as `chain_fixed_time_layout()`**: chain starts 02:20 (clear of `backup_offsite.sh`'s 02:00 run),
`run_daily_maintenance.sh` (Sunday) still starts at a **fixed** clock time (09:00) afterward — exactly the
same structural weakness as (a), just moved downstream by one link: the chain-vs-maintenance gap starts
clean (week 0-1) and **starts colliding again from week 2 (2026-10-11) onward**, confirmed by the
simulation, because ELO's growth eventually outpaces any fixed gap chosen today. Correct on ordering,
still wrong on erosion.

**(c) SHARED WAITING LOCK — recommended.** Same chain as (b) for the ordering fix, but
`run_daily_maintenance.sh`'s Sunday start is **not a fixed clock time** — it blocks on the chain's own
completion (plus a fixed margin), so it structurally cannot start early regardless of how long the chain
runs, at any future runtime. Modeled in `simulate_recommended()`: `maintenance_start = max(04:00 floor,
chain_end + 15min margin)`. **This requires two separate locks with two separate semantics, addressed
directly per the task's explicit instruction:**

| lock | held by | semantics | purpose |
|---|---|---|---|
| `run_daily_maintenance.sh.lock` (existing, `bfdf9d6`) | one `daily_maintenance.py` instance at a time | `flock -n` — **refuse** immediately, exit 75, alert | self-overlap: a second daily_maintenance must never start while one is running, any day of the week |
| `sunday_db_chain.sh.lock` (new, not yet built) | the sweep→ELO→backup chain | `flock` **blocking**, no `-n` | Sunday's daily_maintenance start gates on this one — it should **wait**, not refuse, because the chain finishing is an expected, everyday part of Sunday's schedule, not an anomaly |

**These must stay two different locks.** If Sunday's `run_daily_maintenance.sh` instead joined the
chain's *own* lock with the existing refuse semantics, a long ELO run would cause that Sunday's
maintenance to be **skipped outright** (exit 75, Telegram alert) rather than delayed — turning a scheduling
question into a missed research-exclusions/Pool-C update for the day, which is a real regression from
today's behavior (today, Sunday's maintenance always eventually runs, just possibly overlapping other
jobs). The wait must be on a **second**, purpose-built lock that only Sunday's invocation of
`run_daily_maintenance.sh` acquires (blocking) *before* proceeding to its own self-overlap guard — the two
checks are independent and both still apply.

**Simulation result, `--layout recommended`, 13 weeks:** zero overlaps in the Sunday DB-write cluster at
every week, **by construction** — not merely "not found in 12 weeks," since the waiting mechanism makes an
overlap between the chain and Sunday's maintenance structurally impossible regardless of future growth.
One flagged item at week 12 (2026-12-20): `run_daily_maintenance.sh (Sun, waits on chain lock)` overlapping
Monday's `backup_offsite.sh` by 1.7 minutes — **this is a low-confidence artifact, not a real finding**:
it comes from extrapolating maintenance's own Sunday-duration fit (**R²=0.114** — essentially no trend,
see Part 1) 12 weeks past its 7 noisy data points, not from anything the chain design does. Reported
because the simulation's job is to report what it finds, not to hide a low-confidence result — but it
should not be read as a defect in the recommended layout.

**Does Part 2's ordering carry through?** Yes — sweep before ELO is the chain's fixed order, addressing
the correctness concern directly rather than leaving it to chance spacing.

**Does the design stay clear of the reboot window?** The chain's 02:20 start and (variable, but always
≥04:00) maintenance start both sit outside the 03:00-03:02 reboot risk window in the sense that neither
*starts* there — but the chain's own run **spans across** 03:00 every week (it starts at 02:20 and, once
ELO's growth is included, runs for hours), so a reboot landing on a future Sunday would still kill
whatever the chain is doing at that moment, same as it killed the standalone ELO job on 09-06. **This
layout does not remove that risk** — nothing proposed here changes the auto-reboot's behavior, per scope.
What it does provide, for free: because the chain now runs inside one lock-guarded wrapper (unlike today's
three independent cron entries), a reboot-induced kill releases that lock automatically (same
kernel-level guarantee as `bfdf9d6`), and the *next* Sunday's chain would simply run fresh — no different
from today's exposure, just now with the same self-healing property the maintenance guard already has,
folded in by using the same locking pattern rather than a new one.

**The corpus reader's safe-window assumption — needs correcting, in the sense that follows.** The corpus
extraction script's `maintenance_in_progress()` does **not** hardcode a fixed "~10:25" finish time
anywhere in its code (checked directly — no such literal exists in
`scripts/corpus_content_extractor.py`); it reads the live `Starting`/`Finished` state of
`logs/daily_maintenance.log`, so it already handles a Sunday finish of 13:12-18:19 correctly by
construction, no code change needed. What **does** need correcting is any *human* planning assumption
that treats "~10:25" as maintenance's typical finish time when scheduling other long-running work near a
Sunday morning — Part 1's data shows Sunday's own historical finish times were 11:45, 09:36(*), 15:09,
10:40, 15:43, 13:45(≈13:59 next-day due to the 09-12 crash), 18:18, 16:45, 13:59, 13:12 — **routinely 3-8
hours later than the weekday norm**, and this design (moving Sunday maintenance to wait on the chain)
will likely push it later still on weeks the chain is long. Documenting this here so the ~10:25 figure
isn't propagated as a Sunday-safe assumption elsewhere.

---

## Part 6 — the growth watch (design only)

**What:** a weekly check, run early each week (proposed: Monday 08:00 UTC, after this design's own Sunday
window closes and before the next Sunday), that re-runs
`python3 scripts/sunday_schedule_simulation.py --layout recommended --weeks 6 --json` and inspects the
result for any reported overlap within the next **N = 4** weeks.

**Why N=4:** this task itself — from "we have a projected collision" to a verified, simulated, documented
recommendation — took one focused session. Even budgeting for approval latency, a test-and-deploy cycle
matching `bfdf9d6`'s own stand-in-test pattern (Part 7), and normal scheduling slack, 4 weeks is enough
runway to repeat that process calmly rather than urgently. Shorter (1-2 weeks) risks alerting into an
already-tight deploy window; longer (8-12 weeks) risks the alert arriving so far ahead of the actual
collision that it's deprioritized and forgotten by the time it matters — the standing problem this project
has repeatedly found with "guard that can't fire because nobody's watching the horizon."

**How it alerts:** same Telegram path as `bfdf9d6`'s refusal alert (`TELEGRAM_AGENTS_TOKEN`/
`TELEGRAM_CHAT_ID`), triggered only when the recommended layout's own zero-overlap guarantee would be
broken — which, since (c)'s waiting-lock mechanism is structurally overlap-proof for the Sunday DB cluster
itself, really means: watching for the *next* thing to grow into a problem this design didn't anticipate
(e.g., `run_daily_maintenance.sh`'s own weekday runtime beginning a real trend, or a new Sunday job being
added). Framed that way, this is a standing regression check on the design's own assumptions, not a
recurring "is the collision here yet" poll — the collision this design targets is closed by construction,
not by continued vigilance.

**Not built.** Per scope ("design, do not build").

---

## Part 7 — test plan

1. **Schedule expressions parse to the intended times.** For any new/changed cron line: verify with the
   same method as Part 1 (computed next-fire, or `systemd-analyze calendar` if a systemd timer is chosen
   for the chain instead of cron — not decided here). For the chain wrapper's fixed 02:20 start and
   maintenance's `MAINT_EARLIEST_DISPATCH` floor (04:00): confirm both against a real clock, not just the
   simulator's internal `datetime` arithmetic.
2. **The simulation shows no overlap.** `python3 scripts/sunday_schedule_simulation.py --layout recommended`
   — already run this session, 13/13 weeks clean in the Sunday DB cluster (the one week-12 flag is
   explained above as the noisy maintenance-fit artifact, not a chain-design failure). Re-run before any
   deploy, not just once here.
3. **Lock stand-in tests, `bfdf9d6`-style, including SIGKILL.** Two locks to test, mirroring
   `tests/test_daily_maintenance_overlap_guard.sh`'s structure exactly:
   - `sunday_db_chain.sh.lock`: BLOCKED PATH (a second chain invocation waits, doesn't refuse — different
     from the maintenance guard's refuse semantics, so the stand-in test must assert *waiting*, not
     immediate exit), SIGKILL of a holder (chain lock releases immediately, same kernel guarantee), NORMAL
     RUN (acquires, runs sweep→ELO→backup in order, releases).
   - The maintenance-side wait: a stand-in holding `sunday_db_chain.sh.lock` while
     `run_daily_maintenance.sh` (Sunday) is invoked — assert it **blocks** (does not refuse, does not
     proceed) until the stand-in releases, **then** proceeds to its own separate self-overlap check
     (`bfdf9d6`'s existing guard) as normal. A SIGKILL of the chain stand-in here must also unblock
     maintenance immediately — the same critical property `bfdf9d6`'s own test suite already demonstrated
     for the self-overlap lock, now needed for this second lock too.
   - Never against production, same isolation pattern as `tests/test_daily_maintenance_overlap_guard.sh`
     and `tests/test_backup_overlap_guard.sh` (temp roots, stubbed payload scripts, shadowed `curl`).
4. **What Monday 2026-09-28's morning check must confirm.** Nothing will be deployed by then — this task
   changes no schedule, and 2026-09-27 will run under **today's unmodified layout**. So Monday's check is
   not "did the new layout work," it is **validation of this document's model against reality**:
   - Did `run_database_backup.sh` and `polymarket-sunday-elo.timer` actually run concurrently for
     ~185 minutes as observed the prior two Sundays, or did it diverge from the pattern?
   - Did `run_daily_maintenance.sh`'s 06:00 start actually land while backup and/or ELO were still
     running, and by how many minutes — compare against the simulation's week-0 prediction (backup: 21.5
     min overlap; ELO: 5.4 min overlap) directly, not just "did something overlap."
   - Did the reboot window fire this particular Sunday (check `last reboot -F` and
     `/var/log/unattended-upgrades/unattended-upgrades.log` the same way Part 3 did)? If so, which job(s)
     did it kill, and did `bfdf9d6`'s self-overlap guard correctly let the next day's cron reacquire
     cleanly (it should — same kernel-release-on-any-exit property already demonstrated).
   - **Whenever the recommended layout is later approved and deployed**, its first real Sunday's morning
     check should instead confirm: `sunday_db_chain.sh.lock` was acquired and released cleanly (sweep →
     ELO → backup, in that log order); `run_daily_maintenance.sh` did not start until the chain released
     (compare its actual start timestamp against the chain's actual finish, not the simulated one); and
     zero `SKIPPED`/refused lines appear for either lock. This second checklist is a template, not tied to
     2026-09-28, since deployment timing is Oscar's decision, not this task's.

---

## Corpus run confirmation

- **Start of this task:** PID 102652, elapsed 1:10:22 — running.
- **End of this task:** PID 102652, elapsed 1:22:30+, `corpus_content_state.json` `{"processed": 51,
  "failed": 0}` — running, healthy, unaffected by anything in this task.

**STOPPING HERE for Oscar's approval, per scope. No cron entry, systemd timer, wrapper, or lock was
changed.**
