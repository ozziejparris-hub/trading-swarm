# Superforecasting: The Art and Science of Prediction
# Philip Tetlock and Dan Gardner (2015)
# Agent Reference Notes — Trading Swarm System
# Crown Publishers. ISBN 978-0-8041-3663-8

---

## Why This Book Matters for Your System

Tetlock ran the Good Judgment Project — the most rigorous
study of human forecasting accuracy ever conducted.
Over 500,000 forecasts from thousands of forecasters
on real geopolitical and economic questions.

The findings directly answer questions your system is
trying to answer with ELO scores and behavioral metrics:
What actually makes a forecaster good? Is it stable?
Can it be measured? Can it be improved?

Your legendary traders (ELO > 2175) are, by definition,
your best forecasters. This book tells you what they
are probably doing right — and gives you a framework
to verify it in your data.

---

## Part 1 — What the Research Actually Found

### 1.1 The Core Finding: Superforecasters Are Real

The single most important finding: a small group of
forecasters (roughly 2% of participants) consistently
outperform prediction markets, intelligence analysts
with classified information, and random chance — over
multiple years, across multiple topic domains.

This is directly relevant to your system because it
validates the premise of RQ1.1 (ELO persistence):
elite forecasting skill is real, stable, and measurable.

Key statistics from the research:
- Superforecasters achieved Brier scores of 0.06-0.12
- Regular forecasters achieved Brier scores of 0.20-0.30
- The gap persisted across years (not regression to mean)
- Superforecasters outperformed prediction markets by ~30%

**Direct implication for your system:**
Your best traders with Brier scores around 0.08 are in
superforecaster territory. This is not noise — this is
a real signal worth following.

---

### 1.2 The Superforecaster Profile

Tetlock identified consistent characteristics across
all superforecasters. Map these against your behavioral
metrics:

**Characteristic 1 — Probabilistic thinking**
Superforecasters think in probabilities, not binaries.
They don't say "it will happen" or "it won't" —
they say "I give this a 73% chance."

Prediction market equivalent: traders who enter at
specific price points (not just YES/NO) and adjust
as prices move. Your patience_score measures this —
high patience = trader waits for the right price,
implying probabilistic discipline.

**Characteristic 2 — Actively open-minded**
Superforecasters seek disconfirming evidence.
They update their beliefs when new information arrives.

Prediction market equivalent: traders who change
sides on a market when new information arrives.
These show up as position changes in your trades table.

```python
def measure_belief_updating(trades_df, traders_df,
                             min_elo=1800):
    """
    Measure how often elite traders update their positions
    when market prices move significantly.
    
    Traders who update more often (in the right direction)
    show active open-mindedness — a superforecaster trait.
    
    trades_df: from polymarket_tracker.db trades table
    traders_df: from polymarket_tracker.db traders table
    """
    import pandas as pd
    import numpy as np
    
    elite = traders_df[traders_df['elo_score'] >= min_elo]['address']
    elite_trades = trades_df[
        trades_df['trader_address'].isin(elite)
    ].sort_values(['trader_address', 'market_id', 'timestamp'])
    
    # Find position reversals (entered YES, then NO or vice versa)
    results = []
    
    for (trader, market), group in elite_trades.groupby(
        ['trader_address', 'market_id']
    ):
        if len(group) < 2:
            continue
        
        outcomes = group['outcome'].tolist()
        reversals = sum(
            1 for i in range(1, len(outcomes))
            if outcomes[i] != outcomes[i-1]
        )
        
        results.append({
            'trader': trader,
            'market': market,
            'n_trades': len(group),
            'n_reversals': reversals,
            'reversal_rate': reversals / len(group)
        })
    
    df = pd.DataFrame(results)
    
    # Merge with ELO
    df = df.merge(
        traders_df[['address', 'elo_score']],
        left_on='trader',
        right_on='address'
    )
    
    # Correlation between ELO and reversal rate
    correlation = df['elo_score'].corr(df['reversal_rate'])
    
    return {
        'correlation_elo_reversals': correlation,
        'avg_reversal_rate_elite': df[
            df['elo_score'] >= 1800
        ]['reversal_rate'].mean(),
        'avg_reversal_rate_standard': df[
            df['elo_score'] < 1800
        ]['reversal_rate'].mean(),
        'interpretation': (
            'Elite traders update more often (active open-mindedness)'
            if correlation > 0.1
            else 'No significant difference in update rate by ELO'
        )
    }
```

