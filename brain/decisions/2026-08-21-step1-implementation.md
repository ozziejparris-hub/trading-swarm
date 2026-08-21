# 2026-08-21 — step 1 (discovery-gap closure): STOPPED, not implemented

**STOPPED at verification (b.c), per the pre-registration's own falsification
condition 1. Not committed. No production write made anywhere in this
session.** Pre-registration: `2026-08-21-discovery-gap-closure-prereg.md`
(`6f8f884`), §A step 1, §B verification bar. The code change was written,
compiled, and verified against the pre-reg's own bar in full — it passed
the branch-split diff and the test suite, then **failed the read-only
correctness pre-check against the known 317-market population** by a wide
margin (0 resolved found vs. an expected ~203), for a reason traced to
root cause and reported below, not patched around. The working tree has
been reverted to `HEAD` (`446bcde`) — `scripts/backfill_market_dates.py`
carries zero diff. Every claim tagged **[V]** (verified this session,
command/evidence given) or **[I]** (inferred).

---

## What was attempted

Per §A step 1 / §B: a new assertion branch in `backfill_market_dates.py`,
alongside the existing, untouched proxy branch — same two-branches-one-script
pattern Stage 1 established for `hydrate_stub_markets.py`.

- **New helper `_extract_clob_resolution(market_data)`**, added right after
  `_fetch_by_clob`: classifies a CLOB response as `resolved` / `open` /
  `indeterminate`, mirroring `discovery_gap_sizing.py`'s `query_clob()`
  classification exactly (not reinvented) — `closed is None` →
  indeterminate; `closed is False` → open; `closed is True` with no token
  `winner: true` → indeterminate (never asserted with a null winner);
  `closed is True` with a winning token → resolved, winner = that token's
  `outcome`.
- **`backfill()`'s loop**: tracked which strategy produced a hit
  (`matched_via` — `"clob"` / `"gamma_api_id"` / `"gamma_title"`).
  `_extract_clob_resolution` is invoked **only** when `matched_via ==
  "clob"` — Gamma-sourced hits (Strategies 1/2) have no `tokens[].winner`
  field and were never routed through the new classification, exactly as
  specified.
- **When classification is `"resolved"`**: calls
  `mark_market_resolved(conn, market_id, winning_outcome=<token's outcome>,
  resolution_event_time=None, evidence_source="clob",
  evidence_detail="token.winner", dry_run=dry_run)`. `allow_no_winner` is
  never passed (defaults `False`) — unreachable anyway, since this branch
  is only entered when a winner was already found. `end_date` keeps its
  existing unconditional direct write (not a canonical-path column, design
  §A/§D) in a separate statement, unchanged in value/shape from the proxy
  branch's own `end_date = ?`. `ResolutionWriteResult.accepted`/`.reason`
  logged per market; new counters `resolved_accepted`/`resolved_rejected`
  added to the final summary line only (not the periodic progress line —
  see below).
- **All other cases** (`matched_via != "clob"`, or classification `open`/
  `indeterminate`) fall through to the **existing proxy branch, untouched**
  — same `[DRY-RUN]` print, same `UPDATE markets SET end_date = ?,
  resolution_date = COALESCE(resolution_date, ?)` statement, byte-for-byte.

The full attempted diff (117 insertions / 8 deletions) is preserved at
`data/characterizations/step1_verification/attempted_change.diff`
(first-repo, uncommitted — see "State left behind," below).

---

## Baseline from git, not transcribed

