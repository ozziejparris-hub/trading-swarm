# Session Summary — 2026-09-06 (Server Setup 12)

## THEME

One arc, start to finish: does directional skill classified pre-split
persist out-of-sample. It hit a real prerequisite-gate failure partway
through, was amended rather than routed around or abandoned, and landed
on a genuine positive result — the first clean one in three days of
selector tests that had otherwise all reversed. That reversal pattern is
itself now recorded as a finding, not background noise. This document is
the record of how each step was reached and why; `MASTER_HANDOVER_2026-09-06.md`
(`6c3ce36`) is the resulting position — read that first if the interest
is "where things stand," this one if it is "how we got there."

---

## THE ARC IN SEQUENCE

Each step: what it decided, first-repo commit, trading-swarm commit.

1. **Null calibration.** The directional-skill harness's per-trader
   classification is well-calibrated at ~5% under a population with zero
   skill by construction — a synthetic zero-skill population run through
   the unmodified harness classified at 4.1%/7.8%/5.6% raw, 0.0% BH.
   Ruled out explanation (b) (mis-specified null) for per-trader results.
   (`f3cb201`, `5939b98`.)
2. **The PIT-legal pool + power estimate.** Built the first script in
   either repo to call the canonical `backtest_window_sql()` directly:
   5,732 PIT-legal classifiable traders, 1,178 BH-skilled pre-split. As
   an unavoidable by-product of a clustered-bootstrap power estimate, this
   step also produced real edge figures — see "What went wrong," below.
   Also resolved a 37.3%/39.2% presentational discrepancy and confirmed
   the BH-correction implementation is genuine. (`4feb97f`, `00fa294`.)
3. **Exploratory-result custody.** Quarantined the by-product edge
   figures as explicitly **not pre-registered**, persisted to new tables
   only, trader-level membership included. Surfaced the `match_control()`
   determinism defect while doing this custody work. (`030ed6a`,
   `056df57` + `7743740` for the persistence pre-registration written
   in the same task.)
4. **`match_control()` determinism fix.** Fixed the seed-nondeterminism
   defect found in step 3 — two lines, `sorted()` in place of `list()` —
   proven with a new fresh-process determinism test. (`42b14fc`, and the
   twice-classifiable population count in the same task: `1d34ced`,
   `f820da1`.)
5. **External dataset scoping.** Verdict: `vgregoire/polymarket-users`
   cannot increase the persistence test's N — whole-history aggregates
   only, no per-position records, and coverage ends before `T_split`
   regardless. Same task amended the persistence pre-registration's
   success criterion (split primary/secondary axes) and control design
   (stratified reporting), both blind, both committed before any real
   figure existed. (`1764e33`, `a4b6494` + `57641b0`.)
6. **S8 gate failure.** Ran the pre-registration's own prerequisite —
   establish an in-house null via split-half persistence on the real
   753-trader population — and it produced a synthetic-cohort denominator
   of 6, below the documented floor of 10. **Reported and halted**, no
   real persistence rate computed. (`ea1140e`, `6b5002c`.)
7. **REPS premise test.** Checked whether the zero-skill population's
   BH=0 result was an artifact of the higher `REPS` used post-split.
   Falsified — BH-adjusted classification was exactly zero in all 36
   tested cells (3 draws × 4 REPS values × 3 groups). (`6dc0bf5`,
   `92569df`.)
8. **S8 amendment.** Stated plainly that the gate as originally specified
   was not met, then established the same null by the REPS test's
   alternative route, fixed numerically at 0%. Committed before any real
   result — git-provable ordering. (`7ae1845`.)
9. **The persistence result.** Ran to completion: outcome cell **A1×B2**
   — persistence rate 37.0% (CI `[0.2945, 0.4521]`) vs. comparison
   group's 18.6% (CI `[0.1549, 0.2175]`), holding up across all five
   activity strata; secondary comparison against Gómez-Cram's 44% is
   unresolved (an expected outcome at this N, not a failure); aggregate
   test shows the comparison group's CI excluding zero while the
   cohort's does not. (`6e69bc8`, `9de3299`.)
10. **Cross-arc pattern note.** Recorded that this same reversal —
    non-selected group matching or beating the selected group on edge —
    now appears in four independent instances across the last three days.
    (`8d14c3b`.)
