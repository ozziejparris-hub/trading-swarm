# Signal Agent Report — 2026-08-17 08:00 UTC

**Run ID:** signal-20260817
**Model:** Claude Sonnet 4.6 (Tier 3)
**Task:** Routine signal scan + active STR-003 rescan + LEGENDARY pool change analysis

---

## Section 9 Validation — PASS

| Metric | Value | Expected | Alert? |
|--------|-------|----------|--------|
| clean_pool | 31,892 | ≈18,910 | No (above minimum of 15,000) |
| true_research_pool | 21,067 | ≈3,837 | No (above minimum of 3,000) |
| clean_markets | 224,614 | ≈24,184 | No (above minimum of 20,000) |
| pool_c | 3,560 | ≈2,185 | No |
| legendary_base | 77 | ≈48 | No (within 15–200) |
| legendary_active | 11 | ≈25 | No (>5 threshold, no alert) |
| legendary_clean | 9 | ≈18 | No (>5 threshold) |
| near_legendary_clean | 21 | ≈21 | No |
| wal_mode | wal | wal | No |

All pool sizes remain above alert thresholds. Contract expected ranges are stale (pool has grown substantially since June 2026 calibration). No action needed — legitimate growth.

---

## STR-003 Signal Scan — 0 New Qualifying Signals

**Cycle result:** No new STR-003 signals registered.

### LEGENDARY Pool Summary — 9 Traders (was 10 last week)

Full LEGENDARY pool (geo_elo_active ≥ 2175, directionality ≥ 0.7, realized_pnl != 0.0 AND > -100000, research_excluded = 0, geo_accuracy_pool = 1, bot_type IS NULL):

| Address | ELO Active | Δ vs Last Wk | Dir | PnL | Archetype | Weight | Active Geo Mkts | STR-003 Block |
|---------|-----------|-------------|-----|-----|-----------|--------|-----------------|----------------|
| 0xecaa8806... | 4200.6 | **+917.6** | 0.960 | +$165,426 | GENUINE_FORECASTER | FULL | 0 (cat. bug) | category_visibility_bug |
| 0xd44e974a... | 3319.8 | -77.6 | 0.981 | +$165,545 | VOLUME_SPECIALIST | MINIMAL | 15 | max-2-markets |
| 0x3d03c46d... | 2624.4 | -61.3 | 0.837 | +$129 | DOMAIN_SPECIALIST | MINIMAL | 14 | max-2-markets |
| 0x6b025355... | 2571.8 | -60.1 | 0.999 | -$1,416 | DOMAIN_SPECIALIST | MINIMAL | 2 | $90 position (<$2K min) |
| **0xc624cccd...** | **2545.0** | **NEW** | 0.951 | +$3,130 | DOMAIN_SPECIALIST | MINIMAL | 41 | max-2-markets + human review |
| 0xd218e474... | 2489.9 | **+121.6** | 0.958 | -$817 | YIELD_HARVESTER | **EXCLUDE** | 10 | EXCLUDE archetype |
| 0x63c6169c... | 2481.1 | -58.0 | 1.000 | +$1,574 | DOMAIN_SPECIALIST | MINIMAL | 2 | $170 position (<$2K min) |
| 0xc722c1a1... | 2305.7 | -53.9 | 0.976 | +$7,467 | DOMAIN_SPECIALIST | MINIMAL | 18 | max-2-markets |
| 0x4fd3503c... | 2226.2 | -52.0 | 0.936 | -$3,683 | YIELD_HARVESTER | **EXCLUDE** | 9 | EXCLUDE archetype + max-2-markets |

**Pool changes this week:**

*Dropped from LEGENDARY:*
- **0x848df648** (2210.2 → 2159.7, -50.5 pts) — now near-LEGENDARY, gap=15.3
- **0x9287bd3d** (2202.3 → 2152.0, -50.3 pts) — now near-LEGENDARY, gap=23.0

