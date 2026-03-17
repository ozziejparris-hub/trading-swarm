# MASTER HANDOVER DOCUMENT
# Trading Swarm System — Server Pre-Setup Chat 1
# Generated: 2026-03-17
# For: Server Pre-Setup Chat 2 (next session)
# Also informs: Fresh Start Fixes 6 (Polymarket system chat)

---

## CONTEXT: WHO OSCAR IS AND WHAT HE'S BUILDING

**Oscar** (GitHub: ozziejparris-hub) is building two parallel systems:

1. **Trading Swarm** — a 24/7 autonomous multi-agent coding and
   research system that will run on a 128GB RAM Linux server
   (not yet arrived). Agents create tools and systems for trading
   across prediction markets (Polymarket primary), with planned
   expansion to equities, futures, and crypto.

2. **Polymarket Monitoring System** — an existing, running system
   on his Windows PC that tracks 53,140 traders with ELO ratings,
   behavioral scores, Telegram alerts, and P&L analysis.
   This runs independently and will be transferred to the server.

**Background:** Oscar comes from a non-technical background and
is actively learning while building. He works in national water
permitting in the UK (completely separate project). He uses
Claude Code for implementation and this chat for architecture,
research, and direction.

**Current hardware:**
- Windows PC (running Polymarket system now)
- WSL2/Ubuntu installed and configured
- 128GB RAM Linux server — NOT YET ARRIVED

---

## PART 1: WHAT WAS BUILT IN THIS CHAT

### 1.1 WSL2 / Ubuntu Setup (Complete)

Ubuntu installed on Windows via WSL2. Username: parison.
All core tools installed: tmux, git, python3, pip, gh (GitHub CLI).
GitHub authenticated. PATH fixed for pip-installed tools.

**Key commands Oscar knows:**
```bash
# Start WSL2
# Open Windows Terminal → select Ubuntu

# Navigate to project
cd ~/trading-swarm

# tmux basics
tmux new -s session-name
tmux ls
tmux attach -t session-name
# Ctrl+B then D to detach
```

---

### 1.2 Trading Swarm Repository (Complete)

**GitHub:** https://github.com/ozziejparris-hub/trading-swarm
**Local path (WSL2):** ~/trading-swarm/

**Full directory structure:**
```
trading-swarm/
├── orchestrator/
│   ├── orchestrator.py          ← main loop, immune system
│   ├── agent_registry.json      ← active task tracking
│   └── task_templates/          ← 12 agent prompt templates
│       ├── orchestrator-system.md
│       ├── signal-agent.md
│       ├── backtest-agent.md
│       ├── quant-research.md
│       ├── market-builder.md
│       ├── niche-app-agent.md
│       ├── research-scout-agent.md
│       ├── performance-analyst-agent.md
│       ├── integration-test-agent.md
│       ├── market-intelligence-agent.md
│       ├── training-librarian-agent.md
│       └── code-hygiene-agent.md
├── brain/
│   ├── signals.json             ← cross-agent signal bus
│   ├── feedback.json            ← memory of failures/successes
│   ├── priorities.md            ← day-one server direction
│   ├── kpis.md                  ← performance metrics
│   ├── definition_of_done.md    ← quality gates (upgraded)
│   ├── lessons-learned.md       ← institutional memory
│   ├── decisions/
│   ├── failed-experiments/
│   ├── strategy-notes/
│   │   ├── research-directions.md  ← 9 directions + 18 RQs
│   │   └── [other notes]
│   ├── agent-outputs/
│   │   ├── signal-agent/
│   │   ├── quant-research/
│   │   ├── backtest-agent/
│   │   ├── market-builder/
│   │   ├── performance-analyst/
│   │   ├── integration-test/
│   │   ├── training-librarian/
│   │   └── code-hygiene/
│   ├── reference-library/
│   │   ├── ml-in-finance-notes.md
│   │   ├── lopez-de-prado-notes.md
│   │   ├── ernest-chan-algo-trading-notes.md
│   │   ├── superforecasting-tetlock-notes.md
│   │   ├── fortunes-formula-poundstone-notes.md
│   │   └── grimes-technical-analysis-notes.md
│   └── research-scout/
│       ├── pending-review/
│       ├── approved/
│       └── dismissed/
├── ci/
│   ├── run_ci.sh                ← master CI pipeline
│   ├── lint.sh                  ← flake8 linting
│   ├── run_tests.sh             ← pytest runner
│   └── validate_backtest.py    ← backtest threshold validator
├── scripts/
│   ├── spawn_agent.sh           ← creates worktree + tmux session
│   ├── verify_output.sh         ← immune system verification
│   └── check_agents.sh          ← instant health check
├── tests/
│   └── test_registry.py         ← 6 passing tests
├── worktrees/                   ← git worktrees per agent task
├── logs/
│   └── agent_logs/
├── .env.example                 ← required environment variables
└── .gitignore
```

