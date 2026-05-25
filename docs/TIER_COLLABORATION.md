# Tier Collaboration — Two-Tier Processing Pattern

## Overview

The trading swarm uses a two-tier processing model to separate **data work** (cheap local
compute) from **reasoning work** (expensive cloud tokens). Tier 2.5 (Qwen3-Coder, local)
handles all database queries, file reads, and intermediate computation. Tier 3 (Claude
Sonnet, $3/$15 per MTok) receives a compact handoff and focuses purely on analysis and
decision-making.

This pattern reduces Tier 3 token costs by 60–80% on data-heavy tasks (e.g. geo_elo
calculation), while keeping complex reasoning on the strongest available model.

---

## Tier Roles

| Tier | Model | Role |
|------|-------|------|
| 2.5 | Qwen3-Coder 30B-A3B (local) | Data layer — reads DB, computes results, writes handoff |
| 3 | Claude Sonnet 4.6 | Reasoning layer — interprets results, makes decisions, writes strategy notes |

**Key principle:** Tier 2.5 never makes strategy decisions. Tier 3 never runs raw SQL queries
if a handoff is available.

---

## Tools Available at Each Tier

### Tier 2.5 tools (via `ollama_agent_loop.py`)

| Tool | Purpose |
|------|---------|
| `read_file` | Read brain/ files, research notes, config |
| `write_file` | Write output files to brain/agent-outputs/ |
| `run_sql` | Read-only SELECT queries against polymarket_tracker.db |
| `run_sql_write` | Approved write queries (allowlisted patterns only — see below) |
| `run_shell` | Whitelisted shell commands (ls, CI runner, tmux status) |
| `append_to_json_array` | Atomically append entries to JSON arrays (signals.json, findings.json) |
| `send_telegram` | Notify Oscar via agents bot |
| `write_handoff` | Write a structured handoff file for Tier 3 consumption |

### Tier 3 tools (Claude Sonnet via Claude CLI -p)

Tier 3 runs in one-shot mode (`-p`). It reads the handoff file injected into its prompt
context and writes its output directly to files in its git worktree. No tool registry —
Claude's own filesystem capabilities are used.

---

## The `run_sql_write` Tool — Approved Write Patterns

Only the following query patterns are permitted. Any other query is rejected with a clear
error message listing the allowed patterns.

| Pattern | Purpose |
|---------|---------|
| `UPDATE traders SET geo_elo` | Write calculated geo ELO scores |
| `UPDATE traders SET geo_directionality_score` | Write geopolitical directional bias |
| `UPDATE traders SET accuracy_pool` | Update pool quality assignments |
| `UPDATE traders SET geo_resolved_trades_count` | Update geo trade counts |
| `ALTER TABLE traders ADD COLUMN` | Schema extension (add new columns) |
| `INSERT INTO trader_notes` | Agent annotations for audit trail |
| `UPDATE traders SET bot_type` | Update bot classification |
| `UPDATE traders SET research_excluded` | Mark/unmark traders from research pool |

**Safety constraints:**
- `db_path` must be exactly `/home/parison/projects/first-repo/data/polymarket_tracker.db`
- WAL mode and 30s busy timeout are always set before any write
- Writes affecting >50,000 rows are rejected — use WHERE clauses to batch
- All writes are logged with: pattern matched, rows affected, timestamp
- Connection is always closed in a `finally` block

---

## The Handoff File Format

Written by Tier 2.5 via `write_handoff` tool. Read by Tier 3 as primary context.

```json
{
  "generated_at": "2026-05-25T14:30:00Z",
  "generated_by": "tier_2.5",
  "handoff_version": "1.0",
  "task_summary": "Computed geo_elo for 312 geopolitically-active traders using 2,847 resolved markets",
  "results": {
    "traders_updated": 312,
    "geo_elo_range": {"min": 1102, "max": 2341, "median": 1487},
    "top_geo_traders": ["0xabc...", "0xdef..."],
    "geo_vs_general_elo_correlation": 0.73
  },
  "files_written": [
    "/home/parison/trading-swarm/brain/agent-outputs/quant-research/geo-elo-2026-05-25.json"
  ],
  "next_agent_instructions": "Interpret the geo_elo distribution. Compare geo vs general ELO correlation (0.73) against the RQ-GEO-ELO-001 hypothesis threshold (>0.5). Write strategy notes to brain/strategy-notes/ and a validation signal to signals.json if the threshold is met.",
  "token_estimate": 850,
  "handoff_version": "1.0"
}
```

