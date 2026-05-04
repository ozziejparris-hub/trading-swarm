#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/backup.log

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting database-backup" >> "$LOG"

bash "$SWARM/scripts/backup_database.sh" >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished database-backup (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
