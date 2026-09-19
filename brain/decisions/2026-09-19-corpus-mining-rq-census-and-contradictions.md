# 2026-09-19 — Mining the corpus index: mechanical queries

No model call anywhere in this task. Every finding below is either a direct field
lookup against `brain/corpus_reader_index_v2.jsonl`, a `grep` against source
documents, or a manual read whose quoted text is reproduced verbatim. Full structured
output: `brain/corpus_reader_index_v2_query_outputs.json`. This document does not rank,
score, or conclude that any RQ was answered or any finding invalidated — it reports
what documents state.

---

## Query 1 — The RQ census (led first, as instructed)

**Setup.** Heatmap pass 2 (`5e94eef`) graded 25 of 35 RQ identifiers
**ABANDONED-UNTESTED** — "dropped for cost/scope/judgment without ever being
measured" — built from ~48 documents read in depth. The corrected index (`4b61fce`)
covers 265 documents and recovered 167 previously-missed identifiers. This tests
whether that 25/35 conclusion survives contact with the fuller index.

**Literal test, as specified:** for each of the 25 ABANDONED-UNTESTED ids, does it
appear in any non-heatmap document typed `result` or `pre-registration`?

**Result: 0 hits.** No ABANDONED-UNTESTED identifier appears in a document strictly
typed `result` or `pre-registration` anywhere else in the corpus. Under the literal
test the task specified, **pass 2's count is corroborated, not refuted.**

**Secondary mechanical check, run because document_type is known to be a loose field**
(see `2026-09-19-corpus-reader-schema-and-verification.md` §3.2): grepped each
identifier's own occurrence line (±3 lines of context) in every non-heatmap mentioning
document for result-shaped language (CONFIRMED, INCONCLUSIVE, ASSESSMENT, VERDICT,
etc.), then read the actual passage. This surfaced one genuine finding and one weak
one:

> **RQ-EXT-001** (graded ABANDONED-UNTESTED). `2026-06-11-session-summary.md` contains
> a literal section:
> **"## RQ-EXT-001 Assessment: INCONCLUSIVE (too early)"**
> **"External seed cohort (195 traders, added June 6) has avg 7.1 geo resolved
> trades. Cannot compare against leaderboard traders with years of history."**
> The same document later lists: **"5. RQ-EXT-001 re-run — 2026-08-01"**. No
> document in the index shows that re-run happening.

RQ-EXT-001 was measured once — inconclusively, for a stated reason — and a follow-up
was scheduled and does not appear to have run. That is a different shape than "dropped
without ever being measured." Reported as stated; whether ABANDONED-UNTESTED is still
the right label, or something like ATTEMPTED-INCONCLUSIVE, is Oscar's call.

> **RQ-SCI-001** (weaker). `2026-06-10-str003-scoring.md`: **"SCS gap: STR003-005 was
> single-trader signal with no consensus. SCS system (built June 9) would have scored
> this LOW — validates RQ-SCI-001 design."** An informal, retrospective check, not a
> run of the pre-registered validation study itself. Included for completeness, likely
> does not change the grade.

**Everything else checked corroborates pass 2, mechanically:** the "July 1 RQ wave"
(RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001, RQ-VPIN-001,
RQ-ILS-001) repeats near-verbatim as a carried-forward TODO across **~12 consecutive
session summaries** (2026-06-10 through 2026-06-29) and is never marked done anywhere
in the index — a mechanical, direct confirmation of "dropped for attention-shift," not
a refutation of it. `2026-06-29-pool-c-decline-investigation.md` mentions
RQ-POOL-QUALITY-001/RQ-SECTOR-001 only as *dependent on* an unresolved prerequisite
(Pool C integrity) — a blocking note, not evidence of execution.

**Identifiers mentioned nowhere outside pass 2's own register:** `RQ3.3`, `RQ4.3`,
`RQ5.1`, `RQ6.1`, `RQ7.1`. Checked directly: all 5 are defined in
`brain/strategy-notes/research-directions.md` (the master RQ registry), which is
**outside `brain/decisions/`** and therefore outside this index's scope entirely. Not
a defect in pass 2 or the index — these were named once in the master registry and
never independently mentioned in a decision document, which is itself consistent with
"never acted on."

**Identifiers pass 2 never listed at all, present in the corrected index:** `LH-001`,
`RQ-CONTESTED-ARCHETYPE-001`, `RQ-EXT-001a`, `RQ-GEO-ELO-003`, `STR-001`, `STR-001b`,
`STR-002`, `STR-003`, `STR-004`, `STR-005`. Expected — pass 2's "35" count is
specifically RQ- identifiers; the STR-/LH- ones are a different namespace it never
claimed to enumerate.

