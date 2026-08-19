# 2026-08-19 — market-resolution write cluster: authority, evidence, and overwrite risk

Read-only. No writer modified, no canonical helper written, no
consolidation implemented. Every claim tagged **[V]** (verified —
file:line, git commit, or live query given) or **[I]** (inferred,
explicitly marked). This is a map of authority and evidence, not a
verdict on which writer is "correct" — per the task's explicit
instruction, that question is not asked here.

Committed script for Q4:
`scripts/characterize_resolution_write_inconsistency.py` (first-repo).
Artifact: `data/characterizations/resolution_write_inconsistency_20260819T190204Z.json`.

---

## Q1 — Per-writer characterization

**Scope note [V]:** the census named "9+" writers; reading each in full
surfaced **13 distinct write sites across 11 files** (some files, notably
`fast_resolution_check.py`, contain multiple independent sites). All 13
are covered below.

| # | Writer (file:line) | Columns | Evidence source | Authority | Guard (exact) | resolution_date semantics | Invocation |
|---|---|---|---|---|---|---|---|
| 1 | `monitoring/database.py:518` `update_market()` (INSERT…ON CONFLICT DO UPDATE) | resolved, winning_outcome, resolution_date, end_date, title, category | Caller-supplied (varies — see rows 1a/1b below) | Establishes on INSERT; **would overwrite unconditionally on the ON CONFLICT branch** (`resolved = excluded.resolved`, `winning_outcome = excluded.winning_outcome`, no guard) — resolution_date is the one column COALESCE-guarded here | `resolved`/`winning_outcome`: **unconditional** on conflict. `resolution_date`: `COALESCE(resolution_date, excluded.resolution_date, excluded.end_date)` | Falls back to `end_date` when no explicit `resolution_date` given (line ~515, `effective_resolution_date`) — event-time when caller supplies a real one, otherwise the market's own scheduled end date, never `datetime.now()` | Live, `polymarket-monitoring` — but see 1a/1b: its two confirmed live callers pre-guard with `if market_exists(): return`, so the ON CONFLICT branch is not reached via them |
| 1a | ↳ `store_market_from_trade` (database.py:762, calls #1) | same, called with `resolved=False, winning_outcome=None` always | none (hardcoded defaults) | establishes a stub only | pre-guarded: `if market_exists(): return` before calling | n/a (no resolution value passed) | live, `monitor.py:911` |
| 1b | ↳ `store_market_dict` (database.py:813, calls #1) | same, called with `resolved = market.get('closed') or market.get('archived')` | **Gamma /markets `closed`/`archived` fields** | establishes at first sighting — but `winning_outcome=None` always, even when `resolved=True` is passed — **this is the confirmed source of the 123-row `resolved=1, winning_outcome=NULL` state's sibling risk for markets NOT hitting the o16-tier2 sentinel path** [I] not itself the source of the 123 (see Q4) but structurally capable of producing the same shape | pre-guarded: `if market_exists(...): return` before calling | n/a | live, `monitoring/trader_analyzer.py:88`, itself called from `monitor.py` |
| 2 | `monitoring/database.py:551` `update_market_resolution()` | resolved, winning_outcome, resolution_date, last_checked | Caller-supplied `winning_outcome` param only | establishes, if called | **none — fully unconditional** | `resolution_date = datetime.now()` — **write-time**, the O-36 shape | **No live call site found** — zero callers outside `scripts/archive/test_resolutions.py` |
| 3 | `scripts/fast_resolution_check.py:265` `batch_update_resolved_markets` | resolved, winning_outcome, resolution_date, last_checked | **Gamma API** `/markets?closed=true`, winner inferred via `outcomePrices >= 0.99` | establishes | Candidate SELECT: `resolved=0 OR NULL`; re-checked `if is_resolved: continue` immediately before write. `resolved`/`winning_outcome`: effectively single-fire per market. **`resolution_date`: unconditional, no COALESCE** | `resolution_date = datetime.now()` — **write-time** | Scheduled — `daily_maintenance.py` step 16 (`run_fast_check`, always runs this site first) |
| 4 | `scripts/fast_resolution_check.py:385` `run_stale_clob_pass` | resolved, winning_outcome, resolution_date, last_checked | **CLOB API** `token.winner` direct flag — its own docstring calls this "the authoritative resolution source" | establishes | Candidate: `resolved=0/NULL AND resolution_date < now-7d`. `resolution_date = COALESCE(resolution_date, ?)` | `datetime.now()` fallback, **but only fills if currently NULL** | Scheduled — `daily_maintenance.py` step 16, **and** `weekly_resolution_sweep.sh` (Sun 03:30 cron, direct call) |
| 5 | `scripts/fast_resolution_check.py:495` `run_recent_overdue_pass` | resolved, winning_outcome, resolution_date, last_checked | **CLOB API**, same `token.winner` flag | establishes | Candidate: 0–7-day recency window, resolved=0/NULL. `resolution_date = COALESCE(...)` | `datetime.now()` fill-if-NULL | Scheduled — `daily_maintenance.py` step 16, **and** weekly cron |
| 6 | `scripts/fast_resolution_check.py:592` `run_external_seed_pass` | resolved, winning_outcome, resolution_date, last_checked | **CLOB API**, same `token.winner` flag | establishes | Candidate: external_seed traders' markets, resolved=0/NULL, >7d stale. `resolution_date = COALESCE(...)` | `datetime.now()` fill-if-NULL | Scheduled — `daily_maintenance.py` step 16 only (not in the weekly sweep) |
| 7 | `scripts/backfill_o16_tier1.py:224,234` (2 sites: winner / no-winner sentinel) | resolved, winning_outcome (site 234 only), resolution_date, data_source, last_checked | **Gamma API**, direct-by-api_id; winner via `outcomePrices>=0.99` → `winnerIndex` fallback → `__RESOLVED_NO_WINNER__` if all-zero prices on a closed market | establishes | Candidate query is self-shrinking (`resolved=0/NULL`, one-off historical population). `resolution_date = COALESCE(...)` | **`res_date = closedTime \|\| umaEndDate \|\| endDate \|\| local end_date`** — genuinely **event-time**, pulled from the API response, not `datetime.now()` | **No live call site** — one-off O-16 Tier-1 remediation, already run to completion per memory (`project_o16_resolution_gap`) |
| 8 | `scripts/backfill_o16_tier2.py:213,223` (2 sites, same shape as #7, own copy of `extract_resolution`) | same as #7, `data_source = 'gamma_backfill_tier2_2026-07-06'` | Gamma API, same extraction logic (duplicated, not shared, with #7) | establishes | same COALESCE guard | **event-time**, same derivation as #7 | **No live call site** — one-off, already run; its `data_source` tag is the confirmed origin of all 123 `resolved=1/winning_outcome=NULL` rows (Q4) |
| 9 | `scripts/resolve_legendary_markets.py:210,215` | resolved, winning_outcome (site 215 only), resolution_date, last_checked | Gamma API, per-market targeted query; same price≥0.99/no-winner-sentinel extraction family | establishes | Candidate: "overdue LEGENDARY trader markets," resolved=0. `resolution_date = COALESCE(...)` | `datetime.now()` — **write-time** (fixed by O-17 for the *missing* case, not the *write-time-vs-event-time* case — see Q3) | Scheduled — `daily_maintenance.py` step 20 |
| 10 | `scripts/legendary_positions_scan.py:304,314` | same shape as #9 | Gamma API, same family | establishes | same COALESCE pattern (added by the same O-17 commit) | `datetime.now()` — write-time | **Direct crontab entry**, Mon 07:30 — not via `daily_maintenance.py` |
| 11 | `scripts/hydrate_stub_markets.py:200` | resolution_date, end_date, resolved, winning_outcome, category, title — **all CASE/COALESCE-guarded, fill-only-if-empty** | Gamma API `endDate`/`endDateIso`/`resolutionTime` for resolution_date; `outcomePrices>=0.99` for winner | establishes gaps only, never overwrites a set value | Candidate: `resolution_date IS NULL` (**not** filtered by `resolved`, so its candidate set can include already-resolved rows — but every write column is individually guarded, so it cannot clobber an existing value regardless) | **Event-time** — derived from the API's own end/resolution fields, same pattern as #7/#8, not `datetime.now()` | Scheduled — `daily_maintenance.py`, post-test-suite step |
| 12 | `scripts/fetch_market_resolutions.py:162` | resolved, winning_outcome, resolution_date, last_checked | **CLOB API** direct query | establishes | Candidate: markets without existing resolution data (`--force` re-checks all). **`resolution_date` unconditional, no COALESCE at all** | `datetime.now().isoformat()` — **write-time** | **No live call site found** |
| 13 | `scripts/fix_expired_unresolved.py:93` | resolved, winning_outcome, resolution_date | **Hardcoded, human-verified list** (`API_ID_NO_MARKETS`, 10 specific IDs) confirmed against Gamma at some past point, frozen into the script | establishes, from a point-in-time human check, not a live call at write time | `WHERE condition_id = ? AND resolved = 0` — state-conditional, but no COALESCE (moot given the WHERE already requires resolved=0, so resolution_date cannot have been previously set by this same transition) | `datetime.now()` — **write-time** | **No live call site found** — narrow, already-run, 10-market scope |

**Not itemized above but touching the same 3 columns via a documented,
different-purpose path:** `monitoring/monitor.py:219,274`
(`_batch_update_market_end_dates`, `_backfill_clob_end_dates`) — writes
**only** `end_date` and `resolution_date` (never `resolved`/`winning_outcome`),
explicitly as a **proxy**, per its own docstring: *"resolution_date as
proxy where NULL... lets STR-003 and other signals see approaching
deadlines even before the market officially resolves."* Guard:
`WHERE end_date IS NULL`, `COALESCE(resolution_date, ?)`. Evidence: Gamma
`/events` category-map refresh (first site) / CLOB market end-date lookup
(second site). Live, `polymarket-monitoring`. This is the writer most
directly responsible for the 1,349-row `resolution_date set, resolved=0`
state in Q4 — **by design**, not by defect, per its own stated purpose.

**Not itemized in the per-writer table but structurally excluded:**
`scripts/backfill_missing_markets.py:135` (`INSERT OR IGNORE`) —
evidence: Gamma API; never overwrites, since `OR IGNORE` means it only
fires when the row doesn't exist at all. Lowest-risk category by
construction. No live call site found.

---

## Q2 — The overwrite matrix

**Framing, stated precisely per the task's instruction:** "lower authority
overwrites higher authority" presumes a hierarchy. This cluster does not
have a declared one — every writer treats itself as authoritative for the
rows it touches. The candidate-selection guard (`WHERE resolved=0`,
present in every establishing writer except #1's ON CONFLICT branch and
#2) means `resolved`/`winning_outcome` are, in practice, **first-writer-wins**
across the query-guarded writers: once a market is `resolved=1`, no other
writer's own candidate SELECT re-targets it. The real exposure is
narrower than "any writer can clobber any other" — it is concentrated in
the writers whose candidate selection or write statement does **not**
respect that convention.

| Writer A | Writer B | Same market reachable by both? | Column(s) in play | Who wins | Mechanism |
|---|---|---|---|---|---|
| #1 `update_market` (ON CONFLICT branch) | any establishing writer (#3–#13) | **Yes, in theory** — if a caller of `update_market()` other than the two known live ones (#1a/#1b) ever calls it on an existing, already-resolved market with `resolved=False` | resolved, winning_outcome | **Whichever calls last** — no guard at all on this branch | Ordering, by chance — **not currently reachable via any confirmed live call site**, since both live callers pre-guard with `market_exists()`. Latent, not demonstrated. |
| #2 `update_market_resolution` | any establishing writer | **No live path found in either direction** — #2 has zero live callers | resolved, winning_outcome, resolution_date | n/a | Dormant — cannot fire today |
| #11 monitor.py proxy writes (`_batch_update_market_end_dates`/`_backfill_clob_end_dates`) | #3 `batch_update_resolved_markets` | **Yes, and demonstrated live** — monitor.py runs continuously; step 16 runs once daily. A market can accumulate a proxy `resolution_date` (from `end_date`) while `resolved=0`, then get its `resolution_date` **overwritten** by #3's unconditional `datetime.now()` write the next time step 16 flips it to `resolved=1` | resolution_date | **#3, the later daily run, on any market where both fired** | Ordering (daily cadence) + **#3's missing COALESCE guard**. Confirmed live: Q4 finds 1,349 markets currently in the `resolution_date set, resolved=0` precursor state this pattern requires. |
| #3 `batch_update_resolved_markets` | #12 `fetch_market_resolutions.py` | Same shape as above **if #12 were ever run** — both write `resolution_date` unconditionally | resolution_date | Whichever runs later | Ordering, by chance — **#12 has no live call site**, so this pair is latent, not active |
| #7/#8 `backfill_o16_tier1/tier2` (event-time resolution_date) | #3/#9/#10/#12 (write-time resolution_date) | **No** — #7/#8 are one-off, already-run, and their candidate query (self-shrinking, `resolved=0/NULL`) has no remaining rows to re-touch; not concurrently live with anything | resolution_date | n/a — not concurrent | n/a |
| #4/#5/#6 (CLOB, COALESCE-guarded) | #9/#10 (Gamma, COALESCE-guarded, `datetime.now()`) | **Yes, if the same market is a LEGENDARY-trader market that's also stale/overdue** — both target overlapping-but-differently-scoped `resolved=0` populations | resolved, winning_outcome, resolution_date | **Whichever runs first sets `resolved`/`winning_outcome`; the second sees `resolved=1` in its own candidate SELECT and is excluded.** `resolution_date`: COALESCE on both sides, so whichever writes first "wins" the value, the second is a no-op on that column | Ordering, but **self-resolving** — both are COALESCE-guarded, so no clobber either direction, just "first past the post" for which evidence source ends up recorded (CLOB vs. Gamma), with no record of which it was |
| #9/#10 (`resolve_legendary_markets.py`/`legendary_positions_scan.py`) | each other | **Yes** — both target overlapping LEGENDARY-market populations, one via daily_maintenance step 20, one via Monday cron | resolved, winning_outcome, resolution_date | Same as above — self-resolving via the shared `resolved=0` guard + COALESCE on resolution_date | Ordering, self-resolving, no clobber |
| #11 (hydration, all-column CASE-guarded) | any other writer | **Yes**, hydrate's candidate query isn't `resolved`-filtered | resolved, winning_outcome, resolution_date, category, title | **Never hydrate** — every column it writes is individually guarded to fill-only-if-currently-empty | Guard — this is the one writer in the cluster that structurally cannot overwrite, regardless of ordering |

**The lower-overwrites-higher set, named explicitly as requested:**
exactly **one demonstrated-live pair** — **#11 monitor.py's proxy
`resolution_date` (evidence: real `end_date`/CLOB lookup, but explicitly
labeled a guess) overwritten by #3 `batch_update_resolved_markets`'s
`datetime.now()` (evidence: nothing — a write-time stamp)** — arguably a
downgrade in evidence quality even though neither writer claims to
represent the true resolution timestamp. One **latent, not-currently-reachable**
pair: #1's ON CONFLICT branch, unconditional, could overwrite any
established `resolved`/`winning_outcome` if ever called by something
other than its two known, pre-guarded live callers.

---

## Q3 — The `fast_resolution_check.py` asymmetry

**[V] Established empirically and via git history, not assumed.**

**What the unconditional site (`batch_update_resolved_markets`, line 265)
does that the other three don't:** writes `resolution_date = ?` bound
directly to `datetime.now()`, with **no `COALESCE`** — it will overwrite
any existing `resolution_date` value for a market that passes its
`resolved=0` guard, unconditionally.

**Is the asymmetry deliberate?** **[V] Partially — traced to a specific
commit and a specific, narrower bug report than "fix all write-time
timestamps."** Commit `a0e08706` (2026-07-01, *"fix: co-write
resolution_date in fast_resolution_check.py's 3 passes + legendary
scripts (O-17)"*) added the `COALESCE` guard to exactly **3** of the 4
sites — `run_stale_clob_pass`, `run_recent_overdue_pass`,
`run_external_seed_pass` — plus `resolve_legendary_markets.py` and
`legendary_positions_scan.py` (2 sites each = 4 more), for **7 total
write paths**. The commit's own diff, read directly, shows the **pre-fix**
code for those 3 sites had **no `resolution_date` column in the SET
clause at all** — the bug being fixed was `resolution_date` staying
**NULL** forever on markets resolved through those paths (breaking
`requeue_resolved_market_traders.py`'s filter), not "write-time vs.
event-time." `batch_update_resolved_markets` was **not touched** by this
commit because it did not exhibit that bug — it had already been writing
*something* to `resolution_date` (the write-time value) since before this
fix, so O-17's own diagnostic criterion ("resolved=1 without writing
resolution_date") did not flag it. The commit message itself states the
7 sites now use *"the same `datetime.now()` source already used by the
working writers"* — i.e., write-time semantics for `resolution_date` was
the accepted, unquestioned status quo at fix time across the whole
cluster; O-17 closed the NULL gap, not the write-time-vs-event-time gap.
**The asymmetry is a side effect of the bug report's own scope, not a
considered decision to leave one site unguarded** — no commit, comment,
or doc found this session states a reason the 4th site was intentionally
left without the guard.

**What it can overwrite:** per Q2, a proxy `resolution_date` set earlier
by `monitor.py`'s end_date-derived writes (while the market was still
`resolved=0`) — demonstrated live via the Q4 count of 1,349 markets
currently sitting in that precursor state.

---

## Q4 — Live inconsistency counts

**[V]** `python3 scripts/characterize_resolution_write_inconsistency.py`,
run against production (read-only):

| State | Count |
|---|---|
| `resolved=1` with `winning_outcome` NULL/empty | **123** |
| `winning_outcome` set with `resolved=0` | **0** |
| `resolution_date` set with `resolved=0` | **1,349** |
| `resolved=1` with `resolution_date` NULL | **8** |

**Context, not left as raw counts:**
- **123** — traced to a single, exact cause: **all 123** carry
  `data_source = 'gamma_backfill_tier2_2026-07-06'` — writer #8's
  (`backfill_o16_tier2.py`) `__RESOLVED_NO_WINNER__` sentinel path
  (all-zero-price closed markets have no winner by definition; this
  schema has no distinct sentinel column for "resolved with no winner"
  vs. "not yet resolved," so it's recorded as `winning_outcome=NULL`).
  **Not an unattributed defect — fully explained, single writer, single
  documented mechanism.** Zero of these 123 are in Geopolitics/Elections.
- **0** — the `winning_outcome`-without-`resolved` state does not occur.
  Consistent with Q2's finding that no live writer sets `winning_outcome`
  without also setting `resolved=1` in the same statement.
- **1,349** — this is `monitor.py`'s documented proxy pattern (Q1, Q2),
  not a defect by that writer's own stated design — though it is the
  precondition for the one demonstrated overwrite case in Q2.
- **8** — a small residual of the O-18 population (60 pre-O-17-fix NULL
  rows, per the `a0e08706` commit message, left unbackfilled and
  ledgered separately). Down from 60 to 8 — **[I]** not traced this
  session whether that's from natural resolution (these specific markets
  eventually got resolved through a COALESCE-guarded path, filling
  `resolution_date` alongside `resolved`) or a separate partial backfill;
  flagged, not chased.

---

## Q5 — Is a canonical path derivable (describe only)

**[V]/[I] A coherent single write path is describable.** Shape: one
function, e.g. `mark_market_resolved(market_id, winning_outcome,
resolution_date, evidence_source, allow_no_winner=False)`, called by
every *establishing* writer (#2–#10, #12, #13), with these properties
inferred as necessary from the per-writer read above:
- `resolved`/`winning_outcome` set only if currently unset (matches what
  the candidate-selection guard already achieves informally across most
  writers — made structural instead of convention).
- `resolution_date` accepted as an **explicit parameter**, not computed
  inside the helper — callers with event-time evidence (#7, #8, #11) pass
  the true API timestamp; callers with only write-time knowledge (#3, #9,
  #10, #12, #13) would still pass `datetime.now()`, but the **fact of
  which kind was passed** could be recorded (an audit-trail improvement
  the task does not ask to build, named only because Q5 asks what the
  path would look like).
  - `allow_no_winner` — an explicit flag for the `__RESOLVED_NO_WINNER__`
    case (#7, #8), replacing the implicit "just leave winning_outcome
    NULL" convention with a stated one.
  - `evidence_source` — a required tag (CLOB / Gamma / manual-verified /
    hydration), turning the currently-implicit authority ranking (Q2) into
    a recorded fact per row, which is also what would make a future
    audit-trail column meaningful.

**What each existing writer becomes:** #3–#10, #12, #13 become thin
callers passing their own evidence + values. #11 (`hydrate_stub_markets.py`)
would call it for the resolution-specific columns only, keeping its
category/title-filling logic separate (different concern). #1's live
callers (#1a/#1b) would call it only when their own initial API read
already shows `resolved=True` at market-discovery time — otherwise they
insert a plain unresolved stub as today.

**Named exception — could NOT be expressed this way:** `monitor.py`'s
proxy writes (`_batch_update_market_end_dates`/`_backfill_clob_end_dates`).
These do not "establish a resolution" at all — they estimate an *upcoming*
deadline for markets that have **not** resolved, explicitly so downstream
signals can see approaching deadlines early. Folding them into a
"mark resolved" canonical path would blur exactly the distinction (proxy
guess vs. established fact) that is the root of the `resolution_date`
confusion this whole cluster exhibits. **These should remain a separate,
distinctly-named operation** (e.g. `estimate_resolution_deadline`) — not
a defect in the current design, just a different question being answered,
per the same framing the task applied to `apply_synthetic_closes` in the
prior write-path census.

---

## Q6 — What would break if each writer were removed or subordinated

| Writer | Downstream consumer that would notice |
|---|---|
| #1/#1a/#1b (`update_market`, `store_market_from_trade`, `store_market_dict`) | **Everything** — this is how markets enter the DB at all. Removing it stops market ingestion outright, not just resolution-writing. |
| #2 (`update_market_resolution`) | **[I]** None found — no live caller. Removing it should be invisible to any live consumer; only risk is an unnoticed future caller depending on it. |
| #3 `batch_update_resolved_markets` | `daily_maintenance.py` step 16's bulk resolution sweep — the primary daily mechanism for detecting the *bulk* of newly-resolved markets via Gamma's recency-sorted feed. Downstream: `evaluate_new_trader_results.py` (step 21), the audit's `pending_geo`/`pending_flagged` invariants, and ultimately every ELO/P&L computation gated on `resolved=1`. |
| #4/#5/#6 (the 3 CLOB passes) | Markets the Gamma bulk scan structurally cannot reach (>20K-recency cap, no `api_id`, `external_seed` traders' historical markets) — per their own docstrings, these exist *because* #3 misses them. Removing any one reopens the specific gap it was built to close (recent-overdue-no-id, stale->7d, or external_seed history). |
| #7/#8 (`backfill_o16_tier1/tier2`) | Already-run, one-off — no live consumer depends on them running again; the *effect* (the historical rows they fixed) is what matters, already persisted. Removing the scripts themselves would break nothing live; removing their **effect** (re-corrupting those rows) would break whatever currently reads those markets' resolution state. |
| #9 `resolve_legendary_markets.py` | The LEGENDARY-trader-tier resolution pipeline specifically — `daily_maintenance.py` step 20's targeted pass exists because LEGENDARY-trader markets need faster/more reliable resolution detection than the bulk pass provides (per its own "targeted resolution pass for overdue LEGENDARY trader markets" framing). |
| #10 `legendary_positions_scan.py` | The Monday-morning trading-swarm positions-scan pipeline (`logs/positions_scan.log`) — a separate cadence/audience from #9 despite overlapping population; removing it likely delays LEGENDARY-market resolution detection to whatever #9/#3 catch on their own schedule, not a hard break. |
| #11 `hydrate_stub_markets.py` | Any market that entered the DB as a bare stub (via #1a's `resolved=False, winning_outcome=None` trade-tape-only creation) and never got enriched any other way — its docstring states it exists specifically to fill metadata gaps left by other ingestion paths. |
| #12 `fetch_market_resolutions.py` | **[I]** No live caller found — removing it should be invisible today; it reads as an earlier/alternate implementation of what #3–#6 now do via `daily_maintenance.py`. |
| #13 `fix_expired_unresolved.py` | Already-run, narrow (10 hardcoded markets) — the *effect* persists; removing the script breaks nothing live. |
| Monitor.py proxy writes (`_batch_update_market_end_dates`/`_backfill_clob_end_dates`) | STR-003 and "other signals" that read `resolution_date` as an approaching-deadline proxy before real resolution — named explicitly in the code's own comment. Removing this would leave those signals blind to markets whose `resolution_date` is otherwise NULL until a resolution pass fires. |

---

## Summary

**13 write sites, 11 files, one true unconditional-and-live resolution_date
overwrite risk** (#3, `batch_update_resolved_markets`), demonstrated
against a live precursor population of 1,349 markets currently holding a
proxy `resolution_date`. **123 `winning_outcome=NULL` rows are fully
attributed to one deliberate, documented mechanism** (o16-tier2's
no-winner sentinel), not an unexplained defect. **The `resolved`/`winning_outcome`
overwrite risk is structurally narrow** — first-writer-wins across nearly
every establishing writer via a shared, if uncoordinated,
`WHERE resolved=0` convention — concentrated instead in two paths
(`update_market`'s ON CONFLICT branch, `update_market_resolution`) that
are unconditional but **not currently reachable via any confirmed live
call site**. Event-time vs. write-time `resolution_date` semantics split
roughly evenly across the cluster — `backfill_o16_tier1/tier2` and
`hydrate_stub_markets.py` get it right (true API timestamps); `fast_resolution_check.py`'s
4 sites, `resolve_legendary_markets.py`, `legendary_positions_scan.py`,
`fetch_market_resolutions.py`, and `fix_expired_unresolved.py` all use
`datetime.now()` — the O-36 bug shape, confirmed present in **at least 8
of the 13 sites**, not just the one previously named.

---

*Generated 2026-08-19. Sources: `monitoring/database.py`,
`monitoring/monitor.py`, `scripts/fast_resolution_check.py` (full read,
all 4 write sites + `run_fast_check`), `scripts/backfill_o16_tier1.py`
(full read, incl. `extract_resolution`), `scripts/backfill_o16_tier2.py`,
`scripts/resolve_legendary_markets.py`, `scripts/legendary_positions_scan.py`,
`scripts/hydrate_stub_markets.py` (full read), `scripts/fetch_market_resolutions.py`,
`scripts/fix_expired_unresolved.py`, `scripts/backfill_missing_markets.py`,
`git log`/`git show a0e08706` (O-17 commit, full diff read),
`2026-08-19-write-path-census.md` (`9938a04`), live DB queries via this
session's new `scripts/characterize_resolution_write_inconsistency.py`
(first-repo) → `data/characterizations/resolution_write_inconsistency_20260819T190204Z.json`
(first-repo, both committed this session). No writer modified, no
canonical helper built, no consolidation implemented.*
