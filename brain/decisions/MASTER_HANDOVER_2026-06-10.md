# MASTER HANDOVER — Polymarket Trading Intelligence System
**Date: 2026-06-10 | Server Setup #29**

---

## PROJECT OVERVIEW

Two repos on server (trading-swarm, parison@trading-swarm, Ubuntu 24.04):
- `ozziejparris-hub/first-repo` — Polymarket monitoring, DB, ELO system
- `ozziejparris-hub/trading-swarm` — multi-agent swarm orchestration

**Server:** Minisforum UM890 Pro, Ryzen 9 8945HS, 96GB DDR5  
**SSH alias:** `trading-swarm` (user: parison)  
**DB:** `~/projects/first-repo/data/polymarket_tracker.db` (~6.3GB+, WAL mode)

---

## NORTH STAR

Track skilled geopolitics prediction market traders via `geo_elo` (category-specific ELO). Surface STR-003 signals when LEGENDARY traders (`geo_elo_active >= 2175`, `geo_accuracy_pool = 1`, `geo_directionality_score >= 0.7`) express strong directional conviction in unresolved geopolitics/elections markets.

---

## CRITICAL ARCHITECTURE RULES

| Rule | Detail |
|------|--------|
| **JOIN KEY** | `trades.market_id = markets.market_id` (NOT `condition_id`) — verified 99.999% match |
| **Category field** | `markets.category` authoritative — `trades.market_category` is 81% Unknown |
| **Pool B filter** | `research_excluded=0 AND resolved_trades_count>=20 AND bot_type IS NULL` — `research_excluded=0` alone insufficient (13K+ thin-sample traders included) |
| **Pool C** | `geo_accuracy_pool=1` — ~402 traders — geo_elo scored (recovering from hydration gap) |
| **LEGENDARY (geo)** | `geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND research_excluded = 0 AND bot_type IS NULL` — 11 active as of June 8 |
| **LEGENDARY (comprehensive)** | `comprehensive_elo > 2175` — do NOT use for signal generation; only for bot detection and Pool B qualification |
| **STR-003 anti-arb** | Entry price `BETWEEN 0.10 AND 0.80` |
| **SCS annotation** | `signal_credibility_score` in positions scan output — annotation-only until 20+ resolved markets validated |

---

## SERVICES (all systemd, server)

| Service | Status | Notes |
|---------|--------|-------|
| `polymarket-monitoring` | Active | Auto-restarts on freeze |
| `polymarket-observer` | Active | |
| `trading-swarm` | **NOT STARTED** | Awaiting 48h parallel run before orchestrator goes live — see CLAUDE.md WARNING |
| `polymarket-sunday-elo.timer` | Fires Sun 03:00 UTC | Log permissions corrected 2026-06-07 |

---

## DAILY MAINTENANCE (06:00 UTC, `daily_maintenance.py`)

Steps in order per integration-contract.md v2.6, with additions from June 6–9 sessions:

```
  Step  0: update_research_exclusions.py             [blocking]
  Step  1: promote_high_pnl_traders.py               [non-blocking]
  Step  2: resolution_sweep.py --days 7              [non-blocking]
  Step  3: update_geo_elo.py                         [non-blocking]
  Step  4: score_insider_signals.py                  [non-blocking]
  Step  5: score_str003_signals.py                   [non-blocking]
  Step  6: backfill_transaction_hashes.py --tier pool_c  [non-blocking]
  Step  7: polygon_maker_taker.py --backfill --limit 500  [non-blocking]
  Step  8: verify_market_titles.py                   [non-blocking]
  Step  9: fast_resolution_check.py                  [blocking] — ceiling raised to 50,000 markets; external_seed targeted pass added
  Step 10: evaluate_new_trader_results.py            [non-blocking]
  Step 10c: hydrate_stub_markets.py --limit 200      [non-blocking] — NEW 2026-06-08; fetches Gamma API metadata for NULL resolution_date stub markets
  Step 11: requeue_resolved_market_traders.py        [blocking]
  Step 12: apply_full_elo_modifiers.py               [blocking]
  Step 13: resolve_legendary_markets.py --limit 50   [non-blocking] — NEW 2026-06-09; targeted resolution for LEGENDARY trader overdue markets
  Step 14: resync_position_counts.py                 [blocking]
  Step 15: write_integration_health.py               [blocking]
  Post:    WAL checkpoint (PASSIVE)
  Post:    backfill_market_dates.py --geo-only --limit 500  [non-blocking]

Sundays only (06:00, appended to daily run):
  discover_leaderboard_traders.py
  Trade dedup

Sundays only (03:00, separate timer: polymarket-sunday-elo.timer):
  recalculate_comprehensive_elo.py
```

