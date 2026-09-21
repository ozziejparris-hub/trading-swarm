#!/usr/bin/env python3
"""
Corpus content extractor: what each brain/decisions/ document CONCLUDED, not
just its shape.

Companion to scripts/corpus_reader_index.py (the structural pass,
brain/corpus_reader_index_v2.jsonl) -- deliberately a SEPARATE artifact, not
a modification of it. The structural index captures type/verdict-line/
commits/identifiers; it says nothing about what a document found, left open,
proposed, decided, or corrected. Heatmap pass 5's stated limitation is that
its shortlist rests on ~190 documents no pass ever read in depth.

Design principle (the whole point of this script): every extracted claim
carries a verbatim quote AND a line number, and the line number is NEVER
asked of the model -- it is computed here, deterministically, by searching
for the model's quote in the actual source text. An LLM asked to count
lines in a 1,800-line document will get it wrong; an LLM asked to copy a
short span of text it just read, verified afterward by exact string search,
is the same anchored-extraction bet that already proved reliable for
corpus_reader_index.py's title/self_stated_verdict/numeric-findings fields
(15/15, 15/15, ~120/120 traced correct) and unreliable for its free-recall
fields (rq_str_lh_ids, artifact_paths_cited -- both under- and over-capture,
including outright fabrication). This script never asks the model to recall
an identifier or path from memory; it only ever asks for a copy of text it
was just given, checked against that same text afterward. See
brain/decisions/2026-09-20-corpus-content-extraction-pilot.md for the full
schema rationale and pilot results.

Infrastructure matches corpus_reader_index.py deliberately (same box, same
proven pattern): stateless per document, qwen3-coder:30b-a3b-q4_K_M via
localhost:11434/api/generate, strict JSON contract, fence stripping,
hard-fail on parse error (flag and move on, no retry-until-parses), a
path-based keyset cursor (not OFFSET -- see that script's own comment on
the 2026-09-13 backfill_market_categories.py incident for why), kill
conditions on wall clock / own RSS / consecutive failures, and per-run
telemetry (wall time, CPU seconds, RSS start/peak/end, call count, per-call
duration).

Differs from it in scope: RECURSES into brain/decisions/archive/ -- the
structural pass did not, and missed archive/MASTER_HANDOVER_2026-05-20.md
and archive/MASTER_HANDOVER_server-pre-setup-1.md entirely (confirmed in
brain/decisions/2026-09-19-corpus-reader-schema-and-verification.md, section
1: "never attempted... the script's file discovery does not recurse into
archive/").

Re-pilot (2026-09-20, second pass): the first pilot found 6 of 12 documents
returned every field as a flat list of bare strings instead of the required
{claim, quote} objects -- not length-correlated, content accurate, just the
wrong shape roughly half the time. Fix tested: one worked example added to
the prompt, isolated deliberately. It raised the schema pass rate (0/6 ->
5/6) but cost ~2x projected runtime, ~11-36% extraction breadth on controls,
a new timeout failure, and produced two confirmed fabrications in
`explicitly_open` on the largest document -- the model generalized the
pattern of that field's genuine items into two plausible-but-unsupported
ones, apparently reaching for the field's cap (8 requested, 8 produced, 6
real). Separately, verify_record_quotes() gained a third "structural" tier
(markdown-decoration-aware: strips **, backticks, |, heading/list markers,
then compares) between "normalized" and "unverified", reported as its own
distinct category -- never folded into "exact". See
brain/decisions/2026-09-20-corpus-content-extraction-repilot.md.

Fourth pilot (2026-09-20, third pass) -- two isolated changes replacing the
worked example, targeting the two costs above separately:

  CHANGE A: constrained decoding via Ollama's /api/generate `format`
  parameter (a JSON schema; supported since Ollama 0.3.0, confirmed on this
  box's 0.22.1 with a minimal proof call before this run -- see the decision
  doc). This makes a schema-shape violation impossible to generate, not
  merely discouraged, and testing reports it also speeds generation (no
  tokens spent on formatting decisions). The worked example was REMOVED when
  this was added -- testing both together would make the result
  unattributable. temperature set to 0 (was "low").

  CHANGE B: every array field's cap is enforced structurally via the JSON
  schema's `maxItems` -- not just described in prose as before. CRITICALLY,
  no field sets `minItems`: confirmed by inspection of GENERATION_SCHEMA
  below (every array has type+items+maxItems, no minItems key anywhere) and
  by a pre-flight proof call that an empty array is genuinely produced when
  nothing qualifies. A `minItems` constraint would force the model to emit
  N items even when fewer exist, making the exact fabrication mechanism
  that produced the two confirmed fabrications structurally mandatory
  instead of merely likely -- the opposite of what this change is for.
  Prose in EXTRACTION_PROMPT was also reworded from "(max N)" to a ceiling
  framing: extract every genuinely-present item, returning fewer -- including
  zero -- is correct.

  A pre-flight proof also found the schema constraint ALONE does not
  prevent fabrication -- a naive prompt without the real anti-fabrication
  instruction still invented content under an empty-array-permitting
  schema. Shape and truthfulness are enforced by different mechanisms here:
  the schema (`format`) governs shape, the prompt's explicit "do not
  invent" instruction plus permitted empty lists governs content honesty.
  Both are necessary; neither alone was sufficient in testing. See
  brain/decisions/2026-09-20-corpus-content-extraction-fourth-pilot.md.

Fourth pilot's own follow-up found two remaining mechanical problems, both
fixed here (2026-09-21) WITHOUT another model experiment -- neither needed
one:

  DEDUP: on the two longest documents, capped fields came back with real,
  verified quotes repeated to reach maxItems -- the same "reach for the
  cap" drive as the fabrication Change B fixed, displaced into repetition
  once outright invention was blocked. dedup_record() removes it
  deterministically post-hoc: two items in the same field of the same
  record are duplicates if their `quote` strings are identical after
  _normalize_ws() -- the SAME whitespace-collapse transform already used
  and tested for the "normalized" verification tier, reused rather than
  reinvented. This transform only ever collapses whitespace; it cannot
  turn two different passages into the same string, which is what makes it
  safe to remove on -- a looser comparison (e.g. the "structural" tier,
  which also strips markdown decoration) was deliberately NOT used here,
  because it does more than the safety property requires. First occurrence
  is kept; the raw (pre-dedup) list is never modified or discarded --
  every record carries both `record[field]` (raw, as extracted) and
  `record["deduped"][field]` (post-dedup), plus `record["padding_removed"]`
  (count per field) and `record["padding_removed_items"]` (the actual
  removed items, for audit). See
  brain/decisions/2026-09-21-dedup-and-length-scaled-timeout.md for the
  offline verification against all three prior pilots' artifacts,
  including manual inspection of every single removal.

  LENGTH-SCALED TIMEOUT: the flat 1200s ceiling was set from one
  12-document sample and had already been breached twice (differently) by
  the second and fourth pilots. Replaced with a timeout derived from a
  through-origin linear fit of call_seconds against document line_count
  across all 24 successful/returned calls in the pilot + re-pilot + fourth
  pilot artifacts (k=0.539 s/line), scaled by a safety multiplier (2.7x)
  set from the worst observed ratio of actual-to-predicted time in that
  same dataset (2.55x, on the smallest, noisiest document), with a 300s
  floor for small documents and a 3600s hard ceiling so no single document
  can run indefinitely regardless of length. See the decision doc for the
  fit, residuals, and full coverage check against every returned call in
  the historical data.

STATELESS PER DOCUMENT. Does not synthesise, rank, or draw conclusions
across documents -- that is a separate, later task by design.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DIR = REPO_ROOT / "brain" / "decisions"
INDEX_FILE = REPO_ROOT / "brain" / "corpus_content_index.jsonl"
STATE_FILE = REPO_ROOT / "brain" / "corpus_content_state.json"
FAILURES_FILE = REPO_ROOT / "brain" / "corpus_content_failures.jsonl"
TELEMETRY_FILE = REPO_ROOT / "logs" / "corpus_content_telemetry.jsonl"
LOG_FILE = REPO_ROOT / "logs" / "corpus_content_extractor.log"

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3-coder:30b-a3b-q4_K_M"

# Same fixed-for-the-whole-run rationale as corpus_reader_index.py: a
# different num_ctx per call forces an Ollama runner reload (~13s, full
# 17GB+ model), not just a bigger per-call allocation. One value, sized to
# the corpus's largest document with headroom, paid once.
OLLAMA_NUM_CTX = 131072
NUM_CTX_SAFETY_FRACTION = 0.85

# Per-call wall-clock ceiling -- LENGTH-SCALED (2026-09-21), replacing the
# flat 1200s figure the fourth pilot breached (the 1,884-line document
# needed 2,400s). Derived from all 24 successful/returned calls across the
# pilot, re-pilot, and fourth pilot artifacts: a through-origin linear fit
# of call_seconds against document line_count gives k=0.539 s/line. Applied
# with a 2.7x safety multiplier -- set from the worst observed ratio of
# actual-to-predicted time in that same 24-point dataset (2.55x, smallest/
# noisiest document, where per-call fixed overhead dominates and a
# through-origin fit under-predicts most) plus a small margin -- so the
# formula covers every historical returned call, not just the mean case.
# See brain/decisions/2026-09-21-dedup-and-length-scaled-timeout.md for the
# fit, residuals, and the full per-point coverage check.
TIMEOUT_SECONDS_PER_LINE = 0.539
TIMEOUT_SAFETY_MULTIPLIER = 2.7
MIN_TIMEOUT_SECONDS = 300
# Hard absolute ceiling -- the kill condition length-scaling itself doesn't
# have: no single document, however long, can make one call run past this.
MAX_TIMEOUT_SECONDS = int(os.environ.get("CORPUS_CONTENT_MAX_TIMEOUT_SECONDS", "3600"))


def timeout_for_lines(line_count: int) -> int:
    """
    Per-call Ollama request timeout for a document of `line_count` lines.
    max(MIN_TIMEOUT_SECONDS, k * lines * SAFETY_MULTIPLIER), capped at
    MAX_TIMEOUT_SECONDS. See the constants above and the decision doc for
    where k and the multiplier come from -- fit to observed data, not
    guessed.
    """
    scaled = TIMEOUT_SECONDS_PER_LINE * line_count * TIMEOUT_SAFETY_MULTIPLIER
    return int(min(MAX_TIMEOUT_SECONDS, max(MIN_TIMEOUT_SECONDS, scaled)))


# --- daily_maintenance overlap guard (2026-09-21) --------------------------
#
# This job only reads brain/decisions/*.md and writes jsonl -- it never
# touches the SQLite database -- so DB lock contention with
# daily_maintenance.py is not expected. But daily_maintenance caused a lock
# storm on its own on 2026-09-20, and GPU/CPU contention between an Ollama
# inference run and a ~4-16 hour maintenance run is unmeasured, so a
# long-running corpus job launched in the evening is made to wait out any
# daily_maintenance run it crosses paths with rather than run alongside it.
#
# daily_maintenance.py deliberately has no PID/lock/sentinel file or DB flag
# of its own -- see scripts/daily_maintenance.py's own comment (and
# brain/decisions/2026-09-10-geo-backfill-wiring-implementation.md, which
# rejected a lock/sentinel file, a DB flag, and running-process detection in
# favor of checkpoint-recency for the same kind of concurrency question
# elsewhere in this codebase). Its wrapper script does write a plain,
# append-only log with bracketed-ISO8601 "Starting"/"Finished" lines --
# that is the one signal that already exists, so this reads it rather than
# inventing a second mechanism.
MAINTENANCE_LOG_FILE = Path("/home/parison/projects/first-repo/logs/daily_maintenance.log")
MAINTENANCE_START_MARKER = "Starting daily-maintenance"
MAINTENANCE_FINISH_MARKER = "Finished daily-maintenance"
MAINTENANCE_POLL_SECONDS = 120


def maintenance_in_progress() -> bool:
    """
    True if daily_maintenance.log's most recent "Starting" line has no
    "Finished" line after it. Reads only the log's tail (up to 64KB, grown
    if needed) rather than the whole multi-hundred-thousand-line file --
    this job may check before every document, so cost matters. The file is
    append-only in time order, so comparing the two markers' BYTE
    POSITIONS within the tail (not parsing their embedded timestamps) is
    enough to tell which is more recent -- deliberately not parsing the
    bracketed ISO8601 timestamp, since byte order already gives temporal
    order for free on an append-only log. Fails safe: any read or parse
    problem (missing file, unexpected format) returns False (not blocking)
    rather than stalling the run on a log-format surprise this job doesn't
    own.
    """
    if not MAINTENANCE_LOG_FILE.exists():
        return False
    try:
        size = MAINTENANCE_LOG_FILE.stat().st_size
        chunk = 65536
        with open(MAINTENANCE_LOG_FILE, "rb") as f:
            while True:
                read_size = min(chunk, size)
                f.seek(size - read_size)
                tail = f.read(read_size).decode("utf-8", errors="replace")
                last_start = tail.rfind(MAINTENANCE_START_MARKER)
                last_finish = tail.rfind(MAINTENANCE_FINISH_MARKER)
                if last_start != -1 or chunk >= size:
                    break
                chunk *= 4  # neither marker in this tail yet -- widen and retry
        if last_start == -1:
            return False  # no Starting line seen in the available tail
        if last_finish == -1 or last_finish < last_start:
            return True  # a Starting line with no Finished line after it
        return False
    except (OSError, UnicodeDecodeError):
        return False


DEFAULT_SLEEP_BETWEEN_CALLS = 1.0

MAX_RUN_WALL_SECONDS = 6 * 3600
MAX_OWN_RSS_MB = 500
MAX_CONSECUTIVE_FAILURES = 5

# Per-field caps -- same rationale as corpus_reader_index.py's
# MAX_NUMERIC_FINDINGS=8: these are traceable pointers back into the source,
# not an exhaustive re-statement, and an uncapped list would make the
# mechanical quote verification and the human spot-check both intractable.
MAX_QUESTION_ITEMS = 3
MAX_LIST_ITEMS = 10
MAX_CONTRADICTION_ITEMS = 5

LIST_FIELDS = (
    "findings",
    "explicitly_open",
    "proposed_not_done",
    "decisions_recorded",
    "failures_and_causes",
    "contradicts_or_corrects",
)
ALL_CLAIM_FIELDS = ("question_addressed",) + LIST_FIELDS


def _claim_quote_array(max_items: int) -> dict:
    """
    One array field's schema. `maxItems` enforces the cap structurally (the
    model cannot emit more than this many items -- constrained decoding
    makes it impossible, not just discouraged). `minItems` is DELIBERATELY
    ABSENT -- see GENERATION_SCHEMA's own docstring-comment for why this is
    checked, not assumed.
    """
    return {
        "type": "array",
        "maxItems": max_items,
        "items": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "quote": {"type": "string"},
            },
            "required": ["claim", "quote"],
        },
    }


# Constrained-decoding schema for Ollama's /api/generate `format` parameter
# (supported since Ollama 0.3.0; confirmed working -- shape enforced even
# under an adversarial prompt with no formatting instructions at all -- on
# this box's installed 0.22.1 before the fourth pilot was run; see the
# decision doc for the proof transcript).
#
# CHECKED, NOT ASSUMED: no key named "minItems" appears anywhere below. Every
# array's only length constraint is its maxItems ceiling; the JSON Schema
# default minItems is 0, so every array here permits an empty list. A
# minItems constraint would force the model to emit that many items even
# when fewer genuinely exist in the document -- structurally mandatory
# fabrication, which is the opposite of what CHANGE B is for. Grep this
# file for "minItems" before ever adding a field here; if it appears more
# than once (the one time in this comment), something has gone wrong.
GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "question_addressed": _claim_quote_array(MAX_QUESTION_ITEMS),
        "findings": _claim_quote_array(MAX_LIST_ITEMS),
        "explicitly_open": _claim_quote_array(MAX_LIST_ITEMS),
        "proposed_not_done": _claim_quote_array(MAX_LIST_ITEMS),
        "decisions_recorded": _claim_quote_array(MAX_LIST_ITEMS),
        "failures_and_causes": _claim_quote_array(MAX_LIST_ITEMS),
        "contradicts_or_corrects": _claim_quote_array(MAX_CONTRADICTION_ITEMS),
    },
    "required": list(ALL_CLAIM_FIELDS),
}

assert "minItems" not in json.dumps(GENERATION_SCHEMA), (
    "GENERATION_SCHEMA must never set minItems on any array -- see the "
    "comment above this schema and CHANGE B in the module docstring."
)


# --- prompt -------------------------------------------------------------

# No worked example (removed for the fourth pilot -- see module docstring:
# testing it alongside constrained decoding would make the result
# unattributable). Shape is now enforced by GENERATION_SCHEMA via Ollama's
# `format` parameter, not by prose or an example; every field description
# below is deliberately still a CEILING, not a target -- "up to N", never
# "N", because the model reaching for a stated maximum by inventing
# plausible-but-unsupported items is exactly the mechanism that produced
# the two confirmed fabrications in explicitly_open on the largest document
# in the third pilot.
EXTRACTION_PROMPT = """\
You are extracting what a project decision document CONCLUDED -- not its \
shape, its opinions about itself, or your judgment of it. Extract ONLY what \
the document explicitly states. Do not judge correctness, importance, or \
quality. Do not infer anything not written in the text.

