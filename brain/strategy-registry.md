# Strategy Registry

Last updated: 2026-03-29
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
```

---

## Active Strategies

### STR-001 — Elite Convergence Signal
```
Status:                 ACTIVE
Description:            3+ legendary traders (ELO > 2175) entering
                        same side of market within short window
                        triggers HIGH confidence signal
Category:               Signal detection
First validated:        —
Last revalidation:      —
Next revalidation due:  —
Validated by:           backtest-agent
Validation metrics:
  DSR:                  —
  Sharpe:               —
  PBO:                  —
  Sample markets:       —
Notes:                  Foundational signal type. Revalidate
                        quarterly or after any ELO methodology change.
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
