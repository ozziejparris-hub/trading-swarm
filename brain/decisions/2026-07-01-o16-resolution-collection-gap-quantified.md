# O-16 — Resolution Under-Collection Gap, Quantified

**Date:** 2026-07-01
**Method:** Read-only. All findings from live DB queries (`data/polymarket_tracker.db`, first-repo) and live, read-only Gamma/CLOB API calls. No writes — first-repo untouched throughout (verified via `git status` before/after), no code changed. Run alongside `daily_maintenance.py` (PID 6794, in progress) with no interference — all queries are `SELECT`, all API calls are `GET`.
**Context:** Follows the O-13 investigation (`2026-07-01-o13-monitoring-blocking-stall-design.md`), which closed its §5b open item by spot-checking a 724-market segment and finding ~76-80% of it already resolved-on-Polymarket-but-stuck-locally. This doc asks the bigger question the 724-sample couldn't answer on its own: how large is the *total* under-collection gap across the whole `markets` table, and is it a fixed backlog or an active daily leak?

---

## 0. Executive Summary

The real gap is **two orders of magnitude larger** than the 724-market segment suggested: **194,216 markets** (all with a valid, routable `api_id`/`condition_id` — zero are the unroutable O-12 class) sit at `resolved = 0` with an `end_date` more than 7 days in the past and `resolution_date` still `NULL`. A live spot-check (40 markets, mixed across overdue-age buckets) found a **95% hit rate** — i.e. the overwhelming majority are already resolved on Polymarket with a clear winning outcome, just never written back locally. Extrapolated: **an estimated 180,000–194,000 genuinely-resolved markets are currently missing their resolution locally.**

**The good news: this is a static, one-time historical artifact, not an active daily leak.** 194,215 of the 194,216 (99.9995%) carry `data_source = 'historical_backfill'` and share a single frozen `last_checked` timestamp — 2025-12-11 — the same date as the one-time successful `check_market_resolutions()` batch identified in the O-13 doc. The live/current monitoring pipeline (`data_source = 'live_monitoring'`) is populating `resolution_date` correctly today — only 1 live-monitoring-sourced market shares this stuck state, against 24,333 that have `resolution_date` set properly. **This is backlog debt from a Dec 11 2025 import, not an ongoing bleed.**

**It is not a "nobody cares" population.** 68,290 of the 194,216 stuck markets (35%) have at least one recorded trade; 62,407 (32%) have a trade from a currently-flagged, non-research-excluded trader; **19,084 of 22,390 flagged+clean traders (85%) have at least one trade in a stuck market.** This directly touches the scored/tracked trader population that feeds ELO and accuracy signals.

**2026-07-01 follow-up (§6-7): confirmed dormant, not just quiet — and a backfill design is ready.** §6 traces the exact write-path mechanism and finds the generator was **structurally fixed by commits `4cdd190`/`446bcde` (2026-05-31)**, which made every `end_date` write co-write `resolution_date`; zero new instances of this pattern have appeared since (verified against the live DB). A **one-time backfill is a permanent fix**, not a stopgap — no code fix is required first. §6.4 separately flags a **different, currently-active, small-scale generator** (`resolve_legendary_markets.py` / `legendary_positions_scan.py` resolving markets correctly but never writing `resolution_date` — 182 rows and growing slowly) that disproportionately affects LEGENDARY-tier P&L requeueing; worth its own quick fix, not part of the 194,216 backlog. §7 scopes the backfill itself: ~2.6-5 hour runtime at light concurrency, resumable via the existing `resolved=0` filter (no new progress file needed), confirmed the per-ID Gamma endpoint works (30/30 in a fresh sample), and recommends processing the 62,407 flagged-trader-affecting markets first.

