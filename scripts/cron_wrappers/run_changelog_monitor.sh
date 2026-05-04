#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/changelog_monitor.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting polymarket-changelog-monitor" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

python3 scripts/polymarket_changelog_monitor.py >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished polymarket-changelog-monitor (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
