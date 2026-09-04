# Relevance Classifier — Formal Validation Gate Result

**Date:** 2026-09-03 (run) / 2026-09-04 (record completed). **Status:
MEASUREMENT COMPLETE, ADJUDICATION NOT YET DONE, NO GATE VERDICT.**
Precision (§3.9) passes on all three measured quantities. Recall (§3.8)
fails on overall relevance recall and on every one of the six per-stratum
cells; directional agreement passes, narrowly. Per §3.11.4, a partial pass
is itself a FAIL and there is no shipping-for-one-use-only carve-out absent
pre-registration — but this document does not declare that verdict, because
the §3.10 formal adjudication (which the design assigns to the human
operator, Oscar, not to this task) has not been run. What follows is the
complete factual record of both runs, exactly as measured, with no
adjudication and no overall pass/fail call.

This section was originally written and committed-in-intent BEFORE a single
real `classify_batch()` call against gate or corpus data, per the task's own
discipline requirement: restate every threshold before generating a single
result, so nothing here can be a post-hoc reinterpretation of what was
already seen. That restatement (§0 below) is unchanged from before either
run executed.

**Design:** `2026-08-31-relevance-classifier-design.md` (e601648) §3.8-3.11.
**Classifier:** `monitoring/relevance_classifier.py` +
`relevance_classifier_prompt.py` (first-repo `5d2a090`), unmodified in this
task. **Gate sets:** `gate-sets-2026-09-01/` (frozen `26cb147`, labelled
`f75e1ea`), unmodified in this task. **Gate-run script:**
`scripts/run_relevance_gate.py` (first-repo, this task) — imports and calls
`classify_batch()`; does not modify the prompt, wrapper, or pre-filter;
writes no `markets`/`category_source`/`category_classification_log` rows,
only its own output artifacts under
`data/characterizations/relevance_gate_2026-09-03/`.
**Tagging:** `[V]` verified this session; `[I]` inferred/judgment call.
Every claim in the task prompt treated as a hypothesis.

---

## 0. THE FIXED THRESHOLDS (§3.8-3.11, restated before any run)

These are quoted/paraphrased from the design doc, not reinterpreted. Where
my wording differs from the task prompt's own restatement, I follow the
design doc's text, per the task's explicit instruction.

**§3.8 — Recall, against the corpus already `category IN
('Geopolitics','Elections')`:**
- **Overall relevance recall** = fraction of the corpus the classifier
  calls Geopolitics or Elections (i.e., NOT NotRelevant). **Threshold: ≥ 95%.**
- **Per-stratum relevance recall**, computed separately for each of 6 cells
  = {Geopolitics, Elections} × {live_monitoring, historical_backfill,
  gamma_backfill} (background_backfill/gap_recovery folded into the
  nearest stratum per the design's own words — this script folds them into
  historical_backfill, a judgment call stated in §1 below, not verified
  design text). **Threshold: ≥ 95% in EVERY cell** — the design is explicit
  that a systematic blind spot in one cell cannot be averaged away by good
  performance elsewhere.
- **Directional agreement** = of the rows the classifier calls relevant
  (Geopolitics or Elections, either one), the fraction whose classifier
  category matches the market's *stored* category. **Threshold: ≥ 90%**
  (design's own stated reasoning for the lower band: the Geo/Elections
  boundary is genuinely fuzzy — a tariff or shutdown market is defensibly
  either).

**§3.9 — Precision, false positives on known negatives:**
- **Classifier false-positive rate on `set_a`** (150 markets, the
  deterministic-template EXCLUDE bucket, hand-labelled 0/150 Relevant) =
  fraction the classifier calls Geopolitics or Elections. **Threshold: ≤ 2%
  (≤ 3 of 150).**
- **Classifier false-positive rate on `set_b`** (150 markets, the
  ambiguous RESIDUAL bucket, hand-labelled 6/150 Relevant) = fraction of
  the **hand-labelled-NotRelevant** rows (144 of the 150) the classifier
  calls Geopolitics or Elections. **Threshold: ≤ 10% (≤ 15 of 150** — the
  design states the threshold as a fraction of the 150-row set, not of the
  144 true-negative subset; both denominators are reported below so the
  distinction is visible, and the design's literal "≤ 15 of 150" is what
  decides pass/fail).
- **Pre-filter false-exclusion rate**, on `set_c` (200 markets the
  deterministic pre-filter EXCLUDEs) = fraction that are hand-labelled
  Relevant on inspection. **Threshold: ≤ 0.5% (≤ 1 of 200).** This is a
  measurement of the **pre-filter's** exclusion decision against
  hand-labels, already computed in `gate-sets-2026-09-01` (0/200 Relevant,
  0% — PASS, established before this task). Per the task's own framing,
  this gate run additionally runs `classify_batch()` over `set_c` as a
  **corroborating** check — does the LLM's independent judgment also call
  these 200 markets NotRelevant — not a re-derivation of the official
  figure.

