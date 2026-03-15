# Algorithmic Trading: Winning Strategies and Their Rationale
# Ernest P. Chan (2013)
# Agent Reference Notes — Trading Swarm System
# Wiley Trading. ISBN 978-1-118-46014-6

---

## Scope of These Notes

Chan writes primarily about equities and futures but the frameworks
transfer cleanly to any liquid market. These notes cover:

1. Prediction markets: direct application notes included
2. Equities: full coverage for when equity trading agents are built
3. Futures: full coverage for futures trading expansion

This is the most practically actionable of the three books.
Dixon gives you the theory. Lopez de Prado gives you the rigour.
Chan gives you strategies that actually work and tells you
honestly when they stop working.

---

## Part 1 — Mean Reversion Strategies

### 1.1 The Statistical Foundation

Mean reversion is the observation that prices tend to revert
toward a long-run average after deviating from it.

**Why mean reversion exists in markets:**
- Overreaction: traders overreact to news, prices overshoot
- Liquidity provision: market makers push prices back toward fair value
- Arbitrage: related assets pulled back into alignment

**The Augmented Dickey-Fuller Test:**
Before building any mean reversion strategy, test whether
the series is actually mean-reverting (stationary).

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

def test_mean_reversion(price_series, significance=0.05):
    """
    Test whether a price series is mean-reverting.
    
    Uses Augmented Dickey-Fuller test.
    Null hypothesis: series has a unit root (random walk, NOT mean-reverting)
    Reject null = series IS mean-reverting
    
    price_series: pandas Series of prices over time
    significance: p-value threshold (0.05 = 95% confidence)
    
    Returns: dict with test results and interpretation
    """
    result = adfuller(price_series.dropna(), autolag='AIC')
    
    p_value = result[1]
    test_statistic = result[0]
    critical_values = result[4]
    
    is_mean_reverting = p_value < significance
    
    # Half-life of mean reversion (how quickly it reverts)
    # Calculated from AR(1) regression
    lagged = price_series.shift(1).dropna()
    delta = price_series.diff().dropna()
    
    beta = np.polyfit(lagged, delta, 1)[0]
    half_life = -np.log(2) / beta if beta < 0 else np.inf
    
    return {
        'is_mean_reverting': is_mean_reverting,
        'p_value': p_value,
        'test_statistic': test_statistic,
        'critical_values': critical_values,
        'half_life_days': half_life,
        'interpretation': (
            f"Mean-reverting with {half_life:.1f} day half-life"
            if is_mean_reverting and half_life > 0
            else "Random walk — mean reversion strategy not appropriate"
        )
    }

# Application to prediction markets:
# Test whether individual market prices are mean-reverting
# Markets far from resolution may be mean-reverting
# Markets near resolution converge to 0 or 1 (not mean-reverting)

# Application to equities:
# Test individual stocks, ETFs, or spread series
# Spread between correlated stocks often mean-reverts
# even when individual prices don't

def test_multiple_series(price_dict, significance=0.05):
    """
    Test mean reversion across multiple series simultaneously.
    Useful for screening many markets or stocks at once.
    """
    results = {}
    for name, series in price_dict.items():
        try:
            results[name] = test_mean_reversion(series, significance)
        except Exception as e:
            results[name] = {'error': str(e)}
    
    # Sort by half-life (fastest reverting first)
    mean_reverting = {
        k: v for k, v in results.items()
        if v.get('is_mean_reverting') and
        v.get('half_life_days', np.inf) > 0
    }
    
    return sorted(
        mean_reverting.items(),
        key=lambda x: x[1]['half_life_days']
    )
```

---

### 1.2 The Ornstein-Uhlenbeck Process

The mathematical model underlying mean reversion strategies.
Understanding this model is essential for parameter estimation.

**The OU process:**
```
dX_t = θ(μ - X_t)dt + σdW_t

where:
θ = speed of mean reversion (higher = faster)
μ = long-run mean
σ = volatility
W_t = Wiener process (random noise)
```

**Estimating OU parameters from data:**
```python
import numpy as np
from scipy.optimize import minimize

def estimate_ou_parameters(price_series, dt=1/252):
    """
    Estimate Ornstein-Uhlenbeck parameters from price series.
    
    dt: time step (1/252 for daily data, 1/365 for daily prediction markets)
    
    Returns: theta (speed), mu (mean), sigma (volatility)
    These parameters drive position sizing and entry/exit rules.
    """
    n = len(price_series)
    prices = price_series.values
    
    # Method of moments estimation
    # Based on discrete-time AR(1) representation
    
    x = prices[:-1]  # X_t
    y = prices[1:]   # X_{t+1}
    
    # OLS regression: y = a + b*x + epsilon
    b = np.cov(x, y)[0,1] / np.var(x)
    a = np.mean(y) - b * np.mean(x)
    
    # Convert AR(1) parameters to OU parameters
    theta = -np.log(b) / dt
    mu = a / (1 - b)
    
    # Residual volatility
    residuals = y - (a + b * x)
    sigma = np.std(residuals) / np.sqrt((1 - b**2) / (2 * theta * dt))
    
    # Half-life
    half_life = np.log(2) / theta
    
    return {
        'theta': theta,      # mean reversion speed
        'mu': mu,            # long-run mean
        'sigma': sigma,      # volatility
        'half_life': half_life,  # days to revert halfway
        'ar1_coefficient': b     # AR(1) coefficient
    }

