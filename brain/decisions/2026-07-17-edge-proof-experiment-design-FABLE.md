# Edge-Proof Experiment Design — Does the elite cohort's aggregate positioning beat the market?

**Date:** 2026-07-17
**Author:** Claude Fable (strategic design session, read-only survey of both repos + live DB)
**Status:** DESIGN — nothing implemented, nothing changed. Awaiting Oscar's review.
**Decision this enables:** whether 9 months of trader-tracking infrastructure has produced a tradeable asset, a diagnosable near-miss, or a disproven thesis. **Disproof is a valid, valuable outcome** — this design is built so a negative result is trustworthy and diagnostic, not just "no."

---

## 0. The hypothesis, stated precisely

**H1 (the thesis):** At time T, the aggregate net positioning of the point-in-time LEGENDARY-tier cohort on an open, contested geopolitics/elections market predicts resolution better than the market price itself, by enough to survive realistic entry lag and transaction costs.

**H0 (the null):** After conditioning on the market price at realistic entry time, cohort positioning carries no exploitable information — the market price already reflects (or beats) whatever the cohort knows, and/or the residual edge is smaller than costs.

Operationally: for a portfolio of cohort-consensus bets entered at realistic prices with realistic costs, is **mean(outcome − p_entry_after_costs) > 0**, statistically distinguishable from zero at the effect sizes worth trading?

Three things this hypothesis is NOT (scope discipline):
- Not individual-trader mirroring (STR-003 tests that separately; it continues unchanged).
- Not "does high ELO predict trader-level future performance" (Stage 0b partially addressed that; useful but different).
- Not "is the cohort smarter than average traders" — the benchmark is the **market price**, the hardest benchmark available. Beating other traders is irrelevant if the price already beats you.

---

## 1. What the system actually has (verified tonight, read-only — every number below queried or read from live code/DB on 2026-07-17)

### 1.1 The cohort machinery — PROVEN facts

- **Canonical tier gate** (`monitoring/column_definitions.py`): LEGENDARY = `geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND research_excluded = 0 AND bot_type IS NULL`. NEAR_LEGENDARY = same at ≥1800. Pool C gate = `geo_elo NOT NULL, geo_elo_active >= 500, geo_resolved_trades_count >= 10, geo_directionality_score NOT NULL, bot/wash clean`.
- **Cohort size today:** 13 LEGENDARY, 32 NEAR_LEGENDARY, Pool C = 3,223.
- **geo_elo is a deterministic, replayable fold** (`scripts/update_geo_elo.py:_compute_geo_elo`): start 1500; per qualifying resolved trade in timestamp order, `elo += K·(actual − expected)` with expected = entry price (Yes) or 1−price (No), K = 32/24/16 by trade count, ratchet cap `1500 + 150·(i+1)`. Qualifying = geo/elections category, `trade_result IN ('won','lost')`, entry price ∈ [0.10, 0.80], trade-gap markets excluded. **This is already a market-relative-edge measure** (actual minus market-implied probability), consistent with the Stage-0b finding that market-relative edge, not win rate, is the correct skill measure.
- **geo_elo_active decay** (`column_definitions.compute_geo_elo_active`): `geo_elo × 0.5^(days_dormant/180)`, dormancy = days since last geo trade.
- **Consequence (the single most important feasibility fact): point-in-time geo_elo is reconstructable at any historical T** by replaying the fold using only trades whose markets had resolved before T, and computing decay relative to T. Nothing about the formula requires future information. Caveats in §4.1 — the reconstruction is *idealized*, not perfect.

### 1.2 Point-in-time records — PROVEN facts

- **`elo_snapshots` table: daily true point-in-time snapshots exist from 2026-06-11 to today** (30 snapshot dates, 81,736 rows, full Pool C each day, with tier). 33 distinct addresses have held LEGENDARY across the 30 days (12–25 per day) — **tier membership turns over materially week to week**, which is exactly why point-in-time correctness matters.
- **`str002_signals`: 151 signals registered live 2026-06-14 → 2026-07-14** with genuinely point-in-time `market_price_at_registration`, `smart_money_pct`, gap, tier, trader counts. 100 resolved, 38 correct. This is an existing, honestly-collected forward dataset (of a *flawed* signal spec — see §2).
- **`order_book_snapshots`: 61 rows, 4 markets** — real bids/asks/spread/depth capture exists but has barely begun. Not enough to calibrate costs historically; enough to prove the capture path works.

