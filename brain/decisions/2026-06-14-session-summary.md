# Session Summary — Server Setup #34
**Date:** 2026-06-14

---

## System Health (startup)
ELO snapshots: 4 days (2848→2850→2851→2875 — Sunday recalc ran, Pool C +24).
Order book snapshots accumulating (STR003-007=5, STR003-008=4).
Backup ran 02:00 UTC cleanly (7.0G drive).
Peru: confirmed genuinely unresolved on Polymarket (CLOB closed=False, ONPE mid-July).
Maine RCV: confirmed still tabulating (no UMA finalization — 95% trading price ≠ resolved).

---

## Telegram Freeze Fix (permanent)
Two freezes in 36h (June 12 22:26, June 14 01:43). Root cause: bot.send_message() has
no timeout by default; hangs indefinitely when Telegram rate-limits at connection level
(no 429 raised, just no response). Fix: wrapped all send calls in asyncio.wait_for(
timeout=15) + read/write/connect_timeout=10. TimeoutError handler added before generic
Exception so timeouts fail fast and retry. Observer restarted. Commit 0f02f14.

---

## Resolution Pipeline Gap Fixes
Diagnosed why 14+ signal markets remained resolved=0 despite being past end_date.
Three-layer problem:
1. Gamma bulk scan has 20K recency cap — older/unindexed markets missed
2. Stale CLOB pass (>7 days) too slow for recently-resolved markets
3. Recent markets (0-7 days past resolution) with NULL condition_id or NULL
   resolution_date (only end_date populated) fell through all three passes

Fix: new run_recent_overdue_pass() method in fast_resolution_check.py:
- Catches markets 0-7 days past resolution (either resolution_date OR end_date fallback)
- No api_id filter (catches both NULL and populated api_id markets Gamma missed)
- Runs as Step 3a in run_fast_check before the stale pass
- Confirmed working: resolved 10+ markets in live run

Commit 7033669. Cosmetic label fix + requirements.txt additions commit a67f358.

---

## Resolution Semantics — UMA Oracle (Section 14b)
Researched Polymarket's official resolution docs. Key finding enshrined in contract:
- ended (past end_date, price ~0.99) ≠ resolved
- A market is ONLY resolved when: closed=true AND a token has winner=true (UMA finalized)
- Resolution scripts already correctly check both conditions before marking resolved
- Dispute window: 2h undisputed; 24-48h debate + ~48h UMA vote if disputed
- Provisional exception (Section 13): only Peru STR003-005 pattern, always flagged
- Historical synthetic-resolution audit flagged as pending future session

---

## STR-002 Signal Registry + Scorer (Gate 3 infrastructure)

### Design
"First-seen wins" principle: a signal = first time a market+direction crosses divergence
threshold in pre-res scan. Subsequent daily appearances ignored. Market_id locked at
registration; scoring queries that market_id directly — no title-matching at score time.

### register_str002_signals.py
- Creates str002_signals table (PK: market_id + direction, INSERT OR IGNORE)
- Reads all 14 historical scan files chronologically
- Registers 27 unique first-seen signals: 10 ELITE, 6 LEGENDARY, 11 QUALIFIED
- 100% title→market_id match (verified before build)
- Complete registration data: market_price_at_registration, smart_money_pct, tier,
  elite/legendary counts, resolution_date
- Idempotent: re-running registers only NEW first-seen signals
- Commit 94e085b (implicit in session)

### score_str002_signals.py
- Reads registry, checks each signal's locked market_id for UMA finalization
- Scores only when DB resolved=1 + winning_outcome populated (trusts resolution pipeline)
- Computes outcome_correct + edge_at_entry (forward-honest, same formula as STR-003)
- Both raw accuracy AND market-relative edge reported (Fable metric-trap fix)
- Gate 3 check built in: >=10 scored at >=60% passes
- Writes findings to brain/agent-outputs/str002-scoring/ for feedback-loop-agent
- Commit 94e085b

### Daily maintenance wiring
Both scripts added as Steps 34-35 after fast_resolution_check (continue_on_error=True):
register_str002_signals → score_str002_signals → resolve_legendary_markets
Commit f03bc6e.

