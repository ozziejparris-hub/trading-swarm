#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
REPO=/home/parison/projects/first-repo
LOG=$REPO/logs/daily_maintenance.log
ENV=/home/parison/.env_trading

source "$ENV" 2>/dev/null || {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

# --- Overlap guard (2026-09-21-daily-maintenance-flock-guard.md) ---
#
# Named the highest-priority remaining target in MASTER_HANDOVER_2026-09-05.md
# ("the eight remaining unguarded cron wrappers ... run_daily_maintenance.sh
# is named as the next and highest-priority target"). PRECAUTIONARY, not a
# fix for an observed daily_maintenance overlap -- the 2026-09-13 audit found
# 87 Starting and 87 Finished markers perfectly 1:1 paired across 106 days of
# log history, zero overlaps ever. It closes two real, separate collision
# risks instead: polymarket-sunday-elo.timer's runtime has grown linearly
# (R^2=0.96, ~8.8 min/week) from 123.7 to 174.4 minutes over six weeks and is
# projected to cross the 06:00 UTC boundary on 2026-09-27, the very next
# Sunday; and a stuck/SIGKILLed daily_maintenance.py (2026-09-20's run alone
# caused a lock storm on its own) previously had nothing to stop a second
# cron-fired instance from starting on top of it.
#
# Same flock (not lockfile-existence / PID file) reasoning as the proven
# guard on run_database_backup.sh (2026-08-26-backup-guard-and-scheduling.md,
# 27/27 assertions including a demonstrated SIGKILL-survival case): the lock
# is held via an open file descriptor, which the kernel releases the instant
# the holding process exits for ANY reason -- clean exit, SIGKILL, OOM, or a
# reboot. There is no on-disk lock *state* to go stale and no cleanup code
# that has to run correctly after a crash for the next run to work. A
# lockfile left behind by a SIGKILLed run would block every subsequent run
# silently and forever -- the worst possible failure mode for a daily job --
# so a bare lockfile-existence check was rejected outright, not merely
# considered.
#
# DIFFERS FROM THE BACKUP GUARD in two deliberate ways, both because a
# refused daily_maintenance run is a bigger deal than a refused nightly
# backup (which tolerates being skipped some nights by explicit prior
# decision): (1) exit code 75 (EX_TEMPFAIL, sysexits.h -- "temporary
# failure, indicating something that is not really an error") on refusal,
# not exit 0, so a refusal is distinguishable from a genuine completed run
# by anything that checks this wrapper's exit code, not just its log; (2) a
# refusal also reaches Telegram (TELEGRAM_AGENTS_TOKEN/TELEGRAM_CHAT_ID --
# the same credentials scripts/polymarket_changelog_monitor.py and
# scripts/run_feedback_loop_agent.py already use for trading-swarm-side
# alerts), sent on EVERY refusal with no change-gating: refusals are
# expected to be extremely rare (this guard is precautionary, not for a
# known-frequent condition, per the 87/87 audit above), so if one ever
# fires that is itself anomalous and worth full visibility every time, not
# summarized or suppressed after the first occurrence -- unlike a slowly
# drifting metric, each additional day maintenance silently doesn't run is
# independently bad, not a repeat of the same news. monitoring/failure_age.py's
# register/reconcile machinery (used elsewhere for exactly this kind of
# decision) was considered and deliberately NOT used here: it is built to
# classify and age-track persistent, content-keyed findings across runs and
# suppress ones a human has explicitly accepted -- the wrong shape for a
# boolean daily gate event that should not be accepted or aged into silence.
# The Telegram send is best-effort (`|| true`): a failed alert must never
# change this wrapper's exit code.
#
# EXTERNAL PROBE: this same lockfile is also the primitive for OTHER jobs to
# ask "is daily_maintenance running?" without blocking or racing the guard
# above -- `flock -n "$LOCKFILE" -c true; echo $?` (0 = lock was free = NOT
# in progress; 1 = lock is held = IN PROGRESS). Non-blocking, side-effect-free
# beyond creating the lockfile if it doesn't exist yet, and uses the same
# kernel primitive as the guard itself rather than a second, weaker signal.
# See the decision doc for why this is documented here rather than shipped
# as a new script in this task, and what adopting it in
# scripts/corpus_content_extractor.py's maintenance_in_progress() (currently
# a log-tail heuristic, mid-run and deliberately untouched right now) would
# involve next.
LOCKFILE="$SWARM/scripts/cron_wrappers/run_daily_maintenance.sh.lock"
exec 200<>"$LOCKFILE"
if ! flock -n 200; then
    HELD_SINCE=$(cat "$LOCKFILE" 2>/dev/null)
    NOW_EPOCH=$(date -u +%s)
    if [ -n "$HELD_SINCE" ] && HELD_EPOCH=$(date -u -d "$HELD_SINCE" +%s 2>/dev/null); then
        ELAPSED=$(( NOW_EPOCH - HELD_EPOCH ))
        ELAPSED_H=$(awk "BEGIN { printf \"%.2f\", $ELAPSED/3600 }")
        REASON="lock held since ${HELD_SINCE}, ~${ELAPSED_H}h ago"
    else
        REASON="lock held by another instance; its start time could not be read"
    fi
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SKIPPED -- daily-maintenance already running (${REASON}). This is a deliberate skip, not a script failure -- see brain/decisions/2026-09-21-daily-maintenance-flock-guard.md." >> "$LOG"
    if [ -n "${TELEGRAM_AGENTS_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -m 15 -X POST "https://api.telegram.org/bot${TELEGRAM_AGENTS_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=daily_maintenance REFUSED (overlap guard) -- ${REASON}. See logs/daily_maintenance.log." \
            > /dev/null 2>&1 || true
    fi
    exit 75
fi
# Lock acquired -- we are the only instance past this point. Safe to
# (re)write our own start time now; any prior content is necessarily
# stale (either a clean prior run that should have cleared it, or an
# orphaned one -- either way it's ours to overwrite once we hold the lock).
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOCKFILE"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting daily-maintenance" >> "$LOG"

cd "$REPO"

PYTHONUTF8=1 python3 scripts/daily_maintenance.py >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished daily-maintenance (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
