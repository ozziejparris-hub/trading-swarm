# ELO Arc Stage 0b — Behavioral Validation Study

**Date:** 2026-07-12
**Status:** COMPLETE (read-only empirical study, no writes)
**Scope:** ELO arc design doc `2026-07-06-elo-arc-design-FABLE.md` §Stage 0b — decides `W_beh`
**Bottom line: the data does not support re-incorporating `behavioral_modifier`. Recommend `W_beh = 0`.** This is a clear, well-powered result, not an underpowered non-finding — see §4 and §5.

---

## 0. Question being answered

Oscar's thesis: P&L is the best predictor of trader skill we have. Behavioral (process metrics — consistency, diversification, kelly-alignment, patience) has been a no-op in `comprehensive_elo` for 7 months (Writer C, `integrate_behavioral_elo.py`, disabled 2026-06-05, deleted entirely in Stage 0c, commit `61adaf5`). The ELO redesign re-incorporates behavioral behind a weight `W_beh`, and this study is what decides its value: `W_beh = 0.5` (clear positive signal), `0.25` (weak), or `0` (zero/negative — ship the unified architecture with behavioral off, one-constant flip preserved if better evidence ever arrives).

---

## 1. Population

**Gate:** `is_flagged = 1 AND research_excluded = 0 AND resolved_trades_count >= 10` (the thin-sample gate already established elsewhere in the ELO design).

**n = 21,249 traders.** A solid sample — see §4 for the formal power calculation.

