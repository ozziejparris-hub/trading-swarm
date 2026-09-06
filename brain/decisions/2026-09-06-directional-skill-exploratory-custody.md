# Directional Skill — Exploratory-Result Custody + Persistence Pre-Registration

Closes the retrospective arc. Part 1 (this document): custody and
characterisation of the 2026-09-06 PIT-pool/power-estimate figures
(first-repo `4feb97f`, trading-swarm `00fa294`), which are **EXPLORATORY**
and **NOT pre-registered** — a by-product of a clustered-bootstrap power
estimate, not a planned test. They do not supersede, amend, or touch the
result of record (`+0.0316`, CI `[-0.0088, +0.0710]`, n=3,032/120,
`metric_v2f_oos_result`), which stands permanently per Oscar's 2026-08-21
decision. Part 2 (separate document, separate commit, no results in the
tree) is the pre-registration for the one remaining untested question:
directional-skill persistence.

Reproducibility: `scripts/persist_directional_skill_pit_exploratory.py`
(first-repo, this commit), run with `--selfcheck --persist`. Durable
artifact: `data/characterizations/directional_skill_pit_exploratory_20260906T163116Z.json`.
New tables (NOT `metric_v2f_oos_result` or any result-of-record table):
`directional_skill_pit_exploratory_result` (4 rows),
`directional_skill_pit_exploratory_membership` (2,430 rows).

---

## 1A — point_gap semantics

**Finding: `point_gap` holds the same quantity — a single group's own
weighted mean edge — for both the result-of-record row and the new rows.
Not a contradiction; the field name is a plausible misnomer, present
since before this task, not introduced by it.**

Traced to source: `weighted_two_way_gap_bootstrap()`
(`trader_skill_metric_v2d.py:175-211`), the function underlying
`measure_oos()` (`trader_skill_metric_v2f.py:315`), computes:

```
point_gap = (base_w * p_won).sum() / point_denom - (base_w * p_price).sum() / point_denom
```

— the cap5-weighted mean of `won` minus the cap5-weighted mean of `price`,
over whatever single group of pairs was passed in. It is **not** a
cohort-minus-placebo difference computed within one call; `measure_oos()`
is called once per group (`label="cohort"`, then separately
`label="placebo"`), and each call's `point_gap` is that group's own mean
edge. This is exactly what the 2026-08-15 handover states for
`+0.0316` ("cohort mean edge," MASTER_HANDOVER_2026-08-15.md §2), and it
is exactly what my 2026-09-06 Step 3 script computed for the four new
rows — same function, same field, same semantics, called the same way. No
STOP condition triggered: the JSON is not comparing unlike things.

**The field name is arguably inaccurate** — "gap" suggests a difference
between two populations, but the value is a single population's edge
relative to its own entry price. This has been true since the
result-of-record row was first persisted (2026-08-15), not something this
task's new rows introduced. Per the task's instruction, **not renamed
here** — reported only.

---

## 1B — placebo survival asymmetry: NOT like-for-like as constructed

**Confirmed exactly as suspected: the cohort arm was drawn from an
already post-split-survival-filtered list; the placebo arm was matched on
pre-split profile only, with survival left to fall where it may. This is
a real defect in the 2026-09-06 Step 3 comparison, independent of which
direction the result went. Not fixed here.**

Construction paths, traced to the actual code:

- **Cohort**: `directional_skill_pit_power_estimate.py` reads
  `raw_survivors` / `bh_survivors` directly from Part B's
  `directional_skill_pit_legal_pool.py` output
  (`data/characterizations/directional_skill_pit_legal_pool_20260906T160303Z.json`,
  `survival.raw_survivors` / `survival.bh_survivors`). That field was
  itself defined in Part B as: skilled traders (raw or BH) **intersected
  with** "has ≥1 post-split resolved position"
  (`load_post_split_positions()` called on the skilled set, unique
  traders kept). **The cohort is therefore a subset selected, in part, on
  the very outcome ("survived into post-split") being measured against.**
  Feeding this set into `measure_oos()` necessarily returns
  `n_surviving_traders == n_traders_input` — 711/711 (100%), 504/504
  (100%) — not because of anything `measure_oos()` does, but because the
  input was pre-conditioned on survival before it ever reached that
  function.
