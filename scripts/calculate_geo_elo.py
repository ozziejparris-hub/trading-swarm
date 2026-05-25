#!/usr/bin/env python3
"""
RQ-GEO-ELO-001 — Phase 1+2: geo_elo and geo_directionality_score computation.

Adds geo_elo (K=32 ELO restricted to Geopolitics+Elections resolved trades)
and geo_directionality_score (position asymmetry in geo markets) to traders table.

Pre-registration: brain/strategy-notes/rq-geo-elo-preregistration-2026-05-25.md
Contract: brain/integration-contract.md v1.3
"""

import sqlite3
import sys
from collections import defaultdict

DB_PATH = "/home/parison/projects/first-repo/data/polymarket_tracker.db"

K_FACTOR = 32
STARTING_ELO = 1500
OPPONENT_ELO = 1500  # Neutral market baseline
MIN_GEO_TRADES = 5
MIN_GEO_POSITIONS = 3


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def validate(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
          (SELECT COUNT(*) FROM traders WHERE research_excluded = 0) AS clean_pool,
          (SELECT COUNT(*) FROM markets WHERE resolved = 1
             AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)) AS clean_markets,
          (SELECT journal_mode FROM pragma_journal_mode()) AS wal_mode
    """)
    row = cur.fetchone()
    clean_pool, clean_markets, wal_mode = row
    print(f"[VALIDATE] clean_pool={clean_pool}, clean_markets={clean_markets}, wal_mode={wal_mode}")
    if clean_pool < 440:
        print(f"[ABORT] clean_pool {clean_pool} < 440 — contract violation", file=sys.stderr)
        sys.exit(1)
    if clean_markets < 11000:
        print(f"[ABORT] clean_markets {clean_markets} < 11000 — contract violation", file=sys.stderr)
        sys.exit(1)
    if wal_mode != "wal":
        print(f"[ABORT] wal_mode={wal_mode} — WAL not active", file=sys.stderr)
        sys.exit(1)
    print("[VALIDATE] OK")


def add_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(traders)")
    existing = {row[1] for row in cur.fetchall()}

    if "geo_elo" not in existing:
        cur.execute("ALTER TABLE traders ADD COLUMN geo_elo REAL DEFAULT NULL")
        print("[SCHEMA] Added geo_elo")
    else:
        print("[SCHEMA] geo_elo already exists")

    if "geo_resolved_trades_count" not in existing:
        cur.execute("ALTER TABLE traders ADD COLUMN geo_resolved_trades_count INTEGER DEFAULT 0")
        print("[SCHEMA] Added geo_resolved_trades_count")
    else:
        print("[SCHEMA] geo_resolved_trades_count already exists")

    if "geo_directionality_score" not in existing:
        cur.execute("ALTER TABLE traders ADD COLUMN geo_directionality_score REAL DEFAULT NULL")
        print("[SCHEMA] Added geo_directionality_score")
    else:
        print("[SCHEMA] geo_directionality_score already exists")

    conn.commit()


def expected_score(trader_elo, opponent_elo=OPPONENT_ELO):
    return 1.0 / (1.0 + 10.0 ** ((opponent_elo - trader_elo) / 400.0))


def compute_geo_elo(conn):
    print("\n[PHASE 1] Loading geo/elections trades...")
    cur = conn.cursor()
    cur.execute("""
        SELECT t.trader_address, t.timestamp, t.trade_result
        FROM trades t
        JOIN markets m ON m.market_id = t.market_id
        WHERE m.category IN ('Geopolitics', 'Elections')
          AND m.resolved = 1
          AND m.winning_outcome NOT IN ('unknown', '')
          AND m.winning_outcome IS NOT NULL
          AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
          AND t.timestamp <= datetime('now')
          AND t.trade_result IN ('won', 'lost')
        ORDER BY t.trader_address, t.timestamp
    """)
    rows = cur.fetchall()
    print(f"[PHASE 1] Loaded {len(rows):,} valid geo trades")

    # Group by trader
    trader_trades = defaultdict(list)
    for address, ts, result in rows:
        trader_trades[address].append((ts, result))

    # Compute ELO for traders with >= MIN_GEO_TRADES trades
    updates = []
    skipped = 0
    for address, trades in trader_trades.items():
        if len(trades) < MIN_GEO_TRADES:
            skipped += 1
            continue
        elo = float(STARTING_ELO)
        for _ts, result in trades:  # already ordered by timestamp from SQL
            actual = 1.0 if result == "won" else 0.0
            exp = expected_score(elo)
            elo += K_FACTOR * (actual - exp)
        updates.append((elo, len(trades), address))

    print(f"[PHASE 1] Traders with geo_elo: {len(updates):,} (skipped {skipped:,} with < {MIN_GEO_TRADES} trades)")

    if len(updates) < 50:
        print(f"[ABORT] Only {len(updates)} traders got geo_elo — below 50 minimum, data too sparse", file=sys.stderr)
        sys.exit(1)
    print(f"[PHASE 1] Note: pre-registration estimated >1,000 traders; actual={len(updates)} — still meaningful (avg {len(rows)//max(len(updates),1)} trades/trader)")

    # Reset then write
    cur.execute("UPDATE traders SET geo_elo = NULL, geo_resolved_trades_count = 0")
    cur.executemany(
        "UPDATE traders SET geo_elo = ?, geo_resolved_trades_count = ? WHERE address = ?",
        updates
    )
    conn.commit()
    print(f"[PHASE 1] Written {len(updates):,} geo_elo values")
    return {addr for _, _, addr in updates}


def compute_directionality(conn, traders_with_geo_elo):
    print("\n[PHASE 2] Loading geo/elections positions...")
    cur = conn.cursor()
    cur.execute("""
        SELECT p.trader_address, p.market_id, p.outcome, p.entry_total_cost
        FROM positions p
        JOIN markets m ON m.market_id = p.market_id
        WHERE m.category IN ('Geopolitics', 'Elections')
          AND p.trader_address IN (
              SELECT address FROM traders WHERE geo_elo IS NOT NULL
          )
    """)
    rows = cur.fetchall()
    print(f"[PHASE 2] Loaded {len(rows):,} geo position rows")

    # Build per-trader, per-market capital totals
    # Structure: trader -> market -> {yes_cap, no_cap}
    trader_market_caps = defaultdict(lambda: defaultdict(lambda: {"yes": 0.0, "no": 0.0}))
    trader_position_counts = defaultdict(int)

    for address, market_id, outcome, cost in rows:
        cost = cost or 0.0
        if outcome == "Yes":
            trader_market_caps[address][market_id]["yes"] += cost
        else:
            trader_market_caps[address][market_id]["no"] += cost
        trader_position_counts[address] += 1

    # Compute directionality per trader
    updates = []
    skipped = 0
    for address, markets in trader_market_caps.items():
        if trader_position_counts[address] < MIN_GEO_POSITIONS:
            skipped += 1
            continue
        market_dirs = []
        for market_id, caps in markets.items():
            yes_cap = caps["yes"]
            no_cap = caps["no"]
            total = yes_cap + no_cap
            if total > 0:
                market_dirs.append(abs(yes_cap - no_cap) / total)
        if market_dirs:
            avg_dir = sum(market_dirs) / len(market_dirs)
            updates.append((avg_dir, address))

    print(f"[PHASE 2] Traders with directionality score: {len(updates):,} (skipped {skipped:,} with < {MIN_GEO_POSITIONS} positions)")

    cur.execute("UPDATE traders SET geo_directionality_score = NULL")
    cur.executemany(
        "UPDATE traders SET geo_directionality_score = ? WHERE address = ?",
        updates
    )
    conn.commit()
    print(f"[PHASE 2] Written {len(updates):,} geo_directionality_score values")
    return len(updates)


def report(conn):
    print("\n[PHASE 3] Tier distribution report...")
    cur = conn.cursor()
    cur.execute("""
        SELECT
          COUNT(*) as traders_with_geo_elo,
          COUNT(CASE WHEN geo_elo >= 2175 THEN 1 END) as geo_legendary,
          COUNT(CASE WHEN geo_elo >= 1800 AND geo_elo < 2175 THEN 1 END) as geo_elite,
          COUNT(CASE WHEN geo_elo >= 1500 AND geo_elo < 1800 THEN 1 END) as geo_qualified,
          COUNT(*) FILTER (WHERE geo_directionality_score IS NOT NULL) as with_directionality,
          AVG(geo_directionality_score) as avg_directionality,
          COUNT(*) FILTER (WHERE geo_directionality_score >= 0.7) as highly_directional
        FROM traders WHERE geo_elo IS NOT NULL
    """)
    row = cur.fetchone()
    (traders_with_geo_elo, geo_legendary, geo_elite, geo_qualified,
     with_directionality, avg_directionality, highly_directional) = row

    print(f"  traders_with_geo_elo : {traders_with_geo_elo:,}")
    print(f"  geo_legendary (≥2175): {geo_legendary:,}")
    print(f"  geo_elite (1800-2175): {geo_elite:,}")
    print(f"  geo_qualified (1500-1800): {geo_qualified:,}")
    print(f"  with_directionality  : {with_directionality:,}")
    avg_dir_str = f"{avg_directionality:.4f}" if avg_directionality is not None else "None"
    print(f"  avg_directionality   : {avg_dir_str}")
    print(f"  highly_directional (≥0.7): {highly_directional:,}")

    return {
        "traders_with_geo_elo": traders_with_geo_elo,
        "geo_legendary": geo_legendary,
        "geo_elite": geo_elite,
        "geo_qualified": geo_qualified,
        "with_directionality": with_directionality,
        "avg_directionality": avg_directionality,
        "highly_directional": highly_directional,
    }


if __name__ == "__main__":
    import json, os, datetime

    conn = connect()
    validate(conn)
    add_columns(conn)
    traders_with_geo_elo = compute_geo_elo(conn)
    compute_directionality(conn, traders_with_geo_elo)
    stats = report(conn)
    conn.close()

    # Write handoff file
    handoff_dir = "/home/parison/trading-swarm/brain/agent-outputs/handoffs"
    os.makedirs(handoff_dir, exist_ok=True)
    handoff_path = os.path.join(handoff_dir, "geo-elo-phase1-2026-05-25.json")

    handoff = {
        "generated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "RQ-GEO-ELO-001",
        "phase": "Phase 1+2 complete — geo_elo and geo_directionality_score calculated",
        "tier_distribution": {
            "traders_with_geo_elo": stats["traders_with_geo_elo"],
            "geo_legendary": stats["geo_legendary"],
            "geo_elite": stats["geo_elite"],
            "geo_qualified": stats["geo_qualified"],
        },
        "directionality": {
            "with_directionality_score": stats["with_directionality"],
            "avg_directionality": stats["avg_directionality"],
            "highly_directional_gte_0_7": stats["highly_directional"],
        },
        "phase3_instructions": (
            "Run accuracy check using geo_elo tiers on resolved geopolitics markets. "
            "Use accuracy_pool=1 for Pool A validation. "
            "Compare LEGENDARY/ELITE/QUALIFIED accuracy under geo_elo vs comprehensive_elo "
            "baseline (LEGENDARY 46%, QUALIFIED 65%). "
            "Also filter to geo_directionality_score >= 0.7 and report accuracy for that subset."
        ),
        "algorithm": {
            "k_factor": K_FACTOR,
            "starting_elo": STARTING_ELO,
            "opponent_elo": OPPONENT_ELO,
            "min_trades_for_geo_elo": MIN_GEO_TRADES,
            "min_positions_for_directionality": MIN_GEO_POSITIONS,
            "categories": ["Geopolitics", "Elections"],
            "join_key": "trades.market_id = markets.market_id",
        },
        "baseline_for_comparison": {
            "comprehensive_elo_legendary_accuracy": 0.46,
            "comprehensive_elo_elite_accuracy": 0.49,
            "comprehensive_elo_qualified_accuracy": 0.65,
            "source": "feedback-loop-agent Run #8, 2026-05-25",
        },
    }

    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)

    print(f"\n[HANDOFF] Written to {handoff_path}")
    print("\n[DONE] Phase 1+2 complete.")
