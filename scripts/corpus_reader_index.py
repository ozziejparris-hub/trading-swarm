#!/usr/bin/env python3
"""
Corpus reader: build a structured, extractive index of brain/decisions/*.md.

Shape copied deliberately from first-repo's scripts/backfill_market_categories.py
(the one proven local-Ollama production consumer): one call per unit of work,
strict JSON-array-or-object contract, markdown-fence stripping, json.loads with
a hard-fail path (no retry-until-parses loop), explicit timeout, resumable via
a keyset (path-based, not OFFSET) cursor.

Differs from that script in one structural way: half the schema is extracted
by regex in this process, not by the model. Document type / self-stated verdict
/ numeric findings / supersedes-relationships need reading comprehension and go
through the LLM. Commit hashes, RQ/STR/LH identifiers, cited artifact paths,
and "what was not determined" sections are pattern-matchable and are extracted
deterministically instead -- see brain/decisions/2026-09-19-tier25-supervisory-
agent-scoping.md Part 4 ("some grunt work needs no LLM") and the 2026-05-14
fabrication precedent (local model invents verdicts when asked to judge; it is
used here only to report what a document *says*, never to judge it).

STATELESS PER DOCUMENT: each document's LLM call is independent of every other.
A parse failure or timeout on document N is recorded and the run moves on; nD's
extraction never depends on N-1's output.
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
INDEX_FILE = REPO_ROOT / "brain" / "corpus_reader_index.jsonl"
STATE_FILE = REPO_ROOT / "brain" / "corpus_reader_state.json"
FAILURES_FILE = REPO_ROOT / "brain" / "corpus_reader_failures.jsonl"
TELEMETRY_FILE = REPO_ROOT / "logs" / "corpus_reader_telemetry.jsonl"
LOG_FILE = REPO_ROOT / "logs" / "corpus_reader.log"

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3-coder:30b-a3b-q4_K_M"

# Fixed for the whole run, NOT sized per document. Piloting this script
# revealed that Ollama allocates the runner's KV cache once, at model load,
# sized to whatever num_ctx the first request specifies (confirmed via
# `journalctl -u ollama`: "load request={...KvSize:32768...}" followed by a
# ~13s "llama runner started" line). A later call with a *different* num_ctx
# forces an unload/reload of the entire 17GB+ runner, not just a bigger
# allocation for that call. Since brain/decisions/*.md is processed in
# filename (roughly chronological) order, document size does not correlate
# with position in that order -- a per-document tiered num_ctx would reload
# the runner on most size changes across 265 documents. One fixed value,
# sized to the corpus's largest document with headroom, is paid once.
#
# Sizing: largest known document is 216,157 chars (1,883 lines). At a
# conservative chars/3 estimate that is ~74,052 tokens; +2,000 for prompt
# scaffolding and generation budget. 131,072 leaves ~55K tokens of headroom
# over that estimate -- generous margin for tokenizer-estimate error without
# reaching the model's full 262,144 window (which would roughly double the
# KV-cache memory footprint for no corpus in this run that needs it).
OLLAMA_NUM_CTX = 131072

# A document whose prompt would use more than this fraction of OLLAMA_NUM_CTX
# (leaving room for the response) is flagged rather than silently sent --
# Ollama truncates an over-length prompt instead of erroring, which would
# produce a confident-looking but silently wrong extraction.
NUM_CTX_SAFETY_FRACTION = 0.85

# Per-call wall-clock ceiling. Justified empirically against this script's
# own pilot runs, not copied from the 120s title-batch precedent (these are
# whole documents requiring comprehension, not one-line classification): a
# 36-line document completed in 19.2s end-to-end; a full pilot run at this
# script's actual num_ctx tier against the corpus's ~90th-percentile-sized
# document (665 lines) and its largest (1,883 lines) are reported in the
# decision doc alongside the real run's measured distribution. Set well
# above the slowest piloted call, with headroom for a colder cache.
OLLAMA_TIMEOUT_SECONDS = 1800

DEFAULT_SLEEP_BETWEEN_CALLS = 1.0

# Kill conditions, enforced by this process between documents (not inside
# Ollama, which is a separate process this script does not own the memory
# of). A run that starts eating hours or gigabytes where the precedent
# takes seconds/megabytes is itself the signal -- see the tier2.5 scoping
# doc's Part 6 and the two runaway-process incidents on record for this box.
MAX_RUN_WALL_SECONDS = 6 * 3600          # abort the whole run past 6h
MAX_OWN_RSS_MB = 500                      # this Python process's own RSS
MAX_CONSECUTIVE_FAILURES = 5              # abort if N calls in a row fail/timeout

# Numeric findings extracted per document, capped to keep the schema and the
# spot-check tractable -- these are meant to be traceable pointers back into
# the source document, not an exhaustive re-statement of it.
MAX_NUMERIC_FINDINGS = 8

DOCUMENT_TYPES = (
    "pre-registration",
    "result",
    "diagnosis",
    "session-summary",
    "decision",
    "other",
)

# --- deterministic extraction (no LLM) -------------------------------------

FILENAME_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
# 7-char hex is the corpus's overwhelming convention for a short git sha
# (1,229 of 1,247 sampled backtick-hex tokens during schema design); 8+/64-char
# hex runs are excluded on purpose -- they are almost always something else in
# this corpus, most notably the metric_v2f_oos_result sha256 quoted at 8-64
# chars, which is not a commit reference and would be a false positive here.
COMMIT_REF_RE = re.compile(r"`([0-9a-f]{7})`|\bcommit\s+([0-9a-f]{7})\b")
IDENTIFIER_RE = re.compile(r"\b(RQ\d+(?:\.\d+)?|STR-\d+|LH-\d+)\b")
ARTIFACT_PATH_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.(?:py|json|md|sql|sh))`")
FIRST_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
WHAT_NOT_DETERMINED_RE = re.compile(
    r"^#{1,3}\s*what was not determined\s*$", re.IGNORECASE | re.MULTILINE
)


def extract_deterministic(text: str, path_rel: str, heatmap_cited: set[str]) -> dict:
    filename = Path(path_rel).name
    m = FILENAME_DATE_RE.match(filename)
    filename_date = m.group(1) if m else None

    commit_refs = sorted({a or b for a, b in COMMIT_REF_RE.findall(text)})
    identifiers = sorted(set(IDENTIFIER_RE.findall(text)))
    artifact_paths = sorted(set(ARTIFACT_PATH_RE.findall(text)))

    heading_m = FIRST_HEADING_RE.search(text)
    first_heading = heading_m.group(1).strip() if heading_m else None

    wnd_m = WHAT_NOT_DETERMINED_RE.search(text)
    what_not_determined_excerpt = None
    has_wnd_section = bool(wnd_m)
    if wnd_m:
        start = wnd_m.end()
        # capture up to the next heading of the same or higher level, or 2000
        # chars, whichever comes first -- bounds record size while staying
        # verbatim (no summarization).
        rest = text[start:]
        next_heading = re.search(r"^#{1,3}\s+\S", rest, re.MULTILINE)
        end = next_heading.start() if next_heading else len(rest)
        what_not_determined_excerpt = rest[:min(end, 2000)].strip()

    return {
        "filename_date": filename_date,
        "line_count": text.count("\n") + 1,
        "byte_size": len(text.encode("utf-8")),
        "first_heading": first_heading,
        "commit_refs": commit_refs,
        "rq_str_lh_ids": identifiers,
        "artifact_paths_cited": artifact_paths,
        "heatmap_flagged": path_rel in heatmap_cited,
        "has_what_was_not_determined_section": has_wnd_section,
        "what_not_determined_excerpt": what_not_determined_excerpt,
    }


def load_heatmap_cited() -> set[str]:
    """
    Filenames cited (by exact match) inside the five 2026-09-12 heatmap pass
    documents (.md and .json). This is a floor, not a ceiling: a pass that
    described a document without giving its exact filename won't be caught.
    Used only as a spot-check aid (flag which records to prioritise cross-
    checking against known-good prior reads), not as a claim of completeness.
    """
    cited = set()
    pattern = re.compile(r"\b\d{4}-\d{2}-\d{2}-[a-zA-Z0-9_-]+\.md\b")
    for f in DECISIONS_DIR.glob("2026-09-12-heatmap-pass*"):
        if f.suffix not in (".md", ".json"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cited.update(pattern.findall(text))
    return cited


# --- LLM extraction ----------------------------------------------------------

EXTRACTION_PROMPT = """\
You are extracting facts from a project decision document. Extract ONLY what \
the document explicitly states about itself. Do not judge whether it is \
correct, important, or reliable. Do not infer anything not written in the text.

