# Phase 2 Becomes the Primary Experiment — B3 Power Shortfall and External Cost/Microstructure Research

**Date:** 2026-08-09
**Author:** Claude Sonnet 5 (documentation session). B3 scoping measurement and external research both conducted by Oscar this session — this record writes them up; no code changes, no DB writes.
**Status:** DECISION — strategic reframe adopted; Phase 1/B3 repurposed; pre-flight checklist open, ranked, none started.
**Numbering:** not O-numbered. O-numbers (`2026-06-29-overhang-ledger.md`) track discrete data-integrity anomalies and bugs found in the live system; this record is a strategic pivot on experiment design plus externally-sourced research, categorically different from that ledger's contents — filed as a design-level decision record instead, extending the FABLE design directly.
**Cross-ref:** `2026-07-17-edge-proof-experiment-design-FABLE.md` (the design this amends — see companion amendment in that file, same date), `2026-06-29-overhang-ledger.md` O-49 (outage self-healing finding — the immediate context for why every week of delay now has a measurable cost), `2026-08-07-session-summary.md` (B3 named as next up, all prerequisites believed done), today's B3 scoping measurement (Part A below).

---

## Part A — The strategic reframe: Phase 2 becomes the primary experiment

### TRIGGER

Today's B3 scoping measured the actual point-in-time consensus signal count on the holdout window (2026-06-01 → 2026-07-20, 353 of 4,712 frozen `bt_pop_2025-11-01_v1` markets):

| Spec | Signals | Distinct event clusters |
|---|---|---|
| Primary (LEGENDARY-only, per the frozen §4.2 spec) | 9 | 8 |
| Pre-approved fallback (LEGENDARY + NEAR_LEGENDARY) | 25 | ~24 |

The design's own pre-stated power requirement (§4.6 of the FABLE doc) is **60–120 independent clusters** to certify an 8–10pt edge. The primary spec is short by roughly an order of magnitude; the pre-approved fallback is still short by 4–6x. **This is a floor** — price-band and liquidity filters from §4.2 were not yet applied on top of this count and would shrink it further, not grow it.

This is not a surprise finding. It is the design's own §8 assumption 5 resolving in its negative branch, exactly as pre-registered: *"if it collapses to <100 train-split bets, the design's pre-approved fallback is widening to Pool C top-N by replayed ELO (documented as a variant, not a re-fit)."* Recording explicitly: **we are acting on a pre-registered contingency, not inventing a post-hoc rescue.** That distinction is the entire point of pre-registration — a data-triggered pivot planned before the data was seen carries none of the p-hacking risk of one improvised after.

### DECISION 1 — Reject the Pool-C-top-N widening

The pre-approved fallback text names Pool C top-N as the next lever if NEAR_LEGENDARY also falls short, which it does (25 clusters vs. a 60–120 requirement). **Rejected.**

Rationale: widening to Pool C top-N doesn't fix power, it changes the hypothesis to a different one that happens to have more data. H1 as stated (§0 of the FABLE doc) is *"the LEGENDARY-tier cohort's aggregate positioning beats the market."* Pool C top-N tests *"traders selected by top-N replayed-ELO rank, at whatever width makes n large enough, beat the market"* — a different, looser claim. A positive result on that widened population couldn't be reported as confirming H1, and a negative result couldn't refute it, because neither result would be about the cohort the thesis is actually making a claim about. It also erases the distinction the ELO system exists to draw — between "elite" and "merely tracked and active" — which is precisely what placebo P1 (§4.8) was built to test. Widening the cohort until P1 becomes untestable by construction defeats the design's own fraud/leak check.

### DECISION 2 — Phase 2 (live forward paper-trading) becomes the PRIMARY experiment

Phase 2 obtains its n by accumulating time rather than by weakening the cohort definition — same LEGENDARY gate, same ≥2-voter/⅔-majority consensus rule, same everything except that cohort membership and market state are read live instead of reconstructed.

It is also methodologically stronger than the backtest it replaces as primary, not just a fallback of convenience:

- **No PIT reconstruction at all.** Cohort membership comes from live `elo_snapshots` — true point-in-time by construction, not the idealized replay of §4.1. Every reconstruction caveat the FABLE doc flags as residual risk — trade-result-availability-as-of-T, the cluster-label knowability question, deleted-duplicate-rows, the 73.1% price cross-source figure from the B2 probe — is an artifact of reconstructing the past. None of them apply to a signal computed and recorded live.
- **It answers a question the backtest structurally cannot:** whether the live pipeline, with its actual lags, actual outages (see O-49's own outage, and O-48's shutdown-hang, both this cycle), and actual bugs, can harvest an edge at all. §4.2 of the FABLE doc already names this as the "operational answer Phase 1's idealized reconstruction deliberately deferred" — that deferral is now the load-bearing reason Phase 2 leads.

