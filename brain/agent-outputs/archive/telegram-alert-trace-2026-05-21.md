# Telegram Alert Trace — LEGENDARY / ELITE NEW POSITION
**Date:** 2026-05-21  
**Scope:** Read-only audit. No files were modified.

---

## 1. Exact Source of the Alert

**File:** `monitoring/system_observer.py`  
**Function:** `_check_legendary_trades()` — defined at **line 1168**  
**Message constructed:** lines **1275–1291**  
**Message sent:** line **1293** — `await self.telegram._send_message(message)`

The message template (line 1275–1291):
```
{tier_icon} {tier_badge} TRADER — NEW POSITION

Trader: {trader_display}
ELO: {elo_str}  |  Tier: {tier_badge}

📊 Track Record
   Closed Positions: {n_closed}
   Avg ROI: {roi_str}
   Realized P&L: {pnl_str}

🎯 New Trade
   Market: {market_str}
   Outcome: {outcome}
   Price: ${price:.4f}
   Shares: {shares:,.0f}
   Size: ${size:,.2f}

⏰ {timestamp}

🔗 https://polymarket.com/profile/{address}
```

`tier_badge` is `"LEGENDARY"` (ELO ≥ 2500, line 1235) or `"ELITE"` (ELO 2000–2499, line 1238).  
`"Track Record"` appears at line 1279.

---

## 2. What Triggers the Function

`_check_legendary_trades()` is called from **`_hourly_report_loop()`**, launched as a background asyncio task at observer startup (line 138). The call site is **line 452**:

```python
# DISABLED 2026-05-20 — pre-Phase 5, not actioning individual trade alerts
# await self._check_legendary_trades()
```

The function uses a **48-hour lookback window** (line 1181):
```python
cutoff = datetime.now() - timedelta(hours=48)
```

Deduplication is via `self._alerted_legendary_trades` — an **in-memory set** on the observer instance (line 1304–1306). It is not persisted to the database.

---

## 3. Why the 2026-05-20 Disable Did Not Stop the Alerts

### Root cause: service not restarted after the code change

| Event | Timestamp (UTC) |
|-------|----------------|
| Observer process PID 1173 started | **2026-05-20 18:25:46** |
| Disable commit `65deb21` pushed | **2026-05-20 20:28:26** |
| Gap | **+2 hours 3 minutes** |

The `polymarket-observer` process (PID 1173, confirmed via `ps aux` and `/proc/1173`) was started **2 hours before** the disable commit was applied to disk. Python loads source files once at import time — editing `.py` files on disk has no effect on an already-running process. The service was never restarted after the commit.

The running process is executing the **pre-disable version** of `_hourly_report_loop`, which still calls `await self._check_legendary_trades()` every hour.

### Secondary issue: in-memory dedup resets on restart

Even if the service is restarted now to pick up the commented-out code, the `_alerted_legendary_trades` set will be empty. With the 48-hour lookback, every trade from the past two days that hasn't been seen by the new process would fire an alert on the first hourly tick after restart. This is a separate problem from the root cause above, but worth noting before restarting.

---

## 4. Other Alert Paths Checked and Ruled Out

| File | Finding |
|------|---------|
| `telegram_elo_bot.py` | Contains `"ELITE TRADER ALERT"` format (line 176) and `send_elite_trader_alert()` (line 148), but **not** the `"LEGENDARY TRADER — NEW POSITION"` / `"Track Record"` format. Not connected to the active alert path. |
| `telegram_health_bot.py` | Line 803: `"ELITE TRADER CONSENSUS"` — a different format for consensus signals, not individual position alerts. |
| `monitoring/monitor.py` | No matches for LEGENDARY, ELITE, NEW POSITION, or Track Record. |
| `monitoring/telegram_bot.py` | No matches. |
| `scripts/pre_resolution_intelligence.py` | Uses `LEGENDARY`/`ELITE` tier labels internally (lines 58, 262) but sends a completely different alert format via `TelegramHealthBot`. Not the source. |
| `analysis/unified_elo_system.py` | Single mention of "LEGENDARY ROI" in a comment (line 3794). Not an alert. |
| `_check_consensus_positions()` | Still active in `_hourly_report_loop` (line 455). Sends `"CONSENSUS SIGNAL — N ELITE TRADERS"` format (line 1765) — a different message type, not individual position alerts. |

---

## 5. Fix Required

Restart `polymarket-observer` to load the current on-disk code:

```bash
sudo systemctl restart polymarket-observer
```

**Warning before restarting:** The 48-hour lookback + in-memory dedup means the first hourly tick after restart will query all trades from the past 48 hours and send alerts for any trade_id not yet in the new process's `_alerted_legendary_trades` set. Since the function will be commented out in the restarted process, this is moot — but it confirms the disable will only take effect after restart.
