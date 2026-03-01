#!/bin/bash
# ─────────────────────────────────────────────
# check_agents.sh
# Quick health check — shows all running agents
# and their status at a glance.
# Run this any time to see what's happening.
#
# Usage: ./scripts/check_agents.sh
# ─────────────────────────────────────────────

BASE_DIR="/home/parison/trading-swarm"
REGISTRY="$BASE_DIR/orchestrator/agent_registry.json"

echo "══════════════════════════════════════"
echo "  Trading Swarm — Agent Status"
echo "  $(date)"
echo "══════════════════════════════════════"

# Show tmux sessions
echo ""
echo "── Active tmux sessions ──"
tmux ls 2>/dev/null || echo "  No active sessions"

# Show registry status
echo ""
echo "── Registry status ──"
python3 - <<EOF
import json
from pathlib import Path
from datetime import datetime

registry_file = Path("$REGISTRY")
try:
    with open(registry_file) as f:
        registry = json.load(f)
except:
    print("  Could not read registry")
    exit()

tasks = registry.get("active_tasks", [])
if not tasks:
    print("  No tasks in registry")
else:
    for task in tasks:
        status = task.get("status", "unknown")
        started = task.get("started_at", "unknown")
        model = task.get("model", "unknown")
        retries = task.get("retries", 0)

        # Calculate runtime
        try:
            start_dt = datetime.fromisoformat(started)
            runtime = datetime.utcnow() - start_dt
            hours = int(runtime.total_seconds() // 3600)
            mins = int((runtime.total_seconds() % 3600) // 60)
            runtime_str = f"{hours}h {mins}m"
        except:
            runtime_str = "unknown"

        status_icon = {
            "running": "🟢",
            "done": "✅",
            "failed": "❌",
            "respawning": "🔄"
        }.get(status, "⚪")

        print(f"  {status_icon} {task['id']}")
        print(f"     Agent:   {task['agent']}")
        print(f"     Model:   {model}")
        print(f"     Status:  {status}")
        print(f"     Runtime: {runtime_str}")
        if retries > 0:
            print(f"     Retries: {retries}")
        print()
EOF

# Show pending signals
echo "── Pending signals ──"
python3 - <<EOF
import json
from pathlib import Path

signals_file = Path("$BASE_DIR/brain/signals.json")
try:
    with open(signals_file) as f:
        data = json.load(f)
except:
    print("  Could not read signals.json")
    exit()

pending = [s for s in data.get("signals", []) if s.get("status") == "pending"]
if not pending:
    print("  No pending signals")
else:
    for s in pending:
        print(f"  → {s.get('type')} from {s.get('from')} to {s.get('to')}")
EOF

echo ""
echo "══════════════════════════════════════"
