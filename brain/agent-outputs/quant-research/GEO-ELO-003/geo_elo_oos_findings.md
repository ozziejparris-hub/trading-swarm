# GEO-ELO-003 Findings — Out-of-Sample geo_elo Validation

**Generated:** 2026-05-26  
**Hypothesis:** RQ-GEO-ELO-003  
**Pre-registration:** brain/strategy-notes/rq-geo-elo-003-preregistration-2026-05-25.md  

---

## Executive Summary

The out-of-sample test FORMALLY FAILS the failure condition (LEGENDARY OOS 9.4% < 55%
threshold). However, this result is not statistically meaningful: all 64 LEGENDARY OOS
trades come from 2 traders in a single market (Russia-Ukraine ceasefire Q2 2026). 44 of
46 LEGENDARY-tier traders had zero OOS trades. The QUALIFIED tier result (58.7%, n=167,
4 markets) is more reliable and marginally below the in-sample 73.7%.

**Bottom line:** 6 OOS markets is insufficient for firm conclusions. Re-run after 20+
OOS geo markets have resolved.

---

## Phase 1 — OOS ELO Computation

**Algorithm (identical to geo_elo v2):**
```
expected_score = price        (outcome_bet = 'Yes')
expected_score = 1 - price   (outcome_bet = 'No')
elo_change     = K * (actual_score - expected_score)
K = 32 (<20 geo trades), 24 (20-50), 16 (>50)
Starting ELO = 1500, min 5 qualifying trades
```

**Training data:** 177,564 qualifying geo/elections trades with timestamp < 2026-01-01  
**Traders receiving OOS ELO:** 435 (same count as full geo_elo — pre-2026 data was sufficient)  
**Column written:** `traders.geo_elo_oos` (added; now populated for 435 Pool C traders)

**OOS ELO distribution (Pool C, geo_accuracy_pool=1):**

| Tier | Count |
|------|-------|
| LEGENDARY (≥2175) | 46 |
| ELITE (1800–2175) | 47 |
| QUALIFIED (1500–1800) | 115 |
| BELOW QUALIFIED (<1500) | 227 |

*Distribution nearly identical to in-sample geo_elo — the training cutoff at 2026-01-01
doesn't meaningfully shift tier assignments. All geo action was pre-2026.*

---

## Phase 2 — OOS Test Set

**6 resolved geo/elections markets from 2026-01-01 onward:**

| Market | Resolution | Outcome | Total Pool C Trades |
|--------|------------|---------|---------------------|
| Ukraine ceasefire before June 2025? | 2026-01-04 | Yes | 20 |
| Will Newsom win 2025 presidential election? | 2026-01-07 | No | 39 |
| Kim Jong Un invade by March 2026? | 2026-01-07 | No | 36 |
| Will Trump win 2027 presidential election? | 2026-01-08 | No | 27 |
| Will Taiwan invade Syria by Dec 2025? | 2026-01-09 | No | 142 |
| Russia x Ukraine ceasefire by Q2 2026? | 2026-05-08 | No | 360 |

**Total OOS trades in scope:** 624 (Pool C, geo_accuracy_pool=1, geo_elo_oos not null)

**Trade distribution by tier and market:**

| Tier | Market | Trades | Wins |
|------|--------|--------|------|
| LEGENDARY | Russia x Ukraine ceasefire Q2 | 64 | 6 |
| ELITE | Russia x Ukraine ceasefire Q2 | 103 | 35 |
| ELITE | Ukraine ceasefire June 2025 | 3 | 1 |
| QUALIFIED | Ukraine ceasefire June 2025 | 17 | 13 |
| QUALIFIED | Will Newsom win? | 39 | 25 |
| QUALIFIED | Will Taiwan invade Syria? | 29 | 16 |
| QUALIFIED | Russia x Ukraine ceasefire Q2 | 82 | 44 |
| BELOW | Kim Jong Un invade? | 36 | 27 |
| BELOW | Will Trump win 2027? | 27 | 16 |
| BELOW | Will Taiwan invade Syria? | 113 | 54 |
| BELOW | Russia x Ukraine ceasefire Q2 | 111 | 49 |

---

## Phase 3 — In-Sample vs Out-of-Sample Comparison

### All geo_elo_oos tiers (Pool C, geo_accuracy_pool=1)

| Tier | In-sample | OOS | Delta | n (OOS) |
|------|-----------|-----|-------|---------|
| LEGENDARY (≥2175) | 67.0% | **9.4%** | -57.6pp | 64 |
| ELITE (1800–2175) | 69.5% | **34.0%** | -35.5pp | 106 |
| QUALIFIED (1500–1800) | 73.7% | **58.7%** | -15.0pp | 167 |
| BELOW QUALIFIED | 28.8% | 50.9% | +22.1pp | 287 |
| ALL | 53.0% | 45.8% | -7.2pp | 624 |

### Directional subset (geo_directionality_score ≥ 0.7)

| Tier | OOS Accuracy | n |
|------|-------------|---|
| LEGENDARY | 9.4% | 64 |
| ELITE | N/A | 0 |
| QUALIFIED | N/A | 0 |
| ALL (dir≥0.7) | 9.4% | 64 |