### 1.3 Trade/market data — PROVEN facts

- 9.87M trades (2022-12 → today; 8.0M live-polled `polymarket_api`, 1.87M `background_backfill`), 6.3M positions (FIFO entry/exit with timestamps), 223K resolved markets, **10,091 resolved geo/elections markets** (clean of trade-gap flag).
- Tracking began 2025-08-10 (earliest `first_seen`). Trades before a trader's discovery exist via backfill.
- **Signal density (hindsight upper bound, using today's cohort):** resolved geo/elec markets with pre-resolution positions from ≥1 current-LEGENDARY trader: **738**. Using the ≥1800 clean-pool cohort (45 traders): ≥1 trader → **1,532** markets; ≥2 → **567**; ≥3 → **268**; ≥5 → **108**. The experiment has a real sample to work with, but consensus-of-many is rare: the design must work at 2–5 traders per market, not 20.
- **Known data outages** (exclusion/handicap windows): trade-gap Apr 7–18 2026 (flagged in DB); power cuts July 1 and July 11–12 2026.

### 1.4 What does NOT exist — PROVEN gaps

- **No historical market-price series.** `clob_token_id_yes/no` populated on only **2 of 10,108** resolved geo/elec markets. Order-book history: 61 rows. The market price at historical time T must be either (a) fetched retrospectively from Polymarket's CLOB `prices-history` endpoint (token IDs first resolvable via Gamma) — **retention for old/delisted markets is UNVERIFIED, this is the #1 feasibility probe** — or (b) estimated from our own trade tape (real executed prices, but sparse/biased in thin markets).
- **No immutable knowability log.** `last_checked` is overwritten; we cannot reconstruct *when the system learned* a market resolved. §4.1 works around this with a conservative margin; §6 proposes fixing it going forward.
- **No pre-June-11 ELO snapshots.** Anything earlier is reconstruction (§4.1), not record.

### 1.5 What STR-002 already taught us — the flaws this design must not repeat

From the 2026-06-30 thesis-cell analysis (9/40 → later 38/100 correct; all verified against `str002_signals` and source code):

1. **Share-weighted, not ELO-weighted** — despite the documented premise, `pre_resolution_intelligence.py` weights by `entry_shares`; one large mediocre position dominated the "smart money %."
2. **NEAR_RESOLVED contamination** — 77.5% of signals fired on markets already at ≤0.10 or ≥0.90; divergence ≥60pt scored **0/24**. Thin-pool unanimity (smart-money % exactly 0 or 1) scored 1/13. Divergence magnitude was a sample-size artifact, not conviction.
3. **Crowded-field YES trap** — 13 of 40 signals were separate YES bets on ~11 mutually exclusive candidates in one election; structurally guaranteed losses. Effective independent n was ~10, not 40.
4. **Tier gates on the (then-corrupted) `comprehensive_elo`** — 39/40 signals gated by a column that was base×pnl only at the time. The ELO arc has since fixed the column's integrity, but this design uses **geo_elo_active** for cohort definition (the column that was never corrupted and matches the geo domain).
5. **`edge_at_entry` couldn't distinguish "wrong" from "late"** — no price trajectory, single-point scoring. The lag-sweep in §4.3 is the direct answer.
6. **The cell that actually tests the thesis — proven trader × contested market — reached n=2.** This whole experiment is, in essence, that cell run at scale with the contamination removed.

The 2026-06-30 verdict was "not falsified, not validated." This design is built to force one of those two words to win.

---

## 2. The five traps and the design's answer (summary)

| Trap | Design answer | Detail |
|---|---|---|
| 1. Costs & slippage | Cost-curve reporting (edge as a function of haircut 0–5¢), primary spec at 2¢/share + spread; forward order-book capture calibrates the real number; GO/NO-GO applies at the calibrated cost | §4.4 |
| 2. Entry-timing realism | Detection lag modeled explicitly (poll cadence + processing); entry price sampled at T_detect+30min from price history, never the cohort's own price; lag-sweep {0, 30m, 2h, 24h} makes decay visible | §4.3 |
| 3. Point-in-time correctness | Replayed cohort with knowledge-lag margin + `first_seen` gating + write-time rules (the O-33 discipline); snapshot-gold era (June 11+) uses true recorded snapshots | §4.1 |
| 4. Out-of-sample | Time-split train/validation/holdout; spec frozen and written to brain/ before the holdout is ever run; holdout is single-shot | §4.5 |
| 5. Significance | Event-cluster bootstrap (correlated bets deflated honestly), one-sided test on after-cost edge, explicit power statement: this experiment certifies ≥8pt edges, not 3pt ones — and sub-5pt edges die to costs anyway | §4.6 |

---

## 3. Phase 1 — Backtest

### 3.1 (§4.1) Point-in-time cohort construction

**Two eras, different fidelity:**

- **Snapshot-gold era (2026-06-11 → present):** cohort at time T = the LEGENDARY (and, per variant, NEAR_LEGENDARY) rows of the latest `elo_snapshots` date ≤ T. True records, zero reconstruction. This era overlaps the holdout split (§4.5) — deliberately: the highest-stakes segment gets the highest-fidelity cohort.
- **Reconstructed era (2025-11-01 → 2026-06-10):** cohort at T computed by a **PIT replay engine** (build item B1):
  1. Universe: traders with `first_seen ≤ T` (we cannot act on a trader we hadn't discovered — this kills discovery-survivorship: a trader leaderboard-discovered in May must not appear in a March cohort).
  2. Qualifying trades: the trader's geo/elec trades with entry price ∈ [0.10,0.80] in markets with `resolution_date ≤ T − 3 days` (the **knowledge-lag margin** — a proxy for "the system had learned this resolution by T," since true detection timestamps weren't preserved; 3 days is conservative vs. the daily resolution sweeps).
  3. Replay `_compute_geo_elo` over those trades; compute decay vs T; apply the Pool C and LEGENDARY gates with replayed values (`geo_resolved_trades_count`, `geo_directionality_score` replayed the same way).
  4. `bot_type` / `wash_trade_suspect` / `research_excluded`: use **today's** labels (mild hindsight, flagged in §7 — it's exclusion-only and mostly cleans; sensitivity variant runs without them).

