# Server Runbook

Last updated: 2026-04-21
Maintained by: Oscar

---

## Purpose

This document contains exact commands for diagnosing and fixing
the most common problems with the trading swarm server.

Read this BEFORE SSHing in when something goes wrong. Knowing
what you're going to do before you do it prevents making things
worse under pressure.

---

## Quick Reference — First Steps for Any Problem

```bash
# 1. SSH into the server
ssh trading-swarm

# 2. Instant health check
cd ~/trading-swarm
bash scripts/check_agents.sh

# 3. Check orchestrator status
sudo systemctl status trading-swarm

# 4. Check what's running in tmux
tmux ls

# 5. Check recent logs
tail -50 logs/orchestrator.log
tail -50 logs/agent_logs/signal-agent.log
```

If those five commands don't reveal the problem, work through
the relevant section below.

---

## Section 1 — Orchestrator Is Down

**Symptoms:** No Telegram messages for more than 2 hours.
check_agents.sh shows no active sessions.

**Step 1 — Check if systemd restarted it:**
```bash
sudo systemctl status trading-swarm
sudo journalctl -u trading-swarm -n 50
```

**Step 2 — If systemd shows failed, restart it:**
```bash
sudo systemctl restart trading-swarm
sudo systemctl status trading-swarm
# Wait 30 seconds then check Telegram for startup message
```

**Step 3 — If systemd restart fails, start manually:**
```bash
tmux new -s orchestrator
cd ~/trading-swarm
source ~/.env_trading
python3 orchestrator/orchestrator.py
# Ctrl+B then D to detach
```

**Step 4 — If orchestrator crashes immediately, check the error:**
```bash
cd ~/trading-swarm
source ~/.env_trading
python3 orchestrator/orchestrator.py 2>&1 | head -50
# Read the error before doing anything else
```

**Common causes:**
- Database locked → see Section 4
- Missing environment variable → check `echo $TELEGRAM_AGENTS_TOKEN`
- File permission issue → check `ls -la brain/signals.json`
- Import error after a bad commit → see Section 7 (rollback)

---

## Section 2 — Polymarket Monitoring System Issues

**Symptoms:** No hourly Telegram health reports. P&L worker
not processing traders. ELO not updating.

**Step 1 — Check which processes are running:**
```bash
sudo systemctl status polymarket-monitoring
sudo systemctl status polymarket-observer
```

**Step 2 — Check monitoring logs:**
```bash
sudo journalctl -u polymarket-monitoring -n 50
# Or follow live:
sudo journalctl -u polymarket-monitoring -f
```

**Step 3 — If monitoring is dead, restart it:**
```bash
sudo systemctl restart polymarket-monitoring
sudo systemctl status polymarket-monitoring
```

**Step 4 — Check observer process:**
```bash
sudo systemctl status polymarket-observer
sudo journalctl -u polymarket-observer -n 50
```

**Step 5 — If observer is dead, restart it:**
```bash
sudo systemctl restart polymarket-observer
sudo systemctl status polymarket-observer
```

**Step 6 — Verify daily maintenance cron is set:**
```bash
crontab -l
# Should show: 0 6 * * * cd ~/projects/first-repo && PYTHONUTF8=1 python3 scripts/daily_maintenance.py >> logs/daily_maintenance.log 2>&1
# If missing, add it:
crontab -e
# Add: 0 6 * * * cd ~/projects/first-repo && PYTHONUTF8=1 python3 scripts/daily_maintenance.py >> logs/daily_maintenance.log 2>&1
```

**Common causes:**
- Screen session died after SSH disconnect → restart with screen
- fcntl file locking issue → check logs for lock errors
- Database file permissions → see Section 5
- Environment variables not loaded → check `echo $TELEGRAM_CHAT_ID`

---

## Section 3 — Agent Producing Empty Output

**Symptoms:** Agent session exists in tmux but no output files
in brain/agent-outputs/. No signal written to signals.json.

**Step 1 — Attach to the agent session:**
```bash
tmux attach -t <agent-name>
# Read what's on screen
# Ctrl+B then D to detach
```

**Step 2 — Check the agent's log:**
```bash
tail -100 logs/agent_logs/<agent-name>.log
```

**Step 3 — Check if the agent is waiting for something:**
```bash
# Check signals.json for pending signals it may be waiting on
cat brain/signals.json | python3 -m json.tool | grep -A5 "pending"
```

