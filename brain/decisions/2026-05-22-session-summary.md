# Session Summary: Server Setup 9 — 2026-05-22

## What Was Built

### 1. Telegram Alerts Fully Fixed
- Root cause confirmed: observer process loaded pre-fix code at startup 2 hours before the disable commit — restarting polymarket-observer loaded the corrected code
- All LEGENDARY and ELITE individual trader alerts now confirmed disabled

### 2. spawn_agent.sh Token Consumption Fix
- Root cause: 565-line model-routing.md was injected into every Tier 3 agent prompt (~8,000 tokens wasted before agent saw any task)
- Fix: replaced full model-routing.md cat with single interpolated line
- Confirmed working: backtest-lh001-v4 produced full output after fix
- Remaining usage (18-49%) is acceptable — agent is doing real work

### 3. LH-001 Backtest Validation Confirmed via spawn_agent.sh
- Independent DB rerun confirms CONDITIONAL_PASS verdict from yesterday's CC validation
- p=0.0067 not reproducible — correct pooled p=0.0160
- Haley-only p=0.1087 (not significant), Iran-only p=0.4818 (not significant)
- Iran market excluded (data quality)
- N=2 events insufficient, per-event power 25-35%
- Validation path: track 7 existing insider_signals detections to resolution
- Output: brain/agent-outputs/backtest-agent/LH-001-validation-v2.md

## Key Decisions
- Do not rebuild lifecycle heuristic infrastructure — insider_signals already covers it
- spawn_agent.sh model-routing.md injection removed permanently
- backtest-agent.md template confirmed loading correctly via fallback path
- LH-001 CONDITIONAL_PASS is now doubly confirmed (CC + agent)

## Next Session Priorities
1. June 1 — RQ1.1 rerun (pre-registered, Phase 5 gate)
2. Track insider_signals 7 detections to resolution (passive, ongoing)
3. ~June 2026 — Putin invasion signal resolves (first STR-003 resolution)
4. Consider adding 0xa8ad...dab1 to bot exclusion list (Bitcoin 5-minute arb bot, ELO 3300)
