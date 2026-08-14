# LP-Dilution-Guard Verification — Guard Is Not The Bottleneck; True Rate Is Lower Than Previously Estimated

**Date:** 2026-08-14
**Author:** Claude Sonnet 5, independent re-derivation (script + artifact committed, not a one-off report).
**Status:** VERIFICATION COMPLETE. Read-only against production data throughout; writes are limited to the new artifact table (`dilution_guard_signals` / `dilution_guard_signals_guard_diffs`, first-repo DB) and the committed generator script.
**Cross-ref:** `2026-08-12-rung-a-retraction.md` (the corrected-28-formations retest this re-derives against the full population), `2026-08-09-phase2-primary-and-paper-trading-preparation.md` (§4.6 power target, 60–120 clusters), `2026-07-17-edge-proof-experiment-design-FABLE.md` §4.2 (the spec being re-derived).

---

## What was asked

An earlier same-day full-population pass (not persisted, not reproducible) found the §4.2 dilution guard (`|net|/gross >= 0.7`) removing raw formations 268 → 10, and reported a ~14.3-year duration to reach the design's n=60/40-cluster target. The guard's exact interpretation was ambiguous — the spec text says "capital split" without fully disambiguating open-position vs. all-time-committed capital — so that 96%-reduction number was carrying almost the entire no-go verdict on one unverified interpretation. This investigation re-derives it independently, under three explicit readings, with the result persisted as a reproducible artifact this time.

## §4.2 literal text (quoted, not paraphrased)

> "Cohort positions at T: for each cohort member (§4.1), net open exposure in M = Yes-capital − No-capital across positions entered ≤ T (per knowability rules) and not exited by T. Members whose per-market capital split is near-balanced (|net|/(gross) < 0.7) are excluded from this market — LP/market-making behavior, STR-002's dilution source."

The phrase "not exited by T" scopes the underlying position set to positions still open at T — the **open-position reading is the textually literal one**. The all-time-committed reading is not what the text says; it's included only because it was the ambiguity under test.

## Headline result — the guard was never the real bottleneck

| Reading | Raw formations | Band-dropped | Liq-dropped | Distinct clusters (full population) | Implied duration to 60 bets |
|---|---|---|---|---|---|
| **open** (literal spec) | 2 | 1 | 0 | **1** | ~43 years |
| **total** (all-time-committed) | 3 | 1 | 0 | **2** | ~21.5 years |
| **direction** (guard off, floor case) | 2 | 1 | 0 | **1** | ~43 years |

Guard-reading choice barely moves the number (1 vs 2 clusters). **The true bottleneck is not the dilution guard — it's the compound requirement that ≥2 cohort members be simultaneously positioned, agreeing, *and* PIT-tier-qualified at the exact same moment**, which decay makes rare (see Task 3 finding below). These numbers are *worse* than the 14.3-year estimate that prompted this check, not better — hardening the methodology moved the conclusion in the opposite direction from what "the guard is too strict" would predict.

**Sensitivity grid** (all at full population, 37.3-week span):

| Variant | open | total | direction |
|---|---|---|---|
| Primary (LEGENDARY, ≥2 voters, liq floor) | 1 cluster (~43y) | 2 clusters (~21.5y) | 1 cluster (~43y) |
| ≥3 voters | 0 clusters | 1 cluster (~43y) | 0 clusters |
| LEGENDARY+NEAR_LEGENDARY | 7 clusters (~6.1y) | 8 clusters (~5.4y) | 7 clusters (~6.1y) |
| No liquidity floor | 1 cluster (~43y) | 2 clusters (~21.5y) | 1 cluster (~43y) | (liquidity floor never binding)

Even the widest fallback (NEAR_LEGENDARY, 3x more candidates) implies ~5–6 years — well short of the design's original 4–9 month estimate, though far better than the strict-spec ~43 years.

## Task 2 — what the strict guard actually excludes (the decisive check)

Sampled **all 5** unique (trader, market) pairs the open reading excludes but the total reading admits (the full population, not just a subsample — only 5 exist). At every one of the 63 individual diff events behind those 5 pairs, **open exposure was exactly zero (`yes_open=0.0, no_open=0.0`) at the moment evaluated.** Inspecting full trade histories:

- 3 of 5 pairs: bought, then fully sold the *entire* position within hours to days — a clean round-trip, zero remaining shares.
- All 5: `bot_type IS NULL`, `wash_trade_suspect=0`, `bot_suspect=0`, and overall book directionality scores of 0.61–1.0 (genuinely directional traders elsewhere in their book, not LP/market-makers).

