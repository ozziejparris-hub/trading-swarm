# 2026-09-09 — `scripts/compare_trade_evaluators.py`: retire, don't repair

**Recommendation: retire (delete) the script. Do not fix its import.**
Retiring is Oscar's call — this is report-and-stop, no first-repo change
made. Found as a side note in `2026-09-09-geo-backfill-wiring-decision.md`
(`28d898b`).

Every claim is **[V]** verified this session (file:line / command given).

---

## What the script is for

**[V]** `scripts/compare_trade_evaluators.py` (docstring lines 2-23) is an
**empirical convergence check between two implementations of win/loss
determination**:

1. `monitoring.trade_evaluator.TradeEvaluator.evaluate_trade()` — canonical
2. `scripts.backfill_trade_results_geo.evaluate_trade()` — the geo-backfill
   script's own local reimplementation

It ran both, read-only, over every already-evaluated (`trade_result IN
('won','lost')`) Geopolitics/Elections trade and compared outputs row by
row. Its docstring names the two as *"structurally identical but not the
same function"* (`2026-08-19-elo-write-architecture-recon.md`).

## Whether it still has a purpose after the repoint — NO

**[V]** The 2026-08-19 repoint commit `8cfeb8e` ("fix: repoint
backfill_trade_results_geo.py onto canonical TradeEvaluator") **removed**
`def evaluate_trade(outcome_bet, side, winning_outcome)` from
`backfill_trade_results_geo.py` and replaced every call site with
`_EVALUATOR.evaluate_trade(trade, winning_outcome)`
(`git show 8cfeb8e -- scripts/backfill_trade_results_geo.py`; current file
has no such symbol — `grep` confirms).

After that commit there is **exactly one** implementation. The second thing
this script compared no longer exists. The comparison is moot by
construction.

**[V]** The script was in fact the **pre-repoint gate for that very
commit**. Timeline, all 2026-08-19:
- 18:04:23 — its only artifact produced:
  `data/characterizations/trade_evaluator_convergence_20260819T180423Z.json`
- 18:06:43 — committed (`e4f4561`, its only commit ever)
- 18:22:15 — repoint `8cfeb8e` lands, message: *"per
  2026-08-19-trade-evaluator-convergence.md's IDENTICAL-REPOINTABLE verdict
  (1,582,064-row zero-disagreement comparison)"* — i.e. acting on this
  script's output.

It answered a one-time question ("are these two functions equivalent
enough to collapse into one?"), the answer was yes, and the collapse
happened 16 minutes later. Its job is done.

**[V]** Not wired anywhere: absent from `crontab -l`, from any systemd
unit, and from `tests/`. The only surviving reference is its successor
naming it in the past tense: `verify_geo_backfill_repoint.py:14` — *"the
same population scripts/compare_trade_evaluators.py used."*

**[V] No coverage is lost by deleting it.** The durable, still-runnable
version of the check is `scripts/verify_geo_backfill_repoint.py` (added in
the same repoint commit `8cfeb8e`): it reconstructs the pre-repoint
`evaluate_trade` from git history via `git show` + `exec` and compares it
against the current canonical path over the same population — so it does
**not** depend on the removed symbol (`grep` of its imports confirms: it
imports only `TradeEvaluator`). That is the regression guard going forward;
`compare_trade_evaluators.py` is the scaffold that was left behind.

## What the "correct import" would be — and why fixing it is wrong

**[V]** The canonical replacement for the removed function is
`TradeEvaluator.evaluate_trade` (instance method;
`monitoring/trade_evaluator.py:16`), signature `(self, trade: Dict,
winning_outcome: str)`.

An import-only fix is **not possible** and would be **meaningless**:

- **Signature mismatch, not just a name.** The removed local function was
  `evaluate_trade(outcome_bet, side, winning_outcome)` — three positional
  scalars. The call site `compare_trade_evaluators.py:84` is written for
  exactly that: `geo_evaluate_trade(row["outcome_bet"], row["side"],
  row["winning_outcome"])`. `TradeEvaluator.evaluate_trade` takes a dict.
  Repointing the import would require rewriting line 84 too — which the
  task explicitly forbids ("Import fix only. Do NOT change its logic ... or
  anything else in the file").
- **Tautology even if done.** Both sides of the comparison would then be
  `TradeEvaluator.evaluate_trade`. The script would compare the canonical
  evaluator against itself: 100% agreement by construction, on every run,
  forever — zero information. That is repairing something that should be
  deleted.

## Anything else importing the removed symbol — NO

**[V]** `grep -rn "backfill_trade_results_geo" --include=*.py`: the only
`import ... evaluate_trade` is `compare_trade_evaluators.py:35`.
`verify_geo_backfill_repoint.py` mentions the module by name in strings and
a `git show` argument but imports nothing from it. `monitoring/trade_evaluator.py:41`
is a comment. Nothing else is affected.

## Recommendation

**Retire it** — `git rm scripts/compare_trade_evaluators.py`. Its one-time
finding is preserved in
`data/characterizations/trade_evaluator_convergence_20260819T180423Z.json`
and `2026-08-19-trade-evaluator-convergence.md`; its ongoing role is
covered by `scripts/verify_geo_backfill_repoint.py`.

Oscar's call. No first-repo change made this session; the broken import is
left as-is pending that decision. If retirement is declined, the file needs
a real rewrite (import + call-site + a non-tautological second comparand),
which is out of scope for an "import fix only" task.

---

*Generated 2026-09-09. Sources: `scripts/compare_trade_evaluators.py`
(full read), `scripts/backfill_trade_results_geo.py` (current + `git show
8cfeb8e`), `scripts/verify_geo_backfill_repoint.py`,
`monitoring/trade_evaluator.py:16-51`, `git log -- scripts/compare_trade_evaluators.py`,
`data/characterizations/` listing, `crontab -l`,
`python3 -c "import scripts.compare_trade_evaluators"` (ImportError
reproduced). No code changed.*
