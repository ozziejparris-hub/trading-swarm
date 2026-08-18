# 2026-08-18: recomputing the LEGENDARY overlap statistic against the canonical gate

Read-only on the DB. The six hardcoded sites were not modified, nothing was
repointed to `cd.LEGENDARY_GATE_WHERE`, and the master handover was not
edited. Measurement only. Every claim below is tagged **[V]** (verified —
command/query/file:line given) or **[I]** (inferred/plausible, explicitly
marked). Unverifiable points are stated in place with what would settle
them, per the standing project instruction (memory:
`feedback_verify_dont_propagate.md`).

Committed script: `scripts/characterize_legendary_overlap_recompute.py`
(first-repo, commit `fd9e329`). Re-run: `python3
scripts/characterize_legendary_overlap_recompute.py`. Writes a timestamped
JSON artifact to `data/characterizations/`. Today's run:
`data/characterizations/legendary_overlap_recompute_20260818T192510Z.json`.

## Background claims, checked before use

- Six sites, identical hardcoded `geo_elo >= 2175`, all classified REPORTING
  (not FILTERING) — **[V]** already established read-only in
  `2026-08-17-legendary-gate-drift-probe.md` (per-site table, git blame, AST
  drift-check mechanism); re-confirmed today by re-reading all six files
  directly (`grep -n "geo_elo\s*>=\s*2175" scripts/trader_skill_metric_v2*.py`
  → exactly six matches, same statement). Not re-litigated per-site here —
  that document already did the individual verification this task's
  background section describes as established.
- Canonical predicate text — **[V]** `monitoring/column_definitions.py:123-128`,
  read directly: `geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND
  research_excluded = 0 AND bot_type IS NULL`. Matches the prompt's
  transcription exactly.
