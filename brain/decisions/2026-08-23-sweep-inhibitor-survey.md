# 2026-08-23 — Sweep Inhibitor Survey (read-only)

Survey of everything that could inhibit or be damaged by the ~50 remaining
hours of the discovery-gap sweep (13% complete: 65,000/492,529 candidates
across four runs, most recently segment 2 — see
`2026-08-23-post-segment2-status.md`). READ-ONLY — nothing fixed. Findings
are **verified** against code/logs/DB unless marked **INFERRED**. Three
items were named going in; each is verified rather than inherited, per
standing instruction.

## Summary table

| # | Item | Class | 
|---|---|---|
| 1a | Hold policy has no enforcement mechanism | DEGRADING |
| 1c | resolution_sweep.py "second writer" claim | **NOT A PROBLEM — premise was wrong, verified** |
| 2 | No automated completion/abort signal | DEGRADING |
| 3 | Segment 2 checkpoint uncommitted | COSMETIC |
| 4a | `fast_resolution_check.py` — bare 5s timeout, raw `UPDATE markets`, bypasses canonical writer | DEGRADING |
| 4b | `resolve_legendary_markets.py` — same pattern, smaller volume | DEGRADING |
| 4c | `promote_high_pnl_traders.py` / `resync_position_counts.py` — bare timeout, different table | COSMETIC |
| 4d | "~25 scripts with no busy_timeout" claim | **corrected: ~5 of 30, only 2 touch `markets`** |
| 4e | `background_pnl_worker.py` — timeout=10 vs sweep's 30 | COSMETIC |
| 4f | `polymarket-monitoring` main loop | NOT A PROBLEM — 30s timeout, verified |
| 5a | Disk space | NOT A PROBLEM — 1.2TB free, no near-term risk |
| 5b | WAL growth | NOT A PROBLEM — checkpoints cleanly, no stray WAL file |
| 5c | Memory | NOT A PROBLEM — 83GB available |
| 5d | Checkpoint file O(n) full-rewrite per batch | DEGRADING (low, back-loaded) |
| 5e | Backup retention (396GB, no cleanup policy) | COSMETIC |
| 6a | `discover_leaderboard_traders.py` runtime growth (Sunday-only) | DEGRADING |
| 6b | Today's 9h43m maintenance runtime, attribution | **corrected: mostly Sunday-effect, not sweep** |
| 6c | `backfill_transaction_hashes.py` runtime growth | COSMETIC |
| 7 | 06:00 collision, structurally | DEGRADING (process-dependent, no automated net) |
| 8a | `trg_resolved_no_unresolve` doesn't catch same-state overwrites | DEGRADING (ties to 4a/4b) |
| 8b | Unrotated multi-month logs | COSMETIC |
| 8c | Sustained API/network dependency over ~50h | DEGRADING (INFERRED severity) |
| 8d | "Canonical definitions drift" daily failure | NOT A PROBLEM for this survey — pre-existing, unrelated to sweep |

**Nothing is BLOCKING.** Segment 3 can run under the same manual discipline
segment 2 used (fresh fingerprint, computed runway, launched with margin).
The degrading items compound over the ~50 remaining hours and multiple
06:00 boundaries and should be closed before the sweep is left running
unattended for extended stretches without a human recomputing the runway
each time.

---

## 1. Hold policy

### 1a. No enforcement mechanism — DEGRADING

Confirmed: `daily_maintenance.py:310-331` hardcodes
`backfill_market_dates.py --limit 2000` with a comment stating this is a
temporary manual value, not a check against sweep state. No code anywhere
inspects whether a sweep is running before executing this step.

**Options assessed (not chosen):**

- **Lock/sentinel file** the sweep writes on start, removes on clean exit.
  Simple, but a bare lock has no expiry: if the sweep process dies (kill -9,
  OOM, power loss) without removing it, the lock never clears and every
  future daily_maintenance run holds this step forever until a human
  intervenes. This box has a real crash history (10 reboots in the visible
  `last reboot` history since April, several unclean per the O-14 finding
  already on record) — a bare lock is exactly the kind of state that
  survives a crash badly.
- **DB flag** (a row/column marking "sweep active"). Same staleness problem
  as a sentinel file unless paired with a timestamp/TTL — a crash leaves the
  flag set with no automatic path back to false.
- **Live-process detection** (the step `pgrep`s for the driver script name
  before running). Crash-safe by construction — a dead process simply isn't
  found, no cleanup required. Weaknesses: fragile to how the sweep is
  invoked (script name, wrapper, screen/tmux session) and to PID reuse in
  the small window between a crash and the check.
