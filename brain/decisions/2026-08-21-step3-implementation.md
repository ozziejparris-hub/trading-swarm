# 2026-08-21 — step 3 (discovery-gap closure), second attempt: IMPLEMENTED

**All verification gates passed. Committed.** Pre-registration:
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`) §A step 3, §B
item 2's step-3 clause. First attempt's stop: `2026-08-21-step3-stop.md`
(`5257f80`). The blocker's removal: `2026-08-21-resolution-sweep-predicate-fix.md`
(`978bb5c`, code `492e028`). Every claim tagged **[V]** (verified this
session, command/file:line given) or **[I]** (inferred, marked
explicitly).

---

## Why this is now unblocked — confirmed, not assumed

**[V]** `scripts/resolution_sweep.py` in the working tree carries the
fix: `grep -n "COALESCE(resolution_recorded_at, last_checked)"` matches
at lines 92, 103, 104. `git log -1 -- scripts/resolution_sweep.py` shows
`492e028` as the current tip. The blocker is present and confirmed before
proceeding.

**[V]** `requeue_resolved_market_traders.py`'s gate re-confirmed: `datetime(last_checked)
> datetime(?)` — not `resolution_date`. `last_checked` is stamped
unconditionally in `fast_resolution_check.py:batch_update_resolved_markets`
(the exact function this attempt edits), via a direct `UPDATE` that runs
regardless of what `resolution_event_time` is passed to
`mark_market_resolved()`. Confirmed still true, not re-derived from the
prior stop's prose.

---

## Fresh consumer re-check — one new item found, checked and cleared

Re-ran the broad `resolution_date` grep, per instruction not to treat the
prior stop's list as complete. One item **not** in the prior stop's
catalogue turned up: `analysis/regret_analysis.py:131`,
`ORDER BY resolution_date DESC`.

**Checked, not a live consumer with the O-16-shaped assumption** [V]:
`get_resolved_markets()`'s `WHERE` clause has **no recency window** —
`WHERE resolved=1 AND winning_outcome IS NOT NULL AND winning_outcome !=
''`, full stop. It fetches the entire resolved population unconditionally
and sorts it; nothing is excluded by a time filter, and the sole caller
(`calculate_comprehensive_stats`-style aggregate regret computation)
consumes the whole list rather than truncating by position. The `ORDER
BY` affects display/iteration order only, not membership — a market with
a historical `closedTime` (post-step-3) still appears in the list, merely
at a different position. Not a conflict.

Re-confirmed, not re-derived: `monitoring/system_observer.py`'s three
metrics (below, unchanged from the prior stop's finding) and
`monitoring/database.py`'s `get_traders_with_recent_evaluated_trades`
(still **dormant** — its only callers remain `monitoring/elo_bridge.py:802,819`,
both inside `--quick-update`/`--update-positions` CLI-only branches,
confirmed zero live call paths). **No fourth live, non-cosmetic instance
found.** Proceeded.

---

## The empirically-established field

**[V]** Sampled 50 real Gamma responses from this pass's own live feed
(`GET /markets?closed=true&limit=50&order=endDate&ascending=false` — the
exact fetch `fetch_all_resolved_markets` performs):

| Field | Populated |
|---|---|
| `closedTime` | **50 / 50** |
| `end_date_iso` | 0 / 50 |
| `resolutionTime` | 0 / 50 |

Confirms register item 2's finding empirically, not inherited. Sample
format: `"2026-08-08 20:33:13+00"` — space-separated (not `T`), a
2-digit UTC offset with no minutes (not `+00:00`, not `Z`). Python 3.12's
`datetime.fromisoformat` parses this directly, unmodified; a defensive
`Z`→`+00:00` replace (matching `hydrate_stub_markets.py`'s
`_parse_date_dt` precedent exactly) is included for robustness against
any format Gamma might send that isn't this session's sample. `endDate`
(`"2029-01-19T23:59:00Z"`, identical across many distinct markets) and
`endDateIso` (`"2029-01-19"`) confirmed placeholder-shaped, consistent
with the sizing work's own finding — not substituted for `closedTime`
anywhere.

---

## The change

Baseline from git, not transcribed [V]:
```
git log --oneline -3 -- scripts/fast_resolution_check.py
  dad2d11 feat: Stage 2 of the canonical resolution write path -- migrate batch_update_resolved_markets, behaviour-preserving
  0a5891c fix: guard resolution_date against overwrite in batch_update_resolved_markets
  a0e0870 fix: co-write resolution_date in fast_resolution_check.py's 3 passes + legendary scripts (O-17)
