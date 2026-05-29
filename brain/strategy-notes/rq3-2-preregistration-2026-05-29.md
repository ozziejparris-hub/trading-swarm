# RQ3.2 Pre-Registration — Geo ELO LEGENDARY Consensus Accuracy

**Pre-registered:** 2026-05-29
**Author:** Oscar (ozziejparris@gmail.com)
**Status:** PRE-REGISTERED — no data collection has begun

---

## Research Question

**RQ3.2:** Does geo_elo LEGENDARY tier accuracy (currently 67% in-sample) persist
out-of-sample when measured on consensus signals?

---

## Hypothesis

Geo_elo LEGENDARY traders in consensus (3+ traders, same direction) achieve >60%
accuracy on resolved geopolitics markets.

Rationale: The 67% in-sample LEGENDARY accuracy (GEO-ELO-001, 2026-05-25) may
reflect real skill or may be driven by a small number of traders on a small number
of markets. Consensus signals (3+ LEGENDARY traders agreeing) provide a stronger
signal than single-trader signals by filtering out individual variance. If the
wisdom-of-crowd effect holds within the LEGENDARY tier, consensus should sustain
or exceed the 67% in-sample baseline.

---

## Method

### Phase 1 — Consensus signal collection
Collect all consensus signals where:
- 3 or more geo_elo LEGENDARY traders (geo_elo >= 2175,
  geo_directionality_score >= 0.7) agree on the same outcome direction
- Geopolitics or Elections markets only
- No bidirectional holders (geo_directionality_score >= 0.7 already filters most)
- Market not yet resolved at signal generation time (prospective signals only)

### Phase 2 — Outcome scoring
Score each signal against the resolved market outcome:
- outcome_correct = 1 if signal direction == winning_outcome
- Use score_str003_signals.py protocol for consistent scoring
- Record resolved_at, trader geo_elo values at signal time

### Phase 3 — Accuracy comparison
Compare consensus signal accuracy against:
- Solo LEGENDARY trader signals (STR-003 baseline: 67% in-sample)
- Random baseline (50%)
- Market price at signal time (informed baseline)

---

## Failure Condition

Accuracy < 55% across 20+ resolved consensus signals.

If the failure condition triggers:
1. Do not advance STR-003 to PENDING_VALIDATION based on geo_elo LEGENDARY tier
2. Investigate whether tier thresholds need adjustment
3. Report to Oscar before any strategy status change

---

## Data Dependency

Requires 20+ resolved consensus signals from geo_elo LEGENDARY traders.

**Estimated accumulation timeline:** July–September 2026.
Rationale: As of 2026-05-29, the 46 geo_elo LEGENDARY traders are predominantly
Haley-2027 specialists with zero active 2026 market positions. The 62 newly
promoted traders (resolution sweep 2026-05-28) need time to accumulate geo trades
and reach LEGENDARY tier. Consensus signals (3+ LEGENDARY agreeing) will be rare
until the pool grows.

---

## Pre-Registration Attestation

As of 2026-05-29:
- No consensus signals from geo_elo LEGENDARY traders exist yet in signals.json
- No LEGENDARY trader geo positions in active 2026 geopolitics markets (all 21
  verified LEGENDARY traders stopped trading 2025-12-31 per swarm assessment)
- This pre-registration is made before any outcome data is available
- The 67% in-sample accuracy figure (GEO-ELO-001) is the only prior evidence

**This hypothesis has NOT been validated in-sample. The 67% figure is in-sample
accuracy across all LEGENDARY geo trades, not consensus signals specifically.**

---

## Related Work

- GEO-ELO-001: geo_elo calculation (2026-05-25) — established 67% LEGENDARY accuracy
- GEO-ELO-003: OOS validation (2026-05-26) — INCONCLUSIVE (2 traders, 1 market)
- STR-003: Single LEGENDARY directional signal — current EXPERIMENTAL strategy
- RQ3.2 builds on STR-003 by requiring 3+ LEGENDARY consensus (stronger filter)

---

## Approval Required

Oscar must approve before Phase 1 data collection begins.
Signal collection infrastructure: score_str003_signals.py + signals.json.
