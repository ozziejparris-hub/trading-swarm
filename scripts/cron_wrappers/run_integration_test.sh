#!/bin/bash
set -uo pipefail

SWARM=/home/parison/trading-swarm
LOG=$SWARM/logs/integration_test.log
ENV=/home/parison/.env_trading

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting integration-test-agent" >> "$LOG"

source "$ENV" 2>/dev/null || {
    echo "ERROR: could not source $ENV" >> "$LOG"
    exit 1
}

cd "$SWARM"

bash scripts/spawn_agent.sh \
    "integration-$(date +%Y%m%d)" \
    "integration-test-agent" \
    "3" \
    "Run full integration test suite. Check all 6 suites: signal bus, agent cadence, feedback loop, registry consistency, CI pipeline, brain completeness." >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished integration-test-agent (exit: $EXIT_CODE)" >> "$LOG"
exit $EXIT_CODE