**A real indexing gap found in the process, reported not fixed (no index edits in this
task):** `RQ4-MULTI` shows **0 mentions** in the corrected index, but direct `grep`
confirms it appears in `2026-09-12-heatmap-pass3-external-research.md:137` and
`MASTER_HANDOVER_2026-06-10.md:302`. The deterministic identifier pattern requires a
hyphen immediately after `RQ`; `RQ4-MULTI` has a digit there instead, so neither RQ
sub-pattern matches it. A real, if narrow, remaining index gap.

**Stop condition check: NOT TRIGGERED.** Pass 2's 25/35 (71%) is not substantially
wrong. One identifier (RQ-EXT-001) has a real, worth-flagging nuance; the rest of the
mechanical evidence corroborates the register rather than undermining it.

---

## Query 2 — Supersession chains

33 documents declare `supersedes`; 0 declare `superseded_by`. `supersedes` is free
text, not a clean pointer, so building the graph required reading each entry, not just
parsing it.

**14 clean, direction-verified document-to-document edges**, forming these chains
(oldest → newest):

```
2026-03-19-intelligence-sources.md -> 2026-04-19-intelligence-sources-nous-research.md
2026-07-15-tier3-pause-token-bleed.md -> 2026-08-31-tier3-credit-shutdown.md
2026-07-17-edge-proof-experiment-design-FABLE.md -> 2026-08-09-phase2-primary-and-paper-trading-preparation.md
2026-07-18-MASTER-HANDOVER.md -> MASTER_HANDOVER_2026-08-15.md -> MASTER_HANDOVER_2026-09-05.md -> MASTER_HANDOVER_2026-09-06.md
2026-07-24-shutdown-state-of-play.md -> 2026-08-07-session-summary.md
2026-08-19-geo-backfill-wiring-prereg.md -> 2026-09-09-geo-backfill-wiring-decision.md
2026-08-21-step1-implementation.md -> 2026-08-21-step1-implementation-v2.md
2026-08-27-session-summary-0825-0827.md -> 2026-09-04-limit-restore-and-sweep-closure.md
2026-08-31-slug-fetch.md -> 2026-09-01-slug-fetch-unswept.md
2026-08-31-why-unknown-investigation.md -> 2026-08-31-ingest-category-defect.md
2026-09-05-copy-trade-decay-prereg.md -> 2026-09-10-copy-trade-decay-result.md
2026-09-06-directional-skill-persistence-prereg.md -> 2026-09-06-external-dataset-scoping-and-prereg-amendment.md
```

**Terminal documents (superseded by nothing declared) — the current state of each
thread:** `2026-04-19-intelligence-sources-nous-research.md`,
`2026-08-07-session-summary.md`,
`2026-08-09-phase2-primary-and-paper-trading-preparation.md`,
`2026-08-21-step1-implementation-v2.md`, `2026-08-31-ingest-category-defect.md`,
`2026-08-31-tier3-credit-shutdown.md`, `2026-09-01-slug-fetch-unswept.md`,
`2026-09-04-limit-restore-and-sweep-closure.md`,
`2026-09-06-external-dataset-scoping-and-prereg-amendment.md`,
`2026-09-09-geo-backfill-wiring-decision.md`, `2026-09-10-copy-trade-decay-result.md`,
`MASTER_HANDOVER_2026-09-06.md`.

### Cycle found — and what it actually is

`2026-07-17-edge-proof-experiment-design-FABLE.md` and
`2026-08-09-phase2-primary-and-paper-trading-preparation.md` each list `supersedes`
pointing at the *other* — a genuine cycle in the raw declared-edges graph. Reading
`2026-07-17`'s own text resolves it: **"Full record: `2026-08-09-phase2-...md`"** — the
correct direction is 2026-08-09 supersedes 2026-07-17. The 2026-07-17 record's own
`supersedes` field is a **reversed duplicate**: the extraction found supersession
language near a filename and filed it under `supersedes` regardless of which way the
sentence actually points.

**This is not an isolated case.** Three more instances of the same class of error,
found while checking suspicious-looking entries, not by exhaustive audit of all 33:

- `2026-07-24-shutdown-state-of-play.md`'s field ("SUPERSEDED 2026-08-07 — B5 is now
  FINAL") is announcing that *it* is superseded, not that it supersedes something —
  same reversed-duplicate pattern; the correct edge is already captured from
  `2026-08-07-session-summary.md`'s own field.
- `2026-09-06-session-summary.md`'s field says it supersedes
  `MASTER_HANDOVER_2026-09-06.md`. The actual source sentence (line 77-78) is about a
  **third, unrelated pair** — "`MASTER_HANDOVER_2026-09-06.md`, superseding the
  2026-09-05 version" — describing MASTER_HANDOVER_2026-09-06 superseding
  MASTER_HANDOVER_2026-09-05 (already correctly captured elsewhere), misattributed to
  this document because it happens to also mention `MASTER_HANDOVER_2026-09-06.md`.
- `2026-09-17-notify-queue-and-cycle-wait-fix.md`'s field says it supersedes
  `2026-09-17-oos-hash-methodology-and-cycle-compounding.md`. Source: **"Follows:
  ...(which diagnosed but did not fix these two mechanisms)"** — a fix building on a
  diagnosis, not a replacement of it. The diagnosis remains valid.

**Net finding: the `supersedes` field frequently gets the direction or the
relationship type wrong** (at minimum 4 of 33 checked entries, ~12% — likely a floor,
since the remaining ~13 non-`.md`-target entries were not individually direction-
verified; see "what was not determined"). The commit hashes and quoted text inside
each field are accurate (matching the pattern already established for
`rq_str_lh_ids`/`artifact_paths_cited`); it is the field's own semantic label
(who-supersedes-whom) that is unreliable.

### Stale citation check

Mechanical test: for each confirmed-superseded document, does any other document,
dated after the supersession, still cite it by filename?

**9 candidates found.** 2 manually verified by reading the citing passage:

- `2026-07-15-tier3-pause-token-bleed.md` (superseded 2026-08-31) cited in
  `2026-09-19-tier25-supervisory-agent-scoping.md` — **legitimate**: cited as historical
  provenance for *why* research-scout-agent was paused, not relied on as current.
- `2026-08-21-step1-implementation.md` (superseded same-day by `-v2.md`) cited in
  `2026-08-22-tranche1-execution.md` — **legitimate**: cites step1's diagnostic finding
  (`end_date_iso: None` on already-resolved CLOB markets), which remains true
  independent of the implementation attempt being superseded.

Both checked candidates are normal, correct historical citation — not the stale-premise
failure mode. **The other 7 are unread candidates, not verdicts** (list in
`query_outputs.json`). Given the false-positive rate on this small sample, this
heuristic should be read as "worth a look," not "confirmed stale."

---

## Query 3 — Citation-free documents, recomputed

| | Old index | Corrected index |
|---|---|---|
| Cites no commit | 83 | **85** |
| Cites no artifact | 32 | **6** |
| Cites neither | 26 | **5** |

The `no_commit` count did not drop (83→85) because `commit_refs` was not touched by
the deterministic fix — only `rq_str_lh_ids` and `artifact_paths_cited` were. The +2
is the two new `archive/` records, which have no `commit_refs` populated (LLM pass
pending, not run). The `no_artifact` and `neither` counts collapsed as expected, given
the fix recovered 1,115 previously-missed paths.

**The 5 remaining citation-free documents, all of which carry numeric findings**
(listed, not adjudicated, per the task):

- `2026-03-19-intelligence-sources.md` (8 findings)
- `2026-06-01-performance-analyst-weekly.md` (8 findings)
- `2026-06-10-str003-scoring.md` (8 findings)
- `2026-07-06-brier-target-crossed.md` (8 findings)
- `2026-07-13-elections-calibration-break.md` (8 findings)

Full finding text for these is in `query3_neither_with_numbers.json` alongside the main
output.

---

## Query 4 — Contradiction candidates

**Method:** grouped `numeric_findings` by shared bigrams of significant (non-stopword)
context words; kept groups spanning ≥2 distinct dates, ≥2 distinct values, and ≤8 total
occurrences (to exclude generic phrases). Produced **391 raw candidate groups** — a
funnel, not a findings list.

**Stop condition check (result of record) — NOT TRIGGERED.** Searched all occurrences
of `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`, `+0.0316`, and
`n=3,032/120` across the index: ~19 occurrences in 13 documents, 2026-08-16 through
2026-09-17, all consistent. Two apparent value changes exist
(`0.0316 → 0.0208` in `2026-09-06-cross-arc-selection-reversal-pattern.md`;
`3,032 → 3,795` in `2026-09-05-copy-trade-decay-prereg.md`) — both are explicitly
narrated **by the documents themselves** as later re-derivation / population growth,
not silent contradictions.

