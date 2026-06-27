# Schema Change Log
**Location:** brain/schema-change-log.md
**Mandatory reading:** Any agent writing DB queries must read this file before starting.
**Maintained by:** training-librarian-agent (weekly audit) + Oscar (on breaking changes)

---

## How to use this log
When a breaking schema change is made:
1. Add an entry here immediately
2. List every template and script that needs updating
3. Check off each one as updated
4. Training-librarian verifies completion in next weekly audit

If you are an agent reading this log: check every entry marked PROPAGATION INCOMPLETE and fix the affected templates/scripts before proceeding with your task.

---

## Change Log

### SCL-001 — market_id vs condition_id distinction
**Date:** 2026-05-20
**Version:** integration-contract v1.3
**Type:** Key definition clarification — BREAKING
**Description:**
condition_id was incorrectly used as a join key in several templates. Clarified:
- market_id — TEXT NOT NULL, primary DB join key, populated for ALL rows
- condition_id — TEXT nullable, Polymarket external API identifier only, NULL for ~53% of markets
Using condition_id as a join key silently returns 0 rows for ~53% of markets including all active STR-003 signals.
**Affected templates (requiring fix):**
- [x] feedback-loop-agent.md — fixed 2026-06-06
- [x] performance-analyst-agent.md — fixed 2026-06-06
- [x] integration-test-agent.md — verified 2026-06-13 (no condition_id join keys; pool size check only)
- [x] backtest-agent.md — verified 2026-06-13 (no SQL queries; Rule 3 specifies correct Pool B filter)
- [x] quant-research.md — verified 2026-06-13 (correct column names; no condition_id join)
- [x] market-intelligence-agent.md — verified 2026-06-13 (JOIN keys fixed 2026-06-06 per SCL-004)
**Reference:** integration-contract.md Section 2

---

### SCL-002 — geo_elo_oos, accuracy_pool, copyable_edge columns dropped
**Date:** 2026-06-05
**Type:** Column removal — BREAKING
**Description:**
Three columns dropped from traders table:
- geo_elo_oos — removed (out-of-sample ELO metric, superseded)
- accuracy_pool — removed (replaced by geo_accuracy_pool)
- copyable_edge — removed (unused)
Any query referencing these columns will throw "no such column" errors.
**Affected templates (requiring fix):**
- [x] signal-agent.md — accuracy_pool removed 2026-06-06
- [x] integration-contract.md Section 3 — documented 2026-06-06
- [x] scripts/calculate_geo_elo.py — accuracy_pool → geo_accuracy_pool fixed 2026-06-08
- [x] backtest-agent.md — verified 2026-06-13 (no SQL queries; no dropped column references)
- [x] quant-research.md — verified 2026-06-13 (no dropped column references)
- [x] feedback-loop-agent.md — verified 2026-06-13 (no geo_elo_oos, accuracy_pool, copyable_edge references)
**Reference:** integration-contract.md Section 3

---

### SCL-003 — comprehensive_elo vs geo_elo distinction
**Date:** 2026-06-06
**Type:** Metric definition clarification — BREAKING for signal generation
**Description:**
comprehensive_elo and geo_elo are different metrics with different use cases:
- comprehensive_elo — all-market ELO, 2.3x accumulation bias toward easy markets. Use for bot detection and Pool B qualification ONLY.
- geo_elo — geopolitics/elections specialist ELO. Use for signal generation and STR-003.
- geo_elo_active — recency-decayed geo_elo. Use for STR-003 qualification specifically.
Using comprehensive_elo for signal generation produces no proven edge on contested markets.
**Affected templates requiring fix:**
- [x] signal-agent.md — fixed 2026-06-06
- [x] performance-analyst-agent.md — elo_score → comprehensive_elo fixed 2026-06-06
- [x] research.md — geo_elo vs comprehensive_elo distinction added 2026-06-06
- [x] orchestrator-system.md — ELO column names specified 2026-06-06
- [x] quant-research.md — ELO column names specified 2026-06-06
- [x] feedback-loop-agent.md — ELO column names specified 2026-06-06
- [x] market-intelligence-agent.md — elo_score → comprehensive_elo fixed 2026-06-06
- [x] pre_resolution_intelligence.py — geo_elo threshold fixed 2026-06-06
- [x] scripts/verify_market_titles.py in first-repo — fixed 2026-06-08
- [x] monitoring/system_observer.py in first-repo — fixed 2026-06-07 (LEGENDARY badge threshold)

**PROPAGATION COMPLETE** — all items resolved as of 2026-06-07.
**Reference:** integration-contract.md Section 10.1

---

