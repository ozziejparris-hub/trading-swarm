# Machine Learning in Finance — Agent Reference Notes
# Dixon, Halperin, Bilokon (2020)
# Extracted and filtered for Polymarket trading intelligence system
# Full book: 565 pages. These notes cover what's directly applicable.

---

## How to Use These Notes

This file is pre-filtered for your specific use case: prediction market
trading, trader behaviour analysis, and quantitative signal generation
using Polymarket data. Chapters with no practical relevance (fixed income,
credit derivatives, high-frequency equity microstructure) are omitted.

Each section includes: what the book says, why it matters for your system,
and what to build or investigate next.

---

## Part 1 — Supervised Learning for Financial Prediction

### 1.1 The Core Problem: Prediction vs Inference

The book draws a sharp distinction between two goals:
- **Inference**: understanding WHY something happens (statistics)
- **Prediction**: accurately forecasting WHAT will happen (ML)

For your system, you are doing prediction. This matters because:
- Traditional statistical tests (p-values, confidence intervals) are
  less important than out-of-sample predictive accuracy
- A model that "makes sense" economically but predicts poorly is
  worse than a model that predicts well even if you can't explain it
- Your validation metric (Brier score) is a prediction metric, not
  an inference metric. This is the correct choice.

**Implication for your system:**
Your backtest-agent should prioritise Brier score and Sharpe ratio
over model interpretability. A black-box model that predicts well
beats a transparent model that predicts poorly.

---

### 1.2 Feature Engineering for Financial Data

The book dedicates significant space to feature engineering because
raw financial data is almost never directly useful for ML models.

**Key transformations relevant to your data:**

1. **Returns vs levels**: Never use raw prices or ELO scores directly
   as features. Use changes (returns, ELO deltas) instead.
   - Raw ELO: 1847 → not useful as-is
   - ELO change over 30 days: +127 → useful signal

2. **Normalisation across traders**: ELO scores need to be normalised
   relative to the population distribution, not used as absolute values.
   A trader at ELO 2000 means something different if the population
   mean is 1200 vs 1600.

3. **Rolling window features**: Compute features over multiple
   time windows simultaneously (7-day, 30-day, 90-day).
   Different signals operate at different timescales.

4. **Interaction features**: Some signals only matter in combination.
   Example: large position size is only a strong signal when combined
   with high ELO. Either alone is weaker.

**Features worth engineering from your database:**

From `traders` table:
- ELO percentile rank (not raw score)
- ELO velocity (rate of change over last 30/90 days)
- Win rate by market category
- Average position size (normalised by market liquidity)

From `trades` table:
- Time to entry (how early relative to market close)
- Position size relative to trader's own historical average
- Entry timing relative to price movement

From `markets` table:
- Market age at time of trade (% of lifespan elapsed)
- Liquidity (total volume)
- Price distance from 50 cents (uncertainty measure)

---

### 1.3 The Overfitting Problem in Finance

The book is unusually direct about overfitting — it calls it the
single biggest failure mode in quantitative finance.

**Why finance is especially vulnerable:**
- Financial data has very low signal-to-noise ratio
- Time series data has serial correlation — observations are not
  independent, which violates assumptions of most ML methods
- "Backtest overfitting": a strategy that looks good historically
  may have been curve-fitted to past data

**The multiple testing problem:**
If you test 100 strategies and accept anything with Sharpe > 1.0,
you will find ~5 strategies by pure chance even if none have
real edge. Your backtest-agent's 30-trade minimum is a start
but is not sufficient alone.

**The book's recommended safeguards:**

1. **Walk-forward validation**: never test on data used in development.
   Split data into: training (60%) → validation (20%) → test (20%).
   Only use test set once. If you look at test set during development,
   it becomes validation set and you need fresh test data.

2. **Deflated Sharpe Ratio**: adjusts Sharpe ratio downward based on
   how many strategies were tried before finding this one.
   The more strategies tested, the higher the required Sharpe threshold.

3. **Out-of-sample period**: require that the strategy works on a
   time period completely excluded from all development.

