# Advances in Financial Machine Learning — Agent Reference Notes
# Marcos Lopez de Prado (2018)
# Extracted and filtered for Polymarket trading intelligence system
# Wiley. ISBN 978-1-119-48208-6

---

## Why This Book Matters More Than Any Other

Lopez de Prado spent years as a quant at hedge funds managing billions.
His core argument: most systematic trading research is statistically
meaningless because researchers don't account for how many strategies
they tested before finding one that "worked."

This book is the antidote to false discovery. It will make your
backtest-agent dramatically more rigorous and your quant-research
agent dramatically less likely to waste time on strategies with
no real edge.

Read the Dixon notes first for foundations. Read these notes for
the discipline that makes those foundations actually work in production.

---

## Part 1 — The False Discovery Problem

### 1.1 Why Most Backtests Are Lies

This is the most important chapter in the book and should be
read by your quant-research agent before starting any research.

**The core problem:**
A researcher tests 100 strategies. By pure chance, approximately
5 will show Sharpe > 1.0 even if all 100 have zero true edge.
The researcher publishes the best one. It fails in production.
This is not fraud — it is a statistical inevitability called
the multiple comparisons problem.

**How bad is this in practice:**
Lopez de Prado estimates that the majority of published quantitative
trading strategies have been overfit to historical data. The strategies
genuinely worked in backtests. They genuinely failed live.

**The mechanism:**
Every time you look at backtest results and adjust your strategy,
you are fitting to noise. Even "obvious" adjustments like
"let's raise the threshold from 0.6 to 0.65 because it improves
Sharpe" are dangerous if done after seeing the results.

**Why this matters for your system specifically:**
Your quant-research agent will test many approaches. Without
explicit safeguards, it will naturally gravitate toward the
approaches that look best on historical data — which are exactly
the approaches most likely to be overfitted.

---

### 1.2 The Deflated Sharpe Ratio

Lopez de Prado's most important practical contribution.

**The problem with standard Sharpe ratio:**
A Sharpe of 1.5 sounds good. But if you tested 50 strategies
to find it, the expected maximum Sharpe from random chance alone
is much higher than 1.0. Your 1.5 may not be significant at all.

**The Deflated Sharpe Ratio (DSR) adjusts for:**
1. How many strategies were tested
2. The length of the backtest
3. Non-normality of returns (skewness, kurtosis)
4. Serial correlation in returns

```python
import numpy as np
from scipy.stats import norm

def deflated_sharpe_ratio(sharpe_ratio, n_trials, backtest_length,
                          skewness=0, kurtosis=3):
    """
    Calculate the Deflated Sharpe Ratio.
    
    Tests whether an observed Sharpe ratio is statistically
    significant given how many strategies were tried.
    
    sharpe_ratio: observed annualised Sharpe ratio
    n_trials: number of strategies tested to find this one
    backtest_length: number of observations in backtest
    skewness: return distribution skewness (0 = normal)
    kurtosis: return distribution kurtosis (3 = normal)
    
    Returns: probability that Sharpe is genuine (not noise)
    """
    # Expected maximum Sharpe from n_trials random strategies
    # Using Extreme Value Theory
    euler_mascheroni = 0.5772156649
    
    expected_max_sharpe = (
        (1 - euler_mascheroni) * norm.ppf(1 - 1/n_trials) +
        euler_mascheroni * norm.ppf(1 - 1/(n_trials * np.e))
    )
    
    # Adjust Sharpe for non-normality
    adjusted_sharpe = sharpe_ratio * (
        1 - skewness * sharpe_ratio +
        (kurtosis - 1) / 4 * sharpe_ratio**2
    ) ** (-0.5)
    
    # DSR: probability the strategy is genuine
    dsr = norm.cdf(
        (adjusted_sharpe - expected_max_sharpe) *
        np.sqrt(backtest_length - 1)
    )
    
    return {
        'dsr': dsr,
        'expected_max_sharpe': expected_max_sharpe,
        'is_significant': dsr > 0.95,
        'n_trials': n_trials
    }

# Example: found Sharpe 1.5 after testing 20 strategies
# on 500 daily observations (2 years)
result = deflated_sharpe_ratio(
    sharpe_ratio=1.5,
    n_trials=20,
    backtest_length=500
)
print(f"DSR: {result['dsr']:.3f}")
print(f"Expected max by chance: {result['expected_max_sharpe']:.3f}")
print(f"Significant: {result['is_significant']}")
# If DSR < 0.95, strategy is probably noise
```

