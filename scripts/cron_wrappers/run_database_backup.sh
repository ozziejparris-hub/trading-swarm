#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/backup.log

# --- Overlap guard (2026-08-26-backup-guard-and-scheduling.md) ---
#
# 2026-08-26-backup-overlap-investigation.md found that the 2026-08-25
# backup instance ran 35.56h and the 2026-08-26 instance launched on top
# of it (11.56h) -- SQLite's Online Backup API restarts whenever a page
# it already copied changes in the source, so a continuously-writing
# sweep can starve this job indefinitely by construction, not by
# coincidence. Nothing previously stopped a second cron-fired instance
# from starting on top of a still-running one.
#
# flock, not a PID file or a pgrep check: the lock is held via an open
# file descriptor, which the kernel releases the instant the holding
# process exits for ANY reason -- clean exit, SIGKILL, OOM, or the box
# rebooting. There is no on-disk lock *state* to go stale and no cleanup
# code that has to run correctly after a crash for the next run to work
# -- the same self-healing reasoning that favored checkpoint-recency
# over a sentinel file for the sweep's own maintenance hold (Fix 1).
#
# CONSEQUENCE, stated plainly per that investigation's own instruction:
# because a starved backup can hold this lock for 35+ hours (observed),
# this guard means a blocked night's backup is SKIPPED, not delayed or
# queued -- flock -n (non-blocking) exits immediately rather than
# waiting behind a holder that could itself run for a day or more.
# Skip-and-log is correct behaviour (queueing would just compound into
# the same pileup one day later, worse each time) but it means, on its
# own, this guard could leave several consecutive nights with no fresh
# backup if the sweep keeps colliding with 03:00 UTC. That is NOT fixed
# here -- it is the reason 2026-08-26-backup-guard-and-scheduling.md's
# Part 2 (segments must finish before the 03:00 UTC backup, not cross
# it) is the primary remedy; this guard is only the backstop that keeps
# a collision from creating a second, compounding overlap.
LOCKFILE="$SWARM/scripts/cron_wrappers/run_database_backup.sh.lock"
exec 200<>"$LOCKFILE"
if ! flock -n 200; then
    HELD_SINCE=$(cat "$LOCKFILE" 2>/dev/null)
    NOW_EPOCH=$(date -u +%s)
    if [ -n "$HELD_SINCE" ] && HELD_EPOCH=$(date -u -d "$HELD_SINCE" +%s 2>/dev/null); then
        ELAPSED=$(( NOW_EPOCH - HELD_EPOCH ))
        ELAPSED_H=$(awk "BEGIN { printf \"%.2f\", $ELAPSED/3600 }")
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SKIPPED -- backup already running (lock held since ${HELD_SINCE}, ~${ELAPSED_H}h ago). This is a deliberate skip, not a script failure -- see 2026-08-26-backup-guard-and-scheduling.md." >> "$LOG"
    else
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SKIPPED -- backup already running (lock held by another instance; its start time could not be read). This is a deliberate skip, not a script failure -- see 2026-08-26-backup-guard-and-scheduling.md." >> "$LOG"
    fi
    exit 0
fi
# Lock acquired -- we are the only instance past this point. Safe to
# (re)write our own start time now; any prior content is necessarily
# stale (either a clean prior run that should have cleared it, or an
# orphaned one -- either way it's ours to overwrite once we hold the lock).
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOCKFILE"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting database-backup" >> "$LOG"

bash "$SWARM/scripts/backup_database.sh" >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished database-backup (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
