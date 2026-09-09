# Final Telegram Cut — strict

**Oscar's decision:** keep as little as possible; silence everything that
does not inform a current decision.

**Audit basis:**
`brain/decisions/2026-09-09-telegram-senders-audit-db-audit-and-legendary.md`
(committed to trading-swarm as `51418a5` before this task — the task's
"uncommitted" note pre-dated that commit).

All code changes in first-repo (one commit). READ-ONLY items recorded as
known, not repaired. Tests via `run_tests.py`, not bare pytest.

Tagging: **[V]** verified this session (ran / read directly), **[I]** inferred.

---

## STOP CONDITIONS — neither triggered

- **No disabled sender suppresses a genuinely actionable alert.** The four
  silenced items are: an always-firing content-free status report, a
  lifecycle announcement, performance observations mislabelled as errors,
  and an alert for position-taking in a retired signal era. Each is argued
  below. Everything that pages on a real incident (health regression,
  monitoring freeze, ELO staleness, canonical drift, new CRITICAL
  invariant, genuine error-log lines, auto-restart failure) is untouched.
- **The failure-age integration does not break `audit_invariants.py`'s
  credential self-load. [V]** A fresh `env -i` process (cron has no
  exported env) running exactly what `main()` does —
  `load_dotenv("/home/parison/.env_trading")` — picks up
  `telegram_alerts_token` (46 chars) and `telegram_chat_id`. `main()` is
  unchanged: it still self-loads before `run_audit()`, and still
  `sys.exit(2 if n_crit > 0 else 0)`.

---

## KEPT — one alert

**`audit_invariants::pending on resolved non-gap geo/elections markets`**
— the only one of the five daily REGRESSION rows that still alerts. Kept
because it is growing (~+600/month) and has a known, unwired fix
(`backfill_trade_results_geo.py`, never added to `daily_maintenance.py`).

Implemented by putting `scripts/audit_invariants.py`'s `--alert` path
under `monitoring/failure_age.py` (first-repo `f6a8b88`), the same pattern
already used by `check_canonical_definitions.py` and the observer's
diagnostic report:

| change | detail |
|---|---|
| `finding_keys(results)` added | one key per REGRESSION/CRITICAL result: `audit_invariants::<invariant name>`. Count deliberately excluded from the key, so day-to-day drift (24,103 → 24,644) does not read as a NEW finding and reset the age — same reasoning as `check_canonical_definitions.finding_keys()` excluding line numbers. |
| `STATE_PATH` = `data/.audit_invariants_state.json` | per-finding `first_seen` / `last_seen`, survives restarts. Seeded this session (`prior_state_status: "missing"` → all five findings stamped 2026-09-09, `age_unknown_at_first_seen: true`, `reported_at_utc: null`). Committed, matching the tracked `data/.canonical_drift_state.json`. |
| `run_audit()` tail | `reconcile → load_register → evaluate → render_message`; on `--alert`, send only if `render_message` returns non-None, then `mark_reported`. The stdout summary table and the JSON report are unchanged — this gates the **alert**, not the audit. |
| `send_telegram_alert(message: str)` | rewritten to take a pre-rendered plain-text message (was `(results, summary)` building an HTML block). Plain text — the message contains `>=` / a bare path. |
| Tier-1 CRITICAL exit code | untouched: `sys.exit(2)` still aborts `daily_maintenance.py` on an impossible-state finding, independent of the alert gate. An un-accepted CRITICAL also still alerts (test 6a). |

**Behaviour now [V]** (ran `python3 scripts/audit_invariants.py`): five
REGRESSIONs detected, message body contains **only** the geo/elections
pending line; the other four are tracked in the state file and produce
**no alert**.

### Register entries added to `config/accepted_failures.json`

Four entries, `accepted_by: Oscar`, `accepted_on: 2026-09-09`. Finding
keys taken verbatim from the state file that `finding_keys()` wrote — not
hand-typed. `reason` drawn from the audit document's §1.3 per-invariant
verdicts (quoted / condensed, not invented).

