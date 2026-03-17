# Fortune's Formula: The Untold Story of the Scientific Betting System
# William Poundstone (2005)
# Agent Reference Notes — Trading Swarm System
# Hill and Wang. ISBN 978-0-8090-4532-3

---

## Why This Book Matters for Your System

Fortune's Formula is the definitive account of the Kelly
criterion — where it came from, how it was proven to work
in practice, and critically, when and why it fails.

Your system already has kelly_alignment_score as a behavioral
metric. This book gives the deep foundation that improves
how that metric is designed, interpreted, and used.

More importantly: the book documents the exact debates
between Kelly believers (Edward Thorp, Claude Shannon)
and Kelly skeptics (Paul Samuelson, academic economists).
Those debates are directly relevant to how aggressively
your system should size positions.

The honest summary: Kelly works. Full Kelly is too
aggressive for anyone who values survival. The debate
is about what fraction to use. This book gives you the
empirical and theoretical answer.

---

## Part 1 — The Kelly Criterion: Origin and Proof

### 1.1 Where It Came From

John Kelly Jr. was a Bell Labs physicist who in 1956
published a paper on information theory that nobody
initially connected to gambling or investing.

His insight: the optimal betting fraction is not the
one that maximises expected return per bet. It is the
one that maximises the long-run growth rate of wealth.

These are different things. Maximising per-bet expected
value leads to overbetting and ruin. Maximising growth
rate leads to Kelly sizing.

**The fundamental equation:**

```
f* = (bp - q) / b

where:
f* = fraction of capital to bet
b  = net odds (profit per unit staked)
p  = probability of winning
q  = probability of losing (1 - p)
```

For prediction markets specifically:

```python
def kelly_fraction_polymarket(entry_price, true_probability,
                               max_fraction=0.25,
                               kelly_multiplier=0.5):
    """
    Kelly criterion for a binary prediction market position.
    
    entry_price: current market price (implied probability)
    true_probability: your estimate of true probability
    max_fraction: hard cap regardless of Kelly output
    kelly_multiplier: fraction of full Kelly to use
                      (0.5 = half Kelly, recommended)
    
    Returns: optimal position size as fraction of capital
    
    Example:
    Market at 0.40 (40% implied), you think true prob = 0.60
    Net odds b = (1-0.40)/0.40 = 1.5
    f* = (1.5*0.60 - 0.40) / 1.5 = 0.333 (33.3% full Kelly)
    Half Kelly = 0.167 (16.7% of capital)
    """
    if true_probability <= entry_price:
        return 0.0  # No edge, no bet
    
    if entry_price <= 0 or entry_price >= 1:
        return 0.0  # Invalid price
    
    # Net odds: what you win per unit staked
    b = (1 - entry_price) / entry_price
    
    p = true_probability
    q = 1 - true_probability
    
    # Full Kelly
    full_kelly = (b * p - q) / b
    
    if full_kelly <= 0:
        return 0.0
    
    # Apply multiplier and cap
    fractional_kelly = full_kelly * kelly_multiplier
    
    return min(fractional_kelly, max_fraction)


def kelly_for_portfolio(positions, kelly_multiplier=0.5):
    """
    Kelly sizing across multiple simultaneous positions.
    
    When holding multiple positions, the individual Kelly
    fractions must be adjusted for correlation between them.
    
    Uncorrelated positions: sum of individual Kellys is safe
    Correlated positions: sum must be reduced
    
    positions: list of dicts with keys:
        entry_price, true_probability, correlation_to_others
    """
    import numpy as np
    
    individual_kellys = []
    
    for pos in positions:
        k = kelly_fraction_polymarket(
            pos['entry_price'],
            pos['true_probability'],
            kelly_multiplier=kelly_multiplier
        )
        individual_kellys.append(k)
    
    # Correlation adjustment
    # If average pairwise correlation is r, reduce total by (1-r)
    if len(positions) > 1:
        avg_correlation = np.mean([
            pos.get('correlation_to_others', 0)
            for pos in positions
        ])
        correlation_discount = 1 - avg_correlation
    else:
        correlation_discount = 1.0
    
    total_kelly = sum(individual_kellys) * correlation_discount
    
    return {
        'individual_kellys': individual_kellys,
        'total_portfolio_fraction': total_kelly,
        'correlation_discount': correlation_discount,
        'warning': (
            'Over 50% of capital in play — reduce positions'
            if total_kelly > 0.5
            else None
        )
    }
```

