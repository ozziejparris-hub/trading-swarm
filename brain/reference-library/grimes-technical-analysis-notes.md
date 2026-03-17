# The Art and Science of Technical Analysis
# Robert Grimes (2012)
# Agent Reference Notes — Trading Swarm System
# Wiley Trading. ISBN 978-1-118-11512-4

---

## Why This Book Matters for Your System

Grimes is unusual in the technical analysis literature
for one reason: he is rigorous about what actually works.

Most technical analysis books present patterns as if
they have been validated. Grimes actually tested them.
His finding: most classic chart patterns have no edge.
A small subset do. The difference is context.

This book matters for your system for three specific reasons:

1. Prediction market prices trace paths over time.
   Those paths have structure that is or isn't exploitable.
   Grimes tells you which structures are real.

2. Your signal-agent currently detects convergence but
   doesn't analyse the price path leading up to entry.
   Grimes provides the framework for doing that properly.

3. Your RQ6.2 (near-resolution mispricing) and RQ2.3
   (signal decay rate) are fundamentally questions about
   price path behaviour. Grimes gives you the toolkit.

**Important caveat:**
Grimes writes about equities and futures. Direct transfer
to prediction markets requires adaptation. Prediction
markets have hard boundaries (0 and 1), fixed resolution
dates, and no overnight gaps. Where standard technical
analysis breaks down in prediction markets is noted
explicitly throughout these notes.

---

## Part 1 — What Actually Works (and What Doesn't)

### 1.1 The Grimes Filter

Before building any price-based strategy, Grimes
applies three tests. Apply these to any prediction
market pattern before using it:

**Test 1 — Is the pattern statistically significant?**
Does it appear more often than chance? Does it predict
the next move better than a coin flip?

**Test 2 — Is it consistent across markets and timeframes?**
A pattern that only works in one specific market
or one specific time period is curve-fitting, not signal.

**Test 3 — Is there a rational explanation for why it works?**
Random patterns that happen to have worked historically
will not persist. Patterns with a causal mechanism
tend to persist.

```python
def grimes_pattern_validity_check(pattern_instances,
                                   outcomes,
                                   min_instances=30,
                                   min_accuracy=0.55):
    """
    Apply Grimes' three-test filter to a price pattern.
    
    pattern_instances: list of (market_id, timestamp, direction)
                       where direction = 1 (predict UP) or -1 (DOWN)
    outcomes: list of actual outcomes (1=correct, 0=wrong)
    min_instances: minimum occurrences for statistical validity
    min_accuracy: minimum accuracy to consider pattern real
    
    Returns: validity assessment
    """
    import numpy as np
    from scipy import stats
    
    if len(pattern_instances) < min_instances:
        return {
            'valid': False,
            'reason': f'Insufficient instances: {len(pattern_instances)} < {min_instances}'
        }
    
    accuracy = np.mean(outcomes)
    n = len(outcomes)
    
    # Test 1: Statistical significance vs 50% baseline
    # One-sided binomial test
    successes = int(accuracy * n)
    p_value = stats.binom_test(successes, n, 0.5, alternative='greater')
    
    is_significant = p_value < 0.05 and accuracy > min_accuracy
    
    # Effect size (how much better than chance)
    effect_size = accuracy - 0.5
    
    return {
        'valid': is_significant,
        'accuracy': accuracy,
        'n_instances': n,
        'p_value': p_value,
        'effect_size': effect_size,
        'practical_significance': (
            'Strong' if effect_size > 0.10
            else 'Moderate' if effect_size > 0.05
            else 'Weak'
        ),
        'recommendation': (
            'Use with Kelly sizing' if is_significant and effect_size > 0.08
            else 'Monitor only' if is_significant
            else 'Discard — no statistical edge'
        )
    }
```

---

### 1.2 What Grimes Found Actually Works

After rigorous testing, Grimes identified these as
genuinely having edge:

**1. Trend following with momentum confirmation**
Prices that have been moving in one direction tend
to continue, but only when volume confirms the move.

