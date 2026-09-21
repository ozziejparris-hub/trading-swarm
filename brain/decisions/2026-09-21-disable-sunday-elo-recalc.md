# Disable the Sunday ELO recalc — archive, composite-reach settlement, and reversible timer disable

**Date:** 2026-09-21. Corpus content extraction (PID 102652) confirmed running throughout — start
(4:12:49 elapsed) and end (4:43:28 elapsed, 130 processed / 6 timed out and flagged, not stalled) — never
touched.

**Outcome:** archive verified and committed (Part 1); the composite found to reach nobody, correcting
this session's own earlier characterization (Part 2, no stop condition); `polymarket-sunday-elo.timer`
stopped and disabled, reversibly (Part 3); nothing else moved, confirmed (Part 4); the freeze recorded in
`CLAUDE.md` (Part 5); Monday's checklist below (Part 6).

---

## Part 1 — archive, verified before anything else

**Exported** (`data/characterizations/elo_behavioral_columns_archive_20260921T204800Z.json`, first-repo
commit `41d68e5`): `address, timing_score, patience_score, kelly_alignment_score, behavioral_modifier,
advanced_modifier, elo_last_updated` for every trader carrying any of the five — **203,677 rows**
(`behavioral_modifier`/`advanced_modifier` are populated near-universally; the practically meaningful
subset with a real `timing_score`/`patience_score`/`kelly_alignment_score` is 46,423/44,470/42,600
respectively — both figures reported, not just the larger one).

