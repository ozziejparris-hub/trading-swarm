# Resolve the 7 canonical-definition violations — Part 2 fix

**Date:** 2026-09-07
**Repo:** first-repo (HEAD at start: 51e3b74)
**Predecessor:** 2026-09-07-canonical-enforcement-part1-stop.md (2b44cb2) — diagnosed
the 7 violations as genuine; this doc resolves the live subset.
**Scope actually executed:** Part 1 (classification), Part 2 (fix LIVE files),
Part 3 (report non-live), Part 4 (re-run). No canonical definition touched. No file
archived / moved / deleted / exempted. check_canonical_definitions.py not modified.

Tagging: [V] = verified this session (ran / read directly), [I] = inferred.

---

## PART 1 — WHICH SCRIPTS ARE LIVE?

### Method [V]
- `grep -rn` across the repo for `import <mod>` / `from <mod> import` / `<mod>.py`
  references to each of the 7 files.
- Checked `scripts/daily_maintenance.py`, `run_tests.py`, `crontab -l`, and
  `~/trading-swarm/` cron wrappers for invocations. **Zero** references in any of
  those — none of the 7 is scheduled anywhere. Liveness is entirely "imported by
  an active research/diagnostic script."
- For each violation, located the enclosing `def` and grepped for external callers
  of *that function* (not just the file).
- Last-modified from `git log -1`; last-executed from dated output artifacts in
  `data/characterizations/` where one exists.

### The enclosing function for each violation [V]

| File:line | Enclosing function | Function has external caller? |
|---|---|---|
| characterize_legendary_overlap_recompute.py:84 | `decompose(conn, inflated_addresses)` | No — called only by this file's own `main()` |
| trader_skill_metric_v2.py:390 | `legendary_overlap(conn, entries_shrunk, verbose=False)` | No — called only by this file's own `main()`. (The `legendary_overlap=` hits in v2c/v2d/v2e are dict keys / column names, not calls.) |
| trader_skill_metric_v2b.py:613 | `main()` | No — `main` is never imported anywhere |
| trader_skill_metric_v2c.py:506 | `main()` | No |
| trader_skill_metric_v2d.py:418 | `main()` | No |
| trader_skill_metric_v2e.py:437 | `main()` | No (line is in `main()`, not the nested `t_ci_at_alpha`) |
| trader_skill_metric_v2f.py:398 | `main()` | No |

**Every one of the 7 violations sits in a function reachable only by running that
script directly as a CLI (`python scripts/<file>.py`). None is on any import
path.** Module-level `import` of these files executes the module body but never
`main()` / `legendary_overlap()` / `decompose()`.

### File-level import graph [V]

`directional_skill_persistence_test.py` (LIVE — in `run_tests.py`? no; but run
2026-09-06, produces `data/characterizations/directional_skill_persistence_*.json`,
last 20260906T195734Z) imports:
- `trader_skill_metric_v2` (`db_connect`)
- `trader_skill_metric_v2f` (`T_SPLIT, SEED, M_CHOSEN, GATE_REPS_LOCAL`)
- `trader_skill_metric_v2d` (`weighted_pair_table, weighted_two_way_gap_bootstrap`)
- `trader_skill_metric_v2c` (`WEIGHT_FNS`)

Transitive closure of those imports:
- `v2f` imports `v2` , `v2c`, `v2d`, `v2e` (`per_trader_t_ci`)
- `v2d` imports `v2`, `v2b` (`fixed_buckets`), `v2c`
- `v2c` imports `v2`, `v2b`
- `v2e` imports `v2`, `v2c`, `v2d`

⇒ **{v2, v2b, v2c, v2d, v2e, v2f} are all loaded when the persistence test runs.**
All six module bodies executed as recently as 2026-09-06.

Additional live consumers (each run manually, none scheduled), confirming the same
six are on active paths — not an exhaustive list:
- `characterize_orphan_sell_scope.py` → v2, v2d, v2e, v2f
- `track2_ci_power_diagnostic.py` → v2, v2c, v2d, v2f
- `discovery_gap_thesis_intersection.py` → v2, v2d, v2e, v2f
- `directional_skill_{diagnostic,null_calibration,pit_legal_pool,pit_power_estimate,reps_bh_effect,twice_classifiable_population}.py` → v2 + v2f
- `characterize_pending_invariant_regression.py`, `characterize_placebo_pending_exposure.py`,
  `persist_directional_skill_pit_exploratory.py` → v2 (+ v2f)

