# Thesis Population Lineage — Is It Still Broken, and How Did We Get Here

**Date:** 2026-09-04. **READ-ONLY.** No writer modified, no market resolved,
no classifier run, no schema touched, no `--persist` invoked anywhere in
this task. One exception, itself read-only and pre-existing-method: Part 2e
re-runs the 2026-08-20 sizing census's own `G`-stratum CLOB check live
(244 GET requests against `clob.polymarket.com`, the identical read-only
method already used and approved twice in this arc) — no DB write, no
category write, no resolution write. Output committed alongside this doc:
`data/characterizations/discovery_gap_sizing_q2_census_20260904.json`
(first-repo).

**Tagging: `[V]` verified this session (query/code/log given), `[I]`
inferred and marked as such.** Every claim in the task prompt is treated as
a hypothesis, checked against source documents and live DB/code state, not
assumed.

---

## HEADLINE

**The thesis population is still broken today, in essentially the same
shape as on 2026-08-20 — and the eleven days of work between then and now
have moved it by a rounding error.** The canonical backtest population
(`column_definitions.py::BACKTEST_WINDOW_BASE_WHERE`) sits at **9,563**
markets today, up from an estimated **~9,079** around 2026-08-16 [I,
derived below] — growth of roughly **+500 markets over three weeks**, of
which **242 are directly traceable** to the entire discovery-gap-closure
sweep and classifier arc combined. The sweep itself resolved **215,887**
markets; **99.88% of them are still `category='Unknown'`** and therefore
invisible to the thesis regardless of being `resolved=1`. The tool built
specifically to fix that — the LLM relevance classifier — **failed its own
recall gate** on 2026-09-03 (documented separately,
`2026-09-03-gate-result.md`). The original 08-20 finding (203 markets)
**is fully closed** — all 203 are now resolved, correctly categorized, and
in the canonical population. But the mechanism that produced that finding
is **not fixed**: a freshly-drawn census of the same population shape today
finds a **worse** rate (75.0% of new arrivals already resolved-and-
undiscovered, vs. 67.4% on 08-20), and a live code-level cause for why is
identified in Part 2 below, not previously documented anywhere in this
arc's decision record.

---

## PART 1 — THE BELIEF CHAIN

