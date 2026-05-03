## RQ1.1 — ELO Persistence Pre-Registration

**Scheduled run:** 2026-06-01  
**Agent:** quant-research-agent  
**Script:** `scripts/compute_period1_elo.py` + `brain/agent-outputs/quant-research/RQ1.1/rq1_1_elo_persistence.py`  
**Pre-registered:** 2026-05-03 (manually, by Oscar)  
**Status:** PENDING — do not run before 2026-06-01

---

### What we're testing

Whether Period 1 ELO (pre April 1 2026) predicts Period 2 Brier score performance.

Pearson r between `elo_period1_cutoff` and Period 2 Brier scores (markets resolved after April 1 2026).

**Null hypothesis:** ELO accumulated in Period 1 has no predictive value for out-of-sample accuracy in Period 2.  
**Alternative hypothesis:** Higher Period 1 ELO → lower (better) Brier score in Period 2 (negative r, or equivalently positive r if we invert the Brier scale).

---

### Why the last run was inconclusive

| Factor | Detail |
|--------|--------|
| n | 16 qualifying traders (need 30+) |
| Period 2 age | Only 25 days at time of run (Apr 26) |
| r | +0.175 — near zero, indistinguishable from noise |
| Previous direction | Was −0.194 with retrospective ELO; flipped positive after point-in-time ELO fix — direction instability was a data artefact, not signal |

The near-zero result is expected when Period 2 has only 25 days of resolved markets. This is a sample-size failure, not a theory failure.

---

### Pass criteria (pre-registered)

All thresholds locked — do not adjust after seeing results.

| Result | Condition | Action |
|--------|-----------|--------|
| **STRONG PASS** | r ≥ 0.40 AND p < 0.05 AND n ≥ 30 | ELO system validated for live signal use |
| **WEAK PASS** | 0.25 ≤ r < 0.40 AND p < 0.05 AND n ≥ 30 | Proceed with caution — monitor signals, do not increase position sizing |
| **INCONCLUSIVE** | r ≥ 0 but p ≥ 0.05, OR n < 30 | Extend Period 2 to Sept 1 2026 — rerun then |
| **FAIL** | r < 0.25 OR p ≥ 0.05 | See stop condition below |

---

### Stop condition

**Only stop the ELO research program if:**
- r is **negative** with p < 0.05  
  **AND**
- n ≥ 50 qualifying traders

A near-zero result at n = 30 is still INCONCLUSIVE, not a failure. Do not shut down the ELO system on weak evidence.

---

### Data requirements check (run first, before RQ1.1)

Before running RQ1.1, verify sample size:

```sql
SELECT COUNT(*) as qualifying_traders
FROM traders
WHERE elo_period1_cutoff IS NOT NULL
AND research_excluded = 0
AND EXISTS (
  SELECT 1 FROM trades t
  JOIN markets m ON m.market_id = t.market_id
  WHERE t.trader_address = traders.address
  AND t.timestamp > '2026-04-01'
  AND m.resolved = 1
);
```

**Target:** ≥ 30 (was 16 on April 26 2026)

If n < 30 on June 1: do not run. Log the count and reschedule for July 1.

---

### What changed since the last run

| Change | Impact |
|--------|--------|
| `research_excluded` pool corrected | 857 clean traders, was previously contaminated by included-then-excluded addresses |
| `trade_gap_flag` filter now active | 166 gap markets excluded from ELO calculation — ELO now reflects legitimate market activity only |
| Analysis modules returning real data | Were frozen at 1.0× multiplier; now using actual computed values |
| Full ELO recalculation completed 2026-04-30 | Clean foundation — all Period 1 ELO scores rebuilt from scratch |

These changes mean the June 1 run is effectively a **first clean run**, not a rerun of the April 26 attempt.

---

### Output format (required)

The quant-research-agent must produce:

1. A `brain/agent-outputs/quant-research/RQ1.1/rq1_1_rerun_june2026.json` with:
   - `n_qualifying_traders`
   - `pearson_r`
   - `p_value`
   - `period2_start`: `"2026-04-01"`
   - `period2_end`: date of run
   - `verdict`: one of `STRONG_PASS / WEAK_PASS / INCONCLUSIVE / FAIL`
   - `next_action`

2. A scatter plot or ranked table of trader ELO vs Brier score (Period 2)

3. A signal to `orchestrator` via `signals.json` with the verdict and next action

The agent **must not** adjust thresholds after seeing r. If the agent wants to propose different thresholds for future runs, document that separately as a new pre-registration — do not modify these criteria.

---

### Integration gate dependency

RQ1.1 STRONG or WEAK PASS is one of the 4 Phase 5 integration gate criteria. A FAIL or INCONCLUSIVE here does **not** halt the program — it delays the gate. RQ3.2 can still be tested independently.
