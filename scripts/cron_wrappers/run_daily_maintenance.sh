#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
REPO=/home/parison/projects/first-repo
LOG=$REPO/logs/daily_maintenance.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting daily-maintenance" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$REPO"

PYTHONUTF8=1 python3 scripts/daily_maintenance.py >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished daily-maintenance (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
