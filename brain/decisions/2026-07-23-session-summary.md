# 2026-07-23 Session Summary

## Theme

Opened intending B1b-prices then B5. Both happened — but B5's scoping surfaced that the backtest-window population itself was defined on the wrong column, contaminating it with 2023-2024 markets. The session's real output: the last PIT component shipped, and the population-selection class closed canonically before any labelling budget was spent on a bad population.

---

## What Shipped

### B1b-prices — BUILT + VALIDATED + SHIPPED (first-repo `5a8c680`, trading-swarm `ea57a48`)

- `monitoring/price_history.py`: extract-3 (`resolve_token_id`, `fetch_price_history_window`, `parse_ts`, unmodified from `scripts/b2_price_history_probe.py`) + new `price_at(token_id, T, lookback_hours)` — last-point-at-or-before-T, never interpolated. All 5 edge cases proven with real calls (normal / no-point / stale-point / no-token / T-after-resolution) plus the flat 15-day interval cap raising loudly rather than silently 400-ing. 10 non-tautological assertions in `tests/test_price_history_price_at.py` (T1/T2 confirmed to fail against inline naive implementations — nearest-point-regardless-of-side, silently-drops-stale — before being paired with the correct-behavior tests).
- **Coverage/staleness (the good news):** 290/302 priced (96.0%), 0 no-token, and 0/290 exceeding the 6h FABLE staleness cap (median 0.008h) — CLOB-side drop rate for B3 is effectively ZERO.
- **Cross-source check:** pre-registered ≥90% of trades within 0.02 of the curve (threshold derived from B4's own captured order-book spreads), measured 73.1% on the 16-market stratified sample (old 55.6% / recent 88.7%) — below the bar, reported as-is, threshold not moved. Root-caused directly, not assumed: CLOB's real curve cadence is ~40-90s (`fidelity=0` and `fidelity=1` return identical points — not a request-parameter fix), which structurally cannot resolve rapid intra-minute price sweeps on thin/volatile markets. No inversion/wrong-token signature in any sampled market. Source characterization downgraded from "strong primary" to **primary-with-fallback, age/liquidity-dependent**, per B2's own three-tier framework.
- **Recorded caveat for B3:** B3 prices at `T_act = T_detect + 30min`, far coarser than CLOB's ~1-minute cadence — this cross-check is stricter than B3's actual use requires, so 73.1% does not bound B3's entry-price accuracy directly; B3 should re-measure at its own granularity rather than inherit this number.
- **Two scoping corrections to the B2 probe record:** the probe's "30min median gap" was an artifact of its own fidelity ladder (it never tried finer than 30 since 30 always succeeded first try) — fidelity=1 (per-minute) is confirmed available for the 2025-11 backtest window. The probe's `chunk_days_for_fidelity()` points-budget model is wrong — CLOB's real interval cap is a flat ~15 calendar days, independent of fidelity — meaning the probe's `MAX_CHUNKS_PER_MARKET=8` under-covered 13/49 (27%) of its own sample's long-lived markets for a fixable reason, and B2's 73% "coverage to resolution" figure was pessimistic, not a real ceiling.

### Canonical backtest-window population (first-repo `8470e8b`, trading-swarm `98f0466` / O-45)

- `monitoring/column_definitions.py` Section 6: `backtest_window_sql(window_start, window_end)`, tape_end-anchored (`MAX(trades.timestamp)`, inner-joined so zero-trade markets drop structurally rather than by a filter someone has to remember), half-open interval so adjacent FABLE §4.5 train/validate/holdout splits can't double-count a boundary market. `scripts/b5_population.py` repointed to it (confirmed 4,690). 21/21 assertions in `tests/test_backtest_window_population.py` + 11 structural self-checks in `column_definitions.py`'s own self-test.
- Two of the test's own bugs were caught before being reported: an initial false-positive count conflated the 573 genuinely-stale-tape_end markets with the 565 zero-trade markets (different exclusion reasons, now kept distinct); an initial false-negative regression assertion used the wrong market_id for "US-Venezuela military engagement" (a similarly-titled but different market), which the before/after non-tautology proof caught immediately when it passed against the *old* logic instead of failing.

---

## The Finding (why the population work happened)

B5's 15-market calibration batch surfaced 7/15 markets that were 2023-2024 real-world events carrying `resolution_date=2026-04-01`. Investigation found:

- **Two distinct bulk-backfill contamination events**, exact timestamps: `2026-04-01 16:19:13` and `2026-06-04 21:36:39`.
- **Population: 5,774 (resolution_date) → 4,690 (tape_end).** 573 false positives (9.9%) including the entire 2024 US Presidential Election family (Harris market alone: 69,475 trades, 511-day gap between resolution_date and real tape_end). 54 false negatives wrongly excluded (52 early-stamped, 2 NULL resolution_date) — real Nov-2025+ geopolitics (US-Venezuela military engagement, Zelenskyy-Putin meeting markets, Andrej Babiš/next Czech PM, Argentina 2025 legislative seat-share). Net 18.8% population swing. 565 zero-trade markets dropped for a *separate*, legitimate reason (no tape_end to anchor on at all) — kept distinct from the 573 figure so future summaries don't conflate them.
- **The class:** this exact selector pattern was independently reinvented 3 times — B5 scoping, RQ1.1's Period-1/Period-2 split, and B1b-prices' own population figure — which is why it's now canonical in `column_definitions.py` rather than patched per-consumer.
- **Event-time vs. write-time:** this is the deliberate inverse of O-33 (gate STALENESS on write-time; gate POPULATION WINDOWING on event-time) — both correct for the question each answers. The `BACKTEST_WINDOW_RATIONALE` docstring exists specifically so the next reader doesn't collapse the two rules and "fix" this back to resolution_date.
- B1b-prices' Stage-2 cross-check sample was checked against tape_end and confirmed clean — all 8 "old"-stratum markets are genuinely Nov-Dec 2025. No re-measuring needed there.

---

## B5 Calibration (labelling not yet run)

Reviewed a 15-market ambiguous-zone batch (`neg_risk=False`, candidate-shaped titles) before committing the full ~150-market hand-labelling budget. Externally verified against real-world facts: Singapore 2023 presidential election (exactly 3 candidates, Tharman 70.41% — labelled SIBLING-SET, correct and complete); California's top-two jungle primary (two candidates genuinely advance, confirmed June 2 2026 — labelled STANDALONE, correct, governs ~34 individual candidate markets in that primary alone). Assessment: 13/15 labels correct, 2 over-cautious (the NY-3 Suozzi/Pilip pair marked UNSURE where the underlying resolution data — both members correctly resolving in a way that already demonstrates non-exclusivity — settles it), zero merge errors. Approved for the full labelling run — but deliberately **not run yet**, pending the corrected 4,690 population from the finding above.

---

## Ledgered This Session

- **O-45** — the population-selection contamination and its class (two bulk-backfill timestamps, 5,774→4,690, 573 false positives / 54 false negatives / 565 zero-trade kept distinct, independently reinvented 3 times, event-time/write-time inverse-of-O-33 rationale). Fixed for B5; open for RQ1.1.
- **RQ1.1 annotated, not fixed:** 1,083 of 15,239 Period-2-window markets have tape_end < 2025-11-01 — the same contamination, landing in an already-shipped research artifact (`rq1_1_elo_persistence.py`). The boundary is applied as string literals at 4 call sites (lines 142, 157-158, 301, 309) that never reference the script's own named `PERIOD_1_END`/`PERIOD_2_START`/`PERIOD_2_END` constants. Effect on RQ1.1's actual conclusion is unknown — not re-derived this session. Deliberate: re-running a published research artifact's numbers deserves its own before/after session, not a tail-end repoint bundled into population-fix work.

---

## State For Next Session

- **All three PIT components DONE:** B1a (geo_elo), B1b-positions, B1b-prices.
- **Next: B5 labelling** (~150 ambiguous-zone markets) against the corrected 4,690 population, then B5's clustering build — native `neg_risk`/`neg_risk_market_id` grouping covers ~30% of the population at near-vendor-grade trust, title-inference fallback for the rest, pre-registered recall ≥95% / precision ≥90% (recall prioritized per the stated asymmetry: under-clustering inflates n and is the dangerous direction), plus 3 no-label structural checks (mutual-exclusivity violation, resolution-date spread, outcome-price sum).
- **Then B3** (the backtest harness) — the last piece before the experiment itself runs.
- **Carried, unchanged:** elections-calibration current-state re-run (O-40's open item), RQ1.1 repoint+re-run (this session's new item, sequencing pending), O-38, O-18, the 3 persistent B4 thin-market failures (Padilla, China-Philippines, Macron — same set as last check).

---

## Methodology Thread

Pre-registration earned its keep twice this session. B1b-prices' cross-source check came in below its pre-stated 90% bar (73.1%) and was reported as-is rather than having the threshold moved after the fact — a component that ships with a surfaced limitation (primary-with-fallback, re-measure at B3's own granularity) is more useful downstream than one carrying an inflated confidence level. And the population check looked in both directions rather than only the one the calibration batch had flagged: the 573 false positives were the expected finding, but the 54 wrongly-*excluded* markets (US-Venezuela, Zelenskyy-Putin, Babiš, Argentina 2025) would have been invisible to a one-directional check — a filter never tells you what it dropped unless you go looking for it specifically.

This continues 07-22's thread (validate against something proven-clean, not merely hoped-clean) one level up: this time the thing that needed validating wasn't a reconstruction against a live table, it was the population-selection logic itself, and the same discipline — reconcile both directions exactly, don't accept a plausible-looking number, non-tautological regression proofs — caught two bugs in the test setup before either could have silently passed (the false-positive/zero-trade conflation, and a copy-paste market-id error that a lazier before/after check would have missed).