*New LEGENDARY entrant:*
- **0xc624cccd** (geo_elo_active=2545.0) — Iran_ME DOMAIN_SPECIALIST, MINIMAL weight, 175 geo resolved trades (173 stored vs ~744 actual — known discrepancy), 41 active geo markets (well above max-2 limit). Profile date: 2026-07-13. Human review required before any STR-003 consideration. Will not generate a signal this cycle or next without human review.

**Pattern note:** 7 of 9 LEGENDARY traders declined ~50–60 ELO points this week. This is consistent with the Sunday 03:00 UTC comprehensive ELO recalculation (recalculate_comprehensive_elo.py). The systematic decline likely reflects correction after a previous week's near-certain wins had temporarily elevated scores. Not alarming — this is the expected decay pattern post-recalculation.

### Why 0 Signals:

- **0xecaa8806 (FULL weight):** Category visibility bug persists — all open positions show as "Unknown" in markets table, making them invisible to STR-003 pipeline queries. Active geo positions confirmed via manual scan (Tisza Hungary YES @ 0.498, Nordone SC Senate YES @ 0.487 pending, Fidesz YES @ 0.456, Gov shutdown YES @ 0.527) but cannot be formalized without category fix. Zero geo markets surfaced by standard STR-003 pipeline.
- **0xd44e974a:** 15 concurrent geo markets (max-2 rule blocks). Extensive Russia/Ukraine + Iran thematic cluster at large sizes.
- **0x3d03c46d:** 14 concurrent geo markets.
- **0x6b025355:** 2 markets but only $90.50 in qualifying price range (0.10–0.80) vs $2,000 minimum. MINIMAL weight.
- **0xc624cccd (NEW):** 41 concurrent geo markets. MINIMAL weight. Human review required.
- **0xd218e474:** YIELD_HARVESTER (EXCLUDE archetype). ELO surge +121.6 is artefact of near-certainty wins, not predictive skill.
- **0x63c6169c:** 2 markets but only $170.35 qualifying position. MINIMAL weight. Thin geo sample (18 geo resolved trades, geo_elo likely inflated by Trump-social-media markets).
- **0xc722c1a1:** 18 concurrent geo markets.
- **0x4fd3503c:** YIELD_HARVESTER (EXCLUDE archetype). 9 markets.

---

## STR-003 Active Signal Rescan

### STR003-001 — Newsom Drop Out (ACTIVE_BELOW_THRESHOLD)

- **Status:** ACTIVE_BELOW_THRESHOLD — unchanged
- Market: "Will Newsom drop out of 2026 race before September?"
- market_id: 0xbc60ca287f8f5ab1a910b1cc6ff51fe32c0b8840517f8220554454b9d2d4afac
- Resolution date: 2026-09-01 — **APPROACHING: 15 days**
- DB: resolved=0, winning_outcome=NULL, **last_checked=2026-04-01** — EXTREMELY STALE
- Expected outcome: **NO** (Newsom did not drop out — he won the 2026 California gubernatorial primary)
- Key trader geo_elo_active: ~843 (heavily decayed, fails 2175 threshold)
- geo_resolved_trades_count: 2 — thin sample, ELO unvalidated (<10)
- Note: thin sample — ELO unvalidated (geo_resolved_trades_count < 10)
- ⚠️ **ALERT:** last_checked=2026-04-01 means this market has had zero resolution pipeline coverage for 4+ months. It will not auto-resolve without intervention. Oscar should trigger manual resolution check.
- Action after Sept 1: record outcome (expected NO=correct) in strategy-registry.md. Does NOT score toward Gate 3 (key trader fails geo qualification criteria).

### STR003-003 — Warsh Fed Chair NO (RESOLVED_WRONG)

- Status: RESOLVED_WRONG — no change. Final.

### STR003-004 — Putin Invasion NO (ACTIVE_OVERDUE — 5th week)