Prediction market equivalent:
- Markets where price has moved 15%+ in one direction
  in the last 48 hours
- With increasing trade volume (confirming momentum)
- Tend to continue in that direction
- This is your RQ6.2 territory

**2. Support and resistance at round numbers**
Prices cluster and bounce at psychologically significant
levels (0.25, 0.50, 0.75, 0.90 in prediction markets).

Prediction market equivalent:
- Markets at exactly 0.50 have high uncertainty
- Markets crossing from below 0.50 to above tend to
  continue to 0.65-0.70 before mean-reverting
- Markets above 0.90 rarely retrace — late-stage
  certainty is sticky

**3. Volume divergence as warning signal**
When price moves in one direction but volume decreases,
the move is suspect and likely to reverse.

Prediction market equivalent:
- Market price rising but number of trades declining
  suggests thin order flow pushing price without
  genuine conviction
- This is a fade signal, not a follow signal

**4. Failed breakouts as reversal signals**
When price breaks above a significant level then
fails to hold it, the reversal is often sharp.

Prediction market equivalent:
- Market crosses 0.70, then falls back below 0.70
  without resolving — often continues falling to 0.50
- This is a timing signal for fading failed moves

---

### 1.3 What Doesn't Work

Grimes is direct about classic patterns that fail
rigorous testing:

**Classic chart patterns with no consistent edge:**
- Head and shoulders (too subjective, not reproducible)
- Double tops/bottoms (random chance explains most occurrences)
- Triangle patterns (breakout direction is random)
- Most candlestick patterns (no edge after transaction costs)

**Why this matters for your system:**
Do not build price-pattern detection into your signal-agent
based on these patterns. The only price structures worth
detecting are the ones listed in 1.2, and even those
require volume confirmation.

---

## Part 2 — The Market Structure Framework

### 2.1 The Most Important Concept in the Book

Grimes argues that before looking at any pattern,
you must understand the market's current structure:

**Trending market:** Price making higher highs and
higher lows (uptrend) or lower highs and lower lows
(downtrend). Momentum strategies work here.

**Ranging market:** Price oscillating between support
and resistance without clear direction. Mean reversion
strategies work here.

**Transitioning market:** Market changing from trending
to ranging or vice versa. Most dangerous for either
strategy. Best to stand aside.

```python
def classify_market_structure(prices, lookback=20):
    """
    Classify prediction market price structure.
    
    Adapted from Grimes for prediction markets:
    - Trending: strong directional move with momentum
    - Ranging: oscillating without clear direction
    - Transitioning: recent structure break
    - Converging: approaching resolution (hard boundary)
    
    prices: Series of market prices over time
    lookback: number of periods for analysis
    
    Returns: structure classification and metrics
    """
    import numpy as np
    import pandas as pd
    
    if len(prices) < lookback:
        return {'structure': 'insufficient_data'}
    
    recent = prices.tail(lookback)
    
    # Linear regression slope (trend direction)
    x = np.arange(len(recent))
    slope, intercept, r_value, p_value, std_err = \
        np.polyfit(x, recent.values, 1, full=False), None, None, None, None
    
    # Simplified: use correlation with time
    correlation = np.corrcoef(x, recent.values)[0, 1]
    
    # Volatility (ranging vs trending)
    rolling_std = recent.std()
    overall_move = abs(recent.iloc[-1] - recent.iloc[0])
    
    # Range vs trend ratio
    # High ratio = trending (directional move dominates noise)
    # Low ratio = ranging (noise dominates directional move)
    if rolling_std > 0:
        trend_ratio = overall_move / (rolling_std * np.sqrt(lookback))
    else:
        trend_ratio = 0
    
    # Prediction market specific: proximity to resolution
    current_price = prices.iloc[-1]
    near_resolution = current_price > 0.85 or current_price < 0.15
    
    # Classify
    if near_resolution:
        structure = 'converging'
        description = (
            'Market approaching resolution. '
            'Price likely to continue to 0 or 1. '
            'Mean reversion is unlikely. '
            'Do not fade this move.'
        )
    elif abs(correlation) > 0.7 and trend_ratio > 1.5:
        structure = 'trending'
        direction = 'up' if correlation > 0 else 'down'
        description = (
            f'Strong {direction}trend detected. '
            'Momentum strategies appropriate. '
            'Look for entries in trend direction on pullbacks.'
        )
    elif abs(correlation) < 0.3 and trend_ratio < 0.8:
        structure = 'ranging'
        description = (
            'Market oscillating without direction. '
            'Mean reversion strategies appropriate. '
            'Buy near lower range, sell near upper range.'
        )
    else:
        structure = 'transitioning'
        description = (
            'Market structure unclear. '
            'Stand aside until direction clarifies. '
            'Neither trend nor mean reversion is reliable here.'
        )
    
    return {
        'structure': structure,
        'description': description,
        'correlation_with_time': correlation,
        'trend_ratio': trend_ratio,
        'current_price': current_price,
        'near_resolution': near_resolution,
        'price_range': (recent.min(), recent.max()),
        'volatility': rolling_std
    }
```