### SCL-004 — trades JOIN key correction
**Date:** 2026-06-06 (discovered — original error unknown)
**Type:** Wrong JOIN key — BREAKING (silently drops 37% of trades)
**Description:**
Correct JOIN between trades and markets:
JOIN trades t ON t.market_id = m.market_id
WRONG (silently drops 37% of trades):
JOIN trades t ON t.market_id = m.condition_id
The condition_id column in the markets table is NULL for 53% of rows. Using it as a JOIN key drops all those trades silently.
**Affected templates requiring fix:**
- [x] market-intelligence-agent.md — 3 queries fixed 2026-06-06
- [x] backtest-agent.md — verified 2026-06-13 (no JOIN queries; process template only)
- [x] quant-research.md — verified 2026-06-13 (no explicit JOIN queries; references integration-contract.md)
- [ ] feedback-loop-agent.md — PENDING OSCAR REVIEW: Step 1 has condition_id vs market_id semantic conflict flagged 2026-06-06; requires Oscar to confirm signal payload values before changing
**Reference:** integration-contract.md Section 2 + Section 10 JOIN KEY WARNING

---

### SCL-005 — Pool B filter completeness requirement
**Date:** 2026-06-06
**Type:** Filter definition — BREAKING for accuracy calculations
**Description:**
research_excluded = 0 alone is INSUFFICIENT as a research pool filter.
Correct Pool B filter:
research_excluded = 0 AND resolved_trades_count >= 20 AND bot_type IS NULL
Using research_excluded = 0 alone includes 13,000+ leaderboard traders with <20 resolved trades, contaminating accuracy calculations.
**Affected templates requiring fix:**
- [x] backtest-agent.md — fixed 2026-06-06
- [x] feedback-loop-agent.md — fixed 2026-06-06
- [x] quant-research.md — fixed 2026-06-06
- [x] integration-contract.md Section 10.2 — documented 2026-06-06
**Reference:** integration-contract.md Section 10.2

---

### SCL-006 — external_seed discovery_source added
**Date:** 2026-06-06
**Type:** New column value — non-breaking
**Description:**
195 traders inserted with discovery_source = 'external_seed' from vgregoire/polymarket-users HuggingFace dataset. These traders have no trade history in our DB yet — backfill worker will populate. Do not include in ELO calculations until resolved_trades_count >= 20.
**No template changes required.**
**Reference:** brain/strategy-notes/trader-discovery-overhaul-2026-06-06.md

---

### SCL-007 — system_observer.py alert thresholds not updated since pre-Phase 5
**Date:** 2026-06-07
**Type:** Configuration drift — non-breaking but produces misleading alerts
**Description:**
system_observer.py has two threshold issues:
1. LEGENDARY tier badge uses comprehensive_elo >= 2500 (line ~1238). Per SCL-003 and integration-contract Section 10.1, LEGENDARY should use geo_elo >= 2175 AND geo_accuracy_pool = 1. comprehensive_elo is for bot detection only.
2. Error rate thresholds (error_rate < 10 = healthy, < 30 = warning, >= 30 = critical) were set before backfill of large trader batches. During backfill of 100+ traders, DB lock contention produces 15-24 errors per 10 minutes which triggers CRITICAL alerts that are actually expected behaviour.
**Affected files requiring fix:**
- [ ] monitoring/system_observer.py (~line 1238) — LEGENDARY threshold: comprehensive_elo >= 2500 → geo_elo >= 2175 AND geo_accuracy_pool = 1
- [ ] monitoring/system_observer.py (~lines 1989-1991) — error rate thresholds: consider raising CRITICAL from 30 to 50 during backfill periods, or add a backfill-mode suppression
**Reference:** integration-contract.md Section 10.1, SCL-003

---

### SCL-008 — legendary_positions_scan.py canonical filters
**Date:** 2026-06-09
**Type:** New script — canonical definitions enforced
**Description:**
New script uses geo_elo_active >= 2175 AND geo_accuracy_pool = 1 for LEGENDARY (not comprehensive_elo).
Also uses research_excluded = 0 AND bot_type IS NULL for pool filter (full Pool B contract).
Markets where Gamma API returns no price are skipped (not reported with stale data).
MIXED_SIGNAL flag added: both_sides_ratio > 0.3 indicates LEGENDARY traders hold both sides.
**Affected:** scripts/legendary_positions_scan.py — PROPAGATION COMPLETE on creation.

---

### SCL-009 — order_book_snapshots table + clob_token_id columns
**Date:** 2026-06-12
**Type:** New table + new columns
**Description:**
Two new columns on markets table: clob_token_id_yes TEXT, clob_token_id_no TEXT.
Stores Polymarket CLOB outcome token IDs for YES and NO sides.
Fetched from Gamma API via conditionIds lookup (api_id not reliable for all markets).
New table order_book_snapshots captures top-10 bid/ask levels for active signal markets.
Purpose: Phase 6 paper trading fill simulator needs real book history; cannot be backfilled.
**Affected:** markets table, new order_book_snapshots table. No downstream scripts consume
these columns yet — pure data capture. PROPAGATION: N/A (new columns, no existing queries break).

