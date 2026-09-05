# Track 2 — CI Power Diagnostic: Pre-Registration

**PRE-REGISTRATION ONLY. Committed before any diagnostic runs, any CI is
computed, or any projection is produced.** Per the standing instruction on
reproducible decision numbers: nothing below may be adjusted after seeing
diagnostic output. This document fixes the question, the decomposition
method, the projection form, the thresholds, and the falsification rule.
The result — if this pre-registration is approved and the diagnostic is
then run — is a separate document, filed after this one, never edited into
it.

**Tagging: `[V]` verified this session (query/code/doc given), `[I]`
inferred or a fixed judgment call, marked as such.** Every claim in the
task prompt was checked against source documents and live DB/code state
before being carried forward. Two of the prompt's framings needed
correcting (§0.3, §0.5) — followed the design where it differed, as
instructed.

No metric-pipeline script (`trader_skill_metric_v2f.py`,
`trader_skill_metric_v2d.py`, or any `--persist` path) was executed in
this session. All verification below used either already-persisted DB
tables or plain read-only `SELECT`s against `positions`/`markets`/`trades`
— never `weighted_pair_table`, `weighted_two_way_gap_bootstrap`,
`build_presplit_cohort`, or `measure_oos`. No CI, decomposition, or
projection number appears anywhere below as a result — only as symbolic
form (§2–§3), historical fact (§0), or explicitly-labeled proxy exploration
used solely to set thresholds (§0.6, §4).

---

## PART 0 — VERIFIED HISTORY (do not inherit the prompt's summary uncritically)

### 0.1 What Track 2 was designed to test, and why

`2026-08-16-session-summary.md` **[V]**: Track 2 is "a CI power
diagnostic — decompose the 08-15 out-of-sample result's CI to determine
whether a frozen-cohort Phase 2 can resolve the underpowered thesis result
in finite time." It exists because the persisted result of record itself
is a null result on power grounds, not on direction:

```
-- data/polymarket_tracker.db, metric_v2f_oos_result (persisted 2026-08-15T19:36:56, commit eaeabbc)
kind     n_positions  n_traders  point_gap             ci_lo                  ci_hi
cohort   3032         120        0.0315983580923187    -0.00881147179033796   0.0710126418085991
placebo  2569         110        0.0127065403076488    -0.0210094439314384    0.0461439972587876
```
**[V, live query this session]** — matches `MASTER_HANDOVER_2026-08-15.md`
exactly. Cohort CI **includes zero** (`ci_lo` is negative); per the
pipeline's own verdict logic (`trader_skill_metric_v2f.py:429-442`) this is
`NULL — the cohort's out-of-sample edge does not exclude zero`, positive
in direction and roughly 2.5× the placebo's point estimate, but not
statistically resolved. Track 2 asks whether that resolution is available
in principle from more data, or whether the program should stop waiting on
it.

**Correction to my own framing before this history section:** the prompt's
implicit premise — that a specific decomposition method, projection form,
and set of thresholds were already specified in 2026-08-16 and merely need
"restoring" — does not hold. `2026-08-16-session-summary.md` **[V]**
specifies only the *question* above. No traders-vs-positions decomposition,
no projection functional form, and no numeric thresholds appear anywhere
in the 08-16 record or in any later session summary before today. Track 2
was deliberately not run on 08-16 itself, on the explicit judgment that
decomposing a CI whose underlying population "had not itself been
characterised" would build on an unverified foundation. **This document is
therefore the first specification of Track 2's method, not a restoration
of one.** ("Track 1" is never defined anywhere in either repo — Track 2
has no named sibling on record.)

### 0.2 Was a pre-registration ever drafted?

No. Repo-wide search (both repos, filenames and content) for
`track2`/`track-2`/`ci-power`/`power-prereg` returns zero files before this
one **[V]**.

### 0.3 The 09-03 status check — corrected citation

The prompt cites a "09-03 status check" reporting Track 2 as NOT STARTED.
`2026-09-03-gate-result.md` contains **no mention of Track 2 at all**
**[V]** — that citation is wrong. The actual, correctly-worded status
check is `2026-09-01-session-summary-0831-0901.md:392-397` **[V]**: "The
Phase 2 chain: the second measurement (§E of the pre-registration), the
Track 2 CI power diagnostic, the cutover decision, ingestion-stall
detection — all **NOT STARTED**." Every session summary from 08-18 through
08-27 repeats the same status in near-identical language. **NOT STARTED is
confirmed correct; the date attribution in the prompt is not.**

