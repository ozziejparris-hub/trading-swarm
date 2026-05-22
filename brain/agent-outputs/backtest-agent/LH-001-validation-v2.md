# LH-001 Lifecycle Heuristic — Backtest Validation Report v2

**Date:** 2026-05-22
**Agent:** backtest-agent (Tier 3 — claude-sonnet-4-6)
**Task ID:** backtest-lh001-v4-20260522
**Input:** brain/agent-outputs/quant-research/LH-001/
**Status:** CONDITIONAL_PASS

> **Independent verification note:** All statistics reproduced directly from
> polymarket_tracker.db via positions + trades tables. WAL mode confirmed.
> Correct join key used: `trades.market_id = markets.market_id`. Clean pool
> at test time: 8,008 traders (research_excluded=0). Group sizes: 59 lifecycle
> candidates, 90 control. Pooled p=0.0160, r=0.2083. Results match prior v2
> exactly. All five tasks verified independently.

---

## Verdict

**CONDITIONAL_PASS — signal direction is real (p=0.0160 pooled) but event-level
validation fails on both events. Original p=0.0067 is not reproducible. V1
Haley p≈0.0000 was a market-scale confound artifact. Deploy as watchlist trigger
only via existing insider_signals infrastructure. Do not use as trading signal.**

---

## Task 1 — Mann-Whitney U Independent Replication

### Claim under review
quant-research-agent reported: p=0.0067 (one-tailed, clean sample excluding bots).

### Method
Pulled all (trader, market) pairs from positions table for the 4 market IDs
comprising the Haley and Iran events. Applied mandatory filters:
- `traders.research_excluded = 0`
- `traders.bot_type IS NULL`
- `markets.resolved = 1`
- `markets.winning_outcome NOT IN ('unknown', '')`
- `trades.timestamp <= datetime('now')`
- `positions.entry_total_cost >= $1,000`
- Join: `positions.market_id = markets.market_id`

Lifecycle criterion: trader's first recorded trade (across all markets) within
0–30 days of market resolution_date. Control: first trade >30 days before
resolution. Days calculated as `(resolution_date - first_trade_ever) / 86400`.

### Results

**Group sizes (confirmed):**

| Group | n | Median PnL |
|-------|---|-----------|
| Lifecycle candidates (clean) | 59 | $606,167 |
| Control (clean)              | 90 | $198,216 |

**Pooled Mann-Whitney U:**

| Test | p-value | Significant? |
|------|---------|-------------|
| One-tailed (candidates > control) | **0.0160** | Yes (p<0.05) |
| Two-tailed | 0.0320 | Yes |
| Rank-biserial r | 0.2083 | Small-medium effect |

**Event-specific results (CRITICAL):**

| Test | n_candidates | n_control | p (one-tailed) | Significant? |
|------|-------------|-----------|----------------|-------------|
| Haley vs Haley control | 36 | 53 | **0.1087** | No |
| Iran vs Iran control   | 23 | 37 | **0.4818** | No |
| Haley vs ALL control (confounded) | 36 | 90 | **0.0000** | Yes — ARTIFACT |

**V1 confound reproduced exactly.** The p≈0.0000 result is generated when Haley
lifecycle candidates (median PnL ~$716K) are compared against a mixed Haley+Iran
control pool (median PnL ~$198K). The mix dilutes the control with lower-profit
Iran entries. This is a market-scale selection artifact, not evidence of
lifecycle signal strength. Event-specific comparison is the methodologically
correct test; both events fail at event level.

**Conclusion:** The original p=0.0067 is NOT reproducible. My independent
replication gives p=0.0160 (pooled) — 2.4× higher p-value. The directional
signal exists at pooled level, but neither event validates individually.

**Verdict Task 1: CLAIMED p=0.0067 NOT CONFIRMED. Correct headline is p=0.0160
(pooled). No event achieves individual significance.**

---

## Task 2 — Bot Exclusion Validity

### Claim under review
Removing known bots from the raw control group is methodologically required.
Without exclusion: p≈0.98 (no signal). With exclusion: p=0.0160 (v2).

### Assessment

**Bot exclusion is methodologically valid.**

The excluded accounts are:
- **ARB_BOT:** 111 coordinated arbitrage wallets (ELO 3308–3315, excluded
  2026-05-06 per integration-contract.md v1.3). These are not human traders
  with private information — they are programmatic arb wallets.
