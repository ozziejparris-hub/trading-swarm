# Trading Swarm — Structural Survey (Stage 1 of comprehensive audit)

**Date:** 2026-07-10
**Method:** Read-only survey. No files modified except this document. Purpose: break the repo into scrutinizable areas for a deep-dive Fable audit (Stage 2). This is a map, not a verdict — flags below are things to check, not confirmed defects unless stated as verified.

---

## 1. Top-Level Structure

```
trading-swarm/
├── brain/                  knowledge layer — 350+ md files, 156 json files, decisions/, agent-outputs/
├── orchestrator/           orchestrator.py (855 lines), permissions/, task_templates/, ollama_agent_loop.py
├── scripts/                agent entrypoints, cron_wrappers/, spawn_agent.sh, DB-touching scripts
├── ci/                     lint.sh, run_ci.sh, run_tests.sh, validate_backtest.py
├── tests/                  3 pytest files (registry, market_filter, write-allowlist)
├── logs/                   orchestrator.log, per-agent logs, agent_logs/ (78 gz archives)
├── docs/                   TIER_COLLABORATION.md (194 lines) — only doc outside brain/
├── worktrees/              empty — actual worktrees live in /tmp/trading-swarm-worktrees (per spawn_agent.sh)
├── .claude/                settings.local.json (permission allowlist for this Claude Code session)
├── .github/                (not inspected in depth — CI workflow presumably)
├── CLAUDE.md               project instructions — contains a stale claim, see §2
├── .env.example            Telegram token placeholders only
└── requirements.txt        scipy, numpy, pytest, flake8 (4 lines — minimal)
```

**Totals:** 701 files (excl. .git). By extension: 352 `.md`, 164 `.json`, 78 `.gz` (archived logs), 48 `.log`, 21 `.sh`, 18 `.py`, 3 `.service`.

**LOC:** Python ~7,364 lines (18 files — small, logic is thin). Shell ~1,698 lines. Markdown ~52,406 lines (this dwarfs code — the "brain" is the actual bulk of the repo, dominated by decisions/ session summaries and the integration-contract).

**Language mix:** This is a documentation-and-orchestration repo, not an application repo. The actual trading/research logic (SQL, ELO calculation, signal generation) lives in the sibling repo `first-repo`, not here. Trading-swarm's own Python is orchestration glue + a handful of DB-touching analysis scripts.

### INITIAL FLAGS
- `worktrees/` directory is empty and stale — the real worktree path (`/tmp/trading-swarm-worktrees`) is documented only in a comment inside `spawn_agent.sh`. Minor: an empty tracked-looking directory with no README explaining it's vestigial.
- The doc-to-code ratio (52K MD lines vs 7.3K Python lines) means most of the "system" is prose decisions, not executable logic — the actual behavior enforcement is thin (see §7 integration contract enforcement gap).

---

## 2. The Orchestrator

**Files:** `orchestrator/orchestrator.py` (855 lines), `orchestrator/agent_registry.json`, `orchestrator/agent_tool_permissions.json`, `orchestrator/permissions/*.json` (5 files), `orchestrator/task_templates/*.md` (15 files), `orchestrator/ollama_agent_loop.py` (1,230 lines), `orchestrator/context_compressor.py`, `scripts/spawn_agent.sh` (agent launcher).

### What it actually does
`orchestrator.py`'s `main()` loop runs **every 600 seconds (10 min) forever**. Each cycle (`run_cycle()`) does exactly three things:
1. **Immune system** (`run_immune_system()`) — checks tmux sessions for tasks marked "running" in `agent_registry.json`, detects dead sessions, auto-respawns up to `MAX_RETRIES=3`, then escalates to Telegram. Checks 4-hour runtime timeout.
2. **Signal processor** (`process_signals()`) — reads `brain/signals.json`, dispatches ~14 known signal types to Telegram messages (3 bots: orchestrator/agents/metrics), unhandled types get a generic alert (fail-loud, not fail-silent — good).
3. **Weekly metrics** — currently a no-op; the function body is fully commented out with a note "DISABLED — performance-analyst-agent not yet activated."

**Critically: the orchestrator does NOT itself spawn agents on a schedule.** Agent spawning is driven entirely by **cron** calling `scripts/cron_wrappers/*.sh`, which either run a Python script directly or call `scripts/spawn_agent.sh` (which creates a git worktree, tmux session, and picks the model command by tier). The orchestrator's only role is health-checking whatever spawn_agent.sh already registered, plus signal routing. This is a two-tier scheduling system (cron = when, orchestrator = health/comms) that isn't obviously documented as such anywhere in CLAUDE.md.

