# Skill Metric Rebuild — geo_elo to the first trustworthy thesis test

**Date:** 2026-08-15
**Scope:** the full metric-rebuild arc, eight pre-registered passes (Layer 0 through v2f), first-repo commits `f1d2555` through `eaeabbc`.
**Method:** each pass pre-registered before computing, persisted as a committed, re-runnable script plus a durable DB artifact table, per the standing reproducibility rule.

---

## WHY THE REBUILD HAPPENED

A confirmed sign error in `_compute_geo_elo`: `expected = 1.0 − price`, but `price` already equals P(the traded outcome wins) for **both** sides — empirically confirmed by pairing Yes/No trades within 60 seconds of each other on the same market and finding they sum to 1.000 ± 0.001. For No-side trades this scored traders against the probability of the outcome they bet *against*.

Found by luck, not process: a calibration curve looked wrong in an unrelated experiment three layers removed. The module docstring embedded the *same* error as the code, which is why every prior code-vs-spec validation passed — the spec was wrong from the birth commit, not the implementation.

The derivation audit that followed found this was not one bug but several:

- **Improper scoring rule.** A zero-skill trader buying favoured No positions earned expected `2·price − 1 > 0` per trade — free rating for zero edge, and not exotic, since ~71% of these markets resolve No and volume clusters on favourites. LEGENDARY may have substantially selected for favourite-betting No traders rather than skill.
- **SELL contamination.** 35.7% of the qualifying population (88,927 rows) folded in under `trade_evaluator.py`'s inverted win-condition. There is no side filter anywhere in `_fetch_qualifying_trades` — an earlier claim that one existed is corrected here.
- **Double-counting.** 52.3% of (trader, market) pairs have more than one qualifying trade, accounting for 86.3% of all qualifying trades (median 2, max 642). The K-schedule was counting decision *fragments*, not decisions.
- **No size or time-to-resolution weighting**; K-schedule (32/24/16), starting rating 1500, ratchet (150/step), MIN_TRADES=5, tier ladder (1000/1400/1800/2175), decay half-life (180 days) — none calibrated against data. The ladder's 1000/1400 don't appear anywhere before the June 22 consolidation commit that claimed to lift values "exactly from source scripts" — verified inaccurate.
- **Structural verdict:** Elo's costs were kept (path-dependence, order-sensitivity, an opaque sequential accumulator), Elo's benefit was discarded (no logistic link, no probability interpretation of the resulting number). A mean-edge metric would have made the sign bug visually obvious on the first calibration plot — that's precisely how it was eventually found, just three layers later than it should have been.

## THE REBUILD (eight passes, each pre-registered before computing)

