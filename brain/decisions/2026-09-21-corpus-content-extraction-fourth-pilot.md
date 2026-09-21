# Corpus content extraction — fourth pilot (constrained decoding + ceiling-framed caps)

**Date:** 2026-09-21. Recovery/completion of a run started 2026-09-20 by a session that ran
out of usage before reporting. This document reconstructs what that session did from the
committed script diff, the run artifacts, and file timestamps (no `logs/corpus_content_extractor.log`
was found — see "Gaps in this reconstruction" below), verifies the result, and closes it out.
Assumes `brain/decisions/2026-09-20-corpus-content-extraction-repilot.md` as read.

---

## What last night's session did

Diffing `scripts/corpus_content_extractor.py` against `fdb8d75` (the re-pilot commit) shows
both intended changes applied correctly and nothing else:

- **CHANGE A** — the worked example is removed from `EXTRACTION_PROMPT`; a `format` JSON
  schema (`GENERATION_SCHEMA`) was added to the Ollama `/api/generate` call; `temperature`
  changed from `0.1` to `0`. The worked example and the schema constraint are never present
  together (the dangerous double-variable state) — confirmed by reading the diff, not
  inferred.
- **CHANGE B** — every array field's `maxItems` is enforced structurally in
  `GENERATION_SCHEMA`; no field sets `minItems` anywhere (the script itself asserts this at
  import time — `assert "minItems" not in json.dumps(GENERATION_SCHEMA)` — and the diff
  confirms the assert is real, not decorative). Prose caps were reworded from "max N" to
  "up to N" ceiling framing with explicit "zero is a correct answer" language.

This is a clean, classifiable state — not the dangerous double-variable state, not a
`minItems` regression. Per the recovery task's own instructions, a script already in this
state (rather than still at `fdb8d75`) is not "proceed to make the changes" — the changes
were already made correctly, and the run below shows they were already executed. Re-running
would have discarded a valid, reproducible result for no reason, so this document verifies
and reports the existing artifacts rather than repeating the LLM pass.

Ollama version 0.22.1 (confirmed live on this box today) supports `format` with a schema
(introduced 0.3.0). No separate proof-call transcript file was found on disk, so that step
of Change A's stated verification could not be independently re-confirmed from an artifact —
but the real run's result is stronger evidence than a synthetic proof call would have been:
all 8 records below have `schema_valid: true`, including the largest, most complex document
in the set, under an unmodified adversarial prompt with the worked example removed.

## Run inventory (what exists, git state)

- `git log`: `HEAD` is still `fdb8d75` — no commit was made last night.
- `git status`: `scripts/corpus_content_extractor.py` modified but uncommitted (the diff
  above); three new files: `brain/corpus_content_fourth_pilot.jsonl` (7 records),
  `brain/corpus_content_fourth_pilot_failures.jsonl` (1 record), and
  `brain/corpus_content_fourth_pilot_supplementary_2400s.jsonl` (1 record, see below).
- No leftover process: no python/ollama process started after 2026-09-20T18:40Z, no
  resident model (`ollama ps` empty), no detached shell. Safe to treat the run as finished,
  not interrupted mid-call.
- All 8 target documents were attempted, in the order specified by the task, reconstructed
  from record timestamps:

| order | document | outcome | call time |
|---|---|---|---|
| 1 | MASTER_HANDOVER_2026-09-05.md | OK | unknown (first call, no prior timestamp) |
| 2 | MASTER_HANDOVER_2026-09-06.md | OK | 177.9s |
| 3 | 2026-08-21-discovery-gap-closure-prereg.md | **TIMED OUT at 1200.6s** | — |
| 4 | 2026-09-05-copy-trade-decay-prereg.md | OK | 574.5s |
| 5 | 2026-09-19-corpus-mining-rq-census-and-contradictions.md | OK | 191.2s |
| 6 | 2026-09-20-spawn-agent-silent-failure-fix.md | OK | 109.1s |
| 7 | MASTER_HANDOVER_2026-06-10.md (control) | OK | 206.0s |
| 8 | 2026-07-10-trading-swarm-deep-audit-FABLE.md (control) | OK | 350.9s |
| 3 (retry) | 2026-08-21-discovery-gap-closure-prereg.md | OK, **outside the 1,200s protocol** — run at a 2,400s timeout | 1680.3s |

The document that timed out this run was **not** the one that timed out in the re-pilot
(`MASTER_HANDOVER_2026-09-06.md`, which completed comfortably this time at 177.9s). It was
`2026-08-21-discovery-gap-closure-prereg.md` — the document that is the whole reason Change
B exists (source of the two confirmed fabrications). The timeout risk did not go away, it
moved, and got worse in absolute terms: this document needed 2,400s (double the protocol
budget) to complete at all.

