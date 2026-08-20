# 2026-08-20 — do the 203 resolved-but-undiscovered markets reach the result of record?

**Read-only. No repair, no resolution, no discovery fix implemented.**
Every claim tagged **[V]** (verified this session, query/script given) or
**[I]** (inferred). Input: the 203 enumerated `market_id`s from
`data/characterizations/discovery_gap_sizing_20260820T211955Z.json`
(classification `"resolved"` rows), used directly, not re-derived. Script:
`scripts/discovery_gap_thesis_intersection.py` (first-repo, committed
alongside this document). Raw output:
`data/characterizations/discovery_gap_thesis_intersection_20260820T213018Z.json`.

---

## Verdict: **TOUCHING**

**Reaches both the OOS survivors and the placebo — substantially — but not
in the way the naive "thinned population" framing predicts.** The
already-published `+0.0316` cohort / `+0.0127` placebo figures are
structurally untouched *today*, because every affected position's
`trade_result` is `pending` and every query that produced those two
numbers filters to `trade_result IN ('won','lost')`. But the trader
populations underlying those two numbers have real, substantial,
currently-invisible exposure in these 203 markets — **90 of 126 (71.4%)
OOS-surviving cohort traders** and **68 of 113 (60.2%) OOS-surviving
placebo traders** hold positions in them, and the counterfactual edge on
that exposure (Q6) trends in a direction that would **narrow**, not
widen, the cohort-vs-placebo gap if these markets were properly resolved
and folded in. Full detail below, per question.

---

## Q1 — temporal placement

**[V]**, via `build_tape_end_map` (the project's own canonical `tape_end`
definition) applied to all 203:

| | Count |
|---|---|
| `tape_end <= T_split` (2026-04-01) — would affect cohort **qualification** | **164** |
| `tape_end > T_split` — would affect the **measured OOS edge** | **39** |
| No tape_end | 0 |

`tape_end` range across all 203: **2025-02-10 to 2026-07-06**, median
**2025-12-28**. These are two different harms, kept separate as
instructed: 164 markets could have changed who qualified for the
pre-split cohort; 39 could have changed what the post-split measurement
actually saw.

**Does the sizing doc's 15-market cross-check (85–555 days back)
generalize?** **Partially, not fully.** That sample (ordered by
`market_id`, effectively arbitrary with respect to time) landed entirely
in the older part of the range and **missed the newest tail** — the full
203-market range extends to `2026-07-06`, only 45 days before today
(2026-08-20), and specifically includes the 39 post-split markets whose
`tape_end` falls after `T_split`. The earlier cross-check's conclusion
("these markets resolved a long time ago, corroborated") is correct in
aggregate and remains uncontradicted (45 days still clears that doc's own
30-day corroboration bar), but **it understates how recent some of the
203 markets' resolutions actually are relative to `T_split`** — which is
exactly why Q1 splits pre/post rather than reporting one pooled range.

---

## Q2 — would they enter the canonical population?

**[V]**, using `monitoring/column_definitions.py::backtest_window_sql()`
directly, not a hand-rolled equivalent.

- Today, with `resolved=1` required: **0 of 203** are in the canonical
  population — confirms the task's premise that these are excluded, by
  construction (they're `resolved=0`).
- As-if `resolved=1` were set: all 203 already satisfy the canonical
  query's category (`Geopolitics`/`Elections`) and gap-flag clauses (this
  is definitional — it's how the 203 were selected in the sizing doc's own
  G stratum). The only remaining canonical clause is the `tape_end >=
  window_start` bound, answered by Q1: **164 would enter any window
  reaching back to their `tape_end`, 39 would only enter a window
  extending to `2026-07-06`.**
- **No disagreement found between the canonical function and a hand-rolled
  check** — the as-if test used `backtest_window_sql` itself with an
  arbitrarily early `window_start`, not a re-implementation.

---

## Q3 — cohort and placebo reach (direct set intersection)

**[V]**, reconstructed via `trader_skill_metric_v2f.py`'s own unmodified
functions (`build_presplit_cohort`, `match_control`), same default
`SEED=42`, same `T_SPLIT`. **Important, flagged plainly:** re-running
today does **not** reproduce the persisted 08-15 counts exactly — this is
already a known, documented phenomenon (`2026-08-16-result-of-record-reproducibility-audit.md`:
"UNREPRODUCIBLE," DB drift since 08-15). Today's re-run: **154**
presplit-qualifying (was 148), **126** OOS survivors (was 120), **154**
placebo pool (was 148), **113** OOS-surviving placebo (was ~106–110
depending on run). The *shape* of the result is unaffected by this drift;
the counts below use today's reproducible re-run, clearly labeled.

