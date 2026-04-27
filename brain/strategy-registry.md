# Strategy Registry

Last updated: 2026-04-27
Maintained by: feedback-loop-agent (weekly) + Oscar (approvals)

---

## Purpose

This is the authoritative record of every active strategy in the
system. It exists for two reasons:

1. **Prevent strategy decay** — a strategy validated in January
   may not work in July. Markets evolve, edges get arbed away,
   trader behaviour changes. This registry surfaces when
   revalidation is due so nothing runs on stale assumptions.

2. **Institutional memory** — when quant-research-agent builds
   something new, it reads this file first to understand what
   has already been tried, validated, and deployed. No
   duplicated effort.

---

## How This File Works

feedback-loop-agent reads this file every Sunday.
Any strategy with last_revalidation_date more than 30 days ago
gets flagged and a revalidation_requested signal is written
to signals.json for backtest-agent to action.

Nothing is retired automatically. Oscar approves all retirements.
feedback-loop-agent flags. backtest-agent revalidates.
Oscar decides.

---

## Status Definitions

```
ACTIVE          — validated, currently in use by signal-agent
PENDING_REVIEW  — revalidation requested, awaiting backtest-agent
UNDER_REVIEW    — backtest-agent currently revalidating
SUSPENDED       — failed revalidation, awaiting Oscar decision
RETIRED         — Oscar approved retirement, kept for reference
EXPERIMENTAL    — in development, not yet validated
```

---

## Data Integrity Gates — PASSED

### RQ0.1 — Wash Trading Contamination Audit
```
Status:                 PASSED
Run date:               2026-03-29
Script:                 scripts/wash_trade_audit.py (first-repo)
Result:                 36 wallets flagged as wash_trade_suspect
                        0 of 36 in current top-50 leaderboard
                        0.1% of ELO >= 1500 traders affected
Conclusion:             ELO leaderboard is clean. Contamination
                        negligible. Safe to proceed to RQ1.1.
Next run:               Monthly or after any major platform
                        volume spike (run before any ELO recalculation)
```

### RQ0.2 — Bot and Automated Trader Detection
```
Status:                 PASSED
Run date:               2026-03-29
Script:                 scripts/bot_detection.py (first-repo)
Result:                 9 traders heavy in short-duration crypto
                        0 traders with 90%+ win rate over 30 trades
                        0 traders with uniform sizing
                        0 flagged (multi-signal threshold not met)
Conclusion:             No automated accounts distorting elite
                        leaderboard. Safe to proceed to RQ1.1.
Next run:               Monthly or as dataset grows — script will
                        activate as bot patterns emerge over time
Upgrade note:           2026-03-29 — upgraded to three-type
                        classification: SPEED_ARBITRAGE (exclude),
                        NEWS_PROCESSING (caution), SYSTEMATIC_RESEARCH
                        (keep — high value signal source)
```

---

## Active Strategies

