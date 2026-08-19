# 2026-08-19 — three open questions gating Stage 0 of the canonical resolution write design

Read-only against production throughout. Nothing implemented, no columns
added to production, no triggers created on production, no writer
modified. Every claim tagged **[V]** (verified — command/output given) or
**[I]** (inferred, explicitly marked). Two live API calls made total
(Q1), reusing market IDs already established in prior sessions rather
than sampling fresh ones; everything else is local DB queries or a
throwaway scratch SQLite file (Q3), deleted after use.

---

## Q1 — Does CLOB expose a resolution event-time?

**[V] No. Established via exactly 2 live calls, cross-validated, not 1
call generalized.**

**Method:** rather than a fresh sample, made one live call to
`https://clob.polymarket.com/markets/{condition_id}` for
`0xbd0c2d5f...` (api_id 906980) — a market already confirmed resolved
in the prior clobber-fix session's dry-run — and dumped the **entire**
raw JSON response, not just the fields the existing code currently reads.

**Every top-level field present:**
```
accepting_order_timestamp, accepting_orders, active, archived, closed,
condition_id, description, enable_order_book, end_date_iso, fpmm,
game_start_time, icon, image, is_50_50_outcome, maker_base_fee,
market_slug, minimum_order_size, minimum_tick_size, neg_risk,
neg_risk_market_id, neg_risk_request_id, notifications_enabled, question,
question_id, rewards, seconds_delay, tags, taker_base_fee, tokens
```

**No field named or shaped like a resolution/settlement timestamp
exists.** The only two timestamp-shaped candidates:

- **`end_date_iso`** — `"2026-06-02T00:00:00Z"` for this market. This is
  the **scheduled** end date — already known, already used elsewhere in
  the cluster (writer #1's fallback, monitor.py's proxy writes) as the
  Rank-2 proxy. Not a resolution fact.
- **`accepting_order_timestamp`** — `"2025-12-11T04:54:55Z"` for this
  market. The only genuinely *new* candidate. **Sanity-checked against
  tape_end, per the task's own instruction:** this market's last trade in
  the local DB is `2026-07-28 13:35:55` — **more than 7 months after**
  `accepting_order_timestamp`. A true resolution timestamp cannot precede
  the last trade by 7 months while trading continued in between — this
  conclusively rules it out as a resolution event marker. **[I]** Most
  plausibly reflects when this market record was created/onboarded in
  CLOB's system (the date is suspiciously close to the
  `historical_backfill` import date referenced elsewhere in this project,
  `2025-12-11` — `backfill_o16_tier1.py`'s own docstring names this exact
  date), not a per-market lifecycle event at all.

**Cross-validated on a second, independently-selected market**
(`0x08e4cea3c55ded3bb7...`, api_id 826115) to confirm this wasn't an
artifact of one market: `accepting_order_timestamp = "2025-12-05T15:20:51Z"`,
tape_end `2026-07-01 23:16:29` — same shape, `accepting_order_timestamp`
again clustered near the same historical-import date, again months before
the actual last trade. Two calls, two markets, same conclusion — treated
as sufficient without a larger sample, since the field's value pattern
(clustered on an unrelated system-migration date, not per-market) is
itself the disqualifying evidence, not a borderline timing call that
would benefit from more samples.

**Incidental finding, worth naming though not the core question:** this
second market's CLOB response showed `closed: False`,
`tokens[].winner: false` for both outcomes, **despite one token pricing
at 0.9995** — meaning Gamma-style price-threshold inference (Rank 2) can
produce a "winner" determination *before* CLOB's own `closed`/`winner`
flags (Rank 1) update. This doesn't affect the ranking's basis (CLOB is
still the more authoritative *type* of evidence when it does declare a
winner — direct vs. inferred) but is a real timing wrinkle for whoever
implements the ranking comparator: a Rank-1 source can be *slower to
populate* than a Rank-2 source for the same market, not just structurally
absent for older markets.

### Implication for the design — revision needed before Stage 0

