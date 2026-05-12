#!/usr/bin/env python3
"""
Polymarket changelog monitor.
Fetches https://docs.polymarket.com/changelog, detects new entries,
and sends a Telegram alert to the agents bot.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

CHANGELOG_URL = "https://docs.polymarket.com/changelog"
STATE_FILE = Path(__file__).parent.parent / "brain" / "polymarket_changelog_state.json"
ENV_FILE = Path.home() / ".env_trading"

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
# Russia x Ukraine ceasefire by Jan 31, 2026 — resolved, stable, known to exist in DB.
GAMMA_FILTER_CHECK_CID = "0xb8c1bd306a8a4cedfb280e114e655c5092b3f37edccae05cd877d7f21a5774ce"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env(path: Path) -> None:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: {key} not set. Source ~/.env_trading before running.", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_seen_date": None, "last_seen_title": None,
                "last_checked": None, "entries_seen": []}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"State saved → {STATE_FILE}")


# ---------------------------------------------------------------------------
# Changelog fetch + parse
# ---------------------------------------------------------------------------

def fetch_changelog(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "trading-swarm-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_latest_entry(html: str) -> tuple[str | None, str | None]:
    """
    Return (date_str, title) for the most recent changelog entry.
    Gitbook changelogs typically render entries as <h2> with a date and then
    a following heading or paragraph for the title/summary.
    We try multiple patterns to stay robust against minor markup changes.
    """
    # Pattern 1: <h2>Month DD, YYYY</h2> optionally followed by <h3>title</h3>
    date_pattern = re.compile(
        r'<h[23][^>]*>\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*'
        r'\s+\d{1,2},\s*\d{4})\s*</h[23]>',
        re.IGNORECASE
    )
    title_pattern = re.compile(
        r'</h[23]>\s*(?:<[^>]+>)*\s*([^<]{5,120})',
        re.IGNORECASE | re.DOTALL
    )

    date_match = date_pattern.search(html)
    if not date_match:
        # Fallback: look for date-like text anywhere
        fallback = re.search(
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s*\d{4})',
            html, re.IGNORECASE
        )
        if fallback:
            return fallback.group(1).strip(), None
        return None, None

    date_str = date_match.group(1).strip()

    # Try to grab a title from the text immediately after the date heading
    remainder = html[date_match.end():]
    title_match = title_pattern.search(remainder[:500])
    title = title_match.group(1).strip() if title_match else None
    if title:
        # Clean up whitespace / HTML entities
        title = re.sub(r'\s+', ' ', title).strip()
        title = title[:120]

    return date_str, title


# ---------------------------------------------------------------------------
# Next Monday helper
# ---------------------------------------------------------------------------

def next_monday_str() -> str:
    today = datetime.now(timezone.utc)
    days_ahead = (7 - today.weekday()) % 7 or 7   # 0=Monday; ensure next Mon
    nxt = today + timedelta(days=days_ahead)
    return nxt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(token: str, chat_id: str, text: str) -> None:
    payload = json.dumps({"chat_id": chat_id, "text": text,
                          "parse_mode": "HTML"}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        if body.get("ok"):
            print("Telegram message sent.")
        else:
            print(f"Telegram API error: {body}", file=sys.stderr)
    except urllib.error.HTTPError as e:
        print(f"Telegram HTTP {e.code}: {e.read().decode()}", file=sys.stderr)


def build_no_change_message(
    last_seen_date: str | None, checked_at: str, gamma_filter: str = "UNKNOWN"
) -> str:
    date_checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    gamma_icon = {"OK": "✅", "BROKEN": "⚠️", "ERROR": "❓"}.get(gamma_filter, "❓")
    return (
        f"🔍 Polymarket Changelog — {date_checked}\n"
        f"No new entries since {last_seen_date or 'unknown'}\n"
        f"Endpoints: Data API ✅ Gamma filter {gamma_icon} ({gamma_filter}) CLOB ✅\n"
        f"Next check: {next_monday_str()}"
    )


def build_new_entry_message(date_str: str, title: str | None) -> str:
    summary = title if title else "(see changelog for details)"
    return (
        f"⚠️ Polymarket Changelog Update\n\n"
        f"New entry: {date_str} — {summary}\n"
        f"Review: {CHANGELOG_URL}\n"
        f"Check if any of these affect our system:\n"
        f"- Data API trade response format\n"
        f"- Gamma API market metadata\n"
        f"- CLOB endpoint structure\n"
        f"- Timestamp formats"
    )


# ---------------------------------------------------------------------------
# Gamma API filter health check
# ---------------------------------------------------------------------------

def check_gamma_filter() -> str:
    """
    Probe whether the Gamma API conditionId filter is working.

    Returns "OK" if the filter returns the expected market, "BROKEN" if the
    filter is silently ignored (wrong market returned), or "ERROR" on network
    or parse failure.
    """
    url = (
        f"{GAMMA_API_BASE}/markets"
        f"?conditionId={GAMMA_FILTER_CHECK_CID}&limit=1"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "trading-swarm-monitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"Gamma filter check ERROR: {e}", file=sys.stderr)
        return "ERROR"

    markets = data if isinstance(data, list) else data.get("markets", [])
    if not markets:
        print("Gamma filter check: empty response — treating as BROKEN")
        return "BROKEN"

    returned_cid = markets[0].get("conditionId", "")
    if returned_cid.lower() == GAMMA_FILTER_CHECK_CID.lower():
        print("Gamma API filter OK — conditionId parameter honoured.")
        return "OK"
    else:
        print(
            f"Gamma API filter BROKEN — requested {GAMMA_FILTER_CHECK_CID[:10]}…"
            f" but got {returned_cid[:10] if returned_cid else '(none)'}…"
        )
        return "BROKEN"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    load_env(ENV_FILE)
    token = require_env("TELEGRAM_AGENTS_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching {CHANGELOG_URL} ...")
    try:
        html = fetch_changelog(CHANGELOG_URL)
    except Exception as e:
        print(f"ERROR fetching changelog: {e}", file=sys.stderr)
        sys.exit(1)

    latest_date, latest_title = parse_latest_entry(html)
    print(f"Latest entry: {latest_date!r}  title: {latest_title!r}")

    state = load_state()
    last_seen_date = state.get("last_seen_date")

    is_new = latest_date and (latest_date not in (state.get("entries_seen") or []))

    # --- Gamma API filter health check ---
    gamma_status = check_gamma_filter()
    prev_gamma_status = state.get("gamma_filter_status", "BROKEN")
    state["gamma_filter_status"] = gamma_status

    # Alert immediately if the filter has recovered (BROKEN → OK).
    if gamma_status == "OK" and prev_gamma_status != "OK":
        recovery_msg = (
            "✅ Gamma API filter RECOVERED\n\n"
            "The conditionId filter on GET /markets is now working.\n"
            "conditionId queries can be used for search again.\n"
            "Update brain/reference-library/polymarket-market-structure.md "
            "Gamma API Known Limitations section accordingly."
        )
        print("Gamma filter recovered — sending recovery alert.")
        send_telegram(token, chat_id, recovery_msg)

    # --- Changelog check ---
    if is_new:
        print(f"New entry detected: {latest_date}")
        msg = build_new_entry_message(latest_date, latest_title)
        entries_seen = list(state.get("entries_seen") or [])
        if latest_date not in entries_seen:
            entries_seen.insert(0, latest_date)
        state.update({
            "last_seen_date": latest_date,
            "last_seen_title": latest_title,
            "last_checked": now_iso,
            "entries_seen": entries_seen[:50],   # keep last 50
        })
    else:
        print("No new entries.")
        msg = build_no_change_message(last_seen_date or latest_date, now_iso, gamma_status)
        state["last_checked"] = now_iso

    send_telegram(token, chat_id, msg)
    save_state(state)


if __name__ == "__main__":
    main()