### STR-001 — Elite Convergence Signal
```
Status:                 SUSPENDED
Description:            3+ legendary traders (ELO > 2175) entering
                        same side of market within short window
                        triggers HIGH confidence signal
Category:               Signal detection
First validated:        2026-04-27
Last revalidation:      2026-04-27
Next revalidation due:  BLOCKED — requires pre-registered refinement
                        (see suspension reason below)
Validated by:           backtest-agent
Validation metrics:
  Accuracy:             56.1% (n=41 signals, threshold: 60%)
  vs random baseline:   +6.1pp edge (fails minimum)
  vs market price:      market price 100% accurate; signal adds no edge
  DSR:                  N/A — signal accuracy test, not P&L backtest
  Sharpe:               N/A — signal accuracy test, not P&L backtest
  PBO:                  N/A — signal accuracy test, not P&L backtest
  Sample markets:       23 unique markets triggering signals
  Data range:           2025-09-27 to 2025-11-30
Suspension reason:      CRITICAL STRUCTURAL FLAW: 78.3% of qualifying
                        markets (18/23) triggered signals on BOTH Yes
                        and No sides simultaneously — legendary traders
                        split across both sides. Paired signals
                        contribute exactly 50% accuracy by construction.
                        7-30 day horizon accuracy: 42.9% (below random).
                        Signal as defined cannot reach 60% threshold.
Positive sub-signals:   30-90 day horizon: 84.6% (n=13)
                        ELO 3000+ tier: 75.0% (n=4)
                        Single-side unambiguous convergence: 100% (n=5)
Path to ACTIVE:         quant-research-agent must pre-register STR-001b
                        with exclusive convergence filter (3+ on one side
                        AND <3 on opposite side). Dominant-side approach
                        achieved 65.2% on 23 markets (above 60% threshold)
                        but requires pre-registered validation before
                        deployment. Oscar must approve the hypothesis.
Full report:            brain/agent-outputs/backtest-agent/
                        STR-001-validation-2026-04-27.json
Notes:
  Superseded by STR-001b (also SUSPENDED) and STR-003
  (PENDING_REVIEW). Root cause: legendary traders are
  predominantly LPs trading both sides, not directional
  bettors. The convergence premise was incorrect.
```

### STR-001b — Elite Exclusive Convergence Signal (PROPOSED)
```
Status:                 SUSPENDED
Description:            3+ legendary traders (ELO > 2175) entering
                        the SAME side of a market within 14 days,
                        WITH fewer than 2 legendary traders on the
                        opposing side. Requires genuine consensus,
                        not just convergence.

                        Key difference from STR-001: the exclusive
                        filter prevents both sides qualifying
                        simultaneously, which caused STR-001 to
                        fail at 56.1% accuracy.

                        Sub-findings from STR-001 backtest support:
                        - Unambiguous single-side signals: 100% (n=5)
                        - 30-90 day horizon: 84.6% (n=13)
                        - ELO 3000+ tier: 75.0% (n=4)

Category:               Signal detection
First validated:        Pending
Pre-registered:         2026-04-27
Approved by:            Oscar (2026-04-27)
Validation criteria:
  - Minimum 10 qualifying signals
  - Accuracy > 60% (minimum actionable)
  - Accuracy > 70% (HIGH confidence)
  - Tested across 2+ market categories
Sample size check:      2026-04-27 — 0 qualifying signals in
                        historical data (ELO > 2175, 3+ same side,
                        <2 opposing, 14-day window, resolved markets).
                        Below 10-signal minimum. Awaiting data
                        accumulation before backtest can proceed.
Literature:             Machine Spirits (2026) — peer-reviewed
                        validation that sophisticated LLMs exploit
                        unsophisticated agents in heterogeneous
                        markets. Supports premise that legendary
                        traders have genuine information advantage
                        over market consensus.
Notes:
  Distribution analysis (2026-04-27): legendary traders
  appear on both sides of markets in 95%+ of cases.
  The exclusive convergence filter will almost never fire
  with 3+ traders because high-ELO traders are predominantly
  LPs not directional bettors.

  The exception is single highly-directional traders at
  95%+ capital on one side — see RQ2.2 finding which showed
  75% positive price movement at 95% threshold (n=13).

  Recommend: retire STR-001 family and replace with
  STR-003 — Single Legendary Directional Signal based
  on RQ2.2 methodology. Pre-register when quant-research-agent
  has sufficient data.
```

