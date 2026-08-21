# 2026-08-21 — closing the resolution-discovery gap: shape assessment

**ASSESSMENT ONLY. No writer modified, no market resolved, no production
write made anywhere in this session.** Every claim tagged **[V]** (verified
this session — command/file:line given) or **[I]** (inferred, marked
explicitly). Every premise in the task prompt was checked, not assumed —
one was corrected (the hydrate-non-progress note, upgraded from "noted in
passing" to verified) and one major fact not in the prompt was surfaced (a
sixth, un-catalogued writer that already does most of what "shape C" would
have built from scratch).

---

## Summary finding, stated up front

**A CLOB-by-market_id-as-condition_id resolution check already exists in
production, already scheduled, already fetching the exact API response
that carries the winner flag — it just never reads that field.**
`scripts/backfill_market_dates.py`, run daily by `daily_maintenance.py`
(`--geo-only --limit 500`), calls `GET
https://clob.polymarket.com/markets/{condition_id}` per candidate market
(`_fetch_by_clob`, line 62) — the identical call the 08-20 sizing run used
to find the 203 — but only harvests `end_date_iso` for a scheduled-date
proxy write. It never inspects `closed` or `tokens[].winner`, and never
touches `resolved`/`winning_outcome`. **All 203 of the sizing run's
confirmed-resolved markets satisfy this script's own candidate predicate
today** [V] (verified below) — this is not a new pass waiting to be
written, it is one unread field in an existing response object away from
closing the gap for the population it already reaches. This reframes the
whole assessment: the honest answer is **repair**, not new, and not really
"consolidate 5 into fewer" either — it's "stop discarding data one
existing writer already paid the API-call cost for."

---

## Coverage cross-checks run this session