- **Checkpoint-recency check** — hold the step if
  `data/checkpoints/segment*_checkpoint.json` was written within some
  threshold (e.g. 20-30 min, matching the observed per-batch checkpoint
  cadence of every ~3-4 min at 0.15-0.22s/call × 500/batch). This is
  self-healing: if the sweep dies, the checkpoint simply stops getting
  fresher and the hold auto-releases on its own within one threshold window,
  with no explicit cleanup step to forget.

### 1b. Most robust given this box's crash history

The **checkpoint-recency check** is the best fit specifically because of the
crash history: it requires no crash-handling logic at all — staleness *is*
the recovery mechanism. A sentinel/lock file needs a `trap`/`finally` to
clear itself, and a hard crash (the exact failure mode this box has hit
before) skips exactly that code path. Process detection is a reasonable
supplement but not a replacement, since it depends on correctly identifying
the sweep's process across however it gets launched.

### 1c. Does resolution_sweep.py (daily_maintenance step 5) need the same treatment? — NOT A PROBLEM, premise verified false

Checked directly: `scripts/resolution_sweep.py` only **reads**
`markets WHERE resolved = 1` (line 102) and writes to the `traders` table
(`INSERT INTO traders`, `UPDATE traders` — lines 223/247). It contains no
`UPDATE markets` and no call to `mark_market_resolved()`. It does **not**
write `markets.resolved` / `resolution_evidence_source` at all — it is a
downstream reader of the sweep's output (discovering new traders in
already-resolved markets), not a co-writer into the same columns. It also
already opens its connection with `timeout=30` (`resolution_sweep.py`),
matching the sweep's own hardening. **The "second writer into the same
evidence-source family" framing does not hold up** — this script needs no
change. (Its own daily log entries show near-zero volume: "Found 0 markets"
in the most recent sample, a 7-day lookback window.)

## 2. Monitor is not a completion signal — DEGRADING

Confirmed (carried over from the prior check): task `bkl2qudts`'s output
file contains only `[killed]`. No mechanism currently notifies anyone —
human or automated — that a detached sweep segment aborted or died,
short of someone manually reading the checkpoint/log the way this and the
prior survey did. `monitoring/telegram_bot.py` exists and is send-capable,
but the sweep driver (`segment2_write.py` and its predecessors) contains no
reference to it — confirmed via grep, zero hits.

Minimum that would work: on driver exit (success, abort-condition fire, or
uncaught exception via a top-level try/finally), write a small
`{status, batches_completed, cumulative_processed, elapsed, reason}` marker
file next to the checkpoint, and send one Telegram message using the
existing `telegram_bot.py` send path. That closes the gap without needing
a persistent watcher process (which is what `bkl2qudts` was, and which
dies with its launching session).

## 3. Segment 2 checkpoint uncommitted — COSMETIC

Confirmed unchanged: `git status` still shows
`data/checkpoints/segment2_checkpoint.json` as untracked, alongside the
four `data/characterizations/*.json` files from this and the prior
segment's runs. Segment 1 had both a launch commit and a completion/stop
commit; segment 2 only has the launch commit (`b3f4aea`). No data-integrity
consequence — the DB itself is the source of truth and is unaffected — this
is purely a provenance/audit-trail gap.

**Fix (not implemented):** commit
`data/checkpoints/segment2_checkpoint.json` and the four characterization
JSONs, either standalone (`docs: segment 2 completion state`) or folded
into segment 3's launch commit.

## 4. Concurrency

Audited all ~30 scripts `daily_maintenance.py` invokes for DB-lock timeout
handling (distinguishing PRAGMA `busy_timeout` / `sqlite3.connect(...,
timeout=N)` from unrelated HTTP `requests.get(..., timeout=N)` calls, which
a naive grep conflates). **Correction to yesterday's count:** only **5** of
~30 scripts are genuinely bare (Python's sqlite3 default is a ~5s busy
wait), not ~25:

| script | timeout | writes to | exposure |
|---|---|---|---|
| `fast_resolution_check.py` | none (bare `connect(self.db_path)`) | `markets` — raw `UPDATE markets SET resolved=1, ...` (line 440), **does not go through `mark_market_resolved()`** | **HIGH** |
| `resolve_legendary_markets.py` | none (bare `connect(_DB_PATH)`) | `markets` — raw `UPDATE markets SET resolved=1, ...` (lines 210/215), same bypass, `--limit 50/day` so lower volume | **MEDIUM** |
| `promote_high_pnl_traders.py` | none | `traders` only | LOW |
| `resync_position_counts.py` | none | `traders` only | LOW |
| `check_canonical_definitions.py` | n/a | **no DB writes at all** — pure static-analysis lint script; its daily failure is a code-drift issue, unrelated to concurrency | none |

