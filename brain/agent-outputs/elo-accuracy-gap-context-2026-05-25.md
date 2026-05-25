# ELO Accuracy Gap — Historical Context
**Date:** 2026-05-25  
**Purpose:** Synthesise what was already known about the LEGENDARY < QUALIFIED accuracy gap and the category-conditioning problem, so today's feedback-loop finding can be properly positioned.

---

## Q1 — Has the LEGENDARY < QUALIFIED gap been identified before? When and what was the conclusion?

**Yes. It has been observed across multiple runs, with growing confidence:**

| Date | Run | LEGENDARY | ELITE | QUALIFIED | Confidence | Status |
|------|-----|-----------|-------|-----------|------------|--------|
| 2026-04-25 | #1 | — | 72% (n=29) | 81% (n=153) | HIGH but **invalidated** | Contaminated pool (9,993 traders; correct clean pool = 857) |
| 2026-04-27 | #2 | — | — | 91% (n=11) | MEDIUM | Same contaminated pool — also invalidated |
| 2026-05-05 | #4 | — | — | 82% (n=67) | HIGH but **invalidated** | Pool contamination (746 vs 493 clean) |
| 2026-05-07 | #5 | — | — | 63% (n=57) | **HIGH, clean pool** | First authoritative result; category breakdown added |
| 2026-05-11 | #6 | — | — | 92% (n=12) | MEDIUM | Clean pool unclear — likely thin-sample artifact |
| 2026-05-18 | #7 | **57%** (n=54) | 53% (n=19) | **92%** (n=86) | HIGH/MEDIUM/HIGH | First time LEGENDARY measured as HIGH confidence; gap = 35pp |
| 2026-05-25 | #8 | **46%** (n=80) | **49%** (n=96) | **65%** (n=152) | HIGH/HIGH/HIGH | All three tiers now HIGH confidence simultaneously |

**First clear documentation of the gap:** May 18 (Run #7) — LEGENDARY 57%, QUALIFIED 92%, 35pp spread. The feedback-loop agent's action recommendation was "LEGENDARY tier at baseline — maintain current weighting." No investigation was triggered.

**Prior indirect evidence:** The May 7 category breakdown (finding `2026-05-07-CATEGORY-ELECTIONS-001` and `2026-05-07-CATEGORY-GEOPOLITICS-001`) showed QUALIFIED accuracy ranged from 46.7% (Elections) to 92.3% (Geopolitics) — a 45pp intra-category spread that foreshadowed why a platform-pooled LEGENDARY tier would be unreliable.

---

## Q2 — Has geopolitics-specific ELO been discussed? What was decided?

**Discussed but not built and no decision made:**

- **2026-05-19 session summary:** Listed as an outstanding item — "Geopolitics-specific ELO (category-conditioned per Nechepurenko paper)." Session noted: "category-conditioning essential — LEGENDARY accuracy at 57% explained by platform-wide pooling across sports/crypto/politics."
- **2026-05-20 MASTER_HANDOVER:** Explicitly flagged — "Geopolitics-specific ELO: identified as essential per Nechepurenko (2026), not yet built." The handover note directly linked it to the gap: "Critical finding: category-conditioning essential — platform-wide ELO pools sports/crypto/geopolitics — Directly explains LEGENDARY 57% vs QUALIFIED 92% accuracy gap."
- **Nechepurenko paper (arXiv 2605.02287):** Identified as must-read. The paper's Layer 1 (sign-randomisation skill classifier) showed 44% out-of-sample persistence for platform-wide ELO — low, consistent with category pollution diluting the signal.

**What was decided:** Nothing formal. It appears in the "outstanding items" list in two handovers but has never been assigned to quant-research-agent, pre-registered as a hypothesis, or given a target date. The May 18 feedback-loop run's action recommendation did not escalate it — it said "maintain current weighting."

---

## Q3 — Is there any existing plan or pre-registration to address this?

**No pre-registration exists for category-conditioned ELO. The closest items are:**

1. **RQ3.1 (research-directions.md):** Pre-registered hypothesis — "ELO-weighted trader predictions are better calibrated in some market categories than others." Tests Brier score by category. Status: not yet run by quant-research-agent. This would surface *which* categories are broken, but does not propose a fix (constructing separate per-category ELO scores).

2. **Category action recommendation (2026-05-07-ELO-QUALIFIED-002):** Finding recommended "Apply category-level weighting: Geopolitics+Unknown signals carry 91% accuracy vs Elections 47%." This is a *signal-weighting* fix at the output layer, not a fix to the ELO scores themselves.

3. **research-directions.md Outstanding Items:** "Geopolitics-specific ELO (category-conditioned)" is listed under the 2026-05-19 session compounding notes. No quant-research task, no pre-registration file, no signals.json entry.

**Gap:** No one has formally proposed or pre-registered the construction of a category-conditioned ELO. The insight exists; the implementation path does not.

---

## Q4 — What does today's finding (LEGENDARY 46%, QUALIFIED 65%) add that is new?

**Three things are genuinely new as of today:**

### 4a. LEGENDARY has crossed below baseline for the first time
May 18: 57% (above baseline, just below the 60% gate).  
Today: **46% (below baseline, HIGH confidence, n=80).**  
This is a qualitative shift: LEGENDARY is now actively generating *negative* alpha. Following LEGENDARY consensus would lose money vs random. The feedback-loop agent's May 18 recommendation ("maintain current weighting") is now clearly wrong — weighting LEGENDARY positively inverts the signal.

### 4b. ELITE has also crossed below baseline simultaneously
May 18: 53% (above baseline).  
Today: **49% (below baseline, HIGH confidence, n=96).**  
Both tiers above QUALIFIED are now sub-baseline. This is the first time all three tiers have been measured simultaneously with HIGH confidence, making the tier inversion statistically robust — not a sample artifact.

### 4c. The tier inversion is now HIGH confidence across the board
| Tier | n today | Confidence |
|------|---------|------------|
| LEGENDARY | 80 | HIGH |
| ELITE | 96 | HIGH |
| QUALIFIED | 152 | HIGH |

Previous readings of the gap used MEDIUM confidence on ELITE/LEGENDARY. Today all three carry HIGH confidence. The inversion can no longer be attributed to small samples.

### What is NOT new
- The explanation (category-conditioning via Nechepurenko) was already documented on 2026-05-19 and in the May 20 handover.
- The QUALIFIED-Geopolitics 92% vs Elections 47% finding has been documented since May 7.
- The existence of a LEGENDARY < QUALIFIED gap was visible at May 18 (Run #7).

---

## Summary for Action

| Question | Answer |
|----------|--------|
| Gap previously identified? | Yes — first documented May 18, Run #7 (57% vs 92%) |
| Explanation pre-existing? | Yes — Nechepurenko paper, documented May 19-20 |
| Geo-specific ELO discussed? | Yes — twice in handovers, never actioned |
| Pre-registration for fix? | No — gap in the research queue |
| What is new today? | LEGENDARY crossed below baseline; ELITE also below baseline; first time all three are HIGH confidence simultaneously |

**Recommended next step:** Pre-register a hypothesis for category-conditioned ELO before running any analysis. Specifically: does splitting the ELO pool by category (Geopolitics / Elections / Crypto / Other) and computing tier accuracy within each category restore the predictive ordering (higher ELO = higher accuracy within a category)? This is RQ3.1 extended — not just measuring the gap but proposing a structural fix. Requires Oscar approval before quant-research-agent implements.

---

*Written: 2026-05-25 | Based on: findings.json (all 35 entries), strategy-registry.md, research-directions.md, brain/decisions/ (all 16 files), weekly-audit 2026-05-25*
