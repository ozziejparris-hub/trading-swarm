# Session Summary — 2026-08-20

## THEME

The session ran the canonical resolution write-path arc's Stages 1 and 2
to completion, then consolidated the arc's scattered open smells into a
register — and that register surfaced the most consequential finding of
the arc so far: a resolution-**discovery** gap sitting upstream of
everything the write-path work has spent three sessions securing. Both
migrations stopped before writing code and found something the design had
asserted and never checked; both resolutions were scope clarifications,
not function changes. The day closed by testing whether the discovery gap
reaches the project's own thesis result — it does, at the trader-population
level, though not (yet) at the level of the published number itself.

## THREE REUSABLE LESSONS (record them)

**The pre-flight earned its place twice in one day.** Both Stage 1 and
Stage 2 stopped before writing code, and both stops found something the
design had asserted and never checked — Stage 1's "maps cleanly onto
propose-defer" claim was false for the dominant branch; Stage 2's implicit
assumption that migrating a writer wouldn't change *what* it's allowed to
touch turned out to matter at 1,618-row scale. Neither would have
surfaced from reading the design; both came from checking it against real
candidate data. This pattern — resolve blocking questions empirically
before implementing a stage, not after — should carry forward to Stages
3–6 unchanged.

**Securing a write path does not secure the data.** Three sessions went
into making resolution writes canonical, correct, and enforced. The
register's own sizing exercise then found that the discovery step
upstream of those writes has a permanent blind spot affecting 203 of the
317 markets in the population this project actually depends on. Correct
plumbing on a pipe that is not receiving. Worth asking, on any future arc,
what feeds the thing being secured — not just whether the thing itself is
sound.

**"Bounded" is about knowing, not about size.** The discovery gap moved
from REAL-UNBOUNDED to REAL-BOUNDED by getting *larger* and
better-specified, not smaller — 203 exact, enumerated market_ids, not a
vague "some." The classification records that the number is now known and
actionable, not that the problem is minor. A future reader should not
infer "bounded" means "safe to deprioritize."

## WHAT WAS ACHIEVED

1. **Progress check, first day with Stage 0 live.** No committed artifact
   — figures recorded here directly. `trg_resolved_no_unresolve` never
   fired; `check_resolution_write_atomicity` reads 0, still Tier
   0/OBSERVE; 26 total invariants; all three new resolution columns intact
   with their CHECK constraint, zero non-null violations; no measurable
   effect on maintenance runtimes; the DB fingerprint increased across the
   board, as expected for a live system. Characterisation series carried
   forward: pending-resolution steady at **92** (zero churn against the
   persisted ID list — a different state than 08-19's non-monotonic
   88→103→92); no-FIFO-close **161 → 162** (+1). The check also corrected
   a method assumption of its own: `trades.timestamp` is execution time,
   not insertion time, so a timestamp gap in the trade tape cannot by
   itself indicate collector downtime — any future ingestion-stall
   detector needs to key on insertion order or rowid, not on this column.

2. **Stage 1 stopped first, then shipped — the split migration.** The
   pre-flight (`2026-08-20-stage1-hydrate-stub-migration.md`, `49f2f89`)
   found the design's claim that `hydrate_stub_markets.py`'s guard "maps
   cleanly onto propose-defer" was false for the dominant branch: **7 of 8
   real writes** in a full-population dry run are markets Gamma reports as
   NOT resolved, where the script fills `resolution_date` as a
   scheduled-end-date proxy — and `mark_market_resolved()` has no branch
   that writes `resolved=0`, structurally cannot express this. The
   resolution was a scope clarification, not a function change: the
   canonical path owns the resolution **assertion**, not the three
   columns; proxy end-date fills are a different operation, already
   excluded for `monitor.py`, now named as a category with an enumerated
   allowlist (design amendment, `a7bfe5e`) and §E's promotion condition
   rescoped from "zero direct writes" (unsatisfiable once proxy fills are
   acknowledged) to "zero direct writes outside the allowlist."
   Implemented as a split migration — assertion branch routed through
   `mark_market_resolved(evidence_source="hydration_fill")`, proxy branch
   untouched. Verification: full-population before/after dry-run diff
   byte-identical, pre-migration behavior extracted from git rather than
   transcribed; the one assertion row correctly tagged
   (`hydration_fill`, `resolution_recorded_at` set) — **the first
   production write ever through `mark_market_resolved()`**; all 7 proxy
   rows confirmed NULL in the new columns, confirming the split did not
   leak. Honest scale, stated plainly in the record: **one row**.
   (`2026-08-20-stage1-implementation.md`, `0f9ade8`; code, first-repo
   `aa797f3`)

