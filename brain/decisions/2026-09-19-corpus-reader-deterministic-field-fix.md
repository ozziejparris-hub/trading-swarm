# 2026-09-19 — Deterministic re-extraction of rq_str_lh_ids and artifact_paths_cited

Companion/amendment to `2026-09-19-corpus-reader-schema-and-verification.md` (`f1c5ed2`).
That document's §3.5 called `rq_str_lh_ids` and `artifact_paths_cited` "unreliable" and
named specific instances as **fabricated**. Rechecking those instances directly against
source with `grep` (not by eyeballing) shows that characterization was **wrong**, and
this document corrects it rather than leaving the two documents in contradiction. No
model call was made anywhere in this task — both fields were already, and remain, pure
regex extraction.

---

## 0. The correction, stated first

Reading `scripts/corpus_reader_index.py` shows `commit_refs`, `rq_str_lh_ids`,
`artifact_paths_cited`, and `has_what_was_not_determined_section` were **already
regex-only** (`extract_deterministic()`), not model output. The model's own prompt
(`EXTRACTION_PROMPT`) only ever asked for `title`, `document_type`,
`self_stated_verdict`, `numeric_findings`, `supersedes`, `superseded_by`.

A pure, single-document `re.findall()` cannot invent a substring absent from its own
input — there is no mechanism for it to do so, and no cross-document state is passed
into the extraction (confirmed: `extract_deterministic()` takes only the one document's
own text). So "fabrication" in the sense the 2026-05-14 local-model precedent describes
was never structurally possible for these two fields, in the original script or this one.

Grepping the three specific documents the prior verification named as containing
fabricated entries confirms all three entries are genuinely present, verbatim, in their
source:

| Claimed fabrication | Source | Actual result |
|---|---|---|
| `STR-004` in `2026-09-12-heatmap-pass5-shortlist.md` | line 365: `...STR-001b/STR-004, the strategy...` | **Present.** Packed against `STR-001b` with no space, easy to miss on a manual read — that is what happened. |
| `backfill_market_dates.py` in `2026-08-30-geo-backlog-and-category-reach.md` | line 252: `` `backfill_market_dates.py` used `trades.market_category`... `` | **Present**, backtick-quoted, exactly where the original regex says it found it. |
| `daily_maintenance.py` in the same document | line 188: `` `--limit 50` has been present in `daily_maintenance.py`'s STEPS... `` | **Present**, backtick-quoted. |
| `scripts/evaluate_new_trader_results.py` in `2026-09-09-background-backfill-ingest-evaluation.md` | line 49: `` ...the same evaluator `scripts/backfill_trade_results_geo.py` and `scripts/evaluate_new_trader_results.py` call... `` | **Present**, backtick-quoted, in the same sentence as a path I did correctly verify. |

**None of these four were fabricated.** The prior verification's manual spot-check
missed them on read — an error in that verification, not a defect in the extraction. It
is corrected here rather than carried forward silently.

**What was real:** under-matching (recall), not invention. Two regex gaps, found and
fixed in this task (§1), account for essentially everything the prior verification
correctly flagged as missing (the 6 RQ- ids in heatmap-pass-3, the ~15 bare script names
in `2026-06-24-session-summary.md`).

---

## 1. The new patterns, and why

Starting from the task's suggested patterns, refined against the corpus (three real bugs
found and fixed while building this, each documented in the script):

```
RQ_WORD_RE  = \bRQ-[A-Z]+(?:-[A-Z]+)*(?:-\d+[a-z]?)?\b
RQ_NUM_RE   = \bRQ\d+(?:\.\d+)*\b
STR_LH_RE   = \b(?:STR|LH)-\d+[a-z]?\b

PATH_RE     = \b(?:scripts|monitoring|config|brain|orchestrator|data|logs|tests|analysis|docs)/[\w./-]+\b
BAREFILE_RE = (?<![\w.])\.?[\w-]+\.(?:py|sh|json|jsonl|md|sql|csv|txt)\b
```

