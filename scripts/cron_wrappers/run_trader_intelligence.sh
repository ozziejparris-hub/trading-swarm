#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/trader_intelligence.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting trader-intelligence-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "trader-intel-$(date +%Y%m%d)" \
    "trader-intelligence-agent" \
    "3" \
    "Run weekly trader intelligence cycle. Delta-detect stale profiles, analyse archetype drift, discover new Pool C qualifiers, build open position intelligence for eligible LEGENDARY traders, write intelligence report to brain/agent-outputs/trader-intelligence/. Update profiles in brain/trader-profiles/ in-place." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished trader-intelligence-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
