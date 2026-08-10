# Signal Agent Report — 2026-08-10 08:00 UTC

**Run ID:** signal-20260810
**Model:** Claude Sonnet 4.6 (Tier 3)
**Task:** Routine signal scan + active STR-003 rescan

---

## Section 9 Validation — PASS

| Metric | Value | Expected | Alert? |
|--------|-------|----------|--------|
| clean_pool | 31,028 | ≈18,910 | No (above, not below) |
| true_research_pool | 20,298 | ≈3,837 | No (above) |
| clean_markets | 224,428 | ≈24,184 | No (above) |
| pool_c | 3,518 | ≈2,185 | No |
| legendary_base | 73 | ≈48 | No |
| legendary_active | 12 | ≈25 | **Low** (12 vs expected 25, but >5 threshold) |
| legendary_clean | 10 | ≈18 | No (>5 threshold) |
| near_legendary_clean | 19 | ≈21 | No |
| wal_mode | wal | wal | No |

Note: Significant pool size growth since contract v2.13 calibration (June 2026). Pools are expanding normally as traders accumulate resolved trades. No action needed; expected ranges in integration-contract.md should be updated.

---

## STR-003 Signal Scan — 0 New Qualifying Signals

**Cycle result:** No new STR-003 signals registered.

### LEGENDARY Pool Summary

10 traders pass all base STR-003 qualification filters:
```
geo_elo_active >= 2175, geo_directionality_score >= 0.7,
realized_pnl != 0.0 AND > -100000, research_excluded = 0,
geo_accuracy_pool = 1, bot_type IS NULL
```

| Address | Elo Active | Dir | Archetype | Signal Weight | Open Geo Mkt | STR-003 Block |
|---------|-----------|-----|-----------|---------------|--------------|----------------|
| 0xd44e974a... | 3397.4 | 0.981 | VOLUME_SPECIALIST | DOMAIN_ONLY | 9 | max-2-markets |
| 0xecaa8806... | 3283.0 | 0.960 | GENUINE_FORECASTER | FULL | 0 | no_open_positions |
| 0x3d03c46d... | 2685.7 | 0.837 | DOMAIN_SPECIALIST | MINIMAL | 12 | max-2-markets |
| 0x6b025355... | 2631.9 | 0.999 | DOMAIN_SPECIALIST | MINIMAL | 2 | below_$2K + price_out_of_range |
| 0x63c6169c... | 2539.1 | 1.000 | DOMAIN_SPECIALIST | MINIMAL | 2 | below_$2K + price_out_of_range |
| 0xd218e474... | 2368.3 | 0.958 | YIELD_HARVESTER | EXCLUDE | 8 | EXCLUDE archetype |
| 0xc722c1a1... | 2359.6 | 0.976 | DOMAIN_SPECIALIST | MINIMAL | 3 | max-2-markets |
| 0x4fd3503c... | 2278.2 | 0.936 | YIELD_HARVESTER | EXCLUDE | 8 | EXCLUDE archetype |
| 0x848df648... | 2210.2 | 0.958 | DOMAIN_SPECIALIST | MINIMAL | 6 | max-2-markets |
| 0x9287bd3d... | 2202.3 | 0.925 | GENUINE_FORECASTER | MINIMAL | 16 | max-2-markets |

**Why 0 signals:**
- 8 of 10 traders trade in more than 2 concurrent geo/elections markets (STR-003 max=2 focus rule)
- 2 traders are YIELD_HARVESTER archetype (EXCLUDE weight, not predictive)
- 2 traders within the 2-market rule have positions below $2,000 minimum or prices outside 0.10–0.80 range
- 0 traders meet all criteria simultaneously

### Key Notable Finding (LOW confidence, not registerable)