**Implication for your backtest-agent:**
Add a walk-forward validation requirement to definition of done.
The current Sharpe > 1.0 threshold should become:
- Training Sharpe > 1.2
- Out-of-sample Sharpe > 0.8
- Test set used only once, never during development

---

## Part 2 — Probabilistic Methods

### 2.1 Bayesian Inference and Prediction Markets

The book's Bayesian chapters are directly applicable to prediction
market probability estimation.

**The core Bayesian framework:**
- Start with a prior belief about an event probability
- Update it as new evidence arrives
- The posterior is your best current estimate

For prediction markets specifically:
- Prior = current market price (efficient market assumption)
- Evidence = elite trader positions, volume, price movement
- Posterior = your updated probability estimate

**Why this matters:**
The market price is not always the best prior. When elite traders
(ELO >1800) have taken positions, the market price may lag their
information. Your signal-agent is essentially doing Bayesian updating:
"given that legendary traders have entered YES, what is the updated
probability beyond the current market price?"

**Conjugate priors for binary outcomes:**
For binary events (YES/NO prediction markets), the Beta distribution
is the natural prior. It is defined on [0,1] and updates cleanly.

```python
# Simple Bayesian update for binary market
from scipy.stats import beta

def update_probability(prior_alpha, prior_beta, elite_yes, elite_no):
    """
    Update probability estimate given elite trader positions.
    
    prior_alpha, prior_beta: Beta distribution parameters
    Uninformative prior: alpha=1, beta=1 (uniform)
    Market-implied prior: alpha=price*n, beta=(1-price)*n
    
    elite_yes: number of elite traders (ELO>1800) on YES
    elite_no: number of elite traders (ELO>1800) on NO
    """
    posterior_alpha = prior_alpha + elite_yes
    posterior_beta = prior_beta + elite_no
    
    posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
    
    dist = beta(posterior_alpha, posterior_beta)
    ci_low, ci_high = dist.interval(0.95)
    
    return {
        'probability': posterior_mean,
        'ci_95': (ci_low, ci_high),
        'confidence': posterior_alpha + posterior_beta
    }

# Example: market at 0.60, 5 legendary traders on YES, 1 on NO
# Market-implied prior with n=20 pseudo-observations
result = update_probability(
    prior_alpha=0.60 * 20,
    prior_beta=0.40 * 20,
    elite_yes=5,
    elite_no=1
)
print(f"Updated probability: {result['probability']:.3f}")
print(f"95% CI: {result['ci_95']}")
```

---

### 2.2 Gaussian Processes for Probability Estimation

The book covers Gaussian Processes (GPs) as a Bayesian non-parametric
method. For your use case, GPs are useful for:

1. **Probability path modelling**: fitting a smooth curve to how
   a market's price evolves over its lifetime
2. **Uncertainty quantification**: unlike point estimates, GPs give
   you a full probability distribution over predictions
3. **Small data problems**: GPs work well when you have limited
   historical data for a specific market type

**When to use GPs vs other methods:**
- GPs: when you need uncertainty estimates and have <1000 data points
- Neural networks: when you have >10,000 data points and need scalability
- Linear models: when interpretability matters more than accuracy

For your Phase 1 research (Brier score calibration), GPs are
worth investigating as a calibration method for ELO-based predictions.

---

### 2.3 Calibration — The Most Important Concept in the Book

The book's treatment of calibration is the most directly relevant
section for your system.

**Definition:**
A probabilistic model is well-calibrated if, among all events
it assigns probability p, approximately p% of them actually occur.

**The calibration curve:**
Plot predicted probability (x-axis) vs actual frequency (y-axis).
A perfectly calibrated model lies on the diagonal y=x.

- If curve is below diagonal: model is overconfident
- If curve is above diagonal: model is underconfident
- If curve is S-shaped: model is overconfident in extremes,
  underconfident in middle

**Why your ELO system probably needs calibration:**
ELO scores measure relative skill, not absolute probability.
An ELO score of 2000 tells you a trader is better than average
but doesn't directly translate to "their positions are right 70%
of the time." The calibration curve tells you the actual relationship.

