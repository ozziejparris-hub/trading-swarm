# Session Summary — 2026-07-07

**Scope:** Morning orientation (Tier-2 backfill confirmed, O-15 trend, overnight health check) → Fable silent-failure audit (major deliverable, 7 classes, both repos) → independent verification of the audit's headline finding, severity-corrected → fix shipped (O-7.1) → backup-corruption discovered as a side effect of the fix's own safety step → read-only investigation into the real Stage-0a blocker → full ledger capture (O-19 through O-29) so none of today's backlog is lost.

---

## What shipped

| # | Item | Commit | Effect |
|---|---|---|---|
| 1 | Silent-failure audit banked | trading-swarm `a8c07f2` | 7-class systematic hunt across first-repo, trading-swarm, and their connection. Closes O-9 (swarm data-layer audit, folded into Class 6). Prioritized fix-now/harness/structural/needs-judgment backlog — see O-22 through O-29 below. |
| 2 | O-7.1 requeue gate fix | first-repo `f5fae64` | `requeue_resolved_market_traders.py` switched from an event-time gate (`resolution_date`) to a write-time gate (`last_checked`) — the O-16 backfills' historical resolution dates could structurally never pass the old gate. `legendary_positions_scan.py` co-stamp fix shipped alongside it (same class of gap, different writer, would have broken the new gate for its markets otherwise). `--force` run requeued 8,971 traders; worker confirmed processing them. |
| 3 | Ledger capture | trading-swarm (this session) | O-19 through O-29 added to the overhang ledger; O-9 closed; O-21 (=O-7.1) marked resolved with a severity correction noted. |

---

## The day's arc

### Morning: orientation, then a note that mattered later
Tier-2 O-16 backfill confirmed complete overnight (131,182/131,765 resolved, 2 errors, clean). O-15 self-heal trend checked: growth rate had crashed ~98% day-over-day (15,337/day → 300/day) but hadn't gone net-negative — correctly flagged as "not plateaued yet, watch it," which turned out to be exactly right (see below). No outage, maintenance completed cleanly, both services healthy. One overnight anomaly found and explained (unattended OS security upgrade bounced both services at 06:13 via `needrestart` — benign, self-recovered). One methodology note surfaced and reported but not acted on: `audit_invariants.py`'s timestamp check uses a majority-wins definition of "canonical" for `elo_last_updated`, not the contract's actual space-sep standard — this became Fable audit finding 5.1 hours later.

### Afternoon: the silent-failure audit
Elevated to Claude Fable for a systematic 7-class hunt (stored-but-unread columns, multi-writer drift, unbounded calls, swallowed exceptions, harness blind spots, the repo connection, silent scope-shrink) across both repos. Produced `2026-07-07-silent-failure-audit-FABLE.md` — three new ACTIVE findings (7.1 requeue miss, 2.5 manual-exclusion clobber, 7.7 category-backfill no-op) plus a prioritized action list. This closed O-9, which had sat open since session #38.

### Verification, not blind trust
Rather than act on Fable's headline finding (7.1) as framed, the next session independently re-verified it against live code and data before touching anything — per instruction. Confirmed the gate bug and its structural inevitability exactly as claimed. **Corrected the severity claim**: Fable's framing implied the O-16 backfill cohort was invisible to the O-15 drain entirely; tracing `background_pnl_worker.py`'s actual code found the ordinary 24-hour staleness rotation sweeps *all* traders regardless of this specific gate — it's a prioritization delay, not a structural block. Position counts on affected markets were already draining fast (more than halved within hours) before any fix landed. This changed the fix's urgency framing without changing whether it should be fixed.

### The fix, and what it surfaced
Implemented per the approved corrected scope: backup → co-stamp fix → gate fix → test → force-run → commit. **The mandated pre-write backup failed its own integrity check** — `backup_database.py`'s raw `shutil.copy2` of a live WAL-mode database is not crash-consistent, and the first attempt today produced a torn-page corrupt file. This is a finding bigger than today's task: every backup taken by that script while services were running (i.e., essentially always) is suspect, including the safety-net backups this project has leaned on all month. Recovered by using SQLite's online backup API for a verified-clean backup, then proceeded. Both fixes verified via full suite (73/73) plus a standalone synthetic-data check with a negative control proving the old gate really would have missed the bug. `--force` run requeued 8,971 traders cleanly; committed and pushed.

