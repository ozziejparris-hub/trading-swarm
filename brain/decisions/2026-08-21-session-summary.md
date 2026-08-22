# Session Summary — 2026-08-21

## THEME

The session took the accepted repair recommendation from assessment to
pre-registration to three shipped code changes — through five stops, each
of which found a real problem before code was written or shipped. The
stops are the story, not an interruption to it.

## FOUR REUSABLE LESSONS (record them)

**A diff that compares before and after cannot detect a change that does
nothing.** Step 1's first attempt passed its branch-split dry-run diff
cleanly while the new branch had zero reach — `_fetch_by_clob`'s existing
gate discarded the response before the new logic ever saw it, so "proxy
branch untouched" and "assertion branch touches nothing" produced the
identical clean diff. Only a check against a population whose answer was
already known (the 317-market Q2 census) caught it. That check had been
an optional addition in the first attempt; the pre-registration was
amended to make it a required gate. Behaviour preservation and actually
working are different claims requiring different tests.

**An assumption embedded in a column holds only for the callers that
existed when it was written.** Three instances in one session:
`_fetch_by_clob`'s date gate (built for the proxy branch's needs, silently
wrong the moment the assertion branch needed something else from the same
response); `resolution_date` as write-time (correct for its original
readers, wrong for a reader wanting genuine event-time); `last_checked`
as a universal freshness signal (correct while every writer stamped it,
silently wrong once two new canonical-path writers didn't). Each was
correct when written and silently wrong for the next caller. When adding
a caller to shared code, ask what the existing shape assumes about its
consumers.

**Fixing a bug where it was found is not fixing the assumption.** `f5fae64`
fixed one consumer of the resolution-date-as-write-time assumption
(`requeue_resolved_market_traders.py`) and left at least three others
carrying it — `resolution_sweep.py` (live, fixed this session),
`system_observer.py` (live, cosmetic, still open), `elo_bridge.py`'s
`--quick-update` (dormant). Same shape as a drift check covering one
column but not a sibling one.

**Predicting the shape is not predicting the location.** The task prompt
predicted the O-16 failure would recur via
`requeue_resolved_market_traders.py` and was wrong about where — that
specific gate had already been fixed five weeks earlier, on the same day
the O-16 audit found it. But the shape was right and existed elsewhere,
unnamed: `resolution_sweep.py` carries the identical
`resolution_date`-as-recency assumption, live, scheduled, untouched. The
blocking-question pattern is what surfaced it; the specific hypothesis
was merely the prompt for looking.

## WHAT WAS ACHIEVED

1. **Progress check, no committed artifact — figures recorded here
   directly.** Stage 1 and Stage 2 both survived their first unattended
   runs. The decisive check: `resolution_evidence_source='gamma'` went
   9 → 12 (9 was Stage 2's own end-of-session count on 2026-08-20),
   matching "Markets updated: 3" from the Gamma pass's own run exactly —
   not the ~1,617-row legacy population size, confirming the
   behaviour-preserving guard held when nobody was watching. Zero trigger
   fires, `check_resolution_write_atomicity` still 0, all writes still on
   the trivial accept-on-unresolved branch. Also visible in the same
   pass: 2,100 fetched, 1,626 skipped as already-resolved, 471 not-found,
   3 updated — the discovery gap showing up in ordinary daily operation.
   Stage 1's hydrate step ran and did nothing (200 processed, 0 updated).
   A reboot at 03:00 (kernel upgrade via unattended-upgrades, services
   recovered clean). Also reconfirmed this session, carried from
   2026-08-20's own correction: `trades.timestamp` is execution time, not
   insertion time, so a timestamp gap cannot by itself indicate collector
   downtime — any future ingestion-stall detector must key on insertion
   order or rowid.

2. **The fix assessment — repair, not new.** The headline finding was a
   sixth writer absent from the 13-writer census:
   `backfill_market_dates.py` already queries CLOB by
   market_id-as-condition_id, already runs daily, and all 203
   confirmed-resolved markets from the 08-20 sizing run already satisfy
   its candidate query. It fetches the response carrying `closed` and
   `tokens[].winner` and never reads them. The census missed it because
   that census was scoped to writers that assert resolution, and this one
   only writes date-proxy fields — a real limitation of how the census
   was scoped, recorded as a finding. Gamma keyset (shape B) rejected: no
   cost bound, no completion guarantee — the underlying `endDate`
   tie-heavy sort key persists regardless of pagination depth. Root cause
   of the dateless population traced to two ingestion paths
   (`background_backfill_worker.py`, `store_market_from_trade`) that never
   make a market-detail call at creation (shape D — a viable complement,
   not a substitute). Critically: the growth-rate finding —
   513,574 of 514,043 dateless-unresolved rows are `category='Unknown'`,
   so the 317-market Q2 census is a 0.06% sliver of the dateless
   population, and its overnight flatness (317 → 317) is a measurement
   floor imposed by a separate, rate-limited category-classification
   backlog, not evidence of stability. Any fix scoped to `--geo-only`
   inherits that lag.
   (`2026-08-21-discovery-fix-assessment.md`, `391db02`)

3. **The pre-registration — five operations, plus a measurement, all
   fixed before anything ran.** It caught something that would have
   destroyed the result of record silently:
   `trader_skill_metric_v2f.py:449` does `DROP TABLE IF EXISTS
   metric_v2f_oos_result` before recreating it, so the stock `--persist`
   path would have deleted the original row — the artifact Oscar had just
   decided stands permanently. Fixed by specification: unmodified
   pipeline functions, no `--persist`, distinctly-named output tables
   (`metric_v2f_oos_result_corrected`,
   `metric_v2f_intersection_cohort_corrected`). Oscar's decision recorded
   as option (c): the result of record stands permanently; the
   recomputation is a second, separately-named measurement; both figures
   stand side by side; the finding of interest is the delta. The
   interpretation rule was fixed in writing before any corrected number
   exists, including the expected direction (gap narrows, because
   affected cohort positions carry a mean edge of ~0.00056 against a
   published +0.0316 while affected placebo positions carry ~0.01143
   against +0.0127) and what each of narrows/holds/widens would mean.
   §F also closes the reproducibility gap that made 2026-08-16's audit
   unreproducible: the OOS cohort and placebo trader sets are computed in
   `main()` and never persisted today; the corrected run will persist
   them to two new tables.
   (`2026-08-21-discovery-gap-closure-prereg.md`, `6f8f884`, amended
   `60a1529`)

4. **Five stops, each finding something real — the session's actual
   substance:**

   **STOP 1 (step 1, first attempt).** Built the assertion branch exactly
   as specified, passed the branch-split dry-run diff cleanly, then
   failed the read-only correctness pre-check: 0 resolved against an
   expected ~203, with 316 of 317 census markets returning no CLOB
   response at all. Root cause: `_fetch_by_clob`'s existing success gate
   discards a fetched, fully-parsed response whenever `end_date_iso` is
   null, regardless of whether `closed`/`winner` are present — confirmed
   by sampling 3 of the 316 directly against the live API (all three
   `closed: true`, a real winning token, `end_date_iso: null`). The gate
   conflates "did we get a usable date?" with "did we get a usable
   response?" — correct for its only caller when written, wrong the
   moment a second caller needed something else. Same one-artifact/
   two-questions shape as `resolution_date` itself.
   (`2026-08-21-step1-implementation.md`, `d41d02b`)

   **STOP 2 (step 3, first attempt).** The task prompt predicted the O-16
   shape would recur via `requeue_resolved_market_traders.py`'s date
   gate. Wrong — that gate keys on `last_checked`, already fixed in
   `f5fae64` on the same day as the O-16 audit (2026-07-07). But a real
   conflict existed in a consumer nobody had named: `resolution_sweep.py`
   queries `resolved=1 AND resolution_date >= now()-7d`, the identical
   write-time assumption, never fixed. Proof: all 12 gamma-tagged rows
   show `resolution_date == last_checked` to the microsecond — they pass
   only because nothing yet supplies a real event-time. The predicted
   shape was right; the predicted location was wrong.
   (`2026-08-21-step3-stop.md`, `5257f80`)

   **STOP 3 (the sweep predicate fix, first attempt).** The `f5fae64`
   pattern does not transfer. A naive swap to `last_checked` alone grows
   the unscoped candidate set 140 → 215 (+54%), the 85 added rows being
   markets resolved months ago but merely revisited recently (confirmed
   by sampling 15 directly). More decisively: `f5fae64` worked only
   because it *also* added a writer that stamps `last_checked` — and
   neither `hydrate_stub_markets.py` nor `backfill_market_dates.py`
   stamps it, so switching would have silently dropped this arc's own two
   newest canonical writers from Channel 2 discovery. Live proof: the
   one `hydration_fill` row shows `resolution_recorded_at` = yesterday
   against `last_checked` ~8 months stale.
   (`2026-08-21-resolution-sweep-predicate-fix-stop.md`, `6ab0c75`)

   **STOP 4 (step 2, first attempt).** Widening scope plus a higher
   `--limit`, with no `ORDER BY`, was predicted to recreate hydrate's
   no-progress trap gradually. It is real but *immediate*, not gradual,
   and benign in cause: rows 1–98 of the insertion-ordered scan are
   2020-era markets CLOB has permanently purged, confirmed by direct
   `curl` as genuine 404s — a fixed ~20% tax on a 500-row daily budget,
   realized from the very first run, not accumulated over time. Row 99
   onward is productive — 40.0% resolved over a 300-row live sample.
   Blocking question 2 resolved favourably: pace-matching the widened
   scope costs roughly 8–38 minutes (0.1–0.25s/call across the estimated
   5,000–9,000/day arrival range) against a 3-hour per-step timeout, so
   the daily pass *can* hold the line against arrivals once widened.
   (`2026-08-21-step2-stop.md`, `2801a13`)

   (The second attempt at step 1 and step 3 is where the shipping
   happened; see below.)

5. **Three code changes shipped, each after its stop:**

   **STEP 1 (first-repo `50e8d25`).** Gate separated from fetch:
   `_fetch_by_clob` now returns the parsed response whenever the HTTP
   call itself succeeds; each caller applies its own usability test. The
   proxy branch keeps its existing `end_date_iso` requirement, applied at
   its own call site, verified byte-for-byte identical in the diff. The
   assertion branch checks `closed == true` plus a winning token, then
   calls `mark_market_resolved(evidence_source="clob",
   resolution_event_time=None, evidence_detail="token.winner")`. The
   decisive gate: the freshly re-derived 317-market census returned
   203 resolved / 98 open / 16 no-response — an exact match to the 08-20
   sizing run, all 203 dry-run calls accepted with `reason='written'`. At
   production `--geo-only` scope, 215 of the 360 markets previously
   absorbed undifferentiated into `not_found=360` are now correctly split
   out — the daily run had been discarding 215 resolved markets every
   day. Honest limitation disclosed: zero markets in that specific
   population exercise the proxy branch's own `UPDATE` write logic when
   triggered, so behaviour was preserved at the selection level and
   remains untested at the write level by this diff alone.
   (`2026-08-21-step1-implementation-v2.md`, `fb5831f`)

   **THE SWEEP PREDICATE FIX (first-repo `492e028`).**
   `resolution_sweep.py` now keys on
   `COALESCE(resolution_recorded_at, last_checked)` — preferring the
   column that is write-time by construction and structurally enforced
   over the one that is write-time by convention. Every pre-flight
   prediction held: three candidate sets measured at 140 / 215 / 216,
   with set 3 differing from set 2 by exactly one row — the predicted
   self-healing case, the `hydration_fill` market rescued from an
   8-month-stale `last_checked`. The 85 semantically-wrong rows survive
   via the fallback, recorded as an accepted, named limitation of the
   transitional form. Self-healing quantified: 13 of 216 unscoped
   candidates (6.0%) use the reliable column today. At the script's own
   real, category-joined scoped query: 8 → 57 markets, 49 added, zero
   removed, all 49 admitted via the fallback — Channel 2 discovery had
   been seeing roughly one-seventh of what it should.
   (`2026-08-21-resolution-sweep-predicate-fix.md`, `978bb5c`)

   **STEP 3 (first-repo `6e0d9d3`).** `closedTime` extracted as a true
   event-time. Field name established empirically: 50 of 50 sampled
   Gamma responses carry `closedTime`; 0 of 50 carry
   `end_date_iso`/`resolutionTime` — the same root error the open-smells
   register had already found in `hydrate_stub_markets.py`'s own date
   extraction. The catch this round: `test_mode=True` skips
   `mark_market_resolved()` entirely, so a naive dry-run diff would have
   been inert regardless of whether the change worked — the same trap
   step 1's first attempt fell into. A proper harness was built instead:
   freeze the candidate population (2,100 markets), call
   `mark_market_resolved(dry_run=True)` twice per genuine candidate with
   old and new arguments, assert every other field identical. Result:
   4 genuine candidates, all with usable `closedTime`, all showing a
   differing `resolution_date` by hours to about a week — reported as
   modest rather than inflated to match the arc's months-scale narrative,
   because this daily pass fetches the top of Gamma's `endDate`-sorted
   feed and skews toward recently-closed markets; the months-scale
   divergence lives in the historical backlog the sweep will reach.
   Sanity-checked against `tape_end` on 1,532 rows: 99.93% pass, one
   34-second failure — nowhere near the mismatch that disqualified
   `accepting_order_timestamp` as a candidate field during the earlier
   CLOB investigation.
   (`2026-08-21-step3-implementation.md`, `4b1a7de`)

   **STEP 2 (first-repo `5fcbffe`).** `--geo-only` dropped, `--limit`
   raised 500 → 35,000, in the `daily_maintenance.py` invocation only —
   the script's own default left at 1,000 so ad-hoc runs stay small. The
   arrival-rate measurement was a real methodological investigation:
   `tape_start` rejected outright, since it measures real-world trading
   dates, not insertion dates (`background_backfill_worker.py` imports a
   trader's whole historical tape at once); `last_checked` showed
   implausible day-to-day swings (11 to 60,156) and was rescued by a
   rowid-density test — genuine same-day inserts cluster tightly in rowid
   space, bulk re-touches scatter across a wide range at low density.
   Density ranged 0.0% to 99.5% across days checked. Restricting to
   >95%-density days in the current steady-state regime gave a
   confirmed-genuine maximum of 16,845 (2026-08-10). Limit set at 35,000,
   ~2.08× headroom, projecting roughly 2h26m at the conservative
   0.25s/call basis inside the 3-hour per-step timeout. Tail risk
   confirmed by construction, not assumed: SQLite assigns rowid
   sequentially at insertion, so newest arrivals sit at the tail of an
   unordered scan by mechanism, not correlation — a limit below the
   arrival rate would starve exactly the newest markets, the coverage
   failure this sizing exercise was guarding against. Verified with a
   real 5,000-candidate live dry-run: zero errors, 95.8% updated (far
   above the first stop's 40.0% 300-row sample, exactly as the dilution
   reasoning predicted), 3,229 resolved_accepted (67.4% of updated,
   consistent with the 317-market census's own rate), and — for the
   first time anywhere in this arc — a live example of the
   untagged-legacy-improvement comparator branch firing, not just the
   trivial first-write case. Widened population confirmed at 524,410
   against the pre-reg's ~515,491 estimate.
   (`2026-08-21-step2-implementation.md`, `7332003`)

## STATE FOR NEXT SESSION

The order below is proposed, not decided.

**THE SWEEP (tomorrow's focus — steps 1-3 are through, this is the gate):**

a. Pre-sweep gates per the pre-reg §C: WAL-safe integrity-verified
   backup; **tranche 1** against the known 317-market census (must
   reproduce the freshly re-derived expected count, not the stale 08-20
   figure of 203); then **tranche 2**, a seeded 5,000-market sample
   including a deliberate kill-and-resume test to validate the
   resumability claim before trusting it for a 36-hour unattended run.
b. The full sweep at 0.25s pacing, detached, 500-row batches with atomic
   checkpointing, against seven fixed abort thresholds.
c. Note the sweep will be the first time the comparator's harder
   branches run at production volume — cross-rank overwrite and
   same-rank disagreement remain unexercised outside dry-run.
d. The O-16 requeue-miss reasoning in the pre-reg's §D is marked `[I]`
   and should be confirmed against live code before or during tranche 2,
   not assumed — reasoning suggests the sweep's `resolution_date` will
   mostly fall to write-time via the 3-tier fallback, the *opposite*
   failure direction from the O-16 case, but this has not been re-traced
   against the live code this session.

**THEN THE SECOND MEASUREMENT (step 5),** per §E, with cohort/placebo
membership persisted per §F. Not before
`evaluate_new_trader_results.py` has run post-sweep so `trade_result`
flips from `pending`.

**NAMED FOLLOW-UPS FROM TODAY, none scheduled:**

e. The permanently-dead ~98-row CLOB-purged prefix at the head of the
   widened scan — accepted, not skipped. A skip/exclusion marker would
   remove a fixed daily cost and, more importantly, stop
   permanently-unreachable rows being indistinguishable from transient
   failures in the sweep's own abort thresholds.
f. `system_observer.py`'s three health metrics still carry the
   `resolution_date`-as-write-time assumption; step 3 will make them
   under-report once genuine event-times start landing. Live but
   cosmetic, named so it isn't rediscovered as a regression.
g. `hydrate_stub_markets.py`'s two defects (register item 2, from
   2026-08-20) — separate track, disjoint population (external_seed
   traders' markets only, zero overlap with the 203), cheap, fully
   diagnosed. Today's step 3 finding (Gamma uses `closedTime`, not the
   fields `hydrate_stub_markets.py` checks) is the same root error.
h. `get_stub_markets()` has no `ORDER BY`/offset/exclusion and may
   re-try the same unmatchable 200 rows every run.
i. Shape D — upstream ingestion-time date fetch, ~21 min/day at the
   observed new-market rate, would stop new dateless rows being created.
   Named, not scheduled.
j. The transitional `COALESCE` in `resolution_sweep.py` is retirable
   once every live resolution writer has migrated to
   `mark_market_resolved()`. Named as a condition, not a date.

**THE CANONICAL ARC, paused mid-sequence:**

k. Stage 3 (`#4`/`#5`/`#6`, the three CLOB sibling passes in
   `fast_resolution_check.py`) — the first cross-rank exercise.
l. Stages 4-6; the legacy provenance backfill and its
   `backfill_verified` schema change; the CI lint rule from design §F.

**CARRIED, UNCHANGED:**

m. `check_pending_geo` still has no daily evaluator wired into
   `daily_maintenance.py`.
n. `apply_synthetic_closes` as a third win/loss implementation.
o. Ingestion-stall detection and the 500-trade recovery threshold —
   with today's reconfirmation that any detector must key on insertion
   order, not `trades.timestamp`.
p. From 2026-08-15: the cutover decision, category-split cost floor,
   consensus question, `comprehensive_elo` sign error, elections
   calibration re-run (O-40), O-38, O-18. Track 2 CI power diagnostic
   still uncommitted.

## BIG PICTURE

The thesis result (+0.0316, CI [-0.0088, +0.0710], NULL, underpowered)
stands untouched and will continue to stand permanently as the result of
record — that is now a recorded decision, not an accident. The corrected
measurement that follows the sweep is a second, separately-named figure,
and its expected direction is written down before it exists: the
cohort-placebo gap should narrow. Three code changes today made the
discovery path capable of finding what it has been silently discarding —
215 markets a day at production `--geo-only` scope, and a daily pass now
sized to keep pace with arrivals rather than falling permanently behind.
Nothing has been swept yet. The consequential write is tomorrow's first
act.

**Plain statement, accurate about what actually shipped, not to be
inflated in a future read of this file:** three code changes went into
production this session — the `backfill_market_dates.py` assertion branch
(step 1), the `resolution_sweep.py` freshness-predicate fix, and the
`fast_resolution_check.py` `closedTime` extraction (step 3) — each
preceded by a stop that found a real problem, one of them (step 1) twice.
No market was resolved by any of them at production write time — every
verification this session ran `dry_run=True` throughout, confirmed
against the actual write target, not inferred from the dry-run flag
alone. Five stops, not four and not six. No sweep run. The result of
record untouched, confirmed still present in the live DB as of this
session.

Write it as a record for a future instance with no memory of today.
