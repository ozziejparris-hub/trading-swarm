# Documented Polymarket Insider Cases Show Near-Zero Pre-Event Leakage

## Source
https://arxiv.org/abs/2605.02286 — "Empirical Evaluation of Deadline-Resolved Information Leakage on Documented Polymarket Insider Cases"
Author: Maksym Nechepurenko (companion paper to 2605.00459, already in pending-review)
Published: May 5, 2026

## Domain
Domain 4 — Prediction Market Intelligence
Domain 2 — Quantitative Methods

## What It Is
Applies the ILS-dl (deadline-resolved Information Leakage Score) methodology to *documented* Polymarket insider trading cases — specifically the U.S.-Iran conflict cluster (markets including "US forces enter Iran by April 30," $269M volume, 332 wallets tracked). Key finding: in 30-minute and 2-hour pre-event windows, even for confirmed insiders, information leakage was near-zero (ILS-dl ≈ -0.331 at resolution-anchored proxy vs +0.113 at public-event timestamp). The large divergence between these two measures reveals that what appears as "leakage" is mostly post-announcement repricing, not pre-event front-running.

## Why It Matters to This System
Direct implication for RQ3.2 (elite consensus outperforms raw market price):

The study establishes that even *confirmed* Polymarket insiders do not show measurable short-window pre-event price drift. This has a counterintuitive but important consequence for the elite trader signal design:

1. **Elite divergence reflects skill, not insider access.** If even documented insiders don't show computable short-window leakage, then elite traders whose positions diverge from consensus pre-resolution are almost certainly doing so through superior information *processing* (better models, broader context, faster reaction) rather than privileged insider access. This strengthens the theoretical basis for RQ3.2 — the mechanism is legitimate skill, not illegal front-running.

2. **Leakage methodology provides a market quality filter.** Markets where ILS-dl is computable and high (leakage present) are contaminated by structural information asymmetry — the "smart money" is insider money, not skilled money. The RQ3.2 design should stratify by ILS-dl score: exclude high-leakage markets from the elite consensus analysis, which should improve signal purity.

3. **Complements the population-scale finding.** The population-scale paper (2605.00459, already in pending-review) establishes which *categories* of markets tend to have leakage. This paper validates the ILS-dl methodology against known ground-truth cases, giving the classification framework empirical credibility. Together they constitute a defensible pre-stratification step before RQ3.2.

## What to Do With It
New research direction: propose pre-stratification to quant-research-agent before RQ3.2 runs —
compute ILS-dl proxies for markets in polymarket_tracker.db using the public ForesightFlow code, then exclude high-leakage markets from the elite consensus analysis. This is a refinement to RQ3.2 pre-registration, not a new hypothesis.

Add this paper to reference library as a supplementary note within brain/reference-library/prediction-market-coordination.md (alongside the population-scale finding). The key empirical result to preserve: ILS-dl near-zero even for confirmed insiders in 30-min/2-hour windows.

## Effort to Implement
Low (< 1 hour) — add pre-stratification note to RQ3.2 hypothesis, update reference library

## Urgency
This week — RQ3.2 pre-registration is upcoming per priorities.md

## Raw Notes
- Study: 332 wallets active across Iran-cluster markets; 4 methodology components (exponential-hazard per category, ILS-dl per contract, cross-market wallet analysis, refinements)
- The +0.113 vs -0.331 ILS-dl split (0.444 gap) is the headline result: resolution-anchored proxy grossly overstates leakage; public-event timestamp is the correct anchor
- Implication: price movement before market resolution is NOT evidence of insider information — it is mostly normal price discovery responding to public events
- This validation makes it safer to treat elite trader position-taking as skill signal rather than flagging it as potential insider activity
- Companion paper 2605.02287 (per-market ILS across three detection layers) extends this methodology — sufficient for reference library note; does not warrant separate pending-review item as the implementation path is already identified in the population-scale finding
- ForesightFlow code public: https://github.com/nechepurenko/foresightflow (to verify)
