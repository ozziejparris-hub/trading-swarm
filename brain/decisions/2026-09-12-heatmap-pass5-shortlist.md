# Heatmap Pass 5 of 5 — Scoring and Shortlist

**Date:** 2026-09-12
**Depends on:** Pass 1 (`1bb36e1`), Pass 2 (`5e94eef`), Pass 3 (`9efc118`), Pass 4
(`8a6c4ea`). This is the final pass — it scores pass 4's candidates and produces the
shortlist. It does not decide anything; the choice is Oscar's.

**Safety check:** `metric_v2f_oos_result` sha256 reconfirmed unchanged before this pass:
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`.

---

## First — the two candidates pass 4 correctly left out of scope, developed in full

Pass 4 respected its own stated four sources literally and recorded these as footnotes.
That was the right call given how pass 4 was scoped — the scoping, not the omission,
was the gap. Developed here to the same standard as pass 4's other candidates before
scoring.

### S5-1. Does a composite informed-trading screen (bet size + timing + profitability + concentration, jointly) flag an anomalous subpopulation in this project's own Geo/Elections trade data?
**Question:** applying the Mitts & Ofir composite (cross-sectional bet size,
within-trader bet size, profitability, pre-event timing, directional concentration,
jointly) to `data_d1`/`data_d2`, does a flagged subpopulation show anomalous win
rate/profit relative to a matched, activity-controlled comparison group?
**Assets:** `data_d1` (trades), `data_d2` (positions) — pass 3 assessed both as
sufficient for every input feature.
**What would make it false:** no flagged subpopulation shows anomalous performance
above what a matched comparison group shows.
**Why it isn't already closed:** this is a direct generalization of LH-001 (pass-2
`C8`, NULL-UNDERPOWERED, stalled at n=2 real-world events because its own criteria
require waiting for specific named events). Mitts & Ofir's composite doesn't require
waiting for named events — it's a standing wallet-level screen runnable against the
full existing trade tape today, at n=210,000+ wallet-market pairs in the source paper
versus LH-001's n=59 candidates.
**External basis:** `jobC_2`; 69.9% win rate on flagged trades, >60 SD above null under
permutation test, ~$143M aggregate anomalous profit.
**Cost floor:** the reported 69.9% is a directional-accuracy figure, not a price-unit
edge — would need translation before comparison to geopolitics 0.0005-0.010 or
elections 0.0056-0.020. **Not assumed to clear.**
**Placebo objection — stated explicitly, not omitted:** this squarely proposes
identifying "informed" wallets by a set of criteria and treating their positions as
meaningful. That is exactly the shape of selector that has failed **four times**
already (`A8`-`A11`) when done via presence/tier-based criteria. **This candidate does
not escape the objection by default** — the external paper's own report has no
activity-matched placebo baked in (it didn't need one, not fighting this project's
specific failure history), and nothing about combining more inputs guarantees survival
against a matched comparison. If run, it would need `instr_v6`'s matched-control
machinery applied to the flagged subpopulation from the start, not appended after a
positive result. **See the Structural Observation section below — this is the closest
available vehicle for testing whether composite signals genuinely escape where
single-dimension ones failed, but it has not yet done so.**

### S5-2. Does network-based wash-trading detection find a materially different population than the project's existing ARB_BOT pattern detection?
**Question:** applying wallet-pair network clustering to `data_d1`'s trade graph, is the
flagged wash-trading population substantially the same as, or materially different
from, the population the project's existing Pattern A/B/C ARB_BOT detection already
catches — and if different, does removing it change any canonical population
definition or headline result?
**Assets:** `data_d1` (trades, has the counterparty/wallet-pair structure needed).
**What would make it false:** network-based detection finds substantially the same
population as existing detection (no new information), or finds a different population
but removing it doesn't materially move any canonical definition or result.
**Why it isn't already closed:** pass 1/2 never benchmarked the project's own bot
detection against any external methodology. This is a genuinely new,
methodologically-distinct cross-check (network-clustering vs. the project's per-trade
pattern rules).
**External basis:** `jobC_9`, SSRN 5714122; ~25% of all Polymarket trades 2022-2025
estimated wash trades, 14% of 1.26M wallets, peaking near 60% of weekly volume December
2024.
**Cost floor:** N/A directly — this is a data-integrity/population-contamination
question, not a trading-edge claim. **But the stakes are foundational**: if the
project's own canonical population (`data_d3`, `instr_v4`, and by extension `data_d7`,
`instr_v7`, `instr_v8`) contains wash-trade contamination the narrower ARB_BOT patterns
miss, that could bear on confidence in every downstream result, not just one arc.
**Placebo objection: does not apply.** This is a noise-removal/data-cleaning question,
the structural opposite of "select skilled traders and act on them" — immune by
construction, not by argument.

---

## Scoring criteria (reproduced, in weighted order)

1. **Decidability** (heaviest) — would the result be interpretable at achievable n?
2. **Consequence** — does a positive answer change what Oscar does? Does a negative
   one? Same-action-either-way scores low.
3. **Cost** — hours / days / weeks / blocked-on-new-data.
4. **Survives the placebo** — immune (diagnostic/market-level) scores up; faces the
   objection with no stated escape scores down.
5. **Cost-floor realism** — for tradeable-edge claims, does the effect size clear
   geopolitics 0.0005-0.010 or elections 0.0056-0.020?

Components are reported separately per candidate below and in the JSON. No blended
score is produced — a single number would hide exactly the tradeoffs that matter here.

---

## Full scoring — all 20 candidates

*(Condensed here; complete per-candidate detail in the JSON. Candidates already marked
`candidate_generated: false` in pass 4 — `S4-1`, `S4-3`, `S4-4`, `S4-6`, `S4-7`, `S4-8`
— are not re-scored; pass 4's reasoning for not generating them stands. `S3-2` remains
not-reachable, also not re-scored.)*

| ID | Decidability | Consequence | Cost | Placebo | Cost-floor |
|---|---|---|---|---|---|
| S1-1 | MEDIUM-HIGH | MEDIUM | DAYS | SURVIVES (market-level) | UNKNOWN, needs re-derivation |
| S1-2 | MEDIUM | LOW-MEDIUM | DAYS | N/A | N/A |
| S1-3 | MEDIUM-HIGH | MEDIUM | DAYS | SURVIVES AS SCOPED | N/A |
| S2-1 | HIGH | MEDIUM-HIGH | HOURS-DAYS | SURVIVES | N/A (shape question) |
| S2-2 | HIGH | MEDIUM | HOURS | SURVIVES | N/A |
| S2-3 | LOW-MEDIUM | MEDIUM | DAYS | SURVIVES | N/A |
| S3-1 | HIGH | HIGH (asymmetric) | DAYS | SURVIVES (matched by design) | **CLEARS** |
| S3-3 | MEDIUM-HIGH | MEDIUM | DAYS | SURVIVES | plausibly within range |
| S3-4 | LOW-MEDIUM | LOW-MEDIUM | WEEKS-MONTHS | untested against placebo | N/A |
| S3-5 | LOW | LOW-MEDIUM | uncontrollable/unknown | untested against placebo | N/A |
| S3-6 | HIGH | **LOW** | HOURS-DAYS | N/A | N/A |
| S3-7 | MEDIUM | LOW-MEDIUM | DAYS+ (build step) | N/A | N/A |
| S3-8 | HIGH | HIGH | DAYS | SURVIVES AS SCOPED | indirect |
| S4-2 | HIGH | MEDIUM | HOURS-DAYS | SURVIVES | N/A |
| S4-5 | LOW (premise unconfirmed) | LOW | unknown/blocked | N/A | N/A |
| S4-9 | HIGH | **LOW** | HOURS | N/A | N/A |
| S4-10 | MEDIUM | **LOW** | DAYS | N/A | N/A |
| S5-1 | MEDIUM-HIGH | HIGH (if positive) | DAYS-WEEKS | **DOES NOT ESCAPE** | UNKNOWN, needs re-derivation |
| S5-2 | HIGH | HIGH (foundational) | DAYS-WEEKS | SURVIVES (not selection-for-action) | N/A |

---

## The structural observation — assessed, not assumed

**The claim:** where this project's single-dimension, presence-based selectors failed
five times, published work that succeeds uses composite, conditioned signals — bet size
AND timing AND profitability AND concentration jointly, never one in isolation.

**Assessment: genuinely uncertain, and both explanations are plausible.**
- **Selection-effect reading:** published papers report positive findings; a composite
  screen that failed against a matched placebo the way this project's selectors did
  would likely never be written up prominently, or would be framed as a negative result
  buried in a robustness section. We would not expect to see composite-failures in the
  literature even if they're common — this is a real, uncorrectable blind spot in what
  pass 3 could find.
- **Genuine-mechanism reading:** the project's failed selectors (`A8`-`A11`) test a
  specific, narrow question — does the mere *presence* of a trader meeting some static
  criterion (tier, ELO threshold, directional-skill classification) predict mispricing
  for *other* market participants to exploit. That is an externality/signaling
  question. The composite methods in the literature (Mitts & Ofir, the ILS papers) ask
  a different question — does a *specific trader's own multi-factor behavioral profile*
  predict *that trader's own* outcome. These are not the same question merely dressed
  in more features; a within-trader prediction problem and a
  presence-marks-the-market-for-others problem could behave differently for structural
  reasons independent of feature count.

**No candidate in this shortlist directly tests this.** `S3-8` tests a property
(timing) of an already-validated cohort, not a new composite selector. `S2-1`, `S2-2`,
`S3-1`, `S5-2` are calibration, diagnostic, and foundational data-integrity questions,
not selector tests at all. **`S5-1` is the closest available vehicle** — it is
structurally the direct test of whether a composite signal escapes where single-dimension
ones failed — **but it is excluded from the shortlist below precisely because it has
not yet escaped the placebo objection**, and nothing about its design guarantees it
will. Stated plainly, per instruction, rather than inventing a candidate to fill the
gap: **the structural question remains genuinely open, and answering it properly would
require designing `S5-1` (or something like it) with a matched-placebo comparison built
in from the first run, not appended after a positive result invites one.**

---

## THE SHORTLIST — at most 5, ordered

### 1. S3-8 — Does execution timing correlate with directional accuracy or realized edge within the directional-skill harness's already-validated cohort?
**Why it's on the list:** HIGH decidability, HIGH consequence in both directions. The
original RQ-EXEC-001 finding (LEGENDARY traders entered *later*, not earlier — the
opposite of the execution-timing hypothesis) rested on n=4 from an external dataset,
too small to trust. `instr_v7`'s cohort (146 pre-split-BH-skilled / 607 comparison, or
the 5,732-trader PIT-legal pool) didn't exist in validated form when that n=4 result was
last touched (2026-06-07). This is the single question whose answer would most redirect
what "execution matters" could concretely mean for this project, per the task's own
framing — every other execution-adjacent door (copy-trade capture, presence-based
mispricing) is already closed; this is the one still standing.
**Cost:** days — assets exist (`instr_v7`, `data_d1`, `data_d2`, `instr_v3`), the
analysis (a correlation/regression) is new but straightforward to build.
**What a negative result would mean, stated as plainly as a positive:** if timing does
*not* correlate with skill or edge within the validated cohort (or reverses again,
replicating the n=4 finding at real power this time), that is a clean, well-powered
closing of the "entry timing is the execution dimension that matters" hypothesis —
narrowing, not just repeating, what's already known. It would not be a wasted test; it
would convert an underpowered lean into a settled negative.
**First concrete step:** pull `instr_v7`'s cohort membership and compute each trader's
entry-time percentile (absolute, via `instr_v3`/`tape_end`, and relative, via
`built_b3`/`timing_score`'s existing computation) against their realized directional
accuracy and edge, using `instr_v5`'s clustered bootstrap for the CI.

### 2. S2-1 — Does re-weighting `own_market_calibration.py` by position size, not price, reproduce the external paper's rising-with-horizon shape?
**Why it's on the list:** resolves this pass's own headline external conflict
(`jobB_1`) at very low cost using an already-validated instrument. HIGH decidability,
MEDIUM-HIGH consequence — the outcome determines whether the project's own
underconfidence-near-resolution finding (concentrated at price extremes, cost-floor
scale) is a real population-specific pattern or an artifact of weighting choice.
**Cost:** hours to days — `instr_v8` already exists and is validated; this changes one
weighting parameter and reruns.
**What a negative result would mean:** if the re-weighted slope still falls with
horizon, weighting is ruled out as the explanation, narrowing the remaining candidates
to population breadth or a genuine, unexplained conflict — informative either way, and
cheap enough that a null result costs almost nothing.
**First concrete step:** re-run `own_market_calibration.py` with position-size
weighting substituted for price-weighting, same population, same lead-time bins,
compare slope-by-horizon shape directly against the current price-weighted output.

### 3. S2-2 — Did maker-labeled trades appear after Polymarket's CLOB v2 maker-rebate program (2026-04-28)?
**Why it's on the list:** the cheapest test in the entire register (hours) with a real,
two-way-informative payoff. HIGH decidability, MEDIUM consequence.
**Cost:** hours — a single date-split count query against `data_d1`, no new instrument.
**What a negative result would mean:** if `is_taker=0` remains exactly zero after
2026-04-28 too, that sharpens (does not resolve, but narrows) the diagnosis toward the
relayer-hash-attribution complication (`jobB_5`) over a pure "no incentive to make
markets here" explanation — informative on its own, and sets up whether `S2-3` (the
much more expensive, feasibility-constrained follow-up) is worth attempting at all.
**First concrete step:** `SELECT COUNT(*) FROM trades WHERE is_taker = 0 AND
created_at >= '2026-04-28'` (or the equivalent timestamp column) against `is_taker = 0
AND created_at < '2026-04-28'`.

### 4. S3-1 — Does recomputing the result-of-record's cohort/selection rule on today's data, with the now-deterministic `match_control()`, narrow the CI to exclude zero?
**Why it's on the list:** the one candidate in the entire register with an effect size
already known to clear the cost floor (+0.0316, comfortably within geopolitics' range
and elections' upper range) if it resolves. HIGH decidability, HIGH but asymmetric
consequence — a positive result would meaningfully strengthen the project's own
headline evidence; a null result confirms underpowered-not-negative persists, which is
expected and still worth confirming rather than assuming.
**Cost:** days — the full pipeline (`instr_v4`, `instr_v5`, `instr_v6`) is validated and
exists, but assembling a fresh run takes real effort, and it must not touch the pinned
`data_d7`.
**What a negative result would mean:** the CI still includes zero — this is the
expected, base-rate outcome given only ~4 weeks have elapsed and pass 2's own rough
power estimate suggested a substantially larger effective sample was needed. Not a
falsification; simply confirms the status quo persists, and is cheap enough relative to
its upside that a null result is not wasted effort.
**First concrete step:** define a new, explicitly-labeled table (not overwriting
`data_d7`) and re-run the v2f-style pipeline end to end on current data, using
`instr_v6` post-fix throughout.

### 5. S5-2 — Does network-based wash-trading detection find a materially different, uncaught population in this project's own trade data?
**Why it's on the list:** the highest-stakes candidate on the list by blast radius —
if the project's canonical population is meaningfully wash-trade-contaminated in a way
the existing ARB_BOT patterns miss, that bears on confidence in every downstream result
(`data_d7`, `instr_v7`, `instr_v8`), not one arc. HIGH decidability, HIGH consequence,
structurally immune to the placebo objection (a data-cleaning question, not a
selector-and-act question).
**Cost:** days to weeks — the highest-cost item on the shortlist; building a wallet-pair
clustering approach at `data_d1`'s scale (13.7M trades) is real instrument-building, not
execution of existing code.
**What a negative result would mean:** if network detection finds substantially the
same population the existing ARB_BOT patterns already catch, that's reassuring, not
wasted — it rules out a class of foundational concern rather than confirming a
suspicion, and closes a door the project has never actually checked.
**First concrete step:** construct the wallet-pair trade graph from `data_d1` for a
bounded time window first (not the full 13.7M-row history) to establish feasibility and
rough contamination-rate order of magnitude before committing to the full-history
build.

---

## NOT-WORTH-DOING — with reasons

- **S1-1** (ILS on own population) — reasonable candidate, not rejected on merit, but
  doesn't clear the top 5: effect size not cost-floor-comparable without re-derivation,
  and conceptually overlaps `S5-1`/`S5-2`'s informed-trading-detection territory at
  higher build cost for a less foundational payoff.
- **S1-2** (adopt SCI spec) — LOW-MEDIUM consequence: improves an internal tool
  (`signal_credibility.py`) that isn't feeding a headline decision; refines quality,
  doesn't redirect anything.
- **S1-3** (Gómez-Cram split-half + overlap check) — decent, but largely redundant with
  what `instr_v7` already established; a positive result mostly reassures, a negative
  one raises questions without a clear next step.
- **S2-3** (transaction-hash relayer investigation) — LOW-MEDIUM decidability: pass 4
  itself flagged that `order_book_snapshots`' 3.57% coverage may make this infeasible
  at adequate n. Sequence conditionally after `S2-2`, not independently.
- **S3-3** (aggregate edge test recompute) — dominated by `S3-1`; secondary/exploratory
  by its own original design (never fed `data_d7`), lower marginal value.
- **S3-4** (STR-003, re-enable signal-agent) — LOW-MEDIUM decidability on a
  weeks-to-months timescale; requires reversing a deliberate, cost-driven governance
  decision for a narrow, lower-profile strategy track; and — flagged honestly — this
  single-trader-conviction signal has itself never been tested against a matched
  placebo the way `A8`-`A11` were.
- **S3-5** (LH-001 reopening) — LOW decidability: depends on an external, uncontrollable
  fact (did qualifying real-world events occur); narrow watchlist-only consequence even
  if reopened; also never placebo-tested.
- **S3-6** (RQ1.1 rerun) — the clean example of "cheap and decidable but doesn't
  matter": HIGH decidability, HOURS-DAYS cost, but **LOW consequence** — it would test
  persistence of `geo_elo`/`comprehensive_elo`, both condemned instruments the project
  has already moved past. `instr_v7` already answered the analogous "does skill
  persist" question with a sound instrument. Running this changes nothing.
- **S3-7** (RQ2.2 extended window) — dominated by `S3-8`, which asks a closely related
  question on a far better-validated population, and `S3-7` needs a build step first
  (status of any prior coding unconfirmed).
- **S4-2** (elo_snapshots churn/stability) — a genuinely reasonable, cheap candidate;
  came close to the cut. Consequence capped at MEDIUM (a positive correlation with
  `instr_v7` would be a nice cross-validation, not a redirection); displaced by higher-
  consequence items.
- **S4-5** (Kelly re-specification) — pass 4's own flag stands: the premise (that the
  project's original formula differs from the literature's KL-divergence framing) is
  **unconfirmed**, and even resolved this feeds a dead blend (`built_b4`, `W_BEH=0`).
- **S4-9** (`measure_prefilter_coverage.py`) — cheap (hours) but **LOW consequence**:
  pass 4 already flagged the tension — this is moot against `C1`'s pending
  abandon-vs-retry adjudication either way.
- **S4-10** (`weighted_consensus_system.py` archaeology) — the task's own example,
  matched almost exactly: "knowing `comprehensive_elo`'s defect changes nothing about
  direction." The project has already moved past `comprehensive_elo` to `instr_v7`;
  characterizing the old instrument's exact defect doesn't redirect current work.
- **S5-1** (Mitts & Ofir composite screen) — excluded specifically for failing the
  placebo criterion as currently specified, per the discipline this pass is required to
  apply. See the Structural Observation section — this is not a low-value candidate,
  it's an unresolved-risk one, and belongs on a future list once (if) designed with a
  matched-placebo comparison from the start.

**Also not re-scored, carried forward as-is from pass 4:** `S3-2` (`A3`, Gómez-Cram 44%
comparison) remains genuinely not reachable — capped by a fixed `T_split`, not a data
problem. `S4-1`, `S4-3`, `S4-4`, `S4-6`, `S4-7`, `S4-8` remain not-candidates per pass
4's own reasoning (superseded by design decision, cross-referenced elsewhere, no
residual content, or already resolved) — not re-litigated here.

---

## What the heatmap establishes overall

**Where the project stands.** Five passes establish a genuinely validated instrument
stack (PIT reconstruction, `price_at()`, the canonical backtest population, the
bootstrap/cap5/EB-shrinkage machinery, `match_control()`, the directional-skill
harness, own-market calibration) built specifically in response to a thoroughly
condemned predecessor (`geo_elo`/`comprehensive_elo`/LEGENDARY). The pivot was real and
well-documented, not cosmetic. The headline finding that survives all five passes:
**directional skill is real and statistically persistent (37.0% vs. 18.6%) but has not
converted into a capturable, tradeable signal via any selector tried so far** — five
falsified selectors, four of them via the same activity-matched-placebo mechanism, is a
convergent, multiply-replicated pattern across independently-designed tests, not a
single fragile result. The project's own working explanation (execution, not
information, drives profit — Della Vedova-style decomposition) has independent external
support (`jobB_4`) for the *mechanism*, though no external replication was found of the
specific *pattern* (matched control beats naive selection).

**The project's single most decision-relevant number — the result of record itself —
remains genuinely unresolved**, not negative: NULL-UNDERPOWERED after roughly five
weeks and several related analyses. That is the honest center of gravity of this whole
exercise: not "the thesis failed," but "the thesis has not yet been tested at adequate
power, and several of the obvious ways to act on a positive belief in it have
independently failed for a *different*, well-understood reason (execution, not
selection)."

**Alongside the research findings sits real administrative drift**, independent of any
evidence: 25 of 35 named research questions were never run — dropped for cost or
attention-shift, not because anything returned negative; a strategy registry silently
stale for three months; a Tier-3 agent layer paused for cost reasons that also happens
to have starved at least one underpowered result (STR-003) of the data that would have
resolved it; a relevance-classifier adjudication still institutionally outstanding.
None of this is a research failure — it's the ordinary cost of a fast-moving, ~10-month
project outrunning its own bookkeeping, but it is real, and pass 2's register is the
first place it was all counted in one place.

**Genuinely closed versus merely stopped.**
- **Genuinely CLOSED, well-powered:** copy-trade decay (`A6`), skilled-presence
  mispricing (`A8`), LEGENDARY/NEAR_LEGENDARY conditioning (`A9`/`A10`), STR-001
  (`C3`), the relevance classifier's recall question (`C1`, evidentially — its
  institutional disposition is a separate, still-open matter).
- **CLOSED as an instrument, but the underlying world-question reopened and
  answered by a better one:** `geo_elo` (`B1`) — the question it was built to answer
  now has a sound answer via `instr_v7`.
- **Merely STOPPED, no evidence involved:** 25 of 35 RQs, the discovery-gap sweep's
  motivating question, STR-001b/STR-004, the strategy registry's maintenance, the
  Tier-3 signal-generation agents.
- **Genuinely UNRESOLVED — neither closed nor stopped, still live:** the result of
  record itself (`A1`), the calibration-shape conflict (`jobB_1`), `comprehensive_elo`'s
  specific defect (`B3`), the `is_taker` structural question (`jobB_5`).

**The coverage gap, and what it leaves uncertain.** Across all five passes,
approximately **190 of 244 decision documents in `brain/decisions/` remain unread by
any pass** — pass 1 read 24 in depth, pass 2 added roughly 24 more primary
pre-registration/result documents (some overlap in what was consulted), passes 3 and 4
did not add new project-corpus reading by design. This means: **any RQ, arc, or finding
mentioned only in the unread ~190 is invisible to this entire shortlist.** Specifically
flagged as a real gap, not a formality: the three large primary pre-registrations never
read in full (the discovery-gap-closure sweep's actual founding pre-registration at
1,883 lines, the copy-trade-decay pre-registration's middle sections, and the
price-substitution-verification document) could contain additional stop-conditions,
caveats, or even additional closed or reopenable questions that would change how
confidently `S3-1`'s "this is reachable" framing, or any other candidate's "why isn't
this already closed" field, should be trusted. **The shortlist above is built on a
genuinely rigorous but incomplete base.** It should be read as the strongest set of
candidates *given what five passes actually found*, not as proof nothing better exists
in the unread remainder. Oscar should treat the not-worth-doing list as provisional
against that gap, not as a closed verdict — something ranked low here could look
different if a currently-unread document turns out to bear on it directly.

---

## What this pass did NOT do (by design, per scope)

No measurement was run. No new external research was done. Nothing was modified or
written to any production table. No decision was recommended — the shortlist and
not-worth-doing list state tradeoffs; the choice of what to pursue, if anything, is
Oscar's.
