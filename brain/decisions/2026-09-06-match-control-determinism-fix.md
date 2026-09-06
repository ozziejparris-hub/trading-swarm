# match_control() Determinism Fix + Twice-Classifiable Population Count

Fixes the reproducibility defect found during
[2026-09-06-directional-skill-exploratory-custody.md](2026-09-06-directional-skill-exploratory-custody.md)
(Part 1D) and answers Open Question 1 of
[2026-09-06-directional-skill-persistence-prereg.md](2026-09-06-directional-skill-persistence-prereg.md)
(§3). **No verdict on approving the persistence pre-registration is stated
here — that is Oscar's.**

Reproducibility: `scripts/trader_skill_metric_v2f.py` (first-repo `42b14fc`,
the fix), `tests/test_match_control_determinism.py` +
`tests/_match_control_determinism_worker.py` (same commit),
`scripts/directional_skill_twice_classifiable_population.py` (first-repo,
this commit). Durable artifact:
`data/characterizations/directional_skill_twice_classifiable_population_20260906T170928Z.json`.

---

## Part 1 — match_control() determinism, fixed

**Change**: two lines, `scripts/trader_skill_metric_v2f.py:301-302`.
`cohort_list = list(cohort_traders)` → `cohort_list = sorted(cohort_traders)`;
`pool = [t for t in elig_traders if t not in cohort_traders]` →
`pool = [t for t in sorted(elig_traders) if t not in cohort_traders]`.
Nothing else in the function was touched — matching criteria (log
positions/log markets/activity span), the distance metric (Euclidean on
that 3-feature vector), the greedy 1:1 logic, and every threshold are
byte-identical to before.

**Full audit of the function for remaining order-dependent paths** (the
task's explicit ask — "inspect the whole function for any other order-
dependent path before deciding the change is complete"):

| line | code | order-dependent? | resolution |
|---|---|---|---|
| `prof = profile.set_index('trader')` | pandas index set | No — `profile`'s row order comes from an upstream `groupby()` (sort=True default), not a Python set inside this function | not touched |
| `cohort_list = sorted(cohort_traders)` | was `list()` | **Yes, fixed** | sorted |
| `pool = [t for ... in sorted(elig_traders) ...]` | was raw set iteration | **Yes, fixed** | sorted |
| `pool_feats = {}` built from `pool` | dict insertion order | No, once `pool` order is fixed — Python dicts preserve insertion order (3.7+) | follows from the fix above |
| `rng.shuffle(order)` | numpy RNG applied to a sequence | No longer — deterministic once the pre-shuffle `order` sequence is deterministic, which it now is | resolved |
| `used = set()` | only `.add()`/`in` used, never iterated | No — membership tests are order-independent | not an issue |
| `pool_arr`, `pool_keys` from `pool_feats.values()/.keys()` | dict iteration order | No, once `pool_feats` insertion order is fixed | follows from the fix above |
| `np.argsort(dists)` | tie-breaking among equal distances | No — NumPy's sort operates purely on array values (not on Python object hashes); given an identical input array, output is bit-for-bit identical across processes on the same NumPy build. It was only ever a *symptom* surface (ties broken differently) because the input `pool_arr` row order itself was nondeterministic pre-fix — with that fixed, `argsort` needs no change | not touched, verified via the tie-stressing worker fixture (§ below) |
| `return set(matches.values())` | final packaging into a set | The *content* is now deterministic; a caller iterating the returned set could still see varying order, but no call site in this codebase relies on the returned set's iteration order (only membership, via SQL `IN` clauses or set operations) | not touched — out of scope, doesn't affect any consumer |

**No order-dependent path remains that `sorted()` does not resolve.**

**Determinism test**: `tests/test_match_control_determinism.py`, added to
`run_tests.py`'s suite (confirmed running and passing:
`PASS test_match_control_determinism.py (6 tests, 6 passed)`). Spawns a
fixed synthetic `(profile, cohort_traders, elig_traders)` construction
(`tests/_match_control_determinism_worker.py` — 5 cohort traders, 12
candidate pool traders including three groups of tied feature vectors, to
stress the `argsort` tie-breaking path specifically) in **8 separate
subprocess invocations** — `PYTHONHASHSEED` ∈ {0, 1, 12345, unset/random,
unset/random, 7, 999, 424242} — and asserts byte-identical matched output
across all eight. **Manually confirmed the test would have caught the
original defect**: running the same fixture through the pre-fix logic
(`list()` instead of `sorted()`) produced `['p01','p02','p03','p07','p12']`
at `PYTHONHASHSEED=0` and `12345`, but
`['p02','p03','p07','p08','p12']` at `PYTHONHASHSEED=1` — the exact
signature of the defect this fix addresses.