---

## EXTERNAL DATASET

**Dataset:** `vgregoire/polymarket-users` (HuggingFace, CC-BY 4.0)  
**Location:** `/home/parison/projects/first-repo/data/external/` (gitignored — 1.26GB)

| File | Size | Coverage |
|------|------|----------|
| `user_pnl_summary.parquet` | 495MB | Nov 2022 – Mar 2026, V1 exchange |
| `user_features.parquet` | 768MB | Same coverage |

**Key fields used:**
- `pnl_taker_politics` — directional politics P&L (taker trades only)
- `frac_both_sides` — fraction of positions held both sides (LP proxy)
- `frac_maker` — fraction of trades as maker
- `frac_held_to_resolution` — fraction of positions held to resolution
- `avg_market_age_at_trade` — execution timing proxy
- `frac_early_trader`, `frac_late_trader`

**Key findings from cross-reference:**
- Pool C mean `frac_both_sides` = 0.513 — significant LP contamination
- `geo_directionality_score` correlation with `frac_both_sides`: −0.135 (near-zero — LP filter nearly ineffective)
- LEGENDARY traders: `frac_held_to_resolution` = 0.978 (vs 0.891 non-LEGENDARY Pool C) — near-perfect conviction holding
- LEGENDARY traders enter slightly LATER than average Pool C (contradicts Della Vedova execution hypothesis) — points toward genuine forecasting skill
- 317 Pool C traders found in external dataset; 4 LEGENDARY traders matched

**Decision gate:** No Pool C or STR-003 changes from external dataset findings until Peru resolution + RQ-EXT-001 results.

---

## NEW TRADERS (207 added June 6–8)

### Layer 2 — external_seed (195 traders, batch insert 2026-06-06)
Filter criteria from parquet:
```
traded_politics = 1
frac_politics > 0.5
frac_both_sides < 0.25
frac_maker < 0.3
n_markets >= 15
pnl_taker_politics > $10,000
last_trade >= 2025-06-01
```
`discovery_source = 'external_seed'`  
Trade histories pending backfill via daily maintenance. Not yet in Pool B (resolved_trades_count < 20).

**Backfill status as of June 10:**
- 17 Pool B eligible (resolved_trades_count >= 20), max 60 resolved trades
- 3,338 stub markets remaining for hydration at 200/day
- `is_flagged=1` fix applied (Blocker 3 resolved)
- 20K cap raised to 50K (Blocker 2 resolved)

### Layer 1 / manual_watchlist (12 traders added June 6–8)

| Name | Address prefix |
|------|---------------|
| Nocthyra | 0x040f |
| Calythius | 0x90fe |
| Wrythor | 0xf79aa5 |
| Brixen | 0x98b049 |
| Zyoran | 0x0132d8 |
| TTNHM | 0x7803ca |
| Orynthos | 0x516c7c |
| Korthen | 0x240040 |
| Quinlith | 0xb6fac8 |
| Xyvaris | 0xc536db |
| Veythoris | 0xaae6b4 |
| Lioren | 0x1699e1 |
| Sylvaren | 0x0833b2 |
| anonymous (0xb464) | Tier 1, added June 6 |
| anonymous (0xb917bb) | Added June 7 |
| anonymous (0x6d20b9) | NEG_RESOLVED pattern, added June 8 |

**NEG_RESOLVED pattern explained:** Hybrid taker/maker traders with profitable directional taker trades ($52K–$114K) offset by loss-making market-making operations (−$103K to −$214K maker P&L). Use `pnl_taker_politics` not `pnl_resolved_politics` for screening.