**Honest framing of the reconstruction:** it answers "who *was in fact* elite at T given what had objectively resolved," using today's cleaned resolution data — an *idealized* point-in-time, slightly better than what the live system (with its since-fixed bugs) would have computed on that date. This is the correct test of the **thesis** (is elite-cohort positioning informative?); it is slightly optimistic about **operational deployability in the past** — which doesn't matter, because deployability is Phase 2's question and Phase 2 has no reconstruction at all.

**Position knowability (the O-33 write-time rule, applied):** the *signal side* (what positions the cohort holds at T) may only use trades we would have observed by T:
- Primary spec: only trades with `timestamp ≥ trader.first_seen` (executed while we were watching → ingested within ~15 min) and `timestamp ≤ T`.
- Backfilled pre-discovery trades may inform the trader's *ELO qualification* (legitimate: at time T the live system genuinely had the backfilled history of any trader discovered before T) but **never the signal** (we can't know at T about a position the backfill hadn't yet written). `backfill_attempted` is a single overwritten timestamp, so per-trade write-time is unrecoverable — the `first_seen` rule is the airtight subset.
- Bets whose detection falls inside a monitoring outage window (Apr 7–18, Jul 1, Jul 11–12) are dropped (we provably couldn't have acted).

### 3.2 (§4.2) Signal definition — primary spec (pre-registered, deliberately minimal)

For each open geo/elec market M on each day T in the backtest window:

1. **Market filters:** `markets.category ∈ {Geopolitics, Elections}` (the clean column — never `trades.market_category`, per O-2/O-30); market price at T ∈ **[0.10, 0.90]** (the CONTESTED band — kills STR-002's NEAR_RESOLVED failure mode); trailing-7-day trade count on our tape ≥ 20 (liquidity floor; tunable on train only); market not in a trade-gap/outage window.
2. **Cohort positions at T:** for each cohort member (§4.1), net open exposure in M = Yes-capital − No-capital across positions entered ≤ T (per knowability rules) and not exited by T. Members whose per-market capital split is near-balanced (|net|/(gross) < 0.7) are excluded from this market — LP/market-making behavior, STR-002's dilution source.
3. **Consensus rule (one trader = one vote):** signal fires on side S when ≥2 cohort members hold net S **and** ≥⅔ of positioned members agree on S. Equal-weight votes are the primary spec *because* STR-002's failure was capital-domination and thin-pool artifacts; ELO-weighted and capital-capped variants are train-split secondaries only.
4. **Mutual-exclusivity guard:** markets are grouped into event clusters (build item B5, extending `enrich_str002_metadata.py`). Within a cluster of mutually exclusive outcomes, at most **one** bet, on the strongest signal (most voters, then largest majority); never multiple YES bets in one candidate field.
5. **One bet per market:** first day the rule fires. Entry per §4.3; hold to resolution (the thesis is about predicting resolution); outcome = 1 if S wins.
6. **No divergence threshold in the primary spec.** The primary question is simply whether consensus-side bets beat their entry price on average. A minimum-divergence filter θ (e.g., cohort side priced ≥10pt below the ⅔-majority "implied" conviction) is a train-only secondary — one fewer fitted parameter, and STR-002 proved divergence magnitude can invert.

Rationale for minimalism: with ~268–567 candidate markets and heavy clustering, every tuned parameter is an overfitting risk. The primary spec has exactly three numbers (price band, ≥2 voters, ⅔ majority), all fixed a priori from STR-002's published failure analysis rather than fitted to this data — and the price band is inherited from geo_elo's own qualifying-trade definition.

### 3.3 (§4.3) Entry-timing and price realism

- **Detection time:** T_detect = cohort trade ingestion (≤15 min post-execution for live-polled trades). **Action time:** T_act = T_detect + 30 min (processing + human/agent latency; conservative).
- **Entry price = the market price at T_act — never the cohort trader's fill price.** Source, in order of preference: (a) CLOB `prices-history` series for the market's token (build item B2 — **feasibility unverified for resolved/delisted markets; probe 50 markets before anything else**); (b) our own trade tape: the nearest executed trade price in [T_act, T_act+6h], any tracked trader, adjusted to the signal side. If neither source yields a price within 6h → the bet is **dropped and counted** (a high drop rate is itself a finding: the signal fires in markets too thin to enter).
- **The lag sweep — STR-002's central unanswered question, answered by design:** every bet is priced at lags {0, 30 min, 2 h, 24 h}. The resulting **edge-vs-lag decay curve** distinguishes "the cohort is right but the price adjusts before we can act" (steep decay → thesis true but untradeable at our latency) from "the cohort adds nothing at any lag" (flat-at-zero) from "tradeable" (positive at 30-min lag). Primary spec scores at 30 min.

### 3.4 (§4.4) Cost model

- **Fee structure (to verify at build time — stated as of knowledge cutoff):** Polymarket charges no maker/taker trading fees on standard markets and gas is relayed; the real costs are **spread crossing, slippage, and (for early exit) round-trip spread**. Verify the current fee schedule before freezing the spec; if a fee exists, add it to the haircut.
- **Primary cost spec:** entry at price + half-spread + slippage, modeled as a flat haircut **h = 2¢/share**, with the full curve **h ∈ {0, 1, 2, 3, 5}¢** reported for every result. No result is quoted without its cost curve.
- **Calibration path:** the 61 existing order-book snapshots prove the capture works; build item B4 expands capture (hourly, all open geo/elec markets) so that within ~4 weeks we have an empirical spread/depth distribution for exactly the market class we'd trade. The GO/NO-GO (§4.7) is evaluated at the **calibrated** haircut, not the assumed one. Position-size realism: assume $100/bet notional; if calibrated depth-at-10 levels shows $100 moves the book in a material fraction of signal markets, the haircut rises accordingly.
- **Hold-to-resolution avoids exit costs** (resolution pays $1/0 without a trade); the cost model is entry-side only in the primary spec.

### 3.5 (§4.5) Train / validation / holdout protocol

Split by **market resolution date** (no market appears in two splits; cohort replay always uses only pre-T data regardless of split):

| Split | Resolution window | Role |
|---|---|---|
| Train | 2025-11-01 → 2026-03-31 | All exploration, all variant tuning (weighting schemes, liquidity floor, θ, cohort width ≥1800 vs ≥2175) |
| Validation | 2026-04-19 → 2026-05-31 | One refinement round: the train-selected spec is confirmed or one pre-listed fallback is chosen. Then the spec is **frozen and committed to brain/** |
| Holdout | 2026-06-01 → present | **Single-shot.** Run once, after freezing. Overlaps the snapshot-gold era (June 11+) — the decisive segment uses true recorded cohorts |

- Before Nov 2025 the replayed cohort has too little resolved-trade runway (tracking began Aug 2025) — excluded.
- Apr 1–18 resolutions excluded (trade gap).
- The 151 live-registered STR-002 signals (June 14+) additionally serve as a **cross-check within holdout**: for markets where both fire, the new spec's entry prices can be validated against the honestly-recorded `market_price_at_registration`.
- **Pre-registration discipline:** the frozen spec (all parameters, the exact SQL/queries, the cost number, the statistical test) is written to `brain/decisions/` and committed **before** the holdout run. The holdout result is reported whatever it says. If the holdout is ambiguous (§4.7), we do NOT re-cut it — Phase 2 becomes the decider or the project takes the NO-GO.

### 3.6 (§4.6) Statistics: metric, test, power — honest about what this can and cannot detect

- **Primary metric:** mean after-cost edge per bet, `E = mean(1{side wins} − p_entry − h)`, on the holdout, at 30-min lag, calibrated h. Equivalently: expected profit per $1 of notional.
- **Secondary metric:** paired Brier comparison — cohort-consensus side as a probability forecast vs the market price, per bet, Diebold-Mariano-style on the paired differences. (Answers "is the cohort better calibrated than the price," even where the tradeable edge is cost-killed.)
- **Inference:** one-sided test of E > 0 via **cluster bootstrap resampling event clusters** (not individual bets — STR-002's colombia lesson: 13 bets, 1 event). Wilson CIs reported alongside.
- **Power (stated before running, so the result can't be spun):** per-bet SD of (outcome − p) in the contested band ≈ 0.45. At one-sided α=0.05, 80% power: detecting a true 5pt edge needs ~500 independent bets; 8pt needs ~195; 10pt needs ~125. The holdout will plausibly contain **60–120 independent clusters** → **this experiment is powered to certify edges ≥~8–10pt and to rule out edges ≥~8pt. It cannot distinguish a true 3pt edge from zero.** That is acceptable *by design*: a 3pt gross edge dies to 2–3¢ of costs anyway — the experiment is powered for exactly the edges that would matter. Train+validation (larger, lower fidelity) provide supporting-not-confirmatory estimates on ~200–400 additional markets.
- **Multiple testing:** exactly one primary spec tests the hypothesis. All variants (weighting, θ, cohort width, lag points, cost points) are labeled exploratory; any of them promoted to "the result" would be p-hacking and the design explicitly forbids it.

### 3.7 (§4.7) GO / NO-GO

Evaluated on the holdout only, primary spec, 30-min lag, calibrated cost:

- **GO to Phase 2:** point estimate E ≥ +3pt **and** cluster-bootstrap one-sided p < 0.05 **and** ≥30 independent clusters contributed **and** the result survives drop-one-trader ablation (no single cohort member's removal flips the sign — with 13 LEGENDARY traders, one hot hand must not masquerade as a cohort effect).
- **NO-GO:** upper bound of the 90% CI < +2pt (an edge worth trading is ruled out), or the zero-cost/zero-lag ceiling (§4.8 rung A) is itself ≤ 0 (the information isn't there at all).
- **Ambiguous** (positive but non-significant, or significant but cost-marginal): no re-cutting the backtest. Either take the NO-GO, or run Phase 2 as the explicitly-labeled decider with its own pre-registered gate — Oscar's call, made once, with the ambiguity documented.

### 3.8 (§4.8) The diagnostic ladder — making a negative result a diagnosis, not a shrug

The backtest runs as a **ladder of nested variants**, each isolating one potential killer. Reported together, they localize any failure:

| Rung | Cohort | Lag | Cost | Isolates |
|---|---|---|---|---|
| **A** (ceiling) | Hindsight (today's tiers) | 0 | 0 | Is the information in cohort positioning *at all*? A ≤ 0 → **thesis dead at the root** — elite positioning adds nothing beyond price, stop here |
| **B** | Point-in-time (§4.1) | 0 | 0 | A>0 but B≈0 → **the ELO ranking is hindsight** — "elite" is only identifiable after the fact; the ranking system, not the edge, is the failure |
| **C** | Point-in-time | 30m–24h sweep | 0 | B>0 but C≈0 → **too late** — the edge is real but decays before we can act; latency engineering (or maker-side entry) is the frontier, not signal quality |
| **D** (the tradeable claim) | Point-in-time | 30m | calibrated | C>0 but D≈0 → **costs kill it** — real but unharvestable at current liquidity; revisit only if market depth grows |

Plus two placebos, run at rung B settings:
- **P1 — random-cohort placebo:** 1,000 draws of equal-sized cohorts from Pool C members (≥10 resolved trades) *below* the LEGENDARY gate, same consensus rule. The LEGENDARY cohort's edge must beat the placebo distribution (p<0.05). **This is the direct test of whether the ELO ranking specifically — versus mere "tracked, active traders" — carries the information.** If LEGENDARY ≈ placebo > market, the system's value is the tracking net, not the rating; that redirects engineering (widen the net, stop refining the rating).
- **P2 — inverted cohort:** bottom-of-pool consensus should show ≤0 edge. If inverted traders also "beat the market," the pipeline has a leak (look-ahead somewhere) — a built-in fraud alarm on our own plumbing.

The ladder is the reason a "no" is worth having: every NO-GO comes with *which rung failed*, which is a specific, actionable diagnosis (§8).

---

## 4. Phase 2 — Forward test (paper trading), conditional on GO

No reconstruction, no hindsight risk: everything computed live on unresolved markets, recorded before resolution.

### 4.1 Protocol

1. **Signal computation:** daily (piggybacking the existing maintenance cadence), the frozen Phase-1 spec runs against live `elo_snapshots` (true PIT by construction) and live open positions. Every firing is written to a new `paper_trades` table at fire time: timestamp, market, side, cohort voters (addresses + ELOs), market price, full order-book snapshot (B4 capture), event cluster.
2. **Entry recording — two books, per Oscar's limit-order-only standing rule:**
   - **Book M (marketable-limit, primary):** paper-filled immediately at best ask (buying S) + modeled slippage — no fill ambiguity, honest full cost. This book carries the confirmatory statistics, because passive fills have adverse-selection bias (limits fill preferentially when the market is moving against you).
   - **Book P (passive-limit, secondary):** limit at best bid + 1¢; paper-filled only if the tape subsequently prints **through** the limit within 24h, else cancelled-and-logged. Measures how much cost the limit discipline actually saves, and the fill rate — but its P&L is bias-flagged.
3. **Exit:** hold to resolution. Record resolution outcome + date when scored (the existing `score_str002_signals` machinery generalizes).
4. **No manual overrides.** If a signal looks obviously wrong, that observation goes in a journal, not into the position log. The point is to test the spec, not the operator.

### 4.2 Duration, n, and the gate for real capital

- **Signal rate is unknown** (the spec is much stricter than STR-002's 151/month). First 2 weeks measure it; expect 1–4 bets/week. Target **≥60 resolved bets across ≥40 event clusters** — realistically **4–9 months**.
- **Interim looks at n=20 and n=40 are descriptive only** (published to brain/, no decisions). The confirmatory test runs at n=60 resolved (or 12 months, whichever first).
- **Real-capital gate (small size):** Book M after-cost ROI > 0 with cluster-bootstrap one-sided p < 0.05; realized spreads/depth consistent with the Phase-1 cost calibration (i.e., the cost model wasn't optimistic); drop-one-trader ablation still passes; Book P fill rate ≥50% (else the limit-only discipline starves execution and the marketable costs are the real costs). Initial capital cap and sizing are Oscar's call — this design only certifies the signal.
- Phase 2 also produces the **operational** answer Phase 1's idealized reconstruction deliberately deferred: whether the live pipeline (with its real bugs, lags, and outages) can harvest the edge, not just whether the edge exists.

---

## 5. What the current system is missing — build inventory (nothing started; ordered by blocking priority)

| # | Item | Why | Size | Blocks |
|---|---|---|---|---|
| **B2** | **Price-history probe** — resolve `clobTokenIds` via Gamma for 50 sampled resolved geo/elec markets (2/10,108 stored today), hit CLOB `prices-history`, measure retention/granularity for old+delisted markets | Entry pricing (§4.3) is the experiment's spine; if retention fails, the trade-tape fallback becomes primary and uncertainty widens — **must know first** | Small (a day) | Everything in Phase 1 |
| B1 | PIT ELO replay engine — pure-function replay of `_compute_geo_elo` + decay + pool/tier gates, parameterized by T; validated by reproducing the 30 existing `elo_snapshots` dates from raw data (a built-in correctness test: replay vs record) | §4.1 reconstructed era | Medium | Phase 1 rungs B–D |
| B3 | Backtest harness — signal spec + entry pricing + cost curve + ladder + cluster bootstrap; read-only vs production DB (scratch-copy discipline like `writer_a_dry_run.py`) | The experiment itself | Medium-large | GO/NO-GO |
| B4 | Order-book capture expansion — hourly snapshot of all open geo/elec markets (existing `order_book_snapshots` path, widened from signal-linked-only) | Cost calibration (§4.4) + Phase 2 fills; **start now regardless — every week of delay is a week less calibration data** | Small-medium | Calibrated GO/NO-GO; Phase 2 |
| B5 | Event-cluster labeling for historical markets (generalize `enrich_str002_metadata.py`; manual review pass for the holdout) | Honest n (§4.6); mutual-exclusivity guard (§4.2) | Small-medium | Inference validity |
| B6 | Immutable knowability log going forward — append-only record of (market resolved, detected-at) and per-batch trade ingestion times | Removes the 3-day-margin proxy for all *future* analysis; the O-33 class fixed structurally | Small | Nothing now; future rigor |
| B7 | `paper_trades` table + scorer | Phase 2 | Small | Phase 2 only |
| — | `elo_snapshots` daily job: **verify it's in maintenance and keep it running** (30/30 days present through today — appears healthy; confirm ownership) | The gold record grows daily | Trivial | Snapshot-gold era |

**Deliberately NOT needed:** any change to the ELO arc (Stage 3/5 proceed independently); `comprehensive_elo` (this design gates on geo_elo_active throughout); the is_taker/transaction_hash chain (irrelevant here — worth noting when deciding that item's fate: this experiment does not rescue it).

---

## 6. Threats to validity — and the defense for each

| # | Threat | Defense | Residual risk |
|---|---|---|---|
| 1 | Backfilled trades leak future knowledge into signals | Signal side restricted to `timestamp ≥ first_seen` (live-observed); backfill allowed only for ELO qualification of already-discovered traders (§4.1) | Low; sensitivity variant: live-polled-only for everything |
| 2 | Reconstruction uses today's *cleaned* resolution data (idealized PIT) | Framed honestly as a thesis test, not a deployability test (§4.1); 3-day knowledge margin; snapshot-gold holdout has no reconstruction; Phase 2 has none at all | Medium in the reconstructed era, ~zero where it matters most |
| 3 | Discovery survivorship (traders found *because* they won) | `first_seen ≤ T` gate — a trader exists for the experiment only after the live system found them | Low |
| 4 | The 2175/1800 thresholds were themselves chosen by looking at this data | Treated as given structural parameters, not re-fit; **P1 placebo tests ranking validity independent of any threshold**; cohort-width is a train-only variant | Medium — inherent to testing a system on the era that shaped it; only Phase 2 fully escapes it |
| 5 | Bot/wash/exclusion labels applied retroactively | Exclusion-only (cleans, doesn't select winners); sensitivity variant without them | Low |
| 6 | Wash-traded or self-dealt "skill" fabricating a LEGENDARY rank | Pool C bot/wash gates + directionality filter; drop-one-trader ablation catches a single fabricated star | Medium — a sophisticated fake survives; forward test + position-size floors mitigate |
| 7 | Entry prices reconstructed from sparse tape are stale/biased | CLOB history primary (B2 probe decides); 6h staleness cap with dropped-bet accounting; liquidity floor | Medium until B2 reports |
| 8 | Correlated bets inflate n | Event-cluster grouping (B5) + cluster bootstrap + one-bet-per-cluster guard | Low-medium (clustering quality dependent — manual pass on holdout) |
| 9 | Variant-shopping / p-hacking | One pre-registered primary spec; frozen-before-holdout commit; ambiguous ≠ re-cut | Low if the discipline holds — the commit trail makes violations visible |
| 10 | Monitoring outages create fake "we'd have acted" windows | Outage windows excluded from actionability (§4.1) | Low |
| 11 | 13-trader cohort → one hot hand masquerades as cohort skill | Drop-one ablation in the GO gate; per-trader contribution report | Medium — small cohorts are the reality; NEAR_LEGENDARY widening is the tested fallback |
| 12 | Category labels incomplete (O-2/O-30 class) | `markets.category` only (verified clean per ledger); the ~4,398-market unclassified backlog shrinks the universe but doesn't bias it (unclassified ≠ correlated with cohort positioning in any known way — **inference, not proven**) | Low-medium |

---

## 7. What we learn under each outcome — the decision table

| Outcome | Interpretation | What Oscar does with it |
|---|---|---|
| Rung A ≤ 0 | Elite positioning carries no information beyond price, even with hindsight tiers, zero lag, zero cost | **Thesis disproven at the root.** The 9-month premise fails on its own terms. Redirect: the infrastructure's residual value is market-data collection, not trader-following. This is the cheapest, cleanest possible "no" |
| A > 0, B ≈ 0 | Information exists but only hindsight identifies who has it | **The rating, not the thesis, is the failure.** ELO refinement (better skill measures, faster identification) becomes the priority — with a concrete target: close the A−B gap |
| B > 0, C ≈ 0 | Real, identifiable edge that decays before we can act | Latency is the frontier: faster polling, push-based detection, maker-side entries. The 15-min poll cadence becomes the named bottleneck with a measured cost |
| C > 0, D ≈ 0 | Edge survives lag but not costs | Untradeable today; parked with a re-trigger condition (liquidity growth, fee changes). Signal has research value (calibration secondary metric) |
| D > 0, GO, Phase 2 confirms | Tradeable edge, live-verified | Small real capital per the gate; scale governed by fill data |
| D > 0, GO, Phase 2 fails | Backtest edge didn't survive live contact | The gap between idealized PIT and operational reality (threats 2/4) was the edge. Diagnose which via Phase 2's recorded books; likely NO-GO overall — and the backtest harness gets an honest post-mortem |
| LEGENDARY ≈ P1 placebo > market | The tracking net works; the rating adds nothing over "active clean traders" | Stop refining ELO; widen the net; rerun with the cheap cohort |

Every row is an action, not a shrug. That's the standard this experiment has to meet to be worth building.

---

## 8. Assumptions register (each one falsifiable, checked at build time)

1. CLOB `prices-history` retains data for resolved/delisted markets at usable granularity — **UNVERIFIED, B2 probes first.**
2. Polymarket still charges no trading fee on standard markets — verify current schedule before freezing the cost spec.
3. `elo_snapshots` has run daily without gaps June 11 → today (30/30 dates present — verified; job ownership to confirm).
4. The positions table's FIFO net-position reconstruction is accurate enough post-O-15/O-20 fixes for cohort exposure at T — the drain has plateaued per the corrected Stage-0a gate, but the backtest should re-check orphaned-trade counts for its specific cohort members (small query, part of B3).
5. ~45 clean-pool traders at ≥1800 is enough cohort width for ≥2-voter consensus on a usable number of markets — supported by the 567-market ≥2-trader count (hindsight version); the PIT version will be smaller by an unknown factor — **B1's first output is this number**, and if it collapses (<100 train-split bets), the design's pre-approved fallback is widening to Pool C top-N by replayed ELO (documented as a variant, not a re-fit).
6. 30-minute action latency is achievable by the live system — Phase 2 measures it directly.

---

## 9. Suggested build order (when Oscar green-lights — none of this is started)

1. **B2 price-history probe** (a day; kills or confirms the design's spine).
2. **B4 order-book capture ON** (small; every week of delay costs calibration data — useful regardless of this experiment's fate).
3. **B1 replay engine** + its replay-vs-snapshot validation; report the PIT cohort widths and bet counts per split (assumption 5 checkpoint).
4. **B5 event clustering**, then **B3 harness**; run train split; explore; validate; **freeze and commit the spec**.
5. Run the ladder + placebos on the holdout, once. Publish rungs A–D and the GO/NO-GO verdict to brain/.
6. If GO: B7 + Phase 2 live.

Total to a Phase-1 verdict: roughly 2–4 focused sessions of build plus one of analysis — cheap relative to what it decides.

---

*Method note: every DB figure in this document was queried read-only tonight (2026-07-17); every code claim was read from live source. Facts are labeled proven; the two load-bearing unknowns (price-history retention, PIT cohort width) are flagged as probes B2/B1, and the design fails gracefully — trade-tape pricing, Pool-C widening — if either comes back thin. Production DB, services, code, and crontab were not modified. The only artifact of this session is this file.*
