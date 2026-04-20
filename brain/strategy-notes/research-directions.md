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

- Nothing completed yet. Phase 1 (Brier score calibration)
  is the starting point.

---

## What Has Failed or Been Ruled Out
(Update this section as experiments conclude)

- Nothing ruled out yet.

---

## Compounding Notes
As the quant-research-agent completes phases, add key findings
here as one-line summaries so future research sessions start
with accumulated knowledge rather than from zero.

Example format:
- 2026-03-01: ELO >2175 traders show 340ms average entry
  advantage over market price movement. See phase-1-results.md


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