### 0.4 The A3 stop condition — confirmed as a required amendment, but never a primary source

The prompt states Track 2's A3 stop condition "treats a failure to
reproduce the result of record as evidence of a broken harness," and that
this needs amending given the 08-16 audit's substrate-drift finding.
**Important flag:** no committed document anywhere — not
`2026-08-16-session-summary.md`, not `MASTER_HANDOVER_2026-08-15.md`, not
any other file — defines an A1/A2/A3 list as primary text **[V, searched]**.
The characterization is attested consistently, in near-identical wording,
across six session summaries (08-18 line 170, 08-19 line 292, 08-20 line
288, 08-21 line 347, 08-24 line 478, 08-27 line 371) **[V]** — real and
unanimous, but secondhand. §6 below treats this as the accurate substance
of what must be amended, without quoting a primary A3 text that does not
exist.

### 0.5 The reproducibility audit — confirmed, and materially extended by a live re-check this session

`2026-08-16-result-of-record-reproducibility-audit.md`, verdict
**UNREPRODUCIBLE** **[V]**. Re-running the identical script under the
identical seed one day later found:

| Quantity | 08-15 | 08-16 re-run | Δ |
|---|---|---|---|
| Objective 2 cohort point estimate | 0.0315983580923187 | 0.03184400367920137 | +0.000246 |
| Objective 2 cohort n_positions | 3,032 | 3,033 | +1 |
| Objective 2 placebo point estimate | 0.01270654030764884 | 0.01391568978328761 | +0.001209 |
| Objective 2 placebo n_positions / n_traders | 2,569 / 110 | 2,518 / 106 | −51 / −4 |

(lines 158-177 **[V]**). Root cause, quoted (lines 204-213): "background
backfill is actively inserting **pre-T_split-timestamped** trades into the
DB after 08-15. Verified directly, not inferred: of the 553,800
most-recently-inserted trade rows (by rowid), 162,648 carry
`timestamp < 2026-04-01`... This is exactly the kind of write that would
silently shift both the Objective-1 population and the Objective-2
pre-split eligibility pool." Code drift was explicitly ruled out (same
commit, `eaeabbc`, zero commits since). This is the audit's own
"mechanism confirmed active" finding — the session summary's gloss of it
as "substrate drift" is accurate, though that exact phrase is not the
audit doc's own words.

**One methodologically important fact the prompt did not surface, found by
reading the audit closely:** the audit's own verdict was **UNREPRODUCIBLE,
explicitly not DRIFTED** (line 21, 257), because one component of the
divergence (the placebo's control-match instability, driven by an
unpersisted `elig_pool`) could not be attributed at the required row
level, even though its mechanism was well understood. The audit states its
own rule plainly: **"an unattributed discrepancy forces UNREPRODUCIBLE,
not DRIFTED, even though the mechanism is well-understood."** This
distinction — magnitude alone is not sufficient; attribution to a named
mechanism is required — is load-bearing for §6's amendment below.

**Also found, and directly relevant: the true Objective-2 cohort was never
persisted anywhere.** Line 89-90: "What is NOT recorded: the actual trader
addresses of the 148 pre-split-qualifying / 120 surviving cohort, or of
the 148 matched placebo controls." Line 79: `metric_v2f_intersection_cohort`
(the one cohort table the pipeline does persist) is "a DIFFERENT, larger
population than Objective 2's 148 pre-split-qualifying traders" — it is
Objective 1's full-history intersection cohort, not Objective 2's
pre-split-only-derived one. Line 125-126: "there is no way to prove
today's 148 are last month's 148."

**This session's own live re-check (read-only, `metric_v2f_intersection_cohort`
joined to `positions`/`markets`/`trades` with the identical structural
filters `measure_oos` uses, no bootstrap, no pipeline script run) confirms
this gap is still open and has grown much larger in magnitude than the
one-day audit measured:**

