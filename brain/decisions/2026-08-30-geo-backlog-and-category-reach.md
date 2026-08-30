# Geo/Elections Backlog and Category Reach — Do They Gate Phase 2?

**Scope:** read-only. Answers whether the flat ~23,000 geo/elec pending-trade backlog
is stuck or churning, why `evaluate_new_trader_results.py` isn't draining it, resolves
a direct conflict in the record about category-backfill throughput, and determines
whether sweep-resolved markets can ever reach the canonical backtest/v2f population.
Nothing fixed, nothing resumed.

Tagging: [V]=verified this session (query/code/log read directly), [I]=inferred. Per
the standing instruction, every claim was checked against the specific component it
names — see §3, where the apparent "conflict in the record" turned out to be a
misreading of one script's own cumulative-counter log line, not an actual behavior
change.

---

## VERDICT

**The backlog question and the category-reach question are INDEPENDENT — different
populations, different mechanisms, and the backlog turns out not to matter to the
thesis at all.**

The flat ~23,000 geo/elec pending-trade count (Part 1) is genuinely **churning, not
stuck** — a 24-day trend shows swings between ~21,400 and ~43,700, with the
previously-checked 3-day window (08-28→08-30) landing on a locally-flat plateau
right after a large drain. It isn't draining to zero because **97.5% of it belongs to
traders `evaluate_new_trader_results.py` was never designed to process** (not
`is_flagged`) — this is a population nothing was ever built to touch, not a failure.
And critically: **zero of the 23,213 pending trades belong to a LEGENDARY-eligible
trader.** The thesis metric does not depend on any of this backlog draining.

The category-reach question is the one that actually matters, and it's worse than
the prior doc's "throughput" framing suggested only in the sense that the mechanism
is now fully nailed down: `column_definitions.py`'s `BACKTEST_WINDOW_BASE_WHERE` and
`trader_skill_metric_v2f.py` both filter on `m.category` (markets.category) — never
`trades.market_category` — confirmed in code, with an explicit comment and a
self-test enforcing it. There is no escape hatch. **Of 214,413 sweep-resolved
markets, exactly 225 (0.10%) enter the canonical population today.** The 08-21/08-30
"conflict" in the record about category-backfill throughput was not a real conflict —
one number was a single day's cumulative-lifetime total misread as a daily figure;
the actual daily rate has been a stable ~60 markets attempted (~8-32 classified) per
day for at least the last 10 days running, confirmed directly from the dedicated log.

---

## PART 1 — Stuck or churning?

### 1a. Persisted artifact [V]

`data/characterizations/geo_elec_pending_backlog_20260830T182900Z.json` — 23,213
trade-level records (trade_id, trader_address, market_id, trade timestamp, market
category/resolution fields, trader flag/exclusion/pool status), captured
2026-08-30T18:29:00Z. No prior trade-ID-level artifact of this backlog exists
anywhere in `data/characterizations/` or `brain/agent-outputs/` — confirmed by
search. **This is the baseline going forward; there was nothing to diff against for
this session.**

### 1b. Historical trend — found richer evidence than a direct ID diff [V]

No ID-level history exists (per 1a), but `brain/agent-outputs/data-audit/*.json`
(daily audit snapshots) go back to at least 2026-08-07, and each one carries the
exact `"pending on resolved non-gap geo/elections markets"` count. Extracted all 24
days:

| date | count | date | count | date | count |
|---|---|---|---|---|---|
| 08-07 | 21,461 | 08-15 | 23,803 | 08-23 | **43,699** |
| 08-08 | 21,781 | 08-16 | 24,067 | 08-24 | 22,896 |
| 08-09 | 22,319 | 08-17 | 24,044 | 08-25 | 33,601 |
| 08-10 | **32,518** | 08-18 | 24,082 | 08-26 | 31,378 |
| 08-11 | 32,655 | 08-19 | 24,719 | 08-27 | 22,738 |
| 08-12 | 22,633 | 08-20 | 24,932 | 08-28 | 22,894 |
| 08-13 | 23,135 | 08-21 | 24,940 | 08-29 | 23,208 |
| 08-14 | 23,611 | 08-22 | 25,577 | 08-30 | 23,161 |

