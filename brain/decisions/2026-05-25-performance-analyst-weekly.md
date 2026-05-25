# Decision Record: Performance Analysis Week of 2026-05-25

**Date:** 2026-05-25  
**Author:** performance-analyst-agent (run 4)  
**Type:** Weekly analysis findings — significant recommendations

---

## Key Finding 1: Elite Tier is the System's Signal Layer, Not Legendary

**Finding:** 30-day directional accuracy by tier (May 25, n=1,071 markets):
- Elite (1800-2175): 62.9% — above Phase 5 gate threshold
- Standard (1200-1800): 58.0% — approaching
- Legendary (>2175): 53.5% — at random baseline

**Interpretation:** The Legendary tier (5 traders in clean pool) is performing at essentially random over 30 days. This is consistent with the STR-001 suspension finding (78% of legendary markets triggered both YES and NO — LPs, not directional bettors). The Elite tier, by contrast, consistently exceeds the 60% gate. This implies:

1. STR-003 (which requires ELO >2175 at 95% conviction) is relying on a specific subset of legendary traders who are NOT LPs. The 5 legendary clean pool traders may not include these individuals if they don't meet resolved_trades_count≥20.
2. Signal strategies should consider lowering the ELO threshold from >2175 to >1800 as an alternative hypothesis for quant-research-agent to pre-register and test.

**Action:** No immediate strategy change. Note for quant-research-agent when pre-registering Phase 2 research questions.

---

## Key Finding 2: Research Pool Composition Has Fundamentally Changed

**Finding:** The explicit clean pool has expanded from 493 (May 7 authoritative) to 1,135 (May 25). The 7-day directional accuracy dropped from 63.16% (May 7 historical) to 50.2% (May 25, 7d window only). The pool expansion (+642 traders) brought in less-established traders who recently crossed the ≥20 resolved trades threshold.

**Interpretation:** The authoritative 63.16% finding is NOT invalidated — it was a historical measurement against 57 well-resolved markets using the 493-trader pool. The May 25 7d window measures a different population (333 markets resolved in the past week with no category labels). A genuine apples-to-apples comparison requires feedback-loop-agent to re-run the historical analysis using the current 1,135-trader pool.

**Action:** Run feedback-loop-agent this week using the explicit pool filter. If accuracy on the expanded pool is materially lower than 63.16%, we need to understand whether pool expansion brings in noise or genuine edge. This is Phase 5 Gate 2 attempt #8 (Run 8).

---

## Key Finding 3: Signal-Agent Stall Has Exceeded Escalation Threshold

**Finding:** 4th consecutive Sunday with signal-agent failure. Integration test has triggered HIGH priority escalation. The Putin market resolves in ~8 days without a rescan.

**Decision:** The integration test escalation threshold is correctly calibrated. The signal-agent is the most operationally critical agent in the system for Phase 5 progress — every week it doesn't run is another week STR-003's n stays at 1. Oscar must spawn it today.

---

## Key Finding 4: feedback.json Corruption is a Weekly Tax

**Finding:** 3 corruption incidents in 5 weeks (May 12, May 18, May 24). Each costs: (1) CI failure, (2) manual restoration time, (3) risk that feedback-loop-agent runs with corrupted memory.

**Decision:** The root cause (research-scout template overwriting the full file) must be treated as a permanent system bug, not a one-off incident. The fix is low complexity (template change to use read-modify-write instead of full overwrite) but has been deferred for 3 weeks. Fix it this week.

---

## Key Finding 5: Category Data Gap Breaks Accuracy Analysis

**Finding:** 99.95% of recently resolved markets have no category label. The category-level accuracy analysis (Geopolitics 92.3%, Elections 46.7%) that informed STR-003 and STR-004 designs cannot be performed on current data.

**Implication for Phase 6:** Without category data, the system cannot apply category-specific confidence multipliers when Phase 6 live trading begins. Category labelling for new markets must be addressed before Phase 6.

**Action:** Brief research-scout-agent to investigate auto-classification of Polymarket market titles by category using keyword/LLM-based matching. This is a data enrichment task, not a strategy task.