`fast_resolution_check.py` and `resolve_legendary_markets.py` are the real
finding here, for two independent reasons, not one: (a) a bare ~5s timeout
against the sweep's 30s means their writes are the ones likeliest to lose a
lock race and error out during a batch window, and (b) because they write
via raw `UPDATE markets` instead of `mark_market_resolved()`, they bypass
the evidence-rank conflict logic entirely — a race isn't just "one side
times out," it's "the lower-quality source can silently clobber a
higher-ranked one," independent of whether the sweep is even running.
**DEGRADING** — pre-existing risk, sharpened by the sweep adding a second
long-lived high-volume writer into the same table for hours at a stretch.

`apply_full_elo_modifiers.py` and `discover_leaderboard_traders.py` pass
`timeout=30` directly to `sqlite3.connect()` (equivalent to setting
`busy_timeout`), so they're adequately covered despite not containing the
literal string `busy_timeout`.

`background_pnl_worker.py` (line 482) uses `timeout=10` — weaker than the
sweep's 30s but not bare, writes `positions`/`traders` (not `markets`), and
already has retry-on-restart semantics for its own per-trader processing
timeouts. **COSMETIC** — a plausible occasional lock-wait failure, not
corruption, and self-recovers.

`polymarket-monitoring`'s main loop (`monitoring/database.py:115-119`) sets
`timeout=30.0` and `PRAGMA busy_timeout=30000` explicitly — matches the
sweep. **NOT A PROBLEM**, verified.

## 5. Resource headroom

- **Disk:** 1.2TB free of 1.8TB (32% used). `backups/` totals 396GB across
  26 dated snapshots (roughly one per major sweep session, ~16.5GB each at
  current DB size). At this rate, even 10 more segments' worth of backups
  (~165GB) leaves >1TB free. **NOT A PROBLEM** over the remaining ~50h, but
  there is no retention/cleanup policy — pure accumulation, oldest backup
  from April is still present. **COSMETIC** for now.
- **WAL:** no stray `data/*.db-wal` file present — the DB checkpoints
  cleanly (today's WAL-checkpoint step logged `0|11190|11190`, i.e. fully
  flushed). Sweep commits after every single market write, so lock/WAL hold
  times per write are short. **NOT A PROBLEM.**
- **Memory:** 86GB total, 83GB available, 6MB swap used. Enormous headroom
  for a single-threaded, API-polling Python driver. **NOT A PROBLEM.**
