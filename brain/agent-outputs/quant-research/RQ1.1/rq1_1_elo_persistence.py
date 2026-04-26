"""
RQ1.1 — ELO Persistence Validation
Does a trader's ELO score in period T predict their Brier score in period T+1?

Pass criterion:  Pearson r < -0.25 (higher ELO = lower/better Brier)
Fail criterion:  r > -0.10
Inconclusive:    -0.25 <= r <= -0.10

Database: ~/projects/first-repo/data/polymarket_tracker.db (READ ONLY)
"""

# ── Required filters — 2026-04-26 data integrity audit ────────────────────────
# Every query joining traders / positions / markets must include:
#
#   JOIN key:        markets m ON m.market_id = t.market_id
#                    Never use condition_id — it misses 12,584 trades.
#
#   Trader filter:   tr.research_excluded = 0
#                    Excludes LP artefacts, thin-sample artefacts,
#                    wash/bot suspects, <20 resolved trades, ELO <= 300.
#
#   Timestamp filter: t.timestamp <= datetime('now')
#                    Excludes 37 future-dated trades (market expiry timestamps
#                    ingested as trade timestamps). N/A for positions-based
#                    queries — positions are already aggregated from filtered
#                    trades and carry no individual trade timestamp.
#
#   Resolution filter: m.resolved = 1
#                      AND m.winning_outcome NOT IN ('unknown', '')
#                      AND m.winning_outcome IS NOT NULL
#                    Excludes 497 markets with unknown resolution (4.5%).
#
# Source: reports/data_integrity_audit_20260426.md in first-repo
# ──────────────────────────────────────────────────────────────────────────────

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

try:
    from scipy import stats
    import numpy as np
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy", "numpy", "-q"])
    from scipy import stats
    import numpy as np

DB_PATH = Path.home() / "projects/first-repo/data/polymarket_tracker.db"
OUT_DIR = Path.home() / "trading-swarm/brain/agent-outputs/quant-research/RQ1.1"
OUT_JSON = OUT_DIR / "rq1_1_results.json"

PASS_THRESHOLD = -0.25
FAIL_THRESHOLD = -0.10
MIN_POSITIONS_PER_PERIOD = 20


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA query_only=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def get_period_split(conn: sqlite3.Connection) -> tuple[str, str, str]:
    """Return (p1_start, split_date, p2_end) for binary resolved markets."""
    row = conn.execute("""
        WITH ranked AS (
            SELECT resolution_date,
                   ROW_NUMBER() OVER (ORDER BY resolution_date) AS rn,
                   COUNT(*) OVER () AS total
            FROM markets
            WHERE winning_outcome IN ('Yes', 'No') AND resolved = 1
        )
        SELECT
            (SELECT MIN(resolution_date) FROM markets
             WHERE winning_outcome IN ('Yes','No') AND resolved=1) AS p1_start,
            resolution_date AS split_date,
            (SELECT MAX(resolution_date) FROM markets
             WHERE winning_outcome IN ('Yes','No') AND resolved=1) AS p2_end
        FROM ranked
        WHERE rn = total / 2
    """).fetchone()
    return row["p1_start"], row["split_date"], row["p2_end"]


def get_trader_elo(conn: sqlite3.Connection) -> dict[str, dict]:
    """Fetch comprehensive_elo and total_trades for research-eligible traders."""
    rows = conn.execute(
        "SELECT address, comprehensive_elo, total_trades FROM traders"
        " WHERE research_excluded = 0"
    ).fetchall()
    return {
        r["address"]: {
            "elo": r["comprehensive_elo"] or 1500.0,
            "total_trades": r["total_trades"] or 0,
        }
        for r in rows
    }


