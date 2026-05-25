# Pre-Registration: RQ-GEO-ELO-001
## Geopolitics-Conditioned ELO for Geopolitics Market Prediction

**Status:** PENDING_APPROVAL  
**Registered:** 2026-05-25  
**Registered by:** quant-research-agent  
**Assigned ID:** RQ-GEO-ELO-001  
**Depends on:** findings.json entries 2026-05-25-ELO-LEGENDARY-001, 2026-05-25-ELO-ELITE-001, 2026-05-25-ELO-QUALIFIED-001  
**Context document:** brain/agent-outputs/elo-accuracy-gap-context-2026-05-25.md  

---

## Motivation

As of Run #8 (2026-05-25), feedback-loop-agent measured the following accuracy across all non-sports markets:

| Tier | Accuracy | n | Confidence | Direction |
|------|----------|---|------------|-----------|
| LEGENDARY (ELO > 2175) | 46% | 80 | HIGH | **below baseline** |
| ELITE (ELO > 1800) | 49% | 96 | HIGH | **below baseline** |
| QUALIFIED (ELO ≥ 1200) | 65% | 152 | HIGH | above baseline |

This is the first time all three tiers have been measured simultaneously with HIGH confidence. Both LEGENDARY and ELITE are now sub-baseline — following LEGENDARY consensus would generate negative alpha.

The hypothesised root cause, documented in two prior session handovers (2026-05-19, 2026-05-20) and supported by the Nechepurenko paper (arXiv:2605.02287), is **category pollution**: `comprehensive_elo` accumulates trader scores across all Polymarket categories including sports and crypto, where different skill sets and bot patterns dominate. A trader who is highly skilled at crypto spread-capture or sports arbitrage may have a high platform-wide ELO but zero predictive edge in geopolitics markets.

Evidence supporting the category-pollution explanation:
- QUALIFIED geopolitics-only accuracy: **92.3%** (n=13, 2026-05-07) — far above the pooled 65%
- QUALIFIED elections accuracy: **46.7%** (n=15) — below baseline in the same run
- Intra-category spread of 45pp within a single tier rules out random noise as an explanation
- The LEGENDARY/ELITE tier inversion is structurally consistent with high-ELO traders who achieved their scores via sports/crypto dominating the leaderboard without geopolitics expertise

No pre-registration or experiment has previously addressed this at the ELO construction level. Prior mitigations have been output-layer fixes (category weighting in signals). This pre-registration proposes a structural fix to the ELO score itself.

---

## Hypothesis

**H1 (primary):** A geopolitics-conditioned ELO score (`geo_elo`) — computed using only resolved trades in the Geopolitics and Elections categories — will show higher predictive accuracy for geopolitics market outcomes than platform-wide `comprehensive_elo` at the LEGENDARY tier (≥ 60% vs current 46%).

**H2 (secondary):** The tier inversion (LEGENDARY < QUALIFIED) will be resolved or substantially reduced under `geo_elo` — i.e., higher `geo_elo` tier will correspond to higher accuracy within geopolitics markets.

**Null hypothesis:** `geo_elo` LEGENDARY accuracy < 55% across 50+ geopolitics markets. Category-conditioned ELO does not materially improve over platform-wide ELO for geopolitics signal generation.

---

## Expected Outcome

| Tier | Current `comprehensive_elo` accuracy | Expected `geo_elo` accuracy |
|------|--------------------------------------|----------------------------|
| LEGENDARY | 46% (n=80) | **≥ 60%** (closing gap with QUALIFIED) |
| ELITE | 49% (n=96) | ≥ 55% (at or above baseline) |
| QUALIFIED | 65% (n=152) | Stable or improved (baseline comparison) |

The 60% threshold for LEGENDARY `geo_elo` accuracy is the Phase 5 gate criterion and the minimum for a tradeable signal. Achieving this would unblock STR-003 from using a category-conditioned qualifier instead of the platform-wide ELO, resolving the structural contamination problem.

---

## Data Available

Sourced from `polymarket_tracker.db` as of 2026-05-25:

| Dataset | Count | Notes |
|---------|-------|-------|
| Traders with at least 1 geopolitics trade | 5,520 | Unfiltered; `research_excluded` not yet applied |
| Geopolitics trades (resolved) | 898,411 | Category = 'Geopolitics', `m.resolved = 1` |
| Elections trades (resolved) | 113,929 | Category = 'Elections', `m.resolved = 1` |
| Clean research pool | Read live from `integration-health.json` | Never hardcode |

Trades are categorised via `markets.category`. Both Geopolitics and Elections are included because: (1) elections markets require geopolitical reasoning; (2) the Elections category already shows signal (46.7% QUALIFIED accuracy is sub-baseline in a predictable direction, suggesting non-random noise worth correcting for rather than excluding).

---

## Method

### Phase 1 — Compute `geo_elo` (estimated: ~2 hours)

Recalculate ELO scores using **only** resolved trades in markets where `m.category IN ('Geopolitics', 'Elections')`.

Apply standard ELO formula (same K-factor and modifier structure as `recalculate_comprehensive_elo.py`) but restricted to this category subset.

Store result as new column `geo_elo` in the `traders` table. Do not modify or overwrite `comprehensive_elo` — both columns must coexist for comparison.

**Query filters for geo_elo input data:**
```sql
JOIN markets m ON m.market_id = t.market_id   -- NOT condition_id (see integration-contract.md v1.3)
WHERE m.category IN ('Geopolitics', 'Elections')
  AND m.resolved = 1
  AND m.winning_outcome NOT IN ('unknown', '')
  AND m.winning_outcome IS NOT NULL
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  AND t.timestamp <= datetime('now')
```

**Tier thresholds for `geo_elo`:** Use the same numerical thresholds as `comprehensive_elo` (Legendary > 2175, Elite > 1800, Qualified ≥ 1200) unless Phase 1 analysis shows the score distribution is materially different, in which case document any adjustment.

### Phase 2 — Re-run Accuracy Check Using `geo_elo` (estimated: ~1 hour)

Re-run the feedback-loop accuracy check substituting `geo_elo` for `comprehensive_elo` in tier assignment. Restrict accuracy evaluation to **geopolitics markets only** (`m.category IN ('Geopolitics', 'Elections')`).

For each tier (LEGENDARY, ELITE, QUALIFIED under `geo_elo`):
- Count resolved markets where the `geo_elo`-tiered consensus predicted the correct outcome
- Record n, accuracy, and confidence level (HIGH ≥ 20, MEDIUM 10–19, LOW < 10)
- Compare directly against the Run #8 `comprehensive_elo` baseline (46% / 49% / 65%)

Apply all mandatory research filters from `integration-contract.md` Section 2:
```sql
AND tr.research_excluded = 0
AND t.timestamp <= datetime('now')
AND m.resolved = 1
AND m.winning_outcome NOT IN ('unknown', '')
AND m.winning_outcome IS NOT NULL
AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
```

### Phase 3 — Decision and STR-003 Update (conditional)

**If `geo_elo` LEGENDARY accuracy ≥ 60% across ≥ 50 geopolitics markets:**
- Propose to Oscar: update STR-003 to use `geo_elo` as the qualification criterion instead of `comprehensive_elo`
- Write finding to `findings.json` with `finding_type: "elo_validity"`, `confidence: HIGH`
- Update `brain/strategy-notes/` with a `rq-geo-elo-001-result.md` report
- Write `hypothesis_confirmed` signal to `signals.json`

**If `geo_elo` LEGENDARY accuracy ≥ 55% but < 60%:**
- Document as partial improvement. Do not update STR-003.
- Pre-register a follow-up investigation: does adding additional category-specific features (e.g. recency weighting, market volume weighting) push accuracy above 60%?
- Write `hypothesis_partial` signal to `signals.json`