**Platt Scaling — the simplest calibration fix:**
```python
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import calibration_curve
import numpy as np

def calibrate_elo_predictions(elo_scores, outcomes):
    """
    Calibrate ELO-based probability predictions using Platt scaling.
    
    elo_scores: array of ELO scores for predictions made
    outcomes: array of 0/1 actual outcomes
    
    Returns a calibrated probability for a given ELO score.
    """
    # Convert ELO to raw probability (sigmoid)
    raw_probs = 1 / (1 + np.exp(-elo_scores / 400))
    
    # Fit logistic regression to calibrate
    calibrator = LogisticRegression()
    calibrator.fit(raw_probs.reshape(-1, 1), outcomes)
    
    return calibrator

def plot_calibration(raw_probs, calibrated_probs, outcomes):
    """
    Compare calibration curves before and after.
    Returns calibration data for analysis.
    """
    raw_fraction_pos, raw_mean_pred = calibration_curve(
        outcomes, raw_probs, n_bins=10
    )
    cal_fraction_pos, cal_mean_pred = calibration_curve(
        outcomes, calibrated_probs, n_bins=10
    )
    
    return {
        'before': {'predicted': raw_mean_pred,
                   'actual': raw_fraction_pos},
        'after': {'predicted': cal_mean_pred,
                  'actual': cal_fraction_pos}
    }
```

**This is your Phase 1 research target.**
Run this on your resolved markets in `polymarket_tracker.db`.
The calibration curve will tell you exactly where your ELO
system over- and under-estimates probability.

---

## Part 3 — Sequential and Reinforcement Learning

### 3.1 Sequential Decision Making Framework

The book frames trading as a sequential decision problem:
at each time step, an agent observes state, takes action,
receives reward, and transitions to new state.

**Mapping to your system:**

| RL Concept | Your System Equivalent |
|------------|----------------------|
| State | Current market prices, ELO signals, trader positions |
| Action | Enter YES / Enter NO / Stay out |
| Reward | P&L, Brier score improvement |
| Policy | Your signal + sizing rules |
| Value function | Expected future P&L from current state |

**Why this framing matters:**
Most trading systems treat each trade as independent. Sequential
framing recognises that decisions interact — a position taken now
affects what positions make sense later (portfolio correlation,
capital allocation, risk budget).

---

### 3.2 Q-Learning for Trading

Q-learning is the simplest practical RL algorithm for trading.
It learns a Q-function: Q(state, action) = expected cumulative reward.

**Minimal implementation for prediction markets:**

```python
import numpy as np
from collections import defaultdict

class PolymarketQLearner:
    """
    Simple Q-learning agent for prediction market position sizing.
    
    States: (elo_signal_strength, market_price, time_to_close)
    Actions: 0=stay_out, 1=small_position, 2=medium_position, 3=large_position
    """
    
    def __init__(self, alpha=0.1, gamma=0.95, epsilon=0.1):
        self.alpha = alpha      # learning rate
        self.gamma = gamma      # discount factor
        self.epsilon = epsilon  # exploration rate
        self.q_table = defaultdict(lambda: np.zeros(4))
    
    def discretise_state(self, elo_signal, price, time_remaining):
        """Convert continuous state to discrete bins."""
        elo_bin = min(int(elo_signal / 0.5), 3)      # 0-3
        price_bin = min(int(price / 0.25), 3)          # 0-3
        time_bin = min(int(time_remaining / 0.25), 3)  # 0-3
        return (elo_bin, price_bin, time_bin)
    
    def choose_action(self, state):
        """Epsilon-greedy action selection."""
        if np.random.random() < self.epsilon:
            return np.random.randint(4)  # explore
        return np.argmax(self.q_table[state])  # exploit
    
    def update(self, state, action, reward, next_state):
        """Q-learning update rule."""
        current_q = self.q_table[state][action]
        max_next_q = np.max(self.q_table[next_state])
        new_q = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )
        self.q_table[state][action] = new_q
    
    def train_on_history(self, historical_trades):
        """
        Train on historical trade data from polymarket_tracker.db.
        
        historical_trades: list of dicts with keys:
            elo_signal, price, time_remaining, action_taken, pnl
        """
        for i, trade in enumerate(historical_trades[:-1]):
            state = self.discretise_state(
                trade['elo_signal'],
                trade['price'],
                trade['time_remaining']
            )
            next_state = self.discretise_state(
                historical_trades[i+1]['elo_signal'],
                historical_trades[i+1]['price'],
                historical_trades[i+1]['time_remaining']
            )
            self.update(state, trade['action_taken'],
                       trade['pnl'], next_state)
```

