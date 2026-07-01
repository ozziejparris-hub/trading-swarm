# 2026-07-01 Session Summary

## Theme
Unplanned **recovery + audit** day. Started as outage cleanup, became a systematic hunt that surfaced multiple silent data-integrity issues.

**Two lessons to carry forward:**
1. "Show me the WHERE clause + count before any mutation" caught a 60-row corruption tonight (see O-17 backfill scoping below).
2. Multi-writer audits ("which scripts write column X, do they *all* follow convention?") are high-value and should be done proactively — they found real bugs twice today (O-17 writers, O-16 generator-dead confirmation).

---

## Recovery (morning)

- Second power outage in 4 days (02:54–07:26 UTC), unclean shutdown. DB integrity confirmed OK, WAL clean, no data loss.
- Both morning cron jobs (3am backup, 6am maintenance) missed — box was down/rebooting.
- Local backup: ran manually, current (`polymarket_tracker_2026-07-01.db`).
- **O-14 RESOLVED — offsite backup fixed.** `/mnt/backup` had been silently unmounted for 12 days (since June 20). Root cause: ext4 label hard-capped at 16 chars; fstab expected `LABEL=polymarket-backup` (17 chars) — disk label got truncated to `polymarket-backu`, so mount-by-label silently no-op'd (exit 0, nothing mounted) through 3 reboots. Fixed by switching fstab to `UUID=299b7d20-68a9-40c3-b3ee-513529ee689b` (backed up `/etc/fstab` first). Confirmed mounted (916G/850G free), offsite backup ran end-to-end. **Follow-up:** confirm auto-mount survives next reboot.

---

## Investigations (read-only, design-ready for next session)

**O-13 — monitoring blocking-call stall — FULLY SCOPED**
(doc: `2026-07-01-o13-monitoring-blocking-stall-design.md`)
- `check_market_resolutions` runs sync inside the async loop, blocking the monitor ~82% of every 2.5h cycle (~10.4h full scan, 95 starts vs 21 completions).
- Not just redundant — **mechanically broken**: looks up by condition-id which Gamma 422s; outcome-parser expects the old dict format and crashes silently. Zero resolutions since 2025-12-11.
- **Recommendation:** remove the call (not async-ify). §5b removal-safety checklist CLOSED — no working collection path lost.
- Second blocking call, `scan_for_successful_traders`, needs **offload**, not removal.
- Implementation-ready for next session.

**O-16 — resolution under-collection — QUANTIFIED**
(doc: `2026-07-01-o16-resolution-collection-gap-quantified.md`)
- 194,216 markets stuck `resolved=0`/`resolution_date` NULL.
- **Static** — 99.9995% traced to the 2025-12-11 `historical_backfill` bulk import. Generator proven dead via the 05-31 co-write commits `4cdd190`/`446bcde`. Not a live leak.
- Affects 85% of the clean trader pool.
- Backfill designed: per-ID Gamma lookup, ~2.6–5hr, resumable, tag `data_source='gamma_backfill'`, prioritize the 62,407 flagged-trader markets first.
- Separately found: Gamma list endpoint now 422s past offset ~2,100 (not the assumed 50K) — Pass 1 under-reaches, but this does **not** explain the backlog.
- Fix-this-week, not urgent.

---

## Fixed tonight

**O-17 — resolution_date co-write leak — RESOLVED (first-repo `a0e0870`)**
The *active* leak, higher priority than the static 194K from O-16.
- Full audit of 12 resolution writers found 7 broken across 3 files (`run_recent_overdue_pass`, `run_stale_clob_pass`, `run_external_seed_pass` in `fast_resolution_check.py` + both legendary scripts) — all written 9–14 days after the 05-31 co-write convention, so never inherited it.
- These writers resolve markets but never write `resolution_date`, silently breaking `requeue_resolved_market_traders.py` — those traders never get P&L-recalc'd.
- **Fix:** 5 COALESCE diffs / 7 write paths (bound to the same `datetime.now()` source the working writers use) + backfilled the stuck rows.
- **Critical scoping catch:** the naive backfill (`resolved=1 AND resolution_date IS NULL` = 182 rows) would have corrupted 60 pre-bug rows (55 from the 2025-12-11 import where `last_checked` is the import time, off by months from the real resolution date). Corrected via `AND last_checked >= '2026-06-05'` (earliest buggy-pass deploy date) → 122 genuine rows.
- **Verified:** 122 populated, 60 untouched (byte-identical to backup), 0 remaining in-window. 11 new tests including a real downstream requeue-visibility proof, 48/48 passing.
- **Deferred:** shared `mark_market_resolved()` helper — 7 call sites have different connection shapes, this is a real refactor, not mechanical.

**O-18 — LEDGERED (the 60 excluded rows)**
Distinct root cause (INSERT-time gap in the historical importer, connected to O-16 by the shared 2025-12-11 signature) — **not** the co-write bug. Do NOT blanket-backfill with `last_checked`. Needs its own investigation.

---

## Also note (minor, for the ledger)

- Maintenance did **not** complete today: morning run died at step 11 on the outage; evening manual re-run hung 80min on a maker/taker RPC call with no effective timeout at step ~24, killed cleanly (DB confirmed OK, no mid-write). Late steps (maker/taker enrichment, test-suite step, WAL checkpoint, market-date backfill) didn't run — idempotent, will re-run. **Watch tomorrow's 06:00 run completes cleanly** (2 interrupted runs in a row).
- The hung-RPC-with-no-timeout is a robustness gap worth its own item — a single hung call shouldn't freeze the whole pipeline.
- O-15 was an honest placeholder — a `pnl_worker` naive/aware datetime bug (`background_pnl_worker.py:410`, self-limiting via the `pnl_skip` circuit breaker, ~1,504 addresses since April 23) was referenced but never actually ledgered; recorded now so it isn't lost again.

---

## State for next session

- Both repos clean/pushed: first-repo `a0e0870`, trading-swarm `911e832`. Services active.
- Backups: local current, offsite fixed (UUID) + working.
- Ledger current: O-0 through O-18. Resolved this session: **O-14, O-17**.
- **Next-session menu** (all scoped): O-16 backfill (194K, needs a clean maintenance window), O-13 removal (implementation-ready), O-18 investigation (60 pre-bug rows), or the hung-RPC-timeout robustness fix. Plus the deferred O-17 shared-helper refactor.
- **First thing next session:** confirm tomorrow's 06:00 maintenance completed (2 interrupted runs in a row).
