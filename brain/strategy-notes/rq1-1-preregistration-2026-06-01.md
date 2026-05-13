# RQ1.1 — ELO Persistence Pre-Registration (June 1, 2026 Rerun)

**Pre-registered:** 2026-05-13
**Scheduled run date:** 2026-06-01 (do not run before this date)
**Agent:** quant-research-agent (Tier 3 — Claude Sonnet 4.6)
**Extends:** rq1-1-rerun-pre-registration-june2026.md (May 3, Oscar)
**Script target:** brain/agent-outputs/quant-research/RQ1.1/rq1_1_elo_persistence.py (update in place)

This document locks the exact methodology and SQL queries for the June 1
rerun. The May 3 pre-registration established pass/fail thresholds — this
document adds the implementation detail that was missing: exact SQL, period
boundaries, query ordering, and what constitutes a hard stop.

Do not adjust thresholds or methodology after observing results.
If you want to propose a different methodology, pre-register it separately.

---

## 1. Research Question

Does a trader's ELO score accumulated in Period 1 (before April 1, 2026)
predict their out-of-sample Brier score in Period 2 (April 1 to June 1,
2026)?

Null hypothesis: ELO accumulated in Period 1 has no predictive relationship
with out-of-sample accuracy in Period 2 (Pearson r = 0).

Alternative hypothesis: Higher Period 1 ELO → lower Period 2 Brier score
(better accuracy). Expected direction: r < 0 (Pearson r between ELO
and Brier score, where lower Brier = better).

---

## 2. Why the April 26 Run Was Inconclusive

| Factor | Value | Problem |
|--------|-------|---------|
| n | 16 traders | Below 30-trader minimum — no statistical power |
| Period 2 age | 25 days | Too few resolved markets to stabilise Brier scores |
| r | +0.174 | Near zero, p = 0.518 — noise, not signal |
| trade_gap_flag filter | Missing | 166 gap markets not excluded from Brier computation |
| Period split method | NTILE(2) dynamic | Split date shifts as markets resolve — inconsistent with fixed elo_period1_cutoff |

The near-zero result is a sample-size failure. With n=16 and Period 2 only
25 days old, there is essentially no statistical power. This is not evidence
against the ELO hypothesis.

---

## 3. Methodology

### 3.1 Period Definitions (Fixed Boundaries — Critical Change)

The April 26 run used NTILE(2) on resolution_date to dynamically determine
the period split. This is wrong because `elo_period1_cutoff` in the traders
table was computed with April 1, 2026 as the explicit cutoff date. Using a
dynamic split makes Period 1 ELO and Period 1 Brier incoherent — the ELO
uses one boundary, the Brier uses another.

For the June 1 rerun, use fixed constants:

```
PERIOD_1_END   = '2026-04-01'   # exclusive upper bound for Period 1
PERIOD_2_START = '2026-04-01'   # inclusive lower bound for Period 2
PERIOD_2_END   = '2026-06-01'   # exclusive upper bound for Period 2 (day of run)
```

Period 1: All resolved markets with resolution_date < '2026-04-01'
Period 2: All resolved markets with resolution_date >= '2026-04-01'
          AND resolution_date < '2026-06-01'

### 3.2 ELO Source

Use `traders.elo_period1_cutoff` exclusively. This is the point-in-time ELO
frozen as of April 1, 2026. Do not use `traders.comprehensive_elo` — that is
retrospective and includes Period 2 market outcomes, which would be lookahead
bias.

Traders where `elo_period1_cutoff IS NULL` must be excluded (they had no
resolved trades before April 1 and cannot be tested).

Default fallback of 1500.0 (as used in April 26 script) is also excluded
here — if elo_period1_cutoff is NULL, the trader has no Period 1 ELO and
must be dropped from the analysis.

### 3.3 Brier Score Computation

Normalise all positions to the YES-probability space before computing Brier:

```
p_yes = entry_avg_price         if position.outcome = 'Yes'
p_yes = 1.0 - entry_avg_price   if position.outcome = 'No'
actual_yes = 1.0 if winning_outcome = 'Yes' else 0.0
brier_component = (p_yes - actual_yes)^2
```

Per-trader Brier = mean(brier_component) across all qualifying positions
in the period.

Only positions where entry_avg_price > 0 and entry_avg_price < 1 are
included (strict bounds — prices at boundary are data artefacts).

