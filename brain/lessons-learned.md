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

---

## System Architecture Lessons
*(what we learned about how the system itself works)*

- Pre-registration protocol prevents compute waste on
  weak hypotheses. Established during build phase.
- Immune system must verify outputs independently —
  agents will confidently report completion on empty files.
- Feedback.json must be read before every task or agents
  repeat identical failures indefinitely.

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
