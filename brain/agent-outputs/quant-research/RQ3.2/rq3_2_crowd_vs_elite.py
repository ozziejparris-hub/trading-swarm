"""
RQ3.2 — Crowd vs Elite Divergence  (v2)

Research question: when ELO-weighted LEGENDARY consensus (ELO >= 2175) differs
from market price by more than 5 percentage points, does the legendary consensus
predict the outcome more accurately than the market price?

Also runs a no-divergence-filter second pass across all markets with >= 2
legendary traders, to test whether they lead or track the crowd.

Pass criterion : legendary correct on >55% of qualifying markets
Fail criterion : legendary correct on <50%
Inconclusive   : 50-55%
"""

# ── Required filters — 2026-04-26 data integrity audit ────────────────────────
# Every query joining traders / trades / markets must include:
#
#   JOIN key:         markets m ON m.market_id = t.market_id
#                     Never use condition_id — it misses 12,584 trades.
#
#   Trader filter:    tr.research_excluded = 0
#                     Excludes LP artefacts, thin-sample artefacts,
#                     wash/bot suspects, <20 resolved trades, ELO <= 300.
#
#   Timestamp filter: t.timestamp <= datetime('now')
#                     Excludes 37 future-dated trades.
#
#   Resolution filter: m.resolved = 1
#                      AND m.winning_outcome NOT IN ('unknown', '')
#                      AND m.winning_outcome IS NOT NULL
#                     Excludes 497 markets with unknown resolution (4.5%).
#
#   Deduplication:    when multiple market_ids share the same title, keep
#                     only the one with the most elite trader activity.
#
# Source: reports/data_integrity_audit_20260426.md in first-repo
# ──────────────────────────────────────────────────────────────────────────────

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/home/parison/trading-swarm')
from scripts.market_filter import should_include_market

DB_PATH     = '/home/parison/projects/first-repo/data/polymarket_tracker.db'
OUTPUT_DIR  = Path(__file__).parent
OUTPUT_JSON = OUTPUT_DIR / 'rq3_2_results.json'

MIN_ELO_LEGENDARY   = 2175   # Change 1: legendary-only threshold
MIN_ELO_BROAD_ELITE = 1800   # kept for comparison
MIN_LEGENDARY       = 2       # Change 2: minimum distinct legendary traders
MIN_DIVERGENCE      = 0.05    # Change 3: 5pp threshold
PASS_THRESHOLD      = 0.55
FAIL_THRESHOLD      = 0.50


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------

def load_data(conn: sqlite3.Connection) -> dict:
    """
    Return a dict keyed by market_id.
    Loads ALL traders (any ELO) for binary resolved markets.
    Aggregates multiple BUY trades for (trader, market, outcome) into one
    volume-weighted average price.
    """
    sql = """
        SELECT
            t.trader_address,
            t.market_id,
            m.title,
            m.winning_outcome,
            t.outcome         AS bet_outcome,
            SUM(t.shares * t.price) / SUM(t.shares) AS avg_price,
            SUM(t.shares)                            AS total_shares,
            tr.comprehensive_elo                     AS elo
        FROM trades t
        JOIN traders tr ON tr.address   = t.trader_address
        JOIN markets m  ON m.market_id  = t.market_id
        WHERE t.side          = 'BUY'
          AND t.timestamp     <= datetime('now')
          AND m.resolved      = 1
          AND m.winning_outcome IN ('Yes', 'No')
          AND m.winning_outcome NOT IN ('unknown', '')
          AND m.winning_outcome IS NOT NULL
          AND t.outcome        IN ('Yes', 'No')
          AND tr.comprehensive_elo IS NOT NULL
          AND tr.research_excluded = 0
        GROUP BY t.trader_address, t.market_id, t.outcome
        ORDER BY t.market_id
    """
    cur = conn.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    markets: dict = {}
    for row in rows:
        r = dict(zip(cols, row))
        mid = r['market_id']
        if mid not in markets:
            markets[mid] = {
                'title':           r['title'],
                'winning_outcome': r['winning_outcome'],
                'positions':       [],
            }
        markets[mid]['positions'].append({
            'trader':      r['trader_address'],
            'elo':         float(r['elo']),
            'bet_outcome': r['bet_outcome'],
            'avg_price':   float(r['avg_price']),
            'shares':      float(r['total_shares']),
        })
    return markets


# ---------------------------------------------------------------------------
# 2. Per-market analysis
# ---------------------------------------------------------------------------

