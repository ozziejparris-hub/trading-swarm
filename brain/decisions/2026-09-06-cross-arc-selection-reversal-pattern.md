# Cross-Arc Pattern: The Non-Selected Group Keeps Matching or Beating the Selected One

A synthesis of already-committed results only. **No computation was run
to produce this document** — every figure below is quoted from its
source, re-checked against the committed doc before being restated here.

---

## The pattern, stated once, then enumerated precisely

Across four independent tests, each built on a different selection
criterion (realised presplit edge, directional-skill classification,
PIT-legal directional selection, pre-split BH-classified persistence),
**the group that was NOT selected on the criterion under test matched or
outperformed the group that WAS**, on the edge/PnL dimension specifically
— not on the dimension each test's own selector was actually built to
measure.

### Instance 1 — presplit-edge selection

Two separate events, not one, and they should not be conflated:

- **The 2026-08-15 result of record itself** (`+0.0316` cohort, CI
  `[-0.0088, +0.0710]`, n=3,032/120 vs. `+0.0127` placebo, CI
  `[-0.0210, +0.0461]`, n=2,569/110; `metric_v2f_oos_result`,
  `generator_commit eaeabbc`) does **not** show the placebo beating the
  cohort — the cohort's point estimate is higher. But the CIs overlap
  substantially, and Oscar's own 2026-08-21 verdict on this figure was
  **NULL** — no clean separation was ever established at this stage.
- **The N=0 gap check** (`2026-09-05-n0-gap-check.md`, commit `7aa3fe5`),
  re-running the identical `measure_oos()` machinery on updated data
  (n=3,795 cohort / 2,693 placebo, not the original 3,032/2,569), found
  the point estimate had reversed: cohort `0.0316 → 0.0208` (−34.2%),
  placebo `0.0127 → 0.0280` (+120.1%, more than doubling) — **"the
  placebo currently outperforms the cohort by about 0.0072 in mean
  weighted edge, reversing the result of record's +0.0189 gap"** (quoted
  directly). The paired CI (`[-0.057, +0.043]`) still straddles zero, so
  this is not proof the gap is negative — only that it stopped being
  demonstrated positive, in the same direction as the other three
  instances below.

### Instance 2 — the 2026-09-05 directional-skill test

`2026-09-05-directional-skill-result.md` (trading-swarm, run from the
prereg at commit `cf88f8a`): **"the placebo beats the cohort on every
measure."** Classified-skilled rate 39.2% (placebo) vs. 26.0% (cohort)
raw; 29.4% vs. 19.2% Benjamini-Hochberg-adjusted; pooled aggregate
significance `p=0.006` (placebo, clears its own 95th-percentile bar) vs.
`p=0.214` (cohort, does not); split-half persistence 58.3% vs. 60.0%
(cohort nominally higher here, both above Gómez-Cram's 44%, but this is
the one sub-measure where cohort edges placebo, on denominators explicitly
flagged as too small to weigh).

### Instance 3 — the 2026-09-06 exploratory PIT figures

`2026-09-06-directional-skill-discrepancy-pit-pool-power.md`: **"in 3 of
4 comparisons, the matched placebo's point estimate is equal to or larger
than the cohort's (raw: 0.0099 vs 0.0090; BH: 0.0161 vs 0.0029)"** —
quoted directly, appearing twice in that document (also at the document's
closing summary: "the matched placebo outperforms the cohort in 3 of 4
comparisons"). The two explicit pairwise figures shown both favor the
placebo; the source document's own "3 of 4" count is cited as written,
not independently re-derived here.

### Instance 4 — the 2026-09-06 persistence test aggregate

`2026-09-06-directional-skill-persistence-test-run-2.md` (§4, two-way
trader × market clustered bootstrap): comparison group's aggregate CI
**excludes zero** — `+0.0210`, CI `[0.0044, 0.0376]`, n_pairs=10,827 —
while the persistence cohort's does not — `+0.0115`, CI `[-0.0151,
0.0362]`, n_pairs=3,025. The group **not** classified as directionally
skilled pre-split shows a statistically significant positive aggregate
edge post-split; the group that **was** so classified does not.

---

## Why this is worth recording as one finding, not four disappointments

A selector that fails randomly relative to its own control is
uninformative on its own — noise, reported and moved past. **Four
selectors, built on four different criteria, at four different points in
this arc, using different populations and in one case different
inference machinery entirely, failing in the SAME DIRECTION is not
consistent with four independent instances of noise.** It is evidence
about the structure of what is being measured — specifically, that
whatever `edge = won − entry_price` actually captures is not being
concentrated by any of the selection criteria tried so far — not just
evidence that four particular selectors underperformed.

---

## Leading candidate explanation — UNTESTED, a hypothesis, not a conclusion

Per Della Vedova (SSRN 6191618): prediction-market returns decompose into
a **directional** component and an **execution** component, with shared
variance **<1%** for humans in that paper's population — nearly
independent dimensions. Execution, not forecasting, is what the paper
finds determines profit.

**If this decomposition holds in this project's own population**:
selecting hard on direction (Instances 2–4) — or on realised presplit
edge, which is itself dominated by direction plus noise (Instance 1) —
produces a group with no particular execution advantage over the
unselected remainder, which retains the population's own average
execution. **That single mechanism would generate this exact pattern
every time it was tried**, regardless of which specific directional or
edge-based criterion was used to build the selected group.

**This is explicitly not established here.** It is the leading candidate
because it is consistent with all four instances and because it is
already the project's own stated reason for building the canonical
skill-metric design's Components 2 and 3 (absolute and relative
earliness — `2026-09-05-canonical-skill-metric-design.md`) — but no test
of execution against edge has been run. **What would settle it**: a
separately pre-registered test of the execution dimension (Components 2
and 3) against edge, on a population not itself pre-selected on
direction — not sketched, proposed, or begun here.

---

## A distinct, separately-flagged open question — not an answer

**The comparison group's positive, significant aggregate edge in the
2026-09-06 persistence test (Instance 4) is itself unexplained.** These
607 traders were specifically classified as **NOT** directionally skilled
pre-split, yet their post-split aggregate edge excludes zero. If traders
who show no evidence of forecasting skill are making money as a group,
something other than forecasting is generating that return. Two
candidates, both untested: **an execution effect** (this group's average
entry timing or market-age-at-entry happens to be more favorable, for
reasons unrelated to direction-calling) or **a structural artifact**
(something about the two-way clustered bootstrap, the cap5 weighting, or
the underlying market structure of this specific population, rather than
any trait of the traders themselves). **Which one — or whether it is
something else entirely — is not established. Stated as an open
question, not resolved, not guessed at further here.**

---

## What this document does not do

Does not propose a fix. Does not propose which of the two open questions
above to pursue first. Does not state whether Della Vedova's
decomposition is confirmed, only that it is consistent with, and not yet
tested against, this project's own four instances. No verdict on what to
do next — that is Oscar's, per every source document this note draws on.