- 15/81 figure, attributed to `MASTER_HANDOVER_2026-08-15.md` §1 — **[V]**
  line 118 (per the 08-17 probe's own grep, re-checked): *"LEGENDARY overlap
  with the new metric's equivalent tier: 15/81 (18.5%). The current
  production tier has little in common with what a defensible metric calls
  the top tier."*
- §6.1 cutover framing — **[V]** the handover has no literal "§6.1" heading;
  it is item 1 of the numbered "## 6. OPEN ITEMS" list (line 239): *"Cutover
  decision — does the new metric replace `geo_elo` in production? **Not
  made.** Requires its own pre-registration and a before/after on cohort
  membership."* Matches the prompt's framing.
- The cohort side of the statistic, `intersection_traders` — **[V]** v2f.py
  computes it at line 377 (sig-95 AND M≥10 AND shrunk edge≥0.02) and prints
  the LEGENDARY overlap against it at line 385:
  `overlap with LEGENDARY: {len(intersection_traders & legendary)}/{len(legendary)}`
  — note the denominator is `len(legendary)`, not `len(intersection_traders)`.
  This exact set is persisted, unchanged since the 2026-08-15T19:36:56Z run
  (commit `eaeabbc`), in `metric_v2f_intersection_cohort` (295 rows) — used
  directly rather than recomputed, since re-running the full EB-shrinkage
  pipeline is out of scope for a measurement-only task and would not change
  this set (nothing has re-persisted to that table since).

## Q1 — reproduce the wrong number first

**[V] Reproduces exactly: 15/81 (18.5%).** `n_legendary_inflated = 81`,
`overlap = 15`, both computed live against `traders WHERE geo_elo >= 2175`
joined to the persisted 295-trader cohort. No discrepancy to attribute to
drift — the count matches the handover's figure precisely, today, three
days later.

One limitation, stated rather than smoothed over: **[U]** this confirms the
*count* is unchanged, not that the *same 15 traders* make up the overlap —
no ID list for the original 15/81 was persisted in the 08-15 handover or
the 08-17 probe, so a literal identity check against that date isn't
possible. What would settle it: nothing, retroactively — the door on that
check closed the moment it wasn't persisted at write time. Today's run
*does* persist the 15 trader IDs (`overlap_traders_inflated` in the JSON
artifact), so this will be diffable going forward.

## Q2 — compute the correct number

**[V] 3/10 (30.0%).** `n_legendary_canonical = 10`, `overlap = 3`, computed
against `traders WHERE geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND
research_excluded = 0 AND bot_type IS NULL`, joined to the same 295-trader
cohort. Overlap trader IDs persisted in the artifact
(`overlap_traders_canonical`).

## Q3 — decompose the difference

**[V]** Of the 81 inflated-set traders, computed by evaluating each of the
four canonical conditions independently against that fixed base set:

| Condition | Traders failing it (of 81) | Share |
|---|---|---|
| `geo_elo_active < 2175` (time-decay) | **69** | 85.2% |
| `geo_accuracy_pool != 1` | 21 | 25.9% |
| `research_excluded != 0` | 4 | 4.9% |
| `bot_type IS NOT NULL` | 1 | 1.2% |
| **Fails at least one (= excluded by canonical)** | **71** | 87.7% |
| Fails ≥2 conditions simultaneously | 20 | 24.7% |

`81 − 71 = 10`, cross-checked directly against the independently-computed
canonical count (10) — consistent.

**The dominant driver is time-decay, not the three added filters.**
Geo-ELO time-decay alone (`geo_elo_active < 2175` despite `geo_elo ≥ 2175`)
removes 69 of the 81 — i.e. most of the inflated set is traders whose
*raw*, never-decaying ELO still shows LEGENDARY-tier but whose
*activity-decayed* ELO has fallen below the bar, which is exactly the
"overstates dormant traders' tier indefinitely" failure mode the canonical
module's own comment (`column_definitions.py:120-122`) names as the reason
`geo_elo_active` exists. The other three conditions (accuracy-pool
membership, research exclusion, bot exclusion) matter — accuracy-pool alone
removes 21 — but are secondary to the decay effect in this population.

## Q4 — direction and meaning

**[V] The corrected figure weakens the handover's claim; it does not
overturn it.**

The printed statistic's fraction very nearly *doubles* under the canonical
gate: 18.5% (15/81) → 30.0% (3/10). Read plainly, the new metric's
intersection cohort agrees with a *larger share* of the true LEGENDARY tier
than the inflated computation reported — the opposite direction from what
would be needed to strengthen "little in common."

That said, the qualitative claim — that most of LEGENDARY is *not* in the
new metric's top intersection cohort — still holds under the corrected
number: 7 of 10 canonical LEGENDARY traders (70%) are absent from the
295-trader cohort, versus 66 of 81 (81.5%) under the inflated one. The
handover's *direction* of argument survives; its *magnitude* does not — 30%
overlap is meaningfully less dramatic than 18.5%, and Q5 below adds a
reason to distrust either figure's precision at this population size.

**[I]** Not the printed statistic, but worth noting as context: measured the
other way (overlap as a share of the 295-trader cohort rather than of the
LEGENDARY set), the numbers are 15/295 = 5.1% vs 3/295 = 1.0% — smaller in
absolute cohort terms either way. This wasn't the handover's chosen framing
and isn't a replacement finding, just a sanity check that the "which
direction did it move" conclusion doesn't flip under the other reasonable
denominator (it doesn't — 5.1%→1.0% also shows the *canonical* set is a
much smaller anchor, consistent with Q5's stability point, not a reversal
of Q4's fraction-rose finding, since that's the LEGENDARY-denominator
version specifically).

## Q5 — is the corrected figure itself stable

**[V] No — it is a point-in-time figure that will drift, and should not be
quoted without an as-of timestamp.** The mechanism is verified directly:
`geo_elo_active` is defined to decay with inactivity (`column_definitions.py`
comment, confirmed above), so the canonical LEGENDARY set's membership
changes continuously even with zero code or DB-write activity — a trader
crossing 2175 downward on any given day moves in or out of the denominator
with no discrete "event" to log.

**[I]** The practical consequence is more severe than for the inflated
figure, precisely because the corrected population is so much smaller:
n=10 means each single trader crossing the threshold moves the reported
percentage by 10 points, and each single trader entering or leaving the
overlap moves it by up to 33 points (1/3). The inflated 81-trader
denominator is comparatively stable by sheer size; the canonical 10-trader
one is not, structurally, regardless of what the true rate is. This is
inferred (no repeated measurements exist yet to observe actual drift) but
follows directly from the verified n=10 denominator.

**As-of date: 2026-08-18T19:25:10Z** (script `generated_at`, UTC). Any
future reference to "3/10" without this timestamp should be treated the
same way this task treated the un-dated 15/81 in the original prompt —
as a claim to re-verify, not a fact to propagate.

## Q6 — cutover relevance

Describing only, per the task's explicit instruction not to compute the
cutover analysis here.

**[V]** The handover's open item 1 (informally "§6.1") states the cutover
decision requires "its own pre-registration and a before/after on cohort
membership," and is explicitly **not made**.

**[I]** What this recomputation implies for that future pre-registration:
whatever "before" reference population is chosen for a before/after
cohort-membership comparison should be the canonical LEGENDARY set (n=10,
verified `cd.LEGENDARY_GATE_WHERE`), not the inflated one (n=81) any of the
six REPORTING sites would hand back if queried naively — using the inflated
set as "before" would compare the new metric's cohort against a population
that is itself already known to include dormant/excluded/bot traders that
no defensible tier definition would count. **[I]** Separately, and
independent of which set is chosen: n=10 is a very small "before"
population for any statistical before/after comparison — Q5's instability
point means a pre-registration built on this reference set should
anticipate that its own baseline will have shifted by the time an "after"
measurement is taken, and should decide up front (as the project's own
pre-registration discipline requires) how much movement in the n=10
reference set is treated as noise versus signal, before running the
comparison. This task does not attempt that pre-registration — it is
Oscar's call per the handover's own division-of-labour note (line 32), not
a finding to assert here.

## Reproducibility

`scripts/characterize_legendary_overlap_recompute.py` (first-repo, commit
`fd9e329`) computes both figures and the decomposition in one run, reading
the cohort from `metric_v2f_intersection_cohort` (not recomputed) and the
two LEGENDARY sets live from `traders`. Output:
`data/characterizations/legendary_overlap_recompute_20260818T192510Z.json`,
committed alongside the script. Re-running later will produce a new
timestamped artifact rather than overwriting this one, so drift in either
figure becomes diffable going forward — closing the same gap Q1 flagged
retroactively for the original, unpersisted 15/81.
