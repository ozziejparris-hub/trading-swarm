# Reproducibility + Canonical-Adherence Enforcement — Part 1 Diagnosis, STOP

**Scope:** read-only. Diagnoses why `check_canonical_definitions.py` fails
chronically (Part 1 of the task), as instructed, before building anything on
top of it. **This document reports a STOP: Part 1 found the failure is a
real canonical violation, not a stale rule — the task's own stop condition
triggers here.** Parts 2 (canonical-call adherence check), 3
(decision-document reproducibility check), and 4 (wiring) were **not
attempted**. Canonical definitions were not revised, re-derived, or
reopened. No bypassing script was touched. No historical document was
amended.

Tagging: [V]=verified this session (code/log read or run directly),
[I]=inferred.

---

## VERDICT

**`check_canonical_definitions.py`'s failure is real, not stale, not a false
positive.** It correctly detects 7 genuine hardcoded-threshold violations
across 6 `trader_skill_metric_v2*.py` scripts plus
`characterize_legendary_overlap_recompute.py` — the exact population
`MASTER_HANDOVER_2026-09-05.md` finding #7 already named. The canonical
constant (`GEO_ELO_LEGENDARY = 2175.0`) has **not** drifted from the
hardcoded value, so this is not a stale-threshold false alarm; it is a
structural bypass of the constant that happens to currently agree with it —
exactly the kind of silent-drift risk the check exists to catch.

**Separately, and not asked for, but explaining why this has gone
unactioned for weeks: the check's own Telegram alert path is broken by a
missing `load_dotenv()` call**, unrelated to the 7 violations themselves.
The violations have been detected and logged every single day since the
check was wired in (`419d223`, 2026-06-24) but have never once reached
Telegram — the only place a human would see them is a 43MB rotating log
file, which is why the 2026-09-07 status check is the first record of
anyone actually reading the violation list rather than just the exit code.

Per the task's own stop condition — **"Part 1 finds
check_canonical_definitions.py's failure is a real canonical violation
rather than a stale rule — that is a finding for Oscar before anything is
built on top of it"** — this document stops here.

---

## PART 1 — What it checks, why it fails, real vs. stale vs. false-positive

### 1.1 What it checks [V — read the AST visitor directly]

`scripts/check_canonical_definitions.py`, `DriftVisitor(ast.NodeVisitor)`,
243 Python files:

1. **`visit_Compare`** — flags `geo_elo` / `geo_elo_active` compared
   (`>=`) against a raw numeric constant in `GATE_THRESHOLDS = {2175, 1800,
   1400, 1000, 500}` — Python-level, e.g.
   `geo_elo_active >= 2175`.
2. **`visit_Constant`** (string literals) — regex
   `geo_elo(_active)? >= (threshold)` inside a string that also contains an
   uppercase SQL keyword (`SELECT|WHERE|UPDATE|INSERT|DELETE|FROM`) —
   distinguishes SQL from English description text.
3. Two Pool-C-specific regexes: a hardcoded `SET geo_accuracy_pool = 1
   WHERE ...` populate statement, and a hardcoded
   `geo_resolved_trades_count >= N` gate condition — both should use
   `cd.POOL_C_POPULATE_SQL` / `cd.POOL_C_GATE_WHERE` /
   `cd.refresh_pool_c()`.

**Explicitly exempted (by design, read directly, not inferred):**
docstrings (first statement of module/function/class body, tracked by
`id()` in `_docstring_node_ids`), `print()`/`logger.*()`/`log.*()` call
arguments (tracked via a call-stack of "am I inside a cosmetic call"
booleans), `monitoring/column_definitions.py` itself (the canonical
source), and the checker script itself.

### 1.2 Why it is failing right now [V — ran it directly, read every flagged line]

```
$ python3 scripts/check_canonical_definitions.py
[check_canonical_definitions] DRIFT DETECTED — 7 violation(s):
  scripts/characterize_legendary_overlap_recompute.py:84  Python comparison `geo_elo_active >= 2175`
  scripts/trader_skill_metric_v2.py:390   SQL string contains `geo_elo >= 2175`
  scripts/trader_skill_metric_v2b.py:613  SQL string contains `geo_elo >= 2175`
  scripts/trader_skill_metric_v2c.py:506  SQL string contains `geo_elo >= 2175`
  scripts/trader_skill_metric_v2d.py:418  SQL string contains `geo_elo >= 2175`
  scripts/trader_skill_metric_v2e.py:437  SQL string contains `geo_elo >= 2175`
  scripts/trader_skill_metric_v2f.py:398  SQL string contains `geo_elo >= 2175`
```

