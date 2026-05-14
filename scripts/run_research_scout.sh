#!/bin/bash
# Research Scout Agent — Daily Run
# Spawns a Tier 3 agent (Claude Sonnet) with the
# research-scout template. Tier 1 insufficient for
# web research and relevance filtering tasks.
# Called by cron daily at 8am UTC

cd /home/parison/trading-swarm
source ~/.env_trading

TASK_ID="scout-$(date +%Y%m%d)"
SESSION_NAME="research-scout-${TASK_ID}"

# Skip if tmux session already exists (e.g. cron fired twice)
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[$(date)] Scout session $SESSION_NAME already exists — skipping spawn" >> logs/research_scout.log
    exit 0
fi

# Skip if task already registered (e.g. manual run after cron)
if python3 -c "
import json
with open('orchestrator/agent_registry.json') as f:
    r = json.load(f)
ids = [t['id'] for t in r.get('active_tasks', [])]
exit(0 if '${TASK_ID}' in ids else 1)
" 2>/dev/null; then
    echo "[$(date)] Scout task $TASK_ID already in registry — skipping spawn" >> logs/research_scout.log
    exit 0
fi

TASK_DESC="Run your daily research scout cycle. Check all \
Tier 1 sources. Surface up to 5 findings to pending-review. \
Send any immediate escalations. Today is $(date +%Y-%m-%d). \
It is $(date +%A) — if Monday, write weekly digest too."

bash scripts/spawn_agent.sh \
  "$TASK_ID" \
  "research-scout-agent" \
  "2.5" \
  "$TASK_DESC" >> logs/research_scout.log 2>&1

echo "[$(date)] Research scout run complete" >> logs/research_scout.log
