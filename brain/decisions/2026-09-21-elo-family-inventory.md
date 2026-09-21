# The ELO family — current use and future potential (read-only inventory)

**Date:** 2026-09-21. Read-only: nothing disabled, modified, or removed. A corpus content extraction run
(PID 102652) was in progress throughout and was not touched — confirmed running at start (4:12:49 elapsed)
and end (4:17:58 elapsed, 118 processed / 6 timed-out-and-flagged, not stalled) of this task.
**Recommends nothing. Oscar decides.**

---

## STOP CONDITIONS TRIGGERED — reported prominently, as instructed

**1. `timing_score`, `patience_score`, and `kelly_alignment_score` are produced ONLY by the Sunday
ELO-family job.** Traced precisely (Part 1/3): the daily step that also touches these columns
(`apply_full_elo_modifiers.py`, "Writer B") reads them from the database and writes the **same value
straight back** — a carry-forward, not a recomputation (`scripts/apply_full_elo_modifiers.py:145-147,
273-283`). The only code path that actually recomputes them is
`monitoring/elo_bridge.py:full_elo_recalculation()`, called exclusively by
`scripts/recalculate_comprehensive_elo.py`, which only ever runs via `polymarket-sunday-elo.timer`
(weekly). **Disabling the Sunday recalc does not merely slow these three columns down — it freezes them
permanently at whatever value the last successful Sunday computed**, with no other live or scheduled path
that would ever change them again. `timing_score` is explicitly named in the task as Component 3 of the
canonical skill metric design and an input to shortlist item 1 — this is exactly the scenario the stop
condition describes.

