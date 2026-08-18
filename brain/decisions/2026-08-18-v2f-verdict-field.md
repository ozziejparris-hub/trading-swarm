# 2026-08-18 — v2f verdict-field discrepancy: characterization

Evidence tagging: **[V]** = verified directly (query/command/file:line given). **[I]** = inferred/plausible, marked as such. Standing project instruction applied throughout — see `feedback_verify_dont_propagate.md`. No fixes, no pipeline re-runs, no persisted-table modifications were made.

## Headline finding — stated prominently per the standing instruction

**There is no discrepancy.** The task's own premise — "under v2f's own verdict logic [the CIs] should yield NULL rather than SUPPORTED... the question is whether the pipeline's own persisted verdict field agrees with it, and if not, why" — is answered directly: **it agrees.** The persisted `thesis_verdict` string, the code that generated it, and the narrative master handover all say **NULL**, and they are mutually consistent. The concern raised incidentally in `2026-08-18-orphan-sell-scope.md` was a correct thing to flag and check (it never claimed to have observed a wrong value, only reasoned about what the logic *would* produce) — but on checking, the flagged risk does not materialize.

## Q1 — What is actually persisted **[V]**

`metric_v2f_oos_result` schema (`sqlite3 data/polymarket_tracker.db ".schema metric_v2f_oos_result"`):
```
CREATE TABLE metric_v2f_oos_result (kind TEXT PRIMARY KEY, n_positions INTEGER,
    n_traders INTEGER, point_gap REAL, ci_lo REAL, ci_hi REAL, spec_version TEXT, generated_at TEXT,
    generator_commit TEXT);
```
**This table has no verdict-like column at all.** Its rows, verbatim:
```
cohort |3032|120|0.0315983580923187 |-0.00881147179033796|0.0710126418085991|SKILLV2F-2026-08-15-v1|2026-08-15T19:36:56.852700+00:00|eaeabbc
placebo|2569|110|0.0127065403076488|-0.0210094439314384 |0.0461439972587876 |SKILLV2F-2026-08-15-v1|2026-08-15T19:36:56.852700+00:00|eaeabbc
```

The actual verdict lives in a separate table, `metric_v2f_findings`, row `finding='objective2'`, as a JSON field. Verbatim (`json_value`, key `thesis_verdict`, whitespace/quoting as stored):
```json
"thesis_verdict": "NULL -- the cohort's out-of-sample edge does not exclude zero. The thesis is not supported at this cohort/window."
```
The full `objective2` JSON blob also embeds `oos_result` and `placebo_result` sub-objects reproducing the same numbers as `metric_v2f_oos_result` (`point_gap`, `ci_lo`, `ci_hi`, `n_positions`, `n_traders`/`n_surviving_traders`) — i.e. the numeric result is stored twice, in two tables, but the verdict label exists in exactly one place: `metric_v2f_findings`, not `metric_v2f_oos_result`.

## Q2 — What the code does **[V]**

`scripts/trader_skill_metric_v2f.py:429-444`:
```python
cohort_excludes_zero = (oos_result.get('ci_lo') is not None and
                        (oos_result['ci_lo'] > 0 or oos_result['ci_hi'] < 0))
cohort_positive = cohort_excludes_zero and oos_result['ci_lo'] > 0
placebo_excludes_zero = (placebo_result.get('ci_lo') is not None and
                         (placebo_result['ci_lo'] > 0 or placebo_result['ci_hi'] < 0))

if cohort_positive and not placebo_excludes_zero:
    thesis_verdict = "SUPPORTED, interpretable -- cohort shows a genuine out-of-sample edge, placebo does not."
elif cohort_positive and placebo_excludes_zero:
    thesis_verdict = "NOT INTERPRETABLE -- placebo is also non-null; the measurement is picking up something structural, not cohort-specific skill."
elif not cohort_excludes_zero:
    thesis_verdict = "NULL -- the cohort's out-of-sample edge does not exclude zero. The thesis is not supported at this cohort/window."
else:
    thesis_verdict = "NEGATIVE -- the cohort's out-of-sample edge is significantly negative."
```
No separate docstring exists for this block (it is inline procedural code with matching print statements) — there is nothing for code and docstring to disagree about here; not applicable.

## Q3 — Defect, naming mismatch, or neither **[V]**

Manually replaying the logic against the persisted cohort row: `ci_lo = -0.00881...`, `ci_hi = 0.07101...`. Neither `ci_lo > 0` nor `ci_hi < 0` holds, so `cohort_excludes_zero = False`, `cohort_positive = False`. The `if`/`elif` chain falls through to `elif not cohort_excludes_zero:` → `thesis_verdict = "NULL -- ..."`. **This exactly matches the persisted string in `metric_v2f_findings` character-for-character.** The placebo branch is never reached (the cohort check short-circuits first), so the placebo's own CI-includes-zero state is irrelevant to why this run says NULL.

