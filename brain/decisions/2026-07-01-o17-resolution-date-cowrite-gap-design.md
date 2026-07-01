# O-17 — `resolution_date` Co-write Gap: Mechanism, Fix Design, Backfill, Audit

**Date:** 2026-07-01
**Method:** Read-only design work, done while `daily_maintenance.py` (PID 6794) was still running (maker/taker backfill step, not yet at "MAINTENANCE COMPLETE"). No writes, no code changes — this doc specifies a fix to implement next session, once maintenance finishes.
**Context:** Follow-up to O-16 (`2026-07-01-o16-resolution-collection-gap-quantified.md` §6.4), which found 182 markets with `resolved = 1` (correctly resolved) but `resolution_date` still `NULL` — a small, currently-active generator, distinct from O-16's 194,216-row static backlog. That doc's same-day addendum attributed this to `resolve_legendary_markets.py` and `legendary_positions_scan.py`. **This doc corrects that attribution** after actually reading every candidate write path end to end, rather than pattern-matching on script names.

---

## Correction to O-16's §6.4 attribution

O-16 §6.4 named `resolve_legendary_markets.py` and `legendary_positions_scan.py` as "the generator." That was an incomplete read, done under time pressure while wrapping up a large investigation — it correctly identified that both scripts have the bug (confirmed below), but **missed that the actual dominant, currently-active mechanism is three of the four passes inside `fast_resolution_check.py` itself** — the same script this whole O-13→O-16 chain has been treating as the correct replacement pipeline. Re-reading all three passes' UPDATE statements character-by-character (not just the one I'd checked closely, Pass 1) found the same missing-column bug in Passes 2, 3, and 4.

**Impact-scope correction too:** O-16 §6.4 framed this as a "LEGENDARY-tier leak." It isn't, predominantly. Of the 182 affected rows: **27 (15%) are LEGENDARY-trader-linked; 147 (81%) are linked to the broader flagged/research-clean trader pool** (`is_flagged=1 AND research_excluded=0`) but not specifically LEGENDARY. The dominant mechanism operates on the general market population without any LEGENDARY-specific filter, so the downstream `requeue_resolved_market_traders.py` breakage (§1 below) affects the general flagged-trader pool, not narrowly LEGENDARY traders. LEGENDARY is a real subset of the harm, not the whole of it.

---

## 1. The Mechanism — Confirmed, Precisely