- **LP_ARTIFACT:** Liquidity provision artefacts with thousands of positions
  from LP interactions. Including these in the control group produces
  artificially negative PnL for the control, biasing the comparison.
- **research_excluded=1:** Traders failing the minimum resolved_trades_count
  threshold (20) or otherwise flagged. Exclusion is per research-standards.md.

Without bot exclusion, bot accounts overwhelm the control group and produce
p≈0.98 (candidates NOT better) — a contaminated result.

**Caveats (non-disqualifying):**
1. V1 used `bot_type IS NULL` only (n=128 candidates); v2 uses the stricter
   `research_excluded=0 AND bot_type IS NULL` (n=59). Both are defensible;
   v2 is more conservative and consistent with research-standards.md.
2. Bot fraction in candidates (52/111 = 46.8%) is lower than control
   (113/203 = 55.7%) — if exclusion threshold is varied, group sizes change.

**Verdict Task 2: BOT EXCLUSION VALID. Methodology is sound.**

---

## Task 3 — N=2 Events: Power Analysis

### Assessment

**N=2 distinct events is INSUFFICIENT for generalisable claims.**

1. **Between-event variance cannot be estimated.** With n=2 events, there is
   no way to determine whether the pooled directional signal generalises to
   other geopolitics events or is specific to the Haley/Iran Nov-Dec 2025 context.

2. **Events are temporally clustered, not independent.** Haley resolved
   2025-11-20; Iran resolved 2025-12-02. Separation: 12 days. Both events
   share the same political news cycle (US/Middle East Nov-Dec 2025). Trader
   overlap is possible — traders monitoring Haley may have simultaneously
   monitored Iran. These are not two statistically independent observations.

3. **Per-event sample sizes are below the power threshold.** At observed
   effect size r≈0.20 (rank-biserial), statistical power is approximately:
   - Haley (n=36 vs n=53): ~25% → expect to FAIL significance ✓ (p=0.1087)
   - Iran (n=23 vs n=37): ~20% → expect to FAIL significance ✓ (p=0.4818)
   - Pooled (n=59 vs n=90): ~69% → borderline significance ✓ (p=0.0160)

4. **Minimum for 80% power at r=0.20:** approximately 100 candidates per
   event. Current: 36 Haley, 23 Iran. Both are well below threshold.

5. **Minimum for generalisable claims:** 5+ additional independent geopolitics
   events across different political contexts, time periods, and market
   structures. At least 3/5 must show p<0.05 at event level.

**Verdict Task 3: N=2 EVENTS INSUFFICIENT. Cannot distinguish "real but small
signal" from "coincidental result in small temporally-clustered sample."**

---

## Task 4 — Iran Market: Include or Exclude?

### Background

The market "Will Iran recognize Iran by June 2025?" has an impossible
self-referential title. Most likely interpretation: "Will Iran recognize Israel?"
or "Will Iran attack Israel" — consistent with late-2025 geopolitics.
Resolution: "No."

Additional concern: multiple Iran candidates show ELO at exactly 3000.0, 2700.0,
2000.0 — round-number clustering consistent with accounts whose ELO reflects
only the single Iran-market win (starting ELO 1500 → boosted to ~3000).
7 Iran candidates are flagged THIN_SAMPLE_ARTIFACT.

### Statistical Results

| Test | n_candidates | n_control | p (one-tailed) | Significant? |
|------|-------------|-----------|----------------|-------------|
| Pooled WITH Iran | 59 | 90 | **0.0160** | Yes |
| Pooled WITHOUT Iran (Haley only) | 36 | 53 | **0.1087** | No |
| Iran vs Iran-specific control | 23 | 37 | **0.4818** | No |

**Key finding: Removing Iran WEAKENS the signal, not strengthens it.** The
pooled p=0.0160 depends on Iran contributing directional support. Excluding
Iran drops to Haley-only p=0.1087, which fails significance.

**Recommendation:** Exclude Iran from any PASS-upgrade analysis given the
data quality concern (impossible market title). However, exclusion has the
paradoxical effect of making the evidence weaker, not stronger. The heuristic
needs more clean events, not fewer.

