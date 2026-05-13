#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/signal_agent.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting signal-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "signal-$(date +%Y%m%d)" \
    "signal-agent" \
    "3" \
    "Routine signal scan. Rescan all active STR-003 signals for upgrade conditions. Check for new qualifying legendary traders at 95% directional threshold. Update signals.json with rescan notes." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished signal-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