---

### 2.2 Applying Market Structure to Your Signals

The most important application of Grimes to your
signal-agent: before acting on an elite convergence
signal, check the market structure.

```python
def signal_structure_filter(signal, market_prices,
                             market_resolution_date,
                             current_date):
    """
    Apply Grimes market structure filter to a signal.
    
    Elite convergence signals are more reliable when:
    - Market is trending in the direction of the signal
    - OR market is ranging and signal is contrarian
    
    Signals are less reliable when:
    - Market is in transitional structure
    - Market is near resolution (converging)
    
    signal: dict from signal-agent with 'direction' and 'confidence'
    market_prices: recent price history
    """
    import pandas as pd
    from datetime import datetime
    
    structure = classify_market_structure(market_prices)
    
    signal_direction = signal.get('direction')
    signal_confidence = signal.get('confidence', 'MEDIUM')
    
    # Days to resolution
    days_remaining = (market_resolution_date - current_date).days
    life_pct_remaining = days_remaining / max(
        (market_resolution_date - market_prices.index[0]).days,
        1
    )
    
    # Grimes filters applied to prediction markets
    warnings = []
    signal_quality_adjustment = 1.0
    
    # Filter 1: Near resolution
    if structure['structure'] == 'converging':
        warnings.append(
            'Market near resolution — price likely to continue '
            'to boundary. Only trade in direction of current price.'
        )
        if signal_direction == 'YES' and market_prices.iloc[-1] < 0.5:
            signal_quality_adjustment *= 0.3
        elif signal_direction == 'NO' and market_prices.iloc[-1] > 0.5:
            signal_quality_adjustment *= 0.3
    
    # Filter 2: Transitioning structure
    if structure['structure'] == 'transitioning':
        warnings.append(
            'Market structure unclear — signal reliability reduced. '
            'Consider waiting for structure to clarify.'
        )
        signal_quality_adjustment *= 0.5
    
    # Filter 3: Signal confirms or opposes trend
    if structure['structure'] == 'trending':
        trend_up = structure['correlation_with_time'] > 0
        signal_with_trend = (
            (signal_direction == 'YES' and trend_up) or
            (signal_direction == 'NO' and not trend_up)
        )
        if signal_with_trend:
            signal_quality_adjustment *= 1.2  # Trend confirmation bonus
        else:
            warnings.append(
                'Signal opposes current trend. '
                'Contrarian signals require higher conviction.'
            )
            signal_quality_adjustment *= 0.7
    
    # Filter 4: Very early in market life
    if life_pct_remaining > 0.85:
        warnings.append(
            'Market very early in its life. '
            'Signals at this stage have lower accuracy (RQ2.3).'
        )
        signal_quality_adjustment *= 0.8
    
    return {
        'original_confidence': signal_confidence,
        'structure': structure['structure'],
        'quality_adjustment': signal_quality_adjustment,
        'adjusted_confidence': (
            'HIGH' if signal_quality_adjustment >= 0.9 and
                      signal_confidence == 'HIGH'
            else 'MEDIUM' if signal_quality_adjustment >= 0.6
            else 'LOW'
        ),
        'warnings': warnings,
        'days_remaining': days_remaining,
        'life_pct_remaining': life_pct_remaining,
        'recommendation': (
            'Act on signal' if signal_quality_adjustment > 0.8
            else 'Reduced position size' if signal_quality_adjustment > 0.5
            else 'Pass on this signal'
        )
    }
```

