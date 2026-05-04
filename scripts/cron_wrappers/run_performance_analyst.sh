#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/performance_analyst.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting performance-analyst-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "analyst-$(date +%Y%m%d)" \
    "performance-analyst-agent" \
    "3" \
    "Run weekly performance analysis. Brier scores, ELO health, signal quality, strategy pipeline, resource usage. Update brain/kpis.md." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished performance-analyst-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