**Step 4 — If agent is stuck, kill and respawn:**
```bash
# Kill the tmux session
tmux kill-session -t <agent-name>

# Remove stale registry entry
# Edit brain/agent_registry.json and remove the stuck entry

# Respawn the agent
bash scripts/spawn_agent.sh <task_id> <agent_type> <tier> "<description>"
```

**Common causes:**
- Waiting for a signal response that never came → clear pending signals
- Database read timeout → see Section 4
- API rate limit hit → wait 60 seconds and check logs
- Context window overflow on large tasks → split the task

---

## Section 4 — Database Locked

**Symptoms:** Errors containing "database is locked" or
"unable to open database file" in any log.

**Step 1 — Check what's holding the lock:**
```bash
lsof ~/projects/first-repo/data/polymarket_tracker.db
# Or for trading swarm DB:
lsof /data/polymarket_tracker.db
```

**Step 2 — Check WAL mode is active:**
```bash
sqlite3 /data/polymarket_tracker.db "PRAGMA journal_mode;"
# Should return: wal
# If not: sqlite3 /data/polymarket_tracker.db "PRAGMA journal_mode=WAL;"
```

**Step 3 — If a process is holding an exclusive lock:**
```bash
# Identify the PID from lsof output
kill -9 <PID>
# Then restart whatever process was killed
```

**Step 4 — If WAL files are corrupted:**
```bash
# Check for stale WAL files
ls -la /data/polymarket_tracker.db*
# If -wal or -shm files exist and the DB is not open:
sqlite3 /data/polymarket_tracker.db "PRAGMA wal_checkpoint(FULL);"
```

**Step 5 — Last resort — restore from backup:**
```bash
# List available backups
ls -la ~/trading-swarm/backups/
# Restore (ONLY if DB is genuinely corrupted):
cp ~/trading-swarm/backups/polymarket_tracker_YYYY-MM-DD.db \
   /data/polymarket_tracker.db
# Verify integrity:
sqlite3 /data/polymarket_tracker.db "PRAGMA integrity_check;"
```

**Prevention:** WAL mode should prevent most locking issues.
If locking is recurring, check that all scripts use:
`PRAGMA journal_mode=WAL;` at connection open.

---

## Section 5 — File Permission Issues

**Symptoms:** Permission denied errors in logs. Agents
cannot write to brain/ directory. Database read errors.

**Step 1 — Check current permissions:**
```bash
ls -la /data/polymarket_tracker.db
ls -la ~/trading-swarm/brain/
ls -la ~/.env_trading
```

**Step 2 — Expected permissions:**
```bash
# Database: owner rw, group r, others none
# -rw-r----- parison:swarm /data/polymarket_tracker.db
sudo chown parison:swarm /data/polymarket_tracker.db
sudo chmod 640 /data/polymarket_tracker.db

# Env file: owner read/write only
# -rw------- parison:parison ~/.env_trading
chmod 600 ~/.env_trading

# Brain directory: owner rwx, group rx, others none
chmod 750 ~/trading-swarm/brain/
```

**Step 3 — If swarm user can't write to agent outputs:**
```bash
sudo chown -R parison:swarm ~/trading-swarm/brain/agent-outputs/
sudo chmod -R g+w ~/trading-swarm/brain/agent-outputs/
```

---

## Section 6 — Telegram Alerts Not Firing

**Symptoms:** System appears running but no Telegram messages
received. No alerts for known events.

**Step 1 — Test Telegram connectivity directly:**
```bash
source ~/.env_trading
python3 << 'EOF'
import requests, os
resp = requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_AGENTS_TOKEN']}/sendMessage",
    json={"chat_id": os.environ["TELEGRAM_CHAT_ID"],
          "text": "Manual test ping from server"}
)
print(resp.json())
EOF
```

**Step 2 — If test fails, check environment variables:**
```bash
echo $TELEGRAM_AGENTS_TOKEN
echo $TELEGRAM_ORCHESTRATOR_TOKEN
echo $TELEGRAM_CHAT_ID
# If blank, env file not loaded:
source ~/.env_trading
```

**Step 3 — If env variables are set but API call fails:**
```bash
# Check outbound HTTPS is allowed
curl -I https://api.telegram.org
# Should return HTTP 200
# If blocked, check UFW:
sudo ufw status
# Should show: 443/tcp ALLOW OUT
```