### The real Stage-0a blocker
Separately, read-only: characterized what's actually driving the "BUY trades with no position record" metric's continued intraday growth (481,997 → 498,661 across the day — O-7.1 only explains ~12% of that). Found two independent, code-confirmed mechanisms: `background_backfill_worker.py` bulk-inserts full trade histories for newly-discovered traders without ever resetting `pnl_last_updated` (proven: 100% of today's 2,594 newly-backfilled traders currently have zero position rows) — bounded and draining (candidate pool 13,436→10,999 today), but currently dominant. And a coarse try/except in `background_pnl_worker.py`'s persist loop that can roll back an entire trader's position batch on a single `database is locked` error while still marking the trader "done" — the same architectural shape as the original O-15 bug, confirmed recurring across 11 separate days since April. Neither fixed (out of scope, read-only as requested) — both ledgered as O-20 with the specific metric and pool to watch.

---

## State for next session

1. **O-19 (backup corruption) — spot-check the existing `backups/` fleet for restorability** before assuming any of them would actually work in an emergency. Fix (`shutil.copy2` → SQLite online backup API) is a one-line-equivalent change, not yet applied to the script itself (only worked around for today's one-off backup).
2. **O-27 (`run_step()` has no subprocess timeout) — top carry-over fix-now item.** Investigated today, design settled, deprioritized when O-7.1 took the session's remaining time. This is the structural gap behind both known 80-minute maintenance hangs.
3. **O-20 — watch, don't act yet.** Sample "BUY trades with no position record" at multiple points across the day (not just 06:00 — that's what caught this). Don't call the Stage-0a plateau until the backfill-worker candidate pool (10,999 as of tonight) visibly drains toward zero and no new `Position insert failed` clusters appear for several more days.
4. **The Fable audit's action list** (`2026-07-07-silent-failure-audit-FABLE.md`) is now the structured backlog for everything else — O-22 through O-26, O-28, O-29 are its fix-now/harness/structural items, each ledgered individually so nothing needs re-deriving from the audit doc itself next time.
5. Everything else on the ledger (O-2, O-8, O-10, O-11, O-18, and the ELO-arc's own Stage 0b/0c) is unchanged and still open.

---

## Final state, both repos

**first-repo:**
```
f5fae64 fix: O-16 requeue event-time gate + legendary co-write gap (O-7.1)
3b80369 feat: O-16 Tier-2 backfill (remaining historical_backfill markets)
54f3d77 fix: O-15 naive/aware datetime TypeError in Position.close_position
ebbb69c fix: O-16 backfill ISO8601 timestamp bug + register gamma_backfill data_source (O-3)
ca30c07 fix: remove dead check_market_resolutions from monitor loop, offload scan_for_successful_traders (O-13)
```
One commit from today (`f5fae64`), pushed. Working tree: 2 pre-existing modified log files (`logs/arb_bot_exclusions.log`, `logs/focus_ratio_review.json`) — already dirty at session start, auto-regenerated by maintenance, deliberately left alone (same as every prior session). One verified-clean database backup taken this session (`backups/markets_20260707_safe_211327.db`, ~12GB) — the corrupted first attempt was deleted, not left in the backups directory.

**trading-swarm:**
```
a8c07f2 docs: bank the 2026-07-07 silent-failure audit (FABLE)
4e96163 docs: 2026-07-06 session summary
35281ac docs: bank ELO-arc design as plan of record for O-5/O-6/O-7...
```
Plus this session's ledger + session-summary commit (see below). Working tree otherwise has the swarm's routine autonomous-agent output accumulation (data-audit snapshots, trader-profile deltas, cron logs) — not touched, same as every prior session; out of scope, no context on correctness.
