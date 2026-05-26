# Quantitative Research Directions

## Purpose
This file gives the quant-research-agent directional nudges
before starting any research session. These are open questions
to investigate, not frameworks to copy. Your job is to find
which approaches have measurable edge specifically in prediction
markets — most traditional equity research methods will not
transfer directly without adaptation.

Read this before starting any new research phase. Add your
findings back to this file over time so it compounds.

---

## Phase 0 — Data Integrity (must complete before Phase 1)
*These two questions must pass before any other research questions run.
ELO validation is meaningless if the trader pool is contaminated.
Clean the pool before validating it.*

---

**RQ0.1 — Wash Trading Contamination Audit**
Hypothesis: A meaningful proportion of traders in the database
have artificially inflated activity records due to wash trading,
which would corrupt ELO calculations.

Background: Columbia University research found ~25% of Polymarket
volume involved wash trading. Sports and election markets worst
affected. Some weeks saw 90%+ of trades in those categories flagged.
A wash trader who trades a market against themselves creates a false
record of activity that could register as skill in the ELO system.

Test: Using network analysis — identify wallets that frequently
trade against each other, have correlated creation dates, trade
primarily at very low prices (<$0.01), and show rapid open/close
patterns. Flag likely wash trading accounts. Calculate what
percentage of current elite traders (ELO >= 1500) would be
reclassified after filtering.

Simpler fallback if network analysis is infeasible: flag any
trader whose trades are more than 80% concentrated in markets
where they appear to be the primary counterparty.

Data: trades table (counterparty patterns, timestamps, prices),
positions table (open/close speed), traders table (creation dates)

Success criterion: Produce a wash_trade_suspect boolean flag
on the traders table. Do NOT delete — flag only. If more than
5% of elite traders are flagged, rerun all ELO calculations
against the clean pool before proceeding to RQ1.1.

Null hypothesis: Fewer than 2% of elite traders are wash
trading suspects (contamination is negligible).

Why this matters: If the ELO pool is contaminated with wash
traders, every downstream research question is built on
corrupted foundations. This must be answered first.

---

**RQ0.2 — Bot and Automated Trader Detection**
Hypothesis: A subset of high-ELO traders are automated bots
whose edge (spread capture, speed arbitrage) is not copyable
by a slower system, and who should be excluded from signals.

Background: 15-minute crypto bots on Polymarket achieve high
win rates through spread capture. Their edge disappears when
copied at market price because the opportunity is gone by the
time a human or slower system can act. These bots likely score
highly on ELO because their win rates are genuine — but the
edge is structural, not informational, and not copyable.

Test: Identify traders whose win rate is concentrated in
short-duration crypto markets (resolving in 15 minutes to
24 hours) and who trade at unusually high frequency with
consistent position sizing. Also flag traders with 90%+
win rates over more than 30 trades — statistically
improbable without either insider information or automated
execution.

Simpler fallback heuristic: flag traders with more than
50% of trades in crypto markets resolving under 24 hours.

Data: trades table (timestamp patterns, market categories,
position sizing consistency, frequency),
markets table (category, resolution timing),
traders table (win rates, trade counts)

Success criterion: Produce a bot_suspect boolean flag on
the traders table. Calculate what the ELO leaderboard
looks like with bot suspects excluded. If more than 20%
of the top 50 change, document this as a critical finding
requiring signal-agent filter update.

Null hypothesis: Fewer than 5% of top-50 ELO traders
are bot suspects (automation is not meaningfully
distorting the leaderboard).

Why this matters: Following a bot into a position after
it has already moved gives you a worse price and no edge.
If bots dominate the elite leaderboard, signals based
on their activity are systematically misleading.

---


## Direction 1 — Trader Behaviour Factors
Prediction markets are driven by people, not algorithms.
Understanding trader behaviour patterns may reveal edge.

Questions worth investigating:
- Do high-ELO traders (>1800) show measurable momentum?
  i.e. when they enter a position, does price continue moving
  in their direction for a predictable window?
- Is there a "smart money" timing signal — do legendary traders
  (ELO >2175) consistently enter earlier than the market moves?
- Do elite traders cluster around specific market categories
  (geopolitical, economic, sports) or are they generalist?
- What is the relationship between position size and ELO score?
  Do better traders size up on higher-conviction markets?
- Is there a meaningful difference between traders who enter
  early vs traders who enter late in a market's lifespan?

Relevant data: traders table (ELO scores), trades table
(timestamps, sizes), markets table (resolution dates)

### Priority Investigation (from live system observation)
Trader 0xb442 holds ELO 3500 with only 4 closed positions.
Traders 0xbf79 and 0x64aa hold ELO ~3340-3347 with 2000+
closed positions, $8-9M realized profit, 80%+ win rate.

Key question: does low-trade-count high-ELO actually predict
outcomes better than high-trade-count moderate-ELO?

Test this in Phase 1 by comparing signal accuracy for:
- Group A: ELO > 3000, trades < 10 (high ELO, low confidence)
- Group B: ELO > 3000, trades > 100 (high ELO, high confidence)
- Group C: ELO 2800-3000, trades > 500 (moderate ELO, deep history)

Hypothesis: Group C may be the most reliable signal source
despite lower raw ELO score.

---

## Direction 2 — Market Pricing Factors
Prediction market prices may be systematically mispriced
in detectable, exploitable ways.

Questions worth investigating:
- Are markets with low elite trader participation consistently
  mispriced relative to markets with high participation?
- Do prices overreact or underreact to external news events?
  Is there a mean-reversion opportunity after sharp moves?
- Are tail-risk markets (trading below 5 cents or above 95)
  systematically over or underpriced relative to true probability?
- Do related markets (same topic, different outcomes) price
  correlated events consistently or are there arbitrage gaps?
- Is there a time-decay pattern — do prices drift toward
  50 cents or toward resolution as expiry approaches?

Relevant data: markets table (prices over time),
trades table (volume patterns), positions table (P&L outcomes)

---

## Direction 3 — Momentum and Timing Factors
Price movement patterns may be predictable in short windows.

Questions worth investigating:
- After a sharp price move (>10% in 24 hours), what is the
  probability of continuation vs reversal?
- Is there a volume signal — does high volume confirm moves
  or is it a contrarian indicator in prediction markets?
- Do prices move predictably around external event dates
  (elections, Fed meetings, economic releases)?
- Is there an opening/closing pattern — do prices behave
  differently when a market first opens vs final 20% of life?
- Does momentum from one related market predict moves
  in correlated markets with a measurable lag?

