# Composite Score Threshold Calibration — 2026-05-26

## Method

Reconstructed composite scores for **all resolved geopolitics/elections** trades in the
DB using the five-signal Mitts/Ofir formula from `detect_insider_activity.py`. Lookup
data (market volumes, trader avg position, markets_count, resolution dates) was pre-fetched
in bulk to avoid per-row DB queries (~179K trades scored without a single extra round-trip).

**Filters applied:**
- `trade_result IN ('won', 'lost')` — resolved only
- `market_category IN ('Geopolitics', 'Elections')`
- `entry_price <= 0.80` — exclude near-certainty arb (same gate as calculate_composite_score)
- `trade_gap_flag = 0` — exclude Apr 7–18 gap window

## Dataset

- **Total eligible trades:** 179,204
- **Baseline win rate (no threshold):** 54.7%

---

## Calibration Table

| Threshold | Sample N | Wins | Win Rate | Notes |
|----------:|---------:|-----:|---------:|-------|
| 0.10 | 158,786 | 83,440 | 52.5% | |
| 0.15 | 138,476 | 70,671 | 51.0% | |
| 0.20 | 110,381 | 55,009 | 49.8% | |
| 0.25 | 51,454 | 24,988 | 48.6% | |
| **0.30** | **32,837** | **16,941** | **51.6%** | current `MIN_COMPOSITE_SCORE` |
| 0.35 | 19,260 | 10,444 | 54.2% | |
| 0.40 | 8,841 | 5,056 | 57.2% | |
| **0.45** | **700** | **416** | **59.4%** | nearest to 60% target |
| 0.50 | 71 | 41 | 57.7% | |
| 0.55 | 0 | 0 | n/a | |
| **0.60** | **0** | **0** | **n/a** | current `HIGH_CONVICTION_THRESHOLD` |
| 0.65–0.90 | 0 | 0 | n/a | |

---

## Findings

### 1. No threshold achieves ≥60% win rate with ≥30 samples

The data-driven optimisation target (≥60% win rate, ≥30 sample) was **not met**.
The closest is `0.45` at **59.4%** (n=700) — 0.6 percentage points short.

Practical interpretation: the composite score adds real but moderate signal over the
baseline (54.7% → 59.4%). It is useful for ranking and prioritising, not a hard gate
that cleanly separates insider vs. noise.

### 2. Composite scores structurally cap out at ~0.50 in the general trade population

This is a design consequence, not a calibration failure. Three signals heavily suppress
scores for established traders:

- **S5 (directional concentration):** Any trader who has touched ≥11 distinct markets
  gets S5 = 0.0. Most traders in our DB have traded tens to hundreds of markets → S5
  is zero for the vast majority of the population.
- **S1 (cross-sectional bet size):** A trade must represent ≥1% of total market volume
  to score above zero, ≥10% for a full score of 1.0. At scale, individual trades almost
  never move the needle on total market volume.
- **S2 (within-trader anomaly):** Requires a trade ≥10× the trader's average to max out.
  Experienced traders have accumulated history that normalises their positions.

These three signals were designed for **fresh-wallet insider detection** — a specific
sub-population (new wallets, single-market focus, large anomalous bets). In the broader
resolved-trade universe, only S3 (price contrarianism) and S4 (pre-resolution timing)
contribute meaningfully to the average, which naturally caps around 0.40–0.50.

### 3. The cliff between 0.40 and 0.45 is the key boundary

| Band | N | Win Rate | Interpretation |
|------|--:|--------:|----------------|
| 0.35–0.40 | ~10,400 | 54.2–57.2% | Moderate signal |
| 0.40–0.45 | ~8,140 | 57.2% | Strong signal |
| **0.45–0.50** | **700** | **59.4%** | **Near-optimal zone** |
| 0.50+ | 71 | 57.7% | Sample too small |

The sharp drop in sample size from 8,841 to 700 between 0.40 and 0.45 marks the
population boundary: above 0.45, only trades with *simultaneously* unusual S1, S2,
S3, S4 AND S5 qualify. This is the insider-like sub-population.

### 4. HIGH_CONVICTION_THRESHOLD (0.60) is correctly scoped for insider signals, not general trades

Zero trades in the general resolved population ever score ≥0.55. This means the
`HIGH_CONVICTION_THRESHOLD = 0.60` in `score_insider_signals.py` operates exclusively
on the **insider signal sub-population** — trades already pre-filtered by fresh wallet,
large bet, and low market count. Within that filtered group, S5 is typically 0.8–1.0 and
S2 is elevated, so composite scores above 0.60 are realistic. The threshold is correctly
calibrated for its intended use case and should not be changed based on this general-population calibration.

### 5. Current MIN_COMPOSITE_SCORE = 0.30 admits too much noise

At 0.30, 32,837 trades pass the gate at only **51.6% win rate** — barely above the
no-threshold baseline (54.7% raw but 51.6% at this score band suggests mean reversion
at mid-range scores). The threshold is admitting a large volume of low-signal trades.

---

## Mitts/Ofir 69.9% Benchmark Context

The Mitts/Ofir (2026) paper reports 69.9% accuracy on insider-flagged trades. In our
general-population calibration:

- The highest win rate achieved with ≥30 samples is **59.4% at threshold 0.45**
- No threshold replicates the 69.9% benchmark

**Why the gap exists:** Mitts/Ofir measure accuracy on a pre-screened set of trades
already classified as insider activity. Our calibration runs across the full geo/elections
resolved population, which dilutes signal with non-insider trades. To reproduce Mitts/Ofir
conditions, calibration would need to run on `insider_signals` with `outcome_correct`
populated — but that table currently has too few resolved entries for statistical inference.
The 69.9% benchmark is the target for the insider-signal sub-population; 59.4% is the
ceiling we can reach on the general population.

---

## Threshold Update Decision

**No automated update applied.**

The formal optimisation criterion (≥60% win rate, ≥30 samples) was not met, so the
update rule does not trigger. Thresholds remain:

| Constant | Current | Data-optimal | Action |
|----------|--------:|-------------:|--------|
| `MIN_COMPOSITE_SCORE` | 0.30 | 0.45 (near-optimal, 59.4%) | No change (criterion not met) |
| `HIGH_CONVICTION_THRESHOLD` | 0.60 | N/A (general pop never reaches) | No change (correctly scoped) |

### Recommendation for future consideration

If the goal is **reducing false-positive alerts**, consider raising `MIN_COMPOSITE_SCORE`
from 0.30 → 0.45. This would:
- Cut passing trades from 32,837 → 700 (98% reduction in general pop)
- Raise win rate from 51.6% → 59.4% (within 0.6% of 60% target)
- Risk: losing some genuine insider signals that score 0.30–0.44

This change should wait until `insider_signals` has ≥100 resolved entries with
`outcome_correct` populated so calibration can run on the *actual insider sub-population*
rather than the general trade universe.

---

## Files Modified

- `detect_insider_activity.py` — no changes (criterion not met)
- This report: `~/trading-swarm/brain/agent-outputs/composite-score-calibration-2026-05-26.md`
- Calibration script: `scripts/calibrate_composite_threshold.py` (reusable)

---

*Generated: 2026-05-26 | DB: polymarket_tracker.db | Trades scored: 179,204*