**Verdict Task 4: EXCLUDE Iran (data quality). Acknowledge that exclusion
reduces rather than increases statistical confidence. Iran market title must
be resolved via Gamma API before any definitive ruling.**

**Action item:** Resolve via Gamma API:
`condition_id: 0xdf31a15ee2f55b675d44882cbb2053a72b83ad40eef5d60b11762517f695f4ba`

---

## Task 5 — Prospective Applicability

### Can the heuristic be applied to new events with current data?

**Assessment: CONDITIONALLY APPLICABLE — infrastructure already exists.**

### What is working

The `insider_signals` table in polymarket_tracker.db already implements this
pattern. Current records: **7 signals** confirmed in DB, detected March–May 2026.

| wallet_age | position_size | market |
|-----------|--------------|--------|
| 3 days | $18,508 | Shelton Fed nomination |
| 3 days | $29,307 | Khamenei Supreme Leader |
| 62 days | $18,196 | US-Iran peace deal |
| 30 days | $2,685 | US forces enter Iran |
| 57 days | $4,457 | US forces enter Iran |
| 62 days | $13,653 | US forces enter Iran by Dec 31 |
| 62 days | $300,000 | Shelton Fed nomination |

Pattern label: "New wallet, large high-price bet, single market focus
(Iran-strike pattern)" — directly implements the lifecycle heuristic logic.

The existing implementation uses `wallet_age_days` which is MORE specific
than the lifecycle heuristic's first-trade proxy, because wallet creation date
may be retrievable from the Gamma API independently of trade history.

### Critical limitations

1. **Account creation proxy.** The lifecycle heuristic uses MIN(trade timestamp)
   as a proxy for account creation. For Nov-Dec 2025 events, any account that
   first traded in Aug-Oct 2025 (the start of our data window) appears "new"
   relative to resolution. True insider detection requires actual wallet creation
   date from Gamma API, not first observed trade.

2. **No outcome validation yet.** All 7 insider_signals records are on markets
   that have not yet fully resolved (or resolution is unknown in our DB). Zero
   confirmed accuracy/inaccuracy measurements are possible yet.

3. **False positive rate unknown.** The test set (Haley, Iran) has 100% win rate
   for all clean traders because both markets resolved "No" and clean traders
   held profitable "No" positions. This means no false positives were measured
   in-sample — because the filter is applied ex-post to already-resolved
   markets. Prospective false positive rate is unknown.

### What must happen before deployment as trading signal

1. Verify whether `wallet_age_days` in insider_signals uses Gamma API wallet
   creation date or first-trade timestamp. If Gamma API: insider_signals is
   already a better implementation. If first-trade proxy: precision is limited.
2. Track the 7 existing insider_signals records to resolution. Need ≥60%
   accuracy on ≥5 resolved records before any position-sizing use.
3. Extend heuristic to Unknown-category markets (366K markets). May contain
   geopolitics events that were never correctly categorised.

**Verdict Task 5: CONDITIONALLY APPLICABLE. Do NOT build a parallel system.
Use existing insider_signals infrastructure. Validate the 7 existing records
as markets resolve.**

---

## 7 Sins of Backtesting — Compliance

| Sin | Status | Notes |
|-----|--------|-------|
| Survivorship bias | ⚠️ PARTIAL | Only resolved markets. CSV filters PnL≥$1k — this selects ex-post winners. True prospective win rate is lower. |
| Lookahead bias | ✅ CLEAN | All timing data from trade timestamps. Resolution outcome not used in candidate selection. |
| Data snooping | ⚠️ CONCERN | Pre-registration exists (2026-05-19). N=2 events in 12-day window cannot fully prevent coincidental fit — too few distinct out-of-sample periods. |
| Transaction costs | N/A | Signal identification heuristic, not a P&L backtest. |
| Volatility clustering | N/A | Binary prediction markets. |
| Liquidity | ⚠️ NOTE | High-volume accounts ($500K–$2M positions) may have experienced meaningful price impact at entry. Not measured. |
| Temporal dependency | ❌ FAIL | Both validation events within 12 days, same political news cycle, potentially shared trader cohort. Temporal independence assumption violated. |

---

## Data Quality Issues

1. **Iran market title.** "Will Iran recognize Iran by June 2025?" is a data
   error. True market unknown. Gamma API resolution required.

