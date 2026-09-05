# MASTER HANDOVER — 2026-09-05 (Server Setup 11)

**Read this first.** This document supersedes `MASTER_HANDOVER_2026-08-15.md`
and every session summary in between as the single entry point for a new
Claude chat instance picking up this project. It covers 2026-08-16 through
2026-09-05 — three weeks in which the thesis measurement did not move, one
of the project's own selection criteria was falsified by direct test, and a
substantial amount of infrastructure was built, some of it useful and some
of it in service of a wrong turn that cost eleven days. It is a snapshot,
not a living doc — cross-check `brain/decisions/` for anything newer before
trusting it blindly.

---

## 0. HOW TO START A NEW SESSION

1. Read this document, in full.
2. Read `MASTER_HANDOVER_2026-08-15.md` §1 (the `geo_elo` teardown) if you
   have not already — it is still the reason `geo_elo` must never be
   consumed for skill-ranking work. Nothing in this document reopens it.
3. Read `2026-09-05-canonical-skill-metric-design.md` before proposing any
   new skill measurement — it is the current design, and §5 of it names
   everything that has already been tried and retired so it isn't
   rediscovered.
4. Check the three services: `polymarket-monitoring`, `polymarket-observer`,
   `trading-swarm.service`.
5. Check today's `daily_maintenance.py` output for anything red, and
   specifically whether the discovery-gap sweep's checkpoint files show any
   sign of having resumed — **it should not have.** It is formally stopped
   (§3 below), not paused.

---

## 1. WHERE THE THESIS ACTUALLY STANDS (read this before infrastructure)

**The result of record: `+0.0316`, CI `[-0.0088, +0.0710]`, n=3,032/120,
`T_split=2026-04-01`.** This stands **permanently** by Oscar's explicit
decision on 2026-08-21 (§E of `2026-08-21-discovery-gap-closure-prereg.md`)
— never superseded, never recomputed, confirmed still present untouched in
`metric_v2f_oos_result` as of this session. Any future measurement of this
same quantity is a **separately-named, second figure**, persisted to new
tables, standing side by side with this one, never overwriting it.

Four measurements taken on 2026-09-05, in sequence, changed what this
figure means without changing the figure itself:

**Track 2 (CI power diagnostic).** Decomposed the result's CI width:
`share_trader = 0.432`, `share_market = 0.391` — neither clears the
pre-registered 0.65 binding threshold. **Outcome: Mixed.** No single-lever
addition of trader data or market data resolves the CI; enlarging either
population alone would not be expected to move the result to significance.