**Pass 1's real reach is ~2,100 closed markets per run, not the 50,000 the code assumes** — Gamma's list endpoint now hard-errors past offset 2,100 with `"offset too large, use /markets/keyset for deeper pagination"`. This is a ~95.8% shortfall against the coded assumption, confirmed precisely below. It's a contributing factor to overall system-wide under-collection but is **not** why the 194,216 are stuck — those lack an `endDate` field on Gamma's side entirely, so no depth of pagination would ever surface them; they're excluded by the sort key, not the cap.

**Bottom line for urgency:** this is a large, real, and materially-relevant data-quality gap — but it is a **backlog to schedule a fix for, not a fire to fight tonight.** The mechanism producing new orphans (the interaction of `run_recent_overdue_pass`'s no-op-on-failure `resolution_date` and `run_stale_clob_pass`'s hard `resolution_date IS NOT NULL` requirement) is a live structural bug that *could* leak going forward, but the live-monitoring evidence (1 stuck vs 24,333 clean) shows it isn't doing so today in any measurable way. Recommend: fix-this-week, not fix-tonight.

---

## 1. The Current Backlog — Measured

### 1.1 Query and scope

Reproduced against the **full `markets` table** (not scoped to flagged traders — this matches the actual scope of `fast_resolution_check.py`'s passes, per O-13 §5's note that they operate unscoped, "a superset of `check_market_resolutions`'s scope"):

```sql
SELECT COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL)
AND resolution_date IS NULL
AND end_date IS NOT NULL
AND end_date < datetime('now','-7 days');
-- 194,216
```

**All 194,216 have a routable ID** — `api_id` or `condition_id` populated on 100% of rows (0 fall into the O-12 unroutable/permanent-loss class). These are not dead markets; they're markets no current pass reaches.

### 1.2 Overdue-age breakdown

| Bucket | Count | % |
|---|---|---|
| 7–30 days overdue | 96 | 0.05% |
| 30–90 days overdue | 489 | 0.25% |
| 90+ days overdue | 193,631 | 99.7% |

`end_date` range across the full set: **2020-10-25 → 2026-06-16**. The 90+ day bucket dominates almost completely and is the historical-backfill artifact described in §2.

For comparison, the *other* stale population — markets that DO have `resolution_date` set and are >7 days overdue (the population `run_stale_clob_pass` actually targets) — is only **301** rows, well under its 500-row daily cap, and is confirmed actively self-healing (see §2, maintenance-log evidence: 180-255 resolved per run out of 300-370 checked, consistently).

### 1.3 Hit-rate spot-check (live, read-only)

Sampled 40 markets total across the backlog, queried live via `GET gamma-api.polymarket.com/markets/{api_id}`:

- **30 random from the 90+ day bucket (dominant segment): 30/30 (100%) already `closed: true, umaResolutionStatus: resolved`** with a clean winning outcome in `outcomePrices`. Titles are overwhelmingly short-horizon, single-event markets (sports results, hourly BTC/ETH up-down bets, single-day price-threshold questions, esports match winners) — exactly the kind of market that resolves within hours of its `end_date`, so a 90+-day-old one being unresolved locally is essentially never a "genuinely still open" case.
- **10 random from the 7–30 day bucket: 8/10 (80%) resolved**, 2/10 genuinely still open (`closed: false`) — both were VA-02 Democratic primary nominee markets sitting at outcome prices 0.954/0.046 and 0.9995/0.0005 (effectively decided but not yet formally closed/certified). This is expected, correct behavior for markets whose real-world outcome is very recent.

**Blended hit rate: 38/40 = 95%.** Extrapolating conservatively (95% on the 96+489 recent buckets, ~100% on the 193,631 90+-day bucket, which the full 30-sample confirmed at 100%): **≈184,000–194,000 of the 194,216 are genuinely resolved on Polymarket and simply never written back locally.**

---

## 2. Growing or Static? (the urgency question)

**Verdict: STATIC. Not growing — this is one-time historical debt, not a daily leak.**

```sql
SELECT data_source, COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL) AND resolution_date IS NULL
AND end_date IS NOT NULL AND end_date < datetime('now','-7 days')
GROUP BY data_source;
-- historical_backfill | 194,215
-- live_monitoring     |      1
```

