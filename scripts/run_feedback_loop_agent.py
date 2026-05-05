#!/usr/bin/env python3
"""
feedback-loop-agent weekly run script.

Closes the prediction loop: audits signal accuracy, pre-resolution
intelligence, ELO predictive validity, and strategy revalidation
schedule. Writes structured findings to findings.json and sends a
Telegram summary via the agents bot.

Run: cd ~/trading-swarm && source ~/.env_trading && python3 scripts/run_feedback_loop_agent.py
Cron: 0 7 * * 1  (Mondays 07:00 UTC)
Database: READ ONLY — never writes to polymarket_tracker.db.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request
import urllib.parse

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT      = Path("/home/parison/trading-swarm")

sys.path.insert(0, str(REPO_ROOT))
from scripts.market_filter import should_include_market
DB_PATH        = Path("/home/parison/projects/first-repo/data/polymarket_tracker.db")
SIGNALS_JSON   = REPO_ROOT / "brain/signals.json"
FINDINGS_JSON  = REPO_ROOT / "brain/findings.json"
FEEDBACK_JSON  = REPO_ROOT / "brain/feedback.json"
STRATEGY_REG   = REPO_ROOT / "brain/strategy-registry.md"
SIGNAL_OUT_DIR = REPO_ROOT / "brain/agent-outputs/signal-agent"
PRE_RES_DIR    = REPO_ROOT / "brain/agent-outputs/pre-resolution"
FL_OUT_DIR     = REPO_ROOT / "brain/agent-outputs/feedback-loop"
FL_STATE_FILE  = REPO_ROOT / "brain/feedback_loop_state.json"
STRAT_NOTES    = REPO_ROOT / "brain/strategy-notes"

# ── Constants ─────────────────────────────────────────────────────────────────
TODAY            = datetime.now(timezone.utc).date()
TODAY_STR        = TODAY.isoformat()
NOW_ISO          = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
EXPIRES_ISO      = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
SEVEN_DAYS_AGO   = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
MIN_SAMPLE       = 10
ELO_TIERS        = {
    "LEGENDARY": (2175, float("inf")),
    "ELITE":     (1800, 2175),
    "QUALIFIED": (1500, 1800),
}
# Sports exclusion — applied to market title (case-insensitive).
# Rule: no sports markets in any agent scope (CLAUDE.md hard rule).
SPORTS_KEYWORDS  = [
    " vs ",          # head-to-head format catches tennis, cricket, boxing, etc.
    "nba", "nfl", "mlb", "nhl",
    "football", "basketball", "baseball", "hockey", "soccer",
    "tennis", "golf", "ufc", "mma", "olympics",
    "draft", "super bowl", "world cup", "world series",
    "warriors", "lakers", "yankees", "giants", "lebron",
    "super league", "premier league", "la liga", "bundesliga",
    "exact score", "cricket", "rugby",
]

# ── Env ────────────────────────────────────────────────────────────────────────
# Load ~/.env_trading directly so the script works whether vars are exported
# in the caller's shell or not (cron, systemd, or direct invocation).
def _load_env_file():
    env_file = Path.home() / ".env_trading"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_env_file()

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_AGENTS_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ── Utilities ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[feedback-loop-agent] {msg}", flush=True)


def is_sports_market(title: str, category: str = "") -> bool:
    if (category or "").lower() == "sports":
        return True
    t = (title or "").lower()
    return any(kw in t for kw in SPORTS_KEYWORDS)


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_db_conn():
    """Open polymarket_tracker.db read-only via URI."""
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def load_and_increment_run_count() -> int:
    """Read run_count from state file, increment, write back, return new count."""
    if FL_STATE_FILE.exists():
        try:
            state = json.loads(FL_STATE_FILE.read_text())
            count = int(state.get("run_count", 0)) + 1
        except (json.JSONDecodeError, ValueError):
            count = 1
    else:
        count = 1
    FL_STATE_FILE.write_text(json.dumps({"run_count": count, "last_run": TODAY_STR}, indent=2))
    log(f"Run count: {count}")
    return count


def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("WARNING: TELEGRAM_AGENTS_TOKEN or TELEGRAM_CHAT_ID not set — skipping notification")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                log("Telegram notification sent")
            else:
                log(f"Telegram API error: {result.get('description', result)}")
    except Exception as exc:
        log(f"Telegram send failed: {exc}")


# ── Step 1 — Signal accuracy audit ────────────────────────────────────────────

def step1_signal_accuracy(conn) -> dict:
    log("Step 1 — Signal accuracy audit")
    signals_data = load_json(SIGNALS_JSON)
    all_signals  = signals_data.get("signals", [])

    auditable = [s for s in all_signals if s.get("confidence") in ("HIGH", "MEDIUM")]
    log(f"  Total signals in bus: {len(all_signals)}, HIGH/MEDIUM: {len(auditable)}")

    resolved_count = 0
    correct        = 0
    incorrect      = 0
    unresolved     = 0
    results        = []

    for sig in auditable:
        payload    = sig.get("payload", {})
        market_id  = payload.get("market_id", "")
        direction  = (payload.get("direction") or "").upper()
        confidence = sig.get("confidence", "")
        title      = payload.get("market_title", "unknown")
        sig_status = (sig.get("status") or "").lower()

        if not market_id:
            continue

        # Operational signals (completed) are not accuracy-trackable
        if sig_status == "completed":
            continue

        # Signal was manually resolved — use its own resolution field
        if sig_status == "resolved":
            resolution = (sig.get("resolution") or "").upper()
            # Resolution field starts with YES or NO (e.g. "NO — Ramaswamy running...")
            resolved_outcome = resolution.split()[0] if resolution else None
            was_correct = bool(resolved_outcome and direction == resolved_outcome)
            resolved_count += 1
            if was_correct:
                correct += 1
            else:
                incorrect += 1
            results.append({
                "title": title, "direction": direction, "confidence": confidence,
                "resolved": True, "outcome": resolved_outcome,
                "correct": was_correct,
                "note": f"resolved in signals.json: {sig.get('resolution', '')}",
            })
            continue

        # For pending/processed signals fall through to DB lookup
        row = conn.execute(
            "SELECT resolved, winning_outcome, title, category FROM markets WHERE market_id = ?",
            (market_id,),
        ).fetchone()

        if not row:
            log(f"  Market {market_id[:20]}... not found in DB")
            results.append({
                "title": title, "direction": direction, "confidence": confidence,
                "resolved": False, "outcome": None, "correct": None,
                "note": "not found in DB",
            })
            continue

        resolved_flag, winning_outcome, db_title, category = row
        display_title = db_title or title

        if not resolved_flag or not winning_outcome:
            unresolved += 1
            results.append({
                "title": display_title, "direction": direction, "confidence": confidence,
                "resolved": False, "outcome": None, "correct": None,
                "note": "market not yet resolved",
            })
            continue

        resolved_count += 1
        was_correct = direction == (winning_outcome or "").upper()
        if was_correct:
            correct += 1
        else:
            incorrect += 1

        results.append({
            "title": display_title, "direction": direction, "confidence": confidence,
            "resolved": True, "outcome": winning_outcome, "correct": was_correct,
        })

    accuracy = (correct / resolved_count) if resolved_count >= MIN_SAMPLE else None
    log(f"  Resolved: {resolved_count}, correct: {correct}, incorrect: {incorrect}, "
        f"unresolved: {unresolved}, sufficient data: {resolved_count >= MIN_SAMPLE}")

    return {
        "total_signals":    len(all_signals),
        "auditable":        len(auditable),
        "resolved_markets": resolved_count,
        "correct":          correct,
        "incorrect":        incorrect,
        "unresolved":       unresolved,
        "accuracy":         accuracy,
        "sufficient_data":  resolved_count >= MIN_SAMPLE,
        "results":          results,
    }


# ── Step 2 — Pre-resolution intelligence audit ────────────────────────────────

def step2_pre_resolution(conn) -> dict:
    log("Step 2 — Pre-resolution intelligence audit")

    if not PRE_RES_DIR.exists():
        log("  Pre-resolution directory not found — agent has not produced output yet")
        return {
            "directory_exists": False,
            "files_found":      0,
            "signals_audited":  0,
            "sufficient_data":  False,
            "note": "brain/agent-outputs/pre-resolution/ does not exist — "
                    "signal-agent pre-resolution scans have not run yet",
        }

    md_files = sorted(PRE_RES_DIR.glob("*.md"), reverse=True)
    log(f"  Found {len(md_files)} pre-resolution file(s)")

    # Pull the 4-signal baseline batch already recorded in findings.json
    findings_data = load_json(FINDINGS_JSON)
    batch = None
    for f in findings_data.get("findings", []):
        if f.get("id") == "2026-03-28-PRE-RES-BASELINE-001" and "signals_in_batch" in f:
            batch = f["signals_in_batch"]
            break

    signals_audited = 0
    by_tier: dict = {
        "LEGENDARY": {"correct": 0, "total": 0},
        "ELITE":     {"correct": 0, "total": 0},
        "QUALIFIED": {"correct": 0, "total": 0},
    }

    if batch:
        for sig in batch:
            outcome   = (sig.get("outcome") or "").upper()
            direction = (sig.get("direction") or "").upper()
            tier      = sig.get("tier", "QUALIFIED")
            if outcome and direction:
                signals_audited += 1
                t = by_tier.get(tier, by_tier["QUALIFIED"])
                t["total"] += 1
                if direction == outcome:
                    t["correct"] += 1

    accuracy = None
    if signals_audited >= MIN_SAMPLE:
        total_correct = sum(v["correct"] for v in by_tier.values())
        accuracy = total_correct / signals_audited

    log(f"  Signals audited: {signals_audited}, sufficient data: {signals_audited >= MIN_SAMPLE}")

    return {
        "directory_exists": True,
        "files_found":      len(md_files),
        "signals_audited":  signals_audited,
        "by_tier":          by_tier,
        "accuracy":         accuracy,
        "sufficient_data":  signals_audited >= MIN_SAMPLE,
        "note": (f"Sample size {signals_audited} < {MIN_SAMPLE} minimum — "
                 "conclusions deferred") if signals_audited < MIN_SAMPLE else None,
    }


# ── Step 3 — ELO predictive validity check ────────────────────────────────────
# Audit filters applied per 2026-04-26 data integrity audit:
#   JOIN key:        markets m ON m.market_id = t.market_id  (never condition_id)
#   Trader filter:   t.research_excluded = 0  (t = traders alias in positions query)
#   Timestamp:       N/A — positions table carries no individual trade timestamp
#   Resolution:      resolved = 1, winning_outcome != '' already applied to markets query
# Source: reports/data_integrity_audit_20260426.md in first-repo

def step3_elo_validity(conn) -> dict:
    log("Step 3 — ELO predictive validity check")

    markets = conn.execute("""
        SELECT market_id, title, category, winning_outcome, resolution_date
        FROM markets
        WHERE resolved = 1
          AND resolution_date IS NOT NULL
          AND resolution_date >= ?
          AND winning_outcome IS NOT NULL
          AND winning_outcome != ''
        ORDER BY resolution_date DESC
    """, (SEVEN_DAYS_AGO,)).fetchall()

    log(f"  Markets resolved in past 7 days: {len(markets)}")

    non_sports = []
    sports_excluded = 0
    for r in markets:
        market_title = r[1] or ""
        if not should_include_market(market_title):
            sports_excluded += 1
            continue
        non_sports.append(r)
    log(f"  After production filter: {len(non_sports)} markets pass "
        f"({sports_excluded} excluded)")

    tier_results = {
        "LEGENDARY": {"correct": 0, "total": 0, "markets": []},
        "ELITE":     {"correct": 0, "total": 0, "markets": []},
        "QUALIFIED": {"correct": 0, "total": 0, "markets": []},
    }
    markets_with_positions = 0

    for market_id, title, category, winning_outcome, resolution_date in non_sports:
        # Exclude bidirectional (LP) traders — only count traders with a single
        # direction in this market. Implements finding 2026-04-21-SIGNAL-STRUCTURE-001.
        positions = conn.execute("""
            WITH directional AS (
                SELECT trader_address
                FROM positions
                WHERE market_id = ?
                GROUP BY trader_address
                HAVING COUNT(DISTINCT outcome) = 1
            )
            SELECT p.outcome, p.entry_shares, t.comprehensive_elo
            FROM positions p
            JOIN traders t  ON p.trader_address = t.address
            JOIN directional d ON p.trader_address = d.trader_address
            WHERE p.market_id = ?
              AND t.comprehensive_elo >= 1500
              AND t.wash_trade_suspect = 0
              AND t.bot_suspect = 0
              AND t.research_excluded = 0
              AND p.entry_shares > 0
        """, (market_id, market_id)).fetchall()

        if not positions:
            continue

        markets_with_positions += 1

        for tier_name, (elo_low, elo_high) in ELO_TIERS.items():
            tier_pos = [(out, shares, elo)
                        for out, shares, elo in positions
                        if elo_low <= elo < elo_high]
            if not tier_pos:
                continue

            votes: dict = {}
            for outcome, shares, elo in tier_pos:
                key = (outcome or "").upper()
                votes[key] = votes.get(key, 0.0) + shares

            if not votes:
                continue

            consensus = max(votes, key=votes.get)
            was_correct = consensus == (winning_outcome or "").upper()

            tier_results[tier_name]["total"] += 1
            if was_correct:
                tier_results[tier_name]["correct"] += 1
            tier_results[tier_name]["markets"].append({
                "title":        (title or "")[:60],
                "consensus":    consensus,
                "outcome":      winning_outcome,
                "correct":      was_correct,
                "tier_traders": len(tier_pos),
            })

    log(f"  Non-sports markets with elite directional positions: {markets_with_positions}")
    for tier, data in tier_results.items():
        if data["total"]:
            log(f"  {tier}: {data['correct']}/{data['total']} = "
                f"{data['correct']/data['total']:.0%}")
        else:
            log(f"  {tier}: no data")

    return {
        "markets_resolved_7d":       len(markets),
        "sports_excluded":           sports_excluded,
        "non_sports_with_positions": markets_with_positions,
        "tier_results":              tier_results,
        "sufficient_data":           markets_with_positions >= MIN_SAMPLE,
    }


# ── Step 4 — Strategy registry review ────────────────────────────────────────

def step4_strategy_review() -> dict:
    log("Step 4 — Strategy registry review")
    text = STRATEGY_REG.read_text() if STRATEGY_REG.exists() else ""

    # Split on "### STR-NNN" headings
    parts = re.split(r"\n### (STR-\d+[^\n]*)", text)
    strategies = []
    i = 1
    while i < len(parts):
        name  = parts[i].strip()
        block = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2

        def _field(pattern):
            m = re.search(pattern, block)
            return m.group(1).strip() if m else "—"

        status    = _field(r"Status:\s*(\S+)")
        last_rev  = _field(r"Last revalidation:\s*(.+)")
        next_due  = _field(r"Next revalidation due:\s*(.+)")

        overdue       = False
        days_overdue  = 0
        overdue_reason = None

        if status == "ACTIVE":
            if last_rev in ("—", ""):
                overdue        = True
                overdue_reason = "ACTIVE strategy has never been revalidated"
            else:
                try:
                    d = datetime.strptime(last_rev[:10], "%Y-%m-%d").date()
                    days = (TODAY - d).days
                    if days > 30:
                        overdue        = True
                        days_overdue   = days
                        overdue_reason = f"{days} days since last revalidation (threshold: 30)"
                except ValueError:
                    pass

        # Also check next_due for any non-RETIRED strategy
        if status not in ("RETIRED",) and next_due not in ("—", ""):
            try:
                d = datetime.strptime(next_due[:10], "%Y-%m-%d").date()
                if TODAY > d:
                    days = (TODAY - d).days
                    if not overdue or days > days_overdue:
                        overdue        = True
                        days_overdue   = days
                        overdue_reason = (
                            f"Past next revalidation due date {next_due} ({days} days overdue)"
                        )
            except ValueError:
                pass

        strategies.append({
            "name":                 name,
            "status":               status,
            "last_revalidation":    last_rev,
            "next_revalidation_due": next_due,
            "overdue":              overdue,
            "days_overdue":         days_overdue,
            "overdue_reason":       overdue_reason,
        })

    overdue = [s for s in strategies if s["overdue"]]
    log(f"  Strategies parsed: {len(strategies)}, overdue: {len(overdue)}")
    for s in overdue:
        log(f"  OVERDUE: {s['name']} — {s['overdue_reason']}")

    return {
        "strategies_checked": len(strategies),
        "overdue":            overdue,
        "all_strategies":     strategies,
    }


# ── Step 5 — Write findings ───────────────────────────────────────────────────

def step5_write_findings(s1, s2, s3, s4, run_count: int = 1) -> list:
    log("Step 5 — Writing findings to findings.json")
    data        = load_json(FINDINGS_JSON)
    existing    = data.get("findings", [])
    existing_ids = {f["id"] for f in existing}
    new_findings = []

    def add(finding):
        if finding["id"] not in existing_ids:
            new_findings.append(finding)

    # Signal accuracy finding
    resolved = s1["resolved_markets"]
    if s1["sufficient_data"]:
        acc = s1["accuracy"]
        add({
            "id":           f"{TODAY_STR}-SIGNAL-ACCURACY-001",
            "generated_by": "feedback-loop-agent",
            "generated_at": NOW_ISO,
            "finding_type": "signal_accuracy",
            "confidence":   "HIGH" if resolved >= 20 else "MEDIUM",
            "sample_size":  resolved,
            "summary":      f"Signal accuracy over {resolved} resolved markets: {acc:.0%}",
            "detail": {
                "metric":         "signal_direction_accuracy",
                "value":          round(acc, 4),
                "baseline":       0.50,
                "direction":      "above_baseline" if acc > 0.50 else "below_baseline",
                "weeks_observed": run_count,
            },
            "actionable": acc < 0.55,
            "action_recommendation": (
                "Signal accuracy above baseline — maintain current methodology"
                if acc >= 0.55
                else "Signal accuracy at or below baseline — review signal logic before expanding scope"
            ),
            "expires_at": EXPIRES_ISO,
        })
    else:
        add({
            "id":           f"{TODAY_STR}-SIGNAL-ACCURACY-INSUFFICIENT-001",
            "generated_by": "feedback-loop-agent",
            "generated_at": NOW_ISO,
            "finding_type": "signal_accuracy",
            "confidence":   "LOW",
            "sample_size":  resolved,
            "summary":      (f"Insufficient resolved signals to compute accuracy — "
                             f"{resolved} resolved, {MIN_SAMPLE} required"),
            "detail": {
                "metric":         "signal_direction_accuracy",
                "value":          None,
                "baseline":       0.50,
                "direction":      "pending",
                "weeks_observed": run_count,
            },
            "actionable": False,
            "action_recommendation": (
                f"Await {MIN_SAMPLE - resolved} more signal resolutions before drawing conclusions"
            ),
            "expires_at": EXPIRES_ISO,
        })

    # ELO validity findings
    mwp = s3["non_sports_with_positions"]
    if s3["sufficient_data"]:
        for tier, data_t in s3["tier_results"].items():
            n = data_t["total"]
            if n >= MIN_SAMPLE:
                acc = data_t["correct"] / n
                add({
                    "id":           f"{TODAY_STR}-ELO-{tier}-001",
                    "generated_by": "feedback-loop-agent",
                    "generated_at": NOW_ISO,
                    "finding_type": "elo_validity",
                    "confidence":   "HIGH" if n >= 20 else "MEDIUM",
                    "sample_size":  n,
                    "summary":      (f"{tier} tier consensus accuracy: {acc:.0%} "
                                     f"over {n} non-sports markets"),
                    "detail": {
                        "metric":         f"elo_{tier.lower()}_consensus_accuracy",
                        "value":          round(acc, 4),
                        "baseline":       0.50,
                        "direction":      "above_baseline" if acc > 0.50 else "below_baseline",
                        "weeks_observed": run_count,
                    },
                    "actionable": acc > 0.60,
                    "action_recommendation": (
                        f"Increase {tier} tier weighting — exceeds 60% accuracy"
                        if acc > 0.60
                        else f"{tier} tier at baseline — maintain current weighting"
                    ),
                    "expires_at": EXPIRES_ISO,
                })
    else:
        add({
            "id":           f"{TODAY_STR}-ELO-VALIDITY-INSUFFICIENT-001",
            "generated_by": "feedback-loop-agent",
            "generated_at": NOW_ISO,
            "finding_type": "elo_validity",
            "confidence":   "LOW",
            "sample_size":  mwp,
            "summary":      (f"Insufficient non-sports resolved markets with elite positions — "
                             f"{mwp} found, {MIN_SAMPLE} required"),
            "detail": {
                "metric":         "elo_consensus_accuracy",
                "value":          None,
                "baseline":       0.50,
                "direction":      "pending",
                "weeks_observed": run_count,
            },
            "actionable": False,
            "action_recommendation": (
                "Continue collecting non-sports market resolutions with elite trader positions"
            ),
            "expires_at": EXPIRES_ISO,
        })

    # Overdue strategy finding
    overdue_strats = s4["overdue"]
    if overdue_strats:
        names = ", ".join(s["name"] for s in overdue_strats)
        add({
            "id":           f"{TODAY_STR}-STRATEGY-OVERDUE-001",
            "generated_by": "feedback-loop-agent",
            "generated_at": NOW_ISO,
            "finding_type": "strategy_performance",
            "confidence":   "HIGH",
            "sample_size":  len(overdue_strats),
            "summary":      f"{len(overdue_strats)} strategy/strategies overdue for revalidation: {names}",
            "detail": {
                "metric":         "strategies_overdue_revalidation",
                "value":          float(len(overdue_strats)),
                "baseline":       0.0,
                "direction":      "above_baseline",
                "weeks_observed": run_count,
            },
            "actionable": True,
            "action_recommendation": (
                "Revalidation signals written to signals.json — backtest-agent to action"
            ),
            "expires_at": EXPIRES_ISO,
        })

    if new_findings:
        data["findings"] = existing + new_findings
        save_json(FINDINGS_JSON, data)
        log(f"  {len(new_findings)} new finding(s) written")
    else:
        log("  No new findings (all IDs already present)")

    return new_findings


# ── Write revalidation signals ─────────────────────────────────────────────────

def write_revalidation_signals(overdue: list) -> list:
    if not overdue:
        return []

    signals_data = load_json(SIGNALS_JSON)
    current      = signals_data.get("signals", [])
    existing_keys = {
        (s.get("payload", {}).get("strategy_name", ""), s.get("type", ""))
        for s in current
    }
    written = []

    for strat in overdue:
        key = (strat["name"], "revalidation_requested")
        if key in existing_keys:
            log(f"  Revalidation signal already exists for {strat['name']} — skipping")
            continue

        current.append({
            "from":      "feedback-loop-agent",
            "to":        "backtest-agent",
            "type":      "revalidation_requested",
            "payload": {
                "strategy_name":       strat["name"],
                "strategy_path":       str(STRATEGY_REG),
                "last_validated":      strat["last_revalidation"],
                "days_since_validation": strat["days_overdue"],
                "original_dsr":        None,
                "original_sharpe":     None,
                "reason":              strat.get("overdue_reason", "Routine 30-day revalidation"),
            },
            "timestamp": NOW_ISO,
            "status":    "pending",
        })
        written.append(strat["name"])
        log(f"  Revalidation signal written for {strat['name']}")

    if written:
        signals_data["signals"] = current
        save_json(SIGNALS_JSON, signals_data)

    return written


# ── Write weekly report ────────────────────────────────────────────────────────

def write_report(s1, s2, s3, s4, new_findings, reval_written, run_count: int = 1) -> Path:
    FL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = FL_OUT_DIR / f"{TODAY_STR}-weekly-audit.md"

    def acc_str(val, n):
        if val is None:
            return f"insufficient data ({n}/{MIN_SAMPLE} samples)"
        return f"{val:.0%} ({n} resolved markets)"

    lines = [
        "# Feedback Loop Agent — Weekly Audit",
        f"**Date:** {TODAY_STR}",
        f"**Generated:** {NOW_ISO}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Markets resolved past 7 days | {s3['markets_resolved_7d']} |",
        f"| Sports markets excluded | {s3['sports_excluded']} |",
        f"| Non-sports markets with elite positions | {s3['non_sports_with_positions']} |",
        f"| Signal accuracy | {acc_str(s1['accuracy'], s1['resolved_markets'])} |",
        f"| Strategies overdue for revalidation | {len(s4['overdue'])} |",
        f"| New findings written | {len(new_findings)} |",
        "",
        "---",
        "",
        "## Step 1 — Signal Accuracy Audit",
        "",
        f"- Total signals in bus: **{s1['total_signals']}**",
        f"- HIGH/MEDIUM signals: **{s1['auditable']}**",
        f"- With resolved market outcomes: **{s1['resolved_markets']}**",
        f"- Unresolved (awaiting outcome): **{s1['unresolved']}**",
        "",
    ]

    if s1["results"]:
        lines += [
            "| Market | Confidence | Signal | Outcome | Correct? |",
            "|--------|-----------|--------|---------|----------|",
        ]
        for r in s1["results"]:
            if r["resolved"]:
                flag = "✓" if r["correct"] else "✗"
            else:
                flag = "⧖ pending"
            lines.append(
                f"| {r['title'][:55]} | {r['confidence']} "
                f"| {r['direction']} | {r.get('outcome','—')} | {flag} |"
            )
        lines.append("")

    if not s1["sufficient_data"]:
        lines += [
            f"> **Insufficient data:** {s1['resolved_markets']}/{MIN_SAMPLE} resolved signals. "
            f"Accuracy conclusions deferred to next run.",
            "",
        ]

    lines += [
        "---",
        "",
        "## Step 2 — Pre-Resolution Intelligence Audit",
        "",
    ]

    if not s2["directory_exists"]:
        lines += [
            f"> **Not yet available:** `brain/agent-outputs/pre-resolution/` does not exist. "
            f"Signal-agent has not produced pre-resolution scans. "
            f"This step will populate once that directory is present.",
            "",
            "**Known baseline batch (4 signals, recorded in findings.json):**",
            "",
            "| Market | Tier | Signal | Outcome | Correct? |",
            "|--------|------|--------|---------|----------|",
            "| Russia/Ukraine ceasefire by Mar 31 2026 | ELITE | YES | NO | ✗ |",
            "| Trump out as President by Mar 31 2026 | LEGENDARY | NO | NO | ✓ |",
            "| Anthropic best AI model end of March 2026 | QUALIFIED | YES | YES | ✓ |",
            "| xAI best AI model end of March 2026 | QUALIFIED | YES | NO | ✗ |",
            "",
            "**Running total: 2/4 (50%) — at baseline. Sample size below minimum (4/10).**",
            "",
        ]
    else:
        lines += [f"- Files in directory: {s2['files_found']}"]
        lines += [f"- Signals audited: {s2['signals_audited']}"]
        if s2.get("note"):
            lines.append(f"> **Note:** {s2['note']}")
        if s2["by_tier"]:
            lines += [
                "",
                "| ELO Tier | Correct | Total | Accuracy |",
                "|----------|---------|-------|----------|",
            ]
            for tier, d in s2["by_tier"].items():
                a = f"{d['correct']/d['total']:.0%}" if d["total"] else "—"
                lines.append(f"| {tier} | {d['correct']} | {d['total']} | {a} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Step 3 — ELO Predictive Validity Check",
        "",
        f"- Markets resolved in past 7 days: **{s3['markets_resolved_7d']}**",
        f"- Sports markets excluded (per hard rules): **{s3['sports_excluded']}**",
        f"- Non-sports markets with elite directional positions: **{s3['non_sports_with_positions']}**",
        "",
    ]

    if s3["sufficient_data"]:
        lines += [
            "| ELO Tier | Markets | Correct | Accuracy |",
            "|----------|---------|---------|----------|",
        ]
        for tier, d in s3["tier_results"].items():
            if d["total"]:
                a = f"{d['correct']/d['total']:.0%}"
            else:
                a = "—"
            lines.append(f"| {tier} | {d['total']} | {d['correct']} | {a} |")
        lines.append("")
    else:
        lines += [
            f"> **Insufficient data:** {s3['non_sports_with_positions']}/{MIN_SAMPLE} "
            f"non-sports markets with elite positions. ELO validity conclusions deferred.",
            "",
        ]
        # Show partial results if any exist
        any_data = any(d["total"] for d in s3["tier_results"].values())
        if any_data:
            lines += ["**Partial (non-conclusive):**", ""]
            for tier, d in s3["tier_results"].items():
                if d["total"]:
                    lines.append(
                        f"- {tier}: {d['correct']}/{d['total']} "
                        f"({d['correct']/d['total']:.0%}) — below minimum sample"
                    )
            lines.append("")

        if s3["sports_excluded"] > 0:
            lines += [
                f"> Note: {s3['sports_excluded']} sports markets excluded per hard rules "
                f"(CLAUDE.md: 'no sports markets in any agent scope'). Elite traders are active "
                f"in sports markets but those cannot inform trading signal design.",
                "",
            ]

    lines += [
        "---",
        "",
        "## Step 4 — Strategy Registry Review",
        "",
        f"Strategies checked: **{s4['strategies_checked']}**",
        "",
    ]

    for strat in s4["all_strategies"]:
        flag = " **⚠ OVERDUE**" if strat["overdue"] else ""
        lines.append(
            f"- **{strat['name']}** `{strat['status']}` — "
            f"last revalidation: {strat['last_revalidation']}, "
            f"next due: {strat['next_revalidation_due']}"
            f"{flag}"
        )
        if strat["overdue"] and strat.get("overdue_reason"):
            lines.append(f"  - {strat['overdue_reason']}")

    lines.append("")

    if s4["overdue"]:
        lines += [
            f"Revalidation signals written for: **{', '.join(s['name'] for s in s4['overdue'])}**",
            "",
        ]
    else:
        lines += ["All strategies within revalidation schedule.", ""]

    lines += [
        "---",
        "",
        "## Step 5 — New Findings Written",
        "",
        f"New entries added to `brain/findings.json`: **{len(new_findings)}**",
        "",
    ]
    for f in new_findings:
        lines.append(f"- `{f['id']}` ({f['confidence']}) — {f['summary']}")
    if not new_findings:
        lines.append("No new findings this cycle (all finding IDs already present).")
    lines.append("")

    lines += [
        "---",
        "",
        "## Data Gaps and Insufficient Sample Notes",
        "",
    ]
    gaps = []
    if not s1["sufficient_data"]:
        gaps.append(
            f"- **Signal accuracy:** {s1['resolved_markets']}/{MIN_SAMPLE} resolved — "
            "deferred"
        )
    if not s2["directory_exists"]:
        gaps.append(
            "- **Pre-resolution:** Output directory absent — "
            "signal-agent pre-resolution scans have not run"
        )
    elif s2["signals_audited"] < MIN_SAMPLE:
        gaps.append(
            f"- **Pre-resolution:** {s2['signals_audited']}/{MIN_SAMPLE} signals — deferred"
        )
    if not s3["sufficient_data"]:
        gaps.append(
            f"- **ELO validity:** {s3['non_sports_with_positions']}/{MIN_SAMPLE} "
            "non-sports markets with elite positions — deferred"
        )
    lines += gaps if gaps else ["No data gaps — all steps had sufficient sample sizes."]
    lines.append("")

    lines += [
        "---",
        "",
        "## Phase 5 Integration Gate Progress",
        "",
        "| Gate | Requirement | Current Status |",
        "|------|------------|----------------|",
        f"| feedback-loop-agent weekly runs | 4+ | **{run_count}** "
        f"{'(this run is the first)' if run_count == 1 else 'run(s) complete'} |",
        "| findings.json HIGH-confidence entries | 3+ (≥20 samples each) | **0** |",
        "| Pre-resolution accuracy | ≥60% across 10+ markets | **50% across 4 markets — insufficient** |",
        "| RQ1.1 + RQ3.2 | Both passed | **Pending** |",
        "",
        "> No Phase 5 gates met. System remains in Phase 2 — First Light.",
        "",
        "---",
        "",
        "*Generated by feedback-loop-agent.*  "
        "*Next scheduled run: Monday 07:00 UTC.*",
    ]

    path.write_text("\n".join(lines))
    log(f"  Report written: {path}")
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log(f"Weekly run — {TODAY_STR}")
    log(f"DB: {DB_PATH}")
    log(f"Repo: {REPO_ROOT}")

    # Rule 6: read feedback.json before starting
    feedback = load_json(FEEDBACK_JSON)
    log(f"Feedback memory: {len(feedback.get('rejected', []))} rejected, "
        f"{len(feedback.get('approved', []))} approved")

    run_count = load_and_increment_run_count()

    conn = get_db_conn()
    try:
        s1 = step1_signal_accuracy(conn)
        s2 = step2_pre_resolution(conn)
        s3 = step3_elo_validity(conn)
        s4 = step4_strategy_review()

        reval_written = write_revalidation_signals(s4["overdue"])
        new_findings  = step5_write_findings(s1, s2, s3, s4, run_count)
        report_path   = write_report(s1, s2, s3, s4, new_findings, reval_written, run_count)
    finally:
        conn.close()

    # Build Telegram message
    resolved   = s3["markets_resolved_7d"]
    sig_acc    = (f"{s1['accuracy']:.0%}" if s1["sufficient_data"] and s1["accuracy"] is not None
                  else "insufficient data")
    tg_msg = (
        f"🔄 feedback-loop-agent weekly run complete\n"
        f"Markets reviewed: {resolved}\n"
        f"Signal accuracy: {sig_acc}\n"
        f"New findings: {len(new_findings)}\n"
        f"Full report: brain/agent-outputs/feedback-loop/{TODAY_STR}-weekly-audit.md"
    )
    send_telegram(tg_msg)

    log(f"Run complete — new findings: {len(new_findings)}, report: {report_path}")


if __name__ == "__main__":
    main()
