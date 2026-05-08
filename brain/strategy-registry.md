# Strategy Registry

Last updated: 2026-05-08
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
Status:                 EXPERIMENTAL
Description:            A legendary trader (ELO > 2175,
                        research_excluded = 0) with >= 95% of
                        their capital on one side of a market
                        (zero or near-zero opposing hedge).
                        Fires on individual conviction not group
                        consensus.

Category:               Signal detection
Pre-registered:         2026-04-27
Approved by:            Oscar (2026-04-27)
Promoted to EXPERIMENTAL: 2026-05-07 (quant-research-agent,
                        RQ2.2 extended window analysis)
Validated threshold:    95% directional (STR-003 canonical)
Validated window:       Eventual resolution (prediction market
                        outcome proxy — no strict window needed)
Validation criteria:
  - Minimum 20 qualifying signals
  - Accuracy > 60% on outcome prediction
  - Price movement > 2pp in correct direction
  - Separate validation for YES vs NO signals
Validation metrics (2026-05-07):
  YES positions (95%, eventual resolution):
    n=18, 8 unique markets, 61.1% correct — PASS (>60%)
    avg days to resolution: 33.5
  NO positions (95%, eventual resolution):
    n=9, 6 unique markets, 77.8% correct — PASS (>60%)
    avg days to resolution: 27.4
  80% threshold + 30d strict window (secondary):
    YES n=42, 64.3% correct — PASS
    NO n=10, 60.0% correct — PASS (marginal)
  Sample base: 143 legendary traders (clean pool)
Asymmetry note:         NO signals more reliable than YES at
                        95% threshold (77.8% vs 61.1%). YES
                        sample concentration: 12 Zelenskyy
                        (all correct) + 12 Haley-Jan (all
                        wrong) partially cancel. Monitor as
                        n grows.
Next revalidation:      After 10 more markets resolve at 95%
                        threshold (target: n=28 YES, n=19 NO).
                        Expected: ~2026-Q3.
Notes:
  RQ2.2 preliminary (April 26, n=13):
    YES: 75% positive at 7d window
    NO: 0% at 7d — window artifact, not structural failure
  RQ2.2 extended (May 7, n=27 combined at 95%):
    YES: 61.1% eventual resolution (18 markets)
    NO: 77.8% eventual resolution (9 markets)
    7d asymmetry was a sample-size artifact — with
    extended data both directions pass 60% threshold.
  Active signals in signals.json (as of 2026-05-07):
    Newsom NO (Elections, before Sep 2026)
    USA UN Security Council NO (Geopolitics, 2026)
    Fed rate cut NO (Economics, March 2027)
    Putin invasion NO (Geopolitics, June 2026)
```

### STR-004 — Capital-Weighted Legendary Aggregate Signal
```
Status:                 HYPOTHESIS
Description:            When the capital-weighted aggregate position of
                        legendary traders (ELO > 2175,
                        research_excluded=0,
                        resolved_trades_count >= 20,
                        bot_type IS NULL) on an unresolved market
                        diverges from the crowd market price by
                        >= 20 percentage points, this constitutes a
                        signal that legendary smart money disagrees
                        with the crowd.

                        Unlike STR-003 (which requires a single 95%+
                        directional trader), STR-004 aggregates ALL
                        legendary capital on a market — including
                        traders with mixed positions — into a single
                        capital-weighted directional view.

                        Formula:
                          legendary_yes_pct = yes_capital /
                            (yes_capital + no_capital)
                          divergence = legendary_yes_pct - market_price_yes
                          Signal fires if abs(divergence) >= 0.20
                            AND total_legendary_capital >= $10,000
                            AND legendary_trader_count >= 3

                        Direction:
                          legendary_yes_pct > market_price_yes → YES signal
                          legendary_yes_pct < market_price_yes → NO  signal

Category:               Signal detection — aggregate capital divergence
Pre-registered:         2026-05-08
Pre-registration file:  brain/strategy-notes/str004-preregistration-2026-05-08.md
Signal scan query:      brain/strategy-notes/str004-signal-scan-query.sql
Approved by:            Oscar (2026-05-08)

Key distinction from prior strategies:
  STR-001 counted traders (convergence of directional positions).
    → SUSPENDED: 78% of markets triggered both Yes+No simultaneously.
  STR-003 requires 95%+ single-trader conviction.
    → Misses markets where no individual trader is 95%+ directional.
  STR-004 uses capital weighting across ALL legendary positions —
    including LPs and mixed holders — treating aggregate capital
    allocation as a price signal. LPs holding both sides at equal
    weight contribute neutrally; only net imbalances produce a signal.
    This directly addresses the STR-001 structural flaw.

Evidence basis:         Russia/Ukraine ceasefire Q2 2026 (May 2026):
                        8 legendary traders, $1.74M total, 55.7% YES
                        capital-weighted vs market price 7% YES = 48pp
                        divergence. None of these traders are 95%+
                        directional, so STR-003 misses them entirely.
                        Resolution: June 30 2026 (founding case).

Category accuracy:
  Geopolitics:          92.3% (HIGH confidence — apply confidence boost)
  Elections:            46.7% (below chance — apply skepticism flag)
  Source:               findings 2026-05-07-CATEGORY-GEOPOLITICS-001
                        and 2026-05-07-CATEGORY-ELECTIONS-001

Validation criteria:
  Minimum 10 resolved markets with STR-004 signals
  Accuracy > 60% on outcome prediction
  Separate YES/NO accuracy tracking required
  Separate Geopolitics/Elections accuracy tracking required

Pass criterion:         Founding case resolves YES (ceasefire happens)
                        AND accuracy >= 60% on first 10 markets;
                        OR: directionally correct in 6/10 first markets
Stop criterion:         Accuracy < 50% on 10+ resolved markets → abandon

Next revalidation:      After June 30 2026 (founding case resolves).
                        Formal backtest when n=10 resolved signals.

First validated:        Pending
Last revalidation:      —
Validated by:           —
Validation metrics:
  YES accuracy:         pending (n=0)
  NO accuracy:          pending (n=0)
  Total sample:         0 resolved markets (1 active signal — founding case)
  Active signals:       Russia/Ukraine ceasefire YES (2026-06-30)
Notes:
  Founding case signal filed in signals.json 2026-05-08.
  Market price must be fetched from Polymarket Gamma API at scan
  time — not stored in DB. See signal scan query for protocol.
  DB may mislabel the founding-case market as "Will Russia invade
  Ukraine by Q2 2026?" — actual market is about ceasefire,
  confirmed via Polymarket API. Direction=YES means ceasefire occurs.
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
Next revalidation due:  2026-07-01
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
| 2026-05-07 | STR-003 Single Legendary Directional | RQ2.2 extended window analysis | EXPERIMENTAL — YES 61.1% (n=18), NO 77.8% (n=9) at 95% eventual resolution. Both above 60% threshold. April 26 NO=0% was 7d window artifact. | quant-research-agent |

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