# Practical interpretation:
# theta > 0: mean-reverting (good)
# theta > 50: very fast reversion (< 5 day half-life)
# theta < 1: very slow reversion (> 250 day half-life)
# 
# For prediction markets:
# theta very high near resolution (forced convergence)
# theta lower early in market life (noisier)
```

---

### 1.3 Bollinger Band Mean Reversion

The simplest mean reversion strategy. Buy when price falls
below the lower band, sell when it rises above the upper band.

```python
import pandas as pd
import numpy as np

class BollingerBandStrategy:
    """
    Bollinger Band mean reversion strategy.
    
    Buys when price falls below lower band (oversold)
    Sells when price rises above upper band (overbought)
    Exits when price crosses the moving average
    
    Applicable to:
    - Prediction market prices (with caution near expiry)
    - Equity prices
    - Spread series between cointegrated pairs
    """
    
    def __init__(self, lookback=20, n_std=2.0, exit_at_mean=True):
        self.lookback = lookback
        self.n_std = n_std
        self.exit_at_mean = exit_at_mean
    
    def calculate_bands(self, prices):
        """Calculate Bollinger Bands."""
        rolling_mean = prices.rolling(self.lookback).mean()
        rolling_std = prices.rolling(self.lookback).std()
        
        upper = rolling_mean + self.n_std * rolling_std
        lower = rolling_mean - self.n_std * rolling_std
        
        return rolling_mean, upper, lower
    
    def generate_signals(self, prices):
        """
        Generate entry/exit signals.
        
        Returns Series: 1 = long, -1 = short, 0 = flat
        """
        mean, upper, lower = self.calculate_bands(prices)
        
        # Z-score: how many std devs from mean
        z_score = (prices - mean) / (prices.rolling(self.lookback).std())
        
        signals = pd.Series(0, index=prices.index)
        position = 0
        
        for i in range(self.lookback, len(prices)):
            z = z_score.iloc[i]
            
            if position == 0:
                if z < -self.n_std:
                    position = 1   # buy (oversold)
                elif z > self.n_std:
                    position = -1  # sell (overbought)
            
            elif position == 1:
                if self.exit_at_mean and z >= 0:
                    position = 0   # exit long at mean
                elif z > self.n_std:
                    position = -1  # flip to short
            
            elif position == -1:
                if self.exit_at_mean and z <= 0:
                    position = 0   # exit short at mean
                elif z < -self.n_std:
                    position = 1   # flip to long
            
            signals.iloc[i] = position
        
        return signals, z_score
    
    def backtest(self, prices, transaction_cost=0.02):
        """
        Backtest the strategy on historical prices.
        Returns performance metrics.
        """
        signals, z_score = self.generate_signals(prices)
        
        # Calculate returns
        price_returns = prices.pct_change()
        strategy_returns = signals.shift(1) * price_returns
        
        # Apply transaction costs
        trades = signals.diff().abs()
        strategy_returns -= trades * transaction_cost
        
        # Performance metrics
        total_return = (1 + strategy_returns).prod() - 1
        annual_return = (1 + total_return) ** (252/len(prices)) - 1
        sharpe = (strategy_returns.mean() /
                 strategy_returns.std() * np.sqrt(252))
        
        # Drawdown
        cumulative = (1 + strategy_returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'n_trades': int(trades.sum() / 2),
            'win_rate': (strategy_returns > 0).mean()
        }

# Important caveat for prediction markets:
# Bollinger bands assume the series can go up OR down.
# Near market resolution, prices converge to 0 or 1.
# Apply only to markets with >30% of lifetime remaining.
# Add a filter: if market_age_pct > 0.7, do not trade.
```

---

### 1.4 Kalman Filter for Dynamic Mean Reversion

Chan's most sophisticated mean reversion approach.
The Kalman filter continuously updates the hedge ratio
between two cointegrated assets, making the strategy
adaptive rather than static.

```python
import numpy as np
import pandas as pd

class KalmanFilterPairsTrade:
    """
    Kalman Filter based pairs trading strategy.
    
    Continuously estimates the dynamic relationship between
    two cointegrated assets. More adaptive than fixed
    hedge ratio approaches.
    
    Applications:
    - Equity pairs (e.g. two correlated tech stocks)
    - ETF pairs (e.g. GLD vs SLV)
    - Prediction market pairs (correlated political markets)
    - Futures calendar spreads
    """
    
    def __init__(self, delta=1e-4, Vw=None, Ve=None):
        """
        delta: state transition variance (lower = slower adaptation)
        Vw: process noise covariance
        Ve: observation noise variance
        """
        self.delta = delta
        self.Vw = Vw if Vw is not None else delta / (1 - delta) * np.eye(2)
        self.Ve = Ve if Ve is not None else 0.001
        
        # State: [intercept, slope/hedge_ratio]
        self.theta = np.zeros(2)
        self.P = np.zeros((2, 2))  # State covariance
        
        self.hedge_ratios = []
        self.spreads = []
        self.errors = []
    
    def update(self, x, y):
        """
        Update Kalman filter with new observation.
        
        x: price of asset X (independent variable)
        y: price of asset Y (dependent variable)
        
        Returns: current spread and hedge ratio
        """
        # Observation matrix
        F = np.array([1.0, x])
        
        # Prediction step
        P_pred = self.P + self.Vw
        
        # Observation prediction
        y_pred = np.dot(F, self.theta)
        
        # Innovation (prediction error)
        innovation = y - y_pred
        
        # Innovation covariance
        S = np.dot(F, np.dot(P_pred, F.T)) + self.Ve
        
        # Kalman gain
        K = np.dot(P_pred, F.T) / S
        
        # Update state
        self.theta = self.theta + K * innovation
        self.P = P_pred - np.outer(K, F) * np.dot(F, P_pred)
        
        # Current spread (residual)
        spread = y - np.dot(F, self.theta)
        
        self.hedge_ratios.append(self.theta[1])
        self.spreads.append(spread)
        self.errors.append(innovation)
        
        return {
            'spread': spread,
            'hedge_ratio': self.theta[1],
            'intercept': self.theta[0],
            'innovation': innovation
        }
    
    def generate_signals(self, x_series, y_series,
                         entry_threshold=1.0, exit_threshold=0.0):
        """
        Generate trading signals from Kalman filter.
        
        entry_threshold: z-score to enter position
        exit_threshold: z-score to exit position
        """
        signals = []
        
        for x, y in zip(x_series, y_series):
            state = self.update(x, y)
            
            if len(self.spreads) < 30:
                signals.append(0)
                continue
            
            # Normalise spread to z-score
            spread_series = np.array(self.spreads[-60:])
            z_score = (state['spread'] - spread_series.mean()) / \
                     spread_series.std()
            
            if z_score < -entry_threshold:
                signals.append(1)   # spread too low, buy spread
            elif z_score > entry_threshold:
                signals.append(-1)  # spread too high, sell spread
            elif abs(z_score) < exit_threshold:
                signals.append(0)   # spread normalised, exit
            else:
                signals.append(signals[-1] if signals else 0)
        
        return pd.Series(signals, index=x_series.index)