Every flagged line was read directly, not trusted from the tool's own
message:

- `trader_skill_metric_v2.py:390`:
  `conn.execute("SELECT address FROM traders WHERE geo_elo >= 2175")` —
  literal SQL string, genuinely hardcoded, no `cd.LEGENDARY_GATE_WHERE`
  reference anywhere in the function.
- Same pattern, same line shape, in `v2b`/`v2c`/`v2d`/`v2e`/`v2f` — six
  independent copies of the identical `legendary_overlap()`-style helper,
  each with its own hardcoded copy (consistent with these being six
  sequential iterations of the same metric-development script, each one
  copy-pasted rather than importing the shared constant).
- `characterize_legendary_overlap_recompute.py:84`:
  `f_active = geo_elo_active is None or geo_elo_active < 2175` — raw
  Python comparison, same pattern.

`monitoring/column_definitions.py` currently defines:
```
GEO_ELO_LEGENDARY: float = 2175.0
LEGENDARY_GATE_WHERE = f"geo_elo_active >= {GEO_ELO_LEGENDARY}"
```
**2175 has not drifted** — the hardcoded value in all 7 violations still
matches the canonical constant exactly. This rules out "the rule's target
value is stale" as an explanation.

### 1.3 Real, stale, or false positive? **Real.** [V]

- **Not stale**: the threshold the rule checks for (2175) is the current
  canonical value, not an outdated one the rule forgot to update.
- **Not a false positive**: every flagged line, read directly, is a literal
  hardcoded `>= 2175` bypassing the constant it should reference. The
  check's own docstring-and-log exemptions are working correctly — none of
  the 7 flags are cosmetic text; all 7 are gate/comparison logic.
- **Real, structural risk, already named**: this is the identical
  population `MASTER_HANDOVER_2026-09-05.md` finding #7 flagged as
  DEGRADING ("a latent correctness risk for Phase 2's own metric, not just
  a style nit... against a threshold known to decay/drift"). Nothing has
  changed about it since 2026-09-05; it has simply continued running,
  unactioned, every day since.

### 1.4 Why has this been ignored for weeks, despite being wired to alert? [V — root-caused, not assumed]

The check has run as a non-blocking, alerting step
(`daily_maintenance.py:148`, `["--alert"]`) since `419d223` (2026-06-24).
Its own commit message describes the alert as "the third standing
protection... fires Telegram only when violations exist." **It has never
actually fired**, for a reason distinct from the 7 violations themselves:

- `check_canonical_definitions.py:191-192` reads credentials via bare
  `os.getenv("telegram_alerts_token")` / `os.getenv("telegram_chat_id")` —
  **no `load_dotenv()` call anywhere in the file.**
- `audit_invariants.py` (the step immediately before it in daily
  maintenance, same credential variable names, same pattern) **does** call
  `load_dotenv("/home/parison/.env_trading")` explicitly at line 1001,
  before reading the same two env vars.
- The cron wrapper that launches daily maintenance
  (`trading-swarm/scripts/cron_wrappers/run_daily_maintenance.sh`) does
  `source "$ENV"` (`/home/parison/.env_trading`) — but every line in that
  file is a plain `VAR=value` assignment with **no `export`** (confirmed
  directly: `grep -n "^export" .env_trading` → zero matches). A bash
  `source` of unexported assignments creates shell variables, not
  environment variables — they do **not** propagate to the `python3`
  child process `daily_maintenance.py` spawns, nor to the further
  `subprocess.run()` children it spawns for each step (`daily_maintenance.py`
  does `env = os.environ.copy()` — copying an environment that never had
  these vars in the first place).
- Confirmed live in today's log (`logs/daily_maintenance.log`, 2026-09-07
  run): `audit_invariants.py`'s alert fires (`[TELEGRAM] Alert sent.`)
  immediately followed by `check_canonical_definitions.py`'s
  (`[TELEGRAM] Credentials not found — skipping alert.`) — same run, same
  inherited environment, different outcome, exactly explained by the
  `load_dotenv()` presence/absence difference above.

