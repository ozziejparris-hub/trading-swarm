# Telegram Notification Audit — 2026-05-20

**Scope:** All Telegram notification sources across first-repo (monitoring/system_observer) and trading-swarm (orchestrator, scripts).  
**Method:** Static code read — no changes made.  
**Date:** 2026-05-20

---

## Bot / Channel Inventory

| Env Var | Used By | Status |
|---------|---------|--------|
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | first-repo `TelegramHealthBot` (system_observer.py) | **Active** |
| `TELEGRAM_ORCHESTRATOR_TOKEN` + `TELEGRAM_CHAT_ID` | trading-swarm orchestrator.py — critical system events | **Active (orchestrator not started yet)** |
| `TELEGRAM_AGENTS_TOKEN` + `TELEGRAM_CHAT_ID` | trading-swarm orchestrator.py (agent events) + scripts/ | **Active** |
| `TELEGRAM_METRICS_TOKEN` + `TELEGRAM_CHAT_ID` | trading-swarm orchestrator.py `send_weekly_metrics()` | **Dead — function returns immediately (disabled)** |

All bots send to the same `TELEGRAM_CHAT_ID`. There are effectively **3 active bot tokens** creating **3 message streams** into one chat.

---

## Dead Code (Never Fires in Current Deployment)

The following are defined but **never instantiated** because `monitor.py` hard-codes `self.elo_bot = None`:

- `ELOTelegramBot.send_elite_trader_alert()` / `send_contrarian_alert()` / `send_large_position_alert()` / `send_win_streak_alert()` / `send_market_momentum_alert()` / `send_daily_leaderboard()` — all in `telegram_elo_bot.py`
- `TelegramScheduler.schedule_daily_leaderboard()` — in `telegram_scheduler.py`
- `send_weekly_metrics()` in orchestrator.py — explicitly disabled (function returns immediately)

These are safe to ignore. Observer's `_send_elo_update_notification()` is also unreachable since `_elo_update_loop` no longer calls `_run_elo_integration()`.

---

## Notification Table

### A. first-repo System Observer (via `TELEGRAM_BOT_TOKEN`)

All sent by `TelegramHealthBot._send_message()` in `system_observer.py`.

