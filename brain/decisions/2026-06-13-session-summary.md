# Session Summary — Server Setup #33
**Date:** 2026-06-13

---

## System Health
ELO snapshots: 3 days (2848 → 2850 → 2851). Order book snapshots: Day 2.
Both Step 19 and Step 20 firing in daily maintenance.
Backup log permission fixed — nightly 02:00 UTC now running cleanly.
Peru oracle: still unresolved, Polymarket 97% Keiko, ONPE mid-July expected.

---

## Backup Fix
Log file at ~/trading-swarm/logs/backup_offsite.log had wrong permissions (root-owned).
Fixed: touch + chown parison. Test run confirmed: June 12 + June 13 directories both
present on /mnt/backup. Drive usage 4.7G. Backup confirmed production-ready.

---

## Market-Relative Scoring (Fable §5.1.1)

### Root cause investigation
Order book mid_price = 0.5 for all active signals — artifact of empty books on
near-resolved markets (bid=0.001, ask=0.999). Not a bug in capture logic.
Gamma conditionIds lookup broken (silently returns popular list for unrecognised IDs).
CLOB /markets/{condition_id} is the correct authoritative price source.

### What was built
score_str003_signals.py:
- edge_at_entry = outcome_correct - market_implied_prob_at_registration
- YES signal: market_implied = market_price_at_registration
- NO signal: market_implied = 1 - market_price_at_registration
- Forward-only: null for legacy signals 001-009 (no registration price stored)
- Accuracy report now includes edge section

snapshot_order_books.py:
- fetch_clob_market_price() added — hits CLOB /markets/{condition_id} for real YES price
- clob_market_price_yes column added to order_book_snapshots table
- Replaces mid_price (meaningless for near-resolved markets) with authoritative price
- STR003-007: YES=0.0075, STR003-008: YES=0.0125 confirmed

STR003-007 and STR003-008: market_price_at_first_capture backfilled (late capture,
flagged with capture_note). edge_at_entry will compute when they resolve June 30.

---

## register_signal.py — Canonical Signal Registration Utility

The single chokepoint through which every STR-003 signal is born.
Direct writes to signals.json are now PROHIBITED — they caused the 001-006 vs 007-009
schema bifurcation.

### What it does atomically
1. Validates inputs (market exists, unresolved, direction valid)
2. Fetches market_price_at_registration from CLOB at exact registration moment
3. Captures registration order-book snapshot (snapshot_type='registration')
4. Looks up each trader's geo_elo_active (point-in-time from live DB)
5. Reads each trader's archetype from brain/trader-profiles/_index.json
6. Computes signal_credibility_score via signal_credibility.py
7. Generates next sequential signal_id (STR003-NNN)
8. Stamps registered_at timestamp
9. Validates all 20 canonical schema fields
10. Writes to signals.json atomically under file lock

### Dry-run validation (Iran market, 2 LEGENDARY traders)
- market_price_at_registration: 0.0075 (live CLOB price) ✅
- trader_elos_at_registration: {0xecaa8806: 3664.0, 0xbbd22b1ace: 2919.7} ✅
- trader_archetypes: {GENUINE_FORECASTER, DOMAIN_SPECIALIST} ✅
- legendary_count: 2 ✅
- signal_credibility_score: 80.0, tier: HIGH ✅
- All 20 canonical fields present ✅

### signal-agent template updated
Both duplicate stale registration blocks replaced with single canonical section
pointing to register_signal.py CLI. Dry-run workflow documented.

---

## Integration Contract v2.9
- Section 7: Step 20 snapshot_order_books.py added
- Section 9: Live numbers updated (pool_c=2,851, legendary_base=48, legendary_active=25,
  legendary_clean=18, near_legendary_clean=21, clean_pool=18,910)
- Section 13 (new): Signal Registration Protocol
- Section 14 (new): Order Book Capture Infrastructure
- Section 15 (new): Backup Infrastructure
- Section 8: v2.9 changelog entry

---

## Fable Roadmap Backlog — Status

### Completed across Sessions 31-33
✅ Offsite backup (USB, nightly 02:00 UTC, 14-day retention)
✅ Order-book capture (Step 20, clob_market_price_yes, registration snapshots)
✅ Event-cluster + correlated_with fields on all signals
✅ CLAUDE.md phase table updated
✅ STR003-005 scored CORRECT
✅ STR003-006 outcome_correct fixed
✅ Signal schema canonicalised (register_signal.py)
✅ Market-relative scoring (edge_at_entry, forward-only)
✅ STR003-007 non_scorable_for_validation tagged
✅ STR-004 re-specification note in strategy-registry
✅ April 28 structural break in integration contract
✅ RQ-CONTESTED-ARCHETYPE-001 pre-registered for July 1
✅ Provisional scoring rule in integration contract

### Remaining Fable items
⏳ Counter-signal detector — earliest June 18 (7 snapshot days)
⏳ STR-002 scoring loop — Gate 3 blocker, build before July 1
⏳ Snapshot-driven replay harness — design now, build July
⏳ Calibration layer — Phase 6 build
⏳ RQ-SCI-001 historical leg — can run anytime, pre-register first

---

## Pending (Next Session Priority)

### Must happen before June 30 (17 days):
1. STR-002 scoring loop (score_str002_signals.py) — Gate 3 blocker
2. Check Maine RCV results — Bellows/Midgley primaries

### June 18 (earliest):
3. Counter-signal detector (7 snapshot days minimum from June 11)

### June 30:
4. Score STR003-004, STR003-007, STR003-008
5. Run RQ-CORRELATION-001 on cluster outcome
6. Note: STR003-007 is non_scorable_for_validation (hindsight contamination)

### July 1:
7. Wave 1: RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001
8. Wave 2: RQ-EXEC-001, RQ-PNLGATE-001, RQ-CONTESTED-ARCHETYPE-001
9. Wave 3 prep: RQ-EXT-001 (Aug 1)

---

## Pool Status (end of session)
| Metric | Value |
|--------|-------|
| Pool C | 2,851 |
| LEGENDARY active clean | 18 |
| NEAR_LEGENDARY clean | 21 |
| elo_snapshots | Day 3 (June 11-13) |
| Order book snapshots | Day 2 (June 12-13) |
| STR-003 scored | 1/4 (25%) — all pre-current-stack |
| STR-003 ACTIVE | 3 (004, 007, 008 — resolve June 30) |
| register_signal.py | Production-ready, tested, wired into signal-agent |
| Integration contract | v2.9 |
| Backup | Confirmed running nightly |