```sql
-- proxy population: metric_v2f_intersection_cohort (295 traders, Objective 1's
-- persisted cohort -- NOT the true 148-trader Objective 2 cohort, which was
-- never persisted and cannot be reconstructed without running the pipeline)
SELECT COUNT(*), COUNT(DISTINCT p.trader_address)
FROM positions p JOIN markets m ON m.market_id = p.market_id
JOIN trades t ON t.trade_id = json_extract(p.entry_trade_ids, '$[0]')
JOIN metric_v2f_intersection_cohort c ON c.trader = p.trader_address
WHERE m.category IN ('Geopolitics','Elections') AND p.entry_avg_price IS NOT NULL
  AND t.trade_result IN ('won','lost') AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  AND p.entry_timestamp > '2026-04-01 00:00:00';
-- → 11,009 positions, 272 traders (today, 2026-09-04)
```

vs. the persisted 3,032/120. Of that growth, only **3** positions have
`entry_timestamp` after the 08-15 result's own `generated_at` — the
remaining ~7,970 already existed as of 08-15 with `entry_timestamp`
already past `T_split`, and have since transitioned from an unresolved
`trade_result` to `won`/`lost` as their markets closed in the ordinary
course of monitoring (only 466 of the 11,009 sit on markets carrying the
discovery-gap sweep's own canonical-write provenance signature — the
sweep is not the main driver). **This is not a precise reproduction of the
persisted result** — it uses the wrong (larger, differently-derived)
cohort, exactly the gap the audit itself flagged — so it is reported here
as a directional, order-of-magnitude proxy only, not as today's true
divergence. It is used in §4 and §6 below strictly as threshold-setting
evidence, never as a stand-in for an actual reproduction.

### 0.6 What has been overtaken by events since 08-16

Track 2's 08-16 design predates the discovery-gap-closure sweep and the
relevance classifier by days and never assumed either as a lever — no
stale assumption there **[V]**. What *has* changed, verified this session
and not previously documented anywhere in this arc: **the same
substrate-drift mechanism the 08-16 audit found (a single day after the
result was generated) is still live three weeks later, and its magnitude
has grown from single-digit position counts to an order of ~4,000
positions** under the (admittedly proxy) cohort checked above. Any Track 2
baseline-reproduction step inherits this same live, unresolved,
now-much-larger risk — this is precisely why §6 fixes numeric thresholds
now rather than leaving "reproduction failure" as a binary pass/fail.

**Also verified this session, using the same proxy cohort, and directly
relevant to §4's attainability threshold:** monthly new-position-entry
counts for the proxy cohort, in Geo/Elec markets, post-`T_split`,
regardless of resolution status:

```sql
SELECT strftime('%Y-%m', p.entry_timestamp), COUNT(*) FROM positions p
JOIN markets m ON m.market_id=p.market_id
JOIN trades t ON t.trade_id=json_extract(p.entry_trade_ids,'$[0]')
JOIN metric_v2f_intersection_cohort c ON c.trader=p.trader_address
WHERE m.category IN ('Geopolitics','Elections') AND p.entry_avg_price IS NOT NULL
  AND (m.trade_gap_flag=0 OR m.trade_gap_flag IS NULL) AND p.entry_timestamp>'2026-04-01'
GROUP BY 1 ORDER BY 1;
```
| Month | New entries (proxy cohort) |
|---|---|
| 2026-04 | 6,461 |
| 2026-05 | 5,026 |
| 2026-06 | 1,289 |
| 2026-07 | 98 |
| 2026-08 | 18 |
| 2026-09 (partial, 4 days) | 1 |

**[V, this session]**. A ~99.7% decline from April to August. This is a
proxy-cohort number, not the true 148-trader cohort's rate — but since
the 295-trader proxy is a *larger*, not smaller, population than the true
cohort, it is reasonable to treat it as a generous upper bound on the true
cohort's activity, not a floor: **if the proxy already shows this
collapse, the true cohort is unlikely to look better.** Whether this
reflects genuine Geo/Elections trading seasonality (plausible — an
election-cycle lull) or a data-completeness artifact is an **open
question, not resolved here** (see Open Questions). Either way, using the
08-15-era rate (or the April/May rate) to judge attainability today would
repeat exactly the mistake this project's own standing rule exists to
prevent — grounding a decision number in a stale snapshot rather than the
population as it stands.

---

## PART 1 — THE QUESTION, STATED PRECISELY

