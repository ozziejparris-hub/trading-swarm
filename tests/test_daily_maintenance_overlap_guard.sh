#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# test_daily_maintenance_overlap_guard.sh
#
# Verifies the flock -n overlap guard added to
#   scripts/cron_wrappers/run_daily_maintenance.sh
# Companion to brain/decisions/2026-09-21-daily-maintenance-flock-guard.md.
# Directly modeled on tests/test_backup_overlap_guard.sh (the proven
# template for this exact pattern, 27/27 assertions, including a
# demonstrated SIGKILL-survival case) -- reused, not reinvented, wherever it
# applies. Extended with an ALERT PATH scenario (this guard, unlike the
# backup one, sends Telegram on refusal) and a PROBE scenario (this guard
# also serves an external "is maintenance running?" primitive purpose 2's
# backup guard did not need).
#
# Covered:
#   A  BLOCKED PATH   — lock held by another process -> wrapper skips
#                       immediately, logs the elapsed-time line, exits 75
#                       (EX_TEMPFAIL, not 0 -- see the decision doc for why
#                       this differs from the backup guard's exit 0),
#                       sends exactly one Telegram alert, does NOT invoke
#                       daily_maintenance.py.
#   B  ALLOW PATH     — no lock held -> wrapper proceeds, invokes the stand-in
#                       maintenance script, logs Starting/Finished, exits 0,
#                       sends NO Telegram alert.
#   C  REACQUIRE      — after a clean exit the next run acquires again.
#   D  SIGKILL        — a stand-in maintenance holder killed with SIGKILL (no
#                       TERM, no cleanup hook) -> lock auto-releases
#                       immediately, next run acquires. THE CRITICAL TEST --
#                       the one a lockfile-existence implementation fails,
#                       silently.
#   P  PROBE          — the documented `flock -n LOCKFILE -c true` one-liner
#                       (purpose 2, the external probe) reports IN_PROGRESS
#                       while a stand-in holds the lock and NOT_IN_PROGRESS
#                       once it exits -- no false positive, no false
#                       negative, and never blocks.
#
# ISOLATION -- no real maintenance run, no real Telegram send, the
# production DB, lockfile, and Telegram credentials are never touched:
#   * The wrapper derives SWARM, REPO, LOG, ENV, and the lockfile path
#     entirely from its own `SWARM=`/`REPO=`/`ENV=` lines. Each test copies
#     the wrapper into a fresh `mktemp -d` root with those three lines
#     rewritten to temp paths; every other line runs verbatim.
#   * ENV points at a temp stub .env_trading (fake TELEGRAM_AGENTS_TOKEN /
#     TELEGRAM_CHAT_ID -- never the real credentials).
#   * `curl` itself is shadowed on PATH by a stub that appends one line per
#     invocation to a marker file and exits 0 -- no real network call, and
#     invocation COUNT is directly assertable (test A.5/B.4).
#   * A stub `scripts/daily_maintenance.py` in the temp REPO root replaces
#     the real 2-10h maintenance run: it appends a marker line and exits 0
#     -- this is the "stand-in script that mimics maintenance" for the
#     ALLOW-PATH / REACQUIRE scenarios (B, C).
#   * Lock holders (scenarios A, D, P) are separate `setsid` subshells that
#     open the temp lockfile, flock -x it, and idle -- a second, more
#     direct stand-in that mimics maintenance HOLDING THE LOCK specifically
#     (the property under test), independent of what the stand-in script
#     above does. They are killed by process-group so nothing is orphaned.
#
# Exit 0 iff every assertion passes.
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER_SRC="$REPO_ROOT/scripts/cron_wrappers/run_daily_maintenance.sh"

PASS=0
FAIL=0
declare -a FAILED=()
declare -a ROOTS=()
HOLDER=""
declare -a HOLDERS=()

ok()  { PASS=$((PASS + 1)); printf '  ok    %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  FAIL  %s\n' "$1"; }

