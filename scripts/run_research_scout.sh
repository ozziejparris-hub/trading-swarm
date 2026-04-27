#!/bin/bash
# Research Scout Agent — Daily Run
# Spawns a Tier 1 agent with the research-scout template
# Called by cron daily at 8am UTC

cd /home/parison/trading-swarm
source ~/.env_trading

TASK_DESC="Run your daily research scout cycle. Check all \
Tier 1 sources. Surface up to 5 findings to pending-review. \
Send any immediate escalations. Today is $(date +%Y-%m-%d). \
It is $(date +%A) — if Monday, write weekly digest too."

bash scripts/spawn_agent.sh \
  "scout-$(date +%Y%m%d)" \
  "research-scout" \
  "1" \
  "$TASK_DESC" >> logs/research_scout.log 2>&1

echo "[$(date)] Research scout run complete" >> logs/research_scout.log
