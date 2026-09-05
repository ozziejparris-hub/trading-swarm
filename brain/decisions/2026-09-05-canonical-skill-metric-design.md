# Canonical Skill Metric — Consolidation Design

**DESIGN ONLY. Nothing computed, nothing implemented, no code written.**
This is a document to argue with, not a build. Builds on, and cites rather
than restates:
`2026-09-05-timing-execution-inventory.md`,
`2026-09-05-execution-signal-feasibility.md`,
`2026-09-05-track2-result.md`,
`2026-08-21-discovery-gap-closure-prereg.md` §E.

Tags: **[V]** verified this session, **[I]** inferred / a design judgment
call open for review.

---

## 0. One more thing the inventory missed, found while grounding this design

Before designing against "three parallel skill-measurement systems," a
fourth was checked and confirmed [V, this session]:
`analysis/composite_skill_score.py` (906 lines, added `b11b42d`,
2025-12-05, "Addition of a master rating system (0-100)") — an 8-dimension,
100-point composite (ELO, forecasting calibration, "execution quality via
regret analysis," consistency, behavioral profile, network independence,
contrarian bonus, copy-trader penalty). Its only entry point,
`UnifiedELOSystem.get_composite_skill_score` (`analysis/unified_elo_system.py:4047`),
has **zero callers anywhere in either repo** [V, exhaustive grep]. `docs/elo_system_reference.py`
carries a duplicate copy, also uncalled. This is the exact pattern the M6
precedent warned about, predating everything else in this arc. It is
folded into §5 below, not treated separately.

---

## 1. The restated thesis