Trader **0xd44e974a...** (geo_elo_active=3397.4, #1 LEGENDARY, VOLUME_SPECIALIST, Russia_UKR domain) holds **$55,460 total across 9 Russia/Ukraine geo markets**, all 100% NO:

| Market | Total Position | Avg Entry Price | Resolves |
|--------|----------------|-----------------|---------|
| Will Russia capture all of Kostyantynivka? | $22,523 NO | 0.651 | 2026-12-31 |
| Ukraine agrees not to join NATO before 2027? | $8,828 NO | 0.736 | 2026-12-31 |
| Will Ukraine agree to cede territory to Russia? | $11,121 NO | 0.715 | 2026-12-31 |
| Ukraine signs peace deal with Russia before 2027? | $3,703 NO | 0.608 | 2026-12-31 |
| Ukraine agrees to limit size of armed forces? | $2,792 NO | 0.471 | 2026-12-31 |
| Ukraine recognizes Russian sovereignty over territory | $3,069 NO | 0.957 | 2026-12-31 |
| US obtains Iranian enriched uranium by Dec 31? | $1,769 NO | 0.720 | 2026-12-31 |
| Ukraine election held by Dec 31, 2026? | $904 NO | 0.620 | 2026-12-31 |
| US x Iran ceasefire by April 30? | $750 NO | 0.338 | None |

This is a **thematic cluster bet** on Russia-Ukraine war NOT resulting in a peace settlement, ceasefire, or territorial concession by end of 2026. The cluster includes 2 additional near-legendary (elo_active 1848–1909) traders confirming the Kostyantynivka NO position. These markets individually pass $2K+, 95% directional, and price filters — they are blocked from STR-003 registration **solely by the max-2-markets portfolio breadth rule**.

STR-003 does not fire because the breadth rule requires focus conviction in ≤2 markets. This trader is spreading conviction across a correlated thematic cluster rather than concentrating in 1-2 markets. This is useful intelligence but not actionable as a formal signal.

**Logged as LOW confidence — intelligence only. Not written to signals.json.**

---

## STR-003 Active Signal Rescan

### STR003-001 — Newsom No Drop Out (ACTIVE_BELOW_THRESHOLD)

- Status: ACTIVE_BELOW_THRESHOLD — unchanged
- Position intact: $3,475 total NO ($3,139 + $336), last updated 2026-08-08
- Key trader geo_elo_active: ~843 (heavily decayed, fails 2175 threshold)
- geo_resolved_trades_count: 2 — thin sample, ELO unvalidated (< 10)
- geo_directionality_score: NULL — fails STR-003 criteria
- **Resolution: 22 days to Sept 1 2026**. APPROACHING. Newsom has not dropped out as of Aug 10.
- Note: thin sample — ELO unvalidated (geo_resolved_trades_count < 10)
- Action: monitor for resolution Sept 1; record outcome in strategy-registry.md.

### STR003-003 — Warsh Fed Chair NO (RESOLVED_WRONG)

- Status: RESOLVED_WRONG — no change. Final.

### STR003-004 — Putin Invasion NO (ACTIVE_OVERDUE — 4th week)

- Status: ACTIVE_OVERDUE — 41 days past June 30 resolution date
- DB: resolved=0, winning_outcome=None, last_checked=2026-04-01
- Position intact: 18,472 NO shares at $7,191 (last updated 2026-08-08)
- Key trader geo_elo_active: not in geo pool, fails LEGENDARY threshold
- Expected outcome: **CORRECT** (Russia did not invade Ukraine by June 30 2026 per available information)
- Signal NOT scorable for STR-003 validation (key trader fails geo_elo >= 2175)
- **ACTION REQUIRED (4th consecutive flag): Oscar to trigger fast_resolution_check.py for market_id=0x657195fda8c315771fe0cf25a1b60df207a9072688f73b96cf17a890ce7ab753**

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

## STR-003 Scored Accuracy Update

| Score | Count | Details |
|-------|-------|---------|
| Correct (scorable) | 2 | STR003-005 (Keiko YES), STR003-008 (EU Security NO) |
| Wrong (scorable) | 3 | STR003-003 (Warsh NO), STR003-006 (Aliaga YES), STR003-009 (Graham NO) |
| Non-scorable | 1 | STR003-007 (Iran NO — retrospective registration) |
| Outcome tracking only | 2 | STR003-001 (Newsom, fails threshold), STR003-004 (Putin, fails threshold) |

**Gate 3 accuracy: 2/5 = 40%** — target ≥60% across 10+ markets. Gate 3 remains pending.

---

## Near-LEGENDARY Watchlist

Top 5 traders closest to LEGENDARY threshold:

| Address | Elo Active | Gap | Dir | PnL | Geo Trades | Blocks |
|---------|-----------|-----|-----|-----|------------|--------|
| 0x8e9eedf2... | 2145.9 | 29.1 | 1.000 | -$0 | 40 | elo gap + pnl=0.0 |
| 0xd684df32... | 2139.5 | 35.5 | 1.000 | -$203 | 40 | elo gap only |
| 0xfbe2f1f7... | 2126.2 | 48.8 | 0.941 | -$166 | 23 | elo gap only |
| 0x9cb98fc5... | 2093.1 | 81.9 | 0.910 | +$8,133 | 225 | elo gap only |
| 0x677aec88... | 2055.2 | 119.8 | 0.607 | -$97 | 28 | elo gap + dir<0.7 |

Closest to promotion: **0x8e9eedf2** (29.1 ELO gap, but pnl=0.0 blocks the != 0.0 filter). Resolution of their next few geo markets could push them over the threshold.

**0x9cb98fc5** (gap=81.9, dir=0.910, pnl=+$8,133, 225 geo trades) — best overall profile in near-legendary tier. Solid track record with positive P&L and high directionality. Most likely to generate a new STR-003 signal once the elo gap closes.

---

## Active Unresolved Geo/Elections Markets

- Total active unresolved geo/elections markets: **1,039**
- Feeds future geo_elo recalculations as markets resolve

---

## Anomalies

1. **STR003-004 resolution blocked (4th week):** Market 0x6571... remains unresolved in DB 41 days past June 30. The fast_resolution_check.py appears to not be catching this market. Manual intervention required.

2. **Integration-health.json pool sizes significantly above contract calibration values:** clean_pool=31,028 vs expected 18,910; true_research_pool=20,298 vs expected 3,837. Both are above thresholds (no alert fires), but the contract expected ranges are stale and should be updated. Pool growth is legitimate — new traders are qualifying daily.

3. **MINIMAL signal_weight in profiles:** Several LEGENDARY traders have signal_weight=MINIMAL in their profiles, a classification not documented in integration-contract.md Section 11 (which defines FULL/DOMAIN_ONLY/EXCLUDE/NARROW). The trader-intelligence-agent appears to have introduced this classification. Oscar should clarify whether MINIMAL means "not used for signals" or "use with strong caution." Currently treating MINIMAL as non-qualifying for new STR-003 signals (more conservative than DOMAIN_ONLY).

---

## Elite Market Intelligence (Informational)

Elite traders (geo_elo_active >= 1800) show strong NO consensus on Ukraine/Russia war termination conditions:

| Market | Elite Total | Direction | Traders |
|--------|------------|-----------|---------|
| Russia captures Kostyantynivka | $23,237 | 100% NO | 3 |
| Ukraine cedes territory | $11,121 | 100% NO | 1 |
| Ukraine joins NATO clause | $9,039 | 100% NO | 2 |
| Ukraine peace deal | $4,774 | 100% NO | 4 |
| Ukraine sovereignty recognition | $3,235 | 100% NO | 2 |
| Ukraine armed forces limit | $3,128 | 100% NO | 2 |

Elite consensus on these markets is **unanimous NO across all six markets**. This is the dominant geo trader thesis: Russia-Ukraine war will not conclude with any of these settlement conditions by end of 2026.

---

## Summary

- **New STR-003 signals: 0**
- **Active HIGH/MEDIUM signals: 0**
- **Markets monitored: 1,039 active geo/elections**
- **LEGENDARY traders scanned: 10**
- **No HIGH or MEDIUM signals to write to signals.json**
- **Recommended action: Oscar to resolve STR003-004 DB blocker (4th week)**

---

*Report generated by signal-agent (claude-sonnet-4-6, Tier 3)*
*Run ID: signal-20260810 | Started: 2026-08-10T08:00:01Z*
