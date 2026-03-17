# System Lessons Learned
Updated weekly by training-librarian-agent.
This document grows more valuable every week.

---

## Principles Established
*(things the system knows to be true based on evidence)*

- None yet — system not yet in production.

---

## Strategy Insights
*(what worked, what failed, and why)*

- None yet — awaiting first validated strategies.

---

## Calibration Findings
*(measured accuracy of ELO predictions by tier and category)*

- None yet — awaiting Phase 1 Brier score calibration.

- 2026-03-16: Baseline Brier scores established.
  897 traders have calibration data. Range: 0.08-0.89.
  388 traders excellent (< 0.10) — superforecaster
  territory per Tetlock. 489 good (0.10-0.20).
  This is the Phase 1 baseline for quant-research-agent
  to improve upon.

---

## System Architecture Lessons
*(what we learned about how the system itself works)*

- Pre-registration protocol prevents compute waste on
  weak hypotheses. Established during build phase.
- Immune system must verify outputs independently —
  agents will confidently report completion on empty files.
- Feedback.json must be read before every task or agents
  repeat identical failures indefinitely.

- 2026-03-16: Behavioral scores (kelly_alignment_score,
  patience_score, timing_score) were silently failing
  due to Windows encoding bug (non-ASCII market titles
  crashing CSV write without utf-8 flag). Always specify
  encoding='utf-8' on all file writes. Fix: line 915
  of trading_behavior_analysis.py.

- 2026-03-16: Correlation matrix was computing 84M pairs
  daily and freezing the observer. Fixed with 7-day TTL
  cache + trader cap (flagged traders with local trade
  rows only = 2,396 traders, 2.87M pairs). 96.6%
  reduction in compute.

- 2026-03-16: composite_skill_score.py could not be
  called per-trader at scale (13K traders) because
  UnifiedELOSystem.__init__ triggers expensive loaders.
  Fixed by bulk SQL approach reading directly from DB
  instead of instantiating the full ELO stack.

- 2026-03-16: CalibrationAnalyzer had two attribute
  bugs (num_predictions vs total_predictions,
  avg_actual_prob vs actual_win_rate) that silently
  returned empty results. Always test analysis scripts
  with explicit output checks before integrating.

---

## What We Tried That Did Not Work
*(permanent record — never delete entries)*

- None yet from production. See /brain/failed-experiments/

---

## Open Questions
*(things the system does not yet know but needs to)*

- What is the actual Brier score of ELO-based predictions
  across resolved markets? (Phase 1 research target)
- Which ELO tier is best calibrated by market category?
- Do legendary traders show measurable entry timing advantage?
- What is the half-life of mean reversion in prediction
  market prices early in a market's lifetime?

- Does low-trade-count high-ELO (e.g. ELO 3500, 4 trades)
  predict outcomes better than high-trade-count moderate-ELO
  (e.g. ELO 3347, 2273 trades, $9.7M profit)?
  Test in RQ1.1 — stratify by trade count.
  (Observed: 0xb442 vs 0xbf79, March 16 2026)