---

---

### SCL-010 — Datetime format normalisation (Section 16)
**Date:** 2026-06-15
**Contract version:** integration-contract v2.10
**Type:** Canonical format standard — BREAKING for ingestion paths
**Description:**
normalize_market_dates.py normalised 471,561 values across resolution_date, end_date, and last_checked columns, removing T-separator/Z-suffix formats that caused SQLite string comparison to misorder dates and silently hide 976+ markets from all resolution passes for weeks. Section 16 added as the authoritative datetime format standard. All dates in the DB are now plain YYYY-MM-DD or YYYY-MM-DD HH:MM:SS without T-separators or Z-suffixes. Any ingestion path writing datetime values MUST normalise before writing.
**Affected templates (requiring fix):**
- [x] market-builder.md — verified 2026-06-27: explicitly states "New market data must never write to polymarket_tracker.db" — no datetime writes possible. No fix needed.
- [ ] All other templates that instruct agents to write datetime values to the DB — check for ISO 8601 T-separator format and remove it. Remaining scope: any new agent templates that generate DB writes.
**Note:** This SCL was not added at time of change (2026-06-15). Added retrospectively by training-librarian-agent 2026-06-20 during weekly audit after identifying gap in v2.10–v2.12 contract changes with no SCL entries.
**Reference:** integration-contract.md Section 16

---

### SCL-011 — Column authority registry (Section 18)
**Date:** 2026-06-18
**Contract version:** integration-contract v2.11
**Type:** Governance standard — BREAKING for write patterns
**Description:**
Single-writer principle codified. Layer 1 aggregate columns on the traders table are now owned by reconcile_trader_aggregates.py:
- total_trades, successful_trades, total_volume — direct aggregates from positions
- win_rate — derived from the above
- total_invested, avg_roi, realized_pnl, open_positions, closed_positions — position-derived
- specialisation_ratio — from analysis_scheduler.py (pending consolidation)
Any agent or script writing these columns directly creates a competing writer. Route all aggregate writes through reconcile_trader_aggregates.py.
Section 18.3 provides the full column authority registry (~37 columns, 5 governance classes).
**Affected:**
- All agents that write to the traders table (signal-agent, feedback-loop-agent if updating trader records) — READ SECTION 18.3 before writing any traders column.
- Verified 2026-06-27: signal-agent.md and feedback-loop-agent.md are READ-ONLY on the traders table. Neither template instructs writing traders columns. Section 18.3 compliance is met for these two agents.
- DEAD columns pending drop: unrealized_pnl, total_pnl, roi_percentage — do not reference these.
**Reference:** integration-contract.md Section 18

---

### SCL-012 — Definitions module live + Section 18.5.1 updated (v2.12–v2.13)
**Date:** 2026-06-23
**Contract versions:** v2.12 (2026-06-18), v2.13 (2026-06-23)
**Type:** Governance/documentation — NO template propagation required
**Description:**
v2.12: Section 18.5.1 acknowledged cross-repo source-of-truth gap and planned definitions-module fix.
v2.13: `monitoring/column_definitions.py` built and live as single canonical source for 6 data-integrity consumers. Tier-1 definitions-module complete — harness-vs-writer divergence now impossible for covered columns. Tier-2 scope (13 read-side scripts) is next milestone.
**Template impact:** None — no new column definitions or schema changes. Agents already directed to Section 10 via existing warning blocks. Agents must NOT write covered Layer 1 columns directly; route through reconcile_trader_aggregates.py.
**PROPAGATION COMPLETE** — no template changes required.
**Reference:** integration-contract.md Section 8 (v2.12, v2.13), Section 18.5.1

---

## Pending verification items
Last full audit: 2026-06-27 (training-librarian-agent)

All SCL-001 through SCL-012 items — status as of 2026-06-27:
- **feedback-loop-agent.md (SCL-004):** condition_id → market_id semantic conflict in Step 1 signal payload lookup. PENDING OSCAR REVIEW (open since 2026-06-06). Requires confirmation of what value is stored in signal.payload.market_id before changing WHERE clause.
- **SCL-010:** All other templates with datetime DB writes — remaining scope is limited (market-builder verified clean). Low risk: most agent templates are read-only.
- **SCL-007:** system_observer.py LEGENDARY threshold + error rate thresholds — still unresolved (in first-repo, outside training-librarian scope). Flag for Oscar.