**Given the frozen 08-15 cohort/placebo definition, `T_split =
2026-04-01`, and the metric as specified (`trader_skill_metric_v2f.py`
Objective 2), is there a plausible, attainable-within-the-horizon-fixed-in-§4
augmentation of the eligible position/trader population — via any
combination of new qualifying trader activity, new qualifying positions
by existing cohort members, or elapsed calendar time allowing currently-pending
positions to resolve — that would move the cohort OOS CI's lower bound
above zero, without changing the cohort definition, the placebo-matching
method, or `T_split`?**

This admits a negative answer directly: if no such augmentation is
attainable within the fixed horizon, the answer is **NO** — the thesis is
not resolvable via additional data alone on a timescale this project can
wait for, under the current cohort/window design. That negative answer is
itself the deliverable of Track 2, not a failure of the diagnostic.

---

## PART 2 — THE DECOMPOSITION METHOD

**Vocabulary correction, fixed before specifying method:** the existing
CI machinery (`trader_skill_metric_v2d.py:164-211`,
`weighted_pair_table`/`weighted_two_way_gap_bootstrap`) does not resample
"positions" as its own unit. Positions are first collapsed, per trader ×
market, into a single weighted pair (`groupby(['trader','market_id'])`,
weight = `weight_fn(n)` under the `cap5` scheme, i.e. capped at 5 — a
sixth-and-later repeat position on the *same* trader/market pair adds no
further weight). The two-way bootstrap then resamples **traders** and
**markets** as two independent cluster dimensions (`t_mult`, `m_mult`,
`trader_skill_metric_v2d.py:192-204`), each drawn via
`np.bincount(rng.integers(...))` — a standard cluster bootstrap — and
combines them multiplicatively per pair. **"More positions" in the
task's sense therefore only helps CI width to the extent it means more
distinct markets** (raising `n_markets`, the second cluster dimension) or
filling previously-thin trader/market pairs up to the weight cap — not
simply more repeat trades on markets already covered. This reframes the
task's "position-bound" outcome as, more precisely, **market-bound** — and
ties directly back to the (now-stopped) discovery-gap sweep, whose entire
purpose was enlarging the categorized Geo/Elec market population; §5
Outcome 1 makes this connection explicit.

**Method specified (first time — reuses the existing bootstrap unmodified,
adds two ablation variants around it, changes no production code):**

1. Reconstruct the frozen cohort/placebo position-level data exactly as
   `measure_oos` (`trader_skill_metric_v2f.py:315-330`) does: the true
   148-trader presplit-qualifying cohort and its 148 matched placebo
   controls (per §0.5, neither is currently persisted — **Step 0 of the
   diagnostic must reconstruct and this time persist both trader lists**,
   see §8), `T_split = 2026-04-01`, identical structural filters
   (category, `entry_avg_price` not null, `trade_result IN
   ('won','lost')`, gap-clean).
2. Build the pair table via the existing, unmodified `weighted_pair_table`
   with `weight_fn = WEIGHT_FNS['cap5']` — same as the result of record.
3. Run three bootstrap variants over the **same pair table**, same
   `seed=42`, same `reps=1500` (`GATE_REPS_LOCAL`), for direct
   comparability with the persisted CI:
   - **Full two-way** (`weighted_two_way_gap_bootstrap`, unmodified) —
     reproduces the reported CI width; this is the baseline.
   - **Trader-only ablation**: resample `t_mult` exactly as today; fix
     `m_mult = 1` for every market (no market resampling). Isolates the
     CI-width contribution from trader-cluster uncertainty alone.
   - **Market-only ablation**: fix `t_mult = 1` for every trader; resample
     `m_mult` exactly as today. Isolates the CI-width contribution from
     market-cluster uncertainty alone.
