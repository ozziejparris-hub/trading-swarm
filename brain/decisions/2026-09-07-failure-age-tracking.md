# Failure-age tracking + accepted-failures register

**Date:** 2026-09-07
**Repo:** first-repo (HEAD at start: 51e3b74; prior task committed f63dd5a)
**Builds on:** [[2026-09-07-telegram-remediation]] (bug-only channel, change-detection
gating). That fixed alert *delivery*. This fixes the layer under it: a check could
fail persistently and nothing escalated.

Tagging: [V] verified this session (ran / read directly), [I] inferred.

---

## PROBLEM (restated)

- `check_canonical_definitions.py` exited 1 every day 2026-06-24 → 2026-09-07
  (~75 days). Logged daily, escalated never.
- `test_backtest_window_population.py` fails every run; routinely called "chronic"
  and skipped past. **Nobody decided it was acceptable — it became habit.**

The gap is not "the alert didn't send." It is that the system tolerates a
persistent failure indefinitely with nobody deciding to tolerate it. This work
makes the toleration an explicit act and makes failure *age* visible.

---

## PART 1 — FAILURE-AGE TRACKING

### New shared module: `monitoring/failure_age.py` [V]

stdlib-only (imports nothing from first-repo), so both consumers — a cron
subprocess and the long-running observer daemon — can import it without
dependency risk. Pure functions except `load_state` / `save_state` /
`load_register`; `load_register` **never writes**.

**State-file schema (v2)** — one file per check, same paths as the 2026-09-07
change-detection signature files (upgraded in place):

```json
{
  "schema_version": 2,
  "check": "canonical_definitions",
  "updated_at_utc": "2026-09-07T06:00:00+00:00",
  "prior_state_status": "ok",          // ok | missing | corrupt | pre_age_schema
  "findings": {
    "<finding key>": {
      "first_seen_utc": "2026-09-07T06:00:00+00:00",
      "last_seen_utc":  "2026-09-07T06:00:00+00:00",
      "age_unknown_at_first_seen": false,
      "reported_at_utc": "2026-09-07T06:00:00+00:00" | null,
      "review_due_alerted_on": "2026-09-07",           // only on register-accepted keys
      "prior_episodes": [ {first_seen_utc, last_seen_utc, reported_at_utc} ]  // only if it returned
    }
  },
  "resolved_history": {
    "<finding key>": [ {first_seen_utc, last_seen_utc, reported_at_utc}, ... ]   // last 5 episodes
  }
}
```

- **Age** = `now - first_seen_utc` (whole days), computed from the timestamp,
  never from the file's mtime. [V — test 3b]
- **Survives restarts**: the state lives in the file; a fresh process reloads it
  and continues the age clock. [V — test 3a/3b, explicit file round-trip]
- **Disappear → return = NEW first_seen.** On disappearance the finding's
  `{first_seen,last_seen,reported_at}` is pushed to `resolved_history[key]`
  (capped at 5). On return it is classified `new` **and** `returned`, gets
  today's `first_seen`, and the earlier episode is attached as `prior_episodes`
  for context. The age clock restarts — a finding that was fixed and regressed
  is a new problem, not a resumption. [V — test 7a–7d]
- **Robust to a missing / corrupt / old-schema file.** `load_state` never
  raises. Missing → `prior_state_status: "missing"`. Unreadable / wrong shape →
  the file is copied aside as `<name>.corrupt-<UTC>` and `prior_state_status:
  "corrupt"`. A pre-age-schema flat file (`{"violations": [...]}` /
  `{"issues": [...]}`) → `prior_state_status: "pre_age_schema"`. In every
  non-`ok` case, `reconcile` stamps **today** as `first_seen` for all current
  findings and sets `age_unknown_at_first_seen: true` — recorded in the file,
  never back-dated. [V — tests 4, 5, 6]

### No invented history [V]

The seven violations already present on the first run under this schema get
2026-09-07 as `first_seen`, each flagged `age_unknown_at_first_seen: true`, and
the file records `prior_state_status: "pre_age_schema"`. An invented historical
timestamp would be exactly the unsourced-number failure this project has been
burned by (MASTER_HANDOVER_2026-09-05 §8). The one-time migration message says
`tracking (age unknown) … counting from 2026-09-07`, not `! NEW`. [V — test 6d]