Every field is a list of items; each item is EXACTLY:
{{"claim": "<your own short sentence stating what this item says, max ~25 words>", \
"quote": "<a VERBATIM copy-paste of the exact text from the document that \
supports this claim -- must be an exact substring of the document text \
below, character for character, not paraphrased, not corrected for typos, \
not shortened with ellipses>"}}

Do NOT include a line number -- it will be computed separately from your quote.

Fields (each has an upper limit on how many items it will accept, stated \
below as "up to N" -- that limit is a CEILING, not a target and not a goal \
to reach. Extract every item the document genuinely and explicitly \
supports, however many that is. Returning fewer than the limit -- including \
zero -- is the CORRECT answer whenever fewer than the limit genuinely \
exist. Inventing an item to approach or reach the limit is a worse outcome \
than leaving the field short or empty; it will be mechanically checked \
against the source and flagged):

question_addressed (up to {max_q}): what the document states it set out to \
  answer, investigate, or decide. Usually near the top.
findings (up to {max_list}): what the document states it found, discovered, \
  measured, or concluded.
explicitly_open (up to {max_list}): what the document explicitly states was \
  NOT determined, left open, deferred, or unresolved. This corpus commonly \
  uses a "What was not determined" heading or a stated stop condition --\
  look for those, but also any other explicit statement of what remains \
  unknown or undecided. Most documents genuinely have only a handful of \
  these, sometimes none -- do not pad the list by generalizing a pattern \
  from the genuine items into additional invented ones.