**Identifiers, three independent patterns unioned, not one alternated regex.** A single
alternated pattern (`A|B|C` in one `findall()`) gives non-overlapping matches: on
`RQ-LH-001` it would consume the whole string via the RQ-word branch and never separately
match the embedded `LH-001` — but this corpus uses both as genuinely distinct,
independently-meaningful identifiers (an RQ *about* LH-001, and LH-001 itself). Running
each pattern as its own `findall()` and unioning the results lets both be captured even
though they overlap in the text. Confirmed this matters: with a single alternated regex,
2 documents lost `LH-001` this way; with three independent patterns, 0 documents lost
anything relative to the original extraction.

**Three refinements made during this task, beyond the starting patterns:**
1. `RQ-[A-Z]+(?:-\d+[a-z]?)?` → trailing `[a-z]?` added. Without it, `RQ-EXT-001a/b/c`
   fails its own trailing `\b` (word-to-word transition between `1` and `a`), forcing a
   backtrack that drops the digits entirely and yields the wrong, truncated `RQ-EXT`.
   Found on `2026-06-06-session-summary.md`.
2. `(?:-[A-Z]+)*` added before the digit suffix. A single `[A-Z]+` segment stops at the
   first internal hyphen, silently dropping the rest of a multi-segment id
   (`RQ-GEO-ELO-001`, `RQ-POOL-QUALITY-001`, `RQ-CONTESTED-ARCHETYPE-001` — 4 distinct
   ids corpus-wide, all previously truncated to their first segment only). Found on
   `2026-09-12-heatmap-pass2-ruled-out-register.md`.
3. `BAREFILE_RE`'s leading `(?<![\w.])\.?` allows one optional leading dot for hidden
   config/state files (`.audit_invariants_state.json`, `.canonical_drift_state.json`),
   which a plain `\b[\w-]+\.ext\b` cannot match (a bare word-boundary can't start on a
   literal dot). Found on `2026-09-16-monitoring-ingestion-stall-diagnosis.md`.

**Fences and inline backticks: matched, not excluded.** The task's own reasoning is
adopted directly — the original script missed a commit hash specifically because it was
inside a code fence-adjacent context, so excluding fenced/backticked text here would risk
the identical failure mode. Both patterns run over the raw text unmodified; nothing is
stripped before matching.

**`.md` matches to other decision documents: in scope.** The existing schema and the
original script's own convention already treat a cited decision document
(`2026-08-30-canonical-writer-column-gap.md`, `CLAUDE.md`) as a legitimate
`artifact_paths_cited` entry — it is something the document points a reader at, which is
what the field is for. Kept in scope, with one exclusion: **the document's own filename**
is stripped from both the bare-file and full-path match sets (self-citation is not an
external reference).

**Bare-file / full-path dedup: prefer the fuller form.** When a bare match's basename
equals the basename of a captured full path (`failure_age.py` vs
`monitoring/failure_age.py`), the bare form is dropped. This alone accounts for the large
majority (497 of 507) of what a raw diff would call "lost" relative to the old
extraction — the artifact is still represented, just once, in its more specific form,
not actually missing.

**`PATH_RE` also matches bare directory references** (e.g. `brain/agent-outputs/`,
`data/characterizations/`) when a document cites the directory itself, not a specific
file inside it — kept, since the document is citing it as a thing to check, which is
exactly what this field is for.

---

## 2. The full census (263 existing records + 132 diff detail in `brain/corpus_reader_index_v2_census.json`)

| | Count |
|---|---|
| Records with ≥1 identifier the old regex missed | **47 / 263** |
| Total identifiers added | **167** |
| Records with ≥1 path the old regex missed | **213 / 263** (81%) |
| Total paths added | **1,115** |
| Records with a **fabricated** identifier (present in output, absent from source) | **0** — structurally impossible for a single-document regex; see §0 |
| Records with a **fabricated** path, same test | **0** — same reason |
| Records where the new regex **lost** an identifier the old one had | **0** (after the three-independent-patterns fix) |
| Records where the new regex **lost** a path the old one had | 132 raw, **4 true** after excluding fuller-form dedup (see below) |

