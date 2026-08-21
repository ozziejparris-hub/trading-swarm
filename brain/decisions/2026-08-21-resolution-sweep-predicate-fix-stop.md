# 2026-08-21 — fix `resolution_sweep.py`'s write-time assumption: STOPPED at pre-flight

**STOPPED before any edit.** Context: `2026-08-21-step3-stop.md` (`5257f80`).
Oscar's direction was to mirror `f5fae64`'s pattern (the fix already
proven for `requeue_resolved_market_traders.py`) and let step 3 proceed.
**The pre-flight measurement shows the pattern does not transfer cleanly —
switching to `last_checked` alone would grow the sweep's candidate set by
+54% with a materially different, less-precise composition, and would
silently drop the two newest resolution writers this arc has itself just
shipped.** Per the task's own branching instruction, this is a stop, not
a pick-a-behavior. Every claim tagged **[V]** (verified this session,
command/file:line given) or **[I]** (inferred, marked explicitly). No file
modified, no dry-run run, no production write anywhere in this session.

---

## (a) `f5fae64`'s diff, read in full — not inferred from the step-3 stop's summary

**[V]** `git show f5fae64`, full diff:

- `requeue_resolved_market_traders.py`: the predicate swap alone
  (`resolution_date` → `last_checked`, same shape proposed here).
- **A second, necessary change the step-3 stop's summary did not mention:**
  `legendary_positions_scan.py`'s two resolution-writing UPDATE statements
  **never stamped `last_checked` at all** (only `resolution_date`) — the
  commit added `last_checked = ?` to both, explicitly *"to match the
  convention already used in `resolve_legendary_markets.py`."* The commit
  message states the reasoning precisely: **the predicate swap only works
  if every writer that can set `resolved=1` reliably co-stamps
  `last_checked` at that same moment.** `f5fae64` didn't just change a
  predicate — it first closed the specific writer-side gap that would
  have made the new predicate wrong, then changed the predicate.

**This is the exact question this pre-flight needs to answer for
`resolution_sweep.py` too: does every current resolution writer co-stamp
`last_checked`? Answered in (c) — no.**

---

## (b) What the sweep is for — read in full, `scripts/resolution_sweep.py`

**[V]**, full file read (323 lines). "Channel 2 discovery": when a
Geopolitics/Elections market resolves, sweep every trader with a
≥$500 position in it into the monitored pool (flag if already known,
insert if new) — specifically to catch single-event insiders who trade
one market in size and would never surface via leaderboard discovery
(which needs 3+ markets). Idempotent per trader (`already_ok` if already
flagged) — the *marginal* value of re-sweeping the same market on a later
day is zero once its traders are flagged, so the 7-day window's job is
narrower than it looks: **give each newly-resolved market roughly a week
of chances to be swept before that window closes and its traders'
one-time insider signal is lost for good.** Supports `--dry-run` natively.

**Scheduling — corrected from the step-3 stop's report, not merely
repeated:** `resolution_sweep.py` is invoked **only** by
`daily_maintenance.py`'s "Resolution sweep" step [V, `grep`]. **There is
no separate weekly cron for it** — `weekly_resolution_sweep.sh` (the
`30 3 * * 0` entry) is a different mechanism entirely: it calls
`fast_resolution_check.py`'s `run_stale_clob_pass`/`run_recent_overdue_pass`
(CLOB-based resolution *discovery*, unrelated to trader *discovery*) [V,
read `weekly_resolution_sweep.sh` in full]. The name collision misled the
step-3 stop's summary; corrected here rather than propagated.

---

## (c) Who writes `last_checked`, and when — enumerated, not assumed

**[V]** `last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP` — the schema
default means it is **never NULL**: `SELECT COUNT(*) FROM markets WHERE
resolved=1` = 224,981; NULL `last_checked` among them = **0**. NULL rate
is not the problem — staleness/meaning is.

**Does `mark_market_resolved()` stamp it? No** [V, `grep -n
"last_checked" monitoring/resolution_writer.py` — zero hits]. It is not a
canonical-path column; every caller is responsible for its own companion
write, exactly as `f5fae64`'s legendary-scripts fix already established
as the precedent.

