# Session Summary — 2026-08-19

## THEME

The session opened on a to-do list — amend the handover, then wire the
geo-backfill script into maintenance — and became a structural arc. The
morning progress check surfaced an invariant regression that didn't resolve
itself; following it produced a write-path census, the market-resolution
write cluster, and the first canonical infrastructure this project has
shipped. Oscar's steer mid-session — prioritise simplicity, coherence, and
grouping things so they function in harmony; understand what everything
does before writing on top of it — is what redirected the work from fixing
individual instances to mapping the population they belonged to and
consolidating from there. Two code fixes and one piece of shipped
infrastructure came out of a session that started as documentation
maintenance.

## THREE REUSABLE LESSONS (record them)

**A map changes what "what next" means.** Four sessions were spent chasing
single instances of one recurring defect shape — an implementation exists,
a canonical version exists, nothing enforces the relationship. The
write-path census produced the population those instances were samples
from, and turned prioritisation from a judgement call into something
readable off a table. The corollary worth stating plainly: the reason
there was so much to find is that nobody had looked. "The list is done" is
not evidence the system is healthy.

**Fix the canonical thing, not the caller.** The trade-evaluator repoint
found the non-canonical copy was *more* defensive than canonical in two of
three divergences. Hardening `TradeEvaluator` itself made all three of its
callers better in one move; wrapping the fix around it inside the one
caller being repointed would have created a fourth variant wearing the
language of consolidation.

**Map before consolidating.** Nine-plus writers on market resolution
looked like a defect surface by count alone. The cluster analysis found
first-writer-wins already protecting most of it by accident, and exactly
one demonstrated live clobber. Consolidating blind, from the count alone,
would have restructured against a threat that was mostly not there, with
all the behaviour-change risk and none of the benefit — the actual
clobber, once found, cost one line.

## WHAT WAS ACHIEVED

1. **Handover amendment, §6.8.** The 254-market v2f population bypass
   updated from "unknown direction and magnitude" to both components
   characterised and bounded — PERSISTENT-BOUNDED (pending-resolution) and
   MATERIAL-OPEN (no-FIFO-close), carried forward from 08-18. Counts
   re-run for today: pending-resolution **88 → 103 → 92** — non-monotonic,
   12 markets left the affected set and 1 entered, a churning population
   rather than a growing backlog, correcting the prior session's "growing"
   framing. No-FIFO-close steady at **161**.
   (handover amendment, commit `a0b281d`)

2. **Pending-invariant regression: two different findings under one
   surprising number.** `check_pending_flagged` moved **0 → 60,345 → 0**
   within 24 hours — not a data problem but a check racing its own
   remediation. Its predicate exactly matches `evaluate_new_trader_results.py`,
   which runs as `daily_maintenance.py` step 21, *after* the audit gate at
   step 7 — so the audit reads a full day's accumulated backlog every
   morning and can structurally never report steady state, and a run that
   fails between steps 7 and 21 would leave the backlog uncleared behind a
   recorded PASS. `check_pending_geo` (**24,082 → 36,213 → 24,704**) is a
   different animal: REAL AND TOUCHING, a weeks-old structural gap, because
   `backfill_trade_results_geo.py` exists specifically to clear it and was
   never wired into maintenance. Zero overlap with the true OOS survivors;
   2 traders overlap the true placebo survivors.
   (`2026-08-19-pending-invariant-regression.md`, commit `9fb436d`; script,
   commit `df01e7c`)

3. **Placebo exposure: NEGLIGIBLE in aggregate, with a trader-level caveat
   reported separately rather than collapsed into the aggregate.**
   Mechanism established, not assumed: stuck-pending positions **drop out**
   of both `build_presplit_cohort` and `measure_oos` entirely — thinning,
   not bias injection. 28 stuck positions = 1.09% of the placebo's 2,569.
   Direction was computable here — unlike the orphan-SELL case, these
   positions have real entry prices — verified against an empirical rule
   (`position.outcome == winning_outcome` ⟺ `trade_result='won'`, zero
   exceptions across 350,008 positions checked) rather than assumed. The
   two affected traders point in opposite directions and largely offset.
   Caveat, not smoothed away: one trader has 28.9% of their own placebo
   footprint stuck, including 9 positions post-split. `cap5` weighting
   bounds any single trader's contribution to the metric, which is the
   actual mechanism that makes the aggregate finding negligible rather than
   merely small.
   (`2026-08-19-placebo-pending-exposure.md`, commit `02ca3e6`; script,
   commit `044d2e6`)

