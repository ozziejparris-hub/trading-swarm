# Session Summary — Server Setup #32
**Date:** 2026-06-12

---

## System Health Check
Snapshot step confirmed firing in daily maintenance pipeline (first run in pipeline).
June 12 snapshot: 2,850 Pool C traders (up 2 from June 11 baseline — manual_watchlist
fix propagating). Both monitoring services active and healthy.

## Peru Oracle
Still unresolved. At 98% counted, ~600 vote margin fluctuating between Keiko and Sánchez.
ONPE warned mid-July proclamation possible. STR003-005 provisional CORRECT scoring
unchanged — not re-scored. Monitor daily.

---

## Tier 1 Completions (from Fable strategic roadmap)

### 1. Offsite Backup ✅
- 1TB USB drive formatted ext4, mounted at /mnt/backup (LABEL=polymarket-backup)
- Added to /etc/fstab with nofail
- scripts/backup_offsite.sh: nightly 02:00 UTC, WAL checkpoint + gzip DB copy + rsync brain/
- 14-day retention on DB snapshots
- Test run PASSED: DB compressed 8.7GB → 2.3G, brain/ synced
- Crontab: 0 2 * * *
- Commit: ade97aa

### 2. Order-Book Capture ✅ (with bug fixes)
- SCL-009: clob_token_id_yes/no columns on markets table + order_book_snapshots table
- scripts/backfill_clob_token_ids.py: fetches CLOB token IDs per market
- scripts/snapshot_order_books.py: daily snapshot of active signal markets, Step 20 in maintenance
- BUGS FOUND AND FIXED:
  - Gamma conditionIds param silently ignores unrecognised IDs, returns default popular list
  - backfill_clob_token_ids.py took markets[0] without verification → all 3 markets got
    "Rihanna album" tokens
  - Fixed: CLOB API now primary lookup; Gamma fallback verifies conditionId match
  - STR003-007 and STR003-008 corrected with real tokens
  - STR003-004 tokens NULL (CLOB 404 — likely neg_risk/archived market, last trade Dec 2025)
- First real snapshots captured: STR003-007 mid=0.500 spread=0.998 bid_depth=867K (correct — Iran NO near-resolved)
- History clock running from 2026-06-12

### 3. Event-Cluster Field ✅
- event_cluster and correlated_with fields added to all 8 STR-003 signals
- Correlated pairs: Peru 005/006, Iran/Europe 007/008
- June 30 three-signal batch now formally tagged as correlated

---

## Fable Roadmap Items Completed

- STR003-007: non_scorable_for_validation=true — registered after 32pp market move (hindsight contamination)
- STR-004: re-specification required note in strategy-registry.md — wrong ELO metric + no archetype filter
- Integration contract §6d: April 28 2026 structural break formally documented — pre/post pooling prohibited
- RQ-CONTESTED-ARCHETYPE-001: pre-registered for July 1 Wave 2 — geo_elo LEGENDARY accuracy on contested markets, archetype-filtered (GENUINE_FORECASTER + DOMAIN_SPECIALIST only), pass threshold ≥70%

---

## Market-Relative Scoring — Deferred to Tomorrow
Registration prices not stored for legacy signals — edge_at_entry is forward-only.
Existing price fields (avg_entry_price, market_price_at_scoring) are wrong concepts.
score_str003_signals.py modification designed but not built — requires fresh session.
Must exist before June 30 scoring.

---

## Integration Contract — Deferred to Tomorrow
v2.8 needs updating for:
- SCL-009 new schema (order_book_snapshots, clob_token_id columns)
- Provisional scoring rule (Keiko precedent formalised)
- Section 6d April 28 break (added today but contract version not bumped)
- New signal schema fields (event_cluster, correlated_with, non_scorable_for_validation)

---

## Pending (Priority Order)

### Must exist before June 30:
1. Market-relative scoring in score_str003_signals.py
   - edge_at_entry = forward-only (no registration price on legacy signals)
   - Capture market_price_at_registration at signal registration time going forward
2. Integration contract v2.9 update

### June 18 (earliest):
3. Counter-signal detector (7 snapshot days minimum)

### June 30:
4. Score STR003-004, STR003-007, STR003-008
5. Run RQ-CORRELATION-001 on the cluster outcome

### July 1:
6. Wave 1: RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001
7. Wave 2: RQ-EXEC-001, RQ-PNLGATE-001, RQ-CONTESTED-ARCHETYPE-001
8. STR-002 scoring loop (Gate 3 blocker)

### August 1:
9. RQ-EXT-001a/b/c rerun

---

## ELO and Pool Status
| Metric | Value |
|--------|-------|
| Pool C | 2,850 (June 12 snapshot) |
| elo_snapshots | Day 2 (June 12) |
| Order book snapshots | Day 1 (June 12) |
| STR-003 scored | 1/4 (25%) — all pre-current-stack |
| STR-003 ACTIVE | 3 (004, 007, 008 — all resolve June 30) |
| STR003-007 | non_scorable_for_validation (hindsight) |
| Offsite backup | LIVE — nightly 02:00 UTC |

