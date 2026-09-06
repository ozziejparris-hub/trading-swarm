# MASTER HANDOVER — 2026-09-06

**Read this first.** This document supersedes `MASTER_HANDOVER_2026-09-05.md`
as the single entry point for a new Claude chat instance picking up this
project. It covers one day (2026-09-06) in which a single arc — the
directional-skill persistence question `MASTER_HANDOVER_2026-09-05.md` §9
left as the obvious next step — was pre-registered, hit a real
prerequisite-gate failure, was amended honestly rather than routed
around, and produced a genuine, informative result. It is a snapshot, not
a living doc — cross-check `brain/decisions/` for anything newer before
trusting it blindly.

---

## 0. HOW TO START A NEW SESSION

1. Read this document, in full.
2. Read `MASTER_HANDOVER_2026-08-15.md` §1 (the `geo_elo` teardown) if you
   have not already — it is still the reason `geo_elo` must never be
   consumed for skill-ranking work. Nothing since has reopened it.
3. Read `2026-09-06-cross-arc-selection-reversal-pattern.md` before
   proposing any new selector work — it records that four independent
   selection criteria have now all shown the same reversal, and names the
   leading (untested) explanation.
4. Read `2026-09-05-canonical-skill-metric-design.md` before proposing
   any new skill measurement — Components 2 and 3 (execution, absolute
   and relative earliness) are now the most evidentially-motivated
   untested piece of this project, per §4 below.
5. Check the three services: `polymarket-monitoring`, `polymarket-observer`,
   `trading-swarm.service`.
6. Check today's `daily_maintenance.py` output for anything red, and
   specifically that the discovery-gap sweep's checkpoint files show no
   sign of having resumed — it should not have. It is formally stopped,
   not paused (see `MASTER_HANDOVER_2026-09-05.md` §3).

---

## 1. WHERE THE THESIS ACTUALLY STANDS (read this before anything else)

**The result of record: `+0.0316`, CI `[-0.0088, +0.0710]`, n=3,032/120,
`T_split=2026-04-01`.** This stands **permanently** by Oscar's explicit
decision on 2026-08-21. **Nothing today touched it** — verified again
this session: current HEAD `metric_v2f_oos_result` still carries these
exact figures, `generator_commit eaeabbc`, untouched by any 2026-09-06
write. Every measurement below is a separately-named, second figure.

### The headline finding, 2026-09-06

**Directional skill classified pre-split (PIT-legally, before `T_split`,
via the Gómez-Cram sign-flip harness) persists out-of-sample.**
Persistence rate among the 146-trader cohort: **37.0% BH-adjusted, CI
`[0.2945, 0.4521]`**, vs. **18.6%, CI `[0.1549, 0.2175]`** for the
607-trader comparison group not so classified. The gap holds up **across
all five pre-specified activity strata** (11–27 percentage points higher
for the cohort in every one of `[10,14)`, `[14,23)`, `[23,46)`,
`[46,83)`, `[83,∞)` post-split-position-count bins) — not concentrated in
any one activity level.

**Stated at the level of what this does and does not establish, because
the bar it formally cleared was a low one by construction**: the primary
axis (A1, established) required only that the real CI's lower bound
exceed a null **fixed at exactly 0%** (Amendment 2026-09-06b — see §3
below for why that null is a point, not a range). Clearing a point-mass
null at zero is not, by itself, strong evidence. **The substantive
evidence is the roughly 2x separation (37.0% vs. 18.6%) and its
consistency across every activity stratum, not the formal A1
classification alone.** The secondary comparison against Gómez-Cram's 44%
external benchmark is **unresolved** (B2 — the CI straddles it), an
expected outcome at N=146 fixed in advance by amendment, not a failure.

**Directional skill is real, persistent, and identifiable in advance in
this population, on this evidence. It does NOT convert into edge** — see
§4 (the cross-arc pattern) immediately below. This is the single most
important thing to hold in mind: this session found a genuine positive
result on the direction question the 2026-09-05 handover left open,
**and** found — for the fourth independent time — that whatever produces
tradeable edge is not what any selection criterion tried so far,
including this one's own comparison-group aggregate, is picking up.

---

## 2. THE RESEARCH THAT REFRAMED THE PROJECT (2026-09-05, unchanged)

