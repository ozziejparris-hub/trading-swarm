# Telegram Alert Audit — Diagnosis Before Redesign

**Scope:** read-only throughout. No alert fixed, disabled, silenced, or
modified. No file deleted or restored. No trigger condition changed. This
audits every Telegram-sending code path across both repos, diagnoses which
are silently dead and which are noisy, and proposes (without recommending)
what a strict, action-only channel would look like. Follows this morning's
[[2026-09-07-canonical-enforcement-part1-stop]] finding that
`check_canonical_definitions.py`'s alert never fires.

Tagging: [V]=verified this session (code/log/live-query read or run
directly), [I]=inferred.

---

## VERDICT — no stop condition triggered

Every finding below is either **noise** (a sender that fires too often to
carry signal) or a **stale/deliberate condition** (an alert correctly
reporting a state that was intentionally created and never cleaned up).
Nothing found here is a *new*, *unnoticed*, *live* system failure in the
sense the stop condition means — i.e., a real incident happening right now
that nobody knows about. The two most dramatic-looking findings resolve
that way on inspection:

- **The elite-trader-alert path (`monitor.py`'s `elo_bot`/`telegram`) is
  permanently `None`, so it has sent nothing since 2026-01-27** — but this
  is not a bug. It is a deliberate, human-authored removal
  (`423b3b5`, Oscar Parris, "telegram monitoring feed removed"), documented
  again in-code at `monitor.py:1430-1431`. Reported as a **silent sender**
  in Part 2, not a stop-worthy failure.
- **"ELO Integration: File missing" has been CRITICAL for ~8 weeks** — the
  file was deliberately deleted (`61adaf5`, "Stage 0c — delete dead Writer
  C", 2026-07-12), verified dormant before removal. The alert is stale, not
  a real failure — see Part 4b.

Proceeding through all five parts as scoped.

---

## PART 1 — Inventory

| Sender | Trigger | Condition (quoted from code) | Credential method | Arriving? |
|---|---|---|---|---|
| `scripts/audit_invariants.py` | daily_maintenance step 7, cron `0 6 * * *` | `--alert`; fires whenever any REGRESSION/CRITICAL invariant is found (unconditional on invocation, conditional on content) | `load_dotenv("/home/parison/.env_trading")` (`:1001`), explicit | **YES** — confirmed live: `[TELEGRAM] Alert sent.` in today's log |
| `scripts/check_canonical_definitions.py` | daily_maintenance step 8, cron `0 6 * * *` | `--alert`; fires only `if violations` | bare `os.getenv("telegram_alerts_token")` (`:191`), no self-load | **NO** — `[TELEGRAM] Credentials not found — skipping alert.` every run |
| `scripts/detect_counter_signals.py` (`_fire_alert`) | daily_maintenance step, cron `0 6 * * *` | Python: fires only on a LEGENDARY-trader reversal (`if leg_reversals:` → `_fire_alert(...)`, `:274`) | n/a — `_fire_alert` only `print()`s to stderr; **no Telegram API call exists in this function at all** | **NO**, structurally — would still not reach Telegram even with perfect credentials |
| `scripts/register_signal.py` (`_fire_telegram_alert`) | event-driven, called on STR-003 signal registration (from trading-swarm orchestrator, not cron) | `if fire_alert:` (caller-supplied flag) | n/a — same as above, `print(f"[telegram] Would send:...")`, no API call | **NO**, structurally, same reason |
| `monitoring/monitor.py` (`self.telegram`, `self.elo_bot`) | `polymarket-monitoring.service` (systemd, continuous 15-min loop) | Both hardcoded `None` at `__init__` (`:86-87`); every call site is dead code behind `if self.elo_bot:` / `if self.telegram:` | n/a — never constructed | **NO** — deliberately disabled since 2026-01-27 (`423b3b5`), not a credential issue |
| `monitoring/background_pnl_worker.py` (PNL-skip alert) | constructed by `monitor.py` with `telegram_bot` unset → defaults to `None` | `if self.telegram_bot is not None:` (`:472`) | n/a — never passed a bot instance | **NO** — same lineage as `monitor.py`, not independently broken |
| `analysis/analysis_scheduler.py` | **not currently invoked** by cron, systemd, or daily_maintenance (grepped all three; zero references) | `self.telegram = None  # Initialize if needed` (`:50`), never wired | n/a | **NO** — dead code, not presently a live sender at all |
| `monitoring/system_observer.py` / `telegram_health_bot.py` — one shared bot instance, `polymarket-observer.service` (systemd) | see sub-rows below | — | systemd `EnvironmentFile=/home/parison/.env_trading` (works — systemd's own parser does not require `export`) | **YES** for the whole file — one bot instance, one working credential path |
| ↳ hourly report | every 60s poll, sends when "time is up" | Code says `if metrics.get("status") != "healthy" or metrics.get("error_count",0)>0` (`:471`) — **but `_collect_metrics()` never sets a key named `"status"`** (only `"health_status"`, `:2020`), so this is always `None != "healthy"` → **always True** | (see file-level row) | YES, ~hourly regardless of health — see Part 3 |
| ↳ daily report (23:00 UTC) | `if now.hour==23 and now.minute==0` | Unconditional digest — `if self.telegram: send` (`:508`), no health gate at all (by design, it's a digest) | (see file-level row) | YES, daily |
| ↳ weekly report | 7-day loop | not deep-audited this session — noted, not characterized | (see file-level row) | presumed YES |
| ↳ comprehensive diagnostic report (6h) | `if hours_since >= 6` | Unconditional — `await self._send_diagnostic_report(report)` runs every cycle regardless of `overall_status`; a *separate* extra alert fires additionally `if report['overall_status']=='CRITICAL'` (`:3124-3126`) | (see file-level row) | YES, every 6h — see Part 3/4 |
| ↳ health-check loop (60s) | per-cycle | `if health['status'] != 'healthy': send` (`:291-292`) — **correctly gated**, uses the right key from `health_checker.check_all()` (a different dict than the hourly report's) | (see file-level row) | YES, only on non-healthy transitions — this one works as intended |
| ↳ log-monitor / error alerts | event-driven | fires on detected error patterns (`:362,381,396`) | (see file-level row) | not deep-audited; event-driven, presumed conditional |
| ↳ insider detection, consensus positions/exits, legendary trades, trend alerts | 15-min / hourly loops | each fires only on a detected pattern (event-driven) | (see file-level row) | not deep-audited; presumed conditional by design |
| `trading-swarm/orchestrator/orchestrator.py` (`send_telegram`) | `trading-swarm.service` (systemd, continuous) | caller-determined per call site (not audited exhaustively) | systemd `EnvironmentFile=/home/parison/.env_trading` (works) + bare `os.getenv` (`:65-68`) — works here because **systemd**, not bash, populates the environment | **YES** |
| `trading-swarm/scripts/run_feedback_loop_agent.py` (`send_telegram`) | weekly cron, `0 7 * * 1` | not deep-audited | hand-rolled `_load_env_file()` (`:75-89`, self-written dotenv-equivalent), explicit self-load | **YES** — confirmed: `[feedback-loop-agent] Telegram notification sent` in log |
| `trading-swarm/scripts/polymarket_changelog_monitor.py` (`send_telegram`) | weekly cron, `30 7 * * 1` | not deep-audited | hand-rolled `load_env()` (`:29-39`), explicit self-load | **YES** — confirmed: `Telegram message sent.` in log |

---

## PART 2 — The silent ones

**Same gap as `check_canonical_definitions.py` (missing self-load, cron
strips the shell's un-exported `.env_trading` vars before they reach
Python):** confirmed to be the **only** instance of this specific failure
mode. Every other cron-launched sender that reads credentials via bare
`os.getenv`/`os.environ` either (a) runs under **systemd** instead of cron
— and systemd's `EnvironmentFile=` directive does not require `export`,
so it works without any self-load — or (b) explicitly self-loads
`.env_trading` itself (`load_dotenv()` in `audit_invariants.py`; two
independent hand-rolled equivalents in
`run_feedback_loop_agent.py`/`polymarket_changelog_monitor.py`).
`check_canonical_definitions.py` is the one sender that does neither.
**Verified empirically**: a minimal reproduction (`source` an unexported
`VAR=value` file, then spawn `python3 -c "os.environ.get(...)"`) confirms
the variable does not propagate — this is a real, general property of the
cron-wrapper pattern, not specific to one script.

**Distinct, non-credential silent senders found this session:**

| Sender | Why it's silent | Since |
|---|---|---|
| `monitor.py` elite-trader / large-position / contrarian / win-streak alerts | `self.elo_bot = None`, deliberately, never reconstructed elsewhere in the codebase (confirmed: `TelegramELOBot(` has zero call sites anywhere) | 2026-01-27 (`423b3b5`) |
| `background_pnl_worker.py` PNL-skip alert | Constructed by `monitor.py` without a `telegram_bot` arg → defaults `None` | same, downstream of the above |
| `detect_counter_signals.py` LEGENDARY-reversal alert | `_fire_alert()` only `print()`s; no Telegram API call was ever wired in (comment: "Wire to actual telegram sender if available in maintenance context") | since the function was written — never wired, not a regression |
| `register_signal.py` STR-003-registration alert | Same pattern, same missing wiring | same |
| `analysis/analysis_scheduler.py` | `self.telegram = None # Initialize if needed`, and the module isn't invoked by cron/systemd/daily_maintenance at all currently | not determinable when it stopped being invoked (or if it ever was) |

**Unreported-finding counts, where logs make it determinable:**

- `check_canonical_definitions.py`: **7 violations × ~75 days (2026-06-24 →
  2026-09-07, ~11 weeks) of daily runs** — matches the task's own framing,
  confirmed against the actual commit date.
- `detect_counter_signals.py`: **0** — the alert's own `print()` text
  (`[ALERT] ⚠️ COUNTER-SIGNAL`) does not appear anywhere in
  `logs/daily_maintenance.log`, meaning the trigger condition (a LEGENDARY
  trader reversing an active signal) has never actually occurred in this
  log's retention — this is a determinable zero, not a hidden miss.
- `register_signal.py`: **not determinable** — its `print()` text
  (`[telegram] Would send`, `STR-003 SIGNAL REGISTERED`) does not appear in
  any log file searched in either repo, but this script is event-driven
  from outside daily_maintenance (the trading-swarm orchestrator), and
  whether its stdout is captured to any persistent log at all was not
  established this session.
- `monitor.py`'s elite-trader alert: **not determinable from logs** — no
  code path ever attempted the alert (unlike
  `check_canonical_definitions.py`, which still logs its findings even
  though the send fails), so there is no log trace of how many top-10
  trader trades would have qualified since 2026-01-27. Reconstructing this
  would require replaying historical trader-rank-at-trade-time against the
  `trades` table — not attempted here (would exceed "read the log").
- `analysis/analysis_scheduler.py`: **not determinable** — not invoked
  anywhere found this session, so there is nothing to count.

---

## PART 3 — The noisy ones

**Hourly status report** — over the last 7 days (journalctl,
`polymarket-observer`), **160 hourly-report cycles fired** (≈168 possible
hours — essentially every hour). **Its trigger condition is currently
incapable of suppressing a send**: [V] `_hourly_report_loop` (`:471`)
gates on `metrics.get("status") != "healthy"`, but `_collect_metrics()`
(`:2020`) never sets a key literally named `"status"` — only
`"health_status"`. `dict.get("status")` therefore always returns `None`,
and `None != "healthy"` is always `True`. The "Only send hourly report if
not fully healthy — HEALTHY hours are silent" comment immediately above
the line (`:470`) describes intended behavior the code does not implement.
This is a key-name typo, not a design choice — a different loop in the
same file (`_health_check_loop:291`, `if health['status'] != 'healthy'`)
uses the *correct* key name against a *different* dict
(`health_checker.check_all()`'s own return value) and gates correctly,
confirming the bug is an isolated naming mismatch between two similarly-
shaped-but-distinct metrics dicts, not a systemic problem in this file.
**Content proxy** (exact message text isn't logged, only sent to
Telegram): the per-minute health-check loop, which draws on the same
underlying health checker, logged **9,161 HEALTHY / 290 CRITICAL / 73
WARNING out of 9,524 checks (96.2% / 3.0% / 0.8%)** over the same 7 days —
consistent with the task's own 7-of-7-HEALTHY sample, and with almost all
of the ~160 unconditional hourly sends carrying nothing new.

**SYSTEM DIAGNOSTIC report** — **28 diagnostic cycles fired in 7 days**
(168h / 6h = 28 exactly — confirms **zero gating of any kind**:
`_send_diagnostic_report(report)` is called unconditionally every cycle,
`:3120`, no health check at all; a *second*, additional alert only fires
`if report['overall_status']=='CRITICAL'`, so CRITICAL cycles get two
messages, not one).

- **`integrate_behavioral_elo.py` CRITICAL**: has been true continuously
  since the file's deletion, **2026-07-12** (`61adaf5`) — **~57 days / 8.1
  weeks / ~228 six-hourly cycles** as of today, since `diagnostics.py` has
  had zero commits since before that date (confirmed: `git log --since
  2026-07-12 -- monitoring/diagnostics.py` returns nothing).
- **Database-size WARNING**: fires today at **19,742 MB** (threshold
  10,000 MB) — [V] confirmed live by running the diagnostics check
  directly. **Not determinable how long it's been firing**: the
  message text only ever reaches Telegram (never printed to stdout/
  journal), and the observer's own historical-metrics buffer
  (`PerformanceMonitor.metrics_history`, `diagnostics.py:486`) is
  **in-memory only** and resets on every process restart — there is no
  persisted db-size-over-time record to check against.
- A third warning is present today but not named in the task's sample:
  **"Last trade 1.6h ago"** (threshold >1.5h warning, >3.0h issue,
  `:350-352`) — this one is genuinely time-varying (not chronic like the
  other two) and only just crossed its threshold; not characterized
  further.

**Is either of the two chronic ones something anyone can or should act
on?** Not assessed as a recommendation (out of scope), but factually: the
file-missing CRITICAL reports on a state that was deliberately created and
verified safe 8 weeks ago (Part 4b) — there is nothing to "fix" about the
file itself, only about whether the check should still ask the question.
The DB-size WARNING reports a real, monotonically-growing fact
(`CLAUDE.md` explicitly says never delete/shrink the DB) — there is no
action available that resolves it short of changing the 10 GB threshold
itself.

---

## PART 4 — Two specific things that look wrong

### (a) "ELO coverage: 290.3%"

[V] Reproduced exactly, live:
```
elo_coverage = traders_with_elo / max(1, qualified_traders)
  traders_with_elo   = COUNT(*) FROM traders WHERE comprehensive_elo IS NOT NULL   = 194,415
  qualified_traders  = COUNT(*) FROM traders WHERE total_trades >= 30              =  66,972
  290.3% = 194,415 / 66,972
```

**Root cause: the numerator is not a subset of the denominator's
population — it is nearly the entire `traders` table.** `traders.
comprehensive_elo` carries a schema-level `DEFAULT 1500` [V, `PRAGMA
table_info`]. Every trader row gets `comprehensive_elo = 1500` at
creation regardless of trade count — confirmed directly: 194,415 total
traders in the table, 194,415 with `comprehensive_elo IS NOT NULL` (an
exact match), including rows with `total_trades = 0`. So the "coverage"
metric's numerator counts "has ever been given the default placeholder
value" (structurally ~100% of all traders, always), while its denominator
counts a genuinely restrictive subset (traders with ≥30 trades, ~34% of
the population). The ratio of (everyone) / (a always-smaller subset) is
mathematically guaranteed to exceed 100% under any realistic population
shape where most traders are low-activity — which is the normal case for
a broad market monitor.

**Has this figure ever been correct?** Not proven back to day one (no
historical DB snapshots were checked), but the mechanism is structural,
not transient: `comprehensive_elo`'s `DEFAULT 1500` and the coverage
formula's shape are both long-standing, and `diagnostics.py`'s
`check_elo_calculation_health` has existed since at least 2026-01-27 per
git history. Given the numerator is essentially fixed at "all traders" by
schema default, this metric would only read ≤100% if `qualified_traders`
(≥30-trade traders) were ever a *majority* of the traders table — which
would require most tracked traders to be high-volume, the opposite of what
a broad monitor observes. **The figure's name ("coverage") does not
describe what it measures**: it is not "fraction of qualified traders with
a real ELO score," it is "count of all traders (nearly all of whom just
carry the untouched default) relative to a much smaller reference
population" — a ratio, not a percentage of anything in particular.

### (b) "[ANALYSIS_TOOLS] ELO Integration: File missing at scripts/integrate_behavioral_elo.py"

[V] `scripts/integrate_behavioral_elo.py` does not exist. Git history is
unambiguous:
```
61adaf5  fix: Stage 0c — delete dead Writer C (integrate_behavioral_elo.py)   2026-07-12
```
Full commit message (read directly, not summarized from elsewhere):
verified dormant before deletion — grepped both repos, crontab, and every
systemd timer/service for a live caller; none existed; its only historical
caller (`system_observer.py`) had the exec block fully commented out since
2026-06-05 ("behavioral_modifier written but silently discarded by
`apply_full_elo_modifiers.py`"); the commit removed that dead
disabled-comment block from `system_observer.py` in the same change. Full
test suite passed (116/116) including `test_behavioral_integration.py`,
which asserts DB state directly and never imported the deleted module.

**This CRITICAL is firing about an intentional, already-verified-safe
state**, consistent with `MASTER_HANDOVER_2026-09-05.md §6`'s
`W_BEH=0` (Stage 0b, 2026-07-12 — same day) framing. `monitoring/
diagnostics.py`'s `analysis_scripts` existence-check dict (`:184-191`)
was never updated to drop the now-permanently-absent entry — the check
itself, not the file's absence, is what's stale.

---

## PART 5 — What a strict channel would look like (options, not a recommendation)

**Senders that would send NOTHING under a "only what Oscar would act on"
standard, as currently implemented:**
- `check_canonical_definitions.py`'s alert (credential-broken; even if
  fixed, its *content* — real drift violations — genuinely IS actionable,
  so this one belongs on the "should be fixed to arrive" side, not the
  "should stay silent" side)
- The hourly status report, in its current unconditional form (Part 3)
- The SYSTEM DIAGNOSTIC report's routine 6-hourly cadence, when nothing
  has changed since the last one (its *first* appearance of a new issue
  would be actionable; its 228th repeat of the same stale issue is not)
- `detect_counter_signals.py` / `register_signal.py` stubs — these
  currently send nothing regardless of standard (structurally incapable);
  under a strict standard they'd either stay that way (if judged
  low-value) or need real wiring (if judged worth having)

**Senders with a genuine failure condition already worth alerting on, as
designed (not proposed — these already work correctly):**
- `audit_invariants.py`'s REGRESSION/CRITICAL invariants
- `_health_check_loop`'s non-healthy-transition alert (correctly gated)
- Elite-trader / legendary-trade / insider-detection / consensus alerts,
  where event-driven and currently firing on real detected conditions
  (not deeply re-audited for false-positive rate this session)

**Currently NOT alerted that arguably should be, candidates from Part 2 —
but only judged by whether the underlying finding is itself actionable,
not just whether the pipe is broken:**
- `check_canonical_definitions.py`'s 7 violations — concretely
  actionable (replace 7 literals with existing constants); candidate.
- The elite-trader-alert silence (`monitor.py`) is a *deliberate*
  removal, not a gap — whether it should be re-enabled is a product
  decision (does Oscar want this feed back?), not an alerting-hygiene
  fix; **not a natural candidate for this list** without that separate
  decision.
- `detect_counter_signals.py` / `register_signal.py` stubs — these
  represent unfinished features (never wired), not regressions; whether
  finishing them is worth the effort depends on how often their trigger
  conditions actually occur (Part 2: the counter-signal one has *never*
  fired in the observed log; may not be worth finishing).

**Consolidated overnight digest vs. per-sender alerts — the tradeoff:**
- **Digest**: one message, read once, covers everything — directly
  matches the stated target ("pasting overnight notifications at session
  start is a complete and sufficient status picture"). Cost: it re-couples
  independent failure domains into one message, so a single noisy
  component (e.g., the stale file-missing CRITICAL) could still drown a
  genuinely new finding inside it unless the digest itself is built to
  separate "new since last digest" from "still true from before" —
  which is nontrivial to get right and is exactly the kind of design
  check_canonical_definitions.py's alert lacked (it re-sends the same 7
  violations identically every day rather than reporting only what
  changed).
- **Per-sender alerts** (current architecture, fixed to be conditional):
  keeps each failure domain independent and traceable to its source
  script, but requires each sender to independently implement correct
  gating — this session found at least 3 different gating bugs/gaps
  across a handful of senders, suggesting the current per-sender
  discipline has not held up in practice.
- A middle option not implemented anywhere currently: a digest that
  distinguishes **new** findings from **still-open** ones (e.g., by
  diffing against the previous run's finding-set, similar to how
  `check_canonical_definitions.py` could diff its violation list run over
  run) — this would let a digest stay complete without becoming
  chronically identical to the last one.

This is presented as three options with tradeoffs; which one (or
combination) to pursue is Oscar's decision.

---

## What was not determined

- The exact content (not just cadence) of every historical hourly/daily/
  diagnostic Telegram message — only reachable via Telegram's own chat
  history, not available to this session; all message-content claims here
  are reconstructed from the sending code and from proxy signals (the
  per-minute health-check log).
- Whether `_weekly_report_loop`, `_log_monitor_loop`'s error alerts,
  `_insider_detection_loop`, `_check_consensus_positions/_exits`,
  `_check_legendary_trades`, and `_trend_analysis_loop` are well-gated or
  noisy in practice — each was located and its trigger code read only
  enough to confirm it exists and is conditional in shape; none received
  the same depth of scrutiny as the hourly/diagnostic reports the task
  specifically named.
- Exactly how many top-10-trader trades occurred since 2026-01-27 that
  would have produced an elite-trader alert had `monitor.py`'s `elo_bot`
  been wired — would require reconstructing historical trader rank at
  each trade's timestamp against the `trades` table; not attempted.
- Whether `register_signal.py`'s stub alert's stdout is captured to any
  persistent log anywhere (trading-swarm orchestrator logs were searched;
  none found) — could not confirm zero-vs-uncaptured.
- Exactly when the database-size WARNING (>10 GB) first started firing —
  no persisted historical db-size record exists; the observer's own
  metrics buffer is in-memory and resets on restart.
- Whether `trading-swarm/orchestrator/orchestrator.py`'s `send_telegram`
  is itself well-gated at every call site — only the function's
  credential-loading and its systemd environment mechanism were verified;
  individual call-site trigger conditions were not audited.
- Whether any sender exists that this grep-based inventory missed
  entirely (e.g., a Telegram call embedded inside a string built
  dynamically, which a literal-text search would not catch).
