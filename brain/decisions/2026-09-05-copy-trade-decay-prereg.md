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
