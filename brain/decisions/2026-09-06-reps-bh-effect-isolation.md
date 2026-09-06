# REPS Effect on BH-Adjusted Classification — Premise Test

Answers one question before anything is built on the answer: on a
population with **no skill by construction**, does BH-adjusted
classification differ materially between `REPS=1,500` and
`REPS=10,000`? Motivated by the 2026-09-06 persistence run (first-repo
`ea1140e`), which found BH=0 in all three synthetic zero-skill groups at
`REPS=10,000`, against the 2026-09-05 real test's BH rates of
19.2%/29.4% at `REPS=1,500`. **Answer: no — the premise is falsified.**
Full numbers and reasoning below. **No fix, remediation, or next step is
proposed here — that is Oscar's.**

Reproducibility: `scripts/directional_skill_reps_bh_effect.py`
(first-repo `6dc0bf5`), run with `--selfcheck`. Durable artifact:
`data/characterizations/directional_skill_reps_bh_effect_20260906T193257Z.json`.

---

## What was NOT touched (scope, as fixed by the task)

No pre-split classification, `N=146`, the 5,732 PIT-legal population, or
any real trader's classification was recomputed. No persistence rate,
partial or otherwise, was computed. `MIN_ADEQUATE_DENOMINATOR` and the
§8 gate were not revisited. `bh_correction()`, `sign_flip_null()`,
`classify()`, `per_trader_and_aggregate()` were imported and used
unmodified; `REPS` was overridden via the same documented module-
attribute rebind the 2026-09-06 persistence run used
(`directional_skill_diagnostic.REPS = <value>`, read by the imported,
unedited functions at call time) — `directional_skill_diagnostic.py`'s
source was not touched.

---

## Construction

Identical to the 2026-09-06 persistence run's §8 synthetic-null
construction: real post-split positions for the 753 twice-classifiable
traders (`load_post_split_positions()`, unchanged; 28,563 positions,
loaded once and shared across every seed/REPS combination — only the
synthetic side-draw varies), each position's side drawn **once** at
random, harness `SEED=42` re-seeded per call site inside
`sign_flip_null()` unchanged, `ALPHA=0.05` unchanged.

**Reproducibility check (STOP-condition gate)**: at `SYNTH_SEED=20260906`,
`REPS=10000`, this script's output was asserted against the 2026-09-06
persistence run's committed figures. **Exact match**: cohort raw=5/bh=0,
comparison raw=30/bh=0, pooled raw=35/bh=0 — all six values identical.
**No reproducibility failure. STOP condition not triggered.**

**Three independent synthetic draws**, each a fresh `SYNTH_SEED`, all
recorded: `20260906` (the original 2026-09-06 run's own seed — appears
here as a directly comparable arm), `31337`, `99991`.

**Four REPS values**: 1,500, 3,000, 5,000, 10,000. Runtime was not
prohibitive (473.4s total across all 3 seeds × 4 REPS values ≈ 7.9
minutes) — both intermediate arms were run, not dropped.

---

## Full results — all 36 combinations

