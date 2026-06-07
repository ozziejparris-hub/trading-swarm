# Audit: Synchronous DB Calls on Event Loop — monitor.py
**Date:** 2026-05-25
**Source file:** `monitoring/monitor.py`
**Scope:** Every `async` method that calls `self.db.*` or raw `sqlite3` directly on the asyncio event loop thread, without wrapping in `run_in_executor` or `asyncio.to_thread`.

---

## Summary

| Method | Blocking calls found | Frequency |
|---|---|---|
| `check_for_new_trades` | 3 | Every cycle (15 min) |
| `notify_new_trades` | 3 | Every cycle when new trades exist |
| `update_position_tracking` | 5 | **Disabled** (commented out in `monitoring_loop`) |
| `monitoring_loop` | 2 | Every cycle / every 10 cycles |
| `start` | 1 | Once at startup |

---

## Findings

### 1. `check_for_new_trades` — defined at line 696

**Line 698** — `self.db.get_flagged_traders()`
- Called bare on the event loop; no executor wrapping.
- Frequency: **every cycle** (~15 min).

**Line 766** — `self.db.store_market_from_trade(trade, event_category=event_category)`
- Called inside a `for` loop over `relevant_trades` (up to ~500 trades/cycle).
- Frequency: **per trade, every cycle** — potentially hundreds of blocking calls per cycle.

**Line 769** — `self.db.add_trade(trade_id=..., trader_address=..., ...)`
- Immediately follows `store_market_from_trade` in the same per-trade loop.
- Frequency: **per trade, every cycle** — same volume as above.

> **Dead code (not flagged):** Lines 793 (`self.db.get_trader_rank`) and 821 (`self.db.get_trader_win_streak`) are inside `if self.elo_bot:` — `elo_bot` is hardcoded `None` at line 79, so these never execute in production.

---

### 2. `notify_new_trades` — defined at line 834

**Line 836** — `self.db.get_unnotified_trades()`
- First call in the method body, no executor.
- Frequency: **every cycle** where the caller (`monitoring_loop` line 1071) saw `new_trades > 0`.

**Line 855** — `self.db.get_trader_stats(trader)` (inside `for trader in trades_by_trader.keys()`)
- Called once per distinct flagged trader that traded this cycle.
- Frequency: **per flagged trader, every applicable cycle**.

**Line 865** — `self.db.mark_trade_notified(trade['trade_id'])` (inside `for trade in unnotified_trades`)
- Called once per unnotified trade.
- Frequency: **per trade, every applicable cycle**.

---

### 3. `update_position_tracking` — defined at line 901

> **Currently disabled:** The call site in `monitoring_loop` is entirely commented out (lines 1104–1122). This method is not reachable from the normal run path. Findings listed for completeness; they become live the moment the block is uncommented.

**Line 913** — `conn = self.db.get_connection()`
- Opens a raw SQLite connection at function entry.
- Frequency (if re-enabled): once per invocation (every cycle).

**Line 932** — `conn = self.db.get_connection()`
- Second bare connection for the whale-trader diagnostic query.
- Frequency: once per invocation.

**Line 968** — `conn = self.db.get_connection()` (inside `for batch_index, trader_address in enumerate(batch)`)
- Per-trader connection to count trades before deciding to skip.
- Frequency: once per active trader per invocation (up to ~200 traders).

**Line 999** — `self.db.insert_position(position)` (inside `for position in positions`)
- Called for every matched position.
- Frequency: per position, per active trader, per invocation.

**Line 1010** — `conn = self.db.get_connection()` (inside per-trader block, for the `UPDATE traders` statement)
- A fourth connection opened inside the same per-trader loop.
- Frequency: once per trader with closed positions.

---

### 4. `monitoring_loop` — defined at line 1054

**Lines 1086–1092** — `conn = self.db.get_connection()` + raw cursor operations
```python
conn = self.db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM markets")
total_markets = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM markets WHERE resolved = 1")
resolved_count = cursor.fetchone()[0]
conn.close()
```
- Two raw `SELECT` queries run directly on the event loop inside the `if cycle_count % 10 == 0` block.
- Frequency: **every 10 cycles** (~every 150 min).

**Line 1132** — `self._update_activity_timestamp()`
- `_update_activity_timestamp` is a **synchronous method** (no `async`). It is called bare — not via `run_in_executor`. Internally it calls `self.db.get_connection()`, runs `CREATE TABLE IF NOT EXISTS`, `INSERT OR REPLACE`, `conn.commit()`, and `conn.close()` (lines 874–898).
- This is effectively 4–5 blocking SQLite operations on the event loop thread every cycle.
- Frequency: **every cycle** (~15 min).

---

### 5. `start` — defined at line 1189

**Lines 1208–1212** — `self.db.get_connection()` + `conn.execute(...)`
```python
conn = self.db.get_connection()
flagged_count = conn.execute(
    "SELECT COUNT(*) FROM traders WHERE is_flagged = 1"
).fetchone()[0]
conn.close()
```
- Raw SQLite `SELECT` called bare on the event loop during startup.
- Frequency: **once** at service startup.

---

## Notes

- `run_in_executor` is used correctly for HTTP calls (`_refresh_event_category_map` line 132) and `initial_scan` (line 690), showing the pattern is known. It is not applied to any of the DB call sites above.
- The highest-frequency/highest-volume offenders are in `check_for_new_trades` (lines 766 and 769) — up to ~500 blocking SQLite writes per cycle with no yield between them.
- `_update_activity_timestamp` (line 1132 call site) is the only case where a *synchronous* method doing substantial DB I/O is called from an async context without a wrapper.
