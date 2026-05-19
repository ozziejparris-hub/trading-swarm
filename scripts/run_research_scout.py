#!/usr/bin/env python3
"""
Research scout — fetches real findings via Anthropic API web_search tool.
Replaces the local Qwen3-Coder agent that fabricated sources from training memory.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SWARM = Path(__file__).parent.parent
PENDING_REVIEW = SWARM / "brain/research-scout/pending-review"
_NOW = datetime.now(timezone.utc)
TODAY = _NOW.strftime("%Y-%m-%d")
HOUR = _NOW.strftime("%H")


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    result = subprocess.run(
        ["bash", "-c", "source ~/.env_trading && echo $ANTHROPIC_API_KEY"],
        capture_output=True, text=True,
    )
    key = result.stdout.strip()
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or ~/.env_trading", file=sys.stderr)
        sys.exit(1)
    return key


def read_context() -> str:
    parts = []

    priorities_path = SWARM / "brain/priorities.md"
    if priorities_path.exists():
        parts.append(f"=== brain/priorities.md ===\n{priorities_path.read_text()[:3000]}")

    directions_path = SWARM / "brain/strategy-notes/research-directions.md"
    if directions_path.exists():
        lines = directions_path.read_text().splitlines()[:100]
        parts.append(
            "=== brain/strategy-notes/research-directions.md (first 100 lines) ===\n"
            + "\n".join(lines)
        )

    ref_lib = SWARM / "brain/reference-library"
    if ref_lib.is_dir():
        names = sorted(p.name for p in ref_lib.iterdir() if p.is_file())
        parts.append("=== brain/reference-library/ filenames ===\n" + "\n".join(names))

    return "\n\n".join(parts)


def call_api(api_key: str) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    system = (
        "You are a research scout for a Polymarket trading intelligence system. "
        "Your job is to find REAL, VERIFIABLE information from actual web sources. "
        "Only report things you actually read from web search results. "
        "Never invent papers, commits, or announcements from memory."
    )

    user = (
        "Search for and report on ONLY these specific topics today:\n"
        "1. Any new Polymarket announcements or API changes "
        '(search: "Polymarket" site:polymarket.com OR site:twitter.com/Polymarket)\n'
        "2. Any new arXiv papers on prediction market efficiency or informed trading "
        "(search: arXiv prediction markets informed trading 2026)\n"
        "3. DeepSeek V4 release status (search: DeepSeek V4 release 2026)\n\n"
        "For each finding, output a JSON object with these exact fields:\n"
        '{"title": str, "source_url": str, "domain": str, "relevance": "HIGH|MEDIUM|LOW", '
        '"summary": str (2-3 sentences max), "action": str, "verified": true}\n\n'
        "Only include findings where verified=true (you actually read the source).\n"
        "Output findings as a JSON array. Nothing else."
    )

    messages = [{"role": "user", "content": user}]
    tools = [{"type": "web_search_20250305", "name": "web_search"}]

    # Handle multi-turn tool_use loop (server-side search resolves in one turn,
    # but guard against unexpected client-side tool_use stop_reason).
    for _ in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    return parse_findings(block.text)
            return []

        if response.stop_reason == "tool_use":
            # Shouldn't occur with server-side web_search; handle gracefully.
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Search not available client-side.",
                }
                for block in response.content
                if hasattr(block, "type") and block.type == "tool_use"
            ]
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        else:
            break

    return []


def parse_findings(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    start = text.find("[")
    end = text.rfind("]") + 1
    if start != -1 and end > start:
        try:
            result = json.loads(text[start:end])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    return []


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:50]


def write_finding(finding: dict) -> Path:
    title = finding.get("title", "untitled")
    source_url = finding.get("source_url", "")
    domain = finding.get("domain", "unknown")
    summary = finding.get("summary", "")
    action = finding.get("action", "")

    filename = f"{TODAY}-{HOUR}-{slugify(title)}.md"
    filepath = PENDING_REVIEW / filename
    filepath.write_text(
        f"# {title}\n"
        f"## Source\n{source_url}\n"
        f"## Domain\n{domain}\n"
        f"## Summary\n{summary}\n"
        f"## Action\n{action}\n"
        f"## Verified\nYes — fetched via web search\n"
    )
    return filepath


def main():
    api_key = load_api_key()
    # Read context (available to scout but not passed to API in this minimal version;
    # priorities and directions are loaded so future prompts can reference them).
    read_context()

    try:
        findings = call_api(api_key)
    except Exception as exc:
        print(f"ERROR: API call failed — {exc}", file=sys.stderr)
        sys.exit(1)

    high = medium = low = written = 0
    for f in findings:
        if not isinstance(f, dict):
            continue
        relevance = f.get("relevance", "LOW").upper()
        verified = f.get("verified", False)

        if relevance == "HIGH":
            high += 1
        elif relevance == "MEDIUM":
            medium += 1
        else:
            low += 1

        if relevance in ("HIGH", "MEDIUM") and verified:
            write_finding(f)
            written += 1

    print(
        f"Research scout complete: {written} findings written "
        f"({high} HIGH, {medium} MEDIUM, {low} LOW relevance)"
    )


if __name__ == "__main__":
    main()