**Important caveat from the book:**
Q-learning with discrete states works for simple problems.
For complex state spaces, Deep Q-Networks (DQN) are needed.
Start with Q-learning and only move to DQN if Q-learning
clearly saturates. Do not over-engineer early.

---

### 3.3 Reward Function Design

The book dedicates a full chapter to reward function design
because the wrong reward function produces perverse behaviour.

**Common mistakes:**
1. **Sparse rewards**: only rewarding at market resolution means
   the agent gets no learning signal during the market's life.
   Better: provide intermediate rewards based on position P&L.

2. **Pure P&L reward**: maximising P&L ignores risk.
   Better: reward = P&L / max_drawdown (Calmar ratio)
   Or: reward = P&L - lambda * variance (risk-penalised)

3. **Reward hacking**: agents find unexpected ways to maximise
   reward that violate intent. Example: an agent that avoids
   all markets (zero trades) has zero drawdown and zero losses.

**Recommended reward for your system:**
```python
def compute_reward(pnl, position_size, max_drawdown,
                   brier_improvement, risk_lambda=0.5):
    """
    Composite reward balancing P&L, risk, and calibration.
    
    pnl: profit/loss on the trade
    position_size: fraction of capital committed
    max_drawdown: worst drawdown during position
    brier_improvement: improvement in Brier score vs baseline
    risk_lambda: how much to penalise risk (tune this)
    """
    # Base P&L reward
    pnl_reward = pnl / position_size  # normalise by size
    
    # Risk penalty
    risk_penalty = risk_lambda * abs(max_drawdown)
    
    # Calibration bonus
    calibration_bonus = 0.2 * brier_improvement
    
    return pnl_reward - risk_penalty + calibration_bonus
```

---

### 3.4 Inverse Reinforcement Learning (IRL)

IRL asks: given observed behaviour, what reward function is
the agent optimising for?

**Application to your legendary traders:**
Your ELO >2175 traders are expert demonstrators. IRL can
infer what objective function they are implicitly optimising.

**Maximum Entropy IRL (the most practical algorithm):**
```python
def maxent_irl_features(trades_df, feature_columns):
    """
    Extract state-action features for MaxEnt IRL.
    
    trades_df: DataFrame from polymarket_tracker.db
    feature_columns: list of state features to use
    
    Returns feature expectations for expert trajectories.
    """
    expert_trajectories = trades_df[
        trades_df['elo_score'] > 2175
    ]
    
    # Feature expectations under expert policy
    expert_feature_expectations = expert_trajectories[
        feature_columns
    ].mean()
    
    return expert_feature_expectations
```

**Practical note:** Full IRL is computationally expensive.
For a first pass, compare the feature distributions of
legendary traders vs random traders. The features where
they differ most are proxies for their reward function.
This is simpler than full IRL and often just as informative.

---

## Part 4 — Deep Learning for Finance

### 4.1 When to Use Deep Learning

The book is measured about deep learning — it works well in
specific conditions and poorly in others.

**Deep learning works well when:**
- Large datasets (>10,000 labelled examples)
- High-dimensional inputs (images, text, many features simultaneously)
- Non-linear relationships that can't be captured by feature engineering

**Deep learning works poorly when:**
- Small datasets (your resolved markets may be limited)
- Interpretability is required
- Overfitting risk is high (financial data)

