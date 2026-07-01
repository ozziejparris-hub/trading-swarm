# O-13 Monitoring Blocking-Call Stall — Design Doc
**Date:** 2026-07-01
**Scope:** `monitoring/trader_analyzer.py:check_market_resolutions()` and its call site `monitoring/monitor.py:1261` (first-repo)
**Purpose:** Design input for next-session implementation. Read-only investigation — no code or DB changes made.
**Status:** Investigation complete, including a removal-safety checklist (§5b) verifying the duplication claim rather than assuming it. Recommendation: **remove**, not async-ify (see §4/§5). One open item before deleting: §5b's 724-market spot-check.

---

## 0. Executive Summary

`check_market_resolutions()` is a synchronous, per-market HTTP-polling resolution scan called directly (no executor, no yield) from the async `monitoring_loop`. Every ~2.5 hours it blocks the entire event loop — including the watchdog — for what is now an estimated **~10.4 hours per full scan**, an 82% duty-cycle stall. That alone would justify an async fix (Option A/B in §4).

But deeper investigation shows the function is not just slow — **it is dead weight**: 78% of its scan scope is markets with no `api_id`/`condition_id` (the O-12 unroutable class) that provably return "no data" from the Gamma API every single time, and **100% of its 21 completed runs in the retained journal (May 21 – Jun 5) resolved zero markets** (`Markets updated in database: 0`, every time, no exceptions) — a finding §5b extends via DB forensics to **~7 months of zero output** (last successful resolution: 2025-12-11, a one-time batch; nothing since). Meanwhile `scripts/fast_resolution_check.py`, run daily via `daily_maintenance.py`, already covers the same market population with a correctly-scoped, correctly-rotating, CLOB-based pipeline, and the post-resolution P&L/ELO work `check_market_resolutions` triggers is independently duplicated by `requeue_resolved_market_traders.py` → background P&L worker → `evaluate_new_trader_results.py` → `apply_full_elo_modifiers.py`. §5b also confirms no hidden side effects and quantifies the one real (but tiny, 0.24%-of-scope) coverage gap between the two pipelines — see §5b for the pre-removal verification step this implies. Separately, §4b confirms the second blocking call found in the same investigation (`scan_for_successful_traders`, `monitor.py:1237`) is genuinely load-bearing (sole new-trader discovery path) and should be offloaded, not removed.

**Recommendation: remove the call at `monitor.py:1261` (and retire `check_market_resolutions`), not offload it to a thread.** Async-ifying a function that has never once found a resolution in six weeks of observed runs would preserve zero value while adding executor/thread-safety surface. Removal is the fix that matches the actual finding. See §4 for the fallback if the team wants a staged rollout instead of outright deletion.

---

## 1. Duty-Cycle Quantification

**Trigger cadence:** `monitor.py:1235` and `:1243` both gate on `cycle_count % 10 == 0`. `check_interval = 900s` (15 min, `monitor.py:67,1469`, no config override found). So the resolution scan fires every **10 cycles = 9,000s = 2.5 hours** — confirmed, matches the prior ledger note.

**Per-market rate (measured, not estimated):** `check_market_resolutions` does one `requests.get(timeout=10)` per market (`polymarket_client.py:298`) plus `time.sleep(0.1)` (`trader_analyzer.py:218`). Empirical rate from three independent completed runs in the journal:

| Run (journal timestamp) | Markets checked | Wall time | Rate |
|---|---|---|---|
| May 21 12:34:56 → 14:13:24 | 46,082 | 98.5 min | 0.1276 s/market |
| Jul 1 01:40:59 → outage at ~02:54 (73 min, 12% done) | 37,160 of 300,437 | 73 min | 0.1179 s/market |

Consistent ~0.12–0.13 s/market.

**Scan-scope growth:** the in-scope unresolved-market count grew from ~46,000–52,000 (May 21–29) to **300,437 (Jul 1)** — roughly 6x in 6 weeks. This tracks directly with §2's rotation bug: markets that are never resolved never get `last_checked` touched, so they never age out of the front of the queue, and the backlog only grows.

**Full-scan duration at current scope:** 300,437 × 0.125s ≈ 37,555s ≈ **~626 minutes ≈ 10.4 hours**.