- **Layer 0** — geo_elo appeared to order traders by forward edge (rank correlation 0.685, placebo p≈0.04). **Retracted at Layer 0b**: the gradient was a normalisation artifact in the metric's *own* spec (double-inverting No-side prices). Corrected, rank correlation collapsed 0.685 → 0.152, population mean edge 0.198 → 0.010, bottom decile 0.179 → 0.004 with a CI straddling zero — exactly H0's prediction for a well-calibrated market, which is itself the confirmation the correction worked.
- **v2** — metric defined: mean market-relative edge per independent decision, empirical-Bayes-shrunk, bootstrap CI, entries-only primary with exits scored separately. **Calibration gate failed; stopped rather than re-specifying.** Diagnosed as market concentration (the Kamala Harris 2024 election market: 65.9%/34% of the two failing buckets), not a normalisation bug. Cause recorded honestly: v2's own pre-registration had correctly removed the unjustified MIN_TRADES inheritance, which had been incidentally diluting Kamala-only traders out of every prior population. The filter was unjustified *and* it was doing real, unacknowledged work.
- **v2b** — two-way trader×market cluster bootstrap; gate passed. The shrinkage estimator was found degenerate (identical to 1e-19 across all traders) — debugged rather than reported, replaced with the standard unbalanced one-way ANOVA method-of-moments estimator; the collapse under market/event weighting was then verified genuine (MSB 0.0621 < sigma2_within 0.0735), not an artifact. Market/event weighting found statistically unaffordable — median trader touches only ~4 distinct markets. Recommendation overridden on evidence against the pre-registration's stated intent.
- **v2c** — capped-multiplicity weighting family. Clean knee at cap5: sigma2_between is exactly zero for market/log/sqrt/cap3 and turns on at cap5 (0.00072 — about a fifth of position-weighting's power at less than half its concentration exposure, 4.94% vs 9.95%). The entries/exits placebo *reversed* the naive reading: random exits gave −0.776 vs real traders' −0.478, meaning real exit decisions partially counteract the mechanical anti-correlation — evidence of genuine exit-timing judgement, not opposed skills. Caught and fixed its own verdict-logic sign error before persisting.
- **v2d** — the properly cap5-weighted two-way bootstrap gate passed (20/20 side×bucket combinations), landing within thousandths of v2c's approximation — retrospectively validating that shortcut, checked rather than assumed. Threshold candidates derived; flagged significance-95 qualifying 14,188 traders (52% of the population) as prima facie wrong. Turnover inverted expectations: percentile cuts were the most stable (73–76%), significance the least (63%/46%).
- **v2e** — small-sample correction. **The coverage simulation caught a real conceptual error before anything was reported**: the first build used a t-interval (df=n−1), but the estimator uses the population sigma2_within (borrowed strength), so a t critical value double-penalises — the thin-trader penalty is already fully carried by the 1/n_i terms in the variance formula. Simulated coverage: old bootstrap 30.6% false-positive rate vs a nominal 5% (exactly explaining the spurious 52%); the first t-interval attempt came in at 0.0% (broken the other way — over-conservative); the corrected z-interval landed at 5.56% (essentially exact). Significance-95 + M≥10: 14,188 → 360 traders (1.3% of the population), a cohort now indistinguishable in kind from percentile cohorts (median 48 positions / 23 markets).
- **Decision taken**: significance-95 + M≥10 as the *definitional* rule; effect-size ≥0.02 as a *required secondary filter* for "tradeable" vs merely "provably nonzero." Percentile explicitly rejected as primary — a percentile cut always has a top 1% even under zero true skill variance, so it cannot distinguish skill from luck by construction, and its better turnover partly rewards volume, which this entire arc exists to stop over-weighting.

## THE FIRST TRUSTWORTHY THESIS TEST (v2f)

**Cost floors**, category-specific, at the cohort's own empirical entry prices (not an assumed p=0.5): Geopolitics is fee-free, floor 0.0005–0.010 (spread only); Elections carries a 4% feeRate, fee 0.0097 at the cohort's median price of 0.59, floor 0.0056–0.020. The blended 0.02 effect-size bar is comfortable for geopolitics (up to 2× headroom) but sits at the *top* of elections' range — defensible, not generous. A category-split bar is flagged as a real, second-order gap in the current definition, not fully resolved.

**Intersection cohort** (significant at 95%, M≥10, shrunk edge ≥0.02): 295 traders, full history. LEGENDARY overlap: 15/81 (18.5%).

**Out-of-sample test.** T_split = 2026-04-01, chosen on volume/power grounds alone, *before computing any outcome* — a 63/37 split by position count, and independently matching FABLE's own original train/validation boundary from months before this metric existed. PIT-correct cohort definition (only positions whose markets had already *resolved* by T_split, via `tape_end` — not merely entered, which would leak resolution information into the "as of" reconstruction): 148 traders qualify on information available at the split. 120 survive into the out-of-sample window (28 stopped trading in scope after the split).

**Result:** cohort mean edge +0.0316, CI [−0.0088, +0.0710], n=3,032 positions. Placebo (matched on position count, market breadth, and activity period from the same eligibility pool, *not* selected on edge): +0.0127, CI [−0.0210, +0.0461].

**Verdict: NULL — the cohort's CI does not exclude zero.** Reported exactly as the pre-registration required, whichever way it fell.

**But not flat-null.** The point estimate is +3.2 percentage points, directionally larger than the placebo's +1.3 points, which sits closer to zero. With 120 surviving traders and roughly 8 points of CI width, a genuine 2–4pt edge — economically meaningful against the cost floors above — cannot be distinguished from noise at this sample size. This is underpowered, in the direction the thesis predicts, not evidence against it. The placebo's own null confirms no structural artifact is contaminating the comparison — the result is interpretable, just not yet conclusive.

Objective 3 (does ≥2-member consensus add anything over individual positioning) was correctly **not run**, per the pre-registered conditional (Objective 2 positive and placebo null). The consensus question remains untested rather than answered on a foundation that isn't there yet.

## WHAT NOT TO DO NEXT (recorded explicitly)

Raising the effect-size bar, trying another weighting, or re-cutting the split are all ways of searching the same data for a specification that clears significance — exactly the garden-of-forking-paths failure this arc was built to avoid. The honest resolution to "suggestive but underpowered" is **more out-of-sample observations**, not more analyses of these ones.

---

**Artifacts, full chain:** first-repo `f1d2555`/`ff9ef7c` (Layer 0), `77017a0` (Layer 0b/0c), `f7695c0` (price-convention audit), `57ed326` (elo formula audit), `5e93131` (v2), `62603f9`/`de1ff84` (v2b), `ad6ed9c`/`eb19b95` (v2c), `57d38bb` (v2d), `511858c`/`e5efb27` (v2e), `eaeabbc` (v2f). DB tables: `layer0_*`, `layer0b_*`, `layer0c_*`, `price_convention_audit_*`, `elo_formula_audit_*`, `geo_elo_derivation_audit`, `metric_v2*_*` (pre-registrations, gate results, threshold candidates, OOS results — one full set per pass).
