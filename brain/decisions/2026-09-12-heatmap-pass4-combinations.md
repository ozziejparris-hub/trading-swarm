# Heatmap Pass 4 of 5 — Combinations

**Date:** 2026-09-12
**Depends on:** Pass 1 (`1bb36e1`), Pass 2 (`5e94eef`), Pass 3 (`9efc118`). This pass is a
cross-product of those three, not a fresh survey — no new reading of the project corpus
or the external literature was done beyond what those three already established.

**Scope:** generate candidates — specific, answerable questions paired with the assets
that would answer them. No ranking, no scoring, no recommendation (pass 5). No
measurement was run. Nothing was modified or written to any production table.

**Correction carried forward:** passes 2 and 3 referred to `signal_credibility.py`
using the label `built_b10` in a few places. That is wrong — pass 1's `built_b10` is
`weighted_consensus_system.py`. `signal_credibility.py` was never assigned its own
pass-1 asset ID (it surfaced only via the scripts-fork's mid-pass correction that it has
live callers, not as a catalogued entry). This pass treats it as **an uncatalogued
asset**, not `built_b10`, and flags the mislabeling for the record rather than silently
perpetuating it.

**Safety check:** `metric_v2f_oos_result` sha256 reconfirmed unchanged before this pass:
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`.

---

## Source 1 — externally answered questions the project never asked

Pass 3 found three cases where a published framework directly matches or answers a
shelved project question (`jobA_2` RQ-ILS-001, `jobA_8` RQ-SCI-001, `jobA_7` RQ3.2). The
discipline here: applying someone else's method to the same platform they used is
replication, not a finding. Each candidate below states what's different — population,
window, or cross-validation against an instrument the source paper didn't have.

### S1-1. Does a per-market Information Leakage Score, computed on this project's own canonical Geo/Elections population, show excess pre-event price discovery — and does it correlate with the directional-skill harness's own cohort?
**Assets:** `data_d1` (trades), `instr_v3` (`price_at()` — PARTIAL, 73.1% cross-source
agreement, primary-with-fallback; adequate for a first pass, flagged as a real caveat
since ILS timing precision depends on price accuracy), `data_d3` (markets), `data_d6`/
`instr_v4` (canonical population, 9,739 markets).
**What would make it false:** ILS computed on this population shows no differential
pre-event price movement relative to a matched baseline, or ILS-high markets show no
excess concentration of `instr_v7`-classified skilled traders.
**Why it isn't already closed:** pass 2's `D8` group has RQ-ILS-001 as
ABANDONED-UNTESTED — never run at all, on any population. The published paper
(arXiv:2605.00493/2605.02287) validated ILS on its own (likely broader/all-category)
population; this project's Geo/Elections-only canonical population is narrower and has
never been checked against ILS. Cross-validating ILS-flagged markets against
`instr_v7`'s already-validated cohort is a check the source paper had no reason to run.
**External basis:** `jobA_2`/`jobC_11`; effect size reported: skilled accounts + market
makers (<3.5% of accounts) capture >30% of platform gains.
**Cost floor problem:** the published effect size is a *concentration* statistic (share
of gains captured), not a per-trade edge in price units — it cannot be compared to the
project's cost floors (geo 0.0005-0.010, elections 0.0056-0.020) without a fresh
derivation on this population. Stated plainly: whatever edge this produces may turn out
smaller once conditioned to Geo/Elections and netted of this project's own fee
structure. Not assumed to clear.

### S1-2. Does adopting the published, Monte-Carlo-validated Signal Credibility Index specification improve on the project's own stalled, annotation-only `signal_credibility.py`?
**Assets:** `signal_credibility.py` (uncatalogued, see correction above — live via
`legendary_positions_scan.py` and `register_signal.py`), `data_d10`
(`insider_signals`-adjacent), `instr_v3`.
**What would make it false:** a credibility-weighted signal built on the published
specification shows no accuracy improvement over the current signal, or the paper's own
τ*=0.27 threshold fails to transfer (the paper itself warns it isn't universal — "should
recalibrate by domain, platform, and response horizon").
**Why it isn't already closed:** RQ-SCI-001 (pass-2 `D4`) is ABANDONED-UNTESTED for the
*validation study* — the internal gate (≥20 resolved LEGENDARY-position markets) was
never reached. This candidate proposes something narrower: adopting an
already-externally-validated specification (Monte Carlo, out-of-distribution stress
tests, coordinated-manipulation scenarios — validation depth the internal version
lacks) rather than waiting on the internal gate, which substitutes for at least part of
what that gate was trying to establish.
**External basis:** `jobA_8`, arXiv:2604.27041.
**Cost floor:** N/A directly — a signal-quality question, not itself a raw-edge claim.

### S1-3. Does a Gómez-Cram-style split-half skill classification, applied to this project's own Geo/Elections canonical population, find a comparable skilled minority — and does it overlap with `instr_v7`'s persistence cohort?
**Assets:** `instr_v7` (directional-skill harness, PROVEN), `instr_v4` (canonical
population), `data_d1`/`data_d2`.
**What would make it false:** no comparable skilled-minority fraction in Geo/Elections
specifically (plausible given far smaller volume/trader count than all-Polymarket), or
zero overlap with `instr_v7`'s 146-trader cohort — which would suggest the two methods
pick up different things, weakening confidence in both rather than confirming either.
**Why it isn't already closed:** RQ3.2 (pass-2 `D3`) was CONFOUNDED then
ABANDONED-UNTESTED using the project's *own* two prior framings (base-rate
elite-consensus divergence with only 4 qualifying markets; a LEGENDARY-consensus
reframe whose data window closed unexecuted) — neither used Gómez-Cram's actual
split-half method. Pass 3's finding that Gómez-Cram "answers" RQ3.2 (`jobA_7`) is for
*all-Polymarket*; it says nothing about this project's specific canonical population or
about whether the resulting minority overlaps `instr_v7`'s already-validated cohort —
that cross-check has never been run.
**External basis:** `jobA_7`, SSRN 6617059, ~3.14% persistently-skilled minority
(1.72M accounts, all-Polymarket).
**Cost floor:** N/A directly — a population-characterization question. Any downstream
trading application would need its own cost-floor test, out of scope here.
**Placebo-objection note:** this candidate characterizes a population, it does not
propose acting on it. If a later step proposed trading on the identified minority's
positions, it would need to independently clear the same activity-matched-placebo test
that killed `A8`-`A11` — noted, not assumed away.

---

## Source 2 — the unexplained conflicts

### S2-1. Does re-weighting `own_market_calibration.py` by position size instead of price reproduce the external paper's rising-with-horizon shape?
**Assets:** `instr_v8` (`own_market_calibration.py`, PROVEN as an instrument for its
existing weighting scheme; re-running under a different weighting reuses the same
validated machinery, not a new instrument).
**What would make it false:** the re-weighted slope still falls with horizon — the same
shape as today — which would rule out weighting as the explanation and leave
population/anchor differences as the remaining candidates.
**Why it isn't already closed:** pass 2 has no register entry for own-market
calibration at all — it is a live, non-ruled-on finding (`instr_v8`), not a closed
question. Pass 3's `jobB_1` only *identified* weighting as a candidate explanation; it
explicitly did not test it. This candidate is exactly that untested test.
**External basis:** `jobB_1`, arXiv:2602.19520's own observation: "larger positions are
associated with prices further from truth."
**Cost floor:** N/A — a shape/methodology question. But the outcome determines whether
the project's own near-resolution slope (~1.29, the largest deviation, concentrated at
price extremes per pass 1) is over- or under-stated by price-weighting — which does
bear on a cost-floor-scale effect the project already characterized as "~1-2pp, at
cost-floor size, not large-effect."

### S2-2. Did maker-labeled (`is_taker=0`) trades appear after Polymarket's CLOB v2 maker-rebate program (2026-04-28)?
**Assets:** `data_d1` (trades, has timestamps), `built_b7` (`is_taker`, zero maker rows
database-wide as of the last full audit — this candidate proposes re-checking with a
date split, not assuming the prior zero still holds identically pre/post).
**What would make it false:** `is_taker=0` count remains exactly zero after 2026-04-28
too. **What true would mean:** if maker rows appear only after that date, it's strong
evidence the pre-2026-04-28 absence was a real market-structure fact (no incentive to
post resting orders), not a permanent detection blindness — and it would sharpen the
diagnosis in `jobB_5`, since the "relayer batches for both sides" hypothesis would
*predict* maker rows should still be zero or misattributed even post-rebate, if the
true cause is hash-attribution rather than market behavior. Either outcome is
informative; this is a clean two-way test.
**Why it isn't already closed:** this exact date-split test appears nowhere in pass 1
or pass 2 — `is_taker` was flagged as dead with "root cause not established"
(`built_b7`). Pass 3 raises the question (`jobC_5`/`jobB_5`) but explicitly does not run
it (out of scope for external research).
**External basis:** `jobC_5` (CLOB v2 upgrade and maker-rebate program — flagged as
secondary-sourced, not pinned to one primary source) and `jobB_5` (relayer
complication).
**Cost floor:** N/A — a data-integrity/instrument-diagnosis question. If maker-taker
detection turns out to be repairable, it unlocks a genuine new execution-quality
dimension the project currently cannot measure at all (per pass 1's `built_b7`
known-limits) — but that is a downstream consequence, not this candidate's own claim.

### S2-3. Does inspecting matched maker/taker transaction hashes show single-hash settlement for both sides (relayer batching), independent of the CLOB v2 rebate program?
**Assets:** `data_d1` (`transaction_hash` column), `data_d4` (`order_book_snapshots`,
3.57% coverage — the only source of maker/taker-adjacent ground truth the project
currently holds, and its coverage is thin).
**What would make it false:** matched maker/taker pairs (if constructible at all) show
genuinely distinct transaction hashes per side — ruling out relayer batching and leaving
the original taker-sends-it hypothesis, or some other explanation, standing.
**Why it isn't already closed:** `jobB_5` raises this as an unconfirmed complication
from secondary sources only (Polymarket's own docs are silent on the point; a technical
deep-dive 403'd) — pass 3 could not settle it empirically because it is barred from
touching project data. This candidate proposes settling it against the project's own
data.
**External basis:** `jobB_5`, secondary source only (relayer/gas-abstraction detail
from an aggregator, not primary Polymarket documentation).
**Cost floor:** N/A, instrument-diagnosis. **Feasibility caveat, stated honestly:**
`order_book_snapshots`' 3.57% coverage may make this infeasible to test with adequate
n — a different kind of "cost floor problem," a data-availability floor rather than an
economic one.

---

## Source 3 — the NULL-UNDERPOWERED revisit candidates

Pass 2 graded exactly 8 entries NULL-UNDERPOWERED: `A1`, `A3`, `A4`, `C6`, `C8`, `D1`,
`D2`, `D5`. Each is assessed honestly below for whether its stated reopening condition
is reachable now, partially reachable, or remains out of reach — per instruction, "more
data" is never accepted as the answer on its own.

### S3-1 (register `A1`, result of record). Reachable via natural accumulation — partially.
Pass 2 estimated (its own rough scaling, not a formal power target) that ~192 effective
independent trader-clusters would be needed vs. 120 at the time of measurement.
**Candidate:** recompute the same cohort/selection rule as of today's data, using
`instr_v6` post-fix (deterministic since 2026-09-06) rather than the original,
non-reconstructable placebo. **This must not overwrite `data_d7`** (pinned by decision)
— it would be a new, cleaner measurement, explicitly labeled as such, not a
reproduction of the frozen result.
**What would make it false:** the recomputed CI still includes zero even with a larger
effective sample.
**Cost floor:** the existing point estimate (+0.0316) already clears geopolitics'
range comfortably and sits within elections' upper range — if narrowed to exclude zero,
this is economically meaningful, not merely statistically distinguishable. Worth
stating plainly since it's the one NULL-UNDERPOWERED entry with an effect size already
known to clear the floor.
**Placebo-objection note:** the design already includes a matched placebo by
construction (`instr_v6`); this doesn't introduce a new naive-selector risk.

### S3-2 (register `A3`, Gómez-Cram 44% comparison). **NOT currently reachable — an honest negative.**
Pass 2 estimated ~185+ cohort traders needed vs. 146. Unlike `A1`, **this population is
capped by definition**: the pre-split BH-skilled cohort is defined by trades *before* a
fixed `T_split=2026-04-01`. It cannot grow by waiting — the passage of time adds
post-split data, not pre-split cohort members. Reopening this specific comparison would
require either accepting a materially different question (a later or rolling
`T_split`, which is effectively a new test, not a reopening) or is simply not
reachable with the current experimental design. **Reported as out of reach, not
generated as a live candidate.**

### S3-3 (register `A4`, aggregate edge test for the persistence cohort). Reachable via accumulation — direction only, magnitude unassessed.
Pass 2 found n_pairs=3,025 for the cohort vs. 10,827 for the comparison group.
Post-split positions *can* accumulate with time (unlike `A3`'s pre-split-capped
population). **Candidate:** recompute with positions accumulated since 2026-09-06.
Some growth has occurred in the ~1 week elapsed; whether it is enough to narrow
CI [−0.0151, 0.0362] to exclude zero is **not assessed here** — this pass does not run
measurements, so reachability is reported qualitatively (directionally reachable,
magnitude unknown) rather than by querying current counts.

### S3-4 (register `C6`, STR-003). Reachable — but requires reversing an unrelated governance decision, not new data collection.
Pass 2 found the mechanism that would generate new signals (`signal-agent`) was paused
2026-08-31 for cost reasons (`infra_o6`), independent of STR-003's own merit. **The data
source is switched off, not exhausted.** Reopening = re-enabling `signal-agent`
(reversible per `infra_o6`) and allowing accumulation toward the registry's own n=28
YES/n=19 NO target. Stated plainly as a governance question, not a measurement design
question — flagged for whoever weighs it next.

### S3-5 (register `C8`, LH-001). Reachable only if new qualifying real-world events have occurred.
Pass 2 found 5 more independent geopolitics events needed (3/5 clearing p<0.05), and
`insider_signals` has recorded zero new events since 2026-05-02. Reachability depends on
an external-world fact (did the right kind of event happen) this pass cannot assess.
**A genuine ambiguity worth flagging**, not resolved here: it's unclear whether zero new
events since 2026-05-02 reflects true event scarcity or that the detection pipeline
simply wasn't run against candidate events — these have different reopening paths (wait
for more history vs. run the existing detector against events already in the data) and
should not be conflated.

### S3-6 (register `D1`, RQ1.1). **The cheapest of the 8 to reopen — code already exists.**
The June rerun was coded (`77a10ad`) but never executed. **Candidate:** execute it,
against `tape_end`-anchored periods rather than `resolution_date` (per pass 2's own
"what would reopen it"), with the O-45 `resolution_date`-contamination risk checked
first. No new measurement design is needed — only execution. Flagged as the single
most immediately actionable item in this entire register.

### S3-7 (register `D2`, RQ2.2). Reachable, but requires a build step first — status less clear than `D1`.
The 14d/30d extended-window rerun was pre-registered for June 2026; unlike `D1`, pass 2
did not find evidence it was ever coded. **Candidate:** build and run it. Flagged as
needing more upfront work than `D1`, and its implementation status should be confirmed
before assuming it's merely an execution gap.

### S3-8 (register `D5`, RQ-EXEC-001). **The question the task calls out — full treatment below.**
**Candidate:** run RQ-EXEC-001 (execution timing vs. directional accuracy) on the
project's own trade/position data, using `instr_v7`'s validated persistence cohort as
the trader population, instead of the original n=4 external-dataset preliminary check.
**Assets:** `instr_v7` (cohort), `data_d1`/`data_d2`, `instr_v3` (`price_at()` for
timing reference).
**What would make it false:** no significant relationship (or a reversed one,
replicating the n=4 finding — LEGENDARY traders entering *later*, not earlier) between
entry timing (absolute or relative) and directional accuracy or realized edge within
the `instr_v7`-classified cohort.
**Why it isn't already closed:** pass 2's own "what would reopen it" for `D5` says only
"the deferred validation was never resumed... needs someone to pick it back up." This
candidate is exactly that, but materially re-specified: the original test used an
external dataset (n=4, no longer trustworthy at that size) and predates `instr_v7`'s
current validated form (proven 2026-09-06, after `RQ-EXEC-001` was last touched
2026-06-07). Re-running with a validated cohort and the project's own data is a
different, better-instrumented test of the same question, not a repeat.
**Why this is the highest-leverage NULL-UNDERPOWERED item:** the project's working
theory (Della Vedova-style execution/direction decomposition, independently supported by
`jobB_4`) already holds that directional skill (proven real, `instr_v7`) does not
convert into capturable copy-trade edge (`A6`, CLOSED-STRONG) or mispricing-marking
power (`A8`-`A11`, mostly CLOSED-STRONG). If sound-instrument-tested execution timing
turns out to correlate with skill or edge *within* the validated cohort, that would be
the first evidence pointing toward *which* execution dimension might matter, rather than
just confirming (again) that naive presence-based signals don't. If it turns out timing
doesn't correlate either, that further narrows what "execution" could mean here.
**External basis:** none new from pass 3 specifically — this candidate draws on `D5`'s
own n=4 finding (sourced in pass 2) and on the general Della Vedova support found in
`jobB_4`, not a new external citation.
**Cost floor:** indirect. This is a within-cohort skill-marker characterization
question, not itself a raw-edge claim; any downstream signal built from it would need
its own cost-floor test.
**Placebo-objection note, stated explicitly per discipline:** this candidate tests a
property (timing) *of* an already-validated skilled group (`instr_v7`, validated via
null-calibration and REPS tests) — it does not propose a *new* selection criterion to
be tested against a placebo, so it partially escapes the objection that killed
`A8`-`A11`. But if the eventual goal were to turn timing into a new *presence-based
mispricing marker* usable by others, that would need to independently clear the same
matched-placebo test `A8` already ran — and `A8` already found the presence-based
version fails at 4/6 horizons. **This candidate does not inherit validity from
`instr_v7`'s classification for that downstream use; the objection would need to be
re-run, not assumed satisfied.**

---

## Source 4 — unexercised assets

Pass 1's `BUILT_NEVER_EXERCISED` class, `built_b1`-`built_b10`. For each: a genuine
still-open question, or an honest rejection with reason.

### S4-1 (`built_b1`, composite_skill_score.py) — REJECTED, no candidate generated.
Explicitly retired by design decision (`2026-09-05-canonical-skill-metric-design.md`
§5): "flagged, explicitly out of scope — not reused, not repaired." Reviving it would
re-collapse distinguishable dimensions into one scalar — the exact mistake the
replacement design was built to avoid, and the project's own text names this as "the
exact pattern the M6 precedent warned about." No candidate generated.

### S4-2 (`built_b2`, elo_snapshots) — genuine candidate: membership dynamics, not score validity.
**Question:** does Pool C membership churn (entries/exits across the 70 recorded
dates, 2026-06-11 to 2026-09-11) show a stable core population versus a high-turnover
fringe — and does that stable-core/fringe split correlate with anything `instr_v7`
already validated?
**Assets:** `built_b2` (`elo_snapshots`), `instr_v7` (cross-reference cohort).
**What would make it false:** near-total turnover every snapshot (no stable core), or a
stable-core/fringe split that shows no relationship to `instr_v7`'s classification.
**Why it isn't already closed:** this doesn't require `geo_elo`'s *score* to be
valid — it uses only the `geo_accuracy_pool` membership flag (a broader, less-condemned
"clean and active enough" filter, not a skill-tier judgment). Pool C's own base-rate
confound (`A11`) is about *market*-level absence, a different axis entirely; nothing in
pass 2 addresses trader-level Pool C *membership stability* as its own question.
**This is the task's own example question, answered directly:** a rating time series
answers a *stability* question a cross-section structurally cannot — who stays, who
churns — independent of whether the underlying rating level is trustworthy.
**Cost floor:** N/A — a population-dynamics/diagnostic question, not a tradeable-edge
claim.

### S4-3 (`built_b3`, timing_score) — no independent candidate; cross-reference `S3-8`.
Its capturability framing is moot (`A6`). Its remaining open use — as a within-cohort
skill-marker, not a copy-trade mechanism — is exactly what `S3-8` (RQ-EXEC-001)
proposes. Not duplicated here.

### S4-4 (`built_b4`, ELO behavioral bonus) — REJECTED, no residual content.
Once its three inputs are separately accounted for (kelly/patience found null via Stage
0b = `built_b5`; timing repurposed elsewhere = `built_b3`), the ±100pt blending
mechanism itself has nothing left to ask — reviving the *blend* specifically would just
recombine already-assessed null and repurposed pieces. No candidate generated.

### S4-5 (`built_b5`, kelly_alignment_score/patience_score) — flagged, LOW CONFIDENCE.
Pass 3 (`jobA_3`) found the Kelly-quality literature (Meister, arXiv:2412.14144)
theoretically consistent with the project's own null finding — this *strengthens* the
case the null is real, not a fluke, rather than opening something.
**Tentative candidate, flagged low-confidence:** does re-specifying
`kelly_alignment_score` using Meister's KL-divergence-between-belief-and-true-distribution
formulation, rather than the project's original formulation, produce a signal Stage
0b's null didn't already rule out?
**Why flagged low-confidence rather than a full candidate:** this pass does not have
the project's exact original `kelly_alignment_score` formula documented in passes 1-3
to confirm whether it already matches or differs from Meister's framing. **The premise
(that they differ) is unconfirmed** and would need checking before this is a live
candidate rather than a restated null. Reported honestly rather than asserted either
way.

### S4-6 (`built_b6`, behavioral_modifier) — REJECTED, genuinely unconsidered, no basis to generate a forced candidate.
No internal evidence (never individually validated or invalidated) and no external
literature (pass 3) touches this specific composite (consistency × diversification ×
style × activity). Left as a residual for a future pass rather than padded into a
candidate here.

### S4-7 (`built_b7`, is_taker) — no independent candidate; already covered by `S2-2`/`S2-3`.

### S4-8 (`built_b8`, run_relevance_gate.py) — resolved by pass 2, not a live Source-4 item.
Pass 2 (`C1`) already established it was run (2026-09-03, real `classify_batch()`
calls) — pass 1's "unclear if ever run" flag no longer applies. No candidate needed.

### S4-9 (`built_b9`, measure_prefilter_coverage.py) — genuine candidate: decomposing where recall loss originates.
**Question:** does running `measure_prefilter_coverage.py` isolate how much of the
classifier cascade's recall shortfall (561 rows, pass-2 `C1`) originates in the
deterministic slug/title pre-filter stage specifically, versus the downstream LLM
stage?
**Assets:** `built_b9` (zero callers, never run).
**Why it isn't already closed:** `C1`'s diagnosis characterizes the *LLM* stage's miss
patterns (18 subtypes, batch-position degradation) but never attributes how much of the
total loss is pre-filter-stage vs. LLM-stage — a decomposition this specific,
purpose-built, never-run script would provide.
**What would make it uninteresting, stated honestly:** if pre-filter-stage coverage is
~100% (no loss there), this would only confirm what `C1` already found by other
means — a plausible null, not assumed away.
**Tension flagged:** this question is somewhat moot given `C1`'s pending institutional
status (Oscar's abandon-vs-retry call outstanding) — if "abandon" is the eventual
call, this diagnostic wouldn't change that decision. Noted, not resolved.

### S4-10 (`built_b10`, weighted_consensus_system.py) — genuine candidate: chasing down `comprehensive_elo`'s uncharacterized defect.
**Question:** does tracing `weighted_consensus_system.py`'s actual role inside
`unified_elo_system.py`'s live `comprehensive_elo` computation reveal what
`comprehensive_elo`'s sign-error-analog defect (`condemned_c3`) actually is?
**Assets:** `built_b10` (deprecated by its own docstring, yet has 5 live callers
including `unified_elo_system.py` and `monitoring/elo_bridge.py` — a contradiction pass
1 flagged and neither pass 2 nor 3 resolved).
**Why it isn't already closed:** pass 2's `B3` states plainly that `comprehensive_elo`'s
defect is "not root-caused... in anything read across both passes." This candidate
proposes exactly the missing investigation, using an asset whose contradictory
live/deprecated status was flagged but never chased down.
**Note on candidate type:** this is a code-archaeology/diagnostic question, not a
data-measurement one — no CI, no n, no cost floor applies. Flagged as a different kind
of candidate than the others, stated explicitly rather than forced into the same shape.

---

## The honest negative — considered and rejected

- **Reviving `composite_skill_score.py`** (`S4-1`) — explicitly superseded by design
  decision; would repeat a named mistake.
- **Reviving the ELO behavioral bonus blend as its own entity** (`S4-4`) — no residual
  content once its three inputs are separately accounted for.
- **`behavioral_modifier`** (`S4-6`) — no internal or external basis found; genuinely
  unconsidered, not forced into a candidate.
- **Re-testing LEGENDARY/NEAR_LEGENDARY tier conditioning with a rebuilt tier
  ladder** — considered, since pass-2 `B2`'s open question raised exactly this. Rejected
  as redundant: `B2` already concludes the generalized question is "already answered
  CLOSED-STRONG by `A8`" (a sound instrument, not tier ladders, already ran the
  presence-marks-mispricing test). No need to regenerate.
- **Re-running the original gap-pinned copy-trade-decay framing** (`A7`, SUPERSEDED) —
  rejected. Its own successor document calls it "permanently unrunnable"; reopening
  would need fundamentally new sub-12-minute-granularity market-microstructure data,
  not a new analysis of existing data. Correctly SUPERSEDED, not a candidate to
  regenerate.
- **RQ-CORRELATION-001 as a generated candidate** — considered, rejected for lack of
  basis. Pass 3 (`jobA_5`) found genuinely nothing in the literature framing
  cross-market position correlation as a trader-level skill signal (only market-level
  arbitrage literature exists, a different question). Without either a pass-2 opening
  or a pass-3 external basis, generating a candidate here would be "investigate X" with
  no specific question — exactly what this pass is instructed not to do.
- **Cross-platform (Kalshi/Polymarket) arbitrage or lead-lag candidates** (`jobC_7`) —
  considered, rejected as not generatable under this pass's own definition of a
  candidate ("paired with the assets that would answer it"). The project has zero
  cross-platform data — no pass-1 asset answers this at all. New data acquisition is a
  pass-5-territory judgment, not a candidate this pass can specify.
- **UMA oracle vote-concentration analysis** (`jobC_1`) — same treatment. No voter-identity
  data exists anywhere in the project's assets. Not generatable.
- **VPIN applied naively (inferred, not ground-truth)** (`jobA_1`) — considered,
  rejected as a standalone candidate. The project has no ground-truth order-flow
  classification (order book coverage only 3.57%, `data_d4`), so any VPIN candidate here
  would necessarily use the *inferred* version, which pass 3 found diverges
  substantially from ground-truth and carries a known critique (mechanical artifact
  under Bulk Volume Classification, not fundamentals-based). Not generated as a clean
  candidate; noted as a data-quality-blocked idea rather than silently dropped.
- **RQ-POSSIZE-001 as an isolated position-size signal** — considered, rejected. Pass 3
  found position size is never used as an isolated signal anywhere in the literature
  found; it's always conditioned on trader history (`jobA_3`). An isolated-signal
  candidate would misrepresent what the external evidence actually supports.
- **Other pass-3 Job C findings measurable with current assets but outside this pass's
  four defined sources** — the Mitts & Ofir wallet-level informed-trading screen
  (`jobC_2`) and the network-based wash-trading detection method (`jobC_9`) were both
  found measurable with `data_d1`/`data_d2` in pass 3, but neither is named under any of
  this pass's four explicit generation sources (Source 1 names only RQ-ILS-001,
  RQ-SCI-001, RQ3.2; Source 2 names only calibration shape, CLOB v2, and `is_taker`).
  Respecting the task's explicit scope rather than expanding it, these are **noted here
  for pass 5's awareness, not expanded into full candidates** in this pass.

---

## What this pass did NOT do (by design, per scope)

No ranking, scoring, or recommendation of any candidate — that is pass 5. No
measurement was run against project data. No new external research was done — pass 3 is
the external record for this whole exercise. Nothing was modified or written to any
production table.