*Only LEGENDARY traders in Pool C have directionality ≥ 0.7 among those with OOS trades.
ELITE/QUALIFIED traders who traded in OOS markets all have directionality < 0.7.*

### Failure condition check

**Formal verdict: FAILED** — LEGENDARY OOS 9.4% < 55% threshold.

---

## Critical Context: Why This Result Is Unreliable

### 1. Extreme sample concentration in LEGENDARY

- 46 LEGENDARY-tier traders (geo_elo_oos ≥ 2175) exist in Pool C
- **Only 2 traded in any OOS market**
- All 64 LEGENDARY OOS trades are in a single market: "Russia x Ukraine ceasefire by Q2 2026?"
- Trader A: ELO 4640, directionality 0.90 → 44 trades, 1 win (2.3%)
- Trader B: ELO 3518, directionality 0.78 → 20 trades, 5 wins (25%)

The LEGENDARY tier accuracy is not a measurement of 46 traders' predictive skill across
6 markets. It is a measurement of 2 traders' bet on whether a ceasefire would happen
before Q2 2026. This is a single binary geopolitical event.

### 2. Russia-Ukraine ceasefire dominates the test set

360 of 624 Pool C OOS trades (57.7%) are in the ceasefire market. This market also
had the most unresolved ambiguity — ceasefire negotiations were ongoing, and the market
traded at 68–74% YES probability before resolving NO. This is precisely the type of
high-uncertainty geopolitical event where even good forecasters are wrong.

### 3. January 2026 markets are an odd sample

5 of 6 OOS markets resolved in a 5-day window (Jan 4–9, 2026). Three are extreme
unlikely events ("Kim Jong Un invade Syria", "Taiwan invade Syria by Dec 2025",
"Trump win 2027 election") which resolved NO. For these, even random chance would
produce high accuracy since the naive prediction is always NO. LEGENDARY traders
didn't trade in these markets (not their focus), but BELOW QUALIFIED traders did,
producing their anomalous 50.9% OOS accuracy.

### 4. QUALIFIED is the most trustworthy OOS signal

QUALIFIED is spread across 4 markets (167 trades), not concentrated in one. Its
OOS accuracy of 58.7% (vs 73.7% in-sample) shows a real decay of ~15pp but remains
above random baseline (50%). This is the only tier with enough OOS market diversity
to draw a directional conclusion.

---

## Pre-Mortem (Required by Research Standards Rule 11)

**Top 3 ways this analysis could be wrong:**

1. **Sample concentration invalidates tier conclusions**: The LEGENDARY failure
   is driven by 2 traders in 1 market. If the ceasefire had happened (it traded
   at 70%), accuracy would flip to ~90%. This result depends on one geopolitical
   outcome, not on a representative test of tier predictive validity.

2. **In-sample baseline was measured on easier markets**: The in-sample accuracy
   (67%/69.5%/73.7%) was computed on all resolved geo markets, many of which
   may have been lower-uncertainty. The 6 OOS markets include the most contested
   geopolitical predictions of early 2026 (ceasefire, invasion scenarios). Direct
   comparison inflates the apparent OOS degradation.

3. **OOS ELO and in-sample ELO have identical training data for most traders**:
   Pre-2026 data was sufficient to assign all 435 Pool C traders to the same tier.
   The OOS test is therefore testing whether geo_elo tiers generalise to new markets,
   not whether OOS ELO scores are better calibrated than in-sample scores.

**Black swan that invalidates this result:** If Russia-Ukraine ceasefire had been
announced before Q2 2026 (nearly happened; market priced at 70%), LEGENDARY
OOS accuracy would be 90%+ and the test would show strong OOS validity. The
failure is contingent on a single historical event outcome.

---

## Implications for STR-003

STR-003 requires `geo_elo >= 2175` (LEGENDARY) as a qualifier for signals. Based
on this OOS test:

**Do not advance STR-003 to live trading on the basis of geo_elo OOS validation.**
The failure condition formally fires, but sample size (n=64 in 1 market, 2 traders)
is insufficient for a reliable conclusion.

**Recommended path:**
1. Wait for 20+ resolved geo markets post-2026-01-01
2. Re-run OOS validation when LEGENDARY tier has trades in 5+ distinct markets
3. If failure condition fails again on broader sample, suspend geo_elo as STR-003 qualifier
4. If it passes, advance STR-003 to ACTIVE with geo_elo OOS confirmation

**QUALIFIED tier (58.7% OOS, 4 markets) is a more promising signal direction** than
LEGENDARY for geopolitics. The in-sample tier hierarchy (QUALIFIED > ELITE > LEGENDARY)
may reflect market-specific concentration rather than genuine skill stratification.

---

## Data Quality

- Contract validation passed: clean_pool=12115, clean_markets=15470, wal=wal
- Mandatory filters applied throughout (research_excluded=0, trade_gap_flag, resolved, etc.)
- geo_elo_oos column written to traders table for 435 Pool C traders
- Pre-2026 training set: 177,564 qualifying geo/elections trades