**Permissions system:** `orchestrator/agent_tool_permissions.json` and `orchestrator/permissions/*.json` are tool allowlists consumed by `ollama_agent_loop.py` (Tier 2/2.5 local-model agentic loop) — they gate `run_sql` vs `run_sql_write` vs `run_shell` per agent type. Only 5 of ~14 agents have a `permissions/*.json` file (backtest-agent, feedback-loop-agent, performance-analyst-agent, quant-research, signal-agent) — the rest presumably run at Tier 3 (Claude CLI, no tool-loop wrapper) where permissioning is implicit in the Claude CLI's own tool access, not this allowlist.

**Agent configuration:** `orchestrator/task_templates/<agent-type>.md` — one markdown prompt template per agent, injected verbatim by `spawn_agent.sh` with `{TASK_DESCRIPTION}` substituted plus `brain/priorities.md`, model-routing note, and (for DB-querying agents only) `brain/integration-contract.md`.

### Reconciling the "not started yet" claim
**CLAUDE.md states: "The `trading-swarm` systemd service has NOT been started yet."** This is **false as of this survey** — `systemctl status trading-swarm` shows `enabled; active (running) since Tue 2026-07-07`, PID 29153, 3 days uptime, cycling normally (confirmed via live orchestrator.log tail). CLAUDE.md was not updated when the service was started on 2026-07-07.

