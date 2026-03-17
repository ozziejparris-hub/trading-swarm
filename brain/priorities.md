# Current Priorities

Last updated: 2026-03-17
Updated by: Oscar (pre-server setup phase)

---

## System Status
Pre-production. Server not yet arrived.
All architecture complete. Agents ready to deploy.
Polymarket monitoring system running independently on Windows.

---

## Priority 1 — Validate Foundations (Week 1-2)
**Do this before anything else.**

Run RQ1.1 (ELO persistence) and RQ3.2 (crowd vs elite
divergence) as the first two research tasks.

These are stopping-rule questions. If either fails,
halt all other research and reassess the system's
core premise before continuing.

RQ1.1: Does ELO in period T predict Brier score in T+1?
RQ3.2: Does elite consensus outperform raw market price?

Both tests use polymarket_tracker.db directly.
Both are runnable by quant-research-agent on day one.

---

## Priority 2 — Get One Agent Running Stably (Week 1)
Before running multiple agents, get signal-agent
running cleanly in a single tmux session with:
- Telegram notifications firing correctly
- Output files being written to brain/agent-outputs/
- Immune system verifying outputs
- Registry correctly tracking the session

Do not spawn multiple agents until one is stable.
Scale only after stability is confirmed.

---

## Priority 3 — Quant Research Phase 1 (Week 2-4)
Once foundations are validated (Priority 1 passed):

Run research questions in this order:
1. RQ1.1 — ELO persistence
2. RQ3.2 — Crowd vs elite divergence
3. RQ2.1 — Elite convergence edge (main signal test)
4. RQ1.2 — Skill tier stability
5. RQ4.1 — Kelly alignment vs Sharpe ratio

Each question follows pre-registration protocol:
write hypothesis first, wait for approval signal,
then run the test. Never skip pre-registration.

Reference: brain/strategy-notes/research-directions.md

---

## Priority 4 — Connect Polymarket System to Swarm (Week 2)
The existing Polymarket monitoring system runs
independently on Windows. When server is live:

- Transfer polymarket_tracker.db to server
- Confirm signal-agent can read it (read-only)
- Confirm P&L worker and ELO modifier scripts
  transfer cleanly to Linux environment
- Do not interrupt the monitoring system during transfer

Key database: polymarket_tracker.db (1581 MB)
Key scripts: apply_full_elo_modifiers.py,
             trading_behavior_analysis.py,
             analysis_scheduler.py (with Phases 2b/2c/3b)

---

## Priority 5 — Reference Library Activation (Ongoing)
The brain/reference-library/ contains notes from:
- Dixon, Halperin, Bilokon — ML in Finance
- Lopez de Prado — Advances in Financial ML
- Chan — Algorithmic Trading
- Tetlock — Superforecasting
- Poundstone — Fortune's Formula
- Grimes — Technical Analysis

Quant-research-agent should read relevant sections
before starting each research phase. The chapter
reference tables at the end of each file map
research questions to specific sections.

Training-librarian-agent maintains these files weekly.
Research-scout-agent adds new findings as they emerge.

---

## What NOT to Do in Week 1

- Do not run all agents simultaneously on day one
- Do not skip the stopping-rule questions
- Do not build trading strategies before RQ1.1 and
  RQ3.2 are validated
- Do not let quant-research-agent skip pre-registration
- Do not modify polymarket_tracker.db from swarm agents
  (read-only access only — always)

---

## Known Issues to Address Early

From pre-server audit (March 16 2026):
- trades.notified / completed / was_successful columns
  are write-only — nothing reads them (low priority)
- weighted_consensus_system.py is deprecated but still
  called by Phase 2 scheduler (code hygiene agent task)
- Worker backlog growing ~150-200/hour — monitor trend

---

## System Health Baseline (March 16 2026)
For performance-analyst-agent to compare against:

- Total traders: 53,140
- ELO range: 300-3500
- Elite traders (ELO >= 1550): 677
- Legendary traders (ELO >= 2175): ~15
- Traders with Brier scores: 897
- Best Brier score: 0.08 (superforecaster territory)
- Traders with Sharpe data: 761
- Sharpe range: -1.66 to 1.58
- Composite scores: 304 ABOVE AVERAGE, 12,715 AVERAGE
- DB size: 1581 MB
- Worker coverage: 99.7%
- Closed positions calculated: 951,694
