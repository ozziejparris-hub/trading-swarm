# Tier-3 Claude-Credit Shutdown — 2026-08-31

**Type:** Cost-control decision (crontab change), reversible.
**Decided by:** Oscar, after a two-phase identify-then-stop investigation this session
(Phase 1 report delivered inline; Phase 2 executed here).
**Predecessor:** `brain/decisions/2026-07-15-tier3-pause-token-bleed.md` — this action
follows the same mechanism and comment style, and pauses the five agents that ledger
had deliberately *left running*.
**Standing instruction:** claims tagged `[V]` verified this session, `[I]` inferred.

---

## What changed

Commented out (not deleted) **five** crontab lines — every remaining Claude-backed
Tier-3 agent in the swarm. Agent code, cron wrappers, task templates, `spawn_agent.sh`,
and all output directories are untouched. This is purely a scheduling pause.

| # | Agent | Original cron line | Cadence (UTC) |
|---|---|---|---|
| A | `code-hygiene-agent` | `0 20 * * 5 /home/parison/trading-swarm/scripts/cron_wrappers/run_code_hygiene.sh` | Fri 20:00 |
| B | `training-librarian-agent` | `0 9 * * 6  /home/parison/trading-swarm/scripts/cron_wrappers/run_training_librarian.sh` | Sat 09:00 |
| C | `performance-analyst-agent` | `0 6 * * 1  /home/parison/trading-swarm/scripts/cron_wrappers/run_performance_analyst.sh` | Mon 06:00 |
| D | `signal-agent` | `0 8 * * 1  /home/parison/trading-swarm/scripts/cron_wrappers/run_signal_agent.sh` | Mon 08:00 |
| E | `trader-intelligence-agent` | `15 7 * * 1 /home/parison/trading-swarm/scripts/cron_wrappers/run_trader_intelligence.sh` | Mon 07:15 |

Each line is now preceded by a 4-line comment block (matching the 2026-07-15 style —
`# PAUSED <date> (<reason tag>) — <agent> ...` + a `# Ledger:` pointer to this file)
and the cron line itself is preserved verbatim with a leading `#`.

All five run via `cron_wrapper → scripts/spawn_agent.sh <id> <agent> 3 "<prompt>"`, and
in `spawn_agent.sh` tier `3` = `claude --model claude-sonnet-4-6
--dangerously-skip-permissions -p` with `ANTHROPIC_API_KEY` explicitly unset, so each
run consumed **one Claude Sonnet session against Oscar's personal OAuth Pro/Max
subscription quota**, not a metered API bill. `[V]` (`spawn_agent.sh:159`, `:283`)

**Estimated saving:** 5 full `claude -p` agentic sessions/week eliminated (3 clustered
Mon 06:00–08:15, 1 Fri 20:00, 1 Sat 09:00). Transcripts this week were 40–121 KB each.
`[V]` Combined with the still-paused research-scout (~14/wk) + integration-test (~1/wk),
the swarm's autonomous Claude footprint is now **zero scheduled sessions**. `[V]`

---

## Left running, unchanged (verified NOT Claude-backed)

| Job | Trigger | Backend — why it's safe to keep |
|---|---|---|
| `polymarket-monitoring.service` | systemd | core ingestion; no Claude. `[V]` |
| `polymarket-observer.service` | systemd | health AI = **local Mistral/Ollama**; also triggers `pre_resolution_intelligence.py` (pure SQLite). `[V]` |
| `trading-swarm.service` (`orchestrator.py`) | systemd, 600 s loop | **No LLM on any path.** Immune system = pure-Python tmux liveness checks; signal handler = Telegram only; explicit "do NOT auto-spawn". The auto-respawn branch (`orchestrator.py:552`) only sets registry status + sends Telegram — it never invokes `spawn_agent.sh` or `claude`. 1.3 s CPU over 4 days. `[V]` |
| `run_daily_maintenance.sh` | cron `0 6 * * *` | 28 pure-Python steps; one uses **local Ollama** (`backfill_market_categories.py`, Qwen3 on `localhost:11434`) — free. `[V]` |
| `polymarket-sunday-elo.timer` | systemd | ELO recalculation, local compute. `[V]` |
| `run_database_backup.sh` / `backup_offsite.sh` | cron `0 3 * * *` / `0 2 * * *` | no LLM. `[V]` |
| `run_feedback_loop.sh` → `run_feedback_loop_agent.py` | cron `0 7 * * 1` | **pure Python** — SQLite + urllib(Telegram) + JSON. Zero `claude`/`anthropic`/`ollama` refs. "agent" is a misnomer. `[V]` |
| `run_changelog_monitor.sh` → `polymarket_changelog_monitor.py` | cron `30 7 * * 1` | **no LLM** — urllib fetch + Telegram post. `[V]` |
| `legendary_positions_scan.py` | cron `30 7 * * 1` | **no LLM** — sqlite3 + urllib + `column_definitions`. `[V]` |
| `weekly_resolution_sweep.sh` | cron `30 3 * * 0` | **no LLM** — `fast_resolution_check`. `[V]` |