def compute_brier_per_trader(
    conn: sqlite3.Connection, split_date: str, period: int
) -> dict[str, dict]:
    """
    Compute per-trader Brier scores for a given period.

    Brier = mean((p_yes - actual_yes)^2) where:
      p_yes = entry_avg_price         if position.outcome = 'Yes'
      p_yes = 1 - entry_avg_price     if position.outcome = 'No'
      actual_yes = 1 if winning_outcome = 'Yes', else 0
    """
    if period == 1:
        date_filter = "m.resolution_date < :split"
    else:
        date_filter = "m.resolution_date >= :split"

    rows = conn.execute(
        f"""
        SELECT
            p.trader_address,
            p.outcome         AS pos_outcome,
            p.entry_avg_price AS entry_price,
            m.winning_outcome AS win_outcome
        FROM positions p
        JOIN markets m  ON m.market_id = p.market_id
        JOIN traders tr ON tr.address  = p.trader_address
        WHERE m.winning_outcome IN ('Yes', 'No')
          AND m.winning_outcome NOT IN ('unknown', '')
          AND m.winning_outcome IS NOT NULL
          AND m.resolved = 1
          AND p.outcome IN ('Yes', 'No')
          AND p.entry_avg_price IS NOT NULL
          AND p.entry_avg_price > 0
          AND p.entry_avg_price < 1
          AND tr.research_excluded = 0
          AND {date_filter}
        """,
        {"split": split_date},
    ).fetchall()

    trader_data: dict[str, list[float]] = {}
    for r in rows:
        addr = r["trader_address"]
        # Normalise to probability-of-YES space
        if r["pos_outcome"] == "Yes":
            p_yes = r["entry_price"]
        else:
            p_yes = 1.0 - r["entry_price"]
        actual_yes = 1.0 if r["win_outcome"] == "Yes" else 0.0
        brier_sq = (p_yes - actual_yes) ** 2
        trader_data.setdefault(addr, []).append(brier_sq)

    return {
        addr: {
            "brier": float(np.mean(sq_errors)),
            "n": len(sq_errors),
        }
        for addr, sq_errors in trader_data.items()
    }


def run_pearson(elos: list[float], briers: list[float]) -> tuple[float, float]:
    if len(elos) < 3:
        return float("nan"), float("nan")
    r, p = stats.pearsonr(elos, briers)
    return float(r), float(p)


def classify_group(total_trades: int) -> str:
    if total_trades < 50:
        return "A"
    if total_trades <= 500:
        return "B"
    return "C"


def verdict(r: float, n: int) -> str:
    if n < 5:
        return "INCONCLUSIVE"  # not enough data regardless of r
    if r < PASS_THRESHOLD:
        return "PASS"
    if r > FAIL_THRESHOLD:
        return "FAIL"
    return "INCONCLUSIVE"