| Check | Result | Tag |
|---|---|---|
| Do any of the 203 overlap `hydrate_stub_markets.py`'s candidate population (external_seed traders' markets)? | **0 of 203** — the 203 split `historical_backfill` 114, `live_monitoring` 87, `background_backfill` 2; zero `external_seed` | [V] `data/characterizations/discovery_gap_sizing_20260820T211955Z.json` cross-referenced against `hydrate_stub_markets.py`'s `get_stub_markets()` query |
| Do all 203 satisfy `backfill_market_dates.py`'s own candidate WHERE (`end_date IS NULL OR resolution_date IS NULL`)? | **203/203** — all have *both* fields NULL | [V] live query, this session |
| Do all 203 have a CLOB-queryable identifier (`condition_id` set, or `market_id` itself hex-shaped)? | **203/203** | [V] live query, this session |
| Does `hydrate_stub_markets.py` re-try the same unmatchable rows every day (prompt's "VERIFY this")? | **Yes, confirmed** — `get_stub_markets()` has no `ORDER BY`; identical `LIMIT 200` result set across separate connections/processes on an unchanged table, and its population (1,250) doesn't shrink because ~99% structurally cannot succeed (item 2, `2026-08-20-open-smells-register.md`) | [V] mechanism (query determinism, tested live) + [I] cross-day stability (population is static because nothing removes rows from it, not independently traced across a literal day boundary) |

---

## The five (now six) writers touching this problem, restated

Per `2026-08-19-market-resolution-write-cluster.md`, the resolution
cluster has 13 writers; four of them (#4/#5/#6 in `fast_resolution_check.py`,
plus #3's Gamma bulk pass) and #11 (`hydrate_stub_markets.py`) are the
*discovery*-relevant ones the prompt names. **A sixth exists and was not
in the 08-19 census: `backfill_market_dates.py`**, correctly excluded from
that census's *establishing-writer* table because it only writes
`end_date`/`resolution_date` as a proxy (same excluded category as
`monitor.py`'s proxy writes, per design §A) — but it shares #4/5/6's exact
discovery mechanism (CLOB lookup by market_id-as-condition_id) and was
missed as a *candidate for extension* precisely because that census was
scoped to writers that already assert resolution.

---

## Shape-by-shape assessment

| Shape | Coverage (candidate predicate) | Cost at scale | Bleeding vs. backlog | Canonical fit | What it breaks |
|---|---|---|---|---|---|
| **A. Fix `hydrate_stub_markets.py`** (identifier fallback + `closedTime` field name + candidate-selection progress) | `resolution_date IS NULL AND market_id IN (external_seed traders' markets)` — **1,250 markets** [V]. **Reaches 0 of the 203** [V] — disjoint population, external_seed-only. | Trivial — already 200/day scheduled; fixing the two defects lets that same budget actually convert instead of no-op. One-time: <1 hour for the whole 1,250-market backlog at current pacing. Steady-state: near-zero, external_seed trader count grows slowly. | **Neither**, with respect to the 513k gap. Clears its own small backlog once fixed; doesn't touch the discovery-gap population at all. | Already compliant — Stage 1 shipped, calls `mark_market_resolved(evidence_source="hydration_fill")` for the assertion branch. | Nothing at scale — narrow, already-isolated, already the register's #2 recommendation (cheap, fully diagnosed). Worth doing regardless, on its own track, not a substitute for the other shapes. |
| **B. Fix `fast_resolution_check`'s Gamma pass to use `/markets/keyset`** | Whatever appears anywhere in Gamma's global closed-markets catalog, walked past the current 2,000-row offset ceiling — **not bounded by our own population**, bounded by Gamma's entire platform-wide resolved-market history, ordered by a `endDate` sort key independently confirmed tie-heavy and uncorrelated with true resolution recency (`2026-08-20-open-smells-register.md` item 1(a)/(b), reconfirmed here, not re-litigated). | **Cannot state a sane per-market cost** — keyset removes the *ceiling* but not the *ordering* problem; a market with an uncommon `endDate` could sit arbitrarily deep in a catalog with no known total size, reachable "but possibly very deep" per the register's own honest framing. This is qualitatively worse than a bounded, targeted sweep: paging cost scales with Gamma's global catalog, not with the 513k rows we actually care about. | **Neither, reliably.** Could stop some future bleeding for markets lucky enough to page in reasonably, but offers no completion guarantee and no cost bound — the register already classified the underlying ceiling problem REAL-UNBOUNDED for exactly this reason. | Already compliant — Stage 2 shipped, this pass already calls `mark_market_resolved(evidence_source="gamma")`. Free upgrade sitting unused: the same Gamma response this pass already fetches carries `closedTime` (a true A2 Rank-1 event-time), never extracted — `resolution_event_time=None` is hardcoded today (`fast_resolution_check.py:279`, own comment confirms). Worth a one-line fix regardless of the keyset question. | Runtime — an uncapped keyset walk deep enough to matter risks blowing past `DEFAULT_STEP_TIMEOUT` (3h, `daily_maintenance.py:24`) the same way the one-time CLOB sweep would, for a worse coverage guarantee. |
| **C. NEW dedicated pass — CLOB by market_id-as-condition_id** | Full **513,567–524,410**-market dateless-unresolved population (the exact predicate depends on whether scoped like `backfill_market_dates.py`'s OR-clause or the stricter AND-clause; both orders of magnitude agree) [V], including all 203. This is the shape proven to work by the sizing run. | **One-time catch-up: ~35.6 hours** at the codebase's 0.25s/call convention (513,000 × 0.25s) — cannot run inside `daily_maintenance.py` (3h41m today's total; 3h per-step timeout). Must run as a standalone one-off, same precedent as `backfill_o16_tier1/tier2.py`. **Steady-state: trivial** — at ~5,108 new markets/day (today's `markets` table growth), a daily quota of a few thousand keeps pace in well under an hour/day. | **Clears the backlog. Does not stop the bleeding by itself** — it's a sweep, not a hook into ingestion; new dateless markets keep arriving at the ingestion rate and need their own recurring pass (which this shape *is*, run daily at a modest quota — so in its steady-state form it does both, just not from a single one-time run). | Must be built canonical from day one per instruction — `evidence_source="clob"` (A1 Rank 1, correct — CLOB's `token.winner` is a direct declaration, the highest tier). `resolution_event_time=None` always: A2 already closes this as a verified negative — CLOB carries no event-time field on any sampled market (`2026-08-19-canonical-design-open-questions.md` Q1, re-cited not re-tested here). Falls to the 3-tier fallback (existing proxy → write-time). | Nothing structural if built to call `mark_market_resolved()` from the start — `trg_resolved_no_unresolve` imposes no friction (only ever proposes 0→1) and `check_resolution_write_atomicity` stays clean by construction. The cost is coherence: **this is literally a duplicate of `backfill_market_dates.py`'s existing CLOB strategy**, minus the part where that script already exists, is already scheduled, and would need only its extraction logic extended — see below. |
| **C-repair. Extend `backfill_market_dates.py` instead of building C new** | Same population as C in principle. **Today's actual candidate reach is much narrower — 360, `--geo-only`-scoped** [V] (matches today's live log: `[BACKFILL] Progress: 100/376 ... Done — updated=16, not_found=360`). Confirmed **203/203 of the sizing run's markets satisfy this script's own WHERE clause** [V] — the ceiling on reach today is the `--geo-only` flag and the classification lag (see growth-rate finding below), not the query shape or the identifier strategy, both of which already work. | **Same cost math as C** for a full unscoped one-time sweep (this script's own pacing is actually `time.sleep(0.1)` between calls — file:line `backfill_market_dates.py:238` — faster than the 0.25s convention, so the real one-time cost is closer to ~14 hours at its current pacing, though a first production run should probably keep the more conservative 0.25s the rest of the CLOB cluster uses). Steady-state identical to C: raise `--limit` and drop `--geo-only` for a modest daily quota. | Same as C's steady-state form — **both**, once widened and run at a sustained daily quota; the one-time sweep clears backlog, the daily cadence (already scheduled infrastructure) stops the bleeding going forward with zero new cron/systemd wiring. | Requires adding a `mark_market_resolved()` call using data **already present in the `_fetch_by_clob` response** — `closed` and `tokens[].winner` are on the exact payload this function already parses for `end_date_iso`, just unread today (`backfill_market_dates.py:62-78`). Zero additional API calls for markets this script already visits. `evidence_source="clob"`, same A1/A2 characterization as C. | **Two purposes in one script** — this file's own commit history (`4cdd190`, `446bcde`) and docstring frame it as an STR-003 signal-visibility proxy-date backfill, not a resolution-discovery tool; adding an assertion branch changes what the script *is*, not just what it does. Mitigated by the same pattern Stage 1 already established for `hydrate_stub_markets.py` — two clearly separated branches (proxy-fill branch untouched, new assertion branch added) rather than blurring the two. Needs its own before/after dry-run diff per the migration discipline in §G, same bar as Stages 1–2. |
| **D. Named other shape — fix ingestion to populate dates at market-creation time (upstream)** | Every market entering the DB from now on via `store_market_from_trade` (writer #1a, `monitor.py:911`) or `background_backfill_worker.py`'s stub INSERT (`background_backfill_worker.py:328`) — **the two live ingestion paths that create the dateless rows in the first place** (see finding below). Reaches 0 of the existing 513k+ backlog — it only prevents new dateless rows. | **Bounded by new-market discovery rate, not trade volume** — the existing `market_exists()` guard already fires the relevant code path only for genuinely *new* market_ids, which is a small fraction of total trade throughput. At today's ~5,108 new-markets/day, one market-detail API call per new market (already the pattern used elsewhere, run via `asyncio.to_thread` off the event loop, same technique `monitor.py:911` already uses for `store_market_from_trade`) costs roughly 5,108 × 0.25s ≈ 21 minutes/day, spread continuously through the day, not a batch job. | **Stops the bleeding, does not touch the backlog.** The 513k+ existing rows still need one of C/C-repair. This is the complement, not a substitute. | Would establish `resolved`/`winning_outcome` at creation time only for markets that happen to already be closed the instant they're first discovered (rare — most newly-discovered markets are open) — for the common case it would populate `end_date`/`resolution_date` as a **proxy**, the same out-of-scope-by-design category as `monitor.py`'s existing proxy writes (design §A). Not itself a `mark_market_resolved()` caller in the common case; it prevents markets from being born dateless, which is a different, upstream fix from asserting resolution. | Adds one synchronous-but-threaded API call to the new-market-discovery path in two live, continuously-running processes (`polymarket-monitoring`'s trade loop and the background backfill worker) — needs its own latency/error-handling review (a slow or failing Gamma/CLOB call must not stall trade ingestion) before being built; not designed here, per the non-goals. |

---

## The upstream-cause finding (item 6)

**[V] Confirmed, not assumed: the dateless population is dateless because
the two live ingestion paths that create these rows never make the API
call that would carry a date, not because a date was available and
discarded.**

- `background_backfill_worker.py:305-330` (`data_source='background_backfill'`,
  **201,599** of the 514,043 dateless-unresolved rows [V], read in full
  this session): its `INSERT OR IGNORE INTO markets` statement supplies
  only `market_id, title, 'Unknown', 0, 'background_backfill'` — no
  `end_date` column in the INSERT at all. The trade payload it parses
  (`transactionHash`, `asset`, `timestamp`, `conditionId`, `title`,
  `outcome`, `size`, `price`, `side`, `proxyWallet`) never includes a date
  field — it isn't dropped, it was never fetched, because the trader
  history endpoint (`/trades?user=...`) is a per-trade record, not a
  per-market one.
- `monitoring/database.py:762-811` `store_market_from_trade`
  (`data_source='live_monitoring'`, **310,992** of the dateless population
  [V]) does make a "best-effort" attempt to read `trade.get('endDate')`/
  `trade.get('end_date')` from the trade object — but the trade objects
  reaching it come from the same Data API `/trades` shape, which the code
  itself never populates from any date-carrying field, and the dateless
  count for this source is the largest of the four `data_source` values —
  consistent with that best-effort read essentially never succeeding
  [I] — not independently re-verified against a live raw trade payload
  this session, but the ingestion code's own field list and the resulting
  DB state agree.
- **Both paths could fetch the date at creation time — they just don't
  today, by design, for throughput**: making a market-detail API call
  (Gamma or CLOB) per newly-discovered market_id would add per-market
  network latency to a per-trade hot loop. This is real cost, not free —
  but it's bounded by *new-market* discovery rate (~5,108/day, per today's
  fingerprint), not by total trade volume (tens of thousands/day), which
  is what makes shape D above tractable rather than a throughput risk.
- **97.0% of the dateless population's `market_id` values are themselves
  condition_id-shaped** (0x-prefixed, 66 chars) [V], re-confirming the
  sizing prereg's independent figure — this is why a CLOB lookup keyed
  directly on `market_id` works for nearly the whole population without
  needing `condition_id` to be separately populated.

**Verdict on "is upstream the most elegant answer": partially, and only
for the future, not the past.** It's real and cheap enough to be worth
doing, but it cannot be the *whole* answer — it does nothing for the 513k
rows that already exist, and per design §A a market discovered while still
open only gets a proxy-date fill from this path anyway, not a resolution
assertion. It is the right complement to a backlog sweep, not a
replacement for one.

---

## The growth-rate finding (item 7)

**[V] The canonical-relevance stratum's flatness (317 → 317, confirmed
this session) is not evidence the underlying phenomenon has stopped
growing — it's an artifact of a separate, much larger classification lag
sitting upstream of it.**

- The base dateless-unresolved population grew **+3,189 to +5,108
  overnight** (two consecutive measurements this session). **513,574 of
  514,043 dateless-unresolved rows — 99.9% — carry `category='Unknown'`**
  [V]. Only 383 total carry `category IN ('Elections','Geopolitics')`
  ((248+135) [V]), of which 347 have trades and 317 additionally pass the
  `trade_gap_flag` filter — i.e. **the entire Q2 census population (317)
  is a 0.06% sliver of the dateless population**, and essentially all
  overnight growth necessarily lands in the 'Unknown' bucket first, not
  directly into Geo/Elections.
- **`category='Unknown'` markets total 728,212** DB-wide [V] (all
  resolution states) — an order of magnitude larger than the specific
  dateless-unresolved slice. `backfill_market_categories.py` (already a
  scheduled daily step) classified **11,708** of a **19,304**-row batch
  today, skipping 7,576 as still unclassifiable from title alone [V,
  today's figures only — not independently confirmed as a sustained daily
  rate].
- **Reading of the mechanism, stated as inference, not measurement:** a
  newly-ingested market is born `category='Unknown'` via both live paths
  above; it only becomes visible to the Q2 canonical-relevance census
  *after* `backfill_market_categories.py` successfully classifies it into
  'Elections'/'Geopolitics' — a separate, rate-limited, title-based
  classification step running against a 728K backlog. **[I]** The 317
  figure staying flat across one day is far more consistent with "new
  Geo/Elections markets are entering the Unknown bucket and haven't been
  classified into visibility yet" than with "no new Geo/Elections markets
  are resolving undiscovered" — the latter would require the underlying
  resolution-discovery gap (already shown REAL-BOUNDED and non-trivial at
  67.4% of a full census) to have specifically stopped affecting this one
  category pair overnight, which has no supporting mechanism. **Not
  independently proven this session** — would require re-running the Q2
  census after a few more days of category-backfill progress and checking
  whether newly-classified Geo/Elections markets, not present in
  yesterday's 317, show the same ~64-67% already-resolved rate. Flagged as
  the natural next check, not performed here (assessment scope).
- Consequence for the recommendation: **any fix scoped to `category IN
  ('Geopolitics','Elections')` (e.g. `backfill_market_dates.py`'s current
  `--geo-only` flag) inherits the same visibility lag** and will
  systematically undercount its own target population until the
  classification backlog is separately addressed or the discovery fix is
  run unscoped against the full dateless population instead of a
  category-filtered slice of it.

---

## The elegance judgement (explicit, as instructed)

**Repair, not new — and the repair is smaller than any shape in the
original list because a sixth writer already does the hard part.**

`backfill_market_dates.py` already: (a) queries by market_id-as-condition_id
against CLOB, the exact method the sizing run proved works and the exact
method shape C proposed building; (b) is already wired into
`daily_maintenance.py` with a working `--limit`/`--geo-only` interface;
(c) already fetches the response object that contains `closed` and
`tokens[].winner`, and discards them. Building shape C as a **new** file
would duplicate this machinery byte-for-byte in spirit — same endpoint,
same identifier strategy, same per-call pacing discipline — for the sake
of a clean assertion-only script, at the cost of a sixth-then-seventh
near-identical CLOB caller in a cluster the project has already twice
flagged (this arc's own write-cluster census, and the
trade-evaluator/geo-backfill precedent — `2026-08-19-trade-evaluator-repoint.md`,
"3 scripts differ only in population/category filter... recommend
consolidating") for exactly this kind of proliferation. This is that
pattern again, caught before being built rather than after: shapes A, B,
C, and `backfill_market_dates.py` all differ from each other primarily in
*candidate predicate and which field of an already-fetched response gets
read* — the same shape as the precedent, not a coincidence.

**Recommended sequence, combining repair (backlog) with upstream repair
(bleeding), per the instruction that a combination answer should be
stated and sequenced:**

1. **Extend `backfill_market_dates.py`'s `_fetch_by_clob` to also extract
   `closed`/`tokens[].winner` and call `mark_market_resolved(evidence_source="clob")`**
   on a new branch, alongside its existing untouched proxy-date branch —
   same two-branches-one-script pattern Stage 1 already established for
   `hydrate_stub_markets.py`. Needs its own before/after dry-run diff,
   same bar as Stages 1–2 (§G). Zero new API calls for markets this
   script already visits.
2. **Widen its candidate scope** — drop or generalize `--geo-only` (given
   the growth-rate finding above shows category scoping systematically
   undercounts) and raise `--limit` for the daily-cadence run once (1) is
   verified; this is the "stop the bleeding" half, using infrastructure
   that already exists and is already scheduled — no new cron/systemd
   entry needed.
3. **Run a one-time, standalone catch-up sweep** (same precedent as
   `backfill_o16_tier1/tier2.py`) against the ~513k-524k backlog, *outside*
   `daily_maintenance.py` — it cannot fit the 3h per-step timeout or the
   existing 3h41m total daily budget. ~14-36 hours depending on pacing
   chosen; run once, observed, not scheduled.
4. **Fix `hydrate_stub_markets.py`'s two defects** (shape A) on its own
   track — cheap, fully diagnosed already (register item 2), reaches a
   disjoint population, doesn't block or get blocked by 1-3.
5. **Reject shape B as specified** (Gamma keyset) — no cost bound, no
   completion guarantee, solves a problem the CLOB-based approach doesn't
   have. Its one salvageable piece — extracting `closedTime` as a true
   event-time in the *existing* Gamma bulk pass — is a free one-line
   addition worth doing opportunistically, independent of the keyset
   question.
6. **Consider shape D (upstream ingestion-time fetch) as a later,
   separate task** — real, bounded, cheap (~21 min/day at today's
   new-market rate), but it only prevents future backlog growth; it
   should not be built instead of 1-3, and per the non-goals here it is
   named, not designed.

Nothing above touches Stage 3 (migrating #4/#5/#6 to call
`mark_market_resolved()` in place) — step 1's new branch in
`backfill_market_dates.py` is a new canonical caller, built canonical from
the start per the task's instruction, entirely separate from whether
`fast_resolution_check.py`'s three CLOB passes are themselves migrated.

---

## What this does not do

No writer modified. No market resolved. No pre-registration written (per
the non-goals, that follows this decision). Stage 3 untouched. The
specific dry-run/verification methodology for step 1 above is not designed
here — that is implementation work for a future task.

---

*Generated 2026-08-21. Sources: `monitoring/resolution_writer.py`,
`scripts/fast_resolution_check.py` (full read, both this session and
inherited from 2026-08-19's cluster read), `scripts/hydrate_stub_markets.py`
(full read), `scripts/backfill_market_dates.py` (full read, this session —
not previously catalogued in the write-cluster census),
`monitoring/database.py` (`store_market_from_trade`, `store_market_dict`),
`monitoring/background_backfill_worker.py` (`_process_trader_sync`, full
read), `monitoring/monitor.py:911`, `scripts/daily_maintenance.py`
(step wiring, `DEFAULT_STEP_TIMEOUT`), live DB queries this session
(dateless-population cross-tabs by `data_source`/category/identifier
shape, candidate-predicate overlap against the 203-market list), live
Gamma API probes this session (`/markets?closed=true`, `/markets/keyset`
shape, no exposed total-count field found), and
`2026-08-19-market-resolution-write-cluster.md`,
`2026-08-19-canonical-resolution-write-design.md`,
`2026-08-20-discovery-gap-sizing-result.md`,
`2026-08-20-open-smells-register.md`,
`2026-08-19-trade-evaluator-repoint.md`,
`2026-08-19-write-path-census.md` (all first-repo/trading-swarm, read not
re-litigated except where explicitly re-verified above). Read-only: no
schema touched, no data repaired.*