---

### 1.3 Agent System Architecture

**Complete roster of 12 agents:**

**Operational (run continuously):**
- signal-agent: monitors Polymarket elite trader activity
- quant-research-agent: builds quantitative models (Phase 1-5 roadmap)
- backtest-agent: validates all models and strategies
- market-intelligence-agent: external domain monitoring daily

**Build (spawned on demand):**
- market-builder-agent: new data connectors and tools
- niche-app-agent: one-off application ideas

**Support (scheduled):**
- research-scout-agent: AI/tech developments (daily)
- performance-analyst-agent: metrics interpretation (Monday 7am)
- training-librarian-agent: knowledge base maintenance (Saturday 9am)
- code-hygiene-agent: codebase cleanliness (Friday 8pm)

**System (infrastructure):**
- integration-test-agent: end-to-end health (Sunday 11pm)

**Orchestrator:** always on, manages everything, Telegram alerts

---

### 1.4 Model Routing Strategy (4-Tier)

```
Tier 1 — Ollama/Mistral (local, free)
  Health monitoring, log watching, immune system checks

Tier 2 — Qwen3-Coder-Next (local, free after hardware)
  Signal agent, code hygiene, training librarian
  Simple well-defined coding tasks

Tier 3 — Claude Sonnet (paid, ~$3-15/million tokens)
  Quant research, backtest validation, market builder
  Complex multi-file reasoning

Tier 4 — Claude Opus (paid, escalation only)
  Architecture decisions, tasks that failed Tier 3 3x
```

---

### 1.5 Telegram Bot Setup (Complete and Tested)

Three bots created and tested — all receiving messages:
- **Orchestrator bot**: urgent alerts requiring human action
- **Agents bot**: routine status updates
- **Metrics bot**: weekly performance summaries

Environment variables stored in `~/.env_trading` on WSL2.
Loaded automatically via `~/.bashrc`.

**Keys needed (Oscar has these):**
- TELEGRAM_ORCHESTRATOR_TOKEN
- TELEGRAM_AGENTS_TOKEN
- TELEGRAM_METRICS_TOKEN
- TELEGRAM_CHAT_ID

---

### 1.6 CI Pipeline (Complete and Passing)

All three steps passing cleanly:
- Step 1: Lint (flake8, ignoring style preferences)
- Step 2: Tests (6/6 passing — pytest)
- Step 3: Backtest validation (threshold checker)

**Run CI:**
```bash
cd ~/trading-swarm
bash ci/run_ci.sh
```

**Upgraded validation thresholds (Lopez de Prado):**
- Sharpe > 1.0 (necessary but not sufficient)
- Deflated Sharpe Ratio (DSR) > 0.95
- Probability of Backtest Overfitting (PBO) < 0.1
- Transaction costs: Polymarket ~2% per trade included
- 7 sins of backtesting checked and cleared
- Purged cross-validation required (not standard split)

---

### 1.7 Definition of Done (Complete)

Located at: `brain/definition_of_done.md`

Covers four categories:
1. Trading system / strategy PRs
2. Quant research outputs
3. New market connectors
4. Universal (any task)

Upgraded with Lopez de Prado standards including DSR,
PBO, walk-forward validation, and 7 sins checklist.

---

## PART 2: REFERENCE LIBRARY (6 BOOKS)

All notes in `brain/reference-library/`. Each file contains:
- Filtered content specific to your system
- Working Python code implementations
- Chapter references mapped to research questions
- Quick reference tables

**Book 1: ML in Finance (Dixon, Halperin, Bilokon)**
File: ml-in-finance-notes.md
Key content: Calibration/Brier score, Bayesian updating,
Kelly criterion, RL for position sizing, IRL for trader
behaviour analysis, LSTM for sequential data.
Most relevant chapters: 3 (evaluation), 7 (calibration),
9 (Bayesian), 16-17 (RL basics).

