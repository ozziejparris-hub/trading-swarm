#!/usr/bin/env python3
"""
validate_backtest.py
Checks that a backtest output file meets minimum quality thresholds.
Called by orchestrator after backtest-agent completes a task.

Usage:
    python3 ci/validate_backtest.py <path_to_backtest_output.json>

Returns:
    0 = passed all thresholds
    1 = failed one or more thresholds
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────
# THRESHOLDS
# Adjust these as your system matures
# ─────────────────────────────────────────────

THRESHOLDS = {
    "sharpe_ratio": 1.0,        # Minimum raw Sharpe
    "dsr": 0.95,                # Minimum Deflated Sharpe Ratio
    "pbo": 0.1,                 # Maximum Probability of Backtest Overfitting
    "brier_score": 0.20,        # Maximum Brier score (lower is better)
    "min_trades": 30,           # Minimum trades for statistical validity
    "max_drawdown": -0.40,      # Maximum acceptable drawdown
    "min_win_rate": 0.40,       # Minimum win rate
    "max_transaction_cost": 0.02  # Polymarket fee assumption
}
# ─────────────────────────────────────────────
# VALIDATOR
# ─────────────────────────────────────────────

def validate(filepath):
    print("══════════════════════════════════════")
    print("  CI — Backtest Validator")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("══════════════════════════════════════")
    print(f"  File: {filepath}")
    print()

    # Load the backtest output
    path = Path(filepath)
    if not path.exists():
        print(f"❌ FAIL: File not found: {filepath}")
        return 1

    try:
        with open(path) as f:
            result = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON: {e}")
        return 1

    failures = []
    warnings = []

    # ── Check required fields exist ──────────
    required_fields = [
        "strategy", "sharpe_ratio", "total_trades",
        "max_drawdown", "win_rate", "verdict"
    ]
    for field in required_fields:
        if field not in result:
            failures.append(f"Missing required field: {field}")

    if failures:
        for f in failures:
            print(f"❌ {f}")
        return 1

    # ── Print what we found ──────────────────
    print(f"  Strategy:     {result.get('strategy', 'unknown')}")
    print(f"  Sharpe ratio: {result.get('sharpe_ratio', 'N/A')}")
    print(f"  Brier score:  {result.get('brier_score', 'N/A')}")
    print(f"  Total trades: {result.get('total_trades', 'N/A')}")
    print(f"  Win rate:     {result.get('win_rate', 'N/A')}")
    print(f"  Max drawdown: {result.get('max_drawdown', 'N/A')}")
    print(f"  Verdict:      {result.get('verdict', 'N/A')}")
    print()

    # ── Run threshold checks ─────────────────

    # Sharpe ratio
    sharpe = result.get("sharpe_ratio")
    if sharpe is not None:
        if sharpe < THRESHOLDS["sharpe_ratio"]:
            failures.append(
                f"Sharpe ratio {sharpe:.2f} below minimum "
                f"{THRESHOLDS['sharpe_ratio']}"
            )
        else:
            print(f"✅ Sharpe ratio: {sharpe:.2f} "
                  f"(minimum {THRESHOLDS['sharpe_ratio']})")

    # DSR check
    dsr = result.get("dsr")
    if dsr is not None:
        if dsr < THRESHOLDS["dsr"]:
            failures.append(
                f"DSR {dsr:.3f} below minimum "
                f"{THRESHOLDS['dsr']} — strategy may be overfit"
            )
        else:
            print(f"✅ DSR: {dsr:.3f} "
                  f"(minimum {THRESHOLDS['dsr']})")
    else:
        warnings.append(
            "DSR not calculated — log number of "
            "strategies tested and recalculate"
        )

    # PBO check
    pbo = result.get("pbo")
    if pbo is not None:
        if pbo > THRESHOLDS["pbo"]:
            failures.append(
                f"PBO {pbo:.3f} above maximum "
                f"{THRESHOLDS['pbo']} — strategy is likely overfit"
            )
        else:
            print(f"✅ PBO: {pbo:.3f} "
                  f"(maximum {THRESHOLDS['pbo']})")
    else:
        warnings.append(
            "PBO not calculated — "
            "run combinatorial purged cross-validation"
        )

    # Brier score (only if present — not all strategies have this)
    brier = result.get("brier_score")
    if brier is not None:
        if brier > THRESHOLDS["brier_score"]:
            failures.append(
                f"Brier score {brier:.3f} above maximum "
                f"{THRESHOLDS['brier_score']} (lower is better)"
            )
        else:
            print(f"✅ Brier score: {brier:.3f} "
                  f"(maximum {THRESHOLDS['brier_score']})")

    # Transaction costs check
    tx_costs = result.get("transaction_costs_assumed")
    if tx_costs is None or tx_costs < THRESHOLDS["max_transaction_cost"]:
        warnings.append(
            "Transaction costs not included or below 2% — "
            "Polymarket charges ~2% per trade"
        )
    else:
        print(f"✅ Transaction costs: {tx_costs:.1%} included")

    # 7 sins check
    sins = result.get("sins_checked", [])
    if len(sins) < 7:
        warnings.append(
            f"Only {len(sins)}/7 backtesting sins checked. "
            "Complete all 7 before approval."
        )
    else:
        print("✅ All 7 backtesting sins checked")

    # Brier score (only if present — not all strategies have this)
    brier = result.get("brier_score")
    if brier is not None:
        if brier > THRESHOLDS["brier_score"]:
            failures.append(
                f"Brier score {brier:.3f} above maximum "
                f"{THRESHOLDS['brier_score']} (lower is better)"
            )
        else:
            print(f"✅ Brier score: {brier:.3f} "
                  f"(maximum {THRESHOLDS['brier_score']})")

    # Minimum trades
    trades = result.get("total_trades", 0)
    if trades < THRESHOLDS["min_trades"]:
        failures.append(
            f"Only {trades} trades — minimum "
            f"{THRESHOLDS['min_trades']} required for validity"
        )
    else:
        print(f"✅ Trade count: {trades} "
              f"(minimum {THRESHOLDS['min_trades']})")

    # Max drawdown
    drawdown = result.get("max_drawdown")
    if drawdown is not None:
        if drawdown < THRESHOLDS["max_drawdown"]:
            failures.append(
                f"Max drawdown {drawdown:.1%} exceeds limit "
                f"{THRESHOLDS['max_drawdown']:.1%}"
            )
        else:
            print(f"✅ Max drawdown: {drawdown:.1%} "
                  f"(limit {THRESHOLDS['max_drawdown']:.1%})")

    # Win rate
    win_rate = result.get("win_rate")
    if win_rate is not None:
        if win_rate < THRESHOLDS["min_win_rate"]:
            warnings.append(
                f"Win rate {win_rate:.1%} below "
                f"{THRESHOLDS['min_win_rate']:.1%} — worth reviewing"
            )
        else:
            print(f"✅ Win rate: {win_rate:.1%} "
                  f"(minimum {THRESHOLDS['min_win_rate']:.1%})")

    # Agent verdict must match our checks
    agent_verdict = result.get("verdict", "").lower()
    if agent_verdict == "pass" and failures:
        warnings.append(
            "Agent reported PASS but CI found failures — "
            "agent self-report overridden by CI"
        )
    elif agent_verdict == "fail" and not failures:
        warnings.append(
            "Agent reported FAIL but CI found no issues — "
            "review manually"
        )

    # ── Print results ────────────────────────
    print()

    if warnings:
        print("⚠️  Warnings:")
        for w in warnings:
            print(f"   {w}")
        print()

    if failures:
        print("❌ BACKTEST FAILED:")
        for f in failures:
            print(f"   {f}")
        print()
        print("This strategy does not meet minimum thresholds.")
        print("Do not deploy. Return to quant-research-agent.")
        return 1

    print("✅ BACKTEST PASSED — all thresholds met")
    print("Ready for orchestrator review.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ci/validate_backtest.py <backtest_output.json>")
        sys.exit(1)

    exit_code = validate(sys.argv[1])
    sys.exit(exit_code)