**Updated threshold for your backtest-agent:**
Replace raw Sharpe > 1.0 with DSR > 0.95.
A strategy with Sharpe 2.0 found after 100 trials may have
lower DSR than a strategy with Sharpe 1.2 found on the first try.

**Add to definition_of_done.md:**
- DSR > 0.95 required for any strategy approval
- Number of trials must be logged honestly
- Each attempt counts, even "obvious" parameter adjustments

---

### 1.3 Walk-Forward Validation (The Right Way)

The book's prescribed method for avoiding overfitting.

**Combinatorial Purged Cross-Validation (CPCV):**
Lopez de Prado's improvement on standard cross-validation
for financial time series.

The key insight: standard k-fold cross-validation assumes
observations are independent. Financial time series are not —
today's market is correlated with yesterday's. Using correlated
data in both train and test sets produces optimistically biased
results.

**The Purge:**
Remove observations near the train/test boundary because
they share information (a market open during training may
resolve during testing).

**The Embargo:**
After the purge, add an additional buffer (embargo) of
observations that are excluded entirely. This prevents
any information leakage through lookahead bias.

```python
import pandas as pd
import numpy as np
from itertools import combinations

def purged_kfold_split(timestamps, n_splits=5,
                       purge_pct=0.01, embargo_pct=0.01):
    """
    Purged K-Fold cross-validation for financial time series.
    
    Removes observations near boundaries to prevent leakage.
    
    timestamps: DatetimeIndex of observations
    n_splits: number of folds
    purge_pct: fraction of data to purge at boundaries
    embargo_pct: fraction of data to embargo after test set
    
    Yields: (train_indices, test_indices) for each fold
    """
    n_obs = len(timestamps)
    fold_size = n_obs // n_splits
    purge_size = int(n_obs * purge_pct)
    embargo_size = int(n_obs * embargo_pct)
    
    for fold in range(n_splits):
        # Test set boundaries
        test_start = fold * fold_size
        test_end = min((fold + 1) * fold_size, n_obs)
        
        # Purge: remove observations near test boundaries
        purge_start = max(0, test_start - purge_size)
        embargo_end = min(n_obs, test_end + embargo_size)
        
        # Training indices (everything outside test + purge + embargo)
        train_indices = list(range(0, purge_start)) + \
                       list(range(embargo_end, n_obs))
        test_indices = list(range(test_start, test_end))
        
        yield train_indices, test_indices

def validate_with_purge(features, labels, timestamps, model,
                        n_splits=5):
    """
    Run purged cross-validation and return honest performance estimate.
    """
    scores = []
    
    for train_idx, test_idx in purged_kfold_split(timestamps, n_splits):
        X_train = features.iloc[train_idx]
        y_train = labels.iloc[train_idx]
        X_test = features.iloc[test_idx]
        y_test = labels.iloc[test_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict_proba(X_test)[:, 1]
        
        # Brier score for each fold
        brier = np.mean((y_pred - y_test.values) ** 2)
        scores.append(brier)
    
    return {
        'mean_brier': np.mean(scores),
        'std_brier': np.std(scores),
        'fold_scores': scores,
        'is_stable': np.std(scores) < 0.05
    }
```

**Add to backtest-agent template:**
All backtests must use purged cross-validation.
Standard train/test split is insufficient.
Log the purge and embargo parameters used.

---

## Part 2 — Feature Engineering

### 2.1 Financial Data Is Not What You Think

The book opens with a chapter that should change how you
think about your Polymarket data.

**The four types of financial data:**

1. **Fundamental data**: earnings, balance sheets — not applicable
2. **Market data**: prices, volumes, timestamps — your trades table
3. **Analytics**: derived statistics (ELO, Sharpe, Brier) — your traders table
4. **Alternative data**: non-traditional signals — trader text, social data

Your system is rich in types 2 and 3. Most systematic traders
only have type 2. Your ELO scores are type 3 analytics that
most people don't have for Polymarket. This is a genuine edge.

---

### 2.2 The Fractionally Differentiated Features Problem

One of the book's most original contributions.

**The problem:**
Financial time series (prices) are non-stationary — they have
trends and the statistical properties change over time.
ML models assume stationarity.

The standard fix is differencing: use returns (price changes)
instead of prices. This makes the series stationary.

