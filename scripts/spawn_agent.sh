#!/bin/bash
# ─────────────────────────────────────────────
# spawn_agent.sh
# Creates a git worktree and spawns an agent
# in its own tmux session with the correct model.
#
# Usage:
#   ./scripts/spawn_agent.sh <task_id> <agent_type> <tier> <"task description">
#
# Tiers:
#   1 = local ollama (monitoring/simple)
#   2 = qwen-coder (standard coding)
#   3 = claude-sonnet (complex coding)
#   4 = claude-opus (architecture/review)
#
# Example:
#   ./scripts/spawn_agent.sh elo-brier-001 quant-research 3 "Calculate Brier scores for ELO predictions across all resolved markets"
# ─────────────────────────────────────────────

set -e  # Exit on any error

# ── Arguments ──────────────────────────────
TASK_ID=$1
AGENT_TYPE=$2
TIER=${3:-3}          # Default to Sonnet if not specified
TASK_DESC=$4

# ── Validate arguments ──────────────────────
if [ -z "$TASK_ID" ] || [ -z "$AGENT_TYPE" ] || [ -z "$TASK_DESC" ]; then
    echo "ERROR: Missing required arguments"
    echo "Usage: $0 <task_id> <agent_type> <tier> <description>"
    exit 1
fi

# ── Configuration ───────────────────────────
BASE_DIR="/home/parison/trading-swarm"
WORKTREES_DIR="$BASE_DIR/worktrees"
TEMPLATE_FILE="$BASE_DIR/orchestrator/task_templates/$AGENT_TYPE.md"
REGISTRY_FILE="$BASE_DIR/orchestrator/agent_registry.json"
BRAIN_DIR="$BASE_DIR/brain"
SESSION_NAME="$AGENT_TYPE-$TASK_ID"
BRANCH_NAME="feat/$TASK_ID"
WORKTREE_PATH="$WORKTREES_DIR/$TASK_ID"
LOG_FILE="$BASE_DIR/logs/agent_logs/$TASK_ID.log"

# ── Select model based on tier ───────────────
case $TIER in
    1)
        MODEL_CMD="ollama run mistral"
        MODEL_NAME="mistral (local)"
        ;;
    2)
        MODEL_CMD="ollama run qwen2.5-coder"
        MODEL_NAME="qwen2.5-coder (local)"
        ;;
    3)
        MODEL_CMD="claude --model claude-sonnet-4-5 --dangerously-skip-permissions -p"
        MODEL_NAME="claude-sonnet"
        ;;
    4)
        MODEL_CMD="claude --model claude-opus-4-5 --dangerously-skip-permissions -p"
        MODEL_NAME="claude-opus"
        ;;
    *)
        echo "ERROR: Invalid tier $TIER (must be 1-4)"
        exit 1
        ;;
esac

echo "──────────────────────────────────────"
echo "Spawning agent: $SESSION_NAME"
echo "Model tier $TIER: $MODEL_NAME"
echo "Task: $TASK_DESC"
echo "──────────────────────────────────────"

# ── Validate template exists ─────────────────
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "ERROR: Template not found: $TEMPLATE_FILE"
    exit 1
fi

# ── Check session not already running ────────
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "ERROR: Session $SESSION_NAME already exists"
    echo "Kill it first: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

# ── Read template and inject task description ─
TEMPLATE=$(cat "$TEMPLATE_FILE")
FULL_PROMPT="${TEMPLATE/\{TASK_DESCRIPTION\}/$TASK_DESC}"

# ── Read current brain context ────────────────
PRIORITIES=$(cat "$BRAIN_DIR/priorities.md" 2>/dev/null || echo "No priorities set")

# ── Build complete agent prompt ───────────────
AGENT_PROMPT="$FULL_PROMPT

## Current System Priorities
$PRIORITIES

## Task ID
$TASK_ID

## Started At
$(date -u +%Y-%m-%dT%H:%M:%SZ)
"

# ── Save prompt to log ────────────────────────
mkdir -p "$(dirname $LOG_FILE)"
echo "=== Agent Prompt ===" > "$LOG_FILE"
echo "$AGENT_PROMPT" >> "$LOG_FILE"
echo "=== Agent Output ===" >> "$LOG_FILE"

# ── Create git worktree (for Claude tiers) ────
if [ "$TIER" -ge 3 ]; then
    echo "Creating git worktree: $BRANCH_NAME"
    mkdir -p "$WORKTREES_DIR"

    # Check if worktree already exists
    if [ -d "$WORKTREE_PATH" ]; then
        echo "Worktree already exists at $WORKTREE_PATH"
    else
        git -C "$BASE_DIR" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" 2>/dev/null || \
        git -C "$BASE_DIR" worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    fi
    WORKING_DIR="$WORKTREE_PATH"
else
    # Local models work in base dir
    WORKING_DIR="$BASE_DIR"
fi

# ── Spawn tmux session ────────────────────────
echo "Spawning tmux session: $SESSION_NAME"

tmux new-session -d \
    -s "$SESSION_NAME" \
    -c "$WORKING_DIR" \
    -x 220 -y 50

# ── Run the agent inside the session ─────────
if [ "$TIER" -ge 3 ]; then
    # Claude Code: pipe prompt in, log output
    tmux send-keys -t "$SESSION_NAME" \
        "$MODEL_CMD \"$AGENT_PROMPT\" 2>&1 | tee -a $LOG_FILE" \
        Enter
else
    # Ollama: simpler invocation
    tmux send-keys -t "$SESSION_NAME" \
        "echo '$AGENT_PROMPT' | $MODEL_CMD 2>&1 | tee -a $LOG_FILE" \
        Enter
fi

# ── Register task in registry ─────────────────
python3 - <<EOF
import json
from datetime import datetime
from pathlib import Path

registry_file = Path("$REGISTRY_FILE")
with open(registry_file) as f:
    registry = json.load(f)

registry["active_tasks"].append({
    "id": "$TASK_ID",
    "agent": "$AGENT_TYPE",
    "description": "$TASK_DESC",
    "branch": "$BRANCH_NAME",
    "tmux_session": "$SESSION_NAME",
    "model": "$MODEL_NAME",
    "tier": $TIER,
    "worktree": "$WORKTREE_PATH",
    "log": "$LOG_FILE",
    "started_at": datetime.utcnow().isoformat(),
    "status": "running",
    "retries": 0,
    "pr": None,
    "verified": False
})

with open(registry_file, "w") as f:
    json.dump(registry, f, indent=2)

print(f"Task registered in registry")
EOF

# ── Confirm ───────────────────────────────────
echo ""
echo "✓ Agent spawned successfully"
echo "  Session:  $SESSION_NAME"
echo "  Model:    $MODEL_NAME"
echo "  Branch:   $BRANCH_NAME"
echo "  Logs:     $LOG_FILE"
echo ""
echo "Watch it:   tmux attach -t $SESSION_NAME"
echo "Detach:     Ctrl+B then D"
echo "Kill it:    tmux kill-session -t $SESSION_NAME"
