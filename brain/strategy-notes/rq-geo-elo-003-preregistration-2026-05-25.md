# Pre-Registration: RQ-GEO-ELO-003

**Date:** 2026-05-25
**Registered by:** Oscar (via trading-swarm session)
**Hypothesis ID:** RQ-GEO-ELO-003

---

## Hypothesis

geo_elo tier discrimination (67%/69.5%/73.7% for LEGENDARY/ELITE/QUALIFIED) will hold
out-of-sample when trained on pre-2026 trades and tested on 2026 trades.

---

## Method

**Phase 1** — Recalculate geo_elo using only trades with timestamp < 2026-01-01

**Phase 2** — Measure accuracy on resolved geopolitics markets from 2026-01-01 onward

**Phase 3** — Compare out-of-sample accuracy to in-sample baseline

---

## Failure Condition

Out-of-sample LEGENDARY accuracy < 55% (vs 67% in-sample)

---

## Why This Matters

In-sample validation is necessary but not sufficient. The same data was used to compute
ELO and measure accuracy. Out-of-sample confirmation is required before STR-003 uses
geo_elo for live signals.

---

## Data Available

Trades from Aug 2025 onward, ~6 months of 2026 data available for out-of-sample test.

---

## Estimated Compute

2-3 hours via quant-research-agent

---

## Pre-Registration Attestation

No out-of-sample calculation has been run yet. This pre-registration is filed before any
out-of-sample test to prevent data snooping. The in-sample baseline (67% LEGENDARY
accuracy, 2026-05-25) is the only figure known at time of registration.