2. **Join key.** Confirmed correct: `m.market_id = t.market_id` (99.999%
   match rate). `condition_id` join misses 37% of trades. Contract updated
   to v1.3 (2026-05-20).

3. **Win rate 100% in clean groups.** Expected: both markets resolved "No"
   and all clean traders held "No" positions. Comparison tests PnL magnitude,
   not win/loss rate. Methodologically valid but must be stated explicitly.

4. **n=69 vs n=59 vs n=128 discrepancy.** CSV (n=69) applied both volume≥$1k
   AND profit≥$1k filters. V1 used volume≥$1k only (n≈128). V2 uses
   research_excluded=0 AND bot_type IS NULL (n=59). V2 is most conservative
   and most consistent with research-standards.md.

---

## Conditions for PASS Upgrade

All six must be met before LH-001 can be promoted to PASS:

1. **5+ additional independent geopolitics events** from different time periods
   and political contexts. At least 3 of 5 must show p<0.05 at event-specific
   (not pooled) level.
2. **Insider_signals validation:** ≥5 of the 7 existing records resolve, with
   ≥60% directional accuracy.
3. **Confirm account_creation_date precision** in insider_signals pipeline
   (Gamma API wallet creation date vs first-trade proxy).
4. **Iran market title resolved** via Gamma API
   (`0xdf31a15ee2f55b675d44882cbb2053a72b83ad40eef5d60b11762517f695f4ba`).
5. **Unknown-category extension:** Run heuristic on Unknown markets with
   geopolitics keywords to expand validation event count.
6. **Oscar approves** promotion to EXPERIMENTAL.

---

## Required Metrics

```json
{
  "strategy": "LH-001 Lifecycle Heuristic — Single-Event Geopolitics Insider Detection",
  "tested_by": "backtest-agent",
  "test_date": "2026-05-22",
  "version": "v2-formal",
  "data_range": "2025-08-03 to 2026-05-22",
  "total_observations": 149,
  "clean_lifecycle_n": 59,
  "clean_control_n": 90,
  "sharpe_ratio": null,
  "brier_score": null,
  "win_rate": 1.0,
  "max_drawdown": null,
  "vs_baseline_rank_biserial_r": 0.2083,
  "transaction_costs_assumed": null,
  "verdict": "CONDITIONAL_PASS",
  "reason": "Pooled directional signal confirmed (p=0.0160, r=0.2083). Neither event individually significant (Haley p=0.1087, Iran p=0.4818). Original p=0.0067 not reproducible. V1 Haley p=0.0000 was market-scale confound — corrected. N=2 events in 12-day window insufficient for cross-event generalisation. insider_signals table (7 records) is the primary validation path.",
  "recommended_next_step": "refine",
  "pooled_p_one_tailed": 0.0160,
  "pooled_p_two_tailed": 0.0320,
  "haley_event_p_one_tailed": 0.1087,
  "iran_event_p_one_tailed": 0.4818,
  "v1_confound_p": "≈0.0000 (artifact)",
  "insider_signals_count": 7,
  "insider_signals_resolved": 0
}
```

---

## Conclusion

LH-001 shows a **pooled directional signal (p=0.0160) but zero event-level
validation.** The original p=0.0067 is not reproducible. The v1 Haley p≈0.0000
finding was a market-scale confound artifact caused by comparing Haley lifecycle
traders against a mixed Haley+Iran control pool.

Neither the Haley market (p=0.1087) nor the Iran market (p=0.4818) individually
validates the lifecycle heuristic. Removing Iran weakens the remaining signal
rather than strengthening it (Haley-only drops to p=0.1087).

The heuristic is conceptually sound — the Van Dyke DOJ indictment (April 2026)
confirms the lifecycle pattern exists in real insider trading. But the in-database
evidence base (2 events, 12-day window, single political news cycle) is
insufficient for statistical validation.

The insider_signals infrastructure already implements a more specific version
of this pattern and has generated 7 real-world detections (wallet age 3–62 days,
positions $2.7K–$300K, all geopolitics markets). The correct next step is to
validate those existing detections as markets resolve, not to build additional
parallel signal infrastructure.

**CONDITIONAL_PASS: Deploy as watchlist trigger only via existing insider_signals.
Do not use for position sizing. Validate on 5+ additional independent events and
7 existing insider_signals records before upgrading to PASS.**