- **Unbounded growth:** the checkpoint file
  (`data/checkpoints/segment2_checkpoint.json`) holds the full
  `resolved_market_ids` list and is rewritten **in full** on every batch
  (every ~500 markets / ~90s at observed pace). At 121 batches it was
  4.4MB; scaled to the full 492,529-candidate population this write grows
  roughly linearly per batch and the *cumulative* I/O across a whole
  segment grows roughly with n² in the list size. Still small in absolute
  terms (tens of MB, well within this box's I/O capacity) but worth
  watching in the later, larger segments. **DEGRADING, low severity,
  back-loaded** — not worth interrupting segment 3 for, but a candidate for
  switching to an append-only or periodic-only checkpoint write if segment
  sizes grow substantially.

## 6. Downstream pressure

**Correction:** today's 9h43m (06:00:01–15:43:48) maintenance runtime is
**not primarily attributable to the sweep.** Today is Sunday, and
`discover_leaderboard_traders.py` (18,714.5s / 5.2h of the total) and the
weekly `sync_trade_categories --full-sync` step only run on Sundays
(`daily_maintenance.py:205-224`). `discover_leaderboard_traders.py` is
already a documented pre-existing hang risk — its own code comment cites
"O-27: all 3 successful runs took 5.45-7.19h, and the first-ever run was
manually SIGKILLed (exit -9) after 4.43h," with a 10h (36000s) timeout
budget set specifically because of that history. This predates the sweep
entirely.

That said, there **is** a real, sweep-plausible signal inside that number:
comparing this Sunday to the prior pre-sweep Sunday (2026-08-16):

| step | Aug 16 (pre-sweep) | Aug 23 (today, post-65k writes) | Δ |
|---|---|---|---|
| `discover_leaderboard_traders.py` | 4,883.2s (1.36h) | 18,714.5s (5.2h) | **+283%** |
| `backfill_transaction_hashes.py` | 9,464.1s (2.63h) | 12,311.7s (3.42h) | +30% |

`discover_leaderboard_traders.py` scans geopolitics/election markets for
new participants — plausibly (**INFERRED**, not confirmed by reading its
internals — scope discipline) doing more work now that the sweep has
resolved tens of thousands more markets in exactly that category space.
At 52% of its 10h budget already, with only 13% of the sweep complete, this
step is trending toward its own timeout on a future Sunday — which would
repeat the exact O-27 SIGKILL incident, this time plausibly caused by sweep
volume rather than pure API scan cost. **DEGRADING** — real, growing, but
Sunday-only and not yet at the failure threshold.

`backfill_transaction_hashes.py`'s +30% is modest and stays well inside its
8h budget. **COSMETIC.**

## 7. The 06:00 collision, structurally — DEGRADING (process-dependent)

Segment sizing already accounts for this correctly *when done manually*:
segment 2's own pre-write fingerprint computed `runway_seconds` against
`next_maintenance_fire_utc` with a 2h target margin, and it worked —
segment 2 finished at ≈04:06, over an hour and a half before 06:00, and
daily_maintenance never overlapped it. A long daily_maintenance run
(today's 9h43m) does **not** shrink a segment's overnight runway by itself,
because maintenance starts *at* 06:00 regardless of how long the *previous*
day's run took, and every run on record — even the worst one (Aug 15,
9.16h) — finished well clear of the next day's 06:00 start.

The actual structural risk is that this margin computation is a **manual
step** someone (or some agent) redoes by hand for every segment launch —
there is no automated check preventing a future segment from being sized or
scheduled without it. That's the same gap as item 1: no enforcement, just
discipline. Given ~7-10 more segments are needed to clear the remaining
~427,000 candidates, that's 7-10 more manual margin computations with no
safety net if one gets skipped.

## 8. Anything else — one-liners

- `trg_resolved_no_unresolve` only catches `resolved` transitioning 1→0; it
  does **not** catch a same-state (`resolved` stays 1) overwrite of
  `winning_outcome`/`resolution_evidence_source` via the raw-`UPDATE` paths
  in item 4a/4b — the DB-level backstop has a gap matching the
  application-level one. DEGRADING, same root cause as 4a/4b.
- Several logs are large, unrotated, multi-month append files
  (`monitoring.log` 129MB, `daily_maintenance.log` 37MB+, `sunday_elo.log`
  17MB) — not sweep-specific and not a disk-space risk given current
  headroom, but they slow down the exact kind of `grep`/`tail` diagnosis
  used in this and the prior survey. COSMETIC.
- Sustained external dependency: at the observed ~0.15-0.22s/call pace,
  427,000 remaining markets is ~25-31h of API calls before any downtime —
  matching the "~50 more hours" estimate once batching/checkpoint overhead
  is included. The driver tallies `no_clob_response` per-call but its
  abort-condition logic wasn't inspected in this survey (scope discipline)
  for how it distinguishes a slow network from a sustained outage — the
  project has already hit one real network outage mid-sweep once
  (Mullvad/Tailscale, 2026-08-21, diagnosed as no-damage). **DEGRADING,
  INFERRED severity** — worth a follow-up look at the abort-threshold logic
  specifically for sustained-outage behavior before the sweep is left
  unattended for a full ~9h+ segment again.
- "Canonical definitions drift" has failed non-blocking on every single
  daily_maintenance run since at least 2026-08-20, independent of the
  sweep. Out of scope for this survey (not sweep-related) but flagged since
  it's the other standing yellow flag in the same log. NOT A PROBLEM *for
  this survey* — pre-existing, unrelated.

## Recommendation

**Nothing here blocks segment 3.** Launch it the same way segment 2 was
launched: fresh backup, fresh fingerprint, computed runway with margin.

**Fix before leaving the sweep to run unattended over the remaining ~50h /
multiple days** (in priority order):
1. Wire a completion/abort marker + one Telegram message into the driver
   (item 2) — cheapest fix, closes the biggest blind spot (nobody currently
   learns of a silent death without manually checking).
2. Route `fast_resolution_check.py` and `resolve_legendary_markets.py`
   through `mark_market_resolved()` with a real `busy_timeout` (item 4a/4b)
   — closes both the lock-race and the rank-bypass exposure at once, and
   incidentally closes the `trg_resolved_no_unresolve` gap noted in 8a for
   the winning_outcome/evidence_source fields specifically.
3. Replace the static `--limit 2000` with the checkpoint-recency hold
   described in item 1 before scheduling segments back-to-back without a
   human in the loop (item 1/7).

**Can wait:**
- Committing segment 2's checkpoint (item 3) — cosmetic, do it opportunistically.
- `discover_leaderboard_traders.py`'s growth (item 6a) — only manifests on
  Sundays and hasn't hit its timeout yet; revisit if it does.
- Checkpoint file O(n) rewrite cost (item 5d) and backup retention (item
  5e) — both real but back-loaded / low severity at current scale.
