# Session Summary — Server Setup #29
**Date:** 2026-06-10

---

## Signal Credibility Score (Fable/Mythos build)

`signal_credibility.py` built using Claude Mythos (Fable 5) — first use of frontier model on this project.
Implements 4-component Signal Credibility Score (0–100) based on arXiv 2604.24147 SCI methodology:

- **Component 1: Net Position Conviction (0–40)** — signed net shares per LEGENDARY trader (BUY − SELL); only counts traders with abs(net_position) > 1.0. Consensus = fraction of net-committed traders agreeing. Score = 40 × consensus²
- **Component 2: Two-Sidedness Penalty (−20 to 0)** — penalises split LEGENDARY capital
- **Component 3: Entry Timing Alpha (0–20)** — rewards early conviction entries where market moved in trader's favour
- **Component 4: Conviction Depth (0–20)** — normalised position size vs trader's average across all markets

`compute_net_positions()` is reusable core — directly implements POSITIONS-ANALYSIS-001 fix.
Integrated into `legendary_positions_scan.py` output (enriches JSON with `signal_credibility_score`, `signal_credibility_tier`, `net_committed_traders`).
Pre-registered as RQ-SCI-001.

**Scores for today's 5 clean signals:**

| Signal | SCS | Tier |
|--------|-----|------|
| Marco Rubio 2028 NO | 53.7 | MEDIUM |
| Bolsonaro Brazil YES | 47.2 | MEDIUM |
| Graham SC NO | 43.2 | MEDIUM |
| US-China tariff NO | 29.6 | LOW |
| Balance of Power YES | 10.9 | LOW |

Key finding: **Balance of Power looked CLEAN to raw scan** (both_sides_ratio 0.157) but SCS revealed traders are split directionally — exactly the Iran failure mode. 2 traders split 1v1.

---

## Integration Test Results (all June 6–9 features)

| Test | Result |
|------|--------|
| TEST 1 hydrate_stub_markets.py | PASS |
| TEST 2 resolve_legendary_markets.py | PASS |
| TEST 3 legendary_positions_scan.py | PASS |
| TEST 4 daily_maintenance step order | PASS |
| TEST 5 integration contract consistency | FAIL → FIXED (canonical headers added to 2 scripts) |
| TEST 6 end-to-end pipeline | PASS (8,681 trades evaluated) |
| TEST 7 crontab | PASS |

---

## Pending Resolution (check at start of next session)

- **Peru:** Keiko at 93.5% YES, still not officially resolved on Polymarket oracle
- STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES) — score once resolved
- STR003-006 will be WRONG — first confirmed wrong STR-003 signal (López Aliaga came 3rd in first round, eliminated)
- **Maine Democratic primary:** Bellows at 4.75% YES market price — likely WRONG pre-resolution signal (1 ELITE trader, thin)
- **Maine Republican primary:** Ben Midgley YES, Nancy Mace YES signals — results pending
- **Graham SC:** LEGENDARY traders said NO vs 99% market — results pending (primary happened June 9, result not yet confirmed in system)

---

## ELO and Pool Status

| Metric | Value |
|--------|-------|
| Pool C | 402 traders (hydration in progress, 3,338 stubs remaining) |
| Active LEGENDARY (geo_elo_active >= 2175) | 11 |
| external_seed Pool B eligible | 17 (max 60 resolved trades) |
| external_seed stubs remaining | 3,338 |
| manual_watchlist | 17 traders, none Pool B eligible yet |