**Confirming the values are from the 2026-09-20 Sunday recalc — the task's own instruction to verify
rather than assume turned up a real trap.** `elo_last_updated` is **not** a reliable per-row timestamp for
"when these five columns were last computed" — it is bumped by the *daily* `apply_full_elo_modifiers.py`
step even when that step changes nothing about these five columns. Confirmed **empirically**, not just by
re-reading the code from `47704b0`: decompressed the 2026-09-21 02:04 UTC offsite backup (captured before
that day's Writer B run) and diffed it against the live table for every trader with a real behavioral
score.

| | result |
|---|---|
| rows compared | 46,423 (all traders with a non-NULL `timing_score`/`patience_score`/`kelly_alignment_score`) |
| `timing_score`/`patience_score`/`kelly_alignment_score`/`behavioral_modifier`/`advanced_modifier` differences | **0 / 46,423** |
| `comprehensive_elo` differences | 201 / 46,423 (expected — Writer B refreshes this daily from P&L) |
| `elo_last_updated` differences | 43,879 / 46,423 (confirms the column is touched daily regardless) |

The **true** last-computed time is independently verified from `logs/sunday_elo.log` (first-repo), quoted:

```
[2026-09-20T03:00:01Z] Starting Sunday ELO recalculation
...Started: 2026-09-20 03:00:03
[ELO_BRIDGE] Full ELO recalculation complete: 41327 updated, 0 failed in 10463.89s (174.4 min)
...Completed: 2026-09-20 05:54:26
[2026-09-20T05:54:33Z] Sunday ELO recalculation complete
```

**Confirmed: 2026-09-20, 03:00:03–05:54:26 UTC, 41,327 traders updated.** The archive's provenance block
records this explicitly and flags `elo_last_updated` as unreliable for this purpose, so a future reader of
the archive doesn't fall into the same trap.

**Provenance embedded in the artifact:** export time (2026-09-21T20:48:00Z), source DB path, the first-repo
commit active at export time (`42d241a`), row count, `sha256_of_rows` (hash of the row data only, computed
independently of export time so it's reproducible from any re-export of the same underlying data), and the
`logs/sunday_elo.log`-verified last-computed record above.

**Verification, before committing:**
1. **Hash reproduces** — recomputed `sha256(json.dumps(rows, sort_keys=True))` from the archived rows and
   it matches the stored `sha256_of_rows` exactly.
2. **20/20 random spot-checks** against the live table match exactly (seeded `random.seed(42)` for
   reproducibility of the check itself).
3. **Row count**: archive has 203,677; a live re-query minutes later returned 203,680 (4 more) —
   **investigated, not waved away**: all 4 are traders with `first_seen` timestamps 20:48:55–20:49:14 UTC,
   seconds after the 20:48:00 export, ingested live by the continuously-running monitor with the default
   `behavioral_modifier=1.0, advanced_modifier=1.0, timing_score=NULL`. Explained drift from a live system
   between two point-in-time reads a few minutes apart — not a defect in the archive itself, and not a
   sign any *existing* row's data is wrong (every row that IS in the archive is byte-for-byte verified
   above).

**Verification passed. Not a stop condition.** Archive committed (first-repo `41d68e5`, pushed).

---

## Part 2 — where the composite actually goes (settled)

**Correction to this session's own 2026-09-21 report (`47704b0`): the composite does not reach Telegram.**
Traced the exact code path, not re-stated from memory:

- `analysis_scheduler.py::run_full_analysis()` does call `run_phase_3b_composite_scores()` unconditionally
  ("Phase 3b: Composite scores (always run — graceful degradation)", `analysis_scheduler.py:1323-1324`) —
  so the computation genuinely runs live, daily, at 01:00 UTC, confirming that part of `47704b0`.
- It writes `reports/composite_scores_{today}.csv` (`analysis_scheduler.py:1016`).
- **`system_observer.py::_run_analysis_scheduler()`'s report-discovery step globs for exactly three
  filename patterns**: `unified_analysis_{today}*.txt`, `top_opportunities_{today}*.txt`,
  `trader_rankings_{today}*.txt` (`system_observer.py:2674-2678`) — **`composite_scores_*.csv` is not
  among them.** The file the composite writes is never matched, never added to `results['reports_generated']`,
  and therefore never named in the Telegram "Reports Generated" list.
- **`generate_unified_report()`** — the method that builds the text later parsed into the Telegram
  message's "KEY INSIGHTS" section — contains **zero references to `composite_scores` anywhere**
  (confirmed by direct search of the method and the whole file; the only occurrences of the word
  "composite" in `analysis_scheduler.py` are inside `run_phase_3b_composite_scores()` itself, writing the
  CSV, and one unrelated docstring comment).
- The unified report's own "trader_rankings" section (which *does* reach Telegram) is sourced from
  `self.results.get('performance')` — Phase 2's separate Trader Performance Analysis, sorted by a field
  literally named `elo_rating`, not from Phase 3b's `composite_scores`. A different pipeline entirely.

**Answering the task's three questions directly:**
- **Does the composite reach Telegram today?** No. The unconditional daily send (confirmed still firing —
  `system_observer.py:678-703`, no gating beyond a basic sufficient-data check, unaffected by the 2026-09-09
  Telegram cut which did not address this loop at all) sends a message every day, but that message's
  content is built from a completely different code path with no knowledge the composite exists.
- **Does anything read the CSV?** No — matches the 2026-09-13 built-never-connected sweep's finding exactly.
- **Does anything else consume the composite?** No other consumer found this session, beyond the
  in-memory `self.results['composite_scores']` dict that dies with the process at the end of that day's
  run.

**This corrects `47704b0`'s "surfaced in the daily Telegram summary" characterization, which conflated
"the loop that computes it also sends an unconditional daily message" with "therefore the message contains
it" — verified false. Stated plainly per the task's instruction: the composite reaches nobody. Proceeding.**

No stop condition triggered.

---

## Part 3 — the Sunday timer, disabled reversibly

Stopped and disabled by the user (sudo required, this session cannot supply an interactive password) via:

```bash
sudo systemctl stop polymarket-sunday-elo.timer
sudo systemctl disable polymarket-sunday-elo.timer
```

**Verified, fully:**

```
$ systemctl is-active polymarket-sunday-elo.timer
inactive
$ systemctl is-enabled polymarket-sunday-elo.timer
disabled
$ systemctl list-timers --all | grep -c sunday-elo
0
```

- **Not masked, not deleted**: both `/etc/systemd/system/polymarket-sunday-elo.timer` (172 bytes) and
  `polymarket-sunday-elo.service` (385 bytes) still exist on disk, unmodified since 2026-05-31;
  `readlink -f` on the timer resolves to the real file, not `/dev/null` (which masking would produce).
- **`systemd-analyze`-equivalent confirmation nothing else triggers the service**:
  `systemctl show polymarket-sunday-elo.service -p WantedBy -p RequiredBy -p TriggeredBy` all returned
  empty, and `systemctl list-dependencies --reverse polymarket-sunday-elo.service` shows only the
  timer/service pair itself, nothing upstream.

**Re-enable procedure**, dated and reversible, matching the 2026-08-31 agent-pause pattern (`138c03b`):

> **Disabled 2026-09-21** (this decision). Reason: the only producer of `timing_score`/`patience_score`/
> `kelly_alignment_score`/`behavioral_modifier`/`advanced_modifier`, whose research role is closed
> (geo_elo condemned for skill-ranking 2026-08-15, tiers falsified as mispricing markers 2026-09-11) and
> whose only live decision-shaped consumer (the composite) reaches nobody (Part 2) — while its runtime
> growth (~8.8 min/week, R²=0.96) was about to collide with `run_daily_maintenance.sh` and was already
> starving `run_database_backup.sh` ~100x on the last two Sundays. **Reverse:**
> ```bash
> sudo systemctl enable --now polymarket-sunday-elo.timer
> ```
> Confirm with `systemctl list-timers | grep sunday-elo` showing a `NEXT` time. No code, schema, or data
> change is needed to reverse this — the timer, service, and `recalculate_comprehensive_elo.py` are all
> untouched.

`update_geo_elo.py`, Writer B, `analysis_scheduler.py`, and every other job: **not touched**, per scope.

---

## Part 4 — verify nothing else moved

**`update_geo_elo.py` remains scheduled**, unchanged:
`scripts/daily_maintenance.py:149`: `("Update geo ELO scores", SCRIPTS_DIR / "update_geo_elo.py", None, True)`
— still a daily step. `crontab -l`: `0 6 * * * .../run_daily_maintenance.sh` — unchanged, will fire
tomorrow at 06:00 UTC as always.

**Nothing checks for the Sunday job having run.** Searched for every reference to
`sunday_elo`/`SUNDAY_ELO`/`polymarket-sunday-elo` across `scripts/*.py` and `monitoring/*.py`: 4 hits, all
comments or an unconditional `print()` statement (`daily_maintenance.py:318,366`; `elo_bridge.py:483,584`)
documenting the relationship in prose — none is a check, none gates an alert, none would fail or behave
differently if the timer never fires again. Re-confirmed `audit_invariants.py::check_comp_elo_write_atomicity`
(the one check `47704b0` flagged as presence-only) directly: its `WHERE` clause is `IS NULL` on each
component column, no timestamp, no age comparison anywhere in the function. **No freshness check exists
anywhere in this codebase for the ELO behavioral columns** — confirmed, not just carried forward from the
prior report.

**Simulation re-run with the Sunday job removed**
(`scripts/sunday_schedule_simulation.py --layout elo_disabled`, new layout added this session, committed):
models the actual state as of today — timer disabled, nothing else changed, no chain/wait redesign (that
was Part 5 of `d45eea8`, never approved or deployed). `run_database_backup.sh (Sun)` reverts to the
weekday-typical runtime model in this layout, not the flat 201.5-minute starved figure `current_layout()`
uses — that figure was modeling exactly the concurrent-ELO starvation this removes; keeping it after
removing its cause would misrepresent the test.

**Result, 13 weeks (2026-09-27 → 2026-12-20): the Sunday DB-write cluster collapses to zero overlaps, at
every single week.** No ELO-vs-backup, no ELO-vs-maintenance, no ELO-vs-sweep, no backup-vs-maintenance —
all gone, exactly as expected. The only overlaps remaining, present at every week, are the pre-existing,
unrelated Monday-morning ones (`run_daily_maintenance.sh (Mon)` vs. `run_feedback_loop.sh`/
`run_changelog_monitor.sh`/`legendary_positions_scan.py`, all read-only or non-DB-touching against
maintenance's writes) — present in `current_layout()` too, not introduced by this change, already flagged
out-of-scope in `d45eea8`.

No consumer this task missed was surfaced by disabling the timer — the stop condition for this part is not
triggered.

---

## Part 5 — the frozen state, documented

`CLAUDE.md` (first-repo, commit `fc83c71`), Important Warning 6 (new):

> **`timing_score`, `patience_score`, `kelly_alignment_score`, `behavioral_modifier`,
> `advanced_modifier` are FROZEN as of the 2026-09-20 Sunday recalc** ... **Do not treat these five
> columns as live** — a query against them today returns exactly what was true on 2026-09-20, not
> "current." A full point-in-time archive (203,677 rows, hash-verified) is committed at
> `data/characterizations/elo_behavioral_columns_archive_20260921T204800Z.json` (commit `41d68e5`).
> Everything else ELO-related ... is on the independent daily `update_geo_elo.py` path and is UNAFFECTED.

Also corrected the now-actively-false "Full 6-dimensional recalculation runs automatically every Sunday"
line in the same file's stale "Current System State" section, which this session's own action superseded
— left uncorrected, it would have directly contradicted Warning 6 two sections later in the same document.

---

## Part 6 — what Monday 2026-09-28 must confirm

1. **`polymarket-sunday-elo.timer` did not fire.** `journalctl -u polymarket-sunday-elo --since "2026-09-27 00:00" --until "2026-09-27 06:00"` should show nothing (or only the disable-time entries from today); `systemctl status polymarket-sunday-elo.service` should show no new `Active:`/`Main PID:` entry dated 2026-09-27. `last reboot -F` unaffected either way — the timer being off doesn't touch reboot behavior.
2. **`run_database_backup.sh` completed in minutes, not hours.** `logs/backup.log`: Sunday 2026-09-27's `Starting`/`Finished` pair should show single-digit-to-low-double-digit minutes, not the 180.6–201.5-minute pattern of the last two Sundays — the direct, checkable prediction of the starvation-removed hypothesis.
3. **`run_daily_maintenance.sh` started at 06:00 with no overlap.** `logs/daily_maintenance.log`: `Starting daily-maintenance` at `06:00:0X`, no `SKIPPED` line (the `bfdf9d6` guard should have nothing to refuse against, since nothing should still be running from 03:00/03:30 by then).
4. **The five archived columns unchanged from the archive.** Spot-check a handful of addresses from
   `data/characterizations/elo_behavioral_columns_archive_20260921T204800Z.json` against the live table —
   should match exactly, the same way this session's own 20/20 check did. A change would mean something
   this task missed is still writing to these columns.
5. **The corpus run's maintenance guard, if still running.** PID 102652 is expected to finish well before
   2026-09-27 (projected 10.8–20.5h from its own launch report, `c7c94aa`/`bfdf9d6`-era estimate, started
   2026-09-21T16:16 UTC); if it is somehow still running that Sunday, confirm its
   `maintenance_in_progress()` log-tail heuristic correctly saw Sunday's `daily_maintenance.log`
   Starting/Finished pair and paused/resumed appropriately — unrelated to today's timer change, but worth
   checking together since it's the other piece of active Sunday-window infrastructure from this same
   week's work.

---

## Corpus run confirmation

- **Start of this task:** PID 102652, elapsed 4:27:13 — running.
- **End of this task:** PID 102652, elapsed 4:43:28, `{"processed": 130, "failed": 6}` (failures isolated,
  not a stall) — running, healthy, unaffected by anything in this task.
