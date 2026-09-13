# The built-never-connected sweep

Read-only. Extends pass 1's asset inventory (trading-swarm `1bb36e1`,
[`2026-09-12-heatmap-pass1-asset-inventory.md`](2026-09-12-heatmap-pass1-asset-inventory.md))
and today's own two findings (the burst-loop diagnosis, `db82c9b`, and the
ErrorParser pruning fix, `f5c2bab`). No fixes, no wiring, no deletions,
no restarts, no writes to any production table. `metric_v2f_oos_result`
sha256 checked before and throughout: `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
— unchanged.

**No active data loss or corruption found. No guard was found to have
already failed to catch something that has actually happened.** The
closest candidate (#22 below) is a structurally broken alert whose
trigger condition has never fired in ~3 months of logs — a loaded gun,
not a bullet that already landed unnoticed. Nothing here meets the
"report prominently" bar.

---

## Method — what this pass covered, and what it did not

Four parallel sweeps, plus direct follow-up on what they surfaced:

1. **Pass-1's explicitly-unswept directories**: `scripts/archive/` (67),
   `scripts/quick_fixes/` (3), `scripts/simulation/` (15) in first-repo;
   `orchestrator/permissions/`, `orchestrator/task_templates/` in
   trading-swarm. Covered by grep-based live-reference checking (does
   anything outside the directory reference a file inside it), not
   full-content reads of all 85 files — archived code with zero live
   references is expected and was not individually catalogued, per the
   task's own framing.
2. **Exhaustive zero-caller function/method sweep** of first-repo
   `monitoring/*.py` (38 files) and `analysis/*.py` (26 files) — AST-based
   extraction of all 647 top-level functions/methods, cross-repo grep for
   callers, manual re-check of the 58 zero-hit candidates for
   bare-reference patterns (callback registration, `asyncio.to_thread`,
   `@property`) that a naive grep misses. This is materially more
   thorough than pass-1's file-level pass. **`scripts/` (147 files) was
   NOT swept to this same function-level granularity** — pass-1's
   file-level docstring+caller-count pass is still the only coverage
   there. This is the largest known gap in this pass; see "Where to
   resume."
3. **Every `daily_maintenance.py` step** (32 Sunday / 30 weekday, read
   from the live `build_steps()` list) checked for a live consumer of its
   output.
4. **DB table delta since pass-1**: current table count vs. pass-1's
   audited 63, plus a fresh freshness check on every table pass-1 flagged
   stale.
5. **Direct follow-up investigation** (not delegated) on the
   `composite_skill_score.py` "undated caller removal" pass-1 left open,
   and on the `AIAnalyzer`/Ollama finding the zero-caller sweep surfaced
   — both below.

**Not done this pass**, honestly flagged rather than silently skipped:
function-level sweep of `scripts/` (147 files, only file-level coverage
exists); full-content read of all 85 archive/quick_fixes/simulation
files (grep-based reference checking only); git-blame on most Shape-3
findings to pin an exact decommission commit (done only where a fork or
this document opportunistically had time — see individual entries);
`database.py::get_traders_needing_pnl_update` and
`ollama_client.py`'s two zero-caller cache methods were surfaced but not
individually chased to a conclusion.

---

## Instances

Numbered continuously. Items 1, 2, 3, and 6 are the task's own named
seed cases, cross-referenced to their pass-1 or today's-session origin
rather than re-investigated from scratch (per instruction not to redo
pass-1's work) — each was still independently re-verified for currency
(freshness re-checked, fix status re-confirmed) rather than blindly
trusted. Items 7 onward are new to this sweep.

### 1. `check_canonical_definitions.py` — missing `load_dotenv()`
**Shape:** 4 (guard that cannot fire). **Cross-ref:** new to this session,
not in pass-1's inventory.
**What it is / where:** `scripts/check_canonical_definitions.py`, wired
into `daily_maintenance.py` in `419d223` (2026-06-24). Its
`send_telegram_alert()` reads credentials via bare `os.getenv(...)` with
no `load_dotenv()` call anywhere in the file — while
`audit_invariants.py`, the step immediately before it in the same run,
has the identical pattern but does call `load_dotenv("/home/parison/.env_trading")`.
**What it was supposed to do:** alert on Telegram the moment a canonical
definition violation is detected.
**Why disconnected:** **drift, not decision** — a copy-paste-shaped
omission relative to the correct sibling pattern in the very next step.
No doc anywhere frames this as intentional.
**Consequence:** 7 real canonical-definition violations were detected
and logged daily for **~11 weeks** (2026-06-24 → 2026-09-07) and never
once reached Telegram — the only record was a 43MB rotating log file.
**Record:** extensively documented — 5+ decision docs, including a
same-day self-correcting amendment. **Fixed** same day it was found,
first-repo `51e3b74` (2026-09-07). Confirmed still present today
(`scripts/check_canonical_definitions.py:236-237`). **Not a currently
open risk** — the template case, but closed.

### 2. `elo_snapshots` table
**Shape:** 1 (written, never read). **Cross-ref:** pass-1 B2.
**Re-verified this pass:** still 232,536 rows / 70 dates, still written
daily by `scripts/snapshot_elo_scores.py` (a live `daily_maintenance.py`
step), still read only by the same two dormant one-off scripts pass-1
named. No change since 2026-09-12.

### 3. `analysis/composite_skill_score.py` — refined, not just cross-referenced
**Shape:** 3 (built, caller lost). **Cross-ref:** pass-1 B1, materially
extended by direct git-archaeology this pass.
**What it is / where:** 906-line `CompositeSkillScoreSystem`
(8-dimension, 100-point trader score); its convenience wrapper
`UnifiedELOSystem.get_composite_skill_score()` (`analysis/unified_elo_system.py:4047`).
**Pass-1 left open:** whether/when a caller existed and was removed
between the module's 2025-12-05 addition and a March 2026 archive
handover showing it "ACTIVE with real output" (13,021 traders scored).
**Resolved this pass:** `git log --all -S".get_composite_skill_score("`
across the entire repository history finds **exactly one commit**
(`b11b42d`, the original addition) — no commit ever added or removed a
call to this method. The March handover's "13,021 scored" activity is
fully explained by a **different mechanism**: the archive handover
itself says composite scores were "activated in scheduler" as
**Phase 3b**, and `analysis/analysis_scheduler.py::run_phase_3b_composite_scores()`
(line 796, unconditionally called from `run_full_analysis()` at line
1324, "always run — graceful degradation") **still exists and is still
called today** — but it does **not** call into `composite_skill_score.py`
at all. It reimplements its own "lightweight inline logic" (`_elo_points`,
`_behavioral_points`, a separate network-independence blend) directly
inside `analysis_scheduler.py`.
**Why disconnected:** the 906-line module and its `UnifiedELOSystem`
wrapper were never wired to anything that survives in version control —
not "caller silently removed" so much as "never had a committed caller
at all," while a completely independent, simpler, live reimplementation
of the same *concept* was built alongside it and is what actually ran
(and still runs). **Undetermined whether this was a deliberate rewrite
decision or two people/sessions solving the same problem twice without
noticing** — no doc found explaining the duplication.
**Consequence:** none currently — a live, much simpler proxy fills the
conceptual gap (see #12, which is itself unconsumed).
**Record:** `2026-09-05-canonical-skill-metric-design.md` explicitly
excludes `composite_skill_score.py` from the metric replacement design,
"named here specifically so it is not 'discovered' again as if new" —
that document did not know about the `run_phase_3b` duplicate, however.

### 4. `ErrorParser.clear_old_errors()` — today's own fix
**Shape:** 3 (built, caller lost). **Cross-ref:** this session,
`2026-09-13-observer-burst-loop-and-memory-diagnosis.md` (diagnosis) and
`2026-09-13-observer-error-parser-pruning-fix.md` (fix). Fixed:
first-repo `eabc323`. **Fully resolved, not an open instance** — included
here only for the pattern count, per the task's own framing.

### 5. `TelegramHealthBot.last_alert_time` — today's own finding, unfixed
**Shape:** 4 (guard that cannot fire — no eviction path exists at all,
not merely uncalled). **Cross-ref:** this session, same two docs as #4.
**Status:** found, reported, intentionally left unfixed per explicit
operator scope decision. Still open.

### 6. `insider_signals` / `insider_clusters` read by `system_observer.py`
**Shape:** 2 (read, never written — a live consumer polling a dead
pipeline). **Cross-ref:** pass-1 D10.
**Re-verified this pass:** no new rows in either table — `insider_signals`
last write still 2026-05-02, `insider_clusters` still 1 row ever, exactly
matching pass-1's figures with zero drift since 2026-09-12. Additionally
found this pass: `daily_maintenance.py` step 10, `score_insider_signals.py`,
only *scores* existing rows against resolved markets — it does not
generate new ones, so this daily step has had structurally nothing new
to score for 4+ months. Folded in as reinforcing evidence of the same
dead pipeline, not counted as a separate instance.

### 7. `scripts/simulation/verify_elo_rankings.py` cited as "ELO Verification"
**Shape:** 4 (guard that cannot fire — looks correct, verifies nothing).
**What it is / where:** `monitoring/diagnostics.py:195`, inside the live
`HealthChecker`/`FixSuggestionEngine`'s `check_analysis_tools()`:
`'ELO Verification': 'scripts/simulation/verify_elo_rankings.py'`. Also
cited as a remediation step by `scripts/validate_roi_rebalancing.py:237`.
**What it was supposed to do:** verify production ELO rankings.
**Why disconnected:** the health check only confirms the file *exists
and compiles* (`Path.exists()` + `compile()`), never runs it, and the
file itself operates on a separate simulation-sandbox database, not
production. **Undetermined** — no doc found explaining why a
simulation-sandbox script was ever wired in under this name.
**Consequence:** an "ELO Verification" health-check entry has been
silently green forever, verifying nothing about production ELO. Not
flagged as prominent — nothing live gates on this check's result beyond
reporting it, so no downstream decision was ever silently miscalibrated
by it, as far as this pass established.
**Record:** none found.

### 8. `scripts/archive/test_market_filtering.py` — broken import in a hand-run CLI
**Shape:** 3 (built, caller lost — but fails loudly, not silently).
**What it is / where:** `scripts/run_analysis.py:102` (a numbered
interactive menu, confirmed zero external callers — a legitimate
hand-run CLI, not a live pipeline component) does
`from test_market_filtering import test_market_exclusion`, but the
target moved to `scripts/archive/` and `run_analysis.py`'s own
`sys.path.insert` only adds `analysis/`. Selecting menu option 9 today
raises `ModuleNotFoundError`.
**Consequence:** low severity — fails immediately and visibly to whoever
runs it by hand, not a silent background failure. Included for
completeness, not because it is dangerous.

### 9. `scripts/integrate_behavioral_elo.py` — deleted, but still told to humans
**Shape:** 4 (a fix-suggestion/documentation guard pointing at nothing).
**What it is / where:** the script itself was **deliberately deleted**
2026-07-12 (`61adaf5`, "Stage 0c — delete dead Writer C") — a
**documented decision**, verified-before-deletion, well-recorded. But
three live references to it as a runnable script survive today:
`CLAUDE.md`'s "Key Scripts" table and "Useful One-Liners" section (loaded
into every session), `scripts/validate_pnl_data.py:242`, and
`scripts/validate_roi_rebalancing.py:236`.
**Why disconnected:** the deletion decision's propagation was
incomplete. One prior instance of exactly this reference (in
`monitoring/diagnostics.py`'s `check_analysis_tools()`) **was found and
fixed** 2026-09-07 after it fired a stale CRITICAL for ~8 weeks
(`2026-09-07-telegram-remediation.md` Part 4a) — but that fix addressed
only that one reference; the other three were not checked at the same
time and still tell a human to run a file that has not existed in over
two months.
**Consequence:** a human following CLAUDE.md's own documented commands,
or a validation script's own remediation advice, would run a command
that fails immediately. Not silent, but actively misleading.
**Record:** the *fixed* instance is documented; these three surviving
ones are not, anywhere — this document is the first place they're named.

### 10. `orchestrator/permissions/` coverage gap
**Shape:** N/A — not a disconnection, a coverage note. 6 of 15
`task_templates/`-defined agent personas (`market-builder`,
`market-intelligence-agent`, `niche-app-agent`, `orchestrator-system`,
`research`, `trader-intelligence-agent`) have no entry in either
`orchestrator/permissions/*.json` or the legacy
`orchestrator/agent_tool_permissions.json`. Confirmed the fallback path:
an agent type found in neither file gets an **empty tool list** (fails
closed, not open) with a logged warning. Not a danger, not reported as
an instance — `trader-intelligence-agent` is one of the five already
paused via commented-out cron (prior project memory), so its gap is
currently moot regardless.

### 11. `config/elo_update_settings.json` — dead, and actively misleading
**Shape:** 4 (a configuration surface that cannot influence behavior, and
whose content contradicts reality).
**What it is / where:** `config/elo_update_settings.json`. **Zero
programmatic readers found anywhere in either repo** — confirmed by grep
and validated against a working contrast case
(`config/accepted_failures.json`, same grep method, 6 live readers
found, so this is not a methodology miss).
**Why this matters beyond "unused config":** its content
(`"telegram_notifications": {"enabled": true, "send_leaderboard": true, "hourly_mini_leaderboard": true}`)
directly **contradicts** actual current behavior — those same features
were hardcoded SILENCED in `system_observer.py` on 2026-09-09. **CLAUDE.md
itself asserts "Config overrides in `config/elo_update_settings.json`"
as live project documentation — that claim is currently false.**
**Why disconnected:** **undetermined origin** — single commit in this
file's entire history (`35090f6`, 2026-01-26, a large consolidation
commit), so whether it once had a reader that was lost, or arrived
already-orphaned, cannot be established from git history. Honestly
flagged as undated rather than guessed.
**Consequence:** anyone editing this file to change ELO-update or
Telegram-notification behavior would have **zero effect** and would not
find out why.
**Record:** none found describing this specific disconnection; the
2026-09-09 Telegram-silencing decision itself (which orphaned this
file's relevance) IS documented elsewhere, just not cross-referenced to
this file.

### 12. `analysis_scheduler.py::run_phase_3b_composite_scores()`'s own output — unread
**Shape:** 1 (written, never read) — new, found via the #3 follow-up.
**What it is / where:** `analysis/analysis_scheduler.py`, called
unconditionally, daily, at 01:00 UTC via the live observer's analysis
scheduler (`monitoring/system_observer.py:2665`,
`scheduler.run_full_analysis()`). Writes a dated CSV
(`reports/composite_scores_YYYYMMDD.csv`) and stores
`self.results['composite_scores']`.
**Consequence if it mattered:** confirmed via direct read of
`generate_unified_report()` (the only consumer of `self.results`,
`analysis_scheduler.py:651`) that `composite_scores` is **never
referenced there or anywhere else** — computed and filed away daily,
indefinitely, unread. Directly analogous to `elo_snapshots` (#2), one
level further down the pipeline and not previously catalogued.
**Record:** none found — genuinely new.

### 13. `monitoring/ai_analyzer.py`'s `AIAnalyzer`/`OllamaClient` — the biggest single finding
**Shape:** 3 (built, caller lost) — at the scale of an entire documented
subsystem, not a function.
**What it is / where:** `AIAnalyzer` (methods `analyze_error`,
`detect_anomaly`, `suggest_optimizations`, `generate_daily_report`,
`is_ollama_available`), wrapping `OllamaClient`. **Zero references to
`AIAnalyzer(` anywhere in either repo outside its own file** — confirmed
independently by direct grep, not just the sweeping fork's report.
**What it was supposed to do:** CLAUDE.md's own top-level description of
this project states: *"Runs AI-powered health monitoring via
Mistral/Ollama (system observer)."* `monitoring/system_observer.py` —
the component this sentence names — contains **zero mentions of Ollama,
Mistral, or AIAnalyzer anywhere**, confirmed by direct grep.
**Why disconnected:** undetermined — not one function losing a caller,
but a class that appears to have never been wired into the live
observer at all, or was wired in and fully unwound at some point with no
trace in `system_observer.py`'s current code. No git-blame run on this
(out of this pass's time budget) — flagged for a future pass rather than
guessed at.
**A second, independent dead attempt at the same capability, found
following up on this:** `monitoring/main.py` has its own, completely
separate Ollama/Mistral integration — a Pydantic-AI agent
(`check_ollama_running()`, `check_mistral_model_available()`,
`"openai:mistral:latest"`). This is dead for a *different* reason:
`monitoring/main.py` itself is not the live monitoring entrypoint — the
actually-running module, confirmed by this session's own earlier
progression-check journal read, is `monitoring.main_telegram_safe`
(`"Starting monitoring (Telegram-safe mode)"`), which contains **zero**
mentions of ollama/mistral/pydantic. `monitoring/main.py` is referenced
by exactly one file in either repo: `scripts/archive/test_integration.py`.
**Consequence:** CLAUDE.md documents a capability — AI-powered health
monitoring via a local LLM — that has **no live implementation at all**,
across both attempts found. This is not a small utility; it's a named
pillar of the system's own top-level description.
**Record:** none found acknowledging this gap anywhere in either repo's
decision-doc history.

### 14. The Telegram send-only migration's orphaned classes (grouped, one family)
**Shape:** 3 (built, caller lost), all **likely by decision** — the
January 2026 "Telegram is send-only — no webhooks, no polling" redesign
CLAUDE.md itself documents — but the old code was never deleted.
- **`monitoring/telegram_bot.py::TelegramNotifier`** — the old
  interactive/polling bot class. Zero live instantiations anywhere. Its
  command handlers (`start_command`, `status_command`, `stop_command`,
  `traders_command`) ARE correctly wired *to the class* via
  `CommandHandler("start", self.start_command)` — the class's internals
  are internally consistent, it is simply never constructed.
- **`monitoring/monitor.py::PolymarketMonitor.request_stop()`** — zero
  callers. This is the other half of the same removed feature: the
  method `TelegramNotifier.stop_command()` was built to invoke. The
  actual live stop path today is `scripts/kill_all.py` (OS-level
  `terminate()`/`kill()`), confirmed no signal handler anywhere calls
  `request_stop()` either.
- **`monitoring/telegram_elo_bot.py::ELOTelegramBot`** — only
  instantiated by two files in `scripts/archive/` (tests). Confirmed dead
  by pass-1 already (its docstring: "Not fixed — flagged for Oscar" —
  pass-1's own D-adjacent verification table).
- **`monitoring/telegram_scheduler.py::TelegramScheduler`** — imports
  `ELOTelegramBot` but is itself **never instantiated anywhere,
  including its own file**. Its one method,
  `schedule_daily_leaderboard()`, is unreachable transitively.
**Consequence:** none currently — this is dead-but-harmless code, not a
live gap, since the send-only redesign correctly routes everything
through the surviving `TelegramBot`/`TelegramHealthBot` send path.
Grouped as one entry because it is one coherent, well-evidenced story,
not four independent mysteries.

### 15. `analysis/pit_positions.py::reconstruct_positions_at()` — refines pass-1's V2
**Shape:** 3 (built, caller lost). **Cross-ref:** pass-1 V2, sharpened.
Pass-1 found the *validation harness* (`scripts/validate_pit_positions.py`)
had zero callers, leaving open whether the underlying function itself
was still used elsewhere. This pass confirms it is not: zero callers
anywhere, including from its own harness. Both halves of V2's proof
chain are disconnected from each other and from everything else — the
PROVEN 1.2M-item validation this function underpins is not re-checked by
anything as the codebase changes.

### 16. `analysis/trader_statistics.py::update_trader_comprehensive_stats()` — a small second composite_skill_score
**Shape:** 3 (built, caller lost).
Docstring: "This replaces `update_trader_win_rate()` with a comprehensive
version." Zero callers. The containing class (`TraderStatisticsCalculator`)
is live and used (`scripts/recalculate_trader_stats.py`,
`scripts/view_trader_stats.py`), and its own internal batch path still
calls the **old** `update_trader_win_rate()` — the replacement was
written and never wired in; the old path was never retired. A smaller,
cleaner instance of exactly #3's pattern (build a replacement, leave the
original live).

### 17. `analysis_scheduler.py::run_phase_3c_confidence()` — a comment describing a call that isn't there
**Shape:** 3 (built, caller lost) — or possibly documentation drift; kept
distinct from #3/#16 because the evidence is a comment, not a docstring
claim. Line 557, exactly where Phase 3c should run:
`# 2. Market Confidence Meter — delegated to run_phase_3c_confidence() (called separately after Phase 3 to keep this block clean)`
— no such call exists anywhere in either repo. Reads like an
uncompleted TODO or a removed call whose comment survived the removal.

### 18. Dead public API surfaces on otherwise-live classes (grouped)
**Shape:** 3 (built, caller lost) — the subtle sub-pattern: the class
works and is actively used, but one specific method on it is not.
- `analysis/correlation_matrix.py::TraderCorrelationMatrix.analyze_trader_relationships()`
- `analysis/copy_trade_detector.py::CopyTradeDetector.validate_signal_independence()`
  — **its own docstring falsely claims** "Used by confidence_meter";
  confirmed `market_confidence_meter.py` calls neither the class nor this
  method.
- `monitoring/error_classifier.py::ErrorClassifier.get_all_known_issues()`
- `monitoring/elo_bridge.py::UnifiedELOMonitoringBridge.get_performance_stats()`
- `analysis/trader_specialization_analysis.py::TraderSpecializationAnalyzer.get_trader_specialist_weight()`
  and `.get_category_specialists()`
All five containing classes confirmed genuinely live elsewhere. Grouped
as one entry — same shape, same low individual severity, worth counting
together as evidence of a recurring micro-pattern rather than five
separate stories.

### 19. `scripts/detect_counter_signals.py::_fire_alert()` — the clearest new match to the template
**Shape:** 4 (guard that cannot fire) — the strongest, cleanest new
instance of this pass, directly analogous to #1.
**What it is / where:** `scripts/detect_counter_signals.py`, step 27 of
`daily_maintenance.py`, live, runs daily. Docstring: "Fires Telegram
alert only on REVERSED by a LEGENDARY trader."
**What it actually does** (`detect_counter_signals.py:310-319`): builds
the alert message, then
`print(f"\n[ALERT] {msg}", file=sys.stderr)` followed by the comment
`# Wire to actual telegram sender if available in maintenance context`.
That is the entire function body. No Telegram call exists, anywhere.
**Why disconnected:** neither decision nor drift in the usual sense —
checked against the introducing commit, `3f61528` (2026-06-15): the
"Wire to actual telegram sender" TODO is present in the **original**
commit. This shipped incomplete from day one and has run daily,
non-blocking, in production for **~3 months**, with no reference to the
gap found anywhere in `brain/decisions/`.
**Consequence if it mattered — checked directly against the log**:
`daily_maintenance.log` (covering 2026-05-31 onward, before the script
even existed) shows exactly 2 counter-signal detections ever, both
classified `EXITED` (the non-alerting branch). **Zero `REVERSED` events
found anywhere, zero `[ALERT]` lines ever printed.** The condition this
guard exists for has genuinely never occurred — this is a confirmed,
currently-broken guard whose trigger has not yet fired, not a case of an
already-missed real event. Does not meet the "report prominently"
stop-condition bar, but it is the single cleanest structural match to
the load_dotenv template (#1) found anywhere this pass — same shape,
same "shipped without the last wire," different specific cause.
**Record:** none found — undocumented anywhere until this sweep.

### 20. Confirmed non-instances worth naming (base-rate evidence for the verdict)
- **`W_BEH = 0.0`** (`analysis/comprehensive_elo_formula.py:15,26`) —
  re-confirmed current and unchanged. Explicitly dated, documented
  decision (2026-07-12, Stage 0b). Pass-1 B3-B6, not new, cited here only
  to confirm it still holds.
- **`category_classification_log` table** — new since pass-1's 63-table
  audit (0 rows, created by migration `26ba190`, 2026-08-31). **By
  explicit documented decision, not drift**: `relevance_classifier.py`'s
  own docstring states the module deliberately makes no DB writes, and
  that a write-path caller "is a separate, later task, not part of this
  module" — that later task was simply never picked up, consistent with
  the relevance classifier's broader `§3.11(a) abandon` status already
  on record.
- **`elo_formula_audit_findings`/`elo_formula_audit_pre_registration`** —
  not actually new (pass-1's own Residual section already named these as
  unaudited); confirmed this pass to match pass-1's own D9 "one-off audit
  trail" pattern exactly, not the `elo_snapshots` failure mode.
- **`system_observer.py`'s own paused methods** (`_daily_report_loop`,
  `_weekly_report_loop`, `_send_diagnostic_report`) — self-documented
  in-code as "NOT CURRENTLY SCHEDULED (paused 2026-09-07...)" — a clean
  example of the *correct* way to leave code disconnected: dated,
  explained, in the code itself.
- **`scripts/simulation/`'s internal structure** — a deliberately
  guarded, self-contained sandbox (`_sim_db_guard.py`, an explicit
  production-write guard imported by ~11 of its 15 scripts). Zero
  external callers into it is expected and correct, not a finding.
- **~20 zero-caller false positives** ruled out by the zero-caller sweep
  before they were ever reported: Telegram `CommandHandler`-registered
  methods, `diagnostics.run_full_diagnostic` (passed to
  `run_in_executor`), `monitor.py`'s `asyncio.to_thread`-offloaded
  methods, a `@property`. Naming these to show the sweep's false-positive
  rate was actively managed, not ignored.
- **No table was dropped since pass-1.** No evidence anywhere of active
  data loss.

---

## What was not determined (honest gaps, not silent ones)

- `scripts/` (147 files) was not swept to the same function-level
  granularity as `monitoring/`/`analysis/` — only pass-1's file-level
  pass exists there. **This is where a second pass should resume first**
  — it is the largest unswept surface and the one most likely to hide
  more Shape-3 instances, by the same base rate this pass found in
  `monitoring/`/`analysis/`.
- All 85 files under `scripts/archive/`, `scripts/quick_fixes/`,
  `scripts/simulation/` were reference-checked, not content-read.
- `database.py::get_traders_needing_pnl_update` and
  `monitoring/ollama_client.py`'s two zero-caller cache methods
  (`clear_cache()` — confirmed benign, see below — and one other) were
  surfaced but not individually chased to a documented conclusion.
- No git-blame was run to pin an exact decommission commit for: #13
  (`AIAnalyzer`), #14's four classes individually (the *family* is dated
  to the January 2026 redesign by inference from CLAUDE.md, not by
  finding the specific commit that stopped calling each one), #17, or
  #18's five methods.
- `monitoring/ollama_client.py::clear_cache()` is dead but was traced far
  enough to confirm **no consequence** — the cache it would clear
  already self-bounds via a size cap and read-time expiry elsewhere in
  the same file. Included in "not determined" only in the sense of "not
  git-blamed," not in the sense of "risk unassessed."

---

## The verdict

**Systemic, not coincidental.**

This pass — four bounded sweeps plus targeted follow-up, explicitly
*not* covering the largest single code surface (`scripts/`, 147 files,
at function granularity) — found **14 new instances** (7 through 19,
excluding the grouped sub-entries counted individually: #14 is 4
classes, #18 is 5 methods) beyond the 6 named in the task prompt, for a
running total of **at least 24 distinct disconnections** now on record
across pass-1, today's earlier diagnosis, and this sweep — found by
three different search strategies (accidental discovery, a systematic
zero-caller AST sweep of under half the codebase's script surface, and a
step-by-step consumer check of one pipeline). A codebase where a
narrower, non-exhaustive search keeps finding more of the same shape,
faster than it can be closed, is not "six coincidences" — six would have
been a plausible base rate; twenty-four, found this fast, in this little
of the codebase, is not.

**Shape distribution confirms a specific mechanism, not a generic "code
rots" story:**
- **Shape 3 (built, caller lost) dominates** — roughly 14 of the 24
  known instances. And within Shape 3, a clear sub-pattern recurs
  independently at least four times: `composite_skill_score.py`
  superseded by an inline reimplementation elsewhere (#3);
  `trader_statistics.py`'s comprehensive-stats replacement never wired in
  while the old path stayed live (#16); the entire Telegram
  interactive-bot family orphaned by the send-only redesign (#14); and
  `ai_analyzer.py`/`main.py`'s AI-monitoring capability orphaned when
  `main_telegram_safe.py` superseded `main.py` (#13). **The common
  mechanism: when this codebase redesigns or rewrites a capability, the
  old implementation is routed around, not deleted — and nothing
  structural (no lint rule, no caller-count test, no dead-code CI check)
  ever catches the orphan.** This is confirmed, not assumed: four
  independent instances of the exact same "superseded, not removed"
  story, found in four unrelated parts of the codebase.
- **Shape 4 (guard that cannot fire) is smaller (6 of 24) but more
  dangerous per-instance**, exactly as the task predicted — every one
  found this pass (#1, #5, #7, #9, #11, #19) looks correct in isolation
  and was found only by checking whether its actual effect matched its
  name/docstring, not by reading the code and stopping at "looks fine."
  The mechanism here is different from Shape 3's: **a human-facing
  reference (a docstring's claim, a health-check label, CLAUDE.md's own
  documentation, a fix-suggestion string) points at something that
  stopped being true, and nothing automated ever re-verifies that the
  reference still resolves to what it claims.**
- **Shape 1 (2 instances) and Shape 2 (1 instance) are rarer** in this
  sample, but not absent — `elo_snapshots` and the newly-found Phase 3b
  composite-score CSV are the same "written on a live schedule, read by
  nothing" story one level apart in the pipeline, which itself is mild
  evidence the mechanism generalizes past just "orphaned callers" to
  "orphaned outputs."

**What would close this concern, and what would not.** A single cleanup
pass through the 24 known instances would not close it — the mechanism
that produced them (redesign-without-deletion, and undated-origin
config/docs) is still active and would produce a 25th tomorrow. What
this sweep cannot determine — and was explicitly told not to propose —
is the remedy; that is Oscar's call, and he has already deferred
deletion pending a path forward.