### 3.4 Minimum Positions Per Period

A trader must have ≥ 20 qualifying positions in EACH period to be included:
- ≥ 20 qualifying positions with resolution_date < '2026-04-01' (Period 1)
- ≥ 20 qualifying positions with resolution_date ≥ '2026-04-01'
  AND < '2026-06-01' (Period 2)

This is unchanged from April 26. The 20-position floor ensures per-trader
Brier scores are meaningful estimates rather than single-trade noise.

### 3.5 Positions Table Join

The positions table uses the market primary key (not condition_id). Use:

```sql
JOIN markets m ON m.market_id = p.market_id
```

This was confirmed correct in the April 26 run (returned 16 qualifying
traders with meaningful ELO/Brier distributions). Contrast with the trades
table, where `trades.market_id` stores condition_id — that join is:
`JOIN markets m ON m.condition_id = t.market_id`. Do not confuse the two.

### 3.6 Correlation Method

Primary: Pearson r between `elo_period1_cutoff` and Period 2 Brier score.
Secondary: Spearman rank correlation as a robustness check (non-parametric,
less sensitive to outliers).

Report both. Pass/fail criteria apply to Pearson r only.

---

## 4. Exact SQL Queries

Run these in order. Stop and write a contract_violation signal if any
validation query fails.

### Query 1 — Integration Contract Validation (Run First)

```sql
SELECT
  (SELECT COUNT(*)
   FROM traders
   WHERE research_excluded = 0)              AS clean_pool,

  (SELECT COUNT(*)
   FROM markets
   WHERE resolved = 1
     AND (trade_gap_flag = 0
          OR trade_gap_flag IS NULL))        AS clean_markets,

  (SELECT journal_mode
   FROM pragma_journal_mode())               AS wal_mode;
```

Expected ranges:

| Column | Expected | Alert if |
|--------|----------|----------|
| clean_pool | 450–600 | < 450 or > 700 |
| clean_markets | ≥ 11,491 | < 11,000 |
| wal_mode | wal | ≠ wal |

### Query 2 — Sample Size Gate (n ≥ 30 Required)

Run this before any analysis. If the count is below 30, halt and reschedule.

```sql
SELECT COUNT(*) AS qualifying_n
FROM traders tr
WHERE tr.research_excluded = 0
  AND tr.elo_period1_cutoff IS NOT NULL

  AND (
    SELECT COUNT(*)
    FROM positions p
    JOIN markets m ON m.market_id = p.market_id
    WHERE p.trader_address = tr.address
      AND m.resolution_date < '2026-04-01'
      AND m.resolved = 1
      AND m.winning_outcome IN ('Yes', 'No')
      AND m.winning_outcome IS NOT NULL
      AND p.outcome IN ('Yes', 'No')
      AND p.entry_avg_price > 0
      AND p.entry_avg_price < 1
      AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  ) >= 20

  AND (
    SELECT COUNT(*)
    FROM positions p
    JOIN markets m ON m.market_id = p.market_id
    WHERE p.trader_address = tr.address
      AND m.resolution_date >= '2026-04-01'
      AND m.resolution_date <  '2026-06-01'
      AND m.resolved = 1
      AND m.winning_outcome IN ('Yes', 'No')
      AND m.winning_outcome IS NOT NULL
      AND p.outcome IN ('Yes', 'No')
      AND p.entry_avg_price > 0
      AND p.entry_avg_price < 1
      AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  ) >= 20;
```

If qualifying_n < 30: write a signal to signals.json with type
`rq1_1_insufficient_n`, log the count, and schedule for July 1.
Do not run the Pearson analysis.

### Query 3 — Period 1 Position Data (for Brier computation)

```sql
SELECT
    p.trader_address,
    p.outcome           AS pos_outcome,
    p.entry_avg_price   AS entry_price,
    m.winning_outcome   AS win_outcome
FROM positions p
JOIN markets m  ON m.market_id   = p.market_id
JOIN traders tr ON tr.address    = p.trader_address
WHERE m.resolved = 1
  AND m.winning_outcome IN ('Yes', 'No')
  AND m.winning_outcome IS NOT NULL
  AND m.winning_outcome NOT IN ('unknown', '')
  AND p.outcome IN ('Yes', 'No')
  AND p.entry_avg_price > 0
  AND p.entry_avg_price < 1
  AND tr.research_excluded = 0
  AND tr.elo_period1_cutoff IS NOT NULL
  AND m.resolution_date < '2026-04-01'
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL);
```

