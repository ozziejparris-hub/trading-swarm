# Session: Server Setup 16 — 2026-05-31

### What was built

1. Sunday WAL lock cascade — root cause fixed
   - Sunday ELO recalculation moved to dedicated systemd timer (03:00 UTC)
   - deploy/polymarket-sunday-elo.service + .timer installed
   - WAL checkpoint added as final daily_maintenance step
   - Write batching: commit every 500 traders in ELO recalc
   - Prevents DB lock cascade that caused 130+ errors/hour this morning

2. STR-003 signal registration — automated outcome scoring
   - 4 active signals registered in signals.json under str003_signals key
   - STR003-003 (Fed chair/Warsh) outcome recorded: WRONG (resolved April 4)
   - Putin/Newsom end_dates manually set (legacy markets, no API path)
   - score_str003_signals.py updated to handle flat signal format
   - signal-agent template: mandatory registration block added

3. Market end_date infrastructure
   - CLOB API integration: get_clob_market_end_date() in polymarket_client.py
   - monitor.py: _backfill_clob_end_dates() called each trade cycle
   - backfill_market_dates.py: Strategy 0 uses CLOB API first
   - daily_maintenance: backfill_market_dates.py --geo-only --limit 500

4. Comprehensive ELO inflation fix
   - Root cause: ROI-based actual_score gave massive ELO to lucky low-price wins
   - Fix 1: apply_full_elo_modifiers.py — bonus multipliers gated on resolved_trades_count >= 10
   - Fix 2: elo_bridge.py — comprehensive_elo capped at 1500 + (resolved_trades_count × 150)
   - Fix 3: elo_bridge.py — leaderboard query requires resolved_trades_count >= 5
   - Fix 4: unified_elo_system.py — per-step soft cap during category ELO update
   - Fix 5: update_geo_elo.py — per-step soft cap during geo_elo loop
   - Result: 206 traders above ELO 3,500 → 2 traders. Max ELO 5,115 → 3,919
   - Problem trader (4 resolved trades) dropped from 5,115 → 1,950 (correct)
   - geo_elo unchanged — high scores legitimate (1,900+ resolved geo trades)

5. Polygon event scanner — targeted block scanning
   - Scans only trader's actual activity window from DB timestamps
   - V2 skipped for traders active before April 28, 2026
   - Adaptive chunking for query timeouts
   - Full LEGENDARY tier scan running in background (~19 hours total)

### Key decisions
- comprehensive_elo cap: 1500 + (resolved_trades_count × 150)
- geo_elo cap: same formula, per-step during loop
- Only 2 traders legitimately above ELO 3,500 after fix
- Legendary scan overnight — review results tomorrow
- Signal 3 (Fed/Warsh) WRONG — first real STR-003 data point (0/1 accuracy)
- Putin market resolves June 30 — monitored, end_date set

### Next session priorities
1. Review legendary scan results (maker/taker labels)
2. Run update_geo_elo.py after scan completes to incorporate new data
3. Performance analyst agent — review May 25 missing report (why no run?)
4. Kalshi integration research
5. June 1: RQ1.1 self-halts at n<30 — no action needed
6. June 1 08:00: signal-agent first run with new geo_elo filters