### Stable finding keys — STOP condition checked, not triggered [V]

| Check | Key | Line-number-independent? |
|---|---|---|
| canonical | `canonical_definitions::<relpath>::<rule message>` (`finding_keys()`) | **Yes** — line number is deliberately excluded; the rule message is the templated description, stable while the violation is the same kind in the same file. [V — test 13a] |
| diagnostic | `diagnostic::issue::<text>` / `diagnostic::warning::<text>`, numeric tokens normalised to `#` via `_normalize_finding` | **Yes** — no line numbers involved; the DB-size byte count etc. is normalised so a drifting number does not reset the age. [V — test 11, and pre-existing T1g] |

Neither key changes when a line shifts. **STOP condition "cannot produce a stable
finding key" does not apply.**

---

## PART 2 — ACCEPTED-FAILURES REGISTER

### `config/accepted_failures.json` [V]

JSON (no yaml dependency; matches `config/elo_update_settings.json`). Committed
**seeded empty**. A long `_README` block in the file states the semantics and
that only Oscar edits it.

```json
{
  "schema_version": 1,
  "_README": [ "...semantics, and: entries are added ONLY by Oscar, by hand..." ],
  "accepted": [
    {
      "finding_key":  "<matches a key in the check's state-file 'findings'>",
      "accepted_by":  "Oscar",
      "accepted_on":  "2026-09-07",
      "reason":       "...",
      "review_by":    "2026-10-15",
      "resolution_hint": "..."          // optional
    }
  ]
}
```

`load_register` validates each entry (all five required fields present and
non-empty; `review_by` parses as `YYYY-MM-DD`); a bad entry is skipped with a
stderr note and the rest still load. A missing file → `{"entries": {}}`. A
corrupt file → `{"entries": {}}`, file left untouched. **It is opened read-only
and never written by any code path.** [V — test 12a–12d]

### Semantics (as implemented) [V]

| State of a failing finding | Behaviour |
|---|---|
| No register entry | **UNEXPECTED** — alerts (as `! NEW` the first time Oscar would see it; then silent while unchanged). Appears in Telegram *and* the state file. |
| Register entry, `now ≤ review_by` | **EXPECTED** — never appears in any message; tracked in the state file with its age. [V — test 2a] |
| Register entry, `now > review_by` | **REVIEW DUE** — alerts again as a `review due` line, distinct from `! NEW`. Re-alerts at most once per UTC calendar day until Oscar bumps `review_by` (a deliberate act) or the finding clears. [V — test 2b–2e] |
| Was reported, now cleared, not an accepted key | one `resolved … was failing Nd` line. [V — test 8a] |
| Cleared but Oscar was never told | silent — no message. [V — test 8b] |

Nothing automated writes to the register. The check reads it; that is all.

### Interaction with each check's existing change-detection — STOP condition checked, not triggered [V]

- **Canonical** (`should_alert` was: non-empty set AND signature changed).
  With an **empty** register (production seed) the new gate reproduces the old
  behaviour exactly: a genuinely new violation → alert; an unchanged already-
  reported set → no alert; a violation clearing → a "resolved" alert (the old
  T3f case). It only *extends* it (review-due). **No conflict.**
- **Diagnostic** (was: `overall_status == 'CRITICAL'` AND signature changed).
  The `CRITICAL` gate is **kept** as an outer condition on producing a message;
  within it, the tracker decides. Warnings are age-tracked on disk but are not
  in `alertable_keys`, so they never trigger a send on their own — the existing
  design. Recovering out of `CRITICAL` still produces no "all clear" (the
  message is only built when `overall_status == 'CRITICAL'`), preserving the
  deliberate 2026-09-07 tradeoff. **No new design decision was forced; the
  existing decisions were preserved.**

### Seed entry: none — as instructed