4. **ELO write architecture reconnaissance — the session's pivot point.**
   The canonical formula (`compute_comprehensive_elo`) exists and is
   genuinely pure, verified by full read. The atomic write helper
   (`write_elo_result`) exists and guarantees exactly one thing: a
   single-statement 9-column write per trader, no more — no transaction
   wrapping, no cross-row atomicity, no enforcement that it's the only
   path. **The central finding: adherence is convention-only.** The ELO
   arc's own designed enforcement invariant (#3, "the single-writer
   enforcement invariant") was never implemented, and the five invariants
   that were built are hardcoded to tier 0 and gate nothing at any value.
   Writer D's code remains in place (6 of 9 columns, raw SQL); its live
   trigger was removed incidentally by unrelated monitor-loop refactoring,
   with no commit documenting the removal. Stage 5: 1 of 3 items resolved,
   and that one by circumstance — the `elo_last_updated` T-separated
   backfill has moved 2 rows in over a month (22,560 → 22,558). "Frozen"
   turned out to mean process-level caution, already superseded by Stages
   2/3 shipping; nothing is runtime-blocked today. Also corrected
   CLAUDE.md in passing: the Sunday full recalculation runs via
   `polymarket-sunday-elo.timer` at 03:00 UTC, **not** via
   `daily_maintenance.py` as documented.
   (`2026-08-19-elo-write-architecture-recon.md`, commit `59a2aee`)

5. **Trade-evaluator convergence and repoint — the session's first code
   change.** Convergence: 1,582,064 rows compared, **zero disagreements**.
   Three real branch-level divergences found by reading both
   implementations in full, and in two of them the geo-backfill's own
   local copy was *more* defensive than the canonical `TradeEvaluator`.
   Repoint: all three divergences resolved by hardening `TradeEvaluator`
   itself rather than wrapping it in the one caller being repointed — so
   all three of its callers benefit, and the fix does not become a fourth
   variant of the thing it's meant to retire. Verification: the
   before/after equivalence check extracted the pre-repoint function
   directly from git rather than hand-transcribing it, comparing against
   1,582,064 + 24,719 rows with zero disagreements; `run_tests.py`
   identical to baseline. Coherence assessment, not implemented:
   `evaluate_new_trader_results.py` and the now-repointed geo backfill
   differ only in a `WHERE` clause and which aggregate column they
   recompute afterward — the recommendation on record is one parameterised
   script, not scheduling a third near-duplicate maintenance step.
   (`2026-08-19-trade-evaluator-convergence.md`, commit `e059b71`, script
   commit `e4f4561`; `2026-08-19-trade-evaluator-repoint.md`, trading-swarm
   commit `3f7fd1b`, code change first-repo commit `8cfeb8e`)

6. **Write-path census — the artifact that changed the session's shape.**
   A committed scanner (`scan_write_paths.py`) mapped ~95 distinct writer
   sites across the core operational tables, plus 45 single-writer research
   tables. Surfaced, beyond what was already known: a **4th** win/loss
   implementation (`fix_expired_unresolved.py`, string-interpolating
   directly into SQL rather than parameterising); market resolution with
   **9+ independent writers and no shared helper**; position construction
   with **4 separate `INSERT` implementations**; trader P&L aggregates with
   **5**; roughly **19 additional orphan writers** (no live call site
   found); roughly **9 additional unscheduled remediation scripts** beyond
   the one already known. Enforcement of any kind is the exception across
   the writers catalogued, not the rule. One real enforcement mechanism
   turned up unexpectedly — a write-allowlist plus row cap in
   `ollama_agent_loop.py` — scoped narrowly to agent-proposed SQL, not to
   any of the ~95 direct-Python writers.
   (`2026-08-19-write-path-census.md`, trading-swarm commit `9938a04`;
   script, first-repo commit `4fb4c01`)

7. **Market-resolution write cluster, fully characterised.** 13 writers
   mapped by authority, evidence source, guard behaviour, timestamp
   semantics, and invocation — not just counted. First-writer-wins
   protects more of the cluster than the raw write count suggested — most
   writers' own candidate-selection guards already make `resolved`/`winning_outcome`
   effectively single-fire per market. The 123 `resolved=1/winning_outcome=NULL`
   rows fully attributed to one documented mechanism, not left as an
   unexplained residue. The `fast_resolution_check.py` asymmetry (one
   unconditional write site, three guarded) traced to O-17's bug scope via
   its actual commit diff, not assumed to be deliberate — O-17 fixed a
   *missing-value* bug in the three sibling sites; the fourth was never in
   that bug's scope because it had never been NULL. **The O-36 write-time
   bug shape is present in 8 of the 13 sites, not the one previously
   known** — it is this cluster's default behaviour, not a single-script
   defect.
   (`2026-08-19-market-resolution-write-cluster.md`, commit `85965c5`;
   script, commit `91ee2b2`)