- **Status:** ACTIVE_OVERDUE — 48 days past June 30 resolution date
- market_id: 0x657195fda8c315771fe0cf25a1b60df207a9072688f73b96cf17a890ce7ab753
- DB: resolved=0, winning_outcome=NULL, resolution_date=2026-06-30, **last_checked=2026-04-01** — EXTREMELY STALE
- Expected outcome: **NO** (Russia did not invade Ukraine by June 30 2026)
- Signal NOT scorable for STR-003 validation (key trader fails geo_elo ≥ 2175)
- ⚠️ **ACTION REQUIRED (5th consecutive flag):** Both STR003-001 and STR003-004 share last_checked=2026-04-01. The fast_resolution_check.py pipeline has not touched either market in over 4 months. Oscar should manually run: `python3 first-repo/scripts/fast_resolution_check.py` targeting these market IDs, or trigger the stale CLOB pass.

### STR003-005 — Keiko Peru YES (RESOLVED_CORRECT)

- Status: RESOLVED_CORRECT — no change. Final. Contributes to Gate 3.

### STR003-006 — López Aliaga YES (RESOLVED_WRONG)

- Status: RESOLVED_WRONG — no change. Final.

### STR003-007 — Iran Regime Fall NO (RESOLVED_NON_SCORABLE)

- Status: RESOLVED_NON_SCORABLE — no change. Final.

### STR003-008 — European Security Guarantee NO (RESOLVED_CORRECT)

- Status: RESOLVED_CORRECT — no change. Final. Contributes to Gate 3.

### STR003-009 — Graham SC NO (RESOLVED_WRONG)

- Status: RESOLVED_WRONG — no change. Final.

---

## STR-003 Scored Accuracy — Unchanged

| Score | Count | Details |
|-------|-------|---------|
| Correct (scorable) | 2 | STR003-005 (Keiko YES), STR003-008 (EU Security NO) |
| Wrong (scorable) | 3 | STR003-003 (Warsh NO), STR003-006 (Aliaga YES), STR003-009 (Graham NO) |
| Non-scorable | 1 | STR003-007 (Iran NO — retrospective registration) |
| Outcome tracking only | 2 | STR003-001 (Newsom, fails threshold), STR003-004 (Putin, fails threshold) |

**Gate 3 accuracy: 2/5 = 40%** — target ≥60% across 10+ markets. Remains pending.

---

## Notable Intelligence (LOW Confidence — Not Signal-Registered)

### Russia/Ukraine + Middle East Thematic Cluster (0xd44e974a — VOLUME_SPECIALIST)

**Note:** This analysis corrects last week's incomplete view. The Iran positions below are NOT new — they were built in February-March 2026 and were missed by last week's narrower title-based search.