Also unchanged: **research-scout** (cron lines `#0 8 * * *` and `#0 20 * * *`) and
**integration-test-agent** (`#0 23 * * 0`) — already paused 2026-07-15, left exactly as
they were. `[V]`

---

## Verification (performed this session, 2026-08-31 ~12:31 UTC)

### a. Crontab diff — exactly five lines newly commented, nothing else changed `[V]`

- Pre-edit copy saved to `logs/crontab.backup.2026-08-31T123016Z.txt`
  (sha256 `28211acc13fe11354a4fff0efc43e3b60b62de8ba62c38d4b9893232c189a80d`).
- Installed copy: `logs/crontab.new.2026-08-31T123016Z.txt`
  (sha256 `25215a228d7859cf77372b63f3b6b17bd092701698dce5ca63cca730802af720`).
  (`logs/` is gitignored, so these recovery artifacts live on disk only.)
- `diff` of live crontab vs the pre-edit backup: **5 removals** (the five active agent
  lines) and **only** additions that are comment lines + those same five lines
  re-prefixed with `#`. Every other line — the 2026-07-15 paused blocks, all backup /
  maintenance / feedback-loop / changelog / positions-scan / offsite / resolution-sweep
  lines, the `@reboot` line — is byte-identical.
- Line count 28 → 48 (+20 = 5 agents × 4 comment lines).

### b. No agent was mid-run, before or after `[V]`

- Before edit: no tmux server; the only `claude` process was this interactive session
  (PID 1612164, parent `-bash`, no `-p`/`--print`/`--dangerously-skip-permissions`).
- After edit: no tmux server; no `claude --model` / `spawn_agent.sh` / `ollama_agent_loop.py`
  processes; no `cron_wrappers/run_*.sh` processes (the one `flock` hit was the sandbox's
  own backup-lock holder in `/tmp/tmp.*`, not a real run).
- `agent_registry.json` `active_tasks`: only `signal-202606042140` with `status:"failed"`
  — the pre-existing 2026-06-04 orphan noted in the 2026-07-15 ledger. No `running` or
  `respawning` task.
- Timing: today is Monday; C/E/D already ran this morning (06:00/07:15/08:00, all exit 0
  with committed output — `2635d35`, `89d8e99`, `e5da6bc`) well before the 12:30 edit.
  Next fire for any of the five would have been Fri 20:00 (code-hygiene).

### c. Untouched jobs still scheduled and intact `[V]`

- All 7 non-Claude cron jobs present and uncommented (backup, daily_maintenance,
  feedback_loop, changelog_monitor, legendary_positions_scan, backup_offsite,
  weekly_resolution_sweep).
- `systemctl is-active`: `polymarket-monitoring`, `polymarket-observer`, `trading-swarm`
  → all `active`. `is-enabled` → all `enabled`; `polymarket-sunday-elo.timer` → `enabled`.
- research-scout + integration-test lines still commented, unchanged.

---

## How to re-enable (least-destructive, per-agent)

Do **not** bulk-uncomment. Reactivate one agent at a time, each confirmed to still
produce value, consistent with Oscar's standing swarm-consolidation instruction.

