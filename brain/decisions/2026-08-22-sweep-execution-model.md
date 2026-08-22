# 2026-08-22 — Full Sweep Execution Model Assessment

**ASSESSMENT ONLY.** No code modified, no sweep started, no production
write beyond one read-only population-count query. Every claim tagged
**[V]** (verified this session) or **[I]** (inferred).

## Headline recommendation

**Chunked, scheduled runs (option 3b), not one continuous detached
process.** Hold `backfill_market_dates.py`'s daily invocation at `--limit
2000` through the sweep, but only for the days it actively overlaps —
**let it run once, unheld, on a day the sweep is paused**, so the
untagged-legacy-improvement branch still gets its first live exercise
without competing with the sweep for write locks. The pre-registration
needs a targeted amendment before the sweep runs — see "Amendment scope"
at the end. A systemd unit remains the wrong tool even at 60 hours.

---

## 1. Concurrency with daily_maintenance

### a. Which steps write to `markets`, and which touch the sweep's own rows

**[V]** Read `scripts/daily_maintenance.py`'s full `STEPS` list directly.
Beyond step 32 (`Backfill market dates`, held at `--limit 2000`,
`bd672fb`), grepped every step script for `UPDATE markets` /
`mark_market_resolved` / `conn.commit`:

| Step | Writes to `markets`? | Touches the sweep's candidate rows specifically? |
|---|---|---|
| `resolution_sweep.py` (step 5) | **[V] Yes** — 3 `conn.commit()` sites, calls into the same assertion-branch-style write path | **Yes, directly** — same evidence-source family (`clob`), same `resolved=0` candidate shape as the sweep |
| `hydrate_stub_markets.py` | **[V] Yes** — 2 `UPDATE markets` sites | Different population (external_seed stub markets only, per this arc's own prior finding — disjoint from the sweep's candidates) |
| `backfill_market_categories.py` | **[V] Yes** — 1 `UPDATE markets` site | Writes `category` only, not `resolved`/`resolution_date` — orthogonal column, but same table, same row-lock contention |
| `resolve_legendary_markets.py` | **[V] Yes** — 2 `UPDATE markets` sites | Narrow, `--limit 50`-scoped population |
| `Backfill market dates` (step 32, held at `--limit 2000`) | **[V] Yes** | **Directly** — its own literal candidate query (no `resolved` filter) overlaps the sweep's `resolved`-filtered predicate wherever both are still `resolved=0`; additionally re-touches recently-sweep-resolved rows via the `end_date IS NULL` side of its OR (this arc's own prior finding, `2026-08-22-tranche2-execution.md` pre-flight question 1: 9,122 such rows existed even before tranche 2's writes) |
| `sync_trade_categories.py`, `evaluate_new_trader_results.py`, `reconcile_geo_resolved_counts.py` | **[V] No** — zero `UPDATE markets` occurrences | n/a |

**Step 32 is not the only concurrent writer — it is the most directly
overlapping one, but `resolution_sweep.py` (step 5, running early in
every maintenance invocation) is a second, independent writer into the
identical evidence-source family and candidate shape**, not previously
weighed in the pre-registration's concurrency thinking (§C does not
mention `daily_maintenance` at all, confirmed by reading the full
document — this is a genuine gap, not a paraphrase).

### b. SQLite's actual behavior — checked, not assumed

**[V]** Both `scripts/backfill_market_dates.py`'s `_get_connection()` and
`monitoring/database.py` set `PRAGMA journal_mode=WAL` and `PRAGMA
busy_timeout=30000` (30s) explicitly. Under WAL, readers never block
writers and writers never block readers, but **SQLite still allows only
one writer transaction at a time**; a second writer attempting to begin
while another holds the write lock blocks for up to `busy_timeout`, then
raises `sqlite3.OperationalError: database is locked` if it's still held.
30 seconds is generous for a single-row `UPDATE` — the sweep's own
per-call transactions are short (fetch, classify, one `UPDATE`, one
`commit()`) — so **serialization via brief blocking, not errors, is the
expected outcome between the sweep and any other 30s-timeout writer.**

**[V] But not every writer in this codebase uses that timeout.**
`2026-07-07-silent-failure-audit-FABLE.md` item 3.2 (read directly this
session): **~25 daily-maintenance-step scripts call raw
`sqlite3.connect()` without setting `busy_timeout` at all** — including
`update_research_exclusions.py` (step 0, blocking), `fast_resolution_check.py`
(×8 sites), `verify_market_titles.py`, `sync_trade_categories.py`,
`update_geo_elo.py`, `resync_position_counts.py`, and most snapshot/backfill
steps. Python's `sqlite3` default `busy_timeout` is effectively 5 seconds.
That audit's own text: *"A locked step either aborts maintenance
(blocking) or gets silently WARN-skipped (non-blocking). PROVEN exposure,
intermittent trigger."* **This is the real concurrency risk — not the
sweep failing (it has a 30s timeout and would simply wait), but a
5-second-timeout maintenance step failing or silently skipping while the
sweep holds a brief write lock**, on a codebase where roughly a quarter
of the daily steps aren't hardened against exactly this.

### c. The "database is locked" history — what it implies

**[V]** The specific figures cited in the task prompt ("06:01:36,"
"~3,874 historical occurrences") **could not be independently located**
in the documents searched this session (`2026-08-19-market-resolution-write-cluster.md`,
the O-13/O-15/O-20/O-27 decision docs, `brain/agent-outputs/`) — flagged
as unverified rather than propagated. What **is** independently
documented and verified: `2026-06-29-overhang-ledger.md` records
`database is locked` causing `background_pnl_worker.py` to roll back an
entire trader's position-insert batch while still marking the trader
"done" with zero positions persisted — **"11 separate days from April 26
through July 5, bursts up to 150/day"** — a confirmed pattern of actual
failed writes, not benign retries, under a *different* (5s-timeout)
writer colliding with a busy DB. **Implication for a long-running writer
running under the hardened 30s timeout (the sweep itself): the sweep is
not the vulnerable party. The vulnerable parties are the ~25
unhardened daily-maintenance steps that could collide with it.**

### d. WAL checkpoint step under a long-running writer

**[V]** Read `daily_maintenance.py` directly: the WAL-checkpoint step
runs `sqlite3 <db> "PRAGMA wal_checkpoint(PASSIVE);"` via `subprocess.run()`,
near the end of the maintenance sequence (just before step 32). `PASSIVE`
mode checkpoints as many WAL frames as possible **without blocking any
concurrent reader or writer** — but it also **will not truncate WAL pages
that are still needed by an open, uncommitted read transaction held by
another connection**. The sweep's own transactions are short and
committed immediately per-row (confirmed: `tranche2_write.py`'s
unconditional `conn.commit()` after every accepted write), so it does not
hold a long-lived open transaction that would block checkpointing.
**Sustained WAL growth is not expected from the sweep's own write
pattern** — each write is committed within milliseconds of being issued,
not batched into one multi-hour transaction. The WAL file was 16.5GB+
compacted cleanly after both tranches this session (confirmed via the
backup process's own integrity checks passing); no evidence of
uncontrolled WAL growth from this write pattern specifically.

### e. `polymarket-monitoring`'s 15-minute loop

**[V]** `monitoring/monitor.py` contains 2 `UPDATE markets` sites,
confirmed by direct grep. This is a third, always-on, independent writer
into the same table, already running concurrently throughout both
tranches with **zero abort-condition fires or atomicity violations across
either run** — the strongest empirical evidence available that the
30s-busy_timeout writers (monitor.py, the sweep) coexist safely with each
other. It does not materially change the risk profile identified in (b)
and (c): the concern is the ~25 *unhardened* steps, not the hardened
always-on services.

---

## 2. The interruption model

### a. Measured worst-case rework per interruption

**[V]** From tranche 2's own checkpoint history (10 batches, 500 rows
each): per-batch elapsed time ranged **202.6s–214.0s**, average ~208.1s.
Confirmed empirically (batch 4's restart after the mid-batch kill):
**a restart always re-issues the entire interrupted batch's 500 calls
from scratch** (`fresh=500, skipped=0`, verified both kill tests) —
already-written rows correctly no-op via the comparator, but the
wall-clock cost of re-fetching and re-classifying them is not avoided.

**Worst case: ~208s (≈3.5 minutes) of redundant wall-clock work per
interruption** — a kill one row before a batch's own completion re-does
essentially the whole batch. **Best case: ~0s** — a kill that lands
between batches (checkpoint already flushed, next batch not yet started)
loses nothing. Over a ~60-hour run, even several worst-case interruptions
cost minutes, not hours — **this cost is not the driving concern for
execution-model choice.**

### b. Would a smaller batch size help, and at what cost

**[I]** A 100-row batch would cut worst-case rework to ~42s (208s × 100/500)
— proportional, as expected. Checkpoint-write cost itself is trivial (a
JSON file write via `os.replace`, measured in milliseconds, not a
meaningful overhead at any batch size tested). The real tradeoff is
volume: a full ~513,770-candidate sweep at 500-row batches produces
~1,028 checkpoint writes; at 100-row batches, ~5,138 — five times the log
volume and file-write events, for a worst-case-rework improvement of
~166s per interruption, against a total runtime measured in tens of
hours. **Not a meaningful improvement at this scale — 500 remains a
reasonable batch size.** (Tranche 2 itself is not evidence this needs
changing — zero data-correctness issue was found at 500 rows in either
kill test.)

### c. Does 60 hours change the systemd-`Restart=on-failure` calculus?

**[V]** §C's exact stated reasoning (read directly): *"which is not
proposed here since this is a one-off, not a permanent service."*
**Assessed honestly, both directions:**

- **The case that it still doesn't change the calculus:** the sweep
  remains a one-off in the sense that matters for the "permanent service"
  framing — it will not recur indefinitely, has a defined end state (the
  candidate population reaching zero, or being judged complete), and
  installing a systemd unit for a single multi-day task is real
  operational overhead (a unit file, a restart policy, cleanup after the
  fact) for something that, per §2a above, only costs minutes per
  interruption to resume manually anyway.
- **The case that 60 hours *does* change something:** at 36 hours, a
  human could plausibly stay loosely aware of the run across roughly one
  overnight period. At 60 hours (spanning **three nights**), the
  probability of an interruption landing while no one is watching to
  manually restart is materially higher — and per the box's own
  documented ~4 connectivity/availability events per month (**this
  session's own overnight-incident finding, `2026-08-22-overnight-incident.md`**,
  is itself one such event), the expected number of interruptions during
  a 60-hour window is `4/30 × 2.5 ≈ 0.33` — call it **roughly 1-in-3 odds
  of at least one interruption landing during any given ~60-hour window**,
  not "likely" in the sense of near-certain, but not negligible either.
- **Resolution: neither "install a systemd unit" nor "assume someone will
  always be watching" is quite right.** The chunked-scheduled execution
  model (§3b below) sidesteps this tension entirely — no run segment is
  ever unattended for more than a few hours, so an interruption during any
  one segment is caught at the next deliberately-scheduled check-in, not
  discovered hours or days later. A systemd unit remains the wrong tool
  not because 60 hours doesn't matter, but because the better fix is
  bounding exposure per segment, not automating restarts of a longer
  unattended run.

---

## 3. Execution model options

| | (a) Continuous detached | (b) Chunked, scheduled | (c) Supervised systemd service | (d) Cron-driven, one batch per fire |
|---|---|---|---|---|
| **Total elapsed** | ~59–60h wall-clock if uninterrupted; unpredictable tail if interruptions go unnoticed | ~59–60h of *processing* time, spread over as many calendar days as scheduling allows (e.g. 3–5 days at a few hours/day) | ~59–60h wall-clock, self-healing around interruptions | Slowest in calendar time — one ~208s×N-batch chunk per cron fire, could take a week+ if scheduled sparsely |
| **Exposure to §1's concurrency problem** | High — spans 06:00 UTC on 2–3 consecutive days by construction (a random ~60h window almost always crosses at least two) | **Controllable** — segments can be deliberately scheduled to avoid the 06:00–~10:00 maintenance window entirely | Same exposure as (a) — the service doesn't know about the maintenance window unless explicitly taught to | Low if fire times are chosen deliberately (same control as (b), less code) |
| **Operator attention required** | Low during the run, but a silent multi-hour stall is easy to miss entirely until checked | **Moderate, deliberate** — someone decides when each segment runs, giving a natural checkpoint for judgment (abort conditions, health) at each boundary | Low, by design — that's the point of automatic restart, but also its risk (see below) | Low, but scheduling logic itself needs building/testing (more code, more to get wrong) |
| **Worst-case interruption timing** | Killed at 05:59, resumes into the teeth of maintenance on restart if restarted promptly, or sits idle for hours if not noticed | Bounded — a segment killed mid-way is caught at the next scheduled check-in, at most a few hours later, and the next segment's schedule can be chosen to avoid re-colliding with maintenance | Auto-restarts immediately, including immediately back into a maintenance-window collision, with **no human judgment applied to whether restarting immediately is even wise** at that moment (e.g. mid-incident, as today's overnight event showed) | A missed/failed cron fire is silent by default unless explicitly monitored — same blind-spot risk as (a), just chunked |

**Recommendation: (b), chunked and scheduled.** It is the only option
that lets a human decide, each time, whether the concurrency conditions
are currently favorable (per §1) — the other three either accept the
maintenance-window collision as a given (a, c) or add automation
complexity that doesn't remove the underlying judgment call, just defers
it to a machine with less context (c), or duplicates (b)'s control with
more moving parts (d).

---

## 4. Should the daily step be held during the sweep?

**[I] Recommend: hold it through the sweep's active days, but deliberately
let it run unheld on at least one day when the sweep is paused (not
running that day) — not indefinitely held, and not simply restored to
full production behavior in parallel with the sweep.**

Reasoning: §1 established the daily step (32) and `resolution_sweep.py`
(step 5) both write into the exact evidence-source family and largely
overlapping candidate shape the sweep is walking. Running the held
(`--limit 2000`) daily step *concurrently* with an active sweep segment
adds: (a) real, if brief, write-lock contention during a chunk that's
already trying to move as fast as safely possible, (b) duplicate CLOB API
calls the sweep would have made anyway on the same rows shortly after,
resolved harmlessly by the comparator but wasteful, and (c) a second
source of `resolved`-flip activity to reason about if any abort condition
fires during a chunk — worse debugging conditions for no benefit.

But the daily step's own held state has **independent, real value named
in this arc already**: tomorrow's (or any day's) unheld run is the first
plausible chance for the untagged-legacy-improvement branch to fire in
production, since the *script's own literal* (non-`resolved`-filtered)
query — unlike every tranche this arc has run so far, all deliberately
scoped to §C's `resolved`-filtered predicate — can reach already-resolved-
but-still-null-`end_date` rows (9,122 of them as of tranche 2's pre-flight
check, now grown by tranche 2's own 4,723 fresh writes that also lack
`end_date`). **Trading that away entirely for the sweep's duration is not
free.** The chunked-scheduling model (§3) already creates natural gaps
between sweep segments — **let the daily step run at full `--limit 2000`
on a day the sweep is not actively mid-segment**, capturing that value
without contending against a live sweep chunk. This is a scheduling
decision, not a code change, and fits cleanly inside option (b)'s
operator-judgment model.

---

## 5. Fresh population figure

**[V]** Live query, this session, §C's exact predicate:
```sql
SELECT COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL) AND (end_date IS NULL OR resolution_date IS NULL);
-- 513,770
```

| Capture point | Population |
|---|---|
| Pre-registration estimate (08-21) | 515,491 |
| Tranche 2's draw time (08-22, ~14:42) | 518,495 |
| **Today, post-tranche-2** | **513,770** |

**First time this figure has been below the original planning estimate**
— tranches 1+2's combined 4,926 resolutions (203+4,723) have outpaced
organic new-market arrival since the pre-registration was written. Not a
concerning decrease; directly attributable to this arc's own successful
writes (self-shrinking candidate set, exactly as §C's resumability design
predicted).

**Re-projected runtime at the measured 0.416s/call:**
513,770 × 0.416s ≈ 213,728s ≈ **59.4 hours ≈ 2.5 days** — consistent with
(very slightly below) the ~60-hour figure in the task prompt, reflecting
the marginally smaller current population.

---

## 6. The two unexercised items — do either block a 60-hour run?

**Atomic rename under a kill landing during the rename itself:**
**[I] Acceptable residual risk, does not need resolving first.**
`os.replace()` (used by the checkpoint writer) is POSIX-atomic by the
OS's own guarantee, not by anything this driver's logic does — there is
no partial-write state for a kill to catch, by construction of the
syscall itself, regardless of whether either kill test in this arc
happened to land during that narrow window. Nothing found this session
contradicts that guarantee holding.

**Cross-rank overwrite never firing across 9,723 candidates:**
**[I] Worth naming as an open question in the amendment, not a blocker.**
§A1 predicts this branch ("a CLOB write is expected to occasionally
outrank an already-present Gamma value") should be routine at scale; zero
occurrences across both tranches combined is a real, if inconclusive,
data point against that framing. It does not indicate a defect — the
branch was fabricated and confirmed working correctly in isolation during
the driver-fix verification (`2026-08-22-tranche2-driver-fixes.md`) — but
a 60-hour run at ~40x tranche 2's volume is exactly the scale that would
either confirm the "routine" prediction or firmly establish it as rare.
**Not a gate; a thing to watch and report on once the sweep has run**,
named here so it isn't mistaken for settled.

---

## Amendment scope

**The pre-registration needs a targeted amendment before the sweep runs.**
Sections that would need it, specifically:

- **§C, "Batching and resumability" / execution mode**: currently silent
  on `daily_maintenance` entirely (confirmed by reading the full
  document — no mention of concurrency with the daily cron job anywhere).
  Needs: the chunked-scheduling execution model (§3 above), the decision
  on holding step 32 during active segments (§4 above), and an explicit
  statement of which maintenance steps are known concurrent writers into
  `markets` (§1a's table).
- **§C, "Backup"**: still correct as written (before the sweep begins,
  not before each chunk) — no change needed, but should note the backup
  taken for tranche 2 (`markets_20260822_143948.db`) may need refreshing
  depending on how much time elapses before the sweep's first chunk
  actually starts, per §G's own "fresh capture immediately before" rule.
- **§I, "What would falsify the plan"**: could gain the cross-rank-
  overwrite non-occurrence as a tracked, not-yet-falsifying observation
  (§6 above), so a future reader doesn't need to re-derive that it was
  already known and assessed.

Not touched by this assessment (assessment only, per the task's
constraints) — a future task should write the actual amendment text.