assert_eq()           { [ "$1" = "$2" ]  && ok "$3" || bad "$3 (got '$1', want '$2')"; }
assert_file()         { [ -f "$1" ]      && ok "$2" || bad "$2 (missing $1)"; }
assert_no_file()      { [ ! -e "$1" ]    && ok "$2" || bad "$2 (unexpectedly present: $1)"; }
assert_contains()     { grep -qF -- "$2" "$1" 2>/dev/null && ok "$3" || bad "$3 (expected substring '$2' in $1)"; }
assert_not_contains() { grep -qF -- "$2" "$1" 2>/dev/null && bad "$3 (unexpected substring '$2' in $1)" || ok "$3"; }
assert_match()        { printf '%s' "$1" | grep -Eq -- "$2" && ok "$3" || bad "$3 (value '$1' does not match /$2/)"; }
count_lines()          { [ -f "$1" ] && wc -l < "$1" | tr -d ' ' || echo 0; }

cleanup() {
  [ -n "$HOLDER" ] && kill -9 -"$HOLDER" 2>/dev/null
  for h in "${HOLDERS[@]:-}"; do [ -n "$h" ] && kill -9 -"$h" 2>/dev/null; done
  for r in "${ROOTS[@]:-}";   do [ -n "$r" ] && rm -rf "$r"; done
}
trap cleanup EXIT

# make_env -> prints the temp root. Builds root/swarm, root/repo (with a
# stub daily_maintenance.py and logs/ dir), root/repo/.env_trading (fake
# Telegram creds), and a stub `curl` shadowing PATH via root/bin.
make_env() {
  # NOTE: called via command substitution (root="$(make_env)") at every call
  # site, so this function runs in a SUBSHELL -- appending to ROOTS here
  # would not survive back to the parent shell where cleanup()'s trap runs.
  # (The backup guard test this is modeled on has exactly this latent bug --
  # harmless there too, just leftover /tmp dirs, not a correctness issue --
  # noted in the decision doc rather than silently carried forward here.)
  # Callers append to ROOTS themselves, right after capturing the path.
  local root
  root="$(mktemp -d "${TMPDIR:-/tmp}/dmguard.XXXXXX")"
  mkdir -p "$root/swarm/scripts/cron_wrappers" "$root/repo/scripts" "$root/repo/logs" "$root/bin"

  sed -e "s#^SWARM=.*#SWARM=$root/swarm#" \
      -e "s#^REPO=.*#REPO=$root/repo#" \
      -e "s#^ENV=.*#ENV=$root/repo/.env_trading#" \
      "$WRAPPER_SRC" > "$root/swarm/scripts/cron_wrappers/run_daily_maintenance.sh"
  chmod +x "$root/swarm/scripts/cron_wrappers/run_daily_maintenance.sh"

  cat > "$root/repo/.env_trading" <<'ENVSTUB'
TELEGRAM_AGENTS_TOKEN=faketoken123
TELEGRAM_CHAT_ID=fakechat456
ENVSTUB

  cat > "$root/repo/scripts/daily_maintenance.py" <<'STUB'
import sys, datetime
sys.path.insert(0, ".")
print(f"STUB maintenance ran {datetime.datetime.utcnow().isoformat()}Z")
with open("logs/stub_ran.log", "a") as f:
    f.write("ran\n")
sys.exit(0)
STUB

  # curl stub: shadows PATH so no real Telegram call ever fires; records
  # one line per invocation so alert-count is directly assertable.
  cat > "$root/bin/curl" <<'CURLSTUB'
#!/bin/bash
echo "curl invoked: $*" >> "$(dirname "$0")/../curl_calls.log"
exit 0
CURLSTUB
  chmod +x "$root/bin/curl"

  printf '%s\n' "$root"
}

lockfile_of()   { printf '%s\n' "$1/swarm/scripts/cron_wrappers/run_daily_maintenance.sh.lock"; }
logfile_of()    { printf '%s\n' "$1/repo/logs/daily_maintenance.log"; }
stubmark_of()   { printf '%s\n' "$1/repo/logs/stub_ran.log"; }
curllog_of()    { printf '%s\n' "$1/curl_calls.log"; }

run_wrapper() {  # <root> -> propagates exit code; PATH shadowed so curl stub wins
  PATH="$1/bin:$PATH" bash "$1/swarm/scripts/cron_wrappers/run_daily_maintenance.sh"
}

