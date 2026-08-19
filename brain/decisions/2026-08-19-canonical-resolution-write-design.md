# 2026-08-19 — canonical market-resolution write path: design

**This is a specification, not an implementation.** No writer modified, no
schema changed, no invariant built. Every claim about the existing 13
writers is cited from `2026-08-19-market-resolution-write-cluster.md`
(`85965c5`) and tagged **[V]** there; every design choice here is this
document's own proposal, tagged **[D]** (design decision — a choice made,
not a fact) so it isn't mistaken for verified behavior. Where two evidence
sources are genuinely equal, this is stated rather than a tiebreak invented.

Designing to Oscar's four directions as given — none re-litigated.

---

## A. The source ranking

Three separate rankings are needed, because the 13 writers supply evidence
for three different kinds of fact, and conflating them is exactly how
`resolution_date` ended up carrying two incompatible meanings.

### A1. Ranking for `resolved` / `winning_outcome` (the resolution fact)

| Rank | Source | Writers using it | Justification |
|---|---|---|---|
| **1 (highest)** | **CLOB API `token.winner` flag** | #4, #5, #6, #12 | A direct, declarative signal from the trading venue itself — the CLOB marks a specific token as the winner. Not an inference. The cluster doc's own code comment (`run_stale_clob_pass`'s docstring) already calls this "the authoritative resolution source" — this design adopts that judgment rather than inventing a new one. |
| **2** | **Gamma API price-threshold inference** (`outcomePrices >= 0.99`, `winnerIndex` fallback, `__RESOLVED_NO_WINNER__` sentinel for all-zero-price closed markets) | #1b (resolved-flag only), #3, #7, #8, #9, #10, #11 | An algorithmic *inference* from market price data, not a direct declaration. Generally reliable (this is the majority evidence source in the cluster) but structurally one step removed from source-of-truth — a market could sit at 0.97 without being un-resolved, or price data could lag. |
| **2 (stated as equal, not ranked separately)** | **Human-verified-then-hardcoded** | #13 | A human confirmed the outcome by reading Gamma at some point in the past and hardcoded it into the script. This is not stronger evidence than a live Gamma read — a human reading Gamma data by eye is the same underlying evidence base as #7/#8/#9/#10's automated extraction, just performed once, manually, and frozen. **No basis was found to rank it above or below Tier 2 — stated as equal rather than inventing a distinction.** Its weakness is staleness (frozen at check-time, never re-verified), not evidentiary quality; staleness is not a ranking axis, it's an argument for the evidence_source tag to record *when* it was checked (see C), not for a rank of its own. |
| **3 (lowest — not a claim at all)** | **Hardcoded default, no live evidence** | #1a (`resolved=False` at stub creation) | This isn't establishing a fact — it's an initial null state at INSERT time. It should never be able to compete with, let alone overwrite, an actual claim from any other source. Modeled as rank 3 only so the ranking is total; in practice this "source" should never reach `mark_market_resolved()` at all (see H). |
| **n/a** | **Caller-supplied, unspecified** | #1 generic case, #2 | `update_market`'s ON CONFLICT branch and `update_market_resolution` take whatever the caller passes with no source tag at all today. Under this design they inherit the rank of whatever evidence the *caller* actually had — they are not their own source, they're a pass-through with no current discipline about what's on the other end. This absence of a tag is itself part of the problem (see F, E). |

**The rank-timing wrinkle — [V] found incidentally while answering Q1
(`c75a906`), and an argument *for* this ranking model, not against it.**
One of the two markets sampled for the CLOB field check showed CLOB
`closed: false` with **both** tokens `winner: false`, despite one token
already pricing at `0.9995` — i.e., a Rank-2 (Gamma price-inference)
determination is fully capable of arriving **before** the Rank-1 (CLOB
declaration) source populates for the very same market. This does not
weaken the ranking: a direct declaration is still a stronger *type* of
evidence than an inference, independent of which one happens to update
first. But it means the comparator inside `mark_market_resolved()` will
**routinely** encounter an already-stored Rank-2 value that a later
Rank-1 write needs to outrank and overwrite — this is not a rare tiebreak
condition, it is expected, frequent, ordinary operation of the ranking
logic. **Stage 3's verification (G) should expect to observe exactly
this pattern on real candidates** — a Rank-1 CLOB write superseding an
already-present Rank-2 Gamma value — and should not treat it as an
anomaly if seen.

### A2. Ranking for `resolution_date` as **event-time** (once the column is split — see D)

**[V] CLOB's own resolution timestamp is a closed negative, not an open
question — resolved by `2026-08-19-canonical-design-open-questions.md`
(`c75a906`), Q1.** Two live calls against independently selected resolved
markets dumped the CLOB `/markets/{condition_id}` response in full (every
top-level field, not just the ones existing code reads). No field carries
a resolution or settlement timestamp. The one candidate,
`accepting_order_timestamp`, was ruled out empirically: on both sampled
markets it precedes the market's own last trade in the local DB by more
than 7 months, and clusters on an unrelated historical-import date
(`2025-12-11`, matching `backfill_o16_tier1.py`'s own documented
migration-batch date) rather than any per-market lifecycle event — a true
resolution timestamp cannot predate 7 further months of trading. **This
is not deferred to Stage 3 for confirmation; it is established.**

