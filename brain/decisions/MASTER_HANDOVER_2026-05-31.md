# MASTER HANDOVER — Polymarket Trading Intelligence System
**Date: 2026-05-31 | Server Setup 16**

---

## PROJECT OVERVIEW

Two repos on server (trading-swarm, parison@trading-swarm, Ubuntu 24.04):
- `ozziejparris-hub/first-repo` — Polymarket monitoring, DB, ELO system
- `ozziejparris-hub/trading-swarm` — multi-agent swarm orchestration

**Server:** Minisforum UM890 Pro, Ryzen 9 8945HS, 96GB DDR5
**SSH alias:** `trading-swarm` (user: parison)
**DB:** `~/projects/first-repo/data/polymarket_tracker.db` (~6.3GB, WAL mode)

---

## NORTH STAR

Track skilled geopolitics prediction market traders via `geo_elo` (category-specific ELO). Surface STR-003 signals when LEGENDARY traders (`geo_elo ≥ 2175`, `directionality ≥ 0.7`, `realized_pnl > 500`) express strong directional conviction in unresolved geopolitics markets.

---

## CRITICAL ARCHITECTURE RULES

| Rule | Detail |
|------|--------|
| **JOIN KEY** | `trades.market_id = markets.market_id` (NOT `condition_id`) |
| **Category field** | `markets.category` unreliable — always use `trades.market_category` |
| **Pool B** | `research_excluded=0` — ~12,000 traders — signal detection |
| **Pool C** | `geo_accuracy_pool=1` — 177 traders — geo_elo scored |
| **LEGENDARY** | `geo_elo ≥ 2175`, `directionality ≥ 0.7`, `pnl > 500`, `research_excluded=0` |
| **STR-003 anti-arb** | Entry price `BETWEEN 0.10 AND 0.80` |

---

## SERVICES (all systemd, server)

| Service | Status | Notes |
|---------|--------|-------|
| `polymarket-monitoring` | Active since 2026-05-31 05:44 | Auto-restarts on freeze |
| `polymarket-observer` | Active since 2026-05-29 12:28 | |
| `trading-swarm` | Active since 2026-05-22 03:00 | |
| `polymarket-sunday-elo.timer` | Fires Sun 03:00 UTC | Installed 2026-05-31 |

---

## DAILY MAINTENANCE (06:00 UTC, `daily_maintenance.py`)

Steps in order:

1. `update_research_exclusions.py`
2. `promote_high_pnl_traders.py`
2b. `resolution_sweep.py --days 7` (geo markets, fixed category filter 2026-05-28)
2c. `score_insider_signals.py`
2d. `score_str003_signals.py`
2e. `backfill_transaction_hashes.py --tier pool_c`
2f. `polygon_maker_taker.py --backfill --limit 500`
3. `verify_market_titles.py`
4. `fast_resolution_check.py`
5. `evaluate_new_trader_results.py`
6. `requeue_resolved_market_traders.py`
7. `apply_full_elo_modifiers.py`
8. `update_geo_elo.py` (--full-recalc Sundays via timer)
9. `resync_position_counts.py`
10. `backfill_market_dates.py --geo-only --limit 500`
11. `write_integration_health.py`
12. WAL checkpoint (PASSIVE)
13. Trade dedup (Sundays only)

---

## STR-003 STATE

**Status: EXPERIMENTAL — 0 qualifying signals under new geo_elo criteria**

Previous signals (comprehensive_elo based — now INVALID under new criteria):

| Signal | Position | Status | Notes |
|--------|----------|--------|-------|
| STR003-001 | Newsom NO | PENDING | Resolves Sept 2026 |
| STR003-002 | UN Security Council NO | PENDING | |
| STR003-003 | Fed/Warsh NO | **WRONG** | Resolved Apr 4, Warsh nominated |
| STR003-004 | Putin invasion NO | PENDING | Resolves Jun 30 2026 |

First genuine STR-003 signal needs geo_elo ≥ 2175 trader with 2026 activity. Currently 0 qualifying signals — expected as 2026 geo markets accumulate.

---

## RESEARCH PIPELINE

| Research Question | Status | Notes |
|-------------------|--------|-------|
| **RQ1.1** — ELO persistence | Script ready, self-halts n=10<30 | Rerun July 1 |
| **RQ3.2** — geo_elo LEGENDARY consensus accuracy | Pre-registered 2026-05-29 | Needs 20+ resolved consensus signals (est. July–Sept 2026) |
| **RQ-STR003-ANTIARB** — anti-arb filter | Phase 1 confirmed safe 2026-05-30 | Activated |

---

## ELO SYSTEM (post-fix 2026-05-31)

### comprehensive_elo
- **Cap formula:** `1500 + (resolved_trades_count × 150)`
- `apply_full_elo_modifiers.py` — bonus multipliers gated on `resolved_trades ≥ 10`
- `elo_bridge.py` — cap applied during `full_elo_recalculation`
- **Result:** max ELO 3,919 (was 5,115); 2 traders above 3,500 (was 206)