4. **Separation rule, fixed now:** let `w_full`, `w_trader`, `w_market` be
   the three resulting CI half-widths. Compute `share_trader =
   (w_full - w_market) / w_full` and `share_market = (w_full - w_trader) /
   w_full` (each ablation's *marginal* contribution, not its raw width,
   since the two dimensions are not independent in general). Classify:
   - **Trader-bound**: `share_trader ≥ 0.65` and `share_market < 0.35`.
   - **Market-bound** (the task's "position-bound"): `share_market ≥ 0.65`
     and `share_trader < 0.35`.
   - **Mixed**: neither threshold is met — both dimensions contribute
     materially. `share_trader`/`share_market` need not sum to 1 in a
     non-orthogonal decomposition; that is expected, not an error, and
     must be reported as such rather than forced to a clean split.
   These cutoffs (0.65/0.35) are a fixed judgment call **[I]**, chosen to
   require a real majority contribution before calling a dimension
   "bound" rather than merely "dominant by a hair" — reviewable before the
   diagnostic runs, not after.

---

## PART 3 — THE PROJECTION

**Functional form:** for a cluster-bootstrap/cluster-robust CI, half-width
scales asymptotically as `1/sqrt(K)` where `K` is the count of the
*binding* cluster dimension identified in §2 (trader count if
trader-bound, market count if market-bound), holding cluster-size balance,
per-cluster variance, and the point estimate fixed. Projected required
count:

```
K_required = K_today * (half_width_today / half_width_target)^2
```

where `half_width_target` is the width needed for the CI's lower bound to
clear zero at the (assumed-fixed) point estimate — i.e.
`half_width_target < point_gap_today` under a symmetric-CI approximation.

**Justification:** this is the standard first-order asymptotic for
cluster-robust standard errors; it is *not* derived from re-fitting
anything here, and it assumes (a) the point estimate is stable as the
cluster count grows — an assumption, not a finding, and the one most
likely to fail if new traders/markets are systematically different from
the existing cohort; (b) cluster-size and heterogeneity structure stay
roughly similar to today's; (c) the two-way structure stays roughly
orthogonal to the binding dimension identified in §2.

**Stated limits, fixed now:** this projection is considered valid only for
`K_required / K_today ≤ 3` (i.e., roughly tripling the binding dimension
or less). Beyond that multiple, report the number as an
order-of-magnitude signal only ("not attainable on any reasonable
reading"), not as a specific target — the sqrt-scaling assumption has no
basis for extrapolation an order of magnitude beyond the observed regime,
and this project has already been burned once this cycle by an
extrapolation of exactly this kind (the sweep's own scope-widening,
[[project_thesis_population_lineage]]).

**No number is computed here.** §0.5/§0.6's proxy-cohort figures
(3,032→11,009 positions, 120→272 traders) are population-scale facts about
a *different, larger* cohort than the true 148-trader one and are not
substituted into this formula anywhere in this document.

---

## PART 4 — THE THRESHOLDS (fixed now)

**"Answerable":** a projected/future CI (recomputed by the diagnostic on
the true cohort, same method) counts as answerable if it (a) excludes
zero, direction positive, **and** (b) its lower bound sits at least 25% of
the point estimate's magnitude away from zero — i.e., not a hairline
exclusion. **[I, fixed threshold.]** Illustration only, using the real
persisted numbers, not a projection: today's lower bound (−0.0088) is
*below* zero by 28% of the point estimate (0.0316) in the wrong direction
— giving a concrete sense of how far short of "answerable" the current
result sits, without projecting how far more data would move it.

**"Attainable":** fixed horizon = **12 months** **[I]**, set by analogy to
this project's own precedent for "additional data" viability decisions —
`2026-08-14-session-summary.md` **[V]**: a related Phase 2 volume question
was judged **not viable** at "43 years (or ~5-6 years with a fallback) vs
a 4-9 month design estimate." Twelve months is chosen as a round ceiling
consistent with that precedent's attainable regime, not as a re-derivation
of it.

Numerically: let `R` = the true 148-trader cohort's most-recent
complete-calendar-month rate of new qualifying-position entries (per
`§2`'s market-cluster sense if market-bound; per new qualifying-trader
count if trader-bound) — **to be established by the diagnostic itself
using the reconstructed true cohort, not fixed here.** For scale only: the
proxy cohort's own most recent complete months ran 98/month (July) and
18/month (August) — two to three orders of magnitude below the
April/May rate (6,461 / 5,026/month) that produced the original sample.
**ATTAINABLE ⟺ `K_required` (§3, only when valid per its stated limit) is
reachable at rate `R` within 12 months** — i.e. `K_required / R ≤ 12`
months. Given the proxy range above, that would require `K_required` in
roughly the 216–1,176 range to qualify under the low end of the observed
proxy rate — stated here only to show the *scale* a genuine answer would
need to clear, not as Track 2's actual figure.

---

## PART 5 — OUTCOMES, ENUMERATED IN ADVANCE

1. **Market-bound (the task's "position-bound") and attainable.** More
   distinct qualifying markets, entered by the existing cohort or by
   newly-qualifying traders, would resolve the CI within the 12-month
   horizon. This is the one outcome that would retroactively justify
   *continuing* to invest in market-population growth — the discovery-gap
   sweep's original premise — but the sweep is closed
   ([[project_limit_restore_and_sweep_closure]]); this outcome would imply
   a *different*, narrower lever (e.g. `backfill_market_dates.py`'s
   Geo/Elec-priority ordering, already shipped) is the relevant one, not a
   new sweep.
2. **Market-bound but not attainable.** Answerable in principle, not in
   practice at the observed rate. Follow-on: state the actual required
   multiple of today's rate explicitly, and treat the thesis as
   **parked**, not falsified — re-check only if the underlying rate
   changes materially (e.g. a new election cycle), not on a fixed
   calendar cadence.
3. **Trader-bound.** More markets do not help; the constraint is the
   number of skilled, cohort-qualifying traders. The strategy must change
   from "wait for more data" to either (a) loosening the cohort
   qualification criteria (significance-95, M≥10, edge≥0.02) — itself a
   new, separately pre-registered decision, not a default fallback — or
   (b) accepting the null result as the answer and closing this thesis
   line.
4. **Mixed.** Both dimensions contribute materially (§2's separation rule
   fails to call either bound). Report both `share_trader`/`share_market`
   and treat as **inconclusive for a single-lever strategy** — a
   combined-lever attainability calculation would need its own
   pre-registration, not an ad-hoc extension of this one.
5. **Inconclusive.** Specify in advance what would make it conclusive:
   the bootstrap fails to converge (`< reps * 0.5` valid draws, per
   `weighted_two_way_gap_bootstrap`'s own existing guard,
   `trader_skill_metric_v2d.py:206`), or the §6 falsification check fires
   (below) before the decomposition can be trusted. **"Run it again with
   different parameters" is explicitly not an acceptable resolution** —
   an inconclusive result under this pre-registration's fixed parameters
   is reported as inconclusive, and any re-run under different parameters
   is a new, separately pre-registered diagnostic.

---

## PART 6 — WHAT WOULD FALSIFY THE DIAGNOSTIC ITSELF

Per §0.4, no primary A3 text exists to quote — the amendment below is
written against the consistently-attested substance ("a reproduction miss
== broken harness") across six session summaries, not a primary document.

**The original framing is now known to be actively wrong in a way that
would have permanently blocked Track 2.** §0.5/§0.6 verified this session:
even a structurally different (larger) proxy cohort shows the qualifying
population growing from an order of 3,000 to an order of 11,000 positions
over three weeks, almost entirely via ordinary resolution of
already-existing positions rather than new entries. A literal "does the
diagnostic reproduce 3,032/120/+0.0316 exactly" check is close to
guaranteed to fail by a wide margin at run time — for reasons that are
expected and (mostly) benign, not evidence of a broken harness. Treating
that as a stop condition, as originally drafted, would have made Track 2
unrunnable forever.

**Amended rule, fixed now, in two parts — magnitude AND attribution
(mirroring the audit's own UNREPRODUCIBLE-vs-DRIFTED distinction, §0.5):**

- **ACCEPTABLE DRIFT** (proceed to §2/§3): the diagnostic's Step 0
  baseline re-run (frozen cohort, `T_split`, identical method) produces a
  cohort point estimate that (a) stays within the original CI bounds
  `[-0.00881, +0.07101]`, (b) keeps the same sign (positive), (c) shows
  `n_positions` and `n_traders` **growing, not shrinking**, relative to
  3,032/120, and (d) every discrepancy of more than 10% in `n_positions`
  or `n_traders` is attributed to a **named, checked mechanism** (e.g.
  "positions transitioning from pending to resolved," verified by a count
  query, exactly as §0.5 did here) — not merely quantified and left
  unexplained. **[I, fixed thresholds — the 10% figure and the CI-bound
  criterion are judgment calls set now, not derived.]**
- **STOP** (do not proceed; report as a diagnostic-integrity failure, not
  a thesis result): the point estimate falls **outside** the original CI
  bounds, **or** flips sign, **or** `n_positions`/`n_traders` **decrease**
  relative to 3,032/120 (would indicate data loss or corruption, not
  accrual — never expected under ordinary operation), **or** a
  >10%-magnitude discrepancy remains unattributed after a genuine
  attribution attempt (mirroring the audit's own bar, not a lower one).

Given §0.5/§0.6's proxy findings, the diagnostic's Step 0 divergence check
is *expected* to show large `n_positions`/`n_traders` growth — that is not,
by itself, a STOP condition under this amended rule, provided it is
positive-sign, within bounds, and attributed. This is the whole point of
fixing the rule now, before any number exists.

---

## PART 7 — WHAT THIS DIAGNOSTIC DOES NOT DO

Track 2 does not re-measure the thesis, does not supersede the result of
record (`metric_v2f_oos_result`, generated 2026-08-15, commit `eaeabbc`),
and does not produce a corrected point estimate or CI for the published
cohort/placebo result. It answers a narrower, forward-looking question:
whether *more* data, along the frozen design, could ever resolve the
existing null result — not what today's number "really" is.

The second measurement (§E of the original pre-registration) is a
separate, already-pre-registered, still-unrun diagnostic, not superseded
or subsumed by this one. `2026-09-04-thesis-population-lineage.md:281`
**[V]**: re-running §E today would move the cohort-vs-placebo gap by about
**−0.0003** (the 242 markets added since 08-16 contribute "4.2%" new
material to the cohort's OOS positions, "3.6%" to the placebo's) — not
urgent, and not addressed further here.

---

## PART 8 — REPRODUCIBILITY

- **Committed script:** the diagnostic must live at a named, version-controlled
  path (e.g. `scripts/track2_ci_power_diagnostic.py`) — not created by
  this pre-registration, named here so the result document can point to
  it.
- **Seed:** `42`, matching `trader_skill_metric_v2f.py`'s `SEED` — for
  comparability with the persisted result, not an independent choice.
- **The gap this pre-registration explicitly requires the diagnostic to
  close, before anything else:** persist the true 148-trader
  presplit-qualifying cohort and its 148 matched controls as their own
  table (e.g. `metric_v2f_objective2_cohort`), addressing the exact,
  named gap the 08-16 audit found ("there is no way to prove today's 148
  are last month's 148") and this session's own proxy-cohort workaround
  had to route around. Every subsequent re-run of this diagnostic must
  compare against that persisted list, not re-derive it fresh each time.
- **Durable artifact:** a JSON file under
  `data/characterizations/track2_ci_power_<UTC-timestamp>.json` (first-repo
  convention used elsewhere in this arc), recording: the reconstructed
  cohort/control trader lists (or a reference to the persisted table
  above), `T_split`, `weight_fn`, `reps`, `seed`, the three bootstrap
  widths and `share_trader`/`share_market`, the §2 classification, the §3
  `K_required` (only if the §3 validity limit holds), the §4/§6 verdicts,
  and the git commit of both the diagnostic script and
  `trader_skill_metric_v2f.py`/`v2d.py` at run time.
- **Parameters recorded, not re-derived silently on a later run:** all of
  the above, plus the exact SQL predicates used for the structural filter
  (category, gap-clean, `entry_avg_price`, `trade_result`), so a future
  reader can tell whether a divergence is a data change or a
  method change.

---

## OPEN QUESTIONS (explicitly deferred — not answered by this document)

1. **Genuine trading decline vs. data-completeness lag** in the July/August
   proxy-cohort entry collapse (§0.6) — not resolved here. The diagnostic
   should check this before applying §4's attainability math, since the
   two explanations imply very different `R` values going forward.
2. **Cohort staleness:** should the diagnostic reconstruct the true
   148-trader cohort using pre-split data *as it stood on 08-15* (for
   comparability with the result of record) or *as it stands today* (a
   different population, given ongoing backfill)? This choice materially
   changes both the decomposition and the projection and is not decided
   here.
3. **The §2 mixed/bound cutoffs (0.65/0.35)** are a fixed judgment call,
   not a derived number — open to revision on review before the
   diagnostic runs, not after.
4. **Attribution bar for STOP (§6):** whether a 10% discrepancy threshold
   is the right level, versus the audit's own (stricter, row-level)
   standard, is a judgment call stated here for review, not a settled
   methodological result.