**This is unambiguous churn, not stasis.** The series swings by 10,000-20,000 in a
single day at least twice (08-09→08-10: +10,199; 08-22→08-23: +18,122), each followed
by a comparably large drain within 1-2 days (08-11→08-12: -10,022; 08-23→08-24:
-20,803). The prior verification's 3-day window (08-28: 22,894, 08-29: 23,208, 08-30:
23,161) happened to land on a genuinely flat plateau — but it's a plateau *following*
a drain (08-26→08-27: 31,378→22,738), not evidence the series doesn't move. [I] The
spikes plausibly correlate with weekly Sunday steps (`discover_leaderboard_traders.py`,
the weekly full trade-category sync) surfacing large batches of previously-invisible
trades at once, which then drain over the following days — this is a pattern match,
not confirmed by tracing a specific spike to a specific step's output, and is named
here rather than chased further (out of this task's scope).

### 1c. Age distribution — informative but contaminated by known-unreliable dates [V, caveated]

Computed age-since-`resolution_recorded_at`/`resolution_date` for all 23,213 records.
Result is **not trustworthy as a clean signal**: ages range from -799 days (a
resolution_date that is a *future* scheduled date, consistent with the
`2028-11-07`-style artifact already found in the prior end-to-end verification) to
+800 days, median 89.8 days. This confirms, again, that `resolution_date` is
unreliable for the 95.4% of this population resolved by non-canonical writers (see
§Part 3 of `2026-08-30-canonical-writer-column-gap.md`) — it cannot be used as a
clean age proxy here. **The 24-day count trend in §1b is the reliable evidence for
churn; the per-record age distribution is reported for completeness but should not
be read as precise.**

---

## PART 2 — Why aren't they draining?

Traced `evaluate_new_trader_results.py`'s actual `WHERE` clause against this specific
23,213-record population (not against its docstring):

```
WHERE t.trade_result = 'pending' AND m.resolved = 1
  AND m.winning_outcome IS NOT NULL AND m.winning_outcome != ''
  AND tr.is_flagged = 1
  AND (tr.research_excluded = 0
       OR (tr.discovery_source IN ('manual_watchlist','external_seed')
           AND tr.resolved_trades_count IS NULL))
```

### 2a. Candidate predicate, applied to this population [V]

| condition | count / 23,213 |
|---|---|
| `winning_outcome` set | 23,213 (100%) — not the constraint |
| `is_flagged = 1` | **577 (2.5%)** |
| `research_excluded = 1` | 23,158 (99.8%) |
| `is_flagged=1 AND research_excluded=0` (full candidate scope) | **55 (0.24%)** |
| **outside scope entirely** (`is_flagged=0`) | **22,636 (97.5%)** |

### 2b. Of the 55 actually in scope, why don't they process? [V, narrow finding]

All 55 belong to just **2 distinct traders**
(`0x51f250fa49ec55fdc1a2ec9c2c832f9d6c138623`,
`0xf6aa05caf3dc5ce11e5ddb6a48e6c9e2a7af178e`), both `discovery_source='live_feed'`,
both with `pnl_last_updated` stamped *today* (2026-08-30 10:27:10) — i.e. actively
touched by the pipeline, not abandoned — yet their `geo_resolved_trades_count` is 0
and these specific trades remain `pending`. No `LIMIT`/batch cap exists in
`evaluate_new_trader_results.py`'s query (confirmed — no `LIMIT` clause, no slicing
in the script). **This is a genuine, narrow, unexplained residual** (0.24% of the
backlog, 2 traders) — named, not chased further given its scale relative to the
other findings in this task.

### 2c. Is this a failure, or an unaddressed population? — and does the thesis care? [V]

**Plainly: for 97.5% of this backlog, it is not a failure. It is a population
`evaluate_new_trader_results.py` was never designed to touch.** `is_flagged=1` is a
deliberate scope boundary (per the script's own docstring, confirmed accurate this
time), not an oversight.

**The consequential question, answered directly:** does the thesis metric depend on
any of this? Checked three populations, live:

| population | pending count |
|---|---|
| All 23,213 (backlog as measured by the audit check) | 23,213 |
| `geo_accuracy_pool=1` (Pool C) traders | 864 (64 distinct traders — all `is_flagged=0, research_excluded=1`, i.e. Pool C membership does **not** imply `is_flagged` or `research_excluded=0`; `POOL_C_GATE_WHERE` in `column_definitions.py` has no such clause) |
| `geo_accuracy_pool=1 AND research_excluded=0 AND bot_type IS NULL` (LEGENDARY-eligible — `LEGENDARY_GATE_WHERE` requires exactly this plus a geo_elo_active threshold) | **0** |

