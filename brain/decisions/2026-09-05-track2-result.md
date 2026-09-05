# Track 2 — CI Power Diagnostic: Result

Pre-registration: `brain/decisions/2026-09-04-track2-ci-power-prereg.md`
(trading-swarm `f5df56a` — see §0 below on why that hash, not the one the
task named). Diagnostic script: `scripts/track2_ci_power_diagnostic.py`
(first-repo, this run's commit `1af61e5`). Every threshold below is
restated from the pre-registration BEFORE any result appears, per its own
anti-post-hoc-reinterpretation mechanism, and none was adjusted after
seeing output.

---

## §0 — Corrections to this task's own framing (checked before computing)

Per standing instruction, every claim in the task prompt was checked
against the actual committed document, not assumed:

- **"The pre-registration is committed... (trading-swarm 5d1a89c)" — false.**
  `5d1a89c` does not exist in trading-swarm. The document was still staged,
  not committed, exactly as the prior read-only audit found. It has now
  been committed as `f5df56a`, unmodified from what was reviewed, before
  this diagnostic ran — satisfying the document's own precondition
  ("committed before any diagnostic runs").
- **"±0.02 tolerance" for Gate A — not the document's rule.** No such
  figure appears anywhere in the pre-registration. The actual rule (§6) is
  four-part: point estimate within the original CI bounds, same sign,
  `n_positions`/`n_traders` growing not shrinking, and any >10%
  discrepancy attributed to a named mechanism. Used below.
- **"≥15% criterion" for the decomposition — not the document's rule.**
  The actual rule (§2) is `share_trader ≥ 0.65` / `share_market ≥ 0.65`
  (with the other `< 0.35`) to call a dimension "bound"; otherwise "Mixed."
  Used below.
- **"~2× benchmark-rate bar and 24-month horizon" — not the document's
  rule.** The actual rule (§4) is a **12-month** horizon and
  `ATTAINABLE ⟺ K_required/R ≤ 12`. No "2×" figure appears anywhere.
- **"Four enumerated outcomes" — the document specifies five** (§5):
  market-bound+attainable, market-bound+not-attainable, trader-bound,
  **mixed**, inconclusive. "Position-bound" is the document's own corrected
  term for what the task calls "position-bound" — §2 reframes it as
  *market*-bound, since the bootstrap's actual resampling units are traders
  and markets, not positions.
- **"Derived cost floor" — not a Track 2 concept.** "Cost floor" belongs to
  a different, unrelated part of `trader_skill_metric_v2f.py` (Objective 1,
  `metric_v2f_cost_floor`). Track 2's derived quantity is `K_required`
  (§3), computed below using the document's own formula — no cost-floor
  number is substituted.

None of the above changed how the diagnostic was run — they are corrections
to this prompt's paraphrase, not to the document, which is authoritative
throughout.

---

## §A — Fixed thresholds, restated (before any result)

- **Gate A / falsification (§6):** ACCEPTABLE DRIFT requires (a) point
  estimate within `[-0.00881, +0.07101]`, (b) same sign (positive), (c)
  `n_positions`/`n_traders` growing vs. `3032`/`120`, (d) any >10%
  discrepancy attributed to a named, checked mechanism. Otherwise STOP.
- **Decomposition (§2):** `share_trader = (w_full - w_market)/w_full`,
  `share_market = (w_full - w_trader)/w_full`. Trader-bound iff
  `share_trader ≥ 0.65` and `share_market < 0.35`; market-bound iff the
  mirror image; otherwise Mixed.
- **Projection (§3):** `K_required = K_today * (hw_today/hw_target)^2`,
  valid only for `K_required/K_today ≤ 3`; beyond that, order-of-magnitude
  only.
- **Attainable (§4):** 12-month horizon; `ATTAINABLE ⟺ K_required/R ≤ 12`.
- **Outcomes (§5):** market-bound+attainable / market-bound+not-attainable
  / trader-bound / mixed / inconclusive.

---

## §B — Reproducibility setup

- **Committed script:** `scripts/track2_ci_power_diagnostic.py`
  (first-repo, commit `1af61e5`, written this run — did not exist before).
- **Seed:** `42` (matches `trader_skill_metric_v2f.SEED`).
- **Reps:** `1500` (`GATE_REPS_LOCAL`).
- **`T_split`:** `2026-04-01 00:00:00`.
- **Weight function:** `cap5`.
- **Durable artifact:** `data/characterizations/track2_ci_power_20260905T104945Z.json`
  (first-repo) — full cohort/control trader lists, all intermediate
  numbers, both repos' commit hashes at run time.
- **Method reused unmodified, not reimplemented:** `build_presplit_cohort`,
  `match_control`, `measure_oos` (from `trader_skill_metric_v2f.py`);
  `weighted_pair_table` (from `trader_skill_metric_v2d.py`). The
  diagnostic's own bootstrap function draws `t_mult` then `m_mult` from a
  single shared RNG stream per replicate, in the same order as
  `weighted_two_way_gap_bootstrap`, so the "full" variant reproduces that
  function's CI bit-for-bit, and the two ablations (fixing the other
  multiplier to 1) use the identical per-replicate draws as the full
  variant, not independently re-drawn.
