# Session Summary — 2026-09-18 (Server Setup 20)

Documentation only. Every commit hash and figure below was checked against
its source this session. first-repo `main`, trading-swarm `master`.

**One discrepancy flagged up front, per instruction not to reconcile
silently:** this summary's source brief titles today "Server Setup 20."
The most recent prior session summary (2026-09-13) is titled "Server
Setup 18," and no "Server Setup 19" exists anywhere in `brain/decisions/`.
Separately, "Server Setup 20" was **already used once before**, for
2026-06-04's summary — three and a half months earlier than today, and
two numbers higher than September 13's "18." The counter does not run
strictly with session chronology across this corpus, for reasons not
established here. The title below uses "Server Setup 20" exactly as
instructed; this note exists so the numbering gap isn't silently
smoothed over.

---

## HEADLINE — a 21-hour-inert fix finally landed clean, a foundational paper was read for the first time, and three of five things the project believed about its own instruments turned out to be wrong

The day's three pieces build on each other in a specific order: first,
the ingestion fixes committed the day before (`01525d7`, `42d241a`) were
finally restarted into the live service and measured working exactly as
designed. Second, with cadence recovered, an entirely different thread —
reading the three papers this project's whole current framing rests on,
properly, for the first time — found one of them freshly primary-sourced
and produced real corrections to numbers this project had been repeating
secondhand. Third, and **the session's most consequential work**: before
building anything on either paper's method, the five components any such
work would actually rest on were checked against the project's own code
and data, not assumed. **Three of the five came back materially
different from what the project believed**, and one — an instrument the
project's own prior documentation cited as "100% coverage, zero
negative-lag artifacts" — does not exist anywhere in the codebase at
all. None of this was softened for this summary, per instruction.

---

## PART A — THE INGESTION FIX LANDING

The three monitor fixes committed 2026-09-17 (notify-queue batch drain +
single-sleep cycle wait, `01525d7`; paginated 10,000-row fetch, `42d241a`)
had sat inert for roughly 21 hours — the restart that would make them
live had not happened. This session did that restart: `systemctl restart
polymarket-monitoring` at **16:22:21 UTC**, a clean SIGTERM stop (no
SIGKILL needed), new **PID 67130**.

Three full post-restart cycles were measured. Every stated expectation
was confirmed:

- **Cycle gaps 904-907s**, against a 900s target — recovered from a
  67-68 minute pre-fix band (measured directly on the last five pre-restart
  cycles, #24-#28).
- **`Processing N` matched each cycle's own `new_trades` count exactly**,
  no carryover, on all three cycles (65/64/86).
- **2-3 API pages per cycle**, no 429s, no 408s, no "database is locked"
  anywhere across startup or all three cycles.
- **Flagged-trader trades captured: 464 / 389 / 533 per cycle**, against
  ~49 on a comparable window before the fix.
- **Ingestion ~343 trades/hour** in the post-restart window, against
  ~1.3/hour over the preceding five days — roughly 260x.
- **`notified = 0` held at zero**, both before and after the restart.

**Root cause, stated plainly**: the Data API's `after` timestamp
parameter is ignored server-side, and testing confirmed this — identical
results regardless of the value passed, ISO or unix-epoch. The cursor
built on it never worked, at any point. Separately, the client's 500-row
fetch limit was an unexamined constant against a real server cap of
10,000 — confirmed by direct testing (`limit=15000`→10000 capped,
`limit=20000`→10000 capped). Two independent, compounding defects, not
one.

**A secondary, unplanned confirmation**: the observer's RSS **fell from
~246 MB to 207 MB** over the ~35 hours since it was bounced (by an
unattended-upgrade restart on 2026-09-17, not a planned one) — the first
time this process has not climbed since the 2026-09-13 pruning fix
landed. An accidental restart supplied the first real test of a planned
fix.

**Open, not resolved this session**: the 2026-09-12-to-now trade gap
remains unbackfilled, and whether to backfill it at all is undecided.
And the 2-3 pages/cycle actually measured is above the ~1-2 pages the
fix's own design doc predicted at a healthy cadence — if it stays at 3
indefinitely, the 10,000-row-per-page cap is being hit every single
cycle, not just during the initial catch-up from the pre-fix gap.

---

## PART B — METHODOLOGY EXTRACTION (trading-swarm `6c9f2d9`)

Access status, honestly reported per paper:

- **Gómez-Cram, Guo, Jensen & Kung — PRIMARY.** The actual 78-page PDF
  (June 25, 2026 revision) was obtained via co-author Howard Kung's
  personal working-papers page, not SSRN (SSRN itself remained
  Cloudflare-blocked on every route tried).
- **Mitts & Ofir — SECONDARY ONLY.** SSRN confirmed Cloudflare-blocked
  via both the fetch tool and a raw `curl` (ruling out a tool-specific
  block). Read via four independent arXiv papers that engaged with the
  working paper's methods directly, plus a Harvard Law Forum repost.
- **Della Vedova — SECONDARY ONLY.** SSRN blocked, including the
  follow-up paper. Read via the author's own public GitHub reproduction
  repository (code plus a companion methodology.tex), labeled
  "secondary-but-authoritative" in that document to distinguish it from
  ordinary blog/press secondary material.

**Real citation corrections, now that primary text exists for Gómez-Cram
et al.**: this project had been citing **10,000 simulations** (the
primary text says **B = 1,000** throughout; "10,000" does not occur
anywhere in the paper); **44% persistence** (the primary text says
**46%**, likely version drift between the original April posting and
this June revision); **3.14% skilled** (the primary text says **3.16%**).

**Question A — does Mitts & Ofir's permutation test already do the work
of an activity-matched placebo here? CANNOT DETERMINE FROM AVAILABLE
ACCESS.** No source reached, including the four academic papers that
read the working paper closely, specifies what is permuted or held
fixed. This must **not** be assumed to match Gómez-Cram's confirmed
activity-matched design — a different paper, independently constructed.

**Question B — should the 2026-09-12 shortlist reorder? No change
indicated.** Reviewed against every shortlist item; nothing extracted
elevates an excluded or deprioritized candidate, or changes any current
item's scoring inputs.

---

## PART C — THE COMPONENT VALIDATION (trading-swarm `5b0e944`) — the session's most consequential work

Five components any Gómez-Cram- or Della-Vedova-based work would rest
on, checked directly against code and data before building anything.
**Three of five came back materially different from what the project
believed.**

**1. `is_taker` — the inherited explanation is wrong, though the practical
conclusion partly survives.** Verified with 3 external calls total (1
call to the public `/trades` API, 2 on-chain transaction-receipt
lookups): the public API has **no maker/taker field anywhere** and
attributes each transaction to exactly one wallet; on-chain `OrderFilled`
logs **do** carry correct role data for every participant — confirmed
directly by finding the project's own tracked wallets appearing as maker
in transaction legs. The root cause is not a labeling bug on rows that
exist — the live ingestion pipeline structurally only ever creates a row
from the transaction's taker side, so maker-side fills were never
captured as rows to label in the first place. **Recoverable, but only
via a real engineering build**: an on-chain sweep (the query logic
already exists in `polygon_event_scanner.py`) plus a currently
nonexistent INSERT path for events that find no matching row. Not a
quick fix. A separate, previously-undocumented hardcoded-contract-address
bug was also found in the existing labeling script (`polygon_maker_taker.py`'s
`EXCHANGE_CONTRACT` constant does not match the settlement contract seen
on at least the two real transactions inspected).

**2. The directional-skill harness randomizes per-position, not
per-event as Gómez-Cram's primary design does** — a foundational
difference, not a cosmetic one, since the paper explicitly built its
event-level unit to avoid exactly the failure mode (splitting correlated
same-event positions into independently-flipped "bets") that this
project's implementation has. Separately, **the p-value floor is worse
than previously on record**: checked directly against the actual
committed result artifact that produced the 37.0%/18.6% figures, **24.0%
of the 146-trader cohort and 8.6% of the 607-trader comparison group are
pinned at the p-value floor** at the real REPS=10,000 configuration —
worse than the 12.5% previously cited, which turned out to be from a
different, earlier pre-split stage at REPS=1,500, not the stage that
actually produced the headline number. **This does not appear to flip
the qualitative 37.0%/18.6% persistence result** — the pinning asymmetry
is consistent with, not contradictory to, genuine skill persistence, and
"does not appear to" is the honest strength of that statement; it was
not independently re-verified at higher precision, which would itself be
a research measurement and was out of scope.

**3. The 26.1% vs. 3.16% skilled-rate gap is not like-for-like — different
denominators, not a genuine eightfold concentration.** This project's
26.1% is skilled-count over its own *classifiable* population; Gómez-Cram's
3.16% is skilled-count over their *full, unfiltered* population. Computed
on the same basis (skilled/classifiable-population) from figures already
in the primary text: **~3-4x, not ~8x** (26.06% vs. 8.63% raw; 20.55% vs.
5.33% BH-corrected). A residual 3-4x gap remains, plausibly explained by
this project's category-restricted (Geopolitics/Elections-only)
population being genuinely more skill-differentiated — stated as a
plausible, unconfirmed candidate, not established.

**4. Entry-to-resolution lag, tape_end-anchored, does not exist anywhere
in this codebase as an instrument — stated plainly, as instructed.** The
2026-09-05 execution-signal-feasibility work is on record describing
exactly this gap in its own words ("Nothing in the ELO/edge pipeline
computes [entry-to-resolution lag]"), and this session's direct code
search confirms it independently: the only thing that resembles it
(`detect_insider_activity.py`'s narrow `s4_days_before_resolution`
signal) is not tape_end-anchored, uses the raw `resolution_date` column
directly, and therefore inherits that column's already-documented ~11%
logically-impossible-value defect rather than routing around it via the
canonical population function. **`timing_score` is fit for the specific,
already-defined 169-trader Track2 cohort** (contamination touches none
of its 3,795 OOS positions) **but not at the general population level**
— 21.2% of all non-null scores sit at the ambiguous 0.5 neutral value,
and a freshly-cited stale/drift failure mode (2 of a checked 300-trader
sample recomputed to neither the fallback default nor 0.5, but to a
genuinely different value) means even non-0.5 stored scores cannot be
trusted as current without individual verification.

**5. The execution-quality benchmark is confirmed endogenous, and
specifically weakest in the high-volume tercile — exactly where the
research cohort concentrates.** Across all three tested time windows
(±1h, ±6h, ±24h), the high-volume tercile of traders has the *lowest*
density of nearby comparison trades of any tercile, at every window, not
a noisy or window-specific effect. The one non-endogenous alternative in
the corpus (order-book mid-price) covers 3.57% of relevant markets with
zero overlap with the research cohort.

---

## PART D — THE BOOKMARK: WHERE THIS RESUMES

**Flagged, not silently affirmed, per the same discipline the prior
session summary applied to its own carried-forward research thread**: the
research-direction conversation below (Oscar's judgment on a Gómez-Cram
replication, and a specific entry-timing-repointing proposal attributed
to a separate chat session) is recorded here exactly as stated in this
task's own brief. No commit in either repository this session documents
that conversation independently; it is not verified against a committed
source, only recorded as told.

As stated: Oscar judged a straight Gómez-Cram replication too
well-trodden to be a final destination, and asked for less-established
branches. The proposal under discussion, **not yet tested or
pre-registered**, is to repoint the project's own calibrated
randomization harness at **entry timing** rather than direction — hold
market and direction fixed, randomize when within the market's life the
trader entered, and ask whether the actual entry beat a random entry in
the same market. Same harness, same BH correction, same calibration
already proven at a 5% floor (per `instr_v7`'s null-calibration work).

**What today's component validation did to that proposal: it is now
constrained, not dead.** Four things this session found bear on it
directly:
- The harness's per-position-vs-per-event randomization difference (Part
  C.2) would need resolving before repointing it at anything new — the
  same foundational gap applies regardless of what's being randomized.
- The p-value floor pinning (24.0%/8.6% at the real headline
  configuration) is a real limit on any ranking or persistence claim this
  repointed version would produce, not unique to the direction test.
- `timing_score` is cohort-only, not general-population-fit (Part C.4) —
  relevant if the entry-timing version leans on it for anything beyond
  its own from-scratch randomization.
- **The tape_end-anchored entry-to-resolution lag this proposal's
  framing would most naturally assume does not exist** (Part C.4) and
  would have to be built from scratch, anchored correctly this time, not
  assumed already in place.

**Two smaller branches raised and not pursued this session**: whether
the project's pre-filter genuinely concentrates skill (Part C.3 found
this is now a ~3-4x story, not ~8x — weaker than it looked, not
resolved); and that this project's own persistence design has a
comparison group Gómez-Cram's design lacks (noted, not developed
further).

