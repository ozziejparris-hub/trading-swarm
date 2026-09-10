# Copy-Trade Decay Measurement — Pre-Registration

**PRE-REGISTRATION ONLY. Compute nothing, produce no curve, write no
analysis code.** This document fixes the method before any result exists,
per the standing rule on reproducible decision numbers. Per
`2026-09-05-canonical-skill-metric-design.md` (`86a7b4e`) §2, this runs
**before** the metric's three components (§3 of that design) precisely
because it is the least contaminated by that design's own §9 circularity
finding — decay is a relative measure (edge at N vs. edge at 0 on the same
positions), so selection bias on the cohort's *level* has far less purchase
on its *shape*. A collapsed decay curve moots every downstream question in
that design.

Tags: **[V]** verified this session (query/code/doc cited), **[I]**
inferred or a fixed judgment call, marked as such.

---

## 1. The measurement, precisely

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. The "next trade at or after `entry_timestamp + N`" rule and the
inclusion of own-trader trades below are PRESERVED and reaffirmed; the
amendment adds the explicit price *source* (the executed trade tape,
`trades.price` — not `price_at()`/CLOB) and its known limits. Nothing
below is deleted.**

**AMENDED AGAIN 2026-09-10b — see "Amendment 2026-09-10b" at the end of
this document. The "next trade in that market" rule below and in
Amendment 2026-09-10 item E is silent on the substituted trade's
*outcome*; the 2026-09-10 run substituted opposite-outcome trade prices
(≈ 1 − p) unconverted for 37.6% of N=15min substitutions
(trading-swarm `3c22b0c`). Amendment 2026-09-10b fixes the outcome rule:
CONVERT opposite-outcome prices `q → 1 − q`, with an
outcome-matched-only curve reported alongside as a robustness check. Use
the 2026-09-10b rule when this is run.**

For each position, hold the trader's actual **direction** and the market's
actual **resolved outcome** fixed. Substitute, in place of the trader's own
`entry_avg_price`, the price a copier would have paid entering at
`entry_timestamp + N`. Recompute edge (`won − substituted_price`) from
that.

**Exact price lookup, fixed now**: the **next** trade in that market at or
after `entry_timestamp + N` — not the *nearest* trade. "Nearest" would
permit a trade timestamped *before* `entry_timestamp + N` if it happened to
be closer in time than the next one after, which is causally wrong for a
copier: they cannot transact on a trade they haven't observed yet. Only
"next at or after" respects the direction time actually runs for a copier.
A single trade's price is used (not a window-average) — the simplest
construction that answers "what would a market order have paid at that
moment," and consistent with this design's own stated principle that
fewer, simpler mechanisms are the objective. Where that next trade is far
in time from the nominal `N` (thin markets), the resulting noise is made
visible via the realised-delay reporting in §5a, not smoothed by
averaging.

**Own-trader trades are included** in the lookup universe. This is a
deliberate, justified departure from the endogeneity concern that excluded
own-trades from the Part-1 fair-price-benchmark assessment in the
feasibility read: that exclusion mattered there because the goal was
isolating a price *independent of the trader's own information* for
skill-attribution. Here the question is purely mechanical — "what would a
copier physically have had to pay" — and a copier observing the market at
`entry_timestamp + N` faces *every* trade that has happened by then,
including any the original trader placed. Excluding them would answer a
different, counterfactual-market question this measurement does not need.

---

## 2. Cohort, placebo, and the gap

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. The text below is PRESERVED AS WRITTEN for the record but is
SUPERSEDED on two points: (i) the PRIMARY population is no longer the
cohort — it is the broad PIT-legal classifiable pool; the frozen Track 2
cohort and placebo lists are still used, but for SECONDARY curves
reported for shape comparison only. (ii) The viability bar is no longer
the cohort-minus-placebo GAP — see the §6 pointer. Use the amendment's
population and bar, not the ones below, when this is run.**

**What is computed at every `N`, for both populations, is the same
pipeline already established and reused, not rebuilt**: `measure_oos`'s
own position-level query (`scripts/trader_skill_metric_v2f.py`), applied
to the trader address lists — but with the entry price *substituted* per
§1 before the pair table is built. This yields, at each `N`: a cohort
point estimate + CI, and a placebo point estimate + CI, via the identical
`weighted_pair_table` / two-way clustered bootstrap machinery Track 2 used
(`seed=42`, `reps=1500`, `cap5` weighting) — the only change from Track 2's
own pipeline is which price feeds the pair table at each `N`.

**Cohort and placebo populations are the exact, frozen trader lists Track 2
already persisted** — `cohort_trader_list` (169 traders) and
`control_trader_list` (169 traders) in
`data/characterizations/track2_ci_power_20260905T104945Z.json` — **not** a
fresh re-run of `build_presplit_cohort`/`match_control`. Track 2 itself
found the presplit-qualifying cohort drifts in size over time (148 → 169
across three weeks, its own §C finding) — re-deriving the cohort fresh for
*this* measurement would introduce a second, independent source of
population drift on top of the one already being measured, confounding
"did the decay curve behave as expected" with "has the underlying
population moved since Track 2 ran." Reusing the frozen lists removes that
confound.

**The viability bar is the gap, not the cohort level — fixed here,
explicitly, because this is the question most likely to be got wrong**:
what determines whether copying inherits anything is whether
`cohort(N) − placebo(N)` survives delay, not whether `cohort(N)` alone
stays positive. A cohort whose edge decays in lockstep with its placebo's
own edge (both driven down by the same generic price-drift-toward-
resolution effect, unrelated to skill) would show "cohort decay" that says
nothing about capturable skill. Every result in this measurement is
reported and interpreted as the gap, cohort and placebo curves shown only
as the gap's two components, never as a standalone cohort verdict.

---

## 3. The N ladder, fixed now

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. The twelve-point ladder below is PRESERVED; the amendment
EXTENDS it with three sub-floor points (1min, 2min, 10min) — fifteen
points total — because the decisive region is at and below the
15-minute floor, not in the day-plus tail. Use the fifteen-point ladder
when this is run.**

**N ∈ {5min, 15min, 30min, 1h, 2h, 4h, 8h, 16h, 1d, 2d, 4d, 8d}** — twelve
points, roughly log₂-spaced (each step ≈ double the last, in minutes: 5,
15, 30, 60, 120, 240, 480, 960, 1440, 2880, 5760, 11520).

**Justification for log spacing, not linear**: price-discovery decay
processes are typically fastest-moving soon after an information event and
flatten thereafter — a linear grid spanning minutes to over a week would
either badly under-resolve the fast part (if step size is set by the long
end) or require an impractically large number of points (if set by the
short end). Doubling gives even resolution, in relative terms, across
every order of magnitude the ladder spans.