**Reproducible from this commit forward. Nothing previously committed was
recomputed, overwritten, or re-derived** — the fix applies to future calls
only, per the task's explicit constraint.

---

## Part 2 — defect log entry

Recorded in `MASTER_HANDOVER_2026-09-05.md` §6 ("KNOWN DEFECTS, LIVE AND
UNFIXED") — the standing defects record that document's own closing note
says it draws on the individual dated decision docs for; this defect is
new since 2026-09-05 and has no earlier entry to amend, so a new bullet
was added there, plus a dated `*Amended 2026-09-06*` postscript at the end
of the file, per that document's own established amendment convention
(matching `MASTER_HANDOVER_2026-08-15.md`'s three prior `*Amended...*`
postscripts).

The §6 entry states, in full: the mechanism (as in CONTEXT above); scope
— **every placebo built via `match_control()` before first-repo `42b14fc`
is not reconstructable from its recorded seed, explicitly naming the
2026-08-15 result-of-record placebo and the 2026-09-06 Step 3 exploratory
placebo**; observed variation — three re-runs, six distinct placebo
survivor counts, raw-placebo point estimate ranging ~0.0099–0.0160, all
CI-overlapping, no qualitative flip observed and not rigorously tested
beyond that; that this is a **second named mechanism**, alongside
background-backfill drift (`MASTER_HANDOVER_2026-08-15.md` §6a), behind
the 2026-08-16 UNREPRODUCIBLE verdict; the fix, commit `42b14fc`, and that
placebo construction is reproducible **from this commit forward only**;
and explicitly that **the fix does not make pre-fix placebos reproducible
and no pre-fix figure has been recomputed**.

---

## Part 3 — twice-classifiable population count

**Counts and position-count distributions only. No sign-flip null, no
p-value, no classification, no outcome-dependent quantity was computed —
`scripts/directional_skill_twice_classifiable_population.py` calls only
`load_post_split_positions()` (imported unchanged, a structural SQL
filter — category/gap-flag/entry-price/closed-trade-result, the same
"resolved position" definition used everywhere in this project) followed
by a plain `groupby().size()`. No `sign_flip_null`, `classify`,
`bh_correction`, or `per_trader_and_aggregate` call appears in the
script.** Pre-split BH classification was **read** from Part B's
committed artifact (`directional_skill_pit_legal_pool_20260906T160303Z.json`),
not recomputed.

**Selfcheck cross-validated against Part B's own committed survival
counts** (any ≥1 post-split position, no minimum): recomputed 711 raw /
504 BH survivors, exact match to Part B's persisted figures both counts
and membership (`load_post_split_positions()` is pure SQL + groupby, no
randomness — an exact match was expected, not merely likely, and is what
was observed). **No STOP condition triggered**: classifiable count is
5,732 exactly as Part B reported; raw/BH survivor counts are 711/504
exactly as Part B reported.

### Results

| | value |
|---|---|
| **[1] twice-classifiable population size** (≥10 post-split resolved positions) | **753** |
| **[2] persistence cohort size, N** (pre-split BH-skilled, within twice-classifiable) | **146** |
| **[3] comparison group size** (pre-split NOT BH-skilled, within twice-classifiable) | **607** |

For reference, Part B's own pre-split figures: 5,732 classifiable, 1,178
BH-skilled, 4,554 not BH-skilled. **The M_CHOSEN≥10 post-split bar is far
stricter than the "any position" survival bar** — 753 twice-classifiable
vs. 504 BH "any position" survivors, and only 146 of the 1,178 pre-split
BH-skilled traders (12.4%) remain classifiable a second time.

### Post-split position-count distribution, twice-classifiable population (n=753)

| median | mean | p10 | p25 | p75 | p90 | max |
|---|---|---|---|---|---|---|
| 23 | 37.9 | 11 | 14 | 46 | 82.8 | 359 |

Right-skewed, consistent with every other position-count distribution
seen in this arc (mean well above median).

### Same distribution, split by pre-split BH classification

| group | n | median | mean | p10 | p25 | p75 | p90 | max |
|---|---|---|---|---|---|---|---|---|
| pre-split BH-skilled (persistence cohort) | 146 | 28.5 | 45.4 | 11 | 17 | 58.5 | 92.0 | 359 |
| pre-split NOT BH-skilled (comparison group) | 607 | 22.0 | 36.1 | 11 | 14 | 44.5 | 79.8 | 261 |

**An imbalance is visible, reported as such, not adjudicated**: the
persistence cohort trades more post-split (median 28.5 vs. 22.0, mean 45.4
vs. 36.1) than the comparison group. Whether this reflects a genuine
activity-level difference between pre-split-skilled and pre-split-not-
skilled traders, or is itself informative about who "survives" to be
twice-classifiable at all, is not established here — noted for whoever
adjudicates the pre-registration, since §3 of that document already
depends on this population being constructed the way it specifies.

### [6] Sensitivity reference only — `M_CHOSEN=10` is fixed, not changed

| post-split threshold | total | pre-split BH-skilled | pre-split not BH-skilled |
|---|---|---|---|
| 5 | 1,171 | 227 | 944 |
| **10 (fixed, pre-registered)** | **753** | **146** | **607** |
| 15 | 555 | 117 | 438 |
| 20 | 441 | 98 | 343 |

The population is sharply threshold-dependent — roughly halving from the
5-position bar to the 20-position bar. This table exists so Oscar can see
that dependence before approving §1's fixed `M_CHOSEN=10`; it is not a
proposal to change it, and it was not changed.

---

## What was not determined

- **Part 1**: whether any OTHER function in either repo has the same
  `list(some_set)`-before-shuffle pattern — only `match_control()` was
  audited and fixed, because it was the specific function named by the
  1D finding. Not searched for elsewhere.
- **Part 1**: whether the `match_control()` nondeterminism materially
  changed the qualitative 2026-08-15 result-of-record verdict — still not
  assessed (carried forward from the custody document); this task fixed
  the mechanism going forward, it did not retroactively evaluate the
  result-of-record's exposure to it.
- **Part 2**: whether every other location that might reference or rely
  on `match_control()`'s pre-fix behavior (e.g., cached downstream
  artifacts, other decision docs' quoted figures) has been enumerated —
  only the two explicitly-named placebos (result-of-record, 2026-09-06
  Step 3) were checked against this defect; a broader repo-wide audit for
  other `match_control()` consumers was not performed.
- **Part 3**: whether N=146 (or the 607-trader comparison group) is
  large enough to support the persistence pre-registration's own success
  criteria (§6 of that document, a trader-clustered bootstrap CI) — a
  power question, not answered here; this task reports the count, not
  its adequacy.
- **Part 3**: the cause of the activity-level imbalance between the
  persistence cohort and comparison group (median 28.5 vs. 22.0
  post-split positions) — reported, not investigated.
- **Part 3**: §8 of the persistence pre-registration's own prerequisite
  (establishing an in-house synthetic-null persistence rate on this
  actual twice-classifiable population) — explicitly out of scope for
  this task and not attempted; still outstanding.
- **No post-split classification, p-value, or outcome-dependent quantity
  was computed anywhere in this task** — confirmed by inspection of
  `directional_skill_twice_classifiable_population.py`, which calls only
  a structural position loader and `groupby().size()`.
