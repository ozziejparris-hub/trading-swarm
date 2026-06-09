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
- [ ] integration-test-agent.md — verify no condition_id join keys
- [ ] backtest-agent.md — verify no condition_id join keys
- [ ] quant-research.md — verify no condition_id join keys
- [ ] market-intelligence-agent.md — verify no condition_id join keys
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
- [ ] backtest-agent.md — verify no references
- [ ] quant-research.md — verify no references
- [ ] feedback-loop-agent.md — verify no references
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
- [ ] backtest-agent.md — verify JOIN keys
- [ ] quant-research.md — verify JOIN keys
- [ ] feedback-loop-agent.md — verify JOIN keys
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

## Pending verification items
These templates have not been fully audited against all SCL entries:
- backtest-agent.md — SCL-001, SCL-002, SCL-004 unverified
- integration-test-agent.md — SCL-001 unverified
- quant-research.md — SCL-001, SCL-002, SCL-004 partially verified

Training-librarian should check these in the next weekly audit (June 13).