**Book 2: Advances in Financial ML (Lopez de Prado)**
File: lopez-de-prado-notes.md
Key content: Deflated Sharpe Ratio, 7 sins of backtesting,
fractional differentiation, triple barrier labelling,
meta-labelling framework, HRP portfolio construction,
Combinatorial Purged Cross-Validation, PBO.
Most important book for backtest-agent rigour.

**Book 3: Algorithmic Trading (Ernest Chan)**
File: ernest-chan-algo-trading-notes.md
Key content: Mean reversion (ADF test, Bollinger bands,
Kalman filter pairs), momentum strategies, cointegration
(Johansen test), position sizing, stop loss rules, MAE/MFE.
Covers equities AND futures for planned expansion.

**Book 4: Superforecasting (Tetlock)**
File: superforecasting-tetlock-notes.md
Key content: Brier score decomposition, superforecaster
profile mapped to your behavioral metrics, belief updating
measurement, calibration improvement tracking, extremising
adjustment for consensus probability, diversity bonus
(excludes copy traders), reference class forecasting.
Validates entire premise: your best traders are in
superforecaster Brier score territory (0.08-0.12).

**Book 5: Fortune's Formula (Poundstone)**
File: fortunes-formula-poundstone-notes.md
Key content: Kelly criterion deep foundation, Thorp's
real-world application (19 years positive returns),
uncertainty-adjusted Kelly, dynamic Kelly table by
signal quality, ruin prevention rules, overbetting
asymmetry (2x Kelly = zero growth).
Current recommendation: 0.25x-0.50x Kelly for Polymarket.
Dynamic Kelly table included keyed by signal confidence
and legendary trader count.

**Book 6: Technical Analysis (Grimes)**
File: grimes-technical-analysis-notes.md
Key content: What actually works (rigorous testing),
market structure classification (trending/ranging/
transitioning/converging), volume confirmation scoring,
prediction market key price levels (0.25/0.50/0.75/0.90),
hard boundary effect, signal-structure filter,
Grimes entry checklist (8 items).
Most important: classify market structure BEFORE acting
on any elite convergence signal.

---

## PART 3: RESEARCH QUESTIONS (18 FORMAL HYPOTHESES)

Located at: `brain/strategy-notes/research-directions.md`

**6 categories, 18 falsifiable hypotheses.**
Each has: specific test, data source, success criterion,
null hypothesis, and why it matters.

**STOPPING RULES — halt everything if these fail:**
- RQ1.1 fails (ELO has no predictive validity) → redesign ELO
- RQ3.2 fails (markets efficient vs elite consensus) → pivot
- RQ2.1 shows <55% accuracy → signal architecture wrong

**Priority order for quant-research-agent:**

Week 1-2 (foundational):
- RQ1.1: ELO persistence (r > 0.25 between periods)
- RQ2.2: Entry timing advantage (legendary vs standard)
- RQ3.2: Crowd vs elite divergence (core premise test)

Week 3-4:
- RQ1.2: Skill tier stability (>70% legendary retention 90 days)
- RQ2.1: Elite convergence edge (>65% accuracy on 3+ legendary)
- RQ4.1: Kelly alignment vs Sharpe (r > 0.20)

Week 5-6:
- RQ3.1: Category calibration (Brier varies by market type)
- RQ2.3: Signal decay rate (accuracy increases near resolution)
- RQ5.2: Copy trader contamination (excluding copies improves signal)

Week 7-8:
- RQ4.2: Overbetting analysis (overbetting kills profits)
- RQ6.2: Near-resolution mispricing (systematic underpricing)
- RQ1.3: Composite score vs ELO alone (>15% improvement)

Week 9-12: remaining + synthesis + build trading strategies

---

## PART 4: POLYMARKET SYSTEM STATUS (March 16 2026)

This is the EXISTING system running on Oscar's Windows PC.
Lives in: C:\Users\Oscar\Projects\first-repo
GitHub: ozziejparris-hub/first-repo (separate repo)
Managed in: Fresh Start Fixes 6 chat (separate chat)

**Current system health:**
- Uptime: 60+ hours clean
- Total traders: 53,140
- ELO range: 300-3,500
- Elite traders (ELO >= 1550): 677
- Legendary traders (ELO >= 2175): ~15
- Top trader: 0xb442 ELO 3500, ROI +45.5%
- DB size: 1,581 MB
- Worker coverage: 99.7%
- Closed positions: 951,694