**Deferred:**
- `0x9d31ca01` (Samurai12) — 72% maker, verification pending
- `0xc05587` and `0xe0fd1b` — large implied open position gaps ($54K–$66K), not yet explained

---

## NEW SCRIPTS (first-repo, June 6–9)

### `scripts/hydrate_stub_markets.py`
Fetches Gamma API metadata (resolution_date, category, end_date) for markets with `resolution_date IS NULL` (stub markets created during backfill import). Added to daily_maintenance.py Step 10c, `--limit 200/day`. ~2,700 markets hydrated manually on 2026-06-08; 3,338 remaining.

### `scripts/resolve_legendary_markets.py`
Targeted daily resolution sweep for markets where LEGENDARY traders have open positions and `resolution_date <= now`. Ensures LEGENDARY trader markets are resolved promptly. Added to daily_maintenance.py Step 13, `--limit 50`.

### `scripts/legendary_positions_scan.py`
Full open positions intelligence across ALL open geo/elections markets with LEGENDARY trader positions, regardless of resolution date. Implements POSITIONS-ANALYSIS-001 fix (net position filter). Weekly Monday 07:30 UTC cron. Output: `brain/agent-outputs/positions-scan/`.

Key filters:
- Stale prices excluded (last_price 0.510–0.520 = no meaningful signal)
- Overdue markets excluded (resolved=0 AND resolution_date past >7 day grace)
- MIXED_SIGNAL flag: `both_sides_ratio > 0.3`
- Canonical LEGENDARY: `geo_elo_active >= 2175 AND geo_accuracy_pool = 1`

### `scripts/signal_credibility.py`
4-component Signal Credibility Score (0–100) implementing arXiv 2604.24147 SCI methodology. Integrated into `legendary_positions_scan.py` output. `compute_net_positions()` is the reusable core. Pre-registered as RQ-SCI-001. Annotation-only until validated on 20+ resolved markets.

SCS tiers: HIGH ≥ 70 | MEDIUM 40–69 | LOW < 40

---

## ELO SYSTEM (post-June 2026)

### comprehensive_elo
- **Cap formula:** `1500 + (resolved_trades_count × 150)`
- Used for bot detection and Pool B qualification ONLY — not for signal generation
- LEGENDARY threshold (comprehensive_elo): contaminated on contested markets (46% accuracy vs 50% random)

### geo_elo
- Per-step soft cap during loop (same formula)
- **geo_elo_active:** recency-decayed version — `geo_elo × 0.5^(days_dormant/180)`, 180-day half-life. Used for STR-003 qualification. Updated daily by `update_geo_elo.py`.
- 44 LEGENDARY total (`geo_elo >= 2175`), 11 active (`geo_elo_active >= 2175`)
- LEGENDARY accuracy (geo_elo): 77.8% (n=28,030 trades, in-sample)
- Pool C accuracy (full 2026, n=444): 70.7%

**Pool C state (as of June 8):** 402 traders — temporarily reduced from ~477. 809 traders have NULL `geo_directionality_score` due to incomplete positions table coverage for newly hydrated markets. Will recover as `hydrate_stub_markets.py` populates data.

### Sunday ELO timer
- `polymarket-sunday-elo.timer` fires 03:00 UTC via dedicated systemd unit
- Log permissions fixed 2026-06-07 (root-owned log was causing failures)
- First successful automated run: 2026-06-07 10:35 UTC (manual after log fix)

---

## MAKER/TAKER PIPELINE

**Keys location:** `~/.env_trading`
- `POLYGON_RPC_URL` — Alchemy PAYG
- `ETHERSCAN_API_KEY` — Etherscan

**Contract addresses:**
- V2 CTF Exchange: `0xe111180000d2663c0091e4f400237545b87b996b`
- V1 CTF Exchange: `0xc5d563a36ae78145c45a50134d48a1215220f80a`
- OrderFilled V2 topic: `0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee`

**V2 skip rule:** V2 skipped for traders active before 2026-04-28.

---

## STR-003 SIGNAL STATUS

### Active / Pending Signals

