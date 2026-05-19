#!/usr/bin/env python3
"""
Research scout — fetches real findings via Claude CLI (Pro subscription with web search).
Replaces direct Anthropic API calls that require paid credits.
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
PROMPT_FILE = Path("/tmp/scout_prompt.txt")
_NOW = datetime.now(timezone.utc)
TODAY = _NOW.strftime("%Y-%m-%d")
HOUR = _NOW.strftime("%H")


def read_priorities() -> str:
    priorities_path = SWARM / "brain/priorities.md"
    if not priorities_path.exists():
        return ""
    lines = priorities_path.read_text().splitlines()[:50]
    return "\n".join(lines)


def build_prompt() -> str:
    priorities = read_priorities()
    context_block = ""
    if priorities:
        context_block = f"\n\n=== brain/priorities.md (first 50 lines) ===\n{priorities}\n"

    return (
        "You are a research scout for a Polymarket trading intelligence system. "
        "Your job is to find REAL, VERIFIABLE information from actual web sources. "
        "Only report things you actually read from web search results. "
        "Never invent papers, commits, or announcements from memory.\n"
        f"{context_block}\n"
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
        "Output findings as a JSON array. Nothing else — no preamble, no explanation."
    )


def call_claude_cli(prompt_text: str) -> list[dict]:
    PROMPT_FILE.write_text(prompt_text)
    # Strip ANTHROPIC_API_KEY so the CLI authenticates via OAuth (Pro subscription)
    # rather than the depleted API key account.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        result = subprocess.run(
            ["claude", "--print", "--allowed-tools", "WebSearch", "--", prompt_text],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    finally:
        PROMPT_FILE.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ERROR: claude CLI exited {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)

    return parse_findings(result.stdout)


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
        f"## Verified\nYes — fetched via Claude CLI web search\n"
    )
    return filepath


def main():
    prompt_text = build_prompt()

    try:
        findings = call_claude_cli(prompt_text)
    except subprocess.TimeoutExpired:
        print("ERROR: claude CLI timed out after 120s", file=sys.stderr)
        PROMPT_FILE.unlink(missing_ok=True)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        PROMPT_FILE.unlink(missing_ok=True)
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