11. **Handover.** `MASTER_HANDOVER_2026-09-06.md`, superseding the
    2026-09-05 version. (`6c3ce36`.)

---

## DECISIONS TAKEN, AND THE REASONING — DISTINGUISHED FROM FINDINGS

Everything above this section is a finding: a number, a classification, a
result. The items below are decisions — points where a choice was made
among live alternatives, not a fact discovered.

**To pursue the directional selector rather than the decay ladder,
classifier, or sweep.** The 2026-09-05 handover left this as the "obvious
next question, now evidentially supported" (its own §9 language) — the
original directional test had found skill-like signal in both cohort and
placebo, meaning the selector, not the phenomenon, had failed. Today's
work is the direct follow-through on that specific opening, not a
default continuation of whichever arc happened to be open — the sweep
was already formally stopped and the classifier's formal adjudication
was already deferred to Oscar, so neither was live work to resume.

**To fix `match_control()` rather than leave it.** Worth being precise
about what actually happened here, since the shape of the decision
matters more than a one-line summary: the custody task (step 3) that
found the defect explicitly scoped fixing it **out** — its own language
was "not fixed here, per this task's scope" and "reported as a finding
for Oscar," never a judgment that leaving it was acceptable on the
merits. The custody document flagged it as unresolved, not as settled
either way. A separate, dedicated task then explicitly commissioned the
fix. This is a scope boundary followed by a deliberate follow-up, not a
recommendation that was reversed — worth stating precisely rather than
letting a punchier "initially recommended leaving it, then reversed"
framing stand uncorrected.

**To approve the persistence pre-registration at N=146 knowing B2 was
a likely landing spot.** By the time the "run it" instruction arrived,
two facts were already committed and available: N=146 (from the
twice-classifiable population count, step 4) and the amendment's own
closed-form CI-width estimate — roughly ±8 percentage points at this N
for a rate near 40%, wide enough to straddle Gómez-Cram's 44% routinely
(the amendment itself, step 5). Approving the run with that estimate
already on the record is why the amendment's own six-cell outcome table
exists at all — it was built specifically so a B2-shaped result would
have somewhere honest to land instead of collapsing into an undifferentiated
"inconclusive."

**To amend §8 rather than abandon the test or wait for more data.** The
reasoning is the purpose-vs-method distinction stated directly in
Amendment 2026-09-06b: §8's *purpose* was to establish a trustworthy null;
its *specified method* (split-half persistence) failed on inadequate
denominators. The REPS test (step 7) established the same null — by
construction, the identical underlying quantity a split-half check would
have measured — through a different, independently verified route with
36 points of agreement rather than one contested denominator. Amending
was the correct response specifically because the purpose was already
served; it would not have been the correct response if only the method
had changed without new evidence establishing what the method was for.

---

## WHAT WENT RIGHT METHODOLOGICALLY

The results are only as trustworthy as the process that produced them,
and several parts of that process are worth recording as working as
designed, not just as background:

- **The S8 gate fired correctly and stopped the run.** A synthetic-cohort
  denominator of 6 against a documented floor of 10 is not a dramatic
  failure — it is close, and it would have been easy to treat 6 as "close
  enough" and proceed. The gate did not do that. It halted, reported
  exactly what was found, and did not compute a real persistence rate
  until the null question was separately and properly resolved. The
  discipline the pre-registration was built to enforce is exactly the
  discipline that fired.
- **The REPS premise test was cheap and answered a question that could
  have invalidated the cohort — run before building on it, not after.**
  Total runtime 473 seconds. Had it found BH rates materially higher at
  `REPS=1,500` than at `10,000`, that would have reached the pre-split
  classification defining N=146 itself, not just the S8 gate. It was run
  and answered before the amendment was written, not discovered as a
  problem after the persistence result was already in hand.
- **The amendment was committed before the result, git-provable.** Both
  the split-criterion amendment (step 5) and the S8-null amendment (step
  8) landed in their own commits with no results in the tree, exactly
  the discipline this project has used since the relevance-classifier
  gate sets. A skeptic does not have to trust an account of what happened
  — the commit graph proves the criterion preceded the number.