def collapse_to_implied(positions: list) -> list[dict]:
    """
    Collapse (trader, market) records — possibly with both YES and NO bets —
    into one implied-prob-YES per trader via share-weighted averaging.
    implied_prob = avg_price if bet=Yes, else 1 - avg_price if bet=No.
    """
    trader_num   = defaultdict(float)
    trader_denom = defaultdict(float)
    trader_elo   = {}

    for pos in positions:
        addr = pos['trader']
        ip   = pos['avg_price'] if pos['bet_outcome'] == 'Yes' else 1.0 - pos['avg_price']
        w    = pos['shares']
        trader_num[addr]   += w * ip
        trader_denom[addr] += w
        trader_elo[addr]    = pos['elo']

    result = []
    for addr, denom in trader_denom.items():
        if denom > 0:
            result.append({
                'trader':       addr,
                'elo':          trader_elo[addr],
                'implied_prob': trader_num[addr] / denom,
            })
    return result


def elo_weighted_consensus(traders: list[dict]) -> float:
    """ELO-weighted mean implied-prob-YES for a list of trader dicts."""
    elo_sum = sum(t['elo'] for t in traders)
    if elo_sum == 0:
        return sum(t['implied_prob'] for t in traders) / len(traders)
    return sum(t['elo'] * t['implied_prob'] for t in traders) / elo_sum


def analyse_market(market: dict, require_divergence: bool = True) -> dict | None:
    """
    Returns a per-market analysis dict, or None if gates not met.

    Gates (when require_divergence=True):
      - >= MIN_LEGENDARY distinct legendary traders
      - abs(legendary_consensus - market_price) >= MIN_DIVERGENCE

    When require_divergence=False, only the legendary count gate applies
    (used for the second pass).

    Change 4: computes BOTH legendary and broad-elite consensus.
    """
    positions = market['positions']
    winning   = market['winning_outcome']
    actual    = 1.0 if winning == 'Yes' else 0.0

    traders_impl = collapse_to_implied(positions)
    if not traders_impl:
        return None

    legendary   = [t for t in traders_impl if t['elo'] >= MIN_ELO_LEGENDARY]
    broad_elite = [t for t in traders_impl if t['elo'] >= MIN_ELO_BROAD_ELITE]

    if len(legendary) < MIN_LEGENDARY:
        return None

    leg_consensus   = elo_weighted_consensus(legendary)
    broad_consensus = elo_weighted_consensus(broad_elite) if len(broad_elite) >= 2 else None

    # Unweighted market price = simple average across ALL traders
    market_price = sum(t['implied_prob'] for t in traders_impl) / len(traders_impl)

    divergence = abs(leg_consensus - market_price)

    if require_divergence and divergence < MIN_DIVERGENCE:
        return None

    # Accuracy vs actual outcome
    leg_err    = abs(leg_consensus - actual)
    market_err = abs(market_price   - actual)
    leg_correct    = leg_err < market_err
    leg_brier      = (leg_consensus - actual) ** 2
    market_brier   = (market_price   - actual) ** 2

    broad_correct = None
    broad_brier   = None
    if broad_consensus is not None:
        broad_err     = abs(broad_consensus - actual)
        broad_correct = broad_err < market_err
        broad_brier   = (broad_consensus - actual) ** 2

    # Divergence band (anchored at 5pp threshold)
    if divergence < 0.10:
        band = '5_10pp'
    elif divergence < 0.20:
        band = '10_20pp'
    else:
        band = 'over_20pp'

    # Direction
    if leg_consensus > 0.5 and market_price <= 0.5:
        direction = 'legendary_yes_market_no'
    elif leg_consensus <= 0.5 and market_price > 0.5:
        direction = 'legendary_no_market_yes'
    else:
        direction = 'same_side'

    return {
        'market_id':        market.get('market_id', '?'),
        'title':            market['title'],
        'winning_outcome':  winning,
        'actual':           actual,
        'leg_consensus':    leg_consensus,
        'broad_consensus':  broad_consensus,
        'market_price':     market_price,
        'divergence':       divergence,
        'leg_correct':      leg_correct,
        'broad_correct':    broad_correct,
        'leg_brier':        leg_brier,
        'broad_brier':      broad_brier,
        'market_brier':     market_brier,
        'n_legendary':      len(legendary),
        'n_broad_elite':    len(broad_elite),
        'n_total':          len(traders_impl),
        'band':             band,
        'direction':        direction,
    }


# ---------------------------------------------------------------------------
# 3. Aggregate helpers
# ---------------------------------------------------------------------------

