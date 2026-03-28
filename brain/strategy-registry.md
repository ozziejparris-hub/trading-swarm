# Strategy Registry

Last updated: 2026-03-28
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
                        Promote to ACTIVE once >= 10 resolved markets
                        with accuracy >= 60% across all tiers.
                        feedback-loop-agent to score after April 1.
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
| —    | —        | —       | —       | —           |

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
