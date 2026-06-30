# STR-002 Thesis-Cell Analysis — June 30 2026 Measurement

**Date:** 2026-06-30
**Scope:** Read-only analysis of the 40 scored STR-002 signals, per `brain/strategy-registry.md`'s "Next revalidation due: 2026-07-01" gate. No code or strategy changes made.
**Data source:** `str002_signals` table in `data/polymarket_tracker.db` (first-repo) — the full registry, richer than the JSON findings files in `brain/agent-outputs/str002-scoring/` (adds `gap_pt_at_registration`, `regime`, `event_cluster`, `has_proven_trader`, trader counts). Cross-checked against `2026-06-30-str002-scoring.json`: totals match exactly (40 scored, 22.5% accuracy, -7.7% avg edge).
**Headline numbers:** 9/40 correct (22.5%), avg `edge_at_entry` = -0.0767. Gate requires ≥60% accuracy on ≥10 signals across all tiers.

---

## 1. What STR-002 actually is

Per `brain/strategy-registry.md` (status: EXPERIMENTAL, pre-registered 2026-03-28):

> ELO-weighted smart money consensus on open markets resolving within 7 days compared against market price. Flags divergence > 15pt. Tier system: LEGENDARY / ELITE / QUALIFIED.

**Mechanism** (`scripts/pre_resolution_intelligence.py`): for every open market resolving within 7 days, pull all open positions held by traders with `comprehensive_elo >= 1500` (min 3 such traders). Compute `elite_yes_pct` = **share-weighted** YES% among those positions (NOT ELO-weighted — see Finding A below). If `|elite_yes_pct - market_price*100| >= 15pt`, fire a signal in the divergence direction. Tier is set by the *best* trader present:
- LEGENDARY: any trader with `geo_elo_active >= 2175` AND `geo_accuracy_pool = 1` (clean pool)
- ELITE: any trader with `comprehensive_elo >= 1800`, `research_excluded = 0`, `bot_type IS NULL`
- QUALIFIED: only traders in the 1500–1799 `comprehensive_elo` band

**Promotion criteria** (registry): 4 weeks of daily runs (met — first signal 2026-03-28), ≥10 resolved markets scored (met — 40), ≥60% accuracy across all tiers (failed — 22.5% overall, and no tier individually clears it on adequate n). `feedback-loop-agent` owns the promotion call; Oscar approves.

