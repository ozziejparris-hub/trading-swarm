# Trading Swarm — Comprehensive Deep Audit (Fable)

**Date:** 2026-07-10
**Method:** Read-only. Every finding below was verified against live code, live crontab/systemd state, live git state, and the live signal bus unless explicitly marked **INFERRED**. No file was modified except this document. The ELO subsystem in first-repo is FROZEN — this audit maps the swarm's interactions with it and proposes no ELO changes.
**Orientation inputs:** `2026-07-10-trading-swarm-structural-survey.md` (Stage 1 map), `2026-06-29-overhang-ledger.md` (O-0…O-30), `2026-07-07-silent-failure-audit-FABLE.md` (Class 1–7 lens).

---

## Executive Summary — the seven findings that matter most

1. **The immune system's respawn does not exist** (Area 1, CRITICAL, proven). `orchestrator.py` marks a dead agent `"respawning"`, sends a Telegram saying "Auto-respawning" — and no code anywhere respawns anything. Tasks marked `respawning` leave the `running` set and are never looked at again. The MAX_RETRIES=3 escalation path is unreachable dead code. CLAUDE.md's "auto-retry up to 3, then escalates to Oscar" is false, and the Telegram message actively misreports.

2. **Output verification — the system's stated core principle — is unimplemented** (Area 1, CRITICAL, proven). `orchestrator.py:verify_output()` is never called; `scripts/verify_output.sh` (header: "Called by orchestrator after every task completion") has zero callers. "Agents cannot self-report success; files either exist or they don't" is enforced by nothing. The only output checking is the *weekly* integration-test agent — whose escalations go nowhere (finding 5).

3. **`geo_elo` has two full implementations, one per repo, and the swarm's one violates the contract's own §18 authority registry** (Area 2, CRITICAL capability / currently dormant, proven). Contract §18.3 names first-repo's `update_geo_elo.py` as sole owner of `geo_elo`/`geo_directionality_score` and `reconcile_geo_resolved_counts.py` as owner of `geo_resolved_trades_count`. Trading-swarm's `scripts/calculate_geo_elo.py` wipes all three **with no WHERE clause** (`UPDATE traders SET geo_elo = NULL, geo_resolved_trades_count = 0`) and rewrites them from a diverged formula, without co-writing `geo_elo_active` or refreshing Pool C. It is not scheduled, but it is unguarded, executable, points at production, and is unowned (its lint errors have been failing CI for 9 straight weeks — finding 6).

4. **Enforcement is inversely proportional to agent capability** (Areas 2/3, HIGH, proven posture). The O-24-hardened write-allowlist only constrains Tier 2/2.5 local models — and its two `run_sql_write` grants (quant-research, backtest-agent) belong to agents whose tier default is 3. Tier 3/4 agents run `claude --dangerously-skip-permissions` with full shell: every weekly agent (signal, trader-intel, performance-analyst, code-hygiene, integration-test, librarian) can write anything to first-repo's DB and files, gated only by prompt text. Additionally, the Tier 2/2.5 `write_file` tool's prefix check is **bypassable via `..` path traversal** (no `resolve()`), so even the weakest agents can technically write outside the swarm repo — including first-repo code and the enforcement layer itself.

5. **The integration-test agent works; the loop around it is broken** (Area 8, HIGH, proven). "86% failure rate" was a misreading — it's an 86% *pass* rate (43/50). But the same 7 failures have recurred for 5–9 consecutive Sundays, each marked "Escalation: YES — SYSTEMIC", written into untracked markdown files that nothing reads. Several failures are real (CI red 9 weeks; signal-agent missed its Jul-6 weekly; STR-003 signals resolved Jun 30 still unscored); several are miscalibrated tests (a weekly agent held to a 4-hour cadence). Reports are filed; nothing ever changes.

6. **CI has been red for 9 consecutive weeks on a 20-minute fix** — 8 F541 lint errors in `calculate_geo_elo.py` + 1 E722 in `run_trader_profiling.py`. Three agents (integration-test, performance-analyst, code-hygiene) independently re-report it weekly. Neutralizing `calculate_geo_elo.py` (finding 3) and the one-line E722 fix clears this too.

7. **The signal bus (`brain/signals.json`) is one corruption away from losing the STR-003 record** (Area 1/4, HIGH, proven latent). The orchestrator writes it non-atomically without a lock, while first-repo's `register_signal.py` writes the same file under a lock and agents use a third (flock-append) path. If the file is ever corrupt at read time, `orchestrator.write_signal()` reinitializes it to `{"signals": []}` — silently destroying `str003_signals` (the live strategy-validation record), `rescan_log`, and `pending`.

---

## Area 1 — Orchestrator core loop & immune system

**What it actually is:** a 10-minute health-check + Telegram-router loop (`run_immune_system()` → `process_signals()` → no-op metrics). It spawns nothing; all spawning is cron → `cron_wrappers/*.sh` → `spawn_agent.sh`. Its own docstring ("spawns new work") and CLAUDE.md's architecture diagram overstate it.

### Findings (severity-ranked)