**The problem with standard differencing:**
It destroys memory. Returns today have almost no correlation
with returns a month ago. You lose all the long-term information.

**Fractional differentiation:**
Use a fractional order d between 0 (raw prices, non-stationary)
and 1 (returns, no memory). Find the minimum d that achieves
stationarity while preserving maximum memory.

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

def get_weights(d, size):
    """
    Calculate weights for fractional differentiation.
    d: differentiation order (0 < d < 1)
    size: number of weights
    """
    w = [1.0]
    for k in range(1, size):
        w_ = -w[-1] / k * (d - k + 1)
        w.append(w_)
    return np.array(w[::-1])

def frac_diff(series, d, threshold=0.01):
    """
    Apply fractional differentiation to a time series.
    
    series: pandas Series (e.g. market prices over time)
    d: differentiation order
    threshold: minimum weight to include
    
    Returns stationary series that preserves long-term memory.
    """
    weights = get_weights(d, len(series))
    
    # Drop weights below threshold for efficiency
    weights_ = np.cumsum(abs(weights))
    weights_ /= weights_[-1]
    skip = weights_[weights_ > threshold].shape[0]
    
    result = {}
    for i in range(skip, len(series)):
        loc = series.index[i]
        if not np.isfinite(series.iloc[i]):
            continue
        result[loc] = np.dot(
            weights[-skip-1:],
            series.iloc[i-skip:i+1].values
        )
    
    return pd.Series(result)

def find_min_d(series, threshold=0.05):
    """
    Find minimum d that achieves stationarity.
    Tests d values from 0 to 1 in steps of 0.1.
    
    Returns: minimum d for stationarity
    """
    for d in np.arange(0, 1.1, 0.1):
        frac_series = frac_diff(series, d)
        adf_result = adfuller(frac_series.dropna(), maxlag=1,
                             regression='c', autolag=None)
        p_value = adf_result[1]
        if p_value < threshold:
            return round(d, 1)
    return 1.0  # full differencing needed

# Application to your market price data:
# Instead of using raw prices or simple returns,
# use fractionally differenced prices as features
# This preserves the memory of where prices have been
# while maintaining stationarity for ML models
```

**Practical application for your system:**
When engineering features from market price history,
apply fractional differentiation instead of simple returns.
This is particularly relevant for your particle filter
research — the state space should use fractionally
differenced prices, not raw prices.

---

### 2.3 Labelling: The Triple Barrier Method

Standard ML labelling for financial data (price went up = 1,
price went down = 0) is too simplistic. Lopez de Prado's
triple barrier method is more realistic.

**Three barriers:**
1. **Upper barrier**: take profit — price rises by threshold t1
2. **Lower barrier**: stop loss — price falls by threshold t2
3. **Vertical barrier**: time exit — position held too long

**The label is which barrier was hit first.**

```python
import pandas as pd
import numpy as np

def triple_barrier_labels(prices, events, pt_sl, molecule):
    """
    Apply triple barrier labelling to price series.
    
    Adapted for prediction market binary contracts.
    
    prices: Series of market prices over time
    events: DataFrame with columns:
        t1: vertical barrier (market resolution date)
        trgt: target return for horizontal barriers
    pt_sl: [profit_take_multiplier, stop_loss_multiplier]
    molecule: subset of events to process
    
    Returns: Series of labels {-1, 0, 1}
        1 = upper barrier hit (profit target reached)
       -1 = lower barrier hit (stop loss triggered)
        0 = vertical barrier hit (time exit)
    """
    out = events.loc[molecule].copy()
    
    if pt_sl[0] > 0:
        pt = pt_sl[0] * events.loc[molecule, 'trgt']
    else:
        pt = pd.Series(index=molecule, dtype=float)
    
    if pt_sl[1] > 0:
        sl = -pt_sl[1] * events.loc[molecule, 'trgt']
    else:
        sl = pd.Series(index=molecule, dtype=float)
    
    for loc, t1 in events.loc[molecule, 't1'].items():
        df0 = prices[loc:t1]
        df0 = (df0 / prices[loc] - 1) * events.at[loc, 'side']
        
        out.at[loc, 'sl'] = df0[df0 < sl[loc]].index.min()
        out.at[loc, 'pt'] = df0[df0 > pt[loc]].index.min()
    
    out['t1'] = out[['sl', 'pt', 't1']].dropna(how='all').min(axis=1)
    out['bin'] = np.where(out['t1'] == out['pt'], 1,
                 np.where(out['t1'] == out['sl'], -1, 0))
    
    return out['bin']