---

### 1.2 Why Kelly Maximises Long-Run Growth

The mathematical proof is elegant and important to
understand — not just accept.

If you bet a fixed fraction f of your capital on each
bet, after N wins and M losses your wealth is:

```
W = W₀ × (1+f)^N × (1-f)^M
```

The growth rate per trial is:

```
G = p × log(1+f) + q × log(1-f)
```

Maximising G with respect to f gives exactly Kelly's
formula. This is not a heuristic — it is the mathematical
optimum for long-run wealth maximisation.

```python
def kelly_growth_rate(f, p, b):
    """
    Calculate the expected growth rate at a given
    betting fraction.
    
    Use this to visualise why Kelly is optimal and
    why overbetting is catastrophic.
    
    f: betting fraction [0,1]
    p: probability of winning
    b: net odds (profit per unit staked)
    
    Returns: expected log growth rate per bet
    """
    import numpy as np
    
    q = 1 - p
    
    if f <= 0:
        return 0.0
    if f >= 1:
        return float('-inf')  # Ruin is inevitable
    
    # Win: multiply by (1 + f*b), lose: multiply by (1 - f)
    growth = p * np.log(1 + f * b) + q * np.log(1 - f)
    
    return growth


def plot_kelly_curve(p, b, output_path=None):
    """
    Show the Kelly growth curve.
    
    The peak of this curve is the Kelly fraction.
    The curve is asymmetric: overbetting is worse
    than underbetting by a large margin.
    
    This asymmetry is the most important practical
    lesson from Kelly theory.
    """
    import numpy as np
    
    fractions = np.linspace(0.001, 0.999, 1000)
    growth_rates = [kelly_growth_rate(f, p, b) for f in fractions]
    
    kelly_f = (b * p - (1-p)) / b
    kelly_growth = kelly_growth_rate(kelly_f, p, b)
    
    # Key insight: at 2x Kelly, growth rate = 0
    # (same as not betting at all)
    # Beyond 2x Kelly: negative growth (certain ruin)
    double_kelly_growth = kelly_growth_rate(2 * kelly_f, p, b)
    
    return {
        'kelly_fraction': kelly_f,
        'kelly_growth_rate': kelly_growth,
        'double_kelly_growth': double_kelly_growth,
        'half_kelly_growth': kelly_growth_rate(
            kelly_f * 0.5, p, b
        ),
        'warning': (
            f'Betting 2x Kelly ({2*kelly_f:.2f}) gives '
            f'growth rate {double_kelly_growth:.4f} — '
            f'same as not betting at all'
        )
    }
```

---

## Part 2 — The Thorp Connection

### 2.1 Edward Thorp: Kelly in Practice

Edward Thorp (mathematician, author of Beat the Dealer)
was the first person to apply Kelly criterion to real
markets. His track record validates the theory:

- 1969-1988: Princeton Newport Partners
- 19 consecutive years of positive returns
- Average annual return: ~20% with low volatility
- Used Kelly sizing throughout
- Never had a losing year

This is the most important empirical validation of
Kelly criterion that exists. 19 years, real money,
real markets, Kelly sizing.

**What Thorp actually used:**
Not full Kelly. He used fractional Kelly (typically
0.25x to 0.5x) because:

1. True probabilities are unknown — estimation error
   means full Kelly overbets