| seed | REPS | group | n | raw | raw% | BH | BH% | distinct p | pinned at floor | floor p-value |
|---|---|---|---|---|---|---|---|---|---|---|
| 20260906 | 1500 | cohort | 146 | 6 | 4.1% | **0** | **0.0%** | 145 | 0 | 0.000666 |
| 20260906 | 1500 | comparison | 607 | 29 | 4.8% | **0** | **0.0%** | 501 | 1 | 0.000666 |
| 20260906 | 1500 | pooled | 753 | 35 | 4.6% | **0** | **0.0%** | 606 | 1 | 0.000666 |
| 20260906 | 3000 | cohort | 146 | 6 | 4.1% | **0** | **0.0%** | 143 | 0 | 0.000333 |
| 20260906 | 3000 | comparison | 607 | 30 | 4.9% | **0** | **0.0%** | 550 | 0 | 0.000333 |
| 20260906 | 3000 | pooled | 753 | 36 | 4.8% | **0** | **0.0%** | 664 | 0 | 0.000333 |
| 20260906 | 5000 | cohort | 146 | 6 | 4.1% | **0** | **0.0%** | 146 | 0 | 0.000200 |
| 20260906 | 5000 | comparison | 607 | 30 | 4.9% | **0** | **0.0%** | 571 | 0 | 0.000200 |
| 20260906 | 5000 | pooled | 753 | 36 | 4.8% | **0** | **0.0%** | 703 | 0 | 0.000200 |
| 20260906 | 10000 | cohort | 146 | 5 | 3.4% | **0** | **0.0%** | 146 | 0 | 0.000100 |
| 20260906 | 10000 | comparison | 607 | 30 | 4.9% | **0** | **0.0%** | 589 | 0 | 0.000100 |
| 20260906 | 10000 | pooled | 753 | 35 | 4.6% | **0** | **0.0%** | 727 | 0 | 0.000100 |
| 31337 | 1500 | cohort | 146 | 9 | 6.2% | **0** | **0.0%** | 139 | 0 | 0.000666 |
| 31337 | 1500 | comparison | 607 | 35 | 5.8% | **0** | **0.0%** | 501 | 1 | 0.000666 |
| 31337 | 1500 | pooled | 753 | 44 | 5.8% | **0** | **0.0%** | 594 | 1 | 0.000666 |
| 31337 | 3000 | cohort | 146 | 10 | 6.8% | **0** | **0.0%** | 139 | 0 | 0.000333 |
| 31337 | 3000 | comparison | 607 | 36 | 5.9% | **0** | **0.0%** | 548 | 0 | 0.000333 |
| 31337 | 3000 | pooled | 753 | 46 | 6.1% | **0** | **0.0%** | 661 | 0 | 0.000333 |
| 31337 | 5000 | cohort | 146 | 10 | 6.8% | **0** | **0.0%** | 145 | 0 | 0.000200 |
| 31337 | 5000 | comparison | 607 | 34 | 5.6% | **0** | **0.0%** | 562 | 0 | 0.000200 |
| 31337 | 5000 | pooled | 753 | 44 | 5.8% | **0** | **0.0%** | 690 | 0 | 0.000200 |
| 31337 | 10000 | cohort | 146 | 10 | 6.8% | **0** | **0.0%** | 145 | 0 | 0.000100 |
| 31337 | 10000 | comparison | 607 | 35 | 5.8% | **0** | **0.0%** | 586 | 0 | 0.000100 |
| 31337 | 10000 | pooled | 753 | 45 | 6.0% | **0** | **0.0%** | 725 | 0 | 0.000100 |
| 99991 | 1500 | cohort | 146 | 6 | 4.1% | **0** | **0.0%** | 133 | 0 | 0.000666 |
| 99991 | 1500 | comparison | 607 | 25 | 4.1% | **0** | **0.0%** | 499 | 1 | 0.000666 |
| 99991 | 1500 | pooled | 753 | 31 | 4.1% | **0** | **0.0%** | 586 | 1 | 0.000666 |
| 99991 | 3000 | cohort | 146 | 5 | 3.4% | **0** | **0.0%** | 140 | 0 | 0.000333 |
| 99991 | 3000 | comparison | 607 | 24 | 4.0% | **0** | **0.0%** | 556 | 0 | 0.000333 |
| 99991 | 3000 | pooled | 753 | 29 | 3.9% | **0** | **0.0%** | 669 | 0 | 0.000333 |
| 99991 | 5000 | cohort | 146 | 5 | 3.4% | **0** | **0.0%** | 145 | 0 | 0.000200 |
| 99991 | 5000 | comparison | 607 | 25 | 4.1% | **0** | **0.0%** | 579 | 0 | 0.000200 |
| 99991 | 5000 | pooled | 753 | 30 | 4.0% | **0** | **0.0%** | 711 | 0 | 0.000200 |
| 99991 | 10000 | cohort | 146 | 5 | 3.4% | **0** | **0.0%** | 144 | 0 | 0.000100 |
| 99991 | 10000 | comparison | 607 | 25 | 4.1% | **0** | **0.0%** | 585 | 0 | 0.000100 |
| 99991 | 10000 | pooled | 753 | 30 | 4.0% | **0** | **0.0%** | 720 | 0 | 0.000100 |