**2. A live operational consumer would go silently stale.** `analysis/analysis_scheduler.py`'s
`run_phase_1_independent()`, called daily at 01:00 UTC from `monitoring/system_observer.py`'s
`_analysis_report_loop` (confirmed live — `polymarket-observer.service`, PID 55866, has been running
continuously since 2026-09-17), reads `comprehensive_elo` and all three behavioral scores fresh from the
database every day (`analysis/analysis_scheduler.py:818-833`) and combines them into a composite
0-100 score and a tier label (`ELITE`/`STRONG`/`ABOVE AVERAGE`/`AVERAGE`/`BELOW AVERAGE`/`WEAK/NOISE` —
a **third**, separate tier vocabulary from both `derive_tier()`'s LEGENDARY-family and any research-script
labels, matching this project's documented pattern of parallel, uncoordinated classification systems).
The result is written to a **freshly-dated** CSV every single day
(`reports/composite_scores_YYYYMMDD.csv`) and that filename is surfaced in the daily Telegram "Reports
Generated" summary (`monitoring/telegram_health_bot.py:send_analysis_summary`). **If the Sunday recalc
stopped, this daily process would keep running, keep producing a new, freshly-dated report and Telegram
line every day, and nothing in that pipeline checks or reports how old the underlying `comprehensive_elo`/
behavioral-score inputs actually are** — an operator watching the Telegram channel would see "report
generated" daily with no signal that the scores inside it stopped changing weeks or months earlier. This
is a silent-staleness risk, not a hypothetical one — traced to a specific, currently-running loop.

Both findings are folded into Part 4's removal scenarios below, not treated as blockers to reporting the
rest of the inventory.

---

## Part 1 — what the ELO family actually computes

| computation | script | schedule | writes |
|---|---|---|---|
| Full comprehensive ELO recalc ("Writer A") | `scripts/recalculate_comprehensive_elo.py` → `monitoring/elo_bridge.py::full_elo_recalculation()` | `polymarket-sunday-elo.timer`, **weekly**, Sun 03:00 UTC | `traders.comprehensive_elo, base_category_elo, behavioral_modifier, advanced_modifier, pnl_modifier, kelly_alignment_score, patience_score, timing_score, elo_last_updated` — one atomic `UPDATE` per trader (`monitoring/database.py::write_elo_result()`) |
| Daily P&L-modifier pass ("Writer B") | `scripts/apply_full_elo_modifiers.py` | `daily_maintenance.py` step, **daily** 06:00 UTC | Same 9 columns via the same `write_elo_result()` — but only `comprehensive_elo` and `pnl_modifier` are freshly recomputed; `behavioral_modifier`, `advanced_modifier`, `kelly_alignment_score`, `patience_score`, `timing_score` are **read from the DB and written back unchanged** (`apply_full_elo_modifiers.py:145-147, 273-283`) |
| Geo ELO (market-implied-probability ELO, Geopolitics/Elections only) | `scripts/update_geo_elo.py` | `daily_maintenance.py` step, **daily**, incremental by default | `traders.geo_elo, geo_directionality_score`. Independent formula and independent of Writer A/B entirely — different algorithm, different columns |
| Behavioral modifiers (timing/patience/kelly) — **computation** | `analysis/trading_behavior_analysis.py::TradingBehaviorAnalyzer.analyze_all_traders()`, invoked from `analysis/unified_elo_system.py::_load_behavioral_data()` | Called from inside Writer A's Sunday run (fresh, 24h in-memory cache, but the object is recreated fresh every Sunday so this is effectively "computed fresh every Sunday"). **Also called independently, daily, at 01:00 UTC** by `system_observer.py`'s analysis loop (`analysis_scheduler.py:227-228`) — but that call's result is used only for an in-memory report/CSV, never written back to the `traders` table (confirmed: zero `UPDATE`/`cursor.execute(...UPDATE...)` statements anywhere in `trading_behavior_analysis.py`) | Nowhere by itself — a pure compute-and-return function. Persistence only happens via Writer A's `write_elo_result()` call |
| bot_type / bot detection | `scripts/detect_arb_bots.py` | `daily_maintenance.py` step, **daily** | `traders.bot_type='ARB_BOT', research_excluded=1, bot_suspect=1`. Independent heuristic (arbitrage-pattern detection) — not derived from any ELO score, feeds INTO Pool C's gate as an input, not a consumer of ELO output |
| Tier assignment | `monitoring/column_definitions.py::derive_tier()` | Not itself scheduled — a pure function called by `snapshot_elo_scores.py` (daily) and `score_str003_signals.py` (daily) | Not a stored column by itself; computed on demand from `geo_elo_active, geo_accuracy_pool, research_excluded, bot_type` — **all geo-ELO-family inputs, not `comprehensive_elo`** (the codebase itself repeatedly documents this distinction verbatim, e.g. `legendary_positions_scan.py:5`: "LEGENDARY: geo_elo_active >= 2175 AND geo_accuracy_pool = 1 (NOT comprehensive_elo)") |
| `elo_snapshots` | `scripts/snapshot_elo_scores.py` | `daily_maintenance.py` step, **daily** | `elo_snapshots` table — **274,189 rows, 79 distinct dates**, as of today (the task's cited "232,536 rows, 70 dates" is stale by ~9 days; verified live, not propagated) |
| Pool B | `scripts/update_research_exclusions.py` | `daily_maintenance.py` Step 0, **daily** | Not a stored flag by itself — "Pool B" is this script's own name for the clean (`research_excluded = 0`) population, **41,472 traders as of this morning's run**. Not ELO-gated at all |
| Pool C (`geo_accuracy_pool`) | `monitoring/column_definitions.py::refresh_pool_c()`, called from `update_research_exclusions.py` and `update_geo_elo.py` | **daily** (twice: Step 0 and the geo-ELO step) | `traders.geo_accuracy_pool` flag. Gate: `geo_elo IS NOT NULL, geo_resolved_trades_count >= 10, geo_elo_active >= 500, research_excluded = 0, bot_type IS NULL` — **4,648 traders as of this morning**. Geo-ELO-family, independent of `comprehensive_elo` |
| `research_excluded` | Multiple independent writers: `detect_arb_bots.py` (bot detection), manual exclusions (`set_manual_research_exclusion.py`), LP/focus-ratio flags, others per `update_research_exclusions.py`'s own step 0 output | **daily**, several steps | `traders.research_excluded`. **Not ELO-derived** — set by bot detection and other independent criteria; ELO's Pool C gate *reads* this flag, it doesn't produce it |

**For each: produced only by an ELO-family job, or independently?** `comprehensive_elo`, its component
modifiers, and the three behavioral scores: **only** by Writer A (weekly) with Writer B carrying the
behavioral three forward unchanged (daily, but not a real refresh). `geo_elo`/`geo_elo_active`/
`geo_accuracy_pool`/tier/LEGENDARY: an independent daily pipeline (`update_geo_elo.py` +
`column_definitions.py`), unrelated to the Sunday job. `bot_type`/`research_excluded`: independent of ELO
entirely, upstream inputs to Pool C rather than downstream outputs of any ELO computation.

---

## Part 2 — every consumer, graded

Grading: **LIVE** (runs on a schedule or inside a running service), **DORMANT** (exists, not called by
anything scheduled), **DEAD** (no path reaches it).

| reader | grade | reads | quote |
|---|---|---|---|
| `monitoring/elo_bridge.py::UnifiedELOMonitoringBridge.quick_elo_update_for_traders()` — the module's own docstring claims this runs "after trade evaluation" during monitoring cycles | **DEAD** | would read/write comprehensive_elo continuously | zero references to `UnifiedELOMonitoringBridge`/`elo_bridge` found anywhere in `monitoring/*.py`; `monitoring/trader_analyzer.py` (the claimed caller) does not import it. Only live caller of the module at all is `full_elo_recalculation()`, from `recalculate_comprehensive_elo.py` |
| `scripts/audit_invariants.py` | **LIVE** (daily, `daily_maintenance.py` Step "Integrity audit") | `comprehensive_elo` (bounds sanity: `400 <= comprehensive_elo <= 3500`), and a coverage-completeness check that all three behavioral scores are non-NULL together | `audit_invariants.py:590-616` (bounds), `:654-667` (coverage) — both **structural sanity checks**, not decision consumers |
| `monitoring/diagnostics.py` (`ELOSystemDiagnostics`) | **LIVE** (part of `system_observer.py`'s periodic diagnostic report, `self.diagnostics.run_full_diagnostic`, already failure-age gated per the 2026-09-09 Telegram cut) | Same three behavioral scores, `IS NOT NULL` coverage check | `monitoring/diagnostics.py:76-78` — coverage check only |
| `analysis/analysis_scheduler.py` composite-scoring step | **LIVE**, daily 01:00 UTC, inside `polymarket-observer.service` | `comprehensive_elo` + all three behavioral scores, genuinely combined into a decision-shaped output (a score and a tier) | See STOP CONDITION 2 above — the one genuine live decision-shaped consumer of `comprehensive_elo`/behavioral scores found |
| `scripts/resolve_legendary_markets.py` | **LIVE**, daily (`daily_maintenance.py`) | `geo_elo_active >= 2175 AND geo_accuracy_pool = 1` | `resolve_legendary_markets.py:5-9` — prioritizes which markets to resolve first |
| `scripts/promote_high_pnl_traders.py` | **LIVE**, daily | `bot_type IS NULL` | `promote_high_pnl_traders.py:23` |
| `scripts/detect_counter_signals.py` | **LIVE**, daily | `geo_elo_active >= ?, geo_accuracy_pool = 1` | `detect_counter_signals.py:101-102` — Telegram alert on a LEGENDARY trader reversing an active signal (this is the one place `LEGENDARY` still reaches Telegram, distinct from the disabled `_check_legendary_trades()`) |
| `scripts/score_str003_signals.py` | **LIVE**, daily | `derive_tier()`, geo_elo tier via multiple schema variants | `score_str003_signals.py:12-20` |
| `scripts/register_str002_signals.py` | **LIVE**, daily | `tier` (elite/legendary counts) | `register_str002_signals.py:20,54,122` |
| `scripts/legendary_positions_scan.py` | **LIVE**, weekly cron (`30 7 * * 1`, Monday) | `geo_elo_active >= 2175, geo_accuracy_pool = 1` — same explicit "NOT comprehensive_elo" note | `legendary_positions_scan.py:5,9,104` |
| `scripts/reconcile_trader_aggregates.py` | **DORMANT** | reads all 3 behavioral scores + `pnl_modifier` | present in the repo, no cron entry, no `daily_maintenance.py` step found |
| `scripts/trader_skill_metric_v2f.py` (the v2 metric) | not scheduled — one-off research script | `geo_elo` (raw stored column) used once, to define a comparison cohort ("legendary traders" for cross-checking), explicitly NOT as a live dependency — the script's own docstring: "No production writes. update_geo_elo.py / geo_elo_active / cohort membership... [not] any live path" | `trader_skill_metric_v2f.py:8,100,400` |
| `analysis/pit_geo_elo.py` (PIT-legal pool) | not scheduled — research tool | Does **not** read the live `geo_elo`/`geo_elo_active` columns at all — re-derives them point-in-time from raw trades using the *formula functions* imported from `update_geo_elo.py`, so it is unaffected by whether that job's schedule runs | `pit_geo_elo.py:3-16,36` |
| `scripts/elo_tier_causal_test.py`, `directional_skill_*.py` (the directional-skill harness) | not scheduled — one-off/prereg research scripts | `geo_elo`/tier used **only as a conditioning variable on market mispricing**, explicitly never as a skill claim (script's own docstring quotes the condemnation) | `elo_tier_causal_test.py:1-16` |
| `monitoring/monitor.py` (live ingestion, the 15-min loop) | **LIVE**, continuous | **zero** references to any ELO-family column | confirmed by direct search |
| the flagged-trader set (~40,734 addresses) | n/a | `is_flagged` is set independently of ELO (trade-volume/activity criteria elsewhere); ELO computations are scoped *to* the flagged set (`WHERE is_flagged = 1`), not the other way around | — |
| `scripts/corpus_content_extractor.py` / `corpus_reader_index.py` (trading-swarm corpus reader) | **LIVE** (currently running, PID 102652) | **zero** references to any ELO-family term | confirmed by direct search |
| `analysis/comprehensive_elo_formula.py` | LIVE (imported by both writers) | pure function, no DB access | the formula itself, not a consumer |

**Directly answering the task's four specific questions:**
- **What reads Pool B and Pool C flags, live?** Pool B (`research_excluded=0`) is read by essentially every
  research query pattern in the codebase as a standard filter (too pervasive to enumerate exhaustively) —
  it is the baseline "clean population" filter. Pool C (`geo_accuracy_pool`): the five LIVE daily/weekly
  consumers listed above (`resolve_legendary_markets.py`, `detect_counter_signals.py`,
  `score_str003_signals.py`, `register_str002_signals.py`, `legendary_positions_scan.py`), all keyed on
  `geo_elo_active`/`geo_accuracy_pool`, **none on `comprehensive_elo`**.
- **Does ingestion, the flagged-trader set, or the monitor depend on ELO output?** No — confirmed
  independent on all three.
- **Does the research programme read any ELO-family output?** Only as a labeled, explicitly-non-causal
  conditioning variable (`geo_elo` tier) in one-off tests that already state the tier is not a skill
  measure — not a load-bearing dependency. The v2 metric and PIT-legal pool are architecturally
  independent (v2f doesn't touch a live path; PIT re-derives from trades, not from stored ELO columns).
  The corpus reader: zero references.
- **The LEGENDARY gate — what still consumes it, given `_check_legendary_trades` was disabled 2026-09-09?**
  Five live daily/weekly consumers (table above) still gate real behavior (which markets get
  resolution-prioritized, which traders get promoted, which signals get scored/registered, one Telegram
  alert path for signal-reversal). The gate is very much alive operationally — only the one specific
  Telegram announcement was silenced.

---

## Part 3 — connected elements, traced individually

**`timing_score`.** Produced **only** by Writer A (Sunday) — see STOP CONDITION 1. Would stopping the
Sunday recalc stop it being refreshed? **Yes, completely** — Writer B's daily touch is a carry-forward,
not a refresh. 34,906 distinct values as of 2026-09-13 is itself a Sunday-cadence artifact — the figure
would not change again after the last Sunday recalc runs. The 2026-09-18 validation finding cited (fit
for the 169-trader cohort, 21.2% population-level contamination, stale/drift failure mode) already flags
this column's own reliability as a live open question — independent of whether the Sunday job keeps
running, this is a column whose trustworthiness was already in doubt.

**`patience_score`, `kelly_alignment_score`.** Same answers as `timing_score` — same writer, same
carry-forward-only daily touch, same complete stop if the Sunday recalc stops.

**`bot_type`.** Produced by `detect_arb_bots.py`, **independently of the ELO family** — daily, unaffected
by anything ELO-related stopping. Consumed live by Pool C's gate (`bot_type IS NULL`) and
`promote_high_pnl_traders.py`. The heatmap's wash-trading-detection candidate (mentioned in the task) was
not traced further this session — flagged under "what was not determined" below, since it's adjacent but
a distinct detection mechanism from `detect_arb_bots.py`'s arbitrage-pattern heuristic, not investigated
here.

**`elo_snapshots`.** 274,189 rows, 79 dates (current, corrected from the task's stale 232,536/70 figure).
Written daily by `snapshot_elo_scores.py`, itself calling `derive_tier()` on the geo-ELO family (not
`comprehensive_elo`) — so this table is really a daily Pool-C/tier history, not a `comprehensive_elo`
history. **No live reader** — six research/verification/migration scripts reference it, none scheduled.
Is it the only longitudinal record of anything? **No, not quite** — `analysis/pit_geo_elo.py` can
reconstruct geo_elo/geo_elo_active/Pool C membership at any past point in time directly from raw trade
data, using the same formula. What `elo_snapshots` uniquely preserves is not the *data* (recoverable from
trades) but the **actual historical computation as it was really run each day** — including whatever the
formula's behavior was on that specific date, which a today's-formula PIT reconstruction would not
replicate if the formula has changed. That is a real, narrow distinction, not a redundant one.

**Pool C's non-ELO conditions** (`geo_resolved_trades_count >= 10, research_excluded = 0,
bot_type IS NULL`). These are genuinely independent of the `geo_elo_active >= 500` threshold and could be
applied as a standalone data-quality filter (sufficient trade history + not excluded + not a detected bot)
without any ELO component at all — this session did not find anything that already does so as a distinct,
named filter, but the three conditions are structurally separable from the ELO threshold in
`column_definitions.py`'s own `POOL_C_POPULATE_SQL` (each is its own `AND` clause).

---

## Part 4 — removal impact, three scenarios

**(a) Only the Sunday full recalc (Writer A / `polymarket-sunday-elo.timer`) is disabled.**
- **Stops:** the only source of fresh `comprehensive_elo`... no — Writer B still refreshes
  `comprehensive_elo`/`pnl_modifier` daily, so `comprehensive_elo` itself keeps moving. What stops
  completely: `timing_score`, `patience_score`, `kelly_alignment_score`, `behavioral_modifier`,
  `advanced_modifier` — frozen forever at the last Sunday's values (STOP CONDITION 1).
- **Goes stale, and how fast:** those five columns, immediately (next Sunday never comes). Nothing else —
  `geo_elo`/tier/Pool B/Pool C/LEGENDARY are entirely on the independent daily `update_geo_elo.py` path and
  are unaffected.
- **Fails loudly or silently:** **silently** for the `analysis_scheduler.py` composite-score consumer
  (STOP CONDITION 2) — it keeps running daily, keeps producing dated reports, gives no indication its
  behavioral inputs stopped moving. `audit_invariants.py`'s and `diagnostics.py`'s coverage checks
  (`IS NOT NULL`) would **not** catch this either — the columns aren't NULL, they're just frozen at a
  real, previously-valid value, which those specific checks don't distinguish from a fresh one. No loud
  failure was found anywhere in this trace.

**(b) Only the daily `update_geo_elo` is disabled.**
- **Stops:** `geo_elo`/`geo_directionality_score` refresh for any trader who crosses the 5-qualifying-
  trade threshold newly, or accumulates new geo trades. `geo_elo_active`'s time-decay component
  (`compute_geo_elo_active`, gated on `last_trade_ts`) would still mechanically decay existing values even
  without new writes, since it's computed from `geo_elo` + trade recency, not re-derived only inside this
  script — worth flagging as a nuance: **`geo_elo_active` can still change (decay downward) even with this
  job disabled**, wherever it's computed on the fly rather than read as a stored column; this session did
  not fully verify which of the five live Pool-C consumers compute it fresh vs. read a stored value, so
  the exact behavior under scenario (b) is not fully pinned down (see "what was not determined").
- **Goes stale, and how fast:** Pool C membership itself (via `refresh_pool_c()`, also called from
  `update_research_exclusions.py` independently, so Pool C's *non-ELO* conditions would still refresh
  daily) would stop reflecting new geo-ELO crossings, but wouldn't freeze entirely the way scenario (a)'s
  behavioral scores would.
- **Fails loudly or silently:** not established with confidence this session — flagged as open.

**(c) Both disabled.**
- Union of (a) and (b): `comprehensive_elo`/`pnl_modifier` keep moving via Writer B (which does not depend
  on Writer A or `update_geo_elo.py` — it only reads whatever's already in the DB and re-applies P&L), but
  the behavioral three freeze immediately (a), and geo_elo/Pool C stop gaining new members (b). **The five
  live LEGENDARY/Pool-C consumers (Part 2) would keep running against an increasingly stale, no-longer-
  growing Pool C** — new traders who *should* qualify never would, existing members never re-evaluate.
  This compounds (a)'s silent-staleness finding onto operationally-live signal generation, not just a
  reporting artifact — the more consequential version of the same risk.

---

## Part 5 — future potential, per element (honest, not advocacy)

**`timing_score`.** Future question it could answer: whether execution timing quality is itself a
persistent, tradeable signal — but the 2026-09-18 validation already found 21.2% population-level
contamination outside the 169-trader cohort it was validated on, so its *current* form is not yet a sound
input to anything beyond that cohort. Not covered by a sound replacement that this session found — the v2
metric and directional-skill harness measure directional accuracy and market mispricing, not execution
timing specifically; this appears to be a genuinely distinct question. **Does it need ongoing computation,
or would a frozen copy suffice?** For the 169-trader cohort it was validated on: a **frozen archive would
suffice** — that population isn't growing in a way this column tracks live, and the contamination finding
means broader population coverage isn't trustworthy today regardless of freshness. For any future
narrower, re-validated population: would need ongoing computation only if that population itself keeps
changing membership; a periodic (not necessarily weekly) recompute would likely serve as well as the
current cadence.

**`patience_score`, `kelly_alignment_score`.** Not validated to any comparable degree this session found —
no equivalent of the 2026-09-18 timing_score validation was located for these two. Future question: same
family as timing_score (behavioral-consistency signal), unvalidated. Archive vs. ongoing: same reasoning
as timing_score — a frozen copy of the currently-flagged population's current values preserves whatever
value exists today; ongoing computation only matters if the underlying trade behavior for that specific
population keeps evolving in a way worth re-measuring, which was not established either way this session.

**`bot_type`.** Live and consumed (Part 2/3). The heatmap's wash-trading-detection candidate is adjacent
but distinct — not traced this session (see "what was not determined"). Needs ongoing computation to stay
useful for its current live role (gating Pool C, excluding traders from `promote_high_pnl_traders.py`) —
new bots keep appearing, so a frozen archive would not serve its operational purpose, only a historical
research one.

**`elo_snapshots`.** Future question: reconstructing what the system's *actual* daily output was on any
past date, including formula-era-specific behavior a PIT recomputation with today's formula wouldn't
replicate. Not covered by a sound replacement — `pit_geo_elo.py` covers "what would the current formula
have produced then," not "what did the system actually say then," which are different questions for
anyone auditing past decisions or past Telegram alerts. **This is squarely an archive-value case**: the
value is already banked in 79 days of history; ongoing daily snapshots only add value if something is
still consuming daily-resolution granularity going forward, which this session found nothing live doing —
a coarser, or fully stopped, cadence would likely preserve the same practical research value.

**Pool C's non-ELO conditions.** Future question: whether trade-count + not-excluded + not-a-bot is a
useful "sufficiently-observed, clean" filter independent of any skill claim, for research that wants a
data-quality baseline without importing the condemned geo_elo threshold. Not currently implemented as a
standalone named filter anywhere this session found. Needs no ongoing ELO computation at all to exist —
it's definitionally independent of the `geo_elo_active` threshold already.

---

## Part 6 — rating as a concept, without designing anything

The project's standing objective ("rate traders continuously") describes exactly what ELO-style rating
provides structurally: **incremental, recency-weighted, updated without a full recompute over the whole
history each time** — new information (a resolved trade) updates a rating in one step, not by re-deriving
it from the complete trade history. The v2 metric (and, by extension, the directional-skill harness built
on it) is architecturally a **batch computation over a fixed window** — it re-derives its result from a
population/tape snapshot each time it's run, not incrementally from the last state plus new evidence.

**Is there a capability a correctly-built incremental rating would provide that v2/the directional harness
do not?** Yes, one specific one, structural rather than about accuracy: **continuous, low-latency
availability of an up-to-date per-trader number without re-running a batch analysis.** An ELO-style update
can, in principle, incorporate a single newly-resolved trade in O(1) work per trader touched, immediately
reflecting it; v2's batch design means "the current number" is only as fresh as the last full run,
whatever that run's cost and cadence are. If a future consumer genuinely needs a number that's current
*right now*, incrementally, rather than current *as of the last scheduled batch*, that is a real capability
gap batch methods don't close by being more accurate.

**The current `geo_elo` is explicitly not that capability, delivered correctly.** The five defects that
condemned it for skill-ranking (MASTER_HANDOVER_2026-08-15) are about what it *measures* and how
soundly — a sign error, an improper scoring rule, contamination, double-counting, uncalibrated parameters.
None of those defects are inherent to the *incremental-update mechanism itself*; they're in the specific
formula and its calibration. So this session's answer is: the incremental-update *property* has standalone
value that a batch method structurally cannot provide, but nothing currently running is a demonstration
that this property has been captured correctly — the existing geo_elo is the wrong implementation of a
potentially-right idea, not evidence the idea itself is empty. Not designing a replacement, per scope —
only noting that "rate continuously" and "geo_elo is broken" are two separate facts, not one.

---

## What was not determined

- **Whether `geo_elo_active`'s live consumers (the five Pool-C/LEGENDARY-gated scripts) each compute it
  fresh on the fly or read a value only ever set by `update_geo_elo.py`'s own run.** This determines
  scenario (b)'s exact staleness behavior and whether it fails loudly anywhere — not established with
  confidence.
- **The heatmap's wash-trading-detection candidate's relationship to `bot_type`/`detect_arb_bots.py`** —
  named as adjacent in the task, not traced this session.
- **Whether `reports_generated` (feeding the daily Telegram summary) definitely includes the composite-
  scores CSV path by filename every day**, or only under some condition — the mechanism is confirmed to
  exist and run daily; the exact Telegram message content was not independently rendered/verified this
  session.
- **Scenario (a)'s and (b)'s exact behavior for the `audit_invariants.py` coverage check
  (`kelly_alignment_score IS NULL OR ...`)** if this project later adds an age/staleness check to that
  invariant — not evaluated, since none exists today (confirmed: the check is presence-only, not a
  freshness check, in the current code).
- **`reconcile_trader_aggregates.py`'s original purpose and why it was never wired into `daily_maintenance.py`**
  — graded DORMANT, not investigated further for intent.

---

## Corpus run confirmation

- **Start of this task:** PID 102652, elapsed 4:12:49 — running.
- **End of this task:** PID 102652, elapsed 4:17:58, `{"processed": 118, "failed": 6}` (failures are
  isolated timeouts, not a stall — most recent success postdates the most recent failure) — running,
  healthy, unaffected by anything in this task.

**Recommends nothing. Oscar decides.**