Carried forward from `MASTER_HANDOVER_2026-09-05.md` §2, unchanged by
anything today:

- **Della Vedova (SSRN 6191618):** prediction-market returns decompose
  into a **directional** component and an **execution** component, nearly
  independent (shared variance **<1%** for humans). Execution, not
  forecasting, determines profit — no trader type in the paper's data
  beats the price-implied accuracy benchmark.
- **Gómez-Cram, Guo, Jensen & Kung (SSRN 6617059):** ~3% of Polymarket
  accounts are persistently skilled; 44% of traders classified skilled on
  a random half of their events are also skilled on the other half.

Today's persistence test is this project's own first direct test of
Gómez-Cram's persistence methodology, temporally rather than by
split-half, on this project's own population — see §3.

---

## 3. TODAY'S ARC (2026-09-06), IN SEQUENCE

1. **Null calibration** (`2026-09-06-directional-skill-null-calibration.md`,
   first-repo `f3cb201`) — the
   directional-skill harness's per-trader classification is well-
   calibrated at ~5% under a population with zero skill by construction.
   Explanation (b) (mis-specified null) ruled out for per-trader results;
   three caveats carried forward (no trader×market clustering in the
   pooled aggregate test; `SEED=42` re-seeded per call site; a ~0.00067
   p-value floor at 1,500 reps with ~15% of traders pinned).
2. **The PIT-legal pool** (`2026-09-06-directional-skill-discrepancy-pit-pool-power.md`):
   5,732 PIT-legal classifiable traders (tape_end-anchored, via the
   canonical `backtest_window_sql()`), 1,178 BH-skilled pre-split, 504
   surviving into post-split with any position. This document also
   resolved a 37.3%/39.2% discrepancy (presentational, not compositional)
   and confirmed the BH-correction implementation is genuine (its
   apparent alignment with a 0.01 threshold was coincidental).
3. **The accidental exploratory edge measurement and its custody**
   (`2026-09-06-directional-skill-exploratory-custody.md`): the PIT-pool
   power estimate produced real cohort/placebo edge figures as an
   unavoidable by-product — **NOT pre-registered, explicitly exploratory**,
   persisted to new tables only (never `metric_v2f_oos_result`), with
   trader-level membership per the Objective-1 pattern. Surfaced the
   `match_control()` determinism defect (below) along the way.
4. **The `match_control()` determinism defect and its fix**
   (`2026-09-06-match-control-determinism-fix.md`, first-repo `42b14fc`):
   `cohort_traders`/`elig_traders` are Python sets; the function iterated
   them directly before shuffling, making its output depend on
   process-level `PYTHONHASHSEED`, not just its `seed` argument. Fixed
   (`sorted()` in place of `list()`, two lines), proven by a new
   fresh-process determinism test, added to the suite. **A second named
   mechanism, alongside background-backfill drift, behind the 2026-08-16
   UNREPRODUCIBLE verdict.** Every placebo built before the fix —
   explicitly including the 2026-08-15 result-of-record placebo and the
   2026-09-06 exploratory placebo — remains unreconstructable from its
   recorded seed and was **not** recomputed.
