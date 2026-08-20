# 2026-08-20 — Stage 1 migration of `hydrate_stub_markets.py`: STOPPED, not implemented

**No code written. No production write made. No commit.** Every claim
tagged **[V]** (verified this session, command/evidence given) or **[I]**
(inferred). Design: `2026-08-19-canonical-resolution-write-design.md`
(`73ca92e`), §G Stage 1. Stage 0: `7667bdd` / `bc9e889`. Function:
`monitoring/resolution_writer.py`.

---

## Summary

The task's posed blocking question (evidence-source-rank divergence)
resolves to **no current divergence** — answered in full below. But
resolving it required reading `mark_market_resolved()`'s comparator
closely enough to surface a **second, structurally distinct divergence**
that the posed question doesn't cover and that empirically **does** fire,
on the majority of real candidate writes: `mark_market_resolved()` has no
code path to express "market is not yet resolved." `hydrate_stub_markets.py`
routinely needs exactly that path. This is not a corner case found by
searching for one — it's what a real, full-population dry run against
production returned today: **7 of the 8 rows the old script would
actually write are still-open markets.**

Per the standing instruction ("if the design cannot be implemented as
specified, STOP AND REPORT rather than improvising") and the task's own
verification-section instruction ("a non-zero difference means the no-op
assumption failed — STOP and report rather than accepting it"), this is
reported rather than resolved by picking a behavior. **No migration code
was written.**

---

## Part 1 — the posed blocking question, answered

### (a) `hydrate_stub_markets.py`'s exact guards — [V], read in full, `scripts/hydrate_stub_markets.py`

**Candidate selection** (`get_stub_markets`, lines 96–110):
```sql
SELECT DISTINCT m.market_id, m.title, m.api_id, m.category
FROM markets m
WHERE m.resolution_date IS NULL
  AND m.market_id IN (
      SELECT DISTINCT t.market_id FROM trades t
      JOIN traders tr ON tr.address = t.trader_address
      WHERE tr.discovery_source = 'external_seed'
  )
```
**Confirmed: gated on `resolution_date IS NULL`, not on `resolved` status** —
exactly the hypothesis the task asked me to verify.

**Per-column write guard** (lines 198–223), one `UPDATE` per market:
- `resolution_date = COALESCE(resolution_date, ?)` — fill only if currently NULL.
- `resolved = CASE WHEN (resolved IS NULL OR resolved = 0) THEN ? ELSE resolved END`
  — writes the newly-computed `is_resolved` (0 or 1) whenever the existing
  value isn't already 1. **Not itself "fill-only-if-empty" in the way `resolution_date` is** — it will happily (re-)write 0 over an existing 0; it's guarded against overwriting a 1, not against writing at all.
- `winning_outcome = CASE WHEN winning_outcome IS NULL AND ? IS NOT NULL THEN ? ELSE winning_outcome END`
  — fill only if currently NULL and the new value is non-null.
- `category`/`title` — separate, similarly-shaped fill-only guards. **Out of scope, untouched, confirmed not read further for this task.**

### (b) `mark_market_resolved()`'s comparator on a non-null value + NULL evidence source — [V], read in full, `monitoring/resolution_writer.py`

Two branches matter here, not one:

1. **`prev_resolved == True` and `prev_evidence_source IS NULL`:** treated as
   *unranked* (`_UNRANKED = 99`), so `new_rank < 99` is always true — **any**
   real evidence source is unconditionally **accepted as an improvement**,
   overwriting `winning_outcome`/`resolution_date` regardless of what was
   already recorded. This is the case the posed blocking question is about.
2. **`prev_resolved == False`** (the row is not yet resolved, regardless of
   `evidence_source`): `accept = True; reason = "written"` — **also**
   unconditionally accepted, and unconditionally writes `resolved = 1`.
   **There is no branch, anywhere in the function, that writes `resolved = 0`
   or otherwise represents "not yet resolved."** This is a structural
   property of the function's contract (consistent with `trg_resolved_no_unresolve`
   only ever needing to block 1→0, never 0→anything), not a bug — but it
   means the function is a pure *resolution-assertion* primitive and cannot
   express a proxy write for a market that isn't resolved.

### (c) Do they diverge? — [V]

**For the posed question's specific case (existing `resolved=1`, `resolution_evidence_source IS NULL`): NO, not currently.** Checked empirically against the real candidate population, not assumed:

```sql
-- full hydrate_stub_markets.py candidate population (resolution_date IS NULL,
-- market_id in trades by external_seed traders)
SELECT COUNT(*) ...                                            -- 1,258
-- of those, already resolved=1
SELECT COUNT(*) ... AND resolved = 1                            -- 0
-- of those, winning_outcome already non-null (any resolved value)
SELECT COUNT(*) ... AND winning_outcome IS NOT NULL             -- 0
```

Every one of the 1,258 current candidates has `resolved=0`, `winning_outcome
IS NULL`, `resolution_date IS NULL` — completely empty slots. **The specific
scenario the task described (an existing resolution value with no evidence
tag, inside this script's candidate population) has zero instances in
production right now.** `resolution_evidence_source` is also confirmed NULL
on 100% of these rows (expected — it's NULL on all 736,738 rows in the DB,
per this morning's Stage 0 check).

**But a second, broader-scope divergence does fire — see Part 2.**

### (d)/(e) — see Part 2 below; this is where the STOP actually happens.

---

## Part 2 — the divergence the posed question didn't ask about, found while answering (b)

**The specific case:** any candidate where the live Gamma lookup returns
`is_resolved = 0` (the market genuinely isn't resolved yet). For these:

- **Old script:** `resolved` stays 0 (CASE's `THEN` branch re-writes 0→0,
  a value no-op), `winning_outcome` stays NULL (guard requires the new value
  be non-null, and it's `None` here), but **`resolution_date` gets filled**
  with the Gamma-reported end-date/`resolutionTime` value — this is a
  scheduled-end-date proxy fill on an open market, not a resolution claim.
- **`mark_market_resolved()`:** has no way to accept this call and leave
  `resolved` at 0. A caller wanting to preserve old behavior for this branch
  cannot use the function at all for it — calling it (with
  `allow_no_winner=True`, since `winning_outcome=None`) would **accept and
  write `resolved=1`** on a market Gamma just told the caller is *not*
  resolved. That's not a rare edge case to special-case away; it's the
  literal majority of what this script does when it finds a live hit.

**Empirical confirmation — full-population dry run against live production,
today, pre-migration code (`git log --oneline -1 -- scripts/hydrate_stub_markets.py`
→ `67b173e`, no changes since; this run *is* the current baseline):**

```
python3 scripts/hydrate_stub_markets.py --limit 2000 --dry-run
[HYDRATE] Stub markets to process: 1258 (limit=2000, dry_run=True)
[HYDRATE] Done — updated=8, not_found=1250, errors=0, total=1258
```

Of the **8** rows the old script would actually write:

```
resolved=0  (7 rows) — e.g. 0xa7abe7ea..., 0xad01e2b4..., 0xb669c8c0...,
                         0xbb57ccf5..., 0xcd264046..., 0xdf8e2dc5..., 0xef89a2e4...
resolved=1  (1 row)  — 0xf8dbde8b..., winner=No
```

**87.5% of the real, current writes are the case `mark_market_resolved()`
cannot represent.** The other 1,250 candidates returned `not_found` from
Gamma (delisted/unavailable — not part of this question).

**This is not the `resolution_evidence_source`-ranking question at all** —
it doesn't depend on evidence tags, ranks, or ties. It's simpler and more
fundamental: `mark_market_resolved()` is a resolution-assertion primitive
with no "not resolved" output, and `hydrate_stub_markets.py`'s dominant
real behavior is exactly that output.

**Design-doc cross-check** — §H already named this as the risk to watch for
at this stage, in general terms: *"if `hydrate_stub_markets.py`'s
fill-only-if-empty guard doesn't map cleanly onto 'Rank 2 filling a null
slot' the way this design assumes — the dry-run diff step exists
specifically to catch that before Stage 2 changes anything with real
overwrite stakes."* The Summary table's row for writer #11 states the guard
"becomes exactly what 'propose, defer to existing' already means under
source-ranking" as a clean total mapping — that statement is **not true**
for the `is_resolved=0` branch, which isn't a "propose, defer" situation at
all; it's a write the canonical function structurally cannot accept without
corrupting the row.

---

## What this means for Stage 1, and why I stopped instead of picking one

A behaviorally-faithful migration is very likely achievable — gate the
`mark_market_resolved()` call on the script's own `is_resolved == 1`
determination, and leave the `resolution_date`-as-scheduled-proxy write for
the `is_resolved == 0` branch as a direct, uncanonicalized write, exactly as
today (structurally the same category as `monitor.py`'s proxy writes, which
§H already excludes from this design for the same reason: a different
question, "when is this scheduled to end," not a resolution claim). This
reading is the only one that could satisfy Stage 1's own stated bar ("zero
behavioral difference expected") — every other reading either drops a
currently-working fill (fails the no-op bar outright) or falsely resolves
open markets (a correctness regression, not a neutral one).

**I did not implement this.** Two reasons:

1. **It is a partial migration, not the total one the task and the design's
   summary table describe** ("replace hydrate_stub_markets.py's direct
   writes to resolved/winning_outcome/resolution_date with calls to
   mark_market_resolved()"). Deciding unilaterally that one of those three
   columns keeps a direct write for 7/8 of real cases is a real design
   decision — the same category of decision the task explicitly reserves
   for Oscar when it says, of the *other* divergence, "this is a design
   question for Oscar, not something to resolve by picking a behaviour."
   That reasoning applies here at least as strongly, since this divergence
   is bigger (dominant case, not a zero-row corner case).
2. **The instruction is unambiguous:** "If the design cannot be implemented
   as specified, STOP AND REPORT rather than improvising." The design's own
   Summary-table claim for writer #11 — a clean, total mapping onto
   "propose, defer to existing" — is the part that doesn't hold up under the
   real candidate data. That is the design not being implementable exactly
   as specified.

## Options for Oscar

1. **Gate on `is_resolved == 1`; keep the `resolution_date` proxy-fill for
   `is_resolved == 0` as a direct write, unchanged.** Preserves 100% of
   current behavior (verifiable by the required before/after dry-run diff).
   Migrates the genuinely-resolved fraction of writes (currently 1 in 8
   live hits) through the canonical path; leaves the majority fraction
   exactly as it is today, outside it — symmetric with how `monitor.py`'s
   proxy writes are already excluded.
2. **Extend `mark_market_resolved()` or add a sibling function** to
   represent "not yet resolved, proxy end-date only." Touches the Stage-0
   function itself, which Stage 0's own commit said nothing would call and
   nothing would need to change until a dedicated migration task — this
   would make Stage 1 partly a Stage-0 amendment, a bigger and different
   change than "migrate one writer."
3. **Drop the open-market proxy fill from `hydrate_stub_markets.py`
   entirely.** Simplest, but a real behavior change (these markets never
   get `resolution_date` filled by this script again) — fails the "pure
   no-op" bar the design itself sets for Stage 1, so this isn't a
   no-decision default either.
4. **Defer Stage 1 until this is resolved**, treating it as a design
   amendment rather than an implementation detail of the migration.

I have a mild preference for (1) as the only option that keeps Stage 1
exactly what it was sold as — but naming a preference is not the same as
picking it unilaterally, per the standing instruction.

---

## Verification status (per task's Verification section)

**Not run — no code changed, nothing to verify.** For completeness, since
verification item (a) doubles as this document's evidence: the required
before/after dry-run diff **cannot be produced** until Part 2 is resolved,
because there is no single unambiguous "after" behavior to diff against
without knowing which option above is chosen.

**WAL-safe backup:** **not taken — confirmed not applicable.** Nothing in
this session wrote to the production database. `hydrate_stub_markets.py`'s
`dry_run=True` branch structurally returns before reaching any
`conn.execute("UPDATE ...")` call (confirmed by reading the control flow at
lines 188–230, same discipline as the trade-evaluator repoint's equivalent
check) — the one script execution this session (`--dry-run`, full
population) only issued `SELECT`s against the local DB and `GET`s against
the Gamma API. `git status` on both repos shows no unexpected changes
beyond this document.

## Reversibility

N/A — no commit made to `first-repo` beyond this decision record in
`trading-swarm`. Nothing to revert.
