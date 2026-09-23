#!/usr/bin/env python3
"""
Read-only verification of brain/corpus_content_index.jsonl (2026-09-23).

Does NOT call the model, does NOT modify the index, the extractor, or any
source document. Imports the extractor's pure functions (locate_quote,
validate_schema, dedup_field) and RE-RUNS them over every record, so the
numbers here are recomputed, not read back from the stored fields -- stored
vs recomputed disagreement is itself reported.

Writes brain/corpus_content_verification_<date>.json (durable artifact for
decision-carrying numbers).
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_content_extractor as ex  # noqa: E402

REPO = ex.REPO_ROOT
SPLIT = "2026-09-22"  # indexed_at < this -> first invocation
KNOWN_FABRICATIONS = (
    "the exact timing of when the sweep will begin is not determined",
    "the final runtime estimate after all adjustments is not yet known",
)
TIERS = ("exact", "normalized", "structural", "unverified")


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def half_of(rec):
    return "first" if rec["indexed_at"] < SPLIT else "second"


def main():
    records = load_jsonl(ex.INDEX_FILE)
    telemetry = [t for t in load_jsonl(ex.TELEMETRY_FILE) if t.get("outcome") != "run_summary"]
    failures = load_jsonl(ex.FAILURES_FILE)

    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "n_records": len(records), "split_rule": f"indexed_at < {SPLIT} => first"}
    paths = [r["path"] for r in records]
    out["duplicate_paths_in_index"] = [p for p, c in Counter(paths).items() if c > 1]
    all_docs = ex.discover_paths()
    out["discovered_docs"] = len(all_docs)
    out["docs_without_record"] = sorted(set(all_docs) - set(paths))
    out["records_for_missing_docs"] = sorted(set(paths) - set(all_docs))

    per_doc = []
    stored_mismatch = []
    dedup_mismatch = []
    raw_missing = []
    modified_after = []
    fab_hits = []
    for r in records:
        text = (REPO / r["path"]).read_text(encoding="utf-8", errors="replace")
        mtime = datetime.fromtimestamp((REPO / r["path"]).stat().st_mtime, timezone.utc).isoformat()
        if mtime > r["indexed_at"]:
            modified_after.append(r["path"])
        problems = ex.validate_schema({f: r.get(f) for f in ex.ALL_CLAIM_FIELDS})
        cache = {}
        tiers = Counter()
        unv = []
        for f in ex.ALL_CLAIM_FIELDS:
            for i, it in enumerate(r.get(f) or []):
                res = ex.locate_quote(text, it.get("quote"), cache)
                tiers[res["status"]] += 1
                if it.get("_verification") != res["status"]:
                    stored_mismatch.append((r["path"], f, i, it.get("_verification"), res["status"]))
                if res["status"] == "unverified":
                    unv.append((f, i))
                blob = (it.get("claim", "") + " " + it.get("quote", "")).lower()
                for k in KNOWN_FABRICATIONS:
                    if k in blob:
                        fab_hits.append((r["path"], f, i, k))
        # dedup recompute
        removed_counts = {}
        for f in ex.ALL_CLAIM_FIELDS:
            kept, removed = ex.dedup_field(r.get(f) or [])
            removed_counts[f] = len(removed)
            if [k.get("quote") for k in kept] != [k.get("quote") for k in (r.get("deduped", {}).get(f) or [])]:
                dedup_mismatch.append((r["path"], f))
            if r.get("padding_removed", {}).get(f) != len(removed):
                dedup_mismatch.append((r["path"], f, "count"))
        # raw preserved: raw >= deduped and raw count == deduped + removed
        for f in ex.ALL_CLAIM_FIELDS:
            if len(r.get(f) or []) != len(r["deduped"][f]) + r["padding_removed"][f]:
                raw_missing.append((r["path"], f))
        per_doc.append({
            "path": r["path"], "half": half_of(r), "lines": r["line_count"],
            "schema_ok": (not problems) and r.get("schema_valid") is True,
            "tiers": dict(tiers), "total": sum(tiers.values()),
            "raw_counts": {f: len(r.get(f) or []) for f in ex.ALL_CLAIM_FIELDS},
            "dedup_counts": {f: len(r["deduped"][f]) for f in ex.ALL_CLAIM_FIELDS},
            "removed": removed_counts, "unverified": unv,
        })

    def agg(rows):
        n = len(rows)
        tot = sum(d["total"] for d in rows)
        t = Counter()
        for d in rows:
            t.update(d["tiers"])
        a = {"docs": n, "schema_pass": sum(d["schema_ok"] for d in rows),
             "total_quotes": tot,
             "tiers": {k: t[k] for k in TIERS},
             "tier_pct": {k: round(100 * t[k] / tot, 2) if tot else None for k in TIERS},
             "verified_pct": round(100 * (tot - t["unverified"]) / tot, 2) if tot else None,
             "mean_claims_raw_per_field": {}, "mean_claims_dedup_per_field": {},
             "mean_removed_per_doc": round(sum(sum(d["removed"].values()) for d in rows) / n, 3) if n else None,
             "removed_per_field": {}, "docs_with_padding": sum(1 for d in rows if sum(d["removed"].values()) > 0),
             "mean_lines": round(statistics.mean(d["lines"] for d in rows), 1) if n else None,
             "mean_quotes_per_doc": round(tot / n, 2) if n else None}
        for f in ex.ALL_CLAIM_FIELDS:
            a["mean_claims_raw_per_field"][f] = round(sum(d["raw_counts"][f] for d in rows) / n, 3)
            a["mean_claims_dedup_per_field"][f] = round(sum(d["dedup_counts"][f] for d in rows) / n, 3)
            a["removed_per_field"][f] = sum(d["removed"][f] for d in rows)
        # per-field unverified rate
        uf = Counter()
        tf = Counter()
        for d in rows:
            for f in ex.ALL_CLAIM_FIELDS:
                tf[f] += d["raw_counts"][f]
            for f, _ in d["unverified"]:
                uf[f] += 1
        a["unverified_rate_by_field"] = {f: (round(100 * uf[f] / tf[f], 2) if tf[f] else None) for f in ex.ALL_CLAIM_FIELDS}
        a["claims_by_field_total"] = dict(tf)
        return a

    out["all"] = agg(per_doc)
    out["first"] = agg([d for d in per_doc if d["half"] == "first"])
    out["second"] = agg([d for d in per_doc if d["half"] == "second"])
    out["stored_vs_recomputed_verification_mismatches"] = len(stored_mismatch)
    out["stored_vs_recomputed_examples"] = stored_mismatch[:10]
    out["dedup_mismatches"] = dedup_mismatch
    out["raw_not_preserved"] = raw_missing
    out["docs_modified_after_indexing"] = modified_after
    out["known_fabrication_hits"] = fab_hits
    out["padding_top10"] = sorted(
        [{"path": d["path"], "removed_total": sum(d["removed"].values()), "removed": d["removed"]} for d in per_doc],
        key=lambda x: -x["removed_total"])[:10]

    # telemetry
    by_path = {}
    for t in telemetry:
        by_path.setdefault(t["path"], []).append(t)
    secs = [t["call_seconds"] for t in telemetry if t.get("outcome") == "ok"]
    out["telemetry"] = {
        "rows": len(telemetry),
        "outcomes": dict(Counter(t.get("outcome") for t in telemetry)),
        "ok_call_seconds": {"n": len(secs), "min": round(min(secs), 1), "median": round(statistics.median(secs), 1),
                            "mean": round(statistics.mean(secs), 1), "p90": round(sorted(secs)[int(0.9 * len(secs))], 1),
                            "max": round(max(secs), 1)},
        "over_safety_margin_docs": [t["path"] for t in telemetry if t.get("over_safety_margin")],
        "ok_docs_within_5pct_of_timeout": [
            t["path"] for t in telemetry if t.get("outcome") == "ok" and t["call_seconds"] > 0.95 * t["call_timeout_assigned"]],
    }
    out["failures_file"] = [{"path": f["path"], "timestamp": f["timestamp"], "error": f["error"]} for f in failures]
    fpaths = Counter(f["path"] for f in failures)
    out["failed_twice"] = sorted(p for p, c in fpaths.items() if c >= 2 and p not in set(paths))
    out["failed_first_then_succeeded"] = sorted(p for p in fpaths if p in set(paths))

    # length ranking for fabrication review
    out["longest_docs"] = [(d["path"], d["lines"]) for d in sorted(per_doc, key=lambda d: -d["lines"])[:20]]
    out["per_doc"] = per_doc

    # ---- claim-level semantic-risk screens (heuristics, NOT proof of fabrication) ----
    import re as _re
    def _shingles(t, n=6):
        w = _re.findall(r"[a-z0-9']+", t.lower())
        return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
    PROMPT_SH = _shingles(ex.EXTRACTION_PROMPT)
    num_re = _re.compile(r"\d[\d,]*\.?\d*")
    def nums(t):
        return {n.rstrip(".,").replace(",", "") for n in num_re.findall(t or "") if len(n.rstrip(".,")) >= 2}
    TEMPLATES = {
        "has_not_yet_determined_full_implications": _re.compile(r"has not yet determined the full", _re.I),
        "what_was_not_determined_placeholder": _re.compile(r"^what was not determined", _re.I),
        "document_corrects_understanding_of": _re.compile(r"^the document corrects the understanding of", _re.I),
        "not_determined_or_unknown_shape": _re.compile(r"\b(is|are|was|were) (not|yet to be) (been )?(determined|specified|known|decided)|not yet (known|determined|specified|decided)", _re.I),
        "X_will_proposal_shape_next_session": _re.compile(r"^the next session will", _re.I),
    }
    sc = {"prompt_echo_quotes": [], "short_quotes_le15chars": Counter(), "short_quotes_verified_exact": 0,
          "claims_total": 0, "claim_num_not_in_quote": 0, "claim_num_not_in_doc": [],
          "claims_with_numbers": 0, "cross_field_dup_claims": 0, "cross_field_dup_by_field": Counter(),
          "templates": {k: Counter() for k in TEMPLATES}, "stitched_ellipsis_quotes": 0,
          "claim_eq_quote": 0, "same_quote_diff_claim_within_field": 0}
    for r in records:
        text = (REPO / r["path"]).read_text(encoding="utf-8", errors="replace")
        text_nums = nums(text)
        doc_sh = _shingles(text)
        seen_quote = {}
        for f in ex.ALL_CLAIM_FIELDS:
            local = {}
            for i, it in enumerate(r.get(f) or []):
                sc["claims_total"] += 1
                q = it.get("quote") or ""; c = it.get("claim") or ""
                qn = ex._normalize_ws(q).lower()
                qsh = _shingles(q)
                if qsh and (qsh & PROMPT_SH) and not (qsh & doc_sh):
                    sc["prompt_echo_quotes"].append((r["path"], f, i, it.get("_verification"), q[:120]))
                if len(q.strip()) <= 15:
                    sc["short_quotes_le15chars"][f] += 1
                    if it.get("_verification") == "exact":
                        sc["short_quotes_verified_exact"] += 1
                if "..." in q or "\u2026" in q:
                    sc["stitched_ellipsis_quotes"] += 1
                if ex._normalize_ws(c).lower() == qn:
                    sc["claim_eq_quote"] += 1
                cn = nums(c)
                if cn:
                    sc["claims_with_numbers"] += 1
                    miss = cn - nums(q)
                    if miss:
                        sc["claim_num_not_in_quote"] += 1
                    absent = cn - text_nums
                    if absent:
                        sc["claim_num_not_in_doc"].append((r["path"], f, i, sorted(absent)[:4], c[:110]))
                for tk, tp in TEMPLATES.items():
                    if tp.search(c):
                        sc["templates"][tk][f] += 1
                if qn:
                    if qn in local and local[qn] != c:
                        sc["same_quote_diff_claim_within_field"] += 1
                    local[qn] = c
                    if qn in seen_quote and seen_quote[qn] != f:
                        sc["cross_field_dup_claims"] += 1
                        sc["cross_field_dup_by_field"][f] += 1
                    seen_quote.setdefault(qn, f)
    out["screens"] = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in sc.items() if k not in ("templates",)}
    out["screens"]["templates"] = {k: dict(v) for k, v in sc["templates"].items()}
    out["screens"]["claim_num_not_in_doc_n"] = len(sc["claim_num_not_in_doc"])
    out["screens"]["prompt_echo_quotes_n"] = len(sc["prompt_echo_quotes"])

    dest = REPO / "brain" / f"corpus_content_verification_{datetime.now(timezone.utc):%Y%m%d}.json"
    dest.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", dest)


if __name__ == "__main__":
    main()