**The largest live option, unscoped**: if maker/taker identity is
recovered via the on-chain build named in Part C.1, Della Vedova's
decomposition moves from approximable to directly computable — a
stronger position than any variant of the Gómez-Cram branch, since it
would be testing the project's own stated current framing (execution,
not information) rather than adapting someone else's direction-only
design. **That build has not been scoped or costed** — Part C.1 named
what it would require (an INSERT path, on-chain sweep, price/market
reconstruction from decoded amounts) but did not estimate hours or a
concrete plan.

---

## OPEN THREADS CARRIED FORWARD

- **The 2026-09-12-to-now trade gap** — unbackfilled, whether to
  backfill at all still undecided.
- **The on-chain maker/taker recovery build** — unscoped, uncosted, the
  precondition for Della Vedova's decomposition becoming directly
  computable.
- **The hardcoded-contract-address bug in `polygon_maker_taker.py`** —
  found this session, not fixed, per scope.
- **The directional-skill harness's per-position vs. per-event
  randomization gap against its primary source** — found this session,
  not fixed.
- **The relevance-classifier §3.10 adjudication** — outstanding since
  the 2026-09-03 gate result; **fifteen days** now, the oldest open item
  carried forward.
- **Telegram token rotation** — still undecided.
- **The 195,625-of-214,413 stranded-markets remediation**
  (`mark_market_resolved()` never setting `last_checked`) — measurable,
  undecided.
- **24 known disconnections** (2026-09-13 built-never-connected sweep) —
  deletion still deferred until a remediation path is chosen.
- **`background_backfill_worker`'s zero-completion anomaly**, flagged
  2026-09-17, still unexplained.
- **`scripts/` at function granularity** — the largest surface the
  built-never-connected sweep did not cover, and now also the surface
  this session's own `is_taker` and harness findings both came from —
  the most likely place a future pass finds more of the same pattern.

---

## What this document does NOT do

No verdict on what to do next, on either the ingestion open items or the
entry-timing proposal. Part C is stated exactly as its source document
states it, not softened: three of five components differed materially
from what the project believed, and one cited instrument does not exist
at all.