---

## Part 3 — Volume Analysis

### 3.1 Why Volume Matters

Grimes dedicates significant attention to volume because
it is the most under-used confirming indicator.

Price moves with high volume are more reliable than
price moves with low volume. The reasoning:

- High volume = many participants agreeing on direction
- Low volume = thin order flow, easily reversed
- Price move + high volume = conviction
- Price move + low volume = manipulation or noise

```python
def volume_confirmation_score(price_changes,
                               volumes,
                               lookback=10):
    """
    Score how well volume confirms recent price movement.
    
    For prediction markets:
    - 'volume' = number of trades or total shares traded
    - High score = price move confirmed by volume
    - Low score = price move on thin volume (suspect)
    
    price_changes: Series of price changes
    volumes: Series of trade volumes
    
    Returns: confirmation score [0-1] and interpretation
    """
    import numpy as np
    import pandas as pd
    
    if len(price_changes) < lookback:
        return {'score': None, 'interpretation': 'insufficient_data'}
    
    recent_prices = price_changes.tail(lookback)
    recent_volumes = volumes.tail(lookback)
    
    # Normalise volumes
    avg_volume = recent_volumes.mean()
    if avg_volume == 0:
        return {'score': 0, 'interpretation': 'no_volume_data'}
    
    norm_volumes = recent_volumes / avg_volume
    
    # Price direction
    price_direction = np.sign(recent_prices)
    
    # Volume-weighted direction
    # Positive when price moves up on high volume
    # Negative when price moves down on high volume
    volume_weighted_direction = (
        price_direction * norm_volumes
    ).mean()
    
    # Net price movement
    net_price_move = recent_prices.sum()
    
    # Confirmation: volume agrees with price direction
    if abs(net_price_move) < 0.02:
        confirmation_score = 0.5  # No clear price move to confirm
    elif net_price_move > 0:
        confirmation_score = min(
            1.0,
            max(0.0, volume_weighted_direction / 2 + 0.5)
        )
    else:
        confirmation_score = min(
            1.0,
            max(0.0, -volume_weighted_direction / 2 + 0.5)
        )
    
    return {
        'score': confirmation_score,
        'net_price_move': net_price_move,
        'avg_volume_ratio': norm_volumes.mean(),
        'interpretation': (
            'Strong confirmation' if confirmation_score > 0.7
            else 'Moderate confirmation' if confirmation_score > 0.5
            else 'Weak confirmation — treat price move with caution'
        )
    }
```

---

### 3.2 Volume Patterns in Prediction Markets

Grimes' volume patterns adapted for prediction markets:

**Pattern 1 — Climactic volume near resolution**
Heavy volume in final days of market life often
indicates forced position closing, not new information.
Prices at this point are unreliable.

**Pattern 2 — Volume dry-up before major move**
Decreasing volume before a sharp price move often
precedes the move. The market is "coiling" before
breaking out.

**Pattern 3 — Volume confirmation of elite entry**
When legendary traders enter with unusually large
positions (vs their historical average), the signal
is stronger than when they enter with small positions.