Test suite (`run_tests.py`, all `tests/test_*.py`):
- `tests/_match_control_determinism_worker.py` → `from scripts.trader_skill_metric_v2f import match_control`
  (driven by `tests/test_match_control_determinism.py`) ⇒ **v2f is exercised by the
  committed test suite**, transitively pulling v2, v2c, v2d, v2e.
- `tests/test_telegram_alert_gating.py` references `trader_skill_metric_v2.py:390`
  only as a string fixture in tuples — it does not import the module or scan the
  file. Unaffected by this change. [V — read the file header + fixture lines]

### Classification

| File | Last modified | Last executed (where determinable) | Class |
|---|---|---|---|
| trader_skill_metric_v2.py  | 2026-08-15 (13ecf07) | 2026-09-06 (module import, persistence test) | **LIVE** |
| trader_skill_metric_v2b.py | 2026-08-15 (de1ff84) | 2026-09-06 (module import via v2c/v2d) | **LIVE** |
| trader_skill_metric_v2c.py | 2026-08-15 (eb19b95) | 2026-09-06 (module import, persistence test) | **LIVE** |
| trader_skill_metric_v2d.py | 2026-08-15 (57d38bb) | 2026-09-06 (module import, persistence test) | **LIVE** |
| trader_skill_metric_v2e.py | 2026-08-15 (e5efb27) | 2026-09-06 (module import via v2f) | **LIVE** |
| trader_skill_metric_v2f.py | 2026-09-06 (42b14fc) | 2026-09-06 (persistence test + `run_tests.py`) | **LIVE** |
| characterize_legendary_overlap_recompute.py | 2026-08-18 (fd9e329) | **2026-08-18 only** — single output artifact `data/characterizations/legendary_overlap_recompute_20260818T192510Z.json`, never re-run | **DORMANT** |

**No SUPERSEDED files.** v2→v2f are sequential iterations, but the import graph
shows the earlier ones are *not* dead-and-replaced — they are a layered library
where each iteration imports helpers from its predecessors, and all six are pulled
in by the still-active persistence test and the `run_tests.py` suite. "Later
iteration exists" is true; "later iteration replaced it" is false for every one.

**No ambiguity** — no STOP on Part 1. The task pre-stated v2d and v2f are live;
the evidence extends the same LIVE verdict to v2, v2b, v2c, v2e on the identical
basis (transitive import from a script run yesterday + the test suite). The
DORMANT/LIVE split for `characterize_legendary_overlap_recompute.py` is
unambiguous: zero importers, zero schedulers, one lifetime execution.

---

## PART 2 — FIX THE LIVE ONES

### (a) vs (b) decision — **(a) for all six, no exceptions**

The six SQL strings are byte-identical: `"SELECT address FROM traders WHERE
geo_elo >= 2175"`. The predicate is on **`geo_elo`**, not `geo_elo_active`.
`cd.LEGENDARY_GATE_WHERE` is `geo_elo_active >= 2175.0 AND geo_accuracy_pool = 1
AND research_excluded = 0 AND bot_type IS NULL` — a **different column plus three
extra conditions**. The 2026-08-15 handover §1 records this exact distinction as
the reason the original 15/81 LEGENDARY-overlap figure was wrong: the hardcoded
`geo_elo >= 2175` predicate is *not* the canonical gate, and swapping the
canonical gate in would **change behaviour** (different result set), not just
centralise a constant.

⇒ Correct fix = **(a): reference the threshold constant only**, via an f-string,
keeping the column (`geo_elo`) and the predicate shape identical:

```python
# before
conn.execute("SELECT address FROM traders WHERE geo_elo >= 2175")
# after
conn.execute(f"SELECT address FROM traders WHERE geo_elo >= {cd.GEO_ELO_LEGENDARY}")
```

Plus one import line added after the existing `sys.path.insert(...)` in each file:
`import monitoring.column_definitions as cd` (the dominant pattern across
`scripts/*.py`).

