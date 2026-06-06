# Session Summary — Server Setup #25
**Date:** 2026-06-06

---

## Critical Bugs Fixed

- **market-intelligence-agent.md:** wrong JOIN key (`market_id=condition_id`) silently dropping 37% of trades — fixed
- **performance-analyst-agent.md:** `elo_score` column does not exist — fixed to `comprehensive_elo` throughout (9 locations)
- **signal-agent.md:** dropped `accuracy_pool` column reference, stale `pnl>500` filter, wrong `market_category` field — fixed
- **integration-test-agent.md:** alert thresholds 22× too low (`clean_pool>=450` → `>=10000`) — fixed
- **feedback-loop-agent.md + performance-analyst-agent.md:** `condition_id` used as join key (NULL for 53% of markets including all 3 active STR-003 signals) → fixed to `market_id`
- **pre_resolution_intelligence.py:** LEGENDARY threshold using `comprehensive_elo` instead of `geo_elo` — fixed
- **pre_resolution_loop:** timing bug (was never firing) — fixed to date-based `last_run_date` tracking
- **market-builder.md:** CLOB V2 breaking changes warning missing (3 weeks unfixed) — fixed
- **STR-005 file header** reading STR-004 — fixed
- **backup_database.sh:** `KEEP_DAYS=7` → `3`

---

## Infrastructure

- LVM disk expanded: 200GB → 1.82TB (12GB free → 1.6TB free)
- Backup cleanup: 5 old backups deleted (freed ~35GB)
- Pre-resolution intelligence: now live, 12 signals sent, 44 markets checked
- Sunday ELO timer: verified, fires 03:00 UTC June 7 (first ever run)

---

## Template Consistency Overhaul

- Full audit of all 14 agent templates against `integration-contract.md`
- Section 10 added to `integration-contract.md`: Canonical Agent Definitions (ELO thresholds, pool filters, output paths, STR-003 criteria, known limitations)
- Section 10 canonical reference header added to 5 highest-risk templates
- Training-librarian Responsibility 8 added: weekly template consistency audit
- Training-librarian test run: successful, found and fixed 5 additional issues autonomously
- Integration contract bumped to v2.4

---

## Schema Change Log

- `brain/schema-change-log.md` created: 6 entries (SCL-001 through SCL-006)
- Tracks all breaking changes with propagation status across all templates
- Training-librarian reads it weekly as Step 0 of Responsibility 8
- 3 templates flagged for pending verification next Saturday (June 13)

---

## Research Pipeline

- Research-to-signal pipeline gap identified: 7 actionable HIGH findings, zero automated into system
- Sunday research review protocol established: Telegram reminder sent
- 4 pending research-scout items approved (DeepSeek V4, ForesightFlow ILS, arXiv 2605.02287, CLOB V2)
- RQ-ILS-001 pre-registered (defer July 1)
- RQ-EXT-001a/b/c pre-registered (after Peru resolution June 8)
- Manual research session found: Polymarket-v1 Database (arXiv 2606.04217), Prediction Arena AI models paper, geopolitics fee-free confirmation
- market-builder CLOB V2 fix: 3-week outstanding item resolved

---

## External Dataset Integration

- `vgregoire/polymarket-users` downloaded: `user_pnl_summary.parquet` (495MB) + `user_features.parquet` (768MB)
- Cross-reference findings:
  - `geo_directionality_score` correlation with `frac_both_sides`: −0.135 (near-zero — LP filter nearly ineffective)
  - `0xecaa8806` is 76% maker, 74% both-sides — primarily market maker, not conviction trader
  - P&L gaps explained by data completeness (external covers Nov 2022, our DB from Jan 2024)
  - Pool C mean `frac_both_sides` = 0.513 — significant LP contamination
- Decision gate: no Pool C or STR-003 changes until Peru resolution + RQ-EXT-001 results

---

## Trader Discovery Overhaul

- Root cause identified: leaderboard-based discovery misses patient directional traders
- 99 genuine directional politics traders in external dataset — only 6 in our DB
- `/holders` API endpoint identified as superior to `/trades` for resolved market discovery
- Layer 1 complete: 3 Tier 1 traders added (Nocthyra `0x040f`, Calythius `0x90fe`, anonymous `0xb464`)
- Layer 2 complete: 195 `external_seed` traders batch-inserted from parquet
- Layer 3 documented: resolution-triggered `/holders` sweep (next session)
- `integration-contract.md` v2.4 reflects new pool composition

---

## STR-003 Signal Status

- STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES): mutual exclusivity documented
- Sánchez Palomino market: Unknown category fixed to Elections, 0 geo LEGENDARY traders confirmed (STR-003 correctly did not fire)
- Pre-resolution scan: 12 signals across 44 markets, all sent to Telegram
- First real STR-003 accuracy test: Peru resolves June 7, scored June 8

---

## Pending Next Session

- [ ] Score Peru signals June 8 (STR003-005, STR003-006)
- [ ] Investigate Sánchez Palomino `comprehensive_elo` LEGENDARY accuracy post-resolution
- [ ] Layer 3: `/holders` endpoint sweep implementation
- [ ] RQ-EXT-001a/b/c analysis after Peru resolution
- [ ] Legacy template audit (backtest-agent, integration-test-agent — SCL-001/002/004 verification)
- [ ] `0x9d31ca01` maker verification before adding to watchlist
- [ ] Parquet Layer 2 seed ELO scores: check backfill progress