**If `geo_elo` LEGENDARY accuracy < 55% across ≥ 50 markets (failure condition):**
- Null hypothesis not rejected. Platform-wide ELO contamination is not the primary driver of LEGENDARY tier underperformance.
- Document alternative hypotheses: LP structure, copy trader dilution, sparse geo history per trader.
- Write `hypothesis_failed` signal to `signals.json`
- Do not update STR-003 or any strategy configuration.

---

## Failure Conditions

**Null hypothesis confirmed (stop criterion):**  
`geo_elo` LEGENDARY accuracy < 55% across ≥ 50 geopolitics markets.

**Insufficient data flag:**  
Fewer than 50 geopolitics markets with at least 3 `geo_elo` LEGENDARY traders in clean pool. If this occurs, reduce minimum threshold to 20 markets with HIGH confidence, but note limitation explicitly.

**Data integrity failure:**  
`geo_elo` column write fails or produces fewer than 1,000 non-null values (category data too sparse for meaningful ELO). Abort and write `contract_violation` signal.

---

## Schema and Query Notes

**Critical JOIN key (integration-contract.md v1.3, 2026-05-20):**  
```sql
-- CORRECT (99.999% match, 3,541,160/3,541,160 trades):
JOIN markets m ON m.market_id = t.market_id

-- WRONG (63% match, silently drops 37% of trades):
-- JOIN markets m ON m.condition_id = t.market_id
```
`condition_id` is a Polymarket external API identifier, NOT a join key to the trades table.

**Research pool — always read live:**
```sql
SELECT COUNT(*) FROM traders WHERE research_excluded = 0
```
Never hardcode. Pool size is updated daily at 06:00 UTC by `update_research_exclusions.py`.

**New column to be added (Phase 1):**
```sql
ALTER TABLE traders ADD COLUMN geo_elo REAL DEFAULT NULL;
```
Null means the trader has no resolved trades in Geopolitics or Elections categories — they are excluded from geo_elo tier assignment, not assigned to QUALIFIED by default.

**Startup validation (run before any queries):**
```sql
SELECT
  (SELECT COUNT(*) FROM traders WHERE research_excluded = 0) AS clean_pool,
  (SELECT COUNT(*) FROM markets WHERE resolved = 1
     AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)) AS clean_markets,
  (SELECT journal_mode FROM pragma_journal_mode()) AS wal_mode;
```
Alert if `clean_pool` < 440, `clean_markets` < 11,000, or `wal_mode` ≠ 'wal'.

---

## Estimated Compute

| Phase | Operation | Estimated Duration |
|-------|-----------|-------------------|
| Phase 1 | ELO recalculation over 898,411 + 113,929 = 1,012,340 filtered trades | ~2 hours |
| Phase 2 | Accuracy re-run on geopolitics markets with new tier assignments | ~1 hour |
| Phase 3 | Results documentation and conditional STR-003 update proposal | ~30 minutes |
| **Total** | | **~3.5 hours** |

---

## Relationship to Existing Research Questions

| Existing RQ | Relationship |
|-------------|-------------|
| RQ1.1 — ELO Persistence | This is a prerequisite quality fix; geo_elo should be used in the June 2026 RQ1.1 rerun if it passes Phase 2 |
| RQ3.1 — Category Calibration | RQ-GEO-ELO-001 is a structural intervention motivated by RQ3.1's category findings; complete this before RQ3.1 |
| RQ3.2 — Crowd vs Elite Divergence | June 2026 RQ3.2 rerun should use geo_elo if this passes |
| STR-003 — Single Legendary Directional | Primary beneficiary of geo_elo if hypothesis confirmed |

---

## Pre-Registration Attestation

This hypothesis was registered **before** any geo_elo calculation has been run. The expected direction (≥ 60% LEGENDARY accuracy) is based on the inferred mechanism (category pollution), not on observed geo_elo data. No geo_elo column exists in the database at time of registration.

Running any geo_elo calculation before Oscar approves this pre-registration would violate the pre-registration requirement in `brain/priorities.md` and invalidate any finding as potential data snooping.

**Awaiting:** Oscar approval via `brain/signals.json` or direct instruction before Phase 1 begins.
