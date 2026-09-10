# Session Summary — 2026-09-10 (Server Setup 15)

Documentation only. Every commit hash and figure below was checked
against its source this session. first-repo `main`, trading-swarm
`master`.

---

## HEADLINE — a published result was wrong for about an hour, and the correction is the finding

**The first copy-trade decay run (first-repo `c9619a4`, trading-swarm
`9732bc9`, committed 19:16–19:17 UTC) reported that copy-edge *rose*
from N=0 to N≈30–60 min and *survived* the 15-minute monitoring cadence
at `+0.03434`, CI `[+0.01369, +0.05622]` — a CI excluding zero.** That
was an artifact.

**The price substitution was not outcome-matched.** The harness took the
next trade in the market at or after `entry+N` from *any* outcome and
used its `trades.price` directly. In a binary market `trades.price` is
`P(that trade's own outcome)`, so an opposite-outcome trade contributes
`≈ 1 − p` where `p` belongs. **37.58% of the N=15 min substitutions were
on the opposite outcome** (13,330 of 35,468), and the error's aggregate
direction was upward.

**Corrected (2026-09-10b amendment `e8eca1c`, re-run first-repo
`1f43424` / trading-swarm `e941403`, committed 19:51–20:09 UTC):**
opposite-outcome prices converted `q → 1 − q`; an outcome-matched-only
curve reported alongside as a robustness check.

- Broad PIT-legal pool, primary (conversion): **N=0 `+0.01208`
  (CI `[−0.00168, +0.02645]`) → N=15 min `+0.01233`
  (CI `[−0.00186, +0.02410]`)** — flat from N=0, CI includes zero.
- No rung on **any of the three populations** (broad pool, Track-2
  cohort, Track-2 placebo), under **either construction** (conversion or
  outcome-matched-only), has a CI excluding zero **at or beyond the
  15-minute cadence**. Only the broad pool's N=1 min and N=2 min
  primary rungs exclude zero, and only barely (`+0.00067`, `+0.00050`
  lower bounds).
- Primary vs. outcome-matched-only CIs at N=15 min **overlap**
  (`material_disagreement = False`).
- Named outcome: **COLLAPSES-BEFORE-CADENCE.**

**What this establishes — stated precisely: not that edge decays, but
that no edge is demonstrable at N=0 either.** The N=0 own-edge
(`+0.01208`) already has a CI straddling zero. There is nothing
measurable for delay to erode. The 2026-09-10 published curve stands in
git as computed — it is not deleted — but it is superseded by the
corrected run, and the amendment `e8eca1c` item G records that the
outcome rule is now fixed: re-running with a different substitution rule
after seeing a disappointing curve is not an acceptable resolution.

Per the copy-decay consequence carried from the 2026-09-10 amendment
item H: COLLAPSES-BEFORE-CADENCE **moots the canonical metric design's
execution-dimension components 2 and 3 as capturability questions** and
**bears directly on Phase 2 as the primary experiment** — a copier
acting on this architecture's 15-minute cadence has nothing to inherit.

`metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` was
re-checked at the top and bottom of **every** run today (both decay
runs, the verification, and the calibration run) — **unchanged
throughout.**

---

## THE ARC IN SEQUENCE

### 1. Start-of-session progression check — read-only, no commit

Confirmed the 2026-09-09 geo drain settled as predicted. All three
services active; the 06:00 daily-maintenance run fired and completed
(one non-blocking failure: the canonical-drift check, see open
threads). Drain settlement: **Pool C (`geo_accuracy_pool = 1`) 4,276 →
4,469, +193**; `geo_resolved_trades_count ≥ 10` 6,097 → 6,379;
**exactly one trader crossed `geo_elo_active` above the 2175 LEGENDARY
threshold, upward** (`0xda9126be…`, no prior active geo ELO → 2321.20);
`geo_elo ≥ 2175` 89 → 91. `resolved_trades_count` / `research_excluded`
moved on ~576 / ~101 pre-existing traders plus 103 new trader rows —
flagged at the time as contrary to the task's "should be unchanged"
expectation but consistent with the overnight monitoring + 06:00
maintenance that legitimately recompute them; no unscheduled-write
signature. Delivered as a report in the reply; **no artifact
committed.**