| Notification Type | Trigger Condition | Bot | Noise/Signal | Recommended Action |
|---|---|---|---|---|
| Observer startup | System observer process starts | `TELEGRAM_BOT_TOKEN` | Noise | Keep — confirms service is up |
| Observer shutdown | Graceful shutdown signal | `TELEGRAM_BOT_TOKEN` | Noise | Keep — confirms clean stop |
| System health alert (warning) | Health check != healthy; rate-limited 10 min | `TELEGRAM_BOT_TOKEN` | Signal | Keep — degraded but not critical |
| System health alert (critical) | Health check == critical; rate-limited 10 min | `TELEGRAM_BOT_TOKEN` | Signal | Keep — immediate attention needed |
| Detailed error alert | New error in monitoring.log (post-observer-start); rate-limited 10 min per error signature | `TELEGRAM_BOT_TOKEN` | Mixed | **Review rate limit** — if error rate is high this becomes noisy; consider raising cooldown to 30 min |
| Known issue alert | Log monitor detects known issue pattern; rate-limited 15 min per type | `TELEGRAM_BOT_TOKEN` | Signal | Keep |
| Monitoring freeze alert | monitoring_activity > 60 min detected in hourly report; rate-limited 20 min | `TELEGRAM_BOT_TOKEN` | Signal | Keep — precedes auto-restart attempt |
| Monitoring auto-restart: attempt | Monitoring dead confirmed on 2nd health check cycle | `TELEGRAM_BOT_TOKEN` | Signal | Keep — confirms autonomous action taken |
| Monitoring auto-restart: still down | Restart attempted but process did not come back | `TELEGRAM_BOT_TOKEN` | Signal | Keep — requires manual intervention |
| Hourly status report | Every 60 min; includes health, top-5 ELO, P&L coverage, worker health, errors | `TELEGRAM_BOT_TOKEN` | Mixed | **Reduce to every 2h** once system is stable — currently generates ~24 messages/day of largely identical data |
| High-value trade alert | ELO ≥ 1550 trader, trade size ≥ $1,000, within last 30 min; deduplicated by trade_id | `TELEGRAM_BOT_TOKEN` | Signal | Keep — core trading intelligence |
| Legendary/Elite/Watched trade alert | ELO ≥ 2000 or `watched = 1`; 48h lookback, hourly; deduplicated by trade_id | `TELEGRAM_BOT_TOKEN` | Signal | Keep — highest-value signal |
| Consensus signal | 3+ traders ELO ≥ 1550, same outcome, ≥1 trade within 24h; up to 5 per run; hourly | `TELEGRAM_BOT_TOKEN` | Signal | Keep — directly supports RQ3.2 hypothesis |
| Consensus exit alert | 2+ elite sellers (ELO ≥ 1550) within 6h, same market/outcome; hourly | `TELEGRAM_BOT_TOKEN` | Signal | Keep — exit signals are actionable |
| Pre-resolution intelligence | Daily 08:00 UTC; markets resolving within 7 days, smart-money divergence | `TELEGRAM_BOT_TOKEN` | Signal | Keep — directly supports STR-002 strategy |
| Trend alert | Every 6h; elite agreement ≥ 70% OR volume spike ≥ 3x; max 5 per run | `TELEGRAM_BOT_TOKEN` | Signal | Keep — but monitor for over-alerting pre-Phase 5 with thin data |
| Daily analysis summary | Daily 01:00 UTC (skips correlation); 8 analysis tools run | `TELEGRAM_BOT_TOKEN` | Signal | Keep — but will say "insufficient data" until ~Phase 3 |
| Correlation matrix update confirmation | Daily 03:00 UTC | `TELEGRAM_BOT_TOKEN` | Noise | **Remove or silence** — a one-line operational ping that adds no decision value |
| Daily report | Daily 23:00 UTC; top 10 traders, winners/losers, best trade, system stats | `TELEGRAM_BOT_TOKEN` | Signal | Keep — useful daily digest |
| Weekly performance summary | Sunday 20:00 UTC; top trader, hot markets, opportunities, consensuses | `TELEGRAM_BOT_TOKEN` | Signal | Keep — highest-value periodic report |
| Comprehensive diagnostic report | Every 6h (first report after 1h uptime); ELO coverage, DB size, data age | `TELEGRAM_BOT_TOKEN` | Mixed | **Suppress if HEALTHY** — only send if WARNING or CRITICAL; currently sends even when all green |
| Critical system diagnostic alert | Companion to diagnostic if `overall_status == CRITICAL` | `TELEGRAM_BOT_TOKEN` | Signal | Keep |
| ELO staleness warning | ELO > 7 days stale; rate-limited 6h per severity | `TELEGRAM_BOT_TOKEN` | Signal | Keep |
| ELO staleness critical | ELO > 14 days stale; rate-limited 6h | `TELEGRAM_BOT_TOKEN` | Signal | Keep |
| Insider individual signal | Fresh wallet + large bet + low-odds + single market; 2h lookback every 15 min | `TELEGRAM_BOT_TOKEN` | Signal | Keep — high alpha potential |
| Insider cluster signal | 3+ fresh wallets, same outcome, same market, within 6h | `TELEGRAM_BOT_TOKEN` | Signal | Keep — strongest insider pattern |

---

### B. trading-swarm Orchestrator — Critical Channel (via `TELEGRAM_ORCHESTRATOR_TOKEN`)

Sent by `orchestrator.py:send_telegram(..., bot="orchestrator")`. Orchestrator is **not yet running** (service not started).

| Notification Type | Trigger Condition | Bot | Noise/Signal | Recommended Action |
|---|---|---|---|---|
| Orchestrator startup | orchestrator.py process starts | Orchestrator | Noise | Keep — operational confirmation |
| Orchestrator cycle error | Unexpected exception in `run_cycle()`; continues on next cycle | Orchestrator | Signal | Keep — unhandled errors need investigation |
| Agent failed (max retries) | Agent tmux session died MAX_RETRIES (3) times | Orchestrator | Signal | Keep — requires manual review |
| Agent timeout warning | Agent running > MAX_AGENT_RUNTIME_HOURS | Orchestrator | Signal | Keep — likely stuck |
| STR-001 HIGH confidence signal | `elite_convergence_detected` signal, HIGH confidence only | Orchestrator | Noise | **STR-001 is SUSPENDED** — this handler fires dead signals; add a guard to drop it until STR-001 is reactivated |
| STR-003 HIGH confidence signal | `str003_directional_*` signal, HIGH confidence only | Orchestrator | Signal | Keep — this is the active trading signal path |
| Backtest passed | `validation_completed` with `verdict == pass` | Orchestrator | Signal | Keep — Phase 5 gate progress |
| New connector ready | `connector_ready` signal | Orchestrator | Noise | Low priority pre-live; keep for now |
| Clarification needed | Agent signals `clarification_needed` | Orchestrator | Signal | Keep — requires human response |
| Knowledge gap critical | training-librarian flags critical gap | Orchestrator | Signal | Keep — gated, no auto-spawn |
| Hypothesis ready | quant-research pre-registration needed | Orchestrator | Signal | Keep — approval required before experiment |
| Unhandled signal type | Unknown signal type received | Orchestrator | Signal | Keep — indicates code gap |

