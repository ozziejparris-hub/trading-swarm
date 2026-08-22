# 2026-08-22 — Tranche 2 Driver Fixes

## SUMMARY: Both defects fixed. A third gap found by full enumeration and fixed alongside them. Both directions verified against the real, unmodified `mark_market_resolved()`. No production code touched. No production DB write.

This is a driver-only fix (`data/characterizations/tranche2_execution/tranche2_write.py`), prompted by tranche 2's pause after batch 1
(`2026-08-22-tranche2-execution.md`, `d9b018f`). Tranche 2 is not resumed
in this task.

All claims tagged **[V]** verified (ran/read it myself) or **[I]** inferred.

---

## Baseline

**[V]** `git log -1 --oneline -- data/characterizations/tranche2_execution/tranche2_write.py`
→ `1a54ad7`, clean, no pending changes, confirmed before any edit.

---

## Full enumeration of `mark_market_resolved()`'s reason strings

**[V]** Read `monitoring/resolution_writer.py` directly, in full, this
session. It can return exactly **9 distinct reason strings** (one is
parameterized with the actual invalid value, otherwise literal). None
were copied from the prior deliverable or this task's prompt without
being checked against the source first.

| Reason string (verbatim) | `accepted` | Reachable from this driver's call pattern? | Classification |
|---|---|---|---|
| `"written"` | True | Yes — the common case | **ACCEPT** |
| `"written: existing value has no recorded evidence_source (pre-canonical), proposal accepted"` | True | Not under SS C's predicate (excludes `resolved=1` rows); kept whitelisted as a matter of design correctness | **ACCEPT** |
| `"written: proposed evidence outranks existing"` | True | **Yes** — if another live writer resolves a sampled market via a lower-ranked source (gamma/manual_verified/hydration_fill) between this run's sample draw and this driver's turn through the batch | **ACCEPT** — SS C's abort condition 6 names this pattern explicitly as "allowed and expected, not an abort trigger." **Missing from the original whitelist — found by this enumeration, not because it had fired.** |
| `"no-op: same-rank value matches existing"` | False | Yes — exactly what batch 1's kill-and-resume test produced 92 times | **ACCEPT** — the comparator correctly declining a redundant write. **The defect this fix addresses.** |
| `"rejected: winning_outcome required unless allow_no_winner=True"` | False | Should never fire — `_extract_clob_resolution()` only classifies `"resolved"` when a winning token was found | PAUSE (defensive; a programming-error signal if ever seen) |
| `"rejected: unknown evidence_source {evidence_source!r}"` | False | Should never fire — this driver always passes `"clob"` literally | PAUSE (defensive) |
| `"rejected: market_id not found"` | False | Should never fire — candidates come from a live query in the same session; nothing deletes from `markets` | PAUSE (defensive) |
| `"no-op: existing value ranks higher than proposed"` | False | **Structurally unreachable** — fires only when `new_rank > existing_rank`; this driver's `new_rank` is always 1 (clob, the minimum), which can never exceed any `existing_rank` (1, 2, or the unranked sentinel 99) | PAUSE (classified for completeness; cannot fire from this call site) |
| `"flagged: same-rank disagreement"` | False | Yes, in principle — two clob-rank sources asserting different outcomes | **PAUSE** — the one genuine concern SS C's abort condition 6 exists to catch. Must never be whitelisted. |

---

## Defect 1: whitelist conflated match with disagreement (plus a second gap found alongside it)

**[V] Fixed.** `ACCEPTED_REASONS` in `tranche2_write.py` now contains all
four ACCEPT-classified reasons above:
```python
ACCEPTED_REASONS = {
    "written",
    "written: existing value has no recorded evidence_source (pre-canonical), proposal accepted",
    "written: proposed evidence outranks existing",   # added
    "no-op: same-rank value matches existing",         # added -- the fix
}
```

**Exact strings verified against the source, not transcribed.** The
verification script (`tranche2_driver_fix_verification.py`, below) calls
the real, unmodified `mark_market_resolved()` against an isolated
in-memory database and compares its actual returned `.reason` strings to
the driver's constant — a hand-typed near-miss would show up as a failed
membership check, not a passing one.

**`"flagged: same-rank disagreement"` confirmed to remain outside the
whitelist — verified by construction, not by inspection alone**: the
verification script fabricates a genuine same-rank disagreement (an
existing `clob`-sourced `"No"` outcome, a new `clob` proposal of
`"Yes"`), calls the real function, and asserts its actual returned reason
string is absent from both the pre-fix and post-fix `ACCEPTED_REASONS`
sets — see checks 3–4 below.

---

## Defect 2: checkpoint skip-list undercounted

**[V] Fixed.** The predicate for adding a market to the checkpoint's
`resolved_market_ids` skip-list changed from `result.reason == "written"`
(the original, narrow check) to `result.reason in ACCEPTED_REASONS` (the
same constant used for the pause-rate check, now covering all four
ACCEPT-classified outcomes). One conditional now serves both purposes,
since both questions — "should this count toward the unpredicted-
rejection rate?" and "is this market now confirmed resolved, correctly?"
— have the identical answer for all nine reasons.

