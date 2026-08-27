#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# test_backup_overlap_guard.sh
#
# Verifies the flock -n overlap guard added to
#   scripts/cron_wrappers/run_database_backup.sh
# in commit 9701d77. Companion to
#   brain/decisions/2026-08-26-backup-guard-and-scheduling.md
#
# Covered:
#   A  BLOCKED PATH   — lock held by another process → wrapper skips
#                       immediately, logs the elapsed-time line, exits 0,
#                       does NOT invoke the backup.
#   B  ALLOW PATH     — no lock held → wrapper proceeds, invokes the
#                       backup, logs Starting/Finished, exits 0.
#   C  REACQUIRE      — after a clean exit the next run acquires again.
#   D  SIGKILL        — holder killed with SIGKILL (no TERM, no cleanup
#                       hook) → lock auto-releases, next run acquires.
#                       This is the property that chose flock over a PID
#                       file, so it is demonstrated, not asserted.
#   E  NEGATIVE       — the same BLOCKED scenario run against the
#                       pre-guard wrapper (9701d77^) proves test A would
#                       fail without the guard: that version runs the
#                       backup anyway despite the held lock.
#
# ISOLATION — no real backup runs; the production DB and the production
# lockfile are never touched:
#   * The wrapper derives LOG, LOCKFILE and the backup-script path
#     entirely from its `SWARM=` line. Each test copies the wrapper into
#     a fresh `mktemp -d` root with that one line rewritten to the temp
#     root; every other line runs verbatim.
#   * A stub `scripts/backup_database.sh` in the temp root replaces the
#     real ~18 GB `sqlite3 .backup`: it appends a marker line and exits 0.
#   * Lock holders are `setsid` subshells that open the temp lockfile,
#     flock it, and idle; they are killed by process-group so nothing
#     is orphaned.
#
# Exit 0 iff every assertion passes.
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER_SRC="$REPO/scripts/cron_wrappers/run_database_backup.sh"
PRE_GUARD_REF="9701d77^"

PASS=0
FAIL=0
declare -a FAILED=()
declare -a ROOTS=()
declare -a TMPFILES=()
HOLDER=""

ok()  { PASS=$((PASS + 1)); printf '  ok    %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  FAIL  %s\n' "$1"; }

assert_eq()           { [ "$1" = "$2" ]  && ok "$3" || bad "$3 (got '$1', want '$2')"; }
assert_file()         { [ -f "$1" ]      && ok "$2" || bad "$2 (missing $1)"; }
assert_no_file()      { [ ! -e "$1" ]    && ok "$2" || bad "$2 (unexpectedly present: $1)"; }
assert_contains()     { grep -qF -- "$2" "$1" 2>/dev/null && ok "$3" || bad "$3 (expected substring '$2' in $1)"; }
assert_not_contains() { grep -qF -- "$2" "$1" 2>/dev/null && bad "$3 (unexpected substring '$2' in $1)" || ok "$3"; }
assert_match()        { printf '%s' "$1" | grep -Eq -- "$2" && ok "$3" || bad "$3 (value '$1' does not match /$2/)"; }

cleanup() {
  [ -n "$HOLDER" ] && kill -9 -"$HOLDER" 2>/dev/null
  for h in "${HOLDERS[@]:-}"; do [ -n "$h" ] && kill -9 -"$h" 2>/dev/null; done
  for r in "${ROOTS[@]:-}";   do [ -n "$r" ] && rm -rf "$r"; done
  for f in "${TMPFILES[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done
}
declare -a HOLDERS=()
trap cleanup EXIT