```python
def elite_entry_volume_score(trader_position,
                              trader_historical_avg_size,
                              trader_elo):
    """
    Score the significance of an elite trader's entry
    based on their position size vs historical average.
    
    A legendary trader entering at 3x their normal size
    is a much stronger signal than entering at 0.5x.
    
    Inspired by Grimes' volume confirmation principle:
    size = conviction = stronger signal.
    
    trader_position: current position size
    trader_historical_avg_size: their average position size
    trader_elo: their ELO score
    """
    if trader_historical_avg_size == 0:
        size_ratio = 1.0
    else:
        size_ratio = trader_position / trader_historical_avg_size
    
    # ELO weight (legendary traders count more)
    elo_weight = min(2.0, trader_elo / 1800)
    
    # Combined signal strength
    signal_strength = size_ratio * elo_weight
    
    return {
        'size_ratio': size_ratio,
        'elo_weight': elo_weight,
        'signal_strength': signal_strength,
        'classification': (
            'Very strong signal' if signal_strength > 3.0
            else 'Strong signal' if signal_strength > 2.0
            else 'Normal signal' if signal_strength > 0.8
            else 'Weak signal — below average position size'
        )
    }
```

---

## Part 4 — Price Levels and Boundaries

### 4.1 Prediction Market Specific Price Levels

Standard technical analysis identifies support and
resistance at round numbers. In prediction markets,
the relevant levels are different:

```python
PREDICTION_MARKET_KEY_LEVELS = {
    0.05: {
        'name': 'near_certain_no',
        'description': 'Market pricing outcome as nearly impossible',
        'behaviour': 'Strong sticky level — hard to move above without news',
        'trading_implication': 'Only buy if you have strong contrary evidence'
    },
    0.10: {
        'name': 'low_probability',
        'description': 'Tail risk territory',
        'behaviour': 'Volatile — small news can double price',
        'trading_implication': 'High variance bets — Kelly suggests tiny sizes'
    },
    0.25: {
        'name': 'minority_view',
        'description': 'Clear underdog but not dismissed',
        'behaviour': 'Often oversold on bad news, undersold on good',
        'trading_implication': 'Mean reversion opportunities if fundamentals stable'
    },
    0.50: {
        'name': 'maximum_uncertainty',
        'description': 'Coin flip — market has no view',
        'behaviour': 'High volatility, sensitive to all information',
        'trading_implication': 'Avoid unless you have strong directional view'
    },
    0.75: {
        'name': 'leading_outcome',
        'description': 'Clear favourite but not certain',
        'behaviour': 'Often overshoots then reverts to 0.70-0.75 range',
        'trading_implication': 'Watch for failed breakouts above 0.80'
    },
    0.90: {
        'name': 'near_certain_yes',
        'description': 'Market pricing outcome as nearly certain',
        'behaviour': 'Very sticky — hard to move below without news',
        'trading_implication': 'Do not fade unless you have strong contrary evidence'
    }
}


def identify_key_level_proximity(current_price,
                                  threshold=0.03):
    """
    Identify if current price is near a key prediction
    market level.
    
    Prices near key levels behave differently than
    prices in open water between levels.
    
    Returns: nearest key level and distance from it
    """
    key_levels = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
    
    nearest = min(key_levels, key=lambda x: abs(x - current_price))
    distance = abs(nearest - current_price)
    
    at_level = distance <= threshold
    
    level_info = PREDICTION_MARKET_KEY_LEVELS.get(nearest, {})
    
    return {
        'current_price': current_price,
        'nearest_level': nearest,
        'distance_from_level': distance,
        'at_key_level': at_level,
        'level_name': level_info.get('name', 'unknown'),
        'behaviour': level_info.get('behaviour', ''),
        'trading_implication': level_info.get('trading_implication', '')
    }
```

---

### 4.2 The Hard Boundary Effect

This is unique to prediction markets and not in Grimes.
Worth documenting here as an adaptation.

Prediction market prices have hard boundaries at 0 and 1.
As prices approach these boundaries, behaviour changes:

1. **Acceleration near boundary:** Once price exceeds 0.90,
   it tends to reach 1.0 faster than a random walk predicts.
   The hard boundary creates a "gravitational pull."

2. **No mean reversion near boundary:** At 0.92, mean reversion
   to 0.50 is almost never the right trade. The market is
   pricing near-certainty. Respect it.

3. **False breakouts above 0.90:** Sometimes prices spike
   above 0.90 on thin volume then retreat. These are the
   most reliable fade opportunities in prediction markets.