Use this to compute per-trader Period 1 position counts (n ≥ 20 gate).
Period 1 Brier scores are not directly used in the correlation — only
Period 1 position counts are needed to confirm the trader was active.

### Query 4 — Period 2 Position Data (for Brier computation)

```sql
SELECT
    p.trader_address,
    p.outcome           AS pos_outcome,
    p.entry_avg_price   AS entry_price,
    m.winning_outcome   AS win_outcome
FROM positions p
JOIN markets m  ON m.market_id   = p.market_id
JOIN traders tr ON tr.address    = p.trader_address
WHERE m.resolved = 1
  AND m.winning_outcome IN ('Yes', 'No')
  AND m.winning_outcome IS NOT NULL
  AND m.winning_outcome NOT IN ('unknown', '')
  AND p.outcome IN ('Yes', 'No')
  AND p.entry_avg_price > 0
  AND p.entry_avg_price < 1
  AND tr.research_excluded = 0
  AND tr.elo_period1_cutoff IS NOT NULL
  AND m.resolution_date >= '2026-04-01'
  AND m.resolution_date <  '2026-06-01'
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL);
```

Compute per-trader Brier scores from this data. Include only traders
with ≥ 20 positions in this period.

### Query 5 — ELO Data

```sql
SELECT
    address,
    elo_period1_cutoff,
    total_trades,
    comprehensive_elo
FROM traders
WHERE research_excluded = 0
  AND elo_period1_cutoff IS NOT NULL;
```

Log `comprehensive_elo` alongside `elo_period1_cutoff` in output for
reference, but correlation analysis uses `elo_period1_cutoff` only.

---

## 5. Pass / Fail Criteria

All thresholds are locked as of 2026-05-13. Do not adjust after observing r.

The correlation is Pearson r between `elo_period1_cutoff` and Period 2
Brier score. Expected direction is r < 0 (higher ELO → lower Brier → better
accuracy). The absolute magnitude thresholds from the May 3 Oscar
pre-registration apply, with the sign requirement made explicit here.

| Verdict | Condition | Next Action |
|---------|-----------|-------------|
| **STRONG PASS** | r ≤ −0.40, p < 0.05, n ≥ 30 | ELO strongly predicts future accuracy — proceed to RQ3.2 and Phase 5 gate |
| **WEAK PASS** | −0.40 < r ≤ −0.25 | Directionally correct, insufficient magnitude — proceed with caution; monitor for 4 more weeks |
| **INCONCLUSIVE** | \|r\| < 0.25 or p ≥ 0.05 | No reliable signal — extend Period 2 to September 1, 2026 and rerun |
| **DIRECTIONAL FAIL** | r > 0, p < 0.05, n ≥ 30 | ELO anti-predicts accuracy — system premise fails; trigger stopping-rule review |

Sign confirmed by Oscar 2026-05-13 — negative r expected because higher ELO
predicts lower (better) Brier score. The April 26 script's convention
(r negative = pass) is authoritative. The May 3 pre-registration's "r ≥ 0.40"
refers to |r| magnitude; the required sign is negative.

---

## 6. Stopping-Rule Failure

The ELO research program halts only if both conditions are met:

1. r > 0 with p < 0.05 (ELO is positively correlated with Brier — higher ELO
   traders are systematically less accurate in Period 2, not more)
2. n ≥ 50 qualifying traders (enough power to trust the result)

A near-zero result at n = 30 does not trigger this. A positive r at n = 30
with p < 0.05 does not trigger this either — wait for n ≥ 50 before halting.

If the stopping rule is triggered, write a `stopping_rule_triggered` signal
to signals.json with the specific r, p, and n values, and do not proceed
with any further ELO-based research phases. Oscar must manually approve any
continuation.

---

## 7. Output Files Required

The run must produce all three or it is not complete:

**1. JSON results:** `brain/agent-outputs/quant-research/RQ1.1/rq1_1_rerun_june2026.json`