### DECISION 3 — Phase 1 / B3 is repurposed, not discarded

Demoted from "the experiment" to two supporting roles:

1. **A rung-A kill-test.** Rung A (§4.8: hindsight cohort, zero lag, zero cost) is asymmetrically informative at low n — a clean zero at n=8-9 clusters is still meaningful (it would mean the thesis is dead at the root even under the most favorable possible measurement conditions: perfect hindsight, no latency, no cost), while a positive result at that n is not certifiable per the power statement above and must not be reported as if it were. Run it; report it as a floor-level check, not a verdict.
2. **A plumbing dress rehearsal.** Proving the signal spec, entry pricing, cost model, and stats layer actually work end-to-end before committing 9–12 months of Phase 2 wall-clock time to a broken harness. This is the standard methodology sequencing — backtest first to filter out broken machinery, forward-test only the survivors — just no longer doing the job of *certifying the effect size*, which Phase 2 now owns.

### Consequence for urgency

If Phase 2 is the real experiment, every week it hasn't started is a week of n permanently lost — there is no way to backfill live-observed weeks later. This moves **B7 (`paper_trades` table + scorer)** and **the live signal-recording loop** up the priority order, ahead of finishing every Phase 1 refinement. Open sequencing question, not resolved here: whether to start the live recording loop in parallel with the rung-A kill-test rather than waiting for Phase 1 to fully complete first — Oscar's call, informed by Part C below.

---

## Part B — Research findings (externally researched 2026-08-09; live sources, not this repo's design doc or DB)

### 1. Fee structure changed — design assumption now falsified

FABLE §8 assumption 2 ("Polymarket still charges no trading fee on standard markets — verify current schedule before freezing the cost spec") was left open. It is now resolved and falsified: Polymarket rolled out taker fees in stages through 2026 (crypto in January, sports in February, a broad schedule in March). **Fee Structure V2**, effective 2026-03-30:

- Taker fees apply across crypto, sports, finance, politics, tech, economics, culture, and weather categories.
- **Geopolitics and world-events markets remain fee-free.**
- Makers pay zero fees and receive rebates, funded by 15–25% of collected taker fees redistributed daily.
- Formula: `fee = shares × feeRate × price × (1 − price)` — peaks at 50% probability, falls off toward the extremes. Politics `feeRate` ≈ 0.04, max roughly $1.00 per 100 shares at the peak.

**Critical open item:** our universe is `markets.category IN ('Geopolitics', 'Elections')` (FABLE §4.2, the clean column per O-2/O-30). Geopolitics is confirmed fee-free. Whether Polymarket's own fee taxonomy classes our "Elections" markets under its fee-bearing "Politics" category is **unverified** and must be checked against the live API — our internal category label is not guaranteed to match their fee-schedule category. This is material precisely because our contested band (price ∈ [0.10, 0.90], FABLE §4.2) is where the fee formula peaks.

Maker rebates mean Oscar's standing limit-order-only rule is not merely cost-avoidance discipline — as a maker under V2 it is zero fees plus a small positive rebate. This should be modeled explicitly in the cost curve, not conservatively assumed away.

**Forward risk:** commentary around the V2 rollout suggests more categories may gain fees over time, potentially including geopolitics. Over a 9–12 month Phase 2 run the cost regime could shift mid-test. The harness must **record the fee schedule in force at each signal**, not apply one constant retroactively across the whole run.

### 2. Paper trading systematically overstates

Consensus across the sources reviewed: treat paper P&L as an optimistic ceiling, not a forecast. Every modeling choice in the harness should push simulated results worse, never better, when the choice is ambiguous. Paper trading is good for proving the system runs, that assumptions aren't obviously wrong, and for exposing lookahead/latency/data quirks — it cannot replicate true fills, market impact, or the emotional pressure of live capital.

**Consequence:** Phase 2 being more trustworthy than the underpowered backtest (Decision 2 above) does **not** make it definitive on its own. FABLE §4.2's post-Phase-2 real-capital gate is doing real work and must not be softened just because Phase 2 is now "the primary experiment" — primary for certifying the thesis is not the same as sufficient for risking capital.

### 3. Queue position is the one thing we cannot simulate

