# 2026-08-21 — step 2 (discovery-gap closure), second attempt: IMPLEMENTED

**All verification gates passed. Committed.** Pre-registration:
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`) §A step 2.
First stop: `2026-08-21-step2-stop.md` (`2801a13`). Oscar's decision:
prioritize coverage over efficiency; accept re-querying permanently-dead
rows; do not accept missing markets; set the limit with headroom. Every
claim tagged **[V]** (verified this session — command/query given) or
**[I]** (inferred, marked explicitly).

---

## Measuring the arrival rate — two signals tried, one rejected outright, one rejected-then-partially-rescued

**This section reports a real methodological difficulty, not a clean
measurement — stated plainly rather than smoothed over.**

### Signal 1 — `tape_start` (MIN(trades.timestamp) per market): rejected

Bucketing the current widened candidate population's `tape_start` by day
produced a *smooth*-looking 90-day series (roughly 1,000–3,700/day) — but
**[V] this measures the wrong thing.** Split by `data_source`: on every
day checked, `background_backfill` supplies effectively the entire count
(e.g. 2026-08-09: 3,216 of 3,222), `live_monitoring` contributes almost
nothing (0–11/day) despite being the *larger* data source overall
(319,593 vs 201,896 rows in the current candidate population).
`background_backfill_worker.py` imports a newly-discovered trader's
**entire historical trade tape in one shot** — a market's `tape_start` is
the real-world date it was first traded on Polymarket, not the date our
system inserted the row. This signal measures "distribution of
real-world trading-activity dates across backfilled traders' histories,"
not "when rows entered our candidate predicate." Rejected.

### Signal 2 — `last_checked`: initially promising, then found to be contaminated by bulk re-touches, rescued via a rowid-density test

Bucketing by `last_checked` (`DEFAULT CURRENT_TIMESTAMP`, not touched by
`INSERT OR IGNORE` on a duplicate key) produced a wildly bursty series —
single days from **11** to **60,156**. Too extreme to accept at face
value. **[V] Decisive test:** if a day's `last_checked` rows are genuine
same-day inserts, their `rowid`s (SQLite's own sequential insertion
counter) should cluster tightly; if they're bulk re-touches of
pre-existing, scattered rows, `rowid`s should span a huge range with low
density (`count / (max_rowid − min_rowid + 1)`).

Result, checked across many days: **density varies from 0.0% to 99.5%.**
Examples: `2026-06-08` (20,763 rows) — rowids span 272,111–474,961, a
202,850-wide span for 20,763 rows, **10.2% density → bulk re-touch, not
genuine arrivals, discarded.** `2026-08-10` (16,845 rows) — rowids span
675,653–692,586, a 16,933-wide span, **99.5% density → genuinely a real,
concentrated batch-insertion event.** Every `live_monitoring`-attributed
day checked (`2026-08-08/13/14/15/18/20`) came back at **0.0–0.1%
density** — this data source's `last_checked` signal is unusable for
this purpose, essentially entirely re-touch noise, likely from a periodic
process that revisits existing rows without creating new ones.
`background_backfill` is a genuine mix: some days near-100% density (real
batches), others under 10% (re-touch).

### The confirmed-genuine distribution

Restricting to high-density (**>95%**) days within the recent window (the
last ~2 weeks, `2026-08-07` onward — this project's current, steady-state
operating regime):

| Day | Count | Density |
|---|---|---|
| 2026-08-07 | 5,742 | 99.1% |
| 2026-08-10 | **16,845** | 99.5% |
| 2026-08-13 | 8,373 | 98.7% |

**Confirmed-genuine recent maximum: 16,845 (2026-08-10).**

**Older, much larger spikes exist but are excluded from the limit-setting
basis, with reasoning, not silently dropped:** `2026-05-15/18/19` show
30,260–60,156 with moderate density (34.8–82.2%) — plausibly real, at
least in part, but concentrated in a period consistent with this
project's own documented initial server-migration/onboarding window
(CLAUDE.md: parallel run started 2026-04-18), not representative of
**current** steady-state arrival. Named here, not erased — if an
onboarding-scale event recurs, see the tail-risk discussion below.

**Distribution, not just a mean, reported as instructed:** day-to-day
arrivals are extremely non-uniform — troughs as low as 11–96/day sit
beside confirmed-genuine peaks near 17,000/day within the same few weeks.
The **maximum**, not the average, is the basis for the limit below, per
Oscar's own instruction.

---

## Tail risk

### (a) Does the scan order actually put newest arrivals last? Confirmed by construction, not assumed

**[V]** SQLite assigns `rowid` sequentially at `INSERT` time — this is
not a correlation to test, it is how the mechanism works: any row
newly entering the candidate predicate today (whether a fresh
`live_monitoring` stub or a `background_backfill` stub for a
just-discovered trader) receives the next sequential `rowid` at the
moment of its own insertion, **regardless of what historical date its own
trades carry** — that is exactly the `tape_start` contamination finding
above, restated as confirmation rather than confusion: a market's
`rowid` position tracks *our own ingestion order*, not the market's
real-world trading history. Newest arrivals are, by construction, always
at the tail of an unordered scan.

### (b) How often would arrivals have exceeded the chosen limit?

With the limit set at **35,000** (below) against a confirmed-genuine
recent maximum of 16,845 — **never, in the confirmed-genuine
distribution.** The only days that would exceed 35,000 are the
moderate-density, likely onboarding-era May spikes, which are explicitly
not treated as representative of current operation. This is not a
zero-risk claim — an onboarding-scale event *recurring* is a named,
residual possibility, not eliminated by this analysis.

### (c) If arrivals ever exceed the limit, does backlog clear the next day or does the front starve the tail?

**Does not starve, under the confirmed-genuine data, and here is why,
mechanically:** the front of the unordered scan is a **fixed, small,
non-growing** dead zone (~98 rows, first stop's own finding — 2020-era
markets CLOB has permanently purged) plus whatever fraction of the
current run's candidates land on `indeterminate`/`no_clob_response` and
therefore **do not leave the candidate set**. Every market that *does*
resolve is removed from the candidate pool on the next query (the
design's own self-shrinking mechanism, already relied on by the sweep).
Since the chosen limit (35,000) is **more than double** the
confirmed-genuine daily maximum (16,845), a single day's run has capacity
to process an entire day's worth of genuine new arrivals **and** still
have over half its budget spare for backlog accumulated from prior runs
or slower-resolving `indeterminate` retries. The fixed dead zone does not
grow, so it never "refills" to consume a larger share of the budget over
time. **This holds for the confirmed-genuine regime.** It would not
necessarily hold against a recurrence of a 30,000–60,000-scale onboarding
event — that would exceed the daily budget on the day it happened, though
the very low troughs seen throughout the measured distribution (many days
under a few hundred) suggest any resulting one-day shortfall would have
ample subsequent low-volume days to clear in, not a compounding one.

**Conclusion: no stop required on tail risk, given the confirmed-genuine
distribution — reported with its residual limits named, not overclaimed
as zero risk.**

---

## The limit

**35,000**, with **~2.08× headroom** over the confirmed-genuine recent
maximum (16,845).

| | 0.25s/call (conservative projection) | 0.1s/call (script's actual current default) |
|---|---|---|
| 35,000 candidates | 8,750s (145.8 min, **2h26m**) | 3,500s (58.3 min) |

**Fits the 3-hour (10,800s) step timeout with ~34 minutes (19%) to
spare** at the conservative 0.25s/call basis, and very comfortably at the
script's actual unchanged 0.1s pacing.

---

## The change

Baseline from git, not transcribed [V]:
```
git log --oneline -3 -- scripts/daily_maintenance.py
  c4ac9fa fix: O-26 honest maintenance-completion banner (Fable finding 4.1)
  269d8d1 feat: O-2 weekly --full-sync backstop in daily_maintenance.py
  764839b fix: O-27 run_step() subprocess timeout — closes the maintenance hang-class
