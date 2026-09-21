#!/usr/bin/env python3
"""
sunday_schedule_simulation.py

Projects the Saturday-22:00-to-Monday-08:00 job window for the current
Sunday-schedule layout, and (with --layout proposed) for the recommended
layout in brain/decisions/2026-09-21-sunday-schedule-design.md, forward
across 13 Sundays (this Sunday + the next 12), applying each job's
observed growth rate. Reports every pairwise overlap found and the first
date it occurs.

Design decisions, stated rather than left implicit:

  - Growth models per job, chosen from what the underlying data actually
    supports (see brain/decisions/2026-09-21-sunday-schedule-design.md
    Part 1 for the full derivation of every number below):
      * polymarket-sunday-elo.timer: LINEAR fit, R^2=0.96, the one job
        with a clean enough trend to extrapolate honestly.
      * run_daily_maintenance.sh (Sunday total, driven by the Sunday-only
        discover_leaderboard_traders.py step): LINEAR fit on the 7
        Sunday-only data points, R^2 reported at run time -- much noisier
        than the ELO fit, flagged as lower-confidence, not hidden.
      * run_database_backup.sh: NO fittable trend -- runtime has spanned
        11s to 41,602s over its history with no clean pattern (confirmed
        NOT Sunday-specific: 693-minute and 185-minute spikes recur on
        weekdays too). Modeled as FLAT at the max of the 4 most recent
        Sunday observations -- a conservative planning figure, not a
        projection, and explicitly reported as such.
      * weekly_resolution_sweep.sh: FLAT at the one reliable observed
        duration (no per-run timestamps exist in its own log and cron's
        journal only records invocation, not completion -- see the
        decision doc's Part 1 for why a history could not be
        reconstructed here).
      * The reboot window: NOT a scheduled job -- modeled as a
        PROBABILISTIC daily risk window (03:00-03:02 UTC) any day an
        unattended-upgrades reboot-required update landed the prior
        morning, not a deterministic future date. Included in every
        week's report as a standing risk annotation, not as a positive
        overlap the way two real scheduled jobs colliding is.

  - "Overlap" for two jobs means their [start, end) windows on the same
    UTC calendar day intersect. Report the OUTPUT, not silently pick a
    threshold: a 0-minute-margin non-overlap is reported as the closest
    near-miss found, distinct from a true overlap.

Usage:
  python3 scripts/sunday_schedule_simulation.py                  # current layout, 13 Sundays
  python3 scripts/sunday_schedule_simulation.py --layout proposed  # recommended layout
  python3 scripts/sunday_schedule_simulation.py --weeks 26        # longer horizon
  python3 scripts/sunday_schedule_simulation.py --json            # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Optional

UTC = timezone.utc


# ---------------------------------------------------------------------------
# growth models -- each takes a week index (0 = this Sunday) and returns a
# duration in minutes. Every model is derived from data quoted in the
# decision doc, not guessed.
# ---------------------------------------------------------------------------

def linear_model(intercept: float, slope: float, floor: float = 0.0) -> Callable[[int], float]:
    return lambda week: max(floor, intercept + slope * week)


def flat_model(minutes: float) -> Callable[[int], float]:
    return lambda week: minutes


# polymarket-sunday-elo.timer: fit on weeks-since-2026-08-09 (see decision
# doc). "week" here is weeks-since-THIS-SUNDAY (2026-09-27), which is
# week-offset 6.86 in the original fit's coordinate system (2026-09-27 is
# 6.857 weeks after 2026-08-09) -- reindexed so week=0 in THIS script means
# 2026-09-27.
_ELO_FIT_INTERCEPT = 123.90
_ELO_FIT_SLOPE = 8.79
_ELO_WEEK0_OFFSET = 7.0  # (2026-09-27 - 2026-08-09).days / 7 == 49/7, exactly 7 weeks

elo_runtime_minutes = linear_model(
    _ELO_FIT_INTERCEPT + _ELO_FIT_SLOPE * _ELO_WEEK0_OFFSET, _ELO_FIT_SLOPE
)

# run_daily_maintenance.sh Sunday total: linear fit on the 7 Sunday data
# points (08-09 through 09-20), reindexed the same way. Noisier (lower R^2,
# reported by fit_sunday_maintenance() below) -- included because the task
# explicitly asks for daily_maintenance's Sunday-specific growth, not
# because the fit is as trustworthy as the ELO one.
_MAINT_SUNDAY_POINTS_MIN = [
    (0, 345.5),   # 2026-08-09
    (1, 280.3),   # 2026-08-16
    (2, 583.8),   # 2026-08-23
    (3, 738.8),   # 2026-08-30
    (4, 645.4),   # 2026-09-06
    (5, 479.4),   # 2026-09-13
    (6, 432.3),   # 2026-09-20
]


def _ols_fit(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Returns (intercept, slope, r_squared)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(points)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in points)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    slope = cov / var_x
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return intercept, slope, r2


_MAINT_INTERCEPT, _MAINT_SLOPE, MAINT_SUNDAY_R2 = _ols_fit(_MAINT_SUNDAY_POINTS_MIN)
# Reindex to week=0 meaning 2026-09-27 -- week 7 in this fit's own
# coordinates (week 0 = 2026-08-09), one week past the last observed point
# (week 6 = 2026-09-20).
maintenance_sunday_runtime_minutes = linear_model(
    _MAINT_INTERCEPT + _MAINT_SLOPE * 7, _MAINT_SLOPE
)

# run_database_backup.sh, Sunday: no fittable trend (see module docstring).
# Flat at the max of the 4 most recent Sunday observations: 08-23 (180.6),
# 08-30 (18.4), 09-13 (185.6), 09-20 (201.5) minutes. 09-06 has no data
# point (that Sunday's backup was itself killed by the reboot -- see the
# reboot-window note below).
backup_sunday_runtime_minutes = flat_model(max(180.6, 18.4, 185.6, 201.5))

# weekly_resolution_sweep.sh: one reliable observation (2026-09-20, ~2 min).
sweep_runtime_minutes = flat_model(2.0)

# Weekday (non-Sunday) runtimes, used to size non-Sunday-window jobs that
# still fall in the Sat22:00-Mon08:00 span (backup, daily_maintenance's
# Monday run, changelog_monitor, feedback_loop, positions_scan). Flat,
# recent-typical values -- these are not the growth story here.
backup_weekday_runtime_minutes = flat_model(6.0)       # typical recent weekday (Sept)
maintenance_weekday_runtime_minutes = flat_model(260.0)  # ~4.3h typical recent weekday
changelog_monitor_minutes = flat_model(0.1)
feedback_loop_minutes = flat_model(0.1)
positions_scan_minutes = flat_model(2.0)                # not independently measured; conservative


@dataclass
class Job:
    name: str
    day: str               # "Sat", "Sun", "Mon" -- day within the simulated window
    start_time: time        # UTC
    runtime_fn: Callable[[int], float]  # week index -> minutes
    lock_guarded: bool
    writes_db: bool
    notes: str = ""

    def window(self, sunday_date: date, week: int) -> tuple[datetime, datetime]:
        day_offset = {"Sat": -1, "Sun": 0, "Mon": 1}[self.day]
        d = sunday_date + timedelta(days=day_offset)
        start = datetime.combine(d, self.start_time, tzinfo=UTC)
        minutes = self.runtime_fn(week)
        end = start + timedelta(minutes=minutes)
        return start, end


def current_layout() -> list[Job]:
    return [
        Job("backup_offsite.sh (Sat)", "Sat", time(2, 0), flat_model(9.0), False, False,
            "not independently trended; typical recent ~9min"),
        Job("run_database_backup.sh (Sat)", "Sat", time(3, 0), backup_weekday_runtime_minutes, True, True),
        Job("polymarket-sunday-elo.timer", "Sun", time(3, 0), elo_runtime_minutes, False, True,
            "linear fit R^2=0.96"),
        Job("run_database_backup.sh (Sun)", "Sun", time(3, 0), backup_sunday_runtime_minutes, True, True,
            "no fittable trend; flat at max of 4 recent Sundays"),
        Job("weekly_resolution_sweep.sh", "Sun", time(3, 30), sweep_runtime_minutes, False, True,
            "flat; only 1 reliable duration observation exists"),
        Job("backup_offsite.sh (Sun)", "Sun", time(2, 0), flat_model(9.0), False, False),
        Job("run_daily_maintenance.sh (Sun)", "Sun", time(6, 0), maintenance_sunday_runtime_minutes, True, True,
            f"linear fit R^2={MAINT_SUNDAY_R2:.2f} -- noisier than the ELO fit"),
        Job("backup_offsite.sh (Mon)", "Mon", time(2, 0), flat_model(9.0), False, False),
        Job("run_database_backup.sh (Mon)", "Mon", time(3, 0), backup_weekday_runtime_minutes, True, True),
        Job("run_daily_maintenance.sh (Mon)", "Mon", time(6, 0), maintenance_weekday_runtime_minutes, True, True),
        Job("run_feedback_loop.sh", "Mon", time(7, 0), feedback_loop_minutes, False, True),
        Job("run_changelog_monitor.sh", "Mon", time(7, 30), changelog_monitor_minutes, False, False),
        Job("legendary_positions_scan.py", "Mon", time(7, 30), positions_scan_minutes, False, False),
    ]


def elo_disabled_layout() -> list[Job]:
    """
    The actual state as of 2026-09-21 (brain/decisions/2026-09-21-disable-sunday-elo-recalc.md):
    polymarket-sunday-elo.timer stopped and disabled, nothing else changed --
    no chain, no wait-lock, no moved start times. Tests whether removing just
    the ELO job (without any of the CHAIN/WAIT redesign in Part 5 of
    2026-09-21-sunday-schedule-design.md, which was never approved or
    deployed) is sufficient on its own.

    run_database_backup.sh (Sun) reverts to the WEEKDAY runtime model here,
    not the flat 201.5min starved figure current_layout() uses -- that
    figure was modeling exactly the concurrent-ELO starvation mechanism
    this removes. Using the starved figure after removing its cause would
    misrepresent the very thing being tested.
    """
    jobs = current_layout()
    return [
        Job("run_database_backup.sh (Sun)", "Sun", time(3, 0), backup_weekday_runtime_minutes, True, True,
            "ELO removed -- reverts to unstarved weekday-typical runtime, not the starved 201.5min figure")
        if j.name == "run_database_backup.sh (Sun)" else j
        for j in jobs
        if j.name != "polymarket-sunday-elo.timer"
    ]


CHAIN_START = time(2, 20)     # sunday_db_chain.sh: sweep -> ELO -> backup (after backup_offsite.sh's 02:00 file-level copy, which typically finishes ~02:09-02:12 and is a different, lower-contention mechanism than the Online Backup API -- given a clean gap anyway rather than relying on that distinction)
MAINT_SUNDAY_START = time(9, 0)  # run_daily_maintenance.sh, Sunday only


def chain_fixed_time_layout() -> list[Job]:
    """
    Option (b), CHAIN with a fixed downstream clock time: sweep -> ELO ->
    backup run back-to-back in one wrapper (the Part 2 order dependency,
    and closes the ELO-vs-backup starvation this task found already
    active on 2026-09-13/09-20), but run_daily_maintenance.sh still starts
    at a FIXED clock time (09:00) afterward, the same way it does today at
    06:00. Kept in the simulator deliberately -- NOT the recommendation --
    to demonstrate empirically (Part 5) that a fixed downstream time still
    erodes as the chain keeps growing: the 13-week run below shows this
    layout is overlap-free for 2 weeks and then starts colliding again
    from 2026-10-11 onward. This is the concrete argument for the
    RECOMMENDED layout (waiting lock) over plain staggering-after-a-chain.
    """
    jobs = current_layout()

    def chain_runtime(week: int) -> float:
        return sweep_runtime_minutes(week) + elo_runtime_minutes(week) + backup_sunday_runtime_minutes(week)

    kept = []
    for j in jobs:
        if j.name in ("polymarket-sunday-elo.timer", "run_database_backup.sh (Sun)"):
            continue  # folded into the chain below
        if j.name == "weekly_resolution_sweep.sh":
            j.start_time = CHAIN_START
            j.runtime_fn = chain_runtime
            j.name = "sunday_db_chain.sh (sweep -> ELO -> backup)"
            j.notes = "CHAIN: fixed order, replaces 3 standalone Sunday entries"
        if j.name == "run_daily_maintenance.sh (Sun)":
            j.start_time = MAINT_SUNDAY_START
            j.notes += f" | moved from 06:00 to {MAINT_SUNDAY_START.isoformat()} to clear the chain with margin"
        kept.append(j)
    return kept


MAINT_WAIT_MARGIN_MINUTES = 15    # buffer after the chain releases its lock
MAINT_EARLIEST_DISPATCH = time(4, 0)  # floor: maintenance never starts before this even if the chain finishes early


def find_overlaps(windows: list[tuple]) -> list[dict]:
    overlaps = []
    for i in range(len(windows)):
        for k in range(i + 1, len(windows)):
            j1, s1, e1 = windows[i]
            j2, s2, e2 = windows[k]
            if s1 < e2 and s2 < e1:
                overlaps.append({
                    "job_a": j1.name if hasattr(j1, "name") else j1,
                    "job_b": j2.name if hasattr(j2, "name") else j2,
                    "a_window": (s1.isoformat(), e1.isoformat()),
                    "b_window": (s2.isoformat(), e2.isoformat()),
                    "overlap_minutes": (min(e1, e2) - max(s1, s2)).total_seconds() / 60,
                })
    return overlaps


def simulate(jobs: list[Job], first_sunday: date, weeks: int) -> list[dict]:
    results = []
    for week in range(weeks):
        sunday_date = first_sunday + timedelta(days=7 * week)
        windows = [(j, *j.window(sunday_date, week)) for j in jobs]
        results.append({
            "week": week, "sunday_date": sunday_date.isoformat(),
            "windows": [(j.name, s.isoformat(), e.isoformat()) for j, s, e in windows],
            "overlaps": find_overlaps(windows),
        })
    return results


def simulate_recommended(first_sunday: date, weeks: int) -> list[dict]:
    """
    Option (c), the RECOMMENDED layout: the same sweep->ELO->backup chain
    as chain_fixed_time_layout(), but run_daily_maintenance.sh's Sunday
    start is DYNAMIC -- max(MAINT_EARLIEST_DISPATCH, chain_end +
    MAINT_WAIT_MARGIN_MINUTES) -- modeling a BLOCKING wait on the chain's
    own lock (a SEPARATE lock from the self-overlap guard bfdf9d6 already
    put on run_daily_maintenance.sh -- see the decision doc Part 5(c) for
    why these must be two distinct locks with two distinct semantics).
    This is why this layout is overlap-free by CONSTRUCTION, not merely
    verified-not-to-overlap for however many weeks were simulated: the
    downstream job literally cannot start until the upstream one is done
    plus a fixed margin, at any runtime, forever.
    """
    jobs_template = current_layout()
    other_jobs = [j for j in jobs_template if j.name not in
                  ("polymarket-sunday-elo.timer", "run_database_backup.sh (Sun)",
                   "weekly_resolution_sweep.sh", "run_daily_maintenance.sh (Sun)")]

    def chain_runtime(week: int) -> float:
        return sweep_runtime_minutes(week) + elo_runtime_minutes(week) + backup_sunday_runtime_minutes(week)

    results = []
    for week in range(weeks):
        sunday_date = first_sunday + timedelta(days=7 * week)
        chain_start = datetime.combine(sunday_date, CHAIN_START, tzinfo=UTC)
        chain_end = chain_start + timedelta(minutes=chain_runtime(week))
        maint_start = max(
            datetime.combine(sunday_date, MAINT_EARLIEST_DISPATCH, tzinfo=UTC),
            chain_end + timedelta(minutes=MAINT_WAIT_MARGIN_MINUTES),
        )
        maint_end = maint_start + timedelta(minutes=maintenance_sunday_runtime_minutes(week))
        chain_job = ("sunday_db_chain.sh (sweep -> ELO -> backup)", chain_start, chain_end)
        maint_job = ("run_daily_maintenance.sh (Sun, waits on chain lock)", maint_start, maint_end)
        windows = [chain_job, maint_job] + [(j, *j.window(sunday_date, week)) for j in other_jobs]
        results.append({
            "week": week, "sunday_date": sunday_date.isoformat(),
            "chain_end": chain_end.isoformat(), "maintenance_start": maint_start.isoformat(),
            "windows": [(n, s.isoformat(), e.isoformat()) for n, s, e in windows],
            "overlaps": find_overlaps(windows),
        })
    return results


def first_overlap_date(results: list[dict], job_a: str, job_b: str) -> Optional[str]:
    for r in results:
        for o in r["overlaps"]:
            if {o["job_a"], o["job_b"]} == {job_a, job_b}:
                return r["sunday_date"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--layout", choices=["current", "chain_fixed_time", "recommended", "elo_disabled"], default="current")
    parser.add_argument("--weeks", type=int, default=13)
    parser.add_argument("--first-sunday", type=str, default="2026-09-27")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    first_sunday = date.fromisoformat(args.first_sunday)

    if args.layout == "recommended":
        results = simulate_recommended(first_sunday, args.weeks)
        n_jobs = len(results[0]["windows"]) if results else 0
    else:
        layout_fns = {
            "current": current_layout,
            "chain_fixed_time": chain_fixed_time_layout,
            "elo_disabled": elo_disabled_layout,
        }
        jobs = layout_fns[args.layout]()
        results = simulate(jobs, first_sunday, args.weeks)
        n_jobs = len(jobs)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Simulating {len(results)} Sundays, {n_jobs} jobs per week (layout={args.layout}).\n")
        any_overlap = False
        for r in results:
            if r["overlaps"]:
                any_overlap = True
                print(f"=== {r['sunday_date']} (week {r['week']}): {len(r['overlaps'])} overlap(s) ===")
                for o in r["overlaps"]:
                    print(f"  {o['job_a']}  <->  {o['job_b']}   ({o['overlap_minutes']:.1f} min overlap)")
        if not any_overlap:
            print("ZERO overlaps found across the simulated horizon.")
        if args.layout == "recommended":
            print(f"\nchain end / maintenance start, by week:")
            for r in results:
                print(f"  {r['sunday_date']}: chain ends {r['chain_end']}, maintenance starts {r['maintenance_start']}")
        print()
        print("Reboot window (probabilistic, not scheduled): 03:00-03:02 UTC any day an "
              "unattended-upgrades reboot-required update landed the prior morning's "
              "apt-daily-upgrade run (~06:00-07:00). Historically ~1 in 9 such events has "
              "coincided with Sunday (2026-09-06). Not a deterministic future date -- flagged "
              "as a standing risk on every week's 03:00-03:02 window, whatever else is "
              "scheduled there, not counted in the overlap total above.")


if __name__ == "__main__":
    main()
