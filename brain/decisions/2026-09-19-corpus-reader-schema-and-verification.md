# 2026-09-19 — Corpus reader: schema, verification, and index status

Companion to `2026-09-19-tier25-supervisory-agent-scoping.md` (`a1db987`). Builds
`scripts/corpus_reader_index.py` and `brain/corpus_reader_index.jsonl` — a structured,
extractive index over `brain/decisions/`, closing the ~190/244-unread gap Pass 5 of the
heatmap flagged as its own limitation. This document covers the schema and its
justification, the Part 4 verification in full (schema validation + manual spot-check),
the counts the index makes available, and what was not determined. It does not
synthesise, rank, or draw conclusions from the corpus content — that is deliberately a
separate task.

---

## 1. Run summary

- **Script:** `scripts/corpus_reader_index.py` (548 lines). Model: `qwen3-coder:30b-a3b-q4_K_M`
  via `localhost:11434/api/generate`, temperature low, `stream: false` — the
  `backfill_market_categories.py` pattern (numbered document in, strict JSON object out,
  markdown-fence stripping, `json.loads` with a hard-fail path, no retry-until-parses
  loop), scaled from a 20-item title batch to one full document per call.
- **Launched:** 2026-09-19T13:21:20Z, detached (`nohup`/`setsid`/`disown`, PPID=1).
  **Finished:** 2026-09-19T18:14:01Z. **Wall time: 17,560.8s (4h52m41s).**
- **Telemetry (logged during the run, not inferred afterward):** `cpu_seconds_self:
  1.25`, `rss_start_mb: 23.7`, `rss_peak_mb: 28.0`, `rss_end_mb: 27.8`,
  `call_count: 265`, `call_seconds_min: 7.6`, `call_seconds_max: 1800.1` (the one
  logged timeout), `call_seconds_mean: 65.3`.
- **Exit:** clean. The script's own closing log line
  (`=== corpus_reader_index finished ===`) fired; no crash, no OOM (checked `dmesg`),
  no unhandled exception.
- **Kill conditions never triggered:** `MAX_RUN_WALL_SECONDS=6h` (actual 4h53m),
  `MAX_OWN_RSS_MB=500` (actual peak 28MB), `MAX_CONSECUTIVE_FAILURES=5` (actual: 2
  isolated failures, never consecutive).
- **Per-call timeout:** `OLLAMA_TIMEOUT_SECONDS=1800`, set from this script's own
  piloted per-document timings (a 36-line document completed in 19.2s; the corpus's
  ~90th-percentile document, 665 lines, and its largest, 1,883 lines, were piloted
  separately), not copied from the classifier's 120s title-batch precedent — these are
  whole-document comprehension calls, not one-line classifications, and the two are not
  comparable.

### Coverage

- Corpus: 267 `.md` files under `brain/decisions/` (282 files total including 6
  gate-set CSV/JSON files and 9 heatmap-pass companion `.json` files, correctly excluded
  from indexing as non-decision-document artifacts).
- **263 indexed successfully. 2 explicit failures. 2 files never attempted.**
  - Failures (`brain/corpus_reader_failures.jsonl`):
    - `2026-06-29-overhang-ledger.md` — `request_failed: timed out` (hit the 1800s
      ceiling; raw response not applicable, the call itself never returned).
    - `2026-09-10-own-market-calibration.md` — `Failed to parse response as JSON
      object: Invalid \escape: line 28 column 40 (char 683)` — the model emitted a
      malformed escape sequence inside a JSON string value; per the hard-fail contract,
      this was flagged and the run moved on, not retried.
  - Never attempted: `brain/decisions/archive/MASTER_HANDOVER_2026-05-20.md` and
    `brain/decisions/archive/MASTER_HANDOVER_server-pre-setup-1.md` — the script's file
    discovery does not recurse into `archive/`. This was not a per-document failure; it
    is a scoping gap in the script, found during this verification, not before. Recorded
    under "what was not determined," below — not silently absorbed into the 263/267
    figure.

---

## 2. Schema and justification

One flat JSON record per document, written to `brain/corpus_reader_index.jsonl`.
Every field is extractive (present in the text), not inferred:

| Field | What it captures | Why |
|---|---|---|
| `path`, `indexed_at`, `filename_date`, `line_count`, `byte_size` | Identity and size | Needed to query/join the index; mechanically derived, not model output. |
| `first_heading`, `title` | The document's own opening heading | Cheap, always-present anchor; two near-duplicate fields exist because the model was asked for both a mechanical first-line capture and a title extraction — in practice near-identical, occasionally differing on `#`-prefix stripping (cosmetic, see §3). |
| `document_type` | One of pre-registration / result / diagnosis / session-summary / decision / other, **taken from the document's own self-description** | Per the tier25 scoping doc's bound: this project has a documented 2026-05-14 precedent (`90a2e26`) of a local model fabricating verdicts when asked to judge a document rather than describe it. Classifying a document's *stated kind* is extractive; classifying its *quality or importance* would not be, and is explicitly out of scope. |
| `self_stated_verdict` | Any verdict/outcome the document states about itself | Same rationale — quoted, not synthesised. |
| `commit_refs` | Commit hashes the document cites | Traceability into git history. |
| `artifact_paths_cited` | File/script/document paths the document cites | Traceability into the repo. |
| `rq_str_lh_ids` | RQ-, STR-, or LH- identifiers mentioned | Cross-referencing into the research-question/strategy registries. |
| `numeric_findings` | `{value, context}` pairs — a number plus the surrounding phrase | Per Part 4's requirement: every numeric finding must be checkable against the source without re-reading the whole document. Capped per document (documented in the script) to keep both the schema and the spot-check tractable — this is a set of traceable pointers, not an exhaustive re-statement. |
| `supersedes`, `superseded_by` | Any explicit supersedes/superseded-by/amends relationship the document declares | Declared, not inferred from dates or filenames. |
| `has_what_was_not_determined_section`, `what_not_determined_excerpt` | Whether the document has a self-described "what was not determined" (or equivalent stop-condition/open-question) section, and its text | This corpus's own convention (pre-registration stop conditions, "what was not determined" sections) makes this extractive — see §3 for where detection missed a differently-titled equivalent section. |
| `heatmap_flagged`, `over_safety_margin` | Mechanical flags: was this path mentioned as a marker-hit in a heatmap pass; did the prompt exceed the safety-margin fraction of context | Computed by the script, not the model. |
| `schema_valid`, `schema_problems` | The script's own structural check of its own output | Not model-derived — see §3.1. |

**Fields considered and dropped:** a document-level "CLOSED" / "OPEN" pair was proposed
in the scoping brief. Not implemented as a separate pair distinct from
`self_stated_verdict` + `has_what_was_not_determined_section` +
`what_not_determined_excerpt`: on inspection, every corpus instance of a document
declaring something "closed" is already captured as its `self_stated_verdict` (e.g.
"STOPPED, not implemented", "Investigation complete — change nothing"), and every
instance of "open" is already captured by the not-determined section. A separate
CLOSED/OPEN pair would either duplicate these fields or require judging closure that
isn't stated in those terms — out of scope per the fabrication precedent. Dropped, not
built, and said here rather than left silent.

**No field requires an opinion.** No importance, relevance, or quality field exists.

---

## 3. Verification (Part 4, in full)

### 3.1 Schema validation — every record

All 263 records have every required field present with the correct type (0 missing
fields, 0 type errors). Independent re-validation against the 6-value `document_type`
enum found exactly the same 5 violations the script's own `schema_valid` flag already
caught — **100% agreement, 0 false negatives, 0 false positives** for this specific
check:

- `2026-06-30-str002-thesis-cell-analysis.md` — `'analysis'`
- `2026-08-22-incident-report-correction.md` — `'correction'`
- `2026-08-31-geo-scoping-inventory.md` — `'inventory'`
- `2026-08-31-relevance-classifier-design.md` — `'design'`
- `2026-09-05-canonical-skill-metric-design.md` — `'design'`

All five are flagged, none silently accepted — the enum-adherence failure the schema
guards against works as designed. **This check does not catch content-accuracy
problems** — two of these five records are separately shown below (§3.2) to also
contain fabricated `artifact_paths_cited` entries despite `schema_valid: true` not
applying there (schema validity only checks structure/enum, not content truth).

### 3.2 Manual spot-check — 15 documents read directly against their records

