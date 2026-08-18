# Today's outage scope — 2026-08-18

**Read-only.** No repair, backfill, or pipeline re-run performed. This document establishes facts; it does not diagnose root cause or remediate.

**Evidence-tagging convention used throughout:** every claim is marked **[VERIFIED: <source>]** (a command, query, or file:line that establishes it directly) or **[INFERRED: <basis>]** (a reasonable but not directly-observed conclusion). Where something could not be settled at all, it is marked **[UNVERIFIABLE-HERE: <what would settle it>]**. Ad-hoc query results that would carry a project decision are marked **(ad-hoc, not yet reproducible via a committed script)**.

**On the prompt's own claims:** per the standing project rule (verify claims, including ones stated in the task itself), each assertion in the originating task — "went down at some point today," "restarted manually by Oscar," "not detected by any alert," "not reflected in today's census," and "yesterday's 13.7-day outage" — was checked rather than assumed. Results below; two needed correction or partial correction (marked inline).

---

## (a) Exact down-window

**Down 2026-08-18 14:45:50 UTC → 16:19:04 UTC, duration 1h 33m 14s (1.554 hours). [VERIFIED]**

- `journalctl --list-boots`: boot `-1` (`9f37d596...`) last entry `Tue 2026-08-18 14:45:50 UTC`; boot `0` (`b456b133...`) first entry `Tue 2026-08-18 16:19:04 UTC`. **[VERIFIED: `journalctl --list-boots`]**
- Corroborated: `polymarket-monitoring`'s own `pnl_worker` log shows batch-start entries every ~12s up through `14:45:50,236` with nothing after in that boot. **[VERIFIED: `journalctl -b -1 --since "2026-08-18 14:45:00"`]**
- The prior boot ended **uncleanly**, not via a graceful shutdown: on boot `0`, `systemd-journald` logs *"File .../system.journal corrupted or uncleanly shut down, renaming and replacing"* and `systemd-fsck` reports *"/dev/nvme0n1p2: recovering journal"* (an ext4/similar journal replay, i.e. the filesystem itself wasn't unmounted cleanly). **[VERIFIED: `journalctl -b 0`]** No `shutdown`/`poweroff`/`systemctl` command appears anywhere in boot `-1`'s log in the minutes before the cutoff. **[VERIFIED: `journalctl -b -1 --since "2026-08-18 14:40:00" | grep -i shutdown/poweroff/systemctl` → no hits]**
- **On "restarted manually by Oscar":** the *mechanism* of going down (abrupt/unclean, not a graceful shutdown command) is verified above. **Who** physically power-cycled the machine, and whether that was Oscar, is **[UNVERIFIABLE-HERE]** — no log source available in this investigation records operator identity for a power-button event; `last -x` shows no interactive session was open on the machine at 14:45:50, and the next login (`pts/0` from `192.168.1.192`) appears at `16:22`, two minutes after boot, consistent with someone logging in shortly after power-on but not proving who flipped the switch. Settling this would require asking the person directly, or physical/badge/camera records outside this system.
- **Observed but not diagnosed:** boot `-1`'s `polymarket-observer` log shows a burst of 8 `[OBSERVER] Error detected: generic_error` lines all timestamped `14:26:48`, ~19 minutes before the last log entry. This is noted as a preceding anomaly only; no root-cause investigation was performed (out of scope). **[VERIFIED: `journalctl -u polymarket-observer --since "2026-08-18 14:00:00" --until "2026-08-18 17:30:00"`]**

---

## (b) Did today's `daily_maintenance.py` run before or after the outage

**Before — entirely. [VERIFIED]**

- `logs/daily_maintenance.log`: run started `2026-08-18 06:00:01`, finished `[2026-08-18T09:21:19Z]`, exit 0, 31/33 steps OK. **[VERIFIED: `grep 2026-08-18 logs/daily_maintenance.log`]**
- 09:21:19Z is ~5.4 hours before the down-window began (14:45:50). The maintenance run, its pre-ELO integrity gate pass, and its 31/33 step result **say nothing about the system's state between 09:21 and the outage, during the outage, or after recovery** — no maintenance run (and therefore no integrity gate, no ELO/order-book snapshot, no resolution sweep) has executed since. The next scheduled run is tomorrow 06:00 UTC.
- The census document's fingerprint **counts** (traders/trades/positions/markets) were pulled via live `SELECT` queries close to the doc's file-mtime, `2026-08-18 18:01:55 UTC` **[VERIFIED: `stat -c '%y' brain/decisions/2026-08-18-system-state-census.md`]** — i.e. **after** the 16:19:04 recovery, not from the 09:21 maintenance run. So: the *counts* in the census are current/post-outage; the *maintenance-health narrative* ("clean, 31/33, integrity gate passed") describes a run that predates the outage and has not been re-validated since. Reading "maintenance ran clean today" as covering the whole day, including after 14:45, would be an unsupported inference — **[INFERRED-risk flagged, not stated as fact in the census]**.

---

## (c) Ingestion loss — outage window vs. neighboring windows

Windows sized to match the outage duration (1h33m14s) exactly, immediately before and after:

| Window | Trades (event `timestamp`) | Positions (`entry_timestamp`) | Markets (`resolution_date`) |
|---|---|---|---|
| before: 13:12:36–14:45:50 | 41 | 0 | 0 |
| **outage: 14:45:50–16:19:04** | **18** | **0** | **0** |
| after: 16:19:04–17:52:18 | 2 | 0 | 0 |

**[VERIFIED via ad-hoc SQL against `data/polymarket_tracker.db` — ad-hoc, not yet reproducible via a committed script]**

All 18 outage-window trade rows are `data_source ∈ {background_backfill (16), polymarket_api (2)}` — **zero** live-monitoring-timestamped rows, as expected since the box was off. **[VERIFIED]**

Reading the raw counts alone is weak evidence either way: overall trade volume in this system is already low and declining (the "after" window's 2 trades in 93 minutes is *lower* than the outage window's 18, showing the same kind of pre-existing-trend confound the 2026-08-17 outage doc found for the 14-day gap — a short window this small is dominated by which few traders happened to get caught up when, not a clean measure of "recovery rate"). **[INFERRED, by analogy to the 08-17 doc's Part 5 boundary-check methodology, not independently re-derived at scale here]**

Zero positions and zero market-resolution-date rows fall inside the window in any of the three windows — **[VERIFIED]**, though note `resolution_date` is separately documented as write-time/COALESCE-backfilled and LATE-biased (see memory `project_o36_resolution_date_reliability`), so absence-of-evidence here is suggestive, not conclusive, for (d) below.

---

## (d) Did any market resolve during the down-window

**No detectable resolution activity in or immediately after the window. [VERIFIED, with the caveat above]**

- Zero markets have `resolution_date` inside `14:45:50–16:19:04`. **[VERIFIED, ad-hoc query]**
- Zero markets have `last_checked` inside the outage window (expected — box off) **or** in the 93 minutes immediately after recovery (`16:19:04–17:52:18`) **with `resolved=1`** — meaning `fast_resolution_check.py` has not run since the outage (it's a `daily_maintenance.py` step, next due tomorrow 06:00). **[VERIFIED, ad-hoc query]**
- This is consistent with the 2026-08-17 doc's classification of the resolution-sweep step as **self-healing / not time-windowed** (it bulk-scans *all* currently-resolved markets via Gamma, not a recency-limited feed) — a resolution that occurred in real-world terms during this 93-minute window, if any, would simply be picked up at the next maintenance run rather than lost. **[INFERRED, by the same mechanism already verified in the 08-17 doc; not independently re-confirmed by reading `fast_resolution_check.py` in this pass]**
- Net: no evidence of a resolution-detection loss for this window, and the mechanism that would eventually catch it either way is not time-limited. Given the short duration, permanent loss here is unlikely but **[UNVERIFIABLE-HERE]** in the strict sense — confirming zero real-world resolutions occurred in this exact 93-minute span would require an external, point-in-time source (e.g., UMA/Gamma resolution timestamps as of that moment), not available read-only from this DB.

---

## (e) Recovery since restart, and the backfill-eligibility split

**Partial correction to the task's framing: already-known traders were NOT all excluded from recovery for this short gap — see below. [VERIFIED]**

`background_backfill_worker.py::_build_batch()` (read directly, current code) confirms the documented behavior is unchanged:
```sql
SELECT address FROM traders
WHERE is_flagged = 1 AND research_excluded = 0
  AND (SELECT COUNT(*) FROM trades WHERE trader_address = traders.address) = 0
  AND backfill_attempted IS NULL
```
Only ever selects a trader with **zero** trades currently in the DB. **[VERIFIED: `monitoring/background_backfill_worker.py` / `scripts/background_backfill_worker.py`, `_build_batch()`]**

Of the **7 distinct traders** with a trade whose event-timestamp falls inside the outage window:

| Class | Count | Mechanism |
|---|---|---|
| Zero-trades before today, `backfill_attempted` stamped **today between 16:22–16:42** | **5** | `background_backfill_worker.py` — full-history fetch, incidentally covers the gap |
| Already had trades before today (`backfill_attempted` from 2026-05-24 and 2026-08-10) | **2** | **Not** `background_backfill_worker` — see below |

**[VERIFIED: ad-hoc query joining `trades`/`traders` — ad-hoc, not yet reproducible via a committed script]**

For the 2 already-known traders, the outage-window trades were **not** produced by the zero-trade backfill path. Directly observed instead: `monitoring/monitor.py::check_for_new_trades()` uses a cursor (`after_timestamp=self.last_trade_timestamp`) against `get_market_trades()` and filters for **all currently-flagged traders**, not just zero-trade ones. **[VERIFIED: `monitoring/monitor.py:808-854`]** The live log confirms this ran immediately on recovery:
```
16:21:42  Fetching recent trades from Polymarket...
16:21:46  [OK] Fetched 500 recent trades
16:21:46  Found 5 trades from flagged traders
```
**[VERIFIED: `journalctl -u polymarket-monitoring --since "2026-08-18 16:19:00" --until "2026-08-18 17:00:00"`]**

**This is a real, evidence-based distinction from the 2026-08-17 doc's finding**, not a contradiction of it: that doc found `background_backfill_worker` was the *sole* source of recovered trades for the 13.7-day gap specifically, implying the ordinary cursor-catchup could not reach that far back (most plausibly because the "recent trades" feed has a retention/window boundary well under 13.7 days). For this **93-minute** gap, the same cursor mechanism evidently still had the whole window in reach and caught up both already-known and newly-discovered traders. **[INFERRED: the retention-boundary explanation is plausible and consistent with observed behavior at both timescales, but the exact retention window of `get_market_trades()` was not read from its implementation or documentation in this pass — [UNVERIFIABLE-HERE] for the precise boundary; would need reading `polymarket.get_market_trades()`'s API-side behavior/docs.]**

**Residual uncertainty:** the 16:21:46 fetch returned exactly the fetch cap (500 trades) — **[UNVERIFIABLE-HERE]** whether platform-wide trade volume during the 93-minute gap exceeded 500 (which would mean the single fetch didn't reach all the way back to 14:45:50 and some older trades in the gap could still be pending a further cursor advance, or silently unreachable if the feed doesn't support deep pagination). Settling this would require comparing against Polymarket's own trade volume for that window, an external source not queried here.

---

## (f) Did anything log, alert, or surface the outage

**No box-down/outage-specific alert fired, during or after — confirmed as expected. [VERIFIED]**

- `polymarket-observer`'s ELO-staleness check (the same proxy the 2026-08-17 doc found fires *retroactively* for long gaps) shows `last recalc 2026-08-18 (0 day(s) ago)` after this outage **[VERIFIED: `journalctl -u polymarket-observer --since "2026-08-18 14:00:00"`]** — because today's full ELO recalc already ran at 06:00–09:21, *before* the gap. This proxy is **day-granularity** and cannot detect a sub-day gap regardless of duration; it would not have fired for this outage even if checked deliberately.
- No box-down, maintenance-staleness, or ingestion-stall alert exists in the codebase (confirmed separately by today's census, item 2, via `grep -rl` across `first-repo` — not re-run here, taken as already current since nothing suggests it changed in the last few hours).
- One incidental failure was logged, not alerted: `Telegram send failed: <urlopen error [Errno -3] Temporary failure in name resolution>` at `16:19:08`, one second after boot — the network wasn't up yet when the monitoring service's startup tried to notify. This produced a log line only; nothing paged or surfaced it as a signal that anything unusual had happened. **[VERIFIED: `journalctl --since "2026-08-18 16:19:00"`]**
- Net: the task's premise "not detected by any alert" is **confirmed true** for this outage.

---

## (g) Does the census fingerprint need re-taking

**No re-take needed for the raw counts; the maintenance-health framing needs an explicit caveat. [VERIFIED / recommendation, not a re-run]**

- The census's numeric fingerprint (traders/trades/positions/markets/etc.) was queried live at ~18:01 UTC, **after** the 16:19:04 recovery and after the post-recovery catch-up activity (16:19–17:2x) had already run. Those counts are current as of ~18:01 and don't need re-measurement on account of this outage. **[VERIFIED, per (b) above]**
- What **should** be added to the census (as a correction/addendum, not a re-run) is the caveat established in (b): the "maintenance ran clean, 31/33, pre-ELO gate passed" statement describes a pre-outage run and does not attest to anything after 09:21:19Z, including the outage itself. As written, the census doesn't claim otherwise, but a reader could easily over-extend "today's maintenance was clean" to "today was clean" — it wasn't; there was a 93-minute unplanned outage the maintenance run has no visibility into.
- Tomorrow's 06:00 UTC `daily_maintenance.py` run will be the first maintenance-level check (integrity gate, resolution sweep, ELO/order-book snapshots) to execute since this outage. Nothing about that is broken or needs acceleration — it's the system's normal next checkpoint.

---

## Relationship to "yesterday's 13.7-day outage"

**Different event, correctly attributed to a prior document, but the duration figure itself doesn't hold up under recomputation. [VERIFIED / CORRECTED]**

- The "13.7-day outage" is not something that happened "yesterday" (2026-08-17) — it's a **prior** outage (machine off 2026-07-24 21:46:17 UTC → 2026-08-07 09:37:02 UTC) that was **documented** yesterday, in `brain/decisions/2026-08-17-maintenance-outage-scope.md` and `2026-08-17-session-summary.md`. The task prompt's phrasing is ambiguous but this is almost certainly what it meant, and the underlying claim (a 13.7-day outage exists and was characterized) **is well-supported** — `2026-08-17-maintenance-outage-scope.md` is a detailed, evidenced document (not a bare assertion). **[VERIFIED: file exists, 195 lines, boot-log-sourced]**
- However, recomputing that boot gap directly from `journalctl`'s own boundary timestamps gives **13 days, 11:50:45 = 13.494 days**, not 13.7 days. **[VERIFIED: `python3` datetime diff on the exact boot-list timestamps, cross-checked against the same boot-list output used here]** The 13.7 figure appears in both 2026-08-17 documents and is off by about 0.2 days (~5 hours) from what the underlying boot timestamps actually compute to. This is a minor, likely-rounding discrepancy, not investigated further (root-causing a stale rounding in a prior doc is out of scope for this task), but is flagged per the standing instruction rather than silently propagated.
- **Shared cause: cannot be determined from available evidence, and there is no positive evidence they share one.** The two events differ in almost every observable respect: the July/August gap was ~13.5 real days with no boot-log entries at all in between (consistent with the machine being fully powered off, e.g. for the documented server migration/parallel-run period referenced elsewhere), while today's gap is 93 minutes with an unclean-shutdown/journal-recovery signature (crash or abrupt power loss, not an extended deliberate power-off). Nothing in either boot record or either outage's logs points to a common trigger. **[VERIFIED: absence of any linking log entry, ad-hoc / not exhaustive]** Settling "no shared cause" with confidence (rather than "no evidence found of one") would require knowing the physical/infrastructure cause of both events, which isn't recorded in any log available to this investigation — **[UNVERIFIABLE-HERE]**.

---

## Summary

| # | Question | Answer |
|---|---|---|
| a | Down-window | 2026-08-18 14:45:50 → 16:19:04 UTC (1h33m14s), unclean shutdown, restart operator unverifiable |
| b | Maintenance vs. outage | Maintenance ran 06:00–09:21, entirely before; census counts queried after recovery, maintenance-health narrative predates outage |
| c | Ingestion loss | 18 trades event-timestamped in-window, all backfill-sourced (no live rows, as expected); comparison to neighboring windows is weak evidence given low overall volume |
| d | Resolution during window | None detected; resolution-sweep mechanism is not time-windowed, so any missed resolution self-heals at next maintenance run |
| e | Recovery mechanism | 5/7 in-window-active traders recovered via zero-trade `background_backfill_worker`; 2/7 already-known traders recovered via ordinary live-monitor cursor catchup (a real distinction from the 13.7-day-outage doc's finding, not a contradiction — short gaps stay within the live feed's reach) |
| f | Detection | Confirmed: no box-down/outage alert exists or fired; ELO-staleness proxy is day-granularity and wouldn't have caught this regardless |
| g | Census re-take | Not needed for the counts; the maintenance-clean framing needs the pre-outage caveat noted above |
| — | Shared cause with 13.7-day outage | No evidence of a shared cause found; that figure itself recomputes to 13.494 days from the same boot-list data, ~0.2 days off from the documented "13.7" |