Relevant data: trades table (timestamps, prices, volumes)

---

## Direction 4 — Quality and Calibration Factors
How well does the existing system predict outcomes?
Improving calibration is the highest-value near-term research.

Questions worth investigating:
- What is the current Brier score of ELO-based predictions
  across all resolved markets? (Phase 1 priority)
- Which ELO ranges are best calibrated and which are worst?
  Are legendary traders more or less calibrated than elite?
- Are predictions better calibrated for certain market types
  (political vs economic vs sports vs crypto)?
- Does calibration improve or degrade as markets approach
  resolution date?
- What simple adjustments to ELO-based probability estimates
  would most improve Brier score?

Relevant data: traders table (ELO), markets table
(resolution outcomes), positions table (prediction vs outcome)

---

## Direction 5 — Composite Scoring
Combining multiple signals may outperform any single factor.

Questions worth investigating:
- What combination of trader behaviour + price momentum +
  calibration factors produces the strongest predictive signal?
- Is a simple equal-weighted composite better or worse than
  a weighted composite optimised on historical data?
- Does adding more factors improve or degrade signal quality?
  At what point does complexity hurt performance?
- Can a single composite score reliably rank markets by
  expected edge from highest to lowest?

Note: build single-factor models first and validate each
before attempting composite models. Composites built on
unvalidated factors compound errors, not signal.

---

## Direction 6 — Risk and Correlation Factors
Understanding portfolio-level risk matters as much as
finding individual market edge.

Questions worth investigating:
- How correlated are related prediction markets?
  (e.g. do US election state markets move together?)
- What is the historical maximum drawdown of following
  elite trader signals without position sizing rules?
- Does Kelly criterion position sizing improve risk-adjusted
  returns vs flat position sizing?
- Are there market categories that act as natural hedges
  against each other?
- What is the tail risk profile — how often do high-confidence
  signals (multiple legendary traders converging) fail?

Relevant data: positions table (P&L, drawdowns),
markets table (categories, correlations)

---

## Direction 7 — Reinforcement Learning for Position Sizing
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: can an agent learn optimal position sizing
by treating each trade as a sequential decision with a reward
signal, rather than using fixed Kelly criterion rules?

Questions worth investigating:
- Can a simple RL agent learn to size positions better than
  fixed Kelly criterion on your Polymarket data?
- What reward signal best captures trading quality —
  pure P&L, risk-adjusted returns, or Brier improvement?
- Do legendary traders (ELO >2175) implicitly follow
  Kelly-optimal sizing, or do they systematically deviate?
- Is there a detectable sizing pattern before high-conviction
  markets vs uncertain markets?

Start simple: Q-learning with discrete position sizes
(small/medium/large) before attempting deep RL.
Validate each step with backtest-agent before proceeding.

---

## Direction 8 — Inverse Reinforcement Learning
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: what objective function are your best
traders actually optimising for? It may not be pure P&L.

Your legendary traders (ELO >2175) are expert demonstrations.
IRL attempts to recover their implicit reward function from
observed behaviour — position sizing, entry timing, market
selection, exit decisions.

Questions worth investigating:
- Do elite traders optimise for Sharpe ratio, pure returns,
  or something else entirely?
- Is there a detectable difference between what legendary
  traders optimise vs elite traders (ELO 1800-2175)?
- Can the inferred reward function be used to score new
  markets before entering — "would a legendary trader
  take this position?"

Note: this is advanced research. Do not start here.
Complete Directions 1-4 first. IRL requires clean
behavioural data from completed markets only.

---

## Direction 9 — Regime Detection
Drawn from ML in Finance (Dixon, Halperin, Bilokon)

The core question: do your ELO signals and quant models
remain valid across different market regimes, or do they
degrade when market dynamics shift?

Questions worth investigating:
- Are there detectable regime shifts in Polymarket —
  periods where elite trader signals stop predicting outcomes?
- Do certain market categories (political vs economic)
  have different regime characteristics?
- Can a Hidden Markov Model detect regime changes in
  real-time before signal quality degrades?
- Should position sizing or signal thresholds adjust
  dynamically based on detected regime?

This protects your system from deploying strategies
in conditions where they no longer have edge.

---

## Direction 10 — News-to-Signal Intelligence Layer (Phase 5-6)

The core idea: press conferences, news articles, and social media
contain structured signals that move markets with a delay of minutes
to hours. Claude can extract these as JSON before the market adjusts.

**Validated architecture precedent:**
The tennis stack Layer 4 architecture demonstrated this pattern:
injury flags, form deltas, surface comfort scores — all extracted as
structured JSON from unstructured text and fed into a decision engine.
The geopolitics equivalent is: escalation signals, diplomatic momentum,
ceasefire probability shifts.

**Live proof (Feb 28 2026):**
Six wallets traded on the Iran/Israel/US strike market 71 minutes
before news broke, at 17% implied probability. The pre-resolution
intelligence layer needs to detect the signals those traders were
reading — before the market adjusts, not after. This is the gap.

**Proposed implementation:**
Claude reads diplomatic statements, official press releases, and X posts
from key accounts (foreign ministries, senior officials, verified
journalists on the beat). Outputs structured JSON per market:

```json
{
  "escalation_flag": true,
  "ceasefire_probability_delta": -0.12,
  "key_actor_positioning": "US SecDef statement ambiguous on red lines",
  "confidence": 0.7,
  "source_count": 3
}
```

Output feeds into pre_resolution_intelligence.py as an additional
signal layer alongside the ELO wallet tracking. ELO tells you
WHERE smart money is positioned. This tells you WHY.

**Phase:** 5-6, after signal quality is validated on wallet-based signals.
Do not build before Phase 5 — validate the ELO signal layer first.

Questions worth investigating:
- Which source types (official statements vs journalist posts vs wire)
  have the best signal-to-noise ratio for geopolitics markets?
- What is the average lag between a structured news signal and
  a measurable market price movement? (This determines build urgency.)
- Can Claude reliably extract escalation_flag as a binary from
  ambiguous diplomatic language? Test on historical statements
  with known market outcomes.
- Does combining news-signal JSON with elite wallet positioning
  improve Brier score over wallet signal alone?

---

## AI Model Watch List

Models being tracked as cost reduction candidates for the agent infrastructure.
Benchmark against Claude Sonnet 4.6 at Phase 2 before making any swap.

