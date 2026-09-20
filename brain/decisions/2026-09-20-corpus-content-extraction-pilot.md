# Corpus content extraction — schema proposal and 12-document pilot

**Date:** 2026-09-20. Second local pass over `brain/decisions/`: the structural index
(`corpus_reader_index_v2.jsonl`, 265 records) captures document shape — type, verdict
line, commits, numeric findings, identifiers — not what any document *concluded*.
Heatmap pass 5's stated limitation stands: its shortlist rests on ~190 documents no pass
ever read. This pilot tests whether local extraction can do that work before scheduling
a full run. Reported here as originally delivered in-conversation, per the task's
instruction to stop and report after the pilot before proceeding further — see
`2026-09-20-corpus-content-extraction-repilot.md` for the follow-up that tested fixes
against this pilot's two findings.

## Schema

One record per document in `brain/corpus_content_index.jsonl` (a separate artifact from
the structural index, joined by `path`, never modifying it). Seven fields —
`question_addressed`, `findings`, `explicitly_open`, `proposed_not_done`,
`decisions_recorded`, `failures_and_causes`, `contradicts_or_corrects` — each a list of
`{claim, quote}`, capped (3 / 10 / 10 / 10 / 10 / 10 / 5) for the same reason
`corpus_reader_index.py`'s `MAX_NUMERIC_FINDINGS=8` is capped: traceable pointers back
into the source, not an exhaustive re-statement, and tractable to spot-check.

**`line` is never asked of the model.** It is computed by the script, by searching for
the model's quote in the actual source text. An LLM asked to count lines in a
1,800-line document will get it wrong; an LLM asked to copy a short span of text it just
read, checked afterward by exact string search, is the same anchored-extraction bet that
already proved reliable for `corpus_reader_index.py`'s `title`/`self_stated_verdict`/
`numeric_findings` fields (15/15, 15/15, ~120/120 traced correct) and unreliable for its
free-recall fields (`rq_str_lh_ids`, `artifact_paths_cited`).

`decisions_recorded`'s "by whom" and `failures_and_causes`' "stated reason" are folded
into the same `claim`/`quote` pair rather than separate fields, keeping every list
uniform and avoiding a field that needs judgment to populate when authorship/reason is
absent. No `title`/`document_type` — already reliable in the structural index, not
duplicated.

## Pilot: 12 documents

6 read in depth by heatmap passes 1–5 (`MASTER_HANDOVER_2026-06-10.md`,
`MASTER_HANDOVER_2026-08-15.md`, `MASTER_HANDOVER_2026-09-05.md`,
`MASTER_HANDOVER_2026-09-06.md`, `2026-07-07-silent-failure-audit-FABLE.md`,
`2026-07-10-trading-swarm-deep-audit-FABLE.md`) + 6 never read by any pass
(`2026-08-21-discovery-gap-closure-prereg.md` — the corpus's largest, 1,884 lines —
`2026-09-05-copy-trade-decay-prereg.md`, `2026-09-06-directional-skill-persistence-
prereg.md`, `2026-09-19-corpus-mining-rq-census-and-contradictions.md`,
`2026-09-19-corpus-reader-deterministic-field-fix.md`,
`2026-09-20-spawn-agent-silent-failure-fix.md`).

**Run:** wall 3,032s (50.5 min), mean call 252.2s, min 90.0s, max 814.2s (the largest
document). RSS peak 27.9MB. Zero kill-conditions, zero call-level parse failures.

