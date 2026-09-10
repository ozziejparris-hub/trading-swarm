# Copy-Trade Decay — Amendment + Result

**Executes `2026-09-05-copy-trade-decay-prereg.md` AS AMENDED 2026-09-10.**
Two commits, in order, git history proves it:

| # | what | commit |
|---|---|---|
| 1 | **amendment alone** — no result in the tree | trading-swarm **`7b9e1e7`** |
| 2 | **result** — script `scripts/copy_trade_decay_diagnostic.py`, artifact `data/characterizations/copy_trade_decay_20260910T191052Z.json`, this doc | first-repo `c9619a4` + trading-swarm `<this commit>` |

The pre-registration is authoritative; where the run and the amended
document differed, the document won. Tags: **[V]** verified against a
cited file/query, **[I]** a judgment call.

**No verdict on what to do next — that is Oscar's.**

---

## Part 1 — the amendment (committed alone, `7b9e1e7`)

### Why it was needed

The pre-registration pinned its viability bar (§2, §6) to the
**cohort-minus-placebo GAP**. That was set when the live thesis was
"presplit-edge-selected traders outperform a matched placebo." Since
then:

- **N=0 gap not demonstrated** — `2026-09-05-n0-gap-check.md` (`7aa3fe5`):
  paired N=0 gap **−0.0072**, CI **[−0.0570, +0.0435]**, straddling zero,
  point estimate now negative. **[V]**
- **Presplit-edge selector falsified** — `2026-09-05-directional-skill-result.md`
  Outcome 2 "in its strongest form": placebo shows *more*
  directional-skill-like signal than the cohort. **[V]**
- **Directional selector shows no edge advantage over a matched
  placebo** (2026-09-06 exploratory custody figures). **[V]**

A gap-pinned bar makes the measurement permanently unrunnable — which is
why it never ran, despite `86a7b4e` §2 naming it THE DECISIVE QUESTION
and sequencing it first. The question the project now needs — **does any
measurable edge survive being copied?** — is a property of post-entry
price movement and needs no selector.

### What the amendment fixed (blind — no decay curve existed at write time)

- **A. Population** → primary is the **broad PIT-legal classifiable
  pool** (≥ M_CHOSEN=10 pre-split resolved geo/elec positions in the
  canonical `backtest_window_sql` set, `tape_end < T_SPLIT`), re-derived
  at run time. Cohort/placebo kept as **secondary**, reported for
  **shape** (decay is relative — level is contaminated, shape less so).