### What runs when (verified via `crontab -l`)
```
@reboot       cpupower frequency-set
03:00 daily   database backup (trading-swarm → backs up first-repo's DB)
06:00 daily   daily_maintenance.py (runs IN first-repo, invoked from trading-swarm's cron_wrappers)
07:00 Mon     feedback-loop-agent
07:15 Mon     trader-intelligence-agent
07:30 Mon     legendary_positions_scan.py (direct first-repo script call, no wrapper)
06:00 Mon     performance-analyst-agent
08:00 Mon     signal-agent
07:30 Mon     changelog_monitor
08:00 daily   research-scout (×2 — see §3 flag)
20:00 daily   research-scout (again — see §3 flag)
20:00 Fri     code-hygiene-agent
09:00 Sat     training-librarian-agent
23:00 Sun     integration-test-agent
02:00 daily   backup_offsite.sh (first-repo script, logs to trading-swarm/logs/)
03:30 Sun     weekly_resolution_sweep.sh (first-repo script)
```
Plus separate systemd timer `polymarket-sunday-elo.timer` (03:00 Sun, first-repo's comprehensive ELO recalc, outside this crontab).

### INITIAL FLAGS
- **CLAUDE.md is stale/wrong on service status** — high-visibility discrepancy between documented and actual system state. Should be corrected or Oscar should confirm intent.
- **research-scout is scheduled twice daily** (08:00 and 20:00) via the same wrapper `run_research_scout.sh` — combined with the known dedup bug (see §3, §6), this doubles the rate of duplicate story filing. Worth checking whether 2x/day is intentional or a leftover from an earlier single-run cadence plus an added evening run.
- `agent_registry.json` currently contains **one stale entry**: a `signal-agent` task from **2026-06-04** (`status: failed`, 1 retry) that was apparently never cleaned up by the immune system or manually — over a month old. Either the immune system's respawn-then-fail path doesn't always clear entries, or this is an orphan from before a code change. Worth checking `update_task`/registry cleanup logic in Fable's deep dive.
- The orchestrator's own scheduling role is nearly vestigial (no dynamic spawning) — worth confirming this is intentional given how much of CLAUDE.md's "Architecture Overview" implies the orchestrator drives agent execution ("Respawn logic" is real; "spawns new work" in orchestrator.py's own docstring is not really true — it only respawns dead sessions of already-registered tasks, it doesn't spawn new task types).
- `send_weekly_metrics()` is dead code (fully commented out) — low risk, but it's a maintenance trap: someone could "fix" the disabled block without noticing `run_cycle()` still calls the no-op wrapper.
- Only 5/14 agent types have explicit tool-permission files; unclear if the rest are unrestricted at their tier or governed some other way — worth Fable confirming the actual blast radius for agents without an entry in `permissions/`.

---

## 3. The Agents

Per `orchestrator/task_templates/` there are **15 template files** (CLAUDE.md claims 14 agent "types" — close, off by one, possibly niche-app-agent or research.md is uncounted/deprecated).

| Agent | Entry point | Cadence | Reads | Writes | Status |
|---|---|---|---|---|---|
| **orchestrator** (immune+signals) | `orchestrator/orchestrator.py` | continuous, 10-min loop (systemd) | `agent_registry.json`, `signals.json`, `feedback.json`, `contract_violation_state.json` | same + Telegram | **ACTIVE** |
| **feedback-loop-agent** | `scripts/run_feedback_loop_agent.py` via `run_feedback_loop.sh` | weekly, Mon 07:00 | first-repo DB (read-only, WAL URI mode) | `brain/agent-outputs/feedback-loop/`, `findings.json` | **ACTIVE** (4+ runs per memory) |
| **trader-intelligence-agent** | `spawn_agent.sh` (Tier 3) via `run_trader_intelligence.sh` | weekly, Mon 07:15 | first-repo DB, `brain/trader-profiles/` | `brain/agent-outputs/trader-intelligence/`, updates `brain/trader-profiles/*.json` in place | **ACTIVE** |
| **signal-agent** | `spawn_agent.sh` (Tier 3) via `run_signal_agent.sh` | weekly, Mon 08:00 | first-repo DB, `signals.json`, `feedback.json` | `brain/signals.json` (via `register_signal.py` per integration-contract v2.9 — direct writes now prohibited) | **ACTIVE** |
| **performance-analyst-agent** | `spawn_agent.sh` (Tier 3) via `run_performance_analyst.sh` | weekly, Mon 06:00 | first-repo DB (read-only) | `brain/kpis.md`, `brain/agent-outputs/performance-analyst/` | **ACTIVE** |
| **research-scout-agent** | `scripts/run_research_scout.py` via `run_research_scout.sh` | **daily, twice (08:00 + 20:00)** | RSS/web sources (arxiv, HF, Anthropic, Polymarket changelog, etc. per `brain/research-scout/*_check.md`) | `brain/research-scout/pending-review/` | **ACTIVE but buggy** — known dedup failure, same 5-6 stories refiled repeatedly (confirmed still happening 06-27/06-29/06-30 per untracked files in git status) |
| **code-hygiene-agent** | `spawn_agent.sh` (Tier 3) via `run_code_hygiene.sh` | weekly, Fri 20:00 | both repos | `brain/agent-outputs/code-hygiene/`, `logs/code_hygiene.log` | **ACTIVE** — promoted to Tier 3 after local model fabricated vulns (2026-05-14) |
| **training-librarian-agent** | `spawn_agent.sh` (Tier 3) via `run_training_librarian.sh` | weekly, Sat 09:00 | `brain/reference-library/`, templates, `findings.json` | `brain/lessons-learned.md`, `brain/agent-outputs/training-librarian/` | **ACTIVE** — promoted to Tier 3 (same 2026-05-14 fabrication issue) |
| **integration-test-agent** | `spawn_agent.sh` (Tier 3) via `run_integration_test.sh` | weekly, Sun 23:00 | signal bus, registry, CI, brain completeness (6 suites) | `brain/agent-outputs/integration-test/` | **ACTIVE** — promoted to Tier 3 (fabricated CRITICAL failures at Tier 2.5, reverted 2026-05-14); recent runs show high failure rate (695f79a commit: "7 failures (86%)") — worth Fable checking whether these are real regressions or a broken test suite |
| **quant-research** | spawned ad hoc (no cron wrapper — invoked manually/on demand per pre-registered hypothesis) | on-demand | first-repo DB | `brain/agent-outputs/quant-research/<RQ>/`, pre-registration in `strategy-notes/` | **ACTIVE**, event-driven not scheduled |
| **backtest-agent** | spawned ad hoc | on-demand (after quant-research `validation_requested` signal) | first-repo DB (read+write via `run_sql_write` allowlist) | `brain/agent-outputs/backtest-agent/` | **ACTIVE**, event-driven |
| **market-builder** | template exists, no cron wrapper found | on-demand | — | — | **DORMANT/unclear** — no evidence of recent runs in agent-outputs; template says "must never write to polymarket_tracker.db" |
| **market-intelligence-agent** | template exists (`market-intelligence-agent.md`), listed in `DB_QUERYING_AGENTS` in spawn_agent.sh, no cron wrapper | on-demand | first-repo DB | — | **DORMANT** — no output directory activity found; possibly superseded by trader-intelligence-agent |
| **niche-app-agent** | template exists (oldest, Apr 21) | on-demand | — | `brain/agent-outputs/niche-app-agent/` (exists) | **DORMANT** — earliest-dated template, no recent cron or output |
| **research-agent** (`research.md`) | template exists, recently touched (Jul 4) | unclear — DB_QUERYING_AGENTS list includes "research" | first-repo DB | `brain/agent-outputs/research/`, signals `finding_ready` | **UNCLEAR** — template was recently edited (Jul 4) but no cron wrapper; may be the successor/rename in progress for market-intelligence or a new agent type being onboarded |
| **legendary_positions_scan.py** | direct script, not via spawn_agent.sh | weekly, Mon 07:30 (raw crontab line, not a cron_wrapper) | first-repo DB | `brain/agent-outputs/positions-scan/` | **ACTIVE** but architecturally inconsistent — every other scheduled agent goes through `cron_wrappers/`, this one is a bare crontab line pointing directly at a first-repo script |

### INITIAL FLAGS
- **research-scout dedup bug is real and ongoing** — confirmed via git status: identical story titles (deepseek-v4, foresightflow, polymarket-exchange-upgrade, "the-anatomy-of-a-decentralized...", "when-do-markets-fully-process...") appear as separate pending-review files dated 06-27, 06-29, 06-30 with only the date changed. Combined with the 2x/day cron cadence, this could be filing near-duplicates up to 12x/month per story. High-value Fable target.
- **market-builder and market-intelligence-agent appear dormant** with no cron wrapper and no recent output — either intentionally paused (Phase 5 doesn't need them yet) or orphaned infrastructure. Worth Fable confirming which.
- **`legendary_positions_scan.py` bypasses the cron_wrapper convention** entirely (raw crontab entry, no `.log` wrapper pattern, no `.env_trading` sourcing shown in the crontab line itself — relies on inherited cron environment). Inconsistent with every other scheduled job.
- **integration-test-agent's recent high failure rate** (86% per commit history) needs a root-cause check — is the swarm actually broken, or is the test suite itself stale/mis-calibrated?
- The **`research.md` / research-agent identity is ambiguous** — recently touched template, appears in `DB_QUERYING_AGENTS`, but has no cron wrapper. Possible in-progress agent that needs documentation, or a duplicate of an existing agent under a new name.
- Three Tier-3 promotions (code-hygiene, training-librarian, integration-test) all cite the *same* root cause (local model fabrication, 2026-05-14) — this was a one-time model-quality cliff that pushed cost up permanently. Worth noting for cost-tracking purposes, not a defect, but a compounding cost signal.

---

## 4. The Brain / Knowledge Layer

**Structure:** `brain/` contains ~350 markdown files and ~156 JSON files across: `decisions/` (100+ dated session summaries + named investigation docs), `agent-outputs/<agent>/` (17 subdirectories, one per agent + `archive/` + `handoffs/`), `research-scout/{approved,dismissed,pending-review,reviewed,archive}/`, `strategy-notes/` (pre-registered hypotheses), `reference-library/` (book/paper notes), `trader-profiles/` (48 JSON files, one per tracked wallet + `_index.json`), `market-intelligence/daily/`, `failed-experiments/`.

**State files at brain/ root:** `signals.json` (69,888 bytes), `feedback.json`, `findings.json` (113,916 bytes), `contract_violation_state.json` (rate-limit dedup for Telegram alerts, 24h window), `feedback_loop_state.json`, `integration-health.json` (written daily 06:00 UTC by first-repo's `write_integration_health.py`... actually the script lives in `scripts/write_integration_health.py` in trading-swarm, see §5), `polymarket_changelog_state.json`, `mythos_profiling_input.json`.

**Signal bus mechanics (`signals.json`):** Array-based, each signal has `{from, to, type, payload, timestamp, status}`. Orchestrator's `read_signals()` unions both a `signals[]` array and a legacy `pending[]` array as a safety net "so no signal is orphaned if an agent writes to the wrong top-level array" — this is a defensive patch for an existing inconsistency in how agents write to the file, not a clean single-schema bus. `mark_signal_processed()` only searches `signals[]`, not `pending[]` — meaning a signal written to the legacy `pending[]` array gets *read* (via the union) but never gets marked processed, so it could be re-processed on every cycle. Worth Fable verifying whether anything still writes to `pending[]`.

**`brain/integration-contract.md` is enormous** (1,413 lines, 90KB) — effectively a living spec of first-repo's schema, pools, known data-quality issues, and a full changelog back to v1.0. This is the single most information-dense file in the repo and the most safety-critical (every DB-querying agent is supposed to read it before querying).

### INITIAL FLAGS
- **`pending[]` vs `signals[]` dual-array bus is a real footgun** — the union-read/single-array-write mismatch in `read_signals()`/`mark_signal_processed()` means legacy-path signals can't be marked done. Confirm whether any current agent still writes to `pending[]`; if not, this is dead defensive code, if so it's a live re-processing bug.
- `brain/test.txt` and `brain/reference-library/test.txt` exist at brain root and inside reference-library — look like debug/scratch artifacts left in the tracked tree, not removed.
- `brain/mythos_profiling_input.json` is explicitly gitignored (only entry beyond broad patterns in `.gitignore`) — worth confirming why this one file needed a special-case ignore rather than a directory-level pattern; may indicate it contains something sensitive or just large/regenerable.
- `contract_violation_state.json` and `feedback_loop_state.json` are both tracked AND modified constantly (both show up as `M` in git status) — these are true "state files," legitimately mutable, but tracking them in git means every orchestrator cycle or feedback run creates a commit-diff, worth confirming this is desired (vs. moving genuinely ephemeral state outside git).

---

## 5. The Data Layer / Repo Connection (first-repo surface)

This is the cross-repo boundary. **First-repo lives at `/home/parison/projects/first-repo`**, owns `data/polymarket_tracker.db` (11.2 GB, ~10.6M rows, WAL mode), and runs its own `daily_maintenance.py` (19+ steps, listed in `integration-contract.md` §7). Trading-swarm does not own or migrate this database — it is a consumer, with one exception below.

**Every trading-swarm file that touches first-repo, by path:**

| File | Interface | Read/Write | Notes |
|---|---|---|---|
| `scripts/run_feedback_loop_agent.py:30,113,115` | direct `sqlite3.connect(uri, uri=True)` with `?mode=ro` | **READ-ONLY** (explicit URI ro mode) | Docstring: "Database: READ ONLY — never writes to polymarket_tracker.db." Matches `permissions/feedback-loop-agent.json` which explicitly forbids `run_sql_write`. |
| `scripts/calculate_geo_elo.py:29,50,143,145,148,195,197,200` | direct `sqlite3.connect(DB_PATH, timeout=30)` (no ro mode) | **WRITE** — `UPDATE traders SET geo_elo = ...`, `UPDATE traders SET geo_directionality_score = ...` | This is a **write from trading-swarm code directly into first-repo's production DB**, run outside the Tier 2/2.5 `ollama_agent_loop.py` write-allowlist mechanism entirely (it's invoked as a bare script, not through the agentic loop) — the O-24 write-allowlist fix (commit 60c0c2c) only hardens `ollama_agent_loop.py`'s in-loop SQL tool, it does not touch this script. Worth Fable confirming who calls this script, how often, and whether its two hardcoded UPDATE statements are still the sole writer for `geo_elo`/`geo_directionality_score` per the contract's "single-writer principle" (§18). |
| `scripts/write_integration_health.py:19,55` | `sqlite3.connect(str(DB_PATH), timeout=30)` | **READ** (queries only, per context — writes go to `brain/integration-health.json`, not the DB) | Runs daily 06:00 UTC per integration-contract §3; produces the pool-size numbers other agents are told to "always read live" rather than hardcode. |
| `orchestrator/ollama_agent_loop.py:280,351` + write-allowlist (lines ~60-150+) | `sqlite3.connect(db_path, timeout=30)` | **READ + gated WRITE** | This is the shared tool-calling runtime for Tier 2/2.5 local-model agents. Implements `run_sql` (any SELECT) and `run_sql_write` restricted to an exact-column allowlist for `UPDATE traders SET <col>`. Recently patched (O-24, 2026-07-10) after Fable found the previous regex only anchored the start of the string, letting `UPDATE traders SET geo_elo=1500, comprehensive_elo=9999 WHERE ...` smuggle an extra column past a check meant to only allow `geo_elo`. Fix adds an exact-assigned-columns check. This is the **primary enforced write boundary** in the whole system. |
| `scripts/backup_database.sh:20` | shells out to `cp`/`sqlite3 .backup` (not inspected line-by-line, but path confirmed) | READ (backup/copy only) | Daily 03:00 cron, copies first-repo's DB out. |
| `scripts/spawn_agent.sh:222` (comment) + `DB_QUERYING_AGENTS` allowlist | N/A — this is the prompt-injection gate | N/A | Determines which agent *types* get `integration-contract.md` injected into their prompt at spawn time: `backtest-agent feedback-loop-agent market-builder market-intelligence-agent performance-analyst-agent quant-research research signal-agent`. Agents not on this list (e.g. research-scout, code-hygiene, training-librarian) never see the contract — correct, since they don't query the DB, but worth Fable double-checking none of them do so anyway via some indirect path. |
| `scripts/cron_wrappers/run_daily_maintenance.sh` | `cd` into first-repo, runs `first-repo/scripts/daily_maintenance.py` | first-repo's own read/write | Trading-swarm's cron *owns the trigger* for first-repo's daily maintenance — an inbound dependency: if trading-swarm's crontab is ever lost/reset, first-repo's entire daily pipeline (19 steps, pool refresh, ELO update, resolution sweep) silently stops, with no alarm in either repo. |
| Raw crontab lines (not cron_wrappers): `legendary_positions_scan.py`, `backup_offsite.sh`, `weekly_resolution_sweep.sh` | direct first-repo script invocation | first-repo's own read/write | These 3 jobs live in the crontab but point straight at first-repo paths, bypassing the cron_wrappers logging convention entirely — inconsistent with the other ~10 jobs. |
| Quant-research one-off scripts (`brain/agent-outputs/quant-research/RQ1.1/rq1_1_elo_persistence.py`, `RQ2.2/rq2_2_entry_timing.py`, `RQ3.2/rq3_2_crowd_vs_elite.py`, `GEO-ELO-003/geo_elo_oos_validation.py`) | `sqlite3.connect` (RQ1.1/RQ2.2/RQ3.2 use explicit `?mode=ro`; GEO-ELO-003 uses plain `sqlite3.connect(DB_PATH, timeout=30)` with no ro flag) | Mostly READ, one (GEO-ELO-003) has no explicit read-only guard | These are historical research artifacts (committed output of past quant-research runs), not live infrastructure — but `geo_elo_oos_validation.py` connecting without `?mode=ro` means if it were ever re-run, it has ambient write capability even though its purpose is validation, not writing. Low risk (script is archived, not scheduled) but worth a one-line Fable check that it's never re-invoked outside a sandboxed copy. |

### INITIAL FLAGS
- **`calculate_geo_elo.py` is the single clearest example of trading-swarm code writing directly to first-repo's production DB outside the audited write-allowlist mechanism.** The O-24 fix protects the *ollama_agent_loop* SQL tool; it does nothing for this standalone script. This should be a named Fable deep-dive item: confirm current invocation frequency/caller, confirm it's still the sole/canonical writer per the contract's single-writer principle (§18), and confirm the write payload can't diverge from the two hardcoded UPDATE statements shown.
- **The daily_maintenance.py trigger lives in trading-swarm's crontab, not first-repo's** — an inverted, undocumented dependency. If anyone reasons about first-repo in isolation ("what schedules my daily maintenance?"), the answer is invisible unless they know to check the sibling repo's crontab.
- **3 of ~13 scheduled cron jobs bypass the cron_wrappers/ + logs/ convention** (`legendary_positions_scan.py`, `backup_offsite.sh`, `weekly_resolution_sweep.sh`), sourcing no `.env_trading`, following no consistent logging pattern. Inconsistent operational hygiene versus the other ~10 jobs.
- No trading-swarm script appears to implement or check the contract's **Section 9 validation query** (the pre-flight pool-size sanity check the contract itself mandates agents run "before executing any research queries"). It's unclear whether this validation is actually run by any agent automatically, or whether it's a documented-only step that depends on the LLM agent choosing to run it each time — see §7.

---

## 6. Git / Commit State

**Current branch:** `master` only (single branch, no evidence of feature branches surviving — `spawn_agent.sh` creates `feat/<task_id>` branches per agent run but merges and deletes them immediately in the same tmux command chain, win-or-abandon).

**Working tree at survey time:** 24 modified + 71 untracked = **95 uncommitted files**. Modified files are almost entirely brain state files (`signals.json`, `findings.json`, `integration-health.json`, `contract_violation_state.json`, `feedback_loop_state.json`, `polymarket_changelog_state.json`, 3 trader-profiles, `agent_registry.json`) plus **every tracked log file** (11 files under `logs/*.log`). Untracked files are almost entirely `brain/agent-outputs/**` daily/weekly outputs spanning **2026-06-26 through 2026-07-10** (14+ days) across data-audit, pre-resolution, str002-scoring, positions-scan, feedback-loop, trader-intelligence, plus 22 research-scout `pending-review/` files (many of which are the duplicate-story artifacts from the known dedup bug, §3).

**Tracked vs churning:** `logs/orchestrator.log`, `logs/backup.log`, `logs/*_agent.log` etc. and the state JSONs above are TRACKED and modified every cycle/run — meaning every orchestrator 10-minute cycle or agent run is technically a diffable change to a tracked file, even though `.gitignore` explicitly lists `logs/`, `*.log`, and `*.db`.

**`.gitignore` correctness — confirmed bug:** `.gitignore` contains `logs/` and `*.log` patterns, yet **46 files under `logs/`** are currently tracked in git (verified via `git ls-files | grep '^logs/'`), including `logs/orchestrator.log` at **5.86 MB** — the single largest tracked file in the repository by a wide margin (next largest tracked file is `findings.json` at 114 KB). This is the classic gitignore-doesn't-retroactively-untrack situation: these files were added to git (`git log --follow` shows the earliest commit as "chore: add analyst agent log files") before or despite the ignore rule, and nothing has run `git rm --cached` on them since. The orchestrator log grows forever and gets committed every session that touches the repo.

**Secrets/credentials check:** No hardcoded tokens or keys found in tracked `.py`/`.sh`/`.json` files (grepped for key/token/secret/password patterns and Telegram token assignments — all route through `os.getenv`/`os.environ.get`). `.env.example` contains only placeholder text. Actual credentials live in `/home/parison/.env_trading` (mode 640, not in this repo, not tracked).

**Wallet addresses:** `brain/trader-profiles/*.json` (48 files) are named by and contain third-party Polymarket wallet addresses. This is **not** a violation of CLAUDE.md's "never log or commit wallet addresses" rule as literally written — that rule is about the swarm's *own trading wallet* (anonymity of the entity that will eventually execute trades), not the public addresses of external traders being studied, which is the explicit purpose of the trader-intelligence subsystem. Worth Fable confirming this distinction is actually understood/intended and not an accidental gap in the rule's scope, since CLAUDE.md's wording is unqualified.

**Commit hygiene:** Recent commits (last 30, per `git log --oneline`) are almost all small, well-scoped `docs:`/`fix:` commits tied to individually-numbered O-series findings (O-2 through O-30) — good discipline, one concern/finding per commit. No evidence of giant multi-topic commits in the recent window.

### INITIAL FLAGS
- **`logs/orchestrator.log` (5.86 MB) and 45 other log files are tracked in git despite `.gitignore` explicitly excluding them.** This is the single most concrete, mechanical git-hygiene fix available: `git rm --cached` the already-tracked log files (keep them on disk, just stop versioning them) — growing forever, adds diff noise to every commit that happens to touch the repo at the same time, and will eventually bloat clone size materially.
- **95 uncommitted files, spanning a 14-day backlog** — confirms the "13-day-plus agent-output backlog" from prior sessions is still unresolved and has grown by roughly one more day. This isn't random churn — it's regular, expected daily/weekly output that simply isn't being committed on a cadence. Needs either an automated daily-commit cron step or a decision that these directories should be gitignored (if they're genuinely disposable) — right now they're neither reliably committed nor ignored, they just accumulate.
- **Stray scratch files** `brain/test.txt` and `brain/reference-library/test.txt` — small, but should be removed or explained.
- No branches other than master survive between sessions — confirms `spawn_agent.sh`'s auto-merge-or-abandon model is working as designed (feature branches for agent runs don't leak into the branch list), not a concern, just confirming expected behavior.

