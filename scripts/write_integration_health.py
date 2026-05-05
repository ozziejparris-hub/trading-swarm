#!/usr/bin/env python3
"""
Write integration-health.json for trading-swarm agents.

Runs as the final step of first-repo's daily_maintenance.py.
Agents read this file at startup instead of connecting directly
to the DB for the Section 9 validation query — faster, no
timeout risk during the maintenance window.

Output: /home/parison/trading-swarm/brain/integration-health.json
"""

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("/home/parison/projects/first-repo/data/polymarket_tracker.db")
HEALTH_PATH = Path("/home/parison/trading-swarm/brain/integration-health.json")

# Schema version = date of the most recent schema-critical commit in first-repo.
# Updated manually when daily_maintenance.py, unified_elo_system.py,
# database.py, or update_research_exclusions.py changes.
SCHEMA_VERSION = "2026-04-30"


def get_last_maintenance_timestamp():
    """Return ISO8601 timestamp of the most recent successful maintenance run."""
    # Best proxy: mtime of resync_position_counts.py output or the DB itself.
    # We use the DB mtime as it is written to by every maintenance step.
    try:
        mtime = DB_PATH.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return None


def main():
    generated_at = datetime.now(tz=timezone.utc).isoformat()

    health = {
        "generated_at": generated_at,
        "clean_pool": None,
        "clean_markets": None,
        "wal_mode": None,
        "last_maintenance": get_last_maintenance_timestamp(),
        "schema_version": SCHEMA_VERSION,
        "contract_valid": False,
        "alerts": [],
    }

    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")

        row = conn.execute(
            "SELECT COUNT(*) FROM traders WHERE research_excluded = 0"
        ).fetchone()
        health["clean_pool"] = row[0] if row else 0

        row = conn.execute(
            """SELECT COUNT(*) FROM markets
               WHERE resolved = 1
                 AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)"""
        ).fetchone()
        health["clean_markets"] = row[0] if row else 0

        row = conn.execute(
            "SELECT journal_mode FROM pragma_journal_mode()"
        ).fetchone()
        health["wal_mode"] = row[0] if row else "unknown"

        conn.close()

    except Exception as e:
        health["alerts"].append(f"DB connection failed: {e}")
        print(f"ERROR: DB connection failed: {e}")
        _write(health)
        raise SystemExit(1)

    # Evaluate contract validity
    alerts = []
    if health["clean_pool"] is not None and health["clean_pool"] < 600:
        alerts.append(f"clean_pool={health['clean_pool']} is below 600 — research pool shrank unexpectedly")
    if health["clean_markets"] is not None and health["clean_markets"] < 11000:
        alerts.append(f"clean_markets={health['clean_markets']} is below 11000 — markets missing")
    if health["wal_mode"] != "wal":
        alerts.append(f"wal_mode={health['wal_mode']} — WAL disabled, risk of read contention")

    health["alerts"] = alerts
    health["contract_valid"] = len(alerts) == 0

    _write(health)

    print(f"integration-health.json written:")
    print(f"  clean_pool    = {health['clean_pool']}")
    print(f"  clean_markets = {health['clean_markets']}")
    print(f"  wal_mode      = {health['wal_mode']}")
    print(f"  contract_valid= {health['contract_valid']}")
    if alerts:
        for a in alerts:
            print(f"  ALERT: {a}")


def _write(health):
    HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_PATH, "w") as f:
        json.dump(health, f, indent=2)


if __name__ == "__main__":
    main()