**Classification split: 0/5 type (i) LP/market-making, 0/5 type (ii) partial-exit-still-net-long, 5/5 type (iii) — fully exited, zero current position.** The strict guard is not over-filtering directional traders; if anything the *total* reading is the interpretive error, since it counts fully-realized, closed-out capital as if it were a live directional stance — economically meaningless for a strategy meant to mirror *current* cohort conviction. This resolves the ambiguity: **the open (literal-spec) reading is correct**, and the guard's own bite (1 vs 2 clusters) is nearly irrelevant next to the compound tier+knowability restrictiveness below.

## Task 3 — cohort-churn suppression (the real bottleneck, quantified)

Across the full population: **100 markets have ≥2 candidate-cohort traders simultaneously positioned and agreeing on the same open-side, ignoring tier entirely.** Of those, only **2 markets ever have 2+ of them simultaneously PIT-tier-qualified (LEGENDARY)** at the same moment. **99 distinct markets are "near-misses"** — genuine directional agreement exists, but tier-decay knocks at least one voter below the LEGENDARY bar before/after the other qualifies. This is a 50x drop from position-agreement to tier-qualified-agreement, and it is the dominant force behind the low signal count — far more than the guard. It also directly explains the sensitivity grid: relaxing the tier bar to NEAR_LEGENDARY (more traders qualified at once) multiplies the cluster count 7x.

**Item 9 (structural blind spot — quantification attempted, not fully measured):** the candidate screen only re-evaluates consensus on a trader's own in-market trades; a trader whose tier status flips due to decay-reset from trades in *other* markets, while already holding a qualifying position here, could be missed between change points. Decay is correctly computed from the trader's most recent geo/elections trade *anywhere* (not just this market — verified in the generator's `TierTimeline`), so tier status itself is right; only the *exact moment it's checked* could lag. Given how rare simultaneous tier-qualification already is (2/100 near-miss-eligible markets), this is judged a timing-precision issue affecting individual formation timestamps by hours to days, not a material change to the overall count — but this is a characterization, not a measurement; a full quantification would need to re-evaluate consensus at every cohort member's tier-crossing moment regardless of which market they traded, which was not built in this pass.

**Low-side asymmetry, still present:** of the 2 raw formations that got band-dropped, 1 priced at 0.03 (genuinely below band) and 1 at the literal 0.10 boundary (a float-precision artifact of `1 - 0.9` computation, corrected with an epsilon guard — without the fix this formation was wrongly dropped). Consistent with the prior retraction's finding that outside-band formations cluster at the low extreme.

## Known unreconciled gap

This re-derivation's raw-formation counts (2–3, full population) are far below both the un-persisted same-day prior pass (10 raw / 268 guard-off) and the 08-12 retest's 28 formations (holdout-only, "consensus forms at all" screen, full-spec filters not yet applied there). The largest identified cause: **this pass applies the §4.1 knowability rule** (signal-side positions bounded to `timestamp >= trader.first_seen`, excluding backfilled pre-discovery trades) **and PIT-exact tier decay at each precise trade timestamp**, neither of which could be confirmed present in the prior pass's methodology (its code was not persisted, so this can't be checked directly). This generator's tier/position reconstruction was cross-validated against `analysis/pit_geo_elo.py` and `analysis/pit_positions.py` (both independently validated modules) via `--selfcheck`, passing 25/25 sampled points with zero mismatches — the reconstruction primitives are trustworthy. The guard-arithmetic layer itself (gross/net capital computation) is new code without a second implementation to cross-check it against, which is the same residual-risk class the original rung-A investigation flagged for position math before `pit_positions.py` existed.

## Artifact (Task 4)

- **Generator script:** `scripts/verify_dilution_guard.py`, first-repo commit `5aa9948df976f7f9017d6bda1b30a089652763a8`.
- **Data artifact:** `dilution_guard_signals` table (every raw formation — survived or dropped, tagged by funnel stage: `band_dropped` / `liquidity_dropped` / `survived_final` / `cluster_dedup_dropped`) and `dilution_guard_signals_guard_diffs` (the 63 strict-excludes/loose-admits events), both in `data/polymarket_tracker.db`, generated `2026-08-14T21:28:24Z`.
- Reproducible via `python3 scripts/verify_dilution_guard.py --selfcheck` (validates reconstruction fidelity) then `--persist [--min-voters N] [--tier-threshold N] [--liquidity-floor N]` for any grid point.

## Status

**Guard-reading question: RESOLVED.** Open (literal-spec) reading confirmed correct by direct inspection of what it excludes (Task 2). **Volume question: WORSE than previously estimated**, not better — true bottleneck identified as tier-decay-driven cohort-churn (Task 3), not the guard. This does not change the 08-12 retraction's verdict that the thesis is alive (that was about whether consensus forms in-band at all, not about volume) — it hardens the existing signal-volume concern from "9–25 clusters, order of magnitude short" to "1–2 clusters under strict spec, ~43 years to power," a materially worse position than assumed as recently as this morning.