| ID | Market | Direction | LEGENDARY | Status | Resolves |
|----|--------|-----------|-----------|--------|---------|
| STR003-001 | Newsom drops out before Sep | NO | 1 (fails geo_elo) | ACTIVE (outcome tracking only) | 2026-09-01 |
| STR003-004 | Putin invades by June 30 | NO | 1 (fails geo_elo) | ACTIVE — counter-signal now $200K+ YES | 2026-06-30 |
| STR003-005 | Keiko wins Peru | YES | 1 | OVERDUE — market at 93.5% YES, oracle not resolved | 2026-06-07 |
| STR003-006 | López Aliaga wins Peru | YES | 1 | OVERDUE — WILL RESOLVE WRONG (eliminated 1st round) | 2026-06-07 |
| STR003-007 | Iran regime fall June 30 | NO | 7 | ACTIVE, HIGH confidence — market moved 32%→1.25% YES | 2026-06-30 |
| STR003-008 | European security guarantee June 30 | NO | 2 | ACTIVE, MEDIUM confidence | 2026-06-30 |

### Scored Signals

| ID | Market | Direction | Status | Notes |
|----|--------|-----------|--------|-------|
| STR003-003 | Warsh Fed nomination | NO | **WRONG** | Warsh nominated April 4 |

**STR003-002 (UN Gaza):** ORPHANED — market not found in DB. Oscar to determine outcome.

**First confirmed WRONG signal:** STR003-006 (López Aliaga YES) — he placed 3rd in first round, eliminated. First round winner was Keiko (17.17%), Sánchez 2nd (12%), López Aliaga 3rd.

**Mutual exclusivity note:** STR003-005 and STR003-006 were same-election from same trader — cannot both be correct. Signal-agent needs inter-signal conflict detection for same-election markets (future improvement).

---

## ACTIVE SIGNAL LANDSCAPE (positions scan June 9, with SCS)

Signals after stale/overdue filtering:

| Rank | Signal | LEGENDARY | SCS | Tier | Resolves |
|------|--------|-----------|-----|------|---------|
| 1 | Marco Rubio 2028 NO | 2 | 53.7 | MEDIUM | ~881 days, $23K capital |
| 2 | Bolsonaro Brazil 2026 YES | 3 | 47.2 | MEDIUM | Oct 4 2026 |
| 3 | Graham SC primary NO | 2 | 43.2 | MEDIUM | June 9 (results pending) |
| 4 | US-China tariff <25% Nov 12 NO | — | 29.6 | LOW / MIXED | Nov 12 |
| 5 | 2026 Balance of Power R Senate R House YES | 2 | 10.9 | **LOW — fake consensus** (traders split 1v1) | — |

**Balance of Power alert:** Raw scan showed it CLEAN (both_sides_ratio 0.157). SCS revealed directional split — exactly the Iran failure mode. Do not act on LOW SCS signals.

---

## RESEARCH PIPELINE

### Phase 5 Gate Status (as of June 10)

| Gate | Status | Notes |
|------|--------|-------|
| Gate 1: feedback-loop 4+ weekly runs | ✅ MET | 10 runs completed as of June 5 |
| Gate 2: 3+ HIGH findings (≥20 markets each) | ✅ MET | Confirmed June 5 by feedback-loop Run #10 |
| Gate 3: STR-002 accuracy ≥60% (10+ markets) | ❌ STALLED | 50%/4 markets — no resolved STR-002 signals in 29+ days |
| Gate 4: RQ1.1 AND RQ3.2 both passed | ❌ PENDING | RQ1.1 deferred to July 1; RQ3.2 needs 50+ markets |

**Phase 5 Gate 2 qualifying HIGH findings:**
1. `2026-06-03-ELO-VS-MARKET-001` — ELO tiers +20–31pp edge on contested markets (n=746)
2. `2026-06-05-CONTESTED-ACCURACY-2026-001` — QUALIFIED 66.3% on 2026 contested markets (n=101)
3. `2026-06-01-GEO-ELO-ACCURACY-001` — Pool C 86.36% accuracy on 30-day geo/elections (n=22)

### Pre-Registered Research Questions

