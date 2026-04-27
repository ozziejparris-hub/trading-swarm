# STR-001 — Elite Convergence Signal (as-defined): FAILED

**Date:** 2026-04-27  
**Tested by:** backtest-agent  
**Result:** FAIL — 56.1% accuracy (threshold: 60%)

---

## What Was Tested

STR-001 as originally defined: when 3+ legendary traders (comprehensive_elo > 2175, research_excluded = 0) enter the **same side** of a resolved market within a 14-day window, record the signal and check if the signal side matches the winning outcome.

Database: polymarket_tracker.db  
Markets tested: 3,699 (after market filter from 10,497 resolved)  
Signals found: 41 (across 23 unique markets)  
Date range: 2025-09-27 to 2025-11-30

---

## Why It Failed

### Primary cause: structural ambiguity in signal definition

The definition requires convergence (3+ traders on the same side) but does NOT require consensus (one side dominant, other side absent). In 78.3% of qualifying markets (18 of 23), legendary traders were split — enough traders qualified on BOTH Yes AND No sides within 14 days.

When the signal fires on both sides of the same market, exactly one must be wrong. These 36 paired signals contributed exactly 50% accuracy — indistinguishable from random. The signal is not measuring conviction; it is measuring market participation by legendary traders, which does not carry directional information when they disagree.

### Secondary cause: 7-30 day horizon performs below random

28 of 41 signals fell in the 7-30 day window. Accuracy: 42.9%. Worse than random. Likely explanation: in the lead-up to resolution (7-30 days out), markets become liquid enough that both Yes and No attract legendary capital, making this the period most prone to split signals.

### Market price already optimal

The market price (avg entry price as proxy for consensus) correctly predicted outcomes 100% of the time in this sample. Legendary convergence adds zero incremental predictive value over the market price under the current definition.

---

## What Does Work (Sub-Signals for STR-001b)

| Sub-signal | Accuracy | n | Notes |
|---|---|---|---|
| Unambiguous single-side convergence | 100.0% | 5 | Only one side qualifies (no split) — the real signal |
| 30-90 day time horizon | 84.6% | 13 | Markets earlier in their lifecycle before split develops |
| ELO 3000+ traders | 75.0% | 4 | Highest-tier traders, very small sample |
| Dominant-side selection on split markets | 65.2% | 23 | Post-hoc; requires pre-registered test to validate |

---

## Do Not Retry Without

1. Pre-registered STR-001b hypothesis with **exclusive convergence** filter: 3+ legendary traders on one side AND fewer than 3 on the opposite side
2. Approval from Oscar before quant-research-agent writes the hypothesis
3. A fresh backtest on the refined definition — do not modify parameters based on these results without registering the new hypothesis first

**quant-research-agent owns the pre-registration step.**  
**Oscar must approve the STR-001b hypothesis before backtest-agent retests.**

---

## Full Report

`/home/parison/trading-swarm/brain/agent-outputs/backtest-agent/STR-001-validation-2026-04-27.json`
