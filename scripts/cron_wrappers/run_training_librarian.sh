#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/training_librarian.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting training-librarian-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "librarian-$(date +%Y%m%d)" \
    "training-librarian-agent" \
    "3" \
    "Run weekly brain maintenance. Audit reference library, update failure taxonomy, check agent templates, identify knowledge gaps, update lessons learned." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished training-librarian-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
