#!/bin/bash
# ─────────────────────────────────────────────
# backup_database.sh
# Daily backup of polymarket_tracker.db.
# Keeps 7 days of rolling backups.
# Runs via cron — see setup instructions below.
#
# Install (run once on server):
#   chmod +x scripts/backup_database.sh
#   crontab -e
#   Add this line:
#   0 3 * * * /home/parison/trading-swarm/scripts/backup_database.sh
#
# That runs daily at 3am, safely between
# the auto-reboot window (3am) and market open.
# ─────────────────────────────────────────────

set -e

DB_SOURCE="/home/parison/projects/first-repo/data/polymarket_tracker.db"
BACKUP_DIR="/home/parison/projects/first-repo/data/backups"
TIMESTAMP=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/polymarket_tracker_$TIMESTAMP.db"
LOG_FILE="/home/parison/trading-swarm/logs/backup.log"
KEEP_DAYS=7

# ── Create backup directory if needed ────────
mkdir -p "$BACKUP_DIR"

# ── Check source exists ───────────────────────
if [ ! -f "$DB_SOURCE" ]; then
    echo "$(date): ERROR — source database not found: $DB_SOURCE" >> "$LOG_FILE"
    exit 1
fi

# ── SQLite safe backup (not a raw file copy) ─
# sqlite3 .backup is safe to run on a live database.
# It won't corrupt the backup if a write happens mid-copy.
sqlite3 "$DB_SOURCE" ".backup '$BACKUP_FILE'"

# ── Verify backup is valid ────────────────────
if sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "$(date): OK — backup created: $BACKUP_FILE ($SIZE)" >> "$LOG_FILE"
else
    echo "$(date): ERROR — backup failed integrity check: $BACKUP_FILE" >> "$LOG_FILE"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# ── Remove backups older than KEEP_DAYS ──────
find "$BACKUP_DIR" -name "polymarket_tracker_*.db" \
    -mtime +$KEEP_DAYS -delete

REMAINING=$(ls "$BACKUP_DIR"/polymarket_tracker_*.db 2>/dev/null | wc -l)
echo "$(date): Retention — $REMAINING backup(s) kept (last $KEEP_DAYS days)" >> "$LOG_FILE"