**Do the two newest canonical-path writers stamp it? No, neither.**
- `scripts/hydrate_stub_markets.py` (Stage 1, shipped): **zero** hits for
  `last_checked` anywhere in the file [V].
- `scripts/backfill_market_dates.py` (step 1, shipped this arc): **zero**
  hits for `last_checked` anywhere in the file [V] — its assertion branch
  writes `end_date` (best-effort) and calls `mark_market_resolved()`;
  neither touches `last_checked`.

**Which writers do?** `scripts/fast_resolution_check.py`'s Gamma bulk pass
(companion direct `UPDATE ... SET last_checked = ?` right after its
`mark_market_resolved()` call — confirmed this session and in the step-1/
step-3 work) and the legacy writers `f5fae64` itself fixed
(`resolve_legendary_markets.py`, `legendary_positions_scan.py`).

**Live proof this isn't hypothetical** — the one live `hydration_fill` row
today [V]:
```
resolution_recorded_at = 2026-08-20 17:32:09   (the actual write, yesterday)
last_checked            = 2025-12-11 11:06:19   (~8 months stale)
```
Written via `hydrate_stub_markets.py`'s assertion branch. **If
`resolution_sweep.py` gated on `last_checked`, this row — genuinely
resolved and written yesterday — would look 8 months old and never be
swept.** The exact O-16 shape, on a writer this arc shipped four weeks
after the original fix.

**Is `last_checked` bumped on any visit, not only at resolution?
Confirmed empirically, part (d).**

---

## (d) Both candidate sets, measured live, full population

| | Count |
|---|---|
| **Current**: `resolved=1 AND resolution_date >= now()-7d` | **140** |
| **Proposed**: `resolved=1 AND last_checked >= now()-7d` | **215** |
| Overlap | 130 |
| In current, not proposed (**lost** by switching) | 10 |
| In proposed, not current (**gained** by switching) | 85 |

**+54% larger, and the composition change is exactly the feared shape,
not a benign superset.**

**The 10 "lost" rows** [V, inspected individually]: all
`data_source='historical_backfill'` (one `hydration_fill`), all showing
`resolution_date` in **2026-11 to 2028-11 — the future** — a pre-existing
data-quality artifact, not a genuine recent resolution, that happens to
satisfy `resolution_date >= now()-7d` today by accident of string
comparison. Losing these specific 10 from the sweep is not itself a
concern (they shouldn't have been swept-as-recent in the first place) —
but it's flagged here as a separate, real anomaly someone should look at,
not chased further in this pre-flight.

**The 85 "gained" rows** [V, sampled 15 directly] are the decisive
evidence: `data_source IN ('live_monitoring','historical_backfill')`,
`resolution_evidence_source` blank (pre-canonical writers), with
`resolution_date` **months** in the past (e.g. `2026-01-09`, `2026-03-13`,
`2026-04-30`) paired with `last_checked` in the **last few days**
(`2026-08-17` to `2026-08-21`). These are markets that resolved long ago
and have simply been **revisited** recently by the live monitoring loop
for reasons unrelated to resolution — `last_checked` moved, nothing about
their resolution status is new. **Switching the predicate would sweep
these into "recently resolved" and re-run Channel 2 discovery against
them as if newly resolved, which they are not** — precisely the
"recently BECAME resolved" → "recently LOOKED AT" semantic drift the task
named as the risk to check for.

---

## (e) A third option — `resolution_recorded_at`

**[V]** Populated on exactly **13** rows today (12 `gamma` + 1
`hydration_fill`) — matches the task prompt's own figure. **Cannot be
used alone** — 224,968 legacy-path resolved rows would be excluded
entirely.

**But where it is populated, it is exactly right, by construction:**
`mark_market_resolved()` sets it to `datetime.now()` on every accepted
write, for every canonical-path caller, with no companion write required
— unlike `last_checked`, no caller can forget to stamp it. The one live
data point available (the `hydration_fill` row above) shows it doing
precisely the job `last_checked` failed at: **`resolution_recorded_at`
correctly reads "yesterday"; `last_checked` incorrectly reads "8 months
ago."** This is the right long-term key for "when did we record this
resolution" — it is the column the canonical design (§D,
`2026-08-19-canonical-resolution-write-design.md`) built specifically to
carry that meaning, separate from `resolution_date`'s event-time meaning.

