# 2026-08-19 — repoint `backfill_trade_results_geo.py` onto the canonical `TradeEvaluator`

**This is the first code change in this arc.** Every claim tagged **[V]**
(verified this session — command/file:line given) or **[I]** (inferred,
explicitly marked). All three verifications in Part 3 passed; the change
was committed and pushed only after they did. No production data was
written by anything in this session — confirmed explicitly in Part 3.

---

## What changed

**`monitoring/trade_evaluator.py`** — one line hardened in
`TradeEvaluator.evaluate_trade`:

```python
# before
side = trade.get('side', 'buy').lower()
# after
side = (trade.get('side') or 'buy').strip().lower()
```

**`scripts/backfill_trade_results_geo.py`** — repointed:
- Removed the local `evaluate_trade(outcome_bet, side, winning_outcome)`
  function (12 lines).
- Added `from monitoring.trade_evaluator import TradeEvaluator` and one
  module-level instance, `_EVALUATOR = TradeEvaluator(None, None)`
  (commented: the constructor args are unused by `evaluate_trade()`).
- Added `t.outcome` to `fetch_pending_trades`'s `SELECT` list, so
  `TradeEvaluator`'s `outcome_bet`→`outcome` fallback path is actually
  reachable through this caller (previously the fallback existed in the
  canonical function but this caller never supplied the second field).
- Both call sites (`--dry-run` and live-write loop) now call
  `_EVALUATOR.evaluate_trade(trade, trade['winning_outcome'])` instead of
  the 3-scalar-arg local function.
- Updated the module docstring to point at this doc and the convergence
  doc instead of describing a local reimplementation.

No other file touched. `daily_maintenance.py` and
`monitoring/position_tracker.py` are confirmed untouched (`git diff
--stat` on both: empty) — the two explicit out-of-scope items in the task
constraints.

---

## Part 1 — the divergence decision

The convergence doc (`2026-08-19-trade-evaluator-convergence.md`, `e059b71`)
found three real statement-level divergences. Per column: which side was
more defensive, and what this repoint does about it.