# Application to prediction markets:
# Two correlated political markets (e.g. two state elections)
# Kalman filter estimates dynamic relationship between them
# Trade the spread when it deviates from the estimated relationship
# 
# This is more sophisticated than static cointegration
# because the relationship between markets changes over time
# as new information arrives
```

---

## Part 2 — Momentum Strategies

### 2.1 Time Series Momentum

**The core finding:**
Assets that have performed well over the past N months
tend to continue performing well over the next M months.
This has been documented across equities, futures, FX,
and commodities over long time periods.

**Why momentum exists:**
- Underreaction: investors update beliefs slowly
- Trend following: momentum begets momentum as more traders pile in
- Risk premium: momentum may compensate for crash risk

```python
import pandas as pd
import numpy as np

class TimeSeriesMomentum:
    """
    Time series momentum strategy.
    
    Goes long assets with positive recent returns,
    short assets with negative recent returns.
    
    Works best for:
    - Futures (strong empirical evidence)
    - Equities (moderate evidence, sector level stronger)
    - Prediction markets (limited evidence, worth testing)
    """
    
    def __init__(self, lookback=252, holding=21,
                 transaction_cost=0.001):
        """
        lookback: momentum calculation window (days)
        holding: how long to hold each position (days)
        transaction_cost: round-trip cost as fraction
        """
        self.lookback = lookback
        self.holding = holding
        self.transaction_cost = transaction_cost
    
    def calculate_momentum(self, prices):
        """
        Calculate momentum signal.
        Simple: past N-day return.
        Sophisticated: risk-adjusted past return.
        """
        # Simple momentum
        simple_momentum = prices.pct_change(self.lookback)
        
        # Risk-adjusted momentum (Sharpe-like)
        rolling_return = prices.pct_change()
        risk_adj_momentum = (
            rolling_return.rolling(self.lookback).mean() /
            rolling_return.rolling(self.lookback).std()
        )
        
        return simple_momentum, risk_adj_momentum
    
    def generate_signals(self, prices_dict):
        """
        Generate signals across multiple assets.
        
        prices_dict: dict of {asset_name: price_series}
        Returns: DataFrame of positions (-1, 0, 1)
        """
        prices_df = pd.DataFrame(prices_dict)
        
        simple_mom, risk_adj_mom = self.calculate_momentum(prices_df)
        
        # Cross-sectional ranking
        # Go long top quartile, short bottom quartile
        rankings = risk_adj_mom.rank(axis=1, pct=True)
        
        signals = pd.DataFrame(0, index=rankings.index,
                               columns=rankings.columns)
        signals[rankings > 0.75] = 1   # top quartile: long
        signals[rankings < 0.25] = -1  # bottom quartile: short
        
        return signals
    
    def backtest(self, prices_dict):
        """
        Backtest momentum strategy across multiple assets.
        """
        prices_df = pd.DataFrame(prices_dict)
        signals = self.generate_signals(prices_dict)
        
        # Calculate returns
        returns = prices_df.pct_change()
        
        # Strategy returns (hold for holding period)
        strategy_returns = pd.Series(0.0, index=returns.index)
        
        for i in range(self.lookback, len(returns), self.holding):
            period_signals = signals.iloc[i]
            period_returns = returns.iloc[i:i+self.holding]
            
            # Equal weight within long and short books
            n_long = (period_signals == 1).sum()
            n_short = (period_signals == -1).sum()
            
            if n_long > 0:
                long_weight = 1.0 / n_long
            else:
                long_weight = 0
                
            if n_short > 0:
                short_weight = 1.0 / n_short
            else:
                short_weight = 0
            
            weighted_signals = period_signals.copy().astype(float)
            weighted_signals[weighted_signals == 1] = long_weight
            weighted_signals[weighted_signals == -1] = -short_weight
            
            period_pnl = (period_returns * weighted_signals).sum(axis=1)
            strategy_returns.iloc[i:i+self.holding] = period_pnl
        
        # Subtract transaction costs
        position_changes = signals.diff().abs().sum(axis=1)
        strategy_returns -= position_changes * self.transaction_cost
        
        sharpe = (strategy_returns.mean() /
                 strategy_returns.std() * np.sqrt(252))
        
        cumulative = (1 + strategy_returns).cumprod()
        max_dd = ((cumulative - cumulative.expanding().max()) /
                  cumulative.expanding().max()).min()
        
        return {
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'annual_return': strategy_returns.mean() * 252,
            'hit_rate': (strategy_returns > 0).mean()
        }