8. **Clobber fix — the session's second code change.** One line,
   `fast_resolution_check.py:267`: `resolution_date = ?` →
   `resolution_date = COALESCE(resolution_date, ?)`, matching its three
   already-guarded siblings exactly. At-risk population: 1,349 markets. A
   live, bounded, read-only dry-run against the real at-risk population
   found **12 of 20 sampled were genuine, currently-active clobber
   candidates** — this was destroying better data (a real API-derived
   proxy timestamp) on every unguarded run, not a theoretical race
   condition. Recorded explicitly, per its own deliverable, as a plug
   closing one of 13 characterised write sites — not a resolution of the
   cluster.
   (`2026-08-19-resolution-date-clobber-fix.md`, commit `da91775`; code,
   commit `0a5891c`)

9. **Canonical resolution write design, then three questions answered
   before building anything.** Designed to Oscar's four directions:
   source-ranked authority (a defined evidence hierarchy, lower ranks fill
   nulls but never overwrite higher); existing writers subordinated, not
   removed; enforcement by detection *and* prevention; timestamps split
   into event-time and write-time rather than one column doing both jobs.
   Then, before Stage 0: CLOB exposes **no** resolution event-time field at
   all — a closed negative, established by dumping the full CLOB response
   for two independently-sampled resolved markets and ruling out the one
   candidate field (`accepting_order_timestamp`) empirically against
   `tape_end` — so the fact-authority source (CLOB) and the
   timestamp-authority source (Gamma) are permanently different sources,
   not a temporary gap Stage 3 might close. `store_market_dict`'s discard
   is real in code but has zero observable live instances in the current
   database. Both candidate DB triggers were built and tested in an
   isolated scratch DB: the resolved-can't-unresolve trigger breaks no
   existing writer; the resolution-provenance co-write trigger breaks
   *all 13* pre-migration, so it lands at Stage 5, not Stage 0; `INSERT OR
   REPLACE` bypasses `BEFORE UPDATE` triggers entirely — a permanent, if
   not currently live, blind spot in the trigger layer.
   (`2026-08-19-canonical-resolution-write-design.md`, commit `7248be7`,
   amended `73ca92e`; `2026-08-19-canonical-design-open-questions.md`,
   commit `c75a906`)

10. **Stage 0 shipped — the first canonical infrastructure this project
    has built.** WAL-safe online backup taken and integrity-verified
    before any schema change. Three nullable columns added to `markets`,
    including a working `CHECK` constraint — no backfill, 735,451 existing
    rows left honestly `NULL`. `trg_resolved_no_unresolve` live on
    production, verified non-tautologically inside rolled-back
    transactions (never committed) rather than assumed to work.
    `monitoring/resolution_writer.py`'s `mark_market_resolved()` built,
    called by nothing — 26/26 unit tests pass, and falsifiability was
    *demonstrated*, not asserted: 7 of the same 26 tests fail against a
    deliberately inverted ranking comparator. `check_resolution_write_atomicity`
    registered at Tier 0/OBSERVE with its promotion condition wired into
    the docstring as a mechanical, re-runnable check (a `scan_write_paths.py`
    re-run reporting zero non-canonical write sites) rather than left in
    prose — directly addressing the ELO arc's own failure (item 4 above)
    to do exactly that.
    (`2026-08-19-stage0-implementation.md`, commit `7667bdd`; code, commit
    `bc9e889`)

All ten items above, this summary, and the geo-backfill wiring
pre-registration superseded in item (d) below are committed and pushed as
of this session (`a0b281d`, `9fb436d`/`df01e7c`, `02ca3e6`/`044d2e6`,
`59a2aee`, `e059b71`/`e4f4561`, `3f7fd1b`/`8cfeb8e`, `9938a04`/`4fb4c01`,
`85965c5`/`91ee2b2`, `da91775`/`0a5891c`, `7248be7`/`73ca92e`, `c75a906`,
`7667bdd`/`bc9e889`, `9610f99`).

## STATE FOR NEXT SESSION

The order below is **proposed, not decided.**