- **A framing error in a task prompt was caught and corrected, not
  inherited.** The cross-arc pattern note's own commissioning prompt
  characterized the 2026-08-15 result of record as an instance of
  "placebo beating cohort" — checked against the actual committed figures
  (`+0.0316` cohort vs. `+0.0127` placebo, cohort ahead) and found not to
  be what that record shows. The reversal at that stage came later, in
  the separate N=0 gap check. The pattern note was written with the
  correction, not the prompt's original framing, and the correction is
  recorded in the note itself.

---

## WHAT WENT WRONG — stated plainly, not softened

**The Step 3 power-estimate task caused an unpre-registered edge
measurement to be taken as a by-product, and the task's author did not
anticipate this.** The task asked for a projected confidence-interval
width — a precision question. The clustered-bootstrap machinery that
answers a precision question (`weighted_two_way_gap_bootstrap()`) cannot
produce a CI width without also producing the point estimate the CI is
centered on — the two are computed together, inseparably, by the same
function call. Asking "how wide would the interval be" mechanically also
asks "what would the number be," whether or not that second question was
intended. The result was real cohort/placebo edge figures existing in
the world with no pre-registration behind them — figures that, per this
project's own standing discipline, can never be retroactively
pre-registered. They were quarantined as explicitly exploratory (step 3)
rather than treated as a result, which contained the damage, but the
figures exist and are on the record regardless.

**This is recorded as a prompt-design lesson, not an execution
failure**: a task that asks for a measurement's *precision* will, by the
nature of the underlying statistical machinery, also produce its
*value*. Anyone drafting a task that only wants to know how wide an
interval would be, without wanting the point estimate that comes with
it, needs to say so explicitly and needs a plan for what happens to that
point estimate once it exists — because it will exist, whether the task
asked for it or not.

---

## OPEN THREADS CARRIED FORWARD, EACH WITH WHAT WOULD SETTLE IT

- **The execution dimension (Components 2 and 3 of the canonical skill
  metric design)** — absolute and relative earliness, proposed
  2026-09-05, never tested. What would settle it: a separately
  pre-registered execution-vs-edge test, on a population not itself
  pre-selected on direction. This is where both Della Vedova's own
  framing and today's cross-arc pattern point, but pointing at it is not
  the same as having tested it.
- **The comparison group's unexplained positive aggregate edge.** 607
  traders classified as **not** directionally skilled show a
  statistically significant positive aggregate edge post-split
  (`+0.0210`, CI `[0.0044, 0.0376]`). What would settle it: distinguishing
  an execution effect from a structural artifact requires examining
  entry timing, market age at entry, or the bootstrap/weighting machinery
  itself against this specific population — none of which was attempted
  today.
- **The cohort's per-trader-vs-aggregate tension.** 37.0% persistence at
  the per-trader level, but the cohort's own aggregate CI includes zero
  (`+0.0115`, CI `[-0.0151, 0.0362]`) while the comparison group's does
  not. This is the same tension the 2026-09-05 directional-skill
  pre-registration's own Open Question 3 anticipated and left unresolved
  — still unresolved today, in a different but structurally similar form.
  What would settle it: understanding why a small number of large-position
  traders can dominate an aggregate statistic in a way that disagrees
  with the per-trader classification rate — not investigated here.
- **The persistence run's observation-log items** — no monotonic trend
  between post-split activity and persistence within the cohort; no
  category, market-count, or entry-price data examined against
  persistence in this run; a prospectively-observable candidate selector
  exists in principle (pre-split BH classification) but its forward
  usability depends entirely on the edge question this arc has not
  answered. All explicitly unregistered and untested per the run's own
  observation log (`2026-09-06-directional-skill-persistence-test-run-2.md`).
  What would settle any of them: dedicated, separately pre-registered
  follow-up tests, none proposed here as more urgent than another.

---

## A note on verification

Every figure and commit hash in this document was checked against its
committed source before inclusion — not restated from the task prompt
that commissioned this document. Two places where the checking mattered
enough to record explicitly: the `match_control()` "recommendation
reversed" framing above, and the exact composition of the "3 of 4
comparisons" figure carried into the cross-arc pattern note, which is
quoted there as written in its source document
(`2026-09-06-directional-skill-discrepancy-pit-pool-power.md`) rather
than independently re-derived, since only two of the four comparisons
are explicitly enumerated in the visible text and re-deriving the other
two would have required new computation this document does not perform.

No verdict on what to do next is stated here. Every open thread above is
carried forward as a thread, not a recommendation.