```sql
SELECT date(last_checked), COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL) AND resolution_date IS NULL
AND end_date IS NOT NULL AND end_date < datetime('now','-7 days')
GROUP BY date(last_checked);
-- 2025-12-11 | 194,215
-- 2026-01-12 |       1
```

**99.9995% of the backlog is a single `data_source = 'historical_backfill'` cohort, frozen at the identical `last_checked` timestamp — 2025-12-11.** This is the same date as O-13's forensic finding (the one-time 15-market `check_market_resolutions` success batch). It reads as a single large one-time market-catalog import that populated `end_date` for ~194K+232K (the latter being O-12's unroutable class) markets in one operation, whose accompanying resolution pass never meaningfully completed against it.

**The live pipeline is healthy by contrast**: markets sourced from `live_monitoring` have `resolution_date` populated correctly at 24,333-to-1 odds against falling into this trap. This is strong evidence the *current*, ongoing monitoring path is not reproducing this failure mode for freshly-tracked markets.

**A real structural bug exists that *could* leak going forward, but isn't currently doing so at meaningful scale.** Traced the mechanism: `run_recent_overdue_pass` (0-7 day window) updates `last_checked` on every check but only ever sets `resolution_date` implicitly (via the `resolved=1` branch) — on a "still open" or "no winner" result it updates only `last_checked`, never `resolution_date`. Once a market ages past day 7 still unresolved, it exits `run_recent_overdue_pass`'s window and can **never** enter `run_stale_clob_pass`, whose query hard-requires `resolution_date IS NOT NULL`. Any market that isn't resolved during its 0-7-day window is structurally orphaned — permanently invisible to Pass 3, with only Pass 1 (Gamma bulk, itself capped per §4) as a remaining, unreliable route. This is a real latent bug (see §4b of the follow-up recommendation), but the live-monitoring evidence shows it isn't presently converting into a measurable ongoing leak — likely because `run_recent_overdue_pass`'s daily window pool (currently 415 markets, cap 200) is small enough, and its hit rate high enough (log evidence: 44/52, 76/92, 23/26, etc., in recent runs — see maintenance log excerpts), that few live-monitoring markets fall through in practice. Worth a fix regardless, since the failure mode is real and would compound if daily window volume ever grows past the 200 cap or hit rates drop.

**One data point worth flagging, not yet fully explained:** the 96 markets currently in the 7–30-day-overdue bucket are *also* all stamped `last_checked = 2025-12-11` — meaning even as they cycled through their nominal 0-7-day window over the past several weeks, none were touched. Since they're part of the same `historical_backfill` cohort (whose `last_checked` ties them for "oldest" against essentially the entire competing window pool every day), the leading hypothesis is a tie-break starvation effect in `run_recent_overdue_pass`'s `ORDER BY last_checked ASC ... LIMIT 200`: with hundreds of `historical_backfill` rows perpetually tied for oldest, SQLite's arbitrary/stable tie-break order likely picks the same subset every day, and non-updates (no `resolution_date` change) don't shift a market's tie position — so distinct markets that only become window-eligible on different days can still lose the tie-break to the same fixed prefix indefinitely. Not fully proven (would need day-by-day historical log archaeology to confirm), but consistent with all observed evidence and worth stating as the leading explanation for the record.

---

## 3. What the Missing Data Affects

**Not a "nobody cares" population — it materially touches the scored/tracked trader pool.**

```sql
-- of the 194,216 stuck markets:
-- 68,290 (35%) have at least one recorded trade
-- 62,407 (32%) have a trade from a trader with is_flagged=1 AND (research_excluded=0 OR NULL)
-- 19,084 of 22,390 such traders (85%) have at least one trade in a stuck market
```

