# Decision Record: 30d Brier Crossed Below 0.20 System Target

**Date:** 2026-07-06
**Recorded by:** performance-analyst-agent (Run #9)
**Type:** Milestone / System health

---

## Milestone

The Pool C geo_elo_active weighted Brier score crossed below the system's minimum prediction accuracy target (0.20) on a trailing 30-day basis for the first time.

**30d Brier as of 2026-07-06:**
- Geopolitics: 0.1798 (n=89, directional acc 82.0%)
- Elections: 0.1912 (n=68, directional acc 80.9%)
- Combined: ~0.185 (n=157)

**Historical trajectory (Geopolitics 30d):**
0.2400 (Jun 8) → 0.2213 (Jun 15) → 0.2168 (Jun 29) → 0.1798 (Jul 6)

**Historical trajectory (Elections 30d):**
0.2982 (Jun 8) → 0.2714 (Jun 15) → 0.2234 (Jun 29) → 0.1912 (Jul 6)

---

## Context and Caveats

This is a genuine 4-consecutive-week improvement trend, not a single-week spike.

**Important caveat on 7-day Brier:** The 7-day Brier looks exceptional (Geo 0.0519, n=77) because 88 "by June 30" deadline Geopolitics markets resolved NO en masse this week — Russia/Sumy, NATO clash, Greenland deal, etc. These are near-certainty outcomes. Pool C correctly predicted NO across all of them, but this does not reflect predictive difficulty. The 30d figure (incorporating a broader distribution of market difficulties) is the authoritative metric.

**Data quality improvement context:** Clean markets grew 3x this week (28,608 → 92,144) due to the O-16 resolution backfill and O-17 co-write fix. This means more markets are now contributing to the 30d window, potentially including some easier ones that improve the average. The improvement is real but the rate of improvement may partly reflect better data coverage rather than purely improved prediction.

---

## Pool C Threshold Clarification

Several `contract_violation` signals were filed citing pool_c <2,500 (training-librarian Jun 27, Jul 4). The current integration contract Section 9 alert threshold is **<1,700**, not 2,500. The 2,500 figure was an older expected value, not the alert threshold.

As of 2026-07-06, pool_c=2,607 which is **above all alert thresholds**. The Jun 27 low of 2,155 was also above the 1,700 alert threshold. The root cause of the Jun 20→27 drop (3,660→2,155) remains unknown.

**Recommended action:** Oscar to clarify whether the pool_c threshold in agent alert logic should be updated to match the current Section 9 contract (<1,700) or whether a more conservative threshold (e.g. <2,000) should be set as a formal alert level.

---

## Implications

1. **Phase 5 Gate 3** still requires 60% accuracy on 10+ signals (current: 40% at n=5) — the Brier milestone does not advance Gate 3 directly.
2. **Phase 6 readiness** requires all 4 gates met + v2 signal cohort ≥10 resolved with positive edge. Brier target being met strengthens the case that the prediction system has real edge, but the gate structure requires formal evidence from the signal pipeline.
3. **LEGENDARY tier (79.6% accuracy, Jun 5)** remains the strongest signal source. Protecting the LEGENDARY pool quality (currently declining: 14 clean, down from 17 peak) is important for maintaining and improving the Brier score.