1. `crontab -e` (or `crontab -l > /tmp/ct && $EDITOR /tmp/ct && crontab /tmp/ct`).
2. For the chosen agent, delete the leading `#` from **its cron line only** (the line
   starting `#<minute> <hour> ...run_<agent>.sh`). Leave the `# PAUSED 2026-08-31 ...`
   comment lines in place as history, or delete them — either is fine.
3. Save. Confirm with `crontab -l | grep run_<agent>`.

The commented lines preserve the exact original schedules — `0 20 * * 5`, `0 9 * * 6`,
`0 6 * * 1`, `0 8 * * 1`, `15 7 * * 1` — so no schedule needs reconstructing.

**Full restore of the pre-edit crontab** (all five at once, if ever needed):

```bash
crontab /home/parison/trading-swarm/logs/crontab.backup.2026-08-31T123016Z.txt
crontab -l   # verify
```

If that backup file is gone, the five lines to restore verbatim are the five
"Original cron line" cells in the table at the top of this document.

**Before reactivating any of these**, note the `spawn_agent.sh` session-limit bug in
the drift findings below — a reactivated agent that hits the Claude session limit will
be marked `completed` in the registry and silently produce nothing.

---

## Drift findings from Phase 1 — RECORDED, NOT FIXED

These were surfaced during the identify phase and are logged here so they are not lost.
None was acted on in this change.

1. **`trader-intelligence-agent` runs on Claude with no routing-table entry.**
   It appears in neither `brain/model-routing.md` nor
   `orchestrator/orchestrator.py:AGENT_TIER_DEFAULTS`. It runs on Claude Sonnet purely
   because `cron_wrappers/run_trader_intelligence.sh` passes the literal `3` as the tier
   argument to `spawn_agent.sh`, which uses that positional value directly. If routing
   were ever consulted for it, the lookup would fall through to the Tier-3 default
   anyway — but the assignment is currently undocumented and unauditable from the
   routing docs alone. `[V]`

2. **`scripts/run_research_scout.py` calls `claude --print` directly**, bypassing
   `spawn_agent.sh`'s tier routing entirely (`run_research_scout.py:56–73`,
   `call_claude_cli()` → `/home/parison/.local/bin/claude --print --allowed-tools
   WebSearch`, with `ANTHROPIC_API_KEY` stripped for OAuth). `brain/model-routing.md`
   lists `research-scout` as **Tier 2.5 / Qwen3-Coder 30B-A3B (local, free)**. So if
   research-scout is reactivated via its current cron wrapper, it will consume Claude
   subscription quota, *not* run locally as the routing doc implies. (Currently moot —
   still paused since 2026-07-15.) `[V]`

3. **`spawn_agent.sh` does not detect Claude session-limit failures.** A run that hits
   `"You've hit your session limit"` still exits the tmux pipeline cleanly, the registry
   cleanup marks the task `status: "completed"`, and zero output is produced with no
   alert. The 2026-07-15 ledger already recorded this affecting `signal-agent` ~2 of its
   last 7 weekly runs and cited `hygiene-20260710`, `signal-20260629`, `signal-20260713`
   logs. Still unfixed. `[V]`

---

## Confirmed: nothing downstream breaks

Same reasoning as the 2026-07-15 ledger, re-checked for the additional three agents:

- No script or agent programmatically consumes the weekly outputs of code-hygiene,
  training-librarian, performance-analyst, signal-agent, or trader-intelligence — they
  write human-facing reports / profile files under `brain/agent-outputs/` and
  `brain/trader-profiles/`. `brain/` consumers read whatever is present and degrade
  gracefully when a week's file is absent (established for training-librarian ←
  research-scout in the prior ledger; the same "optional advisory input" pattern applies
  here). `[I]`
- `orchestrator.py`'s immune system only tracks tasks currently in `agent_registry.json`;
  it has no "agent X hasn't run in N days" alerting, so it will not emit false
  dark-agent warnings for the paused five. `[V]`
- `signal-agent` is the one closest to the live thesis (STR-003 rescan, legendary-trader
  threshold checks). Its weekly output feeds Oscar's review, not an automated pipeline —
  pausing it defers that review, it does not corrupt any state. `[V]/[I]`

---

*No code fixed, no service touched. Crontab-only, reversible.*
