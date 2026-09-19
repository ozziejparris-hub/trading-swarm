# Scoping Local Tier-2.5 Supervisory Agents — 2026-09-19

**Type:** Read-only design assessment. No implementation, no agent enabled, no config
changed, no model downloaded, nothing written to a production table, no service touched.
**Standing instruction:** claims tagged `[V]` verified this session against the live repo
or a live measurement; `[I]` inferred/estimated; `[G]` taken as given from the task brief
(not independently re-derived).
**Scope note:** ranks nothing, recommends nothing. This is material for Oscar to choose
from, not a proposal.

---

## PART 1 — What agent infrastructure actually exists

### Tier definitions: where, and current vs. stale

Three places define "tier" in this repo, and they disagree with each other:

1. **`CLAUDE.md`** (trading-swarm root) — architecture diagram + "Model Routing (Current)"
   table. States Tier 2.5 = **Claude Haiku 4.5**, assigned to `integration-test,
   research-scout`. Last touched `f6dc86f`, 2026-06-11. `[V]`
2. **`brain/model-routing.md`** — the file the repo itself calls "the authoritative
   source of truth" (its own header: "governs `spawn_agent.sh` and
   `AGENT_TIER_DEFAULTS`... they must stay in sync"). States Tier 2.5 =
   **Qwen3-Coder 30B-A3B (Ollama, local)**, changed 2026-05-13 specifically *because*
   Haiku/Ollama-stdin couldn't execute tools for signal-agent. `integration-test` is
   listed as **Tier 3**, promoted 2026-05-14 after the local model at Tier 2.5
   "produced 10 fabricated CRITICAL failures." Header self-reports
   "Last updated: 2026-05-13" but contains dated entries through 2026-05-14. `[V]`
3. **`orchestrator/orchestrator.py`** — `AGENT_TIER_DEFAULTS` dict (line 293), which
   comments itself as "the executable version of that document" (model-routing.md).
   Matches model-routing.md, not CLAUDE.md: `integration-test: 3`, no Haiku anywhere,
   `research-scout-agent: 2.5` with Qwen3-Coder. `[V]`
4. **`docs/TIER_COLLABORATION.md`** — a fourth document, dated implicitly by content
   (references `ollama_agent_loop.py`, ~May 2026 era). Also states Tier 2.5 =
   Qwen3-Coder 30B-A3B, and adds detail absent everywhere else: a
   `run_sql` / `run_sql_write` / `write_handoff` tool surface for Tier 2.5, an
   allowlist of writable columns, and a "Tier 2.5 does data, Tier 3 does reasoning"
   handoff-file pattern (`brain/agent-outputs/handoffs/<task_id>.json`). `[V]`

**Verdict: the definition is establishable, and it is stale in exactly one place —
`CLAUDE.md`, which has been wrong about Tier 2.5's model since before its own last
edit** (the Haiku→Qwen3-Coder swap was 2026-05-13; CLAUDE.md was last edited
2026-06-11 and never corrected it — over 4 months stale as of today). The
orchestrator's live dict and model-routing.md agree with each other and are current.
`[V]`

Working definition used for the rest of this document (orchestrator + model-routing.md,
the two that agree and the one the orchestrator actually executes):

| Tier | Model | Execution mode |
|---|---|---|
| 1 | Gemma 4 E2B (Ollama, local) | text-only, stdin |
| 2 | Gemma 4 E4B (Ollama, local) | text-only, stdin |
| 2.5 | Qwen3-Coder 30B-A3B Q4_K_M (Ollama, local) | text-only by default; a tool-calling variant exists (`ollama_agent_loop.py` / ci `run_sql`/`write_file`/etc.) but is documented as usable only when context stays under ~15-20K tokens |
| 3 | Claude Sonnet 4.6 (cloud) | full tool use via Claude CLI |
| 4 | Claude Opus 4.7 (cloud) | escalation only, 3× Sonnet failure gate |

Nothing in the repo defines a distinct "Tier 3" vs "Tier 2.5" *capability* boundary
beyond this — the promotions on record (code-hygiene, training-librarian,
integration-test, all 2026-05-14) all moved *up* from a local tier to Sonnet after the
local model **fabricated findings/CRITICAL alerts when asked to render a verdict**, not
after a capacity or speed problem. This is the concrete, repo-native precedent for
research corner #2 (generate-the-check-not-the-verdict) — it already happened here,
independently, before that framing existed. `[V]`

### Every agent template: what, when written, when it last ran, still running?

15 files in `orchestrator/task_templates/`. Cross-referenced against crontab, per-agent
log tails, and `brain/agent-outputs/` mtimes:

| Template | Tier (current) | Cron? | Last real run (evidence) | Status now |
|---|---|---|---|---|
| `orchestrator-system.md` | 3 | systemd, 600s loop | continuous, `logs/orchestrator.log` cycling every 10 min as of 10:17 UTC today | **LIVE** — but its own loop invokes no LLM (see below) |
| `research-scout-agent.md` | 2.5 | `#0 8,20 * * *` | pre-2026-07-15 | **PAUSED** 2026-07-15 (`138c03b`'s predecessor commit `2026-07-15-tier3-pause-token-bleed.md`) — dedup bug, 20% zero-output runs |
| `integration-test-agent.md` | 3 | `#0 23 * * 0` | pre-2026-07-15 | **PAUSED** 2026-07-15 — CI failed 10 consecutive Sundays, re-diagnosing known-unfixed issues at full Sonnet cost |
| `code-hygiene-agent.md` | 3 | `#0 20 * * 5` | `logs/code_hygiene.log`: 2026-08-28T20:00 exit 0 `[V]` | **PAUSED** 2026-08-31 (`138c03b`) — credit shutdown |
| `training-librarian-agent.md` | 3 | `#0 9 * * 6` | `logs/training_librarian.log`: 2026-08-29T09:00 exit 0 `[V]` | **PAUSED** 2026-08-31 |
| `performance-analyst-agent.md` | 3 | `#0 6 * * 1` | `logs/performance_analyst.log`: 2026-08-31T06:00 exit 0 `[V]` | **PAUSED** 2026-08-31 (ran once more that same morning, paused later that day) |
| `signal-agent.md` | 3 | `#0 8 * * 1` | `logs/signal_agent.log`: 2026-08-31T08:00 exit 0 `[V]` | **PAUSED** 2026-08-31 |
| `trader-intelligence-agent.md` | undocumented (runs as literal `3`, no routing-table entry — flagged as drift in `138c03b`'s own ledger) | `#15 7 * * 1` | `logs/trader_intelligence.log`: 2026-08-31T07:15 exit 0 `[V]` | **PAUSED** 2026-08-31 |
| `feedback-loop-agent.md` | N/A — pure Python, "agent" is a misnomer per `138c03b`'s own ledger, zero `claude`/`anthropic`/`ollama` references `[V]` | `0 7 * * 1` | `logs/feedback_loop.log`: **2026-09-14T07:00 exit 0**, 5 new findings, report written `[V]` | **LIVE**, weekly, no LLM |
| `market-builder.md`, `quant-research.md`, `market-intelligence-agent.md`, `backtest-agent.md` | 3 | none — not in crontab at all | on-demand only; `brain/agent-outputs/quant-research/` top-level file dated 2026-05-19, subdirectories (GEO-ELO-001, RQ1.1, RQ2.2, RQ3.2, LH-001) have later dates but read as manual/interactive-session output, not autonomous cron runs `[I]` | **NEVER CRON-SCHEDULED** — spawned manually only |
| `niche-app-agent.md` | — | none | one file, 2026-04-21 | effectively abandoned |
| `research.md` | — | none | one file | effectively abandoned |

Non-template, non-LLM cron jobs also live and unaffected by any of the above:
`run_database_backup.sh` (03:00 daily), `backup_offsite.sh` (02:00 daily),
`run_changelog_monitor.sh` (07:30 Mon — pure urllib+Telegram, no LLM `[V]`),
`legendary_positions_scan.py` (07:30 Mon — pure sqlite3+urllib `[V]`, ran 2026-09-14),
`weekly_resolution_sweep.sh` (03:30 Sun), and `run_daily_maintenance.sh` (06:00 daily,
first-repo script, the one LLM call inside it is `backfill_market_categories.py`, see
Ollama section below).

Current live crontab confirmed byte-for-byte against `138c03b`'s stated diff: 7
non-Claude jobs uncommented, 7 Claude-backed jobs (5 from `138c03b` + research-scout ×2
+ integration-test from `2026-07-15`) commented out with intact reversal instructions.
`[V]`

### The five Tier-3 agents paused 2026-08-31 (`138c03b`)

Commit `138c03b176eedcdc28498c3aaedb18dc21b8df61`, "docs: disable 5 Claude-backed
Tier-3 swarm agents (crontab pause)," documented in
`brain/decisions/2026-08-31-tier3-credit-shutdown.md`. Confirmed by direct commit
inspection `[V]`:

| Agent | Original schedule | Recorded reason |
|---|---|---|
| code-hygiene-agent | Fri 20:00 UTC | Cost control — each run was one Claude Sonnet session against Oscar's personal OAuth subscription quota, not a metered bill |
| training-librarian-agent | Sat 09:00 UTC | same |
| performance-analyst-agent | Mon 06:00 UTC | same |
| signal-agent | Mon 08:00 UTC | same |
| trader-intelligence-agent | Mon 07:15 UTC | same |

**Re-enable procedure** (from the ledger, not paraphrased): `crontab -e`, delete the
leading `#` from the *one* chosen agent's cron line only — do not bulk-uncomment;
schedules are preserved verbatim in the comment so nothing needs reconstructing.
Full-crontab rollback file also exists at
`logs/crontab.backup.2026-08-31T123016Z.txt` (sha256 recorded in the ledger),
gitignored so it lives on disk only. The ledger explicitly warns: before reactivating
any of these, note the `spawn_agent.sh` session-limit bug (a run that hits Claude's
session limit exits clean, gets marked `"completed"` in the registry, and produces
silent zero output with no alert) — unfixed as of the ledger and not independently
re-checked this session.

### The orchestrator: dispatch, model assumptions, live?

**Live**, confirmed by direct process inspection this session: `trading-swarm.service`
active since 2026-09-12T13:07:25 UTC (the last reboot), `orchestrator.log` cycling
every 600s as designed, most recent cycle at 10:17 UTC today, "Immune system: all
agents healthy," "No pending signals." `[V]` **This directly contradicts CLAUDE.md's
own warning** ("`trading-swarm` systemd service has NOT been started yet... Do not
`systemctl start trading-swarm` without Oscar's explicit instruction") — that warning
is stale; the service has been running continuously since at least 2026-08-31 (per
`138c03b`'s own verification) and is running now. `[V]`

Dispatch mechanism: `orchestrator.py`'s `run_immune_system()` checks tmux session
liveness for anything in `agent_registry.json`'s `active_tasks`, and on a dead session
either auto-respawns (increments retry count, sends a Telegram warning) or, after
`MAX_RETRIES=3`, marks the task failed and alerts Oscar. **The auto-respawn branch
only calls `update_task()` and `send_telegram()` — it never calls `spawn_agent.sh` or
`claude`.** Confirmed by reading the function body (`orchestrator.py:552-562`); this
matches `138c03b`'s own claim verbatim. `[V]` `agent_registry.json`'s only entry is one
stale `"failed"` task from 2026-06-04 — nothing has been actively dispatched through
this mechanism in the period covered by available logs. `[V]`

Model availability assumption: `select_tier()` reads `AGENT_TIER_DEFAULTS`, which
assumes Ollama is reachable at `localhost:11434` for tiers 1/2/2.5 and the Claude CLI
is authenticated (OAuth, not `ANTHROPIC_API_KEY` — explicitly unset per
`spawn_agent.sh`) for tiers 3/4. The orchestrator's own loop does not itself call any
model — its 600s cycle is pure Python (tmux checks, JSON file reads, Telegram POSTs);
CPU cost was measured at "1.3s over 4 days" in `138c03b`'s own audit. `[V]`

### `brain/agent-outputs/`: what accumulated, from what, read by what

Largest subdirectories by file count: `pre-resolution/` (99 files), `data-audit/`
(81 files), `str002-scoring/` (73 files), `feedback-loop/` (23 files),
`performance-analyst/` (16 files), `training-librarian/` (15 files),
`code-hygiene/` (15 files), `signal-agent/` (17 files). `[V]`

**Correction to the task's own framing**: the three highest-volume directories
(`pre-resolution`, `data-audit`, `str002-scoring` — 253 files combined, roughly daily
cadence since 2026-08-29 through today for `data-audit`, longer for the others) are
**not written by any trading-swarm "agent" at all**. They are written by four
deterministic first-repo scripts — `scripts/audit_invariants.py` →
`data-audit`, `scripts/pre_resolution_intelligence.py` → `pre-resolution`,
`scripts/score_str002_signals.py` / `register_str002_signals.py` → `str002-scoring` —
none of which contain an LLM call. `[V]` (grep for the exact output paths in both
repos; zero matches in trading-swarm, four matches in first-repo). They land in a
directory named `agent-outputs` by filing convention, not because an agent produced
them.

**Whether anything ever reads them back: no.** `[V]` Grepped both repos for
programmatic reads (`glob`/`listdir`/`open`/`json.load`) against
`agent-outputs/data-audit`, `agent-outputs/pre-resolution`,
`agent-outputs/str002-scoring` — zero hits anywhere except the writers themselves.
Every other match is a *prose reference* inside other Markdown files (session
summaries, `brain/decisions/*`, `brain/lessons-learned.md`) — a human or an
interactive Claude Code session citing a path, not code consuming it. This is a clean,
verified instance of the "written-never-read" shape named in the task's Part 3 list —
253 files, roughly a month-plus of daily accumulation, zero programmatic consumers.

The genuinely Claude-generated outputs (`code-hygiene/`, `training-librarian/`,
`performance-analyst/`, `signal-agent/`, `trader-intelligence/`, all now paused) are
"human-facing reports... `brain/` consumers read whatever is present and degrade
gracefully when absent" per `138c03b`'s own ledger — but that specific claim is
tagged `[I]` (inferred) in the source document itself, not verified there either.
Not independently re-verified this session (see "what was not determined").

### Ollama integration that already exists

**`scripts/backfill_market_categories.py` (first-repo)** — the one confirmed
production Ollama consumer. `[V]`, read directly:

- Endpoint: `http://localhost:11434/api/generate` (single-shot completion API, not
  the chat/tool-calling API)
- Model: `qwen3-coder:30b-a3b-q4_K_M`, `temperature: 0.1`, `stream: false`
- Batch: 20 market titles per call (`DEFAULT_BATCH_SIZE=20`), numbered-list prompt,
  strict JSON-array-only output contract, markdown-fence stripping, `json.loads` with
  a hard failure path (`return None`) on malformed output — no retry-until-parses loop
- Timeout: 120s per call; `SLEEP_BETWEEN_BATCHES = 0.5`s between calls
- Called from `daily_maintenance.py` step "Backfill market categories" with
  `--limit 50` per day
- **Measured throughput, live today**: 2026-09-19 run, 09:47:25→09:48:51 UTC = **86
  seconds** for a 50-market batch (3 Ollama calls at batch size 20), cumulative
  `classified` counter 12382→12413 (+31), `skipped` 8482→8511 (+29). 2026-09-18 run:
  76 seconds for the same shape. `[V]` (both from `logs/daily_maintenance.log`,
  timestamps read directly)
- No other consumer of this specific model/endpoint pattern was found in either repo. `[V]`

**`orchestrator/ollama_agent_loop.py` (trading-swarm)** exists and implements the
tool-calling variant documented in `docs/TIER_COLLABORATION.md` (`read_file`,
`write_file`, `run_sql`, `run_sql_write`, `run_shell`, `append_to_json_array`,
`send_telegram`, `write_handoff`) — but its only assigned consumer,
`research-scout-agent`, has been paused since 2026-07-15, so **this tool-calling
wrapper currently has zero live callers.** `[V]` (cron confirms research-scout still
commented out; no other agent template routes to Tier 2.5 in `AGENT_TIER_DEFAULTS`).

**`brain/decisions/2026-05-13-ollama-tool-calling-debt.md`** is a pre-existing,
repo-native statement of research corner #1/#2's conclusion, written four months
before this task and independently: Ollama-via-stdin cannot execute tools; the
two architectures considered were (A) a full Ollama-native tool-calling loop, or
(B) "Python wrapper handles all I/O directly... only calls Ollama for the
reasoning/classification step." The doc's own recommendation: **"Option B is simpler
and more reliable for well-defined tasks."** `backfill_market_categories.py` is
Option B, already built, already in production. `ollama_agent_loop.py` is Option A,
built, wired to exactly one now-paused agent.

**Model inventory on the box** (`ollama list`, live): `qwen3-coder:30b-a3b-q4_K_M`
(18GB), `gemma4:e4b` (9.6GB), `gemma4:e2b` (7.2GB), `mistral:latest` (4.4GB). `[V]`
No model was loaded in memory at check time (`ollama ps` empty). `[V]`

### Dormant LLM implementations named in CLAUDE.md (first-repo)

Both confirmed to exist only in first-repo (grep for `ai_analyzer.py` and
`pydantic_ai` in trading-swarm: zero matches). `[V]`

- **`monitoring/ai_analyzer.py`'s `AIAnalyzer`/`OllamaClient`**: 444 lines, wraps
  `mistral:latest` via a small HTTP client with response caching. Zero callers
  anywhere in the codebase — `AIAnalyzer` appears in no file except its own. `[V]`
  Last touched 2025-12-17 (single commit, "AI added to health checker") — over 9
  months stale relative to today. Never wired into `system_observer.py`.
- **`monitoring/main.py`'s Pydantic-AI agent**: uses `pydantic_ai.Agent`, checks for a
  running Ollama server, defaults to `mistral`. `main.py` itself is not the live
  monitoring entrypoint (`main_telegram_safe.py` is, per `scripts/start_monitoring.py`'s
  actual import — established in an earlier session, not re-derived here). The
  apparent references to `monitoring.main` in `system_observer.py`,
  `health_checker.py`, and `scripts/verify_system_observer.py` were checked directly
  this session and are **string-literal process-name matches** ("is a process named
  `monitoring.main` currently running?"), not Python imports of the module's code. `[V]`
  Confirmed dead: no code path executes it.

**Salvageable or superseded?** Neither is superseded — nothing else in the codebase
does AI-powered health analysis today. Both are salvageable in the narrow sense that
the code compiles against a still-installed model (`mistral:latest`) and the pattern
(wrap Ollama, cache, call from a health check) is sound — but both predate the
research-corner conclusions this task treats as given (neither is stateless-invocation
designed, neither generates a checking function, both were built to answer "is this
healthy?" directly via a model call, i.e. exactly the LLM-as-verdict pattern the
repo's own `138c03b`/model-routing.md history shows failing at Tier 2.5). Reviving
either as-is would reproduce the failure mode already recorded for code-hygiene and
integration-test. Neither has been run or imported since its last commit, so neither
is validated against the current DB schema or `system_observer.py`'s current
interfaces.

---

## PART 2 — Runtime capacity, honestly

**Live measurement, 2026-09-19 ~10:24 UTC** `[V]`:

- **CPU**: AMD Ryzen 9 8945HS, 8 physical cores / 16 threads (SMT2). `nproc` = 16.
- **RAM**: 86Gi total, 2.5Gi used, 35Gi free, 49Gi buff/cache, **83Gi "available"**
  (i.e. reclaimable-from-cache-inclusive headroom). Swap: 8Gi total, 40Mi used
  (effectively unused).
- **Load average** at check time: 1.71 / 1.37 / 1.30 — well under the 16-thread
  ceiling even with `polymarket-monitoring` (measured 86.7% of one core, sustained,
  per `ps`) and `polymarket-observer` (~6% of one core) both running continuously.
- **GPU**: the task brief frames the box as CPU-only. Repo evidence says
  otherwise for a narrow slice: `/etc/systemd/system/ollama.service.d/rocm.conf` sets
  `OLLAMA_VULKAN=1` + `OLLAMA_FLASH_ATTENTION=1`, and `lspci` confirms an AMD
  Radeon 780M (HawkPoint) iGPU is present and this is the active backend for
  Ollama (`systemctl show ollama` confirms the env vars are live in the running
  service). `[V]` — **this is a correction, not a contradiction of the brief's
  substance**: the iGPU has only a 4GB UMA VRAM allocation (per
  `model-routing.md`'s GPU section, upgradeable to 8G via BIOS, not yet done), so
  only Tier 1/2 (Gemma E2B fully resident, E4B partially) benefit meaningfully from
  it. The 30B Qwen3-Coder model (19GB) cannot be VRAM-resident at 4G and runs
  CPU-bound in practice, which is consistent with the brief's "inference speed is the
  constraint" framing for anything above Tier 2. Net effect: capacity is confirmed
  not the constraint (RAM headroom is enormous); inference speed for anything Tier
  2.5+ is still CPU-bound as the brief assumes.

### When the box is busy vs. idle across 24h (UTC, from crontab + measured log durations)

| Window | What | Duration (measured) | CPU character |
|---|---|---|---|
| 02:00 | `backup_offsite.sh` | short (log shows single-minute completion, e.g. 02:09:04→02:09:05 today) | brief I/O burst |
| 03:00 | `run_database_backup.sh` | short (03:08:05→03:08:06 today, 22G DB copy — I/O bound, ~1 min logged but underlying `cp`/rsync of a 22GB file will run longer in the background than the log-visible completion suggests) `[I]` | I/O heavy |
| **03:00–~06:00 Sundays only** | `polymarket-sunday-elo.timer` → full 6-dimension ELO recalc | **123.7–172.8 min, trending upward** week over week (123.7 on 08/09, 132.8 on 08/16, 145.1 on 08/23, 144.0 on 08/30, 172.8 on 09/13 — growing with trader-count growth) `[V]`, direct from `logs/sunday_elo.log` | CPU + DB-write heavy, the single longest contention window in the week |
| **06:00–~10:15–10:25 daily** | `run_daily_maintenance.sh` (first-repo `daily_maintenance.py`, 28 steps) | **4h13–4h25 historically** (08/16: 4:13, 08/17: 4:20, 08/18: 4:19; today 09/19 still running as of last check at 4h24 elapsed, longer-tailed than the 3 prior days) `[V]` — includes the `backfill_market_categories.py` Ollama call (~80s of the 4+ hours) and a `pool_c` trader backfill against the Polymarket API (thousands of sequential HTTP calls, the actual bulk of the runtime) | **The daily contention window** — CPU + heavy sequential network I/O + DB writes, every day, 4+ hours |
| Mon 07:00 | `run_feedback_loop.sh` | brief (log shows single-run completion within the hour) | pure Python, SQLite + urllib, light |
| Mon 07:15 | `trader-intelligence-agent` cron line — **paused**, no longer fires | n/a | n/a |
| Mon 07:30 | `legendary_positions_scan.py` + `run_changelog_monitor.sh` | brief | light, no LLM |
| Sun 03:30 | `weekly_resolution_sweep.sh` | not measured this session | unknown, likely light per prior characterization |
| **Continuous, 24/7** | `polymarket-monitoring.service` | n/a | **sustained ~87% of one core** for the life of the process (measured across a 16.5h window in this session's earlier check), plus periodic 15-19 min heavier bodies every 10th cycle (~every 2.5h) |
| **Continuous, 24/7** | `polymarket-observer.service` | n/a | ~6% of one core, light, but is the process with the documented SQLite-contention/SIGTERM-hang history `[G]` (asserted in the task brief; corroborating decision docs exist — `brain/decisions/2026-09-13-observer-burst-loop-and-memory-diagnosis.md` and others in first-repo cover observer instability, but the specific SIGTERM/blocking-SQLite claim was not re-traced to a specific line this session — treat as given per the brief, not independently re-verified) |
| **Continuous, 10-min cycle** | `trading-swarm.service` orchestrator | n/a | negligible (1.3s CPU over 4 days per `138c03b`'s own measurement) |

**Named safe windows** (no scheduled heavy job contending, based on the above):

- **Any day, ~10:30–02:00 UTC** (i.e., after daily_maintenance finishes and before the
  02:00 backup_offsite starts) is the single largest clear window — roughly 15+ hours
  — with only the two always-on services (`polymarket-monitoring` at ~87% of one
  core, `polymarket-observer` at ~6%) as background load. Given 16 threads and a
  measured load average of ~1.3–1.7, this leaves the large majority of the box
  genuinely idle.
- **Any night 02:00–06:00 UTC except Sundays** is also clear (backups are brief;
  daily_maintenance hasn't started yet).
- **NOT safe: 06:00–~10:25 UTC, every day** — daily_maintenance is CPU- and
  network-I/O-heavy for 4+ hours and its tail length is not perfectly consistent
  (today ran longer than the prior three days). A supervisory job scheduled inside
  this window risks exactly the resource contention the brief warns about — this
  window should be treated as occupied, not just "probably fine."
  - **Full box CPU headroom is genuinely large even during this window** on paper
    (16 threads, one process using <1 core) — the risk here is less about raw CPU
    availability and more about **the two named failure modes being real and already
    observed on this box** (runaway-process unresponsiveness; observer SIGTERM hangs
    tracing to SQLite contention). A new CPU-bound Ollama inference process running
    concurrently with `daily_maintenance.py`'s own heavy DB writes multiplies the
    surface for exactly that kind of contention, even if headroom numbers look fine
    in isolation.
- **NOT safe: 03:00–~06:00 UTC on Sundays** — the ELO recalc window, and the longest
  single contention window in the week, growing over time.

### Existing Ollama classifier's resource footprint when running

The only local-inference data point that exists in production
(`backfill_market_categories.py`) was not instrumented for CPU/RAM during its run this
session (it had already completed by the time this investigation started — 09:48:51
UTC finish, checked at 10:24). What is known: 3 sequential calls of 20-title batches
to a resident-in-RAM 18GB Q4 model, ~25–29s per call, total wall time 76–86s for the
daily 50-market batch, run serially inside `daily_maintenance.py`'s own process (not
concurrent with anything else it does) with a 120s per-call timeout and 0.5s
inter-batch sleep. No OOM, no timeout, no error logged on either of the two observed
runs (08/18, 09/19). This is 76-86 seconds of the 4+ hour daily_maintenance window —
proportionally negligible contribution to that window's total duration, though it
does run serially inside the busy window rather than the safe one, since
`daily_maintenance.py` calls it as one of its 28 sequential steps.

---

## PART 3 — Candidate supervisory roles

Following the task's list; **rejecting any that don't earn a place**, per its own
instruction.

### 1. Freshness supervisor

- **Question it answers**: "Does any of a fixed, enumerated set of claim-bearing
  artifacts (CLAUDE.md's specific factual claims, `brain/model-routing.md`'s tier
  table vs. `AGENT_TIER_DEFAULTS`, `brain/strategy-registry.md`'s per-strategy
  status) currently disagree with a live, checkable ground truth?" — checkable,
  because each claim in scope has to be paired at authoring time with a concrete
  check (a file mtime, a grep, a systemctl query, a dict comparison), not a
  free-form "is this doc still accurate" judgment.
- **Needs an LLM?** For the mechanical half — no. "Does CLAUDE.md's Tier 2.5 model
  string match `AGENT_TIER_DEFAULTS`'s"; "is `trading-swarm.service` active"; "when
  was this file last modified vs. the event it claims" — these are all deterministic
  string/dict/systemctl comparisons, exactly what this session did by hand to find
  the two stale claims documented in Part 1. **An LLM is only justifiable for the
  half that's inherently fuzzy**: does a piece of *prose* (not a structured value)
  still match reality — e.g. "the strategy-registry went stale for three months
  unnoticed" implies free-text status descriptions, not just enum fields. Per research
  corner #2, even that fuzzy half should not be "ask a model to verdict this
  paragraph" — it should be "write a checking function (e.g., extract every
  `component: claim` pair the doc makes in a fixed format, then check each
  mechanically)," with the LLM's one-time role being to help write or update that
  extraction, not to run it repeatedly.
- **Model class / CPU-only viability**: the mechanical comparisons need no model at
  all. Where an LLM is used (authoring/updating the extraction function, or scoring
  ambiguous prose matches offline), Tier 2.5 (Qwen3-Coder, ~25-29s/call at the
  observed batch shape) is viable for a low-frequency, non-interactive job; this is
  squarely the corpus-reader/batch-classification shape the existing Ollama consumer
  already proves out.
- **Schedule / window**: nightly or weekly, not more — freshness doesn't change fast.
  Use the **10:30–02:00 daily window** or any non-Sunday 02:00–06:00 window.
- **Output**: a structured findings file (one row per claim checked: claim, expected,
  actual, match/mismatch), written once per run to a fixed path — **not** prose.
  Consumer: see Part 5.
- **Failure mode**: silent non-run (cron didn't fire, or crashed before writing) looks
  identical to "nothing stale found" unless the output file's own mtime is itself
  checked by something — i.e., this supervisor needs the same kind of freshness check
  applied to *its own* output that it applies to everything else, or its absence is
  invisible. Noted explicitly because this is exactly how `brain/agent-outputs/`
  became unread in Part 1 — nothing was watching for the watcher going quiet.

### 2. Provenance supervisor

- **Question it answers**: "Does every numeric or dated claim in a newly-written
  decision document cite a committed, hashable artifact — a script path, a SQL query
  this session actually ran, a file this session actually read — rather than
  appearing without a traceable source?"
- **Needs an LLM?** The *extraction* step (find every number/date/claim in a Markdown
  document and pair it with its nearest citation, if any) is closer to structured
  parsing than judgment — a deterministic Markdown/regex pass could plausibly get
  most of the way (numbers near a code-fence, a `[V]`/`[I]` tag, a file path, or a
  command output block count as cited; a bare number in prose with none of those
  nearby doesn't). Where this tips into needing an LLM is judging whether a *cited*
  source actually supports the *specific* claim made about it — that's closer to
  judgment than extraction, and per research corner #2 should not be "ask a model:
  is this number supported?" on every future document, but rather "have a model
  generate a checking function once (parse citation markers, verify the cited
  path/command exists and was run) and run that deterministically forever."
- **Model class / viability**: same shape as above — deterministic pass first, model
  used once (offline, in the "generate the check" sense) to help build the extraction
  pattern, not invoked per-document afterward if the deterministic pass suffices.
- **Schedule**: event-triggered in principle (on new-file-in-`brain/decisions/`), but
  given no such trigger exists, nightly batch scan of files modified since last run
  is the realistic shape. Same safe window as above.
- **Output**: per-document pass/fail list of unsupported claims. Consumer: see Part 5.
- **Failure mode**: false negatives (a citation exists but is wrong/stale) are the
  real risk and are NOT caught by this design — it checks "is there a citation,"
  not "is the citation still true" (that's the freshness supervisor's job on a
  longer cycle). Noted so this isn't oversold: it stops the *shape* of the four
  unreproducible-number incidents (a number entering the record with zero traceable
  source), not every way a number can be wrong.

### 3. Disconnection supervisor

- **Question it answers**: for a fixed enumerable set of {writer, reader} pairs
  across the codebase, "is this pair still connected?" — decomposed per the task's
  four named shapes: written-never-read, read-never-written, built-caller-lost,
  guard-that-cannot-fire.
- **Needs an LLM? No — this is the strongest "should not use a model" candidate in
  the whole list.** Every one of these four shapes reduces to static analysis this
  session performed manually in Part 1 and got clean, unambiguous answers from:
  - written-never-read: grep every writer of a path (`open(..., 'w')`,
    `Path(...).write_text`, a script's declared `OUTPUT_DIR`) against every reader
    (`open(..., 'r')`, `glob`, `listdir`, `json.load`) of the same path across both
    repos. This session did exactly this for `data-audit`/`pre-resolution`/
    `str002-scoring` by hand with grep and got a definitive, no-LLM-needed answer:
    253 files, zero readers.
  - built-caller-lost (e.g. `AIAnalyzer`, the Pydantic-AI agent in `main.py`): AST-level
    "is this class/function imported anywhere outside its own file" — this session
    did this by hand with grep for both and got clean answers.
  - guard-that-cannot-fire: harder (requires reasoning about *reachability*, not just
    reference existence — e.g. a check gated behind a condition that's always false),
    genuinely closer to needing either careful static analysis (a real AST/CFG tool,
    not grep) or a one-time model-assisted read to spot the shape, then a
    deterministic check thereafter, consistent with the "generate the check" pattern.
- **Model class / viability**: none needed for 3 of 4 shapes. For guard-that-cannot-fire,
  a one-time Tier 3 pass to help write the detector, then deterministic re-runs — same
  pattern as everywhere else in this document.
- **Schedule**: this is cheap enough (AST parse + import graph) to run on every commit
  or nightly; no reason to wait for a "safe window" at all for the no-LLM shapes.
- **Output**: a list of {writer, reader, status} triples, refreshed each run.
  Consumer: see Part 5.
- **Failure mode**: false positives from dynamic imports/reflection (code that reads
  a path from a config value rather than a literal string) will not be caught by a
  literal-path grep; this session's own Part 1 findings are only as good as that
  same limitation (a script reading `OUTPUT_DIR` from an env var instead of a
  hardcoded path would have been invisible to the greps performed here). Worth
  stating plainly since this document's own Part 1 evidence has this exact caveat.

### 4. Trace supervisor

- **Question it answers**: for a given agent invocation transcript, did it (a)
  decompose the task reasonably, (b) select an appropriate tool, (c) extract correct
  parameters for that tool, (d) self-correct after a tool error — the four
  production-standard targets named in the brief.
- **Needs an LLM? Yes, unavoidably** — this is genuine judgment about reasoning
  quality, not a structured-data check. This is also the one candidate that sits
  closest to "LLM-as-judge," which research corner #4 says is *not* the primary gate
  in production — it's for **selective, offline, high-volume evaluation**, with
  deterministic checks and human review as the actual gate.
- **Is there a live population to judge?** This is the load-bearing question, and
  Part 1's finding answers it negatively for now: **the only tool-calling local-agent
  path (`ollama_agent_loop.py`) has zero live callers** (research-scout paused since
  2026-07-15), and the Claude-CLI-backed Tier 3 agents that *do* produce traces are
  paused too (5 of them, since 2026-08-31). There is essentially no fresh transcript
  volume being generated right now for this supervisor to score. It would have a
  real job the moment any Tier 2.5/3 agent is reactivated, but scoped against the
  repo as it stands today, this candidate has no current input.
- **Model class / viability**: would need Tier 3-class judgment (Sonnet) to be
  trustworthy for (a)-(d) given the repo's own documented experience that local
  models fabricate verdicts under exactly this kind of "was this good?" framing
  (code-hygiene, integration-test, both promoted off local tiers for this reason).
  Running Sonnet offline, in a batch, well after the fact, on stored transcripts is
  consistent with corner #4's "selective offline evaluation" framing and does not
  need to be CPU-only/local at all.
- **Schedule**: offline batch, whenever transcript volume justifies it — moot until
  something is reactivated.
- **Output/consumer**: would feed a scored-transcript table, presumably consumed by
  whoever decides whether to keep a reactivated agent running — not designed further
  here since there's no current population.
- **Failure mode**: n/a while dormant; the risk when live is the judge itself
  fabricating or rubber-stamping scores, which is exactly why corner #4 keeps it
  offline/selective rather than gating.

### 5. Corpus reader (~190 unread decision documents)

- **Question it answers**: for each of a fixed, enumerable set of decision documents,
  extract a fixed-schema summary (date, subject, verdict/status, key numbers, the
  claims it makes) so ~190 documents become a queryable index instead of unread prose.
- **Needs an LLM?** Yes, for the extraction itself (unstructured Markdown to
  structured schema is genuinely a language task), but the task is bounded,
  parallelizable, and independently verifiable per-document — the split-and-merge
  shape the brief names, and the shape research corner #1 says is the good fit for
  stateless invocation (each document's extraction doesn't depend on any other
  document, so a failure on document #47 is traceable and doesn't poison #48).
- **Model class / viability**: Tier 2.5 (Qwen3-Coder) is plausible for a
  fixed-schema JSON-extraction task at this volume — it's the same shape as
  `backfill_market_categories.py`'s proven pattern (numbered batch in, strict JSON
  out, hard-fail on parse error, no free-form reasoning required). At the observed
  throughput (~25-29s per 20-item batch), ~190 documents in batches of, say, 10
  (documents are much longer than market titles) would run in well under an hour —
  trivially fits in any of the named safe windows and does not need to run daily at
  all; this is a one-time or occasional-refresh job, not a recurring supervisor in
  the same sense as the others.
- **Schedule**: one-off backfill, then incremental (only new/changed documents) —
  not a recurring cadence question in the way the other four are.
- **Output**: a structured index file. Consumer: this is the one candidate where the
  consumer is obvious and immediate — future Claude Code sessions (like the one
  running Part 1 of this very task) that currently have to grep decision docs one at
  a time. A queryable index directly serves the next session doing exactly this kind
  of investigation. This is also the strongest answer to "who reads it" of all five
  candidates.
- **Failure mode**: per-document extraction failure is cheap to detect (schema
  validation fails → flag that document, move on) and does not cascade, per the
  stateless-invocation property. The index itself needs the same "is this stale"
  freshness check as everything else if new decision documents keep landing and the
  incremental-update step silently stops running.

---

## PART 4 — What should not use a model

Per the task's instruction, this section is not empty:

1. **Zero-caller / built-caller-lost detection** (e.g. is `AIAnalyzer` imported
   anywhere; is `main.py`'s Pydantic-AI agent invoked anywhere). **Deterministic
   version**: `grep -rn "AIAnalyzer\|from.*ai_analyzer"` across the repo, or a proper
   AST-based import-graph walk for cases grep would miss (aliased imports,
   `importlib`). **Why it beats an LLM**: this session got a complete, unambiguous
   answer for both named dormant implementations in under a minute with grep; an LLM
   adds latency, cost, and a non-zero hallucination risk to a question that has one
   correct, mechanically-derivable answer.

2. **Written-but-never-read detection** (e.g. does anything consume
   `brain/agent-outputs/data-audit/`). **Deterministic version**: for each known
   writer path, grep for `open`/`glob`/`listdir`/`json.load` referencing that path
   elsewhere in the codebase. **Why it beats an LLM**: this is exactly how this
   session found the 253-file written-never-read instance in Part 1 — a clean,
   binary, mechanically-verifiable fact. Judgment adds nothing here; it can only
   introduce doubt about a fact that isn't actually in doubt.

3. **Checkpoint / state-file freshness** (e.g. is `data/category_backfill_state.json`,
   `data/.audit_invariants_state.json` current, or is a cursor stuck). **Deterministic
   version**: compare a checkpoint's timestamp/cursor value against the current time
   or the underlying table's current max value; this already exists in
   `monitoring/failure_age.py`'s `age_days()` pattern (first-repo) — a direct
   subtraction, no model involved. **Why it beats an LLM**: freshness is a
   subtraction, not a judgment call.

4. **Hash / canonical-value comparison** (e.g. the `metric_v2f_oos_result` canonical
   hash check performed in this session's earlier progression-check task — a
   `sha256sum` of a `SELECT * ... ORDER BY` against a known-good value). **Deterministic
   version**: exactly what it already is — a hash comparison. **Why it beats an
   LLM**: a hash mismatch is unambiguous; asking a model "does this data still look
   right" would be strictly worse (slower, costs tokens/inference time, and — per the
   repo's own documented experience — local models fabricate verdicts on exactly
   this kind of "is this correct" framing).

5. **Tier-table / config-dict consistency** (does `CLAUDE.md`'s tier table match
   `orchestrator.py`'s `AGENT_TIER_DEFAULTS` match `brain/model-routing.md`'s table —
   the specific staleness this document found in Part 1). **Deterministic version**:
   parse the three sources into comparable structures (a small, fixed regex/Markdown-table
   parse per source — brittle but bounded, since there are only three sources and
   their formats are stable) and diff them. **Why it beats an LLM**: this session
   found the exact discrepancy (CLAUDE.md still says Tier 2.5 = Haiku) by reading
   three files and comparing them directly — no ambiguity, no judgment, a table diff.

6. **Cron/systemd-vs-documentation consistency** (does the crontab's actual live
   state match what a decision document claims was paused/active — the check this
   session performed against `138c03b`'s claims). **Deterministic version**:
   `crontab -l` piped through a parser, diffed against the set of lines a decision
   document's own table claims should be commented/uncommented. **Why it beats an
   LLM**: this session verified `138c03b`'s crontab claims byte-for-byte with a plain
   read-and-compare; a model would add nothing but the possibility of misreading a
   `#`.

---

## PART 5 — The consumer problem

Per-candidate, extending Part 3's consumer notes:

| Candidate | What consumes its output | What makes absence/staleness visible |
|---|---|---|
| Freshness supervisor | Not yet named — this is the open question | See below (failure_age path) |
| Provenance supervisor | Not yet named | See below |
| Disconnection supervisor | Not yet named, but cheapest to imagine wiring since output is a simple triple-list | See below |
| Trace supervisor | Whoever decides to keep a reactivated agent running — but moot, no live population | N/A while dormant |
| Corpus reader | **Concrete and immediate**: future investigative sessions (this document is itself an example of the kind of grep-heavy work a queryable index would shortcut) | A stale index is visible the moment someone queries it for a document that was added after the index's last refresh and gets nothing back — self-evident on first use, unlike the silent-accumulation failure mode of the other four |

**The honest answer for the first three**: as scoped in Part 3, none of them has a
named consumer yet. That is instance-25 risk exactly as the task frames it, and it is
not resolved by this document — Oscar naming a consumer (a person who reads a
Telegram digest, or a mechanism that gates something) is a prerequisite for any of
these three being worth building, not a detail to fill in afterward.

### Does `failure_age.py` + `accepted_failures.json` provide a ready-made consumer path?

**Yes, and it is a strong answer for the freshness/provenance/disconnection
candidates specifically.** Confirmed live in first-repo (`monitoring/failure_age.py`,
`config/accepted_failures.json`) `[V]`:

- The register's own header states its contract precisely: "A failing check WITH a
  current (un-expired) entry here is EXPECTED. It does not alert. A failing check
  WITHOUT an entry is UNEXPECTED. It alerts. An entry PAST its `review_by` date makes
  its finding alert again."
- It is generic over *which* check produces the finding — the existing consumers
  (`canonical`, `diagnostic`, `audit_invariants`) each write to their own state file
  keyed by a `finding_keys()`-style string, and `failure_age.py`'s `reconcile()`
  handles new-vs-known diffing and age tracking uniformly across all of them.
- It already reaches Telegram (established in this session's earlier progression-check
  task, and consistent with `audit_invariants.py`'s design).
- `accepted_failures.json`'s own header is explicit that entries are added **only by
  Oscar, by hand** — no automated process may write to it. This means a new
  supervisor plugging into this path gets alerting and new-vs-known gating for free,
  but every finding it raises still routes through Oscar's manual acceptance to go
  quiet — it does not create a new autonomous-acceptance path, which is a feature,
  not a limitation, for a first deployment.

**This is the closest thing to a ready-made answer to "who reads it" that exists in
either repo.** A new supervisor (freshness, provenance, or disconnection — all three
produce the same shape of output: a list of findings, each either new or
already-known) could write its own state file in the same format and register itself
with `failure_age.py` rather than inventing a new consumer mechanism. Whether that is
the right home for these three candidates, or whether they deserve a different
channel, is Oscar's call — but the plumbing to make a finding visible without
inventing something new already exists and is exercised daily.

---

## PART 6 — Cost and runaway telemetry

Both named failure modes are real and documented, not hypothetical: Oscar exhausted
API credits mid-task 2026-09-17 `[G]`, and the box has gone unresponsive from a
runaway process `[G]` (both asserted in the task brief; the credit exhaustion is
also consistent with the entire reason `138c03b` exists — cost control was already
enough of a concern to pause five agents outright).

Per-run telemetry any local-inference agent loop would need, specified (not built):

- **Wall time**: start/end timestamp per invocation, logged before any inference
  call fires — so a hang is visible even if the process never returns.
- **CPU time**: `ps`/`/proc/<pid>/stat`-derived CPU-seconds consumed, comparable to
  the measurements this session took for `polymarket-monitoring` (86.7% of one core
  sustained) and the orchestrator (1.3s/4 days) — those two numbers already establish
  what "normal" looks like on this box for an always-on vs. a near-idle process; a
  new supervisor's own baseline should be established the same way on first real
  runs, not guessed in advance.
- **RAM (RSS) at start, peak, and end**: given the 19GB footprint of the one model
  class already benchmarked (Qwen3-Coder), a supervisor loop that leaks or fails to
  release RSS between stateless invocations (violating research corner #1's
  precondition) would be directly visible against the 83Gi "available" baseline this
  session measured — but only if RSS is actually logged per-run, not inferred from
  `free -h` after the fact.
- **Call count / batch count**: for local-Ollama-backed work, the number of
  `/api/generate` calls per run and their individual durations (the existing
  `backfill_market_categories.py` pattern already logs `classified`/`skipped`/`errors`
  counters per run — the same shape extends directly to any new local-inference
  consumer).
- **Token or call count for anything cloud-backed**: not applicable to a CPU-only
  local-Tier-2.5 design as scoped here, but flagged because the credit-exhaustion
  failure mode specifically involved a cloud model — if any candidate here were ever
  escalated to Tier 3 (Sonnet) for verification, as corner #4 allows for offline
  judging, that path needs the token/call ceiling the local path doesn't.

**Kill condition, specified**: a hard wall-clock ceiling per invocation (the existing
`OLLAMA_TIMEOUT = 120` in `backfill_market_categories.py` is the only precedent in
either repo — a per-call timeout, not a per-run one) plus a hard RSS ceiling checked
between batches (not just at start), both enforced by the calling Python process
(the pattern `backfill_market_categories.py` already uses: `urllib.request.urlopen`
with an explicit `timeout=`, and a `try`/`except` that logs and returns `None` rather
than retrying indefinitely) rather than by Ollama itself. Given `daily_maintenance.py`
already runs for 4+ hours as a matter of course, a wall-clock ceiling for a new
supervisor should be set relative to its own expected single-batch duration (e.g. a
small multiple of the ~25-29s per-call figure observed for the existing classifier),
not to daily_maintenance's multi-hour scale — a supervisor that takes hours where the
existing local-inference precedent takes seconds-to-minutes is itself a signal
something is wrong, and the kill condition should be set tight enough to catch that,
not loose enough to accommodate it.

---

## What was not determined

- **The exact SIGTERM/blocking-SQLite citation** for the observer's documented hang
  behavior — treated as given per the task brief; corroborating decision documents
  exist in first-repo (`2026-09-13-observer-burst-loop-and-memory-diagnosis.md` and
  adjacent session summaries) but the specific claim was not traced to a line number
  or a specific incident report this session.
- **Whether the genuinely-Claude-generated `brain/agent-outputs/` subdirectories**
  (code-hygiene, training-librarian, performance-analyst, signal-agent,
  trader-intelligence — all now paused) have any programmatic reader, as opposed to
  the three deterministic-script directories which were verified to have none. The
  `138c03b` ledger's claim that "brain/ consumers read whatever is present" for these
  is tagged `[I]` (inferred) in its own source document and was not independently
  re-verified this session.
- **Actual CPU/RAM footprint of `backfill_market_categories.py` while running** —
  the only production Ollama consumer had already finished its daily run by the time
  this investigation started; wall-time (76-86s) is verified from logs, but live
  process-level CPU/RSS during a run was not captured this session.
- **Underlying I/O duration of `run_database_backup.sh`** — the log line shows a
  1-minute completion for a stated 22GB backup file, which likely understates the
  actual I/O window; not independently timed.
- **`weekly_resolution_sweep.sh`'s duration** (Sun 03:30) — not measured this session,
  so its overlap with the 03:00 Sunday ELO recalc window is unquantified.
- **Whether the 4h13–4h25 historical daily_maintenance runtime is itself stable
  going forward** — today's run (09-19) had a noticeably longer tail than the three
  prior days at the time this investigation began, and its exact finish time was not
  confirmed before this document was written (see cross-reference: the same session's
  earlier progression-check task flagged this same run as still in progress with an
  unexplained ~30-minute stall near its end).
- **No stop condition was triggered**: Part 2 found real safe windows (the
  ~15-hour 10:30–02:00 daily window, and non-Sunday 02:00–06:00), so the "no safe
  window" stop condition does not apply. The tier-definition stop condition also does
  not apply — the definition was establishable, with one document (CLAUDE.md) found
  stale against two others that agree.
