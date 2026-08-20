# 2026-08-20 — open "bad smells" register

**Read-only investigation. No code modified, no writer migrated, no schema
touched, nothing repaired.** Every claim tagged **[V]** (verified this
session, command/query given) or **[I]** (inferred). Item 1 investigated in
depth per the task's instruction; items 2–8 investigated to the depth
needed to classify, not resolve — three were delegated to parallel
sub-agents (forks) working from this same standing instruction, and their
findings are reproduced here with the same evidentiary discipline, not
summarized away.

Every prompt premise was checked, not assumed — several turned out to need
correction (see items 2, 4, 6 below): the design doc's own guess that
`hydrate_stub_markets.py`'s misses were "delisted" was wrong; the write-path
census's "10 hardcoded markets" for `fix_expired_unresolved.py` undercounts
by 2; the census's "no invariant coverage at all" for P&L aggregates is
partially wrong (`total_invested` has soft Tier-3 coverage).

---

## Register

| # | Item | Classification | Current state (one line) | Evidence | What would settle it |
|---|---|---|---|---|---|
| 1 | Gamma 2,100 pagination ceiling | **REAL-UNBOUNDED** | Confirmed permanent blind spot; extent unknown | [V] live API probes, this session | Walk `/markets/keyset` to full depth and cross-reference vs. 513,179 unresolved DB rows, or CLOB-sample the 511,829 dateless subset |
| 2 | `hydrate_stub_markets.py` 8-in-1,258 hit rate | **REAL-BOUNDED** | Two concrete, fixable code defects account for ~99% of misses | [V] live-sampled against Gamma, this session | Already settled — see below; a fix is a small, scoped code change (not done here, read-only) |
| 3 | Step-7-vs-step-21 ordering (`daily_maintenance.py`) | **BENIGN** | Mechanically possible, never occurred (0/66 runs), and reports REGRESSION+alert, not silent PASS, in 33/40 observed instances | [V] full log grep, this session | Settled |
| 4 | `fix_expired_unresolved.py` SQL interpolation | **BENIGN** | Dormant, already-run, hardcoded values only, effects verified persisted correctly | [V] git log, live DB check, this session | Settled |
| 5 | Position construction — 4 INSERT implementations | **REAL-BOUNDED** | `is_synthetic_close` silently goes stale on `background_pnl_worker.py`'s UPDATE-conflict branch; `INSERT OR REPLACE` incident already fixed in live code | [V] read all 4 writers + schema, this session | Add `is_synthetic_close` to the `ON CONFLICT DO UPDATE SET` clause (not done here) |
| 6 | P&L aggregate recomputation — 5 implementations | **REAL-BOUNDED** (+1 NEEDS-INVESTIGATION sub-item) | 2 of 5 writers live, agree with each other; 3 dormant; `trader_statistics.py`'s formula unverified | [V] read all 5 writers, `audit_invariants.py`, this session | Read `trader_statistics.py:222-266`'s `calculate_comprehensive_stats()` |
| 7 | `elo_last_updated` T-separated backfill | **REAL-BOUNDED** | 22,558 rows today (unchanged from 08-19); incidental-rewrite mechanism ≈1,113 years to zero — practically permanent | [V] live count, this session | A dedicated one-time rewrite script + a wired verification check (neither exists) |
| 8 | Writer D unretired code (`elo_bridge.py`) | **REAL-BOUNDED** | Code present, zero live call paths (no cron/systemd/script/runbook invokes it) | [V] full sweep of cron/systemd/scripts/docs, this session | Delete the 4 named artifacts, or leave as documented dead code — either closes it |

---

## Item 1 — the Gamma 2,100 ceiling (investigated in depth, per instruction)

### (a) How does Gamma order `/markets`? — determined empirically, not from docs

`fetch_all_resolved_markets` requests `order=endDate&ascending=false`.
Confirmed today, live, that the API does sort by `endDate` descending — but
**`endDate` is a scheduled/nominal end date, not the market's actual
resolution/closure timestamp** [V]:

- At `offset=500`, three consecutive rows share the identical
  `endDate=2027-01-01T05:00:00Z` but their `closedTime`/`umaEndDate`
  (the genuine resolution timestamp — the same fields the design doc's own
  A2 ranking already established as the only true event-time source) span
  `2025-12-11` to `2026-02-05` — nearly two months apart despite an
  identical sort key.
- In the first 100 rows alone, `endDate=2028-01-01T05:00:00Z` recurs **79
  times**; two other values recur 12 and 9 times. These read as shared
  template/placeholder dates (e.g. "end of next year"), not per-market
  unique timestamps.
- Given ties this large, secondary/tiebreak ordering is opaque — sampled
  `id` values within a tie block were not monotonic.

This directly undercuts treating the fetch as a "recency window": a
market's rank in this list is only weakly related to when it actually
resolved.

### (b) Can a resolved market permanently sit outside the window? — Yes, via two compounding mechanisms

1. **A hard, API-enforced pagination ceiling**, not the script's own
   50,000-market safety comment. Binary-searched the exact boundary today
   [V]: `offset=2000` succeeds at any `limit`; `offset=2001` fails
   immediately with HTTP 422, body `"offset too large, use /markets/keyset
   for deeper pagination"` — the API's own error names the escape hatch.
   The 50,000-row comment in the script is never reached in practice
   (confirmed already in the Stage 2 stop, and reconfirmed here); the real,
   binding limit is Gamma's fixed offset ceiling at 2,000.
2. **The sort key's massive tie structure makes the reachable window's
   coverage arbitrary, not a clean recency cutoff.** Because so many
   markets share common placeholder `endDate` values, and true resolution
   time doesn't correlate with position in the list, a market resolving
   *today* but carrying a less-common/older nominal `endDate` could rank
   behind thousands of markets sharing a more common future placeholder
   date — never entering the reachable ~2,100-row window at all, not now,
   not ever. This is not a market "aging out" of a moving recency window
   (which would at least be predictable and eventually self-correct); it's
   a structurally poor sort key producing a slice whose membership isn't
   governed by actual resolution recency.

Both are verified, not hypothetical. Combined, they establish a genuine,
permanent blind spot in Gamma-based resolution discovery.

### (c) Quantify, and do the other 3 passes cover the gap?

DB query today [V]:

| Population | Count |
|---|---|
| Total unresolved markets | 513,179 |
| ...with `resolution_date IS NULL` | 511,829 (99.7%) |
| ...with `resolution_date` set and >7 days old (`run_stale_clob_pass` candidates) | 132 |
| ...with no `resolution_date` but `end_date` >7 days old | 603 |
| ...with **both** `resolution_date` and `end_date` NULL | 510,380 (99.5%) |