```
Confirmed working tree byte-identical to `dad2d11` before editing (`diff`
against `git show HEAD:...`, zero output; `sha256sum` match). Copied
verbatim into
`data/characterizations/step3_verification/fast_resolution_check_baseline_dad2d11.py`
(committed).

**New helper, `_parse_closed_time(raw) -> datetime | None`**, mirroring
`hydrate_stub_markets.py:_parse_date_dt`'s exact shape (epoch-int
branch, `Z`-replace, try/except → `None`) — added at module level, not
inside the class.

**One argument at one call site, nothing else:**
```diff
-                        # resolution_event_time is always None: this writer
-                        # never holds a true Gamma event-time (Stage 2 stop,
-                        # Q1), only write-time, which the canonical
-                        # three-tier fallback already supplies identically to
-                        # the retired COALESCE(resolution_date, ?) patch.
+                        # resolution_event_time: discovery-gap closure step 3
+                        # ... Gamma's own `closedTime` field ...
+                        resolution_event_time = _parse_closed_time(market_data.get('closedTime'))
                         mmr_result = mark_market_resolved(
                             conn,
                             market_id,
                             winning_outcome=winner,
-                            resolution_event_time=None,
+                            resolution_event_time=resolution_event_time,
                             evidence_source="gamma",
                             evidence_detail="outcomePrices>=0.99",
                         )