```
Confirmed working tree byte-identical to `c4ac9fa` before editing.
`backfill_market_dates.py` confirmed byte-identical to its own `HEAD`
(untouched by this change).

**Changed the `daily_maintenance.py` invocation only** — dropped
`--geo-only`, raised `--limit` from `500` to `35000`:
```diff
-        extra_args=["--geo-only", "--limit", "500"],
+        extra_args=["--limit", "35000"],
```
Plus an explanatory comment above the call site. **The script's own
`--limit` default (1000) was deliberately left unchanged** — a manual,
ad-hoc invocation of `backfill_market_dates.py` without an explicit
`--limit` should stay a quick, testing-scale run, not silently trigger a
~1-hour live sweep; only the scheduled daily invocation needed sizing for
steady-state coverage. `--geo-only` requires no corresponding script-level
change to "drop" — it is `action="store_true"`, already `False` by
default; removing it from `daily_maintenance.py`'s `extra_args` is the
entire change needed.

**The permanently-dead ~98-row prefix is accepted, not skipped** — no
`ORDER BY`, no skip/exclusion marker, no retry backoff implemented, per
constraint. Named as a follow-up in the code comment and here.

---

## Pre-registration's own stop condition

**[V]** Widened population, live: **524,410** — consistent with the
pre-reg's ~515,491 estimate (a 1.7% difference, same order of magnitude,
consistent with ordinary daily growth over the hours since that estimate
was recorded). Not off by an order of magnitude. Satisfied, not
triggered.

---

## Verification

**(a) Baseline from git** — above.

**(b) Both candidate population counts, live:**

| | Count |
|---|---|
| Current `--geo-only`-scoped (script's own query) | **360** |
| Widened (script's own query, no `--geo-only`) | **524,410** |

**(c) Dry-run at the widened scope — a real, meaningful-scale live test,
not a toy sample:** `--dry-run --limit 5000` (chosen as a representative
sample rather than the full 35,000, for practicality — reasoning stated,
not hidden):
```
[BACKFILL] Done — updated=4790, not_found=210, skipped_no_api_id=0, errors=0,
           resolved_accepted=3229, resolved_rejected=0, total=5000