# For prediction markets specifically:
# Upper barrier = price reaches your confidence threshold (e.g. 0.75)
# Lower barrier = price falls to your stop level (e.g. 0.30)
# Vertical barrier = market resolves
# 
# This gives richer training labels than just "resolved YES/NO"
# because it captures whether your entry timing was good
```

---

### 2.4 Sample Weights: Not All Observations Are Equal

A subtle but important concept from the book.

**The problem:**
If a market has 1000 price observations but 800 of them are
in a quiet period with almost no activity, giving all 1000
equal weight biases your model toward quiet periods.

**Uniqueness weighting:**
Weight each observation by how unique it is —
observations in quiet, correlated periods get lower weight.
Observations during active, informative periods get higher weight.

```python
def get_sample_weights(timestamps, resolution_dates):
    """
    Calculate sample weights based on observation uniqueness.
    
    Observations that overlap with many others get lower weight.
    Observations that are unique get higher weight.
    
    timestamps: when each observation was made
    resolution_dates: when each associated market resolved
    
    Returns: array of weights summing to 1
    """
    # Count how many observations are "active" at each point
    overlaps = pd.Series(0, index=timestamps)
    
    for t_start, t_end in zip(timestamps, resolution_dates):
        mask = (timestamps >= t_start) & (timestamps <= t_end)
        overlaps[mask] += 1
    
    # Weight = 1 / overlap count (unique observations weighted higher)
    weights = 1.0 / overlaps
    weights /= weights.sum()
    
    return weights
```

**Application to your system:**
When training any ML model on your Polymarket trade data,
apply sample weights. Trades made during high-activity periods
(election days, major announcements) should receive higher weight
than trades made during quiet periods.

---

## Part 3 — Strategy Development

### 3.1 The Meta-Labelling Framework

Lopez de Prado's most practically useful framework for
building on top of existing signals.

**The concept:**
You already have a primary signal (your ELO-based elite trader
detection). Meta-labelling asks: given that the primary signal
fired, should you actually take this trade?

**Two-stage model:**
1. **Stage 1 (primary model)**: generates a signal direction
   (elite traders are buying YES)
2. **Stage 2 (meta-model)**: predicts whether this particular
   signal instance will be profitable

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import numpy as np

class MetaLabellingSystem:
    """
    Two-stage prediction system using meta-labelling.
    
    Stage 1: ELO-based signal detection (your existing system)
    Stage 2: Meta-model that filters signal quality
    """
    
    def __init__(self):
        # Primary model: already built (your ELO system)
        # Meta model: learns when to trust the primary signal
        self.meta_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=4,  # shallow to prevent overfitting
            min_samples_leaf=10
        )
        self.is_fitted = False
    
    def create_meta_features(self, signal_row):
        """
        Features for meta-model — context around each signal.
        
        These describe the CONDITIONS under which the primary
        signal fired, so the meta-model learns which conditions
        lead to good vs bad signals.
        """
        return {
            # Signal strength
            'n_legendary_traders': signal_row.get('n_legendary', 0),
            'avg_elo_score': signal_row.get('avg_elo', 0),
            'max_elo_score': signal_row.get('max_elo', 0),
            
            # Market conditions
            'market_price': signal_row.get('price', 0.5),
            'price_distance_from_50': abs(
                signal_row.get('price', 0.5) - 0.5
            ),
            'market_age_pct': signal_row.get('age_pct', 0.5),
            'market_volume': signal_row.get('volume', 0),
            
            # Position context
            'avg_position_size': signal_row.get('avg_size', 0),
            'position_size_vs_history': signal_row.get(
                'size_vs_history', 1.0
            ),
            
            # Timing
            'time_since_last_signal': signal_row.get(
                'time_since_last', 0
            ),
            'n_signals_today': signal_row.get('signals_today', 0)
        }
    
    def fit(self, historical_signals, outcomes):
        """
        Train meta-model on historical signal outcomes.
        
        historical_signals: list of signal context dicts
        outcomes: 1 if signal was profitable, 0 if not
        """
        X = pd.DataFrame([
            self.create_meta_features(s)
            for s in historical_signals
        ])
        y = np.array(outcomes)
        
        self.meta_model.fit(X, y)
        self.is_fitted = True
        
        # Feature importance tells you what makes signals good
        self.feature_importance = dict(zip(
            X.columns,
            self.meta_model.feature_importances_
        ))
    
    def should_trade(self, signal, min_probability=0.6):
        """
        Given a new signal, decide whether to trade.
        
        Returns: (trade_yes, probability, position_size_multiplier)
        """
        if not self.is_fitted:
            # If meta-model not trained yet, use primary signal only
            return True, 0.5, 1.0
        
        features = pd.DataFrame([self.create_meta_features(signal)])
        probability = self.meta_model.predict_proba(features)[0][1]
        
        trade = probability >= min_probability
        
        # Scale position size by meta-model confidence
        size_multiplier = probability if trade else 0
        
        return trade, probability, size_multiplier
```