**This means the primary, comparable-timeout (1,200s) dataset has no result for the one
document the fabrication fix most needs to be checked against.** The only data for it comes
from a 2,400s supplementary run, which breaks the "same timeout, for comparability"
instruction. I'm reporting it, clearly labeled as non-comparable, because the alternative —
having nothing to check Change B against on its own source document — is worse. This is a
finding, not a footnote: the constrained-decoding change did not fix the timeout problem,
and it landed on the document that matters most for the other change.

### Gaps in this reconstruction

`logs/corpus_content_extractor.log` (the script's own `LOG_FILE` default) does not exist
anywhere on disk — not for this run, not for the pilot or re-pilot runs earlier the same
day. Per-call kill-condition state (own-RSS ceiling, consecutive-failure counter, run-wall-time
ceiling) and the script's own `call_seconds_min/max/mean` summary line are therefore
unavailable; all timing above is reconstructed from record `indexed_at` timestamps, which is
coarser (includes verification/write overhead, not just the Ollama call) and cannot confirm
whether the script hit any of its own kill conditions during the run. Flagging this rather
than assuming a clean exit — the run's own artifacts strongly suggest a clean, deliberate
exit (correctly ordered records, a deliberate supplementary retry with a doubled timeout,
files closed properly, no truncated JSON), but the log that would prove it outright is
missing.

---

## Schema pass rate

**8/8 = 100%** (0/6 → 5/6 → 8/8). Every record, including the 2,400s supplementary one, has
`schema_valid: true`. This is the expected result of constrained decoding — a shape
violation is not merely discouraged, it's unreachable — and it held under the removed-worked-
example prompt on the largest document in the set, which is the strongest evidence available
that Change A works as intended.

## Runtime

Returned-call mean (6 successful primary calls with a known delta, excluding the unknown
first call and the failed/supplementary 08-21 attempts): **268.3s** (177.9, 574.5, 191.2,
109.1, 206.0, 350.9s). Including the 1,200.6s timeout as a 7th call: **401.5s**.

| | original pilot | re-pilot | fourth pilot |
|---|---|---|---|
| mean, returned only | 252.2s | 348.2s | 268.3s |
| mean, with timeout | — | 454.7s | 401.5s |
| projected full corpus (272 docs), returned-only | ~18.6h | — | ~20.3h |
| projected full corpus (272 docs), with-timeout | — | ~34.4h | ~30.4h |

Faster than the re-pilot on both measures (consistent with the claimed speed benefit of not
spending tokens on formatting decisions) but not back to the original pilot's speed, and
still with a live, unresolved timeout failure mode on the corpus's harder documents.

## Quote breadth — did it recover from the worked example's control losses?

| control | original pilot | re-pilot (worked example) | fourth pilot |
|---|---|---|---|
| `MASTER_HANDOVER_2026-06-10.md` | 50 quotes | 32 quotes (−36%) | 36 quotes (−28% vs original) |
| `2026-07-10-trading-swarm-deep-audit-FABLE.md` | 35 quotes | 31 quotes (−11%) | 40 quotes (**+14%** vs original) |

Breadth substantially recovered on both controls versus the re-pilot; the FABLE control now
exceeds the original pilot's extraction breadth outright. The 06-10 control is better than
the re-pilot but still short of the original. Removing the worked example did what it was
supposed to do.

## Three-tier verification rate

**254/286 = 88.8%** across all 8 documents (81.9% like-for-like → 86.8% re-pilot → 88.8%
fourth pilot). Continued improvement.

Per-document (exact / normalized / structural / unverified out of total):

| document | total | verified | rate |
|---|---|---|---|
| MASTER_HANDOVER_2026-09-05.md | 34 | 29 | 85.3% |
| MASTER_HANDOVER_2026-09-06.md | 26 | 25 | 96.2% |
| 2026-09-05-copy-trade-decay-prereg.md | 38 | 37 | 97.4% |
| 2026-09-19-corpus-mining-rq-census-and-contradictions.md | 30 | 25 | 83.3% |
| 2026-09-20-spawn-agent-silent-failure-fix.md | 29 | 28 | 96.6% |
| MASTER_HANDOVER_2026-06-10.md (control) | 36 | 27 | 75.0% |
| 2026-07-10-trading-swarm-deep-audit-FABLE.md (control) | 40 | 39 | 97.5% |
| 2026-08-21-discovery-gap-closure-prereg.md (2,400s, non-comparable) | 53 | 44 | 83.0% |

## `explicitly_open` on 2026-08-21 — the document Change B exists for

10 items, 6 verified (60%), 4 unverified. **Both known fabrications are confirmed absent** —
searched their exact text across the entire record, not just `explicitly_open`:

- `"the exact timing of when the sweep will begin is not determined"` — **not present**
- `"the final runtime estimate after all adjustments is not yet known"` — **not present**

The 4 unverified items are not new fabrications — they're genuine content the structural
verifier can't match (same class as the re-pilot's markdown-reformatting misses), and 2 of
those 4 are exact duplicates of the other 2 (see next section). Change B's stated goal —
stop the model from inventing content to fill a capped field — appears to have worked on
this document, the one place it had previously and concretely failed.