> **Note — UFW outgoing policy:** UFW's default outgoing policy is set to `allow` (not `deny`).
> This is intentional: Mullvad VPN's kill switch conflicts with `ufw default deny outgoing` and
> prevents all traffic when the rule is active. Mullvad handles outbound traffic protection while
> connected. **If Mullvad is ever removed**, run `sudo ufw default deny outgoing` and re-add
> explicit allow rules for required ports (443, 53, etc.) before restarting the server.

**Step 4 — Check if bot token is still valid:**
```bash
curl "https://api.telegram.org/bot$TELEGRAM_AGENTS_TOKEN/getMe"
# Should return bot info JSON
# If returns 401, token has been revoked — generate new token via BotFather
```

---

## Section 7 — Rolling Back a Bad Commit

**Symptoms:** System was working, a git pull or code change
broke something. Need to revert to last working state.

**Step 1 — Identify the last working commit:**
```bash
cd ~/trading-swarm
git log --oneline -10
# Find the commit hash before the problem started
```

**Step 2 — Check what changed:**
```bash
git diff <commit-hash> HEAD
# Read carefully before reverting
```

**Step 3 — Revert to last working commit (safe method):**
```bash
# This creates a new commit that undoes the bad one
git revert HEAD
# Or revert a specific commit:
git revert <commit-hash>
```

