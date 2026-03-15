# Definition of Done

## Trading System / Strategy PR
- [ ] PR created, branch clean, no merge conflicts
- [ ] Lint passes with zero errors
- [ ] Backtest runs without exception
- [ ] Sharpe ratio calculated and meets threshold (>1.0)
- [ ] P&L metrics exported to brain/kpis.md
- [ ] No hardcoded API keys or credentials
- [ ] Output file verified by immune system (not self-reported)
- [ ] At least one AI review passes
- [ ] Telegram notification sent with metrics summary

## Quant Research Output
- [ ] Brier score calculated and logged (target <0.20)
- [ ] Results compared against previous model version
- [ ] Findings written to brain/strategy-notes/
- [ ] Signal written to brain/signals.json for backtest-agent

## New Market Connector / Data Tool
- [ ] Live data confirmed (not mocked)
- [ ] Error handling for API downtime included
- [ ] Reconnection logic tested
- [ ] Added to market registry

## Any Task (Universal)
- [ ] Agent did NOT self-report success
- [ ] Immune system verified output independently
- [ ] Result logged to brain/agent-outputs/
- [ ] feedback.json updated with outcome and reason

## Upgraded Backtest Standards (Lopez de Prado)

### Deflated Sharpe Ratio
- [ ] Number of strategies tested logged honestly (every attempt counts)
- [ ] Deflated Sharpe Ratio (DSR) calculated and > 0.95
- [ ] Raw Sharpe > 1.0 is necessary but NOT sufficient alone

### The 7 Sins Check
- [ ] SIN 1: Cancelled/low-volume markets included (no survivorship bias)
- [ ] SIN 2: ELO scores reconstructed point-in-time (no lookahead bias)
- [ ] SIN 3: All strategy variants tested logged (data snooping check)
- [ ] SIN 4: Polymarket ~2% transaction cost included in all returns
- [ ] SIN 5: Volatility clustering acknowledged (rolling vol used)
- [ ] SIN 6: Liquidity filter applied (min volume threshold enforced)
- [ ] SIN 7: Tested across minimum 2 distinct time periods

### Validation Method
- [ ] Purged cross-validation used (not standard train/test split)
- [ ] Purge and embargo parameters logged
- [ ] PBO (Probability of Backtest Overfitting) calculated and < 0.1