```
git log --oneline -3 -- scripts/backfill_market_dates.py
  446bcde feat: CLOB API end_date lookup — permanent resolution date coverage
  4cdd190 feat: market end_date backfill — resolution date coverage for STR-003 signals
```
Confirmed the working tree was byte-identical to `446bcde` before editing —
`diff <(git show HEAD:...) scripts/backfill_market_dates.py` returned
nothing, and the two files' `sha256sum` matched exactly. Copied `git show
HEAD:scripts/backfill_market_dates.py` verbatim into
`data/characterizations/step1_verification/backfill_market_dates_baseline_446bcde.py`
(committed, first-repo) as the durable pre-change artifact — not retyped
from the file or this document's own paraphrase.

---

## Verification (b): before/after dry-run diff, production `--geo-only` scope

Ran the **unmodified** script, then the **modified** script, both
`--dry-run --geo-only --limit 2000` (the production invocation shape,
`daily_maintenance.py` step "Backfill market dates"), against the same
unchanged DB snapshot (no write occurred between the two runs — nothing in
either dry-run writes).

```
diff pre_dryrun_geoonly.txt post_dryrun_geoonly.txt
6c6
< [BACKFILL] Done — updated=0, not_found=360, skipped_no_api_id=0, errors=0, total=360
---
> [BACKFILL] Done — updated=0, not_found=360, skipped_no_api_id=0, errors=0, resolved_accepted=0, resolved_rejected=0, total=360
```

**Result: the only line that differs is the final summary line, gaining
two new, zero-valued fields.** Every pre-existing field's value
(`updated`, `not_found`, `skipped_no_api_id`, `errors`, `total`) is
identical, and all three periodic progress lines are byte-identical —
confirmed by first reverting the periodic-progress-line print to its
exact original text (an earlier draft of this change had added the new
counters there too; reverted specifically to keep this diff's surface
minimal and unambiguous before running it).

**Why this diff would fail if the change were wrong, stated plainly, not
just "it passed":** if the new classification logic incorrectly matched a
`gamma_api_id`/`gamma_title`-sourced response as CLOB-resolved (a
plumbing bug in the `matched_via` gating), or if it misparsed a
still-open market as resolved, or if the proxy branch's own `UPDATE`
statement or `[DRY-RUN]` print format had been accidentally altered
while editing nearby code, this diff would show either a changed
`not_found`/`updated`/`errors` value, a missing or reformatted
`[DRY-RUN]` line, or a nonzero `resolved_accepted`/`resolved_rejected`
count where the pre-change run has none to compare against — any of
those would be a real, load-bearing failure of this specific check. None
occurred.

**Honest limitation of this specific result, not glossed over:** today's
production `--geo-only` candidate population (360 markets) is, right now,
**100% `not_found` under all three strategies** — `_fetch_by_clob` never
returned a usable response for any of the 360 during either run (see the
root-cause finding below for why). This means the diff is a **real and
valid proof that the proxy branch is untouched**, but it is **weak
evidence for the assertion branch specifically** — zero markets in this
particular population exercised the new classification/`mark_market_resolved()`
call path at all. That is exactly why §B.c (below) exists as a separate,
required check against a population with a known answer, not a
substitute for it — and it is exactly where this attempt failed.

---

## Verification (c): read-only correctness pre-check, 317-market Q2 census — **FAILED**

**Freshly re-derived** (not the stale 08-20 figure) via the exact §3
predicate, `2026-08-20-discovery-gap-sizing-prereg.md`:
```sql
SELECT COUNT(*) FROM markets m
JOIN (SELECT DISTINCT market_id FROM trades) t ON t.market_id = m.market_id
WHERE (m.resolved = 0 OR m.resolved IS NULL)
  AND m.resolution_date IS NULL AND m.end_date IS NULL
  AND m.category IN ('Elections','Geopolitics')
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL);
```
**317** [V] — unchanged from 08-20 and from this session's own earlier
status check. Since the script has no native "run against this explicit
market_id list" mode (its own candidate query is scoped by `--geo-only`'s
JOIN or the full population, not an arbitrary list), a small read-only
harness (`data/characterizations/step1_verification/q2_census_precheck.py`,
committed) called the **modified** script's own `_fetch_by_clob` and
`_extract_clob_resolution` directly against these 317 live market_ids, and
`mark_market_resolved(..., dry_run=True)` for every one classified
`"resolved"` — read-only throughout (DB opened `mode=ro`; `dry_run=True`
returns before `mark_market_resolved()` reaches its own `UPDATE`).

**Result:**

| | Expected (08-20, for context — not treated as gospel) | This session, live |
|---|---|---|
| resolved | ~203 | **0** |
| open | ~98 | 1 |
| indeterminate | ~16 | 0 |
| no CLOB response at all | 0 (not a category in the 08-20 method) | **316** |

**This is a materially different result — the branch is built on a wrong
assumption about the response shape, per the pre-reg's own falsification
condition 1. Stop, not a tweak.**

### Root cause, traced, not assumed

Live raw-API check, 3 of the 317 market_ids sampled directly (not through
either script):

```
GET https://clob.polymarket.com/markets/0x005aa3a9e019fade8240f0651b631d27fa74549aed52dea9a95a5de9533b119f
  closed: True | end_date_iso: None | tokens: [{'outcome':'Yes','winner':True}, {'outcome':'No','winner':False}]