**Analysis pipeline (as of March 16 2026):**
All four dormant features activated in scheduler:
- Phase 2b: risk_adjusted_returns.py (761 traders, Sharpe -1.66 to 1.58)
- Phase 2c: calibration_analysis.py (897 traders, Brier 0.08-0.89)
- Phase 3b: composite_skill_score.py (13,021 scored, 304 ABOVE AVERAGE)
- Correlation matrix: 7-day TTL cache, 2,396-trader cap

**Behavioral scores (fixed March 16):**
- timing_score: 3,231 traders
- patience_score: 2,194 traders
- kelly_alignment_score: 1,153 traders
- Fix: encoding='utf-8' added to CSV writer

**Database integrity (fixed March 16):**
- 12 orphaned traders inserted (was causing 735/647 warnings)
- Behavioral coverage warning changed to INFO severity
- All database integrity warnings now cleared

**CRITICAL RULE for swarm agents:**
polymarket_tracker.db is READ-ONLY for all swarm agents.
Never write to this database from the trading swarm.
The Polymarket monitoring system writes to it independently.

---

## PART 5: KEY ARCHITECTURAL DECISIONS

**Decision 1: One swarm, specialist agents (not separate swarms)**
Future market expansions (equities, futures, crypto) get
specialist agents within the same swarm — not separate
swarm instances. Shared brain, shared orchestrator,
shared support agents. Cross-market intelligence only
exists if agents share a brain.

**Decision 2: Hybrid model routing (not 99% local)**
Realistic split: ~40-50% Tier 1 (free), ~30-40% Tier 2 (free),
~15-20% Tier 3 (Sonnet, paid), ~5% Tier 4 (Opus, paid).
Research questions need Sonnet minimum — statistical
reasoning on subtle points fails with weaker models.

**Decision 3: No OpenClaw**
Deliberate decision. OpenClaw is general-purpose business
automation. Your system is Polymarket/trading-specific.
The specificity is the edge. Don't dilute it.

**Decision 4: VS Code Remote first, Grafana dashboard later**
Use VS Code Remote SSH for server setup and development.
Build Grafana dashboard once system is stable and you know
what metrics you need. Don't build dashboard before
knowing what to put in it.

**Decision 5: Pre-registration protocol mandatory**
Before any quant-research-agent implements a model,
it must write a hypothesis file and wait for approval.
Prevents compute waste on weak hypotheses.
Directly drawn from Karpathy's autoresearch pattern.

**Decision 6: Never delete automatically**
Code-hygiene-agent and integration-test-agent flag issues
but never act autonomously on irreversible actions.
Delete and modify require human approval via signal review.

**Decision 7: Stopping rules before trading strategies**
RQ1.1 and RQ3.2 must pass before any trading strategy
is built. Building strategies on unvalidated foundations
wastes months. Tetlock, Lopez de Prado, and Chan all
agree on this.

---

## PART 6: WEEKLY RHYTHM (WHEN SERVER IS LIVE)

```
Daily:
  signal-agent           ← Polymarket elite trader monitoring
  market-intelligence    ← external domain scan
  research-scout         ← AI/tech/quant developments

Friday 8pm:
  code-hygiene-agent     ← codebase cleaning

Saturday 9am:
  training-librarian     ← knowledge base maintenance

Sunday 11pm:
  integration-test-agent ← end-to-end system health

Monday 7am:
  performance-analyst    ← metrics interpretation

Monday 8am:
  orchestrator           ← weekly metrics Telegram report

Continuous:
  quant-research-agent   ← tunnelling on research questions
  backtest-agent         ← validating quant outputs
  orchestrator loop      ← 10-minute cycles, immune system
```

---

## PART 7: WHEN SERVER ARRIVES — EXACT STEPS

```bash
# Step 1: Clone the repo
git clone https://github.com/ozziejparris-hub/trading-swarm.git
cd trading-swarm

# Step 2: Install tools (same as WSL2)
sudo apt update
sudo apt install tmux git python3 python3-pip gh -y
pip install flake8 pytest --break-system-packages
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Step 3: Install Ollama and models
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral
ollama pull qwen2.5-coder

# Step 4: Install Claude Code
npm install -g @anthropic-ai/claude-code
claude auth

# Step 5: Set up environment variables
nano ~/.env_trading
# Paste Telegram tokens and chat ID
echo "source ~/.env_trading" >> ~/.bashrc
source ~/.env_trading

# Step 6: Transfer Polymarket database
# (from Windows machine to server)
# scp C:\Users\Oscar\Projects\first-repo\data\polymarket_tracker.db
#     oscar@server:/data/polymarket_tracker.db

# Step 7: Start orchestrator
tmux new -s orchestrator
cd ~/trading-swarm
python3 orchestrator/orchestrator.py

# Step 8: Verify it's working
bash scripts/check_agents.sh
# Check Telegram — should receive startup message
```

