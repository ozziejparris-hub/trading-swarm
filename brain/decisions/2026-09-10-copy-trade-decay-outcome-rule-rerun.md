# Copy-Trade Decay — Outcome-Rule Amendment (2026-09-10b) + Re-Run

**Two commits, in order; git history proves it.**

| # | what | commit |
|---|---|---|
| 1 | **amendment alone** — no result in the tree | trading-swarm **`e8eca1c`** |
| 2 | **result** — `scripts/copy_trade_decay_diagnostic.py` (modified), artifact `data/characterizations/copy_trade_decay_20260910T200321Z.json`, this doc | first-repo `1f43424` + trading-swarm `<this commit>` |

The pre-registration is authoritative. The prior published run
(`copy_trade_decay_20260910T191052Z.json`, first-repo `c9619a4`, doc
`9732bc9`) **is not touched — it stands as computed.** This is a
separate, re-pre-registered re-run with the outcome rule fixed.

Tags: **[V]** verified this session (command/query shown), **[I]**
reasoned judgment.

**Headline:** with the price substitution corrected (opposite-outcome
trade price `q → 1 − q`), **the N=0→~30min *rise* in the 2026-09-10
published curve disappears**. The corrected broad-pool primary curve is
flat at N=0's level (~+0.012) through the 15-minute cadence, then
declines gently; at the decisive rung it is **+0.01233, CI
[−0.00186, +0.02410] — includes zero, not thin**. Primary and the
outcome-matched-only robustness curve agree (CIs overlap;
`material_disagreement = False`). **Named outcome:
COLLAPSES-BEFORE-CADENCE** — no demonstrable copy edge survives to the
architectural cadence under the correct substitution, on any of the
three populations. **No verdict on what to do next — Oscar's call.**

---

## Part 1 — the amendment (committed alone, `e8eca1c`)

BLIND: no corrected decay curve, at any `N`, on any population, under
either construction, existed when it was written. The 2026-09-10
published figures were recorded as the pre-existing result they are, not
as a target.

Appended to `2026-09-05-copy-trade-decay-prereg.md` as "Amendment
2026-09-10b" (dated-section convention, matching the "-b" pattern of
`2026-09-06-directional-skill-persistence-prereg.md`); pointers added at
§1 and at Amendment 2026-09-10 item E; **256 insertions, 0 deletions** —
nothing earlier deleted or rewritten.

### Why

§1 and Amendment 2026-09-10 item E specify "the **next trade in that
market** … **from any trader**" — addressing *trader*, never *outcome*.
In a binary market `trades.price = P(the trade's own outcome)`
(`P(Yes) + P(No) ≈ 1.0`), so "the next trade's price" is ambiguous. The
2026-09-10 run took whichever outcome traded first and used its price
unconverted; the 2026-09-10 verification (`3c22b0c`) found **37.58%** of
N=15min substitutions were opposite-outcome, at `≈ 1 − p`. Same shape as
the `geo_elo` docstring embedding the same error as its code: the spec
inferred a price field's meaning from context.

### What was fixed

- **A. Outcome rule — CONVERSION is primary.** Opposite-outcome
  substituted trade price `q` → **`1 − q`** as the implied held-outcome
  price; same-outcome used directly. Justified from the verification's
  own Part 1: paired opposite-outcome trades within 10 s sum to median
  **1.00000**, IQR **[0.999, 1.001]**, 97.9% within [0.98, 1.02]
  (n = 45,984). Cost stated: complementarity is empirical, not exact,
  loosening to 92.0% within [0.98, 1.02] at 300 s. Expected
  per-substitution error **≈ ±0.001 (IQR) to ±0.02 (95%)**, ≈ mean-zero
  (median deviation 0.00000), so expected aggregate bias is order
  **1–2 ×10⁻³** — an order of magnitude below the +0.018 inflation that
  *unconverted* opposite-outcome substitution produced at N=15min.