**Worst individual cases, by count of previously-missed identifiers:**
`2026-09-12-heatmap-pass2-ruled-out-register.md` (15 missed — RQ-CONTESTED-001,
RQ-CONVICTION-001, RQ-CORRELATION-001, RQ-EXEC-001, RQ-EXT-001, RQ-GEO-ELO-001,
RQ-ILS-001, RQ-LH-001, RQ-PNLGATE-001, RQ-POOL-QUALITY-001, RQ-POSSIZE-001, RQ-SCI-001,
RQ-SECTOR-001, RQ-VPIN-001, STR-001b), `MASTER_HANDOVER_2026-06-10.md` (11),
`2026-06-13-session-summary.md` (9), `2026-06-14-session-summary.md` (9),
`2026-06-12-session-summary.md` (8).

**Worst individual cases, by count of previously-missed paths:**
`2026-08-16-comprehensive-elo-dependency-trace.md` (46), `2026-07-10-trading-swarm-structural-survey.md` (39),
`2026-08-19-write-path-census.md` (30), `2026-09-13-built-never-connected-sweep.md` (25),
`MASTER_HANDOVER_2026-06-10.md` (21). These are, unsurprisingly, the corpus's own
census/inventory/survey documents — exactly the shape of document where an enumeration
task has the most surface area to miss.

**The 4 true path losses**, after distinguishing "represented in fuller form" (497 of
501 raw losses — not real losses) from actual absence:

| Document | Lost string | Why |
|---|---|---|
| `2026-08-17-maintenance-outage-scope.md` | `...07-24-pre-res-scan.json`, `...08-07-pre-res-scan.json` | Author's own elliptical shorthand (literal `...` in the source, eliding a shared date prefix between two sibling filenames). Neither the old nor new regex reconstructs the implied full filename; catching a bare `...` prefix would reintroduce the class of false positive below. Accepted, not fixed. |
| `2026-08-19-write-path-census.md` | `..._v2b.py` | Same shorthand convention. |
| `2026-09-07-stranded-markets-figure-reconciliation.md` | `.json/.sql` | This one is a **correction, not a loss** — the old regex matched a literal extension-list fragment (`` `.py`/`.md`/`.json/.sql` `` naming candidate extensions to grep, not a real file) as if it were a filename. The new regex correctly does not reproduce this false positive. |

**Confirmed catches of the named known defects:**
- **6 RQ- ids in `2026-09-12-heatmap-pass3-external-research.md`** — RQ-VPIN-001,
  RQ-ILS-001, RQ-POSSIZE-001, RQ-SECTOR-001, RQ-CORRELATION-001, RQ-SCI-001 — all 6 now
  present, verified directly against `index_v2.jsonl`.
- **STR-004 in heatmap-pass5** — was never missing (§0); still present in the new record.
- **~15 script names in `2026-06-24-session-summary.md`** — old record: `[]`. New record:
  7 real paths (`findings.json`, `monitoring/column_definitions.py`,
  `reconcile_geo_resolved_counts.py`, `register_signal.py`, `score_str003_signals.py`,
  `scripts/check_canonical_definitions.py`, `signals.json`). Fewer than "~15" because
  several script names in that document (`system_observer.py`,
  `snapshot_elo_scores.py`, `detect_counter_signals`, `resolve_legendary_markets`,
  `verify_market_titles`, `pre_resolution_intelligence`, etc.) are named **without** a
  file extension in the prose (bare identifiers, not literal filenames) — genuinely
  outside what either the old or new pattern can distinguish from ordinary text, since
  neither ends in a matchable extension as written. Reported as a real, remaining gap for
  this document (not silently closed) rather than rounded up.
- **The two "fabricated path sets"** — never fabricated (§0); both already fully present
  in the old and new extraction alike.

---