**Kimi K2.6** — Released 2026-04-20. Open-weight, modified MIT license.
- API pricing: $0.60/$2.50 per MTok input/output (5-6x cheaper than Claude Sonnet 4.6)
- Benchmarks competitive with Claude Opus 4.6 and GPT-5.4 on coding and agent tasks
- Agent Swarm feature (up to 300 parallel agents) is a closed platform feature — not applicable to this architecture
- OpenAI-compatible API endpoint via platform.moonshot.ai — can be tested in spawn_agent.sh without code changes by swapping the base URL
- Priority: benchmark against Sonnet 4.6 at Phase 2 as potential Tier 3 replacement
- Watch alongside DeepSeek V4 as the two most important cost reduction candidates

---

## Social Media Noise Contamination — Pre-Resolution Intelligence Gap

Identified: April 2026
Source: Polyfactual analysis of Netanyahu market ($84M volume)

**The problem:**
A market ("Netanyahu out by March 31") was driven to $84M volume
almost entirely by unverified X rumours. Smart money correctly
held at ~8% odds. The crowd drove the price up based on viral
misinformation rather than informed trading.

This creates a false signal problem for the pre-resolution
intelligence system: if elite traders are correctly positioned
at 8% while the market price is elevated due to noise, the
divergence signal fires correctly — but without knowing WHY
the crowd price moved, the signal interpretation is ambiguous.

**The gap:**
The system currently cannot distinguish:
- Price moved because informed money disagrees with crowd → strong signal
- Price moved because viral X post inflated crowd price → weaker signal
  (elite traders may simply be ignoring noise, not making an informed bet)

**Proposed addition (Phase 5-6):**
A social media noise filter for pre-resolution signals. When a
market shows unusual price movement, cross-reference against
whether that movement correlates with viral X/news activity vs
genuine order flow. Polymarket volume spike + X trending =
noise flag. Polymarket volume spike without X activity =
potentially informed trading signal.

This connects to the Phase 7 news processing layer — the same
infrastructure that reads news for betting signals can flag
when a market price is likely noise-driven rather than
information-driven.

**Interim approach (now):**
When reviewing pre-resolution signals manually, check whether
the market has had unusual volume spikes recently and whether
those spikes correlate with X activity. Flag manually as
NOISE_RISK if so. This is a human judgement call until the
automated filter is built.

## What Has Already Been Investigated
(Update this section as research completes)

### Data Integrity Gates (both PASSED)

**RQ0.1 — Wash Trading Contamination Audit (PASSED, 2026-03-29)**
Result: 36 wash trade suspects identified; 0 in top-50 leaderboard;
0.1% of ELO ≥1500 traders affected. ELO leaderboard is clean.
Next run: monthly, especially before any ELO recalculation.

**RQ0.2 — Bot and Automated Trader Detection (PASSED, 2026-03-29)**
Result: 0 traders meet multi-signal bot threshold; 9 flagged heavy
in short-duration crypto (below threshold). Three bot types classified:
SPEED_ARBITRAGE (exclude), NEWS_PROCESSING (caution), SYSTEMATIC_RESEARCH
(keep). NEAR_RESOLUTION bot type added separately (do not follow).
Next run: monthly.

### Foundational Research Questions

**RQ1.1 — ELO Persistence (INCONCLUSIVE, 2026-04-26)**
r=+0.175, p=0.52, n=16. Sample size failure — Period 2 had only 25 days
of resolved markets. Rerun pre-registered for June 1 2026 with full
60-day Period 2 window. Do not treat as evidence of no signal.

**RQ2.2 — Entry Timing Advantage (INCONCLUSIVE, 2026-04-26)**
YES positions (n=18): 61.1% resolved in signal direction — PASSES 60%.
NO positions (n=9): 77.8% resolved — PASSES 60%.
Both tested at 95% directional threshold (STR-003 compatible).
Extended window (14-day, 30-day outcome) pre-registered for June 2026.

**RQ3.2 — Crowd vs Elite Divergence (INCONCLUSIVE, 2026-04-26)**
Only 4 qualifying markets after filters (need 50+). Methodology needs
reframing toward single 95%-directional legendary traders vs market price.
Extended approach pre-registered for June 2026.

### Strategy Validation Results

**STR-001 — Elite Convergence Signal (FAILED, 2026-04-27)**
56.1% accuracy (threshold: 60%). Structural flaw: LP contamination.
78% of markets triggered both YES and NO signals — legendary traders
hold mixed positions as LPs. Exclusive convergence definition (STR-001b)
requires pre-registration before retest.
See: brain/failed-experiments/STR-001-as-defined-2026-04-27.md

**STR-003 — Single Legendary Directional Signal (EXPERIMENTAL, 2026-05-07)**
YES 61.1% (n=18), NO 77.8% (n=9). Both pass 60% threshold at 95%
directional filter. 1/1 resolved signal correct (Ramaswamy NO, 2026-05-02).
Not yet validated to ACTIVE — needs ≥20 resolved signals.
Key insight: 95% directional threshold effectively filters LP positions.

**STR-004 — Capital-Weighted Legendary Aggregate Signal (EXPERIMENTAL, 0/1)**
Founding case: Russia/Ukraine ceasefire market resolved NO on 2026-05-08.
8 legendary traders, $1.74M, 55.7% YES vs market 7% YES — crowd was correct.
n=1 failure, stop criterion <50% over 10 markets. Strategy continues.
Open question: does capital weighting fail in asymmetric markets (<10% crowd)
where legendary YES may be hedges rather than conviction bets?

### Category Calibration (from feedback-loop-agent)