2. Drawdowns from full Kelly are psychologically
   intolerable (50%+ drawdowns are possible)
3. The opportunity cost of a ruin event is infinite

```python
def thorp_position_sizing(edge, variance, capital,
                           max_drawdown_tolerance=0.30,
                           kelly_fraction=0.25):
    """
    Thorp's practical Kelly implementation.
    
    Unlike pure Kelly, this accounts for:
    - Estimation uncertainty in edge calculation
    - Maximum acceptable drawdown
    - Multiple simultaneous positions
    
    edge: expected return per unit (your probability 
          minus market implied probability)
    variance: variance of returns (measure of uncertainty)
    capital: total capital
    max_drawdown_tolerance: maximum acceptable loss (0.30 = 30%)
    kelly_fraction: fraction of Kelly to use (Thorp used 0.25)
    
    Returns: position size in currency units
    """
    import numpy as np
    
    if edge <= 0:
        return 0
    
    # Kelly fraction (edge / variance for continuous case)
    full_kelly_pct = edge / variance
    
    # Apply Thorp's fraction
    fractional_kelly_pct = full_kelly_pct * kelly_fraction
    
    # Drawdown constraint
    # Maximum drawdown ≈ kelly_fraction² / 2 for full Kelly
    # Scale to meet tolerance
    drawdown_limited_pct = np.sqrt(
        2 * max_drawdown_tolerance
    ) * kelly_fraction
    
    # Take the more conservative of the two
    final_pct = min(fractional_kelly_pct, drawdown_limited_pct)
    
    position_size = final_pct * capital
    
    return {
        'position_size': position_size,
        'position_pct': final_pct,
        'full_kelly_pct': full_kelly_pct,
        'kelly_reduction_factor': kelly_fraction,
        'estimated_max_drawdown': final_pct ** 2 / 2
    }
```

---

### 2.2 The Shannon Connection

Claude Shannon (inventor of information theory) was
Thorp's colleague and separately arrived at Kelly
from information theory.

Shannon's insight: the Kelly criterion is the solution
to the same equation as the channel capacity theorem
in information theory.

**What this means for your system:**

The Kelly fraction is not just an optimal bet size.
It is a measure of the information content of your
edge. A Kelly fraction of 10% means you have about
as much information advantage as a 10% efficient
information channel.

When your signal-agent detects elite convergence,
the appropriate Kelly fraction should scale with
signal quality:

```python
def signal_quality_to_kelly(signal_confidence,
                             signal_accuracy_historical,
                             base_kelly=0.25):
    """
    Scale Kelly fraction by signal quality.
    
    Shannon's insight: Kelly fraction = information content.
    Better signals = more information = higher Kelly.
    
    signal_confidence: HIGH/MEDIUM/LOW from signal-agent
    signal_accuracy_historical: historical accuracy of
                                this signal type (0-1)
    base_kelly: minimum Kelly fraction to use
    
    Returns: Kelly fraction appropriate for this signal
    """
    confidence_multipliers = {
        'HIGH': 1.0,
        'MEDIUM': 0.6,
        'LOW': 0.3
    }
    
    multiplier = confidence_multipliers.get(
        signal_confidence, 0.3
    )
    
    # Accuracy adjustment
    # Perfect accuracy (1.0) → full multiplier
    # Random (0.5) → zero Kelly
    accuracy_factor = max(0, (signal_accuracy_historical - 0.5) * 2)
    
    kelly = base_kelly * multiplier * accuracy_factor
    
    return min(kelly, 0.25)  # Hard cap at 25%
```

---

## Part 3 — The Kelly Skeptics

### 3.1 Why Samuelson Hated Kelly

Paul Samuelson (Nobel laureate economist) wrote an
entire paper arguing against Kelly, including one
sentence written entirely in words of one syllable
to make his point accessible:

*"I say it is not right."*

His argument: Kelly maximises geometric mean returns,
but investors should maximise expected utility, not
geometric mean. For an investor with different risk
preferences, Kelly is wrong.