5. **Twice-classifiable population count**
   (same doc as #4, first-repo `1d34ced`): of the 5,732 PIT-legal
   classifiable traders, **753** also have ≥10 post-split resolved
   positions; of those, **146** are the pre-split BH-skilled persistence
   cohort and **607** the comparison group. An activity imbalance was
   found (median 28.5 vs. 22.0 post-split positions) and addressed by
   pre-specified stratification, not by adjustment.
6. **External dataset scoping** (`2026-09-06-external-dataset-scoping-and-prereg-amendment.md`):
   verdict **NO** — `vgregoire/polymarket-users` cannot increase N, for
   two independently sufficient reasons: it is whole-history per-trader
   aggregates only (no per-position records at any granularity), and its
   coverage ends 2026-03-29, before `T_split`, regardless of granularity.
   Same document amended the persistence pre-registration's success
   criterion (split into primary/secondary axes) and control design
   (stratified reporting), both blind, both before any real figure
   existed.
7. **The S8 gate failure** (`2026-09-06-directional-skill-persistence-test-run.md`,
   first-repo `ea1140e`): the pre-registration's own prerequisite —
   establish an in-house null via split-half persistence on the actual
   753-trader population — produced a synthetic-cohort denominator of
   **6**, below the documented adequacy floor of 10. **Reported and
   halted, exactly as the pre-registration required.** No real
   persistence rate was computed at this stage.
8. **The REPS premise test** (`2026-09-06-reps-bh-effect-isolation.md`,
   first-repo `6dc0bf5`): tested whether the earlier BH=0 zero-skill
   result was a `REPS`-driven artifact. **Falsified**: BH-adjusted
   classification is exactly zero in all 36 tested cells (3 independent
   synthetic draws × 4 REPS values from 1,500 to 10,000 × 3 groups), zero
   spread across draws. The gap between this and the 2026-09-05 real
   test's BH rates (19.2%/29.4%) needs a different explanation, not
   established.
9. **The S8 amendment and the persistence result** (Amendment
   2026-09-06b, appended directly to
   `2026-09-06-directional-skill-persistence-prereg.md`, commit
   `7ae1845`; result in
   `2026-09-06-directional-skill-persistence-test-run-2.md`, first-repo
   `6e69bc8`): stated plainly that the S8 gate **as originally specified
   was not met**, then established the same null by an alternative,
   more thorough route (the REPS test's 36-cell agreement), fixed
   numerically at 0%, and recorded a structural point — a well-calibrated
   null on zero-skill data is nearly empty by construction, so the
   split-half method's denominator may be an unfixable shape, not a
   sample-size problem. The real test then ran to completion: **outcome
   cell A1×B2**, detailed in §1 above.

---

## 4. THE CROSS-ARC PATTERN (new, cross-linked)

**`2026-09-06-cross-arc-selection-reversal-pattern.md`** records that
across **four independent selector tests** — presplit-edge selection (the
2026-08-15 result of record, CI-overlapping, and its later reversal in
the 2026-09-05 N=0 gap check), the 2026-09-05 directional-skill test, the
2026-09-06 exploratory PIT figures, and today's persistence-test
aggregate — **the non-selected group has matched or outperformed the
selected group on edge, every time.**

Argued there, not repeated in full here: this is evidence about the
*structure of what is being measured*, not four independent
disappointments, precisely because a selector failing randomly is
uninformative while four selectors failing in the same direction is not.
**Leading candidate explanation, explicitly labelled UNTESTED**: Della
Vedova's <1% shared-variance decomposition — selecting hard on direction
produces no execution advantage, while the unselected remainder retains
the population's average execution. **Separately flagged open question,
not answered**: today's comparison group's own significant positive
aggregate edge is itself unexplained — execution effect or structural
artifact, not established.

---

## 5. WHERE THIS LEAVES THE STANDING OBJECTIVE

The project's standing objective: identify traders who are profitable,
and rate them continuously. Today's evidence bears on it as follows,
stated as read, not as decided:

- **Direction is a genuine, identifiable, persistent trait** in this
  population — the first clean positive result of this entire retrospective
  arc, after presplit-edge, the original directional test, and the
  exploratory PIT figures all came back null-or-reversed.
- **Direction is very likely the wrong trait to select ON for
  profitability**, per the cross-arc pattern in §4 — selecting on it (or
  on its noisy edge-proxy) has not concentrated edge in four independent
  attempts.
- **The execution dimension — Components 2 and 3 of the canonical skill
  metric design (absolute and relative earliness), proposed
  2026-09-05, never tested** — is where the evidence now points, per
  both Della Vedova's own framing and the pattern in §4. This is a
  proposal, not a decision — see §8.

---

## 6. THE DISCOVERY-GAP ARC AND THE CLASSIFIER ARC (unchanged, carried forward)

Nothing today touched either. Full detail remains in
`MASTER_HANDOVER_2026-09-05.md` §3–§4; summarized for continuity:

**Discovery-gap sweep**: a genuine, real, and growing finding (203/317
undiscovered-resolved markets in the canonical population) led to an
11-day, 215,887-market sweep whose actual yield to the canonical
population was 267 markets (0.12%) — a wrong-turn in *sequencing*
(a cheap premise check that would have predicted this exact yield was
available from day one but not run until day 9) rather than in the
underlying diagnosis. **Formally STOPPED (2026-09-04), not paused. Do
not resume.**

**Relevance classifier**: built to address `category='Unknown'` on 99.9%
of sweep-resolved markets. Gate result: precision passed, recall failed
(90.35% vs. ≥95%, all six stratified cells failed). Diagnosis: 79%
genuine classifier misses, diffuse across 18 unrelated market subtypes —
§3.11(a) abandon indicated. **Oscar's formal §3.10 adjudication and blind
spot-check remain OUTSTANDING** — still true today, not resolved this
session.

---

## 7. WHAT WAS BUILT AND IS LIVE (today's additions on top of 2026-09-05 §5)

Everything in `MASTER_HANDOVER_2026-09-05.md` §5 stands unchanged. Added
today:

- **PIT-legal population infrastructure**:
  `scripts/directional_skill_pit_legal_pool.py`,
  `scripts/directional_skill_twice_classifiable_population.py` — the
  first scripts in either repo to call the canonical `backtest_window_sql()`
  directly for this purpose (existing bypasses in `trader_skill_metric_v2f.py`
  and `directional_skill_diagnostic.py` were logged, not fixed).
- **`match_control()` determinism fix** (first-repo `42b14fc`) +
  `tests/test_match_control_determinism.py`, now in the suite.
- **`scripts/persist_directional_skill_pit_exploratory.py`** — the
  exploratory-figure custody pattern (new tables, trader-level membership,
  explicit `is_exploratory`/`is_preregistered` flags).
- **`scripts/directional_skill_reps_bh_effect.py`** — the REPS premise
  test, reusable for any future REPS-sensitivity question on this
  harness.
- **`scripts/directional_skill_persistence_test.py`** — the persistence
  test itself, now reflecting Amendment 2026-09-06b's fixed null (updated
  from its first, S8-gate-stopped version at `ea1140e` to the completed
  version at `6e69bc8`).
- **`scripts/external_dataset_scoping_check.py`** — read-only schema/
  coverage/overlap inspection for `vgregoire/polymarket-users`; concluded
  it cannot contribute to this or (on the same grounds) any post-split
  measurement.

---

## 8. KNOWN DEFECTS, LIVE AND UNFIXED (carried forward from 2026-09-05 §6)

All eight items from `MASTER_HANDOVER_2026-09-05.md` §6 stand exactly as
recorded there — `last_checked`/195,625 stranded markets;
`category='Unknown'` on 99.9% of sweep-resolved markets; zero maker-side
`is_taker` rows; nine independent classification code paths;
`composite_skill_score.py` dead code; inert ELO behavioural modifiers;
eight unguarded cron wrappers; `discover_leaderboard_traders.py` runtime
growth; ~300 markets/day ingest drop. **Not reproduced verbatim here to
avoid drift between two copies — read them at the source.**

The ninth item, `match_control()`'s seed-nondeterminism, is now **FIXED**
(first-repo `42b14fc`, same-day) — full detail already in that section
and in `2026-09-06-match-control-determinism-fix.md`. No new defect was
found today beyond this one.

---

## 9. PRE-REGISTRATIONS WRITTEN AND THEIR STATUS

Carried forward from `MASTER_HANDOVER_2026-09-05.md` §7, plus today's
additions:

- Discovery-gap-closure, Track 2 CI power, copy-trade decay, the original
  directional skill test, the canonical skill metric design — unchanged,
  see the 09-05 handover for full status on each.
- **Directional-skill persistence** (`2026-09-06-directional-skill-persistence-prereg.md`,
  `7743740`, amended twice — `a4b6494` split-criterion/stratification,
  `7ae1845` S8-null-by-alternative-route) — **RUN**, outcome **A1×B2**
  (§1 above). Both amendments were committed before any real result
  existed, git-provably.
- **The canonical skill metric design's Components 2 and 3** (absolute
  and relative earliness) — **still never tested**, and now the most
  evidentially-motivated open item in the project per §4/§5 above.