```
`evidence_source`, `evidence_detail`, `winning_outcome`, the `last_checked`
direct write, `conn.commit()`, the accept/reject warning print — all
unchanged. If `closedTime` is absent or unparseable, `_parse_closed_time`
returns `None` and the call falls through to `mark_market_resolved()`'s
existing 3-tier fallback exactly as before — no substitute field used,
per instruction.

---

## Verification

### (b) Before/after dry-run diff — a proper one, not the degenerate kind

**`test_mode=True` skips `mark_market_resolved()` entirely** (the whole
`if not test_mode:` block never runs) — a naive test-mode diff would show
zero difference regardless of the change, the exact inert-diff trap
step 1's first attempt fell into. Built a proper harness instead
(`data/characterizations/step3_verification/gamma_pass_closedtime_precheck.py`,
committed): fetched and **froze** the live 2,100-market Gamma feed once
(`resolved_markets_snapshot.json`, committed) to remove API-timing drift
between before/after, replicated `batch_update_resolved_markets`'s own
matching SQL and `extract_winner` call (not a reimplementation), then
called `mark_market_resolved(dry_run=True)` **twice per genuine
candidate** — once with `resolution_event_time=None` (old), once with
`_parse_closed_time(closedTime)` (new) — comparing the two
`ResolutionWriteResult`s directly, no write either time.

**Result:**
```
Snapshot: 2100 | already_resolved=1612 | not_found=484 | no_winner=0
Genuine candidates: 4
usable closedTime: 4/4
resolution_date DIFFERS: 4/4
resolution_date IDENTICAL: 0/4
```
**Required assertion held for all 4, checked in code, not eyeballed:**
`accepted`, `reason`, `resolved`, `winning_outcome`, and
`resolution_evidence_source` identical between the before/after call for
every candidate (the harness asserts this and would have raised, not
silently passed, on any mismatch) — **only `resolution_date` differs, and
only where `closedTime` was present and parseable.**

**Usable-`closedTime` count, reported plainly per instruction:** 4 of 4
genuine candidates today. **Not near zero — the change is live, not
inert**, on today's data. (Population is small — 4 candidates out of
2,100 fetched — because this pass's own daily yield is small, as observed
throughout this arc; the *rate* among candidates that do convert is what
matters here, and it is 100%.)

### (c) Magnitude — reported honestly, including its limits

| Market | Old (write-time) | New (`closedTime`) | Gap |
|---|---|---|---|
| `0x6cc6478d...` | 2026-08-21 21:13:17 | 2026-08-21 19:41:12 | ~1.5 hours |
| `0xb2486580...` | 2026-08-21 21:13:17 | 2026-08-21 16:42:55 | ~4.5 hours |
| `0xa24100a9...` | 2026-08-21 21:13:17 | 2026-08-14 23:43:42 | ~7 days |
| `0xda1e8975...` | 2026-08-21 21:13:17 | 2026-08-14 23:45:42 | ~7 days |

**Hours to about a week today — not months.** Stated plainly rather than
inflated to match the arc's larger narrative: this specific daily pass
fetches the **top** of Gamma's `endDate`-sorted feed, which skews toward
markets that closed relatively recently; the multi-month mislabeling this
whole arc is about is characteristic of the **historical backlog**
(what `backfill_market_dates.py`/the eventual sweep target), not
necessarily this pass's typical daily catch. On a day when this pass
happens to catch an older, previously-missed resolution (as the broader
sanity-check sample below shows exist, closedTime ranging back to
2026-02-14 in the same feed), the gap would be larger — but today's
actual 4 conversions are modest in magnitude, and that is reported as
observed, not adjusted to look more dramatic.

### Sanity check against `tape_end`

**The exact test that disqualified `accepting_order_timestamp` during the
CLOB investigation, applied here.** Ran against a broader sample than the
4 genuine candidates — every snapshot market matchable to a `market_id`
in the DB with a parseable `closedTime`, regardless of resolved status
(1,532 markets, read-only, no writes):

```
checked=1532, passed=1531, failed=1, no_tape_end=84
failure rate: 0.07%
```
**One failure**, inspected: `closedTime` preceded `tape_end` by **34
seconds** — trivially small, consistent with ordinary processing-order
noise between a trade landing and Gamma's own closure timestamp, not a
field-identity problem. **Nowhere near the multi-month mismatch that
disqualified `accepting_order_timestamp`.** 99.93% pass rate — the field
is what we think it is.

### (d) `run_tests.py`

**16 files run, 15 passed, 1 failed (`test_backtest_window_population.py`,
24 tests, 19 passed)** — matches the standing baseline exactly, no new
failure.

### (e) Confirm no production write — against the actual write target

| | Before | After |
|---|---|---|
| `resolution_evidence_source='gamma'` | 12 | **12** |
| `resolution_evidence_source='hydration_fill'` | 1 | **1** |
| `check_resolution_write_atomicity` | 0 | **0** |

**Additionally, per the same standard the resolution-sweep fix used**:
queried the 4 specific candidate `market_id`s directly against the live
production DB after all verification — **all four still show
`resolved=0`, `resolution_date=NULL`.** Not inferred from a dry-run flag;
checked against the row the write would have touched.

---

## `system_observer.py` — recorded, not fixed

**Named explicitly so it is not rediscovered as a regression.**
`monitoring/system_observer.py`'s three health metrics
(`markets_resolved_24h`, `markets_resolved_7d`, `markets_resolved_count`
— lines ~2190, 2464, 2498) filter `resolved=1 AND resolution_date >
now() - {24h/7d}`, the same write-time assumption this step removes for
the Gamma pass. **Classified live-but-cosmetic in the first attempt's
stop** (`2026-08-21-step3-stop.md`) — an under-reported dashboard metric,
not a lost discovery channel or a data-correctness risk. Once this
commit lands, any Gamma-pass conversion with a `closedTime` older than
24h/7d will **stop counting** toward these three numbers, by design, the
day it happens. **Not modified here — separate follow-up, per
constraint.**

---

## Commit

One commit: `scripts/fast_resolution_check.py` (new module-level helper +
one changed argument at one call site + the surrounding comment) plus
verification artifacts under `data/characterizations/step3_verification/`
(git baseline copy, frozen 2,100-market snapshot, the precheck harness
and its JSON result, dry-run stdout capture). Cleanly revertible — `git
revert` restores `resolution_event_time=None` and removes the helper in
one step.

---

*Generated 2026-08-21. Implemented and verified — the consumer re-check
found one new item (`regret_analysis.py`) and cleared it; the field name
was established empirically (50/50 and 4/4 samples); the before/after
diff used a harness built specifically to avoid the degenerate
zero-diff failure mode `test_mode=True` would otherwise have produced;
the sanity check against `tape_end` passed at 99.93% on a 1,532-row
sample. No production write occurred at any point in this session,
confirmed against the actual write target. Sources:
`scripts/fast_resolution_check.py` (before: `dad2d11`; after: this
session's commit), `monitoring/resolution_writer.py` (unmodified),
`scripts/resolution_sweep.py` (confirmed fixed, `492e028`),
`scripts/requeue_resolved_market_traders.py`,
`analysis/regret_analysis.py`, `monitoring/system_observer.py`,
`monitoring/database.py`, `monitoring/elo_bridge.py` (all read/grepped
this session), live Gamma API probes this session,
`2026-08-21-step3-stop.md` (`5257f80`),
`2026-08-21-resolution-sweep-predicate-fix.md` (`978bb5c`),
`2026-08-21-discovery-gap-closure-prereg.md` (`60a1529`) (all
trading-swarm except first-repo scripts as cited).*
