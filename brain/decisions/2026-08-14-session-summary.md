# Session Summary — 2026-08-14

## THEME

Volume question pursued to a conclusion. The dilution guard — which carried 96% of the prior no-go verdict — was verified and found correct, but resolving it made the number worse, not better. The real bottleneck turned out to be elsewhere: tier-decay synchronisation.

## HEALTH (brief)

Clean uptime since 08-11, three services up, order-book capture stayed caught up (last snapshot 08-14 08:20, 210 captured). Maintenance 32/33 — the one failure is the known `test_backtest_window_population.py` drift (population-convergence guard correctly firing on moving backfill data). 402 `gap_recovery_20260811` rows intact. Yesterday's retraction artifacts confirmed pushed (`65ca8a4`).

NOTE: box clock reads 2026-08-14; the session was opened labelled 08-13. Working date is 08-14.

## O-49: STILL NOT CONVERGED — AND DIVERGING

| check | Aug 07 | Aug 09 | Aug 14 |
|---|---|---|---|
| tape_end in outage window | 0 | 4,979 | 20,211 |
| opened during outage | 0 | 4,767 | 19,641 |
| open-through | 4 | 197 | 1,173 |

Backfill still actively writing (trades max rowid +553,800 since 08-09; 102,933 trades now carry in-window timestamps). The gap between readings is WIDENING not narrowing — tape_end roughly quadrupled since 08-09 vs +62% the prior day. Gap-flagging deferred again. Do not execute until two consecutive readings are materially unchanged.

## TASK 1 — VOLUME, MEASURED WITH THE CORRECTED METHOD

All prior estimates (9/8, 40/38, 0-4) were void — produced before the 08-12 fixes (tape_end change-points, outcome-side price normalisation) and with the truncated 06-01 lookback.

Full population (4,712 markets, 37.3-week span), full §4.2 spec:
- First pass: 3 signals / 3 clusters -> 0.080 clusters/week -> ~14.3 years to >=60 bets / >=40 clusters.
- After the guard verification (below) tightened the method: 2 raw / 1 cluster -> ~43 years.
- NEAR_LEGENDARY fallback: 7-8 clusters -> ~5-6 years. Still far outside the design's 4-9 month estimate.

Funnel (first pass): 4,712 population -> 711 candidate markets -> 10 raw formations -> 3 survive band -> 3 survive liquidity (never binding) -> 3 clusters.

## TASK 2 — LATENCY: CLOSED

All formations checked at +33min and +65min stayed on the same side of both band boundaries. Typical drift 0-5 price points — immaterial against the 58-day median formation-to-resolution horizon. Independently replicates the 08-12 conclusion on a different dataset. The copy-bot latency concern from the 08-10 research is RETIRED.

## TASK 3 — LOW-SIDE ASYMMETRY: RESOLVED AS MEASUREMENT ARTIFACT

All outside-band formations sit below 0.10, none above 0.90 — replicated on a new dataset. They are near-certain-No prop questions ("Will Trump say 'Iran' during events with Xi Jinping?", "Iran closes its airspace by May 21?") that trivially pass voter/majority mechanics because "No" is obvious to nearly everyone. This is STR-002's NEAR_RESOLVED contamination class; the band filter rejecting them is the filter WORKING, not evidence of herding. Closed.

## THE DILUTION-GUARD VERIFICATION (the session's main work)

Question: the |net|/gross >= 0.7 guard removed ~96% of raw formations (268 -> 10) and therefore carried the entire no-go verdict. Was it correct, or were we filtering out our own signal?