**A2's "Rank 1 — but currently unpopulated" row should be deleted, not
left as an open question for Stage 3.** The design as written treated
this as something to check "if the CLOB API exposes one" during
migration Stage 3. It's now established there is nothing to extract —
CLOB contributes **zero** event-time evidence at any rank. The corrected
A2 ranking collapses to:

- **Rank 1 (only real event-time source, from either API):** Gamma's
  `closedTime` / `umaEndDate` / `endDate` — unchanged from the design as
  written, since this was never CLOB's contribution anyway.
  `accepting_order_timestamp` is **not** added as a candidate at any rank
  — it's disqualified, not merely deprioritized.
- **Rank 2:** `end_date` proxy — unchanged.
- CLOB remains Rank 1 for **who won** (A1) — unaffected by this finding.
  The two rankings (A1 for the fact, A2 for the timestamp) were already
  separate axes in the design; this finding sharpens that separation
  rather than undermining it: **the highest-authority source for the fact
  and the highest-authority source for the timestamp are not the same
  source**, and the design should say so explicitly rather than imply
  Stage 3 might unify them.
- **Migration Stage 3's task** ("extract a true event-time from CLOB if
  the API supports it") is now answered — remove that conditional
  language, replace with: Stage 3's CLOB migration supplies
  `evidence_source="clob"` for the *fact* only; `resolution_event_time`
  passed to `mark_market_resolved()` from these writers will be `None`
  unless a Gamma cross-reference is also performed in the same call
  (out of this task's scope to design further).

**Schema (D) is unaffected** — the column split itself doesn't depend on
which API supplies the event-time, only on separating it from write-time
at all. No revision needed there.

---

## Q2 — How much data does `store_market_dict` (#1b) discard?

### a. Is a winner extractable from data it already holds?

**[V] Yes, structurally.** `store_market_dict` receives `market: Dict`
from `get_markets()` — the same Gamma bulk `/markets` list endpoint shape
`fast_resolution_check.py`'s `extract_winner()` already parses elsewhere
in this codebase (`outcomes` / `outcomePrices` fields, JSON-string-or-list).
`store_market_dict` reads `market.get('closed')` / `market.get('archived')`
from this exact object to set `resolved`, but never reads `outcomes`/`outcomePrices`
from the same object to set `winning_outcome` — it hardcodes `None`
unconditionally. The data is present in the object already in memory;
it's simply not read. **Confirmed a genuine discard, not an
unavailable-data limitation.**

### b. Volume — invocation frequency, and the limit of what's countable

**[V] Invocation frequency:** `scan_for_successful_traders()` (the only
caller of `store_market_dict`, via `analyze_and_flag_traders`) runs from
two sites in `monitor.py`: once at `initial_scan()` (process startup
only) and periodically inside the main loop, gated
`if cycle_count % 10 == 0`. At the documented 15-minute cycle interval,
this is **roughly every 2.5 hours, ~9–10 times/day**, scanning across 6
hardcoded categories (`Geopolitics`, `Global Politics`, `Ukraine & Russia`,
`Elections`, `Economics`, `Unknown`) each time.

**[V] Row-count attribution is NOT determinable from current data.**
Checked: `update_market`'s `INSERT` (called by both `store_market_from_trade`
(#1a) and `store_market_dict` (#1b)) does not set a distinguishing
`data_source` — both rely on the column's schema default,
`'live_monitoring'`. There is no column, tag, or other marker
distinguishing which of the two call sites created a given row.
**Stated as a genuine limit of what this investigation can answer, not
glossed over with an estimate.**

### c. How many were later corrected by a different writer — the actual cost

**[V] Directly measurable via the one population this discard would
produce: `resolved=1 AND winning_outcome IS NULL`.**

```sql
SELECT data_source, COUNT(*) FROM markets
WHERE resolved = 1 AND (winning_outcome IS NULL OR winning_outcome = '')
GROUP BY data_source;
-- gamma_backfill_tier2_2026-07-06 | 123
```

**All 123 currently-observable rows in this state are tagged from one
already-known, unrelated one-off backfill (`backfill_o16_tier2.py`'s
no-winner sentinel, per `2026-08-19-market-resolution-write-cluster.md`
Q4). Zero rows carry `data_source='live_monitoring'` in this state —
i.e., zero currently-observable instances are attributable to
`store_market_dict`.**

**[I] Most plausible explanation, not confirmed by direct trace (no audit
trail exists to trace it — this is inference, stated as such):** two
independent, non-exclusive mechanisms likely explain the zero count:
1. `store_market_from_trade` (#1a) — driven continuously by trade-tape
   activity, effectively real-time — almost always creates a market's
   stub row (with `resolved=False`, no discard possible) **before**
   `store_market_dict`'s ~2.5-hourly category scan ever reaches it, since
   this system's core function is trade-tape monitoring; a market this
   system cares about has usually already been traded on by the time a
   periodic category scan would independently discover it.
2. Even in the narrower case `store_market_dict` *does* win the race and
   creates a `resolved=1, winning_outcome=NULL` row: `hydrate_stub_markets.py`
   (already scheduled daily, post-test-suite step) independently guards
   `winning_outcome = CASE WHEN winning_outcome IS NULL AND ? IS NOT NULL
   THEN ? ELSE winning_outcome END`, candidate-gated on
   `resolution_date IS NULL` — not on `resolved` status — so it would
   plausibly self-heal exactly this shape of row before it's ever
   observed at audit time, **without needing to be aware #1b's gap
   exists.**

### d. High-volume enough to reprioritize, or a genuine footnote?

**A genuine footnote — stated with the evidence, not just asserted.** The
theoretical discard is real (a) and the invocation frequency is not
trivial (b, ~9–10x/day), but the actual observable cost (c) is **zero**
in the live database today, and the most plausible mechanism is
structural (trade-tape discovery usually wins the race) rather than
lucky. **This does not mean the code path should be left as-is
indefinitely** — it's still a latent gap that could manifest under
different traffic patterns (e.g., a category scan running before any
trade-tape activity for a newly-added category) — but it does not rise
to the level of reprioritizing ahead of the design's other open items.
**Confirms the design doc's own framing (H) was directionally correct**
— named as a migration-time side-benefit, not a live defect requiring
urgent attention — with the added, now-verified nuance that it appears to
already be self-healed in practice, not merely theoretically low-risk.

### Implication for the design

**No revision needed to Stage 0's schema or scope.** #1b remains, as the
design already stated, an optional follow-on improvement at whatever
point #1b is touched (not scheduled in the 7-stage migration sequence,
and this finding doesn't argue for adding it).

---

## Q3 — Is a narrow DB trigger feasible?

**[V] Built and tested both triggers in an isolated scratch SQLite file
(`/home/parison/.claude/jobs/9ffb0909/tmp/trigger_scratch*.db`, deleted
after use) — never touched production. Schema replicated exactly from
`sqlite3 .schema markets` (read-only) plus the 3 hypothetical Stage-0
columns.**

```sql
CREATE TRIGGER trg_resolved_no_unresolve
BEFORE UPDATE OF resolved ON markets
WHEN OLD.resolved = 1 AND NEW.resolved = 0
BEGIN SELECT RAISE(ABORT, 'resolved cannot transition from 1 to 0'); END;

CREATE TRIGGER trg_require_recorded_at
BEFORE UPDATE OF resolved, winning_outcome, resolution_date ON markets
WHEN (
    (NEW.resolved IS NOT OLD.resolved)
    OR (NEW.winning_outcome IS NOT OLD.winning_outcome)
    OR (NEW.resolution_date IS NOT OLD.resolution_date)
)
AND NEW.resolution_recorded_at IS OLD.resolution_recorded_at
BEGIN SELECT RAISE(ABORT, 'writes to resolved/winning_outcome/resolution_date must also set resolution_recorded_at'); END;
```

### a. Can SQLite express both? Yes, confirmed by running them.

Both are plain `BEFORE UPDATE ... WHEN ... RAISE(ABORT, ...)` triggers —
no extensions, no recursive-trigger concerns, no deferred-constraint
machinery needed.

### b. What happens to legitimate writes — tested against real shapes, isolated per trigger

| Test | Shape | Result |
|---|---|---|
| A pre-migration writer's exact current UPDATE (sets `resolved`/`winning_outcome`/`resolution_date`, does **not** set `resolution_recorded_at` — this column doesn't exist in any of the 13 writers' code today) | `fast_resolution_check.py`-shaped | **BLOCKED** by `trg_require_recorded_at` |
| `hydrate_stub_markets.py`-shaped write (only touches `category`/`title`, not resolution columns) | fill-only-if-empty, unrelated columns | **SUCCEEDED** — neither trigger fires |
| Re-assigning `resolved=1` to an already-`resolved=1` row (a no-op re-write some writers perform) | | **SUCCEEDED** |
| `resolved` 1→0, isolated so only trigger 1's condition is in play (test also sets `resolution_recorded_at` so trigger 2 doesn't confound the result) | the actual attack trigger 1 exists for | **BLOCKED** by `trg_resolved_no_unresolve`, confirmed in isolation |
| `resolved` 0→1 (the legitimate direction) | | **SUCCEEDED** |
| A canonical-path-shaped write (sets `resolution_recorded_at` + `resolution_evidence_source` together) | post-migration shape | **SUCCEEDED** |

**Direct answer to "does the second trigger break any of the 13 writers
pre-migration":** **Yes, unconditionally — confirmed empirically, not
assumed.** Every one of the 13 writers' current UPDATE statements would
be rejected by `trg_require_recorded_at` today, because none of them set
a column that doesn't exist yet. **This trigger can only be added at
Stage 5 or later**, after every writer is migrated to call
`mark_market_resolved()` (which always sets `resolution_recorded_at`) —
exactly the constraint the task's own framing anticipated, now confirmed
rather than assumed.

**`trg_resolved_no_unresolve` breaks nothing** — none of the 13 writers'
candidate-selection or write logic ever attempts to set `resolved=0` on
an already-`resolved=1` row (every establishing writer's candidate query
requires `resolved=0` to begin with). **Viable at Stage 0**, before any
writer migration.

### c. Performance — measured, not assumed, at production scale

Seeded **733,000** synthetic rows (matching the live `markets` row count
measured earlier this session) in the scratch DB.

- **Loop of 500 individual single-row UPDATEs** (matching
  `fast_resolution_check.py`'s per-market write pattern): 8.0ms with
  triggers vs. 15.4ms without, in this run — **negative/negligible
  measured overhead**, within noise at this scale; not claimed as proof
  triggers make writes faster, just that the cost is unmeasurably small
  relative to run-to-run variance at 500 rows.
- **Single-statement bulk UPDATE, 5,000 rows via `WHERE market_id IN
  (...)`** (representative of a larger batch operation): **7.2ms with
  triggers vs. 5.7ms without — 1.5ms absolute overhead, ~27% relative.**
  In absolute terms, 1.5ms for 5,000 rows is inconsequential next to any
  of the 13 writers' actual bottleneck (network-bound API calls taking
  hundreds of milliseconds to seconds per market, not the local SQLite
  write). **Not a performance concern at any stage.**

### d. Interaction with WAL, backup, batch commits, `INSERT OR REPLACE`

- **WAL mode:** every test above ran under `PRAGMA journal_mode=WAL`
  throughout (matching production) — no observed interaction issue;
  triggers execute identically regardless of journal mode, since they
  operate at the SQL statement-execution layer, not the storage layer.
- **Batch commits:** the 500-row loop test committed once at the end
  (matching the writers' own batch-commit pattern) with triggers firing
  per-statement inside the transaction — no issue.
- **Backup discipline:** **[I]**, not separately empirically tested this
  session — `scripts/backup_database.py` uses SQLite's online backup API
  (`Connection.backup()`), which is a page-level copy of the entire
  database file including schema objects (tables, indexes, triggers)
  identically. This is standard, well-established SQLite behavior, not
  something specific to this design — stated with lower confidence than
  the empirically-tested items above, but not flagged as a risk.
- **`INSERT OR REPLACE` — tested, and this is the one real finding under
  (d):** **`INSERT OR REPLACE` completely bypasses both `BEFORE UPDATE`
  triggers.** SQLite implements `INSERT OR REPLACE` as an atomic
  delete-then-insert, not an update — neither trigger fires, confirmed by
  directly testing `INSERT OR REPLACE INTO markets (market_id, resolved)
  VALUES ('m1', 0)` against a row that was `resolved=1`: the value
  silently became `0` with **no trigger firing at all**. **Checked
  against the 13 writers: none currently use `INSERT OR REPLACE` on
  `markets`** (creation paths use `INSERT OR IGNORE`; resolution paths use
  plain `UPDATE`) — **not a live risk today**, but a genuine, permanent
  blind spot for any future writer that does use this pattern. Named
  explicitly rather than discovered later.

### e. Recommendation

**Viable as a defense-in-depth backstop — for `trg_resolved_no_unresolve`
specifically, add it at Stage 0, immediately, before any writer
migration.** It costs nothing (no legitimate writer relies on unresolving
a market), blocks a real class of mistake outright, and doesn't wait on
anything else in the design.

**`trg_require_recorded_at` is the more valuable trigger — it is the
direct, structural answer to the exact gap the design's own E section
admitted (`"case (a)... a writer that ignores both new columns
entirely"`)**: a rogue or forgotten writer that never learned about the
new columns will have its statement **aborted outright**, not merely
detected after the fact at the next audit cycle. **Add it at Stage 5**,
the same point the migration sequence already requires for the invariant
promotion condition — bundling them makes sense, since both are gated on
the same fact (all 13 writers migrated) and both exist to catch the same
failure mode from complementary angles (trigger: prevent at write time;
invariant: detect anything that slips past, including the
`INSERT OR REPLACE` blind spot the trigger itself can't cover).

### Implication for the design

**Revises G (migration sequence) and F/E (enforcement), not Stage 0's
schema.** Two additions:
- **Stage 0** should include creating `trg_resolved_no_unresolve`
  alongside the schema columns — it has no dependency on the canonical
  function or any writer migration.
- **Stage 5** should include creating `trg_require_recorded_at`
  immediately before (or together with) the Stage 6 invariant promotion
  — it directly closes the invariant's own admitted case-(a) gap for
  everything except the `INSERT OR REPLACE` blind spot, which should be
  named in F's write-up as a residual limitation of the trigger approach,
  not silently left for someone to discover later.

---

## Summary — what changes before Stage 0 is built

| Question | Finding | Design revision needed |
|---|---|---|
| Q1 | CLOB exposes no resolution event-time field, at all, on any market checked | **Yes** — A2's "Rank 1, currently unpopulated" row is deleted, not deferred to Stage 3; Stage 3's task description simplified accordingly |
| Q2 | #1b's discard is real in code but has produced zero observable instances; plausibly self-healing via existing daily writers | **No** — design's existing footnote framing (H) confirmed correct, no schema or scope change |
| Q3 | Both triggers work as specified; the second breaks all 13 writers pre-migration (confirmed, not assumed); negligible performance cost; `INSERT OR REPLACE` is a permanent blind spot, currently unused | **Yes** — add `trg_resolved_no_unresolve` to Stage 0, add `trg_require_recorded_at` to Stage 5, document the `INSERT OR REPLACE` gap in F |

---

*Generated 2026-08-19. Sources: `2026-08-19-canonical-resolution-write-design.md`
(`7248be7`), `2026-08-19-market-resolution-write-cluster.md` (`85965c5`),
live CLOB API calls (2, both re-using previously-established market IDs),
`monitoring/database.py`, `monitoring/monitor.py`,
`monitoring/trader_analyzer.py`, live production DB queries (read-only),
and a throwaway scratch-SQLite trigger test (never touched production,
deleted after use). No columns added to production, no triggers created
on production, no writer modified.*