| RQ | Hypothesis | Defer Until |
|----|-----------|------------|
| RQ-EXT-001a/b/c | External dataset cross-reference (after Peru resolution) | After Peru scored |
| RQ-EXEC-001 | Execution vs forecasting in LEGENDARY accuracy (Della Vedova test) | July 1 |
| RQ-CONTESTED-001 | Difficulty-weighted K factor (needs 30 contested geo markets) | July 1 |
| RQ-LH-001 | Lifecycle/conviction heuristic (4 independent events needed) | July 1 |
| RQ-ILS-001 | Information Leakage Score market filter | July 1 |
| RQ-POSSIZE-001 | Normalised position size as ELO signal | July 1 |
| RQ-SECTOR-001 | Category specialisation weighting | July 1 |
| RQ-PNLGATE-001 | `pnl_taker_politics` as secondary STR-003 filter | July 1 |
| RQ-SCI-001 | Signal Credibility Score validation vs raw trader count | Validate now on historical resolved markets |
| RQ1.1 | ELO persistence (T→T+1 Brier) | July 1 (n=10 at last run, need 30) |
| RQ3.2 | geo_elo LEGENDARY consensus vs market price | July–Sept 2026 (needs 50+ markets) |
| RQ-CONVICTION-001 | frac_held_to_resolution as STR-003 quality filter | After July 1 |
| RQ4-MULTI | Multivariate Kelly for correlated positions | Phase 4+ |

### Completed Research

| RQ | Result |
|----|--------|
| RQ0.1 Wash Trading | PASSED — 0.1% contamination |
| RQ0.2 Bot Detection | PASSED — 3 bot types classified |
| GEO-ELO-001 | PASSED in-sample — LEGENDARY 78% accuracy |
| GEO-ELO-003 OOS | INCONCLUSIVE — 2 traders, 1 market |
| RQ-CONTESTED-001 | PASS — QUALIFIED 66.3% on 2026 contested (n=101) |
| STR-003 RQ2.2 | PASS — YES 61.1%, NO 77.8% at 95% threshold |
| LH-001 | CONDITIONAL_PASS — watchlist trigger only, 4/7 insider signals correct |
| STR-001 | FAILED — LP contamination structural flaw |
| STR-004 founding case | 0/1 — Russia/Ukraine ceasefire. n=1, stop criterion at n=10 |

---

## INTEGRATION CONTRACT + SCHEMA CHANGE LOG

**Contract version:** v2.6 — 2026-06-09  
**Location:** `brain/integration-contract.md`

| Version | Key change |
|---------|-----------|
| v2.6 | `legendary_positions_scan.py` added; weekly Monday 07:30 UTC cron |
| v2.5 | Pool C temporarily 402 (hydration gap); 3 scoring pipeline blockers fixed |
| v2.4 | 195 external_seed traders added; `/holders` endpoint identified |
| v2.3 | Section 10 — Canonical Agent Definitions |
| v2.0–v2.2 | Pool B contamination warning; `accuracy_pool`/`geo_elo_oos` dropped |

### Schema Change Log — propagation status

| SCL | Change | Status |
|-----|--------|--------|
| SCL-001 | `market_id` vs `condition_id` join key | PARTIALLY COMPLETE — backtest-agent, integration-test-agent, quant-research.md UNVERIFIED |
| SCL-002 | `accuracy_pool`, `geo_elo_oos`, `copyable_edge` columns dropped | PARTIALLY COMPLETE — backtest-agent, quant-research.md, feedback-loop-agent UNVERIFIED |
| SCL-003 | `comprehensive_elo` vs `geo_elo` distinction | **PROPAGATION COMPLETE** — all scripts fixed |
| SCL-004 | Wrong JOIN key silently drops 37% trades | PARTIALLY COMPLETE — backtest-agent, quant-research.md, feedback-loop-agent UNVERIFIED |
| SCL-005 | Pool B filter completeness | PROPAGATION COMPLETE |
| SCL-006 | `external_seed` discovery_source added | Non-breaking, no template changes needed |
| SCL-007 | `system_observer.py` alert thresholds stale | Fixed 2026-06-07 (LEGENDARY badge + error rate thresholds) |
| SCL-008 | `legendary_positions_scan.py` canonical filters | PROPAGATION COMPLETE on creation |