---

## 10. WHAT IS EXPLICITLY NOT WORTH RESUMING (so it is not rediscovered)

Carried forward from `MASTER_HANDOVER_2026-09-05.md` §9, quoted exactly,
plus one addition:

*"the discovery-gap sweep (formally stopped, its prerequisites moot); the
relevance classifier in its current form (failed its own gate, diffuse
cause, abandon indicated); the copy-trade decay ladder in its current
form (its gate does not test the quantity that matters — amend before
running, do not run as written)."*

**New this session**: **the split-half persistence-null method, as a
general technique on this project's own well-calibrated harness.**
Recorded in Amendment 2026-09-06b: a well-calibrated null on zero-skill
data is nearly empty by construction (near-zero base rate → almost no
synthetic "skilled" traders on a first half → a tiny split-half
denominator), so growing the population grows split-half *eligibility*
without growing the count that actually clears significance on a first
half. **This may be an unfixable shape, not a sample-size problem** — do
not retry it expecting a larger population alone to fix it; if an
in-house null is needed again, the alternative-route approach used this
session (direct chance-floor classification rate across independent
synthetic draws and REPS values) is the demonstrated working method.

---

## 11. OUTSTANDING DECISIONS — EXPLICITLY OSCAR'S, NOT PROPOSED HERE AS DECIDED

