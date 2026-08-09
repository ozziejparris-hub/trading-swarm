# 2026-08-08 / 2026-08-09 Session Summary

## Theme

Two short sessions, combined here because 08-08 didn't get its own summary. 08-08 was meant to execute the outage gap-flagging deferred from 08-07; instead it found the gap is substantially self-healing and corrected a wrong structural claim made the night before. 08-09 re-checked whether the population had converged (it hadn't — deferred a second time, correctly, on evidence), and used the blocked time for B3 scoping, which produced the session's real finding: the backtest is underpowered by an order of magnitude, forcing a strategic reframe with Phase 2 promoted to the primary experiment.

---

## Part 1 — 2026-08-08 (short morning session)

**Context:** Oscar rebooted the box manually around 09:40 local. The 06:43–08:44 "outage" the system had detected was that reboot, not a fault. Consequence: the 06:00 cron maintenance never ran, and today's partial run stalled at step 2/27.

**Action:** relaunched maintenance manually, detached via `cron_wrappers/run_daily_maintenance.sh` (nohup + disown, so env and log paths match production rather than an ad hoc invocation). Worker PID 4327, confirmed reparented to PID 1 — genuinely detached, not tied to the session.

**The finding (O-49):** the outage gap is largely *not* a permanent hole. Polymarket's API serves historical trades, so the system has been retroactively backfilling since coming back online. Evidence: 9,654 trade rows carrying 2026-07-25 → 08-06 timestamps, spread across every day of the gap (39/day rising to ~1,900/day), rowids at the very top of the table (10,824,745–10,851,634, against a table max of 10,851,784) — inserted that morning, absent the night before. Recorded in `brain/decisions/2026-06-29-overhang-ledger.md` and committed to trading-swarm as `3ca23da` ("docs: O-49 — outage gap is substantially self-healing, correcting last night's structural claim").

**The correction (recorded bluntly, not softened):** 08-07's claim that "zero trades exist anywhere in the window, therefore `tape_end` inside it is structurally impossible" was **wrong**. It treated a *current* absence of data as a *permanent* absence — the mirror image of the O-45 detection-lag trap this project correctly avoided for the 177 `resolution_date`-only markets, fallen into in the opposite direction within 24 hours. General lesson recorded: **after an outage, absence-of-data is not evidence of absence-of-event until backfill has demonstrably completed.**

**Narrower real loss confirmed:** `order_book_snapshots` cannot be backfilled — book depth only exists live, so ~14 days of forward calibration data is genuinely and permanently lost. That conclusion from 08-07 stands; it's just far narrower than 08-07's framing implied.

**Gap-flagging: deferred, not cancelled.** The record-broadly/exclude-narrowly plan and its pre-stated severity rule (gap >25% of trading life, or within 14 days of `tape_end`) are unchanged, pending a settled baseline — see Part 2, Gate B.

---

## Part 2 — 2026-08-09 (Sunday)

### Gate A — system healthy

- 08-08's manual run completed (exit 0, 32/33 steps, 3h11m). The one FAILED step was "Run test suite" — see Gate B, this is not a maintenance failure, it's the population-convergence tests correctly firing. Today's scheduled 06:00 run completed clean (35/36). No reboot since 08-08 08:44; all three services up.
- Sunday Writer A full ELO recalc — the first since the outage, running against an actively-backfilling tape — ran 03:00–05:03, exit 0, 29,733 updated / 0 failed, no divergence signals (no sign flips, no negatives, no new NULLs, no soft-cap breaches). Population drift 29,745 → 29,733 (−12).
- `audit_invariants.py`: 0 CRITICAL, 2 REGRESSION (one fewer than the 3-item baseline; not investigated further this session). O-37 quarantine: 84 markets still flagged, invariant intact.
- **Caveat flagged, not glossed over:** the maintenance script has no PID logging or lock file, so overlap between the manual 08-08 run and the automatic 06:00 run can't be cleanly ruled out from the logs alone. Small hardening item, carried to next session (State For Next Session, item 4).

### Gate B — convergence NOT met, flagging deferred a second time

| check | Aug 07 night | Aug 08 morning | Aug 09 |
|---|---|---|---|
| `tape_end` in outage window | 0 | 3,066 | 4,979 |
| opened during outage | 0 | 2,821 | 4,767 |
| open-through | 4 | 147 | 197 |
| `resolution_date` in window | 177 | 185 | 178 |