# make_env <wrapper-source-file>  ->  prints the temp SWARM root
make_env() {
  local src="$1" root
  root="$(mktemp -d "${TMPDIR:-/tmp}/bkguard.XXXXXX")"
  ROOTS+=("$root")
  mkdir -p "$root/scripts/cron_wrappers" "$root/logs"
  sed "s#^SWARM=.*#SWARM=$root#" "$src" > "$root/scripts/cron_wrappers/run_database_backup.sh"
  chmod +x "$root/scripts/cron_wrappers/run_database_backup.sh"
  cat > "$root/scripts/backup_database.sh" <<'STUB'
#!/bin/bash
# test stub — stands in for the real sqlite3 .backup, does NOT copy anything
echo "STUB backup ran $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$(dirname "$0")/../logs/stub_ran.log"
exit 0
STUB
  chmod +x "$root/scripts/backup_database.sh"
  printf '%s\n' "$root"
}

lockfile_of() { printf '%s\n' "$1/scripts/cron_wrappers/run_database_backup.sh.lock"; }
logfile_of()  { printf '%s\n' "$1/logs/backup.log"; }
stubmark_of() { printf '%s\n' "$1/logs/stub_ran.log"; }

run_wrapper() { bash "$1/scripts/cron_wrappers/run_database_backup.sh"; }  # propagates exit code

seed_lock_ago() {  # <lockfile> <"N hours ago">
  date -u -d "$2" +%Y-%m-%dT%H:%M:%SZ > "$1"
}

start_holder() {  # <lockfile>  -> sets global HOLDER to the holder's process-group id
  local lf="$1" i
  setsid bash -c 'exec 9<>"$0"; flock -x 9; echo $$ > "$0.holder"; while :; do sleep 0.2; done' "$lf" &
  HOLDER=$!
  HOLDERS+=("$HOLDER")
  for i in $(seq 1 50); do
    if ! flock -n "$lf" -c true 2>/dev/null; then return 0; fi   # lock is held → good
    sleep 0.1
  done
  echo "start_holder: holder never acquired $lf" >&2
  return 1
}

kill_holder_sigkill() {  # SIGKILL only — no SIGTERM, no cleanup hook
  kill -9 -"$HOLDER" 2>/dev/null
  wait "$HOLDER" 2>/dev/null
  HOLDER=""
}

# ─────────────────────────────────────────────────────────────────────────────
echo "backup overlap guard — verification harness"
echo "REPO=$REPO"
echo "wrapper under test: $WRAPPER_SRC"
echo

# ── A. BLOCKED PATH ─────────────────────────────────────────────────────────
echo "A. BLOCKED PATH — lock held, wrapper must skip"
rootA="$(make_env "$WRAPPER_SRC")"
lfA="$(lockfile_of "$rootA")"; logA="$(logfile_of "$rootA")"; markA="$(stubmark_of "$rootA")"
seededA="$(date -u -d '5 hours ago' +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "$seededA" > "$lfA"
start_holder "$lfA" || bad "A: could not establish lock holder"
rcA=0; run_wrapper "$rootA" || rcA=$?
assert_eq "$rcA" "0" "A: blocked run exits 0 (deliberate skip, not failure)"
assert_contains "$logA" "SKIPPED -- backup already running (lock held since $seededA" "A: skip line records the held-since timestamp"
skiplineA="$(grep 'SKIPPED' "$logA" 2>/dev/null || true)"
assert_match "$skiplineA" '~[0-9]+\.[0-9]{2}h ago'      "A: skip line reports elapsed hours"
assert_match "$skiplineA" '~(4\.9[0-9]|5\.0[0-9])h ago' "A: elapsed ≈ 5h as seeded"
assert_no_file "$markA" "A: backup script NOT invoked while blocked"
assert_not_contains "$logA" "Starting database-backup" "A: no 'Starting' line emitted"
kill_holder_sigkill
echo

# ── B. ALLOW PATH ──────────────────────────────────────────────────────────
echo "B. ALLOW PATH — no lock held, wrapper must proceed"
rootB="$(make_env "$WRAPPER_SRC")"
lfB="$(lockfile_of "$rootB")"; logB="$(logfile_of "$rootB")"; markB="$(stubmark_of "$rootB")"
rcB=0; run_wrapper "$rootB" || rcB=$?
assert_eq "$rcB" "0" "B: allow run exits 0"
assert_file "$markB" "B: backup script invoked"
assert_contains "$logB" "Starting database-backup"          "B: 'Starting' logged"
assert_contains "$logB" "Finished database-backup (exit: 0)" "B: 'Finished' logged with exit 0"
assert_not_contains "$logB" "SKIPPED" "B: no skip line"
assert_match "$(cat "$lfB")" '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' "B: lockfile stamped with fresh start time after acquire"
echo