**The honest response:**
Samuelson is technically correct and practically wrong
for your use case. Here's why:

Kelly is optimal IF:
1. You are making a long sequence of bets
2. You have a fixed edge that doesn't change
3. You care about long-run wealth, not short-run utility
4. You can tolerate large drawdowns

For Polymarket trading:
1. ✅ Long sequence of markets available
2. ⚠️ Edge varies by market — you need signal quality weighting
3. ✅ Long-run wealth accumulation is the goal
4. ⚠️ Drawdown tolerance is personal — use fractional Kelly

The practical resolution: use Kelly as a ceiling, not
a prescription. Never bet more than Kelly. Bet less
when uncertain about edge.

```python
KELLY_PRINCIPLES = {
    'never_overbetfull_kelly': (
        'Full Kelly maximises growth but causes severe drawdowns. '
        'Always use fractional Kelly (0.25-0.5x). '
        'Thorp used 0.25x in real markets for 19 years.'
    ),
    'estimation_error_discount': (
        'True probability is never known exactly. '
        'Uncertainty in probability estimate means actual '
        'Kelly is lower than calculated Kelly. '
        'Add a 20-30% discount for estimation uncertainty.'
    ),
    'correlation_matters': (
        'Individual Kelly fractions assume independence. '
        'Correlated positions reduce effective diversification. '
        'Scale down total portfolio exposure when '
        'positions are correlated.'
    ),
    'zero_is_valid': (
        'When edge is uncertain or small, zero is '
        'a valid position size. Kelly says bet nothing '
        'when you have no edge. This is correct.'
    ),
    'ruin_is_irreversible': (
        'Overbetting leads to ruin. Ruin ends the game. '
        'Survival is prerequisite to compounding. '
        'Conservative sizing preserves optionality.'
    )
}
```

---

## Part 4 — Practical Kelly for Prediction Markets

### 4.1 The Estimation Problem

The biggest practical challenge with Kelly in prediction
markets: you never know the true probability.

You have:
- Market price (consensus estimate)
- Your model's estimate (ELO-weighted consensus)
- Uncertainty around that estimate

The estimation problem is solved by shrinking the
Kelly fraction toward zero as uncertainty grows:

```python
def uncertainty_adjusted_kelly(market_price,
                                model_estimate,
                                model_uncertainty,
                                base_kelly=0.5):
    """
    Adjust Kelly fraction for estimation uncertainty.
    
    The wider the confidence interval around your
    model estimate, the smaller the Kelly fraction
    should be.
    
    This is the practical resolution to Samuelson's
    critique: when you are uncertain, bet less.
    
    market_price: current market price
    model_estimate: your probability estimate
    model_uncertainty: standard deviation of estimate
                       (wider = more uncertain)
    base_kelly: starting Kelly fraction before adjustment
    
    Returns: uncertainty-adjusted Kelly fraction
    """
    import numpy as np
    from scipy.stats import norm
    
    # Calculate the probability that your edge is real
    # (model estimate truly > market price)
    if model_estimate <= market_price:
        return 0.0
    
    edge = model_estimate - market_price
    
    # P(true_prob > market_price) given model estimate
    # and uncertainty
    z_score = edge / (model_uncertainty + 1e-6)
    prob_edge_real = norm.cdf(z_score)
    
    # Raw Kelly
    b = (1 - market_price) / market_price
    p = model_estimate
    q = 1 - p
    
    raw_kelly = (b * p - q) / b
    
    if raw_kelly <= 0:
        return 0.0
    
    # Scale by probability that edge is real
    # and by base Kelly fraction
    adjusted_kelly = raw_kelly * base_kelly * prob_edge_real
    
    return min(adjusted_kelly, 0.25)


def kelly_from_elo_consensus(market_price,
                              elite_traders_yes,
                              elite_traders_no,
                              avg_elo_yes,
                              avg_elo_no,
                              n_legendary):
    """
    Calculate Kelly fraction from ELO-weighted consensus.
    
    Combines your system's ELO-weighted probability
    estimate with uncertainty scaling based on how
    many elite traders are in agreement.
    
    More legendary traders agreeing = lower uncertainty
    = higher Kelly fraction appropriate.
    
    elite_traders_yes: count of elite traders on YES
    elite_traders_no: count of elite traders on NO
    avg_elo_yes: average ELO of YES traders
    avg_elo_no: average ELO of NO traders
    n_legendary: count of legendary traders (ELO > 2175)
    """
    import numpy as np
    
    total_elite = elite_traders_yes + elite_traders_no
    if total_elite == 0:
        return 0.0
    
    # ELO-weighted probability estimate
    yes_weight = elite_traders_yes * avg_elo_yes
    no_weight = elite_traders_no * avg_elo_no
    total_weight = yes_weight + no_weight
    
    if total_weight == 0:
        return 0.0
    
    model_estimate = yes_weight / total_weight
    
    # Uncertainty decreases with more traders
    # and more legendary traders
    base_uncertainty = 0.15
    trader_reduction = min(0.10, total_elite * 0.01)
    legendary_reduction = min(0.05, n_legendary * 0.02)
    
    model_uncertainty = max(
        0.02,
        base_uncertainty - trader_reduction - legendary_reduction
    )
    
    return uncertainty_adjusted_kelly(
        market_price=market_price,
        model_estimate=model_estimate,
        model_uncertainty=model_uncertainty
    )
```