**Justification for the specific span — below, at, and well beyond the
architectural floor**: the project's own monitoring cadence polls every 15
minutes [V, `CLAUDE.md`] — a real, fixed floor on how fast any copy system
built on this architecture could ever act. The ladder places one point
*below* that floor (5min — a lower bound on what could ever be achieved,
useful only to characterize the curve's shape near zero, not as a
realistic operating point), one point *at* it (15min — the realistic
floor itself), and points running out to 8 days — matching the order of
magnitude of the entry-to-resolution lag distribution the feasibility read
already measured for this same cohort (tape_end-anchored median 8.92
days), so the ladder's upper end reaches into the range where the curve
should plausibly have fully flattened (converged to whatever floor value
it converges to) rather than stopping arbitrarily short of it.

`N=0` (no substitution — the trader's own actual entry price) is handled
separately, as the reproduction gate (§4), not as a ladder point — it is
not a "delay" and does not belong on a decay curve.

---

## 4. The N=0 reproduction gate

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. This gate is REPLACED in full. The original gate below — agree
with a frozen Track 2 figure within tolerance — tests substrate
stability, not harness correctness, and the substrate has moved
substantially (3,032 → 3,795 positions, and again after the 2026-09-09
geo drain). The replacement is an INTERNAL consistency gate: at N=0 the
decay harness must reproduce a direct `measure_oos`-style edge
computation on the SAME positions in the SAME run, to |Δ| ≤ 1e-9. Do not
apply the gate below.**

**Reference baseline: Track 2's own reproduction, not the original 08-15
result of record.** Track 2's diagnostic
(`data/characterizations/track2_ci_power_20260905T104945Z.json`, first-repo
`7aaf8d9`) already established, and its own pre-registration already
validated as acceptable, a reconstruction of this exact frozen cohort at
`n=3,795` positions / `141` surviving traders, cohort point_gap
`0.02078654`, CI `[-0.01216, +0.05582]` (placebo: `n=2,693`/`118`,
point_gap `0.02795233`, CI `[-0.00946, +0.06595]`). Using this as the N=0
reference — rather than re-litigating drift against the original
3,032/120 figure a second time — avoids re-deriving a tolerance Track 2
already fixed and defended.

**The gate, reusing Track 2's own §6 rule verbatim, applied against this
new reference point**: N=0 PASSES if (a) the point estimate stays within
Track 2's own CI bounds `[-0.01216, +0.05582]`, (b) the sign is unchanged
(positive), (c) `n_positions`/`n_traders` are not *shrinking* relative to
3,795/141, and (d) any discrepancy in `n_positions`/`n_traders` exceeding
10% is attributed to a named, checked mechanism — reusing the identical
attribution query Track 2 used (new entries since Track 2's own
`generated_at`, `2026-09-05T10:49:46`, vs. pre-existing positions
transitioning pending→resolved). **STOP condition**: point estimate
outside those CI bounds, sign flip, a *shrinking* population, or an
unattributed >10% discrepancy — reported as a harness-integrity failure,
not a result, exactly as Track 2's own falsification rule specifies.

The small remaining time gap between Track 2's run and this measurement's
eventual run should produce far less drift than Track 2's own three-week
comparison (148→169 traders, +25%/+17.5% at the position/trader level) —
so this gate is expected to be comfortably tight, not merely "not worse
than Track 2's own tolerance."

---

## 5. Missing and thin data

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. §5a/§5b's rules are PRESERVED and reaffirmed (carry forward to
the next available trade; exclude per-rung when the market's `tape_end`
precedes `entry+N`). The amendment adds a hard, fixed thin-rung flag
threshold and a per-rung surviving-n reporting requirement for every
population. Nothing below is deleted.**

**5a. No trade at or after `entry_timestamp + N`, but the market's tape
continues beyond that point.** Use the **next available trade whenever it
occurs** — do not drop, do not merely flag. Dropping would systematically
remove exactly the positions the feasibility read already flagged as
thin-benchmarked (20.4% of positions have zero other-trader activity
within ±1h; this measurement's "no trade at N" case is a superset of that
concern extended over time), which the same read found correlates,
however modestly, with the cohort's own highest-volume traders — dropping
here would compound that exact bias, not merely tolerate it.

Because "next available" can land well past the nominal `N`, **the
realised-delay distribution (actual elapsed time from entry to the
substituted trade, per position per nominal N) is reported alongside the
curve, not folded into it** — a curve point built from realised delays
much larger than its nominal `N` must be visibly flagged as such, not
presented as if every position was sampled at exactly `N`.

**5b. The market's own tape ends (via `tape_end`, the O-36-validated
anchor — not `resolution_date`) before `entry_timestamp + N`.** No
legitimate copier's entry price exists at that horizon — the market had
already stopped trading. These positions are **excluded** from that
specific `N`'s curve point (not assigned a synthetic resolution-adjacent
price), and the **exclusion count and fraction, per N, is reported
explicitly** — expected to rise with `N`, and to rise sharply once `N`
approaches the cohort's own entry-to-resolution lag distribution (median
8.92 days under the tape_end anchor, per the feasibility read), which is
exactly why the ladder's own top end (8 days) sits near that median: the
curve is expected to be built from a shrinking, and shrinking-in-a-
characterizable-way, subsample at its longest horizons, and that shrinkage
must be visible, not implicit.

**5c. Preventing thin data from silently biasing the curve.** Two
disclosures are required at every `N`, not just at the extremes: (i) the
included-position count and the exclusion count from §5b, so sample size
at each point is always visible next to the estimate it produced; (ii)
whether the population *actually included* at large `N` differs
systematically from the full cohort on the one dimension already shown to
matter — trader volume (feasibility read §1c: the highest-volume tercile
has the thinnest nearby-trade density of all three terciles, at every
window tested). **This is recorded as an open question, not answered
here**: if the subsample surviving to large `N` turns out to
systematically exclude the highest-volume traders, the long end of the
curve would describe a *different*, lower-volume-skewed slice of the
cohort than the short end does — a real threat to reading the curve as one
continuous object, and one this pre-registration cannot resolve without
the computation it is barred from doing.

---

