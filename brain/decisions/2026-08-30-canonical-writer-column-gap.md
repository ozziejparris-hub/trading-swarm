# Canonical Writer Column Gap — Full Diff and Consumer Trace

**Scope:** read-only. Establishes the full column gap between `mark_market_resolved()`
and every writer it replaces, traces consumers for each gap column, tests the
geo/elec-backlog hypothesis from the prior verification, and quantifies the stranded
population — before any fix. Nothing remediated, nothing resumed.

Tagging: [V]=verified this session (code/query read directly), [I]=inferred. Per the
standing instruction, every claim in the task prompt was checked against the specific
writer it names, not assumed — see §3, where the prior verification's own scope
correction ("this hypothesis needs checking against the writer it concerns") applied
to its own §4a finding and did not hold as stated.

---

## VERDICT

**`last_checked` is not the only gap column, but it is the only one with confirmed,
large, ongoing downstream consequence.** A second gap column — `category` — has an
even larger stranded population (214,155 of 214,413 clob-resolved markets, 99.9%,
sit as `'Unknown'`) with its own, structurally distinct root cause (a 50/day backfill
throughput problem, not a silent gate) but the same practical effect: sweep-resolved
markets are invisible to every category-scoped consumer, including the geo_elo
pipeline and the exact audit check the prior investigation used to measure the
geo/elec backlog.

**The geo/elec-backlog hypothesis from the prior verification FAILS.** Only 1,069 of
the ~23,213 geo/elec pending trades (4.6%) sit on clob-resolved markets; **22,144
(95.4%) sit on markets with no evidence-source tag at all** — i.e., resolved by a
non-canonical writer, all of which correctly set `last_checked` and therefore pass
the requeue gate fine. The flat ~23,000 trend is not sweep fallout. It is a separate,
older, unexplained backlog that predates this entire investigation and was not
caused by either gap column found here. Per the task's own framing, this is the more
serious outcome: there are now two independent unexplained problems, not one root
cause wearing two faces.

**The stranding is structural, not incidental, and would recur identically if the
sweep resumed unfixed.** None of the six sweep driver scripts (segments 1-4,
tranches 1-2) reference `last_checked` anywhere — confirmed by direct grep, zero
matches across all six files. One writer (`fast_resolution_check.py`'s Gamma
branch) already discovered and manually patched around this exact gap with an
explicit code comment naming it — that patch was never propagated to the sweep's own
driver scripts, which is the proximate reason the sweep-specific stranding exists at
all.

---

## PART 1 — The column diff

### 1.1 What `mark_market_resolved()` writes [V]

Exactly six columns, one `UPDATE` statement (`monitoring/resolution_writer.py:224-234`):

```
resolved, winning_outcome, resolution_date, resolution_recorded_at,
resolution_evidence_source, resolution_evidence_detail
```

### 1.2 Re-verified writer census [V — re-derived, not inherited from the prior doc]

Re-ran `scripts/scan_write_paths.py` fresh this session and read every match's
surrounding source, rather than trusting the prior doc's 13-file list. Two
corrections to that prior list:

- **`monitor.py`'s two matches confirmed, again, not resolution writers** — they only
  touch `end_date`/`resolution_date` via a `COALESCE`-guarded proxy fill, never
  `resolved` or `winning_outcome`. Excluded, as before.
- **A writer the prior census missed: `monitoring/database.py`'s `update_market()`**
  (line 503-533), an `INSERT ... ON CONFLICT(market_id) DO UPDATE`. This is a
  *third* markets-resolution write path in `database.py` alongside the
  `update_market_resolution()` method the prior doc found (line 539). It sets
  `resolved = excluded.resolved` and `winning_outcome = excluded.winning_outcome`
  **unconditionally** — no evidence-source ranking, no accept/reject logic, just
  whatever the caller passed (default `resolved=False`). Two live call sites exist
  (`database.py:802`, `:862`); one (`:862`) passes `resolved=<derived from API>` but
  **always `winning_outcome=None`** — a related, narrower defect (a market can reach
  `resolved=1, winning_outcome=NULL` this way) noted here but not chased further; it
  affects 123 rows DB-wide currently, immaterial next to the two gaps below. Named,
  not investigated — separate failure class (incomplete-field write, not
  canonical-vs-non-canonical column gap).

Full column set per writer/branch, non-canonical only:

| Writer | Branch | Full column set in that `UPDATE`/`INSERT` |
|---|---|---|
| `monitoring/database.py:539` `update_market_resolution()` | only | `resolved, winning_outcome, resolution_date, `**`last_checked`** |
| `monitoring/database.py:503` `update_market()` (UPSERT) | only | `resolved, winning_outcome, resolution_date, `**`last_checked`**`, title, category, end_date, condition_id` |
| `scripts/backfill_o16_tier1.py:224/234` | no-winner / with-winner | `resolved, [winning_outcome], resolution_date, `**`data_source`**`, `**`last_checked`** |
| `scripts/backfill_o16_tier2.py:213/223` | no-winner / with-winner (identical) | `resolved, [winning_outcome], resolution_date, `**`data_source`**`, `**`last_checked`** |
| `scripts/fast_resolution_check.py` (4 write branches, diffed separately per the task's instruction) | Branch 1, line 310 — **canonical** (Gamma) | `mark_market_resolved()`'s 6 columns, **plus an explicit separate direct-write of `last_checked`** immediately after (line 321-324) — self-patched, with a code comment: *"last_checked is not a canonical-path column — stays a direct write, unchanged."* |
| | Branch 2, line 440 — direct | `resolved, winning_outcome, resolution_date, `**`last_checked`** |
| | Branch 3, line 550 — direct | `resolved, winning_outcome, resolution_date, `**`last_checked`** |
| | Branch 4, line 647 — direct | `resolved, winning_outcome, resolution_date, `**`last_checked`** |
| | (non-resolving branches at 222/532/544 touch only `last_checked`, for still-open/no-winner markets — not part of the diff) | |
| `scripts/hydrate_stub_markets.py` | Branch 1 (`is_resolved`) — **canonical** | `mark_market_resolved()`'s 6 columns, plus a separate direct-write of **`end_date, category, title`** — explicitly does **not** patch `last_checked` (no comment acknowledging the gap here, unlike `fast_resolution_check.py`) |
| | Branch 2 (`else`, proxy-fill on still-open markets) | `resolution_date, end_date, resolved` (CASE-guarded), `winning_outcome` (CASE-guarded), `category` — no `last_checked` |
| `scripts/resolve_legendary_markets.py:210/215` | no-winner / with-winner | `resolved, [winning_outcome], resolution_date, `**`last_checked`** |
| `scripts/legendary_positions_scan.py:304/314` | with-winner / no-winner(price-sum-zero) | `resolved, [winning_outcome], resolution_date, `**`last_checked`** |
| `scripts/fetch_market_resolutions.py:162` | only | `resolved, winning_outcome, resolution_date, `**`last_checked`** |
| `scripts/fix_expired_unresolved.py:93` | only | `resolved, winning_outcome, resolution_date` — **no `last_checked` either** (a second, independent occurrence of the same omission, in a fully non-canonical, one-off fix script) |

**The sweep's own driver scripts** (`data/characterizations/{sweep_segment1..4,
tranche1_execution,tranche2_execution}/*_write.py`) call `mark_market_resolved()`
exclusively — confirmed zero references to `last_checked`, `category`, `data_source`,
`end_date`, or `title` in any of the six files. They inherit exactly
`mark_market_resolved()`'s 6-column write, nothing more.

### 1.3 The difference [V]

Every column some non-canonical writer sets, in the same resolution-act statement,
that `mark_market_resolved()` does not:

| Gap column | Set by | Widespread? |
|---|---|---|
| **`last_checked`** | `database.py` (both writers), `backfill_o16_tier1/2.py`, `fast_resolution_check.py` (3 of 4 branches, self-patched onto the 4th), `resolve_legendary_markets.py`, `legendary_positions_scan.py`, `fetch_market_resolutions.py` — 7 of 9 distinct non-canonical writer files | **Yes** — the majority pattern |
| **`category`** | `database.py`'s `update_market()`, `hydrate_stub_markets.py` (both branches) | Narrow (2 files) but see §2 — its consumer reach is large |
| `data_source` | `backfill_o16_tier1.py`, `backfill_o16_tier2.py` only | Narrow, both writers legacy/likely-dormant (O-16 tier-1/2 completed per prior project record, not present in `daily_maintenance.py`'s `STEPS`) |
| `end_date` | `database.py`'s `update_market()`, `hydrate_stub_markets.py`'s proxy branch | Narrow, general market-metadata sync, not resolution-specific semantics |
| `title` | `database.py`'s `update_market()`, `hydrate_stub_markets.py`'s canonical-branch follow-up | Narrow |
| `condition_id` | `database.py`'s `update_market()` only (COALESCE-guarded) | Narrowest |

Two of these six (`last_checked`, `category`) get a full consumer trace in Part 2, per
the instruction to rank by consequence, not consumer count. `data_source`, `end_date`,
`title`, `condition_id` were checked for consumers and found to have no material,
resolution-gating consequence (see §2.3) — named and cleared, not chased further.

---

## PART 2 — Consumer trace, ranked by consequence

### 2.1 `last_checked` — BLOCKING (re-confirmed, quantified fresh)

**Consumer:** `scripts/requeue_resolved_market_traders.py:79-86` (daily,
`daily_maintenance.py` step 23, blocking). **What it does:** gates its entire
"markets resolved since last run" query on
`datetime(last_checked) > datetime(last_run)`; the resulting market set drives which
traders get `pnl_last_updated` reset to `NULL` (line 137-141), which is the sole
signal `background_pnl_worker.py` uses to prioritize reprocessing. **Consequence for
a canonically-written row:** the market is invisible to this query, permanently,
because nothing will ever touch its `last_checked` again after
`mark_market_resolved()` writes it once. Not delayed — permanent, unless
`last_checked` happens to be bumped for an unrelated reason (routine polling of a
still-active market). **Population, live today [V]:**

- 214,413 total clob-resolved markets; **195,625 (91.2%) stranded** (`last_checked` ≤
  the pre-sweep baseline, 2026-08-14).
- **8,077 open positions across 1,983 distinct traders** currently sit on
  last_checked-stranded, sweep-resolved markets (grown from the 4,991/594 figure in
  the prior verification doc, taken a few hours earlier the same day — this is a live,
  continuously-growing figure as the 15-minute monitor loop keeps writing new trades
  against already-stranded markets, not a one-time snapshot).
- Per-segment rate is consistent but not literally 100%: segment 3's own window
  (2026-08-24T17:15:37–2026-08-25T04:06:52) resolved 61,463 markets, of which 52,325
  (**85.1%**) are stranded — the ~9-15 point gap from the 91.2% aggregate is
  [I] incidental `last_checked` refreshes from unrelated routine polling of markets
  that happened to still be actively monitored, not any partial fix.

### 2.2 `category` — DEGRADING, larger population than `last_checked`, different mechanism [V]

**Consumers (file:line), all daily/weekly/scheduled and all filter
`m.category IN ('Geopolitics', 'Elections')`:**
- `scripts/audit_invariants.py:287,297,309-311` — the "pending on resolved non-gap
  geo/elections markets" REGRESSION check (daily, step 7).
- `scripts/geo_elo_derivation_audit.py:61,84` — geo_elo computation audit.
- `scripts/elo_formula_audit.py:54` — ELO formula audit population.
- `scripts/verify_dilution_guard.py:120,170,189` — dilution-guard population.
- `scripts/characterize_placebo_pending_exposure.py:62,75`,
  `characterize_orphan_sell_scope.py:76,97` — prior-session characterization scripts,
  not scheduled, but same predicate.
- (Also the core geo_elo/Pool-C machinery — `column_definitions.py`'s
  `geo_accuracy_pool`/`LEGENDARY` definitions are category-gated upstream of all of
  the above, per `daily_maintenance.py`'s "Update geo ELO scores" step.)

**What they do with it:** gate population membership — a market with
`category != 'Geopolitics'/'Elections'` is excluded from every one of these checks
and from the geo_elo pipeline's input population, full stop, no partial credit.

**Consequence for a canonically-written row:** `mark_market_resolved()` never
touches `category`, and neither does the sweep's own driver code. The only process
that fixes a `'Unknown'` category is `scripts/backfill_market_categories.py`
(daily, `--limit 50`, `WHERE category='Unknown' ORDER BY market_id`) — **not gated
by `last_checked` or evidence source, a genuinely separate mechanism from §2.1's
bug**, but running at 50 markets/day against a 214,155-market backlog. [I] At that
rate, clearing today's backlog alone (ignoring the ~10,700 new sweep-resolved
markets `daily_maintenance.py`'s own backfill/resolution steps add most days) would
take roughly 4,283 days (~11.7 years). This is a throughput failure, openly running,
not a silent gate — but the practical effect on every category-scoped consumer above
is identical to §2.1's: the row is invisible.

**Population, live today [V]:** 214,155 of 214,413 clob-resolved markets (**99.9%**)
sit at `category='Unknown'`; only 258 carry a real category (136 Elections, 122
Geopolitics). Overlap with §2.1's stranded set: 195,367 of 195,625 last-checked-
stranded markets are *also* category-stranded — near-total overlap, i.e. this is
functionally the same population hit by two independent gaps, not two disjoint
populations (contra the task's own caution that "the sets may not be the same" — in
this instance they very nearly are, checked directly, not assumed).

**What this cannot tell you:** how many of the 214,155 `'Unknown'`-category
sweep-resolved markets are *actually* Geopolitics/Elections markets miscategorized,
versus genuinely belong to other categories. Re-classifying 214,155 market titles is
a separate task, not attempted here — the honest statement is that the true
geo/elec-relevant sweep population is unknown and could be smaller or larger than
the 258 markets currently visible to any category-scoped consumer.

### 2.3 `data_source`, `end_date`, `title`, `condition_id` — checked, cleared [V]

- `data_source`: consumers found (`audit_invariants.py`'s
  `check_data_source_nulls`/`check_data_source_invalid`) operate across "4 core
  tables" generically; the specific `markets.data_source` writes come only from
  `backfill_o16_tier1/2.py`, both apparently dormant (O-16 tier-1/2 completed per
  prior project record, absent from `daily_maintenance.py`'s `STEPS`). This is very
  likely the source of the already-known, already-flat "577 data_source not in
  canonical set" REGRESSION from the prior verification — narrow, frozen, no new
  finding. **NOT A PROBLEM** (already accounted for).
- `end_date`, `title`, `condition_id`: no consumer found that gates behavior on
  these specifically for *resolved* rows — they're general market-metadata fields,
  read by display/UI-adjacent code and matching logic (`condition_id` for
  trade-market joins), not by anything that decides whether a resolution gets
  processed. **NOT A PROBLEM** for the resolution pipeline specifically; not
  re-verified for every possible non-resolution consumer (out of scope for this
  task).

---

## PART 3 — The backlog hypothesis: FAILS

**Prompt's hypothesis:** geo/elec pending-trade-result flatness (~23,000, prior
verification) is explained by the same requeue/`last_checked` gap — one root cause,
not two problems.

**Checked directly, live [V]:**

| `resolution_evidence_source` | pending geo/elec trades |
|---|---|
| (untagged — non-canonical writer) | **22,144 (95.4%)** |
| `clob` (sweep) | **1,069 (4.6%)** |

**Verdict: FAILS.** The overwhelming majority of the flat geo/elec backlog sits on
markets resolved by non-canonical writers — writers that (per §1.2/§2.1) correctly
set `last_checked` and therefore pass the requeue gate without issue. The
`last_checked` gap explains, at most, a small 4.6% slice of this specific number.
[I] The likely reason `evaluate_new_trader_results.py` (the script that actually
flips `trade_result`, independent of `requeue`/`last_checked` entirely — its own
`WHERE` clause needs only `resolved=1`, `winning_outcome` set, and `is_flagged=1`,
with no dependency on `last_checked`) hasn't drained these 22,144 trades is a
genuinely separate, unexplained problem — not chased further here, named for a
future investigation.

Per the task's own framing: this is the more serious outcome. There are now **two**
independent, unexplained gaps sitting in the pipeline — the column-diff bug this
task set out to characterize, and a pre-existing (older, non-sweep-caused) geo/elec
pending-trade problem this task found but did not solve.

---

## PART 4 — The stranded population

**4a. `last_checked` gap, confirmed live:** 195,625 of 214,413 clob-resolved markets
(91.2%) — see §2.1. (The prior verification's figure, 195,228/214,016, was measured
a few hours earlier the same day; both the total and stranded counts have grown
slightly since, consistent with the sweep-adjacent pipeline continuing to run.)

**4b. `category` gap, quantified separately, near-total overlap with 4a:**
214,155 of 214,413 (99.9%) — see §2.2. 195,367 of these are the *same* markets
counted in 4a; only 788 category-stranded markets are not also `last_checked`-
stranded (these presumably had `last_checked` incidentally refreshed but never got a
category backfill hit).

**4c. Traders and open positions affected, live [V]:**
- Via the `last_checked`/requeue gap specifically: **8,077 open positions, 1,983
  distinct traders**, growing.
- The `category` gap does not have a "traders/positions" figure in the same sense —
  its consequence is population-membership exclusion from category-scoped
  *aggregates and audits* (geo_elo, the geo/elec REGRESSION check, dilution guard),
  not a per-trader processing backlog. Stating a trader count for it would conflate
  two different kinds of harm; not done here.

**4d. What remediation would require — described, not implemented, not assessed as
safe:**

The obvious fix for §2.1 is adding `last_checked = ?` to `mark_market_resolved()`'s
`UPDATE` statement (one column, one function, matching what `fast_resolution_check.py`
already does manually). **The obvious follow-on — backfilling `last_checked = now()`
across the existing 195,625 stranded markets so `requeue_resolved_market_traders.py`
picks them up — should not be assumed safe, for two concrete, code-level reasons:**

1. **A likely hard failure, not just a slow one.** `requeue_resolved_market_traders.py`
   builds its `market_id IN (...)` and `trader_address IN (...)` queries with one `?`
   placeholder per row and no batching/chunking (`scripts/requeue_resolved_market_traders.py:78,
   115, 139-140`, read directly). A single-shot backfill would hand it a
   ~195,625-item `IN` clause. [I] Whether this errors outright depends on the
   linked SQLite build's `SQLITE_MAX_VARIABLE_NUMBER` (historically 999, raised to
   32,766 in SQLite ≥3.32.0) — not tested here, per the read-only scope, but the
   query as written has no defense against either outcome.
2. **Even if the query survives, it creates a burst load of the same class already
   found incompatible with this system.** All ~1,983+ affected traders would have
   `pnl_last_updated` reset to `NULL` in the same commit, making
   `background_pnl_worker.py` treat all of them as highest-priority simultaneously.
   The prior verification's own §4c already characterized this worker as
   continuously-running but rate-limited/API-bound per trader; a synchronous burst
   of ~2,000 traders needing reprocessing at once is the same *shape* of problem as
   the backup-vs-sweep contention already documented (`2026-08-26-backup-guard-and-
   scheduling.md`) — not evaluated for actual duration or collision risk here, named
   as a risk class, not a quantified one.

Any real remediation decision needs, at minimum: (a) the writer fix itself; (b)
a decision on whether the historical 195,625-market backfill is chunked/rate-limited
rather than run in one pass; (c) a decision on whether `category` gets backfilled
too, and by what mechanism, given `backfill_market_categories.py`'s current
50/day throughput cannot plausibly absorb 214,155 rows in any useful timeframe as
currently configured. None of that is proposed here — this is the read.

---

## PART 5 — Would the sweep keep stranding?

**Confirmed: yes, at essentially the same rate, if resumed unfixed.** [V] All six
sweep driver scripts (`segment1_write.py` through `segment4_write.py`,
`tranche1_write.py`, `tranche2_write.py`) call `mark_market_resolved()` exclusively
and contain zero references to `last_checked` or `category` anywhere in their source
— confirmed by direct grep across all six files, not inferred from one. Nothing
about segment 5 (not yet built) would differ unless its driver is written
differently from its five predecessors, which there is no evidence of — no segment 5
script exists yet (confirmed in the prior verification session).

**Per-segment rate, from actual data rather than assumption:** segment 3's own
61,463-market window stranded 52,325 (**85.1%**) on `last_checked` alone; the
aggregate across all sweep activity to date is 91.2%; `category` stranding is 99.9%
regardless of segment. **This is the strongest concrete argument in this task's
findings for why the sweep should stay paused**, independent of the three named
prerequisites from the prior end-to-end verification (segment 4's unwalked tail,
`max_batches`, and the exclusion-derivation re-keying) — a fourth, newly-established
one: **resuming today would strand ~85-91% of whatever segment 5 resolves, on top of
the ~195,625 already stranded, growing the remediation problem in lockstep with the
sweep's own progress rather than leaving it fixed-size.**

---

## WHAT REMAINS UNCHECKED (named, not chased — scope discipline)

- Why 22,144 non-sweep geo/elec pending trades are stuck (Part 3's residual finding)
  — a genuinely separate investigation, not attempted here.
- Whether the 214,155 `'Unknown'`-category clob-resolved markets contain a
  meaningful count of true Geopolitics/Elections markets — would require title
  reclassification at scale, not attempted.
- `SQLITE_MAX_VARIABLE_NUMBER` for this system's actual linked SQLite build — not
  tested, per read-only scope; §4d's placeholder-limit risk is code-level reasoning,
  not an observed failure.
- `database.py:862`'s `winning_outcome=None`-on-resolve defect (123 rows DB-wide) —
  named in §1.2, not traced to consumers; immaterial in scale next to the two gaps
  above.
- Whether `database.py`'s `update_market()` UPSERT is exercised on already-resolved
  rows in practice (which would test `trg_resolved_no_unresolve`'s defensive value
  directly) — not traced to call-site behavior at runtime, only read at the source
  level.

No fix, no plan — this is the read the fix will be built from.