| Date | Document | Belief established | Basis |
|---|---|---|---|
| 08-20 | `discovery-gap-sizing-prereg.md` / `-result.md` | The canonical-relevance population (**Q2**, 317 markets: Geo/Elec, has trades, gap-clean, dateless+unresolved-per-DB) is **67.4% already resolved and undiscovered** on CLOB (203/301 determinate) | **VERIFIED** — a full census (not a sample), pre-registered before any CLOB call, cross-checked against `tape_end` (15/15 corroborate) |
| 08-20 | `discovery-gap-thesis-intersection.md` | The 203 markets have **real, substantial, currently-invisible exposure** in the published thesis cohort (71.4% of OOS survivors) and placebo (60.2%), though structurally unable to move the *published* number today (100% of touching positions are `pending`) | **VERIFIED** — direct set intersection using `trader_skill_metric_v2f.py`'s own unmodified functions, zero recomputation, zero persistence |
| 08-21 | `discovery-fix-assessment.md` | Fixing the discovery gap for the **backlog** requires repairing `backfill_market_dates.py` (an existing writer that already fetches the needed CLOB response and discards the winner field), not building a new script. Fixing it for the **bleeding** (new markets arriving dateless) requires widening past `--geo-only`, because **category-scoped candidate selection inherits a separate, much larger classification lag** — 99.9% of the base dateless population is `category='Unknown'`, and the Q2 population's flatness across a day is explained by that lag, not by the discovery gap having stopped | **VERIFIED, then reasoned to a decision.** The classification-lag mechanism was checked directly (513,574/514,043 = 99.9% `Unknown`, `backfill_market_categories.py`'s actual daily throughput read from its log). **The decision to widen scope to the full ~515k population was an explicit, reasoned choice, not an inherited default** — it is argued for in writing, on evidence available that day, in this exact document. **What was NOT checked at this point, and should have been: how fast the classification lag itself clears** — the growth-rate finding established that Unknown markets *eventually* get classified, but not at what rate, or over what horizon. That question is the one that later turned out to be decisive (08-30), and it was cheap to ask on 08-21 already (the log this ends up read from, `logs/category_backfill.log`, already existed and was already running daily). |
| 08-21 | `discovery-gap-closure-prereg.md` | Full operational plan: repair `backfill_market_dates.py` (add a `mark_market_resolved()` assertion branch alongside its existing proxy-date branch), widen scope, sweep the ~515k backlog, then run a **second, separately-named measurement** (§E) against the corrected data, side by side with the untouched result of record | **PRE-REGISTERED**, thresholds and abort conditions fixed before any sweep call. The first implementation attempt of step 1 **failed its own gate** (0 resolved found against an expected ~203, root-caused to a fetch/usability conflation bug) and was fixed and re-verified before proceeding — the discipline caught a real defect, not a false alarm. |
| 08-22 | `tranche1-completion.md` | **Tranche 1 = the original 317-market Q2 population itself**, re-swept with the repaired writer. **203/98/16 — an exact match to the 08-20 census.** This is the *only* tranche/segment that touched the 317 population. `Geo/Elec resolved+gap-clean` moved **10,589 → 10,792, +203, exact.** | **VERIFIED**, re-derived live, not carried forward from 08-20 |
| 08-22 → 08-26 | Tranche 2 + Segments 1-4 | Sweep the **widened** population (~510k-524k, later carving out 15,427 structurally-unresolvable combo/parlay markets found mid-run). **Not the 317 population** — a categorically different, much larger population, swept for the reasons established 08-21. 231,000 markets drawn in; ~215,000 walked; 210,485 cumulative accepted `mark_market_resolved()` writes by 08-27. | **VERIFIED**, execution logs and terminal markers read directly this session. Segment 4 aborted at 101/133 batches (76%) on a pacing threshold later traced to a nightly-backup starvation interaction, not a sweep defect. |
| 08-26/27 | `post-segment4-status.md`, `session-summary-0825-0827.md` | Sweep **paused**, pending three named prerequisites for segment 5 (resume batch 102, re-key exclusion on processed not materialized IDs, implement launch-time-dependent `max_batches`). Remaining candidate population: 291,148. | **STATED AS A PAUSE, NOT A STOP** — but no segment 5 document exists anywhere in the decision record, and the segment 3/4 checkpoint and terminal-marker files remain **uncommitted in the working tree to this day** (`git status`, this session) — direct, physical evidence the pause was never formally closed out or resumed. |
| 08-30 | `geo-backlog-and-category-reach.md` | **The sweep's output cannot reach the thesis population.** Of 214,413 sweep-resolved markets, exactly **225 (0.10%)** pass `m.category IN ('Geopolitics','Elections')` — the sole and total blocker. Real classification throughput: ~19-32/day against a 214,155-market Unknown backlog **within the sweep-resolved population alone** — 9.8 to 30.9 years to clear. | **VERIFIED**, first time this specific question was asked and measured precisely — 9 days after the sweep began, and 3 days after the sweep paused. **This is the belief that should have been checked before the sweep, not after it.** See Part 4. |
| 08-31 | `why-unknown-investigation.md` | Gamma itself carries **no category data** for these markets (0/97 sampled, including genuine election markets) — the source cannot fix this, a title-based classifier is structurally required, not merely a better cache/backfill path | **VERIFIED**, live Gamma API sampling this arc's own session |
| 08-31 → 09-04 | Relevance-classifier design, build, gate | Build an LLM classifier to reclassify the Unknown backlog (including the sweep's 214k). **Precision passes; recall fails** — 90.35% overall vs. ≥95% required, all 6 per-stratum cells fail. Diagnostic sample: 79% genuine classifier misses, not stale labels — the recall gap is real. **§3.11(a) abandon indicated over (b) retry**, per this task's own prior provisional read. | **VERIFIED** — `2026-09-03-gate-result.md`, `2026-09-04-gate-recall-diagnosis.md`, produced by this session's immediately preceding task. **No adjudication (§3.10) completed; Oscar's call, not made.** |

**Direct answer to the task's specific question:** the sweep's scoping
decision (317 → full dateless population) was **explicitly made**, on
08-21, in writing, with evidence cited — it was **not inherited** silently.
What *was* effectively inherited without re-checking, for nine days, was
the implicit assumption behind that decision: that resolving the widened
population would eventually translate into thesis-relevant category
coverage at some usable rate. That specific number — the classification
throughput — was not measured until 08-30, well after the 231,000-market
sweep had already consumed essentially all of its wall-clock cost.

---

## PART 2 — IS THE THESIS POPULATION ACTUALLY BROKEN TODAY?

### 2a. Canonical population today `[V]`

Using `monitoring/column_definitions.py::backtest_window_sql()` directly
(not a hand-rolled equivalent), window_start far enough back to capture
everything (`2000-01-01`, open-ended):

**9,563 markets** satisfy `BACKTEST_WINDOW_BASE_WHERE` today
(`m.resolved=1 AND m.category IN ('Geopolitics','Elections') AND
(trade_gap_flag=0 OR NULL)`, INNER JOIN to at least one trade). Split at
`T_SPLIT = 2026-04-01`: **7,251 pre-split** (tape_end < T_split), **2,312
post-split** (tape_end ≥ T_split) — these sum exactly to 9,563, confirming
internal consistency of the canonical function's own half-open-interval
composition.

A plain count without the trades-join requirement (`m.resolved=1 AND
category IN (...) AND gap-clean`, no `EXISTS trade` condition) returns
**11,006** — 1,443 more, all zero-trade markets, correctly excluded from
the canonical backtest population by its own INNER JOIN.

### 2b. Comparison to 2026-08-15 `[V]/[I]`

No frozen snapshot exists at exactly 08-15 or 08-16 for this predicate —
the only frozen row in `backtest_population_snapshots` is
`bt_pop_2025-11-01_v1`, taken 07-24 (4,712 markets, window_start=2025-11-01).
Re-running that identical window today returns **5,235** — **+523 over 42
days**, ordinary background growth, unrelated to the sweep (the sweep's
own resolved population is almost entirely `category='Unknown'`, so it
barely touches this number either).

For the all-time predicate specifically: `MASTER_HANDOVER_2026-08-15.md`'s
08-16 fingerprint states **`Geopolitics/Elections resolved+gap-clean =
10,448`** [V, quoted directly] — this is the **plain-count** form (no
trades-join stated in that fingerprint's own framing). Today's plain count
is **11,006**, **+558 over 19 days**. Applying today's observed zero-trade
fraction (1,443/11,006 = 13.1%) to back out an estimated with-trades figure
for 08-16 gives **≈9,079** [I — this scales today's ratio onto 08-16's
count; not independently measured at 08-16, offered as a bounded estimate,
not a precise historical figure]. **On that estimate, the canonical
(with-trades) population grew from ~9,079 to 9,563 — roughly +484 markets
over three weeks.**

**Of today's 9,563, exactly 242 carry `resolution_evidence_source IN
('clob','gamma')`** [V] — the marker of the new canonical write path this
entire arc built (the sweep's `clob` writes, plus 8 markets from the
`fast_resolution_check.py` Gamma `closedTime` fix). **This is the
directly-attributable contribution of eleven days of infrastructure work:
242 markets, against a population estimated to have grown by ~484-500 over
the same period.** The remaining ~250-350 markets' worth of growth is
ordinary background activity (legacy writers classifying already-resolved
markets, M9's daily keyword pass, etc.) that would have happened with or
without this arc.

### 2c. The fate of the original 203 `[V]`

Checked all 203 market_ids from
`discovery_gap_sizing_20260820T211955Z.json`'s `classification=="resolved"`
rows against today's live DB, three conditions checked **separately**, not
assumed to travel together:

| Condition | Result |
|---|---|
| `resolved = 1` | **203/203** |
| `category IN ('Geopolitics','Elections')` | **203/203** (106 Geopolitics, 97 Elections) |
| `trade_gap_flag` clean | **203/203** |
| Inside the canonical population today (all three above + has-trades) | **203/203** |

**All three conditions are satisfied for all 203 — closed, cleanly.** This
is not surprising once traced to its source: Q2's own population
definition already required `category IN ('Geopolitics','Elections')`
*before* the 08-20 census ever ran (these markets were dateless and
unresolved, but already correctly tagged) — so the category condition was
never actually at risk for this specific 203-market set. **Tranche 1
(08-22) is the exact mechanism that closed this**, per Part 1: it resolved
exactly this population, exactly 203, exact match to the census. **The
narrow 08-20 finding is fully resolved.** What it does not mean is
addressed in 2d/2e below.

### 2d. Is 203/317 representative of the sweep's actual payoff? `[V]`

No. The 203 were drawn from a population that was *by construction*
already Geo/Elec-tagged — the category gate was never the obstacle for
this specific set. The sweep's *actual* scope (the widened ~510k-524k
population) is overwhelmingly `category='Unknown'`, and that is where the
category gate bites: of **215,887** sweep-resolved markets today (up from
214,413 on 08-30 — the daily `backfill_market_dates.py` step continues to
find a trickle each day), **215,620 (99.88%) are still `category='Unknown'`
today**. Only **267** (142 Elections, 125 Geopolitics — up from 225 on
08-30) have ever been reclassified. **The 203-market success and the
215,887-market sweep are, in payoff terms, almost entirely disjoint
stories** — the arc solved the small, already-tagged residual cleanly, and
made only trickle-level progress (267 of 215,887, 0.12%) on the actual bulk
of what it swept.

### 2e. The current equivalent of the 08-20 finding — re-run live, today `[V]`

Re-ran the 08-20 sizing prereg's own **Q2 census method exactly**
(`scripts/discovery_gap_sizing.py`'s own `get_stratum_g`, `build_clob_id`,
`query_clob`, `run_stratum` functions, unmodified, imported directly — not
reimplemented), against today's live Q2 population. Read-only: 244 GET
requests to `clob.polymarket.com`, zero DB writes. Output:
`data/characterizations/discovery_gap_sizing_q2_census_20260904.json`.

| | 08-20 (n=317) | Today (n=244) |
|---|---|---|
| Resolved | 203 (64.0%) | **100 (41.0%)** |
| Open | 98 | 128 |
| Indeterminate | 16 (5.05%) | 16 (6.6%) |
| Resolved / determinate | 67.4% | **43.9%** |

**The gap has not closed — it is smaller in absolute count but the
population itself has not stopped producing new cases at a comparable, or
worse, rate.** Isolating the **132 markets that entered this population
for the first time since 08-20** (i.e., excluding the 112 that were already
in the original 317 and never got resolved or discovered): **99 of 132
(75.0%) are already resolved and undiscovered** — a *higher* rate than the
original 67.4%. **This is the current-equivalent finding, and it is worse
per-new-arrival than the finding that justified eleven days of work.**

**Root cause identified this session, not previously documented anywhere
in this arc [V, code read]:** `daily_maintenance.py`'s `backfill_market_dates.py`
step still runs at `--limit 2000`, **unscoped** (`--geo-only` was
deliberately dropped 08-21, permanently, to fix the classification-lag
visibility problem) — but the code's own comment states this 2000 figure
was **always meant to be a temporary bridge value** ("2000 dilutes the
permanently-dead ~98-row CLOB-purged prefix... gives a bounded, recoverable
first live sample of the widened step's real behaviour... **35000 remains
the intended steady-state value once the staged sweep has run**"). The
sweep never finished (Part 1); nobody has since raised the limit.
`_sweep_recently_active()` — the mechanism that holds this step down while
a segment is live — correctly reports **not active today** (the segment 4
checkpoint is ~9.6 days stale, far past its 1800s recency window) [V,
computed this session], so the step *is* running, unheld, every day — just
at the stale bridge value. **Consequence, quantified:** 2,000 candidates
drawn (with no `ORDER BY`, no random sampling — a plain `LIMIT` scan) out
of a **390,804**-row unscoped candidate pool is a 0.51% daily sweep of that
pool; the 244-row Geo/Elec-tagged sub-population, when it was scoped
directly (`--geo-only`, pre-08-21), was checked **exhaustively every single
day**. **Dropping `--geo-only` fixed one real problem (newly-classified
markets becoming invisible to a category-scoped query) and created another,
never revisited: it diluted the daily catch-up rate for the specific,
already-correctly-tagged, highest-priority sub-population by roughly two
orders of magnitude**, with no compensating restoration of the `--limit`
value the code's own comment says was always the intended next step. This
is a live, current, uncorrected defect — not historical.

---

## PART 3 — WHAT WOULD THE SECOND MEASUREMENT SEE?

### 3a. Markets not in the 08-15 population that are in it now `[V]/[I]`

**Precisely identifiable: 242 markets** — every market in today's canonical
population carrying `resolution_evidence_source IN ('clob','gamma')`, the
signature of this arc's own canonical write path (Part 2b). Of these,
**181 have `tape_end < T_split`** (could affect **cohort qualification**),
**61 have `tape_end ≥ T_split`** (could affect the **measured OOS edge**
directly).

**Not precisely identifiable without a historical snapshot:** an estimated
further **~250-350 markets** [I, from the population-growth arithmetic in
2b] entered via ordinary, pre-existing (non-canonical) writers over the
same three weeks — background M9 classification of markets that were
independently already `resolved=1`, etc. These cannot be isolated by
market_id without a frozen 08-15 population list, which does not exist.
**This is a genuine limitation of this analysis, stated plainly rather than
papered over**: Part 3b-c below can only be answered precisely for the
242-market identifiable subset.

### 3b. Do these carry cohort/placebo-relevant positions? `[V]`

Reconstructed today's presplit-qualifying cohort and matched placebo via
`trader_skill_metric_v2f.py`'s own unmodified functions
(`build_presplit_cohort`, `match_control`, same `SEED=42`, same `T_SPLIT`),
**read-only, no `--persist`** — same discipline as the 08-20 intersection
doc. Today's re-run (subject to the same ongoing, already-documented DB
drift as every prior re-run in this arc): **169** presplit-qualifying
cohort, **141** OOS survivors, **169**-trader matched placebo pool, **118**
OOS-survivor placebo.

| | Traders touching the 242-set | Positions on the 242-set | Already `won`/`lost` |
|---|---|---|---|
| OOS-surviving cohort | 114/169 (67.5%) | 981 | **980 (99.9%)** |
| OOS-surviving placebo | 92/169 (54.4%) | 615 | **611 (99.3%)** |

**Unlike the 08-20 finding (100% `pending`), the vast majority of these
positions have already resolved to `won`/`lost`.** This means these 242
markets' effect is **not hypothetical or future** — it is already flowing
into any fresh, unpersisted re-run of the pipeline today, and has been for
some time (consistent with `evaluate_new_trader_results.py` running daily
against the now-much-smaller pending backlog this arc's own 08-30 doc
already characterized). It has **not** flowed into the persisted result of
record: `metric_v2f_oos_result` still holds exactly the 08-15 row
(`generated_at=2026-08-15T19:36:56`, confirmed unchanged this session) —
no `_corrected` table (§E of the closure pre-registration) has ever been
created. **The formal second measurement has not been run.**

**Direction, computed the same way as the original Q6 [V]:** restricting
today's OOS positions to the 242-set specifically vs. everything else:

| | n (in 242-set) | mean edge (242-set) | n (rest) | mean edge (rest) |
|---|---|---|---|---|
| Cohort | 161 | **−0.0410** | 3,634 | +0.0226 |
| Placebo | 102 | **−0.0316** | 2,708 | +0.0345 |

Both cohort's and placebo's newly-identifiable exposure trends **negative**
— pulling the pooled mean down by a similar small amount on both sides
(cohort: 0.02264 → 0.01994 including the 242-set; placebo: 0.03451 →
0.03211). **The cohort-vs-placebo gap moves by about −0.0003** when the
242-set is included vs. excluded — a negligible shift relative to either
figure's own uncertainty. (Note: today's live re-run shows placebo's point
estimate *exceeding* cohort's, +0.032 vs +0.020 — itself a consequence of
the already-documented, unrelated DB-drift non-reproducibility, not of the
242-set; flagged for completeness, not chased further here.)

### 3c. Materially different population, or essentially the same? `[V]`

**Essentially the same population.** The identifiable, attributable new
material (242 markets, 981+615=1,596 positions) is a **4.2%** addition to
the cohort's OOS position count (161/3,795) and a **3.6%** addition to the
placebo's (102/2,810) — small relative to either, and its own internal
direction (negative for both sides, roughly equally) does not favor one
side over the other. **A second measurement run today, even a fully
executed one, would not be expected to move the headline gap materially**
— not because the underlying question has been answered, but because
eleven days of infrastructure work added a population too small, and too
evenly negative across both arms, to shift a comparison whose entire point
was statistical power in the first place.

---

## PART 4 — WHAT WAS THE WRONG TURN, IF ANY

**Was scoping the sweep to the full dateless population a mistake?** —
**No, not given what was known on 08-21.** The decision was explicit,
written, evidence-based: the 317-population's flatness across a day was
correctly diagnosed as a classification-lag artifact (99.9% of the base
population `Unknown`), not as evidence the discovery gap had stopped. Given
that diagnosis, scoping narrowly to `category IN (...)` would have
systematically undercounted a real and growing phenomenon. This was the
right call **on the question it was answering** — whether to scope narrow
or wide.

**Was there a cheaper path available and not taken?** — **Yes, and it is
precisely identifiable.** The question that actually determined whether the
widened sweep would ever matter to the thesis — *how fast does
`category='Unknown'` clear into `Geopolitics`/`Elections`* — was
answerable in minutes from a log file that already existed
(`logs/category_backfill.log`, already running daily, unmodified since
before this arc began) and was not asked until **08-30, nine days and a
231,000-market, multi-day, multi-night, backup-guard-building sweep
later.** Reading that log on 08-21 (or even 08-20) would have shown the
same ~19-32/day classification rate found on 08-30, and the same
9.8-30.9-year backlog-clearing horizon — a fact that changes the entire
calculus of whether a 515k-market sweep is worth running *before that rate
is separately fixed*, not after. This is the project's own first standing
rule (`MASTER_HANDOVER`, §"HOW WE WORK", item 2): **"test the premise
before building the instrument."** The premise here — "resolving these
markets will make them reach the thesis population" — was never tested
before the instrument (the sweep, its execution model, its abort
conditions, its backup-overlap guard) was built. It was tested nine days
later, by which point the instrument had already consumed essentially all
of its wall-clock and engineering cost, for a payoff (267 of 215,887
sweep-resolved markets ever reaching the target categories, 0.12%) that the
cheap test would have predicted almost exactly.

**What belief propagated for multiple sessions without being re-checked,
and what would have caught it?** — **The belief that "resolved" and
"reaches the thesis population" were close enough to the same thing to
justify sequencing the sweep before the classification question.** This
propagated from 08-21 through 08-27 (the entire tranche/segment sweep) —
six documents, four sweep segments, a backup-starvation investigation, and
a `flock`-guard implementation — without anyone re-reading
`column_definitions.py`'s own `BACKTEST_WINDOW_BASE_WHERE`, which states
plainly, in one line, that `category IN ('Geopolitics','Elections')` is a
**required, independent** clause, not a formality that `resolved=1` implies
or trends toward. **What would have caught it:** the same discipline this
project used successfully elsewhere in this exact window — checking a
striking number against the actual predicate it's meant to satisfy, not a
proxy for it (§"boundary check" in `MASTER_HANDOVER`'s standing rules). The
08-20/08-21 sizing work did this correctly *for the narrow 317 population*
(which is why the 203 finding is real and now fully closed, per Part 2c)
but the check was never generalized to the *widened* population the team
decided, on the same day, to sweep instead.

**A second, smaller wrong turn, live and uncorrected today (Part 2e):**
`--limit 2000` on `backfill_market_dates.py`'s daily invocation was
explicitly written as a temporary bridge value pending the sweep's
completion, with 35,000 named in the code's own comment as the intended
next step. The sweep paused without completing (08-26/27) and was never
formally closed out — no document declares it done, abandoned, or
resumed — and the bridge value was never revisited. The result: the daily
catch-up mechanism for the specific, small, highest-priority Geo/Elec
sub-population is currently running at roughly two orders of magnitude
below the coverage it had before `--geo-only` was dropped, with nothing in
the codebase or the decision record flagging that this is happening. This
is not a historical mistake to learn from — it is a live, small,
easily-fixed defect this task found while looking for something else,
exactly the kind of thing the "test the premise" discipline is meant to
surface early rather than nine days (or, in this case, still-ongoing) into
a sweep.

**Do not soften this:** eleven days of real engineering discipline —
pre-registration, abort conditions, a backup-starvation root cause found
through genuine diagnostic rigor, a verified `flock` guard — were spent
executing a plan whose central premise (that resolving markets would feed
the thesis) was checkable in minutes and was not checked until the plan was
essentially finished. The discipline was excellent; the sequencing was
backwards. The thesis measurement has not moved since 2026-08-15 because
the actual bottleneck (category classification, not resolution discovery)
was identified only after the resolution-discovery work was already spent,
and the tool built to address the bottleneck once found has itself just
failed validation.

---

## Reproducibility

- Canonical population counts (2a): `python3 -c` querying
  `monitoring.column_definitions.backtest_window_sql`, this session, no
  script committed (single ad hoc query, not a decision-carrying number
  requiring its own artifact — the underlying function is already
  canonical and version-pinned).
- Current Q2 census (2e): re-run of `scripts/discovery_gap_sizing.py`'s own
  functions, live, this session. Output committed:
  `data/characterizations/discovery_gap_sizing_q2_census_20260904.json`
  (first-repo).
- Cohort/placebo reconstruction (3b): `trader_skill_metric_v2f.py`'s own
  `build_presplit_cohort`/`match_control`/`measure_oos`, unmodified,
  `--persist` never invoked, same pattern as
  `discovery_gap_thesis_intersection.py`. Not separately committed as a
  script this session (ad hoc read-only reproduction, same discipline the
  08-20 intersection doc used); the resulting cohort/placebo trader lists
  are in `/tmp` only and not preserved past this session — a future task
  wanting to re-check this should re-run the same three functions live,
  not treat this document's 169/141/118 figures as a frozen artifact (they
  are already known to drift day to day, per the standing reproducibility
  finding this arc has documented since 08-16).

---

*Generated 2026-09-04. Sources: every document cited inline above (all
`trading-swarm/brain/decisions/`), `monitoring/column_definitions.py`,
`scripts/trader_skill_metric_v2f.py`, `scripts/backfill_market_dates.py`,
`scripts/daily_maintenance.py`, `scripts/discovery_gap_sizing.py`, live DB
queries and one live CLOB census (244 calls) this session. Read-only
throughout.*