# ── C. REACQUIRE AFTER CLEAN EXIT ──────────────────────────────────────────
echo "C. REACQUIRE — second run after B's clean exit must acquire"
rm -f "$markB"
rcC=0; run_wrapper "$rootB" || rcC=$?
assert_eq "$rcC" "0" "C: second run exits 0"
assert_file "$markB" "C: second run invokes backup (lock was free after clean exit)"
cntC="$(grep -c 'Finished database-backup' "$logB" 2>/dev/null || echo 0)"
assert_eq "$cntC" "2" "C: two 'Finished' lines after two clean runs"
echo

# ── D. SIGKILL SURVIVAL ────────────────────────────────────────────────────
echo "D. SIGKILL — holder killed -9, lock must auto-release"
rootD="$(make_env "$WRAPPER_SRC")"
lfD="$(lockfile_of "$rootD")"; logD="$(logfile_of "$rootD")"; markD="$(stubmark_of "$rootD")"
seed_lock_ago "$lfD" '2 hours ago'
start_holder "$lfD" || bad "D: could not establish lock holder"
rcD1=0; run_wrapper "$rootD" || rcD1=$?
assert_eq "$rcD1" "0" "D: run while holder alive exits 0"
assert_contains "$logD" "SKIPPED" "D: run while holder alive skips (holder really holds the lock)"
assert_no_file "$markD" "D: backup not invoked while holder alive"
kill_holder_sigkill
sleep 0.3
rcD2=0; run_wrapper "$rootD" || rcD2=$?
assert_eq "$rcD2" "0" "D: run after SIGKILL exits 0"
assert_file "$markD" "D: backup invoked after holder SIGKILLed — lock released with no cleanup code"
assert_contains "$logD" "Starting database-backup" "D: 'Starting' logged on reacquire"
assert_match "$(cat "$lfD")" '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' "D: stale holder timestamp overwritten on reacquire"
echo

# ── E. NEGATIVE — pre-guard wrapper fails the BLOCKED test ─────────────────
echo "E. NEGATIVE — same BLOCKED scenario against $PRE_GUARD_REF (no guard)"
preE="$(mktemp "${TMPDIR:-/tmp}/preguard.XXXXXX")"
TMPFILES+=("$preE")
if git -C "$REPO" show "$PRE_GUARD_REF:scripts/cron_wrappers/run_database_backup.sh" > "$preE" 2>/dev/null; then
  assert_not_contains "$preE" "flock" "E: pre-guard wrapper genuinely has no flock"
  rootE="$(make_env "$preE")"
  lfE="$(lockfile_of "$rootE")"; logE="$(logfile_of "$rootE")"; markE="$(stubmark_of "$rootE")"
  seed_lock_ago "$lfE" '5 hours ago'
  start_holder "$lfE" || bad "E: could not establish lock holder"
  rcE=0; run_wrapper "$rootE" || rcE=$?
  assert_eq "$rcE" "0" "E: pre-guard run exits 0"
  assert_file "$markE" "E: pre-guard INVOKES the backup despite the held lock (test A depends on the guard)"
  assert_not_contains "$logE" "SKIPPED" "E: pre-guard emits no skip line"
  assert_contains "$logE" "Starting database-backup" "E: pre-guard proceeds straight to 'Starting'"
  kill_holder_sigkill
else
  bad "E: could not retrieve $PRE_GUARD_REF version of the wrapper"
fi
echo

# ── summary ────────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────"
echo "  $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  for f in "${FAILED[@]}"; do printf '   - %s\n' "$f"; done
  exit 1
fi
echo "  ALL PASS"
exit 0