Sample: 3 heatmap-pass documents (pass 1, 3, 5 — required minimum) + 12 documents drawn
at random (seeded) from the remaining 260 successful records. Every field on every
sampled document was read against the actual source file, not inferred from the
record.

**Per-field accuracy across the 15-document sample (~8 numeric findings × 15 docs ≈ 120
value/context pairs checked):**

| Field | Result |
|---|---|
| `title` | 15/15 correct. |
| `document_type` | No clear misclassifications in the sample, but several loose/coarse fits (e.g. `diagnosis` for a research-survey document, `session-summary` for a launch-status document) — usable as a rough signal, not a precise one. |
| `self_stated_verdict` | 15/15 traced to real text; 1 case used a section heading rather than the crispest interior sentence (not wrong, imprecise). |
| `commit_refs` | **Zero fabrications** across all 15 documents — every hash listed is a real citation in the source. **Recall gaps in 3/15**: `2026-08-21-step1-implementation.md` (1 of 4 hashes missed, inside a code fence), `2026-08-24-sweep-segment3.md` (3 of 6 missed, from a dense opening paragraph), `2026-09-12-heatmap-pass1-asset-inventory.md` (1 of 10 missed, phrased as `generator_commit X` rather than `(commit X)`). Estimated precision 100%, recall ~85–90%. |
| `numeric_findings` (values) | **100% accurate** — every one of ~120 checked values is genuinely present in the source. |
| `numeric_findings` (context) | 2 confirmed defects out of ~120 (~1.7%): `2026-09-06-directional-skill-persistence-test-run-2.md`'s `"0.4521"` entry has an invented parallel sentence not literally in the source (the real text states the parallel claim only for the *lower* CI bound); `2026-09-09-background-backfill-ingest-evaluation.md`'s `"20,285"` entry is **misattributed** — the record's context ties it to `worker-stubbed (background_backfill)`, but the source explicitly attributes 20,285 to `live_monitoring` and ties the actual worker-stubbed figure (220) to a separate, correctly-labeled entry. Low rate, but each defect would actively mislead a reader who trusted the context without checking the source. |
| `has_what_was_not_determined_section` | 2/2 true-positive instances checked, both accurate. 1 likely false negative: `2026-09-12-heatmap-pass3-external-research.md` has an equivalent section titled "What this pass did NOT cover" that was not counted — detection appears to key on the literal phrase rather than functional equivalents. |
| `supersedes` | 1 instance checked where the cited hashes/text were accurate but the relationship *type* was arguably mischaracterized — `2026-09-06-directional-skill-persistence-test-run-2.md` is labeled as "superseding" the amendments it actually *applies/depends on*, not replaces. Single data point. |
| `rq_str_lh_ids` | **Unreliable for the RQ- component.** STR- and LH- identifiers were captured correctly in every instance checked. RQ- identifiers were **missed in 6 of the 15 sampled documents that contained one**, ranging from single misses (`2026-06-29-comprehensive-elo-writer-map.md` missed `RQ-CONTESTED-001`; `2026-06-09-session-summary.md` missed 4 of 5 RQ-prefixed table entries) to severe under-capture (`2026-09-12-heatmap-pass3-external-research.md` missed at least 6 of ~11 RQ- ids used as inline section headers). One confirmed **fabrication in the opposite direction**: `2026-09-12-heatmap-pass5-shortlist.md`'s record lists `STR-004`, which does not appear anywhere in that document's text — plausibly bled in from the identifier's real presence elsewhere in the corpus. |
| `artifact_paths_cited` | **Unreliable — the most serious finding of this verification.** 3 documents had complete, accurate lists (0 errors). 1 document (`2026-06-24-session-summary.md`) had a **complete miss** — 0 paths captured despite ~15 bare script names in the text (e.g. `scripts/check_canonical_definitions.py`, cited explicitly). 2 documents contained **confirmed fabrications** — paths that do not appear anywhere in the source: `2026-08-30-geo-backlog-and-category-reach.md` lists `backfill_market_dates.py` and `daily_maintenance.py`, neither of which is mentioned in that document (both are real filenames elsewhere in the corpus); `2026-09-09-background-backfill-ingest-evaluation.md` lists `scripts/evaluate_new_trader_results.py`, also absent from that document's text. |