| Document | Lines | Runtime | Schema valid | Quotes | Exact | Normalized | Unverified |
|---|---:|---:|:---:|---:|---:|---:|---:|
| MASTER_HANDOVER_2026-06-10 (read) | 498 | 250.7s | ✅ | 50 | 22 | 5 | 23 |
| MASTER_HANDOVER_2026-08-15 (read) | 527 | 318.5s | ✅ | 30 | 2 | 23 | 5 |
| MASTER_HANDOVER_2026-09-05 (read) | 521 | 187.9s | ❌ | 0 | 0 | 0 | 0 |
| MASTER_HANDOVER_2026-09-06 (read) | 412 | 119.9s | ❌ | 0 | 0 | 0 | 0 |
| 2026-07-07-silent-failure-audit-FABLE (read) | 167 | 229.1s | ✅ | 28 | 13 | 0 | 15 |
| 2026-07-10-trading-swarm-deep-audit-FABLE (read) | 268 | 297.7s | ✅ | 35 | 10 | 0 | 25 |
| 2026-08-21-discovery-gap-closure-prereg (unread, largest) | 1,884 | 814.2s | ❌ | 0 | 0 | 0 | 0 |
| 2026-09-05-copy-trade-decay-prereg (unread) | 1,066 | 270.5s | ❌ | 0 | 0 | 0 | 0 |
| 2026-09-06-directional-skill-persistence-prereg (unread) | 666 | 216.8s | ✅ | 22 | 1 | 17 | 4 |
| 2026-09-19-corpus-mining-rq-census (unread) | 301 | 90.0s | ❌ | 0 | 0 | 0 | 0 |
| 2026-09-19-corpus-reader-deterministic-field-fix (unread) | 315 | 139.9s | ✅ | 28 | 3 | 17 | 8 |
| 2026-09-20-spawn-agent-silent-failure-fix (unread, mine) | 436 | 90.8s | ❌ | 0 | 0 | 0 | 0 |

## Finding 1: 6/12 (50%) schema failures

Every field returned as a flat list of bare strings instead of `{claim, quote}` objects.
`validate_schema()` caught all 6 correctly (hard-fail contract worked as designed). Not
length-correlated — the 1,884-line largest document failed; so did a 301-line document
(90s call); a 527-line document succeeded. Content read against independent knowledge of
the project was accurate and substantive in every failing case — the model knew what to
extract, it just didn't reliably sustain the nested `{claim, quote}` shape across a long
generation roughly half the time.

## Finding 2: quotes verify, once markdown is accounted for

Aggregate (6 valid documents): 193 quotes, 51 exact (26.4%), 62 whitespace-normalized
(32.1%), 80 unverified (41.5%) by the two-tier check available at pilot time. **Every one
of the 80 unverified quotes was manually traced against source — zero fabrications.**
All are genuine content the model reformatted out of markdown when copying it: table
rows (`| **Label** | value |`) rewritten as "Label: value" prose, `**bold**` markers
stripped, a heading merged with the following line's body text. A prototype markdown-
aware normalizer recovered most (not all) of these on two test documents — the residual
gap is specifically table rows where the model also inserts a colon absent from the
source.

## Agreement with the 6 already-read documents

Strong, no disagreements found. The two FABLE audits' extracted findings matched
independent verification exactly (e.g. "the immune system's respawn does not exist",
the `difficulty_score` 123/581,214 dead-column finding — which came back with a
byte-exact verified quote, proof the model preserves markdown perfectly when it happens
to).

## Recommendation (acted on same day — see the re-pilot doc)

Do not proceed to the full corpus yet. Two isolated fixes proposed: a worked example in
the prompt (targeting Finding 1) and a markdown-structural verification tier, reported as
its own category, never merged into "exact" (targeting Finding 2). Timeout for the
follow-up test set at 1,200s (1.5x this pilot's own 814.2s observed maximum). Both fixes
were tested, not assumed, against exactly the 6 documents that failed here — outcome in
`2026-09-20-corpus-content-extraction-repilot.md`.

## What this does not fix / did not do

- Did not run the full corpus.
- Did not modify the structural index.
- Did not re-enable any paused agent.
- Did not synthesise, rank, or draw conclusions from extracted content — deliberately a
  separate, later task.

---

*Pilot run 2026-09-20T15:13:15Z–16:03:47Z.
`scripts/corpus_content_extractor.py`, `brain/corpus_content_pilot.jsonl`,
`brain/corpus_content_pilot_failures.jsonl` (empty — no call-level parse failures)
committed alongside this document.*
