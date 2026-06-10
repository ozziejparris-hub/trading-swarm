# Session: Server Setup #28 — 2026-06-09

## Builds Completed

### 1. `legendary_positions_scan.py`
Full open positions intelligence across ALL open geo/elections markets with LEGENDARY trader positions, regardless of resolution date. Filters: stale prices (0.510–0.520), overdue markets (>7 day grace), MIXED_SIGNAL detection. Weekly Monday 07:30 UTC cron. Output: `brain/agent-outputs/positions-scan/`

### 2. `resolve_legendary_markets.py`
Targeted daily resolution sweep for LEGENDARY trader markets. Added to `daily_maintenance.py` Step 13, `--limit 50`. Resolves overdue markets before they go cold.

### 3. `signal_credibility.py` (Mythos)
4-component Signal Credibility Score (0–100) implementing arXiv 2604.24147 SCI methodology:
- **Net Position Conviction (0–40):** filters exited/flat traders using signed net shares
- **Two-Sidedness Penalty (−20–0):** penalises split LEGENDARY positions
- **Entry Timing Alpha (0–20):** rewards early conviction entries
- **Conviction Depth (0–20):** normalised position size vs trader average

Integrated into `legendary_positions_scan.py` output. `compute_net_positions()` is reusable core. Pre-registered as RQ-SCI-001 for validation.

### 4. Integration Test
6/7 PASS, 1 fixed (canonical definitions headers). All June 6–9 features verified.

---

## Key Findings

- **POSITIONS-ANALYSIS-001:** Raw trader count in positions_scan overcounts consensus. Iran analysis: 7 counted, 3 genuine open positions (SirHarryOakes, randomWalkingShrimp, Giorgio2). N0stradumba55 was on wrong side and exited. Spirit of Ukraine exited for profit. Anonymous was news trading.
- **Balance of Power signal exposed as fake consensus:** 2 traders split 1v1 (YES vs NO). SCS correctly scored LOW (10.9). Raw scan had it CLEAN.
- **Portugal signals confirmed:** Seguro YES ✅ CORRECT, Ventura NO ✅ CORRECT
- **Ukraine war 90 days NO** ✅ CORRECT (10/11 LEGENDARY, $388K NO capital, war did not end)
- Ukraine war market updated to `resolved=NO` in DB

---

## Research Pre-Registered

| ID | Hypothesis |
|----|-----------|
| RQ-SCI-001 | Does SCS > 70 predict better accuracy than raw trader count ≥ 2? |
| RQ-POSSIZE-001 | Normalised position size as ELO signal |
| RQ-SECTOR-001 | Category specialisation weighting |
| RQ-CORRELATION-001 | LEGENDARY traders show correlated worldview (Iran NO, regime change NO, escalation NO) — may reduce independence assumption |

---

## STR-003 New Signals

- **STR003-007:** Iran regime fall June 30 NO — 7 LEGENDARY, avg entry 0.678, SCS pending full net position calculation, resolves June 30
- **STR003-008:** European security guarantee to Ukraine June 30 NO — 2 LEGENDARY, MEDIUM confidence

---

## Active Signal Landscape (from positions scan)

Top 5 clean signals after filtering:

| Rank | Signal | LEGENDARY | SCS | Confidence | Resolves |
|------|--------|-----------|-----|-----------|---------|
| 1 | Bolsonaro Brazil 2026 YES | 3 | 47.2 | MEDIUM | Oct 4 |
| 2 | Graham SC primary NO | 2 | 43.2 | MEDIUM | Tonight (results pending) |
| 3 | US-China tariff <25% Nov 12 NO | — | 29.6 | LOW / MIXED | Nov 12 |
| 4 | 2026 Balance of Power R Senate R House YES | — | 10.9 | LOW (fake consensus) | — |
| 5 | Marco Rubio 2028 NO | 2 | 53.7 | MEDIUM | 881 days |

---

## Pending — June 10

- Score STR003-005 (Keiko YES) and STR003-006 (López Aliaga YES) once Peru resolves — Keiko at 93.5% YES, market not yet official
- Score Maine pre-resolution signals (Bellows, Jackson, Midgley, Mace, Evette) — ranked choice counting ongoing, Bellows at 4.75% YES (signal likely wrong)
- Score Graham SC primary — results coming in, LEGENDARY traders said NO vs 99% market
- `external_seed` backfill: 17 Pool B eligible, max 60 resolved trades — progress continues
- 3,338 stub markets remaining for hydration