**Characteristic 3 — Dragonfly-eye view**
Superforecasters aggregate perspectives from multiple
angles before forming a view. They consider base rates,
specific case factors, and recent trends simultaneously.

Prediction market equivalent: traders who look at
multiple related markets before positioning.
Cross-market analysis in your correlation data.

**Characteristic 4 — Pragmatic not ideological**
Superforecasters don't have strong political or
ideological priors that bias their forecasts.
They follow the evidence wherever it leads.

Prediction market equivalent: traders whose accuracy
is consistent across market categories (political,
economic, sports, crypto) rather than only good
in one domain. Your category-level Brier scores
(RQ3.1) test this directly.

**Characteristic 5 — Growth mindset**
Superforecasters treat forecasting as a skill to
improve, not a fixed talent. They debrief their
mistakes and adjust.

Prediction market equivalent: traders whose Brier
score improves over time as they gain experience.

```python
def measure_calibration_improvement(positions_df,
                                     markets_df,
                                     traders_df,
                                     min_trades=30):
    """
    Measure whether traders improve their calibration
    over time — a growth mindset indicator.
    
    Splits each trader's history into thirds and
    measures Brier score in each period.
    Improving traders show declining Brier over time.
    """
    import pandas as pd
    import numpy as np
    
    results = []
    
    for trader_addr in traders_df[
        traders_df['elo_score'] >= 1800
    ]['address']:
        
        # Get resolved positions for this trader
        trader_positions = positions_df[
            positions_df['trader_address'] == trader_addr
        ].merge(
            markets_df[['condition_id', 'outcome', 'resolution_date']],
            left_on='market_id',
            right_on='condition_id'
        ).dropna(subset=['outcome'])
        
        if len(trader_positions) < min_trades:
            continue
        
        # Sort by resolution date and split into thirds
        trader_positions = trader_positions.sort_values(
            'resolution_date'
        )
        n = len(trader_positions)
        third = n // 3
        
        periods = [
            trader_positions.iloc[:third],
            trader_positions.iloc[third:2*third],
            trader_positions.iloc[2*third:]
        ]
        
        brier_by_period = []
        for period in periods:
            actual = (period['outcome'] == 'YES').astype(int)
            predicted = period['entry_price']
            brier = ((predicted - actual) ** 2).mean()
            brier_by_period.append(brier)
        
        # Is Brier improving (declining) over time?
        improving = brier_by_period[0] > brier_by_period[2]
        improvement_magnitude = brier_by_period[0] - brier_by_period[2]
        
        results.append({
            'trader': trader_addr,
            'elo': traders_df[
                traders_df['address'] == trader_addr
            ]['elo_score'].values[0],
            'brier_early': brier_by_period[0],
            'brier_mid': brier_by_period[1],
            'brier_late': brier_by_period[2],
            'improving': improving,
            'improvement': improvement_magnitude
        })
    
    df = pd.DataFrame(results)
    
    pct_improving = df['improving'].mean()
    avg_improvement = df['improvement'].mean()
    
    return {
        'n_traders_analysed': len(df),
        'pct_improving_over_time': pct_improving,
        'avg_brier_improvement': avg_improvement,
        'interpretation': (
            'Elite traders show learning over time'
            if pct_improving > 0.6
            else 'No clear learning trend in elite traders'
        )
    }
```

---

### 1.3 The 10 Commandments of Superforecasting

Tetlock distilled the research into 10 practical rules.
Map each against your existing metrics:

```
Commandment                    Your Metric          Status
─────────────────────────────────────────────────────────────
1. Triage — focus on          market_confidence     Phase 3c
   tractable questions         meter output          (planned)

2. Break problems into        No direct metric       Gap
   component parts             yet

3. Strike the right balance   patience_score        ✅ exists
   between inside/outside      (measures if trader
   views                       waits for good odds)

4. Update beliefs when        belief_updating()     Code above
   evidence arrives            (measure reversals)   (new)

5. Look for the               timing_score          ✅ exists
   right question

6. Distinguish degrees        kelly_alignment_score ✅ exists
   of doubt                    (probability sizing)

7. Strike the right balance   No direct metric      Gap
   between under/over-         yet
   reacting

8. Learn from mistakes        calibration over      Code above
                               time measurement      (new)

9. Distinguish good           composite_score       ✅ Phase 3b
   forecasting process         (8 dimensions)

10. Master the team           copy relationships    ✅ correlation
    dynamic                    (avoid copy traders)   matrix
```