seed_lock_ago() {  # <lockfile> <"N hours ago">
  date -u -d "$2" +%Y-%m-%dT%H:%M:%SZ > "$1"
}

start_holder() {  # <lockfile> -> sets global HOLDER to the holder's process-group id
  local lf="$1" i
  setsid bash -c 'exec 9<>"$0"; flock -x 9; while :; do sleep 0.2; done' "$lf" &
  HOLDER=$!
  HOLDERS+=("$HOLDER")
  for i in $(seq 1 50); do
    if ! flock -n "$lf" -c true 2>/dev/null; then return 0; fi   # lock is held -> good
    sleep 0.1
  done
  echo "start_holder: holder never acquired $lf" >&2
  return 1
}

kill_holder_sigkill() {
  kill -9 -"$HOLDER" 2>/dev/null
  wait "$HOLDER" 2>/dev/null
  HOLDER=""
}

# The documented external probe (purpose 2), exactly as it appears in the
# wrapper's own comment and the decision doc: 0 = free = NOT in progress,
# 1 = held = IN PROGRESS. Never blocks.
probe() {  # <lockfile> -> prints IN_PROGRESS or NOT_IN_PROGRESS
  if flock -n "$1" -c true 2>/dev/null; then
    echo "NOT_IN_PROGRESS"
  else
    echo "IN_PROGRESS"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
echo "daily_maintenance overlap guard — verification harness"
echo "REPO_ROOT=$REPO_ROOT"
echo "wrapper under test: $WRAPPER_SRC"
echo

# ── A. BLOCKED PATH ─────────────────────────────────────────────────────────
echo "A. BLOCKED PATH — lock held, wrapper must skip, exit 75, alert once"
rootA="$(make_env)"; ROOTS+=("$rootA")
lfA="$(lockfile_of "$rootA")"; logA="$(logfile_of "$rootA")"; markA="$(stubmark_of "$rootA")"; curlA="$(curllog_of "$rootA")"
seededA="$(date -u -d '5 hours ago' +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "$seededA" > "$lfA"
start_holder "$lfA" || bad "A: could not establish lock holder"
rcA=0; run_wrapper "$rootA" || rcA=$?
assert_eq "$rcA" "75" "A: blocked run exits 75 (EX_TEMPFAIL, not 0 -- distinguishable from a real run)"
assert_contains "$logA" "SKIPPED -- daily-maintenance already running (lock held since $seededA" "A: skip line records the held-since timestamp"
skiplineA="$(grep 'SKIPPED' "$logA" 2>/dev/null || true)"
assert_match "$skiplineA" '~[0-9]+\.[0-9]{2}h ago'      "A: skip line reports elapsed hours"
assert_match "$skiplineA" '~(4\.9[0-9]|5\.0[0-9])h ago' "A: elapsed ≈ 5h as seeded"
assert_no_file "$markA" "A: daily_maintenance.py NOT invoked while blocked"
assert_not_contains "$logA" "Starting daily-maintenance" "A: no 'Starting' line emitted"
assert_eq "$(count_lines "$curlA")" "1" "A: exactly one Telegram alert sent on refusal"
assert_contains "$curlA" "faketoken123" "A: alert used the configured bot token"
assert_contains "$curlA" "daily_maintenance REFUSED" "A: alert text names the refusal"
kill_holder_sigkill
echo

# ── B. ALLOW PATH ──────────────────────────────────────────────────────────
echo "B. ALLOW PATH — no lock held, wrapper must proceed, no alert"
rootB="$(make_env)"; ROOTS+=("$rootB")
lfB="$(lockfile_of "$rootB")"; logB="$(logfile_of "$rootB")"; markB="$(stubmark_of "$rootB")"; curlB="$(curllog_of "$rootB")"
rcB=0; run_wrapper "$rootB" || rcB=$?
assert_eq "$rcB" "0" "B: allow run exits 0"
assert_file "$markB" "B: stand-in daily_maintenance.py invoked"
assert_contains "$logB" "Starting daily-maintenance"          "B: 'Starting' logged"
assert_contains "$logB" "Finished daily-maintenance (exit: 0)" "B: 'Finished' logged with exit 0"
assert_not_contains "$logB" "SKIPPED" "B: no skip line"
assert_match "$(cat "$lfB")" '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' "B: lockfile stamped with fresh start time after acquire"
assert_eq "$(count_lines "$curlB")" "0" "B: normal run sends no Telegram alert"
echo

# ── C. REACQUIRE AFTER CLEAN EXIT ──────────────────────────────────────────
echo "C. REACQUIRE — second run after B's clean exit must acquire"
rm -f "$markB"
rcC=0; run_wrapper "$rootB" || rcC=$?
assert_eq "$rcC" "0" "C: second run exits 0"
assert_file "$markB" "C: second run invokes maintenance (lock was free after clean exit)"
cntC="$(grep -c 'Finished daily-maintenance' "$logB" 2>/dev/null || echo 0)"
assert_eq "$cntC" "2" "C: two 'Finished' lines after two clean runs"
assert_eq "$(count_lines "$curlB")" "0" "C: still no Telegram alert after two clean runs"
echo

# ── D. SIGKILL SURVIVAL ────────────────────────────────────────────────────
echo "D. SIGKILL — holder killed -9, lock must auto-release (THE CRITICAL TEST)"
rootD="$(make_env)"; ROOTS+=("$rootD")
lfD="$(lockfile_of "$rootD")"; logD="$(logfile_of "$rootD")"; markD="$(stubmark_of "$rootD")"; curlD="$(curllog_of "$rootD")"
seed_lock_ago "$lfD" '2 hours ago'
start_holder "$lfD" || bad "D: could not establish lock holder"
rcD1=0; run_wrapper "$rootD" || rcD1=$?
assert_eq "$rcD1" "75" "D: run while holder alive exits 75 (blocked)"
assert_contains "$logD" "SKIPPED" "D: run while holder alive skips (holder really holds the lock)"
assert_no_file "$markD" "D: maintenance not invoked while holder alive"
assert_eq "$(count_lines "$curlD")" "1" "D: one alert while holder alive"
kill_holder_sigkill
sleep 0.3
rcD2=0; run_wrapper "$rootD" || rcD2=$?
assert_eq "$rcD2" "0" "D: run after SIGKILL exits 0"
assert_file "$markD" "D: maintenance invoked after holder SIGKILLed — lock released with no cleanup code"
assert_contains "$logD" "Starting daily-maintenance" "D: 'Starting' logged on reacquire"
assert_match "$(cat "$lfD")" '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' "D: stale holder timestamp overwritten on reacquire"
assert_eq "$(count_lines "$curlD")" "1" "D: reacquire after SIGKILL sends no NEW alert (still just the one from the blocked attempt)"
echo

# ── P. EXTERNAL PROBE ──────────────────────────────────────────────────────
echo "P. PROBE — flock -n LOCKFILE -c true reports state correctly, never blocks"
rootP="$(make_env)"; ROOTS+=("$rootP")
lfP="$(lockfile_of "$rootP")"
: > "$lfP"  # lockfile must exist for the probe to open it
before="$(probe "$lfP")"
assert_eq "$before" "NOT_IN_PROGRESS" "P: probe reports NOT_IN_PROGRESS before anything holds the lock"
start_holder "$lfP" || bad "P: could not establish lock holder"
during="$(timeout 2 bash -c "$(declare -f probe); probe '$lfP'")"
assert_eq "$during" "IN_PROGRESS" "P: probe reports IN_PROGRESS while a holder holds the lock (no false negative)"
t0=$(date +%s%N)
timeout 2 bash -c "$(declare -f probe); probe '$lfP'" > /dev/null
t1=$(date +%s%N)
elapsed_ms=$(( (t1 - t0) / 1000000 ))
assert_match "$elapsed_ms" '^[0-9]{1,3}$' "P: probe returns in well under 1s while blocked (${elapsed_ms}ms) -- non-blocking, not a slow poll"
kill_holder_sigkill
sleep 0.3
after="$(probe "$lfP")"
assert_eq "$after" "NOT_IN_PROGRESS" "P: probe reports NOT_IN_PROGRESS again once the holder is gone (no false positive)"
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
