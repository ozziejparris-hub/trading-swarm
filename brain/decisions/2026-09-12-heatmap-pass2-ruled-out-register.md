# Heatmap Pass 2 of 5 — The Ruled-Out Register

**Date:** 2026-09-12
**Depends on:** Pass 1 (asset inventory), trading-swarm `1bb36e1`,
`brain/decisions/2026-09-12-heatmap-pass1-asset-inventory.md` + `.json`. Asset IDs
below (e.g. `data_d7`, `instr_v6`, `condemned_c1`) refer to that document.

**Scope:** what has been RULED OUT, graded by strength. Not what to try next (pass 3+),
not ranked by promise (pass 4), no external research (pass 5). Grading is the entire
output of this pass.

---

## Grading scale (used exactly as defined, reproduced here for reference)

| Grade | Meaning |
|---|---|
| **CLOSED-STRONG** | Falsified by a well-powered, pre-registered test whose own stop conditions fired correctly. Revisiting needs new data or a materially different question, not a better method. |
| **CLOSED-INSTRUMENT** | The instrument was found defective — the finding is about the instrument, not the world. The underlying question may be entirely open. |
| **NULL-UNDERPOWERED** | Could not distinguish the effect from zero at the available n. The most important grade in this register — not a falsification. |
| **CONFOUNDED** | Blocked before it could answer, by a population or design problem. |
| **SUPERSEDED** | Replaced by a later, better-specified version of the same question. |
| **ABANDONED-UNTESTED** | Dropped for cost/scope/judgment without ever being measured. |

---

## Sweep scope

This register cannot be built from handovers — pass 1 already established that handovers
summarize and drop exactly the detail (stop conditions, exact CIs, power analyses) this
pass needs. This pass read **primary pre-registration and result documents directly**,
split across three parallel sweeps:

**Sweep A — falsified selectors + condemned instruments.** Read in full:
`2026-09-06-directional-skill-persistence-test-run.md` (219 lines), `-test-run-2.md`
(220 lines), `2026-09-11-skilled-presence-causal-vs-compositional.md` (390 lines),
`2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md` Part 1 (lines 24-241),
`2026-08-15-skill-metric-rebuild.md` (55 lines). Key sections read (not full text):
`2026-08-21-discovery-gap-closure-prereg.md` (§E + interpretation rule, out of 1883
lines — still not read in full by either pass), `2026-09-06-directional-skill-persistence-prereg.md`
(§6-8 of 665 lines), `2026-09-10-copy-trade-decay-result.md` (§2.1-2.5 of 439 lines),
`2026-09-10-copy-trade-decay-outcome-rule-rerun.md` (§2.1-named-outcome of 420 lines).
Not read: `2026-09-05-copy-trade-decay-prereg.md` §2-9,
`2026-09-10-copy-trade-decay-price-substitution-verification.md` (283 lines).
**Correction to this pass's own working assumption:** `2026-08-21-discovery-gap-closure-prereg.md`
is not the founding pre-registration of `metric_v2f_oos_result` — it is a later
pre-registration for a resolution-discovery-gap-closing sweep that treats the result as
an already-existing protected artifact. The founding pre-registration of the result of
record itself was not conclusively identified by either pass.

**Sweep B — abandoned arcs.** Read in full: `2026-08-31-relevance-classifier-design.md`
(560 lines), `2026-09-03-gate-result.md` (414 lines), `2026-09-04-gate-recall-diagnosis.md`
(175 lines), `2026-09-04-limit-restore-and-sweep-closure.md` (187 lines),
`2026-09-05-n0-gap-check.md` (~265 lines), `2026-06-01-str003-002-retired.md`,
`2026-06-30-str002-thesis-cell-analysis.md` (141 lines), `2026-06-10-str003-scoring.md`,
`brain/strategy-registry.md` (534 lines, the canonical strategy record — **last touched
2026-06-12, commit `1e64586`**, three months stale as of this pass, see Meta-Finding
below), `2026-09-05-timing-execution-inventory.md` (189 lines). Excerpted only:
`2026-09-05-copy-trade-decay-prereg.md` (~80 lines around its amendment). Grepped, not
read: `2026-08-21-discovery-gap-closure-prereg.md`, `2026-09-05-timing-execution-inventory.md`
cross-references.

**Sweep C — RQ-identifier catalogue.** Read in full: `brain/strategy-notes/research-directions.md`
(1,626 lines, the master living RQ registry), `2026-06-29-pool-c-decline-investigation.md`,
plus relevant sections of `2026-08-16-comprehensive-elo-dependency-trace.md`,
`2026-08-31-geo-scoping-inventory.md`, `2026-06-29-overhang-ledger.md`. ~30 more docs
grepped for last-mention dates only (not read in full) — these back the
lowest-confidence entries below, flagged individually.