Three of the four counts moved 34–69% day-over-day. Direct evidence: the `trades` table grew by 19,330 rows since the prior high-water mark, 17,587 of them carrying in-window timestamps.

**Independent corroboration:** `run_tests.py` showed 5 failures, all 5 in `test_backtest_window_population.py` — the B5/backtest-population reconciliation checks built 07-23/24. They're failing because the population is genuinely moving underneath them. Two separate instruments (the manual count sweep and the test suite) agreeing independently — the guard built for exactly this case is doing its job. Noted for later: if backfill runs long, consider marking these known-failing-pending-convergence explicitly rather than leaving 5 red tests indefinitely (the O-35 cry-wolf lesson — a red suite that's expected-red for a known reason should say so, or it trains people to ignore red).

**Order-book capture has resumed post-outage** (last snapshot 09:05 UTC) — the book gap is closed-historical, not still accruing. This was the item that would have jumped the deferral queue (permanent, non-backfillable loss, still open); it hasn't, because it's no longer open.

Frozen population `bt_pop_2025-11-01_v1` remains intact and untouched: 4,712 rows, `MAX(tape_end) = 2026-07-20`.

### B3 scoping — the session's real finding

- Ran the actual point-in-time consensus signal count on the holdout window (2026-06-01 → 2026-07-20, 353 of 4,712 frozen markets): **LEGENDARY-only primary spec = 9 signals / 8 distinct clusters. LEGENDARY+NEAR_LEGENDARY fallback = 25 / ~24.** The design's own pre-stated requirement is 60–120 independent clusters to certify an 8–10pt edge. Primary spec short by roughly an order of magnitude; fallback still short by 4–6x. This is a floor — price-band and liquidity filters (FABLE §4.2) were not yet applied and would shrink it further.
- Lookahead audit came back clean, re-verified by reading the code rather than trusting prior docs: PIT ELO, PIT positions, and `price_at()` are all genuinely bounded to T. The cluster-label leak was argued, not assumed: 43/4,712 markets (0.9%) had their event-cluster label settled using resolution outcomes — but that's a knowability violation about market *structure* (which markets are mutually exclusive), not outcome, and it only ever *un-merges* a false single into siblings, never fabricates exclusivity where none exists. It increases eligible n correctly rather than inflating it falsely. Low residual risk; named in the threat register as a quality issue, not a knowability breach.
- New finding, not previously recorded: **trade-result-availability-as-of-T.** There is no `evaluated_at` column, so the PIT replay reads today's `trade_result` rather than what was actually known at T. Inherited from B1b, unfixed, n=1 observed divergence in this pass. Treated as a sensitivity check to run during the holdout, not a blocker.

### The reframe (decision record, commit `4efe74f`)