## 6. The viability bar — grounded, not invented

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. The bar is MOVED off the cohort-minus-placebo gap and onto the
broad pool's curve shape and level against fixed, numeric per-category
transaction-cost floors (geopolitics 0.0005–0.010; elections
0.0056–0.020; blended 0.02, at the top of elections' range). The
`cost_floor()` mechanism below is PRESERVED as a cross-check but the
handover's fixed figures are the pre-registered bar, and the check is on
the broad pool's `edge(N)`, not on a gap. Use the amendment's bar.**

**Where on the curve it must be checked**: at and beyond the 15-minute
architectural floor (§3) — not at `N=0` (trivially true by construction)
and not only at the ladder's longest point (which would miss whether
anything survives at a realistic operating latency at all).

**What size of gap counts as economically meaningful**: a statistically
distinguishable-from-zero gap is necessary but not sufficient — it must
also clear a real transaction-cost floor to represent a *tradeable* edge,
independent of statistical significance. This project already has a
project-derived cost-floor construction for exactly this purpose:
`trader_skill_metric_v2f.py`'s `cost_floor()` function — spread cost
(`SPREAD_LO, SPREAD_HI = 0.001, 0.02`, "per B4's captured range" per that
script's own header) plus a category-dependent fee
(`FEE_RATE_ELECTIONS = 0.04`, Geopolitics fee-free), evaluated at the
cohort's own empirical entry-price distribution, separately per category
since a blended figure would misrepresent both. **The viability bar,
stated as a relationship, not a number**: the cohort-minus-placebo gap's
**lower confidence bound** at `N=15min` (and at every `N` beyond it up the
ladder) must exceed this same cost-floor construction, reused exactly as
`cost_floor()` already computes it — not a new number invented for this
measurement, and not fixed to an exact figure here, since that requires
running the function against this measurement's own data, which this
pre-registration does not do.

**Per-N confidence intervals are required, not a point curve.** Every
curve point (cohort, placebo, and the gap) is reported with the bootstrap
CI the same two-way clustered machinery already produces — a point
estimate alone cannot distinguish "the gap collapsed" from "the gap is
merely too noisily estimated to tell," and those two outcomes mean
different things (§7).

---

## 7. Outcomes, enumerated in advance

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. The four outcomes below are re-framed around the broad pool's
`edge(N)` versus the per-category cost floor (not the gap), and each is
given a name: SURVIVES-ABOVE-FLOOR, SURVIVES-BELOW-FLOOR,
COLLAPSES-BEFORE-CADENCE, TOO-THIN-AT-DECISIVE-N. The standing rule that
re-running with different parameters after a disappointing curve is not
an acceptable resolution is PRESERVED and restated. Use the amendment's
enumeration.**

1. **Gap survives well beyond the 15-minute floor.** Phase 2 has a
   subject. The curve's own shape — where it starts to bend, where it
   flattens — becomes the latency budget for any Phase 2 design, not a
   number invented separately from this measurement.
2. **Gap collapses within the floor** (indistinguishable from zero, or
   from the cost floor of §6, by `N=15min`). Phase 2 has no subject on
   this cohort. Per the design's §7, the canonical metric's value in this
   world is **diagnostic** — it explains *why* `+0.0316` is not capturable
   — not a replacement headline measurement.
3. **Gap never existed at N=0** (the reproduction gate, §4, fails). **STOP.**
   This is a harness-integrity failure, not a thesis result — report
   exactly what diverged and why, per §4's own criteria, and do not
   proceed to interpret any `N>0` point until this is resolved.
4. **Curve too noisy to distinguish** (confidence intervals at the
   relevant `N` values are too wide, overlapping zero and overlapping each
   other, to call either outcome 1 or 2). **What would make it
   conclusive, stated now**: materially tighter per-N confidence intervals
   — which, given the bootstrap machinery is fixed and reused unchanged,
   would require either a larger surviving sample at the relevant `N`
   (not obtainable by construction — it is what the tape provides) or
   accepting a coarser verdict (e.g., collapsing to fewer, wider `N` bins)
   as a **separately pre-registered** follow-up. **Re-running with a
   different N ladder is explicitly not an acceptable resolution** —
   mirroring Track 2's own §5 outcome-5 rule verbatim: an inconclusive
   result under this pre-registration's fixed parameters is reported as
   inconclusive.

---

## 8. Two limitations recorded, not resolved

**AMENDED 2026-09-10 — see "Amendment 2026-09-10" at the end of this
document. §8a (self-inflicted decay; best case for a size-one copier) and
§8b (tape price ≠ achievable fill; necessary-not-sufficient asymmetry)
are PRESERVED and reaffirmed — stated, NOT corrected for. The amendment
adds an explicit "what this measurement cannot establish" list (item I).
Nothing below is deleted.**

**8a. Decay is partly self-inflicted, and this is a best case, not a
size-independent one.** Some of the price movement between a trader's
entry and `entry_timestamp + N` was plausibly caused by that trader's own
entry (their trade itself moves the price, however slightly). This is
realistic for a copier trading at *comparable* size, but it means the
measured curve is specifically a **best case for a single, size-one
copier** — a copy system trading at larger size than the original trader
would face additional price impact this measurement cannot capture at all.
**No result from this measurement should be read as size-independent.**

**8b. The substituted tape price is not what a real copy system would
achieve.** No slippage beyond the recorded trade price, no fill
uncertainty, no guarantee the same size could be filled at all at that
moment. Per the design's §9: **passing this measurement does not prove
Phase 2 works — failing it is decisive against Phase 2.** This asymmetry
is recorded here so it is not lost when the eventual result is read: a
surviving gap is necessary-but-not-sufficient evidence for viability; a
collapsed gap is sufficient evidence against it.

---

## 9. Reproducibility

- **Committed script**: `scripts/copy_trade_decay_diagnostic.py`
  (first-repo, `scripts/` — matching `track2_ci_power_diagnostic.py`'s
  naming and location; not created by this pre-registration, named here
  so the eventual result document can point to it). Reuses
  `measure_oos`, `weighted_pair_table`, and the two-way clustered
  bootstrap unmodified — only the entry-price substitution (§1) and the
  N-loop are new logic.
- **Seed**: `42`, matching the whole `v2d`/`v2f`/Track 2 lineage, for
  comparability across every CI this project has produced from this
  bootstrap.
- **Reps**: `1500` (`GATE_REPS_LOCAL`), unchanged.
- **Population**: the exact frozen `cohort_trader_list` /
  `control_trader_list` from
  `data/characterizations/track2_ci_power_20260905T104945Z.json` (§2) —
  read from that artifact, not re-derived.
- **`T_SPLIT = "2026-04-01 00:00:00"`**, unchanged, hardcoded module
  constant, not passed as an argument — no way to accidentally vary it.
- **Durable artifact**: `data/characterizations/copy_trade_decay_<UTC-timestamp>.json`
  (first-repo convention), recording: every `N` in the ladder plus the
  N=0 gate result; cohort and placebo point estimates + CIs at each `N`;
  the gap and its own CI at each `N` (derived from the same resampled
  bootstrap distributions, paired where the underlying trader/position
  sets overlap — not a naive independent-CI subtraction, mirroring the
  delta-CI construction already specified in the discovery-gap-closure
  prereg's §E); the realised-delay distribution per `N` (§5a); the
  inclusion/exclusion counts per `N` (§5b/§5c); the git commit of this
  script and of `trader_skill_metric_v2f.py`/`v2d.py` at run time.
- **Parameters recorded, not re-derived silently on a later run**: all of
  the above, plus the exact SQL predicates used for the structural filter
  (category, gap-clean, `entry_avg_price`, `trade_result`) and for the
  "next trade at or after" lookup, so a future reader can tell whether a
  divergence from this run is a data change or a method change.

---

## Open questions (explicitly deferred — not answered by this document)

1. **§5c's volume-composition question**: whether the subsample surviving
   to large `N` systematically excludes high-volume cohort traders, which
   would mean the curve's short and long ends describe different
   populations. Only answerable by running the measurement; flagged here
   so the eventual result is read with this in mind, not treated as a
   single continuous object by default.
2. **Whether the exact cost-floor figure (§6)**, once actually computed
   via `cost_floor()` against this measurement's own data, differs
   meaningfully between Geopolitics and Elections positions in a way that
   makes a single gap-vs-cost-floor comparison across the whole cohort
   misleading — this pre-registration reuses the existing per-category
   split in principle but does not resolve whether the decay curve itself
   should also be reported split by category, rather than pooled.
3. **Component 1, 2, and 3's own thresholds** (the canonical metric's
   directional-skill, absolute-earliness, and relative-earliness
   validation bars) are explicitly out of scope for this document, per
   the task's own constraint — they get their own, separate
   pre-registration.

---

## Amendment 2026-09-10 — re-pin from the cohort-minus-placebo gap to the copy-viability curve on the broad PIT-legal pool

This amendment is appended as a dated section at the end of the document,
per the convention used in `2026-09-06-directional-skill-persistence-prereg.md`
and `MASTER_HANDOVER_2026-08-15.md`'s postscripts. Pointers were added at
§§1–8; **no original text was deleted or rewritten.** It commits **alone**,
with no decay result in the tree.

**This amendment is BLIND.** No decay curve — at any `N`, on any
population (broad, cohort, or placebo) — exists at the time of writing.
Nothing below was informed by, references, or waited on any `N>0`
figure. Every fixed number here is drawn from an already-committed
source, cited inline.

Tags: **[V]** verified against a cited file/query/doc this session,
**[I]** a fixed judgment call, marked.

---

### Why this amendment is needed

The pre-registration pinned its viability bar (its §2, §6) to the
**cohort-minus-placebo GAP** — "what determines whether copying inherits
anything is whether `cohort(N) − placebo(N)` survives delay". That bar
was set when the live thesis was *"traders selected by presplit edge
outperform a matched placebo."* Since it was written:

- **The N=0 gap is not demonstrated.** `2026-09-05-n0-gap-check.md`
  (`7aa3fe5`) computed the paired N=0 gap at **−0.0072**, paired 95% CI
  **[−0.0570, +0.0435]** — straddling zero, point estimate now negative,
  reversing the result of record's `+0.0189`. The gap "has not been
  proven absent; it has stopped being demonstrated present." **[V]**
- **The presplit-edge selector is falsified as a selection criterion.**
  `2026-09-05-directional-skill-result.md`, Outcome 2 "in its strongest
  form": the placebo shows *more* directional-skill-like signal than the
  cohort on every measure — "nothing in this result rescues the thesis as
  originally framed." **[V]**
- **The directional selector shows no edge advantage over a matched
  placebo** (2026-09-06 exploratory custody figures; the persistence
  test's aggregate). **[V]**

With no demonstrated gap, a gap-pinned bar makes this measurement
**permanently unrunnable** — which is why it has never run, despite
`2026-09-05-canonical-skill-metric-design.md` (`86a7b4e`) §2 naming it
**THE DECISIVE QUESTION** and sequencing it first.

The question the project now needs answered **does not require a selector
at all**: **DOES ANY MEASURABLE EDGE SURVIVE BEING COPIED?** That is a
property of how fast prices move after an informed trade — answerable on
any population, selector or no selector.

---

### A. Population — primary becomes the broad PIT-legal classifiable pool

**Primary population (new): the broad PIT-legal classifiable pool.**
Every trader with **≥ `M_CHOSEN` (10)** pre-split resolved
Geopolitics/Elections positions in the canonical pre-split market set —
`backtest_window_sql(VERY_EARLY, "2026-04-01 00:00:00")`: `resolved = 1`,
category ∈ {Geopolitics, Elections}, gap-clean, `tape_end < T_SPLIT`,
`entry_avg_price IS NOT NULL`, `trade_result IN ('won','lost')` — exactly
as `scripts/directional_skill_pit_legal_pool.py` derives it (**5,732
traders as of 2026-09-06**, `directional_skill_pit_legal_pool_20260906T160303Z.json`,
pre-drain). **[V]**

- **Re-derived at run time** from the current (post-2026-09-09-drain) DB
  by importing that script's pool logic unchanged — not frozen from the
  09-06 artifact, which pre-dates the drain. The run-time count and its
  delta from 5,732 are recorded in the artifact.
- Decay is measured on **this pool's OOS positions** — post-split
  (`entry_timestamp > T_SPLIT`), geo/elec, gap-clean, resolved won/lost —
  via `measure_oos`'s own position query with `trader_address IN (pool)`
  substituted for the cohort list. No other change to that query.

**Justification.** (i) The question — "does any measurable edge survive
being copied?" — is a property of post-entry price movement and needs no
selector. (ii) The broad pool is selected **only on having enough
pre-split history to be classifiable**, never on the outcome variable, so
it is free of the canonical design's §9 selection circularity (which is a
select-on-the-thing-you-measure problem). (iii) It is a large, already
named, reproducible population.

**Cohort and placebo curves are still computed and reported — as
SECONDARY.** On the exact frozen Track 2 lists
(`track2_ci_power_20260905T104945Z.json`: `cohort_trader_list` 169,
`control_trader_list` 169), unchanged from §2. Their value is **on SHAPE,
not LEVEL**: decay is relative — `edge at N` vs `edge at N=0` on the
*same* positions — so the cohort's presplit-edge selection inflates the
*level* of its curve but has far less purchase on its *shape* (the
original document's own opening argument, §-preamble). The cohort curve's
**level is contaminated** — by that selection, and by the N=0 gap having
stopped being demonstrated (−0.0072, CI straddling zero). It is reported
**for shape comparison only**, never as a standalone cohort-vs-placebo
verdict.

The **N=0 internal consistency gate (item D) applies to all three
populations** independently.

---

### B. The viability bar — off the gap, onto the curve vs. fixed cost floors

The bar moves off `cohort(N) − placebo(N)` and onto **the broad pool's
`edge(N)` curve, its shape and its level, against transaction-cost
floors fixed numerically here** from `MASTER_HANDOVER_2026-08-15.md` §5
**[V]**:

| category | fee | cost floor (per-side, at the cohort's own empirical entry prices) |
|---|---|---|
| **Geopolitics** | fee-free (spread only) | **0.0005 – 0.010** |
| **Elections** | 4% `feeRate`; fee 0.0097 at the cohort median price 0.59 | **0.0056 – 0.020** |
| blended effect-size bar | — | **0.02** — comfortable for geopolitics (up to 2× headroom), **at the top of elections' range** (the handover's own words: "defensible, not generous") |

**At which N the edge must clear the floor for copying to be viable:**
at **N = 15 minutes** (the project's architectural monitoring cadence,
`CLAUDE.md` **[V]**) **and at every N beyond it up the ladder.** Not
below 15 minutes — those rungs are sub-architectural and exist only to
characterise the curve's near-zero shape.

**What "clear" means:** the broad pool's `edge(N)` — **both the point
estimate and the lower bound of its bootstrap CI** — remains **above the
relevant per-category cost-floor lower bound** (`0.0005` geopolitics,
`0.0056` elections). Remaining above the cost-floor *upper bound*
(`0.010` / `0.020`) in addition is reported as the stronger statement.

**Per-category curves are reported** (geopolitics, elections, each
against its own floor), not only the blended curve — the blended `0.02`
bar sits at the top of elections' range and would misrepresent both
categories if used alone. `cost_floor()` (`trader_skill_metric_v2f.py`,
unchanged) is **also** run against each population's own OOS entry-price
distribution and reported as a cross-check, but **the fixed handover
figures above are the pre-registered bar**, not whatever `cost_floor()`
returns on this run's data.

---

### C. The N ladder — fixed, fifteen points

**N ∈ {1min, 2min, 5min, 10min, 15min, 30min, 1h, 2h, 4h, 8h, 16h, 1d,
2d, 4d, 8d}** — in minutes: **1, 2, 5, 10, 15, 30, 60, 120, 240, 480,
960, 1440, 2880, 5760, 11520.**

This **extends §3's twelve-point ladder** (5min … 8d, log₂-spaced) with
**three sub-floor points: 1min, 2min, 10min.**

**Spacing, justified:**

- **Below the floor (1, 2, 5, 10 min):** denser than log₂ because the
  interesting region is minutes, not days — price-discovery decay is
  fastest immediately after an information event, and the copy-viability
  question is decided at or just above the 15-minute floor, not in the
  tail. Four points below 15 min resolve the initial slope; without them
  the curve's steepest segment is a single 5min→15min chord.
- **At the floor (15 min):** the realistic architectural operating point
  — the rung the item-B bar is checked against first.
- **Beyond (30 min … 8 d):** §3's log₂ spacing, unchanged — even
  relative resolution across every order of magnitude. **8 days** is
  retained as the top: it matches the order of magnitude of this
  cohort's tape_end-anchored entry-to-resolution lag (median 8.92 days,
  feasibility read), so the ladder reaches into the range where the
  curve should have flattened to whatever floor value it converges to.

`N=0` is not a ladder point — it is the internal consistency gate (item
D).

---

### D. The N=0 gate — internal consistency, not agreement with a frozen figure

§4's original gate (reproduce Track 2's frozen `0.02078654` / CI
`[-0.01216, +0.05582]` within tolerance) is **replaced in full.** With
the population having moved substantially — 3,032 → 3,795 positions, and
again after the 2026-09-09 geo drain (`eee49ee`) — agreement with a
frozen figure tests **substrate stability, not harness correctness.**
That is the wrong thing to gate on.

