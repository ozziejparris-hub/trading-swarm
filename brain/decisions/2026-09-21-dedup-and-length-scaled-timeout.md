# Deterministic dedup + length-scaled timeout — verified offline, full corpus launched

**Date:** 2026-09-21. Follow-up to the fourth pilot (`258b860`,
`brain/decisions/2026-09-21-corpus-content-extraction-fourth-pilot.md`), which closed the
schema-shape and fabrication problems but left two mechanical issues: capped fields padded
with duplicate (not invented) items on the two longest documents, and a timeout that had
already been breached twice by different documents. Both are fixed here without another
model experiment — neither needed one — verified entirely against the three pilots'
existing artifacts, then the full corpus was launched. Covers Parts 1–4 of the task; Part 5
(launch) is reported in the commit log / operator channel, not committed here, since the
full-run artifact does not exist yet.

---

## Part 1 — Deterministic dedup

**Definition:** two items within the *same field* of the *same record* are duplicates if
their `quote` strings are identical after `_normalize_ws()` — the exact whitespace-collapse
transform already used and tested for the verifier's "normalized" tier. Comparison is never
made across fields or across documents. First occurrence is kept.

**Why this transform and not the looser "structural" tier:** `_normalize_ws()` only
collapses whitespace runs and trims — it cannot make two different passages compare equal
unless every non-whitespace character already matched. That's what makes "identical after
this transform" conservative: a false-positive removal (collapsing two genuinely distinct
claims) is structurally impossible unless the two quotes were already the same text modulo
line-wrap whitespace. The "structural" tier (also strips `**`, backticks, `|`, heading/list
markers) was available and considered, but rejected here — it does more transformation than
the safety property requires, and every duplicate actually observed in the fourth pilot's
artifacts was already identical under plain whitespace normalization, so the looser tier
would buy no additional recall at the cost of a weaker safety argument. The conservative
failure direction this definition takes: a duplicate that differs only in markdown
decoration would NOT be caught. That's accepted — missing a duplicate is the stated
acceptable failure mode, collapsing a distinct item is not, and no instance of the missed
case was found anywhere in the four artifact sets checked (Part 3 below).

This is a genuinely conservative definition, not one requiring judgement to make safe: no
manual tuning or fuzzy-matching threshold is involved anywhere in it.

**Implementation** (`scripts/corpus_content_extractor.py`): `dedup_field()` returns
`(kept, removed)`; `dedup_record()` applies it to all 7 claim fields and attaches three new
keys — `record["deduped"][field]` (post-dedup list), `record["padding_removed"][field]`
(count), `record["padding_removed_items"][field]` (the removed items themselves, for audit).
**The raw top-level fields (`record[field]`) are never modified or shortened** — every
record keeps the full, unedited model output alongside the deduplicated view. Wired into
`process_one()`, so every document processed by the full run carries both.

## Part 2 — Length-scaled timeout