**No file should use the full canonical gate here.** These are exploratory
LEGENDARY-overlap diagnostics that deliberately compare the new metric's cohort
against the *legacy raw-`geo_elo`* LEGENDARY notion — the whole point of
`characterize_legendary_overlap_recompute.py` (DORMANT, untouched) was to quantify
the gap between that raw predicate and the canonical gate (15/81 → 3/10). Forcing
the canonical gate into these six sites would silently redefine what they measure.
That is a behaviour change and Oscar's call, not this task's. **Reported, not done.**

### Equivalence verification [V]

`cd.GEO_ELO_LEGENDARY` is `2175.0` (float), so the rendered SQL becomes
`... geo_elo >= 2175.0`. The *only* textual delta is `2175` → `2175.0`.

Confirmed equivalent against the live DB (`data/polymarket_tracker.db`,
`typeof(geo_elo)` ∈ {null, real}):

```
SELECT COUNT(*) FROM traders WHERE geo_elo >= 2175     -> 89
SELECT COUNT(*) FROM traders WHERE geo_elo >= 2175.0   -> 89
(addr set A) EXCEPT (addr set B)  -> 0 rows
(addr set B) EXCEPT (addr set A)  -> 0 rows
```

Identical result set, zero symmetric difference. SQLite numeric comparison treats
`2175` and `2175.0` identically against a REAL/NULL column. Behaviour preserved.

All six modules re-import cleanly (`python3 -c "import scripts.trader_skill_metric_v2X"`)
and `python3 -m py_compile` passes for all six.

### Files changed (6)

| File | import added at | query line |
|---|---|---|
| scripts/trader_skill_metric_v2.py  | after L140 | L392 |
| scripts/trader_skill_metric_v2b.py | after L140 | L615 |
| scripts/trader_skill_metric_v2c.py | after L123 | L508 |
| scripts/trader_skill_metric_v2d.py | after L111 | L420 |
| scripts/trader_skill_metric_v2e.py | after L109 | L439 |
| scripts/trader_skill_metric_v2f.py | after L120 | L400 |

---

## PART 3 — THE NON-LIVE ONE

**`scripts/characterize_legendary_overlap_recompute.py:84`** —
`f_active = geo_elo_active is None or geo_elo_active < 2175` inside
`decompose()`. Classification: **DORMANT** (not SUPERSEDED).

- **What it is:** a read-only, single-use characterization script that produced
  the corrected LEGENDARY-overlap figure (3/10, as-of 2026-08-18T19:25:10Z) cited
  in `MASTER_HANDOVER_2026-08-15.md` §1 and `2026-08-18-legendary-overlap-recompute.md`
  (commit dd2261a). Generating artifact:
  `data/characterizations/legendary_overlap_recompute_20260818T192510Z.json`.
- **What supersedes it:** nothing. It is standalone audit-trail evidence, not a
  step in any pipeline. It has no importers and is not scheduled.
- **Why the check still fires on it:** its violation is a *Python* `Compare` node
  (`geo_elo_active < 2175`), which `visit_Compare` flags regardless of operator.
  (Its two SQL-ish strings `CANONICAL_LEGENDARY_WHERE` / `HARDCODED_LEGENDARY_WHERE`
  are *not* flagged — they lack an uppercase SQL keyword, so `RE_SQL_CONTEXT`
  misses them. Only line 84 trips the check.)

### Options for Oscar (this task changes none of them)

1. **Fix the literal anyway** — `geo_elo_active < cd.GEO_ELO_LEGENDARY` + add the
   `cd` import. Pure (a): `2175` vs `2175.0` is identical for a Python `<`
   comparison. One-line change, makes the check fully green, touches a DORMANT
   audit-trail file. Lowest-risk of the three; the only argument against is not
   wanting to modify a frozen characterization artifact.