def main():
    print("=" * 60)
    print("RQ1.1 — ELO Persistence Validation")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    conn = connect_readonly(DB_PATH)
    print(f"\n[DB] Connected (read-only): {DB_PATH}")

    # ── 1. Determine period split ──────────────────────────────────
    p1_start, split_date, p2_end = get_period_split(conn)
    print(f"\n[PERIODS]")
    print(f"  Period 1: {p1_start}  →  {split_date}")
    print(f"  Period 2: {split_date}  →  {p2_end}")

    # ── 2. Fetch ELO scores ────────────────────────────────────────
    trader_meta = get_trader_elo(conn)
    print(f"\n[ELO] Loaded metadata for {len(trader_meta):,} traders")

    # ── 3. Compute Brier scores per period ─────────────────────────
    print("\n[BRIER] Computing period-1 position counts...")
    p1_data = compute_brier_per_trader(conn, split_date, period=1)
    print(f"  → {len(p1_data):,} traders have ≥1 qualifying position in P1")

    print("[BRIER] Computing period-2 Brier scores...")
    p2_data = compute_brier_per_trader(conn, split_date, period=2)
    print(f"  → {len(p2_data):,} traders have ≥1 qualifying position in P2")

    # ── 4. Filter to traders with ≥20 qualifying in EACH period ────
    qualified = []
    for addr in set(p1_data) & set(p2_data):
        if (
            p1_data[addr]["n"] >= MIN_POSITIONS_PER_PERIOD
            and p2_data[addr]["n"] >= MIN_POSITIONS_PER_PERIOD
            and addr in trader_meta
        ):
            meta = trader_meta[addr]
            qualified.append(
                {
                    "address": addr,
                    "elo": meta["elo"],
                    "total_trades": meta["total_trades"],
                    "p1_n": p1_data[addr]["n"],
                    "p2_brier": p2_data[addr]["brier"],
                    "p2_n": p2_data[addr]["n"],
                    "group": classify_group(meta["total_trades"]),
                }
            )

    qualified.sort(key=lambda x: x["elo"], reverse=True)
    n_total = len(qualified)

    print(f"\n[FILTER] Traders with ≥{MIN_POSITIONS_PER_PERIOD} positions in EACH period: {n_total}")

    if n_total == 0:
        print("\nERROR: No traders meet the minimum position threshold. Exiting.")
        sys.exit(1)

    # ── 5. Print per-trader table ──────────────────────────────────
    print(f"\n{'Rank':<5} {'ELO':>8} {'P2 Brier':>10} {'P1_n':>6} {'P2_n':>6} "
          f"{'Trades':>8} {'Grp':>4}  {'Address'}")
    print("-" * 80)
    for i, t in enumerate(qualified, 1):
        print(
            f"{i:<5} {t['elo']:>8.1f} {t['p2_brier']:>10.5f} {t['p1_n']:>6} "
            f"{t['p2_n']:>6} {t['total_trades']:>8} {t['group']:>4}  {t['address']}"
        )

    # ── 6. Overall Pearson correlation ─────────────────────────────
    all_elos   = [t["elo"] for t in qualified]
    all_briers = [t["p2_brier"] for t in qualified]
    overall_r, overall_p = run_pearson(all_elos, all_briers)

    print(f"\n[OVERALL CORRELATION]")
    print(f"  n = {n_total}")
    print(f"  Pearson r = {overall_r:.4f}")
    print(f"  p-value   = {overall_p:.4f}")
    print(f"  Pass threshold: r < {PASS_THRESHOLD}")

    # ── 7. Group-stratified correlations ──────────────────────────
    groups = {"A": [], "B": [], "C": []}
    for t in qualified:
        groups[t["group"]].append(t)

    group_results = {}
    print(f"\n[STRATIFIED BY TRADE COUNT]")
    group_labels = {
        "A": "total_trades < 50",
        "B": "50 ≤ total_trades ≤ 500",
        "C": "total_trades > 500",
    }
    for grp in ("A", "B", "C"):
        members = groups[grp]
        n_g = len(members)
        if n_g >= 3:
            g_elos   = [m["elo"] for m in members]
            g_briers = [m["p2_brier"] for m in members]
            g_r, g_p = run_pearson(g_elos, g_briers)
        else:
            g_r, g_p = float("nan"), float("nan")
        group_results[grp] = {"correlation": g_r, "p_value": g_p, "n": n_g}
        print(
            f"  Group {grp} ({group_labels[grp]}): n={n_g:>3}  "
            f"r={g_r:>7.4f}  p={g_p:>7.4f}"
            + (" [insufficient data]" if n_g < 3 else "")
        )

    # ── 8. Verdict ────────────────────────────────────────────────
    v = verdict(overall_r, n_total)

    print(f"\n[VERDICT]  {v}")
    print(f"  r = {overall_r:.4f}  (pass if r < {PASS_THRESHOLD})")

    small_sample_warning = ""
    if n_total < 30:
        small_sample_warning = (
            f"WARNING: n={n_total} is below the 30-trade minimum for reliable inference. "
            "Statistical power is very low; treat results as preliminary only."
        )
        print(f"\n  ⚠  {small_sample_warning}")

    # ── 9. Write results JSON ──────────────────────────────────────
    results = {
        "rq": "RQ1.1",
        "description": "Does ELO in period T predict Brier score in period T+1?",
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_correlation": overall_r if not np.isnan(overall_r) else None,
        "p_value": overall_p if not np.isnan(overall_p) else None,
        "n_traders_qualified": n_total,
        "min_positions_per_period": MIN_POSITIONS_PER_PERIOD,
        "period_1_date_range": [p1_start, split_date],
        "period_2_date_range": [split_date, p2_end],
        "by_trade_count_group": {
            grp: {
                "correlation": v_["correlation"] if not np.isnan(v_["correlation"]) else None,
                "p_value": v_["p_value"] if not np.isnan(v_["p_value"]) else None,
                "n": v_["n"],
                "label": group_labels[grp],
            }
            for grp, v_ in group_results.items()
        },
        "verdict": v,
        "pass_criterion": f"Pearson r < {PASS_THRESHOLD} (negative because higher ELO = lower Brier)",
        "fail_criterion": f"Pearson r > {FAIL_THRESHOLD}",
        "notes": {
            "elo_source": "comprehensive_elo from traders table (built from full history)",
            "brier_normalisation": (
                "Prices normalised to YES-probability space: "
                "p_yes = entry_avg_price if bet=YES, else 1 - entry_avg_price. "
                "Brier = mean((p_yes - actual_yes)^2)."
            ),
            "period_split": "Chronological NTILE(2) on resolution_date of binary (Yes/No) resolved markets",
            "small_sample_warning": small_sample_warning or None,
            "qualified_traders": [
                {
                    "address": t["address"],
                    "elo": t["elo"],
                    "p2_brier": t["p2_brier"],
                    "p1_n": t["p1_n"],
                    "p2_n": t["p2_n"],
                    "total_trades": t["total_trades"],
                    "group": t["group"],
                }
                for t in qualified
            ],
        },
    }

    OUT_JSON.write_text(json.dumps(results, indent=2))
    print(f"\n[OUTPUT] Results written to {OUT_JSON}")
    print("\n" + "=" * 60)
    print("RQ1.1 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