### 2. `backfill_trade_results_geo.py` wired into daily maintenance — first-repo `4deb57c`, trading-swarm `9fd0734` (16:05 UTC)

Final part of the three-part plan (ingest fix `7ae0f2a`; baseline +
24,390-row drain `eee49ee`; this = the daily top-up). New non-blocking
`STEPS` entry "Evaluate geo/elec pending results (all traders)", between
"Evaluate new trader results" and "Reconcile geo resolved counts
[post-eval]".

**Arrival-rate check overrode the assessment's proposed `--limit 200`.**
The assessment sized 200 as ≈ 10× an estimated ~20/day. The first
post-drain cycle produced **460 pending rows** (`check_pending_geo`, ~19 h
after the drain took it to 0) — **1.5–2 orders of magnitude above
20/day**. All 460 were genuine post-drain arrivals (0 of 460 present in
the pre-drain manifest); ~250 structural (newly-resolved markets) + a
~210-row lump from `background_backfill` re-ingesting historical trades
on already-resolved markets as `'pending'`. Sized at **`--limit 1000`**
(= `BATCH_SIZE`, one commit point), which clears one observed cycle with
~2× headroom and is a top-up, not a drain (no historical backlog
remains). Manual `--limit 1000` run: 460 rows, 243 won / 217 lost / 0
invalid, 13.6 s, `check_pending_geo` 460 → 0, monitor heartbeat
unbroken, no lock contention, `metric_v2f_oos_result` sha256 unchanged.
New test `tests/test_geo_backfill_step_registered.py` (16 assertions,
following `test_weekly_full_sync_gate.py`). `run_tests.py` 25/25. True
steady-state rate not establishable from one cycle — revisit after a
week.

### 3. Research pass on the execution thread — no commit in either repo

The prompt's arc places a research pass here. **No committed artifact
exists in first-repo or trading-swarm for it** (git log for 2026-09-10
shows only the four first-repo / seven trading-swarm commits listed in
this summary). It appears to have been chat-Claude / task-preparation
work that fed the framing of steps 4–8 rather than a committed
deliverable. Recorded here so the arc is complete; **not reconciled
into a commit that does not exist.**

### 4. Copy-trade decay pre-registration re-pin + first run — trading-swarm `7b9e1e7` (amendment, 18:55 UTC), first-repo `c9619a4` / trading-swarm `9732bc9` (run, 19:16–19:17 UTC)