### 3.3 Heatmap-pass cross-check (required minimum: 3)

`2026-09-12-heatmap-pass1-asset-inventory.md`, `-pass3-external-research.md`, and
`-pass5-shortlist.md` were read in full against their own records (these documents
are themselves what "heatmap passes 1–5 recorded" — there is no separate external
ledger to check against). Disagreements found, not rounded away:

- Pass 1: missed commit hash `eaeabbc` (`generator_commit` phrasing) and RQ- id
  `RQ-CONTESTED-001`.
- Pass 3: missed at least 6 RQ- identifiers used as its own section headers
  (`RQ-VPIN-001`, `RQ-ILS-001`, `RQ-POSSIZE-001`, `RQ-SECTOR-001`,
  `RQ-CORRELATION-001`, `RQ-SCI-001`) while correctly capturing `RQ3.2`, `RQ4.1`,
  `LH-001`, `STR-004`; `document_type` classified as `diagnosis` for what is a
  research-survey document (loose fit); a functionally-equivalent
  not-determined-style section ("What this pass did NOT cover") was not detected.
  Everything else checked (title, verdict, commit_refs, numeric_findings) was
  accurate.
- Pass 5: one fabricated identifier (`STR-004`, not present in this document) inside
  an otherwise-correct `rq_str_lh_ids` list; everything else checked (title, verdict,
  4/4 commit_refs, 4/4 artifact_paths_cited, 8/8 numeric findings) was accurate.

### 3.4 Numeric findings traceability sample

Exceeded the required sample of 10: ~120 numeric findings were checked as part of
§3.2 across all 15 documents. Every value was confirmed present in the source (0
fabricated numbers). 2 of ~120 had a context string that would mislead a reader
checking it against the source without independently re-reading the surrounding
paragraph (detailed in §3.2). This is the concrete traceability failure mode the task
asked this check to surface, and it was found, not merely looked for.

### 3.5 Verdict

**The index is trustworthy overall and is being shipped**, with two fields named as
unreliable rather than presented as complete:

- **`rq_str_lh_ids` should be treated as a lower bound for STR-/LH- identifiers and
  unreliable for RQ- identifiers** — both under-captured (majority-miss rate when
  several RQ- ids appear together) and, in one case, fabricated. Do not use this
  field to claim a document does *not* reference a given RQ without checking the
  source.
- **`artifact_paths_cited` should not be trusted without spot-checking the specific
  record** — it can both miss real paths entirely and fabricate plausible-sounding
  absent ones. It is useful as a starting point for "what might this document
  reference," not as a citation-complete or citation-accurate list.

Every other field — `title`, `document_type` (as a coarse signal), `self_stated_verdict`,
`commit_refs` (as a high-precision lower bound), `numeric_findings` values, and
`has_what_was_not_determined_section` — held up well enough across the sample to use
directly, with the isolated exceptions named above.

---

## 4. What the index makes available (counts, not conclusions)

- **263 of 267 `.md` documents indexed** (98.5%); 2 explicit failures, 2 never
  attempted (see §1).
- **By document type:** session-summary 94, decision 87, diagnosis 54, result 13,
  pre-registration 10, design 2, analysis 1, correction 1, inventory 1 (the last 5 are
  the enum violations from §3.1).
- **By month:** 2026-03: 2, 04: 1, 05: 18, 06: 34, 07: 34, 08: 94, 09: 75, unknown
  (no filename date, e.g. `MASTER_HANDOVER_*.md`): 5.
- **33 documents declare an explicit `supersedes`/amends relationship. 0 documents
  declare `superseded_by`** — expected, since a document cannot know at write time
  what will later supersede it.
- **83 documents cite no commit hash. 32 cite no artifact path. 26 cite neither.**
  Given §3.2's finding that `commit_refs` and `artifact_paths_cited` both have real
  recall gaps, these "cites nothing" counts should be read as an upper bound on true
  citation-free documents, not an exact count.
- **32 documents have a self-described "what was not determined" (or clearly
  equivalent) section** — likely an undercount per §3.2's pass-3 finding.
- **94 documents have at least one RQ-/STR-/LH- identifier captured** — given the
  RQ- recall problem, likely an undercount of true RQ- coverage specifically.