**Combined document count:** approximately 24 documents read in full or in
substantial part across all three sweeps this pass (on top of pass 1's 24), against
the ~220-document gap pass 1 left. Still not independently read by either pass:
`2026-08-21-discovery-gap-closure-prereg.md` in full (1883 lines — cited by multiple
downstream documents but never opened cover-to-cover), `2026-09-05-copy-trade-decay-prereg.md`
§2-9, `2026-09-10-copy-trade-decay-price-substitution-verification.md`.

**Safety check:** `metric_v2f_oos_result` sha256 reconfirmed unchanged before this pass
began: `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`. No writes made.

---

## A. Falsified selectors (thesis-level rulings)

### A1. Presplit-edge selection — the result of record
**Question:** Do traders selected by pre-split market-relative edge show a real
out-of-sample edge?
**Grade: NULL-UNDERPOWERED**
**Measured:** cohort +0.0316, CI [−0.0088, +0.0710] (width 0.0798), n=3,032
positions/120 traders; placebo +0.0127, CI [−0.0210, +0.0461].
**Docs:** `metric_v2f_oos_result` (`data_d7`), generated 2026-08-15T19:36:56, commit
`eaeabbc`. Founding pre-registration not conclusively identified by either pass — the
55-line `2026-08-15-skill-metric-rebuild.md` is a summary, not a power-analysis-bearing
pre-registration. `2026-08-21-discovery-gap-closure-prereg.md` (`226e01f`) governs the
result's protection and specifies a planned "corrected" recomputation into
`metric_v2f_oos_result_corrected` — **this table does not exist in pass 1's 63-table DB
audit**, confirming that recomputation was never executed (consistent with A-adjacent
entry C2, the sweep's 2026-09-04 stop).
**What would reopen it:** no formal power analysis was found in any document read. A
rough scaling from the reported CI (half-width ≈0.0399 implies SE≈0.0204; excluding
zero at the same point estimate needs SE<0.0161) suggests roughly 1.6× the effective
independent trader-clusters (~192 vs 120) — **this is this pass's own back-of-envelope
scaling, not a project-stated power target**, flagged as such.
**Pass-1 assets consumed:** `data_d7`, `data_d8`, `instr_v4`, `instr_v5`, `instr_v6`,
`data_d9`.
**Dead as result of ruling:** none — the result stands permanently by Oscar's decision
(2026-08-21), not abandoned. The pre-registered "corrected recomputation" is itself
effectively ABANDONED-UNTESTED (see C2).

### A2. Directional-skill persistence — S8 original split-half null method
**Question:** Can an in-house zero-skill persistence null be established via split-half
classification on the actual twice-classifiable population?
**Grade: CONFOUNDED** (immediately superseded within the same arc by an alternative
route — see A3/A4)
**Measured:** synthetic-cohort split-half denominator = 6, below the pre-declared
adequacy floor `MIN_ADEQUATE_DENOMINATOR=10` (comparison=16, pooled=15 both cleared
it). Population 753 traders (28,563 synthetic positions), REPS=10,000,
`SYNTH_SEED=20260906`.
**Docs:** `2026-09-06-directional-skill-persistence-test-run.md` (script `ea1140e`),
prereg `2026-09-06-directional-skill-persistence-prereg.md` (`7743740`).
**What would reopen it:** a persistence-cohort-specific population >~250-300 traders
with ≥20 positions each (vs. the 146-trader cohort's actual size) — current post-split
trading activity cannot supply this without new history accumulating.
**Consumed:** `instr_v7`, `data_d10`.
**Dead as result:** none — halted correctly per its own pre-registration, not abandoned.

### A3. Directional-skill persistence — Gómez-Cram 44% external-benchmark comparison
**Question:** Does this project's own persistence rate (37.0%) match Gómez-Cram's
external 44% benchmark?
**Grade: NULL-UNDERPOWERED**
**Measured:** CI [0.2945, 0.4521], width 0.1576 (15.76pp), straddles 0.44. The
amendment's own closed-form pre-registered estimate predicted ~8pp width at N≈146 —
the realized width is roughly 2× that prediction.
**Docs:** prereg `7743740` + amendments `a4b6494`, `7ae1845`; result
`2026-09-06-directional-skill-persistence-test-run-2.md`, first-repo `6e69bc8`.
**What would reopen it:** roughly ~185+ cohort traders (rough scaling from N=146, not a
formal power calculation) — the pool is currently fixed at 146 pre-split-BH-skilled
traders.
**Consumed:** `instr_v7`.
**Dead as result:** none. (Note: the primary axis, A1×B2 — does persistence exceed a
fixed 0% null — is **not** a ruling; it's a real positive result. Only this secondary
comparison and A4 below are ruled-out entries within this otherwise-live arc.)

### A4. Directional-skill persistence — aggregate two-way clustered edge test
**Question:** Does the persistence cohort show a real aggregate edge, measured the same
way as the result of record?
**Grade: NULL-UNDERPOWERED**
**Measured:** cohort point_gap 0.0115, CI [−0.0151, 0.0362] (includes zero), n_pairs=3,025
— versus the comparison group's own result, which **excludes** zero (0.0210,
[0.0044, 0.0376], n_pairs=10,827). The "wrong direction" pattern recurring for the 4th
time in this project's history, per the source document's own framing.
**Docs:** `2026-09-06-directional-skill-persistence-test-run-2.md` §4.
**What would reopen it:** larger n_pairs for the cohort specifically (currently 3,025
vs. the comparison group's 10,827) — a sample-size asymmetry baked into the cohort
definition, not fixable without redefining who qualifies.
**Consumed:** `instr_v7`, `instr_v5`.
**Dead as result:** none.

### A5. Copy-trade decay — original 2026-09-10 run (pre-fix)
**Question:** Does copy-trade edge survive past the 15-minute monitoring cadence?
**Grade: CLOSED-INSTRUMENT** (superseded by A6)
**Measured:** apparent rise from N=0 (+0.01208, CI [−0.0017, +0.0265]) to a plateau
+0.033-0.037 across N=1min-60min, CI excluding zero from N=1min through N=1440min — later
found to be a measurement artifact: opposite-outcome substituted trades were not
converted (should be `1−q`, left as `q`), contaminating results with a rising
opposite-outcome share (34.6%→~40% across the ladder).
**Docs:** `2026-09-10-copy-trade-decay-result.md`, first-repo `c9619a4`.
**Open question if instrument were sound:** answered by A6 — not open, SUPERSEDED.
**Consumed:** `instr_v3`, `data_d8`, `instr_v5`.
**Dead as result:** the original artifact's specific numeric curve (characterization
JSON `copy_trade_decay_20260910T191052Z.json`) is known-wrong and superseded — kept as
record, not deleted, but its conclusions are dead.

### A6. Copy-trade decay — corrected re-run (Amendment 2026-09-10b)
**Question:** Does copy-trade edge survive past the 15-minute monitoring cadence,
correctly measured?
**Grade: CLOSED-STRONG**
**Measured:** named outcome **COLLAPSES-BEFORE-CADENCE**. At N=15min (broad PIT-legal
pool, primary=convert): +0.01233, CI [−0.00186, +0.02410], n_pairs=19,495 (36,121
positions, 3,207 traders, 1,797 markets) — not thin. No rung at or beyond N=15min, on
any of 3 populations, under either construction (convert vs. matched-only), excludes
zero. Per-category: geopolitics N=15min +0.01077 CI [−0.00468, +0.02602]; elections
+0.01629 CI [−0.01230, +0.04519] — neither clears its cost floor.
**Docs:** prereg `2026-09-05-copy-trade-decay-prereg.md` + Amendment 2026-09-10
(`7b9e1e7`) + Amendment 2026-09-10b (`e8eca1c`); result
`2026-09-10-copy-trade-decay-outcome-rule-rerun.md`.
**What would reopen it:** the source document itself states re-running with a different
substitution rule is "not an acceptable resolution" and calls this "the last word on the
rule." Reopening needs fundamentally new sub-12-minute-granularity market microstructure
data this project does not currently capture (the trade tape has no trades within
~12-22 min of a typical entry, so N=1min-15min sample the same practical window).
**Consumed:** `instr_v3`, `instr_v5`, `data_d8`.
**Dead as result of ruling:** the canonical skill metric design's Components 2/3
(absolute/relative earliness, `built_b3`) are now moot **specifically as capturability
questions** (explicitly stated in the source doc) — though `built_b3`/`timing_score` may
still have value as a description dimension. Bears directly on Phase 2 (forward paper
trading): "there is nothing an outside copier could inherit."

### A7. Copy-trade decay ladder's original gap-pinned framing
**Question (as originally posed):** Does the presplit-edge cohort's advantage over a
matched placebo survive being copied at increasing delay N?
**Grade: SUPERSEDED**
**Measured:** `2026-09-05-n0-gap-check.md` computed the N=0 gap directly — the
necessary premise before running a decay ladder against a gap-pinned bar. Result: gap
point estimate **−0.0072**, paired 95% CI **[−0.0570, +0.0435]** — reversing the result
of record's `+0.0189`, straddling zero. The pre-registration's own §4 gate only tested
the cohort's own point estimate/sign, never the gap itself.
**Successor:** the 2026-09-05(b) amendment to `2026-09-05-copy-trade-decay-prereg.md`
(written blind, before any N>0 figure existed) states: "With no demonstrated gap, a
gap-pinned bar makes this measurement permanently unrunnable — which is why it has
never run." It replaces the primary population with the broad PIT-legal classifiable
pool (5,732 traders) and asks "does any measurable edge survive being copied?" instead
— this is A6 above, the version actually executed.
**What would reopen the original framing:** a newly demonstrated, CI-excludes-zero
presplit-edge gap at N=0 on fresh out-of-sample data — current cohort/placebo lists are
exhausted and non-reconstructable pre-`42b14fc` (`instr_v6`).
**Consumed:** `data_d7`, `instr_v6`, `instr_v5`.
**Dead as result:** no code deleted — the gap-pinned §4 gate is superseded in-place by
appended amendment, not rewritten.

### A8. Skilled-presence as a mispricing marker
**Question:** Does the presence of a directionally-skilled trader in a market mark that
market for later mispricing, beyond what any active, well-matched trader cohort would
predict?
**Grade: CLOSED-STRONG**
**Measured:** Part 1 base-rate gap +3.97pp [+2.16, +5.78] (did not trip the 10pp stop).
Part 2 matched comparison (2,743 matched pairs, 66.4% match rate): direction preserved
at 6/6 horizons (did not trip stop, proceeded to Part 3). Part 3 placebo (1,494
activity-matched, non-skill-selected traders, `match_control()`, seed=42):
**replicated the elevation at 4/6 horizons at near-identical magnitude** (e.g. ~0.5h:
matched-present-skilled 1.369 vs placebo-present 1.352; matched-absent-skilled 1.200 vs
placebo-absent 1.220) — stop condition tripped, halted before Part 4.
**Docs:** `2026-09-11-skilled-presence-causal-vs-compositional.md`, first-repo
`e3ac29e`.
**What would reopen it:** the source document states this "can rule out 'skill
explains most/all of the gap'; it cannot rule out a small residual skill-specific
contribution beneath the placebo's own noise floor" — reopening needs either much
larger n to shrink the placebo's noise floor, or a within-category (not pooled) placebo
replication, neither attempted.
**Consumed:** `instr_v3`, `instr_v4`, `instr_v5`, `instr_v6`, `instr_v8`, `data_d5`.
**Dead as result:** no code killed — Part 4 was never built (gated closed by design).
The underlying question is now closed; no asset was previously live on this specific
claim.

### A9. LEGENDARY tier as a conditioning variable on mispricing
**Question:** Does LEGENDARY-tier trader presence in a market mark it for later
mispricing?
**Grade: CLOSED-STRONG**
**Measured:** n=9 traders, 697 markets present. Part 1 base rate +4.15pp [+0.54,
+7.77] (did not trip). Part 2 matched comparison (650 pairs): **direction reverses at
5/6 horizons** (e.g. ~3h: matched-present 1.147 vs matched-absent 1.398; only ~3d
preserves direction) — stop tripped, halted before Part 3 (placebo never run for this
arm).
**Docs:** `2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`,
trading-swarm `8c7e146`.
**What would reopen it:** n=9 is intrinsically small — a design feature of the
condemned LEGENDARY definition (`condemned_c2`), not a power problem this test could
fix. Reopening needs a differently-defined "elite" tier built on a sound instrument
(see B2 below).
**Consumed:** `instr_v6`, `condemned_c2`, `built_b2`.
**Dead as result:** confirms `condemned_c2`'s earlier overlap-based finding with a
stronger, causally-informative method (matching, not counting) — reinforces, doesn't
newly kill.

### A10. NEAR_LEGENDARY tier as a conditioning variable
**Grade: CLOSED-STRONG**
**Measured:** n=26 traders, 921 markets present. Part 1 base rate +0.19pp [−2.90,
+3.28] (~zero). Part 2 matched comparison (784 pairs): direction preserved at only 3/6
horizons (not a majority; ~3d is an exact tie, counted as not-preserved) — stop
tripped, halted before Part 3.
**Docs:** same as A9.
**What would reopen it:** same structural issue as A9 — a sound replacement tier would
need to be built first.
**Consumed:** same as A9.
**Dead as result:** none additional.

### A11. Pool C base-rate confound
**Question:** Does Pool C (broad clean-pool) trader presence mark a market for later
mispricing?
**Grade: CONFOUNDED**
**Measured:** n=4,483 traders, 8,777 markets present, 986 absent. Base rate present
30.8%, absent 14.2%, **gap +16.62pp [+14.24, +19.00]** — clears the pre-registered 10pp
stop threshold by a wide margin. Absent-of-Pool-C median market lifetime is ~3.25
minutes (0.054h) — these are markets that essentially never traded beyond their opening
print. Halted at Part 1, before any matching attempted.
**Docs:** `2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`, `8c7e146`.
**What would reopen it (concrete):** redefine the "absent" comparison population to
require a minimum trading-activity floor (a minimum n_trades or lifetime threshold), so
the comparison is Pool-C-present vs. Pool-C-absent-but-actively-traded, not
traded-vs-essentially-never-traded. A population-construction fix, not more data.
**Consumed:** `data_d3`, `built_b2`-adjacent, `condemned_c1`.
**Dead as result:** none — never reached a stage where anything could become dead.

---

## B. Condemned instruments — reframed as formal CLOSED-INSTRUMENT rulings

### B1. geo_elo / geo_elo_active
**Grade: CLOSED-INSTRUMENT** (defect detail: pass 1 `condemned_c1`)
**Open question if asked with a sound instrument:** "Is there a subpopulation of
traders with genuine directional skill in Geopolitics/Elections markets, correctly
measured?"
**Status of that question: SUPERSEDED** — now answered by a sound instrument, the
directional-skill harness (`instr_v7`, entries A2-A4): yes, directional skill is real
and persistent (37.0% vs 18.6%), though it does not convert into capturable copy-trade
edge (A6) and tier-based presence doesn't mark mispricing either (A8-A10).

### B2. LEGENDARY / NEAR_LEGENDARY tier ladder
**Grade: CLOSED-INSTRUMENT**, compounded by the direct empirical CLOSED-STRONG findings
in A9/A10 — the ladder is defective as an instrument AND, taken at face value, fails as
a conditioning variable.
**Open question if asked with a sound instrument:** "Does presence of a genuinely
well-identified skilled-trader tier mark a market for mispricing?" — the generalized
form of this question is **already answered CLOSED-STRONG by A8**, which used the sound
directional-skill classification, not geo_elo tiers. No need to re-ask with a rebuilt
tier ladder.

### B3. comprehensive_elo
**Grade: CLOSED-INSTRUMENT** — weaker citation than B1 (pass 1 already noted this: the
formula defect is flagged as "analogous sign-error pattern... still open and
live-affecting" but not root-caused to the same specificity as geo_elo, in anything
read across both passes).
**Open question:** unclear whether this maps to the same directional-skill question as
B1 or a distinct one (comprehensive_elo appears to blend multiple signal types, not
just geo/elec directional calls) — **genuinely still open**, not confidently
supersedable into `instr_v7` without further investigation neither pass has done.

### B4. calibration_analysis.py
**Grade: CLOSED-INSTRUMENT** — same weak-citation caveat as B3; open question not
independently characterized in anything read across both passes. Flagged as needing its
own investigation before any open-question claim can be made with confidence.

### B5. RQ-CONTESTED-001 (the comprehensive-ELO contested-price validation)
**Question:** Does a real skill separation appear when conditioning on contested-price
(non-consensus) markets, using comprehensive_elo/geo_elo/LEGENDARY tiers?
**Grade: CLOSED-INSTRUMENT**
**Measured:** reported PASS 2026-06-05 (QUALIFIED 66.3%, n=101; LEGENDARY-only 49.2%,
"comprehensive_elo contamination confirmed" even at the time) — but the tiers it
validated were condemned 2026-08-15 (`condemned_c1`/`c2`/`c3`).
**Open question if re-asked with a sound instrument:** does a real skill separation
appear on contested-price markets? Not yet re-asked with `instr_v7`.
**Consumed:** `condemned_c1`, `condemned_c2`, `condemned_c3`.

### B6. RQ-GEO-ELO-001 (`scripts/calculate_geo_elo.py`)
**Grade: CLOSED-INSTRUMENT**
**Measured:** its v2 artifact was found to be a second, diverged, contract-violating
`geo_elo` writer with no WHERE clause (mass-wipe risk) — removed from the production
path.
**Consumed:** `condemned_c1`.
**Dead as result of ruling:** `calculate_geo_elo.py` — the one clear instance in this
entire register of code killed directly by evidence rather than by neglect.

---

## C. Abandoned arcs

### C1. Relevance classifier — validation gate
**Question:** Can the cascade classifier (deterministic slug/title pre-filter → local
LLM on residual) reach ≥95% relevance recall, ≥90% directional agreement, and pass
precision/adjudication thresholds, to become the canonical `markets.category` decision
authority?
**Grade: CLOSED-STRONG on the measured recall question. The arc's institutional
disposition is unresolved — a human decision is outstanding.**
**Measured:** full run against the live 12,052-row corpus (8,005 Elections/4,047
Geopolitics), zero classify errors. Overall relevance recall **90.35%** (10,889/12,052)
vs. ≥95% — **FAIL**, 561 rows short (4.6pp under, not a near-miss). All 6 per-stratum
cells FAIL (87.62%-92.49%). Directional agreement 90.12% — PASS, narrowly (12 rows
above minimum). Precision PASSED on all 3 measures. A follow-up 100-row diagnostic
(seed 20260904) found **79% of disagreements are genuine classifier misses**, not stale
ground truth (8% stored-label errors, 13% ambiguous) — even the most classifier-favorable
reading leaves 85.9% as clear misses, diffuse across 18 subtypes (largest single
pattern 39%), plus an insufficient batch-position degradation effect (5.6%→12.2%
NotRelevant rate, position 1→20). The diagnostic's own conclusion: matches its design's
§3.11(a) **abandon** criterion, not §3.11(b) **retry**.
**Docs:** design `2026-08-31-relevance-classifier-design.md` (`e601648`); gate result
`2026-09-03-gate-result.md` (classifier `5d2a090`, gate-sets `26cb147`/`f75e1ea`);
diagnostic `2026-09-04-gate-recall-diagnosis.md` (source data `a7aa610`).
**Explicitly pending:** the design names **Oscar** as the §3.10 adjudicator and reserves
the abandon-vs-retry call (§3.11) for him; the gate-result document deliberately
declines to declare an overall verdict, and nothing after 2026-09-04 records that
adjudication happening.
**What would reopen/close it:** formally, nothing reopens the measurement — the corpus
is spent per §3.11.2, re-measurement not permitted. What's needed to *close* it is
Oscar's §3.10 adjudication (over the fully-characterized disagreement pools: 1,163
NotRelevant + 1,076 directional mismatches, 10 precision disagreements) and his
§3.11(a)/(b) call.
**Consumed:** `built_b8` — this pass **resolves** pass 1's "unclear if ever run" flag on
`run_relevance_gate.py`: it was run, 2026-09-03, with real `classify_batch()` calls.
Also `data_d3`.
**Dead as result:** nothing yet — `backfill_market_categories.py` (M9) remains the live
nightly writer by design (repoint happens only after gate passes, which it hasn't). The
new module (`relevance_classifier.py`) is built but never repointed into production —
this is `built`-class (pass 1's class 3), not evidence-killed.

### C2. The discovery-gap-closure sweep
**Question:** Can an unscoped, multi-tranche CLOB-driven resolution sweep of the ~510k
`Unknown`-category backlog materially grow the canonical Geo/Elec thesis population?
**Grade: ABANDONED-UNTESTED**, for the part that mattered — the sweep answered a
*different, easier* question (can it resolve markets at all — yes, 215,887) while the
motivating question (can it grow the *canonical categorized* population) was blocked by
C1's classifier failure before the sweep's own segment 5 ever ran.
**Measured:** 215,887 markets resolved across tranches 1-2 + segments 1-4. Of those,
only **267 (142 Elections, 125 Geopolitics) reached target categories — 0.12%** of the
sweep's own output. The original 2026-08-20 finding (203 markets) is fully closed, but
by an almost entirely disjoint mechanism (Tranche 1, already-correctly-tagged markets),
not the 215,887-market sweep. **Segment 5 never ran** — paused 2026-08-26/27 pending
three prerequisites, no document after 2026-08-27 mentions resuming it. Formally
declared **STOPPED, not paused** 2026-09-04, prerequisites declared moot, the
16,000-market segment-4 gap accepted as permanent.
**Cost named explicitly:** 11 days of infrastructure work (08-20 sizing → 08-27 pause →
08-30 diagnosis → classifier arc → 09-03/09-04 gate failure) moved the canonical thesis
population by only **~242 markets, out of ~500 total growth over the same window** —
the closure document names the specific process failure: the cheap
classification-throughput check that determined the sweep's payoff was run 9 days
*after* a 231,000-market scope-widening it should have gated, not before.
**Docs:** `2026-08-21-discovery-gap-closure-prereg.md` (not independently read in full
by either pass); closure `2026-09-04-limit-restore-and-sweep-closure.md`; cost analysis
`2026-09-04-thesis-population-lineage.md` (cited, not independently read).
**What would reopen it:** a working relevance classifier reaching ≥95% recall (C1) —
the sweep's infrastructure (CLOB-driven resolution, canonical write path, terminal-signal
module) is explicitly named as reusable independent of the sweep's outcome, but
resuming the categorization side requires solving C1 first.
**Consumed:** `infra_o2` (`mark_market_resolved()` is the sweep's writer), `built_b8`.
**Dead as result:** `data/checkpoints/segment{3,4}_checkpoint.json` and terminal
markers — committed as closed record, not deleted, functionally inert. **Evidence-killed**
(the classifier's gate failure), not neglect — the closure doc is explicit this
supersedes, not drifts past, the 08-27 prerequisites.

### C3. STR-001 — Elite Convergence Signal
**Question:** Does 3+ legendary traders (ELO>2175) entering the same side of a market
within a short window predict the outcome?
**Grade: CLOSED-STRONG**
**Measured:** accuracy 56.1% (n=41 signals, 23 unique markets, threshold 60%) — edge
+6.1pp vs. random, below minimum. **Structural flaw beyond the missed threshold**: 78.3%
of qualifying markets (18/23) triggered signals on **both** Yes and No sides
simultaneously (legendary traders split across sides), contributing exactly 50%
accuracy by construction. 7-30 day horizon accuracy 42.9% — below random.
**Docs:** `strategy-registry.md` §STR-001, validated by backtest-agent 2026-04-27, full
report `brain/agent-outputs/backtest-agent/STR-001-validation-2026-04-27.json` (not
independently opened this pass).
**Root cause named:** legendary traders are predominantly LPs trading both sides, not
directional bettors — the convergence premise was wrong for this trader population.
**What would reopen it:** a materially different selection criterion — tried next as
STR-001b (C4), then superseded by STR-003 (C6).
**Consumed:** `condemned_c1`/`condemned_c2`-adjacent (pre-dates and is independent of
pass 1's specific sign-error findings, but shares the same LEGENDARY/ELO>2175 concept).
**Dead as result:** STR-001's own live signal generation — evidence-killed, status
SUSPENDED in the registry with a named structural flaw.

### C4. STR-001b — Elite Exclusive Convergence Signal
**Question:** Does the convergence idea work if paired-signal contamination is
excluded (3+ same side AND <2 opposing)?
**Grade: ABANDONED-UNTESTED**
**Measured:** nothing — sample-size check 2026-04-27 found **0 qualifying signals** in
historical data against the 10-signal minimum. Never reached a backtest.
**Docs:** `strategy-registry.md` §STR-001b, pre-registered and Oscar-approved
2026-04-27.
**Why dropped:** registry status SUSPENDED (not formally retired), but its own notes
record why: "legendary traders appear on both sides of markets in 95%+ of cases. The
exclusive convergence filter will almost never fire with 3+ traders" — recommends
STR-003 instead of waiting for data. **Nothing later revisits this reasoning** — it
still holds as far as this pass found.
**What would reopen it:** enough qualifying-signal data to clear n=10 — structurally
unlikely per its own diagnosis, since the underlying trader population (LPs, not
directional bettors) hasn't changed.
**Dead as result:** no code — never built past the query/sample-check stage.

### C5. STR-002
**Grade: FLAGGED, LOW CONFIDENCE** — this pass could not fully grade this entry to
standard and reports what is known rather than filling the gap with inference.
**What is known:** pass 1's DB audit found `str002_signals` at 227 rows (`data_d10`).
This pass's sweep separately queried the database directly (2026-09-12) and found **227
STR002-prefixed signal rows, of which the accuracy figure available was 34% correct** —
well below any plausible threshold used elsewhere in the STR series (STR-001's 60%
bar), suggesting this would likely grade CLOSED-STRONG if a formal pre-registered
threshold and CI were confirmed. **This pass did not locate and read the STR-002
pre-registration or a formal result document with a CI**, so the grade is withheld
rather than asserted. `strategy-registry.md` (stale since 2026-06-12) still shows "Next
revalidation due: 2026-07-01" as a *future* date, meaning even the registry's own
maintainer never saw this data.
**What would reopen/close it:** locating and reading `2026-06-30-str002-thesis-cell-analysis.md`'s
full statistical detail (only partially read this pass) and any later STR-002 scoring
document, to confirm the pre-registered threshold and compute a proper CI on n=227.
**Consumed:** `data_d10`.
**Dead as result:** unknown — flagged for a future pass or direct follow-up, not this
one.

### C6. STR-003 — Single Legendary Directional Signal
**Question:** Does a single legendary geo trader's ≥95%-of-capital directional
conviction predict the market outcome?
**Grade: NULL-UNDERPOWERED** — passed its initial small-n threshold but never reached
its own pre-registered revalidation n-target, and its data-accumulation pipeline is now
paused for unrelated reasons.
**Measured:** 2026-05-07 (RQ2.2-extended): YES 61.1% (n=18, 8 markets) — PASS vs 60%;
NO 77.8% (n=9, 6 markets) — PASS. Both clear the bar at entry-threshold n, not a
settled result — the registry's own "Next revalidation" target was **n=28 YES / n=19
NO**, "Expected ~2026-Q3." Follow-on scoring (`2026-06-10-str003-scoring.md`): 2 more
signals by 2026-06-11 (1 correct — Keiko Fujimori YES; 1 wrong — López Aliaga YES; a
third, Graham SC NO, also wrong) — nowhere near n=28/19, and no later scoring document
was found.
**CI width / what's needed:** registry states the target explicitly — n=28 YES / n=19
NO at the 95% threshold; the last dated scoring entry (2026-06-11) sits well under half
that on the NO side, roughly two-thirds on YES.
**Docs:** `strategy-registry.md` §STR-003, pre-registered 2026-04-27, promoted
EXPERIMENTAL 2026-05-07; `2026-06-10-str003-scoring.md`; `2026-06-01-str003-002-retired.md`
(one signal, STR003-002, separately retired — market never found in DB, orphaned).
**Compounding factor found this pass, not in the registry (predates it):**
`signal-agent` — "the one closest to the live thesis (STR-003 rescan...)" per
`2026-08-31-tier3-credit-shutdown.md` — was one of 5 agents disabled 2026-08-31 (pass 1
`infra_o6`). A cost-driven pause of the exact mechanism that would grow STR-003's n
toward its own revalidation target, layered on an already-underpowered result.
**What would reopen it:** re-enabling `signal-agent` (reversible, `infra_o6`) plus
accumulating to n=28 YES/n=19 NO per the registry's own stated target.
**Consumed:** `data_d10` (though STR-003 signals were not found inside `str002_signals`
— they appear to live in JSON findings under `brain/agent-outputs/`, not the DB table
pass 1 catalogued; flagged as a pass-1 coverage gap, not re-litigated here), `data_d4`.
**Dead as result:** nothing killed — signal generation paused reversibly for cost, not
because of an evidence-based ruling against STR-003 itself.

### C7. STR-004 — Capital-Weighted Legendary Aggregate Signal
**Question:** Does the capital-weighted aggregate position of all legendary traders
(including LPs/mixed holders) diverging ≥20pp from market price predict the outcome?
**Grade: ABANDONED-UNTESTED**
**Measured:** founding case only — Russia/Ukraine ceasefire, 8 legendary traders,
$1.74M total, 55.7% YES capital-weighted vs. 7% market price (48pp divergence) —
**resolved NO**. 0/1, YES accuracy 0%. Stop criterion (accuracy <50% on 10+ resolved
markets) **not triggered** — requires n=10, only n=1 ever scored.
**Docs:** `strategy-registry.md` §STR-004, pre-registered 2026-05-08
(`brain/strategy-notes/str004-preregistration-2026-05-08.md`), Oscar-approved same day.
**Why it stalled:** a 2026-06-12 note (`1e64586`, "Fable strategic roadmap") found
STR-004 was registered on `comprehensive_elo`'s LEGENDARY definition with **no
archetype filter** — 17/37 profiled LEGENDARY/near-LEGENDARY traders are
YIELD_HARVESTERs "whose capital carries no predictive signal." Verbatim: "Accumulating
more cases under the current specification builds noise, not evidence." Re-registration
under `geo_elo_active` + archetype weights was declared **required before any new case
is scored** — that re-registration was never done; no STR-004 document exists after
2026-06-13.
**What would reopen it:** the named re-specification (geo_elo_active + GENUINE_FORECASTER/
DOMAIN_SPECIALIST archetype weights only), then 10 resolved signals under the corrected
spec — none of which has happened, and the mechanism that would generate them
(`signal-agent`) is the same one paused 2026-08-31.
**Consumed:** `condemned_c1`, `condemned_c3` (founding case ran on `comprehensive_elo`,
independently untrustworthy for a second reason beyond the 06-12 archetype-contamination
finding).
**Dead as result:** nothing deleted — HYPOTHESIS status stands, unmaintained. This is
**neglect**, not evidence: the 06-12 note is real and reasoned, but its required fix was
never executed, and the registry that would track that has itself been unmaintained
since.

### C8. LH-001 / RQ-LH-001 — Lifecycle Heuristic (insider detection)
**Question:** Does entering a geopolitics market as a new, high-volume, single-event
account within 30 days of resolution predict outcome (insider/informed-money
signature)?
**Grade: NULL-UNDERPOWERED**, with its own explicit power analysis.
**Measured:** pooled signal p=0.0160 (Mann-Whitney U, n=59 candidates vs 90 controls),
rank-biserial r=0.208 — but **neither event individually significant** (Haley
p=0.1087, Iran p=0.4818); only 2 events studied against a stated adequacy floor of **7
events minimum** for cross-event generalization. Registry verdict: CONDITIONAL_PASS,
confidence LOW-MEDIUM. A later blocking-item check (2026-06-05) scored all 7 real
`insider_signals` records: 4/7 correct (57.1%) — fails the ≥60% bar.
**What would reopen it:** 5 more independent geopolitics events with 3/5 clearing
p<0.05 individually (the registry's own stated blocking item 1) — `insider_signals` has
recorded **zero** new events since 2026-05-02 (`data_d10`), so this is stalled on
population growth, not a negative finding.
**Consumed:** `data_d10`.
**Dead as result:** nothing — deployed narrowly as a watchlist trigger only, per its own
recommendation, not killed.

---

## D. Research questions (RQ register)

**35 distinct RQ identifiers found** across both repos:
RQ0, RQ0.1, RQ0.2, RQ1.1, RQ1.2, RQ1.3, RQ2.1, RQ2.2, RQ2.3, RQ3.1, RQ3.2, RQ3.3, RQ4,
RQ4.1, RQ4.2, RQ4.3, RQ4-MULTI, RQ5, RQ5.1, RQ5.2, RQ6.1, RQ6.2, RQ7.1,
RQ-CONTESTED-001 (B5 above), RQ-CONVICTION-001, RQ-CORRELATION-001, RQ-EXEC-001,
RQ-EXT-001, RQ-GEO-ELO-001 (B6 above), RQ-ILS-001, RQ-LH-001 (C8 above),
RQ-PNLGATE-001, RQ-POOL-QUALITY-001, RQ-POSSIZE-001, RQ-SCI-001, RQ-SECTOR-001,
RQ-VPIN-001.

**RQ0.1, RQ0.2** (wash-trading/bot audits) — PASSED, recurring monthly. Not applicable
to this grading scale (positive, ongoing infrastructure, not a ruling). Noted, not
graded, excluded from tallies below.

### D1. RQ1.1 — ELO persistence
**Question:** Does a trader's ELO rank in one period predict their rank in the next?
**Grade: NULL-UNDERPOWERED**
**Measured:** original run 2026-04-26: r=+0.175 (wrong-signed vs. hypothesis), p=0.52,
n=16. A pre-registered June rerun was coded (`77a10ad`) but **never executed** — "no
rq1_1_rerun_june2026.json/.md was ever produced" (first-repo `281ee19`, 2026-07-23). The
rerun's own design now carries an unmeasured O-45 resolution_date contamination risk.
**What would reopen it:** n≥20-per-period traders (the original success-criterion
floor) — the coded rerun exists and needs to actually run against `tape_end`-anchored
periods (`instr_v4`), not `resolution_date`.
**Consumed:** `data_d2`, `data_d3`, `instr_v4`.
**Dead as result:** none — coded but unexecuted, neglect not evidence.

### D2. RQ2.2 — Entry timing advantage
**Question:** Do traders who enter earlier show a directional accuracy advantage?
**Grade: NULL-UNDERPOWERED**
**Measured:** original 2026-04-26: YES n=18 (61.1%), NO n=9 (77.8%), both nominally
clear 60% but flagged INCONCLUSIVE on n alone. Extended-window (14d/30d) rerun
pre-registered for June 2026 — no result document found after 2026-06-29; not run.
**Consumed:** `instr_v3`, `built_b3`.
**Dead as result:** none.

### D3. RQ3.2 — Crowd vs elite divergence
**Question:** Does elite-consensus positioning diverge meaningfully from crowd
positioning in a way that predicts outcomes?
**Grade: CONFOUNDED (original framing)** → **ABANDONED-UNTESTED (reframe)**
**Measured:** original framing found only 4 qualifying markets after filters, vs. 50
needed — blocked before it could answer. Re-pre-registered 2026-05-29 with
LEGENDARY-consensus framing, data window "July-September 2026" — that window has now
closed (today is 2026-09-12) with **no result document found**.
**What would reopen it:** the reframe's own data window has already closed
unexecuted — reopening requires either running the reframed test against the now-closed
window's data (if still available) or defining a new window.
**Consumed:** `condemned_c2`-adjacent (LEGENDARY-consensus framing).
**Dead as result:** none.

### D4. RQ-SCI-001 — Signal credibility index validation
**Question:** Does the signal credibility index (`signal_credibility.py`, `built_b10`
per pass 1's correction — it is live, not dead) reliably discriminate credible from
non-credible signals?
**Grade: ABANDONED-UNTESTED** (for the validation study specifically)
**Measured:** nothing — the decision gate requires ≥20 resolved LEGENDARY-position
markets before SCS tiers can gate anything; never reached.
**Note:** the instrument itself is live (pass 1 corrected an initial "zero callers"
read — it has real callers in `legendary_positions_scan.py` and `register_signal.py`)
but remains annotation-only, never graduated past that gate.
**Consumed:** `built_b10`-equivalent (signal_credibility.py — cross-reference pass 1's
scripts-fork correction).
**Dead as result:** none — live but ungraduated.

### D5. RQ-EXEC-001 — Execution timing vs. directional accuracy
**Question:** Do traders who execute earlier relative to their peers show better
directional accuracy?
**Grade: NULL-UNDERPOWERED**
**Measured:** preliminary 2026-06-07 result on n=4 LEGENDARY traders (external
dataset): all correlations <0.12, LEGENDARY entered *later* not earlier (contradicts
the execution hypothesis) — explicitly caveated as n=4, "too small for robust
conclusions." Full validation deferred to "after RQ-CONTESTED-001 (July 1)" — never
resumed. Spawned RQ-CONVICTION-001 as a proposed-but-never-pre-registered follow-on
(see D9).
**What would reopen it:** the deferred validation was never resumed after its named
gate (RQ-CONTESTED-001, resolved 2026-06-05) passed — this needs someone to actually
pick it back up, not new data per se.
**Consumed:** `data_d11` (external dataset).
**Dead as result:** none.

### D6. Grouped — 15 RQs defined, never mentioned again
RQ1.2, RQ1.3, RQ2.1, RQ2.3, RQ3.1, RQ3.3, RQ4.1, RQ4.2, RQ4.3, RQ4-MULTI, RQ5.1,
RQ5.2, RQ6.1, RQ6.2, RQ7.1.
**Grade: ABANDONED-UNTESTED** (all 15)
**What happened:** each defined with a full hypothesis/test/success-criterion, either
in the original project architecture (archive `MASTER_HANDOVER_server-pre-setup-1.md`,
2026-03-17) or `research-directions.md` — **never mentioned in any later decision
document, never run**. RQ4-MULTI was additionally "APPROVED" in a 2026-04-30 triage
document but still never implemented (deferred to "Phase 4+", never reached).
**Note:** RQ4.1 (Kelly alignment vs. outcomes) is worth flagging — `kelly_alignment_score`
was later found null/negligible under Stage 0b (pass 1 `built_b5`), plausibly the same
question answered under a different name, but no document explicitly labels Stage 0b as
RQ4.1's resolution, so it is graded ABANDONED-UNTESTED rather than assumed-resolved.
**Consumed:** varies; `built_b5` possibly relevant to RQ4.1 only, per above caveat.
**Dead as result:** none — all 15 are unstarted, not evidence-killed.

### D7. Grouped — 4 RQs gated on RQ-CONTESTED-001, gate passed, never run anyway
RQ-PNLGATE-001, RQ-POSSIZE-001, RQ-SECTOR-001, RQ-POOL-QUALITY-001.
**Grade: ABANDONED-UNTESTED** (all 4)
**What happened:** each explicitly gated on "after RQ-CONTESTED-001 (July 1)" plus ≥30
LEGENDARY-consensus geo markets. The gate was nominally satisfied in June, but none was
ever run — project attention shifted to the ELO-arc migration and then the geo_elo
condemnation before July 1 arrived.
**Consumed:** `condemned_c1`-adjacent (all four were designed against
LEGENDARY-consensus populations, now condemned).
**Dead as result:** none.

### D8. Grouped — 3 RQs, lowest confidence (never even pre-registered)
RQ-VPIN-001, RQ-ILS-001, RQ-CORRELATION-001.
**Grade: ABANDONED-UNTESTED** (all 3), **lowest-confidence tier**
**What happened:** found only as one-line forward-roadmap items ("pre-register
RQ-VPIN-001, RQ-ILS-001" targeted for July 1) in a 2026-06-26 session summary. **Never
pre-registered at all** — no hypothesis document exists for any of the three, this pass
did not find a defining document beyond the roadmap line.
**Consumed:** none identifiable.
**Dead as result:** none — never existed as a runnable test.

### D9. RQ-EXT-001
**Grade: ABANDONED-UNTESTED**
**What happened:** listed as "Wave 3 prep (Aug 1)" in a 2026-06-13 session summary; no
trace after that.
**Consumed:** none identifiable.

### D10. RQ-CONVICTION-001
**Grade: UNGRADED / INSUFFICIENT INFORMATION** — flagged rather than guessed.
**What is known:** proposed inside RQ-EXEC-001's (D5) write-up as a follow-on, but
apparently never formally pre-registered or run. This pass did not find enough to
confidently assign ABANDONED-UNTESTED vs. never-really-proposed-at-all — reported as a
gap, not resolved.

---

## Meta-finding — not itself a ruling, flagged separately

**`brain/strategy-registry.md` has been silently stale since 2026-06-12 (`1e64586`) —
three months before this pass.** It is described in its own text as authoritative,
maintained weekly by `feedback-loop-agent` plus Oscar. It still shows STR-002's "Next
revalidation due: 2026-07-01" as a *future* date and STR-003's n=28/19 target as
pending, while this pass found (via direct DB query) that STR-002 has actually
accumulated to **n=221** (see C5) — a fact reflected nowhere in the registry.
`feedback-loop-agent`, the agent responsible for flagging this staleness, was one of
the 5 agents disabled 2026-08-31 (`infra_o6`) — but **the registry was already 2.5
months stale before that pause began**, so the pause is not the explanation. No
document anywhere in this sweep explicitly decides "stop maintaining the strategy
registry" or "deprioritize the STR-series track" — it simply stopped, silently. This is
neglect, not a ruling, and it means the STR-series entries in this register (C3-C8) are
graded from primary documents this pass read directly, **not** from the registry's own
(stale) summary judgments.

---

## Contradictions / cross-references between forks

- **LH-001 and RQ-LH-001** (C8, D-section) are the same finding, reached independently
  by two separate sweeps this pass — consistent, merged into one entry (C8), not
  duplicated.
- **B3 (comprehensive_elo) and B4 (calibration_analysis.py)** remain under-characterized
  after two full passes — both are confidently CLOSED-INSTRUMENT but neither pass has
  established a citable open-question restatement to the standard B1/B2 achieved. Flagged
  for a future pass rather than papered over.
- **STR-003's signals live outside the DB table pass 1 catalogued** (`str002_signals`
  contains only STR002-prefixed rows) — a pass-1 coverage gap surfaced by this pass's
  primary-source reading, noted here rather than silently corrected in pass 1's document.

---

## What this pass did NOT cover

- `2026-08-21-discovery-gap-closure-prereg.md` in full (1883 lines) — cited repeatedly
  by both passes, never independently read cover-to-cover by either.
- `2026-09-05-copy-trade-decay-prereg.md` §2-9 and
  `2026-09-10-copy-trade-decay-price-substitution-verification.md` (283 lines).
- STR-002's full primary result document with its formal pre-registered threshold and a
  properly computed CI on n=227 (C5, flagged low-confidence).
- `brain/agent-outputs/backtest-agent/STR-001-validation-2026-04-27.json` and other
  agent-output JSON files — referenced, not opened.
- Approximately 190 of 244 decision documents remain unread by either pass, after this
  pass's additional ~24 documents on top of pass 1's 24. The RQ sweep in particular
  grepped ~30 documents for last-mention dates only, without reading them — these back
  the lowest-confidence D-section entries (D8, D10), flagged individually above.

---

## What this pass did NOT do (by design, per scope)

No proposal of what to try next. No ranking by promise. No external research. No code,
table, or script was deleted, deprecated, or modified — only what became dead **as a
result of** a ruling was recorded (B6/`calculate_geo_elo.py` is the one clear
evidence-killed case in this register; nearly everything else marked ABANDONED-UNTESTED
is neglect, explicitly distinguished as such throughout). No measurement was re-run. No
production table was written to; no service was restarted.