- **The relevance-classifier gate adjudication and blind spot-check**
  (§6 above / `MASTER_HANDOVER_2026-09-05.md` §4) — still outstanding,
  unchanged by anything today.
- **The `last_checked` fix and the 195,625 stranded markets** (§8 above)
  — still outstanding, still growing.
- **Whether to pre-register an execution-dimension test next**
  (Components 2/3, §4/§5/§9 above) — **proposed, not decided.** This is
  new framing from this session, not a restatement of prior text: the
  2026-09-05 handover named Components 2/3 as untested and evidentially
  relevant; today's cross-arc pattern (§4) is what specifically motivates
  treating this as the *next* candidate test, ahead of any other open
  item. Whether to actually pre-register and run it is not decided by
  this document.

---

## 12. REUSABLE LESSONS

**A discrepancy worth flagging, not silently reconciled**: this document
was asked to carry forward "the standing methodology rules." A section by
that exact name — "STANDING METHODOLOGY RULES" — exists only in
`MASTER_HANDOVER_2026-08-15.md` §7 (six rules: reproducibility,
pre-registration, boundary checks, empirical field semantics, calibration
plots as a precondition, test-the-premise-before-building-the-instrument).
`MASTER_HANDOVER_2026-09-05.md` did **not** carry that section forward
under that name or reproduce its content — it substituted a different,
newer, session-specific "REUSABLE LESSONS" section (§8 there) covering
lessons from the 2026-08-16→09-05 window specifically. **The two are not
simple supersets of each other**, and 2026-09-05 already made the choice
not to merge them. This document follows that same precedent — carrying
forward 09-05's own §8 as the operative "lessons" section (all six
items stand unchanged, not reproduced verbatim here to avoid drift; read
them at the source) — and adds one new lesson from today, rather than
attempting to retroactively merge in 08-15's original six rules, which
neither this document nor 09-05's construction attempted.

**New this session**: **a purpose-vs-method distinction is the correct
basis for amending a pre-registered gate that fails, and it is different
from abandoning the gate.** The S8 gate's *specified method* (split-half
persistence) failed on inadequate denominators; its *purpose* (establish
a trustworthy null) was then satisfied by a different, independently
verified route (the REPS test's 36-cell agreement). The amendment stated
both facts plainly — the gate as specified was not met, and the purpose
was nonetheless served — rather than either silently declaring the gate
"met" by a different measure, or abandoning the test because its first
specified method failed. This is now the demonstrated pattern for this
situation going forward, not a one-off.

---

*This document was generated by Claude (chat instance) on 2026-09-06 at
Oscar's request, to replace `MASTER_HANDOVER_2026-09-05.md` as the entry
point for new-chat handoff. Every figure restated here was checked
against its committed source before inclusion, per this project's own
standing lesson (`MASTER_HANDOVER_2026-09-05.md` §8, "Chat-Claude's
premises enter the record and must be verified, not inherited") — the
task prompt commissioning this document itself contained at least one
imprecise framing (Instance 1 of the cross-arc pattern, §4 above, and
the "standing methodology rules" naming, §12 above), both corrected
against source rather than carried through unchecked. Treat this
document as a snapshot — verify anything load-bearing against current
repo state before relying on it if significant time has passed.*
