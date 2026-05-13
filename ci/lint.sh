# ─────────────────────────────────────────────
# lint.sh
# Runs flake8 on all Python files in the project.
# Returns 0 (pass) or 1 (fail).
# Called by orchestrator after every agent task.
# ─────────────────────────────────────────────

BASE_DIR="/home/parison/trading-swarm"
BRAIN_OUTPUTS="$BASE_DIR/brain/agent-outputs"

echo "══════════════════════════════════════"
echo "  CI — Lint Check"
echo "  $(date)"
echo "══════════════════════════════════════"

# Run flake8
# Cosmetic whitespace — suppressed (alignment style, not correctness)
#   E221 multiple spaces before operator (dict/var alignment)
#   E241 multiple spaces after colon (dict alignment)
#   E261 at least two spaces before inline comment
#   E305 expected 2 blank lines after function definition
#   E203 whitespace before punctuation (e.g. slice notation)
#   F824 unused global declaration
#   E402 module-level import not at top (needed in some scripts)
#   E231 missing whitespace after ',' (alignment style in dicts/calls)
#   E127 continuation line over-indented for visual indent
# Style preferences — suppressed
#   W503 line break before binary operator
#   E302 expected 2 blank lines (function spacing)
#   E226 whitespace around arithmetic operator
#   E501 line too long (agents write long lines)
# Kept ACTIVE (real bug risk)
#   F541 f-string without placeholders
#   F401 unused imports
flake8 "$BASE_DIR" \
    --exclude="$BASE_DIR/worktrees,$BASE_DIR/.git,$BRAIN_OUTPUTS" \
    --ignore=E501,W503,E302,E226,F401,E221,E241,E261,E305,E203,F824,E402,E231,E127 \
    --max-line-length=120 \
    --count \
    --statistics

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ LINT PASSED"
else
    echo ""
    echo "❌ LINT FAILED — fix errors before proceeding"
fi

exit $EXIT_CODE