**Replacement — an INTERNAL consistency gate.** In the **same run**, at
**N=0** (no price substitution — the position's own `entry_avg_price`
used directly, no lookup), the decay harness's edge computation must
reproduce a **direct `measure_oos`-style computation on the identical
position set**, for **each of the three populations** (broad, cohort,
placebo):

- `point_gap`, `ci_lo`, `ci_hi`: **|Δ| ≤ 1e-9** (absolute).
- `n_positions`, `n_pairs`, `n_traders`: **exactly equal.**

**Tolerance rationale.** At N=0 with no substitution, the decay harness
*is* `measure_oos`: same position query, same `cap5` `weighted_pair_table`,
same `weighted_two_way_gap_bootstrap` (`seed=42`, `reps=1500`). The only
admissible difference is floating-point non-associativity from
independent summation order — bounded well under `1e-9` at these
magnitudes. Anything larger means the harness's position assembly,
pairing, weighting, or bootstrap has diverged from the canonical path, so
**nothing it produces at any `N>0` can be trusted.**

**If the gate fails for any population: STOP.** Report the diverging
quantity and which population, as a harness-integrity failure — not a
result. Do not interpret, or even compute onward to, any `N>0` point.
(This is outcome **N=0-GATE-FAILS** in item H.)

---

### E. Price lookup — source and its limits, made explicit

