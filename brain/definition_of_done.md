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