def summarise(results: list[dict], label: str) -> dict:
    n = len(results)
    if n == 0:
        return {'n': 0}
    n_leg_correct    = sum(1 for r in results if r['leg_correct'])
    n_market_correct = sum(
        1 for r in results
        if abs(r['market_price'] - r['actual']) < abs(r['leg_consensus'] - r['actual'])
    )
    avg_leg_brier    = sum(r['leg_brier']    for r in results) / n
    avg_market_brier = sum(r['market_brier'] for r in results) / n

    leg_acc    = n_leg_correct    / n
    market_acc = n_market_correct / n

    if leg_acc > PASS_THRESHOLD:
        verdict = 'PASS'
    elif leg_acc < FAIL_THRESHOLD:
        verdict = 'FAIL'
    else:
        verdict = 'INCONCLUSIVE'

    print(f"\n{'─'*60}")
    print(f"{label}")
    print(f"{'─'*60}")
    print(f"  n markets:              {n}")
    print(f"  Legendary accuracy:     {leg_acc:.1%}  ({n_leg_correct}/{n})")
    print(f"  Market accuracy:        {market_acc:.1%}  ({n_market_correct}/{n}  market beats legendary)")
    print(f"  Legendary avg Brier:    {avg_leg_brier:.4f}")
    print(f"  Market avg Brier:       {avg_market_brier:.4f}")
    print(f"  Brier Δ (mkt−leg):      {avg_market_brier - avg_leg_brier:+.4f}  (pos = legendary better)")
    print(f"  Verdict:                {verdict}")

    return {
        'n': n,
        'leg_accuracy': round(leg_acc, 4),
        'market_accuracy': round(market_acc, 4),
        'avg_leg_brier': round(avg_leg_brier, 4),
        'avg_market_brier': round(avg_market_brier, 4),
        'verdict': verdict,
    }


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("RQ3.2 — Crowd vs Elite Divergence  (v2 — Legendary tier)")
    print("=" * 60)
    print(f"  Legendary threshold:   ELO >= {MIN_ELO_LEGENDARY}")
    print(f"  Broad elite threshold: ELO >= {MIN_ELO_BROAD_ELITE}")
    print(f"  Min legendary traders: {MIN_LEGENDARY}")
    print(f"  Divergence threshold:  {MIN_DIVERGENCE:.0%}")
    print()

    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA query_only=ON;")

    print("Loading trades from DB...")
    raw_markets = load_data(conn)
    conn.close()

    print(f"  Binary resolved markets (raw):  {len(raw_markets)}")
    for mid, m in raw_markets.items():
        m['market_id'] = mid

    # Deduplicate by title — when multiple market_ids share the same title
    # (split condition_ids), keep only the one with the most elite trader
    # activity (ELO >= MIN_ELO_BROAD_ELITE positions).
    title_best: dict = {}
    for mid, m in raw_markets.items():
        title  = m['title']
        n_elite = sum(1 for p in m['positions'] if p['elo'] >= MIN_ELO_BROAD_ELITE)
        if title not in title_best or n_elite > title_best[title][1]:
            title_best[title] = (mid, n_elite)
    raw_markets = {mid: raw_markets[mid] for _, (mid, _) in title_best.items()}
    print(f"  After title deduplication:      {len(raw_markets)}")

    filtered = {mid: m for mid, m in raw_markets.items()
                if should_include_market(m['title'])}
    print(f"  After market filter:            {len(filtered)}")
    print()

    # -----------------------------------------------------------------------
    # PASS A — divergence-filtered main analysis
    # -----------------------------------------------------------------------
    results_div: list[dict] = []
    skipped_count = skipped_div = 0

    for mid, market in filtered.items():
        res = analyse_market(market, require_divergence=True)
        if res is None:
            traders_impl = collapse_to_implied(market['positions'])
            n_leg = sum(1 for t in traders_impl if t['elo'] >= MIN_ELO_LEGENDARY)
            if n_leg < MIN_LEGENDARY:
                skipped_count += 1
            else:
                skipped_div += 1
        else:
            results_div.append(res)

    print("PASS A — divergence-filtered (>=5pp)")
    print(f"  Skipped (< {MIN_LEGENDARY} legendary traders): {skipped_count}")
    print(f"  Skipped (divergence < {MIN_DIVERGENCE:.0%}):      {skipped_div}")
    print(f"  Qualifying markets:             {len(results_div)}")

    # -----------------------------------------------------------------------
    # PASS B — no divergence filter (all markets with >= 2 legendary traders)
    # -----------------------------------------------------------------------
    results_all: list[dict] = []
    for mid, market in filtered.items():
        res = analyse_market(market, require_divergence=False)
        if res is not None:
            results_all.append(res)

    print(f"\nPASS B — no divergence filter")
    print(f"  Markets with >= {MIN_LEGENDARY} legendary traders: {len(results_all)}")

    # -----------------------------------------------------------------------
    # Full per-market printout — Change 5
    # -----------------------------------------------------------------------
    def print_market_table(results: list[dict], heading: str) -> None:
        print(f"\n{'═'*72}")
        print(f"  {heading}  (n={len(results)})")
        print(f"{'═'*72}")
        if not results:
            print("  (no markets)")
            return
        hdr = (f"  {'✓/✗':3} {'div':>5} {'leg':>6} {'broad':>6} "
               f"{'mkt':>6} {'act':>4} {'n_leg':>5}  title")
        print(hdr)
        print(f"  {'-'*68}")
        for r in sorted(results, key=lambda x: x['divergence'], reverse=True):
            tick  = '✓' if r['leg_correct'] else '✗'
            broad = f"{r['broad_consensus']:.2f}" if r['broad_consensus'] is not None else '  -- '
            act   = 'YES' if r['actual'] else 'NO '
            print(f"  [{tick}] {r['divergence']:>5.2f} {r['leg_consensus']:>6.2f} "
                  f"{broad:>6} {r['market_price']:>6.2f} {act:>4} "
                  f"{r['n_legendary']:>5}  {r['title'][:52]}")

    print_market_table(results_div,
        f"PASS A — with divergence filter (>={MIN_DIVERGENCE:.0%})")
    print_market_table(results_all,
        f"PASS B — all markets with >={MIN_LEGENDARY} legendary traders (no divergence filter)")

    # -----------------------------------------------------------------------
    # Aggregate summaries
    # -----------------------------------------------------------------------
    sum_div = summarise(results_div, "PASS A SUMMARY — divergence-filtered")
    sum_all = summarise(results_all, "PASS B SUMMARY — no divergence filter")

    # By divergence band (Pass A)
    print("\nPASS A — BY DIVERGENCE BAND:")
    bands = ['5_10pp', '10_20pp', 'over_20pp']
    by_band = {}
    for band in bands:
        subset = [r for r in results_div if r['band'] == band]
        n = len(subset)
        acc = sum(1 for r in subset if r['leg_correct']) / n if n else 0.0
        by_band[band] = {'n': n, 'legendary_accuracy': round(acc, 4)}
        label = {'5_10pp': ' 5-10pp', '10_20pp': '10-20pp', 'over_20pp': ' >20pp'}[band]
        print(f"  {label}: n={n:3d}, legendary accuracy={acc:.1%}")

    # By direction (Pass A)
    print("\nPASS A — BY DIRECTION:")
    directions = ['legendary_yes_market_no', 'legendary_no_market_yes', 'same_side']
    by_dir = {}
    for d in directions:
        subset = [r for r in results_div if r['direction'] == d]
        n = len(subset)
        acc = sum(1 for r in subset if r['leg_correct']) / n if n else 0.0
        by_dir[d] = {'n': n, 'legendary_accuracy': round(acc, 4)}
        if n:
            label = {
                'legendary_yes_market_no': 'Legendary YES / Market NO (backing underdog)',
                'legendary_no_market_yes': 'Legendary NO  / Market YES (fading crowd)',
                'same_side':               'Same direction (magnitude divergence only)',
            }[d]
            print(f"  {label}: n={n}, accuracy={acc:.1%}")

    # -----------------------------------------------------------------------
    # Write JSON
    # -----------------------------------------------------------------------
    output = {
        # New fields (Change 6 / spec)
        'legendary_threshold':                  MIN_ELO_LEGENDARY,
        'broad_elite_threshold':                MIN_ELO_BROAD_ELITE,
        'legendary_n_qualifying':               sum_div['n'],
        'legendary_accuracy_pct':               sum_div.get('leg_accuracy', 0.0),
        'legendary_brier':                      sum_div.get('avg_leg_brier', 0.0),
        'market_brier_on_legendary_markets':    sum_div.get('avg_market_brier', 0.0),
        'no_divergence_filter': {
            'n_markets':          sum_all['n'],
            'legendary_accuracy': sum_all.get('leg_accuracy', 0.0),
            'market_accuracy':    sum_all.get('market_accuracy', 0.0),
        },
        # Retained fields
        'min_divergence_threshold': MIN_DIVERGENCE,
        'min_legendary_traders':    MIN_LEGENDARY,
        'by_divergence_band':       by_band,
        'by_direction': {
            'legendary_yes_market_no': by_dir.get('legendary_yes_market_no',
                                                   {'n': 0, 'legendary_accuracy': 0.0}),
            'legendary_no_market_yes': by_dir.get('legendary_no_market_yes',
                                                   {'n': 0, 'legendary_accuracy': 0.0}),
        },
        'verdict':         sum_div.get('verdict', 'INCONCLUSIVE'),
        'pass_criterion':  'Legendary correct >55% of qualifying markets',
    }

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to: {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