| # | Sev | Status | Finding |
|---|-----|--------|---------|
| 1.1 | CRITICAL | proven | **Respawn is fictional.** `run_immune_system()` (orchestrator.py:439-449) sets `status: "respawning"`, increments `retries`, telegrams "Auto-respawning (attempt N/3)" — and returns. Nothing consumes `"respawning"`: `get_running_tasks()` filters `status == "running"` only. Consequences: (a) a dead agent is never retried; (b) `retries >= MAX_RETRIES` → "failed + alert Oscar" is unreachable (retries can only ever reach 1); (c) the Telegram message misinforms. The registry's lone stale entry (`signal-202606042140`, `status: failed, retries: 1`, June 4) is in a state the current code cannot produce — evidence of manual edit or older code, either way the registry has no lifecycle owner. |
| 1.2 | CRITICAL | proven | **Output verification dead in both implementations.** `verify_output()` defined orchestrator.py:340, zero call sites. `scripts/verify_output.sh` zero callers despite its header claiming the orchestrator calls it after every task. Every task's `"verified": false` registry field stays false forever (stored-but-never-applied class). |
| 1.3 | HIGH | proven, latent | **signals.json corruption → silent bus wipe.** `save_json()` is a plain overwrite (no temp+rename, no flock) racing register_signal.py's locked writes and agents' flock-append. On a corrupt read (`load_json` → None), `write_signal()` rebuilds the file as `{"signals": []}` — destroying `str003_signals` (8 entries incl. the resolved/active STR-003 validation cohort), `rescan_log`, `pending`. |
| 1.4 | MEDIUM | proven, latent | **Dual-array bus half-repair.** `read_signals()` unions `signals[]` + legacy `pending[]`; `mark_signal_processed()` only searches `signals[]`. A pending-status entry in `pending[]` would re-fire (and re-Telegram) every 10 minutes forever. Currently latent — `pending[]`'s 2 entries have statuses `processed`/`approved` — but one legacy-path write away from live. |
| 1.5 | MEDIUM | proven | **Uncontrolled status vocabulary.** Live bus contains statuses `processed`, `completed`, `approved`, and one signal with **no status field** (permanently invisible — only exact `"pending"` is processed). No schema validation on entries; the contract's 20-field schema is enforced only inside register_signal.py, for STR-003 entries. |
| 1.6 | MEDIUM | proven | **The 4-hour timeout only warns, never acts, and spams.** `check_agent_timeout()` never kills the session or changes status, and the warning has no rate limit (unlike contract violations) → identical Telegram every 10 min for a long-running agent. "Timeouts (>4h)" in CLAUDE.md implies enforcement that doesn't exist. |
| 1.7 | LOW-MED | proven | **Alert delivery can fail silently.** `send_telegram()` uses `parse_mode: Markdown` with unescaped dynamic content (market titles, task descriptions). An underscore/asterisk in a payload → Telegram 400 → exception caught, `log.error` only. Alerts about failures can themselves silently fail. (The ollama-loop's `tool_send_telegram` sends plain text — inconsistent.) |
| 1.8 | LOW | proven | Registry read-modify-write races: three unlocked writers (orchestrator, spawn_agent.sh registration heredoc, per-task cleanup script). Cleanup writes `status: completed` then immediately deletes the entry (dead write; no run history retained). If cleanup throws, the entry stays `running` forever — this is the stale-entry generator. `mark_signal_processed` keyed on timestamp only (collisions co-mark). `send_weekly_metrics()` fully commented out but still called. `AGENT_TIER_DEFAULTS`/`select_tier()` appear to have **no callers** — dead config (spawn tier comes from cron wrappers' explicit argument) — **INFERRED** (grep of orchestrator.py; confirm nothing external imports it). |

### Structural recommendation
Decide what the orchestrator *is*. Either (a) make it a real supervisor — implement respawn by actually invoking `spawn_agent.sh`, wire `verify_output` to a per-agent expected-output manifest (each cron wrapper already knows what file its agent must produce), enforce the timeout by killing + marking failed — or (b) demote it honestly to "health reporter + Telegram router" in CLAUDE.md and its own docstrings, and delete the dead respawn/verify/tier-selection code. Both are defensible; the current state (documented supervisor, actual reporter, lying alerts) is the worst option. Independently: a single locked, atomic (temp+rename) write helper for signals.json, shared by both repos (this is O-29's shared-helper discipline applied at the swarm boundary), and never reinitialize the bus on corrupt read — halt and alert instead.

---

## Area 2 — Cross-repo write surface (HIGHEST PRIORITY)

Complete map of every path by which trading-swarm code can write to first-repo's DB or files, plus the reverse surface.

### 2a — `scripts/calculate_geo_elo.py` — the loaded gun (CRITICAL capability, dormant)

- **Writes:** `UPDATE traders SET geo_elo = NULL, geo_resolved_trades_count = 0` (no WHERE — every row), then rewrites both for qualifying traders; `UPDATE traders SET geo_directionality_score = NULL` then rewrites. Single transaction per phase (atomic, at least). Also writes `brain/findings.json` **without a lock** (races the flock-append path).
- **Contract violation (proven):** §18.3 assigns all three columns to first-repo owners (`update_geo_elo.py`, `reconcile_geo_resolved_counts.py`). This script is a second, diverged implementation: different filters (joins `markets.category`; its own `winning_outcome` exclusions), **no `geo_elo_active` co-write, no `refresh_pool_c()`, no bot/wash-filter pass** — first-repo's owner does all three. A run today would clobber the canonical daily values with formula-divergent ones and leave `geo_elo_active`/Pool C inconsistent until the next daily maintenance partially self-heals. This is O-6's Path-A/Path-B disease reproduced *across repos*, on the geo chain.
- **Current invocation: none** (proven — no cron entry, no wrapper, no code caller). It's a May-25 research artifact (RQ-GEO-ELO-001 v2) left executable on the production path. Its own pre-flight `validate()` hardcodes thresholds (`clean_pool < 440`, `clean_markets < 11000`) that are stale by an order of magnitude vs contract §9's 2026-06-29 expected values.
- **It is also the file breaking CI** (8×F541, 9 consecutive weeks — see Area 8).
- **Fix (one decision, three payoffs):** retire it — move to `brain/agent-outputs/quant-research/GEO-ELO-001/` as a historical artifact, or add the first-repo simulation-script guard (hard-refuse without `--allow-production-write`, session #41 precedent, commit `a5f9bb7`). Either clears the §18 violation, removes the loaded gun, and (if moved out of `scripts/`) ends the 9-week CI failure in the same stroke. Record the retirement in §18/§8 of the contract.

### 2b — `orchestrator/ollama_agent_loop.py` `run_sql_write` (post-O-24)

- The exact-column fix is sound for the smuggling class (verified by code read — see Area 3). But **the allowlist's five permitted columns each contradict §18**: `geo_elo`/`geo_directionality_score` (owner: update_geo_elo.py), `geo_resolved_trades_count` (owner: reconcile_geo_resolved_counts.py), `research_excluded` (owner: update_research_exclusions.py + the O-23 `manual_override` mechanism — an agent write would either be reverted within 24h by the daily state machine, or worse, *set* an exclusion without `manual_override`, which then silently reverts: the exact O-23 failure mode, re-introduced by design), and `bot_type` (the durable-exclusion marker O-23 leans on — an agent setting/clearing `bot_type` silently corrupts the exclusion state machine).
- **Never invoked to date** (O-24 verified zero `run_sql_write:` log lines; unchanged). And the two agents holding the grant (quant-research, backtest-agent) default to Tier 3, where this code path isn't even used — the grants are live only if someone spawns them at Tier 2/2.5.
- **Verdict:** the mechanism is now well-guarded against the found attack, is aimed at columns it shouldn't permit at all, for agents that don't currently run through it. Structural fix in Area 3.

### 2c — Tier 3/4 agents: the unguarded majority (HIGH, proven posture)

`spawn_agent.sh` runs Tiers 3/4 as `claude --dangerously-skip-permissions -p` in a worktree with full shell. Nothing mechanical prevents any of the six weekly Tier-3 agents from executing arbitrary SQL against `polymarket_tracker.db` or editing first-repo files. The entire write-governance investment (O-24, permissions/*.json) applies to the tier that runs the *weakest* models on the *narrowest* tasks; the strongest agents with the broadest missions have prompt-text governance only. No incident found — but this is the same "hole was live, we got lucky" shape as O-24. Needs a posture decision from Oscar (see Action List / consolidation).

### 2d — Path-traversal bypass in the Tier 2/2.5 write tools (HIGH capability, proven by code read)

`tool_write_file`, `tool_append_to_json_array`, and `tool_write_handoff` gate on `path.startswith("/home/parison/trading-swarm/")` **without normalizing**: `/home/parison/trading-swarm/../projects/first-repo/scripts/anything.py` passes the check and writes outside the repo. A Tier-2/2.5 agent (or anything that prompt-injects one via content it reads) can write **any file writable by user `parison`** — first-repo production code, `~/.env_trading`, cron wrapper scripts that cron later executes. Also, even without traversal, `WRITE_PREFIX` legitimately includes `orchestrator/ollama_agent_loop.py` itself and `scripts/cron_wrappers/` — **the enforcement layer is inside its own write surface**. Fix: `Path(path).resolve()` before the prefix check, and narrow the write prefix to `brain/` (+ `logs/agent_logs/`). Not tested live (read-only audit) — the code path is unambiguous.

### 2e — Lower-risk writers / readers (verified)

| Path | Mode | Verdict |
|---|---|---|
| `scripts/run_feedback_loop_agent.py` | `?mode=ro` URI | Correct — genuinely read-only, matches its permissions note. |
| `scripts/write_integration_health.py` | plain connect, queries only | Works, but carries ambient write capability — switch to `?mode=ro` (one line). |
| `scripts/backup_database.sh` | `sqlite3 .backup` + `PRAGMA integrity_check` + delete-on-fail | Sound (the swarm-side backup never had first-repo's O-19 bug). Minor drift: header says "keeps 7 days", `KEEP_DAYS=3`. |
| Archived quant scripts (GEO-ELO-003 etc.) | one lacks `?mode=ro` | Historical artifacts; same retirement sweep as 2a. |

### 2f — The reverse surface: first-repo writes INTO trading-swarm's brain (bigger than the survey mapped)

At least **10 first-repo scripts** hardcode trading-swarm paths: `register_signal.py`, `score_str003_signals.py`, `detect_counter_signals.py` (→ `brain/signals.json` / `findings.json`); `audit_invariants.py` (→ `agent-outputs/data-audit/`); `pre_resolution_intelligence.py`, `score_str002_signals.py`, `legendary_positions_scan.py`, `register_str002_signals.py`, `calibrate_composite_threshold.py`, `signal_credibility.py` (reads positions-scan). **brain/ is a genuinely shared cross-repo datastore, with three different locking disciplines on its most critical file and no contract governing the first-repo→brain direction at all** (the integration contract only governs swarm→DB). The daily data-audit/pre-resolution/str002 files that dominate the git backlog (Area 9) are first-repo outputs.

### First-repo integrity threats — explicit flag

1. `calculate_geo_elo.py` — unguarded, contract-violating full-column rewrite capability on the geo chain (dormant; retire it).
2. Tier-3 `--dangerously-skip-permissions` posture — unbounded DB/file write capability on 6 weekly agents (standing).
3. Allowlist sanction of `bot_type`/`research_excluded` agent writes — would corrupt the O-23 exclusion state machine (latent; never exercised).
4. `write_file` path traversal — swarm agents can write first-repo code (latent; fix is one `resolve()`).
None of these touches the frozen `comprehensive_elo` chain today (O-24 closed that specific path), but 2c could — a Tier-3 agent is one prompt-drift away from any column.

---

## Area 3 — The write-allowlist mechanism itself

- **3.1 (verified sound):** `_assigned_columns()`/`_match_write_allowlist()` — the O-24 exact-single-column check is correct for the smuggling class; ambiguity (e.g. `=` inside quoted values) fails toward deny; full-table `UPDATE traders SET geo_elo=…` without WHERE is caught by the 50K row cap (traders table >> 50K rows). The 23 O-24 tests cover the attack variants.
- **3.2 (MEDIUM, proven):** **Tool-description drift inside the just-patched file.** `TOOL_DEFINITIONS`' `run_sql_write` description (ollama_agent_loop.py:688-700) still advertises the three patterns O-24 *removed*: `UPDATE traders SET accuracy_pool`, `ALTER TABLE traders ADD COLUMN`, `INSERT INTO trader_notes`. The LLM is explicitly invited to attempt writes the allowlist will reject (wasted iterations, confusing failures), and a future maintainer reading the tool schema gets the pre-fix picture. Related dead code: `_DDL_RE` and the "skip row-count guard for DDL" branch survive although no DDL can pass the allowlist anymore.
- **3.3 (structural, echoes O-24's "NOT DONE"):** Regex-gating LLM-generated SQL text remains the wrong posture, and now demonstrably drifts against §18 (Area 2b). The structural fix is **named, parameterized operations**: e.g. `set_trader_bot_type(address, bot_type, reason)` implemented as a thin wrapper that routes through (or is exported by) first-repo's owning script for that column, with value-range checks and a durable audit trail (current trail = log lines only). The allowlist's column set should be *generated from* §18's registry, not maintained in parallel — today they contradict each other, and §18 is defined as authoritative.
- **3.4:** `run_shell` exact-list whitelist is fine. `run_sql` SELECT-gating regex (`^\s*(INSERT|UPDATE|...)`) doesn't block `PRAGMA`-based writes or CTE tricks — **INFERRED** low risk (SQLite `WITH ... SELECT` can't write; `PRAGMA journal_mode` etc. is benign-ish) but worth a denylist review when 3.3 lands.
- **3.5:** see 2d — the file-write tools in the same file are the weaker sibling; fix together.

---

## Area 4 — Integration-contract enforcement gap

**How the contract is "enforced," precisely, in descending order of realness:**

1. **Mechanical, real:** the run_sql_write allowlist (but see 2b — it enforces the wrong column set) and `run_sql`'s SELECT-only gate, for Tier 2/2.5 only.
2. **Injection, not validation:** `spawn_agent.sh` inlines the full 1,413-line contract into DB-querying agents' prompts with "Run the Section 9 validation query first. Halt if it fails." Guarantees exposure, verifies nothing.
3. **Nothing:** no wrapper, spawner, or loop actually executes §9. Bare scripts do their own thing (`run_feedback_loop_agent.py` has no §9 run — **INFERRED** from grep, spot-check its query preamble; `calculate_geo_elo.py` has a hand-rolled version with thresholds ~14× stale). The `contract_violation` signal path is real on the *receiving* side (orchestrator handler, 24h rate-limit) — the *sending* side is voluntary.

**How bad is it?** For reads: medium — the failure mode is research on a degraded pool (exactly what O-0's Pool C decline would have produced silently), not corruption. For writes: the contract isn't the write barrier anyway (Areas 2/3 are). The asymmetry to fix first is that §9 is *cheap to enforce for real*: one shared `preflight_contract_check.py` (runs the §9 SQL, compares against `brain/integration-health.json` — not the prose table's hardcoded 2026-06-29 numbers, which are already a stale-threshold instance of the O-28 class — writes `contract_violation` + exits nonzero on breach), called by `spawn_agent.sh` before spawning any `DB_QUERYING_AGENTS` member and by the bare-script wrappers. That converts the contract's most safety-relevant clause from LLM-discretion to a gate, for ~50 lines.

**Also noted (proven):** the contract v2.9 prohibits direct signals.json writes, and first-repo's `register_signal.py` honors that with locked atomic writes — but the orchestrator's own `write_signal()` and two other first-repo scripts write the file directly with different discipline. The rule exists; its own infrastructure doesn't follow it. And §13's mandated `register_signal.py` **does exist and is used** (survey's open question — resolved, it's real).

---

## Area 5 — Agent inventory reconciliation

15 templates (CLAUDE.md says 14 — off by one, the ambiguous `research.md`).

| Agent | Schedule | Tier | Status | Notes |
|---|---|---|---|---|
| feedback-loop | Mon 07:00 | bare Python | **ACTIVE** | read-only DB (ro URI), healthy |
| performance-analyst | Mon 06:00 | 3 | **ACTIVE** | weekly output current |
| trader-intelligence | Mon 07:15 | 3 | **ACTIVE** | |
| changelog-monitor | Mon 07:30 | bare Python | **ACTIVE** | has timeouts, state-file dedup — clean |
| positions-scan | Mon 07:30 | first-repo script, raw crontab | **ACTIVE** | bypasses wrapper convention |
| signal-agent | Mon 08:00 | 3 | **ACTIVE but faltering** | missed its Jul-6 weekly output (proven, integration-test 07-05); STR003-004/008 resolved Jun 30 remain unscored |
| research-scout | daily ×2 | bare Python + Claude CLI websearch | **ACTIVE, buggy** | Area 6 |
| code-hygiene | Fri 20:00 | 3 | **ACTIVE** | |
| training-librarian | Sat 09:00 | 3 | **ACTIVE** | |
| integration-test | Sun 23:00 | 3 | **ACTIVE** | Area 8 |
| quant-research | on-demand | 3 | **DARK 40+ days** | integration-test: Phase 5 Gate 4 blocked on it — this is a *strategic* dormancy, needs Oscar |
| backtest-agent | on-demand | 3 | **DARK 35+ days** | downstream of quant-research |
| market-builder | none | — | **DORMANT** | Phase 7 material; fine, but mark it |
| market-intelligence-agent | none | — | **DORMANT/superseded?** | likely superseded by trader-intelligence — retire or document |
| niche-app-agent | none | — | **DORMANT** | oldest template |
| research (`research.md`) | none | — | **AMBIGUOUS** | edited Jul 4, in `DB_QUERYING_AGENTS`, no wrapper, no outputs — in-progress onboarding or an orphan; needs an owner decision |

**Dead/contradictory config (proven):**
- `AGENT_TIER_DEFAULTS` + `select_tier()` in orchestrator.py: no live caller found — tier actually comes from each cron wrapper's explicit argument. Its keys also don't match template names (`training-librarian` vs `training-librarian-agent`, `market-intelligence` vs `market-intelligence-agent`), and unknown keys silently default to Tier 3 (paid) — harmless only because the whole map appears dead.
- `agent_tool_permissions.json` (legacy shared file): lists tool grants for integration-test/code-hygiene/training-librarian — all Tier 3, never routed through the ollama loop. Dead config whose own `note` fields admit it.
- `permissions/quant-research.json` and `permissions/backtest-agent.json` say "Tier 2.5 Qwen3-Coder" in their notes while every other source says Tier 3. These are the only two `run_sql_write` grants in the system, attached to a mode nothing currently uses. Self-contradictory config on the most sensitive permission.
- `run_trader_profiling.py` docstring says it calls the **Anthropic API** — the rest of the system deliberately unsets `ANTHROPIC_API_KEY` ("zero credit balance"). If the trader-intelligence flow depends on this script, it either fails or bills a dead key — **INFERRED**, trace its caller before trusting trader-profile freshness.
- Registry: one stale June-4 entry in a state current code can't produce (Area 1.1).

**Structural:** an `agents-manifest` (one file: agent → template, tier, schedule, entry point, expected output path, status ACTIVE/DORMANT/RETIRED) from which the crontab expectations, integration-test cadence checks (Area 8), and the orchestrator's verification manifest (Area 1) are all derived. Today those four views of "what agents exist" are maintained independently and all disagree somewhere.

---

## Area 6 — research-scout dedup bug (root cause + corpus verdict)

**Root cause (proven, by construction):** `run_research_scout.py` has no dedup anywhere in its path:
1. `write_finding()` names files `{TODAY}-{HOUR}-{slug}.md` and never consults what's already in `pending-review/` (or approved/dismissed/reviewed/archive).
2. The prompt contains **no memory** of previously filed findings — nothing tells the model "you already reported this."
3. The prompt **hardcodes the same 3 search topics permanently**, including "DeepSeek V4 release status" as a standing daily query — which is why that exact story recurs forever. Topic 1/2 (Polymarket announcements, arXiv prediction-market papers) regenerate the same hits for as long as they stay in search results.
4. The cron runs it **twice daily** (08:00 + 20:00); the `-{HOUR}-` filename component exists precisely so the evening run doesn't overwrite the morning file — the collision that would have accidentally deduped same-day repeats was engineered *around* instead of treated as a signal.

So duplicates are structural: ~2 filings/day per still-newsworthy story, matching the observed 06-27/06-29/06-30/07-03 refilings and O-11's 40+ item backlog.

**Is the corpus trustworthy for Oscar's eventual review?** Partly. Each file's *content* is a genuine one-shot Claude web-search result (real capability, 120s timeout, HIGH/MEDIUM filter) — the findings aren't fabricated-by-construction. But: (a) the `## Verified — Yes` stamp is written **unconditionally** on every finding, and the `verified: true` field it reflects is *model-self-asserted* — nothing checks the URL resolves or says what the summary claims; (b) the corpus is duplicate-dominated, so review effort is mostly wasted re-reading; (c) the fixed 3-topic prompt means the scout's actual coverage is far narrower than "external AI developments" — scope silently shrunk to whatever those three queries return (circuit-breaker-shrinks-scope class). **Verdict: redundant and over-labeled, not corrupted.** A one-time dedup (key: slug or source_url across all five state dirs) + honest labeling makes it reviewable.

**Fix shape:** (1) an index file (`brain/research-scout/_seen.json`: slug/source_url → first-filed date, current status) checked before writing and injected into the prompt as "already reported — do not refile"; (2) rotate/derive topics from `priorities.md` instead of hardcoding; (3) label verification honestly ("model-asserted"); (4) drop to 1×/day unless the evening run has a distinct purpose; (5) one-time dedup pass over pending-review as the precondition for the O-11 triage session.

---

## Area 7 — Cron scheduling & cross-repo trigger integrity

Live crontab verified (15 entries) + `polymarket-sunday-elo.timer` + `trading-swarm.service` (**active since 2026-07-07 06:13 UTC** — CLAUDE.md's "NOT been started" warning is 3 days stale; proven).

| # | Sev | Finding |
|---|-----|---------|
| 7.1 | MED | **`weekly_resolution_sweep.sh` (Sun 03:30) has no output redirect** — the only crontab line with none. stdout/stderr are discarded (no MTA). The weekly resolution sweep can fail silently forever — textbook Class-4. One-line fix. |
| 7.2 | MED | **Inverted dependency, still undocumented:** first-repo's entire daily pipeline is triggered from the *swarm's* crontab (`run_daily_maintenance.sh` cd's into first-repo). Crontab loss = first-repo's 29-step maintenance silently stops. O-28's maintenance-freshness invariant is the detection fix; until it lands, this is a single point of silent failure spanning both repos. Document it in both repos' CLAUDE.md at minimum. |
| 7.3 | MED | research-scout ×2 daily — doubles the dedup bug's output (Area 6). No documented rationale found for the 20:00 run. |
| 7.4 | LOW-MED | 3 of 15 entries bypass the cron_wrappers convention (positions-scan, backup_offsite, resolution-sweep): no `.env_trading` sourcing, inconsistent logging (7.1 is the worst case). Normalize into wrappers. |
| 7.5 | LOW | **Monday convoy:** 06:00 first-repo maintenance (steps budgeted up to 8-10h post-O-27) overlaps every weekly agent (06:00–08:00) on the same WAL DB. WAL reads are safe and agents carry 30s busy_timeouts, so this is contention, not corruption — but Monday agent output is computed *mid-maintenance* (pool counts moving underneath them). Worth a conscious ordering decision, not urgent. |
| 7.6 | LOW | Tier-3 agents end their runs with `git checkout master && merge && push` on the shared base repo — two agents finishing simultaneously race; a merge conflict strands output on a branch with the failure noted only in the agent's own log. Historically clean (all 82 surviving branches are merged — proven), but the failure path is silent by design. |

---

## Area 8 — integration-test-agent: 86% and what it means

**Correction:** 86% is the **pass** rate (43/50, 2026-07-05 report). The survey's "86% failure rate" was a misread of the commit message "7 failures (86%)".

**The real problem is worse than a flaky suite — it's a working smoke alarm in an empty building:**
- **Real failures, correctly detected, never actioned:** `ci_pipeline_passes` red for **9 consecutive Sundays** (the calculate_geo_elo/run_trader_profiling lint, a self-described 20-minute fix — Areas 2a/6 of this doc); signal-agent produced no Jul-6 weekly output; STR003-004/008 resolved Jun 30 and still unscored in strategy-registry (live Phase-5 evidence going stale).
- **Miscalibrated tests, permanently red by design:** signal-agent held to a "max cadence 4h" (it's weekly); quant-research to 72h (it's on-demand and strategically paused). These will never pass under the current schedule, and their noise buries the real reds.
- **The escalation loop is toothless:** every failure carries "Escalation: YES — SYSTEMIC — escalate HIGH" computed each week into an untracked markdown file. Whether the agent also fires Telegram alerts is **unverified** — but empirically irrelevant: the same CRITICAL persisted 9 weeks, so either alerts don't fire or they don't land as work items. Reports that nobody consumes are the exact "presence-tested, not liveness-tested" theme of the 07-07 audit, applied to the auditor itself.

**Fixes:** (a) clear the 9-week CI red via Area 2a's retirement + the one-line E722; (b) derive cadence expectations from the agents-manifest/crontab (Area 5) so a weekly agent is tested weekly; (c) give escalations a durable landing: write a `contract_violation`-style signal to the bus (the orchestrator already Telegrams those, rate-limited) with a consecutive-weeks counter, and/or commit the reports so they show in git history; (d) after recalibration, a red Sunday report should be rare enough to treat as a page, not wallpaper.

---

## Area 9 — Git hygiene & repo state

**Proven state:** 46 log files tracked (7.0MB, `orchestrator.log` 5.86MB = largest tracked file, grows every 10-min cycle) despite `.gitignore` listing `logs/` and `*.log` — twice each (the ignore file itself has duplicate blocks). 96 uncommitted files (24 M, 72 ??), the untracked set spanning 2026-06-26→07-10 agent outputs (mostly *first-repo-generated* daily files: data-audit, pre-resolution, str002-scoring — see 2f). 82 fully-merged stale `feat/` branches (survey's "no branches survive" was wrong; `spawn_agent.sh` removes worktrees but never deletes branches — all merged, so clutter, not stranded work). `.claude/` untracked. `brain/test.txt` + `brain/reference-library/test.txt` stray. Secrets: **clean** (all credentials env-based, `~/.env_trading` mode 640 outside the repo, `.env.example` placeholders only). Recent commit discipline good (small, O-numbered).

**Proposed correct state:**
1. `git rm --cached -r logs/` (keep on disk) — kills per-cycle diff noise and the 5.86MB growth; add logrotate or size-capped rotation for `orchestrator.log` separately (it grows unbounded on disk too).
2. **Untrack ephemeral runtime state:** `orchestrator/agent_registry.json`, `brain/contract_violation_state.json`, `brain/feedback_loop_state.json`, `brain/polymarket_changelog_state.json`, `brain/integration-health.json` (regenerated daily) → gitignore. These are runtime state with no forensic value per-commit.
3. **Keep tracked, commit on cadence:** `signals.json`, `findings.json`, `trader-profiles/`, `strategy-registry.md` — these are the strategy-validation record; the O-ledger repeatedly cites their history as evidence. Add a **nightly auto-commit cron step** scoped to `brain/agent-outputs/ brain/research-scout/ brain/signals.json brain/findings.json brain/trader-profiles/` with a dated message — this single job ends the standing N-day backlog class permanently. (Needs Oscar's sign-off on "commit generated outputs" as policy; the alternative — gitignore them — contradicts how much this project's audits lean on their history.)
4. Delete the 82 merged branches (`git branch --merged master | grep -v master | xargs git branch -d` — all verified merged); add `git branch -d "$BRANCH_NAME"` to spawn_agent.sh's post-merge chain; prune the 3 stale `origin/feat/*` remotes.
5. Ignore `.claude/`; delete the two `test.txt` strays; fix the duplicated `.gitignore` blocks.
6. **Wallet-address rule needs scoping (Oscar):** `trader-profiles/` commits 48 third-party wallet addresses; CLAUDE.md's "never log or commit wallet addresses" is unqualified. Almost certainly intended to mean *the system's own trading wallet* — codify that distinction in CLAUDE.md so a future hygiene agent doesn't "fix" the trader-intelligence corpus.
7. Reconsider unattended `git push origin master` from agent tmux sessions (7.6): keep auto-merge locally if desired, but pushing unreviewed agent commits to the remote as `master` is a posture choice Oscar should re-confirm now that Tier-3 agents run weekly.

---

## Silent-failure-class scorecard (the first-repo lens, applied)

| Class | Swarm instances found |
|---|---|
| Stored-but-never-applied | `verify_output` (both impls); registry `verified` field; `AGENT_TIER_DEFAULTS`/`select_tier`; legacy `agent_tool_permissions.json`; allowlist tool-description phantom patterns; `send_weekly_metrics` |
| Multi-writer convention drift | `geo_elo` chain: 2 implementations across repos + allowlist third path (§18 says one owner); `signals.json`: 3 writer classes, 3 locking disciplines; `findings.json`: locked-append vs raw-overwrite writers |
| No-timeout/no-bound | agent 4h "timeout" warns forever, never kills; `orchestrator.log` unbounded + tracked; (external calls are otherwise well-bounded — better than first-repo was) |
| Silently-swallowed exceptions | Telegram send failures (alerts about failures die in a log); merge failures noted only in agent logs; registry cleanup failure → permanent "running" entry |
| Health-checks testing the wrong thing | immune system checks tmux liveness, not outputs; "Auto-respawning" message with no respawn; integration-test cadence expectations wrong for ≥2 agents; §9 expected-values table hardcoded at 2026-06-29; scout's unconditional "Verified: Yes" |
| Circuit-breaker silently shrinking scope | research-scout's hardcoded 3-topic prompt vs its broad mission; `DB_QUERYING_AGENTS` list vs agents added later (manual sync) |
| Derived fields not co-written | `calculate_geo_elo.py` writes `geo_elo` without co-writing `geo_elo_active`/Pool C (the owner script co-writes both) — O-17's class at the cross-repo level |

---

## Prioritized Action List

### FIX NOW (small, high leverage — most are <1 session combined)
1. **Retire `calculate_geo_elo.py`** (move to agent-outputs archive or hard-guard with `--allow-production-write`); note retirement in contract §18/§8. Simultaneously fix `run_trader_profiling.py:271` E722. **Clears: the loaded gun, the §18 violation, and the 9-week CI red in one commit.**
2. **`Path(path).resolve()` before every prefix check** in `tool_write_file`/`tool_append_to_json_array`/`tool_write_handoff`; narrow `WRITE_PREFIX` to `brain/` (+ `logs/agent_logs/`). (2d)
3. **Fix the `run_sql_write` tool description** (remove the 3 removed patterns; delete the dead DDL branch). (3.2)
4. **Make the orchestrator honest:** implement respawn (invoke spawn_agent.sh) *or* first-death→`failed`+accurate Telegram; delete/repair the unreachable escalation branch; rate-limit the timeout warning. (1.1, 1.6)
5. **Signals.json safety:** locked atomic write in `save_json` (or route orchestrator writes through the flock-append helper that already exists in the same codebase); on corrupt read, halt+alert — never reinitialize. (1.3)
6. **Update CLAUDE.md:** service is running (since 07-07); orchestrator's real role; 15 templates; wallet-rule scoping (pending Oscar). (7.6, 5, 9.6)
7. **Git mechanical pass:** `git rm --cached -r logs/`; delete 82 merged branches + add `branch -d` to spawn_agent.sh; ignore `.claude/` + ephemeral state JSONs; delete `test.txt`×2; dedupe `.gitignore`. (9)
8. **Add the missing log redirect** to the `weekly_resolution_sweep.sh` crontab line. (7.1)

### HARDEN (medium)
9. **§9 pre-flight as code:** shared `preflight_contract_check.py` (compares against live `integration-health.json`, writes `contract_violation`, exits nonzero) wired into spawn_agent.sh for `DB_QUERYING_AGENTS` + bare-script wrappers. (4)
10. **Research-scout dedup:** `_seen.json` index + prompt memory + honest verification labels + topics derived from priorities; one-time dedupe of pending-review (precondition for O-11 triage); Oscar decides 1×/day vs 2×. (6)
11. **Integration-test recalibration + landing escalations:** cadence from the agents-manifest; escalations become bus signals (orchestrator already Telegrams those) with consecutive-week counters; commit the Sunday reports. (8)
12. **Wire output verification:** per-agent expected-output manifest; orchestrator (or the cron wrapper itself) verifies post-run and signals on absence — this is the cheap, honest version of the immune-system promise. (1.2)
13. **Nightly brain auto-commit** (pending Oscar's policy sign-off) — ends the backlog class. (9.3)
14. **Bus schema:** single status vocabulary, validate on write, migrate `pending[]` remnants into `signals[]` and delete the union hack. (1.4, 1.5)

### CONSOLIDATE (structural — where the swarm needs first-repo's discipline)
15. **Named write operations across the boundary (O-29 extended):** kill raw-SQL agent writes entirely; swarm-side writes become named, parameterized, range-checked operations that route through first-repo's §18 owner scripts (or a library they export); allowlist column set generated from §18, not maintained in parallel. This retires the "regex vs LLM" posture O-24 flagged as structurally fragile.
16. **Tier-3 posture decision (Oscar):** today the most capable agents have zero mechanical write governance (`--dangerously-skip-permissions` + full shell). Options, in increasing effort: (a) prompt-level hard rules + post-run DB-diff audit (detective); (b) run Tier-3 agents under a user/group with read-only filesystem access to first-repo, writes only via named operations (preventive); (c) accept the risk explicitly and document it. Choosing *none* is the current state and shouldn't survive the audit.
17. **Agents-manifest as single source of truth** (Area 5) feeding crontab docs, integration-test expectations, verification manifests, and tier routing; delete the four divergent copies (AGENT_TIER_DEFAULTS, legacy permissions file, template set, survey tables).
18. **Contract the reverse surface:** a new integration-contract section governing first-repo→brain writes (who may write which brain paths, with which helper, under which lock) — brain/ is a shared datastore and currently only one direction has rules; both repos should share one signals/findings write helper.
19. **Registry lifecycle ownership:** locked writes, retain completed-run history (or explicitly don't), stale-entry sweep in the immune system.

### Needs Oscar's judgment (collected)
- Tier-3 enforcement posture (16) — the single biggest open risk decision.
- Unattended auto-push of agent merges to `origin/master` (9.7).
- Commit-vs-ignore policy for generated agent outputs (13) — this audit recommends commit.
- quant-research/backtest 35-40-day dormancy: Phase 5 Gate 4 is blocked on work that was Oscar-approved May 25 and never executed (per integration-test 07-05) — strategic, not technical.
- research-scout cadence (2×/day?) and whether its 3 fixed topics reflect current priorities.
- Wallet-address rule scoping in CLAUDE.md.
- Whether orchestrator respawn should exist at all, or be deleted honestly (4).

---

*Audit complete 2026-07-10. Read-only; no code touched. Companion to the Stage-1 structural survey (same date). Items here that duplicate O-ledger entries are cross-referenced rather than re-numbered; new swarm-side findings above are candidates for O-31+ at Oscar's discretion.*