### STR-003 — Single Legendary Directional Signal (PROPOSED)
```
Status:                 PENDING_REVIEW
Description:            A legendary trader (ELO > 2175,
                        research_excluded = 0) with >= 95% of
                        their capital on one side of a market
                        (zero or near-zero opposing hedge).
                        Based on RQ2.2 finding: YES positions
                        at 95% threshold showed 75% positive
                        price movement within 7 days (n=13).

                        Simpler and more empirically grounded
                        than STR-001 family. Fires on individual
                        conviction not group consensus.

Category:               Signal detection
Pre-registered:         2026-04-27
Approved by:            Oscar (2026-04-27)
Validation criteria:
  - Minimum 20 qualifying signals
  - Accuracy > 60% on outcome prediction
  - Price movement > 2pp in correct direction
  - Separate validation for YES vs NO signals
  - NO signal needs 14-30 day window (RQ2.2 finding)
Blockers:
  - Need more resolved markets with 95% directional
    legendary entries (currently n=13 from RQ2.2)
  - Rerun RQ2.2 with extended 14/30 day windows
    before declaring NO signal broken
Notes:
  RQ2.2 preliminary (n=13, LOW confidence):
  YES positions: 75% positive movement (above 60% threshold)
  NO positions: 0% at 7-day window (needs longer window)
  Current Harris/Florida signal in signals.json is
  STR-003 pattern — one trader, $130K NO, zero YES hedge.
```

### STR-002 — Pre-Resolution Intelligence
```
Status:                 EXPERIMENTAL
Description:            ELO-weighted smart money consensus on open
                        markets resolving within 7 days compared
                        against market price. Flags divergence > 15pt.
                        Tier system: LEGENDARY / ELITE / QUALIFIED.
Category:               Pre-resolution analysis
First validated:        2026-03-28 (dry run — 4 signals, pending
                        outcome validation after March 31 resolutions)
Last revalidation:      —
Next revalidation due:  2026-04-28
Validated by:           —
Validation metrics:
  Accuracy (LEGENDARY): pending first resolution batch
  Accuracy (ELITE):     pending first resolution batch
  Accuracy (QUALIFIED): pending first resolution batch
  Sample markets:       4 (insufficient — minimum 10 required)
Notes:                  First live signals generated 2026-03-28.
                        March 31 resolution batch is first real test.
                        Promote to ACTIVE criteria (all three required):
                        1. 4 weeks of daily runs completed
                        2. >= 10 resolved markets scored
                        3. >= 60% accuracy across all tiers
                        feedback-loop-agent owns promotion decision.
                        Oscar approves final status change.
```

---

## Retired Strategies

None yet.

---

## Experimental / In Development

See /brain/strategy-notes/ for hypotheses not yet submitted
for validation. Quant-research-agent manages that directory.

---

## Revalidation Log

| Date | Strategy | Trigger | Outcome | Approved by |
|------|----------|---------|---------|-------------|
| 2026-03-29 | RQ0.1 Wash Trading Audit | Initial run | PASSED — 36 suspects, 0 in top-50 | Oscar |
| 2026-03-29 | RQ0.2 Bot Detection | Initial run | PASSED — 0 flagged, dataset growing | Oscar |
| 2026-04-27 | STR-001 Elite Convergence Signal | First validation (never previously run) | FAILED — 56.1% accuracy (min 60%), structural flaw: 78% of markets trigger both Yes+No signals simultaneously | backtest-agent |

---

## Notes for Agents Reading This File

**quant-research-agent:** Before proposing any new strategy,
check this file. If something similar exists at ACTIVE or
SUSPENDED status, understand why before duplicating effort.
RETIRED strategies have failure reasons — read them.

**backtest-agent:** When you receive a revalidation_requested
signal, update this file's status to UNDER_REVIEW before
starting. Update to ACTIVE or SUSPENDED when complete.
Always update validation metrics after any run.

**feedback-loop-agent:** You own the revalidation schedule.
Flag overdue strategies, write signals, update
last_revalidation dates after backtest-agent confirms.
Never change status directly — write the signal and let
backtest-agent own the status update.

**signal-agent:** Read this file at startup. Only use
strategies with ACTIVE status. If a strategy you rely on
moves to PENDING_REVIEW or SUSPENDED, log this in your
cycle report and notify via agents bot.