proposed_not_done (up to {max_list}): what the document proposes, \
  recommends, or schedules for later -- work that has NOT yet been done, \
  as of this document.
decisions_recorded (up to {max_list}): decisions the document records as \
  having been taken (a choice made, a policy set, a thing paused/enabled/ \
  changed). If the document names who made the decision, that name should \
  appear inside the quote itself -- do not add a separate field for it.
failures_and_causes (up to {max_list}): things the document states were \
  tried and did not work, together with the stated reason -- the reason, \
  if given, should be part of the same quote (pick a quote span that \
  includes both the failure and its stated cause where they appear near \
  each other).
contradicts_or_corrects (up to {max_contra}): places the document explicitly \
  states it corrects, contradicts, retracts, or amends an earlier finding, \
  document, or claim.

An empty list [] is a normal, expected, and frequently correct answer for \
any of these fields. Do not invent an item to fill a field. A quote that is \
not an exact substring of the document text is worse than an empty list -- \
it will be mechanically checked and flagged as unverified.

DOCUMENT (path: {path}):
{text}
"""


def strip_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.startswith("```")).strip()
    return raw


def estimate_prompt_tokens(text: str) -> int:
    return len(text) // 3 + 700


# --- quote verification (mechanical, no model involvement) ---------------
#
# Three tiers, reported separately, never merged: "exact" (byte-for-byte
# substring), "normalized" (whitespace-only collapsing -- a wrapped line's
# internal newline/indentation folded to one space), and "structural" (also
# strips markdown decoration: **bold**, `backticks`, table `|` pipes,
# leading heading/list markers). The 2026-09-20 pilot manually traced 80
# "unverified" quotes across 6 documents and found zero fabrications --
# every one was genuine content the model had reformatted out of markdown
# table/heading syntax when it copied it. "structural" exists to stop that
# from being miscounted as inaccuracy, WITHOUT silently loosening what
# "exact" or "normalized" mean, and without becoming loose enough to match
# anything (see the deliberate limit below: a colon the model inserts
# between a table label and its value, which the source never had, is a
# real character difference and is correctly left unverified).

def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_HEADING_MARKER_RE = re.compile(r"#{1,6}[ \t]+")
_NUMBERED_LIST_MARKER_RE = re.compile(r"\d+\.[ \t]+")
_BULLET_MARKER_RE = re.compile(r"[-*][ \t]+")


def _structural_strip_with_map(text: str) -> tuple[str, list[int]]:
    """
    Returns (stripped_text, offset_map) where offset_map[i] is the index in
    `text` that stripped_text[i] came from. Strips, character-exactly:
    '**', backticks, replaces '|' with a single space, drops a leading
    heading/numbered-list/bullet marker at the start of each line, and
    collapses whitespace runs (including newlines) to a single space.
    Applied identically to both the document and the quote before
    comparison -- this is a shared lens, not test-only leniency.
    """
    out_chars: list[str] = []
    out_map: list[int] = []

    def emit_space(pos: int) -> None:
        # Never emit two consecutive spaces -- a '|' and an adjacent real
        # whitespace run must collapse to exactly one separator, or a
        # table cell's stripped form ends up with doubled spaces the
        # (single-space-normalized) quote can never match.
        if out_chars and out_chars[-1] == " ":
            return
        out_chars.append(" ")
        out_map.append(pos)

    i = 0
    n = len(text)
    at_line_start = True
    while i < n:
        if at_line_start:
            m = (_HEADING_MARKER_RE.match(text, i)
                 or _NUMBERED_LIST_MARKER_RE.match(text, i)
                 or _BULLET_MARKER_RE.match(text, i))
            if m:
                i = m.end()
                at_line_start = False
                continue
            at_line_start = False

        if text[i:i + 2] == "**":
            i += 2
            continue
        ch = text[i]
        if ch == "`":
            i += 1
            continue
        if ch == "|":
            emit_space(i)
            i += 1
            continue
        if ch.isspace():
            start = i
            while i < n and text[i].isspace():
                i += 1
            hard_wrapped_hyphen = (
                out_chars and out_chars[-1] == "-" and "\n" in text[start:i]
            )
            if hard_wrapped_hyphen:
                # "majority-\ngenuine" is one hyphenated word broken by a
                # markdown hard wrap, not "majority-" then a new word --
                # join with no separator rather than inserting a space a
                # human reader (and the model, copying it as one word)
                # would never perceive as there. Found via a genuine
                # verification false-negative in the 2026-09-20 re-pilot;
                # not a leniency added to raise the pass rate.
                pass
            else:
                emit_space(start)
            if "\n" in text[start:i]:
                at_line_start = True
            continue
        out_chars.append(ch)
        out_map.append(i)
        i += 1
    return "".join(out_chars), out_map


def locate_quote(document_text: str, quote: str,
                  doc_structural_cache: dict | None = None) -> dict:
    """
    Deterministic. Returns {"status": "exact"|"normalized"|"structural"|
    "unverified", "line": int|None, "occurrences": int}. "line" is
    1-indexed, first match. Never trusts anything the model said about
    location -- only the quote string itself, searched against the actual
    source. `doc_structural_cache` (optional, a dict this function may
    populate) avoids recomputing the structural strip of the same document
    for every one of its quotes.
    """
    if not isinstance(quote, str) or not quote.strip():
        return {"status": "unverified", "line": None, "occurrences": 0}

    idx = document_text.find(quote)
    if idx != -1:
        line = document_text.count("\n", 0, idx) + 1
        occurrences = document_text.count(quote)
        return {"status": "exact", "line": line, "occurrences": occurrences}

    # Tier 2: whitespace-only normalization.
    norm_doc = _normalize_ws(document_text)
    norm_quote = _normalize_ws(quote)
    if norm_quote:
        norm_idx = norm_doc.find(norm_quote)
        if norm_idx != -1:
            orig_pos = 0
            norm_pos = 0
            prev_ws = False
            for ch in document_text:
                if norm_pos >= norm_idx:
                    break
                if ch.isspace():
                    if not prev_ws:
                        norm_pos += 1
                    prev_ws = True
                else:
                    norm_pos += 1
                    prev_ws = False
                orig_pos += 1
            line = document_text.count("\n", 0, orig_pos) + 1
            occurrences = norm_doc.count(norm_quote)
            return {"status": "normalized", "line": line, "occurrences": occurrences}

    # Tier 3: structural (markdown-decoration-aware) normalization.
    if doc_structural_cache is not None and "stripped" in doc_structural_cache:
        struct_doc, struct_map = doc_structural_cache["stripped"], doc_structural_cache["map"]
    else:
        struct_doc, struct_map = _structural_strip_with_map(document_text)
        if doc_structural_cache is not None:
            doc_structural_cache["stripped"] = struct_doc
            doc_structural_cache["map"] = struct_map

    struct_quote, _ = _structural_strip_with_map(quote)
    struct_quote = _normalize_ws(struct_quote)
    if struct_quote:
        struct_idx = struct_doc.find(struct_quote)
        if struct_idx != -1:
            orig_offset = struct_map[struct_idx] if struct_idx < len(struct_map) else len(document_text) - 1
            line = document_text.count("\n", 0, orig_offset) + 1
            occurrences = struct_doc.count(struct_quote)
            return {"status": "structural", "line": line, "occurrences": occurrences}

    return {"status": "unverified", "line": None, "occurrences": 0}


def verify_record_quotes(record: dict, document_text: str) -> dict:
    """Walks every claim item in every field, verifies its quote against
    document_text, and returns a summary + per-item detail. Mutates nothing
    in `record` -- callers attach the result under a separate key."""
    total = 0
    exact = 0
    normalized = 0
    structural = 0
    unverified = 0
    unverified_detail = []
    doc_structural_cache: dict = {}

    for field in ALL_CLAIM_FIELDS:
        items = record.get(field) or []
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            quote = item.get("quote")
            total += 1
            result = locate_quote(document_text, quote, doc_structural_cache)
            item["line"] = result["line"]
            item["_verification"] = result["status"]
            if result["status"] == "exact":
                exact += 1
            elif result["status"] == "normalized":
                normalized += 1
            elif result["status"] == "structural":
                structural += 1
            else:
                unverified += 1
                unverified_detail.append({
                    "field": field, "index": i,
                    "quote": quote if isinstance(quote, str) else repr(quote),
                })

    return {
        "total_quotes": total,
        "verified_exact": exact,
        "verified_normalized": normalized,
        "verified_structural": structural,
        "unverified": unverified,
        "unverified_detail": unverified_detail,
    }


# --- deterministic dedup (2026-09-21, no model involvement) ---------------
#
# Definition: two items within the SAME field of the SAME record are
# duplicates if their `quote` strings are identical after _normalize_ws()
# -- the exact whitespace-collapse transform already used, and tested, for
# the "normalized" verification tier above. Comparison is scoped per
# (record, field); quotes are never compared across fields or across
# documents.
#
# Why this transform and not a looser one: _normalize_ws() only collapses
# whitespace runs and trims. It cannot merge two different passages into
# the same string -- every non-whitespace character must already match,
# character for character, for two quotes to compare equal under it. That
# is what makes "identical after this transform" a safe, conservative
# definition: a false-positive removal (collapsing two genuinely distinct
# claims) is impossible unless the two quotes were already the same text
# modulo line-wrap whitespace. The "structural" tier (also strips **,
# backticks, |, heading/list markers) was deliberately NOT used here even
# though it's available and tested -- it does more transformation than the
# safety property requires, and every duplicate actually observed in the
# fourth pilot's artifacts was already identical under plain whitespace
# normalization, so the looser tier buys no additional recall at the cost
# of a weaker safety argument. If a future run produced duplicates that
# differed only in markdown decoration, they would NOT be caught here --
# that is the intended, conservative failure direction (miss a duplicate
# rather than risk removing a distinct item).
#
# First occurrence is kept; order is otherwise preserved. Nothing is ever
# removed from the raw record -- `record[field]` is untouched by this pass.
# Results are attached under new keys so the raw extraction stays fully
# intact and auditable alongside the deduplicated view.

def _dedup_key(item: dict) -> str | None:
    quote = item.get("quote") if isinstance(item, dict) else None
    if not isinstance(quote, str) or not quote.strip():
        return None
    return _normalize_ws(quote)


def dedup_field(items: list) -> tuple[list, list]:
    """
    Returns (kept, removed). `kept` preserves original order, first
    occurrence of each normalized quote wins. Items whose quote isn't a
    non-empty string (malformed model output) are never treated as
    duplicates of anything and are always kept.
    """
    if not isinstance(items, list):
        return items, []
    seen: set[str] = set()
    kept: list = []
    removed: list = []
    for item in items:
        key = _dedup_key(item) if isinstance(item, dict) else None
        if key is None:
            kept.append(item)
            continue
        if key in seen:
            removed.append(item)
        else:
            seen.add(key)
            kept.append(item)
    return kept, removed


def dedup_record(record: dict) -> dict:
    """
    Mutates nothing in `record`'s existing top-level claim fields (the raw
    extraction, already annotated by verify_record_quotes with line/
    _verification, stays exactly as extracted). Adds three new keys:
      record["deduped"][field]              -> deduplicated item list
      record["padding_removed"][field]      -> int, duplicates removed
      record["padding_removed_items"][field]-> the removed item dicts
    A padding_removed count > 0 means the document had fewer genuinely
    distinct items of that type than its cap -- information the cap itself
    was obscuring, not discarded here.
    """
    deduped = {}
    padding_removed = {}
    padding_removed_items = {}
    for field in ALL_CLAIM_FIELDS:
        kept, removed = dedup_field(record.get(field) or [])
        deduped[field] = kept
        padding_removed[field] = len(removed)
        padding_removed_items[field] = removed
    record["deduped"] = deduped
    record["padding_removed"] = padding_removed
    record["padding_removed_items"] = padding_removed_items
    return record


# --- schema validation (structure only, not truth) ------------------------

def validate_schema(llm_record: dict) -> list[str]:
    problems = []
    caps = {
        "question_addressed": MAX_QUESTION_ITEMS,
        **{f: MAX_LIST_ITEMS for f in LIST_FIELDS if f != "contradicts_or_corrects"},
        "contradicts_or_corrects": MAX_CONTRADICTION_ITEMS,
    }
    for field, cap in caps.items():
        val = llm_record.get(field)
        if not isinstance(val, list):
            problems.append(f"{field} is not a list: {type(val)}")
            continue
        if len(val) > cap:
            problems.append(f"{field} has {len(val)} items, exceeds cap {cap}")
        for i, item in enumerate(val):
            if not isinstance(item, dict) or "claim" not in item or "quote" not in item:
                problems.append(f"{field}[{i}] malformed: {item!r}")
            elif not isinstance(item.get("claim"), str) or not isinstance(item.get("quote"), str):
                problems.append(f"{field}[{i}] claim/quote not strings")
    return problems


# --- ollama call -----------------------------------------------------------

def call_ollama(path_rel: str, text: str, logger: logging.Logger,
                 line_count: int) -> tuple[dict | None, dict]:
    prompt = EXTRACTION_PROMPT.format(
        max_q=MAX_QUESTION_ITEMS, max_list=MAX_LIST_ITEMS,
        max_contra=MAX_CONTRADICTION_ITEMS, path=path_rel, text=text,
    )
    est_tokens = estimate_prompt_tokens(prompt)
    over_safety_margin = est_tokens > OLLAMA_NUM_CTX * NUM_CTX_SAFETY_FRACTION
    call_timeout = timeout_for_lines(line_count)

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": GENERATION_SCHEMA,
        "options": {"temperature": 0, "num_ctx": OLLAMA_NUM_CTX},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )

    t0 = time.monotonic()
    meta = {
        "path": path_rel, "num_ctx": OLLAMA_NUM_CTX, "prompt_chars": len(prompt),
        "est_prompt_tokens": est_tokens, "over_safety_margin": over_safety_margin,
        "call_timeout_assigned": call_timeout,
    }
    if over_safety_margin:
        logger.warning(f"[{path_rel}] estimated prompt tokens ({est_tokens}) exceeds "
                        f"{NUM_CTX_SAFETY_FRACTION:.0%} of num_ctx ({OLLAMA_NUM_CTX}) -- "
                        f"sending anyway; flagged in telemetry.")
    try:
        with urllib.request.urlopen(req, timeout=call_timeout) as resp:
            result = json.loads(resp.read().decode())
            raw_text = result.get("response", "").strip()
        meta["call_seconds"] = time.monotonic() - t0
        meta["eval_count"] = result.get("eval_count")
        meta["prompt_eval_count"] = result.get("prompt_eval_count")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        meta["call_seconds"] = time.monotonic() - t0
        meta["error"] = f"request_failed: {e}"
        logger.error(f"[{path_rel}] Ollama request failed: {e}")
        return None, meta

    # Under format-constrained decoding this should always be a no-op (a
    # fence is not valid JSON and the constraint makes it unreachable) --
    # kept as cheap, harmless defensive verification rather than removed on
    # the assumption that it can never fire.
    cleaned = strip_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("expected a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        meta["error"] = f"parse_failed: {e}"
        meta["raw_response"] = raw_text[:4000]
        logger.error(f"[{path_rel}] Failed to parse response as JSON object: {e}")
        return None, meta

    return parsed, meta


# --- discovery (RECURSES into archive/, unlike corpus_reader_index.py) ----

def discover_paths() -> list[str]:
    return sorted(p.relative_to(REPO_ROOT).as_posix()
                  for p in DECISIONS_DIR.rglob("*.md"))


# --- checkpointing (path-based keyset cursor, same shape/rationale as
# corpus_reader_index.py -- see that script for the 2026-09-13 incident this
# guards against) --------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_seen_path": None, "processed": 0, "failed": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def already_indexed_paths(index_file: Path) -> set[str]:
    if not index_file.exists():
        return set()
    seen = set()
    with open(index_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line)["path"])
            except (json.JSONDecodeError, KeyError):
                continue
    return seen


def setup_logging(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("corpus_content_extractor")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, mode="a")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)
    return logger


def write_telemetry(telemetry_file: Path, record: dict) -> None:
    telemetry_file.parent.mkdir(parents=True, exist_ok=True)
    with open(telemetry_file, "a") as f:
        f.write(json.dumps(record) + "\n")


def process_one(path_rel: str, logger: logging.Logger) -> tuple[dict | None, dict, dict | None]:
    """Returns (record_or_None, call_meta, failure_detail_or_None). Never raises."""
    abs_path = REPO_ROOT / path_rel
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return None, {"path": path_rel, "call_seconds": 0}, {"path": path_rel, "error": f"read_failed: {e}"}

    line_count = text.count("\n") + 1
    llm_record, call_meta = call_ollama(path_rel, text, logger, line_count)
    if llm_record is None:
        return None, call_meta, {
            "path": path_rel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": call_meta.get("error"),
            "raw_response": call_meta.get("raw_response"),
        }

    problems = validate_schema(llm_record)
    record = {
        "path": path_rel,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "line_count": line_count,
        "question_addressed": llm_record.get("question_addressed", []),
        "findings": llm_record.get("findings", []),
        "explicitly_open": llm_record.get("explicitly_open", []),
        "proposed_not_done": llm_record.get("proposed_not_done", []),
        "decisions_recorded": llm_record.get("decisions_recorded", []),
        "failures_and_causes": llm_record.get("failures_and_causes", []),
        "contradicts_or_corrects": llm_record.get("contradicts_or_corrects", []),
        "schema_valid": len(problems) == 0,
        "schema_problems": problems,
        "over_safety_margin": call_meta.get("over_safety_margin", False),
        "call_timeout_assigned": call_meta.get("call_timeout_assigned"),
    }
    record["quote_verification"] = verify_record_quotes(record, text)
    record = dedup_record(record)

    return record, call_meta, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract content claims from brain/decisions/*.md, quote-anchored.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_BETWEEN_CALLS)
    parser.add_argument("--paths-file", type=str, default=None,
                         help="Newline-delimited list of repo-relative paths to process, "
                              "in that order, ignoring the normal cursor/discovery. Pilot mode.")
    parser.add_argument("--out", type=str, default=None,
                         help="Override output index path (pilot mode uses a separate file).")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--failures-file", type=str, default=None)
    parser.add_argument("--telemetry-file", type=str, default=None)
    parser.add_argument("--log-file", type=str, default=None)
    args = parser.parse_args()

    index_file = Path(args.out) if args.out else INDEX_FILE
    state_file = Path(args.state_file) if args.state_file else STATE_FILE
    failures_file = Path(args.failures_file) if args.failures_file else FAILURES_FILE
    telemetry_file = Path(args.telemetry_file) if args.telemetry_file else TELEMETRY_FILE
    log_file = Path(args.log_file) if args.log_file else LOG_FILE

    logger = setup_logging(log_file)
    proc = psutil.Process(os.getpid())
    run_start = time.monotonic()
    run_start_iso = datetime.now(timezone.utc).isoformat()
    rss_start_mb = proc.memory_info().rss / 1e6
    rss_peak_mb = rss_start_mb
    cpu_start = proc.cpu_times()

    logger.info(f"=== corpus_content_extractor starting === rss_start_mb={rss_start_mb:.1f} "
                f"timeout=length-scaled(k={TIMEOUT_SECONDS_PER_LINE}*lines*{TIMEOUT_SAFETY_MULTIPLIER}, "
                f"floor={MIN_TIMEOUT_SECONDS}s, ceiling={MAX_TIMEOUT_SECONDS}s) out={index_file}")

    if args.paths_file:
        pending = [line.strip() for line in Path(args.paths_file).read_text().splitlines() if line.strip()]
        logger.info(f"pilot mode: {len(pending)} explicit paths from {args.paths_file}")
    else:
        state = load_state()
        done_paths = already_indexed_paths(index_file)
        all_paths = discover_paths()
        cursor = state["last_seen_path"]
        pending = [p for p in all_paths if (cursor is None or p > cursor) and p not in done_paths]
        logger.info(f"resuming: last_seen_path={state['last_seen_path']!r} "
                    f"already_indexed={len(done_paths)} discovered_total={len(all_paths)} "
                    f"pending={len(pending)}")

    run_processed = 0
    run_failed = 0
    consecutive_failures = 0
    call_durations = []

    for path_rel in pending:
        if args.limit is not None and run_processed + run_failed >= args.limit:
            logger.info(f"Reached --limit {args.limit} for this run, stopping.")
            break
        if time.monotonic() - run_start > MAX_RUN_WALL_SECONDS:
            logger.error(f"KILL CONDITION: run wall time exceeded {MAX_RUN_WALL_SECONDS}s. Aborting.")
            break
        current_rss_mb = proc.memory_info().rss / 1e6
        rss_peak_mb = max(rss_peak_mb, current_rss_mb)
        if current_rss_mb > MAX_OWN_RSS_MB:
            logger.error(f"KILL CONDITION: own RSS {current_rss_mb:.1f}MB exceeded ceiling {MAX_OWN_RSS_MB}MB. Aborting.")
            break
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.error(f"KILL CONDITION: {consecutive_failures} consecutive failures. Aborting.")
            break

        if maintenance_in_progress():
            logger.info(f"daily_maintenance in progress -- pausing before [{path_rel}], "
                        f"polling every {MAINTENANCE_POLL_SECONDS}s")
            waited = 0
            while maintenance_in_progress():
                time.sleep(MAINTENANCE_POLL_SECONDS)
                waited += MAINTENANCE_POLL_SECONDS
                if waited % 600 == 0:
                    logger.info(f"still waiting on daily_maintenance ({waited}s so far)")
            logger.info(f"daily_maintenance cleared after {waited}s -- resuming with [{path_rel}]")

        record, call_meta, failure_detail = process_one(path_rel, logger)
        call_durations.append(call_meta.get("call_seconds", 0))

        if record is None:
            failures_file.parent.mkdir(parents=True, exist_ok=True)
            with open(failures_file, "a") as f:
                f.write(json.dumps(failure_detail) + "\n")
            run_failed += 1
            consecutive_failures += 1
            if not args.paths_file:
                state["last_seen_path"] = path_rel
                state["failed"] += 1
                save_state(state)
            write_telemetry(telemetry_file, {**call_meta, "outcome": "failed",
                                              "timestamp": datetime.now(timezone.utc).isoformat()})
            logger.warning(f"[{path_rel}] extraction failed, flagged, moving on "
                            f"({call_meta.get('call_seconds', 0):.1f}s)")
            time.sleep(args.sleep)
            continue

        index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(index_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        run_processed += 1
        consecutive_failures = 0
        if not args.paths_file:
            state["last_seen_path"] = path_rel
            state["processed"] += 1
            save_state(state)
        qv = record["quote_verification"]
        write_telemetry(telemetry_file, {
            **call_meta, "outcome": "ok", "schema_valid": record["schema_valid"],
            "quote_verification": qv,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[{path_rel}] extracted in {call_meta.get('call_seconds', 0):.1f}s "
                    f"valid={record['schema_valid']} quotes={qv['total_quotes']} "
                    f"exact={qv['verified_exact']} normalized={qv['verified_normalized']} "
                    f"structural={qv['verified_structural']} unverified={qv['unverified']}")
        time.sleep(args.sleep)

    cpu_end = proc.cpu_times()
    cpu_seconds = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
    rss_end_mb = proc.memory_info().rss / 1e6
    wall_seconds = time.monotonic() - run_start

    summary = {
        "run_start": run_start_iso, "run_end": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": wall_seconds, "cpu_seconds_self": cpu_seconds,
        "rss_start_mb": rss_start_mb, "rss_peak_mb": rss_peak_mb, "rss_end_mb": rss_end_mb,
        "documents_processed": run_processed, "documents_failed": run_failed,
        "call_count": len(call_durations),
        "call_seconds_min": min(call_durations) if call_durations else None,
        "call_seconds_max": max(call_durations) if call_durations else None,
        "call_seconds_mean": (sum(call_durations) / len(call_durations)) if call_durations else None,
    }
    write_telemetry(telemetry_file, {"outcome": "run_summary", **summary})
    logger.info(f"=== corpus_content_extractor finished === {json.dumps(summary)}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