### Current Gate 3 status
PENDING (0/10 scored). 27 signals registered, all awaiting UMA finalization:
- June 7 signals (Peru): ONPE delayed mid-July
- June 9 signals (Maine/SC): RCV tabulation ongoing (days away)
- June 15 signals (Iran/Israel): resolve tomorrow — will score automatically
- June 17 signals (Fed): resolve in 3 days — will score automatically

---

## Code Hygiene Items (from June 12 weekly report)
All three flagged items resolved:
- apscheduler + psutil added to requirements.txt with usage comments (a67f358)
- signal-202606042140 zombie: status flipped respawning→failed in agent_registry.json
  (worktree gone, no tmux, not in git worktree list). Commit b15e4eb.
- WeightedConsensusSystem: migration to unified_elo_system.py DEFERRED to Phase 6.
  Two callers (consensus_divergence_detector.py, market_confidence_meter.py).
  Not blocking core pipeline. Note added to 2026-06-12-weekly.md. Commit d5e875b.
- recent_overdue_pass header label corrected ("no api_id" → "no api_id or condition_id")

---

## Research Scout Review (11 items processed)
All archived to brain/research-scout/reviewed/.

Actions taken:
- Prediction Arena (arXiv 2604.07355): filed to competitive-moat.md. All 6 frontier
  AI models lost money on Kalshi (16-30%). Validates validated-strategy + CI-gate design.
- RQ-ILS-001 placeholder pre-registered: Information Leakage Score as signal quality
  filter. Pre-register properly before July 1 RQ wave.
- arXiv 2606.07811 (liquidity-conditional underreaction): queued for RQ3.2 design.
- DeepSeek V4: already on model-routing watch list. V4-Pro exceeds UM890 Pro capacity
  even quantized. API pricing vs Haiku 4.5 the relevant comparison for Tier 2.5.
- Polymarket V3/pUSD/geoblock items: confirmed Phase 7 concerns only (see API audit).

---

## V3 API Migration Audit
Full audit of read stack vs V3 migration. Conclusion: no action needed.
- Gamma API (gamma-api.polymarket.com): public, unaffected by V3. Offset pagination
  on Gamma's own /markets endpoint works (different from V3 REST keyset migration).
- CLOB (clob.polymarket.com): public unauthenticated read endpoints unaffected.
- Data API (data-api.polymarket.com/trades): offset pagination works, separate system.
- POLYMARKET_API_KEY: UUID format key sent as Bearer on Gamma requests but ignored
  (Gamma is public). Zero auth failures in monitoring logs since June 1.
- V3 key requirement: Phase 7 only (authenticated order placement).
Audit note added to integration contract. Commit a9f2b2c.

---

## Pending — Next Session Priority

### Immediate (June 15 tomorrow):
1. Iran/Israel markets resolve — check maintenance scored STR-002 signals automatically
2. Run fast_resolution_check manually if maintenance hasn't fired yet

### June 17-18:
3. Fed markets resolve — more STR-002 auto-scoring
4. Counter-signal detector — earliest June 18 (7 snapshot days from June 11)

### June 30:
5. Score STR003-004, STR003-007, STR003-008 (correlated cluster)
6. RQ-CORRELATION-001 on cluster outcome

### July 1:
7. Wave 1 RQs: RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ1.1, RQ-CONTESTED-001
8. Wave 2: RQ-EXEC-001, RQ-PNLGATE-001, RQ-CONTESTED-ARCHETYPE-001
9. RQ-ILS-001 pre-registration (proper, before wave)
10. RQ-SCI-001 historical leg

### Ongoing:
11. Maine RCV winner when final → score STR-002 signals automatically
12. Peru ONPE oracle → confirm STR003-005 provisional score
13. Historical synthetic-resolution audit (UMA winner vs closed — future session)
14. WeightedConsensusSystem migration (Phase 6)

---

## Pool Status (end of session)
| Metric | Value |
|--------|-------|
| Pool C | 2,875 (post-Sunday recalc) |
| LEGENDARY active clean | 18 |
| ELO snapshots | Day 4 (June 11-14) |
| Order book snapshots | Day 3 (June 12-14) |
| STR-002 registered | 27 signals (0 scored, Gate 3 PENDING) |
| STR-003 scored | 1/4 (25%), 3 ACTIVE resolving June 30 |
| Integration contract | v2.9 + 14b + API audit |
| Backup | Confirmed nightly |
| Telegram freeze | Fixed (timeout added) |
| Resolution pipeline | Fixed (recent_overdue_pass) |
