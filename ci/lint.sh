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
# E501 = line too long (ignored, agents write long lines)
# W503 = line break before binary operator (style preference)
flake8 "$BASE_DIR" \
    --exclude="$BASE_DIR/worktrees,$BASE_DIR/.git,$BRAIN_OUTPUTS" \
    --ignore=E501,W503,E302,E226,F401 \
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