```

---

### 2.2 Cross-Sectional Momentum

Instead of looking at one asset over time, rank multiple
assets against each other and trade the relative winners
and losers.

```python
def cross_sectional_momentum(prices_df, lookback=21,
                              top_pct=0.2, bottom_pct=0.2,
                              transaction_cost=0.001):
    """
    Cross-sectional momentum strategy.
    
    Ranks assets by recent performance.
    Long top performers, short bottom performers.
    
    prices_df: DataFrame with assets as columns
    lookback: ranking window in days
    top_pct: fraction of assets to go long
    bottom_pct: fraction of assets to go short
    
    Strong application for:
    - Sector rotation in equities
    - Ranking prediction markets by recent accuracy
    - Identifying outperforming futures contracts
    """
    returns = prices_df.pct_change()
    momentum = prices_df.pct_change(lookback)
    
    # Percentile rank each day
    ranks = momentum.rank(axis=1, pct=True)
    
    positions = pd.DataFrame(0.0, index=ranks.index,
                             columns=ranks.columns)
    positions[ranks >= 1 - top_pct] = 1
    positions[ranks <= bottom_pct] = -1
    
    # Normalise to dollar neutral
    long_count = (positions == 1).sum(axis=1)
    short_count = (positions == -1).sum(axis=1)
    
    positions_norm = positions.copy()
    for col in positions.columns:
        positions_norm.loc[positions[col] == 1, col] /= \
            long_count[positions[col] == 1]
        positions_norm.loc[positions[col] == -1, col] /= \
            short_count[positions[col] == -1]
    
    # Strategy returns
    strategy_returns = (returns * positions_norm.shift(1)).sum(axis=1)
    
    # Transaction costs
    turnover = positions_norm.diff().abs().sum(axis=1)
    strategy_returns -= turnover * transaction_cost
    
    sharpe = (strategy_returns.mean() /
             strategy_returns.std() * np.sqrt(252))
    
    return {
        'returns': strategy_returns,
        'positions': positions_norm,
        'sharpe_ratio': sharpe
    }

# Application to your trader system:
# Rank traders by recent Brier score improvement
# Go long (follow) top performers
# Ignore or fade bottom performers
# This is a meta-strategy on top of your ELO system
```

---

## Part 3 — Statistical Arbitrage

### 3.1 Cointegration — The Foundation

Two assets are cointegrated if a linear combination of them
is stationary (mean-reverting) even though each individually
is a random walk.

This is more powerful than correlation:
- Correlation measures co-movement direction
- Cointegration measures long-run equilibrium relationship

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

def find_cointegrated_pairs(prices_df, significance=0.05):
    """
    Find all cointegrated pairs in a universe of assets.
    
    prices_df: DataFrame with assets as columns, prices as rows
    significance: p-value threshold
    
    Returns: list of (asset1, asset2, hedge_ratio, half_life)
    sorted by half_life (fastest reverting first)
    
    Applications:
    - Equity pairs trading (two correlated stocks)
    - ETF arbitrage (ETF vs underlying basket)
    - Prediction market pairs (two correlated markets)
    - Cross-listed futures arbitrage
    """
    n = prices_df.shape[1]
    assets = prices_df.columns
    cointegrated_pairs = []
    
    for i in range(n):
        for j in range(i+1, n):
            asset1 = assets[i]
            asset2 = assets[j]
            
            series1 = prices_df[asset1].dropna()
            series2 = prices_df[asset2].dropna()
            
            # Align series
            aligned = pd.concat([series1, series2], axis=1).dropna()
            s1 = aligned.iloc[:, 0]
            s2 = aligned.iloc[:, 1]
            
            # Engle-Granger cointegration test
            try:
                score, p_value, _ = coint(s1, s2)
            except Exception:
                continue
            
            if p_value < significance:
                # Estimate hedge ratio via OLS
                model = OLS(s1, add_constant(s2)).fit()
                hedge_ratio = model.params[1]
                
                # Calculate spread
                spread = s1 - hedge_ratio * s2
                
                # Test stationarity of spread
                adf_result = adfuller(spread)
                
                # Half-life of spread
                lagged_spread = spread.shift(1).dropna()
                delta_spread = spread.diff().dropna()
                beta = np.polyfit(lagged_spread, delta_spread, 1)[0]
                half_life = -np.log(2) / beta if beta < 0 else np.inf
                
                cointegrated_pairs.append({
                    'asset1': asset1,
                    'asset2': asset2,
                    'p_value': p_value,
                    'hedge_ratio': hedge_ratio,
                    'half_life': half_life,
                    'spread_std': spread.std()
                })
    
    # Sort by half-life
    return sorted(cointegrated_pairs, key=lambda x: x['half_life'])

def pairs_trade_signals(prices_df, asset1, asset2,
                        hedge_ratio, entry_z=2.0, exit_z=0.5,
                        transaction_cost=0.001):
    """
    Generate pairs trading signals for a cointegrated pair.
    
    When spread is too high: short asset1, long asset2
    When spread is too low: long asset1, short asset2
    Exit when spread normalises
    """
    s1 = prices_df[asset1]
    s2 = prices_df[asset2]
    
    spread = s1 - hedge_ratio * s2
    
    # Rolling z-score
    rolling_mean = spread.rolling(60).mean()
    rolling_std = spread.rolling(60).std()
    z_score = (spread - rolling_mean) / rolling_std
    
    # Signals
    long_entry = z_score < -entry_z
    short_entry = z_score > entry_z
    exit_signal = abs(z_score) < exit_z
    
    position = pd.Series(0, index=spread.index)
    current_pos = 0
    
    for i in range(len(spread)):
        if current_pos == 0:
            if long_entry.iloc[i]:
                current_pos = 1
            elif short_entry.iloc[i]:
                current_pos = -1
        elif exit_signal.iloc[i]:
            current_pos = 0
        
        position.iloc[i] = current_pos
    
    # PnL
    spread_returns = spread.pct_change()
    strategy_returns = position.shift(1) * spread_returns
    strategy_returns -= position.diff().abs() * transaction_cost
    
    sharpe = (strategy_returns.mean() /
             strategy_returns.std() * np.sqrt(252))
    
    return {
        'signals': position,
        'z_score': z_score,
        'spread': spread,
        'sharpe_ratio': sharpe
    }

# Prediction market application:
# US election swing states are highly cointegrated
# e.g. Pennsylvania and Michigan presidential markets
# Trade the spread when one moves more than the other
# expecting them to realign
#
# Equity application:
# Classic pairs: KO/PEP, GLD/SLV, XOM/CVX
# ETF pairs: SPY/IVV, GLD/IAU
```