## 3. Two gaps from the same run

### (a) `brain/decisions/archive/` — indexed now, deterministic fields only

Two files, never reached by the original script's non-recursive `DECISIONS_DIR.glob("*.md")`:

| Path | First heading | Lines | RQ/STR/LH ids | Artifact paths |
|---|---|---|---|---|
| `archive/MASTER_HANDOVER_2026-05-20.md` | "Master Handover Document — 2026-05-20" | 335 | 9 | 39 |
| `archive/MASTER_HANDOVER_server-pre-setup-1.md` | "MASTER HANDOVER DOCUMENT" | 617 | 12 | 43 |

Both are now in `brain/corpus_reader_index_v2.jsonl` with `path`, dates, sizes,
`first_heading`, and the two deterministic fields populated. `title`,
`document_type`, `self_stated_verdict`, `numeric_findings`, `supersedes`,
`superseded_by` are `null` and the record carries `"llm_fields_pending": true` plus a
`schema_problems` note explaining why, rather than a guessed or silently-omitted value.

**Whether to run the LLM pass for these two is a separate decision, not made here.**
Reasons to run it: these are `MASTER_HANDOVER` documents — the corpus's session/state
summaries — so a search that filters on `document_type` or `self_stated_verdict` will
silently skip these two until that pass runs. Reasons to hold: it's 2 documents, ~2
Ollama calls, effectively free relative to the original 4h53m run — there is no
resource argument for delay, only a "was this asked for" one, and it wasn't in this
task's scope. Flagged for a decision, model not run.

### (b) The two failed documents — not retried, cost estimated

- **`2026-06-29-overhang-ledger.md`** — timed out at the 1800s ceiling. At 1,032 lines
  it is above this corpus's piloted 90th-percentile size (665 lines) but well under the
  max (1,883 lines), and other documents in that size range completed in 90–220s during
  the actual run. A full 1800s timeout (not a partial completion) suggests a genuine
  stall on this specific call, not pure document-size cost — not confirmed without
  retrying, which this task does not do.
- **`2026-09-10-own-market-calibration.md`** — a malformed JSON escape sequence in the
  model's own output, unrelated to timing or size (403 lines, well within normal range).

**Retry cost:** 2 Ollama calls. At this run's own observed mean (65.3s) that's on the
order of 2 minutes if both succeed cleanly; worst case (one hits its ceiling again) adds
whatever timeout is set for the retry. Trivial next to the original 4h53m run.

**Does the GPU finding (§7 of the prior verification — 49/49 layers GPU-resident, not
CPU-bound) change the timeout to use?** It changes what a *sensible* timeout looks like,
but not because the original 1800s was set on a mistaken CPU-bound assumption — it
wasn't; `OLLAMA_TIMEOUT_SECONDS` was piloted empirically against this exact GPU-resident
setup, not derived from the scoping doc's now-corrected 4GB/CPU-bound premise. What the
GPU finding does support: since every one of 265 real calls in this run finished well
under 300s except the one that hit the full 1800s ceiling, a **retry-specific shorter
timeout (e.g. 300–600s)** would fail fast on a genuine repeat stall rather than waiting
30 minutes to find out, while still sitting comfortably above the observed working
range. This is a recommendation for whoever runs the retry, not applied here — **no
retry was run in this task.**

---

## 4. Verification of the replacement

**Method:** 10 documents read directly (`grep`/manual read against the actual `.md`
file, not inferred from either index): the 5 documents named in the prior verification's
confirmed-defect list (heatmap-pass-3, heatmap-pass-5, `2026-06-24-session-summary.md`,
`2026-08-30-geo-backlog-and-category-reach.md`,
`2026-09-09-background-backfill-ingest-evaluation.md`) plus 5 more
(`2026-05-21-session-summary.md`, `2026-06-09-session-summary.md`,
`2026-06-06-session-summary.md`, `2026-07-12-session-summary.md`,
`2026-06-29-comprehensive-elo-writer-map.md`) already read in full during the prior
verification, now re-checked against the new extraction.

