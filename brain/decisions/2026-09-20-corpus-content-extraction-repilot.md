# Corpus content extraction — re-pilot on the 6 schema failures

**Date:** 2026-09-20. Second pass, following the same day's initial 12-document pilot
(`brain/decisions/2026-09-20-corpus-content-extraction-pilot.md` — this document assumes
that one as read). That pilot found 6 of 12 documents returned every field as a flat list
of bare strings instead of `{claim, quote}` objects — not length-correlated, content
accurate, wrong shape roughly half the time — and that 80 of 193 quotes were unverified
by exact substring, all 80 manually traced to genuine content reformatted out of markdown
(table rows rewritten as prose, bold markers stripped, headings merged with following
lines). This document tests two isolated fixes against exactly the documents that failed,
rather than assuming they work.

---

## Fix 1 — one worked example, isolated

Added a single fully-populated `{"claim": ..., "quote": ...}` example to
`EXTRACTION_PROMPT` (`scripts/corpus_content_extractor.py`), generic and clearly marked as
illustration, not document content. Nothing else about the instructions changed.

**Field caps were NOT also reduced as a second condition.** Considered per the task's
instruction to state reasoning either way: the worked-example fix alone raised the schema
pass rate from 0/6 to 5/6 on the failing set (below). Given that result, spending a second
full LLM pass over the same 8 documents to test whether smaller caps *also* help would not
have changed the decision this pilot exists to inform, and duplicating an ~18-minute-per-
document run for a question the first result already answers well enough was not judged
worth the compute. If the pass rate had stayed materially below 100%, a caps-reduction
condition would have been the obvious next lever — it wasn't needed to reach a verdict here.

## Fix 2 — a third verification tier, reported separately

`verify_record_quotes()` gained a `structural` tier between `normalized` and
`unverified`: strips `**`, backticks, `|`, leading heading/numbered-list/bullet markers,
and collapses whitespace runs (via `_structural_strip_with_map`, a character-offset-mapped
transform so line numbers stay exact) before comparing. **Reported as its own count in
every record and every table below — never merged into `exact`.**

While building this I found and fixed a genuine bug in my own normalizer, not a leniency
added to raise the pass rate: a hyphenated word hard-wrapped across a markdown line break
(`majority-\ngenuine`) was being rejoined with an inserted space (`majority- genuine`)
instead of no separator, producing a false unverified on real, unaltered content. Fixed by
treating a hyphen immediately followed by a newline as a word-join, not a word-boundary.
Confirmed by regression-testing the four cases from the original pilot's normalizer
prototype (table-row recovery, deliberately-still-broken colon-insertion, fabrication
rejection, an ordinary numeric hyphen range) before and after the fix — all four behave
correctly.

**The predicted residual — a colon the model inserts between a table label and its value
that the source never had — is deliberately NOT closed.** Verified directly:

```
source:  | **LEGENDARY (geo)** | `geo_elo_active >= 2175 ...` |
quote:   'LEGENDARY (geo): geo_elo_active >= 2175 ...'
result:  unverified (correctly -- the colon is a real character difference)
```

---

## Run

8 documents: the 6 that failed entirely, plus 2 controls that succeeded in the first
pilot (`MASTER_HANDOVER_2026-06-10.md`, `2026-07-10-trading-swarm-deep-audit-FABLE.md`).
Same conditions otherwise: `qwen3-coder:30b-a3b-q4_K_M`, stateless per document, strict
JSON contract, hard-fail on parse error, path-based state, kill conditions unchanged.
Timeout **1,200s**, set from the first pilot's own observed maximum (814.2s) with ~1.5x
headroom — see the cost this created, below. Confirmed `daily_maintenance` had finished
(last completion 13:12 UTC; run launched 17:37 UTC, well inside the safe window) before
launching, detached via `setsid`/`nohup`/`disown`.

**Run summary:** wall 3,641.6s (60.7 min) for 8 calls, `call_seconds_min=147.8`,
`call_seconds_max=1200.1` (the one timeout), `call_seconds_mean=454.7` (including the
timeout; **348.2s across the 7 that actually returned**). RSS peak 32.5MB. 7 processed,
1 failed (timeout, not a parse or schema failure — the call itself never returned).

---

## Schema pass rate: 5/6, up from 0/6