**Structural fact of the design, stated plainly rather than left implicit:**
the highest-authority source for the resolution **fact** (CLOB, A1 Rank
1) and the highest-authority source for the resolution **timestamp**
(Gamma's `closedTime` / `umaEndDate` / `endDate`, A2 Rank 1 below) are
**different sources, permanently** — not a temporary artifact Stage 3
might unify. CLOB has nothing to contribute to this ranking at any rank;
it is absent from the table below entirely, not listed and marked
unpopulated.

| Rank | Source | Writers using it today | Justification |
|---|---|---|---|
| **1** | **True API-sourced resolution timestamp** — Gamma's `closedTime` / `umaEndDate` / `endDate` fields | #7, #8, #11 | An actual timestamp attributable to the market's real-world resolution event, not a guess. The only real event-time source found across either API — see the closed-negative finding above. |
| **2** | **`end_date` (scheduled end date), used explicitly as a proxy** | #1 (fallback), monitor.py's proxy writes (out of scope, see H) | Real evidence, but evidence of a *different* fact (when the market was scheduled to end) being used to estimate a fact it resembles (when it actually resolved). Explicitly a downgrade, not a lie — this is why it's ranked, not excluded. |
| **n/a — moved out of this ranking entirely** | `datetime.now()` at write time | #2, #3, #9, #10, #12, #13 (6 of 13; #4/#5/#6 also fall back to it, now confirmed unconditionally rather than pending CLOB extraction) | **This is the core fix.** Write-time is not evidence about the market at all — it's evidence about *our system*. Under the split schema (D) it stops competing in this ranking altogether; it goes to its own column with its own, non-competing meaning ("when we recorded this"), which every writer populates unconditionally with no ranking question involved. |

### A3. `winning_outcome = NULL` on a resolved market (the no-winner case)

Not really a ranking question — a **type** distinction, currently
unmodeled (see D's `resolution_evidence_source` proposal and the schema
note on `allow_no_winner`). #7/#8's `__RESOLVED_NO_WINNER__` handling and
the 123 live rows it produced (`85965c5` Q4) are the only writers that
currently distinguish "resolved with no winner" from "not yet resolved" —
every other writer either doesn't handle the case or (per #1b) sets
`resolved=True` with `winning_outcome=NULL` without ever declaring
whether that's deliberate.

---

## B. The tie case

**Which writers can actually collide at equal rank, in practice:** per
the cluster doc's overwrite matrix, **#9 (`resolve_legendary_markets.py`)
and #10 (`legendary_positions_scan.py`)** are the one confirmed pair —
both Rank-2 (Gamma inference), both target overlapping LEGENDARY-trader
market populations, on different schedules (`daily_maintenance.py` step
20 vs. Monday-only direct cron). **[V]** cited from `85965c5`'s overwrite
matrix, row for that pair.

A second same-rank overlap exists in principle but has not been
demonstrated: **#3 (`batch_update_resolved_markets`, step 16) and #9
(step 20)** are both Rank-2/Gamma and #3's candidate population (all
unresolved markets) is a superset of #9's (LEGENDARY-tier markets only).
**[I]** Because #3 runs at step 16 and #9 at step 20 — earlier in the
same daily run — #3 will, in practice, already have flipped
`resolved=1` on any market #9 would have reached, before #9's own
`resolved=0` candidate filter ever sees it. **This means today's ordering
already resolves this pair by accident (step sequence), the same way the
cluster doc found #4/#5/#6-vs-#9/#10 self-resolving by accident** — not
evidence the tie case doesn't matter, evidence that it's currently masked
by scheduling, which is exactly the kind of dependency this design should
not continue to rely on implicitly.

**Proposed behavior [D], considered against all four options named in the task:**

- **Reject-second** (silently refuse any write once a same-rank value
  exists): too rigid — it throws away a genuine disagreement signal. If
  two Rank-2 sources produce *different* winners for the same market
  (rare, but the whole reason evidence quality matters), silently
  discarding the second tells nobody that a disagreement occurred.