**Why this is powerful for your system:**
Your signal-agent currently fires whenever elite trader convergence
is detected. Some of those signals are high quality, some are noise.
The meta-model learns to distinguish them — increasing your
effective approval rate without changing the primary signal logic.

**Expected improvement:**
The book shows meta-labelling typically improves precision
(fewer false positives) significantly while maintaining recall.
Applied to your system: fewer bad signals acted on, more
capital allocated to confirmed good signals.

---

### 3.2 Feature Importance

The book strongly advocates using feature importance to
understand what is actually driving predictions.

**Mean Decrease Impurity (MDI) — built into Random Forests:**
```python
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

def get_feature_importance_mdi(features, labels):
    """
    Calculate Mean Decrease Impurity feature importance.
    
    Tells you which features are actually driving predictions.
    Use this to prune useless features before model training.
    """
    clf = RandomForestClassifier(n_estimators=100, n_jobs=-1)
    clf.fit(features, labels)
    
    importance = pd.Series(
        clf.feature_importances_,
        index=features.columns
    ).sort_values(ascending=False)
    
    return importance

def get_feature_importance_mda(features, labels, timestamps,
                                n_splits=5):
    """
    Mean Decrease Accuracy — more reliable than MDI.
    
    Measures how much accuracy drops when each feature is shuffled.
    A feature that doesn't matter can be shuffled without penalty.
    """
    from sklearn.model_selection import KFold
    from sklearn.metrics import log_loss
    
    clf = RandomForestClassifier(n_estimators=100)
    kf = KFold(n_splits=n_splits)
    
    base_scores = []
    feature_scores = {col: [] for col in features.columns}
    
    for train_idx, test_idx in kf.split(features):
        X_train = features.iloc[train_idx]
        X_test = features.iloc[test_idx]
        y_train = labels.iloc[train_idx]
        y_test = labels.iloc[test_idx]
        
        clf.fit(X_train, y_train)
        base_score = log_loss(
            y_test, clf.predict_proba(X_test)
        )
        base_scores.append(base_score)
        
        for col in features.columns:
            X_shuffled = X_test.copy()
            X_shuffled[col] = X_shuffled[col].sample(
                frac=1
            ).values
            shuffled_score = log_loss(
                y_test,
                clf.predict_proba(X_shuffled)
            )
            feature_scores[col].append(
                shuffled_score - base_score
            )
    
    importance = pd.Series({
        col: np.mean(scores)
        for col, scores in feature_scores.items()
    }).sort_values(ascending=False)
    
    return importance
```

**Application to your system:**
Run MDA feature importance on your engineered features
from the database. Features with near-zero importance
should be dropped — they add noise without signal.
Features with high importance tell you what actually
predicts outcomes in Polymarket.

---

## Part 4 — Backtesting

### 4.1 The 7 Sins of Backtesting

Lopez de Prado's list of the most common backtesting errors.
Your backtest-agent must check for all of these.

**Sin 1 — Survivorship Bias**
Only including markets that completed and resolved.
Excluding markets that were cancelled or had no volume.
Fix: include all markets regardless of outcome.

**Sin 2 — Lookahead Bias**
Using information at time T that was only available after T.
Example: using a trader's ELO score that was calculated
using trades they made after the signal date.
Fix: reconstruct ELO scores as they would have been at
signal time, not as calculated today.

**Sin 3 — Data Snooping**
Testing the same data multiple times.
Every time you look at performance and adjust parameters,
you are data snooping.
Fix: use purged cross-validation, log all trials,
apply deflated Sharpe ratio.