**The N=0 gap check.** The cohort-minus-placebo gap — computed properly,
with a paired bootstrap CI, for the first time — is **`-0.0072`**, CI
`[-0.057, +0.043]`, straddling zero. The original result-of-record's
implied gap was `+0.0189`. **The gap has stopped being demonstrated, not
been proven absent** — the CI is too wide to call it positive, negative, or
zero with confidence. Diagnosed: cohort's own edge fell 34% (`0.0316 →
0.0208`), placebo's rose 120% (`0.0127 → 0.0280`), both **100% attributable
to the identical mechanism** — pre-existing positions transitioning
pending→resolved as three weeks passed, zero genuinely new entrants on
either side, verified by the same row-level query on both populations.

**The directional skill test (Gómez-Cram randomised-direction benchmark).**
The discriminating result: **the placebo beats the cohort on every measure.**
Classified-skilled rate 39.2% (placebo) vs. 26.0% (cohort) raw, 29.4% vs.
19.2% Benjamini-Hochberg-adjusted; pooled aggregate significance `p=0.006`
(placebo, clears its own 95th-percentile bar) vs. `p=0.214` (cohort, does
not); split-half persistence 58.3% vs. 60.0%, both comfortably above
Gómez-Cram's own 44% external benchmark. **Outcome 2 of the pre-registered
four: the cohort's presplit edge selection captured nothing distinctive.**

**The honest reading, stated plainly:** the original thesis framing —
*"traders selected by presplit edge outperform"* — is falsified as a
selection criterion. But directional skill appears **present and
persistent in this population generally**, in both the cohort and the
placebo, well above this test's own ~5% chance floor and above
Gómez-Cram's ~3% population-wide rate. **The selector failed, not the
underlying phenomenon.** This reframes the open question from "does skill
exist" to "what would a selector built on directional skill, rather than
realised edge, identify" — genuinely live, not yet asked.

**One internal tension recorded, not resolved:** the cohort's own
per-trader classified-skilled rate (26.0%) reads as individually
"meaningful" against this test's own evidence bands, while the same
cohort's pooled aggregate test is not significant at all (`p=0.214`). This
was anticipated as Open Question 3 in the directional-skill pre-registration
and remains genuinely unresolved — per-trader and aggregate evidence
disagree about the cohort even holding the placebo comparison aside.

---

## 2. THE RESEARCH THAT REFRAMED THE PROJECT (2026-09-05)

Two 2026 papers, both postdating this project's start, motivated all four
2026-09-05 measurements above:

- **Della Vedova (SSRN 6191618):** prediction-market returns decompose into
  a **directional** component and an **execution** component, nearly
  independent (shared variance <1% for humans). Execution, not
  forecasting, determines profit — no trader type in the paper's data beats
  the price-implied accuracy benchmark. Bots entered markets >8 days before
  resolution vs. retail's ~3 days; roughly 70% of the bots' advantage was
  attributable to lifecycle timing, not superior calls.
- **Gómez-Cram, Guo, Jensen & Kung (SSRN 6617059):** ~3% of Polymarket
  accounts are persistently skilled; 44% of traders classified skilled on a
  random half of their events are also skilled on the other half. Method:
  hold each trader's actual markets, timing, prices, and bet sizes fixed,
  randomise only buy/sell direction, many times, compare realised PnL to
  that coin-toss benchmark.

**The implication for this project's own metric:** `edge = won −
entry_price` is a profitability measure that conflates two nearly
independent dimensions the research says should be separated. This is the
leading candidate explanation for both the original null result and Track
2's mixed variance split — and it motivated building and running the four
2026-09-05 measurements in §1, in the sequence chosen specifically because
the directional-skill test does not depend on the (now-missing) gap to be
informative on its own.

---

## 3. THE DISCOVERY-GAP ARC — what happened, what it cost, what it achieved

**The genuine finding (2026-08-20).** A pre-registered, full census (not a
sample) of the project's own 317-market canonical-relevance population
(Geopolitics/Elections, has trades, gap-clean, dateless-per-DB) found **203
of 317 were already resolved in reality but undiscovered in the DB** —
67.4% of the determinate ones. Cross-checked 15/15 against `tape_end`.
Real and growing (`live_monitoring` showed a *higher* rate than
`historical_backfill`), not a historical residue.

**Tranche 1 (2026-08-22) closed those 203 exactly.** 203 resolved / 98 open
/ 16 no-CLOB-response — an exact match to the census. **All 203 are
confirmed today (2026-09-04 verification): `resolved=1`, correctly
categorized (106 Geopolitics, 97 Elections), gap-clean, and inside the
canonical population.** This narrow finding is fully, cleanly closed.

**The sweep then widened to the full ~515k dateless population** —
tranche 2 plus segments 1-4, 2026-08-22 through 08-26 — and resolved
**215,887 markets** in total through the canonical write path. Of those,
**267 (142 Elections, 125 Geopolitics) reached the target categories —
0.12% of the sweep's own output.** The canonical thesis population moved
`~9,079 → 9,563` over the three weeks; **only 242 of that growth is
directly attributable to the entire eleven-day effort** (the remainder is
ordinary background activity that would have happened regardless).

**The wrong turn, stated plainly, per
`2026-09-04-thesis-population-lineage.md`:** widening the sweep's scope on
08-21 was the *right* call given what was known that day (the 317
population's flatness was correctly diagnosed as a classification-lag
artifact, not evidence the gap had stopped). **The cheap premise-test that
would have changed everything — "how fast does `category='Unknown'`
actually clear into Geopolitics/Elections?"** — was answerable in minutes
from an already-running log file (`logs/category_backfill.log`) that
predates this arc entirely. It was not run until **08-30, nine days and a
231,000-market sweep later**, and found the same ~19-32/day classification
rate a same-day check would have found — a 9.8-to-30.9-year backlog-
clearing horizon that predicted the sweep's actual 0.12% payoff almost
exactly. This is the project's own first standing rule ("test the premise
before building the instrument") violated in its most consequential
instance to date. The discipline around the sweep itself — pre-
registration, abort conditions, a genuinely rigorous backup-starvation
diagnosis, a verified `flock` guard — was excellent. The sequencing was
backwards.

**The sweep is formally STOPPED (2026-09-04), not paused.** Segment 5's
three prerequisites (resume segment 4's unwalked 16,000-market tail,
re-key the exclusion derivation on processed not materialised IDs,
implement launch-time-dependent `max_batches`) are **moot** — there is no
segment 5, and none should be built. The 16,000-market segment-4 gap is now
a permanent, accepted gap in coverage, not pending work.

---

## 4. THE CLASSIFIER ARC AND ITS FAILURE

**Why it was built.** Of the sweep's 214,413 resolved markets, only **225
(0.10%)** entered the canonical population — blocked by
`category='Unknown'`. Investigated whether Gamma (the upstream API) could
simply be asked: **no** — Gamma's category field is empty even for genuine,
current election markets (0 of 97 sampled, then 0 of 34 more, live). A
title-based classifier was structurally required.

**What was built, in order:** a schema migration (`category_source`
provenance column + `category_classification_log` sidecar table); a
deterministic pre-filter (13 keyword/pattern families, 87.6% coverage,
**zero market_ids inspected while drafting the patterns** — every pattern
traces to a committed doc, not to eyeballing the data, so the eventual gate
sample is uncontaminated by construction); two one-off Gamma slug fetches
for the swept and unswept populations (99.94% / 100% `event.slug` coverage
respectively); the validation gate sets, **drawn, frozen, and hand-labelled
before the LLM classification stage existed** (committed with no labels in
the tree, labels landed in the next commit — git history itself is the
proof the gate cannot have been tuned against); then the LLM classification
stage (`monitoring/relevance_classifier.py`, local Qwen3-Coder model).

**The gate result (2026-09-03).** **Precision PASSED** on all three
measured quantities (false-positive rate 0.67% on the template-exclusion
bucket, 6.00% on the ambiguous residual, both under their thresholds).
**Recall FAILED**: overall relevance recall **90.35%** against a **≥95%**
requirement, and **all six of six** stratified cells failed (87.62% to
92.49%, no cell close to 95%). Directional agreement passed narrowly
(90.12% against ≥90%).

**The diagnosis (2026-09-04, provisional — not Oscar's formal
adjudication).** A 100-row sample of the recall misses: **79% genuine
classifier misses** (stored label correct, classifier wrong), **8%
stored-label error** (pre-existing, not introduced by this classifier),
**13% genuinely ambiguous**. Even the most classifier-favorable reading
still leaves 86% as clear misses. The miss causes are **diffuse across 18
distinct market subtypes** — the largest single pattern (an appearance-prop
"will X say/post" carve-in) accounts for only 39% of misses; the rest spans
pardons, cabinet moves, a Senate vote, a referendum, military strikes,
diplomatic meetings, with no shared mechanical cause. **§3.11(a) — abandon
— is indicated over a one-shot retry**, because the design's retry
provision requires a narrowly-diagnosed, purely mechanical bug with a fix
arguable on paper before any new result exists, and a diffuse, majority-
genuine failure across 18 unrelated content types is not that shape.
**Oscar's formal §3.10 adjudication and blind spot-check remain
OUTSTANDING** — this document does not declare a final gate verdict, and
neither does the diagnostic; both are Oscar's to make.

**What survives, intact and reusable regardless of the classifier's fate:**
the pre-filter, the slug staging table, the schema
(`category_source`/`category_classification_log`), and the gate sets are
all explicitly *not* wasted — they were reasoned to be independently useful
when built, and nothing about the recall failure invalidates any of them.

---

## 5. WHAT WAS BUILT AND IS LIVE

**Canonical resolution write path.** `monitoring/resolution_writer.py`'s
`mark_market_resolved()`, three provenance columns
(`resolution_evidence_source`, `resolution_recorded_at`,
`resolution_evidence_detail`), `trg_resolved_no_unresolve` (verified live,
non-tautologically, inside rolled-back transactions), and the
`check_resolution_write_atomicity` invariant at Tier 0/OBSERVE. **Stages
0-2 shipped; 3 of 13 originally-mapped market-resolution writers have
migrated** (the sweep's own driver scripts inherit the canonical path
exclusively). **Stages 3-6 of the design are NOT done** — the comparator's
harder branches (cross-rank overwrite, same-rank disagreement) remain
essentially unexercised in production; cross-rank overwrite has fired
**zero** times across all ~210,000+ accepted writes to date, in tension
with the design's own prediction that it should be routine at scale — two
candidate explanations remain live, neither chosen.

**TradeEvaluator repoint**, with hardening pushed into the canonical
function itself (not wrapped around the one caller being repointed), so
all three of its callers benefit from one fix rather than becoming a fourth
variant.

**The `resolution_date` clobber fix** (`fast_resolution_check.py:267`):
`resolution_date = ?` → `resolution_date = COALESCE(resolution_date, ?)`,
matching its three already-guarded sibling write sites. A live dry-run
found 12 of 20 sampled at-risk markets were genuine, currently-active
clobber candidates — this was destroying real API-derived data on every
unguarded run, not a theoretical race.

**`resolution_sweep.py`'s `COALESCE` predicate fix**: keys on
`COALESCE(resolution_recorded_at, last_checked)` instead of
`resolution_date` alone, restoring roughly 7x the daily Channel-2 discovery
coverage this script had silently lost.

**The `flock` guard on the backup wrapper**, verified with a negative
control (the same blocked-run scenario replayed against the pre-guard
commit, which — correctly — ran the backup anyway despite a held lock,
proving the test actually depends on the guard). 27 assertions across 5
scenarios, including a demonstrated (not merely asserted) SIGKILL-survival
case.

**`sweep_terminal_signal.py`** (terminal marker + Telegram, guaranteed
never to raise) and the **`.env_trading` `set -a` launch fix** — the sweep
driver's Telegram notifications were silently dead because `.env_trading`
has no `export` statements, so sourcing it never propagated credentials to
child processes; `set -a` around the sourcing fixed it, verified by an
actual delivered test message.

**The Geo/Elec candidate-ordering fix in the daily backfill step
(2026-09-04):** `backfill_market_dates.py`'s daily invocation now draws the
Geo/Elec-tagged sub-population first, filling remaining budget from the
general pool — restoring exhaustive same-day coverage of that
sub-population (verified: at `--limit 2000`, all **499** currently-tagged
candidates are drawn, occupying the first 499 rows of the result) without
raising the limit, which the sweep's incompletion left unjustified.

**Tier-3 Claude-credit agents: FIVE DISABLED 2026-08-31** — `code-hygiene`,
`training-librarian`, `performance-analyst`, `signal-agent`,
`trader-intelligence` — commented out (not deleted), reversibly, with a
dated block and full re-enable procedure recorded in `138c03b`. Combined
with research-scout and integration-test-agent (already paused earlier),
the swarm's scheduled autonomous Claude footprint is now zero.

---

## 6. KNOWN DEFECTS, LIVE AND UNFIXED

- **`mark_market_resolved()` never sets `last_checked`.** 7 of the 9
  non-canonical writers it replaced did. Consequence:
  `requeue_resolved_market_traders.py` gates its entire query on
  `datetime(last_checked) > datetime(last_run)` — a canonically-written
  row is invisible to it **permanently**, not delayed. **195,625 of
  214,413 (91.2%) sweep-resolved markets are stranded**, affecting
  **8,077 open positions across 1,983 distinct traders**, a figure that
  grows continuously as the live monitor keeps writing trades against
  already-stranded markets. The old non-canonical writers set this column
  correctly; the canonical writer broke it. **NOT FIXED.** A naive
  backfill is not assumed safe either — `requeue_resolved_market_traders.py`
  builds unbounded `IN (...)` clauses with no batching, and a synchronous
  reset of ~2,000 traders' `pnl_last_updated` would create the same kind
  of burst-load contention already found incompatible with this system
  (the backup-vs-sweep starvation, §5).
- **`category`: 99.9% of sweep-resolved markets (214,155 of 214,413) sit at
  `'Unknown'`.** The classifier meant to fix this is abandoned pending
  Oscar's formal call (§4). `backfill_market_categories.py` (M9) runs at
  ~19-32/day against this backlog — 9.8 to 30.9 years to clear at current
  throughput.
- **`is_taker`: zero maker-side rows anywhere in the database** (621,350
  labeled trades, all `is_taker=1`, none `=0`). Both writer scripts'
  branching logic explicitly supports writing `0` for a confirmed maker
  match — the code is not the bug. Likely structural: on a CLOB, the
  taker's wallet sends the settling transaction; a resting maker order may
  never generate one of its own, so this project's per-trade-hash-based
  detection method may simply never observe a maker fill. **Root cause not
  established** — confirming this would require inspecting live Polygon
  receipts, not attempted.
- **Nine independent market-classification code paths across five
  vocabularies, no designated decision authority.** `markets.category`'s
  *write* side has been canonical since `column_definitions.py`; the
  *decision* side never was — three keyword forks (`market_filter.py`,
  `_is_geopolitics` in `detect_insider_activity.py`, `backfill_market_dates.py
  --geo-only`) were each copied by value out of `monitor.py` at different
  times and never re-synced, plus M9's own keyword pass and the (now-
  abandoned) LLM classifier.
- **`composite_skill_score.py`: 906 lines, zero callers, since 2025-12-05.**
  An elaborate 8-dimension, 100-point composite skill score, its only entry
  point (`get_composite_skill_score`) never called by anything in either
  repo. Found while grounding the canonical skill metric design — a fourth
  parallel skill-measurement system nobody had named.
- **ELO behavioural modifiers (`kelly_alignment_score`, `patience_score`,
  `timing_score`'s ELO-bonus role) inert since `W_BEH=0` (Stage 0b,
  2026-07-12)** — computed and written weekly, contributing zero to
  `comprehensive_elo`. (`timing_score` itself has since been repurposed as
  a component of the new canonical metric design, §7 — this is a different
  role, not a fix to the ELO bonus.)
- **The eight remaining unguarded cron wrappers** — only the backup
  wrapper has a `flock` guard; `run_daily_maintenance.sh` is named as the
  next and highest-priority target (it runs 2-10h daily against a growing
  window), never implemented.
- **`discover_leaderboard_traders.py` trending toward its 10-hour Sunday
  timeout** — runtime grew 283% against the prior Sunday (4,883s →
  18,714s) as of 08-23, plausibly sweep-adjacent (more geo/election
  resolutions to scan); flagged as degrading, not yet at the failure
  threshold, not re-checked since.
- **~300 markets/day dropped at ingest by an unaudited keyword filter** —
  absent from the DB entirely, not merely miscategorised; figure
  extrapolated from a single 2-hour window, not independently confirmed.

---

## 7. PRE-REGISTRATIONS WRITTEN AND THEIR STATUS

- **Discovery-gap-closure** (2026-08-21, amended 5 times) — steps 1-4
  executed; **step 5 (the second measurement) was NEVER RUN.** Per the
  09-04 lineage analysis, running it today would move the cohort-vs-
  placebo gap by roughly `-0.0003` — the newly-identifiable material from
  the classifier/sweep arc trends negative on both sides, by a similar
  small amount, and is too small to matter. (This is unrelated to, and
  should not be confused with, the much larger gap movement the N=0 gap
  check found — that movement is driven by ordinary pending→resolved
  accrual over three weeks, not by anything this pre-registration's own
  step 5 would newly surface.)
- **Track 2 CI power** (2026-09-04) — **RUN**, outcome Mixed (§1).
- **Copy-trade decay** (2026-09-05) — **WRITTEN, UN-RUN.** Its §4
  reproduction gate, inherited from Track 2's Gate A, tests the cohort's
  own point estimate and CI — not the cohort-minus-placebo gap the entire
  measurement is about. The N=0 gap check confirmed this gate would have
  **passed** on today's numbers while the gap itself had already gone
  missing. **This pre-registration needs its §4 gate amended to test the
  gap directly before it should be run** — not amended yet, per the task
  that found this.
- **Directional skill** (2026-09-05) — **RUN**, Outcome 2 (§1).
- **The canonical skill metric design** (2026-09-05) — proposes three
  components (a Gómez-Cram directional-skill benchmark, `tape_end`-anchored
  absolute earliness, `timing_score`'s existing relative-entry-percentile
  as relative earliness). **Component 1 (directional skill) has been run**
  (this is the directional-skill test above). **Components 2 and 3
  (absolute and relative earliness) have NEVER BEEN TESTED** — they remain
  proposed, not validated.

---

## 8. REUSABLE LESSONS

**The one-artifact-two-questions pattern, found five-plus times this
window.** `resolution_date` serving as both write-time and event-time;
`last_checked` as both freshness signal and (silently) resolution-discovery
gate; `avg_pace` timing CLOB fetch and DB commit as one number; a diff
comparing before-and-after states without checking whether the change did
anything at all; a single `endDate` sort key serving as both a real
timestamp and, for many rows, a placeholder. Each time, the fix was to
split the measurement, not reinterpret the single number it produced.

**Simulate a guard against real data ordering before trusting it.** The
unswept slug fetch's front-loaded synthetic-id cluster would have tripped
its own abort guard at batch ~2 with the *opposite* message from the truth
("identifier assumption wrong") had the guard's arithmetic not been
simulated against the actual sorted key distribution before launch.
Nothing in the code was wrong; the interaction between a correct threshold
and the real key order was.

**A diff comparing before and after cannot detect a change that does
nothing.** Twice this window — step 1's first attempt (a gate discarded
the response before new logic ever saw it) and Writer C style issues
elsewhere — a byte-identical dry-run diff was mistaken for proof of
correct behavior when it was actually proof of *no reachable behavior at
all*. Only a check against a population whose true answer was already
known caught it.

**Draw the gate before the thing it gates, and make the order provable in
git.** The relevance-classifier's validation sets were committed with no
labels in the tree; labels landed in the next commit. This is not a
convention — it is evidence a future skeptic can check without trusting
anyone's account of what happened.

**A metric that sums two things points at the wrong one.** Segment 4's
pacing-abort condition measured CLOB fetch time and DB commit time as one
number; the real cause (a starved backup holding a write lock under a
silent 30-second timeout) was invisible to that metric by construction and
was only found by reading outside the sweep's own telemetry entirely.

**Distributions contradict means.** The directional-skill pre-flight found
a post-split trade-count mean of ~27 per trader concealing a median of 12
(cohort) / 7 (placebo) — a heavily right-skewed distribution that directly
changed which minimum-count and split-half decisions were defensible. A
mean alone would have suggested comfortable power the actual distribution
did not support.

**Chat-Claude's premises enter the record and must be verified, not
inherited.** Repeatedly this window — the task prompt's own framing of
figures, dates, and even what a cited document predicted — needed
correction against the actual source before being carried into a decision
document. The 2026-09-04 lineage-prediction mix-up (a task prompt
conflating a narrow, correct 242-market-specific prediction with the much
larger, separately-caused overall gap movement) is the most recent
instance, but far from the only one this window.

---

## 9. WHAT THE NEXT SESSION SHOULD CONSIDER (proposed, not decided)

- **The obvious next question, now evidentially supported, not merely
  plausible:** what would a selector built on **directional skill**
  (Gómez-Cram-style, within-trader, no placebo needed) rather than
  **realised edge** look like, and does it identify a stable population?
  The directional-skill test found skill-like signal present in *both*
  the cohort and placebo populations, well above chance — the selection
  criterion failed, the phenomenon may not have.
- **Components 2 and 3 of the canonical metric** (absolute and relative
  earliness) remain untested and would speak directly to the execution
  dimension Della Vedova's research names as the more important one.
- **Oscar's outstanding gate adjudication and blind spot-check** for the
  relevance classifier (§4) — the formal decision to abandon or retry has
  not been made by the person the design assigns it to.
- **The `last_checked` fix and the 195,625 stranded markets** (§6) — real,
  quantified, growing, and not yet remediated; any fix needs an explicit
  decision on batching/rate-limiting the historical backfill, not a
  one-shot pass.
- **Explicitly NOT worth resuming, stated so it isn't rediscovered as
  unfinished work:** the discovery-gap sweep (formally stopped, its
  prerequisites moot); the relevance classifier in its current form
  (failed its own gate, diffuse cause, abandon indicated); the copy-trade
  decay ladder in its current form (its gate does not test the quantity
  that matters — amend before running, do not run as written).

---

*This document was generated by Claude (chat instance) on 2026-09-05 at
Oscar's request, to replace `MASTER_HANDOVER_2026-08-15.md` as the entry
point for new-chat handoff. It draws on the committed session summaries for
2026-08-16 through 2026-09-01 and, for 2026-09-03 through 2026-09-05 (no
session summaries exist for this range), directly on the decision docs
those dates produced. Treat it as a snapshot — verify anything load-bearing
against current repo state before relying on it if significant time has
passed.*