**`edge_at_entry` is not a price-movement metric.** Per `scripts/score_str002_signals.py`: `edge_at_entry = outcome_correct − market_implied_signal_side`, where `market_implied_signal_side` is the market's own probability for STR-002's chosen side *at signal-registration time* (not the trader's entry price, not a post-signal price track). This is a single-point calibration-vs-outcome measure, not a trajectory. **It structurally cannot distinguish "signal fired too late" from "directional call was wrong" — both collapse to the same low/negative edge.** STR-002 has no analog to STR-003's "price movement > 2pp in correct direction" validation criterion. This is a real methodological gap, not just a finding about this batch — flagging it as something the next iteration needs (see §6).

---

## 2. Tier breakdown — underperformance is NOT uniform

| Tier | n | Correct | Accuracy | Avg edge |
|---|---|---|---|---|
| LEGENDARY | 1 | 1 | 100% | +0.0500 |
| ELITE | 22 | 6 | 27.3% | -0.0777 |
| QUALIFIED | 17 | 2 | 11.8% | -0.0829 |

QUALIFIED is the worst tier by a wide margin, and it's structurally the weakest signal source: those 17 signals have **zero** ELITE or LEGENDARY traders present at all (`elite_traders=0 AND legendary_traders=0` by construction of the tier label) — every qualifying trader is in the 1500–1799 `comprehensive_elo` band. LEGENDARY's 1/1 is not a usable sample, but it's the one tier gated on `geo_elo_active` (clean-pool geo ELO) rather than `comprehensive_elo`, and it's the only correct-skewed result. Directionally consistent with "lower tiers are noise," but n=1 cannot confirm it — see §5/§6.

**Important data-quality link:** ELITE and QUALIFIED gate on `comprehensive_elo`. Per the existing project finding (RQ-CONTESTED-001, [[project-comprehensive-elo-bug]], investigated in last night's O-6 session), `comprehensive_elo` is currently `base × pnl` only — the daily writer (`apply_full_elo_modifiers.py`) overwrites the behavioral dimension every day after Sunday's full recalc. This is intentional/known (pending the O-7 redesign), not a new bug. So 39/40 of these signals (everything but the single LEGENDARY one) are gated by a column that is, right now, a P&L-momentum proxy rather than the "6-dimensional ELO" the strategy's premise assumes. STR-003 deliberately avoids this column (uses `geo_elo` instead) — see §5.

**This makes STR-002 a live downstream consumer of the O-7 gap, not just an abstract data-quality concern.** O-6/O-7 (`brain/decisions/2026-06-29-overhang-ledger.md`) were scoped as an internal data-integrity problem with no named external cost. STR-002's tier-gating is concrete evidence of one: a real strategy's trader-quality filter is degraded today because `comprehensive_elo` doesn't carry behavioral skill. This doesn't change O-7's priority ranking on its own (O-7 is already gated behind O-5/O-6 for other reasons), but it adds a second motivating example beyond the design-conflict diagnostic itself. Cross-referenced in the ledger under O-7.

---

## 3. Edge decomposition — it's a calibration metric, and the divergence-magnitude gate is inverted

Since `edge_at_entry` can't separate "late" from "wrong" (§1), the decomposition that *is* possible and informative is by `gap_pt_at_registration` — the divergence magnitude that gates whether a signal fires at all (current threshold: ≥15pt, no upper bound):

| Gap bucket | n | Correct | Accuracy |
|---|---|---|---|
| 15–30pt | 5 | 3 | 60.0% |
| 30–60pt | 11 | 6 | 54.5% |
| 60–90pt | 13 | 0 | **0.0%** |
| 90–100pt | 11 | 0 | **0.0%** |

**Collapsed: gap < 60pt → 9/16 correct = 56.2%. Gap ≥ 60pt → 0/24 correct = 0.0%.** Every single correct call in the dataset has a divergence under 60pt; every signal with a divergence of 60pt or more — 24 of the 40, 60% of the sample — was wrong, with no exceptions.

This is the opposite of the strategy's implicit assumption (bigger divergence = stronger conviction = more reliable). The mechanism is visible in the `regime` field (computed in `scripts/enrich_str002_metadata.py`: NEAR_RESOLVED = market price ≤0.10 or ≥0.90): 31 of 40 signals (77.5%) fire in NEAR_RESOLVED markets — i.e., the market was *already* near-certain when the divergence was flagged. With only a handful of qualifying traders (`MIN_TRADERS=3` is the only floor, and it's on total qualified count, not per-tier), share-weighting concentrates hard toward 0% or 100% whenever the pool is thin — a single trader's position on a longshot mechanically produces a "100% smart money, 90+pt gap" reading that is a sample-size artifact, not conviction. Confirms directly: signals where `smart_money_pct_at_registration` is exactly 0.0 or 1.0 (unanimous-from-a-thin-pool) score 1/13 = 7.7%; signals with a genuine split score 8/27 = 29.6%.

**Finding A (mechanism, not just correlation):** the strategy is documented as "ELO-weighted" but the code (`_compute_signal` in `pre_resolution_intelligence.py`) weights by `entry_shares`, not by ELO at all. Tier is set by whether *any* trader clears the ELO bar; direction/magnitude is set by raw capital, regardless of who holds it. A QUALIFIED-only signal's "smart money %" can be dominated by a trader barely above 1500 `comprehensive_elo` (a corrupted column per §2) with a large position, with no LEGENDARY or ELITE trader anywhere near the market. This compounds with the gap-magnitude effect: QUALIFIED-only signals with gap ≥60pt are 0/13; QUALIFIED-only with gap <60pt are 2/4 (50%, tiny n but directionally consistent with the rest of the pattern).

---

## 4. Sample quality — small, and ~half of it is two correlated events

**Confidence interval (Wilson, 95%):** 9/40 = 22.5%, CI **[12.3%, 37.5%]**. The upper bound sits well below the 60% gate — this is *not* noise around a true rate that could plausibly be 60%+. The overall verdict ("doesn't currently pass") is not a small-sample artifact.

**But the 40 signals are not 40 independent tests.** `event_cluster` grouping (already built into the pipeline specifically to deflate n for correlated signals — see `enrich_str002_metadata.py` docstring) shows:

| Cluster | n | Correct | Accuracy |
|---|---|---|---|
| colombia_2026 | 13 | 2 | 15.4% |
| fed_june_2026 | 7 | 4 | 57.1% |
| (standalone) | 5 | 0 | 0.0% |
| maine_governor_2026 | 4 | 0 | 0.0% |
| iran_us_peace_2026 | 3 | 2 | 66.7% |
| israel/iran airspace, hormuz | 6 | 0 | 0.0% |
| lebanon_ceasefire / sc_governor | 2 | 1 | 50.0% |

**colombia_2026 alone is 13/40 — 32.5% of the entire sample — and it's a single multi-candidate presidential election**, where STR-002 fired a separate "Will X win" signal for ~11 different candidates. By construction, only one candidate wins; betting YES on any individual candidate in a crowded field is structurally biased toward NO regardless of any genuine signal quality. 11 of the 13 colombia signals are YES at `market_price_at_registration` of 0.001–0.11 (the market already pricing these candidates as near-zero chance) — mechanically close to guaranteed losses. fed_june_2026 has the same structure (7 mutually-exclusive sub-questions about one Fed decision) but performs much better (57.1%), because a rate decision has only a few plausible outcomes, not eleven.

Effective independent-event count is closer to 10 than 40. This matters directly for §5's verdict: the failure is concentrated in identifiable, structurally-explicable subsets, not spread evenly across genuinely independent draws.

---

## 5. The correlation, and the comparison to STR-003

**Direction asymmetry** is the largest single split in the data:

| Direction | n | Correct | Accuracy | Wilson 95% CI |
|---|---|---|---|---|
| YES | 29 | 3 | 10.3% | [3.6%, 26.4%] |
| NO | 11 | 6 | 54.5% | [28.0%, 78.7%] |

NO's CI actually reaches up to 78.7% — its performance is not statistically distinguishable from a passing rate at this n. YES's CI tops out at 26.4% — unambiguously bad. This lines up with §4: the colombia cluster (11 of 13 signals YES, on longshot candidates) and the standalone/maine clusters (all-YES, all-wrong) are doing most of the damage, and YES-in-a-crowded-multi-candidate-field is a structural trap independent of whether "smart money diverging from price predicts outcomes" is true in general.

**The cell that would actually test the premise is starved.** `enrich_str002_metadata.py` already names and tracks this: `has_proven_trader=1 AND regime='CONTESTED'` (a proven ELITE/LEGENDARY trader, on a market that isn't already near-certain) — its own comment calls this "the gap the redesign targets." As of today: **n=2** (50%, STR002-0008 wrong / STR002-0026 right). Far too small to conclude anything. The bulk of the 40 — 31/40 (77.5%) — are in NEAR_RESOLVED regime, the band where §3 showed the divergence signal degrades into thin-sample noise.

**STR-003 comparison.** STR-003 (~40%, 2/5, tracking toward its 60% gate per session context) tests a closely related thesis — single-trader directional conviction predicts outcome — but with filters that map almost exactly onto the contamination sources found above:

| | STR-002 | STR-003 |
|---|---|---|
| Trader quality gate | `comprehensive_elo` (ELITE/QUALIFIED — 39/40 signals) | `geo_elo >= 2175` (geo-specific, not the corrupted comprehensive column) |
| Weighting | Share-weighted aggregate across all qualifying traders | Single trader, ≥95% of their own capital on one side |
| LP/market-maker exclusion | None — mixed-position traders count toward the tally | `geo_directionality_score >= 0.7` excludes LPs holding both sides |
| P&L floor | None | `realized_pnl > 500` (excludes $0 LP-redemption artifacts and large-loss spread-compression accounts) |
| Price-band filter | None — fires most in NEAR_RESOLVED (≤0.10 / ≥0.90), 77.5% of signals | Anti-arb filter: entry price strictly between 0.10 and 0.80 |
| Portfolio cap | None | Max 5 concurrent geo/elections positions |

STR-003 excludes, by design, almost precisely the conditions under which STR-002 is empirically failing (extreme/near-certain prices, comprehensive_elo-gated low-quality tiers, non-directional/LP capital diluting the signal). If the underlying premise — smart-money divergence carries information — were false, STR-003 should be failing too, on the same trader pool and similar markets. It isn't (yet, on small n itself, but it's tracking toward the gate, not away from it). **That's evidence against the premise being structurally dead. It is not evidence the premise is confirmed** — STR-003 hasn't passed its own gate yet either, and the cell within STR-002 that would directly test the premise is too small to read (see Verdict).

---

## Verdict: (b) SIGNAL-QUALITY / FILTERING PROBLEM — NOT FALSIFIED, NOT YET VALIDATED, not pure noise

**What this analysis rules out:** the premise being dead. Evidence for **not (a) premise flaw**: STR-003 tests a structurally similar thesis on overlapping data and is tracking toward its gate, not failing it. STR-002's own failures concentrate in mechanically-explicable buckets (gap ≥60pt, NEAR_RESOLVED regime, comprehensive_elo-gated tiers, YES-in-crowded-field) rather than being spread evenly — if the premise itself were wrong, there'd be no reason for failure to cluster this cleanly on identifiable attributes.

Evidence for **not (c) pure noise**: the overall 95% CI [12.3%, 37.5%] sits entirely below the 60% gate, so "currently passing, this is just bad luck" is not supported. More importantly, the patterns aren't just statistical — they're mechanistic and independently corroborated by source code: (1) weighting is share-based not ELO-based despite the documented premise (Finding A, §3); (2) two of three tiers are gated on a column independently known to be temporarily corrupted (RQ-CONTESTED-001, §2, see also O-7 cross-ref above); (3) the pipeline's own enrichment script already flagged the thesis-relevant cell as starved before this analysis (§5).

**What this analysis does NOT establish — and this is the important limit:** that STR-002 has positive edge in the regime that matters. The clean test of the premise is `has_proven_trader=1 AND regime='CONTESTED'` — a real ELITE/LEGENDARY trader, on a market that isn't already near-certain. That cell is **n=2** (1 right, 1 wrong). Two data points cannot confirm an edge exists; they also can't rule one out. The 56.2% (9/16) gap<60pt figure is encouraging but is drawn from the same contaminated, NEAR_RESOLVED-heavy, comprehensive_elo-gated pool described above — it is a hypothesis generated by this batch, not a result independently confirmed by it (see §6: this must not be retrofit-validated on the same 40).

So: **failures are explained by contamination and regime artifacts, not by the core thesis being wrong (not falsified) — but the strategy has not yet demonstrated a positive edge in a clean, uncontaminated setting (not validated).** Both halves of that statement need to survive into any summary of this doc; reporting only the encouraging half would overclaim.

**Caveat — this is a hypothesis to test going forward, not a proven fix.** Every sub-bucket above (n=5, n=16, n=2) is small; none of these splits are independently powered to clear 60% with confidence. The recommendation in §6 is "narrow the filter and test out-of-sample," not "STR-002 is secretly fine."

---

## 6. Recommendations — a pre-registered hypothesis for a FORWARD test, not a retrofit

**These 7 items are derived from the 40-signal batch analyzed above. That batch is the training set that generated the hypothesis — it cannot also be the validation set.** Applying these filters retroactively to the existing 40 and reporting the resulting accuracy (e.g. the 56.2% gap<60pt figure) would be overfitting: the threshold was chosen *because* it maximized accuracy on this exact data. None of the numbers in §3–§5 should be read as "STR-002 v2 already passes" — they're the basis for a pre-registration, and the actual test is on signals STR-002 hasn't seen yet.

**Proposed STR-002 v2 pre-registration** (for whoever owns the promotion decision — not actioned here, no code changed):
1. **Cap the divergence gate** at `15 <= gap < 60` (currently open-ended above 15pt).
2. **Fix the ELO-weighted vs share-weighted mismatch (Finding A).** Either make the code match the documented premise (weight by trader ELO) or correct the registry description to "capital-weighted," and separately require a *minimum* proven-trader presence rather than letting QUALIFIED-only signals fire at all.
3. **Stop gating ELITE/QUALIFIED on `comprehensive_elo` until O-7 lands** (or switch to `geo_elo`/`geo_elo_active` for geo/elections markets, matching STR-003's approach) — currently rewarding P&L momentum, not the 6-dimensional skill the tier system implies. See O-7 cross-reference above.
4. **Suppress or down-weight NEAR_RESOLVED-regime signals** (price ≤0.10 or ≥0.90 at registration).
5. **De-duplicate correlated multi-candidate events** before scoring accuracy (event_cluster already exists for this — just isn't applied to the headline accuracy number yet).
6. **Add a price-movement / time-decay metric** akin to STR-003's "price movement > 2pp in correct direction" — `edge_at_entry` alone cannot separate late-firing signals from wrong directional calls.
7. **Keep accumulating the thesis cell** (proven trader + CONTESTED regime) specifically — it's the actual test of the premise and currently has n=2.

**Validation protocol:** pre-register items 1–6 as the v2 filter set *before* the next batch of signals is generated, then score only NEW signals (post-pre-registration first-seen date) against it. The 60% gate must be cleared on out-of-sample data. Do not re-score the existing 40 under the new filter and call it a pass — that number would be circular by construction.

This does not recommend killing STR-002. It recommends pre-registering a narrower v2 spec and measuring it forward, not backfitting the existing batch.