---

### 4.2 The Half-Kelly Rule in Practice

The book documents extensive empirical evidence that
half-Kelly (0.5x full Kelly) is the practical sweet spot:

```
Full Kelly:   Maximum long-run growth, severe drawdowns
              50%+ drawdowns are common
              Psychologically very difficult to maintain

Half Kelly:   75% of maximum growth rate
              Drawdowns roughly halved
              Psychologically manageable
              Used by Thorp and most professional Kelly users

Quarter Kelly: 50% of maximum growth rate
               Very small drawdowns
               Appropriate when edge is uncertain
               Conservative but survivable
```

```python
def kelly_comparison(p, b):
    """
    Compare growth rates at different Kelly fractions.
    Shows the practical tradeoff between growth and drawdown.
    """
    import numpy as np
    
    full_kelly = (b * p - (1-p)) / b
    
    if full_kelly <= 0:
        return {'edge': False}
    
    def growth(f):
        return p * np.log(1 + f*b) + (1-p) * np.log(1-f)
    
    full_growth = growth(full_kelly)
    
    results = {}
    for name, fraction in [
        ('full_kelly', 1.0),
        ('half_kelly', 0.5),
        ('quarter_kelly', 0.25),
        ('tenth_kelly', 0.1)
    ]:
        f = full_kelly * fraction
        g = growth(f)
        
        # Approximate expected max drawdown
        # For Kelly, max drawdown ≈ f² / (2 * growth_rate)
        est_drawdown = (f ** 2) / (2 * abs(g) + 0.001)
        
        results[name] = {
            'fraction': f,
            'growth_rate': g,
            'pct_of_max_growth': g / full_growth * 100,
            'estimated_max_drawdown': min(est_drawdown, 1.0)
        }
    
    return results
```

---

## Part 5 — Kelly and Your Research Questions

### Direct Application to RQ4.1, RQ4.2, RQ4.3

**RQ4.1 (Kelly alignment vs Sharpe ratio):**

Theoretical prediction from this book:
- Traders who bet Kelly-optimally maximise long-run
  geometric returns
- This translates to higher Sharpe ratios because
  Kelly-optimal sizing reduces both return variance
  and drawdown relative to overbetting
- Expected correlation: r > 0.3 between kelly_alignment
  and Sharpe ratio