| Divergence | More defensive | Decision | Where fixed |
|---|---|---|---|
| `outcome_bet`→`outcome` fallback | Canonical (already had it; geo-backfill's SQL never even fetched `outcome`) | Make the fallback actually reachable through this caller | `fetch_pending_trades` now selects `t.outcome` |
| `side=None` crashes canonical (`AttributeError`); geo-backfill tolerates it | geo-backfill | **Preserve the more defensive behavior — in canonical, not in the caller** | `TradeEvaluator.evaluate_trade`, `(trade.get('side') or 'buy')` |
| Whitespace-padded `side` misread as SELL by canonical; geo-backfill strips it | geo-backfill | **Preserve — in canonical** | `TradeEvaluator.evaluate_trade`, `.strip()` added |

**Rationale for hardening canonical rather than wrapping the call in the
caller**, per the task's own instruction: this fix now protects **all
three** callers of `TradeEvaluator` —
`scripts/evaluate_new_trader_results.py` (live, daily),
`scripts/backfill_trade_results.py` (unwired but real), and the newly
repointed `backfill_trade_results_geo.py` — rather than only the one
caller that happened to prompt the investigation. Wrapping the fix around
`TradeEvaluator` inside `backfill_trade_results_geo.py` (e.g. sanitizing
`trade['side']` before calling it) would have reintroduced exactly the
kind of caller-specific special case the arc exists to remove — a second
place where the input gets massaged before the "canonical" evaluation, no
better than a second implementation of the evaluation itself.

**No regression accepted.** All three divergences are now resolved in
canonical's favor of whichever side was more defensive — nothing was
downgraded.

---

## Part 2 — the coherence question

**Assessed, not implemented, per the task's explicit instruction.**

Read all three scripts in full (`evaluate_new_trader_results.py`,
`backfill_trade_results_geo.py` post-repoint, `backfill_trade_results.py`)
and their underlying `Database` methods (`get_resolved_markets`,
`get_trades_for_market`) to compare actual behavior, not just docstrings:

| Axis | `evaluate_new_trader_results.py` | `backfill_trade_results_geo.py` | `backfill_trade_results.py` |
|---|---|---|---|
| Trader population | `is_flagged=1` (+ manual_watchlist/external_seed exception) | ALL traders | ALL traders |
| Category filter | none | Geopolitics/Elections only | **none** |
| `trade_gap_flag` filter | yes | yes | **none at all** |
| Trade selection scope | `trade_result='pending'` only | `trade_result='pending' OR NULL` | **every trade on every resolved market, every run, regardless of current `trade_result`** — `get_trades_for_market()` has no `trade_result` filter (`monitoring/database.py:619-630`, verified), so this script re-evaluates and re-writes already-`won`/`lost` rows unconditionally each time it runs |
| Evaluator | `TradeEvaluator` (canonical) | `TradeEvaluator` (canonical, as of this repoint) | `TradeEvaluator` (canonical) |
| Post-write aggregate recompute | `traders.resolved_trades_count` | `traders.geo_resolved_trades_count` | **none** |
| Invocation | `daily_maintenance.py` step 21, automated, non-blocking | manual CLI (`--dry-run`/`--limit`), scriptable | manual CLI, **blocks on an interactive `input("Proceed? (yes/no): ")` prompt** — not automatable without modification |
| DB access pattern | `Database` wrapper class | raw `sqlite3.Connection`, WAL, batched 1,000-row commits | `Database` wrapper class |

**Honest assessment: yes, this is the "three scripts, one WHERE clause
each" pattern for the two that matter operationally** —
`evaluate_new_trader_results.py` and (post-repoint)
`backfill_trade_results_geo.py` now share the identical mechanism
end-to-end (fetch pending trades on resolved markets via a filter, call
`TradeEvaluator`, write `trade_result`, recompute one aggregate count) and
differ **only** in which population filter is applied and which column
gets recomputed afterward. Both are entirely expressible as
`--population {flagged,all}`, `--category {all,geo_elec}`,
`--recompute-column {resolved_trades_count,geo_resolved_trades_count,none}`
flags on one script.

`backfill_trade_results.py` is a genuine outlier on one real axis, not
just cosmetically different: it has no incremental/pending-only semantics
at all (it re-touches every trade on every run, not just newly-pending
ones) and is not automatable in its current form (the `input()` prompt).
Both of those are themselves easily-fixed properties of an old,
never-modernized tool, not evidence that it's answering a different
question — the underlying operation (fetch trades on resolved markets,
call `TradeEvaluator`, write `trade_result`) is identical to the other two.

**Recommendation, stated plainly and not implemented:** consolidate into
one parameterized script. The current state is not "three tools for three
jobs" — it is one operation, implemented three times, currently producing
**two independently-drifting aggregate columns**
(`resolved_trades_count` and `geo_resolved_trades_count`) computed by two
separately-maintained recompute queries reading the same `trades` table,
with no single source of truth for "how many of this trader's trades are
resolved." That is the same shape of problem the ELO arc was built to
remove from `comprehensive_elo`'s write path — it currently exists,
unaddressed, one layer upstream of it, in the inputs that feed
`resolved_trades_count` into `compute_comprehensive_elo`. Scheduling a
third invocation path (the pending wiring decision) without consolidating
first would schedule three near-duplicate maintenance steps instead of
one parameterized one. **This was not implemented here** — the task asked
for assessment only; the recommendation is handed to whoever makes the
wiring decision next.

---

## Part 3 — non-tautological verification

All three run **after** the code change, **before** commit. All three
could have failed; none did.

### 1. Before/after equivalence check

**Why this test could fail, unlike re-running the old comparison
verbatim:** the old `compare_trade_evaluators.py` imported the *local*
`evaluate_trade` function from `backfill_trade_results_geo.py` — that
function no longer exists post-repoint, so simply re-running it would
either error (proving nothing useful) or need to import something that
isn't the thing being tested. Instead, wrote
`scripts/compare_trade_evaluators.py`'s replacement,
`scripts/verify_geo_backfill_repoint.py`, which extracts the **exact
pre-repoint function body** via `git show HEAD:scripts/backfill_trade_results_geo.py`
(execed in an isolated namespace — no hand-transcription, so no
transcription-error risk) and compares it against the **current, hardened**
`TradeEvaluator.evaluate_trade`. This test fails if either (a) the
hardening changed any real output, or (b) the mechanical rewiring (dict
construction, added `outcome` column, method-call shape) introduced an
error.

**[V] Run against both populations:**

```
[already-evaluated, trade_result IN ('won','lost'), Geo/Elections]
  compared=1,582,064  agree=1,582,064  disagree=0

[current stuck-pending population — the actual backfill target]
  compared=24,719      agree=24,719      disagree=0
```

Zero disagreements on both. Artifact:
`data/characterizations/geo_backfill_repoint_verification_20260819T181726Z.json`.

### 2. Dry-run against the current stuck-pending population

**[V]** `python3 scripts/backfill_trade_results_geo.py --dry-run`, the
actual repointed script, end-to-end (not just the isolated function):

```
Found 24,719 pending trades to evaluate.
[DRY RUN] Would write: won=12,484, lost=12,235, invalid=0
[DRY RUN] Traders affected: 1,733
```

**24,719 rows compared** — matches the "current stuck-pending population"
count from verification #1 exactly, confirming the full pipeline (SQL
fetch with the newly-added `outcome` column, dict construction, canonical
evaluator call) runs without error and produces a result consistent with
the isolated function-level check. `invalid=0` — matches the empirical
finding from the convergence doc that `outcome_bet` is never null on this
population, so the newly-reachable fallback path is exercised zero times
by current data (as expected, and as already flagged as a property of
current data, not an invariant).