---

## 7. Integration Contract

**File:** `brain/integration-contract.md`, versioned (currently v2.13, 2026-06-23), 1,413 lines, with a full changelog back to v1.0 (2026-05-05).

**Is it enforced, or documentation-only?** Mixed — genuinely enforced in some places, documentation-only in others:

- **Enforced (code matches):** `orchestrator/ollama_agent_loop.py`'s write-allowlist mechanically restricts which columns Tier 2/2.5 agents can write via `run_sql_write`, matching the contract's single-writer principle (§18) for at least `geo_elo`/`comprehensive_elo`. The O-24 fix (2026-07-10) closed a real gap here (regex anchor bug), and that fix is now live in code — contract-vs-code alignment was actively tested and repaired, not just assumed.
- **Enforced (by injection, not validation):** `spawn_agent.sh` force-injects the full contract text into the prompt of any agent on the `DB_QUERYING_AGENTS` list before it can act — this guarantees the agent *sees* the contract, but nothing mechanically stops a Tier-3 Claude CLI agent from writing a query that ignores it. Enforcement here is "the LLM was told the rules," not "the rules are checked."
- **Documentation-only / trust-based:** The contract's own **Section 9 "Validation Query"** instructs agents to run a pool-size sanity check "at agent startup" and "halt if it fails," writing a `contract_violation` signal otherwise. There is no evidence in `orchestrator.py`, `spawn_agent.sh`, or `ollama_agent_loop.py` that this validation query is run automatically by any wrapper — it depends entirely on the spawned LLM agent choosing to execute it as instructed. The orchestrator *does* have a rate-limited handler for `contract_violation` signals (`_violation_rate_limited`, 24h dedup) — so the reporting side is real, but the triggering side is optional/LLM-discretion, not guaranteed.
- **Documentation-only:** Most of the contract (Sections 2-6d: query filters, pool definitions, known data-quality issues, ELO tier thresholds) is pure knowledge for the LLM to read and reason with — there's no static analysis or CI check that a given agent's generated SQL actually included the mandatory filters from Section 2. This is inherent to the LLM-prompted-agent design (you can't statically verify SQL an LLM hasn't written yet) but worth stating plainly: the "mandatory query filters" are mandatory by instruction, not by a gate.

