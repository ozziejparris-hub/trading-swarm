#!/bin/bash
# ─────────────────────────────────────────────
# run_ci.sh
# Master CI script. Runs all checks in sequence.
# Orchestrator calls this after every agent task.
#
# Usage:
#   ./ci/run_ci.sh                          # lint + tests only
#   ./ci/run_ci.sh <backtest_output.json>   # lint + tests + backtest
#
# Returns 0 (all pass) or 1 (any failure)
# ─────────────────────────────────────────────

BASE_DIR="/home/parison/trading-swarm"
BACKTEST_FILE=$1
FAILURES=0

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Trading Swarm CI Pipeline        ║"
echo "║     $(date '+%Y-%m-%d %H:%M:%S')           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Step 1: Lint ─────────────────────────────
echo "Step 1/3: Lint"
bash "$BASE_DIR/ci/lint.sh"
if [ $? -ne 0 ]; then
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ── Step 2: Tests ────────────────────────────
echo "Step 2/3: Tests"
bash "$BASE_DIR/ci/run_tests.sh"
if [ $? -ne 0 ]; then
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ── Step 3: Backtest validation (if provided) ─
echo "Step 3/3: Backtest validation"
if [ -z "$BACKTEST_FILE" ]; then
    echo "⚠️  No backtest file provided — skipping"
else
    python3 "$BASE_DIR/ci/validate_backtest.py" "$BACKTEST_FILE"
    if [ $? -ne 0 ]; then
        FAILURES=$((FAILURES + 1))
    fi
fi
echo ""

# ── Final result ─────────────────────────────
echo "╔══════════════════════════════════════╗"
if [ $FAILURES -eq 0 ]; then
    echo "║         ✅ CI PIPELINE PASSED        ║"
else
    echo "║    ❌ CI PIPELINE FAILED ($FAILURES checks)   ║"
fi
echo "╚══════════════════════════════════════╝"
echo ""

exit $FAILURES
