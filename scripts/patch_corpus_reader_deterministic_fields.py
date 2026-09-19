#!/usr/bin/env python3
"""
Re-derive rq_str_lh_ids and artifact_paths_cited deterministically (regex
only, no model call), patch them onto the existing corpus_reader_index.jsonl
records, and write a NEW index file. Also builds minimal deterministic-only
records for the two brain/decisions/archive/ files the original script never
reached (its glob was non-recursive).

Correction made while building this: the two fields being replaced were
ALREADY regex-only in the original script (see corpus_reader_index.py
IDENTIFIER_RE / ARTIFACT_PATH_RE) -- there is no model in this path at all,
in the original script or this one. What the 2026-09-19 verification called
"fabrication" for these two fields was, on re-check against source with grep
(not eyeballing), not fabrication: a pure single-document regex .findall()
cannot invent a substring that is not literally in its input. The instances
named as fabricated (STR-004 in heatmap-pass5, backfill_market_dates.py and
daily_maintenance.py in the geo-backlog doc, scripts/evaluate_new_trader_
results.py in the background-backfill doc) are all present, verbatim, in
their respective source documents -- the original regex already matched
them correctly. That was a verification error (missed on manual read), not
an extraction defect, and is corrected in the companion decision doc rather
than silently carried forward.

The real, confirmed defect class is under-matching (recall), from two
regex gaps:
  1. IDENTIFIER_RE only matched RQ<digits> (e.g. RQ1.1, RQ3.2) and STR-<digits>
     / LH-<digits>. It had no pattern for RQ-<WORD>-<NNN> (e.g. RQ-CONTESTED-
     001, RQ-VPIN-001) -- this corpus's more common RQ- naming convention.
  2. ARTIFACT_PATH_RE only matched backtick-quoted `path.ext` tokens. A bare
     script name mentioned without backticks (2026-06-24-session-summary.md
     names ~15 scripts this way) was invisible to it.
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DIR = REPO_ROOT / "brain" / "decisions"
OLD_INDEX_FILE = REPO_ROOT / "brain" / "corpus_reader_index.jsonl"
NEW_INDEX_FILE = REPO_ROOT / "brain" / "corpus_reader_index_v2.jsonl"
CENSUS_FILE = REPO_ROOT / "brain" / "corpus_reader_index_v2_census.json"

# --- new patterns ------------------------------------------------------------

# Two identifier shapes: RQ-WORD(-NNN) and RQ<digits>(.digits), plus STR-/LH-.
# Applied over the raw text -- no fence/backtick stripping, deliberately (see
# decision doc: a commit hash inside a code fence was missed before by
# excluding fenced content; the same risk applies here, so fenced/backticked
# text is included).
# Three independent patterns, unioned rather than alternated in one findall().
# Alternation would make a compound id like "RQ-LH-001" (a real, distinct RQ
# identifier that embeds LH-001's own name) swallow the LH-001 substring so
# it never separately matches -- both "RQ-LH-001" and "LH-001" are genuine,
# independently-queryable identifiers for this corpus's convention, so both
# must be captured even though they overlap in the text.
# Trailing [a-z]? handles a real corpus convention: "RQ-EXT-001a/b/c" style
# sub-variant suffixes. Without it, a bare \b after \d+ fails to match when
# immediately followed by a lowercase letter (word-to-word, no boundary),
# forcing a backtrack that drops the digits entirely (RQ-EXT instead of
# RQ-EXT-001) -- found by this task's own spot-check, fixed here.
# (?:-[A-Z]+)* handles multi-segment names (RQ-GEO-ELO-001, RQ-POOL-QUALITY-001,
# RQ-CONTESTED-ARCHETYPE-001) -- a single [A-Z]+ segment stopped at the first
# internal hyphen and silently dropped everything after it (also found by
# this task's own spot-check, fixed here).
RQ_WORD_RE = re.compile(r"\bRQ-[A-Z]+(?:-[A-Z]+)*(?:-\d+[a-z]?)?\b")
RQ_NUM_RE = re.compile(r"\bRQ\d+(?:\.\d+)*\b")
STR_LH_RE = re.compile(r"\b(?:STR|LH)-\d+[a-z]?\b")

PATH_RE = re.compile(
    r"\b(?:scripts|monitoring|config|brain|orchestrator|data|logs|tests|analysis|docs)"
    r"/[\w./-]+\b"
)

BAREFILE_RE = re.compile(
    r"(?<![\w.])\.?[\w-]+\.(?:py|sh|json|jsonl|md|sql|csv|txt)\b"
)


def extract_identifiers(text: str) -> list[str]:
    ids = set(RQ_WORD_RE.findall(text))
    ids |= set(RQ_NUM_RE.findall(text))
    ids |= set(STR_LH_RE.findall(text))
    return sorted(ids)


def extract_artifact_paths(text: str, own_filename: str) -> list[str]:
    full_paths = set(PATH_RE.findall(text))
    bare_files = set(BAREFILE_RE.findall(text))

    # Strip trailing punctuation a word-boundary match can drag in (e.g. a
    # filename immediately followed by a period ending a sentence, or a
    # comma/parenthesis in prose). Conservative: only strip a single trailing
    # '.' when it is not part of the extension itself.
    def clean(p: str) -> str:
        if p.endswith(".") and not re.search(r"\.(py|sh|json|jsonl|md|sql|csv|txt)\.$", p):
            return p[:-1]
        return p

    full_paths = {clean(p) for p in full_paths}
    bare_files = {clean(p) for p in bare_files}

    # Exclude the document's own filename -- a self-reference is not a cited
    # artifact.
    bare_files.discard(own_filename)
    full_paths = {p for p in full_paths if Path(p).name != own_filename}

    # Dedupe bare-file / full-path overlap: if a bare filename is also the
    # basename of some captured full path, drop the bare form and keep only
    # the fuller one (e.g. drop "failure_age.py" if "monitoring/failure_age.py"
    # was also captured).
    full_basenames = {Path(p).name for p in full_paths}
    bare_files = {b for b in bare_files if b not in full_basenames}

    return sorted(full_paths | bare_files)


def load_docs() -> dict[str, str]:
    docs = {}
    for f in DECISIONS_DIR.rglob("*.md"):
        rel = f.relative_to(REPO_ROOT).as_posix()
        docs[rel] = f.read_text(encoding="utf-8", errors="replace")
    return docs


FILENAME_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
FIRST_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def build_archive_record(path_rel: str, text: str) -> dict:
    filename = Path(path_rel).name
    m = FILENAME_DATE_RE.match(filename)
    heading_m = FIRST_HEADING_RE.search(text)
    return {
        "path": path_rel,
        "indexed_at": None,
        "filename_date": m.group(1) if m else None,
        "line_count": text.count("\n") + 1,
        "byte_size": len(text.encode("utf-8")),
        "first_heading": heading_m.group(1).strip() if heading_m else None,
        "commit_refs": None,
        "rq_str_lh_ids": extract_identifiers(text),
        "artifact_paths_cited": extract_artifact_paths(text, filename),
        "heatmap_flagged": False,
        "has_what_was_not_determined_section": None,
        "what_not_determined_excerpt": None,
        "title": None,
        "document_type": None,
        "self_stated_verdict": None,
        "numeric_findings": None,
        "supersedes": None,
        "superseded_by": None,
        "schema_valid": None,
        "schema_problems": ["llm_fields_pending: never indexed (archive/ not reached "
                             "by the original script's non-recursive glob); "
                             "rq_str_lh_ids/artifact_paths_cited/mechanical fields "
                             "are populated deterministically here, everything else "
                             "requires the LLM pass, not run in this task"],
        "over_safety_margin": None,
        "llm_fields_pending": True,
    }


def main():
    docs = load_docs()

    old_records = [json.loads(l) for l in open(OLD_INDEX_FILE)]

    new_records = []
    diffs = []  # per-doc diff report for the census

    for rec in old_records:
        path_rel = rec["path"]
        text = docs.get(path_rel)
        if text is None:
            raise SystemExit(f"missing source for indexed path: {path_rel}")
        own_filename = Path(path_rel).name

        new_ids = extract_identifiers(text)
        new_paths = extract_artifact_paths(text, own_filename)

        old_ids = set(rec.get("rq_str_lh_ids") or [])
        old_paths = set(rec.get("artifact_paths_cited") or [])

        missed_ids = sorted(set(new_ids) - old_ids)
        missed_paths = sorted(set(new_paths) - old_paths)
        # "old had it, new regex dropped it" -- a real regression to flag.
        regressed_ids = sorted(old_ids - set(new_ids))
        regressed_paths = sorted(old_paths - set(new_paths))

        diffs.append({
            "path": path_rel,
            "missed_ids_now_caught": missed_ids,
            "missed_paths_now_caught": missed_paths,
            "regressed_ids_lost": regressed_ids,
            "regressed_paths_lost": regressed_paths,
        })

        patched = dict(rec)
        patched["rq_str_lh_ids"] = new_ids
        patched["artifact_paths_cited"] = new_paths
        new_records.append(patched)

    # archive/ -- new minimal records, deterministic fields only
    archive_records = []
    for path_rel, text in sorted(docs.items()):
        if "/archive/" not in path_rel:
            continue
        archive_records.append(build_archive_record(path_rel, text))

    with open(NEW_INDEX_FILE, "w") as f:
        for r in new_records + archive_records:
            f.write(json.dumps(r) + "\n")

    with open(CENSUS_FILE, "w") as f:
        json.dump(diffs, f, indent=2)

    print(f"patched {len(new_records)} existing records")
    print(f"added {len(archive_records)} archive records: {[r['path'] for r in archive_records]}")

    docs_with_missed_ids = sum(1 for d in diffs if d["missed_ids_now_caught"])
    total_missed_ids = sum(len(d["missed_ids_now_caught"]) for d in diffs)
    docs_with_missed_paths = sum(1 for d in diffs if d["missed_paths_now_caught"])
    total_missed_paths = sum(len(d["missed_paths_now_caught"]) for d in diffs)
    docs_regressed_ids = sum(1 for d in diffs if d["regressed_ids_lost"])
    docs_regressed_paths = sum(1 for d in diffs if d["regressed_paths_lost"])

    print(f"docs with >=1 previously-missed identifier now caught: {docs_with_missed_ids}, total ids added: {total_missed_ids}")
    print(f"docs with >=1 previously-missed path now caught: {docs_with_missed_paths}, total paths added: {total_missed_paths}")
    print(f"docs where new regex LOST an id the old one had: {docs_regressed_ids}")
    print(f"docs where new regex LOST a path the old one had: {docs_regressed_paths}")


if __name__ == "__main__":
    main()