**Sin 4 — Transaction Cost Neglect**
Polymarket charges fees on trades.
A strategy that shows Sharpe 1.5 before fees may show
Sharpe 0.8 after fees.
Fix: always include realistic transaction cost assumptions
in every backtest.

**Sin 5 — Volatility Clustering**
Assuming returns are independently distributed.
Financial returns cluster — volatile periods beget volatile periods.
Fix: use GARCH or HAR models for volatility estimation,
or at minimum use rolling volatility windows.

**Sin 6 — Shorting Bias**
Assuming you can always take the short side.
In prediction markets, liquidity may not always allow
selling YES at the price you want.
Fix: apply a liquidity filter — only trade markets with
volume above a minimum threshold.

**Sin 7 — Overfitting to Regime**
Strategy was developed during one market regime
(e.g. low volatility bull market) and fails in another.
Fix: test across multiple distinct time periods and
market conditions. Include at least one stress period.

```python
def check_backtest_sins(backtest_config, backtest_results):
    """
    Automated check for the 7 sins of backtesting.
    Returns list of warnings for backtest-agent to review.
    """
    warnings = []
    
    # Sin 1: Survivorship bias
    if not backtest_config.get('includes_cancelled_markets', False):
        warnings.append(
            "SIN 1: Survivorship bias risk — "
            "cancelled/low-volume markets excluded"
        )
    
    # Sin 2: Lookahead bias
    if not backtest_config.get('point_in_time_features', False):
        warnings.append(
            "SIN 2: Lookahead bias risk — "
            "confirm ELO scores are point-in-time"
        )
    
    # Sin 3: Data snooping
    n_trials = backtest_config.get('n_strategies_tested', 1)
    if n_trials > 5:
        warnings.append(
            f"SIN 3: Data snooping risk — "
            f"{n_trials} strategies tested. "
            f"Apply deflated Sharpe ratio."
        )
    
    # Sin 4: Transaction costs
    if not backtest_config.get('transaction_costs_included', False):
        warnings.append(
            "SIN 4: Transaction costs not included. "
            "Polymarket fee: ~2% per trade."
        )
    
    # Sin 5: Volatility
    if not backtest_config.get('volatility_adjusted', False):
        warnings.append(
            "SIN 5: Returns assumed i.i.d. "
            "Consider rolling volatility normalisation."
        )
    
    # Sin 6: Liquidity
    if not backtest_config.get('liquidity_filter', False):
        warnings.append(
            "SIN 6: No liquidity filter applied. "
            "Low-volume markets may not be tradeable."
        )
    
    # Sin 7: Regime
    n_periods = backtest_config.get('n_distinct_periods', 1)
    if n_periods < 2:
        warnings.append(
            "SIN 7: Only one time period tested. "
            "Strategy may be regime-specific."
        )
    
    return warnings
```

**Add to backtest-agent definition of done:**
All 7 sins must be checked and either cleared or
explicitly acknowledged with mitigation before approval.

---

### 4.2 Combinatorial Purged Cross-Validation (CPCV)

The book's most rigorous backtesting framework.
More thorough than standard walk-forward validation.

**The idea:**
Instead of one train/test split, generate all possible
combinations of train/test splits. This gives you a
distribution of Sharpe ratios, not just one number.

**Probability of Backtest Overfitting (PBO):**
The fraction of combinations where out-of-sample Sharpe
is negative, given that in-sample Sharpe is positive.

```python
from itertools import combinations
import numpy as np

def probability_backtest_overfitting(returns_matrix, n_splits=10):
    """
    Calculate Probability of Backtest Overfitting.
    
    returns_matrix: T x N matrix
        T = time periods
        N = different strategy variants tested
    n_splits: number of folds for CPCV
    
    Returns: PBO (0 = no overfitting, 1 = certain overfitting)
    """
    T, N = returns_matrix.shape
    fold_size = T // n_splits
    
    # Generate all combinations of train/test splits
    all_folds = list(range(n_splits))
    n_test_folds = n_splits // 2
    
    logit_values = []
    
    for test_folds in combinations(all_folds, n_test_folds):
        train_folds = [f for f in all_folds if f not in test_folds]
        
        # Build train and test indices
        train_idx = []
        test_idx = []
        for f in train_folds:
            train_idx.extend(range(f*fold_size, (f+1)*fold_size))
        for f in test_folds:
            test_idx.extend(range(f*fold_size, (f+1)*fold_size))
        
        # Find best strategy on training set
        train_sharpes = returns_matrix[train_idx].mean(axis=0) / \
                       returns_matrix[train_idx].std(axis=0)
        best_strategy = np.argmax(train_sharpes)
        
        # Evaluate best strategy on test set
        test_returns = returns_matrix[test_idx, best_strategy]
        test_sharpe = test_returns.mean() / test_returns.std()
        
        # Rank of best strategy on test set
        test_sharpes_all = returns_matrix[test_idx].mean(axis=0) / \
                          returns_matrix[test_idx].std(axis=0)
        rank = np.sum(test_sharpes_all < test_sharpe) / N
        
        # Logit of relative rank
        if 0 < rank < 1:
            logit_values.append(np.log(rank / (1 - rank)))
    
    # PBO = fraction with negative logit
    pbo = np.mean([l < 0 for l in logit_values])
    
    return {
        'pbo': pbo,
        'is_overfit': pbo > 0.5,
        'logit_mean': np.mean(logit_values)
    }
```

