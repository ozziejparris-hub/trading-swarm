# Prediction Arena: AI Models Trading Live on Polymarket and Kalshi

## Source
https://arxiv.org/abs/2604.07355

## Domain
Domain 4 — Prediction Market Intelligence
Domain 2 — Quantitative Methods

## What It Is
Prediction Arena benchmarks six frontier AI models by having them autonomously trade with real capital ($10,000 each) on Kalshi and Polymarket over 57 days (Jan 12 – Mar 9 2026), making decisions every 15–45 minutes. Results: models lost -16% to -30.8% on Kalshi but averaged only -1.1% on Polymarket, with Grok-4 achieving 71.4% settlement win rate and Gemini-3.1-pro achieving +6.02% in a 3-day paper trading cohort.

## Why It Matters to This System
This is the first published empirical evidence of AI agent trading performance on Polymarket specifically — our Phase 6 target venue. The dramatic performance gap between Kalshi (-22.6% average) and Polymarket (-1.1%) validates our platform choice: Polymarket's CLOB-based microstructure appears fundamentally better suited to AI agent strategies than Kalshi's AMM design. The finding that research volume showed no correlation with trading outcomes is a direct challenge to our quant-research-agent's assumption that deeper analysis produces better signals. This warrants a design review of whether quant-research effort is being optimally allocated.

## What to Do With It
Add to reference library: create brain/reference-library/prediction-arena-live-trading-notes.md

Also note for quant-research-agent: the no-correlation-between-research-volume-and-performance finding should be included as a constraint in the pre-registration protocol — research questions must specify their expected edge mechanism, not just the research depth.

## Effort to Implement
Low (< 1 hour) — add to reference library and update quant-research-agent template note

## Urgency
This week

## Raw Notes
- 6 frontier models in Cohort 1 (live, 57 days): all net negative on Kalshi
- Cohort 2 (4 next-gen models, 3 days paper): Gemini-3.1-pro-preview +6.02% on Polymarket
- Grok-4 achieved 71.4% settlement win rate on Polymarket
- Key finding: "platform design has a profound effect on which models succeed"
- Kalshi uses AMM-based pricing; Polymarket uses CLOB order book — AI agents exploit CLOB better
- No code or data availability mentioned in the abstract
- Paper submitted April 2026; should verify full results table when full text accessible
- Implication for Phase 6: avoid Kalshi for AI agent trading, prioritise Polymarket CLOB
- Implication for quant-research-agent: pre-register WHY research volume should matter, not just what to research