| Document | Result |
|---|---|
| `MASTER_HANDOVER_2026-09-05.md` | ✅ valid (281.4s) |
| `MASTER_HANDOVER_2026-09-06.md` | ❌ **timed out at 1,200.1s** — the one document in this batch that finished in 119.9s *before* the fix now exceeds the new, tighter ceiling |
| `2026-08-21-discovery-gap-closure-prereg.md` (corpus's largest, 1,884 lines) | ✅ valid (1,008.7s) |
| `2026-09-05-copy-trade-decay-prereg.md` | ✅ valid (283.9s) |
| `2026-09-19-corpus-mining-rq-census-and-contradictions.md` | ✅ valid (164.1s) |
| `2026-09-20-spawn-agent-silent-failure-fix.md` | ✅ valid (147.8s) |

Every document that returned came back **fully schema-valid** — no partial or bare-string
failures at all in this batch, only the one clean timeout. The worked example works.

## Quote verification, three tiers, per document

| Document | Total | Exact | Normalized | Structural | Unverified |
|---|---:|---:|---:|---:|---:|
| `MASTER_HANDOVER_2026-09-05.md` | 29 | 0 | 19 | 6 | 4 |
| `2026-08-21-discovery-gap-closure-prereg.md` | 48 | 6 | 20 | 13 | 9 |
| `2026-09-05-copy-trade-decay-prereg.md` | 12 | 0 | 10 | 2 | 0 |
| `2026-09-19-corpus-mining-rq-census-and-contradictions.md` | 30 | 2 | 15 | 6 | 7 |
| `2026-09-20-spawn-agent-silent-failure-fix.md` | 23 | 16 | 6 | 1 | 0 |
| `MASTER_HANDOVER_2026-06-10.md` (control) | 32 | 19 | 0 | 6 | 7 |
| `2026-07-10-trading-swarm-deep-audit-FABLE.md` (control) | 31 | 17 | 0 | 14 | 0 |
| **Total** | **205** | **60** | **70** | **48** | **27** |

Verified (exact + normalized + structural): **178/205 = 86.8%**. For comparison, the
original pilot's 6 valid documents, re-verified against this same final three-tier
normalizer (not the two-tier count reported same-day): 158/193 = 81.9%. Both pilots'
underlying accuracy is in the same range; the improvement from the original pilot's
raw two-tier report (58.5%) to either of these three-tier numbers is almost entirely the
normalizer closing a measurement gap, not the extraction becoming more accurate.

## What's left unverified (27), by class — manually traced, not assumed

Sampled ~20 of the 27 directly against source (not exhaustive — noted, not hidden).

- **Majority (~13 of ~20 checked): the predicted, deliberately-uncorrected residual** —
  two-column table rows (`| **Label** | value |`) where the model inserts a colon between
  label and value that the source never had, plus a small number of sibling patterns the
  task didn't originally name but are the same class: a `**Bold**` phrase at a sentence
  boundary with a capitalization change (`adopted` for `**Adopted**`, `this` for `this` —
  case is real content, correctly not normalized away), and markdown **blockquote `>`
  markers** (not in Fix 2's stripped-character list — found in
  `2026-09-19-corpus-mining-rq-census-and-contradictions.md`'s quoting of another
  document's blockquoted section headers). Real content in every case checked; none
  fabricated.
- **2 confirmed likely fabrications**, both in `2026-08-21-discovery-gap-closure-prereg.md`
  (the corpus's largest document), both in `explicitly_open`:
  `"the exact timing of when the sweep will begin is not determined"` and
  `"the final runtime estimate after all adjustments is not yet known"`. Exhaustive
  case-insensitive search for every substantive word/phrase in both ("sweep will begin",
  "runtime estimate", "not determined" in any spelling) found **no textual basis anywhere
  in the 1,884-line source**. The other 6 items in the same field's list, on the same
  document, all verified correctly (structural or normalized) against real text. This
  looks like the model generalizing the pattern of the field's genuinely-present items
  ("X is not yet implemented/fixed") into two additional plausible-sounding but
  unsupported ones, possibly reaching toward the field's cap (8 items requested, 8
  produced, 6 real). **Not observed in the original pilot's 80 manually-traced items** —
  this is a new finding from this run, not a recurrence.
- **1 isolated word-omission**: `"(Areas 2/3, HIGH, proven)"` vs. source's
  `"(Areas 2/3, HIGH, proven posture)"` — "posture" dropped. Real content, minor genuine
  alteration, not decoration.

**No field is recommended for outright exclusion from a future full run** on this
evidence — but `explicitly_open` on long, dense documents is the one place this re-pilot
found content that doesn't trace to the source at all, and that's worth a targeted,
larger sample before trusting that field's output at full-corpus scale without spot-
checking it specifically.

## Controls: no degradation in accuracy, a real reduction in extraction breadth

| Document | Quotes before → after | Verified rate before → after |
|---|---|---|
| `MASTER_HANDOVER_2026-06-10.md` | 50 → 32 (−36%) | 74.0% → 78.1% |
| `2026-07-10-trading-swarm-deep-audit-FABLE.md` | 35 → 31 (−11%) | 91.4% → 100% |

Schema stayed valid in both; no fabrication found in either control's output; verified
rate held or improved. But **both extracted meaningfully fewer claims** with the worked
example in the prompt than without it. That is a real cost, stated plainly per
instruction rather than folded into the accuracy numbers: the fix appears to trade some
extraction breadth for (at worst) unchanged, and in these two cases improved, precision.
Whether that trade is worth it at full-corpus scale is a judgment call, not something
this re-pilot's n=2 control settles definitively.

## Projected full-corpus runtime

Corpus is now **272 documents** (`brain/decisions/**/*.md`, including the 2 `archive/`
files), up from the 265 referenced in the task. Using this run's own observed mean —
**454.7s/document, including the one timeout failure** (the defensible single number: it
already reflects the ~12.5% timeout rate observed, since `0.875 × 348.2s (mean of the 7
that returned) + 0.125 × 1,200s (the timeout ceiling) = 454.7s` is the same figure) —
projected full-corpus wall time is **272 × 454.7s ≈ 123,678s ≈ 34.4 hours**, against the
~18.6 hours the original (pre-fix) pilot's 252.2s mean would have projected. **The fix
roughly doubles the expected wall-clock cost of the full run.**

---

## Plain verdict

**Not yet good enough to commit to, as configured.** Three specific reasons, not a vague
caution:

1. **The cost changed materially.** ~34 hours, not ~18. The worked example that fixed the
   schema-shape problem also makes the model generate substantially more per call.
2. **12.5% (1/8) still failed outright** — a clean timeout, not a bad extraction, but zero
   output for that document. Projected across 272 documents at this rate, that's roughly
   **34 documents producing no anchored output at all**, before any schema or quote
   problems are even considered. This is the honest translation the task asked for if the
   pass rate stayed materially below 100% — it did, once timeouts are counted alongside
   schema failures.
3. **A new, narrow fabrication risk surfaced** in the largest document's `explicitly_open`
   field, not present in the original (smaller-schema) pilot's fully-checked sample. Two
   data points isn't enough to call a rate, but it's enough to say this specific field, on
   long documents, needs a dedicated check before the full run's output is trusted without
   spot-checking.

**What would change the verdict:** a higher timeout (the 1,200s ceiling was sized from the
*pre-fix* pilot's maximum and is demonstrably too tight for the *post-fix* prompt) tested
against documents similar in size/density to the one that failed here, and a targeted,
larger sample of `explicitly_open` items on long documents specifically, checking for the
same class of unsupported items found here. Neither was run — this re-pilot answered the
two questions it was asked to answer, not a redesigned third pilot.

## What this does not fix / did not do

- Did not run the full corpus (scope).
- Did not modify the structural index (`corpus_reader_index_v2.jsonl`) — separate artifact,
  untouched.
- Did not re-enable any paused agent.
- Did not widen the normalizer to close the colon-insertion residual or the blockquote-
  marker gap found during this run — both are named above, neither is patched over.
- Did not run a caps-reduction condition (reasoning stated above, not silently skipped).
- Did not raise the timeout past 1,200s to see whether the one failing document would
  succeed given more time — that's the natural next check, not run here.

---

*Re-pilot run 2026-09-20T17:37:11Z–18:37:53Z. `scripts/corpus_content_extractor.py`,
`brain/corpus_content_repilot.jsonl`, `brain/corpus_content_repilot_failures.jsonl`
committed alongside this document.*