The register is committed empty. Populating it is Oscar's explicit act; CC
pre-filling it would reproduce the silent-tolerance failure in a new form.
**Proposed entries, for Oscar to accept or reject:**

1. **`canonical_definitions::scripts/characterize_legendary_overlap_recompute.py::Python comparison `geo_elo_active >= 2175` — replace with cd.GEO_ELO_* constant`**
   - reason: DORMANT single-use characterisation script (see
     [[2026-09-07-canonical-violations-part2-fix.md]] Part 3); the `< 2175`
     compare is a deliberate probe of the *legacy* raw-`geo_elo` LEGENDARY
     notion, not gate logic. Oscar has three options on the table (fix the
     literal / exempt in the checker / leave) and has not chosen.
   - review_by: **2026-10-15** (forces the choice within ~5 weeks).
   - resolution_hint: pick one of the three options in that doc's Part 3.

2. **`run_tests::test_backtest_window_population.py`** *(key is provisional —
   `run_tests.py` is not yet wired for age-tracking; see Part 4)*
   - reason: fails every run; the T2/T2b/T2c/T2d/T2f assertions hardcode market
     counts against a frozen `backtest_population_snapshots` row that drifts as
     trades accrue. Needs diagnosis (separate work — explicitly out of scope
     here).
   - review_by: **2026-10-01** (shorter — this one is a real test regression,
     not a style nit, and should not sit).
   - resolution_hint: decide whether the frozen snapshot or the test's expected
     counts are authoritative, then re-baseline or fix the population query.

Both are *proposals*. Neither is in the committed file.

---

## PART 3 — MESSAGE FORMAT

`fa.render_message(check_title, decision, new_state, now, state_path)` → a
plain-text string or `None`. Rules enforced: ≤ 15 lines (hard cap with a
"… truncated — see <file>" fallback); ≤ 6 findings listed per section then
"… and N more — see <file>"; changes first, `! NEW` before everything else;
age shown on every non-new line; register-accepted-and-in-window findings never
appear; one severity marker (`!`) and only on `NEW` lines; no counts, no
component tables, no "healthy" text; `None` when there is nothing to say so the
caller sends nothing at all.

### Worked examples (rendered by the real code) [V]

**Scenario 1 — nothing wrong**

```
(no Telegram message is sent — render_message returned None)
```

**Scenario 2 — one new failure**

```
canonical drift — 2026-09-07

! NEW  scripts/new_report.py — SQL string contains `geo_elo >= 1400` — use cd.LEGENDARY_GATE_WHERE or …

state: data/.canonical_drift_state.json
```

**Scenario 3 — one new failure, plus two registered-and-accepted (within review window)**

```
canonical drift — 2026-09-07

! NEW  scripts/fresh.py — Python comparison `geo_elo_active >= 1800` — replace with cd.GEO_ELO_* const…

state: data/.canonical_drift_state.json
```

Identical to Scenario 2. The two accepted findings
(`…scripts/legacy_a.py…geo_elo >= 2175…` and
`diagnostic::issue::[BACKTEST] population snapshot drift…`) do **not** appear in
the message. They are in the state file with their `first_seen` / age; Oscar sees
them there, not in Telegram.

*(A message that also carried ongoing-but-already-reported unexpected findings
would add one line: `also still failing: <short> 40d; <short> 12d`. A review-due
finding would add: `review due  <short> — failing 74d`. A cleared finding:
`resolved  <short> — was failing 12d`. None of those are in the three scenarios
above.)*

---

## PART 4 — WHAT WAS WIRED