If your data shows this correlation, it validates:
1. Your kelly_alignment_score metric is measuring
   real position sizing discipline
2. Kelly-optimal sizing actually improves risk-adjusted
   returns in Polymarket specifically

**RQ4.2 (Overbetting vs underbetting):**

The book makes a strong prediction here:
- Overbetting is asymmetrically worse than underbetting
- At 2x Kelly, growth rate = 0 (same as not betting)
- At >2x Kelly, expected loss (ruin is certain)
- Underbetting merely reduces growth — it doesn't cause ruin

Expected finding from your data:
- Overbetting positions show lower P&L despite correct
  direction more often than underbetting positions
- The asymmetry should be measurable in your positions table

```python
def classify_position_sizing(entry_price,
                              position_size_fraction,
                              true_probability_estimate,
                              kelly_multiplier=0.5):
    """
    Classify a position as overbetting, optimal, or underbetting
    relative to Kelly criterion.
    
    entry_price: market price at entry
    position_size_fraction: fraction of capital in position
    true_probability_estimate: best estimate of true probability
    kelly_multiplier: what fraction of Kelly is considered optimal
    
    Returns: classification and degree of deviation
    """
    optimal_kelly = kelly_fraction_polymarket(
        entry_price,
        true_probability_estimate,
        kelly_multiplier=kelly_multiplier
    )
    
    if optimal_kelly == 0:
        return {
            'classification': 'no_edge',
            'optimal': 0,
            'actual': position_size_fraction,
            'deviation': None
        }
    
    ratio = position_size_fraction / optimal_kelly
    
    if ratio > 2.0:
        classification = 'severe_overbetting'
    elif ratio > 1.5:
        classification = 'overbetting'
    elif ratio > 0.8:
        classification = 'approximately_optimal'
    elif ratio > 0.3:
        classification = 'underbetting'
    else:
        classification = 'severe_underbetting'
    
    return {
        'classification': classification,
        'optimal_kelly': optimal_kelly,
        'actual_fraction': position_size_fraction,
        'kelly_ratio': ratio,
        'is_overbetting': ratio > 1.5,
        'growth_rate_penalty': (
            'Severe — near ruin zone'
            if ratio > 2.0
            else 'Moderate' if ratio > 1.5
            else 'Minimal'
        )
    }
```

**RQ4.3 (Empirically optimal fraction):**

The book's prediction: optimal fraction for real
markets with estimation error is 0.25x-0.50x full Kelly.

Testing this on legendary traders (ELO > 2175):
- Calculate what fraction of Kelly each position represents
- Correlate Kelly fraction used with subsequent P&L
- The fraction showing highest risk-adjusted returns
  is the empirical optimum for Polymarket

Expected result: 0.25x-0.40x Kelly will show best
risk-adjusted returns in your data. If it's outside
this range, something interesting is happening in
Polymarket's market structure that differs from
the markets Thorp traded.

---

## Part 6 — The Ruin Question

### 6.1 Why Survival Matters More Than Optimisation

The most important practical lesson from the book:

**Kelly is only optimal conditional on survival.**

If you bet more than Kelly and go broke, you cannot
compound. The opportunity cost of ruin is infinite
because you lose all future gains.

This is why the Kelly criterion includes a hard rule:
never bet so much that a single loss ruins you.

For prediction markets:
- Never put more than 25% of capital in any single market
- Never put more than 50% of capital in correlated markets
- Always reserve capital for future opportunities

```python
RUIN_PREVENTION_RULES = {
    'single_market_cap': 0.25,
    'correlated_market_cap': 0.50,
    'minimum_reserve': 0.30,  # always keep 30% in reserve
    'stop_betting_threshold': 0.50,  # if capital drops 50%, stop
    
    'rationale': {
        'single_market_cap': (
            'Even a 4x Kelly bet cannot ruin you in one trade. '
            'But psychological pressure at 25% concentration '
            'is already high.'
        ),
        'correlated_market_cap': (
            'Correlated markets can all resolve against you '
            'simultaneously. Treat as single exposure.'
        ),
        'minimum_reserve': (
            'Reserve capital for future opportunities. '
            'The best opportunities come when others are '
            'scared and capital is scarce.'
        ),
        'stop_betting_threshold': (
            'A 50% drawdown requires 100% gain to recover. '
            'At this point, reassess edge before continuing.'
        )
    }
}
```