19,084 out of 22,390 flagged, non-research-excluded traders — 85% of the tracked pool as defined by the `is_flagged=1 AND research_excluded=0` filter CLAUDE.md specifies for research queries — have exposure to at least one currently-stuck-unresolved market. (Note: this is a different, broader cohort than the "857 clean pool" figure in CLAUDE.md's April 30 audit findings, which reflects a narrower audit criterion — not reconciled here, out of scope for this measurement.)

This means P&L, win-rate, and downstream ELO calculations for the large majority of the tracked trader population are potentially missing resolution outcomes for a real slice of their trading history. Individually, per-trader impact is likely small (each trader's stuck-market exposure is probably a handful of positions against a much larger total trade history), but in aggregate this is a legitimate accuracy concern for the ELO/signal-integrity arc — worth cross-referencing against the ongoing Comprehensive ELO Bug investigation (RQ-CONTESTED-001) and O-0 (Pool C decline) as a candidate contributing factor, though no causal link is established here — this doc only measures the resolution-collection gap itself, not its downstream ELO impact.

---

## 4. Pass 1's True Reach — Confirmed Precisely

**Gamma's `/markets` list endpoint (`closed=true&order=endDate&ascending=false`, the exact query `fetch_all_resolved_markets` uses) hard-errors with HTTP 422 (`"offset too large, use /markets/keyset for deeper pagination"`) starting at `offset=2100`.** Confirmed via direct binary search with the script's actual `batch_size=100` paging:

```
offset=2000, limit=100 → HTTP 200 (succeeds — last good page, records 2000-2099)
offset=2100, limit=100 → HTTP 422 (fails — loop breaks here)
```

`fetch_all_resolved_markets`'s status-code check (`if response.status_code != 200: break`, `fast_resolution_check.py:97-99`) handles this gracefully — no crash, no exception — but it means **Pass 1's actual daily reach is ~2,100 closed markets, not the 50,000 the `if offset >= 50000: break` safety limit (`fast_resolution_check.py:132-134`) is coded to assume.** That's roughly **4.2% of the intended scan depth** — a ~95.8% shortfall. This is a Gamma-side API change (the offset ceiling), unrelated to anything in this repo, and independent of the O-13 removal decision.

**This does not explain the 194,216 backlog.** None of the sampled `historical_backfill` markets have an `endDate` field on Gamma's side at all (confirmed via full-field dump in the O-13 investigation) — under an `endDate`-descending sort they'd rank last regardless of cap depth, so they were never reachable by Pass 1 even before this offset regression. The offset-cap discovery is a **separate, additional** finding: it reduces Pass 1's coverage of the *rest* of the closed-market universe (markets that do have valid Gamma `endDate` values) far below what the code assumes, worth its own fix, but not the mechanism behind this doc's headline number.

---

## 5. Recommendations (scoping only — not implemented, this doc is measurement-only)

Two independent follow-up items, neither urgent enough to interrupt current work, both real:

1. **One-time backfill for the 194,216 `historical_backfill` markets.** Since ~95% are already resolved on Polymarket, a targeted one-time script — direct `GET gamma-api.polymarket.com/markets/{api_id}` per row (not the broken list-pagination path), writing `resolved`/`winning_outcome`/`resolution_date` — would very likely close the vast majority of this gap in a single bounded run (194K requests at ~10 req/s with rate-limiting ≈ 5-6 hours; parallelizable). This is the highest-leverage single fix here given the 85% flagged-trader overlap.
2. **Fix the `run_recent_overdue_pass` / `run_stale_clob_pass` handoff gap** so markets that age past 7 days unresolved don't become permanently unreachable — either have `run_recent_overdue_pass` write a sentinel `resolution_date` on non-match (careful: must not be mistaken for a real resolution date elsewhere) or have `run_stale_clob_pass` fall back to `end_date` the same way `run_recent_overdue_pass` does. Low current urgency (§2's live-monitoring evidence shows negligible active leakage), but it's the structural reason any future backlog of this shape could recur.
3. **(Lower priority, flagged not scoped here)** Gamma's new ~2,100-record offset ceiling — `fast_resolution_check.py` should move to Gamma's suggested `/markets/keyset` pagination to recover Pass 1's intended reach.

---

## 6. Follow-up Investigation 1 — Is the Generator Dormant or Live? (2026-07-01, read-only, alongside `daily_maintenance.py` PID 6794)

**Verdict, for the exact pattern that produced the 194,216 backlog: DORMANT, and structurally fixed — not just quiet.** But a second, distinct, currently-active generator was found for an adjacent pattern (§6.4) — small in scale, worth its own fix, not the same bug.

### 6.1 The mechanism — how a live market could end up like the 194,216

Traced every write path that touches `markets.end_date`:

- `monitor.py`'s `_batch_update_market_end_dates` (event-category-map refresh, every ~10 cycles) and `_backfill_clob_end_dates` (per-cycle CLOB fallback) both write `end_date` and `resolution_date` **in the same UPDATE statement**, via `resolution_date = COALESCE(resolution_date, ?)` — so `resolution_date` is always co-populated the first time `end_date` is set. Both are guarded by `WHERE end_date IS NULL`, so they only fire once per row (first population), which is exactly right.
- `database.py`'s `update_market()` (the general upsert used when a market is first seen from trade data) computes `effective_resolution_date = resolution_date if resolution_date is not None else end_date` before the INSERT, and the `ON CONFLICT` clause does `resolution_date = COALESCE(resolution_date, excluded.resolution_date, excluded.end_date)` — same pattern, same guarantee: whenever `end_date` is provided, `resolution_date` gets a value too (at minimum, `end_date` itself as a proxy).
- **These co-write functions were added in commits `4cdd190` and `446bcde`, both dated 2026-05-31** — "market end_date backfill — resolution date coverage for STR-003 signals" / "CLOB API end_date lookup — permanent resolution date coverage." Before that date, `_refresh_event_category_map` didn't write to the DB at all (verified via `git show 4cdd190` diff — the whole `_batch_update_market_end_dates` function and its call site are new in that commit).
- The one confirmed exception to the co-write guarantee anywhere in the current codebase is `scripts/fix_expired_unresolved.py`'s Task 4 (`"UPDATE markets SET end_date = ? WHERE api_id = ?"`, no `resolution_date` touch) — but this is a **hardcoded, one-off manual data-fix script** (2 specific `api_id`s, not scheduled by `daily_maintenance.py` or cron, run by hand). Not a generator.

**Confirmed empirically: zero rows in the "`end_date` set, `resolution_date` NULL" state have `last_checked` later than 2026-05-31** (`SELECT COUNT(*) ... WHERE end_date IS NOT NULL AND resolution_date IS NULL AND last_checked > '2026-05-31'` → **0**). The May 31 fix has held for 5+ weeks with zero recurrence.

### 6.2 The 1 (now 3) stuck `live_monitoring` markets — genuine leak or fluke?

Widening the filter to include not-yet-overdue markets (not just the 194,216 already-overdue ones) surfaces **3** `live_monitoring` rows in this state, not 1 — but **all 3 share the identical `last_checked` timestamp, 2026-01-12 21:11:10.** This is a second, tiny, one-time event (3 rows, not a trickle), and — critically — it **predates** the May 31 fix by 4.5 months. No commit or scheduled script matches this exact timestamp; most likely an ad-hoc/manual DB touch during early STR-003 experimentation (which the May 31 commit message explicitly references: "Putin and Newsom markets not indexed in Gamma... end_dates will be captured on next cycle").

Investigated the one **currently overdue** member of this trio directly (`0x5e15850d...42a`, title "US recession in 2027?", `end_date` 2026-05-29, `api_id` empty):
- **Neither Gamma nor CLOB recognizes this `condition_id`.** Gamma: HTTP 422 ("id is invalid" — same hex-ID rejection as O-13's finding). CLOB: `{"error": "market not found"}`. A Gamma full-text search for "recession in 2027" returns zero matches (only 2025/2026-titled recession markets from other countries/years exist).
- **28 real trades** exist for this `market_id` in our DB, spanning 2026-03-09 to 2026-05-22 — genuine trading activity, not synthetic/test data.

**Verdict: this is an O-12-class unroutable-ID fluke, not the leading edge of a slow leak.** The market was genuinely traded, but whatever ID we hold for it doesn't resolve through either live API today — a different, already-known problem (O-12), not evidence that O-16's specific `end_date`/`resolution_date` mechanism is still active.

### 6.3 The key question: does the backlog refill after backfilling?

**No — for the specific pattern this doc measures (194,216 rows: `resolved=0`, `end_date` set, `resolution_date` NULL).** Both known instances of this pattern (194,215-row Dec 11 2025 bulk import; 3-row Jan 12 2026 anomaly) predate the May 31 2026 structural fix, and zero new instances have appeared since. **A one-time backfill of the 194,216 is a permanent fix for this specific gap shape** — no code fix is required first (though §6.4's separate finding is worth fixing too, on its own timeline).

### 6.4 A different, currently-active generator found along the way (not part of the 194,216, flagged separately)

While confirming §6.3, found that **182 markets currently have `resolved = 1` (correctly resolved, with `winning_outcome` set) but `resolution_date` still NULL** — a different failure shape (resolution *did* happen; only the `resolution_date` metadata is missing). Day-by-day breakdown of `last_checked` for this population shows an **ongoing trickle through the most recent weeks** (2026-06-15 through 2026-06-30, roughly 1-57/day, not one clustered event) — this one is live.

**Root cause: `scripts/resolve_legendary_markets.py`** (scheduled **daily** via `daily_maintenance.py:50`, `["--limit", "50"]`, non-blocking) — its two `UPDATE` statements (`resolve_legendary_markets.py:210,215`) write `resolved = 1` and, where known, `winning_outcome`, but **never write `resolution_date`.** `scripts/legendary_positions_scan.py` (weekly, Monday cron) has the identical gap at its own `UPDATE markets SET resolved = 1, winning_outcome = ?` call (line 304) and `resolved = 1`-only variant (line 314).

**This matters disproportionately for data quality despite the small row count (182 total)**, because it specifically targets **LEGENDARY-tier markets** (`geo_elo_active >= 2175 AND geo_accuracy_pool = 1`) — the highest-value trader population in the system — and because `scripts/requeue_resolved_market_traders.py:76` filters newly-resolved markets via `AND datetime(resolution_date) > datetime(?)`. **Any market `resolve_legendary_markets.py` resolves never gets its traders requeued for P&L recalculation via that script**, since `resolution_date` stays NULL and the comparison never matches — a silent, compounding gap specifically in LEGENDARY-trader P&L accuracy. Not investigated further here (out of this doc's scope), but flagged as a clear, cheap, high-value fix: add `resolution_date = datetime('now')` (or a Gamma-sourced value, if available in the API response already being parsed) to both `UPDATE` statements in `resolve_legendary_markets.py` and the two in `legendary_positions_scan.py`.

---

## 7. Follow-up Investigation 2 — Backfill Design (scoping only, not implemented)

### 7.1 Runtime

Measured live, read-only, against a random sample of the actual 194,216-row target set:

| Mode | Measured throughput | Est. runtime for 194,216 |
|---|---|---|
| Sequential, no delay (20 requests) | 0.46s/req (2.17 req/s) | ~24.9 hours |
| Concurrency 5 (40 requests, `xargs -P 5`) | 10.7 req/s | ~5.0 hours |
| Concurrency 10 (80 requests, `xargs -P 10`) | 20.5 req/s, **0 non-200 responses** | ~2.6 hours |

Concurrency scaled roughly linearly from 5→10 with zero errors in these test batches, suggesting Gamma isn't aggressively rate-limiting at this depth — but these are short bursts (40-80 requests), not a sustained multi-hour run, so **recommend starting at concurrency 5 (~5-hour, safely-overnight run) with a backoff-on-429/5xx handler, and only stepping up to 8-10 if the first hour shows zero throttling.** A plain sequential run (matching the existing scripts' `time.sleep(0.1-0.2)` convention) would take ~24-32 hours — too long to call "overnight" — so some parallelism is warranted, but this is a new pattern for this codebase (existing resolution scripts are all single-threaded) and should be tested conservatively rather than assumed safe at full production scale.

### 7.2 Idempotency / Resumability

**No new progress file or checkpoint table needed — the existing `last_checked` column and the target-set query are naturally resumable, with one caveat.**

The target set is `SELECT market_id, api_id FROM markets WHERE data_source = 'historical_backfill' AND resolved = 0 AND resolution_date IS NULL` (a stable ~194,215-row set per §2 — no longer moving, per §6.3's dormant-generator finding, so no need to also filter by `end_date`/overdue-window). On each (re)start, simply **re-run this exact query**: rows already fixed by a prior partial run have `resolved = 1` now and drop out of the `WHERE` clause automatically — no separate "done" marker required. This is the same idiom `fast_resolution_check.py`'s passes already use (`last_checked ASC` rotation), just applied to a query where the drop-out condition (`resolved = 0`) is the resume signal, not `last_checked` order.

**Caveat, given "two power outages this week":** commit in small batches (e.g., every 20-50 rows, not one giant transaction and not one commit per row) — bounds both the write amplification (SQLite WAL under concurrent maintenance) and the amount of re-fetched-but-uncommitted work lost to a mid-batch crash, without either extreme. Also worth writing a plain-text progress line (`processed / total, last market_id`) to a log file each batch, matching every other script's `print(f"Checked {idx}/{total}...")` convention — not for resumability (the DB already provides that), just for visibility into how far a killed run got before restarting.

### 7.3 Confirming the Gamma per-ID lookup works for this specific population

**Confirmed, cleanly: 30/30 (100%) fresh random samples from the actual 194,216-row set returned HTTP 200 from `GET gamma-api.polymarket.com/markets/{api_id}`.** Combined with the ~65 per-ID lookups already performed across this investigation and the original O-16 measurement (all against real members of this same population), **95+/95 (100%) success rate on the direct per-ID endpoint** — this is a confirmed, working data source for the backfill; **no CLOB or on-chain fallback is needed** for the vast majority. (The list-pagination endpoint, `/markets?closed=true&order=endDate...`, is the broken one per §4 — the backfill must use the per-ID endpoint, `/markets/{api_id}`, not the list endpoint.)

One real-world wrinkle to design for: ~5% of samples return `closed: false` (genuinely still open, correctly not resolved yet — e.g. the VA-02 primary-nominee markets in §1.3). **Recommend the backfill also write `resolution_date = end_date` (no `resolved` change) for these** — matching the existing `update_market()` proxy convention already used elsewhere in the codebase — so they at least become visible to `run_stale_clob_pass` for future/normal resolution checking, rather than remaining permanently stuck outside all 4 passes the way they are today.

### 7.4 Correctness / Provenance

- **`INSERT OR REPLACE` is not used anywhere on the `markets` table in the current codebase** (`grep -rn "INSERT OR REPLACE\|REPLACE INTO"` — the only 2 matches are `monitoring_status` and `baselines`, unrelated tables). Every existing resolution-writer (`update_market_resolution`, all 4 `fast_resolution_check.py` passes, `resolve_legendary_markets.py`) uses a plain `UPDATE markets SET ... WHERE market_id = ?` — touches only the named columns, cannot wipe unrelated ones. **The backfill should follow this exact same pattern** — plain `UPDATE`, never `INSERT OR REPLACE` — to avoid any risk of reintroducing the column-wiping bug already fixed elsewhere (per the positions-table `ON CONFLICT DO UPDATE` fix referenced in the 2026-06-25 session summary).
- **Provenance:** write a new, explicit `data_source` value on touched rows — e.g. `'gamma_backfill_2026-07-01'` — rather than leaving `data_source = 'historical_backfill'` in place or silently overwriting it to `'live_monitoring'`. This preserves an honest audit trail (these rows were bulk-imported without resolution data, then later backfilled by a dedicated one-time script) and won't be mistaken for either the original import or the organic live-monitoring pipeline in any future forensic investigation like this one. Set `resolution_date` to the actual value read from Gamma (`umaEndDate`/`closedTime`, or the market's own `endDate` if that's absent too — matching this doc's finding that these markets don't have `endDate` populated on Gamma's side; `closedTime` is the closest real resolution-date value.

### 7.5 Prioritization

Exact breakdown of the 194,216 by trader relevance (same join as §3):

| Tier | Count | % | Criterion |
|---|---|---|---|
| 1 — highest value | 62,407 | 32% | Has a trade from a flagged, non-research-excluded trader |
| 2 — some value | 5,883 | 3% | Has a trade, but not from a flagged/clean trader |
| 3 — no known trade | 125,926 | 65% | No trade record in our DB at all |

**Recommend processing in exactly this tier order.** Tier 1 (62,407) alone, at the concurrency-5 throughput measured in §7.1, is roughly a 1.6-hour run — it recovers essentially all of the ELO/signal-relevant value (the 85%-of-flagged-traders finding in §3) in a bounded, low-risk first pass, with Tiers 2-3 following as lower-priority, resumable continuation work rather than blocking the highest-value data from landing quickly.

---

## 8. Files Referenced

| File | Role |
|------|------|
| `scripts/fast_resolution_check.py:132-134` | `fetch_all_resolved_markets`'s coded 50K safety limit — never reached; real ceiling is Gamma's own offset error at ~2,100 |
| `scripts/fast_resolution_check.py:412-513` | `run_recent_overdue_pass` — updates `last_checked` on every check but never `resolution_date` on non-match; source of the orphaning mechanism in §2 |
| `scripts/fast_resolution_check.py:315-411` | `run_stale_clob_pass` — hard-requires `resolution_date IS NOT NULL`, structurally excluding anything `run_recent_overdue_pass` didn't resolve |
| `scripts/daily_maintenance.py:46` | Where `fast_resolution_check.py --stale-limit 500` is scheduled daily |
| `data/polymarket_tracker.db` `markets.data_source` | The `historical_backfill` vs `live_monitoring` distinction that proves §2's static-not-growing verdict |
| `2026-07-01-o13-monitoring-blocking-stall-design.md` §5b | The 724-market segment that prompted this broader measurement; same 2025-12-11 forensic timestamp appears in both |
| `monitoring/monitor.py:205-232` | `_batch_update_market_end_dates` — confirmed co-writes `resolution_date` whenever `end_date` is first set (§6.1) |
| `monitoring/monitor.py:234-288` | `_backfill_clob_end_dates` — same co-write guarantee, CLOB-sourced path (§6.1) |
| `monitoring/database.py:434-467` | `update_market()` — the general upsert; `ON CONFLICT` co-writes `resolution_date` via `COALESCE(..., excluded.end_date)` (§6.1) |
| commits `4cdd190`, `446bcde` (2026-05-31) | The structural fix that makes §6.1's dormant-generator verdict hold — introduced the co-write pattern repo-wide |
| `scripts/fix_expired_unresolved.py:228-231` | The one confirmed exception to the co-write guarantee — a hardcoded, unscheduled, 2-row manual fix script, not a generator (§6.1) |
| `scripts/resolve_legendary_markets.py:210,215` | Daily-scheduled (`daily_maintenance.py:50`), resolves LEGENDARY-tier markets but never writes `resolution_date` — the live, currently-active generator found in §6.4 |
| `scripts/legendary_positions_scan.py:304,314` | Weekly (Monday cron), same missing-`resolution_date` gap as above (§6.4) |
| `scripts/requeue_resolved_market_traders.py:76` | The downstream consumer silently broken by §6.4's gap — its `resolution_date > ?` filter never matches a NULL `resolution_date` |