**Duty-cycle math for one "meta-cycle" (10 monitoring cycles):**
- 9 quick cycles × 15 min = 135 min (normal, non-blocking work: trade checks, background workers running freely)
- 1 resolution-scan cycle ≈ 626 min (event loop fully blocked: no pnl_worker, no backfill_worker, no watchdog heartbeat, no new-trade checks)
- Meta-cycle total ≈ 761 min
- **Blocked fraction ≈ 626 / 761 ≈ 82%**

This is a lower bound — it assumes the scan is allowed to run to completion, which §1b shows rarely happens.

**§1b — Scans usually don't finish:** across the full retained journal (3.6 GB, `journalctl -u polymarket-monitoring`), there are **95** "Starting resolution check" events but only **21** "Summary" (completion) events. **~78% of scan attempts are killed mid-flight** (service restart, crash, or — as on Jul 1 — a genuine outage) before completing. Combined with §1's growth trend, this means the scan is now large enough that it is more often interrupted than finished, and every restart starts the count back over (see §2 — the same first markets every time).

**Watchdog claim verified:** `_watchdog_task` is created via `asyncio.create_task` (`monitor.py:1395`) as an independent task with its own `asyncio.sleep(300)` loop. It is correctly *scheduled*, but asyncio is single-threaded cooperative — while `monitoring_loop` is inside the synchronous `check_market_resolutions()` call with no `await`, the event loop cannot switch to any other task, including the watchdog. So the watchdog does not fail to run because it's unscheduled; it fails to run because nothing yields control back to the loop for the scan's entire duration. Confirmed by log cross-reference: `logs/monitoring.log` (the `logging` module) goes silent 01:40:59→02:54:13 on Jul 1 while the journal (fed by `print()`, which bypasses the stalled loop by writing straight to stdout) keeps showing `[RESOLUTION]` lines — proof the process is alive and single-threaded-blocked, not crashed.

---

## 2. What Exactly Blocks

Confirmed by direct code read, not inference:

- **The HTTP call is the primary blocker.** `trader_analyzer.py:154` → `self.polymarket.get_market(market_id)` → `polymarket_client.py:309` → `get_market_details()` → `polymarket_client.py:298`: `self.session.get(url, timeout=10)`. This is a plain synchronous `requests`-style call with no `await`, executed once per market, up to 300,437 times per scan.
- **The `time.sleep(0.1)` rate-limit (`trader_analyzer.py:218`) is a secondary, smaller blocker** — real (adds ~0.1s × 300K ≈ 8.3 hours of the ~10.4-hour total on its own), not incidental. Removing only the HTTP-call cost via threading would still leave this sleep serialized unless it too is offloaded or replaced with `asyncio.sleep`.
- **DB writes are NOT a meaningful blocker for this function.** `update_market_resolution()` (`database.py:470`) is only called when a winning outcome is actually found, which — per §0 — happened **zero times** in every observed completed run. The DB-write path is essentially untested by real traffic in this function.
- **Compounding, previously unnoted:** the same `cycle_count % 10 == 0` branch that gates `check_market_resolutions` (`monitor.py:1243`) *also* gates a second unrelated blocking call one branch earlier — `self.analyzer.scan_for_successful_traders()` at `monitor.py:1237` — called **synchronously, directly, with no executor**. This is the same function that `initial_scan()` (`monitor.py:802`) *does* offload via `loop.run_in_executor(None, ...)`. So on every 10th cycle, the loop blocks on `scan_for_successful_traders` (unknown but likely non-trivial duration — it does an HTTP-backed trader-history fetch per newly-seen trader via `analyze_trader_performance` → `get_trader_history`, `polymarket_client.py:257`, synchronous `requests.get`) *before* it even reaches `check_market_resolutions`. This is not the primary O-13 finding but it means the actual per-10-cycle blocking window is `scan_for_successful_traders` duration + `check_market_resolutions` duration, not just the latter. **Disposition (this is in scope for the O-13 fix, not a separate item — see §4b): offload, do not remove.**

---

## 3. Scan Scope — Measured, Not Estimated

Queried directly against the live DB (read-only `SELECT`s, safe under WAL alongside the concurrent maintenance backfill):