Geopolitics: 92.3% accuracy (n=13) — HIGH confidence, confidence boost applied
Elections: 46.7% accuracy (n=15) — below 50%, active skepticism applied
Economics: Unknown at n=4 — insufficient data
(Source: feedback-loop-agent run #4, signal-agent category flags 2026-05-07)

---

## What Has Failed or Been Ruled Out
(Update this section as experiments conclude)

- **STR-001 as-defined (RULED OUT, 2026-04-27):** Elite convergence
  without exclusivity filter has no predictive value over market price.
  Root cause: LP structure of legendary traders means convergence
  without exclusivity is noise, not signal. Retry only as STR-001b
  with exclusive convergence filter, pre-registered.

- **Pure ELO-ensemble vs market price (RQ3.2 first framing):** Testing
  ELO-weighted consensus across ALL legendary traders (including mixed-LP
  positions) against market price — produces only 4 qualifying markets
  after appropriate filters. The framing may be wrong. Single highly-
  directional traders (95% threshold) vs market price is the more
  meaningful test. Reframed for June 2026.

---

## Compounding Notes
As the quant-research-agent completes phases, add key findings
here as one-line summaries so future research sessions start
with accumulated knowledge rather than from zero.

- 2026-04-27: RQ0.1 PASSED — ELO leaderboard clean. 0.1% contamination by wash traders.
- 2026-04-27: RQ0.2 PASSED — No bot distortion at top of leaderboard. Three bot types defined.
- 2026-04-27: STR-001 FAILED — LP contamination structural flaw. 78% markets split. Paired = 50%.
- 2026-04-27: STR-001 sub-signal: exclusive 1-sided legendary convergence = 100% accuracy (n=5 small).
- 2026-04-26: RQ2.2 YES positions (n=18): 61.1% resolve in signal direction. NO (n=9): 77.8%.
- 2026-05-05: QUALIFIED ELO consensus accuracy: 82% (n=67, HIGH confidence). +32pp above random.
- 2026-05-07: STR-003 EXPERIMENTAL: 95% directional filter works — YES 61.1%, NO 77.8% at resolution.
- 2026-05-07: Category calibration: Geopolitics 92.3% (HIGH), Elections 46.7% (CAUTION).
- 2026-05-08: STR-004 pre-registered: 48.7pp legendary/market divergence in founding case (Russia/Ukraine).
- 2026-05-09: ELO calibration drift — legendary count 28x since March baseline. Investigate before June 1 rerun.
- 2026-05-13: RQ0.1 and RQ0.2 re-run (May 13) — BOTH PASSED again. Clean pool 493 post-maintenance (588 pre-maintenance, 16 wash suspects removed by daily maintenance 2026-05-14). Next run due 2026-06-13.
- 2026-05-08: STR-004 FIRST DATA POINT — founding case (Russia/Ukraine ceasefire) FAILED. Crowd at 7% YES was correct; 8 legendary traders at $1.74M 55.7% YES were wrong. n=1, stop criterion is <50% over 10 markets. Continue validation.
- 2026-05-16: Research pool discrepancy — live `WHERE research_excluded=0` returns 604 traders vs 493 authoritative. Use explicit criteria: `research_excluded=0 AND resolved_trades≥20 AND bot_suspect=0 AND wash_trade_suspect=0` until code-hygiene fixes update_research_exclusions.py.
- 2026-05-20: LH-001 PARTIALLY VALIDATED — lifecycle heuristic (single-geo-market, 0-30 days before resolution) shows p=0.0067 profit advantage over control (clean, n=69 vs 160), but win rate only 47.7% (target 70%). 2 events only. CRITICAL: integration-contract.md condition_id join is WRONG — use m.market_id = t.market_id (3.5M vs 2.2M trades). Backtest validation pending.
- 2026-05-21: LH-001 CONDITIONAL_PASS (backtest-agent v2) — original p=0.0067 not reproducible.
  Corrected: pooled p=0.0160 (n=59 vs n=90 clean). V1 Haley p=0.0000 was a market-scale confound.
  Neither event independently significant. Effect size r=0.208 (small-medium). N=2 events
  insufficient for trading signal deployment. DEPLOY AS WATCHLIST TRIGGER ONLY via existing
  insider_signals table (7 detections already). Validate on 5+ distinct events before promotion.
- 2026-05-20: Research pool now 7,908 traders (integration-health.json 2026-05-20). Previous figure of 493 was from May 7 — pool grows daily as traders reach resolved_trades >= 20 threshold.


## Formal Research Questions
*(Added after system maturation — these are falsifiable hypotheses
to be tested by quant-research-agent using actual system data.
Each question has a specific test, specific data source, and
specific success criterion. Do not treat these as directions —
treat them as experiments to run and report verdicts on.)*

---

### Category 1 — Trader Skill Durability
*The fundamental question: is ELO measuring real skill or noise?*

**RQ1.1 — ELO Persistence**
Hypothesis: A trader's ELO score in period T predicts their
Brier score in period T+1 better than chance.

Test: Split resolved markets into two chronological halves.
Calculate ELO from first half only. Measure Brier score
in second half. Correlate.

Data: positions table (resolution outcomes),
traders table (ELO scores), markets table (resolution dates)

Success criterion: Pearson r > 0.25 between first-half ELO
and second-half Brier score across traders with >= 20
predictions in each half.

Null hypothesis: r <= 0.10 (ELO is noise)

Why this matters: If ELO doesn't predict future Brier score,
the entire signal-detection system is built on noise.
This is the most important question in the system.

---

**RQ1.2 — Skill Tier Stability**
Hypothesis: Traders who reach legendary tier (ELO > 2175)
stay there. Reaching legendary is not random noise.

Test: For all traders who reached ELO > 2175 at any point,
measure what fraction are still above 2175 after 60 days,
90 days, 180 days.

Data: traders table (ELO history if available),
trades table (timestamps)

Success criterion: > 70% of legendary traders remain
above ELO 1800 after 90 days.

Null hypothesis: ELO tier assignment is transient
(< 50% retention after 90 days)

Why this matters: If legendary status is transient,
the signal-agent's watch list needs a stability filter,
not just a threshold filter.

---

**RQ1.3 — Composite Score vs ELO Alone**
Hypothesis: The 8-dimension composite score predicts
future performance better than ELO alone.

Test: For the 304 traders currently ABOVE AVERAGE,
compare predictive accuracy of:
  A) ELO score alone
  B) Composite score (ELO + Brier + Sharpe + behavioral)
Using out-of-sample market resolutions.

Data: composite_scores CSV, positions table,
markets table (resolved outcomes)

Success criterion: Composite score shows >= 15% lower
Brier score on out-of-sample predictions vs ELO alone.

Null hypothesis: Composite score adds no predictive
power over ELO alone (<5% improvement)

Why this matters: If composite score doesn't improve
on ELO, the complexity of Phase 3b is not justified.
If it does, it should replace ELO as the primary
signal threshold.

---

### Category 2 — Signal Quality and Entry Timing
*Does following elite traders actually work?
Under what conditions?*

**RQ2.1 — Elite Convergence Edge**
Hypothesis: When 3+ legendary traders (ELO > 2175) enter
the same side of a market within 48 hours, the market
resolves in that direction more than 65% of the time.

Test: Identify all historical instances of 3+ legendary
traders entering same side within 48 hours.
Measure resolution rate in predicted direction.

Data: trades table (timestamps, outcome direction),
traders table (ELO scores),
markets table (winning_outcome)

Success criterion: > 65% resolution rate in signal direction
across >= 30 historical instances.