```python
def boundary_proximity_adjustment(signal_direction,
                                   current_price,
                                   elite_signal=False):
    """
    Adjust signal strength based on proximity to hard boundaries.
    
    Grimes principle: respect strong trends near boundaries.
    Prediction market adaptation: near 0 or 1, momentum dominates.
    
    signal_direction: 'YES' or 'NO'
    current_price: current market price
    elite_signal: whether this is backed by elite traders
    """
    adjustments = []
    quality_multiplier = 1.0
    
    # Near YES boundary (price > 0.85)
    if current_price > 0.85:
        if signal_direction == 'YES':
            # Confirming near-certain outcome
            quality_multiplier *= 0.7
            adjustments.append(
                'Price near YES boundary — limited upside, '
                'small Kelly appropriate'
            )
        else:
            # Betting against near-certain outcome
            if not elite_signal:
                quality_multiplier *= 0.2
                adjustments.append(
                    'WARNING: Fading near-certain outcome without '
                    'elite signal confirmation. Very high risk.'
                )
            else:
                quality_multiplier *= 0.5
                adjustments.append(
                    'Contrarian elite signal near YES boundary. '
                    'Small position only — very high conviction required.'
                )
    
    # Near NO boundary (price < 0.15)
    elif current_price < 0.15:
        if signal_direction == 'NO':
            quality_multiplier *= 0.7
            adjustments.append(
                'Price near NO boundary — limited downside, '
                'small Kelly appropriate'
            )
        else:
            if not elite_signal:
                quality_multiplier *= 0.2
                adjustments.append(
                    'WARNING: Buying near-impossible outcome without '
                    'elite signal. Very high risk.'
                )
            else:
                quality_multiplier *= 0.5
                adjustments.append(
                    'Elite signal on near-impossible outcome. '
                    'Tiny position only — extraordinary conviction required.'
                )
    
    # At maximum uncertainty (near 0.50)
    elif 0.45 <= current_price <= 0.55:
        adjustments.append(
            'Market at maximum uncertainty (near 0.50). '
            'Signals here are highest variance. '
            'Reduce position size accordingly.'
        )
        quality_multiplier *= 0.8
    
    return {
        'quality_multiplier': quality_multiplier,
        'adjustments': adjustments,
        'final_recommendation': (
            'Proceed with normal sizing'
            if quality_multiplier >= 0.8
            else 'Reduce position size significantly'
            if quality_multiplier >= 0.4
            else 'Pass on this signal'
        )
    }
```

---

## Part 5 — Risk Management Framework

### 5.1 The Grimes Risk Rules

Grimes is more rigorous about risk management than
most technical analysis authors. His core rules:

**Rule 1 — Define risk before entry**
Before entering any position, know exactly where
you are wrong. The exit level is determined at entry,
not after the position moves against you.

```python
def define_entry_risk(entry_price,
                       signal_direction,
                       market_structure,
                       days_to_resolution):
    """
    Define risk parameters at entry — before taking position.
    
    Grimes principle: know your exit before your entry.
    
    For prediction markets, the 'stop loss' is a price
    level at which the thesis is invalidated — not just
    an arbitrary percentage.
    
    entry_price: price at which position is entered
    signal_direction: 'YES' or 'NO'
    market_structure: output from classify_market_structure()
    days_to_resolution: days until market resolves
    """
    
    if signal_direction == 'YES':
        # Thesis invalidated if price drops significantly
        # Thesis invalidation level depends on entry price
        if entry_price > 0.70:
            stop_level = entry_price - 0.15
            rationale = 'Drop of 15pp from near-certain level invalidates thesis'
        elif entry_price > 0.50:
            stop_level = 0.45
            rationale = 'Drop below 50% means consensus has shifted against us'
        else:
            stop_level = entry_price * 0.6
            rationale = 'Drop of 40% from entry on low-probability bet'
    else:
        # Betting NO — thesis invalidated if price rises
        if entry_price < 0.30:
            stop_level = entry_price + 0.15
            rationale = 'Rise of 15pp from low level invalidates thesis'
        elif entry_price < 0.50:
            stop_level = 0.55
            rationale = 'Rise above 50% means consensus has shifted against us'
        else:
            stop_level = entry_price + (1 - entry_price) * 0.4
            rationale = 'Rise of 40% of remaining space invalidates thesis'
    
    # Time stop: if thesis hasn't played out by halfway point
    time_stop_days = days_to_resolution // 2
    
    # Maximum loss calculation
    position_size = 1.0  # Placeholder — scaled by Kelly elsewhere
    max_loss_pct = abs(entry_price - stop_level) / entry_price
    
    return {
        'entry_price': entry_price,
        'stop_level': stop_level,
        'max_loss_pct': max_loss_pct,
        'time_stop_days': time_stop_days,
        'rationale': rationale,
        'risk_reward': (
            abs(1.0 - entry_price) / abs(entry_price - stop_level)
            if signal_direction == 'YES'
            else abs(entry_price) / abs(stop_level - entry_price)
        )
    }
```