- **B. Robustness check — outcome-matched-only, secondary, every rung.**
  Discard every opposite-outcome substitution. Secondary because
  discarding ~37% is a non-random selection (which outcome trades next
  correlates with market conditions), whereas conversion imports only
  the small licensed measurement error.
- **C. Material disagreement — fixed now:** the primary and secondary
  **95% bootstrap CIs at N=15min on the broad pool do not overlap**.
  CI-overlap chosen over a point-estimate threshold because the CI is
  the harness's own statement of what it can resolve. Non-overlap →
  named outcome **PRIMARY-AND-ROBUSTNESS-DISAGREE**, both curves
  reported, not resolved by picking one.
- **D. Decisive rung N = 15 min**; per-category cost floors **unchanged**
  (geopolitics 0.0005–0.010, elections 0.0056–0.020, blended 0.02).
- **E. Sub-15-minute region — permanent trade-tape limitation**, not a
  parameter: median realised delay at nominal N=1min is 12–22 min; no
  substitution rule and no finer rung can fix it.
- **F. N=0 gate — unchanged, re-run as-is** (uses
  `positions.entry_avg_price`; verification confirmed 0.00% outcome
  mismatch on 4,000 sampled positions).
- **G. Outcomes — retain the 2026-09-10 named set + add
  PRIMARY-AND-ROBUSTNESS-DISAGREE.** Standing rule restated: **this
  amendment is the last word on the substitution rule.**

### HARD GATE

**Every item was fixable without reference to a corrected curve. No
STOP.** No computation was performed before `e8eca1c`.

---

## Part 2 — the re-run

Script `scripts/copy_trade_decay_diagnostic.py`, modified per the
amendment to (i) load `p.outcome` and the substituted trade's `outcome`;
(ii) apply conversion as the primary curve; (iii) compute the
outcome-matched-only curve at every rung; (iv) record opposite-outcome
share per rung. **Unchanged:** N=0 gate, N ladder, cost floors,
cohort/placebo definitions, `seed=42`, `reps=1500`, `cap5`, `T_SPLIT`.
Artifact: `data/characterizations/copy_trade_decay_20260910T200321Z.json`.

**`--selfcheck` PASSED:** edge-identity 0 mismatches; N=0 identity vs
`measure_oos` OK; **conversion-rule check — 625 substitutions verified,
0 mismatches** (`1 − q` applied iff outcome differs, `q` used iff it
matches).

### 2.1 — N=0 gate (reported first)