| finding_key (suffix) | review_by | reason (audit doc §1.3) |
|---|---|---|
| `pending on resolved non-gap markets (flagged traders)` | 2026-12-01 | within-cycle backlog gauge (audit @ step 7 vs `evaluate_new_trader_results.py` @ step 21); oscillates 0↔100k's, no trend, self-healing; floor 0 aspirational, never held; root-caused in `2026-08-19-pending-invariant-regression.md` Q4 |
| `timestamp mixed formats (per-column breakdown)` | **2026-10-15** | `FLOOR_TS_TOTAL=24996` is a stale point-in-time capture (`b30c5ff`, "until Teardown 3" — never happened); the real growing regression is recorded (`2026-08-30-end-to-end-verification.md` #8) with its driver now pinned to `backfill_market_dates.py`'s `.isoformat()`. Shorter window: growing, driver known. |
| `data_source not in canonical set (write-path regression)` | 2026-12-01 | closed historical set — 178 markets + 399 trades, all `data_source='gap_recovery_20260811'`, a literal never added to `cd.DATA_SOURCE_MARKETS`/`DATA_SOURCE_TRADES`; recorded `2026-08-30` #10 (COSMETIC); floor 0 is correct; check re-measures (stepped 580→577 on 08-17) |
| `total_invested vs SUM(entry_total_cost) mismatch >5%` | 2026-12-01 | reconciliation lag, not corruption; recorded `2026-08-30` #11 (COSMETIC, "no identified consumer depends on this being exact"); floor 0 aspirational Tier-3, Teardown never scheduled; check re-measures, holds flat for weeks then steps |

Each has an optional `resolution_hint` pointing at the concrete fix.

### Control test (as done for the 2026-09-07 canonical entry, `f882a86`) [V]

For each of the four keys, with `finding_keys()` output fed through
`reconcile`/`evaluate`:

| register | `pending geo` (kept) | the four accepted |
|---|---|---|
| **live** (`config/accepted_failures.json`) | in `report_new`, in message | **not** in `report_new`, **not** in message |
| **empty** `{"entries": {}}` | in `report_new`, in message | **all four** in `report_new`, in message |

The kept key alerts under both registers — confirming suppression comes
from the register, nothing else. An accepted key past its `review_by`
produces a `review due` message (test 5a).

---

## SILENCED — everything else

Reversible, dated comment + re-enable note, the `138c03b` pattern
(comment out, don't delete; leave a `# Reversible:` block).

### 1. Hourly status report — `monitoring/system_observer.py`

The `if self._should_send_hourly_report(metrics): await
self.telegram.send_hourly_report(metrics)` block inside
`_hourly_report_loop` is commented out. The gate fires on
`error_count > 0`, effectively always true, and the report carries no
actionable content (2026-09-07 audit Part 3). **The loop still runs** —
the monitoring-freeze alert, `_check_consensus_positions/_exits`, and
`_check_elo_staleness` are all inside it and untouched. `run()`'s startup
banner updated to say so. Reverse: uncomment the two lines.

### 2. "SYSTEM OBSERVER STARTED" — `monitoring/system_observer.py`

`await self.telegram.send_startup_notification()` in `run()` commented
out. Lifecycle announcement, not a finding. Reverse: uncomment the one
line.

### 3. "COMPONENT ERROR: Unknown" slow-trade notices

`monitoring/background_pnl_worker.py` — the `elapsed > 5` branch changed
from `self.logger.warning("Slow: %s — %d trades took %.1fs", …)` to
`self.logger.info(…)`. **Mechanism [V]:** the observer's `_log_monitor_loop`
→ `ErrorParser.parse_log_line` matches on `LEVEL_PATTERN =
r'- (ERROR|WARNING|CRITICAL) -'` and relays anything it matches to
Telegram, classifying "Slow:" as component `Unknown`. At `INFO` the line
no longer matches, so it stays in the log but off the alert channel. The
sibling `Timeout:` warning and the `_record_failure` alert are untouched.
Reverse: restore `.warning`.

### 4. `_check_legendary_trades()` — `monitoring/system_observer.py`

The `await self._check_legendary_trades()` call inside
`_hourly_report_loop` is commented out. **The function is left fully
intact** for reversibility — only the call site is disabled. It works
correctly (gate reads `geo_elo_active >= cd.GEO_ELO_LEGENDARY`, per the
audit) but reports position-taking from the retired STR-003 signal era
and informs no current decision. Reverse: uncomment the one line.

### NOT disabled (explicit)

- `_health_check_loop`'s non-healthy-transition alert — untouched.
- `check_canonical_definitions.py`'s drift alert — untouched (already
  failure-age gated, 1 accepted finding).
- The comprehensive diagnostic report's CRITICAL + change-gated send —
  untouched (already failure-age gated; current `overall_status` is
  WARNING, so it sends nothing anyway).
- Monitoring-freeze alert, consensus position/exit alerts, ELO-staleness
  alert — untouched; each fires only on a real detected condition and was
  not in scope.

---

## DO NOT FIX — recorded as known

| item | status |
|---|---|
| The `ELO:` line in the legendary alert showing `comprehensive_elo` next to a `geo_elo_active`-derived badge | moot — alert is now off. Left as-is. |
| `traders.avg_roi` = unweighted mean of per-position `roi_percent` (structurally broken, same family as "290.3% ELO coverage") | not repaired. |
| The four accepted invariants' underlying problems (pending-flagged cadence, timestamp `.isoformat()` driver, `gap_recovery_20260811` literal, reconciliation lag) | not repaired — each has a `resolution_hint` in the register and a `review_by`. |
| `FLOOR_TS_TOTAL`'s stale 2026-06-18 point-in-time capture | not repaired — folded into the timestamp entry's `review_by 2026-10-15`. |

---

## VERIFY — what Telegram sends over a typical 24 h

**Expectation: nothing, most days.**

| sender | cadence | sends when | typical 24 h |
|---|---|---|---|
| `audit_invariants.py --alert` | daily (maintenance ~06:00 UTC) | a REGRESSION/CRITICAL invariant is newly-failing & un-accepted, OR an accepted one is past `review_by`, OR a previously-reported one resolves | **nothing** — 4 of 5 accepted; `pending geo` sends **one** transitional "tracking (age unknown)" line on the first post-change `--alert` run, then silent |
| `check_canonical_definitions.py --alert` | daily | drift beyond the 1 accepted finding | nothing |
| observer — health-check loop | 60 s | transition to non-healthy | nothing (healthy ~96% of the time) |
| observer — diagnostic report | 6 h | `overall_status == CRITICAL` AND finding-set changed | nothing (status is WARNING) |
| observer — monitoring-freeze | hourly | monitor silent > 45 min | nothing |
| observer — ELO staleness | ≤ 6 h | ELO > 7 d (WARNING) / > 14 d (CRITICAL) stale | nothing (refreshed weekly + daily) |
| observer — consensus position/exit | hourly | smart-money consensus detected in geo/elections | occasional, event-driven; not in scope |
| observer — log-monitor error alerts | ~2 s | an ERROR/CRITICAL/WARNING log line (minus the now-INFO "Slow:" line) | only on a real error |
| `background_pnl_worker` PNL-skip alert | continuous | — | never (`telegram_bot` is `None`, pre-existing) |

**Live senders after this cut, and what each alerts on:**

1. **DB audit invariants** — a new/un-accepted failing invariant, an
   accepted one going past review, or a reported one resolving. Currently:
   only `pending on resolved non-gap geo/elections markets`.
2. **Canonical drift check** — a new hardcoded-threshold violation beyond
   the one accepted until 2026-10-15.
3. **Observer health-check loop** — the monitored service becoming
   non-healthy.
4. **Observer diagnostic report** — a CRITICAL diagnostic finding that is
   new since the last report.
5. **Observer monitoring-freeze** — the 15-min monitor going silent.
6. **Observer ELO-staleness** — ELO scores aging past 7 / 14 days.
7. **Observer consensus position/exit** — a detected smart-money
   consensus in geo/elections markets.
8. **Observer log-monitor** — genuine ERROR/WARNING/CRITICAL log lines.
9. **Observer auto-restart failure** — `systemctl restart` of the monitor
   failing.

Silenced and no longer live: hourly status report, "SYSTEM OBSERVER
STARTED", slow-trade "COMPONENT ERROR: Unknown", legendary-trade alert.

---

## TESTS

`run_tests.py` (skipping the documented always-hangs
`test_behavioral_integration.py`): **22 files, 22 passed, 339,848
assertions, 0 failed.** [V]

- **`tests/test_audit_invariants_failure_age.py`** (new, 20 assertions):
  `finding_keys()` returns a key only for REGRESSION/CRITICAL and it is
  name- not count-based; a count change keeps the age (finding stays
  "ongoing", not "new"); a newly-failing invariant alerts; an
  already-reported one does not; with the live register only the kept
  invariant alerts and each of the four accepted ones suppresses; with an
  empty register all five would alert (the control); an accepted finding
  past `review_by` alerts as "review due"; an un-accepted CRITICAL still
  alerts.
- **`tests/test_failure_age_tracking.py:308`** fixed (was 38 assertions,
  now 41). The old `12d` hard-asserted `fa.load_register() == {"entries":
  {}}`, which broke when the first register entry landed 2026-09-07 —
  the same brittle-literal anti-pattern removed from
  `test_backtest_window_population.py`. Replaced with: the register loads
  with the expected **shape** (`{"entries": dict}`), every entry
  `load_register` returned is well-formed (no entry silently dropped —
  loaded count == raw `accepted` count), every entry has the required
  string fields and parseable `accepted_on`/`review_by`, and keys are
  unique and namespaced. No literal.
- `test_telegram_alert_gating.py` (7/7) — unaffected; the
  `_should_send_hourly_report` gate function is untouched, only its call
  site is commented out.
- `test_backtest_window_population.py` now passes (20/20) — fixed
  earlier by `f415faa`, unrelated to this task.

---

## WHAT WAS NOT DETERMINED

- **Whether the one transitional `pending geo` alert on the next
  `--alert` run is desirable or should be pre-suppressed.** It is a
  one-time artefact of seeding the state file today (`age_unknown_at_first_seen`).
  Left to fire once: it is honest ("tracking started 2026-09-09") and
  after it `mark_reported` silences the finding until it resolves or a
  new invariant fails. Not pre-marked-reported.
- **Live end-to-end Telegram send** was not exercised (would spam the
  channel). The credential path and the gate logic were verified
  in-process; the actual `bot.send_message` call is unchanged from the
  working `check_canonical_definitions.py` sender.
- **The observer changes require a service restart to take effect**
  (`polymarket-observer.service`). Not restarted this session — same
  posture as the 2026-09-07 remediation (do not restart a live
  production service without asking). Until restart, the running process
  keeps the old behaviour.
- **Consensus position/exit alert false-positive rate** — not assessed;
  left live per scope, flagged here as the most likely remaining source
  of non-incident Telegram traffic.
- **`check_canonical_definitions.py`'s cron credential path** — reported
  fixed by `51e3b74`; not re-verified this session.
- **Whether `data/.audit_invariants_state.json` should be gitignored
  instead of committed.** Committed to match the tracked
  `data/.canonical_drift_state.json`; the sibling
  `data/.diagnostic_report_state.json` is currently untracked, so
  practice is inconsistent. Chose the closest precedent.

---

## FILES CHANGED (first-repo, one commit)

- `scripts/audit_invariants.py` — failure-age integration, `finding_keys()`,
  `send_telegram_alert(message)` rewrite, docstring.
- `config/accepted_failures.json` — 4 `audit_invariants::` entries, README
  updated.
- `monitoring/system_observer.py` — hourly-report send, startup
  announcement, `_check_legendary_trades()` call site: all commented out
  with dated reversible blocks; startup banner updated.
- `monitoring/background_pnl_worker.py` — "Slow:" line `warning` → `info`.
- `tests/test_audit_invariants_failure_age.py` — new (20 assertions).
- `tests/test_failure_age_tracking.py` — `12d` brittle-literal fix (+3
  assertions).
- `data/.audit_invariants_state.json` — new, seeded 2026-09-09.

Audit document `2026-09-09-telegram-senders-audit-db-audit-and-legendary.md`
already committed to trading-swarm as `51418a5`.

*Generated 2026-09-09.*
