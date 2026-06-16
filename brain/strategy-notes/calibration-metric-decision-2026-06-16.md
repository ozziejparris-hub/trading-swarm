# Calibration Layer Metric Decision — log-likelihood, NOT Brier
**Date:** 2026-06-16
**Status:** DECIDED (applies when calibration layer is built, Phase 6)

## Decision
When the calibration layer is built (Phase 6, before any Kelly sizing), use
LOG-LIKELIHOOD as the scoring rule, NOT the Brier score.

## Rationale
Research (arXiv physics/0401046 and the Brier-score literature) establishes that
the Brier score cannot be trusted to decide which of two forecasts is better, and
systematically OVER-ENCOURAGES prediction of very small or zero probabilities.

This matters acutely for our signal distribution: most STR-002/STR-003 signals sit
on NEAR_RESOLVED markets (prices near 0.0 or 1.0). Brier would systematically mislead
us in exactly the regime where most of our signals live. The likelihood score is the
standard measure for calibrating and comparing continuous probabilistic forecasts —
the forecast that gives the highest probability for the observations is the better one.

## Implementation note (for Phase 6)
- Score calibration via mean log-likelihood: mean(log(p_assigned_to_actual_outcome))
- Avoid Brier decompositions for model selection between signal variants
- Reliability diagrams still useful for visualisation, but selection metric = log-likelihood
- Guard against log(0): clip probabilities to [epsilon, 1-epsilon] before scoring

## Source
arXiv physics/0401046 "The problem with the Brier score" — Brier over-encourages
extreme probability predictions; likelihood is the correct calibration metric.