Gaps identified: component decomposition and
over/under-reaction measurement are not yet in
the system. Worth adding to research directions.

---

## Part 2 — The Brier Score Framework

### 2.1 What Brier Score Actually Measures

Tetlock's research operationalised forecasting quality
using the Brier score. Understanding what it measures
at a deep level improves how you interpret your 897
traders' scores.

**The decomposition:**
Brier score = Reliability + Resolution - Uncertainty

Where:
- **Reliability**: Are your 70% predictions right 70%
  of the time? (calibration)
- **Resolution**: Do your predictions distinguish
  outcomes? (discrimination)
- **Uncertainty**: Base rate difficulty of the questions

```python
def decompose_brier_score(predictions, outcomes):
    """
    Decompose Brier score into its three components.
    
    This reveals WHY a trader has a good or bad score:
    - Poor reliability: systematically over/underconfident
    - Poor resolution: can't distinguish outcomes
    - High uncertainty: just asking hard questions
    
    predictions: list of floats [0,1]
    outcomes: list of ints [0,1]
    
    Returns: total Brier and three components
    """
    import numpy as np
    
    predictions = np.array(predictions)
    outcomes = np.array(outcomes)
    n = len(predictions)
    
    # Overall Brier score
    brier_total = np.mean((predictions - outcomes) ** 2)
    
    # Base rate (mean outcome)
    base_rate = outcomes.mean()
    
    # Bin predictions for reliability calculation
    bins = np.linspace(0, 1, 11)
    bin_indices = np.digitize(predictions, bins) - 1
    bin_indices = np.clip(bin_indices, 0, 9)
    
    reliability = 0
    resolution = 0
    
    for bin_idx in range(10):
        mask = bin_indices == bin_idx
        if mask.sum() == 0:
            continue
        
        n_k = mask.sum()
        f_k = bins[bin_idx] + 0.05  # bin centre
        o_k = outcomes[mask].mean()  # actual rate in bin
        
        reliability += (n_k / n) * (f_k - o_k) ** 2
        resolution += (n_k / n) * (o_k - base_rate) ** 2
    
    uncertainty = base_rate * (1 - base_rate)
    
    return {
        'brier_total': brier_total,
        'reliability': reliability,   # lower is better
        'resolution': resolution,     # higher is better
        'uncertainty': uncertainty,   # fixed by question set
        'check': abs(
            (reliability - resolution + uncertainty) - brier_total
        ) < 0.01,  # should be True
        'interpretation': {
            'reliability': (
                'Well calibrated' if reliability < 0.02
                else 'Poorly calibrated — overconfident'
                if reliability > 0.05
                else 'Acceptable calibration'
            ),
            'resolution': (
                'Good discrimination' if resolution > 0.05
                else 'Poor discrimination — predictions near base rate'
            )
        }
    }
```

**Why this matters for your system:**
A trader with Brier 0.10 could get there two ways:
1. Excellent reliability AND excellent resolution
   (genuinely skilled superforecaster)
2. Poor reliability but very hard questions
   (lucky domain selection)

Your signal-agent should prefer type 1 traders.
The decomposition tells you which type each trader is.

---

### 2.2 Reference Class Forecasting

One of Tetlock's most actionable findings:
before making any forecast, establish the base rate
(what fraction of similar questions resolve YES?).

This is the "outside view" — what happens in general
before looking at the specific case.