Null hypothesis: Resolution rate <= 55% (no meaningful edge
over market price)

Important control: Compare to market price at signal time.
Edge must exceed what the market already implies.

Why this matters: This is what signal-agent is built to
detect. If the edge doesn't exist historically, the
entire signal detection architecture needs rethinking.

---

**RQ2.2 — Entry Timing Advantage**
Hypothesis: Legendary traders enter positions earlier
in a market's price movement than elite traders,
who enter earlier than standard traders.

Test: For each resolved market, calculate the market
price at time of entry for each trader tier.
Measure average entry price vs final resolution price.
Better traders should show larger price movement
in their favour after entry.

Data: trades table (entry price, timestamp),
traders table (ELO tiers),
markets table (resolution price, winning_outcome)

Success criterion: Legendary traders show >= 15%
better average entry price vs resolution price
compared to standard traders.

Null hypothesis: No significant difference in entry
timing across ELO tiers (< 5% difference)

Why this matters: If legendary traders aren't entering
earlier/better, they may be winning through position
sizing or market selection, not timing. This changes
what the signal-agent should be detecting.

---

**RQ2.3 — Signal Decay Rate**
Hypothesis: The predictive value of an elite convergence
signal decays over time — signals are more accurate
closer to market resolution.

Test: Bin all historical signals by time remaining
until market resolution at signal time:
  > 30 days remaining
  15-30 days remaining
  7-15 days remaining
  < 7 days remaining
Measure resolution accuracy in each bin.

Data: trades table (timestamps),
markets table (resolution_date, winning_outcome),
traders table (ELO)

Success criterion: Measurable monotonic increase in
accuracy as time-to-resolution decreases.

Null hypothesis: Accuracy is uniform across time bins
(signals are equally good at any point in market life)

Why this matters: If accuracy increases near resolution,
the signal-agent should weight recent signals more
heavily and potentially reduce position sizing for
early-life signals. This directly affects Kelly sizing.

---

### Category 3 — Calibration and Probability Estimation
*Are prices right? Are our traders right?
Where is the systematic mispricing?*

**RQ3.1 — Market Category Calibration**
Hypothesis: ELO-weighted trader predictions are better
calibrated in some market categories than others.

Test: Calculate Brier score for ELO-weighted consensus
predictions separately for each market category:
Political / Economic / Sports / Crypto / Other

Data: positions table, markets table (category, outcome),
traders table (ELO)

Success criterion: At least one category shows Brier < 0.10,
at least one shows Brier > 0.20, confirming meaningful
category-level variation.

Null hypothesis: Brier scores are uniform across
categories (< 0.03 range between best and worst)

Why this matters: Category-specific calibration means
the system should apply different confidence thresholds
per category. A signal in a well-calibrated category
deserves higher conviction than one in a poorly
calibrated category.

---

**RQ3.2 — Crowd vs Elite Divergence**
Hypothesis: When the market price and the ELO-weighted
elite consensus diverge by > 10%, the elite consensus
is more accurate than the market price.

Test: Identify all resolved markets where ELO-weighted
elite consensus differed from market price by > 10%.
Measure which was closer to the resolution outcome.

Data: trades table (entry prices, trader positions),
traders table (ELO > 1800),
markets table (winning_outcome)

Success criterion: Elite consensus within 10% of
resolution outcome more often than market price,
across >= 50 historical instances.

Null hypothesis: Market price is more accurate than
elite consensus (markets are efficient)

Why this matters: If markets are already efficient
relative to elite trader consensus, the entire
signal-detection premise fails. This test either
validates the core premise or invalidates it.

---

**RQ3.3 — Contrarian Signal Value**
Hypothesis: When a trader with ELO > 2000 AND patience_score
> 0.7 takes the opposite side from the crowd,
they are right more than 60% of the time.

Test: Identify trades where high-ELO high-patience
traders entered the minority side of a market
(less than 40% of volume).
Measure their resolution accuracy.

Data: trades table, traders table (ELO, patience_score),
markets table (winning_outcome, total_volume)

Success criterion: > 60% accuracy for this specific
trader/behaviour combination.

Null hypothesis: Contrarian trades by high-ELO traders
show no edge over 50% baseline.

Why this matters: Patience score measures willingness
to wait for good odds. A patient high-ELO trader
taking a contrarian position is a qualitatively
different signal than a high-ELO trader following
the crowd. If this signal is real, it should get
a distinct signal type in signal-agent.

---

### Category 4 — Position Sizing and Kelly Optimality
*Are the best traders already Kelly-optimal?
What does optimal sizing look like in practice?*

**RQ4.1 — Kelly Alignment vs Outcomes**
Hypothesis: Traders with higher kelly_alignment_score
show better risk-adjusted returns (higher Sharpe ratio).

Test: Correlate kelly_alignment_score with Sharpe ratio
across all traders who have both metrics.

Data: traders table (kelly_alignment_score),
risk analysis results (Sharpe ratio)

Success criterion: Pearson r > 0.20 between
kelly_alignment_score and Sharpe ratio.

Null hypothesis: r <= 0.05 (Kelly alignment has no
relationship with risk-adjusted returns)

Why this matters: If Kelly alignment doesn't predict
Sharpe ratio, the kelly_alignment_score metric needs
redesigning. If it does, it validates using it as a
signal quality filter.

---

**RQ4.2 — Overbetting vs Underbetting**
Hypothesis: Most traders lose money by overbetting
high-probability events rather than underbetting.

Test: Classify each closed position as:
  Overbetting: position_size > Kelly_optimal * 1.5
  Underbetting: position_size < Kelly_optimal * 0.5
  Approximately optimal: within Kelly range
Measure average P&L for each category.

Data: positions table (size, entry_price, pnl),
markets table (winning_outcome)
Kelly optimal = derived from entry price and outcome

Success criterion: Overbetting positions show
negative average P&L despite correct direction
(overbetting is killing profits even when right)

Null hypothesis: Position sizing has no relationship
with P&L independent of direction.

Why this matters: If overbetting is the main source
of losses, the most valuable thing the system can
do is enforce Kelly discipline, not find better signals.
This determines the priority of signal quality vs
sizing discipline in the system architecture.

---

**RQ4.3 — Optimal Fraction Empirically**
Hypothesis: The empirically optimal Kelly fraction
for Polymarket is between 0.25x and 0.5x full Kelly.

Test: For all legendary traders, back-calculate what
Kelly fraction they implicitly used (position_size
relative to implied Kelly optimal at entry).
Measure correlation between implied fraction and
subsequent P&L.