| Population | N (today) | Traders touching the 203 | Positions in 203 | Distinct markets of 203 touched |
|---|---|---|---|---|
| **a. 148→154 presplit-qualifying cohort** | 154 | **104 (67.5%)** | 695 | 73 |
| **b. 120→126 OOS survivors** | 126 | **90 (71.4%)** | 637 | 62 |
| **c(i). 148→154 placebo pool** | 154 | **75 (48.7%)** | 438 | 70 |
| **c(ii). placebo OOS survivors** | 113 | **68 (60.2%)** | 424 | 70 |

**(b) is not zero — stated plainly per the task's own instruction.** The
measured edge's own surviving cohort has substantial, real exposure to
these markets.

**Every single one of the 2,194 touching positions across all four rows
has `trade_result = 'pending'` — zero `won`/`lost` — confirmed by direct
count, not assumed.** This is the structural reason the *already-published*
headline figures are untouched despite this large trader-level overlap:
`build_presplit_cohort`, `measure_oos`, and `match_control`'s own
eligibility pool all filter `t.trade_result IN ('won','lost')` — a
position sitting in one of these 203 markets is invisible to every one of
those queries today, regardless of whose position it is.

Full per-position detail (all four populations) is in the committed JSON.

---

## Q4 — per-trader materiality

**[V]**, computed for all 179 distinct traders appearing in any of Q3's
four rows. Denominator: each trader's total distinct markets in the same
Geopolitics/Elections, gap-clean, `won`/`lost`-resolved population v2f's
own queries use (i.e. their current, real cohort-eligible footprint).

- **Median exposure: 4.9% of a touching trader's total market footprint
  is in the 203-set** — most affected traders are large, diversified
  traders for whom this is a small fraction.
- **34 of 179 (19%) have >=10% of their total markets in the 203-set; 3
  have >=25%.** The highest: a placebo-pool trader with 4 of 15 total
  markets (26.7%) in the 203-set, and a presplit-cohort trader with 13 of
  57 (22.8%).
