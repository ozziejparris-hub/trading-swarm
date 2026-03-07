#!/bin/bash
# ─────────────────────────────────────────────
# run_tests.sh
# Runs pytest on all test files in the project.
# Returns 0 (pass) or 1 (fail).
# ─────────────────────────────────────────────

BASE_DIR="/home/parison/trading-swarm"
TESTS_DIR="$BASE_DIR/tests"

echo "══════════════════════════════════════"
echo "  CI — Test Suite"
echo "  $(date)"
echo "══════════════════════════════════════"

# Create tests directory if it doesn't exist yet
mkdir -p "$TESTS_DIR"

# Check if any tests exist
if [ -z "$(ls -A $TESTS_DIR/*.py 2>/dev/null)" ]; then
    echo "⚠️  No tests found in $TESTS_DIR"
    echo "   Agents should write tests as they build."
    echo "   Passing for now — add tests as system grows."
    exit 0
fi

# Run pytest
pytest "$TESTS_DIR" \
    --tb=short \
    --quiet \
    -v

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ TESTS PASSED"
else
    echo ""
    echo "❌ TESTS FAILED"
fi

exit $EXIT_CODE