**Zero.** No pending trade in this backlog belongs to a trader who could possibly be
LEGENDARY today. The thesis metric's actual input population is untouched by this
entire backlog, at every tier checked. **The flat-count finding from the prior
verification was correctly observed but wrongly worried about** — it's real churn,
mostly out-of-scope-by-design, and irrelevant to the thing Phase 2 would actually
consume.

---

## PART 3 — The category-throughput "conflict": resolved, no conflict

**a/b as stated in the prompt, checked directly against the actual script and its
dedicated log** (`logs/category_backfill.log`, not `daily_maintenance.log`, which
never carried per-run classify/skip detail — `backfill_market_categories.py` logs to
its own file via a `FileHandler`):

**08-21's entry, read exactly:**
```
2026-08-21 09:14:26,534 INFO === category_backfill starting ===
2026-08-21 09:15:44,025 INFO Reached --limit 50 for this run, stopping.
2026-08-21 09:15:44,026 INFO === category_backfill finished === classified=11708 skipped=7576 errors=1
```

**This was a single, ordinary, `--limit 50`-bounded run — identical in shape to
every other day.** `classified=11708` / `skipped=7576` are the script's own
**persisted lifetime cumulative totals** (`state["total_classified"]`,
`state["total_skipped"]`, loaded from and written back to
`data/category_backfill_state.json` on every run — read directly in
`scripts/backfill_market_categories.py`), not that day's batch size. **The prior
assessment doc read a cumulative counter as if it were a single-day figure** — its
own caveat ("today's figures only — not independently confirmed as a sustained daily
rate") was the tell; it was never a sustained rate because it was never a rate at
all, it was a running total. `--limit 50` has been present in `daily_maintenance.py`'s
`STEPS` since before this — confirmed by `git log -p --follow`, the line is
unchanged across every version in history back to the earliest diff available.
**There is no discrepancy to resolve between a "changed" throughput and a "current"
one — the throughput never changed.**

**Real daily figures, last 7 days, counted directly from
`logs/category_backfill.log`'s per-record `CLASSIFY`/`SKIP` lines (not the
cumulative summary line):**

| date | attempted | classified | skipped |
|---|---|---|---|
| 08-24 | 60 | 8 | 52 |
| 08-25 | 60 | 25 | 35 |
| 08-26 | 60 | 32 | 28 |
| 08-27 | 60 | 28 | 32 |
| 08-28 | 60 | 10 | 50 |
| 08-29 | 60 | 18 | 42 |
| 08-30 | 60 | 12 | 48 |