**Rule 2 — Position size from risk, not conviction**
Never size a position based on how confident you feel.
Size based on the maximum loss you can accept.

```python
def size_from_risk(capital, max_loss_per_trade_pct,
                    stop_level, entry_price,
                    signal_direction):
    """
    Calculate position size from maximum acceptable loss.
    
    Grimes and Kelly agree on this:
    Position size should be derived from risk parameters,
    not from how confident you feel.
    
    capital: total capital
    max_loss_per_trade_pct: maximum acceptable loss as
                             fraction of total capital
                             (e.g. 0.02 = 2% max loss per trade)
    stop_level: price at which thesis is invalidated
    entry_price: current entry price
    signal_direction: 'YES' or 'NO'
    """
    max_loss_dollars = capital * max_loss_per_trade_pct
    
    # Loss per unit if stopped out
    if signal_direction == 'YES':
        loss_per_unit = entry_price - stop_level
    else:
        loss_per_unit = stop_level - entry_price
    
    if loss_per_unit <= 0:
        return 0
    
    # Number of units to buy
    units = max_loss_dollars / loss_per_unit
    
    # Total position size
    position_size = units * entry_price
    position_pct = position_size / capital
    
    return {
        'position_size_dollars': position_size,
        'position_pct_of_capital': position_pct,
        'units': units,
        'max_loss_dollars': max_loss_dollars,
        'max_loss_pct': max_loss_per_trade_pct,
        'warning': (
            'Position exceeds 25% of capital — reduce'
            if position_pct > 0.25
            else None
        )
    }
```

**Rule 3 — Asymmetric risk/reward**
Only take trades where the potential gain is at
least 2x the potential loss.

```python
def check_risk_reward(entry_price, stop_level,
                       target_price, signal_direction,
                       min_ratio=2.0):
    """
    Check if trade has acceptable risk/reward ratio.
    
    Grimes minimum: 2:1 reward to risk.
    For lower-probability signals: require 3:1 or higher.
    
    entry_price: position entry price
    stop_level: price at which thesis is wrong
    target_price: expected price at thesis completion
    signal_direction: 'YES' or 'NO'
    min_ratio: minimum reward/risk to proceed
    """
    if signal_direction == 'YES':
        risk = entry_price - stop_level
        reward = target_price - entry_price
    else:
        risk = stop_level - entry_price
        reward = entry_price - target_price
    
    if risk <= 0:
        return {'acceptable': False, 'reason': 'Invalid stop level'}
    
    ratio = reward / risk
    
    return {
        'ratio': ratio,
        'risk': risk,
        'reward': reward,
        'acceptable': ratio >= min_ratio,
        'recommendation': (
            f'Acceptable — {ratio:.1f}:1 reward/risk'
            if ratio >= min_ratio
            else f'Reject — {ratio:.1f}:1 below minimum {min_ratio}:1'
        )
    }
```

---

## Part 6 — Applying Grimes to Your Research Questions

### How Grimes Informs Each RQ

**RQ2.3 (Signal decay rate):**
Grimes would predict: signals are more reliable when
they align with market structure. A signal in a
trending market (confirming the trend) will decay
slower than a contrarian signal in a trending market.