Output ONLY a JSON object (no markdown fence, no prose before or after) with \
exactly these fields:

title: the document's own title, verbatim (usually the first heading line).
document_type: exactly one of {types}. Base this on how the document \
  frames its own purpose (e.g. explicit "Type:" labels, or the shape of the \
  content -- a pre-registration states hypotheses before running anything; a \
  result reports what happened; a diagnosis investigates a problem; a \
  session-summary recaps a work session; a decision records a choice made).
self_stated_verdict: a short literal quote (max ~40 words) from the document \
  stating its own outcome, verdict, or status about itself (e.g. "CONFIRMED", \
  "REFUTED", "NULL result", "STOPPED", a pass/fail line). null if the \
  document does not state one.
numeric_findings: an array of up to {max_findings} objects, each \
  {{"value": "<the number or quantity, as written>", "context": "<the \
  surrounding phrase or sentence fragment it appears in, max 25 words, \
  verbatim or near-verbatim from the text>"}}. Only the document's own \
  headline/decision-relevant numbers, not every digit in it.
supersedes: if the document explicitly states it supersedes, replaces, or \
  amends another document, a literal quote or the cited path/filename. \
  null if no such statement exists.
superseded_by: if the document explicitly states it was superseded, \
  replaced, or amended by another document, a literal quote or the cited \
  path/filename. null if no such statement exists.