- **Placebo**: built inside `directional_skill_pit_power_estimate.py` via
  `match_control(profile, cohort, elig_traders, seed=SEED)`
  (`trader_skill_metric_v2f.py:279`), where `profile` and `elig_traders`
  come from `build_presplit_cohort()`'s **pre-split-only** output
  (`n_pairs ≥ M_CHOSEN`, no reference to post-split activity anywhere in
  the matching feature vector: `log(n_positions)`, `log(n_markets)`,
  `log(activity_span_days)`, all pre-split). Matching is 1:1 nearest-
  neighbour on these pre-split features alone. Whether a matched control
  has **any** post-split resolved position is not checked at match time —
  it is only discovered afterward, when `measure_oos()` applies its own
  `entry_timestamp > T_SPLIT` filter. Result: 368/711 (51.8%) and
  280/504 (55.6%) actually surviving.

**This is a genuine construction asymmetry, not a presentational one.**
The cohort is implicitly conditioned on "kept trading past the split";
the placebo is not. Whether traders who keep trading past a gap differ
systematically in average edge from traders matched only on pre-split
activity is unknown and untested here — the direction of any resulting
bias is not established, only the fact that the two arms are not
comparably constructed. **Reported plainly, not fixed, per the task's
instruction** — see `ASYMMETRY_NOTE` embedded in the persisted exploratory
table (1D below) so no future reader of these figures misses it.

---

## 1C — canonical population bypass: further instance of §6.8

**Confirmed: neither pre-existing directional script calls
`backtest_window_sql()`. One is the already-logged §6.8 instance
(`trader_skill_metric_v2f.py`, still open, not fixed by this session);
the other (`directional_skill_diagnostic.py`) is a related but distinct
bypass, newly identified in this arc's Step 2, answering a different
windowing question by design.**

| script | function | what it computes instead | relationship to §6.8 |
|---|---|---|---|
| `trader_skill_metric_v2f.py` | `build_presplit_cohort()` → `build_tape_end_map()` (`trader_skill_metric_v2d.py:268`) | its own `tape_end` via `SELECT market_id, MAX(timestamp) FROM trades WHERE market_id IN (...) GROUP BY market_id`, anchored on a market-id list derived from `positions`, not from `markets`/`trades` directly; no `m.resolved=1` filter | **This is §6.8 itself** (MASTER_HANDOVER_2026-08-15.md §6, item 8, "v2f population bypass," found 2026-08-16). Symmetric difference measured there: 254 markets, canonical=6,842 vs v2f-implicit=6,588. Logged as "still open... v2f should be made to call the canonical function" — **remains unfixed as of this session**, confirmed by reading current `trader_skill_metric_v2f.py`, unchanged. |
| `directional_skill_diagnostic.py` | `load_post_split_positions()` | filters on `p.entry_timestamp > T_SPLIT` — **position entry time**, not market conclusion time; no `tape_end` reference anywhere in the file | **Related but distinct.** This script is not attempting to reproduce the canonical backtest population at all — it is deliberately answering "was this position entered after the split," a different question than "did this market conclude before/after the split," for its post-split arm. It is a further instance of the broader pattern (a script computing its own ad hoc window instead of consulting the canonical definition) but not literally the same bypass as v2f's, since the two windowing concepts (entry-time vs. tape_end) are not interchangeable for this script's purpose. First identified in Step 2 of this arc (2026-09-06). |
| `scripts/directional_skill_pit_legal_pool.py` (this arc, Part B, first-repo `4feb97f`) | `load_presplit_market_ids()` | calls `monitoring.column_definitions.backtest_window_sql()` directly | **The first script in either repo to call the canonical function**, per a grep across `scripts/*.py` and `monitoring/*.py` for `backtest_window_sql` / `column_definitions` imports, confirmed during Step 2. |