| File | Change |
|---|---|
| `monitoring/failure_age.py` | **new** — the shared mechanism (load/save state, reconcile, load_register, evaluate, render_message, mark_reported) |
| `config/accepted_failures.json` | **new** — register, seeded empty, with an in-file README |
| `scripts/check_canonical_definitions.py` | `sys.path` + `import monitoring.failure_age`; removed `violation_signature`/`load_previous_signature`/`save_signature`/`should_alert`; added `finding_keys()`; `main()` now reconciles + evaluates + renders + persists v2 state; `send_telegram_alert(message:str) -> bool`; `_send_telegram_async` switched to plain text (message contains `>=`, which HTML mode breaks) |
| `monitoring/system_observer.py` | `from . import failure_age as fa`; removed `_diagnostic_signature`/`_should_send_diagnostic_report`/`_load_diagnostic_signature`/`_save_diagnostic_signature`; kept `_normalize_finding` (key builder); added `_diagnostic_finding_keys` + `_evaluate_diagnostic`; diagnostic loop now sends the terse failure-age message under the retained `overall_status == 'CRITICAL'` gate; `_send_diagnostic_report` retained but marked NOT CURRENTLY CALLED |
| `tests/test_failure_age_tracking.py` | **new** — 38 assertions (see Reproducibility) |
| `tests/test_telegram_alert_gating.py` | trimmed to the hourly-report section (§1) + a `_normalize_finding` structural check; §2/§3 coverage moved to `test_failure_age_tracking.py` |

**Not wired (deliberately, per scope): every other check.** Age-tracking is
proven on the two checks that already persisted state. Candidates for the same
treatment later:

| Candidate | Why | Note |
|---|---|---|
| `scripts/audit_invariants.py` (`--alert`) | Sends a REGRESSION-tier invariant list every daily-maintenance run; [[2026-09-07-telegram-remediation]] explicitly left "does it re-send identical regressions daily?" unassessed. Stable keys already exist (invariant names). | Highest-value next target — it is the current daily-noise source. |
| `run_tests.py` per-file failures | `test_backtest_window_population.py` is the motivating example: a test that fails every run and gets skipped past. Needs `run_tests.py` to emit a stable per-file (ideally per-assertion) key. | Enables proposed register entry #2. |
| `daily_maintenance.py` per-step non-zero exits | A step failing every day (as the canonical check did) should escalate by age, not be a silent log line. | Wrap the step runner; key = step name. |
| `scripts/fast_resolution_check.py`, `reconcile_geo_resolved_counts.py` | Data-quality steps in daily maintenance that can emit findings. | Only if they start emitting structured findings. |
| Observer **hourly report** / **health-check loop** | Transient by nature (a momentary health status), not a persistent "finding" with an age. | Probably NOT a fit — noted so it is not reflexively added. |
| trading-swarm `orchestrator.py` alert sites | Different repo; its own send-gating was never fully audited. | Out of scope; flagged. |

### Re-run of the real canonical check after wiring [V]

```
$ python3 scripts/check_canonical_definitions.py
[check_canonical_definitions] DRIFT DETECTED — 1 violation(s):
  scripts/characterize_legendary_overlap_recompute.py:84  Python comparison `geo_elo_active >= 2175` …
[check_canonical_definitions] prior state was 'pre_age_schema' — every current finding seeded
    with today's date; its true age is unknown (flagged in the state file).
--- message ---
canonical drift — 2026-09-07

tracking (age unknown)  scripts/characterize_legendary_overlap_recompute.py — Python comparison `geo…