2. **Exempt it** — add `ROOT / "scripts" / "characterize_legendary_overlap_recompute.py"`
   to `EXEMPT_FILES` in `check_canonical_definitions.py` with a comment ("frozen
   2026-08-18 characterization; the `< 2175` compare is a deliberate probe of the
   *legacy* raw-geo_elo LEGENDARY notion, not gate logic"). Keeps the file
   byte-frozen; costs one entry in the exemption list and the precedent.
3. **Leave it** — the check stays at 1 violation forever; `should_alert()`
   suppresses it after the first observation, so it is silent noise in the log
   only. Acceptable but leaves a permanent non-green check.

Recommendation (non-binding): option 1 if Oscar is comfortable touching the file;
option 2 otherwise. Not option 3 — a permanently-red check erodes the signal.

---

## PART 4 — RE-RUN RESULT

```
$ python3 scripts/check_canonical_definitions.py
[check_canonical_definitions] DRIFT DETECTED — 1 violation(s):

  scripts/characterize_legendary_overlap_recompute.py:84  Python comparison
      `geo_elo_active >= 2175` — replace with cd.GEO_ELO_* constant
EXIT=1
```

**7 → 1.** The six `trader_skill_metric_v2*.py` violations are cleared. The one
remaining is the DORMANT file (Part 3) — expected, and left for Oscar.

### The Telegram alert will fire exactly once — this is correct

`check_canonical_definitions.py` persists a violation signature to
`data/.canonical_drift_state.json` and (with `--alert`, as
`daily_maintenance.py` runs it) alerts only when the signature *changes*. Going
from the committed 7-entry signature to a 1-entry signature **is** a change, so
the next `daily_maintenance.py` run will send one Telegram alert showing the
reduced set, then persist the new signature and go quiet again.

**That single alert is the expected, correct consequence of fixing six violations
— not a regression or noise.** After it, the check is silent (1 stable violation,
`should_alert()` returns False on an unchanged set).

Note: the manual re-run above *also* calls `save_signature()` as a side effect. To
preserve the once-alert on the normal daily path, `data/.canonical_drift_state.json`
was restored to its committed 7-entry state (`git checkout HEAD -- ...`) after the
verification run. The next `--alert` run legitimately detects 7→1 and notifies.

### run_tests.py [V]

`python3 run_tests.py --skip=test_behavioral_integration.py` (the skip is the
documented cold-cache hang, not related to this work):

```
Files  : 20 run, 19 passed, 1 failed
Tests  : 339804 run, 339799 passed, 5 failed
RESULT: FAILURES DETECTED
  - test_backtest_window_population.py
```

- **The single failing file is `test_backtest_window_population.py`** — the
  chronic, pre-existing failure. Its 5 failing assertions (T2/T2b/T2c/T2d/T2f)
  hardcode market counts (4658, 54, 555, 573) against a frozen
  `backtest_population_snapshots` row; they drift as new trades accrue and move
  `tape_end` (got 4660 / 52 / 575 / 648). This is Section 6 (`backtest_window_sql`)
  territory — **nothing to do with `geo_elo` thresholds or this change**. Reported
  as **unchanged**, not caused by this work.
- All 19 other files pass (339,799 assertions). Specifically:
  `test_match_control_determinism.py` 6/6 (imports `trader_skill_metric_v2f`,
  transitively v2/v2c/v2d/v2e — the edited files) and
  `test_telegram_alert_gating.py` 20/20 (the alert-signature/gating logic).

---

## WHAT WAS NOT DETERMINED

- **Whether any `v2*` `main()` is ever still run directly.** They have no
  scheduler and no importer of `main`; the *modules* were loaded 2026-09-06, but
  whether anyone has executed `python scripts/trader_skill_metric_v2d.py` (etc.)
  since 2026-08-15 is not recorded anywhere (these scripts print to stdout / write
  ad-hoc artifacts, no run log). The fix is behaviour-neutral either way, so this
  does not matter for correctness — only for how "dead" the enclosing function is.
- **Whether Oscar wants `characterize_legendary_overlap_recompute.py:84` fixed,
  exempted, or left** (Part 3). Not touched here.
- **Whether these six diagnostics *should* migrate to the full canonical
  `cd.LEGENDARY_GATE_WHERE`.** That is a behaviour change (different column +
  three extra predicates → different result set) and a measurement-definition
  decision for Oscar. This task deliberately kept option (a).
- **The check's own `load_dotenv()` gap** (from the Part 1 STOP doc §1.4) — still
  unfixed; out of scope here (would modify `check_canonical_definitions.py`).
  Until it is fixed, even the "alert once" above will not actually reach Telegram
  when run under cron's unexported-env wrapper.
- **Whether other DORMANT `characterize_*` / one-off scripts carry similar
  hardcoded thresholds not yet flagged** (e.g. strings without an uppercase SQL
  keyword, like this file's own `CANONICAL_LEGENDARY_WHERE`). Not audited.
