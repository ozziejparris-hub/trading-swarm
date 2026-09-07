# Stranded-Markets Defect — Figure Reconciliation

**Scope:** read-only. Locates the origin of the `last_checked`-stranding
defect's headline figures (195,625/214,413 markets; 8,077 open positions;
1,983 distinct traders — `MASTER_HANDOVER_2026-09-05.md` §6, sourced from
`2026-08-30-canonical-writer-column-gap.md`), establishes whether they are
reproducible, and — regardless of the answer — ships a committed,
parameterised, re-runnable script (first-repo
`scripts/characterize_last_checked_stranded_markets.py`) that measures the
defect's current scope going forward with persisted membership. No fix, no
backfill, no writer touched. This is the fourth unreproducible
decision-carrying number in this project (after the B3 9/8 scoping, the
28-formation retest, and v2's first raw count) — per
[[feedback_reproducibility_decision_numbers]], this doc exists to close that
pattern for the largest open defect on the list, not to re-litigate it.

Tagging: [V]=verified this session (code/query read or run directly),
[I]=inferred, [U]=undetermined — evidence does not distinguish.

---

## VERDICT

**The recorded 8,077/1,983 figure is (c) unreproducible by construction.**
Neither of the two decision docs that produced it (`9041ab8`, `96be474`)
committed a script or persisted a market/trader ID list; both are narrative
`[V]` tags meaning "read directly this session," not "re-runnable by anyone
else." Part 1 stops there per the task's own instruction.

**Part 2 ships a committed, parameterised, self-checking replacement**
(first-repo, this session): population 216,499 clob-resolved markets,
196,764 (90.9%) stranded, 8,831 open positions, **1,168** distinct affected
traders — all four counts backed by a persisted JSON artifact carrying the
full market-ID and trader-address lists, so this exact question cannot recur
against *this* script's output.

**Part 3 does not resolve the trader-count anomaly.** Markets and positions
both show smooth, monotonic growth across all three measurements taken over
the last eight days (population, stranded-market-count, and open-position-
count all only ever increased). Distinct-trader-count did not: 594 → 1,983 →
**1,168** — up, then down. I tested every predicate variant named in the
task prompt (open-only vs. any-status vs. open+partially_closed vs.
distinct-via-trades-table) and **none reproduces 1,983** — the nearest
alternative (open+partially_closed) gives 1,364, still off by 619. **[U]
Undetermined**: the evidence available today (a single live snapshot, no
persisted membership from 2026-08-30) cannot distinguish a genuine-churn
explanation from an unidentified methodology difference in the original
count. Reported as such, not resolved into the more plausible-sounding one.

---

## PART 1 — Locating the original

### 1.1 Where the figures came from [V]

Two trading-swarm decision docs, same day (2026-08-30), same narrative
pattern:

| Doc | Commit | Figure | Population |
|---|---|---|---|
| `2026-08-30-end-to-end-verification.md` §3a/§4b | `9041ab8` | 4,991 positions / 594 traders | 195,228/214,016 stranded |
| `2026-08-30-canonical-writer-column-gap.md` §2.1/§4c | `96be474` | 8,077 positions / 1,983 traders | 195,625/214,413 stranded |

Both commits are **doc-only** — confirmed by `git show --stat` on each:

```
9041ab8  .../2026-08-30-end-to-end-verification.md      | 330 +++++++++
96be474  .../2026-08-30-canonical-writer-column-gap.md   | 357 +++++++++
```

No `.py`, `.sql`, or `.json` file accompanies either commit. Neither
document contains a SQL code block, a script invocation, or a file path for
the query that produced these four numbers — the only code block in either
document is `mark_market_resolved()`'s six-column `UPDATE` statement, quoted
for a different point (§1.1 of the 08-30 gap doc).

### 1.2 Is it re-runnable? **No.** [V]

- **No committed script.** Searched both repos (`grep -rl "195625\|195,625\|stranded"` across `.py`/`.md`/`.json/.sql`) — only the decision docs and downstream summaries that quote them ever mention these figures. `first-repo` has no hits at all outside this session's new script.
- **No persisted membership list.** The 2026-08-30 commit window's only data artifact (`first-repo 3d369c5`, same day) persists the *geo/elec pending-trade backlog* — a different characterization entirely, not this one.
- **The population definition is stated precisely enough to approximate** ("214,413 total **clob-resolved** markets," i.e. `resolved=1 AND resolution_evidence_source='clob'`) **and the stranded predicate is stated precisely enough to approximate** (`last_checked` ≤ "the pre-sweep baseline, 2026-08-14") — both narrative, both exact enough to write code against.
- **The "open position" and "affected trader" definitions are NOT stated at all** — no column, no status value, no join shape named anywhere in either document. The closest thing to an authoritative definition is the actual consumer script the defect is *about* — `scripts/requeue_resolved_market_traders.py:113` (`WHERE status = 'open'`) and its two-step join shape (`:106-115`) — but there is no evidence either decision doc actually reused that code path rather than writing an independent ad-hoc query.

**Finding: the original is not re-runnable.** No committed script, no
persisted membership, and the two counts most in question (positions,
traders) have no stated predicate at all. Per the task's own instruction,
Part 1 stops here — Part 2 proceeds as a fresh measurement, not a
reconciliation.

---

## PART 2 — Fresh measurement, from a committed script

**Script:** `scripts/characterize_last_checked_stranded_markets.py`
(first-repo, this session, uncommitted as of this doc — see §Reproducibility
below for the commit this doc's own figures are pinned to once committed).

**Exact predicates, as stated in the script (not narrated here):**

```
POPULATION_WHERE = "m.resolved = 1 AND m.resolution_evidence_source = 'clob'"
STRANDED         = POPULATION_WHERE + " AND datetime(last_checked) <= datetime(baseline)"
                   # baseline defaults to 2026-08-14T00:00:00, the doc's stated pre-sweep cutoff
OPEN POSITION    = "positions.status = 'open'"
                   # identical to requeue_resolved_market_traders.py:113's own predicate
AFFECTED TRADER  = DISTINCT positions.trader_address
                   JOIN positions.market_id = markets.market_id
                   WHERE STRANDED AND status = 'open'
```

**Run, `--selfcheck` enabled** (2026-09-07T17:01:43Z):

```
[selfcheck] JOIN-style traders: 1168  IN-list-style traders: 1168  match=True
[selfcheck] PASSED: exact match, as expected for two equivalent SQL formulations
[selfcheck] stranded (196764) is a subset of population (216499): OK
population=216499 stranded=196764 (90.9%) open_positions=8831 affected_traders=1168
```

The selfcheck recomputes the affected-trader set two independent ways — a
direct SQL `JOIN` (the script's primary path) and the literal two-step
IN-list shape `requeue_resolved_market_traders.py` itself uses (market IDs
fetched first, then queried against `positions` via `market_id IN (...)`) —
and asserts an exact match. Both are pure SQL with no randomness; a
mismatch would be a real bug, not noise. They matched.

**Figures:**

| Metric | Value | Predicate |
|---|---|---|
| Population | 216,499 | `resolved=1 AND resolution_evidence_source='clob'` |
| Stranded markets | 196,764 (90.9%) | population AND `last_checked` ≤ 2026-08-14T00:00:00 |
| Open positions | 8,831 | `positions.status='open'`, joined to stranded markets |
| Affected traders | **1,168** | DISTINCT `trader_address` on the above |

**Artifact:** `data/characterizations/last_checked_stranded_markets_20260907T170143Z.json`
— persists `stranded_market_ids` (196,764 IDs), `open_position_ids` (8,831
IDs), and `affected_trader_addresses` (1,168 addresses) in full, plus
`generated_at`, `db_path`, and the exact predicate strings. Anyone (or any
future script) can now diff this exact membership against a later run
without narrating anything.

**No re-runnable original exists to run side-by-side** (Part 1). The table
below is the only side-by-side available: this script's output against the
two narrated readings, in trend order.

| Reading | Date | Population | Stranded | Open positions | Traders |
|---|---|---|---|---|---|
| Prior verification (`9041ab8`) | 2026-08-30, early | 214,016 | 195,228 (91.2%) | 4,991 | 594 |
| Column-gap doc (`96be474`) | 2026-08-30, later, same day | 214,413 | 195,625 (91.2%) | 8,077 | 1,983 |
| This script | 2026-09-07 | 216,499 | 196,764 (90.9%) | 8,831 | **1,168** |

Population and stranded-market counts move smoothly and monotonically
across all three readings, consistent with the "continuously growing, live
monitor keeps writing against already-stranded markets" description in both
source docs. Open positions also move monotonically. Distinct traders does
not — see Part 3.

---

## PART 3 — The trader-count drop

**The anomaly, restated precisely:** across the three readings above, open
positions rose monotonically (4,991 → 8,077 → 8,831) while distinct
affected traders did not (594 → **1,983** → **1,168**) — up sharply, then
down by ~41% against the last-known reading, over roughly eight days.

### 3.1 What was tested [V]

Every candidate the task named, run directly against today's DB (not
theorized):

| Variant | Traders | Positions | Matches 1,983? |
|---|---|---|---|
| `status='open'` only (this script's definition) | 1,168 | 8,831 | No |
| `status IN ('open','partially_closed')` | 1,364 | 9,314 | No — nearest, still off by 619 |
| any `status` (open + partially_closed + closed) | 38,165 | 1,994,326 | No — off by more than an order of magnitude |
| distinct `trader_address` via `trades` table (any trade on a stranded market, not positions) | 39,543 | n/a | No |

**None of the four reproduces 1,983.** The "any status" and "via trades"
variants are so far off (38,165 and 39,543) that they can be ruled out as
*the* explanation for the original figure with reasonable confidence — the
original was almost certainly not counting an unrestricted population this
large. The two closer variants (`open` alone: 1,168; `open`+
`partially_closed`: 1,364) bracket the plausible range but neither lands on
1,983, and 1,983 sits **above both**, not between them and some other
tested value — i.e., no simple status-predicate relaxation closes the gap;
if anything, relaxing the predicate moves in the wrong direction relative
to today's figures, since 1,983 is further from today's 1,168 than
1,364 is.

### 3.2 What is structurally true, but doesn't resolve it [V]

Position-count concentration among a small number of high-volume traders is
real and large: today's top 3 traders alone hold 645, 545, and 388 open
positions respectively on stranded markets — 1,578 of 8,831 (17.9%) from
just three addresses. 462 traders hold exactly one open position each. This
kind of concentration means position-count and trader-count are not
required to move together: a handful of high-frequency traders opening new
positions in newly-stranding markets can drive position-count growth
independent of whether the *number of distinct traders* in the set is
rising or falling, if lower-volume traders are simultaneously entering and
exiting the set via ordinary trading activity (a position closes via an
organic SELL regardless of the `last_checked`/requeue defect — that defect
only blocks the `pnl_last_updated` **signal**, not FIFO position-closing
itself).

**This is a real, verified structural fact about today's population. It is
not evidence about what happened between 2026-08-30 and today**, because no
membership snapshot exists from 2026-08-30 to check whether the traders
who dropped out actually did so via organic closes, versus the 1,983 figure
having been computed under a materially different (and unstated) method.

### 3.3 Verdict on Part 3 — [U] undetermined, stated plainly

**The evidence does not distinguish between:**
 (a) the original 1,983 was computed under a query this session did not
     manage to reconstruct (candidate predicates tested above do not
     reproduce it), or
 (b) genuine trader churn occurred — plausible given the concentration
     structure in §3.2, but unconfirmed, because no 2026-08-30 trader-ID
     list was ever persisted to diff against (Part 1's finding).

This doc does **not** pick (a) or (b) as more likely. Both remain open.
Going forward, this question cannot recur in this form: this session's
script persists the full trader-address list, so the next reading can be
diffed directly against `last_checked_stranded_markets_20260907T170143Z.json`
rather than against a narrated number.

---

## What was NOT determined

- Whether the original 195,625/214,413 market-level figures used *exactly*
  this script's predicate, or a compatible-but-different one that happens
  to produce a similar smooth trend. The market-level trend across three
  readings is consistent with a shared methodology but this is
  circumstantial, not confirmed — no 2026-08-30 market-ID list exists to
  diff against either.
- Whether the 1,983-trader figure reflects a real population this script's
  definition doesn't capture, a transcription/computation artifact in the
  original ad-hoc query, or genuine week-over-week churn. See §3.3.
- Whether the `open+partially_closed` variant (1,364) is closer to "correct"
  than `open`-only (1,168) as the operationally right definition of
  "affected trader" — both are defensible; this doc did not choose one as
  canonical beyond noting `open`-only matches `requeue_resolved_market_traders.py`'s
  own existing code exactly, which is why the committed script uses it.
- Any assessment of whether remediating this defect is safe or how to
  batch it — out of scope per the task, Oscar's to decide.

---

## Reproducibility

- Script: `scripts/characterize_last_checked_stranded_markets.py` (first-repo
  `52cfa39`, this session).
- Artifact: `data/characterizations/last_checked_stranded_markets_20260907T170143Z.json`,
  persisting `stranded_market_ids` (196,764), `open_position_ids` (8,831),
  `affected_trader_addresses` (1,168), plus generating parameters
  (`baseline`, all three predicate strings, `db_path`, `generated_at`).
- `--selfcheck` passed (two independent SQL formulations of the
  affected-trader query, exact match).
- Full suite run via `python run_tests.py` (not bare pytest), 2026-09-07:
  20 files, 19 passed, 1 failed (`test_backtest_window_population.py`) —
  pre-existing, unrelated to this task, same failure signature as every
  daily-maintenance run this week; not investigated further here.