RESOLVED — the guard is correct, and the ambiguity was smaller than feared:
- Only 5 unique trader-market pairs in the ENTIRE population are affected by the strict-vs-loose reading at all (the fork sampled all of them, not a subset — that's all there were).
- Across all 63 diff events for those 5: open exposure was exactly ZERO every time.
- Classification: 0/5 genuinely two-sided/LP, 0/5 partial-exit-still-directional, 5/5 FULLY-EXITED ROUND-TRIPPERS — closed out completely, no live position at T. No bot-type flags; clean directional books elsewhere.
- Verdict: the strict (open-position) reading is correct. §4.2's text ("not exited by T") is literal, not ambiguous. The loose reading wasn't rescuing wrongly-filtered directional traders — it was counting CLOSED-OUT, RESOLVED BETS as live conviction.

Three readings, full population: open (literal) 2 raw / 1 cluster / ~43yrs; total (all-time) 3 / 2 / ~21.5yrs; direction-only (guard off) 2 / 1 / ~43yrs.

Bug caught and fixed en route: a formation wrongly dropped at the 0.10 boundary due to a float artifact (1-0.9 = 0.09999999999999998) — epsilon-guarded now.

## THE REAL BOTTLENECK — TIER-DECAY SYNCHRONISATION (record this prominently)

Not the guard. **100 markets have >=2 cohort traders simultaneously positioned AND directionally agreeing — but only 2 ever have both members LEGENDARY-qualified at the same moment.** A 50x drop from tier-decay timing alone.

99 near-miss markets are lost to the synchronised-churn effect, not to any filter choice. Related: 53 of 80 candidate traders had `geo_elo_active` reset in the same 5-day window (2026-05-17/18, real Iran-crisis/election activity, verified not a data artifact).

INTERPRETATION: it is not that elite traders fail to agree. It is that our DEFINITION OF WHO COUNTS AS ELITE AT TIME T is volatile enough that agreement rarely registers simultaneously. That is a property of the `geo_elo_active` decay mechanism, not of the traders. This is now the most promising thread if the thesis is pursued further.

Also flagged: the screen only re-evaluates consensus when a cohort member TRADES in that market — it won't catch two already-positioned voters crossing the LEGENDARY threshold via decay-reset from activity elsewhere. Unquantified; would push the true rate higher for reasons unrelated to the guard.

## ARTIFACTS PERSISTED (fixing the reproducibility failure)

- first-repo `5aa9948` — `scripts/verify_dilution_guard.py` (parameterised, re-runnable, `--selfcheck`/`--persist`), pushed.
- trading-swarm `dd99e87` — `brain/decisions/2026-08-14-dilution-guard-verification.md`, pushed.
- DB tables `dilution_guard_signals` + `dilution_guard_signals_guard_diffs`, every formation tagged by funnel-stage outcome.

## HONEST GAP (not swept under)

This pass's raw counts (2-3) sit below the prior un-persisted pass's 10, and far below the 08-12 retest's 28 (different scope). Best-identified cause: this pass enforces the §4.1 knowability rule and exact-timestamp PIT decay in ways that can't be confirmed present in the earlier code — because that code no longer exists to diff against. Reconstruction primitives passed 25/25 self-check against the validated modules; the guard arithmetic itself is new and not independently cross-checked.

## STATE FOR NEXT SESSION

Oscar's framing unchanged: everything in order before paper trading commences, no rush.

1. THE DECISION: as measured, Phase 2 is not viable on the current spec — 43 years (or ~5-6 with NEAR_LEGENDARY) vs a 4-9 month design estimate. Before accepting that, the tier-decay-synchronisation finding is the one thread that could change it: if the LEGENDARY-at-T definition is the binding constraint rather than trader behaviour, a different (still pre-registered, still principled) cohort-membership rule might recover the 99 near-miss markets. That is a THESIS-SPEC question, not a filter-tuning one, and must be pre-registered if pursued.
2. Ingestion detection (no alert when our DB is missing trades the API has — found the 08-11 gap by luck). Mandatory before any months-long passive run.
3. Carried: O-49 gap-flagging (blocked on convergence), canonical allowlist fix for `gap_recovery_20260811`, elections calibration re-run, O-38, O-18.

## STANDING LESSON

See the reproducibility-of-decision-carrying-numbers standing rule added to `2026-06-29-overhang-ledger.md` this session (below the O-49 entry) — three unreproducible numbers in a row (B3's 9/8, the 08-12 retest's 28, this session's first 10) is now a pattern, not a coincidence. First correctly applied here.
