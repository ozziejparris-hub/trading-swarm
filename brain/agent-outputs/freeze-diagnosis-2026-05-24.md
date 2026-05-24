# Monitoring Freeze Root Cause Diagnosis — 2026-05-24 13:46 UTC

**Files reviewed:**
- `monitoring/background_pnl_worker.py` (full)
- `monitoring/monitor.py` (lines 700–900)
- `monitoring/database.py` (full)

---

## Q1 — Does the pnl_worker properly release the SQLite connection after a timeout?

**Short answer: Partially. The asyncio timeout does NOT kill the thread, and two connection paths have no `try/finally` guard.**

When `asyncio.wait_for` raises `TimeoutError` in `_process_single_trader` (line 362–377), only the asyncio future is cancelled. The underlying thread-pool thread is **not interrupted** — Python has no mechanism to forcibly kill a running thread. The thread continues executing `_process_trader_sync` until it finishes naturally.

Inside `_process_trader_sync`, there are three distinct connection opens:

| Connection | Lines | try/finally? | Verdict |
|---|---|---|---|
| Trade count SELECT | 196–202 | **No** | Leaks if `cursor.execute` or `cursor.fetchone` raises (e.g., DB locked on reader) |
| Positions INSERT batch | 230–290 | Yes | Safe — `finally: conn.close()` always runs |
| Traders row UPDATE | 300–324 | Yes | Safe — `finally: conn.close()` always runs |

There is a fourth unguarded call in `database.py::mark_trader_pnl_updated` (lines 1119–1136):
```python
conn.commit()
conn.close()   # ← never reached if commit raises
```
No `try/finally`. If `commit()` hits "database is locked", `conn.close()` is skipped and the connection leaks.

**Effect of a leaked connection:** In WAL mode a leaked connection that held no transaction won't block writers, but it does pin a WAL reader snapshot. SQLite cannot checkpoint WAL pages needed by any open reader. As leaked connections accumulate, the WAL file grows unboundedly and all subsequent read/write latency rises — a slow-burning positive feedback loop.

---

## Q2 — Is monitor.py using WAL mode correctly; are reads and writes properly isolated?

**Short answer: WAL is configured correctly but the isolation model is broken for the main loop.**

`database.py::get_connection()` sets both `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=30000` on every connection (lines 46–51). That is correct.

However, the isolation guarantee in the pnl_worker docstring —
> "ALL SQLite I/O … runs inside a single ThreadPoolExecutor call … The asyncio event loop thread never touches SQLite directly"

— **applies only to the pnl_worker itself**. Monitor.py's async methods (`check_flagged_traders`, `notify_new_trades`, `_update_activity_timestamp`) call `self.db.*` directly and synchronously **on the event loop thread**, without offloading to an executor. Examples from the reviewed code:

- `self.db.store_market_from_trade(...)` — line 766
- `self.db.add_trade(...)` — line 769
- `self.db.mark_trade_notified(...)` — line 865
- `self.db.get_unnotified_trades()` — line 836
- Direct `conn = self.db.get_connection()` block in `_update_activity_timestamp` — line 874

Any of these calls that block (waiting for a busy lock, up to 30 seconds) will **block the entire asyncio event loop**. While the event loop is blocked, no other coroutine can run: the pnl_worker's `await asyncio.sleep(0.1)` yields cannot fire, the 15-minute monitoring cycle timer cannot tick, and the watchdog cannot signal liveness.

---

## Q3 — Can a failed pnl_worker operation leave a connection open or a transaction uncommitted?

**Yes. There are three confirmed code paths.**

### Path A — Trade count connection (pnl_worker lines 196–202)
```python
conn = self.db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM trades WHERE trader_address = ?", ...)
trade_count = cursor.fetchone()[0]
conn.close()          # ← skipped if any line above raises
```
No `try/finally`. An exception anywhere between `get_connection()` and `conn.close()` leaves the connection open. Because no write transaction was open, writers are not directly blocked, but the WAL reader pin grows.

### Path B — `mark_trader_pnl_updated` (database.py lines 1119–1136)
```python
conn = self.db.get_connection()
cursor = conn.cursor()
cursor.execute("UPDATE traders SET pnl_last_updated = ... WHERE address = ?", ...)
conn.commit()         # ← raises if DB locked
conn.close()          # ← skipped
```
If the DB is locked when this UPDATE runs (which it is, during the freeze cascade), `commit()` raises, `close()` is skipped, and the connection leaks with an uncommitted write transaction pending. This is the most dangerous path: an uncommitted write on a leaked connection can block all subsequent writers until the Python GC destroys the connection object.