Required fields:
```json
{
  "rq": "RQ1.1",
  "run_timestamp": "<ISO8601>",
  "period_1_end": "2026-04-01",
  "period_2_start": "2026-04-01",
  "period_2_end": "2026-06-01",
  "n_qualifying_traders": <int>,
  "pearson_r": <float>,
  "pearson_p": <float>,
  "spearman_r": <float>,
  "spearman_p": <float>,
  "verdict": "<STRONG_PASS|WEAK_PASS|INCONCLUSIVE|DIRECTIONAL_FAIL|NOISE_FAIL>",
  "stopping_rule_triggered": <bool>,
  "next_action": "<string>",
  "elo_source": "elo_period1_cutoff",
  "trade_gap_flag_applied": true,
  "period_split_method": "fixed_2026-04-01",
  "qualified_traders": [...]
}
```

**2. Ranked table:** `brain/agent-outputs/quant-research/RQ1.1/rq1_1_rerun_june2026_ranked.md`

A markdown table of all qualifying traders sorted by ELO descending, showing
ELO, Period 2 Brier, Period 1 n, Period 2 n, total_trades. This allows
manual inspection of the relationship.

**3. Signal to orchestrator:** Write to `brain/signals.json`

```json
{
  "from": "quant-research-agent",
  "to": "orchestrator",
  "type": "rq1_1_complete",
  "payload": {
    "verdict": "<verdict>",
    "pearson_r": <float>,
    "pearson_p": <float>,
    "n": <int>,
    "stopping_rule_triggered": <bool>,
    "next_action": "<string>",
    "results_path": "brain/agent-outputs/quant-research/RQ1.1/rq1_1_rerun_june2026.json"
  },
  "timestamp": "<ISO8601>",
  "status": "pending"
}
```

---

## 8. Script Changes Required

The June 1 run uses `rq1_1_elo_persistence.py` as the base. The following
changes must be made before running:

| Change | Current (April 26) | Required (June 1) |
|--------|-------------------|-------------------|
| Period split method | NTILE(2) dynamic | Fixed: `'2026-04-01'` |
| Period 2 upper bound | MAX(resolution_date) | Fixed: `'2026-06-01'` |
| trade_gap_flag filter | Missing | Add to both period queries |
| NULL ELO handling | Default to 1500.0 | Exclude NULL — drop from analysis |
| n gate | Warn only | Hard exit if n < 30 |
| Output filename | rq1_1_results.json | rq1_1_rerun_june2026.json (preserve old file) |
| Spearman | Not computed | Add as robustness check |
| Stopping rule check | Not implemented | Log and signal if triggered |

The old rq1_1_results.json must NOT be overwritten — it is the April 26
baseline record. Write to the new filename.

---

## 9. Pre-mortem

Per Rule 11, before finalising this pre-registration:

**Top 3 ways this analysis could be wrong:**

1. **Period 2 is still too short.** Even by June 1, traders who entered
   markets in early April may not have had those markets resolve by June 1.
   Brier scores based on 20 positions are highly variable for a 2-month
   window. If n remains low (30–40), r will be unreliable.

2. **Market category composition shifts.** Period 1 included the US election
   markets (pre-November 2024), which were the highest-volume category. If
   Period 2 has a different distribution of market types, the Brier scores
   are not comparable across periods — a trader who specialised in political
   markets may look worse in a post-election environment not because their
   skill declined but because their market category is less active.

3. **ELO scale non-linearity.** Pearson r assumes a linear relationship.
   The ELO hypothesis may hold only at the elite tail (ELO > 1800) and not
   across the full research pool. A linear correlation across the full range
   may be near zero even if the elite signal is real. If Pearson r is
   inconclusive, add a stratified analysis: correlation within ELO ≥ 1800
   subset only.

**Black swan that would invalidate the result:**

A systematic data quality event (e.g., a second server migration window
similar to the April 7-18 gap that produced trade_gap_flag) in February–
March 2026 would mean elo_period1_cutoff itself is computed from incomplete
data. Run the trade_gap_flag check on Period 1 markets first — if more than
10% of Period 1 markets carry trade_gap_flag=1, halt and audit before
proceeding.

These items do not change the pre-registration. They are documented so the
analyst can interpret edge cases correctly.

---

## 10. Integration Gate Dependency

RQ1.1 STRONG PASS or WEAK PASS is one of the four Phase 5 integration gate
criteria. An INCONCLUSIVE result delays the gate but does not block RQ3.2.
A DIRECTIONAL FAIL (with n ≥ 50) triggers the stopping rule and requires
Oscar's manual approval before any further ELO-dependent research proceeds.