- **Per Part 8's persistence requirement, amended by this task's own
  constraint:** the true cohort/control trader lists are persisted in the
  JSON artifact above, not as a new `metric_v2f_*` DB table — this task
  explicitly forbade writing to `metric_v2f_*` or any production table;
  no such write occurred.

---

## §C — Gate A: reproduction

| | original (2026-08-15) | reproduced (2026-09-05) |
|---|---|---|
| cohort point_gap | 0.0315984 | **0.0207865** |
| cohort CI | [-0.00881, +0.07101] | **[-0.01216, +0.05582]** |
| cohort n_positions | 3,032 | **3,795** (+25.2%) |
| cohort n_traders | 120 | **141** (+17.5%) |
| placebo point_gap | 0.0127065 | 0.0279523 |
| placebo CI | [-0.02101, +0.04614] | [-0.00946, +0.06595] |

Checks: within original CI bounds — **true**. Same sign (positive) —
**true**. Growing, not shrinking — **true**. Both discrepancies exceed
10% (25.2% and 17.5%), so attribution was required: a same-cohort query
(same mechanism check the pre-registration's own §0.5 used) found **all
3,795** cohort OOS positions have `entry_timestamp` at or before the
original result's `generated_at` (2026-08-15T19:36:56) — **zero** are
genuinely new entries; 100% are pre-existing positions whose markets have
since resolved (pending→won/lost). Fully attributed to the named,
anticipated mechanism.

**GATE A: PASS.** Proceeding to decomposition.

**Caveat, not part of the gate rule but material to interpretation:** the
*presplit-qualifying cohort itself* also grew, from the historically-cited
148 traders to **169** today (+21, +14.2%) — before the OOS survival
filter narrows it to the 141 above. The pre-registration's §6 rule is
written over the OOS measurement's `n_positions`/`n_traders`, which this
gate correctly checks; it has no separate threshold for presplit-cohort
membership drift. This is exactly the staleness question Open Question 2
left unresolved (reconstruct "as of 08-15" vs "as of today") — flagged
here, not resolved, and not used to alter the PASS call above.

---

## §D — Decomposition

| variant | CI | half-width |
|---|---|---|
| full two-way | [-0.01216, +0.05582] | **0.033990** |
| trader-only (m_mult=1) | [+0.00082, +0.04219] | **0.020687** |
| market-only (t_mult=1) | [+0.00201, +0.04062] | **0.019303** |

`share_trader = (0.033990 − 0.019303) / 0.033990 = 0.4321`
`share_market = (0.033990 − 0.020687) / 0.033990 = 0.3914`

Neither clears the fixed 0.65 bar, and both clear the 0.35 "not-bound"
ceiling — the §2 rule's own explicit non-orthogonality note applies:
the two shares don't need to sum to 1 (0.4321 + 0.3914 = 0.8235 here),
and that is expected, not an error.

**Classification: Mixed.** Neither dimension binds.

---

## §E — Binding dimension

**Neither.** Both trader-cluster and market-cluster uncertainty contribute
materially to CI width (43.2% and 39.1% respectively); the fixed 0.65/0.35
rule does not call a winner.

---

## §F — Projection (K_required)

**Not computed.** §3's formula is defined only "if trader-bound" or "if
market-bound" (`K` = the binding dimension's count). With classification
= Mixed, there is no single binding dimension to project against, and the
pre-registration gives no formula for a mixed case — per its own text
(§5, Outcome 4), a combined-lever calculation "would need its own
pre-registration, not an ad-hoc extension of this one." No number is
substituted.

---

## §G — Attainability

**Not computed**, for the same reason: attainability (§4) is defined in
terms of `K_required`, which does not exist here. The monthly
new-qualifying-market rate for the true (141-surviving) cohort was
measured anyway, for the record, and is **not** used to derive an
attainability verdict:

| month | new positions | new distinct markets |
|---|---|---|
| 2026-04 | 2,174 | 351 |
| 2026-05 | 1,333 | 245 |
| 2026-06 | 270 | 61 |
| 2026-07 | 16 | 8 |
| 2026-08 (last complete month) | 2 | 2 |

(2026-09 excluded as partial.) Same collapse pattern the pre-registration's
§0.6 proxy-cohort exploration flagged — now confirmed on the **true**
cohort, not the proxy — but it plays no role in this verdict, per §F.

---

## §H — Verdict against the five enumerated outcomes

1. Market-bound and attainable — NO
2. Market-bound but not attainable — NO
3. Trader-bound — NO
4. **Mixed — YES**
5. Inconclusive — NO (bootstrap converged on all three variants: 1500/1500
   valid draws each; this is not a non-convergence case)

**Outcome 4: MIXED.**

---

## §I — What this means, per the document's own text

Quoting §5, Outcome 4, verbatim: "Both dimensions contribute materially
(§2's separation rule fails to call either bound). Report both
`share_trader`/`share_market` and treat as **inconclusive for a
single-lever strategy** — a combined-lever attainability calculation would
need its own pre-registration, not an ad-hoc extension of this one."

Concretely: this is **not** the "trader-bound" outcome — the document is
explicit that only in that case does "enlarging the market population not
help." Here, enlarging the market population *would* help
(`share_market` = 39%, non-trivial), just not enough on its own to be
called market-bound; the same is true of adding qualifying traders in the
other direction. Neither single lever — more markets alone, or more
skilled traders alone — is licensed by this result as *the* answer. A
combined-lever attainability question is a live, real follow-on, but is
explicitly **out of scope for this pre-registration** and would require
its own pre-registration before computing anything, per §5 and per the
project's standing reproducibility rule.

---

## §J — Constraints honored

- No component was re-specified, re-parameterised, or re-run after seeing
  its result.
- No corrected thesis measurement was produced; `metric_v2f_oos_result`
  (2026-08-15, commit `eaeabbc`) is untouched and remains the result of
  record. This diagnostic answers a narrower question (§7 of the
  pre-registration) and does not supersede it.
- No write to `metric_v2f_*` or any other production table. All output is
  in the JSON artifact and this document.
- Nothing was left to "approximate" — where §3/§4 could not be computed as
  specified (no binding dimension), that is reported as such, not
  substituted.

---

**Bottom line: Gate A PASSED. The decomposition result is Mixed (Outcome
4) — neither trader count nor market count binds the CI width on its own.
No cost-floor/K_required number exists, because the pre-registration's own
method does not define one for a mixed result. Per the document's own
text, this is inconclusive for any single-lever strategy; a combined-lever
question would need a new, separate pre-registration.**