Data: positions table, trades table (entry prices),
traders table (ELO > 2175)

Success criterion: Identify the Kelly fraction range
(e.g. 0.3x-0.6x) that maximises risk-adjusted returns
empirically across legendary traders.

Why this matters: The brain currently specifies
0.5x Kelly as the default. This test either validates
that assumption or replaces it with an empirically
derived value specific to Polymarket.

---

**RQ4-MULTI — Multivariate Kelly for Correlated Positions**
Hypothesis: Standard single-asset Kelly applied independently to correlated Polymarket
positions systematically overfits and risks ruin when correlated events co-resolve.
A multivariate Kelly optimisation using the O(N) integral transform (arXiv:2604.24723)
will produce more robust sizing by accounting for the 933 high-correlation pairs already
in correlation_cache.json.

Test: Implement multivariate Kelly using the integral transform approach from
arXiv:2604.24723. Apply to historical position data using the 933 high-correlation pairs
as the correlation structure input. Compare simulated blow-up risk vs independent
single-asset Kelly on the same positions.

Data: positions table, correlation_cache.json (high_correlation_pairs)

Success criterion: Multivariate Kelly reduces max drawdown in simulated portfolio vs
independent Kelly by > 10% while maintaining similar expected return.

Null hypothesis: Correlation structure is already captured by independent Kelly on each
position (i.e., correlated positions do not materially change optimal sizing).

Why this matters: The 933 high-correlation pairs are a documented systemic risk (RQ5.1).
When correlated positions co-resolve unexpectedly, independent Kelly fails. The O(N)
integral transform (arXiv:2604.24723) makes this tractable for hundreds of simultaneous
positions. The correlation data structure (correlation_cache.json) already exists —
the algorithm input is ready.

Priority: Phase 4+ — do not implement before RQ4.1–4.3 are complete and Phase 5 gate
criteria are met. This is position sizing infrastructure; signal quality must be
validated first.

Reference: arXiv:2604.24723 (approved research-scout 2026-04-30). See
brain/reference-library/ for implementation notes once Phase 4 begins.

---

### Category 5 — Correlation and Portfolio Risk
*How do positions interact?
What does a well-diversified Polymarket portfolio look like?*

**RQ5.1 — Correlated Market Blow-Up Risk**
Hypothesis: The 933 high-correlation pairs represent
genuine systemic risk — when one resolves unexpectedly,
correlated markets also move against the consensus.

Test: For each of the 933 high-correlation pairs,
measure whether an unexpected resolution in market A
(price moved > 20% in last 24 hours before resolution)
was preceded or followed by large price moves in
correlated market B.

Data: trades table (price history),
correlation_cache.json (high_correlation_pairs),
markets table (resolution outcomes)

Success criterion: > 60% of unexpected resolutions
in market A are accompanied by > 10% price moves
in correlated market B within 48 hours.

Null hypothesis: Correlations in price history don't
predict co-movement around resolution events.

Why this matters: If correlated markets co-move at
resolution, a position in market A implicitly adds
exposure to market B. The system needs to account
for this in position sizing — Kelly should be
adjusted downward when holding correlated positions.

---

**RQ5.2 — Copy Trader Contamination**
Hypothesis: Copy traders (the 102 identified in the
correlation network) are systematically degrading
the quality of the elite consensus signal.

Test: Run RQ2.1 (elite convergence edge) twice:
  A) Including all legendary traders
  B) Excluding the 102 identified copy followers
Compare signal accuracy between A and B.

Data: trades table, traders table (ELO),
correlation_cache.json (copy_relationships)

Success criterion: Version B shows >= 5% higher
accuracy than version A.

Null hypothesis: Removing copy traders has no effect
on signal accuracy (< 2% difference).

Why this matters: If copy traders are diluting the
signal, the signal-agent should explicitly exclude
them from convergence counting. A convergence of
5 legendary traders is much weaker if 3 of them
are copying a fourth.

---

### Category 6 — Regime Detection
*Does the system work across different market conditions?
When does it break down?*

**RQ6.1 — Bull vs Uncertainty Regime**
Hypothesis: Elite trader signal accuracy is higher
in high-volume markets (liquid) than low-volume
markets (illiquid).

Test: Bin all resolved markets by total volume:
  High: > $100k
  Medium: $10k-$100k
  Low: < $10k
Measure elite consensus accuracy in each bin.

Data: markets table (volume, winning_outcome),
trades table (trader positions),
traders table (ELO)

Success criterion: High-volume markets show Brier
score at least 0.05 lower than low-volume markets
for elite trader consensus predictions.

Null hypothesis: Volume has no relationship with
elite consensus accuracy.

Why this matters: If elite traders are more accurate
in liquid markets, the signal-agent should apply
a volume filter — don't fire signals on low-volume
markets regardless of elite convergence.

---

**RQ6.2 — Near-Resolution Mispricing**
Hypothesis: In the final 20% of a market's lifetime,
prices systematically underprice the leading outcome
(markets are slow to fully price in near-certain outcomes).

Test: For all resolved markets, calculate the market
price at the 80% lifetime mark. Measure how often
the price at 80% lifetime underestimates the final
resolution probability.

Data: trades table (prices at various timestamps),
markets table (creation date, resolution date, outcome)

Success criterion: Price at 80% lifetime underestimates
final resolution price by > 5 percentage points on
average across all resolved markets.

Null hypothesis: No systematic bias — prices at 80%
lifetime are already at final resolution price
(markets are efficient near resolution).

Why this matters: If late-stage prices systematically
underprice certainty, there is a mechanical edge
in buying near-certain outcomes in final 20% of
market life. This is a strategy, not just a signal.

---

### Category 7 — Market Efficiency Creep
*As leaderboard visibility grows, does broadcasting ELO signals
degrade the edge those signals are based on?*

**RQ7.1 — Signal Crowding Detection**
Hypothesis: As copy trading and leaderboard visibility have grown,
simple top-wallet following is being front-run in real time.
At some point, ELO signal broadcasting degrades its own edge
by attracting enough followers to move the market before position
entry is complete.

Background: PolyTrack, Kiyotaka, Polycool, and HashDive all
surface elite wallet activity with varying latency. As these tools
proliferate, the window between a legendary trader entering a position
and the copy-following crowd reacting is shrinking. A signal that
had a 30-minute entry window in 2024 may have a 5-minute window
by Phase 6. The ELO edge is in identifying the signal; the timing
edge is the moat that competition erodes.