Amendment `7b9e1e7` (committed alone, no results in the tree, per the
task's hard gate) re-pinned `2026-09-05-copy-trade-decay-prereg.md` off
the cohort-minus-placebo **gap** — which stopped being demonstrated
(N=0 gap `−0.0072`, paired CI straddling zero, `7aa3fe5`; presplit-edge
selector falsified 2026-09-05 Outcome 2) — onto the **broad PIT-legal
classifiable pool's `edge(N)` vs. fixed per-category cost floors**
(geopolitics 0.0005–0.010, elections 0.0056–0.020). Items A–I fixed
blind: primary population = broad pool (5,907 traders re-derived at run
time), cohort/placebo kept as secondary shape-only; N=0 gate replaced
with an internal-consistency check (harness N=0 must reproduce
`measure_oos` on the same positions, |Δ| ≤ 1e-9); 15-point N ladder;
outcomes named.

Run `c9619a4`: N=0 gate **passed bit-identically** for all three
populations. And it produced the artifact curve now known to be wrong —
see the HEADLINE and step 5.

### 5. Price-substitution verification — trading-swarm `3c22b0c` (19:41 UTC), read-only

Triggered by the run's own "what was not determined" flag: the N=0→30 min
rise was "observed, not explained," and a delayed copier appearing to
beat the trader being copied **cannot be true.**

- **Part 1 — what `trades.price` means, established empirically** (not
  from the column name), per `MASTER_HANDOVER_2026-08-15` §1
  methodology rule 4: paired opposite-outcome (`Yes`/`No`) trades on the
  same resolved non-gap market, matched within a short window,
  `price_Yes + price_No`: median **1.00000** at every window (10 s:
  n = 45,984, IQR `[0.9990, 1.0010]`, 97.9% within `[0.98, 1.02]`;
  300 s: 92.0% within `[0.98, 1.02]` — complementarity is empirical and
  tight, loosens with the window). **`trades.price` is `P(the outcome
  that trade bought)`, both sides.** STOP-condition check: N=0 uses
  `positions.entry_avg_price`, which a 4,000-position sample confirmed
  is outcome-matched (0.00% mismatch) — the result of record is
  unaffected; the defect is confined to the `N>0` tape substitution.
- **Part 2 — the substitution predicate quoted verbatim.** The tape
  query `SELECT market_id, timestamp, price FROM trades WHERE market_id
  IN (…) ORDER BY market_id, timestamp` has **no outcome filter, no
  side filter**; `substitute_price_at_N` picks `pxs[bisect_left(tss,
  target)]` regardless of outcome; `OOS_POSITIONS_SQL` does not even
  select `p.outcome`. **37.58%** of N=15 min substitutions land on the
  opposite outcome.
- **Part 3 — diagnostic estimate (labelled not-a-correction).** N=15 min
  broad pool, outcome-matched substitutions only: **`+0.01592`,
  CI `[−0.00130, +0.03317]`** vs. published `+0.03434`; 22,138 positions
  / 13,853 pairs, not thin. The rise from N=0 (`+0.01208`) essentially
  disappears. Opposite-outcome-only context: `+0.06693`.
- **Part 4 — survivorship checked independently.** §5b exclusions at
  N=1 min shift the weighted N=0 gap by `+0.00009` against a ~+0.019
  rise. Complement mechanism accounts for essentially all of the rise;
  survivorship ≈ 0.5%.

### 6. Second amendment + corrected re-run — trading-swarm `e8eca1c` (amendment alone, 19:51 UTC), first-repo `1f43424` / trading-swarm `e941403` (re-run, 20:09 UTC)

Amendment **2026-09-10b** (`e8eca1c`, committed alone, blind, 256
insertions / 0 deletions, pointers at §1 and the 2026-09-10 amendment's
item E): the outcome rule. (A) **Conversion is primary** —
opposite-outcome `q → 1 − q`; justified from the verification's Part 1
distribution; expected per-substitution error ≈ ±0.001 (IQR) to ±0.02
(95%), ≈ mean-zero, aggregate bias order 1–2×10⁻³, an order of
magnitude below the +0.018 inflation from leaving it unconverted.
(B) **Outcome-matched-only is a mandatory secondary** at every rung —
secondary because discarding ~37% is a non-random selection.
(C) **Material disagreement** fixed numerically: non-overlapping 95% CIs
at N=15 min on the broad pool → outcome **PRIMARY-AND-ROBUSTNESS-DISAGREE**.
(E) sub-15-min region recorded as a **permanent trade-tape limitation**
(median realised delay 12–22 min at nominal N=1 min — no rule and no
finer rung can fix it). (F) N=0 gate unchanged, re-run as-is.

Re-run `1f43424`: N=0 gate passed bit-identically all three populations;
sha256 unchanged; no THIN rung; `outcome` available for every
substituted trade. Result = the HEADLINE. Cohort's 2026-09-10
"invert-to-negative-by-13-min" and placebo's "jump-to-+0.070" shapes
were **also artifacts** — under conversion both decline gently, same
shape as the broad pool, all CIs straddling zero.

### 7. External-literature research — no commit in either repo

The prompt's arc places a literature pass here. As with step 3, **no
committed artifact exists** for it. The three arXiv references it
produced — `2602.19520` (recalibration slopes 0.99 → 1.32),
`2606.04217` (mean return by price decile −0.0023 → +0.0076),
`2607.14430` (calibration near reference down to ~half an hour), plus
the 124M-trade "no general longshot bias" counter-finding — arrived
**inside the step-8 task prompt** and are cited there. Recorded so the
arc is complete; not attributed to a commit that does not exist.

### 8. Own-market calibration — first-repo `b81e2f6`, trading-swarm `bdaa5b4` (20:49 UTC)

Premise test. Read-only, no selector / cohort / placebo — deliberately
abandoning trader selection. `scripts/own_market_calibration.py`,
artifact `own_market_calibration_20260910T204249Z.json`. See "The
calibration finding" below.

---

## WHAT THE DEFECT TEACHES (the session's most transferable lesson)

1. **The pre-registration was underspecified, not the code wrong.**
   `2026-09-05-copy-trade-decay-prereg.md` §1 and the 2026-09-10
   amendment item E both say "the next trade in that market at or after
   `entry+N`, **from any trader**" — addressing *trader*, never
   *outcome*. In a binary market a trade carries the price of *its own*
   outcome, so "the next trade's price" is ambiguous between
   `P(held outcome)` and `P(¬held outcome)`. The implementation followed
   the written rule exactly.

2. **Chat-Claude wrote the 2026-09-10 amendment reaffirming that exact
   rule** (item E, "§1's rules are reaffirmed, not changed") **and did
   not catch the gap.** The amendment was a re-pin of the viability bar;
   the price-lookup wording passed through untouched and unexamined.

3. **The error's direction was flattering.** It made copy-trading look
   viable — a rising, cadence-surviving, zero-excluding curve. A
   deflating artifact would have invited scrutiny; a confirming one did
   not. It was found only by noticing that a copier entering 13–50 min
   *after* the trader appeared to *beat* that trader, which cannot be
   true, and following that thread rather than banking the result.

4. **Same shape as a known prior.** `MASTER_HANDOVER_2026-08-15` §1
   records the `geo_elo` docstring embedding the same sign error as its
   code — a field's meaning inferred from its name / surrounding text
   rather than established empirically. The fix in both cases is the
   paired-opposite-outcome (or randomized-direction) empirical check,
   not a re-read of the code.

5. **Three shape readings were retracted on correction.** The corrected
   re-run doc marks two numbered observation-log entries **RETRACTED**,
   covering three distinct 2026-09-10 findings: (a) the N=0→30 min
   *rise* read as an "immediacy premium a patient copier avoids" —
   built entirely on the artifact; (b) the cohort's immediate
   collapse-and-inversion; (c) the placebo's jump. Only the "elections
   decays slower than geopolitics" reading survived, downgraded to
   point-estimate-only (all CIs include zero).

   *(Discrepancy flagged, not reconciled: the task prompt says "three
   observation-log entries were retracted." The repo's re-run doc
   retracts **two** numbered entries — entry 2 and entry 3 — where
   entry 3's retraction spans the cohort and placebo readings. Three
   findings, two log entries.)*

---

## THE CALIBRATION FINDING

`scripts/own_market_calibration.py` (first-repo `b81e2f6`), artifact
`own_market_calibration_20260910T204249Z.json`, decision doc
`2026-09-10-own-market-calibration.md` (trading-swarm `bdaa5b4`).
Read-only; `--persist` never passed; `metric_v2f_oos_result` sha256
unchanged. `seed=42`, `reps=1500`, two-way clustered bootstrap on
`event_cluster_labels.cluster_id` **and** market.

**Population** [V]: `backtest_window_sql` with an early `window_start`
(`resolved=1`, category ∈ {Geopolitics, Elections}, gap-clean,
`tape_end`-anchored), restricted to binary `winning_outcome`. **9,799
canonical → 9,739 used** (60 non-binary excluded); **29.1% resolve
YES**. 4,693 markets carry an event-cluster label, 5,046 are solo.

**Price definition** (fixed structurally, before any calibration
output — the STOP condition): the `trades.price` of the last trade at or
before `(tape_end − h)`, normalised to `P(Yes)` (`price` if the trade's
outcome is `'Yes'`, else `1 − price`), for `h ∈ {0.5 h, 3 h, 12 h, 3 d,
14 d, 45 d}`. Anchor = `tape_end`, not `resolution_date` (O-36: ~11%
impossible values). Not a VWAP window — the median market has 8 trades
over its whole life.

### Slope

Logistic recalibration slope `b1` in `P(y=1) = sigmoid(b0 + b1·logit(p_yes))`:

| lead time | pooled slope | 95% CI | CI excl. 1.0 |
|---|---|---|---|
| ~0.5 h | **1.293** | [1.196, 1.417] | yes |
| ~3 h | 1.228 | [1.135, 1.331] | yes |
| ~12 h | 1.140 | [1.052, 1.238] | yes |
| ~3 d | 1.123 | [1.031, 1.231] | yes |
| ~14 d | 1.155 | [1.031, 1.305] | yes |
| ~45 d | 1.149 | [0.983, 1.386] | no (thin) |

- **Slope > 1 at every lead time, CI excluding 1.0 at 5 of 6** —
  underconfidence (prices compressed toward 50%; longshots slightly
  overpriced, favourites slightly underpriced). **Direction agrees with
  arXiv 2602.19520.**
- **Shape disagrees.** The pooled slope is **highest near resolution
  (1.293 at ~0.5 h) and falls with time-to-resolution** to ~1.12–1.16,
  flat thereafter — the **reverse** of the external 0.99 → 1.32 *rise*.
  **Recorded as a discrepancy with a literature that already
  disagrees with itself (the 124M-trade "no longshot bias"
  counter-finding); not reconciled.** Geopolitics carries the higher
  slope at every lead time (1.46 / 1.38 at 0.5 h / 3 h).

### Deviations

- Concentrated in the **two price-extreme deciles**. Bucket [0.0, 0.1)
  (≈ 57% of the population): deviation **−0.006 to −0.009** across
  horizons, CI-solid (excludes ±floor-lo) only at the short lead times.
  Bucket [0.9, 1.0) (≈ 17%): **+0.010 to +0.030**, CI-solid at ~3 d
  (`+0.0221`, CI `[+0.0021, +0.0349]`).
- **All solid deviations are ≈ 0.006–0.022 in edge units — at
  cost-floor magnitude, not several times it.** The large-effect
  scenario (~+0.06 at p ≈ 0.80 implied by a 1.32 slope) **does not
  appear at any cell with supporting n**: every p ∈ [0.5, 0.9) bucket
  with n > 200 has a deviation CI spanning zero. The gate opened on 6
  cells; 3 have defensible n (> 400), all Geopolitics price extremes;
  the other 3 are thin (n = 117, 95, 14). **No Elections cell clears
  its own floor.**

### The reconciling hypothesis is REFUTED

Chat-Claude's proposed reconciliation — miscalibration lives where few
people trade, so entry-weighted edge averages to zero — **is disproved
by measurement.** OOS overlay: 151,360 positions, ≈ $100.75 M.
**Bucket [0.0, 0.1) holds ≈ 58% of entry volume and bucket [0.9, 1.0)
≈ 22% — ~81% of trader volume sits in the same two price-extreme
deciles that carry the solid calibration deviation.** Deviation and
entry density coincide on the mass; they are not disjoint. What differs
is the *weighting*: volume-weighted mean |deviation| **0.0131** vs.
plain **0.0227**; in those cells the entry-weighted edge
(`won − entry_price`, order ±0.3–3 pp, mixed sign, dragged by the rare
large loss in a near-certain bucket) is a smaller, noisier quantity
than the one-signed price-weighted deviation. **Record: a chat-Claude
premise disproved by measurement.**

*(No committed project finding is contradicted — the project's nulls are
entry-weighted; this is price-weighted; the task's own premise is that
the two can differ.)*

---

## THE ONE LIVE THREAD

**Part 3 of the calibration run (gate open): calibration conditioned on
directionally-skilled-trader *presence*.**

Framed exactly as in the run: **skilled-trader presence as a
CONDITIONING VARIABLE on market mispricing, not a copy signal.** The
copy-decay null does **not** close this — it says there is no edge to
inherit from a trader's *entry*; this asks whether their *presence
marks* a mispriced market, which is actionable at one's **own** entry
time and price, which copying is not.

Instrument: the PIT-legal directional-skill pool
(`directional_skill_pit_legal_pool_20260906T160303Z.json`,
`raw_skilled_traders`, 1,494 traders; harness calibrated ~5% raw /
BH=0 across 36 zero-skill cells on 2026-09-06; persistence 37.0% vs.
18.6%). A population market is skilled-present iff ≥ 1 of those traders
holds any position in it: **5,619 of 9,739 markets (57.7%)**.

| lead time | skilled-present slope [CI] | skilled-absent slope [CI] |
|---|---|---|
| ~0.5 h | **1.400** [1.258, 1.584] | 1.178 [1.041, 1.347] |
| ~3 h | **1.310** [1.192, 1.470] | 1.122 [0.990, 1.297] |
| ~12 h | **1.197** [1.089, 1.336] | 1.049 [0.907, 1.225] |
| ~3 d | **1.169** [1.059, 1.312] | 1.037 [0.885, 1.242] |
| ~14 d | **1.175** [1.036, 1.354] | 1.123 [0.900, 1.491] |
| ~45 d | 1.174 [0.994, 1.424] | 1.074 [0.781, 1.757] |

**Skilled-present markets carry a higher recalibration slope at every
one of six lead times.** The present-slope CI excludes 1.0 at **5 of
6**; the absent-slope CI excludes 1.0 at **1 of 6** (~0.5 h only). **But
the present and absent CIs overlap at every horizon** — the
present-minus-absent gap is a consistent *direction* across all six
lead times, not a per-horizon-significant difference.

**Competing explanation, unresolved:** compositional — skilled-present
markets are the 57.7% majority and are plausibly larger, longer-lived,
or a different market-type mix. The run did not control for this.

---

## OSCAR'S STATED DIRECTION (recorded for the next instance)

*Recorded as stated, not endorsed here.*

- It is **more likely the project will use what it has already built
  than find an edge from scratch.** The intuition is that whatever works
  will involve **tracking skilled others somehow** — which is why the
  live thread above (skilled-presence as a mispricing marker) matters
  even though the copy-decay null closed the direct-copy path.
- A future session should **sweep everything built over the last 10–12
  months and heat-map it against current external work** for promising
  combinations — a deeper, full-context version of today's research
  pass (steps 3 and 7).

---

## OPEN THREADS CARRIED FORWARD

1. **Part 3's causal-vs-compositional question — the live one.**
   Whether skilled-present markets are more miscalibrated because
   skilled traders select into mispriced markets, or because
   skilled-present markets differ structurally (they are 57.7% of the
   population). Not resolvable without a matched comparison.
2. **Mid-price-decile calibration deviations.** In this population
   deciles [0.1, 0.9) hold ~200–420 markets each at short lead times,
   fewer at long ones; every one has a deviation CI spanning zero at
   reps=1500. The large point estimates (+0.10 to +0.18) are not
   distinguishable from noise.
3. **Why the calibration slope shape disagrees with the literature**
   (falling here, rising in arXiv 2602.19520). Candidates not chased:
   the 29% YES base rate and its interaction with the logit-linear
   form; this population's short-lived-market mix; the tape-end anchor
   vs. the external studies' clock.
4. **The ~210-row `background_backfill` re-ingestion lump.** If it
   recurs weekly, the ingest path (`background_backfill_worker.py`'s
   hardcoded `trade_result='pending'`) is not fully closed by `7ae0f2a`,
   and the remedy is at ingest — not a bigger `--limit` on the daily
   step. Watch the per-run "Found N pending trades" line in
   `daily_maintenance.log`.
5. **The canonical-drift check still exits 1 every day.** One residual
   violation — a `geo_elo_active >= 2175` literal in
   `characterize_legendary_overlap_recompute.py` (first_seen
   2026-09-08). Non-blocking; register-suppressed from Telegram; but a
   permanently-red maintenance step that a reader will keep
   re-discovering.
6. **The relevance-classifier gate adjudication** — still outstanding
   (2026-09-03 gate: precision PASS, recall FAIL 90.35%; 09-04
   diagnostic indicated §3.11(a) abandon; Oscar's formal call pending).
7. **Process hygiene:** ~5 leftover wait-loop bash shells (malformed
   `until ! pgrep …; do sleep …; done` spinners from background waits —
   read-only, no DB writes, harmless) and 1 Monitor task
   (`befbcizwd`, armed for the calibration run which has since
   completed) left running at session end.

---

*Generated 2026-09-10 (documentation only; no computation). Sources:
first-repo commits `4deb57c`, `c9619a4`, `1f43424`, `b81e2f6`;
trading-swarm commits `9fd0734`, `7b9e1e7`, `9732bc9`, `3c22b0c`,
`e8eca1c`, `e941403`, `bdaa5b4`; artifacts
`copy_trade_decay_20260910T191052Z.json`,
`copy_trade_decay_20260910T200321Z.json`,
`own_market_calibration_20260910T204249Z.json`. `MASTER_HANDOVER_2026-09-06.md`
remains the entry point and is not superseded by this summary.*