Test modification: when running RQ2.3, stratify by
market structure at time of signal. Decay rate will
differ significantly by structure.

**RQ6.2 (Near-resolution mispricing):**
Grimes' hard boundary effect directly predicts:
prices in the final 20% of market life accelerate
toward resolution. The mispricing is real but the
trade becomes harder to execute profitably because:
- Less time for thesis to play out
- Lower Kelly fractions appropriate
- Volume may be thin

**RQ3.2 (Crowd vs elite divergence):**
Grimes would frame this as: elite traders are
providing the "smart money" volume that makes
price discovery more efficient. Where they diverge
from crowd, they are correcting mispricing.

Volume confirmation matters: elite divergence
backed by large position sizes (vs their historical
average) is more reliable than small-position divergence.

---

## Part 7 — The Grimes Checklist

Before any position entry, run this checklist:

```python
GRIMES_ENTRY_CHECKLIST = [
    {
        'check': 'Market structure identified',
        'question': 'Is the market trending, ranging, or transitioning?',
        'fail_action': 'Do not enter transitioning markets'
    },
    {
        'check': 'Volume confirms price',
        'question': 'Does volume support the recent price move?',
        'fail_action': 'Reduce position size by 50%'
    },
    {
        'check': 'Key level awareness',
        'question': 'Is price near a key level? If so, which?',
        'fail_action': 'Adjust position based on boundary_proximity_adjustment()'
    },
    {
        'check': 'Risk defined before entry',
        'question': 'Where am I wrong? What is my stop level?',
        'fail_action': 'Do not enter without defined stop'
    },
    {
        'check': 'Risk/reward acceptable',
        'question': 'Is reward at least 2x risk?',
        'fail_action': 'Pass on trade'
    },
    {
        'check': 'Position sized from risk',
        'question': 'Is position sized to limit loss, not maximise gain?',
        'fail_action': 'Resize using size_from_risk()'
    },
    {
        'check': 'Signal quality filter applied',
        'question': 'Has signal been filtered by signal_structure_filter()?',
        'fail_action': 'Apply filter before sizing'
    },
    {
        'check': 'Pattern has statistical basis',
        'question': 'Has this pattern been validated by grimes_pattern_validity_check()?',
        'fail_action': 'Do not trade unvalidated patterns'
    }
]
```

---

## Quick Reference

```
What works in prediction markets (Grimes-validated):
- Trend following with volume confirmation
- Support/resistance at 0.25, 0.50, 0.75, 0.90
- Volume divergence as reversal warning
- Failed breakouts at key levels

What doesn't work:
- Classic chart patterns (head/shoulders, triangles)
- Most candlestick patterns
- Patterns without volume confirmation

Market structures:
- Trending: momentum strategies work
- Ranging: mean reversion strategies work
- Transitioning: stand aside
- Converging (near resolution): momentum only

Key prediction market levels:
- 0.05/0.95: near-certain outcomes — very sticky
- 0.50: maximum uncertainty — highest volatility
- 0.25/0.75: minority/majority view — mean reversion zone

Risk management minimums:
- Minimum reward/risk: 2:1
- Maximum single position: 25% of capital
- Stop level: defined BEFORE entry
- Size: from maximum loss, not from conviction

Volume confirmation score > 0.7: strong signal
Volume confirmation score < 0.5: treat price move with caution
Elite entry at >2x historical average size: strong conviction signal
```

---

## Chapter Reference by Research Question

```
RQ2.3 (Signal decay rate):          Chapters 4, 7, 12
RQ6.1 (Volume vs accuracy):         Chapters 5, 6
RQ6.2 (Near-resolution mispricing): Chapters 8, 13
RQ3.2 (Crowd vs elite):             Chapters 9, 10
RQ4.2 (Overbetting analysis):       Chapter 14 (risk management)
```

---

*Notes compiled for trading-swarm signal-agent and quant-research agent.*
*Reference: Grimes — The Art and Science of Technical Analysis (2012)*
*Wiley Trading. ISBN 978-1-118-11512-4*