**Pending verification (training-librarian June 13):**
- `backtest-agent.md` — SCL-001, SCL-002, SCL-004
- `integration-test-agent.md` — SCL-001
- `quant-research.md` — SCL-001, SCL-002, SCL-004

---

## CANONICAL DEFINITIONS (agents must use these)

**LEGENDARY definition:**
```sql
geo_elo_active >= 2175
AND geo_accuracy_pool = 1
AND research_excluded = 0
AND bot_type IS NULL
```

**Pool B filter (authoritative):**
```sql
research_excluded = 0
AND resolved_trades_count >= 20
AND bot_type IS NULL
```

**JOIN key:**
```sql
JOIN markets m ON m.market_id = t.market_id  -- NOT m.condition_id
```

**STR-003 qualification criteria:**
```sql
geo_elo_active >= 2175
AND geo_accuracy_pool = 1
AND geo_directionality_score >= 0.7
AND realized_pnl != 0.0 AND realized_pnl > -100000
AND research_excluded = 0
AND entry_price BETWEEN 0.10 AND 0.80
AND market.category IN ('Geopolitics', 'Elections')
AND >= 95% of trader's capital on one side
```

---

## AGENT SCHEDULE

| Time | Agent | Notes |
|------|-------|-------|
| Daily 06:00 UTC | `daily_maintenance.py` | All 15 steps + new additions |
| Daily 08:00 + 20:00 | `research-scout` | |
| Monday 07:00 | `feedback-loop-agent` | |
| Monday 07:30 | `legendary-positions-scan` | NEW 2026-06-09 |
| Monday 07:30 | `changelog-monitor` | |
| Monday 08:00 | `signal-agent` | |
| Monday 08:00 | `performance-analyst-agent` | |
| Friday 20:00 | `code-hygiene-agent` | |
| Saturday 09:00 | `training-librarian-agent` | Responsibility 8: weekly template audit against SCL |
| Sunday 03:00 | `polymarket-sunday-elo.timer` | Log permissions fixed 2026-06-07 |
| Sunday 06:00 (appended) | `discover_leaderboard_traders.py` + trade dedup | |
| Sunday 23:00 | `integration-test-agent` | |

---

## CONTRACT VIOLATION — OUTSTANDING

**Signal from performance-analyst-agent (2026-06-08):**
`legendary_base` (geo_elo >= 2175, research_excluded=0) dropped from 47 (June 1) to 25 (June 8) — below alert threshold of 30.

- `legendary_active` (geo_elo_active >= 2175) = 11–13 UNCHANGED — STR-003 signal capacity unaffected
- Cause: possibly Sunday June 7 `recalculate_comprehensive_elo.py` run or `update_research_exclusions.py` batch change
- Action: query `traders WHERE geo_elo >= 2175 ORDER BY research_excluded DESC` to identify newly excluded traders before next STR-003 scan

---

## HOW TO START A NEW SESSION

```bash
# 1. Check services
sudo systemctl status polymarket-monitoring polymarket-observer --no-pager | grep Active

# 2. Check DB lock
lsof ~/projects/first-repo/data/polymarket_tracker.db 2>/dev/null | wc -l

# 3. Catch overnight resolutions
cd ~/projects/first-repo && python scripts/resolve_legendary_markets.py --limit 50

# 4. Score any new resolutions
python scripts/evaluate_new_trader_results.py

# 5. Check Peru/Maine/Graham market resolution status via Gamma API
# Peru: STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES) — Keiko at 93.5% YES
# Maine: Bellows primary, Midgley/Mace Republican primary
# Graham SC: primary happened June 9, results pending confirmation

# 6. Check positions scan output
cat ~/trading-swarm/brain/agent-outputs/positions-scan/latest.json

# 7. Read today's pending items from this handover
```

---

## IMMEDIATE PRIORITIES FOR NEXT SESSION