**Consequence:** the 7 violations have been silently logged, never
alerted, every single day for roughly 11 weeks. The only way to see them is
to read the log file directly or run the script by hand — which is exactly
how this session found them, and how the 2026-09-07 status check first
surfaced "Canonical definitions drift" as one of two chronic red items
without (at the time) knowing why.

**Not fixed here.** This is a real, distinct bug from the 7 violations
themselves, but it is still a change to `check_canonical_definitions.py`'s
behavior (adding a `load_dotenv()` call), and the task's scope permits
fixing that file only "if Part 1 finds it is a trivially stale rule" — it
is not; the rule itself is correct and the violations are real. Reported,
not touched.

### 1.5 Can it be extended to cover Part 2 / Part 3? [I — assessed, not built, per the stop below]

Assessed for completeness since Part 1 asks for it, but **not
implemented** — the stop condition (§1.3 verdict) means nothing is built on
top of this check in this session.

- **Part 2 (canonical backtest-window-call adherence)** is a structurally
  different detection shape than anything `DriftVisitor` currently does.
  Every existing rule is a "does this literal/constant pattern appear"
  check (Compare-node threshold, string-literal regex) — a **presence**
  check. Part 2 needs an **absence** check: does a function that computes
  a market-population WHERE/JOIN shape fail to call
  `backtest_window_sql()` anywhere in scope, and is that omission
  undocumented. That requires function-level (not expression-level)
  traversal, a model of "what does a bypass look like structurally" (a
  SQL string with population-shaped predicates but no call to the
  canonical function in the same function/module), and a
  documented-exception list (the custody doc's §1C carve-out for
  `directional_skill_diagnostic.py`) that this file's current exemption
  model (per-file, not per-function-with-justification) doesn't support.
  It **could** live in the same file mechanically (same AST-parsing
  scaffolding, same CLI/exit-code contract), but the rule itself would be
  new, not an extension of the existing three rules.
- **Part 3 (decision-document reproducibility)** cannot be an extension of
  this file under any reading — it operates over Markdown prose in a
  different repository (`trading-swarm/brain/decisions/`), not Python ASTs
  in `first-repo`. A separate tool is unambiguously required.

---

## PARTS 2, 3, 4 — NOT ATTEMPTED

Per the task's explicit stop condition, no canonical-call adherence check
was built, no decision-document reproducibility check was built, and no
wiring was implemented. Nothing was fixed, extended, or modified in
`check_canonical_definitions.py`, any `trader_skill_metric_v2*.py` script,
`characterize_legendary_overlap_recompute.py`, or
`directional_skill_diagnostic.py`.

---

## What was not determined

- Whether Oscar wants the 7 hardcoded-threshold violations fixed (replace
  literal `2175` with `cd.GEO_ELO_LEGENDARY` / `cd.LEGENDARY_GATE_WHERE` in
  the 6 `v2*.py` scripts and `characterize_legendary_overlap_recompute.py`)
  before or independent of building further enforcement on top of the same
  theme.
- Whether Oscar wants the check's alert path fixed (adding
  `load_dotenv()`, matching `audit_invariants.py`'s pattern) so future
  violations actually reach Telegram, and whether that fix should be
  bundled with or kept separate from a fix to the 7 violations themselves.
- Whether, once those are resolved, `check_canonical_definitions.py` should
  become the home for a new Part-2-style absence-check (same file, new
  visitor) or whether a dedicated script is preferred structurally — this
  doc assessed feasibility (§1.5) but did not decide or build either.
- Everything Part 2, Part 3, and Part 4 of the original task asked for:
  the canonical-call adherence check, the decision-document reproducibility
  check (including its precision/recall against the corpus), and the
  wiring decision. None were attempted.
- Whether other non-blocking, alerting daily-maintenance steps have the
  same `load_dotenv()` gap as this one — not checked; this session verified
  only `check_canonical_definitions.py` against `audit_invariants.py`, not
  the full step list.