Test: For all resolved markets, measure the time lag between first
legendary trader entry and subsequent volume spike (>2x baseline).
Track this lag over calendar time (2024 vs 2025 vs 2026).
Hypothesis: the lag is shrinking monotonically.

Secondary test: measure whether entry price disadvantage for followers
(entering after the legendary trader) has grown over time. If the
market moves further against followers on entry, crowding is confirmed.

Data: trades table (timestamps, prices, volumes),
traders table (ELO tiers),
markets table (creation date, category)

Success criterion: Measurable reduction in entry lag over time
AND measurable increase in price slippage for follow-on entry.

Null hypothesis: Entry lag and slippage are stable over time
(crowding is not yet affecting signal quality).

Implications for build decisions:
- If crowding is confirmed, the moat response is longitudinal ELO
  trajectory (not available to leaderboard scrapers) and pre-resolution
  intelligence (news-to-signal layer) — both identify position intent
  before public entry is visible.
- Static leaderboard copying degrades; trajectory-aware calibrated
  skill scoring does not. This validates the Direction 10 build priority.
- Flag for Phase 5 paper trading validation: measure live entry lag
  vs the historical baseline established here.

Flag: Phase 5 paper trading validation. Do not build mitigation
before measuring the problem.

---

### Priority Order for Quant-Research Agent

