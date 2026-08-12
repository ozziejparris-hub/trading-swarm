# Rung-A Finding Retracted — "Consensus Forms Late" Was a Lookback-Boundary Artifact

**Date:** 2026-08-12
**Author:** Claude Sonnet 5. Analysis conducted by a background subagent (two runs, same session), directed and synthesized by the primary session.
**Status:** RETRACTION + CORRECTED RESULT. No code changes, no DB writes — this whole investigation is read-only, both the flawed run and the retest.
**Cross-ref:** `2026-08-09-phase2-primary-and-paper-trading-preparation.md` (Phase 2 promotion, the ~9/25-cluster power shortfall this reopens), `2026-07-17-edge-proof-experiment-design-FABLE.md` §4.2/§4.8 (rung A of the diagnostic ladder, the signal spec), `2026-06-29-overhang-ledger.md` O-49 (the same error class, see "The Lesson" below).

---

## What was concluded (2026-08-12, morning) and retracted (same day, evening)

**Conclusion reported that morning:** across the full 353-market holdout (`bt_pop_2025-11-01_v1`, tape_end 2026-06-01→07-20), cohort consensus forms at/after price certainty — 80% of formations (16/20) outside the contested band [0.10,0.90], 10/20 at ≥0.95, zero clean in-band formations. Read as a rung-A failure: H1 (elite-cohort consensus predicts resolution better than market price) not supported at the root. Framed as stop-the-project-as-conceived.

**RETRACTED**, same day, on a hardening retest. The finding was an artifact of the reconstruction's own lookback boundary, not cohort behaviour.

---

## The decisive number

With roster/position lookback extended to each market's TRUE first-trade date (not capped at the holdout window start, 2026-06-01), floored only at the design doc's own PIT-reliability boundary (2025-11-01 — trader tracking began Aug 2025, too little resolved-trade runway before Nov):

**18 of 28 markets (64.3%) where cohort consensus ever forms had their true first-fire moment INSIDE the contested band [0.10, 0.90].** A majority, not near-zero — a near-total inversion of the morning's 80%-outside reading.

Corrected histogram (28 formations, all priced via CLOB `price_at()` at the exact formation timestamp):

| Price bucket | Count |
|---|---|
| [0, 0.05) | 6 |
| [0.05, 0.10) | 4 |
| [0.10, 0.25) | 7 |
| [0.25, 0.50) | 9 |
| [0.50, 0.75) | 2 |
| [0.75, 0.90) | 0 |
| [0.90, 0.95) | 0 |
| [0.95, 1.0] | **0** |

Zero formations above 0.90, against 10/20 at ≥0.95 in the retracted run.

---

## Root cause

Roster reconstruction was capped at 2026-06-01 (the holdout window start). For markets whose cohort positions were established months earlier, that boundary got stamped as the "first visible" fire day — by which point price had often already drifted to an extreme. The signature was visible in the retracted run and misread rather than caught: **17 of 20 signals firing on literally day 1 of the window is a property of a boundary, not of markets.** It should have been read as a methodological red flag immediately; instead it was reported as a finding.

**Worked examples** — the two markets cited that morning as the *strongest clean evidence* for "forms late" were themselves the clearest victims:

- `0xd86a816093fcd0`: retracted run — fires 06-08 at price 0.05 (outside band). Corrected — true fire 2026-06-01 at price **0.17** (in-band). The market had been trading for 13+ days before the recorded "fire" and the 06-01 boundary simply couldn't see it.
- `0x9352c559e9648a`: retracted run — 0.978, held up as the starkest "pinned near certainty" case. Corrected — true fire **2026-03-05** at price **0.39** (mid-band). Three months of the market's life, and the actual consensus formation, were invisible to the flawed reconstruction.

---

## Timing — materially changes the latency picture too

The 18 in-band formations: 6–179 days to resolution, **median 58 days**. Consensus typically forms roughly two months before resolution — the opposite of herding into obvious outcomes, and it defuses the copy-bot/detection-latency concern raised in the 08-10 external research: a 30–65min detection lag is immaterial against a 58-day median horizon between signal and payoff.

---

## Two real bugs caught and fixed during the retest (both would have silently corrupted results if uncaught)

1. **PIT bug:** change-points must use each trade's `tape_end` (the moment it becomes knowable to the ELO fold), not its raw timestamp. Caught by checking the broadened reconstruction against the known-correct morning roster *before* trusting anything computed downstream of it.
2. **Pricing bug:** the trade-tape price proxy didn't normalize for outcome side — a No-side trade at 0.84 was reported as price=0.84 instead of the correct implied-YES price 0.16. Because [0.10,0.90] is symmetric about 0.5, this specific bug could never have flipped an in/out-of-band classification on its own — but every reported magnitude in the morning run was wrong, and it's the kind of bug that would corrupt a less-symmetric filter silently. Fixed and re-verified against CLOB.

---

## Validation of the corrected result

- **Broader candidate screen:** 46-trader roster (morning run) → 58 traders (anyone whose undecayed geo_elo ever crossed 2175), surfacing 87 candidate markets vs. the morning run's 20.
- **CLOB re-pricing:** all 28 formations priced via `price_at()` (monitoring/price_history.py) at the true-fire timestamp — zero errors, zero staleness-cap breaches. CLOB and the corrected trade-tape proxy agree on in/out-of-band classification for every single formation.
- **Position math cross-validated:** `analysis/pit_positions.reconstruct_positions_at()` (the module already validated at scale elsewhere — 1.2M positions, zero unexplained divergence vs. the live table) run independently against the inline consensus-computation for all 28 formations' voters. Zero genuine disagreements. (One apparent 3-market mismatch during the check was a bug in the comparison script itself — comparing minority-side voters against the majority label — not a real reconstruction divergence.)

---

## Residual caveats (recorded, not chased)

1. The 58-trader screen is broad but finite — can't fully rule out a LEGENDARY path it doesn't cover. No positive evidence one exists.
2. One market, `0xfbe85201...` (first trade 2025-08-26), is unresolved — one of its two voters never crosses the screen. Reported unresolved, not guessed.
3. "True fire day" is day-granularity, not intra-day.
4. **Unchased asymmetry worth a later look:** the 10 outside-band formations cluster *entirely* at the low extreme (all <0.10, none >0.90). That is not what noise looks like. The herding-pattern diagnostic that would characterize this wasn't run — it was conditioned on the HOLDS branch of the verdict, and the verdict came back BREAKS.

---

## The lesson (the generalisable one)

This is the same error class as **O-49** (`2026-06-29-overhang-ledger.md`): treating the edge of our data as the edge of the world. O-49 was current-absence-of-trades mistaken for permanent-absence. This was no-consensus-visible-before-2026-06-01 mistaken for no-consensus-formed-before-2026-06-01. Same shape, opposite direction, five weeks apart.

**Standing rule, recorded here so it's checkable next time:** when a reconstruction produces a striking result, check first whether the result sits at a boundary *we* chose, before concluding it's a property of the world. "17 of 20 fire on day 1 of the window" should have triggered that check immediately — instead it shipped as a headline finding for most of a day.

---

## Status

**Thesis ALIVE.** The open question reverts to **signal volume** — the ~9–25-cluster count vs. the 60–120 required by §4.6's power analysis (`2026-08-09-phase2-primary-and-paper-trading-preparation.md`) — not signal existence.

**New asset produced by this investigation:** 28 corrected, properly-dated formation events with CLOB-verified in-band pricing and time-to-resolution, cross-validated position math. Available for the detection-latency re-run and any further work on the volume question.