**§3.10 — Adjudication:**
- A disagreement = classifier output ≠ stored label (§3.8 population) OR
  classifier output ≠ hand label (§3.9 population).
- Rubric (fixed, same as the gate sets' own labelling rubric — see
  `relevance_classifier_prompt.py`'s category definitions, drafted to
  match this exactly): **Elections** = resolution turns on a
  vote/candidate/seat/primary/nomination/coalition/party-leadership
  outcome, OR on a declared political figure's official conduct in
  political capacity (including "will X say/post" appearance-props scoped
  to a political event/role — matches M9's convention). **Geopolitics** =
  resolution turns on state action, armed conflict, diplomacy, sanctions,
  treaties, territorial control, or an international-relations event.
  **Relevant** = Elections ∨ Geopolitics; **NotRelevant** = everything
  else. Geo-vs-Elections ambiguity: the gate scores *relevance*, so any
  relevant call counts as a directional match; the adjudicator notes it as
  "boundary" and moves on. Evidence usable: title + slugs, NOT the stored
  label (that is what is being adjudicated).
- Sample: a random 50 disagreements, stratified ~25 from the §3.8
  mismatch set and ~25 from the §3.9 mismatch set (fewer if either pool has
  fewer than 25 — reported explicitly if so, not padded).
- **Genuine classifier-error rate** = fraction of the 50 where the
  adjudicated truth matches the stored/hand label (i.e. the classifier was
  actually wrong, not the old label). **Threshold: ≤ 20% (≤ 10 of 50).**
  Above 20% ⇒ the disagreements are the classifier failing, not old labels
  being sloppy ⇒ **gate FAILS.**
- Single-adjudicator safeguard: a genuinely-unsure call is recorded as
  "classifier error" (ties break against the classifier).
- **This task's adjudication is explicitly PROVISIONAL** — the design
  names Oscar as the human adjudicator (§3.10: "who decides: the human
  operator running the gate... per this project's decision-record
  convention, Oscar"). Section 5 below applies the rubric mechanically and
  reports a proposed reading, clearly marked as not a substitute for
  Oscar's adjudication.

**§3.11 — What a FAIL means (restated, not to be softened after seeing
results):**
- **Any** threshold above missed, by any margin, is a FAIL. **No partial
  credit — a near-miss is not rounded to a pass.**
- Partial pass is *also* a FAIL: "recall passes but precision fails" (or
  vice versa) does not license shipping the classifier for one use and not
  another, because that two-gate split was not pre-registered before any
  result existed (design §3.11.4). One gate, pass-or-abandon.
- On FAIL: **STOP.** Do not propose a fix. Do not suggest tuning. Name
  exactly which threshold failed and by how much, and stop. This corpus
  (the recall corpus + the 300 §3.9 negatives + the 200 §3.9 pre-filter
  exclusions) is then **spent** — it must not be re-measured against a
  revised classifier.
- The **only** permitted next step after a FAIL is exactly one of: **(a)
  abandon** the classifier for this population (a valid, expected outcome,
  not a defeat to engineer around), or **(b) one fresh-corpus retry**, and
  only if the failure is a narrowly-diagnosed, purely mechanical bug (e.g.
  a prompt-formatting error) whose fix is written down *before* any new
  result is seen, run against a freshly-drawn, independently-relabelled
  validation set, same thresholds, one retry maximum. A second failure ⇒
  abandon.
- This task's own instructions add: if a FAIL occurs, this doc states the
  failure and stops — it does not attempt (a) or (b), those are Oscar's
  decision to make, informed by this doc.

---

## 2. RUN 2 — PRECISION (set_a / set_b / set_c, `labels.csv`) `[V]`

Run first (before Run 1's much longer recall pass) to validate the
end-to-end pipeline on real LLM calls at a manageable scale. Executed via
`scripts/run_relevance_gate.py --stage precision`, real `classify_batch()`
calls, no dry-run. 500/500 markets classified, **zero errors** (no
network/parse/vocabulary failures — see `monitoring/relevance_classifier.py`'s
`category=None` error convention, none triggered). Slugs: 62/500 already
staged (from `relevance_slug_staging`, carried in `labels.csv`), 438/500
fetched live this run (428/438 found; 10/438 not_found — title-only for
those, expected, matches the design's characterisation of non-conditionId-
shaped ids in the residual population). Real per-batch latency: ~26.5s per
20-market batch on this hardware (25 batches, 500 markets total, ~11 min
wall time after the slug fetch) — recorded here as an actual measurement,
not the design's earlier ~27s/batch estimate for the *title-only* M9 shape,
though it lands very close to it.

**Output artifact:** `data/characterizations/relevance_gate_2026-09-03/precision_results.jsonl` (500 lines, one per market, committed with this doc).

### 2.1 `set_a` — template bucket, threshold ≤ 2% (≤ 3/150)

| | count |
|---|---|
| Hand-label | 150/150 NotRelevant |
| Classifier | 149 NotRelevant, 1 Geopolitics |
| **False positives** (hand=NotRelevant, classifier=Relevant) | **1/150 = 0.67%** |

The one FP: `0x2bd86ac8...` — *"Will Czechia win on 2026-05-31?"* → classifier
said Geopolitics. This is a sports-template title (crypto/weather/sports
template family, per the pre-filter's EXCLUDE classification) that reads,
out of context, like it could be an election/international-contest
question — genuinely ambiguous on title alone without more context. Flagged
for adjudication (§4).

**§3.9 threshold (≤ 2%, ≤ 3/150): PASS** (1/150 = 0.67%, well under).

### 2.2 `set_b` — ambiguous residual, threshold ≤ 10% (≤ 15/150)

| | count |
|---|---|
| Hand-label | 144/150 NotRelevant, 6/150 Relevant |
| Classifier | 135 NotRelevant, 13 Elections, 2 Geopolitics |
| **False positives** (hand=NotRelevant, classifier=Relevant) | **9/150 = 6.00%** (9/144 of the true-negative subset = 6.25% — both reported per §0's note; the design's literal threshold is stated as a fraction of 150) |

**§3.9 threshold (≤ 10%, ≤ 15/150): PASS** (9/150 = 6.00%).

**But the 9 FPs are qualitatively concerning and central to adjudication,
not just a number that cleared a bar.** Six of the nine are markets with no
plausible political content at all misclassified as "Elections":
*"Will the Bills win the AFC East?"*, *"Bills vs. Patriots"*, *"Will the
Knicks hire John Calipari as their next head coach?"*, *"Will Tyler Shough
start Week 1 for the Saints?"* (all sports), and *"Will Elon Musk post
60-79 tweets from March 3 to March 10, 2026?"*, *"Will Saylor say
'Inflation' during his Strategy World 2025 keynote?"* (neither Musk nor
Michael Saylor is a political figure — the prompt's "will X say/post"
carve-in is written for a *declared political figure's* conduct, and
appears to be firing on the sentence pattern alone, not the identity check).
A seventh, *"Will Ted Cruz post 120-139 posts from April 17 to April 24,
2026?"*, involves an actual senator but a generic tweet-count market, not
one obviously "scoped to a political event" the way the design's carve-in
was written to cover. The remaining two — *"Will the next reconciliation
bill be passed..."* and *"Judge McConnell impeached before April?"* — are
more defensibly boundary/borderline calls (a reconciliation bill is a
legislative/political process; a judicial impeachment is government
process, arguably Elections-adjacent, arguably not). **This pattern — the
classifier over-applying its political-figure-conduct clause to any "will X
[verb] Y" sentence shape regardless of the subject's actual identity — is
exactly the kind of thing §3.10's adjudication exists to catch, and is
carried into that section verbatim, not smoothed over here.**

Bonus (not a gated §3.9 metric, but directly relevant to §3.10's pooling):
all 6 of set_b's hand-labelled-**Relevant** rows were correctly called
relevant by the classifier (`Will Joshua Vasquez be the Republican nominee
for FL-06?` → Elections; `Will the US strike Yemen next?` → Geopolitics;
`Will a candidate win outright in Ireland's first round?` → Elections;
`Will Pelosi say "Stocks" at DNC speech?` → Elections; `Will Israel strike
≥4 countries in April 2026?` → Geopolitics; `Will Bill Clinton say
"Hillary" at DNC speech?` → Elections) — 0 false negatives on the known-
relevant subset of set_b.

### 2.3 `set_c` — pre-filter false-exclusion, corroboration only

**Official §3.9 pre-filter false-exclusion figure** (already established in
`gate-sets-2026-09-01`, by hand-label alone, before this task): **0/200 =
0%** — **PASS** against the ≤ 0.5% (≤ 1/200) threshold. This task did not
re-derive that figure; it is unchanged.

**Corroboration run this task performed:** `classify_batch()` over all 200
`set_c` markets — **0/200 called Geopolitics or Elections**, i.e. the LLM's
independent judgment agrees with the pre-filter's exclusion decision on
100% of `set_c`. This is consistent with (not a substitute for) the
official hand-label figure.

### 2.4 All precision-run disagreements (pooled for §3.10)

`classifier relevant/not-relevant call ≠ hand_label` across all 500 rows:
**10 total** (1 from `set_a`, 9 from `set_b`, 0 from `set_c`) — the full
list is the 10 rows itemised in §2.1/§2.2 above. This is smaller than the
design's "~25 from 3.9" expectation for the 50-row adjudication draw; see
§4 for how the draw is adjusted.

---

## 3. RUN 1 — RECALL (the corpus `category IN ('Geopolitics','Elections')`) `[V]`

**COMPLETE.** Launched via `scripts/run_relevance_gate.py --stage recall`,
real `classify_batch()` calls, no dry-run. Completed **2026-09-03T20:28:46Z**
(file mtime on `recall_results.jsonl`, taken as the completion timestamp).
12,052/12,052 rows classified, **zero errors** (no `category=None` rows).

**Output artifact:**
`data/characterizations/relevance_gate_2026-09-03/recall_results.jsonl`
(12,052 lines, one per market, committed with this doc).

**Corpus-size drift, verified not assumed:** the design doc (08-31) and the
09-01 gate-sets manifest both cite **11,967** (7,937 Elections, 4,030
Geopolitics). A live query against the current DB (2026-09-03) returns
**12,052** (8,005 Elections, 4,047 Geopolitics) — **+85 rows**, consistent
with M9's nightly classification continuing to run in the ~3 days since
08-31 (M9 was never paused; per design §2.8 it stays live until this gate
passes). This task measures against the **current, live 12,052**, per the
task's own instruction to run "over all 11,967 markets **currently**
category IN (...)" — the number is a label carried from the design doc, not
a frozen population; using the live set is the faithful reading of
"currently."

**Stratification, as computed:** origin (`data_source`) mix, folded per
design §3.8's own instruction that `background_backfill`/`gap_recovery` are
"too small... folded into nearest" (design does not say which is nearest —
this script's judgment call, stated before any result was seen: fold both
into `historical_backfill`, since both are backfill-shaped origins, not live
ingest):

| Stratum | Elections | Geopolitics |
|---|---|---|
| `live_monitoring` | 4,691 | 2,901 |
| `historical_backfill` (+`background_backfill`+`gap_recovery`) | 1,424 | 538 |
| `gamma_backfill` (`_2026-07-02` + `_tier2_2026-07-06`) | 1,890 | 608 |
| **Total** | **8,005** | **4,047** |

All 6 cells have ≥ 538 rows — none is "too small to report meaningfully"
(design's own escape hatch for a cell this task would otherwise have had to
invoke; not needed here).

### 3.1 Classifier verdict counts (all 12,052 rows)

| Classifier call | Count |
|---|---|
| Elections | 8,031 |
| Geopolitics | 2,858 |
| NotRelevant | 1,163 |
| **Total** | **12,052** |

(Confidence: 12,017 HIGH, 35 LOW — LOW confidence rows are not treated
specially by any threshold below; the design does not carve out a separate
LOW-confidence gate.)

### 3.2 Overall relevance recall — §3.8, threshold ≥ 95%

Relevant (Elections ∪ Geopolitics) calls: **10,889 / 12,052 = 90.35%**.

**§3.8 threshold (≥ 95%): FAIL.** Shortfall: would need ≥ 11,450 relevant
calls to clear 95%; actual is 10,889 — **561 rows short**. This is not a
near-miss margin; 90.35% is over 4.6 points below the bar.

### 3.3 Per-stratum relevance recall — §3.8, threshold ≥ 95% in EVERY cell

| Stratum × stored category | Relevant / Total | Recall | vs. 95% threshold |
|---|---|---|---|
| `live_monitoring` × Elections | 4,194 / 4,691 | 89.41% | **FAIL** (short 263) |
| `live_monitoring` × Geopolitics | 2,682 / 2,901 | 92.45% | **FAIL** (short 74) |
| `historical_backfill` × Elections | 1,317 / 1,424 | 92.49% | **FAIL** (short 36) |
| `historical_backfill` × Geopolitics | 493 / 538 | 91.64% | **FAIL** (short 19) |
| `gamma_backfill` × Elections | 1,656 / 1,890 | 87.62% | **FAIL** (short 140) |
| `gamma_backfill` × Geopolitics | 547 / 608 | 89.97% | **FAIL** (short 31) |

**§3.8 per-stratum threshold: FAIL in all 6 of 6 cells.** This is exactly
the pattern the design's per-stratum requirement exists to catch and the
overall-recall number alone would have obscured only mildly (overall is
already a clear fail here, but the per-cell view shows the miss is uniform
across strata, not concentrated in one — see Phase 2 for whether it
concentrates on some other axis instead). Worst cell: `gamma_backfill` ×
Elections at 87.62%. Best cell: `historical_backfill` × Elections at
92.49%. No cell reaches 95%; none is close (the smallest shortfall, 19 rows
in `historical_backfill` × Geopolitics, is still a real miss, not a
rounding artifact).

### 3.4 Directional agreement — §3.8, threshold ≥ 90%

Of the 10,889 rows the classifier calls relevant, agreement with the
market's *stored* category (Elections vs. Geopolitics, not relevance):
**9,813 / 10,889 = 90.12%**.

**§3.8 threshold (≥ 90%): PASS**, by a narrow margin — 90% of 10,889 rounds
up to 9,801; actual agreement is 9,813, a margin of **12 rows / 0.12
percentage points** above the minimum passing count. This is a genuine pass,
not a rounded one, but the margin is thin enough to flag: a handful of
additional Geo/Elec direction flips would fail it.

Mismatch breakdown (1,076 total directional mismatches, all counted against
the pass above): stored **Geopolitics**, classifier said **Elections**: 970.
Stored **Elections**, classifier said **Geopolitics**: 106. The mismatch is
heavily one-directional — the classifier is far more likely to call a
stored-Geopolitics market "Elections" than the reverse. This asymmetry is
noted here as a fact; it is not adjudicated in this document (§4).

### 3.5 §3.8 threshold summary

| Metric | Result | Threshold | Verdict |
|---|---|---|---|
| Overall relevance recall | 90.35% | ≥ 95% | **FAIL** |
| Per-stratum relevance recall (6 cells) | 87.62%–92.49% | ≥ 95% each | **FAIL** (6/6 cells) |
| Directional agreement | 90.12% | ≥ 90% | **PASS** (narrow) |

Per §3.11.1, any threshold missed is a FAIL of the gate as a whole, and
per §3.11.4 a partial pass (here: directional agreement passing while
overall and per-stratum recall fail) does not create a scoped pass for one
use — it is still one gate, and it has a miss in it. No overall verdict is
recorded in this document; see §5.

---

## 4. §3.10 ADJUDICATION — NOT YET DONE

The design (§3.10) names the human operator running the gate — per this
project's decision-record convention, **Oscar** — as the adjudicator of
record. This task's own instructions (quoted in §0 above) direct that this
document record the measurement in full and explicitly **not** perform that
adjudication or declare a verdict.

**Status: adjudication not started in this document.** The disagreement
pools it would draw from are, however, fully characterized by the
measurement above and available for Oscar to sample from:
- §3.8 mismatch pool: the 1,163 `NotRelevant` calls (§3.2) plus the 1,076
  directional mismatches (§3.4) — these overlap in kind (both are "classifier
  output ≠ stored label") but are counted separately above per their
  distinct thresholds; the design's §3.10 draw treats all classifier-output
  ≠ stored-label rows as one pool to sample 25 from.
- §3.9 mismatch pool: the 10 precision disagreements itemised in §2.4.

A separate, explicitly-provisional diagnostic pass over a 100-row sample of
the §3.8 `NotRelevant` pool (not the formal 50-row §3.10 draw, and not a
substitute for it) is reported in
`brain/decisions/2026-09-04-gate-recall-diagnosis.md`, produced as a
distinct task from this document.

---

## 5. OVERALL GATE STATUS

**No overall verdict is recorded.** Per the design (§3.10), the gate is not
decided until the adjudication is complete, and per this task's explicit
instruction, that adjudication is Oscar's to perform, not this document's.

What is established as fact, without interpretation:
- Precision (§3.9): **PASS** on all three measured quantities (§2).
- Recall (§3.8): **FAIL** on overall relevance recall and on all 6 of 6
  per-stratum cells; **PASS** (narrowly) on directional agreement (§3).
- Per §3.11.1 and §3.11.4 of the design, a miss on any threshold — and a
  partial pass generally — would ordinarily mean the gate as a whole fails;
  this document deliberately stops short of declaring that, because §3.10
  adjudication has not run and this task's instructions reserve that
  declaration for after adjudication.
- The two possible actions on a FAIL (§3.11.3: abandon, or one narrowly-
  diagnosed mechanical-bug retry) are Oscar's decision, informed by this
  document and by the diagnostic pass in
  `2026-09-04-gate-recall-diagnosis.md`. Neither is proposed or applied
  here.