```
**Zero errors.** `updated=4,790` (95.8%) — far higher than the first
stop's 300-row sample (67% updated), because the fixed ~98-row dead zone
is now diluted across 5,000 candidates instead of 300, exactly as the
headroom reasoning predicted. `resolved_accepted=3,229` (64.6% of total,
67.4% of updated — consistent with step 1's 317-market census, 67.4%
resolved), `resolved_rejected=0`. Both the proxy branch (plain
`[DRY-RUN]` lines, non-assertion markets) and the assertion branch
(`[DRY-RUN][CLOB-ASSERT]` lines) fire correctly at this scale, including
a same-run example of the **untagged-legacy-improvement comparator
branch** (`reason='written: existing value has no recorded
evidence_source (pre-canonical), proposal accepted'`), not just the
trivial first-write case — confirmed directly against the live DB, no
write occurred (below).

**Runtime observed:** approximately 950–1,100 seconds (~16–18 minutes)
for 5,000 candidates — file-timestamp-derived, not a precisely instrumented
figure (noted honestly rather than presented as more precise than it is).
Implies an observed per-call rate of roughly 0.19–0.22s (the script's
0.1s sleep plus real network latency) — consistent with, and slightly
faster than, the conservative 0.25s/call basis used for the feasibility
projection above. Extrapolated to 35,000: **roughly 111–129 minutes**,
comfortably inside the 3-hour ceiling, consistent with the a-priori
projection.

**(d) `run_tests.py`:** **16 files run, 15 passed, 1 failed
(`test_backtest_window_population.py`, 24 tests, 19 passed)** — matches
the standing baseline exactly, no new failure.

**(e) Confirm no production write — against the actual write target, not
the dry-run flag:**

| | Before | After |
|---|---|---|
| `resolution_evidence_source='gamma'` | 12 | **12** |
| `resolution_evidence_source='hydration_fill'` | 1 | **1** |
| `check_resolution_write_atomicity` | 0 | **0** |

**Additionally**, per the standard the last several changes used: pulled
the full `market_id`s for six sampled `[DRY-RUN][CLOB-ASSERT]` lines
(three each from the trivial `reason='written'` branch and the
untagged-legacy-improvement branch) and queried them directly:
- Trivial-branch samples: all three still show `resolved=0,
  resolution_date=NULL, resolution_evidence_source=NULL` — unwritten,
  as expected for a first-time resolution that never happened.
- Untagged-legacy-improvement samples: all three show `resolved=1`
  (**pre-existing**, from some earlier, non-canonical writer, unrelated
  to this session) with `resolution_evidence_source` still NULL/empty —
  **exactly the pre-dry-run state**, confirming the dry-run's
  `mark_market_resolved(dry_run=True)` call correctly computed what
  *would* improve the tag without writing it.

`git status --short` confirms only `scripts/daily_maintenance.py`
modified; `backfill_market_dates.py`, `fast_resolution_check.py`,
`hydrate_stub_markets.py`, `monitoring/system_observer.py`, and
`monitoring/resolution_writer.py` all clean.

---

## Commit

One commit: `scripts/daily_maintenance.py` (the one call site's
`extra_args` plus an explanatory comment) plus verification artifacts
under `data/characterizations/step2_verification/` (git baseline copy,
the 5,000-candidate widened dry-run capture). Cleanly revertible — `git
revert` restores `--geo-only --limit 500` in one step.

---

*Generated 2026-08-21. Implemented and verified — the arrival-rate
measurement required rejecting one signal outright (`tape_start`) and
partially rescuing a second (`last_checked`, via a rowid-density test
distinguishing genuine batch inserts from bulk re-touch noise) before a
defensible, density-validated maximum could be established. No
production write occurred at any point in this session, confirmed
against the actual write target for both comparator branches exercised.
Sources: live DB queries this session (tape_start/last_checked
day-bucketing, rowid-density validation across many days, candidate
population counts, before/after write-target verification),
`scripts/daily_maintenance.py` (before: `c4ac9fa`; after: this session's
commit), `scripts/backfill_market_dates.py` (unmodified, confirmed),
`run_tests.py` output, `2026-08-21-step2-stop.md` (`2801a13`),
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`),
`2026-08-21-step1-implementation-v2.md` (`50e8d25`) (all trading-swarm
except first-repo scripts as cited).*