---

## Part 7 — Updating Kelly for Your System

### 7.1 Dynamic Kelly Based on Signal Quality

The static Kelly formula assumes a fixed known edge.
In reality, edge varies by signal strength.

Your signal-agent classifies signals as HIGH/MEDIUM/LOW.
Kelly fraction should scale accordingly:

```python
DYNAMIC_KELLY_TABLE = {
    # (signal_confidence, n_legendary_traders): kelly_fraction
    ('HIGH', 5): 0.20,   # 5+ legendary, HIGH confidence
    ('HIGH', 4): 0.17,
    ('HIGH', 3): 0.15,   # Minimum for HIGH signal
    ('MEDIUM', 5): 0.12,
    ('MEDIUM', 4): 0.10,
    ('MEDIUM', 3): 0.08,
    ('MEDIUM', 2): 0.05,
    ('LOW', 'any'): 0.03,  # Barely worth sizing
    ('NONE', 'any'): 0.00  # No signal = no position
}

# These are starting points.
# RQ4.3 will replace these with empirically derived values
# from your actual legendary trader data.
# The table above is the prior.
# The research question produces the posterior.
```

---

## Part 8 — Key Quotes Worth Preserving

**On why Kelly works:**
"The Kelly bettor never goes broke betting on a
favourable game, provided he has enough capital
to weather the inevitable losing streaks."

**On overbetting:**
"A bettor who wagers more than the Kelly amount
will have a lower expected geometric rate of growth
than the Kelly bettor, and will suffer deeper
drawdowns on the way."

**On the practical fraction:**
"In practice, most serious Kelly investors use
a fraction — typically one-half to one-quarter
of the full Kelly amount — to reduce volatility
while preserving most of the long-run growth advantage."

**On survival:**
"The Kelly criterion is only defined for someone
who will be around to collect. Strategies that
risk ruin are dominated by survival strategies,
regardless of their expected return."

---

## Quick Reference

```
Full Kelly formula:    f* = (bp - q) / b
Half Kelly:            f* = 0.5 × (bp - q) / b  ← recommended
Quarter Kelly:         f* = 0.25 × (bp - q) / b ← conservative

At 2x Kelly:           growth rate = 0 (same as not betting)
Beyond 2x Kelly:       negative growth (certain ruin eventually)
Half Kelly growth:     ~75% of full Kelly growth
Quarter Kelly growth:  ~50% of full Kelly growth

Thorp's actual fraction used: 0.25x
Recommended for Polymarket:   0.25x-0.50x (depends on RQ4.3)

Single position cap:   25% of capital (hard rule)
Correlated cap:        50% of capital (hard rule)
Minimum reserve:       30% always undeployed

Kelly fraction = information content of your edge
Higher signal quality → higher Kelly appropriate
No signal → Kelly = 0 (don't bet)
```

---

## Chapter Reference by Research Question

```
RQ4.1 (Kelly alignment vs Sharpe):     Chapters 5, 6, 10
RQ4.2 (Overbetting vs underbetting):   Chapters 6, 7
RQ4.3 (Empirical optimal fraction):    Chapters 8, 9, 10
RQ5.1 (Correlated market risk):        Chapter 10
RQ1.1 (ELO persistence):              Chapter 5 (Thorp track record)
```

---

*Notes compiled for trading-swarm quant-research and signal agents.*
*Reference: Poundstone — Fortune's Formula (2005)*
*Hill and Wang. ISBN 978-0-8090-4532-3*