GET .../0x02f8dd15d4c674a75fccbd0e00f0cf1256101c45ef41f6d0c5dfde9c36d4141e
  closed: True | end_date_iso: None | tokens_winner: [True, False]
GET .../0x0425c582c43e27c6d74af7a553c1ce68b32bacdc77f0b23d62cdfe8aa1da0556
  closed: True | end_date_iso: None | tokens_winner: [False, True]
```

**3 of 3 sampled resolved markets have `closed=True`, a real winning
token, and `end_date_iso: None`.** `_fetch_by_clob` (unchanged by this
session's edit — this is the script's pre-existing, original gate) only
returns a response at all when `data.get("end_date_iso") or
data.get("endDateIso")` is truthy (`backfill_market_dates.py:74`,
original code). For these markets that evaluates `None or None` →
falsy → `_fetch_by_clob` returns `None`, exactly as if CLOB had never
answered — the caller never sees `closed`/`tokens` at all, because the
existing gate discards the response before either field is ever read.

**This is not a bug introduced by this session's edit.** The new
classification code (`_extract_clob_resolution`) unit-tests correctly
against synthetic inputs (confirmed this session: `open`/`resolved`/
`indeterminate` all classify as expected — see below) and was never
reached for 316 of 317 real markets, because the pre-existing
`_fetch_by_clob` gate — built for the proxy branch's original,
different purpose (finding a *scheduled end date* to backfill) — silently
filters out almost this entire population before the new logic ever runs.

**Why this specifically falsifies the pre-reg's assumption:** §A step 1's
premise, and the assessment's own headline finding
(`2026-08-21-discovery-fix-assessment.md`), was "the response it already
fetches carries `closed` and `tokens[].winner` — currently unread." That
is true **only for the small subset of markets where a response comes
back at all** — which, for this specific 317-market population, is
essentially none of them, for a reason (`end_date_iso` absence)
structurally unrelated to whether the market is resolved. The assumption
that today's `_fetch_by_clob` already *reaches* the population step 1
needs was wrong; the fact that it would correctly *classify* what it
receives, if it received anything, does not rescue the branch's practical
coverage.

**Unit-level confirmation the new logic itself is correct, isolated from
the reach problem** [V], this session:
```python
_extract_clob_resolution({'closed': False})
  → ('open', None)
_extract_clob_resolution({'closed': True, 'tokens': [{'outcome':'Yes','winner':False},{'outcome':'No','winner':True}]})
  → ('resolved', 'No')
_extract_clob_resolution({'closed': True, 'tokens': [{'outcome':'Yes','winner':False},{'outcome':'No','winner':False}]})
  → ('indeterminate', None)
_extract_clob_resolution({'closed': None})
  → ('indeterminate', None)