**PASS, exactly, all three populations** — Δ = 0.0 on
`point_gap`/`ci_lo`/`ci_hi`/`n_positions`/`n_pairs`/`n_traders`.
`metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
**unchanged** before and after. **No STOP.**

Conversion coverage: `outcome` was available for **every** substituted
trade and every held position (0 unavailable). Non-convertible
substitutions (opposite-outcome where one side is a non-binary label —
named candidate / Up-Down / Over-Under) were **1–2 per broad-pool rung**
(max 2; the broad pool has 2 non-binary held positions of 36,121);
excluded from that rung and counted. Not a stop condition.

### 2.2 — broad PIT-legal pool (PRIMARY = convert), all 15 rungs

5,907 traders (2026-09-06: 5,732; +175). 36,121 OOS positions, 3,207
traders, 1,797 markets. **No rung THIN, none UNCOMPUTABLE.**

| N | edge(N) | 95% CI | n_pairs | n_pos | opp-outcome share | realised delay median |
|---|---|---|---|---|---|---|
| **0** | **+0.01208** | [−0.00168, +0.02645] | 19,922 | 36,121 | — | 0 |
| 1 min | +0.01409 | **[+0.00067, +0.02731]** | 19,567 | — | 0.346 | 14.3 min |
| 2 min | +0.01389 | **[+0.00050, +0.02716]** | 19,557 | — | 0.353 | 16.4 min |
| 5 min | +0.01315 | [−0.00080, +0.02695] | 19,538 | — | 0.362 | 20.9 min |
| 10 min | +0.01266 | [−0.00046, +0.02680] | 19,516 | — | 0.369 | 27.0 min |
| **15 min** | **+0.01233** | **[−0.00186, +0.02410]** | 19,495 | 35,468 | 0.376 | 32.7 min |
| 30 min | +0.01202 | [−0.00209, +0.02580] | 19,444 | — | 0.384 | 49.5 min |
| 60 min | +0.01129 | [−0.00254, +0.02474] | 19,346 | — | 0.389 | 81 min |
| 120 min | +0.00963 | [−0.00482, +0.02354] | 19,143 | — | 0.392 | 143 min |
| 240 min | +0.00825 | [−0.00590, +0.02192] | 18,790 | — | 0.399 | 268 min |
| 480 min | +0.00682 | [−0.00731, +0.01929] | 18,376 | — | 0.402 | 512 min |
| 960 min | +0.00738 | [−0.00643, +0.02040] | 17,707 | — | 0.405 | 993 min |
| 1440 min (1 d) | +0.00785 | [−0.00603, +0.02173] | 17,207 | — | 0.398 | 1,473 min |
| 2880 min (2 d) | +0.00572 | [−0.00916, +0.01907] | 15,850 | — | 0.407 | 2,919 min |
| 5760 min (4 d) | +0.00395 | [−0.01194, +0.01763] | 13,532 | — | 0.396 | 5,809 min |
| 11520 min (8 d) | +0.00854 | [−0.00501, +0.02226] | 11,041 | — | 0.394 | 11,580 min |

**The rise is gone.** N=0 → N=15min: **+0.01208 → +0.01233** — flat.
The point estimate then declines slowly and shallowly to ~+0.004–0.009
past a day. **Only N=1min and N=2min have a CI that excludes zero, and
only barely** (lower bounds +0.00067, +0.00050); every rung from N=5min
onward — including the decisive N=15min — has a CI that **includes
zero**. The opposite-outcome share rises from 0.346 (N=1min) to ~0.40
(long N), so conversion's exposure is real and grows with `N`.

### 2.3 — broad pool (SECONDARY = outcome-matched-only), all 15 rungs

| N | edge(N) | 95% CI | n_pairs |
|---|---|---|---|
| 1 min | +0.01491 | [−0.00212, +0.03212] | 14,297 |
| 5 min | +0.01408 | [−0.00239, +0.03173] | 14,099 |
| **15 min** | **+0.01592** | **[−0.00130, +0.03317]** | 13,853 |
| 30 min | +0.01318 | [−0.00590, +0.03220] | 13,697 |
| 60 min | +0.01347 | [−0.00492, +0.03183] | 13,575 |
| 120 min | +0.01213 | [−0.00728, +0.03089] | 13,330 |
| 240 min | +0.01082 | [−0.00737, +0.02967] | 12,980 |
| 480 min | +0.00917 | [−0.01089, +0.02830] | 12,577 |
| 960 min | +0.00856 | [−0.01075, +0.02652] | 12,111 |
| 1440 min | +0.00866 | [−0.00877, +0.02801] | 11,818 |
| 2880 min | +0.00936 | [−0.01112, +0.02781] | 10,799 |
| 5760 min | +0.00446 | [−0.01505, +0.02121] | 9,344 |
| 11520 min | +0.00773 | [−0.01226, +0.02500] | 7,569 |

(N=1/2/10min: +0.01491 / +0.01427 / +0.01454.) **Every matched-only rung
CI includes zero.** Same flat-then-gentle-decline shape as the primary,
one notch higher in level, wider CIs (fewer pairs). No rung THIN.

### 2.4 — item C: primary vs secondary at the decisive rung

| N=15min, broad pool | edge(N) | 95% CI | n_pairs |
|---|---|---|---|
| **primary (convert)** | **+0.01233** | **[−0.00186, +0.02410]** | 19,495 |
| **secondary (matched-only)** | **+0.01592** | **[−0.00130, +0.03317]** | 13,853 |

**CIs overlap → `material_disagreement = False`.** The two constructions
agree within the harness's own uncertainty. The primary (conversion)
curve is the result; the matched-only curve confirms it. **Outcome
PRIMARY-AND-ROBUSTNESS-DISAGREE does not obtain.**

### 2.5 — per-category, PRIMARY (convert), vs the fixed floors

**Geopolitics** (25,891 positions; floor 0.0005–0.010, fee-free):

| N | edge(N) | 95% CI | n_pairs | opp share |
|---|---|---|---|---|
| 1 min | +0.01263 | [−0.00210, +0.02796] | 13,385 | 0.381 |
| **15 min** | **+0.01077** | **[−0.00468, +0.02602]** | 13,349 | 0.416 |
| 60 min | +0.00956 | [−0.00536, +0.02406] | 13,259 | 0.427 |
| 240 min | +0.00578 | [−0.01147, +0.02070] | 12,898 | 0.442 |
| 1440 min | +0.00561 | [−0.00999, +0.01977] | 11,797 | 0.439 |
| 8 d | +0.01075 | [−0.00394, +0.02590] | 6,734 | 0.450 |

**No geopolitics rung's CI excludes zero, under either construction**
(matched N=15min +0.01536 [−0.00358, +0.03355]). The N=15min point
estimate (+0.011) sits at the floor's *upper* bound (0.010) but its
lower CI is negative → **does not clear the fee-free floor**.

**Elections** (10,230 positions; floor 0.0056–0.020, 4% fee):

| N | edge(N) | 95% CI | n_pairs | opp share |
|---|---|---|---|---|
| 1 min | +0.01777 | [−0.01022, +0.04622] | 6,182 | 0.253 |
| **15 min** | **+0.01629** | **[−0.01230, +0.04519]** | 6,146 | 0.272 |
| 60 min | +0.01566 | [−0.01247, +0.04461] | 6,087 | 0.288 |
| 240 min | +0.01456 | [−0.01464, +0.04354] | 5,892 | 0.287 |
| 1440 min | +0.01357 | [−0.01383, +0.04120] | 5,410 | 0.289 |
| 8 d | +0.00461 | [−0.02529, +0.03249] | 4,307 | 0.292 |

Elections keeps its **flat point-estimate shape** (+0.014–0.018 to
N=1440min, vs geo's decline) — the 2026-09-10 observation survives
correction as a point-estimate feature. But **no elections rung's CI
excludes zero, under either construction** (matched N=15min +0.01710
[−0.02064, +0.05400]); the N=15min point estimate (+0.016) sits between
the floor bounds and its lower CI is negative → **does not clear the
election floor**. Opposite-outcome share is notably lower for elections
(~0.26) than geopolitics (~0.42).

### 2.6 — cohort and placebo (SECONDARY populations — shape only)

**Cohort** (Track 2 frozen, 169 traders; 3,881 OOS positions), PRIMARY
(convert):

| N | edge(N) | 95% CI |
|---|---|---|
| 0 | +0.02304 | — |
| 1 min | +0.02042 | [−0.01069, +0.05761] |
| 15 min | +0.01787 | [−0.01382, +0.05413] |
| 240 min | +0.01448 | [−0.01637, +0.04758] |
| 8 d | +0.00823 | [−0.02152, +0.03744] |

**The 2026-09-10 "immediate collapse-and-inversion" is gone.** Under
conversion the cohort does **not** invert — it decays **gently and
monotonically** from +0.023 (N=0) toward ~+0.010, CI straddling zero at
every rung. Matched-only: same shape (N=15min +0.01968 [−0.01775,
+0.05942]).

**Placebo** (Track 2 frozen, 169 traders; 2,727 OOS), PRIMARY (convert):

| N | edge(N) | 95% CI |
|---|---|---|
| 0 | +0.02801 | — |
| 1 min | +0.02835 | [−0.00752, +0.06517] |
| 15 min | +0.02634 | [−0.00922, +0.06772] |
| 1440 min | +0.01304 | [−0.02434, +0.05358] |
| 8 d | +0.00492 | [−0.03434, +0.04383] |

**The 2026-09-10 "jump to +0.070 at N=1min" is gone.** Under conversion
the placebo is **flat at ~+0.028 then decays gently**; CI straddles zero
at every rung. Matched-only: same (N=15min +0.02468 [−0.01871,
+0.06697]).

Both secondary populations now show the **same qualitative shape as the
broad pool and as each other** — flat/gentle monotone decline, no jump,
no inversion, no CI-positive rung past N=0. The 2026-09-10 cohort/placebo
shape divergence was an artifact of unconverted opposite-outcome
substitution.

---

## The named outcome (item G)

**COLLAPSES-BEFORE-CADENCE.**

At the decisive rung — N=15min, broad pool, primary (convert) — the
edge is **+0.01233, CI [−0.00186, +0.02410]**: indistinguishable from
zero, **not thin** (19,495 pairs). The primary and outcome-matched-only
curves agree (CIs overlap; not PRIMARY-AND-ROBUSTNESS-DISAGREE). No rung
on any of the three populations, under either construction, has a
CI that excludes zero at or beyond N=15min; the corrected curve is flat
at N=0's own level (whose CI *also* straddles zero) through the cadence
and declines gently thereafter.

Stated precisely: **the apparent rise-and-survival in the 2026-09-10
published curve was the unconverted-opposite-outcome artifact. With the
substitution corrected, there is no demonstrable copy edge at the
architectural cadence — nor at N=0, nor at any delay.**

Per this outcome's standing consequence (carried from Amendment
2026-09-10 item H): this **moots the canonical metric design's
execution-dimension components 2 and 3 as capturability questions**, and
**bears directly on Phase 2 as the primary experiment** — there is
nothing an outside copier could inherit by the time a real copy could
physically occur.

Re-running with a different substitution rule after this is **not** an
acceptable resolution (Amendment 2026-09-10b item G — this amendment is
the last word on the rule).

---

## Observation log

*UNREGISTERED, UNTESTED. Changes nothing about the pre-registered
outcome. Each entry is a read of numbers the pre-registered run already
produced — no extra computation.*

**The four 2026-09-10 watch-points, re-checked against the corrected
curves:**

1. **Elections decays far more slowly than geopolitics, beyond the fee
   difference.** *Survives correction — as a point-estimate feature
   only.* Under conversion, elections' point estimate is flat
   (+0.014–0.018 to N=1440min) while geopolitics declines (+0.013 →
   +0.004 by N=480min). But every rung of both, under both
   constructions, has a CI including zero, so this is a shape
   observation with no statistical support. Pre-registered test that
   would settle it: a category-stratified decay pre-registration
   powered to distinguish "flat" from "declining" at the 1–8 day rungs.

2. **The N=0→30min *rise* as evidence of an "immediacy premium a
   patient copier avoids."** **RETRACTED. The rise was the artifact.**
   Under conversion the broad-pool curve is flat from N=0 to N=30min
   (+0.01208 → +0.01202). There is no immediacy premium visible in the
   corrected data; the 2026-09-10 observation was built entirely on the
   unconverted-complement inflation and does not stand. (The
   maker/taker split the 2026-09-10 log proposed as a test for it is
   moot — there is no rise to explain.)

3. **Cohort and placebo move in opposite directions at the first
   observable rung.** **RETRACTED. Both were artifacts.** Under
   conversion the cohort does not invert (+0.020 at N=1min vs +0.023 at
   N=0) and the placebo does not jump (+0.028 at N=1min vs +0.028 at
   N=0); both decline gently and in the same direction. The "one place
   the presplit-edge cohort looked different from a null" is gone —
   corrected, the cohort curve is a slightly-lower-level version of the
   placebo curve, both flat-to-declining, both CI-straddling-zero
   throughout.

4. **The long-N subsample is lower-volume-skewed** (§5c; §5b exclusions
   remove markets that resolved soon after entry). *Unchanged — it is a
   survivorship property of the tape-end exclusions, independent of the
   substitution rule.* Broad-pool excluded fraction still rises 0.014
   (N=1min) → 0.48 (N=8d). Pre-registered test unchanged: stratify the
   ladder by pre-split volume tercile with per-tercile CIs.

*No new watch-point developed.*

---

## What was NOT determined

- **Whether the corrected flat ~+0.012 broad-pool level is a real (tiny)
  edge or N=0 sampling noise.** Its CI includes zero at N=0 and at every
  rung ≥ N=5min. The measurement cannot say it is non-zero.
- **The sub-15-minute shape.** Permanently unmeasurable on the trade
  tape (Amendment 2026-09-10b item E): median realised delay at nominal
  N=1min is 12–33 min across populations/categories. The 1/2/5/10min
  rungs' nominal labels are not delays.
- **Per-category significance.** No per-category rung, under either
  construction, has a CI excluding zero — so geo-vs-elections shape
  differences (obs. 1) are point-estimate only.
- **Whether "convert" or "outcome-matched-only" is the truer copy
  construction.** The amendment makes convert primary on the
  licensed-inference argument (item A/B); both are reported and here
  they agree (item C), so the question is not forced.
- **Why elections' opposite-outcome share (~0.26) is lower than
  geopolitics' (~0.42).** Observed, not chased.
- **Anything about copy size > 1.** Unchanged limitation (Amendment
  2026-09-10 G / §8a): this is a size-one best case and is not
  corrected for self-inflicted decay.
- **Whether a slower-decaying, prospectively selectable subpopulation
  exists.** Not a test this pre-registration runs (Amendment 2026-09-10
  item I).

---

## Reproducibility

- **Script:** `scripts/copy_trade_decay_diagnostic.py` (first-repo,
  committed with this result). Diff from the 2026-09-10 version: loads
  `p.outcome` and the substituted trade's `outcome`; `substitute_price_at_N`
  now takes a `construction` arg (`"convert"` / `"matched"`) and applies
  `1 − q` for opposite-outcome, `q` for same-outcome, excludes
  non-convertible (opposite + non-binary) with a count; `run_population`
  runs both constructions at every rung; the artifact records the
  opposite-outcome share per rung and the item-C evaluation.
  **Unchanged:** `measure_oos` / `weighted_pair_table` /
  `weighted_two_way_gap_bootstrap` / `cost_floor` / the
  `directional_skill_pit_legal_pool` loaders (all imported unmodified),
  the N=0 gate, the 15-point ladder, the cost floors, the
  cohort/placebo definitions, `seed=42`, `reps=1500`, `cap5`, `T_SPLIT`.
- **`--selfcheck`:** edge identity + N=0-gate identity vs `measure_oos`
  + **conversion-direction check** (`1 − q` applied iff outcomes differ)
  — 625 substitutions verified, 0 mismatches.
- **Durable artifact:**
  `data/characterizations/copy_trade_decay_20260910T200321Z.json`
  (197 KB; the 2026-09-10 artifact is untouched). For **both
  constructions** at every rung, per population and per category:
  `point_gap` + CI, `n_pairs`/`n_positions`/`n_traders`,
  `opposite_outcome_share`, `n_nonconvertible`, `n_excluded_tape_end`,
  realised-delay distribution, THIN flag; the N=0 gate deltas; the
  item-C material-disagreement evaluation; `metric_v2f_oos_result`
  sha256 before/after.
- **`script_commit` in the artifact** is `c9619a4` (HEAD at run time);
  the modified script lands in first-repo `1f43424` (parent `c9619a4`).
- **Stop conditions — none tripped:** N=0 gate passed for all three
  populations (Δ = 0.0); `metric_v2f_oos_result` sha256
  `021be40a…4cd4e` unchanged; `outcome` available for every substituted
  trade (0 unavailable; 1–2 non-binary non-convertible per rung,
  counted not dropped); no rung THIN or uncomputable.
- **`--persist` was never passed. No write to any production table.**
- **Tests:** `run_tests.py` (not bare pytest) — **25 files, 25 passed,
  0 failed** (339,909 assertions). The modified script adds no test file;
  no existing module changed; suite unchanged and green.