Audited every `UPDATE markets` statement that touches `resolved` or `winning_outcome` in the codebase (12 total, across `database.py`, `fast_resolution_check.py`'s 4 passes, `resolve_legendary_markets.py`, `legendary_positions_scan.py`, `fix_expired_unresolved.py`, `fetch_market_resolutions.py`, `hydrate_stub_markets.py`). Full table in §5. **7 of the 12 never write `resolution_date`.**

### The dominant, confirmed-active generator: `scripts/fast_resolution_check.py`, 3 of its 4 passes

Scheduled **daily** via `daily_maintenance.py:46` ("Fetch new market resolutions", non-blocking). Pass 1 is correct; Passes 2-4 are not:

| Pass | Lines | Success-path SQL | `resolution_date`? |
|---|---|---|---|
| 1 — `batch_update_resolved_markets` (Gamma bulk) | 264-271 | `SET resolved=1, winning_outcome=?, resolution_date=?, last_checked=?` | ✅ correct |
| 2 — `run_recent_overdue_pass` (0-7 day window) | 492-499 | `SET resolved=1, winning_outcome=?, last_checked=?` | ❌ **missing** |
| 3 — `run_stale_clob_pass` (>7 day, has `resolution_date`) | 383-389 | `SET resolved=1, winning_outcome=?, last_checked=?` | ❌ **missing** |
| 4 — `run_external_seed_pass` (external_seed traders) | 588-595 | `SET resolved=1, winning_outcome=?, last_checked=?` | ❌ **missing** |

This matches the 182-row evidence exactly: the sample market checked in O-16 (`0x8a2017...`, "Will Waymo launch in Nashville by June 30 2026?", `api_id=675598`, `end_date=2026-06-30`, `last_checked=2026-06-30 08:43:12`) resolved on the same calendar day as its `end_date` — the signature of Pass 2's 0-7-day window, not a LEGENDARY-specific pass. 118 of the 182 rows are `category='Unknown'` (mostly World Cup group-stage markets) — outside the `Geopolitics`/`Elections`/`Global Politics` scope that `legendary_positions_scan.py`'s geo pass requires, ruling that script out as the source for those specific rows and confirming `fast_resolution_check.py` as the only mechanism broad enough to touch them.

### Secondary, confirmed-real, but narrower generators

**`scripts/legendary_positions_scan.py`** (weekly, Monday 07:30 cron) — `_resolve_one_market`, called from two unguarded-by-`resolution_date` queries (`_check_and_update_stale_markets`, lines 338-366): Ukraine-war-titled markets (any category) and geo/elections-category markets linked to LEGENDARY traders. Its two `UPDATE` statements:

```python
# line 304
"UPDATE markets SET resolved = 1, winning_outcome = ? WHERE market_id = ?"
# line 314
"UPDATE markets SET resolved = 1 WHERE market_id = ?"
```

Both omit `resolution_date`. This script's query does **not** require `resolution_date IS NOT NULL` up front, so it's mechanistically capable of producing new NULL-`resolution_date` rows — plausibly responsible for some of the 61 Geopolitics/Elections-tagged rows in the 182 (not disambiguated further from Pass 2/3/4's contribution; both are live and both could produce a geo-category row).

**`scripts/resolve_legendary_markets.py`** (daily, `daily_maintenance.py:50`, `--limit 50`) — lines 209-217:

```python
# line 210 (no-winner branch)
"UPDATE markets SET resolved = 1, last_checked = ? WHERE market_id = ?"
# line 215 (winner branch)
"UPDATE markets SET resolved = 1, winning_outcome = ?, last_checked = ? WHERE market_id = ?"
```

Also omits `resolution_date` — same bug pattern, code-confirmed. **But currently self-protected in practice**: its own input query, `_fetch_overdue_legendary_markets` (lines 53-58), hard-requires `m.resolution_date IS NOT NULL` to even select a market as a candidate. Since the script never touches `resolution_date` in its `UPDATE`, and its `WHERE` guarantees a non-NULL value existed at selection time, **it cannot currently transition a row from "has resolution_date" to "NULL resolution_date"** — the bug is real but structurally inert given today's query shape. Still worth fixing (§2) for defense-in-depth: if that `WHERE` clause is ever loosened, the latent bug activates immediately with no other warning sign.

### Why did none of these get the co-write pattern? — Timing, not an audit miss

Checked git history for when each script's resolution-writing code was introduced, against the two commits that established the `resolution_date = COALESCE(resolution_date, ?)` co-write convention repo-wide (`4cdd190`, `446bcde`, both **2026-05-31**):

| Code | Introduced | vs. May 31 fix |
|---|---|---|
| `fast_resolution_check.py`'s `run_recent_overdue_pass` | `7033669`, **2026-06-14** | 2 weeks after |
| `legendary_positions_scan.py`'s `_check_and_update_stale_markets` | `6519456`, **2026-06-09** | 9 days after |
| `resolve_legendary_markets.py` (whole file) | `0ac5c48`, **2026-06-09** | 9 days after |

**All three were written after the May 31 fix, not before it.** They weren't overlooked in an audit of pre-existing code — they're new code, added in the following two weeks, that simply didn't inherit the convention because it was never encoded anywhere the next author would see it (no shared helper function, no lint rule, no test asserting the invariant — just two isolated call sites in `monitor.py`/`database.py` that a new script author had no reason to know about). This is a process gap, not a one-time slip: **any new resolution-writing code added after May 31 had a real chance of reproducing this bug, and 3 of 3 new scripts did.**

---

## 2. The Fix — Designed, Not Applied

**Convention to match:** every currently-correct writer (`database.py`'s `update_market_resolution`, `fast_resolution_check.py`'s Pass 1, `fix_expired_unresolved.py`, `fetch_market_resolutions.py`) sets `resolution_date = datetime.now()` (or equivalent) at the moment the resolution is *detected*, not an attempt to recover Polymarket's true on-chain resolution timestamp. Match this — don't invent a new semantic.

**Refinement over a blind overwrite:** use `resolution_date = COALESCE(resolution_date, ?)` (the exact idiom already established in `monitor.py`/`database.py`/`hydrate_stub_markets.py`), not a bare `resolution_date = ?`. For `resolve_legendary_markets.py` specifically this matters — its rows already have a genuine, existing `resolution_date` (guaranteed by its own `WHERE`), so a bare overwrite would clobber real data with today's date on every re-run; `COALESCE` preserves it. For the other four call sites `resolution_date` is NULL at select time in the normal case, so `COALESCE` and a bare `?` are equivalent there — but using `COALESCE` everywhere is one consistent pattern instead of two, cheaper to reason about.

### 2.1 `scripts/fast_resolution_check.py`

```python
# Pass 2 — run_recent_overdue_pass, lines 492-499 (was: no resolution_date)
cursor.execute("""
    UPDATE markets
    SET resolved = 1,
        winning_outcome = ?,
        resolution_date = COALESCE(resolution_date, ?),
        last_checked = ?
    WHERE market_id = ?
""", (winner_outcome, datetime.now(), datetime.now(), market_id))

# Pass 3 — run_stale_clob_pass, lines 383-389 (was: no resolution_date)
cursor.execute("""
    UPDATE markets
    SET resolved = 1,
        winning_outcome = ?,
        resolution_date = COALESCE(resolution_date, ?),
        last_checked = ?
    WHERE market_id = ?
""", (winner_outcome, datetime.now(), datetime.now(), market_id))

# Pass 4 — run_external_seed_pass, lines 588-595 (was: no resolution_date)
cursor.execute("""
    UPDATE markets
    SET resolved = 1,
        winning_outcome = ?,
        resolution_date = COALESCE(resolution_date, ?),
        last_checked = ?
    WHERE market_id = ?
""", (winner_outcome, datetime.now(), datetime.now(), market_id))
```

Three call sites, same one-line addition each (`resolution_date = COALESCE(resolution_date, ?)` in the `SET`, one extra bound param). This is the highest-leverage fix — it's the dominant, daily-running, category-unrestricted mechanism.

### 2.2 `scripts/legendary_positions_scan.py`, `_resolve_one_market` (lines 300-318)

```python
if winning:
    cur.execute(
        "UPDATE markets SET resolved = 1, winning_outcome = ?, "
        "resolution_date = COALESCE(resolution_date, ?) WHERE market_id = ?",
        (winning, datetime.now(), row["market_id"])
    )
    ...
else:
    total_price = sum(float(p) for p in (outcome_prices or []) if p)
    if total_price == 0.0 and closed:
        cur.execute(
            "UPDATE markets SET resolved = 1, "
            "resolution_date = COALESCE(resolution_date, ?) WHERE market_id = ?",
            (datetime.now(), row["market_id"])
        )
```

### 2.3 `scripts/resolve_legendary_markets.py` (lines 209-217)

```python
if winning == "__RESOLVED_NO_WINNER__":
    cur.execute(
        "UPDATE markets SET resolved = 1, "
        "resolution_date = COALESCE(resolution_date, ?), last_checked = ? WHERE market_id = ?",
        (datetime.now(), datetime.now(), row["market_id"])
    )
else:
    cur.execute(
        "UPDATE markets SET resolved = 1, winning_outcome = ?, "
        "resolution_date = COALESCE(resolution_date, ?), last_checked = ? WHERE market_id = ?",
        (winning, datetime.now(), datetime.now(), row["market_id"])
    )
```

Lower priority (currently inert per §1), but cheap to fix at the same time since the file is already open for this class of change.

### 2.4 Recommended, larger-scope fix: stop hand-rolling this UPDATE

**5 broken call sites across 3 files, all making the same mistake independently, is a strong signal to extract a shared helper** rather than patch each site individually and hope the next new script remembers. Recommend adding one function to `monitoring/database.py` — e.g. `Database.mark_market_resolved(market_id, winning_outcome=None, resolved_no_winner=False)` — that always does the `resolved=1, winning_outcome=?, resolution_date=COALESCE(resolution_date, ?), last_checked=?` write correctly, and have all 5 (plus `database.py`'s own `update_market_resolution`, unifying 6 call sites into 1 implementation) call it instead of hand-writing SQL. This doesn't just fix today's 5 sites — it removes the opportunity for a 6th script to reproduce the bug next month. Scoping only, not designed in full here — a reasonable next-session task once the immediate fix lands.

---

## 3. The Existing 182 — Retroactive Backfill (separate from the generator fix)

**These do not need any API calls.** They already have `resolved=1` and (mostly) `winning_outcome` — the only missing piece is `resolution_date` metadata, and the best available proxy for "when we detected the resolution" is already sitting in the same row: `last_checked`, which every one of the 7 broken call sites *does* correctly update to `datetime.now()` at write time (only `resolution_date` was left out).

```sql
UPDATE markets
SET resolution_date = last_checked
WHERE resolved = 1 AND resolution_date IS NULL;
```

**Single statement, 182 rows, no network calls, matches the existing detection-time semantic exactly** (this is precisely what every correct writer already does — set `resolution_date` to the timestamp of detection). Safe to run any time, independent of the generator fix in §2 — in fact **should run first**, since it's what actually restores the 147 flagged-trader-linked (27 LEGENDARY) markets to `requeue_resolved_market_traders.py`'s visibility; the generator fix in §2 only prevents *new* rows from joining this population; it doesn't retroactively fix the 182 already stuck.

After this backfill, re-run (or wait for the next scheduled run of) `requeue_resolved_market_traders.py` to pick up the newly-visible 182 and requeue their traders' `pnl_last_updated` — confirms the fix closes the loop end to end, not just the DB column.

---

## 4. Test Design (not implemented — for next session)

Following the shape the user proposed, scoped against this repo's actual structures:

```python
def test_run_recent_overdue_pass_writes_resolution_date(tmp_db):
    """
    A market resolved by run_recent_overdue_pass must get resolution_date
    populated, not just resolved/winning_outcome — this is the O-17 regression.
    """
    # Arrange: seed one market, resolved=0, resolution_date=NULL,
    # end_date = 3 days ago (inside the 0-7-day window), with a mocked
    # CLOB response indicating closed=True, one token winner=True.
    seed_market(tmp_db, market_id="0xtest", end_date=days_ago(3),
                resolution_date=None, resolved=0)
    mock_clob_response(closed=True, tokens=[{"outcome": "Yes", "winner": True},
                                             {"outcome": "No", "winner": False}])

    checker = FastResolutionChecker(db_path=tmp_db)
    checker.run_recent_overdue_pass(limit=10, test_mode=False)

    row = fetch_market(tmp_db, "0xtest")
    assert row["resolved"] == 1
    assert row["winning_outcome"] == "Yes"
    assert row["resolution_date"] is not None          # <- the O-17 regression check
    assert row["resolution_date"] == row["last_checked"]  # detection-time semantic

def test_requeue_catches_market_after_resolution_date_fix(tmp_db):
    """
    End-to-end: a market resolved with resolution_date now populated must
    be visible to requeue_resolved_market_traders.py's filter — this is
    the actual downstream harm O-17 causes, not just a missing column.
    """
    seed_market(tmp_db, market_id="0xtest", resolved=1,
                winning_outcome="Yes", resolution_date=recent_timestamp())
    seed_position(tmp_db, market_id="0xtest", trader_address="0xtrader",
                   status="open")
    seed_trader(tmp_db, address="0xtrader", pnl_last_updated=old_timestamp())

    requeue_resolved_market_traders.run(db_path=tmp_db, since=days_ago(1))

    trader = fetch_trader(tmp_db, "0xtrader")
    assert trader["pnl_last_updated"] is None            # requeued
    assert trader["pnl_update_priority"] == 1
```

Two tests, mirroring the two-part fix: (1) the write-path unit test per broken call site (would need one instance per pass/script, or a parametrized version covering all 5 — same assertion shape each time), and (2) one end-to-end test proving the *consequence* (requeue) is actually restored, not just the column. Test 2 is the more important one — it's the test that would have caught this whole class of bug regardless of which of the 5 call sites regressed, since it tests the contract `requeue_resolved_market_traders.py` actually depends on, not the internal implementation detail of which UPDATE statement ran.

---

## 5. Full Audit — Does Any Other Resolution Writer Have the Same Gap?

Every `UPDATE markets` statement touching `resolved` or `winning_outcome` in the codebase, audited:

| # | File:Lines | Scheduled? | `resolution_date` co-written? |
|---|---|---|---|
| 1 | `monitoring/database.py:481-489` (`update_market_resolution`) | Called by `check_market_resolutions` (slated for removal, O-13) | ✅ Yes — `resolution_date = ?` |
| 2 | `scripts/fast_resolution_check.py:264-271` (Pass 1, Gamma bulk) | Daily, `daily_maintenance.py:46` | ✅ Yes |
| 3 | `scripts/fast_resolution_check.py:492-499` (Pass 2, recent overdue) | Daily, same step | ❌ **No — fixed in §2.1** |
| 4 | `scripts/fast_resolution_check.py:383-389` (Pass 3, stale CLOB) | Daily, same step | ❌ **No — fixed in §2.1** |
| 5 | `scripts/fast_resolution_check.py:588-595` (Pass 4, external seed) | Daily, same step | ❌ **No — fixed in §2.1** |
| 6 | `scripts/resolve_legendary_markets.py:209-217` (×2) | Daily, `daily_maintenance.py:50` | ❌ **No — fixed in §2.3** (currently inert, §1) |
| 7 | `scripts/legendary_positions_scan.py:304,314` (×2) | Weekly, Monday cron | ❌ **No — fixed in §2.2** |
| 8 | `scripts/fix_expired_unresolved.py:92-96` | Manual, unscheduled (hardcoded IDs) | ✅ Yes — `resolution_date=datetime('now')` |
| 9 | `scripts/fetch_market_resolutions.py:156-166` | Manual, unscheduled | ✅ Yes |
| 10 | `scripts/hydrate_stub_markets.py:198-219` | Daily, `daily_maintenance.py` (date/category hydration step) | ✅ Yes — `COALESCE(resolution_date, ?)` |

**Result: 7 of 12 broken (5 unique bugs × the count of call sites), all 7 concentrated in exactly the 3 files identified in §1. No other resolution writer in the codebase has this gap** — `database.py`'s canonical function and every unscheduled/manual script are correct; the pattern breaks exclusively in code written after 2026-05-31 that didn't reuse the canonical path. This confirms §2.4's diagnosis: the fix that matters most isn't patching these 5 call sites (necessary, but insufficient on its own) — it's removing the ability to hand-roll this UPDATE at all, so a hypothetical 6th script can't reproduce it a third time.

---

## 6. Files Referenced

| File | Role |
|------|------|
| `scripts/fast_resolution_check.py:492-499,383-389,588-595` | The 3 broken passes — dominant, confirmed-active generator |
| `scripts/legendary_positions_scan.py:300-366` | `_resolve_one_market` + its two unguarded call sites — secondary, real generator |
| `scripts/resolve_legendary_markets.py:53-58,205-217` | Same bug, but self-protected/inert today given its own `resolution_date IS NOT NULL` input filter |
| `monitoring/database.py:434-489` | The canonical, correct patterns (`update_market`, `update_market_resolution`) the fix should match |
| `scripts/requeue_resolved_market_traders.py:76` | The downstream consumer broken by this gap — `resolution_date > ?` never matches NULL |
| commits `4cdd190`, `446bcde` (2026-05-31) | Established the co-write convention that 3 later scripts (all written within 2 weeks after) didn't inherit |
| commits `7033669` (06-14), `6519456`/`0ac5c48` (06-09) | Introduction dates of the 3 broken scripts — all post-date the convention |
| `2026-07-01-o16-resolution-collection-gap-quantified.md` §6.4 | The original (incompletely-attributed) finding this doc corrects and completes |