---

### 3.2 The Johansen Test for Multiple Cointegrated Assets

When you have more than 2 assets, the Johansen test finds
the optimal linear combination of all of them.

```python
from statsmodels.tsa.vector_ar.vecm import coint_johansen

def johansen_portfolio(prices_df, significance_level=0):
    """
    Find cointegrating vectors across multiple assets.
    
    More powerful than pairwise cointegration when
    multiple assets are related (e.g. sector basket).
    
    significance_level: 0=90%, 1=95%, 2=99% confidence
    
    Returns: hedge ratios for stationary portfolio
    """
    result = coint_johansen(prices_df, det_order=0, k_ar_diff=1)
    
    # Number of cointegrating relationships
    # Compare trace statistic to critical value
    trace_stats = result.lr1
    critical_values = result.cvt[:, significance_level]
    
    n_cointegrating = sum(
        trace_stats[i] > critical_values[i]
        for i in range(len(trace_stats))
    )
    
    if n_cointegrating == 0:
        return None, 0
    
    # First cointegrating vector (most stationary combination)
    hedge_ratios = result.evec[:, 0]
    
    # Normalise
    hedge_ratios = hedge_ratios / hedge_ratios[0]
    
    # Portfolio value
    portfolio = (prices_df * hedge_ratios).sum(axis=1)
    
    return {
        'hedge_ratios': dict(zip(prices_df.columns, hedge_ratios)),
        'n_cointegrating_vectors': n_cointegrating,
        'portfolio_series': portfolio,
        'half_life': test_mean_reversion(portfolio)['half_life_days']
    }

# Application: basket of correlated prediction markets
# e.g. all US Senate race markets in an election cycle
# Johansen finds the optimal combination that is most stationary
# Trade the basket spread rather than individual markets
```

---

## Part 4 — Risk Management

### 4.1 Position Sizing — The Most Important Chapter

Chan's most practical contribution: proper position sizing
matters more than strategy selection.

**The core principle:**
Position size should be proportional to:
1. Your edge (expected return)
2. Inversely proportional to risk (volatility)
3. Adjusted for correlation to existing positions

```python
import numpy as np
import pandas as pd

class PositionSizer:
    """
    Dynamic position sizing based on Chan's framework.
    
    Combines Kelly criterion with volatility targeting
    and correlation adjustment.
    """
    
    def __init__(self, target_volatility=0.15,
                 max_position_pct=0.20,
                 kelly_fraction=0.5):
        """
        target_volatility: annual portfolio volatility target
        max_position_pct: maximum single position size
        kelly_fraction: fraction of Kelly to use (0.5 = half Kelly)
        """
        self.target_vol = target_volatility
        self.max_pos = max_position_pct
        self.kelly_fraction = kelly_fraction
    
    def volatility_adjusted_size(self, signal_strength,
                                  asset_volatility,
                                  capital):
        """
        Size position to target portfolio volatility.
        
        signal_strength: expected return of position (-1 to 1)
        asset_volatility: annualised volatility of asset
        capital: total portfolio capital
        
        Returns: position size in currency units
        """
        # Volatility-adjusted position
        vol_target_size = (
            self.target_vol / asset_volatility *
            abs(signal_strength) * capital
        )
        
        # Apply Kelly fraction
        kelly_size = vol_target_size * self.kelly_fraction
        
        # Apply maximum position limit
        max_size = self.max_pos * capital
        
        return min(kelly_size, max_size) * np.sign(signal_strength)
    
    def portfolio_size(self, signals_dict, volatilities_dict,
                       correlation_matrix, capital):
        """
        Size all positions simultaneously accounting for correlations.
        
        signals_dict: {asset: expected_return}
        volatilities_dict: {asset: annualised_vol}
        correlation_matrix: DataFrame of correlations
        capital: total capital
        
        Returns: dict of position sizes
        """
        assets = list(signals_dict.keys())
        
        # Individual sizes ignoring correlation
        raw_sizes = {
            asset: self.volatility_adjusted_size(
                signals_dict[asset],
                volatilities_dict[asset],
                capital
            )
            for asset in assets
        }
        
        # Correlation adjustment
        # Reduce positions in highly correlated clusters
        if len(assets) > 1:
            corr = correlation_matrix.loc[assets, assets]
            
            for asset in assets:
                # Average correlation to all other positions
                other_assets = [a for a in assets if a != asset]
                if other_assets:
                    avg_corr = corr.loc[asset, other_assets].mean()
                    
                    # Reduce size for highly correlated assets
                    corr_adjustment = 1 - max(0, avg_corr) * 0.5
                    raw_sizes[asset] *= corr_adjustment
        
        return raw_sizes
    
    def kelly_for_binary(self, win_probability, win_payoff,
                         loss_payoff, capital):
        """
        Kelly criterion specifically for binary bet (prediction markets).
        
        win_probability: your model's probability of winning
        win_payoff: profit if correct (e.g. 0.6 for a 40c contract)
        loss_payoff: loss if wrong (e.g. -0.4 for a 40c contract)
        capital: available capital
        
        Returns: position size in currency units
        """
        # Expected value check
        ev = (win_probability * win_payoff +
              (1 - win_probability) * loss_payoff)
        
        if ev <= 0:
            return 0  # No edge, no bet
        
        # Kelly formula for binary bet
        kelly_pct = (win_probability / abs(loss_payoff) -
                    (1 - win_probability) / win_payoff)
        
        # Apply fraction and cap
        position_pct = min(
            kelly_pct * self.kelly_fraction,
            self.max_pos
        )
        
        return max(0, position_pct * capital)
```

