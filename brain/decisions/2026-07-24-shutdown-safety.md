# Shutdown safety — 2026-07-24, ~2 weeks offline

Investigation only, read-only checks against the running system. Nothing executed. See `brain/decisions/2026-07-24-shutdown-state-of-play.md` for the project-state companion doc.

## 1. Are services safe to stop mid-cycle?

**Yes.** Checked the two workers most likely to be mid-write at any given moment:

- **`background_backfill_worker.py`** (historical trade backfill, runs inside the monitoring process) — processes one trader per iteration, `conn.commit()` per trader after that trader's trades are inserted. A kill mid-trader loses at most that one trader's uncommitted batch, which SQLite rolls back automatically on the next connection (not torn state) — and the worker's `_build_batch()` query naturally re-selects that trader as still-pending next run. Resumable by design.
- **`background_pnl_worker.py`** — same pattern: "one connection, one commit for the batch" per trader.
- **`monitoring/main.py`** has an explicit shutdown-signal handler (`[SHUTDOWN] Received shutdown signal...`), so a graceful `systemctl stop` / `scripts/kill_all.py` (uses `proc.terminate()`, i.e. SIGTERM, not SIGKILL) lets in-flight work finish its current commit boundary before exiting.
- `polymarket-observer` has `TimeoutStopSec=30` set explicitly; `polymarket-monitoring` and `trading-swarm` use systemd's default timeout (SIGTERM, then SIGKILL after the timeout if it hasn't exited) — sufficient given the per-trader commit granularity above.

**Clean stop sequence:** `python scripts/kill_all.py` (stops monitoring + observer, cleans PID files) + `sudo systemctl stop trading-swarm`. No special care needed beyond not stopping mid-transaction in a way SQLite/WAL doesn't already handle — it does.

## 2. Live/forward data capture gap

Confirmed nothing **breaks** from a 2-week gap — it's simply 2 weeks of B4 order-book snapshots and live monitoring data not captured, permanently (as CLAUDE.md already notes for the April 2026 trade gap: unrecoverable, not backfillable from the API after the fact). No mechanism tries to reconstruct historical order-book state after the fact.

**Resumption is NOT a catch-up thrash, for two independent reasons:**
- The monitor polls **current state** each cycle (current positions, current trade history via the API), not a "since last successful poll" delta — so on restart it just resumes normal 15-minute-cycle polling of live state. It does not attempt to reconstruct the 2 weeks of missed intervals.
- `fast_resolution_check.py` (the "Fetch new market resolutions" maintenance step) re-fetches the **entire currently-closed-market list** from the API every run (up to a 50,000-market safety cap) and diffs against the DB — this payload size is a function of Polymarket's total closed-market count, not of how long the gap was, so it costs the same whether run daily or after 2 weeks.
- `requeue_resolved_market_traders.py` (newly-resolved → reset pnl_last_updated) is a bulk `UPDATE ... WHERE trader_address IN (...)` against however many traders newly qualify — a bigger IN-list after a gap, but still a single set-based statement, not a per-row loop; SQLite handles this in seconds even at high multiples of normal volume.
- `run_stale_clob_pass` is explicitly capped at 200 markets/run regardless of backlog — a larger backlog just means more days to fully drain, not a single-run blowup.

**T2 "pending on resolved" context:** already observed swinging 0 → 111,913 day-to-day under *normal* daily operation this month (see today's session-start check) — a 2-week accumulation is very unlikely to be qualitatively different in kind from swings the harness already tolerates, though the absolute newly-resolved-market count on the first run back will likely be at the high end of that range. Worth eyeballing the first post-restart `daily_maintenance.log` banner and runtime rather than assuming it's silently fine, but nothing in the code paths above suggests a design that would hang or corrupt state under higher volume — only take longer.

**Recommendation:** let the first maintenance run go on its normal 6am cron schedule rather than manually forcing a catch-up run immediately on power-on — there's no unbounded-blowup risk to preempt, and running it unattended once services have stabilized post-boot is simpler than trying to time a manual run.

## 3. Cron on a powered-off box

All cron jobs (3am backup, 6am maintenance, weekly agents) simply don't fire while off — confirmed no jobs specifically fire "the moment the box comes back" or make up for missed runs (no `anacron`-style catch-up configured). First real activity after power-on is whatever's next in the crontab, e.g. the following day's 3am backup / 6am maintenance if boot happens outside those windows.

## 4. Backups — confirmed fresh, both layers

- **Local:** `data/backups/polymarket_tracker_2026-07-24.db` (15G), completed 2026-07-24 03:08 UTC, exit 0, retention keeping 3-5 days. **This predates tonight's session work** — the `event_cluster_labels` and `backtest_population_snapshots` tables (created this evening) are NOT yet in any local backup file.
- **Offsite (O-14):** ran 2026-07-24 02:03:57 UTC, completed successfully, `/mnt/backup` autofs mount confirmed active and mounted (`/dev/sda`, ext4), 51G used, 14-day pruning working. Same "predates tonight" caveat applies to the trading-swarm brain backup component too, though brain/ is git-tracked and pushed separately (see state-of-play doc's commit hashes) so that part is recoverable from git regardless.

**Action needed before power-off: run `python scripts/backup_database.py` once more** to capture a backup that includes tonight's new tables (WAL-safe online backup API + `PRAGMA integrity_check`, per the O-7.1 fix — safe to run against a live DB, no need to stop services first).

## 5. WAL checkpoint

Checked twice this session (20:49 and 20:50 UTC): `polymarket_tracker.db-wal` is **0 bytes** both times — already clean/checkpointed, not accumulating. The system appears to checkpoint aggressively already (daily_maintenance's own "WAL checkpoint" step ran `OK — 0|0|0` this morning per the session-start check).

**Action needed before power-off: run `PRAGMA wal_checkpoint(TRUNCATE);` once, right before stopping services**, as a final explicit confirmation rather than relying on it already being clean — cheap, and guarantees no bloated/torn WAL file across the 2-week gap regardless of what the last few minutes of activity before shutdown do to it.

## Recommended sequence (not yet executed — for your confirmation)

1. `python scripts/backup_database.py` — fresh local backup including tonight's new tables.
2. Confirm exit 0 / `PRAGMA integrity_check` passed.
3. `python scripts/kill_all.py` — stop monitoring + observer cleanly.
4. `sudo systemctl stop trading-swarm`.
5. `sqlite3 data/polymarket_tracker.db "PRAGMA wal_checkpoint(TRUNCATE);"` — confirm `0|0|0` result.
6. `sudo systemctl status polymarket-monitoring polymarket-observer trading-swarm` — confirm all three inactive.
7. Power off.

No destructive or write action taken as part of this investigation.
