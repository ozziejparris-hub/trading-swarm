# Session Summary — 2026-08-15

## THEME

Realignment day. Stepped back from a spec that had accreted until it fired twice in 4,712 markets, collapsed the problem to a layered question (does the base metric predict at all → where does signal live → is aggregation useful → is it tradeable), and discovered the base metric was broken. Rebuilt it properly across eight pre-registered passes, then asked the original thesis question honestly for the first time. Full detail in the companion record: `2026-08-15-skill-metric-rebuild.md`.

## HOW WE GOT BOGGED (record it — this is the reusable lesson)

The original question was simple: do skilled traders predict outcomes better than the market? What we ended up testing was a construct with roughly eight stacked conditions, every one individually defensible, collectively so specific it fired twice in 4,712 markets. We spent weeks debugging the instrument without asking whether it measured the thing we cared about. And underneath all of it sat an assumption nobody had tested: that geo_elo measures skill. Every filter layered on top was a refinement of "who is skilled" — refinement on noise, if the base metric doesn't predict at all.

**STANDING LESSON: test the premise before building the instrument.** Rung A (does the information exist in cohort positioning at all, hindsight, zero lag, zero cost) was the cheapest thing on the FABLE design's own diagnostic ladder and got sequenced last in practice, after months of building on top of an unvalidated foundation.

## WHAT WAS ACHIEVED

1. **geo_elo established as unfit for purpose** (see the rebuild record) — not one bug but several, none of which prior validation could catch, because the spec itself was wrong, not just the implementation.
2. **A trustworthy replacement built**: a proper scoring rule, correct price normalisation (calibration gate passed under properly-weighted two-way clustering), aggregation per independent decision rather than per raw trade, principled empirical-Bayes shrinkage, cap5 weighting bounding single-event concentration, a CI with verified nominal coverage (5.56% vs a nominal 5%), thresholds derived from the metric's own distribution rather than inherited from an uncalibrated ladder.
3. **The thesis tested out-of-sample on a trustworthy measure for the first time**: null but directionally positive and underpowered, with a clean, non-contaminating placebo.
4. **Three self-caught errors disclosed rather than smoothed over** — a degenerate shrinkage estimator, a placebo verdict sign error, a t-vs-z coverage miscalibration — each caught by a check built specifically to catch it, before being reported.

## STATE FOR NEXT SESSION

Oscar's framing unchanged: everything in order before paper trading commences, no rush.

**The reframe that matters:** Phase 2's purpose has changed. It is no longer "test a thesis we have no evidence for" — it is "accumulate the out-of-sample observations needed to resolve a directionally-positive but underpowered signal." That is exactly what forward paper trading does well, and it now has a validated measurement instrument to do it with, rather than a broken one.

Open, in rough order:
1. **Cutover decision**: does the new metric replace geo_elo in production? Not made — requires its own pre-registration and a before/after audit of cohort membership (LEGENDARY overlap is 15/81 — the tier as currently defined has little in common with what a defensible metric calls the top tier).
2. **Category-split cost floor** — elections' 0.02 effect-size bar sits at the top of its own cost range; geopolitics has roughly 2x headroom at the same bar. A blended bar is defensible but not tight.
3. **Ingestion detection** — still mandatory before any months-long passive run. No alert exists when our DB is missing trades the API has; the 2026-08-11 gap was found by luck, not process.
4. **The consensus question** (does ≥2-member agreement beat individual positioning) — untested, and now testable on a sound foundation, once Objective 2's signal has more out-of-sample power behind it.
5. **Carried**: O-49 gap-flagging (still diverging, not converged), the `comprehensive_elo`/`calibration_analysis.py` analogous sign-error bug (out of scope all session, still open — same structural pattern found in the geo_elo derivation audit, unquantified), elections calibration re-run, O-38, O-18.