---

### C. trading-swarm Orchestrator — Agents Channel (via `TELEGRAM_AGENTS_TOKEN`)

Lower-priority events not requiring immediate action.

| Notification Type | Trigger Condition | Bot | Noise/Signal | Recommended Action |
|---|---|---|---|---|
| Agent auto-respawn | Session died, respawn attempt 1–2 of 3 | Agents | Mixed | **Silence unless retries ≥ 2** — retry 1 is expected noise; only alert when escalating |
| STR-003 MEDIUM confidence signal | `str003_directional_*`, non-HIGH confidence | Agents | Noise | **Suppress until Phase 5** — MEDIUM signals are not actionable before validation gates pass; log to file instead |
| Validation requested | quant-research ready for backtest | Agents | Noise | Operational plumbing — keep at low volume |
| Backtest failed | `validation_completed` with fail verdict | Agents | Signal | Keep — research loop feedback |
| Strategy revalidation requested | feedback-loop signals overdue strategy | Agents | Signal | Keep — triggers maintenance cycle |

---

### D. trading-swarm Scripts (via `TELEGRAM_AGENTS_TOKEN`)

| Notification Type | Trigger Condition | Bot | Noise/Signal | Recommended Action |
|---|---|---|---|---|
| Polymarket changelog: no change | Weekly cron run, no new entries detected | Agents | **Noise** | **Remove** — weekly confirmation that nothing happened adds no value; log to file only |
| Polymarket changelog: new entry | New entry detected in Polymarket changelog | Agents | Signal | Keep — potential API breaking change |
| Gamma API filter recovery | Filter status transitions BROKEN → OK | Agents | Signal | Keep — rare but important |
| feedback-loop-agent weekly run | Weekly audit complete; markets reviewed, accuracy, new findings | Agents | Signal | Keep — Phase 5 gate progress |

---

## Summary: Noise Reduction Recommendations

| Priority | Recommendation | Estimated Impact |
|---|---|---|
| High | **Remove** changelog weekly no-change ping | Eliminates 1 noise message/week |
| High | **Suppress** STR-003 MEDIUM signals until Phase 5 | Removes clutter on agents channel before live trading |
| High | **Drop** STR-001 elite_convergence_detected handler (STR-001 suspended) | Prevents spurious signals on orchestrator channel |
| Medium | **Raise** hourly status report to every 2h once system stable | Cuts observer messages from ~24/day to ~12/day |
| Medium | **Suppress** comprehensive diagnostic report when status is HEALTHY | Removes 2–4 noise messages/day |
| Medium | **Silence** agent respawn alert on first attempt (retry 1 of 3) | Reduces expected noise from transient session deaths |
| Low | **Remove** correlation matrix confirmation ping (03:00 UTC) | Removes 1 operational noise message/day |

**Net effect:** Approximately 30–40% reduction in daily message volume with no loss of actionable signal.

---

## Files Audited

- `~/projects/first-repo/monitoring/telegram_bot.py` — TelegramNotifier (unused in production)
- `~/projects/first-repo/monitoring/monitor.py` — PolymarketMonitor (Telegram disabled by design)
- `~/projects/first-repo/monitoring/system_observer.py` — SystemObserver + all notification loops
- `~/projects/first-repo/monitoring/telegram_elo_bot.py` — ELOTelegramBot (dead code, elo_bot = None)
- `~/projects/first-repo/monitoring/telegram_health_bot.py` — TelegramHealthBot (active)
- `~/projects/first-repo/monitoring/telegram_scheduler.py` — TelegramScheduler (dead code)
- `~/projects/first-repo/monitoring/main_telegram_safe.py` — entry point (no Telegram)
- `~/trading-swarm/orchestrator/orchestrator.py` — send_telegram() calls throughout
- `~/trading-swarm/scripts/polymarket_changelog_monitor.py` — 3 notification types
- `~/trading-swarm/scripts/run_feedback_loop_agent.py` — 1 notification type
