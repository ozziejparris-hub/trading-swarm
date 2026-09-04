# Relevance Classifier — Recall-Failure Diagnostic (provisional, read-only)

**Date:** 2026-09-04. **Status: DIAGNOSTIC ONLY — NOT the §3.10 formal
adjudication, NOT a gate verdict.** Everything below is a provisional
reading applied by this task, explicitly marked as such throughout, per the
task's own instruction. It exists to inform Oscar's §3.10 adjudication and
the §3.11 abandon-vs-retry call, not to make either decision.

**Design:** `2026-08-31-relevance-classifier-design.md` (e601648) §3.8-3.11.
**Gate result:** `2026-09-03-gate-result.md` — overall recall 90.35%
(FAIL, ≥95% required), all 6 per-stratum cells FAIL, directional agreement
90.12% PASS. This document diagnoses the shape of that failure: 1,163 of
12,052 recall-corpus markets (9.65%) were called `NotRelevant` by the
classifier despite a stored `Elections`/`Geopolitics` label.

**No re-run performed.** Everything below is read from the already-committed
`data/characterizations/relevance_gate_2026-09-03/recall_results.jsonl`
(first-repo `a7aa610`) plus one read-only DB query (`markets.category_source`)
and one read-only grep of `logs/category_backfill.log` (M9's own run log).
No `classify_batch()` call was made, no prompt/wrapper/pre-filter file was
touched, no `category`/`category_source`/`category_classification_log` row
was written.

---

## 1. Sample and seed

Population: the 1,163 `NotRelevant` calls in the recall corpus, cross-tabbed
by the same six §3.8 cells (stratum × stored category):

| Cell | Count | % of 1,163 |
|---|---|---|
| `live_monitoring` × Elections | 497 | 42.73% |
| `live_monitoring` × Geopolitics | 219 | 18.83% |
| `gamma_backfill` × Elections | 234 | 20.12% |
| `gamma_backfill` × Geopolitics | 61 | 5.25% |
| `historical_backfill` × Elections | 107 | 9.20% |
| `historical_backfill` × Geopolitics | 45 | 3.87% |

**Seed: `20260904`** (today's date, chosen before drawing, no retries).
Allocation to 100 by proportional share with **largest-remainder rounding**
(not naive floor/ceil, so the 100 total is exact): `live_monitoring`×Elections
43, `gamma_backfill`×Elections 20, `live_monitoring`×Geopolitics 19,
`historical_backfill`×Elections 9, `gamma_backfill`×Geopolitics 5,
`historical_backfill`×Geopolitics 4 — sums to 100. `random.seed(20260904)`,
then `random.sample()` drawn independently within each cell from its pool.
**Composition drawn matches the allocation exactly** (verified: each cell's
sample count equals its target).

## 2. Committed CSV

`data/characterizations/relevance_gate_2026-09-03/notrelevant_diagnostic_sample_100.csv`
(first-repo, committed with this doc) — 100 rows, columns: `idx, market_id,
title, market_slug, event_slug, event_title, stratum, stored_label,
classifier_call, batch_position, title_len, has_slug_context,
m9_keyword_path, provisional_verdict, subtype, provisional_reason`.
`batch_position` is the market's 1-indexed position within its 20-market
`classify_batch()` call, recovered from `classifier_raw`'s own `id` field —
not re-derived, just read back. `m9_keyword_path` says whether the
market_id appears in `logs/category_backfill.log` with a non-dry-run
`CLASSIFY` line (i.e., M9's `backfill_market_categories.py` actually applied
this market's stored category).

## 3. Provisional rubric application (§3.10 rubric, PROVISIONAL — not Oscar's adjudication)

Applied the design's §3.10 rubric (title + slugs, not the stored label) to
each of the 100 rows myself. **This is diagnostic, explicitly not a
substitute for the formal 50-row §3.10 adjudication**, which draws from a
different, smaller pool (25 from §3.8's mismatch set, 25 from §3.9's) and is
Oscar's to perform.

| Verdict | Count | % |
|---|---|---|
| **(a) CLASSIFIER MISS** — stored label right, classifier wrong | **79** | **79%** |
| **(b) STORED-LABEL ERROR** — stored label wrong, classifier right | **8** | **8%** |
| **(c) GENUINELY AMBIGUOUS** — defensible either way | **13** | **13%** |

**This is the number that matters, per the task's own framing: most
disagreements are (a), not (b).** The 1,163-`NotRelevant` figure — and the
90.35% recall miss — is not an artifact of stale/noisy ground truth; on this
sample, the classifier is genuinely under-calling relevance on markets that
are, by the design's own rubric (including its explicit M9-derived "will
X say/post" carve-in), real Elections/Geopolitics markets. Even a
maximally classifier-favorable reading — folding all 13 (c) rows in with
(b) — still leaves 79/92 = 85.9% as clear misses. The gate's recall failure
is real, not a labelling artifact.

The 8 (b) rows are themselves informative and worth naming plainly, since
they show two distinct, already-known M9 labelling defects, both **pre-existing
in the stored corpus, not introduced by this classifier**: naive keyword
substring matches (country names inside sports team/tournament names —
"Will Ukraine win?" [Euro 2024 soccer], "Will IR Iran win?" [FIFA]; "election"
appearing as a date reference in an unrelated crypto market) and
non-conduct name mentions (Trump's name in someone else's manifesto, a
Google search-popularity ranking, a celebrity performing at an event Trump
also appears at). None of these 8 argues for a bigger classifier problem —
if anything the classifier correctly declined all 8.

The 13 (c) rows cluster heavily (10 of 13) around **Trump approval-rating
tracking markets** (`Trump's approval rating be X% on DATE`, `Trump
approval Up/Down this week`) — a market type the design's rubric text does
not clearly place on either side: it is not a vote outcome and arguably not
"official conduct," yet it is unmistakably political-figure content. This
ambiguity is a rubric-text gap, not a classifier defect either way, and is
flagged here for Oscar rather than resolved.

## 4. Clustering analysis (among the 79 (a) CLASSIFIER MISS rows)

| Axis | Finding | Diagnostic? |
|---|---|---|
| **Slug context** | 78/79 misses had full `market_slug`/`event_slug`/`event_title` context; only 1/79 was title-only. Sample-wide, only 1/100 rows were title-only at all. | **No** — title-only rows are too rare in this sample to explain anything, and the one title-only row is not itself a miss driver; the classifier is missing markets it had full context for. |
| **M9 keyword-path origin** | 78/79 misses (99%) came from a non-dry-run M9 `CLASSIFY` log line; 99/100 of the *whole sample* did too. | **No** — this is the sample-wide baseline, not a differential. Virtually the entire recall corpus is M9-sourced; this axis carries no separating signal. |
| **Stratum** | Misses: 52 `live_monitoring`, 16 `gamma_backfill`, 11 `historical_backfill` — proportional to each stratum's share of the 100-sample, not concentrated in one. | **No** — matches §3.3's finding that all 6 per-stratum cells fail by comparable margins; the miss is not a single-stratum problem. |
| **Title length** | Misses average 67.3 chars vs. 63.9 for the full 100-sample. | **Weak/no** — a ~3.4-char difference is not a meaningful effect size. |
| **Market subtype** | 18 distinct subtypes among the 79 misses. Two largest: `say/post-prop` (31, the explicit "will X say/announce/post" carve-in) and `truth-post-count` (14, Trump's Truth Social post-count markets) = 45/79 = 57%. The remaining 34/79 (43%) spread across 16 other subtypes with no shared surface form: presidential pardons, cabinet-departure markets, executive orders, a Senate roll-call vote, a referendum, military-strike markets, diplomatic meetings, a presidential candidacy announcement, state economic-policy actions. | **Partially** — the "say/post" pattern is over-represented, but a slim majority reading requires the *rest*, which is genuinely heterogeneous. A fix targeting only the say/post carve-in would leave over 40% of this sample's misses uncorrected. |
| **Batch position** (`classifier_raw`'s own per-batch `id`, 1–20) | **The one real, quantified structural signal.** Corpus-wide (all 12,052 rows, not just the sample): `NotRelevant` rate is 5.6% averaged over batch positions 1–5, rising to 12.2% averaged over positions 16–20 — **more than double**, over ~3,000 rows per position-group (this is not sampling noise). Within the 100-row diagnostic sample, misses average batch position 13.2 vs. 10.2 for non-misses. | **Yes, but partial** — see §5. |

## 5. Is this a §3.11(b) narrowly-diagnosed mechanical bug, or §3.11(a) abandon?

**§3.11(a) — abandon — is what the evidence supports. Stated honestly, not
constructed to sound mechanical:**

1. **The failure is majority-(a), not majority-(b).** 79% of the sampled
   disagreements are the classifier being wrong, not the corpus being
   stale. This alone answers the question this diagnostic was built to
   answer: the recall gate did not fail because of dirty ground truth.

2. **The miss causes are substantively diffuse.** Even the largest single
   pattern (the "say/post" appearance-prop carve-in, explicit in both the
   design's rubric text and the classifier's own prompt — see
   `monitoring/relevance_classifier_prompt.py`'s Elections definition,
   which spells out "will X say/announce/post... treat these as Elections,
   not NotRelevant") only accounts for 31/79 = 39% of misses. Widening to
   include the closely-related post/tweet-count variant still leaves 34/79
   = 43% of misses in 16 other, structurally unrelated subtypes (pardons,
   cabinet moves, a Senate vote, a referendum, military strikes, diplomatic
   meetings). A "narrowly diagnosed, mechanical" bug, per the design's own
   example ("a prompt-formatting error"), is not what a failure spread this
   wide across unrelated content types looks like.

3. **The one real structural signal — batch-position degradation — is a
   statistical tendency of the local 30B model under batched inference, not
   a discrete, provably-correct bug with a fix writable in advance.** The
   corpus-wide gradient (5.6% → 12.2% NotRelevant rate from batch position
   1 to 20) is real and worth recording, but: (a) even the *best* position
   (1–5, 5.6% NotRelevant / ~94.4% relevance-call rate on those rows) is
   still short of the ≥95% bar this specific slice would need to clear on
   its own — the degradation explains a *gradient*, not the *baseline*
   shortfall; (b) the design's §3.11(b) bar requires a fix "written down
   before any new result is seen" — "shrink the batch size and see if
   recall clears 95%" is not such a fix, it is a new hypothesis that would
   itself require a fresh validation run to confirm, which is exactly the
   "iterate until it passes" pattern §3.11 rules out for a retry. A retry
   under (b) needs the fix's correctness argued on paper first; "try a
   smaller batch and re-measure" is not that.

4. **Net:** the recall shortfall is real (not a ground-truth artifact),
   large (561 rows short of the overall bar, all 6 cells failing by
   19–263 rows), and diffuse in cause (many unrelated content types miss,
   plus a partial-but-insufficient positional effect). That is the profile
   §3.11 describes as "abandon," not the profile it reserves for a one-shot
   retry.

This is a provisional reading for Oscar, not this document's call to make —
§3.11 itself reserves the abandon/retry decision for the human operator,
informed by this diagnostic and by the (not-yet-performed) formal §3.10
adjudication in `2026-09-03-gate-result.md`.

---

*Everything in §3–5 is explicitly provisional: one adjudicator (this task),
not Oscar; a 100-row diagnostic sample of one disagreement type
(§3.8 `NotRelevant` calls only), not the formal 50-row §3.10 draw across
both §3.8 and §3.9's mismatch pools. Both remain to be done before any gate
verdict is recorded.*