Composition note (relevant to §4's survivorship caveat): 20,965/21,249 (98.7%) of this population has `discovery_source = 'leaderboard'` — i.e. nearly the entire study population is traders who at some point appeared on Polymarket's own leaderboard. This is the population the ELO system actually scores, so it's the right population to study, but it means the result below speaks to *leaderboard-visible* traders specifically, not to trading skill in some more general sense.

---

## 2. Outcome variable — recommendation: market-relative edge

Three candidates, per the brief:

| Candidate | What it measures | Problem |
|---|---|---|
| Resolved-trade win rate | Fraction of resolved trades that won | **Mechanically dominated by bet selection, not skill** — see below |
| Realized ROI on resolved positions | Return per dollar invested | Conflates skill with position-sizing/leverage decisions — circular if testing whether `kelly_alignment` (a *sizing* metric) predicts it |
| **Market-relative edge** | `(won ? 1 : 0) − entry_avg_price`, averaged per trader across resolved positions | None of the above — nets out what the market already knew |

**Recommendation: market-relative edge.** Rationale, empirically confirmed in this dataset, not just asserted:

`entry_avg_price` on Polymarket *is* the market-implied probability at the moment the trader bought. A trader who buys "Yes" at 0.90 and wins hasn't demonstrated skill — the market already thought that outcome was 90% likely. Edge asks the right question: did the trader's picks resolve correctly *more often than the price they paid implied they should*?

I checked whether this distinction actually matters here, and it matters enormously: **`mean_entry_price` correlates with raw win rate at r = 0.982** in this population — win rate is almost entirely explained by how much of a favorite a trader tends to buy, not by anything else. Raw win rate is close to a restatement of "did you buy favorites," not a skill measure. ROI has the reverse problem — it's correlated with `pnl_modifier` by construction (both derive from the same P&L data), making any regression of ROI on `pnl_modifier` close to tautological, and it bundles in position-sizing skill that overlaps with `kelly_alignment_score` itself.

**Computation:** for every `closed` position joined to a `resolved` market with a non-null `winning_outcome`, excluding the April 7–18 trade-gap window (`trade_gap_flag`) per standing project convention:

```sql
edge_i = (position.outcome = market.winning_outcome ? 1.0 : 0.0) − position.entry_avg_price
mean_edge(trader) = AVG(edge_i)  over trader's resolved positions
```

**Coverage:** computable for 21,218 / 21,249 traders (99.85%; 31 traders in the trades-based population gate had no qualifying closed/resolved position, likely a trades-vs-positions consolidation edge case — negligible).

**Reliability of the per-trader estimate:** median 45 resolved positions per trader (IQR 30–82), only 315/21,249 (1.5%) below 10 resolved positions despite passing the trades-based gate. `resolved_trades_count` (trades-based) and `n_resolved_positions` (positions-based) correlate at r = 0.853 — consistent, not two unrelated countable things. The outcome measure is stable for the large majority of the population; results are also checked against a `n_resolved_positions ≥ 30` (median) high-reliability subsample in §3.

Reported as robustness checks below: win rate and ROI, run through the identical model, specifically to show how differently they answer this question.

---

## 3. The test

### 3.1 Main test — does `behavioral_modifier` add anything beyond ELO + P&L?

`mean_edge ~ base_category_elo + pnl_modifier + behavioral_modifier` (all variables standardized; n = 21,218)

| | coef (SD units) | SE | t | p |
|---|---|---|---|---|
| base_category_elo | 0.0249 | 0.0062 | 4.02 | <0.001 |
| pnl_modifier | **0.4471** | 0.0062 | 72.6 | <0.001 |
| **behavioral_modifier** | **−0.0137** | 0.0062 | −2.21 | **0.027** |

R² = 0.2019. Base-only model (elo + pnl, no behavioral): R² = 0.2017. **Incremental R² from adding `behavioral_modifier`: 0.00018** — i.e., behavioral explains an additional 0.018 percentage points of variance in market-beating edge, on top of a model that already explains 20.17%.

In raw units: moving `behavioral_modifier` from its 10th to 90th percentile (a range of 0.305) while holding ELO and P&L fixed is associated with a **−0.18 percentage-point** change in edge. That's not a typo — it's negative, and it's economically nothing.

**Robustness check — does this hold in the more reliable half of the sample?** Restricting to `n_resolved_positions ≥ 30` (median, n = 16,045): `behavioral_modifier` coefficient = **+0.0067, p = 0.35**. The sign flips and the effect is no longer statistically distinguishable from zero. **The full-sample "significant" result does not replicate in the subsample with the more reliable outcome estimates** — the honest read is that the full-sample p = 0.027 is noise inflated by n, not a real (even if tiny) effect. See §4.

**Verdict on the main test: no economically meaningful signal, and the marginal statistical signal that exists doesn't survive a basic reliability check.**

### 3.2 Decomposition — is a sub-component predictive even if the composite isn't?

`behavioral_modifier` (the stored composite) = `consistency × diversification × trading_style × activity`, computed live inside `unified_elo_system.py` and never persisted as separate columns — I can't decompose *that specific* composite without re-running the underlying (expensive, non-read-only-friendly) behavioral analysis pipeline live, which is out of scope for a read-only study. What *is* separately stored on `traders` are three older, related scores — `kelly_alignment_score`, `patience_score`, `timing_score` — written by a since-archived CSV-import pipeline (`scripts/archive/update_database_from_csvs.py` is the only live `SET` for these columns anywhere in either repo). These map to "kelly-alignment" and "patience" in the brief directly; treat them as the best available decomposition.

`mean_edge ~ base_category_elo + pnl_modifier + kelly_alignment_score + patience_score + timing_score` (standardized, n = 21,218)

| | coef (SD units) | SE | t | p |
|---|---|---|---|---|
| base_category_elo | 0.0257 | 0.0062 | 4.13 | <0.001 |
| pnl_modifier | 0.4461 | 0.0062 | 72.5 | <0.001 |
| kelly_alignment_score | 0.0164 | 0.0068 | 2.42 | 0.015 |
| patience_score | −0.0035 | 0.0068 | −0.51 | 0.613 |
| **timing_score** | 0.0210 | 0.0063 | 3.34 | <0.001 |

R² = 0.2023 (vs. 0.2017 base-only — again negligible incremental contribution from the whole block).

Reading this component by component:
- **`kelly_alignment_score`**: tiny positive, marginally significant. Not nothing, but an order of magnitude too small to matter (same "large-n, trivial effect" pattern as §3.1).
- **`patience_score`**: null. No detectable relationship at all.
- **`timing_score`**: the largest of the three, and "significant" — **but this one needs a heavy caveat, not a promotion.** Per `CLAUDE.md`, timing quality is intentionally disabled system-wide (`created_at` doesn't exist on `markets`); I confirmed in the data that a large cluster of traders (1,541, ~7%) sit at exactly `0.5` — a neutral-default signature — while the rest carry values from whatever pre-disablement computation last ran. This column is a mix of stale historical signal and placeholder defaults, not a clean live measurement. I would not treat this coefficient as evidence for anything without first re-deriving `timing_score` from scratch on a repaired `created_at`-equivalent input — which is out of scope here and arguably its own separate piece of work, not part of `W_beh`.

**A finding that undercuts "behavioral" as a coherent single construct**: `kelly_alignment_score` and `patience_score` correlate with the stored `behavioral_modifier` composite at **r = −0.593 and r = −0.596** respectively — strongly *negatively*. These are supposed to be cousins under the same "process quality" umbrella, and instead they point in opposite directions from each other. That's consistent with what the code shows: they come from two different, never-cross-validated pipelines (the archived CSV-import scores vs. the live `unified_elo_system.calculate_behavioral_multiplier` composite). This is a data-quality finding independent of the skill question — even setting aside whether behavioral predicts anything, the current behavioral columns don't agree with each other.

### 3.3 Robustness — same model, other outcome variables (this is the important cautionary result)

`win_rate ~ base_category_elo + pnl_modifier + behavioral_modifier` (n = 21,218):

| | coef (SD) | p |
|---|---|---|
| base_category_elo | 0.269 | <0.001 |
| pnl_modifier | 0.114 | <0.001 |
| **behavioral_modifier** | **0.519** | **<0.001** |

R² = 0.403. Taken at face value, this looks like a *huge*, clean positive result for behavioral — five times the size of the pnl_modifier effect on this same outcome.

**This is exactly the trap flagged in the brief, and it's fully explained by the mechanical confound in §2**: `behavioral_modifier` correlates with `mean_entry_price` at **r = 0.576**, and `mean_entry_price` correlates with raw win rate at **r = 0.982**. Traders with a higher `behavioral_modifier` tend to buy bigger favorites; buying bigger favorites mechanically produces a higher win rate; none of this is skill. Against the market-neutral outcome (`mean_edge`), the raw bivariate correlation of `behavioral_modifier` is **r = 0.009** — essentially zero. If this study had used win rate as the outcome (a very natural first choice), it would have concluded the *opposite* of the truth. This is why §2's outcome choice was the most consequential decision in the study.

`mean_position_roi ~ base_category_elo + pnl_modifier + behavioral_modifier` (n = 21,218):

| | coef (SD) | p |
|---|---|---|
| base_category_elo | −0.010 | 0.079 |
| pnl_modifier | 0.564 | <0.001 |
| **behavioral_modifier** | **0.027** | **<0.001** |

Small but real-looking, unlike win rate. Plausible explanation: `behavioral_modifier` folds in position-sizing/activity components that mechanically correlate with realized ROI patterns (larger, more confident bets sized differently) rather than with pure predictive accuracy. This is a secondary, much smaller finding (β = 0.027 vs. β = 0.564 for pnl_modifier — a 20x gap) and doesn't overturn the primary edge-based null; it's reported for completeness since ROI was one of the brief's candidate outcomes.

---

## 4. Honest checks

**Sample size / power — this is NOT an underpowered study.** With n = 21,218 and this study's covariate structure, the minimum detectable partial correlation at α = .05 is **|r| ≈ 0.0135**, corresponding to an R² as small as **0.00018**. That is a genuinely tiny bar — smaller than the incremental R² actually observed for `behavioral_modifier` (0.00018, right at the detection threshold) and comparable to the decomposition components. In plain terms: **this sample is large enough to detect even trivially small real effects**, which is exactly why a couple of coefficients cross p < .05 despite being economically meaningless. The correct reading of "no economically meaningful signal, with one borderline-significant near-zero effect that doesn't replicate" is a **clear result**, not an inconclusive one — if there were a real, moderate effect, this sample would find it easily. This is the opposite failure mode from underpowering: it's a demonstration of how much noise a small-but-"significant" coefficient can hide when n is this large.

**Is the outcome measure itself reliable?** Yes, with a small caveat. Median 45 resolved positions per trader, only 1.5% of the population below 10. The main result is unchanged in sign-and-null-ness when restricted to the more reliable `n_resolved_positions ≥ 30` half of the sample (§3.1) — if anything, restricting to higher-reliability traders makes the tiny full-sample effect disappear entirely, not strengthen.

**Confounds checked:**
- *"Good traders are good at everything" (the core confound this study exists to rule out):* addressed directly by controlling for `base_category_elo` and `pnl_modifier` in every model — `behavioral_modifier`'s near-zero coefficient is *after* netting out general trader quality, not instead of it.
- *Multicollinearity among predictors:* `base_category_elo`, `pnl_modifier`, and `behavioral_modifier` correlate weakly with each other (r = 0.08–0.14) — not a confound driving the null result via collinearity.
- *Survivorship (does behavioral correlate with how long/how much someone has traded?):* `behavioral_modifier` vs. `resolved_trades_count`: r = −0.015. vs. `total_volume`: r = −0.0004. vs. tenure (days since `first_seen`): r = 0.073. All negligible — behavioral score isn't a proxy for "has traded a long time" or "trades a lot."
- *Population survivorship (broader):* as noted in §1, 98.7% of the population is leaderboard-discovered. This study can only speak to traders who made it onto Polymarket's leaderboard at some point — it says nothing about whether behavioral metrics might matter for a differently-selected population (e.g. all traders regardless of leaderboard status). Given the ELO system only ever scores the leaderboard-flagged population in practice, this is the right population for the decision at hand, but it's a real scope limit worth stating.
- *Discretization / data quality of `behavioral_modifier` itself:* the composite has only 439 distinct values across 21,249 traders, and the single most common value covers 1,967 traders (9.3% of the population) — consistent with it being built from a handful of discrete tiered classifications (`"Very Consistent"`, `"Excellent diversification"`, etc.) multiplied together rather than a continuous measurement. This doesn't invalidate the test, but it does mean `behavioral_modifier` has a low practical ceiling on how much information it could carry even if the underlying construct were valid.

---

## 5. Recommendation

**`W_beh = 0`.**

- Primary, correctly-specified test (market-relative edge, controlling for ELO + P&L): no economically meaningful effect (incremental R² = 0.00018), a marginally-significant *negative* coefficient that **does not replicate** in a more reliable subsample (flips sign, p = 0.35).
- Decomposition: nothing clears the bar either. `kelly_alignment_score` and `patience_score` — the two components named in Oscar's thesis — are individually tiny-to-null, and are themselves *strongly negatively correlated with each other and with the composite `behavioral_modifier`* (r ≈ −0.59), meaning "behavioral" isn't even a coherent single construct in the current data.
- The one outcome that *did* show a large behavioral effect (win rate, β = 0.52) is fully explained by a mechanical confound (favorite-buying, r = 0.98 between entry price and win rate) that has nothing to do with skill — a clean demonstration of why the outcome-variable choice in §2 mattered, not evidence for behavioral.
- This is not an underpowered "we can't tell" result. n = 21,218 detects effects as small as R² = 0.00018 — this sample would have found a real signal if a real signal existed at anything above a trivial magnitude.

**Confidence: clear result, not weak or inconclusive.** Ship the unified single-writer architecture at `W_beh = 0`. The whole architectural win (single-writer, harness coverage, Cluster D resolution path) lands regardless of this result, per the design doc — Stage 0b was never a blocker for shipping, only for whether behavioral gets switched on at launch. The one-constant flip stays available if the underlying behavioral computation is ever rebuilt on cleaner inputs (live-recomputed `kelly_alignment_score`/`patience_score` instead of the currently-archived pipeline; a genuinely repaired `timing_score`) — this study doesn't rule out behavioral signal existing in principle, it rules out the *current, frozen, internally-inconsistent* behavioral columns as a basis for weighting `comprehensive_elo` today.

---

## Appendix: methodology notes

- All SQL/analysis run read-only against `data/polymarket_tracker.db` (no writes).
- OLS implemented manually via `numpy.linalg.lstsq` (statsmodels/sklearn not installed in this environment) — classical (non-robust) standard errors, t-tests, two-tailed p-values via `scipy.stats.t.sf`. Given n > 21,000 and the effect sizes discussed are near-zero either way, heteroskedasticity-robust SEs would not change any conclusion in this report (they would, if anything, tend to widen CIs further around already-null estimates).
- Population and outcome extraction script + regression script + intermediate CSV are in the session scratchpad, not committed (this is a read-only research task; the DB queries and derivation are fully reproducible from the SQL and formulas quoted inline above).
- `trade_gap_flag` markets (2026-04-07–18 monitoring outage) excluded from the outcome computation per standing project convention (`CLAUDE.md`).
