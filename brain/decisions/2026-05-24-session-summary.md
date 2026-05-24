# Session: Server Setup 10 — 2026-05-24

### What was built

1. Backfill stall spam eliminated
   - background_backfill_worker.py: when consecutive_empty >= 20, now checks 
     pending count first
   - If pending_count == 0: logs "Backfill complete — queue empty, worker idle" 
     at DEBUG (was WARNING)
   - If pending_count > 0: logs stall warning at DEBUG (was WARNING)
   - Was generating ~130 noise messages per day, now silent
   - Committed and pushed to first-repo

2. Monitoring freeze root cause diagnosed and partially fixed
   - Two 2-hour freezes this week (May 22 21:07, May 24 13:46)
   - Root cause: background_pnl_worker times out on whale trader → position 
     insert fails → mark_trader_pnl_updated's commit() raises DB locked → 
     conn.close() skipped → connection leaks with uncommitted write transaction 
     → blocks all subsequent writers → monitor.py's synchronous DB calls on 
     event loop thread block for 30s → event loop frozen → full monitoring freeze
   - Fix 1 applied: 7 functions in database.py now have try/finally around 
     commit/close pairs — conn.close() guaranteed even if commit() raises
     Functions fixed: init_database, add_or_update_trader, mark_trade_notified,
     update_market, update_market_resolution, update_trade_result, 
     mark_trader_pnl_updated
   - Diagnosis written: brain/agent-outputs/freeze-diagnosis-2026-05-24.md
   - Service restarted at 20:51 UTC, pushed to first-repo

3. System health observations
   - Monitored pool grown to 11,975 traders (was 7,900 two weeks ago, +51%)
   - Sunday maintenance now takes 7.4 hours (leaderboard discovery 6.3h)
   - ELO behavioral coverage 11.8% (961/11,975) — data maturity issue, passive fix
   - Duplicate trades warning: 8,988 detected — flagged for future investigation
   - Top 5 ELO jumped from ~3,300 to ~4,655 after Sunday leaderboard discovery

### Key decisions
- Fix 1 only tonight — database.py connection leaks. Low risk, no logic changes
- Fix 2 deferred (moving monitor.py synchronous DB calls to executor) — bigger 
  architectural change, needs its own session
- Monitor overnight: if freeze recurs, Fix 2 is next. If clean, Fix 1 was primary cause
- Pool size growth (11,975) needs quality threshold pruning — future session

### Next session priorities
1. Check overnight — did the freeze recur? If yes, implement Fix 2 immediately
2. Fix 2: move monitor.py synchronous DB calls off event loop thread (run_in_executor)
3. Investigate 8,988 duplicate trades warning
4. Pool pruning strategy — 11,975 traders is too many, need quality threshold
5. June 1 — RQ1.1 rerun (pre-registered, Phase 5 gate, 8 days away)
