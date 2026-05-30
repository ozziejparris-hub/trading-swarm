# Pre-Registration: STR-003 Anti-Arb Entry Price Filter

**Pre-registration date:** 2026-05-30
**Filed by:** Oscar (ozziejparris@gmail.com)
**Status:** PRE-REGISTERED — filter NOT yet applied
**Approval required:** Oscar must approve before quant-research-agent implements

---

## Hypothesis

Restricting STR-003 qualifying trades to `entry_price BETWEEN 0.10 AND 0.80`
will improve signal accuracy by eliminating near-certainty arb trades that
inflate `geo_elo` win rates without representing genuine directional information.

---

## Evidence Basis

Identified 2026-05-29 during geo_elo LEGENDARY tier audit:

- Top qualifying LEGENDARY trader `0x63d43b` (geo_elo 3503, 94.3% win rate)
  was buying near-certainty outcomes ($0.997–$0.999) across multiple Fed chair
  candidates simultaneously.
- Near-certainty arb trades ($0.95+) contribute to geo_elo win rate but carry
  no directional information value — the outcome is already nearly certain.
- The composite insider score already enforces `entry_price <= 0.80` as a
  disqualification filter. This pre-registration brings STR-003 into alignment
  with that existing standard.
- STR-003 qualifies signals on individual trader directionality. An arb trader
  accumulating near-certainty positions at $0.997 shows 95%+ directionality
  by construction — not by conviction. The 95% directional filter was designed
  to catch LPs; it does not catch arb traders.

---

## Method

**Phase 1 — Quantify contamination**
Calculate what percentage of current geo_elo LEGENDARY trader resolved trades
fall outside the 0.10–0.80 price range. Query: resolved geopolitics trades
with entry_price < 0.10 OR entry_price > 0.80, grouped by trader.

**Phase 2 — Recalculate geo_elo with filter applied**
Rerun geo_elo calculation excluding out-of-range trades from the win/loss
record used to compute ELO. Traders whose win rate was primarily arb-driven
should see material geo_elo reduction.

**Phase 3 — Compare LEGENDARY tier accuracy with and without filter**
- Accuracy of current LEGENDARY tier (unfiltered geo_elo) on resolved markets
- Accuracy of LEGENDARY tier after filter applied to qualification criteria
- Primary metric: accuracy on resolved geopolitics markets where a LEGENDARY
  trader held >= 95% directional position at entry
- Secondary metric: LEGENDARY tier population size change (expected reduction)

**Data available:** 898,411 geopolitics trades with price data
**Estimated compute:** 1–2 hours via quant-research-agent

---

## Failure Condition

Filter is rejected if accuracy **decreases** after applying the 0.10–0.80
range. This would mean arb trades are actually predictive — unlikely but
possible if arb traders also take genuine directional positions that happen
to be at near-certainty prices because the market hasn't fully priced in
an outcome yet.

If the filter reduces the LEGENDARY pool to fewer than 5 active traders,
reconsider the upper bound (0.80) before proceeding. The goal is to remove
arb noise, not collapse the signal pool.

---

## Implementation (after quant-research-agent validation)

Two changes required:
1. `unified_elo_system.py` — add `entry_price BETWEEN 0.10 AND 0.80` filter
   to geo_elo win/loss calculation
2. `signal-agent.md` task template — add `entry_price BETWEEN 0.10 AND 0.80`
   to STR-003 signal qualification query

Neither change may be made before quant-research-agent completes Phase 1–3
above and Oscar approves the result.

---

## Pre-Registration Attestation

Filter not yet applied as of 2026-05-30. This document was written before
any analysis was run. The hypothesis and failure condition are fixed here
and may not be altered after the analysis begins.

The composite insider score's existing `entry_price <= 0.80` rule is the
prior evidence motivating this pre-registration, not any result from running
the filter on geo_elo data.

---

## Related Files

- `brain/strategy-registry.md` — STR-003 EXPERIMENTAL entry
- `brain/strategy-notes/research-directions.md` — STR-003 Enhancement section
  (anti-arb note added 2026-05-29)
- `brain/decisions/` — integration contract v1.7 (stale market exclusion,
  2026-05-29)