No script is changed here, per the task's instruction. This finding is
logged as a further data point on the pattern already named at
MASTER_HANDOVER_2026-08-15 §6.8 and §6b ("canonical adherence... is
convention-only, not structural").

---

## 1D — persisting the exploratory figures, and a further finding along the way

**Persisted, following the Objective-1 pattern
(`metric_v2f_intersection_cohort`) — trader-level membership, not just
aggregates — to two new tables, neither of which is
`metric_v2f_oos_result` or any other result-of-record table:**

- `directional_skill_pit_exploratory_result` (4 rows: `raw_cohort`,
  `raw_placebo`, `bh_cohort`, `bh_placebo`). Carries, per row:
  `is_exploratory=1`, `is_preregistered=0`, `produced_as_byproduct_of`
  (text, cites the Step 3 power-estimate script and commit),
  `asymmetry_note` (the 1B finding, verbatim), `point_gap`/`ci_lo`/`ci_hi`
  (**unchanged from the committed Step 3 JSON — never recomputed or
  overwritten**), `mde_half_width` (2.1–2.9pp, from Step 3), generating
  `seed`, `t_split`, `generated_at`, `generator_commit`, and pointers to
  both source JSON artifacts.
- `directional_skill_pit_exploratory_membership` (2,430 rows: one per
  trader per group — cohort and matched-placebo membership for both the
  raw and BH selection rules, `survived_post_split` flagged per trader).

### A further finding, surfaced while doing this custody work

**`match_control()` (`trader_skill_metric_v2f.py:279`) is not fully
determined by its `seed` parameter.** Re-deriving the placebo membership
in a fresh process, with the identical `seed=42`, did **not** reproduce
the exact matched-placebo set (nor its resulting `point_gap`/CI) from the
committed Step 3 artifact — confirmed across three repeated attempts in
this session, each producing a different placebo survivor count (368, 371,
372, 284, 279, 283 — six distinct values across three raw/bh reruns) and a
different recomputed `point_gap`. Mechanism, traced to the code:
`cohort_traders` and `elig_traders` are Python **sets**; `match_control()`
calls `list()` on them before shuffling (`cohort_list = list(cohort_traders)`)
and before building the candidate pool (`pool = [t for t in elig_traders
if ...]`), and CPython's set iteration order for strings depends on the
**process-level hash seed** (`PYTHONHASHSEED`), confirmed unset (random
per process) in this environment. The function's own `seed` argument
fixes the `numpy` RNG draws, but not the order of the sequence those
draws are applied to — so the same `seed` produces a different greedy
1:1 match in a different process.

**This affects every placebo ever built via `match_control()`, including
the 2026-08-15 result-of-record placebo and the 2026-09-06 Step 3
placebo** — neither is exactly reconstructable from its recorded seed
alone. It is a second, independent construction defect on top of 1B's
survivorship asymmetry, specific to the mechanics of the matcher rather
than the matching criteria.

**Handling, consistent with "report and halt, do not work around" for a
figure that contradicts the Step 2/3 doc**: the original, committed Step
3 `point_gap`/`ci_lo`/`ci_hi` figures are persisted **unchanged** as the
authoritative record (never overwritten by a recomputation). The
re-derived placebo membership from this session is persisted
**separately and explicitly flagged**
(`membership_verified_matches_original=0` for every placebo row, `=1` for
every cohort row, which reproduced exactly on every attempt) and its own
recomputed figures are stored alongside, in dedicated `redevrived_*`
columns, never conflated with the original. **Not fixed** — `match_control()`
is unchanged, per this task's scope. This is reported as a finding for
Oscar, not resolved.

---

## What Part 1 did NOT determine

- **Direction or magnitude of any bias from 1B's survivorship asymmetry**
  — only that the asymmetry exists. Whether traders who trade past a gap
  differ systematically from the matched-profile placebo population is
  untested.
- **Whether the `match_control()` nondeterminism materially changed the
  qualitative 2026-08-15 or 2026-09-06 verdicts** — not assessed. The
  three re-derivations in this session moved the raw-placebo `point_gap`
  between roughly 0.0099 and 0.0160 and the BH-placebo between roughly
  0.0120 and 0.0161 (all comfortably CI-overlapping with the originally
  committed values and with each other), so nothing suggests a qualitative
  flip, but this was not tested rigorously (e.g. no repeated-draws
  distribution over many `PYTHONHASHSEED` values was constructed — that
  would itself be new computation, out of scope for a custody task).
- **Whether `directional_skill_diagnostic.py`'s entry-timestamp-based
  windowing should, in principle, be replaced by a tape_end-based one for
  its post-split arm** — reported as a distinct design question (1C), not
  adjudicated.
- **Whether the result-of-record itself (2026-08-15, `eaeabbc`) is
  affected by the same `match_control()` nondeterminism in a way that
  would change its own reported numbers** — plausible by the same
  mechanism, not verified here (would require re-running the original
  Objective-2 pipeline, which touches result-of-record territory and was
  out of scope for this custody task).
- **No STOP condition from the task's own list was triggered as stated**:
  1D persisted without touching any result-of-record table; 1A found
  consistent (not contradictory) `point_gap` semantics across old and new
  rows. The one figure-level discrepancy encountered (placebo
  recomputation vs. the Step 2/3 doc) was a **newly surfaced mechanism**,
  reported in full rather than silently reconciled or worked around, and
  did not require abandoning Part 1D — the original figures remain
  intact and are what is persisted as authoritative.

---

**Hard gate**: Part 1 complete and reported above, including the 1B
survivorship asymmetry (arms are NOT like-for-like as constructed) and the
newly discovered `match_control()` nondeterminism. Part 2's control design
must account for both. Proceeding to the pre-registration document
(separate file, separate commit, no results computed).