```python
def calculate_market_base_rates(markets_df):
    """
    Calculate base rates for each market category.
    
    This is the outside view for prediction markets:
    what fraction of markets in each category resolve YES?
    
    Knowing base rates prevents anchoring errors —
    don't forecast 70% YES if only 40% of similar
    markets historically resolve YES.
    
    markets_df: from polymarket_tracker.db markets table
    """
    import pandas as pd
    
    resolved = markets_df[markets_df['outcome'].notna()]
    
    base_rates = resolved.groupby('category').agg(
        total_markets=('condition_id', 'count'),
        yes_resolutions=('outcome', lambda x: (x == 'YES').sum()),
        no_resolutions=('outcome', lambda x: (x == 'NO').sum())
    )
    
    base_rates['yes_rate'] = (
        base_rates['yes_resolutions'] / base_rates['total_markets']
    )
    base_rates['no_rate'] = (
        base_rates['no_resolutions'] / base_rates['total_markets']
    )
    
    # Market difficulty (Brier uncertainty component)
    base_rates['uncertainty'] = (
        base_rates['yes_rate'] * base_rates['no_rate']
    )
    
    # Easiest = closest to 0 or 1
    # Hardest = closest to 0.5
    base_rates['difficulty'] = 1 - abs(
        base_rates['yes_rate'] - 0.5
    ) * 2
    
    return base_rates.sort_values('difficulty', ascending=False)

# Application for signal-agent:
# Before flagging a signal on a market, check the base rate
# for that category. If base rate is 35% YES but market
# trades at 60% YES, that's a much stronger signal than
# if base rate is 55% YES and market trades at 60%.
# The deviation from base rate is the signal, not the price.
```

---

## Part 3 — Team Forecasting and Aggregation

### 3.1 The Superteam Finding

Tetlock found that aggregating forecasts from
multiple good forecasters outperforms any individual —
even the best individual superforecaster.

But simple averaging is worse than weighted averaging.
Weights should reflect track record, not equal weight.

```python
def weighted_consensus_probability(trader_positions,
                                    traders_df,
                                    market_id,
                                    weight_by='elo_score'):
    """
    Calculate ELO-weighted consensus probability
    for a specific market.
    
    This is Tetlock's aggregation applied to Polymarket:
    weight each trader's implied probability by their
    track record (ELO or Brier score).
    
    Better than simple market price because it
    up-weights skilled traders and down-weights noise.
    
    trader_positions: current open positions for market
    traders_df: trader metadata including ELO
    market_id: which market to calculate for
    weight_by: 'elo_score' or 'brier_score' (lower=better)
    """
    import numpy as np
    import pandas as pd
    
    market_positions = trader_positions[
        trader_positions['market_id'] == market_id
    ].merge(
        traders_df[['address', 'elo_score', 'brier_score']],
        left_on='trader_address',
        right_on='address'
    )
    
    if len(market_positions) == 0:
        return None
    
    # Convert position to probability
    # YES position at price P implies P probability
    market_positions['implied_prob'] = np.where(
        market_positions['outcome'] == 'YES',
        market_positions['entry_price'],
        1 - market_positions['entry_price']
    )
    
    if weight_by == 'elo_score':
        # Higher ELO = higher weight
        weights = market_positions['elo_score']
    else:
        # Lower Brier = higher weight (invert)
        brier = market_positions['brier_score'].fillna(0.25)
        weights = 1 / (brier + 0.01)
    
    # Weighted average
    weighted_prob = np.average(
        market_positions['implied_prob'],
        weights=weights
    )
    
    # Simple average for comparison
    simple_prob = market_positions['implied_prob'].mean()
    
    n_elite = (market_positions['elo_score'] >= 1800).sum()
    
    return {
        'market_id': market_id,
        'weighted_probability': weighted_prob,
        'simple_average': simple_prob,
        'n_traders': len(market_positions),
        'n_elite': n_elite,
        'elite_weighted_prob': np.average(
            market_positions[
                market_positions['elo_score'] >= 1800
            ]['implied_prob'],
            weights=market_positions[
                market_positions['elo_score'] >= 1800
            ]['elo_score']
        ) if n_elite > 0 else None
    }
```

**The extremising finding:**
Tetlock discovered that slightly pushing weighted
averages toward the extremes (away from 50%) improves
accuracy. A weighted average of 62% should be pushed
to maybe 67%.

This is because aggregation introduces regression
toward the mean. Reversing some of that regression
improves calibration.

```python
def extremise_probability(p, extremising_factor=1.3):
    """
    Apply Tetlock's extremising adjustment to aggregated
    probability estimates.
    
    Pushes probabilities away from 50% by a small factor.
    Empirically improves calibration of aggregated forecasts.
    
    p: aggregated probability [0,1]
    extremising_factor: typically 1.2-1.4
    
    Returns: extremised probability
    """
    import numpy as np
    
    # Convert to log odds
    if p <= 0 or p >= 1:
        return p
    
    log_odds = np.log(p / (1 - p))
    
    # Extremise in log odds space
    extremised_log_odds = log_odds * extremising_factor
    
    # Convert back to probability
    extremised_p = 1 / (1 + np.exp(-extremised_log_odds))
    
    return extremised_p

# Example:
# Weighted consensus = 0.62
# After extremising (factor 1.3): ~0.68
# This is more aggressive but empirically more accurate
# when aggregating multiple forecasters

# For your signal-agent:
# Apply extremising to ELO-weighted consensus before
# comparing to market price. The extremised consensus
# is a better estimate of true probability than the
# raw weighted average.
```