---

## PART 8: WHAT'S LEFT TO DO (BEFORE SERVER)

**Remaining from pre-server checklist:**
- [ ] Git worktree practice (30 mins — still not done)
- [ ] VS Code Remote SSH connection practice

**Optional (can wait for server):**
- regret_analysis.py integration as Phase 2d
- market_confidence_meter.py as Phase 3c
- More books from Scribd (Prediction Markets — Hahn/Tetlock,
  Active Portfolio Management — Grinold/Kahn,
  Kelly Capital Growth — MacLean/Thorp/Ziemba)

**What research-scout-agent should monitor:**
- github.com/karpathy/autoresearch (commits/issues)
- arXiv cs.AI and q-fin daily
- Anthropic blog and changelog
- Polymarket blog and governance forum
- @karpathy, @lopezdeprado on Twitter

---

## PART 9: IMPORTANT CONTEXT FOR NEXT CHAT

**What this chat covered:**
Everything from WSL2 installation through to a complete
pre-server architecture including 12 agent templates,
6 reference library books, 18 formal research questions,
CI pipeline, Telegram bots, orchestrator core loop,
spawn/verify/check scripts, priorities, and lessons learned.

**What next chat (Server Pre-Setup 2) should cover:**
- Git worktree practice
- VS Code Remote SSH setup
- Any remaining books or research inputs
- Server arrival preparation
- Possibly: running foundational research questions
  (RQ1.1, RQ3.2) on current Windows machine using
  Claude Code before server arrives

**What Fresh Start Fixes 6 (Polymarket chat) should know:**
- March 16 2026: 4 dormant features activated in scheduler
- Behavioral scores encoding bug fixed
- Correlation matrix performance fixed (96.6% reduction)
- Composite skill scores now running (Phase 3b)
- Risk-adjusted returns integrated (Phase 2b)
- Calibration/Brier scores integrated (Phase 2c)
- 12 orphaned traders repaired
- Database integrity warnings cleared
- Full handover summary pasted into that chat separately

**Key GitHub repos:**
- Trading swarm: github.com/ozziejparris-hub/trading-swarm
- Polymarket system: github.com/ozziejparris-hub/first-repo
- Clothes bot: github.com/ozziejparris-hub/clothes-bot

---

## PART 10: QUICK REFERENCE — KEY NUMBERS

```
System baseline (March 16 2026):
  Total Polymarket traders:    53,140
  ELO range:                   300 - 3,500
  Elite traders (ELO >= 1550): 677
  Legendary (ELO >= 2175):     ~15
  Best Brier score:            0.0798 (superforecaster territory)
  Sharpe range:                -1.66 to 1.58
  DB size:                     1,581 MB
  Closed positions:            951,694
  Worker coverage:             99.7%

Kelly criterion defaults:
  Recommended fraction:        0.25x - 0.50x full Kelly
  Single position cap:         25% of capital
  Correlated position cap:     50% of capital
  At 2x Kelly:                 growth rate = 0 (don't overbetf)

Brier score thresholds:
  Excellent:                   < 0.10 (superforecaster)
  Good:                        0.10 - 0.20
  Acceptable:                  0.20 - 0.25
  Random baseline:             0.25
  Target for system:           < 0.20 (minimum)

ELO thresholds:
  Standard:                    < 1800
  Elite:                       1800 - 2175
  Legendary:                   > 2175
  Maximum observed:            3500

Validation thresholds:
  Sharpe minimum:              1.0 (necessary, not sufficient)
  DSR minimum:                 0.95
  PBO maximum:                 0.10
  Transaction cost assumed:    2% (Polymarket fee)
  Minimum trades:              30

WSL2 username: parison
Server username: (not yet assigned)
```

---

*End of handover document.*
*Next session: Server Pre-Setup Chat 2*
*Save this file locally — it contains full system context.*
