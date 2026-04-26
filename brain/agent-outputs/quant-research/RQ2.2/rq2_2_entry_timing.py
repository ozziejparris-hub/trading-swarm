"""
RQ2.2: Do legendary traders show entry timing advantage?

When a legendary trader enters a directional position, does the market
price subsequently move in their direction over the following 7 days?
"""

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/parison/trading-swarm')
from scripts.market_filter import should_include_market

DB_PATH = '/home/parison/projects/first-repo/data/polymarket_tracker.db'
OUTPUT_PATH = Path(__file__).parent / 'rq2_2_results.json'

ELO_THRESHOLD = 2175
TOP_TIER_ELO = 3000
DIRECTION_THRESHOLD = 0.80
MIN_POST_ENTRY_TRADES = 3
POST_ENTRY_WINDOW_DAYS = 7


def connect_readonly(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA query_only=ON;')
    conn.row_factory = sqlite3.Row
    return conn


def load_legendary_trader_market_pairs(conn: sqlite3.Connection) -> list[dict]:
    """
    Step 1: For each legendary trader × resolved market pair, compute
    directional bias, entry price, and first entry timestamp.
    """
    sql = """
        SELECT
            t.trader_address,
            t.market_id,
            m.title          AS market_title,
            tr.comprehensive_elo,
            t.outcome,
            t.shares,
            t.price,
            t.timestamp
        FROM trades t
        JOIN traders tr ON t.trader_address = tr.address
        JOIN markets m  ON m.market_id = t.market_id
        WHERE tr.comprehensive_elo > :elo_threshold
          AND tr.research_excluded = 0
          AND m.resolved = 1
          AND t.timestamp <= datetime('now')
        ORDER BY t.trader_address, t.market_id, t.timestamp
    """
    rows = conn.execute(sql, {'elo_threshold': ELO_THRESHOLD}).fetchall()
    print(f"  Raw rows from DB: {len(rows):,}")

    # Group by (trader_address, market_id)
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        groups[(row['trader_address'], row['market_id'])].append(row)

    print(f"  Trader-market pairs before filters: {len(groups):,}")

    pairs = []
    n_market_filtered = 0
    n_bidirectional = 0

    for (trader_addr, market_id), trades in groups.items():
        market_title = trades[0]['market_title']
        elo_score = trades[0]['comprehensive_elo']

        # Market filter
        if not should_include_market(market_title):
            n_market_filtered += 1
            continue

        # Capital-weighted directional bias
        yes_capital = sum(
            r['shares'] * r['price']
            for r in trades
            if r['outcome'] and r['outcome'].strip().lower() in ('yes',)
        )
        no_capital = sum(
            r['shares'] * r['price']
            for r in trades
            if r['outcome'] and r['outcome'].strip().lower() in ('no',)
        )
        total_capital = yes_capital + no_capital
        if total_capital <= 0:
            n_bidirectional += 1
            continue

        yes_frac = yes_capital / total_capital
        no_frac = no_capital / total_capital

        if yes_frac > DIRECTION_THRESHOLD:
            direction = 'YES'
            dir_trades = [r for r in trades if r['outcome'] and r['outcome'].strip().lower() == 'yes']
        elif no_frac > DIRECTION_THRESHOLD:
            direction = 'NO'
            dir_trades = [r for r in trades if r['outcome'] and r['outcome'].strip().lower() == 'no']
        else:
            n_bidirectional += 1
            continue

        if not dir_trades:
            n_bidirectional += 1
            continue

        # Volume-weighted entry price on directional side
        total_shares = sum(r['shares'] for r in dir_trades)
        if total_shares <= 0:
            n_bidirectional += 1
            continue
        entry_price = sum(r['shares'] * r['price'] for r in dir_trades) / total_shares

        # First entry timestamp on directional side
        first_entry_ts = min(r['timestamp'] for r in dir_trades)

        pairs.append({
            'trader_address': trader_addr,
            'market_id': market_id,
            'market_title': market_title,
            'elo_score': elo_score,
            'direction': direction,
            'entry_price': entry_price,
            'first_entry_ts': first_entry_ts,
        })

    print(f"  Market-filtered out: {n_market_filtered:,}")
    print(f"  Bidirectional/LP skipped: {n_bidirectional:,}")
    print(f"  Qualifying directional pairs: {len(pairs):,}")
    return pairs


def get_post_entry_price(
    conn: sqlite3.Connection,
    market_id: str,
    first_entry_ts: str,
    direction: str,
) -> tuple[float | None, int]:
    """
    Step 2: Average price of all trades in the market over the 7 days
    after first_entry_ts, from ANY trader.
    Returns (avg_price, trade_count).
    """
    outcome_col = 'Yes' if direction == 'YES' else 'No'
    sql = """
        SELECT AVG(price) AS avg_price_7d,
               COUNT(*)   AS trade_count_7d
        FROM trades
        WHERE market_id = :market_id
          AND timestamp > :ts_start
          AND timestamp <= datetime(:ts_start, :window)
          AND outcome = :outcome
    """
    row = conn.execute(sql, {
        'market_id': market_id,
        'ts_start': first_entry_ts,
        'window': f'+{POST_ENTRY_WINDOW_DAYS} days',
        'outcome': outcome_col,
    }).fetchone()

    if row is None or row['avg_price_7d'] is None:
        return None, 0
    return row['avg_price_7d'], row['trade_count_7d']


def analyse(pairs: list[dict], conn: sqlite3.Connection) -> dict:
    """Steps 2–4: Compute price movement per pair, aggregate results."""
    movements = []
    n_insufficient_data = 0

    print(f"\nStep 2/3: Fetching post-entry prices for {len(pairs):,} pairs...")
    for i, pair in enumerate(pairs):
        if i % 50 == 0 and i > 0:
            print(f"  ... processed {i}/{len(pairs)}")

        avg_7d, count_7d = get_post_entry_price(
            conn,
            pair['market_id'],
            pair['first_entry_ts'],
            pair['direction'],
        )

        if avg_7d is None or count_7d < MIN_POST_ENTRY_TRADES:
            n_insufficient_data += 1
            continue

        multiplier = 1.0 if pair['direction'] == 'YES' else -1.0
        price_movement = (avg_7d - pair['entry_price']) * multiplier

        movements.append({
            **pair,
            'avg_price_7d': avg_7d,
            'trade_count_7d': count_7d,
            'price_movement_pp': price_movement,
            'positive': price_movement > 0,
        })

    print(f"  Insufficient post-entry data: {n_insufficient_data:,}")
    print(f"  Final qualifying pairs: {len(movements):,}")

    n = len(movements)
    if n == 0:
        return _empty_result(len(pairs), len(pairs) - n_insufficient_data, n)

    n_positive = sum(1 for m in movements if m['positive'])
    pct_positive = n_positive / n * 100
    avg_movement = sum(m['price_movement_pp'] for m in movements) / n

    # By ELO tier
    top = [m for m in movements if m['elo_score'] > TOP_TIER_ELO]
    mid = [m for m in movements if ELO_THRESHOLD < m['elo_score'] <= TOP_TIER_ELO]

    def tier_stats(group):
        if not group:
            return {'n': 0, 'pct_positive': None, 'avg_movement_pp': None}
        np_ = sum(1 for x in group if x['positive'])
        return {
            'n': len(group),
            'pct_positive': round(np_ / len(group) * 100, 2),
            'avg_movement_pp': round(sum(x['price_movement_pp'] for x in group) / len(group), 4),
        }

    # By direction
    yes_group = [m for m in movements if m['direction'] == 'YES']
    no_group  = [m for m in movements if m['direction'] == 'NO']

    def dir_stats(group):
        if not group:
            return {'n': 0, 'pct_positive': None}
        np_ = sum(1 for x in group if x['positive'])
        return {'n': len(group), 'pct_positive': round(np_ / len(group) * 100, 2)}

    verdict = _verdict(pct_positive, avg_movement)

    return {
        'n_qualifying': n,
        'n_directional_filtered': len(pairs),
        'n_sufficient_post_entry_data': n,
        'pct_positive_movement': round(pct_positive, 2),
        'avg_price_movement_pp': round(avg_movement, 4),
        'by_elo_tier': {
            'top_3000': tier_stats(top),
            'mid_2175_3000': tier_stats(mid),
        },
        'by_direction': {
            'YES': dir_stats(yes_group),
            'NO':  dir_stats(no_group),
        },
        'verdict': verdict,
        'pass_criterion': '>60% positive movement AND avg_movement > 2pp',
    }


def _verdict(pct_positive: float, avg_movement: float) -> str:
    passes_pct = pct_positive > 60
    passes_avg = avg_movement > 0.02  # 2 percentage points
    if passes_pct and passes_avg:
        return 'PASS'
    if not passes_pct and avg_movement < 0:
        return 'FAIL'
    return 'INCONCLUSIVE'


def _empty_result(n_directional, n_data, n_final) -> dict:
    return {
        'n_qualifying': 0,
        'n_directional_filtered': n_directional,
        'n_sufficient_post_entry_data': 0,
        'pct_positive_movement': None,
        'avg_price_movement_pp': None,
        'by_elo_tier': {
            'top_3000': {'n': 0, 'pct_positive': None, 'avg_movement_pp': None},
            'mid_2175_3000': {'n': 0, 'pct_positive': None, 'avg_movement_pp': None},
        },
        'by_direction': {
            'YES': {'n': 0, 'pct_positive': None},
            'NO':  {'n': 0, 'pct_positive': None},
        },
        'verdict': 'INCONCLUSIVE',
        'pass_criterion': '>60% positive movement AND avg_movement > 2pp',
    }


def print_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print("RQ2.2 RESULTS: Entry Timing Advantage")
    print("=" * 60)
    print(f"  Directional pairs found:        {results['n_directional_filtered']:,}")
    print(f"  Pairs with sufficient data:     {results['n_qualifying']:,}")
    print(f"  % positive price movement:      {results['pct_positive_movement']}%")
    print(f"  Avg price movement (pp):        {results['avg_price_movement_pp']}")
    print()
    print("  By ELO tier:")
    for tier, stats in results['by_elo_tier'].items():
        if stats['n'] > 0:
            print(f"    {tier:20s}: n={stats['n']:4d}  "
                  f"pct_pos={stats['pct_positive']}%  "
                  f"avg_mvmt={stats['avg_movement_pp']} pp")
    print()
    print("  By direction:")
    for dir_, stats in results['by_direction'].items():
        if stats['n'] > 0:
            print(f"    {dir_:6s}: n={stats['n']:4d}  pct_pos={stats['pct_positive']}%")
    print()
    print(f"  Pass criterion: {results['pass_criterion']}")
    print(f"  VERDICT: {results['verdict']}")
    print("=" * 60)


def main():
    print(f"RQ2.2 — Entry Timing Advantage  [{datetime.now().isoformat()}]")
    print(f"DB: {DB_PATH}")
    print(f"ELO threshold: >{ELO_THRESHOLD}  |  Direction threshold: {DIRECTION_THRESHOLD:.0%}")
    print(f"Post-entry window: {POST_ENTRY_WINDOW_DAYS}d  |  Min trades: {MIN_POST_ENTRY_TRADES}")
    print()

    conn = connect_readonly(DB_PATH)
    try:
        print("Step 1: Loading legendary directional positions...")
        pairs = load_legendary_trader_market_pairs(conn)

        results = analyse(pairs, conn)
    finally:
        conn.close()

    print_summary(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