- **Rejected** the pre-registered Pool-C-top-N widening fallback: it doesn't fix statistical power, it changes the hypothesis to a different one that happens to have more data. It also blurs exactly what the ELO system exists to do — separate "elite" from "merely tracked and active" — which is what placebo P1 was built to test.
- **Phase 2 (live forward paper-trading) becomes the primary experiment.** It obtains n by accumulating time, not by weakening the cohort; it has no PIT reconstruction at all, so the reconstruction caveats (backfill-availability, cluster-label knowability, the B2 probe's 73.1% price cross-source figure) simply don't apply; and it answers the operational question the backtest structurally can't — whether the live pipeline, with real lags and outages, can actually harvest an edge.
- **Phase 1/B3 is repurposed**, not discarded: (a) a rung-A kill-test — asymmetrically useful at low n, since a clean zero is still meaningful (thesis dead at the root even under the most favorable measurement conditions) while a positive result at n=8-9 clusters is not certifiable; and (b) a plumbing dress rehearsal proving the signal spec, entry pricing, cost model, and stats layer before committing 9–12 months to Phase 2.
- The distinction recorded explicitly: this was acting on a **pre-registered contingency** (FABLE design §8, assumption 5's own stated trigger), not a post-hoc rescue invented after seeing an unwelcome number.

### Research findings (externally sourced 2026-08-09 — full detail in the decision record)

- **Polymarket Fee Structure V2** (effective 2026-03-30) **falsifies** the FABLE design's §8 assumption 2 (no trading fee). Geopolitics is fee-free; Politics is fee-bearing (feeRate ≈ 0.04, max ~$1.00/100 shares). The fee formula peaks at 50% probability — exactly our contested band. Makers pay zero fees **and** receive rebates (15–25% of taker fees redistributed daily), so the standing limit-order-only rule is a small positive carry, not merely cost-avoidance. **Open item:** whether Polymarket's own fee taxonomy classes our `category='Elections'` markets as fee-bearing "Politics" is unverified against the live API.
- **Paper trading systematically overstates.** Treat simulated P&L as an optimistic ceiling; every ambiguous modeling choice should push results worse, never better. Phase 2 being more trustworthy than the underpowered backtest does not make it definitive — the design's post-Phase-2 real-capital gate stays exactly as strict.
- **Queue position is the one thing that cannot be simulated** — its value can be the same order of magnitude as the half-spread, and orders resting deeper in the book fill against more informed flow. This validates the existing Book M (confirmatory) / Book P (bias-flagged) split. Mitigation available now: bound queue risk using B4's already-accumulating depth-at-touch data, before the Phase 2 clock starts.
- **Prediction markets strip out most of the execution risk** the general paper-trading literature warns about, for a hold-to-resolution binary contract: no exit slippage, no round-trip spread, no borrow cost, no overnight gap risk, no exit market impact. Real cost surface narrows to entry spread + entry fee (zero if maker) + resolution risk.

### Artifacts (commit `4efe74f`, trading-swarm, pushed to `origin/master`)

- **New:** `brain/decisions/2026-08-09-phase2-primary-and-paper-trading-preparation.md` — deliberately **not** O-numbered. O-numbers track discrete data-integrity anomalies in the overhang ledger; this is a strategic-pivot-plus-external-research record, filed as a design-level document extending the FABLE design instead.
- **Amended:** `2026-07-17-edge-proof-experiment-design-FABLE.md` — dated, additive `AMENDMENT (2026-08-09)` block matching the doc's own established CORRECTION convention; original text preserved throughout. §3.4 cost model (no-fee assumption struck through, V2 schedule inserted), §4/§4.2 (Phase 2 now primary, no longer conditional on a Phase-1 GO), §8 assumptions 2 and 5 marked RESOLVED-AND-FALSIFIED / RESOLVED-NEGATIVE respectively.

---

## State For Next Session

1. **Re-check the four structural counts** in the Gate B table. Flag only once two consecutive readings are materially unchanged — still moving as of 08-09.
2. **Work the pre-flight checklist** from the decision record, in rank order: (a) resolve the Elections fee classification against the live API and rebuild the cost model on the V2 schedule including the maker rebate; (b) measure the true live signal rate — the holdout implies ~1.3 signals/week → 60 resolved bets ≈ 46 weeks, not the design's original 4–9 month estimate — and decide/pre-register any universe-widening *before* the Phase 2 clock starts, never mid-run; (c) calibrate queue risk from B4's accumulated depth data; (d) freeze the spec and commit a config hash; (e) automate signal recording end-to-end; (f) keep the journal a separate artifact from the position log.
3. **B7 (`paper_trades` table + scorer) and the live signal-recording loop move up the build order** — every week Phase 2 hasn't started is n that can never be recovered later.
4. **Carried:** elections calibration re-run (O-40), RQ1.1 repoint-and-re-run, O-38, O-18, the maintenance-script lock-file hardening item (Gate A caveat), and the 5 currently-red population-reconciliation tests (Gate B) — expected to clear once the backfill converges, not a regression to chase now.

---

## Methodology Thread

The 08-07 → 08-08 correction is the sharpest lesson from these two sessions: the detection-lag trap was correctly identified and avoided in one direction (refusing to flag the 177 `resolution_date`-only markets), then fallen into in the exact inverse direction within 24 hours (treating a current absence of trades as proof the outage created a permanent hole). Writing down both directions, not just the one that was caught first, is what actually makes the lesson stick rather than just closing the incident.

Deferring the gap-flagging twice, on evidence both times, was correct both times — the counts were genuinely still moving, corroborated independently by the test suite catching the same drift the manual sweep did. The blocked time wasn't wasted: it went into B3 scoping, which surfaced the power problem *before* the backtest harness was fully built rather than after an ambiguous holdout run had already burned the one-shot holdout discipline the design itself requires.

The power finding arrived via a pre-registered trigger (FABLE §8 assumption 5's own stated fallback condition), which is exactly why the response — reject the further cohort-widening, promote Phase 2 — is a contingency the design already committed to, not a rationalization invented after seeing an inconvenient number.
