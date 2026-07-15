# Tier-3 Token-Bleed Pause — 2026-07-15

**Type:** Cost-control decision (crontab change), reversible.
**Decided by:** Oscar, acting on the same-day Tier-3 token audit (this session).
**Principle applied:** make the swarm work-as-intended before running autonomous automation
on top of it — pause premature/low-value automation rather than let it keep consuming
Oscar's personal Claude subscription quota while unsupervised.

---

## What changed

Commented out (not deleted) 3 crontab lines. Agent code, config, task templates, and output
directories are all untouched — this is purely a scheduling pause.

| Agent | Cron line paused | Verdict from audit |
|---|---|---|
| research-scout (morning) | `0 8 * * * run_research_scout.sh` | (c) NOT USEFUL |
| research-scout (evening) | `0 20 * * * run_research_scout.sh` | (c) NOT USEFUL, exact duplicate of morning run |
| integration-test-agent | `0 23 * * 0 run_integration_test.sh` | (b) REDUNDANT |

Live crontab now has these 3 lines commented, each with an inline reason and a pointer back
to this file. `crontab -l` reflects this as of 2026-07-15.

## Left running, unchanged

Rated **(a) genuinely useful** by the audit, and none were running more often than their
stated cadence warrants (all weekly, no cadence reduction needed):
- code-hygiene-agent — Fri 20:00
- training-librarian-agent — Sat 09:00
- performance-analyst-agent — Mon 06:00
- signal-agent — Mon 08:00
- trader-intelligence-agent — Mon 07:15

Not Tier-3 / no Claude tokens, untouched: database backup, daily_maintenance,
feedback-loop-agent (pure Python, no LLM calls), changelog_monitor,
legendary_positions_scan.py, backup_offsite.sh, weekly_resolution_sweep.sh, orchestrator.py
(systemd, local health-check loop, no LLM calls), all Tier-1/2/2.5 Ollama agents.

## Why (full detail in the audit, summarized here)

**research-scout** (2×/day, `claude --print --allowed-tools WebSearch`, no worktree):
- 135 logged runs: 27 timed out (20%, zero output), 19 completed with zero findings (14%).
  ~34% of all runs cost a full session for nothing.
- Of 58 files in `brain/research-scout/pending-review/`, dedup is broken: DeepSeek V4 filed
  9x, "when-do-markets-fully-process-public-information" 6x, "foresightflow" 5x. Roughly
  two-thirds of the surviving corpus is re-filed duplicates of ~20 unique underlying stories.
  2×/day cadence doubles the rate of duplicate filing.

**integration-test-agent** (weekly, full worktree + Tier-3 Sonnet session, 45 tests / 6 suites):
- Diagnosis quality is real, not hallucinated — but CI has failed 10 consecutive Sundays,
  and 6 failure categories are tagged SYSTEMIC (3rd-10th consecutive recurrence). One
  recent CRITICAL finding was a one-line fix (`touch orchestrator/__init__.py`) that had
  already been diagnosable for weeks. Paying full agentic-audit price weekly to re-discover
  known, unfixed problems.

## Confirmed: nothing downstream breaks

- No script or agent programmatically consumes integration-test-agent's output — it's a
  diagnostic report for humans, not a data source anything else reads.
- training-librarian-agent reads `brain/research-scout/approved/` as optional/advisory input
  (folds in new approved findings if present) — with the scout paused it simply sees no new
  approved items each week. Degrades gracefully, does not error or block.
- `orchestrator.py`'s own immune system only checks tmux-session liveness/timeout for tasks
  currently in `agent_registry.json` — it has no independent "agent X hasn't run in N days"
  alerting outside of integration-test-agent's own weekly test suite. Since that suite is
  now paused too, there is no risk of the orchestrator spamming false "dark agent" alerts
  about either paused agent.
- `brain/integration-contract.md` explicitly lists research-scout as "external reference
  only," not a dependency of any other agent's write path.

## Also found, NOT acted on in this change (separate governance/bugfix items)

- `spawn_agent.sh` does not check the Claude CLI's exit condition — a session-limit failure
  (`"You've hit your session limit"`) still gets marked `status: completed` in the registry
  and silently produces zero output. Confirmed in `hygiene-20260710`, `signal-20260629`,
  `signal-20260713` logs. This affects agents left running (signal-agent hit it ~2 of its
  last 7 weekly runs) and should be fixed independently of this pause.
- Stale orphaned registry entry `signal-202606042140` (dated 2026-06-04, `status: failed`)
  was not cleared as part of this change.
- The Monday-morning cluster (performance-analyst 06:00 → trader-intelligence 07:15 →
  signal-agent 08:00, previously also colliding with research-scout's 08:00 run) is
  partially resolved by this pause since research-scout no longer fires then. The remaining
  3-agent cluster was left as-is since all three are rated (a) useful and none were flagged
  as over-cadenced individually.

## Estimated token/quota savings

All Tier-3 agents run via `claude --dangerously-skip-permissions` or `claude --print` under
Oscar's OAuth Pro/Max subscription (`ANTHROPIC_API_KEY` explicitly unset in `spawn_agent.sh`)
— this is Oscar's personal session quota, not a metered API bill, so savings are stated as
sessions/week eliminated rather than dollars.

- research-scout: **14 full Claude sessions/week eliminated** (2/day × 7), each up to 120s
  with WebSearch tool calls — the highest-frequency Tier-3 job in the swarm, and the one
  with the worst waste rate (~34% pure failure, ~65% of the rest duplicate).
- integration-test-agent: **1 full worktree + Tier-3 Sonnet session/week eliminated** — the
  heaviest single Tier-3 session in the swarm (6 test suites reading registry, logs, CI,
  brain completeness across two repos).
- **Total: 15 Claude sessions/week removed from Oscar's personal quota**, concentrated
  exactly at the times (daily 08:00/20:00, Sunday 23:00) that were most likely to precede or
  collide with his own interactive usage.
- Remaining Tier-3 footprint: 5 sessions/week (one each for code-hygiene, training-librarian,
  performance-analyst, signal-agent, trader-intelligence), all weekly, all rated useful.

## Reactivation

Do **not** re-enable by bulk-uncommenting. Per Oscar's instruction, reactivate deliberately
during swarm consolidation, **one agent at a time**, each confirmed to produce value before
the next:

1. integration-test-agent: reactivate only after the current SYSTEMIC backlog (10-week CI
   failure streak, 6 flagged categories) is actually fixed — otherwise it will immediately
   resume re-diagnosing the same known issues.
2. research-scout: reactivate only after the dedup bug is fixed (dedup logic needs to check
   existing `pending-review/` + `approved/` + `dismissed/` + `archive/` content before filing
   a "new" finding). Consider reactivating at 1×/day rather than restoring the 2×/day cadence.
3. Fix the `spawn_agent.sh` exit-condition gap (silent session-limit failures marked
   "completed") before reactivating either — otherwise reactivation risk includes the same
   invisible-failure mode that was already observed on `signal-agent`.

## How to reverse this pause

Uncomment the 3 lines in the live crontab (`crontab -e` or `crontab -l | ...`). The commented
lines preserve the exact original schedule (`0 8 * * *`, `0 23 * * 0`, `0 20 * * *`) — no
schedule was altered, only disabled.