```
All four match the specified classification exactly. **The stop is about
reach, not about the classification logic being wrong** — but reach is
what the whole point of this step is, so this is still a real stop, not
a footnote.

**What this means for the pre-registration, stated as a finding, not a
fix proposed here:** closing this gap for real will require either (a)
loosening `_fetch_by_clob`'s own success gate to also accept a response
based on `closed`/`tokens` presence alone (not requiring `end_date_iso`)
— which is itself a behavioral change to the **proxy branch's** own reach
and would need its own dry-run diff and explicit review, since it changes
which markets the existing, currently-untouched code path even sees — or
(b) a different fetch path for the assertion branch specifically. Neither
is decided or implemented here; this is squarely the kind of finding the
pre-reg's falsification condition 1 exists to surface before a sweep, not
after one.

---

## Verification (d): `run_tests.py`

`python3 run_tests.py --verbose`, run against the **modified** (not yet
reverted) code: **16 files run, 15 passed, 1 failed
(`test_backtest_window_population.py`, 24 tests, 19 passed)** — matches
the standing baseline exactly, no new failure. Full output preserved
(`/tmp/run_tests_step1_output.txt`, not committed — ephemeral, the
summary above is the durable record).

---

## Verification (e): confirm no production write occurred

Re-derived live, not trusted from the session-start figures:

| | Pre-change (this session's own earlier baseline) | Post-verification |
|---|---|---|
| `resolution_evidence_source='clob'` | 0 (no row) | **0 (no row)** |
| `resolution_evidence_source='gamma'` | 12 | **12** |
| `resolution_evidence_source='hydration_fill'` | 1 | **1** |
| `check_resolution_write_atomicity` | 0 | **0** |

**Unchanged.** No production write occurred at any point — every call
into `mark_market_resolved()` during this session (unit tests aside, which
called it zero times; the 317-market pre-check called it zero times since
zero markets classified `"resolved"`) used `dry_run=True` or never
reached the function at all.

---

## The two deferred items

1. **`ORDER BY market_id`** — not implemented, per §C's own instruction.
   The production invocation uses `--limit`, so adding an ordering would
   change *which* 360 (or N) markets get selected each run — a legitimate
   behavioral difference the diff bar (§B.b) would have to account for,
   and it belongs to the sweep driver (step 4), which owns
   resumability/batch semantics, not step 1.
2. **Pacing (`--sleep`, default `0.1`, unchanged)** — implemented, as an
   additive optional parameter threaded through `backfill()` and
   `main()`'s argparse, judged safe to include: `time.sleep()` produces no
   stdout, so it cannot affect any diff comparison in §B.b, and with no
   `--sleep` override the value is identical to today's hardcoded `0.1` —
   zero behavioral difference for the current scheduled invocation, which
   passes no such flag. Step 4's sweep driver would pass `--sleep 0.25`
   explicitly, per the pre-reg. **This part of the attempted change is
   itself uncontroversial and remains available in the preserved diff**
   (`attempted_change.diff`) for reuse once the reach problem above is
   resolved — it is not what caused the stop.

---

## State left behind

- **`scripts/backfill_market_dates.py`: reverted to `HEAD` (`446bcde`),
  confirmed byte-identical via `diff`.** Not committed. No code change is
  live.
- **Preserved, committed artifacts** (first-repo,
  `data/characterizations/step1_verification/`):
  `backfill_market_dates_baseline_446bcde.py` (the git-sourced baseline),
  `pre_dryrun_geoonly.txt` / `post_dryrun_geoonly.txt` (the §B.b diff
  inputs), `attempted_change.diff` (the full attempted patch, for reuse),
  `q2_census_precheck.py` (the verification harness), and
  `q2_census_precheck_result.json` (the per-market detail behind the
  0/1/0/316 tally).
- **`monitoring/resolution_writer.py`, `scripts/fast_resolution_check.py`,
  `scripts/hydrate_stub_markets.py`: untouched**, confirmed via `git
  status` — clean.

---

## Recommendation

**Do not proceed to step 2, 3, or 4 on this branch of work until the
reach problem is resolved and re-verified.** The classification logic
itself is sound (confirmed at the unit level); what needs a decision is
whether and how to widen `_fetch_by_clob`'s own success gate — a change
to the **proxy branch**, which is explicitly out of step 1's stated scope
("proxy branch: untouched, byte-for-byte") and would need its own
pre-registration amendment or a separate, explicitly-scoped step, since
loosening that gate changes what the *existing*, already-scheduled
behavior sees, not just what the new branch sees. Reported here rather
than decided unilaterally, per the standing instruction.

---

*Generated 2026-08-21. STOPPED, not implemented — no commit made in
first-repo for the code change itself (the verification artifacts under
`data/characterizations/step1_verification/` are new, uncommitted files;
see the commit note below). No production write occurred. Sources:
`scripts/backfill_market_dates.py` (`HEAD`, `446bcde`),
`monitoring/resolution_writer.py`,
`2026-08-21-discovery-gap-closure-prereg.md` (`6f8f884`),
`2026-08-21-discovery-fix-assessment.md` (`391db02`),
`2026-08-20-discovery-gap-sizing-prereg.md`, `discovery_gap_sizing.py`
(first-repo), live DB queries and live CLOB API probes this session.*
