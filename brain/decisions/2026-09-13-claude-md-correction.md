# Correcting CLAUDE.md's false and misleading claims

Follows: the built-never-connected sweep (trading-swarm `c45fb45`,
`brain/decisions/2026-09-13-built-never-connected-sweep.md`). This task
corrects first-repo's `CLAUDE.md` — the document loaded into every
session — where the sweep (and fresh verification) found it wrong.
Documentation only: no code changed, no wiring, no restarts, no writes
to any production table. `metric_v2f_oos_result` sha256 checked
throughout: `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
— unchanged.

**Governing distinction applied throughout:** (a) factually wrong — the
claim describes something that doesn't work and isn't intended to;
corrected or marked broken. (b) dormant intent — a wanted capability
that was built and never wired up; **not deleted**, relabeled with a
`[DORMANT INTENT]` marker and a pointer to where the existing code
lives, per Oscar's explicit direction that the local-LLM/agentic
elements are still wanted, planned for a dedicated session, and
expected to live mainly in trading-swarm.

---

## Part 1 — every claim checked, and its verdict

### The four claims named in the task

| Claim | Verdict | Action |
|---|---|---|
| "Runs AI-powered health monitoring via Mistral/Ollama (system observer)" | **(b) dormant intent** — confirmed `system_observer.py` has zero mentions of Ollama/Mistral/AIAnalyzer; `monitoring/ai_analyzer.py`'s `AIAnalyzer`/`OllamaClient` has zero callers anywhere; `monitoring/main.py` has a *second*, independent Pydantic-AI-via-Ollama agent, dead because `main.py` itself is not the live entrypoint (`scripts/start_monitoring.py` imports `monitoring.main_telegram_safe`, confirmed by direct read) | Relabeled `[DORMANT INTENT — not currently wired, do not delete]`, both dead implementations named, pointer to the sweep doc added. Not removed. |
| "Config overrides in `config/elo_update_settings.json`" | **(a) factually wrong** — zero programmatic readers anywhere (verified by grep, cross-checked against `config/accepted_failures.json`'s 6 live readers as a working-methodology control); its `telegram_notifications` block (`enabled`/`send_leaderboard`/`hourly_mini_leaderboard`: all `true`) actively contradicts the 2026-09-09 hardcoded Telegram silencing. This is not a dormant feature anyone is waiting to revive — there's no record of intent to wire it up, it's simply stale/orphaned documentation of a config surface nothing reads. | Corrected: states zero readers, flags the contradiction, marks the file non-authoritative. |
| `scripts/integrate_behavioral_elo.py` in "Key Scripts" and "Useful One-Liners" | **(a) factually wrong** — confirmed deleted, `61adaf5` (2026-07-12), file does not exist anywhere in the repo (not even archived) | Struck through in the table with the deletion commit noted; the one-liner replaced with `scripts/recalculate_comprehensive_elo.py` (the actual full-recalc script) and a comment explaining the substitution. |
| Documented DB size ~1.6 GB (April 2026) | **(a) factually wrong**, and worse than the task's own figure — actual size today is **~21 GB** (`ls -lh`, not the ~20.7GB estimate cited in the task; the DB has grown further since the sweep) | Corrected to current size with today's date; added a note to check `ls -lh` rather than trust any number in the file. |

### Found beyond the four ("look beyond these four")

| Claim | Verdict | Action |
|---|---|---|
| Row counts: traders 87,063+, trades 1M+, markets 220K+, positions 1,064K+ | **(a) factually wrong** — actual (2026-09-13, direct `SELECT COUNT(*)`): traders 198,699; trades 14,460,577; markets 878,646; positions 9,661,891. All previously understated 2x-9x. | Corrected to current counts with today's date. |
| Traders count in the opening description ("~87,000") | **(a) factually wrong**, same root cause as above | Corrected; cross-referenced to the Database table's fuller correction to avoid stating the number twice inconsistently. |
| "Sends Telegram alerts for elite trader activity" | **(a) factually wrong** — confirmed via direct grep of `system_observer.py`: `"[OBSERVER] Legendary-trade alert: SILENCED 2026-09-09 (final Telegram cut) — retired STR-003 signal era"`. The elite/LEGENDARY-tier alert this line describes was retired. | Corrected to name what actually alerts today (geo/elec pending-backlog, health-check degradation) and note the retirement. |
| "6-dimensional ELO ratings with behavioral analysis (Kelly criterion, patience metrics, market difficulty weighting)" | **(a) misleading as worded** — `W_BEH=0.0` (`analysis/comprehensive_elo_formula.py:15,26`, dated 2026-07-12, Stage 0b, tested and found null) means these components are computed but contribute exactly zero to the final score. The original wording implies they meaningfully shape the ELO number; they don't, by decision. | Corrected to state computed-but-zero-weighted, with the decision citation, so this isn't mistaken for a bug. |
| `polymarket-observer` service description: "AI health monitor" | **(a) factually wrong**, same root cause as the Mistral/Ollama claim (b) above — this is a second occurrence of the same false framing in the Services table | Corrected to remove "AI," with a pointer to the dormant-intent note so the two corrections stay consistent with each other. |
| `monitoring/main.py` — "Core monitor orchestrator" (Key Modules) | **(a) factually wrong** — confirmed via direct read of `scripts/start_monitoring.py`: it imports `from monitoring.main_telegram_safe import main`, not `monitoring.main`. `monitoring/main.py` is referenced by exactly one file in either repo: `scripts/archive/test_integration.py`. | Corrected to name `monitoring/main_telegram_safe.py` as the actual live orchestrator, with `main.py` explicitly flagged as superseded. |
| `monitoring/telegram_bot.py` — "Send-only Telegram notifications" (Key Modules) | **(a) factually wrong file** — this module's only class, `TelegramNotifier`, is the *old interactive/polling bot* (confirmed: zero live instantiations anywhere; its command handlers are correctly wired to the class, but the class itself is never constructed). The actual live send-only class is `TelegramHealthBot` in `monitoring/telegram_health_bot.py`, confirmed instantiated by `system_observer.py` and `scripts/verify_market_titles.py`. | Corrected to point at `monitoring/telegram_health_bot.py`, with `telegram_bot.py` explicitly named as dead code from the Jan-2026 send-only redesign. |
| Telegram config path: `monitoring/telegram_bot_config.py` | **(a) factually wrong path** — file does not exist at that path; it exists at `config/telegram_bot_config.py` | Corrected path. |
| `scripts/check_processes.py`, `scripts/check_monitoring.py` (Key Scripts + "Checking what's running") | **(a) factually wrong** — both moved to `scripts/archive/`, and confirmed **broken from there**: `check_monitoring.py` computes `project_root = Path(__file__).parent.parent`, which from `scripts/archive/` resolves one directory too shallow, so it would look for `logs/monitoring.log` and the DB at the wrong location. Not simply "moved," actually non-functional at any path today. | Marked NOT RUNNABLE in both places, with the systemd `systemctl status` commands (already documented one section above) offered as the working current alternative. |
| `scripts/update_database_from_csvs.py` (Key Scripts) | **(a) factually wrong** — also moved to `scripts/archive/`; not confirmed to still function from there (not independently traced for the same path-assumption bug as the two above, so marked as unconfirmed rather than asserted-broken) | Marked NOT RUNNABLE / unconfirmed. |
| "ELO recalculation schedule: Full 6-dimensional recalculation now runs automatically every Sunday via `daily_maintenance.py`" | **(a) factually wrong mechanism** — confirmed via `systemctl cat polymarket-sunday-elo.timer` (`OnCalendar=Sun *-*-* 03:00:00 UTC`) and its `ExecStart=.../scripts/run_sunday_elo.sh`, which directly calls `scripts/recalculate_comprehensive_elo.py` with `--skip-correlation --skip-contrarian --skip-advanced-metrics`. This is a dedicated systemd timer, entirely separate from `daily_maintenance.py` (which runs separately, daily at 06:00 UTC, and has its own additional Sunday-only steps that are NOT the full ELO recalculation). | Corrected to name the actual mechanism (`polymarket-sunday-elo.timer` → `run_sunday_elo.sh` → `recalculate_comprehensive_elo.py`) and explicitly distinguish it from `daily_maintenance.py`. |
| "Timing quality is intentionally disabled... all traders receive a neutral timing score" | **(a) factually wrong today** — confirmed `markets.created_at` still doesn't exist (unchanged), but a direct query (`SELECT timing_score, COUNT(*) FROM traders GROUP BY timing_score`) shows 34,906 distinct values across 44,652 traders with a score — only 8,670 sit at the neutral 0.5. `analysis/trading_behavior_analysis.py` contains the comment "works without created_at column (uses existing trade data)," confirming the computation was reworked at some point to route around the missing column rather than staying neutral-disabled. Separately and correctly noted elsewhere in the file: whatever it computes doesn't affect final ELO, because of `W_BEH=0`. | Corrected to state the column is still missing but the computation was reworked and produces real values; the W_BEH=0 non-effect is kept as a separate, correctly-stated fact. |
| "research_excluded clean pool is 857 traders" (April 30 2026 audit findings) | **Stale, not individually corrected** — direct query today: 43,176. This entire subsection is explicitly dated "as of April 30 2026" and reads as a historical audit record, not a live claim, so it was not rewritten line-by-line (would require re-verifying every other historical figure in that subsection to the same standard, which risks scope creep into "restructuring"). | Handled at the section level: added a `[STALE]` marker at the top of the whole "Current System State" section, naming this specific figure's staleness as the example, rather than correcting every number inside. |
| "Analysis modules returning real data — calibration, risk, and regret analysis modules... This is fixed" | **Not independently verified** — attempted a direct query but guessed the wrong column name; did not pursue further, since this is not one of the four named claims and no contradicting evidence was found (absence of verification is not evidence of wrongness) | **Left unchanged**, per the task's instruction to correct only what was found wrong. |
| Row-level commands: `python scripts/view_trader_rankings.py`, `python scripts/view_pnl_performance.py`, `python scripts/backup_database.py`, `scripts/kill_all.py`, `scripts/start_monitoring.py`, `scripts/run_system_observer.py`, `scripts/daily_maintenance.py`, `scripts/update_research_exclusions.py`, `scripts/recalculate_comprehensive_elo.py` | **TRUE** — every file confirmed to exist at its stated path | No change. |
| Services table names/commands (`polymarket-monitoring`, `polymarket-observer`, all `systemctl`/`journalctl` commands) | **TRUE** — confirmed both services `enabled`/live via `systemctl list-unit-files` | No change beyond the "AI health monitor" wording fix noted above. |
| "Telegram is send-only — no webhooks, no polling. Conflicts were fixed in Jan 2026" | **TRUE** as a behavioral description — confirmed this matches the live architecture (the dead `TelegramNotifier` polling class is exactly what this warning says was retired) | No change. |
| Trade gap April 7–18 2026 / `trade_gap_flag` guidance | **TRUE**, not contradicted by anything found | No change. |
| WAL mode permanence | **TRUE**, confirmed live in this session's own earlier work (`PRAGMA journal_mode=WAL` seen set on connection in `health_checker.py`, `database.py`, etc.) | No change. |

### Nothing required Oscar's input to classify

No claim was found ambiguous between (a) and (b) that couldn't be
resolved by direct verification. `config/elo_update_settings.json` was
the closest candidate for genuine ambiguity — asked and answered: there
is no record anywhere of intent to wire it up, only evidence it was
orphaned by the 2026-09-09 Telegram-silencing change, so it was treated
as (a), not (b).

---

## Part 2 — what changed, and what didn't

**Full diff reported in the reply to this task**, per the instruction
that a silent edit to this file is worse than a silent edit anywhere
else. Every edit was a targeted `Edit` (find-and-replace on the exact
wrong text), not a rewrite — the document's structure, section order,
and every claim not found wrong is untouched.

**A new section, "Known Documentation Gaps,"** was added (after
"Important Warnings," before "Architecture Summary" — the closest
existing structural seam, chosen to avoid inserting mid-section) naming
the 24-instance sweep and this correction pass, with the practical
instruction to verify rather than trust any "X reads Y" claim —
per the task's own framing, this is the durable fix; the four (now
sixteen) specific corrections are the immediate one.

**Nothing relating to local LLM, Ollama, Mistral, or agentic automation
was deleted, deprecated, or marked abandoned.** Both occurrences (the
opening bullet and the Architecture Summary diagram) use the same
`[DORMANT INTENT]` marker and point to the same evidence, so a future
session encountering either one lands on a consistent, non-conflicting
story.

**None of the 24 disconnections themselves were fixed.** This task
changed documentation text only — `git diff` on this session's work
touches only `CLAUDE.md`.

---

## Part 3 — verification

- Every command remaining in the document was checked to either run as
  written, or be explicitly marked NOT RUNNABLE with the reason
  (`check_processes.py`, `check_monitoring.py`, the struck-through
  `integrate_behavioral_elo.py` line).
- Every script/module path named anywhere in the corrected document was
  confirmed to exist via direct filesystem check — see the consolidated
  list in this session's own verification pass (23 paths, all present,
  including the newly-introduced `scripts/run_sunday_elo.sh`,
  `monitoring/main_telegram_safe.py`, `monitoring/telegram_health_bot.py`,
  `config/telegram_bot_config.py`).
- Every schedule claim was checked against live `systemctl` state:
  `polymarket-monitoring.service`, `polymarket-observer.service`, and
  `polymarket-sunday-elo.timer`/`.service` all confirmed `enabled` with
  the stated `OnCalendar`/`ExecStart` values.
- `metric_v2f_oos_result` sha256 re-checked immediately before
  committing: unchanged.