If a field cannot be determined from the text, use null (or [] for \
numeric_findings). Do not guess.

DOCUMENT (path: {path}):
{text}

Respond with ONLY the JSON object.
"""


def estimate_prompt_tokens(text: str) -> int:
    # Conservative chars-per-token estimate (dense English prose/markdown/
    # code fences), plus fixed overhead for the prompt scaffolding.
    return len(text) // 3 + 500


def strip_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.startswith("```")).strip()
    return raw


def call_ollama(path_rel: str, text: str, logger: logging.Logger) -> tuple[dict | None, dict]:
    """Returns (parsed_json_or_None, call_meta). Never raises on a normal
    failure path -- timeouts and parse failures are reported, not thrown."""
    prompt = EXTRACTION_PROMPT.format(
        types=", ".join(DOCUMENT_TYPES),
        max_findings=MAX_NUMERIC_FINDINGS,
        path=path_rel,
        text=text,
    )
    est_tokens = estimate_prompt_tokens(prompt)
    over_safety_margin = est_tokens > OLLAMA_NUM_CTX * NUM_CTX_SAFETY_FRACTION

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": OLLAMA_NUM_CTX},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.monotonic()
    meta = {
        "path": path_rel,
        "num_ctx": OLLAMA_NUM_CTX,
        "prompt_chars": len(prompt),
        "est_prompt_tokens": est_tokens,
        "over_safety_margin": over_safety_margin,
    }
    if over_safety_margin:
        logger.warning(
            f"[{path_rel}] estimated prompt tokens ({est_tokens}) exceeds "
            f"{NUM_CTX_SAFETY_FRACTION:.0%} of num_ctx ({OLLAMA_NUM_CTX}) -- "
            f"Ollama may silently truncate. Sending anyway; flagged in telemetry."
        )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
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


def validate_schema(record: dict) -> list[str]:
    """Returns a list of validation problems; empty means the record is
    well-formed (says nothing about whether it is *true* -- that is Part 4's
    job, done by a human reading a sample, not by this function)."""
    problems = []
    if record.get("document_type") not in DOCUMENT_TYPES:
        problems.append(f"document_type not in allowed set: {record.get('document_type')!r}")
    nf = record.get("numeric_findings")
    if not isinstance(nf, list):
        problems.append("numeric_findings is not a list")
    else:
        for i, item in enumerate(nf):
            if not isinstance(item, dict) or "value" not in item or "context" not in item:
                problems.append(f"numeric_findings[{i}] malformed: {item!r}")
    for field in ("title", "self_stated_verdict", "supersedes", "superseded_by"):
        if field in record and record[field] is not None and not isinstance(record[field], str):
            problems.append(f"{field} is not a string or null: {type(record[field])}")
    return problems


# --- checkpointing (path-based keyset cursor) --------------------------------
#
# Deliberately NOT an OFFSET/position counter. The 2026-09-13 incident
# (scripts/backfill_market_categories.py) lost 67.8% of its backlog because
# an OFFSET advanced by rows *fetched* while the underlying WHERE-clause
# result set shrank as rows got classified -- a position stopped meaning the
# same row. That failure mode requires a *mutable, filtered* result set
# (rows leaving the set as they're processed). This corpus has no such
# mechanism: the file list under brain/decisions/ does not shrink as
# documents are indexed, so a plain path cursor cannot drift the way the
# OFFSET did. It is used anyway, on principle -- same shape as the proven
# fix (WHERE path > cursor ORDER BY path), for the same reason: immune to
# any future change in how documents are enumerated, not just the specific
# bug being avoided today.


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_seen_path": None, "processed": 0, "failed": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def already_indexed_paths() -> set[str]:
    """Paths already present in the index file, used to skip re-processing on
    resume without relying solely on the cursor (belt-and-braces: a record
    already on disk is never re-fetched even if the cursor were somehow
    stale)."""
    if not INDEX_FILE.exists():
        return set()
    seen = set()
    with open(INDEX_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                seen.add(rec["path"])
            except (json.JSONDecodeError, KeyError):
                continue
    return seen


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("corpus_reader")
    logger.setLevel(logging.DEBUG)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, mode="a")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)
    return logger


def write_telemetry(record: dict) -> None:
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index brain/decisions/*.md, extractively.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N documents this run")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_BETWEEN_CALLS)
    args = parser.parse_args()

    logger = setup_logging()
    proc = psutil.Process(os.getpid())
    run_start = time.monotonic()
    run_start_iso = datetime.now(timezone.utc).isoformat()
    rss_start_mb = proc.memory_info().rss / 1e6
    rss_peak_mb = rss_start_mb
    cpu_start = proc.cpu_times()

    logger.info(f"=== corpus_reader_index starting === rss_start_mb={rss_start_mb:.1f}")

    heatmap_cited = load_heatmap_cited()
    logger.info(f"heatmap-cited filenames found: {len(heatmap_cited)}")

    state = load_state()
    done_paths = already_indexed_paths()
    logger.info(f"resuming: last_seen_path={state['last_seen_path']!r} "
                f"already_indexed={len(done_paths)} processed_ctr={state['processed']} "
                f"failed_ctr={state['failed']}")

    all_paths = sorted(p.relative_to(REPO_ROOT).as_posix() for p in DECISIONS_DIR.glob("*.md"))
    cursor = state["last_seen_path"]
    pending = [p for p in all_paths if (cursor is None or p > cursor) and p not in done_paths]

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
            logger.error(f"KILL CONDITION: own RSS {current_rss_mb:.1f}MB exceeded "
                         f"ceiling {MAX_OWN_RSS_MB}MB. Aborting.")
            break

        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.error(f"KILL CONDITION: {consecutive_failures} consecutive failures. Aborting.")
            break

        abs_path = REPO_ROOT / path_rel
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.error(f"[{path_rel}] could not read file: {e}")
            run_failed += 1
            consecutive_failures += 1
            state["last_seen_path"] = path_rel
            state["failed"] += 1
            save_state(state)
            continue

        deterministic = extract_deterministic(text, path_rel, heatmap_cited)
        llm_record, call_meta = call_ollama(path_rel, text, logger)
        call_durations.append(call_meta.get("call_seconds", 0))

        if llm_record is None:
            with open(FAILURES_FILE, "a") as f:
                f.write(json.dumps({
                    "path": path_rel,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": call_meta.get("error"),
                    "raw_response": call_meta.get("raw_response"),
                }) + "\n")
            run_failed += 1
            consecutive_failures += 1
            state["last_seen_path"] = path_rel
            state["failed"] += 1
            save_state(state)
            write_telemetry({**call_meta, "outcome": "failed", "timestamp": datetime.now(timezone.utc).isoformat()})
            logger.warning(f"[{path_rel}] extraction failed, flagged, moving on "
                            f"({call_meta.get('call_seconds', 0):.1f}s)")
            time.sleep(args.sleep)
            continue

        problems = validate_schema(llm_record)
        record = {
            "path": path_rel,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            **deterministic,
            "title": llm_record.get("title"),
            "document_type": llm_record.get("document_type"),
            "self_stated_verdict": llm_record.get("self_stated_verdict"),
            "numeric_findings": llm_record.get("numeric_findings", []),
            "supersedes": llm_record.get("supersedes"),
            "superseded_by": llm_record.get("superseded_by"),
            "schema_valid": len(problems) == 0,
            "schema_problems": problems,
            "over_safety_margin": call_meta.get("over_safety_margin", False),
        }

        with open(INDEX_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

        run_processed += 1
        consecutive_failures = 0
        state["last_seen_path"] = path_rel
        state["processed"] += 1
        save_state(state)
        write_telemetry({**call_meta, "outcome": "ok", "schema_valid": record["schema_valid"],
                          "timestamp": datetime.now(timezone.utc).isoformat()})

        logger.info(f"[{path_rel}] indexed in {call_meta.get('call_seconds', 0):.1f}s "
                    f"type={record['document_type']} valid={record['schema_valid']}")

        time.sleep(args.sleep)

    cpu_end = proc.cpu_times()
    cpu_seconds = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
    rss_end_mb = proc.memory_info().rss / 1e6
    wall_seconds = time.monotonic() - run_start

    summary = {
        "run_start": run_start_iso,
        "run_end": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": wall_seconds,
        "cpu_seconds_self": cpu_seconds,
        "rss_start_mb": rss_start_mb,
        "rss_peak_mb": rss_peak_mb,
        "rss_end_mb": rss_end_mb,
        "documents_processed": run_processed,
        "documents_failed": run_failed,
        "call_count": len(call_durations),
        "call_seconds_min": min(call_durations) if call_durations else None,
        "call_seconds_max": max(call_durations) if call_durations else None,
        "call_seconds_mean": (sum(call_durations) / len(call_durations)) if call_durations else None,
    }
    write_telemetry({"outcome": "run_summary", **summary})
    logger.info(f"=== corpus_reader_index finished === {json.dumps(summary)}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