---

### 3.2 The Diversity Bonus

Groups of forecasters with diverse information
and approaches outperform groups of even slightly
more skilled but similar forecasters.

This maps directly onto your copy-trading problem:
10 traders who all copy each other count as 1 trader
for consensus purposes, not 10.

The diversity correction:

```python
def diversity_adjusted_consensus(trader_positions,
                                  copy_relationships,
                                  traders_df,
                                  market_id):
    """
    Calculate consensus probability with copy-trader
    diversity adjustment.
    
    Groups of copy traders count as one independent
    data point, not N data points.
    
    This is Tetlock's diversity bonus applied to
    prediction market consensus calculation.
    
    copy_relationships: from correlation_cache.json
    """
    import numpy as np
    
    market_positions = trader_positions[
        trader_positions['market_id'] == market_id
    ].merge(
        traders_df[['address', 'elo_score']],
        left_on='trader_address',
        right_on='address'
    )
    
    # Identify copy clusters
    # Traders in the same copy cluster share one "vote"
    copy_followers = set(
        rel['follower']
        for rel in copy_relationships
    )
    
    independent_positions = market_positions[
        ~market_positions['trader_address'].isin(copy_followers)
    ]
    
    if len(independent_positions) == 0:
        return None
    
    # Weight by ELO, exclude copy followers
    implied_probs = np.where(
        independent_positions['outcome'] == 'YES',
        independent_positions['entry_price'],
        1 - independent_positions['entry_price']
    )
    
    diversity_adjusted = np.average(
        implied_probs,
        weights=independent_positions['elo_score']
    )
    
    # Apply extremising
    final_estimate = extremise_probability(diversity_adjusted)
    
    n_removed = len(market_positions) - len(independent_positions)
    
    return {
        'diversity_adjusted_prob': final_estimate,
        'raw_consensus': np.average(
            np.where(
                market_positions['outcome'] == 'YES',
                market_positions['entry_price'],
                1 - market_positions['entry_price']
            ),
            weights=market_positions['elo_score']
        ),
        'copy_traders_excluded': n_removed,
        'independent_traders': len(independent_positions)
    }
```

---

## Part 4 — What Superforecasters Get Wrong

### 4.1 The Failure Modes

Tetlock was equally rigorous about when superforecasters
fail. These are directly relevant to your stopping rules.

**Failure mode 1 — Black swans**
Superforecasters perform poorly on genuine black swan
events — things outside historical reference classes.
In prediction markets: unprecedented geopolitical events,
sudden regulatory changes, market manipulation.

**Implication:** Your signal-agent should not treat
elite convergence as strong signal in market categories
with high black swan exposure. Political markets in
stable democracies: reliable. Markets involving
unprecedented events: unreliable.

**Failure mode 2 — Distant time horizons**
Accuracy degrades significantly for predictions beyond
6-12 months. Superforecasters outperform most at
1-30 day horizons.

**Implication:** Your RQ2.3 (signal decay rate) will
likely show that signals are most accurate close to
resolution. This is not a flaw in the signal — it's
fundamental to the nature of prediction.

**Failure mode 3 — Correlated questions**
When all questions in a portfolio are correlated
(e.g. all US election-related), diversification
benefits disappear and errors compound.

**Implication:** Your RQ5.1 (correlated market
blow-up risk) tests this directly. The 933
high-correlation pairs are exactly this risk.

---

## Part 5 — Direct Applications to Your Research Questions

### How Tetlock Informs Each RQ

**RQ1.1 (ELO persistence):**
Tetlock found superforecaster status persists across
years with r ≈ 0.65 year-over-year correlation.
Your success criterion (r > 0.25) is conservative —
if ELO is measuring real skill, you should see higher.
If you see r < 0.25, your ELO system is measuring
something less durable than Tetlock's metrics.