- **B. Viability bar** → off the gap, onto the broad-pool `edge(N)`
  curve vs **fixed per-category cost floors** (MASTER_HANDOVER_2026-08-15
  §5): geopolitics **0.0005–0.010** (fee-free), elections
  **0.0056–0.020** (4% fee), blended **0.02** (top of elections' range).
  Checked at **N=15min** (the architectural cadence) and every N beyond;
  per-category curves required.
- **C. N ladder** → **15 points**, minutes
  `1, 2, 5, 10, 15, 30, 60, 120, 240, 480, 960, 1440, 2880, 5760, 11520`
  (§3's 12 + three sub-floor points, because the decisive region is
  minutes not days).
- **D. N=0 gate** → **replaced** with an INTERNAL consistency gate: at
  N=0 the harness must reproduce a direct `measure_oos` computation on
  the same positions, **|Δ| ≤ 1e-9** on `point_gap`/`ci_lo`/`ci_hi` and
  **exact** `n_positions`/`n_pairs`/`n_traders`, per population. (The old
  gate — agree with a frozen Track 2 figure — tests substrate stability,
  not harness correctness; the substrate has moved 3,032 → 3,795 → and
  again after the 2026-09-09 drain.)
- **E. Price lookup** → reaffirms §1 ("next trade at or after
  `entry_ts + N`", single trade, own-trader trades included); adds the
  explicit **source: `trades.price`, the executed trade tape**;
  `price_at()`/CLOB explicitly not used (quote not a fill; one HTTP call
  per (position,N) infeasible; 73.1% cross-source agreement).
- **F. Thin/missing** → reaffirms §5a (carry forward) / §5b (exclude
  per-rung when `tape_end < entry+N`); adds a hard per-rung surviving-n
  requirement and a **THIN flag** at `n_pairs < max(30, 5% of the
  population's N=0 pair count)`; uncomputable rungs named, never dropped.
- **G. Self-inflicted decay** → stated, **not corrected**; the curve is
  a size-one best case and is size-dependent.
- **H. Outcomes** → named: **SURVIVES-ABOVE-FLOOR / SURVIVES-BELOW-FLOOR
  / COLLAPSES-BEFORE-CADENCE / TOO-THIN-AT-DECISIVE-N** + **N=0-GATE-FAILS**;
  collapse is mated to mooting the canonical design's components 2/3 and
  Phase 2. Re-running with different parameters after a disappointing
  curve is not an acceptable resolution.
- **I. Cannot establish** → selector validity, canonical design
  components 2/3, sufficiency for viability, existence of a
  slower-decaying selectable subpopulation.

### HARD GATE

**Every item A–I was fixable without reference to any decay result. No
STOP.** The amendment committed alone (`7b9e1e7`, 452 insertions, 0
deletions — original text preserved, pointers at §§1–8, dated amendment
appended). No decay computation was performed before that commit.

---

## Part 2 — the run

Script: `scripts/copy_trade_decay_diagnostic.py` (first-repo, committed
with this result). `seed=42`, `reps=1500`, `cap5`,
`T_SPLIT=2026-04-01 00:00:00` — reuses `measure_oos` /
`weighted_pair_table` / `weighted_two_way_gap_bootstrap` and
`directional_skill_pit_legal_pool`'s loaders unmodified.
Artifact: `data/characterizations/copy_trade_decay_20260910T191052Z.json`.
`--selfcheck` PASSED (edge identity 0 mismatches; N=0 `point_gap`/`n`
identity vs `measure_oos` OK).

### 2.1 — N=0 internal consistency gate (reported FIRST, per the prompt)

**PASS for all three populations, exactly.**

| population | harness N=0 point_gap | direct `measure_oos` | Δ (point_gap, ci_lo, ci_hi, n_pos, n_pairs, n_traders) |
|---|---|---|---|
| broad PIT-legal pool | 0.01207960227790117 | 0.01207960227790117 | all **0.0** |
| cohort (Track 2 frozen) | 0.023044072741755295 | 0.023044072741755295 | all **0.0** |
| placebo (Track 2 frozen) | 0.028012712074971247 | 0.028012712074971247 | all **0.0** |

The harness at N=0 is bit-identical to the canonical path. Downstream
`N>0` points are trustworthy. **No STOP.**

**Stop-condition check:** `metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` —
**unchanged**, before and after the run.

### 2.2 — broad PIT-legal pool (PRIMARY)

Pool: **5,907 traders** clear ≥10 pre-split resolved geo/elec positions
(2026-09-06 was 5,732; **+175** post-drain). Of these, **3,207** have ≥1
OOS geo/elec position — **36,121 OOS positions, 1,797 markets**.

Blended curve (`edge(N) = weighted_mean(won) − weighted_mean(substituted_price)`,
cap5, two-way clustered bootstrap CI):

| N | edge(N) | 95% CI | n_pairs | n_pos | excl (tape_end) | realised delay median | THIN |
|---|---|---|---|---|---|---|---|
| **0** | **+0.01208** | [−0.00168, +0.02645] | 19,922 | 36,121 | — | 0 | — |
| 1 min | +0.03140 | [+0.0103, +0.0523] | 19,568 | 35,607 | 514 | 14.3 min | no |
| 2 min | +0.03243 | [+0.0113, +0.0530] | 19,558 | 35,584 | 537 | 16.4 min | no |
| 5 min | +0.03264 | [+0.0095, +0.0543] | 19,539 | 35,542 | 579 | 20.9 min | no |
| 10 min | +0.03349 | [+0.0115, +0.0552] | 19,517 | 35,504 | 617 | 27.0 min | no |
| **15 min** | **+0.03434** | **[+0.0137, +0.0562]** | 19,496 | 35,468 | 653 | 32.7 min | no |
| 30 min | +0.03705 | [+0.0144, +0.0587] | 19,445 | 35,372 | 749 | 49.5 min | no |
| 60 min | +0.03700 | [+0.0147, +0.0588] | 19,348 | 35,157 | 964 | 81.4 min | no |
| 120 min | +0.03363 | [+0.0112, +0.0578] | 19,145 | 34,764 | 1,357 | 143 min | no |
| 240 min | +0.03187 | [+0.0087, +0.0559] | 18,792 | 34,044 | 2,077 | 268 min | no |
| 480 min (8 h) | +0.02381 | [+0.0013, +0.0465] | 18,378 | 33,224 | 2,897 | 512 min | no |
| 960 min | +0.02617 | [+0.0013, +0.0511] | 17,708 | 31,888 | 4,233 | 993 min | no |
| 1440 min (1 d) | +0.02899 | [+0.0049, +0.0539] | 17,208 | 30,955 | 5,166 | 1,473 min | no |
| 2880 min (2 d) | +0.02373 | [−0.0020, +0.0506] | 15,851 | 28,171 | 7,950 | 2,919 min | no |
| 5760 min (4 d) | +0.01919 | [−0.0100, +0.0453] | 13,533 | 23,572 | 12,549 | 5,809 min | no |
| 11520 min (8 d) | −0.00062 | [−0.0317, +0.0332] | 11,041 | 18,721 | 17,400 | 11,580 min | no |

**What the curve shows.** At N=0 the pool's own mean edge is **+0.012
with a CI that straddles zero** ([−0.0017, +0.0265]). The point estimate
then **rises** from N=0 (+0.012) to a plateau **+0.033–0.037 across
N=1min–60min** — and the CI now *excludes* zero — is still **+0.034 at
N=15min, CI [+0.0137, +0.0562]**, then declines
gradually: +0.032 (4 h), +0.024 (8 h), holding ~+0.024–0.029 through 1
day, then decays to +0.024 (2 d), +0.019 (4 d), and **reaches zero
(−0.0006) at 8 days**. The **lower CI bound stays above zero from N=1min
through N=1440min (1 day)** and first straddles zero at N=2 days. **The
edge does not collapse before the 15-minute monitoring cadence — it
survives it with room to spare.**

No rung was THIN or UNCOMPUTABLE.

### 2.3 — per-category curves vs the fixed cost floors (item B)

**Geopolitics** — 25,891 OOS positions; fixed floor **0.0005–0.010**
(fee-free). `cost_floor()` cross-check on this pool: lo 0.0005, hi 0.010.

| N | edge(N) | 95% CI | n_pairs | realised delay median |
|---|---|---|---|---|
| 0 | +0.01043 | — | 13,548 | — |
| 1 min | +0.02790 | [+0.0050, +0.0531] | 13,385 | 12.1 min |
| **15 min** | **+0.03240** | **[+0.0047, +0.0591]** | 13,349 | 30.0 min |
| 30 min | +0.03710 | [+0.0129, +0.0631] | 13,322 | 46.5 min |
| 60 min | +0.03612 | [+0.0091, +0.0619] | 13,259 | 78 min |
| 240 min | +0.02960 | [+0.0025, +0.0553] | 12,898 | 262 min |
| 480 min | +0.01917 | [−0.0082, +0.0467] | 12,632 | 506 min |
| 1440 min | +0.02395 | [−0.0068, +0.0516] | 11,797 | 1,466 min |
| 8 d | −0.01527 | [−0.0517, +0.0236] | 6,734 | 11,572 min |

Geopolitics **clears its fee-free floor lower bound (0.0005) on the
lower CI from N=15min out to N=240min (4 h)** — lower CI +0.0047 at
15min. From N=480min (8 h) the lower CI crosses zero; the point estimate
decays to zero by ~4 d and negative by 8 d. It does **not** clear the
floor *upper* bound (0.010) on the lower CI at any rung, though the
point estimate does through ~4 h.

**Elections** — 10,230 OOS positions; fixed floor **0.0056–0.020** (4%
`feeRate`, fee 0.0097 at median price 0.59). `cost_floor()` cross-check
on this pool: lo 0.0015, hi 0.0195 (its lo is below the handover's fixed
0.0056 because it takes the min-over-quartiles fee; **the handover
figure is the pre-registered bar**).

| N | edge(N) | 95% CI | n_pairs | realised delay median |
|---|---|---|---|---|
| 0 | +0.01616 | — | 6,374 | — |
| 1 min | +0.04022 | [+0.0036, +0.0758] | 6,183 | 22.2 min |
| **15 min** | **+0.03926** | **[+0.0011, +0.0774]** | 6,147 | 43.5 min |
| 60 min | +0.03924 | [+0.0006, +0.0757] | 6,089 | 96 min |
| 240 min | +0.03763 | [−0.0031, +0.0796] | 5,894 | 296 min |
| 1440 min | +0.04185 | [+0.0044, +0.0818] | 5,411 | 1,506 min |
| 2880 min | +0.03384 | [−0.0099, +0.0768] | 5,146 | 2,957 min |
| 8 d | +0.02550 | [−0.0290, +0.0740] | 4,307 | 11,601 min |

Elections has a **strikingly flat, persistently positive point
estimate** — **+0.037 to +0.042 across the entire ladder**, still
**+0.026 at 8 days** (it barely decays). But its **lower CI bound never
clears the 0.0056 election cost floor** at N=15min or beyond (the
tightest lower bounds sit around +0.001 to +0.004, and several rungs —
30min, 120min, 240min, and 2 d+ — straddle zero outright). The edge
appears **real but not demonstrably tradeable net of the 4% election
fee** at the confidence this measurement provides.

### 2.4 — cohort and placebo (SECONDARY — shape only, level contaminated)

**Cohort (Track 2 frozen, 169 traders):** 3,881 OOS positions, 142
surviving traders.

| N | edge(N) | 95% CI |
|---|---|---|
| 0 | **+0.02304** | — |
| 1 min | **−0.02183** | [−0.0893, +0.0419] |
| 15 min | −0.02544 | [−0.0914, +0.0403] |
| 60 min | −0.00999 | [−0.0771, +0.0620] |
| 480 min | −0.05297 | [−0.1290, +0.0163] |
| 8 d | −0.07314 | [−0.1596, +0.0104] |

**Shape: immediate collapse-and-inversion.** The cohort's own positive
N=0 edge (+0.023) goes **negative by the first observable rung** (~13 min
realised) and stays negative across the entire ladder (−0.010 to −0.073).
Every CI straddles zero. Consistent with the cohort's N=0 edge being
timing/execution-located and **not inheritable by a later entrant** — but
this is the contaminated-level secondary population and nothing here is
CI-distinguishable from zero.

**Placebo (Track 2 frozen, 169 traders):** 2,727 OOS positions, 118
surviving traders.

| N | edge(N) | 95% CI |
|---|---|---|
| 0 | +0.02801 | — |
| 1 min | **+0.06978** | [+0.0024, +0.1347] |
| 15 min | +0.07372 | [−0.0011, +0.1428] |
| 60 min | +0.07786 | [−0.0042, +0.1543] |
| 1440 min | +0.05395 | [−0.0291, +0.1400] |
| 8 d | −0.03497 | [−0.1436, +0.0789] |

**Shape: jump-up then slow decay** — like the broad pool but larger and
noisier. Lower CI above zero only at N=1–10min; straddles zero from
15min on.

**Cohort and placebo move in opposite directions from N=0 to the first
rung** (cohort −0.045, placebo +0.042). The cohort curve's shape is
genuinely different from the broad pool's — but read it only as shape,
per the amendment.

### 2.5 — the sub-15-minute region is not observable on this tape

The amendment added N = 1, 2, 5, 10 min specifically to resolve the fast
initial decay. **Those rungs do not sample those delays.** Median
*realised* delay at nominal N=1min: broad pool **14.3 min**, geopolitics
12.1 min, elections 22.2 min, cohort 12.6 min, placebo 20 min. The trade
tape has no trades within ~12–22 min of a typical entry, so every rung
from N=1min to N=15min is effectively sampling the ~12–33 min window;
nominal and realised N converge only around N=15–30min. **How the edge
behaves in the first few minutes after an informed entry cannot be
measured on this data.**

### 2.6 — §5c volume-composition disclosure (recorded, not corrected)

The surviving subsample drifts lower-volume at long N: mean OOS
positions per surviving trader falls from **11.1** (N=1min, base 11.26)
to **6.6** (N=8d); trader retention 0.999 → 0.888; excluded fraction
0.014 → 0.482. So the long end of the broad-pool curve describes a
somewhat lower-volume slice than the short end. Flagged per §5c; **not
corrected**.

---

## The named outcome (item H)

**Not a single clean label — it splits by category, and the fast region
is unmeasurable.** Stated exactly:

- **The primary (broad PIT-legal) population does NOT show
  COLLAPSES-BEFORE-CADENCE.** `edge(N)` is **+0.034 with a
  zero-excluding CI [+0.0137, +0.0562] at N=15min**, and stays
  CI-positive out to ~1 day.
- **Geopolitics: SURVIVES-ABOVE-FLOOR** at the 15-minute cadence — lower
  CI +0.0047 clears the fee-free floor lower bound 0.0005 — and holds
  that out to ~4 hours. Beyond ~8 hours it becomes **TOO-THIN /
  inconclusive** (lower CI crosses zero) and the point estimate decays
  to zero by ~4 days.
- **Elections: SURVIVES-BELOW-FLOOR** — the point estimate is a stable,
  barely-decaying **+0.037–0.042** all the way to 8 days, but the lower
  CI never clears the **0.0056** election cost floor at or beyond
  N=15min. Real, not demonstrably tradeable net of the 4% fee at this
  measurement's confidence.
- Against the **blended 0.02 bar**, the broad-pool lower CI does not
  clear at N=15min (0.0137 < 0.02); the point estimate (0.034) does.
- **The sub-15-minute shape is TOO-THIN-AT-DECISIVE-N by construction** —
  the tape has no trades that close to entries (§2.5).

Per the standing rule (amendment H, §7 outcome 4): this is reported as
it came out. No parameter was changed and no further analysis was run to
move it toward any outcome.

---

## Observation log

*UNREGISTERED, UNTESTED. Changes nothing about the pre-registered
outcome. No computation was added to develop these — each is a read of
the numbers the pre-registered run already produced.*

1. **Elections decays far more slowly than geopolitics, beyond the fee
   difference.** Geopolitics `edge(N)` falls from +0.037 (peak) to zero
   by ~4 days and negative by 8; elections holds **+0.037–0.042 flat to
   8 days**. The fee gap explains the *floor*, not the *shape*. Why it
   might matter to "identify profitable traders, rate them continuously":
   if election-market edge genuinely persists over days, a copy latency
   budget for elections could be hours-to-days rather than minutes — a
   different operating regime from geopolitics. **Pre-registered test
   that would settle it:** a category-stratified decay pre-registration
   with per-category CIs powered to distinguish "flat" from "slow
   decay" at the 2–8 day rungs (the current elections CIs are too wide
   at the long end to call it).

2. **The broad-pool curve *rises* from N=0 to N≈30–60min (+0.012 →
   +0.037), then decays.** A copier entering ~13–50 min after the
   original trader gets, on average, a *better* price than the trader
   paid. This is the opposite of "decay" over that segment. Why it
   might matter: it suggests the median informed entry in this pool is
   into short-term price *pressure* that partly reverts within the hour
   — i.e. the original traders are, on average, paying a small
   immediacy premium a patient copier avoids. **Pre-registered test:**
   split the ladder by whether the original entry was a maker or taker
   fill (`is_taker`, already on `trades`) — a taker-heavy subpopulation
   should show the rise; a maker-heavy one should not.

3. **Cohort vs placebo move in opposite directions at the first
   observable rung** (cohort −0.045, placebo +0.042 vs their own N=0).
   The cohort's positive N=0 edge is gone — inverted — within ~13 min;
   the placebo's is not. Read as shape only (levels contaminated), this
   is the single place in the run where the presplit-edge cohort looks
   *different* from a null population: its edge is the one that
   evaporates fastest under delay. Why it might matter: it is weak,
   CI-straddling evidence that whatever the presplit selection caught
   was **short-horizon and execution-located** — exactly the thing a
   copy system cannot inherit. **Pre-registered test:** the canonical
   design's component 2/3 (absolute / relative earliness) on the
   cohort vs a matched pool — if the cohort is *relatively* early
   (first-mover in its markets) but its copy-edge dies in minutes, the
   two together would localize the edge to execution timing.

4. **The long-N subsample is lower-volume-skewed** (§2.6: mean
   positions/trader 11.1 → 6.6 from N=1min to N=8d). The feasibility
   read already flagged that the highest-volume tercile has the
   thinnest nearby-trade density. So the 2–8 day rungs describe a
   lower-volume slice, and the high-volume traders — where the cohort
   concentrates — are underrepresented exactly where the curve is
   flattest. **Pre-registered test:** stratify the decay ladder by
   pre-split volume tercile with per-tercile CIs; a slower-decaying
   subpopulation, if one exists, would most plausibly be a
   volume/liquidity stratum.

*Watch-point not developed: whether decay differs by the trader's own
entry-to-resolution lag (early vs late entries) — the cohort's median
is 8.92 days with 53.8% beyond 8 days. Not computed here; it would be a
separate stratified pre-registration.*

---

## What was NOT determined

- **The sub-15-minute decay shape.** The trade tape has no trades within
  ~12–22 min of a typical entry (§2.5), so the four sub-floor rungs the
  amendment added do not sample sub-floor delays. How the edge behaves
  in the first minutes after an informed entry is unmeasurable on this
  data with this (trade-tape) price source.
- **Whether elections' edge genuinely persists over days or merely
  decays too slowly for these CIs to catch.** The elections long-N CIs
  ([−0.010, +0.077] at 8 d) are too wide to distinguish "flat" from
  "declining."
- **Whether the broad-pool edge clears a cost floor at all in a
  decision-relevant sense.** Geopolitics clears its fee-free floor lower
  bound on the lower CI only to ~4 h; elections never clears its
  fee-laden floor on the lower CI; neither clears the blended 0.02 bar
  on the lower CI. The point estimates are comfortably above the floors;
  the CIs are not.
- **Whether the cohort's immediate collapse-and-inversion is signal or
  noise.** Every cohort CI straddles zero; the shape is suggestive, not
  established. Its level is contaminated by construction and by the
  N=0 gap no longer being demonstrated.
- **Attribution of the N=0 → N=30min *rise*.** Observed, not explained.
- **Anything about size > 1.** Per amendment G, this is a size-one best
  case and is not corrected for self-inflicted decay.
- **Whether any of this supports or refutes a selector.** Per amendment
  I, the measurement is selector-free and cannot speak to it.

---

## Reproducibility

- **Script:** `scripts/copy_trade_decay_diagnostic.py` (first-repo,
  committed with this result). Reuses `measure_oos`,
  `weighted_pair_table`, `weighted_two_way_gap_bootstrap`, `cost_floor`,
  and `directional_skill_pit_legal_pool`'s
  `load_presplit_market_ids`/`load_presplit_positions` **unmodified** —
  new logic is only the price substitution, the 15-point N-loop, and the
  three-population wrapper. `--selfcheck` present, consistent with
  `trader_skill_metric_v2*` (edge identity + N=0-gate identity vs
  `measure_oos`). Read-only against production; the run wrote nothing to
  any `metric_v2f_*` or other production table.
- **Parameters (in the artifact):** `seed=42`, `reps=1500`,
  `weight_fn=cap5`, `T_SPLIT=2026-04-01 00:00:00`, `M_CHOSEN=10`,
  `gate_tolerance=1e-9`, `thin_abs=30`, `thin_frac=0.05`, the 15-point N
  ladder, the fixed per-category cost floors.
- **Durable artifact:**
  `data/characterizations/copy_trade_decay_20260910T191052Z.json` — per
  population and per category: `point_gap` + CI, `n_pairs`/`n_positions`/
  `n_traders`, per-rung realised-delay distribution, §5b exclusion
  counts/fractions, THIN flags, the §5c volume-composition disclosure,
  the N=0 gate deltas, `cost_floor()` cross-check, the broad-pool
  run-time size (5,907, +175 vs 09-06), the SQL predicates, and the
  `metric_v2f_oos_result` sha256 before/after.
- **`script_commit` in the artifact** is `4deb57c` — the HEAD at run
  time; the script itself lands in first-repo `c9619a4` (parent `4deb57c`).
  The artifact is otherwise fully self-describing.
- **Stop conditions — none tripped:** N=0 gate passed for all three
  populations (Δ = 0.0 exactly); `metric_v2f_oos_result` sha256
  `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
  unchanged before and after; no rung was uncomputable or dropped; every
  amended parameter applied as written.
- **Tests:** `run_tests.py` (not bare pytest) — **25 files, 25 passed,
  0 failed** (339,909 assertions). The decay script adds no test file
  and touches no existing module; the suite is unchanged and green.
