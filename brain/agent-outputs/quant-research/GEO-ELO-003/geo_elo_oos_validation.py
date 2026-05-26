"""
RQ-GEO-ELO-003: Out-of-sample geo_elo validation
--------------------------------------------------
TRAIN: geo/elections trades with timestamp < 2026-01-01
TEST:  resolved geo/elections markets from 2026-01-01 onward

Algorithm: market-implied probability ELO v2
  expected_score = price       (outcome_bet = 'Yes')
  expected_score = 1 - price  (outcome_bet = 'No')
  K = 32 (<20 geo trades at time), 24 (20-50), 16 (>50)
  starting ELO = 1500, min 5 qualifying trades
"""

import sqlite3
import json
from datetime import datetime, timezone
from collections import defaultdict

DB_PATH = "/home/parison/projects/first-repo/data/polymarket_tracker.db"
SIGNALS_PATH = "/home/parison/trading-swarm/brain/signals.json"
FINDINGS_PATH = "/home/parison/trading-swarm/brain/findings.json"


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def validate_contract(conn):
    row = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM traders WHERE research_excluded = 0) AS clean_pool,
            (SELECT COUNT(*) FROM markets WHERE resolved = 1
               AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)) AS clean_markets,
            (SELECT journal_mode FROM pragma_journal_mode()) AS wal_mode
    """).fetchone()
    assert row["clean_pool"] > 440, f"Contract violation: clean_pool={row['clean_pool']} < 440"
    assert row["clean_markets"] >= 11000, f"Contract violation: clean_markets={row['clean_markets']}"
    assert row["wal_mode"] == "wal", f"Contract violation: wal_mode={row['wal_mode']}"
    print(f"Contract validated: pool={row['clean_pool']}, markets={row['clean_markets']}, wal={row['wal_mode']}")


def add_oos_column(conn):
    existing = [r[1] for r in conn.execute("PRAGMA table_info(traders)").fetchall()]
    if "geo_elo_oos" not in existing:
        conn.execute("ALTER TABLE traders ADD COLUMN geo_elo_oos REAL")
        conn.commit()
        print("Added geo_elo_oos column to traders")
    else:
        print("geo_elo_oos column already exists")


def compute_oos_elo(conn):
    """Phase 1: compute geo_elo using only pre-2026 trades."""
    rows = conn.execute("""
        SELECT t.trader_address, t.outcome_bet, t.price, t.trade_result, t.timestamp
        FROM trades t
        JOIN markets m ON m.market_id = t.market_id
        WHERE t.market_category IN ('Geopolitics', 'Elections')
          AND t.trade_result IN ('won', 'lost')
          AND t.timestamp < '2026-01-01'
          AND t.timestamp <= datetime('now')
          AND m.resolved = 1
          AND m.winning_outcome NOT IN ('unknown', '')
          AND m.winning_outcome IS NOT NULL
          AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
        ORDER BY t.timestamp ASC
    """).fetchall()

    print(f"Loaded {len(rows):,} qualifying pre-2026 geo trades")

    elo = defaultdict(lambda: 1500.0)
    count = defaultdict(int)

    for row in rows:
        addr = row["trader_address"]
        n = count[addr]

        if n < 20:
            k = 32
        elif n <= 50:
            k = 24
        else:
            k = 16

        price = row["price"]
        outcome_bet = row["outcome_bet"]
        if outcome_bet == "Yes":
            expected = price
        else:
            expected = 1.0 - price

        actual = 1.0 if row["trade_result"] == "won" else 0.0

        elo[addr] = elo[addr] + k * (actual - expected)
        count[addr] += 1

    qualifying = {addr: elo[addr] for addr, n in count.items() if n >= 5}
    print(f"OOS ELO computed for {len(qualifying):,} traders with >= 5 qualifying trades")

    # Clear existing oos values then write new
    conn.execute("UPDATE traders SET geo_elo_oos = NULL")
    updates = [(v, k) for k, v in qualifying.items()]
    conn.executemany("UPDATE traders SET geo_elo_oos = ? WHERE address = ?", updates)
    conn.commit()
    print(f"Stored geo_elo_oos for {len(updates):,} traders")
    return qualifying, count


def measure_oos_accuracy(conn):
    """Phase 2: accuracy on resolved geo markets from 2026-01-01 onward."""

    # OOS test markets
    markets = conn.execute("""
        SELECT market_id, title, resolution_date, winning_outcome
        FROM markets
        WHERE category IN ('Geopolitics', 'Elections')
          AND resolved = 1
          AND (trade_gap_flag = 0 OR trade_gap_flag IS NULL)
          AND winning_outcome NOT IN ('unknown', '')
          AND winning_outcome IS NOT NULL
          AND resolution_date >= '2026-01-01'
        ORDER BY resolution_date
    """).fetchall()

    print(f"\nOOS test markets: {len(markets)}")
    for m in markets:
        print(f"  {m['resolution_date'][:10]}  {m['title'][:60]}  → {m['winning_outcome']}")

    # Trades by Pool C traders in OOS markets
    rows = conn.execute("""
        SELECT t.trader_address, t.market_id, t.outcome_bet, t.trade_result,
               tr.geo_elo_oos, tr.geo_directionality_score
        FROM trades t
        JOIN markets m ON m.market_id = t.market_id
        JOIN traders tr ON tr.address = t.trader_address
        WHERE t.market_category IN ('Geopolitics', 'Elections')
          AND t.trade_result IN ('won', 'lost')
          AND m.resolved = 1
          AND m.winning_outcome NOT IN ('unknown', '')
          AND m.winning_outcome IS NOT NULL
          AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
          AND m.resolution_date >= '2026-01-01'
          AND tr.geo_accuracy_pool = 1
          AND tr.geo_elo_oos IS NOT NULL
        ORDER BY t.timestamp
    """).fetchall()

    print(f"\nPool C trades in OOS markets (with geo_elo_oos): {len(rows):,}")

    def tier(elo):
        if elo >= 2175:
            return "legendary"
        elif elo >= 1800:
            return "elite"
        elif elo >= 1500:
            return "qualified"
        else:
            return "below_qualified"

    tiers = ["legendary", "elite", "qualified", "below_qualified"]
    correct = defaultdict(int)
    total = defaultdict(int)
    dir_correct = defaultdict(int)
    dir_total = defaultdict(int)

    for row in rows:
        oos_elo = row["geo_elo_oos"]
        t = tier(oos_elo)
        won = row["trade_result"] == "won"
        correct[t] += int(won)
        total[t] += 1
        correct["all"] += int(won)
        total["all"] += 1

        if row["geo_directionality_score"] is not None and row["geo_directionality_score"] >= 0.7:
            dir_correct[t] += int(won)
            dir_total[t] += 1
            dir_correct["all"] += int(won)
            dir_total["all"] += 1

    print("\nOOS accuracy by geo_elo_oos tier (Pool C):")
    results = {}
    for t in tiers + ["all"]:
        n = total[t]
        acc = correct[t] / n if n > 0 else None
        results[t] = {"n": n, "accuracy": round(acc, 4) if acc is not None else None}
        print(f"  {t:18s}: {acc:.1%} (n={n})" if acc is not None else f"  {t:18s}: no data")

    print("\nOOS accuracy by geo_elo_oos tier (dir >= 0.7):")
    dir_results = {}
    for t in tiers + ["all"]:
        n = dir_total[t]
        acc = dir_correct[t] / n if n > 0 else None
        dir_results[t + "_dir"] = {"n": n, "accuracy": round(acc, 4) if acc is not None else None}
        print(f"  {t:18s}: {acc:.1%} (n={n})" if acc is not None else f"  {t:18s}: no data")

    return results, dir_results, [dict(m) for m in markets]


def get_oos_distribution(conn):
    row = conn.execute("""
        SELECT
            COUNT(*) FILTER (WHERE geo_elo_oos IS NOT NULL) AS total,
            AVG(geo_elo_oos) as avg_elo,
            MAX(geo_elo_oos) as max_elo,
            MIN(geo_elo_oos) as min_elo,
            COUNT(*) FILTER (WHERE geo_elo_oos >= 2175) AS legendary,
            COUNT(*) FILTER (WHERE geo_elo_oos >= 1800 AND geo_elo_oos < 2175) AS elite,
            COUNT(*) FILTER (WHERE geo_elo_oos >= 1500 AND geo_elo_oos < 1800) AS qualified,
            COUNT(*) FILTER (WHERE geo_elo_oos < 1500) AS below_qualified
        FROM traders
        WHERE geo_accuracy_pool = 1
    """).fetchone()
    return dict(row)


def main():
    conn = connect()

    # Section 9 contract validation
    validate_contract(conn)

    # Phase 1: OOS ELO
    print("\n=== PHASE 1: OOS ELO COMPUTATION ===")
    add_oos_column(conn)
    qualifying, counts = compute_oos_elo(conn)

    # Distribution among Pool C traders
    dist = get_oos_distribution(conn)
    print(f"\nOOS ELO distribution (Pool C, geo_accuracy_pool=1):")
    print(f"  Total with oos ELO: {dist['total']}")
    print(f"  LEGENDARY (>=2175): {dist['legendary']}")
    print(f"  ELITE (1800-2175):  {dist['elite']}")
    print(f"  QUALIFIED (1500-1800): {dist['qualified']}")
    print(f"  BELOW (<1500):      {dist['below_qualified']}")

    # Phase 2: OOS accuracy
    print("\n=== PHASE 2: OOS ACCURACY MEASUREMENT ===")
    acc_results, dir_results, test_markets = measure_oos_accuracy(conn)

    # Phase 3: comparison
    print("\n=== PHASE 3: IN-SAMPLE vs OUT-OF-SAMPLE ===")
    in_sample = {"legendary": 0.6698, "elite": 0.695, "qualified": 0.7368}
    print(f"{'Tier':18s}  {'In-sample':>10}  {'OOS':>10}  {'Delta':>8}")
    print("-" * 55)
    for t in ["legendary", "elite", "qualified"]:
        oos = acc_results[t]["accuracy"]
        insample = in_sample[t]
        delta = (oos - insample) if oos is not None else None
        oos_str = f"{oos:.1%}" if oos is not None else "N/A"
        delta_str = f"{delta:+.1%}" if delta is not None else "N/A"
        print(f"  {t:16s}  {insample:.1%}       {oos_str}       {delta_str}")

    failure_condition = acc_results["legendary"]["accuracy"]
    if failure_condition is not None:
        passed = failure_condition >= 0.55
        print(f"\nFailure condition (LEGENDARY OOS < 55%): {'PASSED' if passed else 'FAILED'} ({failure_condition:.1%})")
    else:
        print("\nFailure condition: N/A (no legendary OOS trades)")

    conn.close()
    return acc_results, dir_results, dist, test_markets, qualifying, counts


if __name__ == "__main__":
    acc_results, dir_results, dist, test_markets, qualifying, counts = main()
    print("\nDone.")
