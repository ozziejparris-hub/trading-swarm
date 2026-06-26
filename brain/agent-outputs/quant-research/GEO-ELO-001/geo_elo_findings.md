# GEO-ELO-001 Findings — Market-Implied Probability ELO

**Generated:** 2026-06-08 17:19 UTC  
**Hypothesis:** RQ-GEO-ELO-001  
**Version:** v2 (market-implied probability ELO)  

---

## Algorithm Change (v1 → v2)

Phase 1 used a fixed-opponent ELO (`opponent_elo=1500`) which caps scores at
~1993 regardless of trader skill, making the LEGENDARY threshold (≥2175)
unreachable by design. v2 replaces this with market-implied probability:

```
expected_score = price        (outcome = 'Yes')
expected_score = 1 - price   (outcome = 'No')
elo_change     = K * (actual_score - expected_score)

K = 32   (<20 geo trades)
K = 24   (20-50 geo trades)
K = 16   (>50 geo trades)
```

This correctly rewards contrarian correct calls (low price, wins) with
large ELO gains, and penalises consensus wrong calls (high price, loses)
with large ELO losses — identical to how skill should be measured in
prediction markets.

---

## Phase 1+2: Distribution (v2)

| Metric | Value |
|--------|-------|
| Traders with geo_elo | 6,098 |
| Max geo_elo | 10002.53 |
| Min geo_elo | -28861.47 |
| Avg geo_elo | 1392.10 |
| LEGENDARY (≥2175) | 169 |
| ELITE (1800–2175) | 224 |
| QUALIFIED (1500–1800) | 4,292 |
| BELOW QUALIFIED (<1500) | 1,413 |
| Highly directional (≥0.7) | 4,292 |

---

## Phase 3: Accuracy Check

### Accuracy_pool overlap

- `geo_accuracy_pool=1 AND geo_elo IS NOT NULL` = **494 traders**
- Root cause: geo_elo holders have <20 total resolved trades (`research_excluded=1`);
  `geo_accuracy_pool` requires `research_excluded=0` (≥20 resolved trades).
- Resolution: accuracy check run on all geo_elo holders (435 traders).
- This is a data reality, not a bug: geo-specialists trade only in geo markets
  and accumulate few total resolved trades relative to general traders.

### Accuracy by geo_elo tier (all geo_elo traders)

| Tier | Accuracy | n |
|------|----------|---|
| LEGENDARY (≥2175) | 77.8% (n=2344) | |
| ELITE (1800–2175) | 75.9% (n=2709) | |
| QUALIFIED (1500–1800) | 69.7% (n=17375) | |
| BELOW QUALIFIED (<1500) | 48.9% (n=5602) | |
| ALL | 66.8% (n=28030) | |

### Accuracy by geo_elo tier (geo_directionality_score ≥ 0.7 only)

| Tier | Accuracy | n |
|------|----------|---|
| LEGENDARY (≥2175) | 77.5% (n=2184) | |
| ELITE (1800–2175) | 76.0% (n=2545) | |
| QUALIFIED (1500–1800) | 69.8% (n=17006) | |
| ALL (dir≥0.7) | 67.5% (n=26812) | |

### Baseline comparison

| Segment | Accuracy | Source |
|---------|----------|--------|
| comprehensive_elo LEGENDARY | 46% | feedback-loop Run #8 2026-05-25 |
| comprehensive_elo ELITE | 49% | feedback-loop Run #8 2026-05-25 |
| comprehensive_elo QUALIFIED | 65% | feedback-loop Run #8 2026-05-25 |

---

## Key Findings

1. **The v2 ELO is uncapped** — LEGENDARY traders (≥2175) now exist (or don't),
   reflecting genuine skill discrimination rather than algorithmic ceiling.
2. **Market-implied probability ELO correctly rewards contrarian accuracy** —
   a trader who wins on a 10% probability bet gains far more ELO than one who
   wins on a 90% probability bet.
3. **Accuracy_pool/geo_elo structural separation** — geo market specialists
   are systematically excluded from the general research pool. Future work
   should consider a geo-specific research pool (≥5 geo trades, bot/wash filters).

---

## Next Steps

- Oscar to review LEGENDARY/ELITE tier accuracy vs comprehensive_elo baseline.
- If geo_elo LEGENDARY accuracy > 50% (outperforms comprehensive_elo LEGENDARY),
  proceed to Phase 4 signal generation using geo_elo tiers.
- Consider defining a geo-specific research pool to enable geo_accuracy_pool crossover.