**Step 4 — Hard reset (only if you're sure):**
```bash
# WARNING: this permanently discards commits
# Only use if revert doesn't work and you understand what you're losing
git reset --hard <commit-hash>
git push --force origin master
```

**Step 5 — Restart affected services after rollback:**
```bash
sudo systemctl restart trading-swarm
screen -r monitoring  # verify still running
```

---

## Section 8 — Server Unreachable via SSH

**Symptoms:** `ssh trading-swarm` times out or refuses connection.

**Step 1 — Check if it's a network issue:**
```bash
# From your Windows PC / WSL2:
ping <server-ip>
# If no response, server may be down or IP changed
```

**Step 2 — If IP changed (router reassigned it):**
```bash
# Check router admin page for new IP
# Update SSH config:
nano ~/.ssh/config
# Change HostName to new IP
```

**Step 3 — Connect via Tailscale (backup method):**
```bash
# Tailscale gives stable hostname regardless of local IP
ssh parison@trading-swarm.tail<xxxxx>.ts.net
```

**Step 4 — If server is genuinely down:**
- Check physical power and ethernet connection
- Check if power outage occurred
- Server should auto-restart on power restore if BIOS
  is configured for it (set this on day one)
- Check systemd services restart automatically on boot:
  `sudo systemctl is-enabled trading-swarm` → should show "enabled"

**Step 5 — BIOS auto-power-on setting (do this on day one):**
On the UM890 Pro, set "Restore on AC Power Loss" to "Power On"
in BIOS so server restarts automatically after any power cut.

---

## Section 9 — API Costs Spiking

**Symptoms:** Unexpected charges on Anthropic account.
Weekly costs significantly above expected.

**Step 1 — Identify which agent is running frequently:**
```bash
# Count agent spawns in logs
grep "spawning" logs/orchestrator.log | \
  grep "$(date +%Y-%m-%d)" | \
  awk '{print $NF}' | sort | uniq -c | sort -rn
```

**Step 2 — Check for runaway agent loops:**
```bash
# An agent that keeps failing and being respawned costs money
grep "respawn\|retry\|failed" logs/orchestrator.log | tail -50
```

**Step 3 — Temporarily throttle a specific agent:**
```bash
# Kill the agent session
tmux kill-session -t <agent-name>
# Remove from registry
# Edit brain/agent_registry.json
# Do not respawn until cause is identified
```

**Step 4 — Check Anthropic usage dashboard:**
```
https://console.anthropic.com/usage
```

**Step 5 — Emergency — pause all paid API calls:**
```bash
# Stop the orchestrator
sudo systemctl stop trading-swarm
# Investigate before restarting
```

---

## Section 10 — Pre-Resolution Intelligence Not Firing

**Symptoms:** No pre-resolution Telegram messages at 8am UTC.

**Step 1 — Check observer is running:**
```bash
screen -r observer
# Look for pre-resolution loop log entries
```

**Step 2 — Run manually to test:**
```bash
cd ~/projects/first-repo
source ~/.env_trading
python scripts/pre_resolution_intelligence.py
```

**Step 3 — Check for errors:**
```bash
# The script logs to stdout — check screen session output
# Common error: database path wrong on Linux vs Windows
# Check DB path in script matches actual location
```

---

## Section 11 — Mullvad Stuck on "Connecting"

**Symptoms:** `mullvad status` shows "Connecting" indefinitely.
Outbound internet access is blocked. Telegram alerts stop firing.

**Cause:** UFW default outgoing policy can flip to `deny` (e.g. after a
system update or manual UFW reset), which blocks the UDP/TCP packets
Mullvad needs to establish its tunnel.

**Fix:**
```bash
# Re-allow outgoing traffic so Mullvad can connect
sudo ufw default allow outgoing

# Force Mullvad to retry
mullvad reconnect

# Verify tunnel is up
mullvad status
# Should return: "Connected to <server>"

# Confirm internet is back
curl -I https://api.telegram.org
```

**After the tunnel is up:** Do NOT reset outgoing to `deny` — see the
note in Section 6 Step 3. Mullvad's kill switch is the intended outbound
protection mechanism on this server.

---

## Section 12 — Weekly Swarm Review (Human Checklist)

This is the recurring human review Oscar runs to verify the swarm is functioning
as intended. It is intentionally lightweight — the goal is to catch drift early,
not to micromanage the agents.

> **Update this checklist as the swarm matures.** Once more agents are active and
> Phase 5 gate criteria are approaching, expand the gate tracker and add
> agent-specific health checks as needed.

---

### Daily Check (~2 minutes)

Run this every morning before starting work:

```bash
ssh trading-swarm
sudo journalctl -u trading-swarm -n 20
```

Then check Telegram for any alert messages from the orchestrator.

**What you're looking for:**
- No `ERROR` or `CRITICAL` lines in journalctl
- No Telegram alerts that you haven't already triaged
- If anything looks wrong, find the relevant Section above before acting

---

### Weekly Check (~10 minutes)

Run every Monday after the daily check:

**1. Did feedback-loop-agent write new findings?**
```bash
cat ~/trading-swarm/brain/findings.json
```
Look for new entries with `"status": "resolved"` since last week. The count should
be climbing toward the Phase 5 gate of 3 HIGH-confidence findings.

**2. Were signals generated and acted on?**
```bash
cat ~/trading-swarm/brain/signals.json
```
Any `"status": "pending"` signals older than a few hours may indicate a stuck agent.
Any `"status": "processed"` entries show the orchestrator is routing correctly.

**3. Did any agents complete tasks this week?**
```bash
cat ~/trading-swarm/orchestrator/agent_registry.json
```
Look for entries with `"status": "completed"` and a recent timestamp. Zero completions
for a full week is a signal something is stalled.

**4. Were there orchestrator errors across the week?**
```bash
tail -100 ~/trading-swarm/logs/orchestrator.log
```
Scan for `ERROR`, `CRITICAL`, or repeated `retry` entries. A single failure followed by
a successful retry is fine. Repeated failures on the same task need investigation.

---

### Phase 5 Gate Tracker

Update this block each week with current status:

| Gate Criterion | Status | Notes |
|----------------|--------|-------|
| feedback-loop-agent weekly runs | 1 / 4 | First run 2026-04-25, cron every Monday 7am UTC |
| HIGH-confidence findings in findings.json | 0 / 3 | 9 total findings, all LOW confidence — need 20+ resolved markets per finding |
| Pre-resolution accuracy ≥60% | 50% from 4 samples — below threshold | STR-002; need 10+ markets |
| RQ1.1 (ELO predicts Brier T+1) | INCONCLUSIVE — rerun 2026-06-01 | n=16, timing constraint. point-in-time ELO fix applied. |
| RQ3.2 (elite consensus > market price) | INCONCLUSIVE — rerun when sample grows | n=4 after clean filters. Methodology reframe to RQ2.2 needed. |

**Scheduled reruns:**
- RQ1.1: 2026-06-01 — Period 2 will have 60 days, expect 50-100 qualifying traders
- RQ3.2: reframe as RQ2.2 (directional entry timing) — design session needed
- feedback-loop-agent run 2: 2026-04-28 (Monday)
- feedback-loop-agent run 3: 2026-05-05 (Monday)
- feedback-loop-agent run 4: 2026-05-12 (Monday) — gate criterion met if run completes

**All 4 criteria must be met before live trading.** Do not lower or skip any gate.

---

### What Healthy Looks Like

| Signal | Healthy | Needs Attention |
|--------|---------|-----------------|
| journalctl -u trading-swarm | No errors; regular 10-min loop entries | Any ERROR or CRITICAL; silence > 30 min |
| Telegram | Routine status messages; no unresolved alerts | Silence > 2 hours; repeated escalation alerts |
| signals.json | Signals processed promptly; no stale pending entries | Pending signals > 6 hours old |
| agent_registry.json | Tasks completing; no agent stuck in `running` for > 4 hours | Same task retried 3+ times; registry not updating |
| findings.json | New entries accumulating over weeks | No new entries after 2+ weeks of operation |
| Anthropic usage | Stable weekly cost; no unexpected spikes | Cost 2× above prior week without explanation |

---

## Daily Health Check (2 minutes)

Run this every morning:

```bash
ssh trading-swarm
bash ~/trading-swarm/scripts/check_agents.sh
tail -20 ~/trading-swarm/logs/orchestrator.log
screen -ls
exit
```

If everything looks normal, you're done. If anything looks
wrong, work through the relevant section above.

---

## Weekly Health Check (10 minutes)

Every Monday:
1. Read performance-analyst Telegram report
2. Check findings.json for new feedback-loop-agent entries
3. Review strategy-registry.md for overdue revalidations
4. Check Anthropic usage dashboard for cost trends
5. Run: `sudo systemctl status trading-swarm`
6. Run: `df -h` (check disk space — models + DB can fill fast)

---

## Monthly Maintenance (30 minutes)

1. Run wash_trade_audit.py and bot_detection.py in first-repo
2. Review API costs — flag if any agent exceeded budget
3. Check disk space and clean old logs if needed:
   ```bash
   find ~/trading-swarm/logs -name "*.log" -mtime +30 -delete
   ```
4. Verify backup integrity:
   ```bash
   sqlite3 ~/trading-swarm/backups/$(ls -t ~/trading-swarm/backups/ | head -1) \
     "PRAGMA integrity_check;"
   ```
5. Update competitive-moat.md if any major new tools emerged
6. Review research-scout-agent outputs for anything flagged

---

## Emergency Contacts and Resources

```
Anthropic status:     status.anthropic.com
Telegram bot issues:  t.me/BotFather
Polymarket status:    polymarket.com (check manually)
Tailscale dashboard:  login.tailscale.com
Server SSH config:    ~/.ssh/config (WSL2)
DB backups:           ~/trading-swarm/backups/
Env file:             ~/.env_trading
```

---

## Section 13 — Post-Polymarket-Upgrade Checklist

Run this after any Polymarket API upgrade announcement:

1. Check fetch_market_resolutions.py still works:
   cd ~/projects/first-repo
   python scripts/fetch_market_resolutions.py --force 2>&1 | head -30
   Confirm tokens[].winner field still present in response.

2. Check Data API trade response format unchanged:
   curl "https://data-api.polymarket.com/trades?limit=1" | python3 -m json.tool
   Confirm timestamp field is still in seconds (value < 2e9 for current dates)
   If value > 1e12 it has switched to milliseconds — update monitor.py line ~638

3. Check monitoring is still ingesting trades:
   tail -20 ~/projects/first-repo/logs/monitoring.log
   Should show trades processed within last 15 minutes

4. Monitor Polymarket changelog weekly:
   https://docs.polymarket.com/changelog
   Bookmark and check every Monday as part of weekly review.

Next scheduled Polymarket upgrade: CLOB V2 — April 28 2026 (verified safe, no changes needed)

---

## Key File Locations (Server)

```
Trading swarm repo:   ~/trading-swarm/
Polymarket system:    ~/projects/first-repo/
Database:             /data/polymarket_tracker.db
DB backups:           ~/trading-swarm/backups/
Env file:             ~/.env_trading
Orchestrator logs:    ~/trading-swarm/logs/orchestrator.log
Agent logs:           ~/trading-swarm/logs/agent_logs/
Brain directory:      ~/trading-swarm/brain/
Signals bus:          ~/trading-swarm/brain/signals.json
Findings bus:         ~/trading-swarm/brain/findings.json
Strategy registry:    ~/trading-swarm/brain/strategy-registry.md
Runbook:              ~/trading-swarm/brain/runbook.md (this file)
```