---

### 4.2 Stop Loss Rules

Chan's framework for stop losses is more nuanced than
simple percentage stops.

```python
def dynamic_stop_loss(entry_price, current_price,
                      position_type, volatility,
                      atr_multiple=2.0, time_stop_days=None,
                      current_day=None):
    """
    Dynamic stop loss based on volatility (ATR multiple).
    
    More adaptive than fixed percentage stops.
    Wider stops in volatile markets, tighter in calm markets.
    
    entry_price: price at which position was entered
    current_price: current market price
    position_type: 'long' or 'short'
    volatility: current asset volatility (daily)
    atr_multiple: how many volatility units for stop
    time_stop_days: maximum days to hold position
    current_day: days held so far
    
    Returns: (should_stop, reason)
    """
    # Volatility-based stop
    stop_distance = volatility * atr_multiple
    
    if position_type == 'long':
        stop_price = entry_price - stop_distance
        price_stop_triggered = current_price < stop_price
    else:
        stop_price = entry_price + stop_distance
        price_stop_triggered = current_price > stop_price
    
    if price_stop_triggered:
        loss_pct = abs(current_price - entry_price) / entry_price
        return True, f"Price stop: {loss_pct:.1%} loss"
    
    # Time stop
    if time_stop_days and current_day:
        if current_day >= time_stop_days:
            return True, f"Time stop: held {current_day} days"
    
    return False, "Hold"

def trailing_stop(prices, position_type, trail_pct=0.05):
    """
    Trailing stop that locks in profits as price moves favourably.
    
    prices: Series of prices since entry
    position_type: 'long' or 'short'
    trail_pct: trailing stop distance as fraction
    
    Returns: stop price at each point in time
    """
    if position_type == 'long':
        rolling_max = prices.expanding().max()
        stop_prices = rolling_max * (1 - trail_pct)
    else:
        rolling_min = prices.expanding().min()
        stop_prices = rolling_min * (1 + trail_pct)
    
    return stop_prices
```

---

### 4.3 Maximum Adverse Excursion (MAE)

Chan's framework for understanding how much a trade
moves against you before turning profitable.

```python
def calculate_mae_mfe(trades_df):
    """
    Calculate Maximum Adverse Excursion and
    Maximum Favourable Excursion for historical trades.
    
    MAE: how far against you did the trade go?
    MFE: how far in your favour did the trade go?
    
    These diagnostics tell you:
    - If MAE is large for winning trades: stops are too tight
    - If MFE is small for winning trades: exits are too early
    - If MAE/final_pnl ratio is high: trade was nearly stopped out
    
    trades_df: DataFrame with columns:
        entry_price, exit_price, min_price, max_price, direction
    """
    results = []
    
    for _, trade in trades_df.iterrows():
        if trade['direction'] == 'long':
            mae = (trade['min_price'] - trade['entry_price']) / \
                  trade['entry_price']
            mfe = (trade['max_price'] - trade['entry_price']) / \
                  trade['entry_price']
        else:
            mae = (trade['entry_price'] - trade['max_price']) / \
                  trade['entry_price']
            mfe = (trade['entry_price'] - trade['min_price']) / \
                  trade['entry_price']
        
        final_pnl = (trade['exit_price'] - trade['entry_price']) / \
                    trade['entry_price']
        if trade['direction'] == 'short':
            final_pnl = -final_pnl
        
        results.append({
            'mae': mae,
            'mfe': mfe,
            'final_pnl': final_pnl,
            'mae_to_pnl': mae / final_pnl if final_pnl != 0 else np.inf
        })
    
    results_df = pd.DataFrame(results)
    
    return {
        'avg_mae': results_df['mae'].mean(),
        'avg_mfe': results_df['mfe'].mean(),
        'mae_winners': results_df[
            results_df['final_pnl'] > 0]['mae'].mean(),
        'mfe_losers': results_df[
            results_df['final_pnl'] < 0]['mfe'].mean(),
        'stop_too_tight': (
            results_df['mae'].abs() >
            results_df['final_pnl'].abs()
        ).mean()
    }
```