**File location:** `brain/agent-outputs/handoffs/<task_id>.json`

---

## The Permissions System

Each agent type has a permissions file at `orchestrator/permissions/<agent_type>.json`.

```json
{
  "allow": ["read_file", "write_file", "run_sql", "run_sql_write", "write_handoff"],
  "note": "Human-readable explanation of why this access level was chosen"
}
```

The `ollama_agent_loop.py` loader checks for a per-agent file first, then falls back to
the legacy `orchestrator/agent_tool_permissions.json` (shared file, older format).

**Current agent permissions:**

| Agent | Has `run_sql_write`? | Notes |
|-------|---------------------|-------|
| `quant-research` | Yes | Primary write agent for geo_elo and related columns |
| `backtest-agent` | Yes | Writes validated backtest annotations |
| `feedback-loop-agent` | No | Read-only — must never modify the DB |
| `signal-agent` | No | Read-only — reads DB to generate signals only |
| `performance-analyst-agent` | No | Read-only — KPI calculations only |

---

## The `--handoff` Flag in `spawn_agent.sh`

```bash
./scripts/spawn_agent.sh <task_id> <agent_type> <tier> <description> --handoff <path>
```

When `--handoff <path>` is provided:
- The handoff file content is injected as the agent's primary context
- `brain/priorities.md` and `brain/integration-contract.md` are **not** injected
- A context note tells the agent not to re-read brain/ files unless instructed
- The spawn is logged as handoff-mode

When no `--handoff` is provided, the standard full-context injection applies
(priorities.md + integration-contract.md for DB-querying agents).

---

## Example Workflow — geo_elo Calculation

**Without handoff (old approach):**
1. Tier 3 Sonnet spawned with full brain/ context (~8,000 tokens)
2. Sonnet reads DB, runs queries (~3,000 tokens of SQL results)
3. Sonnet reasons and writes output
4. **Total: ~11,000 tokens at $0.033 per run**

**With two-tier handoff (new approach):**
1. Tier 2.5 Qwen3-Coder spawned (local, $0)
   - Reads brain/research-standards.md
   - Queries DB for geo-active traders
   - Computes geo_elo scores
   - Writes scores to DB via `run_sql_write`
   - Writes handoff JSON (~850 tokens)
2. Tier 3 Sonnet spawned with `--handoff <path>`
   - Reads only the 850-token handoff
   - Reasons about results and writes strategy notes
   - **Tier 3 cost: ~1,200 tokens at $0.0036**
3. **Total: ~$0.0036 (89% reduction)**

---

## When to Use Each Tier

| Use Tier 2.5 alone | Use Tier 2.5 + Tier 3 handoff | Use Tier 3 alone |
|-------------------|-------------------------------|-----------------|
| Structured data extraction | Complex hypothesis evaluation | Novel research requiring judgment |
| ELO score computation | Cross-strategy reasoning | Architecture decisions |
| DB writes from pre-approved formulas | Interpreting statistical results | First-pass hypothesis generation |
| Signal generation from known rules | Writing strategy notes after data analysis | Escalations from repeated Tier 3 failures |

**Rule of thumb:** If the task is mostly "fetch data and apply a formula", use Tier 2.5.
If the task requires "understand what this data means and decide what to do", involve Tier 3.

---

## Token Cost Estimates

| Approach | Context tokens | Output tokens | Est. cost (Sonnet) |
|----------|---------------|---------------|--------------------|
| Full brain/ context (Tier 3 only) | 8,000–15,000 | 2,000–4,000 | $0.03–$0.09 |
| Handoff only (two-tier) | 500–2,000 | 1,000–2,000 | $0.004–$0.015 |
| Local Tier 2.5 only | N/A (local) | N/A (local) | $0.00 |

For tasks running weekly (e.g. feedback-loop-agent), the two-tier approach saves
approximately $3–4/month at current cadence. At higher frequencies, savings compound.