### 3. `run_tests.py` (canonical runner)

**[V]** `python3 run_tests.py --verbose`, full run, ~140s:

```
Files  : 15 run, 14 passed, 1 failed
Tests  : 339,700 run, 339,695 passed, 5 failed
  FAIL  test_backtest_window_population.py  (24 tests, 19 passed)
RESULT: FAILURES DETECTED
```

**Identical to the stated baseline** (14/15 files, 19/24 in the one known
failing file, same 5 sub-test failures, same file name). **No new
failure.** Checked specifically: no test file references
`trade_evaluator` or `backfill_trade_results_geo` at all (`grep` on the
full run output: zero hits) — there is no dedicated test coverage for
either module, so this run's clean result reflects "nothing broke
elsewhere," not "the repoint itself is covered by a test" — named
honestly rather than overclaimed.

### WAL-safe backup discipline — confirmed not applicable

**[V]** No write path was exercised anywhere in this session's
verification: `verify_geo_backfill_repoint.py` opens the DB via a
`mode=ro` URI connection; `backfill_trade_results_geo.py --dry-run`'s
`if dry_run:` branch structurally returns before the code ever reaches
the `cursor.execute("UPDATE trades ...")` block (confirmed by reading the
control flow, not assumed); `run_tests.py` is the same suite
`daily_maintenance.py` runs non-destructively every day. Confirmed before
proceeding, per the task's explicit instruction.

---

## Summary

| Item | Result |
|---|---|
| Repoint | Done — `backfill_trade_results_geo.py` now calls canonical `TradeEvaluator.evaluate_trade` exclusively |
| Divergence decision | All 3 resolved in favor of the more-defensive behavior, fixed in canonical (benefits all 3 callers), no regression accepted |
| Coherence assessment | 3 scripts differ only in population/category filter + which aggregate to recompute (2 of 3); recommend consolidating into one parameterized script — **not implemented, handed off** |
| Verification 1 (before/after equivalence) | 1,582,064 + 24,719 rows, 0 disagreements |
| Verification 2 (dry-run) | 24,719 rows, won=12,484/lost=12,235/invalid=0, 1,733 traders — consistent with #1 |
| Verification 3 (`run_tests.py`) | 14/15 files, identical to baseline, no new failure |
| `daily_maintenance.py` | Untouched (confirmed) |
| `apply_synthetic_closes` | Untouched (confirmed) |
| Production writes this session | None (confirmed) |

All three verifications passed; the change is committed.

---

*Generated 2026-08-19. Sources: `monitoring/trade_evaluator.py`,
`scripts/backfill_trade_results_geo.py`, `scripts/backfill_trade_results.py`,
`scripts/evaluate_new_trader_results.py`, `monitoring/database.py`
(`get_resolved_markets` line 566, `get_trades_for_market` line 619),
`2026-08-19-trade-evaluator-convergence.md` (`e059b71`),
`2026-08-19-geo-backfill-wiring-prereg.md` (`9610f99`), this session's new
`scripts/verify_geo_backfill_repoint.py` (first-repo) →
`data/characterizations/geo_backfill_repoint_verification_20260819T181726Z.json`,
and a full `run_tests.py --verbose` run (both committed/logged this
session).*