---

## Part 5 — Specific Strategy Frameworks

### 5.1 Mean Reversion in Equities

**The most reliable mean reversion setups in equities:**

1. **Index arbitrage**: ETF vs underlying basket
   - SPY vs S&P 500 futures
   - Spread mean-reverts with very short half-life (<1 day)
   - Requires fast execution (not suitable for daily strategy)

2. **Pairs trading within sectors**:
   - Two stocks in same sector with stable business relationship
   - e.g. Coca-Cola vs PepsiCo, ExxonMobil vs Chevron
   - Half-life typically 5-30 days
   - Suitable for daily strategy

3. **ETF mean reversion**:
   - Leveraged ETFs decay over time
   - Inverse relationship between leveraged ETF pairs
   - e.g. SSO (2x SPY long) and SDS (2x SPY short)

```python
def equity_pairs_universe_scan(price_data, sector_map,
                                min_half_life=2,
                                max_half_life=30):
    """
    Scan equity universe for tradeable pairs within sectors.
    
    price_data: DataFrame of stock prices
    sector_map: dict {ticker: sector}
    min_half_life: minimum half-life in days
    max_half_life: maximum half-life in days
    
    Returns: ranked list of pairs by trading suitability
    """
    # Group by sector
    sectors = {}
    for ticker, sector in sector_map.items():
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(ticker)
    
    all_pairs = []
    
    for sector, tickers in sectors.items():
        # Only test within-sector pairs
        sector_prices = price_data[
            [t for t in tickers if t in price_data.columns]
        ]
        
        if sector_prices.shape[1] < 2:
            continue
        
        pairs = find_cointegrated_pairs(sector_prices)
        
        for pair in pairs:
            if (min_half_life <= pair['half_life'] <= max_half_life):
                pair['sector'] = sector
                all_pairs.append(pair)
    
    return sorted(all_pairs, key=lambda x: x['half_life'])
```

---

### 5.2 Momentum in Futures

**The most reliable momentum setups in futures:**

Chan documents that trend following in futures is one of
the most robust quantitative strategies ever discovered.
It has worked for 50+ years across all asset classes.

```python
def futures_trend_following(prices_dict, lookback_short=20,
                            lookback_long=252,
                            transaction_cost=0.001):
    """
    Dual moving average trend following for futures.
    
    Classic CTA (Commodity Trading Advisor) strategy.
    Goes long when short MA crosses above long MA.
    Goes short when short MA crosses below long MA.
    
    Works best for:
    - Commodity futures (crude oil, gold, grains)
    - Financial futures (equity index, bonds, FX)
    - Moderate for crypto
    
    prices_dict: {contract_name: price_series}
    lookback_short: fast moving average period
    lookback_long: slow moving average period
    """
    all_returns = []
    
    for name, prices in prices_dict.items():
        ma_short = prices.rolling(lookback_short).mean()
        ma_long = prices.rolling(lookback_long).mean()
        
        # Signal: +1 when short MA above long MA, -1 below
        signal = np.sign(ma_short - ma_long)
        
        # Returns
        price_returns = prices.pct_change()
        strategy_returns = signal.shift(1) * price_returns
        
        # Transaction costs on signal changes
        signal_changes = signal.diff().abs()
        strategy_returns -= signal_changes * transaction_cost
        
        all_returns.append(strategy_returns.rename(name))
    
    # Portfolio: equal weight across all futures
    portfolio_returns = pd.concat(all_returns, axis=1).mean(axis=1)
    
    sharpe = (portfolio_returns.mean() /
             portfolio_returns.std() * np.sqrt(252))
    
    return {
        'portfolio_returns': portfolio_returns,
        'sharpe_ratio': sharpe,
        'individual_returns': pd.concat(all_returns, axis=1)
    }
```

---

## Part 6 — Applying Chan to Your System

### 6.1 Prediction Market Specific Applications

**Mean reversion in prediction markets:**

Most applicable early in a market's life when price is noisy.
Least applicable near resolution when price converges to 0/1.

```python
def prediction_market_mean_reversion(market_prices,
                                      resolution_date,
                                      current_date,
                                      min_life_remaining_pct=0.30):
    """
    Apply mean reversion only when sufficient market life remains.
    
    Near resolution, prices don't mean-revert — they converge.
    This filter prevents applying mean reversion inappropriately.
    """
    total_life = (resolution_date - market_prices.index[0]).days
    remaining_life = (resolution_date - current_date).days
    life_remaining_pct = remaining_life / total_life
    
    if life_remaining_pct < min_life_remaining_pct:
        return None, "Too close to resolution for mean reversion"
    
    # Apply Bollinger band strategy
    strategy = BollingerBandStrategy(lookback=10, n_std=1.5)
    signals, z_scores = strategy.generate_signals(market_prices)
    
    return signals, f"Mean reversion active ({life_remaining_pct:.0%} life remaining)"
```

**Momentum in prediction markets:**

More applicable when strong information flow is driving prices.
Elite trader entry (your ELO signal) may be a momentum signal —
prices continue in the direction elite traders push them.