`get_unresolved_markets()` (`database.py:515`) scope: markets with `resolved = 0 OR NULL`, joined to trades from `is_flagged=1, research_excluded=0` traders. **298,631 distinct markets** (journal's 300,437 from the same day is consistent — small drift as new markets/flags accrue).

| Segment of the 298,631 scan scope | Count | % |
|---|---|---|
| No `api_id` AND no `condition_id` (O-12 unroutable class) | 234,029 | **78.4%** |
| `end_date IS NULL` | 233,684 | 78.2% |
| `end_date` more than 30 days in the past | 62,573 | 21.0% |
| `end_date` more than 90 days in the past | 62,193 | 20.8% |
| `end_date` within the last 30 days (plausibly still pending resolution) | **2,374** | **0.8%** |

**Empirical proof the unroutable class is dead weight, not just theoretically:** the first 3 markets checked every run (debug-logged at `idx <= 3`) are the *same three market IDs* across every single sampled run from May 20 through Jul 1 (`0xa434a4dc...`, `0x34cf1582...`, `0x79ca3466...`), all logging `❌ No data returned from API`. This is because `check_market_resolutions` — unlike the fixed pass in `6c08afc` — **never updates `last_checked` for a market that isn't found resolved** (`update_market_resolution`, `database.py:470`, is the only writer of `last_checked` in this path, and it only fires on a winning-outcome match). The `ORDER BY m.last_checked ASC` (`database.py:542`) is therefore a no-op for ~100% of the scan's population: the same unroutable markets sort to the front of every run, forever, exactly the bug class `6c08afc` fixed in the *other* resolution pass but never ported to this one.

**Is this the O-12 class specifically?** Yes — same fingerprint as the ledger's Putin-market example (raw `0x...` hex `market_id`, empty `api_id`/`condition_id`, no `end_date`). Confirmed via direct row sample (5 markets pulled from the no-id set) — all raw hex IDs with blank `api_id`/`condition_id` columns.

**Conclusion:** the scan is overwhelmingly (78%+) checking markets it structurally cannot resolve (O-12), and of the remainder, only 0.8% (2,374 markets) fall in a plausible "might resolve soon" window. A scope reduction to `end_date`/`resolution_date` within a rolling window (mirroring `fast_resolution_check.py`'s own 0–7-day and >7-day passes, §5) would cut the scan by roughly two orders of magnitude on its own — but see §5 for why scope reduction is superseded by the redundancy finding.

---

## 4. Fix Options

### Option A — `run_in_executor` (thread-pool offload)
Wrap the whole call: `newly_resolved = await loop.run_in_executor(None, self.analyzer.check_market_resolutions)`. Matches the existing precedent at `monitor.py:802` (`initial_scan` already does this for `scan_for_successful_traders`) and the `asyncio.to_thread` precedent at `monitor.py:1257,1298`.
- **Pro:** simplest, smallest diff, proven pattern already in this codebase.
- **Con:** `Database.get_connection()` opens a fresh `sqlite3.connect()` per call with WAL + `busy_timeout=30000` (`database.py:39-51`) — safe to call from a worker thread (each call gets its own connection object, never shared across threads), so no new thread-safety risk. But it does nothing about the ~10.4-hour scan itself still hammering the Gamma API for 10+ hours; it just moves the pain off the event loop. Given §0/§3, this fixes the *symptom* (loop starvation) while leaving the *disease* (a scan that finds nothing, 78% of it structurally unresolvable) running indefinitely in the background, competing for API rate limit and DB connections the whole time.

### Option B — chunked with `await asyncio.sleep(0)` yields
Break the market loop into batches (e.g. 50-100 markets), yielding control between batches so the loop stays responsive. Keeps everything on the main thread/single-writer path.
- **Pro:** no new thread-safety surface at all; watchdog and other tasks get to run interleaved.
- **Con:** still fundamentally serial and still ~10.4 hours wall-clock for a full pass; doesn't address the 78% dead-weight scope or the zero-resolutions-ever finding. More invasive to write correctly (need to track loop position across yields, handle the resume-after-restart case) than Option A for a function that — per §5 — should not exist in this form regardless.

### Option C — scope reduction (check only plausible markets)
Restrict `get_unresolved_markets()` to a recent `end_date`/`resolution_date` window, mirroring `run_recent_overdue_pass`'s 0-7-day logic. Would cut scope from ~298K to ~2,374 (§3), making even the unmodified synchronous version fast enough (2,374 × 0.125s ≈ 5 min) that blocking barely matters.
- **Pro:** attacks the actual cost driver (scope), not just its symptom (sync call).
- **Con:** as designed, it would just be reinventing `fast_resolution_check.py`'s existing `run_recent_overdue_pass` — see §5.

### Option D (not in the original 3, but the one the evidence points to) — remove the call
Delete the `check_market_resolutions()` call at `monitor.py:1261` and the surrounding periodic-check block (`monitor.py:1242-1267`); retire `check_market_resolutions()` and its dead-code post-resolution block (`trader_analyzer.py:121-319`, unreachable in practice since `newly_resolved` has been 0 in every observed completed run). No caller outside `monitor.py:1261` exists (`grep` confirms — the only other references are stale print-statement suggestions of a nonexistent `monitoring/check_market_resolutions.py` script path in unrelated files, not real call sites).

**Recommended primary fix: Option D**, on the strength of §5's redundancy finding. Options A/B are valid *fallbacks* if the team wants to keep the monitoring-loop resolution check alive for some reason not visible in this investigation (e.g. as a faster-cadence supplement to the daily maintenance pass) — in that case, Option A + Option C combined (offload AND scope down to the same recency window as `run_recent_overdue_pass`) is the right compromise, not Option A alone.

---

## 4b. The Second Blocking Call — `scan_for_successful_traders` (in scope for this fix)

§2 found that `monitor.py:1237` calls `self.analyzer.scan_for_successful_traders()` synchronously on the exact same `cycle_count % 10 == 0` branch, one statement before the resolution check — so it compounds the same stall and belongs in the same implementation pass. Unlike `check_market_resolutions`, **this one is not redundant and should not be removed** — it needs the offload treatment only.

**Why it's not redundant:** `scan_for_successful_traders()` (`trader_analyzer.py:67-100`) is the only mechanism in the codebase that *discovers brand-new trader addresses* — it fetches markets from Polymarket by category (`Geopolitics`, `Global Politics`, `Ukraine & Russia`, `Elections`, `Economics`, `Unknown`), extracts every active trader address from those markets' trade history, and for each one not already tracked, `db.add_or_update_trader(...)` inserts a new row and flags it if it clears the volume/trade-count threshold. This was checked against the other trader-flagging step in `daily_maintenance.py`, `promote_high_pnl_traders.py` (`SET is_flagged = 1 ... WHERE realized_pnl > 50000 ... AND (is_flagged = 0 OR research_excluded = 1)`) — that script is an `UPDATE` against traders **already present** in the `traders` table; it cannot discover an address that was never inserted. Nothing else in `daily_maintenance.py`'s 29 steps does category-based market scanning or trader ingestion. Without `scan_for_successful_traders`, new traders active in these categories would simply never enter the `traders` table, and `promote_high_pnl_traders.py` would have nothing new to act on.

**Recommended fix:** wrap the `monitor.py:1237` call the same way `initial_scan()` (`monitor.py:802`) already wraps the identical function — `newly_flagged = await loop.run_in_executor(None, self.analyzer.scan_for_successful_traders)`. This is a one-line change copying an existing, already-proven pattern in the same file — not a new design decision. Its duration wasn't separately measured in this investigation (flagged in §8 as not quantified), but regardless of duration, offloading it removes its contribution to the event-loop stall at negligible risk, using a pattern already validated elsewhere in this codebase.

---

## 5. The Overlap Question — Answered

**`scripts/fast_resolution_check.py` already solves this exact problem, and its own docstring says so:**

> "Instead of checking each market individually (11.8 hours for 213k markets), this script fetches ALL resolved markets from Gamma API in one batch query... Expected performance: 10-30 seconds vs 11.8 hours." (`fast_resolution_check.py:1-19`)

This is a direct description of replacing `check_market_resolutions`'s exact approach. It ships four passes, run daily via `daily_maintenance.py` step "Fetch new market resolutions" (`daily_maintenance.py:46`, `--stale-limit 500`, non-blocking):

1. **Bulk Gamma pass** (`fetch_all_resolved_markets` / `batch_update_resolved_markets`) — one paginated batch query for ALL closed markets, ~10-30s.
2. **Recent overdue pass** (`run_recent_overdue_pass`, `fast_resolution_check.py:412`) — targets markets 0-7 days past `resolution_date`/`end_date` with no `api_id`/`condition_id` (i.e., exactly the O-12-shaped markets), via CLOB with `condition_id or market_id` fallback. **Correctly updates `last_checked` on every check, resolved or not** (lines 476, 488, 497) — the rotation fix `check_market_resolutions` never got. This is the fix landed in `6c08afc`.
3. **Stale CLOB pass** (`run_stale_clob_pass`, `fast_resolution_check.py:315`) — markets >7 days overdue with a known `resolution_date`, via CLOB, capped at `--stale-limit` (500 in production).
4. **External seed pass** (`run_external_seed_pass`, `fast_resolution_check.py:515`) — same CLOB-by-ID approach as pass 2/3, scoped to markets traded by `discovery_source = 'external_seed'` traders with `resolution_date < now - 7 days`. Read in full for §5b below (needed for the coverage-gap analysis).

These passes operate on the `markets` table directly (not scoped to flagged/non-excluded traders — a *superset* of `check_market_resolutions`'s scope), run daily, and are already correctly rotation-safe. **There is no gap `check_market_resolutions` uniquely fills on the detection side.**

**Post-resolution processing is also independently duplicated.** `check_market_resolutions`'s tail (`trader_analyzer.py:252-319`) — evaluate resolved-market trades, recalc trader stats, quick ELO update — never actually runs in observed history (gated on `newly_resolved > 0`, which has been 0 every time). But even if it did, the daily maintenance pipeline has its own independent chain for markets resolved via `fast_resolution_check.py`: `requeue_resolved_market_traders.py` (resets `pnl_last_updated` for traders with open positions in newly-resolved markets, `requeue_resolved_market_traders.py:1-18`) → background P&L worker applies synthetic resolution closes → `evaluate_new_trader_results.py` → `apply_full_elo_modifiers.py` (Writer B, per the O-6 writer map). So removing `check_market_resolutions` does not orphan any resolved market from P&L/ELO processing — it's already covered on a daily cadence by a separate, already-running pipeline.

**Verdict: `check_market_resolutions` is fully redundant on both the detection side and the post-resolution side.** It is a legacy per-market implementation that predates `fast_resolution_check.py` (whose docstring literally cites the "11.8 hours for 213k markets" problem as the reason it was built) and was never decommissioned from the monitoring loop after its replacement shipped. The empirical zero-resolutions-ever result (§0) is the expected outcome of this: everything it might have caught, the daily pipeline already catches, faster and with correct rotation.

---

## 5b. Removal-Safety Checklist — Proving the Duplication, Not Assuming It

Removal (Option D) rests entirely on "the 4 passes fully duplicate `check_market_resolutions`." That claim needed to be tested, not asserted. Three checks were run against the live code and DB (read-only); results below. **Net conclusion: the duplication claim holds for all practical purposes, with one small, quantified, pre-existing gap that removal does not make worse.**

### Checklist item 1 — Does the 4-pass coverage catch every market type/timing-window the loop scan did?

**Not quite — one narrow, quantified gap exists, and it predates and is independent of this fix.** All 4 passes bound their queries by `resolution_date`/`end_date` (passes 2-4) or by Gamma's `endDate`-descending feed capped at 50,000 closed markets (pass 1, `fetch_all_resolved_markets`, `fast_resolution_check.py:132-134`: `if offset >= 50000: break`). `check_market_resolutions` bounds by nothing — it queries every unresolved market by ID directly, regardless of date fields.

Measured against the current 298,631-market scope:

| Segment | Count | % of scope | Reachable by which pass? |
|---|---|---|---|
| No `api_id`/`condition_id` AND no `end_date` AND no `resolution_date` | 232,960 | 78.0% | **None** — no ID for Gamma/CLOB matching, no date for windowing. True O-12 permanent-loss class; `check_market_resolutions` cannot reach these either (confirmed by the "same 3 markets fail every run" evidence in §3) — not a gap introduced by removal. |
| Has `api_id` or `condition_id` but no `end_date`/`resolution_date` | **724** | **0.24%** | Only pass 1 (bulk Gamma, matched via `api_id = ? OR market_id = ? OR condition_id = ?`, `fast_resolution_check.py:238-243`) — **if** the market falls within Gamma's 50K-most-recent-by-endDate window. Passes 2-4 all require a non-NULL date field to build their window, so these 724 never enter them. `check_market_resolutions` **would** reach these (it checks every unresolved market by ID unconditionally) — this is the one real, if narrow, coverage difference. |
| Everything else (has usable date and/or is within pass 2/3/4 windows) | 64,947 | 21.8% | Covered by one or more of passes 2-4 on the same cadence as today. |

**What this means for removal:** the 724-market edge case (0.24% of scope) is the only segment where `check_market_resolutions` has a theoretical reach advantage over the 4-pass pipeline. In practice this theoretical advantage produced **zero resolutions** in the entire observed DB history (see checklist item 2) — so there's no evidence it's converting the advantage into real coverage. **Before deleting the call, next session should spot-check a sample of the 724 against the live Gamma/CLOB APIs** (read-only `get_market`/CLOB calls, a handful of markets) to confirm they're either (a) genuinely unroutable/dead like the O-12 class, or (b) still within Gamma's 50K window and thus already covered by pass 1 despite missing local date fields. If (b), the gap is illusory (Gamma has its own end date even though our DB row doesn't). If a nontrivial fraction turn out to be (c) — resolvable, with a date, and outside Gamma's window — the fix is to backfill `end_date`/`resolution_date` for these 724 rows (a `scripts/backfill_market_categories.py`-style targeted backfill) so they fall into pass 2/3's windows, not to keep `check_market_resolutions` alive for 724 markets out of 298,631.

### Checklist item 2 — Is "zero in 21 runs" the full history, or just the retained-journal window?

**It's just the retained-journal window (~May 20 – Jul 1 2026) — but DB forensics extend the finding much further back, and confirm it, rather than undermining it.** The journal's 3.6GB retention doesn't go back indefinitely, so the 21-run sample can't speak to anything before ~May 20. However, `winning_outcome` values written by `check_market_resolutions` have a distinct forensic signature: `trader_analyzer.py:197` does `winning_outcome = name.lower()`, while every other writer (`fast_resolution_check.py`'s `extract_winner`, and the CLOB-based passes reading `token.get('outcome')`) preserves the API's original casing (`"Yes"`/`"No"`, never lowercased). A direct DB query for lowercase-only `winning_outcome` values found:

```
no          13 rows
yes          2 rows
republican   1 row
```

All 15 rows share `resolution_date`/`last_checked` clustered within a single 37-second window on **2025-12-11 12:00:04–12:00:41** — a one-time batch, all long-settled 2024-election and 2022-era markets (Trump/Harris primary markets, "will Turkish Lira fall below $0.05 by end of 2022," "will OpenSea launch a token by Dec 31 2022"). **This is the only evidence anywhere in the database of `check_market_resolutions` ever successfully resolving a market.** Nothing with this signature appears after Dec 11 2025 — meaning the function has found **zero resolutions for approximately seven months** (Dec 11 2025 → Jul 1 2026), a materially stronger and longer-baseline result than the 21-runs/0-found finding from the journal alone. (A separate lowercase cluster, `'unknown'` × 498, does not match this signature — `name.lower()` only fires on an actual matched outcome name, and there's no evidence tying `'unknown'` to this function specifically; likely a different writer's sentinel value, not investigated further as it's outside O-13's scope.)

**Conclusion: the "zero" finding is not an artifact of short log retention. It's corroborated by DB-level forensic evidence spanning ~7 months, the DB's only record of this function's lifetime output.**

### Checklist item 3 — Does anything else depend on `check_market_resolutions` as a side effect?

**No hidden dependency found.** Traced every write inside the function:
- `db.update_market_resolution()` (only on a winning-outcome match) — writes `resolved`, `winning_outcome`, `resolution_date`, `last_checked`. Same columns, same semantics as every `fast_resolution_check.py` pass's own UPDATE statements.
- The post-resolution tail (`trader_analyzer.py:252-319`, gated on `newly_resolved > 0`, which — per checklist item 2 — has been true exactly once in the DB's history, 2025-12-11) calls `TradeEvaluator.batch_evaluate_resolved_markets` and `TraderStatisticsCalculator.recalculate_all_flagged_traders`, then `UnifiedELOMonitoringBridge` position/ELO updates. Confirmed `scripts/evaluate_new_trader_results.py` (daily_maintenance step, non-blocking) targets the identical criteria — `trade_result = 'pending'` in a market where `resolved = 1 AND winning_outcome IS NOT NULL`, for `is_flagged = 1, research_excluded = 0` traders (`evaluate_new_trader_results.py:3-9,42-49`) — i.e. it is the general-purpose version of exactly what `TradeEvaluator.batch_evaluate_resolved_markets` does, running daily regardless of which pipeline set `resolved = 1`. Downstream ELO (`apply_full_elo_modifiers.py`, Writer B per the O-6 writer map) then picks up any resulting P&L changes on its own daily cadence.
- No other repo file reads any column or state that only `check_market_resolutions` would produce (grep confirms the only call site is `monitor.py:1261`; nothing imports `TraderAnalyzer.check_market_resolutions` elsewhere).

**Conclusion: no side effect of `check_market_resolutions` is unique to it.** Everything it writes or triggers has an independent daily-cadence equivalent already running.

---

## 6. Recommended Design (for next session)

0. **Do §5b's spot-check first, before deleting anything.** Pull a small sample of the 724 has-ID/no-date markets (§5b item 1) and query them directly against live Gamma/CLOB to confirm they're either dead (like the O-12 class) or already inside Gamma's 50K-recency window despite the missing local date. This is the one open item standing between "assumed-safe" and "proven-safe" removal — everything else in §5b (items 2 and 3) is already resolved with DB/code evidence, not open.
1. **Remove** the periodic-resolution-check block at `monitor.py:1242-1267` and the call to `self.analyzer.check_market_resolutions()`.
2. **Retire** `check_market_resolutions()` in `trader_analyzer.py` (and its unused imports `TradeEvaluator`, `TraderStatisticsCalculator`, `UnifiedELOMonitoringBridge` if nothing else in the file uses them — verify before deleting).
3. **Fix the compounding issue found in §2/§4b as part of the same change:** wrap `monitor.py:1237`'s `scan_for_successful_traders()` call in `run_in_executor`, matching the precedent already used for the identical call in `initial_scan()` (`monitor.py:802`). Confirmed **not** redundant (§4b — it's the sole new-trader discovery path; `promote_high_pnl_traders.py` only updates traders already in the DB), so this one gets the offload treatment, not removal. One-line change, same file, existing pattern.
4. **Do not silently drop the "3 total/resolved market counts" debug print** (`monitor.py:1246-1259`, the `_fetch_market_counts` thread-offloaded block) — it's cheap, already async-safe, and harmless to keep as a periodic health signal independent of the removed scan.
5. **If stakeholders want a safety margin before deleting outright:** land Option A (executor offload) + Option C (scope to the same 0-7-day window as `run_recent_overdue_pass`) as a one-cycle bridge, observe for 1-2 weeks that it still finds nothing beyond what `fast_resolution_check.py` already caught, then remove.

### What a test would look like
- **Regression test for the removal:** assert `monitor.py`'s `monitoring_loop` no longer references `check_market_resolutions`; assert the watchdog task (`_watchdog_task`) logs a heartbeat within any single monitoring cycle under simulated load (i.e., nothing in the loop can block >300s uninterrupted) — this is the structural invariant O-13 exists to protect.
- **If Option A/B is landed instead of removal:** a test that mocks `polymarket.get_market` with an injected delay and asserts `_watchdog_loop`'s heartbeat still logs during a simulated multi-minute scan (proves the offload/yield actually restores loop responsiveness) — this test would **fail today** against the unmodified code, which is the point (it surfaces the exact defect this doc describes).
- **Regardless of path chosen:** a test asserting `scan_for_successful_traders()` in the main `monitoring_loop` (not just `initial_scan`) is invoked via executor/thread, not synchronously — catches the §2 compounding issue if it regresses.

---

## 7. Files Referenced

| File | Role |
|------|------|
| `monitoring/monitor.py:1215-1327` | `monitoring_loop` — the call site, cadence gating, watchdog interaction |
| `monitoring/monitor.py:793-806` | `initial_scan` — existing `run_in_executor` precedent for the same function that's called synchronously elsewhere |
| `monitoring/monitor.py:1329-1354` | `_watchdog_loop` — confirmed independently scheduled but starved by the synchronous call |
| `monitoring/trader_analyzer.py:121-319` | `check_market_resolutions` — the blocking function, plus its dead post-resolution tail |
| `monitoring/polymarket_client.py:286-314` | `get_market_details`/`get_market` — the synchronous `requests` call that blocks |
| `monitoring/polymarket_client.py:257-275,361+` | `get_trader_history`/`get_active_traders_from_markets` — the same synchronous-HTTP pattern behind the compounding `scan_for_successful_traders` issue (§2) |
| `monitoring/database.py:515-548` | `get_unresolved_markets` — scan-scope query, no recency filter, no O-12 filter |
| `monitoring/database.py:470-493` | `update_market_resolution` — the only writer of `last_checked` in this path (only on success) — root of the no-rotation bug |
| `scripts/fast_resolution_check.py:1-19` | Docstring explicitly describes replacing the per-market approach this doc is about |
| `scripts/fast_resolution_check.py:412-513` | `run_recent_overdue_pass` — correctly-scoped, correctly-rotating equivalent (this is the `6c08afc` fix, in the pass that already has it) |
| `scripts/fast_resolution_check.py:315-411` | `run_stale_clob_pass` — safety net for >7-day-overdue markets |
| `scripts/daily_maintenance.py:46` | Where `fast_resolution_check.py` is scheduled (daily, non-blocking) |
| `scripts/requeue_resolved_market_traders.py:1-44` | Independent post-resolution P&L requeue path, parallel to `check_market_resolutions`'s dead tail |

---

## 8. Inference vs. Proven

**Proven (direct code read + log/DB evidence):**
- The call is synchronous with no `await`/executor (code read).
- Cadence: every 10 cycles = 2.5h (code read, `check_interval=900` confirmed, no override).
- Per-market rate ~0.12-0.13s (measured from 2 independent journal runs).
- Scan scope 298,631 markets; 78.4% have no `api_id`/`condition_id`; 0.8% have a recent `end_date` (direct DB query).
- `last_checked` is never updated except on resolution success (code read of `database.py:470-493` and the query at `:515-548` — no other writer found via grep).
- Same 3 markets return "no data" at the front of every sampled run, May 20 – Jul 1 (log grep).
- 95 scan starts vs 21 completions in the retained journal; **all 21 completions show 0 resolutions found** (log grep, exhaustive over retained journal history).
- `fast_resolution_check.py` exists, runs daily via `daily_maintenance.py`, and its docstring explicitly frames itself as the fix for the per-market approach (code read).
- No other call site for `check_market_resolutions` exists (grep across repo).
- **Coverage gap is exactly 724 markets (0.24% of scope)** — has an `api_id`/`condition_id` but no `end_date`/`resolution_date`, reachable only by pass 1's recency-capped bulk feed, not passes 2-4 (direct DB query, §5b item 1).
- **`check_market_resolutions` last successfully resolved a market on 2025-12-11**, a one-time 15-market batch identifiable by its unique `winning_outcome = name.lower()` signature; nothing since, through 2026-07-01 (DB query, §5b item 2) — this is DB-forensic evidence independent of and predating the journal's retention window.
- **`evaluate_new_trader_results.py` targets the identical criteria as `check_market_resolutions`'s post-resolution evaluation tail** (code read, `evaluate_new_trader_results.py:3-9,42-49` vs `trader_analyzer.py:252-266`) — confirms no unique side effect (§5b item 3).
- **`scan_for_successful_traders` is not redundant** — it is the only code path that inserts new trader rows from category-based market discovery; `promote_high_pnl_traders.py` only updates existing rows (code read of both files, §4b). This resolves the "removable or needs offload" question the second blocking call raised: needs offload, not removal.

**Inferred / extrapolated (flagged explicitly):**
- Full-scan duration of ~10.4 hours at current 300K scope is an extrapolation from measured per-market rate, not a directly observed complete run at this scale (no run has completed at this scope in the retained journal — consistent with the 78%-interrupted finding).
- The 82% duty-cycle-blocked figure assumes a scan is allowed to run to completion once per meta-cycle; in practice interruptions mean the *effective* pattern is closer to "blocked more or less continuously, with cycles restarting the count," which is qualitatively worse, not better.
- `scan_for_successful_traders`'s exact duration was not measured — its *redundancy status* is now resolved (see above), but how long it blocks the loop per occurrence is still unquantified. Worth a quick timing check next session, though it doesn't change the offload recommendation either way.
- Whether `run_external_seed_pass` (Pass 4) has any relevance to O-13 beyond the coverage-gap analysis in §5b was not investigated further.
- **Still open, not yet proven:** whether the 724-market coverage gap (§5b item 1) is illusory (already covered by Gamma's 50K window despite missing local dates) or real (genuinely uncovered). This is the one item this investigation could not close from static code/DB analysis alone — it requires a handful of live API calls, explicitly deferred to next session per §6 step 0 so this investigation stays read-only as scoped.
- Whether the 498 lowercase `'unknown'` `winning_outcome` rows (§5b item 2) trace to any particular writer was not resolved — noted as an unrelated observation, not pursued further.

---

*Investigation complete 2026-07-01. No code or DB changes made. Change nothing until this design is reviewed and an implementation session is explicitly started.*