**One run per day, every day, exactly one `"Reached --limit 50"` line per day** (a
batch size of 20 means the loop always overshoots the 50-item stopping check by
completing its in-progress batch, landing at 60, not 50, every time — this is the
script's own arithmetic, not a change in configuration). Classified count varies
day to day (8-32, mean ~19) depending on what titles happen to be in that day's
`ORDER BY market_id` slice — not a trend, just batch composition.

**Real time-to-clear, using the corrected, confirmed-stable rate:** against the
214,155-market `'Unknown'` backlog *within the sweep-resolved population alone*
(§Part 4 below) — at 60/day attempted: **214,155 / 60 ≈ 3,569 days ≈ 9.8 years.** At
the mean 19/day actually classified into a real category: **214,155 / 19 ≈ 11,271
days ≈ 30.9 years.** The prior doc's "~11.7 years" estimate, made from a single
day's ~50/day observation, sits between these two more precisely-bounded figures and
was directionally correct — refined here, not overturned.

---

## PART 4 — Can sweep output reach the thesis population?

### 4a. The critical distinction, resolved by reading the actual predicates [V]

`monitoring/column_definitions.py`, `BACKTEST_WINDOW_BASE_WHERE` (line 468-471):

```python
BACKTEST_WINDOW_BASE_WHERE = (
    "m.resolved = 1"
    "\n  AND m.category IN ('Geopolitics', 'Elections')"
    "\n  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)"
)
```

With an explicit, self-aware comment directly above it: *"category IN (...) reads
markets.category — never trades.market_category (O-2/O-30: the trades-table column
is a write-time denormalization that can lag or diverge from the markets table's own
category, which is canonical for this purpose)."* A structural self-test in the same
file (line 659-662) actively asserts the generated SQL contains `m.category IN
('Geopolitics', 'Elections')` and does **not** contain `trades.market_category` or
`tr.market_category`.

`scripts/trader_skill_metric_v2f.py` — every market-population query (lines 208, 243,
324, 481) uses `m.category IN ('Geopolitics','Elections')`. Zero references to
`trades.market_category`/`tr.market_category` anywhere in the file.

**There is no escape hatch.** The 2026-08-21 `--geo-only` finding (that
`backfill_market_dates.py` used `trades.market_category` while other code used
`markets.category`) concerned a *different* script — a date-filling utility, not the
backtest population or v2f's own predicates, both of which have always used
`markets.category`, deliberately, tested, and documented as deliberate.

### 4b. One sweep-resolved market, traced end to end against the predicate [V]

`0x2b1a5aa2f2bad83ac7efacfa77328930a010b3eb6208313767b591bb3757bea1`
("Will Armenia win Eurovision 2026?"):

| clause | value | passes? |
|---|---|---|
| `m.resolved = 1` | 1 | ✓ |
| `m.category IN ('Geopolitics','Elections')` | `'Unknown'` | **✗** |
| `(trade_gap_flag = 0 OR NULL)` | 0 | ✓ |
| has trades (tape_end exists) | 10,911 trades | ✓ |

**Excluded by exactly one clause: `category`.** Every other structural requirement
is satisfied. This is not a market with thin or gap-flagged data — it has more trade
volume than most markets that *do* enter the population — it is excluded purely
because nothing has ever classified it past `'Unknown'`.

### 4c. Quantified across the full sweep-resolved population [V]

| | count | % of 214,413 |
|---|---|---|
| Total sweep-resolved (`resolution_evidence_source='clob'`) | 214,413 | 100% |
| **Enters the canonical population today** (category + gap-flag + has-trades all pass) | **225** | **0.10%** |
| Would pass every *other* filter if category were not the blocker (gap-flag clean + has trades, category ignored) | 213,926 | 99.8% |

**213,926 is a ceiling, not a forecast** — it assumes every remaining sweep-resolved
market both belongs in Geopolitics/Elections *and* gets correctly classified there,
which is not true; the large majority of sweep-resolved markets are genuinely other
categories (sports, entertainment, crypto — visible in the sample titles throughout
this and the prior two investigations: Eurovision, World Cup, etc.). **The honest
statement is the same one made in the prior column-gap doc: the true count of
sweep-resolved markets that are actually Geopolitics/Elections and merely
miscategorized is unknown without title-level reclassification, which was not
attempted here.** What *is* now established precisely is the mechanism and the
ceiling: category is the sole and total blocker for whatever that true count turns
out to be, and at the confirmed ~19/day real classification rate, clearing enough of
the backlog to find out would take years, not weeks.

---

## PART 5 — Do they interact?

**Independent. Neither subsumes the other. Stated plainly, not forced:**

- The **backlog** (Parts 1-2) concerns trades on markets that **already have a
  correct category tag** — the audit check that measures it filters on
  `m.category IN ('Geopolitics','Elections')`, so by construction every trade in that
  23,213-record population sits on a market that already passed the category gate.
  Its blocker is trader-scope (`is_flagged`), not category.
- The **category-reach problem** (Parts 3-4) concerns markets that **never reach that
  gate at all** — `'Unknown'`-category markets are invisible to the same audit check,
  to the backtest population, and to v2f, before trader-scope or trade-result status
  is ever considered.
- **Mechanically disjoint populations, disjoint root causes** (trader-flagging design
  scope vs. classification throughput), and — per Part 2c — **disjoint consequence
  for the thesis**: the backlog has *zero* measured effect on the thesis population;
  the category-reach problem is the actual, sole, and total determinant of whether
  the sweep's 214,413 resolved markets can ever contribute to it (currently 0.10%
  can).

A market could in principle be affected by both (an `'Unknown'`-tagged market that,
if reclassified, would *also* turn out to have only unflagged traders) — but that
would be coincidence at the individual-market level, not a shared mechanism, and
nothing in this task's data suggests it's common enough to matter.

---

## WHAT REMAINS UNCHECKED (named, not chased — scope discipline)

- Why the 2 traders / 55 trades in evaluate_new_trader_results.py's actual scope
  still don't process despite no `LIMIT` and a `pnl_last_updated` touched today
  (§2b) — narrow (0.24% of the backlog), not chased further.
- The [I] hypothesis that weekly Sunday steps drive the backlog's periodic spikes
  (§1b) — pattern-matched from the 24-day trend, not traced to a specific step's
  output.
- The true count of sweep-resolved markets that are genuinely Geopolitics/Elections
  but miscategorized `'Unknown'` (§4c) — would require title-level reclassification
  at scale (214,155 markets), explicitly out of scope for this read.

No fixes, no plan — this is the read.