Run these in this order. Earlier questions validate
the foundations that later questions build on.
If RQ1.1 fails (ELO doesn't predict future Brier),
stop and redesign the ELO system before proceeding.

**Week 1-2:**
RQ1.1 — ELO persistence (foundational validity test)
RQ2.2 — Entry timing advantage (validates signal premise)
RQ3.2 — Crowd vs elite divergence (validates core premise)

**Week 3-4:**
RQ1.2 — Skill tier stability
RQ2.1 — Elite convergence edge (main signal test)
RQ4.1 — Kelly alignment vs Sharpe

**Week 5-6:**
RQ3.1 — Category calibration
RQ2.3 — Signal decay rate
RQ5.2 — Copy trader contamination

**Week 7-8:**
RQ4.2 — Overbetting analysis
RQ6.2 — Near-resolution mispricing
RQ1.3 — Composite score vs ELO

**Week 9-12:**
Remaining questions + synthesis
Begin building trading strategies based on validated findings

---

### Stopping Rules

If any of these fail, stop and reassess before continuing:

**STOP if RQ1.1 fails:** ELO has no predictive validity.
The monitoring system needs fundamental redesign.

**STOP if RQ3.2 fails:** Markets are efficient relative
to elite consensus. The signal premise is wrong.
Pivot to different edge source.

**STOP if RQ2.1 shows < 55% accuracy:** Elite convergence
signals have no edge. Signal-agent architecture is wrong.

These are not setbacks — they are the most valuable
possible findings. A system that knows what doesn't
work is worth more than one that doesn't know.

---

### What Success Looks Like

After 12 weeks of quant-research-agent running these
questions systematically, the system should be able
to answer:

"In market category X, when Y or more legendary traders
with composite score > Z enter the same side with
volume > V, and the market has > W% lifetime remaining,
and copy traders are excluded, the historical edge is
E% with Brier score B and Sharpe ratio S."

That sentence, filled in with real validated numbers,
is a trading strategy. Everything before it is
research infrastructure.

---

## Nous Research / Hermes Agent — Open-Weight Agentic Fine-Tuning

Source: @nousr_computer, @jquesnelle (added April 2026)

Nous Research's Hermes series represents the leading open-weight
approach to instruction-following and agentic task performance.
Hermes 3 on Llama 3.1 70B outperforms base Llama on:
- Structured output adherence (JSON schemas, function call formats)
- Multi-turn instruction following (critical for agent prompt templates)
- Tool-use reliability (signals.json format, task template parsing)

**Research question (non-blocking, Phase 3+):**
Can a Hermes 3 (or Hermes 4 when released) checkpoint replace
Claude Haiku 4.5 as the Tier 2.5 model for structured tasks
(integration-test-agent, research-scout-agent), reducing API cost
to zero for that tier?

Benchmark criteria (when evaluated):
- JSON schema adherence rate: must match or exceed Haiku 4.5
- Inference speed on UM890 Pro: must be under 15s per agent call
- Agent prompt template following: must pass integration-test suite
- If all three pass: propose Tier 2.5 routing change to Oscar

**Do not evaluate prematurely.** Wait until Nous releases a Hermes
checkpoint on a Llama 4-class base or equivalent. Current Hermes 3
on Llama 3.1 70B is a candidate but has not been benchmarked locally.
research-scout-agent will escalate when a relevant new release appears.

---

## Exit Timing Intelligence — Pre-Resolution Layer Gap

91% of top wallet exits happen before resolution.
Average exit captures 73% of max potential profit.
Primary trigger: volume spike within 10 minutes.
Secondary: price target at ~85% of estimated gap.

Add volume spike monitoring to pre-resolution signals.
3x normal volume in 10-minute window + elite open positions
= smart money exit. Flag as close signal, not open signal.

## NEAR_RESOLUTION Bot Type — Fourth Classification

Buys near-certain outcomes (98-99c) before settlement.
High win rate but structural not predictive edge.
Following them gives worse fills on tiny margin.
Classify separately — do not follow into positions.
Already confirmed in bot_detection.py RQ0.2 work.

## Sports Markets — Deprioritise

52% win rate for systematic approaches on sports.
Geopolitics and macro is where edge exists.
Category filter must exclude sports in Phase 6.

---

## Validated Geopolitics Trader Watch List

Live examples of real-world geopolitics edge — use these to calibrate
what skill looks like in the category this system targets.

**@wickier** — polymarket.com/@wickier
Strategy: buys $10K-$95K on conflict outcomes at 2¢-18¢ odds.
Returns: 800%-2,000% per trade.
Best single trade: $9,951 → $217,308 (+2,083%) on Iran/Israel/US conflict.
All-time P&L: $660,484. 919 predictions logged.
Significance: real-world validation that geopolitics at low odds is where
the edge exists — exactly the category this system targets. The position
sizing ($10K-$95K range) and the odds range (2¢-18¢) are the empirical
benchmarks for what informed geopolitics trading looks like in practice.
Cross-reference against ELO system when geopolitics wallet data is pulled.

---

## Resolution-Zone Orderbook Thinning — New Pre-Resolution Signal Candidate

**Identified:** 2026-05-12 (research-scout pending-review)
**Source:** arXiv:2605.10400 — Polymarket resolution-zone microstructure analysis, 13,115 markets

**The finding:** Polymarket orderbooks show "boundary depth asymmetry" — one side of the book
thins predictably before resolution. In the final 24 hours, the thinning side correlates with
the eventual resolution direction. This is independent of ELO signals.

**Proposed RQ (pre-registration required before test):**
In the 24 hours before resolution, does the YES/NO depth ratio predict the resolution direction?
Test on PMXT v2 archive (archive.pmxt.dev, Parquet snapshots from 2026-04-13, 13,115 markets).

**Backtest rule addition:** Any strategy that holds positions into the final 24h before resolution
must be flagged for terminal-jump slippage risk (non-continuous price jumps documented).

**Phase:** 4-5. Do not build before signal-layer validation is complete.
**Data requirement:** Orderbook depth data — not available in local DB. Requires PMXT v2 archive.

---

## PMXT — Unified Prediction Market SDK + Free Historical Data Archive

**Identified:** 2026-05-12 (research-scout pending-review)
**Source:** github.com/pmxt-dev/pmxt — v2.40.5, MIT license, 1.7k stars

**What it provides:**
- Unified API across 10+ prediction markets (Polymarket, Kalshi, Limitless, Metaculus, etc.)
- Free Parquet data archive at archive.pmxt.dev: hourly snapshots from 2026-04-13, millisecond
  timestamps, 110,828+ markets
- Potential Phase 6 execution layer: supports both Polymarket and Kalshi limit orders

**Relevance to current research:**
- quant-research-agent can use Parquet archive for resolution-zone research (above) and
  any tick-level analysis not available in local DB
- Cross-platform signals: Kalshi vs Polymarket price divergence on same event = potential alpha
- Pending Oscar review before any integration (check vs integration-contract.md)

**Reference:** brain/research-scout/pending-review/2026-05-12-08-pmxt-unified-prediction-market-sdk-free-data-archive.md

---

## Insider Trading Methodology — ELO Pool Sharpening (arXiv 2605.02287)

**Identified:** 2026-05-19 (research-scout pending-review)
**Source:** arXiv:2605.02287 — "Per-Market Information Leakage and Order-Flow Skill"

**The finding:** Applied to Polymarket across 93,000+ markets and 210,000 wallet-market pairs:
- 3.14% of accounts classified as "skilled winners" (systematic positive edge)
- 1,950 accounts flagged as likely insiders
- Composite insider screen: 69.9% win rate on flagged trades
- Methodology uses per-market information leakage score + order flow skill decomposition

**Relevance to current system:**
- Directly relevant to RQ3.2 (elite consensus signal quality) — the 69.9% insider win rate
  independently validates the ELO-based approach and provides a competing methodology for
  benchmarking
- ELO pool construction: could sharpen pool by selecting skilled insiders as confirmed signal
  sources, or filtering adversarial actors to avoid being on the wrong side of their trades
- Lifecycle heuristic (LH-001) complements this: new accounts within 30d of resolution + this
  paper's skilled-winner screen = compound insider detection layer
- Must read before RQ3.2 June 2026 follow-up to incorporate relevant methodology upgrades

**Pre-registration required** before any empirical test comparing this methodology to ELO.

**Reference:** brain/research-scout/pending-review/2026-05-19-17-per-market-information-leakage-and-order-flow-skil.md  
**Priority:** HIGH — pending Oscar review

---

## ForesightFlow — Per-Market Information Leakage Score (arXiv 2605.00493)

**Identified:** 2026-05-19 (research-scout pending-review)
**Source:** arXiv:2605.00493 — "ForesightFlow: Information Leakage Score Framework"

**The finding:** Introduces a per-market Information Leakage Score (ILS) quantifying how much
early order flow predicts resolution outcomes. Markets with high ILS have detectable pre-
resolution information asymmetry.

**Relevance to current system:**
- market-builder-agent market selection: filter for high-ILS markets to improve signal quality
- Signal weighting: downweight signals from low-ILS markets where noise dominates
- Complements ELO ranking — ELO identifies WHO has edge, ILS identifies WHICH MARKETS have
  detectable information flow. Combining both creates a two-axis quality filter.
- Directly applicable to STR-003 and STR-004 signal confidence scoring

**Pre-registration required** before any empirical ILS calculation on local DB.

**Reference:** brain/research-scout/pending-review/2026-05-19-17-foresightflow-information-leakage-score-framework-.md  
**Priority:** HIGH — pending Oscar review

---

## Community Tool Directories — Research-Scout Monitoring

The most complete community-maintained indexes of prediction market tools.
Research-scout-agent should check both weekly for new entries and flag
anything relevant to competitive-moat.md or this file.

**github.com/aarora4/Awesome-Prediction-Market-Tools**
Broadest coverage — Polymarket, Kalshi, Manifold, and adjacent tools.
Preferred source for cross-platform competitive intelligence.

**github.com/harish-garg/Awesome-Polymarket-Tools**
Polymarket-specific curated index. More focused; useful for catching
new entrants in the core competitive space before they gain traction.

Monitoring instruction: check both repos weekly. If a new tool appears
that overlaps with ELO tracking, wallet clustering, informed trader
detection, or pre-resolution intelligence — escalate via signals.json
with signal_type: COMPETITIVE_ALERT before the weekly digest.

---

## Future Agent Concept — Pattern Recognition Agent

Concept: A swarm agent that performs cross-contextual pattern recognition across
all data sources — not running pre-registered experiments, but surfacing anomalies
and connections that domain-specific agents working in isolation would miss.

Examples of what it would catch:
- Trader appearing in geo_elo LEGENDARY tier AND resolution sweep AND insider_signals simultaneously
- Sudden clustering of new wallets on a specific geopolitics market before resolution
- Market structure changes (volume spike + directional concentration + new wallet activity)
- Cross-referencing findings.json entries for emerging patterns across research threads

Distinction from existing agents:
- quant-research-agent: runs pre-registered experiments
- signal-agent: applies known strategies to live data
- pattern-recognition-agent: open-ended anomaly surfacing, no pre-registration required

Risks:
- High hallucination risk without pre-registration discipline
- Needs strong immune system integration (feedback.json as primary check)
- Output must be flagged as HYPOTHESIS not FINDING until validated

Prerequisites before building:
- geo_elo, Pool C, resolution sweep, insider_signals scoring all stable
- At least 3 months of pattern data to work with
- Pre-registration framework adapted for open-ended hypotheses

Status: CONCEPT — do not build until Phase 5 gates passed