**The other three passes in this file** (`run_stale_clob_pass`,
`run_recent_overdue_pass`, `run_external_seed_pass` — writers #4/#5/#6)
**do not share this specific blind spot** — they query CLOB directly
per-market via `condition_id`, keyed off our own DB's date fields, not
Gamma's recency-ordered list.

**But they share a different, larger blind spot that compounds with this
one.** `run_stale_clob_pass` requires `resolution_date IS NOT NULL`; only
132 of 513,179 unresolved markets qualify. `run_recent_overdue_pass`
accepts `end_date` as a fallback, but 510,380 markets (99.5%) have
**neither** field populated. **The combined candidate pool for all three
CLOB-based safety-net passes is capped at roughly 132–735 markets out of a
513,179-row unresolved population.** They cannot plausibly backstop the
Gamma pass's blind spot at scale, because the population that would need
backstopping overwhelmingly lacks the date field these passes require to
even become a candidate.

**Caveat, stated plainly, not glossed over:** it is not established that
most of the 511,829 dateless unresolved markets are *actually* resolved
right now and simply undiscovered — many are plausibly still-open, or
stub markets that a different path (`hydrate_stub_markets.py`,
`store_market_dict`) should be reaching. Item 2 below independently
confirms `hydrate_stub_markets.py` itself is only reaching a small,
identifier-limited slice of even its own narrower candidate scope. What
*is* established here is narrower and still real: the mechanism that would
need to backstop the Gamma window's blind spot is itself only reachable
for ~0.1–0.3% of the unresolved population.

### (d) Alternative Gamma pagination — described, not implemented

`/markets/keyset` — confirmed live and functional today [V]: returns HTTP
200 with a `next_cursor` opaque token (encodes a time+id composite key)
instead of `offset`/`limit`; a follow-up request with that cursor would
continue past row 2,000 indefinitely. This is Gamma's own documented
escape hatch (named in its 422 error text), not a workaround this project
would be inventing.

**Would not, by itself, fix (b)'s tie-ordering problem** — keyset
pagination still walks the same `endDate`-sorted sequence, just without
stopping at row 2,000. It would convert "permanently unreachable" into
"reachable but possibly very deep," which is a real improvement but not a
complete fix; a more direct fix for (b) would need a different sort key
tied to `closedTime`/`umaEndDate` (not tested — whether Gamma exposes an
`order` value for those fields is unknown, out of this session's budget)
or leaning further on the CLOB-based passes instead of the Gamma bulk
fetch.

### Classification: REAL-UNBOUNDED

Genuine, doubly-verified defect. Not classified as bounded because the
actual count of currently-resolved-but-undiscovered markets is unknown —
establishing it requires either a full-depth `/markets/keyset` walk
cross-referenced against the 513,179 unresolved DB rows, or CLOB-sampling
a random subset of the 511,829 dateless unresolved markets to estimate
what fraction are already resolved on-chain. Neither was done here
(investigate-to-classify, not resolve, per the task's scope discipline).

---

## Items 2–8

*(Each investigated by a parallel fork under the same standing instruction
— verified/inferred tagging, classify-don't-resolve budget. Findings
reproduced here, not condensed away.)*

### Item 2 — `hydrate_stub_markets.py`'s 8-in-1,258 live-hit rate — REAL-BOUNDED

Root cause identified by live-sampling against the actual Gamma API — and
it is **not** delisting, contrary to the design doc's own guess
("delisted or otherwise unavailable"). Two distinct, compounding code
defects account for essentially the entire not_found population:

1. **[V]** Of the 1,250 not_found candidates, **1,214 (97.1%) have both
   `api_id IS NULL` and `condition_id IS NULL`.** This skips
   `_fetch_market()`'s primary lookup and falls through to
   `GET /markets?id={market_id}`, sending a 66-char hex `market_id` where
   Gamma's `id` param expects an integer — confirmed live to return HTTP
   422 `"invalid integer"` on every sample tested, a type-mismatch this
   script's current two lookup strategies can never satisfy for these
   rows. One sampled market was independently confirmed to genuinely exist
   on Gamma (via `/public-search`) — real data, structurally unreachable
   through either lookup path as written.
2. **[V]** Of the 36 candidates that *do* have a valid `api_id`, live
   lookups succeed 6/6 sampled — full resolved market data returned
   (`closed=true`, `umaResolutionStatus="resolved"`, prices set). But the
   script's date extraction only checks
   `endDate`/`endDateIso`/`end_date_iso`/`resolutionTime` — Gamma
   populates **none** of these for closed markets, using `closedTime`
   instead (present in all 6/6 samples, absent in all 6/6 under the
   checked names). Extraction fails, the script falls to `not_found`
   *before* reaching resolved/winner logic, despite a fully successful
   fetch.
3. **[V]** Hypothesis (c) from the task — a stale candidate predicate
   matching already-resolved markets — is ruled out directly: 0 of 1,250
   candidates have `resolved=1` despite `resolution_date IS NULL`.

**Bound:** no correctness risk — the script only writes when
`resolution_date` is successfully derived, so this is a pure
opportunity-cost defect, not a data-corruption one. At current code,
~99% of the candidate pool is permanently unfindable regardless of
retries until the lookup path and date-field list are fixed. **The
script is effectively dead weight in the daily pipeline at its current
~0.6% hit rate**, though the underlying data is retrievable with a
corrected lookup/field-mapping (not implemented here — read-only task).

### Item 3 — step-7-vs-step-21 ordering — BENIGN

**[V]** Step numbers verified from live log output, not assumed:
`[7/29] Integrity audit (pre-ELO gate)` (calls `check_pending_flagged`)
and `[21/29] Evaluate new trader results`. The mechanism the prompt
describes is real — step 7 does read a backlog step 21 clears later —
but:

- `check_pending_flagged` is **Tier-2 REGRESSION**, not Tier-1 CRITICAL;
  the maintenance gate's exit code only counts Tier-1 criticals, so a
  Tier-2 regression never aborts the run, by design.
- Grepping ~40 logged instances of this check: **~33 report REGRESSION
  (alerted via Telegram), only ~7 report PASS** — nonzero backlog is the
  *normal* daily state because the check structurally runs before
  remediation, not a rare edge case masked by a false PASS.
- **[V]** Full log grep across all 66 runs: only 5 historical failures (4
  at step 6, 1 at step 13). **Zero failures ever occurred between step 7
  and step 21**, and step 21 itself has never failed in 37 executions.

The theoretical failure mode is mechanically possible but has never
occurred, and even absent a crash, this check alerts rather than silently
passing in the large majority of runs. `2026-08-19-pending-invariant-regression.md`
and `2026-08-18-pending-resolution-inconsistency.md` already cover the
adjacent real, standing issue: `check_pending_geo` has **no daily
evaluator wired into `daily_maintenance.py` at all** (unlike
`check_pending_flagged`) — a different, already-ledgered defect, not this
one.

### Item 4 — `fix_expired_unresolved.py` SQL interpolation — BENIGN

**(a) Dormant [V]:** not in `daily_maintenance.py`, not in `crontab -l`
(18 active entries, none reference it), no systemd unit references it.
Git log shows it ran exactly once (`9b4c833`). Live DB check confirms all
12 target markets currently hold the exact resolved outcomes the script
would have written — effect persisted, script now inert.

**(b) The interpolation** (`fix_expired_unresolved.py:53-73`,
`_synthetic_close_sql()`): `winning_outcome` is f-string-embedded 4 times
into `CASE WHEN outcome = '{win}' THEN ... ELSE ...` for the
`positions`-closing SQL only — the market-level `UPDATE markets` is
properly parameterized.

**(c) Not attacker-influenced [V]:** `winning_outcome` reaches this
function from exactly 3 call sites, all hardcoded literals (`"No"`,
`"No"`, `"Yes"`) — no runtime API call, DB read, or CLI arg ever feeds
this value. **Correction to the write-path census's own citation:** it
describes "10 hardcoded markets"; the actual hardcoded scope is **12**
(the cited 10 plus a ceasefire market and a bitcoin market handled by
separate functions calling the same interpolating SQL builder) — doesn't
change the risk conclusion, but the citation undercounts.

**(d)** Diverges structurally from the canonical `TradeEvaluator` (no
side-handling, no invalid state, case-sensitive compare) — same shape as
`position_tracker.py`'s already-known "3rd" win/loss implementation,
confirming this as the cluster's "4th," consistent with both cited prior
docs.

**Classification rationale:** the SQL-injection shape is real but
unreachable (dormant, hardcoded-only, already-run with verified-correct
effects). The underlying duplicate-win/loss-logic pattern is a genuine
smell but already tracked elsewhere and frozen here — no live path can
re-trigger this script's contribution to it.

### Item 5 — position construction, 4 INSERT implementations — REAL-BOUNDED

**List confirmed, line numbers current:** `position_tracker.py:518`
(live, primary), `database.py:390`'s `insert_position()` (**confirmed
dormant** — zero external callers found repo-wide, upgrading the
census's earlier "[I] unconfirmed" to a confirmed fact),
`background_pnl_worker.py:284` (live), `backfill_synthetic_closes.py:84`
(confirmed dormant).

**Columns:** all four use `INSERT ... ON CONFLICT(position_id) DO UPDATE
SET ...` — **none use `INSERT OR REPLACE` in live code.** The only
surviving `INSERT OR REPLACE` is in `docs/position_tracker_reference.py`
— a stale, non-imported reference file preserving the *pre-fix* code from
before `791dbf5` ("wire data_source into positions write paths + fix
INSERT OR REPLACE bugs") — the exact historical incident the task's
prompt named (`is_synthetic_close`) is already remediated in live code.

**Collision risk:** `position_id` is deterministic
(`f"{trader}_{market}_{outcome}_{ts}"`), generated once in the shared
`Position` class, so all 4 writers converge on the same id for the same
logical position by construction; the `positions` table's only unique
constraint is that same `position_id` primary key. Handled correctly via
`ON CONFLICT DO UPDATE`, not a duplicate-row risk.

**The real, bounded gap:** `background_pnl_worker.py`'s `ON CONFLICT DO
UPDATE SET` clause **omits `is_synthetic_close`** even though it's in the
INSERT column list; `backfill_synthetic_closes.py` includes it correctly
in both branches. Net effect: a position inserted while open, then
synthetically closed on a *later* `background_pnl_worker.py` run, gets
its financial fields updated correctly but `is_synthetic_close` silently
stays stale at 0 — any downstream consumer filtering by that flag
misclassifies these rows as organic closes.

**Bound:** one boolean column, one writer's UPDATE branch, triggers only
for positions synthetically closed on a run *after* their initial insert.
Financial correctness is unaffected.

### Item 6 — P&L aggregate recomputation, 5 implementations — REAL-BOUNDED (+1 sub-item NEEDS-INVESTIGATION)

**List confirmed:** `background_pnl_worker.py:352` (live), `monitor.py:1175`
(live), `trader_statistics.py:317` (dormant, manual-CLI only),
`backfill_synthetic_closes.py:145` (dormant), `reconcile_trader_aggregates.py:366`
(dormant).

**Formula agreement, not divergence, where it's checkable:** the two live
writers and the dormant `reconcile_trader_aggregates.py` all compute
`realized_pnl`/`avg_roi` via mathematically equivalent logic off the same
closed-position population. `trader_statistics.py`'s formula was **not
traced this session** (budget) — flagged as the sub-item.

**Columns differ** across the five (some write `total_pnl`, some
`total_invested`, `reconcile_trader_aggregates.py` writes the widest set
in one batched UPDATE). That file's own header comment already
self-flags `roi_percentage, total_pnl, unrealized_pnl` as
"DEAD/DUPLICATE — drop next session," not yet acted on — and a precedent
exists for partial convergence: `trader_statistics.py` has `win_rate`
explicitly disabled with a comment that it's "now owned by
`reconcile_trader_aggregates.py`," not extended to `realized_pnl`/`avg_roi`.

**Reconciliation:** `audit_invariants.py` has **no invariant on
`realized_pnl` or `avg_roi` directly** — but does have a Tier-3
`check_invested_mismatch` comparing `traders.total_invested` against a
live recomputation from `positions`. This **partially contradicts** the
write-path census's blanket "no invariant coverage at all" claim:
`total_invested` has soft coverage; the two columns named in this task's
prompt do not.

**ELO connection**, noted not traced: `compute_comprehensive_elo` is
defined at `analysis/comprehensive_elo_formula.py:65` — the downstream
consumer a P&L divergence would reach, per the task's own framing.

**Bound:** only 2 of 5 writers are live, and both agree with each other
and with the dormant third implementation on formula. What would settle
the sub-item: read `trader_statistics.py:222-266`'s
`calculate_comprehensive_stats()` to confirm its `pnl_based` path matches
— low priority given no confirmed live/scheduled call site for that file.

### Item 7 — `elo_last_updated` T-separated backfill — REAL-BOUNDED

**[V]** `SELECT COUNT(*) FROM traders WHERE elo_last_updated LIKE '%T%'`
today: **22,558** — identical to the 08-19 figure; zero rows fixed in the
one day since. The historical rate (22,560 → 22,558 over 07-14 → 08-19,
36 days) holds: **2 rows / 36 days ≈ 0.056 rows/day → 22,558 rows would
take ≈406,000 days ≈ 1,113 years** to reach zero via incidental rewrite
alone. Not "slow but converging" — practically a permanent asymptote.
(Caveat: the mechanism isn't a constant-rate process; a future full-table
touch for an unrelated reason could clear a batch of these in one shot —
but nothing like that is scheduled.)

**What a real backfill requires (shape only, not designed here):** (1) a
dedicated one-time script rewriting every T-separated `elo_last_updated`
value to the canonical space-separated form, touching no other ELO
column; (2) a verification step wired into `audit_invariants.py` (today's
`FLOOR_TS_TRADER_ELO = 22560` is a static baseline constant from
2026-07-14, not a live target-seeking check) confirming the count hits
and stays at 0.

**Bound:** confined to one column's format on ~26% of the ~87K trader
population; doesn't affect ELO values themselves, doesn't grow, doesn't
spread to other columns.

### Item 8 — Writer D's unretired code — REAL-BOUNDED

**(a) [V]** All four artifacts still exist in `monitoring/elo_bridge.py`:
`_batch_store_elo_results` (line 208), `_process_trader_chunk` (line
259), `quick_elo_update_for_traders` (line 330), `--quick-update` CLI
flag (line 781, dispatch at 813) — shapes unchanged from the 08-19 doc,
line numbers stable except the CLI flag (shifted from ~812-826 to 781).

**(b) [V]** `trader_analyzer.py` confirmed still has zero ELO-related
code.

**(c) [V]** No live invocation found anywhere, swept today: `crontab -l`
(full listing, no reference), `daily_maintenance.py` (zero grep hits),
every systemd unit's `ExecStart` for `polymarket-monitoring`,
`polymarket-observer`, and `polymarket-sunday-elo` (none reference it),
every script under `scripts/` excluding `archive/` (4 files import
`elo_bridge` but only for the unrelated, live `UnifiedELOMonitoringBridge`
/ Writer A path, never `quick_elo_update_for_traders`), and every
live-tree markdown runbook (zero hits outside `docs/` and
`archive/docs_historical/`).

**Bound:** dead code sitting in a live-imported module with zero live
call paths. Nothing today would fire it accidentally — it requires a
human to manually run `python monitoring/elo_bridge.py --quick-update`,
a deliberate action, not a latent trigger.

---

## Item 9 — anything else encountered, not investigated

One line each, aggregated across this session's own item-1 work and all
three forks' incidental findings, no further investigation performed on
any of these:

- `docs/MONITORING_ELO_INTEGRATION.md`, `docs/MONITORING_ELO_INTEGRATION_DESIGN.md`, `docs/ELO_SYSTEM.md`, `docs/ELO_PERFORMANCE_OPTIMIZATION.md`, `docs/DETAILED_ERROR_REPORTING.md` — live (non-archived) docs still describe `quick_elo_update_for_traders()` as the current monitoring-cycle ELO path; stale since well before this arc, sitting outside `docs/archive/` where a reader could mistake them for current.
- `docs/position_tracker_reference.py` — stale, non-imported snapshot of pre-`791dbf5` code still showing the fixed `INSERT OR REPLACE` pattern; risk of a future reader copying the wrong pattern from `docs/`.
- `monitoring/database.py`'s `insert_position()` — zero external callers anywhere in the repo; genuinely dead code, not merely "unconfirmed" as the write-path census hedged it.
- `reconcile_trader_aggregates.py` prints a runtime warning about `win_rate > 1.0` violations from same-market multi-trade double-counting, capped via `MIN(1.0, ...)` — a live, acknowledged data-quality workaround, unrelated to items 4–6.
- `scripts/daily_maintenance.py` step 8 (`check_canonical_definitions.py`, "Canonical definitions drift") was reported "failing daily" as of the 2026-08-19 write-path census; not re-verified this session — still open per that source, flagged again here since nobody has revisited it since.
- `check_pending_geo` (Tier-2) has **no daily evaluator wired into `daily_maintenance.py`** at all (unlike `check_pending_flagged`, which does) — growing on a base of never-evaluated historical trades per `2026-08-19-pending-invariant-regression.md`; a real, separately-tracked gap, distinct from item 3's (benign) finding.
- `2026-08-19-pending-invariant-regression.md` itself has an unresolved sub-question (whether the transient 60,345-row `check_pending_flagged` spike touched cohort survivors before self-healing) — no snapshot exists to settle it; still open.
- Gamma's `/markets` endpoint silently **ignores unrecognized query parameters** (e.g. `condition_id=`) rather than erroring, returning an unrelated default result set instead — a footgun for any future ad hoc probing of this API, discovered while investigating item 2.
- `hydrate_stub_markets.py`'s own module docstring implies it processes "200/day until the backlog is cleared" — given item 2's ~99% structural miss rate, this backlog will not clear at the documented pace; the comment is stale/optimistic relative to what the current code can achieve.
- `daily_maintenance.py`'s `DEFAULT_STEP_TIMEOUT` comment cites a historical 22,996.8s (6.39h) "Backfill transaction hashes" run as "completed successfully (not a true hang)" during the 2026-06-09/06-12 RPC incident — worth a skeptical re-check someday; a 6+ hour "non-hang" is a large outlier under any framing.
- Working tree (`first-repo`) carries uncommitted background-system churn unrelated to this investigation: `data/.last_requeue_run`, `data/category_backfill_state.json`, `logs/arb_bot_exclusions.log`, `logs/focus_ratio_review.json`, plus two untracked files under `data/characterizations/` — noted for completeness, not touched.

---

## Closing recommendation

Ranked by where real work should go next, reasoning given for the ranking
itself (not just the items):

**1. Item 1 — the Gamma ceiling (REAL-UNBOUNDED).** This is the only item
on the register whose blast radius is genuinely unknown, and it sits
upstream of the entire resolution-discovery pipeline this arc has spent
two stages building a canonical write path for — an unbounded gap in
*discovering* resolutions undermines the value of getting the *write*
path right. It doesn't need a full fix to be worth prioritizing next: a
bounded sizing exercise (walk `/markets/keyset` to depth against a sample,
or CLOB-sample the 511,829 dateless population) converts "unknown" to
"known" cheaply, and that number should exist before anyone decides how
urgently to act on it.

**2. Item 2 — `hydrate_stub_markets.py`'s hit rate (REAL-BOUNDED, but
cheap and already fully diagnosed).** Unlike item 1, this one doesn't need
further investigation — the two defects (missing-identifier fallback,
wrong date-field names) are pinned down precisely enough to fix directly.
It's ranked second, not first, because its blast radius is already known
and its population (1,258 external_seed-trader markets) is a small slice
of item 1's (513,179 unresolved markets) — but fixing it is nearly free
relative to item 1's sizing work, and it directly shrinks the population
that compounds item 1's finding (markets with no date metadata at all).
Good next PR-sized task.

**3. Item 5's `is_synthetic_close` staleness (REAL-BOUNDED, narrow,
cheap).** A single missing column in one `ON CONFLICT` clause, with a
concrete, already-diagnosed downstream consequence (silent
misclassification of synthetically-closed positions in anything that
filters on that flag). Ranked third over item 7 (`elo_last_updated`,
similarly cheap) because it's a correctness/classification issue for
*current* data going forward, not a cosmetic format issue on historical
rows — lower severity than items 1–2, but the fix is close to a one-line
change with a clear, bounded blast radius, making it good opportunistic
work whenever someone is next in that file.

*Not ranked, but worth a name-check: item 8 (Writer D) needs no urgency —
it has zero live trigger path — and can be deleted whenever convenient
rather than scheduled. Item 6's `trader_statistics.py` sub-item is genuinely
low-priority given it has no confirmed live call site.*

---

*Generated 2026-08-20. Investigation split across this session (item 1,
directly) and three parallel forks (items 2–8, under the same standing
instruction — verified/inferred tagging, read-only, classify-don't-resolve
budget). Sources cited inline per item. No code modified. No writer
migrated. No schema touched. Nothing repaired.*