**Precision: 100% across all 10.** Every entry in the new `rq_str_lh_ids` and
`artifact_paths_cited` output for these 10 documents was confirmed, by direct grep
against the source, to be a real, verbatim substring of that document. This is expected
given §0 (a single-document regex cannot invent content), and it held.

**Recall: complete for 9 of 10; one small residual gap named, not rounded away.** For 9
documents, every identifier and path a careful direct read turns up is present in the
new output. `2026-06-24-session-summary.md` has a residual gap: several script names in
that document are written without a file extension in the prose (bare identifiers like
`system_observer`, `resolve_legendary_markets`, referenced by name but not as a literal
`name.py` string) — genuinely unrecoverable by any extension-anchored pattern, old or
new, without a much looser (and much noisier) heuristic. Reported as a known, accepted
limit of this approach, not claimed as fixed.

**Where the new regex is worse than the old one:** the 4 true path losses in §2 (author
shorthand + one corrected false positive) are, on inspection, either an accepted tradeoff
or an improvement mislabeled as a loss by raw set difference — not a case where the new
pattern is genuinely worse at the field's actual job. No case was found where the new
regex is worse in a way that matters.

**Verdict: `rq_str_lh_ids` and `artifact_paths_cited` are upgraded from "unreliable" to
trustworthy**, with two named residual limits:
1. A bare identifier/filename mentioned without its RQ-/STR-/LH- prefix or file
   extension is invisible to pattern matching by construction — this applies to any
   regex-based approach, not a bug to fix, and is the boundary of what "deterministic
   extraction" can promise.
2. Four documents carry a handful of author-shorthand elliptical filename references
   that resolve to a real file only with cross-reference to a preceding sentence — named
   in §2, not silently dropped.

Neither limit is a fabrication risk (§0 rules that out structurally), and neither
produces a false positive that would mislead a reader — both are pure omissions of a
kind a reader skimming the source prose would also need care to catch. This is a
materially different, and much better, risk profile than the "unreliable" verdict this
document supersedes for these two fields.

---

## 5. What was not determined

- Whether to run the LLM pass on the 2 archive/ documents for their non-deterministic
  fields — flagged in §3a, not decided here.
- Whether retrying the 2 failed documents should also independently retry with a shorter
  timeout, and what that timeout should be exactly — a range (300–600s) is suggested in
  §3b, not fixed or applied.
- The true cause of `2026-06-29-overhang-ledger.md`'s full-ceiling timeout (genuine stall
  vs. undermeasured size cost) — not established without a retry, which this task does
  not perform.
- Whether the `2026-06-24-session-summary.md`-style bare-identifier-without-extension gap
  is common enough elsewhere in the corpus to be worth a dedicated (and necessarily
  noisier) heuristic — not surveyed beyond this one document.
- The full content of the 4 census-flagged "true loss" author-shorthand references (what
  the elided filenames actually resolve to) — named as a gap in §2, not resolved.

---

## 6. Where this lives

- Patch script: `scripts/patch_corpus_reader_deterministic_fields.py`.
- New index: `brain/corpus_reader_index_v2.jsonl` — 265 records (263 patched + 2 new
  archive/ records). The original `brain/corpus_reader_index.jsonl` is untouched, left in
  place for comparison per this task's own instruction.
- Full per-document diff (every added/lost identifier and path, by document):
  `brain/corpus_reader_index_v2_census.json`.
- This document amends `2026-09-19-corpus-reader-schema-and-verification.md`'s §3.5:
  where that document named `rq_str_lh_ids` and `artifact_paths_cited` unreliable and
  cited specific fabrications, read this document instead — those two fields are now
  regenerated and trustworthy, and the named fabrications were verification errors, not
  real defects, per §0.

---

*Deterministic re-extraction and verification performed 2026-09-19, read-only against
source documents, no model call, no retry of the two failed documents, no edit to the
original index or the archive files themselves.*