**A transitional `COALESCE(resolution_recorded_at, last_checked)`
predicate looks sound, not merely another conflation — reasoned, not
asserted:** it resolves to `resolution_recorded_at` for exactly the
population where `last_checked` is currently unreliable (the canonical-
path writers — `hydrate_stub_markets.py`, `backfill_market_dates.py`, and
`fast_resolution_check.py`'s Gamma pass once step 3 migrates it), and
falls back to `last_checked` for exactly the legacy writers where
`f5fae64` already made that column reliable (`resolve_legendary_markets.py`,
`legendary_positions_scan.py`, the O-16 backfills). Each half of the
COALESCE is used only where it is known-good, not blended in a way that
could mask a gap. **Not verified against live data in this session** —
it was not implemented, per the task's own instruction not to pick a
behavior once the naive pattern failed to transfer.

---

## Conclusion: does not transfer cleanly — stop

Both symptoms the pre-flight asked about are real, measured, live:
1. **Composition change**: +54% (140→215), with the added 85 confirmed to
   be "recently touched," not "recently resolved" — exactly the semantic
   drift named as the risk.
2. **Missing-writer regression**: the naive swap would silently drop the
   two newest canonical-path writers (`hydrate_stub_markets.py`,
   `backfill_market_dates.py`) from Channel 2 discovery entirely, the
   identical failure shape `f5fae64` fixed, recurring on writers built
   after that fix landed — and `backfill_market_dates.py` is the specific
   mechanism step 4's sweep will scale up, so this gap would only widen.

Per the task's explicit instruction, this is a stop.

---

## Options, for Oscar — not decided here

1. **`COALESCE(resolution_recorded_at, last_checked)`** (part e) — the
   measurement-informed candidate. Would need its own before/after
   measurement against live data before being trusted, not assumed sound
   from reasoning alone.
2. **Co-stamp `last_checked` in `hydrate_stub_markets.py` and
   `backfill_market_dates.py`'s assertion branches first** (mirroring
   `f5fae64`'s own two-part shape exactly — fix the writers, *then* swap
   the predicate), rather than reading from `resolution_recorded_at` at
   all. Closer to a literal repeat of `f5fae64`, but does nothing about
   the +85 "recently touched, not recently resolved" composition problem,
   which is independent of any writer gap.
3. **Leave `resolution_sweep.py` on `resolution_date` and instead fix the
   85-row composition problem's root cause** — find and stop whatever
   revisits already-resolved markets' `last_checked` on an unrelated
   schedule, if that's judged worth doing — a larger, separately-scoped
   investigation, not sketched further here.
4. **Do not fix this dependency before step 3** — accept that step 3, once
   it ships, will make `resolution_sweep.py`'s window silently start
   missing Gamma-pass discoveries older than 7 days (the step-3 stop's
   original finding), and treat that as a known, bounded, low-daily-volume
   gap to close later rather than a blocker now.

Not decided here, per instruction.

---

## What this does not do

No code written. No dry-run run. No file modified anywhere in
`first-repo` this session (confirmed: `git status --short` shows only
pre-existing, unrelated background churn). `resolution_sweep.py`,
`fast_resolution_check.py`, `system_observer.py`, `mark_market_resolved()`
all untouched. No production write.

---

*Generated 2026-08-21. Stopped at the pre-flight, per the task's own
explicit branching instruction. Sources: `git show f5fae64` (full diff
and message, this session), `scripts/resolution_sweep.py` (full read,
323 lines), `scripts/weekly_resolution_sweep.sh` (full read),
`scripts/hydrate_stub_markets.py` / `scripts/backfill_market_dates.py` /
`monitoring/resolution_writer.py` (grepped for `last_checked`, this
session), `scripts/fast_resolution_check.py:283-288` (read this and prior
sessions), live DB queries this session (candidate-set measurement,
`last_checked` NULL rate, `resolution_recorded_at` population and
per-row comparison), `crontab -l`, `scripts/daily_maintenance.py`,
`2026-08-21-step3-stop.md` (`5257f80`),
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`) (all
trading-swarm except first-repo scripts as cited). No writer modified, no
schema touched, no data repaired.*