**Predicate used, stated explicitly:** a market enters the skip list if
and only if `mark_market_resolved()`'s reason is one of the four
ACCEPT-classified strings above (fresh write, untagged-legacy-improvement,
cross-rank overwrite, or same-rank match). Open, indeterminate, and
no-CLOB-response classifications never reach `mark_market_resolved()` at
all in this driver's loop (checked by direct code inspection — those
three tally buckets are populated in an `else`/earlier branch that never
calls the function), so they were never at risk of incorrect inclusion.
Genuinely-rejected reasons (the five PAUSE-classified strings, including
same-rank disagreement) are excluded deliberately — per the task's own
instruction, their state may still change and they must remain
re-attemptable, not silently skipped.

---

## Both-directions verification

**[V]** `tranche2_driver_fix_verification.py` (committed alongside the
fix) — opens an **in-memory** SQLite database only (`sqlite3.connect(":memory:")`),
never the production database, and calls the real, unmodified
`mark_market_resolved()` three times against three fabricated scenarios:

```
same_rank_match:        reason='no-op: same-rank value matches existing'  accepted=False
same_rank_disagreement: reason='flagged: same-rank disagreement'          accepted=False
cross_rank_overwrite:   reason='written: proposed evidence outranks existing' accepted=True
```

All nine checks passed:

```
[PASS] same-rank MATCH was NOT whitelisted pre-fix (proves the bug existed)
[PASS] same-rank MATCH IS whitelisted post-fix (proves the fix works)
[PASS] same-rank DISAGREEMENT was NOT whitelisted pre-fix
[PASS] same-rank DISAGREEMENT is STILL NOT whitelisted post-fix (still pauses)
[PASS] cross-rank overwrite was NOT whitelisted pre-fix (a second real gap, found by enumeration)
[PASS] cross-rank overwrite IS whitelisted post-fix
[PASS] skip-list predicate (reason in ACCEPTED_REASONS) is TRUE for same-rank match
[PASS] skip-list predicate is FALSE for same-rank disagreement (must remain re-attemptable)
[PASS] skip-list predicate is TRUE for cross-rank overwrite (confirmed resolved via our write)
```

**The pre-fix comparison set was not retyped** — it was read directly
from `git show 1a54ad7:.../tranche2_write.py` at verification time, so
"this would have failed against the pre-fix code" is checked against the
actual prior committed content, not a description of it.

---

## d. Confirm no production code changed

**[V]** `git diff --stat -- scripts/backfill_market_dates.py monitoring/resolution_writer.py scripts/fast_resolution_check.py scripts/daily_maintenance.py`
returned empty — zero changes to any of the four named files. `git status`
for this task's changes shows exactly two files touched:
`tranche2_write.py` (the fix) and `tranche2_driver_fix_verification.py`
(new, the verification script) — plus the same pre-existing, unrelated
housekeeping files noted in every prior status check this session
(`data/.last_requeue_run`, `data/category_backfill_state.json`,
`logs/arb_bot_exclusions.log`, `logs/focus_ratio_review.json`), not
touched by this task.

## e. No production DB write — verified against the actual write target

**[V]** The verification script's only database connection is
`sqlite3.connect(":memory:")` — confirmed by grepping the script for
every `sqlite3.connect`/`_get_connection` call site (exactly one match,
the in-memory one) and separately confirming the script never references
`polymarket_tracker.db`, `DB_PATH`, or `_get_connection` anywhere at all.
The production database's on-disk mtime (14:59) reflects the
always-on `polymarket-monitoring` service continuing to run in the
background throughout this task, unrelated to anything executed here.

---

## The existing batch-1 checkpoint: leave it as-is, do not rewrite

**Recommendation: leave `data/checkpoints/tranche2_checkpoint.json`
(first-repo `6a6bfaa`) unmodified.** Reasoning:

1. **It is a durable, historical artifact.** It accurately records what
   that specific run actually did (378 fresh writes, tracked under the
   old, narrower skip-list logic) — rewriting it to reflect what the
   *fixed* logic would have recorded blurs the line between "what
   happened" and "what we'd prefer it to say in hindsight," which the
   task explicitly warned against ("do not silently rewrite a durable
   artifact").
2. **It has no functional effect on the intended resume path.** Checked
   directly: the driver's batch loop is `for batch_num in range(batches_completed,
   n_batches)` — since the checkpoint records `batches_completed: 1`, any
   resume starts at batch 2 and **never re-enters batch 1's slice at
   all**. `resolved_market_ids` is only consulted for rows within a batch
   that gets *re-entered* after an interruption; a batch already marked
   complete is never revisited, so its skip-list entries (complete or
   not) are never read again under normal continuation.
3. **Even the edge case is now safe.** The only scenario where this
   checkpoint's incompleteness would matter is a full restart from
   scratch that re-enters batch 1 (e.g. a deliberate reset, not a normal
   continuation). In that case, the 92 already-resolved markets would be
   redundantly re-attempted — but with this fix live, that redundant
   attempt now correctly resolves to a whitelisted no-op, gets added to
   `resolved_market_ids` for the first time as a side effect of that
   re-attempt, and does not pause the run. The gap is self-healing under
   the fixed code, not a residual risk requiring a manual correction.

"Resume accounting for it" (the task's second option) is therefore not a
separate code path to build — it is what the general-case fix already
does, for free, if that path is ever exercised.

---

## What was NOT done, per the constraints

Tranche 2 was not resumed. No production code (`backfill_market_dates.py`,
`resolution_writer.py`, `fast_resolution_check.py`, `daily_maintenance.py`)
was touched. No write reached the production database. One commit in
first-repo, covering the driver fix and its verification script together,
cleanly revertible.