**THE CANONICAL ARC (the live thread):**

a. **Stage 1 — migrate `hydrate_stub_markets.py`,** the most conservative
   writer in the cluster (fill-only-if-empty on every column it touches);
   before/after dry-run diff across its full candidate population, expect
   a pure no-op. **Note for whoever verifies Stage 2:** Stage 0 resolved an
   untagged legacy `resolved=1` row as lower-ranked than any real evidence
   source (documented in `monitoring/resolution_writer.py`'s own
   docstring) — so Stage 2 (`batch_update_resolved_markets`) will be the
   *first* time the canonical path actually rewrites existing resolved
   rows at scale, not just fills gaps. Read that dry-run with this
   specifically in mind, not as a generic sanity check.
b. **Stages 2–6 per the design's sequence** (`2026-08-19-canonical-resolution-write-design.md`
   §G), each individually reversible, each verified before the next.
c. **The CI lint rule from design §F** — buildable at any point after
   Stage 0, has no dependency on writer-migration order.

**SUPERSEDED / REDIRECTED:**

d. **The geo-backfill wiring pre-registration (`9610f99`) is superseded,
   not amended.** Its central step-22 question dissolves under the
   consolidation recommendation from item 5 above:
   `evaluate_new_trader_results.py` and the repointed geo backfill differ
   only in a `WHERE` clause and which aggregate column they recompute, so
   the coherent move is one parameterised script invoked twice, not a
   third scheduled near-duplicate step. Needs its own pre-registration,
   written fresh against that shape, not a patch of the old one.

**ELO CLEANUP (real, but sequence after the canonical model exists):**

e. Invariant #3 was never built; the five implemented ELO invariants gate
   nothing at any value; Writer D's code remains un-retired; the
   `elo_last_updated` backfill is not converging (2 rows/month). Better
   done once one working enforcement pattern exists in this codebase
   (Stage 0 is now that pattern) than by inventing a second, parallel one
   for ELO specifically.

**OPEN, UNCHANGED:**

f. The `check_pending_flagged` step-7-vs-step-21 ordering defect itself —
   named and explained today, not fixed.
g. `apply_synthetic_closes` as a third win/loss implementation — different
   unit (positions, not trades), does most of the actual synthetic-close
   work in this system, and is missing the `invalid`-state guard the two
   trade-level evaluators both have.
h. The other clusters the census surfaced but did not investigate:
   position construction (4 `INSERT` implementations), P&L aggregates (5),
   trader flag-state (4 files writing around one deliberate state
   machine), ~19 orphan writers, ~9 unscheduled remediation scripts beyond
   the geo-backfill one.
i. Ingestion-stall detection and the 500-trade recovery-window threshold
   — both carried from 08-18, neither touched today.
j. **Carried from 08-15, unchanged:** the cutover decision; the
   category-split cost floor; the consensus question; the
   `comprehensive_elo` sign error; elections calibration re-run (O-40);
   O-38; O-18. Track 2 CI power diagnostic still uncommitted; its A3 stop
   condition still needs amending.

## BIG PICTURE

The thesis result (+0.0316, CI [−0.0088, +0.0710], NULL, underpowered) is
untouched by everything found this session and remains exactly as it was
on 08-15. What changed is the project's understanding of its own write
surface: roughly 95 writers mapped, enforcement the exception rather than
the rule, and the same defect shape — an implementation exists, a
canonical version exists, nothing enforces the relationship — recurring
because nothing had made the population of it visible until today. The
canonical resolution write path is the first structural answer to that
shape, and it is one stage in of a seven-stage design; the ELO arc's own
equivalent gap (invariant #3, never built) is still open and is now a
known, named instance of the same pattern rather than a surprise waiting
to be rediscovered.

**Plain statement, accurate about what actually shipped, not to be
inflated in a future read of this file:** two code fixes went into
production this session — the trade-evaluator repoint (with the canonical
function itself hardened, not wrapped) and the one-line `resolution_date`
clobber guard — plus Stage 0 of the canonical write design (schema,
trigger, function, invariant; called by nothing, no writer migrated).
Everything else — the handover amendment, both invariant/placebo
investigations, the ELO recon, the write-path census, the resolution
cluster, the design itself, and the three open-questions answers — was
characterisation or design, not implementation. The thesis question itself
is unchanged and unresolved: the result is underpowered, the honest
resolution is more out-of-sample observations, and whether Phase 2 can
deliver them in finite time (Track 2) is still unanswered.