**Threshold for your system:**
PBO < 0.1 = strategy is genuinely robust
PBO 0.1-0.3 = borderline, needs more data
PBO > 0.3 = strategy is likely overfit, reject

---

## Part 5 — Execution and Portfolio Construction

### 5.1 The Efficiency Cost of Poor Execution

Even a strategy with genuine edge can lose money through
poor execution. In prediction markets:

- Entering at a worse price than expected (slippage)
- Trading in illiquid markets (moving the market against yourself)
- Timing entries poorly (entering just before a price spike)

**Minimum viable execution rules for your system:**

```python
def should_execute_trade(market_price, target_price,
                         market_volume, position_size,
                         max_market_impact=0.02):
    """
    Pre-trade execution check.
    
    market_price: current best price
    target_price: price at which signal was generated
    market_volume: total market volume (liquidity proxy)
    position_size: intended position size
    max_market_impact: maximum acceptable price impact
    
    Returns: (execute, reason)
    """
    # Price drift check: has price moved too far since signal?
    price_drift = abs(market_price - target_price) / target_price
    if price_drift > 0.05:
        return False, f"Price drifted {price_drift:.1%} since signal"
    
    # Liquidity check: position too large for market?
    market_impact = position_size / max(market_volume, 1)
    if market_impact > max_market_impact:
        return False, (
            f"Position size {position_size} too large "
            f"for market volume {market_volume}"
        )
    
    # Minimum volume filter
    if market_volume < 1000:
        return False, "Market volume below minimum threshold"
    
    return True, "Execution approved"
```

---

### 5.2 Hierarchical Risk Parity (HRP)

Lopez de Prado's alternative to mean-variance optimisation
for portfolio construction across multiple positions.

**Why standard portfolio optimisation fails for prediction markets:**
Mean-variance optimisation (Markowitz) requires estimating
a covariance matrix. With limited history and many markets,
this estimate is extremely noisy. Small errors in covariance
estimates produce wildly unstable portfolio weights.

**HRP uses hierarchical clustering instead:**

```python
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform

def hierarchical_risk_parity(returns_matrix):
    """
    Hierarchical Risk Parity portfolio weights.
    
    More robust than mean-variance for correlated markets.
    
    returns_matrix: DataFrame of strategy/market returns
    Returns: dict of weights summing to 1
    """
    # Correlation matrix
    corr = returns_matrix.corr()
    
    # Convert to distance matrix
    dist = np.sqrt((1 - corr) / 2)
    
    # Hierarchical clustering
    link = linkage(squareform(dist), method='single')
    
    # Quasi-diagonalise
    sort_idx = _get_quasi_diag(link)
    sorted_corr = corr.iloc[sort_idx, sort_idx]
    
    # Recursive bisection for weights
    weights = _recursive_bisection(
        returns_matrix.iloc[:, sort_idx]
    )
    
    # Reorder to original order
    weights = weights.reindex(returns_matrix.columns)
    
    return weights.to_dict()

def _get_quasi_diag(link):
    """Sort clustered items by distance."""
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    num_items = link[-1, 3]
    
    while sort_ix.max() >= num_items:
        sort_ix.index = range(0, sort_ix.shape[0]*2, 2)
        df0 = sort_ix[sort_ix >= num_items]
        i = df0.index
        j = df0.values - num_items
        sort_ix[i] = link[j, 0]
        df0 = pd.Series(link[j, 1], index=i+1)
        sort_ix = pd.concat([sort_ix, df0])
        sort_ix = sort_ix.sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    
    return sort_ix.tolist()

def _recursive_bisection(returns):
    """Assign weights via recursive bisection."""
    weights = pd.Series(1.0, index=returns.columns)
    cluster_items = [returns.columns.tolist()]
    
    while cluster_items:
        cluster_items = [
            i[j:k]
            for i in cluster_items
            for j, k in ((0, len(i)//2), (len(i)//2, len(i)))
            if len(i) > 1
        ]
        for i in range(0, len(cluster_items), 2):
            cluster_0 = cluster_items[i]
            cluster_1 = cluster_items[i+1]
            
            var_0 = _get_cluster_var(returns[cluster_0])
            var_1 = _get_cluster_var(returns[cluster_1])
            
            alpha = 1 - var_0 / (var_0 + var_1)
            
            weights[cluster_0] *= alpha
            weights[cluster_1] *= 1 - alpha
    
    return weights

def _get_cluster_var(returns):
    """Calculate cluster variance for HRP."""
    cov = returns.cov()
    w = pd.Series(1.0 / np.diag(cov), index=cov.columns)
    w /= w.sum()
    return float(np.dot(w, np.dot(cov, w)))
```