```python
def elite_trader_momentum(trades_df, traders_df,
                           lookback_hours=24,
                           min_elo_threshold=1800):
    """
    Momentum signal based on elite trader activity.
    
    When elite traders (ELO > threshold) are consistently
    buying YES/NO, price tends to continue in that direction.
    
    trades_df: from polymarket_tracker.db trades table
    traders_df: from polymarket_tracker.db traders table
    lookback_hours: window for momentum calculation
    """
    import sqlite3
    
    # Join trades with trader ELO scores
    elite_trades = trades_df[
        trades_df['trader_address'].isin(
            traders_df[traders_df['elo_score'] >= min_elo_threshold]
            ['address']
        )
    ]
    
    # Calculate net direction of elite trader activity
    # +1 = net buying YES, -1 = net buying NO
    recent_elite = elite_trades[
        elite_trades['timestamp'] >=
        pd.Timestamp.now() - pd.Timedelta(hours=lookback_hours)
    ]
    
    if len(recent_elite) == 0:
        return 0, "No recent elite activity"
    
    net_direction = np.sign(
        recent_elite['outcome'].map({'YES': 1, 'NO': -1}).sum()
    )
    
    # Weight by ELO score
    elo_weighted_direction = (
        recent_elite.merge(
            traders_df[['address', 'elo_score']],
            left_on='trader_address',
            right_on='address'
        ).apply(
            lambda row: row['elo_score'] *
            (1 if row['outcome'] == 'YES' else -1),
            axis=1
        ).sum()
    )
    
    return np.sign(elo_weighted_direction), "Elite momentum signal"
```

---

### 6.2 Equities Agent — When You Build It

When you add an equities trading agent, Chan's framework
suggests this priority order for strategy development:

**Start with:**
1. Pairs trading within sectors (clear edge, well-documented)
2. ETF arbitrage (low risk, fast reversion)
3. Index mean reversion (SPY, QQQ daily patterns)

**Progress to:**
4. Cross-sectional momentum (sector rotation)
5. Earnings mean reversion (post-earnings drift)
6. Factor investing (value + momentum combination)

**Only after validation:**
7. Options strategies (require accurate volatility models)
8. Statistical arbitrage baskets (require Johansen cointegration)
9. High frequency patterns (require execution infrastructure)

---

## Part 7 — Key Lessons and Warnings

### 7.1 What Chan Says Doesn't Work

The book is unusually honest about strategy failures.
These are approaches that look good in backtests but fail live:

1. **Overly complex models**: more parameters = more overfitting.
   The best performing strategies in Chan's experience are simple.

2. **Short-term mean reversion in equities without execution edge**:
   Works for market makers, not for daily strategy traders.

3. **Momentum in individual stocks** (vs sectors or asset classes):
   Too much idiosyncratic risk, reversals are severe.

4. **Seasonal patterns**: work until they become widely known,
   then arbitraged away.

5. **Any strategy that required extensive parameter optimisation**:
   If you needed to tune 10 parameters to make it work,
   it probably doesn't.

### 7.2 Chan's Most Important Practical Rules

```python
CHAN_RULES = {
    "rule_1": (
        "If a strategy needs more than 3 parameters, "
        "be very suspicious of backtest results"
    ),
    "rule_2": (
        "Transaction costs kill more strategies than bad signals. "
        "Always include realistic costs before celebrating"
    ),
    "rule_3": (
        "A strategy that works in one regime may fail in another. "
        "Test across multiple distinct market periods"
    ),
    "rule_4": (
        "Cointegration is more reliable than correlation. "
        "Correlation changes, cointegration is structural"
    ),
    "rule_5": (
        "The Sharpe ratio of a live strategy is typically "
        "half the backtest Sharpe. Budget for this degradation"
    ),
    "rule_6": (
        "Position sizing determines long-run returns more "
        "than strategy selection. Get this right first"
    ),
    "rule_7": (
        "Mean reversion strategies fail catastrophically "
        "in trending markets. Always have a trend filter"
    ),
    "rule_8": (
        "If you cannot explain why a strategy works economically, "
        "it is probably curve-fitted. Require an explanation"
    )
}
```

---

## Quick Reference: Strategy Selection Matrix

```
Market Condition    Best Strategy        Avoid
─────────────────────────────────────────────────────
Ranging/quiet      Mean reversion       Momentum
Trending           Momentum             Mean reversion  
High volatility    Reduce all sizes     Full Kelly
Low volatility     Vol-scaled up        Fixed position
Correlated assets  Pairs/cointegration  Single asset
Uncorrelated       Diversified momentum Pairs trading
Near resolution*   Directional only     Mean reversion
Early life*        Mean reversion       Strong directional

* Prediction market specific
```

---

## Key Formulas Quick Reference

```
ADF Test:          H0: unit root (random walk)
                   Reject H0 (p < 0.05) = mean-reverting

Half-life:         HL = -ln(2) / beta
                   where beta from AR(1): ΔX = alpha + beta*X_{t-1}
                   Target: 2-30 days for daily trading

Z-score entry:     z = (price - rolling_mean) / rolling_std
                   Entry: |z| > 2.0, Exit: |z| < 0.5

Cointegration:     Engle-Granger: coint(s1, s2) -> p-value
                   Johansen: for 3+ assets simultaneously

Kelly (binary):    f* = p/|loss| - (1-p)/win
                   Use 0.5x Kelly, cap at 20% per position

ATR Stop:          stop = entry ± (ATR * multiplier)
                   Typical multiplier: 1.5-3.0x ATR
```

---

*Notes compiled for trading-swarm quant-research and market-builder agents.*
*Reference: Chan — Algorithmic Trading: Winning Strategies (2013)*
*Wiley Trading. ISBN 978-1-118-46014-6*