3. **Stage 2 stopped first, then shipped — behaviour-preserving
   migration and a policy for the whole arc.** The pre-flight
   (`2026-08-20-stage2-stop.md`, `d2fe369`) cleared two of four blocking
   questions: this writer never holds a true Gamma event-time, so the
   COALESCE patch and the canonical three-tier fallback are behaviourally
   **identical**, not merely equivalent (Q1); and it is a pure assertion
   writer with no proxy branch (Q4). The other two diverged: **1,618 of
   2,100** Gamma-fetched resolved markets are already `resolved=1` with a
   NULL evidence source, and a literal migration would fire 1,618 writes
   on the first unattended nightly run — value-safe (every one carries the
   same `winning_outcome` Gamma reports now) but new and large,
   unsupervised. Reported rather than resolved by picking a behaviour, per
   instruction. Oscar's decision, recorded once as **§A4 policy for every
   future stage, not re-derived per writer**: migration is
   behaviour-preserving (existing skip guards stay); legacy provenance
   backfill is a separate, pre-registered task, not bundled into a nightly
   step; and a fifth evidence source, `backfill_verified`, will mark
   reconciled-legacy rows distinctly from writer-asserted ones once that
   task exists — ranked at a new Rank 3, **below** `gamma`, reasoned out
   explicitly so a genuine canonical write can always improve on a
   backfill tag rather than being gated by the same-rank tie policy.
   Implemented behaviour-preserving: the `if is_resolved: continue` guard
   stays ahead of the canonical call. Verification: dry-run diff
   byte-identical; the decisive check — `evidence_source='gamma'` count
   went **0 → 9, not 1,617** — confirming the guard held and no legacy
   backfill leaked. Honest scale: **9 rows**, all on the trivial
   accept-on-unresolved branch. **Across Stages 1 and 2 combined, ten
   production rows have gone through the canonical path, and the ranking
   comparator (same-rank match, same-rank disagreement, cross-rank
   overwrite, untagged-legacy improvement) remains entirely unexercised
   outside unit tests.**
   (design amendment §A4, `070b795`; `2026-08-20-stage2-implementation.md`,
   `be829d0`; code, first-repo `dad2d11`)

