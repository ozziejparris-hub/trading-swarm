# 2026-08-21 — step 1 (discovery-gap closure), second attempt: IMPLEMENTED

**All verification gates passed. Committed.** Pre-registration:
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`, as amended) — §A
step 1, §B including the 2026-08-21 amendment and the renumbered
verification items 1-5. First attempt and its stop:
`2026-08-21-step1-implementation.md` (`d41d02b`). Every claim tagged
**[V]** (verified this session, command/evidence given) or **[I]**
(inferred).

---

## What changed

Two things, per the amended pre-reg:

### 1. Gate separation

`_fetch_by_clob` no longer gates on `end_date_iso` presence. It now
returns the parsed response whenever the HTTP call itself succeeds (200,
valid JSON) — `None` only on a genuine fetch failure. The date test that
used to live inside the function moved to the caller.

### 2. The two branches, using the separated fetch

In `backfill()`'s loop, the CLOB identifier-fallback loop (`condition_id`,
then `market_id`) now tracks two things independently:
- **`market_data`** — set only when a response carries a usable date,
  via the *exact same trigger condition and break/continue mechanics* the
  old, gated `_fetch_by_clob` produced. This is what the proxy branch
  still uses, completely unchanged below it.
- **`clob_response`** — the first raw response obtained from CLOB
  regardless of whether it carries a date, captured as a side channel that
  does not alter the `market_data` loop's iteration or break logic at all.

Immediately after the CLOB loop, **ahead of** the Gamma fallback
strategies and the `not_found` skip: if `clob_response` is present, it's
classified via `_extract_clob_resolution` (mirrors
`discovery_gap_sizing.py`'s `query_clob()` exactly — `closed is None` →
indeterminate; `closed is False` → open; `closed is True` with a winning
token → resolved; `closed is True` with no winning token → indeterminate,
never asserted with a null winner). If `"resolved"`:

```python
result = mark_market_resolved(
    conn, market_id,
    winning_outcome=clob_winner,          # the outcome name of the token with winner: true
    resolution_event_time=None,           # CLOB has no event-time field — closed negative, Q1
    evidence_source="clob",
    evidence_detail="token.winner",
    dry_run=dry_run,
)
```

`allow_no_winner` is never passed — unreachable, since this branch only
fires when a winner was already found by `_extract_clob_resolution`.
`end_date` keeps a direct, best-effort write in the same branch (not a
canonical-path column) using whatever date field the same already-fetched
response happens to carry — often `None` for resolved markets, in which
case nothing is written, which is correct. `ResolutionWriteResult`'s
`accepted`/`reason` is logged per market; the branch then `continue`s,
skipping the entire proxy-branch code path below for that market.

**Everything below that `continue` — the Gamma fallback strategies, the
`not_found`/`skipped_no_api_id` accounting, `end_date_str` derivation, the
proxy `UPDATE` statement, the `[DRY-RUN]` print — is untouched, byte-for-
byte, from the pre-change file.**

New counters `resolved_accepted`/`resolved_rejected`, added to the final
summary line only (not the periodic progress line, kept byte-identical to
minimize the diff surface). Additive `--sleep` parameter, default `0.1`
unchanged, threaded through `backfill()`/`main()`.

---

## Baseline from git, not transcribed

```
git log --oneline -3 -- scripts/backfill_market_dates.py
  446bcde feat: CLOB API end_date lookup — permanent resolution date coverage
  4cdd190 feat: market end_date backfill — resolution date coverage for STR-003 signals
```
Confirmed the working tree was byte-identical to `446bcde` before editing
(`diff <(git show HEAD:...) scripts/backfill_market_dates.py`, zero
output; `sha256sum` match). Copied `git show HEAD:...` verbatim into
`data/characterizations/step1_verification_v2/backfill_market_dates_baseline_446bcde.py`
(committed, first-repo).

**One operational note, disclosed rather than hidden:** an early
`git checkout -- scripts/backfill_market_dates.py`, issued out of habit
from the first attempt's cleanup step, briefly reverted this session's own
in-progress (uncommitted) edit before verification began. No production
data was touched by this — the file was simply rewritten from the
already-validated content and re-verified via `py_compile` and the unit
checks below before any dry-run was run against it. Recorded here per the
standing instruction to report rather than gloss over, even though it had
no effect on the DB or on any result below.

---

## Verification 1: unit-level correctness of `_extract_clob_resolution`

**[V]**, isolated from the reach question entirely:
```python
_extract_clob_resolution({'closed': False})                                    → ('open', None)
_extract_clob_resolution({'closed': True, 'tokens': [Yes:False, No:True]})      → ('resolved', 'No')
_extract_clob_resolution({'closed': True, 'tokens': [Yes:False, No:False]})     → ('indeterminate', None)
_extract_clob_resolution({'closed': None})                                      → ('indeterminate', None)
```
All four match the specified classification exactly — unchanged from the
first attempt, since this logic was never the problem.

---

## Verification 2: branch-split dry-run diff, production `--geo-only` scope

Ran the **unmodified** script (`git show HEAD:...` copied to a sibling
file in `scripts/` so its relative `DB_PATH` resolves correctly, deleted
after use — safer than overwriting the live file in place, which is what
caused the operational note above the first time), then the **modified**
script, both `--dry-run --geo-only --limit 2000`, against the same
unchanged DB snapshot.

**Result:**
```
Before: [BACKFILL] Done — updated=0, not_found=360, skipped_no_api_id=0, errors=0, total=360
After:  [BACKFILL] Done — updated=215, not_found=145, skipped_no_api_id=0, errors=0,
                    resolved_accepted=215, resolved_rejected=0, total=360