### Path C — Multiple methods in database.py with the same pattern
`mark_trade_notified` (lines 311–319), `update_market` (lines 350–376), `update_market_api_id` (lines 742–758) all follow the same no-`try/finally` pattern for their `conn.commit()` / `conn.close()` tail. Under lock pressure any of these can silently leak.

---

## Q4 — Most likely sequence of events leading to the 13:46 UTC freeze

### Timeline reconstruction

```
08:41        DB locked error
             └─ First sign: the event loop made a synchronous DB write (add_trade or
                similar) while the pnl_worker thread held an open write transaction.
                SQLite busy_timeout=30s elapsed with no release → raised OperationalError.
                This 30-second block paused the ENTIRE asyncio event loop.

~13:30–13:45 Slow: 0x16c7bf49 — 425 trades took 46.3s
             └─ Large trader (likely > 100 closed positions → 180s budget, or at minimum
                close to 90s). During the 46.3s it spent in the write-positions block
                (lines 230–285), the thread held the SQLite write lock. Every concurrent
                write attempt from the event loop thread hit the 30s busy_timeout.

~13:45       Position insert failed for 0xd6b6f692
             └─ A subsequent trader's INSERT OR REPLACE batch raised an exception inside
                the positions loop (likely "database is locked" because 0x16c7bf49's
                thread held the lock). The except/finally block ran correctly — rollback +
                close — but `mark_trader_pnl_updated` was then called (line 327). That
                call's commit() also hit "DB locked", leaking the connection (Path B above)
                with an uncommitted UPDATE on the traders row.

~13:46       Timeout: 0x0296a34c exceeded 90s
             └─ This is the tipping point. Sequence:
                1. asyncio.wait_for fires — coroutine is cancelled.
                2. Thread is NOT killed; it continues executing _process_trader_sync
                   for 0x0296a34c, which is mid-transaction inserting positions.
                3. asyncio calls _record_failure (no DB write for failures < 5).
                4. asyncio moves to the next batch trader; submits it to _THREAD_POOL.
                5. _THREAD_POOL has max_workers=1 — the new trader QUEUES behind the
                   still-running 0x0296a34c thread.
                6. The new trader's asyncio.wait_for timer starts NOW (before the
                   thread is even free), compressing its actual processing budget.
                7. Meanwhile, the main monitoring loop calls _update_activity_timestamp
                   (or add_trade) synchronously on the event loop thread.
                8. SQLite busy_timeout waits 30 seconds for 0x0296a34c's write lock.
                9. Those 30 seconds block the event loop completely.

13:46 UTC    Complete freeze
             └─ After the 30s block, one of two outcomes (or both):
                A. The OperationalError propagates up and crashes the monitoring cycle
                   coroutine. No new 15-minute cycle is scheduled.
                B. The event loop resumes but 0x0296a34c is re-queued immediately
                   (pnl_last_updated was NOT stamped after timeout, by design). The
                   thread starts processing 0x0296a34c again → holds write lock again →
                   event loop blocks again → perpetual freeze loop.
                The leaked connection from Path B (uncommitted UPDATE for 0xd6b6f692)
                may have held the write lock continuously between the position insert
                failure and the garbage collector destroying it, accelerating the cascade.
```

### Root cause

**The fundamental architectural conflict is that `monitor.py`'s async methods make synchronous blocking SQLite calls on the event loop thread, while the pnl_worker's thread pool can hold write locks for 90–180 seconds.** When those two overlap, the event loop blocks for up to 30 seconds per write attempt (`busy_timeout`). A single timeout event (0x0296a34c) turned a recurring write-contention issue (present since 08:41) into a complete freeze by holding the write lock past the busy_timeout after asyncio had already moved on.

Secondary contributing factors:
1. Three unguarded connection paths (Q3 above) that leak connections under lock pressure, growing the WAL file and degrading subsequent query latency.
2. The single thread pool worker design means a timed-out thread still consuming the only worker slot delays all subsequent traders, compressing their effective budget.
3. `mark_trader_pnl_updated` has no retry or guard — under lock pressure it silently fails AND leaks a connection with an uncommitted write.

---

## Files and Line References

| Issue | File | Lines |
|---|---|---|
| Thread continues after asyncio timeout | `background_pnl_worker.py` | 362–377 |
| Trade count conn — no try/finally | `background_pnl_worker.py` | 196–202 |
| `mark_trader_pnl_updated` — no try/finally | `database.py` | 1119–1136 |
| Event loop does direct SQLite I/O | `monitor.py` | 766, 769, 836, 865, 874–896 |
| `busy_timeout=30000` setting | `database.py` | 50 |
| Single thread pool worker | `background_pnl_worker.py` | 33–35 |
| pnl_last_updated not stamped after timeout | `background_pnl_worker.py` | 370–377 (no stamp in timeout branch) |