4. **Open smells register — eight items surfaced across the arc and
   never followed up, investigated to classification, not resolution.**
   **BENIGN:** the step-7-vs-step-21 ordering defect (mechanically
   possible, zero occurrences across 66 logged runs, and it alerts — Tier
   2 REGRESSION — rather than silently passing in 33 of 40 observed
   instances); `fix_expired_unresolved.py`'s SQL interpolation (dormant,
   hardcoded values only across 12 markets not the cited 10, already run,
   effects verified persisted correctly). **REAL-BOUNDED:** hydrate's
   8-in-1,258 hit rate — two concrete code defects, not delisting as the
   design doc had guessed: 1,214 of 1,250 misses have NULL `api_id` **and**
   `condition_id`, falling through to a Gamma endpoint expecting an
   integer; the other 36 fetch successfully but the date extraction checks
   the wrong field names (Gamma uses `closedTime` for closed markets, the
   script checks `endDate`/`endDateIso`/`end_date_iso`/`resolutionTime`)
   — ~99% of candidates structurally unfindable, a pure opportunity-cost
   defect; position construction (`background_pnl_worker.py`'s `ON
   CONFLICT` clause omits `is_synthetic_close`, so a position closed on a
   later run keeps a stale flag); P&L aggregates (2 of 5 implementations
   live, both agree with each other); `elo_last_updated` (22,558 T-separated
   rows today, ~1,113 years to converge by incidental rewrite alone — a
   practical asymptote, not a slow trend); Writer D (code present in
   `elo_bridge.py`, zero live call paths, requires a deliberate manual
   invocation to fire). Item 9 surfaced ten further incidental findings,
   including five live (non-archived) docs still describing Writer D's
   `quick_elo_update_for_traders()` as the current monitoring-cycle ELO
   path.
   (`2026-08-20-open-smells-register.md`, `f4418cb`)

5. **The discovery gap — the session's headline, method pre-registered
   before any sampling.** Item 1's deep dive found Gamma's `/markets`
   sorts by `endDate`, which is a **placeholder** for many markets (79 of
   the first 100 rows share one value; rows sharing an identical `endDate`
   have real `closedTime` values two months apart), and paginates hard at
   `offset=2000` with HTTP 422 explicitly naming `/markets/keyset` as the
   escape hatch — which exists, works (confirmed live), and this writer
   does not use. So a resolved market can sit **permanently** outside the
   reachable window rather than ageing out of it. The three CLOB-based
   passes in the same file don't share that specific blind spot but
   require `resolution_date` or `end_date` to become a candidate at all,
   and **510,378 of 513,179 unresolved markets (99.5%) have neither** —
   the safety net can reach roughly 0.1–0.3% of the population that would
   need it. Sizing, method locked and committed (`a9a0cf9`) before a
   single CLOB call: **Q2, a full census** (not a sample) of the 317
   markets in the project's own canonical-relevance population
   (Geopolitics/Elections, with trades, gap-flag clean) — **203 confirmed
   already resolved on CLOB and undiscovered**, 98 open, 16 indeterminate.
   **Q1**, a stratified sample across all 510,378: **99.3% resolved**, 95%
   CI [97.9%, 100%]. Cross-check: 15 of 15 corroborate — `tape_end` 85–555
   days before today, trading long since stopped, zero discrepancies.
   Boundary check: **not** an artifact of age (both the oldest and newest
   of three tape-start terciles show the pattern across a 3.5-year range)
   and **not** one ingestion batch — `live_monitoring` shows a **higher**
   rate than `historical_backfill` (71.3% vs 59.1%), meaning this is
   actively growing, not a historical residue winding down. The barrier
   is not missing identifiers: 97% of `market_id` values are themselves
   `condition_id`-shaped and CLOB answered them cleanly. It is that **no
   script queries these markets this way** — a coverage-of-code problem,
   not a data-availability one. Reclassified **REAL-UNBOUNDED →
   REAL-BOUNDED** by the pre-registered materiality rule (203 ≥ 16).
   Bounded means known extent, not small.
   (`2026-08-20-discovery-gap-sizing-prereg.md`, `a9a0cf9`;
   `2026-08-20-discovery-gap-sizing-result.md`, `ff40b79`; script and raw
   census, first-repo `171a4d9`)

6. **Thesis intersection — verdict TOUCHING, not the simple thinning
   story.** The published `+0.0316` cohort / `+0.0127` placebo figures are
   structurally unaffected **today**, verified by direct count, not
   inference: of 2,194 positions where cohort/OOS-survivor/placebo traders
   hold stakes in these 203 markets, **zero** have `trade_result` other
   than `pending` — and every query that produced the headline figures
   filters to `won`/`lost`, so this exposure was invisible to the
   computation by construction. But the trader populations behind those
   numbers are substantially exposed: **71.4% of OOS-surviving cohort
   traders** and **60.2% of OOS-surviving placebo traders** hold real,
   dormant positions in these markets (637 and 424 positions
   respectively). **Direction, computable here** — unlike every prior
   position-exposure finding in this arc, CLOB reports a winner for all
   203: the affected cohort positions' own mean edge is **~0.0006**,
   essentially flat against the published +0.0316; the affected placebo
   positions' mean edge is **~0.0114**, close to the placebo's own
   +0.0127. Folding this exposure into a corrected measurement would
   **narrow** the cohort–placebo gap, not widen it — reported as the
   affected positions' own edge distribution, not a recomputed headline,
   per instruction. Qualification boundary: 164 of the 203 markets could
   have affected who qualified for the pre-split cohort; **46 traders are
   upper-bound candidates** to newly cross `M≥10` if these were resolved,
   one going from zero current presence to 26 markets — flagged explicitly
   as an upper bound, not a confirmed recount, with the settling method
   named. Fully disjoint from the known 92-market pending-resolution and
   162-market no-FIFO-close populations — no double-counting.
   (`2026-08-20-discovery-gap-thesis-intersection.md`, `cd32c10`; script
   and raw output, first-repo `8898ec4`)

## STATE FOR NEXT SESSION

The order below is **proposed, not decided.** Oscar has flagged the
discovery gap as the thing to tackle deeply tomorrow.

**THE DISCOVERY GAP (tomorrow's focus):**

a. **It is growing** — `live_monitoring` at 71.3% means new markets enter
   this state continuously, not just legacy ones. Any fix should stop the
   bleeding before backfilling the 203 already found.
b. **Two candidate fix shapes, neither implemented, neither assessed
   against each other yet:** `/markets/keyset` pagination (Gamma's own
   escape hatch, but still walks the same bad sort key — would convert
   "permanently unreachable" into "reachable but possibly very deep," not
   a full fix on its own); or a CLOB pass keyed on
   `market_id`-as-`condition_id` (which the sizing exercise proved works
   — 527 calls, low indeterminate rate, no new infrastructure). The
   second looks structurally stronger but should be assessed properly,
   not assumed from this session's read.
c. **Fixing hydrate's two defects (register item 2) directly shrinks the
   dateless population that compounds this gap.** Cheap, fully diagnosed,
   no further investigation needed before implementing.
d. **Any fix needs its own pre-registration.** Resolving any of the 203
   changes the canonical backtest population, which changes the thesis
   result's own inputs — a deliberate, observed operation, not something
   to fold into a nightly step.
e. **The qualification-boundary upper bound (46 traders, one gaining 26
   markets) needs settling by the method the intersection doc names** —
   inject synthetic `won`/`lost` labels using the already-known CLOB
   winners and re-run the real pairing/significance/effect-bar chain. It
   is currently an upper bound, not a recount.

**THE CANONICAL ARC (paused mid-sequence, not abandoned):**

f. **Stage 3** (`#4/#5/#6`, the three CLOB sibling passes) — the first
   cross-rank exercise (Rank-1 CLOB vs. already-migrated Rank-2 writers)
   and the first real test of the ranking comparator at all, since Stages
   1–2 only ever hit the trivial accept-on-unresolved branch. Same
   pre-flight discipline applies.
g. **Stages 4–6 per the design.** Stage 5 adds `trg_require_recorded_at`;
   Stage 6 promotes the invariant against the rescoped assertion-only
   condition.
h. **The legacy provenance backfill (§A4 policy 2) and its
   `backfill_verified` schema/CHECK-constraint change** — a separate,
   pre-registered task, not bundled into any migration stage.
i. **The CI lint rule from §F** — buildable at any point after Stage 0,
   no dependency on writer-migration order.

**FROM THE REGISTER, RANKED BY THE REGISTER ITSELF:**

j. Item 2 (hydrate's two defects) — cheap, diagnosed, directly shrinks
   item 1's population (see (c) above).
k. Item 5's `is_synthetic_close` omission — one column in one `ON
   CONFLICT` clause, concrete downstream consequence (stale flag on
   later-synthetically-closed positions).
l. Items 6, 7, 8 — low urgency, no live trigger paths; safe to leave
   until convenient.

**CARRIED, UNCHANGED:**

m. `check_pending_geo` still has no daily evaluator wired into
   `daily_maintenance.py`.
n. `apply_synthetic_closes` as a third win/loss implementation, still
   missing the `invalid`-state guard the two trade-level evaluators both
   have.
o. Ingestion-stall detection and the 500-trade recovery-window threshold
   — carried from 08-18/08-19, still untouched — and note today's
   correction: any such detector must key on insertion order or rowid,
   not `trades.timestamp`, which is execution time.
p. **Carried from 08-15, unchanged:** the cutover decision; the
   category-split cost floor; the consensus question; the
   `comprehensive_elo` sign error; elections calibration re-run (O-40);
   O-38; O-18. Track 2 CI power diagnostic still uncommitted; its A3 stop
   condition still needs amending.

## BIG PICTURE

The thesis result (`+0.0316`, CI `[-0.0088, +0.0710]`, NULL, underpowered)
is unchanged and, as of today, structurally unaffected by everything
found — but for the first time in this arc there is a finding with a
**computable direction, and it is unfavourable**: the positions this gap
hides carry a near-flat mean edge for the cohort and a placebo-like edge
for the placebo, so a corrected measurement would narrow the gap the
thesis currently rests on. That is not a result — it is an exposure, and
settling it is next session's work.

The canonical write path is three stages in (0, 1, 2) and sound: two
migrations shipped, both behind a pre-flight that caught a real design gap
each time, both verified against production with a byte-identical
before/after diff and a decisive tag-count check. Ten rows total have
gone through `mark_market_resolved()`, all on the trivial branch — the
comparator's harder logic remains untested in production. The discovery
step feeding that write path is not sound: a permanent, growing,
now-precisely-sized blind spot sits upstream of it, and no amount of
correctness in the write path compensates for markets it never sees.

**Plain statement, accurate about what actually shipped, not to be
inflated in a future read of this file:** two migrations went into
production this session (Stage 1's split migration, one row; Stage 2's
behaviour-preserving migration, nine rows) — both preceded by a stop that
found a real gap in the design, both resolved by a scope clarification
recorded in a design amendment, neither by a code change to
`mark_market_resolved()` itself, which remains unmodified since Stage 0.
Everything else this session — the progress check, the open-smells
register, the discovery-gap pre-registration and sizing, and the thesis
intersection test — was characterisation and measurement, not repair.
**Nothing was fixed in the discovery path itself; nothing was resolved;
no market's `resolved` flag was flipped outside the 10 canonical-path
rows named above.** The 203-market finding is a sized, cross-checked,
directionally-informative exposure, not yet an action.

Write it as a record for a future instance with no memory of today.