```

**215 + 145 = 360 — exactly the original total, fully accounted for.**
Every one of the 215 markets the new assertion branch now correctly
identifies as resolved was, under the old code, silently absorbed into
the `not_found=360` bucket (the pre-change run shows **zero** distinction
between "genuinely unfindable" and "found but discarded by the
`end_date_iso` gate" — both looked identical: `not_found`). The 145 that
remain `not_found` after the fix are markets the fix does not and should
not touch — no CLOB response, or a CLOB response indicating `open`/
`indeterminate`, or a resolved CLOB response but a fallback failure
unrelated to `end_date_iso`.

**Proxy branch: zero behavioral difference — a stronger claim than the
first attempt's, verified precisely.** This is now a claim about a moved
gate, not an additive branch, and the diff supports it directly: **zero**
markets in today's production `--geo-only` population exercise genuine
proxy-branch write logic in *either* run (0 `[DRY-RUN]` lines without the
`[CLOB-ASSERT]` tag appear in either file) — the population's `open`/
`indeterminate`/`no_clob_response` markets (145 of them) all fail the
Gamma fallback identically before and after, landing on `not_found` by
the same unchanged code path in both runs. **Honestly limited, stated
plainly, same limitation as the first attempt:** this specific population
does not contain a market that reaches the proxy branch's own `UPDATE`
statement today, so this diff cannot demonstrate that statement itself is
unchanged in *behavior when triggered* — only that the code controlling
whether it is reached is unchanged (confirmed via full read of the
post-change file, §"What changed" above: the proxy-branch code block is
textually byte-for-byte identical to the pre-change file, not merely
diff-silent by chance of population). The decisive test for whether the
new logic itself is *correct*, independent of today's population
composition, is Verification 3.

**Why this diff would fail if the change were wrong:** if the
`market_data`/break-continue mechanics I rewrote to reproduce the old
gate had a bug — e.g., if `clob_response` capture interfered with the
loop's iteration over `[condition_id, market_id]`, or if the assertion
branch's early `continue` fired for an `open` market — the `145`/`215`
split would not sum to `360`, or an `open`-classified market would show
up as a spurious `[DRY-RUN][CLOB-ASSERT]` line, or the proxy branch's own
`not_found` count would drop below `145` (evidence of a market being
wrongly diverted). None of these occurred.

---

## Verification 3: the correctness pre-check — **the decisive gate, passed**

Freshly re-derived Q2 census population (not the stale 08-20 figure),
exact §3 predicate, `2026-08-20-discovery-gap-sizing-prereg.md`: **317**
[V] — unchanged from every prior session this week. Ran the harness
(`data/characterizations/step1_verification_v2/q2_census_precheck.py`,
committed), calling the **modified** script's own `_fetch_by_clob` /
`_extract_clob_resolution` against these 317 live market_ids, and
`mark_market_resolved(..., dry_run=True)` for every one classified
resolved — read-only throughout (DB opened `mode=ro`).

**Result:**

| | 08-20 sizing run (context only) | This session, live, second attempt |
|---|---|---|
| resolved | 203 | **203** |
| open | 98 | **98** |
| indeterminate / no-CLOB-response | 16 (all `http_404`) | **16** (all `no_clob_response`) |
| indeterminate rate (of classifiable) | 5.05% | **0.0%** — zero `closed:true, no winner` cases this run |

**Exact match to the freshly re-derived expectation — 203/98/16, to the
digit.** `mark_market_resolved(dry_run=True)`: **203 accepted, 0
rejected**, all `reason='written'` (every one a first-time resolution —
`resolved=0` in the DB today, consistent with the cluster's own history
that all prior production calls have landed on the trivial accept-on-
unresolved branch). Full per-market detail:
`data/characterizations/step1_verification_v2/q2_census_precheck_result.json`.

**This is what caught the inert branch last time and the clean
branch-split diff did not.** The first attempt's branch-split diff was
equally clean — proxy branch untouched, zero crashes — while the
assertion branch had, in practice, zero reach (0 of 317 resolved). This
run's branch-split diff (Verification 2) is *also* clean, but this time
the pre-check confirms the branch actually works at the scale that
matters: not merely "nothing broke," but "the thing this step exists to
build now does what it's supposed to."

**Per the amended falsification condition 1** (§I,
`2026-08-21-discovery-gap-closure-prereg.md`): this was the "second
failure" checkpoint — had the pre-check still not reproduced ~203 after
the gate separation, the conclusion would have been that the CLOB-by-
market_id shape itself is in question, not merely reach. It did reproduce
it, exactly. The gate-separation diagnosis from the first attempt is
confirmed correct, not merely plausible.

---

## Verification 4: no partial credit, gates run in full

Both Verifications 2 and 3 passed on the same, single, clean attempt — no
delta-on-a-failed-attempt was needed. Recorded per the pre-reg's own
requirement that this be stated explicitly regardless of outcome.

---

## Verification 5: `run_tests.py`

**16 files run, 15 passed, 1 failed (`test_backtest_window_population.py`,
24 tests, 19 passed)** — matches the standing baseline exactly, no new
failure. `test_mark_market_resolved.py`: still `PASS` (26/26, unaffected —
`mark_market_resolved()` itself was not modified). Full output:
`/tmp/run_tests_step1_v2_output.txt` (not committed, ephemeral; this
summary is the durable record, matching the convention the first attempt
used).

---

## Verification 6: confirm no production write occurred

Re-derived live, not trusted from any prior session's figures:

| | Pre-verification | Post-verification |
|---|---|---|
| `resolution_evidence_source='clob'` | 0 (no row) | **0 (no row)** |
| `resolution_evidence_source='gamma'` | 12 | **12** |
| `resolution_evidence_source='hydration_fill'` | 1 | **1** |
| `check_resolution_write_atomicity` | 0 | **0** |

**Unchanged.** Every `mark_market_resolved()` call this session — the
branch-split diff's 215, the pre-check's 203 — used `dry_run=True`. Zero
production writes anywhere. `git status` confirms `monitoring/resolution_writer.py`,
`scripts/fast_resolution_check.py`, and `scripts/hydrate_stub_markets.py`
are all clean — none touched.

---

## The three deferred items — confirmed still deferred

1. **`ORDER BY market_id`** — not implemented. Belongs to the sweep driver
   (step 4); the production `--limit`-based invocation means adding an
   ordering would change *which* markets are selected, a real behavioral
   difference outside this step's scope.
2. **Pacing (`--sleep`, default `0.1`, unchanged)** — implemented as an
   additive parameter, same reasoning as the first attempt: `time.sleep()`
   has no stdout footprint and cannot appear in any diff comparison, and
   with no override the value is identical to today's hardcoded `0.1` —
   confirmed zero-risk again by the clean diff above (no discrepancy
   attributable to this addition). Step 4's sweep driver would pass
   `--sleep 0.25` explicitly.
3. **Scope widening (`--geo-only`)** — untouched. `get_markets_to_backfill`
   is byte-for-byte identical to the pre-change file; today's production
   invocation still runs `--geo-only --limit 500`. Widening is step 2,
   not attempted here.

---

## Commit

One commit, `scripts/backfill_market_dates.py` (147 insertions / 15
deletions from `446bcde`) plus the verification artifacts under
`data/characterizations/step1_verification_v2/` (baseline copy, pre/post
dry-run captures, the correctness-pre-check harness and its result JSON).
Cleanly revertible — `git revert` restores the pre-change gate and removes
both branches in one step, same as any other writer migration in this
arc.

---

*Generated 2026-08-21. Implemented and verified — all gates in
`2026-08-21-discovery-gap-closure-prereg.md` §B (as amended, `60a1529`)
passed on the first attempt against the revised scope. No production
write occurred at any point in this session. Sources:
`scripts/backfill_market_dates.py` (before: `446bcde`; after: this
session's commit), `monitoring/resolution_writer.py` (unmodified),
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`),
`2026-08-21-step1-implementation.md` (`d41d02b`),
`2026-08-20-discovery-gap-sizing-prereg.md`, `discovery_gap_sizing.py`
(first-repo), live DB queries this session.*