**For your system:**
Your current dataset of resolved markets may be too small for
deep learning to outperform simpler methods. The book recommends:
start with gradient boosting (XGBoost/LightGBM) before neural networks.
Gradient boosting handles tabular financial data extremely well
and is much less prone to overfitting.

---

### 4.2 LSTM for Sequential Market Data

If you do use deep learning, LSTMs (Long Short-Term Memory networks)
are the book's recommended architecture for sequential financial data.

**Why LSTMs for prediction markets:**
- They can learn long-term dependencies (a trader's behaviour
  three weeks ago may predict their behaviour today)
- They handle variable-length sequences (markets have different lifespans)
- They can process multiple simultaneous time series

**Minimal LSTM for trader behaviour:**
```python
import torch
import torch.nn as nn

class TraderBehaviourLSTM(nn.Module):
    """
    LSTM to model trader behaviour sequences.
    
    Input: sequence of (price, elo_signal, volume, time_remaining)
    Output: probability of YES outcome
    """
    def __init__(self, input_size=4, hidden_size=64,
                 num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        # x shape: (batch, sequence_length, input_size)
        lstm_out, _ = self.lstm(x)
        # Use last timestep output
        last_output = lstm_out[:, -1, :]
        return self.sigmoid(self.fc(last_output))
```

**Practical note:** Only attempt LSTM after simpler methods
(logistic regression, gradient boosting) have been validated.
The book is explicit: complexity should be justified by
performance improvement on out-of-sample data.

---

### 4.3 Attention Mechanisms and Transformers

The book's most forward-looking chapter covers attention mechanisms.

**Relevance to your system:**
Attention lets a model learn which parts of the input to focus on.
For prediction markets, this could learn:
- Which traders' positions are most predictive for each market type
- Which time periods in a market's history matter most
- Which market features deserve most weight

**This is future research, not immediate priority.**
Transformers require substantial data and compute.
File under Direction research but do not implement before
simpler models are validated.

---

## Part 5 — Risk Management

### 5.1 Kelly Criterion and Position Sizing

The book's treatment of Kelly criterion is the most practical
section for immediate implementation.

**The Kelly formula:**
```
f* = (bp - q) / b

where:
f* = fraction of capital to bet
b  = net odds received (profit per unit staked)
p  = probability of winning
q  = probability of losing (1-p)
```

**For prediction markets (binary outcomes):**
If a market is at price 0.40 and your model says true
probability is 0.55:
```python
def kelly_fraction(model_prob, market_price, max_fraction=0.25):
    """
    Calculate Kelly-optimal position size for a binary market.
    
    model_prob: your model's probability estimate
    market_price: current market price (= implied probability)
    max_fraction: cap to prevent overbetting (full Kelly is too aggressive)
    
    Returns: fraction of capital to commit
    """
    if model_prob <= market_price:
        return 0  # no edge, don't bet
    
    # Net odds: if price is 0.40, winning pays (1-0.40)/0.40 = 1.5x
    b = (1 - market_price) / market_price
    p = model_prob
    q = 1 - model_prob
    
    kelly = (b * p - q) / b
    
    # Use fractional Kelly (half-Kelly is standard)
    # Full Kelly maximises growth but has huge variance
    half_kelly = kelly * 0.5
    
    return min(half_kelly, max_fraction)

# Example
fraction = kelly_fraction(
    model_prob=0.55,
    market_price=0.40
)
print(f"Kelly fraction: {fraction:.3f}")
# Output: Kelly fraction: 0.125 (commit 12.5% of capital)
```

**The book's key warning about Kelly:**
Kelly assumes you know the true probability. If your model's
probability estimate is wrong by even a small amount, Kelly
can recommend overbetting. Always use fractional Kelly (0.25-0.5x)
and never bet more than your max_fraction cap.

---

### 5.2 Value at Risk and Expected Shortfall

For portfolio-level risk management across multiple open positions:

```python
import numpy as np

def portfolio_var(position_pnls, confidence=0.95):
    """
    Calculate Value at Risk for a portfolio of prediction market positions.
    
    position_pnls: list of historical P&L values for each position
    confidence: VaR confidence level (0.95 = 95%)
    
    Returns: VaR (maximum expected loss at given confidence)
    """
    combined_pnl = np.sum(position_pnls, axis=0)
    var = np.percentile(combined_pnl, (1 - confidence) * 100)
    
    # Expected Shortfall (CVaR) — average loss beyond VaR
    es = combined_pnl[combined_pnl <= var].mean()
    
    return {
        'var': var,
        'expected_shortfall': es,
        'confidence': confidence
    }
```

**Practical application:**
Before entering a new position, check that adding it to your
portfolio doesn't push VaR beyond your risk budget. This is
what prevents correlated losses when multiple related markets
move against you simultaneously.

---

### 5.3 Drawdown Management

The book's most actionable risk management section:

**Maximum drawdown formula:**
```python
def calculate_max_drawdown(equity_curve):
    """
    Calculate maximum peak-to-trough drawdown.
    
    equity_curve: array of cumulative P&L values
    Returns: maximum drawdown as a fraction
    """
    peak = equity_curve[0]
    max_dd = 0
    
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_dd:
            max_dd = drawdown
    
    return max_dd

# Add to your backtest validation threshold
# The book suggests max drawdown > 30% warrants rejection
# for most systematic strategies
```

---

## Part 6 — Most Relevant Chapters by Research Phase

### Phase 1 (Brier score calibration):
- Chapter 3: Evaluation metrics — Brier score, log loss, calibration
- Chapter 7: Probabilistic calibration — Platt scaling, isotonic regression
- Chapter 9: Bayesian methods — Beta-Binomial model for binary outcomes

### Phase 2 (Particle filter):
- Chapter 8: Sequential methods — particle filters, Kalman filters
- Chapter 10: State space models — dynamic probability estimation

### Phase 3 (Monte Carlo):
- Chapter 11: Simulation methods — Monte Carlo for option pricing
  (adapt for binary prediction market pricing)
- Chapter 12: Variance reduction — antithetic variates, control variates

### Phase 4 (Correlation modelling):
- Chapter 14: Copula models — tail dependence, t-copula
- Chapter 15: Factor models — shared risk factors across correlated markets

### Phase 5 (RL for position sizing):
- Chapter 16: Reinforcement learning basics — MDP formulation
- Chapter 17: Q-learning and Deep Q-Networks
- Chapter 18: Policy gradient methods
- Chapter 19: Inverse reinforcement learning

---

## Summary: Priority Reading Order for Your Quant-Research Agent

1. **Chapter 3** (evaluation metrics) — before any research starts
2. **Chapter 7** (calibration) — Phase 1 foundation
3. **Chapter 9** (Bayesian) — Bayesian updating of ELO signals
4. **Chapter 8** (sequential) — particle filter implementation
5. **Chapter 16-17** (RL basics) — position sizing research
6. **Chapter 14** (copulas) — correlation modelling

Everything else is optional or longer-term.

---

## Key Formulas Quick Reference

```
Brier Score:     BS = (1/N) * Σ(f_i - o_i)²
                 f_i = predicted probability, o_i = actual outcome
                 Target: BS < 0.20, Excellent: BS < 0.10

Kelly Fraction:  f* = (bp - q) / b
                 Use 0.5x Kelly. Cap at 25% of capital.

Sharpe Ratio:    SR = (R_p - R_f) / σ_p
                 Minimum acceptable: 1.0
                 Good: > 1.5, Excellent: > 2.0

Calmar Ratio:    CR = Annual Return / Max Drawdown
                 Alternative to Sharpe, penalises drawdown

Beta Posterior:  posterior = Beta(alpha + wins, beta + losses)
                 Use for Bayesian probability updates
```

---

*Notes compiled for trading-swarm quant-research agent.*
*Reference: Dixon, Halperin, Bilokon — Machine Learning in Finance (2020)*
*Springer. ISBN 978-3-030-41068-1*