**When to use HRP:**
Once you have 5+ simultaneous open positions across
correlated prediction markets, HRP gives more stable
portfolio weights than equal weighting or mean-variance.
Start with equal weighting — implement HRP when you have
enough history to make it meaningful.

---

## Part 6 — Key Improvements to Your Current System

### Immediate (Add Before Server Arrives)

**1. Update backtest-agent definition of done:**
```
OLD: Sharpe ratio > 1.0
NEW: Deflated Sharpe Ratio > 0.95, log n_trials honestly

OLD: Minimum 30 trades
NEW: Minimum 30 trades + purged cross-validation

OLD: Check lint passes
NEW: Check 7 sins of backtesting cleared
```

**2. Add to quant-research pre-registration:**
Before starting any research phase, document:
- How many strategies will be tested
- What constitutes a genuine improvement
- What data period will be held out as test set
- How point-in-time features will be constructed

**3. Add transaction costs to all backtests:**
Polymarket charges approximately 2% per trade.
Any strategy with gross Sharpe < 1.5 may be below 1.0
after transaction costs. All backtests must include this.

### Medium Term (When System Is Running)

**4. Implement meta-labelling on signal-agent output:**
Train a meta-model on historical signal outcomes.
Filter signals by meta-model confidence before acting.
Expected result: higher precision, fewer wasted trades.

**5. Apply fractional differentiation to price features:**
Replace raw prices and simple returns with fractionally
differenced series. Preserves memory while achieving
stationarity. Improves all ML models trained on price data.

**6. Implement HRP for portfolio allocation:**
When running 5+ simultaneous positions, use HRP weights
instead of equal weighting. Reduces correlation-driven
drawdowns.

---

## Quick Reference: Lopez de Prado vs Dixon

| Topic | Dixon et al | Lopez de Prado |
|-------|------------|----------------|
| Focus | Methods | Rigour |
| Backtesting | Standard validation | CPCV + DSR |
| Features | Engineering techniques | Fractional diff + labelling |
| Portfolio | Risk metrics | HRP |
| Key concept | What to build | How to avoid fooling yourself |
| Difficulty | Graduate textbook | Practitioner handbook |
| Read first? | Yes | After Dixon |

**One sentence summary:**
Dixon teaches you the tools. Lopez de Prado teaches you
not to lie to yourself when using them.

---

## Key Formulas Quick Reference

```
Deflated Sharpe:   DSR = Φ[(SR* - E[max SR]) * sqrt(T-1)]
                   Target: DSR > 0.95

Fractional Diff:   (1-L)^d * x_t, where 0 < d < 1
                   Find minimum d for stationarity

Triple Barrier:    Label = which barrier hit first
                   {profit_target, stop_loss, time_exit}

PBO:               Fraction of CPCV combinations where
                   out-of-sample Sharpe is negative
                   Target: PBO < 0.1

HRP Weight:        Recursive bisection on clustered corr matrix
                   More stable than Markowitz weights
```

---

*Notes compiled for trading-swarm quant-research agent.*
*Reference: Lopez de Prado — Advances in Financial Machine Learning (2018)*
*Wiley. ISBN 978-1-119-48208-6*