**Sample of 10 verified by opening both documents:**

| Candidate | Verdict |
|---|---|
| "legal classifiable" (5,732 vs 1,178 vs 753) | False match — different, correctly-labeled sub-populations |
| "flagged trader" | False match — structurally unrelated numbers sharing a generic phrase |
| "clean pool" (493→1,135) | Documented change, narrated in the same sentence |
| "traders geo_elo" (2175 constant; 177/402/435 counts) | False match — 2175 is a stable threshold; the count swings are known Pool C volatility, already investigated elsewhere (`2026-06-29-pool-c-decline-investigation.md`: ARTIFACT, no pool bug) |
| "sunday recalc" (2848→2850→2851→2875) | Documented change, self-narrated as a sequence in one sentence |
| "opposite outcome" (37.58%) | Consistent — repeated identically across 5 independent documents |
| "point estimate" | False match — 8 unrelated statistics share only a generic phrase |
| "cohort n_positions" (3,032→3,795) | Already resolved clean under the stop-condition check above |
| "markets exactly" / "enter canonical" (225, 214,413) | Consistent — same figures repeat exactly |
| **"clob resolved" (214,155 vs 214,516 vs 216,499)** | **Genuine open discrepancy** |

**The one genuine candidate:** `2026-08-30-canonical-writer-column-gap.md` states
**"214,155 of 214,413 clob-resolved markets (99.9%) sit at category='Unknown'"**.
The same day, `2026-08-30-category-classifier-investigation.md` states
**"CLOB-resolved (`sweep`) Unknown markets... = 214,516"**, and
`2026-08-31-geo-scoping-inventory.md` repeats **"clob-resolved Unknown = 214,516
markets"**. That is a same-day, 361-market disagreement on what reads as the same
population. By 2026-09-07, `2026-09-07-stranded-markets-figure-reconciliation.md`
states **"population 216,499 clob-resolved markets"** — which may be organic growth on
top of an already-unresolved base figure, or may not be. **Not adjudicated here.**

**False-match rate: 9/10 (90%).** This is high. The bigram heuristic should be treated
as a coarse funnel that needs a human (or a second, more targeted mechanical pass) to
narrow it — most of what it surfaces is either a generic-phrase collision or a change
the source documents already explain themselves.

---

## Scope compliance

No model call was made. No index, script, or production table was modified. No
ranking, scoring, or recommendation is offered anywhere above — findings are reported
as document quotes plus mechanical counts.

**Auto-push:** this task's deliverables were committed locally. The `post-commit` hook
installed earlier fires automatically on any commit touching `brain/decisions/` and
will push this commit to `origin/master` — flagged here as instructed, not suppressed
(no opt-out mechanism exists yet; see the open question from the prior session).

---

## What was not determined

- Whether RQ-EXT-001's grade should change from ABANDONED-UNTESTED given the one
  inconclusive measurement found — reported, not adjudicated; Oscar's call.
- Whether RQ-SCI-001's informal retrospective mention should count as any form of
  validation — reported as weak evidence, not resolved.
- The remaining ~13 non-`.md`-target `supersedes` entries were not individually
  direction-verified beyond what's shown in "non-document supersedes targets" and
  "self-amendments" — the ~12% mischaracterization rate found is a floor from a partial
  check, not a full audit of all 33.
- 7 of the 9 stale-citation candidates in Query 2 were not read — listed as candidates
  only.
- The `clob-resolved-Unknown` discrepancy (214,155 / 214,516 / 216,499) is reported,
  not resolved — determining which figure (if either) is correct, and whether the
  09-07 growth is organic or compounds an existing error, needs a direct read of all
  three documents' methodology, not attempted here.
- The `RQ4-MULTI` indexing gap is reported, not fixed — this task makes no index
  changes.
- Whether any of the 5 remaining citation-free documents' numeric findings (Query 3)
  are among the project's previously-recorded unreproducible figures — listed, not
  cross-referenced against that history.
- 381 of the 391 raw Query 4 candidate groups were not individually read — the
  false-match rate above is a sample estimate from 10, not a census.

---

*Mechanical queries performed 2026-09-19 against `brain/corpus_reader_index_v2.jsonl`
and direct reads of source documents in `brain/decisions/`. No model call. No writes
to any index, script, or production table.*
