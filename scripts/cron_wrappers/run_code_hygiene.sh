#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/code_hygiene.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting code-hygiene-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "hygiene-$(date +%Y%m%d)" \
    "code-hygiene-agent" \
    "2" \
    "Run weekly code hygiene audit. Check both repos: /home/parison/projects/first-repo and /home/parison/trading-swarm. Full audit per template." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished code-hygiene-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