## 5. Where it lives and how to query it

- Script: `scripts/corpus_reader_index.py`.
- Index: `brain/corpus_reader_index.jsonl` — one JSON object per line, one line per
  successfully indexed document.
- Failures: `brain/corpus_reader_failures.jsonl` — one line per failed document, with
  the error and (where available) the raw model response for inspection.
- Checkpoint (not committed — operational state): `brain/corpus_reader_state.json`.
- Query with `jq` or Python, e.g.: `jq 'select(.document_type=="decision")' brain/corpus_reader_index.jsonl`,
  or `python3 -c "import json; [print(r['path']) for r in map(json.loads, open('brain/corpus_reader_index.jsonl')) if r['rq_str_lh_ids']]"`.
  For `rq_str_lh_ids` or `artifact_paths_cited` specifically, treat a match as "worth
  checking the source," not as ground truth, per §3.5.

## 6. What was not determined

- Whether the 2 archived documents never attempted (`archive/MASTER_HANDOVER_2026-05-20.md`,
  `archive/MASTER_HANDOVER_server-pre-setup-1.md`) contain anything the shortlist or
  any RQ would care about — not read, not indexed, not assessed here.
- The true extent of the `rq_str_lh_ids` RQ- recall gap and the `artifact_paths_cited`
  fabrication rate across the full 263 records — only 15 were read directly; the
  defect rates above are sample estimates, not a full census. A targeted re-pass
  specifically re-extracting these two fields (or a second, independent model call
  per document for just these fields) was not attempted and would be needed before
  either field could be upgraded to "trustworthy."
- Whether the two confirmed `artifact_paths_cited` fabrications and the one
  `rq_str_lh_ids` fabrication (`STR-004`) share a common mechanism (e.g. contextual
  bleed from adjacent documents processed in the same run, versus the model's general
  training-time association with this corpus's real filenames) — not investigated;
  would matter for whether a schema or prompt change could fix it.
- Whether the GPU findings in §7 change the viable batch size or per-call timeout for
  a future re-run of the two failed/skipped/RQ-targeted-re-extraction documents — not
  assessed; this run's parameters were not revisited in light of §7.

## 7. The GPU question, resolved

The tier25 scoping document's assumption that this box's iGPU has a 4GB UMA VRAM
allocation and therefore runs a 30B model CPU-bound **is factually wrong as currently
configured**:

- `mem_info_vram_total` (sysfs): **8 GiB** dedicated VRAM — already double the 4GB
  the scoping doc assumed.
- `mem_info_gtt_total` (sysfs): **~43.1 GiB** — GTT (system RAM the GPU can address
  under this AMD Radeon 780M/Phoenix iGPU's unified-memory architecture, confirmed
  `uma: 1` in Ollama's own Vulkan device log), out of 86 GiB total system RAM.
- Ollama's own startup log for this run: `"offloaded 49/49 layers to GPU"`, model
  weights `17.1 GiB` on `Vulkan0`, KV cache up to `12.0 GiB` at this run's
  `num_ctx=131072` — **the entire model is GPU-resident**, not partially or CPU-bound.
  `sched.go` reports `~50.6 GiB` available to Ollama via Vulkan, far beyond the
  assumed 4GB ceiling.
- Observed throughput (this run's own telemetry): mean **65.3s/call**, min 7.6s, for
  documents ranging 18–1,883 lines — consistent with genuine GPU-accelerated
  inference, not CPU-bound execution (a CPU-only 30B q4 model would typically be
  several times slower per call at this context size).

**The scoping document's CPU-bound assumption should be treated as incorrect**, and
that changes the viable workload envelope for every local-agent candidate it
evaluated on that basis — the actual constraint is not "this box can't run a 30B
model at usable speed," it can, and did, unattended, for 4h53m with negligible driver
overhead (28MB peak RSS for the Python process). What the real ceiling is (concurrent
load, GTT contention with other processes, sustained multi-hour throughput under
production traffic) was not tested here and is not claimed.

---

*Corpus reader run 2026-09-19T13:21:20Z–18:14:01Z. Verification performed
2026-09-19, read-only, no production writes. Script, index, and failures log
committed alongside this document.*