**Data:** reconstructed `(line_count, call_seconds)` for every successful/returned call
across the pilot (12 docs), re-pilot (7 of 8 — one timed out), and fourth pilot (7 of 8 plus
the 2,400s supplementary retry) artifacts, from each record's `indexed_at` timestamp delta
within its run — 24 points total. (The task's "four pilots" matches the numbering in the
script's own docstring; only these three artifact sets exist on disk to reconstruct from.)

**Fit:** a through-origin linear fit (`seconds = k × lines`, no intercept) gives
**k = 0.539 s/line**. An unconstrained OLS fit was tried first and rejected — its intercept
went negative (−35.8), which is a modeling artifact of noisy short documents pulling the
line down, not a real "negative fixed cost," and it made ratio-based safety margins blow up
for small documents. Through-origin avoids that.

**Safety margin:** the worst observed ratio of actual-to-predicted time in the 24-point
dataset is 2.55× (the smallest, noisiest document, where fixed per-call overhead dominates
and a through-origin fit under-predicts most). Applied multiplier: **2.7×** (worst observed
+ small headroom).

**Formula:** `timeout(lines) = clip(0.539 × lines × 2.7, 300, 3600)` seconds — a 300s floor
(covers small-document fixed overhead) and a **3,600s hard ceiling** (the kill condition the
task asked to preserve: no single document, however long, can run past this).

**Coverage check** — every one of the 24 historical returned calls against the timeout the
new formula would have assigned it:

| lines | max observed (s) | formula timeout (s) | covered |
|---:|---:|---:|:---:|
| 167 | 229.6 | 300 | ✅ |
| 268 | 350.9 | 390 | ✅ |
| 301 | 191.2 | 438 | ✅ |
| 315 | 140.5 | 458 | ✅ |
| 412 | 177.9 | 600 | ✅ |
| 436 | 148.3 | 635 | ✅ |
| 498 | 290.3 | 725 | ✅ |
| 521 | 188.4 | 758 | ✅ |
| 527 | 319.1 | 767 | ✅ |
| 666 | 217.3 | 969 | ✅ |
| 1,066 | 574.5 | 1,551 | ✅ |
| **1,884 (largest, corpus max)** | **1,680.3** | **2,742** | ✅ |

All 24 points covered (`tests/test_corpus_content_extractor.py::TestTimeoutForLines::test_covers_every_returned_call_in_pilot_history`).
The largest document — `2026-08-21-discovery-gap-closure-prereg.md`, confirmed the actual
maximum across the live 275-document corpus, not just the pilot sample — gets **2,742s**,
above both its observed real need (1,680.3s) and the 2,400s ceiling the fourth pilot's
supplementary retry used successfully.

---

## Part 3 — Offline verification, no model run

### Dedup: results on the fourth pilot's artifact

Ran `dedup_record()` over `brain/corpus_content_fourth_pilot.jsonl` and
`brain/corpus_content_fourth_pilot_supplementary_2400s.jsonl`:

| document | field | removed |
|---|---|---:|
| `MASTER_HANDOVER_2026-09-05.md` | explicitly_open | 2 |
| `MASTER_HANDOVER_2026-09-05.md` | proposed_not_done | 1 |
| `2026-08-21-discovery-gap-closure-prereg.md` (2,400s supplementary) | explicitly_open | 5 |
| `2026-08-21-discovery-gap-closure-prereg.md` | proposed_not_done | 5 |
| `2026-08-21-discovery-gap-closure-prereg.md` | decisions_recorded | 4 |
| `2026-08-21-discovery-gap-closure-prereg.md` | failures_and_causes | 1 |
| `2026-08-21-discovery-gap-closure-prereg.md` | contradicts_or_corrects | 4 |

This exactly matches the duplication counts manually found and reported in the fourth
pilot's decision document — the same two documents, the same fields, the same counts.
**Confirms the dedup catches the specific padding it was built to catch.**

### False positives — every one of the 24 removals manually inspected

24 total duplicates were found across all four artifact sets (3 on `MASTER_HANDOVER_2026-09-05.md`,
19 on `2026-08-21-discovery-gap-closure-prereg.md`'s supplementary run, and — new finding,
below — 2 on `2026-09-19-corpus-reader-deterministic-field-fix.md` in the *original* pilot).
Every single removed item was printed alongside the survivor it matched and compared by
hand, not sampled:

**All 24 removed quotes are byte-for-byte identical to their surviving counterpart's
quote** — not merely equal after normalization, the literal same substring of the source
document, cited twice. In several cases the model's `claim` paraphrase differs slightly
between the kept and removed copy (e.g. "The classifier's recall failure is not yet
resolved" vs. "The formal decision on the relevance classifier's fate is not yet made" —
both quoting the identical §3.10 sentence), but the evidentiary anchor — the quote itself —
is identical every time. **Zero false positives.** No removed item cited a different
passage than its survivor. The negative-control shape this task warned about (two distinct
claims that happen to share wording) did not occur once in any of the 24 real removals
found; `tests/test_corpus_content_extractor.py`'s
`test_negative_control_shared_wording_different_passages_both_survive` constructs that
shape synthetically (using the real, genuinely-distinct 08-21 checklist items as the basis)
and confirms both survive when they're not in fact byte-identical.

### Original pilot and re-pilot: untouched where not padded, one new finding

Ran the same dedup pass over `brain/corpus_content_pilot.jsonl` (12 docs) and
`brain/corpus_content_repilot.jsonl` (7 docs, 1 failure):

- **Re-pilot: zero duplicates in all 7 records**, including the same two long documents
  (`2026-08-21-discovery-gap-closure-prereg.md`, `MASTER_HANDOVER_2026-09-05.md`) that show
  heavy duplication under the fourth pilot's schema-constrained approach. This is a genuine
  new finding, not something the task asked for but worth recording: **duplication
  correlates with the `maxItems`-constrained-decoding approach itself, not simply with
  document length** — the re-pilot processed the identical two long documents via the
  worked-example approach (no `format` schema) and produced no duplicates on either. The
  schema's hard cap appears to be what induces the model to repeat content near the
  boundary; a prose-only cap (re-pilot) or no cap-adjacent pressure did not.
- **Original pilot: 11 of 12 documents come through with zero removals — untouched**, as
  required. One exception, not previously known: `2026-09-19-corpus-reader-deterministic-field-fix.md`
  (315 lines, not a long document) had 2 duplicates (`proposed_not_done`: 1,
  `contradicts_or_corrects`: 1), both manually confirmed genuine (byte-identical quotes,
  paraphrased claims, included in the 24 above). This shows the duplication mechanism isn't
  exclusively new to the fourth pilot's constrained decoding — it existed, rarely, even in
  the very first pilot — but it is far more frequent and severe under the schema-constrained
  approach, and concentrated on long documents there specifically.

### Unit tests

`tests/test_corpus_content_extractor.py` — 23 tests, all passing
(`python3 -m pytest tests/test_corpus_content_extractor.py -v`): dedup correctness (no-op on
distinct items, exact/whitespace-only duplicate removal, order preservation, malformed-item
handling, the negative control described above), the timeout formula (floor, ceiling,
monotonicity, largest-document coverage, and the full 24-point historical coverage check),
and the maintenance guard (no log file, started/not-finished, started/finished, a prior
day's cycle not leaking into today's check, and the wide-tail-scan retry path).

---

## Part 4 — Pre-launch checks

- **Document count:** 275 (`DECISIONS_DIR.rglob("*.md")` — this script already recurses into
  `archive/`, unlike the structural pass; 2 of the 275 are under `archive/`). Largest
  document confirmed as `2026-08-21-discovery-gap-closure-prereg.md` at 1,884 lines — the
  same document the timeout formula was validated against directly.
- **Projected wall time:** two estimates, reported as a range rather than a single number
  because they disagree meaningfully and I don't want to hide that:
  - Flat mean (fourth pilot's actual returned-call mean, 268.3s) × 275 docs ≈ **20.5h**.
  - Length-weighted (k=0.539 s/line × 71,930 total corpus lines) ≈ **10.8h**.
  - The flat-mean figure is likely an overestimate: the fourth pilot's 8-document sample
    deliberately included the corpus's two longest documents (1,884 and 1,066 lines), which
    over-represents long, slow documents relative to their true ~1% share of the 275-document
    corpus. The length-weighted estimate is probably closer to reality. Either way, both are
    plausible run lengths, not implausible ones — no stop condition triggered here.
  - Sleep-between-calls overhead: 275 × 1.0s ≈ 4.6 minutes, negligible against either
    estimate.
- **The maintenance overlap:** implemented as `maintenance_in_progress()` in
  `scripts/corpus_content_extractor.py`, checked before every document in the main loop (not
  just at startup). `daily_maintenance.py` deliberately has no PID/lock/sentinel file or DB
  flag of its own (see its own comment, and
  `brain/decisions/2026-09-10-geo-backfill-wiring-implementation.md`, which rejected exactly
  those mechanisms for a similar concurrency question elsewhere in this codebase) — but its
  wrapper script writes a plain append-only log with bracketed-ISO8601 "Starting"/"Finished"
  lines, and that's the signal this reads rather than inventing a second one. The function
  reads only the log's tail (64KB, widened ×4 and retried if no marker is found there,
  bounded by file size) rather than the whole 750K+-line file, since this may be checked
  before every one of 275 documents. If a "Starting" line has no "Finished" line after it
  (compared by byte position in the append-only file, not by parsing timestamps), the main
  loop pauses, polling every 120s and logging every 10 minutes, until it clears, then
  resumes with the same document — the existing path-based checkpoint means a pause here
  costs only wall time, never correctness or a skipped/duplicated document. This job never
  writes to the SQLite database (reads markdown, writes jsonl), so it wasn't expected to
  need this, but 2026-09-20's maintenance caused a lock storm on its own and GPU/CPU
  contention during a multi-hour maintenance run is unmeasured, so this is a load-avoidance
  wait, not a correctness fix.
- **No other corpus process running:** confirmed — no `corpus_content_extractor` or
  `corpus_reader_index` process in `ps aux`, no resident Ollama model (`ollama ps` empty)
  before launch.
- **Disk space:** 1.1T free on the filesystem holding the repo (39% used of 1.8T). The
  jsonl artifact for the full corpus will be on the order of tens of MB at most (the 7-record
  fourth-pilot artifact is 95KB) — not a constraint.
- **Maintenance status at launch time (2026-09-21T16:14 UTC):** today's run finished at
  10:37 UTC, 5.5 hours before launch. `maintenance_in_progress()` returns `False`. Next run
  is tomorrow 06:00 UTC (~13.75h away) — inside the ~10.8–20.5h projected window, so this run
  is very likely to cross paths with it; the guard above exists for exactly this case and
  will pause rather than run alongside it.

No stop condition was triggered: nothing from a previous run is active, and the projected
wall time is plausible under either estimate.

---

## Part 5 — Launch

Launched after Parts 1–4 passed, with: `qwen3-coder:30b-a3b-q4_K_M`, the `format` schema
constraint (`maxItems`, no `minItems`), temperature 0, caps-as-ceilings prompt, the new
length-scaled timeout, dedup applied and padding recorded per document, stateless per
document, path-based resumable checkpoint, per-run telemetry, existing kill conditions
(6h run wall time, 500MB own RSS, 5 consecutive failures) plus the new maintenance-overlap
wait. Detached with `setsid`+`nohup`+`disown`. Launch details (PID, start time, first
document, telemetry confirmation) are in the commit/operator report accompanying this
document, not restated here since the full-run artifact itself is explicitly out of scope
for this commit.