## New finding: duplication, not fabrication, in capped fields

Traced every item in every field on 2026-08-21, not a sample, and checked for duplicate
`quote` text within each field (same check run across all 8 documents):

| field (2026-08-21, supplementary) | items | distinct | duplicates |
|---|---|---|---|
| question_addressed | 3 | 3 | 0 |
| findings | 10 | 10 | 0 |
| **explicitly_open** | 10 | 5 | **5** |
| **proposed_not_done** | 10 | 5 | **5** |
| **decisions_recorded** | 10 | 6 | **4** |
| failures_and_causes | 5 | 4 | 1 |
| **contradicts_or_corrects** | 5 | 1 | **4** (i.e. the same single item repeated 5 times) |

This is real, verified content — every duplicated quote is a genuine substring of the
document — repeated near-verbatim to fill a field up to its `maxItems` ceiling, instead of
stopping at the genuinely-distinct count. It is not the fabrication mechanism the checklist
was built to catch (nothing invented), but it produces the same downstream harm: inflated,
misleading item counts. `MASTER_HANDOVER_2026-09-05.md` — the other long, complex document
in the set — shows the same pattern at smaller scale (`explicitly_open` 8→6 distinct,
`proposed_not_done` 5→4 distinct). The other 6 (shorter, simpler) documents show zero
duplication in any field.

**Pattern:** duplication appears exactly on the two longest/most complex documents in the
set and nowhere else. `maxItems` structurally prevents the model from exceeding the cap, but
nothing currently stops it from reaching the cap by repeating real content when genuinely-
distinct material runs out — which is the same "reaching for the cap" failure mode Change B
was written to eliminate, resurfacing in a different, quieter form. A `uniqueItems: true`
constraint on each array in `GENERATION_SCHEMA` (or a within-field dedup check added to
`verify_record_quotes()`) is the obvious next lever, not implemented here — out of scope for
this recovery task, and the task's instructions said not to widen the normalizer.

No other new unsupported item was found in any field on 2026-08-21 beyond the known
duplication above and the pre-existing class of structurally-unmatched-but-genuine quotes.

---

## Verdict: do not commit to the full 272-document run yet

The fabrication mechanism the re-pilot found is fixed — confirmed on its own source document,
not assumed. But two things stop this from being ready for the full corpus:

1. **Timeout risk did not go away, it relocated** — to the document Change B was built
   around, and got worse (2,400s needed, not 1,200s). At the observed 1/8 timeout rate,
   scaling naively to 272 documents implies roughly 34 documents would need the same
   1,200s-wasted-then-2,400s-retry handling this document needed here — a real, currently
   unbudgeted cost, concentrated on the corpus's longer documents (which independently
   correlates with the duplication finding below).
2. **A new, previously unseen defect**: duplicate items padding capped list fields on longer
   documents (2/8 documents affected here, both the longest ones). This wasn't caught by any
   check this pipeline currently runs — `schema_valid` passes, and 3 of the 4 unverified
   `explicitly_open` slots on 08-21 are *verified* duplicates, not unverified ones, so
   `quote_verification`'s existing tiers don't flag it either. Undetected on a full run, it
   would silently inflate counts on exactly the documents most likely to matter (the longest,
   most eventful ones — audits, handovers).

If run at full scale today: expect schema shape to hold near-universally (constrained
decoding is doing real work), fabrication in the literal sense to stay near zero, but an
estimated ~10-25% of the corpus's longer documents (by the 2/8 rate observed here, likely
concentrated among the ~30 `MASTER_HANDOVER_*` and other long audit/handover documents in
the 272) to return duplicate-padded list fields that look clean by every check this pipeline
currently runs. Recommend adding a duplicate-detection check (schema `uniqueItems` and/or a
verifier-side dedup pass) and re-running this same 8-document comparison set once before
scaling to 272.
