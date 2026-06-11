# Trading Swarm — Claude Code Context

## What This Repo Is

A **multi-agent autonomous trading swarm for Polymarket prediction markets**. The system spawns specialised AI agents in isolated git worktrees, routes them to appropriate model tiers by task complexity, validates all outputs through an independent immune system, and builds toward live trading via a staged research pipeline.

Owner: Oscar (ozziejparris@gmail.com). Server: UM890 Pro running Ubuntu, accessible via Tailscale.

---

## Current Phase

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 — Infrastructure | ✅ Complete | Server hardened, systemd services, CI pipeline, orchestrator loop |
| Phase 1 — Server Setup | ✅ Complete | All services deployed, model routing validated, benchmarks done |
| Phase 5 — Validation Gates | 🔄 CURRENT | All 4 integration gates met (2 of 4 complete as of June 2026) |
| Phase 6 — Paper Trading / Shadow Book | ⏳ Pending | All 4 gates met + v2 signal cohort ≥10 resolved with positive market-relative edge |
| Phase 7 — Live Pilot | ⏳ Pending | Phase 6 exit criteria met; V2 CLOB execution layer built; kill switch tested |
| Phase 8 — Scaled Operation | ⏳ Pending | Multi-book, RL sizing, full self-improving loop governing real capital |

> **WARNING: The `trading-swarm` systemd service has NOT been started yet.** The system is waiting for a 48-hour parallel run of the polymarket observer/monitoring services before the orchestrator goes live. Do not `systemctl start trading-swarm` without Oscar's explicit instruction.

---

## Architecture Overview

```
BRAIN (Knowledge Layer)
├── strategy-registry.md     — validated strategies + revalidation schedule
├── signals.json              — agent-to-agent message bus (file-based)
├── feedback.json             — learning memory {approved, rejected}
├── kpis.md                   — immutable baseline (Mar 16 2026) + weekly updates
├── priorities.md             — current phase gates + stopping rules (Oscar updates)
├── model-routing.md          — tier assignments, pricing, model strings
├── runbook.md                — 10-section emergency procedures
├── competitive-moat.md       — why this beats 170+ competitors
├── lessons-learned.md        — weekly updates from training-librarian-agent
├── agent-outputs/            — per-agent output directories
├── reference-library/        — research book summaries (Lopez de Prado etc.)
├── strategy-notes/           — pre-registered hypotheses awaiting approval
├── decisions/                — timestamped decision records
├── research-scout/           — approved/dismissed/pending-review research pipeline
└── integration-contract.md  — authoritative interface spec for first-repo DB queries

ORCHESTRATOR (orchestrator/orchestrator.py — 667 lines, runs every 10 min)
├── Immune system             — checks tmux sessions, timeouts (>4h), file existence
├── Signal processor          — reads signals.json, routes, sends Telegram alerts
├── Tier selector             — maps agent types → model tiers
├── Respawn logic             — auto-retry up to MAX_RETRIES=3, then escalates to Oscar
└── agent_registry.json       — live task tracking (id, branch, session, status, retries)

AGENTS (14 types, launched via scripts/spawn_agent.sh into tmux + git worktrees)
├── Tier 1 (local)     — health checks, pattern matching (zero cost)
├── Tier 2 (local)     — signal-agent, code-hygiene, training-librarian
├── Tier 2.5 (Haiku)   — integration-test, research-scout
├── Tier 3 (Sonnet)    — quant-research, backtest, market-builder, performance-analyst
└── Tier 4 (Opus)      — escalation only (3× Sonnet failures)
```

Key principle: **agents cannot self-report success — files either exist or they don't.** The orchestrator verifies outputs independently.

---

## Key Brain Files

| File | Purpose | Who Updates |
|------|---------|-------------|
| `brain/priorities.md` | Phase gates, stopping rules, what NOT to do | Oscar (manually) |
| `brain/strategy-registry.md` | All strategies with ACTIVE/PENDING/SUSPENDED/RETIRED status | feedback-loop-agent |
| `brain/model-routing.md` | Tier → model mapping, cost table, watch list of upcoming models | Oscar |
| `brain/kpis.md` | Baseline metrics (immutable) + weekly trend entries | performance-analyst-agent every Monday |
| `brain/runbook.md` | Emergency procedures for 10 failure scenarios | Oscar |
| `brain/lessons-learned.md` | Accumulated learnings from agent runs | training-librarian-agent weekly |
| `brain/competitive-moat.md` | Differentiation from 170+ competitors; ELO methodology depth | Oscar monthly |
| `brain/findings.json` | Structured research findings from agents | quant-research-agent |
| `brain/feedback.json` | Approved/rejected outcomes; agents read before starting | Orchestrator + agents |
| `brain/signals.json` | Inter-agent message bus; orchestrator processes pending signals | All agents |
| `brain/integration-contract.md` | Authoritative interface spec between first-repo DB and all agents | Oscar (manually) |

---

## Phase 5 Validation Gates — All 4 Required Before Phase 6

