#!/usr/bin/env python3
"""
context_compressor.py — Pre-pass compression of brain files for local Ollama agents.

Reads brain/{signals,feedback,findings}.json and writes stripped versions to
/tmp/swarm-context/ so Tier 2 / 2.5 agents start with minimal context overhead.

Run: python3 orchestrator/context_compressor.py
No arguments. Compresses all three files. Exits 0 on success, 1 on any error.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("/home/parison/trading-swarm")
OUT_DIR = Path("/tmp/swarm-context")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compress_signals() -> tuple[bool, str]:
    src = BASE_DIR / "brain/signals.json"
    dst = OUT_DIR / "signals_compressed.json"
    try:
        original_bytes = src.stat().st_size
        with open(src) as f:
            data = json.load(f)

        signals = data.get("signals", [])
        original_count = len(signals)
        active = [s for s in signals if s.get("status") in ("active", "pending")]
        active_count = len(active)

        if active_count == 0:
            out = {
                "_compressed": True,
                "_active_count": 0,
                "_note": "No active signals",
            }
        else:
            compressed = []
            for s in active:
                payload = s.get("payload", {})
                entry: dict = {
                    "type": s.get("type"),
                    "confidence": s.get("confidence"),
                    "status": s.get("status"),
                    "timestamp": s.get("timestamp"),
                    "upgrade_status": s.get("upgrade_status"),
                }
                for field in ("market_id", "market_title", "direction", "upgrade_condition"):
                    if field in payload:
                        entry[f"payload.{field}"] = payload[field]
                reasoning = payload.get("reasoning")
                if reasoning:
                    entry["payload.reasoning"] = reasoning[:200]
                if "category_flag" in s:
                    entry["category_flag"] = s["category_flag"]
                compressed.append(entry)

            out = {
                "_compressed": True,
                "_original_count": original_count,
                "_active_count": active_count,
                "_generated_at": _iso_now(),
                "signals": compressed,
            }

        with open(dst, "w") as f:
            json.dump(out, f, indent=2)

        compressed_bytes = dst.stat().st_size
        reduction = (1 - compressed_bytes / original_bytes) * 100
        return True, f"signals.json: {original_bytes:,} bytes → {compressed_bytes:,} bytes ({reduction:.1f}% reduction)"
    except Exception as e:
        return False, f"signals.json: ERROR — {e}"


def compress_feedback() -> tuple[bool, str]:
    src = BASE_DIR / "brain/feedback.json"
    dst = OUT_DIR / "feedback_compressed.json"
    try:
        original_bytes = src.stat().st_size
        with open(src) as f:
            data = json.load(f)

        scout_cycles_count = len(data.get("scout_cycles", []))

        def _strip_approved(entry: dict) -> dict:
            result: dict = {}
            # Map spec field names → candidate keys in the actual entry
            for target, fallbacks in [
                ("id",                   ["id", "task_id"]),
                ("finding_type",         ["finding_type"]),
                ("confidence",           ["confidence"]),
                ("summary",              ["summary", "description"]),
                ("actionable",           ["actionable"]),
                ("action_recommendation",["action_recommendation", "action_taken"]),
            ]:
                for key in fallbacks:
                    val = entry.get(key)
                    if val is not None:
                        if isinstance(val, str) and target in ("summary", "action_recommendation"):
                            result[target] = val[:150]
                        else:
                            result[target] = val
                        break
            return result

        out = {
            "_compressed": True,
            "_scout_cycles_dropped": scout_cycles_count,
            "_generated_at": _iso_now(),
            "rejected": data.get("rejected", []),
            "approved": [_strip_approved(e) for e in data.get("approved", [])],
            "data_integrity_gates": data.get("data_integrity_gates", []),
        }

        with open(dst, "w") as f:
            json.dump(out, f, indent=2)

        compressed_bytes = dst.stat().st_size
        reduction = (1 - compressed_bytes / original_bytes) * 100
        return True, f"feedback.json: {original_bytes:,} bytes → {compressed_bytes:,} bytes ({reduction:.1f}% reduction)"
    except Exception as e:
        return False, f"feedback.json: ERROR — {e}"


def compress_findings() -> tuple[bool, str]:
    src = BASE_DIR / "brain/findings.json"
    dst = OUT_DIR / "findings_compressed.json"
    try:
        original_bytes = src.stat().st_size
        with open(src) as f:
            data = json.load(f)

        findings = data.get("findings", [])
        total_count = len(findings)
        valid = [
            f for f in findings
            if f.get("confidence") == "HIGH" and not f.get("invalidated_at")
        ]
        valid_count = len(valid)

        def _strip_finding(f: dict) -> dict:
            result = {
                k: f[k]
                for k in ("id", "finding_type", "confidence", "summary", "actionable")
                if k in f
            }
            if "action_recommendation" in f:
                result["action_recommendation"] = f["action_recommendation"][:200]
            if "expires_at" in f:
                result["expires_at"] = f["expires_at"]
            return result

        out = {
            "_compressed": True,
            "_total_findings": total_count,
            "_valid_high_count": valid_count,
            "_generated_at": _iso_now(),
            "findings": [_strip_finding(f) for f in valid],
        }

        with open(dst, "w") as f:
            json.dump(out, f, indent=2)

        compressed_bytes = dst.stat().st_size
        reduction = (1 - compressed_bytes / original_bytes) * 100
        return True, f"findings.json: {original_bytes:,} bytes → {compressed_bytes:,} bytes ({reduction:.1f}% reduction)"
    except Exception as e:
        return False, f"findings.json: ERROR — {e}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = [
        compress_signals(),
        compress_feedback(),
        compress_findings(),
    ]

    all_ok = True
    for ok, msg in results:
        print(msg)
        if not ok:
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