**AMENDED 2026-09-10b — see "Amendment 2026-09-10b" at the end of this
document. This item fixed the price *source* (trade tape) but not the
substituted trade's *outcome*; the run then substituted opposite-outcome
prices unconverted. Amendment 2026-09-10b adds the outcome rule
(CONVERT `q → 1 − q` for opposite-outcome trades) + an
outcome-matched-only robustness curve. The source, "next trade", single
trade, and own-trader-inclusion rules below are otherwise unchanged.**

§1's rules are **reaffirmed**, not changed:

- **The NEXT trade in that market at or after `entry_timestamp + N`** —
  not the nearest. A copier cannot transact on a trade they have not yet
  observed; only "next at or after" respects the direction time runs for
  a copier.
- **A single trade's price**, not a window average.
- **Own-trader trades ARE included** in the lookup universe. A copier
  observing the market at `entry_timestamp + N` faces *every* trade
  that has printed by then, including any the original trader placed.
  Excluding them would answer a different, counterfactual-market
  question. (This is a deliberate departure from the feasibility read's
  fair-price benchmark, which excluded own-trades for skill-attribution
  reasons that do not apply to this purely mechanical "what would a
  copier have paid" question.)

**Price source — fixed: the executed trade tape, `trades.price`.** The
substitution price is the `price` column of that next trade row in the
`trades` table.

**`price_at()` / CLOB (`monitoring/price_history.py`) is NOT used** as
the substitution price, for three reasons: (i) it returns a CLOB
last/mid quote, not an executable counterparty trade — a copier sending
a market order transacts against the tape, not the quote; (ii) it
requires one live HTTP call per `(position, N)` pair — infeasible and
non-reproducible at this scale (fifteen rungs × the broad pool's OOS
positions); (iii) it is itself characterised as **primary-with-fallback,
age- and liquidity-dependent, 73.1% stratified cross-source agreement**
— stacking that uncertainty on top of the decay signal.

**The trade tape's own known limits**, carried not smoothed: thinness
(the feasibility read: **20.4%** of positions have zero other-trader
activity within ±1h) and **realised-delay drift** when the next trade is
far past nominal `N`. Both are surfaced via item F's rules and §5a's
per-rung realised-delay distribution — never averaged away.

---

### F. Thin and missing data — decided in advance

§5a/§5b are **reaffirmed** and made fully explicit:

- **Case 1 — no trade at/after `entry_timestamp + N`, but the market's
  tape continues past that point (§5a):** the position is **carried
  forward to the next available trade whenever it occurs.** NOT dropped,
  NOT excluded from the ladder, NOT valued at any pre-`N` price. Its
  realised delay (actual elapsed entry → substituted trade) is recorded;
  the per-rung realised-delay distribution is reported.
- **Case 2 — the market's own `tape_end` (the O-36-validated anchor, not
  `resolution_date`) precedes `entry_timestamp + N` (§5b):** no legitimate
  copier entry price exists at that horizon. The position is **excluded
  from that rung only** — not from the whole ladder. The per-rung
  exclusion count and fraction are reported (expected to rise with `N`,
  sharply once `N` approaches the ~8.92-day median lag).