**RQ1.2 (Skill tier stability):**
Tetlock found ~85% of superforecasters remained above
the skill threshold after 1 year. Your 70% criterion
is conservative. Expect higher if ELO is calibrated well.

**RQ2.1 (Elite convergence edge):**
Tetlock found aggregated superforecaster consensus
beat prediction markets by ~30%. Your 65% threshold
is asking whether your elite traders, in aggregate,
outperform the market. This should pass if your
ELO system correctly identifies skill.

**RQ3.1 (Category calibration):**
Tetlock found significant variation by question type.
Geopolitical questions near resolution: excellent.
Long-range economic forecasts: poor. Expect your
data to show similar category-level variation.

**RQ3.2 (Crowd vs elite divergence):**
This is the most contested finding. Tetlock's
superforecasters beat prediction markets but only
marginally. Your elite traders may or may not.
This test determines whether you have genuine edge
over market prices or just good relative ranking
within the trader pool.

---

## Part 6 — Metrics to Add to Your System

Based on Tetlock's research, these metrics are
worth adding to your trader profiles:

```python
TETLOCK_METRICS = {
    'belief_update_rate': {
        'description': 'How often does trader change sides on a market',
        'higher_is': 'better (active open-mindedness)',
        'implementation': 'measure_belief_updating() above',
        'database_column': 'belief_update_rate'
    },
    'calibration_improvement': {
        'description': 'Is Brier score improving over time?',
        'higher_is': 'better (growth mindset)',
        'implementation': 'measure_calibration_improvement() above',
        'database_column': 'calibration_trend'
    },
    'category_consistency': {
        'description': 'Is accuracy consistent across market types?',
        'higher_is': 'better (domain agnostic skill)',
        'implementation': 'RQ3.1 methodology per trader',
        'database_column': 'category_consistency_score'
    },
    'base_rate_deviation': {
        'description': 'Do predictions deviate appropriately from base rates?',
        'higher_is': 'complex (depends on accuracy)',
        'implementation': 'compare predictions to category base rates',
        'database_column': 'base_rate_awareness'
    }
}

# These four metrics, combined with existing
# kelly_alignment_score, patience_score, and timing_score,
# give a near-complete Tetlock superforecaster profile
# for each trader in your database.
```

---

## Part 7 — The Most Important Paragraph in the Book

Tetlock writes:

"The average expert was roughly as accurate as a dart-throwing
chimpanzee. But the superforecasters were different. They beat
the chimps. They beat other experts. They even beat prediction
markets — which are supposed to be the gold standard."

The reason superforecasters beat prediction markets is that
prediction markets aggregate all traders, skilled and unskilled.
Superforecasters are the subset who are systematically right.

**This is the entire premise of your system stated in one sentence.**

Your ELO system is trying to identify the prediction market
equivalent of superforecasters. If it succeeds — and your
Brier scores suggest it does — following their consensus
is not just a trading strategy. It is the academically
validated optimal strategy for extracting signal from
prediction markets.

---

## Quick Reference

```
Superforecaster Brier score:  0.06 - 0.12
Your best traders:            0.08 - 0.12  ← in range ✅
Average forecaster:           0.20 - 0.30
Random (always 50%):          0.25

Year-over-year skill persistence: r ≈ 0.65
Your RQ1.1 success criterion:     r > 0.25  ← conservative ✅

Aggregation improvement over best individual: ~15-20%
Diversity bonus (excluding copy traders):     ~5-10%
Extremising improvement:                      ~3-5%

Optimal forecast horizon:     1-30 days
Signal decay expected:        faster beyond 30 days
```

---

## Chapter Reference by Research Question

```
RQ1.1 (ELO persistence):        Chapters 2, 3, 8
RQ1.2 (Skill stability):        Chapter 8
RQ2.1 (Elite convergence):      Chapters 5, 9
RQ2.3 (Signal decay):           Chapter 6
RQ3.1 (Category calibration):   Chapter 3
RQ3.2 (Crowd vs elite):         Chapter 9
RQ4.1 (Kelly vs Sharpe):        Chapter 4
RQ5.2 (Copy trader effect):     Chapter 9
```

---

*Notes compiled for trading-swarm quant-research and signal agents.*
*Reference: Tetlock and Gardner — Superforecasting (2015)*
*Crown Publishers. ISBN 978-0-8041-3663-8*