- **13 touching traders have a total market footprint of 15 or fewer** —
  close enough to the `M>=10` qualification boundary that a few additional
  markets is not a rounding error for them specifically; this population
  overlaps with, but is not identical to, Q5's boundary-crossing set
  below (Q4's "close to the boundary" is about *existing* qualifiers near
  the floor; Q5 is about *non*-qualifiers who'd cross it).

Full 179-row table (trader, memberships, total markets/positions, count
and fraction touched) is in the committed JSON — not reproduced here in
full per the task's own steer toward materiality distinctions, not raw
aggregate dumps.

---

## Q5 — qualification-boundary effect

**[V], with a stated approximation, not a full re-derivation.** Method:
for every trader holding any position in the 164 pre-split-relevant
markets (from Q1), computed their **current** `n_pairs` (the actual metric
`M_CHOSEN=10` is thresholded on, via `compute_cap5_metric`/`per_trader_t_ci`
on today's real presplit population — not a stand-in), then upper-bounded
what `n_pairs` could become if every additional distinct 203-market they
touch contributed one more pair (cap5 pairing is per trader-market, so
this is a legitimate upper bound, not an exact recomputation — a true
recount would require re-running the pairing algorithm on an augmented
dataset with synthetic `won`/`lost` outcomes injected, which this
investigation did not do; **flagged as an approximation, per the task's
own instruction to state clearly if something cannot be fully settled**).

- **1,077 distinct traders** hold some position in the 164 pre-split-relevant
  203-markets.
- **46 of them currently have `n_pairs < 10` (do not qualify today) but
  have an upper-bound `n_pairs >= 10` if these markets were resolved and
  counted** — real candidates for the "invisible non-qualifier" case Q5
  asks about. Most are 1 market away from the boundary (`current=9,
  +1=10`); several are further: one trader has `current=0, +26=26` — a
  trader with **zero** presence in the entire current presplit-eligible
  population who would become a substantial (26-market) cohort candidate
  outright if these markets were resolved.
- **This is an upper bound, not a confirmed count of new qualifiers** —
  actually crossing `M_CHOSEN` also requires the trader's confidence
  interval to clear `ci_lo_t > 0` (the significance gate) and their
  shrunk mean to clear `EFFECT_BAR=0.02`, neither of which this
  approximation checks. **What would settle this precisely:** inject
  synthetic `won`/`lost` labels (using the CLOB winner already known for
  each of the 164 markets) into the presplit position set and re-run
  `compute_cap5_metric` + `per_trader_t_ci` + the full eligibility chain
  on the augmented population — not done here, out of this task's
  read-only/no-recomputation scope, and explicitly named as the next step
  if this question needs a firm answer rather than a bound.

---

## Q6 — direction (computable, unlike the orphan SELLs)

**[V].** For the 637 (OOS-survivor) and 424 (placebo-survivor) affected
positions, `winner` was extracted cleanly for **100%** — `n_no_winner_extractable
= 0` in both cases, since every one of the 203 markets' `winner` values
came from the sizing census's own `classification == "resolved"`
requirement (a token showing `winner: true` was mandatory to be in the 203
at all).

| | n positions | Mean edge | Median edge |
|---|---|---|---|
| **OOS-survivor-affected positions** | 637 | **+0.00056** | +0.0100 |
| **Placebo-survivor-affected positions** | 424 | **+0.01143** | +0.0035 |

**Compare to the persisted headline figures: cohort +0.0316, placebo
+0.0127.** The affected cohort positions' own mean edge (+0.00056) is
**roughly 1/56th of the cohort's headline figure** — essentially flat,
near zero. The affected placebo positions' own mean edge (+0.01143) is
close to the **placebo's own headline figure** (+0.0127).

**Stated plainly, without recomputing the headline:** if this exposure
were folded into a corrected measurement at face value, the cohort's own
newly-available evidence looks much weaker than its published edge, while
the placebo's newly-available evidence looks similar to its own published
edge. That pattern — if it held under a real, gated recomputation — would
**narrow the gap** between the two, not widen it. This is not a
recomputed headline; it is what the affected positions' own edge
distribution shows, reported for the reader to judge, per the task's
explicit instruction.

---

## Q7 — overlap with known populations

**[V].** Checked against the latest committed snapshots
(`pending_resolution_inconsistency_20260820T162816Z.json`, 92 markets;
`no_fifo_close_markets_20260820T162853Z.json`, 162 markets):

- Overlap with the 92-market pending-resolution set: **0**.
- Overlap with the 162-market no-FIFO-close set: **0**.

**Fully disjoint — no double-counting.** This is close to structurally
guaranteed (both of those populations require `resolved=1` with some
other inconsistency; the 203 are `resolved=0` by construction), but
checked directly rather than assumed, per instruction.

---

## Summary of what changed and what didn't

- **The published `+0.0316` / `+0.0127` numbers: unaffected today.**
  Structurally impossible for them to include these 203 markets' positions
  — confirmed by direct count (0 of 2,194 touching positions are
  `won`/`lost`), not inferred from the filter logic alone.
- **The trader populations behind those numbers: substantially touched.**
  71% of OOS-surviving cohort traders and 60% of OOS-surviving placebo
  traders hold real, dormant exposure in these markets — not a fringe
  effect.
- **Cohort qualification: a real, quantified open question, not fully
  settled.** 164 of the 203 could have affected who qualified; 46 traders
  are upper-bound candidates to newly cross `M>=10`, one of them (0 → 26)
  dramatically so — but confirming actual new qualifiers requires the
  full pairing/significance/effect-bar chain re-run on an augmented
  dataset, not done here.
- **Direction, where computable: adverse to the current gap, not neutral.**
  The affected cohort positions show far less edge than the cohort's own
  headline; the affected placebo positions show edge comparable to the
  placebo's own headline. Reported as the affected positions' own
  distribution, not a recomputed thesis result.

---

## Reproducibility

```
python3 scripts/discovery_gap_thesis_intersection.py
```
No `--persist`, no writes anywhere (confirmed by code inspection — the
script contains no `INSERT`/`UPDATE`/`DELETE`/`.commit()` call, only
`SELECT`s and its own JSON output file). Cohort/placebo membership is
regenerated fresh each run via `trader_skill_metric_v2f.py`'s own
functions with fixed `seed=42` — subject to the same DB-drift-driven
non-reproducibility already documented in
`2026-08-16-result-of-record-reproducibility-audit.md`; today's counts
(154/126/154/113) are this run's actual, reproducible-as-of-today output,
not a re-derivation of the original 08-15 148/120/148/~110 figures, which
remain unreproducible for the reasons that audit already established.

---

*Generated 2026-08-20. Input: `2026-08-20-discovery-gap-sizing-result.md`
and its 203-market census (first-repo,
`data/characterizations/discovery_gap_sizing_20260820T211955Z.json`).
Script: `scripts/discovery_gap_thesis_intersection.py` (first-repo). Raw
output: `data/characterizations/discovery_gap_thesis_intersection_20260820T213018Z.json`.
Read-only throughout: no writer modified, no market resolved, no discovery
fix implemented, no `--persist` used anywhere in this chain.*