**Hard reporting requirement.** At **every rung, for every population**,
the artifact records surviving **n_pairs, n_positions, n_traders**. A
rung whose surviving pair count is below **max(30, 5% of that
population's N=0 pair count)** **[I]** is reported but explicitly flagged
`THIN — not interpretable on par with denser rungs`; its point estimate
and CI are still shown, never silently omitted. If price-lookup coverage
at a rung is so thin the rung cannot be computed at all, that rung is
**named and reported as uncomputable — never silently dropped** (a stop
condition).

Per §5c, whether the surviving subsample's **trader-volume composition**
at large `N` drifts from the N=0 composition is reported as an open
question, **not corrected for**.

---

### G. The self-inflicted-decay caveat — stated, not corrected

Reaffirming §8a: when a copier enters at `+N`, **part of the price move
they pay for was caused by the original trader's own entry.** That is
realistic — it is what would actually happen — but it means:

- The measured curve is a **BEST CASE for a single, size-one copier.**
- It **worsens at larger copy sizes** (additional price impact this
  measurement cannot capture at all).
- **The curve is size-dependent. This measurement fixes copy size at
  one and does NOT correct for self-inflicted decay.** No result from it
  should be read as size-independent.

---

### H. Outcomes — enumerated and named in advance

Re-framed around the **broad pool's `edge(N)` versus the per-category
cost floor** (item B), not the gap:

1. **SURVIVES-ABOVE-FLOOR.** The broad pool's `edge(N)` — point estimate
   and lower CI bound — stays **above the relevant category cost-floor
   lower bound** at `N = 15min` and every `N` beyond. Copy-trading has a
   subject at size one. The curve's own shape — where it bends, where it
   flattens — becomes the latency budget for any Phase 2 design.
2. **SURVIVES-BELOW-FLOOR.** `edge(N)` stays distinguishable from zero
   past `15min` but does **not** clear the cost floor. A **real but not
   tradeable** edge at size one. Phase 2 has no viable subject on this
   measurement; the canonical metric design's role becomes **diagnostic**
   (explaining why `+0.0316` is not capturable), not a headline.
3. **COLLAPSES-BEFORE-CADENCE.** `edge(N)` is indistinguishable from zero
   — or from the cost floor — **by `N = 15min`.** **Copy-trading is
   structurally non-viable on this 15-minute architecture.** Stated
   plainly, as the task requires: **this moots the canonical metric
   design's remaining execution-dimension components (2 and 3) as
   capturability questions, and bears directly on Phase 2 as the primary
   experiment** — there is nothing left to inherit by the time a real
   copy could physically occur.
4. **TOO-THIN-AT-DECISIVE-N.** Surviving `n` and/or CI width at `N = 15min`
   and its immediate neighbours are too poor to separate outcomes 1–3.
   Reported as **inconclusive under these fixed parameters.**

Plus **N=0-GATE-FAILS** (item D): harness-integrity failure, **STOP**,
not a thesis result.

**Standing rule, restated (verbatim intent from §7 outcome 4 and Track 2
§5):** re-running with a different `N` ladder, a different population, a
different price rule, or any other parameter **after seeing a
disappointing curve is not an acceptable resolution.** An inconclusive
or collapsed result under these fixed parameters is reported as such.

---

### I. What this measurement cannot establish — explicitly

- It measures **price movement after an informed entry.** It does **not**
  establish that any selector — presplit-edge, directional, or otherwise
  — identifies skilled traders. The presplit-edge selector is already
  falsified as a selection criterion (2026-09-05 Outcome 2); the
  directional selector shows no edge advantage over a matched placebo
  (2026-09-06 exploratory). This measurement is deliberately
  selector-free and **cannot revive either.**
- It does **not** speak to the canonical design's **components 2
  (absolute earliness) and 3 (relative earliness)** as skill measures —
  only to whether the price has already moved by the time a copier could
  act.
- A **surviving curve is necessary but NOT sufficient** for viability:
  no slippage beyond the recorded trade price, no fill-size guarantee,
  no fill uncertainty, size fixed at one (item G). Per §8b — a collapsed
  curve is sufficient *against* Phase 2; a surviving one is not
  sufficient *for* it.
- It says **nothing** about whether a slower-decaying, prospectively
  selectable subpopulation exists — that is an observation-log
  watch-point, not a test this pre-registration runs.

---

### Reproducibility (supplements §9, does not replace it)

- **Script:** `scripts/copy_trade_decay_diagnostic.py` (first-repo,
  created by Part 2 of this task, not by this amendment). Reuses
  `measure_oos` / `weighted_pair_table` / `weighted_two_way_gap_bootstrap`
  unmodified; imports the broad-pool logic from
  `scripts/directional_skill_pit_legal_pool.py` unmodified; only the
  entry-price substitution (item E), the fifteen-point N-loop (item C),
  and the three-population wrapper are new logic.
- **`--selfcheck`** consistent with `trader_skill_metric_v2*` — at
  minimum re-derives `edge = won − substituted_price` for a sample and
  asserts exact match, and asserts the N=0 internal consistency gate
  (item D) as part of the check.
- **Seed 42, reps 1500, `cap5`, `T_SPLIT = 2026-04-01 00:00:00`** —
  hardcoded, unchanged from the whole `v2d`/`v2f`/Track 2 lineage.
- **Durable artifact:**
  `data/characterizations/copy_trade_decay_<UTC-timestamp>.json` —
  records: the fifteen-point N ladder; the N=0 internal-consistency gate
  result per population; for **each of the three populations** at every
  `N` — `point_gap` + CI, `n_pairs`/`n_positions`/`n_traders`, the
  realised-delay distribution (§5a), the §5b exclusion count/fraction,
  the THIN flag; **per-category (geopolitics, elections) curves** with
  the fixed cost floors from item B; the broad-pool run-time size and
  its delta from 5,732; the git commit of the script and of
  `trader_skill_metric_v2f.py` / `v2d.py` / `directional_skill_pit_legal_pool.py`;
  every SQL predicate used.
- **Stop conditions** (in addition to §-level ones): N=0 gate fails for
  any population; any amended parameter cannot be applied as written;
  `metric_v2f_oos_result` sha256 changes from
  `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`;
  price-lookup coverage at any rung too thin to compute it (report which
  rungs — do not silently drop).

---

## Amendment 2026-09-10b — the outcome rule for the price substitution

Appended as a dated section at the end, per this document's convention
(matching `2026-09-06-directional-skill-persistence-prereg.md`'s
"Amendment 2026-09-06" / "Amendment 2026-09-06b" pattern). Pointers added
at §1 and at Amendment 2026-09-10 item E; **no earlier text deleted or
rewritten.** Commits **alone**, before any corrected curve exists.

**This amendment is BLIND.** No corrected decay curve — at any `N`, on
any population, under either construction below — exists at the time of
writing. Nothing here was informed by a corrected figure.

**The pre-existing result, recorded as what it is, NOT as a target.**
The 2026-09-10 run (`data/characterizations/copy_trade_decay_20260910T191052Z.json`,
first-repo `c9619a4`, doc `9732bc9`) published, on the broad PIT-legal
pool: N=0 `+0.01208` (CI `[−0.00168, +0.02645]`); N=15min `+0.03434`
(CI `[+0.01369, +0.05622]`); the point estimate rising from N=0 to a
`+0.033–0.037` plateau across N=1min–60min and CI-positive through
N=1440min. **That curve stands as computed.** The 2026-09-10
verification (`3c22b0c`) then established the rise is a price-semantics
artifact: the substitution took the next trade of *any outcome*, and
**37.58%** of N=15min substitutions were on the opposite outcome, at
price `≈ 1 − p` unconverted; outcome-matched-only gave N=15min `+0.01592`
(CI `[−0.00130, +0.03317]`), within noise of N=0. This amendment is not
about moving toward or away from either number — it fixes the rule that
should have been specified in the first place.

Tags: **[V]** verified against a cited file/query, **[I]** a fixed
judgment call.

---

### Why the rule was underspecified

§1 and Amendment 2026-09-10 item E both say "the **next trade in that
market** at or after `entry_timestamp + N`, **from any trader**". Both
address *trader*; **neither addresses outcome**. In a binary market a
trade carries the price of *its own* outcome (`P(Yes) + P(No) ≈ 1.0`,
established empirically — see item A), so "the next trade's price" is
ambiguous between `P(held outcome)` and `P(¬held outcome)`. The
implementation followed the written rule exactly and took whichever
came first. Same shape as the `geo_elo` docstring embedding the same
sign error as its code: the spec inferred a price field's meaning from
context instead of pinning it.

---

### A. The outcome rule — CONVERSION is primary

For each substituted trade, let `q` be its recorded `trades.price` and
`O` the position's held outcome:

- **Same-outcome substitution** (the substituted trade's `outcome == O`):
  use `q` directly as the implied price of `O`.
- **Opposite-outcome substitution** (`outcome != O`): use **`1 − q`** as
  the implied price of `O`.

`edge = won − implied_price_of_O` as before. This is the **primary
construction** — the reported decay curve.

**Justification, from the verification's own Part 1 evidence [V]**
(`3c22b0c` §Part 1): paired opposite-outcome trades on the same resolved
non-gap geo/elec market, matched within 10 s, have `price_Yes +
price_No` with **median exactly 1.00000**, IQR **[0.999, 1.001]**,
**97.9%** within [0.98, 1.02] (n = 45,984 pairs; 739,459 rows in the
population). Complementarity is empirical and tight, so an
opposite-outcome trade **is informative** about the held outcome's
price — `1 − q` recovers it to within the pair-sum's deviation from 1.0.
Discarding those trades instead throws away real information and, worse,
a non-random 37.6% of the sample (item B).

**The cost, stated honestly.** Complementarity is empirical, not exact,
and loosens with the match window: **92.0%** within [0.98, 1.02] at
300 s (vs 97.9% at 10 s). Conversion therefore imports a price error on
each converted substitution equal to that instantaneous pair-sum's
deviation `ε` from 1.0 (`implied = 1 − q = p_true − ε`).

**Expected magnitude, from the Part 1 distribution, without a curve
[V/I]:** the 10 s window is the best available proxy for "instantaneous"
(no genuine drift between the two legs). There, `|ε|` is **≈ ±0.001 for
the middle half** of converted substitutions and **≤ ±0.02 for ~98%** of
them. `ε` is approximately symmetric about 0 (median deviation 0.00000),
so the **expected aggregate bias** from applying conversion to ~37% of
substitutions is a fraction of the mean `|ε|` (order **1–2 ×10⁻³**),
far below any rung's bootstrap CI half-width (~0.02) and **an order of
magnitude smaller than the +0.018 inflation that *un*converted
opposite-outcome substitution produced at N=15min**. Conversion trades
a large, one-signed artifact for a small, roughly mean-zero measurement
error.

---

### B. The robustness check — outcome-matched-only, secondary, every rung

**Outcome-matched-only** (discard every opposite-outcome substitution;
keep only same-outcome, used directly) is computed and reported **at
every rung, for every population and per category, alongside the primary
— never instead of it.**

**Why secondary, not primary.** Discarding 37.6% of substitutions is not
a random thinning: *which* outcome trades next after a given entry
correlates with market conditions at that entry (momentum, which side
has flow, time-to-resolution), so the retained same-outcome subsample is
a biased slice. Conversion keeps every substitution and imports only the
small, licensed measurement error of item A. The matched-only curve is
the check that conversion is not itself introducing a level shift; it is
not the answer.

**Both curves are required in the deliverable.** If they disagree
materially (item C), **that disagreement is the finding** and neither is
to be reported as "the" result.

---

### C. Material disagreement — the criterion, fixed now

**Criterion: at the decisive rung (N=15min, broad PIT-legal pool), the
primary (conversion) and secondary (outcome-matched-only) 95% bootstrap
CIs do not overlap.**

- If the two CIs **overlap**: the constructions agree within the
  harness's own uncertainty. The **primary (conversion) curve is the
  result**; the matched-only curve is reported as confirmation.
- If the two CIs **do not overlap**: the choice of construction
  dominates the measurement at the rung the viability judgment turns on.
  No single number is defensible. Named outcome
  **PRIMARY-AND-ROBUSTNESS-DISAGREE** (item G) — reported as such, with
  both curves, and **not resolved by picking one.**

**Why CI-overlap rather than a point-estimate threshold.** The bootstrap
CI is the harness's own statement of what it can and cannot resolve;
non-overlap is a construction-agnostic statement that the two rules
produce answers the harness itself considers distinguishable. A raw
point-estimate threshold (e.g. "> 0.01") would need separate
justification per cost floor and would fire or not fire on noise at
these sample sizes. Non-overlapping CIs is the stricter, cleaner test
and maps directly onto "can the viability verdict even be stated."

The criterion is evaluated **only at N=15min on the broad pool** — the
decisive rung (item D). Overlap/agreement at other rungs is reported but
does not change the named outcome.

---

### D. The decisive rung and the cost floors — restated, unchanged

- **Decisive rung: N = 15 minutes**, the project's architectural
  monitoring cadence (Amendment 2026-09-10 item B). The viability
  judgment turns on the broad-pool `edge(N=15min)` — point estimate and
  lower CI bound — under the primary construction.
- **Per-category cost floors — UNCHANGED** (MASTER_HANDOVER_2026-08-15
  §5): geopolitics **0.0005–0.010** (fee-free), elections
  **0.0056–0.020** (4% fee), blended bar **0.02**. Per-category curves
  reported against their own floors, for both constructions.

---

### E. The sub-15-minute region — a permanent limitation of this data

The 2026-09-10 run found the **median realised delay at nominal
N=1min is 12–22 minutes** across populations (broad pool 14.3 min;
geopolitics 12.1; elections 22.2) — the trade tape simply has **no
trades within ~12–22 minutes of a typical entry**. **[V]**

This is recorded as a **permanent property of the trade-tape data, not a
parameter**: the sub-cadence region (how the edge behaves in the first
minutes after an informed entry) is **unmeasurable on the trade tape
regardless of the substitution rule**, and **adding finer rungs cannot
fix it** — a rung nominally at 1min still resolves to a ~15min realised
sample. The 1/2/5/10min rungs are retained (they bound the realised-delay
disclosure) but their nominal labels are not to be read as delays.

---

### F. The N=0 gate — unchanged, retained, re-run

**Unchanged.** N=0 uses `positions.entry_avg_price` (no tape lookup, no
substitution), which the verification confirmed is outcome-correct —
**0.00% outcome mismatch on 4,000 sampled positions**, `entry_avg_price`
= the share-weighted mean of the position's own entry-trade prices
(median diff 0.00000) **[V]**. The gate passed bit-identically for all
three populations in the 2026-09-10 run (`Δ = 0.0` on
`point_gap`/`ci_lo`/`ci_hi`/`n`). It is re-run as-is: the harness's N=0
computation must reproduce a direct `measure_oos` on the same positions
to **|Δ| ≤ 1e-9** and exact `n`, per population. Failure ⇒ STOP.

---

### G. Outcomes — the 2026-09-10 set, plus one

Retained verbatim from Amendment 2026-09-10 item H, evaluated on the
**primary (conversion)** curve: **SURVIVES-ABOVE-FLOOR**,
**SURVIVES-BELOW-FLOOR**, **COLLAPSES-BEFORE-CADENCE**,
**TOO-THIN-AT-DECISIVE-N**, **N=0-GATE-FAILS**. The COLLAPSES outcome's
consequence is unchanged: it moots the canonical design's execution
components 2/3 as capturability questions and bears on Phase 2 as the
primary experiment.

**Added: PRIMARY-AND-ROBUSTNESS-DISAGREE** — per item C, the primary and
outcome-matched-only 95% CIs at N=15min (broad pool) do not overlap.
Reported with both curves in full; not resolved by picking one.

**Standing rule, restated:** re-running with a *different substitution
rule* after seeing a disappointing curve is **not** an acceptable
resolution. **This amendment is the last word on the substitution
rule.** An inconclusive, collapsed, or disagreeing result under the
2026-09-10b rule is reported as such.

---

### Reproducibility (supplements §9 and Amendment 2026-09-10's own)

- **Script:** `scripts/copy_trade_decay_diagnostic.py`, modified by Part
  2 of this task to (i) load `p.outcome` and the substituted trade's
  `outcome`; (ii) apply the item-A conversion as the primary curve;
  (iii) compute the item-B outcome-matched-only curve at every rung;
  (iv) record the opposite-outcome share per rung per population. The
  N=0 gate, N ladder, cost floors, seeds, `cap5`, `T_SPLIT`, and the
  cohort/placebo definitions are **not** changed. `--selfcheck`
  additionally asserts, on a sample, that `1 − q` is applied iff the
  substituted trade's outcome differs from the position's.
- **Durable artifact:** a **new**
  `data/characterizations/copy_trade_decay_<UTC-timestamp>.json` (the
  2026-09-10 artifact is not touched). Records, for **both
  constructions**, every rung's `point_gap` + CI,
  `n_pairs`/`n_positions`/`n_traders`, THIN flag, realised-delay
  distribution, §5b exclusion counts, **and the opposite-outcome share**;
  per-category curves; the N=0 gate deltas; the item-C criterion
  evaluation; `metric_v2f_oos_result` sha256 before/after.
- **Stop conditions** (additional): the conversion cannot be applied
  because `outcome` is unavailable for some substituted trade — report
  the coverage, do not silently drop; `metric_v2f_oos_result` sha256
  changes from
  `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`;
  N=0 gate fails for any population.