None of the four provided classifications (a: logic wrong / b: naming mismatch / c: stale threshold / d: something else) describes a real problem, because **there is no problem to classify** — the code is doing exactly what its branches say, the persisted value matches the code exactly, and both match the narrative conclusion. If forced to pick the closest label: **(d), and the "something else" is "no discrepancy exists."**

## Q4 — Does anything consume it **[V]**

Grep across first-repo and trading-swarm for `thesis_verdict`, `metric_v2f_oos_result`, `metric_v2f_findings`:
- The only reader anywhere is `scripts/characterize_orphan_sell_scope.py:150`, which reads `metric_v2f_oos_result`'s five numeric columns (`n_positions, n_traders, point_gap, ci_lo, ci_hi`) for a drift cross-check against persisted 08-15 values. **It does not read `thesis_verdict` or `metric_v2f_findings` at all.**
- No other script, report generator, or swarm/agent orchestration code in either repo references `thesis_verdict` or `metric_v2f_findings`.

So even in the counterfactual where the verdict logic *were* wrong, the blast radius would be documentation-only (whoever reads the JSON blob or the master handover by eye) — nothing automated consumes it. As established in Q3, this is moot here since the value is correct.

## Q5 — Effect on carried figures **[V]**

Verified by code order, not assumption: `oos_result` and `placebo_result` are computed and fully populated at lines 419-420, *before* any verdict logic runs. `thesis_verdict` is first assigned at lines 438-444 and is read only afterward (printed at 445, embedded in the `findings` dict at 469 for storage). There is no code path where `thesis_verdict` — or any verdict-branch variable — feeds back into `oos_result`, `placebo_result`, or the values persisted to `metric_v2f_oos_result`. The verdict is strictly a derived label over the four carried figures (+0.0316 CI[-0.0088,+0.0710] n=3032 cohort; +0.0127 CI[-0.0210,+0.0461] n=2569 placebo — both **[V]** confirmed present verbatim in Q1's dump), never an input to them.

## Q6 — How long **[V]**

`git log --oneline --follow -- scripts/trader_skill_metric_v2f.py` returns exactly **one** commit: `eaeabbc feat: trader skill metric v2f -- close cost-floor gap, ask the thesis out-of-sample`. The verdict-branch code (lines 429-444) has existed in this form since the file's only commit — there is no prior version to diff against, and `git log -p` on the file shows the four `thesis_verdict = "..."` strings appearing for the first and only time in that commit. `metric_v2f_oos_result` and `metric_v2f_findings` are both dropped and recreated fresh on every run (`DROP TABLE IF EXISTS` immediately before each `CREATE TABLE`), and both currently hold exactly one `generated_at` timestamp (`2026-08-15T19:36:56.852700+00:00`) — v2f has been run and persisted exactly once, ever. There is no historical row set to check for behavior drift.

## Narrative cross-check **[V]**

`MASTER_HANDOVER_2026-08-15.md:141`: **"Verdict: NULL — the CI does not exclude zero."** — matches the DB exactly. The task's background claim that "every narrative document we hold... reports the result as NULL" is confirmed correct for this document (not exhaustively checked against every other doc in the repo, which was outside this task's scope).

## Verdict

**None of the four provided categories (NAMING-ONLY / DEFECT-INERT / DEFECT-PROPAGATED / UNRESOLVED) accurately fits**, because all four presuppose that some discrepancy or defect exists. It doesn't. Stating this plainly rather than forcing a fit, per the standing instruction:

**No discrepancy found.** The persisted verdict (`metric_v2f_findings.objective2.thesis_verdict`), the code that computes it (`trader_skill_metric_v2f.py:429-444`), and the narrative conclusion carried in `MASTER_HANDOVER_2026-08-15.md` all agree: **NULL**. The field's *location* is arguably a minor documentation gap worth naming even though it isn't a "defect" — `metric_v2f_oos_result` (the table most scripts would naturally check first, since it holds the numbers) carries no verdict column at all; the verdict lives only in `metric_v2f_findings`'s JSON blob. That is a findability quirk, not a correctness problem, and it is the reason the earlier fork's incidental flag was reasonable to raise without yet knowing the answer — it was looking at the table that has no verdict field.

## What remains unverified

- Whether *every* other narrative document beyond the master handover also says NULL (only the master handover was checked, per the task's own §2 reference).
- Whether earlier, unpersisted dry-runs of v2f (if any existed before the single committed/persisted run) ever produced a different verdict string — no such runs are recoverable from the DB or git history; this would require checking any external run logs not covered by this investigation.