**Does code match the contract?** Where checked (§5), yes — the JOIN key correction (v1.3), `geo_elo_active` usage, and single-writer discipline for `calculate_geo_elo.py`'s two columns all line up with what the contract currently says. The contract's own changelog shows a healthy pattern of "found a mismatch → fixed the contract or the code → documented it" (e.g. v1.3 JOIN key fix, v2.0 Pool B contamination warning, O-24 today).

### INITIAL FLAGS
- **Section 9's pre-flight validation query has no verified automatic trigger** — it's a documented obligation, not a code path Fable can point to and confirm runs every time. Good deep-dive target: grep every DB-querying agent template for whether it actually includes/executes the Section 9 query, versus just having it available to read.
- The contract is **the load-bearing document for correctness** of nearly every research/signal output in the system, and it is **maintained entirely as prose** (1,413 lines of markdown) with a manual changelog — there is no schema file, no JSON Schema, no generated-from-DB source of truth. Every update depends on a human or LLM session accurately transcribing DB reality into English. Given how much churn the changelog shows (14 versions in ~7 weeks), this is a high-maintenance, high-consequence-of-drift document.

---

## 8. External Surface

**Ollama (local models):** `http://localhost:11434/api/chat`, hardcoded in `ollama_agent_loop.py:OLLAMA_API_URL`. No auth (local-only service, standard for Ollama). Models: `gemma4:e2b`, `gemma4:e4b`, `qwen3-coder:30b-a3b-q4_K_M` per `spawn_agent.sh`'s tier mapping. Process confirmed running (`ollama serve`, PID 1110).