### geo_elo
- Per-step soft cap during loop (same formula)
- 47 LEGENDARY traders — high scores legitimate (1,900+ resolved geo trades)

### Sunday ELO timer
- Fires 03:00 UTC via `polymarket-sunday-elo.timer`
- Separate from `daily_maintenance` — this was the WAL lock fix

---

## MAKER/TAKER PIPELINE (new 2026-05-30/31)

**Keys location:** `~/.env_trading`
- `POLYGON_RPC_URL` — Alchemy PAYG
- `ETHERSCAN_API_KEY` — Etherscan

**Scripts:**
- `polygon_event_scanner.py` — targeted block scanning (trader activity window from DB timestamps)
- `polygon_maker_taker.py` — labels trades maker/taker
- `backfill_transaction_hashes.py` — backfills tx hashes by tier

**Contract addresses:**
- V2 CTF Exchange: `0xe111180000d2663c0091e4f400237545b87b996b`
- V1 CTF Exchange: `0xc5d563a36ae78145c45a50134d48a1215220f80a`
- OrderFilled V2 topic: `0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee`

**V2 skip rule:** V2 skipped for traders active before 2026-04-28.

**Legendary tier scan:** RUNNING in background screen session
```bash
screen -r legendary_scan
# OR
tail -f /tmp/legendary_scan.log
```
~19 hours total — check tomorrow (2026-06-01).

---

## AGENT SCHEDULE

| Time | Agent | Notes |
|------|-------|-------|
| Daily 08:00 + 20:00 | `research-scout` | |
| Monday 07:00 | `feedback-loop-agent` | |
| Monday 07:30 | `changelog-monitor` | |
| Monday 08:00 | `signal-agent` | June 1 = first run with geo_elo filters |
| Monday 08:00 | `performance-analyst-agent` | |
| Friday 20:00 | `code-hygiene-agent` | |
| Saturday 09:00 | `training-librarian-agent` | |
| Sunday 03:00 | `polymarket-sunday-elo.timer` | NEW — replaces maintenance step |
| Sunday 23:00 | `integration-test-agent` | |

---

## SESSION SUMMARIES (read for full history)

All in `brain/decisions/`:

| File | Session |
|------|---------|
| `2026-05-26-session-summary.md` | Server Setup 12 |
| `2026-05-27-session-summary.md` | Server Setup 13 |
| `2026-05-28-session-summary.md` | Server Setup 14 |
| `2026-05-29-session-summary.md` | Server Setup 15 |
| `2026-05-30-session-summary.md` | Server Setup 15 (continued) |
| `2026-05-31-session-summary.md` | Server Setup 16 (TODAY) |

---

## IMMEDIATE PRIORITIES FOR NEXT SESSION

1. **Check legendary scan results** — `screen -r legendary_scan` or `tail /tmp/legendary_scan.log`
2. **Run `update_geo_elo.py`** after scan completes to incorporate maker/taker data
3. **Review June 1 signal-agent output** (runs 08:00 UTC — first run with geo_elo filters)
4. **RQ1.1 self-halt** — will write `rq1_1_insufficient_n` at n=10<30, no action needed
5. **Putin signal** — resolves June 30, monitor `score_str003_signals.py` output
6. **Missing May 25 performance-analyst report** — investigate why agent did not run

---

## KNOWN ISSUES (all fixed unless noted)

| Issue | Status | Fix |
|-------|--------|-----|
| Duplicate trades | Fixed | Persisted cursor + tx hash unique index + weekly dedup |
| WAL lock cascade Sundays | Fixed | Sunday timer at 03:00 + write batching (500 traders/commit) |
| FIFO timeout | Fixed | `pnl_skip` for `0xc8a852...`, FIFO cap for large share counts |
| consensus signals | Fixed | geopolitics/elections-only filter |
| ELO inflation | Fixed | Cap formula applied across 5 scripts |
| Market end_dates (new) | Fixed | CLOB API integration in `polymarket_client.py` |
| Market end_dates (legacy) | Partial | Putin/Newsom set manually; no API path for legacy markets |
| Calibration warnings in ELO recalc | Expected | Noise, not errors — no action needed |

---

## PATTERN RECOGNITION AGENT (CONCEPT)

Documented in `brain/research-directions.md`.
**Status: CONCEPT — do not build until Phase 5 integration gates are passed.**

---

## PHASE 5 INTEGRATION GATES (none met yet)

1. `feedback-loop-agent` has completed 4+ weekly validation runs
2. `findings.json` contains 3+ HIGH-confidence findings (each from ≥20 resolved markets)
3. Pre-resolution accuracy ≥60% across 10+ markets (STR-002)
4. RQ1.1 AND RQ3.2 both passed

Do not skip or lower these gates.