1. **Score Peru signals** — STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES) are OVERDUE. Keiko at 93.5%, oracle slow. Check Polymarket and force-resolve if needed.
2. **STR003-006 confirmed WRONG** — first confirmed wrong STR-003 signal. Document in strategy-registry.md when scored.
3. **Score Graham SC primary** — LEGENDARY traders said NO vs 99% market. Results pending.
4. **Score Maine pre-resolution signals** — Bellows (4.75% YES — likely WRONG), Midgley/Mace/Evente.
5. **Investigate legendary_base drop** — query traders WHERE geo_elo >= 2175 ORDER BY research_excluded DESC. Confirm cause.
6. **STR-003 June 30 resolutions** — STR003-004 (Putin invasion NO) and STR003-007 (Iran regime fall NO) both resolve June 30. Record in strategy-registry.md immediately after.
7. **external_seed backfill progress** — 17 Pool B eligible, max 60 resolved trades. Run hydrate_stub_markets.py pass and check progress.
8. **Layer 3 trader discovery** — `/holders` endpoint sweep (identified but not implemented). Resolves markets by checking who holds positions.
9. **RQ-EXT-001a/b/c** — run after Peru signals scored.
10. **Legacy template audit** — `backtest-agent.md`, `integration-test-agent.md`, `quant-research.md` (SCL-001/002/004 verification, scheduled for training-librarian June 13).

---

## SESSION SUMMARIES (read for full history)

All in `brain/decisions/`:

| File | Session | Key Changes |
|------|---------|-------------|
| `2026-05-26-session-summary.md` | Server Setup 12 | |
| `2026-05-27-session-summary.md` | Server Setup 13 | |
| `2026-05-28-session-summary.md` | Server Setup 14 | |
| `2026-05-29-session-summary.md` | Server Setup 15 | STR-003 anti-arb filter; geo_elo_active |
| `2026-05-30-session-summary.md` | Server Setup 15 cont. | Maker/taker pipeline |
| `2026-05-31-session-summary.md` | Server Setup 16 | Sunday ELO timer |
| `2026-06-06-session-summary.md` | Server Setup 25 | External dataset; 195 external_seed; agent template audit; disk expansion |
| `2026-06-07-session-summary.md` | Server Setup 26 | 12 manual_watchlist traders; POSITIONS-ANALYSIS-001; repo cleanup |
| `2026-06-08-session-summary.md` | Server Setup 27 | 3 pipeline blockers fixed; Pool C 402; NEG_RESOLVED pattern explained |
| `2026-06-09-session-summary.md` | Server Setup 28 | legendary_positions_scan.py; resolve_legendary_markets.py; STR003-007/008 |
| `2026-06-10-session-summary.md` | Server Setup 29 | signal_credibility.py (Fable/Mythos); integration test 6/7→7/7 |

---

## KNOWN ISSUES

| Issue | Status | Notes |
|-------|--------|-------|
| Duplicate trades | Fixed | Persisted cursor + tx hash unique index + weekly dedup |
| WAL lock cascade Sundays | Fixed | Sunday timer at 03:00 + write batching |
| ELO inflation | Fixed | Cap formula applied across 5 scripts |
| Market end_dates (legacy) | Partial | Putin/Newsom set manually |
| Pool C below 477 | In progress | 809 traders have NULL geo_directionality_score from hydration gap; recovering via hydrate_stub_markets.py |
| legendary_base below threshold | Investigate | Dropped 47→25 since June 1; legendary_active (11) unchanged; cause unknown |
| external_seed scoring | In progress | 17/195 traders Pool B eligible; 3,338 stubs remaining at 200/day |
| `system_observer.py` LEGENDARY badge | Fixed 2026-06-07 | comprehensive_elo → geo_elo + geo_accuracy_pool |
| Sunday ELO log permissions | Fixed 2026-06-07 | Root-owned log corrected |
| SCL-001/002/004 in legacy templates | Pending | backtest-agent, integration-test-agent, quant-research.md — training-librarian June 13 |
| `0x9d31ca01` (Samurai12) | Deferred | 72% maker — verify before adding to watchlist |
| STR003-002 UN Gaza | Orphaned | Market not in DB — Oscar to determine resolution outcome |