Simulators generally assume a limit order fills the instant price touches it; live, an order sits in a queue behind other resting orders at that price and may not fill at all before the market moves away. Microstructure literature: the value of queue position can be the same order of magnitude as the half-spread; adverse selection is lower near the top of the queue; orders resting deeper in the book execute against larger and more informed flow when they do fill.

**Consequence:** both the fill *rate* and fill *quality* of FABLE's Book P (passive-limit, §4.1 protocol) are optimistic as currently modeled. The existing split — Book M (marketable-limit) carries the confirmatory statistics, Book P is bias-flagged and secondary — is correct on this evidence and must be held firmly, not loosened toward trusting Book P's numbers as the run accumulates.

**Mitigation available now:** B4's order-book capture already gives depth-at-best-bid for our actual signal markets. True queue position can't be reconstructed retroactively, but it can be **bounded**: small depth at the touch implies small queue risk (little competing size ahead of us), large depth implies Book P is heavily optimistic. This calibration should run against data already accumulating, before the Phase 2 clock starts — see Part C item 3.

### 4. Procedural rules to adopt verbatim

- Never modify the rules mid-test.
- Wait for a meaningful trade count before drawing any conclusion (consistent with FABLE §4.2's "interim looks at n=20/40 are descriptive only" rule).
- Systematically compare metrics against backtest values as Phase 2 accumulates; treat simultaneous divergence across multiple metrics as a signal to investigate, not a coincidence to explain away in isolation.

### 5. What prediction markets make easier than the generic paper-trading literature assumes

Worth stating explicitly, because the generic literature above is written for equities and overstates our actual problem surface:

- Hold-to-resolution on a binary contract (FABLE §3.4/§4.1, already the design's convention) means **no exit slippage, no round-trip spread, no borrow cost, no overnight gap risk, no market impact on exit** — resolution pays $1/0 without a trade.
- Our real cost surface is narrow: **entry spread + entry fee (zero if maker, per Finding 1) + resolution risk.** That's materially simpler than the general paper-trading caution above implies.
- Context: average Polymarket spreads tightened from roughly 4.5% in 2023 to roughly 1.2% in late 2025 — typically 1–2¢ on liquid markets, 5–10¢ during volatility or on illiquid ones. This is consistent with B4's own captured range (0.001–0.02) — which is exactly why the FABLE liquidity floor (§4.2, trailing-7-day trade count ≥20) matters: it's the filter keeping signal markets out of the 5–10¢ tail.

---

## Part C — Pre-flight checklist, before the Phase 2 clock starts, ranked by cost of getting it wrong

1. **Resolve the Elections fee question against the live API**; rebuild the cost model on the actual V2 schedule including the maker-rebate credit. Record the fee schedule in force per-signal, not as a constant applied retroactively (Finding 1).
2. **Measure the true live signal rate.** The holdout measurement (Part A) implies roughly 1.3 signals/week at the primary spec → 60 resolved bets ≈ 46 weeks, not the FABLE §4.2 estimate of 4–9 months. If confirmed live, decide **now**, before the clock starts, whether to widen the market universe (adjacent categories) or relax the ≥2-voter consensus rule — and pre-register whichever choice is made, never mid-run. Note this is a different lever from Decision 1's rejected cohort-widening and less damaging to the thesis (it changes what markets get watched, not who counts as elite), but it is still a hypothesis change and must be declared as such, not slipped in silently.
3. **Calibrate queue risk from accumulated B4 depth data** — bound how optimistic Book P can be, using the depth-at-touch heuristic in Finding 3, before Book P numbers start accumulating under the live clock.
4. **Freeze and commit the spec**; the harness should record a config hash at signal-fire time so "this ran against the frozen spec" is independently verifiable via `git log`, not asserted from memory.
5. **Automate recording end-to-end.** Over 9–12 months anything manual drifts. Signals written at fire time, before resolution, no human in the loop (FABLE §4.1's existing "no manual overrides" rule — this item is about making the automation itself robust enough to hold that rule for a year, not about the rule's content, which is already correct).
6. **Set up the journal as a separate artifact from the position log.** Observations belong in the journal; they must never leak into the trade record (FABLE §4.1 point 4, restated here as a build requirement rather than a stated intention).

---

*Method note: Part A's counts were produced by this session's B3 scoping query against the frozen `bt_pop_2025-11-01_v1` population and are read-only. Part B's figures are from external sources queried live this session (2026-08-09) — not from this repo's design doc, not from our own DB — and are dated accordingly; they should be re-verified against Polymarket's live fee-schedule API before being load-bearing in the cost model (Part C item 1), since this document reports what was found, not a guarantee it stays current. No code was written, no production data was modified.*