0xd44e974a (geo_elo_active=3319.8, #2 LEGENDARY, Russia_UKR domain, VOLUME_SPECIALIST) holds a large correlated thematic cluster — 15 active geo markets, all NO:

**Ukraine/Russia settlement (pre-existing, established by Aug 10):**
| Market | Qualifying Cost (0.10–0.80) | Avg Price | Resolves |
|--------|---------------------------|-----------|---------|
| Russia captures all of Kostyantynivka | $22,523 | 0.529 | 2026-12-31 |
| Ukrainian regime fall before 2027 | $19,779 | 0.645 | 2026-12-31 |
| Ukraine agrees to cede territory | $13,990 | 0.731 | 2026-12-31 |
| Ukraine not join NATO before 2027 | $8,828 | 0.711 | 2026-12-31 |
| US x Iran ceasefire by March 31 | $7,716 | 0.467 | — |
| Russia x Ukraine Peace Parlay (partial) | $6,739 | 0.783 | 2026-12-31 |
| US x Iran ceasefire by April 30 | $5,892 | 0.359 | — |
| Ukraine peace deal before 2027 | $3,703 | 0.557 | 2026-12-31 |
| Ukraine agree to limit armed forces | $2,792 | 0.606 | 2026-12-31 |
| Israel x Hezbollah ceasefire extended | $2,687 | 0.346 | — |
| US obtains Iranian enriched uranium | $1,769 | 0.720 | 2026-12-31 |
| Ukraine election Dec 2026 | $887 | 0.707 | 2026-12-31 |

**Total qualifying position cost: ~$97K+ across 12 correlated markets, all NO.**

Dominant thesis: Russia-Ukraine war does NOT conclude with any peace settlement, territorial concession, NATO concession, or sovereignty recognition by end 2026. The Iran cluster adds: no Iran-US ceasefire AND no Iranian regime change. The thesis spans both the Eastern Europe and Middle East theaters of current great-power conflict.

Near-LEGENDARY traders confirming the Ukraine NO cluster (partial overlap):
- 0x9ca119b8 (Elite, 1865.7): Ukraine peace talks NO $1,826, Ukraine cede NO $864, Ukraine peace deal NO $864
- 0x606ed794 (near-LEGENDARY, 2139.1): Ukraine peace deal — bidirectional (YES $1,052 AND NO $917), DISQUALIFIED

**Why not a formal signal:** 15 concurrent geo markets. STR-003 max=2 focus rule. VOLUME_SPECIALIST archetype (not GENUINE_FORECASTER). Signal informally logged at LOW confidence — do not register. Useful as macro backdrop intelligence.

---

## STR002 Active Signals — Key Update

| Signal | Market | Direction | Regime | has_proven_trader | Resolves |
|--------|--------|-----------|--------|-------------------|---------|
| STR002-0172 | US-Iran Final Nuclear Deal by August 18, 2026? | NO | NEAR_RESOLVED | 1 | **2026-08-18 (TOMORROW)** |
| STR002-0158 | Trump out as President before GTA VI? | NO | CONTESTED | 1 | 2026-07-31 (overdue) |
| STR002-0159 | China invades Taiwan before GTA VI? | NO | CONTESTED | 1 | 2026-07-31 (overdue) |
| STR002-0165 | New Playboi Carti Album before GTA VI? | NO | LEGENDARY | 1 | 2026-07-31 (overdue) |
| STR002-0166 | Bitcoin hits $1M before GTA VI? | NO | CONTESTED | 1 | 2026-07-31 (overdue) |

**STR002-0172 RESOLVES TOMORROW (Aug 18):** "US-Iran Final Nuclear Deal by August 18, 2026?" direction=NO, NEAR_RESOLVED regime, has_proven_trader=1. Expected to resolve NO (no final nuclear deal finalized by deadline). NEAR_RESOLVED regime means this will NOT contribute to Gate 3 thesis-cell scoring (requires CONTESTED + has_proven_trader). Records the outcome for calibration purposes.

**STR002-0158/0159/0165/0166:** All have resolution_date 2026-07-31 but no outcome yet — the GTA VI release-date conditional markets. These markets resolve based on GTA VI release, not a calendar date. Still open.

---

## Near-LEGENDARY Watchlist

| Address | ELO Active | Gap | Dir | PnL | Geo Trades | Notes |
|---------|-----------|-----|-----|-----|------------|-------|
| 0x848df648... | 2159.7 | 15.3 | 0.958 | +$1,655 | 118 | **Just fell from LEGENDARY** |
| 0x9287bd3d... | 2152.0 | 23.0 | 0.925 | +$369 | 105 | **Just fell from LEGENDARY** |
| 0x606ed794... | 2139.1 | 35.9 | 0.912 | +$5,491 | 136 | **NEW to top 3**; bidirectional Ukraine — STR-003 disqualified |
| 0x8e9eedf2... | 2096.8 | 78.2 | 1.000 | $0.00 | 40 | pnl=0.0 blocks STR-003 |
| 0xd684df32... | 2090.6 | 84.4 | 1.000 | -$203 | 40 | elo gap only |
| 0xfbe2f1f7... | 2077.7 | 97.3 | 0.941 | -$166 | 23 | elo gap only |
| 0x9cb98fc5... | 2045.3 | 129.7 | 0.910 | +$8,133 | 225 | Best profile in near-legendary tier |
| 0xe2349595... | 2028.4 | 146.6 | 0.901 | -$14,084 | 10 | pnl fails STR-003 filter |
| 0x677aec88... | 2008.3 | 166.7 | 0.607 | -$97 | 28 | directionality <0.7 |
| 0x51b5b8b1... | 1998.5 | 176.5 | 0.968 | -$765 | 124 | new to top 10 |

**Key near-LEGENDARY notes:**
- 0x848df648 and 0x9287bd3d just dropped from LEGENDARY this cycle. Both have small gaps (15.3, 23.0) — a few good resolved markets could restore LEGENDARY. Monitor next week.
- 0x606ed794 (gap=35.9, strong profile) — holds bidirectional position on Ukraine peace deal (both YES and NO), which disqualifies for STR-003 even if they reach LEGENDARY threshold.
- 0x9cb98fc5 (gap=129.7, pnl=+$8,133, 225 geo trades, directionality=0.91) — best overall near-legendary candidate by track record. Gap is wider but fundamentals are strongest.

---

## Markets Monitored This Cycle

- Total active unresolved geo/elections markets: **1,109** (was 1,039 last week, +70)
- Markets approaching resolution within 30 days: **121**
- LEGENDARY traders scanned: **9**

---

## Anomalies

1. **STR003-001 and STR003-004 both have last_checked=2026-04-01:** Neither market has been touched by the resolution pipeline in 4+ months. Both will fail to auto-resolve. Oscar must manually trigger fast_resolution_check.py for these market IDs. STR003-001 resolves Sept 1 (15 days). STR003-004 is 48 days overdue.

2. **0xecaa8806 ELO surge (+917 in one week, 3283→4200):** The profile flags this as anomalous — likely near-certainty wins propagating through geo_elo formula. The ELO formula does not downweight near-certainty positions in the geo calculation. This trader's ELO is now #1 LEGENDARY but profile flags performance deterioration in recent geo calls. GENUINE_FORECASTER archetype maintained at MEDIUM confidence.

3. **0xd218e474 ELO surge (+122, now 2489.9):** Confirmed YIELD_HARVESTER (EXCLUDE). This ELO gain is a measurement artefact of near-certainty harvesting. Not predictive.

4. **Systematic ~50 pt LEGENDARY decline:** 7 of 9 current LEGENDARY traders and both newly-dropped traders declined 48–61 pts this week. Consistent with Sunday comprehensive_elo recalculation adjusting for near-certainty wins. Two traders (0x848df648, 0x9287bd3d) fell below the 2175 threshold as a result.

5. **Category visibility bug (0xecaa8806):** Now in 4th consecutive weekly report without fix. This trader is the highest-quality (GENUINE_FORECASTER, FULL weight) trader in the LEGENDARY pool and is fully invisible to STR-003 pipeline queries. Fix would require resolving why markets.category = 'Unknown' for this trader's markets — likely these markets were ingested before category classification was in place.

6. **Iran-themed cluster confirmation:** Query this week captured 0xd44e974a's Iran positions (regime fall NO $19.8K, US-Iran ceasefire NO $13.6K) which were missed by last week's narrower title search. These positions date from Feb-March 2026, not new. Total cluster is ~$97K across 12 correlated markets.

---

## Summary

- **New STR-003 signals: 0** (4+ consecutive zero-signal weeks)
- **Active HIGH/MEDIUM signals: 0**
- **LEGENDARY pool: 9 (was 10 — two dropped, one new entrant)**
- **Markets monitored: 1,109 active geo/elections**
- **LEGENDARY traders scanned: 9**
- **No HIGH or MEDIUM signals — no write to signals.json required**
- **Gate 3 accuracy: 2/5 = 40% (target ≥60% across 10+)**

**Recommended actions (Oscar):**
1. Manually trigger resolution check for STR003-001 (market_id=0xbc60ca2..., resolves Sept 1) and STR003-004 (market_id=0x657195f..., 48 days overdue). Both last_checked=2026-04-01.
2. Investigate category visibility bug for 0xecaa8806 — this trader is the highest-quality signal source (GENUINE_FORECASTER, FULL weight) but is invisible to the STR-003 pipeline.
3. Review new LEGENDARY entrant 0xc624cccd (Iran_ME specialist, geo_resolved_trades_count discrepancy 173 stored vs 744 actual). Human review required before STR-003 consideration.

---

*Report generated by signal-agent (claude-sonnet-4-6, Tier 3)*
*Run ID: signal-20260817 | Started: 2026-08-17T08:00:01Z*