1. **feedback-loop-agent** has completed 4+ weekly validation runs
2. **findings.json** contains 3+ HIGH-confidence findings (each from min 20 resolved markets)
3. **Pre-resolution accuracy** ≥60% across 10+ markets (STR-002 strategy)
4. **RQ1.1** (ELO in period T predicts Brier in T+1) **and RQ3.2** (elite consensus outperforms market price) both passed

Gates 1 and 2 are met (June 2026). Gates 3 and 4 pending. Do not skip or lower these gates.

---

## Hard Rules — Never Violate

- **Limit orders only** — no market orders, ever. Market orders pay the spread; this system never does.
- **No sports markets** — low signal-to-noise, dominated by sharp bettors; explicitly excluded from all agent scope.
- **Wallet anonymity** — trading wallet must not be linkable to any personal identity. Never log or commit wallet addresses.
- **Pre-registration required** — quant-research-agent must write a hypothesis to `brain/strategy-notes/` and receive approval before running any experiment. Prevents data snooping.
- **7 Sins of Backtesting checklist** — every backtest must pass all 7 (survivorship bias, lookahead, data snooping, transaction costs, volatility clustering, liquidity, temporal dependency). Enforced by `ci/validate_backtest.py`.

---

## Model Routing (Current)

| Tier | Model | Speed | Cost | Use Cases |
|------|-------|-------|------|-----------|
| 1 | **Gemma 4 E2B** (primary) | 0.79s | $0 (local) | Session health checks, log watching, pattern matching |
| 1 | Mistral (fallback) | 2.80s | $0 (local) | Tier 1 fallback if Gemma unavailable |
| 2 | **Gemma 4 E4B** | 5.86s | $0 (local) | Signal-agent, code-hygiene, training-librarian, DB queries |
| 2.5 | **Claude Haiku 4.5** | — | $1/$5 per MTok | Integration-test, research-scout (structured tasks) |
| 3 | **Claude Sonnet 4.6** | — | $3/$15 per MTok | Quant-research, backtest, market-builder, performance-analyst |
| 4 | **Claude Opus 4.7** | — | $5/$25 per MTok | Escalation only — 3× Sonnet failures on same task |

> Llama 4 Scout was **removed** — benchmarked at 24s on the UM890 Pro (too slow for practical use).
>
> Watch list for future routing upgrades: Llama 4 Maverick, Gemini 3.1 Flash, Claude Mythos, GPT-6, DeepSeek V4.

Model strings and full routing rationale are in `brain/model-routing.md`.

---

## Validation Thresholds (Enforced by CI)

All backtests must pass these or are rejected by `ci/validate_backtest.py`:

- Sharpe ratio: **≥ 1.0**
- Deflated Sharpe Ratio (DSR): **≥ 0.95**
- Probability of Backtest Overfitting (PBO): **≤ 0.1**
- Brier score: **≤ 0.20**
- Minimum trades: **30**

---

## Quick Health Check

```bash
bash ~/trading-swarm/scripts/check_agents.sh      # agent status + pending signals
tail -20 ~/trading-swarm/logs/orchestrator.log    # recent orchestrator activity
cat ~/trading-swarm/brain/signals.json            # inter-agent bus
```

For emergencies, see `brain/runbook.md` (10 sections covering orchestrator down, DB locked, agent timeout, Telegram failure, API cost spike, etc.).

---

## Key File Locations

| Path | Purpose |
|------|---------|
| `orchestrator/orchestrator.py` | Main control loop (667 lines) |
| `scripts/spawn_agent.sh` | Agent launcher — worktrees, tmux, model selection |
| `scripts/check_agents.sh` | Quick health dashboard |
| `scripts/trading-swarm.service` | Systemd service definition (NOT started yet) |
| `orchestrator/task_templates/` | 14 agent prompt templates |
| `orchestrator/agent_registry.json` | Live task registry |
| `ci/validate_backtest.py` | Backtest threshold enforcement |
| `brain/decisions/` | Timestamped architecture decision records |
| `brain/integration-contract.md` | **Agents must follow this contract before querying first-repo** |

---

## Session Discipline

### Commit Protocol
At the end of every session that modifies any file, commit
before closing. Do not let changes accumulate as unstaged.

After any set of related changes:
  git add -A
  git commit -m "descriptive message covering all changes"
  git push origin main

Commit message format:
  "feat: ..." for new functionality
  "fix: ..." for bug fixes
  "refactor: ..." for restructuring
  "defensive: ..." for hardening/future-proofing
  "docs: ..." for documentation only

### Information Gathering vs Editing
These two types of prompts must be kept distinct:

INFORMATION GATHERING (no commits needed):
- Reading files, querying database, running diagnostics
- grep, cat, sqlite3 queries, tail logs
- Any prompt that starts with "check", "verify", "audit",
  "show me", "what is", "diagnose"
- Never commit after a pure information-gathering session

EDITING (always commit):
- Writing or modifying any .py, .md, .json, .sh file
- Any prompt that starts with "add", "fix", "update",
  "change", "create", "write", "patch", "refactor"
- Commit immediately after each logical group of changes
- Do not bundle unrelated edits into one commit

If unsure: if a file was modified, commit it.