**Telegram:** 3 bots (orchestrator/agents/metrics), tokens loaded via `os.getenv("TELEGRAM_*_TOKEN", "")` in `orchestrator.py` and `scripts/run_feedback_loop_agent.py`. Chat ID also via env var. If unset, code degrades gracefully (`log.warning`, skips send) rather than crashing — confirmed by reading the `send_telegram()` function. No token ever appears hardcoded in tracked source (verified by grep, §6).

**Claude CLI (Tier 3/4):** invoked via `claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p` (or `claude-opus-4-7` for Tier 4), inside a git worktree, one-shot mode. `spawn_agent.sh` explicitly `unset ANTHROPIC_API_KEY` before invoking, forcing OAuth Pro-subscription billing instead of API-key billing (comment: "the API key has zero credit balance") — an interesting, deliberate cost-routing choice baked into the launcher, not documented in CLAUDE.md's model-routing table.

**First-repo (cross-repo, not strictly "external" but the only other codebase this system talks to):** covered exhaustively in §5.

**Credential handling, overall:** All secrets (`TELEGRAM_*_TOKEN`, `TELEGRAM_CHAT_ID`) live in `/home/parison/.env_trading` (mode `640`, owner `parison:parison`, not in git, sourced by cron_wrappers and the systemd `EnvironmentFile=` directive). `.env.example` is the only tracked reference and contains placeholders only. This pattern is consistent and correctly followed everywhere checked — no exceptions found.