**BH-adjusted classification is 0 in all 36 cells**, at every REPS value
tested, on every synthetic draw, in every group.

## Range across the three synthetic draws (Monte Carlo stability)

Per the task's instruction, ranges are reported, not averaged:

| REPS | group | BH rate across 3 draws | range |
|---|---|---|---|
| 1500 / 3000 / 5000 / 10000 | cohort | 0.0%, 0.0%, 0.0% | **[0.0%, 0.0%]** |
| 1500 / 3000 / 5000 / 10000 | comparison | 0.0%, 0.0%, 0.0% | **[0.0%, 0.0%]** |
| 1500 / 3000 / 5000 / 10000 | pooled | 0.0%, 0.0%, 0.0% | **[0.0%, 0.0%]** |

BH rate has zero spread across draws at every REPS value — the result is
not an artifact of an unlucky single seed.

**Raw rates, for context (not the question this task answers), do show
Monte Carlo variation across draws** — cohort raw ranges 3.4–6.8% across
the three seeds (same trader set, same REPS, only the random side-draw
differs), comparison 4.0–5.9%, pooled 3.9–6.1%. All three seeds' raw
rates stay within roughly 3–7%, consistent with the ~5% chance floor
Step 1 established — no seed produced a materially inflated raw rate.

---

## The plain-language answer

**BH-adjusted classification does NOT differ materially between
REPS=1,500 and REPS=10,000 on this zero-skill population — it is
identically zero at both, and at 3,000 and 5,000 as well, across three
independent synthetic draws.**

Per the task's own framing of the two acceptable outcomes: **this is the
first one.** The 1,500-rep BH bar was not admitting false positives on
this construction; the cohort's pre-split BH classification (computed at
`REPS=1,500`, producing `N=146`) is not undermined by this specific
mechanism. **The zero-BH result at REPS=10,000 needs a different
explanation than "REPS was too coarse at 1,500" — and that explanation is
not established here.** In particular, this task does not investigate
why the 2026-09-05 REAL test found BH rates of 19.2%/29.4% while this
SYNTHETIC zero-skill construction finds 0.0% at the identical REPS=1,500
— a genuine population is not a zero-skill construction, and any
number of differences between them (market structure, real vs.
synthesized direction, position-count distribution, category mix) could
account for the gap. None of those is examined here.

---

## What was not determined

- **Why the 2026-09-05 real test's BH rates (19.2%/29.4% at REPS=1,500)
  differ from this synthetic zero-skill population's BH rate (0.0% at
  the same REPS)** — the premise this task set out to test (a REPS
  artifact) is ruled out, but no alternative explanation is established,
  investigated, or even outlined here. This was explicitly out of scope.
- **Whether raw rates' Monte Carlo range (3.4–6.8% across three seeds)
  is itself expected variation at this population size or worth a closer
  look** — reported, not interpreted.
- **Whether the same null result (BH=0 at both REPS) would hold on a
  different population** (e.g., the original 338-trader frozen
  cohort/placebo set from Step 1, or a different real population
  entirely) — only the 753-trader twice-classifiable population, already
  fixed by the persistence pre-registration, was tested here.
- **Any consequence for the §8 gate, the persistence pre-registration,
  or the pre-split cohort definition** — none drawn. The task's own
  framing states plainly what scope a "materially higher BH rate at
  1,500" finding would have reached; since that finding did not obtain,
  no such consequence is stated, and none is implied by omission either.
- **Whether `MIN_ADEQUATE_DENOMINATOR` or the §8 gate's earlier STOP
  should be revisited in light of this result** — explicitly out of
  scope per the task's instruction; not addressed.

No OBSERVATION LOG section is included — nothing surfaced during this
run beyond what the task's own reporting requirements already capture
above (the raw-rate Monte Carlo range and the pinned-at-floor/distinct-
p-value counts, both included in the results table as the task's own
requested quantities, not as separate unregistered observations).