- **Last-wins**: reopens exactly the non-determinism problem this design
  exists to remove — which value survives becomes a function of run
  order again, just moved one layer down (now it's "which same-rank
  writer runs later" instead of "which writer of any rank runs later").
- **First-wins, unconditionally**: matches today's accidental behavior
  and is the right choice for the *overwhelming majority* of same-rank
  collisions, because two Rank-2 Gamma reads of the same already-closed
  market's price data should almost always agree — treating agreement as
  a silent no-op is correct, not a gap.
- **Proposed: first-wins by default, with an explicit branch for
  disagreement.** When a same-rank writer's proposed value **matches**
  the already-recorded value: silent no-op (this is the common case and
  should not generate noise). When a same-rank writer's proposed value
  **differs** from the already-recorded value: **flag-for-review** — do
  not overwrite (still first-wins for the actual stored fact, so nothing
  about live behavior regresses), but record the disagreement somewhere
  a human or an audit can find it (see E's audit surface). This is a
  hybrid, not a dodge: it keeps the simple, low-noise case simple, and
  makes the rare, actually-informative case visible instead of silently
  discarded or silently overwritten.

**Still needs an answer even though the demonstrated set is small (1
confirmed pair, 1 masked-by-ordering pair):** yes, stated explicitly per
the task's instruction — any future Rank-1 or Rank-2 writer added to this
cluster inherits this same policy by construction (it's a property of
`mark_market_resolved()`, not of any specific writer pair), so the design
does not need to be revisited each time a new same-rank writer appears.

---

## C. The function signature

```python
@dataclass(frozen=True)
class ResolutionWriteResult:
    accepted: bool
    reason: str                    # e.g. "written", "no-op: existing value ranks >= proposed",
                                    # "flagged: same-rank disagreement", "rejected: winning_outcome
                                    # required unless allow_no_winner=True"
    previous_value: dict | None    # {resolved, winning_outcome, resolution_date, resolution_evidence_source} or None if row was unresolved
    written_value: dict | None     # the same shape, post-write; None if accepted=False


def mark_market_resolved(
    conn: sqlite3.Connection,
    market_id: str,
    *,
    winning_outcome: str | None,
    allow_no_winner: bool = False,
    resolution_event_time: datetime | None,   # true event-time if known; None if only write-time is known
    evidence_source: Literal["clob", "gamma", "manual_verified", "hydration_fill"],
    evidence_detail: str | None = None,       # free text, e.g. "outcomePrices>=0.99" / "token.winner" / a human's note
    dry_run: bool = False,
) -> ResolutionWriteResult:
    ...
```

**Parameters, justified:**
- `winning_outcome: str | None` with `allow_no_winner` required to pass
  `None` — makes #7/#8's currently-implicit "no winner" case an explicit,
  named argument instead of a silent default, closing A3's gap.
- `resolution_event_time: datetime | None` — **not computed inside the
  function.** The caller supplies whatever true event-time it has (or
  `None`). This is the split from D made concrete at the call boundary:
  a caller with only write-time knowledge cannot accidentally smuggle it
  in as event-time, because there's no code path inside the function that
  defaults `resolution_event_time` to `datetime.now()` — that value is
  captured automatically and separately, for `resolution_recorded_at`
  (D), regardless of what's passed here.
- `evidence_source` — a closed enum (`Literal`), matching A1/A2's ranking.
  Required, not optional — a call that can't name its evidence source is
  exactly the caller pattern (#1, #2's "caller-supplied, unspecified")
  this design exists to close.
- `dry_run` — mirrors the convention already used across this cluster
  (`fast_resolution_check.py --test`, `backfill_o16_tier1.py --dry-run`),
  so migrated writers keep their existing CLI dry-run behavior by passing
  it straight through.

**What happens on rejection [D]:** **returns a value, does not raise.** A
rejection (existing value outranks the proposal, or a same-rank match) is
an *expected, routine* outcome for the majority of calls — #4/#5/#6's
own candidate rows will very often already be covered by #3's earlier
daily pass, and that is correct, not exceptional. Raising would force
every caller into a try/except for the common case. `ResultWriteResult.accepted`
tells the caller definitively whether its proposal took effect;
`reason` tells it why not, distinguishing "already resolved by something
at least as authoritative" from "flagged: same-rank disagreement" — a
caller that cares (or one instrumented to log summary stats, matching
`backfill_trade_results_geo.py`'s own `won=/lost=/invalid=` counters
pattern already established in this codebase) can act on the distinction;
one that doesn't can ignore the return value entirely without breaking.
**Also always logs** at INFO for accepted writes and no-ops, WARNING for
flagged disagreements — the flag-for-review behavior from B needs a place
to land, and a log line plus (see E) an audit trail via the new columns
is proposed rather than a new dedicated conflicts table, to avoid adding
schema beyond what D already specifies.

---

## D. The schema change

**[D] Additive only — no rename, no repurposing of the existing
`resolution_date` column's name or its readers' expectations.**
`resolution_date` is read by `requeue_resolved_market_traders.py`'s
`resolution_date > ?` filter, the v2f arc's `tape_end`/population
queries, and an unknown-but-probably-large set of other consumers per the
write-path census — renaming it would be a breaking change to every one
of them for no benefit the new columns don't already provide additively.

**New columns, on `markets`:**

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| `resolution_recorded_at` | TIMESTAMP | Yes | **Write-time.** When *our system* recorded this row's current resolution state — exactly what `datetime.now()` was already capturing, given an honest name and moved out of `resolution_date`. Populated unconditionally by `mark_market_resolved()` on every accepted write, regardless of evidence source. |
| `resolution_evidence_source` | TEXT, `CHECK (resolution_evidence_source IN ('clob','gamma','manual_verified','hydration_fill') OR resolution_evidence_source IS NULL)` | Yes | The A1/A2 rank-bearing tag. NULL means "not written via the canonical path" — this is what makes the invariant in E non-tautological. |
| `resolution_evidence_detail` | TEXT | Yes | Free text (e.g. `"outcomePrices>=0.99"`, `"token.winner"`, a human's note for `manual_verified`) — not rank-bearing, just provenance detail for anyone auditing a specific row by hand. |

**`resolution_date` itself is unchanged in schema** — same column, same
type, same nullability — but its *going-forward* semantics under the
canonical path are: best-known event-time, or the A2-Rank-2 `end_date`
proxy, or — **only when no better information exists at all and an
existing downstream consumer depends on non-null values** — the write-time
value, exactly as today, but now distinguishable from a real event-time
by checking `resolution_evidence_source` and comparing `resolution_date`
against `resolution_recorded_at` (if they're equal, or absent a
Rank-1/2 evidence tag, the value is a write-time fallback, not a true
event-time). **This is a deliberate compromise, not an oversight** — see
H for why leaving `resolution_date` NULL when no event-time is known was
considered and rejected.

**Backfill — explicitly, per the task's instruction, NOT proposed for
existing rows:** the ~224,910 currently-resolved markets' `resolution_date`
values are an unrecoverable mix of true event-time (writers #7, #8, #11)
and write-time-masquerading-as-event-time (writers #2, #3, #9, #10, #12,
#13, and #4/#5/#6 whenever their CLOB-timestamp extraction gap from A2
means they also fell back to write-time) — **there is no way to tell,
after the fact, which historical row came from which**, because none of
the 13 writers recorded their evidence source until now. `resolution_recorded_at`
and `resolution_evidence_source` are left **NULL for every row that
predates this migration** — NULL is the honest state ("provenance
unknown, predates tracking"), not a guess. No backfill script, no
heuristic reclassification, no "assume rows written by writers we now
know were write-time-only are write-time" retroactive tagging — even
that would be an unverifiable assumption about *which writer touched a
given row*, which is not recorded anywhere either. **Historical rows
remain exactly as unreliable for event-time purposes as O-36 already
established them to be** — this design does not and cannot fix the past.

---

## E. The invariant

**Shape, modeled directly on ELO arc invariant #4 (write atomicity), not
#3** — read closely, #3's own design ("`|comp − compute_comprehensive_elo(stored
components)| < ε`") requires a *pure recomputation function* to compare
the stored value against; there is no equivalent recomputation for "was
this the correct resolution" (that would require re-deriving the Gamma/CLOB
evidence at audit time, which is a live external-API dependency the audit
harness doesn't have elsewhere). #4's shape — "a row that must have gone
through the canonical path has all canonical-path columns populated
together; find the ones where they're not" — has a direct, checkable
analog here and needs no external call:

```sql
SELECT COUNT(*) FROM markets
WHERE resolution_recorded_at IS NOT NULL
  AND resolution_evidence_source IS NULL
```

**What it asserts:** any row whose `resolution_recorded_at` has been
touched (i.e., *something* wrote to its resolution state during the
canonical-path era, since only `mark_market_resolved()` populates that
column) must also carry a non-null `resolution_evidence_source` (since
`mark_market_resolved()` always sets both together, in the same
statement, same discipline as `write_elo_result`'s all-9-columns-together
pattern). **Floor: 0.**

**Why this is non-tautological — stated explicitly, since the task
requires it:** this is not "does the canonical function set both
columns" (trivially true by construction, and would be tautological if
that's all it checked). It's "did **anything else** — a rogue writer, a
manual `UPDATE`, a future script that forgot to migrate — touch
`resolution_recorded_at` without going through the function that's
supposed to be the only thing that touches it." **[D]** This requires
`resolution_recorded_at` to be a column *only* `mark_market_resolved()`
ever writes — a non-canonical writer bypassing the function has no reason
to know this column exists or to populate it "correctly" paired with
`resolution_evidence_source`, so a rogue write is far more likely to
either (a) not touch `resolution_recorded_at` at all (leaving both NULL,
invisible to this specific check — a real limitation, named in H) or (b)
touch it via copy-pasted code that doesn't also set `evidence_source`
(caught). This check catches (b) but not (a) — **a genuinely
non-tautological but incomplete detector**, not a complete one; stated
honestly rather than oversold.

**Architectural consequence, now that F's `trg_require_recorded_at`
(Stage 5, G) exists alongside this invariant — stated plainly, because
detection and prevention here cover each other's blind spots and
**neither can be retired once the other lands**:**

- **This invariant's own admitted gap, case (a)** — a writer that
  ignores both new columns entirely, never touching
  `resolution_recorded_at` at all — **is closed by
  `trg_require_recorded_at` for every write shape that goes through
  SQLite's normal `UPDATE` path**, since the trigger aborts the statement
  outright rather than letting a column-less write land silently. The
  invariant no longer needs to be the only thing standing between a
  forgotten writer and an unnoticed gap once Stage 5 lands the trigger.
- **The trigger's own admitted gap, `INSERT OR REPLACE`** (F) — is where
  this invariant remains the *only* backstop: a delete-then-insert
  statement bypasses the trigger entirely, but if it also fails to set
  `resolution_recorded_at`, this invariant's `SELECT COUNT(*) ...` cannot
  see it either, because case (a) is exactly what an `INSERT OR REPLACE`
  omitting the new columns produces. **What remains uncovered by both,
  stated explicitly rather than implied to be solved:** a future writer
  that uses `INSERT OR REPLACE` on `markets` and does not set
  `resolution_recorded_at` is invisible to the trigger (bypassed) and
  invisible to this invariant (case-(a) blind spot) simultaneously. This
  is not a live risk today (no current writer uses that statement shape
  on this table), but it is a genuine residual gap in the combined
  detection-and-prevention model, not something either mechanism alone
  or both together fully close.

**Tier and promotion condition — the part the ELO arc's design never
answered concretely:**
- **Starts at Tier 0 / OBSERVE**, same convention as the ELO arc's Stage
  0d, for the same reason: the columns don't exist yet at design time,
  and even once they do, the first migrated writers (G, Stage 1–2) need
  to run for a real period before the check's own baseline is trustworthy.
- **Promotion to Tier 1 / CRITICAL is gated on a checkable, mechanical
  condition, not a calendar date:** re-run `scripts/scan_write_paths.py`
  (already committed, this session) against `markets.resolved` /
  `winning_outcome` / `resolution_date` and confirm **zero** direct
  `UPDATE markets SET (resolved|winning_outcome|resolution_date)`
  statements remain outside `mark_market_resolved()`'s own module — i.e.,
  promotion happens exactly when Migration Stage 5 (G) is verified
  complete by the same tooling that produced the original 13-writer map,
  not by someone remembering to flip a flag. **This is the concrete
  answer the ELO arc's own design document specified in prose
  ("gating from end of Stage 3") but never actually wired into
  `audit_invariants.py`'s tier-0-forever hardcoding** — naming that
  precedent explicitly so this design doesn't repeat it silently.

---

## F. The allowlist assessment

**[V] Read `trading-swarm/orchestrator/ollama_agent_loop.py` in full for
the relevant sections (`_WRITE_ALLOWLIST`, `_match_write_allowlist`,
`_assigned_columns`, `tool_run_sql_write`).**

**What it actually gates:** a single tool function,
`tool_run_sql_write(db_path, query, params)`, exposed to a local LLM
agent inside `ollama_agent_loop.py`'s tool-calling loop. When the agent
chooses to call this tool, the function (a) rejects any `db_path` other
than the exact production path, (b) regex-matches the **SQL text string**
against a hardcoded list of 5 permitted `UPDATE traders SET <single
column>` shapes, using an exact-assigned-column check (`_assigned_columns`)
specifically to prevent a second, smuggled column riding along behind a
permitted one (the O-24/Fable-6.1 fix named in its own comments), and (c)
caps `rows_affected` at 50,000 for non-DDL statements. If the query
doesn't match, it's rejected before ever reaching `sqlite3.execute()`.

**Does it extend to direct Python writers? No — stated plainly, not
forced.** Three structural reasons, not one:
1. **It gates SQL *text*, intercepted at a specific function call.** A
   Python script that does `conn.execute("UPDATE markets SET resolved = 1, ...")`
   directly never calls `tool_run_sql_write` — there is no interception
   point between arbitrary Python code and `sqlite3`. The allowlist has
   nothing to inspect unless the write is routed through this one
   function, which none of the 13 writers are, or would naturally be
   (they're not LLM-agent tool calls).
2. **It targets a different threat model.** The module's own docstring
   frames it as guarding *unpredictable, model-generated* input — an LLM
   deciding what SQL to write, which could hallucinate a column name or
   attempt something unintended. The 13 writers in this cluster are
   fixed, human-written, code-reviewed Python — a different risk (a
   correct-looking write bypassing agreed discipline, not an
   unpredictable one).
3. **It's scoped to `traders`, not `markets`.** Even if the interception
   problem were solved, the current allowlist doesn't cover any of the
   three resolution columns at all — it would need new rules regardless.

**What would actually work at this layer — three options assessed, one recommended:**

- **DB trigger (`CREATE TRIGGER ... BEFORE UPDATE ON markets ...`).**
  Real, connection-agnostic, runtime enforcement — the only option that
  would catch a write regardless of which Python process issued it,
  including a future script nobody remembers to migrate. **Cost/risk:**
  SQLite triggers can express "reject if `resolved` is already 1"
  reasonably cleanly, but expressing the *ranking* logic (B) — "accept
  if proposed evidence_source outranks stored evidence_source, else
  reject, except silently accept if values match" — inside trigger SQL is
  awkward and hard to keep in sync with the ranking table living in
  Python (A). A trigger also has no legitimate way to let the canonical
  function itself write (it would need to distinguish "the sanctioned
  path" from "everyone else," which SQLite has no session-scoped
  mechanism for beyond fragile conventions like a temp table flag). **Not
  recommended as the primary mechanism for this reason, but adopted as a
  defense-in-depth backstop specifically for the `resolved`-can't-flip-back-to-0
  case and for requiring the `resolution_recorded_at` co-write**, both
  simple enough to express as plain triggers without needing the ranking
  table at all — built, tested at production scale in an isolated scratch
  DB, and sequenced into G (`c75a906`, Q3). **A residual limitation, named
  rather than left to be discovered later: `INSERT OR REPLACE` bypasses
  `BEFORE UPDATE` triggers entirely.** SQLite implements it as an atomic
  delete-then-insert, not an update — confirmed by direct test (`c75a906`
  Q3d): neither trigger fires, and a `resolved=1` row can be silently
  reset to `resolved=0` via this statement shape with no interception at
  all. **Not a live risk today** — checked against all 13 writers; none
  use `INSERT OR REPLACE` on `markets` (creation paths use
  `INSERT OR IGNORE`, resolution paths use plain `UPDATE`) — but a
  **permanent** hole in the trigger layer for any future writer that does.
  See E for how this interacts with the invariant's own coverage gap.
- **Import-time / module-privacy guard** (e.g., only the canonical
  module holds a connection with write permission to `markets.resolved`,
  everyone else gets a restricted view). **Cost/risk:** SQLite has no
  native column-level or row-level permission system to build this on;
  approximating it (a wrapper connection class that inspects outgoing SQL
  in Python before passing it to the real connection) is really the same
  idea as the allowlist, just moved into a shared library instead of the
  agent-loop file — feasible, but it only helps if **every** writer is
  required to obtain its connection through that wrapper, which is a
  much larger architectural change than this cluster's scope (every raw
  `sqlite3.connect()` call in all 13 writers would need to change).
- **Static-analysis / CI lint rule, extending the pattern this codebase
  already has.** **Recommended.** `scripts/check_canonical_definitions.py`
  already exists, already runs as `daily_maintenance.py` step 8
  (currently non-blocking, per this session's own earlier Task-A
  finding that it fails daily) — it is, in spirit, exactly this kind of
  check for a different domain (hardcoded ELO thresholds instead of the
  canonical `column_definitions.py` constants). A parallel check —
  regex or `ast`-based, scanning for `UPDATE\s+markets\s+SET\s+.*\b(resolved|winning_outcome|resolution_date)\b`
  outside `mark_market_resolved()`'s own module — is a small, incremental
  addition to a pattern already in daily use, not a new architectural
  layer. **Cost:** low to build (a few hours' worth of code, similar
  scope to `scan_write_paths.py` built this session), but it is a
  **commit/CI-time** check, not a runtime one — a script that's already
  deployed and simply never re-linted (or a one-off manual `sqlite3`
  shell command run by a human) would not be caught. **Named honestly as
  a real limitation, not glossed over** — this is prevention for *new or
  modified* code, and detection (E's invariant) is what catches anything
  that slips through it at runtime, which is exactly why the design
  specifies both, per Oscar's direction 3, rather than treating either as
  sufficient alone.

---

## G. Migration sequence

Following the ELO arc's own staging discipline — every step individually
reversible, every step verified before the next, output-neutral before
anything behavior-changing.

| Stage | What moves | Verification before proceeding | Reversible how |
|---|---|---|---|
| **0** | Add the 3 new columns (D) + build `mark_market_resolved()` (C), unused by anything yet. **Also create `trg_resolved_no_unresolve`** — see below. No writer touched. | Schema migration applies cleanly; new columns nullable, no existing reader affected (confirm via `run_tests.py`, same non-tautological standard as this session's clobber fix). Trigger tested in an isolated scratch DB, not production, prior to this stage (`c75a906`, Q3) — confirmed to break none of the 13 writers, since every establishing writer's candidate query already requires `resolved=0`. | `DROP COLUMN` / revert the migration commit — nothing depends on the columns yet. Trigger: `DROP TRIGGER`. |
| **1** | Migrate **#11 `hydrate_stub_markets.py`** first — already the most conservative writer in the cluster (fill-only-if-empty on every column it touches), so subordinating it should be a pure no-op in observable output. | Before/after dry-run diff across its full candidate population — same methodology as this session's trade-evaluator repoint (§Part 3 of `2026-08-19-trade-evaluator-repoint.md`): zero behavioral difference expected, verify it. | `git revert` the one commit; #11 goes back to direct writes, harmless since the new columns stay empty for its rows either way. |
| **2** | Migrate **#3 `batch_update_resolved_markets`** — already carries this session's one-line COALESCE patch (`0a5891c`); folding it into the canonical function retires that patch in favor of the real mechanism. | Live, bounded, read-only dry-run against the known at-risk population — same 12-real-market methodology already proven in `2026-08-19-resolution-date-clobber-fix.md`. Confirm identical accept/reject decisions to the patched-but-not-yet-canonical version. | `git revert`; #3 reverts to its already-safe (COALESCE-guarded) direct-write state from Stage 2 of the prior fix — not back to the original unguarded version, since that commit stays in history. |
| **3** | Migrate **#4/#5/#6** (the 3 CLOB sibling passes) together — same file, same Rank-1 evidence tier. **First real exercise of cross-tier logic** (CLOB Rank 1 vs. the Rank-2 writers already migrated in Stages 1–2) — per A1's rank-timing wrinkle, expect this to fire routinely, not rarely. CLOB supplies `evidence_source="clob"` for the fact only; `resolution_event_time` is `None` from these writers (A2, `c75a906` Q1 — no CLOB field carries one), unless a Gamma cross-reference is added in the same call, which is not designed here. | Confirm via live dry-run that CLOB-sourced writes now out-rank any Rank-2 value already present from Stage 2, on real overlapping candidates if any exist. | `git revert`, same as above. |
| **4** | Migrate **#9/#10** (`resolve_legendary_markets.py` / `legendary_positions_scan.py`) — **the one confirmed same-rank collision pair (B)**. This is where flag-for-review becomes live-testable for real, not just designed. | Specifically construct or find a live case where both would fire on the same market and confirm: matching values → silent no-op; differing values → flagged, first-recorded value retained, disagreement logged. | `git revert`. |
| **5** | Migrate remaining dormant/one-off writers for completeness and to close the two **latent** overwrite risks the cluster doc identified (#1's ON CONFLICT branch, #2) — low urgency since none are live, but leaving them un-migrated would mean the Stage-6 promotion condition (zero non-canonical write sites) can never actually be met. **Also create `trg_require_recorded_at`** — see below. | `scan_write_paths.py` re-run confirms zero direct `UPDATE markets SET (resolved\|winning_outcome\|resolution_date)` statements remain outside the canonical module. Trigger: re-confirm in a scratch DB seeded from the now-migrated codebase's actual write shapes that every remaining writer's statement sets `resolution_recorded_at` (all should, since all now call `mark_market_resolved()`). | `git revert` per writer; each is independent. Trigger: `DROP TRIGGER`. |
| **6** | **Promote the invariant (E) from OBSERVE to Tier 1/CRITICAL** — gated exactly on Stage 5's `scan_write_paths.py` confirmation, per E's stated promotion condition. Bundled with Stage 5's trigger addition — both are gated on the identical fact (all 13 writers migrated) and address the same failure mode from complementary angles (E: SQL detects it after the fact; the trigger: prevents it outright at write time). | The promotion criterion **is** the verification for this stage — nothing further needed if Stage 5's census is clean. | Demote the tier back to 0; no data changes involved in this stage at all. |

**Triggers, tested and measured (`c75a906`, Q3) — not designed in the
abstract:**

```sql
-- Stage 0
CREATE TRIGGER trg_resolved_no_unresolve
BEFORE UPDATE OF resolved ON markets
WHEN OLD.resolved = 1 AND NEW.resolved = 0
BEGIN SELECT RAISE(ABORT, 'resolved cannot transition from 1 to 0'); END;

-- Stage 5
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

`trg_resolved_no_unresolve` is placed at Stage 0, not later, because it
was **verified to break no existing writer** — every establishing writer
in the cluster already requires `resolved=0` in its own candidate
selection, so none ever attempts the transition this trigger forbids; it
has no dependency on the canonical function or on any writer migration.
`trg_require_recorded_at` cannot move earlier than Stage 5: it was
**verified empirically, not assumed,** to reject every one of the 13
writers' current UPDATE shapes, because none of them set a column that
doesn't exist until Stage 0 and isn't populated by any of them until
their own migration — placed at Stage 5 alongside the last writers'
migration and bundled with Stage 6's invariant promotion since both share
the same gating fact.

**Performance, measured, not assumed:** 733,000 synthetic rows (matching
production's live `markets` row count), a representative 5,000-row
single-statement bulk `UPDATE`: **1.5ms absolute overhead with both
triggers active, ~27% relative** — against writers whose real per-market
cost is hundreds of milliseconds to seconds of network-bound API latency,
not the local SQLite write. Not a performance concern at any stage.

**Not included as a stage:** building the CI lint rule from F. **[D]**
That is prevention infrastructure, independent of any single writer's
migration — it can be built at any point after Stage 0 (once the
canonical module exists to check writes *against*) and doesn't block or
get blocked by the writer-by-writer sequence above. Named here so it
isn't lost, not sequenced into the table because it has no dependency on
writer migration order.

---

## H. What could go wrong

**Per stage, what breaks if the design is wrong — matching the "what
would break" discipline from the prior write-path census:**

- **Stage 0 (schema only):** wrong column types or a non-nullable
  constraint added by mistake would break every existing INSERT across
  all 13 writers immediately (they don't know the new columns exist) —
  this is why D specifies nullable, additive-only, and Stage 0's
  verification is exactly "confirm nothing existing breaks."
- **Stage 1–2 (low-risk migrations):** if the ranking model (A) is wrong
  in some way not yet surfaced — e.g., if `hydrate_stub_markets.py`'s
  fill-only-if-empty guard doesn't map cleanly onto "Rank 2 filling a
  null slot" the way this design assumes — the dry-run diff step exists
  specifically to catch that before Stage 2 changes anything with real
  overwrite stakes.
- **Stage 3 (CLOB migration):** **resolved, not outstanding.** The risk
  this document originally flagged — that the CLOB API might not expose
  an event-time field — is answered: it does not (A2, `c75a906` Q1,
  established by dumping the full response for two independent resolved
  markets and ruling out the one candidate field empirically). Stage 3
  supplies `evidence_source="clob"` for the resolution **fact** only;
  `resolution_event_time` passed to `mark_market_resolved()` from these
  writers will be `None` unless a Gamma cross-reference is performed in
  the same call, which this design does not specify. This is expected
  behavior under the corrected A2 ranking, not a gap to investigate
  further at Stage 3 — the checking has already happened, at design time,
  not deferred to migration time.
- **Stage 4 (tie case goes live):** if the flag-for-review log/audit
  surface is never actually looked at by anyone, this stage silently
  degrades to "first-wins, no-op on disagreement" in practice — the same
  as today, just with better bookkeeping nobody reads. **[D]** Not a
  design flaw, but worth naming: flag-for-review only delivers value if
  something consumes the flag.
- **The `resolution_date`-NULL risk, checked against a real downstream
  consumer, not assumed:** the alternative design (leave `resolution_date`
  NULL whenever no true event-time is known, rather than D's write-time
  fallback) was considered and **rejected specifically because**
  `requeue_resolved_market_traders.py`'s `resolution_date > ?` filter (per
  the O-17 commit message, `85965c5` cites it directly) depends on
  `resolution_date` being **non-null** on every resolved market to queue
  traders for P&L recalculation. Leaving it NULL for write-time-only
  writers would silently reintroduce the *symptom* O-17 fixed (traders
  never requeued) via a different mechanism (no event-time known, vs.
  O-17's "column simply never written") — a genuinely non-obvious
  consequence, caught by checking the actual downstream reader rather
  than designing the schema in isolation.

**Writers whose current behavior the design cannot express — checked
explicitly, per the task's instruction that this would be a finding, not
a failure:**

- **None of the 12 fact-establishing writers (#2–#13) are inexpressible.**
  Every one supplies (or, per G, could be made to supply) an evidence
  source from A1/A2's enum, a winning_outcome-or-explicit-no-winner, and
  either a true event-time or none.
- **#1a (`store_market_from_trade`) does not need to be expressed** —
  it never asserts a resolution fact (`resolved=False` always, no
  `winning_outcome`), it's INSERT-time stub initialization. Correctly
  outside `mark_market_resolved()`'s scope, not a gap.
- **#1b (`store_market_dict`) is a genuine partial fit, named as such —
  and now checked empirically rather than left as a plausible concern
  (`c75a906`, Q2):** it currently passes `resolved` from Gamma's
  `closed`/`archived` flags but hardcodes `winning_outcome=None`
  regardless, even though a winner is structurally extractable from the
  same Gamma object already in memory — a genuine discard in the code.
  **But the live database shows zero currently-observable instances of
  the failure shape this would produce** (`resolved=1,
  winning_outcome=NULL` with `data_source='live_monitoring'`): all 123
  rows in that state trace to one unrelated, already-known backfill
  (`gamma_backfill_tier2_2026-07-06`), none to this path. **[I]** Most
  plausibly because `store_market_from_trade` (#1a)'s continuous
  trade-tape-driven discovery usually creates a market's stub (with
  `resolved=False`, no discard possible) before #1b's ~2.5-hourly
  category scan would independently reach it, and because
  `hydrate_stub_markets.py`'s own fill-only-if-empty guard (candidate-gated
  on `resolution_date IS NULL`, not on `resolved` status) plausibly
  self-heals the rare row that does slip through, without needing to know
  #1b's gap exists. **Confirms this is a genuine footnote, not a
  reprioritization case** — checked, not merely asserted. Under this
  design it *could* call `mark_market_resolved()` with a real
  winning_outcome if one is extractable — still a natural follow-on, not
  implemented here (writers are out of scope for this task).
- **`monitor.py`'s proxy writes are correctly excluded, not
  accommodated** — per the prior doc's own Q5 (`85965c5`), these answer a
  different question (estimate an upcoming deadline) and folding them
  into `mark_market_resolved()` would blur the exact distinction this
  whole design exists to make explicit. They remain a separate, direct
  write path, unguarded by this design, exactly as decided in the prior
  document — restated here rather than silently dropped.

---

## Summary — what each of the 13 writers becomes

| # | Writer | Becomes under the design |
|---|---|---|
| 1 | `update_market()` (ON CONFLICT branch) | Its live callers (1a, 1b) never reach this branch and stay INSERT-only, unchanged. The branch itself would call `mark_market_resolved()` for the `resolved`/`winning_outcome`/`resolution_date` fields on the rare/latent path where it fires on an existing row, instead of `excluded.*` unconditional assignment — closes the one latent overwrite risk the cluster doc named for this writer. |
| 1a | `store_market_from_trade` | Unchanged — never asserts a resolution fact, out of scope. |
| 1b | `store_market_dict` | Unchanged behaviorally in this design's minimum scope; a natural follow-on (not implemented here) would let it call `mark_market_resolved(evidence_source="gamma")` with a real winner when extractable, instead of hardcoding `None`. |
| 2 | `update_market_resolution()` | Migrated in Stage 5 for completeness (dormant, no live caller) — becomes a thin wrapper calling `mark_market_resolved(evidence_source=<caller-supplied, now required>)`. |
| 3 | `batch_update_resolved_markets` | Migrated in Stage 2. Calls `mark_market_resolved(evidence_source="gamma", resolution_event_time=None)` — the COALESCE patch from this session's prior fix is retired in favor of the canonical function's own guard logic. |
| 4–6 | The 3 CLOB passes | Migrated in Stage 3 as a batch. Call `mark_market_resolved(evidence_source="clob", resolution_event_time=None, ...)` — first real exercise of Rank-1 evidence in the canonical path, expected (per A1's rank-timing wrinkle) to routinely outrank an already-present Rank-2 value; `resolution_event_time` is always `None` from these writers since CLOB carries no timestamp field (A2, `c75a906` Q1, closed). |
| 7–8 | `backfill_o16_tier1/tier2` | Already-run, dormant — migrated in Stage 5 for completeness only. Would call `mark_market_resolved(evidence_source="gamma", resolution_event_time=<true API timestamp>, allow_no_winner=True)` for the sentinel case — the one writer whose event-time discipline was already correct, now made structural instead of a per-writer convention. |
| 9–10 | `resolve_legendary_markets.py` / `legendary_positions_scan.py` | Migrated in Stage 4 — the tie-case pair (B) becomes live for the first time. Both call `mark_market_resolved(evidence_source="gamma")`. |
| 11 | `hydrate_stub_markets.py` | Migrated first, Stage 1. Its fill-only-if-empty discipline for `resolved`/`winning_outcome`/`resolution_date` becomes exactly what "propose, defer to existing" already means under source-ranking — its category/title-filling logic (a different concern) stays separate, untouched. |
| 12 | `fetch_market_resolutions.py` | Dormant, no live caller — migrated in Stage 5. Would call `mark_market_resolved(evidence_source="clob")`. |
| 13 | `fix_expired_unresolved.py` | Dormant, narrow (10 hardcoded markets), already run — migrated in Stage 5 for completeness. Calls `mark_market_resolved(evidence_source="manual_verified", evidence_detail=<the hardcoded market list's context>)`. |
| — | `monitor.py`'s proxy writes | **Unchanged, explicitly out of scope** — answers a different question (Q5, prior doc), stays a separate write path. |

---

*Generated 2026-08-19. Sources: `2026-08-19-market-resolution-write-cluster.md`
(`85965c5`, all 13-writer facts cited from there), `2026-08-19-write-path-census.md`,
`trading-swarm/orchestrator/ollama_agent_loop.py` (full read of the
allowlist mechanism), `2026-07-06-elo-arc-design-FABLE.md` (invariant #3
and the Stage 0–5 staging discipline this design follows),
`2026-08-19-resolution-date-clobber-fix.md` and
`2026-08-19-trade-evaluator-repoint.md` (verification methodologies
referenced for the migration sequence's own verification steps). No code
written, no schema changed, no writer modified, no invariant built. This
is a specification for review.*

---

*Amended 2026-08-19 (later pass): folded in the three open questions
resolved by `2026-08-19-canonical-design-open-questions.md` (`c75a906`).
A2's "CLOB event-time, currently unpopulated" row deleted as a closed
negative (no CLOB field carries a resolution timestamp, established by
dumping the full response for two independently-sampled resolved markets
and empirically ruling out the one candidate field against tape_end) and
replaced with a stated structural fact — the fact-authority source (CLOB)
and timestamp-authority source (Gamma) are permanently different, not a
gap Stage 3 might close. A1 gained the rank-timing wrinkle (a Rank-2
value can and will routinely arrive before the Rank-1 source populates
for the same market — expected, frequent operation of the ranking logic,
not an anomaly). G gained two tested triggers at two stages:
`trg_resolved_no_unresolve` at Stage 0 (verified to break no existing
writer) and `trg_require_recorded_at` at Stage 5, bundled with the Stage
6 invariant promotion (verified empirically to break all 13 writers
pre-migration, and measured at negligible performance cost — 1.5ms
absolute overhead on a 5,000-row bulk update at production's 733,000-row
scale). E and F gained the `INSERT OR REPLACE`-bypasses-triggers finding
and its architectural consequence: the invariant and the Stage-5 trigger
now close most of each other's admitted blind spots, except the one
statement shape (`INSERT OR REPLACE` omitting the new columns) both still
miss simultaneously — not a live risk today, named rather than left to be
discovered later. H's Stage 3 entry and #1b entry updated from
open-question framing to resolved findings — the CLOB risk is closed, and
#1b's discard, while real in code, produced zero observable live
instances, confirming (not merely asserting) the design's original
footnote treatment. Oscar's four directions are unchanged; no
restructuring. Sources: `2026-08-19-canonical-design-open-questions.md`
(`c75a906`), which cites its own live-call and scratch-DB evidence in
full.*