**No other external APIs found** (no web-search, no market-data API keys, no exchange/CLOB API credentials in this repo — those, if they exist, would live in first-repo, since trading-swarm doesn't yet execute trades per the Phase 5/6/7 status in CLAUDE.md).

### INITIAL FLAGS
- The `unset ANTHROPIC_API_KEY` / OAuth-billing choice in `spawn_agent.sh` is a meaningful operational decision (cost model for every Tier 3/4 agent run) that isn't documented in `brain/model-routing.md` or CLAUDE.md — worth surfacing so it isn't silently "discovered" later if the OAuth subscription lapses or changes.
- No secrets exposure found anywhere in the external-surface review — this section is clean.

---

## Proposed Fable Deep-Dive Breakdown

Based on the map above, the following **9 areas** are sized for independent, self-contained deep review:

1. **Orchestrator core loop & immune system** (`orchestrator/orchestrator.py`) — registry cleanup correctness (stale June entry), respawn/retry logic, signal-bus dual-array (`signals[]`/`pending[]`) footgun.
2. **Cron scheduling & cross-repo trigger integrity** — full crontab audit, the 3 jobs that bypass `cron_wrappers/`, the inverted dependency where trading-swarm's cron triggers first-repo's `daily_maintenance.py`, and the research-scout 2x/day cadence question.
3. **Agent inventory reconciliation** — confirm live/dormant/renamed status of `market-builder`, `market-intelligence-agent`, `research.md`/research-agent, `niche-app-agent`; resolve the 14-vs-15-template count.
4. **research-scout dedup bug** — root-cause the re-filing mechanism (dedup check absent per prior memory), quantify duplicate volume given 2x/day cadence.
5. **Direct DB-write surface outside the allowlist** (`scripts/calculate_geo_elo.py`, `scripts/write_integration_health.py`, quant-research one-off scripts) — verify single-writer compliance and read/write mode correctness, independent of the already-audited `ollama_agent_loop.py` allowlist.
6. **`ollama_agent_loop.py` tool/write-allowlist mechanism** — the O-24-patched code itself; confirm the exact-column-match fix is complete and no analogous smuggling exists in `run_shell` or other tool paths.
7. **Integration-contract enforcement gap** — specifically whether Section 9's validation query is actually executed by any agent automatically versus documented-only; audit each DB-querying agent template for this.
8. **Git hygiene & repo state** — tracked log files (46 files incl. 5.86MB orchestrator.log) needing `git rm --cached`, the 95-file/14-day agent-output commit backlog, stray scratch files (`test.txt`×2), `.gitignore` correctness pass.
9. **integration-test-agent reliability** — investigate the recent 86% failure rate (7 failures) to determine if it reflects real regressions or a stale/miscalibrated test suite, given it's the agent explicitly responsible for catching exactly this class of problem.