state: /home/parison/projects/first-repo/data/.canonical_drift_state.json
---------------
EXIT=1
```

The committed `data/.canonical_drift_state.json` was **restored to its v1 shape**
after this verification run — the schema migration (and the one-time
`tracking (age unknown)` baseline message, under `--alert`) will happen on the
next real `daily_maintenance.py` run, in production, where Oscar sees it. The
observer's `data/.diagnostic_report_state.json` does not exist yet and will be
created v2 on the observer's first post-restart diagnostic cycle.

**Observer restart:** `monitoring/system_observer.py` changes are inert until
`polymarket-observer.service` is restarted (the running process holds the old
code). `check_canonical_definitions.py` needs no restart (fresh subprocess per
cron run). Restarting the observer is Oscar's call — flagged, not done.

---

## PART 5 — CORRECTION TO 2026-09-07-canonical-violations-part2-fix.md

That document's "what was not determined" section states the
`check_canonical_definitions.py` `load_dotenv()` gap is "still unfixed." **That
is wrong.** It was fixed earlier the same day in **first-repo `51e3b74`** — the
commit that document cites as its own starting HEAD. `git log -S load_dotenv --
scripts/check_canonical_definitions.py` returns exactly `51e3b74`; the file
carries `from dotenv import load_dotenv; load_dotenv("/home/parison/.env_trading")`
inside `send_telegram_alert()` since that commit. [V]

A dated amendment has been appended to
`brain/decisions/2026-09-07-canonical-violations-part2-fix.md` (amendment
convention: append, do not rewrite), and the erroneous bullet corrected in place
with a marker pointing to the amendment.

**This is at least the fourth instance** of the project's own standing lesson —
*"Chat-Claude's premises enter the record and must be verified, not inherited"*
(MASTER_HANDOVER_2026-09-05 §8; prior instances there include the 2026-09-04
lineage-prediction mix-up). The premise "the gap is unfixed" came from the task
framing of the predecessor task and was carried into the decision document
without being checked against `51e3b74`'s actual diff.

---

## REPRODUCIBILITY

`tests/test_failure_age_tracking.py` — **38 assertions, all pass** via
`run_tests.py` (not bare pytest). Covers every item the task named:

- a new finding alerts (1a/1b); an unchanged already-reported finding does not (1c)
- a registered finding does not alert (2a); past its review date it does (2b/2c),
  once per day (2d), again the next day (2e)
- age computed correctly across a simulated restart — explicit file round-trip,
  30-day gap (3a/3b)
- a corrupt state file degrades safely — no raise, quarantined, findings reseeded
  + flagged, file rewritten valid (4a–4d); missing file (5a/5b)
- pre-age-schema migration stamps today, flags age-unknown, no back-dating (6a–6d)
- disappear→return = fresh first_seen, prior episode kept (7a–7d)
- resolved-finding messaging + negative control (8a/8b)
- nothing to report → no message (9a)
- 15-line cap with 40 findings (10a/10b)
- diagnostic warnings tracked on disk but never alertable (11a–11c)
- register robustness + never written (12a–12d)
- line-number-independent keys (13a)

Full `run_tests.py` (`--skip=test_behavioral_integration.py`, the documented
cold-cache hang): **21 files, 20 pass, 339,824 assertions pass.** The sole
failing file is `test_backtest_window_population.py` — the chronic, pre-existing,
unrelated failure (T2/T2b/T2c/T2d/T2f, hardcoded market counts vs a drifting
`backtest_population_snapshots` row). Unchanged by this work; **not** caused by
it. `test_match_control_determinism.py` 6/6 (confirms `system_observer` imports
cleanly with the new `failure_age` dependency).

---

## WHAT WAS NOT DETERMINED

- **Whether `_send_diagnostic_report` (now uncalled) should be deleted.** Kept
  with a NOT-CURRENTLY-CALLED docstring, matching the repo's convention for
  `_daily_report_loop` etc. Its component-breakdown + fix-engine format may be
  wanted on a non-Telegram channel later; if not, it and `self.fix_engine` are
  dead and can go.
- **Whether the observer should be restarted now** to load the new diagnostic
  path. Inert until then. Oscar's call.
- **Whether "review-due re-alerts once per day forever until Oscar acts" is the
  right cadence.** It is a deliberate choice (persistent escalation without
  6-hourly spam); an alternative is "alert once, then silent until review_by is
  bumped." Not hard to change; not decided by anyone but implemented as the
  former.
- **Whether the diagnostic report's `resolved`/all-clear suppression is still
  wanted** now that age-tracking exists. Preserved the 2026-09-07 decision
  (no all-clear); revisiting it is a separate call.
- **Whether `run_tests.py` / `audit_invariants.py` get this treatment** and on
  what schedule — Part 4 lists them as candidates; not built.
- **The true age of the one currently-tracked canonical finding**
  (`characterize_legendary_overlap_recompute.py:84`). It has been failing since
  at least 2026-08-18 (file creation) but the state file will honestly say
  `age_unknown_at_first_seen: true, first_seen 2026-09-07`. Not back-dated.
- **Whether any register entry will ever be added.** The file is committed
  empty by design; if Oscar never populates it, every failing check stays
  UNEXPECTED and alerts — which is the safe default.