The original question — "do skilled traders predict geopolitics better
than market price" — is answered by a single scalar (`edge = won −
entry_price`) that Della Vedova's finding says conflates two nearly
orthogonal things. The replacement is not one question but three, asked
**in sequence, each capable of independently returning a negative
answer that moots what follows it**:

**(a) Directional skill.** Stripped of price, size, and timing — using the
Gómez-Cram randomized-direction benchmark (hold the cohort's actual
markets, timing, prices, and sizes fixed; randomize only buy/sell
direction, many times; compare realized PnL to that null) — do cohort
traders call the *direction* of geopolitical events better than chance
would, given the exact bets they actually placed? A negative answer here
is total: if there is no directional skill, nothing downstream can rescue
the thesis, because there is no directional signal for execution to be
"the vehicle for."

**(b) Source of profit.** *If* (a) is positive: is the `+0.0316` result of
record's profitability attributable to that directional skill, to
execution/timing advantage (earliness — absolute and relative), or a mix?
Della Vedova's <1% shared-variance finding is the license to ask this as
two nearly-separable questions rather than one entangled one.

**(c) THE DECISIVE ONE: capturability.** Whatever combination (a) and (b)
produce, how much of it is available to an outside party who must act
*after* the cohort trader — necessarily later, at a necessarily different
price? This is not answered by (a) or (b) at all, however they come out —
it is answered empirically, by the copy-trade decay measurement in §2.
**A positive (a) and a profit profile in (b) that leans directional does
not, by itself, prove capturability** — it only makes capturability
*plausible*, because pure direction should degrade more slowly under delay
than pure execution advantage. §2 is where that plausibility gets tested,
not assumed.

This form admits every kind of negative answer the original one-dimensional
question couldn't distinguish: "no skill" (fails at a), "skill but it's
all execution, not direction" (b resolves toward execution, motivating (c)
directly), and "skill, plausibly directional, but not capturable anyway"
(a and b both favorable, (c) still fails). Only the last combination — (a)
positive, (b) meaningfully directional, (c) surviving delay — gives Phase
2 a subject at all.

---

## 2. The copy-trade decay question (central, not an addendum)

**Why this is the load-bearing question, restated plainly**: if profit is
execution-driven, copying a trader's *direction* at *our* entry time —
necessarily later — inherits the direction and none of the edge that lived
in the original timing. This is not a hypothesis to model; it is directly
measurable on data already held, and it should be measured **before**
anything about Phase 2 is designed, because a decayed-to-zero curve makes
every downstream design question moot.

**How to measure it, on data already held, without building anything new**:

For each of the cohort's 3,795 OOS positions, and for a swept range of
delays `N` (a reasonable exploratory ladder — e.g. minutes, tens of
minutes, hours, and a day-plus point — the exact set is a measurement
design detail, not fixed here): find the market's own **prevailing trade
tape price at `entry_timestamp + N`** (the next/nearest trade in that
market at or after that time, from any trader — this is a purely
mechanical, descriptive lookup, not the endogenous fair-price-benchmark
problem from the feasibility read, because here the tape is being used to
answer "what would a copier's entry price actually have been," not to
adjudicate skill). Holding the trader's actual direction and the market's
actual resolved outcome fixed, recompute what edge/PnL that same
directional call would have realized entering at that later, delayed
price instead of the trader's own. Plot the resulting **edge(N)** against
N — the decay curve.

**What it would need to look like for paper trading to be viable at all,
stated before computing it**: this project's own monitoring architecture
polls every 15 minutes [V, `CLAUDE.md`] — that is a real, concrete,
*already-fixed* floor on how small a realistic copy-delay can ever be; no
copy system built on this monitoring cadence acts faster than that. **For
Phase 2 to have a subject, the decay curve must retain a materially
positive edge — one that survives whatever the eventual pre-registration
fixes as "materially positive," not a number decided here — at or beyond
that ~15-minute realistic floor**, not just at `N=0`. If the curve
collapses to indistinguishable-from-zero (or from the placebo baseline)
within the first 15 minutes, Phase 2 has no subject, regardless of how
well any downstream execution engineering is done — there would be
nothing left to inherit by the time a real copy could physically occur.
If edge survives well past that floor, Phase 2 has something to build
toward, and the decay curve's own shape (how fast, how far) becomes the
design input for what a viable Phase 2 latency budget would need to be.

**This measurement should run before, and independently of, everything
else in this design being built out** — it is cheap (data already held,
no new instrumentation), and a negative result here changes the priority
of every other section.

---

## 3. The metric's components — minimum set, each justified against the others

**Design principle, stated first because it constrains everything below**:
the entire premise of this redesign is that collapsing distinguishable
dimensions into one scalar (`edge = won − entry_price`) is what produced
an uninterpretable result. **The canonical metric must not repeat that
mistake by collapsing its own components into a new single score.** It
should output a small, labeled vector, not a blended composite —
otherwise this design is `composite_skill_score.py` (§0) with new inputs.

**Proposed minimum set — three components:**

1. **Directional skill** — the Gómez-Cram randomized-direction benchmark
   (§1a). Necessary: nothing else in this list measures skill independent
   of price, size, or timing at all.
2. **Absolute earliness** — entry-to-resolution lag, **tape_end-anchored**
   (per the feasibility read: 100% coverage, zero negative-lag artifacts,
   versus `resolution_date`'s 11% logically-impossible values — this is
   not a new choice, it reuses O-36's already-validated workaround).
   Measures position *relative to the resolution timeline* — comparable
   across markets of different duration, and directly the Della Vedova
   ">8 days" benchmark.
3. **Relative earliness** — `timing_score`'s existing relative
   entry-percentile computation, reused as-is (98.6% clean for this
   cohort). Measures position *relative to other participants in the same
   market* — a peer-ranking, not a resolution-timeline measure.

**Are (2) and (3) redundant? Explicitly assessed, not assumed — kept as
two, not one.** They can diverge in both directions: a trader can enter
*absolute*-early in a market's life (many days before resolution) while
being *relatively* late if that specific market drew a rush of early
attention before them; conversely, a trader can be the *relative*
first-mover in a market that itself only exists briefly, and so still be
*absolute*-late. They also have different robustness profiles: absolute
earliness depends on a resolution-timeline anchor that is known-unreliable
under one construction and requires the tape_end fix (§ above); relative
earliness never references the resolution timeline at all and is immune
to that specific failure mode. **This is a reasoned, not an empirically
tested, non-redundancy judgment [I]** — a cheap correlation check between
the two, on this cohort, belongs in §8's eventual validation pass; if it
turns out empirically that they move together almost perfectly for this
specific population, one could be dropped later without revisiting this
document's reasoning, which rests on the conceptual distinction, not on
an assumed correlation.

**Explicitly excluded from the minimum set**, and why:
`kelly_alignment_score` and `patience_score` — Stage 0b already found
these null/negligible (§5, retired, not carried forward); neither Della
Vedova nor Gómez-Cram motivates a sizing-discipline or trading-frequency
dimension as operative for *this* question.

---

## 4. What it does not measure

- **The endogenous trade-tape fair-price benchmark** (a mid-price
  constructed from other traders' nearby trades, per the feasibility
  read's Della Vedova-decomposition assessment). Excluded because it is
  thin and degrades for exactly the high-volume cohort traders that
  matter most (§1c/§4 of the feasibility read), **and because the
  copy-trade decay curve (§2) already answers the more directly relevant
  version of the same question** — "how much profit survives delay" is a
  more honest, mechanically cleaner proxy for execution-dependence than
  trying to adjudicate a fair price at the instant of entry from a benchmark
  built out of possibly-equally-informed peers.
- **Maker/taker liquidity provision** (`is_taker`). Excluded because it is
  dead: zero maker-side rows exist database-wide, plausibly for a
  structural reason (a CLOB taker sends the transaction; a maker's resting
  order may never generate one of its own) — not a metric-design choice,
  a data-availability fact. If root-caused and repaired, this would add a
  genuine, independent execution-quality dimension (who provides
  liquidity vs. who consumes it) not currently expressible by any of the
  three components above.
- **Anything B4 order books would have supplied** (a true, non-endogenous
  bid/ask mid-price and spread at entry). Excluded at 3.57% coverage of
  Geopolitics+Elections markets, disjoint from this cohort. If B4 (or an
  equivalent) ever reached broad coverage, it would let the design add a
  genuine execution-quality component *and* could calibrate/validate the
  decay curve's own tape-price proxy against a true order-book benchmark
  — an upgrade, not a duplication, of what's proposed here.

---

## 5. Retirement — named, so none of this is rediscovered

| mechanism | status | disposition |
|---|---|---|
| ELO behavioral bonus (`calculate_behavioral_elo_bonus`, kelly=40/patience=30/timing=30, ±100pt) | dormant — never called by current writers, inert since `W_BEH=0` (2026-07-12) | **dormant, flagged with a note** (this document) — not deleted (out of scope), not silently left for rediscovery |
| `kelly_alignment_score`, `patience_score` (columns + writers) | live write path, zero ELO effect, Stage 0b found null/negligible | **superseded, not carried forward** into the canonical metric; columns/writers untouched, simply not read by the new module |
| `timing_score` (column + `calculate_timing_quality`) | live, computed weekly | **repurposed, not retired** — same existing function, reused directly as component 3 (§3), read in a new context instead of feeding a dead ELO bonus |
| `behavioral_modifier` composite (consistency×diversification×style×activity) | dormant, `W_BEH=0` | **dormant, flagged** — distinct from and unrelated to the three behavioral *score* columns; not part of this design at all |
| `composite_skill_score.py` / `get_composite_skill_score` (§0) | **dead** — zero callers, verified this session | **flagged, explicitly out of scope** — not reused, not repaired; named here specifically so it is not "discovered" again as if new |
| `is_taker` / `transaction_hash` maker-taker mechanism | dead — zero maker rows, likely structural | **dormant, flagged** — root cause not investigated (bounded diagnosis stopped short per the feasibility doc); revisit only if that changes |
| B4 order-book snapshots | live, serving its own purpose (STR-002/STR-003 signal-market fill simulation) | **not retired at all** — explicitly out of scope for this metric, not abandoned; do not attempt to fold in |
| `detect_insider_activity.py` / `resolution_sweep.py` Channel 2 | live, different purpose (single-event insider discovery, population widening) | **not retired, explicitly out of scope** — its "late entry = suspicious" polarity is the *opposite* of this metric's "early = skill" framing; naming this tension here so the two are never conflated downstream |
| LH-001 lifecycle heuristic | already closed (`conditional_pass`/insufficient, folded into `insider_signals` per its own recommendation) | nothing new to retire — cited as the precedent this design follows (reuse existing infrastructure rather than spin up a parallel system) |
| `edge = won − entry_price` / `metric_v2f_oos_result` | live, result of record | **not retired** — see §7, stands permanently by prior decision |
| Track 2's decomposition machinery (ablation bootstrap) | complete, one-off diagnostic, verdict Mixed | not a standing mechanism — nothing to retire; historical precedent only |

---

## 6. Canonical placement

**One module** [I, naming for review, not a commitment]:
`analysis/skill_signal.py` — a single new file, deliberately **not**
named in the `trader_skill_metric_v2*` suffix-versioning pattern this
project has used six times over (v2 → v2b → ... → v2f). That pattern
should not continue: amendments to this metric should be handled the way
`metric_v2f_amendment`/`spec_version` already work — a versioned spec
constant and an amendment table — inside one stable module and file name,
not a new suffixed file per revision.

**What it owns**: the single function that returns the canonical
three-component vector for a trader/cohort — reusing, not reimplementing,
`build_presplit_cohort`, `match_control`, `measure_oos` (for cohort/control
construction, exactly as Track 2 did), `calculate_timing_quality`
(component 3, as-is), and `build_tape_end_map` (component 2's anchor). The
copy-trade decay measurement (§2) is a related but logically distinct
artifact — a program-level feasibility gate, not a per-trader score —
and should not be persisted as if it were a fourth component.

**Decision authority**: one persisted output — a single table this module
alone writes — is the only sanctioned source of "the canonical skill
signal" for any downstream consumer. No other script computes or
persists a rival version of any of the three components; the ELO stack's
own history (nine columns, six writers, only one of thirteen writers ever
migrated to the canonical resolution-writer equivalent, per prior
project experience) is exactly the failure mode this is designed against.

**Enforcement — convention alone has already failed here once (the ELO
stack, `is_taker`, `composite_skill_score.py`), so this needs a
mechanism, not a promise**: this project already runs exactly the right
kind of check for a different concern — `check_canonical_definitions.py`,
a live, non-blocking step in `daily_maintenance.py`'s STEPS list, that
"alerts if any `.py` file hardcodes ELO thresholds instead of using
canonical `column_definitions` constants." **The same pattern should be
extended to this metric**: a periodic scan for any script that computes
something matching any of the three components' logic (direction-vs-price
comparisons, resolution/tape-timing lag, entry-percentile ranking)
outside the one sanctioned module, and alerts if found — mirroring the
existing drift-detection precedent rather than inventing a new
enforcement mechanism. This is a design requirement for whoever builds
this, not built here.

---

## 7. Relationship to the result of record

`+0.0316`, CI `[-0.0088, +0.0710]`, `n=3,032`, stands **permanently** —
decided 2026-08-21 (§E of the discovery-gap-closure prereg), confirmed
still present, untouched, in `metric_v2f_oos_result` as of that session
[V, that doc's own live query]. That same document already establishes
the exact coexistence pattern this design follows: a recomputation is
"a second, separately named measurement... both figures stand permanently,
side by side," persisted to **new, distinctly-named tables**, never
reusing or dropping the original.

**This canonical metric is that same pattern, one level further removed**:
not a recomputation of the same quantity under the same method (as §E's
"corrected" run was), but a **different measurement of a different
question** (§1's restated thesis) about the same cohort. It gets its own
table(s), under its own name, and coexists with `metric_v2f_oos_result`
indefinitely. Neither supersedes the other by default.

**What would make the new one primary** — not "bigger" or "more correct,"
but *decision-relevant* in a way the old scalar structurally cannot be:
if (a) its own validation (§8) survives pre-registered falsification, and
(b) it answers something `+0.0316` alone cannot — specifically, whether
that profit is directional or execution-driven, and whether any of it
survives the copy-trade delay in §2. **If §2's decay curve shows the
profit does not survive realistic delay, this metric's primary value is
diagnostic — it explains why `+0.0316` is not capturable — not a
replacement headline number.** Only if the decay curve shows surviving
edge does this design have a claim to becoming the number that gates a
Phase 2 decision, as opposed to the number that closes the question.

---

## 8. The validation design — outline only, thresholds fixed elsewhere

**What would falsify each component** (structure, not numbers):

- **Directional skill**: falsified if realized PnL does not exceed the
  Gómez-Cram randomized-direction null at whatever confidence bar the
  metric's own pre-registration fixes. A null result here is a valid,
  reportable finding — not a design failure.
- **Absolute earliness**: falsified if it does not differ between the
  cohort and its already-constructed, matched placebo control (Track 2's
  own control population — reused, not rebuilt) in the direction Della
  Vedova predicts.
- **Relative earliness**: falsified the same way, against the same
  placebo comparison.
- **The copy-trade decay curve**: not a pass/fail component, but its own
  reliability needs reporting — per-N confidence intervals, not just a
  point curve, since the feasibility read already found trade density
  itself thins at short windows; an unreliable curve at some N must be
  reported as such, not smoothed over.

**The Gómez-Cram 44% split-half persistence figure as an external
benchmark**: the paper's own method — split a trader's events into two
random halves, classify skill independently on each, check what fraction
classified-skilled on one half are also skilled on the other — is directly
reusable here as a structural cross-check, distinct from Track 2's
temporal `T_split`: split the cohort's *own* qualifying events randomly
into two halves, apply the same directional-skill test to each half
independently, and compare the resulting persistence rate against the
paper's 44% as an external reference point. Whether meeting, falling short
of, or exceeding 44% counts as confirming external validity for *this*
cohort specifically is not decided here.

**What must be fixed in a separate pre-registration before anything
runs**, named but not decided: the confidence bar for the Gómez-Cram
randomization test; the significance bar for the cohort-vs-placebo
earliness comparisons; the persistence-rate bar relative to 44%; the
decay curve's viability bar (what surviving edge, at what N, counts as
"Phase 2 has a subject") and the exact N ladder to test; and how thin/
missing data at extreme N gets handled (drop, flag, or otherwise) —
explicitly not decided here.

---

## 9. What this design could be wrong about

- **Imported near-independence.** Della Vedova's <1% shared-variance
  finding is from a different study population. If direction and
  execution turn out to be materially correlated in *this* cohort (e.g.
  more-informed traders also systematically trade earlier, linking the two
  "independent" dimensions), the clean separability this whole design
  rests on weakens, and the three components should be read as correlated
  proxies of one underlying quality factor rather than orthogonal facts —
  itself a cheap check worth adding to §8's eventual pre-registration.
- **Method transfer to a pre-selected sample.** Gómez-Cram's method was
  built for a broad population; this cohort was already selected on the
  *old*, conflated edge metric (significance-95, M≥10, edge≥0.02). Applying
  a randomization test to an already-filtered, edge-selected sample may
  behave differently (survivorship, regression to the mean) than applying
  it to an unfiltered population — not accounted for here.
- **The decay curve is necessary, not sufficient.** It uses the tape's own
  recorded prices, not what a real copy system would actually achieve
  (real slippage, real detection-latency variance, whether the same size
  could even be filled on a copy). Passing it does not guarantee Phase 2
  works; failing it is decisive against Phase 2. That asymmetry should be
  read into any result, not glossed over.
- **`tape_end`'s validation was for a different purpose.** O-36's
  workaround was validated for PIT position-reconstruction splits, not
  specifically for using earliness as a skill signal. The transfer is
  reasonable but inherited, not independently re-verified for this use.
- **A real circularity, named plainly.** The cohort this design is built
  and validated on (169/141 traders) was selected using the very edge
  metric this design exists to move past. If `edge = won − entry_price`
  is itself a conflated, misleading selection criterion, then the
  population being handed to the new metric may already be biased by the
  old one's blind spots. This is not resolved here — it is named because
  it is real, and any future population re-derivation for this metric
  should reckon with it explicitly rather than inherit the old cohort by
  default.
